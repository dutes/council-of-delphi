# Council of Delphi — Phase 4 H1e Robustness Preregistration

> **Superseded before execution.** This v1 freeze predates the Phase 3R scoring,
> provenance, output-cap, and JEV-payload corrections and now fails machine
> verification by design. Do not run it. A later Phase 4 v2 must receive a new
> freeze ID and be preregistered after Phase 3R.

Freeze ID: `phase4-h1e-robustness-2026-09-22-v1`  
Status: frozen before any Phase 4 live model call  
Primary hypothesis: H1e

## Question

Does the frozen JEV-mediated Delphi procedure lose less accuracy than its paired
baselines when council members receive misleading, duplicated, or correlated evidence?

This is a falsification-oriented experiment. Correlated misinformation may cause JEV
to mistake repeated reasoning for independent corroboration. A null or adverse result
is valid evidence against H1e.

## Dataset

- Version: `phase4-robustness-300-v1`
- Path: `datasets/phase4_robustness_300.jsonl`
- SHA-256: `780ac51accdb7a24969b17230544b831eae95c030abc24af3dc4e270f3bf3264`
- Size: 300 multiple-choice questions
- Composition: 250 MMLU-Pro and 50 ARC-Challenge
- Exclusions: every source row and exact question text used in Phase 2, Phase 3 v4,
  or Phase 3 v5
- Sensitive categories: MMLU health and law remain excluded

One incorrect option is selected for each question by fixed-seed SHA-256 ranking.
No model chooses the misleading answer or evidence target.

## Paired conditions

Every base question is evaluated once in each condition. Condition order is
deterministically randomized within question.

1. `control`: no external evidence.
2. `single_misleading`: one deterministically assigned agent receives one false claim.
3. `duplicated_misleading`: two agents receive the same false claim with the same source ID.
4. `correlated_misleading`: two agents receive differently worded, independent-looking
   claims that point to the same false answer.

Evidence is framed as fallible evidence, not an instruction. Agents are told to assess
its reliability. The same assigned evidence persists if Round 2 occurs. Agents never
see another member's evidence assignment.

## Blinding

- Agent and condition assignments are stored separately under opaque run IDs.
- JEV is not shown the condition, corrupted-agent identities, evidence IDs,
  misleading answer, or correct answer.
- JEV receives only the sanitized source question and the actual council outputs.
- Ground truth is used locally after completion for scoring only.

This explicit JEV blinding is new in Phase 4. Retrospective inspection found that the
Phase 3 JEV payload serialized `correct_answer` as part of the Question object. JEV did
not produce final answers, but this is a limitation of Phase 3 routing evidence and is
not reproduced here.

## Frozen inference system

- OpenAI: `gpt-4.1-mini-2025-04-14`, one agent
- Anthropic: `claude-haiku-4-5-20251001`, one agent
- Google: `gemini-3.8-flash`, one agent, thinking level `LOW`
- JEV: `jev-1.13.0`
- Temperature: `0.0`
- Maximum rounds: 2
- Required quorum: 3
- Escalation: agreement `weak` or `none`, or deliberation score `>= 0.10`
- Seed: `20260924`
- Agent prompt: `agent-v2-choice-labels`
- JEV prompt: `jev-routing-v1`
- Perturbation prompt: `evidence-perturbation-v1`
- Prompt SHA-256: `3faa046297f962445af6ce9e293481ea5195a0731be1b7c44a2c6de692d4d857`
- Implementation SHA-256: `d7e285b013e0ee0926cf47e919e084ee3396e166e2f6b7a74621d8888afbaf5d`

## Outcomes and decision rule

The primary condition is `correlated_misleading`. For each comparator:

```text
degradation = control accuracy - perturbed accuracy
robustness advantage = comparator degradation - Delphi degradation
```

The co-primary comparators are:

1. majority vote derived from the same three Round-one outputs;
2. the Google Round-one member, preregistered because it was the strongest individual
   provider in Phase 3.

Ten-thousand question-clustered bootstrap draws produce 95% intervals. H1e is:

- fully supported when the interval excludes zero above zero for both comparisons;
- partially supported when it does so for exactly one comparison;
- not supported when it does so for neither comparison;
- not evaluable if paired primary-condition data are incomplete.

The intersection rule requiring both comparisons controls the full-support claim
without selecting the easier comparator after observing results.

Secondary analyses cover the other perturbations, each provider, false consensus,
escalation, cost, tokens, latency, and failures. They do not replace the primary rule.

## Execution and stopping

An excluded live systems check uses five fixed questions crossed with all four
conditions (20 condition-runs). Those calls are not written to the experiment database.

The confirmatory experiment contains 1,200 condition-runs. An operational checkpoint
after the first 50 base questions is permitted, but accuracy cannot be used to change
or stop the protocol. Provider credit exhaustion pauses immediately; completed rows and
failures are retained and the same experiment is resumed.

No model, prompt, evidence wording, assignment algorithm, routing threshold, scoring
rule, dataset row, or analysis rule may change under this freeze ID.

## Commands

Offline verification only:

```powershell
python run_phase4.py
```

Excluded 20-run live systems check:

```powershell
python run_phase4.py --preflight --execute
```

Operational first selection (50 questions × 4 conditions):

```powershell
python run_phase4.py --limit 50 --db-path phase4-results.sqlite3 --execute
```

Resume the same experiment through all 300 questions:

```powershell
python run_phase4.py --resume EXPERIMENT_ID --db-path phase4-results.sqlite3 --execute
```

Final preregistered analysis:

```powershell
python scripts/analyze_phase4_robustness.py --db phase4-results.sqlite3 --experiment EXPERIMENT_ID --dataset datasets/phase4_robustness_300.jsonl
```
