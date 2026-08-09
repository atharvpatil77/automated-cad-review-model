"""
Automated CAD Design Review — Streamlit web app.

Wraps the existing extraction / rule-checking / LLM-explanation pipeline
in a simple upload-and-review UI. No new logic here -- this is purely a
frontend over src/extraction, src/rules, and src/agent.

Run locally:
    streamlit run app.py

Deploy: push to GitHub, then connect the repo on share.streamlit.io.
Set GEMINI_API_KEY under that app's Settings -> Secrets (never commit it).
"""
import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.extraction.cad_extractor import extract_features
from src.rules.rule_checker import check_part, load_json, Status

RULES_PATH = ROOT / "src" / "rules" / "rules_bracket.json"
APPROVED_MATERIALS = ["Aluminum 6061", "Aluminum 5052", "Stainless Steel 304", "Other / Not sure"]

st.set_page_config(page_title="CAD Design Review Agent", page_icon="🔧", layout="centered")

st.title("🔧 Automated CAD Design Review")
st.caption(
    "**Scope:** single-part, single-thickness, flat/near-flat sheet metal parts "
    "(STEP format only). Checks material, wall thickness, envelope size, fillet "
    "radius, and flags hole tolerance for manual review (not extractable from "
    "geometry alone). Other part types are not yet supported and results will "
    "be unreliable."
)

with st.expander("What this does and doesn't check"):
    st.markdown("""
**Automatically checked (from real geometry):**
- Wall/sheet thickness
- Overall bounding box / envelope
- Fillet / edge radius
- Material against an approved list (you provide the material)

**Flagged for manual review (cannot be extracted from geometry alone):**
- Hole diameter tolerance — this is a manufacturing tolerance, not a property of nominal 3D geometry

**Not yet supported:**
- Multi-thickness, curved/formed sheet, machined, or cast parts
- Assemblies (multiple parts in one file)
- Non-STEP file formats
""")

uploaded_file = st.file_uploader("Upload a STEP file (.step / .stp)", type=["step", "stp"])
material = st.selectbox("Material", APPROVED_MATERIALS)

run = st.button("Run Design Review", type="primary", disabled=uploaded_file is None)

if run and uploaded_file is not None:
    with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    with st.spinner("Extracting geometry..."):
        try:
            part = extract_features(
                step_path=tmp_path,
                part_id="WEB-001",
                part_name=uploaded_file.name,
                material=material,
            )
        except Exception as e:
            st.error(f"Extraction failed: {e}")
            st.info(
                "This usually means the STEP file uses geometry this system doesn't "
                "yet support (see 'What this does and doesn't check' above), or the "
                "file didn't export cleanly from your CAD tool."
            )
            st.stop()

    st.subheader("Extracted Features")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Wall thickness", f"{part['wall_thickness_mm']} mm" if part['wall_thickness_mm'] else "N/A")
        st.metric("Fillet radius (min)", f"{part['min_fillet_radius_mm']} mm" if part['min_fillet_radius_mm'] else "N/A")
    with col2:
        bbox = part["bounding_box_mm"]
        st.metric("Bounding box", f"{bbox[0]} × {bbox[1]} × {bbox[2]} mm")
        st.metric("Holes found", len(part["features"]))

    rules = load_json(RULES_PATH)["rules"]
    report = check_part(part, rules)

    st.subheader("Compliance Results")
    if report.passed:
        st.success("✅ All automated checks passed.")
    else:
        st.error("❌ One or more checks failed — part cannot ship as-is.")

    for r in report.results:
        icon = {"PASS": "✅", "FAIL": "❌", "MANUAL_REVIEW": "🟡"}[r.status.value]
        st.write(f"{icon} **[{r.rule_id}] {r.description}** — {r.detail}")

    with st.spinner("Generating explanation..."):
        try:
            from src.agent.agent import explain_compliance
            narrative = explain_compliance(report)
            st.subheader("AI Summary")
            st.write(narrative)
        except Exception as e:
            st.warning(f"AI explanation unavailable: {e}")
