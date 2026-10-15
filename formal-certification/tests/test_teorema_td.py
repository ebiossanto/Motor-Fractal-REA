#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Testes do Teorema TD + LB1/LB2 (FCT-ADV-006)."""
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "experiments"
OUT = BASE / "out_teorema_td.json"


def test_teorema_executa_e_gera_saida():
    r = subprocess.run([sys.executable, str(BASE / "teorema_transicao_dupla_check.py")],
                       capture_output=True, text=True, cwd=str(BASE.parent.parent))
    assert r.returncode == 0, r.stderr[-2000:]
    assert OUT.exists()


def test_T1_simbolico():
    d = json.loads(OUT.read_text(encoding="utf-8"))["T1"]
    assert d["derivada_ok"] and d["razao_igual_4"] and d["instancias_A_B_ok"]


def test_LB1_monotono_sem_violacao():
    d = json.loads(OUT.read_text(encoding="utf-8"))["LB1"]
    for nome in ("A", "B"):
        assert d[nome]["monotono"] and d[nome]["pior_violacao"] >= -1e-12


def test_LB2_exato_e_numerico():
    d = json.loads(OUT.read_text(encoding="utf-8"))["LB2"]
    assert d["n3_forma_exata_ok"] and d["ok"] and d["pior_violacao_3000_grades"] >= -1e-12


def test_tudo_ok():
    assert json.loads(OUT.read_text(encoding="utf-8"))["tudo_ok"] is True
