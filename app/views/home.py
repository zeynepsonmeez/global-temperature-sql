"""Home page: hero, rotatable latitude-band globe, dataset facts and the two entry points."""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

import queries as q
from components import COAST, GRID, LAND, OCEAN, WARM_SCALE, footer
from database import read_df, read_row
from i18n import month_names, t

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

    fig = go.Figure(go.Scattergeo(
        lat=lats, lon=lons, mode="markers",
        marker=dict(size=6, opacity=0.85, color=values, colorscale=WARM_SCALE, cmin=0, cmax=max(values),
                    line=dict(width=0),
                    colorbar=dict(title="°C", thickness=10, len=0.55, x=1.0)),
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
    fig.update_layout(height=430, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)")
    return fig


hero, globe = st.columns([1.05, 1], gap="large", vertical_alignment="center")
with hero:
    st.markdown(f'<span class="gts-badge">{t("home.badge")}</span>', unsafe_allow_html=True)
    st.markdown('<div class="gts-hero">Query the Data.<br><span>Understand the Climate.</span></div>',
                unsafe_allow_html=True)
    st.markdown(f'<p class="gts-muted" style="font-size:1.15rem;line-height:1.6">{t("home.sub")}</p>',
                unsafe_allow_html=True)
    a, b = st.columns(2)
    a.page_link("views/explorer.py", label=t("home.exp.cta"), icon=":material/monitoring:")
    b.page_link("views/playground.py", label=t("home.pg.cta"), icon=":material/terminal:")

with globe:
    with st.container(border=True):
        st.markdown(f"**{t('home.globe.title')}**")
        st.caption(t("home.globe.caption"))
        st.plotly_chart(globe_figure(), width="stretch", config={"displayModeBar": False})
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
left, right = st.columns(2, gap="large")
with left, st.container(border=True):
    st.markdown("### :material/monitoring: Climate Explorer")
    st.caption(t("home.exp.sub"))
    st.write(t("home.exp.desc"))
    st.page_link("views/explorer.py", label=t("home.exp.cta"), icon=":material/arrow_forward:")
with right, st.container(border=True):
    st.markdown("### :material/terminal: SQL Playground")
    st.caption(t("home.pg.sub"))
    st.write(t("home.pg.desc"))
    st.code("SELECT year, anomaly,\n       RANK() OVER (ORDER BY anomaly DESC)\nFROM   v_monthly\nWHERE  region = 'GLB'\nLIMIT  10;",
            language="sql")
    st.page_link("views/playground.py", label=t("home.pg.cta"), icon=":material/arrow_forward:")

footer()
