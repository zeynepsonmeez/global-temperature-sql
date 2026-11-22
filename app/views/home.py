"""Home page: hero, rotatable latitude-band globe, dataset facts and a card for every page."""

import numpy as np
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import queries as q
from components import COAST, GRID, LAND, OCEAN, WARM_SCALE, footer
from database import read_df, read_row
from i18n import month_names, t
from library import load_samples

bands = read_df(q.GLOBE)
facts = read_row(q.FACTS)
findings = read_row(q.FINDINGS)


def globe_figure() -> go.Figure:
    # A grid of dots, each coloured by the anomaly of the latitude band it falls in.
    lats, lons, values = [], [], []
    for lat in np.arange(-87, 88, 6.0):
        band = bands[(bands.lat_min <= lat) & (lat < bands.lat_max)]
        if band.empty:
            continue
        step = 6.0 / max(np.cos(np.radians(lat)), 0.2)       # fewer dots near the poles
        for lon in np.arange(-180, 180, step):
            lats.append(lat)
            lons.append(lon)
            values.append(float(band.anomaly.iloc[0]))

    # The globe is drawn inside its own frame (render_globe), which cannot follow the app's
    # light/dark theme: the colour-bar text uses a grey that is readable on both.
    axis_font = dict(color="#94A3B8", size=11)
    fig = go.Figure(go.Scattergeo(
        lat=lats, lon=lons, mode="markers",
        marker=dict(size=6, opacity=0.85, color=values, colorscale=WARM_SCALE, cmin=0, cmax=max(values),
                    line=dict(width=0),
                    colorbar=dict(title=dict(text="°C", font=axis_font), tickfont=axis_font,
                                  thickness=10, len=0.55, x=1.0)),
        hovertemplate="%{lat:.0f}° · %{marker.color:+.2f} °C<extra></extra>",
    ))
    fig.update_geos(
        projection_type="orthographic", projection_rotation=dict(lon=20, lat=22),
        showland=True, landcolor=LAND, showocean=True, oceancolor=OCEAN,
        showcoastlines=True, coastlinecolor=COAST, coastlinewidth=0.8, showcountries=False,
        showframe=False, bgcolor="rgba(0,0,0,0)",
        lataxis=dict(showgrid=True, gridcolor=GRID, dtick=30),
        lonaxis=dict(showgrid=True, gridcolor=GRID, dtick=30),
    )
    fig.update_layout(height=360, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)")
    return fig


# Spins the globe slowly until the visitor touches it (click, drag, touch or scroll); a small
# button pauses or resumes it. Visitors who ask the system for reduced motion start paused.
# st.plotly_chart cannot animate on its own, so the figure is rendered as a small HTML
# component and rotated through Plotly.relayout.
_SPIN_SCRIPT = """
<style>
  html, body { margin: 0; background: transparent; }
  .wrap { position: relative; }
  #globe-toggle { position: absolute; top: 6px; left: 6px; z-index: 10; width: 34px; height: 34px;
                  border-radius: 999px; border: 1px solid rgba(148, 163, 184, 0.6); cursor: pointer;
                  background: rgba(148, 163, 184, 0.15); color: #94A3B8; font-size: 14px; }
  #globe-toggle:hover { background: rgba(234, 88, 12, 0.18); color: #EA580C; }
</style>
<script>
(function () {
  const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  function start() {
    const el = document.getElementById("globe");
    const btn = document.getElementById("globe-toggle");
    if (!el || !btn || !window.Plotly || !el.layout) { return setTimeout(start, 100); }
    let timer = null;
    const lon = () => ((el.layout.geo.projection.rotation || {}).lon || 0);
    const tick = () => Plotly.relayout(el, {"geo.projection.rotation.lon": ((lon() + 0.35 + 540) % 360) - 180});
    const set = (on) => {
      clearInterval(timer);
      timer = on ? setInterval(tick, 60) : null;
      btn.textContent = on ? "\\u23F8" : "\\u25B6";
      btn.setAttribute("aria-label", on ? "__PAUSE__" : "__PLAY__");
      btn.title = btn.getAttribute("aria-label");
    };
    ["mousedown", "touchstart", "wheel"].forEach((ev) => el.addEventListener(ev, () => set(false), {passive: true}));
    btn.addEventListener("click", () => set(timer === null));
    set(!reduce);
  }
  start();
})();
</script>
"""


def render_globe(fig: go.Figure) -> None:
    chart = fig.to_html(full_html=False, include_plotlyjs="cdn", div_id="globe",
                        config={"displayModeBar": False, "responsive": True})
    script = _SPIN_SCRIPT.replace("__PAUSE__", t("home.globe.pause")).replace("__PLAY__", t("home.globe.play"))
    html = f'<div class="wrap"><button id="globe-toggle" type="button"></button>{chart}</div>{script}'
    components.html(html, height=370)


hero, globe = st.columns([1.3, 1], gap="large", vertical_alignment="center")
with hero:
    st.markdown(f'<span class="gts-badge">{t("home.badge")}</span>', unsafe_allow_html=True)
    st.markdown('<div class="gts-hero">Query the Data.<br><span>Understand the Climate.</span></div>',
                unsafe_allow_html=True)
    st.markdown(f'<p class="gts-muted" style="font-size:1.15rem;line-height:1.6">{t("home.sub")}</p>',
                unsafe_allow_html=True)
    a, b, _ = st.columns([1, 1, 0.4])
    if a.button(t("home.exp.cta"), type="primary", icon=":material/monitoring:", width="stretch"):
        st.switch_page("views/explorer.py")
    if b.button(t("home.pg.cta"), icon=":material/terminal:", width="stretch"):
        st.switch_page("views/playground.py")

with globe, st.container(border=True):
    st.markdown(f"**{t('home.globe.title')}**")
    st.caption(t("home.globe.caption"))
    render_globe(globe_figure())
    with st.expander(t("sql.behind")):
        st.code(q.GLOBE, language="sql")

f1, f2, f3, f4 = st.columns(4)
last = f"{month_names()[facts.last_month.month - 1]} {facts.last_month.year}"
f1.metric(t("home.fact.range"), f"{facts.first_month:%Y}–{facts.last_month:%Y}", border=True)
f1.caption(f"→ {last}")
f2.metric(t("home.fact.base"), f"{facts.base_period_start}–{facts.base_period_end}", border=True)
f3.metric(t("home.fact.regions"), "14", border=True)
f3.caption(t("home.fact.regions.v"))
f4.metric(t("home.fact.version"), f"{facts.downloaded_at:%Y-%m-%d}", border=True)

st.subheader(t("home.findings"))
c1, c2, c3 = st.columns(3)
cool = f"{month_names()[findings.last_cool_month.month - 1]} {findings.last_cool_month.year}"
if st.session_state.get("lang", "en") == "tr":
    c1.info(f"**{cool}**: küresel olarak 1951–1980 ortalamasından serin olan son ay.")
    c2.info(f"**{findings.current_streak_months} ay** üst üste +1.0 °C ya da üzeri (en güncel seri).")
    c3.info(f"En sıcak 10 yılın **{findings.top10_since_2015}** tanesi 2015 ve sonrasında.")
else:
    c1.info(f"**{cool}**: the last month cooler than the 1951–1980 average, globally.")
    c2.info(f"**{findings.current_streak_months} months** in a row at or above +1.0 °C (the most recent streak).")
    c3.info(f"**{findings.top10_since_2015} of the 10** hottest years occurred in 2015 or later.")

st.subheader(t("home.choose"))
# One card per page, two per row; the sample count is read from sql/ so it never goes stale.
CARDS = [
    ("views/explorer.py", ":material/monitoring:", t("nav.explorer"), "home.exp", {}),
    ("views/map.py", ":material/map:", t("nav.map"), "home.map", {}),
    ("views/drivers.py", ":material/insights:", t("nav.drivers"), "home.drv", {}),
    ("views/playground.py", ":material/terminal:", t("nav.playground"), "home.pg", {"count": len(load_samples())}),
]
for row in (CARDS[:2], CARDS[2:]):
    for column, (page, icon, title, key, values) in zip(st.columns(2, gap="medium"), row, strict=True):
        with column, st.container(border=True, height="stretch"):
            st.markdown(f"#### {icon} {title}")
            st.caption(t(f"{key}.sub"))
            st.write(t(f"{key}.desc", **values))
            st.page_link(page, label=t(f"{key}.cta"), icon=":material/arrow_forward:")

footer()
