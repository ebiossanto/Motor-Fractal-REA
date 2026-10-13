import os
import time
import math
import csv
import json
from datetime import datetime, timezone
import psutil

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[AVISO] matplotlib não instalado. Gráficos não serão gerados. Instale com: pip install matplotlib")


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


def collect_cpu_timeseries(duration_seconds=30, interval=0.1):
    """Coleta série temporal de uso de CPU."""
    samples = []
    timestamps = []
    start_time = time.time()
    
    for i in range(int(duration_seconds / interval)):
        cpu_pct = psutil.cpu_percent(interval=None)
        samples.append(cpu_pct)
        timestamps.append(time.time() - start_time)
        time.sleep(interval)
    
    return timestamps, samples


def save_raw_data(timestamps, cpu_data, entropy_value, output_prefix="cpu_timeseries"):
    """Salva dados brutos em JSON e CSV."""
    # JSON com metadados completos
    data = {
        "metadata": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "data_source": "psutil.cpu_percent (Global OS Kernel Space)",
            "metric_type": "cpu_timeseries_raw",
            "duration_seconds": len(timestamps) * 0.1,
            "interval_seconds": 0.1,
            "sample_rate_hz": 10,
            "sample_count": len(cpu_data),
            "entropy_value": round(entropy_value, 4),
            "confidence_score": 0.95
        },
        "timeseries": [
            {"t": round(ts, 3), "cpu_percent": round(cpu, 2)}
            for ts, cpu in zip(timestamps, cpu_data)
        ]
    }
    
    json_file = f"{output_prefix}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[DADOS] Série temporal salva em {json_file}")
    
    # CSV simples para análise externa
    csv_file = f"{output_prefix}.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_seconds", "cpu_percent"])
        for ts, cpu in zip(timestamps, cpu_data):
            writer.writerow([round(ts, 3), round(cpu, 2)])
    print(f"[DADOS] CSV salvo em {csv_file}")
    
    return json_file, csv_file


def plot_timeseries(timestamps, cpu_data, entropy_value, output_file="cpu_timeseries_plot.png"):
    """Gera gráfico da série temporal de CPU."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
    
    # Gráfico 1: Série temporal de CPU
    ax1.plot(timestamps, cpu_data, 'b-', linewidth=0.8, alpha=0.8, label='CPU %')
    ax1.axhline(y=sum(cpu_data)/len(cpu_data), color='r', linestyle='--', linewidth=1, 
                label=f'Média: {sum(cpu_data)/len(cpu_data):.1f}%')
    ax1.fill_between(timestamps, cpu_data, alpha=0.1, color='blue')
    ax1.set_ylabel('Uso de CPU (%)', fontsize=11)
    ax1.set_title(f'Série Temporal de Uso de CPU — 30s @ 10Hz — Entropia de Shannon: {entropy_value:.4f} bits', 
                  fontsize=12, fontweight='bold')
    ax1.set_ylim(0, max(100, max(cpu_data) * 1.2))
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper right')
    
    # Gráfico 2: Histograma (distribuição)
    ax2.hist(cpu_data, bins=20, color='green', alpha=0.7, edgecolor='black', density=True)
    ax2.axvline(sum(cpu_data)/len(cpu_data), color='r', linestyle='--', linewidth=1.5, label='Média')
    ax2.set_xlabel('Uso de CPU (%)', fontsize=11)
    ax2.set_ylabel('Densidade', fontsize=11)
    ax2.set_title('Distribuição de Frequência do Uso de CPU', fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Estatísticas no gráfico
    stats_text = (f"Média: {sum(cpu_data)/len(cpu_data):.1f}%\n"
                  f"Mín: {min(cpu_data):.1f}% | Máx: {max(cpu_data):.1f}%\n"
                  f"Desvio: {math.sqrt(sum((x - sum(cpu_data)/len(cpu_data))**2 for x in cpu_data)/len(cpu_data)):.1f}%\n"
                  f"Entropia (Shannon): {entropy_value:.4f} bits\n"
                  f"Amostras: {len(cpu_data)} @ 10Hz")
    ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, fontsize=9,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
             fontfamily='monospace')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[GRÁFICO] Salvo em {output_file}")
    return output_file


def main():
    print("=" * 60)
    print("COLETA DE SÉRIE TEMPORAL DE CPU — 30 SEGUNDOS @ 10Hz")
    print("=" * 60)
    
    duration = 30  # segundos
    interval = 0.1  # 10Hz
    
    print(f"[INFO] Coletando {int(duration/interval)} amostras por {duration}s...")
    
    timestamps, cpu_data = collect_cpu_timeseries(duration_seconds=duration, interval=interval)
    
    # Discretização para entropia de Shannon
    discretized_cpu = [round(val / 5) * 5 for val in cpu_data]
    shannon_ent = calculate_shannon_entropy(discretized_cpu)
    
    print(f"[INFO] Entropia de Shannon (bins de 5%): {shannon_ent:.4f} bits")
    print(f"[INFO] CPU Média: {sum(cpu_data)/len(cpu_data):.1f}% | Min: {min(cpu_data):.1f}% | Max: {max(cpu_data):.1f}%")
    
    # Salvar dados brutos
    json_file, csv_file = save_raw_data(timestamps, cpu_data, shannon_ent)
    
    # Gerar gráfico
    plot_file = plot_timeseries(timestamps, cpu_data, shannon_ent)
    
    # Log no CSV principal (linhagem)
    log_entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "data_source": "psutil.cpu_percent (Global OS Kernel Space)",
        "metric_type": "shannon_entropy_cpu",
        "sample_size": len(cpu_data),
        "entropy_value": round(shannon_ent, 4),
        "confidence_score": 0.95
    }
    
    main_csv = "sistema_complexo_entropia.csv"
    file_exists = os.path.isfile(main_csv)
    with open(main_csv, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=log_entry.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(log_entry)
    
    print("=" * 60)
    print("COLETA CONCLUÍDA COM SUCESSO")
    print("=" * 60)
    print(f"Entropia de Shannon: {shannon_ent:.4f} bits")
    print(f"Amostras coletadas: {len(cpu_data)}")
    print(f"Arquivos gerados:")
    print(f"  - {json_file} (dados completos + metadados)")
    print(f"  - {csv_file} (série temporal simples)")
    if plot_file:
        print(f"  - {plot_file} (gráfico PNG)")
    print(f"  - {main_csv} (log de linhagem)")


if __name__ == "__main__":
    main()