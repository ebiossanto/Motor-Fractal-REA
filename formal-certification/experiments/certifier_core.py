#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
certifier_core.py — Núcleo de certificação formal (kit Ten-Proofs)
==================================================================

Implementa a cadeia de certificação em 5 níveis, inspirada no pipeline
openai/ten-proofs (Descoberta → Formalização → Verificação → Certificação →
Reprodutibilidade), adaptada aos projetos de Euzébio Soares:

    Nível 0  Proposição (claim)            — a afirmação formalizada
    Nível 1  Prova                          — artefato de prova (Lean, .md, .py)
    Nível 2  Verificação                    — checagem de máquina executada
    Nível 3  Meta-verificação               — checagem independente do verificador
    Nível 4  Certificação externa           — auditoria externa / âncora pública

Emitir:
    python certifier_core.py emitir   --spec experiments/spec_certificado.json \
                                      --out  certificates/certificate.json

Verificar:
    python certifier_core.py verificar --cert certificates/certificate.json

Garantias:
  * Determinístico: o certificate_hash NÃO depende de timestamp (é o hash
    canônico do conteúdo); o timestamp fica registrado ao lado, para rastreio.
  * Integridade: verificar recomputa os SHA-256 de TODOS os artefatos
    referenciados e compara com os registrados na emissão.
  * Só stdlib (hashlib, json, pathlib, argparse) — sem dependências.

Autor do kit: método Ten-Proofs adaptado por OpenCode para o ecossistema
IA-RESEARCH de Euzébio Soares. Versão 1.0.0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_ID = "ten-proofs-certificate/v1"
TOOL_NAME = "certifier_core.py"
TOOL_VERSION = "1.0.0"

# Campos que NÃO entram no certificate_hash (metadados de rastreio).
_EXCLUIR_DO_HASH = {"certificate_hash", "timestamp_utc"}

NIVEIS = {
    0: "proposicao",
    1: "prova",
    2: "verificacao",
    3: "meta_verificacao",
    4: "certificacao_externa",
}


# ---------------------------------------------------------------------------
# Primitivas criptográficas e de serialização
# ---------------------------------------------------------------------------

def sha256_bytes(data: bytes) -> str:
    """SHA-256 hexadecimal de um buffer de bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    """SHA-256 hexadecimal do conteúdo de um arquivo."""
    return sha256_bytes(Path(path).read_bytes())


def json_canonico(obj) -> bytes:
    """Serialização canônica: chaves ordenadas, sem espaços, UTF-8."""
    return json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def _resolver(caminho: str, base: Path) -> Path:
    p = Path(caminho)
    return p if p.is_absolute() else (base / p)


def _entrada_artefato(caminho: str, base: Path) -> dict:
    """Entrada canônica de um artefato: path relativo + sha256 + bytes."""
    resolvido = _resolver(caminho, base)
    if not resolvido.is_file():
        return {
            "path": Path(caminho).as_posix(),
            "sha256": None,
            "bytes": None,
            "status": "ausente",
        }
    return {
        "path": Path(caminho).as_posix(),
        "sha256": sha256_file(resolvido),
        "bytes": resolvido.stat().st_size,
        "status": "registrado",
    }


# ---------------------------------------------------------------------------
# Cadeia de certificação
# ---------------------------------------------------------------------------

def calcular_certificate_hash(certificado: dict) -> str:
    """Hash canônico do certificado, excluindo metadados de rastreio."""
    payload = {k: v for k, v in certificado.items() if k not in _EXCLUIR_DO_HASH}
    return sha256_bytes(json_canonico(payload))


def _validar_confianca(conf: dict) -> list[str]:
    """Valida o espectro ρ, β, γ, δ. Retorna avisos (não erros fatais)."""
    avisos = []
    chaves = ("empirical", "statistical", "logical", "formal")
    for c in chaves:
        v = conf.get(c)
        if not isinstance(v, (int, float)) or not (0.0 <= float(v) <= 1.0):
            avisos.append(f"confiança.{c}: valor inválido ou ausente ({v!r})")
    if all(isinstance(conf.get(c), (int, float)) for c in chaves):
        rho, beta, gama, delta = (float(conf[c]) for c in chaves)
        if not (delta >= gama >= beta >= rho):
            avisos.append(
                "espectro fora da hipótese de ordem δ ≥ γ ≥ β ≥ ρ "
                f"(recebido ρ={rho}, β={beta}, γ={gama}, δ={delta})"
            )
    return avisos


def emitir_certificado(spec: dict, base_dir: str | Path) -> dict:
    """
    Monta o certificado a partir de uma especificação JSON.

    Spec esperada (todos os campos opcionais, mas a cadeia fica incompleta
    se os artefatos não forem fornecidos):

    {
      "project": "IA-RESEARCH-Logica",
      "claim":  {"id": "LC-001", "statement": "...", "source": "proofs/x.md"},
      "proof":  {"artifacts": ["proofs/y.md", "lean/Z.lean"], "note": "..."},
      "verification":       {"method": "...", "tool": "...", "command": "...",
                             "result": "pass|fail", "output": "results/out.txt"},
      "meta_verification":  {"method": "...", "tool": "...", "command": "...",
                             "result": "pass|fail|pending", "output": null},
      "external_certification": {"auditor": "...", "status": "pending|pass|fail",
                                 "reference": ""},
      "confidence": {"empirical": 0.8, "statistical": 0.7,
                     "logical": 0.9, "formal": 0.6}
    }
    """
    base = Path(base_dir)
    avisos: list[str] = []

    claim = spec.get("claim", {}) or {}
    if not claim.get("statement"):
        avisos.append("Nível 0: proposição sem enunciado (claim.statement)")

    cert: dict = {
        "schema": SCHEMA_ID,
        "project": spec.get("project", "desconhecido"),
        "niveis": {},
        "confidence": dict(spec.get("confidence", {}) or {}),
        "generator": {"tool": TOOL_NAME, "version": TOOL_VERSION},
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    # Nível 0 — Proposição
    cert["niveis"]["0_proposicao"] = {
        "id": claim.get("id", "sem-id"),
        "statement": claim.get("statement", ""),
        "source": _entrada_artefato(claim["source"], base) if claim.get("source") else None,
        "status": "registrado" if claim.get("statement") else "ausente",
    }

    # Nível 1 — Prova
    proof = spec.get("proof", {}) or {}
    artefatos = [_entrada_artefato(a, base) for a in proof.get("artifacts", [])]
    faltando = [a["path"] for a in artefatos if a["status"] == "ausente"]
    cert["niveis"]["1_prova"] = {
        "artifacts": artefatos,
        "note": proof.get("note", ""),
        "status": "ausente" if not artefatos else ("parcial" if faltando else "registrado"),
    }
    if faltando:
        avisos.append(f"Nível 1: artefatos ausentes: {', '.join(faltando)}")

    # Nível 2 — Verificação
    ver = spec.get("verification", {}) or {}
    saida = _entrada_artefato(ver["output"], base) if ver.get("output") else None
    cert["niveis"]["2_verificacao"] = {
        "method": ver.get("method", ""),
        "tool": ver.get("tool", ""),
        "command": ver.get("command", ""),
        "result": ver.get("result", "pending"),
        "output": saida,
        "status": "registrado" if ver.get("result") in ("pass", "fail") else "pendente",
    }
    if ver.get("result") not in ("pass", "fail", "pending"):
        avisos.append(f"Nível 2: resultado inesperado ({ver.get('result')!r})")

    # Nível 3 — Meta-verificação
    meta = spec.get("meta_verification", {}) or {}
    saida_m = _entrada_artefato(meta["output"], base) if meta.get("output") else None
    cert["niveis"]["3_meta_verificacao"] = {
        "method": meta.get("method", ""),
        "tool": meta.get("tool", ""),
        "command": meta.get("command", ""),
        "result": meta.get("result", "pending"),
        "output": saida_m,
        "status": "registrado" if meta.get("result") in ("pass", "fail") else "pendente",
    }

    # Nível 4 — Certificação externa
    ext = spec.get("external_certification", {}) or {}
    cert["niveis"]["4_certificacao_externa"] = {
        "auditor": ext.get("auditor", "pendente"),
        "status": ext.get("status", "pending"),
        "reference": ext.get("reference", ""),
    }

    # Espectro de confiança
    avisos.extend(_validar_confianca(cert["confidence"]))

    # Avisos entram ANTES do hash (fazem parte do conteúdo certificado)
    cert["avisos"] = avisos

    # Hash da cadeia (independente de timestamp)
    cert["certificate_hash"] = calcular_certificate_hash(cert)
    return cert


def verificar_certificado(cert: dict, base_dir: str | Path) -> dict:
    """
    Reverifica um certificado: (i) todos os artefatos ainda batem (SHA-256);
    (ii) o certificate_hash confere; (iii) estado de cada nível da cadeia.
    Retorna {"ok": bool, "checks": [ {...}, ... ]}.
    """
    base = Path(base_dir)
    checks: list[dict] = []

    def add(nome: str, ok: bool, detalhe: str = "") -> None:
        checks.append({"check": nome, "ok": ok, "detalhe": detalhe})

    # 1. Hash do certificado
    esperado = cert.get("certificate_hash")
    calculado = calcular_certificate_hash(cert)
    add(
        "certificate_hash",
        esperado == calculado,
        f"registrado={esperado} recalculado={calculado}",
    )

    # 2. Artefatos Nível 0 (fonte da proposição)
    n0 = cert.get("niveis", {}).get("0_proposicao", {})
    src = n0.get("source")
    if src:
        ok = _checar_artefato(src, base)
        add("nivel0_fonte", ok, src["path"])

    # 3. Artefatos Nível 1
    n1 = cert.get("niveis", {}).get("1_prova", {})
    for art in n1.get("artifacts", []):
        ok = _checar_artefato(art, base)
        add(f"nivel1_prova:{art['path']}", ok, art["path"])

    # 4. Saídas Nível 2 / 3
    for nivel, chave in (("2_verificacao", "nivel2"), ("3_meta_verificacao", "nivel3")):
        out = cert.get("niveis", {}).get(nivel, {}).get("output")
        if out:
            ok = _checar_artefato(out, base)
            add(f"{chave}_output:{out['path']}", ok, out["path"])

    # 5. Estado consolidado da cadeia
    estados = {k: v.get("status", "ausente") for k, v in cert.get("niveis", {}).items()}
    cadeia_completa = (
        estados.get("0_proposicao") == "registrado"
        and estados.get("1_prova") == "registrado"
        and estados.get("2_verificacao") == "registrado"
        and estados.get("3_meta_verificacao") == "registrado"
    )
    add(
        "cadeia_n0_a_n3",
        cadeia_completa,
        "completa" if cadeia_completa else f"estados={estados}",
    )

    ok = all(c["ok"] for c in checks)
    return {"ok": ok, "checks": checks, "estados": estados}


def _checar_artefato(entrada: dict, base: Path) -> bool:
    resolvido = _resolver(entrada["path"], base)
    if not resolvido.is_file():
        return False
    return sha256_file(resolvido) == entrada.get("sha256")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _base_padrao(start: Path) -> Path:
    """
    Raiz do repositório a partir de um arquivo: o ancestral mais próximo que
    contém `.git`. Permite que as specs usem caminhos relativos à RAIZ do
    projeto (ex.: "src/python/verifica_espectro.py"), independentemente de
    onde o certifier é invocado. Fallback: pasta do próprio arquivo.
    """
    p = start.resolve()
    if p.is_file():
        p = p.parent
    for candidato in [p, *p.parents]:
        if (candidato / ".git").exists():
            return candidato
    return start.parent


def _cmd_emitir(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec)
    if not spec_path.is_file():
        print(f"[ERRO] spec não encontrada: {spec_path}", file=sys.stderr)
        return 2
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))  # tolera BOM do Windows
    base = Path(args.base) if args.base else _base_padrao(spec_path)
    cert = emitir_certificado(spec, base)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(cert, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"[OK] certificado emitido: {out}")
    print(f"     certificate_hash: {cert['certificate_hash']}")
    for aviso in cert.get("avisos", []):
        print(f"     [AVISO] {aviso}")
    return 0


def _cmd_verificar(args: argparse.Namespace) -> int:
    cert_path = Path(args.cert)
    if not cert_path.is_file():
        print(f"[ERRO] certificado não encontrado: {cert_path}", file=sys.stderr)
        return 2
    cert = json.loads(cert_path.read_text(encoding="utf-8-sig"))  # tolera BOM do Windows
    base = Path(args.base) if args.base else _base_padrao(cert_path)
    relatorio = verificar_certificado(cert, base)
    for c in relatorio["checks"]:
        marca = "PASS" if c["ok"] else "FAIL"
        print(f"  [{marca}] {c['check']}" + (f" — {c['detalhe']}" if c["detalhe"] else ""))
    print(
        f"[{'OK' if relatorio['ok'] else 'FALHOU'}] verificação da cadeia "
        f"({sum(c['ok'] for c in relatorio['checks'])}/{len(relatorio['checks'])})"
    )
    return 0 if relatorio["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1252 não imprime acentos/gregos
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="Cadeia de certificação formal Ten-Proofs (Níveis 0–4).",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p_emit = sub.add_parser("emitir", help="Emitir certificate.json a partir de uma spec")
    p_emit.add_argument("--spec", required=True, help="Caminho do spec JSON")
    p_emit.add_argument("--out", required=True, help="Caminho de saída do certificate.json")
    p_emit.add_argument("--base", default=None, help="Base para resolver caminhos (padrão: pasta do projeto)")
    p_emit.set_defaults(func=_cmd_emitir)

    p_ver = sub.add_parser("verificar", help="Reverificar um certificate.json")
    p_ver.add_argument("--cert", required=True, help="Caminho do certificate.json")
    p_ver.add_argument("--base", default=None, help="Base para resolver caminhos (padrão: pasta do projeto)")
    p_ver.set_defaults(func=_cmd_verificar)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
