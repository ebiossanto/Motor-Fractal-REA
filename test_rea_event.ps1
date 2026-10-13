# test_rea_event.ps1 - Simula eventos do REA para testar a ponte

$PIPE_NAME = "rea_telemetry_pipe"
$PIPE_PATH = "\\.\pipe\$PIPE_NAME"

# Parâmetros com valores padrão (evitar $PID que é built-in)
$EventState = "CPU_CRITICAL"
$EventPID = "1423"

# Parse argumentos se fornecidos
$args | ForEach-Object {
    if ($_ -like "-State*") { $EventState = $_.Split("=")[1].Trim('"') }
    if ($_ -like "-PID*") { $EventPID = $_.Split("=")[1].Trim('"') }
}

$message = "$EventState,$EventPID"

Write-Host "[TESTE] Enviando evento simulado para o REA Bridge..." -ForegroundColor Cyan
Write-Host "[TESTE] Estado: $EventState | PID: $EventPID" -ForegroundColor Gray

try {
    $pipeClient = New-Object System.IO.Pipes.NamedPipeClientStream(".", $PIPE_NAME, 'Out', 'None')
    $pipeClient.Connect(5000)  # Timeout 5 segundos
    
    $writer = New-Object System.IO.StreamWriter($pipeClient)
    $writer.AutoFlush = $true
    $writer.WriteLine($message)
    
    Write-Host "[TESTE] Evento enviado com sucesso!" -ForegroundColor Green
}
catch {
    Write-Host "[ERRO] Não foi possível conectar ao pipe. O bridge está rodando?" -ForegroundColor Red
    Write-Host "[ERRO] $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    if ($writer) { $writer.Close() }
    if ($pipeClient) { $pipeClient.Close() }
}