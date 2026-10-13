"""
Módulo de cálculo do Expoente de Hurst via R/S Analysis e DFA.

Referências:
- Hurst, H.E. (1951). "Long-term storage capacity of reservoirs"
- Peng, C.K. et al. (1994). "Mosaic organization of DNA nucleotides"
- Mottl/hurst: https://github.com/Mottl/hurst
"""

import numpy as np
import math
from typing import Tuple, Optional


def compute_hurst_rs(time_series: np.ndarray, min_lag: int = 2, max_lag: Optional[int] = None) -> float:
    """
    Calcula o Expoente de Hurst via análise R/S (Rescaled Range).

    Args:
        time_series: Série temporal (1D numpy array)
        min_lag: Lag mínimo para análise
        max_lag: Lag máximo (padrão: len(series)//2)

    Returns:
        Expoente de Hurst (H)
    """
    if max_lag is None:
        max_lag = len(time_series) // 2

    lags = range(min_lag, max_lag + 1)
    rs_values = []

    for lag in lags:
        # Dividir a série em janelas de tamanho lag
        n_windows = len(time_series) // lag
        rs_window = []

        for i in range(n_windows):
            window = time_series[i * lag:(i + 1) * lag]
            if len(window) < 2:
                continue

            # Média da janela
            mean = np.mean(window)

            # Desvios acumulados
            deviations = np.cumsum(window - mean)

            # Range (R)
            R = np.max(deviations) - np.min(deviations)

            # Desvio padrão (S)
            S = np.std(window, ddof=1)
            if S == 0:
                continue

            rs_window.append(R / S)

        if rs_window:
            rs_values.append(np.mean(rs_window))

    if len(rs_values) < 2:
        return 0.5  # Valor padrão para ruído branco

    # Regressão linear: log(R/S) = H * log(lag) + c
    log_lags = np.log(list(lags)[:len(rs_values)])
    log_rs = np.log(rs_values)

    # Ajuste linear
    H, c = np.polyfit(log_lags, log_rs, 1)

    return H


def compute_dfa(time_series: np.ndarray, min_scale: int = 4, max_scale: Optional[int] = None,
                 order: int = 1) -> Tuple[float, np.ndarray, np.ndarray]:
    """
    Calcula o Detrended Fluctuation Analysis (DFA).

    Args:
        time_series: Série temporal (1D numpy array)
        min_scale: Escala mínima
        max_scale: Escala máxima (padrão: len(series)//4)
        order: Ordem do polinômio de detrending (1 = linear)

    Returns:
        Tuple (alpha, scales, fluctuation_function)
        onde alpha é o expoente de escala (≈ Hurst para ruído fracionário)
    """
    if max_scale is None:
        max_scale = len(time_series) // 4

    # Integrar a série (soma cumulativa dos desvios)
    integrated = np.cumsum(time_series - np.mean(time_series))

    scales = np.unique(np.logspace(np.log10(min_scale), np.log10(max_scale), num=20).astype(int))
    scales = scales[scales >= min_scale]

    F = np.zeros(len(scales))

    for i, scale in enumerate(scales):
        # Dividir em janelas de tamanho scale
        n_windows = len(integrated) // scale
        fluctuation = []

        for j in range(n_windows):
            window = integrated[j * scale:(j + 1) * scale]

            # Ajuste polinomial para remover tendência
            x = np.arange(len(window))
            coeffs = np.polyfit(x, window, order)
            trend = np.polyval(coeffs, x)

            # Flutuação quadrática média
            fluctuation.append(np.sqrt(np.mean((window - trend) ** 2)))

        F[i] = np.mean(fluctuation)

    # Regressão linear: log(F) = alpha * log(scale) + c
    log_scales = np.log(scales)
    log_F = np.log(F)

    alpha, c = np.polyfit(log_scales, log_F, 1)

    return alpha, scales, F


def compute_hurst_dfa(time_series: np.ndarray) -> float:
    """
    Calcula o Expoente de Hurst via DFA.

    Para ruído fracionário: H ≈ alpha
    Para fBm: H = alpha - 1
    """
    alpha, _, _ = compute_dfa(time_series)
    return alpha


def compute_permutation_entropy(time_series: np.ndarray, order: int = 3, delay: int = 1) -> float:
    """
    Calcula a Entropia de Permutação.

    Args:
        time_series: Série temporal
        order: Ordem do padrão (tipicamente 3-7)
        delay: Delay entre elementos do padrão

    Returns:
        Entropia de permutação normalizada [0, 1]
    """
    n = len(time_series)
    patterns = {}

    for i in range(n - (order - 1) * delay):
        # Extrair padrão
        pattern = tuple(np.argsort(time_series[i:i + order * delay:delay]))
        patterns[pattern] = patterns.get(pattern, 0) + 1

    # Calcular entropia
    total = sum(patterns.values())
    entropy = 0.0

    for count in patterns.values():
        p = count / total
        entropy -= p * np.log2(p)

    # Normalizar pelo máximo possível (log2(order!))
    max_entropy = math.log2(math.factorial(order))

    return entropy / max_entropy if max_entropy > 0 else 0.0


def compute_fractal_dimension_higuchi(time_series: np.ndarray, k_max: int = 10) -> float:
    """
    Calcula a Dimensão Fractal de Higuchi.

    Args:
        time_series: Série temporal
        k_max: Escala máxima

    Returns:
        Dimensão fractal (D_H)
    """
    n = len(time_series)
    L = []

    for k in range(1, k_max + 1):
        L_k = 0.0
        for m in range(k):
            # Comprimento da curva para escala k
            indices = np.arange(m, n, k)
            if len(indices) < 2:
                continue

            diffs = np.abs(np.diff(time_series[indices]))
            L_m = np.sum(diffs) * (n - 1) / (len(indices) * k)
            L_k += L_m

        L.append(L_k / k)

    # Regressão linear: log(L(k)) = -D_H * log(k) + c
    log_k = np.log(np.arange(1, k_max + 1))
    log_L = np.log(L)

    D_H, c = np.polyfit(log_k, log_L, 1)

    return -D_H


class FractalAnalyzer:
    """Analisador fractal completo para séries temporais de sistemas operacionais."""

    def __init__(self):
        self.results = {}

    def analyze(self, time_series: np.ndarray, label: str = "series") -> dict:
        """
        Executa análise fractal completa.

        Args:
            time_series: Série temporal
            label: Identificador da série

        Returns:
            Dicionário com todas as métricas fractais
        """
        if len(time_series) < 30:
            return {
                'label': label,
                'status': 'INSUFFICIENT_DATA',
                'sample_count': len(time_series)
            }

        # Hurst via R/S
        H_rs = compute_hurst_rs(time_series)

        # Hurst via DFA
        H_dfa = compute_hurst_dfa(time_series)

        # Dimensão fractal
        D_H = compute_fractal_dimension_higuchi(time_series)

        # Entropia de permutação
        S_p = compute_permutation_entropy(time_series)

        # Classificação
        if H_rs < 0.35:
            status = "CRITICAL_CAOTIC_ZONE"
            prediction = "Vulnerabilidade iminente a colapso por latência de cauda"
        elif H_rs <= 0.65:
            status = "NOMINAL_FRACTAL_STABILITY"
            prediction = "Sistema em equilíbrio metaestável saudável"
        else:
            status = "HIGHLY_PERSISTENT_STATE"
            prediction = "Tendências lineares previsíveis dominando o sistema"

        self.results[label] = {
            'label': label,
            'sample_count': len(time_series),
            'hurst_rs': round(H_rs, 4),
            'hurst_dfa': round(H_dfa, 4),
            'fractal_dimension': round(D_H, 4),
            'permutation_entropy': round(S_p, 4),
            'stability_status': status,
            'predictive_analysis': prediction
        }

        return self.results[label]

    def get_summary(self) -> dict:
        """Retorna resumo de todas as análises realizadas."""
        return self.results
