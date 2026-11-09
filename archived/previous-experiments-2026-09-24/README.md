# Council of Delphi

![Council of Delphi experiment infographic](docs/council-of-delphi-infographic.png)

Council of Delphi is a deliberately small Python research harness for comparing a single LLM, majority voting, LLM synthesis, and JEV-mediated Delphi-style reconsideration on the same labelled dataset. It is built to make negative results visible: the Delphi strategy can be slower, costlier, less calibrated, or less accurate than its baselines, and the stored data will show that.

This is a v0.1 experiment framework, not a product or agent platform.

## Current study: clean-slate non-reasoning council

The current paper pipeline starts at
[`docs/clean-slate-preregistration.md`](docs/clean-slate-preregistration.md).
It uses one comparably positioned, capable throughput model per provider:
GPT-4.1 Mini, Claude Haiku 4.5, and Gemini 2.5 Flash. Provider-side hidden or
extended thinking is disabled and enforced fail-closed. Earlier phases and the
earlier manuscript are retained only as an audit archive; their results and
prose are not inputs to the new paper.

After exporting all four API keys, validate the freeze and run the unscored
provider preflight:

```powershell
python run_clean_slate_study.py
python run_clean_slate_study.py --preflight
```

The scored, resumable execution is capped at $15 of recorded token cost:

```powershell
python run_clean_slate_study.py --execute --max-recorded-cost-usd 15
python scripts/analyze_clean_slate_study.py
```

Progress is written without interim accuracy to
`reports/clean-slate/progress.txt`. The new manuscript will be created from the
locked clean-slate analysis only after the run is complete.

## Strategies

- **Single model (`single`)** asks one configured agent once.
- **Majority vote (`vote`)** runs independent council members concurrently. Ties are resolved by mean confidence and then ascending lexical order.
- **LLM synthesis (`synthesis`)** runs the same independent council, then gives every answer, confidence, reason, and evidence item to a separately identified synthesizer.
- **JEV Delphi (`delphi`)** sends an allowlisted, provider-anonymized first-round state to JEV for a structured routing judgment. Ground truth and metadata are excluded. Python code applies a deterministic threshold. If escalation is warranted, council members receive a neutral disagreement summary and reconsider once. The last round is finalized by the same deterministic vote.

The confidence attached to a vote result is the mean self-reported confidence of agents supporting the winning answer. Synthesis and single-model confidence come from one model. These are not identical semantics, so cross-strategy Brier/ECE comparisons should be interpreted cautiously.

## Architecture

```text
Dataset
   |
   v
Experiment Runner
   |
   +-- Single LLM
   |
   +-- Majority Vote Council
   |
   +-- LLM Synthesis Council
   |
   +-- JEV Delphi Council
           |
           v
      Independent agents
           |
           v
      JEV judgment
           |
           v
    Deterministic policy
           |
      +----+----+
      |         |
     stop    reconsider
                |
                v
             Round 2
   |
   v
SQLite
   |
   v
Evaluation
```

`CouncilRunner` is the library boundary. The CLI is a thin wrapper, so a later MCP server can call `await runner.consult(question)` without rewriting orchestration.

## Install

Python 3.12 or newer is required.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

On macOS/Linux, activate with `source .venv/bin/activate`.

## Environment

Copy `.env.example` as a reference and export only the keys for providers you use:

```text
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
TYPESAFE_API_KEY=
JEV_API_URL=
```

The project intentionally does not load `.env` files or add another dependency. Export variables in the shell or use your preferred secret loader. Missing keys fail only when that provider is called. No secret is stored in experiment metadata.

`HttpJevJudge` uses TypeSafe's documented `POST /v1/systemone` contract with one Choice question and three Noul questions. `JEV_API_URL` is an optional override for a compatible gateway. JEV failures are recorded and fail the affected question; there is no silent fallback. Live access, account limits, and the suitability of the four routing rubrics still require verification with your TypeSafe account.

## Run the pilot

The default council is three OpenAI, three Anthropic, and three Google agents with distinct IDs. Counts may be zero as long as at least one agent remains and the quorum is achievable.

```bash
python run_experiment.py --dataset datasets/pilot.jsonl --strategy single
python run_experiment.py --dataset datasets/pilot.jsonl --strategy vote --repetitions 3
python run_experiment.py --dataset datasets/pilot.jsonl --strategy synthesis
python run_experiment.py --dataset datasets/pilot.jsonl --strategy delphi --max-rounds 2
```

For more disagreement pressure, `datasets/challenge.jsonl` contains 25 objectively scored multiple-choice problems emphasizing multi-step arithmetic, probability, logic traps, combinatorics, and rate reasoning:

```bash
python run_experiment.py --dataset datasets/challenge.jsonl --strategy delphi --max-rounds 2
```

Useful controls include `--openai-agents`, `--anthropic-agents`, `--google-agents`, `--temperature`, `--minimum-valid-council-size`, `--deliberation-threshold`, `--seed`, and `--db-path`.

By default the CLI prints a live trace for every question: concurrent round size, answer distribution, member failures, JEV scores, the deterministic routing decision, and the final answer with latency and cost. Pass `--quiet` when only the final summary is wanted. The same information is emitted through an optional `CouncilRunner` event callback, so alternative visualizers do not affect experiment decisions.

## Frozen Phase 2 benchmark

The next evaluation phase is pre-registered in [`PHASE2_FROZEN_EXPERIMENT.md`](PHASE2_FROZEN_EXPERIMENT.md). It uses a checked-in, reproducible 500-question benchmark and a machine-verified frozen configuration. Preview and verify it without making API calls:

```bash
python run_phase2.py
```

Paid execution requires the explicit `--execute` flag:

```bash
python run_phase2.py --strategies single vote synthesis delphi --repetitions 3 --db-path phase2-results.sqlite3 --execute
```

The frozen runner rejects modified prompt or dataset content. The benchmark manifest records pinned upstream revisions and deterministic selection rules. GPQA is intentionally not copied into this repository because its official access conditions ask users not to reveal examples.

## Phase 3 archive and final Phase 3R confirmation

Phase 2 is preserved as exploratory evidence under `archives/phase2-exploratory-2026-09-22/`. The cost-controlled follow-up is preregistered in [`PHASE3_PREREGISTRATION.md`](PHASE3_PREREGISTRATION.md).

The v4 operational pilot is preserved under `archives/phase3-v4-pilot-2026-09-22/`; it is not a confirmatory result. V5 quarantines those 100 questions, retains the 400 unobserved rows, adds 100 source/category-matched replacements, and uses constrained `A`–`Z` choice labels so mathematical typography cannot invalidate an otherwise valid council member. Both raw labels and mapped option text are stored.

Phase 3 v5 runs only Delphi once. The same three Round-one answers provide the single-member and majority-vote baselines without additional API calls. Gemini 3.8 Flash runs with `LOW` thinking, and execution can resume without repeating successful questions. Dataset provenance is recorded in `datasets/phase3_confirmatory_500_v2.manifest.json`.

The locked Phase 3 result is preserved in `archives/phase3-v5-confirmatory-2026-09-22/`.
A checksummed companion erratum is preserved in
`archives/phase3-v5-erratum-2026-09-22/`. Retrospective inspection found that its JEV
request exposed `correct_answer` and that the generic scorer rejected many valid GSM1k
and BBEH answer formats. Phase 3 v5 is therefore compromised/exploratory rather than
confirmatory; its original archive has not been changed.

While Phase 3 runs, a human-readable checkpoint is refreshed after every question at `reports/phase3/<experiment-id>/progress.txt`. Stage and final snapshots are retained in the same folder for sharing and independent analysis.

```bash
python run_phase3.py
python run_phase3.py --preflight --execute
python run_phase3.py --limit 100 --db-path phase3-v5-results.sqlite3 --execute
```

The clean replacement is preregistered in
[`PHASE3R_PREREGISTRATION.md`](PHASE3R_PREREGISTRATION.md). It uses 500 completely
fresh questions, three repetitions, source-aware frozen scoring, equal output caps,
full successful-response provenance, and a ground-truth-free anonymized JEV payload.
It compares the Delphi final with both the same-run Round-one vote and same-run Google
member. First validate locally, then run an excluded four-question preflight:

```bash
python run_phase3r.py
python run_phase3r.py --preflight --execute
```

The first 50 questions are an operational cost/reliability stage only. Do not use
their accuracy to decide whether to continue:

```bash
python run_phase3r.py --limit 50 --db-path phase3r-final-results.sqlite3 --execute
python run_phase3r.py --resume EXPERIMENT_ID --db-path phase3r-final-results.sqlite3 --execute
python scripts/analyze_phase3r.py --db phase3r-final-results.sqlite3 --experiment EXPERIMENT_ID
```

Live reports are written to `reports/phase3r/<experiment-id>/progress.txt`. Credit or
quota exhaustion pauses without consuming a scientific run attempt. Other failures
are retained and get at most the frozen two run attempts.

## Phase 4 evidence robustness (v1 superseded; do not run yet)

[`PHASE4_PREREGISTRATION.md`](PHASE4_PREREGISTRATION.md) describes the planned H1e
test, but its v1 implementation freeze predates the Phase 3R core corrections and now
fails closed by design. It has not been run and must receive a new freeze ID after
Phase 3R before any Phase 4 live call. The dataset remains reserved and excluded from
Phase 3R.

Do not use `--execute` with `run_phase4.py` until v2 is preregistered.

## Phase 5 prospective routing comparison

[`docs/phase5-routing-preregistration.md`](docs/phase5-routing-preregistration.md)
freezes a new 500-question, one-run paired comparison. It tests whether JEV's
escalation rule is better than simply escalating when the three initial answers
disagree. Both rules share the same independent first-round answers and any
peer-reconsideration outputs. A separate own-answer-only revision branch tests
whether peer exposure helps beyond self-correction. This is a new experiment,
not a reanalysis of the Phase 3R sample. The dataset manifest records pinned
source revisions and zero overlap with the project's earlier question sets.

Use the existing environment with all four API keys set. First validate the
freeze without any paid calls or database writes:

```powershell
python run_phase5_routing.py
python -m pytest -q
```

Then start the registered sample. The runner is resumable; repeating the same
command skips successful calls and retains failures. It pauses at the recorded
cost cap (default $15), but that is not a guaranteed billing limit because
failed requests may incur unrecorded charges.

```powershell
python run_phase5_routing.py --execute --max-recorded-cost-usd 15
```

Operational progress without interim accuracy is written to
`reports/phase5-routing/progress.txt`. The final analysis stays locked while
calls are pending. Once all questions are complete or have exhausted their
frozen two attempts, run:

```powershell
python scripts/analyze_phase5_routing.py
```

The final report is saved to `reports/phase5-routing/final-analysis.txt`.
Its primary conclusion uses the preregistered paired accuracy difference and
2-percentage-point noninferiority margin. A non-significant difference is not
automatically evidence of equivalence.

## Phase 6 local-model routing pilot (v3)

The [v1 ten-question operational check](archives/phase6-local-v1-aborted-2026-09-23/ERRATUM.md)
exposed a per-agent skip bug and a too-short JSON output cap. It completed
zero councils and is **aborted, not a result**. Do not resume
`run_phase6_local.py` or use its database in analysis. Its lock, preflight,
database, and source are preserved.

The [v2 ten-question check](archives/phase6-local-v2-aborted-2026-09-23/ERRATUM.md)
then found deterministic JSON truncation in four first-round calls. V2 was
stopped after its permitted retries and is **not an accuracy result**. Do not
resume `run_phase6_local_v2.py`.

[`docs/phase6-local-v3-protocol.md`](docs/phase6-local-v3-protocol.md)
describes the separate **180-question** exploratory test, excluding all
questions touched by v1 or v2. It uses a bounded short-reason JSON format,
the same three small Ollama models and larger single-model baseline, and
compares JEV routing with simple disagreement routing on paired outputs.
Only JEV uses `TYPESAFE_API_KEY`; local calls stay on loopback.

On the Windows machine with the RX 7900 GRE, install/start [Ollama](https://ollama.com/download),
then pull the four exact tags:

```powershell
ollama pull qwen3:4b
ollama pull gemma3:4b
ollama pull phi4-mini:3.8b
ollama pull qwen3:8b
```

Model downloads require several gigabytes. The study runner does not download
models automatically or make any scored calls without `--execute`. In a
PowerShell session with `TYPESAFE_API_KEY` set:

```powershell
python run_phase6_local_v3.py
python run_phase6_local_v3.py --preflight
python run_phase6_local_v3.py --execute --limit 10 --max-jev-usd 0.50
python run_phase6_local_v3.py --execute --max-jev-usd 0.50
```

The v3 model digests and code were already locked in
`configs/phase6_local_locked_v3.json`; **do not rerun `--lock-models`**. The
excluded preflight checks 28 local outputs, one JEV judgment, and GPU
residency. The first ten questions are a mandatory operational gate: the
full command refuses to start until all ten are fully paired. Resume the
same `--limit 10` command once if needed; do not tune from interim accuracy.
Calls resume from `phase6-local-v3-results.sqlite3`.

```powershell
python scripts/analyze_phase6_local_v3.py
```

That final command writes `reports/phase6-local-v3/final-analysis.txt`. It refuses
to report interim accuracy while questions remain retryable. This pilot is
descriptive, not a powered proof of JEV superiority. The earlier Phase 3R and
Phase 5 freezes, databases, and reports are untouched.

## Exploratory routing replays

The saved Phase 5 and Phase 6 outputs support higher-threshold and hybrid
router replays without any new model calls. The post-hoc analyzer also reports
Newcombe paired intervals, unanimous-subset AUROC, accuracy by first-round
agreement, per-member accuracy, and round-two switching:

```powershell
python -m scripts.analyze_posthoc_routing
```

Outputs are written to `reports/posthoc-routing/analysis.txt`,
`threshold-sweep.csv`, and `threshold-sweep.svg`. These analyses are explicitly
exploratory and do not replace the frozen preregistered reports.

Provider pricing changes over time. The values in `council/config.py` are illustrative defaults, not a live price source. Override `ExperimentConfig.pricing` for a dated, reproducible experiment.

## Tests

Tests use fake agents and a mock JEV judge; they make no network calls.

```bash
python -m pytest
```

The suite covers vote and both tie-breaks, escalation/non-escalation, the two-round ceiling, confidence validation, SQLite persistence, lazy missing-key errors, and the absence of peer context in round one.

## Persistence

SQLite tables are created automatically:

- `experiments`: dataset, strategy, prompt version, providers/models, temperature, council settings, and seed.
- `agent_runs`: every successful answer plus the full provider response, requested and resolved model, request ID, finish reason, detailed usage, reasoning/evidence, token counts, latency/cost, round, and retry count.
- `jev_runs`: structured scores, full JEV response, request ID, retries, token counts, latency, and cost where available.
- `results`: objective outcome plus aggregate cost, token, wall-clock latency, disagreement, agents used, and rounds.
- `failures`: provider/JEV/quorum/parse failures, including failed member details and retry counts where available.

The evaluator reports accuracy, mean cost, tokens, latency, escalation rate, agents used, rounds, Brier score, and expected calibration error. Failed questions are excluded from accuracy and printed separately, while remaining visible in SQLite.

## Experimental safeguards

- Every strategy reads the same source `Question` objects.
- Scoring and voting use frozen source-aware normalization, including constrained multiple-choice labels, GSM numeric final-answer extraction, and target-free BBEH formatting normalization; raw answers remain unchanged in SQLite.
- Vote, synthesis, and Delphi use the same versioned first-round prompt.
- `asyncio.gather(..., return_exceptions=True)` runs round-one agents independently and retains individual failures.
- A configurable quorum permits partial council failure without hiding it.
- Round two includes the agent's own prior position, answer distribution, and conflicting reasoning, but no alleged correct answer.
- JEV judges and routes only; it never writes the final answer. Python owns the escalation decision.
- Raw successful provider outputs, resolved models, request IDs, detailed usage, JEV responses, retries, and failures are retained.

## Current limitations

- Provider and TypeSafe/JEV response contracts are isolated because APIs and model availability evolve; they have not been exercised with this repository's credentials.
- Pricing is static configuration and may become stale.
- Repetitions are run sequentially; members within a council round are concurrent.
- Normalization remains deliberately task-specific; richer symbolic equivalence and arbitrary unit conversion are not attempted.
- There is no migration system, global rate-limit coordinator, or MCP server yet.

## Future experiments

High-value next steps after Phase 4 are: (1) compare JEV routing with cheaper deterministic
routers, (2) run a fixed-two-round counterfactual, and (3) add concurrency/rate-limit
coordination. Other useful work includes per-provider prompt adapters, council-composition
ablations, independent reproduction, and a small MCP façade.
