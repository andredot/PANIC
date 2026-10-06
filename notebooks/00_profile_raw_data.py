# -*- coding: utf-8 -*-
"""
00_profile_raw_data.py
======================

Read-only structural profile of the real raw extracts in data/raw/.

Answers the open [CONFIRM] items from the audit without exporting any
patient-level data:
  - exact column headers, separator and encoding of each file
  - ED: esito codebook, ICD coding system per year, T-code length / intent
    distribution, monthly completeness (is 2025 a full year?)
  - FUR: DDD column name, date range, monthly completeness, ATC N05/N06 volume
  - cod_sindromi_mental.txt: first lines (code list, no patient data)

Output: printed to console AND written to outputs/profile/raw_profile.txt.
Only aggregate counts are reported; cells below SMALL_CELL are suppressed,
so the output file can be shared outside the VDI.

Requires polars (files are ~1 GB each).
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import polars as pl

from config import DATA_DIR, OUTPUT_DIR

# =============================================================================
# SETTINGS
# =============================================================================

ED_FILE = DATA_DIR / "PS2017_2025.csv"
ED_SMALL_FILE = DATA_DIR / "ed_presentations.csv"
FUR_FILES = sorted(DATA_DIR.glob("FUR_*.csv"))
MENTAL_CODES_FILE = DATA_DIR / "cod_sindromi_mental.txt"

SMALL_CELL = 10          # suppress counts below this
TOP_N = 40               # rows shown for value tables

OUT_DIR = OUTPUT_DIR / "profile"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "raw_profile.txt"

_lines: list[str] = []


def out(text: str = "") -> None:
    print(text)
    _lines.append(text)


def section(title: str) -> None:
    out("\n" + "=" * 78)
    out(title)
    out("=" * 78)


def suppress(df: pl.DataFrame, col: str = "n") -> pl.DataFrame:
    return df.with_columns(
        pl.when(pl.col(col) < SMALL_CELL).then(None).otherwise(pl.col(col)).alias(col)
    )


def show(df: pl.DataFrame, n: int = TOP_N) -> None:
    with pl.Config(tbl_rows=n, tbl_cols=20, fmt_str_lengths=60, tbl_width_chars=160):
        out(str(df.head(n)))


# =============================================================================
# FILE SNIFFING
# =============================================================================

def sniff(path: Path) -> dict:
    """Detect encoding and separator from the first line."""
    raw = path.open("rb").read(64_000)
    encoding = "utf8"
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        encoding = "latin1"
    if raw.startswith(b"\xef\xbb\xbf"):
        encoding = "utf8 (with BOM)"
    first = raw.split(b"\n", 1)[0].decode("utf-8" if encoding.startswith("utf8") else "latin-1")
    first = first.lstrip("﻿")
    sep = max([";", ",", "\t", "|"], key=first.count)
    return {"encoding": encoding, "sep": sep, "header": first.rstrip("\r").split(sep)}


def scan(path: Path, info: dict) -> pl.LazyFrame:
    return pl.scan_csv(
        path,
        separator=info["sep"],
        encoding="utf8-lossy",
        infer_schema=False,       # everything as string: we only profile
        quote_char='"',
        truncate_ragged_lines=True,
    )


def describe_file(path: Path) -> dict:
    info = sniff(path)
    out(f"\nFile: {path.name}  ({path.stat().st_size / 1e6:,.0f} MB)")
    out(f"  encoding: {info['encoding']}   separator: {info['sep']!r}")
    out(f"  {len(info['header'])} columns:")
    for c in info["header"]:
        out(f"    - {c!r}")
    return info


def missing_profile(lf: pl.LazyFrame, cols: list[str]) -> None:
    markers = ["", "_", "?", "-", "DATO NON APPLICABILE", "NON APPLICABILE", "DATO MANCANTE"]
    exprs = [pl.len().alias("__rows")]
    for c in cols:
        v = pl.col(c).str.strip_chars()
        exprs.append((v.is_null() | v.is_in(markers)).sum().alias(c))
    res = lf.select(exprs).collect(engine="streaming").row(0, named=True)
    rows = res.pop("__rows")
    out(f"  rows: {rows:,}")
    out("  missing / marker share per column:")
    for c, n in res.items():
        out(f"    {c:<45} {100 * n / max(rows, 1):6.2f}%")


def find_col(cols: list[str], *needles: str) -> str | None:
    for c in cols:
        if all(n.lower() in c.lower() for n in needles):
            return c
    return None


# =============================================================================
# ED PROFILE
# =============================================================================

def profile_ed(path: Path) -> None:
    section(f"ED DATA: {path.name}")
    info = describe_file(path)
    lf = scan(path, info)
    cols = lf.collect_schema().names()
    missing_profile(lf, cols)

    ym = find_col(cols, "annomese") or find_col(cols, "anno")
    dx1 = next((c for c in cols if "cod diagnosi" in c.lower() and "second" not in c.lower()), None)
    dx2 = next((c for c in cols if "cod diagnosi" in c.lower() and "second" in c.lower()), None)
    esito = find_col(cols, "codice esito")
    esito_d = find_col(cols, "descrizione esito")
    pid = find_col(cols, "microbio")
    out(f"\n  detected: year_month={ym!r} dx1={dx1!r} dx2={dx2!r} esito={esito!r} patient={pid!r}")

    # Monthly completeness
    if ym:
        out("\n  Presentations per month (all diagnoses) - check for gaps / partial 2025:")
        monthly = (
            lf.group_by(pl.col(ym).str.slice(0, 6).alias("year_month"))
            .agg(pl.len().alias("n"))
            .sort("year_month")
            .collect(engine="streaming")
        )
        show(suppress(monthly), n=200)

    # Esito codebook
    if esito:
        out("\n  Esito codebook (code x description):")
        keys = [esito] + ([esito_d] if esito_d else [])
        tab = lf.group_by(keys).agg(pl.len().alias("n")).sort("n", descending=True).collect(engine="streaming")
        show(suppress(tab))

    # Diagnosis coding system per year
    for dx in [d for d in (dx1, dx2) if d]:
        out(f"\n  Diagnosis column {dx!r}:")
        code = pl.col(dx).str.replace_all(r"[.\s]", "").str.to_uppercase()
        icd10_poison = code.str.contains(r"^T(3[6-9]|4[0-9]|50)")
        icd9_poison = code.str.contains(r"^9(6[0-9]|7[0-9])")
        icd10_any = code.str.contains(r"^[A-Z]\d")
        icd9_any = code.str.contains(r"^(\d{3}|V\d{2}|E\d{3})")
        yr = pl.col(ym).str.slice(0, 4) if ym else pl.lit("all")
        by_year = (
            lf.group_by(yr.alias("year"))
            .agg(
                pl.len().alias("rows"),
                icd10_any.sum().alias("icd10_like"),
                icd9_any.sum().alias("icd9_like"),
                icd10_poison.sum().alias("T36_T50"),
                icd9_poison.sum().alias("960_979"),
                code.str.contains(r"^F").sum().alias("F_codes"),
            )
            .sort("year")
            .collect(engine="streaming")
        )
        show(by_year, n=20)

        out("\n  Length of T36-T50 codes (after removing dots) - 7 = full ICD-10-CM:")
        lens = (
            lf.filter(icd10_poison)
            .group_by(code.str.len_chars().alias("length"))
            .agg(pl.len().alias("n"))
            .sort("length")
            .collect(engine="streaming")
        )
        show(suppress(lens))

        out("\n  Example T-code shapes (digits->9, letters kept) - format check:")
        shapes = (
            lf.filter(icd10_poison)
            .group_by(code.str.replace_all(r"\d", "9").alias("shape"))
            .agg(pl.len().alias("n"))
            .sort("n", descending=True)
            .collect(engine="streaming")
        )
        show(suppress(shapes), n=15)

        out("\n  T36-T50 by 4-char subcategory (e.g. T424 = benzodiazepines):")
        sub = (
            lf.filter(icd10_poison)
            .group_by(code.str.slice(0, 4).alias("subcat"))
            .agg(pl.len().alias("n"))
            .sort("n", descending=True)
            .collect(engine="streaming")
        )
        show(suppress(sub), n=80)

        out("\n  Intent character (6th char of 7-char ICD-10-CM T-codes; 1-6):")
        intent = (
            lf.filter(icd10_poison & (code.str.len_chars() >= 6))
            .group_by(code.str.slice(5, 1).alias("intent_char"))
            .agg(pl.len().alias("n"))
            .sort("intent_char")
            .collect(engine="streaming")
        )
        show(suppress(intent))

        out("\n  960-979 codes (if any) by 4-char prefix:")
        sub9 = (
            lf.filter(icd9_poison)
            .group_by(code.str.slice(0, 4).alias("prefix"))
            .agg(pl.len().alias("n"))
            .sort("n", descending=True)
            .collect(engine="streaming")
        )
        show(suppress(sub9), n=40)

    # Repeat presentations
    if pid:
        res = lf.select(
            pl.len().alias("rows"), pl.col(pid).n_unique().alias("patients")
        ).collect(engine="streaming")
        out(f"\n  rows vs distinct patients: {res.row(0)}")


# =============================================================================
# FUR PROFILE
# =============================================================================

def profile_fur(path: Path) -> None:
    section(f"FUR DATA: {path.name}")
    info = describe_file(path)
    lf = scan(path, info)
    cols = lf.collect_schema().names()
    missing_profile(lf, cols)

    ddd_candidates = [c for c in cols if "ddd" in c.lower() or "dose" in c.lower()]
    out(f"\n  DDD-like columns: {ddd_candidates or 'NONE FOUND'}")
    for c in ddd_candidates:
        sample = (
            lf.select(pl.col(c).str.strip_chars())
            .filter(pl.col(c).is_not_null())
            .group_by(pl.col(c).str.replace_all(r"\d", "9").alias("shape"))
            .agg(pl.len().alias("n"))
            .sort("n", descending=True)
            .collect(engine="streaming")
        )
        out(f"  value shapes of {c!r} (decimal separator check):")
        show(suppress(sample), n=10)

    date_col = find_col(cols, "erogazione") or find_col(cols, "data")
    if date_col:
        out(f"\n  Dispensations per month by {date_col!r}:")
        monthly = (
            lf.group_by(pl.col(date_col).str.slice(0, 7).alias("year_month"))
            .agg(pl.len().alias("n"))
            .sort("year_month")
            .collect(engine="streaming")
        )
        show(suppress(monthly), n=40)

    atc = find_col(cols, "cod atc")
    if atc:
        out("\n  ATC length distribution:")
        show(suppress(
            lf.group_by(pl.col(atc).str.len_chars().alias("len")).agg(pl.len().alias("n"))
            .sort("len").collect(engine="streaming")
        ))
        out("\n  N05/N06/N02A/N07B volume by 5-char ATC:")
        show(suppress(
            lf.filter(pl.col(atc).str.contains(r"^(N05|N06|N02A|N07B)"))
            .group_by(pl.col(atc).str.slice(0, 5).alias("atc5"))
            .agg(pl.len().alias("n"))
            .sort("n", descending=True)
            .collect(engine="streaming")
        ), n=40)

    for c in [find_col(cols, "tipo medico"), find_col(cols, "sesso")]:
        if c:
            out(f"\n  Values of {c!r}:")
            show(suppress(
                lf.group_by(c).agg(pl.len().alias("n")).sort("n", descending=True)
                .collect(engine="streaming")
            ), n=20)


# =============================================================================
# MAIN
# =============================================================================

section("RAW DATA PROFILE")
out(f"Data directory: {DATA_DIR}")
for f in sorted(DATA_DIR.iterdir()):
    out(f"  {f.name:<30} {f.stat().st_size / 1e6:>10,.1f} MB")

if MENTAL_CODES_FILE.exists():
    section(f"LOOKUP: {MENTAL_CODES_FILE.name}")
    text = MENTAL_CODES_FILE.read_bytes().decode("utf-8", errors="replace").splitlines()
    out(f"  {len(text)} lines; first 40:")
    for line in text[:40]:
        out(f"    {line}")

for f in (ED_FILE, ED_SMALL_FILE):
    if f.exists():
        profile_ed(f)

for f in FUR_FILES:
    profile_fur(f)

OUT_FILE.write_text("\n".join(_lines), encoding="utf-8")
print(f"\nSaved profile to: {OUT_FILE}")
