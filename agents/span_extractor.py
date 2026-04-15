"""Agent 3: Span Extractor — extract exact verbatim spans from the original sentence."""

import json
from openai import AsyncOpenAI
from prompts.templates import SPAN_EXTRACTOR_SYSTEM, SPAN_EXTRACTOR_USER
from config import MODEL


async def extract_spans(client: AsyncOpenAI, sentence: str, metaphors: list[dict]) -> tuple[list[str], dict]:
    """
    Extract exact verbatim metaphor spans from the original sentence.

    Returns (verified_spans, raw_log).
    """
    if not metaphors:
        return [], {"agent": "3_span_extractor", "skipped": True}

    metaphors_summary = json.dumps(
        [{"expression": m["expression"], "source_domain": m.get("source_domain", ""),
          "target_domain": m.get("target_domain", "")} for m in metaphors],
        indent=2
    )

    user_msg = SPAN_EXTRACTOR_USER.format(
        sentence=sentence,
        metaphors_json=metaphors_summary
    )

    response = await client.responses.create(
        model=MODEL,
        input=user_msg,
        instructions=SPAN_EXTRACTOR_SYSTEM,
    )

    output_text = response.output_text.strip()
    raw_log = {
        "agent": "3_span_extractor",
        "response_id": response.id,
        "input": user_msg,
        "instructions": SPAN_EXTRACTOR_SYSTEM,
        "output": output_text,
        "usage": response.usage.model_dump() if response.usage else {},
    }

    try:
        result = _parse_json(output_text)
        raw_spans = result.get("spans", [])
    except (json.JSONDecodeError, ValueError):
        raw_spans = [{"span": m["expression"]} for m in metaphors]

    # Verify each span is actually a substring of the original sentence
    verified_spans = []
    for item in raw_spans:
        span = item.get("span", "")
        if span and span in sentence:
            verified_spans.append(span)
        else:
            span_lower = span.lower()
            sent_lower = sentence.lower()
            idx = sent_lower.find(span_lower)
            if idx != -1:
                verified_spans.append(sentence[idx:idx + len(span)])
            else:
                expr = item.get("expression", span)
                if expr in sentence:
                    verified_spans.append(expr)

    raw_log["verified_spans"] = verified_spans
    return verified_spans, raw_log


def _parse_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
