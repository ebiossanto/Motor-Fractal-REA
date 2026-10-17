#!/usr/bin/env python3
"""
NT-08: Modelo P99 com Termo Linear Explicito (CORRIGIDO)
========================================================

Correcao: usar P99_ideal REAL da simulacao (p_controller=0),
nao o baseline_map hardcoded do NT-02.

O NT-02 usava baseline_map = {0.5: 1450, 0.7: 3000, 0.9: 48000}
mas o P99_ideal real da simulacao e:
  rho=0.5: ~417
  rho=0.7: ~1291  
  rho=0.9: ~1685

A inflacao REAL e:
  rho=0.5: 1650/417 - 1 = 2.96 (296%)
  rho=0.7: 3463/1291 - 1 = 1.68 (168%)
  rho=0.9: 55617/1685 - 1 = 32.0 (3200%)

O modelo anterior "calibrava" eta para compensar o baseline errado.
Agora testamos modelos fisicamente significativos.

Autor: Euzebio Soares
Data: 2026-10-13
"""
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Dict, List
import json
import hashlib
import math


# ============================================================================
# Configuracao
# ============================================================================

@dataclass(frozen=True)
class SimConfig:
    seed: int = 42
    rho: float = 0.7
    alpha: float = 1.5
    n_samples: int = 100_000
    warmup: int = 5_000


@dataclass(frozen=True)
class FCTParams:
    E_dynamic: float = 1.0 / 6.0
    E_static: float = 1.0 / 12.0
    beta: float = 1.34
    delta_sat: float = 2.0
    kappa_load: float = 0.3
    gamma_load: float = 1.0
    xi_hurst: float = 0.5


# ============================================================================
# Simulacao M/G/1-Pareto (vetorizada, Lindley recursion)
# ============================================================================

def simulate_mg1_waits(config: SimConfig, p_controller: float = 0.0) -> np.ndarray:
    """Simula M/G/1 Pareto. Retorna array de WAITS (tempo de espera na fila)."""
    rng = np.random.default_rng(config.seed)
    scale = config.alpha - 1.0
    lam = config.rho
    total = config.n_samples + config.warmup

    inter_arrivals = rng.exponential(1.0 / lam, total)
    u = rng.random(total)
    services = scale * (u ** (-1.0 / config.alpha) - 1.0)

    if p_controller > 0:
        controller_errors = rng.random(total) < p_controller
        error_multipliers = np.where(
            controller_errors,
            1.0 + rng.exponential(2.0, total),
            1.0
        )
        services = services * error_multipliers

    netput = services - inter_arrivals
    cumsum = np.cumsum(netput)
    running_min = np.minimum.accumulate(np.concatenate([[0], cumsum[:-1]]))
    waits = np.maximum(0, cumsum - running_min)

    waits = waits[config.warmup:]
    return waits


def hurst_pareto_mg1(rho: float, alpha: float) -> float:
    """Aproximacao analitica do expoente de Hurst."""
    H_0 = (3.0 - alpha) / 2.0
    return H_0 * (1.0 - 0.3 * rho)


def p_controller_rate(params: FCTParams, rho: float, H_rs: float) -> float:
    """Taxa de erro do controlador (Eixo 1 FCT)."""
    p_base = params.E_dynamic
    load_factor = 1.0 + params.kappa_load * math.tanh(
        params.gamma_load * rho / (1.0 - rho)
    )
    hurst_factor = 1.0
    if H_rs is not None and H_rs < 0.5 and H_rs > 0:
        hurst_factor = (0.5 / H_rs) ** params.xi_hurst
    p_ctrl = p_base * load_factor * hurst_factor
    return min(p_ctrl, 0.95)


def phi_saturation(params: FCTParams, rho: float) -> float:
    """Phi(rho) = (rho/(1-rho)) * tanh(delta*(1-rho)) — saturacao."""
    saturation = math.tanh(params.delta_sat * (1.0 - rho))
    return (rho / (1.0 - rho)) * saturation


def lambda_load(params: FCTParams, rho: float) -> float:
    """Lambda(rho) = 1 + kappa * tanh(gamma * rho/(1-rho))."""
    return 1.0 + params.kappa_load * math.tanh(
        params.gamma_load * rho / (1.0 - rho)
    )


# ============================================================================
# Modelos de inflacao eta
# ============================================================================

def model_A_old(rho, x, params, **kwargs):
    """Modelo A (antigo): eta = Phi(rho) * x^beta."""
    return phi_saturation(params, rho) * (x ** params.beta)


def model_B_linear(rho, x, params, a1=1.0, **kwargs):
    """Modelo B (linear puro): eta = a1 * x."""
    return a1 * x


def model_C_linear_phi(rho, x, params, a1=1.0, **kwargs):
    """Modelo C (linear + Phi): eta = Phi(rho) * a1 * x."""
    return phi_saturation(params, rho) * a1 * x


def model_D_lin_quad(rho, x, params, a1=1.0, a2=1.0, **kwargs):
    """Modelo D (linear + quadratico): eta = Phi(rho) * [a1*x + a2*x^beta]."""
    return phi_saturation(params, rho) * (a1 * x + a2 * (x ** params.beta))


def model_E_mm1_exact(rho, x, params, **kwargs):
    """Modelo E (M/M/1 exato): eta = x / (1 - rho - x).  DIVERGE."""
    denom = 1.0 - rho - x
    if denom <= 0:
        return 1e6
    return x / denom


def model_F_polynomial(rho, x, params, a1=1.0, a2=1.0, **kwargs):
    """Modelo F (polinomial): eta = a1*x + a2*x^2."""
    return a1 * x + a2 * x * x


def model_G_cubic(rho, x, params, a1=1.0, a2=1.0, a3=1.0, **kwargs):
    """Modelo G (cubico + Phi): eta = Phi(rho) * [a1*x + a2*x^2 + a3*x^3]."""
    return phi_saturation(params, rho) * (a1 * x + a2 * x * x + a3 * x ** 3)


# ============================================================================
# Geracao de dados com P99_ideal REAL
# ============================================================================

def generate_dataset(params: FCTParams, rhos, alphas, n_samples=100_000):
    """Gera dataset (rho, alpha, x, eta_real) usando P99_ideal REAL da simulacao."""
    data = []
    for rho in rhos:
        for alpha in alphas:
            sim = SimConfig(seed=42, rho=rho, alpha=alpha,
                            n_samples=n_samples, warmup=5000)
            H_rs = hurst_pareto_mg1(rho, alpha)

            # P99_ideal REAL (sem controller)
            waits_ideal = simulate_mg1_waits(sim, p_controller=0.0)
            p99_ideal = float(np.percentile(waits_ideal, 99))

            # p_controller (do modelo FCT)
            x = p_controller_rate(params, rho, H_rs)

            # P99_sim (com controller DFA)
            waits_sim = simulate_mg1_waits(sim, p_controller=x)
            p99_sim = float(np.percentile(waits_sim, 99))

            eta_actual = p99_sim / p99_ideal - 1.0

            data.append({
                'rho': rho,
                'alpha': alpha,
                'H_rs': H_rs,
                'p99_ideal': p99_ideal,
                'p99_sim': p99_sim,
                'x': x,
                'eta_actual': eta_actual,
                'phi': phi_saturation(params, rho),
                'lambda': lambda_load(params, rho),
            })
    return data


# ============================================================================
# Calibracao por minimos quadrados
# ============================================================================

def build_design_matrix(data, model_fn, param_names, base_params):
    """Constrói matriz de design A para modelo linear em parametros."""
    n = len(data)
    n_params = len(param_names)
    A = np.zeros((n, n_params))
    
    for i, d in enumerate(data):
        rho, x = d['rho'], d['x']
        for j, pname in enumerate(param_names):
            kwargs = {pn: 0.0 for pn in param_names}
            kwargs[pname] = 1.0
            A[i, j] = model_fn(rho, x, base_params, **kwargs)
    return A


def fit_linear_model(data, model_fn, param_names, base_params):
    """Ajusta modelo linear nos parametros: eta = sum(a_i * basis_i)."""
    A = build_design_matrix(data, model_fn, param_names, base_params)
    y = np.array([d['eta_actual'] for d in data])
    
    try:
        coeffs, residuals, rank, sv = np.linalg.lstsq(A, y, rcond=None)
    except np.linalg.LinAlgError:
        return None, None, None
    
    y_pred = A @ coeffs
    errors = np.abs(y_pred - y) / np.maximum(y, 1e-10) * 100
    return coeffs, float(np.mean(errors)), errors


def evaluate_fixed_model(data, model_fn, base_params):
    """Avalia modelo sem parametros livres (ex: Modelo A, E)."""
    errors = []
    for d in data:
        rho, x = d['rho'], d['x']
        eta_pred = model_fn(rho, x, base_params)
        eta_actual = d['eta_actual']
        err = abs(eta_pred - eta_actual) / max(eta_actual, 1e-10) * 100
        errors.append(err)
    return float(np.mean(errors)), np.array(errors)


# ============================================================================
# LOOCV
# ============================================================================

def loocv_error(data, model_fn, param_names, base_params):
    """LOOCV para modelo linear."""
    n = len(data)
    errors = []
    for held in range(n):
        train = [d for i, d in enumerate(data) if i != held]
        test = data[held]
        coeffs, _, _ = fit_linear_model(train, model_fn, param_names, base_params)
        if coeffs is None:
            errors.append(1e6)
            continue
        rho, x = test['rho'], test['x']
        eta_actual = test['eta_actual']
        A_test = np.zeros(len(param_names))
        for j, pname in enumerate(param_names):
            kwargs = {pn: 0.0 for pn in param_names}
            kwargs[pname] = 1.0
            A_test[j] = model_fn(rho, x, base_params, **kwargs)
        eta_pred = float(A_test @ coeffs)
        err = abs(eta_pred - eta_actual) / max(eta_actual, 1e-10) * 100
        errors.append(err)
    return float(np.mean(errors))


# ============================================================================
# Experimento principal
# ============================================================================

def main():
    print("=" * 72)
    print("NT-08: Modelo P99 com Termo Linear Explicito (CORRIGIDO)")
    print("=" * 72)

    params = FCTParams()

    # Grid de dados
    rhos = [0.5, 0.6, 0.7, 0.8, 0.9]
    alphas = [1.2, 1.5, 1.8, 2.0]

    print(f"\nGerando dataset: rho={rhos}, alpha={alphas}")
    print(f"Total: {len(rhos) * len(alphas)} pontos (n=100k cada, seed=42)")

    data = generate_dataset(params, rhos, alphas, n_samples=100_000)

    print(f"\n{'rho':>5} {'alpha':>6} {'x':>8} {'Phi':>8} {'eta_real':>10} {'P99_ideal':>10} {'P99_sim':>10}")
    print("-" * 72)
    for d in data:
        print(f"{d['rho']:5.1f} {d['alpha']:6.1f} {d['x']:8.4f} "
              f"{d['phi']:8.4f} {d['eta_actual']:10.4f} "
              f"{d['p99_ideal']:10.0f} {d['p99_sim']:10.0f}")

    # =========================================================================
    # Modelos sem parametros livres
    # =========================================================================
    print("\n" + "=" * 72)
    print("MODELOS SEM PARAMETROS LIVRES")
    print("=" * 72)

    err_A, _ = evaluate_fixed_model(data, model_A_old, params)
    print(f"Modelo A (antigo beta=1.34):   erro medio = {err_A:6.2f}%")

    err_E, _ = evaluate_fixed_model(data, model_E_mm1_exact, params)
    print(f"Modelo E (M/M/1 exato):        erro medio = {err_E:6.2f}%")

    # =========================================================================
    # Modelos com parametros livres (minimos quadrados)
    # =========================================================================
    print("\n" + "=" * 72)
    print("MODELOS COM PARAMETROS LIVRES (minimos quadrados)")
    print("=" * 72)

    coeffs_B, err_B, _ = fit_linear_model(data, model_B_linear, ['a1'], params)
    print(f"Modelo B (linear a1*x):        erro medio = {err_B:6.2f}%  "
          f"a1={coeffs_B[0]:.4f}")

    coeffs_C, err_C, _ = fit_linear_model(data, model_C_linear_phi, ['a1'], params)
    print(f"Modelo C (Phi*a1*x):           erro medio = {err_C:6.2f}%  "
          f"a1={coeffs_C[0]:.4f}")

    coeffs_D, err_D, _ = fit_linear_model(data, model_D_lin_quad, ['a1', 'a2'], params)
    print(f"Modelo D (Phi*[a1*x+a2*x^b]):  erro medio = {err_D:6.2f}%  "
          f"a1={coeffs_D[0]:.4f}, a2={coeffs_D[1]:.4f}")

    coeffs_F, err_F, _ = fit_linear_model(data, model_F_polynomial, ['a1', 'a2'], params)
    print(f"Modelo F (a1*x+a2*x^2):        erro medio = {err_F:6.2f}%  "
          f"a1={coeffs_F[0]:.4f}, a2={coeffs_F[1]:.4f}")

    coeffs_G, err_G, _ = fit_linear_model(data, model_G_cubic, ['a1', 'a2', 'a3'], params)
    print(f"Modelo G (Phi*[a1*x+a2*x^2+a3*x^3]): erro medio = {err_G:6.2f}%  "
          f"a1={coeffs_G[0]:.4f}, a2={coeffs_G[1]:.4f}, a3={coeffs_G[2]:.4f}")

    # =========================================================================
    # LOOCV
    # =========================================================================
    print("\n" + "=" * 72)
    print("VALIDACAO CRUZADA LEAVE-ONE-OUT (LOOCV)")
    print("=" * 72)

    loocv_A, _ = evaluate_fixed_model(data, model_A_old, params)
    loocv_B = loocv_error(data, model_B_linear, ['a1'], params)
    loocv_C = loocv_error(data, model_C_linear_phi, ['a1'], params)
    loocv_D = loocv_error(data, model_D_lin_quad, ['a1', 'a2'], params)
    loocv_F = loocv_error(data, model_F_polynomial, ['a1', 'a2'], params)
    loocv_G = loocv_error(data, model_G_cubic, ['a1', 'a2', 'a3'], params)

    print(f"Modelo A (antigo beta=1.34):   LOOCV = {loocv_A:6.2f}%")
    print(f"Modelo B (linear a1*x):        LOOCV = {loocv_B:6.2f}%")
    print(f"Modelo C (Phi*a1*x):           LOOCV = {loocv_C:6.2f}%")
    print(f"Modelo D (lin+quad):           LOOCV = {loocv_D:6.2f}%")
    print(f"Modelo F (polinomial):         LOOCV = {loocv_F:6.2f}%")
    print(f"Modelo G (cubico):             LOOCV = {loocv_G:6.2f}%")

    # =========================================================================
    # Analise de correlacao
    # =========================================================================
    print("\n" + "=" * 72)
    print("ANALISE: O TERMO LINEAR AJUDA?")
    print("=" * 72)

    etas = np.array([d['eta_actual'] for d in data])
    xs = np.array([d['x'] for d in data])
    phis = np.array([d['phi'] for d in data])

    corr_linear = np.corrcoef(xs, etas)[0, 1]
    corr_power = np.corrcoef(xs ** params.beta, etas)[0, 1]
    corr_phi_linear = np.corrcoef(phis * xs, etas)[0, 1]
    corr_phi_power = np.corrcoef(phis * xs ** params.beta, etas)[0, 1]

    print(f"Corr(eta, x)              = {corr_linear:+.4f}  (linear puro)")
    print(f"Corr(eta, x^beta)         = {corr_power:+.4f}  (potencia)")
    print(f"Corr(eta, Phi*x)          = {corr_phi_linear:+.4f}  (linear + Phi)")
    print(f"Corr(eta, Phi*x^beta)     = {corr_phi_power:+.4f}  (potencia + Phi)")

    ratio = etas / np.maximum(phis, 1e-10)
    corr_ratio_x = np.corrcoef(xs, ratio)[0, 1]
    corr_ratio_power = np.corrcoef(xs ** params.beta, ratio)[0, 1]
    print(f"\nCorr(eta/Phi, x)          = {corr_ratio_x:+.4f}")
    print(f"Corr(eta/Phi, x^beta)     = {corr_ratio_power:+.4f}")

    # =========================================================================
    # Conclusao
    # =========================================================================
    print("\n" + "=" * 72)
    print("CONCLUSAO")
    print("=" * 72)

    models = {
        'A_antigo': err_A,
        'B_linear': err_B,
        'C_linear_Phi': err_C,
        'D_lin_quad': err_D,
        'E_MM1_exato': err_E,
        'F_polinomial': err_F,
        'G_cubico': err_G,
    }
    best = min(models, key=models.get)
    print(f"Melhor modelo (erro medio): {best} = {models[best]:.2f}%")

    loocv_models = {
        'A_antigo': loocv_A,
        'B_linear': loocv_B,
        'C_linear_Phi': loocv_C,
        'D_lin_quad': loocv_D,
        'F_polinomial': loocv_F,
        'G_cubico': loocv_G,
    }
    best_loo = min(loocv_models, key=loocv_models.get)
    print(f"Melhor modelo (LOOCV):      {best_loo} = {loocv_models[best_loo]:.2f}%")

    improvement = (err_A - models[best]) / err_A * 100 if err_A > 0 else 0
    print(f"Melhoria vs Modelo A:       {improvement:+.1f}%")

    # =========================================================================
    # Salvar resultados
    # =========================================================================
    results = {
        'nt': 'NT-08',
        'title': 'Modelo P99 com Termo Linear Explicito (P99_ideal real)',
        'data': data,
        'models': {
            'A_old': {'error_mean_pct': err_A, 'loocv_pct': loocv_A,
                      'formula': 'eta = Phi(rho) * x^beta, beta=1.34'},
            'B_linear': {'error_mean_pct': err_B, 'loocv_pct': loocv_B,
                         'coeffs': coeffs_B.tolist() if coeffs_B is not None else None,
                         'formula': 'eta = a1 * x'},
            'C_linear_Phi': {'error_mean_pct': err_C, 'loocv_pct': loocv_C,
                             'coeffs': coeffs_C.tolist() if coeffs_C is not None else None,
                             'formula': 'eta = Phi(rho) * a1 * x'},
            'D_lin_quad': {'error_mean_pct': err_D, 'loocv_pct': loocv_D,
                           'coeffs': coeffs_D.tolist() if coeffs_D is not None else None,
                           'formula': 'eta = Phi(rho) * [a1*x + a2*x^beta]'},
            'E_MM1_exact': {'error_mean_pct': err_E, 'loocv_pct': err_E,
                            'formula': 'eta = x / (1 - rho - x)'},
            'F_polynomial': {'error_mean_pct': err_F, 'loocv_pct': loocv_F,
                             'coeffs': coeffs_F.tolist() if coeffs_F is not None else None,
                             'formula': 'eta = a1*x + a2*x^2'},
            'G_cubic': {'error_mean_pct': err_G, 'loocv_pct': loocv_G,
                        'coeffs': coeffs_G.tolist() if coeffs_G is not None else None,
                        'formula': 'eta = Phi(rho) * [a1*x + a2*x^2 + a3*x^3]'},
        },
        'correlations': {
            'corr_eta_x': float(corr_linear),
            'corr_eta_xbeta': float(corr_power),
            'corr_eta_phi_x': float(corr_phi_linear),
            'corr_eta_phi_xbeta': float(corr_phi_power),
            'corr_etaPhi_x': float(corr_ratio_x),
            'corr_etaPhi_xbeta': float(corr_ratio_power),
        },
        'best_model': best,
        'best_loocv': best_loo,
        'improvement_vs_A_pct': float(improvement),
        'parameters': {
            'E_dynamic': params.E_dynamic,
            'beta': params.beta,
            'delta_sat': params.delta_sat,
            'kappa_load': params.kappa_load,
            'gamma_load': params.gamma_load,
            'xi_hurst': params.xi_hurst,
        },
        'grid': {'rhos': rhos, 'alphas': alphas, 'n_samples': 100_000, 'seed': 42},
    }

    output_path = 'experiments/nt08_linear_term.json'
    # Serialização determinística para reprodutibilidade
    content = json.dumps(results, sort_keys=True, indent=2)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # Hash do arquivo salvo (bytes reais, inclui CRLF no Windows)
    with open(output_path, 'rb') as f:
        file_bytes = f.read()
    result_hash = hashlib.sha256(file_bytes).hexdigest()[:16]

    print(f"\nResultados salvos: {output_path}")
    print(f"Hash SHA256 (arquivo): {result_hash}")

    return results


if __name__ == "__main__":
    main()