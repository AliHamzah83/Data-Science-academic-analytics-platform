from __future__ import annotations

import csv
import os
import sqlite3
import tempfile
import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = Path(os.environ.get("ACADEMIC_ANALYTICS_RAW_DIR", ROOT / "data" / "raw"))
DB_PATH = ROOT / "data" / "academic_analytics.db"
SCHEMA_PATH = ROOT / "sql" / "ddl" / "create_tables.sql"
WARNINGS: list[str] = []

EXPECTED_COLUMNS = {
    "dim_department": ["department_id", "department_code", "department_name", "faculty_name", "campus"],
    "dim_program": ["program_id", "program_code", "program_name", "department_id", "degree_level"],
    "dim_course": ["course_id", "course_code", "course_name", "department_id", "credits", "is_core", "course_level"],
    "dim_student": [
        "student_id", "student_code", "first_name", "last_name", "gender", "age",
        "nationality", "residency_status", "first_generation", "scholarship_flag",
        "admission_year", "current_year", "academic_status",
    ],
    "dim_term": ["term_id", "academic_year", "term_name", "start_date", "end_date"],
    "fact_enrollment": [
        "student_id", "program_id", "course_id", "term_id", "section_id",
        "attendance_rate", "assignment_avg", "midterm_score", "final_score",
        "course_grade", "letter_grade", "course_status",
    ],
    "fact_attendance": ["student_id", "course_id", "term_id", "lectures_attended", "total_lectures", "attendance_pct", "absences"],
    "fact_lms_activity": ["student_id", "course_id", "term_id", "logins", "discussion_posts", "videos_watched", "time_spent_minutes", "activity_score"],
    "fact_assignment_scores": ["student_id", "course_id", "term_id", "assignment_name", "week_number", "score", "max_score", "submission_delay_days"],
    "fact_exam_scores": ["student_id", "course_id", "term_id", "exam_type", "score", "max_score", "exam_date"],
    "fact_gpa_history": ["student_id", "term_id", "semester_gpa", "cumulative_gpa", "academic_standing"],
    "fact_risk_assessment": ["student_id", "term_id", "risk_score", "risk_label", "intervention_flag", "risk_reasons"],
}


class ETLError(ValueError):
    """Raised when a raw CSV violates its documented data contract."""


def source_name(table_name: str) -> str:
    return f"{table_name}.csv"


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return None if cleaned.lower() in {"", "none", "null", "nan"} else cleaned


def parse_int(value: str | None, field: str, source: str, row_number: int, required: bool = False) -> int | None:
    cleaned = clean_text(value)
    if cleaned is None:
        if required:
            raise ETLError(f"{source}:{row_number}: {field} is required")
        return None
    try:
        return int(cleaned)
    except ValueError as exc:
        raise ETLError(f"{source}:{row_number}: {field} must be an integer: {cleaned!r}") from exc


def parse_float(value: str | None, field: str, source: str, row_number: int, required: bool = False) -> float | None:
    cleaned = clean_text(value)
    if cleaned is None:
        if required:
            raise ETLError(f"{source}:{row_number}: {field} is required")
        return None
    try:
        return float(cleaned)
    except ValueError as exc:
        raise ETLError(f"{source}:{row_number}: {field} must be numeric: {cleaned!r}") from exc


def parse_bool(value: str | None, field: str, source: str, row_number: int, required: bool = False) -> int | None:
    cleaned = clean_text(value)
    if cleaned is None:
        if required:
            raise ETLError(f"{source}:{row_number}: {field} is required")
        return None
    if cleaned.lower() in {"true", "1", "yes"}:
        return 1
    if cleaned.lower() in {"false", "0", "no"}:
        return 0
    raise ETLError(f"{source}:{row_number}: {field} must be boolean: {cleaned!r}")


def parse_date(value: str | None, field: str, source: str, row_number: int, required: bool = False) -> str | None:
    cleaned = clean_text(value)
    if cleaned is None:
        if required:
            raise ETLError(f"{source}:{row_number}: {field} is required")
        return None
    try:
        datetime.strptime(cleaned, "%Y-%m-%d")
    except ValueError as exc:
        raise ETLError(f"{source}:{row_number}: {field} must be YYYY-MM-DD: {cleaned!r}") from exc
    return cleaned


def read_csv(table_name: str) -> list[dict[str, str | None]]:
    path = RAW_DIR / source_name(table_name)
    if not path.exists():
        raise ETLError(f"Missing required source file: {path}")

    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        columns = reader.fieldnames or []
        expected = EXPECTED_COLUMNS[table_name]
        if len(columns) != len(set(columns)):
            raise ETLError(f"{path.name}: duplicate column names in header")
        if columns != expected:
            raise ETLError(f"{path.name}: expected columns {expected}, found {columns}")
        return [dict(row) for row in reader]


def row_error(table_name: str, row_number: int, message: str) -> ETLError:
    return ETLError(f"{source_name(table_name)}:{row_number}: {message}")


def require_range(value: float | int | None, lower: float, upper: float, field: str, table_name: str, row_number: int) -> None:
    if value is not None and not lower <= value <= upper:
        raise row_error(table_name, row_number, f"{field} must be between {lower} and {upper}: {value}")


def require_non_negative(value: int | float | None, field: str, table_name: str, row_number: int) -> None:
    if value is not None and value < 0:
        raise row_error(table_name, row_number, f"{field} cannot be negative: {value}")


def check_unique(rows: list[dict[str, Any]], fields: tuple[str, ...], table_name: str) -> None:
    seen: dict[tuple[Any, ...], int] = {}
    for row_number, row in enumerate(rows, start=2):
        key = tuple(row[field] for field in fields)
        if key in seen:
            raise row_error(table_name, row_number, f"duplicate key {fields}={key}; first seen on row {seen[key]}")
        seen[key] = row_number


def parse_dimensions() -> dict[str, list[dict[str, Any]]]:
    department_rows: list[dict[str, Any]] = []
    for row_number, row in enumerate(read_csv("dim_department"), start=2):
        source = source_name("dim_department")
        department_rows.append({
            "department_id": parse_int(row["department_id"], "department_id", source, row_number, True),
            "department_code": clean_text(row["department_code"]),
            "department_name": clean_text(row["department_name"]),
            "faculty_name": clean_text(row["faculty_name"]),
            "campus": clean_text(row["campus"]),
        })
    check_unique(department_rows, ("department_id",), "dim_department")
    check_unique(department_rows, ("department_code",), "dim_department")

    program_rows: list[dict[str, Any]] = []
    for row_number, row in enumerate(read_csv("dim_program"), start=2):
        source = source_name("dim_program")
        department_id = parse_int(row["department_id"], "department_id", source, row_number, True)
        if department_id not in {r["department_id"] for r in department_rows}:
            raise row_error("dim_program", row_number, f"unknown department_id {department_id}")
        program_rows.append({
            "program_id": parse_int(row["program_id"], "program_id", source, row_number, True),
            "program_code": clean_text(row["program_code"]),
            "program_name": clean_text(row["program_name"]),
            "department_id": department_id,
            "degree_level": clean_text(row["degree_level"]),
        })
    check_unique(program_rows, ("program_id",), "dim_program")
    check_unique(program_rows, ("program_code",), "dim_program")

    course_rows: list[dict[str, Any]] = []
    for row_number, row in enumerate(read_csv("dim_course"), start=2):
        source = source_name("dim_course")
        department_id = parse_int(row["department_id"], "department_id", source, row_number, True)
        if department_id not in {r["department_id"] for r in department_rows}:
            raise row_error("dim_course", row_number, f"unknown department_id {department_id}")
        credits = parse_int(row["credits"], "credits", source, row_number, True)
        course_level = parse_int(row["course_level"], "course_level", source, row_number)
        if credits is not None and credits <= 0:
            raise row_error("dim_course", row_number, "credits must be positive")
        course_rows.append({
            "course_id": parse_int(row["course_id"], "course_id", source, row_number, True),
            "course_code": clean_text(row["course_code"]),
            "course_name": clean_text(row["course_name"]),
            "department_id": department_id,
            "credits": credits,
            "is_core": parse_bool(row["is_core"], "is_core", source, row_number, True),
            "course_level": course_level,
        })
    check_unique(course_rows, ("course_id",), "dim_course")
    check_unique(course_rows, ("course_code",), "dim_course")

    student_rows: list[dict[str, Any]] = []
    for row_number, row in enumerate(read_csv("dim_student"), start=2):
        source = source_name("dim_student")
        age = parse_int(row["age"], "age", source, row_number)
        if age is not None and not 0 <= age <= 120:
            raise row_error("dim_student", row_number, f"age is outside 0..120: {age}")
        student_rows.append({
            "student_id": parse_int(row["student_id"], "student_id", source, row_number, True),
            "student_code": clean_text(row["student_code"]),
            "first_name": clean_text(row["first_name"]),
            "last_name": clean_text(row["last_name"]),
            "gender": clean_text(row["gender"]),
            "age": age,
            "nationality": clean_text(row["nationality"]),
            "residency_status": clean_text(row["residency_status"]),
            "first_generation": parse_bool(row["first_generation"], "first_generation", source, row_number, True),
            "scholarship_flag": parse_bool(row["scholarship_flag"], "scholarship_flag", source, row_number, True),
            "admission_year": parse_int(row["admission_year"], "admission_year", source, row_number),
            "academic_status": clean_text(row["academic_status"]) or "Good Standing",
        })
    check_unique(student_rows, ("student_id",), "dim_student")
    check_unique(student_rows, ("student_code",), "dim_student")

    term_rows: list[dict[str, Any]] = []
    for row_number, row in enumerate(read_csv("dim_term"), start=2):
        source = source_name("dim_term")
        start_date = parse_date(row["start_date"], "start_date", source, row_number)
        end_date = parse_date(row["end_date"], "end_date", source, row_number)
        if start_date and end_date and end_date < start_date:
            raise row_error("dim_term", row_number, "end_date cannot precede start_date")
        term_rows.append({
            "term_id": parse_int(row["term_id"], "term_id", source, row_number, True),
            "academic_year": clean_text(row["academic_year"]),
            "term_name": clean_text(row["term_name"]),
            "start_date": start_date,
            "end_date": end_date,
        })
    check_unique(term_rows, ("term_id",), "dim_term")
    check_unique(term_rows, ("academic_year", "term_name"), "dim_term")
    return {"department": department_rows, "program": program_rows, "course": course_rows, "student": student_rows, "term": term_rows}


def parse_facts(dimensions: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    student_ids = {r["student_id"] for r in dimensions["student"]}
    program_ids = {r["program_id"] for r in dimensions["program"]}
    course_ids = {r["course_id"] for r in dimensions["course"]}
    term_ids = {r["term_id"] for r in dimensions["term"]}

    enrollments: list[dict[str, Any]] = []
    for row_number, row in enumerate(read_csv("fact_enrollment"), start=2):
        source = source_name("fact_enrollment")
        values = {
            "student_id": parse_int(row["student_id"], "student_id", source, row_number, True),
            "program_id": parse_int(row["program_id"], "program_id", source, row_number, True),
            "course_id": parse_int(row["course_id"], "course_id", source, row_number, True),
            "term_id": parse_int(row["term_id"], "term_id", source, row_number, True),
            "section_id": clean_text(row["section_id"]),
            "course_status": clean_text(row["course_status"]) or "Enrolled",
            "attendance_rate": parse_float(row["attendance_rate"], "attendance_rate", source, row_number, True),
            "assignment_avg": parse_float(row["assignment_avg"], "assignment_avg", source, row_number, True),
            "midterm_score": parse_float(row["midterm_score"], "midterm_score", source, row_number, True),
            "final_score": parse_float(row["final_score"], "final_score", source, row_number, True),
            "course_grade": parse_float(row["course_grade"], "course_grade", source, row_number, True),
            "letter_grade": clean_text(row["letter_grade"]),
        }
        for field, valid_ids in (("student_id", student_ids), ("program_id", program_ids), ("course_id", course_ids), ("term_id", term_ids)):
            if values[field] not in valid_ids:
                raise row_error("fact_enrollment", row_number, f"unknown {field} {values[field]}")
        require_range(values["attendance_rate"], 0, 1, "attendance_rate", "fact_enrollment", row_number)
        for field in ("assignment_avg", "midterm_score", "final_score", "course_grade"):
            require_range(values[field], 0, 100, field, "fact_enrollment", row_number)
        enrollments.append(values)
    check_unique(enrollments, ("student_id", "course_id", "term_id", "section_id"), "fact_enrollment")

    enrollment_keys = {(r["student_id"], r["course_id"], r["term_id"]): r for r in enrollments}
    if len(enrollment_keys) != len(enrollments):
        raise ETLError("fact_enrollment.csv: more than one section exists for a student/course/term; child facts need section-level keys")

    attendance: list[dict[str, Any]] = []
    for row_number, row in enumerate(read_csv("fact_attendance"), start=2):
        source = source_name("fact_attendance")
        values = {"student_id": parse_int(row["student_id"], "student_id", source, row_number, True), "course_id": parse_int(row["course_id"], "course_id", source, row_number, True), "term_id": parse_int(row["term_id"], "term_id", source, row_number, True), "lectures_attended": parse_int(row["lectures_attended"], "lectures_attended", source, row_number, True), "total_lectures": parse_int(row["total_lectures"], "total_lectures", source, row_number, True), "attendance_pct": parse_float(row["attendance_pct"], "attendance_pct", source, row_number, True), "absences": parse_int(row["absences"], "absences", source, row_number, True)}
        key = (values["student_id"], values["course_id"], values["term_id"])
        if key not in enrollment_keys:
            raise row_error("fact_attendance", row_number, f"no matching enrollment for {key}")
        if values["total_lectures"] <= 0 or values["lectures_attended"] < 0 or values["lectures_attended"] > values["total_lectures"] or values["absences"] < 0 or values["absences"] > values["total_lectures"]:
            raise row_error("fact_attendance", row_number, "invalid lecture or absence counts")
        expected_pct = 100 * values["lectures_attended"] / values["total_lectures"]
        if abs(values["attendance_pct"] - expected_pct) > 0.01:
            WARNINGS.append(f"fact_attendance.csv:{row_number}: attendance_pct {values['attendance_pct']} disagrees with counts-derived {expected_pct:.2f}")
        attendance.append(values)
    check_unique(attendance, ("student_id", "course_id", "term_id"), "fact_attendance")

    lms: list[dict[str, Any]] = []
    for row_number, row in enumerate(read_csv("fact_lms_activity"), start=2):
        source = source_name("fact_lms_activity")
        values = {"student_id": parse_int(row["student_id"], "student_id", source, row_number, True), "course_id": parse_int(row["course_id"], "course_id", source, row_number, True), "term_id": parse_int(row["term_id"], "term_id", source, row_number, True), "logins": parse_int(row["logins"], "logins", source, row_number, True), "discussion_posts": parse_int(row["discussion_posts"], "discussion_posts", source, row_number, True), "videos_watched": parse_int(row["videos_watched"], "videos_watched", source, row_number, True), "time_spent_minutes": parse_int(row["time_spent_minutes"], "time_spent_minutes", source, row_number, True), "activity_score": parse_float(row["activity_score"], "activity_score", source, row_number)}
        key = (values["student_id"], values["course_id"], values["term_id"])
        if key not in enrollment_keys:
            raise row_error("fact_lms_activity", row_number, f"no matching enrollment for {key}")
        for field in ("logins", "discussion_posts", "videos_watched", "time_spent_minutes", "activity_score"):
            require_non_negative(values[field], field, "fact_lms_activity", row_number)
        lms.append(values)
    check_unique(lms, ("student_id", "course_id", "term_id"), "fact_lms_activity")

    assignments: list[dict[str, Any]] = []
    for row_number, row in enumerate(read_csv("fact_assignment_scores"), start=2):
        source = source_name("fact_assignment_scores")
        values = {"student_id": parse_int(row["student_id"], "student_id", source, row_number, True), "course_id": parse_int(row["course_id"], "course_id", source, row_number, True), "term_id": parse_int(row["term_id"], "term_id", source, row_number, True), "assignment_name": clean_text(row["assignment_name"]), "week_number": parse_int(row["week_number"], "week_number", source, row_number), "score": parse_float(row["score"], "score", source, row_number, True), "max_score": parse_float(row["max_score"], "max_score", source, row_number, True), "submission_delay_days": parse_int(row["submission_delay_days"], "submission_delay_days", source, row_number, True)}
        key = (values["student_id"], values["course_id"], values["term_id"])
        if key not in enrollment_keys:
            raise row_error("fact_assignment_scores", row_number, f"no matching enrollment for {key}")
        if values["max_score"] <= 0 or values["score"] < 0 or values["score"] > values["max_score"] or values["submission_delay_days"] < 0:
            raise row_error("fact_assignment_scores", row_number, "invalid score, maximum, or submission delay")
        assignments.append(values)
    check_unique(assignments, ("student_id", "course_id", "term_id", "assignment_name"), "fact_assignment_scores")

    exams: list[dict[str, Any]] = []
    for row_number, row in enumerate(read_csv("fact_exam_scores"), start=2):
        source = source_name("fact_exam_scores")
        exam_type = clean_text(row["exam_type"])
        exam_type = exam_type.title() if exam_type else None
        values = {"student_id": parse_int(row["student_id"], "student_id", source, row_number, True), "course_id": parse_int(row["course_id"], "course_id", source, row_number, True), "term_id": parse_int(row["term_id"], "term_id", source, row_number, True), "exam_type": exam_type, "score": parse_float(row["score"], "score", source, row_number, True), "max_score": parse_float(row["max_score"], "max_score", source, row_number, True), "exam_date": parse_date(row["exam_date"], "exam_date", source, row_number)}
        key = (values["student_id"], values["course_id"], values["term_id"])
        if key not in enrollment_keys:
            raise row_error("fact_exam_scores", row_number, f"no matching enrollment for {key}")
        if values["exam_type"] not in {"Midterm", "Final"} or values["max_score"] <= 0 or values["score"] < 0 or values["score"] > values["max_score"]:
            raise row_error("fact_exam_scores", row_number, "invalid exam type or score")
        exams.append(values)
    check_unique(exams, ("student_id", "course_id", "term_id", "exam_type"), "fact_exam_scores")

    exam_by_key = {(r["student_id"], r["course_id"], r["term_id"], r["exam_type"]): r["score"] for r in exams}
    for enrollment in enrollments:
        key = (enrollment["student_id"], enrollment["course_id"], enrollment["term_id"])
        for field, exam_type in (("midterm_score", "Midterm"), ("final_score", "Final")):
            source_score = exam_by_key.get((*key, exam_type))
            if source_score is not None and abs(enrollment[field] - source_score) > 0.01:
                WARNINGS.append(f"fact_enrollment.csv: {field} disagrees with fact_exam_scores for {key}: {enrollment[field]} vs {source_score}")

    gpa: list[dict[str, Any]] = []
    for row_number, row in enumerate(read_csv("fact_gpa_history"), start=2):
        source = source_name("fact_gpa_history")
        values = {"student_id": parse_int(row["student_id"], "student_id", source, row_number, True), "term_id": parse_int(row["term_id"], "term_id", source, row_number, True), "semester_gpa": parse_float(row["semester_gpa"], "semester_gpa", source, row_number, True), "cumulative_gpa": parse_float(row["cumulative_gpa"], "cumulative_gpa", source, row_number, True), "academic_standing": clean_text(row["academic_standing"])}
        if values["student_id"] not in student_ids or values["term_id"] not in term_ids:
            raise row_error("fact_gpa_history", row_number, "unknown student_id or term_id")
        require_range(values["semester_gpa"], 0, 4, "semester_gpa", "fact_gpa_history", row_number)
        require_range(values["cumulative_gpa"], 0, 4, "cumulative_gpa", "fact_gpa_history", row_number)
        gpa.append(values)
    check_unique(gpa, ("student_id", "term_id"), "fact_gpa_history")

    risk: list[dict[str, Any]] = []
    for row_number, row in enumerate(read_csv("fact_risk_assessment"), start=2):
        source = source_name("fact_risk_assessment")
        values = {"student_id": parse_int(row["student_id"], "student_id", source, row_number, True), "term_id": parse_int(row["term_id"], "term_id", source, row_number, True), "risk_score": parse_float(row["risk_score"], "risk_score", source, row_number, True), "risk_label": clean_text(row["risk_label"]), "intervention_flag": parse_bool(row["intervention_flag"], "intervention_flag", source, row_number, True), "risk_reasons": clean_text(row["risk_reasons"])}
        if values["student_id"] not in student_ids or values["term_id"] not in term_ids:
            raise row_error("fact_risk_assessment", row_number, "unknown student_id or term_id")
        require_range(values["risk_score"], 0, 100, "risk_score", "fact_risk_assessment", row_number)
        values["risk_label"] = values["risk_label"].title() if values["risk_label"] else None
        if values["risk_label"] == "Moderate":
            values["risk_label"] = "Medium"
        if values["risk_label"] not in {"Low", "Medium", "High"}:
            raise row_error("fact_risk_assessment", row_number, f"invalid risk_label {values['risk_label']!r}")
        risk.append(values)
    check_unique(risk, ("student_id", "term_id"), "fact_risk_assessment")
    return {"enrollment": enrollments, "attendance": attendance, "lms": lms, "assignments": assignments, "exams": exams, "gpa": gpa, "risk": risk}


def insert_many(conn: sqlite3.Connection, table: str, columns: tuple[str, ...], rows: list[tuple[Any, ...]]) -> None:
    if rows:
        placeholders = ", ".join("?" for _ in columns)
        conn.executemany(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", rows)


def create_database(conn: sqlite3.Connection, schema_path: Path = SCHEMA_PATH) -> None:
    conn.executescript(schema_path.read_text(encoding="utf-8"))


def load_database(
    dimensions: dict[str, list[dict[str, Any]]],
    facts: dict[str, list[dict[str, Any]]],
    db_path: Path = DB_PATH,
) -> dict[str, int]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{db_path.stem}.", suffix=".tmp", dir=db_path.parent)
    os.close(handle)
    temporary_path = Path(temporary_name)
    temporary_path.unlink()
    conn = sqlite3.connect(temporary_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        create_database(conn)
        insert_many(conn, "dim_department", ("department_id", "department_code", "department_name", "faculty_name", "campus"), [tuple(r[c] for c in ("department_id", "department_code", "department_name", "faculty_name", "campus")) for r in dimensions["department"]])
        insert_many(conn, "dim_program", ("program_id", "program_code", "program_name", "department_id", "degree_level"), [tuple(r[c] for c in ("program_id", "program_code", "program_name", "department_id", "degree_level")) for r in dimensions["program"]])
        insert_many(conn, "dim_course", ("course_id", "course_code", "course_name", "department_id", "credits", "is_core", "course_level"), [tuple(r[c] for c in ("course_id", "course_code", "course_name", "department_id", "credits", "is_core", "course_level")) for r in dimensions["course"]])
        insert_many(conn, "dim_student", ("student_id", "student_code", "first_name", "last_name", "gender", "age", "nationality", "residency_status", "first_generation", "scholarship_flag", "admission_year", "academic_status"), [tuple(r[c] for c in ("student_id", "student_code", "first_name", "last_name", "gender", "age", "nationality", "residency_status", "first_generation", "scholarship_flag", "admission_year", "academic_status")) for r in dimensions["student"]])
        insert_many(conn, "dim_term", ("term_id", "academic_year", "term_name", "start_date", "end_date"), [tuple(r[c] for c in ("term_id", "academic_year", "term_name", "start_date", "end_date")) for r in dimensions["term"]])

        enrollment_columns = ("student_id", "program_id", "course_id", "term_id", "section_id", "course_status")
        insert_many(conn, "fact_enrollment", enrollment_columns, [tuple(r[c] for c in enrollment_columns) for r in facts["enrollment"]])
        enrollment_lookup = {(r["student_id"], r["course_id"], r["term_id"]): conn.execute("SELECT enrollment_id FROM fact_enrollment WHERE student_id=? AND course_id=? AND term_id=?", (r["student_id"], r["course_id"], r["term_id"])).fetchone()[0] for r in facts["enrollment"]}

        insert_many(conn, "fact_grade", ("enrollment_id", "assessment_type", "score", "max_score", "letter_grade"), [(enrollment_lookup[(r["student_id"], r["course_id"], r["term_id"])], "Course Final", r["course_grade"], 100, r["letter_grade"]) for r in facts["enrollment"]])
        insert_many(conn, "fact_attendance", ("enrollment_id", "lectures_attended", "total_lectures", "absences", "attendance_pct"), [(enrollment_lookup[(r["student_id"], r["course_id"], r["term_id"])], r["lectures_attended"], r["total_lectures"], r["absences"], r["attendance_pct"]) for r in facts["attendance"]])
        insert_many(conn, "fact_lms_activity", ("enrollment_id", "logins", "discussion_posts", "videos_watched", "time_spent_minutes", "activity_score"), [(enrollment_lookup[(r["student_id"], r["course_id"], r["term_id"])], r["logins"], r["discussion_posts"], r["videos_watched"], r["time_spent_minutes"], r["activity_score"]) for r in facts["lms"]])
        insert_many(conn, "fact_assignment_scores", ("enrollment_id", "assignment_name", "week_number", "score", "max_score", "submission_delay_days"), [(enrollment_lookup[(r["student_id"], r["course_id"], r["term_id"])], r["assignment_name"], r["week_number"], r["score"], r["max_score"], r["submission_delay_days"]) for r in facts["assignments"]])
        insert_many(conn, "fact_exam_scores", ("enrollment_id", "exam_type", "score", "max_score", "exam_date"), [(enrollment_lookup[(r["student_id"], r["course_id"], r["term_id"])], r["exam_type"], r["score"], r["max_score"], r["exam_date"]) for r in facts["exams"]])
        insert_many(conn, "fact_gpa_history", ("student_id", "term_id", "semester_gpa", "cumulative_gpa", "academic_standing"), [tuple(r[c] for c in ("student_id", "term_id", "semester_gpa", "cumulative_gpa", "academic_standing")) for r in facts["gpa"]])
        insert_many(conn, "fact_risk_assessment", ("student_id", "term_id", "model_version", "risk_score", "risk_label", "risk_reasons"), [(r["student_id"], r["term_id"], "source-v1", r["risk_score"], r["risk_label"], r["risk_reasons"]) for r in facts["risk"]])
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        temporary_path.unlink(missing_ok=True)
        raise
    conn.close()
    os.replace(temporary_path, db_path)
    return {"departments": len(dimensions["department"]), "programs": len(dimensions["program"]), "courses": len(dimensions["course"]), "students": len(dimensions["student"]), "terms": len(dimensions["term"]), "enrollments": len(facts["enrollment"]), "grades": len(facts["enrollment"]), "attendance": len(facts["attendance"]), "lms_activity": len(facts["lms"]), "assignments": len(facts["assignments"]), "exams": len(facts["exams"]), "gpa_history": len(facts["gpa"]), "risk_assessments": len(facts["risk"])}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate source CSVs and load the SQLite warehouse")
    parser.add_argument("--db-path", type=Path, default=DB_PATH, help="Output SQLite path; replaced only after a successful load")
    args = parser.parse_args()
    WARNINGS.clear()
    dimensions = parse_dimensions()
    facts = parse_facts(dimensions)
    counts = load_database(dimensions, facts, args.db_path)
    print(f"Database created successfully at: {args.db_path}")
    for table, count in counts.items():
        print(f"  {table}: {count}")
    print(f"Warnings: {len(WARNINGS)}")
    for warning in WARNINGS[:10]:
        print(f"  WARNING {warning}")
    if len(WARNINGS) > 10:
        print(f"  ... {len(WARNINGS) - 10} additional warnings")


if __name__ == "__main__":
    try:
        main()
    except (ETLError, sqlite3.Error) as exc:
        raise SystemExit(f"ETL failed: {exc}") from exc
