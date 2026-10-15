#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fct_rho_regime_tracker.py — Regime tracker de rho(t) na telemetria real.
=============================================================================
Questão (F1 corrigido): o audit FCT-AUDIT-001 achou P90=89.4 (F1 usava 39.0,
5 eventos; correto: 10 eventos) e três limiares concorrentes — break-even A
0.0625, meia-mitigaç��o/doc 0.25, break-even B 0.7063. Quando o sistema cruza
cada limiar, quanto tempo permanece acima, e qual modelo recomenda PFA?

Método Ten-Proofs. Determinístico (sem RNG). Saídas congeladas neste diretório:
out_fct_rho_regimes.json + out_fct_rho_series.csv.
Uso: python formal-certification/experiments/fct_rho_regime_tracker.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None

BASE = Path(__file__).resolve().parent
REPO_ROOT = BASE.parent.parent
CPU_CSV = REPO_ROOT / "cpu_timeseries.csv"
OUT_JSON = BASE / "out_fct_rho_regimes.json"
OUT_CSV = BASE / "out_fct_rho_series.csv"

LIMIARES = {
    "break_even_A": 1 / 16,          # 0.0625 — Modelo A (E_pfa absoluto)
    "half_mit_A_doc": 0.25,          # meia-mitigaç��o A (= "rho_c" do doc §2.4)
    "break_even_B": (11 / 12) ** 4,  # ≈0.7063 — Modelo B (E_pfa relativo)
}
P = 1.0 / 6.0
E_A = 1.0 / 12.0
E_B = P * (11 / 12)


def carregar() -> tuple[np.ndarray, np.ndarray]:
    if pd is not None and CPU_CSV.exists():
        df = pd.read_csv(str(CPU_CSV))
        tcol = "timestamp_seconds" if "timestamp_seconds" in df.columns else df.columns[0]
        ccol = "cpu_percent" if "cpu_percent" in df.columns else df.columns[1]
        return df[tcol].astype(float).to_numpy(), df[ccol].astype(float).to_numpy()
    t, v = [], []
    with open(CPU_CSV, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for row in rd:
            t.append(float(row["timestamp_seconds"]))
            v.append(float(row["cpu_percent"]))
    return np.asarray(t), np.asarray(v)


def episodios(acima: np.ndarray) -> list[tuple[int, int]]:
    d = np.diff(acima.astype(int))
    starts = (np.where(d == 1)[0] + 1).tolist()
    ends = (np.where(d == -1)[0] + 1).tolist()
    if acima[0]:
        starts = [0] + starts
    if len(ends) < len(starts):
        ends = ends + [len(acima)]
    return list(zip(starts, ends))


def main() -> dict:
    t, cpu = carregar()
    rho = cpu / 100.0
    n = len(rho)
    dt = float(np.median(np.diff(t))) if n > 1 else 0.1

    regimes: dict = {}
    for nome, lim in LIMIARES.items():
        ac = rho > lim
        eps = episodios(ac)
        dur = [(e - s) * dt for s, e in eps]
        regimes[nome] = {
            "limiar": lim,
            "fracao_acima": float(np.mean(ac)),
            "tempo_acima_s": float(np.sum(ac) * dt),
            "n_episodios": len(eps),
            "duracao_max_episodio_s": float(max(dur)) if dur else 0.0,
            "duracao_media_episodio_s": float(np.mean(dur)) if dur else 0.0,
            "episodios": [{"start": int(s), "end": int(e),
                           "t_ini": float(t[s]), "t_fim": float(t[e - 1]),
                           "rho_max": float(np.max(rho[s:e]))} for s, e in eps],
        }

    rho_g = float(np.mean(rho))
    p99 = float(np.percentile(cpu, 99))

    def infl(r, e):
        return (r / (1 - r)) * e ** 2 if r < 1 else float("inf")

    rec = {}
    for nome, lim in LIMIARES.items():
        rec[nome] = ("ATIVAR PFA" if rho_g > lim else "DFA suficiente")

    out = {
        "questao": "F1 corrigido: rho(t) dinâmico, cruzamentos e dwell por limiar",
        "n": n, "dt_mediano_s": dt,
        "rho_global": rho_g, "cpu_p99": p99,
        "p90_cpu": float(np.percentile(cpu, 90)),
        "inflacao_dfa_rho_global": infl(rho_g, P),
        "inflacao_pfaA_rho_global": (rho_g ** 0.5 / (1 - rho_g)) * E_A ** 2,
        "inflacao_pfaB_rho_global": (rho_g ** 0.5 / (1 - rho_g)) * E_B ** 2,
        "regimes": regimes,
        "recomendacao_por_modelo_rho_global": rec,
        "leitura": (
            f"ρ global={rho_g:.3f}: Modelo A (BE 0.0625) → PFA; doc (0.25) → PFA; "
            f"Modelo B (BE 0.706) → DFA. Saturação P90+ ocupa "
            f"{regimes['break_even_B']['fracao_acima']:.1%} do tempo acima de 0.706 "
            f"em {regimes['break_even_B']['n_episodios']} episódios "
            f"(máx {regimes['break_even_B']['duracao_max_episodio_s']:.1f}s). "
            f"A decisão operacional PFA×DFA depende do modelo — sem fixar o modelo "
            f"PFA, o tracker não fecha recomendação única (honesto)."
        ),
        "reprodutibilidade": {
            "comando": "python formal-certification/experiments/fct_rho_regime_tracker.py",
            "semente": "determinístico (sem RNG)",
            "saidas": [OUT_JSON.name, OUT_CSV.name],
        },
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False, default=str)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "cpu", "rho", "acima_BE_A", "acima_HM_doc", "acima_BE_B"])
        for i in range(n):
            w.writerow([t[i], cpu[i], rho[i],
                        int(rho[i] > LIMIARES["break_even_A"]),
                        int(rho[i] > LIMIARES["half_mit_A_doc"]),
                        int(rho[i] > LIMIARES["break_even_B"])])
    print(f"rho_global={rho_g:.3f} p99={p99:.1f} "
          f"ep_BE_A={regimes['break_even_A']['n_episodios']} "
          f"ep_025={regimes['half_mit_A_doc']['n_episodios']} "
          f"ep_BE_B={regimes['break_even_B']['n_episodios']}")
    print(f"Salvo: {OUT_JSON.name}, {OUT_CSV.name}")
    return out


if __name__ == "__main__":
    main()
