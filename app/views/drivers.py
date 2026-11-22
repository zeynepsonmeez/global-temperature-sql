"""Climate Drivers: ENSO, CO2 and the regression model (scripts/run_models.py, docs/METHODS.md)."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import queries as q
from components import COOL, GRID, HEAT, HEAT_LIGHT, MUTED, footer, sql_panel, style_figure
from database import read_df
from i18n import t

EL_NINO, LA_NINA = "#E11D48", "#3B82F6"

st.title(t("nav.drivers"))
st.caption(t("drv.intro"))

results = read_df(q.MODEL_RESULTS).set_index("metric")
if results.empty:
    st.warning("Run `python scripts/run_models.py` to compute the model results.")
    st.stop()
m = results.value.to_dict()

k1, k2, k3, k4 = st.columns(4)
k1.metric(t("drv.kpi.lag"), f"{m['enso_lag_months']:.0f} {t('drv.months')}", border=True)
k2.metric(t("drv.kpi.coef"), f"{m['enso_coefficient']:+.3f}", t("drv.kpi.coef.unit"),
          delta_color="off", delta_arrow="off", border=True)
k3.metric(t("drv.kpi.trend"), f"{m['trend_monthly_hac']:+.2f}", t("unit.decade"),
          delta_color="off", delta_arrow="off", border=True)
k4.metric(t("drv.kpi.r2"), f"{m['r2_trend_only']:.0%} → {m['r2_trend_enso']:.0%}", border=True)
st.info(t("drv.caution"), icon=":material/info:")

enso_tab, records_tab, trend_tab, co2_tab = st.tabs(
    [t("drv.tab.enso"), t("drv.tab.records"), t("drv.tab.trend"), t("drv.tab.co2")])

# 1. ENSO ----------------------------------------------------------------------------------------
with enso_tab:
    series = read_df(q.ENSO_TEMP)
    st.subheader(t("drv.enso.title"))
    colors = series.phase.map({"El Nino": EL_NINO, "La Nina": LA_NINA}).fillna(MUTED)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06, row_heights=[0.45, 0.55])
    fig.add_bar(x=series.obs_date, y=series.oni, marker_color=colors, name=t("drv.oni"),
                hovertemplate="%{x|%b %Y}: ONI %{y:+.2f}<extra></extra>", row=1, col=1)
    fig.add_scatter(x=series.obs_date, y=series.anomaly, mode="lines", line=dict(color=HEAT, width=1.4),
                    name=t("region.GLB"), hovertemplate="%{x|%b %Y}: %{y:+.2f} °C<extra></extra>", row=2, col=1)
    fig = style_figure(fig, height=520, y_title="")
    fig.update_yaxes(title_text="ONI", row=1, col=1)
    fig.update_yaxes(title_text="°C", row=2, col=1)
    fig.update_layout(showlegend=False, bargap=0, hovermode="closest")
    st.plotly_chart(fig, width="stretch")
    st.caption(t("drv.enso.note"))
    sql_panel(q.ENSO_TEMP, {}, series, "enso_temperature")

    left, right = st.columns(2, gap="large")
    with left:
        phases = read_df(q.library("D2"))
        st.markdown(f"**{t('drv.phase.title')}**")
        fig = go.Figure(go.Bar(
            x=phases.phase, y=phases.mean_departure_from_trend,
            marker_color=phases.phase.map({"El Nino": EL_NINO, "La Nina": LA_NINA}).fillna(MUTED),
            text=[f"{v:+.3f} °C" for v in phases.mean_departure_from_trend], textposition="outside",
            hovertemplate="%{x}: %{y:+.3f} °C<extra></extra>",
        ))
        fig = style_figure(fig, height=320)
        fig.update_layout(hovermode="closest")
        st.plotly_chart(fig, width="stretch")
        st.caption(t("drv.phase.note"))
        sql_panel(q.library("D2"), {}, phases, "enso_phases")
    with right:
        lags = read_df(q.library("D3"))
        st.markdown(f"**{t('drv.lag.title')}**")
        best = int(lags.loc[lags.correlation.idxmax(), "lag_months"])
        fig = go.Figure(go.Bar(
            x=lags.lag_months, y=lags.correlation,
            marker_color=[HEAT if k == best else HEAT_LIGHT for k in lags.lag_months],
            hovertemplate="%{x}: r = %{y:.3f}<extra></extra>",
        ))
        fig = style_figure(fig, height=320, y_title="r")
        fig.update_xaxes(title_text=t("drv.lag.axis"), dtick=1)
        fig.update_layout(hovermode="closest")
        st.plotly_chart(fig, width="stretch")
        st.caption(t("drv.lag.note"))
        sql_panel(q.library("D3"), {}, lags, "enso_lags")

# 2. Records without ENSO ---------------------------------------------------------------------------
with records_tab:
    annual = read_df(q.ADJUSTED_ANNUAL)
    st.subheader(t("drv.records.title"))
    fig = go.Figure()
    fig.add_scatter(x=annual.year, y=annual.observed, name=t("drv.observed"), mode="lines+markers",
                    line=dict(color=HEAT, width=2), marker=dict(size=5))
    fig.add_scatter(x=annual.year, y=annual.adjusted, name=t("drv.adjusted"), mode="lines+markers",
                    line=dict(color=COOL, width=2, dash="dot"), marker=dict(size=5))
    st.plotly_chart(style_figure(fig, height=420), width="stretch")
    sql_panel(q.ADJUSTED_ANNUAL, {}, annual, "enso_adjusted")

    ranking = read_df(q.library("D8"))
    st.markdown(f"**{t('drv.records.rank')}**")
    st.dataframe(ranking, hide_index=True, width="stretch")
    st.caption(t("drv.records.note"))
    sql_panel(q.library("D8"), {}, ranking, "records_without_enso")

# 3. Trend and breakpoint -----------------------------------------------------------------------------
with trend_tab:
    annual = read_df(q.ANNUAL_GLOBAL)
    profile = read_df(q.BREAK_PROFILE)
    year, low, high = (int(results.loc["break_year", c]) for c in ("value", "ci_low", "ci_high"))
    st.subheader(t("drv.trend.title"))

    # Re-draw the best two-segment fit (the same least-squares hinge model as run_models.py).
    x, y = annual.year.to_numpy(float), annual.anomaly.to_numpy(float)
    X = np.column_stack([np.ones_like(x), x, np.maximum(0, x - year)])
    fitted = X @ np.linalg.lstsq(X, y, rcond=None)[0]

    fig = go.Figure()
    fig.add_vrect(x0=low, x1=high, fillcolor=HEAT_LIGHT, opacity=0.18, line_width=0)
    fig.add_scatter(x=x, y=y, mode="markers", marker=dict(color=MUTED, size=5), name=t("region.GLB"))
    fig.add_scatter(x=x, y=fitted, mode="lines", line=dict(color=HEAT, width=3), name=t("drv.trend.fit"))
    st.plotly_chart(style_figure(fig, height=420), width="stretch")
    st.markdown(t("drv.trend.break", year=year, low=low, high=high,
                  before=m["slope_before_break"], after=m["slope_after_break"]))

    fig = go.Figure(go.Scatter(x=profile.break_year, y=profile.sse, mode="lines", line=dict(color=HEAT, width=2),
                               hovertemplate="%{x}: %{y:.3f}<extra></extra>"))
    fig.add_vline(x=year, line_color=MUTED, line_dash="dash")
    fig = style_figure(fig, height=260, y_title=t("drv.profile.axis"))
    fig.update_layout(hovermode="closest")
    st.markdown(f"**{t('drv.profile.title')}**")
    st.plotly_chart(fig, width="stretch")
    sql_panel(q.BREAK_PROFILE, {}, profile, "breakpoints")

    st.markdown(f"**{t('drv.ci.title')}**")
    rows = []
    for series_key, label in (("monthly", t("drv.ci.monthly")), ("annual", t("drv.ci.annual"))):
        for method_key, method in (("naive", t("drv.ci.classical")), ("hac", "Newey-West")):
            r = results.loc[f"trend_{series_key}_{method_key}"]
            rows.append({t("drv.ci.col.series"): label, t("drv.ci.col.method"): method,
                         t("drv.ci.col.trend"): round(r.value, 3),
                         t("drv.ci.col.ci"): f"[{r.ci_low:+.3f}, {r.ci_high:+.3f}]",
                         t("drv.ci.col.width"): round((r.ci_high - r.ci_low) / 2, 3)})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption(t("drv.ci.note", ac=m["residual_autocorrelation_lag1"]))
    sql_panel(q.MODEL_RESULTS, {}, results.reset_index(), "model_results")

# 4. CO2 ----------------------------------------------------------------------------------------------------
with co2_tab:
    co2 = read_df(q.CO2_MONTHLY)
    st.subheader(t("drv.co2.title"))
    fig = go.Figure()
    fig.add_scatter(x=co2.obs_date, y=co2.co2_ppm, name=t("drv.co2.monthly"), mode="lines",
                    line=dict(color=HEAT_LIGHT, width=1))
    fig.add_scatter(x=co2.obs_date, y=co2.co2_deseason, name=t("drv.co2.trend"), mode="lines",
                    line=dict(color=HEAT, width=2.5))
    st.plotly_chart(style_figure(fig, height=380, y_title="ppm"), width="stretch")
    sql_panel(q.CO2_MONTHLY, {}, co2, "co2_monthly")

    pairs = read_df(q.CO2_TEMP_ANNUAL)
    stats = read_df(q.library("D7")).iloc[0]
    slope, intercept = np.polyfit(pairs.co2_ppm, pairs.anomaly, 1)
    line_x = np.array([pairs.co2_ppm.min(), pairs.co2_ppm.max()])
    st.markdown(f"**{t('drv.scatter.title')}**")
    fig = go.Figure()
    fig.add_scatter(x=pairs.co2_ppm, y=pairs.anomaly, mode="markers", text=pairs.year,
                    marker=dict(color=pairs.year, colorscale=[[0, "#FDE68A"], [1, "#E11D48"]], size=8,
                                line=dict(width=0.5, color=GRID)),
                    hovertemplate="%{text}: %{x:.1f} ppm, %{y:+.2f} °C<extra></extra>", showlegend=False)
    fig.add_scatter(x=line_x, y=slope * line_x + intercept, mode="lines", line=dict(color=MUTED, dash="dash"),
                    showlegend=False)
    fig = style_figure(fig, height=400)
    fig.update_xaxes(title_text="CO₂ (ppm)")
    fig.update_layout(hovermode="closest")
    st.plotly_chart(fig, width="stretch")
    st.caption(t("drv.scatter.note", slope=stats.degrees_per_100_ppm, r2=stats.r_squared,
                 first=int(stats.from_year), last=int(stats.to_year)))
    sql_panel(q.library("D7"), {}, pairs, "co2_temperature")

footer()
