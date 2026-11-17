from __future__ import annotations

import csv
import html
from contextlib import contextmanager
import io
import json
import logging
import mimetypes
import os
import re
import shutil
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import world
from .engine import (
    FEATURES,
    analyze_resume_text,
    ats_check,
    ROLE_KEYWORDS,
    calculate_resume_score,
    extract_text_from_file,
    generate_roadmap,
    recommend_projects,
    recommend_skills,
    train_models,
    validate_dataset,
    normalize_dataset,
    predict_profile,
)

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DATASET_DIR = DATA_DIR / "datasets"
UPLOAD_DIR = DATA_DIR / "uploads"
REPORT_DIR = DATA_DIR / "reports"
DB_PATH = DATA_DIR / "placement_history.sqlite3"
STATIC_DIR = Path(__file__).resolve().parent / "static"
PLACEMENT_DATASET = DATASET_DIR / "Placement_Prediction_data.csv"
SALARY_DATASET = DATASET_DIR / "Salary_prediction_data.csv"

for directory in (DATASET_DIR, UPLOAD_DIR, REPORT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("placement-intelligence")

DEFAULT_SETTINGS: dict[str, Any] = {
    "display_name": "Student",
    "theme": "dark",
    "max_upload_mb": 50,
    "currency": "INR",
    "store_original_files": True,
}

models: dict[str, Any] | None = None
model_lock = threading.RLock()

app = FastAPI(title="Placement Intelligence", version="2.0.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                candidate_name TEXT NOT NULL,
                file_name TEXT,
                upload_id INTEGER,
                prediction TEXT NOT NULL,
                probability REAL NOT NULL,
                salary REAL NOT NULL,
                resume_score INTEGER NOT NULL,
                profile_json TEXT NOT NULL,
                recommendations_json TEXT NOT NULL,
                report_name TEXT,
                model_metrics_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                content_type TEXT,
                size_bytes INTEGER NOT NULL,
                uploaded_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)",
                (key, json.dumps(value)),
            )


def load_settings() -> dict[str, Any]:
    settings = DEFAULT_SETTINGS.copy()
    with get_db() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    for row in rows:
        try:
            settings[row["key"]] = json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            pass
    return settings


def save_settings(changes: dict[str, Any]) -> dict[str, Any]:
    current = load_settings()
    for key, value in changes.items():
        if key == "display_name":
            value = str(value).strip()[:60] or "Student"
        elif key == "theme":
            if value not in {"dark", "light"}:
                raise HTTPException(400, "Theme must be dark or light.")
        elif key == "max_upload_mb":
            value = max(1, min(200, int(value)))
        elif key == "store_original_files":
            value = bool(value)
        elif key not in DEFAULT_SETTINGS:
            raise HTTPException(400, f"Unknown setting: {key}")
        current[key] = value
    with get_db() as conn:
        for key, value in changes.items():
            conn.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(current[key])),
            )
    return current


def _safe_original_name(name: str | None) -> str:
    raw = Path(name or "uploaded-file").name
    raw = re.sub(r"[\x00-\x1f<>:\"/\\|?*]", "_", raw).strip(" .")
    return raw[:180] or "uploaded-file"


def _save_file_record(
    original_name: str,
    content: bytes,
    content_type: str | None,
    category: str,
) -> dict[str, Any]:
    safe_name = _safe_original_name(original_name)
    ext = Path(safe_name).suffix.lower()[:12]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    destination = UPLOAD_DIR / stored_name
    destination.write_bytes(content)
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO uploads(original_name, stored_name, category, content_type, size_bytes, uploaded_at) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (safe_name, stored_name, category, content_type or "application/octet-stream", len(content), utc_now()),
        )
        file_id = cursor.lastrowid
    return {
        "id": file_id,
        "name": safe_name,
        "category": category,
        "content_type": content_type or "application/octet-stream",
        "size_bytes": len(content),
        "uploaded_at": utc_now(),
    }


def _check_upload_size(content: bytes) -> None:
    maximum = int(load_settings().get("max_upload_mb", 50)) * 1024 * 1024
    if len(content) > maximum:
        raise HTTPException(413, f"File is larger than the configured {maximum // (1024 * 1024)} MB upload limit.")




def get_cohort_snapshot() -> dict[str, Any]:
    try:
        placement_df, _ = validate_dataset(PLACEMENT_DATASET, "placement")
        salary_df, _ = validate_dataset(SALARY_DATASET, "salary")
        statuses = placement_df["PlacementStatus"].astype(str).str.strip().str.lower()
        placed_count = int(statuses.isin({"placed", "yes", "1", "true"}).sum())
        not_placed_count = int(statuses.isin({"notplaced", "not placed", "no", "0", "false"}).sum())
        total = int(placed_count + not_placed_count)
        salary_status = salary_df["PlacementStatus"].astype(str).str.strip().str.lower()
        salary_values = pd.to_numeric(salary_df["salary"], errors="coerce")
        placed_salaries = salary_values[salary_status.isin({"placed", "yes", "1", "true"}) & salary_values.gt(0)]
        return {
            "ready": True,
            "total_students": total,
            "placed_count": placed_count,
            "not_placed_count": not_placed_count,
            "placement_rate": round((placed_count / total) * 100, 2) if total else 0,
            "average_salary": round(float(placed_salaries.mean()), 2) if len(placed_salaries) else 0,
            "median_salary": round(float(placed_salaries.median()), 2) if len(placed_salaries) else 0,
            "salary_records": int(len(placed_salaries)),
            "source": "Local training datasets",
        }
    except Exception as exc:
        return {"ready": False, "message": str(exc)}


def _serialize_history(row: sqlite3.Row, include_detail: bool = False) -> dict[str, Any]:
    item = {
        "id": row["id"],
        "created_at": row["created_at"],
        "candidate_name": row["candidate_name"],
        "file_name": row["file_name"],
        "prediction": row["prediction"],
        "probability": row["probability"],
        "salary": row["salary"],
        "resume_score": row["resume_score"],
        "has_report": bool(row["report_name"]),
    }
    if include_detail:
        item["profile"] = json.loads(row["profile_json"])
        item["recommendations"] = json.loads(row["recommendations_json"])
        item["model_metrics"] = json.loads(row["model_metrics_json"])
    return item


def _current_models() -> dict[str, Any]:
    if models is None:
        raise HTTPException(503, "The prediction models are not ready. Check your dataset files in data/datasets.")
    return models


def _normalise_profile(profile: dict[str, Any]) -> dict[str, Any]:
    result = dict(profile)
    result["name"] = str(result.get("name") or "Candidate").strip()[:100] or "Candidate"
    numeric = {
        "cgpa": (0, 10),
        "major_projects": (0, 100),
        "workshops": (0, 100),
        "mini_projects": (0, 100),
        "skills_count": (0, 20),
        "communication": (0, 5),
        "twelfth": (0, 100),
        "tenth": (0, 100),
        "backlogs": (0, 100),
    }
    for key, (low, high) in numeric.items():
        raw = result.get(key)
        if raw in (None, ""):
            result[key] = None
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise HTTPException(422, f"{key.replace('_', ' ').title()} must be a number or left blank.")
        if value < low or value > high:
            raise HTTPException(422, f"{key.replace('_', ' ').title()} must be between {low} and {high}.")
        result[key] = value
    for key in ("internship", "hackathon"):
        raw = str(result.get(key) or "Unknown").strip().lower()
        result[key] = "Yes" if raw in {"yes", "y", "true", "1"} else "No" if raw in {"no", "n", "false", "0"} else "Unknown"
    skills = result.get("skills") or []
    if not isinstance(skills, list):
        skills = [str(skills)]
    result["skills"] = [str(x)[:50] for x in skills[:40]]
    if result.get("skills_count") is None:
        result["skills_count"] = min(20, len(result["skills"]))
    return result


def _create_pdf_report(
    record_id: int,
    profile: dict[str, Any],
    result: dict[str, Any],
    recommendations: dict[str, Any],
) -> str:
    file_name = f"placement_report_{record_id}_{uuid.uuid4().hex[:6]}.pdf"
    path = REPORT_DIR / file_name
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitleCenter", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#3247a8")))
    styles.add(ParagraphStyle(name="SmallNote", parent=styles["BodyText"], fontSize=8, leading=11, textColor=colors.HexColor("#566174")))
    story: list[Any] = [
        Paragraph("Placement Intelligence — Candidate Report", styles["ReportTitleCenter"]),
        Spacer(1, 5 * mm),
        Paragraph(f"Candidate: {html.escape(str(profile.get('name', 'Candidate')))}", styles["Heading2"]),
        Paragraph(f"Generated: {html.escape(utc_now())}", styles["BodyText"]),
        Spacer(1, 5 * mm),
    ]
    salary = f"₹{result['salary']:,.0f}"
    table_data = [
        ["Measure", "Model result"],
        ["Placement class", str(result["prediction"])],
        ["Model-estimated probability of Placed", f"{result['probability']:.2f}%"],
        ["Indicative salary estimate if placed", salary],
        ["Resume score (heuristic)", f"{result['resume_score']}/100"],
    ]
    table = Table(table_data, colWidths=[76 * mm, 92 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#26345b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#ccd3df")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f6fb")]),
    ]))
    story += [table, Spacer(1, 6 * mm), Paragraph("Profile inputs", styles["Heading2"])]
    profile_rows = [
        ["CGPA", profile.get("cgpa")], ["Major projects", profile.get("major_projects")],
        ["Certifications / workshops", profile.get("workshops")], ["Mini projects", profile.get("mini_projects")],
        ["Detected / entered skills", ", ".join(profile.get("skills", [])) or "Not provided"],
        ["Internship", profile.get("internship")], ["Hackathon", profile.get("hackathon")],
        ["12th percentage", profile.get("twelfth")], ["10th percentage", profile.get("tenth")],
        ["Backlogs", profile.get("backlogs")], ["Communication rating", profile.get("communication")],
    ]
    ptable = Table([[str(k), str(v if v is not None else "Not provided")] for k, v in profile_rows], colWidths=[76 * mm, 92 * mm])
    ptable.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d7dce5")), ("PADDING", (0, 0), (-1, -1), 6)]))
    story += [ptable, Spacer(1, 5 * mm), Paragraph("Recommended skill focus", styles["Heading2"])]
    for skill in recommendations["missing_skills"]:
        story.append(Paragraph(f"• {html.escape(skill)}", styles["BodyText"]))
    story += [Spacer(1, 4 * mm), Paragraph("Suggested projects", styles["Heading2"])]
    for project in recommendations["projects"]:
        story.append(Paragraph(f"<b>{html.escape(project['name'])}</b> — {html.escape(project['difficulty'])}", styles["BodyText"]))
        story.append(Paragraph(html.escape(project["description"]), styles["SmallNote"]))
    story += [Spacer(1, 5 * mm), Paragraph(
        "Important: this output is an estimate based on the uploaded training data and the entered profile. "
        "The model probability is not guaranteed to be calibrated, placement outcomes depend on many factors, "
        "and the salary estimate is conditional on being placed. The resume score is a rules-based indicator, not a hiring score.",
        styles["SmallNote"],
    )]
    SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm).build(story)
    return file_name


@app.on_event("startup")
def on_startup() -> None:
    global models
    init_db()
    try:
        with model_lock:
            models = train_models(PLACEMENT_DATASET, SALARY_DATASET)
        logger.info("Placement and salary models trained successfully.")
    except Exception:
        logger.exception("Model initialisation failed. App remains available for settings and dataset upload.")


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/api/bootstrap")
def bootstrap() -> dict[str, Any]:
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        placed = conn.execute("SELECT COUNT(*) FROM analyses WHERE lower(prediction)='placed'").fetchone()[0]
        average_probability = conn.execute("SELECT AVG(probability) FROM analyses").fetchone()[0]
        average_salary = conn.execute("SELECT AVG(salary) FROM analyses WHERE salary > 0").fetchone()[0]
        uploads_count = conn.execute("SELECT COUNT(*) FROM uploads").fetchone()[0]
        recent_rows = conn.execute("SELECT * FROM analyses ORDER BY id DESC LIMIT 6").fetchall()
    model_status = None
    if models:
        model_status = {
            "placement": models["placement_metrics"],
            "salary": models["salary_metrics"],
            "features": models["features"],
        }
    return {
        "settings": load_settings(),
        "summary": {
            "analyses": int(count),
            "placed": int(placed),
            "average_probability": round(float(average_probability or 0), 2),
            "average_salary": round(float(average_salary or 0), 2),
            "uploads": int(uploads_count),
        },
        "recent": [_serialize_history(row) for row in recent_rows],
        "models": model_status,
        "cohort": get_cohort_snapshot(),
    }


@app.get("/api/settings")
def get_settings() -> dict[str, Any]:
    return load_settings()


class SettingsUpdate(BaseModel):
    display_name: str | None = None
    theme: Literal["dark", "light"] | None = None
    max_upload_mb: int | None = Field(default=None, ge=1, le=200)
    store_original_files: bool | None = None


@app.put("/api/settings")
def update_settings(payload: SettingsUpdate) -> dict[str, Any]:
    return save_settings({k: v for k, v in payload.model_dump().items() if v is not None})


@app.get("/api/history")
def get_history(q: str = "", limit: int = 200) -> list[dict[str, Any]]:
    limit = max(1, min(500, limit))
    with get_db() as conn:
        if q.strip():
            term = f"%{q.strip()}%"
            rows = conn.execute(
                "SELECT * FROM analyses WHERE candidate_name LIKE ? OR file_name LIKE ? ORDER BY id DESC LIMIT ?",
                (term, term, limit),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM analyses ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [_serialize_history(row, include_detail=True) for row in rows]


@app.get("/api/history/{record_id}")
def get_history_item(record_id: int) -> dict[str, Any]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM analyses WHERE id=?", (record_id,)).fetchone()
    if not row:
        raise HTTPException(404, "History record not found.")
    return _serialize_history(row, include_detail=True)


@app.delete("/api/history/{record_id}")
def delete_history_item(record_id: int) -> dict[str, bool]:
    with get_db() as conn:
        row = conn.execute("SELECT report_name FROM analyses WHERE id=?", (record_id,)).fetchone()
        if not row:
            raise HTTPException(404, "History record not found.")
        conn.execute("DELETE FROM analyses WHERE id=?", (record_id,))
    if row["report_name"]:
        (REPORT_DIR / row["report_name"]).unlink(missing_ok=True)
    return {"deleted": True}


@app.delete("/api/history")
def clear_history() -> dict[str, int]:
    with get_db() as conn:
        total = int(conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0])
        rows = conn.execute("SELECT report_name FROM analyses WHERE report_name IS NOT NULL").fetchall()
        conn.execute("DELETE FROM analyses")
    for row in rows:
        if row["report_name"]:
            (REPORT_DIR / row["report_name"]).unlink(missing_ok=True)
    return {"deleted": total}


@app.get("/api/export/history")
def export_history(format: Literal["csv", "json"] = "csv") -> StreamingResponse:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM analyses ORDER BY id DESC").fetchall()
    records = [_serialize_history(row, include_detail=True) for row in rows]
    if format == "json":
        content = json.dumps(records, indent=2, ensure_ascii=False)
        return StreamingResponse(io.BytesIO(content.encode("utf-8")), media_type="application/json", headers={"Content-Disposition": "attachment; filename=placement-history.json"})
    output = io.StringIO()
    fields = ["id", "created_at", "candidate_name", "file_name", "prediction", "probability", "salary", "resume_score"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in records:
        writer.writerow({field: row.get(field) for field in fields})
    return StreamingResponse(io.BytesIO(output.getvalue().encode("utf-8-sig")), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=placement-history.csv"})


@app.post("/api/upload")
async def upload_to_library(file: UploadFile = File(...)) -> dict[str, Any]:
    content = await file.read()
    _check_upload_size(content)
    if not content:
        raise HTTPException(400, "The uploaded file is empty.")
    item = _save_file_record(file.filename or "uploaded-file", content, file.content_type, "file")
    return item


@app.post("/api/parse-resume")
async def parse_resume(file: UploadFile = File(...)) -> dict[str, Any]:
    content = await file.read()
    _check_upload_size(content)
    if not content:
        raise HTTPException(400, "The uploaded file is empty.")
    original_name = _safe_original_name(file.filename)
    suffix = Path(original_name).suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt", ".md", ".rtf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp", ".csv", ".xlsx", ".xls", ".json", ".html", ".htm"}:
        raise HTTPException(415, "Resume parsing supports PDF, DOCX, TXT, MD, RTF, image, CSV, Excel, JSON, and HTML files. Any other file can still be stored in the File Library.")
    temp_path = UPLOAD_DIR / f"parse_{uuid.uuid4().hex}{suffix}"
    temp_path.write_bytes(content)
    try:
        text = extract_text_from_file(temp_path)
        if len(text.strip()) < 20:
            raise HTTPException(422, "Not enough readable text was found. Try a text-based PDF/DOCX or fill in the profile manually.")
        profile = analyze_resume_text(text, fallback_name=Path(original_name).stem)
        settings = load_settings()
        saved = None
        if settings.get("store_original_files", True):
            saved = _save_file_record(original_name, content, file.content_type, "resume")
        return {
            "profile": profile,
            "upload": saved,
            "filename": original_name,
            "extracted_characters": len(text),
            "text": text[:30000],
            "message": "Resume text extracted. Review and correct every field before running the prediction.",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Resume extraction failed")
        raise HTTPException(422, f"Could not extract this file: {exc}") from exc
    finally:
        temp_path.unlink(missing_ok=True)


class AnalyzeRequest(BaseModel):
    profile: dict[str, Any]
    upload_id: int | None = None
    file_name: str | None = None


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest) -> dict[str, Any]:
    global models
    normalized = _normalise_profile(payload.profile)
    with model_lock:
        active_models = _current_models()
        prediction = predict_profile(normalized, active_models)
    score = calculate_resume_score(normalized)
    missing_skills = recommend_skills(normalized)
    recommendations = {
        "missing_skills": missing_skills,
        "projects": recommend_projects(normalized),
        "roadmap": generate_roadmap(normalized),
    }
    prediction["resume_score"] = score
    prediction["model_metrics"] = {
        "placement": active_models["placement_metrics"],
        "salary": active_models["salary_metrics"],
    }
    candidate_name = normalized.get("name") or "Candidate"
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO analyses(created_at, candidate_name, file_name, upload_id, prediction, probability, salary, resume_score, profile_json, recommendations_json, report_name, model_metrics_json) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                utc_now(), candidate_name, payload.file_name, payload.upload_id,
                prediction["prediction"], prediction["probability"], prediction["salary"], score,
                json.dumps(normalized, ensure_ascii=False), json.dumps(recommendations, ensure_ascii=False),
                None, json.dumps(prediction["model_metrics"]),
            ),
        )
        record_id = int(cursor.lastrowid)
    report_name = _create_pdf_report(record_id, normalized, prediction, recommendations)
    with get_db() as conn:
        conn.execute("UPDATE analyses SET report_name=? WHERE id=?", (report_name, record_id))
    return {
        "id": record_id,
        "created_at": utc_now(),
        "profile": normalized,
        "result": prediction,
        "recommendations": recommendations,
        "report_url": f"/api/reports/{record_id}",
        "notice": "This is a model estimate, not a placement guarantee. Confirm extracted profile details before relying on the result.",
    }


@app.get("/api/reports/{record_id}")
def download_report(record_id: int) -> FileResponse:
    with get_db() as conn:
        row = conn.execute("SELECT report_name, candidate_name FROM analyses WHERE id=?", (record_id,)).fetchone()
    if not row or not row["report_name"]:
        raise HTTPException(404, "Report not found.")
    path = REPORT_DIR / row["report_name"]
    if not path.exists():
        raise HTTPException(404, "The report file is missing from local storage.")
    return FileResponse(path, media_type="application/pdf", filename=f"{_safe_original_name(row['candidate_name'])}_Placement_Report.pdf")


@app.get("/api/files")
def list_files() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM uploads ORDER BY id DESC LIMIT 300").fetchall()
    return [{
        "id": row["id"], "name": row["original_name"], "category": row["category"],
        "content_type": row["content_type"], "size_bytes": row["size_bytes"],
        "uploaded_at": row["uploaded_at"],
    } for row in rows]


@app.get("/api/files/{file_id}/download")
def download_file(file_id: int) -> FileResponse:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM uploads WHERE id=?", (file_id,)).fetchone()
    if not row:
        raise HTTPException(404, "File not found.")
    path = UPLOAD_DIR / row["stored_name"]
    if not path.exists():
        raise HTTPException(404, "Stored file is missing.")
    media_type = row["content_type"] or mimetypes.guess_type(row["original_name"])[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=row["original_name"], content_disposition_type="attachment")


@app.delete("/api/files/{file_id}")
def delete_file(file_id: int) -> dict[str, bool]:
    with get_db() as conn:
        row = conn.execute("SELECT stored_name FROM uploads WHERE id=?", (file_id,)).fetchone()
        if not row:
            raise HTTPException(404, "File not found.")
        conn.execute("DELETE FROM uploads WHERE id=?", (file_id,))
    (UPLOAD_DIR / row["stored_name"]).unlink(missing_ok=True)
    return {"deleted": True}


@app.post("/api/datasets/{kind}")
async def replace_dataset(kind: Literal["placement", "salary"], file: UploadFile = File(...)) -> dict[str, Any]:
    global models
    filename = _safe_original_name(file.filename)
    suffix = Path(filename).suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xls"}:
        raise HTTPException(415, "Training datasets must be CSV or Excel files.")
    content = await file.read()
    _check_upload_size(content)
    temp_path = DATASET_DIR / f"incoming_{uuid.uuid4().hex}{suffix}"
    temp_path.write_bytes(content)
    target = PLACEMENT_DATASET if kind == "placement" else SALARY_DATASET
    backup = DATASET_DIR / f"backup_{uuid.uuid4().hex}{target.suffix}"
    had_old = target.exists()
    normalized_path = DATASET_DIR / f"normalized_{uuid.uuid4().hex}.csv"
    try:
        validated_df, _ = validate_dataset(temp_path, kind)
        validated_df.to_csv(normalized_path, index=False)
        if had_old:
            shutil.copy2(target, backup)
        shutil.copy2(normalized_path, target)
        with model_lock:
            candidate_models = train_models(PLACEMENT_DATASET, SALARY_DATASET)
            models = candidate_models
        return {
            "success": True,
            "kind": kind,
            "filename": filename,
            "placement_metrics": models["placement_metrics"],
            "salary_metrics": models["salary_metrics"],
            "message": "Dataset replaced and models retrained successfully.",
        }
    except Exception as exc:
        if had_old and backup.exists():
            shutil.copy2(backup, target)
        elif not had_old:
            target.unlink(missing_ok=True)
        logger.exception("Dataset update failed; restored previous dataset where possible.")
        raise HTTPException(422, f"Dataset was not applied. {exc}") from exc
    finally:
        temp_path.unlink(missing_ok=True)
        normalized_path.unlink(missing_ok=True)
        backup.unlink(missing_ok=True)


@app.get("/api/cohort")
def cohort_snapshot() -> dict[str, Any]:
    return get_cohort_snapshot()


@app.get("/api/model")
def model_details() -> dict[str, Any]:
    active = _current_models()
    return {
        "placement": active["placement_metrics"],
        "salary": active["salary_metrics"],
        "features": active["features"],
        "note": "Metrics come from a held-out test split of the current local dataset. They do not guarantee performance on a different college, year, or hiring market.",
    }


@app.get("/api/countries")
def countries() -> dict[str, Any]:
    world.refresh_fx()
    return world.public_countries()


class WorldRequest(BaseModel):
    profile: dict[str, Any]


@app.post("/api/world/estimate")
def world_estimate(payload: WorldRequest) -> dict[str, Any]:
    world.refresh_fx()
    normalized = _normalise_profile(payload.profile)
    with model_lock:
        active = _current_models()
        prediction = predict_profile(normalized, active)
        oob = active.get("salary_oob")
    q = world.percentile(prediction["salary"], oob)
    return {
        "prediction": prediction, "percentile": round(q * 100, 1),
        "resume_score": calculate_resume_score(normalized),
        "skills": normalized.get("skills", []), "estimates": world.estimate_all(q),
    }


class AtsRequest(BaseModel):
    role: str = "Software Engineer"
    text: str = ""
    skills: list[str] = []


@app.post("/api/ats")
def ats(payload: AtsRequest) -> dict[str, Any]:
    text = payload.text.strip() or " ".join(payload.skills)
    if len(text) < 5:
        raise HTTPException(422, "Upload a resume first (or add skills) so there is something to check.")
    return ats_check(text, payload.role)


@app.get("/api/ats/roles")
def ats_roles() -> list[str]:
    return list(ROLE_KEYWORDS)
