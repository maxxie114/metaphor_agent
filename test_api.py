#!/usr/bin/env python3
"""Minimal test to verify the OpenAI API key works."""

from openai import OpenAI
from config import OPENAI_API_KEY, MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

try:
    response = client.responses.create(
        model=MODEL,
        input="Say 'ok' and nothing else.",
    )
    print(f"SUCCESS")
    print(f"Model: {response.model}")
    print(f"Output: {response.output_text}")
    print(f"Usage: {response.usage}")
except Exception as e:
    print(f"FAILED: {type(e).__name__}")
    print(f"Error: {e}")
