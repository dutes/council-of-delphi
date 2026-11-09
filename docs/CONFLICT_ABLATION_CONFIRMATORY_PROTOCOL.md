# Confirmatory protocol: arbiter specificity under scope-aware conflict

Author: Brian Doutey, independent researcher (no institutional affiliation)

Status: frozen before confirmatory API calls.

## Research questions

When three mutually incompatible evidence packets require resolving provenance,
scope, negation, and chronology:

1. Does JEV outperform a fixed deterministic keyword rule?
2. Does JEV outperform, underperform, or perform equivalently to a capable
   non-reasoning language model prompted to apply the same policy?

The first paired contrast tests the value of semantic classification over a
simple rule. The second tests whether any benefit is specific to JEV.

## Design

The frozen dataset contains 300 new four-choice, three-link synthetic chains,
disjoint from both engineering pilots. Each stage presents the identical three
anonymized candidate packets to all arbiters. One packet is correct under the
visible policy, but misleading positive and negative provenance terms appear
in every class. Correct-candidate positions are exactly balanced: 300 instances
each of C1, C2, and C3 across 900 stages. Answer labels are exactly balanced.

Arbiters are:

- deterministic hash selection, representing a tied 1-1-1 vote;
- the unchanged frozen keyword rule;
- non-reasoning `gpt-4.1-mini-2025-04-14` at temperature zero;
- JEV `jev-latest` using native closed-set classification.

Every arbiter judges all stages independently. Stage accuracy is selection of
the policy-preferred packet. Question-level path accuracy requires all three
stages to be correct. This deliberately isolates arbitration from specialist
retrieval and controller behavior.

## Frozen analysis

The two named paired question-level contrasts are:

```text
JEV full-path accuracy - keyword-rule full-path accuracy
JEV full-path accuracy - OpenAI-classifier full-path accuracy
```

Hash-tie comparisons and stage-level accuracies are secondary. Paired-question
bootstrap 95% intervals use 10,000 draws. Results are evaluable with at least
98% complete questions. Equivalence is reported descriptively when the entire
JEV-minus-OpenAI interval lies inside a preregistered ±3 percentage-point band;
otherwise no equivalence claim is made.

No interim accuracy is displayed. Successful calls are not replaced. Missing
calls may receive at most two recorded attempts.

## Boundaries

The correct answer is defined by an explicit synthetic provenance policy. The
study does not prove that provenance guarantees factual truth, test forged
metadata, or establish performance on uncontrolled documents. It isolates
closed-set semantic arbitration, not open-ended reasoning or question writing.

## Independence

This is Brian Doutey's independent, unfunded personal project. No person or
organization paid for, commissioned, or influenced it. The author has no
affiliation with TypeSafe.

