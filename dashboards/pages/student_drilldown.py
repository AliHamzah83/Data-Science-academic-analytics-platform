from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboards import charts
from dashboards.data import load_failed_courses, load_student_profile
from dashboards.pages.common import show_cohort_note


def render(
    all_rows: pd.DataFrame,
    cohort: pd.DataFrame,
    term_id: int,
    model_version: str,
) -> None:
    st.title("Student Drill Down")
    st.caption("Review an individual student's academic profile and recorded risk signals.")
    if not show_cohort_note(cohort):
        return

    choices = cohort[["student_id", "student_display"]].drop_duplicates().sort_values("student_display")
    selected_display = st.selectbox("Student", choices["student_display"].tolist())
    selected_id = int(choices.loc[choices["student_display"] == selected_display, "student_id"].iloc[0])
    profile = load_student_profile(selected_id, term_id, model_version)
    if profile is None:
        st.error("Student details are unavailable for the selected term.")
        return

    name = " ".join(part for part in (profile.get("first_name"), profile.get("last_name")) if part)
    st.subheader(name or profile.get("student_code") or f"Student {selected_id}")
    st.caption(
        f"{profile.get('student_code', '')} | {profile.get('program_name', 'Program not available')} | "
        f"{profile.get('department_name', 'Department not available')} | "
        f"{profile.get('academic_year', '')} {profile.get('term_name', '')}"
    )

    metrics = st.columns(4)
    metric_values = (
        ("Semester GPA", profile.get("semester_gpa"), ".2f", ""),
        ("Attendance", profile.get("attendance_rate_pct"), ".1f", "%"),
        ("Risk score", profile.get("risk_score"), ".1f", ""),
        ("Risk category", profile.get("risk_label") or "Not assessed", None, ""),
    )
    for column, metric in zip(metrics, metric_values):
        label, value, number_format, suffix = metric
        if number_format and pd.notna(value):
            formatted = format(float(value), number_format) + suffix
        elif value is None or pd.isna(value):
            formatted = "N/A"
        else:
            formatted = str(value)
        column.metric(label, formatted)

    left, right = st.columns(2)
    with left:
        st.subheader("Student profile")
        st.write(
            {
                "Academic status": profile.get("academic_status"),
                "Academic standing": profile.get("academic_standing"),
                "Cumulative GPA": profile.get("cumulative_gpa"),
                "Courses enrolled": profile.get("enrolled_courses"),
                "Failed courses": profile.get("failed_courses"),
            }
        )
    with right:
        st.subheader("Risk reasons")
        reasons = [part.strip() for part in (profile.get("risk_reasons") or "").split(";") if part.strip()]
        if reasons:
            for reason in reasons:
                st.markdown(f"- {reason}")
        else:
            st.info("No risk reasons recorded for this assessment.")

    history = all_rows.loc[all_rows["student_id"] == selected_id]
    trend_gpa, trend_risk = st.columns(2)
    with trend_gpa:
        st.subheader("GPA trend")
        st.plotly_chart(charts.student_gpa_trend(history), width="stretch")
        st.caption("Semester GPA history for this student across available terms; hover for exact values.")
    with trend_risk:
        st.subheader("Risk trend")
        st.plotly_chart(charts.student_risk_trend(history), width="stretch")
        st.caption("Risk scores across terms. Shaded bands show the existing Low (0–29), Medium (30–59), and High (60–100) thresholds.")

    st.subheader("Failed courses")
    failed_courses = load_failed_courses(selected_id, term_id)
    if failed_courses.empty:
        st.info("No failed courses recorded for this term.")
    else:
        display = failed_courses.rename(
            columns={
                "course_code": "Course code",
                "course_name": "Course",
                "course_status": "Status",
                "grade_pct": "Final grade (%)",
            }
        )
        st.dataframe(display[["Course code", "Course", "Status", "Final grade (%)"]], hide_index=True, width="stretch")
