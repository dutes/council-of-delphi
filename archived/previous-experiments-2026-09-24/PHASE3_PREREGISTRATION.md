# Phase 3 v5 Paired Low-Thinking Confirmation

Freeze ID: `phase3-paired-low-labels-2026-09-22-v5`  
Machine configuration: `configs/phase3_paired_low_v5.json`

## Status and claim boundary

Phase 3 v5 is the confirmatory test of the exploratory Delphi signal. It must not be pooled silently with Phase 2 or the v4 feasibility pilot.

The v4 Stage 1 run (`45d25750cf5c`) completed 94 of 100 questions but failed its preregistered operational gate. Six MMLU-Pro questions repeatedly failed because agents had to reproduce typography-heavy option text exactly. Correctly intended choices such as `2000 - 150x` and `-32 ft/s` were rejected when the dataset used Unicode minus signs or LaTeX. V4 is closed as a feasibility pilot and preserved at `archives/phase3-v4-pilot-2026-09-22/` with its code, configuration, database, reports, dataset, and checksums.

V5 addresses only that transport defect. Multiple-choice options receive stable labels `A` through `Z`; provider JSON schemas constrain `answer` to the available labels; code maps the label to the original option without consulting the ground truth. Both the raw label and mapped option text are retained. Free-response handling and objective scoring remain unchanged.

## Confirmation dataset

The 100 v4 pilot questions are quarantined. The new 500-question set contains:

- the 400 v4 rows whose outcomes were never observed;
- 100 new rows drawn from the same pinned revisions;
- replacement counts matched exactly by source and MMLU category or BBEH task;
- zero Phase 2 source-row overlap;
- zero v4-pilot source-row overlap;
- the original 250 MMLU-Pro / 100 BBEH / 100 GSM1k / 50 ARC composition.

Dataset: `datasets/phase3_confirmatory_500_v2.jsonl`  
Manifest: `datasets/phase3_confirmatory_500_v2.manifest.json`  
Selection seed: `20260923`  
Dataset SHA-256: `fbad0ab74a3fcaa7a79d4c912e97583a3e0264c329ef966d6129717185813cbf`

## Primary question and paired design

Does JEV-mediated reconsideration improve accuracy over the majority vote derived from the exact same three Round-one answers?

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

The Round-one vote and single OpenAI baseline are derived locally. They require no additional calls. Synthesis is not run.

## Frozen configuration

- OpenAI: one `gpt-4.1-mini-2025-04-14` agent
- Anthropic: one `claude-haiku-4-5-20251001` agent
- Google: one `gemini-3.8-flash` agent at `LOW` thinking
- JEV: `jev-1.13.0`
- Temperature: `0.0`
- Quorum: all 3 council members
- Escalate when agreement is `weak`/`none` or `needs_deliberation >= 0.10`
- Maximum rounds: 2
- Repetitions: 1
- Seed: `20260923`
- Agent prompt: `agent-v2-choice-labels`
- Synthesis prompt: `synthesis-v2-choice-labels` (not used)
- JEV prompt: `jev-routing-v1`
- Prompt SHA-256: `70379f27465f5f0b1e49d0c3442ef8356a56282eebf40f59c60bb6e40a20f736`
- Experiment implementation SHA-256: `9b8b696741301a32b65f7786839708c8eb13c012ffa6ab7f3e20955425fd47ac`
- Scoring: `exact-equivalence-v1`
- Free-response normalization: `objective-v1`
- Multiple-choice transport: `choice-label-enum-v1`

The runner verifies the dataset, prompt bundle, scoring/normalization versions, and a hash covering the experiment-critical implementation files before permitting execution.

`LOW` thinking differs from Phase 2's default Google behavior. Phase 3 evaluates the complete frozen v5 system; cross-phase accuracy comparisons are contextual, while the within-question Round-one-versus-Delphi comparison is primary.

## Staging and continuation

An excluded preflight validates all four integrations and the labelled multiple-choice path. It is not written to the evaluation database.

Stage 1 is the first 100 deterministically shuffled v5 rows. Continue to 500 only when:

- unresolved questions are below 5%;
- no provider reports exhausted credits;
- actual spend is acceptable;
- no configuration change is required.

Stage 1 accuracy is not a continuation criterion and must not be used to retune the protocol. Any change creates another freeze ID.

## Persistence, reporting, and failures

Each successful question is committed immediately. Raw labels, mapped answers, reasoning, evidence, tokens, latency, retry count, JEV judgments, and failures are stored in SQLite. `--resume` skips successful questions and retries unresolved questions without deleting historical failures.

`reports/phase3/EXPERIMENT_ID/progress.txt` is atomically refreshed after every success or failure. Completed stages create retained snapshot files. Interim reports are observational and cannot justify retuning.

Credit exhaustion pauses immediately after retaining the failed attempt. Ordinary provider or parse failures remain visible and execution continues.

## Outcomes

Primary:

- paired accuracy change: Delphi final minus Round-one vote;
- wrong-to-right and right-to-wrong transitions;
- net corrections.

Secondary:

- cost per net correction;
- latency attributable to routing and Round 2;
- escalation and unresolved-failure rates;
- results by source benchmark;
- provider token usage and recorded cost.

## Commands

Validate without API calls:

```powershell
python run_phase3.py
```

Excluded live preflight:

```powershell
python run_phase3.py --preflight --execute
```

Stage 1 in a new database so it cannot mix with v4:

```powershell
python run_phase3.py --limit 100 --db-path phase3-v5-results.sqlite3 --execute
```

Continue the same experiment after the operational gate passes:

```powershell
python run_phase3.py --resume EXPERIMENT_ID --db-path phase3-v5-results.sqlite3 --execute
```

Paired analysis:

```powershell
python scripts/analyze_delphi_marginal.py --db phase3-v5-results.sqlite3 --experiment EXPERIMENT_ID --dataset datasets/phase3_confirmatory_500_v2.jsonl
```

Rebuild the registered dataset from pinned sources:

```powershell
python scripts/build_phase3_v5_dataset.py
```

## Archived predecessors

- Phase 2 exploratory experiment: `archives/phase2-exploratory-2026-09-22/`
- Phase 3 v4 feasibility pilot: `archives/phase3-v4-pilot-2026-09-22/`
