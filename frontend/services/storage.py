"""
Browser persistence helpers for auth tokens.

READ  : streamlit_js_eval reads localStorage values back to Python.
        Called once per browser session inside _restore_auth() in app.py.

WRITE : st.components.v1.html fires JS in a same-origin iframe (no return
        value → no automatic rerun).  Writes are QUEUED in session_state via
        queue_save_tokens() / queue_clear_tokens(), then executed at the very
        start of the NEXT render by flush_pending() in app.py.
        This guarantees the component is in the page before any st.rerun()
        could discard it.

Page / session_id state : stored in st.query_params (URL), not here.
"""
import json
import streamlit as st
import streamlit.components.v1 as components
from streamlit_js_eval import streamlit_js_eval

_AT  = "ds_at"   # localStorage key for access token
_RT  = "ds_rt"   # localStorage key for refresh token
_NUL = "__null__"  # sentinel: key absent from localStorage


# ── READ ─────────────────────────────────────────────────────────────────────

def read_tokens() -> dict | None:
    """
    Read tokens from localStorage.

    Returns None on the first render (JS hasn't executed yet).
    Returns {"access_token": str|None, "refresh_token": str|None} on the
    second render after the JS components fire.  None value = key absent.
    """
    raw = streamlit_js_eval(
        js_expressions=(
            "setFrameHeight(0);"
            "JSON.stringify({"
            f"access_token: localStorage.getItem('{_AT}') ?? '{_NUL}',"
            f"refresh_token: localStorage.getItem('{_RT}') ?? '{_NUL}'"
            "})"
        ),
        key="_ls_tokens",
    )
    if raw is None:
        return None

    values = json.loads(raw)
    at = values["access_token"]
    rt = values["refresh_token"]

    return {
        "access_token":  None if at == _NUL else at,
        "refresh_token": None if rt == _NUL else rt,
    }


# ── WRITE QUEUE ───────────────────────────────────────────────────────────────

def queue_save_tokens(access_token: str, refresh_token: str):
    """Queue a token save.  Executed by flush_pending() on the next render."""
    st.session_state["_pending_storage"] = {
        "action": "save",
        "at": access_token,
        "rt": refresh_token,
    }


def queue_clear_tokens():
    """Queue a token clear.  Executed by flush_pending() on the next render."""
    st.session_state["_pending_storage"] = {"action": "clear"}


# ── FLUSH ─────────────────────────────────────────────────────────────────────

def flush_pending():
    """
    Execute any queued localStorage write.
    Must be called at the very start of each render in app.py,
    before _restore_auth() or _route().
    """
    pending = st.session_state.pop("_pending_storage", None)
    if pending is None:
        return
    if pending["action"] == "save":
        _write_tokens_js(pending["at"], pending["rt"])
    elif pending["action"] == "clear":
        _clear_tokens_js()


# ── INTERNAL JS HELPERS ───────────────────────────────────────────────────────

def _write_tokens_js(at: str, rt: str):
    n = _bump("_ls_wn")
    js = (
        f"try{{"
        f"window.parent.localStorage.setItem({json.dumps(_AT)},{json.dumps(at)});"
        f"window.parent.localStorage.setItem({json.dumps(_RT)},{json.dumps(rt)});"
        f"}}catch(e){{}}/*w{n}*/"
    )
    components.html(f"<script>{js}</script>", height=0)


def _clear_tokens_js():
    n = _bump("_ls_cn")
    js = (
        f"try{{"
        f"window.parent.localStorage.removeItem({json.dumps(_AT)});"
        f"window.parent.localStorage.removeItem({json.dumps(_RT)});"
        f"}}catch(e){{}}/*c{n}*/"
    )
    components.html(f"<script>{js}</script>", height=0)


def _bump(key: str) -> int:
    """Increment and return a per-session counter (survives _reset_session)."""
    n = st.session_state.get(key, 0) + 1
    st.session_state[key] = n
    return n
