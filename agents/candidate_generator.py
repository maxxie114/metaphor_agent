"""Agent 1: Candidate Generator — identify all potentially metaphorical expressions."""

import json
from openai import AsyncOpenAI
from prompts.templates import CANDIDATE_GENERATOR_SYSTEM, CANDIDATE_GENERATOR_USER
from config import MODEL, REASONING_EFFORT


async def generate_candidates(client: AsyncOpenAI, sentence: str) -> tuple[list[dict], dict]:
    """
    Identify all candidate metaphorical expressions in a sentence.

    Returns (candidates, raw_log) where:
    - candidates: list of dicts with keys: expression, source_domain, target_domain, reasoning
    - raw_log: dict with response_id, input, output, usage for debug logging
    """
    user_msg = CANDIDATE_GENERATOR_USER.format(sentence=sentence)

    response = await client.responses.create(
        model=MODEL,
        reasoning={"effort": REASONING_EFFORT},
        instructions=CANDIDATE_GENERATOR_SYSTEM,
        input=user_msg,
    )

    output_text = response.output_text.strip()
    raw_log = {
        "agent": "1_candidate_generator",
        "response_id": response.id,
        "input": user_msg,
        "instructions": CANDIDATE_GENERATOR_SYSTEM,
        "output": output_text,
        "usage": response.usage.model_dump() if response.usage else {},
    }

    try:
        result = json.loads(output_text)
        return result.get("candidates", []), raw_log
    except json.JSONDecodeError:
        text = output_text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        try:
            result = json.loads(text)
            raw_log["output_parsed"] = text
            return result.get("candidates", []), raw_log
        except json.JSONDecodeError:
            return [], raw_log
