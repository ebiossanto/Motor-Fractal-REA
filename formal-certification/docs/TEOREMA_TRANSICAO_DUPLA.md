# Teorema da Transição Dupla (TD) + Lower Bounds LB1/LB2 — Doc. de desenvolvimento

**Data:** 15/10/2026 · **Status:** T1/LB1/LB2 **(P)** — provados aqui + checados
por máquina (`teorema_transicao_dupla_check.py`, sympy 1.14 + grade + seed 11;
`out_teorema_td.json`, TUDO_OK=True) · **Nível 4:** `pending` (sem auditor externo).
**Condicional a (A):** fórmulas-ponte dos Eixos 1/2 (`FCT_REFINAMENTO_PREDITIVO.md` §1).

> O que se pretende provar: (i) que break-even e meia-mitigaç��o PFA×DFA têm
> forma fechada **para qualquer razão de erro** `q = E_pfa/p`, com a identidade
> de razão `ρ_1/2 = 4·ρ*`; (ii) um **lower bound de mitigação** (LB1) que
> reabilita o 0.25 com o significado correto; (iii) um **lower bound de
> cascata** (LB2): amplificação bullwhip cresce **pelo menos linearmente** em n.
> Nada aqui é lower bound de complexidade — ver §7 (non-claims).

## 1. Análise do projeto (vários ângulos)

1. **Algébrico:** `M(ρ) = 1 − q²/√ρ` — toda a fenomenologia (dois modelos,
   três números 0.0625/0.25/0.706) colapsa num único parâmetro `q`. A forma
   `1 − C/√ρ` explica *por que* a confusão era inevitável sem parametrizar.
2. **Analítico:** `M′ > 0`, `M → −∞` em 0⁺ — unicidade de cada travessia é
   gratuita; o conteúdo real está nas **condições de existência em [0,1)**.
3. **Operacional:** `ρ_global = 0.272` cai exatamente na faixa onde os modelos
   discordam (A: >50% mitigação; B: DFA suficiente) — a ambiguidade morde na prática.
4. **Estatístico:** calibração ADV-003 mostrou estimadores com viés sistemático;
   este teorema não depende de estimação — é dedutivo a partir de (A).
5. **Complexidade:** ponte L2→L3 segue aberta; nenhum lower bound aqui transfere
   para `Res(k)`/P-vs-NP. Qualquer leitura nesse sentido é proibida (§7).

## 2. Definições

Fixados `p > 0` (erro DFA), `e ≥ 0` (erro PFA), `ρ ∈ (0,1)`:

- `D(ρ) = ρ/(1−ρ)·p²` (inflação DFA, Eixo 1), `F(ρ) = √ρ/(1−ρ)·e²` (PFA, Eixo 4),
- `M(ρ) = (D−F)/D = 1 − q²/√ρ`, `q = e/p` (fator de mitigação, §2.3),
- cascata (Eixo 2): `P⁽ⁿ⁾/P⁽⁰⁾ = ∏_{k=1}^{n}(1+a_k)`, `a_k = ρ_k/(1−ρ_k)·p_k² ≥ 0`.

## 3. Teorema TD (transição dupla parametrizada)

> **Teorema T1 (P).** Seja `q ∈ (0,1)`. Então:
> (a) existe **único** break-even `ρ* = q⁴` com `M(ρ*) = 0`;
> (b) existe **único** ponto de meia-mitigaç��o `ρ_1/2 = 4q⁴` com `M = 1/2`;
> (c) identidade de razão `ρ_1/2 = 4·ρ*`;
> (d) `0 < ρ* < ρ_1/2 < 1 ⟺ q < 1/√2`; se `1/√2 ≤ q < 1`, o break-even existe
>     mas a meia-mitigaç��o é **inatingível** em `[0,1)`; se `q ≥ 1`, nem
>     break-even há (PFA nunca vence).

**Prova.** `M′(ρ) = q²/(2ρ^{3/2}) > 0` (derivada checada no sympy), logo `M`
estritamente crescente, `lim_{ρ→0⁺} M = −∞`, `M(1⁻) = 1−q²`. Cada equação
`M = c < 1−q²` tem no máximo uma solução; `M = 0 ⟺ √ρ = q² ⟺ ρ = q⁴` (única);
`M = 1/2 ⟺ q²/√ρ = 1/2 ⟺ √ρ = 2q² ⟺ ρ = 4q⁴` (única). (c) é imediato. (d):
`4q⁴ < 1 ⟺ q⁴ < 1/4 ⟺ q < (1/4)^{1/4} = 1/√2`; e `q⁴ ≥ 1 ⟺ q ≥ 1` mata o
break-even pois `M(1⁻) = 1−q² ≤ 0` com `M` crescente. ∎

**Corolário C1 (instâncias, P).** Modelo A (`q = 1/2`): `ρ* = 1/16 = 0.0625`,
`ρ_1/2 = 1/4 = 0.25` (o "ρ_c do doc", agora com o nome certo). Modelo B
(`q = 1−r = 11/12 ≈ 0.917 > 1/√2`): `ρ* = (11/12)⁴ ≈ 0.7063` existe, mas
`ρ_1/2 = 4(11/12)⁴ ≈ 2.82` é inatingível.

**Corolário C2 — cap assintótico (novo, P).** `lim_{ρ→1⁻} M = 1−q²`: Modelo A
tende a 75%; Modelo B a `1−(11/12)² = 23/144 ≈ 0.16`. Sob o Modelo B o PFA
**jamais** passa de ~16% de mitigação — nem em saturação total.

## 4. Lower bound LB1 (mitigação mínima)

> **LB1 (P).** Para `ρ ≥ ρ₀`: `M(ρ) ≥ 1 − q²/√ρ₀`.

**Prova.** Monotonicidade de T1. ∎
**Instância:** Modelo A, `ρ ≥ 0.25 ⟹ M ≥ 0.5` — o 0.25 do doc reabilitado com
o significado correto: **limiar de garantia** (lower bound), não break-even.

## 5. Lower bound LB2 (cascata bullwhip aditiva)

> **LB2 (P).** Para `a_k ≥ 0`: `∏_{k=1}^{n}(1+a_k) ≥ 1 + Σ_{k=1}^{n} a_k`.

**Prova** (indução). Base `n=1` igualdade. Passo: supondo para `n`,
`∏_{k=1}^{n+1}(1+a_k) ≥ (1+S_n)(1+a_{n+1}) = 1+S_n+a_{n+1}+S_n·a_{n+1} ≥
1+S_{n+1}`, pois `S_n·a_{n+1} ≥ 0`. ∎ (Caso `n=3`: resto `ab+bc+ac+abc ≥ 0`,
checado simbolicamente.)

**Corolário C3 (P).** `P⁽ⁿ⁾/P⁽⁰⁾ ≥ 1 + Σ_k ρ_k/(1−ρ_k)·p_k²`; caso uniforme
`≥ 1 + n·ρ/(1−ρ)·p²` — a cascata cresce **pelo menos linearmente** em `n`.
Ex.: `ρ = 0.8`, `p = 1/6`, `n = 5` ⟹ inflação `≥ 1+5·(4/36) ≈ 1.56` (lower bound;
o relato 2.07× é consistente, acima do piso).

## 6. Verificação por máquina

`teorema_transicao_dupla_check.py`: derivada/resolução/razão/instâncias no
sympy (exato); LB1 em grade 2000 pontos × 2 modelos × 6 âncoras (pior
violação 0); LB2 em 3000 grades aleatórias (seed 11, pior 0.0) + forma exata
`n=3`. `out_teorema_td.json`: TUDO_OK=True. Teste `test_teorema_td.py` (5 testes).

## 7. Non-claims (proibido inferir)

- Nada aqui é lower bound de **complexidade** (`Res(k)`, DD_P, P-vs-NP).
- T1/LB1 condicionais às fórmulas-ponte (A) dos Eixos 1/4; LB2/C3 condicionais
  ao Eixo 2 (A). Se a ponte cair, o teorema cai junto (marcado, não escondido).
- Nível 4 `pending`: sem auditor externo; Lean formal futuro, não presente.

## 8. Próximos passos (estudo)

1. **Conjectura (C):** cascata PFA (Eixo 4 em `n` estágios com `√ρ_k`) —
   lower bound análogo com `Σ √ρ_k/(1−ρ_k)·e_k²`? Prova segue se a forma por
   estágio for `(1+b_k)` com `b_k ≥ 0` (checar definição do estágio PFA).
2. Formalizar T1/LB2 em Lean 4 (`lean/` futuro).
3. Auditoria externa do pacote (nível 4).
4. Q-estendida: `q ≥ 1` (PFA pior que DFA em toda carga) — caracterizar
   controladores degenerados; e sensibilidade `dρ*/dq = 4q³`.
