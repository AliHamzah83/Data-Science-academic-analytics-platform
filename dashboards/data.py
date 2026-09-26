from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "python" / "src"
if str(SOURCE_PATH) not in sys.path:
    sys.path.insert(0, str(SOURCE_PATH))

from kpi_service import KPIService


class DashboardDataError(RuntimeError):
    """Raised when the warehouse cannot provide dashboard data."""


@st.cache_resource
def _service() -> KPIService:
    return KPIService(ROOT / "data" / "academic_analytics.db")


def _dashboard_error(exc: Exception) -> DashboardDataError:
    return DashboardDataError(
        "Unable to read the academic analytics warehouse. Confirm the SQLite database "
        "and KPI views are available, then run the ETL and KPI view installation steps. "
        f"Details: {exc}"
    )


@st.cache_data(ttl=300, show_spinner=False)
def load_terms() -> list[dict[str, Any]]:
    try:
        return _service().terms()
    except (FileNotFoundError, sqlite3.Error) as exc:
        raise _dashboard_error(exc) from exc


@st.cache_data(ttl=300, show_spinner=False)
def load_student_terms(model_version: str) -> pd.DataFrame:
    try:
        rows = _service().student_term_rows(model_version=model_version)
    except (FileNotFoundError, sqlite3.Error) as exc:
        raise _dashboard_error(exc) from exc
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["term_label"] = frame["academic_year"].astype(str) + " " + frame["term_name"].astype(str)
    first_name = frame["first_name"].fillna("").astype(str).str.strip()
    last_name = frame["last_name"].fillna("").astype(str).str.strip()
    frame["student_name"] = (first_name + " " + last_name).str.strip()
    frame["student_display"] = frame["student_code"].fillna(frame["student_id"].astype(str)).astype(str)
    named = frame["student_name"].ne("")
    frame.loc[named, "student_display"] += " | " + frame.loc[named, "student_name"]
    frame["risk_category"] = frame["risk_label"].fillna("Not assessed")
    return frame


@st.cache_data(ttl=300, show_spinner=False)
def load_student_profile(student_id: int, term_id: int, model_version: str) -> dict[str, Any] | None:
    try:
        return _service().student_profile(student_id, term_id, model_version)
    except (FileNotFoundError, sqlite3.Error) as exc:
        raise _dashboard_error(exc) from exc


@st.cache_data(ttl=300, show_spinner=False)
def load_failed_courses(student_id: int, term_id: int) -> pd.DataFrame:
    try:
        rows = _service().failed_courses(student_id, term_id)
    except (FileNotFoundError, sqlite3.Error) as exc:
        raise _dashboard_error(exc) from exc
    return pd.DataFrame(rows)
