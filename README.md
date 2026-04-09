# PANIC - Drug Intoxication Analysis

**P**harmaceutical **A**nd **N**europsychiatric **I**ntoxication **C**haracterisation

Analysis of drug intoxication trends in Lombardy Emergency Departments, 2017-2025.

## Quick Start

```bash
# 1. Run setup (installs all dependencies)
python setup_environment.py

# 2. Generate synthetic test data
python notebooks/00_generate_synthetic_data.py

# 3. Run the analysis pipeline
python notebooks/03_intoxication_trends.py
python notebooks/04_stratified_analysis.py
python notebooks/05_prescription_linkage.py

# 4. Generate the report
python notebooks/06_generate_report.py
```

## Research Questions

| # | Question | Status |
|---|----------|--------|
| Q1 | Does trend exist for ED presentations AND hospital admissions? | ✅ Answerable |
| Q2 | Does ED diagnosis agree with SDO discharge diagnosis? | ⏳ Needs SDO data |
| Q3 | Who are the patients? Trends by sex, age, urban/rural? | ✅ Answerable |
| Q4 | Is trend linked to psychiatric diagnoses increase? | ✅ Answerable |
| Q5 | Is trend linked to prescribing changes? Chronic vs sporadic? | ✅ Answerable |
| Q6 | Are prescribing changes linked to psychiatric service use? | ⏳ Needs outpatient data |

## Project Structure

```
PANIC/
├── setup_environment.py          # Run FIRST - installs dependencies
├── config.py                     # Study parameters and paths
│
├── data/
│   ├── raw/                      # VDI CSV exports (gitignored!)
│   ├── lookups/                  # ISTAT FUA lookup (public, committed)
│   └── processed/                # Intermediate files
│
├── intox_analysis/               # Analysis package
│   ├── data/
│   │   ├── schemas.py            # ICD-9/10 code classification
│   │   ├── pharmaceutical.py     # ATC codes, Polars processing
│   │   ├── residence.py          # Urban/rural classification
│   │   └── generators.py         # Synthetic data generation
│   └── analysis/
│       └── trends.py             # Trend analysis functions
│
├── notebooks/                    # Analysis scripts (run in order)
│   ├── 00_generate_synthetic_data.py
│   ├── 00_verify_setup.py
│   ├── 03_intoxication_trends.py
│   ├── 04_stratified_analysis.py
│   ├── 05_prescription_linkage.py
│   └── 06_generate_report.py
│
├── outputs/
│   ├── figures/                  # PNG charts
│   ├── tables/                   # CSV tables
│   └── report_*.html             # Generated reports
│
└── tests/                        # Unit tests (pytest)
```

## Dependencies

### Required
| Package | Purpose |
|---------|---------|
| `pandas` | DataFrame operations |
| `numpy` | Numerical computing |
| `matplotlib` | Visualisations |
| `polars` | Fast processing of large files (1GB+) |
| `scipy` | Statistical tests |
| `pandera` | DataFrame schema validation |
| `pydantic` | Data validation |
| `pytest` | Testing framework |

### Optional
| Package | Purpose |
|---------|---------|
| `seaborn` | Enhanced statistical plots |
| `statsmodels` | Segmented regression / ITS |

All installed automatically by `setup_environment.py`.

## Key Features

### ICD Code Classification (ED Data)
```python
from intox_analysis.data.schemas import classify_drug_intoxication

classify_drug_intoxication("T424X2A")  # → benzodiazepine, self-harm (ICD-10)
classify_drug_intoxication("9694")      # → benzodiazepine (ICD-9)
```

### ATC Drug Classification (Pharma Data)
```python
from intox_analysis.data.pharmaceutical import classify_atc_code

classify_atc_code("N05BA12")  # → benzodiazepine (Alprazolam)
classify_atc_code("N05CF01")  # → z_drug (Zopiclone)
```

### Memory-Efficient Pharma Processing
```python
from intox_analysis.data.pharmaceutical import scan_pharmaceutical_data

# Lazy loading - processes 1GB+ files without memory issues
lf = scan_pharmaceutical_data(["pharma_2017.csv", "pharma_2018.csv"])
result = lf.filter(pl.col("is_benzodiazepine")).collect()
```

### Urban/Rural Classification
```python
from intox_analysis.data.residence import setup_urban_rural_classification

mapping, _ = setup_urban_rural_classification("data/lookups/istat_fua_comuni.csv")
# "Milano" → Urban, "Bormio" → Rural
```

## Data Sources

| Source | Description | Key Variables |
|--------|-------------|---------------|
| ED Syndromic | Emergency presentations | ICD diagnosis, age, sex, facility, residence |
| Pharmaceutical | Prescription dispensations | ATC code, DDD, patient ID |
| FUA Lookup | ISTAT urban/rural classification | Municipality → Urban/Rural |
| SDO | Hospital discharges | (future) |
| Outpatient | Mental health contacts | (future) |

## Outputs

### Figures
- `intox_annual_trends.png` - Drug class trends over time
- `intox_trends_by_sex.png` - Stratified by sex
- `intox_trends_by_age.png` - Stratified by age group
- `intox_trends_by_residence.png` - Urban vs rural
- `forest_plot_age.png` - Growth rates by age
- `prescribing_ddd_trends.png` - Prescribing volume trends

### Tables
- `trends_by_sex.csv` - Trend metrics by sex
- `trends_by_age_group.csv` - Trend metrics by age
- `trends_by_residence.csv` - Trend metrics by urban/rural
- `prescribing_ddd_annual.csv` - Annual DDD rates
- `prescription_linkage_summary.csv` - Linkage results

### Report
- `report_drug_intoxication_lombardy.html` - Complete HTML report

## License

[To be determined]

## Authors

[To be added]
