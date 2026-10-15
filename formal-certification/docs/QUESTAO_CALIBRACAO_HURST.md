# FCT-ADV-003 — Calibração de estimadores H com ground-truth (14/10/2026)

**Questão:** Higuchi 0.22 × R/S 0.91 × DFA inválido no dado real. Quem é
confiável sob spikes + platô de saturação?

**Ferramenta:** `formal-certification/experiments/hurst_estimator_calibration.py`
(ARFIMA(0,d,0), H={0.2,0.3,0.35,0.5,0.7} × {limpo,spikes,plato,real_like},
semente 7, N=300; 100 linhas em `out_hurst_calibration.csv`)
**Certificado:** `certificate_fct_adv3.json` (`ee58b684…`, 9/9)

## Resultado (P)

- Ranking (MAE): **varlag 0.296 > higuchi 0.297 > rs 0.338 > dfa 0.549 > box2d 0.657**.
- Viés real_like: higuchi −0.29, varlag −0.25 (subestimam), rs +0.47,
  dfa +0.86, box2d +0.64 (superestimam).
- H real corrigido (H − viés, mediana dos válidos): **raw 0.44** (cruza 0.35),
  **Donoho 0.55**. O "raw anti-persistente 0.26" era subestimação por spikes.

## Leitura honesta

A travessia de 0.35 não é só artefacto de filtro: o raw corrigido também
cruza. DFA e box2d declarados frágeis neste regime (não usados sozinhos).
Síntese numérica honesta, não prova de universalidade (5 H × 4 condições).

**Status:** (P) máquina; (C) só auditoria externa (nível 4).
