"""
CAD feature extraction module -- sheet metal parts.

Extracts structured features from a STEP file using CadQuery/OCCT, matching
the schema expected by src/rules/rule_checker.py:

{
  "part_id": str,
  "part_name": str,
  "part_category": "sheet_metal_bracket",
  "material": str,              # NOT extractable from geometry alone -- see note below
  "wall_thickness_mm": float,
  "bounding_box_mm": [x, y, z],
  "min_fillet_radius_mm": float,
  "features": [
    {"type": "mounting_hole", "diameter_mm": float, "position": [x, y]},
    ...
  ]
}

IMPORTANT LIMITATIONS (be upfront about these in any writeup):
- `material` is usually NOT embedded in a plain STEP file. It's only present
  if the exporting CAD tool wrote AP242 PMI/metadata, which many don't.
  For now this must be supplied separately (manual tag, filename convention,
  or a config file per part) -- see `material` param below.
- `hole_diameter_tolerance_mm` is a manufacturing tolerance, not a geometric
  property of the nominal model -- it typically lives in the drawing/PMI,
  not the solid body. Geometry alone gives you nominal hole diameter and
  position, not the tolerance band. This is a real gap: either the
  tolerance must come from the requirement spec instead of the part (i.e.
  "all holes must be held to +/-0.1mm" becomes a manufacturing instruction,
  not a per-hole extracted value), or it must be manually supplied.
- Thickness detection assumes a simple sheet metal part with one dominant
  pair of parallel opposite-facing planar faces. Complex multi-thickness
  or non-planar sheet parts will need a more advanced approach.
- Fillet radius extraction is not yet implemented here (see TODO below) --
  it requires walking TORUS/CYLINDER edge-adjacent geometry, which is more
  involved than hole detection since fillets on complex parts vary widely.
"""
from __future__ import annotations
import math
from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface


def _get_bounding_box(shape) -> list[float]:
    bbox = shape.BoundingBox()
    return [round(bbox.xlen, 3), round(bbox.ylen, 3), round(bbox.zlen, 3)]


def _get_holes(shape) -> list[dict]:
    """
    Detect true through-holes (full-circle cylindrical faces), excluding
    partial cylindrical surfaces like corner fillets (which share the same
    geomType() but only span a partial angular arc).
    """
    holes = []
    for face in shape.Faces():
        if face.geomType() != "CYLINDER":
            continue
        surf = BRepAdaptor_Surface(face.wrapped)
        cyl = surf.Cylinder()
        radius = cyl.Radius()
        loc = cyl.Position().Location()

        u_min, u_max = surf.FirstUParameter(), surf.LastUParameter()
        angular_span = abs(u_max - u_min)
        is_full_hole = angular_span > (2 * math.pi - 0.01)

        if is_full_hole:
            holes.append({
                "type": "mounting_hole",
                "diameter_mm": round(radius * 2, 3),
                "position": [round(loc.X(), 3), round(loc.Y(), 3)],
            })
    return holes


def _get_fillet_radii(shape) -> list[float]:
    """
    Detect fillet/rounded-edge radii: partial-angle cylindrical faces
    (as opposed to full-circle cylindrical faces, which are holes --
    see _get_holes). Returns all fillet radii found; the caller decides
    whether to report the minimum, since that's the DFM-relevant value
    (smallest fillet = highest stress concentration risk).

    Caveat: this heuristic assumes fillets are the only partial-cylinder
    features on the part. Slots, counterbores, or partial-cylindrical
    functional features would also be picked up here and would need
    additional filtering (e.g. by comparing against known hole positions)
    on more complex parts.
    """
    radii = []
    for face in shape.Faces():
        if face.geomType() != "CYLINDER":
            continue
        surf = BRepAdaptor_Surface(face.wrapped)
        cyl = surf.Cylinder()
        radius = cyl.Radius()

        u_min, u_max = surf.FirstUParameter(), surf.LastUParameter()
        angular_span = abs(u_max - u_min)
        is_full_hole = angular_span > (2 * math.pi - 0.01)

        if not is_full_hole:
            radii.append(round(radius, 3))
    return radii


def _get_sheet_thickness(shape) -> float | None:
    """
    Finds the largest pair of planar faces with opposite normals -- the
    top/bottom of a sheet metal part -- and measures the distance between
    their centers. Works for simple single-thickness sheet parts.
    """
    planar_faces = []
    for face in shape.Faces():
        if face.geomType() == "PLANE":
            normal = face.normalAt()
            planar_faces.append({
                "normal": (round(normal.x, 4), round(normal.y, 4), round(normal.z, 4)),
                "area": face.Area(),
                "center": face.Center(),
            })

    planar_faces.sort(key=lambda f: -f["area"])

    for i, f1 in enumerate(planar_faces):
        for f2 in planar_faces[i + 1:]:
            n1, n2 = f1["normal"], f2["normal"]
            is_opposite = all(abs(n1[k] + n2[k]) < 0.01 for k in range(3))
            if is_opposite:
                c1, c2 = f1["center"], f2["center"]
                dist = ((c1.x - c2.x) ** 2 + (c1.y - c2.y) ** 2 + (c1.z - c2.z) ** 2) ** 0.5
                return round(dist, 3)
    return None


def extract_features(
    step_path: str | Path,
    part_id: str,
    part_name: str,
    material: str,
) -> dict:
    """
    Extract structured features from a STEP file.

    `material` must be supplied by the caller -- see module docstring on
    why this generally can't be read reliably from the STEP geometry itself.
    """
    model = cq.importers.importStep(str(step_path))
    shape = model.val()

    fillet_radii = _get_fillet_radii(shape)

    return {
        "part_id": part_id,
        "part_name": part_name,
        "part_category": "sheet_metal_bracket",
        "material": material,
        "wall_thickness_mm": _get_sheet_thickness(shape),
        "bounding_box_mm": _get_bounding_box(shape),
        "min_fillet_radius_mm": min(fillet_radii) if fillet_radii else None,
        "features": _get_holes(shape),
    }


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 4:
        print("Usage: python cad_extractor.py <step_file> <part_id> <part_name> [material]")
        sys.exit(1)

    result = extract_features(
        step_path=sys.argv[1],
        part_id=sys.argv[2],
        part_name=sys.argv[3],
        material=sys.argv[4] if len(sys.argv) > 4 else "UNKNOWN",
    )
    print(json.dumps(result, indent=2))