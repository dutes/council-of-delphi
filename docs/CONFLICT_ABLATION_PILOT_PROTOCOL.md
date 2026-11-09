# Engineering pilot: conflicting-evidence arbiter ablation

Author: Brian Doutey, independent researcher (no institutional affiliation)

Status: frozen before API calls. These 30 questions are engineering-only and
excluded from the confirmatory study.

## Purpose

The preceding active Delphi experiment showed that targeted retrieval can
recover a distributed evidence chain, but did not isolate whether JEV added
value because the retrieved evidence was conflict-free. This pilot validates a
controlled ablation in which every stage contains three mutually incompatible
claims with different provenance quality.

## Evidence policy and conditions

Problems use novel three-link chains. At every link, the arbiters receive the
same three anonymized candidate packets. Exactly one packet has the provenance
preferred by a fixed, visible policy: current over superseded; authenticated
primary over derivative or anonymous; direct observation over inference or
hearsay; genuinely independent corroboration over common-source duplication;
and final audited correction over preliminary, withdrawn, or rejected claims.

Four arbiters select from the identical closed set:

1. deterministic hash choice, representing a tied 1-1-1 vote;
2. a frozen keyword scoring rule;
3. non-reasoning OpenAI `gpt-4.1-mini-2025-04-14` prompted as a classifier;
4. JEV `jev-latest` using its native closed-set choice interface.

Candidate order is exactly balanced. Each arbiter judges all three stages
independently. A question-level path is correct only if all three choices are
correct. This deliberately removes specialist retrieval variability and
isolates arbitration.

## Engineering gates

- at least 29/30 questions complete for all arbiters;
- no hidden reasoning tokens are accepted;
- JEV and the OpenAI classifier each select at least 81/90 policy-preferred
  stage candidates;
- each correct-candidate position occurs exactly 30 times across 90 stages;
- no scored pilot item is reused in confirmation.

Pilot accuracy is a feasibility check, not confirmatory evidence. Any prompt,
policy, generator, parsing, or decision-rule change requires a new disjoint
confirmatory freeze.

## Interpretation boundary

The task tests classification under explicit provenance rules. It does not
establish factual truth from provenance, resistance to adversarial forged
metadata, or performance on uncontrolled natural documents.

## Independence

This is Brian Doutey's independent personal project. No person or organization
paid for, commissioned, or influenced the work. There is no affiliation with
TypeSafe and no external funding.

