# NT-01: Estado da Arte e Escolha do Framework Analítico

**Projeto**: IA-RESEARCH-P99-TAIL-LATENCY  
**Nível Ten-Proofs**: 0 — Proposição  
**Data**: 2026-10-12  
**Autor**: Euzébio Soares  
**Status**: `draft` (pendente formalização)

---

## 1. Problema

Sistemas distribuídos exibem latência de cauda (P99, P99.9) que **não é explicada** por modelos clássicos de fila (M/M/1, M/G/1) com tempos de serviço leves. A "ponte analítica" buscada deve conectar:

- **Micro-causas**: GC pauses, lock contention, cache misses, network jitter, thermal throttling
- **Meso-estrutura**: Filas com tempos de serviço heavy-tailed, prioridades, retry storms
- **Macro-comportamento**: Scaling laws de P99 vs carga (ρ), número de hops, grau de paralelismo

---

## 2. Trabalho Prévio Relevante: Teoria de Controle Fractal (FCT)

**Repositório**: https://github.com/ebiossanto/IA-Research-Fractal-Control-Theory  
**Autor**: Euzébio Soares (este workspace)

A FCT já estabelece uma **ponte analítica** entre obstruções algébricas e latência de cauda, através de 4 eixos:

| Eixo | Artigo | Resultado Principal | Status |
|------|--------|---------------------|--------|
| **1. Ponte Analítica** | `ponte_analitica/main.tex` | Z₂³ sem quociente de ordem 6 → E₆* = 1/6 → P99 = P99_ideal · (1 + ρ/(1-ρ)·p²) | **Retificado** (ver §2.1) |
| **2. Bullwhip Algébrico** | `bullwhip_effect/main.tex` | Amplificação multiplicativa em n hops: P99⁽ⁿ⁾ = P99⁽⁰⁾ · ∏(1 + ρₖ/(1-ρₖ)·pₖ²) | **Retificado** (ver §2.1) |
| **3. Expansão Não-Abeliana** | `nonabelian_expansion/main.tex` | S_n: E_m* = (n!-m)/(n!·(n-1)), γ(Ω) = 2(n!-m)/(n!·(n!-1)) | Fórmula corrigida |
| **4. Relaxamento Estocástico** | `stochastic_relaxation/main.tex` | PFA quebra piso determinístico: P99(PFA) = P99_ideal · (1 + √ρ/(1-ρ)·p²) | **Válido e chave** |

### 2.1 Retificação Crítica (Cost-of-Equivariance, Apêndice)

O artigo `IA-Research-Cost-of-Equivariance/paper.tex` (Apêndice "The withdrawn queueing claim") **retira a fórmula exata** do Eixo 1:

> **A fórmula está errada e é retirada.**
> 1. **Expoente de p não é 2**: Simulação mostra slope log-log global ~1.34, tendendo a 2 apenas para p grande. Para p pequeno (regime de interesse), efeito é de primeira ordem em p.
> 2. **Dependência de carga satura**: Fórmula prevê divergência ρ→1, mas simulação mostra achatamento. Baseline ideal já contém blow-up 1/(1-ρ).
> 3. **Composição multi-hop está errada**: Trabalho original elevava multiplicador por-hop à 5ª potência. Se cada hop escala por c, razão fim-a-fim é c, não c⁵.
> 4. **Identificação p = E é definição, não teorema**: Nenhuma regra de decisão mapeando estados do controller para classes servidas foi especificada.

**Consequência**: A **ponte conceitual** (obstrução algébrica → erro do controller → inflação de P99) permanece válida, mas a **fórmula exata** precisa ser rederivada com:
- Expoente empírico β ≈ 1.34 (não 2)
- Saturação da dependência em ρ
- Composição aditiva (não multiplicativa) entre hops
- Regra de decisão explícita conectando E → p

---

## 3. Literatura Complementar

### 3.1 Teoria de Filas — Cauda de Latência

| Referência | Contribuição | Gap para P99 |
|------------|--------------|--------------|
| Kingman (1961) | Bound para G/G/1 | Apenas média; cauda exponencial assumida |
| Abate & Whitt (1997) | Transforms para M/G/1 tail | Requer LST do tempo de serviço |
| Zwart & Boxma (2000) | Tail asymptotics M/G/1 subexponencial | P(W > x) ~ (ρ/(1-ρ)) · P(S > x) — **chave** |
| Nuyens & Zwart (2006) | Large deviations filas com prioridade | Prioridade não-preemptiva vs preemptiva |

### 3.2 Teoria de Valores Extremos (EVT)

| Referência | Contribuição |
|------------|--------------|
| Pickands (1975) / Balkema & de Haan (1974) | GPD para excessos sobre limiar |
| Embrechts et al. (1997) | *Modelling Extremal Events* — subexponencial, Fréchet |
| Rootzén & Tajvidi (2006) | EVT para processos estacionários — declustering |

### 3.3 Sistemas Distribuídos — Evidência Empírica

| Referência | Sistema | Achado P99 |
|------------|---------|------------|
| Dean & Barroso (2013) | Google WSC | "Tail at scale" — P99 dominado por outliers raros |
| Ananthanarayanan et al. (2013) | Bing/Google | Stragglers → speculative execution |
| Curino et al. (2019) | Azure Cosmos DB | P99 = f(ρ, partition count, replica lag) |
| Ousterhout et al. (2020) | FaRM / RDMA | Network tail ≠ compute tail |

---

## 4. Framework Atualizado: "Fila + EVT + Obstrução Algébrica + Relaxamento Estocástico"

### 4.1 Hipótese Central (Revisada)

> **Teorema Alvo (Proposição Nível 0 — Revisado)**  
> Para uma rede de filas com tempos de serviço no domínio de atração de Fréchet (índice α ∈ (1,2)), controlada por autômatos finitos com obstrução algébrica (ex.: Z₂³ sem quociente de ordem 6), e com relaxamento estocástico via PFA:
> ```
> P99 ≈ P99_ideal(ρ, α) × [1 + η(ρ, α, hops, σ_interf, p_E)]
> ```
> onde:
> - `p_E = f(E_dinâmico)` é a taxa de erro do controller (E_dinâmico = 1/6 para Z₂³ determinístico)
> - `η` captura amplificação por hops, interferência e relaxamento estocástico
> - Expoente empírico β ≈ 1.34 (não 2) para p pequeno
> - Dependência em ρ **satura** (não diverge)
> - Composição multi-hop é **aditiva em log-escala** (não multiplicativa)

### 4.2 Componentes do Modelo

| Componente | Formalismo | Parâmetros-chave | Status |
|------------|------------|------------------|--------|
| **Obstrução algébrica** | Teoria de grupos finitos (Z₂³, S_n) | `E_dinâmico = 1/6` (Z₂³, 6 estados) | **Estabelecido (FCT Eixo 1)** |
| **Erro do controller** | Autômato finito (determinístico/PFA) | `p = g(E_dinâmico, p_relax)` | **Parcial (FCT Eixo 4)** |
| **Fila base** | M/G/1 ou G/G/1 com prioridade | `ρ`, `α` (tail index), `c_s²` | Clássico |
| **Cauda do serviço** | Generalized Pareto (GPD) / Pareto tipo II | `ξ = 1/α`, `σ`, `u` (threshold) | EVT |
| **Interferência sistema** | Ruído multiplicativo `exp(σ Z - σ²/2)` | `σ_interf` (GC, lock, network) | Empírico |
| **Relaxamento estocástico** | PFA com prob. transição `p_relax` | `p_relax ∈ [0,1]` | **FCT Eixo 4 (chave)** |
| **Composição multi-hop** | Aditiva em log-escala / Max-plus | `h` hops, correlação `ρ_hop` | **Retificado (não multiplicativa)** |

### 4.3 Perguntas de Pesquisa (Derivadas)

1. **Q1**: Qual o `α` efetivo observado em produção (GC pauses, lock contention)?
2. **Q2**: A interferência é aditiva ou multiplicativa na cauda? Como saturar ρ?
3. **Q3**: Como `P99` escala com `h` hops (aditiva em log? sublinear? superlinear?)?
4. **Q4**: Existe "phase transition" em `ρ_crit` onde P99 explode?
5. **Q5**: Qual `p_relax` ótimo para PFA dado `ρ`, `h`, `α`?
6. **Q6**: Como derivar regra de decisão explícita `p = f(E, estado_fila)`?

---

## 5. Plano de Formalização (Próximas NTs)

| NT | Título | Entregável | Nível Alvo |
|----|--------|------------|------------|
| NT-02 | Modelo Canônico Corrigido: M/G/1-Pareto + Obstrução Algébrica | Teorema: `P(W > x) ~ C(ρ,α) x^{-α}` com `p = f(E)` | 1 (Prova) |
| NT-03 | Ponte Analítica Corrigida: Saturação ρ + Expoente β + Composição Aditiva | Teorema: fórmula `P99 = f(ρ, α, h, σ, p_relax)` | 1 (Prova) |
| NT-04 | Relaxamento Estocástico Ótimo: PFA para Quebra de Rigidez | Teorema: `p_relax* = argmin P99(ρ, h, α)` | 1 (Prova) |
| NT-05 | Validação Empírica | Simulador + traces reais (Azure, Google, open) | 2 (Verificação) |
| NT-06 | Sensibilidade & Robustez | Bounds para estimação de `α`, `β`, `σ` com dados finitos | 2 (Verificação) |

---

## 6. Critérios de Aceitação (Nível 1 — Prova)

- [ ] Teorema principal enunciado com hipóteses explícitas (corrigindo FCT Eixo 1)
- [ ] Prova completa (ou esboço rigoroso) no `formal-certification/docs/NT-02_*.md`
- [ ] Código de verificação numérica em `src/python/verify_nt02.py`
- [ ] Certificado Nível 1 emitido: `formal-certification/certificates/nt02_certificate.json`

---

## 7. Referências Completas (BibTeX)

```bibtex
@article{kingman1961single,
  title={The single server queue in heavy traffic},
  author={Kingman, JFC},
  journal={Mathematical Proceedings of the Cambridge Philosophical Society},
  volume={57}, number={4}, pages={902--904}, year={1961}
}

@article{zwart2000tail,
  title={Tail asymptotics for the waiting time in a queue with heavy-tailed service times},
  author={Zwart, Bert and Boxma, Onno},
  journal={Queueing Systems}, volume={35}, pages={141--165}, year={2000}
}

@book{embrechts1997modelling,
  title={Modelling extremal events: for insurance and finance},
  author={Embrechts, Paul and Kl{\"u}ppelberg, Claudia and Mikosch, Thomas},
  year={1997}, publisher={Springer}
}

@article{dean2013tail,
  title={The tail at scale},
  author={Dean, Jeffrey and Barroso, Luiz Andr{\'e}},
  journal={Communications of the ACM}, volume={56}, number={2}, pages={74--80}, year={2013}
}

@article{harchol2016queueing,
  title={Queueing theory for computer systems},
  author={Harchol-Balter, Mor},
  year={2016}, publisher={Cambridge University Press}
}

@misc{soares2026fct1,
  title={An Analytic Bridge Between Group-Theoretic Obstruction and Queueing Tail Latency},
  author={Soares, Euz{\'e}bio},
  year={2026},
  howpublished={\url{https://github.com/ebiossanto/IA-Research-Fractal-Control-Theory/tree/main/ponte_analitica}},
  note={Retificado em Cost-of-Equivariance Apêndice}
}

@misc{soares2026fct2,
  title={Algebraic Origin of the Bullwhip Effect in Supply Networks},
  author={Soares, Euz{\'e}bio},
  year={2026},
  howpublished={\url{https://github.com/ebiossanto/IA-Research-Fractal-Control-Theory/tree/main/bullwhip_effect}}
}

@misc{soares2026fct3,
  title={Generalized Queueing Performance Under Non-Abelian Symmetric Group Expansions},
  author={Soares, Euz{\'e}bio},
  year={2026},
  howpublished={\url{https://github.com/ebiossanto/IA-Research-Fractal-Control-Theory/tree/main/nonabelian_expansion}}
}

@misc{soares2026fct4,
  title={Stochastic Relaxation via Probabilistic Finite Automata},
  author={Soares, Euz{\'e}bio},
  year={2026},
  howpublished={\url{https://github.com/ebiossanto/IA-Research-Fractal-Control-Theory/tree/main/stochastic_relaxation}}
}
```

---

## 8. Próxima Ação Imediata

> **Escrever NT-02** com o modelo canônico corrigido:  
> 1. M/G/1-Pareto + assintótico Zwart & Boxma (validado em `tail_model.py`)  
> 2. Obstrução algébrica Z₂³ → `E_dinâmico = 1/6` (FCT Eixo 1, válido)  
> 3. Regra de decisão: `p = E_dinâmico · h(estado_fila)` (a definir)  
> 4. Expoente empírico β ≈ 1.34 (não 2) — calibrar via simulação  
> 5. Saturação ρ: propor forma funcional `η(ρ) = ρ/(1-ρ) · s(ρ)` com `s(ρ) → 0` quando ρ→1  
> 6. Implementar `src/python/nt02_bridge.py` com validação (seed=42)

---

*Documento parte da cadeia de certificação Ten-Proofs. Não alterar essência conceitual; apenas adicionar subárvore `formal-certification/`.*