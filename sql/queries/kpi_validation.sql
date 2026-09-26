-- KPI layer validation and reconciliation checks.
-- Expected: zero rows for all exception queries unless noted otherwise.

-- 1. Confirm the declared view contract exists.
SELECT name AS missing_view
FROM (
    SELECT 'vw_kpi_latest_risk_assessment' AS name
    UNION ALL SELECT 'vw_kpi_student_term'
    UNION ALL SELECT 'vw_kpi_term_summary'
    UNION ALL SELECT 'vw_kpi_risk_by_department'
    UNION ALL SELECT 'vw_kpi_risk_by_program'
    UNION ALL SELECT 'vw_kpi_top_risk_factors'
) AS expected
WHERE NOT EXISTS (
    SELECT 1 FROM sqlite_master AS actual
    WHERE actual.type = 'view' AND actual.name = expected.name
);

-- 2. Student-term-model grain must be unique because source-v1 and rules-v1
-- are both retained for comparison.
SELECT student_id, term_id, model_version, COUNT(*) AS row_count
FROM vw_kpi_student_term
GROUP BY student_id, term_id, model_version
HAVING COUNT(*) <> 1;

-- 3. Risk category counts must reconcile to students with assessments.
SELECT
    term_id,
    model_version,
    total_students,
    high_risk_students + medium_risk_students + low_risk_students
        + students_without_risk_assessment AS reconciled_students
FROM vw_kpi_term_summary
WHERE total_students <> high_risk_students + medium_risk_students + low_risk_students
                         + students_without_risk_assessment;

-- 4. Values must remain within expected percentage/GPA bounds.
SELECT student_id, term_id, attendance_rate_pct, failure_rate_pct,
       semester_gpa, cumulative_gpa
FROM vw_kpi_student_term
WHERE (attendance_rate_pct IS NOT NULL AND attendance_rate_pct NOT BETWEEN 0 AND 100)
   OR (failure_rate_pct IS NOT NULL AND failure_rate_pct NOT BETWEEN 0 AND 100)
   OR (semester_gpa IS NOT NULL AND semester_gpa NOT BETWEEN 0 AND 4)
   OR (cumulative_gpa IS NOT NULL AND cumulative_gpa NOT BETWEEN 0 AND 4);

-- 5. For each term/model, department student counts should equal the
-- distinct university student count. Programs are student memberships here;
-- every student-term is expected to have one program in the current model.
SELECT t.term_id, t.model_version, t.total_students, SUM(d.total_students) AS department_students
FROM vw_kpi_term_summary AS t
JOIN vw_kpi_risk_by_department AS d
  ON d.term_id = t.term_id AND d.model_version = t.model_version
GROUP BY t.term_id, t.model_version, t.total_students
HAVING t.total_students <> SUM(d.total_students);

-- 6. The same student-program cardinality reconciliation.
SELECT t.term_id, t.model_version, t.total_students, SUM(p.total_students) AS program_students
FROM vw_kpi_term_summary AS t
JOIN vw_kpi_risk_by_program AS p
  ON p.term_id = t.term_id AND p.model_version = t.model_version
GROUP BY t.term_id, t.model_version, t.total_students
HAVING t.total_students <> SUM(p.total_students);

-- 7. Risk labels in the normalized latest-assessment view are canonical.
SELECT DISTINCT risk_label
FROM vw_kpi_latest_risk_assessment
WHERE risk_label NOT IN ('Low', 'Medium', 'High');

-- 8. Useful result queries for manual review.
SELECT * FROM vw_kpi_term_summary ORDER BY term_id, model_version;
SELECT * FROM vw_kpi_risk_by_department ORDER BY term_id, model_version, department_name;
SELECT * FROM vw_kpi_risk_by_program ORDER BY term_id, model_version, program_name;
SELECT * FROM vw_kpi_top_risk_factors ORDER BY term_id, model_version, student_term_mentions DESC;
