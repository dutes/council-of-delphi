# Phase 6 local-model routing pilot — corrected v2 protocol

Status: **prepared before any v2 scored calls**. The aborted v1 ten-question
operational run is preserved at
`archives/phase6-local-v1-aborted-2026-09-23/ERRATUM.md` and is not pooled
with this study. No v1 final-answer accuracy was computed or used to select
the v2 sample. The v1 run showed a per-agent skip bug and JSON cut off by the
512-token output cap. The corrected runner uses agent-specific completion
checks; v2 uses a 2048-token cap and explicitly asks for reasoning under
300 characters.

## Question and design

The primary descriptive estimand is paired accuracy, **JEV route minus simple
disagreement route**, on the same first-round local council outputs. Report a
10,000-draw question-bootstrap 95% interval, discordant outcomes, and
worst/best-case missingness bounds. This is an exploratory pilot, not a
powered formal superiority test. Also report the initial majority vote and a
predeclared larger single-model baseline. A promising result needs another
fresh holdout before a confirmatory claim.

## Frozen sample

- 190 previously untouched questions: 93 MMLU-Pro, 20 BBEH Mini, 49 GSM1K,
  28 ARC-Challenge. They are exactly the uncalled tail of the pinned v1
  200-question holdout. The ten questions touched by any v1 call are excluded.
- v1 had zero source-row and exact-text overlap with pilot, challenge, and
  Phases 2/3/3R/4/5, so this untouched subset inherits that property. The
  v2 manifest records its SHA-256, pinned upstream revisions, archived v1
  database SHA-256, and all ten excluded IDs.
- “Fresh” means not previously used in this project's live calls, not
  guaranteed absent from any model's pretraining corpus.

## Models, prompts, and routing

The council has one each of `qwen3:4b`, `gemma3:4b`, and
`phi4-mini:3.8b`. The independent larger single baseline is `qwen3:8b`.
The installed Ollama `/api/tags` digests are locked before preflight and
checked on resume. Local requests go only to `http://127.0.0.1:11434` and
are processed sequentially by model on the single RX 7900 GRE GPU. The
excluded preflight checks valid JSON for all four models, JEV, and positive
GPU residency from `/api/ps`.

All four models receive the same versioned base prompt plus the v2 compact-
reasoning instruction. Temperature 0, fixed question/agent/stage seed,
8192-token context setting, 2048-token generation cap, JSON-schema response,
and model-specific thinking settings are frozen in the draft config. An
answer is rejected if the prompt-token count reaches the context limit;
invalid/truncated JSON is a visible failure, not silently repaired.

Round one is independent: no agent receives peer answers. JEV receives only
the ground-truth-free question, options, and anonymized council positions.
Its model is `jev-1.13.0`. Python routes a second round when JEV reports
weak/none agreement or needs-deliberation >= 0.10. The simple rule routes a
second round when normalized initial answers are not unanimous. If *either*
rule escalates, produce one common peer-reconsideration branch. Both policies
use the same saved branch when escalating; otherwise they use the same
first-round majority vote. The larger single model never sees peer outputs.

The original deterministic vote tie-break, choice-label transport,
source-aware answer scoring, peer-reconsideration wording, and JEV payload
allowlist come from the unchanged Phase 3R core freeze. JEV never writes the
final answer. No target answer is sent to local models or JEV.

## Missingness and operations

- At most two recorded attempts per missing agent/JEV stage. Successful calls
  are retained on resume. A failed JEV judgment leaves the paired question
  incomplete; no simple-rule fallback is substituted.
- More than 5% incomplete questions makes the primary descriptive comparison
  not evaluable. No replacement questions or threshold/prompt tuning after
  looking at outcomes. An optional `--limit` run is operational only; no
  interim accuracy is printed.
- The final analysis remains locked while any incomplete question has an
  allowed attempt remaining. Report local token use, recorded JEV cost, and
  summed per-call latency. The JEV rate is estimated at $0.042 per million
  input tokens; this is not an invoice. Local electricity/hardware costs are
  not priced. Model-major batch timing is not equivalent to live serving.

## Commands after the v2 implementation is validated

With Ollama already running, the four tags pulled, and `TYPESAFE_API_KEY` in
the active PowerShell session:

```powershell
python run_phase6_local_v2.py
python run_phase6_local_v2.py --lock-models
python run_phase6_local_v2.py --preflight
python run_phase6_local_v2.py --execute --limit 10 --max-jev-usd 0.50
python run_phase6_local_v2.py --execute --max-jev-usd 0.50
python scripts/analyze_phase6_local_v2.py
```

The first execution command is a ten-question reliability/timing check; do
not use it to alter the frozen model or routing choices. The database,
progress, and final report have v2-specific paths. Leave the archived v1
evidence intact.
