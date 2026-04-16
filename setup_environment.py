# -*- coding: utf-8 -*-
"""
Setup script for the PANIC (Drug Intoxication Analysis) project.

Run this script FIRST after opening the project in Spyder to:
1. Install all required packages
2. Verify the installation
3. Set up the Python path

Instructions:
1. Open this file in Spyder
2. Press F5 (or click Run) to execute
3. Follow any prompts in the console
"""

import subprocess
import sys
from pathlib import Path


# =============================================================================
# PACKAGE DEFINITIONS
# =============================================================================

# Core packages - required for basic functionality
CORE_PACKAGES = [
    ("pandas", "DataFrame operations, CSV I/O", True),
    ("numpy", "Numerical computing", True),
    ("matplotlib", "Visualisations", True),
    ("scipy", "Statistical tests", True),
]

# Optional packages - enhanced features, pipeline works without them
OPTIONAL_PACKAGES = [
    ("polars", "Fast processing of large files (1GB+)", False),
    ("seaborn", "Enhanced statistical visualisations", False),
    ("statsmodels", "Segmented regression / ITS", False),
]

# Validation packages - recommended but not blocking
VALIDATION_PACKAGES = [
    ("pandera", "DataFrame schema validation", False),
    ("pydantic", "Data validation", False),
    ("pytest", "Testing framework", False),
]


# =============================================================================
# INSTALLATION FUNCTIONS
# =============================================================================

def get_pip_command():
    """Get the appropriate pip command for this environment."""
    pip_args = [sys.executable, "-m", "pip", "install", "--quiet"]
    
    # Check if we're in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if not in_venv:
        pip_args.append("--user")
    
    return pip_args, not in_venv


def install_package(package_name: str, pip_args: list) -> bool:
    """Install a single package. Returns True if successful."""
    try:
        result = subprocess.run(
            pip_args + [package_name],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return True
        
        # Try with --break-system-packages for newer pip
        result2 = subprocess.run(
            pip_args + ["--break-system-packages", package_name],
            capture_output=True,
            text=True
        )
        return result2.returncode == 0
        
    except Exception:
        return False


def install_packages():
    """Install all packages."""
    
    print("=" * 60)
    print("INSTALLING PACKAGES")
    print("=" * 60)
    
    pip_args, using_user = get_pip_command()
    
    if using_user:
        print("\nNote: Installing with --user flag (not in virtual environment)")
    print()
    
    failed_required = []
    
    # Install core packages (required)
    print("Core packages (required):")
    print("-" * 40)
    for package, description, required in CORE_PACKAGES:
        print(f"  {package:15} - {description}...", end=" ", flush=True)
        if install_package(package, pip_args):
            print("OK")
        else:
            print("FAILED")
            if required:
                failed_required.append(package)
    
    print()
    
    # Install optional packages
    print("Optional packages (enhanced features):")
    print("-" * 40)
    for package, description, _ in OPTIONAL_PACKAGES:
        print(f"  {package:15} - {description}...", end=" ", flush=True)
        if install_package(package, pip_args):
            print("OK")
        else:
            print("skipped")
    
    print()
    
    # Install validation packages
    print("Validation packages (recommended):")
    print("-" * 40)
    for package, description, _ in VALIDATION_PACKAGES:
        print(f"  {package:15} - {description}...", end=" ", flush=True)
        if install_package(package, pip_args):
            print("OK")
        else:
            print("skipped")
    
    print()
    
    return len(failed_required) == 0


def verify_installation():
    """Verify that packages can be imported."""
    
    print("=" * 60)
    print("VERIFYING INSTALLATION")
    print("=" * 60)
    print()
    
    packages_to_check = [
        # (import_name, display_name, required, fallback_msg)
        ("pandas", "pandas", True, None),
        ("numpy", "numpy", True, None),
        ("matplotlib.pyplot", "matplotlib", True, None),
        ("scipy", "scipy", True, None),
        ("polars", "polars", False, "Will use pandas for pharma processing"),
        ("seaborn", "seaborn", False, "Will use basic matplotlib"),
        ("statsmodels", "statsmodels", False, "Segmented regression unavailable"),
        ("pandera", "pandera", False, "Schema validation unavailable"),
        ("pydantic", "pydantic", False, "Data validation unavailable"),
        ("pytest", "pytest", False, "Testing unavailable"),
    ]
    
    all_required_ok = True
    
    print("Package               Version      Status")
    print("-" * 55)
    
    for import_name, display_name, required, fallback in packages_to_check:
        try:
            if "." in import_name:
                main_pkg = import_name.split(".")[0]
            else:
                main_pkg = import_name
            
            mod = __import__(main_pkg)
            version = getattr(mod, "__version__", "?")
            
            marker = "*" if required else " "
            print(f"  {display_name:18} {version:12} OK {marker}")
            
        except ImportError:
            marker = "*" if required else " "
            if required:
                print(f"  {display_name:18} {'--':12} MISSING {marker}")
                all_required_ok = False
            else:
                print(f"  {display_name:18} {'--':12} not installed")
                if fallback:
                    print(f"      -> {fallback}")
    
    print()
    print("  * = required package")
    print()
    
    return all_required_ok


def setup_python_path():
    """Add the project root to Python path."""
    
    print("=" * 60)
    print("SETTING UP PYTHON PATH")
    print("=" * 60)
    print()
    
    project_root = Path(__file__).parent.resolve()
    
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        print(f"  Added to Python path: {project_root}")
    else:
        print(f"  Already in path: {project_root}")
    
    print()
    print("To make this permanent in Spyder:")
    print("  1. Go to: Tools -> PYTHONPATH manager")
    print(f"  2. Add: {project_root}")
    print()


def test_project_imports():
    """Test that project modules can be imported."""
    
    print("=" * 60)
    print("TESTING PROJECT IMPORTS")
    print("=" * 60)
    print()
    
    project_root = Path(__file__).parent.resolve()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    tests = [
        ("intox_analysis.data.schemas", "ICD code classification", True),
        ("intox_analysis.data.pharmaceutical", "Pharmaceutical processing", True),
        ("intox_analysis.data.generators", "Synthetic data generation", True),
        ("intox_analysis.data.residence", "Urban/rural classification", False),
        ("intox_analysis.analysis.trends", "Trend analysis", True),
    ]
    
    all_required_ok = True
    for module_name, description, required in tests:
        try:
            __import__(module_name)
            print(f"  + {description}")
        except ImportError as e:
            if required:
                print(f"  x {description}: {e}")
                all_required_ok = False
            else:
                print(f"  - {description} (optional, not loaded)")
    
    print()
    return all_required_ok


def print_summary(success: bool):
    """Print summary and next steps."""
    
    print("=" * 60)
    if success:
        print("SETUP COMPLETE")
    else:
        print("SETUP COMPLETED WITH WARNINGS")
    print("=" * 60)
    print("""
Libraries:
  Required:  pandas, numpy, matplotlib, scipy
  Optional:  polars (fast files), statsmodels (regression), seaborn (plots)
  Validation: pandera, pydantic, pytest

Pipeline scripts (run in order):
  00_verify_setup.py           - Check installation
  01_load_ed_data.py           - Load ED data
  02_load_pharma_data.py       - Load pharmaceutical data
  05_intoxication_trends.py    - Drug class trends
  06_stratified_analysis.py    - Demographics
  07_prescription_linkage.py   - Pharma linkage
  08_generate_report.py        - HTML report

Data folders:
  data/raw/      <- Place your VDI CSV exports here
  data/lookups/  <- Optional lookup tables
  outputs/       <- Generated figures, tables, reports

Configuration:
  config.py      <- ALL study parameters (change here, propagates everywhere)
""")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print()
    print("+" + "=" * 58 + "+")
    print("|     PANIC - Drug Intoxication Analysis Setup Wizard      |")
    print("+" + "=" * 58 + "+")
    print()
    
    install_success = install_packages()
    verify_success = verify_installation()
    
    if verify_success:
        setup_python_path()
        imports_success = test_project_imports()
        print_summary(install_success and imports_success)
    else:
        print("\n! Some required packages are missing.")
        print("  Try installing them manually with:")
        print("    pip install pandas numpy matplotlib scipy --user")
