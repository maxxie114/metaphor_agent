"""Agent 4: Verifier — independent second opinion on proposed metaphor spans."""

import json
from openai import AsyncOpenAI
from prompts.templates import VERIFIER_SYSTEM, VERIFIER_USER
from config import MODEL, REASONING_EFFORT


async def verify_spans(client: AsyncOpenAI, sentence: str, spans: list[str]) -> tuple[list[str], dict]:
    """
    Independently verify proposed metaphor spans.

    Returns (kept_spans, raw_log).
    Strict: only keeps spans explicitly marked keep=True.
    """
    if not spans:
        return [], {"agent": "4_verifier", "skipped": True}

    spans_json = json.dumps([{"span": s} for s in spans], indent=2)

    user_msg = VERIFIER_USER.format(
        sentence=sentence,
        spans_json=spans_json
    )

    response = await client.responses.create(
        model=MODEL,
        reasoning={"effort": REASONING_EFFORT},
        instructions=VERIFIER_SYSTEM,
        input=user_msg,
    )

    output_text = response.output_text.strip()
    raw_log = {
        "agent": "4_verifier",
        "response_id": response.id,
        "input": user_msg,
        "instructions": VERIFIER_SYSTEM,
        "output": output_text,
        "usage": response.usage.model_dump() if response.usage else {},
    }

    try:
        result = _parse_json(output_text)
        verified = result.get("verified", [])
        raw_log["evaluations"] = verified
    except (json.JSONDecodeError, ValueError):
        return spans, raw_log

    # Only keep spans explicitly marked keep=True
    kept = []
    for v in verified:
        if v.get("keep", False):
            kept.append(v["span"])

    return kept, raw_log


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
