@echo off
REM rea_bridge.bat - Windows version of the REA Bridge for Event-Driven Automation

set PIPE_PATH=\\.\pipe\rea_telemetry_pipe

echo [LABORATORIO] Aguardando transicoes de estado critico do REA...
echo [INFO] No Windows, use named pipes via PowerShell ou crie o pipe manualmente
echo [INFO] Para testar, execute em outro terminal: echo CPU_CRITICAL,1423 ^> \\.\pipe\rea_telemetry_pipe

REM Loop persistente - Windows version using PowerShell for named pipe
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$pipe = New-Object System.IO.Pipes.NamedPipeServerStream('rea_telemetry_pipe', 'In', 1, 'Byte', 'None'); ^
   while ($true) { ^
     $pipe.WaitForConnection(); ^
     $reader = New-Object System.IO.StreamReader($pipe); ^
     $line = $reader.ReadLine(); ^
     $pipe.Disconnect(); ^
     if ($line) { ^
       $timestamp = Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ' -AsUTC; ^
       $parts = $line.Split(','); ^
       $state = $parts[0]; ^
       $pid = $parts[1]; ^
       Write-Host \"[EVENTO - $timestamp] Mudanca detectada pelo REA: $state no PID $pid\"; ^
       switch ($state) { ^
         'CPU_CRITICAL' { ^
           Write-Host '[OPENCODE] Invocando pipeline matematico para calculo de Entropia de Shannon (CPU)...'; ^
           & python scripts/entropy_calc.py --source=$pid ^
         } ^
         'SYSCALL_BURST' { ^
           Write-Host '[OPENCODE] Roteando fluxo analitico de alta performance para o motor Julia...'; ^
           & julia scripts/entropy_syscalls.jl ^
         } ^
         'MUTATION_DETECTED' { ^
           Write-Host '[OPENCODE] Roteando fluxo analitico de alta performance para o motor Julia...'; ^
           & julia scripts/entropy_syscalls.jl ^
         } ^
         default { ^
           Write-Host \"[INFO] Estado '$state' registrado, mas nenhuma regra de entropia critica associada.\" ^
         } ^
       } ^
     } ^
   }"