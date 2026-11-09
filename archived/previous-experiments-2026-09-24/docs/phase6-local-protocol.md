# Phase 6 local-model routing pilot — protocol v1

Status: **setup complete; no scored local-model or JEV calls yet**. This is a
new exploratory study, not a continuation of Phase 5 or a replacement for its
negative JEV-routing result. Before scored calls, lock the installed local
model digests with `run_phase6_local.py --lock-models`, then complete the
excluded preflight. A locked run may not silently change models or code.

## Question and interpretation

Does the fixed JEV routing rule improve a *local, smaller-model* council more
than the deterministic rule “escalate if the normalized initial answers
disagree”? The primary descriptive estimand is paired accuracy, **JEV route
minus disagreement route**. Report a 10,000-draw question-bootstrap 95% interval
and right/wrong transitions. This 200-question pilot is not powered or
predeclared as a formal superiority test. An observed gain is hypothesis-
generating and requires a separate fresh holdout to confirm.

Also report the first-round vote and a predeclared larger local single-model
baseline. The single model gets only the question and never council outputs.
This guards against claiming that a council is useful merely because it beats
its own weaker vote.

## Sample

- 200 unique public benchmark questions: 100 MMLU-Pro, 20 BBEH Mini, 50
  GSM1K, 30 ARC-Challenge. Four pinned upstream revisions and seed 20260927.
- Exclude source rows and exact question texts from pilot, challenge, Phases
  2/3/3R/4/5. Hash the resulting JSONL and manifest before model calls.
- MMLU-Pro is category-stratified; BBEH Mini is fixed-seed hash-ranked because
  few unused Mini rows remain. The changed source mix limits direct numerical
  comparison with hosted phases.
- “Fresh” means unused in this project's earlier live calls, not guaranteed
  absent from model pretraining.

## Frozen candidate setup

One agent each: `qwen3:4b`, `gemma3:4b`, and `phi4-mini:3.8b`, using Ollama's
quantized local tags. The separate larger single baseline is `qwen3:8b`.
The tags are *not* sufficient identifiers: the `/api/tags` SHA-256 digests are
recorded in the lock file, and every resume checks them again. This choice is
for a 16 GB Radeon RX 7900 GRE and 48 GB system RAM; actual GPU residency is
recorded during preflight. Do not treat this small, convenience sample of local
models as a universal model ranking.

Runtime: local loopback Ollama `/api/chat`, JSON-schema output, temperature 0,
fixed per-agent/per-question seed, 8192-token context setting, 512 generated-
token cap, and a 300-second request timeout. Qwen's thinking output is
explicitly disabled; other models use their default non-thinking behavior.
Each model processes a batch of questions sequentially so that a single GPU
does not need to host all four models simultaneously. Local model requests
never use cloud Ollama. Only JEV is remote and needs `TYPESAFE_API_KEY`.

JEV model `jev-1.13.0`; trigger a second round for agreement `weak`/`none` or
needs-deliberation >= 0.10, as in Phase 5. The simple rule triggers when
normalized answers are not unanimous. Both decisions are made from the same
saved three independent first-round answers and JEV judgment before any
second-round output is seen. If either rule escalates, generate one common
peer-reconsideration branch. Both rules use that same branch when they
escalate; otherwise each uses the initial majority vote. This isolates
routing rather than confounding it with fresh second-round sampling.

The first-round prompt and neutral peer-reconsideration prompt, choice-label
transport, deterministic majority tie-break, JEV ground-truth/provider
anonymization, and source-aware answer scoring are inherited from the frozen
core. Round one never receives peer answers. JEV never writes the final
answer. The dataset target is removed from all inference/JEV request objects.

## Operations and reporting

- An excluded synthetic question checks all four local JSON outputs and JEV;
  it is not in the scored sample. `/api/ps` GPU residency is recorded, and
  preflight fails if any model is not observed on the GPU.
- At most two *recorded* attempts per missing agent or JEV stage. Successful
  outputs are retained on resume, with raw responses and usage. JEV failure
  leaves the question incomplete; there is no silent simple-rule fallback.
- A 5% incomplete-question cap applies to descriptive paired reporting. Above
  it, label the primary comparison not evaluable. Show worst/best-case
  missingness bounds. No tuning or replacement questions after looking at
  accuracy. The optional `--limit` is for operations only and does not change
  the frozen 200-question plan.
- A scored response is rejected if its prompt-token count reaches the
  configured context limit, where silent truncation is possible.
- No interim accuracy is printed. Operational progress reports completion,
  failures, and recorded JEV spend. The analysis script refuses to run while
  any incomplete question is still retryable.
- Report route-specific token use, JEV charges, and summed per-call latency.
  On this sequential local GPU, that latency is a proxy, not a controlled
  live-deployment stopwatch. Electricity and hardware wear are not priced.
  JEV's frozen input estimate is $0.042 per million tokens; invoices may differ.

## Environment and provenance

Ollama's [official AMD support note](https://ollama.com/blog/amd-preview)
lists the RX 7900 GRE on Windows. Its
[chat endpoint](https://docs.ollama.com/api/chat) documents JSON schema,
seeding options, timing, and token counts; [tags](https://docs.ollama.com/api/tags)
and [running models](https://docs.ollama.com/api/ps) expose model digests and
GPU residency. Model tag sizes are published in the Ollama library. We use
this loopback backend instead of a CUDA-oriented vLLM/Transformers stack
because the current workstation is Windows with an AMD GPU and the research
question needs paired custom orchestration, not a generic leaderboard task.

The local-model experiment has not begun until the lock, preflight, and first
`--execute` call succeed. The Phase 3R and Phase 5 databases remain unchanged.
