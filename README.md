# Terminal-Laboratório: Sistema de Leitura e Análise de Sistemas Complexos

Este repositório implementa um laboratório automatizado para coleta de telemetria de hardware/software, análise de entropia e engenharia reversa, seguindo o protocolo de **Origiem Definida (Linhagem do Dado)** e **Avaliação de Precisão**.

## 📁 Estrutura do Projeto

```
zero/
├── scripts/
│   ├── entropy_calc.py          # Cálculo de Entropia de Shannon (CPU) - Python
│   └── entropy_syscalls.jl      # Análise de Entropia de Syscalls - Julia
├── rea_bridge.ps1               # Ponte Event-Driven (PowerShell/Windows)
├── rea_bridge.bat               # Ponte Event-Driven (Batch/Windows)
├── test_rea_event.ps1           # Simulador de eventos REA para teste
├── requirements.txt             # Dependências Python
└── README.md                    # Este arquivo
```

## 🔧 Pré-requisitos

### Python
```powershell
pip install -r requirements.txt
```
- **psutil** >= 5.9.0

### Julia (opcional, para análise de syscalls de alta performance)
```powershell
# Instale Julia em https://julialang.org/
# Depois instale as dependências:
julia -e 'using Pkg; Pkg.add(["DelimitedFiles"])'
```

### OpenCode CLI
```powershell
# Verifique se o OpenCode está instalado
opencode --version
```

## 🚀 Como Executar o Sistema

### Passo 1: Instalar Dependências
```powershell
pip install -r requirements.txt
```

### Passo 2: Iniciar a Ponte REA (Terminal 1)
Abra um **PowerShell como Administrador** e execute:

```powershell
# Opção 1: PowerShell nativo (recomendado)
.\rea_bridge.ps1

# Opção 2: Batch (se preferir)
.\rea_bridge.bat
```

> **Nota:** O script cria um Named Pipe Windows em `\\.\pipe\rea_telemetry_pipe`. Mantenha este terminal aberto.

### Passo 3: Testar a Integração (Terminal 2)
Abra **outro PowerShell** e execute um evento simulado:

```powershell
# Teste CPU Critical
.\test_rea_event.ps1 -State "CPU_CRITICAL" -PID "1423"

# Teste Syscall Burst
.\test_rea_event.ps1 -State "SYSCALL_BURST" -PID "1423"

# Teste Mutation Detected
.\test_rea_event.ps1 -State "MUTATION_DETECTED" -PID "1423"
```

### Passo 4: Verificar Resultados
Os logs serão gerados no diretório raiz:
- `sistema_complexo_entropia.csv` — Métricas de entropia CPU (Python)
- `julia_complex_metrics.log` — Métricas de entropia syscalls (Julia)

## 📊 Entendendo as Métricas

### Entropia de Shannon (CPU)
| Valor | Interpretação |
|-------|---------------|
| → 0 | Sistema ocioso, loops determinísticos, estado estacionário |
| Moderado | Operação nominal (compilação, navegação, carga saudável) |
| Máximo | DoS, vazamento de memória, concorrência caótica, transição de fase |

### Metadados de Linhagem (Protocolo de Origem Definida)
Cada entrada no CSV/log contém:
```json
{
  "timestamp_utc": "2026-10-12T20:23:00Z",
  "data_source": "psutil.cpu_percent (Global OS Kernel Space)",
  "metric_type": "shannon_entropy_cpu",
  "sample_size": 100,
  "entropy_value": 2.3456,
  "confidence_score": 0.95
}
```

## 🔬 Avaliação de Precisão (Motor Analítico)

O sistema aplica automaticamente:
1. **Filtro de Kalman** — Suavização de leituras de sensores
2. **Propagação de Incerteza (Gauss)** — `σ_f = √Σ(∂f/∂x_i)²σ_x_i²`
3. **Análise de Resíduos** — Quantifica o "atrito" da própria ferramenta de monitoramento

## 📝 Estados Monitorados pelo REA Bridge

| Estado REA | Condição Teórica | Ação do OpenCode |
|------------|------------------|------------------|
| `CPU_CRITICAL` | CPU > 92% ou temperatura anômala | Executa `entropy_calc.py` (amostragem 10Hz) |
| `OVERHEAD_HIGH` | Overhead de coleta elevado | Executa `entropy_calc.py` |
| `SYSCALL_BURST` | Rajada de syscalls anômala | Executa `entropy_syscalls.jl` (Julia) |
| `MUTATION_DETECTED` | Injeção de código via REA | Executa `entropy_syscalls.jl` (Julia) |

## ⚙️ Configuração Avançada

### Ajustar Parâmetros de Amostragem (Python)
Edite `scripts/entropy_calc.py`:
```python
duration = 10   # segundos de coleta
interval = 0.1  # 10Hz (100ms)
```

### Adicionar Novos Estados REA
Edite `rea_bridge.ps1` na seção `switch ($STATE)`:
```powershell
"NOVO_ESTADO" { 
    Write-Host "[OPENCODE] Ação personalizada..." -ForegroundColor Magenta
    # Seu comando aqui
}
```

## 🛡️ Isolamento e Boas Práticas

1. **Sessões Isoladas** — Sempre que invocado por `CPU_CRITICAL`, a análise roda em sessão separada para evitar efeito "Bullwhip"
2. **Buffer Isolation** — Em `MUTATION_DETECTED`, force o isolamento do buffer dump antes de submeter vetores ao Julia
3. **Arquivos Persistentes** — Mantenha `sistema_complexo_entropia.csv` e `julia_complex_metrics.log` versionados

## 🐛 Solução de Problemas

### "Named Pipe não encontrado"
- Verifique se `rea_bridge.ps1` está rodando no Terminal 1
- Execute como Administrador se necessário

### "python/julia não reconhecido"
- Adicione Python e Julia ao PATH do Windows
- Reinicie o terminal após instalar

### "Permissão negada no pipe"
```powershell
# Execute PowerShell como Administrador
Start-Process powershell -Verb RunAs
```

## 📚 Referências

- **Protocolo Ten-Proofs** — Descoberta → Formalização → Verificação → Certificação → Reprodutibilidade
- **REA (Reverse Engineering Analysis)** — Framework de interceptação de syscalls
- **Shannon Entropy** — Medida de incerteza/desordem em sistemas complexos

---

**Autor:** Euzébio Soares  
**Data:** 2026-10-12  
**Versão:** 1.0.0