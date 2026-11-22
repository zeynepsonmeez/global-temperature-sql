"""Climate Explorer: ready-made analyses with filters. Every chart comes from app/queries.py."""

import plotly.graph_objects as go
import streamlit as st

import queries as q
from components import (COOL, DIVERGING, GRID, HEAT, HEAT_LIGHT, MUTED, REGION_COLORS,
                        footer, sql_panel, style_figure)
from database import read_df, read_row
from i18n import month_names, t

latest_year = read_row(q.FACTS).last_month.year
REGIONS = ["GLB", "NH", "SH"]

# --- Filters --------------------------------------------------------------------------
st.sidebar.header(t("exp.filters"))
start, end = st.sidebar.slider(t("exp.years"), 1880, latest_year, (1880, latest_year))
regions = st.sidebar.multiselect(
    t("exp.regions"), REGIONS, default=["GLB"], format_func=lambda c: t(f"region.{c}"),
)
month_options = [0, *range(1, 13)]
month = st.sidebar.selectbox(
    t("exp.month"), month_options,
    format_func=lambda m: t("exp.month.annual") if m == 0 else month_names()[m - 1],
)
smooth = st.sidebar.toggle(t("exp.smooth"), value=True)
st.sidebar.caption(t("footer.data"))

if not regions:
    st.warning(t("exp.pick_region"))
    st.stop()
focus = regions[0]  # single-region charts use the first selected region
period = {"start": start, "end": end}

st.title(t("nav.explorer"))

# --- Headline numbers ---------------------------------------------------------------
kpi = read_row(q.KPIS, {"region": focus})
k1, k2, k3, k4 = st.columns(4)
k1.metric(f"{t('kpi.latest')} ({kpi.latest_year})", f"{kpi.latest_anomaly:+.2f} °C")
k2.metric(t("kpi.rate"), f"{kpi.rate_since_1970:+.2f} {t('unit.decade')}")
k3.metric(t("kpi.hottest"), f"{kpi.hottest_year}", f"{kpi.hottest_anomaly:+.2f} °C", delta_color="off", delta_arrow="off")
k4.metric(t("kpi.nulls"), f"{kpi.null_months}")
st.caption(f"{t(f'region.{focus}')} · GISTEMP v4")

tabs = st.tabs([t("tab.trend"), t("tab.hottest"), t("tab.decades"), t("tab.hemis"),
                t("tab.monthly"), t("tab.records"), t("tab.bands")])

# 1. Trend ------------------------------------------------------------------------------
with tabs[0]:
    params = {"regions": regions, "month": month, **period}
    df = read_df(q.TREND, params)
    st.subheader(t("trend.title"))
    fig = go.Figure()
    for region in regions:
        part = df[df.region == region]
        color = REGION_COLORS[region]
        fig.add_scatter(x=part.year, y=part.anomaly, name=t(f"region.{region}"), mode="lines",
                        line=dict(color=color, width=1.2), opacity=0.45 if smooth else 1)
        if smooth:
            fig.add_scatter(x=part.year, y=part.moving_avg_5y, mode="lines",
                            name=f"{t(f'region.{region}')} · 5y", line=dict(color=color, width=3))
    st.plotly_chart(style_figure(fig), width="stretch")
    st.caption(t("trend.note"))
    sql_panel(q.TREND, params, df, "trend")

# 2. Hottest years ------------------------------------------------------------------------
with tabs[1]:
    params = {"region": focus, **period}
    df = read_df(q.HOTTEST, params)
    st.subheader(f"{t('hottest.title')} · {t(f'region.{focus}')}")
    ordered = df.sort_values("anomaly")
    fig = go.Figure(go.Bar(
        x=ordered.anomaly, y=ordered.year.astype(str), orientation="h",
        marker_color=HEAT, text=[f"#{r}  {a:+.2f}" for r, a in zip(ordered["rank"], ordered.anomaly)],
        textposition="outside", hovertemplate="%{y}: %{x:+.2f} °C<extra></extra>",
    ))
    fig = style_figure(fig, height=440, y_title="")
    fig.update_xaxes(title_text="°C", showgrid=True, gridcolor=GRID)
    fig.update_layout(hovermode="closest")
    st.plotly_chart(fig, width="stretch")
    st.caption(t("hottest.note"))
    sql_panel(q.HOTTEST, params, df, "hottest_years")

# 3. Decades ------------------------------------------------------------------------------
with tabs[2]:
    params = {"regions": regions, **period}
    df = read_df(q.DECADES, params)
    st.subheader(t("decades.title"))
    fig = go.Figure()
    for region in regions:
        part = df[df.region == region]
        fig.add_bar(x=part.decade.astype(str) + "s", y=part.anomaly, name=t(f"region.{region}"),
                    marker_color=REGION_COLORS[region])
    fig = style_figure(fig)
    fig.update_layout(barmode="group", hovermode="closest")
    st.plotly_chart(fig, width="stretch")
    st.caption(t("decades.note"))
    sql_panel(q.DECADES, params, df, "decades")

# 4. Hemispheres ----------------------------------------------------------------------------
with tabs[3]:
    params = dict(period)
    df = read_df(q.HEMISPHERES, params)
    st.subheader(t("hemis.title"))
    fig = go.Figure()
    fig.add_scatter(x=df.year, y=df.nh, name=t("region.NH"), line=dict(color=REGION_COLORS["NH"], width=2))
    fig.add_scatter(x=df.year, y=df.sh, name=t("region.SH"), line=dict(color=COOL, width=2))
    fig.add_bar(x=df.year, y=df.nh_minus_sh, name="NH − SH", marker_color=HEAT_LIGHT, opacity=0.6)
    st.plotly_chart(style_figure(fig), width="stretch")
    st.caption(t("hemis.note"))
    sql_panel(q.HEMISPHERES, params, df, "hemispheres")

# 5. Monthly patterns -------------------------------------------------------------------------
with tabs[4]:
    params = {"region": focus, **period}
    grid = read_df(q.MONTHLY_GRID, params)
    st.subheader(f"{t('monthly.title')} · {t(f'region.{focus}')}")
    pivot = grid.pivot(index="month", columns="year", values="anomaly")
    limit = float(grid.anomaly.abs().max())
    heat = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns, y=month_names(), colorscale=DIVERGING,
        zmin=-limit, zmax=limit, colorbar=dict(title="°C", thickness=10),
        hovertemplate="%{y} %{x}: %{z:+.2f} °C<extra></extra>",
    ))
    heat = style_figure(heat, height=380, y_title="")
    heat.update_yaxes(autorange="reversed", zeroline=False)
    heat.update_layout(hovermode="closest")
    st.plotly_chart(heat, width="stretch")
    sql_panel(q.MONTHLY_GRID, params, grid, "monthly_grid")

    rates = read_df(q.MONTHLY_RATES, params)
    st.markdown(f"**{t('monthly.rates')}** ({start}–{end})")
    bars = go.Figure(go.Bar(x=month_names(), y=rates.rate_per_decade, marker_color=HEAT,
                            hovertemplate="%{x}: %{y:+.3f}<extra></extra>"))
    bars = style_figure(bars, height=300, y_title=t("unit.decade"))
    bars.update_layout(hovermode="closest")
    st.plotly_chart(bars, width="stretch")
    st.caption(t("monthly.note"))
    sql_panel(q.MONTHLY_RATES, params, rates, "monthly_rates")

# 6. Records ----------------------------------------------------------------------------------
with tabs[5]:
    params = {"region": focus, **period}
    df = read_df(q.RECORDS, params)
    st.subheader(f"{t('records.title')} · {t(f'region.{focus}')}")
    records = df[df.is_record]
    fig = go.Figure()
    fig.add_scatter(x=df.year, y=df.anomaly, mode="lines", line=dict(color=MUTED, width=1.2),
                    name=t("trend.title"), showlegend=False)
    fig.add_scatter(x=records.year, y=records.anomaly, mode="markers+text", name=t("records.legend"),
                    marker=dict(color=HEAT, size=9), text=records.year.astype(str),
                    textposition="top center", textfont=dict(size=10))
    st.plotly_chart(style_figure(fig, height=440), width="stretch")
    st.caption(t("records.note"))
    sql_panel(q.RECORDS, params, df, "records")

# 7. Latitude bands -----------------------------------------------------------------------------
with tabs[6]:
    params = dict(period)
    df = read_df(q.BANDS, params)
    st.subheader(t("bands.title"))
    labels = [f"{code}  ·  {name}" for code, name in zip(df.code, df.name)]
    fig = go.Figure(go.Bar(
        x=df.rate_per_decade, y=labels, orientation="h", marker_color=HEAT,
        text=[f"{v:+.2f}" for v in df.rate_per_decade], textposition="outside",
        hovertemplate="%{y}: %{x:+.3f}<extra></extra>",
    ))
    fig = style_figure(fig, height=420, y_title="")
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title_text=t("unit.decade"), showgrid=True, gridcolor=GRID)
    fig.update_layout(hovermode="closest")
    st.plotly_chart(fig, width="stretch")
    st.caption(t("bands.note"))
    sql_panel(q.BANDS, params, df, "latitude_bands")

footer()
