"""Deduplicate overlapping metaphor spans within the same sentence."""


def dedupe_spans(spans: list[str]) -> list[str]:
    """
    Remove redundant spans where one is a substring of another.

    Keeps only maximal spans (no other span in the list strictly contains it).
    Example:
        ["thirst", "colossal thirst", "California's colossal thirst"]
        -> ["California's colossal thirst"]

    Also removes exact duplicates.
    """
    if not spans:
        return []

    # Remove exact duplicates while preserving order
    seen = set()
    unique = []
    for s in spans:
        if s not in seen:
            seen.add(s)
            unique.append(s)

    # Keep only spans that are NOT a proper substring of another span
    result = []
    for i, s in enumerate(unique):
        is_contained = False
        for j, other in enumerate(unique):
            if i == j:
                continue
            # If s is strictly inside other (and shorter), drop s
            if s in other and len(s) < len(other):
                is_contained = True
                break
        if not is_contained:
            result.append(s)

    return result


def dedupe_rows(rows: list[dict]) -> list[dict]:
    """
    Deduplicate spans per (slug, triplet_id) group.
    Expects rows with keys: slug, triplet_id, metaphor_span, selected, annotator_id.
    """
    # Group by triplet_id
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        key = row["triplet_id"]
        grouped.setdefault(key, []).append(row)

    deduped = []
    for triplet_id, group in grouped.items():
        spans = [r["metaphor_span"] for r in group]
        kept_spans = dedupe_spans(spans)
        kept_set = set(kept_spans)
        for row in group:
            if row["metaphor_span"] in kept_set:
                deduped.append(row)
                kept_set.discard(row["metaphor_span"])  # keep only first occurrence

    return deduped
