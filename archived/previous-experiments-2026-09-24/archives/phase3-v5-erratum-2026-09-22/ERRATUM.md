# Phase 3 v5 Erratum

Date: 2026-09-22  
Affected experiment: `82ad9fb9945d`  
Original archive: `archives/phase3-v5-confirmatory-2026-09-22`  
Status: preserved but reclassified as compromised/exploratory

The original archive has not been edited. Its checksum manifest remains the chain
of custody for the exact code, database, data, and reports used in Phase 3 v5.

## Material findings

1. The production JEV adapter serialized the complete `Question`, including
   `correct_answer` and metadata. JEV only routed escalation and did not generate
   the final answer, but this is ground-truth leakage into the treatment mechanism.
2. The frozen `objective-v1` scorer used generic exact equivalence for free-response
   data. It marked many semantically correct GSM1k answers with units/currency and
   BBEH formatting variants as incorrect.
3. Successful provider responses did not retain enough provenance to reconstruct
   the resolved model, request ID, finish reason, detailed usage, and raw response.
4. Provider output caps were unequal, and invoice-level JEV cost was not fully
   represented in the aggregate cost estimate.

## Consequence

The reported 75.7% accuracy and estimated Delphi improvement cannot be treated as a
clean confirmatory estimate. An audit-only rescoring sensitivity changed the paired
summary from approximately 65.2% vote versus 75.7% Delphi to approximately 69.4%
versus 82.7%. This supports neither value as definitive: the treatment routing was
already exposed to ground truth, and the rescoring rules were created after seeing
the data.

The defensible conclusion is limited to: the archived run provided evidence that a
clean, preregistered rerun was warranted. It does not establish H1a.

## Corrective action

Phase 3R uses a fresh non-overlapping 500-question dataset, three repetitions,
source-aware frozen scoring, equal output caps, full response provenance, and a
strict allowlisted JEV payload that excludes ground truth and model identity. See
`PHASE3R_PREREGISTRATION.md` and `configs/phase3r_final_v1.json`.
