"""
test_polla_points.py
====================
Tests unitarios para polla_points.py.
Ejecutar con:  python test_polla_points.py

Los casos de puntos_group y points_ko son los mínimos obligatorios del
enunciado, más los tests de valor esperado con una matriz pequeña construida
a mano.
"""

import unittest
from polla_points import (
    points_group,
    points_ko,
    expected_points_group,
    best_bet_group,
    expected_points_ko,
    best_bet_ko,
)


class TestPointsGroup(unittest.TestCase):
    """Reglamento de puntos para partidos de fase de grupos."""

    # --- Resultado exacto: 6 pts ---
    def test_exacto_victoria(self):
        self.assertEqual(points_group((2, 1), (2, 1)), 6)

    def test_exacto_empate(self):
        self.assertEqual(points_group((1, 1), (1, 1)), 6)

    # --- Ganador correcto, un gol coincide: 4 pts ---
    def test_victoria_gol_local_coincide(self):
        # pred 2-1, actual 2-0: ganador=local, gol local coincide (2==2)
        self.assertEqual(points_group((2, 1), (2, 0)), 4)

    def test_victoria_gol_visita_coincide_pred(self):
        # pred 2-1, actual 3-1: ganador=local, gol visita coincide (1==1)
        self.assertEqual(points_group((2, 1), (3, 1)), 4)

    def test_victoria_visita_gol_visita_coincide(self):
        # pred 0-2, actual 1-2: ganador=visita, gol visita coincide (2==2)
        self.assertEqual(points_group((0, 2), (1, 2)), 4)

    # --- Ganador correcto, sin gol coincidente o empate no exacto: 3 pts ---
    def test_victoria_sin_gol_coincidente(self):
        # pred 2-1, actual 1-0: ganador=local, ningún gol coincide
        self.assertEqual(points_group((2, 1), (1, 0)), 3)

    def test_empate_no_exacto(self):
        # pred 1-1, actual 2-2: empate, no exacto
        self.assertEqual(points_group((1, 1), (2, 2)), 3)

    def test_empate_no_exacto_00(self):
        # pred 1-1, actual 0-0: empate, no exacto
        self.assertEqual(points_group((1, 1), (0, 0)), 3)

    # --- Ganador incorrecto, un gol coincide: 1 pt ---
    def test_incorrecto_gol_local_coincide(self):
        # pred 2-1 (victoria local), actual 2-2 (empate): gol local coincide
        self.assertEqual(points_group((2, 1), (2, 2)), 1)

    def test_incorrecto_gol_visita_coincide(self):
        # pred 2-1 (victoria local), actual 0-1 (victoria visita): gol visita coincide
        self.assertEqual(points_group((2, 1), (0, 1)), 1)

    def test_incorrecto_empate_pred_victoria_actual_gol_coincide(self):
        # pred 1-1 (empate), actual 1-0 (victoria local): gol local coincide
        self.assertEqual(points_group((1, 1), (1, 0)), 1)

    # --- Ganador incorrecto, ningún gol coincide: 0 pts ---
    def test_incorrecto_sin_goles(self):
        # pred 2-1 (local), actual 0-3 (visita): ninguno coincide
        self.assertEqual(points_group((2, 1), (0, 3)), 0)

    def test_incorrecto_empate_pred_victoria_actual_sin_gol(self):
        # pred 1-1 (empate), actual 0-2 (visita): ninguno coincide
        self.assertEqual(points_group((1, 1), (0, 2)), 0)


class TestPointsKO(unittest.TestCase):
    """Reglamento de puntos para partidos de eliminación directa."""

    # --- Ambos empate ---
    def test_empate_exacto_advancer_ok(self):
        self.assertEqual(points_ko((2, 2), 'home', (2, 2), 'home'), 9)

    def test_empate_exacto_advancer_nok(self):
        self.assertEqual(points_ko((2, 2), 'home', (2, 2), 'away'), 6)

    def test_empate_no_exacto_advancer_ok(self):
        self.assertEqual(points_ko((1, 1), 'home', (2, 2), 'home'), 6)

    def test_empate_no_exacto_advancer_nok(self):
        self.assertEqual(points_ko((1, 1), 'away', (2, 2), 'home'), 3)

    # --- Ambos victoria (reglas de grupos) ---
    def test_victoria_exacta(self):
        # pred 2-1, actual 2-1: exacto → 6 pts
        self.assertEqual(points_ko((2, 1), None, (2, 1), None), 6)

    def test_victoria_gol_coincide(self):
        # pred 2-1, actual 2-0: gol local coincide → 4 pts
        self.assertEqual(points_ko((2, 1), None, (2, 0), None), 4)

    # --- Casos cruzados ---
    def test_cruzado_pred_victoria_actual_empate_gol_coincide(self):
        # pred 2-1 (victoria local), actual 1-1 (empate): gol visita coincide (1==1) → 1
        self.assertEqual(points_ko((2, 1), None, (1, 1), 'home'), 1)

    def test_cruzado_pred_victoria_actual_empate_sin_gol(self):
        # pred 3-1, actual 0-0: ningún gol coincide → 0
        self.assertEqual(points_ko((3, 1), None, (0, 0), 'home'), 0)

    def test_cruzado_pred_empate_actual_victoria_gol_coincide(self):
        # pred 1-1 (empate, adv home), actual 1-0 (victoria local): gol local coincide → 1
        # Sin bonificación por advancer en cruce
        self.assertEqual(points_ko((1, 1), 'home', (1, 0), 'home'), 1)


class TestEV(unittest.TestCase):
    """
    Tests de valor esperado con la siguiente matriz pequeña:

        (1,0) : 0.40   victoria local
        (1,1) : 0.35   empate
        (0,1) : 0.25   victoria visita

    Cálculos a mano para expected_points_group con pred=(1,0):
        actual (1,0): exacto           → 6 pts  | 0.40 × 6 = 2.40
        actual (1,1): incorrecto, gol  → 1 pt   | 0.35 × 1 = 0.35
        actual (0,1): incorrecto       → 0 pts  | 0.25 × 0 = 0.00
        EV = 2.75

    Con pred=(1,1):
        actual (1,0): incorrecto, gol  → 1 pt   | 0.40 × 1 = 0.40
        actual (1,1): exacto           → 6 pts  | 0.35 × 6 = 2.10
        actual (0,1): incorrecto, gol  → 1 pt   | 0.25 × 1 = 0.25
        EV = 2.75

    Con pred=(0,1):
        actual (1,0): incorrecto       → 0 pts  | 0.40 × 0 = 0.00
        actual (1,1): incorrecto, gol  → 1 pt   | 0.35 × 1 = 0.35
        actual (0,1): exacto           → 6 pts  | 0.25 × 6 = 1.50
        EV = 1.85

    best_bet_group → (1,0) o (1,1) (empatan EV=2.75); desempate por prob →
    (1,0) con prob 0.40 > 0.35.

    best_bet_ko con p_home_adv_draw=0.7:
        Candidato (1,0) victoria:
            actual (1,0): pts_ko = points_group((1,0),(1,0)) = 6  | 0.40 × 6 = 2.40
            actual (1,1) empate (adv_ok=p_home? no, pred es victoria): cruzado, gol local=1==1 → 1 | 0.35 × 1 = 0.35
            actual (0,1): incorrecto → 0 | 0.25 × 0 = 0.00
            EV = 2.75

        Candidato (1,1) empate, adv='home' (p>=0.5):
            actual (1,0) victoria (adv derivado='home'):
                points_ko((1,1),'home',(1,0),'home') = 1 (cruzado, gol local coincide) | 0.40 × 1 = 0.40
            actual (1,1) empate:
                exacto=True, p_adv_ok=0.7
                pts = 9 × 0.7 + 6 × 0.3 = 6.30 + 1.80 = 8.10 | 0.35 × 8.10 = 2.835
            actual (0,1) victoria (adv='away'):
                points_ko((1,1),'home',(0,1),'away') = cruzado, gol visita? pred_a=1,actual_a=1 → 1 | 0.25 × 1 = 0.25
            EV = 0.40 + 2.835 + 0.25 = 3.485

        Candidato (0,1) victoria:
            actual (1,0): incorrecto → 0 | 0.40 × 0 = 0.00
            actual (1,1) empate: cruzado, gol visita=1==1 → 1 | 0.35 × 1 = 0.35
            actual (0,1): points_group((0,1),(0,1)) = 6 | 0.25 × 6 = 1.50
            EV = 1.85

        → best_bet_ko = ((1,1), 'home', 3.485)
    """

    MATRIZ = {(1, 0): 0.40, (1, 1): 0.35, (0, 1): 0.25}
    TOL = 1e-9  # tolerancia para comparaciones flotantes

    def test_ev_group_pred_10(self):
        ev = expected_points_group(self.MATRIZ, (1, 0))
        self.assertAlmostEqual(ev, 2.75, places=9)

    def test_ev_group_pred_11(self):
        ev = expected_points_group(self.MATRIZ, (1, 1))
        self.assertAlmostEqual(ev, 2.75, places=9)

    def test_ev_group_pred_01(self):
        ev = expected_points_group(self.MATRIZ, (0, 1))
        self.assertAlmostEqual(ev, 1.85, places=9)

    def test_best_bet_group_argmax(self):
        score, ev = best_bet_group(self.MATRIZ)
        # EV máximo es 2.75; desempate por prob → (1,0) con prob 0.40
        self.assertEqual(score, (1, 0))
        self.assertAlmostEqual(ev, 2.75, places=9)

    def test_best_bet_ko_argmax_y_advancer(self):
        score, advancer, ev = best_bet_ko(self.MATRIZ, p_home_adv_draw=0.7)
        # Mayor EV es el empate (1,1) con advancer 'home'
        self.assertEqual(score, (1, 1))
        self.assertEqual(advancer, 'home')
        self.assertAlmostEqual(ev, 3.485, places=9)

    def test_best_bet_ko_advancer_home_cuando_p_gte_05(self):
        # Con p=0.7 >= 0.5 y cualquier matriz con un empate, advancer debe ser 'home'
        matriz_empate = {(0, 0): 1.0}
        _, advancer, _ = best_bet_ko(matriz_empate, p_home_adv_draw=0.7)
        self.assertEqual(advancer, 'home')

    def test_best_bet_ko_advancer_away_cuando_p_lt_05(self):
        # Con p=0.3 < 0.5, advancer debe ser 'away'
        matriz_empate = {(0, 0): 1.0}
        _, advancer, _ = best_bet_ko(matriz_empate, p_home_adv_draw=0.3)
        self.assertEqual(advancer, 'away')


if __name__ == '__main__':
    unittest.main(verbosity=2)
