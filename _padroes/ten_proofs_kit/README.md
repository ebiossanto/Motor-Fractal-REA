# Kit Ten-Proofs — `_padroes/ten_proofs_kit/`

Infraestrutura compartilhada de **descoberta, validação e certificação de
conhecimento produzido por IA**, inspirada metodologicamente no repositório
`openai/ten-proofs` e nos princípios do **Documento de Diretrizes para o
OpenCode** (Integração das ideias do Ten-Proofs aos projetos de Euzébio Soares).

## Pipeline

```
Descoberta → Formalização → Verificação → Certificação → Reprodutibilidade
```

Cadeia de certificação por afirmação:

```
Nível 0  Proposição          claim id + enunciado + fonte (hash)
Nível 1  Prova               artefatos (Lean, .md, .py) (hash)
Nível 2  Verificação         checagem executada por máquina (comando + saída congelada)
Nível 3  Meta-verificação    checagem independente do verificador (pytest/referee)
Nível 4  Certificação externa auditor externo / âncora pública (status explícito)
```

## Componentes

| Arquivo | Função |
|---|---|
| `certifier_core.py` | Núcleo determinístico: `emitir` e `verificar` certificates.json (SHA-256 da cadeia inteira; só stdlib). |
| `simulador_confiabilidade.py` | Simulador do espectro ρ, β, γ, δ ao longo da pipeline (determinístico, semente fixa). |
| `test_kit.py` | Testes do kit (pytest): emissão, verificação, adulteração, simulador. |
| `templates/README_formal_certification.md` | Template do índice `formal-certification/README.md` de cada projeto. |
| `templates/cadeia_de_certificacao.md` | Template do documento de níveis 0–4. |
| `templates/espectro_confiabilidade_formal.md` | Template do documento ρ/β/γ/δ. |

## Instalação em um projeto

1. Criar a branch `formal-certification` no repositório do projeto.
2. Copiar `certifier_core.py` e `simulador_confiabilidade.py` para
   `<projeto>/formal-certification/experiments/`.
3. Preencher os templates de `templates/` em `<projeto>/formal-certification/docs/`,
   sempre com **artefatos reais do repositório** (nada genérico).
4. Escrever `experiments/spec_certificado.json` apontando para 1–3 cadeias reais.
5. Emitir `certificates/certificate.json` e escrever `tests/test_cadeia_certificacao.py`.
6. Rodar testes; commitar **apenas** `formal-certification/**` na branch.

## Testar o kit

```powershell
cd _padroes\ten_proofs_kit
python -m pytest test_kit.py -v
```

## Regras de honestidade (obrigatórias)

1. Nível não cumprido ⇒ `pending`/`pendente` — nunca afirmar verificação que
   não foi executada nesta máquina.
2. "Verificado" só com comando reproduzível + saída congelada + hash registrado.
3. Auditoria externa (Nível 4) é sempre `pending` até haver um auditor real.
4. O `certificate_hash` é independente de timestamp — dois emits idênticos
   geram o mesmo hash (reprodutibilidade).
5. Não alterar a essência conceitual dos projetos existentes: o método entra
   como camada aditiva (`formal-certification/`), nunca reescrevendo o que já
   foi produzido.
