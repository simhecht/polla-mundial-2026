"""
predictor.py
Motor de predicción Poisson para partidos del Mundial 2026.
Capas: ELO base → ajuste forma → ajuste táctico → distribución Poisson
"""
import sqlite3
import math
from itertools import product
import os

DB_PATH = "/tmp/mundial_2026.db"

# Promedio histórico de goles en mundiales (fase de grupos): ~2.5 goles/partido
WORLD_CUP_AVG_GOALS = 1.3  # por equipo por partido

# Mapeo de ventajas/desventajas tácticas
# (estilo_atacante, estilo_defensor) -> multiplicador de goles atacante
TACTICAL_EDGE = {
    ("high_press", "possession"): 1.08,   # presión alta vs posesión: riesgo
    ("high_press", "defensive"):  0.92,   # presión alta vs bloque bajo: difícil
    ("high_press", "counter"):    1.05,
    ("high_press", "high_press"): 1.0,
    ("high_press", "mixed"):      1.02,
    ("possession", "defensive"):  0.90,   # posesión vs bloque bajo: muy difícil
    ("possession", "counter"):    1.05,   # posesión vs contra: riesgo de contra
    ("possession", "high_press"): 1.05,
    ("possession", "possession"): 1.0,
    ("possession", "mixed"):      1.0,
    ("counter",    "possession"): 1.12,   # contra vs posesión: ideal
    ("counter",    "defensive"):  0.95,
    ("counter",    "high_press"): 0.98,
    ("counter",    "counter"):    1.0,
    ("counter",    "mixed"):      1.03,
    ("defensive",  "possession"): 0.85,
    ("defensive",  "defensive"):  0.90,
    ("defensive",  "counter"):    0.92,
    ("defensive",  "high_press"): 0.95,
    ("defensive",  "mixed"):      0.88,
    ("mixed",      "possession"): 0.98,
    ("mixed",      "defensive"):  0.95,
    ("mixed",      "counter"):    1.0,
    ("mixed",      "high_press"): 0.98,
    ("mixed",      "mixed"):      1.0,
}


def get_team(conn, name):
    cur = conn.cursor()
    cur.execute("SELECT * FROM teams WHERE name=? OR name_es=?", (name, name))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Equipo no encontrado: {name}")
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def elo_win_prob(elo_a, elo_b):
    """Probabilidad de que A gane según ELO (escala FIFA: 200 pts ≈ 76% win rate)."""
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def compute_lambdas(team_home, team_away):
    """
    Calcula los goles esperados (lambda) para cada equipo en el partido.

    Lambda = base_goals
             × attack_factor(equipo)
             × defense_factor(rival)
             × elo_factor
             × form_factor
             × tactical_factor
             × depth_factor
    """
    # Factor de ataque/defensa basado en ELO relativo (normalizado a 1500)
    avg_elo = 1600
    atk_home = (team_home["elo_rating"] / avg_elo) ** 0.6
    def_away = (avg_elo / team_away["elo_rating"]) ** 0.4
    atk_away = (team_away["elo_rating"] / avg_elo) ** 0.6
    def_home = (avg_elo / team_home["elo_rating"]) ** 0.4

    # Factor de forma (normalizado: 5.0 = neutro)
    form_home = team_home["form_score"] / 5.0
    form_away = team_away["form_score"] / 5.0

    # Factor de profundidad de plantilla (importa menos en grupos)
    depth_home = (team_home["squad_depth_score"] / 5.0) ** 0.2
    depth_away = (team_away["squad_depth_score"] / 5.0) ** 0.2

    # Factor táctico
    style_h = team_home.get("tactical_style", "mixed") or "mixed"
    style_a = team_away.get("tactical_style", "mixed") or "mixed"
    tact_home = TACTICAL_EDGE.get((style_h, style_a), 1.0)
    tact_away = TACTICAL_EDGE.get((style_a, style_h), 1.0)

    lambda_home = WORLD_CUP_AVG_GOALS * atk_home * def_away * form_home * depth_home * tact_home
    lambda_away = WORLD_CUP_AVG_GOALS * atk_away * def_home * form_away * depth_away * tact_away

    return lambda_home, lambda_away


def poisson_prob(lam, k):
    """P(X=k) para distribución Poisson con media lam."""
    return (math.exp(-lam) * lam**k) / math.factorial(k)


def score_matrix(lambda_home, lambda_away, max_goals=6):
    """Matriz de probabilidades para todos los marcadores posibles."""
    matrix = {}
    for gh, ga in product(range(max_goals + 1), repeat=2):
        matrix[(gh, ga)] = poisson_prob(lambda_home, gh) * poisson_prob(lambda_away, ga)
    return matrix


def predict_match(name_home, name_away, conn=None, verbose=True):
    """
    Predice el resultado de un partido.
    Retorna dict con marcador más probable, lambdas y probabilidades.
    """
    close_conn = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close_conn = True

    try:
        th = get_team(conn, name_home)
        ta = get_team(conn, name_away)
    except ValueError as e:
        if close_conn:
            conn.close()
        raise e

    lh, la = compute_lambdas(th, ta)
    matrix = score_matrix(lh, la)

    prob_home = sum(p for (gh, ga), p in matrix.items() if gh > ga)
    prob_draw = sum(p for (gh, ga), p in matrix.items() if gh == ga)
    prob_away = sum(p for (gh, ga), p in matrix.items() if gh < ga)

    # Marcador más probable
    best_score = max(matrix, key=matrix.get)

    # Top 5 marcadores
    top5 = sorted(matrix.items(), key=lambda x: -x[1])[:5]

    # Confianza basada en diferencia ELO
    elo_diff = abs(th["elo_rating"] - ta["elo_rating"])
    if elo_diff > 250:
        confidence = "alta"
    elif elo_diff > 100:
        confidence = "media"
    else:
        confidence = "baja"

    result = {
        "home": th["name_es"] or th["name"],
        "away": ta["name_es"] or ta["name"],
        "elo_home": th["elo_rating"],
        "elo_away": ta["elo_rating"],
        "lambda_home": round(lh, 3),
        "lambda_away": round(la, 3),
        "best_score": best_score,
        "prob_home_win": round(prob_home * 100, 1),
        "prob_draw":     round(prob_draw * 100, 1),
        "prob_away_win": round(prob_away * 100, 1),
        "top5_scores":   [(s, round(p * 100, 2)) for s, p in top5],
        "confidence":    confidence,
        "style_home": th.get("tactical_style", "?"),
        "style_away": ta.get("tactical_style", "?"),
    }

    if verbose:
        print(f"\n{'='*55}")
        print(f"  {result['home']} (ELO {result['elo_home']:.0f})  vs  {result['away']} (ELO {result['elo_away']:.0f})")
        print(f"  Estilo: {result['style_home']} vs {result['style_away']}")
        print(f"  λ home={result['lambda_home']} | λ away={result['lambda_away']}")
        print(f"  Marcador más probable: {best_score[0]}-{best_score[1]}")
        print(f"  Victoria local: {result['prob_home_win']}% | Empate: {result['prob_draw']}% | Victoria visitante: {result['prob_away_win']}%")
        print(f"  Top scores: {[(f'{s[0]}-{s[1]}', f'{p}%') for s,p in result['top5_scores']]}")
        print(f"  Confianza: {confidence}")

    if close_conn:
        conn.close()

    return result


def simulate_group(group_name, conn=None, verbose=True):
    """
    Simula todos los partidos de un grupo y devuelve la tabla de posiciones.
    """
    close_conn = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close_conn = True

    cur = conn.cursor()
    cur.execute("""
        SELECT team_home, team_away FROM recent_matches
        WHERE competition='GROUP_FIXTURE'
        AND team_home IN (SELECT name FROM teams WHERE group_name=?)
        ORDER BY date
    """, (group_name,))
    fixtures = cur.fetchall()

    # Tabla: {team: {pts, gf, ga, w, d, l}}
    teams_in_group = []
    cur.execute("SELECT name, name_es FROM teams WHERE group_name=? ORDER BY elo_rating DESC", (group_name,))
    for row in cur.fetchall():
        teams_in_group.append({"name": row[0], "name_es": row[1] or row[0],
                                "pts": 0, "gf": 0, "ga": 0, "w": 0, "d": 0, "l": 0})

    standings = {t["name"]: t for t in teams_in_group}

    results = []
    for home_name, away_name in fixtures:
        r = predict_match(home_name, away_name, conn=conn, verbose=False)
        gh, ga = r["best_score"]
        results.append({
            "home": r["home"], "away": r["away"],
            "score": f"{gh}-{ga}",
            "prob_h": r["prob_home_win"],
            "prob_d": r["prob_draw"],
            "prob_a": r["prob_away_win"],
        })
        # Actualizar tabla
        sh = standings[home_name]
        sa = standings[away_name]
        sh["gf"] += gh; sh["ga"] += ga
        sa["gf"] += ga; sa["ga"] += gh
        if gh > ga:
            sh["pts"] += 3; sh["w"] += 1; sa["l"] += 1
        elif gh == ga:
            sh["pts"] += 1; sh["d"] += 1
            sa["pts"] += 1; sa["d"] += 1
        else:
            sa["pts"] += 3; sa["w"] += 1; sh["l"] += 1

    # Ordenar: pts → diferencia de goles → goles a favor
    sorted_teams = sorted(standings.values(),
                          key=lambda t: (t["pts"], t["gf"]-t["ga"], t["gf"]),
                          reverse=True)

    if verbose:
        print(f"\n{'='*55}")
        print(f"  GRUPO {group_name} — PARTIDOS")
        print(f"{'='*55}")
        for r in results:
            print(f"  {r['home']:20s} {r['score']:5s} {r['away']:20s}  ({r['prob_h']}% / {r['prob_d']}% / {r['prob_a']}%)")
        print(f"\n  TABLA FINAL GRUPO {group_name}")
        print(f"  {'Equipo':<22} {'PJ':>2} {'G':>2} {'E':>2} {'P':>2} {'GF':>3} {'GC':>3} {'DG':>4} {'PTS':>4}")
        print(f"  {'-'*55}")
        for i, t in enumerate(sorted_teams):
            marker = "✅" if i < 2 else "  "
            print(f"{marker} {t['name_es']:<22} {3:>2} {t['w']:>2} {t['d']:>2} {t['l']:>2} {t['gf']:>3} {t['ga']:>3} {t['gf']-t['ga']:>4} {t['pts']:>4}")

    if close_conn:
        conn.close()

    return sorted_teams, results


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    for g in "ABCDEFGHIJKL":
        simulate_group(g, conn=conn, verbose=True)
    conn.close()
