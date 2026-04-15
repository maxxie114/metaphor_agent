#!/usr/bin/env python3
"""
Convert OpenAI responses_export.json into a readable CSV for scholarly analysis.

Each row = one API call, with columns for the agent type, input sentence,
the model's JSON output, reasoning tokens, and full metadata.

Usage:
    python json_to_csv.py [input.json] [output.csv]
"""

import csv
import json
import sys
from datetime import datetime, timezone

AGENT_LABELS = {
    "You are an expert linguist": "1_candidate_generator",
    "You are a specialist in inferential": "2_inferential_filter",
    "You are a precise text extraction": "3_span_extractor",
    "You are an independent reviewer": "4_verifier",
}


def classify_agent(instructions: str) -> str:
    for prefix, label in AGENT_LABELS.items():
        if instructions.startswith(prefix):
            return label
    return "unknown"


def extract_sentence(input_text: str) -> str:
    """Pull out the SENTENCE / ORIGINAL SENTENCE from the input prompt."""
    for marker in ["SENTENCE: ", "ORIGINAL SENTENCE: "]:
        if marker in input_text:
            after = input_text.split(marker, 1)[1]
            # Sentence ends at the next double newline or end
            return after.split("\n\n")[0].strip()
    return ""


def extract_input_text(item: dict) -> str:
    """Get the full user input text from the response item."""
    for inp in item.get("input", []):
        for c in inp.get("content", []):
            if c.get("type") == "input_text":
                return c.get("text", "")
    return ""


def extract_output_text(item: dict) -> str:
    """Get the model's output message text."""
    for o in item.get("output", []):
        if o.get("type") == "message":
            for c in o.get("content", []):
                if "text" in c:
                    return c["text"]
    return ""


def parse_responses(data: list[dict]) -> list[dict]:
    """Parse the full export into flat CSV rows."""
    rows = []

    for item in data:
        instructions = item.get("instructions", "")
        agent = classify_agent(instructions)

        # Skip non-metaphor responses
        if agent == "unknown":
            continue

        input_text = extract_input_text(item)
        sentence = extract_sentence(input_text)
        output_text = extract_output_text(item)

        usage = item.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        reasoning_tokens = usage.get("output_tokens_details", {}).get("reasoning_tokens", 0)
        cached_tokens = usage.get("input_tokens_details", {}).get("cached_tokens", 0)

        created_at = item.get("created_at", 0)
        timestamp = datetime.fromtimestamp(created_at, tz=timezone.utc).isoformat() if created_at else ""

        rows.append({
            "response_id": item.get("id", ""),
            "timestamp": timestamp,
            "model": item.get("model", ""),
            "agent": agent,
            "sentence": sentence,
            "output_json": output_text,
            "has_output": "yes" if output_text else "no",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "reasoning_tokens": reasoning_tokens,
            "cached_tokens": cached_tokens,
            "total_tokens": usage.get("total_tokens", 0),
            "reasoning_effort": item.get("reasoning", {}).get("effort", ""),
            "status": item.get("status", ""),
        })

    # Sort by timestamp then agent order
    rows.sort(key=lambda r: (r["timestamp"], r["agent"]))
    return rows


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else "logs/responses_export.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "logs/responses_analysis.csv"

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Loaded {len(data)} total responses from {input_path}")

    rows = parse_responses(data)
    print(f"Filtered to {len(rows)} metaphor-related responses")

    fieldnames = [
        "response_id", "timestamp", "model", "agent", "sentence",
        "output_json", "has_output",
        "input_tokens", "output_tokens", "reasoning_tokens",
        "cached_tokens", "total_tokens",
        "reasoning_effort", "status",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")

    # Summary stats
    agents = {}
    for r in rows:
        agents[r["agent"]] = agents.get(r["agent"], 0) + 1
    print("\nBy agent:")
    for agent, count in sorted(agents.items()):
        print(f"  {agent}: {count}")

    has_output = sum(1 for r in rows if r["has_output"] == "yes")
    print(f"\nWith output text: {has_output}/{len(rows)}")
    print(f"Missing output (need re-download): {len(rows) - has_output}")


if __name__ == "__main__":
    main()
