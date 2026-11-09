# Council of Delphi — Phase 3R Final Preregistration

Freeze ID: `phase3r-final-clean-2026-09-22-v1`  
Status: frozen before any Phase 3R live model call  
Purpose: clean confirmatory rerun of H1a after the Phase 3 v5 audit

## Why a rerun is required

Phase 3 v5 remains preserved, but it is classified as compromised/exploratory. Its
JEV request contained the scored `Question` object, including `correct_answer`, and
its generic exact-text scorer incorrectly rejected many numerically correct answers
with units and BBEH formatting variants. The corrected run does not overwrite or
reinterpret Phase 3 v5 as confirmatory evidence.

## Hypothesis and co-primary comparisons

H1a states that the JEV-mediated Delphi result has higher task accuracy than simpler
baselines. Each live run yields two paired, same-call comparators without making
extra model calls:

1. the deterministic majority vote from the three independent Round-one answers;
2. the Google Round-one member answer, selected before this run because it was the
   strongest single-model baseline in the prior exploratory evidence.

Full directional support requires the lower bound of the question-clustered 95%
bootstrap interval to exceed zero for both comparisons. One comparison meeting the
rule is partial support; neither is no support. Repetitions are clustered within
base question. Exact paired McNemar p-values are descriptive secondary statistics.

## Fresh data

- Dataset: `datasets/phase3r_final_500.jsonl`
- SHA-256: `b4c46614cddcb66cb9f0d5fb9d17abd423e316ebb31d40a183e5bc40f5aa9b3f`
- 500 questions: 250 MMLU-Pro, 100 BBEH Mini, 100 GSM1k, 50 ARC-Challenge
- Fixed selection seed: `20260925`
- No source-row or exact-text overlap with Phase 2, either Phase 3 set, or the
  prepared Phase 4 set
- Public dataset revisions and selection details are pinned in the manifest

## Frozen inference system

- One OpenAI agent: `gpt-4.1-mini-2025-04-14`
- One Anthropic agent: `claude-haiku-4-5-20251001`
- One Google agent: `gemini-3.8-flash`, thinking `LOW`
- JEV: `jev-1.13.0`
- Temperature: `0.0`
- Maximum output tokens: 4096 for every provider
- Maximum rounds: 2; valid quorum: all 3 agents
- Escalate for agreement `weak`/`none` or deliberation score `>= 0.10`
- Three independent stateless API repetitions per base question
- Prompts: agent v3, synthesis v3 (unused here), JEV routing v2

The seed governs selection, opaque run IDs, processing order, and bootstrap draws.
It cannot make hosted APIs deterministic, even at temperature zero.

## Blinding and leakage controls

Round-one agents are concurrent and receive no peer context. JEV receives only:

- question text and choices;
- anonymized positions, answers, confidences, reasoning, evidence, and round number.

JEV does not receive ground truth, question metadata, agent/provider/model identity,
telemetry, or cost. Ground truth is used only by local scoring after inference.

## Scoring

The scorer is frozen as `source-aware-equivalence-v2`:

- multiple choice uses constrained labels mapped locally to option text;
- GSM1k extracts the final numeric value and compares Decimal-equivalent values;
- BBEH uses target-free formatting normalization aligned to its public evaluator;
- all raw outputs and normalized values are retained.

No answer-specific correction or scorer change is permitted after live calls begin.

## Missing data, retries, and stopping

Each HTTP request allows two recorded retries. Each question/repetition allows two
run attempts. Credit/quota exhaustion pauses the run and does not consume a run
attempt. Other failures consume an attempt and remain in SQLite.

The primary analysis is marked not evaluable if more than 2% of the 1,500 paired
runs remain unresolved. Complete-case estimates and worst/best-case missingness
bounds are reported regardless. The first 50 questions are only an operational
spend/reliability checkpoint; their accuracy must not govern continuation.

## Outcomes

- Primary: paired accuracy difference versus vote and Google
- Secondary: wrong-to-right, right-to-wrong, false consensus, escalation rate
- Descriptive: tokens, cost estimate, latency, attempts, provider failures
- Exploratory: Brier score and 10-bin ECE because confidence semantics differ

H1d and H1e are not tested by this protocol. Phase 4 is the separate H1e robustness
experiment and must be refrozen against this corrected core before it is run.

## Commands

```powershell
python run_phase3r.py
python run_phase3r.py --preflight --execute
python run_phase3r.py --limit 50 --execute
python run_phase3r.py --resume EXPERIMENT_ID --db-path phase3r-final-results.sqlite3 --execute
python scripts/analyze_phase3r.py --db phase3r-final-results.sqlite3 --experiment EXPERIMENT_ID
```

The first command is dry validation and makes no API calls. The four-question
preflight uses excluded questions and is not included in the analysis.
