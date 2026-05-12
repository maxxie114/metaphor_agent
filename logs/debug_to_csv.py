#!/usr/bin/env python3
"""
Convert a debug JSONL log into a readable CSV with one row per candidate expression,
showing how it flowed through all 4 agents.

Usage:
    python3 logs/debug_to_csv.py logs/debug_log_20260414_232310.jsonl logs/exp4_reasoning.csv
"""

import csv
import json
import sys


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input.jsonl> <output.csv>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    rows = []

    with open(input_path, encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            idx = entry["idx"]
            slug = entry["slug"]
            triplet_id = entry["triplet_id"]
            sentence = entry["sentence"]
            final_spans = set(entry.get("result", []))

            agents = entry["agents"]

            # Agent 1: candidates
            a1 = agents.get("1_candidate_generator", {})
            a1_output = json.loads(a1.get("output", "{}"))
            candidates = a1_output.get("candidates", [])

            # Agent 2: evaluations (keyed by expression)
            a2 = agents.get("2_inferential_filter", {})
            a2_evals = {e["expression"]: e for e in a2.get("evaluations", [])}

            # Agent 3: verified spans (keyed by expression)
            a3 = agents.get("3_span_extractor", {})
            a3_output = json.loads(a3.get("output", "{}"))
            a3_spans = {s["expression"]: s.get("span", "") for s in a3_output.get("spans", [])}
            a3_verified = set(a3.get("verified_spans", []))

            # Agent 4: verifier (keyed by span)
            a4 = agents.get("4_verifier", {})
            a4_evals = {e["span"]: e for e in a4.get("evaluations", [])}

            for cand in candidates:
                expr = cand["expression"]

                # Agent 2 eval
                a2_eval = a2_evals.get(expr, {})
                a2_inferential = a2_eval.get("is_inferential", "")
                a2_reasoning = a2_eval.get("reasoning", "")

                # Agent 3 span
                a3_span = a3_spans.get(expr, "")
                a3_verified_ok = a3_span in a3_verified if a3_span else ""

                # Agent 4 eval (match on span text)
                span_text = a3_span or expr
                a4_eval = a4_evals.get(span_text, {})
                a4_keep = a4_eval.get("keep", "")
                a4_confidence = a4_eval.get("confidence", "")
                a4_reasoning = a4_eval.get("reasoning", "")

                in_final = span_text in final_spans or expr in final_spans

                rows.append({
                    "idx": idx,
                    "slug": slug,
                    "triplet_id": triplet_id,
                    "sentence": sentence,
                    "expression": expr,
                    "source_domain": cand.get("source_domain", ""),
                    "target_domain": cand.get("target_domain", ""),
                    "a1_reasoning": cand.get("reasoning", ""),
                    "a2_is_inferential": a2_inferential,
                    "a2_reasoning": a2_reasoning,
                    "a3_span": a3_span,
                    "a3_substring_verified": a3_verified_ok,
                    "a4_keep": a4_keep,
                    "a4_confidence": a4_confidence,
                    "a4_reasoning": a4_reasoning,
                    "in_final_result": in_final,
                })

    fieldnames = [
        "idx", "slug", "triplet_id", "sentence",
        "expression", "source_domain", "target_domain", "a1_reasoning",
        "a2_is_inferential", "a2_reasoning",
        "a3_span", "a3_substring_verified",
        "a4_keep", "a4_confidence", "a4_reasoning",
        "in_final_result",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
