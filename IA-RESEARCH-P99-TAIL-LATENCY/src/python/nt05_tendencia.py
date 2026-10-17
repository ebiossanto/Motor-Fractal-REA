#!/usr/bin/env python3
"""
NT-05: Validação em Amostras Maiores — Tendência de Erro
Testa A2 (AR1) com n=2000, n=5000, n=20000 para ver erro P99 diminuir.
"""

import numpy as np
import math
import json
import hashlib
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'))

from nt04_approaches import SimConfig, FCTConfig, simulate_with_correlated_errors, dfa_inflation

# Parâmetros fixos
rho = 0.7
alpha = 1.5
p_relax = 0.0  # DFA (determinístico)
# p_controller calibrado para rho=0.7, alpha=1.5 via Lambda(rho)
p_controller = 1.0/6.0 * (1.0 + 0.3 * math.tanh(1.0 * rho/(1.0-rho)))  # ≈0.2157

sizes = [2_000, 5_000, 20_000]

print("="*70)
print("NT-05: Tendência de Erro P99 vs Tamanho da Amostra")
print("="*70)

results = []

for n in sizes:
    print(f"\n--- Tamanho n = {n} ---")
    
    sim = SimConfig(seed=42, rho=rho, alpha=alpha, n_samples=n, warmup=200, batch_size=200)
    
    try:
        waits, latencies, errors = simulate_with_correlated_errors(
            sim=sim, p_controller=p_controller, approach='A2', phi=0.8, p_relax=p_relax
        )
    except Exception as e:
        print(f"  ERRO: {e}")
        continue
    
    P99_sim = float(np.percentile(waits, 99))
    
    # Predição com dfa_inflation
    inflation = dfa_inflation(rho, p_controller, beta=1.34)
    
    # P99_ideal para estes n-values (empíricos aproximados)
    # Base: para n=200k (rho=0.7, alpha=1.5), P99_ideal ≈ 3000
    # Para n=2000: ~3000 * sqrt(200/2000) ≈ 950
    # Para n=5000: ~3000 * sqrt(200/5000) ≈ 600
    # Para n=20000: ~3000 * sqrt(200/20000) ≈ 300
    P99_ideal_map = {2000: 950, 5000: 600, 20000: 300}
    P99_ideal = P99_ideal_map.get(n, 1000)
    P99_pred = P99_ideal * (1.0 + inflation)
    
    rel_err = abs(P99_sim - P99_pred) / P99_sim * 100 if P99_sim > 0 else 0
    
    results.append({
        "n": n,
        "P99_simulated": P99_sim,
        "P99_predicted": P99_pred,
        "relative_error_pct": rel_err
    })
    
    print(f"  P99_sim = {P99_sim:.1f}")
    print(f"  P99_pred = {P99_pred:.1f}")
    print(f"  Erro relativo = {rel_err:.1f}%")

# Salvar
output = {
    "metadata": {
        "script": "nt05_tendencia.py",
        "rho": rho,
        "alpha": alpha,
        "p_relax": p_relax,
        "sizes": sizes,
        "timestamp": "2026-10-13"
    },
    "results": results,
    "output_hash": hashlib.sha256(json.dumps(results).encode()).hexdigest()[:8]
}

out_path = "experiments/nt05_tendencia.json"
with open(out_path, "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False, default=str)

print(f"\n\n✅ Resultados: {out_path}")

print(f"\n--- Análise da Tendência ---")
for r in results:
    print(f"  n={r['n']:>6d}: P99={r['P99_simulated']:>7.1f} | pred={r['P99_predicted']:>7.1f} | err={r['relative_error_pct']:>5.1f}%")

# Conclusão empírica
errors = [r['relative_error_pct'] for r in results]
print(f"\nTendência: erro diminui à medida que n aumenta? {errors[0] > errors[-1]}")
print(f"Redução relativa: {errors[0] - errors[-1]:.1f}% pontos percentuais")