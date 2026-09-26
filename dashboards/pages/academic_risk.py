from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboards import charts
from dashboards.pages.common import show_cohort_note


def render(cohort: pd.DataFrame) -> None:
    st.title("Academic Risk Analysis")
    st.caption("Assessment severity, cohort composition, and the most common recorded warning signals.")
    if not show_cohort_note(cohort):
        return

    left, right = st.columns(2)
    with left:
        st.subheader("Risk score distribution")
        st.plotly_chart(charts.risk_score_histogram(cohort), width="stretch")
        st.caption("Distribution of numeric assessment scores from 0 to 100; hover for score bins and student counts.")
    with right:
        st.subheader("Risk level breakdown")
        st.plotly_chart(charts.risk_level_breakdown(cohort), width="stretch")
        st.caption("Counts by the latest risk category, including students without an assessment.")

    factor_column, ranking_column = st.columns((1, 1.25))
    with factor_column:
        st.subheader("Top risk factors")
        st.plotly_chart(charts.risk_factors(cohort), width="stretch")
        st.caption("Distinct selected-cohort students mentioning each stored reason; reasons are not causal effects.")
    with ranking_column:
        st.subheader("Student risk ranking")
        st.plotly_chart(charts.student_ranking(cohort), width="stretch")
        st.caption("Highest numeric risk scores in the filtered cohort. Use student drill-down for context.")

    high_risk = cohort.loc[cohort["risk_category"] == "High"].sort_values("risk_score", ascending=False)
    st.subheader("High-risk students")
    if high_risk.empty:
        st.info("No high-risk students match the selected filters.")
    else:
        columns = ["student_code", "student_name", "department_name", "program_name", "risk_score", "risk_reasons"]
        display = high_risk[columns].rename(
            columns={
                "student_code": "Student ID",
                "student_name": "Student",
                "department_name": "Department",
                "program_name": "Program",
                "risk_score": "Risk score",
                "risk_reasons": "Risk reasons",
            }
        )
        st.dataframe(display, hide_index=True, width="stretch")
