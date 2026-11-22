"""Shared UI pieces: page styling, chart theme and the "SQL behind this chart" panel."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from i18n import t
from queries import render

# Every colour here must work on BOTH the light (#F6F7F9) and the dark (#0B1220) background.
# st.context.theme can report the wrong theme on first load or right after a switch, so the
# app does not pick colours per theme: text inherits the theme colour, lines are translucent
# greys, and the accents are mid-tones that keep their contrast on either background.
HEAT = "#EA580C"
HEAT_LIGHT = "#FB923C"
COOL = "#3B82F6"
MUTED = "rgba(148, 163, 184, 0.95)"          # slate-400: readable on light and dark
GRID = "rgba(148, 163, 184, 0.22)"
ZERO = "rgba(148, 163, 184, 0.75)"
REGION_COLORS = {"GLB": HEAT, "NH": "#E11D48", "SH": COOL}
# Up to five countries side by side: distinct hues, readable on light and dark backgrounds.
COMPARE_COLORS = ["#EA580C", "#3B82F6", "#10B981", "#A855F7", "#E11D48"]
# Sequential warm scale for anomalies: amber -> orange -> red. It ends on a SATURATED colour,
# not a dark one, so the strongest warming (the Arctic) stands out on both backgrounds;
# a scale ending in dark brown vanishes on the dark theme.
WARM_SCALE = ["#FDE68A", "#FCD34D", "#FBBF24", "#F59E0B", "#F97316", "#EF4444", "#E11D48"]
# Diverging scale for heatmaps: blue below the baseline, red above, neutral grey at zero
# (a near-white midpoint would glare on the dark theme).
DIVERGING = [[0.0, "#2563EB"], [0.3, "#93C5FD"], [0.5, "#94A3B8"], [0.7, "#FB923C"], [1.0, "#E11D48"]]
# Globe base map
LAND = "rgba(148, 163, 184, 0.38)"
OCEAN = "rgba(148, 163, 184, 0.10)"
COAST = "rgba(100, 116, 139, 0.95)"

PLAYGROUND_PAGE = "views/playground.py"


def page_style() -> None:
    st.markdown(
        """
        <style>
          .block-container, [data-testid="stMainBlockContainer"] { padding-top: 3.2rem; max-width: 1280px; }
          /* The EN/TR switch sits in the top bar instead of taking a row of every page. */
          .st-key-lang_toggle { position: fixed; top: 0.55rem; right: 3.4rem; z-index: 999991; width: auto !important; }
          /* Orange top bar with white navigation on both themes. */
          [data-testid="stHeader"] { background: #EA580C; }
          [data-testid="stTopNavLink"], [data-testid="stTopNavLink"] *,
          [data-testid="stMainMenuButton"], [data-testid="stMainMenuButton"] * { color: #FFFFFF !important; }
          [data-testid="stTopNavLink"]:hover { background: rgba(255, 255, 255, 0.16) !important; }
          [data-testid="stTopNavLink"][aria-current="page"], [data-testid="stTopNavLink"].active {
            background: rgba(255, 255, 255, 0.24) !important; }
          .st-key-lang_toggle button { background: transparent !important; color: #FFFFFF !important;
                                       border-color: rgba(255, 255, 255, 0.7) !important; }
          .st-key-lang_toggle button[aria-checked="true"] { background: #FFFFFF !important; color: #EA580C !important;
                                                            border-color: #FFFFFF !important; }
          .st-key-lang_toggle button * { color: inherit !important; }
          @media (max-width: 640px) {
            .block-container, [data-testid="stMainBlockContainer"] { padding-top: 2.6rem; }
          }
          [data-testid="stMetricValue"] { font-size: 1.9rem; }
          .stTextArea textarea { font-family: "JetBrains Mono", "Cascadia Code", Consolas, monospace;
                                 font-size: 0.9rem; line-height: 1.55; }
          h1, h2, h3 { letter-spacing: -0.02em; }
          .gts-hero { font-size: 3.2rem; line-height: 1.05; font-weight: 700; margin: 0.4rem 0 1rem; color: inherit; }
          .gts-hero span { color: #EA580C; }
          .gts-badge { display: inline-block; font-size: 0.8rem; font-weight: 600; color: #EA580C;
                       background: rgba(234, 88, 12, 0.12); border: 1px solid rgba(234, 88, 12, 0.35);
                       padding: 4px 10px; border-radius: 999px; }
          .gts-muted { color: inherit; opacity: 0.78; }
          @media (max-width: 640px) { .gts-hero { font-size: 2.2rem; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


# Streamlit offers System / Light / Dark in its main menu but always starts on "System",
# with no config option to change that. It remembers the choice in localStorage under a
# key PER PAGE PATH. This watcher (one per browser tab) checks once a second:
#   * a page path seen for the first time -> give it the visitor's preferred theme
#     (Light unless they picked another one) and reload only if it shows the other theme;
#   * otherwise -> record the theme the visitor picked, so every page follows it.
# Polling is needed because the menu changes localStorage without a 'storage' event in the
# same tab, and switching pages in the app does not re-run page scripts.
_THEME_SCRIPT = """
<script>
(() => {
  const W = window.parent;
  if (W.__gtsThemeWatcher) return;
  W.__gtsThemeWatcher = true;
  const ls = W.localStorage, PREF = "gts-theme-pref";
  const showingDark = () => {
    const app = W.document.querySelector('[data-testid="stApp"]');
    if (!app) return false;
    const [r, g, b] = getComputedStyle(app).backgroundColor.match(/\\d+/g).map(Number);
    return (r + g + b) / 3 < 128;
  };
  const tick = () => {
    const path = W.location.pathname;
    const key = `stActiveTheme-${path}-v2`, flag = `gts-theme-init-${path}`;
    if (!ls.getItem(flag)) {
      const pref = ls.getItem(PREF) || '"Light"';
      ls.setItem(key, pref);
      ls.setItem(flag, "1");
      if ((pref === '"Light"' && showingDark()) || (pref === '"Dark"' && !showingDark())) W.location.reload();
      return;
    }
    const current = ls.getItem(key);
    if (current && current !== ls.getItem(PREF)) ls.setItem(PREF, current);
  };
  tick();
  W.setInterval(tick, 1000);
})();
</script>
"""


def default_light_theme() -> None:
    try:
        st.html(_THEME_SCRIPT, unsafe_allow_javascript=True)
    except TypeError:                     # older Streamlit without unsafe_allow_javascript
        import streamlit.components.v1 as components
        components.html(_THEME_SCRIPT, height=0)


def style_figure(fig: go.Figure, height: int = 420, y_title: str = "°C") -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        # No fixed font colour: st.plotly_chart's Streamlit theme sets it for light and dark.
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID)
    fig.update_yaxes(title_text=y_title, gridcolor=GRID, zeroline=True, zerolinecolor=ZERO)
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
