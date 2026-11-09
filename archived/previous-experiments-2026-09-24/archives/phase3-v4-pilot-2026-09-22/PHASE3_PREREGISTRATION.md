# Phase 3 Paired Low-Thinking Confirmation

Freeze ID: `phase3-paired-low-fresh-2026-09-22-v4`  
Machine configuration: `configs/phase3_paired_low.json`

## Status and claim boundary

Phase 3 is a preregistered confirmation of the Phase 2 exploratory signal. It uses a new configuration, experiment ID, SQLite database, and fresh 500-question holdout. It must never be pooled silently with Phase 2.

The holdout was drawn from the same pinned benchmark revisions and with the same 250/100/100/50 source composition as Phase 2. All 500 Phase 2 source rows were excluded before selection. Automated validation confirms zero overlap by `(source, source_row_index)` and zero exact question-text overlap. The superseded, unexecuted reuse design remains at `configs/phase3_paired_minimal_reuse_v1.json` as protocol history.

The excluded v2 preflight discovered that `gemini-3.8-flash` rejects the frozen `MINIMAL` thinking level. No evaluation question was run or written to the Phase 3 database. V2 is retained at `configs/phase3_paired_minimal_fresh_v2_failed_preflight.json`. The unexecuted v3 proposal using `gemini-3.6-flash` at `MINIMAL` is retained at `configs/phase3_paired_minimal.json`. Before any evaluation run, v4 restored the Phase 2 Google model and selected its lowest supported level, `LOW`, improving cross-phase comparability while reducing thinking relative to Phase 2's default.

## Primary question

Does JEV-mediated reconsideration improve accuracy over the majority vote derived from the exact same three Round-one answers?

The primary comparison is paired within each completed question:

```text
OpenAI + Anthropic + Gemini Round-one answers
                    |
          +---------+---------+
          |                   |
    Majority vote       JEV routing policy
                              |
                       optional Round 2
                              |
                        Delphi final
```

The single OpenAI answer and Round-one vote are derived locally. They do not require separate paid experiments. Synthesis is not part of Phase 3.

## Frozen configuration

- One OpenAI agent: `gpt-4.1-mini-2025-04-14`
- One Anthropic agent: `claude-haiku-4-5-20251001`
- One Google agent: `gemini-3.8-flash`
- Gemini thinking: `LOW`
- JEV: `jev-1.13.0`
- Temperature: `0.0`
- Quorum: all 3 council members
- JEV threshold: `needs_deliberation >= 0.10`, or agreement `weak`/`none`
- Maximum rounds: 2
- Repetitions: 1
- Seed: `20260922`
- Dataset: `datasets/phase3_fresh_500.jsonl`
- Dataset SHA-256: `65bab046a4f465c397faeafa470eefb9b8c06a44766a03a8e62c08896c1bbff1`
- Prompt SHA-256: `0d3e3bd01aeabf4cd45f706bc200341a9683acf47f688259d513b90318f53a47`

`LOW` thinking is a material configuration change from Phase 2's default behavior. Phase 3 evaluates the complete system with that setting; it does not assume Gemini quality is unchanged.

## Staging and continuation

An excluded preflight question verifies all four live integrations. It is never written to the evaluation database.

Stage 1 consists of the first 100 rows of the deterministically shuffled fresh holdout. It is an operational checkpoint only: Stage 1 accuracy must not be used to alter prompts, models, thresholds, scoring, or the continuation decision. Continue to all 500 only when:

- unresolved questions are below 5%;
- no provider is returning credit-exhaustion errors;
- actual provider spend is acceptable;
- no configuration change is required.

If configuration must change, stop and create a new freeze ID. Do not continue the existing experiment under modified settings.

## Resume policy

Every successful question is committed immediately. `--resume EXPERIMENT_ID` skips successful questions and retries only questions without a successful result. Historical failed attempts remain in SQLite. Omitting `--limit` while resuming the Stage 1 experiment extends the same frozen experiment to all 500 questions.

During execution, `reports/phase3/EXPERIMENT_ID/progress.txt` is atomically refreshed after every completed or failed question. It contains the paired outcome, source and provider breakdowns, costs, latency, escalation, failures, and per-question results. A completed 100-question stage also creates `stage-100-complete.txt`; the full run creates `final-500-complete.txt`. These reports are observational and must not be used to retune the frozen protocol during Phase 3.

An HTTP 402 or recognized provider credit/quota exhaustion response pauses the experiment immediately after retaining the failed attempt. No subsequent question is called. After credits are restored, the printed resume command retries that unresolved question and continues. Ordinary malformed answers remain visible failures and do not pause the full experiment.

## Outcomes

Primary:

- paired accuracy change: Delphi final minus Round-one majority vote;
- wrong-to-right count;
- right-to-wrong count;
- net corrections.

Secondary:

- recorded cost per net correction;
- latency added by JEV and Round 2;
- escalation rate;
- unresolved failure rate;
- accuracy by source benchmark;
- Gemini input, candidate-output, and thinking tokens where available.

The existing adapter stores Gemini candidate and thinking tokens together for billing-compatible totals. Separating them in future reporting is desirable but is not required to execute this frozen replication.

## Commands

Validate without API calls:

```powershell
python run_phase3.py
```

Excluded live preflight:

```powershell
python run_phase3.py --preflight --execute
```

Stage 1:

```powershell
python run_phase3.py --limit 100 --db-path phase3-results.sqlite3 --execute
```

The output prints the experiment ID. Continue the same experiment to 500 with:

```powershell
python run_phase3.py --resume EXPERIMENT_ID --db-path phase3-results.sqlite3 --execute
```

If Stage 1 is interrupted, use both `--limit 100` and `--resume EXPERIMENT_ID` to finish only Stage 1.

Paired analysis:

```powershell
python scripts/analyze_delphi_marginal.py --db phase3-results.sqlite3 --experiment EXPERIMENT_ID --dataset datasets/phase3_fresh_500.jsonl
```

## Holdout construction and verification

Rebuild command (not part of experiment execution):

```powershell
python scripts/build_phase3_dataset.py
```

The builder verifies pinned upstream revisions, excludes Phase 2 rows before selection, applies SHA-256 ranking with seed `20260922`, checks the fixed source composition, and refuses to write an overlapping or internally duplicated benchmark. The complete provenance and overlap checks are recorded in `datasets/phase3_fresh_500.manifest.json`.

## Archived predecessor

Phase 2 is preserved at `archives/phase2-exploratory-2026-09-22/`. Its database, exact dataset, configuration, reports, reconstructed run-time source, and hashes are retained as immutable exploratory evidence.
