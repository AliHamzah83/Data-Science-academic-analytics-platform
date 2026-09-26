# Project Health Report

**Review date:** 2026-09-26  
**Scope:** Project closure review of Python sources, SQLite warehouse/ETL, rules risk engine, KPI views, dashboard pages, and portfolio documentation.

## Executive Status

The portfolio MVP is structurally complete. Core warehouse, KPI, risk, and dashboard flows passed isolated validation on fresh and existing synthetic CSVs. The checked-in live database was not rebuilt or modified during validation. A corrected fresh-data run passed before the final exam-source alignment change; the latest generator edit was syntax-checked but not rerun end-to-end because full generator execution timed out in one environment path.

## Validation Results

| Area | Result | Evidence / caveat |
|---|---|---|
| Python review | Pass with fixes | Reviewed all 14 Python files; removed unused imports and corrected generator, ETL, and drill-down issues |
| SQLite DDL | Pass | Reconciled DDL with live normalized contract; disposable ETL build created 16 tables |
| ETL on current raw CSVs | Pass with warnings | 1,500 students, 24,000 enrollments, 96,063 assignments, 48,000 exams; zero FK violations; 71,946 source-consistency warnings in older raw files |
| Fresh generator + ETL + risk + KPI | Pass before final exam-source alignment | 24,000 enrollments, 6,000 rules assessments; database integrity `ok`; zero FK violations; all five KPI checks passed |
| Fresh synthetic outcome mix | Pass before final exam-source alignment | 22,839 Pass, 458 Fail, 703 Withdrawn |
| Latest generator exam-source alignment | Not revalidated end-to-end | Final code uses the same exam values in enrollment and exam facts; most recent full generator attempt timed out |
| Grade-unit threshold probe | Pass | Representative weighted fraction 0.752 became 75.25%/Pass; 0.498 became 49.75%/Fail |
| ETL atomic failure safety | Pass | Deliberately invalid FK load raised `IntegrityError`, left existing destination bytes unchanged, and removed its temporary build file |
| Rules risk engine | Pass on disposable database | 6,000 rules-v1 rows inserted; Low 4,475, Medium 1,444, High 81 on that synthetic run |
| KPI layer | Pass on disposable database | Duplicate grain, metric bounds, risk reconciliation, department reconciliation, and program reconciliation all zero |
| Dashboard pages | Pass | Streamlit AppTest: zero exceptions across all five pages; charts/tables rendered on each relevant page |
| Workspace database | Preserved | Read-only schema inspection confirmed current warehouse. No full rebuild was run against it |
| Storage | Environment constraint | C: reported 0 bytes free; validation temp files were redirected to D:, which had ample free space |

## Code Review Changes

- Replaced stale PostgreSQL-style DDL with SQLite DDL matching the current `enrollment_id` facts, `fact_grade`, versioned risk assessment, and reserved advisor/intervention tables.
- Made ETL output path configurable with `--db-path` and changed full refresh to build a temporary database before atomic replacement.
- Added `ACADEMIC_ANALYTICS_RAW_DIR` for isolated synthetic source generation/loading.
- Corrected course-grade scaling so normalized 0–1 weighted grades convert to 0–100 before thresholds and CSV output.
- Made attendance percentage derive from attended/total lecture counts.
- Aligned generated exam source values with the duplicate enrollment score fields used by ETL consistency checks.
- Excluded withdrawn courses from student failed-course detail.
- Removed unused imports and reduced a repeated generator scan to a term-local accumulator.

## Documentation Status

README, architecture diagrams, data model, KPI definitions, dashboard user guide, project showcase, and roadmap now describe the implemented SQLite/Streamlit/rules MVP and distinguish future Power BI/ML/recommendation phases. Risk methodology now states that the current implementation escalates Probation but not Academic Warning.

## Remaining Tasks

1. Regenerate the ignored `data/raw/*.csv` with the corrected generator before a portfolio demo, then rerun ETL/risk/KPI validations. Do not rely on older source CSV warning counts as current generator quality.
2. Re-run the complete fresh-data pipeline after the final exam-score source-alignment edit.
3. Capture real screenshots from the running dashboard into `docs/screenshots/` before publishing the case study.
4. Reclaim free space on C:; system temporary storage currently reports zero free bytes.
5. Consider a later engineering task to support config-driven paths consistently across KPI/dashboard CLI tools and add an automated regression test suite.

## Readiness

- **Estimated project completion:** 90%. MVP work is complete; closure evidence, screenshots, and one final fresh-pipeline rerun remain.
- **Portfolio:** Ready with caveats; add current screenshots and rerun the final generator revision.
- **GitHub:** Nearly ready; check ignored/generated data policy and add reproducible validation evidence/screenshots before publishing.
- **Job interviews:** Ready to discuss the end-to-end design and limitations; distinguish descriptive rules scoring from predictive ML.
- **Power BI integration:** Ready to begin as the next phase; preserve KPI definitions and reconcile report measures to SQL outputs.