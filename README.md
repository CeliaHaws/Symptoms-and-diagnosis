# Symptoms & Diagnosis Knowledge Graph

A project exploring whether **GraphRAG / knowledge graphs** can be used to take a set of reported symptoms and surface a ranked list of possible diagnoses, along with the reasoning path (which symptoms connected to which condition) that led to each suggestion.

## Motivation

Symptom checkers usually work as flat keyword lookups. This project instead models symptoms and diseases as a **graph** — diseases and symptoms as nodes, and the relationships between them as edges — so that:

- A diagnosis can be linked to *multiple* contributing symptoms at once, not just the closest keyword match.
- Shared symptoms across diseases become visible (e.g. "chest tightness" connecting to several conditions), which helps explain *why* a diagnosis was suggested.
- Retrieval-augmented generation (GraphRAG) can traverse those relationships to generate a natural-language explanation, rather than just returning a raw label.

## Data

`diagnosis.py` reads two CSVs (loaded by `Triplets`):

- `Final CSV.csv` — wide format, one disease per row with up to 17 symptom columns.
- `final_symptoms_to_disease.csv` — long format, one disease per row with a comma-separated symptom string (handles "x and y" / "x or y" phrasing via `SymptomSplitter`).

Both are combined into `(disease, HAS_SYMPTOM, symptom)` triples that back the graph.

The other large CSVs in this folder (`disease_symptom_triples.csv`, `disease_symptom_triples2.csv`, `disease_symptom_triples_2.csv`, `weighted_disease_symptom_triples.csv`) are intermediate outputs from `Notebook.ipynb` — exploratory data prep, not read by `diagnosis.py`.

## Planned approach

1. **Graph** — `SymptomGraph` builds a directed graph of diseases → symptoms from the triples.
2. **Weighting** — symptoms are weighted by rarity (IDF-style, `SymptomRarityWeighting`) and by how often they show up for a given disease (`SymptomPerDiseaseFrequencyWeighting`), combined in `CombinedSymptomScorer`.
3. **Scoring** — candidate diseases are ranked with a weighted-Jaccard score against the reported symptoms, with a penalty applied when a typical symptom has been explicitly ruled out.
4. **Canonicalisation** — `SymptomCanonicaliser` maps free-text phrases ("throwing up", "temperature") onto real graph nodes, via a synonym table plus fuzzy matching (`rapidfuzz`), so the graph can be queried in natural language rather than exact symptom names.
5. **Agent** — `DiagnosisAgent` wraps the graph as tools for a locally-hosted LLM (via LM Studio's OpenAI-compatible endpoint, `localhost:1234`), asks one follow-up question per turn (the graph's own "discriminator" symptoms — whichever best splits the current candidates), and is restricted to only naming diseases/symptoms the tool actually returned. `Guardrails` strips out anything the model invents that isn't grounded in the graph's output.
6. **Visualisation** — `DiagnosisVisuliser` colours the graph live: diseases red→green by current score, symptoms light→dark blue for unreported→reported.

## Project structure

Everything the project actually reasons with lives in `diagnosis.py` — the graph, weighting/scoring, canonicaliser, guardrails, the LangChain agent, and the graph visualiser. Everything else here is a way of driving or exploring that:

- `diagnosis.py` — the graph-RAG engine described above.
- `Notebook.ipynb` — data exploration / prep notebook that also produced the intermediate CSVs listed under Data above.
- `app.py` — a small Tkinter chat front end for `diagnosis.chat()`; redraws the graph panel after every message.
- `app(graph_button).py` — same front end, but with graph redrawing decoupled from sending messages: symptoms are still recorded each turn, but the (slow) graph layout only redraws when you press **Generate Graph** (unlocked after the 2nd message).

## Status

Working prototype: graph construction, scoring, canonicalisation, and guardrails run end-to-end against a local LLM served through LM Studio, with two small Tkinter front ends for poking at it. Known rough edges are tracked in the `#BUGGS` list at the top of `diagnosis.py` (e.g. repeated follow-up questions, underscore formatting in symptom names).

