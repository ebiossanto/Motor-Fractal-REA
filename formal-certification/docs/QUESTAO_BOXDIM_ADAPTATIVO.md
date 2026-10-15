# FCT-ADV-004 — Box-dim com bins adaptativos (14/10/2026)

**Questão:** box-counting legacy satura; `ema→donoho` Box-D p<1e-11 suspeito
de espúrio. Bins adaptativos resgatam D?

**Ferramenta:** `fct_boxdim_adaptive.py` (bordas por quantis, k=2..12, 1D e
grade 2D; critério: D finito + R2>=0.9; saturação exata N(k)=k → "trivial")
**Certificado:** `certificate_fct_adv4.json` (`1f1f4687…`, 9/9)

## Resultado (P)

5/6 resgatados: raw 1D **0.86** / 2D **1.65**; donoho 2D **1.24**; tail
**0.77**/**1.04**. Donoho-1D: D=1.0/R2=1.0 exatos = **saturação trivial**,
não medição (marcado, não contado como resgate).

## Leitura

D2 reabilitado como métrica **auxiliar** onde resgatado; onde não, segue
só-H (F2 mantido). O p<1e-11 legado em `ema→donoho` permanece classificado
como espúrio até re-teste com bins adaptativos no pipeline de filtros
(não executado aqui — sem claim).

**Status:** (P) máquina; (C) só auditoria externa.
