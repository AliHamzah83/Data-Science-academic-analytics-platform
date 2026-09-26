# KPI Definitions

## Scope and Grain

SQLite views are the source of truth for academic measures. `vw_kpi_student_term` aggregates course-grain grades, attendance, assignments, exams, and LMS activity before joining student-term GPA, dimensions, and latest risk assessments. Aggregate views report by term/model, department, program, and stored risk-reason phrase.

Students enter a cohort when they have at least one enrollment in the term. Risk facts are selected by `model_version`; latest assessment ties resolve by timestamp and then `risk_id`. Legacy `Moderate` labels are normalized to `Medium`.

## Measures

| KPI | Definition | Denominator / notes |
|---|---|---|
| Total students | Distinct enrolled students in the student-term cohort | Includes students without a risk assessment |
| High / medium / low risk students | Distinct students with the latest selected-model label | Unassessed students remain separately counted |
| Average semester GPA | Mean non-null semester GPA | GPA history at student-term grain; scale 0–4 |
| Average cumulative GPA | Mean non-null cumulative GPA | GPA history at student-term grain; scale 0–4 |
| Attendance rate | Lecture-weighted mean source attendance percentage | Weight by total lectures; percentage scale 0–100 |
| Failure rate | Failed valid course-final outcomes / all valid completed course-final outcomes × 100 | A final grade below 60 is failed; withdrawals and missing/invalid grades excluded |
| High-risk share | High-risk assessed students / all assessed students × 100 | Do not confuse with high-risk students / total enrollment |
| Risk by department/program | Selected-model category counts and high-risk share assigned to term enrollment unit | Compare both count and rate because cohort sizes differ |
| Top risk factors | Distinct students mentioning each stored reason phrase | Reason frequency is descriptive, not causal |

## View Catalog

- `vw_kpi_latest_risk_assessment`: latest assessment per student-term-model.
- `vw_kpi_student_term`: student-term measures and dimensions by model row.
- `vw_kpi_term_summary`: institution summary by term/model.
- `vw_kpi_risk_by_department`: department measures by term/model.
- `vw_kpi_risk_by_program`: program measures by term/model.
- `vw_kpi_top_risk_factors`: reason phrase mention counts and affected students.

`KPIService` exposes summary, department, program, risk-factor, term, student-term, student-profile, failed-course, and validation queries. The dashboard recomputes filtered aggregates from student-term rows so its global filters remain consistent with these definitions.

## Validation and Interpretation

`KPIService.validate()` checks student-term/model grain, metric bounds, category reconciliation, and department/program population reconciliation. The SQL validation query provides corresponding database checks.

The warehouse is synthetic. Older generated raw CSVs may reflect earlier generator logic; regenerate sources when demonstrating the corrected Pass/Fail distribution. Attendance percentage is stored as the authoritative source metric and ETL reports count/percentage mismatches. Risk categories are prioritization signals, not decisions about student ability or support eligibility.

## Commands

From the repository root in PowerShell:

```powershell
.venv\Scripts\python.exe python\src\kpi_service.py --install-views --validate --json
.venv\Scripts\python.exe python\src\kpi_service.py --term-id 4 --model-version rules-v1 --json
```

Use the complete setup sequence in [README.md](../README.md) when rebuilding the warehouse. The loader supports `--db-path` for isolated output validation.