#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes do kit Ten-Proofs (certifier_core + simulador).
Executar a partir da pasta do kit:

    python -m pytest test_kit.py -v
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import certifier_core as cc  # noqa: E402
import simulador_confiabilidade as sim  # noqa: E402


@pytest.fixture()
def projeto_tmp(tmp_path: Path) -> Path:
    """Mini-projeto temporário com claim, prova e saída de verificação."""
    (tmp_path / "proofs").mkdir()
    (tmp_path / "results").mkdir()
    (tmp_path / "proofs" / "prova.md").write_text("# Prova\nAssume A logo B.\n", encoding="utf-8")
    (tmp_path / "results" / "saida.txt").write_text("todos os casos: OK\n", encoding="utf-8")
    return tmp_path


def _spec_ok() -> dict:
    return {
        "project": "KIT-TESTE",
        "claim": {"id": "KT-001", "statement": "A → B", "source": "proofs/prova.md"},
        "proof": {"artifacts": ["proofs/prova.md"], "note": "prova elementar"},
        "verification": {
            "method": "exaustiva", "tool": "python", "command": "python verifica.py",
            "result": "pass", "output": "results/saida.txt",
        },
        "meta_verification": {
            "method": "reexecucao-independente", "tool": "pytest", "command": "python -m pytest",
            "result": "pass", "output": "results/saida.txt",
        },
        "external_certification": {"auditor": "pendente", "status": "pending", "reference": ""},
        "confidence": {"empirical": 0.60, "statistical": 0.70, "logical": 0.90, "formal": 0.95},
    }


class TestPrimitivas:
    def test_sha256_file(self, projeto_tmp: Path):
        esperado = cc.sha256_bytes((projeto_tmp / "proofs" / "prova.md").read_bytes())
        assert cc.sha256_file(projeto_tmp / "proofs" / "prova.md") == esperado

    def test_json_canonico_deterministico(self):
        a = cc.json_canonico({"b": 1, "a": [1, 2]})
        b = cc.json_canonico({"a": [1, 2], "b": 1})
        assert a == b


class TestEmissao:
    def test_emissao_basica(self, projeto_tmp: Path):
        cert = cc.emitir_certificado(_spec_ok(), projeto_tmp)
        assert cert["schema"] == cc.SCHEMA_ID
        assert cert["project"] == "KIT-TESTE"
        assert cert["certificate_hash"]
        assert cert["avisos"] == []

    def test_hash_independente_de_timestamp(self, projeto_tmp: Path):
        c1 = cc.emitir_certificado(_spec_ok(), projeto_tmp)
        c2 = cc.emitir_certificado(_spec_ok(), projeto_tmp)
        assert c1["certificate_hash"] == c2["certificate_hash"]
        assert c1["niveis"] == c2["niveis"]

    def test_confianca_fora_da_ordem_gera_aviso(self, projeto_tmp: Path):
        spec = _spec_ok()
        spec["confidence"] = {"empirical": 0.9, "statistical": 0.8, "logical": 0.5, "formal": 0.3}
        cert = cc.emitir_certificado(spec, projeto_tmp)
        assert any("δ ≥ γ ≥ β ≥ ρ" in a for a in cert["avisos"])

    def test_artefato_ausente_gera_aviso(self, projeto_tmp: Path):
        spec = _spec_ok()
        spec["proof"]["artifacts"] = ["proofs/nao_existe.md"]
        cert = cc.emitir_certificado(spec, projeto_tmp)
        assert any("ausentes" in a for a in cert["avisos"])
        assert cert["niveis"]["1_prova"]["status"] == "parcial"


class TestVerificacao:
    def test_verificacao_passa(self, projeto_tmp: Path):
        cert = cc.emitir_certificado(_spec_ok(), projeto_tmp)
        rel = cc.verificar_certificado(cert, projeto_tmp)
        assert rel["ok"], rel["checks"]

    def test_tamper_prova_falha(self, projeto_tmp: Path):
        cert = cc.emitir_certificado(_spec_ok(), projeto_tmp)
        (projeto_tmp / "proofs" / "prova.md").write_text("# Prova alterada!\n", encoding="utf-8")
        rel = cc.verificar_certificado(cert, projeto_tmp)
        assert not rel["ok"]
        assert any(c["check"].startswith("nivel1_prova") and not c["ok"] for c in rel["checks"])

    def test_tamper_certificado_falha(self, projeto_tmp: Path):
        cert = cc.emitir_certificado(_spec_ok(), projeto_tmp)
        cert["niveis"]["2_verificacao"]["result"] = "fail"  # adulteração do registro
        rel = cc.verificar_certificado(cert, projeto_tmp)
        assert not rel["ok"]

    def test_artefato_deletado_falha(self, projeto_tmp: Path):
        cert = cc.emitir_certificado(_spec_ok(), projeto_tmp)
        (projeto_tmp / "results" / "saida.txt").unlink()
        rel = cc.verificar_certificado(cert, projeto_tmp)
        assert not rel["ok"]


class TestSimulador:
    def test_deterministico(self):
        a = sim.simular(semente=7, passes=2)
        b = sim.simular(semente=7, passes=2)
        assert a == b

    def test_ordem_final(self):
        linhas = sim.simular(semente=42, passes=6)
        finais = linhas[-1]
        assert finais["delta"] >= finais["gamma"] >= finais["beta"] >= finais["rho"]

    def test_resumo_consistente(self):
        linhas = sim.simular(semente=1, passes=3)
        r = sim.resumo(linhas)
        assert r["passes"] == 3
        assert 0.0 <= r["proporcao_violacoes"] <= 1.0
