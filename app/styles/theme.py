"""Botanical Theme loader and styling helpers for 'Conoce tu planta'."""

from __future__ import annotations

from pathlib import Path
import streamlit as st

CSS_PATH = Path(__file__).resolve().parent / "botanical.css"

# Authoritative Color Tokens
BG_COLOR = "#FAFCF8"
CARD_SURFACE = "#FFFFFF"
TEXT_MAIN = "#1C2826"
TEXT_MUTED = "#4B5563"
BORDER_LIGHT = "#D9E2D5"

PRIMARY_GREEN = "#1B4332"
SECONDARY_GREEN = "#2D6A4F"
ACCENT_GREEN = "#40916C"
LIGHT_GREEN_BG = "#E8F5E9"

AMBER_BIAS = "#D97706"
AMBER_BG = "#FFFBEB"

BLUE_INFO = "#0284C7"
BLUE_BG = "#F0F9FF"

RED_EXTREME = "#EF4444"
RED_BG = "#FEF2F2"


import functools


@functools.lru_cache(maxsize=1)
def get_css_content() -> str:
    """Reads the botanical.css stylesheet content."""
    try:
        return CSS_PATH.read_text(encoding="utf-8")
    except Exception:
        return ""


def inject_botanical_theme() -> None:
    """Injects the custom botanical CSS stylesheet into the Streamlit session."""
    css = get_css_content()
    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def format_database_badge(db_name: str) -> str:
    """Returns an HTML badge for data source provenance (LOTUS, COCONUT, etc.)."""
    return f'<span class="badge-database">{db_name}</span>'


def format_chembl_badge(chembl_id: str) -> str:
    """Returns an HTML badge for ChEMBL identifier."""
    if not chembl_id:
        return ""
    url = f"https://www.ebi.ac.uk/chembl/compound_report_card/{chembl_id}/"
    return f'<a href="{url}" target="_blank" style="text-decoration:none;"><span class="badge-chembl">ChEMBL: {chembl_id}</span></a>'
