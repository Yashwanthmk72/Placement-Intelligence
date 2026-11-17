"""Run from the project folder:  python -m pytest -q   (pip install pytest first)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from app import engine, world
D = Path(__file__).resolve().parents[1] / "data" / "datasets"
M = engine.train_models(D / "Placement_Prediction_data.csv", D / "Salary_prediction_data.csv")
STRONG = dict(cgpa=9.2, major_projects=2, workshops=3, mini_projects=2, skills_count=9, communication=4.8, internship="Yes", hackathon="Yes", twelfth=90, tenth=92, backlogs=0)
WEAK = dict(cgpa=6.0, major_projects=0, workshops=0, mini_projects=0, skills_count=2, communication=3, internship="No", hackathon="No", twelfth=55, tenth=55, backlogs=4)

def test_models_and_oob():
    assert M["placement_metrics"]["accuracy"] > 60 and len(M["salary_oob"]) > 100

def test_strong_beats_weak():
    ps, pw = engine.predict_profile(STRONG, M), engine.predict_profile(WEAK, M)
    assert ps["probability"] > pw["probability"]

def test_percentile_monotonic_and_bounded():
    qs = [world.percentile(s, M["salary_oob"]) for s in (0, 5e5, 1e6, 5e6)]
    assert qs == sorted(qs) and 0 <= qs[0] and qs[-1] <= 1

def test_estimates_increase_with_percentile():
    lo, hi = world.estimate_all(0.1), world.estimate_all(0.9)
    assert all(hi[k]["gross_inr"] > lo[k]["gross_inr"] for k in lo)

def test_country_table_sane():
    ids = [c["id"] for c in world.COUNTRIES]
    assert len(ids) == len(set(ids)) >= 30 - 1
    for c in world.COUNTRIES:
        assert c["low"] < c["typical"] < c["high"] and 1 <= c["ease"] <= 5 and c["currency"] in world.FX_INR and 0 <= c["tax_pct"] < 60

def test_ats():
    r = engine.ats_check("Python SQL pandas projects education skills github.com/x a@b.com 9876543210", "Data Analyst")
    assert 0 <= r["score"] <= 100 and "sql" in r["matched"]
