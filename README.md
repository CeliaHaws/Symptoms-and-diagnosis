# Symptoms & Diagnosis Knowledge Graph

A project exploring whether **GraphRAG / knowledge graphs** can be used to take a set of reported symptoms and surface a ranked list of possible diagnoses, along with the reasoning path (which symptoms connected to which condition) that led to each suggestion.

## Motivation

Symptom checkers usually work as flat keyword lookups. This project instead models symptoms and diseases as a **graph** — diseases and symptoms as nodes, and the relationships between them as edges — so that:

- A diagnosis can be linked to *multiple* contributing symptoms at once, not just the closest keyword match.
- Shared symptoms across diseases become visible (e.g. "chest tightness" connecting to several conditions), which helps explain *why* a diagnosis was suggested.
- Retrieval-augmented generation (GraphRAG) can traverse those relationships to generate a natural-language explanation, rather than just returning a raw label.

## Data



## Planned approach



## Project structure


## Status




