# NT-08: Modelo P99 com Termo Linear Explícito — Análise e Conclusão

**Projeto**: IA-RESEARCH-P99-TAIL-LATENCY  
**Nível Ten-Proofs**: 1 — Prova (análise empírica de modelos)  
**Data**: 2026-10-13  
**Autor**: Euzébio Soares  
**Status**: `completed` — Análise concluída  
**Hash SHA256**: `d56e1cee78f38c64`

---

## 0. Resumo Executivo

Testamos se adicionar um **termo linear explícito** em `p_controller` melhora o modelo de inflação P99, motivado pela expansão M/M/1:

```
P99_obs / P99_ideal = (1-ρ)/(1-ρ-p) = 1 + p/(1-ρ) + p²/(1-ρ)² + ...
```

**Resultado**: O termo linear **não melhora** o modelo. O Modelo A original (β=1.34 com Φ(ρ)) permanece o melhor (erro médio 96.6%, LOOCV 96.6%).

**Causa raiz**: A variação principal de η (inflação) é com **α** (cauda Pareto), não com ρ ou `p_controller`. O modelo atual não tem α como variável, e os modelos polinomiais em `x = p_controller` apenas fazem overfit.

---

## 1. Contexto e Motivação

### 1.1 Correção NT-07
O repositório de refutação mostrou que o modelo M/M/1 com μ_eff = μ(1-p) implica termo **linear** em p:
```
η = p/(1-ρ) + p²/(1-ρ)² + ...
```
A fórmula quadrática pura (β=2) não decorre do modelo. O β=1.34 do NT-02 é um ajuste empírico entre linear (1) e quadrático (2).

### 1.2 Correção de Baseline (Crítica)
O NT-02 usava `baseline_map` hardcoded {0.5: 1450, 0.7: 3000, 0.9: 48000} que **não corresponde** ao P99_ideal real da simulação:
| ρ | P99_ideal NT-02 | P99_ideal Real (sim) | Inflação NT-02 | Inflação Real |
|---|-----------------|----------------------|----------------|---------------|
| 0.5 | 1450 | ~417 | 14% | 296% |
| 0.7 | 3000 | ~1291 | 15% | 168% |
| 0.9 | 48000 | ~1685 | 16% | 3200% |

O NT-08 usa **P99_ideal real** da simulação (p_controller=0).

---

## 2. Modelos Testados

| Modelo | Fórmula | Parâmetros Livres |
|--------|---------|-------------------|
| **A (antigo)** | η = Φ(ρ) · x^β | 0 (β=1.34 fixo) |
| **B (linear)** | η = a₁ · x | a₁ |
| **C (linear+Φ)** | η = Φ(ρ) · a₁ · x | a₁ |
| **D (lin+quad)** | η = Φ(ρ) · [a₁·x + a₂·x^β] | a₁, a₂ |
| **E (M/M/1 exato)** | η = x / (1-ρ-x) | 0 |
| **F (polinomial)** | η = a₁·x + a₂·x² | a₁, a₂ |
| **G (cúbico+Φ)** | η = Φ(ρ) · [a₁·x + a₂·x² + a₃·x³] | a₁, a₂, a₃ |

Onde:
- `x = p_controller` (taxa de erro do controlador FCT)
- `Φ(ρ) = (ρ/(1-ρ)) · tanh(δ·(1-ρ))` com δ=2.0

---

## 3. Dataset (seed=42, n=100k)

20 pontos: ρ ∈ {0.5, 0.6, 0.7, 0.8, 0.9} × α ∈ {1.2, 1.5, 1.8, 2.0}

| ρ | α | x | Φ | P99_ideal | P99_sim | η_real |
|---|---|---|---|-----------|---------|--------|
| 0.5 | 1.2 | 0.205 | 0.762 | 1369 | 3401 | 1.48 |
| 0.5 | 1.5 | 0.205 | 0.762 | 456 | 1350 | 1.96 |
| 0.5 | 1.8 | 0.205 | 0.762 | 162 | 566 | 2.49 |
| 0.5 | 2.0 | 0.222 | 0.762 | 100 | 338 | 2.37 |
| 0.7 | 1.2 | 0.216 | 1.253 | 1733 | 4741 | 1.74 |
| 0.7 | 1.5 | 0.216 | 1.253 | 614 | 3114 | 4.07 |
| 0.7 | 1.8 | 0.222 | 1.253 | 256 | 2743 | 9.71 |
| 0.7 | 2.0 | 0.243 | 1.253 | 148 | 5501 | 36.1 |
| 0.9 | 1.2 | 0.217 | 1.776 | 2118 | 16758 | 6.91 |
| 0.9 | 1.5 | 0.217 | 1.776 | 886 | 31090 | 34.1 |
| 0.9 | 1.8 | 0.232 | 1.776 | 406 | 36010 | 87.6 |
| 0.9 | 2.0 | 0.254 | 1.776 | 269 | 40648 | 149.9 |

**Observação-chave**: `x = p_controller` varia muito pouco (0.20–0.25), enquanto η varia de 1.5 a 150. A variação principal é com **α**, não com x ou ρ.

---

## 4. Resultados

### 4.1 Erro Médio (%)

| Modelo | Erro Médio | LOOCV |
|--------|-----------|-------|
| **A (antigo β=1.34)** | **96.6%** | **96.6%** |
| B (linear a₁·x) | 686.4% | 719.9% |
| C (Φ·a₁·x) | 628.6% | 652.0% |
| D (Φ·[a₁·x+a₂·x^β]) | 244.4% | 259.5% |
| E (M/M/1 exato) | 3,470,436% | — |
| F (a₁·x+a₂·x²) | 349.5% | 382.6% |
| G (Φ·[a₁·x+a₂·x²+a₃·x³]) | 205.8% | 228.2% |

### 4.2 Coeficientes Ajustados (Overfit Evidente)

| Modelo | Coeficientes |
|--------|--------------|
| D | a₁ = -4942, a₂ = 8392 |
| F | a₁ = -2276, a₂ = 10808 |
| G | a₁ = 1331, a₂ = -17733, a₃ = 54457 |

Coeficientes **negativos e gigantes** → overfit severo. As bases polinomiais em x são quase colineares (x varia pouco).

### 4.3 Correlações

| Correlação | Valor |
|------------|-------|
| Corr(η, x) | +0.821 |
| Corr(η, x^β) | +0.824 |
| Corr(η, Φ·x) | +0.731 |
| Corr(η, Φ·x^β) | +0.763 |
| Corr(η/Φ, x) | +0.838 |
| Corr(η/Φ, x^β) | +0.841 |

η/Φ correlaciona bem com x e x^β, mas a dispersão residual é grande devido à dependência em **α**.

---

## 5. Análise: Por Que o Termo Linear Não Ajuda?

### 5.1 Estrutura dos Dados
```
η(ρ, α) = f(α) · g(ρ) + ruído
```
- `x = p_controller(ρ, α)` ≈ constante (~0.22) pois Φ e Λ compensam
- A variação em η vem **predominantemente de α**
- O modelo A captura g(ρ) via Φ(ρ), mas f(α) é implícito em x^β

### 5.2 Modelo A Funciona Porque
```
η_pred = Φ(ρ) · x^β
```
- Φ(ρ) captura a dependência em ρ (cresce com ρ)
- x^β captura implicitamente a dependência em α (via H_rs no cálculo de x)
- É um modelo **esparso** (1 parâmetro efetivo: β)

### 5.3 Modelos Polinomiais Falham Porque
- Tentam ajustar variação em α usando potências de x
- x varia pouco → bases quase colineares → matriz mal condicionada
- Coeficientes explodem para compensar → overfit

---

## 6. Conclusão e Próximos Passos

### 6.1 Conclusão
**O termo linear explícito NÃO melhora o modelo.** O Modelo A (β=1.34 com Φ) permanece o melhor entre os testados.

A "correção teórica" do termo linear (M/M/1) não se traduz em melhoria empírica porque:
1. A simulação usa M/G/1-Pareto, não M/M/1
2. A dependência principal é com α (cauda), não com p
3. Φ(ρ) já captura a saturação em ρ

### 6.2 Modelo Recomendado (Manter NT-02)
```
η(ρ, α) = Φ(ρ) · [E* · Λ(ρ) · H_factor]^β

Φ(ρ) = (ρ/(1-ρ)) · tanh(δ(1-ρ))
Λ(ρ) = 1 + κ · tanh(γ·ρ/(1-ρ))
H_factor = (0.5/H_rs)^ξ  (H_rs ≈ (3-α)/2 · (1-0.3ρ))
```
Parâmetros: δ=2.0, κ=0.3, γ=1.0, ξ=0.5, β=1.34, E*=1/6

### 6.3 Próximos Passos Reais (NT-09+)
| Prioridade | Ação |
|------------|------|
| **Alta** | **NT-09**: Formalização Lean 4 do Teorema de Rigidez Dinâmica (Nível 3) |
| **Alta** | Adicionar **α como variável explícita** no modelo de η |
| **Média** | **NT-10**: Derivação teórica de E* = 1/6 como parâmetro de acoplamento |
| **Média** | Validar em traces reais (Azure, Google, LMSYS) |
| **Baixa** | Testar modelos com H_rs explícito: η = f(Φ, x, H_rs) |

---

## 7. Reprodutibilidade

### 7.1 Comando Exato
```powershell
cd IA-RESEARCH-P99-TAIL-LATENCY
python src/python/nt08_linear_term.py
# Hash: c08c97a6d95eb1e1
```

### 7.2 Arquivos Gerados
- `experiments/nt08_linear_term.json` — resultados completos
- `src/python/nt08_linear_term.py` — script de análise

### 7.3 Dados Congelados
```json
{
  "seed": 42,
  "n_samples": 100000,
  "rhos": [0.5, 0.6, 0.7, 0.8, 0.9],
  "alphas": [1.2, 1.5, 1.8, 2.0]
}
```

---

## 8. Honestidade Epistêmica (Ten-Proofs)

| Nível | Status | Nota |
|-------|--------|------|
| 0 (Proposição) | ✅ | Hipótese: termo linear ajuda |
| 1 (Prova) | ✅ | Testado empiricamente — **hipótese REFUTADA** |
| 2 (Verificação) | ✅ | Código reproduzível, hash congelado |
| 3 (Meta-verificação) | ⏳ | Pendente: Lean 4 para Rigidez Dinâmica (NT-09) |
| 4 (Certificação) | ⏳ | Futuro |

**Importante**: Resultado negativo (termo linear não ajuda) é **válido e informativo**. Evita perseguir direção improdutiva.

---

*Última atualização: 2026-10-13 | NT-08 concluído | Próximo: NT-09 (Lean 4)*