# Academic Analytics Platform

An end-to-end, synthetic academic analytics demonstration. The current MVP covers data generation and validation, a SQLite warehouse, explainable rules-based student risk assessment, reusable KPI views, and an interactive Streamlit dashboard.

> **Data notice:** All supplied student records are synthetic. Risk categories are decision-support signals for demonstration, not diagnoses, causal findings, or intervention decisions.

## Business Problem

University leaders need a consistent view of student outcomes across terms and academic units. This project demonstrates how enrollment, course outcomes, attendance, engagement, and GPA can be organized into a reporting warehouse and presented as actionable cohort-level information.

## Current Capabilities

- Python generator produces synthetic department, program, course, student, term, and academic fact CSVs.
- Validating ETL loads normalized enrollment-linked facts to SQLite with referential and domain checks.
- Rules-based risk engine stores versioned student-term risk scores, labels, and reasons.
- SQLite KPI views define student-term measures and aggregate reporting slices.
- `KPIService` exposes read-only KPI and student-detail queries plus validation checks.
- Streamlit provides executive, risk, department, program, and student drill-down pages with filters and Plotly charts.

Power BI integration, predictive machine learning, and intervention recommendations are future roadmap items, not current features.

## Architecture

```text
Synthetic CSVs -> Validating Python ETL -> SQLite warehouse
                                      |-> Rules risk engine -> Risk fact
                                      |-> KPI SQL views -> KPIService
                                                       -> Streamlit + Plotly
```

See [architecture.md](docs/architecture.md) for system, data-flow, ETL, and risk-analytics diagrams. See [data_model.md](docs/data_model.md) for the implemented SQLite contract.

## Run Locally

Use Python 3.11 or newer. From the repository root in PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe python\src\generate_synthetic_data.py
.venv\Scripts\python.exe python\src\load_to_sqlite.py
.venv\Scripts\python.exe python\src\calculate_risk.py
.venv\Scripts\python.exe python\src\kpi_service.py --install-views --validate --json
.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

The loader atomically replaces its configured output database only after a successful build. For isolated ETL validation, pass `--db-path <temporary-file>`; to generate CSVs outside `data/raw`, set `ACADEMIC_ANALYTICS_RAW_DIR` before running the generator and loader.

The dashboard expects `data/academic_analytics.db` with KPI views already installed. It is read-only and caches query results for five minutes.

## Repository Map

```text
dashboards/               Streamlit app, data adapter, Plotly builders, page renderers
data/raw/                 Synthetic source CSVs (ignored by Git)
data/processed/           Reserved for processed exports
docs/                     Architecture, data, KPI, risk, dashboard, and showcase docs
python/src/               Generator, SQLite ETL, risk engine, and KPI service
sql/ddl/                  SQLite-compatible warehouse schema
sql/queries/              KPI views and validation queries
streamlit_app.py          Root Streamlit entry point
reports/                  Validation and analysis outputs
```

## Key Documentation

- [Dashboard user guide](docs/dashboard_user_guide.md)
- [Project showcase](docs/project_showcase.md)
- [Project roadmap](docs/roadmap.md)
- [KPI definitions](docs/kpi_definitions.md)
- [Risk scoring methodology](docs/risk_scoring_methodology.md)
- [ETL data flow](docs/data_flow_etl.md)
- [Project health report](docs/project_health_report.md)

## Roadmap

1. **Power BI integration:** publish the existing KPI contract and reproduce core stakeholder views.
2. **Predictive risk modeling:** evaluate a leakage-controlled model against the rules baseline.
3. **Intervention recommendation system:** develop governed, advisor-reviewed recommendations using intervention outcome data when available.

Detailed exit criteria are in [roadmap.md](docs/roadmap.md).