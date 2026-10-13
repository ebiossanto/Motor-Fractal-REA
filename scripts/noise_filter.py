"""
Módulo de Filtragem de Ruído do Observador para Cálculo da Dimensão Fractal.

Implementa a correção do "Atrito do Observador" (R_o) mencionado no DOC-FCT-001:
- Decomposição Wavelet para separar ruído de alta frequência
- Limiarização suave de Donoho-Johnstone
- Correção do viés do observador no cálculo de Hurst

Referência: Paper 4 - Stochastic Relaxation (decorrelação de erros)
"""

import numpy as np
from typing import Tuple, Optional

try:
    import pywt
    PYWT_AVAILABLE = True
except ImportError:
    PYWT_AVAILABLE = False
    print("[AVISO] PyWavelets não instalado. Usando filtragem alternativa. Instale com: pip install PyWavelets")


class ObserverNoiseFilter:
    """
    Filtra o ruído do observador (OpenCode + scripts) das medições fractais.

    O princípio é o mesmo do PFA (Eixo 4): decorrelacionar o ruído
    para que ele não se acumule e distorça a estimativa da dimensão fractal.
    """

    def __init__(self, wavelet: str = 'db4', level: int = 4):
        """
        Inicializa o filtro.

        Args:
            wavelet: Família wavelet (db4 = Daubechies 4, boa para sinais com transientes)
            level: Nível de decomposição
        """
        self.wavelet = wavelet
        self.level = level
        self.noise_variance = None
        self.original_variance = None

    def estimate_noise_variance(self, series: np.ndarray) -> float:
        """
        Estima a variância do ruído usando o estimador MAD (Median Absolute Deviation).

        σ = MAD / 0.6745

        Args:
            series: Série temporal

        Returns:
            Variância estimada do ruído
        """
        if PYWT_AVAILABLE:
            # Usar coeficientes de detalhe do nível mais fino
            coeffs = pywt.wavedec(series, self.wavelet, level=1)
            detail_coeffs = coeffs[-1]
            mad = np.median(np.abs(detail_coeffs - np.median(detail_coeffs)))
            sigma = mad / 0.6745
            return sigma ** 2
        else:
            # Estimativa alternativa: diferenças de primeira ordem
            diffs = np.diff(series)
            mad = np.median(np.abs(diffs - np.median(diffs)))
            sigma = mad / 0.6745
            return sigma ** 2

    def filter_wavelet(self, series: np.ndarray) -> np.ndarray:
        """
        Aplica filtragem wavelet com limiarização suave.

        Args:
            series: Série temporal original

        Returns:
            Série filtrada
        """
        if not PYWT_AVAILABLE:
            return self._filter_alternative(series)

        # Decomposição wavelet
        coeffs = pywt.wavedec(series, self.wavelet, level=self.level)

        # Estimar ruído do nível mais fino
        detail_coeffs = coeffs[-1]
        mad = np.median(np.abs(detail_coeffs - np.median(detail_coeffs)))
        sigma = mad / 0.6745

        # Limiar universal de Donoho-Johnstone
        uthresh = sigma * np.sqrt(2 * np.log(len(series)))

        # Limiarização suave dos coeficientes de detalhe
        filtered_coeffs = [coeffs[0]]  # Manter aproximação
        for detail in coeffs[1:]:
            # Soft thresholding
            filtered_detail = np.sign(detail) * np.maximum(0, np.abs(detail) - uthresh)
            filtered_coeffs.append(filtered_detail)

        # Reconstrução
        filtered_series = pywt.waverec(filtered_coeffs, self.wavelet)

        # Ajustar tamanho (waverec pode retornar array maior)
        return filtered_series[:len(series)]

    def _filter_alternative(self, series: np.ndarray) -> np.ndarray:
        """
        Filtragem alternativa quando PyWavelets não está disponível.
        Usa média móvel ponderada + detecção de outliers.
        """
        # Média móvel com janela adaptativa
        window_size = max(3, len(series) // 20)
        filtered = np.copy(series).astype(float)

        # Suavização por média móvel
        for i in range(window_size, len(series) - window_size):
            window = series[i - window_size:i + window_size + 1]
            # Média ponderada (pesos maiores para o centro)
            weights = np.exp(-0.5 * ((np.arange(len(window)) - window_size) / (window_size / 2)) ** 2)
            weights /= np.sum(weights)
            filtered[i] = np.sum(window * weights)

        # Detecção e correção de outliers (beyond 3 sigma)
        std = np.std(filtered)
        mean = np.mean(filtered)
        outliers = np.abs(filtered - mean) > 3 * std
        filtered[outliers] = mean

        return filtered

    def correct_hurst_bias(self, H_observed: float, series: np.ndarray) -> float:
        """
        Corrige o viés do observador no cálculo de Hurst.

        H_corrigido = H_observado - (σ²_η / σ²_X) * ΔH_viés

        Args:
            H_observed: Hurst observado (bruto)
            series: Série temporal original

        Returns:
            Hurst corrigido
        """
        self.original_variance = np.var(series)
        self.noise_variance = self.estimate_noise_variance(series)

        if self.original_variance == 0:
            return H_observed

        # Fator de correção empírico (tipicamente ~0.1)
        delta_H = 0.1

        # Correção
        bias = (self.noise_variance / self.original_variance) * delta_H
        H_corrected = H_observed - bias

        # Garantir que H permanece em [0, 1]
        return max(0.0, min(1.0, H_corrected))

    def compute_snr(self, series: np.ndarray) -> float:
        """
        Calcula a razão sinal-ruído (SNR) da série.

        Args:
            series: Série temporal

        Returns:
            SNR em dB (limitado a [-100, 100] para evitar infinitos)
        """
        self.original_variance = np.var(series)
        self.noise_variance = self.estimate_noise_variance(series)

        if self.noise_variance <= 0 or not np.isfinite(self.noise_variance):
            return 100.0  # SNR máximo (ruído desprezível)

        signal_power = self.original_variance - self.noise_variance
        if signal_power <= 0 or not np.isfinite(signal_power):
            return -100.0  # SNR mínimo (ruído dominante)

        snr = 10 * np.log10(signal_power / self.noise_variance)

        # Limitar a [-100, 100] para evitar infinitos
        return float(np.clip(snr, -100.0, 100.0))

    def filter_and_correct(self, series: np.ndarray, H_observed: float) -> dict:
        """
        Executa pipeline completo de filtragem e correção.

        Args:
            series: Série temporal original
            H_observed: Hurst observado (bruto)

        Returns:
            Dicionário com resultados da filtragem
        """
        # 1. Filtrar ruído
        filtered = self.filter_wavelet(series)

        # 2. Calcular SNR
        snr = self.compute_snr(series)

        # 3. Corrigir Hurst
        H_corrected = self.correct_hurst_bias(H_observed, series)

        # 4. Calcular variância residual
        residual = series - filtered
        residual_variance = np.var(residual)

        return {
            'original_series': series,
            'filtered_series': filtered,
            'residual_variance': residual_variance,
            'noise_variance': self.noise_variance,
            'snr_db': snr,
            'hurst_observed': H_observed,
            'hurst_corrected': H_corrected,
            'correction_applied': H_observed - H_corrected
        }


def demonstrate_filtering_impact(series: np.ndarray, H_observed: float) -> dict:
    """
    Demonstra o impacto da filtragem na estimativa de Hurst.

    Args:
        series: Série temporal original
        H_observed: Hurst observado (bruto)

    Returns:
        Comparação antes/depois da filtragem
    """
    filter_obj = ObserverNoiseFilter()
    results = filter_obj.filter_and_correct(series, H_observed)

    # Calcular Hurst da série filtrada
    from hurst_calculator import compute_hurst_rs
    H_filtered = compute_hurst_rs(results['filtered_series'])

    results['hurst_filtered'] = H_filtered
    results['improvement'] = abs(H_filtered - 0.5) < abs(H_observed - 0.5)

    return results
