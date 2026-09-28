# Setting Up PANIC in Spyder

## Step 1: Open the Project

In Spyder, go to **Projects → New Project → Existing directory** and select this folder.

Or simply open files via **File → Open**.

## Step 2: Set Working Directory

**Important!** Spyder needs to know where your project root is.

Option A: In the **Files** pane, navigate to this folder, right-click → **"Set as current working directory"**

Option B: In the IPython console:
```python
import os
os.chdir(r"C:\Users\andre\OneDrive\Documenti\PANIC")  # Your actual path
```

## Step 3: Run Setup

Open and run `setup_environment.py` (F5). This will:
1. Install all required packages
2. Verify the installation
3. Set up Python paths

## Step 4: Verify Everything Works

Run `notebooks/00_verify_setup.py` to check that all imports work correctly.

## Step 5: Run the Analysis Pipeline

```
00_generate_synthetic_data.py  → Creates test data
03_intoxication_trends.py      → Drug class trends (Q1, Q4)
04_stratified_analysis.py      → Demographics (Q3)
05_prescription_linkage.py     → Pharma linkage (Q5)
06_generate_report.py          → HTML report
```

## Dependencies

### Required
| Package | Purpose |
|---------|---------|
| `pandas` | DataFrame operations |
| `numpy` | Numerical computing |
| `matplotlib` | Visualisations |
| `polars` | Fast large file processing |
| `scipy` | Statistical tests |
| `pandera` | DataFrame validation |
| `pydantic` | Data validation |
| `pytest` | Testing |

### Optional
| Package | Purpose |
|---------|---------|
| `seaborn` | Enhanced plots |
| `statsmodels` | Segmented regression |

## Folder Structure

```
PANIC/
├── setup_environment.py      # Run FIRST
├── config.py                 # Paths and parameters
│
├── intox_analysis/           # Analysis package
│   ├── data/
│   │   ├── schemas.py        # ICD classification
│   │   ├── pharmaceutical.py # ATC codes, Polars
│   │   ├── residence.py      # Urban/rural
│   │   └── generators.py     # Synthetic data
│   └── analysis/
│       └── trends.py         # Trend functions
│
├── notebooks/                # Run these scripts
│   ├── 00_generate_synthetic_data.py
│   ├── 00_verify_setup.py
│   ├── 03_intoxication_trends.py
│   ├── 04_stratified_analysis.py
│   ├── 05_prescription_linkage.py
│   └── 06_generate_report.py
│
├── data/
│   ├── raw/                  # Your VDI exports (gitignored)
│   ├── lookups/              # ISTAT FUA (public)
│   └── processed/            # Intermediate files
│
└── outputs/
    ├── figures/              # PNG charts
    ├── tables/               # CSV tables
    └── report_*.html         # Reports
```

## Troubleshooting

### "No module named 'intox_analysis'"

Make sure your working directory is set correctly:
```python
import os
print(os.getcwd())  # Should show your PANIC folder
```

If not, set it:
```python
os.chdir(r"C:\path\to\PANIC")
```

### Import still fails after setting directory

Add the project to Python path:
```python
import sys
sys.path.insert(0, r"C:\path\to\PANIC")
```

Or use PYTHONPATH manager: **Tools → PYTHONPATH manager → Add path**

### Polars won't install

Try:
```python
import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "polars", "--user"])
```

Then restart the kernel: **Consoles → Restart kernel**
