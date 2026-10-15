# FCT-ADV-002 — Tracker rho(t): regimes, episódios e recomendação (14/10/2026)

**Questão:** F1 corrigido — quando o sistema cruza cada limiar (BE-A 0.0625,
doc 0.25, BE-B 0.706), quanto tempo fica acima, e qual modelo recomenda PFA?

**Ferramenta:** `formal-certification/experiments/fct_rho_regime_tracker.py`
**Certificado:** `certificate_fct_adv2.json` (`9a10e4f8…`, 9/9)

## Resultado (P)

- ρ_global = 0.272, P99 = 100.0, n = 300.
- Episódios acima: BE-A **53**, 0.25 **21**, BE-B **9**.
- ρ_global → Modelo A: PFA; doc 0.25: PFA; Modelo B: DFA suficiente.
- Saturação P90+ em 9 episódios acima de 0.706 (dwell medido por episódio
  em `out_fct_rho_regimes.json`); série congelada em `out_fct_rho_series.csv`.

## Leitura honesta

Sem fixar o modelo PFA não há recomendação única — o tracker registra os
três regimes lado a lado em vez de escolher. Fecha F1-dinâmico; reabre a
escolha do modelo como decisão explícita (não mais "ρ_c" ambíguo).

**Status:** (P) máquina; (C) só auditoria externa (nível 4).
