#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fct_boxdim_adaptive.py — Box-dim com bins adaptativos (quantis).
==================================================================
Questão (F2/D2): o box-counting legacy satura (10/9 caixas, D=1.0/0.95) e o
boxdim_2d uniforme dá null honesto quando sem escala. O achado "ema→donoho
Box-D p<1e-11" é suspeito de espúrio. Bins adaptativos (igual-contagem por
quantis) resgatam D finito?

Método: para escalas k=2..12 bins, bordas = quantis da série (1D) e grade
quantílica (2D em (t,x)); N(bins) = nº bins ocupados; D = slope logN~log(bins),
com R2 do ajuste. Compara legacy-uniforme × adaptativo em raw/donoho/tail.
Critério: D finito + R2>=0.9 = resgatado; senão, D2 segue só-H (F2 já declarado).

Ten-Proofs. Determinístico. Saídas: out_boxdim_adaptive.json/.csv.
Uso: python formal-certification/experiments/fct_boxdim_adaptive.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from fct_phase_transition_audit import (  # noqa: E402
    boxdim_2d, carregar_serie, donoho_surrogate,
)

OUT_JSON = BASE / "out_boxdim_adaptive.json"
OUT_CSV = BASE / "out_boxdim_adaptive.csv"
K_GRID = tuple(range(2, 13))


def boxdim_1d_adaptive(x: np.ndarray, ks: tuple[int, ...] = K_GRID) -> dict:
    x = np.asarray(x, dtype=float)
    if len(x) < 10 or float(np.max(x) - np.min(x)) < 1e-12:
        return {"D": None, "R2": None, "nota": "serie degenerada"}
    ns, lks = [], []
    for k in ks:
        edges = np.quantile(x, np.linspace(0, 1, k + 1))
        edges = np.unique(edges)
        if len(edges) < 3:
            continue
        idx = np.clip(np.digitize(x, edges[1:-1], right=False), 0, len(edges) - 2)
        ns.append(float(len(np.unique(idx))))
        lks.append(float(k))
    if len(set(ns)) < 2 or len(ns) < 3:
        return {"D": None, "R2": None, "nota": "sem escala (bins saturados)"}
    if all(abs(a - b) < 1e-9 for a, b in zip(ns, lks)):
        return {"D": 1.0, "R2": 1.0, "nota": "trivial (saturado: N(k)=k)"}
    lx, ly = np.log(np.asarray(lks)), np.log(np.asarray(ns))
    slope, icept = np.polyfit(lx, ly, 1)
    pred = slope * lx + icept
    ss = float(np.sum((ly - pred) ** 2))
    st = float(np.sum((ly - np.mean(ly)) ** 2))
    r2 = 1.0 - ss / st if st > 0 else 0.0
    return {"D": float(slope), "R2": float(r2),
            "nota": "resgatado" if r2 >= 0.9 else "ajuste fraco"}


def boxdim_2d_adaptive(x: np.ndarray, ks: tuple[int, ...] = K_GRID) -> dict:
    n = len(x)
    if n < 10:
        return {"D": None, "R2": None, "nota": "serie curta"}
    tn = np.arange(n) / max(n - 1, 1)
    xn = np.asarray(x, dtype=float)
    ns, lks = [], []
    for k in ks:
        et = np.unique(np.quantile(tn, np.linspace(0, 1, k + 1)))
        ex = np.unique(np.quantile(xn, np.linspace(0, 1, k + 1)))
        if len(et) < 3 or len(ex) < 3:
            continue
        it = np.clip(np.digitize(tn, et[1:-1]), 0, len(et) - 2)
        ix = np.clip(np.digitize(xn, ex[1:-1]), 0, len(ex) - 2)
        ns.append(float(len(set(zip(it.tolist(), ix.tolist())))))
        lks.append(float(k))
    if len(set(ns)) < 2 or len(ns) < 3:
        return {"D": None, "R2": None, "nota": "sem escala"}
    if all(abs(a - b) < 1e-9 for a, b in zip(ns, lks)):
        return {"D": 1.0, "R2": 1.0, "nota": "trivial (saturado: N(k)=k)"}
    lx, ly = np.log(np.asarray(lks)), np.log(np.asarray(ns))
    slope, icept = np.polyfit(lx, ly, 1)
    pred = slope * lx + icept
    ss = float(np.sum((ly - pred) ** 2))
    st = float(np.sum((ly - np.mean(ly)) ** 2))
    r2 = 1.0 - ss / st if st > 0 else 0.0
    return {"D": float(slope), "R2": float(r2),
            "nota": "resgatado" if r2 >= 0.9 else "ajuste fraco"}


def main() -> dict:
    vals = carregar_serie()
    filt = donoho_surrogate(vals)
    thr = float(np.percentile(vals, 90))
    idx = np.where(vals > thr)[0]
    tail = vals[idx[0]:idx[-1] + 1] if len(idx) > 30 else vals[vals > thr]
    series = {"raw": vals, "donoho": filt, "tail": tail}
    linhas, blocos = [], {}
    for nome, v in series.items():
        r1 = boxdim_1d_adaptive(v)
        r2 = boxdim_2d_adaptive(v)
        leg = boxdim_2d(v)  # uniforme legacy (referência)
        blocos[nome] = {"adapt_1d": r1, "adapt_2d": r2, "legacy_2d_uniforme": leg,
                        "n": int(len(v))}
        for metodo, r in (("adapt_1d", r1), ("adapt_2d", r2)):
            linhas.append({"serie": nome, "metodo": metodo, "D": r["D"],
                          "R2": r["R2"], "nota": r["nota"]})
    n_resg = sum(1 for L in linhas if L["nota"] == "resgatado")
    out = {
        "questao": "Bins adaptativos resgatam Box-D? (F2/D2)",
        "blocos": blocos,
        "veredito": (
            f"{n_resg}/{len(linhas)} combinações resgatadas (D finito, R2>=0.9). "
            + ("D2 reabilitado como métrica auxiliar onde resgatado; onde não, "
               "segue só-H (F2 mantido)." if n_resg else
               "Nada resgatado: D2 segue só-H; o p<1e-11 ema→donoho é espúrio.")
        ),
        "reprodutibilidade": {
            "comando": "python formal-certification/experiments/fct_boxdim_adaptive.py",
            "semente": "determinístico (sem RNG)",
            "saidas": [OUT_JSON.name, OUT_CSV.name],
        },
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False, default=str)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["serie", "metodo", "D", "R2", "nota"])
        w.writeheader()
        w.writerows(linhas)
    print(out["veredito"])
    print(f"Salvo: {OUT_JSON.name}, {OUT_CSV.name}")
    return out


if __name__ == "__main__":
    main()
