# Agentic Inferential Metaphor Identification

An agent-based pipeline for identifying **inferential metaphors** in text, built for the ECOLE lab's research on metaphor and inferential meaning in text simplification.

## Background

This project improves on a prior single-shot GPT solution that underperformed on the task. Instead of one LLM call, this system uses a **4-agent pipeline** where each agent has a focused role, and sentences are processed in parallel with full reasoning logs saved locally.

An **inferential metaphor** (per the annotation instructions):
- Uses language from one domain to describe another
- Supports reasoning about cause, structure, direction, or system-level relationships
- Helps the reader infer how something works

Decorative, emotional, and dead/idiomatic metaphors are excluded.

## Architecture

```
Input CSV (slug, triplet_id, original_sentence)
    |
    v
[Agent 1: Candidate Generator]  -- High recall, find all possible metaphors
    |
    v
[Agent 2: Inferential Filter]    -- Apply inferential criteria, reject dead/decorative
    |
    v
[Agent 3: Span Extractor]        -- Extract exact verbatim text spans
    |
    v
[Agent 4: Verifier]              -- Independent sanity check
    |
    v
[Dedup Pass]                     -- Remove overlapping/nested spans
    |
    v
Output CSV
```

All 100 sentences run in parallel via `asyncio.gather()` with a semaphore throttle.

## Project Structure

```
metaphor_agent/
├── main.py                          # Async pipeline orchestrator
├── config.py                        # Model, API key, file paths
├── requirements.txt                 # openai, pandas, python-dotenv
├── .env                             # OPENAI_API_KEY (not committed)
├── PLANNER.md                       # Design document
├── agents/
│   ├── candidate_generator.py       # Agent 1
│   ├── inferential_filter.py        # Agent 2
│   ├── span_extractor.py            # Agent 3
│   └── verifier.py                  # Agent 4
├── prompts/
│   └── templates.py                 # All prompt templates
├── utils/
│   ├── csv_io.py                    # Read/write CSV
│   ├── dedup.py                     # Span deduplication
│   └── dedupe_csv.py                # Standalone dedup script
├── logs/
│   ├── download_all.py              # Download OpenAI Responses API logs
│   ├── json_to_csv.py               # Convert API logs to CSV
│   ├── log_to_csv.py                # Convert console log to CSV
│   ├── run_exp*.log                 # Experiment run logs
│   ├── exp*_output*.csv             # Experiment outputs
│   └── debug_log_*.jsonl            # Per-run agent reasoning logs
└── metaphor_selection_batch_01_1A_input.csv
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env and set OPENAI_API_KEY
```

## Usage

Run the full pipeline on all 100 sentences in parallel:

```bash
python3 main.py
```

Custom input/output:

```bash
python3 main.py --input custom_input.csv --output custom_output.csv --annotator ag
```

Dedupe an existing output CSV (no API calls):

```bash
python3 utils/dedupe_csv.py logs/exp4_output.csv logs/exp4_output_deduped.csv
```

## Debug Logs

Every run saves a `logs/debug_log_<timestamp>.jsonl` file with the full input, output, and reasoning from each agent on each sentence. Each line is a JSON object with fields:
- `idx`, `slug`, `triplet_id`, `sentence`
- `agents`: full input/output/usage for each of the 4 agents
- `result`: final verified metaphor spans

No need to go to the OpenAI dashboard — everything is captured locally.

## Experiment Log

| Experiment | Spans | Notes |
|---|---|---|
| exp1 | 145 | Too permissive — kept dead metaphors ("higher", "cuts", "credits") |
| exp2 | 1 | Too strict — Agent 1 filtered too aggressively |
| exp3 | 24 | Agent 2 + Verifier too strict |
| exp4 | 110 | Good quality, but overlapping spans |
| **exp4 deduped** | **90** | **Best result** |

Each experiment has its full output, console log, and debug JSONL saved under `logs/`.

## Key Design Decisions

1. **Separation of concerns**: Recall (Agent 1) and precision (Agent 2) are conflicting objectives that work better as separate agents.
2. **Independent verification**: Agent 4 has not seen prior reasoning — it provides a fresh sanity check.
3. **Full parallelism**: All 100 sentences run concurrently. Runtime dropped from ~2.5 hours (sequential) to ~5 minutes.
4. **Dedup as post-processing**: Nested/overlapping spans from the same metaphor are collapsed to the maximal span locally, no extra API calls.
5. **Substring verification**: Span extraction is programmatically checked against the original sentence to prevent paraphrasing.

## Model

The pipeline uses OpenAI's Responses API with `reasoning.effort = "high"` for Agents 1, 2, and 4 (reasoning-heavy tasks) and default effort for Agent 3 (simple extraction).
