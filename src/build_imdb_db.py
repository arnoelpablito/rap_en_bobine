import duckdb

BASE = "data"
IMDB_DIR = BASE / "IMDb"
DB_PATH = BASE / "imdb.duckdb"

FILES = {
    "title_basics": "title.basics.tsv.gz",
    "title_akas": "title.akas.tsv.gz",
    "title_crew": "title.crew.tsv.gz",
    "title_episode": "title.episode.tsv.gz",
    "title_principals": "title.principals.tsv.gz",
    "title_ratings": "title.ratings.tsv.gz",
    "name_basics": "name.basics.tsv.gz",
}

missing = [f for f in FILES.values() if not (IMDB_DIR / f).exists()]
if missing:
    raise FileNotFoundError("Fichiers IMDb manquants:\n" + "\n".join(missing))

con = duckdb.connect(DB_PATH)
con.execute("SET preserve_insertion_order=false")
con.execute("SET threads=2")
con.execute("SET memory_limit='2GB'")

def q(path):
    return path.resolve().as_posix().replace("'", "''")

for table, filename in FILES.items():
    path = IMDB_DIR / filename
    exists = con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name=?",
        [table],
    ).fetchone()[0]

    if exists:
        print(f"{table}: déjà présent, ignoré")
        continue

    print(f"Import de {filename} -> {table}...")
    con.execute(f"""
        CREATE TABLE {table} AS
        SELECT *
        FROM read_csv(
            '{q(path)}',
            delim='\\t',
            header=true,
            nullstr='\\\\N',
            all_varchar=true,
            compression='gzip'
        )
    """)
    n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    print(f"  {n:,} lignes")
    con.execute("CHECKPOINT")

print("Création de la table de recherche des titres...")

con.execute("DROP TABLE IF EXISTS imdb_search_titles")
con.execute("""
CREATE TABLE imdb_search_titles AS
WITH x AS (
    SELECT tconst, titleType, primaryTitle AS title, 'primary' AS source
    FROM title_basics
    WHERE primaryTitle IS NOT NULL

    UNION ALL

    SELECT tconst, titleType, originalTitle AS title, 'original' AS source
    FROM title_basics
    WHERE originalTitle IS NOT NULL

    UNION ALL

    SELECT a.titleId AS tconst, b.titleType, a.title, 'aka_fr' AS source
    FROM title_akas a
    JOIN title_basics b ON b.tconst=a.titleId
    WHERE a.title IS NOT NULL
      AND (a.region='FR' OR a.language='fr')
)
SELECT DISTINCT tconst, titleType, title, source
FROM x
WHERE length(trim(title)) >= 2
""")

con.execute("CHECKPOINT")

print("\nTerminé.")
print(f"Base: {DB_PATH}")
print("Tables:")
for row in con.execute("SHOW TABLES").fetchall():
    print(" -", row[0])

con.close()
