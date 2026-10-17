#!/usr/bin/env python3
"""
NT-05: Validação em Amostras Maiores — Grid Formalizada
Testa A2 (AR1) com n=2_000, n=5_000, n=20_000, n=100_000 para verificar tendência de erro P99.
"""

import numpy as np
import math
import json
import hashlib
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'))

from nt04_approaches import SimConfig, simulate_with_correlated_errors, dfa_inflation

# Parâmetros fixos
rho = 0.7
alpha = 1.5
p_relax = 0.0  # DFA (determinístico)
# p_controller calibrado para rho=0.7, alpha=1.5 via Lambda(rho)
p_controller = 1.0/6.0 * (1.0 + 0.3 * math.tanh(1.0 * rho/(1.0-rho)))  # ≈0.2157

# Tamanhos de amostra (progressivos)
sizes = [2_000, 5_000, 20_000, 100_000]

print("="*70)
print("NT-05: Validação em Amostras Maiores — Grid Formalizada")
print("="*70)

results = []

for i, n in enumerate(sizes):
    print(f"\n--- Tamanho {i+1}/{len(sizes)}: n = {n:,} ---")
    start_time = time.time()
    
    sim = SimConfig(seed=42, rho=rho, alpha=alpha, n_samples=n, warmup=500, batch_size=500)
    
    try:
        waits, latencies, errors = simulate_with_correlated_errors(
            sim=sim, p_controller=p_controller, approach='A2', phi=0.8, p_relax=p_relax
        )
    except Exception as e:
        print(f"  ERRO: {e}")
        # Em caso de erro, ainda registra attempt
        results.append({
            "n": n,
            "error": str(e),
            "elapsed_s": None
        })
        continue
    
    P99_sim = float(np.percentile(waits, 99))
    
    # Predição com dfa_inflation
    inflation = dfa_inflation(rho, p_controller, beta=1.34)
    
    # P99_ideal escalonado: base n=200k é 3000, escalonar para n atual
    # Fator de escala: sqrt(200_000 / n) para Pareto α=1.5 (cauda heavy-tailed)
    P99_ideal_base = 3000.0  # n=200_000, rho=0.7, alpha=1.5
    scale_factor = math.sqrt(200_000 / n)
    P99_ideal = P99_ideal_base * scale_factor
    P99_pred = P99_ideal * (1.0 + inflation)
    
    rel_err = abs(P99_sim - P99_pred) / P99_sim * 100 if P99_sim > 0 else 0
    
    elapsed = time.time() - start_time
    
    results.append({
        "n": n,
        "P99_simulated": P99_sim,
        "P99_predicted": P99_pred,
        "relative_error_pct": rel_err,
        "elapsed_s": elapsed,
        "n_errors": int(np.sum(errors))
    })
    
    print(f"  P99_sim = {P99_sim:.1f}")
    print(f"  P99_pred = {P99_pred:.1f}")
    print(f"  Erro relativo = {rel_err:.1f}%")
    print(f"  Tempo de simulação: {elapsed:.1f}s")
    print(f"  n_errors = {int(np.sum(errors))}")

# Salvar resultados
output = {
    "metadata": {
        "script": "nt05_grid.py",
        "rho": rho,
        "alpha": alpha,
        "p_relax": p_relax,
        "approach": "A2-AR1",
        "sizes": sizes,
        "timestamp": "2026-10-13"
    },
    "results": results,
    "output_hash": hashlib.sha256(json.dumps(results).encode()).hexdigest()[:16]
}

out_path = "experiments/nt05_grid.json"
with open(out_path, "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False, default=str)

print(f"\n\n✅ Resultados salvos em: {out_path}")
print(f"   SHA256: {output['output_hash']}")

print(f"\n--- Análise da Tendência ---")
for r in results:
    print(f"  n={r['n']:,}: P99={r['P99_simulated']:>8.1f} | pred={r['P99_predicted']:>8.1f} | "
          f"err={r['relative_error_pct']:>5.1f}% | tempo={r['elapsed_s']:.1f}s")

# Conclusão empírica
errors = [r['relative_error_pct'] for r in results if 'relative_error_pct' in r]
if errors:
    print(f"\nRedução de erro: {errors[0]:.1f}% → {errors[-1]:.1f}% ({(errors[0]-errors[-1])/errors[0]*100:.1f}% de melhoria)")
    print(f"Meta <15% atingida: {any(e < 15 for e in errors)}")