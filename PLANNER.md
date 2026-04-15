# PLANNER: Agentic Inferential Metaphor Identification System

## Problem Analysis

### The Task
Identify **inferential metaphors** in sentences -- metaphors that use language from one domain to describe another and help the reader reason about **cause, structure, direction, or system-level relationships**. Decorative, emotional, and idiomatic metaphors must be excluded.

### Why the Existing Notebook Solution Performs Poorly

The teammate's notebook (`ECOLE ChatGPT ongoing (1).ipynb`) has several fundamental flaws:

1. **Wrong task framing**: The prompt asks for generic Lakoff/Johnson conceptual metaphors (ANY metaphor), but the task specifically requires only *inferential* metaphors. This leads to massive over-identification (low precision) of decorative and idiomatic metaphors.

2. **Wrong input handling**: Reads a raw text file and splits by regex on sentence boundaries, instead of reading the structured CSV with `slug` and `triplet_id` fields. This loses the metadata needed for the output.

3. **Wrong output format**: Produces JSONL with `{sentence, words, target_domain, source_domain}` but the required output is a CSV with `{slug, triplet_id, metaphor_span, selected, annotator_id}` -- one row per metaphor *span* (a phrase, not a single word).

4. **Single-shot prompting**: One pass with no verification, no self-correction, no chain-of-thought reasoning about *why* something qualifies as inferential vs. decorative.

5. **No examples from the annotation guidelines**: The prompt doesn't include the include/exclude examples from the instructions (e.g., "plummeted" = include, "hit hard" = exclude).

6. **Word-level, not span-level**: Identifies individual words, but the task requires exact phrase spans copied from the text (e.g., "The number of bats has plummeted" not just "plummeted").

---

## Proposed Agentic Architecture

### Overview

Instead of a single LLM call, we build a **multi-agent pipeline** with specialized stages, self-verification, and structured output. The system uses Claude as the backbone model (via the Anthropic API).

```
Input CSV
    |
    v
[Agent 1: Candidate Generator]  -- High recall, identify ALL possible metaphors
    |
    v
[Agent 2: Inferential Filter]   -- Apply inferential criteria, reject decorative/idiomatic
    |
    v
[Agent 3: Span Extractor]       -- Extract exact text spans from original sentence
    |
    v
[Agent 4: Verifier]             -- Independent re-check, resolve disagreements
    |
    v
Output CSV
```

### Agent Descriptions

#### Agent 1: Candidate Generator (High Recall)
- **Goal**: Cast a wide net. For each sentence, identify ALL expressions that could be metaphorical.
- **Strategy**: Process each sentence individually (not in batches) to give full attention.
- **Prompt design**: Ask the model to think step-by-step about each phrase, identifying any non-literal language. Use chain-of-thought reasoning.
- **Output**: List of candidate metaphorical expressions per sentence, with brief reasoning.
- **Design principle**: Favor recall over precision -- the instructions say "high recall is preferred" and "when unsure, include it."

#### Agent 2: Inferential Filter (High Precision)
- **Goal**: For each candidate from Agent 1, determine if it meets the **inferential metaphor** criteria.
- **Criteria check** (from the annotation instructions):
  - Does it use language from one domain to describe another? (cross-domain mapping)
  - Does it support reasoning about cause, structure, direction, or system-level relationships?
  - Does it help the reader infer how something works?
- **Exclusion check**:
  - Is it merely expressive/emotional? (e.g., "a classroom nightmare") -> REJECT
  - Is it a dead/conventional idiom? (e.g., "hit hard", "going after") -> REJECT
  - Is it literal description? (e.g., "the virus spreads quickly") -> REJECT
- **Prompt design**: Include the exact include/exclude examples from the annotation instructions. Ask the model to explicitly reason through the three criteria before making a decision.
- **Output**: Filtered list of confirmed inferential metaphors with reasoning.

#### Agent 3: Span Extractor
- **Goal**: For each confirmed metaphor, extract the **exact phrase span** from the original sentence text.
- **Rules**:
  - The span must be copied character-for-character from `original_sentence`.
  - The span should be the minimal meaningful phrase (not too short like a single word when context matters, not too long like the whole sentence).
  - Verify the span is a substring of the original sentence.
- **Output**: Exact span strings, verified against source text.

#### Agent 4: Verifier (Quality Gate)
- **Goal**: Independent second opinion. Re-read each original sentence and the proposed metaphor spans. Confirm or reject each one.
- **Strategy**: This agent has NOT seen the reasoning from Agents 1-3. It receives only the sentence and proposed spans, and independently evaluates them against the inferential metaphor criteria.
- **Disagreement handling**: If the verifier rejects a span, the span is dropped. If uncertain, it is kept (high recall preference).
- **Output**: Final validated list of metaphor spans.

---

## Implementation Plan

### Step 1: Project Setup
- Create a Python project structure:
  ```
  metaphor_agent/
    main.py              # Orchestrator / pipeline runner
    agents/
      __init__.py
      candidate_generator.py
      inferential_filter.py
      span_extractor.py
      verifier.py
    prompts/
      __init__.py
      templates.py       # All prompt templates
    utils/
      __init__.py
      csv_io.py          # Read input CSV, write output CSV
    config.py            # API keys, model settings, parameters
    requirements.txt
  ```
- Dependencies: `anthropic`, `pandas`, `pydantic` (for structured output validation)

### Step 2: Prompt Engineering
Design prompts for each agent, including:

**Candidate Generator prompt** -- key elements:
- Role: linguistic analyst specializing in metaphor identification
- Task: identify all non-literal language use in the sentence
- Chain-of-thought: for each phrase, ask "is this literal or figurative?"
- Output: JSON list of candidate expressions with brief reasoning
- Few-shot examples from the annotation guide

**Inferential Filter prompt** -- key elements:
- Role: metaphor classification specialist
- Input: the sentence + list of candidate metaphors
- For each candidate, explicitly evaluate:
  1. Cross-domain mapping? (source domain -> target domain)
  2. Supports reasoning about cause/structure/direction/system relationships?
  3. Helps reader infer how something works?
  4. NOT merely emotional/decorative/idiomatic?
- Include the exact examples from instructions:
  - INCLUDE: "plummeted", "top predators", "fishing down the food web", "drives development"
  - EXCLUDE: "going after predators", "classroom nightmare", "hit hard", literal descriptions
- Output: filtered list with include/exclude decision and reasoning

**Span Extractor prompt** -- key elements:
- Given: original sentence + confirmed metaphor concept
- Task: extract the minimal exact substring from the original sentence
- Constraint: output must be a verbatim substring (verified programmatically)

**Verifier prompt** -- key elements:
- Fresh perspective (no prior reasoning visible)
- Given: original sentence + proposed metaphor spans
- Task: for each span, independently assess if it's an inferential metaphor
- Apply the same criteria as the filter but from scratch

### Step 3: Implement the Pipeline
- Read the input CSV using pandas
- For each row (sentence):
  1. Run Candidate Generator -> get candidates
  2. Run Inferential Filter on candidates -> get confirmed metaphors
  3. Run Span Extractor -> get exact spans
  4. Programmatic verification: assert each span is a substring of original_sentence
  5. Run Verifier -> final validation
- Collect all results into output rows

### Step 4: Output Assembly
- For each validated metaphor span, create an output row:
  - `slug`: copied from input
  - `triplet_id`: copied from input
  - `metaphor_span`: the exact span
  - `selected`: (leave empty or mark as needed)
  - `annotator_id`: "agent" or configurable identifier
- If a sentence has no inferential metaphors, produce no rows (per instructions)
- Write to output CSV matching the template format

### Step 5: Cost/Latency Optimization
Since we have 4 agent calls per sentence x 99 sentences = ~396 API calls, we should:
- **Batch where possible**: Agents 1+2 can potentially be combined into a single call with structured output to reduce to 2 calls per sentence
- **Parallel processing**: Process multiple sentences concurrently (async API calls)
- **Caching**: Cache intermediate results so re-runs don't repeat completed work
- **Model selection**: Use Claude Sonnet for Agents 1/3 (simpler tasks), Claude Opus for Agent 2/4 (nuanced reasoning)

### Step 6: Evaluation & Iteration
- Compare agent output against any available human annotations
- Analyze common error patterns (false positives, false negatives)
- Tune prompts based on error analysis
- Consider adding a few-shot calibration step using a small set of human-annotated examples

---

## Key Design Decisions

### Why multi-agent instead of a better single prompt?
1. **Separation of concerns**: Recall-focused generation vs precision-focused filtering are conflicting objectives that work better as separate steps.
2. **Debuggability**: When the system makes an error, we can trace which agent failed and why.
3. **Independent verification**: The Verifier agent provides a fresh perspective, catching errors that propagate through the earlier stages.
4. **Iterability**: Each agent's prompt can be tuned independently without affecting others.

### Why per-sentence processing instead of batching?
- The existing notebook batches 25 sentences together, which causes the model to give less attention to each sentence.
- Inferential metaphor identification requires careful, nuanced reasoning about each sentence's content and domain.
- Per-sentence processing ensures maximum attention and reasoning depth.
- The cost increase is manageable for 99 sentences.

### Why exact span extraction as a separate step?
- The annotation instructions emphasize: "Copy the phrase exactly as written. Do not paraphrase."
- Making span extraction explicit (and programmatically verified) prevents the common LLM failure mode of paraphrasing or slightly altering the source text.

### Why Claude over GPT for the agentic system?
- The existing GPT-5 solution underperformed. Using a different model family provides a different perspective on the task.
- Claude's extended thinking and chain-of-thought capabilities are well-suited for the nuanced reasoning required for inferential metaphor classification.
- The Anthropic SDK supports structured outputs and tool use, enabling cleaner agent interfaces.

---

## Potential Enhancements (Future Work)

1. **Human-in-the-loop**: For ambiguous cases (where the Verifier is uncertain), surface them for human review instead of auto-including.
2. **Context window**: Include surrounding sentences from the original article (via the `slug` grouping) to provide topical context for metaphor identification.
3. **Domain knowledge retrieval**: Use RAG to retrieve relevant linguistic resources about common inferential metaphor patterns in specific domains (science, politics, etc.).
4. **Calibration set**: Use a small set of expert-annotated sentences to calibrate the system before running on the full batch.
5. **Ensemble approach**: Run the pipeline with multiple models and take the intersection/union based on recall/precision requirements.

---

## Estimated API Cost

For 99 sentences with the 4-agent pipeline:
- Agent 1 (Candidate Generator): ~99 calls, ~500 input + 300 output tokens each = ~80K tokens
- Agent 2 (Inferential Filter): ~99 calls, ~800 input + 400 output tokens each = ~120K tokens
- Agent 3 (Span Extractor): ~99 calls, ~400 input + 100 output tokens each = ~50K tokens
- Agent 4 (Verifier): ~99 calls, ~600 input + 200 output tokens each = ~80K tokens
- **Total**: ~330K tokens (~$2-5 depending on model mix)

With optimization (combining Agents 1+2, skipping Agent 3 for clear cases): ~200K tokens (~$1-3)

---

## Implementation Order

1. **[Step 1]** Set up project structure and CSV I/O utilities
2. **[Step 2]** Implement and test Agent 1 (Candidate Generator) on 5 sample sentences
3. **[Step 3]** Implement and test Agent 2 (Inferential Filter) on Agent 1's output
4. **[Step 4]** Implement Agent 3 (Span Extractor) with programmatic substring verification
5. **[Step 5]** Implement Agent 4 (Verifier)
6. **[Step 6]** Wire up the full pipeline orchestrator in main.py
7. **[Step 7]** Run on full dataset, inspect results, tune prompts
8. **[Step 8]** Add async parallelism and caching for efficiency
