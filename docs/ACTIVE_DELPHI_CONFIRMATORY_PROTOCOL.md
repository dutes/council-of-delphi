# Confirmatory protocol: JEV-classified active Delphi retrieval

Author: Brian Doutey, independent researcher (no institutional affiliation)

Status: preregistered and frozen before preflight or scored calls.

## Question and prediction

Does an iterative evidence process controlled by closed-set JEV classifications
outperform one-round specialist summaries when indispensable novel facts are
distributed across three non-reasoning language models?

The primary estimand is paired answer accuracy:

```text
active JEV-classified retrieval - one-round JEV report synthesis
```

The directional prediction is positive.

## Dataset and rotation

There are 300 locally generated four-choice questions using novel entity names
and a three-link artifact-to-clearance chain. Each provider receives one true
link and five distractors. The six assignments of link positions to providers
occur exactly 50 times each; consequently every provider occupies every link
position exactly 100 times. Answer labels occur exactly 75 times each. The
dataset is disjoint from the 30-question engineering pilot.

## Models

- OpenAI `gpt-4.1-mini-2025-04-14`;
- Anthropic `claude-haiku-4-5-20251001`;
- Mistral `ministral-14b-2512`, reasoning disabled;
- JEV `jev-latest`, used only through closed-set choice classifications.

## Frozen conditions

1. **JEV question-only:** question and choices, without evidence.
2. **Specialist vote:** one full-question report per private partition; plurality
   with deterministic hash tie-breaking.
3. **One-round synthesis:** JEV classifies the answer from the three anonymized
   reports produced in condition 2.
4. **All raw evidence:** JEV classifies the answer with all 18 statements.
5. **Active retrieval:** a deterministic three-stage controller asks all three
   specialists for the next exact relationship. JEV chooses a single action
   from `accept_E##`, `retry`, or `halt_unresolved`. An accepted evidence
   object's object becomes the next stage's subject. JEV writes neither the
   requests nor the final answer. There are at most two semantic retrieval
   attempts per stage.

The active condition uses the controller frozen and tested in the engineering
pilot without changing its prompts or decision rules.

## Outcomes and analysis

Primary: active minus one-round synthesis. Secondary paired effects: active
minus specialist vote, active minus question-only, all-raw minus active.
Intervals are paired-question bootstrap 95% intervals with 10,000 draws.
The analysis is evaluable if at least 98% of questions have every condition.

Audit outcomes include active full-path completion, accepted-link validity,
accepted true-support precision, one-round support availability, and provider
support recall. No interim accuracy is displayed. Successful calls are reused.
Operations may be resumed, but model outputs are never replaced after success.

## Interpretation limits

This study tests routing over synthetic, structured, conflict-free facts. It
does not establish open-ended question generation, reliability on uncontrolled
documents, or resolution of genuinely contradictory evidence.

## Independence and disclosure

This is Brian Doutey's personal project. No person or organization paid for,
commissioned, or influenced the work. The author reports no affiliation or
relationship with TypeSafe and no external funding.

