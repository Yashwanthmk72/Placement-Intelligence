# Placement Intelligence

A local-first student placement prediction and career readiness website built from the uploaded Colab prototype. It keeps the original placement and salary Random Forest approach, adds a reviewable resume-to-profile workflow, persistent SQLite history, a local file library, dataset replacement/retraining, PDF reports, dark/light themes, and animated navigation.

## Run on Windows

1. Extract the ZIP file into a normal folder.
2. Install **Python 3.10 or newer** if it is not already installed.
3. Double-click `start.bat`.
4. The first run creates `.venv`, installs the packages in `requirements.txt`, trains the models from the two included datasets, and opens `http://127.0.0.1:8000`.
5. Keep the terminal window open while using the website. Close it to stop the local server.

PowerShell alternative:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\start.ps1
```

Manual start:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000` in your browser.

## Features

- **Overview:** saved analysis counts, recent predictions, a probability trend chart, and held-out model evaluation metrics.
- **Work with a profile:** upload a resume, extract supported fields, review/edit the values, and run the placement and indicative salary models. You can also enter a profile manually without uploading a resume.
- **History:** saved analyses, record details, search, PDF report downloads, and CSV/JSON exports.
- **Settings:** profile display name, dark/light theme, upload-size limit, original-file retention, dataset updates, and file library management.
- **File library:** store files of any type as local attachments. The app does not execute stored files. Automatic resume extraction supports PDF, DOCX, TXT, MD, RTF, common images, CSV, Excel, JSON, and HTML. Image OCR may require a local Tesseract OCR installation.
- **Dataset updates:** placement and salary datasets can be replaced independently with CSV/Excel files. The app validates the schema and retrains both models; a failed retraining restores the previous dataset file.
- **Storage:** analysis records live in `data/placement_history.sqlite3`; uploads are in `data/uploads/`; generated PDF reports are in `data/reports/`; training datasets are in `data/datasets/`.

## Dataset schema

Both datasets require these feature columns:

- `CGPA`
- `Major Projects`
- `Workshops/Certificatios` (the source dataset's spelling is accepted; `Workshops/Certifications` is also accepted)
- `Mini Projects`
- `Skills`
- `Communication Skill Rating`
- `Internship`
- `Hackathon`
- `12th Percentage`
- `10th Percentage`
- `backlogs`

The placement dataset also requires `PlacementStatus` with both placed and not-placed examples. The salary dataset requires `PlacementStatus` and `salary`; salary training only uses placed rows with salary greater than zero.

## Understanding the estimates

The placement percentage is the Random Forest model's estimated probability for the `Placed` class. It is **not necessarily calibrated** and it is not a guaranteed real-world chance. The displayed accuracy, precision, recall, and F1 are measured on a held-out split from the local training dataset, not on an independent college-wide or future placement cohort. Salary is an indicative estimate trained on placed students only. The resume readiness score is a transparent rules-based checklist, not a recruiter score.

Resume extraction is best-effort. Please verify academic scores, project counts, experience flags, and other extracted inputs before running the prediction. Fields left blank are median-imputed by the model, and the UI identifies this behavior.

## Privacy and login note

This is designed as a **single-user local workspace**, not a multi-user hosted service. The welcome screen stores a display name, but it is not password authentication. Keep the server bound to `127.0.0.1` unless you deliberately configure a secure hosted deployment. Do not expose it directly to the public internet without adding authentication, HTTPS, access controls, and appropriate privacy safeguards.

The dashboard links to the official AICTE National Internship Portal and the NIRF Engineering Rankings. Listings and ranking data are not imported into the prediction model; this project does not claim to use live market or hiring feeds.

## Legacy version

The original Google Colab/Gradio script is preserved at `legacy/original_colab_app.py`. The sample resume supplied in the ZIP is retained under `samples/` for local testing only.

## New in this version: Aurora UI + World Globe

- **Aurora neon-glass redesign** (`app/static/aurora.css`, `fx.js`): animated gradient mesh, starfield, intro splash on every load, cursor spotlight, shimmer buttons, staggered entrances, confetti on strong results. Dark and light themes both work; `prefers-reduced-motion` is respected.
- **Globe · Base price** view: drag/zoom a 3D globe (d3-geo, bundled in `static/vendor/`), click a country or glowing pin to see your estimated base price, tax/living costs, visa route, in-demand skills (green = you have it) and watch-outs. Also: what-if simulator, best-fit ranking with weights, compare up to 3 countries.
- **How the price is computed** (`app/world.py`): your predicted salary is ranked among out-of-bag predictions on the training data (a percentile), then mapped onto each country's low/typical/high entry-level benchmark.
- **IMPORTANT:** the benchmark table in `world.py` is indicative, compiled without live source verification (the automated research step did not complete). Visa rules and thresholds change often. Edit `COUNTRIES`, and verify on official sites before relying on any number. Exchange rates are from 2026-11-12 (x-rates.com) and are static.
- The world-map outlines load from the jsDelivr CDN (`world-atlas@2`) in your browser; offline, the pins still work.
- New endpoints: `GET /api/countries`, `POST /api/world/estimate`.

## v3 additions
- Fonts (Syne, Space Grotesk, Inter, Sora, JetBrains Mono via Google Fonts), neon-glass backdrop, neon glow + grow on hover, larger text, illustrations in `static/img/`.
- **ATS & keyword check** (Work with a profile): `POST /api/ats`, role keyword lists in `engine.py` (`ROLE_KEYWORDS`).
- **Result card**: PNG download from the result panel or the globe toolbar.
- **Live exchange rates**: `world.refresh_fx()` pulls rates from open.er-api.com (cached 6 h); falls back to the static 2026-11-12 table if offline.
- Country pay/visa figures are still indicative and unsourced; see the note above.

## v5: trust, tests, access
- Visa figures for the UK, Germany and Singapore were checked against official pages on 2026-11-15 and show a green "checked" badge; all other countries show an amber "Unverified estimate" badge plus a link to the official immigration site. Pay figures remain indicative benchmarks.
- `tests/test_core.py`: run `python -m pip install pytest` then `python -m pytest -q`.
- Country search box, keyboard-selectable ranking, focus outlines, mobile layout.
