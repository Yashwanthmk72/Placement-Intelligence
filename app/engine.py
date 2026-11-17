"""Model training, resume extraction, and profile analysis for Placement Intelligence."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    precision_score,
    r2_score,
    recall_score,
    root_mean_squared_error,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

FEATURES = [
    "CGPA",
    "Major Projects",
    "Workshops/Certificatios",
    "Mini Projects",
    "Skills",
    "Communication Skill Rating",
    "Internship",
    "Hackathon",
    "12th Percentage",
    "10th Percentage",
    "backlogs",
]
NUMERIC_FEATURES = [
    "CGPA", "Major Projects", "Workshops/Certificatios", "Mini Projects",
    "Skills", "Communication Skill Rating", "12th Percentage",
    "10th Percentage", "backlogs",
]
CATEGORICAL_FEATURES = ["Internship", "Hackathon"]
SALARY_CATEGORICAL_FEATURES = ["Internship", "Hackathon", "PlacementStatus"]
TARGET_PLACEMENT = "PlacementStatus"
TARGET_SALARY = "salary"

SKILL_DATABASE: dict[str, list[str]] = {
    "Python": ["python", "pandas", "numpy", "matplotlib", "scikit-learn", "sklearn"],
    "Machine Learning": ["machine learning", "ml", "regression", "classification", "random forest"],
    "Deep Learning": ["deep learning", "tensorflow", "keras", "pytorch", "neural network", "cnn", "rnn"],
    "Computer Vision": ["computer vision", "opencv", "image processing", "object detection", "yolo"],
    "Data Science": ["data science", "data analysis", "data analytics", "statistics", "visualization"],
    "SQL": ["sql", "mysql", "postgresql", "oracle", "database"],
    "Java": ["java", "spring", "spring boot"],
    "C/C++": ["c++", "cpp", "c programming"],
    "Web Development": ["html", "css", "javascript", "web development", "frontend", "backend"],
    "React": ["react", "reactjs", "next.js", "nextjs"],
    "Cloud": ["aws", "azure", "google cloud", "gcp", "cloud computing"],
    "DevOps": ["docker", "kubernetes", "jenkins", "ci/cd", "devops"],
    "Git/GitHub": ["git", "github", "gitlab"],
    "Data Structures": ["data structures", "dsa", "algorithms", "competitive programming"],
    "Communication": ["communication", "presentation", "public speaking", "leadership"],
}
SKILL_PRIORITY = [
    "Python", "Data Structures", "SQL", "Machine Learning", "Git/GitHub",
    "Deep Learning", "Computer Vision", "Data Science", "Cloud", "Web Development",
    "React", "DevOps",
]


def _column_token(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


COLUMN_ALIASES = {
    "cgpa": "CGPA",
    "majorprojects": "Major Projects",
    "workshopscertificatios": "Workshops/Certificatios",
    "workshopscertifications": "Workshops/Certificatios",
    "workshopscertificate": "Workshops/Certificatios",
    "miniprojects": "Mini Projects",
    "skills": "Skills",
    "communicationskillrating": "Communication Skill Rating",
    "internship": "Internship",
    "hackathon": "Hackathon",
    "12thpercentage": "12th Percentage",
    "12th": "12th Percentage",
    "10thpercentage": "10th Percentage",
    "10th": "10th Percentage",
    "backlogs": "backlogs",
    "backlog": "backlogs",
    "placementstatus": "PlacementStatus",
    "salary": "salary",
}


def normalize_dataset(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.loc[:, ~out.columns.astype(str).str.match(r"^Unnamed", case=False)]
    rename: dict[Any, str] = {}
    for col in out.columns:
        token = _column_token(col)
        if token in COLUMN_ALIASES:
            rename[col] = COLUMN_ALIASES[token]
    out = out.rename(columns=rename)
    return out


def validate_dataset(path: str | Path, kind: str) -> tuple[pd.DataFrame, list[str]]:
    path = Path(path)
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        raise ValueError("Dataset must be a CSV or Excel file (.csv, .xlsx, .xls).")
    df = normalize_dataset(df)
    required = FEATURES + [TARGET_PLACEMENT]
    if kind == "salary":
        required += [TARGET_SALARY]
    missing = [name for name in required if name not in df.columns]
    if missing:
        raise ValueError("Dataset is missing required columns: " + ", ".join(missing))
    if len(df) < 20:
        raise ValueError("Please provide at least 20 rows so the model can be evaluated reliably.")
    return df, list(df.columns)


def _normalize_yes_no(series: pd.Series) -> pd.Series:
    mapping = {
        "yes": "Yes", "y": "Yes", "true": "Yes", "1": "Yes",
        "no": "No", "n": "No", "false": "No", "0": "No",
    }
    values = series.astype("string").str.strip()
    return values.map(lambda x: mapping.get(str(x).lower(), "Unknown") if pd.notna(x) else "Unknown")


def _prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    x = df[FEATURES].copy()
    for col in NUMERIC_FEATURES:
        x[col] = pd.to_numeric(x[col], errors="coerce")
    for col in CATEGORICAL_FEATURES:
        x[col] = _normalize_yes_no(x[col])
    return x


def _numeric_pipeline() -> Pipeline:
    return Pipeline([("imputer", SimpleImputer(strategy="median"))])


def _categorical_pipeline() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])


def _make_preprocessor(categorical: list[str]) -> ColumnTransformer:
    return ColumnTransformer([
        ("categorical", _categorical_pipeline(), categorical),
        ("numeric", _numeric_pipeline(), NUMERIC_FEATURES),
    ])


def train_models(placement_path: str | Path, salary_path: str | Path) -> dict[str, Any]:
    placement_df, _ = validate_dataset(placement_path, "placement")
    salary_df, _ = validate_dataset(salary_path, "salary")

    placement_df = placement_df.copy()
    placement_df["PlacementStatus"] = placement_df["PlacementStatus"].astype(str).str.strip()
    valid_placement = placement_df["PlacementStatus"].str.lower().isin({"placed", "notplaced", "not placed", "yes", "no", "1", "0", "true", "false"})
    placement_df = placement_df.loc[valid_placement].copy()
    placement_df["PlacementStatus"] = placement_df["PlacementStatus"].replace({
        "not placed": "NotPlaced", "notplaced": "NotPlaced", "placed": "Placed",
        "yes": "Placed", "no": "NotPlaced", "1": "Placed", "0": "NotPlaced",
        "true": "Placed", "false": "NotPlaced",
    })
    if placement_df["PlacementStatus"].nunique() < 2:
        raise ValueError("Placement dataset must include both placed and not-placed examples.")

    X = _prepare_features(placement_df)
    y = placement_df["PlacementStatus"]
    counts = y.value_counts()
    stratify = y if counts.min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=stratify
    )
    placement_model = Pipeline([
        ("preprocessor", _make_preprocessor(CATEGORICAL_FEATURES)),
        ("model", RandomForestClassifier(
            n_estimators=300, criterion="entropy", random_state=42,
            class_weight="balanced", n_jobs=-1, min_samples_leaf=2,
        )),
    ])
    placement_model.fit(X_train, y_train)
    pred = placement_model.predict(X_test)
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, pred)) * 100, 2),
        "precision": round(float(precision_score(y_test, pred, average="weighted", zero_division=0)) * 100, 2),
        "recall": round(float(recall_score(y_test, pred, average="weighted", zero_division=0)) * 100, 2),
        "f1": round(float(f1_score(y_test, pred, average="weighted", zero_division=0)) * 100, 2),
        "rows": int(len(placement_df)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "class_counts": {str(k): int(v) for k, v in y.value_counts().items()},
    }

    salary_df = salary_df.copy()
    salary_df["PlacementStatus"] = salary_df["PlacementStatus"].astype(str).str.strip()
    placed_mask = salary_df["PlacementStatus"].str.lower().isin({"placed", "yes", "1", "true"})
    salary_df["salary"] = pd.to_numeric(salary_df["salary"], errors="coerce")
    salary_df = salary_df.loc[placed_mask & salary_df["salary"].gt(0)].copy()
    if len(salary_df) < 20:
        raise ValueError("Salary dataset needs at least 20 placed students with a salary greater than zero.")
    salary_df["PlacementStatus"] = "Placed"
    Xs = _prepare_features(salary_df)
    Xs["PlacementStatus"] = "Placed"
    y_salary = salary_df["salary"].astype(float)
    sx_train, sx_test, sy_train, sy_test = train_test_split(
        Xs, y_salary, test_size=0.20, random_state=42
    )
    salary_preprocessor = ColumnTransformer([
        ("categorical", _categorical_pipeline(), SALARY_CATEGORICAL_FEATURES),
        ("numeric", _numeric_pipeline(), NUMERIC_FEATURES),
    ])
    salary_model = Pipeline([
        ("preprocessor", salary_preprocessor),
        ("model", RandomForestRegressor(
            n_estimators=300, random_state=42, n_jobs=-1, min_samples_leaf=2, oob_score=True
        )),
    ])
    salary_model.fit(sx_train, sy_train)
    salary_pred = salary_model.predict(sx_test)
    salary_metrics = {
        "mae": round(float(mean_absolute_error(sy_test, salary_pred)), 2),
        "r2": round(float(r2_score(sy_test, salary_pred)), 4),
        "rows": int(len(salary_df)),
        "train_rows": int(len(sx_train)),
        "test_rows": int(len(sx_test)),
    }
    return {
        "placement_model": placement_model,
        "salary_model": salary_model,
        "placement_metrics": metrics,
        "salary_metrics": salary_metrics,
        "features": FEATURES,
        "salary_oob": np.sort(np.asarray(salary_model.named_steps["model"].oob_prediction_, dtype=float)),
    }


def profile_to_frame(profile: dict[str, Any], placement_status: str | None = None) -> pd.DataFrame:
    values: dict[str, Any] = {
        "CGPA": profile.get("cgpa"),
        "Major Projects": profile.get("major_projects"),
        "Workshops/Certificatios": profile.get("workshops"),
        "Mini Projects": profile.get("mini_projects"),
        "Skills": profile.get("skills_count"),
        "Communication Skill Rating": profile.get("communication"),
        "Internship": profile.get("internship") or "Unknown",
        "Hackathon": profile.get("hackathon") or "Unknown",
        "12th Percentage": profile.get("twelfth"),
        "10th Percentage": profile.get("tenth"),
        "backlogs": profile.get("backlogs"),
    }
    for key in NUMERIC_FEATURES:
        if values[key] in (None, ""):
            values[key] = np.nan
        else:
            values[key] = float(values[key])
    if placement_status is not None:
        values["PlacementStatus"] = placement_status
    return pd.DataFrame([values])


def predict_profile(profile: dict[str, Any], models: dict[str, Any]) -> dict[str, Any]:
    frame = profile_to_frame(profile)
    model = models["placement_model"]
    prediction = str(model.predict(frame)[0])
    probability_map = dict(zip(model.classes_, model.predict_proba(frame)[0]))
    placed_probability = float(probability_map.get("Placed", 0.0) * 100)
    salary_frame = profile_to_frame(profile, placement_status="Placed")
    salary = max(0.0, float(models["salary_model"].predict(salary_frame)[0]))
    return {
        "prediction": prediction,
        "probability": round(placed_probability, 2),
        "salary": round(salary, 2),
    }


def calculate_resume_score(profile: dict[str, Any]) -> int:
    score = 0.0
    cgpa = float(profile.get("cgpa") or 0)
    score += min(20, cgpa / 10 * 20)
    score += min(15, float(profile.get("major_projects") or 0) * 5)
    score += min(8, float(profile.get("mini_projects") or 0) * 2.67)
    score += min(8, float(profile.get("workshops") or 0) * 2.67)
    score += min(15, float(profile.get("skills_count") or 0) * 1.5)
    if profile.get("internship") == "Yes":
        score += 10
    if profile.get("hackathon") == "Yes":
        score += 7
    score += min(7, float(profile.get("communication") or 0) / 5 * 7)
    score += min(5, float(profile.get("twelfth") or 0) / 100 * 5)
    score += min(5, float(profile.get("tenth") or 0) / 100 * 5)
    score -= min(15, float(profile.get("backlogs") or 0) * 3)
    return int(round(max(0, min(100, score))))


def detect_skills(text: str) -> list[str]:
    lowered = text.lower()
    detected = []
    for skill, keywords in SKILL_DATABASE.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            detected.append(skill)
    return sorted(set(detected))


def _extract_number(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            try:
                value = float(match.group(1))
                if np.isfinite(value):
                    return value
            except (ValueError, IndexError):
                continue
    return None


def _extract_name(text: str, fallback: str = "") -> str:
    for line in [x.strip() for x in text.splitlines()[:12] if x.strip()]:
        cleaned = re.sub(r"[^A-Za-z .'-]", "", line).strip()
        if 2 <= len(cleaned.split()) <= 4 and len(cleaned) <= 45:
            skip = {"resume", "curriculum vitae", "career objective", "profile summary", "contact details"}
            if cleaned.lower() not in skip:
                return cleaned.title()
    return fallback or "Candidate"


def _count_items(text: str, section_words: list[str], explicit_patterns: list[str] | None = None) -> int:
    if explicit_patterns:
        explicit = _extract_number(text, explicit_patterns)
        if explicit is not None:
            return max(0, min(100, int(explicit)))
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    section_headers = {
        "education", "technical skills", "skills", "projects", "major projects",
        "mini projects", "certifications and workshops", "certifications", "workshops",
        "internship", "hackathons", "achievements", "areas of interest", "languages",
        "github projects", "declaration", "soft skills", "career objective", "experience",
    }
    for i, line in enumerate(lines):
        normalized = re.sub(r"[^a-z ]", "", line.lower()).strip()
        if any(word in normalized for word in section_words):
            segment = []
            for item in lines[i + 1:i + 25]:
                clean = re.sub(r"[^a-z ]", "", item.lower()).strip()
                if clean in section_headers and segment:
                    break
                if item.isupper() and len(item) < 45 and segment:
                    break
                segment.append(item)
            bullets = sum(1 for item in segment if re.match(r"^(?:[-*•]|\d+[.)])\s*", item))
            named = sum(1 for item in segment if re.search(r"\b(project|workshop|certification|hackathon)\b", item, re.I))
            count = max(bullets, named)
            if count:
                return min(count, 20)
    return 0


def analyze_resume_text(text: str, fallback_name: str = "") -> dict[str, Any]:
    skills = detect_skills(text)
    cgpa = _extract_number(text, [r"(?:cgpa|c\.g\.p\.a\.?|gpa)\s*[:\-]?\s*(\d+(?:\.\d+)?)"])
    tenth = _extract_number(text, [r"(?:10th|tenth|sslc)\D{0,50}(\d+(?:\.\d+)?)\s*%"])
    twelfth = _extract_number(text, [r"(?:12th|twelfth|puc|hsc)\D{0,50}(\d+(?:\.\d+)?)\s*%"])
    communication = _extract_number(text, [r"communication\s*(?:skill\s*)?rating\D{0,12}(\d+(?:\.\d+)?)"])
    backlogs = _extract_number(text, [r"(?:backlogs?|arrears?)\s*[:\-]?\s*(\d+)"])
    internship = "Yes" if re.search(r"\b(internship|interned|intern)\b", text, re.I) else "No"
    hackathon = "Yes" if re.search(r"\bhackathons?\b", text, re.I) else "No"
    return {
        "name": _extract_name(text, fallback_name),
        "cgpa": min(10, max(0, cgpa)) if cgpa is not None else None,
        "tenth": min(100, max(0, tenth)) if tenth is not None else None,
        "twelfth": min(100, max(0, twelfth)) if twelfth is not None else None,
        "major_projects": _count_items(text, ["major projects", "project experience", "academic projects"], [r"major\s+projects?\s*[:\-]?\s*(\d+)"]),
        "workshops": _count_items(text, ["certifications", "certificates", "workshops"], [r"(?:certifications?\s*(?:/|and)\s*workshops?|workshops?\s*/\s*certifications?)\s*[:\-]?\s*(\d+)"]),
        "mini_projects": _count_items(text, ["mini projects", "minor projects"], [r"mini\s+projects\s*[:\-]\s*(\d+)"]),
        "skills": skills,
        "skills_count": min(20, len(skills)),
        "communication": min(5, max(0, communication)) if communication is not None else None,
        "internship": internship,
        "hackathon": hackathon,
        "backlogs": max(0, backlogs) if backlogs is not None else None,
    }


def extract_text_from_file(path: str | Path) -> str:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix in {".txt", ".md", ".rtf", ".csv", ".json", ".html", ".htm"}:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        from pypdf import PdfReader
        text = "\n".join((page.extract_text() or "") for page in PdfReader(str(file_path)).pages)
        if len(text.strip()) < 30:
            try:
                import fitz
                import pytesseract
                from PIL import Image
                import io
                pdf = fitz.open(str(file_path))
                chunks = []
                for page in pdf:
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
                    image = Image.open(io.BytesIO(pix.tobytes("png")))
                    chunks.append(pytesseract.image_to_string(image))
                text = "\n".join(chunks)
            except Exception:
                pass
        return text
    if suffix == ".docx":
        from docx import Document
        doc = Document(str(file_path))
        chunks = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                chunks.extend(cell.text for cell in row.cells if cell.text.strip())
        return "\n".join(chunks)
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}:
        try:
            import pytesseract
            from PIL import Image
            return pytesseract.image_to_string(Image.open(file_path))
        except Exception as exc:
            raise ValueError("Image OCR is unavailable. Install Tesseract OCR to read image-based resumes.") from exc
    if suffix in {".xlsx", ".xls"}:
        try:
            book = pd.ExcelFile(file_path)
            return "\n".join(pd.read_excel(book, sheet_name=sheet).to_string(index=False) for sheet in book.sheet_names)
        except Exception as exc:
            raise ValueError(f"Could not read spreadsheet: {exc}") from exc
    raise ValueError("This file can be stored in your file library, but automatic resume extraction supports PDF, DOCX, TXT, MD, RTF, images, CSV, and Excel files.")


def recommend_skills(profile: dict[str, Any]) -> list[str]:
    current = set(profile.get("skills") or [])
    return [skill for skill in SKILL_PRIORITY if skill not in current][:6]


PROJECTS = {
    "Python": ("Personalized Career Analytics Dashboard", "Beginner", "Python, Pandas, Plotly", "Build a dashboard that explores placement and skill trends."),
    "Data Structures": ("DSA Progress Tracker", "Beginner", "Python or Java, SQLite", "Track topic coverage, practice sessions, and solved problems."),
    "SQL": ("Recruitment Insights Database", "Intermediate", "SQL, PostgreSQL", "Design a relational database for candidates, jobs, and hiring outcomes."),
    "Machine Learning": ("Student Employability Model", "Intermediate", "Scikit-learn, Pandas", "Compare models with stratified validation and explain their errors."),
    "Git/GitHub": ("Open-source Contribution Portfolio", "Beginner", "Git, GitHub", "Publish clean repositories with documentation and tests."),
    "Deep Learning": ("Resume Section Classifier", "Advanced", "PyTorch, NLP", "Classify resume sections and extract entities from varied layouts."),
    "Computer Vision": ("Document OCR Quality Checker", "Intermediate", "OpenCV, OCR", "Detect low-quality scans and improve text extraction."),
    "Data Science": ("Placement Trends Study", "Intermediate", "Pandas, Matplotlib", "Analyze cohort outcomes and document possible data bias."),
    "Cloud": ("Career App Deployment", "Intermediate", "Docker, Cloud", "Deploy an API with monitoring, backups, and secure configuration."),
    "Web Development": ("Student Portfolio Website", "Beginner", "HTML, CSS, JavaScript", "Present projects, achievements, and a downloadable resume."),
    "React": ("Interactive Job Tracker", "Intermediate", "React, REST API", "Create a searchable application tracker with status history."),
    "DevOps": ("CI Pipeline for ML App", "Advanced", "GitHub Actions, Docker", "Automate tests, linting, packaging, and deployment checks."),
}


def recommend_projects(profile: dict[str, Any]) -> list[dict[str, str]]:
    missing = recommend_skills(profile)
    selected = missing[:3] if missing else ["Machine Learning"]
    return [
        {"name": PROJECTS[key][0], "difficulty": PROJECTS[key][1], "technology": PROJECTS[key][2], "description": PROJECTS[key][3]}
        for key in selected
    ]


def generate_roadmap(profile: dict[str, Any]) -> list[dict[str, str]]:
    targets = recommend_skills(profile)[:6]
    if not targets:
        targets = ["Advanced project work", "Interview preparation"]
    tasks = [
        "Revise core concepts and complete a focused learning module.",
        "Solve practical exercises and document what you learn.",
        "Build a small project and publish a clear README.",
        "Ask for feedback, improve the project, and prepare to explain it.",
        "Add tests, deployment notes, and measurable project outcomes.",
        "Update your resume and practise role-specific interview questions.",
    ]
    return [{"week": f"Week {i + 1}", "skill": skill, "task": tasks[i % len(tasks)]} for i, skill in enumerate(targets)]


ROLE_KEYWORDS: dict[str, list[str]] = {
    "Software Engineer": ["data structures", "algorithms", "java", "python", "c++", "git", "sql", "api", "oop", "testing", "docker", "system design", "linux", "agile", "rest"],
    "Data Analyst": ["sql", "excel", "python", "pandas", "tableau", "power bi", "statistics", "visualization", "data cleaning", "dashboard", "etl", "analysis", "reporting", "numpy", "a/b testing"],
    "ML / AI Engineer": ["python", "machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn", "nlp", "computer vision", "pandas", "numpy", "model deployment", "statistics", "mlops", "docker", "sql"],
    "Web Developer": ["html", "css", "javascript", "react", "node", "typescript", "rest", "git", "responsive", "sql", "mongodb", "api", "testing", "deployment", "figma"],
    "Cloud / DevOps": ["aws", "azure", "docker", "kubernetes", "linux", "ci/cd", "terraform", "git", "python", "bash", "monitoring", "networking", "jenkins", "github actions", "security"],
}


def ats_check(text: str, role: str) -> dict[str, Any]:
    low = text.lower()
    keys = ROLE_KEYWORDS.get(role) or ROLE_KEYWORDS["Software Engineer"]
    matched = [k for k in keys if k in low]
    missing = [k for k in keys if k not in low]
    checks = [
        ("Email address", bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text))),
        ("Phone number", bool(re.search(r"\+?\d[\d\s-]{8,}", text))),
        ("Education section", "education" in low),
        ("Projects section", "project" in low),
        ("Skills section", "skills" in low),
        ("Measurable results (numbers/%)", len(re.findall(r"\d+\s*%|\b\d{2,}\+?\b", text)) >= 3),
        ("Sensible length (150-900 words)", 150 <= len(text.split()) <= 900),
        ("Links (GitHub/LinkedIn)", "github" in low or "linkedin" in low),
    ]
    kw_score = len(matched) / len(keys) * 70
    fmt_score = sum(1 for _, ok in checks if ok) / len(checks) * 30
    tips = [f"Add evidence of: {', '.join(missing[:5])}." ] if missing else []
    tips += [f"Add or fix: {name}." for name, ok in checks if not ok]
    return {"role": role, "score": int(round(kw_score + fmt_score)), "matched": matched, "missing": missing,
            "checks": [{"name": n, "ok": ok} for n, ok in checks], "tips": tips[:6], "roles": list(ROLE_KEYWORDS)}
