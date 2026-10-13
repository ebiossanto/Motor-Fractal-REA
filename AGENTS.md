# AGENTS.md — Workspace IA-RESEARCH (Euzébio Soares)

## Método padrão (obrigatório)

Todo trabalho neste workspace segue o **método Ten-Proofs**
(Descoberta → Formalização → Verificação → Certificação → Reprodutibilidade),
com cadeia de certificação em 5 níveis (0 Proposição · 1 Prova · 2 Verificação ·
3 Meta-verificação · 4 Certificação externa) e espectro de confiança
ρ (empírica), β (estatística), γ (lógica) e δ (formal), com hipótese de ordem `δ ≥ γ ≥ β ≥ ρ`.

- Instruções completas: skill **`ten-proofs`** (`.opencode/skills/ten-proofs/SKILL.md`) — carregar com a ferramenta `skill`.
- Kit executável compartilhado: `_padroes/ten_proofs_kit/` (certifier, simulador, testes, templates).
- Relatório consolidado das integrações: `RELATORIO_INTEGRACAO_TEN_PROOFS.md`.

## Regras de ouro

1. **Aditivo, não destrutivo.** Nunca alterar a essência conceitual dos
   projetos existentes; o método entra como subárvore `formal-certification/`.
2. **Honestidade epistêmica.** Nível não executado ⇒ `pending`. "Verificado"
   exige comando reproduzível + saída congelada + hash SHA-256 registrado.
3. **Reprodutibilidade.** Nada de "funcionou aqui": todo resultado tem comando
   exato e semente fixa quando houver aleatoriedade.
4. **Commit seletivo.** Commits do método tocam apenas `formal-certification/**`
   (branch `formal-certification`); mudanças pré-existentes não relacionadas
   (banners, `.pyc`) nunca entram no mesmo commit.

## Estrutura do workspace

```
zero\
├── .opencode/skills/ten-proofs/   ← skill do método (padrão desde 12/10/2026)
├── _padroes/                      ← padrões compartilhados (banners, kit Ten-Proofs)
├── RELATORIO_INTEGRACAO_TEN_PROOFS.md
├── IA-RESEARCH-Logica/            formal-certification/ ✔
├── IA-RESEARCH-MUTARIC/           formal-certification/ ✔
├── IA-RESEARCH-NFT-CONTAINER/     formal-certification/ ✔
├── IA-research-Godel-e-Krajicek/  formal-certification/ ✔
├── IA-RESEARCH-DELTA-H/           formal-certification/ ✔
├── IA-RESEARCH-QESCUDO-NR12/      formal-certification/ ✔
├── IA-Research-Quantum-Local-Packing/  formal-certification/ ✔
├── IA-Research-Cost-of-Equivariance/   formal-certification/ ✔
├── IA-Research-Desafio-Criptogr-fico/  formal-certification/ ✔
├── IA-RESEARCH-PESQUISA-ASSISTIDA/     formal-certification/ ✔
└── IA-RESEARCH-REINO-DIGITAL-BRIEF/    formal-certification/ ✔
```

## Convenções

- Idioma: português (documentos); comandos em `powershell` no Windows.
- Python 3.12 + pytest disponíveis; Lean 4 via `elan`/`lake` (toolchain por
  repositório — verificar `lean-toolchain` antes de afirmar verificação Lean).
- Cada certificado: `formal-certification/certificates/certificate.json`,
  esquema `ten-proofs-certificate/v1`.
