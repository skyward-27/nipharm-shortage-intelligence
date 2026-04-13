"""
31_wire_missing_features.py — Wire BSO NI shortages, FDA warnings, manufacturer count into panel
=================================================================================================
Adds 3 new feature columns to panel_feature_store_train.csv:
  - bso_ni_shortage_flag:  1 if drug appears in BSO NI shortage notices (fuzzy first-word match)
  - fda_warning_flag:      1 if any manufacturer of drug has FDA warning letter
  - manufacturer_count:    number of marketing authorisation holders (lower = higher risk)

Data sources (all in data/mhra/):
  - bso_ni_shortages.csv      (305 rows — NI shortage notices)
  - fda_warning_letters.csv   (10 rows — India/China manufacturer warnings)
  - manufacturer_count.csv    (30 drugs — estimated manufacturer counts)

RUN:
  cd "/Users/chaitanyawarhade/Documents/NPT Stock Inteligance Unit/scrapers"
  python 31_wire_missing_features.py
"""

import pandas as pd
import numpy as np
import re
import os

BASE = "/Users/chaitanyawarhade/Documents/NPT Stock Inteligance Unit/scrapers"
PANEL_PATH = f"{BASE}/data/features/panel_feature_store_train.csv"

BSO_PATH = f"{BASE}/data/mhra/bso_ni_shortages.csv"
FDA_PATH = f"{BASE}/data/mhra/fda_warning_letters.csv"
MFR_PATH = f"{BASE}/data/mhra/manufacturer_count.csv"

print("=" * 70)
print("31 — Wire BSO NI shortages, FDA warnings, manufacturer count into panel")
print("=" * 70)

# ── LOAD PANEL ───────────────────────────────────────────────────────────────
panel = pd.read_csv(PANEL_PATH)
print(f"\nPanel loaded: {panel.shape[0]:,} rows x {panel.shape[1]} cols")
print(f"  Unique drugs: {panel['drug_name'].nunique()}")

# Helper: extract first word (the active substance) from panel drug_name
# e.g. "Metformin 850mg tablets" -> "metformin"
# e.g. "Co-codamol 30mg/500mg capsules" -> "co-codamol"
def extract_first_word(name):
    """Extract first word (active substance) from drug name, lowered."""
    if pd.isna(name):
        return ""
    # Take everything before the first digit or slash
    m = re.match(r'^([A-Za-z][A-Za-z\- ]*?)(?:\s+\d|\s*$)', str(name).strip())
    if m:
        return m.group(1).strip().lower()
    # Fallback: first whitespace-separated token
    return str(name).strip().split()[0].lower()

panel['_substance'] = panel['drug_name'].apply(extract_first_word)

# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE 1: bso_ni_shortage_flag
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'─'*70}")
print("FEATURE 1: bso_ni_shortage_flag")
print(f"{'─'*70}")

bso = pd.read_csv(BSO_PATH)
print(f"  BSO NI data: {len(bso)} rows")

# The BSO data is messy scraped text. Extract drug-like names:
# Look for entries that start with [PDF] or contain known drug patterns
bso_drugs = set()
for name in bso['drug_name'].dropna().unique():
    name_clean = str(name).strip()
    # Remove [PDF] prefix
    name_clean = re.sub(r'^\[PDF\]\s*', '', name_clean)
    # Extract first word if it looks like a drug name (starts with uppercase letter)
    first_word = name_clean.split()[0].lower() if name_clean else ""
    # Skip junk entries (sentences, bullets, etc.)
    if len(first_word) < 3:
        continue
    if first_word.startswith('•') or first_word.startswith('–'):
        continue
    if first_word in ('the', 'and', 'for', 'this', 'consider', 'administer',
                       'recommendations', 'treating', 'porcine'):
        continue
    # If the first word looks like a drug name (not a common English word), add it
    bso_drugs.add(first_word.rstrip(',').rstrip('.'))

# Also try to extract multi-word drug names like "co-codamol", "co-amoxiclav"
for name in bso['drug_name'].dropna().unique():
    name_clean = re.sub(r'^\[PDF\]\s*', '', str(name).strip())
    m = re.match(r'^([A-Za-z][A-Za-z\-]+)', name_clean)
    if m:
        word = m.group(1).lower()
        if len(word) >= 3 and word not in ('the', 'and', 'for', 'this', 'consider',
                                            'administer', 'recommendations', 'treating',
                                            'porcine', 'remaining', 'stock'):
            bso_drugs.add(word)

print(f"  Extracted {len(bso_drugs)} unique drug substances from BSO notices")
print(f"  Examples: {sorted(list(bso_drugs))[:10]}")

# Match against panel substances
panel['bso_ni_shortage_flag'] = panel['_substance'].isin(bso_drugs).astype(int)
matched = panel['bso_ni_shortage_flag'].sum()
matched_drugs = panel.loc[panel['bso_ni_shortage_flag'] == 1, '_substance'].nunique()
print(f"  Panel matches: {matched:,} rows ({matched_drugs} unique drugs)")

# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE 2: fda_warning_flag
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'─'*70}")
print("FEATURE 2: fda_warning_flag")
print(f"{'─'*70}")

fda = pd.read_csv(FDA_PATH)
print(f"  FDA data: {len(fda)} warning letters")

# Build a set of drug substances mentioned in FDA warning letters
fda_substances = set()
for drugs_str in fda['drugs_affected'].dropna():
    # Split on commas, clean each drug name
    for drug in str(drugs_str).split(','):
        drug = drug.strip().lower()
        # Remove suffixes like " API", " formulations"
        drug = re.sub(r'\s+(api|formulations|products|intermediates)$', '', drug)
        # Skip vague entries
        if drug in ('multiple oral generics', 'injectable products',
                     'multiple api intermediates', 'multiple generics including metformin',
                     'multiple generics', 'amlodipine'):
            # For "multiple generics including X, Y" — extract the specific drugs
            pass
        if len(drug) >= 3 and drug not in ('multiple oral generics', 'injectable products',
                                            'multiple api intermediates', 'multiple generics'):
            fda_substances.add(drug.split()[0])  # First word = substance

# Also handle "Multiple generics including metformin, amlodipine"
for drugs_str in fda['drugs_affected'].dropna():
    m = re.search(r'including\s+(.*)', str(drugs_str), re.IGNORECASE)
    if m:
        for drug in m.group(1).split(','):
            word = drug.strip().lower().split()[0]
            if len(word) >= 3:
                fda_substances.add(word)

print(f"  Extracted {len(fda_substances)} unique drug substances from FDA letters")
print(f"  Substances: {sorted(fda_substances)}")

# Match against panel
panel['fda_warning_flag'] = panel['_substance'].apply(
    lambda s: 1 if s in fda_substances else 0
)
matched = panel['fda_warning_flag'].sum()
matched_drugs = panel.loc[panel['fda_warning_flag'] == 1, '_substance'].nunique()
print(f"  Panel matches: {matched:,} rows ({matched_drugs} unique drugs)")

# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE 3: manufacturer_count
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'─'*70}")
print("FEATURE 3: manufacturer_count")
print(f"{'─'*70}")

mfr = pd.read_csv(MFR_PATH)
print(f"  Manufacturer data: {len(mfr)} drugs")

# Build lookup: substance -> manufacturer_count
mfr_lookup = {}
for _, row in mfr.iterrows():
    substance = str(row['active_substance']).strip().lower()
    # Map first word for matching
    first_word = substance.split()[0]
    mfr_lookup[first_word] = int(row['manufacturer_count'])
    # Also store full name for exact matches
    mfr_lookup[substance] = int(row['manufacturer_count'])

print(f"  Lookup keys: {len(mfr_lookup)}")

# Compute median for default
median_count = int(np.median(mfr['manufacturer_count']))
print(f"  Median manufacturer count: {median_count} (used as default for unmatched)")

# Match
panel['manufacturer_count'] = panel['_substance'].map(mfr_lookup).fillna(median_count).astype(int)
matched = (panel['manufacturer_count'] != median_count).sum()
matched_drugs = panel.loc[panel['manufacturer_count'] != median_count, '_substance'].nunique()
print(f"  Exact matches: {matched:,} rows ({matched_drugs} unique drugs)")
print(f"  Defaulted to median: {(panel['manufacturer_count'] == median_count).sum():,} rows")

# ── CLEANUP & SAVE ───────────────────────────────────────────────────────────
panel.drop(columns=['_substance'], inplace=True)

print(f"\n{'='*70}")
print("SAVING UPDATED PANEL")
print(f"{'='*70}")
print(f"  Final shape: {panel.shape[0]:,} rows x {panel.shape[1]} cols")
print(f"  New columns: bso_ni_shortage_flag, fda_warning_flag, manufacturer_count")

# Check for duplicates in column names
if panel.columns.duplicated().any():
    dupes = panel.columns[panel.columns.duplicated()].tolist()
    print(f"  WARNING: Duplicate columns found: {dupes} — dropping duplicates")
    panel = panel.loc[:, ~panel.columns.duplicated(keep='last')]

panel.to_csv(PANEL_PATH, index=False)
print(f"  Saved to: {PANEL_PATH}")

# ── SUMMARY ──────────────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")
print(f"  bso_ni_shortage_flag:  {panel['bso_ni_shortage_flag'].sum():,} positive ({panel['bso_ni_shortage_flag'].mean()*100:.1f}%)")
print(f"  fda_warning_flag:      {panel['fda_warning_flag'].sum():,} positive ({panel['fda_warning_flag'].mean()*100:.1f}%)")
print(f"  manufacturer_count:    min={panel['manufacturer_count'].min()}, median={panel['manufacturer_count'].median():.0f}, max={panel['manufacturer_count'].max()}")
print(f"\nDone. Panel updated in place: {PANEL_PATH}")
