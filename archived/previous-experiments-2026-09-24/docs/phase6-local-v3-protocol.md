# Phase 6 local-model routing pilot — bounded-output v3

Status: prepared **before any v3 scored calls**. V1 and v2 are separate,
aborted operational studies; see their archived errata. Do not pool their
answers with v3 or treat their six/other partial pairs as study results.

## Why v3 exists

V2 asked for reasoning under 300 characters but four of its first ten
questions still produced open-ended reasoning until the 2048-token output cap.
The same four responses failed on both deterministic attempts. We kept the
original raw errors, did not score incomplete JSON, and stopped v2 at 40%
missingness among attempted questions. On those already-excluded questions,
an exploratory local-only diagnostic with a JSON-schema `maxLength` of 120
for reasoning, an empty evidence array, and a 512-token diagnostic cap
returned complete JSON for all four previously failing model/question pairs.
That diagnostic is engineering evidence, not accuracy evidence.

V3 requests one reason of at most 120 characters. Its per-question JSON
schema also limits reasoning to 120 characters and evidence to an empty
array. The adapter verifies these limits, rejects `done_reason=length`, and
never recovers an answer from truncated JSON. The scored cap is 1024 tokens,
not the diagnostic cap. This changes the information available to JEV and to
peer reconsideration; v3 is not directly comparable to v2 on those outputs.

## Question and sample

The primary descriptive estimand remains paired accuracy, **JEV route minus
simple disagreement route**, on the same first-round local council outputs.
Also report the initial majority vote and predeclared larger local single
model. Use the inherited 10,000-draw question bootstrap interval, discordant
outcomes, and worst/best-case missingness bounds. This is exploratory, not a
powered confirmatory superiority test. Any promising finding needs a fresh
external holdout because the output protocol was developed using failed
questions from this project.

The sample is the 180 never-called questions from the v2 holdout: 84
MMLU-Pro, 20 BBEH Mini, 48 GSM1K, and 28 ARC-Challenge. All ten v1-touched
and ten v2-touched IDs are excluded. Dataset and source revision checksums
are in `datasets/phase6_local_v3_180.manifest.json`. "Fresh" means not used
in this project's live calls, not absent from model pretraining.

## Frozen behaviour

- Council: `qwen3:4b`, `gemma3:4b`, `phi4-mini:3.8b`, one independent member
  each. Larger single baseline: `qwen3:8b`. Installed model digests are
  locked before preflight and checked on resume.
- All four use the same versioned base prompt plus the v3 bounded-output
  instruction. Temperature 0, fixed question/agent/stage seed, 8192-token
  context, 1024-token generation cap, model-specific thinking settings,
  strict JSON schema, and 120-character reasoning limit are fixed.
- First-round calls are independent. JEV sees only a ground-truth-free
  question, options, and anonymized council positions. JEV is
  `jev-1.13.0`. Python escalates for weak/none agreement or deliberation
  score >= 0.10; the simple rule escalates when normalized initial answers
  are not unanimous. If either escalates, one common peer branch is called.
  Both policies reuse exactly that branch. The single model has no peer
  information. JEV never produces a final answer.
- Original choice-label transport, deterministic voting, source-aware
  scoring, peer wording, and JEV allowlist are inherited unchanged from the
  pinned Phase 3R core. Ground truth is never sent to local models or JEV.
- Local calls are sequential in model-major batches on one GPU, so summed
  call latency is only a proxy for deployment latency. Electricity and
  hardware are not priced. JEV cost is estimated from recorded usage, not
  claimed as an invoice.

## Reliability gate and missingness

The excluded preflight uses seven **already-used** questions: the four v2
truncation cases, one v1 GSM1K case, one v1 ARC case, and one Phase 3R BBEH
case. All four local models must return complete bounded JSON on all seven;
GPU residency is checked and one JEV call is validated. None overlaps v3.
This is a hard engineering check, not a representative reliability estimate.

The first ten v3 questions then form an operational gate. Their calls are
part of the eventual v3 study, but no interim accuracy is printed or used to
change settings. The full 180-question command refuses to run until **all
ten** are fully paired. At most two recorded attempts are allowed per missing
agent or JEV stage. Successful calls persist on resume. If the ten-question
gate fails after permitted retries, preserve v3 and stop; do not loosen it.
The complete study is descriptively evaluable only if at most 5% of 180
questions remain unresolved. Missing answers are never silently replaced.
The final analyzer refuses to run while an incomplete question still has an
allowed attempt remaining.

## Commands

With Ollama running, the four local model tags installed, and
`TYPESAFE_API_KEY` set in the active PowerShell session:

```powershell
python run_phase6_local_v3.py
python run_phase6_local_v3.py --lock-models
python run_phase6_local_v3.py --preflight
python run_phase6_local_v3.py --execute --limit 10 --max-jev-usd 0.50
python run_phase6_local_v3.py --execute --max-jev-usd 0.50
python scripts/analyze_phase6_local_v3.py
```

If the operational check reports incomplete pairs, resume the identical
`--limit 10` command once before considering the full run. Do not change
models, prompts, output caps, sample, or thresholds after locking. The
database and reports use v3-specific paths.
