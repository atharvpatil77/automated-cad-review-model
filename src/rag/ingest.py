"""
RAG ingestion module for client requirement specs.

STATUS: not yet implemented. Currently the pipeline consumes hand-authored
rule JSON (src/rules/rules_bracket.json) derived manually from
data/sample_specs/bracket_requirements.md. This module's job is to automate
that derivation: spec doc -> chunked, retrievable requirement rules.

Planned approach:
1. Chunk source documents (PDF/Markdown) by requirement, not by page --
   each chunk should be one checkable rule, not an arbitrary text window.
2. Store chunk text + structured metadata (material, part_category,
   feature_type) alongside the embedding, so retrieval can be filtered,
   not just semantic. Pure vector similarity is unreliable for numeric
   tolerances -- "must be 2.5mm" and "must be 25mm" are semantically
   near-identical but operationally opposite.
3. Embed with a standard sentence embedding model and store in Chroma
   (simplest for prototyping) or pgvector (if integrating with a real DB).
4. A separate extraction step (can be LLM-assisted) converts each
   retrieved chunk into the same structured rule schema used by
   src/rules/rule_checker.py, so retrieval output and hand-authored
   rules are interchangeable.

Example planned interface:

    from chromadb import Client

    def ingest_spec(doc_path: str, collection_name: str) -> None:
        ...

    def retrieve_requirements(query: str, part_category: str, k: int = 5) -> list[dict]:
        ...
"""

raise NotImplementedError("RAG ingestion pipeline not yet implemented -- see module docstring for plan.")
