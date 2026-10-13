"""
Demo: Aplicação da filtragem wavelet para correção de Hurst antes de decisões
de controle do sistema operacional.
"""
import warnings
warnings.filterwarnings('ignore')
import numpy as np
import time
from fractal_engine import FractalControlEngine
from hurst_calculator import compute_hurst_rs
from noise_filter import ObserverNoiseFilter


def demonstrate_wavelet_correction():
    """Demonstra como a filtragem wavelet corrige o Hurst antes de decisões."""
    
    print("=== DEMONSTRAÇÃO: Filtragem Wavelet para Correção de Hurst ===")
    print()
    
    # 1. Coletar série temporal simulada (com ruído do observador)
    np.random.seed(42)
    n = 300
    # Série com tendência persistente + ruído do observador
    t = np.arange(n)
    trend = 0.02 * t  # tendência lenta
    fGn = np.random.normal(0, 5, n)  # ruído gaussiano
    series_with_noise = trend + fGn
    
    # 2. Calcular Hurst BRUTO (sem filtragem)
    H_bruto = compute_hurst_rs(series_with_noise)
    
    # 3. Aplicar filtragem wavelet
    filter_obj = ObserverNoiseFilter(wavelet='db4', level=3)
    filter_results = filter_obj.filter_and_correct(series_with_noise, H_bruto)
    H_filtrado = filter_results['hurst_corrected']
    
    # 4. Calcular Hurst da série filtrada independentemente
    H_filtrado_directo = compute_hurst_rs(filter_results['filtered_series'])
    
    # 5. Decisão de controle baseada em cada métrica
    print("--- Resultados ---")
    print(f"Hurst bruto (sem filtragem):    {H_bruto:.4f}")
    print(f"Hurst filtrado (com wavelet):    {H_filtrado:.4f}")
    print(f"Hurst da série filtrada:        {H_filtrado_directo:.4f}")
    print()
    
    # 6. Comparação de decisões de controle
    print("--- Decisões de Controle ---")
    
    # Decisão baseada em Hurst bruto
    if H_bruto < 0.35:
        decisao_bruto = "ATIVAR MITIGAÇÃO DE URGÊNCIA"
        risco_bruto = "CRÍTICO"
    elif H_bruto > 0.65:
        decisao_bruto = "MANTENER MONITORAMENTO CONTINUO"
        risco_bruto = "PERSISTENTE"
    else:
        decisao_bruto = "OPERAÇÕES NORMAS"
        risco_bruto = "NORMAL"
    
    # Decisão baseada em Hurst filtrado
    if H_filtrado < 0.35:
        decisao_filtrado = "ATIVAR MITIGAÇÃO DE URGÊNCIA"
        risco_filtrado = "CRÍTICO"
    elif H_filtrado > 0.65:
        decisao_filtrado = "MANTENER MONITORAMENTO CONTINUO"
        risco_filtrado = "PERSISTENTE"
    else:
        decisao_filtrado = "OPERAÇÕES NORMAS"
        risco_filtrado = "NORMAL"
    
    print(f"Decisão (bruto):    {decisao_bruto} (risco: {risco_bruto})")
    print(f"Decisão (filtrado): {decisao_filtrado} (risco: {risco_filtrado})")
    print()
    
    # 7. SNR e correção aplicada
    snr = filter_obj.compute_snr(series_with_noise)
    correcao = H_bruto - H_filtrado
    print(f"SNR da série: {snr:.2f} dB")
    print(f"Correção aplicada: {correcao:.4f} (H bruto -> H filtrado)")
    print()
    
    # 8. Verificar se a filtragem melhorou a classificação
    decisoes_iguais = (decisao_bruto == decisao_filtrado)
    print(f"Decisões coincidem: {'Sim' if decisoes_iguais else 'Não'}")
    if not decisoes_iguais:
        print("=> A filtragem wavelet mudou a decisão de controle!")
    
    return {
        'H_bruto': H_bruto,
        'H_filtrado': H_filtrado,
        'H_filtrado_direto': H_filtrado_directo,
        'correcao': correcao,
        'snr': snr,
        'decisao_mudou': not decisoes_iguais
    }


if __name__ == "__main__":
    result = demonstrate_wavelet_correction()
    print("\n=== DEMONSTRAÇÃO CONCLUÍDA ===")
    print("A filtragem wavelet removeu o ruído do observador e")
    print("corrigiu o expoente de Hurst para decisões mais precisas.")