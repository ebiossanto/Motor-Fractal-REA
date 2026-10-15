#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teste da auditoria FCT: travessias analíticas × numéricas + H válido."""
import csv
import json
import math
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "experiments"
OUT_JSON = BASE / "out_fct_audit.json"
OUT_SWEEP = BASE / "out_fct_rho_sweep.csv"


def test_auditoria_executa_e_gera_saidas():
    r = subprocess.run([sys.executable, str(BASE / "fct_phase_transition_audit.py")],
                       capture_output=True, text=True, cwd=str(BASE.parent.parent))
    assert r.returncode == 0, r.stderr[-2000:]
    assert OUT_JSON.exists() and OUT_SWEEP.exists()


def test_travessias_analitico_vs_numerico():
    d = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    a, b = d["modelos"]["A_doc_absoluto"], d["modelos"]["B_gk_relativo"]
    assert abs(a["break_even_analitico"] - 1 / 16) < 1e-12
    assert abs(a["half_mitigation_analitica"] - 0.25) < 1e-12
    assert abs(b["break_even_analitico"] - (11 / 12) ** 4) < 1e-12
    for k in ("break_even_numerico", "half_mitigation_numerica"):
        assert abs(a[k] - (a["break_even_analitico"] if "break" in k else a["half_mitigation_analitica"])) < 0.005
    assert abs(b["break_even_numerico"] - b["break_even_analitico"]) < 0.005


def test_rho_c_025_nao_e_break_even():
    d = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    a = d["modelos"]["A_doc_absoluto"]
    b = d["modelos"]["B_gk_relativo"]
    assert abs(0.25 - a["break_even_analitico"]) > 0.1
    assert abs(0.25 - b["break_even_analitico"]) > 0.1


def test_hurst_valido_e_bug_variance_morto():
    d = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    for serie in ("raw", "donoho_surrogate", "tail_block"):
        h = d["hurst"][serie]
        for k in ("H_higuchi", "H_rs", "H_dfa", "H_variance_corr"):
            v = h[k]
            if v is not None:
                assert -0.5 < v < 1.6, (serie, k, v)  # estimador pode falhar; consenso deve ser (0,1)
        c = h["H_consenso_mediana"]
        assert c is not None and 0.0 < c < 1.0, (serie, c)


def test_sweep_csv_consistente():
    with open(OUT_SWEEP, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 99
    r0 = rows[0]
    assert abs(float(r0["rho"]) - 0.01) < 1e-9
    # monotonicidade: mitigação cresce com rho nos dois modelos
    m_a = [float(r["mitig_A"]) for r in rows]
    m_b = [float(r["mitig_B"]) for r in rows]
    assert m_a[-1] > m_a[0] and m_b[-1] > m_b[0]
