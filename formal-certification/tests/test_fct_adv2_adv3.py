#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Testes das frentes FCT-ADV-002 (regimes) e FCT-ADV-003 (calibração H)."""
import csv
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "experiments"
REG_JSON = BASE / "out_fct_rho_regimes.json"
REG_CSV = BASE / "out_fct_rho_series.csv"
CAL_JSON = BASE / "out_hurst_calibration.json"
CAL_CSV = BASE / "out_hurst_calibration.csv"


def test_tracker_executa_e_gera_saidas():
    r = subprocess.run([sys.executable, str(BASE / "fct_rho_regime_tracker.py")],
                       capture_output=True, text=True, cwd=str(BASE.parent.parent))
    assert r.returncode == 0, r.stderr[-2000:]
    assert REG_JSON.exists() and REG_CSV.exists()


def test_regimes_coerentes():
    d = json.loads(REG_JSON.read_text(encoding="utf-8"))
    assert d["n"] == 300
    regs = d["regimes"]
    # limiar maior ⇒ fração acima menor ou igual
    assert regs["break_even_A"]["fracao_acima"] >= regs["half_mit_A_doc"]["fracao_acima"]
    assert regs["half_mit_A_doc"]["fracao_acima"] >= regs["break_even_B"]["fracao_acima"]
    assert regs["break_even_B"]["n_episodios"] == 9
    with open(REG_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 300
    assert set(rows[0].keys()) == {"t_s", "cpu", "rho", "acima_BE_A", "acima_HM_doc", "acima_BE_B"}


def test_calibracao_executa_e_gera_saidas():
    r = subprocess.run([sys.executable, str(BASE / "hurst_estimator_calibration.py")],
                       capture_output=True, text=True, cwd=str(BASE.parent.parent))
    assert r.returncode == 0, r.stderr[-2000:]
    assert CAL_JSON.exists() and CAL_CSV.exists()


def test_calibracao_ranking_e_correcao():
    d = json.loads(CAL_JSON.read_text(encoding="utf-8"))
    assert d["ranking_robustez"][0] in ("varlag", "higuchi")
    assert d["ranking_robustez"][-1] in ("dfa", "box2d")
    for rot in ("raw", "donoho"):
        c = d["H_real_corrigido"][rot]["consenso_corrigido"]
        assert c is not None and 0.0 < c < 1.0, (rot, c)
    with open(CAL_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 5 * 4 * 5  # H_grid × condições × estimadores
    assert {r["est"] for r in rows} == {"higuchi", "rs", "dfa", "varlag", "box2d"}
