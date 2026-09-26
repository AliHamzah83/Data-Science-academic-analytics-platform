# Future Roadmap

## Current Baseline

The completed MVP contains synthetic data generation, validated full-refresh ETL to SQLite, an explainable rules-based risk assessment, SQL KPI views, read-only Python KPI services, and a five-page Streamlit dashboard. Future work should preserve these KPI contracts and keep human review central to student support.

## Phase 2: Power BI Integration

**Objective:** Reproduce the existing stakeholder experience in Power BI using the current KPI definitions, not a parallel set of business logic.

**Planned work:**
- Define a supported refresh and connection pattern for the SQLite-derived reporting layer.
- Map term, department, program, and risk filters to the existing reporting grain.
- Build executive, department/program, and risk-review pages with measure parity to Streamlit.
- Document refresh ownership, data lineage, and published synthetic-data notice.

**Exit criteria:**
- All displayed measures reconcile to KPI SQL outputs for a documented test cohort.
- Risk share and failure-rate denominators are explicit in report tooltips/docs.
- Refresh and connection steps are reproducible on a clean environment.
- No student-level identifying data is published beyond synthetic portfolio records.

## Phase 3: Machine Learning Risk Prediction

**Objective:** Evaluate whether a predictive model adds reliable early-warning value beyond the rules-based baseline.

**Planned work:**
- Define a target from a later outcome period and enforce a time-aware, student-safe train/validation/test split.
- Audit target leakage, label quality, missingness, class balance, and synthetic-data limitations.
- Compare a simple baseline with candidate models using recall/precision, calibration, and threshold trade-offs.
- Review subgroup performance and document intended use, limitations, monitoring, and versioning.
- Retain rules-v1 as a benchmark until evidence supports a change.

**Exit criteria:**
- No future-period predictors leak into training features.
- Evaluation is reproducible and compares against rules-v1.
- Threshold selection is tied to an explicit review capacity and error-cost discussion.
- Governance review approves any use beyond demonstration.

## Phase 4: Student Intervention Recommendation System

**Objective:** Support advisors with transparent next-step suggestions using validated intervention and outcome records, without automating high-impact student decisions.

**Prerequisites:**
- Authoritative intervention events with dates, type, owner, status, and outcomes.
- Stakeholder-approved support catalog and referral criteria.
- Privacy, access-control, retention, and human-oversight requirements.

**Planned work:**
- Analyze observed intervention outcomes with selection-bias caveats.
- Present eligible support options and evidence/rationale to an authorized advisor.
- Record advisor acceptance/override and subsequent outcomes for evaluation.
- Test for disparate impact, inappropriate recommendations, and feedback loops.

**Exit criteria:**
- Recommendations are advisory, explainable, and overrideable by a human.
- No recommendation is framed as a student diagnosis or entitlement decision.
- Outcome evaluation and privacy/governance approvals are in place before operational deployment.

## Cross-Phase Guardrails

- Keep synthetic demonstration data visibly distinguished from real institutional data.
- Preserve KPI definitions in a shared semantic contract and reconcile consuming tools to it.
- Version model changes and retain an interpretable benchmark.
- Do not infer causality from risk-reason frequency or observational comparisons.
- Require stakeholder, privacy, security, and governance review before any real-data deployment.