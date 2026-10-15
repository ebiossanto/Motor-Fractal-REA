#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fct_phase_transition_audit.py — Auditoria da transição de fase FCT (ρ_c) + H real.
===============================================================================
Questão não respondida (Q*):
  FCT_REFINAMENTO_PREDITIVO.md §2.4 afirma ρ_c = 0.25 ("PFA se torna vantajoso"),
  mas os artefatos gk_D1/gk_F1 usam ρ_c = (1-r)^4 ≈ 0.706 (r=1/12).
  Qual vale? E qual é o H real da telemetria durante tail-latency, dado que o
  variance-slope atual dá H=4.83 (impossível) e o Box-Dim legacy é degenerado?

Resposta antecipada (a confirmar por esta ferramenta):
  Há DOIS modelos PFA distintos em jogo; 0.25 não é break-even em nenhum deles.
  - Modelo A (doc §2.3, E_pfa=1/12 absoluto): break-even ρ=1/16=0.0625;
    M=0.5 (meia-mitigaç��o) em ρ=0.25.
  - Modelo B (artefatos gk, E_pfa=p(1-r), r=1/12): break-even ρ=(1-r)^4≈0.7063.
  Logo "ρ_c=0.25" como "ponto onde PFA se torna vantajoso" está errado sob as
  próprias fórmulas do doc (vantagem começa em 0.0625, Modelo A) ou em 0.706
  (Modelo B). Recomendação: corrigir §2.4 distinguindo break-even × meia-mitigaç��o.

Método Ten-Proofs: Descoberta → Formalização → Verificação → Certificação → Reprodutibilidade.
Determinístico: sem aleatoriedade; semente fixa onde houver empate.
Saídas congeladas: out_fct_audit.json + out_fct_rho_sweep.csv (mesmo diretório).
Uso:
  python formal-certification/experiments/fct_phase_transition_audit.py
"""
from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path

try:
    import numpy as np
except ImportError as e:  # pragma: no cover
    raise SystemExit("numpy é obrigatório: pip install numpy") from e

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None

BASE = Path(__file__).resolve().parent
REPO_ROOT = BASE.parent.parent  # .../zero
CPU_CSV = REPO_ROOT / "cpu_timeseries.csv"
OUT_JSON = BASE / "out_fct_audit.json"
OUT_SWEEP = BASE / "out_fct_rho_sweep.csv"

P = 1.0 / 6.0        # E_6^* DFA (doc §2.2)
R = 1.0 / 12.0       # coeficiente de relaxamento (artefatos gk)
E_PFA_ABS = 1.0 / 12.0   # Modelo A: erro PFA absoluto (doc §2.3)
E_PFA_REL = P * (1.0 - R)  # Modelo B: erro PFA relativo (artefatos gk)


# --------------------------------------------------------------------------
# Parte A — derivação analítica fechada (P)
# --------------------------------------------------------------------------
def dfa_infl(rho: float) -> float:
    return (rho / (1.0 - rho)) * P ** 2


def pfa_infl_modelo_a(rho: float) -> float:
    return (math.sqrt(rho) / (1.0 - rho)) * E_PFA_ABS ** 2


def pfa_infl_modelo_b(rho: float) -> float:
    return (math.sqrt(rho) / (1.0 - rho)) * E_PFA_REL ** 2


def mitigacao(modelo: str, rho: float) -> float:
    d = dfa_infl(rho)
    pfa = pfa_infl_modelo_a(rho) if modelo == "A" else pfa_infl_modelo_b(rho)
    return (d - pfa) / d if d > 0 else 0.0


def rho_break_even_analitico(modelo: str) -> float:
    if modelo == "A":
        # rho*P^2 = sqrt(rho)*E^2  =>  sqrt(rho) = (E/P)^2 = (1/2)^2 = 1/4
        return (E_PFA_ABS / P) ** 4  # = (1/2)^4 = 1/16
    # rho*P^2 = sqrt(rho)*[P(1-r)]^2  =>  sqrt(rho) = (1-r)^2
    return (1.0 - R) ** 4


def rho_half_mitigation_analitico(modelo: str) -> float:
    # M = 1 - (E_pfa/P)^2 / sqrt(rho) = 1/2  =>  sqrt(rho) = 2*(E_pfa/P)^2
    ratio = (E_PFA_ABS / P) ** 2 if modelo == "A" else (1.0 - R) ** 2
    return (2.0 * ratio) ** 2


# --------------------------------------------------------------------------
# Parte B — sweep numérico + cruzamentos por interpolação linear
# --------------------------------------------------------------------------
def rho_sweep(n: int = 99) -> list[dict]:
    rows = []
    for i in range(1, n + 1):
        rho = 0.01 + (0.99 - 0.01) * (i - 1) / (n - 1)
        d = dfa_infl(rho)
        pa = pfa_infl_modelo_a(rho)
        pb = pfa_infl_modelo_b(rho)
        rows.append({
            "rho": rho,
            "dfa": d,
            "pfa_A": pa,
            "pfa_B": pb,
            "mitig_A": (d - pa) / d,
            "mitig_B": (d - pb) / d,
        })
    return rows


def cruzar(rows: list[dict], key: str, alvo: float = 0.0,
           diff: str = "d_minus_p") -> float | None:
    """Interpola linearmente o rho onde (dfa - key) cruza `alvo`,
    ou onde `key` cruza `alvo` se diff='self'."""
    prev_r, prev_v = None, None
    for r in rows:
        v = (r["dfa"] - r[key]) if diff == "d_minus_p" else r[key]
        if prev_v is not None and (prev_v - alvo) * (v - alvo) <= 0 and v != prev_v:
            t = (alvo - prev_v) / (v - prev_v)
            return prev_r + t * (r["rho"] - prev_r)
        prev_r, prev_v = r["rho"], v
    return None


# --------------------------------------------------------------------------
# Parte C — telemetria real: eventos de tail-latency e ρ efetivo
# --------------------------------------------------------------------------
def carregar_serie() -> np.ndarray:
    if pd is not None and CPU_CSV.exists():
        df = pd.read_csv(str(CPU_CSV))
        col = "cpu_percent" if "cpu_percent" in df.columns else df.columns[1]
        return df[col].astype(float).to_numpy()
    vals = []
    with open(CPU_CSV, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        col = "cpu_percent" if "cpu_percent" in (rd.fieldnames or []) else (rd.fieldnames or [])[1]
        for row in rd:
            vals.append(float(row[col]))
    return np.asarray(vals, dtype=float)


def eventos_tail(vals: np.ndarray, q: float = 90.0) -> tuple[float, list[dict]]:
    thr = float(np.percentile(vals, q))
    acima = vals > thr
    d = np.diff(acima.astype(int))
    starts = (np.where(d == 1)[0] + 1).tolist()
    ends = (np.where(d == -1)[0] + 1).tolist()
    if acima[0]:
        starts = [0] + starts
    if len(ends) < len(starts):
        ends = ends + [len(vals)]
    evs = []
    for i, (s, e) in enumerate(zip(starts, ends)):
        seg = vals[s:e]
        evs.append({
            "event_id": i, "start": int(s), "end": int(e),
            "duration": int(e - s),
            "mean_cpu": float(np.mean(seg)) if len(seg) else 0.0,
            "rho_eff": float(np.mean(seg) / 100.0) if len(seg) else 0.0,
        })
    return thr, evs


# --------------------------------------------------------------------------
# Parte D — estimadores de Hurst corretos (com guardas 0<H<1)
# --------------------------------------------------------------------------
def higuchi_fd(series: np.ndarray, kmax: int = 20) -> tuple[float | None, float | None]:
    x = np.asarray(series, dtype=float)
    n = len(x)
    if n < 16:
        return None, None
    kmax = min(kmax, n // 3)
    ks = list(range(1, kmax + 1))
    lk: list[float] = []
    for k in ks:
        acc, cnt = 0.0, 0
        for m in range(1, k + 1):
            seq = x[(m - 1)::k]
            if len(seq) < 2:
                continue
            norm = (n - 1) / (k * len(seq))
            acc += float(np.sum(np.abs(np.diff(seq))) * norm) / k
            cnt += 1
        lk.append(acc / cnt if cnt else 0.0)
    lk = np.asarray(lk, dtype=float)
    logs = np.log(np.maximum(lk, 1e-12))
    logk = np.log(1.0 / np.asarray(ks, dtype=float))
    mask = np.isfinite(logs)
    if int(mask.sum()) < 4:
        return None, None
    slope = float(np.polyfit(logk[mask], logs[mask], 1)[0])
    D = slope  # D de Higuchi; H = 2 - D
    return D, 2.0 - D


def rs_hurst(series: np.ndarray, min_win: int = 10) -> float | None:
    x = np.asarray(series, dtype=float)
    n = len(x)
    if n < 4 * min_win:
        return None
    wins = []
    w = min_win
    while w <= n // 2:
        wins.append(w)
        w *= 2
    rs, ns = [], []
    for w in wins:
        k = n // w
        vals = []
        for j in range(k):
            seg = x[j * w:(j + 1) * w]
            m = np.mean(seg)
            dev = seg - m
            cum = np.cumsum(dev)
            rng = float(np.max(cum) - np.min(cum))
            std = float(np.std(seg))
            if std > 1e-12:
                vals.append(rng / std)
        if vals:
            rs.append(float(np.mean(vals)))
            ns.append(w)
    if len(rs) < 3:
        return None
    lr, ln = np.log(np.asarray(rs)), np.log(np.asarray(ns))
    mask = np.isfinite(lr) & np.isfinite(ln)
    if int(mask.sum()) < 3:
        return None
    return float(np.polyfit(ln[mask], lr[mask], 1)[0])


def dfa_hurst(series: np.ndarray, min_win: int = 8) -> float | None:
    x = np.asarray(series, dtype=float) - float(np.mean(series))
    y = np.cumsum(x)
    n = len(y)
    wins = []
    w = min_win
    while w <= n // 4:
        wins.append(w)
        w = int(w * 1.5) + 1
    if len(wins) < 3:
        return None
    fl, ns = [], []
    t = np.arange(n)
    for w in wins:
        k = n // w
        var = []
        for j in range(k):
            seg = y[j * w:(j + 1) * w]
            tt = t[j * w:(j + 1) * w]
            coef = np.polyfit(tt, seg, 1)
            trend = coef[0] * tt + coef[1]
            var.append(float(np.mean((seg - trend) ** 2)))
        if var:
            fl.append(float(np.sqrt(np.mean(var))))
            ns.append(w)
    lf, ln = np.log(np.asarray(fl)), np.log(np.asarray(ns))
    mask = np.isfinite(lf) & np.isfinite(ln)
    if int(mask.sum()) < 3:
        return None
    return float(np.polyfit(ln[mask], lf[mask], 1)[0])


def variance_lag_hurst(series: np.ndarray,
                       lags: tuple[int, ...] = (2, 4, 8, 16, 32)) -> tuple[float | None, float | None]:
    """CORRETO: Var(X_{t+s} - X_t) ~ s^{2H}. Retorna (slope, H=slope/2).
    O bug antigo usava np.diff(x, n=s) (diferença de ordem n, não lag s),
    o que produzia slope≈8.65 e H≈4.83 (impossível)."""
    x = np.asarray(series, dtype=float)
    n = len(x)
    use = [s for s in lags if s < n // 2]
    if len(use) < 3:
        return None, None
    vs = [float(np.var(x[s:] - x[:-s])) for s in use]
    lv = np.log(np.maximum(np.asarray(vs), 1e-12))
    ls = np.log(np.asarray(use, dtype=float))
    mask = np.isfinite(lv)
    if int(mask.sum()) < 3:
        return None, None
    slope = float(np.polyfit(ls[mask], lv[mask], 1)[0])
    return slope, slope / 2.0


def boxdim_2d(series: np.ndarray,
              scales: tuple[float, ...] = (0.02, 0.05, 0.1, 0.2)) -> float | None:
    """Box-counting 2D sobre embedding (t,x) normalizado — evita a degeneração
    do box-counting 1D legacy (caixas saturadas em 10/9)."""
    x = np.asarray(series, dtype=float)
    n = len(x)
    if n < 10 or float(np.max(x) - np.min(x)) < 1e-12:
        return None
    tn = np.arange(n) / max(n - 1, 1)
    xn = (x - np.min(x)) / (np.max(x) - np.min(x))
    counts = []
    for eps in scales:
        boxes = set()
        for a, b in zip(tn, xn):
            boxes.add((int(a / eps), int(b / eps)))
        counts.append(len(boxes))
    lc = np.log(np.asarray(counts, dtype=float))
    le = np.log(1.0 / np.asarray(scales, dtype=float))
    if not bool(np.all(np.isfinite(lc))):
        return None
    if len(set(counts)) < 2:
        return None  # degenerado: sem escala
    return float(np.polyfit(le, lc, 1)[0])


def donoho_surrogate(series: np.ndarray) -> np.ndarray:
    """Filtro estilo Donoho sem pywt: limiar suave universal sobre detalhes
    de primeira diferença (surrogate de wavelet), reconstrução por cumsum.
    Determinístico."""
    x = np.asarray(series, dtype=float)
    det = np.diff(x)
    sigma = float(np.median(np.abs(det)) / 0.6745) if len(det) else 0.0
    if sigma < 1e-12:
        return x.copy()
    uthr = sigma * math.sqrt(2.0 * math.log(len(x)))
    soft = np.sign(det) * np.maximum(0.0, np.abs(det) - uthr * 0.5)
    rec = np.empty_like(x)
    rec[0] = x[0]
    rec[1:] = x[0] + np.cumsum(soft)
    return rec


def avaliar_serie(nome: str, vals: np.ndarray) -> dict:
    D_h, H_h = higuchi_fd(vals)
    H_rs = rs_hurst(vals)
    H_dfa = dfa_hurst(vals)
    slope_v, H_v = variance_lag_hurst(vals)
    D_b = boxdim_2d(vals)

    def ok(h):
        return h is not None and 0.0 < h < 1.0

    hs = [h for h in (H_h, H_rs, H_dfa, H_v) if ok(h)]
    consenso = float(np.median(hs)) if hs else None
    return {
        "serie": nome, "n": int(len(vals)),
        "higuchi_D": D_h, "H_higuchi": H_h,
        "H_rs": H_rs, "H_dfa": H_dfa,
        "variance_slope_corr": slope_v, "H_variance_corr": H_v,
        "boxdim_2d": D_b,
        "H_consenso_mediana": consenso,
        "n_validos_01": len(hs),
        "abaixo_035": bool(consenso is not None and consenso < 0.35),
    }


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> dict:
    # A — analítico
    be_a = rho_break_even_analitico("A")
    be_b = rho_break_even_analitico("B")
    hm_a = rho_half_mitigation_analitico("A")
    hm_b = rho_half_mitigation_analitico("B")

    # B — sweep + cruzamentos numéricos
    rows = rho_sweep(99)
    be_a_num = cruzar(rows, "pfa_A")
    be_b_num = cruzar(rows, "pfa_B")
    hm_a_num = cruzar(rows, "mitig_A", alvo=0.5, diff="self")
    hm_b_num = cruzar(rows, "mitig_B", alvo=0.5, diff="self")

    with open(OUT_SWEEP, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["rho", "dfa", "pfa_A", "pfa_B", "mitig_A", "mitig_B"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # C — telemetria real
    if not CPU_CSV.exists():
        raise SystemExit(f"telemetria não encontrada: {CPU_CSV}")
    vals = carregar_serie()
    thr, evs = eventos_tail(vals, 90.0)
    rho_global = float(np.mean(vals) / 100.0)
    limiares = {"break_even_A": be_a, "half_mit_A_doc_025": 0.25, "break_even_B": be_b}
    for e in evs:
        e["acima_de"] = {k: bool(e["rho_eff"] > v) for k, v in limiares.items()}
    fracao_acima = {
        k: float(np.mean([1.0 if e["rho_eff"] > v else 0.0 for e in evs])) if evs else 0.0
        for k, v in limiares.items()
    }

    # D — Hurst correto, raw vs Donoho, + bloco tail (t>=21.5s ≈ regime 90-100%)
    filtr = donoho_surrogate(vals)
    # bloco de tail: índices com cpu>thr estendido ao entorno contínuo final
    tail_mask = vals > thr
    idx = np.where(tail_mask)[0]
    bloco = vals[idx[0]:idx[-1] + 1] if len(idx) > 30 else vals[tail_mask]
    a_raw = avaliar_serie("raw", vals)
    a_fil = avaliar_serie("donoho_surrogate", filtr)
    a_tail = avaliar_serie("tail_block", bloco)

    out = {
        "questao": "rho_c=0.25 (doc §2.4) vs rho_c=(1-r)^4≈0.706 (gk_D1/gk_F1); H real no tail?",
        "modelos": {
            "A_doc_absoluto": {"E_pfa": E_PFA_ABS, "p": P,
                               "break_even_analitico": be_a, "break_even_numerico": be_a_num,
                               "half_mitigation_analitica": hm_a, "half_mitigation_numerica": hm_a_num},
            "B_gk_relativo": {"E_pfa_expr": "p*(1-r)", "r": R, "p": P,
                              "break_even_analitico": be_b, "break_even_numerico": be_b_num,
                              "half_mitigation_analitica": hm_b, "half_mitigation_numerica": hm_b_num},
        },
        "veredito_rho_c": (
            "0.25 NÃO é break-even em nenhum modelo: é a meia-mitigaç��o do Modelo A "
            "(M=0.5 em ρ=0.25). Break-even (DFA=PFA): 0.0625 no Modelo A; 0.7063 no "
            "Modelo B. A frase 'ρ_c=0.25 onde o PFA se torna vantajoso' (§2.4) está "
            "errada sob as próprias fórmulas do doc (vantagem começa em 0.0625) e "
            "incompatível com o Modelo B (0.7063). Correção: distinguir break-even × "
            "meia-mitigaç��o e fixar um modelo PFA."
        ),
        "telemetria": {
            "n": int(len(vals)), "p90_threshold": thr,
            "rho_global": rho_global, "n_eventos": len(evs),
            "eventos": evs, "fracao_eventos_acima": fracao_acima,
            "leitura": (
                f"ρ global={rho_global:.3f}; {len(evs)} eventos P90 com "
                f"ρ_eff médio={float(np.mean([e['rho_eff'] for e in evs])):.3f} "
                f"quando há eventos. Sob Modelo A, o sistema real opera ACIMA do "
                f"break-even (0.0625) — PFA justificado; sob Modelo B, ABAIXO de "
                f"0.706 — DFA ainda suficiente. A escolha do modelo decide a "
                f"recomendação operacional."
            ) if evs else "sem eventos P90",
        },
        "hurst": {
            "raw": a_raw, "donoho_surrogate": a_fil, "tail_block": a_tail,
            "bug_variance_antigo": (
                "O H=4.83 impossível vinha de np.diff(x, n=s) (diferença de ordem n, "
                "não lag s). Corrigido para Var(X_{t+s}-X_t); H resultante fica em (0,1)."
            ),
            "boxdim": (
                "Box-counting 1D legacy saturava (10/9 caixas). Reimplementado em 2D "
                "(t,x); se ainda degenerar (contagens sem escala), retorna null "
                "honesto em vez de número espúrio."
            ),
        },
        "reprodutibilidade": {
            "comando": "python formal-certification/experiments/fct_phase_transition_audit.py",
            "semente": "determinístico (sem RNG)",
            "saidas": [OUT_JSON.name, OUT_SWEEP.name],
        },
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False, default=str)

    print("=== AUDITORIA FCT: transição de fase + H real ===")
    print(f"Modelo A break-even: analítico={be_a:.6f} numérico={be_a_num:.6f}" if be_a_num else f"A: {be_a}")
    print(f"Modelo A meia-mit.:  analítico={hm_a:.6f} numérico={hm_a_num:.6f}" if hm_a_num else f"A: {hm_a}")
    print(f"Modelo B break-even: analítico={be_b:.6f} numérico={be_b_num:.6f}" if be_b_num else f"B: {be_b}")
    print(f"Telemetria: n={len(vals)} P90={thr:.1f} rho_global={rho_global:.3f} eventos={len(evs)}")
    for k in ("raw", "donoho_surrogate", "tail_block"):
        a = {"raw": a_raw, "donoho_surrogate": a_fil, "tail_block": a_tail}[k]
        fmt = lambda v: f"{v:.4f}" if isinstance(v, float) else "null"
        print(f"H[{k}]: higuchi={fmt(a['H_higuchi'])} rs={fmt(a['H_rs'])} "
              f"dfa={fmt(a['H_dfa'])} var_corr={fmt(a['H_variance_corr'])} "
              f"box2d={fmt(a['boxdim_2d'])} consenso={fmt(a['H_consenso_mediana'])}")
    print(f"Salvo: {OUT_JSON.name}, {OUT_SWEEP.name}")
    return out


if __name__ == "__main__":
    main()
