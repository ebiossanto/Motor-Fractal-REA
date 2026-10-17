#!/usr/bin/env python3
"""
NT-04: PFA Decorrelation — Multiple Approaches Comparison (VERSÃO RÁPIDA)
Seed: 42 fixo, Grid reduzido.
"""

import numpy as np
import math
from dataclasses import dataclass, asdict
from typing import Tuple, Dict, List, Optional
import json
import hashlib
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'))

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
    n_samples: int = 2_000    # Muito menor para teste rápido
    warmup: int = 200
    batch_size: int = 200


@dataclass(frozen=True)
class FCTConfig:
    E_dynamic: float = 1.0/6.0
    E_static: float = 1.0/12.0
    beta: float = 1.34
    rho_saturation: bool = True
    delta_sat: float = 2.0
    kappa_load: float = 0.3
    gamma_load: float = 1.0
    xi_hurst: float = 0.2
    pfa_enabled: bool = False
    pfa_relax_prob: float = 0.3
    pfa_beta_reduction: float = 0.5
    n_hops: int = 1
    hop_correlation: float = 0.0


# ============================================================
# APPROACH A1: Markov Chain Errors
# ============================================================

class MarkovErrorGenerator:
    def __init__(self, p_controller: float, p_relax: float, correlation_strength: float = 0.85):
        self.p_controller = p_controller
        self.p_relax = p_relax
        self.p_low = p_controller * 0.4
        self.p_high = p_controller * 1.6
        self.phi = correlation_strength
        self.matrix_dfa = np.array([[self.phi, 1 - self.phi],
                                     [1 - self.phi, self.phi]])
        self.matrix_random = np.array([[0.5, 0.5],
                                        [0.5, 0.5]])
        self.update_matrix_pfa()
    
    def update_matrix_pfa(self):
        self.matrix_pfa = (1 - self.p_relax) * self.matrix_dfa + self.p_relax * self.matrix_random
    
    def generate_sequence(self, n: int) -> np.ndarray:
        rng = np.random.default_rng(int(self.p_controller * 10000) % (2**31))
        state = rng.random() < 0.5
        errors = np.zeros(n, dtype=int)
        for i in range(n):
            p_err = self.p_low if state == 0 else self.p_high
            errors[i] = 1 if rng.random() < p_err else 0
            transition_probs = self.matrix_pfa[state]
            state = rng.random() < transition_probs[1]
        return errors


# ============================================================
# APPROACH A2: AR(1) Correlation Time
# ============================================================

class AR1ErrorGenerator:
    def __init__(self, phi: float, p_controller: float):
        self.phi = phi
        self.p_controller = p_controller
        self.threshold = float(np.percentile(np.random.randn(10_000), 100 * (1 - p_controller)))
    
    def generate_sequence(self, n: int) -> np.ndarray:
        rng = np.random.default_rng(42)
        X = np.zeros(n)
        errors = np.zeros(n, dtype=int)
        X[0] = rng.normal()
        errors[0] = 1 if X[0] > self.threshold else 0
        for i in range(1, n):
            X[i] = self.phi * X[i-1] + rng.normal()
            errors[i] = 1 if X[i] > self.threshold else 0
        return errors


# ============================================================
# APPROACH A3: Analytical FCT (baseline - sem sim)
# ============================================================

def pfa_analytical_inflation(rho: float, p_relax: float, 
                              E_star: float = 1.0/6.0, 
                              beta: float = 1.34) -> float:
    E_pfa = E_star - p_relax / 12.0
    E_pfa = max(E_pfa, E_star / 6)
    beta_pfa = beta * math.sqrt(1 - p_relax)
    if rho >= 1.0:
        return float('inf')
    load_factor = math.sqrt(rho) / (1.0 - rho)
    inflation = load_factor * (E_pfa ** beta_pfa)
    return inflation


def dfa_inflation(rho: float, p_controller: float, beta: float = 1.34) -> float:
    if rho >= 1.0:
        return float('inf')
    load_factor = rho / (1.0 - rho)
    inflation = load_factor * (p_controller ** beta)
    return inflation


# ============================================================
# SIMULATION WITH CORRELATED ERRORS
# ============================================================

def simulate_with_correlated_errors(sim: SimConfig, p_controller: float,
                                     approach: str = 'A1', 
                                     **kwargs) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(sim.seed)
    scale = sim.alpha - 1.0
    lam = sim.rho
    total = sim.n_samples + sim.warmup
    
    n = total
    if approach == 'A1':
        p_relax = kwargs.get('p_relax', 0.0)
        error_gen = MarkovErrorGenerator(p_controller, p_relax, 0.85)
        errors = error_gen.generate_sequence(n)
    elif approach == 'A2':
        phi = kwargs.get('phi', 0.8)
        error_gen = AR1ErrorGenerator(phi, p_controller)
        errors = error_gen.generate_sequence(n)
    elif approach == 'A3':
        errors = np.random.random(n) < p_controller
        errors = errors.astype(int)
    else:
        raise ValueError(f"Approach {approach} não reconhecido")
    
    u = rng.random(total)
    services = scale * (u ** (-1.0 / sim.alpha) - 1.0)
    
    if approach in ['A1', 'A2']:
        error_multipliers = np.where(errors == 1,
                                      1.0 + rng.exponential(2.0, total),
                                      1.0)
        services = services * error_multipliers
    
    inter_arrivals = rng.exponential(1.0 / lam, total)
    
    netput = services - inter_arrivals
    cumsum = np.cumsum(netput)
    running_min = np.minimum.accumulate(np.concatenate([[0], cumsum[:-1]]))
    waits = np.maximum(0, cumsum - running_min)
    
    waits = waits[sim.warmup:]
    latencies = waits + services[sim.warmup:]
    
    return waits, latencies, errors


# ============================================================
# EXPERIMENTAL GRID (REDUCIDA)
# ============================================================

def run_experiment_approach(approach: str, rho: float, alpha: float,
                             p_relax_values: List[float], 
                             base_sim: SimConfig, base_fct: FCTConfig) -> List[Dict]:
    results = []
    
    for p_relax in p_relax_values:
        load_factor = 1.0 + base_fct.kappa_load * math.tanh(base_fct.gamma_load * 
                                                              rho / (1.0 - rho))
        p_controller = base_fct.E_dynamic * load_factor
        
        if base_fct.pfa_enabled:
            p_controller_adj = (1 - p_relax) * p_controller + p_relax * base_fct.E_static
        else:
            p_controller_adj = p_controller
        
        try:
            waits, latencies, errors = simulate_with_correlated_errors(
                sim=SimConfig(seed=base_sim.seed, rho=rho, alpha=alpha,
                              n_samples=base_sim.n_samples, 
                              warmup=base_sim.warmup,
                              batch_size=base_sim.batch_size),
                p_controller=p_controller_adj,
                approach=approach,
                p_relax=p_relax,
                phi=0.85 if approach in ['A1', 'A2'] else None
            )
        except Exception as e:
            continue
        
        P99_sim = float(np.percentile(waits, 99))
        
        if approach == 'A3':
            inflation = pfa_analytical_inflation(rho, p_relax, 
                                                  base_fct.E_dynamic, base_fct.beta)
            P99_ideal_map = {0.5: 145, 0.7: 300, 0.9: 4800}
            P99_ideal = P99_ideal_map.get(rho, 1000)
            P99_pred = P99_ideal * (1.0 + inflation)
        else:
            inflation = dfa_inflation(rho, p_controller_adj, base_fct.beta)
            P99_ideal_map = {0.5: 145, 0.7: 300, 0.9: 4800}
            P99_ideal = P99_ideal_map.get(rho, 1000)
            P99_pred = P99_ideal * (1.0 + inflation)
        
        rel_err = abs(P99_sim - P99_pred) / P99_sim * 100 if P99_sim > 0 else 0
        
        H_rs = 0.5
        if FRACTAL_ENGINE_AVAILABLE and approach != 'A3':
            try:
                engine = FractalControlEngine()
                fractal_result = engine.run_fractal_canary_test(latencies.tolist())
                H_rs = fractal_result.get("hurst_exponent", 0.5)
            except:
                pass
        
        result = {
            "approach": approach,
            "rho": rho,
            "p_relax": p_relax,
            "p_controller": p_controller_adj,
            "P99_simulated": P99_sim,
            "P99_predicted": P99_pred,
            "relative_error_pct": rel_err,
            "H_rs": H_rs,
            "n_errors": int(np.sum(errors))
        }
        results.append(result)
        
    return results


def main():
    print("="*70)
    print("NT-04: PFA Decorrelation — Multiple Approaches (RÁPIDO)")
    print("="*70)
    
    base_sim = SimConfig()
    base_fct = FCTConfig()
    
    rhos = [0.5, 0.7]
    p_relax_values = [0.0, 0.3, 0.5]
    approaches = ['A1', 'A2', 'A3']
    
    all_results = []
    
    for approach in approaches:
        print(f"\n{'='*70}")
        print(f"EXPERIMENTO: Approach {approach}")
        print(f"{'='*70}")
        
        for rho in rhos:
            print(f"\n  rho={rho}")
            result = run_experiment_approach(approach, rho, base_sim.alpha, 
                                              p_relax_values, base_sim, base_fct)
            all_results.extend(result)
            
            for r in result:
                print(f"    p_relax={r['p_relax']:.1f} | P99_sim={r['P99_simulated']:.1f} | "
                      f"P99_pred={r['P99_predicted']:.1f} | err={r['relative_error_pct']:.1f}% | "
                      f"H={r['H_rs']:.3f} | n_err={r['n_errors']}")
    
    output = {
        "metadata": {
            "script": "nt04_approaches.py",
            "seed": base_sim.seed,
            "approaches_tested": approaches,
            "rho_values": rhos,
            "p_relax_values": p_relax_values,
            "timestamp": "2026-10-13"
        },
        "results": all_results
    }
    
    json_str = json.dumps(output, indent=2, ensure_ascii=False, default=str)
    hash_sha256 = hashlib.sha256(json_str.encode()).hexdigest()[:16]
    output["metadata"]["output_hash"] = hash_sha256
    
    out_path = "experiments/nt04_approach_results.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n\n✅ Resultados salvos em: {out_path}")
    print(f"   SHA256: {hash_sha256}")
    
    print("\n\n=== RESUMO COMPARATIVO ===")
    for approach in approaches:
        approach_results = [r for r in all_results if r['approach'] == approach]
        if not approach_results:
            continue
        mean_err = np.mean([r['relative_error_pct'] for r in approach_results])
        print(f"  {approach}: erro médio = {mean_err:.1f}% | n_points = {len(approach_results)}")
    
    best = min(all_results, key=lambda r: r['relative_error_pct']) if all_results else None
    if best:
        print(f"\n  Melhor: {best['approach']} rho={best['rho']} p_relax={best['p_relax']} err={best['relative_error_pct']:.1f}%")


if __name__ == "__main__":
    main()