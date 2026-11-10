# TAKES fr.zip and takes the subtitles that actually interest us (by comparing id with films_francais.csv)


import argparse
import csv
import io
import re
import shutil
from collections import defaultdict
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import BadZipFile, ZipFile


DOCUMENT = re.compile(r"(?:^|/)fr/[^/]+/(?:tt)?([0-9]+)/([0-9]+)(\.xml(?:\.gz)?)\Z")
COLUMNS = ("imdb_id", "imdb_url", "original_title", "year", "statut", "subtitle_id", "fichier_local")


def read_films(path):
    films = {}
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if "imdb_id" not in (reader.fieldnames or []):
            raise ValueError(f"La colonne imdb_id est absente de {path}.")
        for row in reader:
            imdb_id = (row["imdb_id"] or "").strip().lower()
            if not re.fullmatch(r"tt[0-9]+", imdb_id):
                raise ValueError(f"Identifiant IMDb invalide à la ligne {reader.line_num} du CSV.")
            number = imdb_id[2:].lstrip("0") or "0"
            films.setdefault(number, {
                "imdb_id": imdb_id,
                "imdb_url": f"https://www.imdb.com/title/{imdb_id}/",
                "original_title": row.get("original_title", ""),
                "year": row.get("year", ""),
            })
    if not films:
        raise ValueError(f"La liste de films est vide dans {path}.")
    return films


def index_documents(archive, films):
    documents = defaultdict(dict)
    has_french_documents = False
    for member in archive.infolist():
        match = DOCUMENT.search(member.filename)
        if not match:
            continue
        has_french_documents = True
        imdb_number, subtitle_id, suffix = match.groups()
        imdb_number = imdb_number.lstrip("0") or "0"
        if imdb_number in films:
            documents[imdb_number].setdefault(subtitle_id, (member, suffix))
    if not has_french_documents:
        raise ValueError("Choisis l'archive XML française d'OPUS avec des chemins fr/année/IMDb/fichier.xml.gz.")
    return documents


def write_file(destination, source):
    temporary = NamedTemporaryFile(dir=destination.parent, prefix=".part-", delete=False)
    temporary_path = Path(temporary.name)
    try:
        with temporary:
            shutil.copyfileobj(source, temporary)
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Extrait les sous-titres d'OPUS pour les films de ton CSV IMDb.")
    parser.add_argument("--films", type=Path, default=Path("../data/films_francais.csv"), help="CSV avec la colonne imdb_id.")
    parser.add_argument("--archive", type=Path, default=Path("../data/fr.zip"), help="Archive ZIP XML française d'OpenSubtitles v2024.")
    parser.add_argument("--out", type=Path, default=Path("../data/opus_fr"), help="Dossier de sortie.")
    args = parser.parse_args()
    index_path = args.out / "index_sous_titres.csv"
    if index_path.resolve() in (args.films.resolve(), args.archive.resolve()):
        parser.error("Choisis un dossier de sortie distinct des fichiers d'entrée.")

    try:
        films = read_films(args.films)
        with ZipFile(args.archive) as archive:
            documents = index_documents(archive, films)
            args.out.mkdir(parents=True, exist_ok=True)
            stream = io.StringIO(newline="")
            writer = csv.DictWriter(stream, fieldnames=COLUMNS)
            writer.writeheader()
            count = 0
            for number, film in films.items():
                versions = documents.get(number)
                if not versions:
                    writer.writerow({**film, "statut": "absent_opus"})
                    continue
                folder = Path("sous_titres") / film["imdb_id"]
                (args.out / folder).mkdir(parents=True, exist_ok=True)
                for subtitle_id, (member, suffix) in versions.items():
                    relative_path = folder / f"{subtitle_id}{suffix}"
                    with archive.open(member) as source:
                        write_file(args.out / relative_path, source)
                    writer.writerow({**film, "statut": "trouve", "subtitle_id": subtitle_id,
                                     "fichier_local": relative_path.as_posix()})
                    count += 1
            write_file(index_path, io.BytesIO(stream.getvalue().encode("utf-8-sig")))
    except (OSError, ValueError, BadZipFile) as error:
        parser.exit(1, f"Extraction interrompue. {error}\n")

    print(f"{len(documents):,} films couverts sur {len(films):,}, {count:,} fichiers extraits.")
    print(f"Index dans {index_path.resolve()}")


if __name__ == "__main__":
    main()