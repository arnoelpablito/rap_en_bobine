import json
import os
import random
import re
import shutil
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CORPUS_PATH = Path("data/corpus.csv")
LONG_PATH = Path("data/annotations.csv")
BACKUP_PATH = Path("data/corpus_before_annotations.csv")

SAVE_EVERY = 100
REQUEST_DELAY = (0.6, 1.0)
TIMEOUT = 30
MAX_REFERENTS_PER_REQUEST = 40

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}


def build_session():
    session = requests.Session()
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        status=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(HEADERS)
    return session


def sleep_between_requests():
    time.sleep(random.uniform(*REQUEST_DELAY))


def chunks(values, n):
    for i in range(0, len(values), n):
        yield values[i:i + n]


def extract_referent_ids(page_html):
    """Extract Genius referent IDs from the annotated lyric fragments in a song page."""
    soup = BeautifulSoup(page_html, "html.parser")
    ids = []

    # Current Genius markup: numeric annotation links inside lyrics containers.
    for container in soup.select("div[data-lyrics-container='true']"):
        for a in container.select("a[href]"):
            href = a.get("href", "")
            match = re.search(r"(?:https?://(?:www\.)?genius\.com)?/(\d+)/", href)
            if match:
                ids.append(int(match.group(1)))

    # Fallback for markup embedded in the preloaded state.
    if not ids:
        ids = [int(x) for x in re.findall(r'data-id=\\?"(\d+)\\?"', page_html)]

    return list(dict.fromkeys(ids))


def extract_song_id(page_html):
    """Useful for diagnostics; annotations themselves are fetched from referent IDs."""
    match = re.search(r'genius://songs/(\d+)', page_html)
    if not match:
        match = re.search(r'\\"song_id\\":(\d+)', page_html)
    if not match:
        match = re.search(r'"song_id"\s*:\s*(\d+)', page_html)
    return int(match.group(1)) if match else None


def fetch_song_page(session, url):
    response = session.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    return response.text


def fetch_referents(session, referent_ids):
    """
    Genius currently exposes a grouped referent endpoint used by its web client.
    One request can return several lyric fragments and their attached annotations.
    """
    referents = []
    for batch in chunks(referent_ids, MAX_REFERENTS_PER_REQUEST):
        params = [("text_format", "plain")] + [("ids[]", str(x)) for x in batch]
        response = session.get(
            "https://genius.com/api/referents/multi",
            params=params,
            headers={"X-Requested-With": "XMLHttpRequest"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        raw = payload.get("response", {}).get("referents", [])
        # Genius is inconsistent here: depending on the request/page, `referents`
        # can be either a JSON array OR an object keyed by referent ID.
        if isinstance(raw, dict):
            raw = list(raw.values())
        elif not isinstance(raw, list):
            raw = []
        referents.extend(x for x in raw if isinstance(x, dict))
        sleep_between_requests()
    return referents


def rich_text_to_plain(body):
    if isinstance(body, str):
        return body.strip()
    if not isinstance(body, dict):
        return ""
    if body.get("plain"):
        return str(body["plain"]).strip()
    if body.get("html"):
        return BeautifulSoup(body["html"], "html.parser").get_text("\n", strip=True)
    if body.get("markdown"):
        return str(body["markdown"]).strip()
    return ""


def parse_referents(referents, song_url, corpus_index):
    rows = []
    for ref in referents:
        if not isinstance(ref, dict):
            continue
        fragment = str(ref.get("fragment") or "").strip()
        ref_id = ref.get("id")
        classification = ref.get("classification")
        annotations = ref.get("annotations") or []
        if isinstance(annotations, dict):
            annotations = list(annotations.values())
        elif not isinstance(annotations, list):
            annotations = []

        for ann in annotations:
            if not isinstance(ann, dict):
                continue
            text = rich_text_to_plain(ann.get("body"))
            if not text:
                continue

            rows.append({
                "corpus_index": corpus_index,
                "song_url": song_url,
                "referent_id": ref_id,
                "annotation_id": ann.get("id"),
                "fragment": fragment,
                "annotation": text,
                "classification": classification,
                "annotation_state": ann.get("state"),
                "verified": ann.get("verified"),
                "votes_total": ann.get("votes_total"),
                "annotation_url": ann.get("url") or ann.get("share_url"),
            })
    return rows


def scrape_song_annotations(session, song_url, corpus_index):
    page_html = fetch_song_page(session, song_url)
    referent_ids = extract_referent_ids(page_html)
    song_id = extract_song_id(page_html)

    if not referent_ids:
        return song_id, [], "no_annotations"

    referents = fetch_referents(session, referent_ids)
    annotations = parse_referents(referents, song_url, corpus_index)

    # A highlighted fragment can exist without a completed annotation.
    status = "ok" if annotations else "referents_without_annotation"
    return song_id, annotations, status


def serialize_song_annotations(annotation_rows):
    compact = [
        {
            "referent_id": r["referent_id"],
            "annotation_id": r["annotation_id"],
            "fragment": r["fragment"],
            "annotation": r["annotation"],
            "classification": r["classification"],
            "verified": r["verified"],
            "votes_total": r["votes_total"],
        }
        for r in annotation_rows
    ]
    return json.dumps(compact, ensure_ascii=False)


def checkpoint(corpus, long_rows):
    tmp = CORPUS_PATH.with_suffix(".csv.tmp")
    corpus.to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, CORPUS_PATH)

    if long_rows:
        long_df = pd.DataFrame(long_rows)
        if LONG_PATH.exists():
            old = pd.read_csv(LONG_PATH, encoding="utf-8-sig")
            long_df = pd.concat([old, long_df], ignore_index=True)

        if "annotation_id" in long_df.columns:
            has_id = long_df["annotation_id"].notna()
            with_id = long_df.loc[has_id].drop_duplicates("annotation_id", keep="last")
            without_id = long_df.loc[~has_id].drop_duplicates(
                ["song_url", "referent_id", "fragment", "annotation"], keep="last"
            )
            long_df = pd.concat([with_id, without_id], ignore_index=True)

        tmp_long = LONG_PATH.with_suffix(".csv.tmp")
        long_df.to_csv(tmp_long, index=False, encoding="utf-8-sig")
        os.replace(tmp_long, LONG_PATH)


def main():
    if not CORPUS_PATH.exists():
        raise FileNotFoundError(f"{CORPUS_PATH} not found")

    corpus = pd.read_csv(CORPUS_PATH, encoding="utf-8-sig")

    if "url" not in corpus.columns:
        raise ValueError("corpus.csv must contain a 'url' column with Genius song URLs.")

    if not BACKUP_PATH.exists():
        shutil.copy2(CORPUS_PATH, BACKUP_PATH)

    defaults = {
        "genius_song_id": pd.NA,
        "n_annotations": pd.NA,
        "annotation_fragments": pd.NA,
        "annotations_text": pd.NA,
        "annotations_json": pd.NA,
        "annotations_status": pd.NA,
    }
    for column, default in defaults.items():
        if column not in corpus.columns:
            corpus[column] = default

    # Resume safely: completed rows are skipped; errors are retried on the next run.
    completed = {"ok", "no_annotations", "referents_without_annotation"}
    todo = corpus.index[~corpus["annotations_status"].isin(completed)].tolist()

    print(f"{len(corpus):,} songs in corpus")
    print(f"{len(todo):,} songs remaining")

    session = build_session()
    new_long_rows = []

    for n, idx in enumerate(todo, start=1):
        url = str(corpus.at[idx, "url"]).strip()

        try:
            song_id, rows, status = scrape_song_annotations(session, url, idx)

            corpus.at[idx, "genius_song_id"] = song_id
            corpus.at[idx, "n_annotations"] = len(rows)
            corpus.at[idx, "annotation_fragments"] = json.dumps(
                [r["fragment"] for r in rows], ensure_ascii=False
            )
            corpus.at[idx, "annotations_text"] = "\n\n--- ANNOTATION ---\n\n".join(
                r["annotation"] for r in rows
            )
            corpus.at[idx, "annotations_json"] = serialize_song_annotations(rows)
            corpus.at[idx, "annotations_status"] = status

            new_long_rows.extend(rows)
            print(f"[{n}/{len(todo)}] {idx}: {len(rows)} annotation(s) - {url}")

        except requests.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "?"
            corpus.at[idx, "annotations_status"] = f"http_error_{code}"
            print(f"[{n}/{len(todo)}] HTTP {code}: {url}")

            # Do not hammer Genius if rate-limited.
            if code == 429:
                time.sleep(60)

        except Exception as exc:
            corpus.at[idx, "annotations_status"] = f"error_{type(exc).__name__}"
            print(f"[{n}/{len(todo)}] ERROR {type(exc).__name__}: {url} -> {exc}")

        sleep_between_requests()

        if n % SAVE_EVERY == 0:
            checkpoint(corpus, new_long_rows)
            new_long_rows = []
            print(f"Checkpoint saved after {n} processed songs.")

    checkpoint(corpus, new_long_rows)

    print("\nDone.")
    print(f"Updated: {CORPUS_PATH}")
    print(f"Long-format annotations: {LONG_PATH}")
    print(f"Original backup: {BACKUP_PATH}")


if __name__ == "__main__":
    main()
