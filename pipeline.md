# Between Film and Flow: Analysis of Cross-References Between Cinema and French Rap

## Research question

How do French rap and cinema reference one another, and to what extent do these references generate cultural circulation between the two?

The project studies two directions:

- **Film → Rap**
- **Rap → Film**

---

## 1. Film → Rap

### Explicit references
Starting from the existing corpus of ~50,000 French rap songs:

- scrape Genius annotations
- identify annotations related to films, series, characters, actors, scenes, etc.
- extract and normalize the referenced films/series

**Output:**  
`Rap song → Film/Series`

### Audio samples
Add films directly sampled in French rap songs:

- movie dialogue
- movie excerpts

**Main source:** SensCritique lists and complementary Genius lists.

**Output:**  
`Rap song → Sampled film`

### Audience circulation
Use the survey to ask:

> Have you ever heard a film or series referenced or sampled in a rap song and, as a result, looked it up or watched it?

Collect:

- song/artist
- film or series discovered
- whether the respondent only searched for it or actually watched it

Then match reported films with the Film → Rap database.

---

## 2. Rap → Film

### Explicit references
Build a corpus of French films since approximately 1985 and search their subtitles for:

- rapper names
- rap groups
- song titles
- album titles

using entities from the existing French rap corpus.

**Output:**  
`Film → Rap artist/song`

### Soundtracks
Retrieve film soundtrack information and match:

- soundtrack artists
- soundtrack song titles

with artists and songs from the existing French rap corpus.

**Output:**  
`Film → French rap song`

### Audience circulation
Use the **same survey in the opposite direction**:

> Have you ever heard or seen a French rapper or rap song in a film and, as a result, discovered or looked up that artist or song?

Collect:

- film
- rapper/song discovered
- whether the respondent subsequently listened to the song or explored the artist

Then match these responses with the Rap → Film database.

---

## 3. Cross-reference network

Build a simple bipartite graph:

`RAP ↔ FILMS`

with four types of links:

### Film → Rap
- `explicit_reference`
- `audio_sample`

### Rap → Film
- `explicit_reference`
- `soundtrack`

The survey provides an additional layer measuring whether these observable references actually produce **cultural discovery**.

---

## Main hypotheses

### H1 — Cultural concentration
Cross-references are concentrated around a limited number of films and rap artists that act as **cultural hubs**.

### H2 — Asymmetric circulation
Cinema and rap influence one another through different channels:

- Film → Rap: mainly references and samples
- Rap → Film: mainly soundtracks and explicit mentions

### H3 — Persistence
Some references persist long after the original release and become part of a shared cultural repertoire.

### H4 — Reciprocity
Some films and artists occupy central positions in both directions of the network.

### H5 — Cross-media discovery
References do not only circulate between cultural products: they also generate consumption across media.

Two symmetric mechanisms are tested:

`Rap song → film reference → discovery/viewing of film`

and

`Film → rap reference/song → discovery/listening of rapper`

---

## Final outputs

1. **Film → Rap database**
   - Genius references
   - film dialogue/excerpt samples

2. **Rap → Film database**
   - rap references in film dialogue
   - French rap songs in soundtracks

3. **Rap ↔ Film network**
   - direction and type of each cross-reference

4. **Audience survey**
   - whether Film → Rap references lead listeners to cinema
   - whether Rap → Film references lead viewers to rap

5. **Comparison between cultural presence and cultural transmission**
   - which references are frequent?
   - which references actually lead people to discover the other cultural field?