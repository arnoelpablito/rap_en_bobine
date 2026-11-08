import argparse
import csv
import json
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import duckdb


BASE = Path(__file__).resolve().parent
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
WIKIDATA_QUERY = """
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
SELECT DISTINCT ?imdb_id WHERE {
    ?film wdt:P495 wd:Q142 ;   # Pays d'origine : France
          wdt:P364 wd:Q150 ;   # Français parmi les langues originales
          wdt:P345 ?imdb_id .  # Identifiant IMDb
}
"""

FILMS_QUERY = """
SELECT b.tconst AS imdb_id, b.originalTitle AS original_title,
       b.primaryTitle AS primary_title, TRY_CAST(b.startYear AS INTEGER) AS year,
       TRY_CAST(b.runtimeMinutes AS INTEGER) AS runtime_minutes, b.genres
FROM title_basics AS b
WHERE b.titleType = 'movie'
  AND TRY_CAST(b.startYear AS INTEGER) BETWEEN ? AND ?
  AND b.tconst IN (SELECT unnest(?::VARCHAR[]))
ORDER BY year, original_title, imdb_id
"""


def fetch_imdb_ids():
    params = urlencode({"query": WIKIDATA_QUERY, "format": "json"})
    request = Request(f"{WIKIDATA_ENDPOINT}?{params}", headers={
        "Accept": "application/sparql-results+json",
        "User-Agent": "FrenchFilmsIMDb/1.0 (French cinema research)",
    })
    with urlopen(request, timeout=75) as response:
        bindings = json.load(response)["results"]["bindings"]
    imdb_ids = sorted({row["imdb_id"]["value"] for row in bindings})
    if not imdb_ids:
        raise ValueError("La requête Wikidata a renvoyé une liste vide.")
    return imdb_ids


def write_csv(path, columns, rows):
    temporary = NamedTemporaryFile(mode="w", encoding="utf-8", newline="",
                                  dir=path.parent, prefix=f".{path.name}.", delete=False)
    temporary_path = Path(temporary.name)
    try:
        with temporary:
            writer = csv.writer(temporary)
            writer.writerow(columns)
            writer.writerows(rows)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Extrait les films français de la base IMDb locale.")
    parser.add_argument("--db", type=Path, default=BASE / "imdb.duckdb", help="Chemin de la base DuckDB.")
    parser.add_argument("--since", type=int, default=1985, help="Première année incluse (1985 par défaut).")
    parser.add_argument("--out", type=Path, default=BASE / "films_francais.csv", help="Chemin du CSV de sortie.")
    args = parser.parse_args()
    if not args.db.is_file():
        parser.error(f"Base introuvable : {args.db}")
    if args.db.resolve() == args.out.resolve():
        parser.error("Choisis un chemin de sortie distinct de celui de la base.")

    print("Recherche des identifiants IMDb dans Wikidata...", flush=True)
    try:
        imdb_ids = fetch_imdb_ids()
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Échec de la requête Wikidata : {error}\n")

    with duckdb.connect(str(args.db), read_only=True) as con:
        result = con.execute(FILMS_QUERY, [args.since, date.today().year, imdb_ids])
        columns = [column[0] for column in result.description]
        rows = result.fetchall()

    write_csv(args.out, columns, rows)
    print(f"{len(rows):,} films exportés dans {args.out.resolve()}")


if __name__ == "__main__":
    main()
