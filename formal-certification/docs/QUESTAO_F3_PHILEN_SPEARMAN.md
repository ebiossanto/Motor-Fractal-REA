# FCT-ADV-005 — Sweep phi_len + regressão H~phi + Spearman σ_tgt×θ (14/10/2026)

**Questões:** H=0.297 (phi 3,4) → 0.409 (phi 5) cruza 0.35: artefato ou sinal?
σ_tgt×θ tem monotonicidade (D4)?

**Ferramenta:** `f3_philen_spearman.py` (leitura read-only do repo Gödel;
phi=12 com 288/288 válidos gerado nesta frente)
**Certificado:** `certificate_fct_adv5.json` (`d0f25073…`, 11/11)

## Resultado (P)

- Z3 (phi 6,7,8,9,10,12): séries theta **binárias** (2 valores) → H≈0.004
  idêntico = resíduo degenerado, **não medição**. Não confirma nem refuta.
- H legado 0.297→0.409 é de pipeline **sem script sobrevivente** → (H);
  F3-H em aberto. Travessia phi=5 como "sinal": **retirada (R)**.
- Spearman **0/48** significativos (n×θ rho=0.0, p=1.0; n×tempo p>0.85):
  **D4 sem suporte**, segue pendente.

## Leitura honesta

A regressão H~phi pedida no frontier não é executável com metodologia única
hoje: misturar H-legado (pipeline perdido) com H-Z3 (degenerado) seria
desonesto. O avanço real: phi=12 inédito + prova de que o pipeline Z3 atual
não mede H (overhead determinístico em 2 valores) + D4 falsificada neste escopo.

**Status:** (P) máquina; (C) só auditoria externa.
