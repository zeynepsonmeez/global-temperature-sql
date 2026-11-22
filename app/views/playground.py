"""SQL Playground: write and run read-only SQL against the playground views."""

import plotly.graph_objects as go
import streamlit as st

import queries as q
from challenges import CHALLENGES, compare
from components import HEAT, footer, style_figure
from database import MAX_ROWS, friendly_error_key, read_df, run_user_query
from i18n import lang, t
from library import load_samples
from sql_guard import check_query

samples = load_samples()
sample_by_label = {s.label: s for s in samples}

st.session_state.setdefault("pg_sql", "")          # the editor starts empty
st.session_state.setdefault("pg_solved", set())
if "pg_pending_sql" in st.session_state:          # arriving from "Open in Playground"
    st.session_state["pg_sql"] = st.session_state.pop("pg_pending_sql")
    st.session_state["pg_result"] = st.session_state["pg_error"] = None


LEVELS = ["Basic", "Intermediate", "Advanced", "Spatial", "Drivers"]
# Playground views grouped by topic, in a sensible reading order.
SCHEMA_GROUPS = {
    "pg.schema.series": ["v_monthly", "v_annual", "regions", "datasets"],
    "pg.schema.spatial": ["v_grid", "v_grid_annual", "v_grid_trends", "v_country_annual",
                          "grid_cells", "countries", "cell_countries"],
    "pg.schema.drivers": ["v_enso", "v_co2", "model_results", "model_enso_adjusted", "model_breakpoints"],
}


def load_sample() -> None:
    choice = st.session_state.get("pg_sample")
    if choice:
        st.session_state["pg_sql"] = sample_by_label[choice].sql


st.title(t("nav.playground"))
left, center, right = st.columns([1.05, 2.6, 1.15], gap="medium")

# --- Left: sample queries first (the usual starting point), then the schema ---------------------
with left:
    with st.container(border=True):
        st.markdown(f"**{t('pg.samples')}** · {len(samples)}")
        level = st.pills(t("pg.level"), LEVELS, default="Basic", key="pg_level",
                         format_func=lambda name: t(f"pg.level.{name.lower()}"), label_visibility="collapsed")
        in_level = [s.label for s in samples if s.level == (level or "Basic")]
        st.selectbox(t("pg.samples.pick"), in_level, index=None, key="pg_sample", on_change=load_sample,
                     placeholder=t("pg.samples.pick"), label_visibility="collapsed")

    with st.container(border=True):
        st.markdown(f"**{t('pg.schema')}**")
        schema = read_df(q.SCHEMA)
        columns_of = {table: ", ".join(group.column_name) for table, group in schema.groupby("table_name")}
        for group_key, tables in SCHEMA_GROUPS.items():
            with st.expander(t(group_key), expanded=group_key == "pg.schema.series"):
                st.markdown("\n\n".join(f"**`{name}`**  \n{columns_of[name]}"
                                        for name in tables if name in columns_of))

# --- Center: editor and results --------------------------------------------------------------
with center:
    st.caption(t("pg.badges", rows=MAX_ROWS))
    sql = st.text_area(t("pg.editor"), key="pg_sql", height=300, label_visibility="collapsed",
                       placeholder=t("pg.placeholder"))
    run = st.button(t("pg.run"), type="primary", icon=":material/play_arrow:")

    if run:
        verdict = check_query(sql)
        if not verdict.ok:
            st.session_state["pg_result"] = None
            st.session_state["pg_error"] = (t("pg.blocked"), verdict.message)
        else:
            result = run_user_query(sql)
            if result.error is not None:
                st.session_state["pg_result"] = None
                detail = result.error.diag.message_primary or str(result.error)
                st.session_state["pg_error"] = (t(friendly_error_key(result.error)), detail)
            else:
                st.session_state["pg_result"] = result
                st.session_state["pg_error"] = None

    error = st.session_state.get("pg_error")
    result = st.session_state.get("pg_result")
    if error:
        title, detail = error
        st.error(f"**{title}**\n\n{detail}", icon=":material/block:")
    elif result is not None:
        frame = result.frame
        st.success(t("pg.ok", rows=len(frame), ms=result.elapsed_ms), icon=":material/check_circle:")
        if result.truncated:
            st.warning(t("pg.truncated", rows=MAX_ROWS))
        if frame.empty:
            st.info(t("pg.empty_result"))
        else:
            st.dataframe(frame, width="stretch", hide_index=True)
            st.download_button(t("sql.download"), frame.to_csv(index=False).encode("utf-8"),
                               file_name="query_result.csv", mime="text/csv", icon=":material/download:")
            numeric = [c for c in frame.columns if frame[c].dtype.kind in "if"]
            if len(frame.columns) >= 2 and numeric:
                with st.expander(t("pg.chart")):
                    a, b = st.columns(2)
                    x = a.selectbox(t("pg.chart.x"), list(frame.columns), key="pg_x")
                    y = b.selectbox(t("pg.chart.y"), [c for c in numeric if c != x] or numeric, key="pg_y")
                    data = frame.sort_values(x)
                    fig = go.Figure(go.Scatter(x=data[x], y=data[y], mode="lines+markers",
                                               line=dict(color=HEAT, width=2)))
                    st.plotly_chart(style_figure(fig, height=320, y_title=y), width="stretch")

# --- Right: challenges ------------------------------------------------------------------------------
with right, st.container(border=True):
    solved = st.session_state["pg_solved"]
    st.markdown(f"**{t('pg.challenges')}**")
    st.progress(len(solved) / len(CHALLENGES), text=t("pg.ch.progress", done=len(solved), total=len(CHALLENGES)))
    labels = [f"{'✓' if c.id in solved else '○'}  {i}. {c.topic}" for i, c in enumerate(CHALLENGES, 1)]
    index = st.radio(t("pg.challenges"), range(len(CHALLENGES)), format_func=lambda i: labels[i],
                     label_visibility="collapsed", key="pg_challenge")
    challenge = CHALLENGES[index]
    st.info(challenge.task[lang()])
    with st.expander(t("pg.ch.hint")):
        st.code(challenge.hint[lang()], language="sql", wrap_lines=True)
    if st.button(t("pg.ch.check"), width="stretch", icon=":material/fact_check:"):
        current = st.session_state.get("pg_result")
        if current is None or current.frame is None:
            st.warning(t("pg.ch.run_first"))
        else:
            reference = run_user_query(challenge.reference_sql).frame
            correct, reason, values = compare(current.frame, reference, challenge.ordered)
            if correct:
                solved.add(challenge.id)
                st.success(t("pg.ch.correct"))
                st.balloons()
            else:
                st.error(t("pg.ch.wrong", detail=t(reason, **values)))

footer()
