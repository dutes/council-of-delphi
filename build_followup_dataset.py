"""Build the follow-up study's questions: 500 for the run and 60 for calibration.

Same sources, pinned revisions and category exclusions as the first study
(build_dataset.py). Excludes every question the project has used before: the
first study's 500, and everything in the quarantined archive. Never overwrites
an existing file.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from build_dataset import SOURCES, convert, exclusions, fetch


SEED = 20261118
MAIN = Path("data/followup_500.jsonl")
CALIBRATION = Path("data/followup_calibration_60.jsonl")
MANIFEST = Path("data/followup.manifest.json")
EARLIER = (Path("data/arbiter_500.jsonl"),)
MAIN_COUNTS = {"mmlu_pro": 400, "arc_challenge": 100}
CALIBRATION_COUNTS = {"mmlu_pro": 48, "arc_challenge": 12}


def rank(scope: str, source: str, index: int) -> str:
    return hashlib.sha256(f"followup:{SEED}:{scope}:{source}:{index}".encode()).hexdigest()


def earlier_questions() -> tuple[set[tuple[str, int]], set[str]]:
    keys, texts = exclusions()  # the quarantined archive, as in the first study
    for path in EARLIER:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                keys.add((row["metadata"]["source"], int(row["metadata"]["source_row_index"])))
                texts.add(row["question"].strip())
    return keys, texts


def stratified_mmlu(rows: list[dict], count: int, scope: str) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for entry in rows:
        if entry["row"]["category"] not in {"health", "law"}:
            groups[entry["row"]["category"]].append(entry)
    names = sorted(groups)
    base, remainder = divmod(count, len(names))
    chosen = []
    for position, name in enumerate(names):
        quota = base + (position < remainder)
        chosen.extend(sorted(groups[name], key=lambda e: rank(scope, "mmlu_pro", e["row_idx"]))[:quota])
    if len(chosen) != count:
        raise RuntimeError("MMLU-Pro strata could not supply the requested count")
    return chosen


def write(path: Path, questions: list[dict]) -> str:
    path.write_text("".join(json.dumps(q, ensure_ascii=False, separators=(",", ":")) + "\n" for q in questions),
                    encoding="utf-8", newline="\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    for path in (MAIN, CALIBRATION, MANIFEST):
        if path.exists():
            raise FileExistsError(f"{path} already exists; never overwrite a study dataset")
    excluded_keys, excluded_texts = earlier_questions()
    fetched = {name: fetch(spec) for name, spec in SOURCES.items()}
    eligible = {name: [e for e in rows
                       if (name, int(e["row_idx"])) not in excluded_keys
                       and str(e["row"]["question"]).strip() not in excluded_texts]
                for name, rows in fetched.items()}

    # Calibration first, then the main sample from what's left, so the two can never overlap.
    calibration = stratified_mmlu(eligible["mmlu_pro"], CALIBRATION_COUNTS["mmlu_pro"], "calibration")
    taken = {e["row_idx"] for e in calibration}
    main_mmlu = stratified_mmlu([e for e in eligible["mmlu_pro"] if e["row_idx"] not in taken],
                                MAIN_COUNTS["mmlu_pro"], "main")
    arc = sorted(eligible["arc_challenge"], key=lambda e: rank("arc", "arc_challenge", e["row_idx"]))
    calibration_arc = arc[:CALIBRATION_COUNTS["arc_challenge"]]
    main_arc = arc[CALIBRATION_COUNTS["arc_challenge"]:][:MAIN_COUNTS["arc_challenge"]]

    def build(mmlu: list[dict], arc_rows: list[dict], scope: str) -> list[dict]:
        out = [convert("mmlu_pro", e) for e in mmlu] + [convert("arc_challenge", e) for e in arc_rows]
        for q in out:
            q["id"] = q["id"].replace("arbiter-", f"followup-{scope}-", 1)
        out.sort(key=lambda q: rank(scope, q["metadata"]["source"], q["metadata"]["source_row_index"]))
        return out

    main_questions = build(main_mmlu, main_arc, "main")
    calibration_questions = build(calibration, calibration_arc, "calibration")
    texts = [q["question"] for q in main_questions + calibration_questions]
    if len(main_questions) != 500 or len(calibration_questions) != 60 or len(set(texts)) != 560:
        raise RuntimeError("Expected 500 + 60 unique questions")
    if set(texts) & excluded_texts:
        raise RuntimeError("A previously used question slipped through")

    Path("data").mkdir(exist_ok=True)
    main_sha = write(MAIN, main_questions)
    calibration_sha = write(CALIBRATION, calibration_questions)
    MANIFEST.write_text(json.dumps({
        "version": "delphi-followup-v1", "seed": SEED,
        "main": {"path": str(MAIN.as_posix()), "question_count": 500, "sha256": main_sha,
                 "source_counts": dict(Counter(q["metadata"]["source"] for q in main_questions))},
        "calibration": {"path": str(CALIBRATION.as_posix()), "question_count": 60, "sha256": calibration_sha,
                        "source_counts": dict(Counter(q["metadata"]["source"] for q in calibration_questions))},
        "source_revisions": {name: spec["revision"] for name, spec in SOURCES.items()},
        "excluded": {"source_rows": len(excluded_keys), "question_texts": len(excluded_texts)},
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Main sample: 500 questions, sha256 {main_sha}")
    print(f"Calibration set: 60 questions, sha256 {calibration_sha}")


if __name__ == "__main__":
    main()
