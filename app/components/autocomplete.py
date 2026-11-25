"""Live search-suggestion widget (review V4).

R1 asks for autocomplete in every tab. Rather than depend on the third-party
``streamlit-searchbox`` component (compatibility with the pinned Streamlit is
unverified), this uses the review's recommended, dependency-free fallback: a
``st.text_input`` plus a server-side suggestion list rendered beneath it. Every
suggestion is backed by a real index row, so selecting one never reaches a
"no data" dead end (except the honest empty states defined in the tabs).

Callers pass a ``search_fn(query) -> list[Suggestion]`` where each ``Suggestion``
is a ``(label, value)`` tuple: ``label`` is shown on the button, ``value`` is the
canonical string written back into the search box when the suggestion is chosen.
"""

from __future__ import annotations

from typing import Callable, Optional
import streamlit as st

Suggestion = tuple[str, str]

# Minimum characters before suggestions are computed (review V4: "from 2 characters").
MIN_CHARS = 2
MAX_SUGGESTIONS = 10


def search_input(
    *,
    label: str,
    state_key: str,
    search_fn: Callable[[str], list[Suggestion]],
    placeholder: str,
    help_text: Optional[str] = None,
    empty_prompt: str,
) -> str:
    """Renders a text input with a live suggestion list and returns the committed query.

    The committed query is whatever is in ``st.session_state[state_key]`` after the
    user types or clicks a suggestion. Suggestions appear only while the box has at
    least ``MIN_CHARS`` characters and the value is not already an exact suggestion.
    """
    if state_key not in st.session_state:
        st.session_state[state_key] = ""

    typed = st.text_input(
        label,
        key=state_key,
        placeholder=placeholder,
        help=help_text,
    )

    query = (typed or "").strip()

    if not query:
        st.info(empty_prompt)
        return ""

    # Live suggestions. Skip if the typed value already equals a suggestion value
    # (i.e. the user just picked one), to avoid a redundant list.
    if len(query) >= MIN_CHARS:
        try:
            suggestions = search_fn(query)[:MAX_SUGGESTIONS]
        except Exception:  # pragma: no cover - defensive; a failed lookup must not crash the UI
            suggestions = []

        suggestion_values = {v for _, v in suggestions}
        if suggestions and query not in suggestion_values:
            st.caption("Sugerencias del índice (seleccione una):")
            for idx, (sug_label, sug_value) in enumerate(suggestions):
                if st.button(sug_label, key=f"{state_key}_sug_{idx}", width="stretch"):
                    st.session_state[state_key] = sug_value
                    st.rerun()

    return query
