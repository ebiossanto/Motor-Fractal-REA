#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Testes das frentes FCT-ADV-004 (boxdim adaptativo) e FCT-ADV-005 (F3/Spearman)."""
import csv
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "experiments"
BX_JSON = BASE / "out_boxdim_adaptive.json"
BX_CSV = BASE / "out_boxdim_adaptive.csv"
RG_JSON = BASE / "out_f3_philen_regression.json"
RG_CSV = BASE / "out_fct_philen_series.csv"
SP_JSON = BASE / "out_spearman_sigma_theta.json"
SP_CSV = BASE / "out_spearman_blocks.csv"


def test_boxdim_executa_e_gera_saidas():
    r = subprocess.run([sys.executable, str(BASE / "fct_boxdim_adaptive.py")],
                       capture_output=True, text=True, cwd=str(BASE.parent.parent))
    assert r.returncode == 0, r.stderr[-2000:]
    assert BX_JSON.exists() and BX_CSV.exists()


def test_boxdim_resgate_honesto():
    d = json.loads(BX_JSON.read_text(encoding="utf-8"))
    with open(BX_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 6  # 3 series x 2 metodos
    notas = [r["nota"] for r in rows]
    assert notas.count("resgatado") == 5
    assert notas.count("trivial (saturado: N(k)=k)") == 1
    for r in rows:
        if r["nota"] == "resgatado":
            assert r["D"] is not None and float(r["R2"]) >= 0.9


def test_f3_executa_e_gera_saidas():
    r = subprocess.run([sys.executable, str(BASE / "f3_philen_spearman.py")],
                       capture_output=True, text=True, cwd=str(BASE.parent.parent))
    assert r.returncode == 0, r.stderr[-2000:]
    for p in (RG_JSON, RG_CSV, SP_JSON, SP_CSV):
        assert p.exists()


def test_f3_regressao_e_spearman():
    d = json.loads(RG_JSON.read_text(encoding="utf-8"))
    assert len(d["pontos"]) == 6  # phi 6,7,8,9,10,12
    assert len(d["legado_referencia_H"]) == 4
    with open(RG_CSV, newline="", encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == 10
    s = json.loads(SP_JSON.read_text(encoding="utf-8"))
    assert len(s["blocos"]) == 48
    assert s["n_significativos"] == 0
    with open(SP_CSV, newline="", encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == 48
