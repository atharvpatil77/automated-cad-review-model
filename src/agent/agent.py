"""
Agentic orchestration layer.

STATUS: not yet implemented. This is the top layer of the pipeline and the
last thing to build -- it should only be added once extraction, rule
checking, and RAG retrieval are each independently proven (see
scripts/run_demo.py for the current deterministic-only pipeline).

Design principle: the LLM is an orchestrator and explainer, NOT the
compliance decision-maker. It should never be asked "does this pass?" --
that question is answered by src/rules/rule_checker.py, which is
deterministic and auditable. The agent's job is to:

  1. Classify the part (category, material family) to select the right
     rule set / RAG query.
  2. Call retrieve_requirements() to pull applicable rules for this part.
  3. Call check_part() (the deterministic checker) with those rules.
  4. Turn the structured CheckResult list into a clear, human-readable
     explanation -- especially for ambiguous or borderline cases where a
     human reviewer needs context, not just a checkbox.
  5. Flag cases where retrieved requirements conflict or are ambiguous,
     rather than silently picking one interpretation.

Planned interface (function-calling / tool-use pattern):

    tools = [
        {"name": "retrieve_requirements", "description": "...", ...},
        {"name": "check_part", "description": "...", ...},
    ]

    def review_part(part_features: dict) -> str:
        # Claude (or similar) is given `part_features` and the tools above,
        # and produces a natural-language compliance narrative grounded in
        # the deterministic tool outputs -- not free-form judgment.
        ...
"""

raise NotImplementedError("Agent orchestration not yet implemented -- see module docstring for plan.")
