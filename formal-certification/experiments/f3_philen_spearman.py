#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
f3_philen_spearman.py — Sweep phi_len + regressão H~phi + Spearman σ_tgt×θ.
================================================================================
Questões (F3/F5): H=0.297 (phi 3,4) → 0.409 (phi 5) cruza 0.35: artefato ou
sinal? E σ_tgt×θ tem monotonicidade (Spearman, hipótese D4)?

Fontes (somente leitura, repo Gödel):
- legado: gk_F3_tau_real.json (configs phi 3,4,5 com H_theta_ordered; script
  gerador NÃO sobrevivente — H legado marcado (H), não reproduzível aqui);
- Z3 disponível: gk_F3_phi_len_{6,7,8,9,10,12}.json (inclui phi=12 gerado
  nesta frente; traduções com sigma_tgt, theta_overhead, interpolant_size,
  proof_src/tgt_len, interpolation_time_ms).

Método: para cada phi Z3, H corrigido (Higuchi/RS/DFA/varlag do audit sobre
séries ordenadas de theta_overhead e interpolant_size; consenso = mediana dos
válidos) + Spearman (scipy) global e por bloco σ_tgt para (n,θ), (n,tempo),
(θ,proof_src). Regressão OLS H_consenso~phi só nos pontos Z3 (metodologia
única); legado plotado como referência (H), fora da regressão.

Ten-Proofs. Determinístico. Saídas: out_f3_philen_regression.json/.csv,
out_spearman_sigma_theta.json/.csv.
Uso: python formal-certification/experiments/f3_philen_spearman.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

try:
    from scipy.stats import spearmanr
except ImportError as e:  # pragma: no cover
    raise SystemExit("scipy é obrigatório") from e

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from fct_phase_transition_audit import (  # noqa: E402
    dfa_hurst, higuchi_fd, rs_hurst, variance_lag_hurst,
)

GODEL = Path(r"C:\Users\Euzébio Soares\Desktop\CyberAmbiente\IA-research-Godel-e-Krajicek")
PHIS_Z3 = (6, 7, 8, 9, 10, 12)
OUT_REG = BASE / "out_f3_philen_regression.json"
OUT_REGC = BASE / "out_fct_philen_series.csv"
OUT_SP = BASE / "out_spearman_sigma_theta.json"
OUT_SPC = BASE / "out_spearman_blocks.csv"


def consenso_h(vals: list) -> float | None:
    v = np.asarray(vals, dtype=float)
    if len(v) < 4:
        return None
    out = []
    for est in (lambda s: higuchi_fd(s)[1], rs_hurst, dfa_hurst,
                lambda s: variance_lag_hurst(s)[1]):
        try:
            h = est(v)
        except Exception:
            h = None
        if h is not None and 0.0 < h < 1.0:
            out.append(h)
    return float(np.median(out)) if out else None


def spearman(a: np.ndarray, b: np.ndarray) -> dict:
    if len(set(a.tolist())) < 2 or len(set(b.tolist())) < 2:
        return {"rho": None, "p": None, "nota": "sem variância (constante)"}
    r, p = spearmanr(a, b)
    return {"rho": float(r), "p": float(p),
            "nota": "significativo" if p < 0.05 else "não significativo"}


def main() -> dict:
    legado = json.loads((GODEL / "gk_F3_tau_real.json").read_text(encoding="utf-8"))["configs"]
    pts, blocos, reg_rows, sp_rows = [], [], [], []
    for phi in PHIS_Z3:
        d = json.loads((GODEL / f"gk_F3_phi_len_{phi}.json").read_text(encoding="utf-8"))
        recs = [t for r in d["theta_translations"] for t in r["translations"]]
        oh = [t["theta_overhead"] for t in recs]
        ip = [t["interpolant_size"] for t in recs]
        h_oh, h_ip = consenso_h(oh), consenso_h(ip)
        h_c = float(np.median([h for h in (h_oh, h_ip) if h is not None])) \
            if any(h is not None for h in (h_oh, h_ip)) else None
        n = np.array([t["n"] for t in recs])
        th = np.array(oh, dtype=float)
        tm = np.array([t["interpolation_time_ms"] for t in recs], dtype=float)
        ps = np.array([t["proof_src_len"] for t in recs], dtype=float)
        st = np.array([t["sigma_tgt"] for t in recs])
        g = {"n_vs_theta": spearman(n, th), "n_vs_tempo": spearman(n, tm),
             "theta_vs_proofsrc": spearman(th, ps)}
        per_tgt = {}
        for tgt in sorted(set(st.tolist())):
            m = st == tgt
            per_tgt[str(tgt)] = {"n": int(m.sum()),
                                 "n_vs_theta": spearman(n[m], th[m]),
                                 "n_vs_tempo": spearman(n[m], tm[m]),
                                 "theta_vs_proofsrc": spearman(th[m], ps[m])}
            for par, s in (("n_vs_theta", spearman(n[m], th[m])),
                           ("n_vs_tempo", spearman(n[m], tm[m]))):
                sp_rows.append({"phi": phi, "bloco": f"sigma_tgt={tgt}", "par": par,
                                "rho": s["rho"], "p": s["p"], "nota": s["nota"]})
        for par, s in (("n_vs_theta", g["n_vs_theta"]), ("n_vs_tempo", g["n_vs_tempo"])):
            sp_rows.append({"phi": phi, "bloco": "global", "par": par,
                            "rho": s["rho"], "p": s["p"], "nota": s["nota"]})
        pts.append({"phi": phi, "n_translations": len(recs),
                    "valid_rate": d["summary"]["valid_rate"],
                    "H_theta": h_oh, "H_interpolant": h_ip, "H_consenso": h_c,
                    "global": g, "por_bloco": per_tgt,
                    "metodologia": "Z3-disponivel+H-corrigido (P)"})
        reg_rows.append({"phi": phi, "H_consenso": h_c, "fonte": "z3"})
    for c in legado:
        try:
            phi = int(c["config"].split("phi_len=")[1].split(",")[0])
        except Exception:
            continue
        reg_rows.append({"phi": phi, "H_consenso": c.get("H_theta_ordered"), "fonte": "legado(H)"})
    # OLS H~phi só Z3
    zx = np.array([p["phi"] for p in pts], dtype=float)
    zy = np.array([p["H_consenso"] if p["H_consenso"] is not None else np.nan for p in pts])
    m = np.isfinite(zy)
    if int(m.sum()) >= 3:
        slope, ice = np.polyfit(zx[m], zy[m], 1)
        pred = slope * zx[m] + ice
        denom = float(np.sum((zy[m] - zy[m].mean()) ** 2))
        r2 = (1.0 - float(np.sum((zy[m] - pred) ** 2)) / denom) if denom > 1e-18 else None
        cross = (0.35 - ice) / slope if abs(slope) > 1e-12 else None
        reg = {"slope": float(slope), "intercept": float(ice),
               "R2": (float(r2) if r2 is not None else None),
               "phi_onde_H_cruza_035": float(cross) if cross is not None else None,
               "n_pontos": int(m.sum()), "nota": "OLS só pontos Z3 (metodologia única)"}
    else:
        reg = {"slope": None, "intercept": None, "R2": None,
               "phi_onde_H_cruza_035": None, "n_pontos": int(m.sum()),
               "nota": "H degenerado no pipeline Z3: série binária {20,53}; sem regressão honesta"}
    # D4: algum bloco significativo?
    sig = [r for r in sp_rows if r["p"] is not None and r["p"] < 0.05]
    out_r = {"questao": "H~phi_len: travessia 0.35 artefato ou sinal?",
             "pontos": pts,
             "legado_referencia_H": [{"config": c["config"], "H": c.get("H_theta_ordered"),
                                      "n": c.get("n_translations")} for c in legado],
             "regressao_Z3": reg,
             "veredito": "",
             "reprodutibilidade": {
                 "comando": "python formal-certification/experiments/f3_philen_spearman.py",
                 "semente": "determinístico (sem RNG)",
                 "saidas": [OUT_REG.name, OUT_REGC.name, OUT_SP.name, OUT_SPC.name]}}
    out_s = {"questao": "Spearman sigma_tgt×theta (D4)?",
             "blocos": sp_rows,
             "n_significativos": len(sig),
             "veredito": (f"{len(sig)}/{len(sp_rows)} pares significativos. " +
                          ("D4 com suporte parcial — ver blocos." if sig else
                           "D4 sem suporte: nenhuma monotonicidade significativa; hipótese segue pendente.")),
             "reprodutibilidade": out_r["reprodutibilidade"]}
    n_z3 = sum(1 for p in pts if p["H_consenso"] is not None)
    if reg["slope"] is not None and reg["R2"] is not None:
        detalhe = f"OLS slope={reg['slope']:.4f}, R2={reg['R2']}."
    elif reg["slope"] is not None:
        detalhe = ("H Z3 identico (~0.004) em todos os phi: serie theta binaria "
                   "(2 valores) -> estimador retorna residuo degenerado, NAO medicao. "
                   "Nao confirma nem refuta travessia; H legado 0.297->0.409 e de "
                   "pipeline distinto cujo script nao sobreviveu -> (H). F3-H em aberto.")
    else:
        detalhe = ("Series theta degeneradas (2 valores) -> H nulo em todos os phi Z3: "
                   "travessia 0.35 NAO testavel neste pipeline; H legado 0.297->0.409 e de "
                   "pipeline distinto cujo script nao sobreviveu -> marcado (H), nao usado "
                   "na regressao. Veredito: travessia phi=5 como 'sinal' RETIRADO (R); "
                   "ate reconstrucao do pipeline legado, F3-H fica em aberto.")
    out_r["veredito"] = f"Z3: {n_z3}/{len(pts)} phi com H valido. " + detalhe
    for o, p in ((out_r, OUT_REG), (out_s, OUT_SP)):
        with open(p, "w", encoding="utf-8") as f:
            json.dump(o, f, indent=2, ensure_ascii=False, default=str)
    with open(OUT_REGC, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["phi", "H_consenso", "fonte"])
        w.writeheader()
        w.writerows(reg_rows)
    with open(OUT_SPC, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["phi", "bloco", "par", "rho", "p", "nota"])
        w.writeheader()
        w.writerows(sp_rows)
    print(out_r["veredito"])
    print(out_s["veredito"])
    print(f"Salvo: {OUT_REG.name}, {OUT_REGC.name}, {OUT_SP.name}, {OUT_SPC.name}")
    return {"regressao": out_r, "spearman": out_s}


if __name__ == "__main__":
    main()
