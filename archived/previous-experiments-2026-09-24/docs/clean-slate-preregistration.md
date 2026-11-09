# Clean-slate non-reasoning council study (v1)

Author: Brian Doutey (independent researcher; no institutional affiliation)

Status: frozen before any scored calls under this protocol.

## Purpose

This is a standalone experiment. No accuracy estimate, effect estimate, table,
figure, or worked example from an earlier implementation will be pooled into or
used as evidence in the resulting paper. Historical files remain available only
as an audit trail and are outside this documentation pipeline.

The research question is whether a paid structured JEV judgment routes a
three-model council's second round materially better than the deterministic
rule “escalate when the three normalized first-round answers are not unanimous.”

## Frozen council and non-reasoning contract

There is exactly one member from each provider:

- OpenAI `gpt-4.1-mini-2025-04-14`;
- Anthropic `claude-haiku-4-5-20251001`;
- Google `gemini-2.5-flash` with `thinkingBudget: 0`.

These are capable, latency-oriented models rather than a mixture of flagship
and economy tiers. “Comparable” is a design judgment about market role and
intended operating tier, not a claim that parameter counts or benchmark scores
are identical. All three must use provider-side non-reasoning operation:

- GPT-4.1 Mini is a non-reasoning model. Any reported non-zero reasoning-token
  count is a hard failure.
- Claude Haiku 4.5 receives no `thinking` parameter. Any `thinking` or
  `redacted_thinking` response block is a hard failure.
- Gemini 2.5 Flash receives `thinkingBudget: 0`. Any reported non-zero
  `thoughtsTokenCount` is a hard failure.

The short visible `reasoning` field is ordinary model output used by JEV and is
not hidden chain-of-thought. Temperature is zero, the structured schema is
identical across providers, and each response is capped at 1,024 output tokens.
A separate, unscored arithmetic preflight must establish model access,
structured output, and the hidden-reasoning checks before scored execution.

## Sample

The fixed sample contains 500 public, objectively scored questions: 250
MMLU-Pro, 100 BBEH Mini, 100 GSM1K, and 50 ARC-Challenge. The JSONL is hashed
before execution. Public benchmarks may have appeared in model training;
“fixed” does not mean uncontaminated. Each question is called once per required
branch. Ground truth and source metadata are never sent to a model or JEV.

## Procedure

For every question, the three members answer independently. JEV receives the
question, choices, and anonymized model answers, but not provider identities or
ground truth. Two routes are then recorded before any second-round result:

1. JEV escalation for weak/none agreement or `needs_deliberation >= 0.10`.
2. Simple escalation whenever normalized initial answers are non-unanimous.

If either route escalates, the same frozen initial state generates two
independent counterfactual branches: peer reconsideration and an own-answer-only
reconsideration control. Branch order is deterministically counterbalanced.
Both routing policies share the peer branch, so their difference isolates the
routing decision. Final answers use deterministic majority voting; there is no
generative tie-breaker.

## Outcomes and inference

The primary estimand is paired accuracy, simple route minus JEV route, over the
500 questions. The practical noninferiority margin is 2 percentage points. The
simple rule is declared noninferior only when the lower bound of a 10,000-draw
question-level percentile-bootstrap 95% interval is greater than -2 points.
The fixed analysis seed is 20260926.

Secondary descriptive outcomes are initial-majority accuracy, each of the three
member accuracies (reported symmetrically), route counts, the own-answer control,
source breakdowns, token cost, and latency. No “best member” is selected after
seeing results for a privileged inferential comparison.

At most two attempts are recorded per missing provider/stage. Successful calls
are never silently rerun. If more than 2% of questions remain incomplete, the
primary result is not evaluable; otherwise complete-case estimates and
worst/best missingness bounds are reported. Quota exhaustion or the $15 recorded
cost cap pauses the run without changing the sample or protocol. No interim
accuracy is displayed.

## Independence and disclosures

This is Brian Doutey's personal project, motivated by a longstanding question
about multi-model deliberation and by the possibility that JEV could act as an
arbiter in a Delphi-style process. The author has no institutional affiliation.
No person or organization paid for, commissioned, or influenced the work. The
author reports no relationship with TypeSafe and no external funding.

