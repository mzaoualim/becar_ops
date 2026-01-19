from __future__ import annotations

import hmac
import os
import streamlit as st

from .i18n import t


def check_password(locale: str) -> bool:
    """Simple password gate for portfolio demos.

    Uses st.secrets["auth"]["password"] or env var APP_PASSWORD.
    """

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    configured_pw = None
    try:
        configured_pw = st.secrets.get("auth", {}).get("password")
    except Exception:
        configured_pw = None
    configured_pw = configured_pw or os.getenv("APP_PASSWORD")

    if not configured_pw:
        st.warning(t(locale, "auth_missing"))
        return False

    def _on_submit():
        entered = st.session_state.get("_pw", "")
        if hmac.compare_digest(entered, configured_pw):
            st.session_state["authenticated"] = True
            st.session_state.pop("_pw", None)
        else:
            st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.subheader(t(locale, "auth_title"))
        st.text_input(
            t(locale, "auth_prompt"),
            type="password",
            key="_pw",
            on_change=_on_submit,
        )
        st.caption(t(locale, "auth_help"))
        if "_pw" in st.session_state and st.session_state.get("_pw"):
            st.error(t(locale, "auth_error"))
        return False

    return True
