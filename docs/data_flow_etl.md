# Phase 2: Data Flow and ETL Analysis

## Scope

This phase covers only ingestion of `data/raw/*.csv` into the normalized SQLite database. The ETL performs validation, cleaning, transformation, and loading. It does not create dashboards, reports, APIs, or machine-learning models.

The implementation is [load_to_sqlite.py](../python/src/load_to_sqlite.py), and the target schema is [create_tables.sql](../sql/ddl/create_tables.sql).

## Raw CSV Inventory

| CSV | Rows observed | Source grain | Main purpose |
|---|---:|---|---|
| `dim_department.csv` | 7 | One row per department | Department master data |
| `dim_program.csv` | 14 | One row per program | Program catalog and department ownership |
| `dim_course.csv` | 35 | One row per course | Course catalog and department ownership |
| `dim_student.csv` | 1,500 | One row per student | Student master and demographic attributes |
| `dim_term.csv` | 4 | One row per academic term | Academic calendar |
| `fact_enrollment.csv` | 24,000 | One row per student-course-term-section | Registration and denormalized course outcome fields |
| `fact_attendance.csv` | 24,000 | One row per student-course-term | Attendance summary |
| `fact_lms_activity.csv` | 24,000 | One row per student-course-term | LMS engagement summary |
| `fact_assignment_scores.csv` | 96,063 | One row per student-course-term-assignment | Assignment-level performance |
| `fact_exam_scores.csv` | 48,000 | One row per student-course-term-exam | Midterm and final exam performance |
| `fact_gpa_history.csv` | 6,000 | One row per student-term | Term and cumulative GPA |
| `fact_risk_assessment.csv` | 6,000 | One row per student-term | Risk score, label, and reasons |

The row counts are treated as observed source characteristics, not hard-coded requirements. The ETL validates keys and grains for every run.

## Structure of Every CSV

### Dimension files

- **`dim_department.csv`:** `department_id`, `department_code`, `department_name`, `faculty_name`, `campus`. The business key is `department_code`.
- **`dim_program.csv`:** `program_id`, `program_code`, `program_name`, `department_id`, `degree_level`. `department_id` is a parent reference.
- **`dim_course.csv`:** `course_id`, `course_code`, `course_name`, `department_id`, `credits`, `is_core`, `course_level`. `department_id` is a parent reference.
- **`dim_student.csv`:** `student_id`, `student_code`, names, `gender`, `age`, `nationality`, `residency_status`, first-generation and scholarship flags, admission/current year, and academic status. `student_id` and `student_code` identify the student.
- **`dim_term.csv`:** `term_id`, `academic_year`, `term_name`, `start_date`, `end_date`. The natural term key is `(academic_year, term_name)`.

### Fact files

- **`fact_enrollment.csv`:** Student, program, course, term, section, attendance rate, assignment average, midterm, final, course grade, letter grade, and course status. The registration key is `(student_id, course_id, term_id, section_id)`.
- **`fact_attendance.csv`:** Student, course, term, attended lectures, total lectures, source attendance percentage, and absences. The key is `(student_id, course_id, term_id)`.
- **`fact_lms_activity.csv`:** Student, course, term, login count, discussion posts, videos watched, time spent, and activity score. The key is `(student_id, course_id, term_id)`.
- **`fact_assignment_scores.csv`:** Student, course, term, assignment name/week, score, maximum score, and submission delay. The key is `(student_id, course_id, term_id, assignment_name)`.
- **`fact_exam_scores.csv`:** Student, course, term, exam type, score, maximum score, and exam date. The key is `(student_id, course_id, term_id, exam_type)`.
- **`fact_gpa_history.csv`:** Student, term, semester GPA, cumulative GPA, and academic standing. The key is `(student_id, term_id)`.
- **`fact_risk_assessment.csv`:** Student, term, risk score, risk label, intervention flag, and reasons. The source key is `(student_id, term_id)`; the target preserves assessment timestamp and model version for future repeated assessments.

## Normalization Issues Identified

1. `fact_enrollment.csv` contains attendance, assignment average, exam scores, and course grade in the enrollment row. These measures have different grains and are separated into attendance, assignment, exam, and grade tables.
2. The attendance, LMS, assignment, exam, GPA, and risk files identify records with natural foreign-key combinations rather than the target surrogate `enrollment_id`. ETL resolves those combinations through an in-memory enrollment lookup.
3. `attendance_rate` is a fraction from 0 to 1 in enrollment, while `attendance_pct` is a percentage from 0 to 100 in attendance. `attendance_pct` is retained as the authoritative source metric and compared with counts-derived attendance. The corrected generator writes the count-derived percentage; older generated CSVs can still produce mismatch warnings until regenerated.
4. Midterm and final scores occur both in enrollment and exam files. The exam file is the authoritative assessment-level source; the enrollment score fields are retained only as compatibility checks. The course-level final grade and letter grade become one `fact_grade` row with `assessment_type = 'Course Final'`.
5. `intervention_flag` is embedded in risk assessment. It is not copied into risk because an intervention is an event with ownership, status, dates, and outcome. The current raw flag is validated and reported as a source signal; no intervention row is fabricated without an intervention event source.
6. The source student table has `age`, whereas the normalized student table originally emphasized date of birth. The target schema stores `age` because it is the supplied source attribute; date of birth remains unavailable and is not invented.
7. No advisor CSV exists, so advisor and student-advisor tables remain empty. The ETL does not create placeholder advisors.
8. Assignment and exam files contain repeated student/course/term keys by design. Their additional assignment/exam type makes the rows distinct and should not be deduplicated.

## Source-to-Target Mapping

### `dim_department.csv` to `dim_department`

| Source column | Target column | Transformation |
|---|---|---|
| `department_id` | `department_id` | Preserve source key as explicit integer key |
| `department_code` | `department_code` | Trim text; require uniqueness |
| `department_name` | `department_name` | Trim text; required |
| `faculty_name` | `faculty_name` | Trim blank values to NULL |
| `campus` | `campus` | Trim blank values to NULL |

### `dim_program.csv` to `dim_program`

All columns map by name. IDs and `department_id` become integers; text is trimmed; `department_id` must exist in `dim_department`.

### `dim_course.csv` to `dim_course`

All columns map by name. IDs, `credits`, and `course_level` become integers; `is_core` converts `True`/`False` to `1`/`0`; text is trimmed; department and course code must be valid and unique.

### `dim_student.csv` to `dim_student`

All columns map by name except `current_year`, which has no target column and is intentionally not loaded. `age` is loaded as an integer; boolean flags become `1`/`0`; text is trimmed; blank values become NULL; `student_code` is unique.

### `dim_term.csv` to `dim_term`

All columns map by name. IDs become integers; dates are validated and stored as ISO text; `(academic_year, term_name)` must be unique; end date cannot precede start date.

### `fact_enrollment.csv` to `fact_enrollment` and `fact_grade`

| Source column | Target column | Transformation |
|---|---|---|
| `student_id` | `fact_enrollment.student_id` | Integer lookup to target student |
| `program_id` | `fact_enrollment.program_id` | Integer lookup to target program |
| `course_id` | `fact_enrollment.course_id` | Integer lookup to target course |
| `term_id` | `fact_enrollment.term_id` | Integer lookup to target term |
| `section_id` | `fact_enrollment.section_id` | Trim text; required |
| `course_status` | `fact_enrollment.course_status` | Trim text; default only if blank |
| `course_grade` | `fact_grade.score` | Create `Course Final` grade row |
| `letter_grade` | `fact_grade.letter_grade` | Trim text on the `Course Final` row |
| `attendance_rate` | none | Validate against attendance source within tolerance; do not duplicate |
| `assignment_avg` | none | Do not load; it is derivable from assignment rows |
| `midterm_score`, `final_score` | none | Validate against exam source where available; exam file is authoritative |

The enrollment lookup key is `(student_id, course_id, term_id, section_id)`. Child fact rows use `(student_id, course_id, term_id)` to resolve `enrollment_id`.

### `fact_attendance.csv` to `fact_attendance`

Student/course/term resolves `enrollment_id`. `lectures_attended`, `total_lectures`, and `absences` become integers, and source `attendance_pct` is stored as the authoritative percentage. The ETL compares it with `100 * lectures_attended / total_lectures`; mismatches are warnings because the supplied counts and percentage are inconsistent.

### `fact_lms_activity.csv` to `fact_lms_activity`

Student/course/term resolves `enrollment_id`. Counts and minutes become non-negative integers; `activity_score` becomes a real number. Every row must resolve to exactly one enrollment.

### `fact_assignment_scores.csv` to `fact_assignment_scores`

Student/course/term resolves `enrollment_id`. Assignment name is trimmed, week/score/max score/delay are numeric, and score must be between 0 and max score. Each source row becomes one target assignment row.

### `fact_exam_scores.csv` to `fact_exam_scores` and `fact_grade`

Student/course/term resolves `enrollment_id`. Exam type is trimmed and normalized to title case (`Midterm`, `Final`); dates are validated ISO text; score and max score are numeric. Each row becomes one target exam row. Exam scores are not duplicated into `fact_grade` because `fact_exam_scores` is the authoritative exam assessment table.

### `fact_gpa_history.csv` to `fact_gpa_history`

Student/term resolves the two foreign keys. GPA values become reals and must be between 0 and 4. Each row becomes one student-term GPA history row.

### `fact_risk_assessment.csv` to `fact_risk_assessment`

Student/term resolves the foreign keys. Risk score becomes a real number from 0 to 100; labels are normalized to title case and legacy `Moderate` is mapped to `Medium`; boolean intervention flag is validated but not loaded into risk. One row becomes one assessment with ETL timestamp and `model_version = 'source-v1'`.

## Transformation Rules, Before Code

1. **File contract:** Every expected CSV must exist, have the exact required header set, and contain no unexpected duplicate header names.
2. **Text cleaning:** Strip leading/trailing whitespace. Convert empty strings, `None`, `null`, and `nan` to NULL. Preserve meaningful case except for controlled values.
3. **Numeric parsing:** Parse integer columns as integers and decimal columns as floats. Reject malformed values instead of silently coercing them.
4. **Boolean parsing:** Accept `true/false`, `1/0`, and common case variants; store SQLite booleans as `1/0`.
5. **Date parsing:** Accept ISO `YYYY-MM-DD` values and store them unchanged after validation.
6. **Reference integrity:** Validate every foreign-key ID before loading and resolve child facts to `enrollment_id` from the loaded enrollment key.
7. **Range validation:** Enforce non-negative counts, `score <= max_score`, GPA between 0 and 4, risk score between 0 and 100, valid attendance counts, and valid date order.
8. **Source consistency:** Compare enrollment attendance and exam fields with their dedicated source facts. Known duplicate-field disagreements are warnings; dedicated attendance and exam files are authoritative for those measures, while enrollment course grade remains authoritative for the course-final grade.
9. **Grain validation:** Reject duplicate dimension keys, enrollment keys, attendance/LMS keys, GPA/risk keys, assignment keys, or exam keys.
10. **Load transaction:** Create the schema, load dimensions first, load enrollment and course final grades, then load child facts. Commit only if all validation and inserts succeed; otherwise roll back.
11. **Idempotency and replacement safety:** Build a complete temporary SQLite database for a full raw-file reload, commit it, then atomically replace the selected output path. A failed validation or insert leaves an existing database untouched.
12. **Missing source domains:** Do not synthesize advisor, intervention, or student-advisor rows because no authoritative CSV supplies them.

## Text Data Flow Diagram

```text
CSV files in data/raw
        |
        v
File contract checks
(headers, required files, duplicate headers)
        |
        v
Raw row cleaning
(trim text, NULL normalization, numeric/boolean/date parsing)
        |
        v
Domain and grain validation
(ranges, duplicate keys, source consistency, foreign-key coverage)
        |
        v
Dimension load
Department -> Program/Course
Student -> Term
        |
        v
Enrollment key creation
(student_id, course_id, term_id, section_id) -> enrollment_id
        |
        +----------------------+
        |                      |
        v                      v
Course final grades      Enrollment child facts
from enrollment CSV      Attendance, LMS, assignments, exams
        |                      |
        +----------+-----------+
                   v
             GPA history
             Risk assessments
                   |
                   v
          SQLite transaction commit
                   |
                   v
       academic_analytics.db
```

## Maintainability Notes

The ETL keeps source parsing, validation, target transformation, and database loading in separate functions. It uses explicit column mappings rather than relying on CSV column order. Validation errors include file, row number, and field context so a bad source record can be corrected without debugging SQL internals. The loader prints a row-count summary after a successful commit. `--db-path` selects a disposable output for validation; `ACADEMIC_ANALYTICS_RAW_DIR` redirects source CSVs for isolated generation and loading.
