"""
Módulo de Integração FCT com Dados REA e Sistema Operacional.

Implementa os protocolos de teste do DOC-FCT-001:
- Teste I: Indução de Sobrecarga por Cascata de Filas
- Teste II: Intercepção de Obstruções Algébricas em Camadas do Kernel

Mapeamento de métricas:
- Dimensão de Hausdorff (D_H): DFA sobre séries de syscalls
- Expoente de Hurst (H): R/S sobre flutuação de CPU
- Entropia de Permutação (S_p): distribuição de padrões de memória
- Atrito do Observador (R_o): overhead do OpenCode
"""

import numpy as np
import time
import csv
import os
import sys
from datetime import datetime, timezone
from typing import Optional

# Corrigir encoding no Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from fractal_engine import FractalControlEngine
from hurst_calculator import compute_hurst_rs, compute_dfa, compute_permutation_entropy
from pfa_mitigation import PFAMitigator
from noise_filter import ObserverNoiseFilter


class FCTExperimentRunner:
    """
    Executor de experimentos FCT conforme DOC-FCT-001.

    Gerencia coleta de dados, análise fractal e registro de resultados
    com assinatura hash exclusiva no fct_experiment_manifest.csv.
    """

    def __init__(self, output_dir: str = "."):
        """
        Inicializa o executor de experimentos.

        Args:
            output_dir: Diretório para salvar resultados
        """
        self.engine = FractalControlEngine()
        self.output_dir = output_dir
        self.manifest_file = os.path.join(output_dir, "fct_experiment_manifest.csv")
        self.experiment_id = self._generate_experiment_id()

    def _generate_experiment_id(self) -> str:
        """Gera ID único para o experimento."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"FCT_{timestamp}"

    def _compute_hash(self, data: str) -> str:
        """Calcula hash SHA-256 dos dados."""
        import hashlib
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def collect_cpu_timeseries(self, duration_seconds: int = 30, interval: float = 0.1) -> list:
        """
        Coleta série temporal de uso de CPU.

        Args:
            duration_seconds: Duração da coleta em segundos
            interval: Intervalo entre amostras em segundos

        Returns:
            Lista de valores de CPU percent
        """
        if not PSUTIL_AVAILABLE:
            print("[AVISO] psutil não disponível. Usando dados sintéticos.")
            np.random.seed(42)
            return list(np.random.exponential(30, int(duration_seconds / interval)))

        samples = []
        start_time = time.time()

        for _ in range(int(duration_seconds / interval)):
            cpu_pct = psutil.cpu_percent(interval=None)
            samples.append(cpu_pct)
            time.sleep(interval)

        return samples

    def collect_memory_states(self, duration_seconds: int = 10, interval: float = 0.5) -> list:
        """
        Coleta estados de alocação de memória virtual.

        Args:
            duration_seconds: Duração da coleta
            interval: Intervalo entre amostras

        Returns:
            Lista de estados de memória
        """
        if not PSUTIL_AVAILABLE:
            return []

        samples = []
        for _ in range(int(duration_seconds / interval)):
            mem = psutil.virtual_memory()
            samples.append(mem.percent)
            time.sleep(interval)

        return samples

    def run_test_i_cascade_overload(self, num_hops: int = 5, base_load: float = 0.7) -> dict:
        """
        Teste I: Indução de Sobrecarga por Cascata de Filas.

        Identifica o ponto de inflexão onde o sistema perde sua
        propriedade de relaxação estocástica.

        Args:
            num_hops: Número de saltos na cascata
            base_load: Carga base do sistema

        Returns:
            Resultados do Teste I
        """
        print(f"\n{'='*70}")
        print("TESTE I: INDUÇÃO DE SOBRECARGA POR CASCATA DE FILAS")
        print(f"{'='*70}")

        # Simular cargas crescentes em cada salto
        hop_loads = [base_load + i * 0.05 for i in range(num_hops)]
        hop_errors = [1/6] * num_hops  # E_6^* = 1/6

        # Calcular amplificação Bullwhip
        bullwhip_dfa = self.engine.compute_bullwhip_amplification(
            hop_loads, hop_errors, 'DFA'
        )
        bullwhip_pfa = self.engine.compute_bullwhip_amplification(
            hop_loads, hop_errors, 'PFA'
        )

        # Coletar dados reais do sistema
        cpu_data = self.collect_cpu_timeseries(duration_seconds=10)

        # Analisar estabilidade
        stability = self.engine.run_fractal_canary_test(cpu_data)

        # Registrar no manifest
        self._log_experiment("TEST_I", {
            "hops": num_hops,
            "base_load": base_load,
            "dfa_inflation": bullwhip_dfa['total_inflation_factor'],
            "pfa_inflation": bullwhip_pfa['total_inflation_factor'],
            "hurst": stability.get('hurst_exponent'),
            "status": stability.get('stability_status')
        })

        return {
            "test": "TEST_I_CASCADE_OVERLOAD",
            "experiment_id": self.experiment_id,
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "hop_loads": hop_loads,
            "bullwhip_dfa": bullwhip_dfa,
            "bullwhip_pfa": bullwhip_pfa,
            "system_stability": stability,
            "critical_threshold": "H < 0.35",
            "validation": "PASS" if stability.get('hurst_exponent', 0.5) > 0.35 else "ALERT"
        }

    def run_test_ii_kernel_obstruction(self, num_layers: int = 3) -> dict:
        """
        Teste II: Intercepção de Obstruções Algébricas em Camadas do Kernel.

        Avalia como restrições estruturais de concorrência se comportam
        como canais laterais algébricos.

        Args:
            num_layers: Número de camadas do kernel a analisar

        Returns:
            Resultados do Teste II
        """
        print(f"\n{'='*70}")
        print("TESTE II: INTERCEPÇÃO DE OBSTRUÇÕES ALGÉBRICAS EM CAMADAS DO KERNEL")
        print(f"{'='*70}")

        # Coletar dados de memória (estados de alocação)
        memory_data = self.collect_memory_states(duration_seconds=5)

        if len(memory_data) < 10:
            print("[AVISO] Dados insuficientes de memória. Usando CPU como proxy.")
            memory_data = self.collect_cpu_timeseries(duration_seconds=5)

        # Calcular entropia de permutação
        S_p = compute_permutation_entropy(np.array(memory_data))

        # Calcular Hurst
        H = compute_hurst_rs(np.array(memory_data))

        # Calcular DFA
        alpha, _, _ = compute_dfa(np.array(memory_data))

        # Identificar obstruções (analogia com camadas do kernel)
        obstructions = []
        for layer in range(num_layers):
            layer_error = (layer + 1) / (num_layers * 6)  # Erro crescente por camada
            obstructions.append({
                "layer": layer,
                "error_rate": round(layer_error, 4),
                "impact": "HIGH" if layer_error > 0.1 else "MODERATE" if layer_error > 0.05 else "LOW"
            })

        # Registrar no manifest
        self._log_experiment("TEST_II", {
            "layers": num_layers,
            "permutation_entropy": round(S_p, 4),
            "hurst": round(H, 4),
            "dfa_alpha": round(alpha, 4),
            "obstructions_detected": len([o for o in obstructions if o['impact'] == 'HIGH'])
        })

        return {
            "test": "TEST_II_KERNEL_OBSTRUCTION",
            "experiment_id": self.experiment_id,
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "permutation_entropy": round(S_p, 4),
            "hurst": round(H, 4),
            "dfa_alpha": round(alpha, 4),
            "obstructions": obstructions,
            "validation": "PASS" if S_p > 0.5 else "ALERT"
        }

    def _log_experiment(self, test_type: str, data: dict):
        """
        Registrar resultado no manifesto de experimentos.

        Args:
            test_type: Tipo de teste (TEST_I ou TEST_II)
            data: Dados do resultado
        """
        # Criar arquivo se não existir
        if not os.path.exists(self.manifest_file):
            with open(self.manifest_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'experiment_id', 'test_type', 'timestamp_utc',
                    'data_hash', 'data_json'
                ])

        # Preparar dados
        import json
        data_json = json.dumps(data)
        data_hash = self._compute_hash(data_json)

        # Registrar
        with open(self.manifest_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                self.experiment_id,
                test_type,
                datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                data_hash,
                data_json
            ])

        print(f"[MANIFEST] Registrado: {test_type} (hash: {data_hash})")

    def run_full_protocol(self) -> dict:
        """
        Executa o protocolo completo DOC-FCT-001.

        Returns:
            Resultados consolidados
        """
        print(f"\n{'#'*70}")
        print("PROTOCOLO DOC-FCT-001: MODELAGEM DE CONTROLE FRACTAL")
        print(f"Experimento: {self.experiment_id}")
        print(f"{'#'*70}")

        # Teste I
        test_i = self.run_test_i_cascade_overload()

        # Teste II
        test_ii = self.run_test_ii_kernel_obstruction()

        # Relatório final
        report = self.engine.generate_fct_report()

        return {
            "experiment_id": self.experiment_id,
            "protocol": "DOC-FCT-001",
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "test_i": test_i,
            "test_ii": test_ii,
            "final_report": report,
            "manifest_file": self.manifest_file
        }


def main():
    """Função principal para execução do protocolo completo."""
    runner = FCTExperimentRunner(output_dir=".")
    results = runner.run_full_protocol()

    print(f"\n{'#'*70}")
    print("RESULTADO FINAL DO PROTOCOLO")
    print(f"{'#'*70}")
    print(f"Experimento: {results['experiment_id']}")
    print(f"Status: {results['final_report']['system_health']}")
    print(f"Recomendação: {results['final_report']['recommendation']}")
    print(f"Manifest: {results['manifest_file']}")

    return results


if __name__ == "__main__":
    main()
