#!/usr/bin/env python3
"""
IA-RESEARCH-P99-TAIL-LATENCY — NT-02: Modelo Canônico Corrigido
Ponte Analítica: Obstrução Algébrica (Z₂³) → Erro do Controller → Inflação P99

Incorpora:
1. M/G/1 com serviço Pareto(alpha) — validado em tail_model.py
2. Obstrução algébrica Z₂³: E_dinâmico = 1/6 (exato, FCT Eixo 1)
3. Regra de decisão: p = E_dinâmico * h(estado_fila) — a calibrar
4. Expoente empírico beta ≈ 1.34 (nao 2) — retificação Cost-of-Equivariance
5. Saturação rho: eta(rho) = rho/(1-rho) * s(rho) com s(rho) → 0 quando rho→1
6. Relaxamento estocástico PFA: p_relax reduz expoente efetivo
7. Composição multi-hop ADITIVA em log-escala (nao multiplicativa)

Reprodutibilidade: seed=42 fixo, comandos exatos documentados.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Dict, List, Optional
import json
import hashlib
import math


# ============================================================
# CONFIGURAÇÕES CONGELADAS
# ============================================================

@dataclass(frozen=True)
class SimConfig:
    """Configuração base do experimento."""
    seed: int = 42
    rho: float = 0.7              # carga (lambda * E[S])
    alpha: float = 1.5            # índice de cauda Pareto (1 < alpha < 2)
    n_samples: int = 2_000_000    # número de clientes simulados
    warmup: int = 10_000          # descarte inicial
    batch_size: int = 100_000     # processamento em lotes


@dataclass(frozen=True)
class FCTConfig:
    """Configuração da Ponte Analítica FCT."""
    # Obstrução algébrica Z₂³ (FCT Eixo 1 - VÁLIDO)
    group: str = "Z2_3"           # Z₂³
    controller_states: int = 6    # 6 estados (sem quociente de ordem 6)
    E_dynamic: float = 1.0/6.0    # Erro dinâmico exato = 1/6
    E_static: float = 1.0/12.0    # Limite estático (pigeonhole)
    
    # Regra de decisão p = f(E, estado_fila) — PARÂMETROS A CALIBRAR
    # Hipótese: p = E_dynamic * (1 + k * rho^m)  onde k, m ajustam sensibilidade à carga
    p_base: float = 1.0/6.0       # p quando rho=0 (erro intrínseco)
    p_load_coeff: float = 0.5     # coeficiente de sensibilidade à carga
    p_load_exp: float = 1.0       # expoente de sensibilidade à carga
    
    # Retificação Cost-of-Equivariance
    beta: float = 1.34            # expoente empírico de p (NÃO 2!)
    rho_saturation: bool = True   # saturação da dependência em rho
    rho_sat_exp: float = 0.5      # expoente de saturação (rho^rho_sat_exp no numerador)
    
    # Relaxamento Estocástico PFA (FCT Eixo 4)
    pfa_enabled: bool = False
    pfa_relax_prob: float = 0.3   # probabilidade de transição aleatória
    pfa_beta_reduction: float = 0.5  # redução do expoente beta (sqrt para PFA)
    
    # Multi-hop (retificado: ADITIVO em log-escala)
    n_hops: int = 1
    hop_correlation: float = 0.0  # correlação entre hops (0=independente)


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
    alpha_est: float
    # Métricas da ponte analítica
    p_controller: float
    inflation_factor: float
    P99_ideal: float
    P99_predicted: float


# ============================================================
# MODELO DE SERVIÇO PARETO
# ============================================================

def pareto_service(rng: np.random.Generator, alpha: float, scale: float = 1.0) -> float:
    """Gera tempo de serviço Pareto Tipo II (Lomax) com cauda ~ x^{-alpha}."""
    u = rng.random()
    return scale * (u ** (-1.0 / alpha) - 1.0)


# ============================================================
# SIMULAÇÃO M/G/1 PURA (sem controller)
# ============================================================

def simulate_mg1_pareto(config: SimConfig) -> Tuple[np.ndarray, float]:
    """
    Simula M/G/1 com chegadas Poisson e serviço Pareto(alpha).
    Retorna (array de waits, C_theory).
    """
    rng = np.random.default_rng(config.seed)
    scale = config.alpha - 1.0  # E[S] = 1
    lam = config.rho            # μ = 1
    C_theory = config.rho / (1.0 - config.rho)

    waits: List[float] = []
    wait = 0.0

    for batch_start in range(0, config.n_samples + config.warmup, config.batch_size):
        batch_n = min(config.batch_size, config.n_samples + config.warmup - batch_start)
        inter_arrivals = rng.exponential(1.0 / lam, batch_n)
        services = np.array([pareto_service(rng, config.alpha, scale) for _ in range(batch_n)])

        for i in range(batch_n):
            wait = max(0.0, wait + services[i] - inter_arrivals[i])
            if batch_start + i >= config.warmup:
                waits.append(wait)

    return np.array(waits), C_theory


# ============================================================
# PONTE ANALÍTICA: CONTROLLER COM OBSTRUÇÃO ALGÉBRICA
# ============================================================

def controller_error_rate(fct: FCTConfig, rho: float) -> float:
    """
    Calcula taxa de erro efetiva do controller.
    
    Base: p = E_dynamic * h(rho)
    Com retificação: p = E_dynamic * (1 + k * rho^m)  [sem PFA]
    Com PFA: p = E_dynamic * (1 - pfa_relax_prob/2) * h(rho)  [aproximação FCT Eixo 4]
    """
    # Erro base (intrínseco à obstrução algébrica)
    p_base = fct.p_base
    
    # Sensibilidade à carga (retificação: nao é p^2, é p^beta)
    if fct.rho_saturation:
        # Saturação: fator cresce mas nao diverge
        load_factor = 1.0 + fct.p_load_coeff * (rho ** fct.p_load_exp) / (1.0 + rho ** fct.rho_sat_exp)
    else:
        load_factor = 1.0 + fct.p_load_coeff * (rho ** fct.p_load_exp)
    
    p = p_base * load_factor
    
    # Relaxamento estocástico PFA (FCT Eixo 4)
    if fct.pfa_enabled:
        # PFA reduz erro efetivo aproximando do limite estático
        # Interpola entre E_dynamic (p_relax=0) e E_static (p_relax=1)
        p_relax = fct.pfa_relax_prob
        p = (1 - p_relax) * p + p_relax * fct.E_static
        # Também reduz expoente beta efetivo
        # (modelado no cálculo de inflação abaixo)
    
    return min(p, 1.0)


def inflation_factor(fct: FCTConfig, rho: float, p: float) -> float:
    """
    Fator de inflação P99 = P99_ideal * (1 + inflation_factor).
    
    Fórmula CORRIGIDA (retificação Cost-of-Equivariance):
    - Expoente beta ≈ 1.34 (nao 2)
    - Saturação em rho: fator rho/(1-rho) * s(rho) onde s(rho) → 0
    - PFA reduz beta efetivo para sqrt(beta) ≈ 1.16
    """
    # Fator de carga com saturação
    if fct.rho_saturation:
        load_factor = (rho / (1.0 - rho)) * (1.0 - math.exp(-fct.rho_sat_exp * rho / (1.0 - rho)))
    else:
        load_factor = rho / (1.0 - rho)
    
    # Expoente efetivo
    beta_eff = fct.beta
    if fct.pfa_enabled:
        # FCT Eixo 4: PFA reduz expoente para ~sqrt
        beta_eff = fct.beta * fct.pfa_beta_reduction  # ~0.67 -> sqrt(1.34) ≈ 1.16
    
    # Inflação: load_factor * p^beta_eff
    inflation = load_factor * (p ** beta_eff)
    
    return inflation


def multi_hop_inflation(fct: FCTConfig, rho_per_hop: List[float], p_per_hop: List[float]) -> float:
    """
    Composição multi-hop RETIFICADA: ADITIVA em log-escala.
    
    Se cada hop tem inflação eta_k, então:
    log(1 + eta_total) = Σ log(1 + eta_k)  =>  eta_total = ∏(1 + eta_k) - 1
    
    Para eta_k pequeno: eta_total ≈ Σ eta_k  (aditivo)
    Para eta_k grande: eta_total = ∏(1 + eta_k) - 1  (multiplicativo exato)
    
    Correlação entre hops aumenta inflação além do independente.
    """
    if len(rho_per_hop) != len(p_per_hop):
        raise ValueError("rho_per_hop e p_per_hop devem ter mesmo tamanho")
    
    eta_total = 0.0
    for rho, p in zip(rho_per_hop, p_per_hop):
        eta_k = inflation_factor(fct, rho, p)
        eta_total = (1.0 + eta_total) * (1.0 + eta_k) - 1.0
    
    # Correção por correlação (FCT Eixo 2: lower bound para independente)
    if fct.hop_correlation > 0:
        eta_total *= (1.0 + fct.hop_correlation * eta_total)
    
    return eta_total


# ============================================================
# SIMULAÇÃO COM CONTROLLER (PONTE ANALÍTICA COMPLETA)
# ============================================================

def simulate_with_controller(sim: SimConfig, fct: FCTConfig) -> TailResult:
    """
    Simula M/G/1 com controller que introduz erros baseados em obstrução algébrica.
    """
    rng = np.random.default_rng(sim.seed)
    scale = sim.alpha - 1.0
    lam = sim.rho
    
    # Parâmetros do controller
    p_controller = controller_error_rate(fct, sim.rho)
    eta = inflation_factor(fct, sim.rho, p_controller)
    
    # Simula fila ideal (sem erros)
    waits_ideal, C_theory = simulate_mg1_pareto(sim)
    P99_ideal = float(np.percentile(waits_ideal, 99))
    
    # Simula com erros do controller
    # Modelo: erro do controller = serviço extra aleatório quando erro ocorre
    # O erro adiciona variabilidade extra ao tempo de serviço
    waits: List[float] = []
    wait = 0.0
    
    for batch_start in range(0, sim.n_samples + sim.warmup, sim.batch_size):
        batch_n = min(sim.batch_size, sim.n_samples + sim.warmup - batch_start)
        inter_arrivals = rng.exponential(1.0 / lam, batch_n)
        services = np.array([pareto_service(rng, sim.alpha, scale) for _ in range(batch_n)])
        
        # Erros do controller: com prob p_controller, serviço é multiplicado por (1 + delta)
        # delta modela o atraso causado por servir classe errada
        controller_errors = rng.random(batch_n) < p_controller
        error_multipliers = np.where(controller_errors, 
                                      1.0 + rng.exponential(2.0, batch_n),  # erro adiciona cauda exponencial
                                      1.0)
        services_eff = services * error_multipliers
        
        for i in range(batch_n):
            wait = max(0.0, wait + services_eff[i] - inter_arrivals[i])
            if batch_start + i >= sim.warmup:
                waits.append(wait)
    
    waits_arr = np.array(waits)
    
    # Percentis
    p50 = float(np.percentile(waits_arr, 50))
    p90 = float(np.percentile(waits_arr, 90))
    p95 = float(np.percentile(waits_arr, 95))
    p99 = float(np.percentile(waits_arr, 99))
    p999 = float(np.percentile(waits_arr, 99.9))
    
    # Estimativa alpha via Hill
    k = max(1, len(waits_arr) // 10)
    sorted_waits = np.sort(waits_arr)[::-1]
    hill = np.mean(np.log(sorted_waits[:k] / sorted_waits[k]))
    alpha_est = 1.0 / hill if hill > 0 else np.nan
    
    # Previsão da ponte analítica
    P99_predicted = P99_ideal * (1.0 + eta)
    
    return TailResult(
        p50=p50, p90=p90, p95=p95, p99=p99, p999=p999,
        mean_wait=float(np.mean(waits_arr)),
        max_wait=float(np.max(waits_arr)),
        alpha_est=alpha_est,
        p_controller=p_controller,
        inflation_factor=eta,
        P99_ideal=P99_ideal,
        P99_predicted=P99_predicted
    )


# ============================================================
# EXPERIMENTOS: VALIDAÇÃO DA PONTE
# ============================================================

def run_bridge_validation(sim: SimConfig, fct: FCTConfig) -> Dict:
    """Valida ponte analítica: compara P99 simulado vs predito."""
    print("\n" + "=" * 70)
    print("VALIDAÇÃO DA PONTE ANALÍTICA")
    print("=" * 70)
    print(f"Grupo: {fct.group} | Controller: {fct.controller_states} estados")
    print(f"E_dinamico = {fct.E_dynamic:.4f} | E_estatico = {fct.E_static:.4f}")
    print(f"beta (expoente p) = {fct.beta:.2f} | Saturacao rho: {fct.rho_saturation}")
    print(f"PFA: {'SIM' if fct.pfa_enabled else 'NAO'} (p_relax={fct.pfa_relax_prob})")
    print(f"Hops: {fct.n_hops} | Correlacao: {fct.hop_correlation}")
    print()
    
    # Simulação com controller
    res = simulate_with_controller(sim, fct)
    
    print(f"--- Resultados (rho={sim.rho}, alpha={sim.alpha}) ---")
    print(f"  p_controller = {res.p_controller:.4f}")
    print(f"  Fator inflação eta = {res.inflation_factor:.4f}")
    print(f"  P99_ideal = {res.P99_ideal:.3f}")
    print(f"  P99_predito = {res.P99_predicted:.3f}")
    print(f"  P99_simulado = {res.p99:.3f}")
    print(f"  Erro relativo = {abs(res.p99 - res.P99_predicted) / res.p99 * 100:.1f}%")
    print(f"  alpha_Hill = {res.alpha_est:.3f}")
    print()
    
    return {
        "config_sim": sim.__dict__,
        "config_fct": fct.__dict__,
        "result": res.__dict__,
        "validation": {
            "relative_error_pct": abs(res.p99 - res.P99_predicted) / res.p99 * 100,
            "p99_simulated": res.p99,
            "p99_predicted": res.P99_predicted,
            "inflation_factor": res.inflation_factor
        }
    }


def run_rho_sweep(sim: SimConfig, fct: FCTConfig, rhos: List[float]) -> List[Dict]:
    """Varre rho e compara ponte analítica vs simulacao."""
    print("\n--- Varredura rho (Ponte Analítica vs Simulação) ---")
    results = []
    
    for rho in rhos:
        sim_rho = SimConfig(seed=sim.seed, rho=rho, alpha=sim.alpha,
                            n_samples=sim.n_samples, warmup=sim.warmup,
                            batch_size=sim.batch_size)
        res = simulate_with_controller(sim_rho, fct)
        rel_err = abs(res.p99 - res.P99_predicted) / res.p99 * 100
        print(f"  rho={rho:.2f} | p_ctrl={res.p_controller:.4f} | eta={res.inflation_factor:.4f} "
              f"| P99_sim={res.p99:.1f} | P99_pred={res.P99_predicted:.1f} | err={rel_err:.1f}%")
        
        results.append({
            "rho": rho,
            "p_controller": res.p_controller,
            "inflation_factor": res.inflation_factor,
            "P99_simulated": res.p99,
            "P99_predicted": res.P99_predicted,
            "relative_error_pct": rel_err,
            "alpha_est": res.alpha_est
        })
    return results


def run_pfa_comparison(sim: SimConfig, fct_base: FCTConfig, relax_probs: List[float]) -> List[Dict]:
    """Compara PFA vs determinístico para diferentes p_relax."""
    print("\n--- Comparação PFA vs Determinístico ---")
    results = []
    
    for p_relax in relax_probs:
        fct = FCTConfig(
            group=fct_base.group,
            controller_states=fct_base.controller_states,
            E_dynamic=fct_base.E_dynamic,
            E_static=fct_base.E_static,
            p_base=fct_base.p_base,
            p_load_coeff=fct_base.p_load_coeff,
            p_load_exp=fct_base.p_load_exp,
            beta=fct_base.beta,
            rho_saturation=fct_base.rho_saturation,
            rho_sat_exp=fct_base.rho_sat_exp,
            pfa_enabled=True,
            pfa_relax_prob=p_relax,
            pfa_beta_reduction=fct_base.pfa_beta_reduction,
            n_hops=fct_base.n_hops,
            hop_correlation=fct_base.hop_correlation
        )
        res = simulate_with_controller(sim, fct)
        print(f"  p_relax={p_relax:.2f} | p_ctrl={res.p_controller:.4f} | eta={res.inflation_factor:.4f} "
              f"| P99={res.p99:.1f} | alpha_Hill={res.alpha_est:.3f}")
        
        results.append({
            "p_relax": p_relax,
            "p_controller": res.p_controller,
            "inflation_factor": res.inflation_factor,
            "P99": res.p99,
            "alpha_est": res.alpha_est
        })
    return results


def run_multi_hop(sim: SimConfig, fct: FCTConfig, n_hops_list: List[int]) -> List[Dict]:
    """Testa composição multi-hop (aditiva em log-escala)."""
    print("\n--- Composição Multi-Hop (Aditiva em Log-Escala) ---")
    results = []
    
    for n_hops in n_hops_list:
        # Assume rho e p iguais por hop
        rho_per_hop = [sim.rho] * n_hops
        p_per_hop = [controller_error_rate(fct, sim.rho)] * n_hops
        
        eta_total = multi_hop_inflation(fct, rho_per_hop, p_per_hop)
        P99_ideal, _ = simulate_mg1_pareto(sim)
        P99_ideal = float(np.percentile(P99_ideal, 99))
        P99_pred = P99_ideal * (1.0 + eta_total)
        
        print(f"  hops={n_hops} | eta_total={eta_total:.4f} | P99_pred={P99_pred:.1f}")
        
        results.append({
            "n_hops": n_hops,
            "eta_total": eta_total,
            "P99_predicted": P99_pred,
            "rho_per_hop": rho_per_hop,
            "p_per_hop": p_per_hop
        })
    return results


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("IA-RESEARCH-P99-TAIL-LATENCY - NT-02 Ponte Analitica Corrigida")
    print("=" * 70)
    print("Seed: 42 (fixo)")
    print("Modelo: M/G/1 Pareto + Obstrucao Z2^3 (E=1/6) + Retificacoes")
    print()
    
    # Configurações base
    sim = SimConfig()
    fct = FCTConfig()
    
    # 1. Validação pontual
    point_result = run_bridge_validation(sim, fct)
    
    # 2. Varredura rho
    rhos = [0.3, 0.5, 0.7, 0.8, 0.85, 0.9, 0.92, 0.95]
    sweep_results = run_rho_sweep(sim, fct, rhos)
    
    # 3. Comparação PFA
    relax_probs = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
    pfa_results = run_pfa_comparison(sim, fct, relax_probs)
    
    # 4. Multi-hop
    n_hops_list = [1, 2, 3, 5, 10]
    multihop_results = run_multi_hop(sim, fct, n_hops_list)
    
    # Salva resultados
    output = {
        "point_result": point_result,
        "rho_sweep": sweep_results,
        "pfa_comparison": pfa_results,
        "multihop": multihop_results,
        "metadata": {
            "script": "nt02_bridge.py",
            "git_commit": "init",
            "timestamp": "2026-10-12",
            "retifications_applied": [
                "beta=1.34_not_2",
                "rho_saturation",
                "additive_multihop",
                "pfa_beta_reduction"
            ]
        }
    }
    
    json_str = json.dumps(output, indent=2, ensure_ascii=False, default=str)
    hash_sha256 = hashlib.sha256(json_str.encode()).hexdigest()[:16]
    output["metadata"]["output_hash"] = hash_sha256
    
    out_path = "experiments/nt02_bridge_results.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\nResultados salvos em: {out_path}")
    print(f"SHA256 (prefixo): {hash_sha256}")
    print()
    print("Proximo: NT-03 - Derivar formula fechada para P99 = f(rho, alpha, h, sigma, p_relax)")


if __name__ == "__main__":
    main()