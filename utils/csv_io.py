import pandas as pd
from pathlib import Path


def read_input_csv(path: str) -> list[dict]:
    """Read the input CSV and return a list of row dicts with slug, triplet_id, original_sentence."""
    df = pd.read_csv(path)
    return df.to_dict(orient="records")


def write_output_csv(rows: list[dict], path: str) -> None:
    """Write the output CSV with columns: slug, triplet_id, metaphor_span, selected, annotator_id."""
    df = pd.DataFrame(rows, columns=["slug", "triplet_id", "metaphor_span", "selected", "annotator_id"])
    df.to_csv(path, index=False, quoting=1)  # quoting=1 = QUOTE_ALL to match template
    print(f"Wrote {len(df)} rows to {path}")
