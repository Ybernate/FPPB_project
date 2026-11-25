"""Centralized session state management for the FitoEvidencia Streamlit application."""

from __future__ import annotations

from typing import Any
import streamlit as st

INITIAL_STATE: dict[str, Any] = {
    # Navigation
    "active_tab_index": 0,
    
    # Mode 1: Planta (empieza vacío; placeholder guía al usuario — decisión de diseño)
    "plant_search": "",
    "plant_selected_species": None,
    "plant_confirmed": False,
    "plant_data": None,

    # Mode 2: Molécula
    "mol_search": "",
    "mol_detected_type": "NAME",
    "mol_data": None,

    # Mode 3: Proteína / Proceso
    "target_radio": "Proteína (Gen/Diana)",
    "only_plants_toggle": True,
    "pchembl_slider": 6.0,
    "protein_input": "",
    "pathway_input": "",
    "target_data": None,
    
    # Global messages / errors
    "error_message": None,
}


def init_session_state() -> None:
    """Initializes default keys in st.session_state if they are not already set."""
    for key, default_val in INITIAL_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = default_val


def get_state(key: str, default: Any = None) -> Any:
    """Safely retrieves a value from st.session_state."""
    return st.session_state.get(key, default)


def set_state(key: str, value: Any) -> None:
    """Sets a value in st.session_state."""
    st.session_state[key] = value
