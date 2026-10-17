# IA-RESEARCH-P99-TAIL-LATENCY — Experimento NT-02 Validação (Windows PowerShell)
# Comando exato para reprodução no Windows

Write-Host "=========================================="
Write-Host "NT-02 Validação Empírica — M/G/1 Pareto"
Write-Host "=========================================="
Write-Host "Seed: 42 (fixo no código)"
Write-Host "Python: $(python --version)"
Write-Host "NumPy:  $(python -c 'import numpy; print(numpy.__version__)')"
Write-Host "SciPy:  $(python -c 'import scipy; print(scipy.__version__)')"
Write-Host ""

Set-Location (Split-Path $PSScriptRoot -Parent)  # raiz do projeto

# Executa simulação
python src/python/tail_model.py

Write-Host ""
Write-Host "=========================================="
Write-Host "Verificação de hash do output"
Write-Host "=========================================="
$json = Get-Content experiments/nt02_validation_results.json -Raw
$bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
$hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
$hashStr = -join ($hash | ForEach-Object { '{0:x2}' -f $_ })
Write-Host "SHA256 (prefixo 16): $($hashStr.Substring(0, 16))"

Write-Host ""
Write-Host "Experimento NT-02 concluído. Resultados em experiments/nt02_validation_results.json"