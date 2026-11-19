# Protocol: does the council still hurt when it's as strong as the judge?

Author: Brian Doutey, independent researcher (no institutional affiliation)

Status: **DRAFT, not frozen.** Nothing in this document has been run. It becomes
binding when the freeze section at the end is completed and the file is hashed.
Until then, anything in it can still change.

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

I'm stating this before the run. The primary estimand is JEV alone minus
Delphi with the strong council, so a positive number means JEV alone did
better.

- If the interval is **entirely below zero**, Delphi with the strong council
  beat JEV alone. I was wrong to generalise from the first study: its result
  was about a weak council, and a strong enough council helps a judge.
- If the interval **includes zero**, the first result doesn't carry over to a
  strong council, and I'll say the question is open.
- If the interval is **entirely above zero**, JEV alone still wins, so adding
  a council costs this judge accuracy even when the council is much stronger,
  in this setup. As the calibration outcome below explains, "much stronger"
  doesn't mean "equal", and I'll say so.

The strength comparison (Delphi with the strong council minus Delphi with the
small one) is read alongside it. If it's clearly positive while JEV alone
still wins, a stronger council helps the process but not enough to beat the
judge on its own.

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
- **Anthropic:** thinking is never requested, as in the first study. Claude
  Sonnet 5.5 thinks by default and won't accept "disabled", so it's sent
  `thinking: {"type": "between_tools"}`, which turns its up-front thinking off;
  with no tools, its reply is text only. Claude Opus 5.5 can't have thinking
  switched off at all, so it isn't a candidate.

Every response is checked as before. Reasoning tokens, a thinking block or a
reasoning field fails the call. A candidate that reasons anyway fails the
preflight check and is dropped before calibration. Models with no reasoning
mode, including the whole original small council, are called exactly as in the
first study.

Two Anthropic candidates, `claude-sonnet-5-5` and `claude-opus-4-8`, no
longer accept a temperature setting at all. If either is chosen, it's
sampled at Anthropic's fixed default instead of the protocol's 0.7, and the
freeze record says so. Every other model, including the whole small council,
uses 0.7 as before.

This is the first protocol's own definition ("no enabled hidden reasoning
mode"). The first study went further and also excluded models that could
reason, based on their listing; the follow-up doesn't.

### Calibration outcome (19 November 2026, before the freeze)

With reasoning switched off, no candidate came within 3 points of JEV. JEV
alone scored 86.7% on the 60 calibration questions, so the rule picked the
closest candidate from each provider:

| Provider | Chosen model | Calibration accuracy | Gap to JEV |
|---|---|---|---|
| Anthropic | `claude-sonnet-5-5` | 83.3% | 3.3 points below |
| OpenAI | `gpt-5.5-2026-04-23` | 75.0% | 11.7 points below |
| Mistral | `mistral-medium-3-5` | 63.3% | 23.3 points below |

On the same questions, the small council's models averaged about 56% and the
chosen council about 74%. So this is a much stronger council than the first
study's, but not JEV's equal, and the report has to say that plainly. The
Anthropic seat is close; the Mistral seat is far off.

Two more things learned at this step:

- **60 questions can't resolve a 3-point gap.** Each question is worth 1.7
  points, and an accuracy on 60 questions is uncertain by roughly 5 points
  either way. The window was finer than the calibration set can measure.
- **The gap is itself informative.** JEV, sold as a fast "System One" model,
  beats every council model with reasoning switched off, including GPT-5.5 by
  12 points. Whether JEV reasons internally isn't public. I've asked TypeSafe,
  and the answer changes how the result should be read.

One candidate was dropped during calibration: `claude-sonnet-4-6` repeatedly
broke the answer format (writing its confidence as 99 instead of 0.99) and
missed 4 of 60 questions on both attempts, above the 5% limit.

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
F-matched Delphi final  -  F-small Delphi final (does council strength help?)
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
- A recorded-cost cap of **$30** pauses the run between questions rather than
  changing the protocol. Calibration estimated the run at $28.54, so the cap
  may be reached near the end; the last question started before the pause can
  overshoot it by a few cents.
- **Resuming.** Re-running picks up only what's unfinished: finished questions
  are skipped, and an unfinished one continues from the step it stopped on.
  Successful calls are never repeated.
- **Raising the cap** is an operational amendment, never a change to the frozen
  config. It's recorded in the results database with the date, the old and new
  cap, the spend at that point and the reason, and the analysis report prints
  every such amendment. Nothing else (models, prompts, questions, analysis)
  can change.
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
