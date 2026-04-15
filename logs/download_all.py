#!/usr/bin/env python3
"""
Download all OpenAI Response API logs for a given time range.
Handles pagination automatically using the `after` cursor.

Usage:
    python download_all.py
"""

import json
import os
import requests
import time

# --- Configuration: set these as environment variables ---
# OPENAI_SESS_TOKEN: the "sess-..." token from a logged-in browser session
# OPENAI_ORG_ID: the "org-..." identifier
# OPENAI_PROJECT_ID: the "proj_..." identifier
AUTH_TOKEN = os.environ.get("OPENAI_SESS_TOKEN", "")
ORG_ID = os.environ.get("OPENAI_ORG_ID", "")
PROJECT_ID = os.environ.get("OPENAI_PROJECT_ID", "")

if not AUTH_TOKEN:
    raise SystemExit("Set OPENAI_SESS_TOKEN environment variable")

CREATED_AFTER = 1776150000
CREATED_BEFORE = 1776236399

# Optional: filter by model (set to None to skip)
MODEL_FILTER = "gpt-5.4-2026-03-05"

OUTPUT_FILE = "responses_export.json"

# --- Headers ---
HEADERS = {
    "accept": "*/*",
    "authorization": f"Bearer {AUTH_TOKEN}",
    "openai-beta": "responses=v1",
    "openai-organization": ORG_ID,
    "openai-project": PROJECT_ID,
    "origin": "https://platform.openai.com",
    "referer": "https://platform.openai.com/",
}

BASE_URL = "https://api.openai.com/v1/responses"


def fetch_page(after: str | None = None) -> dict:
    """Fetch one page of responses."""
    params = {
        "created_after": CREATED_AFTER,
        "created_before": CREATED_BEFORE,
        "include[]": "message.input_image.image_url",
        "input_item_limit": 256,
        "output_item_limit": 256,
    }
    if MODEL_FILTER:
        params["model"] = MODEL_FILTER
    if after:
        params["after"] = after

    resp = requests.get(BASE_URL, headers=HEADERS, params=params)
    resp.raise_for_status()
    return resp.json()


def main():
    all_responses = []
    after = None
    page = 0

    while True:
        page += 1
        result = fetch_page(after=after)

        batch = result.get("data", [])
        total = result.get("total", "?")
        all_responses.extend(batch)

        print(f"Page {page}: fetched {len(batch)} responses "
              f"({len(all_responses)}/{total} total)")

        if not result.get("has_more", False):
            break

        after = result.get("last_id")
        if not after:
            break

        # Small delay to be polite
        time.sleep(0.5)

    # Write all responses to a single JSON file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_responses, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Saved {len(all_responses)} responses to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
