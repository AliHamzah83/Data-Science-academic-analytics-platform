from __future__ import annotations

import html
import math

import pandas as pd
import streamlit as st

from dashboards import charts
from dashboards.pages.common import (
    cohort_summary,
    executive_observations,
    filter_cohort,
    health_score,
    leadership_recommendations,
    show_cohort_note,
)


def _formatted(value: float | int, precision: int = 0, suffix: str = "") -> str:
    if not math.isfinite(float(value)):
        return "N/A"
    return f"{float(value):,.{precision}f}{suffix}"


def _kpi_cards(metrics: dict[str, float | int]) -> None:
    cards = (
        ("◉", "Total students", _formatted(metrics["total_students"]), ""),
        ("▲", "High risk", _formatted(metrics["high_risk_students"]), "high"),
        ("◆", "Medium risk", _formatted(metrics["medium_risk_students"]), "medium"),
        ("●", "Low risk", _formatted(metrics["low_risk_students"]), "low"),
        ("⌂", "Average GPA", _formatted(metrics["average_gpa"], 2, " / 4.00"), ""),
        ("◷", "Attendance", _formatted(metrics["attendance_rate"], 1, "%"), ""),
        ("▤", "Failure rate", _formatted(metrics["failure_rate"], 1, "%"), ""),
    )
    markup = '<div class="kpi-grid">'
    for icon, label, value, risk_class in cards:
        markup += (
            f'<div class="kpi-card {risk_class}"><div class="kpi-label">{icon} &nbsp;{html.escape(label)}</div>'
            f'<div class="kpi-value">{html.escape(value)}</div></div>'
        )
    st.markdown(markup + "</div>", unsafe_allow_html=True)


def _health_panel(score: float | None) -> None:
    if score is None:
        label, message, display = "Not available", "There are not enough complete KPI values to calculate this index.", "N/A"
    elif score >= 80:
        label, message, display = "Strong", "The available indicators are broadly favorable; continue routine monitoring.", f"{score:.0f} / 100"
    elif score >= 65:
        label, message, display = "Watch", "Review the underlying indicators and maintain targeted support for cohorts under pressure.", f"{score:.0f} / 100"
    else:
        label, message, display = "Priority review", "Several indicators warrant leadership attention and coordinated follow-up.", f"{score:.0f} / 100"
    st.markdown(
        f'<div class="health-panel"><div><small>Institutional academic health index · {label}</small>'
        f'<strong>{display}</strong></div><p>{message}</p></div>',
        unsafe_allow_html=True,
    )


def render(all_rows: pd.DataFrame, cohort: pd.DataFrame, filters: dict[str, object]) -> None:
    st.markdown(
        '<div class="page-heading"><h1>Executive Overview</h1>'
        '<div style="color:#5d706e">Institutional performance, student risk, and leadership priorities</div></div>',
        unsafe_allow_html=True,
    )
    if not show_cohort_note(cohort):
        return

    st.markdown(
        '<div class="welcome-panel"><div><strong>Welcome to the Academic Analytics Platform</strong>'
        '<span>A clear view of student success signals across the selected term. Use this overview to orient leadership review, '
        'then move into department, program, or student detail for context.</span></div><div class="welcome-mark" aria-hidden="true">✦</div></div>',
        unsafe_allow_html=True,
    )

    metrics = cohort_summary(cohort)
    _health_panel(health_score(metrics))
    _kpi_cards(metrics)

    st.markdown('<div class="section-heading"><h3>Executive readout</h3></div>', unsafe_allow_html=True)
    observations = executive_observations(cohort, metrics)
    cards = '<div class="story-grid">'
    for title, observation in observations:
        cards += f'<div class="story-card"><strong>{html.escape(title)}</strong><span>{html.escape(observation)}</span></div>'
    st.markdown(cards + "</div>", unsafe_allow_html=True)

    left, right = st.columns((1, 1.5))
    with left:
        st.markdown('<div class="section-heading"><h3>Risk distribution</h3></div>', unsafe_allow_html=True)
        st.plotly_chart(charts.risk_distribution(cohort), width="stretch")
        st.caption("Share of selected-cohort students by latest risk category; unassessed students remain visible.")
    with right:
        st.markdown('<div class="section-heading"><h3>Risk trend by term</h3></div>', unsafe_allow_html=True)
        trend_cohort = filter_cohort(all_rows, filters, include_term=False)
        st.plotly_chart(charts.risk_trend(trend_cohort), width="stretch")
        st.caption("Stacked student counts across terms. Hover to inspect each category; the selected term does not truncate this trend.")

    st.markdown('<div class="section-heading"><h3>What should leadership do next?</h3></div>', unsafe_allow_html=True)
    actions = leadership_recommendations(metrics, cohort)
    st.markdown('<ol class="action-list">' + "".join(f"<li>{html.escape(action)}</li>" for action in actions) + "</ol>", unsafe_allow_html=True)
    st.caption("The health index is an equal-weighted descriptive composite of GPA, attendance, inverse failure rate, and inverse assessed high-risk share. It is not a validated institutional benchmark.")
