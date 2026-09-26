# Phase 5: Dashboard Architecture

## Purpose and Scope

The dashboard is a read-only Streamlit presentation layer for the existing SQLite warehouse, KPI SQL views, and risk assessments. It does not change the warehouse schema, ETL rules, KPI definitions, or risk scoring model.

## Data Flow

```text
Raw CSVs
   -> Existing ETL and risk scoring
   -> SQLite academic_analytics.db
   -> KPI SQL views (student-term grain and aggregate views)
   -> KPIService read-only adapter
   -> 5-minute Streamlit data cache
   -> Global filters and page-specific summaries
   -> Plotly charts and student tables
```

`KPIService.student_term_rows()` reads from `vw_kpi_student_term`, selecting one row per student-term and preferring the requested risk model. If the requested model has no assessment for a student-term, academic measures remain in the cohort and risk fields are blank. This preserves the denominator and makes missing risk coverage visible.

The dashboard aggregates filtered rows from that KPI view for cohort and comparison visuals. The SQL views remain the metric source of truth; the student-term view already applies course-grain aggregation before exposing GPA, attendance, course outcomes, and risk fields. Student profile and failed-course details are read from the existing dimensions and fact tables through `KPIService`.

## Navigation and Filters

The left sidebar contains a page selector, followed by global filters for term, department, program, risk level, and risk model. The latest term is selected by default. The Executive Overview cards and all page-level cohort comparisons use the selected term and filters. Its risk trend intentionally displays every available term while retaining the selected department, program, and risk-level filters; the selected term does not truncate the trend.

The five pages are:

1. **Executive Overview:** cohort KPI cards, risk distribution, and a stacked term-by-term risk count chart.
2. **Academic Risk Analysis:** risk-score histogram, risk-level counts, top recorded risk reasons, ranked student scores, and a high-risk student table.
3. **Department Analytics:** risk-level counts by department, GPA and attendance comparisons, a relative metric heatmap, and a comparison table.
4. **Program Analytics:** high-risk share ranking, a GPA/attendance comparison scatter plot with cohort-size bubbles, and a program comparison table.
5. **Student Drill Down:** profile, selected-term GPA/attendance/course outcomes/risk details, recorded reasons, failed courses, and GPA history.

## Visualization Choices

- **KPI cards** provide decision-ready counts and rates at a glance.
- **Risk distribution pie** communicates the composition of the selected cohort; “Not assessed” is included so incomplete coverage is not hidden.
- **Stacked risk trend bars** compare risk counts across terms and preserve the changing cohort size context.
- **Risk score histogram** shows score spread rather than only threshold categories.
- **Risk-factor bars and student ranking** expose common recorded reasons and prioritize individual review. Reasons are descriptive rule outputs, not causal explanations.
- **Department/program bars** show both counts and cohort-normalized risk share. GPA and attendance remain separately legible rather than sharing an arbitrary mixed unit axis.
- **Department heatmap** standardizes each metric within the currently filtered cohort and reports actual values on hover. It is a relative comparison, not a performance grade.
- **Program scatter plot** compares GPA and attendance together, uses point size for cohort size, and colors by high-risk share.
- **Student GPA line** shows each selected student's available term history.

## KPI Sources

| Dashboard measure | Source |
|---|---|
| Total and risk-level student counts | `vw_kpi_student_term` and latest selected-model risk assessment |
| Average semester GPA | `fact_gpa_history` through `vw_kpi_student_term` |
| Attendance rate | `fact_attendance` through the lecture-weighted student-term KPI view |
| Failure rate and failed courses | Course-final records in `fact_grade`, aggregated through the KPI view |
| Risk score, category, and reasons | Latest assessment in `fact_risk_assessment`, exposed by KPI views |
| Department and program assignment | Term enrollment joined through `dim_program` and `dim_department` |
| Failed course details | `fact_enrollment`, `fact_grade`, and `dim_course` |
| Term labels | `dim_term` |

The summary, department, program, and risk-factor aggregate views remain available through `KPIService` for other consumers. The dashboard's interactive filters require re-aggregation at student-term grain, so its filtered calculations use the canonical student-term KPI view.

## Project Structure

```text
dashboards/
  app.py                 Streamlit navigation, filters, and page dispatch
  data.py                Cached, read-only access through KPIService
  charts.py              Reusable Plotly chart builders
  pages/                 One renderer per dashboard page and shared helpers
streamlit_app.py         Root Streamlit entry point
python/src/kpi_service.py Dashboard-facing read-only KPI queries
docs/
  dashboard_architecture.md
  dashboard_user_guide.md
```

## Operations and Error Handling

Dashboard reads are cached for five minutes. After reloading data, clear the Streamlit cache or wait for its TTL. Missing databases and missing KPI views produce an actionable dashboard error; no schema or view is silently created during a dashboard session. Run ETL, calculate risk, and install KPI views using the existing pipeline before starting the app.

Launch from the repository root:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```
