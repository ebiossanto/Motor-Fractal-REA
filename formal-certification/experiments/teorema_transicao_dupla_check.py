#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
teorema_transicao_dupla_check.py — Verificação por máquina do Teorema TD + LB1/LB2.
====================================================================================
Verifica (sympy simbólico + grade numérica + indução numérica):
 T1: M(rho)=1-q^2/sqrt(rho); M'=q^2/(2 rho^3/2); zeros rho*=q^4, rho_1/2=4q^4;
     razão rho_1/2/rho*=4; instâncias A (q=1/2) e B (q=(11/12)^2).
 LB1: monotonicidade => M(rho)>=1-q^2/sqrt(rho0) para rho>=rho0 (grade).
 LB2: prod(1+a_k)>=1+sum(a_k) em grades aleatórias (semente 11) + caso n=3 simbólico.
Saídas: out_teorema_td.json (+ console). Determinístico (seed 11).
Uso: python formal-certification/experiments/teorema_transicao_dupla_check.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import sympy as sp

BASE = Path(__file__).resolve().parent
OUT = BASE / "out_teorema_td.json"
RHO = np.linspace(0.001, 0.999, 2000)


def check_T1() -> dict:
    rho, q = sp.symbols("rho q", positive=True)
    M = 1 - q**2 / sp.sqrt(rho)
    dM = sp.simplify(sp.diff(M, rho) - q**2 / (2 * rho**sp.Rational(3, 2)))
    be = sp.solve(sp.Eq(M, 0), rho)
    hm = sp.solve(sp.Eq(M, sp.Rational(1, 2)), rho)
    ratio = sp.simplify(hm[0] / be[0])
    ok_inst = (
        abs(float(be[0].subs(q, sp.Rational(1, 2))) - 1 / 16) < 1e-15
        and abs(float(hm[0].subs(q, sp.Rational(1, 2))) - 1 / 4) < 1e-15
        and abs(float(be[0].subs(q, sp.Rational(11, 12))) - (11 / 12) ** 4) < 1e-12
    )
    return {"derivada_ok": bool(dM == 0), "break_even": str(be[0]),
            "half": str(hm[0]), "razao": str(ratio),
            "razao_igual_4": bool(ratio == 4),
            "instancias_A_B_ok": bool(ok_inst)}


def check_LB1() -> dict:
    piores = {}
    for nome, qq in (("A", 0.5), ("B", 11 / 12)):
        M = 1 - qq**2 / np.sqrt(RHO)
        mono = bool(np.all(np.diff(M) > 0))
        # pior violação de M(rho)>=1-q^2/sqrt(rho0) em 6 âncoras
        viol = 0.0
        for r0 in (0.05, 0.1, 0.25, 0.5, 0.7, 0.9):
            bound = 1 - qq**2 / np.sqrt(r0)
            viol = min(viol, float(np.min(M[RHO >= r0] - bound)))
        piores[nome] = {"monotono": mono, "pior_violacao": viol,
                        "ok": bool(mono and viol >= -1e-12)}
    return piores


def check_LB2() -> dict:
    a, b, c = sp.symbols("a b c", nonnegative=True)
    resto = sp.expand((1 + a) * (1 + b) * (1 + c) - (1 + a + b + c))
    esperado = sp.expand(a * b + b * c + a * c + a * b * c)
    forma_exata_ok = bool(sp.simplify(resto - esperado) == 0)
    rng = np.random.RandomState(11)
    pior = 0.0
    for _ in range(3000):
        n = int(rng.randint(1, 8))
        ak = rng.rand(n) * 3.0
        pior = min(pior, float(np.prod(1 + ak) - (1 + np.sum(ak))))
    return {"n3_resto": str(resto),
            "n3_forma_exata_ok": forma_exata_ok,
            "pior_violacao_3000_grades": pior,
            "ok": bool(pior >= -1e-12)}


def main() -> dict:
    t1, lb1, lb2 = check_T1(), check_LB1(), check_LB2()
    ok = t1["derivada_ok"] and t1["razao_igual_4"] and t1["instancias_A_B_ok"] \
        and all(v["ok"] for v in lb1.values()) and lb2["ok"]
    out = {"T1": t1, "LB1": lb1, "LB2": lb2, "tudo_ok": bool(ok),
           "reprodutibilidade": {
               "comando": "python formal-certification/experiments/teorema_transicao_dupla_check.py",
               "semente": "11 (só LB2 numérico; resto exato/determinístico)",
               "saidas": [OUT.name]}}
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str),
                   encoding="utf-8")
    print(f"T1 derivada={t1['derivada_ok']} razao={t1['razao']} inst={t1['instancias_A_B_ok']}")
    print(f"LB1 { {k: v['ok'] for k, v in lb1.items()} } LB2 ok={lb2['ok']} "
          f"pior={lb2['pior_violacao_3000_grades']:.2e}")
    print(f"TUDO_OK={ok} Salvo: {OUT.name}")
    return out


if __name__ == "__main__":
    main()
