# Phase 6 local v1: aborted operational check

The first `--limit 10` execution on 23 September 2026 produced **zero fully
paired questions**. It must not be analyzed as an accuracy experiment or
resumed under the original freeze. The original SQLite database, lock,
preflight, and progress report are preserved in this directory. The v1 source
files remain at their original project paths.

Two problems were observed before looking at final-answer accuracy:

1. In the initial/model-major loop, the runner tested whether *any* answer
   existed for the question, instead of whether the **current agent** had
   answered. Thus a valid Qwen answer caused Gemma and Phi to be skipped.
   The database contains 7 Qwen, 2 Gemma, 1 Phi, and 10 larger-single valid
   answers, plus 4 failed structured responses; no three-member council or
   JEV judgment was completed.
2. Four responses ended with `done_reason=length` and `eval_count=512`. The
   model output JSON was truncated mid-string at the frozen output cap.

These findings came from an operational `--limit 10` stage. The ten touched
questions are excluded from the new v2 scored sample. The fix is a new
versioned runner, larger output cap, new dataset manifest, new lock, and a
fresh excluded preflight; the v1 database is never merged into v2.
