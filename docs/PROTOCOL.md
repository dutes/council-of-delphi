# Protocol: crowds, a heterogeneous council, and JEV Delphi arbitration

Author: Brian Doutey, independent researcher (no institutional affiliation)

Status: v5 frozen before the restarted scored run, following the documented
aborted operational pilot below.

## Pre-study model-slate amendment

The initial clean-slate protocol named Google `gemini-2.5-flash` as the third
council model. During unscored API-contract preflight on 24 September 2026,
Google's API rejected calls to that model because it was no longer available
to new users. The model appeared in API discovery, but could not be invoked by
either Google project tested. These calls used only a synthetic arithmetic
question; no question from the frozen 500-item dataset was submitted, no
scored response was generated, and no outcome analysis had begun.

Before any scored call, Mistral was selected as the third independent provider.
Mistral Large 3 (`mistral-large-2512`) was considered first, but an unscored
preflight returned a subscription-tier rejection. The account's model metadata
marked its stronger available generalists as reasoning-capable and marked
Ministral 3 14B as `reasoning: false`. The dated model
`ministral-14b-2512` was therefore selected as the strongest available Mistral
generalist meeting the non-reasoning constraint. It then passed the synthetic
structured-output preflight. This final replacement produced freeze v4. The
Gemini and Mistral Large preflights are excluded from the experiment and will
not be represented as study data. The final report must disclose this amendment
when describing model selection and limitations.

## Operational amendment after aborted start

The v4 run was stopped after six questions had been touched because the
512-token output ceiling caused structured JSON to be truncated across all
three providers. At stoppage, the database contained 68 calls: 50 successful
calls and 18 truncation failures, with a recorded estimated cost of $0.04113655.
No accuracy, ground-truth comparison, or aggregate outcome was calculated or
inspected. The failure mode was identified solely from invalid JSON ending at
the configured output boundary.

The entire v4 database and progress record were quarantined and are excluded
from every analysis. The output ceiling was raised uniformly for all three
providers from 512 to 2,048 tokens, and the experiment was restarted in a new
database under freeze v5. Prompts, models, sampling temperature, sample size,
questions, estimands, arbitration logic, and analysis plan were unchanged.
This operational amendment must be disclosed in the final paper's methods and
limitations.

## Motivation and research question

This study separates three ideas that are often conflated: repeated sampling
from one model (a homogeneous crowd), aggregation across different model
families (a heterogeneous council), and evidence-sensitive arbitration. It asks:

1. Does a three-sample crowd improve each non-reasoning model's first answer?
2. Does an equal vote among three model-family crowd positions improve on the
   corresponding vote among their first answers?
3. Does JEV improve on simple council voting by selecting the strongest
   available answer?
4. Does a bounded JEV-controlled Delphi procedure improve further by deciding
   whether the council should reconsider before a final selection?

The study tests these as empirical hypotheses. It does not assume that crowds,
heterogeneity, JEV, or reconsideration must help.

## Models and operational reasoning control

The three council members are:

- OpenAI `gpt-4.1-mini-2025-04-14`;
- Anthropic `claude-haiku-4-5-20251001`, with extended thinking omitted;
- Mistral `ministral-14b-2512`.

They are treated as comparably positioned, general-purpose, lower-latency model
offerings from different families. The comparison does not claim identical
capability. Provider-level accuracy is reported symmetrically.

"Non-reasoning" is operationalized as no enabled hidden reasoning mode. Any
OpenAI reasoning tokens or an Anthropic thinking block make that call fail.
Ministral 3 14B is used through its standard general-purpose chat endpoint. Its
account model metadata reports `reasoning: false`, no reasoning-mode parameter
is sent, and any reasoning field in its response makes the call fail. A short
visible justification is requested because JEV must have
evidence to assess; it is not treated as a hidden chain-of-thought.

Initial calls use temperature 0.7 so repeated samples can differ. Each provider
receives identical question content, output fields, sample count, and output
cap. Samples are generated independently and never see other samples.

## Frozen conditions

For each question, the following conditions are recorded:

### A. First answers

Sample 1 from each provider is retained. The three labels receive one equal
vote each to form the first-answer heterogeneous baseline.

### B. Each model's own crowd

Each provider produces three independent initial samples. Plurality within that
provider produces one provider-level position. A within-provider tie is broken
by a question-, provider-, and seed-specific SHA-256 ordering frozen before
calls. Each model family still contributes exactly one position.

### C. Cross-model crowd majority

The three provider positions receive one equal vote each. A 2-1 or 3-0 result
is used directly. A 1-1-1 tie is resolved by a question-specific SHA-256 label
ordering. Provider identity, stated confidence, and JEV do not break this tie.
This is the primary non-JEV comparator.

### D. JEV alone

JEV receives the public question and choices without council answers and
selects a label. This controls for JEV simply being a capable fourth solver.

### E. JEV selection-only

Matching provider positions are collapsed into anonymized candidates. JEV sees
the question, choices, internal crowd vote counts, concise rationales, and
evidence, but no provider/model identities, ground truth, costs, or baseline
choice. JEV must select an existing candidate and cannot invent another answer.
Unanimous councils pass through without a paid selection call.

### F. JEV-controlled Delphi

JEV assesses every initial council, including unanimous councils. In the same
typed assessment it selects the strongest current candidate and chooses one of:

- `stop`: current evidence is sufficient and the selected candidate is final;
- `reconsider`: exactly one additional review round is warranted.

If reconsideration is requested, each of the three models receives the same
anonymized initial candidate record. It is warned that the majority may be
wrong and independently returns one revised position. The models do not see
provider identities or the ground truth. JEV then selects among the revised
positions. There is no second reconsideration round, so the stopping horizon is
fixed and cannot be extended after inspecting results.

## Outcomes and estimands

The primary estimand is the paired question-level accuracy difference:

```text
full JEV-controlled Delphi final - cross-model majority of provider crowds
```

The two principal secondary estimands decompose the system:

```text
cross-model majority of provider crowds - cross-model vote of first answers
JEV selection-only - cross-model majority of provider crowds
```

The final report also includes:

- JEV-alone accuracy;
- first-sample and own-crowd accuracy for every provider;
- the simple vote over post-controller positions, separating reconsideration
  effects from final JEV selection;
- paired 95% question-bootstrap intervals;
- helpful and harmful primary transitions;
- disagreement and reconsideration frequencies;
- the candidate oracle ceiling (a correct provider position exists);
- the raw-sample oracle ceiling (any of nine initial samples is correct);
- selection accuracy conditional on a correct candidate being available;
- cost, failures, missingness, and resolved model identifiers.

## Sample and operational safeguards

The frozen sample contains 500 public multiple-choice questions: 400 from
MMLU-Pro and 100 from ARC-Challenge. Health and law categories are excluded, as
are every source row and exact question text found in the quarantined earlier
project. Public benchmark questions may nevertheless have appeared in model
training data.

The dataset and implementation hashes are frozen before scored calls. Ground
truth remains local and is replaced with a dummy label in every model-facing
object. No interim accuracy is displayed. Successful calls are never rerun.
Each missing stage gets at most two recorded execution attempts. More than 2%
incomplete questions makes the primary analysis non-evaluable. Quota exhaustion
or the recorded-cost cap pauses execution rather than changing the protocol.

## Interpretation boundaries

The provider crowd samples are correlated observations, not independent human
participants. Results apply to this model slate, prompt, temperature, question
distribution, crowd size, and one-round Delphi policy. A positive result cannot
establish that all model crowds or arbiters improve accuracy. JEV selection can
only succeed when a correct candidate exists; the JEV-alone control is used to
distinguish arbitration from direct question-answering ability.

## Independence and disclosure

This is Brian Doutey's personal project, motivated by a longstanding question
about whether LLMs can use a wisdom-of-crowds mechanism and by the possibility
that JEV's typed classifier could serve as a Delphi arbiter. No person or
organization paid for, commissioned, or influenced the work. The author reports
no affiliation or relationship with TypeSafe and no external funding.
