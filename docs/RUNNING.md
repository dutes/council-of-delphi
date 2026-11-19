# Running the study

This workspace contains one active clean-slate experiment. It tests whether
accuracy changes as a question moves through:

```text
first answers
  -> each model's three-sample crowd
  -> equal cross-model majority
  -> JEV selection
  -> optional JEV-triggered reconsideration and final arbitration
```

The council uses OpenAI `gpt-4.1-mini-2025-04-14`, Anthropic
`claude-haiku-4-5-20251001`, and Mistral `ministral-14b-2512`. Hidden reasoning is
disabled or rejected for all three. JEV is also evaluated alone so that direct
JEV capability is not confused with an arbitration benefit.

The primary comparison is full JEV-controlled Delphi accuracy versus the simple
majority of the three provider-level crowd positions. See
[`docs/PROTOCOL.md`](docs/PROTOCOL.md) for all conditions, estimands, tie rules,
and safeguards.

Earlier experiments remain quarantined under
[`archived/previous-experiments-2026-09-24`](archived/previous-experiments-2026-09-24/QUARANTINE.md).
Nothing there is imported by the active study.

## Setup and validation

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
python run_study.py
```

`python run_study.py` validates the dataset and implementation freeze without
making network calls or writing results.

Execution requires `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `MISTRAL_API_KEY`, and
`TYPESAFE_API_KEY`. The runner loads either ordinary `KEY=value` entries or
PowerShell-style `$env:KEY='value'` entries from a root `.env` file. Do not
commit secrets. An unscored API-contract preflight
and the scored run are explicit operations:

```powershell
python run_study.py --preflight
python run_study.py --execute --max-recorded-cost-usd 15
python analyze_study.py
```

The runner records operational progress but never interim accuracy.

## The follow-up study

The follow-up is set out in [`FOLLOWUP_PROTOCOL.md`](FOLLOWUP_PROTOCOL.md). Its
code lives in `followup_study/` plus the scripts below, and reuses the first
study's model and JEV calls from `arbiter_study/` without changing them, so the
first study's freeze still validates. Run every step from the repo root with the
virtual environment active.

**1. See which models your keys can reach.** Free, read-only:

```powershell
python tools/list_models.py
```

The candidates for each provider are in `"candidates"` in
`config/followup_v1.json`, with their list prices per million input and output
tokens. Check the prices are still current before calibrating. Models that can
reason are called with reasoning switched off, and any response that reasons
anyway fails (see the protocol's "Reasoning switched off").

**2. Build the questions.** Needs internet access to Hugging Face and the
quarantined archive in `archived/`, which it uses to exclude every question
used before. It never overwrites an existing file:

```powershell
python build_followup_dataset.py
```

**3. Check every model answers.** Unscored, one synthetic question each:

```powershell
python run_followup.py --preflight
python run_followup_calibration.py --preflight
```

**4. Calibrate.** Runs the 60 calibration questions through JEV and every
candidate, picks the matched council by the protocol's rule, and estimates the
main run's cost. Resumable:

```powershell
python run_followup_calibration.py --execute
```

**5. Freeze.** Fills in the matched council, the hashes and the protocol's
freeze record, and marks the study frozen. Pick the cost cap from the estimate
in step 4. Commit and push straight afterwards:

```powershell
python tools/freeze_followup.py --cost-cap 30
python run_followup.py
```

**6. Run, then analyse.** The run is resumable and never shows interim
accuracy. The analysis refuses to run until every question is finished:

```powershell
python run_followup.py --execute --limit 5    # optional smoke test
python run_followup.py --execute
python run_followup.py --status               # progress and spend, never accuracy
python analyze_followup.py
```

**If it stops.** Run `--execute` again. Finished questions are skipped and
unfinished ones carry on from the step they stopped on, so only the missing
calls are made. If the cost cap paused it, raise the cap with a reason. The
amendment is recorded in the results database and printed in the analysis
report:

```powershell
python run_followup.py --execute --raise-cap 40 --reason "Calibration estimate was low"
```
