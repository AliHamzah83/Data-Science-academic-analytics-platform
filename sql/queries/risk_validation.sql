-- Phase 3 risk validation queries.
-- Run after: python python/src/calculate_risk.py

-- 1. Distribution of the rules-based assessment.
SELECT
    term_id,
    risk_label,
    COUNT(*) AS student_count,
    ROUND(AVG(risk_score), 2) AS average_score,
    MIN(risk_score) AS minimum_score,
    MAX(risk_score) AS maximum_score
FROM fact_risk_assessment
WHERE model_version = 'rules-v1'
GROUP BY term_id, risk_label
ORDER BY term_id, risk_label;

-- 2. Scores must be bounded and labels must match the documented thresholds.
SELECT risk_id, student_id, term_id, risk_score, risk_label
FROM fact_risk_assessment
WHERE model_version = 'rules-v1'
  AND (
      risk_score < 0 OR risk_score > 100
      OR (risk_score < 30 AND risk_label <> 'Low')
      OR (risk_score >= 30 AND risk_score < 60 AND risk_label <> 'Medium')
      OR (risk_score >= 60 AND risk_label <> 'High')
  );

-- 3. Exactly one rules-based assessment per student and term.
SELECT student_id, term_id, COUNT(*) AS assessment_count
FROM fact_risk_assessment
WHERE model_version = 'rules-v1'
GROUP BY student_id, term_id
HAVING COUNT(*) <> 1;

-- 4. Predictor coverage used by the scoring query.
WITH student_terms AS (
    SELECT DISTINCT student_id, term_id
    FROM fact_enrollment
), attendance AS (
    SELECT e.student_id, e.term_id
    FROM fact_enrollment e
    JOIN fact_attendance a ON a.enrollment_id = e.enrollment_id
    GROUP BY e.student_id, e.term_id
), assignments AS (
    SELECT e.student_id, e.term_id
    FROM fact_enrollment e
    JOIN fact_assignment_scores a ON a.enrollment_id = e.enrollment_id
    GROUP BY e.student_id, e.term_id
), exams AS (
    SELECT e.student_id, e.term_id
    FROM fact_enrollment e
    JOIN fact_exam_scores x ON x.enrollment_id = e.enrollment_id
    GROUP BY e.student_id, e.term_id
), gpa AS (
    SELECT student_id, term_id
    FROM fact_gpa_history
)
SELECT
    COUNT(*) AS student_terms,
    SUM(gpa.student_id IS NOT NULL) AS with_gpa,
    SUM(attendance.student_id IS NOT NULL) AS with_attendance,
    SUM(assignments.student_id IS NOT NULL) AS with_assignments,
    SUM(exams.student_id IS NOT NULL) AS with_exams
FROM student_terms
LEFT JOIN gpa USING (student_id, term_id)
LEFT JOIN attendance USING (student_id, term_id)
LEFT JOIN assignments USING (student_id, term_id)
LEFT JOIN exams USING (student_id, term_id);

-- 5. High-risk records and their explainable reasons.
SELECT student_id, term_id, risk_score, risk_reasons
FROM fact_risk_assessment
WHERE model_version = 'rules-v1'
  AND risk_label = 'High'
ORDER BY risk_score DESC, student_id, term_id;

-- 6. Foreign-key integrity for all loaded risk assessments.
PRAGMA foreign_key_check;
