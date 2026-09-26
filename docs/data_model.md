# Data Model and Warehouse Contract

## Overview

The implemented warehouse is SQLite and is defined by [`../sql/ddl/create_tables.sql`](../sql/ddl/create_tables.sql). It combines academic dimensions, enrollment-grain facts, student-term GPA and risk facts, and currently empty advisor/intervention tables reserved by the established schema. The dashboard and KPI views rely on this normalized contract; the older PostgreSQL-style draft has been retired.

## Dimensions

| Table | Grain | Key attributes |
|---|---|---|
| `dim_student` | One row per student | `student_id`, `student_code`, demographic descriptors, admission year, academic status |
| `dim_department` | One row per department | `department_id`, unique code, name, faculty, campus |
| `dim_program` | One row per program | `program_id`, unique code, name, department, degree level |
| `dim_course` | One row per course | `course_id`, unique code, name, department, credits, core flag, level |
| `dim_term` | One row per academic term | `term_id`, academic year, term name, start/end dates |
| `dim_advisor` | One row per advisor | Advisor code, contact fields, department, active flag; no source advisor CSV currently exists |

## Facts

| Table | Grain | Main measures / relationships |
|---|---|---|
| `fact_enrollment` | One student-course-section-term | Student, program, course, term, section, status; unique student/course/term/section |
| `fact_grade` | One assessment type per enrollment | Score, maximum score, grade date, letter grade; `Course Final` is the KPI course-outcome record |
| `fact_attendance` | One row per enrollment | Attended/total lectures, absences, source attendance percent |
| `fact_lms_activity` | One row per enrollment | Logins, posts, videos, time, activity score |
| `fact_assignment_scores` | One assignment per enrollment | Week, score/max score, submission delay |
| `fact_exam_scores` | One exam type per enrollment | Exam type, score/max score, exam date |
| `fact_gpa_history` | One student-term | Semester GPA, cumulative GPA, academic standing |
| `fact_risk_assessment` | One assessment per student-term-model-time | Timestamp, model version, score, label, reasons; repeated assessments are supported |
| `student_advisor` | One student-advisor assignment interval | Start/end date and assignment type; currently empty |
| `fact_intervention` | One intervention event | Student, term, optional advisor/risk, type, dates, status, outcome, notes; currently empty |

## Relationships

```text
dim_department 1---* dim_program 1---* fact_enrollment *---1 dim_student
       |                                     |                |
       +---* dim_course ---------------------+                +---1 dim_term
                                             |
                 +---------------------------+-------------------------------+
                 |                           |                               |
              fact_grade               fact_attendance                 fact_lms_activity
              fact_assignment_scores   fact_exam_scores

dim_student 1---* fact_gpa_history *---1 dim_term
dim_student 1---* fact_risk_assessment *---1 dim_term
dim_student 1---* fact_intervention *---1 dim_term
```

All course-level child facts reference `fact_enrollment.enrollment_id`. GPA and risk assessments are student-term facts. A program is taken from enrollment and is therefore term-scoped for reporting.

## KPI Reporting Grain

`vw_kpi_student_term` is one row per enrolled student-term and risk model row. It first aggregates course-grain grades, attendance, assignments, exams, and LMS activity, then joins GPA and the latest risk assessment. Aggregate views provide:

- `vw_kpi_latest_risk_assessment`: latest row per student-term-model; ties resolve deterministically by `risk_id`; legacy `Moderate` becomes `Medium`.
- `vw_kpi_student_term`: academic measures and dimensions at student-term/model grain.
- `vw_kpi_term_summary`: institution-level counts and measures by term/model.
- `vw_kpi_risk_by_department`: department comparison by term/model.
- `vw_kpi_risk_by_program`: program comparison by term/model.
- `vw_kpi_top_risk_factors`: parsed reason phrase mentions by term/model.

See [`kpi_definitions.md`](kpi_definitions.md) for formulas, denominators, and interpretation.

## Data Quality and Limitations

- IDs and declared natural keys are unique; facts must resolve to valid dimensions/enrollments.
- GPA is constrained to 0–4; risk score to 0–100; attendance to 0–100; assessment/assignment scores cannot exceed their maximum.
- Attendance percentage is retained as the source metric; ETL reports a warning if it differs from counts-derived attendance beyond tolerance.
- Failed course outcomes use the KPI definition based on a valid course-final grade below 60; withdrawals are excluded from completion/failure denominators.
- Current advisor and intervention fact tables are empty because no authoritative source files provide those events.
- All supplied records are synthetic; the model is suitable for demonstrations, not institutional decisions.