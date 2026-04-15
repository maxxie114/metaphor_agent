#!/usr/bin/env python3
"""
Agentic Inferential Metaphor Identification Pipeline

Processes sentences through a 4-agent pipeline (fully parallel across sentences):
  1. Candidate Generator  — identify possible active metaphors
  2. Inferential Filter    — keep only inferential metaphors (strict)
  3. Span Extractor        — extract exact verbatim text spans
  4. Verifier              — independent second opinion (strict)

All 100 sentences run in parallel. Each sentence's 4 agents run sequentially.
Full reasoning logs saved to logs/debug_log.jsonl.

Usage:
    export OPENAI_API_KEY="your-key"
    python main.py [--input FILE] [--output FILE] [--annotator ID]
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from openai import AsyncOpenAI

from config import OPENAI_API_KEY, INPUT_CSV, OUTPUT_CSV, ANNOTATOR_ID
from utils.csv_io import read_input_csv, write_output_csv
from utils.dedup import dedupe_rows
from agents.candidate_generator import generate_candidates
from agents.inferential_filter import filter_inferential
from agents.span_extractor import extract_spans
from agents.verifier import verify_spans


LOG_DIR = Path("logs")
DEBUG_LOG_PATH = LOG_DIR / f"debug_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"


def write_debug_log(entry: dict) -> None:
    """Append one JSON line to the debug log."""
    with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def process_sentence(
    client: AsyncOpenAI,
    row: dict,
    idx: int,
    total: int,
    annotator_id: str,
    semaphore: asyncio.Semaphore,
) -> list[dict]:
    """Run the full 4-agent pipeline on a single sentence."""
    async with semaphore:
        slug = row["slug"]
        triplet_id = row["triplet_id"]
        sentence = row["original_sentence"]

        log_entry = {
            "idx": idx,
            "slug": slug,
            "triplet_id": triplet_id,
            "sentence": sentence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agents": {},
        }

        print(f"[{idx}/{total}] {slug} | {triplet_id}")

        # --- Agent 1: Candidate Generator ---
        candidates, log1 = await generate_candidates(client, sentence)
        log_entry["agents"]["1_candidate_generator"] = log1
        print(f"  [{idx}] Agent 1: {len(candidates)} candidates")

        if not candidates:
            log_entry["result"] = []
            write_debug_log(log_entry)
            return []

        # --- Agent 2: Inferential Filter ---
        inferential, log2 = await filter_inferential(client, sentence, candidates)
        log_entry["agents"]["2_inferential_filter"] = log2
        print(f"  [{idx}] Agent 2: {len(inferential)} passed filter")

        if not inferential:
            log_entry["result"] = []
            write_debug_log(log_entry)
            return []

        # --- Agent 3: Span Extractor ---
        raw_spans, log3 = await extract_spans(client, sentence, inferential)
        log_entry["agents"]["3_span_extractor"] = log3
        print(f"  [{idx}] Agent 3: {len(raw_spans)} spans")

        if not raw_spans:
            log_entry["result"] = []
            write_debug_log(log_entry)
            return []

        # --- Agent 4: Verifier ---
        verified_spans, log4 = await verify_spans(client, sentence, raw_spans)
        log_entry["agents"]["4_verifier"] = log4
        print(f"  [{idx}] Agent 4: {len(verified_spans)} verified")

        # --- Build output rows ---
        output_rows = []
        for span in verified_spans:
            output_rows.append({
                "slug": slug,
                "triplet_id": triplet_id,
                "metaphor_span": span,
                "selected": "",
                "annotator_id": annotator_id,
            })

        log_entry["result"] = [r["metaphor_span"] for r in output_rows]
        write_debug_log(log_entry)

        return output_rows


async def run_pipeline(input_path: str, output_path: str, annotator_id: str) -> None:
    """Run the full pipeline on all sentences in parallel."""
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    rows = read_input_csv(input_path)
    total = len(rows)

    LOG_DIR.mkdir(exist_ok=True)

    print(f"Loaded {total} sentences from {input_path}")
    print(f"Model: {__import__('config').MODEL}")
    print(f"Output: {output_path}")
    print(f"Debug log: {DEBUG_LOG_PATH}")
    print(f"Annotator ID: {annotator_id}")
    print(f"Running ALL {total} sentences in parallel")
    print("=" * 70)

    start_time = time.time()

    # Semaphore to limit concurrency (avoid rate limits)
    # 100 sentences * 4 agents = 400 calls, but only 4 concurrent per sentence
    # With semaphore=50, up to 50 sentences process at once
    semaphore = asyncio.Semaphore(50)

    tasks = [
        process_sentence(client, row, idx, total, annotator_id, semaphore)
        for idx, row in enumerate(rows, 1)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect all output rows (in order)
    all_output_rows = []
    errors = 0
    for idx, result in enumerate(results, 1):
        if isinstance(result, Exception):
            print(f"  [ERROR] Sentence {idx}: {result}")
            errors += 1
        else:
            all_output_rows.extend(result)

    # Deduplicate overlapping/nested spans per sentence
    before = len(all_output_rows)
    all_output_rows = dedupe_rows(all_output_rows)
    print(f"Deduped {before} -> {len(all_output_rows)} rows "
          f"(removed {before - len(all_output_rows)} redundant)")

    # Write final output
    write_output_csv(all_output_rows, output_path)

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"DONE. Processed {total} sentences in {elapsed:.1f}s")
    print(f"Found {len(all_output_rows)} inferential metaphor spans")
    print(f"Errors: {errors}")
    print(f"Output saved to {output_path}")
    print(f"Debug log saved to {DEBUG_LOG_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Agentic Inferential Metaphor Identification")
    parser.add_argument("--input", default=INPUT_CSV, help="Input CSV path")
    parser.add_argument("--output", default=OUTPUT_CSV, help="Output CSV path")
    parser.add_argument("--annotator", default=ANNOTATOR_ID, help="Annotator ID for output")
    args = parser.parse_args()

    if not OPENAI_API_KEY:
        print("ERROR: Set OPENAI_API_KEY in .env or environment")
        sys.exit(1)

    asyncio.run(run_pipeline(args.input, args.output, args.annotator))


if __name__ == "__main__":
    main()
