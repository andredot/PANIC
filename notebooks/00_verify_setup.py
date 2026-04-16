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

print("=" * 60)
print("PANIC - SETUP VERIFICATION")
print("=" * 60)
print()

# =============================================================================
# Step 1: Python Version
# =============================================================================
print("1. Python Version")
print(f"   {sys.version.split()[0]}")
print()

# =============================================================================
# Step 2: Add project to path
# =============================================================================
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
print(f"2. Project Root")
print(f"   {project_root}")
print()

# =============================================================================
# Step 3: Check packages
# =============================================================================
print("3. Packages")
print("-" * 40)

packages = {
    # (name, import_name, required)
    "pandas": ("pandas", True),
    "numpy": ("numpy", True),
    "matplotlib": ("matplotlib.pyplot", True),
    "scipy": ("scipy", True),
    "polars": ("polars", False),
    "seaborn": ("seaborn", False),
    "statsmodels": ("statsmodels", False),
    "pandera": ("pandera", False),
    "pydantic": ("pydantic", False),
    "pytest": ("pytest", False),
}

missing_required = []
available_optional = []

for name, (import_name, required) in packages.items():
    try:
        mod = __import__(import_name.split(".")[0])
        version = getattr(mod, "__version__", "?")
        marker = "*" if required else " "
        print(f"   [OK] {name:15} v{version:10} {marker}")
        if not required:
            available_optional.append(name)
    except ImportError:
        marker = "*" if required else " "
        if required:
            print(f"   [!!] {name:15} MISSING      {marker}")
            missing_required.append(name)
        else:
            print(f"   [--] {name:15} not installed")

print()
print("   * = required")
print()

# =============================================================================
# Step 4: Check project modules
# =============================================================================
print("4. Project Modules")
print("-" * 40)

modules = [
    ("intox_analysis.data.schemas", "ICD code classification", True),
    ("intox_analysis.data.pharmaceutical", "Pharmaceutical processing", True),
    ("intox_analysis.data.generators", "Synthetic data generation", True),
    ("intox_analysis.data.residence", "Urban/rural (optional)", False),
    ("intox_analysis.analysis.trends", "Trend analysis", True),
]

modules_ok = True
for module_name, description, required in modules:
    try:
        __import__(module_name)
        print(f"   [OK] {description}")
    except ImportError as e:
        if required:
            print(f"   [!!] {description}: {e}")
            modules_ok = False
        else:
            print(f"   [--] {description}")

print()

# =============================================================================
# Step 5: Check config imports
# =============================================================================
print("5. Configuration")
print("-" * 40)

try:
    from config import (
        PROJECT_DIR, DATA_DIR, OUTPUT_DIR,
        STUDY_PERIOD, PRIMARY_DRUG_CLASSES,
        ICD10_INTOX_PREFIXES
    )
    print(f"   [OK] config.py loaded")
    print(f"        Study period: {STUDY_PERIOD[0]}-{STUDY_PERIOD[1]}")
    print(f"        Drug classes: {len(PRIMARY_DRUG_CLASSES)}")
    print(f"        ICD-10 prefixes: {len(ICD10_INTOX_PREFIXES)}")
except ImportError as e:
    print(f"   [!!] config.py failed: {e}")
    modules_ok = False

print()

# =============================================================================
# Step 6: Check directories
# =============================================================================
print("6. Directories")
print("-" * 40)

dirs = [
    ("data/raw", "VDI data"),
    ("data/lookups", "Lookup tables"),
    ("data/processed", "Intermediate"),
    ("outputs/figures", "Charts"),
    ("outputs/tables", "Tables"),
]

for rel_path, description in dirs:
    full_path = project_root / rel_path
    if full_path.exists():
        print(f"   [OK] {rel_path:20}")
    else:
        print(f"   [--] {rel_path:20} (creating...)")
        full_path.mkdir(parents=True, exist_ok=True)

print()

# =============================================================================
# Step 7: Quick function test
# =============================================================================
print("7. Function Tests")
print("-" * 40)

# Test ICD classification
try:
    from intox_analysis.data.schemas import classify_drug_intoxication
    result = classify_drug_intoxication("T424X2A")
    if result["is_intoxication"] and result["drug_class"] == "benzodiazepine":
        print("   [OK] ICD-10: T424X2A -> benzodiazepine")
    else:
        print(f"   [!!] ICD-10 unexpected: {result}")
except Exception as e:
    print(f"   [!!] ICD classification: {e}")

# Test ATC classification
try:
    from intox_analysis.data.pharmaceutical import classify_atc_code
    result = classify_atc_code("N05BA12")
    if result["drug_class"] == "benzodiazepine":
        print("   [OK] ATC: N05BA12 -> benzodiazepine")
    else:
        print(f"   [!!] ATC unexpected: {result}")
except Exception as e:
    print(f"   [!!] ATC classification: {e}")

print()

# =============================================================================
# Summary
# =============================================================================
print("=" * 60)
print("SUMMARY")
print("=" * 60)

all_ok = len(missing_required) == 0 and modules_ok

if all_ok:
    print("""
[OK] Setup is complete! Your environment is ready.

Available features:""")
    
    if "polars" in available_optional:
        print("  + Fast pharmaceutical processing (polars)")
    else:
        print("  - Fast processing unavailable (using pandas)")
    
    if "statsmodels" in available_optional:
        print("  + Segmented regression (statsmodels)")
    else:
        print("  - Segmented regression unavailable")
    
    if "seaborn" in available_optional:
        print("  + Enhanced plots (seaborn)")
    
    print("""
Next steps:
  1. Run 01_load_ed_data.py to load/generate ED data
  2. Run 02_load_pharma_data.py to load pharmaceutical data
  3. Run 05_intoxication_trends.py for trend analysis
""")
else:
    print("""
[!!] Some issues found:
""")
    if missing_required:
        print(f"  Missing packages: {', '.join(missing_required)}")
        print(f"  Fix: pip install {' '.join(missing_required)} --user")
    if not modules_ok:
        print("  Some project modules failed to import")
        print("  Fix: Ensure working directory is project root")

print("=" * 60)
