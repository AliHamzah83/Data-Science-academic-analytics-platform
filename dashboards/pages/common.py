from __future__ import annotations

import math

import pandas as pd


def filter_cohort(frame: pd.DataFrame, filters: dict[str, object], include_term: bool = True) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    result = frame
    if include_term and filters.get("term_id") is not None:
        result = result.loc[result["term_id"] == filters["term_id"]]
    if filters.get("department") != "All departments":
        result = result.loc[result["department_name"] == filters["department"]]
    if filters.get("program") != "All programs":
        result = result.loc[result["program_name"] == filters["program"]]
    if filters.get("risk_level") != "All risk levels":
        result = result.loc[result["risk_category"] == filters["risk_level"]]
    return result.copy()


def cohort_summary(frame: pd.DataFrame) -> dict[str, float | int]:
    if frame.empty:
        return {
            "total_students": 0,
            "high_risk_students": 0,
            "medium_risk_students": 0,
            "low_risk_students": 0,
            "average_gpa": float("nan"),
            "attendance_rate": float("nan"),
            "failure_rate": float("nan"),
        }
    return {
        "total_students": int(frame["student_id"].nunique()),
        "high_risk_students": int(frame.loc[frame["risk_category"] == "High", "student_id"].nunique()),
        "medium_risk_students": int(frame.loc[frame["risk_category"] == "Medium", "student_id"].nunique()),
        "low_risk_students": int(frame.loc[frame["risk_category"] == "Low", "student_id"].nunique()),
        "average_gpa": float(frame["semester_gpa"].mean()),
        "attendance_rate": float(frame["attendance_rate_pct"].mean()),
        "failure_rate": float(100 * frame["failed_courses"].sum() / frame["completed_courses"].sum())
        if frame["completed_courses"].sum()
        else float("nan"),
        "high_risk_share": float(
            100
            * frame.loc[frame["risk_category"] == "High", "student_id"].nunique()
            / frame.loc[frame["risk_score"].notna(), "student_id"].nunique()
        )
        if frame.loc[frame["risk_score"].notna(), "student_id"].nunique()
        else float("nan"),
    }


def group_summary(frame: pd.DataFrame, group_column: str, group_name: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    records: list[dict[str, object]] = []
    for group_value, group in frame.groupby(group_column, dropna=False):
        assessed = group.loc[group["risk_score"].notna(), "student_id"].nunique()
        high_risk = group.loc[group["risk_category"] == "High", "student_id"].nunique()
        records.append(
            {
                group_name: group_value,
                "total_students": int(group["student_id"].nunique()),
                "high_risk_students": int(high_risk),
                "medium_risk_students": int(group.loc[group["risk_category"] == "Medium", "student_id"].nunique()),
                "low_risk_students": int(group.loc[group["risk_category"] == "Low", "student_id"].nunique()),
                "high_risk_share_pct": 100 * high_risk / assessed if assessed else float("nan"),
                "average_semester_gpa": group["semester_gpa"].mean(),
                "average_attendance_rate_pct": group["attendance_rate_pct"].mean(),
                "failure_rate_pct": 100 * group["failed_courses"].sum() / group["completed_courses"].sum()
                if group["completed_courses"].sum()
                else float("nan"),
            }
        )
    return pd.DataFrame(records)


def health_score(summary: dict[str, float | int]) -> float | None:
    """Equal-weighted composite of existing KPIs; higher indicates healthier."""
    components: list[float] = []
    gpa = summary.get("average_gpa")
    attendance = summary.get("attendance_rate")
    failure = summary.get("failure_rate")
    high_risk_share = summary.get("high_risk_share")
    for value, ceiling in ((gpa, 4.0), (attendance, 100.0)):
        if value is not None and math.isfinite(float(value)):
            components.append(max(0.0, min(100.0, float(value) / ceiling * 100.0)))
    if failure is not None and math.isfinite(float(failure)):
        components.append(max(0.0, min(100.0, 100.0 - float(failure))))
    if high_risk_share is not None and math.isfinite(float(high_risk_share)):
        components.append(max(0.0, min(100.0, 100.0 - float(high_risk_share))))
    return sum(components) / len(components) if components else None


def top_recorded_risk_factor(frame: pd.DataFrame, high_risk_only: bool = True) -> tuple[str, int] | None:
    if frame.empty or "risk_reasons" not in frame:
        return None
    source = frame
    if high_risk_only and "risk_category" in frame:
        source = frame.loc[frame["risk_category"] == "High"]
    reasons = source.loc[source["risk_reasons"].notna(), ["student_id", "risk_reasons"]].copy()
    if reasons.empty:
        return None
    reasons["factor"] = reasons["risk_reasons"].astype(str).str.split(";")
    reasons = reasons.explode("factor")
    reasons["factor"] = reasons["factor"].astype(str).str.strip()
    reasons = reasons.loc[reasons["factor"].ne("")]
    if reasons.empty:
        return None
    counts = reasons.groupby("factor")["student_id"].nunique().sort_values(ascending=False)
    factor = str(counts.index[0])
    return factor, int(counts.iloc[0])


def executive_observations(frame: pd.DataFrame, summary: dict[str, float | int]) -> list[tuple[str, str]]:
    total = int(summary["total_students"])
    high = int(summary["high_risk_students"])
    high_share = 100.0 * high / total if total else 0.0
    observations = [
        (
            "Risk exposure",
            f"{high_share:.1f}% of students ({high:,} of {total:,}) are classified as High Risk. "
            + ("This warrants a prioritized outreach review." if high_share >= 20 else "Continue monitoring the high-risk caseload."),
        )
    ]
    factor = top_recorded_risk_factor(frame)
    if factor:
        observations.append(
            (
                "Most common recorded signal",
                f'"{factor[0]}" is the most frequently recorded reason among high-risk students ({factor[1]:,} students). '
                "This is a rule-generated signal, not evidence of causation.",
            )
        )
    attendance = summary["attendance_rate"]
    if math.isfinite(float(attendance)):
        message = (
            f"Average attendance is {float(attendance):.1f}%, below the 75% risk-monitoring threshold."
            if float(attendance) < 75
            else f"Average attendance is {float(attendance):.1f}%, above the 75% monitoring threshold."
        )
        observations.append(("Attendance", message))
    return observations


def leadership_recommendations(summary: dict[str, float | int], frame: pd.DataFrame) -> list[str]:
    actions: list[str] = []
    total = int(summary["total_students"])
    high_count = int(summary["high_risk_students"])
    high_share = 100 * high_count / total if total else 0.0
    if high_share >= 20:
        actions.append(f"Prioritize advisor outreach for the {high_count:,} high-risk students; review caseload capacity before the next term.")
    elif high_count:
        actions.append(f"Maintain targeted monitoring for the {high_count:,} high-risk students and confirm support follow-up is recorded.")
    attendance = summary["attendance_rate"]
    factor = top_recorded_risk_factor(frame)
    if math.isfinite(float(attendance)) and float(attendance) < 75:
        actions.append("Ask departments to review attendance support and early-alert follow-up, then compare attendance trends next term.")
    elif factor and "attendance" in factor[0].lower():
        actions.append("Review attendance practices in the cohorts where this signal is recorded most often; validate changes against later terms.")
    failure = summary["failure_rate"]
    if math.isfinite(float(failure)) and float(failure) >= 10:
        actions.append("Direct academic support toward courses and programs contributing to failed outcomes; monitor the next course-final cycle.")
    gpa = summary["average_gpa"]
    if math.isfinite(float(gpa)) and float(gpa) < 2.5:
        actions.append("Review academic support coverage for students with lower term GPA and track whether subsequent term GPA improves.")
    if not actions:
        actions.append("Sustain current support practices and review the same indicators after the next reporting period.")
    return actions


def show_cohort_note(frame: pd.DataFrame) -> bool:
    if frame.empty:
        import streamlit as st

        st.info("No student-term records match the selected filters.")
        return False
    return True
