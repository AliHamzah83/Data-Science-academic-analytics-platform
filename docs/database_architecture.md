# Academic Analytics Database Architecture

## Scope

This document defines the normalized relational database for Students, Departments, Advisors, Courses, Enrollments, Grades, Attendance, Interventions, and Risk Assessments. It is limited to the database design phase.

The project currently contains dimension-style CSVs (`dim_student`, `dim_department`, `dim_program`, `dim_course`, and `dim_term`) and fact-style CSVs for enrollment, attendance, LMS activity, assignments, exams, GPA, and risk. The existing enrollment CSV is denormalized because it repeats attendance, assessment, and final-grade values. The normalized database stores those measures in their own tables and treats enrollment as the parent academic registration record.

The executable SQLite DDL is [create_tables.sql](../sql/ddl/create_tables.sql).

## Design Decisions

- Integer surrogate keys are used for joins; business identifiers remain unique natural keys such as `student_code` and `course_code`.
- `fact_enrollment` is the central course-registration grain: one student, course, term, and section.
- Grades, attendance, assignments, exams, and LMS activity reference `enrollment_id`, preventing mismatched student/course/term combinations.
- SQLite-native types are used: `INTEGER`, `REAL`, `TEXT`, and `INTEGER` flags with `0`/`1` values.
- Date and timestamp values use ISO-8601 text, which sorts correctly in SQLite.
- Foreign keys are enabled and checks enforce valid score, GPA, percentage, status, and date ranges. Attendance counts and the supplied percentage are both retained because the raw files contain inconsistent values; the ETL documents and warns on that discrepancy.
- Risk assessments are versioned and timestamped so multiple assessments can be retained for the same student and term.

## ER Diagram

```text
DIM_DEPARTMENT 1 ─────< DIM_PROGRAM
       │
       ├──────────────< DIM_COURSE
       │
       └──────────────< DIM_ADVISOR

DIM_STUDENT 1 ─────< STUDENT_ADVISOR >───── 1 DIM_ADVISOR
      │
      ├────────────< FACT_ENROLLMENT >───── 1 DIM_PROGRAM
      │                         │
      │                         ├─────────── 1 DIM_COURSE
      │                         ├─────────── 1 DIM_TERM
      │                         ├──── 0..1 FACT_ATTENDANCE
      │                         ├──── 0..1 FACT_LMS_ACTIVITY
      │                         ├───────< FACT_GRADE
      │                         ├───────< FACT_ASSIGNMENT_SCORES
      │                         └───────< FACT_EXAM_SCORES
      │
      ├────────────< FACT_GPA_HISTORY >──── 1 DIM_TERM
      │
      ├────────────< FACT_RISK_ASSESSMENT > 1 DIM_TERM
      │                         │
      │                         └──────────< FACT_INTERVENTION
      │                                      │
      ├──────────────────────────────────────┘
      └────────────── 1 DIM_ADVISOR (through advisor_id)

FACT_INTERVENTION also optionally references its triggering FACT_RISK_ASSESSMENT.
```

## Table Specifications

### `dim_department`

- **Purpose:** University academic department master data.
- **Primary key:** `department_id`.
- **Foreign keys:** None.
- **Relationships:** One department has many programs, courses, and advisors.

### `dim_program`

- **Purpose:** Degree or academic program catalog.
- **Primary key:** `program_id`.
- **Foreign keys:** `department_id` references `dim_department`.
- **Relationships:** A department owns many programs; a program appears on many enrollments.

### `dim_student`

- **Purpose:** One master record per student, including stable identity and academic status attributes.
- **Primary key:** `student_id`.
- **Foreign keys:** None.
- **Relationships:** A student has many enrollments, GPA records, risk assessments, interventions, and advisor assignments.

### `dim_advisor`

- **Purpose:** Advisor/staff master data and organizational assignment.
- **Primary key:** `advisor_id`.
- **Foreign keys:** `department_id` references `dim_department`.
- **Relationships:** An advisor can serve many students and own many interventions; advisor assignments are historized through `student_advisor`.

### `student_advisor`

- **Purpose:** Bridge and history table for the many-to-many student/advisor relationship.
- **Primary key:** `student_advisor_id`.
- **Foreign keys:** `student_id` references `dim_student`; `advisor_id` references `dim_advisor`.
- **Relationships:** A student may have multiple advisors over time, and an advisor may serve many students. `start_date` and `end_date` preserve changes in assignment.

### `dim_course`

- **Purpose:** Course catalog and department ownership.
- **Primary key:** `course_id`.
- **Foreign keys:** `department_id` references `dim_department`.
- **Relationships:** A department offers many courses; a course has many enrollments across terms and sections.

### `dim_term`

- **Purpose:** Academic calendar and reporting period.
- **Primary key:** `term_id`.
- **Foreign keys:** None.
- **Relationships:** A term contains many enrollments, GPA records, risk assessments, and interventions.

### `fact_enrollment`

- **Purpose:** Registration fact at the grain of one student in one course section during one term.
- **Primary key:** `enrollment_id`.
- **Foreign keys:** `student_id`, `program_id`, `course_id`, and `term_id` reference their respective dimensions.
- **Relationships:** It is the parent of course-level grades, attendance, LMS activity, assignment scores, and exam scores. The unique combination of student, course, term, and section prevents duplicate registrations.

### `fact_grade`

- **Purpose:** Grade or assessment result associated with an enrollment. `assessment_type` distinguishes final, midterm, or other grade events.
- **Primary key:** `grade_id`.
- **Foreign keys:** `enrollment_id` references `fact_enrollment`.
- **Relationships:** One enrollment may have multiple grade records, but only one record per assessment type.

### `fact_attendance`

- **Purpose:** Course-level attendance summary for an enrollment.
- **Primary key:** `attendance_id`.
- **Foreign keys:** `enrollment_id` references `fact_enrollment`.
- **Relationships:** At most one attendance summary belongs to an enrollment. `attendance_pct` is retained from the authoritative attendance source while lecture counts remain available for audit and quality checks.

### `fact_lms_activity`

- **Purpose:** Course-level learning-management-system engagement for an enrollment.
- **Primary key:** `lms_activity_id`.
- **Foreign keys:** `enrollment_id` references `fact_enrollment`.
- **Relationships:** At most one current summary belongs to an enrollment. If event-level LMS logs are added later, this table can become a derived summary.

### `fact_assignment_scores`

- **Purpose:** Individual assignment results and submission timeliness.
- **Primary key:** `assignment_id`.
- **Foreign keys:** `enrollment_id` references `fact_enrollment`.
- **Relationships:** One enrollment has many assignments. The assignment name is unique within an enrollment.

### `fact_exam_scores`

- **Purpose:** Individual exam results such as midterm and final.
- **Primary key:** `exam_id`.
- **Foreign keys:** `enrollment_id` references `fact_enrollment`.
- **Relationships:** One enrollment has many exam records, with one record per exam type in the current design.

### `fact_gpa_history`

- **Purpose:** Student-level term GPA, cumulative GPA, and academic standing history.
- **Primary key:** `gpa_id`.
- **Foreign keys:** `student_id` references `dim_student`; `term_id` references `dim_term`.
- **Relationships:** A student has at most one GPA snapshot per term. It is intentionally separate from course enrollment because GPA is a student-term measure.

### `fact_risk_assessment`

- **Purpose:** Time-stamped, model- or rules-generated risk result for a student and term.
- **Primary key:** `risk_id`.
- **Foreign keys:** `student_id` references `dim_student`; `term_id` references `dim_term`.
- **Relationships:** A student can receive multiple assessments per term as model versions or assessment timestamps change. An intervention may reference the assessment that triggered it.

### `fact_intervention`

- **Purpose:** Operational record of support actions taken for a student.
- **Primary key:** `intervention_id`.
- **Foreign keys:** `student_id` and `term_id` reference the student and term; optional `advisor_id` references `dim_advisor`; optional `risk_id` references `fact_risk_assessment`.
- **Relationships:** A student can have many interventions. An advisor can manage many interventions. A risk assessment can lead to many interventions, while an intervention can remain valid if the originating assessment is later removed because `risk_id` is nullable.

## Relationship Reasoning

- **Department to program/course/advisor:** Department is the organizational parent, so these entities reference it rather than storing repeated department names.
- **Student to enrollment:** Enrollment records the student-course participation event and gives all course-level facts one consistent join path.
- **Program to enrollment:** A student can change programs, so program membership belongs on the term-specific enrollment rather than as a single immutable student attribute.
- **Course and term to enrollment:** The same course is offered repeatedly and in multiple sections; term and section belong at enrollment grain.
- **Enrollment to grades/attendance/LMS/assignments/exams:** These measures describe a student's participation in a particular course offering. Referencing enrollment prevents facts from being attached to the wrong term or course.
- **Student to GPA history:** GPA is calculated at student-term grain, not course grain, and must remain independent of individual course rows.
- **Student and term to risk assessment:** Risk is evaluated for a student in a temporal context. Keeping history enables point-in-time analysis and avoids overwriting prior scores.
- **Student to advisor through a bridge:** Advisor responsibility changes over time and may be multiple or role-based; a bridge preserves assignment history without duplicating advisor attributes.
- **Risk assessment to intervention:** This optional link supports outcome analysis by connecting a support action to the risk signal that motivated it.

## Necessary Indexes

The DDL creates indexes for:

- Department foreign-key lookups from programs, courses, and advisors.
- Student/advisor history and advisor caseload queries.
- Enrollment by student-term, course-term, and program-term.
- Grade, assignment, and exam lookup by enrollment.
- GPA and risk history by student-term.
- Risk filtering by label and term.
- Intervention queues by student/status and advisor/status.

Unique constraints also create SQLite indexes for business identifiers, term identity, enrollment identity, and one-to-one or one-per-type fact relationships.

## Missing Entities for Future Analytics and ML

These are intentionally not required to implement the current core schema but should be considered before production use:

- **Course sections and instructors:** A section entity would normalize room, delivery mode, capacity, instructor, and schedule instead of using `section_id` as text.
- **Assessment definitions:** A separate assessment catalog would store assignment/exam weight, due date, rubric, and course-level assessment metadata.
- **Academic calendar events:** Useful for census dates, withdrawal deadlines, holidays, and intervention timing.
- **Student program history:** Needed to accurately model program changes, majors, minors, and effective-dated enrollment status.
- **Student support services and outcomes:** Distinguishes advising, tutoring, financial aid, counseling, and other support channels, with standardized outcome codes.
- **LMS event or weekly activity table:** Event-level or weekly snapshots improve early-warning feature timing and trend calculations.
- **Data provenance and ingestion batches:** Source system, extraction time, batch ID, and record-quality status support reproducibility and auditability.
- **Model registry and prediction run metadata:** Stores training-data cutoff, feature version, model version, threshold, and prediction run timestamp without confusing predictions with observed outcomes.
- **Outcome/label definitions:** A controlled label table and observation window help prevent target leakage by documenting when a risk label became knowable.
- **Demographic and consent reference tables:** Separate controlled vocabularies and privacy/consent metadata support fair, governed analysis.

## Why This Database Design Supports Academic Risk Prediction and Student Analytics

The design produces reliable point-in-time features. Enrollment connects a student, course, section, and term; attendance, grades, assignments, exams, and LMS activity can therefore be aggregated consistently without mixing academic periods. GPA and risk history preserve temporal change, while versioned assessments make it possible to compare predictions with later outcomes.

Normalization reduces duplicate values and contradictory measures, and constraints prevent impossible scores, GPAs, dates, and percentages. The intervention relationship adds the operational outcome needed to evaluate whether support was offered and what happened afterward. Together, these properties support reproducible student analytics and risk-prediction datasets while reducing join errors, leakage risk, and loss of historical context.
