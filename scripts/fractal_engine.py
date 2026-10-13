"""
Motor de Teoria de Controle Fractal (FCT) para Previsão de Colapso por Latência de Cauda.

Integra os quatro eixos da FCT:
1. Ponte Analítica: cálculo de Hurst e DFA
2. Bullwhip Algébrico: amplificação em cascata
3. Não-Abeliano: extensões para grupos simétricos
4. Relaxamento Estocástico: mitigação via PFA

Referências:
- Repositório: https://github.com/ebiossanto/IA-Research-Fractal-Control-Theory
- DOC-FCT-001: Protocolo de Testes para Modelagem de Controle Fractal
"""

import numpy as np
import time
import sys
from datetime import datetime, timezone
from typing import Optional

# Corrigir encoding no Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Módulo opcional de Rigidez Dinâmica (novo framework 2026)
try:
    from rigidez_dinamica import RigidezDinamica, verificar_teoremas_novas
    RIGIDEZ_DINAMICA_DISPONIVEL = True
except ImportError:
    RIGIDEZ_DINAMICA_DISPONIVEL = False


from hurst_calculator import FractalAnalyzer, compute_hurst_rs, compute_dfa, compute_hurst_dfa
from pfa_mitigation import PFAMitigator
from noise_filter import ObserverNoiseFilter


class FractalControlEngine:
    """
    Motor principal de Teoria de Controle Fractal.

    Avalia a assinatura fractal atual do sistema e prevê colapso
    por latência de cauda antes que a entropia informacional atinja
    o teto de saturação termodinâmica.

    Atributos adicionais (2026):
    - Integração com teoria de rigidez dinâmica (módulo rigidez_dinamica)
    - Novos teoremas de limiares e conflitos estático/dinâmico
    """

    def __init__(self, controller_states: int = 6, system_states: int = 8):
        """
        Inicializa o motor FCT.

        Args:
            controller_states: Número de estados do controlador (|Q|)
            system_states: Número de estados do sistema (|S|)
        """
        self.analyzer = FractalAnalyzer()
        self.mitigator = PFAMitigator(system_states, controller_states)
        self.noise_filter = ObserverNoiseFilter()
        self.history = []

    def run_fractal_canary_test(self, cpu_stream: list) -> dict:
        """
        Avalia a assinatura fractal atual do sistema.

        Se H -> 0, o sistema está perdendo resiliência (antipersistente).
        Se H -> 0.5, o sistema está em equilíbrio (ruído branco).
        Se H -> 1, o sistema está altamente persistente.

        Args:
            cpu_stream: Série temporal de uso de CPU

        Returns:
            Dicionário com status de estabilidade e predição
        """
        if len(cpu_stream) < 30:
            return {
                "timestamp_utc": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "status": "INSUFFICIENT_DATA",
                "hurst": None,
                "sample_count": len(cpu_stream),
                "message": "Mínimo de 30 amostras necessário para análise fractal"
            }

        series = np.array(cpu_stream)

        # 1. Filtrar ruído do observador
        H_raw = compute_hurst_rs(series)
        filter_results = self.noise_filter.filter_and_correct(series, H_raw)
        H = filter_results['hurst_corrected']

        # 2. Calcular métricas adicionais
        H_dfa = compute_hurst_dfa(series)
        D_H = self.analyzer.compute_fractal_dimension_higuchi(series) if hasattr(self.analyzer, 'compute_fractal_dimension_higuchi') else None

        # 3. Classificar estabilidade
        if H < 0.35:
            status = "CRITICAL_CAOTIC_ZONE"
            prediction = "Vulnerabilidade iminente a colapso por latência de cauda"
            action = "ATIVAR PFA DE MITIGAÇÃO IMEDIATAMENTE"
        elif H <= 0.65:
            status = "NOMINAL_FRACTAL_STABILITY"
            prediction = "Sistema em equilíbrio metaestável saudável"
            action = "Monitorar continuamente"
        else:
            status = "HIGHLY_PERSISTENT_STATE"
            prediction = "Tendências lineares previsíveis dominando o sistema"
            action = "Verificar gargalos de longo prazo"

        # 4. Calcular recomendação de carga (com novo framework opcional)
        rho_c = self.mitigator.find_phase_transition()

        # Novo: Verificar rigidez dinâmica se módulo disponível
        if RIGIDEZ_DINAMICA_DISPONIVEL:
            # Verificar teoremas novos para o par (system_states, controller_states)
            n = self.mitigator.n  # |S|
            m = self.mitigator.m  # |Q|
            teoremas = verificar_teoremas_novas(n, m)
            recommendation = self.mitigator.recommend_controller(rho=0.5)
            # Adicionar informações de rigidez ao resultado
            result = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "hurst_exponent": round(H, 4),
                "hurst_raw": round(H_raw, 4),
                "hurst_dfa": round(H_dfa, 4),
                "fractal_dimension": round(D_H, 4) if D_H else None,
                "stability_status": status,
                "predictive_analysis": prediction,
                "recommended_action": action,
                "observer_noise": {
                    "snr_db": round(filter_results['snr_db'], 2),
                    "correction_applied": round(filter_results['correction_applied'], 4)
                },
                "mitigation_recommendation": recommendation,
                "sample_count": len(cpu_stream),
                "teorema_rigidez": teoremas["teorema_rigidez"],
                "conflito_estatico_dinamico": teoremas["conflito_estatico_dinamico"]["descricao_curta"],
                "erro_dinamico": teoremas["erro_dinamico_minimo"],
                "melhoria_teorica": teoremas["melhoria"]
            }
        else:
            # comportamento original quando módulo não disponível
            # Incluir chave placeholder para compatibilidade com testes
            recommendation = self.mitigator.recommend_controller(rho=0.5)
            result = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "hurst_exponent": round(H, 4),
                "hurst_raw": round(H_raw, 4),
                "hurst_dfa": round(H_dfa, 4),
                "fractal_dimension": round(D_H, 4) if D_H else None,
                "stability_status": status,
                "predictive_analysis": prediction,
                "recommended_action": action,
                "observer_noise": {
                    "snr_db": round(filter_results['snr_db'], 2),
                    "correction_applied": round(filter_results['correction_applied'], 4)
                },
                "mitigation_recommendation": recommendation,
                "sample_count": len(cpu_stream),
                "teorema_rigidez": {"satisfaz": False, "mensagem": "Módulo rigidez_dinamica nao disponivel"},
                "conflito_estatico_dinamico": "Módulo rigidez_dinamica nao disponivel",
                "erro_dinamico": 0.0,
                "melhoria_teorica": "Módulo rigidez_dinamica nao disponivel - use python scripts/rigidez_dinamica.py para ativar"
            }

        self.history.append(result)
        return result

    def predict_collapse_window(self, cpu_stream: list, threshold_h: float = 0.35) -> dict:
        """
        Prevê a janela de colapso baseada no cruzamento do limiar de Hurst.

        Args:
            cpu_stream: Série temporal de CPU
            threshold_h: Limiar de Hurst para zona crítica (padrão: 0.35)

        Returns:
            Dicionário com previsão de janela de colapso
        """
        if len(cpu_stream) < 30:
            return {"status": "INSUFFICIENT_DATA"}

        series = np.array(cpu_stream)
        H = compute_hurst_rs(series)

        # Calcular tendência de Hurst (janela deslizante)
        window_size = min(30, len(series) // 3)
        if window_size >= 10:
            hurst_series = []
            for i in range(0, len(series) - window_size + 1, window_size // 2):
                window = series[i:i + window_size]
                H_window = compute_hurst_rs(window)
                hurst_series.append(H_window)

            # Tendência linear
            if len(hurst_series) >= 3:
                x = np.arange(len(hurst_series))
                slope, intercept = np.polyfit(x, hurst_series, 1)

                # Estimar quando H cruzará o limiar
                if slope < 0:  # Hurst decrescente
                    steps_to_threshold = (threshold_h - intercept) / slope
                    delta_t = steps_to_threshold * (window_size // 2) * 0.1  # Assumindo 10Hz

                    return {
                        "status": "COLLAPSE_PREDICTED",
                        "current_hurst": round(H, 4),
                        "hurst_trend_slope": round(slope, 4),
                        "threshold_h": threshold_h,
                        "predicted_delta_t_seconds": round(delta_t, 2),
                        "confidence": "medium" if abs(slope) > 0.01 else "low"
                    }

        return {
            "status": "STABLE",
            "current_hurst": round(H, 4),
            "threshold_h": threshold_h,
            "message": "Hurst acima do limiar crítico"
        }

    def compute_bullwhip_amplification(self, hop_loads: list, hop_errors: list,
                                        controller_type: str = 'DFA') -> dict:
        """
        Calcula a amplificação em cascata (Efeito Bullwhip Algébrico).

        Args:
            hop_loads: Lista de cargas para cada salto
            hop_errors: Lista de taxas de erro para cada salto
            controller_type: 'DFA' ou 'PFA'

        Returns:
            Dicionário com análise de amplificação
        """
        inflation = self.mitigator.compute_bullwhip_cascade(
            hop_loads, hop_errors, controller_type
        )

        # Calcular equivalente DFA para comparação
        if controller_type == 'PFA':
            dfa_inflation = self.mitigator.compute_bullwhip_cascade(
                hop_loads, hop_errors, 'DFA'
            )
            improvement = dfa_inflation / inflation
        else:
            dfa_inflation = inflation
            improvement = 1.0

        return {
            "controller_type": controller_type,
            "hop_count": len(hop_loads),
            "total_inflation_factor": round(inflation, 4),
            "dfa_equivalent_inflation": round(dfa_inflation, 4),
            "improvement_ratio": round(improvement, 2),
            "risk_level": "CRITICAL" if inflation > 10 else "HIGH" if inflation > 5 else "MODERATE" if inflation > 2 else "LOW"
        }

    def generate_fct_report(self) -> dict:
        """
        Gera relatório consolidado de todas as análises realizadas.

        Returns:
            Dicionário com relatório completo
        """
        if not self.history:
            return {"status": "NO_DATA", "message": "Nenhuma análise realizada"}

        latest = self.history[-1]
        critical_count = sum(1 for h in self.history if h.get('stability_status') == 'CRITICAL_CAOTIC_ZONE')

        return {
            "report_timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "total_analyses": len(self.history),
            "critical_alerts": critical_count,
            "latest_status": latest,
            "system_health": "CRITICAL" if critical_count > len(self.history) * 0.3 else "STABLE",
            "recommendation": "Ativar mitigação PFA" if critical_count > 0 else "Manter monitoramento"
        }


def run_fractal_canary_test(cpu_stream: list) -> dict:
    """
    Função standalone para compatibilidade com o DOC-FCT-001.

    Avalia a assinatura fractal atual do sistema.
    Se H -> 0, o sistema está perdendo resiliência (antipersistente).
    """
    engine = FractalControlEngine()
    return engine.run_fractal_canary_test(cpu_stream)


# Teste com dados locais
if __name__ == "__main__":
    import csv

    print("=" * 70)
    print("MOTOR DE TEORIA DE CONTROLE FRACTAL (FCT)")
    print("=" * 70)

    # Carregar dados locais
    cpu_data = []
    try:
        with open("../cpu_timeseries.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cpu_data.append(float(row['cpu_percent']))
        print(f"\n[INFO] Carregadas {len(cpu_data)} amostras de cpu_timeseries.csv")
    except FileNotFoundError:
        print("[AVISO] cpu_timeseries.csv não encontrado. Usando dados sintéticos.")
        np.random.seed(42)
        cpu_data = list(np.random.exponential(30, 300))

    # Executar análise
    engine = FractalControlEngine()
    result = engine.run_fractal_canary_test(cpu_data)

    print("\n" + "=" * 70)
    print("RESULTADO DA ANÁLISE FRACTAL")
    print("=" * 70)
    for key, value in result.items():
        if isinstance(value, dict):
            print(f"\n{key}:")
            for k, v in value.items():
                print(f"  {k}: {v}")
        else:
            print(f"{key}: {value}")

    # Teste de previsão de colapso
    print("\n" + "=" * 70)
    print("PREVISÃO DE COLAPSO")
    print("=" * 70)
    prediction = engine.predict_collapse_window(cpu_data)
    for key, value in prediction.items():
        print(f"{key}: {value}")

    # Teste de mitigação PFA
    print("\n" + "=" * 70)
    print("ANÁLISE DE MITIGAÇÃO PFA")
    print("=" * 70)
    for rho in [0.3, 0.5, 0.7, 0.9, 0.95]:
        rec = engine.mitigator.recommend_controller(rho)
        print(f"\nρ = {rho}:")
        print(f"  Controlador recomendado: {rec['recommended_controller']}")
        print(f"  Inflação DFA: {rec.get('expected_inflation', rec.get('expected_inflation_dfa', 'N/A'))}")
        if 'expected_inflation_pfa' in rec:
            print(f"  Inflação PFA: {rec['expected_inflation_pfa']}")
            print(f"  Fator de mitigação: {rec['mitigation_factor']}")

    # Teste de Bullwhip
    print("\n" + "=" * 70)
    print("EFEITO BULLWHIP ALGÉBRICO (5 saltos)")
    print("=" * 70)
    hop_loads = [0.8, 0.85, 0.9, 0.85, 0.8]
    hop_errors = [1/6] * 5
    bullwhip = engine.compute_bullwhip_amplification(hop_loads, hop_errors, 'DFA')
    for key, value in bullwhip.items():
        print(f"{key}: {value}")

    print("\n" + "=" * 70)
    print("ANÁLISE CONCLUÍDA")
    print("=" * 70)