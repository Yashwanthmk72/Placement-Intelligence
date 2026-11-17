# ================================================================
# 🚀 AI PLACEMENT & CAREER ANALYZER
# ================================================================
# COMPLETE GOOGLE COLAB VERSION
#
# DATASETS REQUIRED:
#   Placement_Prediction_data.csv
#   Salary_prediction_data.csv
#
# RESUME SUPPORTED:
#   PDF / DOCX / TXT / MD / PNG / JPG / JPEG / WEBP
#
# ================================================================


# ================================================================
# 1. INSTALL DEPENDENCIES
# ================================================================

!pip -q install gradio pandas numpy scikit-learn pypdf python-docx pillow pytesseract reportlab pymupdf


# ================================================================
# 2. SYSTEM DEPENDENCY FOR OCR
# ================================================================

!apt-get -qq update
!apt-get -qq install -y tesseract-ocr


# ================================================================
# 3. IMPORT LIBRARIES
# ================================================================

import os
import re
import traceback
import warnings
import numpy as np
import pandas as pd

from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")


# Machine Learning
from sklearn.model_selection import train_test_split
from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor
)

from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


# Resume extraction
from pypdf import PdfReader
from docx import Document

from PIL import Image
import pytesseract

import fitz


# Website
import gradio as gr


# PDF report
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


# ================================================================
# 4. UPLOAD DATASETS
# ================================================================

from google.colab import files

print("=" * 70)
print("📂 UPLOAD DATASETS")
print("=" * 70)

print("""
Please upload BOTH files:

1. Placement_Prediction_data.csv
2. Salary_prediction_data.csv

""")

uploaded = files.upload()

uploaded_files = list(uploaded.keys())

print("\nFiles uploaded:")

for filename in uploaded_files:
    print("✓", filename)


# ================================================================
# 5. FIND DATASET FILES
# ================================================================

placement_candidates = [
    f for f in uploaded_files
    if "placement" in f.lower()
    and f.lower().endswith(".csv")
]

salary_candidates = [
    f for f in uploaded_files
    if "salary" in f.lower()
    and f.lower().endswith(".csv")
]


if not placement_candidates:

    raise FileNotFoundError(
        "\n❌ Placement dataset was not found.\n\n"
        "Upload a CSV containing 'placement' "
        "in its filename."
    )


if not salary_candidates:

    raise FileNotFoundError(
        "\n❌ Salary dataset was not found.\n\n"
        "Upload a CSV containing 'salary' "
        "in its filename."
    )


PLACEMENT_FILE = placement_candidates[0]
SALARY_FILE = salary_candidates[0]


print("\nPlacement dataset:")
print(PLACEMENT_FILE)

print("\nSalary dataset:")
print(SALARY_FILE)


# ================================================================
# 6. LOAD DATASETS
# ================================================================

placement_df = pd.read_csv(
    PLACEMENT_FILE
)

salary_df = pd.read_csv(
    SALARY_FILE
)


# Remove unnamed columns
placement_df = placement_df.loc[
    :,
    ~placement_df.columns.astype(str).str.contains(
        "^Unnamed",
        case=False
    )
]

salary_df = salary_df.loc[
    :,
    ~salary_df.columns.astype(str).str.contains(
        "^Unnamed",
        case=False
    )
]


print("\n" + "=" * 70)
print("📊 DATASET INFORMATION")
print("=" * 70)

print(
    "\nPlacement shape:",
    placement_df.shape
)

print(
    "Salary shape:",
    salary_df.shape
)

print(
    "\nPlacement columns:"
)

print(
    placement_df.columns.tolist()
)

print(
    "\nSalary columns:"
)

print(
    salary_df.columns.tolist()
)


# ================================================================
# 7. NORMALIZE COLUMN NAMES
# ================================================================

def clean_column_name(column):

    return (
        str(column)
        .strip()
        .replace("\n", " ")
        .replace("\t", " ")
    )


placement_df.columns = [
    clean_column_name(c)
    for c in placement_df.columns
]

salary_df.columns = [
    clean_column_name(c)
    for c in salary_df.columns
]


# ================================================================
# 8. EXPECTED COLUMNS
# ================================================================

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
    "backlogs"
]

TARGET_PLACEMENT = "PlacementStatus"
TARGET_SALARY = "salary"


# ================================================================
# 9. CHECK DATASET COLUMNS
# ================================================================

missing_placement = [
    column
    for column in FEATURES + [TARGET_PLACEMENT]
    if column not in placement_df.columns
]

if missing_placement:

    print("\n❌ PLACEMENT DATASET ERROR")

    print(
        "\nMissing columns:"
    )

    for column in missing_placement:
        print(
            " -",
            column
        )

    print(
        "\nYour placement CSV contains:"
    )

    print(
        placement_df.columns.tolist()
    )

    raise ValueError(
        "\nPlacement dataset has missing columns."
    )


missing_salary = [
    column
    for column in FEATURES + [
        TARGET_PLACEMENT,
        TARGET_SALARY
    ]
    if column not in salary_df.columns
]

if missing_salary:

    print("\n❌ SALARY DATASET ERROR")

    print(
        "\nMissing columns:"
    )

    for column in missing_salary:
        print(
            " -",
            column
        )

    print(
        "\nYour salary CSV contains:"
    )

    print(
        salary_df.columns.tolist()
    )

    raise ValueError(
        "\nSalary dataset has missing columns."
    )


# ================================================================
# 10. CLEAN DATA
# ================================================================

placement_df = placement_df.copy()
salary_df = salary_df.copy()


# Convert numeric fields
numeric_columns = [
    "CGPA",
    "Major Projects",
    "Workshops/Certificatios",
    "Mini Projects",
    "Skills",
    "Communication Skill Rating",
    "12th Percentage",
    "10th Percentage",
    "backlogs"
]


for column in numeric_columns:

    placement_df[column] = pd.to_numeric(
        placement_df[column],
        errors="coerce"
    )

    salary_df[column] = pd.to_numeric(
        salary_df[column],
        errors="coerce"
    )


# Fill numeric missing values
for column in numeric_columns:

    placement_df[column] = placement_df[column].fillna(
        placement_df[column].median()
    )

    salary_df[column] = salary_df[column].fillna(
        salary_df[column].median()
    )


# Fill categorical values
for column in [
    "Internship",
    "Hackathon",
    "PlacementStatus"
]:

    if column in placement_df.columns:

        placement_df[column] = (
            placement_df[column]
            .astype(str)
            .fillna("No")
        )

    if column in salary_df.columns:

        salary_df[column] = (
            salary_df[column]
            .astype(str)
            .fillna("No")
        )


# ================================================================
# 11. PLACEMENT MODEL
# ================================================================

X_placement = placement_df[
    FEATURES
].copy()

y_placement = (
    placement_df[TARGET_PLACEMENT]
    .astype(str)
    .str.strip()
)


categorical_features = [
    "Internship",
    "Hackathon"
]


numeric_features = [
    "CGPA",
    "Major Projects",
    "Workshops/Certificatios",
    "Mini Projects",
    "Skills",
    "Communication Skill Rating",
    "12th Percentage",
    "10th Percentage",
    "backlogs"
]


placement_preprocessor = ColumnTransformer(

    transformers=[

        (
            "categorical",

            OneHotEncoder(
                handle_unknown="ignore"
            ),

            categorical_features
        ),

        (
            "numeric",

            "passthrough",

            numeric_features
        )

    ]

)


placement_model = Pipeline(

    steps=[

        (
            "preprocessor",
            placement_preprocessor
        ),

        (
            "model",

            RandomForestClassifier(

                n_estimators=300,

                criterion="entropy",

                random_state=42,

                class_weight="balanced",

                n_jobs=-1

            )

        )

    ]

)


# ================================================================
# 12. TRAIN PLACEMENT MODEL
# ================================================================

try:

    X_train, X_test, y_train, y_test = train_test_split(

        X_placement,

        y_placement,

        test_size=0.30,

        random_state=42,

        stratify=y_placement

    )

except:

    X_train, X_test, y_train, y_test = train_test_split(

        X_placement,

        y_placement,

        test_size=0.30,

        random_state=42

    )


placement_model.fit(
    X_train,
    y_train
)


placement_predictions = placement_model.predict(
    X_test
)


placement_accuracy = accuracy_score(
    y_test,
    placement_predictions
)


# ================================================================
# 13. PLACEMENT METRICS
# ================================================================

placement_precision = precision_score(
    y_test,
    placement_predictions,
    average="weighted",
    zero_division=0
)

placement_recall = recall_score(
    y_test,
    placement_predictions,
    average="weighted",
    zero_division=0
)

placement_f1 = f1_score(
    y_test,
    placement_predictions,
    average="weighted",
    zero_division=0
)


print("\n" + "=" * 70)
print("🎯 PLACEMENT MODEL")
print("=" * 70)

print(
    f"Accuracy : {placement_accuracy * 100:.2f}%"
)

print(
    f"Precision: {placement_precision * 100:.2f}%"
)

print(
    f"Recall   : {placement_recall * 100:.2f}%"
)

print(
    f"F1 Score : {placement_f1 * 100:.2f}%"
)


# ================================================================
# 14. SALARY MODEL
# ================================================================
# Salary is continuous numeric data.
# Therefore RandomForestRegressor is used.
# ================================================================

salary_features = FEATURES + [
    TARGET_PLACEMENT
]


X_salary = salary_df[
    salary_features
].copy()


y_salary = pd.to_numeric(
    salary_df[TARGET_SALARY],
    errors="coerce"
)


valid_salary = y_salary.notna()


X_salary = X_salary[
    valid_salary
].copy()

y_salary = y_salary[
    valid_salary
].copy()


salary_categorical_features = [
    "Internship",
    "Hackathon",
    "PlacementStatus"
]


salary_preprocessor = ColumnTransformer(

    transformers=[

        (
            "categorical",

            OneHotEncoder(
                handle_unknown="ignore"
            ),

            salary_categorical_features
        ),

        (
            "numeric",

            "passthrough",

            numeric_features
        )

    ]

)


salary_model = Pipeline(

    steps=[

        (
            "preprocessor",
            salary_preprocessor
        ),

        (
            "model",

            RandomForestRegressor(

                n_estimators=300,

                random_state=42,

                n_jobs=-1

            )

        )

    ]

)


# ================================================================
# 15. TRAIN SALARY MODEL
# ================================================================

salary_X_train, salary_X_test, salary_y_train, salary_y_test = train_test_split(

    X_salary,

    y_salary,

    test_size=0.30,

    random_state=42

)


salary_model.fit(

    salary_X_train,

    salary_y_train

)


salary_predictions = salary_model.predict(
    salary_X_test
)


salary_mae = mean_absolute_error(
    salary_y_test,
    salary_predictions
)


salary_rmse = np.sqrt(
    mean_squared_error(
        salary_y_test,
        salary_predictions
    )
)


salary_r2 = r2_score(
    salary_y_test,
    salary_predictions
)


print("\n" + "=" * 70)
print("💰 SALARY MODEL")
print("=" * 70)

print(
    f"MAE : ₹{salary_mae:,.2f}"
)

print(
    f"RMSE: ₹{salary_rmse:,.2f}"
)

print(
    f"R²  : {salary_r2:.4f}"
)


# ================================================================
# 16. SKILL DATABASE
# ================================================================

SKILL_DATABASE = {

    "Python": [
        "python",
        "pandas",
        "numpy",
        "matplotlib",
        "scikit-learn",
        "sklearn"
    ],

    "Machine Learning": [
        "machine learning",
        "ml",
        "scikit-learn",
        "sklearn",
        "regression",
        "classification",
        "random forest"
    ],

    "Deep Learning": [
        "deep learning",
        "tensorflow",
        "keras",
        "pytorch",
        "neural network",
        "cnn",
        "rnn"
    ],

    "Computer Vision": [
        "computer vision",
        "opencv",
        "image processing",
        "object detection",
        "yolo"
    ],

    "Data Science": [
        "data science",
        "data analysis",
        "data analytics",
        "statistics",
        "visualization"
    ],

    "SQL": [
        "sql",
        "mysql",
        "postgresql",
        "oracle",
        "database"
    ],

    "Java": [
        "java",
        "spring",
        "spring boot"
    ],

    "C/C++": [
        "c++",
        "cpp",
        "c programming"
    ],

    "Web Development": [
        "html",
        "css",
        "javascript",
        "web development",
        "frontend",
        "backend"
    ],

    "React": [
        "react",
        "reactjs",
        "next.js",
        "nextjs"
    ],

    "Cloud": [
        "aws",
        "azure",
        "google cloud",
        "gcp",
        "cloud computing"
    ],

    "DevOps": [
        "docker",
        "kubernetes",
        "jenkins",
        "ci/cd",
        "devops"
    ],

    "Git/GitHub": [
        "git",
        "github",
        "gitlab"
    ],

    "Data Structures": [
        "data structures",
        "dsa",
        "algorithms",
        "competitive programming"
    ],

    "Communication": [
        "communication",
        "presentation",
        "public speaking",
        "leadership"
    ]

}


# ================================================================
# 17. EXTRACT RESUME TEXT
# ================================================================

def extract_text_from_file(
    file_path
):

    if file_path is None:

        return ""


    extension = (
        Path(file_path)
        .suffix
        .lower()
    )


    # ------------------------------------------------------------
    # TXT / MD
    # ------------------------------------------------------------

    if extension in [
        ".txt",
        ".md"
    ]:

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as file:

                return file.read()

        except Exception as error:

            print(
                "Text file error:",
                error
            )

            return ""


    # ------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------

    if extension == ".pdf":

        text = ""


        try:

            reader = PdfReader(
                file_path
            )

            for page in reader.pages:

                page_text = page.extract_text()

                if page_text:

                    text += (
                        page_text
                        + "\n"
                    )

        except Exception as error:

            print(
                "PDF text extraction error:",
                error
            )


        # OCR fallback for scanned PDF
        if len(text.strip()) < 30:

            try:

                pdf = fitz.open(
                    file_path
                )

                for page in pdf:

                    pix = page.get_pixmap(
                        matrix=fitz.Matrix(
                            1.5,
                            1.5
                        )
                    )

                    image = Image.frombytes(
                        "RGB",
                        [
                            pix.width,
                            pix.height
                        ],
                        pix.samples
                    )

                    text += pytesseract.image_to_string(
                        image
                    )

                pdf.close()

            except Exception as error:

                print(
                    "PDF OCR error:",
                    error
                )


        return text


    # ------------------------------------------------------------
    # DOCX
    # ------------------------------------------------------------

    if extension == ".docx":

        try:

            document = Document(
                file_path
            )

            text_parts = []


            for paragraph in document.paragraphs:

                if paragraph.text.strip():

                    text_parts.append(
                        paragraph.text
                    )


            for table in document.tables:

                for row in table.rows:

                    for cell in row.cells:

                        if cell.text.strip():

                            text_parts.append(
                                cell.text
                            )


            return "\n".join(
                text_parts
            )

        except Exception as error:

            print(
                "DOCX error:",
                error
            )

            return ""


    # ------------------------------------------------------------
    # IMAGE
    # ------------------------------------------------------------

    if extension in [
        ".png",
        ".jpg",
        ".jpeg",
        ".webp"
    ]:

        try:

            image = Image.open(
                file_path
            )

            return pytesseract.image_to_string(
                image
            )

        except Exception as error:

            print(
                "Image OCR error:",
                error
            )

            return ""


    return ""


# ================================================================
# 18. DETECT SKILLS
# ================================================================

def detect_skills(
    text
):

    text_lower = text.lower()

    detected = []


    for skill, keywords in SKILL_DATABASE.items():

        for keyword in keywords:

            if keyword.lower() in text_lower:

                detected.append(
                    skill
                )

                break


    return sorted(
        set(
            detected
        )
    )


# ================================================================
# 19. EXTRACT NUMBERS
# ================================================================

def extract_number(
    text,
    patterns,
    default=None
):

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE |
            re.DOTALL
        )

        if match:

            try:

                return float(
                    match.group(1)
                )

            except:

                continue


    return default


# ================================================================
# 20. EXTRACT NAME
# ================================================================

def extract_name(
    text
):

    lines = [

        line.strip()

        for line in text.splitlines()

        if line.strip()

    ]


    for line in lines[:15]:

        low = line.lower()


        if any(
            word in low

            for word in [

                "resume",

                "curriculum",

                "vitae",

                "email",

                "phone",

                "linkedin",

                "github",

                "@"

            ]

        ):

            continue


        if 2 <= len(
            line.split()
        ) <= 5:

            if re.fullmatch(
                r"[A-Za-z .'-]+",
                line
            ):

                return line


    return "Candidate"


# ================================================================
# 21. YES / NO DETECTION
# ================================================================

def detect_yes_no(
    text,
    keywords
):

    text_lower = text.lower()


    for keyword in keywords:

        if keyword.lower() in text_lower:

            return "Yes"


    return "No"


# ================================================================
# 22. COUNT PROJECTS
# ================================================================

def count_projects(
    text
):

    text_lower = text.lower()


    # Explicit project count
    match = re.search(

        r"(?:major\s+projects?|projects?)"
        r"\s*[:\-]?\s*(\d+)",

        text_lower

    )


    if match:

        try:

            return min(
                2,
                max(
                    0,
                    int(
                        match.group(1)
                    )
                )
            )

        except:

            pass


    # Count project sections
    count = len(
        re.findall(
            r"\bproject\b",
            text_lower
        )
    )


    if count >= 4:

        return 2


    if count >= 2:

        return 1


    return 0


# ================================================================
# 23. COUNT CERTIFICATIONS / WORKSHOPS
# ================================================================

def count_certifications(
    text
):

    text_lower = text.lower()


    match = re.search(

        r"(?:certifications?|"
        r"workshops?)"
        r"\s*[:\-]?\s*(\d+)",

        text_lower

    )


    if match:

        try:

            return min(
                3,
                max(
                    0,
                    int(
                        match.group(1)
                    )
                )
            )

        except:

            pass


    count = 0


    count += len(
        re.findall(
            r"\bcertification\b",
            text_lower
        )
    )

    count += len(
        re.findall(
            r"\bworkshop\b",
            text_lower
        )
    )


    return min(
        3,
        count
    )


# ================================================================
# 24. COUNT MINI PROJECTS
# ================================================================

def count_mini_projects(
    text
):

    text_lower = text.lower()


    match = re.search(

        r"mini\s+projects?"
        r"\s*[:\-]?\s*(\d+)",

        text_lower

    )


    if match:

        try:

            return min(
                3,
                max(
                    0,
                    int(
                        match.group(1)
                    )
                )
            )

        except:

            pass


    count = len(
        re.findall(
            r"mini\s+project",
            text_lower
        )
    )


    return min(
        3,
        count
    )


# ================================================================
# 25. ANALYZE RESUME
# ================================================================

def analyze_resume(
    text
):

    skills = detect_skills(
        text
    )


    cgpa = extract_number(

        text,

        [
            r"cgpa\s*[:\-]?\s*(\d+(?:\.\d+)?)",
            r"gpa\s*[:\-]?\s*(\d+(?:\.\d+)?)"
        ],

        7.0

    )


    tenth = extract_number(

        text,

        [
            r"10th.*?(\d+(?:\.\d+)?)\s*%",
            r"tenth.*?(\d+(?:\.\d+)?)\s*%",
            r"sslc.*?(\d+(?:\.\d+)?)\s*%"
        ],

        70.0

    )


    twelfth = extract_number(

        text,

        [
            r"12th.*?(\d+(?:\.\d+)?)\s*%",
            r"twelfth.*?(\d+(?:\.\d+)?)\s*%",
            r"puc.*?(\d+(?:\.\d+)?)\s*%"
        ],

        70.0

    )


    communication = extract_number(

        text,

        [
            r"communication\s*skill\s*rating"
            r".*?(\d+(?:\.\d+)?)",

            r"communication"
            r".*?(\d+(?:\.\d+)?)"
        ],

        4.0

    )


    backlogs = extract_number(

        text,

        [
            r"backlogs?\s*[:\-]?\s*(\d+)",
            r"arrears?\s*[:\-]?\s*(\d+)"
        ],

        0

    )


    profile = {

        "name":
            extract_name(text),

        "cgpa":
            float(cgpa),

        "tenth":
            float(tenth),

        "twelfth":
            float(twelfth),

        "major_projects":
            count_projects(text),

        "workshops":
            count_certifications(text),

        "mini_projects":
            count_mini_projects(text),

        "skills":
            skills,

        "actual_skill_count":
            len(skills),

        "communication":
            float(communication),

        "internship":
            detect_yes_no(
                text,
                [
                    "internship",
                    "intern",
                    "interned"
                ]
            ),

        "hackathon":
            detect_yes_no(
                text,
                [
                    "hackathon",
                    "hackathons"
                ]
            ),

        "backlogs":
            int(backlogs)

    }


    # Keep values within sensible ranges

    profile["cgpa"] = min(
        10,
        max(
            0,
            profile["cgpa"]
        )
    )


    profile["tenth"] = min(
        100,
        max(
            0,
            profile["tenth"]
        )
    )


    profile["twelfth"] = min(
        100,
        max(
            0,
            profile["twelfth"]
        )
    )


    profile["communication"] = min(
        5,
        max(
            0,
            profile["communication"]
        )
    )


    profile["backlogs"] = max(
        0,
        profile["backlogs"]
    )


    # Dataset expects Skills around a numeric value.
    # Use detected skill count.
    profile["model_skill_count"] = min(
        20,
        profile["actual_skill_count"]
    )


    return profile


# ================================================================
# 26. BUILD MODEL INPUT
# ================================================================

def build_model_input(
    profile,
    placement_status=None
):

    data = {

        "CGPA":
            profile["cgpa"],

        "Major Projects":
            profile["major_projects"],

        "Workshops/Certificatios":
            profile["workshops"],

        "Mini Projects":
            profile["mini_projects"],

        "Skills":
            profile["model_skill_count"],

        "Communication Skill Rating":
            profile["communication"],

        "Internship":
            profile["internship"],

        "Hackathon":
            profile["hackathon"],

        "12th Percentage":
            profile["twelfth"],

        "10th Percentage":
            profile["tenth"],

        "backlogs":
            profile["backlogs"]

    }


    if placement_status is not None:

        data[
            "PlacementStatus"
        ] = placement_status


    return pd.DataFrame(
        [data]
    )


# ================================================================
# 27. PLACEMENT PREDICTION
# ================================================================

def predict_placement(
    profile
):

    data = build_model_input(
        profile
    )


    prediction = placement_model.predict(
        data
    )[0]


    probabilities = placement_model.predict_proba(
        data
    )[0]


    classes = list(
        placement_model.classes_
    )


    probability_map = dict(
        zip(
            classes,
            probabilities
        )
    )


    # Try to find the class representing placement
    placed_probability = 0


    for class_name, probability in probability_map.items():

        if str(class_name).strip().lower() in [

            "placed",

            "yes",

            "1",

            "true"

        ]:

            placed_probability = (
                probability * 100
            )

            break


    # If no "Placed" class exists,
    # use predicted-class probability.
    if placed_probability == 0:

        placed_probability = (
            max(probabilities) * 100
        )


    return (
        prediction,
        placed_probability
    )


# ================================================================
# 28. SALARY PREDICTION
# ================================================================

def predict_salary(
    profile
):

    # Salary dataset generally contains salary
    # for placed candidates.
    salary_input = build_model_input(
        profile,
        placement_status="Placed"
    )


    try:

        salary = salary_model.predict(
            salary_input
        )[0]


        return max(
            0,
            float(salary)
        )

    except Exception as error:

        print(
            "Salary prediction error:",
            error
        )

        return 0


# ================================================================
# 29. RESUME SCORE
# ================================================================

def calculate_resume_score(
    profile
):

    score = 0.0


    # CGPA
    score += min(
        20,
        profile["cgpa"] / 10 * 20
    )


    # Projects
    score += min(
        15,
        profile["major_projects"] * 5
    )


    # Mini projects
    score += min(
        8,
        profile["mini_projects"] * 2.67
    )


    # Certifications
    score += min(
        8,
        profile["workshops"] * 2.67
    )


    # Skills
    score += min(
        15,
        profile["actual_skill_count"] * 1.5
    )


    # Internship
    if profile["internship"] == "Yes":

        score += 10


    # Hackathon
    if profile["hackathon"] == "Yes":

        score += 7


    # Communication
    score += min(
        7,
        profile["communication"] / 5 * 7
    )


    # 12th
    score += min(
        5,
        profile["twelfth"] / 100 * 5
    )


    # 10th
    score += min(
        5,
        profile["tenth"] / 100 * 5
    )


    # Backlog penalty
    score -= min(
        15,
        profile["backlogs"] * 3
    )


    return int(
        round(
            max(
                0,
                min(
                    100,
                    score
                )
            )
        )
    )


# ================================================================
# 30. SKILL RECOMMENDATIONS
# ================================================================

SKILL_PRIORITY = [

    "Python",

    "Data Structures",

    "SQL",

    "Machine Learning",

    "Git/GitHub",

    "Deep Learning",

    "Computer Vision",

    "Data Science",

    "Cloud",

    "Web Development",

    "React",

    "DevOps"

]


def recommend_skills(
    profile
):

    current = set(
        profile["skills"]
    )


    missing = [

        skill

        for skill in SKILL_PRIORITY

        if skill not in current

    ]


    return missing[:6]


# ================================================================
# 31. PROJECT DATABASE
# ================================================================

PROJECT_DATABASE = {

    "Python": {

        "name":
            "AI Resume Analyzer",

        "difficulty":
            "Intermediate",

        "technology":
            "Python, Pandas, Scikit-learn, Gradio",

        "description":
            "Build an application that extracts information from resumes and provides career insights."

    },


    "Machine Learning": {

        "name":
            "Student Placement Prediction",

        "difficulty":
            "Intermediate",

        "technology":
            "Python, Pandas, Scikit-learn, Random Forest",

        "description":
            "Build a complete machine-learning placement prediction system."

    },


    "Deep Learning": {

        "name":
            "Image Classification System",

        "difficulty":
            "Intermediate",

        "technology":
            "Python, TensorFlow, Keras",

        "description":
            "Train a neural network to classify images."

    },


    "Computer Vision": {

        "name":
            "Real-Time Object Detection",

        "difficulty":
            "Advanced",

        "technology":
            "Python, OpenCV, YOLO",

        "description":
            "Create a real-time webcam object detection system."

    },


    "Data Science": {

        "name":
            "Placement Analytics Dashboard",

        "difficulty":
            "Intermediate",

        "technology":
            "Python, Pandas, Plotly",

        "description":
            "Create a dashboard that analyzes student placement data."

    },


    "SQL": {

        "name":
            "College Placement Database",

        "difficulty":
            "Intermediate",

        "technology":
            "SQL, MySQL",

        "description":
            "Design a relational database for students and companies."

    },


    "Data Structures": {

        "name":
            "Algorithm Visualizer",

        "difficulty":
            "Intermediate",

        "technology":
            "Python / JavaScript",

        "description":
            "Create a visual application for sorting and graph algorithms."

    },


    "Cloud": {

        "name":
            "Cloud Resume Deployment",

        "difficulty":
            "Intermediate",

        "technology":
            "AWS / Azure / GCP",

        "description":
            "Deploy a professional resume application to the cloud."

    },


    "Web Development": {

        "name":
            "Placement Portal",

        "difficulty":
            "Intermediate",

        "technology":
            "HTML, CSS, JavaScript",

        "description":
            "Build a responsive placement management portal."

    },


    "Git/GitHub": {

        "name":
            "Open Source Portfolio",

        "difficulty":
            "Beginner",

        "technology":
            "Git, GitHub",

        "description":
            "Create a professional GitHub portfolio."

    }

}


# ================================================================
# 32. PROJECT RECOMMENDATIONS
# ================================================================

def recommend_projects(
    profile
):

    missing = recommend_skills(
        profile
    )


    projects = []


    # Projects based on missing skills
    for skill in missing:

        if skill in PROJECT_DATABASE:

            projects.append(
                PROJECT_DATABASE[skill]
            )


    # Add projects based on current skills
    for skill in profile["skills"]:

        if skill in PROJECT_DATABASE:

            projects.append(
                PROJECT_DATABASE[skill]
            )


    unique_projects = []

    seen = set()


    for project in projects:

        if project["name"] not in seen:

            seen.add(
                project["name"]
            )

            unique_projects.append(
                project
            )


    return unique_projects[:6]


# ================================================================
# 33. SIX WEEK ROADMAP
# ================================================================

ROADMAP_ACTIONS = {

    "Python":
        "Strengthen Python, OOP, functions, file handling and data processing.",

    "Data Structures":
        "Practice arrays, strings, linked lists, stacks, queues, trees, graphs and sorting.",

    "SQL":
        "Practice SELECT, JOIN, GROUP BY, subqueries, indexes and database design.",

    "Machine Learning":
        "Learn preprocessing, feature engineering, classification, regression and model evaluation.",

    "Git/GitHub":
        "Build a professional GitHub profile and publish well-documented projects.",

    "Deep Learning":
        "Learn neural networks, CNNs, training, validation and model deployment.",

    "Computer Vision":
        "Practice OpenCV, image preprocessing and object detection.",

    "Data Science":
        "Practice Pandas, visualization, statistics and exploratory data analysis.",

    "Cloud":
        "Learn cloud fundamentals, deployment, storage and networking.",

    "Web Development":
        "Learn HTML, CSS and JavaScript and build a responsive project.",

    "React":
        "Learn components, props, state, hooks and API integration.",

    "DevOps":
        "Learn Docker, CI/CD, GitHub Actions and deployment."

}


def generate_roadmap(
    profile
):

    missing = recommend_skills(
        profile
    )


    roadmap = []


    for index, skill in enumerate(
        missing[:6]
    ):

        roadmap.append({

            "week":
                f"Week {index + 1}",

            "skill":
                skill,

            "task":
                ROADMAP_ACTIONS.get(
                    skill,
                    f"Develop practical {skill} skills."
                )

        })


    return roadmap


# ================================================================
# 34. PROGRESS BAR
# ================================================================

def progress_bar(
    value,
    label
):

    value = max(
        0,
        min(
            100,
            float(value)
        )
    )


    return f"""

    <div class="progress-wrapper">

        <div class="progress-title">

            <span>{label}</span>

            <span>
                {value:.1f}%
            </span>

        </div>


        <div class="progress-bg">

            <div
                class="progress-fill"
                style="width:{value}%"
            ></div>

        </div>

    </div>

    """


# ================================================================
# 35. CREATE PDF REPORT
# ================================================================

def create_report(

    profile,

    prediction,

    probability,

    salary,

    resume_score,

    roadmap,

    projects

):

    output_dir = (
        "/content/placement_reports"
    )


    os.makedirs(
        output_dir,
        exist_ok=True
    )


    safe_name = re.sub(

        r"[^A-Za-z0-9_-]",

        "_",

        profile["name"]

    )


    report_path = os.path.join(

        output_dir,

        f"{safe_name}_Placement_Report.pdf"

    )


    document = SimpleDocTemplate(

        report_path,

        pagesize=A4

    )


    styles = getSampleStyleSheet()

    story = []


    story.append(
        Paragraph(
            "AI Placement & Career Analysis Report",
            styles["Title"]
        )
    )


    story.append(
        Spacer(
            1,
            15
        )
    )


    story.append(
        Paragraph(
            f"Candidate: {profile['name']}",
            styles["Heading2"]
        )
    )


    story.append(
        Paragraph(
            "Generated: "
            + datetime.now().strftime(
                "%d-%m-%Y %H:%M"
            ),
            styles["Normal"]
        )
    )


    story.append(
        Spacer(
            1,
            15
        )
    )


    salary_text = (

        f"₹{salary:,.0f}"

        if salary > 0

        else "N/A"

    )


    table_data = [

        [
            "Metric",
            "Result"
        ],

        [
            "Placement Prediction",
            str(prediction)
        ],

        [
            "Placement Probability",
            f"{probability:.2f}%"
        ],

        [
            "Expected Salary",
            salary_text
        ],

        [
            "Resume Score",
            f"{resume_score}/100"
        ]

    ]


    table = Table(

        table_data,

        colWidths=[
            220,
            220
        ]

    )


    table.setStyle(

        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor(
                    "#111827"
                )
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                8
            )

        ])

    )


    story.append(
        table
    )


    story.append(
        Spacer(
            1,
            20
        )
    )


    story.append(
        Paragraph(
            "Detected Skills",
            styles["Heading2"]
        )
    )


    story.append(

        Paragraph(

            ", ".join(
                profile["skills"]
            )
            if profile["skills"]

            else
            "None detected",

            styles["Normal"]

        )

    )


    story.append(
        Spacer(
            1,
            15
        )
    )


    story.append(
        Paragraph(
            "Skill Development Roadmap",
            styles["Heading2"]
        )
    )


    for item in roadmap:

        story.append(

            Paragraph(

                f"<b>{item['week']} - "
                f"{item['skill']}</b>: "
                f"{item['task']}",

                styles["Normal"]

            )

        )


        story.append(
            Spacer(
                1,
                7
            )
        )


    story.append(
        Spacer(
            1,
            15
        )
    )


    story.append(
        Paragraph(
            "Recommended Projects",
            styles["Heading2"]
        )
    )


    for project in projects:

        story.append(

            Paragraph(

                f"<b>{project['name']}</b> "
                f"({project['difficulty']})"
                f"<br/>{project['description']}"
                f"<br/><b>Technology:</b> "
                f"{project['technology']}",

                styles["Normal"]

            )

        )


        story.append(
            Spacer(
                1,
                8
            )
        )


    story.append(
        Spacer(
            1,
            15
        )
    )


    story.append(

        Paragraph(

            "Disclaimer: Placement probability "
            "and salary are machine-learning "
            "estimates based on the supplied "
            "training dataset. They are not "
            "guarantees.",

            styles["Normal"]

        )

    )


    document.build(
        story
    )


    return report_path


# ================================================================
# 36. WEBSITE CSS
# ================================================================

CUSTOM_CSS = """

body {

    background:
        radial-gradient(
            circle at 20% 10%,
            rgba(99,102,241,.18),
            transparent 35%
        ),
        radial-gradient(
            circle at 80% 20%,
            rgba(14,165,233,.15),
            transparent 35%
        ),
        #050816 !important;

    color:
        #f8fafc !important;

}


.gradio-container {

    max-width:
        1400px !important;

    margin:
        auto !important;

    background:
        #050816 !important;

}


.app-header {

    padding:
        45px 30px;

    border-radius:
        30px;

    margin-bottom:
        25px;

    background:
        linear-gradient(
            135deg,
            rgba(99,102,241,.18),
            rgba(14,165,233,.10)
        );

    border:
        1px solid
        rgba(255,255,255,.08);

    box-shadow:
        0 25px 80px
        rgba(0,0,0,.35);

    overflow:
        hidden;

}


.app-title {

    font-size:
        48px;

    font-weight:
        900;

    letter-spacing:
        -2px;

    background:
        linear-gradient(
            90deg,
            #ffffff,
            #a5b4fc,
            #67e8f9
        );

    -webkit-background-clip:
        text;

    -webkit-text-fill-color:
        transparent;

}


.app-subtitle {

    color:
        #94a3b8;

    font-size:
        18px;

    max-width:
        850px;

    margin-top:
        12px;

    line-height:
        1.7;

}


.hero {

    padding:
        45px;

    border-radius:
        30px;

    margin-top:
        20px;

    background:
        linear-gradient(
            135deg,
            rgba(79,70,229,.25),
            rgba(8,145,178,.15)
        );

    border:
        1px solid
        rgba(255,255,255,.08);

}


.eyebrow {

    color:
        #67e8f9;

    font-size:
        12px;

    letter-spacing:
        3px;

    font-weight:
        800;

}


.hero h1 {

    font-size:
        40px;

    margin:
        10px 0;

}


.hero h1 span {

    background:
        linear-gradient(
            90deg,
            #818cf8,
            #22d3ee
        );

    -webkit-background-clip:
        text;

    -webkit-text-fill-color:
        transparent;

}


.hero p {

    color:
        #94a3b8;

    font-size:
        16px;

    line-height:
        1.7;

}


.stats-grid {

    display:
        grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap:
        18px;

    margin-top:
        20px;

}


.stat-card {

    display:
        flex;

    align-items:
        center;

    gap:
        18px;

    padding:
        25px;

    border-radius:
        24px;

    background:
        rgba(15,23,42,.75);

    border:
        1px solid
        rgba(255,255,255,.07);

    transition:
        transform .25s ease,
        box-shadow .25s ease;

}


.stat-card:hover {

    transform:
        translateY(-6px);

    box-shadow:
        0 20px 50px
        rgba(0,0,0,.25);

}


.stat-icon {

    width:
        52px;

    height:
        52px;

    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

    border-radius:
        17px;

    background:
        rgba(99,102,241,.13);

    font-size:
        25px;

}


.stat-label {

    color:
        #94a3b8;

    font-size:
        11px;

}


.stat-number {

    font-size:
        24px;

    font-weight:
        800;

    margin-top:
        5px;

}


.stat-number.small {

    font-size:
        17px;

}


.section {

    margin-top:
        25px;

    padding:
        30px;

    border-radius:
        28px;

    background:
        rgba(15,23,42,.65);

    border:
        1px solid
        rgba(255,255,255,.06);

}


.section-title {

    font-size:
        21px;

    font-weight:
        800;

    margin-bottom:
        22px;

}


.profile-grid {

    display:
        grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap:
        15px;

}


.info-card {

    padding:
        20px;

    border-radius:
        18px;

    background:
        rgba(30,41,59,.55);

    border:
        1px solid
        rgba(255,255,255,.05);

}


.info-card span {

    display:
        block;

    color:
        #94a3b8;

    font-size:
        12px;

    margin-bottom:
        8px;

}


.info-card strong {

    font-size:
        20px;

}


.skills-container {

    display:
        flex;

    flex-wrap:
        wrap;

    gap:
        10px;

}


.skill-pill,
.missing-pill {

    padding:
        9px 15px;

    border-radius:
        999px;

    font-size:
        13px;

    font-weight:
        700;

}


.skill-pill {

    background:
        rgba(34,197,94,.12);

    color:
        #86efac;

}


.missing-pill {

    background:
        rgba(99,102,241,.13);

    color:
        #c7d2fe;

}


.progress-wrapper {

    margin:
        20px 0;

}


.progress-title {

    display:
        flex;

    justify-content:
        space-between;

    color:
        #cbd5e1;

    font-size:
        13px;

    margin-bottom:
        8px;

}


.progress-bg {

    width:
        100%;

    height:
        9px;

    border-radius:
        999px;

    background:
        #1e293b;

    overflow:
        hidden;

}


.progress-fill {

    height:
        100%;

    border-radius:
        999px;

    background:
        linear-gradient(
            90deg,
            #6366f1,
            #22d3ee
        );

    animation:
        growBar 1.3s ease;

}


@keyframes growBar {

    from {

        width:
            0 !important;

    }

}


.roadmap-grid {

    display:
        grid;

    grid-template-columns:
        repeat(3, 1fr);

    gap:
        15px;

}


.roadmap-card {

    padding:
        23px;

    border-radius:
        20px;

    background:
        rgba(30,41,59,.8);

    border:
        1px solid
        rgba(255,255,255,.06);

    transition:
        transform .25s ease;

}


.roadmap-card:hover {

    transform:
        translateY(-6px);

}


.roadmap-card .week {

    color:
        #67e8f9;

    font-size:
        12px;

    font-weight:
        800;

}


.roadmap-card h3 {

    margin:
        8px 0;

}


.roadmap-card p {

    color:
        #94a3b8;

    font-size:
        13px;

    line-height:
        1.6;

}


.project-grid {

    display:
        grid;

    grid-template-columns:
        repeat(2, 1fr);

    gap:
        18px;

}


.project-card {

    padding:
        25px;

    border-radius:
        22px;

    background:
        rgba(30,41,59,.6);

    border:
        1px solid
        rgba(255,255,255,.07);

    transition:
        transform .25s ease;

}


.project-card:hover {

    transform:
        translateY(-6px);

}


.project-top {

    display:
        flex;

    align-items:
        center;

    justify-content:
        space-between;

}


.project-card h3 {

    margin:
        0;

}


.project-card p {

    color:
        #94a3b8;

    line-height:
        1.6;

    font-size:
        14px;

}


.difficulty {

    padding:
        5px 10px;

    border-radius:
        999px;

    background:
        rgba(99,102,241,.15);

    color:
        #c7d2fe;

    font-size:
        11px;

}


.tech-stack {

    margin-top:
        15px;

    color:
        #67e8f9;

    font-size:
        13px;

}


.empty-state,
.error-box {

    padding:
        50px;

    text-align:
        center;

    border-radius:
        25px;

    background:
        rgba(15,23,42,.8);

    color:
        #94a3b8;

}


.error-box {

    color:
        #fca5a5;

}


button {

    border-radius:
        14px !important;

    transition:
        transform .2s ease !important;

}


button:hover {

    transform:
        translateY(-2px);

}


@media(max-width:900px) {

    .stats-grid {

        grid-template-columns:
            repeat(2, 1fr);

    }

    .profile-grid {

        grid-template-columns:
            repeat(2, 1fr);

    }

    .roadmap-grid {

        grid-template-columns:
            1fr;

    }

    .project-grid {

        grid-template-columns:
            1fr;

    }

}


@media(max-width:600px) {

    .app-title {

        font-size:
            32px;

    }

    .stats-grid {

        grid-template-columns:
            1fr;

    }

    .profile-grid {

        grid-template-columns:
            1fr;

    }

}

"""


# ================================================================
# 37. MAIN DASHBOARD FUNCTION
# ================================================================

def create_dashboard(
    file_path
):

    try:

        print("\n")
        print("=" * 70)
        print("🚀 ANALYZING RESUME")
        print("=" * 70)


        # --------------------------------------------------------
        # Check upload
        # --------------------------------------------------------

        if file_path is None:

            raise ValueError(
                "No resume was uploaded."
            )


        print(
            "Resume:",
            file_path
        )


        # --------------------------------------------------------
        # Extract text
        # --------------------------------------------------------

        print(
            "\n1️⃣ Extracting resume text..."
        )


        text = extract_text_from_file(
            file_path
        )


        if not text or len(
            text.strip()
        ) < 30:

            raise ValueError(

                "Could not extract enough "
                "text from this resume. "
                "Try a text-based PDF, DOCX "
                "or TXT file."

            )


        print(
            "✓ Text extracted:",
            len(text),
            "characters"
        )


        # --------------------------------------------------------
        # Analyze profile
        # --------------------------------------------------------

        print(
            "\n2️⃣ Analyzing resume..."
        )


        profile = analyze_resume(
            text
        )


        print(
            "✓ Candidate:",
            profile["name"]
        )

        print(
            "✓ Skills:",
            profile["skills"]
        )


        # --------------------------------------------------------
        # Placement
        # --------------------------------------------------------

        print(
            "\n3️⃣ Predicting placement..."
        )


        prediction, probability = (
            predict_placement(
                profile
            )
        )


        print(
            "✓ Prediction:",
            prediction
        )

        print(
            "✓ Probability:",
            round(
                probability,
                2
            ),
            "%"
        )


        # --------------------------------------------------------
        # Salary
        # --------------------------------------------------------

        print(
            "\n4️⃣ Predicting salary..."
        )


        salary = predict_salary(
            profile
        )


        print(
            "✓ Salary:",
            salary
        )


        # --------------------------------------------------------
        # Resume score
        # --------------------------------------------------------

        print(
            "\n5️⃣ Calculating resume score..."
        )


        resume_score = calculate_resume_score(
            profile
        )


        print(
            "✓ Resume score:",
            resume_score
        )


        # --------------------------------------------------------
        # Skill gap
        # --------------------------------------------------------

        missing_skills = recommend_skills(
            profile
        )


        # --------------------------------------------------------
        # Roadmap
        # --------------------------------------------------------

        roadmap = generate_roadmap(
            profile
        )


        # --------------------------------------------------------
        # Projects
        # --------------------------------------------------------

        projects = recommend_projects(
            profile
        )


        # --------------------------------------------------------
        # HTML skill pills
        # --------------------------------------------------------

        if profile["skills"]:

            skills_html = "".join(

                f'<span class="skill-pill">'
                f'{skill}'
                f'</span>'

                for skill in profile["skills"]

            )

        else:

            skills_html = (
                '<span>'
                'No skills detected'
                '</span>'
            )


        if missing_skills:

            missing_html = "".join(

                f'<span class="missing-pill">'
                f'{skill}'
                f'</span>'

                for skill in missing_skills

            )

        else:

            missing_html = (
                '<span>'
                'No major skill gaps detected'
                '</span>'
            )


        # --------------------------------------------------------
        # Roadmap HTML
        # --------------------------------------------------------

        roadmap_html = ""


        for item in roadmap:

            roadmap_html += f"""

            <div class="roadmap-card">

                <div class="week">
                    {item['week']}
                </div>

                <h3>
                    {item['skill']}
                </h3>

                <p>
                    {item['task']}
                </p>

            </div>

            """


        if not roadmap_html:

            roadmap_html = """

            <div class="empty-state">

                No major skill gaps were detected.

            </div>

            """


        # --------------------------------------------------------
        # Project HTML
        # --------------------------------------------------------

        project_html = ""


        for project in projects:

            project_html += f"""

            <div class="project-card">

                <div class="project-top">

                    <h3>
                        {project['name']}
                    </h3>

                    <span class="difficulty">
                        {project['difficulty']}
                    </span>

                </div>

                <p>
                    {project['description']}
                </p>

                <div class="tech-stack">

                    🛠️ {project['technology']}

                </div>

            </div>

            """


        # --------------------------------------------------------
        # Salary display
        # --------------------------------------------------------

        salary_display = (

            f"₹{salary:,.0f}"

            if salary > 0

            else "N/A"

        )


        # --------------------------------------------------------
        # DASHBOARD HTML
        # --------------------------------------------------------

        dashboard_html = f"""

        <div class="dashboard">


            <div class="hero">

                <div class="eyebrow">
                    AI CAREER ANALYSIS
                </div>

                <h1>

                    Welcome,
                    <span>
                        {profile['name']}
                    </span>

                </h1>

                <p>

                    Your resume has been analyzed using
                    the trained placement and salary
                    machine-learning models.

                </p>

            </div>


            <div class="stats-grid">


                <div class="stat-card">

                    <div class="stat-icon">
                        🎯
                    </div>

                    <div>

                        <div class="stat-label">
                            PLACEMENT PREDICTION
                        </div>

                        <div class="stat-number">
                            {prediction}
                        </div>

                    </div>

                </div>


                <div class="stat-card">

                    <div class="stat-icon">
                        📈
                    </div>

                    <div>

                        <div class="stat-label">
                            PLACEMENT PROBABILITY
                        </div>

                        <div class="stat-number">
                            {probability:.1f}%
                        </div>

                    </div>

                </div>


                <div class="stat-card">

                    <div class="stat-icon">
                        💰
                    </div>

                    <div>

                        <div class="stat-label">
                            EXPECTED SALARY
                        </div>

                        <div class="stat-number small">
                            {salary_display}
                        </div>

                    </div>

                </div>


                <div class="stat-card">

                    <div class="stat-icon">
                        ⭐
                    </div>

                    <div>

                        <div class="stat-label">
                            RESUME SCORE
                        </div>

                        <div class="stat-number">
                            {resume_score}/100
                        </div>

                    </div>

                </div>


            </div>


            <div class="section">

                <div class="section-title">
                    📋 Candidate Profile
                </div>


                <div class="profile-grid">


                    <div class="info-card">

                        <span>
                            CGPA
                        </span>

                        <strong>
                            {profile['cgpa']}
                        </strong>

                    </div>


                    <div class="info-card">

                        <span>
                            10th Percentage
                        </span>

                        <strong>
                            {profile['tenth']}%
                        </strong>

                    </div>


                    <div class="info-card">

                        <span>
                            12th Percentage
                        </span>

                        <strong>
                            {profile['twelfth']}%
                        </strong>

                    </div>


                    <div class="info-card">

                        <span>
                            Backlogs
                        </span>

                        <strong>
                            {profile['backlogs']}
                        </strong>

                    </div>


                    <div class="info-card">

                        <span>
                            Major Projects
                        </span>

                        <strong>
                            {profile['major_projects']}
                        </strong>

                    </div>


                    <div class="info-card">

                        <span>
                            Mini Projects
                        </span>

                        <strong>
                            {profile['mini_projects']}
                        </strong>

                    </div>


                    <div class="info-card">

                        <span>
                            Certifications
                        </span>

                        <strong>
                            {profile['workshops']}
                        </strong>

                    </div>


                    <div class="info-card">

                        <span>
                            Internship
                        </span>

                        <strong>
                            {profile['internship']}
                        </strong>

                    </div>


                    <div class="info-card">

                        <span>
                            Hackathon
                        </span>

                        <strong>
                            {profile['hackathon']}
                        </strong>

                    </div>


                    <div class="info-card">

                        <span>
                            Communication
                        </span>

                        <strong>
                            {profile['communication']}/5
                        </strong>

                    </div>


                </div>

            </div>


            <div class="section">

                <div class="section-title">
                    🧠 Detected Skills
                </div>

                <div class="skills-container">

                    {skills_html}

                </div>

            </div>


            <div class="section">

                <div class="section-title">
                    🎯 Recommended Skills
                </div>

                <div class="skills-container">

                    {missing_html}

                </div>

            </div>


            <div class="section">

                <div class="section-title">
                    📊 Career Readiness
                </div>


                {progress_bar(
                    probability,
                    "Placement Probability"
                )}


                {progress_bar(
                    resume_score,
                    "Resume Strength"
                )}


                {progress_bar(
                    min(
                        100,
                        profile["actual_skill_count"]
                        / 15
                        * 100
                    ),
                    "Technical Skill Coverage"
                )}


                {progress_bar(
                    min(
                        100,
                        profile["major_projects"]
                        / 3
                        * 100
                    ),
                    "Project Experience"
                )}

            </div>


            <div class="section">

                <div class="section-title">
                    🚀 6-Week Skill Development Roadmap
                </div>


                <div class="roadmap-grid">

                    {roadmap_html}

                </div>

            </div>


            <div class="section">

                <div class="section-title">
                    💡 Recommended Projects
                </div>


                <div class="project-grid">

                    {project_html}

                </div>

            </div>


            <div class="disclaimer">

                ⚠️ <b>Important:</b>

                The placement probability and salary
                are machine-learning estimates based
                on the training dataset and extracted
                resume information. They are not
                guarantees.

            </div>


        </div>

        """


        # --------------------------------------------------------
        # PROFILE MARKDOWN
        # --------------------------------------------------------

        profile_markdown = f"""

## 👤 {profile['name']}

| Information | Value |
|---|---:|
| CGPA | {profile['cgpa']} |
| 10th Percentage | {profile['tenth']}% |
| 12th Percentage | {profile['twelfth']}% |
| Backlogs | {profile['backlogs']} |
| Major Projects | {profile['major_projects']} |
| Mini Projects | {profile['mini_projects']} |
| Certifications / Workshops | {profile['workshops']} |
| Internship | {profile['internship']} |
| Hackathon | {profile['hackathon']} |
| Communication | {profile['communication']}/5 |

### 🧠 Detected Skills

{", ".join(profile['skills']) if profile['skills'] else "None detected"}

### 🎯 Recommended Skills

{", ".join(missing_skills) if missing_skills else "No major skill gaps detected"}

"""


        # --------------------------------------------------------
        # MODEL MARKDOWN
        # --------------------------------------------------------

        prediction_markdown = f"""

## 🎯 Placement Prediction

**Prediction:** `{prediction}`

**Placement Probability:** `{probability:.2f}%`

**Expected Salary:** `{salary_display}`

**Resume Score:** `{resume_score}/100`

---

## 📊 Placement Model Performance

**Accuracy:** `{placement_accuracy * 100:.2f}%`

**Precision:** `{placement_precision * 100:.2f}%`

**Recall:** `{placement_recall * 100:.2f}%`

**F1 Score:** `{placement_f1 * 100:.2f}%`

---

## 💰 Salary Model Performance

**MAE:** `₹{salary_mae:,.2f}`

**RMSE:** `₹{salary_rmse:,.2f}`

**R²:** `{salary_r2:.4f}`

"""


        # --------------------------------------------------------
        # CREATE PDF
        # --------------------------------------------------------

        print(
            "\n6️⃣ Creating PDF report..."
        )


        report_path = create_report(

            profile,

            prediction,

            probability,

            salary,

            resume_score,

            roadmap,

            projects

        )


        print(
            "✓ PDF created:",
            report_path
        )


        print(
            "\n" + "=" * 70
        )

        print(
            "✅ ANALYSIS COMPLETED"
        )

        print(
            "=" * 70
        )


        return (

            dashboard_html,

            profile_markdown,

            prediction_markdown,

            report_path

        )


    except Exception as error:

        print(
            "\n" + "=" * 70
        )

        print(
            "❌ ERROR WHILE ANALYZING RESUME"
        )

        print(
            "=" * 70
        )

        print(
            str(error)
        )

        traceback.print_exc()


        error_html = f"""

        <div class="error-box">

            <h2>
                ❌ Analysis Failed
            </h2>

            <p>
                {str(error)}
            </p>

            <p>
                Check the Google Colab output
                below the cell for the detailed
                error.
            </p>

        </div>

        """


        return (

            error_html,

            "❌ Resume analysis failed.",

            f"""

### Error

`{str(error)}`

Please check the Colab console for
the complete traceback.

""",

            None

        )


# ================================================================
# 38. BUILD GRADIO WEBSITE
# ================================================================

with gr.Blocks(

    css=CUSTOM_CSS,

    title=
        "AI Placement & Career Analyzer"

) as app:


    # ------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------

    gr.HTML(

        """

        <div class="app-header">

            <div class="app-title">

                🚀 AI Placement & Career Analyzer

            </div>

            <div class="app-subtitle">

                Upload your resume and get a
                machine-learning placement prediction,
                salary estimate, resume score,
                skill-gap analysis, personalized
                development roadmap and project
                recommendations.

            </div>

        </div>

        """

    )


    with gr.Row():


        # --------------------------------------------------------
        # UPLOAD PANEL
        # --------------------------------------------------------

        with gr.Column(
            scale=1
        ):


            gr.Markdown(

                """

## 📄 Upload Resume

Supported formats:

**PDF • DOCX • TXT • MD • PNG • JPG • JPEG • WEBP**

The system automatically extracts information
from your resume.

                """

            )


            resume_file = gr.File(

                label=
                    "Upload your Resume",

                file_types=[

                    ".pdf",

                    ".docx",

                    ".txt",

                    ".md",

                    ".png",

                    ".jpg",

                    ".jpeg",

                    ".webp"

                ],

                type=
                    "filepath"

            )


            analyze_button = gr.Button(

                "🚀 ANALYZE MY RESUME",

                variant=
                    "primary",

                size=
                    "lg"

            )


            gr.Markdown(

                """

### How it works

**1. Upload Resume**

↓

**2. Extract Information**

↓

**3. Machine Learning Prediction**

↓

**4. Salary Estimation**

↓

**5. Skill Gap Analysis**

↓

**6. Career Roadmap**

                """

            )


        # --------------------------------------------------------
        # DASHBOARD
        # --------------------------------------------------------

        with gr.Column(
            scale=3
        ):


            dashboard = gr.HTML(

                """

                <div class="empty-state">

                    <h2>
                        👋 Ready when you are
                    </h2>

                    <p>
                        Upload your resume and click
                        <b>Analyze My Resume</b>.
                    </p>

                </div>

                """

            )


    # ------------------------------------------------------------
    # PROFILE DETAILS
    # ------------------------------------------------------------

    with gr.Accordion(

        "📋 Extracted Resume Information",

        open=False

    ):

        profile_output = gr.Markdown()


    # ------------------------------------------------------------
    # MODEL DETAILS
    # ------------------------------------------------------------

    with gr.Accordion(

        "🎯 Machine Learning Prediction Details",

        open=False

    ):

        prediction_output = gr.Markdown()


    # ------------------------------------------------------------
    # REPORT
    # ------------------------------------------------------------

    report_output = gr.File(

        label=
            "📥 Download Full Placement Report"

    )


    # ============================================================
    # 🔥 THIS IS THE FUNCTION CALL
    # ============================================================

    analyze_button.click(

        fn=create_dashboard,

        inputs=resume_file,

        outputs=[

            dashboard,

            profile_output,

            prediction_output,

            report_output

        ]

    )


# ================================================================
# 39. START WEBSITE
# ================================================================

print("\n")
print("=" * 70)
print("🚀 AI PLACEMENT & CAREER ANALYZER")
print("=" * 70)

print(
    "\nPlacement Model Accuracy:",
    f"{placement_accuracy * 100:.2f}%"
)

print(
    "Salary Model MAE:",
    f"₹{salary_mae:,.2f}"
)

print(
    "Salary Model R²:",
    f"{salary_r2:.4f}"
)

print("\n" + "=" * 70)
print("🌐 STARTING GRADIO WEBSITE")
print("=" * 70)


app.launch(

    share=True,

    debug=True

)