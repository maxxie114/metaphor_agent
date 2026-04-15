"""Agent 2: Inferential Filter — filter candidates to only inferential metaphors."""

import json
from openai import AsyncOpenAI
from prompts.templates import INFERENTIAL_FILTER_SYSTEM, INFERENTIAL_FILTER_USER
from config import MODEL, REASONING_EFFORT


async def filter_inferential(client: AsyncOpenAI, sentence: str, candidates: list[dict]) -> tuple[list[dict], dict]:
    """
    Filter candidate metaphors to only those that qualify as inferential.

    Returns (filtered_candidates, raw_log).
    """
    if not candidates:
        return [], {"agent": "2_inferential_filter", "skipped": True}

    candidates_summary = json.dumps(
        [{"expression": c["expression"], "source_domain": c.get("source_domain", ""),
          "target_domain": c.get("target_domain", "")} for c in candidates],
        indent=2
    )

    user_msg = INFERENTIAL_FILTER_USER.format(
        sentence=sentence,
        candidates_json=candidates_summary
    )

    response = await client.responses.create(
        model=MODEL,
        reasoning={"effort": REASONING_EFFORT},
        instructions=INFERENTIAL_FILTER_SYSTEM,
        input=user_msg,
    )

    output_text = response.output_text.strip()
    raw_log = {
        "agent": "2_inferential_filter",
        "response_id": response.id,
        "input": user_msg,
        "instructions": INFERENTIAL_FILTER_SYSTEM,
        "output": output_text,
        "usage": response.usage.model_dump() if response.usage else {},
    }

    try:
        result = _parse_json(output_text)
        evaluations = result.get("evaluations", [])
        raw_log["evaluations"] = evaluations
    except (json.JSONDecodeError, ValueError):
        return candidates, raw_log

    kept_expressions = {
        e["expression"] for e in evaluations if e.get("is_inferential", False)
    }

    return [c for c in candidates if c["expression"] in kept_expressions], raw_log


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
