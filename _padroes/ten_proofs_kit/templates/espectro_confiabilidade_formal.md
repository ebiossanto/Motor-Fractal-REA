# Espectro de Confiabilidade Formal — ρ, β, γ, δ

**Projeto:** `<NOME_DO_PROJETO>`
**Data:** `<AAAA-MM-DD>`

## 1. Definição dos parâmetros

Quatro camadas distintas de confiança, cada uma com seu próprio suporte:

| Símbolo | Nome | O que sustenta | Exemplo no projeto |
|---|---|---|---|
| ρ (rho) | confiança empírica | evidência experimental bruta, observações, execuções | `<ex.: resultado de execução exaustiva>` |
| β (beta) | confiança estatística | suporte amostral, intervalos, controle de múltiplas comparações | `<ex.: bootstrap, correção>` |
| γ (gama) | confiança lógica | rigor do argumento dedutivo escrito (prova humana/IA) | `<ex.: cadeia de lemas em proofs/>` |
| δ (delta) | confiança formal | checagem por kernel/checker independente (Lean, verificador próprio) | `<ex.: lake build / certifier_core>` |

## 2. Hipótese de ordem

$$\delta \ge \gamma \ge \beta \ge \rho$$

**Interpretação:** confiança formal só pode superar a lógica quando a prova
foi formalizada sem lacunas; confiança lógica só supera a estatística quando
a evidência estatística é usada como premissa, não como sucedâneo de prova.

**Implicações investigáveis:**

1. *Cascata de rebaixamento:* se δ é atribuído sem γ correspondente, a cadeia
   está falsificada — o certificador deve registrar `aviso`.
2. *Platô empírico:* projetos com ρ alto e δ baixo (experimentos sem
   formalização) convivem com projetos de δ alto e ρ modesto (formalização de
   objetos abstratos). O espectro permite comparar ambos sem confundir métricas.
3. *Custo marginal:* em cada estágio da pipeline, o ganho de δ por unidade de
   trabalho cai — ver `formal-certification/experiments/simulador_confiabilidade.py`.

## 3. Valores no projeto atual

| Estágio da pipeline | ρ | β | γ | δ | Observação |
|---|---|---|---|---|---|
| `<descoberta>` | `<…>` | `<…>` | `<…>` | `<…>` | `<…>` |
| `<formalização>` | `<…>` | `<…>` | `<…>` | `<…>` | `<…>` |
| `<verificação>` | `<…>` | `<…>` | `<…>` | `<…>` | `<…>` |
| `<meta-verificação>` | `<…>` | `<…>` | `<…>` | `<…>` | `<…>` |
| `<certificação externa>` | `<…>` | `<…>` | `<…>` | `<…>` | `<…>` |

## 4. Estudo simulado

Executar:

```powershell
python formal-certification/experiments/simulador_confiabilidade.py --semente 42 --passes 4 --out formal-certification/results/simulacao_confiabilidade.csv
```

O simulador é determinístico (semente fixa) e mede, por passo, se a ordem
δ ≥ γ ≥ β ≥ ρ se sustenta e com que frequência ela é violada durante a
transição entre estágios.
