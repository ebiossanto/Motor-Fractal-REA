#!/usr/bin/env python3
"""
IA-RESEARCH-P99-TAIL-LATENCY — Simulador Mínimo para Validação NT-02
Modelo canônico: M/G/1 com tempo de serviço Pareto (cauda pesada, α ∈ (1,2))

Reprodutibilidade: seed=42 fixo, comandos exatos documentados.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Dict, List
import json
import hashlib


@dataclass(frozen=True)
class SimConfig:
    """Configuração congelada do experimento."""
    seed: int = 42
    rho: float = 0.7              # carga (λ * E[S])
    alpha: float = 1.5            # índice de cauda Pareto (1 < α < 2)
    n_samples: int = 2_000_000    # número de clientes simulados
    warmup: int = 10_000          # descarte inicial
    batch_size: int = 100_000     # processamento em lotes (memória)


@dataclass(frozen=True)
class TailResult:
    """Resultados de cauda com estatísticas de ordem."""
    p50: float
    p90: float
    p95: float
    p99: float
    p999: float
    mean_wait: float
    max_wait: float
    # Asintótico teórico (Zwart & Boxma 2000)
    C_theory: float
    alpha_est: float


def pareto_service(rng: np.random.Generator, alpha: float, scale: float = 1.0) -> float:
    """
    Gera tempo de serviço Pareto Tipo II (Lomax) com cauda ~ x^{-α}.
    E[S] = scale / (α - 1)  para α > 1.
    """
    # Inverse transform: F(x) = 1 - (1 + x/scale)^{-α}
    u = rng.random()
    return scale * (u ** (-1.0 / alpha) - 1.0)


def simulate_mg1_pareto(config: SimConfig) -> TailResult:
    """
    Simula M/G/1 com chegadas Poisson e serviço Pareto(α).
    Retorna estatísticas de tempo de espera na fila (W_q).
    """
    rng = np.random.default_rng(config.seed)

    # Escala do Pareto para obter E[S] = 1/μ tal que ρ = λ/μ
    # E[S] = scale / (α - 1)  =>  scale = (α - 1) / μ
    # ρ = λ * E[S] = λ * scale / (α - 1)
    # Fixamos μ = 1 => E[S] = 1 => scale = α - 1
    scale = config.alpha - 1.0
    lam = config.rho  # pois μ = 1

    # Constante teórica Zwart & Boxma: C = ρ/(1-ρ) * E[S^α] / E[S]  (para Pareto)
    # E[S^α] diverge para α ≤ 2; usamos a forma assintótica exata:
    # P(W > x) ~ (ρ/(1-ρ)) * P(S > x)  para serviços subexponenciais
    C_theory = config.rho / (1.0 - config.rho)

    waits: List[float] = []
    wait = 0.0
    next_arrival = 0.0

    for batch_start in range(0, config.n_samples + config.warmup, config.batch_size):
        batch_n = min(config.batch_size, config.n_samples + config.warmup - batch_start)

        # Gera chegadas e serviços do lote
        inter_arrivals = rng.exponential(1.0 / lam, batch_n)
        services = np.array([pareto_service(rng, config.alpha, scale) for _ in range(batch_n)])

        for i in range(batch_n):
            next_arrival += inter_arrivals[i]
            # Lindley recursion: W_{n+1} = max(0, W_n + S_n - A_{n+1})
            wait = max(0.0, wait + services[i] - inter_arrivals[i])

            if batch_start + i >= config.warmup:
                waits.append(wait)

    waits_arr = np.array(waits)

    # Percentis
    p50 = float(np.percentile(waits_arr, 50))
    p90 = float(np.percentile(waits_arr, 90))
    p95 = float(np.percentile(waits_arr, 95))
    p99 = float(np.percentile(waits_arr, 99))
    p999 = float(np.percentile(waits_arr, 99.9))

    # Estimativa de α via Hill estimator (top 10% da cauda)
    k = max(1, len(waits_arr) // 10)
    sorted_waits = np.sort(waits_arr)[::-1]
    hill = np.mean(np.log(sorted_waits[:k] / sorted_waits[k]))
    alpha_est = 1.0 / hill if hill > 0 else np.nan

    return TailResult(
        p50=p50, p90=p90, p95=p95, p99=p99, p999=p999,
        mean_wait=float(np.mean(waits_arr)),
        max_wait=float(np.max(waits_arr)),
        C_theory=C_theory,
        alpha_est=alpha_est
    )


def run_sweep_rho(config: SimConfig, rhos: List[float]) -> List[Dict]:
    """Varre ρ e coleta P99 para validar scaling law."""
    results = []
    for rho in rhos:
        cfg = SimConfig(seed=config.seed, rho=rho, alpha=config.alpha,
                        n_samples=config.n_samples, warmup=config.warmup,
                        batch_size=config.batch_size)
        res = simulate_mg1_pareto(cfg)
        results.append({
            "rho": rho,
            "alpha": config.alpha,
            "p50": res.p50, "p90": res.p90, "p95": res.p95,
            "p99": res.p99, "p999": res.p999,
            "mean_wait": res.mean_wait,
            "C_theory": res.C_theory,
            "alpha_est": res.alpha_est
        })
        print(f"rho={rho:.2f}  P99={res.p99:.3f}  C_theory={res.C_theory:.3f}  alpha_est={res.alpha_est:.3f}")
    return results


def main():
    print("=" * 70)
    print("IA-RESEARCH-P99-TAIL-LATENCY - NT-02 Validacao Empirica")
    print("=" * 70)
    print("Seed: 42 (fixo)")
    print("Modelo: M/G/1 com servico Pareto(alpha)")
    print()

    # Configuração base
    base_config = SimConfig()

    # Validação pontual (ρ=0.7, α=1.5)
    print("--- Validação pontual ---")
    res = simulate_mg1_pareto(base_config)
    print(f"rho={base_config.rho}, alpha={base_config.alpha}")
    print(f"  P50={res.p50:.3f}  P90={res.p90:.3f}  P95={res.p95:.3f}  P99={res.p99:.3f}  P99.9={res.p999:.3f}")
    print(f"  E[W]={res.mean_wait:.3f}  max={res.max_wait:.3f}")
    print(f"  C_theory (rho/(1-rho))={res.C_theory:.3f}  alpha_Hill={res.alpha_est:.3f}")
    print()

    # Varredura rho para lei de escala
    print("--- Varredura rho (scaling law P99 vs rho) ---")
    rhos = [0.3, 0.5, 0.7, 0.8, 0.85, 0.9, 0.92, 0.95]
    sweep_results = run_sweep_rho(base_config, rhos)

    # Salva resultados (JSON + hash para reprodutibilidade)
    output = {
        "config": base_config.__dict__,
        "point_result": res.__dict__,
        "sweep": sweep_results,
        "metadata": {
            "script": "tail_model.py",
            "git_commit": "init",
            "timestamp": "2026-10-12"
        }
    }

    json_str = json.dumps(output, indent=2, ensure_ascii=False)
    hash_sha256 = hashlib.sha256(json_str.encode()).hexdigest()[:16]
    output["metadata"]["output_hash"] = hash_sha256

    out_path = "experiments/nt02_validation_results.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Resultados salvos em: {out_path}")
    print(f"   SHA256 (prefixo): {hash_sha256}")
    print()
    print("Próximo: NT-02 — Derivar lei de escala P99 ~ C(ρ) * x^{-α} e comparar.")


if __name__ == "__main__":
    main()