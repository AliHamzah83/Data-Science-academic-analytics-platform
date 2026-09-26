from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboards import charts
from dashboards.pages.common import group_summary, show_cohort_note


def render(cohort: pd.DataFrame) -> None:
    st.title("Program Analytics")
    st.caption("Compare program-level risk exposure with GPA, attendance, and cohort size.")
    if not show_cohort_note(cohort):
        return

    summary = group_summary(cohort, "program_name", "program_name")
    summary = summary.merge(
        cohort[["program_name", "department_name"]].drop_duplicates(),
        on="program_name",
        how="left",
    )
    left, right = st.columns((1, 1.2))
    with left:
        st.subheader("High-risk share by program")
        st.plotly_chart(charts.program_risk_share(summary), width="stretch")
        st.caption("High-risk students divided by students with a risk assessment; hover for headcounts.")
    with right:
        st.subheader("Program comparison")
        st.plotly_chart(charts.program_comparison(summary), width="stretch")
        st.caption("GPA and attendance comparison; bubble size represents program enrollment and color represents high-risk share.")

    display = summary.rename(
        columns={
            "program_name": "Program",
            "department_name": "Department",
            "total_students": "Students",
            "high_risk_students": "High risk",
            "high_risk_share_pct": "High-risk share (%)",
            "average_semester_gpa": "Average GPA",
            "average_attendance_rate_pct": "Attendance (%)",
            "failure_rate_pct": "Failure rate (%)",
        }
    )
    st.dataframe(
        display[["Program", "Department", "Students", "High risk", "High-risk share (%)", "Average GPA", "Attendance (%)", "Failure rate (%)"]],
        hide_index=True,
        width="stretch",
    )
