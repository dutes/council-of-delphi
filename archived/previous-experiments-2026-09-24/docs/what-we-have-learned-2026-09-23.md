# Council of Delphi: what we have learned so far

*Research note, 23 September 2026. This is a plain-language summary of completed
hosted-model experiments, not a claim that the approach has been proven in general.*

## The question we started with

Could several independent language models answer a question more reliably than
one model? And could JEV, acting only as a disagreement judge, decide when it
is worth asking those models to reconsider?

The project compares a single model, a first-round majority vote, and a Delphi
council. In the Delphi council, three independent agents answer first. JEV
judges their answers; a fixed Python rule then decides whether to stop or ask
for a second round. JEV never supplies the final answer.

## What the larger completed tests say

| Test | Initial vote | Delphi with JEV | Strongest single member | What it tells us |
| --- | ---: | ---: | ---: | --- |
| Phase 3R: 1,490 completed paired runs, drawn from 500 questions repeated three times | 72.62% | 80.87% | Google: 87.92% | Delphi helped the vote substantially, but still trailed Google alone. |
| Phase 5: 495 fully paired *new* questions | 71.11% | 80.40% | Google: 85.66% | The same broad pattern appeared on a fresh project holdout. |

Phase 3R is the clean rerun after earlier implementation and scoring problems
were addressed. Its 10 incomplete runs (0.67%) were retained. The earlier
pilots helped develop the system but should not be treated as independent
confirmation of its final performance. Phase 3R's better calibration numbers
for Delphi are exploratory because the vote and final confidence scores have
different meanings.

The important caution is that **“better than a three-model vote” is not the
same as “better than the best single model.”** In Phase 5, relative to the
Google member alone, the simple-route council rescued 6 questions but also
turned 31 Google-correct answers into wrong final answers.

## What JEV routing added

After inspecting Phase 3R, we suspected that a simple rule—escalate whenever
the initial answers disagree—might do as well as JEV routing. A small
follow-up on old questions supported that suspicion, but it was retrospective
and could not settle it. We therefore froze a **new, prospective Phase 5** test
on 500 previously unused questions. Both routing policies shared the same
initial answers and, when needed, the same peer-reconsideration outputs.

Of the 500 questions, 495 were fully paired; 5 exhausted the allowed retries.
This 1% missing rate stayed below the prespecified 2% analysis limit. On those
495 questions:

- JEV routing answered **398 correctly (80.40%)**.
- Simple disagreement routing answered **399 correctly (80.61%)**.
- The simple rule was better on one question; JEV was better on none.
- The prespecified paired analysis found the simple rule **noninferior** within
  a 2-percentage-point margin. This does **not** prove that the two policies
  are exactly equivalent, nor that the simple rule is universally superior.
- JEV alone called for a second round on 133 questions that the simple rule
  would have stopped; the simple rule alone escalated 8. The estimated
  policy cost was $0.011462 per question with JEV routing versus $0.010105
  with the simple rule. The full paired study, including control branches,
  recorded $8.2515 of estimated spend. These are not provider invoices.

For this council, dataset, and frozen threshold, **JEV did not earn its extra
routing complexity or cost**. That is a useful negative finding, not a failed
experiment.

## Was reconsideration itself useful?

Phase 5 also included an own-answer-only second round: each agent could revisit
its answer without seeing peers. Under JEV routing, peer reconsideration scored
398/495, compared with 385/495 for own-answer reconsideration. In paired
cases, peer exposure won 27 times and own-answer revision won 14 times. This
suggests that sharing reasoning may sometimes help; it is a **secondary,
exploratory** result, not proof that peer discussion is always beneficial.
Neither approach beat the Google single-member result overall.

## What remains uncertain

These are public benchmarks, so we cannot rule out questions appearing in
model training data. “Fresh” means unused in this project's earlier live
experiments. Hosted models and provider APIs may drift despite fixed model IDs
and temperature zero. Five Phase 5 questions were unresolved, though the
predeclared missingness check passed. Costs are frozen estimates; the latency
comparison is a service-time proxy, not measured end-to-end elapsed time.

The results do **not** tell us that JEV cannot help anywhere. They tell us
that it did not beat a very simple routing rule in this particular hosted
council. They also do not support a claim that this council is better than
its strongest member.

## Why try local models next?

One plausible hypothesis is that a disagreement judge may be more useful when
the underlying agents are weaker, more diverse, or face harder questions.
That remains a hypothesis. A local-model experiment would test it with much
lower hosted-agent spending, although computation time and electricity still
have costs. The next study should compare JEV routing with simple disagreement
routing and the **best local single-model baseline** on the same fresh
questions. It should also keep first-round outputs fixed across routing
policies, measure real wall time, and freeze model versions, quantization,
prompts, thresholds, and scoring before examining outcomes.

No local-model result exists yet. If a rule or model combination is chosen
after inspecting the current results, it must be tested on a separate holdout
before making a confirmatory claim.

## Source reports

- [Phase 3R final analysis](../reports/phase3r/465b46617632/final-analysis.txt)
- [Phase 3R exploratory routing follow-up](../reports/phase3r/465b46617632/routing-followup.txt)
- [Phase 5 preregistration](phase5-routing-preregistration.md)
- [Phase 5 final analysis](../reports/phase5-routing/final-analysis.txt)
