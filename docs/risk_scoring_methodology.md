# Phase 3: Explainable Academic Risk Scoring

## Scope

This phase implements a rules-based academic risk score from the warehouse. It is an explainable baseline for student-term monitoring, not a machine-learning model and not a causal assessment of student ability.

The score is calculated at the grain of one student in one academic term and stored in `fact_risk_assessment` with `model_version = 'rules-v1'`.

## Available Predictors

| Factor | Warehouse source | Student-term feature | Why it matters |
|---|---|---|---|
| Semester GPA | `fact_gpa_history` | `semester_gpa` | Direct term-level academic performance |
| Cumulative GPA | `fact_gpa_history` | Available for analysis, not in baseline score | Longer-term academic trajectory |
| Academic standing | `fact_gpa_history` | Probation escalation only in the current implementation | Existing institutional status |
| Attendance | `fact_attendance` through `fact_enrollment` | Average `attendance_pct` | Participation and absence behavior |
| Failed courses | `fact_enrollment` | Failed-course rate | Direct evidence of course difficulty or non-completion |
| Assignments | `fact_assignment_scores` | Average normalized assignment percentage | Ongoing performance before final outcomes |
| Exams | `fact_exam_scores` | Average normalized exam percentage | Summative performance signal |
| LMS activity | `fact_lms_activity` | Available for future extension | Engagement signal; not included in the first baseline to avoid expanding the requested core formula |
| Demographics | `dim_student` | Available for monitoring only | Not used in the risk score to avoid encoding protected or proxy attributes |

## How Factors Contribute

- **GPA:** Low semester GPA is a broad summary of academic performance. The score rises as GPA falls below 3.0 and reaches maximum component risk at GPA 0.
- **Attendance:** Attendance below 75% is treated as a warning signal. The component increases as attendance falls and reaches maximum risk at 0%.
- **Failed courses:** A student failing a larger share of enrolled courses receives a proportionally higher risk component. A course is counted as failed when `course_status = 'Fail'` or the course-final grade is below 60.
- **Assignments:** Assignments represent repeated progress checks. The component increases when the normalized average falls below 70%.
- **Exams:** Exams provide summative evidence. The component increases when the normalized average falls below 60%.
- **Academic standing:** The current implementation adds 15 points and a reason when standing is `Probation`. `Warning` does not currently change the score. Standing is not a weighted feature because it may be derived from GPA and failed courses and could double-count related evidence.

## Component Formulas

Each component is scaled from 0 to 100, where 0 is no measured risk and 100 is the maximum risk for that component:

```text
GPA risk        = max(0, min(100, (3.0 - semester_gpa) / 3.0 * 100))
Attendance risk = max(0, min(100, (75 - attendance_pct) / 75 * 100))
Failure risk    = failed_courses / enrolled_courses * 100
Assignment risk = max(0, min(100, (70 - assignment_avg_pct) / 70 * 100))
Exam risk       = max(0, min(100, (60 - exam_avg_pct) / 60 * 100))
```

`assignment_avg_pct` and `exam_avg_pct` are normalized as `100 * score / max_score` before averaging. Failure rate is already a percentage after multiplying the failed-course proportion by 100.

The baseline score is a weighted average:

```text
baseline_score =
    (0.30 * GPA risk)
  + (0.20 * Attendance risk)
  + (0.20 * Failure risk)
  + (0.15 * Assignment risk)
  + (0.15 * Exam risk)
```

If a component is unavailable, its weight is removed and the remaining component weights are renormalized. This prevents missing attendance or exam data from automatically appearing as low risk or high risk.

## Business Rules and Categories

After calculating the weighted score, the following transparent escalation rules are applied:

- Add 10 points when semester GPA is below 2.0.
- Add 10 points when attendance is below 60%.
- Add 10 points when at least two courses are failed.
- Add 15 points when academic standing is `Probation` (`Warning` is not escalated by the current code).
- Cap the final score at 100.

Risk categories:

| Final score | Category | Meaning |
|---:|---|---|
| 0 to below 30 | Low | No material combination of current academic warning signals |
| 30 to below 60 | Medium | One or more meaningful warning signals; monitor and review |
| 60 to 100 | High | Multiple or severe warning signals; prioritize academic support |

The boundaries are business rules for an interpretable baseline. They must be reviewed against historical outcomes before being treated as intervention policy.

## Risk Reasons

The assessment stores a semicolon-separated reason list generated from the same rules used in scoring, for example:

```text
Low semester GPA; Attendance below 60%; Two or more failed courses
```

Reasons are explanatory evidence, not a causal explanation. A reason is included only when its corresponding condition is true.

## Population and Provenance

The calculation uses all student-term combinations represented by enrollment. The previous source assessment rows are not used as predictors and are replaced for `rules-v1`. Existing source rows loaded by the ETL use `model_version = 'source-v1'`, preserving lineage and allowing comparison.

Demographic attributes are deliberately excluded from the score. They may be used for governance checks such as comparing coverage and error rates across groups later, but they should not determine a student's support priority.

## Limitations and Next Review

- The score is a transparent prioritization aid, not a diagnosis.
- The data is synthetic and thresholds are illustrative.
- Current raw attendance and enrollment exam fields contain consistency warnings; dedicated attendance and exam facts are used as the authoritative measures.
- LMS activity is available but excluded from this first core score; it can be added as a separately validated component.
- Thresholds should be calibrated against later outcomes, reviewed for fairness, and versioned before operational use.
- The generator and rules engine are demonstration components; review the standing and course-failure semantics before treating scores as policy signals.
