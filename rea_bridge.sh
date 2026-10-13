#!/bin/bash
# rea_bridge.sh - Ponte de Automação Event-Driven do Laboratório

PIPE_PATH="/tmp/rea_telemetry_pipe"

# Garante a criação do canal de comunicação isolado
if [[ ! -p $PIPE_PATH ]]; then
    mkfifo "$PIPE_PATH"
fi

echo "[LABORATÓRIO] Aguardando transições de estado crítico do REA..."

# Loop persistente que escuta os eventos do REA
while true; do
    if read -r line < "$PIPE_PATH"; then
        # Extrai o estado e a origem emitidos pelo REA
        TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        STATE=$(echo "$line" | cut -d',' -f1)
        SOURCE_PID=$(echo "$line" | cut -d',' -f2)

        echo "[EVENTO - $TIMESTAMP] Mudança detectada pelo REA: $STATE no PID $SOURCE_PID"

        case "$STATE" in
            "CPU_CRITICAL"|"OVERHEAD_HIGH")
                echo "[OPENCODE] Invocando pipeline matemático para cálculo de Entropia de Shannon (CPU)..."
                # OpenCode executa o isolamento e roda o script Python
                opencode run python3 scripts/entropy_calc.py --source="$SOURCE_PID"
                ;;
            "SYSCALL_BURST"|"MUTATION_DETECTED")
                echo "[OPENCODE] Roteando fluxo analítico de alta performance para o motor Julia..."
                # OpenCode aciona o interpretador Julia para processar a matriz de interrupções
                opencode run julia scripts/entropy_syscalls.jl
                ;;
            *)
                echo "[INFO] Estado '$STATE' registrado, mas nenhuma regra de entropia crítica associada."
                ;;
        esac
    fi
done