#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simulador_confiabilidade.py — Simulador do espectro de confiança formal
=======================================================================

Estuda a evolução dos quatro parâmetros de confiança ao longo da cadeia de
certificação (ideia do Projeto 1 — IA-RESEARCH-Logica, `src/python/formal_confidence/`):

    ρ (rho)   = confiança empírica    — evidência experimental bruta
    β (beta)  = confiança estatística — suporte amostral/estatístico
    γ (gama)  = confiança lógica      — rigor do argumento dedutivo
    δ (delta) = confiança formal      — verificação por kernel/checker independente

Hipótese investigada:  δ ≥ γ ≥ β ≥ ρ  (ordem de confiança por nível de certificação)

O simulador percorre os estágios da pipeline

    descoberta → formalização → verificação → meta-verificação → certificação externa

com um modelo simples e determinístico (semente fixa): cada estágio reduz a
incerteza acumulada dos parâmetros que ele efetivamente controla, respeitando
tetos por estágio (o que não é verificável num estágio não pode crescer nele).

Uso:
    python simulador_confiabilidade.py --semente 42 --passes 12 --out resultados.csv

Só stdlib. Determinístico: mesma semente ⇒ mesma saída.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

ESTAGIOS = ("descoberta", "formalizacao", "verificacao", "meta_verificacao", "certificacao_externa")

# Ganho máximo de cada parâmetro por estágio (fração da incerteza remanescente
# que o estágio tem autoridade para eliminar). ρ é ampliado por qualquer
# evidência; δ só cresce em verificação/meta-verificação/certificação externa.
GANHOS = {
    "rho":    {"descoberta": 0.50, "formalizacao": 0.10, "verificacao": 0.15, "meta_verificacao": 0.10, "certificacao_externa": 0.10},
    "beta":   {"descoberta": 0.20, "formalizacao": 0.15, "verificacao": 0.35, "meta_verificacao": 0.15, "certificacao_externa": 0.10},
    "gamma":  {"descoberta": 0.10, "formalizacao": 0.45, "verificacao": 0.20, "meta_verificacao": 0.20, "certificacao_externa": 0.05},
    "delta":  {"descoberta": 0.00, "formalizacao": 0.05, "verificacao": 0.45, "meta_verificacao": 0.30, "certificacao_externa": 0.20},
}

NOMES = {"rho": "ρ (empírica)", "beta": "β (estatística)", "gamma": "γ (lógica)", "delta": "δ (formal)"}

# Assíptotas do modelo: cada parâmetro converge para um teto próprio,
# refletindo a hipótese de ordem δ > γ > β > ρ em regime saturado.
TETOS = {"rho": 0.970, "beta": 0.985, "gamma": 0.995, "delta": 0.999}


def simular(semente: int = 42, passes: int = 1, ruido: float = 0.05) -> list[dict]:
    """Executa `passes` ciclos completos da pipeline e devolve a tabela de estados."""
    rng = random.Random(semente)
    estado = {"rho": 0.30, "beta": 0.20, "gamma": 0.15, "delta": 0.05}
    linhas = [{"pass": 0, "estagio": "inicial", **{k: round(v, 4) for k, v in estado.items()},
               "ordem_delta_ge_gamma_ge_beta_ge_rho": estado["delta"] >= estado["gamma"] >= estado["beta"] >= estado["rho"]}]

    for p in range(1, passes + 1):
        for estagio in ESTAGIOS:
            for param, ganhos in GANHOS.items():
                g = ganhos[estagio]
                if g <= 0:
                    continue
                incerteza = TETOS[param] - estado[param]
                if incerteza <= 0:
                    continue
                perturba = 1.0 + rng.uniform(-ruido, ruido)
                estado[param] = min(TETOS[param], estado[param] + incerteza * g * perturba)
            ordem = estado["delta"] >= estado["gamma"] >= estado["beta"] >= estado["rho"]
            linhas.append({
                "pass": p,
                "estagio": estagio,
                **{k: round(v, 4) for k, v in estado.items()},
                "ordem_delta_ge_gamma_ge_beta_ge_rho": ordem,
            })
    return linhas


def resumo(linhas: list[dict]) -> dict:
    finais = linhas[-1]
    violacoes = sum(1 for l in linhas if not l["ordem_delta_ge_gamma_ge_beta_ge_rho"])
    return {
        "passes": finais["pass"],
        "finais": {k: finais[k] for k in ("rho", "beta", "gamma", "delta")},
        "violacoes_da_ordem": violacoes,
        "proporcao_violacoes": round(violacoes / len(linhas), 4),
        "ordem_final_observada": " > ".join(
            sorted(("rho", "beta", "gamma", "delta"), key=lambda k: finais[k], reverse=True)
        ),
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1252 não imprime gregos
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--semente", type=int, default=42)
    parser.add_argument("--passes", type=int, default=4)
    parser.add_argument("--ruido", type=float, default=0.05)
    parser.add_argument("--out", default=None, help="CSV de saída (opcional)")
    args = parser.parse_args(argv)

    linhas = simular(args.semente, args.passes, args.ruido)
    cabecalho = ("pass", "estagio", "rho", "beta", "gamma", "delta", "ordem_delta_ge_gamma_ge_beta_ge_rho")
    print("  ".join(cabecalho))
    for l in linhas:
        print("  ".join(str(l[c]) for c in cabecalho))

    r = resumo(linhas)
    print("\nResumo:")
    print(f"  finais: {r['finais']}")
    print(f"  ordem final observada: {r['ordem_final_observada']}")
    print(f"  violações da ordem δ≥γ≥β≥ρ: {r['violacoes_da_ordem']} ({r['proporcao_violacoes']:.1%})")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=cabecalho)
            writer.writeheader()
            writer.writerows(linhas)
        print(f"  tabela gravada em: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
