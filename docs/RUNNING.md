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
