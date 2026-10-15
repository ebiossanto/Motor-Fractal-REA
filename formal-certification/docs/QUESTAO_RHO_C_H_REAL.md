# Q* — ρ_c = 0.25 vs 0.706 + H real no tail (resolvida em P, 14/10/2026)

**Questão:** `FCT_REFINAMENTO_PREDITIVO.md` §2.4 afirma ρ_c = 0.25, mas
`gk_D1/gk_F1` usam ρ_c = (1−r)⁴ ≈ 0.706. Qual vale? E qual o H real,
dado H=4.83 impossível no variance atual?

**Ferramenta:** `formal-certification/experiments/fct_phase_transition_audit.py`
**Certificado:** `formal-certification/certificates/certificate_fct_audit.json`
(hash `4e79d5b2…`, verificação 9/9; aviso honesto δ<γ registrado pelo certifier)
**Testes:** `formal-certification/tests/test_fct_audit.py` (5/5 PASS)

## Resposta

Dois modelos PFA distintos estavam em jogo; 0.25 não é break-even em nenhum:

| Modelo | E_pfa | break-even (DFA=PFA) | meia-mitigaç��o (M=0.5) |
|---|---|---|---|
| A (doc §2.3) | 1/12 absoluto | **0.0625** (=1/16) | **0.25** |
| B (gk) | p(1−r) | **0.7063** (=(11/12)⁴) | 2.82 (fora de [0,1], inatingível) |

Numérico confirma analítico (<0.005). Correção: §2.4 deve distinguir
break-even × meia-mitigaç��o e fixar um modelo PFA.

## Dados novos (telemetria n=300)

- P90 real = **89.4** (F1 usava 39.0 — limiar errado, 5 eventos; correto: **10 eventos**).
- ρ_global = 0.272; ρ_eff médio dos eventos ≈ 0.95 (saturação 90–100%).
- Operacional: sob A, sistema opera acima do break-even (PFA justificado);
  sob B, abaixo de 0.706 (DFA suficiente). O modelo decide a recomendação.
- H consenso (mediana de estimadores válidos): raw **0.26** (anti),
  Donoho **0.46** (cruza 0.35 ✓ F4), **bloco tail 0.12** (novo: saturação
  sustentada é fortemente anti-persistente).
- Bug morto: `np.diff(x, n=s)` (ordem-n) → `Var(X[t+s]−X[t])` (lag-s);
  H=4.83 impossível eliminado. R/S (0.91) e DFA (1.27) divergem neste dado
  espiculado — só Higuchi+variance concordam; consenso usa mediana dos válidos.
- Box-dim 2D (t,x): 0.94 raw / 0.73 filtrado / 0.24 tail; sem saturação legacy.

## Status

(P) verificado máquina; (C) pendente só auditoria externa (nível 4).
