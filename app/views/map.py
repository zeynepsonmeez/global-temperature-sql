"""Warming Map: country choropleth, 2°x2° grid map and country comparison (PostGIS)."""

import plotly.graph_objects as go
import streamlit as st

import queries as q
from components import (
    COAST,
    COMPARE_COLORS,
    DIVERGING,
    GRID,
    LAND,
    MUTED,
    OCEAN,
    WARM_SCALE,
    footer,
    sql_panel,
    style_figure,
)
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

# 3. Compare countries ------------------------------------------------------------------------------
with country_tab:
    options = read_df(q.COUNTRY_LIST)
    names = dict(zip(options.adm0_a3, options.country, strict=True))
    picked = st.multiselect(t("map.compare.pick"), list(names), default=["TUR"] if "TUR" in names else [],
                            format_func=names.get, max_selections=len(COMPARE_COLORS), key="map_countries")
    smooth = st.toggle(t("exp.smooth"), value=True, key="map_smooth")
    params = {"countries": picked}
    series = read_df(q.COUNTRY_COMPARE, params)
    stats = read_df(q.COUNTRY_COMPARE_STATS, params)

    st.subheader(t("map.compare.title"))
    if not picked:
        st.info(t("map.compare.empty"))

    # Global mean first (grey, behind), then each country in its own colour.
    fig = go.Figure()
    order = ["GLB", *picked]
    colors = {"GLB": MUTED, **dict(zip(picked, COMPARE_COLORS, strict=False))}
    for code in order:
        part = series[series.code == code]
        label = t("map.global") if code == "GLB" else names[code]
        y = part.moving_avg_5y if smooth else part.anomaly
        dash = "dash" if code == "GLB" else "solid"
        fig.add_scatter(x=part.year, y=y, name=label, mode="lines",
                        line=dict(color=colors[code], width=3 if code != "GLB" else 2.5, dash=dash))
    st.plotly_chart(style_figure(fig, height=460), width="stretch")

    # Comparison table: rate, recent mean and how many times faster than the globe.
    global_rate = float(stats.loc[stats.code == "GLB", "rate_since_1970"].iloc[0])
    table = stats.assign(
        name=[t("map.global") if c == "GLB" else names[c] for c in stats.code],
        ratio=(stats.rate_since_1970 / global_rate).round(1),
    )[["name", "rate_since_1970", "mean_last_10y", "ratio"]].rename(columns={
        "name": t("map.compare.col.name"),
        "rate_since_1970": f"{t('map.country.rate')} ({t('unit.decade')})",
        "mean_last_10y": f"{t('map.country.recent')} (°C)",
        "ratio": t("map.country.ratio"),
    })
    st.dataframe(table, hide_index=True, width="stretch")
    st.caption(t("map.country.note"))
    sql_panel(q.COUNTRY_COMPARE, params, series, "country_compare")

footer()
