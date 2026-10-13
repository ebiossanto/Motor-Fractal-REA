---
name: Ten-Proofs
description: Método padrão de trabalho para o ecossistema IA-RESEARCH de Euzébio Soares. Usar em TODO trabalho de pesquisa, código, formalização ou documento produzido neste workspace — aplica a pipeline Descoberta → Formalização → Verificação → Certificação → Reprodutibilidade com cadeia de certificação em 5 níveis (0 Proposição, 1 Prova, 2 Verificação, 3 Meta-verificação, 4 Certificação externa) e espectro de confiança ρ, β, γ, δ. Ativar também ao criar novos repositórios, branches, protótipos, testes ou relatórios.
---

# Método Ten-Proofs (padrão obrigatório)

Todo trabalho desenvolvido neste workspace segue o método do **Documento de
Diretrizes para o OpenCode** (integração das ideias de `openai/ten-proofs` aos
projetos de Euzébio Soares). A identidade conceitual de cada projeto é
preservada: o método entra como **camada aditiva**, nunca reescrevendo o que
já foi produzido.

## Pipeline

```
Descoberta → Formalização → Verificação → Certificação → Reprodutibilidade
```

## Cadeia de certificação (obrigatórias para qualquer afirmação de resultado)

```
Nível 0  Proposição            id + enunciado formal + fonte (hash SHA-256)
Nível 1  Prova                 artefato real (.lean, .md, .py) (hash)
Nível 2  Verificação           checagem executada POR MÁQUINA: comando reproduzível + saída congelada + hash
Nível 3  Meta-verificação      checagem independente do verificador (pytest, referee interno, reexecução)
Nível 4  Certificação externa  auditor real / âncora pública — status explícito (geralmente "pending")
```

## Espectro de confiança

Cada cadeia registra quatro parâmetros em `[0,1]`:

- **ρ** confiança empírica (evidência experimental)
- **β** confiança estatística (suporte amostral)
- **γ** confiança lógica (rigor dedutivo)
- **δ** confiança formal (kernel/checker independente)

Hipótese investigada: `δ ≥ γ ≥ β ≥ ρ`. Violações geram aviso no certificado,
nunca silêncio.

## Procedimento padrão (checklist)

1. **Mapear antes de agir.** Leia o README e a estrutura do projeto; nunca
   altere a essência conceitual existente (somente aditivo).
2. **Criar/entender a branch.** Trabalhos novos de certificação vivem na branch
   `formal-certification` (criar a partir da branch principal se não existir).
3. **Subárvore obrigatória** em cada projeto tocado:

   ```
   formal-certification/
   ├── README.md                       índice + status da cadeia
   ├── docs/cadeia_de_certificacao.md  níveis 0–4 com artefatos REAIS do projeto
   ├── docs/espectro_confiabilidade_formal.md
   ├── lean/                           formalizações Lean 4 quando aplicável
   ├── experiments/certifier_core.py   cópia do kit (_padroes/ten_proofs_kit)
   ├── experiments/spec_certificado.json
   ├── certificates/certificate.json   emitido pelo certifier
   └── tests/test_cadeia_certificacao.py
   ```

4. **Kit compartilhado.** Copiar componentes de `_padroes/ten_proofs_kit/`
   (nunca importar por caminho relativo entre repositórios — copiar, para o
   repositório ser autossuficiente). Antes de copiar, conferir se o kit mudou.
5. **Emitir e reverificar.**

   ```powershell
   python formal-certification/experiments/certifier_core.py emitir --spec formal-certification/experiments/spec_certificado.json --out formal-certification/certificates/certificate.json
   python formal-certification/experiments/certifier_core.py verificar --cert formal-certification/certificates/certificate.json
   python -m pytest formal-certification/tests -v
   ```

6. **Honestidade epistêmica (regra de ouro).** Nível não executado ⇒ `pending`.
   Prova escrita a mão NÃO é "verificada"; verificação executada em máquina é.
   Auditoria externa só existe com auditor externo real.
7. **Commit seletivo.** Commitar apenas `formal-certification/**` (e artefatos
   novos do método); nunca incluir mudanças pré-existentes não relacionadas
   (banners, `.pyc`, downloads) no mesmo commit.
8. **Registrar no relatório.** Ao final de integrações multi-repositório,
   atualizar `RELATORIO_INTEGRACAO_TEN_PROOFS.md` na raiz do workspace com
   alterações, impacto, riscos e próximos passos.

## Fontes do kit

| Recurso | Caminho |
|---|---|
| Certifier (emitir/verificar) | `_padroes/ten_proofs_kit/certifier_core.py` |
| Simulador ρ/β/γ/δ | `_padroes/ten_proofs_kit/simulador_confiabilidade.py` |
| Testes do kit | `_padroes/ten_proofs_kit/test_kit.py` |
| Templates de docs | `_padroes/ten_proofs_kit/templates/` |
| Guia do kit | `_padroes/ten_proofs_kit/README.md` |

## Escopo dos projetos-alvo do documento de diretrizes

- **Presentes neste workspace:** IA-RESEARCH-Logica, IA-RESEARCH-MUTARIC,
  IA-RESEARCH-NFT-CONTAINER (+ os demais repositórios IA-RESEARCH).
- **Ausentes (aplicar o mesmo método quando surgirem):** JEV-IA (módulos
  JEV-R/P/C/A), ORIGO (diretivas `@claim/@proof/@verify/@certificate`),
  ORIGO Overlay (`[[verified]] [[proven]] [[certified]]`), AI-FORMAL-CERTIFICATION
  (repositório-ponte Lean).
