#!/usr/bin/env python3
"""
Standalone script to dedupe an existing output CSV.

Usage:
    python utils/dedupe_csv.py <input.csv> [output.csv]
"""

import csv
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.dedup import dedupe_rows


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input.csv> [output.csv]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else input_path.replace(".csv", "_deduped.csv")

    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Loaded {len(rows)} rows from {input_path}")

    deduped = dedupe_rows(rows)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["slug", "triplet_id", "metaphor_span", "selected", "annotator_id"],
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()
        writer.writerows(deduped)

    removed = len(rows) - len(deduped)
    print(f"Wrote {len(deduped)} rows to {output_path} (removed {removed} redundant)")


if __name__ == "__main__":
    main()
