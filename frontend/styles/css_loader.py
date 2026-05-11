from pathlib import Path

import streamlit as st


_FRONTEND_ROOT = Path(__file__).resolve().parents[1]


def load_css(*files: str) -> None:
    """Load one or more CSS files from frontend/styles."""
    chunks = []
    for file in files:
        path = Path(file)
        if not path.is_absolute():
            path = _FRONTEND_ROOT / "styles" / file
        chunks.append(path.read_text(encoding="utf-8"))

    st.markdown("<style>\n" + "\n".join(chunks) + "\n</style>", unsafe_allow_html=True)


def load_css_with_vars(file: str, variables: dict[str, str]) -> None:
    """Load CSS after defining a small set of CSS custom properties."""
    declarations = "\n".join(f"    {name}: {value};" for name, value in variables.items())
    st.markdown(f"<style>\n:root {{\n{declarations}\n}}\n</style>", unsafe_allow_html=True)
    load_css(file)
