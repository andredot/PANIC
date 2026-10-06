# PANIC — canonical analysis pipeline

One pipeline, config-driven. All settings live in `config.py`; scripts read from
and write to the locations it defines. Run in order.

| # | Script | Purpose | Prerequisite |
|---|--------|---------|--------------|
| — | `00_verify_setup.py` | Check environment, dependencies, and `config.py` load | none |
| — | `00_generate_synthetic_data.py` | Generate synthetic ED + FUR CSVs for out-of-VDI development (skip when using real data) | none |
| 1 | `01_load_ed_data.py` | Load/validate ED presentations, standardise columns, flag intoxications | 00 (data present) |
| 2 | `02_load_pharma_data.py` | Load/validate FUR dispensations (Polars), classify ATC, derive columns | 00 (data present) |
| 5 | `05_intoxication_trends.py` | Drug-class trends over time (segmented regression) | 01 |
| 6 | `06_stratified_analysis.py` | Stratification by sex / age group / residence | 01 |
| 7 | `07_prescription_linkage.py` | Link ED intoxication patients to prior prescriptions (Q5) | 01, 02 |
| 8 | `08_generate_report.py` | Compile figures/tables into the final report | 01, 02, 05, 06, 07 |

> **Numbering gap (03/04):** the canonical scripts jump from 02 to 05. Those
> numbers were freed by deleting the old generation; the gap is cosmetic and can
> be closed later (see cleanup script).

## Removed in the de-duplication

The following **stale** scripts (a pre-`config.py` generation) were deleted.
They collided with the new numbering, referenced a `notebooks/` layout and an
`analysis/trends.py` "to be created", and read outputs the new pipeline no
longer produces:

- `01_getting_started.py`
- `03_intoxication_trends.py`  (superseded by `05_intoxication_trends.py`)
- `04_stratified_analysis.py`  (superseded by `06_stratified_analysis.py`)
- `05_prescription_linkage.py` (superseded by `07_prescription_linkage.py`)
- `06_generate_report.py`      (superseded by `08_generate_report.py`)

## Manual follow-ups the delete can't do

1. **`00_generate_synthetic_data.py`** — update its printed "NEXT STEPS" block,
   which still lists the old `03/04/05` names, to `05_intoxication_trends`,
   `06_stratified_analysis`, `07_prescription_linkage`, `08_generate_report`.
2. **`pharmaceutical.py`** — remove `generate_synthetic_pharmaceutical_data()`;
   `generators.py::generate_pharma_data` is now the single source of synthetic
   data. Redirect any import accordingly.

## Related reconciliations (tracked elsewhere)

- **Filename:** real ED file is `ed_presentation.csv` (singular) while the
  generator/`config.py` use `ed_presentations.csv` (plural). Make
  `config.ED_DATA_FILE` match whichever you standardise on.
- **DDD column:** set `pharmaceutical.DDD_SOURCE_COLUMN` to the real FUR header
  once known (loader already handles it, and tolerates its absence).
- **Taxonomy harmonisation:** `pharmaceutical.classify_atc_code` still returns
  `stimulant`/`z_drug`/`opioid` labels; align these with the ED taxonomy
  (`psychostimulant`, `hypnotic_sedative`, `non_medical`, add `antipsychotic`)
  before the linkage compares drug classes across the two flows.
