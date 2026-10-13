# Cadeia de Certificação Formal — Níveis 0–4

**Projeto:** `<NOME_DO_PROJETO>`
**Subprojeto:** `formal-certification/`
**Método:** Ten-Proofs adaptado (Descoberta → Formalização → Verificação → Certificação → Reprodutibilidade)
**Data:** `<AAAA-MM-DD>`

> Documento que formaliza, para este projeto, a cadeia
> **Proposição → Prova → Verificação → Meta-Verificação → Certificação Externa**
> (inspirada no pipeline openai/ten-proofs). Cada nível é registrado com
> artefatos reais e hashes SHA-256 em `certificates/certificate.json`.

## 0. Princípio

Uma afirmação produzida (ou verificada) por IA só é tratada como conhecimento
do projeto quando percorre a cadeia completa. Nível não cumprido ⇒ status
honesto ("pendente"), nunca afirmado como concluído.

## Nível 0 — Proposição

| Campo | Valor |
|---|---|
| Identificador | `<ID-XXX>` |
| Enunciado | `<enunciado formal da afirmação>` |
| Fonte | `<arquivo do projeto onde vive a afirmação>` |
| Classificação A–D | A definição / B lema elementar / C teorema condicionado / D conjectura |

## Nível 1 — Prova

| Artefato | Caminho | Papel |
|---|---|---|
| `<nome>` | `<caminho>` | prova escrita / rascunho Lean / verificador |

## Nível 2 — Verificação (checagem de máquina)

| Campo | Valor |
|---|---|
| Método | `<exaustiva / estatística / simulação / type-check>` |
| Ferramenta | `<python / lean / lake / …>` |
| Comando reproduzível | `<comando exato>` |
| Resultado | `pass` / `fail` / `pending` |
| Saída congelada | `<arquivo>` |

## Nível 3 — Meta-Verificação (verificador verificado)

| Campo | Valor |
|---|---|
| Método | `<reexecução independente / testes adversariais / propriedades / auditoria interna>` |
| Ferramenta | `<pytest / referee interno / …>` |
| Comando | `<comando exato>` |
| Resultado | `pass` / `fail` / `pending` |

## Nível 4 — Certificação externa

| Campo | Valor |
|---|---|
| Auditor | `<quem>` |
| Status | `pending` / `pass` / `fail` |
| Referência | `<link, e-mail, issue, relatório>` |

## Espectro de confiança alocado a esta cadeia

| Parâmetro | Valor | Base |
|---|---|---|
| ρ — empírica | `<0.00–1.00>` | `<evidência experimental>` |
| β — estatística | `<0.00–1.00>` | `<suporte amostral>` |
| γ — lógica | `<0.00–1.00>` | `<rigor dedutivo>` |
| δ — formal | `<0.00–1.00>` | `<kernel/checker independente>` |

## Como reproduzir / reverificar

```powershell
# emitir (após alterações nos artefatos)
python formal-certification/experiments/certifier_core.py emitir --spec formal-certification/experiments/spec_certificado.json --out formal-certification/certificates/certificate.json

# reveribir
python formal-certification/experiments/certifier_core.py verificar --cert formal-certification/certificates/certificate.json

# testes da cadeia
python -m pytest formal-certification/tests -v
```
