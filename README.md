# Symptoms & Diagnosis Knowledge Graph

A project exploring whether **GraphRAG / knowledge graphs** can be used to take a set of reported symptoms and surface a ranked list of possible diagnoses, along with the reasoning path (which symptoms connected to which condition) that led to each suggestion.

## Motivation

Symptom checkers usually work as flat keyword lookups. This project instead models symptoms and diseases as a **graph** — diseases and symptoms as nodes, and the relationships between them as edges — so that:

- A diagnosis can be linked to *multiple* contributing symptoms at once, not just the closest keyword match.
- Shared symptoms across diseases become visible (e.g. "chest tightness" connecting to several conditions), which helps explain *why* a diagnosis was suggested.
- Retrieval-augmented generation (GraphRAG) can traverse those relationships to generate a natural-language explanation, rather than just returning a raw label.

## Data

| File | Description |
|---|---|
| `DiseaseAndSymptoms.csv` | Diseases mapped to up to 17 discrete symptom columns per row. |
| `final_symptoms_to_disease.csv` | Diseases mapped to free-text symptom descriptions (`symptom_text`), useful for embedding/NLP-based graph construction. |

## Planned approach

1. **Build the graph** — parse both CSVs into a unified graph structure (e.g. `Disease -[HAS_SYMPTOM]-> Symptom`), deduplicating symptom names/synonyms across the two data sources.
2. **Store the graph** — load into a graph database or in-memory graph library (e.g. Neo4j, NetworkX) for querying.
3. **Retrieval** — given a set of input symptoms, traverse the graph to find candidate diseases ranked by symptom overlap/strength of connection.
4. **Generation** — use an LLM (GraphRAG-style) to turn the retrieved subgraph into a human-readable explanation of *why* each diagnosis was suggested.
5. **Interface** — expose this as a simple script/notebook or small app where a user can input symptoms and get back ranked possibilities with explanations.

## Project structure

```
.
├── DiseaseAndSymptoms.csv          # structured symptom data
├── final_symptoms_to_disease.csv   # free-text symptom data
├── The_code                        # main working script (in progress)
└── README.md
```

## Status

Early stage — data collected, graph construction and retrieval logic not yet implemented.

## Disclaimer

This project is for educational/portfolio purposes only. It is **not a medical device** and should never be used as a substitute for professional medical advice, diagnosis, or treatment.
