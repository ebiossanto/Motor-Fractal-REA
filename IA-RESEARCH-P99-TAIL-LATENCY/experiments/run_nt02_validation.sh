#!/bin/bash
# IA-RESEARCH-P99-TAIL-LATENCY — Experimento NT-02 Validação
# Comando exato para reprodução (Linux/macOS/WSL)
# Windows PowerShell: python src/python/tail_model.py

set -euo pipefail

echo "=========================================="
echo "NT-02 Validação Empírica — M/G/1 Pareto"
echo "=========================================="
echo "Seed: 42 (fixo no código)"
echo "Python: $(python --version)"
echo "NumPy:  $(python -c 'import numpy; print(numpy.__version__)')"
echo "SciPy:  $(python -c 'import scipy; print(scipy.__version__)')"
echo ""

cd "$(dirname "$0")/.."  # raiz do projeto

# Executa simulação
python src/python/tail_model.py

echo ""
echo "=========================================="
echo "Verificação de hash do output"
echo "=========================================="
if command -v sha256sum >/dev/null; then
    sha256sum experiments/nt02_validation_results.json | cut -c1-16
elif command -v shasum >/dev/null; then
    shasum -a 256 experiments/nt02_validation_results.json | cut -c1-16
else
    python -c "import hashlib, json; d=json.load(open('experiments/nt02_validation_results.json')); print(hashlib.sha256(json.dumps(d, separators=(',',':'), ensure_ascii=False).encode()).hexdigest()[:16])"
fi

echo ""
echo "✅ Experimento NT-02 concluído. Resultados em experiments/nt02_validation_results.json"