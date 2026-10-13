"""
Meta-Verificação Independente — Nível 3 da Cadeia Ten-Proofs.

Verifica independentemente os resultados da validação estatística:
1. Reprodutibilidade (mesma semente = mesmo resultado)
2. Consistência interna (Estatísticas batem com dados brutos)
3. Robustez (intervalos de confiança não degenerados)

Executar:
    python -m pytest formal-certification/tests/test_meta_verification.py -v
"""

import json
import sys
from pathlib import Path

import pytest

# Caminhos relativos à raiz do workspace
WORKSPACE = Path(__file__).resolve().parent.parent.parent
SCRIPTS = WORKSPACE / "scripts"

sys.path.insert(0, str(SCRIPTS))

from hurst_calculator import compute_hurst_rs, compute_dfa, compute_permutation_entropy
from pfa_mitigation import PFAMitigator


def _load_report() -> dict:
    report_path = SCRIPTS / "validation_report.json"
    if not report_path.is_file():
        pytest.skip("validation_report.json não encontrado — execute validacao_estatistica.py primeiro")
    return json.loads(report_path.read_text(encoding="utf-8"))


class TestReproducibility:
    """Nível 3.1: Reprodutibilidade com semente fixa."""

    def test_hurst_deterministico_com_semente(self):
        """Hurst deve ser determinístico com mesma entrada."""
        import numpy as np
        np.random.seed(42)
        series1 = np.random.exponential(30, 300)
        np.random.seed(42)
        series2 = np.random.exponential(30, 300)

        H1 = compute_hurst_rs(series1)
        H2 = compute_hurst_rs(series2)

        assert H1 == H2, f"Hurst não reproduzível: {H1} != {H2}"

    def test_certificado_deterministico(self):
        """Certificate_hash não deve depender de timestamp."""
        sys.path.insert(0, str(WORKSPACE / "formal-certification" / "experiments"))
        import certifier_core as cc

        spec = json.loads(
            (WORKSPACE / "formal-certification" / "experiments" / "spec_certificado.json").read_text(
                encoding="utf-8-sig"
            )
        )

        cert1 = cc.emitir_certificado(spec, WORKSPACE / "formal-certification")
        cert2 = cc.emitir_certificado(spec, WORKSPACE / "formal-certification")

        assert cert1["certificate_hash"] == cert2["certificate_hash"], \
            "Certificado não é determinístico"


class TestConsistency:
    """Nível 3.2: Consistência interna dos resultados."""

    def test_intervalos_confianca_validos(self):
        """IC deve ter limite inferior < média < limite superior."""
        report = _load_report()
        stats = report.get("statistics", {})

        for key, s in stats.items():
            if "ci_low" in s and "ci_high" in s and "mean" in s:
                assert s["ci_low"] <= s["mean"] <= s["ci_high"], \
                    f"IC inválido para {key}: [{s['ci_low']}, {s['ci_high']}] não contém {s['mean']}"

    def test_contagem_iteracoes(self):
        """Contagem de iterações válidas deve ser <= total."""
        report = _load_report()
        total = report.get("num_iterations", 0)
        stats = report.get("statistics", {})

        for key, s in stats.items():
            count = s.get("count", 0)
            assert 0 <= count <= total, f"Contagem inválida para {key}: {count} > {total}"


class TestRobustness:
    """Nível 3.3: Robustez estatística."""

    def test_hurst_dentro_intervalo_unitario(self):
        """Hurst deve estar em [0, 1]."""
        report = _load_report()
        stats = report.get("statistics", {})

        if "hurst_values" in stats:
            H_mean = stats["hurst_values"]["mean"]
            H_min = stats["hurst_values"]["min"]
            H_max = stats["hurst_values"]["max"]

            assert 0.0 <= H_min <= 1.0, f"Hurst mínimo fora do intervalo: {H_min}"
            assert 0.0 <= H_max <= 1.0, f"Hurst máximo fora do intervalo: {H_max}"
            assert 0.0 <= H_mean <= 1.0, f"Hurst médio fora do intervalo: {H_mean}"

    def test_inflacao_positiva(self):
        """Fatores de inflação devem ser >= 1.0."""
        report = _load_report()
        stats = report.get("statistics", {})

        for key in ["dfa_inflation", "pfa_inflation"]:
            if key in stats:
                assert stats[key]["min"] >= 1.0, \
                    f"{key} mínimo < 1.0: {stats[key]['min']}"

    def test_entropia_permutacao_valida(self):
        """Entropia de permutação normalizada deve estar em [0, 1]."""
        report = _load_report()
        stats = report.get("statistics", {})

        if "permutation_entropy" in stats:
            s = stats["permutation_entropy"]
            assert 0.0 <= s["min"] <= 1.0, f"Entropia mínima inválida: {s['min']}"
            assert 0.0 <= s["max"] <= 1.0, f"Entropia máxima inválida: {s['max']}"


class TestPFAMitigation:
    """Nível 3.4: Validação da mitigação PFA."""

    def test_pfa_sempre_melhor_que_dfa_em_alta_carga(self):
        """PFA deve ter inflação menor que DFA para ρ > ρ_c."""
        mitigator = PFAMitigator(system_states=8, controller_states=6)

        for rho in [0.5, 0.7, 0.8, 0.9, 0.95, 0.99]:
            dfa_inf = mitigator.compute_tail_latency(rho, "DFA")
            pfa_inf = mitigator.compute_tail_latency(rho, "PFA")
            assert pfa_inf <= dfa_inf, \
                f"PFA não é melhor que DFA em ρ={rho}: {pfa_inf} > {dfa_inf}"

    def test_ponto_transicao_fase(self):
        """Ponto de transição de fase deve ser 0.25."""
        mitigator = PFAMitigator()
        assert mitigator.find_phase_transition() == 0.25


class TestEspectroConfianca:
    """Nível 3.5: Hipótese de ordem δ ≥ γ ≥ β ≥ ρ."""

    def test_espectro_respeitado_no_certificado(self):
        """Espectro de confiança do certificado deve respeitar a ordem."""
        cert_path = WORKSPACE / "formal-certification" / "certificates" / "certificate.json"
        if not cert_path.is_file():
            pytest.skip("certificate.json não encontrado")

        cert = json.loads(cert_path.read_text(encoding="utf-8-sig"))
        conf = cert.get("confidence", {})

        rho = conf.get("empirical", 0.0)
        beta = conf.get("statistical", 0.0)
        gamma = conf.get("logical", 0.0)
        delta = conf.get("formal", 0.0)

        assert delta >= gamma >= beta >= rho, \
            f"Espectro violado: ρ={rho}, β={beta}, γ={gamma}, δ={delta}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
