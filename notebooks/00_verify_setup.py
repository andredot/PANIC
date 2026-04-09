# -*- coding: utf-8 -*-
"""
00_verify_setup.py
==================

Run this script to verify your environment is set up correctly.
It checks that all required packages are installed and that the 
project structure is correct.

To run: Press F5 or click the green "Run" button in Spyder.
"""

import sys
from pathlib import Path

print("=" * 70)
print("PANIC - SETUP VERIFICATION")
print("=" * 70)
print()

# =============================================================================
# Step 1: Python Version
# =============================================================================
print("1. Python Version")
print(f"   {sys.version}")
print()

# =============================================================================
# Step 2: Add project to path
# =============================================================================
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
print(f"2. Project Root")
print(f"   {project_root}")
print(f"   Added to Python path: ✓")
print()

# =============================================================================
# Step 3: Check required packages
# =============================================================================
print("3. Required Packages")
print("-" * 40)

packages = {
    # Core
    "pandas": ("pandas", True),
    "numpy": ("numpy", True),
    "matplotlib": ("matplotlib.pyplot", True),
    # Analysis
    "polars": ("polars", True),
    "scipy": ("scipy", True),
    # Validation
    "pandera": ("pandera", True),
    "pydantic": ("pydantic", True),
    "pytest": ("pytest", True),
    # Optional
    "seaborn": ("seaborn", False),
    "statsmodels": ("statsmodels", False),
}

missing_required = []
missing_optional = []

for name, (import_name, required) in packages.items():
    try:
        mod = __import__(import_name.split(".")[0])
        version = getattr(mod, "__version__", "?")
        marker = "*" if required else " "
        print(f"   ✓ {name:15} v{version:12} {marker}")
    except ImportError:
        marker = "*" if required else " "
        if required:
            print(f"   ✗ {name:15} NOT INSTALLED   {marker}")
            missing_required.append(name)
        else:
            print(f"   - {name:15} not installed")
            missing_optional.append(name)

print()
print("   * = required")

if missing_required:
    print()
    print("   To install missing packages:")
    print(f"   pip install {' '.join(missing_required)} --user")
print()

# =============================================================================
# Step 4: Check project modules
# =============================================================================
print("4. Project Modules")
print("-" * 40)

modules_to_check = [
    ("intox_analysis.data.schemas", "ICD code classification"),
    ("intox_analysis.data.pharmaceutical", "ATC drug classification"),
    ("intox_analysis.data.residence", "Urban/rural classification"),
    ("intox_analysis.data.generators", "Synthetic data generation"),
    ("intox_analysis.analysis.trends", "Trend analysis"),
]

modules_ok = True
for module_name, description in modules_to_check:
    try:
        __import__(module_name)
        print(f"   ✓ {description}")
    except ImportError as e:
        print(f"   ✗ {description}")
        print(f"     Error: {e}")
        modules_ok = False

print()

# =============================================================================
# Step 5: Quick function tests
# =============================================================================
print("5. Function Tests")
print("-" * 40)

# Test ICD classification
try:
    from intox_analysis.data.schemas import classify_drug_intoxication
    result = classify_drug_intoxication("T424X2A")
    if result["is_intoxication"] and result["drug_class"] == "benzodiazepine":
        print("   ✓ ICD-10 classification (T424X2A → benzodiazepine)")
    else:
        print(f"   ✗ ICD-10 unexpected result: {result}")
except Exception as e:
    print(f"   ✗ ICD classification error: {e}")

# Test ICD-9 classification
try:
    from intox_analysis.data.schemas import classify_drug_intoxication
    result = classify_drug_intoxication("9694")
    if result["is_intoxication"] and result["drug_class"] == "benzodiazepine":
        print("   ✓ ICD-9 classification (9694 → benzodiazepine)")
    else:
        print(f"   ✗ ICD-9 unexpected result: {result}")
except Exception as e:
    print(f"   ✗ ICD-9 classification error: {e}")

# Test ATC classification
try:
    from intox_analysis.data.pharmaceutical import classify_atc_code
    result = classify_atc_code("N05BA12")
    if result["drug_class"] == "benzodiazepine":
        print("   ✓ ATC classification (N05BA12 → benzodiazepine)")
    else:
        print(f"   ✗ ATC unexpected result: {result}")
except Exception as e:
    print(f"   ✗ ATC classification error: {e}")

print()

# =============================================================================
# Step 6: Check directory structure
# =============================================================================
print("6. Directory Structure")
print("-" * 40)

dirs_to_check = [
    ("data/raw", "VDI data exports"),
    ("data/lookups", "ISTAT FUA lookup"),
    ("data/processed", "Intermediate files"),
    ("outputs/figures", "Generated charts"),
    ("outputs/tables", "Generated tables"),
]

for rel_path, description in dirs_to_check:
    full_path = project_root / rel_path
    if full_path.exists():
        print(f"   ✓ {rel_path:20} ({description})")
    else:
        print(f"   - {rel_path:20} (creating...)")
        full_path.mkdir(parents=True, exist_ok=True)

print()

# =============================================================================
# Step 7: Check for data files
# =============================================================================
print("7. Data Files")
print("-" * 40)

data_dir = project_root / "data" / "raw"
lookups_dir = project_root / "data" / "lookups"

# Check raw data
print("   data/raw/:")
if data_dir.exists():
    files = list(data_dir.glob("*.csv"))
    if files:
        for f in files[:5]:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"     • {f.name} ({size_mb:.1f} MB)")
        if len(files) > 5:
            print(f"     ... and {len(files) - 5} more files")
    else:
        print("     (empty - run 00_generate_synthetic_data.py or add your data)")
else:
    print("     (directory will be created)")

# Check lookups
print("   data/lookups/:")
if lookups_dir.exists():
    files = list(lookups_dir.glob("*.csv"))
    if files:
        for f in files:
            print(f"     • {f.name}")
    else:
        print("     (empty - FUA lookup will be generated with synthetic data)")
else:
    print("     (directory will be created)")

print()

# =============================================================================
# Summary
# =============================================================================
print("=" * 70)
print("SUMMARY")
print("=" * 70)

all_ok = len(missing_required) == 0 and modules_ok

if all_ok:
    print("""
✓ Setup is complete! Your environment is ready.

Next steps:
  1. Run 00_generate_synthetic_data.py to create test data
  2. Run 03_intoxication_trends.py for trend analysis
  3. Run 04_stratified_analysis.py for demographics
  4. Run 05_prescription_linkage.py for pharma linkage
  5. Run 06_generate_report.py to create HTML report
""")
else:
    print("""
⚠ Some issues were found:
""")
    if missing_required:
        print(f"  • Missing packages: {', '.join(missing_required)}")
        print(f"    Fix: pip install {' '.join(missing_required)} --user")
    if not modules_ok:
        print("  • Some project modules failed to import")
        print("    Fix: Check that working directory is set to project root")
    print()

print("=" * 70)
