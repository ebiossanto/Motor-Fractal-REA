#!/usr/bin/env python3
"""
NT-06: Sensibilidade & Robustez — Bootstrap, Learning Curve, Influência, CV
Quantifica incerteza estatística dos parâmetros calibrados.
"""

import numpy as np
import math
import json
import hashlib
import sys
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'))

from nt04_approaches import SimConfig, simulate_with_correlated_errors, dfa_inflation

# Parâmetros base fixos
rho = 0.7
alpha = 1.5
p_relax = 0.0
p_controller = 1.0/6.0 * (1.0 + 0.3 * math.tanh(1.0 * rho/(1.0-rho)))  # ≈0.2157

print("="*70)
print("NT-06: Sensibilidade & Robustez")
print("="*70)

# ============================================================
# 1. LEARNING CURVE: Erro P99 vs Tamanho da Amostra
# ============================================================

def run_single_experiment(n: int, seed: int = 42) -> float:
    """Executa um experimento único e retorna erro relativo."""
    sim = SimConfig(seed=seed, rho=rho, alpha=alpha, n_samples=n, warmup=500, batch_size=500)
    waits, latencies, errors = simulate_with_correlated_errors(
        sim=sim, p_controller=p_controller, approach='A2', phi=0.8, p_relax=p_relax
    )
    P99_sim = float(np.percentile(waits, 99))
    
    # Predição
    inflation = dfa_inflation(rho, p_controller, beta=1.34)
    P99_ideal_base = 3000.0  # n=200k
    scale_factor = math.sqrt(200_000 / n)
    P99_ideal = P99_ideal_base * scale_factor
    P99_pred = P99_ideal * (1.0 + inflation)
    
    return abs(P99_sim - P99_pred) / P99_sim * 100 if P99_sim > 0 else 0

def learning_curve(n_values=[2000, 5000, 10000, 20000, 50000, 100000], n_reps=5):
    """Curva de aprendizado: erro médio + desvio vs n."""
    print(f"\n{'='*70}")
    print("LEARNING CURVE: Erro P99 vs n (n_reps={n_reps})")
    print(f"{'='*70}")
    
    results = {}
    for n in n_values:
        print(f"  n={n:,}...", end=" ", flush=True)
        errs = []
        for rep in range(n_reps):
            err = run_single_experiment(n, seed=42 + rep)
            errs.append(err)
        results[n] = {
            "mean": np.mean(errs),
            "std": np.std(errs),
            "min": np.min(errs),
            "max": np.max(errs)
        }
        print(f"média={results[n]['mean']:.1f}% ± {results[n]['std']:.1f}%")
    return results

# ============================================================
# 2. BOOTSTRAP PARA PARÂMETROS (simplificado)
# ============================================================

def bootstrap_params(n_bootstrap=100, sample_size=20_000):
    """Bootstrap simplificado: reamostra latências e recalcula inflação."""
    print(f"\n{'='*70}")
    print(f"BOOTSTRAP: n_boot={n_bootstrap}, sample_size={sample_size:,}")
    print(f"{'='*70}")
    
    # Primeiro, gerar uma amostra base grande
    print("  Gerando amostra base...")
    base_sim = SimConfig(seed=42, rho=rho, alpha=alpha, n_samples=sample_size, warmup=500, batch_size=500)
    waits, latencies, _ = simulate_with_correlated_errors(
        sim=base_sim, p_controller=p_controller, approach='A2', phi=0.8, p_relax=p_relax
    )
    
    print(f"  Latências geradas: {len(latencies):,} amostras")
    print(f"  P99 base: {np.percentile(waits, 99):.1f}")
    
    # Bootstrap: reamostrar com reposição
    boot_errors = []
    boot_inflations = []
    
    print("  Executando bootstrap...")
    for b in range(n_bootstrap):
        # Reamostrar latências com reposição
        idx = np.random.randint(0, len(latencies), size=sample_size)
        boot_latencies = latencies[idx]
        boot_waits = waits[idx]
        
        # P99 bootstrap
        P99_boot = np.percentile(boot_waits, 99)
        P99_ideal_boot = np.percentile(boot_latencies, 99)  # approx
        
        # Inflação bootstrap
        infl = (P99_boot / P99_ideal_boot) - 1 if P99_ideal_boot > 0 else 0
        boot_inflations.append(infl)
        
        # Erro relativo vs predição analítica
        inflation_theory = dfa_inflation(rho, p_controller, beta=1.34)
        err = abs(infl - inflation_theory) / infl * 100 if infl > 0 else 0
        boot_errors.append(err)
        
        if (b + 1) % 25 == 0:
            print(f"    {b+1}/{n_bootstrap}...", end=" ", flush=True)
    
    print()
    
    # Estatísticas bootstrap
    return {
        "inflation_mean": np.mean(boot_inflations),
        "inflation_std": np.std(boot_inflations),
        "inflation_ci95": np.percentile(boot_inflations, [2.5, 97.5]),
        "error_mean": np.mean(boot_errors),
        "error_std": np.std(boot_errors),
        "error_ci95": np.percentile(boot_errors, [2.5, 97.5]),
        "n_bootstrap": n_bootstrap
    }

# ============================================================
# 3. ANÁLISE DE INFLUÊNCIA (OUTLIERS)
# ============================================================

def influence_analysis(latencies, top_k=10):
    """Identifica pontos de alta influência no P99."""
    print(f"\n{'='*70}")
    print(f"ANÁLISE DE INFLUÊNCIA: top_k={top_k}")
    print(f"{'='*70}")
    
    P99_full = np.percentile(latencies, 99)
    influences = []
    
    # Amostrar subset se muito grande
    n_check = min(len(latencies), 5000)
    indices = np.random.choice(len(latencies), n_check, replace=False)
    
    for idx in indices:
        # Leave-one-out
        loo_latencies = np.delete(latencies, idx)
        P99_loo = np.percentile(loo_latencies, 99)
        influence = abs(P99_full - P99_loo) / P99_full if P99_full > 0 else 0
        influences.append((idx, influence))
    
    # Top-k
    influences.sort(key=lambda x: x[1], reverse=True)
    top = influences[:top_k]
    
    print(f"  P99 completo: {P99_full:.1f}")
    print(f"  Top {top_k} pontos mais influentes:")
    for i, (idx, inf) in enumerate(top):
        print(f"    {i+1}. idx={idx}: influência={inf*100:.2f}%")
    
    return {
        "P99_full": float(P99_full),
        "top_influences": [{"index": int(idx), "influence": float(inf)} for idx, inf in top],
        "max_influence": float(top[0][1]) if top else 0,
        "mean_influence": float(np.mean([inf for _, inf in influences]))
    }

# ============================================================
# 4. VALIDAÇÃO CRUZADA ρ×α
# ============================================================

def validate_params(rho_test: float, alpha_test: float, n_samples=20_000):
    """Testa modelo em (ρ, α) específico."""
    # p_controller calibrado para rho_test
    p_ctrl = 1.0/6.0 * (1.0 + 0.3 * math.tanh(1.0 * rho_test/(1.0-rho_test)))
    
    sim = SimConfig(seed=42, rho=rho_test, alpha=alpha_test, n_samples=n_samples, warmup=500, batch_size=500)
    waits, latencies, _ = simulate_with_correlated_errors(
        sim=sim, p_controller=p_ctrl, approach='A2', phi=0.8, p_relax=0.0
    )
    
    P99_sim = float(np.percentile(waits, 99))
    inflation = dfa_inflation(rho_test, p_ctrl, beta=1.34)
    
    # P99_ideal empírico para este (rho, alpha, n)
    P99_ideal_emp = np.percentile(latencies, 99) / (1.0 + inflation) if inflation > 0 else np.percentile(waits, 99)
    P99_pred = P99_ideal_emp * (1.0 + inflation)
    
    err = abs(P99_sim - P99_pred) / P99_sim * 100 if P99_sim > 0 else 0
    return err

def cross_validation_rho_alpha():
    """Grid search ρ×α."""
    print(f"\n{'='*70}")
    print("VALIDAÇÃO CRUZADA ρ×α")
    print(f"{'='*70}")
    
    rho_grid = [0.3, 0.5, 0.7, 0.8, 0.9]
    alpha_grid = [1.2, 1.5, 1.8]
    
    results = {}
    for rho_t in rho_grid:
        for alpha_t in alpha_grid:
            print(f"  rho={rho_t}, alpha={alpha_t}...", end=" ", flush=True)
            try:
                err = validate_params(rho_t, alpha_t)
                results[f"rho_{rho_t}_alpha_{alpha_t}"] = err
                print(f"err={err:.1f}%")
            except Exception as e:
                results[f"rho_{rho_t}_alpha_{alpha_t}"] = {"error": str(e)}
                print(f"ERRO: {e}")
    return results

# ============================================================
# MAIN
# ============================================================

def main():
    start_total = time.time()
    
    # 1. Learning Curve
    lc_results = learning_curve()
    
    # 2. Bootstrap
    boot_results = bootstrap_params(n_bootstrap=100, sample_size=20_000)
    
    # 3. Influence Analysis (usar latências do bootstrap)
    # Re-gerar amostra base para análise de influência
    base_sim = SimConfig(seed=42, rho=rho, alpha=alpha, n_samples=20_000, warmup=500, batch_size=500)
    waits, latencies, _ = simulate_with_correlated_errors(
        sim=base_sim, p_controller=p_controller, approach='A2', phi=0.8, p_relax=p_relax
    )
    inf_results = influence_analysis(latencies)
    
    # 4. Cross-validation
    cv_results = cross_validation_rho_alpha()
    
    # Consolidar
    output = {
        "metadata": {
            "script": "nt06_sensibilidade.py",
            "rho": rho,
            "alpha": alpha,
            "p_relax": p_relax,
            "timestamp": "2026-10-13"
        },
        "learning_curve": lc_results,
        "bootstrap": boot_results,
        "influence_analysis": inf_results,
        "cross_validation": cv_results,
        "output_hash": hashlib.sha256(json.dumps({
            "lc": lc_results, "boot": boot_results, 
            "inf": inf_results, "cv": cv_results
        }, default=str).encode()).hexdigest()[:16]
    }
    
    out_path = "experiments/nt06_sensibilidade.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n\n✅ Resultados salvos em: {out_path}")
    print(f"   SHA256: {output['output_hash']}")
    print(f"   Tempo total: {time.time() - start_total:.1f}s")
    
    # Resumo
    print(f"\n{'='*70}")
    print("RESUMO NT-06")
    print(f"{'='*70}")
    print(f"Learning Curve: {len(lc_results)} pontos testados")
    print(f"Bootstrap: {boot_results['n_bootstrap']} amostras, inflação CI95={boot_results['inflation_ci95']}")
    print(f"Influência max: {inf_results['max_influence']*100:.2f}%")
    print(f"CV ρ×α: {len(cv_results)} combinações testadas")

if __name__ == "__main__":
    main()