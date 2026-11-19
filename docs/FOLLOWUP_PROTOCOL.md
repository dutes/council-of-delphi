# Protocol: does the council still hurt when it's as strong as the judge?

Author: Brian Doutey, independent researcher (no institutional affiliation)

Status: **DRAFT, not frozen.** Nothing in this document has been run. It becomes
binding when the freeze section at the end is completed and the file is hashed.
Until then, every item marked *[to fix at freeze]* can still change.

## Why this study exists

The first study ([`PROTOCOL.md`](PROTOCOL.md), freeze v5) answered its
pre-registered question: JEV-controlled Delphi beat a simple council vote by
+13.2 points. However, it also produced a result I didn't plan for. JEV answering
on its own scored 87.3%, and the full Delphi process it controlled scored 80.8%.
Adding the council cost the judge 6.5 points (95% CI +3.4 to +9.5).

That comparison was post-hoc. I added it after the locked analysis, so I can't
treat it as a confirmed finding. There's also an obvious alternative
explanation: the council was three small, fast models, and the judge may simply
be a stronger model. A strong model dragged down by weaker ones isn't the same
claim as "councils make judges worse".

This protocol tests both things properly, and I'm writing it down before running
anything so the result can't shape the question.

## Research questions

1. **Replication.** On fresh questions, does JEV alone still beat the full
   Delphi process with the original small council?
2. **Strength.** When the council is matched in strength to JEV, does the full
   Delphi process still do worse than JEV alone?
3. **A seat at the table.** If JEV's own answer is added as one of the
   candidates, can the Delphi process at least match JEV alone?

## What would change my mind

I'm stating this before the run:

- If the matched-council Delphi process **beats JEV alone** (95% interval
  entirely above zero), I was wrong to generalise from the first study. The
  first result was about weak councils, and councils can help a judge when
  they're strong enough.
- If the interval **includes zero**, the first result doesn't carry over to a
  strong council, and I'll say the question is open.
- If JEV alone **still wins** (interval entirely below zero), adding a council
  costs a capable judge accuracy even when the council is its equal, in this
  setup. That's the strongest form of the finding, and the one I'd want most
  carefully replicated before anyone relies on it.

## Conditions

All conditions run on the same questions, so every comparison is paired.

### D. JEV alone

JEV receives the question and choices with no council input and selects a
label. Unchanged from the first study.

### F-small. Delphi with the original council (replication arm)

The first study's council, prompts, temperature, crowd size and one-round
Delphi procedure, unchanged:

- OpenAI `gpt-4.1-mini-2025-04-14`
- Anthropic `claude-haiku-4-5-20251001`, extended thinking omitted
- Mistral `ministral-14b-2512`

### F-matched. Delphi with a strength-matched council (primary arm)

The same Delphi procedure as F-small, with three different council models
chosen by the matching rule below. Nothing else changes.

### G. Delphi with JEV as a candidate

The same as F-matched, using the same council answers, except JEV's answer
from condition D is added to the anonymised candidate list before JEV's
assessment. It's presented like a council position, with a vote count of one,
no rationale and no stated confidence, and nothing labels it as JEV's. If it
matches a council answer, it joins that candidate's support, because
candidates are grouped by answer.

JEV can stop, ask for one reconsideration round, and select the final answer,
exactly as in F-matched. Council members see JEV's candidate in the
reconsideration round like any other. It stays in the list for the final
selection, so reconsideration can't remove it; only JEV can pass it over.

### C-matched. Strength-matched council majority

The equal vote over the matched council's three provider positions, with the
same SHA-256 tie rule as the first study. Reported so the matched council's own
strength is visible.

## Choosing the strength-matched council

I don't know which model powers JEV (I've asked TypeSafe). So I'll match on
measured accuracy rather than on model names.

1. **Calibration set.** 60 questions drawn by the same rules as the main
   sample, disjoint from it and from every question used before. These are
   used only for matching and are excluded from every analysis.
2. **Measure JEV alone** on the calibration set.
3. **Candidate models.** For each of OpenAI, Anthropic and Mistral, a short
   list of general-purpose models, fixed in `config/followup_v1.json` before
   calibration, with reasoning switched off (see below).
4. **Measure each candidate's first-answer accuracy** (one sample, the first
   study's prompt and temperature) on the calibration set.
5. **Selection rule.** For each provider, pick the cheapest candidate, by
   measured cost per question on the calibration set, whose accuracy is
   within 3 points of JEV alone in either direction. A council far stronger
   than JEV isn't a match any more than a far weaker one. If no candidate is
   within 3 points, pick the one closest to JEV alone and record the gap.
6. Record the chosen models, their calibration accuracy and the gaps in the
   freeze record before any scored call.

If a provider has no candidate within 3 points, the study runs anyway, and the
report has to say the match wasn't achieved and by how much.

### Reasoning switched off

The first study used only models with no reasoning mode, because with
reasoning on, the strongest models leave a judge little to add. That stays
true here: no council model reasons before answering. However, almost no model
built without reasoning gets near JEV's accuracy, so the strict rule would make
a matched council impossible for two of the three providers.

So the follow-up allows models that *can* reason, with reasoning switched off on
every call:

- **OpenAI** GPT-5 family: `reasoning_effort` set to `none`.
- **Mistral** Medium and Small: `reasoning_effort` set to `none`.
- **Anthropic:** extended thinking is never requested, as in the first study.

Every response is checked as before. Reasoning tokens, a thinking block or a
reasoning field fails the call. A candidate that reasons anyway fails the
preflight check and is dropped before calibration. Models with no reasoning
mode, including the whole original small council, are called exactly as in the
first study.

Two of the Anthropic candidates, `claude-sonnet-5-5` and `claude-opus-5-5`,
no longer accept a temperature setting at all. If either is chosen, it's
sampled at Anthropic's fixed default instead of the protocol's 0.7, and the
freeze record says so. Every other model, including the whole small council,
uses 0.7 as before.

This is the first protocol's own definition ("no enabled hidden reasoning
mode"). The first study went further and also excluded models that could
reason, based on their listing; the follow-up doesn't.

## Outcomes and estimands

**Primary estimand** (paired, question-level accuracy difference):

```text
JEV alone  -  F-matched Delphi final
```

**Key secondary estimands:**

```text
JEV alone  -  F-small Delphi final              (replication of the post-hoc result)
G final    -  JEV alone                         (does a seat at the table help?)
F-matched Delphi final  -  C-matched majority   (does Delphi still beat voting?)
```

Also reported:

- accuracy for every condition and every council model;
- helpful and harmful transitions for the primary comparison: questions where
  JEV alone was right and Delphi wrong, and the reverse;
- the candidate oracle ceiling (a correct candidate exists) and selection
  accuracy when one does;
- how often JEV asks for reconsideration, and how often reconsideration moves
  a correct council to a wrong answer;
- for condition G, how often the final answer is JEV's own answer;
- cost, failures and missingness per condition.

## Analysis

- Paired question bootstrap, 10,000 draws, 95% percentile intervals, with the
  analysis seed set in `config/followup_v1.json`.
- One primary estimand, so no multiplicity correction on it. The secondary
  estimands are reported with their intervals and described as secondary.
- Questions with a missing value in a comparison's two conditions are dropped
  from that comparison only, and the count is reported.
- No interim accuracy is viewed. The analysis script is written, tested on a
  synthetic database and hashed before the first scored call.

## Sample

- 500 new public multiple-choice questions: 400 from MMLU-Pro and 100 from
  ARC-Challenge, the same mix as the first study.
- Health and law categories are excluded.
- Every question used in any earlier study, including the 500 from freeze v5,
  the calibration set and the quarantined exploratory work, is excluded by
  source row and by exact text.
- Public benchmark questions may still appear in the models' training data.
  That applies to every condition equally.

## Operational safeguards

Carried over from the first study unchanged:

- Ground truth stays local and is replaced with a dummy label in every
  model-facing object.
- Successful calls are never rerun. Each missing stage gets at most two
  recorded attempts.
- More than 2% incomplete questions in the primary comparison makes the
  primary analysis non-evaluable.
- Output ceiling of 2,048 tokens for every model.
- A recorded-cost cap pauses the run rather than changing the protocol
  *[to fix at freeze: cap, set from the calibration run's cost per question]*.
  For reference, the first study's 494 scored questions cost $5.65 in total,
  almost all of it council calls. Larger council models will cost more.
- Any amendment after freeze is written into this file with its date and
  reason, and disclosed in the report.

## Interpretation boundaries

Results apply to this judge, these council models, these prompts and this
question mix. A council matched on multiple-choice accuracy isn't necessarily
matched on everything that matters to a judge, such as calibration or the
quality of its rationales. Whichever way the primary result goes, it won't show
that councils always or never help.

## Independence and disclosure

This is my personal, self-funded project. No person or organisation paid for,
commissioned or influenced it. I have no affiliation with TypeSafe AI or any
model provider.

## Freeze record

*[to complete at freeze]*

- Date:
- Council candidate list:
- Calibration results and chosen matched council:
- Cost cap:
- Seeds (crowd, arbitration, tie, analysis):
- Dataset SHA-256 (main sample and calibration set):
- Implementation SHA-256:
- This file's SHA-256:
