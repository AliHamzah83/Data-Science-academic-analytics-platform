from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

RISK_COLORS = {
    "High": "#c4473a",
    "Medium": "#d9952b",
    "Low": "#438a68",
    "Not assessed": "#8c969f",
}
px.defaults.template = "plotly_white"
px.defaults.color_discrete_map = RISK_COLORS


def _polish(figure: go.Figure) -> go.Figure:
    figure.update_layout(
        font={"family": "Aptos, Segoe UI, sans-serif", "color": "#263b3a", "size": 12},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        hoverlabel={"bgcolor": "#173c37", "font_color": "#ffffff", "bordercolor": "#173c37"},
        margin={"l": 14, "r": 14, "t": 22, "b": 14},
    )
    figure.update_xaxes(showgrid=True, gridcolor="#e7eeec", zerolinecolor="#d1ddda")
    figure.update_yaxes(showgrid=True, gridcolor="#e7eeec", zerolinecolor="#d1ddda")
    return figure


def _empty_figure(message: str) -> go.Figure:
    figure = go.Figure()
    figure.add_annotation(text=message, x=0.5, y=0.5, showarrow=False)
    figure.update_xaxes(visible=False)
    figure.update_yaxes(visible=False)
    figure.update_layout(height=320, margin={"l": 12, "r": 12, "t": 24, "b": 12})
    return _polish(figure)


def risk_distribution(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _empty_figure("No students match the selected filters")
    counts = frame["risk_category"].value_counts().rename_axis("Risk level").reset_index(name="Students")
    figure = px.pie(
        counts,
        names="Risk level",
        values="Students",
        hole=0.54,
        color="Risk level",
        color_discrete_map=RISK_COLORS,
    )
    figure.update_traces(textposition="inside", textinfo="percent+label")
    figure.update_layout(showlegend=False, margin={"l": 8, "r": 8, "t": 18, "b": 8})
    return _polish(figure)


def risk_trend(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _empty_figure("No trend data available")
    order = frame[["term_id", "term_label"]].drop_duplicates().sort_values("term_id")["term_label"].tolist()
    counts = (
        frame.groupby(["term_id", "term_label", "risk_category"], dropna=False)["student_id"]
        .nunique()
        .reset_index(name="Students")
    )
    figure = px.bar(
        counts,
        x="term_label",
        y="Students",
        color="risk_category",
        barmode="stack",
        category_orders={"term_label": order, "risk_category": ["High", "Medium", "Low", "Not assessed"]},
        color_discrete_map=RISK_COLORS,
        labels={"term_label": "Academic term", "risk_category": "Risk level"},
    )
    figure.update_layout(legend_title_text="Risk level", margin={"l": 8, "r": 8, "t": 18, "b": 8})
    return _polish(figure)


def risk_score_histogram(frame: pd.DataFrame) -> go.Figure:
    scores = frame.loc[frame["risk_score"].notna()]
    if scores.empty:
        return _empty_figure("No scored assessments in this cohort")
    figure = px.histogram(
        scores,
        x="risk_score",
        color="risk_category",
        nbins=20,
        color_discrete_map=RISK_COLORS,
        labels={"risk_score": "Risk score", "risk_category": "Risk level", "count": "Students"},
    )
    figure.update_layout(barmode="stack", showlegend=True, margin={"l": 8, "r": 8, "t": 18, "b": 8})
    return _polish(figure)


def risk_level_breakdown(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _empty_figure("No students match the selected filters")
    levels = ["High", "Medium", "Low", "Not assessed"]
    counts = frame["risk_category"].value_counts().reindex(levels, fill_value=0).rename_axis("Risk level").reset_index(name="Students")
    figure = px.bar(
        counts,
        x="Risk level",
        y="Students",
        color="Risk level",
        color_discrete_map=RISK_COLORS,
        category_orders={"Risk level": levels},
    )
    figure.update_layout(showlegend=False, margin={"l": 8, "r": 8, "t": 18, "b": 8})
    return _polish(figure)


def student_ranking(frame: pd.DataFrame, limit: int = 15) -> go.Figure:
    ranked = frame.loc[frame["risk_score"].notna()].nlargest(limit, "risk_score").sort_values("risk_score")
    if ranked.empty:
        return _empty_figure("No scored students in this cohort")
    figure = px.bar(
        ranked,
        x="risk_score",
        y="student_display",
        color="risk_category",
        orientation="h",
        color_discrete_map=RISK_COLORS,
        labels={"risk_score": "Risk score", "student_display": "Student", "risk_category": "Risk level"},
        hover_data={"risk_reasons": True, "risk_score": ":.1f"},
    )
    figure.update_layout(yaxis_title="", margin={"l": 8, "r": 8, "t": 18, "b": 8})
    return _polish(figure)


def risk_factors(frame: pd.DataFrame, limit: int = 12) -> go.Figure:
    reasons = frame.loc[frame["risk_reasons"].notna(), ["student_id", "risk_reasons"]].copy()
    if reasons.empty:
        return _empty_figure("No risk reasons are available")
    reasons["factor"] = reasons["risk_reasons"].str.split(";")
    factors = reasons.explode("factor")
    factors["factor"] = factors["factor"].astype(str).str.strip()
    factors = factors.loc[factors["factor"].ne("")]
    counts = factors.groupby("factor")["student_id"].nunique().nlargest(limit).sort_values().reset_index(name="Students")
    if counts.empty:
        return _empty_figure("No risk reasons are available")
    figure = px.bar(counts, x="Students", y="factor", orientation="h", labels={"factor": "Risk reason"})
    figure.update_traces(marker_color="#347a82")
    figure.update_layout(yaxis_title="", margin={"l": 8, "r": 8, "t": 18, "b": 8})
    return _polish(figure)


def department_risk(frame: pd.DataFrame) -> go.Figure:
    if frame.empty:
        return _empty_figure("No department data available")
    counts = (
        frame.groupby(["department_name", "risk_category"])["student_id"]
        .nunique()
        .reset_index(name="Students")
    )
    figure = px.bar(
        counts,
        x="department_name",
        y="Students",
        color="risk_category",
        barmode="group",
        color_discrete_map=RISK_COLORS,
        labels={"department_name": "Department", "risk_category": "Risk level"},
    )
    figure.update_layout(xaxis_title="", legend_title_text="Risk level", margin={"l": 8, "r": 8, "t": 18, "b": 8})
    return _polish(figure)


def department_metric_bars(summary: pd.DataFrame, metric: str, label: str, color: str) -> go.Figure:
    if summary.empty:
        return _empty_figure("No department data available")
    figure = px.bar(summary.sort_values(metric), x=metric, y="department_name", orientation="h")
    figure.update_traces(marker_color=color, hovertemplate=f"%{{y}}<br>{label}: %{{x:.1f}}<extra></extra>")
    figure.update_layout(xaxis_title=label, yaxis_title="", margin={"l": 8, "r": 8, "t": 18, "b": 8})
    return _polish(figure)


def department_heatmap(summary: pd.DataFrame) -> go.Figure:
    metrics = [
        ("high_risk_share_pct", "High-risk share (%)"),
        ("average_semester_gpa", "Average GPA"),
        ("average_attendance_rate_pct", "Attendance (%)"),
        ("failure_rate_pct", "Failure rate (%)"),
    ]
    if summary.empty:
        return _empty_figure("No department data available")
    raw = summary.set_index("department_name")[[column for column, _ in metrics]].astype(float)
    standardized = raw.apply(lambda column: (column - column.mean()) / column.std(ddof=0) if column.std(ddof=0) else column * 0)
    figure = go.Figure(
        go.Heatmap(
            z=standardized.to_numpy(),
            x=[label for _, label in metrics],
            y=standardized.index.tolist(),
            customdata=raw.to_numpy(),
            colorscale="RdBu_r",
            zmid=0,
            colorbar={"title": "Std. dev."},
            hovertemplate="%{y}<br>%{x}<br>Value: %{customdata:.1f}<br>Relative deviation: %{z:.2f} SD<extra></extra>",
        )
    )
    figure.update_layout(height=max(300, 42 * len(summary)), margin={"l": 8, "r": 8, "t": 18, "b": 8})
    return _polish(figure)


def program_risk_share(summary: pd.DataFrame) -> go.Figure:
    if summary.empty:
        return _empty_figure("No program data available")
    figure = px.bar(
        summary.sort_values("high_risk_share_pct"),
        x="high_risk_share_pct",
        y="program_name",
        orientation="h",
        color="department_name",
        hover_data={"total_students": True, "high_risk_students": True},
        labels={"high_risk_share_pct": "High-risk share (%)", "program_name": "Program", "department_name": "Department"},
    )
    figure.update_layout(yaxis_title="", margin={"l": 8, "r": 8, "t": 18, "b": 8})
    return _polish(figure)


def program_comparison(summary: pd.DataFrame) -> go.Figure:
    if summary.empty:
        return _empty_figure("No program data available")
    figure = px.scatter(
        summary,
        x="average_semester_gpa",
        y="average_attendance_rate_pct",
        size="total_students",
        color="high_risk_share_pct",
        hover_name="program_name",
        hover_data={"department_name": True, "total_students": True, "high_risk_share_pct": ":.1f"},
        color_continuous_scale="YlOrRd",
        labels={
            "average_semester_gpa": "Average semester GPA",
            "average_attendance_rate_pct": "Average attendance (%)",
            "high_risk_share_pct": "High-risk share (%)",
        },
    )
    figure.update_layout(margin={"l": 8, "r": 8, "t": 18, "b": 8})
    return figure


def student_gpa_trend(frame: pd.DataFrame) -> go.Figure:
    trend = frame.loc[frame["semester_gpa"].notna()].sort_values("term_id")
    if trend.empty:
        return _empty_figure("No GPA history available")
    figure = px.line(
        trend,
        x="term_label",
        y="semester_gpa",
        markers=True,
        labels={"term_label": "Academic term", "semester_gpa": "Semester GPA"},
    )
    figure.update_yaxes(range=[0, 4])
    figure.update_traces(
        line={"color": "#347a82", "width": 3},
        marker={"size": 8, "color": "#347a82", "line": {"color": "#ffffff", "width": 1}},
        hovertemplate="%{x}<br>Semester GPA: %{y:.2f}<extra></extra>",
    )
    return _polish(figure)


def student_risk_trend(frame: pd.DataFrame) -> go.Figure:
    trend = frame.loc[frame["risk_score"].notna()].sort_values("term_id")
    if trend.empty:
        return _empty_figure("No risk-score history available")
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=trend["term_label"],
            y=trend["risk_score"],
            mode="lines+markers",
            name="Risk score",
            line={"color": RISK_COLORS["High"], "width": 3},
            marker={"size": 9, "color": [RISK_COLORS.get(level, RISK_COLORS["Not assessed"]) for level in trend["risk_category"]]},
            customdata=trend[["risk_category", "risk_reasons"]].fillna("").to_numpy(),
            hovertemplate="%{x}<br>Score: %{y:.1f}<br>Category: %{customdata[0]}<br>Reasons: %{customdata[1]}<extra></extra>",
        )
    )
    figure.add_hrect(y0=0, y1=30, fillcolor=RISK_COLORS["Low"], opacity=0.06, line_width=0)
    figure.add_hrect(y0=30, y1=60, fillcolor=RISK_COLORS["Medium"], opacity=0.08, line_width=0)
    figure.add_hrect(y0=60, y1=100, fillcolor=RISK_COLORS["High"], opacity=0.06, line_width=0)
    figure.update_yaxes(range=[0, 100], title="Risk score")
    figure.update_xaxes(title="Academic term", categoryorder="array", categoryarray=trend["term_label"].tolist())
    return _polish(figure)
