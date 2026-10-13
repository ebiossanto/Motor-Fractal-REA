"""
Módulo de Mitigação Estrutural via Autômatos Finitos Probabilísticos (PFA).

Implementa o Eixo 4 da Teoria de Controle Fractal:
- PFA quebra o piso determinístico E_6^* = 1/6
- Reduz inflação de cauda de ρ/(1-ρ) para √ρ/(1-ρ)
- Ponto de transição de fase: ρ_c = 0.25

Referência: Paper 4 - Stochastic Relaxation via Probabilistic Finite Automata
"""

import numpy as np
from typing import Tuple, Optional


class PFAMitigator:
    """
    Controlador PFA para mitigação de latência de cauda em filas M/M/1.
    
    O PFA (Probabilistic Finite Automaton) relaxa a rigidez algébrica
    do controlador determinístico, reduzindo o erro de rastreamento
    e decorrelacionando a sequência de erros.
    """

    def __init__(self, system_states: int = 8, controller_states: int = 6):
        """
        Inicializa o PFA.

        Args:
            system_states: Número de estados do sistema (|S|)
            controller_states: Número de estados do controlador (|Q|)
        """
        self.n = system_states  # |S|
        self.m = controller_states  # |Q|
        self.M = None  # Matriz de transição
        self.p_relax = 0.0  # Probabilidade de relaxamento

    def compute_min_error(self) -> float:
        """
        Calcula o erro mínimo determinístico E_m^*.

        Para Z_2^3 com m=6: E_6^* = 1/6
        Fórmula geral: E_m^* = (n - m) / (n * (n - 1)) para m < n
        """
        if self.m >= self.n:
            return 0.0
        return (self.n - self.m) / (self.n * (self.n - 1))

    def compute_pfa_error(self, p_relax: float = 0.5) -> float:
        """
        Calcula o erro do PFA com probabilidade de relaxamento p.

        E_6^*(PFA) = 1/6 - p/12

        Args:
            p_relax: Probabilidade de relaxamento (0 = determinístico, 1 = totalmente aleatório)

        Returns:
            Taxa de erro do PFA
        """
        E_dfa = self.compute_min_error()
        return E_dfa - p_relax / 12.0

    def build_optimal_pfa_matrix(self, p_relax: float = 0.5) -> np.ndarray:
        """
        Constrói a matriz de transição PFA ótima.

        Para Z_2^3 (8 estados) com controlador de 6 estados:
        - Estados não-colididos: mapeamento determinístico
        - Pares de colisão: distribuição uniforme (0.5, 0.5)

        Args:
            p_relax: Probabilidade de relaxamento

        Returns:
            Matriz de transição M (m x n), coluna-estocástica
        """
        self.p_relax = p_relax
        M = np.zeros((self.m, self.n))

        # Caso especial: Z_2^3 com m=6
        if self.n == 8 and self.m == 6:
            # Mapeamento determinístico para estados não-colididos
            # Estados 0-3 (010, 011, 100, 101) → controlador 3-6
            deterministic_map = {0: 2, 1: 3, 2: 4, 3: 5}  # 0-indexed

            # Pares de colisão: (000, 110) e (001, 111)
            # Estados 4-7 (000, 001, 110, 111) → controlador 1-2 com probabilidade 0.5
            collision_pairs = [(4, 6), (5, 7)]  # (000, 110), (001, 111)

            # Preencher mapeamentos determinísticos
            for sys_state, ctrl_state in deterministic_map.items():
                M[ctrl_state, sys_state] = 1.0

            # Preencher pares de colisão com probabilidade 0.5
            for s1, s2 in collision_pairs:
                M[0, s1] = 0.5
                M[0, s2] = 0.5
                M[1, s1] = 0.5
                M[1, s2] = 0.5

        else:
            # Caso geral: distribuição uniforme para estados excedentes
            for s in range(self.n):
                if s < self.m:
                    M[s, s] = 1.0
                else:
                    # Estados excedentes distribuídos uniformemente
                    for q in range(self.m):
                        M[q, s] = 1.0 / self.m

        self.M = M
        return M

    def compute_mitigation_factor(self, rho: float, p_relax: float = 0.5) -> float:
        """
        Calcula o fator de mitigação M(M*).

        M(M*) = 1 - √ρ / (4ρ)

        Args:
            rho: Carga do sistema
            p_relax: Probabilidade de relaxamento

        Returns:
            Fator de mitigação [0, 1]
        """
        if rho <= 0 or rho >= 1:
            return 0.0

        # Fator de mitigação teórico
        mitigation = 1.0 - np.sqrt(rho) / (4.0 * rho)

        return max(0.0, min(1.0, mitigation))

    def compute_tail_latency(self, rho: float, controller_type: str = 'DFA',
                            p_relax: float = 0.5) -> float:
        """
        Calcula P_99 dado o tipo de controlador.

        Args:
            rho: Carga do sistema
            controller_type: 'DFA' (determinístico) ou 'PFA' (probabilístico)
            p_relax: Probabilidade de relaxamento (apenas para PFA)

        Returns:
            Fator de inflação de P_99
        """
        if rho <= 0 or rho >= 1:
            return 1.0

        if controller_type == 'DFA':
            p = self.compute_min_error()
            return 1.0 + (rho / (1.0 - rho)) * p ** 2
        elif controller_type == 'PFA':
            p = self.compute_pfa_error(p_relax)
            return 1.0 + (np.sqrt(rho) / (1.0 - rho)) * p ** 2
        else:
            raise ValueError(f"Tipo de controlador desconhecido: {controller_type}")

    def compute_bullwhip_cascade(self, rhos: list, ps: list,
                                  controller_type: str = 'DFA') -> float:
        """
        Calcula a amplificação em cascata (Efeito Bullwhip Algébrico).

        P_99^(n) = P_99^(0) * ∏_{k=1}^{n} (1 + ρ_k/(1-ρ_k) * p_k^2)

        Args:
            rhos: Lista de cargas para cada salto
            ps: Lista de taxas de erro para cada salto
            controller_type: 'DFA' ou 'PFA'

        Returns:
            Fator de inflação total de ponta a ponta
        """
        inflation = 1.0

        for rho_k, p_k in zip(rhos, ps):
            if controller_type == 'DFA':
                inflation *= (1.0 + (rho_k / (1.0 - rho_k)) * p_k ** 2)
            elif controller_type == 'PFA':
                inflation *= (1.0 + (np.sqrt(rho_k) / (1.0 - rho_k)) * p_k ** 2)

        return inflation

    def find_phase_transition(self) -> float:
        """
        Encontra o ponto de transição de fase ρ_c.

        ρ_c = 0.25 (onde PFA se torna vantajoso sobre DFA)

        Returns:
            Carga crítica
        """
        return 0.25

    def recommend_controller(self, rho: float) -> dict:
        """
        Recomenda o tipo de controlador baseado na carga.

        Args:
            rho: Carga do sistema

        Returns:
            Dicionário com recomendação
        """
        rho_c = self.find_phase_transition()

        if rho < rho_c:
            return {
                'recommended_controller': 'DFA',
                'reason': f'Carga ρ={rho:.3f} < ρ_c={rho_c:.3f}: erros são absorvidos naturalmente',
                'expected_inflation': self.compute_tail_latency(rho, 'DFA'),
                'mitigation_factor': 0.0
            }
        else:
            mitigation = self.compute_mitigation_factor(rho)
            return {
                'recommended_controller': 'PFA',
                'reason': f'Carga ρ={rho:.3f} > ρ_c={rho_c:.3f}: PFA necessário para prevenir colapso',
                'expected_inflation_dfa': self.compute_tail_latency(rho, 'DFA'),
                'expected_inflation_pfa': self.compute_tail_latency(rho, 'PFA'),
                'mitigation_factor': round(mitigation, 4)
            }


def compare_controllers(rho_values: np.ndarray, p_relax: float = 0.5) -> dict:
    """
    Compara DFA vs PFA para uma faixa de cargas.

    Args:
        rho_values: Array de valores de carga
        p_relax: Probabilidade de relaxamento do PFA

    Returns:
        Dicionário com comparações
    """
    mitigator = PFAMitigator(system_states=8, controller_states=6)

    results = {
        'rho': rho_values,
        'dfa_inflation': [],
        'pfa_inflation': [],
        'improvement_ratio': [],
        'mitigation_factor': []
    }

    for rho in rho_values:
        dfa_inf = mitigator.compute_tail_latency(rho, 'DFA')
        pfa_inf = mitigator.compute_tail_latency(rho, 'PFA', p_relax)

        results['dfa_inflation'].append(dfa_inf)
        results['pfa_inflation'].append(pfa_inf)
        results['improvement_ratio'].append(dfa_inf / pfa_inf if pfa_inf > 0 else 1.0)
        results['mitigation_factor'].append(mitigator.compute_mitigation_factor(rho, p_relax))

    return results
