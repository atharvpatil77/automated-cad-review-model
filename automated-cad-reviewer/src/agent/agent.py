"""
Agentic explanation layer.

The LLM here is an orchestrator/explainer, NOT the compliance decision-maker.
It receives a PartReport that has already been fully decided by
src/rules/rule_checker.py (deterministic, auditable) and turns it into a
clear, human-readable narrative. It must never be asked to judge whether a
value passes -- that decision is made before this module is ever called.

Provider: Google Gemini (gemini-2.5-flash). The prompt/response contract is
provider-agnostic by design -- swapping to Claude or GPT would only change
the client setup below, not the surrounding architecture.

API key handling:
- Local/Colab: read from environment variable GEMINI_API_KEY, or Colab's
  userdata secrets store. NEVER hardcode a key in this file.
- Streamlit deployment: read from st.secrets["GEMINI_API_KEY"], configured
  in the Streamlit Cloud dashboard, not committed to the repo.
"""
from __future__ import annotations
import os

from google import genai

from src.rules.rule_checker import PartReport

_SYSTEM_CONTEXT = """You are a design-review explainer for a mechanical engineering team.
You are given deterministic compliance check results for a CAD part. These results
are ground truth -- you must NEVER contradict, override, or reinterpret a PASS, FAIL,
or MANUAL_REVIEW status. Your job is only to explain them clearly in plain engineering
language for a human reviewer, and to note the practical implication of each result."""


def _get_client(api_key: str | None = None) -> genai.Client:
    """
    Resolves an API key from (in order): explicit argument, GEMINI_API_KEY
    env var, or Streamlit secrets if running inside a Streamlit app.
    Raises a clear error rather than silently failing if none is found.
    """
    if api_key:
        return genai.Client(api_key=api_key)

    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return genai.Client(api_key=env_key)

    try:
        import streamlit as st
        if "GEMINI_API_KEY" in st.secrets:
            return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except ImportError:
        pass

    raise RuntimeError(
        "No Gemini API key found. Set the GEMINI_API_KEY environment variable, "
        "pass api_key= explicitly, or configure st.secrets['GEMINI_API_KEY'] "
        "if running in Streamlit."
    )


def explain_compliance(part_report: PartReport, api_key: str | None = None) -> str:
    """
    Generate a human-readable compliance narrative for a fully-decided
    PartReport. Does not re-evaluate or alter any PASS/FAIL/MANUAL_REVIEW
    status -- purely explanatory.
    """
    client = _get_client(api_key)

    results_text = "\n".join(
        f"- [{r.status.value}] {r.description}: {r.detail}"
        for r in part_report.results
    )

    prompt = f"""{_SYSTEM_CONTEXT}

Part: {part_report.part_id} ({part_report.part_name})

Check results:
{results_text}

Write a short (4-6 sentence) compliance summary a design engineer could read before
signing off on this part."""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text
