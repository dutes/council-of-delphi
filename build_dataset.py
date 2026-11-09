"""Build a fresh 500-question MC sample, excluding quarantined project data."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import duckdb


SEED = 20260924
OUTPUT = Path("data/arbiter_500.jsonl")
MANIFEST = Path("data/arbiter_500.manifest.json")
ARCHIVE = Path("archived/previous-experiments-2026-09-24")
SOURCES = {
    "mmlu_pro": {
        "dataset": "TIGER-Lab/MMLU-Pro", "revision": "b189ec765aa7ed75c8acfea42df31fdae71f97be",
        "config": "default", "split": "test", "count": 400,
    },
    "arc_challenge": {
        "dataset": "allenai/ai2_arc", "revision": "210d026faf9955653af8916fad021475a3f00453",
        "config": "ARC-Challenge", "split": "test", "count": 100,
    },
}


def get_json(url: str) -> dict:
    last = None
    for attempt in range(7):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "jev-arbiter-study/0.1"})
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except Exception as exc:
            last = exc
            if attempt < 6:
                time.sleep(min(20, 2 ** attempt))
    raise RuntimeError(f"Could not fetch {url}: {last}")


def fetch(source: dict) -> list[dict]:
    metadata = get_json(f"https://huggingface.co/api/datasets/{source['dataset']}")
    if metadata.get("sha") != source["revision"]:
        raise RuntimeError(
            f"Pinned revision changed for {source['dataset']}: {metadata.get('sha')}"
        )
    query = urllib.parse.urlencode({"dataset": source["dataset"]})
    parquet = get_json(f"https://datasets-server.huggingface.co/parquet?{query}")
    files = [item for item in parquet["parquet_files"]
             if item["config"] == source["config"] and item["split"] == source["split"]]
    if not files:
        raise RuntimeError(f"No parquet shard for {source['dataset']} {source['config']}/{source['split']}")
    cache = Path(".dataset-cache")
    cache.mkdir(exist_ok=True)
    entries: list[dict] = []
    offset = 0
    for item in files:
        local = cache / f"{source['dataset'].replace('/', '--')}--{item['filename']}"
        if not local.exists():
            urllib.request.urlretrieve(item["url"], local)
        connection = duckdb.connect()
        cursor = connection.execute("SELECT * FROM read_parquet(?)", [str(local)])
        names = [column[0] for column in cursor.description]
        for values in cursor.fetchall():
            entries.append({"row_idx": offset, "row": dict(zip(names, values, strict=True))})
            offset += 1
        connection.close()
    return entries


def exclusions() -> tuple[set[tuple[str, int]], set[str]]:
    keys: set[tuple[str, int]] = set()
    texts: set[str] = set()
    for path in ARCHIVE.rglob("*.jsonl"):
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                metadata = row.get("metadata", {})
                if "source" in metadata and "source_row_index" in metadata:
                    keys.add((str(metadata["source"]), int(metadata["source_row_index"])))
                if "question" in row:
                    texts.add(str(row["question"]).strip())
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    return keys, texts


def rank(source: str, index: int) -> str:
    return hashlib.sha256(f"{SEED}:{source}:{index}".encode()).hexdigest()


def select_mmlu(rows: list[dict], count: int) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for entry in rows:
        category = entry["row"]["category"]
        if category not in {"health", "law"}:
            groups[category].append(entry)
    names = sorted(groups)
    base, remainder = divmod(count, len(names))
    selected = []
    for position, name in enumerate(names):
        quota = base + (position < remainder)
        selected.extend(sorted(groups[name], key=lambda e: rank("mmlu_pro", e["row_idx"]))[:quota])
    if len(selected) != count:
        raise RuntimeError("MMLU strata could not supply the requested count")
    return selected


def convert(source: str, entry: dict) -> dict:
    row, index = entry["row"], int(entry["row_idx"])
    if source == "mmlu_pro":
        choices = list(row["options"])
        correct_index = int(row["answer_index"])
        category, source_id = row["category"], row["question_id"]
    else:
        choices = list(row["choices"]["text"])
        labels = list(row["choices"]["label"])
        correct_index = labels.index(row["answerKey"])
        category, source_id = "science", row["id"]
    return {
        "id": f"arbiter-{source}-{index:05d}", "question": row["question"],
        "choices": choices, "correct_label": chr(ord("A") + correct_index),
        "metadata": {
            "source": source, "source_row_index": index, "category": category,
            "source_question_id": source_id, "source_revision": SOURCES[source]["revision"],
        },
    }


def main() -> None:
    if OUTPUT.exists() or MANIFEST.exists():
        raise FileExistsError("Active dataset already exists; never overwrite it")
    excluded_keys, excluded_texts = exclusions()
    fetched = {name: fetch(spec) for name, spec in SOURCES.items()}
    eligible = {
        name: [entry for entry in rows
               if (name, int(entry["row_idx"])) not in excluded_keys
               and str(entry["row"]["question"]).strip() not in excluded_texts]
        for name, rows in fetched.items()
    }
    selected = [*select_mmlu(eligible["mmlu_pro"], 400)]
    selected_arc = sorted(
        eligible["arc_challenge"], key=lambda e: rank("arc_challenge", e["row_idx"])
    )[:100]
    questions = [convert("mmlu_pro", entry) for entry in selected]
    questions += [convert("arc_challenge", entry) for entry in selected_arc]
    questions.sort(key=lambda q: rank(q["metadata"]["source"], q["metadata"]["source_row_index"]))
    if len(questions) != 500 or len({q["question"] for q in questions}) != 500:
        raise RuntimeError("Fresh dataset is not 500 unique questions")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("".join(json.dumps(q, ensure_ascii=False, separators=(",", ":")) + "\n"
                              for q in questions), encoding="utf-8", newline="\n")
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    manifest = {
        "version": "jev-arbiter-fresh-mc-500-v1", "seed": SEED,
        "question_count": 500, "sha256": digest,
        "source_counts": dict(Counter(q["metadata"]["source"] for q in questions)),
        "source_revisions": {name: spec["revision"] for name, spec in SOURCES.items()},
        "quarantine_exclusions": {"source_rows": len(excluded_keys), "question_texts": len(excluded_texts)},
        "overlap_with_quarantine": 0,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote 500 fresh questions: {digest}")


if __name__ == "__main__":
    main()
