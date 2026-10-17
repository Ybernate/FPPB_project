"""2D Chemical Structure depiction with RDKit SVG and ChEMBL fallbacks.

Authoritative source:
- ORIGINAL_REQUEST.md (Requirement R1, R5)
- PROJECT.md (Components: app/components/chem_render.py)
"""

from __future__ import annotations

import functools
import logging
from typing import Optional
import streamlit as st

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=128)
def smiles_to_svg(
    smiles: str,
    width: int = 260,
    height: int = 180,
    chembl_id: Optional[str] = None,
) -> str:
    """Generates a 2D chemical structure drawing as clean transparent SVG.
    
    Tries RDKit MolDraw2DSVG locally first; gracefully falls back to ChEMBL or placeholder SVG.
    """
    if smiles and smiles.strip():
        try:
            from rdkit import Chem
            from rdkit.Chem.Draw import rdMolDraw2D

            mol = Chem.MolFromSmiles(smiles.strip())
            if mol:
                drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
                opts = drawer.drawOptions()
                opts.clearBackground = True
                opts.bondLineWidth = 2
                opts.padding = 0.08
                drawer.DrawMolecule(mol)
                drawer.FinishDrawing()
                svg_text = drawer.GetDrawingText()
                # Ensure SVG transparent background
                if "<svg" in svg_text:
                    return svg_text
        except Exception as e:
            logger.debug("Local RDKit SVG generation failed for %s: %s", smiles, e)

    # Fallback 1: ChEMBL Depiction API if ID is available
    if chembl_id and str(chembl_id).upper().startswith("CHEMBL"):
        cid = str(chembl_id).strip().upper()
        return (
            f'<div style="text-align:center;">'
            f'<img src="https://www.ebi.ac.uk/chembl/api/data/image/{cid}.svg" '
            f'width="{width}" height="{height}" alt="Estructura química {cid}" '
            f'style="background:transparent; max-width:100%; border-radius:6px;"/>'
            f'</div>'
        )

    # Fallback 2: Clean SVG Placeholder
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="border:1px dashed #D9E2D5; border-radius:8px; background:#FAFCF8;">'
        f'<rect width="100%" height="100%" fill="none"/>'
        f'<text x="50%" y="45%" dominant-baseline="middle" text-anchor="middle" '
        f'fill="#4B5563" font-family="sans-serif" font-size="12" font-weight="600">🧪 Estructura 2D</text>'
        f'<text x="50%" y="60%" dominant-baseline="middle" text-anchor="middle" '
        f'fill="#9CA3AF" font-family="sans-serif" font-size="11">no disponible</text>'
        f'</svg>'
    )


def render_molecule_svg(
    smiles: str,
    chembl_id: Optional[str] = None,
    caption: str = "",
    width: int = 260,
    height: int = 180,
) -> None:
    """Renders 2D molecule drawing directly into Streamlit view."""
    svg_html = smiles_to_svg(smiles, width=width, height=height, chembl_id=chembl_id)
    st.markdown(svg_html, unsafe_allow_html=True)
    if caption:
        st.caption(caption)
