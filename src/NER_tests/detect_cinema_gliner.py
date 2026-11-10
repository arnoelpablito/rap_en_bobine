import re
import time
import unicodedata

import pandas as pd
from gliner import GLiNER

BASE = "data"
INPUT = BASE / "annotations.csv"

OUT_ENTITIES = BASE / "cinema_entities_gliner.csv"
CHECKPOINT = BASE / "annotations_gliner_checkpoint.csv"

MODEL = "VAGOsolutions/SauerkrautLM-GLiNER"

LABELS = [
    "movie",
    "TV series"
]

THRESHOLD = 0.45
SAVE_EVERY = 100


def clean_text(x):
    return "" if pd.isna(x) else str(x)


def normalize_entity(x):
    x = unicodedata.normalize("NFKC", str(x or ""))
    x = x.replace("’", "'").replace("‘", "'").replace("\xa0", " ")
    x = re.sub(r"\s+", " ", x).strip(" \t\r\n\"“”«».,;:!?()[]")
    return x


def detect_entities(model, text):
    if not text.strip():
        return []

    entities = model.predict_entities(
        text,
        LABELS,
        threshold=THRESHOLD,
    )

    out = []
    seen = set()

    for e in entities:
        entity = normalize_entity(e.get("text", ""))
        label = str(e.get("label", "")).strip()
        score = float(e.get("score", 0))

        if not entity:
            continue

        key = (entity.casefold(), label.casefold())

        if key in seen:
            continue

        seen.add(key)

        out.append({
            "entity": entity,
            "entity_type": label,
            "gliner_score": score,
            "start": e.get("start"),
            "end": e.get("end"),
        })

    return out


def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    df = pd.read_csv(INPUT, encoding="utf-8-sig")

    if "annotation" not in df.columns:
        raise ValueError("annotations.csv doit contenir une colonne 'annotation'.")

    print(f"Chargement de {MODEL}...")
    model = GLiNER.from_pretrained(MODEL)

    print(f"{len(df):,} annotations à analyser")

    if CHECKPOINT.exists():
        previous = pd.read_csv(CHECKPOINT, encoding="utf-8-sig")
        done = set(previous["annotation_row"].astype(int))
        entity_rows = previous.to_dict("records")
        print(f"Reprise : {len(done):,} annotations déjà traitées")
    else:
        done = set()
        entity_rows = []

    initial_done = len(done)
    started = time.time()

    for idx, row in df.iterrows():
        if idx in done:
            continue

        text = clean_text(row["annotation"])
        entities = detect_entities(model, text)

        if entities:
            for e in entities:
                entity_rows.append({
                    "annotation_row": idx,
                    "corpus_index": row.get("corpus_index"),
                    "song_url": row.get("song_url"),
                    "referent_id": row.get("referent_id"),
                    "annotation_id": row.get("annotation_id"),
                    "fragment": row.get("fragment"),
                    "annotation": text,
                    **e,
                })

        else:
            # Marker used only for checkpoint/resume.
            entity_rows.append({
                "annotation_row": idx,
                "corpus_index": row.get("corpus_index"),
                "song_url": row.get("song_url"),
                "referent_id": row.get("referent_id"),
                "annotation_id": row.get("annotation_id"),
                "fragment": row.get("fragment"),
                "annotation": text,
                "entity": "",
                "entity_type": "",
                "gliner_score": None,
                "start": None,
                "end": None,
            })

        done.add(idx)

        processed_this_run = len(done) - initial_done

        if processed_this_run % SAVE_EVERY == 0 or len(done) == len(df):
            pd.DataFrame(entity_rows).to_csv(
                CHECKPOINT,
                index=False,
                encoding="utf-8-sig",
            )

            elapsed = time.time() - started
            rate = processed_this_run / elapsed if elapsed else 0
            remaining = (len(df) - len(done)) / rate if rate else 0

            print(
                f"{len(done):,}/{len(df):,} annotations "
                f"({len(done) / len(df):.1%}) - "
                f"ETA ~ {remaining / 60:.1f} min"
            )

    entities_df = pd.DataFrame(entity_rows)

    entities_df = entities_df[
        entities_df["entity"].fillna("").ne("")
    ].copy()

    entities_df = entities_df.sort_values(
        "gliner_score",
        ascending=False,
    )

    entities_df.to_csv(
        OUT_ENTITIES,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print(f"{len(entities_df):,} entités détectées par GLiNER")
    print(f"Saved: {OUT_ENTITIES}")


if __name__ == "__main__":
    main()