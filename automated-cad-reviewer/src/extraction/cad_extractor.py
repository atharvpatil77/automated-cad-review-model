"""
CAD feature extraction module.

STATUS: not yet implemented against real geometry -- this is the Phase 1
target. Currently the pipeline consumes hand-authored JSON in
data/sample_parts/ that mimics this module's intended output schema, so the
rule-checking and reporting layers can be built and validated independently.

Planned implementation (CadQuery, built on the OCCT kernel):

    pip install cadquery

    import cadquery as cq

    def extract_features(step_path: str) -> dict:
        model = cq.importers.importStep(step_path)
        bbox = model.val().BoundingBox()
        return {
            "bounding_box_mm": [bbox.xlen, bbox.ylen, bbox.zlen],
            # wall thickness, fillet radii, and hole detection require walking
            # the B-rep face/edge topology -- see OCCT docs on
            # BRepAdaptor / GProp for the relevant APIs.
            ...
        }

Output schema (must match what src/rules/rule_checker.py expects):

{
  "part_id": str,
  "part_name": str,
  "part_category": str,
  "material": str,           # from STEP metadata/PMI if present, else manual tag
  "wall_thickness_mm": float,
  "bounding_box_mm": [x, y, z],
  "min_fillet_radius_mm": float,
  "features": [
    {"type": "mounting_hole", "diameter_mm": float,
     "hole_diameter_tolerance_mm": float, "position": [x, y]},
    ...
  ]
}
"""


def extract_features(step_path: str) -> dict:
    raise NotImplementedError(
        "Real STEP extraction not yet implemented. "
        "See module docstring for the CadQuery-based plan. "
        "For now, use data/sample_parts/*.json as extraction stand-ins."
    )
