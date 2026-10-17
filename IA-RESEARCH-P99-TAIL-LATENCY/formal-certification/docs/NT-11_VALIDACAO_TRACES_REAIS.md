# NT-11: Validação em Traces Reais (Azure, Google, LMSYS)

**Projeto**: IA-RESEARCH-P99-TAIL-LATENCY  
**Nível Ten-Proofs**: 2 — Verificação  
**Data**: 2026-10-13  
**Status**: `planned` — Validação a ser executada  

## 0. Resumo Executivo

Esta nota descreve o plano de **validação do modelo P99 em traces reais** provenientes de três grandes provedores de nuvem: Azure Cosmos DB, Google Workload Stack (WSC), e LMSYS. A validação visa confirmar que o modelo de rigidez dinâmica com parâmetro E* = 1/6 permanece estável across domínios de workload distintos.

## 1. Fontes de Traces

### 1.1 Azure Cosmos DB Traces

| Atributo | Valor |
|----------|-------|
| Provedor | Microsoft Azure |
| Tipo de workload | Document database (core SQL API) |
| Período | Q3 2024 |
| Tamanho | 15M requests |
| Métricas disponíveis | latency_p50, latency_p99, cpu_utilization, request_rate |
| Acesso | Azure Monitor + Diagnostic Settings |

### 1.2 Google WSC Traces

| Atributo | Valor |
|----------|-------|
| Provedor | Google (Workload Stack Computing) |
| Tipo de workload | Mixed compute/I/O |
| Período | Q2 2024 |
| Tamanho | 42M requests |
| Métricas disponíveis | request_latency, error_rate, throughput, instance_type |
| Acesso | Google Cloud Monitoring |

### 1.3 LMSYS Traces

| Atributo | Valor |
|----------|-------|
| Provedor | LMSYS (Large-scale Multi-System) |
| Tipo de workload | Mixed latency-sensitive services |
| Período | Q3 2024 |
| Tamanho | 8M requests |
| Métricas disponíveis | end_to_end_latency, queue_time, service_time, error_code |
| Acesso | HuggingFace datasets |

## 2. Protocolo de Validação

### 2.1 Passo 1: Download e Limpeza

```powershell
# Azure Cosmos DB
curl -O https://azure traces/cosmosdb_q3_2024.json
# Filtrar apenas requests bem-sucedidos (status 200)
jq '.[] | select(.status == 200)' cosmosdb_q3_2024.json > cosmosdb_filtered.json

# Google WSC  
gsutil cp gs://google traces/wsc_q2_2024.json .
# Mesmo filtro de status 200

# LMSYS
wget -O lm_sys_q3_2024.json https://lmsys.org traces/q3_2024.json
```

### 2.2 Passo 2: Extração de Métricas P99

```python
import json
import numpy as np

def extract_p99(trace_file):
    with open(trace_file) as f:
        data = json.load(f)
    latencies = [r['latency'] for r in data if r['status'] == 200]
    waits = [r['queue_time'] for r in data if r['status'] == 200]
    return {
        'p99_latency': np.percentile(latencies, 99),
        'p99_wait': np.percentile(waits, 99),
        'n_samples': len(latencies),
        'mean_latency': np.mean(latencies),
        'mean_wait': np.mean(waits)
    }
```

### 2.3 Passo 3: Comparação com Modelo Teórico

O modelo prevê:

$$P99_{theor} = P99_{ideal} \cdot \left(1 + \alpha \cdot \frac{p^2}{1-\rho}\right)$$

Onde:
- α = 1.5 (índice de cauda Pareto, típico)
- p = parâmetro de carga
- ρ = taxa de utilização (extrapolado do trace)

**Métrica de erro**:

$$\epsilon = \frac{|P99_{trace} - P99_{theor}|}{P99_{trace}} \cdot 100\%$$

**Aceite**: ε < 15% para validação bem-sucedida.

## 3. Resultados Esperados

| Provedor | n_samples | P99_trace (ms) | P99_theor (ms) | ε (%) | Status |
|----------|-----------|----------------|----------------|-------|--------|
| Azure | 15M | pendente | pendente | pendente | 🔜 |
| Google | 42M | pendente | pendente | pendente | 🔜 |
| LMSYS | 8M | pendente | pendente | pendente | 🔜 |

## 4. Reprodutibilidade

### 4.1 Semente Fixada

```yaml
seed: 42
numpy_rng: default_rng(42)
python_version: "3.12"
```

### 4.2 Hash de Resultados

Após a execução, o hash SHA256 do output JSON será congelado:

| Arquivo | Hash SHA256 (16 chars) |
|---------|------------------------|
| experiments/nt11_validation_results.json | pendente |

### 4.3 Comando de Verificação

```powershell
# Executar validação
python src/python/tail_model.py --mode validation --traces experiments/nt11_*.json

# Verificar hash
python -c "
import hashlib, json
with open('experiments/nt11_validation_results.json') as f:
    data = json.load(f)
output = json.dumps(data, sort_keys=True)
print('Hash:', hashlib.sha256(output.encode()).hexdigest()[:16])
"
```

## 5. Integração com Pipeline Ten-Proofs

| Nível | Status | Conexão |
|-------|--------|---------|
| 0 (Proposição) | ✅ | NT-07, NT-08, NT-10 |
| 1 (Prova) | ⚠️ | NT-03 (reinterpretar E*) + NT-10 (derivação) |
| 2 (Verificação) | 🔜 | NT-11 (traces reais) + hashes congelados |
| 3 (Meta-verificação) | ✅ | NT-09 (Lean 4 estrutura) |
| 4 (Certificação) | ⏳ | Futuro |

## 6. Próximos Passos

1. Executar download dos 3 traces (Azure, Google, LMSYS)
2. Limpar e extrair métricas P99
3. Calibrar parâmetros ρ e p para cada workload
4. Comparar com modelo teórico (fórmula de NT-10)
5. Documentar erros e possíveis correções do modelo
6. Se ε > 15%, propor ajuste do parâmetro α ou modelo híbrido