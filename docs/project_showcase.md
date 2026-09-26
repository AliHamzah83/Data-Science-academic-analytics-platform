# Academic Analytics Platform: Portfolio Case Study

## Business Problem

Academic leaders need a timely, consistent way to monitor student outcomes across terms, programs, and departments. Data is distributed across enrollment, grades, attendance, LMS activity, and GPA records. Without shared definitions, cohort comparisons can be inconsistent, and student-level warning signals are difficult to review alongside context.

This project demonstrates an end-to-end analytics workflow using synthetic data. It is a portfolio demonstration, not a deployed institutional service or student decision system.

## Solution

The delivered MVP validates and loads synthetic academic records into SQLite, calculates explainable rules-based student-term risk, exposes reusable KPI views, and presents those measures in a filtered Streamlit dashboard. It keeps metric definitions in SQL and treats risk reasons as review signals rather than causal explanations.

## Data Sources

Synthetic CSV files represent:

- Student, department, program, course, and term dimensions.
- Student-course-term enrollment and course-final grades.
- Attendance counts and percentages.
- LMS activity, assignments, and exams.
- Student-term GPA history and source risk assessments.

No real student records, advisor assignments, or intervention events are included. Advisor/intervention tables exist in the warehouse contract but are empty because there are no authoritative source files for them.

## Data Warehouse Design

The SQLite warehouse uses dimensions for students, departments, programs, courses, terms, and advisors. Enrollment is the course-level parent fact; grades, attendance, LMS activity, assignments, and exams link to `enrollment_id`. GPA history and risk assessment are student-term facts. Risk assessments also carry a model version and timestamp so repeated/versioned assessments can be retained.

The KPI base view aggregates course-grain facts before joining to student-term measures. This prevents one-to-many grade, assignment, or exam records from inflating student metrics. See [`data_model.md`](data_model.md) for grains and relationships.

## ETL

The Python ETL checks source headers, parsing, required values, domain ranges, natural keys, fact grains, and foreign-key coverage. It creates a temporary SQLite build and replaces the destination only after the load commits successfully. Error messages identify source files and row numbers where applicable. A destination override supports isolated validation.

## KPI Layer

SQLite views provide:

- Latest risk assessment by student-term-model.
- Student-term academic and risk measures.
- Institution summary by term/model.
- Risk distribution by department and program.
- Counts of stored risk-reason phrases.

`KPIService` provides read-only Python access and validation checks. High-risk share uses assessed students as its denominator. Failure rate uses course-final outcomes and excludes withdrawals and missing grades.

## Risk Analytics

The `rules-v1` engine calculates a 0–100 weighted score using semester GPA, attendance, failed courses, assignments, and exams, then applies documented escalation rules and stores a category and reason phrases. Demographic fields are excluded from the score. In the current implementation, Probation adds an escalation; Academic Warning does not. See [`risk_scoring_methodology.md`](risk_scoring_methodology.md).

The score is an explainable baseline, not a predictive ML model. It has not been calibrated against real historical outcomes, independently validated, or approved as intervention policy.

## Dashboard

The Streamlit application offers five pages:

1. **Executive Overview:** cohort KPIs, descriptive health index, risk mix and term trend, generated observations, and suggested leadership follow-up.
2. **Academic Risk Analysis:** score distribution, category counts, common reasons, ranked students, and high-risk table.
3. **Department Analytics:** risk counts, GPA, attendance, relative heatmap, high-risk ranking, and best-performing ranking.
4. **Program Analytics:** high-risk share and program comparisons across GPA, attendance, cohort size, and risk share.
5. **Student Drill Down:** profile, attendance, GPA, course failures, risk score/category/reasons, and GPA/risk trends.

Global filters support term, department, program, risk level, and risk model. The app reads existing KPI views and facts; it does not write to the warehouse.

The dashboard's academic health index equally weights normalized semester GPA, attendance, inverse failure rate, and inverse assessed high-risk share. This is a presentation aid only, not a validated institutional benchmark. Automatic leadership recommendations are conditional prompts based on descriptive measures, not tested interventions.

## Key Outcomes

- Delivered a repeatable synthetic-data-to-dashboard pipeline across Python, SQLite, SQL, and Streamlit.
- Defined and reused KPI logic at a student-term grain, with aggregate views for stakeholder comparisons.
- Made the current risk score explainable with stored reason phrases and visible scope limitations.
- Added safe ETL destination replacement and isolated path overrides for validation.
- Created an executive-facing dashboard with cohort filters and student drill-down.

Sample row counts and validation evidence are recorded in [`project_health_report.md`](project_health_report.md). Since records are synthetic, observed dashboard values demonstrate application behavior only and should not be presented as university benchmarks.

## Run the Demonstration

From the repository root in PowerShell:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

The app expects `data/academic_analytics.db` with KPI views installed. Full setup and refresh steps are in [`dashboard_user_guide.md`](dashboard_user_guide.md).

## Screenshots

Capture current UI screens and place them in `docs/screenshots/` before publishing a visual case study. Use current screenshots from the running application, not mockups.

| Screenshot | Suggested view |
|---|---|
| `executive-overview.png` | Health index, KPI tiles, risk distribution, trend, and leadership actions |
| `academic-risk.png` | Score distribution, risk breakdown, reasons, ranking, high-risk table |
| `department-analytics.png` | Department comparisons, heatmap, and two ranking tables |
| `program-analytics.png` | Risk-share ranking and program comparison chart |
| `student-drilldown.png` | Student profile, GPA/risk trends, reasons, failed courses |

Screenshots are not embedded until captured from the final application state; no placeholder image is represented as product output.