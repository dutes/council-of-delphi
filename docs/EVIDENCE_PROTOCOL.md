# Protocol: evidence-partitioned council and JEV arbitration

Author: Brian Doutey, independent researcher (no institutional affiliation)

Status: design draft before any API preflight or scored call.

## Research question

The completed crowd-to-council study found that JEV arbitration improved a
three-model council, but JEV answering alone was more accurate. This follow-up
tests the situation in which JEV cannot rely on prior knowledge because the
facts needed to answer are novel and distributed across independent models.

Primary question:

> Does JEV synthesis of partitioned specialist reports improve accuracy over
> JEV receiving the question without evidence?

Secondary questions ask whether report synthesis improves on a simple vote of
evidence-limited specialists, how closely it approaches JEV with all raw
evidence, and whether its cited evidence forms a complete and valid proof path.

## Dataset

The frozen sample will contain 300 locally generated four-choice questions.
Each question uses novel pseudonymous entities in a three-link chain:

```text
artifact -> vault -> sector -> clearance code
```

The correct answer requires all three links. Eighteen evidence statements are
generated per question: three indispensable support statements and fifteen
matched distractors. Each of the three providers receives exactly one support
statement and five distractors. No single provider receives a complete proof.
The mapping of proof links to providers, statement order, entity names, and
answer position are seed-controlled. Answer positions are exactly balanced to
within one item.

The synthetic design is deliberate: neither JEV nor a provider can know the
novel entity relationships from model training. Accuracy must come from the
supplied evidence.

## Models

The same non-reasoning slate as the completed v5 study is retained:

- OpenAI `gpt-4.1-mini-2025-04-14`;
- Anthropic `claude-haiku-4-5-20251001`;
- Mistral `ministral-14b-2512` (`reasoning: false` in account metadata);
- JEV `jev-latest` as question-only control and evidence arbiter.

## Frozen conditions

### A. JEV question-only

JEV receives the question and four answer choices but no evidence. This is the
primary control for direct prior knowledge or answer-position bias. Expected
performance is chance if the generator has no leakage.

### B. Evidence-limited specialist vote

Each provider receives its private six-statement partition, returns an answer
label, and reports potentially relevant facts with their evidence IDs. The
three labels receive one equal vote each. A 1-1-1 tie is resolved by frozen
question-specific hash ordering.

### C. JEV report synthesis

JEV receives anonymized provider reports, including guesses, visible
justifications, and cited evidence claims, but not the raw partitions or
provider identities. It selects an answer and identifies three evidence links.
This is the primary treatment.

### D. JEV with all raw evidence

JEV receives all eighteen raw evidence statements and selects an answer and
three evidence links. This estimates the ceiling when report extraction and
compression are removed.

## Outcomes

The primary estimand is the paired accuracy difference:

```text
JEV report synthesis - JEV question-only
```

Secondary estimands are:

```text
JEV report synthesis - specialist majority vote
JEV all-raw-evidence - JEV report synthesis
```

Auditability outcomes include:

- specialist citation validity: cited IDs exist in that specialist's partition;
- specialist support recall: its indispensable support ID was reported;
- JEV evidence precision: cited IDs belong to the true proof path;
- JEV complete-proof rate: all three support IDs were cited;
- report availability ceiling: all three support IDs appeared somewhere in the
  anonymized reports.

Accuracy differences use paired question bootstrap intervals with 10,000 draws.
The primary analysis is evaluable only if at least 98% of questions complete.

## Safeguards

- Ground truth and `is_support` flags remain local and are removed from every
  model-facing object.
- JEV never sees provider identities.
- Successful calls are never rerun; missing calls receive at most two attempts.
- No interim accuracy or auditability result is displayed.
- The dataset, implementation, prompt text, and analysis plan are hashed before
  scored calls.
- Preflight uses a separate synthetic question that is not in the frozen set.

## Interpretation boundaries

The synthetic benchmark isolates distributed evidence integration, not broad
real-world expertise. High performance would show that the system can assemble
novel facts across partitions. It would not establish that model-generated
reports are faithful on uncontrolled documents or that citations imply causal
reasoning. A later real-document study would be required for external validity.

## Independence and disclosure

This is Brian Doutey's personal project. No person or organization paid for,
commissioned, or influenced the work. The author reports no affiliation or
relationship with TypeSafe and no external funding.
