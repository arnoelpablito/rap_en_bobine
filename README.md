# Between Film and Flow

### Cross-References and Cultural Circulation Between French Rap and Cinema (through audio and text)

**Between Film and Flow** is a research project investigating how French rap and cinema reference one another, and whether these cross-media references contribute to cultural discovery. It combines large-scale text analysis, named-entity recognition, film and music metadata, and (at a later stage) survey evidence.

> **Research question:** How do French rap and cinema reference one another, and to what extent do these references generate cultural circulation between the two?

The study examines two complementary mechanisms:

1. **Film → Rap:** Cinema enters French rap through lyrical references, dialogue excerpts, and audio samples.
2. **Rap → Film:** French rap enters cinema through mentions of rappers, groups, songs, and albums, as well as through film soundtracks.

**Direction convention:** These arrows denote the *direction of cultural circulation*, as in [`pipeline.md`](pipeline.md), rather than the direction of a textual mention. Thus, an observed reference from a *rap song to a film* belongs to the **Film → Rap** strand; a reference from a *film to a rapper* belongs to **Rap → Film**.

## Research design

| Direction of cultural circulation | Evidence | Observed link | Approach |
| --- | --- | --- | --- |
| Film → Rap | Explicit references | Rap song → film, series, character, or actor | Genius annotations; entity extraction and normalization |
| Film → Rap | Audio samples | Rap song → sampled film | Sample and dialogue-excerpt metadata |
| Rap → Film | Explicit references | Film → rapper, group, song, or album | French-film metadata; subtitle search |
| Rap → Film | Soundtracks | Film → French rap recording | Film soundtrack and rap-corpus metadata matching |

The project starts from an existing corpus of approximately **80,000 French rap songs** and builds a complementary corpus of **French films released since approximately 1985**. The two are linked through references identified in annotations, subtitles, audio samples, and soundtrack credits. These datasets will ultimately support a bipartite **rap–cinema network**.

**Note** : the french film file will be used to restrain the number of movies in which we search french rap songs. However, rap songs mention movies at a larger scale (ex: Scarface), so fir this part of the project the whole IMDb dataset will be considered.

## Repository structure

The tree below reflects the **currently visible project layout**. Files described in later sections as planned are *not* included in this tree.

```text
rap_cinema/
├── data/
│   ├── IMDb/                           # IMDb source data
│   ├── opus_fr/
│   │   ├── sous_titres/                # Extracted French subtitle files, grouped by film
│   │   └── index_sous_titres.csv       # Subtitle-to-film index
│   ├── annotations.csv                 # Collected Genius annotations
│   ├── annotations_gliner_checkpoint.csv
│   ├── annotations_mistral_checkpoint.csv
│   ├── cinema_entities_gliner.csv      # GLiNER entity-extraction output (DISAPPOINTING)
│   ├── cinema_entities_mistral.csv     # Mistral entity-extraction output (DISAPPOINTING)
│   ├── corpus.csv                      # French rap corpus of 80k songs with the scraped annotations added
│   ├── corpus_before_annotations.csv   # French rap corpus without scraped annotations
│   ├── films_francais.csv              # Selected French films and IMDb identifiers
│   ├── fr.zip                          # French OPUS/OpenSubtitles archive
│   ├── imdb.duckdb                     # Local IMDb database            
│   └── old_corpus.csv                  # French rap corpus of 50k songs
├── src/
│   ├── NER_tests/
│   │   ├── detect_cinema_gliner.py     # Cinema-related NER with GLiNER
│   │   └── detect_cinema_mistral.py    # Alternative extraction with Mistral
│   ├── build_imdb_db.py                # Build the local IMDb database
│   ├── extract_opensubtitles.py        # Extract subtitles for selected films
│   ├── requete_french_movies.py       # Query the IMDb database for French films
│   └── scrape_genius_annotations.py   # Collect Genius annotations
├── .gitignore
├── pipeline.md                        # Research design and hypotheses
└── README.md
```

## Data pipeline

### 1. Cinema references in French rap — Film → Rap

**Goal:** Identify films, television series, and other cinema-related entities referenced by French rap songs.


**Workflow:**

```text
French rap corpus (corpus.csv)
        │
        ▼
Scrape Genius annotations (scrape_genius_annotations.py)
        │
        ▼
annotations.csv
        │
        ├── GLiNER  ──► cinema_entities_gliner.csv (Does not work very well)
        │
        └── Mistral ──► cinema_entities_mistral.csv (Does not work very well)
        │
        ▼
larger local model or GPT to detect movie entities ?
        │
        ▼
Rap song ↔ referenced film/series
```

**Planned extension — audio samples:** Add films whose dialogue or audio is sampled in French rap recordings. => Maybe also use the genius annotations for that and look for the mention of a sample of an extract or dialogue of a movie.

### 2. Rap references in French films — Rap → Film

**Goal:** Identify explicit references to French rap in the dialogue of French films released since approximately 1985 (start of rap songs on Genius).

**Existing files and scripts:**

- `src/build_imdb_db.py` — construct a DuckDB database from IMDb source data => `data/imdb.duckdb`
- `src/requete_french_movies.py` — select French films after 1985, including `imdb_id` identifiers. => `data/films_francais.csv
- `data/fr.zip` — Downloaded all French OPUS/OpenSubtitles archive up to 2024.
- `src/extract_opensubtitles.py` — extract available subtitles corresponding to the selected films after 1985 => `data/opus_fr/sous_titres/` (XML files) and metadata in `data/opus_fr/index_sous_titres.csv`


**Planned extension — soundtracks:** Collect film soundtrack credits and match performers and recording titles against the French rap corpus. (On IMBd)

### 3. Audience survey (NOT STARTED)

**Planned stage.** Measure whether an observable cross-reference is associated with subsequent discovery and consumption.

For the **Film → Rap** direction, ask whether a respondent looked up or watched a film/series after hearing it referenced or sampled in a rap song. For **Rap → Film**, ask whether a respondent discovered, searched for, or listened to a rap artist/song after encountering it in a film.

Record the specific works involved and distinguish **searching for a work** from **consuming it**. Match reported references, where possible, with the observational databases. Self-reported discovery should be interpreted as reported behavior, not as a causal estimate without a suitable identification design.


## Research hypotheses

The project tests five hypotheses described in [`pipeline.md`](pipeline.md):

- **H1 — Cultural concentration:** References are concentrated around a limited number of films and artists acting as cultural hubs.
- **H2 — Asymmetric circulation:** The two media circulate through different channels, including references, samples, and soundtracks.
- **H3 — Persistence:** References can survive long after the release of the original work.
- **H4 — Reciprocity:** Some films and artists occupy central positions in both directions of the network.
- **H5 — Cross-media discovery:** Exposure to cross-references may prompt audiences to explore works in the other medium.

## Expected research outputs

1. **Film → Rap database:** References to film and television in French rap, plus film audio samples used in rap recordings.
2. **Rap → Film database:** Rap mentions in film dialogue and French rap recordings in film soundtracks.
3. **Cross-reference network:** A typed, directed representation of relations between the two cultural fields.
4. **Audience survey dataset:** Respondents' reported exposure, discovery, and consumption across media.
5. **Comparative analysis:** Cultural presence (how often references appear) versus cultural transmission (whether audiences report discovering new works).