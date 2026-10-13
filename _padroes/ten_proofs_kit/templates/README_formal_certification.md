# Certificação Formal — `<NOME_DO_PROJETO>`

Este subprojeto aplica o **método Ten-Proofs** ao trabalho já existente no
repositório, sem alterar sua essência conceitual:

```
Descoberta → Formalização → Verificação → Certificação → Reprodutibilidade
```

## Cadeia de certificação (Níveis 0–4)

| Nível | O que é | Status neste projeto |
|---|---|---|
| 0 | Proposição | `<registrado / pendente>` |
| 1 | Prova | `<registrado / pendente>` |
| 2 | Verificação (máquina) | `<registrado / pendente>` |
| 3 | Meta-verificação | `<registrado / pendente>` |
| 4 | Certificação externa | `pending` (auditoria externa) |

## Estrutura

```
formal-certification/
├── README.md                      ← este índice
├── docs/
│   ├── cadeia_de_certificacao.md  ← Níveis 0–4 com artefatos reais
│   └── espectro_confiabilidade_formal.md  ← ρ, β, γ, δ do projeto
├── lean/                          ← rascunhos/formalizações Lean 4 (quando aplicável)
├── experiments/
│   ├── certifier_core.py          ← núcleo determinístico de emissão/verificação
│   ├── simulador_confiabilidade.py
│   └── spec_certificado.json      ← especificação da cadeia atual
├── certificates/
│   └── certificate.json           ← certificado emitido (hash da cadeia)
└── tests/
    └── test_cadeia_certificacao.py
```

## Comandos

```powershell
# 1) emitir o certificado
python formal-certification/experiments/certifier_core.py emitir --spec formal-certification/experiments/spec_certificado.json --out formal-certification/certificates/certificate.json

# 2) reverificar integridade da cadeia
python formal-certification/experiments/certifier_core.py verificar --cert formal-certification/certificates/certificate.json

# 3) testes automatizados
python -m pytest formal-certification/tests -v
```

## Relação com o trabalho existente

`<1–5 linhas: quais resultados do repositório esta cadeia certifica e onde eles vivem>`
