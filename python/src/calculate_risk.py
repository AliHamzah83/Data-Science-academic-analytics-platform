from __future__ import annotations

import sqlite3
import argparse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "academic_analytics.db"
MODEL_VERSION = "rules-v1"

FEATURE_SQL = """
WITH enrollment_features AS (
    SELECT
        e.student_id,
        e.term_id,
        COUNT(*) AS enrolled_courses,
        SUM(CASE WHEN e.course_status = 'Fail' OR g.score < 60 THEN 1 ELSE 0 END) AS failed_courses
    FROM fact_enrollment AS e
    LEFT JOIN fact_grade AS g
      ON g.enrollment_id = e.enrollment_id
     AND g.assessment_type = 'Course Final'
    GROUP BY e.student_id, e.term_id
), attendance_features AS (
    SELECT e.student_id, e.term_id, AVG(a.attendance_pct) AS attendance_pct
    FROM fact_enrollment AS e
    JOIN fact_attendance AS a ON a.enrollment_id = e.enrollment_id
    GROUP BY e.student_id, e.term_id
), assignment_features AS (
    SELECT e.student_id, e.term_id,
           AVG(100.0 * a.score / NULLIF(a.max_score, 0)) AS assignment_avg_pct
    FROM fact_enrollment AS e
    JOIN fact_assignment_scores AS a ON a.enrollment_id = e.enrollment_id
    GROUP BY e.student_id, e.term_id
), exam_features AS (
    SELECT e.student_id, e.term_id,
           AVG(100.0 * x.score / NULLIF(x.max_score, 0)) AS exam_avg_pct
    FROM fact_enrollment AS e
    JOIN fact_exam_scores AS x ON x.enrollment_id = e.enrollment_id
    GROUP BY e.student_id, e.term_id
)
SELECT
    e.student_id,
    e.term_id,
    e.enrolled_courses,
    e.failed_courses,
    100.0 * e.failed_courses / NULLIF(e.enrolled_courses, 0) AS failed_course_rate,
    g.semester_gpa,
    g.academic_standing,
    a.attendance_pct,
    ass.assignment_avg_pct,
    ex.exam_avg_pct
FROM enrollment_features AS e
LEFT JOIN fact_gpa_history AS g
  ON g.student_id = e.student_id AND g.term_id = e.term_id
LEFT JOIN attendance_features AS a
  ON a.student_id = e.student_id AND a.term_id = e.term_id
LEFT JOIN assignment_features AS ass
  ON ass.student_id = e.student_id AND ass.term_id = e.term_id
LEFT JOIN exam_features AS ex
  ON ex.student_id = e.student_id AND ex.term_id = e.term_id
ORDER BY e.student_id, e.term_id
"""


def component_risk(value: float | None, threshold: float, maximum: float) -> float | None:
    if value is None:
        return None
    return max(0.0, min(100.0, (threshold - value) / maximum * 100.0))


def calculate_score(row: sqlite3.Row) -> tuple[float, str, str]:
    components = [
        ("GPA", component_risk(row["semester_gpa"], 3.0, 3.0), 0.30),
        ("attendance", component_risk(row["attendance_pct"], 75.0, 75.0), 0.20),
        ("failed courses", row["failed_course_rate"], 0.20),
        ("assignments", component_risk(row["assignment_avg_pct"], 70.0, 70.0), 0.15),
        ("exams", component_risk(row["exam_avg_pct"], 60.0, 60.0), 0.15),
    ]
    available = [(name, value, weight) for name, value, weight in components if value is not None]
    denominator = sum(weight for _, _, weight in available)
    baseline = sum(value * weight for _, value, weight in available) / denominator if denominator else 0.0
    score = baseline
    reasons: list[str] = []

    if row["semester_gpa"] is not None and row["semester_gpa"] < 2.0:
        score += 10.0
        reasons.append("Semester GPA below 2.0")
    if row["attendance_pct"] is not None and row["attendance_pct"] < 60.0:
        score += 10.0
        reasons.append("Attendance below 60%")
    if row["failed_courses"] >= 2:
        score += 10.0
        reasons.append("Two or more failed courses")
    if (row["academic_standing"] or "").strip().lower() == "probation":
        score += 15.0
        reasons.append("Academic standing is probation")

    if row["semester_gpa"] is not None and row["semester_gpa"] < 3.0:
        reasons.append("Low semester GPA")
    if row["attendance_pct"] is not None and row["attendance_pct"] < 75.0:
        reasons.append("Attendance below 75%")
    if row["failed_courses"] > 0:
        reasons.append("One or more failed courses")
    if row["assignment_avg_pct"] is not None and row["assignment_avg_pct"] < 70.0:
        reasons.append("Low assignment average")
    if row["exam_avg_pct"] is not None and row["exam_avg_pct"] < 60.0:
        reasons.append("Low exam average")
    if not reasons:
        reasons.append("No measured warning signals")

    score = round(min(100.0, max(0.0, score)), 2)
    label = "High" if score >= 60.0 else "Medium" if score >= 30.0 else "Low"
    return score, label, "; ".join(dict.fromkeys(reasons))


def populate_risk_assessments(db_path: Path = DB_PATH) -> int:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        rows = conn.execute(FEATURE_SQL).fetchall()
        assessed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        conn.execute("DELETE FROM fact_risk_assessment WHERE model_version = ?", (MODEL_VERSION,))
        conn.executemany(
            """
            INSERT INTO fact_risk_assessment
                (student_id, term_id, assessment_timestamp, model_version,
                 risk_score, risk_label, risk_reasons)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (row["student_id"], row["term_id"], assessed_at, MODEL_VERSION, *calculate_score(row))
                for row in rows
            ],
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate versioned rule-based student risk assessments")
    parser.add_argument("--db-path", type=Path, default=DB_PATH, help="SQLite warehouse path")
    args = parser.parse_args()
    count = populate_risk_assessments(args.db_path)
    print(f"Inserted {count} {MODEL_VERSION} risk assessments into {args.db_path}")
