from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboards import charts
from dashboards.pages.common import group_summary, health_score, show_cohort_note


def render(cohort: pd.DataFrame) -> None:
    st.title("Department Analytics")
    st.caption("Compare department risk volume, academic outcomes, and participation.")
    if not show_cohort_note(cohort):
        return

    summary = group_summary(cohort, "department_name", "department_name")
    st.subheader("Risk distribution by department")
    st.plotly_chart(charts.department_risk(cohort), width="stretch")
    st.caption("Category counts by department. Compare with the high-risk share ranking below when cohorts differ in size.")

    gpa_column, attendance_column = st.columns(2)
    with gpa_column:
        st.subheader("Average GPA")
        st.plotly_chart(
            charts.department_metric_bars(summary, "average_semester_gpa", "Average semester GPA", "#347a82"),
            width="stretch",
        )
        st.caption("Mean semester GPA on the 0–4 scale for each department.")
    with attendance_column:
        st.subheader("Attendance")
        st.plotly_chart(
            charts.department_metric_bars(summary, "average_attendance_rate_pct", "Attendance (%)", "#d9952b"),
            width="stretch",
        )
        st.caption("Mean attendance percentage for the selected department cohort.")

    st.subheader("Department metric heatmap")
    st.plotly_chart(charts.department_heatmap(summary), width="stretch")
    st.caption("Heatmap colors show relative standard deviations within this filtered cohort; hover for actual values. GPA is favorable upward; risk and failure are favorable downward.")

    summary["health_index"] = summary.apply(
        lambda row: health_score(
            {
                "average_gpa": row["average_semester_gpa"],
                "attendance_rate": row["average_attendance_rate_pct"],
                "failure_rate": row["failure_rate_pct"],
                "high_risk_share": row["high_risk_share_pct"],
            }
        ),
        axis=1,
    )
    high_risk_rank = summary.sort_values(
        ["high_risk_share_pct", "high_risk_students"], ascending=[False, False]
    ).head(10)
    best_performing_rank = summary.sort_values("health_index", ascending=False).head(10)
    risk_table, performance_table = st.columns(2)
    with risk_table:
        st.subheader("Top 10 highest-risk departments")
        st.caption("Ranked by high-risk share among assessed students; headcount is shown for workload context.")
        st.dataframe(
            high_risk_rank[
                ["department_name", "total_students", "high_risk_students", "high_risk_share_pct", "average_semester_gpa"]
            ].rename(
                columns={
                    "department_name": "Department",
                    "total_students": "Students",
                    "high_risk_students": "High-risk students",
                    "high_risk_share_pct": "High-risk share (%)",
                    "average_semester_gpa": "Average GPA",
                }
            ).style.format({"High-risk share (%)": "{:.1f}%", "Average GPA": "{:.2f}"}),
            hide_index=True,
            width="stretch",
        )
    with performance_table:
        st.subheader("Top 10 best-performing departments")
        st.caption("Ranked by the same descriptive health index used on the executive page.")
        st.dataframe(
            best_performing_rank[
                ["department_name", "total_students", "health_index", "average_semester_gpa", "average_attendance_rate_pct"]
            ].rename(
                columns={
                    "department_name": "Department",
                    "total_students": "Students",
                    "health_index": "Health index",
                    "average_semester_gpa": "Average GPA",
                    "average_attendance_rate_pct": "Attendance (%)",
                }
            ).style.format(
                {"Health index": "{:.1f}", "Average GPA": "{:.2f}", "Attendance (%)": "{:.1f}%"}
            ),
            hide_index=True,
            width="stretch",
        )

    display = summary.rename(
        columns={
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
        display[["Department", "Students", "High risk", "High-risk share (%)", "Average GPA", "Attendance (%)", "Failure rate (%)"]],
        hide_index=True,
        width="stretch",
    )
