"""Warming Map: country choropleth, 2°x2° grid map and single-country series (PostGIS)."""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

import queries as q
from components import (COAST, DIVERGING, GRID, HEAT, LAND, MUTED, OCEAN, WARM_SCALE,
                        footer, sql_panel, style_figure)
from database import read_df, read_row
from i18n import t

years = read_row(q.GRID_YEARS)
first_year, last_year = int(years.first_year), int(years.last_year)

st.title(t("nav.map"))
st.caption(t("map.intro"))


def base_geo(fig: go.Figure, projection: str = "natural earth") -> go.Figure:
    fig.update_geos(
        projection_type=projection, showframe=False, bgcolor="rgba(0,0,0,0)",
        showland=True, landcolor=LAND, showocean=True, oceancolor=OCEAN,
        showcoastlines=True, coastlinecolor=COAST, coastlinewidth=0.6,
        showcountries=True, countrycolor=GRID, lataxis=dict(range=[-60, 85]),
    )
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)")
    return fig


countries_tab, grid_tab, country_tab = st.tabs([t("map.tab.countries"), t("map.tab.grid"), t("map.tab.country")])

# 1. Countries -------------------------------------------------------------------------------
with countries_tab:
    start, end = st.slider(t("map.period"), first_year, last_year, (1970, last_year), key="map_period")
    params = {"start": start, "end": end}
    rates = read_df(q.COUNTRY_RATES, params)
    st.subheader(f"{t('map.countries.title')} · {start}–{end}")
    fig = go.Figure(go.Choropleth(
        locations=rates.iso3, z=rates.rate_per_decade, text=rates.country,
        colorscale=WARM_SCALE, zmin=0, zmax=float(rates.rate_per_decade.quantile(0.98)),
        marker_line_color=COAST, marker_line_width=0.3,
        colorbar=dict(title=t("unit.decade"), thickness=10, len=0.6),
        hovertemplate="%{text}: %{z:+.2f} °C / decade<extra></extra>",
    ))
    st.plotly_chart(base_geo(fig), width="stretch")
    st.caption(t("map.countries.note"))

    st.markdown(f"**{t('map.top')}**")
    top = rates.head(10)[["country", "continent", "rate_per_decade", "mean_last_10y"]]
    st.dataframe(top, hide_index=True, width="stretch")
    sql_panel(q.COUNTRY_RATES, params, rates, "country_rates")

# 2. Grid ---------------------------------------------------------------------------------------
with grid_tab:
    year = st.slider(t("map.grid.year"), first_year, last_year, last_year, key="map_year")
    params = {"year": year}
    cells = read_df(q.GRID_YEAR, params)
    st.subheader(f"{t('map.grid.title')} · {year}")
    fig = go.Figure(go.Scattergeo(
        lat=cells.lat, lon=cells.lon, mode="markers",
        marker=dict(symbol="square", size=5.2, color=cells.anomaly, colorscale=DIVERGING,
                    cmin=-4, cmax=4, line=dict(width=0), colorbar=dict(title="°C", thickness=10, len=0.6)),
        hovertemplate="%{lat:.0f}°, %{lon:.0f}°: %{marker.color:+.2f} °C<extra></extra>",
    ))
    st.plotly_chart(base_geo(fig, "equirectangular"), width="stretch")
    st.caption(t("map.grid.note"))
    sql_panel(q.GRID_YEAR, params, cells, f"grid_{year}")

# 3. One country ------------------------------------------------------------------------------------
with country_tab:
    options = read_df(q.COUNTRY_LIST)
    names = dict(zip(options.adm0_a3, options.country))
    codes = list(names)
    country = st.selectbox(t("map.country.pick"), codes, format_func=names.get,
                           index=codes.index("TUR") if "TUR" in codes else 0, key="map_country")
    params = {"country": country}
    series = read_df(q.COUNTRY_SERIES, params)
    recent = series[series.year > series.year.max() - 10]
    since_1970 = series[series.year >= 1970]
    rate =np.polyfit(since_1970.year, since_1970.country, 1)[0] * 10
    global_rate = np.polyfit(since_1970.year, since_1970["global"], 1)[0] * 10

    st.subheader(t("map.country.title", country=names[country]))
    k1, k2, k3 = st.columns(3)
    k1.metric(t("map.country.rate"), f"{rate:+.2f} {t('unit.decade')}", border=True)
    k2.metric(t("map.country.recent"), f"{recent.country.mean():+.2f} °C", border=True)
    k3.metric(t("map.country.ratio"), f"× {rate / global_rate:.1f}", border=True)

    fig = go.Figure()
    fig.add_scatter(x=series.year, y=series.country, name=names[country], line=dict(color=HEAT, width=2))
    fig.add_scatter(x=series.year, y=series["global"], name=t("map.global"), line=dict(color=MUTED, width=2))
    st.plotly_chart(style_figure(fig), width="stretch")
    st.caption(t("map.country.note"))
    sql_panel(q.COUNTRY_SERIES, params, series, f"country_{country}")

footer()
