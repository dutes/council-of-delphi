# Phase 2 Frozen Experiment

Freeze ID: `phase2-2026-09-21-v1`  
Freeze date: 21 September 2026  
Machine-readable specification: `configs/phase2_frozen.json`

This document is the human-readable pre-registration for the next Council of Delphi evaluation. The frozen runner verifies the dataset and prompt hashes before making an API call. If either changes, the run stops.

## Research question

On a larger, held-out, objectively scored benchmark, does JEV-mediated reconsideration improve accuracy enough to justify its additional model calls, cost, and latency relative to single-model, majority-vote, and synthesis baselines?

The result may favour or reject Delphi. No Phase 2 result will be used to retune the frozen configuration and then reported as held-out evidence.

## Freeze basis

The configuration is based on experiment `061b6c83ee90` in `challenge-delphi-t010.sqlite3`, which was the successful three-member Delphi run with a 0.10 deliberation threshold. That experiment recorded `random_seed = null`; Phase 2 corrects this before any held-out run by fixing the seed to `20260921`.

## Dataset

File: `datasets/phase2_500.jsonl`  
Version: `phase2-500-v1`  
Questions: 500  
SHA-256: `10fe6680aebbe2a855aa53cdf9b52e0ab62e8de8c002e02ca9d9e70b8f755652`

Composition:

| Source | Questions | Selection |
|---|---:|---|
| MMLU-Pro test | 250 | Equally stratified over retained categories |
| BBEH Mini | 100 | Equally stratified over its 23 tasks |
| GSM1k test | 100 | Deterministic SHA-256-ranked sample |
| ARC-Challenge test | 50 | Deterministic SHA-256-ranked sample |

Sampling uses seed `20260921`. Health and law categories are excluded from MMLU-Pro to preserve the project's original restriction against medically or legally sensitive questions. The final 500 rows are deterministically interleaved. Every row records its source dataset, pinned source revision, split, original row index, and source URL.

The exact source revisions and selection details are in `datasets/phase2_500.manifest.json`. `scripts/build_phase2_dataset.py` can reproduce the file only while those exact revisions remain current; it deliberately fails if an upstream repository changes.

### Why GPQA is absent

The earlier proposed mix included GPQA Diamond. Its official Hugging Face distribution is gated and asks users not to reveal examples publicly. A complete plaintext copy in this project could violate that condition, so no GPQA examples are redistributed. Public MMLU-Pro and ARC-Challenge questions replace that allocation.

This is a custom, documented benchmark mixture—not an official aggregate score. The BBEH portion uses this project's frozen conservative answer normalizer rather than every task-specific official BBEH evaluator, so results must be labelled “Council of Delphi Phase 2,” not an official BBEH score.

## Frozen providers and models

| Role | Count | Provider | Model |
|---|---:|---|---|
| Council member | 1 | OpenAI | `gpt-4.1-mini-2025-04-14` |
| Council member | 1 | Anthropic | `claude-haiku-4-5-20251001` |
| Council member | 1 | Google | `gemini-3.8-flash` |
| Synthesis-only model | 1 | OpenAI | `gpt-4.1-mini-2025-04-14` |
| Delphi judge | 1 per judged question | TypeSafe | `jev-1.13.0` |

The calibration run requested the OpenAI alias `gpt-4.1-mini`; Phase 2 uses its dated `gpt-4.1-mini-2025-04-14` snapshot so OpenAI behaviour cannot move with the alias. The JEV version is pinned to the exact model identifier returned by the calibration run, rather than the mutable `jev-latest` alias. The Anthropic identifier was already dated. The Google identifier is frozen at the exact requested identifier retained by the calibration database because no resolved backend revision was stored. Live availability of pinned identifiers must be verified by the first Phase 2 call; failure is recorded and is not silently replaced.

## Frozen orchestration

- Temperature: `0.0`
- Council size: 3, one member per LLM provider
- Minimum valid council size: 3
- Maximum Delphi rounds: 2
- Escalate if JEV agreement is `weak` or `none`, or `needs_deliberation >= 0.10`
- Final Delphi answer: majority vote over the last completed round
- Majority tie-break: vote count, then mean confidence among supporters, then ascending lexical canonical answer
- Request timeout: 60 seconds
- Retries: at most 2 retries after the initial request, with 0.5-second exponential base delay
- Seed: `20260921`
- Planned repetitions: 3 per strategy

Round-one members run concurrently and receive no peer answers. If Delphi escalates, every member receives the same neutral distribution/conflict summary plus its own prior answer. The exact instruction includes: “Reassess the problem independently. You may retain your original answer. Do not change your answer merely to agree with the other agents.”

## Frozen prompts

Versions: `agent-v1`, `synthesis-v1`, and `jev-routing-v1`  
Canonical prompt-bundle SHA-256: `0d3e3bd01aeabf4cd45f706bc200341a9683acf47f688259d513b90318f53a47`

### Independent agent system prompt

```text
You are an independent reasoning agent in a research experiment.
Return only a JSON object with keys: answer, confidence, reasoning, evidence.
confidence must be a number from 0 to 1. reasoning must be concise. evidence must be a JSON list of strings.
You have no access to other agents' answers and must solve the problem independently.{choice_instruction}
```

For multiple choice, `{choice_instruction}` becomes: ` Your answer must exactly match one of the provided choices.` Otherwise it is empty.

### Reconsideration instruction

```text
A council disagreement was detected. Here is a neutral summary:
{context}

Reassess the problem independently. You may retain your original answer. Do not change your answer merely to agree with the other agents.
```

### Synthesis system prompt

```text
You are a synthesizer, not a voter. Assess the original question and the supplied independent answers.
Return only a JSON object with keys: answer, confidence, reasoning, evidence. confidence is 0 to 1.
For multiple choice, answer must exactly match one listed choice.
```

### JEV routing questions

- Agreement: classify `strong`, `partial`, `weak`, or `none` using the criteria in `council/prompts.py`.
- Needs deliberation: “Would another independent reconsideration round materially improve this council decision?”
- Evidence conflict: “Do council members rely on materially conflicting evidence or assumptions?”
- Minority view material: “Does a minority view raise a material issue the majority may have missed?”

JEV judges and routes only. It does not produce the final answer.

## Frozen scoring and normalization

Scoring version: `exact-equivalence-v1`  
Normalization version: `objective-v1`

Multiple-choice provider output must exactly match a displayed option. For grouping and scoring, text is Unicode NFKC-normalized, case-folded, trimmed, internal whitespace is collapsed, and trailing `. ! , ; :` characters are removed.

Free-response scoring uses the same text rules and also normalizes standalone decimal representations, including comma separators and insignificant trailing zeros. It recognizes only explicitly requested USD, percentage, and kilometres-per-hour aliases. It does not perform symbolic algebra, arbitrary unit conversion, semantic equivalence, or LLM-as-judge scoring.

The strict rule may produce false negatives for semantically equivalent free responses. That limitation is accepted and frozen before evaluation. Raw answers remain available for a separately declared sensitivity analysis, but such an analysis must not replace the primary frozen score.

## Primary comparisons

All four strategies receive the same 500 questions in the same order:

1. Single OpenAI model
2. Three-member majority vote
3. Three-member council plus OpenAI synthesizer
4. Three-member JEV Delphi council

Report accuracy, failures, mean cost, token usage, wall-clock latency, escalation rate, mean agents used, mean rounds, Brier score, and ECE. Confidence is not semantically identical across strategies, so calibration comparisons are descriptive rather than strictly like-for-like.

The most informative accuracy analysis is paired by question: Delphi versus vote, including counts of wrong-to-right and right-to-wrong changes. Cost figures exclude JEV whenever TypeSafe does not return billable cost information; this must be stated with results.

## Commands

Validate the frozen files without API calls:

```powershell
python run_phase2.py
```

Run a one-question connectivity check for all live integrations (this is not a registered Phase 2 result):

```powershell
python run_phase2.py --strategies delphi --repetitions 1 --limit 1 --db-path phase2-smoke.sqlite3 --execute
```

Run the pre-registered full experiment:

```powershell
python run_phase2.py --strategies single vote synthesis delphi --repetitions 3 --db-path phase2-results.sqlite3 --execute
```

The full command represents 6,000 scored question-runs and at least 16,500 paid LLM answer/synthesis calls, plus 1,500 JEV judgments and any escalated second-round calls. Validate provider budgets and rate limits before starting it.
