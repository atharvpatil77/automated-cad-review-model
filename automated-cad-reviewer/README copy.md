# Automated CAD Design Review Agent

An agent that checks CAD models against client design requirements, combining
structured CAD feature extraction, RAG over requirement documents, and an
LLM orchestration layer for explanation and edge-case handling.

**Design principle:** numeric/logical compliance decisions are made by
deterministic code, never by an LLM. The AI layers (RAG retrieval, agent
orchestration) find and explain the right requirements -- they don't decide
whether 1.8mm satisfies a 2.5mm minimum. This keeps the system auditable and
trustworthy for real engineering sign-off.

## Status: Phase 1 MVP complete

The deterministic core pipeline works end-to-end on a synthetic test set:

```
data/sample_parts/*.json  -->  rule_checker.py  -->  compliance_report.md
      (extracted CAD          (deterministic         (per-part pass/fail
       features, currently     checks against          + reasons)
       hand-authored)          rules_bracket.json)
```

Run it:
```bash
pip install -r requirements.txt
python scripts/run_demo.py
```

Expected output: 2/5 sample parts pass, 3 fail (wrong material, out-of-spec
wall thickness, out-of-tolerance hole, oversized envelope) -- each caught
with a clear reason. These are deliberately-seeded known-bad parts, used to
validate the checker actually catches problems rather than rubber-stamping.

## Architecture

| Layer | Module | Status |
|---|---|---|
| Extraction | `src/extraction/cad_extractor.py` | Stub -- plan documented, needs CadQuery/OCCT implementation |
| Rule checking | `src/rules/rule_checker.py` | **Working** -- deterministic, no CAD/LLM dependency |
| RAG (spec ingestion + retrieval) | `src/rag/ingest.py` | Stub -- plan documented |
| Agent orchestration | `src/agent/agent.py` | Stub -- plan documented |
| Reporting | `src/report/report_generator.py` | **Working** |

## Roadmap

- [x] **Phase 1a:** Synthetic test data (5 parts, 1 spec doc, deliberately-seeded failures)
- [x] **Phase 1b:** Deterministic rule checker + Markdown report, proven end-to-end
- [ ] **Phase 1c:** Real STEP file extraction via CadQuery (`src/extraction/cad_extractor.py`)
      -- replace hand-authored JSON in `data/sample_parts/` with real extraction output
- [ ] **Phase 2:** Generalize requirement rules beyond the single hardcoded bracket set;
      add more feature/part types
- [ ] **Phase 3:** RAG layer -- ingest `data/sample_specs/*.md` (and real PDFs), chunk by
      requirement, retrieve with metadata filtering (material/category), auto-derive
      rule JSON instead of hand-authoring it
- [ ] **Phase 3/4:** Agent orchestration -- part classification, tool-calling into
      `retrieve_requirements()` and `check_part()`, natural-language compliance narrative,
      conflict/ambiguity flagging
- [ ] **Phase 4 (optional, only if needed):** Geometric ML for feature recognition beyond
      what the CAD kernel + rules cover

## Project structure

```
automated-cad-reviewer/
├── data/
│   ├── sample_specs/       # Client requirement docs (source of truth for rules)
│   └── sample_parts/       # Extracted CAD features (currently hand-authored,
│                           # will be replaced by cad_extractor.py output)
├── src/
│   ├── extraction/         # CAD -> structured feature JSON
│   ├── rules/              # Deterministic compliance checking
│   ├── rag/                # Spec ingestion + retrieval
│   ├── agent/              # LLM orchestration + explanation
│   └── report/             # Report generation
├── scripts/
│   └── run_demo.py         # End-to-end MVP demo
└── tests/
```

## Why this order

Extraction and RAG are both significant engineering efforts on their own
(CAD kernel APIs, document chunking strategy). Building the rule checker
first -- against hand-authored data standing in for their eventual output --
lets the core compliance logic get proven and tested independently, before
either of those heavier pieces exists. Each phase above is meant to replace
one stand-in with a real implementation without changing the interface the
rest of the pipeline depends on.
