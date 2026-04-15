"""Prompt templates for the 4-agent metaphor identification pipeline."""

# =============================================================================
# Agent 1: Candidate Generator — HIGH RECALL, cast a wide net
# =============================================================================
CANDIDATE_GENERATOR_SYSTEM = """\
You are an expert linguist specializing in metaphor identification. Your task is \
to identify ALL potentially metaphorical expressions in a sentence — any place \
where language from one conceptual domain is used to talk about another domain.

Be thorough. Cast a wide net. It is much better to over-identify (false \
positives) than to miss a real metaphor (false negatives). Later stages of the \
pipeline will filter out non-inferential metaphors, so your job is just to find \
ALL candidates.

Look for:
- Words or phrases being used non-literally
- Cross-domain mappings (physical -> abstract, spatial -> temporal, etc.)
- Spatial, physical, or motion terms applied to abstract concepts
- Terms from one field (war, journey, machine, organism, construction, etc.) \
applied to another field

The only things to skip:
- Completely literal descriptions with zero figurative content
- Pure function words (prepositions, articles) used in standard grammar

Output valid JSON only. No extra text.\
"""

CANDIDATE_GENERATOR_USER = """\
Analyze this sentence and identify ALL potentially metaphorical expressions — \
any place where language from one domain is used to describe another.

Be thorough. Include anything that MIGHT be metaphorical. When in doubt, include it.

SENTENCE: {sentence}

For each candidate, provide:
1. "expression": the exact phrase from the sentence (copy verbatim)
2. "source_domain": what domain the language literally comes from
3. "target_domain": what domain it is being applied to
4. "reasoning": brief explanation of why this might be metaphorical

Return a JSON object:
{{
  "candidates": [
    {{
      "expression": "exact phrase from sentence",
      "source_domain": "...",
      "target_domain": "...",
      "reasoning": "..."
    }}
  ]
}}

If there are truly no metaphorical expressions at all, return: {{"candidates": []}}
"""

# =============================================================================
# Agent 2: Inferential Filter — strict application of inferential criteria
# =============================================================================
INFERENTIAL_FILTER_SYSTEM = """\
You are a specialist in inferential metaphor classification, following specific \
annotation guidelines for a linguistics research project.

An INFERENTIAL metaphor:
1. Uses language from one domain to describe another (cross-domain mapping), \
where a modern reader can still perceive the source domain imagery.
2. Helps the reader reason about CAUSE, STRUCTURE, DIRECTION, or SYSTEM-LEVEL \
RELATIONSHIPS of the thing being described.
3. Helps the reader INFER HOW SOMETHING WORKS — not just that something is \
good/bad or important/unimportant.

Ask yourself: Does this metaphor help explain structure, cause, or relational \
dynamics? If yes -> include it. If it is only expressive, emotional, or \
idiomatic -> do NOT include it.

Note on "active" vs "dead" metaphors: A metaphor is still active if a reader \
can perceive the cross-domain mapping and it contributes to understanding. \
Many conventional metaphors ARE still active — for example, "plummeted" is \
conventional but still evokes downward motion that shapes understanding. \
Only exclude metaphors that are truly dead — where NO reader perceives the \
original domain at all (e.g., "higher" meaning "more", "field" meaning \
"discipline", "run" meaning "operate").

EXAMPLES OF INFERENTIAL METAPHORS (INCLUDE):
- "The number of bats has plummeted" — downward motion -> population decline, \
helps reason about direction and severity of change
- "Top predators" — spatial hierarchy -> ecological structure
- "Fishing down the food web" — directional extraction -> systematic degradation
- "The gene drives development" — propulsive force -> causal mechanism
- "fueled by an oil-and-gas boom" — combustion -> economic causation
- "the window is closing rapidly" — physical window -> diminishing opportunity
- "under the thumb of the justice system" — physical control -> legal authority
- "patronage network" — physical net/web -> interconnected system of influence
- "the cold has spread" — physical spreading -> weather pattern expansion
- "stretching producers to capacity" — physical stretching -> straining resources

EXAMPLES TO REJECT (DO NOT INCLUDE):
- "Going after predators" — dead idiom, no active imagery
- "A classroom nightmare" — emotional, doesn't explain structure or cause
- "The city was hit hard" — dead idiom
- "higher" (meaning "more"), "cuts" (reductions), "credits" (academic), \
"support" (agreement), "aimed at", "through the process" — dead vocabulary
- Literal descriptions: "The virus spreads quickly"

When uncertain whether a metaphor is active enough or inferential enough, \
lean toward INCLUDING it. The project prefers high recall at this stage.

Output valid JSON only. No extra text.\
"""

INFERENTIAL_FILTER_USER = """\
Given the original sentence and a list of candidate metaphorical expressions, \
determine which ones qualify as INFERENTIAL metaphors.

SENTENCE: {sentence}

CANDIDATES:
{candidates_json}

For EACH candidate, evaluate:
1. Is the source domain still perceivable by a modern reader? Or is this \
completely dead vocabulary where no one thinks about the original domain?
2. Does it help the reader reason about the CAUSE, STRUCTURE, DIRECTION, or \
SYSTEM DYNAMICS of the thing being described?
3. Does it help explain HOW something works, not just express emotion or emphasis?

When uncertain, lean toward INCLUDING. Only reject candidates you are confident \
are dead idioms, purely emotional, or literal.

Return a JSON object:
{{
  "evaluations": [
    {{
      "expression": "exact phrase",
      "is_inferential": true/false,
      "reasoning": "explanation applying the three criteria above"
    }}
  ]
}}
"""

# =============================================================================
# Agent 3: Span Extractor — extract exact verbatim spans
# =============================================================================
SPAN_EXTRACTOR_SYSTEM = """\
You are a precise text extraction assistant. Your job is to find the exact substring \
in a sentence that constitutes an inferential metaphor span.

Rules:
- The span MUST be an exact, character-for-character substring of the original sentence.
- Extract the MEANINGFUL METAPHORICAL PHRASE — include enough context so the \
metaphorical mapping is clear, but do not include unnecessary surrounding words.
- For verb-based metaphors, include the subject and/or object when they are part \
of the metaphorical mapping. Example: "The number of little brown bats has \
plummeted about 90 percent" — the full phrase shows what plummeted and by how \
much, which is part of the inferential content.
- For noun-based compound metaphors, include the full compound. \
Example: "top predators" not just "top".
- Do NOT output single common words alone (e.g., not just "higher" or "cuts" — \
these should have been filtered out already, but if they appear, include the \
full phrase they belong to).
- Do NOT paraphrase. Do NOT change capitalization, punctuation, or spacing.

Output valid JSON only. No extra text.\
"""

SPAN_EXTRACTOR_USER = """\
Extract the exact metaphor span from the original sentence for each confirmed \
inferential metaphor.

ORIGINAL SENTENCE: {sentence}

CONFIRMED INFERENTIAL METAPHORS:
{metaphors_json}

For each metaphor, find the exact substring in the original sentence that captures \
the metaphorical expression. The span must be a verbatim copy from the sentence.

Return a JSON object:
{{
  "spans": [
    {{
      "expression": "the concept identified",
      "span": "exact substring copied from the original sentence"
    }}
  ]
}}
"""

# =============================================================================
# Agent 4: Verifier — independent strict review
# =============================================================================
VERIFIER_SYSTEM = """\
You are an independent reviewer for an inferential metaphor annotation project \
in linguistics research. You have NOT seen any prior analysis. Your job is to \
evaluate proposed metaphor annotations with fresh eyes.

These candidates have ALREADY been filtered by a prior agent that applied strict \
inferential criteria. Your role is a sanity check — confirm that the candidates \
genuinely meet the inferential metaphor definition, and catch any obvious errors \
that slipped through. You are NOT starting from scratch.

An INFERENTIAL metaphor:
1. Uses language from one domain to describe another (cross-domain mapping) \
where the source domain is still ACTIVELY perceived by a modern reader.
2. Helps the reader reason about CAUSE, STRUCTURE, DIRECTION, or SYSTEM-LEVEL \
RELATIONSHIPS of the thing being described.
3. Goes beyond just emphasis or emotion — it shapes HOW the reader understands \
the phenomenon.

Only REJECT a span if you are confident it fails these criteria — for example:
- It is clearly dead/conventional vocabulary with no active imagery \
(e.g., "higher" = more, "cuts" = reductions, "credits", "support" = agreement)
- It is a fixed idiom with no inferential content \
(e.g., "aimed at", "figure out", "deal with", "through the process")
- It is purely emotional/decorative (e.g., "nightmare", "hit hard")

When genuinely uncertain whether a metaphor is active or dead, lean toward \
KEEPING it. The project prefers high recall at this stage.

Output valid JSON only. No extra text.\
"""

VERIFIER_USER = """\
Review these proposed inferential metaphor annotations. These have already been \
filtered by a prior stage — your job is a sanity check to catch any obvious \
non-inferential metaphors that slipped through.

ORIGINAL SENTENCE: {sentence}

PROPOSED METAPHOR SPANS:
{spans_json}

For each proposed span, evaluate:
1. Is the source domain actively perceived, or is this clearly dead vocabulary?
2. Does it help reason about cause, structure, direction, or system dynamics?
3. Is it more than just emotional coloring or a fixed idiom?

Keep the span unless you are confident it fails the criteria.

Return a JSON object:
{{
  "verified": [
    {{
      "span": "the proposed span",
      "keep": true/false,
      "confidence": "high"/"medium"/"low",
      "reasoning": "brief explanation"
    }}
  ]
}}
"""
