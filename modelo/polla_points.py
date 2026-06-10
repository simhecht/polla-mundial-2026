"""
polla_points.py
===============
Módulo puro (solo stdlib) que implementa:
  - El reglamento de puntos de una polla mundialista (fase de grupos y knockout).
  - El optimizador de apuesta por valor esperado dado una matriz de probabilidades
    de marcador (formato Dixon-Coles).

Convenciones de tipos
---------------------
  Marcador : tuple[int, int]   — (goles_local, goles_visita)
  Advancer : str | None        — 'home' | 'away' | None (se deriva si el marcador
                                 no es empate)
  Matriz   : dict[tuple[int,int], float]  — probabilidades normalizadas

Autores: módulo generado para el proyecto Polla Mundial 2026.
"""

from __future__ import annotations
from typing import Optional


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _signo(gh: int, ga: int) -> int:
    """Devuelve 1 si local gana, 0 si empate, -1 si visita gana."""
    if gh > ga:
        return 1
    elif gh == ga:
        return 0
    else:
        return -1


def _derivar_advancer(gh: int, ga: int) -> Optional[str]:
    """
    Devuelve el lado que avanza implícito en un marcador de victoria.
    Para empates devuelve None (el advancer no está determinado por el marcador).
    """
    if gh > ga:
        return 'home'
    elif ga > gh:
        return 'away'
    return None


# ---------------------------------------------------------------------------
# Fase de grupos
# ---------------------------------------------------------------------------

def points_group(pred: tuple[int, int], actual: tuple[int, int]) -> int:
    """
    Calcula los puntos obtenidos por una predicción de partido de fase de grupos.

    Reglamento
    ----------
    - Resultado exacto (pred == actual)                                    : 6 pts
    - Ganador correcto, NO exacto:
        · Victoria con un gol coincidente (pred_h==actual_h o pred_a==actual_a): 4 pts
        · Empate no exacto                                                 : 3 pts
        · Victoria sin ningún gol coincidente                              : 3 pts
    - Ganador incorrecto:
        · Un gol coincide (pred_h==actual_h o pred_a==actual_a)            : 1 pt
        · Ningún gol coincide                                              : 0 pts

    Parámetros
    ----------
    pred   : (goles_local_predichos, goles_visita_predichos)
    actual : (goles_local_reales,    goles_visita_reales)

    Retorna
    -------
    int : puntos obtenidos (0–6)
    """
    ph, pa = pred
    ah, aa = actual

    exacto = (ph == ah and pa == aa)
    if exacto:
        return 6

    ganador_correcto = (_signo(ph, pa) == _signo(ah, aa))
    gol_coincide = (ph == ah) or (pa == aa)

    if ganador_correcto:
        # En empates no exactos nunca puede haber un gol coincidente sin ser
        # exacto (si ambos son empate y ph==ah entonces también pa==aa → exacto).
        if _signo(ph, pa) != 0 and gol_coincide:
            return 4
        else:
            return 3
    else:
        return 1 if gol_coincide else 0


# ---------------------------------------------------------------------------
# Eliminación directa (knockout)
# ---------------------------------------------------------------------------

def points_ko(
    pred_score: tuple[int, int],
    pred_advancer: Optional[str],
    actual_score: tuple[int, int],
    actual_advancer: Optional[str],
) -> int:
    """
    Calcula los puntos por una predicción de partido de eliminación directa.

    El marcador es el resultado a los 90 minutos. El advancer es quién avanza
    de ronda (puede diferir del resultado en 90' si hay empate seguido de
    prórroga/penales).

    Si el marcador NO es empate, el advancer se puede derivar automáticamente
    del marcador (se acepta None y se calcula).

    Nota sobre casos cruzados (pred victoria/actual empate o viceversa)
    -------------------------------------------------------------------
    El reglamento no contempla bonificación por advancer en estos casos:
    se aplica únicamente la lógica de goles coincidentes (1 pt) o ninguno (0 pts).
    Esto es una decisión de diseño documentada; si el reglamento cambia, solo
    hay que modificar los bloques 'cruzados' de esta función.

    Parámetros
    ----------
    pred_score     : marcador predicho a 90'
    pred_advancer  : 'home' | 'away' | None
    actual_score   : marcador real a 90'
    actual_advancer: 'home' | 'away' | None

    Retorna
    -------
    int : puntos obtenidos (0–9)
    """
    ph, pa = pred_score
    ah, aa = actual_score

    pred_es_empate   = (ph == pa)
    actual_es_empate = (ah == aa)

    # Derivar advancers implícitos en victorias
    if not pred_es_empate:
        pred_advancer = _derivar_advancer(ph, pa)
    if not actual_es_empate:
        actual_advancer = _derivar_advancer(ah, aa)

    # --- Ambos empate ---
    if pred_es_empate and actual_es_empate:
        exacto = (ph == ah)   # pa==aa se cumple trivialmente si ph==ah y empate
        advancer_ok = (pred_advancer == actual_advancer)
        if exacto and advancer_ok:
            return 9
        elif exacto and not advancer_ok:
            return 6
        elif not exacto and advancer_ok:
            return 6
        else:  # no exacto, no advancer
            return 3

    # --- Ambos victoria (ninguno es empate) ---
    if not pred_es_empate and not actual_es_empate:
        # Reutilizamos la lógica de grupos; el advancer se deriva del marcador
        # y ya se validó arriba que ganador correcto ↔ advancer correcto.
        return points_group(pred_score, actual_score)

    # --- Casos cruzados: pred victoria / actual empate, o viceversa ---
    # Sin bonificación por advancer (ver docstring).
    gol_coincide = (ph == ah) or (pa == aa)
    return 1 if gol_coincide else 0


# ---------------------------------------------------------------------------
# Valor esperado — fase de grupos
# ---------------------------------------------------------------------------

def expected_points_group(
    matrix: dict[tuple[int, int], float],
    pred: tuple[int, int],
) -> float:
    """
    Valor esperado de puntos para una predicción dada, usando reglas de grupos.

    E[puntos] = Σ_{actual} P(actual) × points_group(pred, actual)

    Parámetros
    ----------
    matrix : dict {(gh, ga): prob}  — probabilidades normalizadas del marcador
    pred   : marcador predicho

    Retorna
    -------
    float : valor esperado de puntos
    """
    ev = 0.0
    for actual, prob in matrix.items():
        ev += prob * points_group(pred, actual)
    return ev


def best_bet_group(
    matrix: dict[tuple[int, int], float],
) -> tuple[tuple[int, int], float]:
    """
    Marcador que maximiza el valor esperado de puntos en fase de grupos.

    Se evalúan todos los marcadores de la matriz como candidatos.

    Desempate
    ---------
    Si dos candidatos tienen el mismo EV, se prefiere el de mayor probabilidad
    en la matriz.

    Parámetros
    ----------
    matrix : dict {(gh, ga): prob}

    Retorna
    -------
    (mejor_marcador, exp_pts)
    """
    mejor_score = None
    mejor_ev    = -1.0
    mejor_prob  = -1.0

    for cand in matrix:
        ev   = expected_points_group(matrix, cand)
        prob = matrix[cand]
        if (ev > mejor_ev) or (ev == mejor_ev and prob > mejor_prob):
            mejor_ev    = ev
            mejor_score = cand
            mejor_prob  = prob

    return (mejor_score, mejor_ev)


# ---------------------------------------------------------------------------
# Valor esperado — eliminación directa
# ---------------------------------------------------------------------------

def expected_points_ko(
    matrix: dict[tuple[int, int], float],
    p_home_adv_draw: float,
    pred_score: tuple[int, int],
    pred_advancer: Optional[str],
) -> float:
    """
    Valor esperado de puntos para una predicción KO dada.

    Parámetros
    ----------
    matrix          : dict {(gh, ga): prob}  — probabilidades del marcador a 90'
    p_home_adv_draw : P(local avanza | empate en 90'), independiente del marcador exacto
    pred_score      : marcador predicho a 90'
    pred_advancer   : 'home' | 'away' | None (se deriva si pred no es empate)

    Retorna
    -------
    float : valor esperado de puntos
    """
    ph, pa = pred_score
    pred_es_empate = (ph == pa)

    # Derivar advancer predicho si es victoria
    if not pred_es_empate:
        pred_advancer = _derivar_advancer(ph, pa)

    # Probabilidad de que pred_advancer sea correcto dado empate real
    if pred_es_empate:
        if pred_advancer == 'home':
            p_adv_ok = p_home_adv_draw
        else:
            p_adv_ok = 1.0 - p_home_adv_draw
    else:
        p_adv_ok = None  # no aplica para empates reales cuando pred es victoria

    ev = 0.0

    for actual_score, prob in matrix.items():
        ah, aa = actual_score
        actual_es_empate = (ah == aa)

        if actual_es_empate:
            # Necesitamos ponderar por probabilidad del advancer real
            if pred_es_empate:
                exacto = (ph == ah)
                # Puntos si advancer correcto (p_adv_ok) y si incorrecto (1-p_adv_ok)
                pts_adv_ok  = 9 if exacto else 6
                pts_adv_nok = 6 if exacto else 3
                pts_esperados = pts_adv_ok * p_adv_ok + pts_adv_nok * (1.0 - p_adv_ok)
            else:
                # Caso cruzado: pred victoria, actual empate
                gol_coincide = (ph == ah) or (pa == aa)
                pts_esperados = 1.0 if gol_coincide else 0.0
        else:
            # Actual es victoria: advancer está determinado por el marcador
            actual_advancer = _derivar_advancer(ah, aa)
            pts_esperados = float(points_ko(pred_score, pred_advancer,
                                            actual_score, actual_advancer))

        ev += prob * pts_esperados

    return ev


def best_bet_ko(
    matrix: dict[tuple[int, int], float],
    p_home_adv_draw: float,
) -> tuple[tuple[int, int], str, float]:
    """
    Marcador y advancer que maximizan el valor esperado de puntos en knockout.

    Para candidatos empate, el advancer óptimo es 'home' si p_home_adv_draw >= 0.5,
    de lo contrario 'away' (el advancer mayoritario domina siempre al contrario,
    por simetría de la función de puntos KO).

    Para candidatos victoria, el advancer es el ganador del marcador.

    Desempate
    ---------
    Mismo criterio que best_bet_group: a igual EV, mayor probabilidad en la matriz.

    Parámetros
    ----------
    matrix          : dict {(gh, ga): prob}
    p_home_adv_draw : P(local avanza | empate en 90')

    Retorna
    -------
    (mejor_marcador, advancer, exp_pts)
    """
    mejor_score    = None
    mejor_advancer = None
    mejor_ev       = -1.0
    mejor_prob     = -1.0

    for cand in matrix:
        gh, ga = cand
        es_empate = (gh == ga)

        if es_empate:
            advancer = 'home' if p_home_adv_draw >= 0.5 else 'away'
        else:
            advancer = _derivar_advancer(gh, ga)

        ev   = expected_points_ko(matrix, p_home_adv_draw, cand, advancer)
        prob = matrix[cand]

        if (ev > mejor_ev) or (ev == mejor_ev and prob > mejor_prob):
            mejor_ev       = ev
            mejor_score    = cand
            mejor_advancer = advancer
            mejor_prob     = prob

    return (mejor_score, mejor_advancer, mejor_ev)
