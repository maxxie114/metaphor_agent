#!/usr/bin/env python3
"""
Convert the pipeline console log into the output CSV format.

Parses the log for sentence headers (slug, triplet_id) and verified spans (* lines),
then writes the output CSV matching the template schema.

Usage:
    python log_to_csv.py <logfile> [output.csv]
"""

import csv
import re
import sys


def parse_log(log_path: str) -> list[dict]:
    """Parse the pipeline log and extract verified metaphor spans."""
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    rows = []
    current_slug = None
    current_triplet_id = None
    in_verifier = False

    # Pattern for sentence header: [N/100] slug | triplet_id
    header_re = re.compile(r"^\[(\d+)/(\d+)\]\s+(\S+)\s+\|\s+(\S+)")

    for line in lines:
        line = line.rstrip("\n")

        # Match sentence header
        m = header_re.match(line)
        if m:
            current_slug = m.group(3)
            current_triplet_id = m.group(4)
            in_verifier = False
            continue

        # Detect verifier section
        if "Agent 4 (Verifier)..." in line:
            in_verifier = True
            continue

        # Detect start of next agent or next sentence (end of verifier section)
        if in_verifier and ("Agent " in line or line.startswith("[")):
            in_verifier = False
            # If it's a new sentence header, re-check
            m = header_re.match(line)
            if m:
                current_slug = m.group(3)
                current_triplet_id = m.group(4)
            continue

        # Capture verified spans (lines starting with "    * ")
        if in_verifier and line.strip().startswith("* "):
            span = line.strip()[2:].strip().strip('"')
            if current_slug and current_triplet_id and span:
                rows.append({
                    "slug": current_slug,
                    "triplet_id": current_triplet_id,
                    "metaphor_span": span,
                    "selected": "",
                    "annotator_id": "agent",
                })

    return rows


def write_csv(rows: list[dict], output_path: str) -> None:
    """Write rows to CSV matching the output template schema."""
    fieldnames = ["slug", "triplet_id", "metaphor_span", "selected", "annotator_id"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {output_path}")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <logfile> [output.csv]")
        sys.exit(1)

    log_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "metaphor_output_from_log.csv"

    rows = parse_log(log_path)
    write_csv(rows, output_path)

    # Print summary
    slugs = set(r["slug"] for r in rows)
    print(f"  Sentences with metaphors: {len(slugs)}")
    print(f"  Total metaphor spans: {len(rows)}")


if __name__ == "__main__":
    main()
