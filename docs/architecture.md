# System Architecture

## Scope and Current State

The implemented platform is a local academic analytics MVP using synthetic CSV sources, Python ETL and rules-based risk scoring, SQLite, SQL KPI views, a read-only Python service, and a Streamlit/Plotly dashboard. Power BI, machine-learning prediction, and intervention recommendations are roadmap work; they are not part of the current implementation.

The SQLite database is the operational contract. The schema in [`../sql/ddl/create_tables.sql`](../sql/ddl/create_tables.sql) uses `enrollment_id` for course-grain child facts, `fact_grade` for course-final grades, and timestamped/versioned records in `fact_risk_assessment`.

## System Architecture

```text
+----------------------+       +--------------------------+
| Synthetic CSV Sources|------>| Python validation + ETL  |
| data/raw/*.csv       |       | load_to_sqlite.py        |
+----------------------+       +------------+-------------+
                                            |
                                            v
                                 +-------------------------+
                                 | SQLite warehouse        |
                                 | dimensions + fact tables|
                                 +-----+--------------+----+
                                       |              |
                         +-------------+              +----------------+
                         v                                             v
              +----------------------+                     +--------------------+
              | Rules risk engine    |                     | KPI SQL views      |
              | calculate_risk.py    |                     | student-term grain |
              +----------+-----------+                     +---------+----------+
                         |                                           |
                         +---------------------+---------------------+
                                               v
                                   +------------------------+
                                   | KPIService (read-only) |
                                   +-----------+------------+
                                               v
                                   +------------------------+
                                   | Streamlit + Plotly     |
                                   | stakeholder dashboard  |
                                   +------------------------+
```

## Data Flow

```text
CSV source files
    -> header, domain, key, grain, range, and referential checks
    -> temporary SQLite database build
    -> transaction commit and atomic destination replacement
    -> risk assessment refresh (rules-v1)
    -> KPI view install/refresh and KPI validation
    -> cached read-only Streamlit queries
    -> filtered charts, tables, and student detail
```

ETL source files and the destination can be redirected for isolated validation. Dashboard sessions do not run ETL, write risk assessments, or install views.

## ETL Pipeline

```text
Read CSV contracts
       |
       v
Parse and normalize values ------> Reject malformed values with file/row context
       |
       v
Validate natural keys, dimensions, ranges, fact grains, and source relationships
       |
       +--> Load dimensions (department, program, course, student, term)
       |
       v
Load enrollment and generate enrollment_id lookup
       |
       +--> Course-final grade
       +--> Attendance / LMS / assignments / exams
       +--> GPA history / source risk assessments
       |
       v
Commit temporary SQLite file -> atomically replace selected destination
```

The ETL is intentionally full-refresh, not incremental. Its output replacement is atomic: an invalid source or failed insert leaves an existing destination in place.

## Risk Analytics Pipeline

```text
Enrollment + grades + attendance + assignments + exams + GPA standing
                              |
                              v
               Student-term feature aggregation
                              |
                              v
             Weighted rules score (0 to 100)
                              |
                +-------------+-------------+
                |                           |
                v                           v
       Escalation rules              Explanation reasons
                |                           |
                +-------------+-------------+
                              v
      fact_risk_assessment (rules-v1, score, label, reasons)
                              |
                              v
          latest-assessment KPI view by term/model
```

The engine uses GPA, attendance, failed courses, assignment average, and exam average. Demographic fields are not score inputs. Current escalation rules are those implemented in [`../python/src/calculate_risk.py`](../python/src/calculate_risk.py); the methodology documentation must remain synchronized with this code. Risk reasons are descriptive rule outputs and do not establish causation.

## Data and Reporting Boundaries

- Course-grain measures are aggregated to student-term before reporting joins to prevent assignment/exam fan-out.
- The selected risk model is resolved independently per student, term, and model version.
- KPI SQL views define shared business metrics; `KPIService` is a read-only adapter and validation surface.
- The dashboard derives filtered comparisons from `vw_kpi_student_term` and reads profile/course details from existing dimensions and facts.
- Streamlit caches warehouse reads for five minutes. Clear the cache or wait for expiry after ETL refresh.

## Deployment and Future Extensions

Current operation is a local Streamlit process reading one SQLite database. A production deployment would require managed secrets/configuration, access control, privacy review, operational monitoring, a controlled database service, and documented refresh ownership. Power BI integration, predictive modeling, and advisor-reviewed recommendations are tracked in [`roadmap.md`](roadmap.md).