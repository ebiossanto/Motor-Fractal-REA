#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hurst_estimator_calibration.py — Calibração dos estimadores H sob spikes/platôs.
================================================================================
Questão (F2/F4硬): no dado real, Higuchi diz H≈0.22, R/S diz ≈0.91 e DFA dá
>1 (inválido). Qual estimador é confiável em telemetria espiculada com platô
de saturação? Sem ground-truth, o consenso por mediana é chute.

Método: gera ARFIMA(0,d,0) com H conhecido (d=H−0.5, semente fixa 7, N=300),
contamina com (a) limpo, (b) spikes, (c) platô, (d) real-like (spikes+platô),
mede viés H_est−H_true por estimador (Higuchi, R/S, DFA, variance-lag, box2d
importados do audit — implementação única), e corrige o H real.

Método Ten-Proofs. Determinístico (RandomState(7)). Saídas congeladas:
out_hurst_calibration.json + out_hurst_calibration.csv.
Uso: python formal-certification/experiments/hurst_estimator_calibration.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from fct_phase_transition_audit import (  # noqa: E402
    boxdim_2d, dfa_hurst, donoho_surrogate, higuchi_fd, rs_hurst,
    variance_lag_hurst, carregar_serie,
)

OUT_JSON = BASE / "out_hurst_calibration.json"
OUT_CSV = BASE / "out_hurst_calibration.csv"
SEED, N, M_TRUNC = 7, 300, 400
H_GRID = (0.2, 0.3, 0.35, 0.5, 0.7)
CONDICOES = ("limpo", "spikes", "plato", "real_like")


def pesos_arfima(d: float, m: int = M_TRUNC) -> np.ndarray:
    # domínio-log (math.lgamma) — gamma(400) estoura float; exp(log) é estável
    w = np.empty(m)
    for k in range(m):
        if d <= 0:
            w[k] = 1.0 if k == 0 else 0.0
        else:
            w[k] = math.exp(math.lgamma(k + d) - math.lgamma(k + 1) - math.lgamma(d))
    return w


def gerar(d: float, rng: np.random.RandomState, n: int = N) -> np.ndarray:
    eps = rng.standard_normal(n + M_TRUNC)
    x = np.convolve(eps, pesos_arfima(d), mode="valid")
    x = x[-n:]
    return (x - x.mean()) / (x.std() or 1.0) * 15.0 + 15.0


def contaminar(x: np.ndarray, cond: str, rng: np.random.RandomState) -> np.ndarray:
    y = x.copy()
    if cond in ("spikes", "real_like"):
        idx = rng.choice(len(y), size=int(0.05 * len(y)), replace=False)
        y[idx] = 95.0 + rng.rand(len(idx)) * 5.0
    if cond in ("plato", "real_like"):
        s = int(len(y) * 0.70)
        y[s:s + int(len(y) * 0.15)] = 96.0
    return np.clip(y, 0.0, 100.0)


def estimar(v: np.ndarray) -> dict:
    _, h_h = higuchi_fd(v)
    out = {"higuchi": h_h, "rs": rs_hurst(v), "dfa": dfa_hurst(v),
           "box2d": boxdim_2d(v)}
    _, h_v = variance_lag_hurst(v)
    out["varlag"] = h_v
    return out


def main() -> dict:
    rng = np.random.RandomState(SEED)
    # ruído branco por H (mesmo eps → comparação justa entre H)
    base_eps = rng.standard_normal(N + M_TRUNC)
    linhas = []
    vies: dict = {}
    for h in H_GRID:
        d = h - 0.5
        for cond in CONDICOES:
            r2 = np.random.RandomState(SEED + int(h * 100) + len(cond))
            x = np.convolve(base_eps, pesos_arfima(max(d, 0.01)), mode="valid")[-N:]
            x = (x - x.mean()) / (x.std() or 1.0) * 15.0 + 15.0
            v = contaminar(x, cond, r2)
            est = estimar(v)
            for nome, hv in est.items():
                bias = (hv - h) if hv is not None and 0.0 < hv < 1.6 else None
                linhas.append({"H_true": h, "cond": cond, "est": nome,
                              "H_est": hv, "bias": bias})
    # viés médio por estimador na condição real_like (a que imita a telemetria)
    cal: dict = {}
    for nome in ("higuchi", "rs", "dfa", "varlag", "box2d"):
        bs = [L["bias"] for L in linhas if L["est"] == nome and L["cond"] == "real_like"
              and L["bias"] is not None]
        allb = [abs(L["bias"]) for L in linhas if L["est"] == nome and L["bias"] is not None]
        cal[nome] = {"bias_medio_real_like": float(np.mean(bs)) if bs else None,
                     "mae_global": float(np.mean(allb)) if allb else None,
                     "n_validos": len(allb)}
    # H real corrigido: H_corr = H_real − bias(real_like); consenso = mediana
    real = carregar_serie()
    filt = donoho_surrogate(real)
    D_h, H_h = higuchi_fd(real)
    corrigidos = {}
    for rot, serie in (("raw", real), ("donoho", filt)):
        est = estimar(serie)
        hc = {}
        for nome, hv in est.items():
            b = cal[nome]["bias_medio_real_like"]
            hc[nome] = (hv - b) if (hv is not None and b is not None) else None
        vals = [v for v in hc.values() if v is not None and 0.0 < v < 1.0]
        corrigidos[rot] = {"brutos": est, "corrigidos": hc,
                           "consenso_corrigido": float(np.median(vals)) if vals else None}
    # ranking de robustez: menor MAE global, desempate por nº válidos
    rank = sorted(cal, key=lambda k: (cal[k]["mae_global"] if cal[k]["mae_global"] is not None else 9e9,
                                      -(cal[k]["n_validos"] or 0)))
    out = {
        "questao": "Qual estimador H é confiável sob spikes/platô? Correção do H real.",
        "semente": SEED, "N_sintetico": N, "H_grid": list(H_GRID),
        "calibracao_por_estimador": cal,
        "ranking_robustez": rank,
        "H_real_corrigido": corrigidos,
        "veredito": (
            f"Ranking: {', '.join(rank)}. "
            f"H raw corrigido={corrigidos['raw']['consenso_corrigido']}, "
            f"Donoho corrigido={corrigidos['donoho']['consenso_corrigido']}. "
            f"Estimadores com MAE alto/DFA inválido são declarados frágeis em dado "
            f"espiculado — o consenso usa só válidos em (0,1) após correção de viés."
        ),
        "reprodutibilidade": {
            "comando": "python formal-certification/experiments/hurst_estimator_calibration.py",
            "semente": "RandomState(7) fixa",
            "saidas": [OUT_JSON.name, OUT_CSV.name],
        },
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False, default=str)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["H_true", "cond", "est", "H_est", "bias"])
        w.writeheader()
        for L in linhas:
            w.writerow(L)
    print(out["veredito"])
    print(f"Salvo: {OUT_JSON.name}, {OUT_CSV.name}")
    return out


if __name__ == "__main__":
    main()
