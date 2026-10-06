"""
Tests for intox_analysis.data.generators.

Verifies that the synthetic data matches the real VDI column structure and that
every intoxication code the generator emits classifies back to the same drug
class the taxonomy assigns it (so the synthetic ground truth is self-consistent).

Run with:  pytest tests/test_generators.py -v
"""

from __future__ import annotations

import pandas as pd
import pytest

from intox_analysis.data import generators as gen
from intox_analysis.data.schemas import classify_drug_intoxication

ED_COLUMNS = [
    "Codice Fiscale Assistito MICROBIO", "Annomese_INGR", "Eta(calcolata)",
    "Sesso (anag ass.to)", "Sesso (flusso)", "Cod Diagnosi", "Diagnosi",
    "Cod Diagnosi Secondaria", "Diagnosi Secondaria", "Codice Esito",
    "Descrizione Esito", "Codice Nazione(flusso)", "Conteggio Persone fisiche",
    "facility_id", "residence",
]
PHARMA_COLUMNS = [
    "Codice Fiscale Assistito MICROBIO", "Eta Anni", "Sesso",
    "Data Prescrizione.Data", "Data Erogazione.Data", "Cod Atc", "Desc Atc",
    "Cod Tipo Medico", "Desc Tipo Medico", "DDD",
]


@pytest.fixture(scope="module")
def ed():
    return gen.generate_ed_data(n_records=8000, seed=1)


@pytest.fixture(scope="module")
def pharma():
    return gen.generate_pharma_data(n_records=8000, seed=2)


# ---------------------------------------------------------------------------
# Column structure matches the real extracts
# ---------------------------------------------------------------------------

def test_ed_columns_exact(ed):
    assert list(ed.columns) == ED_COLUMNS


def test_pharma_columns_exact(pharma):
    assert list(pharma.columns) == PHARMA_COLUMNS


def test_ed_static_fields(ed):
    assert (ed["Conteggio Persone fisiche"] == 1).all()
    assert (ed["Codice Nazione(flusso)"] == "100").all()
    assert ed["Codice Fiscale Assistito MICROBIO"].str.match(r"^MB-[A-F0-9]{64}$").all()


# ---------------------------------------------------------------------------
# Every intoxication code round-trips to its taxonomy class
# ---------------------------------------------------------------------------

def test_generated_intox_codes_roundtrip():
    # Build the generator's own ground-truth mapping and classify each code.
    for table in (gen.ICD10_CODES_BY_CLASS, gen.ICD9_CODES_BY_CLASS):
        for expected_class, codes in table.items():
            for code in codes:
                result = classify_drug_intoxication(code)
                assert result["is_intoxication"] is True, code
                assert result["drug_class"] == expected_class, (code, result["drug_class"])


def test_all_classes_appear_in_data():
    # A large ICD-10-era extract should exercise every class except anxiolytic
    # (which is ICD-9 only by design).
    df = gen.generate_ed_data(n_records=40000, seed=7, icd10_transition_yearmonth="201701")
    intox = df[df["Cod Diagnosi"].isin(gen.ALL_INTOX_CODES)]
    classes = {classify_drug_intoxication(c)["drug_class"] for c in intox["Cod Diagnosi"]}
    expected = set(gen.ICD10_CODES_BY_CLASS)  # no anxiolytic in ICD-10 era
    assert expected <= classes


def test_non_intox_codes_not_flagged(ed):
    non = ed[~ed["Cod Diagnosi"].isin(gen.ALL_INTOX_CODES)]
    sample = non["Cod Diagnosi"].drop_duplicates().tolist()
    for code in sample:
        assert classify_drug_intoxication(code)["is_intoxication"] is False, code


# ---------------------------------------------------------------------------
# Esito / admission
# ---------------------------------------------------------------------------

def test_esito_values_valid(ed):
    assert set(ed["Codice Esito"].unique()) <= set(gen.ESITO_DISTRIBUTION)
    # admission dispositions (2 ward, 3 transfer) should occur in a sample this size
    assert ed["Codice Esito"].isin({"2", "3"}).any()


# ---------------------------------------------------------------------------
# Pharma specifics
# ---------------------------------------------------------------------------

def test_pharma_atc_in_scope(pharma):
    assert pharma["Cod Atc"].str.startswith(("N05", "N06")).all()


def test_pharma_ddd_numeric_and_present(pharma):
    assert gen.DDD_COLUMN in pharma.columns
    assert pd.api.types.is_numeric_dtype(pharma["DDD"])
    assert (pharma["DDD"] >= 0).all()


def test_pharma_dates_formatted(pharma):
    assert pharma["Data Erogazione.Data"].str.match(r"^\d{4}/\d{2}/\d{2} 00:00:00$").all()


# ---------------------------------------------------------------------------
# Linkage and reproducibility
# ---------------------------------------------------------------------------

def test_linked_data_has_patient_overlap():
    ed, pharma = gen.generate_linked_data(n_ed_records=8000, n_pharma_records=8000, seed=3)
    ed_intox = set(ed.loc[ed["Cod Diagnosi"].isin(gen.ALL_INTOX_CODES),
                          "Codice Fiscale Assistito MICROBIO"])
    rx = set(pharma["Codice Fiscale Assistito MICROBIO"])
    overlap = ed_intox & rx
    assert len(overlap) > 0  # some intoxication patients have prescriptions


def test_reproducible(ed):
    again = gen.generate_ed_data(n_records=8000, seed=1)
    pd.testing.assert_frame_equal(ed, again)
