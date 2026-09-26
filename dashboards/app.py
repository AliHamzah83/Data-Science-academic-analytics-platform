from __future__ import annotations

import streamlit as st

from dashboards.data import DashboardDataError, load_student_terms, load_terms
from dashboards.pages import academic_risk, department_analytics, executive_overview, program_analytics, student_drilldown
from dashboards.pages.common import filter_cohort

PAGES = (
    "Executive Overview",
    "Academic Risk Analysis",
    "Department Analytics",
    "Program Analytics",
    "Student Drill Down",
)
PAGE_DESCRIPTIONS = {
        "Executive Overview": "Institution-wide health, risk mix, and leadership priorities.",
        "Academic Risk Analysis": "Risk-score distribution, recorded signals, and highest-priority students.",
        "Department Analytics": "Compare departmental risk exposure and academic outcomes.",
        "Program Analytics": "Compare program-level risk, GPA, attendance, and cohort size.",
        "Student Drill Down": "Review an individual student's academic and risk history.",
}

THEME_CSS = """
<style>
:root {
    --ink: #1d3534;
    --ink-soft: #5d706e;
    --forest: #183f3b;
    --teal: #397a78;
    --paper: #f3f6f4;
    --line: #d9e3df;
    --white: #ffffff;
    --high: #c4473a;
    --medium: #d9952b;
    --low: #438a68;
}
.stApp, [data-testid="stAppViewContainer"] { background: var(--paper); color: var(--ink); }
[data-testid="stHeader"] { background: rgba(243,246,244,.94); }
[data-testid="stSidebar"] { background: #e9efec; border-right: 1px solid var(--line); }
[data-testid="stSidebar"] h1 { color: var(--forest); font-family: "Aptos Display", Georgia, serif; font-size: 1.36rem; }
h1, h2, h3 { color: var(--ink); font-family: "Aptos Display", Georgia, serif; letter-spacing: 0; }
h1 { font-size: 2.2rem; }
[data-testid="stMainBlockContainer"] { padding-top: 3.2rem; padding-bottom: 1.5rem; max-width: 1500px; }
[data-testid="stCaptionContainer"] { color: var(--ink-soft); }
[data-testid="stMetric"] {
    background: var(--white); border: 1px solid var(--line); border-top: 3px solid var(--teal);
    border-radius: 6px; padding: 18px 20px; min-height: 120px;
    box-shadow: 0 4px 14px rgba(26, 59, 52, .07);
}
[data-testid="stMetricLabel"] { color: var(--ink-soft); font-weight: 650; }
[data-testid="stMetricValue"] { color: var(--ink); font-weight: 740; font-size: 2rem; }
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
[data-testid="stExpander"] { border: 1px solid var(--line); border-radius: 6px; background: rgba(255,255,255,.72); }
.brand-header { display:flex; align-items:center; justify-content:space-between; gap:20px; padding:18px 24px; margin:2px 0 26px; background:linear-gradient(105deg,#173f3b 0%,#285a53 67%,#397a78 100%); border-radius:7px; box-shadow:0 5px 16px rgba(25,60,54,.14); }
.brand-title { color:#fff; font-family:"Aptos Display",Georgia,serif; font-size:1.6rem; font-weight:700; line-height:1.15; }
.brand-subtitle { color:#dcebe6; font-size:.92rem; margin-top:5px; }
.brand-mark { display:flex; align-items:center; justify-content:center; width:48px; height:48px; flex:0 0 48px; color:#173f3b; background:#edf5f1; border-radius:6px; font-size:1.55rem; font-weight:800; }
.brand-version { color:#dcebe6; border:1px solid rgba(255,255,255,.35); border-radius:4px; padding:6px 9px; white-space:nowrap; font-size:.76rem; }
.sidebar-brand { display:flex; align-items:center; gap:11px; padding:8px 2px 16px; margin-bottom:12px; border-bottom:1px solid #ccd9d4; }
.sidebar-crest { display:flex; width:39px; height:39px; align-items:center; justify-content:center; border-radius:5px; background:var(--forest); color:#f3f6f4; font-size:1.2rem; font-weight:700; }
.sidebar-brand strong { display:block; color:var(--forest); font-size:.9rem; line-height:1.2; }
.sidebar-brand span { display:block; color:var(--ink-soft); font-size:.72rem; margin-top:3px; }
.sidebar-meta { border-top:1px solid #ccd9d4; margin-top:12px; padding:12px 2px 2px; color:var(--ink-soft); font-size:.76rem; line-height:1.6; }
.page-heading { padding-bottom:12px; margin-bottom:18px; border-bottom:1px solid var(--line); }
.page-heading h1 { margin-bottom:3px; }
.section-heading { display:flex; align-items:center; gap:10px; margin:20px 0 10px; }
.section-heading:after { content:""; height:1px; flex:1; background:var(--line); }
.welcome-panel { display:flex; align-items:center; justify-content:space-between; gap:20px; padding:19px 22px; margin:0 0 16px; border:1px solid #d6e2dc; border-left:4px solid var(--teal); border-radius:6px; background:#fff; box-shadow:0 3px 11px rgba(26,59,52,.045); }
.welcome-panel strong { display:block; color:var(--forest); font-family:"Aptos Display",Georgia,serif; font-size:1.18rem; margin-bottom:4px; }
.welcome-panel span { display:block; color:var(--ink-soft); font-size:.9rem; line-height:1.45; }
.welcome-mark { color:var(--teal); font-size:1.5rem; padding:0 8px; }
.app-footer { display:flex; justify-content:space-between; gap:12px; margin:28px 0 0; padding:10px 0 2px; color:#526763; background:transparent; border-top:1px solid #d9e3df; font-size:.74rem; }
.story-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin: 12px 0 20px; }
.story-card { background: var(--white); border: 1px solid var(--line); border-left: 4px solid var(--teal); border-radius: 5px; padding: 15px 17px; min-height: 100px; box-shadow:0 3px 11px rgba(26,59,52,.045); }
.story-card strong { color: var(--forest); display: block; margin-bottom: 6px; font-size: .88rem; }
.story-card span { color: var(--ink-soft); font-size: .9rem; line-height: 1.45; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 16px 0 22px; }
.kpi-card { background: #fff; border: 1px solid var(--line); border-top: 3px solid var(--teal); border-radius: 6px; padding: 15px 17px; min-height: 104px; box-shadow:0 4px 14px rgba(26,59,52,.07); }
.kpi-card .kpi-label { color: var(--ink-soft); font-size: .78rem; font-weight: 700; text-transform: uppercase; }
.kpi-card .kpi-value { color: var(--ink); font-size: 1.72rem; font-weight: 740; margin-top: 10px; line-height:1.15; }
.kpi-card.high { border-top-color: var(--high); }
.kpi-card.medium { border-top-color: var(--medium); }
.kpi-card.low { border-top-color: var(--low); }
.health-panel { background: var(--forest); color: #fff; padding: 18px 22px; border-radius: 6px; margin: 12px 0 16px; display: flex; align-items: center; justify-content: space-between; gap: 18px; }
.health-panel small { color: #d1e3dc; display: block; font-size: .86rem; margin-bottom: 4px; }
.health-panel strong { font-size: 2.15rem; line-height: 1; }
.health-panel p { color: #e8f1ed; max-width: 660px; margin: 0; }
.action-list { background: #fff; border: 1px solid var(--line); border-radius: 6px; padding: 14px 20px 14px 38px; }
.action-list li { padding: 5px 0; color: var(--ink-soft); }
@media (max-width: 700px) {
    .health-panel { align-items: flex-start; flex-direction: column; }
    [data-testid="stMetric"] { padding: 13px; min-height: 100px; }
    .brand-header { align-items:flex-start; padding:15px; }
    .brand-title { font-size:1.25rem; }
    .brand-version { display:none; }
    .welcome-panel { align-items:flex-start; }
    .app-footer { padding:10px 0 2px; font-size:.68rem; }
}
</style>
"""


def _filter_controls(rows, terms) -> dict[str, object]:
    st.sidebar.subheader("Filters")
    term_labels = [f"{term['academic_year']} {term['term_name']}" for term in terms]
    term_ids = {label: int(term["term_id"]) for label, term in zip(term_labels, terms)}
    latest_term = term_labels[-1] if term_labels else None
    selected_term = st.sidebar.selectbox(
        "Term",
        term_labels,
        index=term_labels.index(latest_term) if latest_term else 0,
        key="dashboard_term",
    )

    departments = sorted(rows["department_name"].dropna().unique().tolist())
    department = st.sidebar.selectbox("Department", ["All departments", *departments], key="dashboard_department")
    available_rows = rows if department == "All departments" else rows.loc[rows["department_name"] == department]
    programs = sorted(available_rows["program_name"].dropna().unique().tolist())
    program = st.sidebar.selectbox("Program", ["All programs", *programs], key="dashboard_program")
    risk_level = st.sidebar.selectbox(
        "Risk level",
        ["All risk levels", "High", "Medium", "Low", "Not assessed"],
        key="dashboard_risk_level",
    )
    return {
        "term_id": term_ids.get(selected_term),
        "department": department,
        "program": program,
        "risk_level": risk_level,
    }


def main() -> None:
    st.set_page_config(page_title="Academic Analytics", page_icon="A", layout="wide")
    st.markdown(THEME_CSS, unsafe_allow_html=True)
    st.markdown(
        '<header class="brand-header"><div style="display:flex;align-items:center;gap:15px">'
        '<div class="brand-mark" aria-hidden="true">A</div><div>'
        '<div class="brand-title">Academic Analytics Platform</div>'
        '<div class="brand-subtitle">Early Warning &amp; Student Risk Analytics</div>'
        '</div></div><div class="brand-version">UNIVERSITY ANALYTICS &nbsp;|&nbsp; V1.0</div></header>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        '<div class="sidebar-brand"><div class="sidebar-crest" aria-hidden="true">A</div>'
        '<div><strong>Academic Analytics</strong><span>Student Success Office</span></div></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("#### Workspace")
    page = st.sidebar.radio("Navigation", PAGES, label_visibility="collapsed")
    st.sidebar.caption(PAGE_DESCRIPTIONS[page])
    with st.sidebar.expander("Help and interpretation"):
        st.markdown(
            "**Filters** apply to the selected cohort. The Executive Overview trend keeps all available terms.\n\n"
            "**Risk colors:** green = Low, orange = Medium, red = High. Gray = not assessed.\n\n"
            "**Health score** is an equal-weighted index of GPA, attendance, inverse failure rate, and inverse high-risk share. "
            "It is a descriptive composite, not an institutional benchmark.\n\n"
            "Risk reasons are rule-generated signals, not causal findings or decisions about individual students."
        )
    try:
        terms = load_terms()
        if not terms:
            st.warning("No academic terms are available. Load the warehouse before opening the dashboard.")
            st.stop()
        model_version = st.sidebar.selectbox("Risk model", ["rules-v1", "source-v1"], key="dashboard_model")
        rows = load_student_terms(model_version)
        if rows.empty:
            st.warning("The KPI view returned no student-term records. Load the warehouse and risk assessments first.")
            st.stop()

        # Render the remaining cohort filters after loading model-specific KPI rows.
        filters = _filter_controls(rows, terms)
        cohort = filter_cohort(rows, filters)

        if page == "Executive Overview":
            executive_overview.render(rows, cohort, filters)
        elif page == "Academic Risk Analysis":
            academic_risk.render(cohort)
        elif page == "Department Analytics":
            department_analytics.render(cohort)
        elif page == "Program Analytics":
            program_analytics.render(cohort)
        else:
            student_drilldown.render(rows, cohort, int(filters["term_id"]), model_version)
        st.sidebar.caption("Data refreshes every 5 minutes. Clear Streamlit cache after ETL reloads.")
        st.sidebar.markdown(
            '<div class="sidebar-meta">Academic Analytics Platform<br>Demonstration build &middot; Version 1.0</div>',
            unsafe_allow_html=True,
        )
    except DashboardDataError as exc:
        st.error(str(exc))
        st.stop()
    st.markdown(
        '<footer class="app-footer"><span>© DevAI | All Rights Reserved</span><span>Version 1.0</span></footer>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
