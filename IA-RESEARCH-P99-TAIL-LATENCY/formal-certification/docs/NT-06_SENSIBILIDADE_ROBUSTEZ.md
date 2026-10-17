# NT-06: Sensibilidade & Robustez (Bootstrap, Dados Finitos)

**Projeto**: IA-RESEARCH-P99-TAIL-LATENCY  
**Nível Ten-Proofs**: 1 — Prova (em andamento)  
**Data**: 2026-10-13  
**Autor**: Euzébio Soares  
**Status**: `planning` — desenho do experimento

---

## 1. Objetivo

Quantificar a **incerteza estatística** dos parâmetros calibrados em NT-02/NT-05 quando:
- Tamanho da amostra é finito (n = 2k a 100k)
- Distribuição subjacente é heavy-tailed (Pareto α=1.5)
- Parâmetros são estimados via bootstrap/monte-carlo

---

## 2. Perguntas de Pesquisa

| Questão | Método | Métrica de Saída |
|---------|--------|------------------|
| Q1: Qual o IC 95% para β, κ, δ, ξ? | Bootstrap não-paramétrico | Intervalo de confiança |
| Q2: Como o erro P99 varia com n? | Curva learning (learning curve) | RMSE vs n |
| Q3: O modelo é robusto a outliers? | Análise de influência (Cook's distance) | Sensibilidade máxima |
| Q4: Generaliza para outros ρ, α? | Validação cruzada ρ×α | Erro out-of-sample |

---

## 3. Desenho Experimental

### 3.1 Bootstrap para Parâmetros (Q1)

```python
def bootstrap_parameters(n_bootstrap=500, sample_size=20_000):
    """Estima IC 95% para β, κ, δ, ξ via bootstrap."""
    params_boot = []
    
    for b in range(n_bootstrap):
        # Reamostrar com reposição da série de latência
        sample = np.random.choice(latencies, size=sample_size, replace=True)
        
        # Recalcular parâmetros via grid search
        best = optimize_parameters(sample)
        params_boot.append(best)
    
    # Percentis 2.5% e 97.5%
    ic_95 = {k: np.percentile([p[k] for p in params_boot], [2.5, 97.5]) 
             for k in ['beta', 'kappa', 'delta', 'xi']}
    return ic_95
```

### 3.2 Curva de Aprendizado (Q2)

```python
def learning_curve(n_values=[2000, 5000, 10000, 20000, 50000, 100000]):
    """Erro P99 vs tamanho da amostra."""
    errors = []
    for n in n_values:
        # Múltiplas rodadas para média
        errs = [run_single_experiment(n) for _ in range(10)]
        errors.append((n, np.mean(errs), np.std(errs)))
    return errors
```

### 3.3 Análise de Influência (Q3)

```python
def influence_analysis(latencies, n_samples=20_000):
    """Identifica pontos de alta influência (outliers)."""
    # Cook's distance para cada ponto
    cook_dist = []
    for i in range(len(latencies)):
        # Remover ponto i, recalcular P99
        p99_full = np.percentile(latencies, 99)
        p99_loo = np.percentile(np.delete(latencies, i), 99)
        influence = abs(p99_full - p99_loo) / p99_full
        cook_dist.append(influence)
    
    # Top-k mais influentes
    top_k = np.argsort(cook_dist)[-10:]
    return top_k, cook_dist
```

### 3.4 Validação Cruzada ρ×α (Q4)

```python
def cross_validation_rho_alpha():
    """Testa generalização em grade ρ×α."""
    rho_grid = [0.3, 0.5, 0.7, 0.8, 0.9]
    alpha_grid = [1.2, 1.5, 1.8]
    
    # Treinar em subset, testar em hold-out
    # k-fold = 3 (baixo n_samples)
    results = {}
    for rho in rho_grid:
        for alpha in alpha_grid:
            # Grid search local
            err = validate_params(rho, alpha)
            results[(rho, alpha)] = err
    return results
```

---

## 4. Parâmetros de Configuração

| Parâmetro | Valor | Justificativa |
|-----------|-------|---------------|
| n_bootstrap | 500 | Trade-off precisão/tempo |
| n_learning | [2k, 5k, 10k, 20k, 50k, 100k] | Cobertura logarítmica |
| n_influence | 20_000 | Representativo |
| n_cv_folds | 3 | Baixo n_samples |
| conf_level | 0.95 | Padrão científico |

---

## 5. Critérios de Sucesso

| Critério | Limite |
|----------|--------|
| IC 95% para β contém 1.34 | Sim |
| Largura IC β < 0.2 | Sim (precisão) |
| Curva learning converge | RMSE → 0 com n |
| Influência max < 10% | Robustez a outliers |
| Generalização ρ×α < 25% erro | Aceitável out-of-sample |

---

## 6. Próximos Passos

1. **Implementar `nt06_bootstrap.py`** com os 4 métodos
2. **Executar grid** (estimado: 30-60 min)
3. **Analisar resultados** e atualizar NT-02 com ICs
4. **Emitir certificado Nível 2** para robustez

---

*Documento em planejamento. Próximo: implementação e execução.*