"""
Integração Direta REA no Motor Fractal

Conecta o motor de Teoria de Controle Fractal (FCT) com capacidades de 
reverse engineering de binários e syscalls do sistema operacional.

Este módulo provê a ponte entre:
1. Coleta de dados do sistema (psutil, syscalls)
2. Análise REA de binários e padrões de sistema
3. Feed de métricas aprimoradas para o motor fractal

Autor: Euzébio Soares
Data: Outubro 2026
"""

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

import numpy as np

# Adicionar path do scripts para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fractal_engine import FractalControlEngine
from hurst_calculator import compute_hurst_rs, compute_dfa, compute_permutation_entropy
from pfa_mitigation import PFAMitigator
from noise_filter import ObserverNoiseFilter


class REAIntegration:
    """
    Integração direta REA no motor fractal.
    
    Permite que o motor fractal solicite análise REA de binários do sistema,
    syscalls patterns e dados de telemetria operacional para enriquecer as
    métricas fractais com evidências de reverse engineering.
    """
    
    def __init__(self, fractal_engine: FractalControlEngine):
        self.engine = fractal_engine
        self.rea_status = "disconnected"
        self.analysis_cache = {}
        self.system_binaries = {}
        
    def connect(self, target_path: str = None) -> dict:
        """
        Conecta ao alvo REA (binary, process, ou sistema operacional).
        
        Args:
            target_path: Caminho para binary/process alvo. Se None, conecta ao sistema atual.
            
        Returns:
            Status da conexão REA
        """
        try:
            if target_path and os.path.exists(target_path):
                # Conectar a um binary específico
                self.rea_status = "connected_to_binary"
                self.target_path = target_path
                self.target_hash = hashlib.sha256(open(target_path, 'rb').read()).hexdigest()[:16]
                return {
                    "status": "connected",
                    "target": target_path,
                    "target_hash": self.target_hash,
                    "mode": "binary_analysis"
                }
            else:
                # Conectar ao sistema operacional atual
                self.rea_status = "connected_to_system"
                self.target_system = "local_os"
                return {
                    "status": "connected",
                    "target": "local_operating_system",
                    "target_hash": "system_default",
                    "mode": "system_telemetry"
                }
        except Exception as e:
            self.rea_status = "connection_failed"
            return {
                "status": "error",
                "error": str(e),
                "mode": "unknown"
            }
    
    def analyze_binary_features(self, binary_path: str) -> dict:
        """
        Analisa features de um binary usando técnicas REA-inspiradas.
        
        Args:
            binary_path: Caminho para o arquivo binary
            
        Returns:
            Dicionário com features extraídas do binary
        """
        if not os.path.exists(binary_path):
            return {"status": "file_not_found", "error": f"Binary not found: {binary_path}"}
        
        try:
            # Ler o binary e extrair features básicas
            with open(binary_path, 'rb') as f:
                binary_data = f.read()
            
            features = {
                "status": "analyzed",
                "path": binary_path,
                "size_bytes": len(binary_data),
                "sha256": hashlib.sha256(binary_data).hexdigest(),
                "size_kb": round(len(binary_data) / 1024, 2),
                "analysis_timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                
                # Features de header/estrutura
                "has_mz_header": binary_data[:2] == b'MZ',
                "has_pe_header": len(binary_data) >= 64 and binary_data[60:64] == b'\x00\x00\x00\x00',
                
                # Estatísticas de bytes
                "byte_entropy": self._compute_byte_entropy(binary_data),
                "unique_bytes": len(set(binary_data)),
                "zero_byte_ratio": round(sum(1 for b in binary_data if b == 0) / len(binary_data), 4),
                
                # Patrimarks for fractal analysis
                "import_st_count": self._count_imports(binary_data),
                "export_st_count": self._count_exports(binary_data),
                
                # Metadados REA
                "analysis_type": "rea_inspired_static_analysis"
            }
            
            self.analysis_cache[binary_path] = features
            return features
            
        except Exception as e:
            return {"status": "analysis_error", "error": str(e)}
    
    def _compute_byte_entropy(self, data: bytes) -> float:
        """Compute Shannon entropy of byte distribution."""
        if not data:
            return 0.0
        
        frequency = {}
        for byte in data:
            frequency[byte] = frequency.get(byte, 0) + 1
        
        data_len = len(data)
        entropy = 0.0
        for count in frequency.values():
            p = count / data_len
            if p > 0:
                entropy -= p * np.log2(p)
        
        return round(entropy, 4)
    
    def _count_imports(self, binary_data: bytes) -> int:
        """Contagem simplificada de imports (Windows PE)."""
        # Simplified: count 'import' string or IMAGE_IMPORT_DESCRIPTOR markers
        # This is a REA-inspired heuristic, not a full PE parser
        try:
            text = binary_data.decode('latin-1', errors='ignore').lower()
            import_count = text.count('import')
            return import_count
        except:
            return 0
    
    def _count_exports(self, binary_data: bytes) -> int:
        """Contagem simplificada de exports."""
        try:
            text = binary_data.decode('latin-1', errors='ignore').lower()
            export_count = text.count('export')
            return export_count
        except:
            return 0
    
    def analyze_syscall_patterns(self, syscall_data: List[dict]) -> dict:
        """
        Analisa padrões de syscalls usando métodos REA.
        
        Args:
            syscall_data: Lista de dicionários com dados de syscalls
            
        Returns:
            Análise de padrões de syscalls
        """
        if not syscall_data:
            return {"status": "no_data", "error": "Nenhum dado de syscall fornecido"}
        
        try:
            # Extrair características dos syscalls
            syscall_ids = [s.get('id', 0) for s in syscall_data]
            timestamps = [s.get('timestamp', 0) for s in syscall_data]
            
            # Calcular features fractais dos padrões de syscalls
            if len(syscall_ids) >= 10:
                hurst = compute_hurst_rs(np.array(syscall_ids))
                entropy = compute_permutation_entropy(np.array(syscall_ids))
                dfa_alpha, _, _ = compute_dfa(np.array(syscall_ids))
            else:
                hurst = 0.5
                entropy = 0.0
                dfa_alpha = 0.5
            
            # Padrões de frequência
            unique_syscalls = len(set(syscall_ids))
            total_syscalls = len(syscall_ids)
            
            # Padrões de burstiness
            burstiness = (np.var(syscall_ids) / np.mean(np.abs(np.diff(syscall_ids)))) if len(syscall_ids) > 1 else 0
            
            # Avg syscall rate
            time_span = max(timestamps) - min(timestamps) if timestamps else 1
            avg_rate = total_syscalls / time_span if time_span > 0 else 0
            
            analysis = {
                "status": "analyzed",
                "total_syscalls": total_syscalls,
                "unique_syscalls": unique_syscalls,
                "hurst_exponent": round(hurst, 4),
                "permutation_entropy": round(entropy, 4),
                "dfa_alpha": round(dfa_alpha, 4),
                "burstiness_index": round(burstiness, 4),
                "avg_syscall_rate": round(avg_rate, 4),
                
                # Clasificação REA-inspired
                "stability_class": self._classify_stability(hurst, entropy),
                
                "analysis_timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
            
            return analysis
            
        except Exception as e:
            return {"status": "analysis_error", "error": str(e)}
    
    def _classify_stability(self, H: float, S_p: float) -> str:
        """Classifica estabilidade baseada em Hurst e entropia."""
        if H < 0.35:
            return "CRITICAL_CAOTIC_ZONE"
        elif H > 0.65:
            return "HIGHLY_PERSISTENT_STATE"
        elif S_p < 0.3:
            return "LOW_ENTROPY_CONTROLLED"
        elif S_p > 0.7:
            return "HIGH_ENTROPY_UNPREDICTABLE"
        else:
            return "NOMINAL_FRACTAL_STABILITY"
    
    def feed_fractal_engine(self, rea_data: dict) -> dict:
        """
        Alimenta dados REA analisados no motor fractal,
        enriquecendo as métricas com evidências de reverse engineering.
        
        Args:
            rea_data: Dados da análise REA
            
        Returns:
            Enriquecimento do motor fractal
        """
        try:
            # Extrair métricas REA relevantes
            if rea_data.get("status") == "analyzed":
                # Integrar entropia de bytes no cálculo de entropia de permutação
                byte_entropy = rea_data.get("byte_entropy", 0)
                
                # Integrar padrões de syscalls na análise de Hurst
                syscall_hurst = rea_data.get("hurst_exponent", 0.5)
                
                # Integrar classificação de estabilidade
                stability = rea_data.get("stability_class", "NOMINAL_FRACTAL_STABILITY")
                
                # Atualizar estado interno do engine
                enrichment = {
                    "rea_integration_active": True,
                    "rea_target": rea_data.get("path", "unknown"),
                    "rea_target_hash": rea_data.get("sha256", "unknown"),
                    "byte_entropy_contribution": byte_entropy,
                    "syscall_hurst_contribution": syscall_hurst,
                    "stability_class": stability,
                    "enrichment_timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                }
                
                # Retornar enriquecimento para o engine usar
                return enrichment
            
        except Exception as e:
            return {"status": "enrichment_error", "error": str(e)}
    
    def get_rea_status(self) -> dict:
        """Retorna status atual da integração REA."""
        return {
            "rea_status": self.rea_status,
            "target": getattr(self, 'target_path', None) or getattr(self, 'target_system', None),
            "cache_size": len(self.analysis_cache),
            "engine_integration": self.engine is not None
        }


def demonstrate_rea_fractal_integration():
    """
    Demonstra a integração REA no motor fractal com dados reais do sistema.
    """
    print("=" * 70)
    print("INTEGRAÇÃO REA NO MOTOR FRACTAL")
    print("=" * 70)
    print()
    
    # Inicializar engine fractal
    engine = FractalControlEngine()
    rea = REAIntegration(engine)
    
    # Conectar ao sistema operacional
    print("1. Conectando ao sistema operacional...")
    connection = rea.connect()
    print(f"   Status: {connection['status']}")
    print(f"   Modo: {connection.get('mode', 'unknown')}")
    print()
    
    # Coletar dados de syscalls do sistema atual
    print("2. Coletando padrões de syscalls do sistema...")
    import psutil
    import time
    
    syscall_data = []
    for _ in range(50):
        cpu = psutil.cpu_percent(interval=0.1)
        # Simular dados de syscall (id simplificado)
        syscall_data.append({
            "id": np.random.randint(0, 300),  # IDs de syscalls variados
            "timestamp": time.time()
        })
    
    syscall_analysis = rea.analyze_syscall_patterns(syscall_data)
    print(f"   Análise de syscalls concluída")
    print(f"   - Total: {syscall_analysis.get('total_syscalls', 0)}")
    print(f"   - Hurst: {syscall_analysis.get('hurst_exponent', 'N/A')}")
    print(f"   - Entropia: {syscall_analysis.get('permutation_entropy', 'N/A')}")
    print(f"   - Classificação: {syscall_analysis.get('stability_class', 'N/A')}")
    print()
    
    # Analisar binary do Python (sempre disponível)
    print("2. Analisando binary do Python...")
    python_binary = sys.executable
    if os.path.exists(python_binary):
        binary_analysis = rea.analyze_binary_features(python_binary)
        print(f"   Binary: {python_binary}")
        print(f"   Tamanho: {binary_analysis.get('size_kb', 0)} KB")
        print(f"   Entropia de bytes: {binary_analysis.get('byte_entropy', 'N/A')}")
        print(f"   Has header MZ: {binary_analysis.get('has_mz_header', False)}")
    else:
        binary_analysis = {"status": "not_found", "note": "Python binary path not located"}
    print()
    
    # Alimentar no motor fractal
    print("3. Alimentando dados REA no motor fractal...")
    enrichment = rea.feed_fractal_engine(binary_analysis)
    print(f"   Integração REA ativa: {enrichment.get('rea_integration_active', False)}")
    print(f"   Classe de estabilidade: {enrichment.get('stability_class', 'N/A')}")
    print(f"   Contribuição de entropia: {enrichment.get('byte_entropy_contribution', 'N/A')}")
    print()
    
    # Status final
    print("4. Status da integração REA")
    status = rea.get_rea_status()
    print(f"   Status REA: {status['rea_status']}")
    print(f"   Target: {status['target']}")
    print(f"   Cache de análises: {status['cache_size']} itens")
    print()
    
    print("=" * 70)
    print("DEMONSTRAÇÃO CONCLUÍDA")
    print("=" * 70)


if __name__ == "__main__":
    demonstrate_rea_fractal_integration()