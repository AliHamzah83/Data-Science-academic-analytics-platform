-- Reusable KPI views for the current SQLite warehouse schema.
-- Apply with: sqlite3 data/academic_analytics.db < sql/queries/kpi_views.sql

DROP VIEW IF EXISTS vw_kpi_top_risk_factors;
DROP VIEW IF EXISTS vw_kpi_risk_by_program;
DROP VIEW IF EXISTS vw_kpi_risk_by_department;
DROP VIEW IF EXISTS vw_kpi_term_summary;
DROP VIEW IF EXISTS vw_kpi_student_term;
DROP VIEW IF EXISTS vw_kpi_latest_risk_assessment;

-- Resolve repeat assessments to one row per student/term/model.
-- Ties are resolved by risk_id for deterministic output.
CREATE VIEW vw_kpi_latest_risk_assessment AS
WITH ranked AS (
    SELECT
        risk_id,
        student_id,
        term_id,
        assessment_timestamp,
        model_version,
        risk_score,
        CASE WHEN risk_label = 'Moderate' THEN 'Medium' ELSE risk_label END AS risk_label,
        risk_reasons,
        ROW_NUMBER() OVER (
            PARTITION BY student_id, term_id, model_version
            ORDER BY assessment_timestamp DESC, risk_id DESC
        ) AS assessment_rank
    FROM fact_risk_assessment
)
SELECT
    risk_id,
    student_id,
    term_id,
    assessment_timestamp,
    model_version,
    risk_score,
    risk_label,
    risk_reasons
FROM ranked
WHERE assessment_rank = 1;

-- Student-term grain. All course-level tables are first aggregated to
-- enrollment/student-term to avoid fan-out from assignments or exams.
CREATE VIEW vw_kpi_student_term AS
WITH enrollment_agg AS (
    SELECT
        e.student_id,
        e.term_id,
        COUNT(*) AS enrolled_courses,
        SUM(CASE WHEN LOWER(TRIM(e.course_status)) = 'withdrawn' THEN 1 ELSE 0 END) AS withdrawn_courses
    FROM fact_enrollment AS e
    GROUP BY e.student_id, e.term_id
), outcome_agg AS (
    SELECT
        e.student_id,
        e.term_id,
        SUM(CASE WHEN 100.0 * g.score / NULLIF(g.max_score, 0) < 60.0 THEN 1 ELSE 0 END) AS failed_courses,
        COUNT(*) AS completed_courses
    FROM fact_enrollment AS e
    JOIN fact_grade AS g
      ON g.enrollment_id = e.enrollment_id
     AND LOWER(TRIM(g.assessment_type)) = 'course final'
    WHERE LOWER(TRIM(e.course_status)) <> 'withdrawn'
      AND g.score IS NOT NULL
      AND g.max_score > 0
    GROUP BY e.student_id, e.term_id
), student_program AS (
        SELECT student_id, term_id, MIN(program_id) AS program_id
        FROM fact_enrollment
        GROUP BY student_id, term_id
), attendance_agg AS (
    SELECT
        e.student_id,
        e.term_id,
        SUM(a.attendance_pct * a.total_lectures) / NULLIF(SUM(a.total_lectures), 0) AS attendance_rate_pct,
        SUM(a.lectures_attended) AS lectures_attended,
        SUM(a.total_lectures) AS total_lectures
    FROM fact_enrollment AS e
    JOIN fact_attendance AS a ON a.enrollment_id = e.enrollment_id
    GROUP BY e.student_id, e.term_id
), grade_agg AS (
    SELECT
        e.student_id,
        e.term_id,
        AVG(100.0 * g.score / NULLIF(g.max_score, 0)) AS average_course_grade_pct,
        COUNT(*) AS graded_course_count
    FROM fact_enrollment AS e
    JOIN fact_grade AS g
      ON g.enrollment_id = e.enrollment_id
     AND LOWER(TRIM(g.assessment_type)) = 'course final'
    WHERE LOWER(TRIM(e.course_status)) IN ('pass', 'fail')
      AND g.score IS NOT NULL
      AND g.max_score > 0
    GROUP BY e.student_id, e.term_id
), assignment_agg AS (
    SELECT
        e.student_id,
        e.term_id,
        AVG(100.0 * a.score / NULLIF(a.max_score, 0)) AS assignment_average_pct,
        COUNT(a.score) AS assignment_score_count
    FROM fact_enrollment AS e
    JOIN fact_assignment_scores AS a ON a.enrollment_id = e.enrollment_id
    WHERE a.score IS NOT NULL AND a.max_score > 0
    GROUP BY e.student_id, e.term_id
), exam_agg AS (
    SELECT
        e.student_id,
        e.term_id,
        AVG(100.0 * x.score / NULLIF(x.max_score, 0)) AS exam_average_pct,
        COUNT(x.score) AS exam_score_count
    FROM fact_enrollment AS e
    JOIN fact_exam_scores AS x ON x.enrollment_id = e.enrollment_id
    WHERE x.score IS NOT NULL AND x.max_score > 0
    GROUP BY e.student_id, e.term_id
), lms_agg AS (
    SELECT
        e.student_id,
        e.term_id,
        AVG(l.activity_score) AS lms_activity_score,
        SUM(l.logins) AS lms_logins,
        SUM(l.discussion_posts) AS lms_discussion_posts
    FROM fact_enrollment AS e
    JOIN fact_lms_activity AS l ON l.enrollment_id = e.enrollment_id
    GROUP BY e.student_id, e.term_id
), latest_gpa AS (
    SELECT
        student_id,
        term_id,
        semester_gpa,
        cumulative_gpa,
        academic_standing
    FROM fact_gpa_history
)
SELECT
    ea.student_id,
    ea.term_id,
    sp.program_id,
    p.program_code,
    p.program_name,
    p.department_id,
    d.department_code,
    d.department_name,
    ea.enrolled_courses,
    COALESCE(outcomes.completed_courses, 0) AS completed_courses,
    COALESCE(outcomes.failed_courses, 0) AS failed_courses,
    ea.withdrawn_courses,
    100.0 * COALESCE(outcomes.failed_courses, 0) / NULLIF(outcomes.completed_courses, 0) AS failure_rate_pct,
    att.attendance_rate_pct,
    att.lectures_attended,
    att.total_lectures,
    gg.semester_gpa,
    gg.cumulative_gpa,
    gg.academic_standing,
    grade.average_course_grade_pct,
    assign.assignment_average_pct,
    exams.exam_average_pct,
    lms.lms_activity_score,
    lms.lms_logins,
    lms.lms_discussion_posts,
    risk.model_version,
    risk.assessment_timestamp,
    risk.risk_score,
    risk.risk_label,
    risk.risk_reasons
FROM enrollment_agg AS ea
JOIN student_program AS sp
    ON sp.student_id = ea.student_id AND sp.term_id = ea.term_id
JOIN dim_program AS p ON p.program_id = sp.program_id
JOIN dim_department AS d ON d.department_id = p.department_id
LEFT JOIN attendance_agg AS att ON att.student_id = ea.student_id AND att.term_id = ea.term_id
LEFT JOIN outcome_agg AS outcomes ON outcomes.student_id = ea.student_id AND outcomes.term_id = ea.term_id
LEFT JOIN latest_gpa AS gg ON gg.student_id = ea.student_id AND gg.term_id = ea.term_id
LEFT JOIN grade_agg AS grade ON grade.student_id = ea.student_id AND grade.term_id = ea.term_id
LEFT JOIN assignment_agg AS assign ON assign.student_id = ea.student_id AND assign.term_id = ea.term_id
LEFT JOIN exam_agg AS exams ON exams.student_id = ea.student_id AND exams.term_id = ea.term_id
LEFT JOIN lms_agg AS lms ON lms.student_id = ea.student_id AND lms.term_id = ea.term_id
LEFT JOIN vw_kpi_latest_risk_assessment AS risk
  ON risk.student_id = ea.student_id AND risk.term_id = ea.term_id;

-- University-level metrics at one row per student-term, scoped by term/model.
CREATE VIEW vw_kpi_term_summary AS
SELECT
    term_id,
    model_version,
    COUNT(DISTINCT student_id) AS total_students,
    COUNT(DISTINCT CASE WHEN risk_label = 'High' THEN student_id END) AS high_risk_students,
    COUNT(DISTINCT CASE WHEN risk_label = 'Medium' THEN student_id END) AS medium_risk_students,
    COUNT(DISTINCT CASE WHEN risk_label = 'Low' THEN student_id END) AS low_risk_students,
    COUNT(DISTINCT CASE WHEN risk_label IS NULL THEN student_id END) AS students_without_risk_assessment,
    AVG(semester_gpa) AS average_semester_gpa,
    AVG(cumulative_gpa) AS average_cumulative_gpa,
    AVG(attendance_rate_pct) AS average_attendance_rate_pct,
    100.0 * SUM(failed_courses) / NULLIF(SUM(completed_courses), 0) AS failure_rate_pct,
    100.0 * COUNT(DISTINCT CASE WHEN risk_label = 'High' THEN student_id END)
        / NULLIF(COUNT(DISTINCT CASE WHEN risk_label IS NOT NULL THEN student_id END), 0) AS high_risk_share_pct
FROM vw_kpi_student_term
GROUP BY term_id, model_version;

-- Department counts and risk distribution at student-term grain.
CREATE VIEW vw_kpi_risk_by_department AS
SELECT
    term_id,
    model_version,
    department_id,
    department_code,
    department_name,
    COUNT(DISTINCT student_id) AS total_students,
    COUNT(DISTINCT CASE WHEN risk_label = 'High' THEN student_id END) AS high_risk_students,
    COUNT(DISTINCT CASE WHEN risk_label = 'Medium' THEN student_id END) AS medium_risk_students,
    COUNT(DISTINCT CASE WHEN risk_label = 'Low' THEN student_id END) AS low_risk_students,
    COUNT(DISTINCT CASE WHEN risk_label IS NULL THEN student_id END) AS students_without_risk_assessment,
    100.0 * COUNT(DISTINCT CASE WHEN risk_label = 'High' THEN student_id END)
        / NULLIF(COUNT(DISTINCT CASE WHEN risk_label IS NOT NULL THEN student_id END), 0) AS high_risk_share_pct,
    AVG(semester_gpa) AS average_semester_gpa,
    AVG(attendance_rate_pct) AS average_attendance_rate_pct,
    100.0 * SUM(failed_courses) / NULLIF(SUM(completed_courses), 0) AS failure_rate_pct
FROM vw_kpi_student_term
GROUP BY term_id, model_version, department_id, department_code, department_name;

-- Program-level equivalent of the department risk distribution.
CREATE VIEW vw_kpi_risk_by_program AS
SELECT
    term_id,
    model_version,
    department_id,
    department_name,
    program_id,
    program_code,
    program_name,
    COUNT(DISTINCT student_id) AS total_students,
    COUNT(DISTINCT CASE WHEN risk_label = 'High' THEN student_id END) AS high_risk_students,
    COUNT(DISTINCT CASE WHEN risk_label = 'Medium' THEN student_id END) AS medium_risk_students,
    COUNT(DISTINCT CASE WHEN risk_label = 'Low' THEN student_id END) AS low_risk_students,
    COUNT(DISTINCT CASE WHEN risk_label IS NULL THEN student_id END) AS students_without_risk_assessment,
    100.0 * COUNT(DISTINCT CASE WHEN risk_label = 'High' THEN student_id END)
        / NULLIF(COUNT(DISTINCT CASE WHEN risk_label IS NOT NULL THEN student_id END), 0) AS high_risk_share_pct,
    AVG(semester_gpa) AS average_semester_gpa,
    AVG(attendance_rate_pct) AS average_attendance_rate_pct,
    100.0 * SUM(failed_courses) / NULLIF(SUM(completed_courses), 0) AS failure_rate_pct
FROM vw_kpi_student_term
GROUP BY term_id, model_version, department_id, department_name, program_id, program_code, program_name;

-- One row per factor phrase and reporting slice. Counts are student-term
-- mentions, not unique students across multiple terms.
CREATE VIEW vw_kpi_top_risk_factors AS
WITH RECURSIVE reason_tokens(term_id, model_version, student_id, remaining, factor) AS (
    SELECT
        term_id,
        model_version,
        student_id,
        TRIM(risk_reasons) || ';',
        NULL
    FROM vw_kpi_latest_risk_assessment
    WHERE risk_reasons IS NOT NULL AND TRIM(risk_reasons) <> ''

    UNION ALL

    SELECT
        term_id,
        model_version,
        student_id,
        SUBSTR(remaining, INSTR(remaining, ';') + 1),
        TRIM(SUBSTR(remaining, 1, INSTR(remaining, ';') - 1))
    FROM reason_tokens
    WHERE remaining <> ''
)
SELECT
    term_id,
    model_version,
    factor AS risk_factor,
    COUNT(*) AS student_term_mentions,
    COUNT(DISTINCT student_id) AS students_affected
FROM reason_tokens
WHERE factor IS NOT NULL AND factor <> ''
GROUP BY term_id, model_version, factor;
