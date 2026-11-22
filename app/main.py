"""GlobalTemperatureSQL — Streamlit entry point.

Run from the project root:
    streamlit run app/main.py
"""

import streamlit as st

from components import default_light_theme, page_style
from database import database_available
from i18n import language_toggle, t

st.set_page_config(
    page_title="GlobalTemperatureSQL",
    page_icon=":material/thermostat:",
    layout="wide",
)
page_style()
default_light_theme()
language_toggle()

if not database_available():
    st.error(t("db.down"))
    st.stop()

pages = [
    st.Page("views/home.py", title=t("nav.home"), icon=":material/public:", default=True),
    st.Page("views/explorer.py", title=t("nav.explorer"), icon=":material/monitoring:"),
    st.Page("views/map.py", title=t("nav.map"), icon=":material/map:"),
    st.Page("views/playground.py", title=t("nav.playground"), icon=":material/terminal:"),
]
st.navigation(pages, position="top").run()
