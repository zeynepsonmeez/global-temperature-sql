"""Shared UI pieces: page styling, chart theme and the "SQL behind this chart" panel."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from i18n import t
from queries import render

HEAT = "#C2410C"
HEAT_LIGHT = "#FDBA74"
COOL = "#1D4ED8"
INK = "#101828"
MUTED = "#475467"
GRID = "#EAECF0"
REGION_COLORS = {"GLB": HEAT, "NH": "#9A3412", "SH": COOL}
# Sequential warm scale for anomalies (light = less warming, dark = more).
WARM_SCALE = ["#FED7AA", "#FDBA74", "#FB923C", "#F97316", "#EA580C", "#C2410C", "#7C2D12"]
# Diverging scale for heatmaps: blue below the baseline, orange above.
DIVERGING = [[0.0, "#1D4ED8"], [0.35, "#93C5FD"], [0.5, "#F8FAFC"], [0.65, "#FDBA74"], [1.0, "#7C2D12"]]

PLAYGROUND_PAGE = "views/playground.py"


def page_style() -> None:
    st.markdown(
        """
        <style>
          .block-container, [data-testid="stMainBlockContainer"] { padding-top: 4.5rem; max-width: 1280px; }
          [data-testid="stMetricValue"] { font-size: 1.9rem; }
          .stTextArea textarea { font-family: "JetBrains Mono", "Cascadia Code", Consolas, monospace;
                                 font-size: 0.9rem; line-height: 1.55; }
          h1, h2, h3 { letter-spacing: -0.02em; }
          .gts-hero { font-size: 3.2rem; line-height: 1.05; font-weight: 700; margin: 0.4rem 0 1rem; color: #101828; }
          .gts-hero span { color: #C2410C; }
          .gts-badge { display: inline-block; font-size: 0.8rem; font-weight: 600; color: #9A3412;
                       background: #FFEDD5; padding: 4px 10px; border-radius: 999px; }
          .gts-muted { color: #475467; }
          @media (max-width: 640px) { .gts-hero { font-size: 2.2rem; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def style_figure(fig: go.Figure, height: int = 420, y_title: str = "°C") -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=INK),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID)
    fig.update_yaxes(title_text=y_title, gridcolor=GRID, zeroline=True, zerolinecolor="#98A2B3")
    return fig


def sql_panel(sql: str, params: dict, data, key: str) -> None:
    """Expander with the chart's SQL, a CSV download and a jump to the Playground."""
    runnable = render(sql, params)
    with st.expander(t("sql.behind")):
        st.code(runnable, language="sql")
        left, right = st.columns(2)
        with left:
            if st.button(t("sql.open"), key=f"open_{key}", icon=":material/terminal:"):
                # Hand-over key: the editor widget's own key is cleared on pages that don't show it.
                st.session_state["pg_pending_sql"] = runnable
                st.switch_page(PLAYGROUND_PAGE)
        with right:
            st.download_button(
                t("sql.download"), data.to_csv(index=False).encode("utf-8"),
                file_name=f"{key}.csv", mime="text/csv", key=f"csv_{key}",
                icon=":material/download:",
            )


def footer() -> None:
    st.divider()
    st.caption(t("footer.data"))
