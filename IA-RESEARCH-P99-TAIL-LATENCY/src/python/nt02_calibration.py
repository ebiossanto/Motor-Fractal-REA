#!/usr/bin/env python3
"""
IA-RESEARCH-P99-TAIL-LATENCY — NT-02 Calibração Empírica (Versão Otimizada)
Usa operações vetorizadas numpy + Motor Fractal para calibração rápida.
"""

from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'))

import numpy as np
from dataclasses import dataclass, asdict
from typing import Tuple, Dict, List, Optional
import json
import hashlib
import math

# Importar Motor Fractal
try:
    from fractal_engine import FractalControlEngine
    FRACTAL_ENGINE_AVAILABLE = True
except ImportError as e:
    print(f"[AVISO] Motor Fractal não disponível: {e}")
    FRACTAL_ENGINE_AVAILABLE = False


@dataclass(frozen=True)
class SimConfig:
    seed: int = 42
    rho: float = 0.7
    alpha: float = 1.5
    n_samples: int = 50_000
    warmup: int = 1_000
    batch_size: int = 10_000


@dataclass(frozen=True)
class FCTConfig:
    E_dynamic: float = 1.0/6.0
    E_static: float = 1.0/12.0
    beta: float = 1.34
    rho_saturation: bool = True
    delta_sat: float = 0.8
    kappa_load: float = 0.5
    gamma_load: float = 1.0
    xi_hurst: float = 0.5
    pfa_enabled: bool = False
    pfa_relax_prob: float = 0.3
    pfa_beta_reduction: float = 0.5
    n_hops: int = 1
    hop_correlation: float = 0.0


@dataclass(frozen=True)
class CalibResult:
    rho: float
    alpha: float
    p_relax: float
    P99_simulated: float
    P99_predicted: float
    H_rs: float
    H_dfa: float
    relative_error_pct: float
    p_controller: float
    inflation_factor: float


def simulate_mg1_vectorized(config: SimConfig, p_controller: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Simulação M/G/1 Pareto totalmente vetorizada (sem loops Python).
    Muito mais rápida que versão loop-a-loop.
    """
    rng = np.random.default_rng(config.seed)
    scale = config.alpha - 1.0
    lam = config.rho
    total = config.n_samples + config.warmup
    
    # Gerar tudo de uma vez
    inter_arrivals = rng.exponential(1.0 / lam, total)
    u = rng.random(total)
    services = scale * (u ** (-1.0 / config.alpha) - 1.0)
    
    # Erros do controller (vetorizado)
    if p_controller > 0:
        controller_errors = rng.random(total) < p_controller
        error_multipliers = np.where(controller_errors, 
                                      1.0 + rng.exponential(2.0, total),
                                      1.0)
        services = services * error_multipliers
    
    # Lindley recursion VETORIZADA usando cumsum trick
    # W_{n+1} = max(0, W_n + S_n - A_{n+1})
    # Isso é equivalente a: W = maximum.accumulate(cumsum(S - A)) mas com floor em 0
    # Para implementação eficiente, usamos o algoritmo de Lindley vetorizado
    
    netput = services - inter_arrivals  # S_n - A_{n+1}
    # W_n = max(0, max_{k<=n} sum_{i=k}^n netput_i) = maximum of cumulative sum from any point
    # Implementação eficiente: running maximum of cumulative sum
    cumsum = np.cumsum(netput)
    # W_n = cumsum_n - min_{k<=n} cumsum_k, com floor em 0
    running_min = np.minimum.accumulate(np.concatenate([[0], cumsum[:-1]]))
    waits = np.maximum(0, cumsum - running_min)
    
    # Descarta warmup
    waits = waits[config.warmup:]
    latencies = waits + services[config.warmup:]
    
    return waits, latencies


def controller_error_rate(fct: FCTConfig, rho: float, H_rs: Optional[float] = None) -> Tuple[float, float]:
    """Calcula p_controller e eta (inflação)."""
    p_base = fct.E_dynamic
    
    if fct.rho_saturation:
        load_factor = 1.0 + fct.kappa_load * (rho ** fct.gamma_load) / (1.0 + rho ** fct.delta_sat)
    else:
        load_factor = 1.0 + fct.kappa_load * (rho ** fct.gamma_load)
    
    hurst_factor = 1.0
    if H_rs is not None and H_rs < 0.5 and H_rs > 0:
        hurst_factor = (0.5 / H_rs) ** fct.xi_hurst
    
    p_controller = p_base * load_factor * hurst_factor
    
    if fct.pfa_enabled:
        p_relax = fct.pfa_relax_prob
        p_controller = (1 - p_relax) * p_controller + p_relax * fct.E_static
    
    p_controller = min(p_controller, 1.0)
    
    # Inflação
    if fct.rho_saturation:
        load_factor_inf = (rho / (1.0 - rho)) * (1.0 - math.exp(-fct.delta_sat * rho / (1.0 - rho)))
    else:
        load_factor_inf = rho / (1.0 - rho)
    
    beta_eff = fct.beta
    if fct.pfa_enabled:
        beta_eff = fct.beta * fct.pfa_beta_reduction
    
    eta = load_factor_inf * (p_controller ** beta_eff) * (hurst_factor ** beta_eff)
    
    return p_controller, eta


def predict_p99_analytic(rho: float, alpha: float, p_controller: float, eta: float) -> float:
    """Prediz P99 usando fórmula analítica (baseline empírico interpolado)."""
    # Baseline P99_ideal conhecido para alpha=1.5
    if abs(alpha - 1.5) < 0.01:
        baseline_map = {0.3: 642, 0.5: 3261, 0.7: 10832, 0.8: 14367, 0.85: 15825, 
                        0.9: 17127, 0.92: 17621, 0.95: 18657}
        if rho in baseline_map:
            P99_ideal = baseline_map[rho]
        else:
            # Interpolação log-log
            rhos = np.array(list(baseline_map.keys()))
            vals = np.array(list(baseline_map.values()))
            log_rhos = np.log(rhos)
            log_vals = np.log(vals)
            P99_ideal = float(np.exp(np.interp(np.log(rho), log_rhos, log_vals)))
    else:
        # Aproximação grosseira para outros alpha
        P99_ideal = 10000 * (rho / 0.7) ** 2 * (1.5 / alpha)
    
    return P99_ideal * (1.0 + eta)


def run_calibration_point(rho: float, alpha: float, p_relax: float,
                           base_sim: SimConfig, base_fct: FCTConfig) -> CalibResult:
    sim = SimConfig(seed=base_sim.seed, rho=rho, alpha=alpha,
                    n_samples=base_sim.n_samples, warmup=base_sim.warmup,
                    batch_size=base_sim.batch_size)
    
    fct = FCTConfig(
        E_dynamic=base_fct.E_dynamic,
        E_static=base_fct.E_static,
        beta=base_fct.beta,
        rho_saturation=base_fct.rho_saturation,
        delta_sat=base_fct.delta_sat,
        kappa_load=base_fct.kappa_load,
        gamma_load=base_fct.gamma_load,
        xi_hurst=base_fct.xi_hurst,
        pfa_enabled=(p_relax > 0),
        pfa_relax_prob=p_relax,
        pfa_beta_reduction=base_fct.pfa_beta_reduction,
        n_hops=base_fct.n_hops,
        hop_correlation=base_fct.hop_correlation
    )
    
    # Primeira passada: simula sem saber H (p_controller inicial)
    p_ctrl_init, _ = controller_error_rate(fct, rho, None)
    waits, latencies = simulate_mg1_vectorized(sim, p_ctrl_init)
    P99_sim = float(np.percentile(waits, 99))
    
    # Análise fractal
    if FRACTAL_ENGINE_AVAILABLE:
        engine = FractalControlEngine()
        fractal_result = engine.run_fractal_canary_test(latencies.tolist())
        H_rs = fractal_result.get("hurst_exponent", 0.5)
        H_dfa = fractal_result.get("hurst_dfa", 0.5)
    else:
        H_rs = 0.5
        H_dfa = 0.5
    
    # Segunda passada: recalcula p_controller com H real
    p_ctrl, eta = controller_error_rate(fct, rho, H_rs)
    P99_pred = predict_p99_analytic(rho, alpha, p_ctrl, eta)
    
    rel_err = abs(P99_sim - P99_pred) / P99_sim * 100
    
    return CalibResult(
        rho=rho, alpha=alpha, p_relax=p_relax,
        P99_simulated=P99_sim,
        P99_predicted=P99_pred,
        H_rs=float(H_rs),
        H_dfa=float(H_dfa),
        relative_error_pct=rel_err,
        p_controller=p_ctrl,
        inflation_factor=eta
    )


def run_grid_calibration(base_sim: SimConfig, base_fct: FCTConfig) -> List[CalibResult]:
    rhos = [0.5, 0.7, 0.9]
    alphas = [1.5]
    p_relaxs = [0.0, 0.5]
    
    results = []
    total = len(rhos) * len(alphas) * len(p_relaxs)
    
    print(f"\n{'='*70}")
    print(f"CALIBRAÇÃO GRID: {total} pontos (vetorizado)")
    print(f"{'='*70}")
    
    for i, rho in enumerate(rhos):
        for alpha in alphas:
            for p_relax in p_relaxs:
                idx = i * len(alphas) * len(p_relaxs) + 1
                print(f"\n[{idx}/{total}] rho={rho}, alpha={alpha}, p_relax={p_relax}")
                res = run_calibration_point(rho, alpha, p_relax, base_sim, base_fct)
                results.append(res)
                print(f"  P99_sim={res.P99_simulated:.1f} | P99_pred={res.P99_predicted:.1f} | "
                      f"err={res.relative_error_pct:.1f}% | H_rs={res.H_rs:.3f} | p_ctrl={res.p_controller:.4f}")
    
    return results


def optimize_parameters(results: List[CalibResult]) -> Dict:
    print("\n" + "="*70)
    print("OTIMIZAÇÃO DE PARÂMETROS")
    print("="*70)
    
    kappa_grid = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]
    delta_grid = [0.4, 0.6, 0.8, 1.0, 1.2]
    xi_grid = [0.2, 0.3, 0.4, 0.5, 0.6, 0.8]
    
    best_score = float('inf')
    best_params = {}
    
    dfa_results = [r for r in results if r.p_relax == 0.0]
    
    for kappa in kappa_grid:
        for delta in delta_grid:
            for xi in xi_grid:
                errors = []
                for res in dfa_results:
                    fct_test = FCTConfig(
                        kappa_load=kappa,
                        delta_sat=delta,
                        xi_hurst=xi
                    )
                    p_ctrl, eta = controller_error_rate(fct_test, res.rho, res.H_rs)
                    P99_pred = predict_p99_analytic(res.rho, res.alpha, p_ctrl, eta)
                    err = abs(res.P99_simulated - P99_pred) / res.P99_simulated
                    errors.append(err)
                
                mean_err = np.mean(errors)
                if mean_err < best_score:
                    best_score = mean_err
                    best_params = {'kappa': kappa, 'delta': delta, 'xi': xi, 'mean_error': mean_err}
    
    print(f"Melhores: {best_params}")
    return best_params


def main():
    print("="*70)
    print("NT-02 Calibração P99 - Vetorizado + Motor Fractal")
    print("="*70)
    
    base_sim = SimConfig()
    base_fct = FCTConfig()
    
    # Calibração
    results = run_grid_calibration(base_sim, base_fct)
    
    # Otimização
    best_params = optimize_parameters(results)
    
    # Re-executa com melhores parâmetros
    print("\n" + "="*70)
    print("RE-EXECUÇÃO COM PARÂMETROS OTIMIZADOS")
    print("="*70)
    
    optimized_fct = FCTConfig(
        kappa_load=best_params.get('kappa', 0.5),
        delta_sat=best_params.get('delta', 0.8),
        xi_hurst=best_params.get('xi', 0.5)
    )
    
    optimized_results = run_grid_calibration(base_sim, optimized_fct)
    
    # Salva
    output = {
        "base_config": {"sim": asdict(base_sim), "fct": asdict(base_fct)},
        "optimized_params": best_params,
        "calibration_results": [asdict(r) for r in results],
        "optimized_results": [asdict(r) for r in optimized_results],
        "metadata": {
            "script": "nt02_calibration.py",
            "seed": base_sim.seed,
            "fractal_engine": FRACTAL_ENGINE_AVAILABLE,
            "timestamp": "2026-10-13"
        }
    }
    
    json_str = json.dumps(output, indent=2, ensure_ascii=False, default=str)
    hash_sha256 = hashlib.sha256(json_str.encode()).hexdigest()[:16]
    output["metadata"]["output_hash"] = hash_sha256
    
    out_path = "experiments/nt02_calibration_results.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n✅ Resultados: {out_path} | SHA256: {hash_sha256}")
    
    # Resumo
    all_errs = [r.relative_error_pct for r in optimized_results]
    print(f"\nErro médio geral: {np.mean(all_errs):.1f}% | Mediana: {np.median(all_errs):.1f}%")
    
    if np.mean(all_errs) < 15:
        print("🎯 META ATINGIDA: <15% — pronto para NT-03")
    else:
        print("⚠️ Erro alto — refinar modelo")


if __name__ == "__main__":
    main()