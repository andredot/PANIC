"""
Unit tests for intox_analysis.data.schemas.

Covers ICD-9/ICD-10 drug-intoxication detection and the ATC-aligned drug-class
taxonomy:

    benzodiazepine        (T42.4 / 969.4 - kept as its own class)
    antipsychotic         (N05A)
    anxiolytic            (N05B, ICD-9 969.5)
    hypnotic_sedative     (N05C)
    antidepressant        (N06A)
    psychostimulant       (N06B, MDMA excluded)
    non_medical           (opioids, cocaine, cannabis, hallucinogens, MDMA)
    other                 (everything else in range)

Also covers: all intents counting as cases (no adverse-effect exclusion),
admission logic including transfers, missing-value handling, column-name
standardisation, and the EDPresentation record model.

Run with:  pytest tests/test_schemas.py -v
"""

from __future__ import annotations

import pytest
import pandas as pd

from intox_analysis.data.schemas import (
    ADMISSION_ESITO_CODES,
    COLUMN_NAME_MAPPING,
    EDPresentation,
    classify_drug_intoxication,
    is_drug_intoxication_icd9,
    is_drug_intoxication_icd10,
    is_missing,
    restore_column_names,
    standardise_column_names,
)


def cls(code):
    """Shorthand: drug_class assigned to a code."""
    return classify_drug_intoxication(code)["drug_class"]


# ---------------------------------------------------------------------------
# is_missing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", ["_", "DATO NON APPLICABILE", "", "   ", None])
def test_is_missing_true(value):
    assert is_missing(value) is True


@pytest.mark.parametrize("value", ["30750", "T424X1A", "9694", "0"])
def test_is_missing_false(value):
    assert is_missing(value) is False


# ---------------------------------------------------------------------------
# Gate: what counts as a drug-poisoning case
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("code", ["960", "9694", "969.4", "979", "9790", " 965 "])
def test_icd9_gate_true(code):
    assert is_drug_intoxication_icd9(code) is True


@pytest.mark.parametrize("code", ["959", "980", "30750", "F329", "", "T424"])
def test_icd9_gate_false(code):
    assert is_drug_intoxication_icd9(code) is False


@pytest.mark.parametrize("code", ["T360X1A", "T424X1A", "T42.4X2A", "T405X1A", "T500X4A"])
def test_icd10_gate_true(code):
    assert is_drug_intoxication_icd10(code) is True


@pytest.mark.parametrize("code", ["T350X1A", "T510X1A", "F329", "30750", "", "T"])
def test_icd10_gate_false(code):
    assert is_drug_intoxication_icd10(code) is False


def test_all_intents_count_as_cases():
    # Per study decision, intent no longer filters cases:
    # adverse effect (5) and underdosing (6) are now included.
    assert is_drug_intoxication_icd10("T424X5A") is True   # adverse effect
    assert is_drug_intoxication_icd10("T424X6A") is True   # underdosing
    # The include_adverse_effects flag is retained but inert.
    assert is_drug_intoxication_icd10("T424X5A", include_adverse_effects=False) is True


# ---------------------------------------------------------------------------
# Drug-class taxonomy - the named medical classes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "code, expected",
    [
        # benzodiazepine (own class)
        ("9694", "benzodiazepine"),
        ("969.4", "benzodiazepine"),
        ("T424X1A", "benzodiazepine"),
        # antipsychotic - N05A
        ("9691", "antipsychotic"),
        ("9692", "antipsychotic"),
        ("9693", "antipsychotic"),
        ("T433X1A", "antipsychotic"),
        ("T434X1A", "antipsychotic"),
        ("T435X1A", "antipsychotic"),
        # anxiolytic - N05B (ICD-9 only)
        ("9695", "anxiolytic"),
        # hypnotic_sedative - N05C
        ("9670", "hypnotic_sedative"),
        ("967", "hypnotic_sedative"),
        ("T423X1A", "hypnotic_sedative"),
        ("T426X1A", "hypnotic_sedative"),
        # antidepressant - N06A
        ("9690", "antidepressant"),
        ("T430X1A", "antidepressant"),
        ("T431X1A", "antidepressant"),
        ("T432X1A", "antidepressant"),
        # psychostimulant - N06B (MDMA excluded, see below)
        ("9697", "psychostimulant"),
        ("9700", "psychostimulant"),    # 970.0 other CNS stimulant
        ("97089", "psychostimulant"),   # 970.89 other CNS stimulant
        ("T4362X1A", "psychostimulant"),  # amphetamine
        ("T4363X1A", "psychostimulant"),  # methylphenidate
    ],
)
def test_named_medical_classes(code, expected):
    assert cls(code) == expected


# ---------------------------------------------------------------------------
# Drug-class taxonomy - non_medical (single undifferentiated bucket)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "code, what",
    [
        # ICD-9
        ("9696", "cannabis/hallucinogens (969.6)"),
        ("97081", "cocaine (970.81)"),
        ("96500", "opium (965.00)"),
        ("96501", "heroin (965.01)"),
        ("96502", "methadone (965.02)"),
        ("96509", "other opiates (965.09)"),
        # ICD-10
        ("T400X1A", "opium (T40.0)"),
        ("T401X1A", "heroin (T40.1)"),
        ("T402X1A", "other opioids (T40.2)"),
        ("T403X1A", "methadone (T40.3)"),
        ("T404X1A", "synthetic narcotics (T40.4)"),
        ("T405X1A", "cocaine (T40.5)"),
        ("T407X1A", "cannabis (T40.7)"),
        ("T408X1A", "LSD (T40.8)"),
        ("T4364X1A", "MDMA / ecstasy (T43.64)"),
    ],
)
def test_non_medical_bucket(code, what):
    assert cls(code) == "non_medical", what


# ---------------------------------------------------------------------------
# Drug-class taxonomy - "other" (in range but not a tracked subgroup)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "code",
    [
        "965",        # unspecified analgesic
        "9654",       # 965.4 aromatic analgesics (paracetamol)
        "972",        # cardiovascular agents
        "962",        # hormones
        "T391X1A",    # paracetamol (nonopioid analgesic)
        "T450X1A",    # antiallergic/antiemetic
    ],
)
def test_other_bucket(code):
    assert cls(code) == "other"


# ---------------------------------------------------------------------------
# Regression guards for the specific reclassification decisions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("code", ["9691", "969.1", "T433X1A"])
def test_phenothiazines_are_antipsychotic_not_antidepressant(code):
    assert cls(code) == "antipsychotic"
    assert cls(code) != "antidepressant"


@pytest.mark.parametrize("code", ["97081", "T405X1A"])
def test_cocaine_is_non_medical_not_stimulant(code):
    assert cls(code) == "non_medical"


def test_mdma_is_non_medical_not_psychostimulant():
    assert cls("T4364X1A") == "non_medical"
    # ...but other T43.6 psychostimulants are not swept into non_medical
    assert cls("T4362X1A") == "psychostimulant"


@pytest.mark.parametrize("code", ["96501", "T401X1A"])
def test_opioids_are_non_medical(code):
    assert cls(code) == "non_medical"


def test_old_class_labels_are_gone():
    # The pre-refactor scheme used a single "stimulant" label; it must not appear.
    assert cls("T436X1A") != "stimulant"
    assert cls("9697") != "stimulant"


# ---------------------------------------------------------------------------
# Coding-system detection, intent recording, and edge cases
# ---------------------------------------------------------------------------

def test_coding_system_detected():
    assert classify_drug_intoxication("9694")["coding_system"] == "ICD-9"
    assert classify_drug_intoxication("T424X1A")["coding_system"] == "ICD-10"


def test_intent_still_recorded_for_icd10():
    assert classify_drug_intoxication("T424X2A")["intent"] == "Intentional self-harm"
    assert classify_drug_intoxication("T424X5A")["intent"] == "Adverse effect"


def test_classify_non_intoxication():
    result = classify_drug_intoxication("30750")  # anxiety state, not poisoning
    assert result["is_intoxication"] is False
    assert result["drug_class"] is None


def test_classify_empty_code_does_not_crash():
    for code in ["", "   ", "."]:
        result = classify_drug_intoxication(code)
        assert result["is_intoxication"] is False
        assert result["drug_class"] is None


# ---------------------------------------------------------------------------
# Admission logic (transfers now count)
# ---------------------------------------------------------------------------

def test_transfer_counts_as_admission():
    assert "5" in ADMISSION_ESITO_CODES            # transfer
    assert ADMISSION_ESITO_CODES == {"2", "3", "4", "5"}
    assert "1" not in ADMISSION_ESITO_CODES         # discharged home


# ---------------------------------------------------------------------------
# EDPresentation record model
# ---------------------------------------------------------------------------

VALID_CF = "MB-" + "A" * 64


def _make(**overrides):
    base = dict(
        codice_fiscale_assistito_microbio=VALID_CF,
        annomese_ingr="201907",
        eta_calcolata=16,
        sesso="F",
        cod_diagnosi="30750",
        codice_esito="1",
    )
    base.update(overrides)
    return EDPresentation(**base)


def test_record_year_month():
    assert _make().year_month == (2019, 7)


def test_record_is_drug_intoxication():
    assert _make(cod_diagnosi="30750").is_drug_intoxication is False
    assert _make(cod_diagnosi="T424X1A").is_drug_intoxication is True
    assert _make(cod_diagnosi="30750", cod_diagnosi_secondaria="9694").is_drug_intoxication is True


def test_record_is_admitted():
    assert _make(codice_esito="1").is_admitted is False
    for code in ADMISSION_ESITO_CODES:
        assert _make(codice_esito=code).is_admitted is True


def test_record_drug_classification_property():
    assert _make(cod_diagnosi="T433X1A").drug_classification["drug_class"] == "antipsychotic"
    assert _make(cod_diagnosi="T405X1A").drug_classification["drug_class"] == "non_medical"
    assert _make(cod_diagnosi="30750").drug_classification is None


@pytest.mark.parametrize("bad_date", ["201612", "202601", "201913"])
def test_record_rejects_dates_outside_study_period(bad_date):
    with pytest.raises(ValueError):
        _make(annomese_ingr=bad_date)


# ---------------------------------------------------------------------------
# Column name standardisation
# ---------------------------------------------------------------------------

def test_column_name_roundtrip():
    italian_cols = list(COLUMN_NAME_MAPPING.keys())
    df = pd.DataFrame({c: [1] for c in italian_cols})
    standardised = standardise_column_names(df)
    assert "codice_fiscale_assistito_microbio" in standardised.columns
    restored = restore_column_names(standardised)
    assert list(restored.columns) == italian_cols
