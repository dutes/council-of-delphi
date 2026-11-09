# Phase 6 v2 operational erratum

Phase 6 v2 was stopped after its ten-question operational check. It is **not**
an accuracy study and its six complete pairs must not be pooled with v3.

- Frozen v2 lock: `configs/phase6_local_locked_v2.json`.
- Original call records: `phase6-local-v2-results.sqlite3` (SHA-256
  `d6551446f966435fea24950e6dcd84de65ec9c1354edb4e47c54dde5d3e9ee6d`
  at closure). The database and lock remain in their original locations.
- Ten distinct v2 questions were called. Six were fully paired. Four were
  unresolved after both allowed attempts, for eight failed call records.
- The same three `qwen3:4b` and one `gemma3:4b` first-round responses were
  cut off at `num_predict=2048` on both attempts (`done_reason=length`).
  Their JSON reasoning strings were incomplete. No partial answer was scored.
- This is a 40% operational missingness rate among attempted questions,
  above the preregistered 5% study limit. The remaining 180 questions were
  never called and are reserved for a separately frozen v3 design.
- No interim accuracy was calculated or used to change the holdout.

The v3 output constraint was tested only on already-excluded questions before
v3 freezing. Do not resume or analyse v2 as a confirmatory study.
