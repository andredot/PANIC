# PANIC - Drug Intoxication Analysis

**P**harmaceutical **A**nd **N**europsychiatric **I**ntoxication **C**haracterisation

Analysis of drug intoxication trends in Lombardy Emergency Departments, 2017-2025.

---

## Quick Start

```bash
# 1. Run setup (installs dependencies)
python setup_environment.py

# 2. Verify installation
python notebooks/00_verify_setup.py

# 3. Generate synthetic test data (optional, for testing)
python notebooks/01_load_ed_data.py

# 4. Run the analysis pipeline
python notebooks/05_intoxication_trends.py
python notebooks/06_stratified_analysis.py
python notebooks/07_prescription_linkage.py
python notebooks/08_generate_report.py
```

---

## Setup in Spyder

### Step 1: Open the Project

In Spyder: **Projects -> New Project -> Existing directory** -> select this folder.

Or simply open files via **File -> Open**.

### Step 2: Set Working Directory

**Important!** Spyder needs to know where your project root is.

**Option A:** In the **Files** pane, navigate to this folder, right-click -> **Set as current working directory**

**Option B:** In the IPython console:
```python
import os
os.chdir(r"C:\Users\YourName\Documents\PANIC")  # Your actual path
```

### Step 3: Run Setup

Open and run `setup_environment.py` (F5). This will:
1. Install required packages
2. Verify the installation
3. Set up Python paths

### Step 4: Verify Everything Works

Run `notebooks/00_verify_setup.py` to check that all imports work correctly.

### Troubleshooting

**"No module named 'intox_analysis'"**

Make sure your working directory is set correctly:
```python
import os
print(os.getcwd())  # Should show your PANIC folder
```

If not, set it:
```python
os.chdir(r"C:\path\to\PANIC")
```

**Import still fails after setting directory**

Add the project to Python path:
```python
import sys
sys.path.insert(0, r"C:\path\to\PANIC")
```

Or use PYTHONPATH manager: **Tools -> PYTHONPATH manager -> Add path**

---

## Research Questions

| # | Question | Status |
|---|----------|--------|
| Q1 | Does trend exist for ED presentations AND hospital admissions? | Available |
| Q2 | Does ED diagnosis agree with SDO discharge diagnosis? | Needs SDO data |
| Q3 | Who are the patients? Trends by sex, age, urban/rural? | Available (urban/rural optional) |
| Q4 | Is trend linked to psychiatric diagnoses increase? | Available |
| Q5 | Is trend linked to prescribing changes? Chronic vs sporadic? | Available |
| Q6 | Are prescribing changes linked to psychiatric service use? | Needs outpatient data |

---

## Project Structure

```
PANIC/
├── setup_environment.py          # Run FIRST - installs dependencies
├── config.py                     # ALL study parameters and paths
│
├── data/
│   ├── raw/                      # VDI CSV exports (gitignored!)
│   ├── lookups/                  # Optional lookup tables
│   └── processed/                # Intermediate files
│
├── intox_analysis/               # Analysis package
│   ├── data/
│   │   ├── schemas.py            # ICD-9/10 code classification
│   │   ├── pharmaceutical.py     # ATC codes, pandas/polars processing
│   │   ├── residence.py          # Urban/rural classification (optional)
│   │   └── generators.py         # Synthetic data generation
│   └── analysis/
│       └── trends.py             # Trend analysis functions
│
├── notebooks/                    # Analysis scripts (run in order)
│   ├── 00_verify_setup.py        # Check installation
│   ├── 01_load_ed_data.py        # Load ED data
│   ├── 02_load_pharma_data.py    # Load pharmaceutical data
│   ├── 05_intoxication_trends.py # Drug class trends
│   ├── 06_stratified_analysis.py # Demographics
│   ├── 07_prescription_linkage.py# Pharma linkage
│   └── 08_generate_report.py     # HTML report
│
├── outputs/
│   ├── figures/                  # PNG charts
│   ├── tables/                   # CSV tables
│   └── report_*.html             # Generated reports
│
└── tests/                        # Unit tests (pytest)
```

---

## Configuration

**All study parameters are in `config.py`**. Change settings there and they propagate everywhere.

### Key Settings

```python
# Study period
STUDY_START_YEAR = 2017
STUDY_END_YEAR = 2025

# COVID interruption point
COVID_INTERRUPTION_DATE = "2020-03"

# Age groups for stratification
AGE_GROUPS = {
    "0-17": (0, 17),
    "18-34": (18, 34),
    ...
}

# ICD codes for intoxication (T36-T50 for ICD-10, 960-979 for ICD-9)
ICD10_INTOX_PREFIXES = ["T36", "T37", "T38", ...]
ICD9_INTOX_RANGE = (960, 979)

# Drug classes of interest
PRIMARY_DRUG_CLASSES = ["benzodiazepine", "opioid", "antidepressant", ...]
```

---

## Dependencies

### Required
| Package | Purpose |
|---------|---------|
| `pandas` | DataFrame operations |
| `numpy` | Numerical computing |
| `matplotlib` | Visualisations |
| `scipy` | Statistical tests |

### Optional (Enhanced Features)
| Package | Purpose | Fallback |
|---------|---------|----------|
| `polars` | Fast large file processing | Uses pandas |
| `statsmodels` | Segmented regression | Basic trends only |
| `seaborn` | Enhanced plots | Uses matplotlib |

### Validation (Recommended)
| Package | Purpose |
|---------|---------|
| `pandera` | DataFrame schema validation |
| `pydantic` | Data validation |
| `pytest` | Testing framework |

All installed automatically by `setup_environment.py`. The pipeline works even if optional packages fail to install.

---

## Data Sources

| Source | Description | Key Variables |
|--------|-------------|---------------|
| ED Syndromic | Emergency presentations | ICD diagnosis, age, sex, facility |
| Pharmaceutical | Prescription dispensations | ATC code, DDD, patient ID |
| FUA Lookup | Urban/rural classification | Optional - privacy restrictions |
| SDO | Hospital discharges | Future |
| Outpatient | Mental health contacts | Future |

---

## Outputs

### Figures
- `intox_annual_trends.png` - Drug class trends over time
- `intox_trends_by_sex.png` - Stratified by sex
- `intox_trends_by_age.png` - Stratified by age group
- `forest_plot_age.png` - Growth rates by age
- `prescribing_ddd_trends.png` - Prescribing volume trends

### Tables
- `trends_by_sex.csv` - Trend metrics by sex
- `trends_by_age_group.csv` - Trend metrics by age
- `prescribing_ddd_annual.csv` - Annual DDD rates
- `prescription_linkage_summary.csv` - Linkage results

### Report
- `report_drug_intoxication_lombardy.html` - Complete HTML report

---

## License

[To be determined]

## Authors

[To be added]

## Repository

https://github.com/andredot/PANIC
