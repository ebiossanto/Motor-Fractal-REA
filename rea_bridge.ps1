# rea_bridge.ps1 - Ponte de Automação Event-Driven do Laboratório (PowerShell)

$PIPE_NAME = "rea_telemetry_pipe"
$PIPE_PATH = "\\.\pipe\$PIPE_NAME"

Write-Host "[LABORATÓRIO] Aguardando transições de estado crítico do REA..." -ForegroundColor Cyan
Write-Host "[INFO] Named Pipe: $PIPE_PATH" -ForegroundColor Gray

# Loop persistente que escuta os eventos do REA via Named Pipe
while ($true) {
    try {
        # Cria o Named Pipe Server
        $pipe = New-Object System.IO.Pipes.NamedPipeServerStream($PIPE_NAME, 'In', 1, 'Byte', 'None')
        
        Write-Host "[PIPE] Aguardando conexão..." -ForegroundColor Yellow
        $pipe.WaitForConnection()
        
        $reader = New-Object System.IO.StreamReader($pipe)
        $line = $reader.ReadLine()
        $pipe.Disconnect()
        $pipe.Close()
        $reader.Close()
        
        if ($line -and $line.Trim()) {
            $TIMESTAMP = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
            $PARTS = $line.Split(',')
            $STATE = $PARTS[0].Trim()
            $SOURCE_PID = if ($PARTS.Count -gt 1) { $PARTS[1].Trim() } else { "unknown" }

            Write-Host "[EVENTO - $TIMESTAMP] Mudança detectada pelo REA: $STATE no PID $SOURCE_PID" -ForegroundColor Green

            switch ($STATE) {
                "CPU_CRITICAL" { 
                    Write-Host "[OPENCODE] Invocando pipeline matemático para cálculo de Entropia de Shannon (CPU)..." -ForegroundColor Magenta
                    & python scripts/entropy_calc.py --source=$SOURCE_PID
                }
                "OVERHEAD_HIGH" { 
                    Write-Host "[OPENCODE] Invocando pipeline matemático para cálculo de Entropia de Shannon (CPU)..." -ForegroundColor Magenta
                    & python scripts/entropy_calc.py --source=$SOURCE_PID
                }
                "SYSCALL_BURST" { 
                    Write-Host "[OPENCODE] Roteando fluxo analítico de alta performance para o motor Julia..." -ForegroundColor Magenta
                    & julia scripts/entropy_syscalls.jl
                }
                "MUTATION_DETECTED" { 
                    Write-Host "[OPENCODE] Roteando fluxo analítico de alta performance para o motor Julia..." -ForegroundColor Magenta
                    & julia scripts/entropy_syscalls.jl
                }
                default { 
                    Write-Host "[INFO] Estado '$STATE' registrado, mas nenhuma regra de entropia crítica associada." -ForegroundColor Gray
                }
            }
        }
    }
    catch {
        Write-Host "[ERRO] $($_.Exception.Message)" -ForegroundColor Red
        Start-Sleep -Seconds 1
    }
}