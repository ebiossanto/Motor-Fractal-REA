import os
import time
import math
import csv
from datetime import datetime, timezone
import psutil

def calculate_shannon_entropy(data_sequence):
    """Calcula a Entropia de Shannon clássica para sequências de dados discretos."""
    if not data_sequence:
        return 0.0
    
    total_elements = len(data_sequence)
    frequencies = {}
    for item in data_sequence:
        frequencies[item] = frequencies.get(item, 0) + 1
        
    entropy = 0.0
    for count in frequencies.values():
        p = count / total_elements
        entropy -= p * math.log2(p)
    return entropy

def collect_system_metrics(duration_seconds=10, interval=0.1):
    """Coleta uso de CPU em intervalos curtos para formar a série temporal."""
    samples = []
    for _ in range(int(duration_seconds / interval)):
        # Coleta a porcentagem de uso de CPU por núcleo ou global
        samples.append(psutil.cpu_percent(interval=None))
        time.sleep(interval)
    return samples

def main():
    print("[INFO] Iniciando coleta de séries temporais do terminal...")
    
    # Parâmetros de amostragem
    duration = 30  # segundos
    interval = 0.1 # amostragem a 10Hz
    
    cpu_data = collect_system_metrics(duration_seconds=duration, interval=interval)
    
    # Como o uso de CPU é contínuo, discretizamos em "bins" (faixas) para Shannon
    discretized_cpu = [round(val / 5) * 5 for val in cpu_data] 
    
    shannon_ent = calculate_shannon_entropy(discretized_cpu)
    
    # Estruturação do Log (Linhagem e Origem)
    log_entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "data_source": "psutil.cpu_percent (Global OS Kernel Space)",
        "metric_type": "shannon_entropy_cpu",
        "sample_size": len(cpu_data),
        "entropy_value": round(shannon_ent, 4),
        "confidence_score": 0.95 if len(cpu_data) > 50 else 0.70
    }
    
    # Salvando em arquivo CSV no laboratório
    csv_file = "sistema_complexo_entropia.csv"
    file_exists = os.path.isfile(csv_file)
    
    with open(csv_file, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=log_entry.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(log_entry)
        
    print(f"[SUCESSO] Cálculo concluído. Entropia registrada: {shannon_ent:.4f} bits. Salvo em {csv_file}")

if __name__ == "__main__":
    main()