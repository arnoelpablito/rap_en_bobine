from pathlib import Path
from typing import Literal
import csv
import hashlib
import json
import time

import pandas as pd
from ollama import chat
from pydantic import BaseModel

INPUT = Path("../data/annotations.csv")
OUTPUT = Path("../data/cinema_entities_mistral.csv")
CHECKPOINT = Path("../data/annotations_mistral_checkpoint.csv")

MODEL = "ministral-3:8b"
LIMIT = 20  # First test: 20 annotations. Set to None for the full corpus.
PRINT_EVERY = 10
MAX_ERRORS = 3


class Work(BaseModel):
    title: str
    type: Literal["movie", "TV series"]


class Extraction(BaseModel):
    works: list[Work]


SYSTEM_PROMPT = """
You are analyzing cultural references in French rap lyrics.

You receive:
1. A lyric fragment from a French rap song.
2. An explanatory annotation written by Genius contributors.

Your task is to identify movies and TV series genuinely referenced by the lyric fragment.

Important rules:
- Analyze the lyric and annotation together.
- References may be explicit, indirect, metaphorical, or based on a fictional character.
- A movie title can also be an ordinary word, a person's name, a song, or a different cultural object.
- Do not assume a movie is referenced simply because a word matches a known movie title.
- Do not extract a movie mentioned in the annotation if it is merely an unrelated example, comparison, or explicitly rejected interpretation.
- Do not confuse references to books, historical events, musicians, or real people with references to movie adaptations.
- A character or scene may identify a work even when its title is not mentioned.
- Infer a work's title only when the available evidence identifies it sufficiently clearly.
- If multiple interpretations remain plausible, do not guess.
- Return all identifiable movie and TV series references.
- If there is no convincing reference, return an empty list.
- Return only the requested structured output.
"""


def fingerprint(fragment, annotation):
    text = json.dumps([fragment, annotation], ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_works(fragment, annotation):
    prompt = f"""
LYRIC FRAGMENT:
{fragment}

GENIUS ANNOTATION:
{annotation}

Identify the movie and TV series references genuinely supported by this lyric and its annotation.
Return an empty list if the evidence is insufficient.
"""

    response = chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        format=Extraction.model_json_schema(),
        options={"temperature": 0},
        keep_alive="30m"
    )

    result = Extraction.model_validate_json(response.message.content)
    seen = set()
    works = []

    for work in result.works:
        title = work.title.strip()
        key = (title.casefold(), work.type)

        if title and key not in seen:
            works.append({"title": title, "type": work.type})
            seen.add(key)

    return works


def save_output(df, results):
    rows = []

    for idx, row in df.iterrows():
        for work in results.get(idx, []):
            rows.append({
                "annotation_row": idx,
                **row.to_dict(),
                "work_title": work["title"],
                "work_type": work["type"],
                "model": MODEL
            })

    columns = ["annotation_row", *df.columns.tolist(), "work_title", "work_type", "model"]
    pd.DataFrame(rows, columns=columns).to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"\nSaved: {OUTPUT.name} ({len(rows):,} references)")
    print(f"Annotations processed: {len(results):,}/{len(df):,}")
    print(f"Annotations with references: {sum(bool(x) for x in results.values()):,}")


def main():
    df = pd.read_csv(INPUT, dtype=str, keep_default_na=False, encoding="utf-8-sig")

    if not {"fragment", "annotation"}.issubset(df.columns):
        raise ValueError("annotations.csv must contain 'fragment' and 'annotation' columns.")

    config = json.dumps({
        "model": MODEL,
        "prompt": SYSTEM_PROMPT,
        "schema": Extraction.model_json_schema(),
        "temperature": 0
    }, sort_keys=True, ensure_ascii=False)
    run_id = hashlib.sha256(config.encode("utf-8")).hexdigest()[:16]

    results = {}

    if CHECKPOINT.exists():
        with CHECKPOINT.open("r", encoding="utf-8", newline="") as f:
            for record in csv.DictReader(f):
                if record["run_id"] != run_id:
                    raise ValueError(
                        "Checkpoint created with another model or prompt. "
                        "Rename or delete it before starting a new experiment."
                    )

                idx = int(record["annotation_row"])

                if idx >= len(df):
                    continue

                row = df.iloc[idx]
                current_hash = fingerprint(row["fragment"], row["annotation"])

                if record["input_hash"] == current_hash:
                    results[idx] = json.loads(record["works_json"])

    print(f"Model: {MODEL}")
    print(f"Annotations: {len(df):,}")
    print(f"Already processed: {len(results):,}")

    fields = ["annotation_row", "run_id", "input_hash", "works_json"]
    new_file = not CHECKPOINT.exists()
    processed = 0
    consecutive_errors = 0
    started = time.time()

    try:
        with CHECKPOINT.open("a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)

            if new_file:
                writer.writeheader()
                f.flush()

            for idx, row in df.iterrows():
                if idx in results:
                    continue

                if LIMIT is not None and processed >= LIMIT:
                    break

                fragment = row["fragment"]
                annotation = row["annotation"]

                try:
                    works = extract_works(fragment, annotation)
                    consecutive_errors = 0
                except Exception as e:
                    consecutive_errors += 1
                    print(f"ERROR annotation {idx}: {e}")

                    if consecutive_errors >= MAX_ERRORS:
                        print("Too many consecutive errors. Stopping.")
                        break

                    continue

                writer.writerow({
                    "annotation_row": idx,
                    "run_id": run_id,
                    "input_hash": fingerprint(fragment, annotation),
                    "works_json": json.dumps(works, ensure_ascii=False)
                })
                f.flush()

                results[idx] = works
                processed += 1

                if works:
                    print(f"[{idx}] " + " | ".join(f"{w['title']} ({w['type']})" for w in works))

                if processed % PRINT_EVERY == 0:
                    elapsed = time.time() - started
                    rate = processed / elapsed
                    remaining = len(df) - len(results)
                    eta = remaining / rate / 60 if rate else 0

                    print(
                        f"Progress: {len(results):,}/{len(df):,} "
                        f"({len(results) / len(df):.1%}) | "
                        f"{rate * 60:.1f} annotations/min | ETA: {eta:.1f} min"
                    )

    except KeyboardInterrupt:
        print("\nInterrupted. Progress has been saved.")

    finally:
        save_output(df, results)


if __name__ == "__main__":
    main()