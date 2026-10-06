"""
Tests for intox_analysis.data.pharmaceutical — focused on loader alignment to
the real FUR extract: column standardisation, date parsing, FUR missing-value
handling, and the configurable/optional DDD column.

Run with:  pytest tests/test_pharmaceutical.py -v
"""

from __future__ import annotations

import polars as pl
import pytest

from intox_analysis.data import generators as gen
from intox_analysis.data import pharmaceutical as ph

STANDARD_COLS = {
    "patient_id", "age_years", "sex", "prescription_date", "dispensing_date",
    "atc_code", "drug_name", "prescriber_type_code", "prescriber_type_desc", "ddd",
}


@pytest.fixture()
def fur_csv(tmp_path):
    path = tmp_path / "fur_full.csv"
    gen.generate_pharma_data(n_records=3000, seed=11).to_csv(path, index=False)
    return path


# ---------------------------------------------------------------------------
# classify_atc_code (light checks; exact labels are the module's own vocabulary)
# ---------------------------------------------------------------------------

def test_classify_atc_benzodiazepine():
    r = ph.classify_atc_code("N05BA12")  # alprazolam
    assert r["is_psychotropic"] is True
    assert r["drug_class"] == "benzodiazepine"


def test_classify_atc_non_psychotropic():
    r = ph.classify_atc_code("A02BC01")  # omeprazole
    assert r["is_psychotropic"] is False


def test_classify_atc_handles_empty():
    r = ph.classify_atc_code("")
    assert r["is_psychotropic"] is False


# ---------------------------------------------------------------------------
# Loader: full extract
# ---------------------------------------------------------------------------

def test_loader_standardises_columns(fur_csv):
    df = ph.scan_pharmaceutical_data(fur_csv).collect()
    assert STANDARD_COLS <= set(df.columns)


def test_loader_parses_dates(fur_csv):
    df = ph.scan_pharmaceutical_data(fur_csv).collect()
    assert df["dispensing_date"].dtype == pl.Datetime
    assert df["prescription_date"].dtype == pl.Datetime


def test_loader_ddd_numeric(fur_csv):
    df = ph.scan_pharmaceutical_data(fur_csv).collect()
    assert df["ddd"].dtype == pl.Float64


def test_loader_nulls_fur_missing_markers(fur_csv):
    df = ph.scan_pharmaceutical_data(fur_csv).collect()
    # "?" sex and blank ages should be null, not literal strings.
    assert "?" not in df["sex"].unique().to_list()
    assert df["age_years"].dtype == pl.Int64  # blanks nulled, column stays integer


def test_loader_can_skip_standardisation(fur_csv):
    df = ph.scan_pharmaceutical_data(fur_csv, standardise_columns=False, parse_dates=False).collect()
    assert "Cod Atc" in df.columns  # original Italian headers retained


# ---------------------------------------------------------------------------
# Loader: robustness to reduced extract and configurable DDD name
# ---------------------------------------------------------------------------

def test_loader_tolerates_missing_columns(tmp_path):
    full = gen.generate_pharma_data(n_records=500, seed=12)
    reduced = full.drop(columns=["Codice Fiscale Assistito MICROBIO", "DDD"])
    path = tmp_path / "fur_reduced.csv"
    reduced.to_csv(path, index=False)
    df = ph.scan_pharmaceutical_data(path).collect()  # must not raise
    assert "ddd" not in df.columns
    assert "patient_id" not in df.columns
    assert "atc_code" in df.columns


def test_loader_configurable_ddd_name(tmp_path, monkeypatch):
    full = gen.generate_pharma_data(n_records=500, seed=13)
    renamed = full.rename(columns={"DDD": "Dose Definita Giornaliera"})
    path = tmp_path / "fur_realddd.csv"
    renamed.to_csv(path, index=False)
    monkeypatch.setattr(ph, "DDD_SOURCE_COLUMN", "Dose Definita Giornaliera")
    df = ph.scan_pharmaceutical_data(path).collect()
    assert "ddd" in df.columns
    assert df["ddd"].dtype == pl.Float64
