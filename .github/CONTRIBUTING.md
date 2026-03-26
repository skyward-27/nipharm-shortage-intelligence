# Contributing to Nipharma Tech Stock Intelligence Unit

This is a private commercial project. These guidelines apply to internal contributors only.

---

## Development Workflow

### Branching

- `main` — production branch, auto-deploys to Streamlit Cloud
- `dev` — integration branch for testing before merge to main
- Feature branches: `feature/<description>` (e.g., `feature/script-21-substitution`)
- Bugfix branches: `fix/<description>` (e.g., `fix/tariff-scraper-timeout`)

### Commit Message Convention

Follow conventional commits:

```
feat: add Script 21 therapeutic substitution cascade predictor
fix: handle CPE scraper timeout when monthly page is not yet live
docs: update README with March 2026 risk molecules
data: refresh concessions archive through March 2026
model: retrain RF v6 with full 27-feature set
```

### Pull Requests

- All changes to `main` must go through a PR
- PRs require at least one review before merging
- Include a short description of what changed and why
- Reference any relevant issue numbers

---

## Data Files

**Never commit data files to this repository.** The `scrapers/data/` directory is gitignored.

This includes:
- Any `.csv` files produced by scrapers
- Any `.pkl` or `.joblib` model files
- Any invoice or purchase price data
- Any files containing pharmacy-specific information

If you need to share a dataset for review, use a private channel — not a git commit.

---

## Adding a New Scraper

1. Create `scrapers/NN_descriptive_name.py` (use the next available number)
2. Follow the existing pattern:
   - Output a CSV to `scrapers/data/<subfolder>/`
   - Print a summary line on completion: `print(f"[NN] Saved {n} rows to data/...")`
   - Handle timeouts and HTTP errors gracefully with a fallback or informative error
3. Register it in `scrapers/00_run_all_scrapers.py`
4. Document it in the Data Sources table in `scrapers/README.md`
5. Add any new features it produces to the feature engineering notes in `11_feature_store_panel.py`

---

## Secrets and API Keys

- Never hardcode API keys in source files
- Always use environment variables (see `README.md` for the full list)
- The `.env` file is gitignored — use it locally, never commit it

---

## Sensitive Data Policy

- No patient data, ever
- No prescription-level data (aggregate BNF-code level only)
- No PII of any kind
- Invoice/purchase price data: gitignored, share only via secure internal channels

---

## Contact

For access, questions, or licensing: contact the project maintainer.
