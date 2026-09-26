from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "academic_analytics.db"
VIEWS_PATH = ROOT / "sql" / "queries" / "kpi_views.sql"


class KPIService:
    """Read-only query service for the reusable academic KPI views."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Warehouse database not found: {self.db_path}")
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def install_views(self, views_path: Path = VIEWS_PATH) -> None:
        """Install or refresh KPI views in the warehouse database."""
        if not views_path.exists():
            raise FileNotFoundError(f"KPI view SQL not found: {views_path}")
        with self._connect() as conn:
            conn.executescript(views_path.read_text(encoding="utf-8"))

    @staticmethod
    def _rows(conn: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        return [dict(row) for row in conn.execute(query, params).fetchall()]

    def summary(self, term_id: int | None = None, model_version: str = "rules-v1") -> dict[str, Any] | None:
        """Return university KPIs for a term; defaults to latest term."""
        with self._connect() as conn:
            if term_id is None:
                term_row = conn.execute("SELECT MAX(term_id) AS term_id FROM dim_term").fetchone()
                term_id = term_row["term_id"] if term_row else None
            if term_id is None:
                return None
            rows = self._rows(
                conn,
                """SELECT s.*, t.academic_year, t.term_name
                   FROM vw_kpi_term_summary AS s
                   JOIN dim_term AS t ON t.term_id = s.term_id
                   WHERE s.term_id = ? AND s.model_version = ?""",
                (term_id, model_version),
            )
            return rows[0] if rows else None

    def risk_by_department(self, term_id: int | None = None, model_version: str = "rules-v1") -> list[dict[str, Any]]:
        with self._connect() as conn:
            if term_id is None:
                row = conn.execute("SELECT MAX(term_id) AS term_id FROM dim_term").fetchone()
                term_id = row["term_id"] if row else None
            if term_id is None:
                return []
            return self._rows(
                conn,
                """SELECT * FROM vw_kpi_risk_by_department
                   WHERE term_id = ? AND model_version = ?
                   ORDER BY high_risk_share_pct DESC, department_name""",
                (term_id, model_version),
            )

    def risk_by_program(self, term_id: int | None = None, model_version: str = "rules-v1") -> list[dict[str, Any]]:
        with self._connect() as conn:
            if term_id is None:
                row = conn.execute("SELECT MAX(term_id) AS term_id FROM dim_term").fetchone()
                term_id = row["term_id"] if row else None
            if term_id is None:
                return []
            return self._rows(
                conn,
                """SELECT * FROM vw_kpi_risk_by_program
                   WHERE term_id = ? AND model_version = ?
                   ORDER BY high_risk_share_pct DESC, program_name""",
                (term_id, model_version),
            )

    def top_risk_factors(
        self,
        term_id: int | None = None,
        model_version: str = "rules-v1",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._connect() as conn:
            if term_id is None:
                row = conn.execute("SELECT MAX(term_id) AS term_id FROM dim_term").fetchone()
                term_id = row["term_id"] if row else None
            if term_id is None:
                return []
            return self._rows(
                conn,
                """SELECT * FROM vw_kpi_top_risk_factors
                   WHERE term_id = ? AND model_version = ?
                   ORDER BY student_term_mentions DESC, risk_factor
                   LIMIT ?""",
                (term_id, model_version, limit),
            )

    def terms(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            return self._rows(
                conn,
                """SELECT term_id, academic_year, term_name, start_date, end_date
                   FROM dim_term ORDER BY term_id""",
            )

    def student_term_rows(
        self,
        term_id: int | None = None,
        model_version: str = "rules-v1",
    ) -> list[dict[str, Any]]:
        """Return one KPI-view row per student-term, scoped to a risk model."""
        with self._connect() as conn:
            query = """WITH selected_model AS (
                           SELECT k.*,
                                  ROW_NUMBER() OVER (
                                      PARTITION BY k.student_id, k.term_id
                                      ORDER BY CASE WHEN k.model_version = ? THEN 0 ELSE 1 END,
                                               k.model_version
                                  ) AS row_rank
                           FROM vw_kpi_student_term AS k
                       )
                       SELECT k.*, t.academic_year, t.term_name,
                              st.student_code, st.first_name, st.last_name
                       FROM selected_model AS k
                       JOIN dim_term AS t ON t.term_id = k.term_id
                       JOIN dim_student AS st ON st.student_id = k.student_id
                       WHERE k.row_rank = 1"""
            params: tuple[Any, ...] = (model_version,)
            if term_id is not None:
                query += " AND k.term_id = ?"
                params += (term_id,)
            query += " ORDER BY k.term_id, k.student_id"
            rows = self._rows(conn, query, params)
            for row in rows:
                if row["model_version"] != model_version:
                    for field in ("assessment_timestamp", "risk_score", "risk_label", "risk_reasons"):
                        row[field] = None
                    row["model_version"] = None
            return rows

    def student_profile(
        self,
        student_id: int,
        term_id: int,
        model_version: str = "rules-v1",
    ) -> dict[str, Any] | None:
        with self._connect() as conn:
            rows = self._rows(
                conn,
                """WITH selected_model AS (
                       SELECT k.*,
                              ROW_NUMBER() OVER (
                                  PARTITION BY k.student_id, k.term_id
                                  ORDER BY CASE WHEN k.model_version = ? THEN 0 ELSE 1 END,
                                           k.model_version
                              ) AS row_rank
                       FROM vw_kpi_student_term AS k
                   )
                   SELECT st.student_id, st.student_code, st.first_name, st.last_name,
                          st.gender, st.age, st.nationality, st.residency_status,
                          st.first_generation, st.scholarship_flag, st.admission_year,
                          st.academic_status, t.academic_year, t.term_name, k.*
                   FROM selected_model AS k
                   JOIN dim_student AS st ON st.student_id = k.student_id
                   JOIN dim_term AS t ON t.term_id = k.term_id
                   WHERE k.row_rank = 1 AND k.student_id = ? AND k.term_id = ?""",
                (model_version, student_id, term_id),
            )
            if not rows:
                return None
            profile = rows[0]
            if profile["model_version"] != model_version:
                for field in ("assessment_timestamp", "risk_score", "risk_label", "risk_reasons"):
                    profile[field] = None
                profile["model_version"] = None
            return profile

    def failed_courses(self, student_id: int, term_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            return self._rows(
                conn,
                """SELECT c.course_code, c.course_name, e.course_status,
                          g.score, g.max_score,
                          100.0 * g.score / NULLIF(g.max_score, 0) AS grade_pct
                   FROM fact_enrollment AS e
                   JOIN dim_course AS c ON c.course_id = e.course_id
                   JOIN fact_grade AS g ON g.enrollment_id = e.enrollment_id
                   WHERE e.student_id = ? AND e.term_id = ?
                                         AND LOWER(TRIM(e.course_status)) <> 'withdrawn'
                     AND LOWER(TRIM(g.assessment_type)) = 'course final'
                     AND g.score IS NOT NULL AND g.max_score > 0
                     AND 100.0 * g.score / g.max_score < 60.0
                   ORDER BY grade_pct, c.course_code""",
                (student_id, term_id),
            )

    def validate(self) -> dict[str, Any]:
        """Run core grain, bounds, and reconciliation checks."""
        with self._connect() as conn:
            checks = {
                "duplicate_student_term_model_rows": """SELECT COUNT(*) FROM (
                    SELECT student_id, term_id, model_version FROM vw_kpi_student_term
                    GROUP BY student_id, term_id, model_version HAVING COUNT(*) <> 1
                )""",
                "invalid_metric_bounds": """SELECT COUNT(*) FROM vw_kpi_student_term
                    WHERE (attendance_rate_pct IS NOT NULL AND attendance_rate_pct NOT BETWEEN 0 AND 100)
                       OR (failure_rate_pct IS NOT NULL AND failure_rate_pct NOT BETWEEN 0 AND 100)
                       OR (semester_gpa IS NOT NULL AND semester_gpa NOT BETWEEN 0 AND 4)
                       OR (cumulative_gpa IS NOT NULL AND cumulative_gpa NOT BETWEEN 0 AND 4)""",
                "risk_count_mismatches": """SELECT COUNT(*) FROM vw_kpi_term_summary
                    WHERE total_students <> high_risk_students + medium_risk_students
                         + low_risk_students + students_without_risk_assessment""",
                "department_count_mismatches": """SELECT COUNT(*) FROM (
                    SELECT s.term_id, s.model_version
                    FROM vw_kpi_term_summary AS s
                    JOIN vw_kpi_risk_by_department AS d
                      ON d.term_id = s.term_id AND d.model_version = s.model_version
                    GROUP BY s.term_id, s.model_version, s.total_students
                    HAVING s.total_students <> SUM(d.total_students)
                )""",
                "program_count_mismatches": """SELECT COUNT(*) FROM (
                    SELECT s.term_id, s.model_version
                    FROM vw_kpi_term_summary AS s
                    JOIN vw_kpi_risk_by_program AS p
                      ON p.term_id = s.term_id AND p.model_version = s.model_version
                    GROUP BY s.term_id, s.model_version, s.total_students
                    HAVING s.total_students <> SUM(p.total_students)
                )""",
            }
            results = {name: conn.execute(query).fetchone()[0] for name, query in checks.items()}
            return {"passed": all(value == 0 for value in results.values()), "checks": results}


def main() -> None:
    parser = argparse.ArgumentParser(description="Query and validate Academic Analytics KPIs")
    parser.add_argument("--term-id", type=int, help="Term ID; defaults to latest term")
    parser.add_argument("--model-version", default="rules-v1", help="Risk model version")
    parser.add_argument("--install-views", action="store_true", help="Install or refresh SQL views")
    parser.add_argument("--validate", action="store_true", help="Run KPI validation checks")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    service = KPIService()
    if args.install_views:
        service.install_views()
    if args.validate:
        result = service.validate()
        print(json.dumps(result, indent=2) if args.json else result)
        if not result["passed"]:
            raise SystemExit(1)
        return

    term_id = args.term_id
    output = {
        "summary": service.summary(term_id, args.model_version),
        "departments": service.risk_by_department(term_id, args.model_version),
        "programs": service.risk_by_program(term_id, args.model_version),
        "top_risk_factors": service.top_risk_factors(term_id, args.model_version),
    }
    print(json.dumps(output, indent=2, default=str) if args.json else output)


if __name__ == "__main__":
    main()
