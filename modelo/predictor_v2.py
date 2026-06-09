"""
predictor_v2.py
Motor de predicción Poisson para partidos del Mundial 2026 — versión 2.

Mejoras sobre predictor.py:
  1. Corrección Dixon-Coles: ajuste de correlación para marcadores bajos (0-0, 1-0, 0-1).
  2. Simulación Monte Carlo: 50,000 iteraciones para distribuciones de clasificación.
  3. Factor de altitud por sede: multiplicador de lambda según metros sobre el nivel del mar.
  4. Función group_report(): tabla detallada con % clasificación e intervalos de confianza.
"""

import sqlite3
import math
import sys
import os
from itertools import product
import numpy as np

# ---------------------------------------------------------------------------
# Configuración global
# ---------------------------------------------------------------------------

DB_PATH = "/tmp/mundial_2026.db"

# Promedio histórico de goles en mundiales (fase de grupos) por equipo por partido
WORLD_CUP_AVG_GOALS = 1.3

# Número de simulaciones Monte Carlo
N_SIMULATIONS = 50_000

# Parámetro rho para corrección Dixon-Coles
# Valor empírico estándar para fútbol internacional: -0.13
DIXON_COLES_RHO = -0.13

# ---------------------------------------------------------------------------
# Factor de altitud por sede
# ---------------------------------------------------------------------------
# Altitudes aproximadas de las sedes del Mundial 2026.
# En altitud elevada el aire es menos denso: el balón viaja más rápido,
# los pulmones se fatigan antes y hay más espacio → más goles.
VENUE_ALTITUDE = {
    # México
    "Ciudad de Mexico":  2240,
    "Guadalajara":       1540,
    "Monterrey":          540,
    # Estados Unidos (nivel del mar o casi)
    "Atlanta":             313,
    "Dallas":              200,
    "Houston":              15,
    "Kansas City":         266,
    "Los Angeles":          71,
    "Miami":                 2,
    "Philadelphia":         12,
    "Boston":               9,
    "Seattle":              56,
    "San Francisco":        16,
    # Canadá
    "Vancouver":             2,
    "Toronto":             76,
    # Nueva York / Nueva Jersey
    "New York":             10,
}

def altitude_multiplier(altitude_m):
    """
    Multiplica lambda según altitud.
    < 500 m  → 0% extra
    500-999  → +2%
    1000-1799 → +6%
    >= 1800  → +12%
    """
    if altitude_m >= 1800:
        return 1.12
    elif altitude_m >= 1000:
        return 1.06
    elif altitude_m >= 500:
        return 1.02
    else:
        return 1.00


# Mapa partido → sede (basado en el fixture oficial del Mundial 2026)
# Formato: (team_home, team_away) → nombre de sede
MATCH_VENUES = {
    # Grupo A — Sede México
    ("Mexico",      "South Africa"): "Ciudad de Mexico",
    ("South Korea", "Czechia"):      "Guadalajara",
    ("Czechia",     "South Africa"): "Guadalajara",
    ("Mexico",      "South Korea"):  "Ciudad de Mexico",
    ("Czechia",     "Mexico"):       "Ciudad de Mexico",
    ("South Africa","South Korea"):  "Guadalajara",
    # Grupo B — Canadá
    ("Canada",      "Bosnia"):       "Toronto",
    ("Qatar",       "Switzerland"):  "Vancouver",
    ("Switzerland", "Bosnia"):       "Vancouver",
    ("Canada",      "Qatar"):        "Toronto",
    ("Switzerland", "Canada"):       "Toronto",
    ("Bosnia",      "Qatar"):        "Toronto",
    # Grupo C — USA Este/Sur
    ("Brazil",      "Morocco"):      "Philadelphia",
    ("Haiti",       "Scotland"):     "Atlanta",
    ("Scotland",    "Morocco"):      "Atlanta",
    ("Brazil",      "Haiti"):        "Miami",
    ("Scotland",    "Brazil"):       "Miami",
    ("Morocco",     "Haiti"):        "Philadelphia",
    # Grupo D — USA Centro/Este
    ("USA",         "Paraguay"):     "Dallas",
    ("Australia",   "Turkey"):       "Houston",
    ("Turkey",      "Paraguay"):     "Houston",
    ("USA",         "Australia"):    "Kansas City",
    ("Turkey",      "USA"):          "Dallas",
    ("Paraguay",    "Australia"):    "Kansas City",
    # Grupo E — USA Centro
    ("Germany",     "Curacao"):      "Dallas",
    ("Ivory Coast", "Ecuador"):      "Atlanta",
    ("Germany",     "Ivory Coast"):  "Kansas City",
    ("Ecuador",     "Curacao"):      "Houston",
    ("Ecuador",     "Germany"):      "Dallas",
    ("Curacao",     "Ivory Coast"):  "Miami",
    # Grupo F — USA Oeste
    ("Netherlands", "Japan"):        "Los Angeles",
    ("Sweden",      "Tunisia"):      "San Francisco",
    ("Netherlands", "Sweden"):       "Seattle",
    ("Tunisia",     "Japan"):        "Los Angeles",
    ("Japan",       "Sweden"):       "San Francisco",
    ("Tunisia",     "Netherlands"):  "Los Angeles",
    # Grupo G — USA Central
    ("Belgium",     "Egypt"):        "Miami",
    ("Iran",        "New Zealand"):  "Kansas City",
    ("Belgium",     "Iran"):         "Kansas City",
    ("New Zealand", "Egypt"):        "Houston",
    ("Egypt",       "Iran"):         "Houston",
    ("New Zealand", "Belgium"):      "Atlanta",
    # Grupo H — USA Este
    ("Spain",       "Cabo Verde"):   "Miami",
    ("Saudi Arabia","Uruguay"):      "Philadelphia",
    ("Spain",       "Saudi Arabia"): "Boston",
    ("Uruguay",     "Cabo Verde"):   "New York",
    ("Cabo Verde",  "Saudi Arabia"): "Boston",
    ("Uruguay",     "Spain"):        "Philadelphia",
    # Grupo I — USA Noreste
    ("France",      "Senegal"):      "New York",
    ("Iraq",        "Norway"):       "Boston",
    ("France",      "Iraq"):         "New York",
    ("Norway",      "Senegal"):      "Philadelphia",
    ("Norway",      "France"):       "Boston",
    ("Senegal",     "Iraq"):         "Philadelphia",
    # Grupo J — USA Central y Este
    ("Argentina",   "Algeria"):      "Dallas",
    ("Austria",     "Jordan"):       "Atlanta",
    ("Argentina",   "Austria"):      "Dallas",
    ("Jordan",      "Algeria"):      "Houston",
    ("Algeria",     "Austria"):      "Atlanta",
    ("Jordan",      "Argentina"):    "Dallas",
    # Grupo K — USA Noreste
    ("Portugal",    "DR Congo"):     "Boston",
    ("Uzbekistan",  "Colombia"):     "New York",
    ("Portugal",    "Uzbekistan"):   "Philadelphia",
    ("Colombia",    "DR Congo"):     "New York",
    ("Colombia",    "Portugal"):     "Boston",
    ("DR Congo",    "Uzbekistan"):   "Philadelphia",
    # Grupo L — USA Oeste
    ("England",     "Croatia"):      "San Francisco",
    ("Ghana",       "Panama"):       "Seattle",
    ("England",     "Ghana"):        "Los Angeles",
    ("Panama",      "Croatia"):      "Los Angeles",
    ("Panama",      "England"):      "San Francisco",
    ("Croatia",     "Ghana"):        "Seattle",
}

# ---------------------------------------------------------------------------
# Estilos tácticos — matriz ventaja/desventaja
# ---------------------------------------------------------------------------
TACTICAL_EDGE = {
    ("high_press", "possession"): 1.08,
    ("high_press", "defensive"):  0.92,
    ("high_press", "counter"):    1.05,
    ("high_press", "high_press"): 1.00,
    ("high_press", "mixed"):      1.02,
    ("possession", "defensive"):  0.90,
    ("possession", "counter"):    1.05,
    ("possession", "high_press"): 1.05,
    ("possession", "possession"): 1.00,
    ("possession", "mixed"):      1.00,
    ("counter",    "possession"): 1.12,
    ("counter",    "defensive"):  0.95,
    ("counter",    "high_press"): 0.98,
    ("counter",    "counter"):    1.00,
    ("counter",    "mixed"):      1.03,
    ("defensive",  "possession"): 0.85,
    ("defensive",  "defensive"):  0.90,
    ("defensive",  "counter"):    0.92,
    ("defensive",  "high_press"): 0.95,
    ("defensive",  "mixed"):      0.88,
    ("mixed",      "possession"): 0.98,
    ("mixed",      "defensive"):  0.95,
    ("mixed",      "counter"):    1.00,
    ("mixed",      "high_press"): 0.98,
    ("mixed",      "mixed"):      1.00,
}

# ---------------------------------------------------------------------------
# Inicialización de base de datos
# ---------------------------------------------------------------------------

def regenerate_db():
    """Asegura que la base de datos esté inicializada llamando a setup_db.setup()."""
    # Añadir el directorio del script al path para importar setup_db
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    # setup_db usa su propio DB_PATH interno; necesitamos sobrescribirlo para apuntar a /tmp
    import importlib
    import setup_db as _setup_db

    # Parchamos el path en el módulo para que use /tmp/mundial_2026.db
    original_path = _setup_db.DB_PATH
    _setup_db.DB_PATH = DB_PATH
    try:
        _setup_db.setup()
    finally:
        _setup_db.DB_PATH = original_path

# ---------------------------------------------------------------------------
# Helpers de DB
# ---------------------------------------------------------------------------

def get_team(conn, name):
    cur = conn.cursor()
    cur.execute("SELECT * FROM teams WHERE name=? OR name_es=?", (name, name))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Equipo no encontrado: {name}")
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


# ---------------------------------------------------------------------------
# Módulo 1 — Cálculo de lambdas (goles esperados)
# ---------------------------------------------------------------------------

def elo_win_prob(elo_a, elo_b):
    """Probabilidad de que A gane según ELO (escala FIFA)."""
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def compute_lambdas(team_home, team_away, venue=None):
    """
    Calcula los goles esperados (lambda) para cada equipo.

    Lambda = base_goals
             × attack_factor(equipo)
             × defense_factor(rival)
             × form_factor
             × depth_factor
             × tactical_factor
             × altitude_factor(sede)
    """
    avg_elo = 1600

    # Factores ataque/defensa basados en ELO relativo
    atk_home = (team_home["elo_rating"] / avg_elo) ** 0.6
    def_away  = (avg_elo / team_away["elo_rating"]) ** 0.4
    atk_away  = (team_away["elo_rating"] / avg_elo) ** 0.6
    def_home  = (avg_elo / team_home["elo_rating"]) ** 0.4

    # Forma (normalizado: 5.0 = neutro)
    form_home = team_home["form_score"] / 5.0
    form_away = team_away["form_score"] / 5.0

    # Profundidad de plantilla (impacto suave)
    depth_home = (team_home["squad_depth_score"] / 5.0) ** 0.2
    depth_away = (team_away["squad_depth_score"] / 5.0) ** 0.2

    # Estilo táctico
    style_h = team_home.get("tactical_style", "mixed") or "mixed"
    style_a = team_away.get("tactical_style", "mixed") or "mixed"
    tact_home = TACTICAL_EDGE.get((style_h, style_a), 1.0)
    tact_away = TACTICAL_EDGE.get((style_a, style_h), 1.0)

    # Factor altitud
    altitude_m = VENUE_ALTITUDE.get(venue, 50) if venue else 50
    alt_factor = altitude_multiplier(altitude_m)

    lambda_home = (WORLD_CUP_AVG_GOALS
                   * atk_home * def_away
                   * form_home * depth_home
                   * tact_home * alt_factor)

    lambda_away = (WORLD_CUP_AVG_GOALS
                   * atk_away * def_home
                   * form_away * depth_away
                   * tact_away * alt_factor)

    return lambda_home, lambda_away


# ---------------------------------------------------------------------------
# Módulo 2 — Distribución Poisson con corrección Dixon-Coles
# ---------------------------------------------------------------------------

def dixon_coles_tau(gh, ga, mu, nu, rho):
    """
    Factor de corrección Dixon-Coles para marcadores bajos.
    Solo aplica cuando gh + ga <= 1 (marcadores: 0-0, 1-0, 0-1).

    Referencia: Dixon & Coles (1997), "Modelling Association Football Scores
    and Inefficiencies in the Football Betting Market".

    tau(0,0) = 1 - mu*nu*rho
    tau(1,0) = 1 + nu*rho
    tau(0,1) = 1 + mu*rho
    tau(x,y) = 1 para x+y > 1
    """
    if gh == 0 and ga == 0:
        return 1.0 - mu * nu * rho
    elif gh == 1 and ga == 0:
        return 1.0 + nu * rho
    elif gh == 0 and ga == 1:
        return 1.0 + mu * rho
    else:
        return 1.0


def poisson_prob(lam, k):
    """P(X=k) para distribución Poisson con media lam."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def score_matrix_dc(lambda_home, lambda_away, max_goals=6, rho=DIXON_COLES_RHO):
    """
    Matriz de probabilidades con corrección Dixon-Coles aplicada a marcadores bajos.
    La normalización final garantiza que las probabilidades sumen 1.
    """
    matrix = {}
    for gh, ga in product(range(max_goals + 1), repeat=2):
        p_raw = poisson_prob(lambda_home, gh) * poisson_prob(lambda_away, ga)
        tau   = dixon_coles_tau(gh, ga, lambda_home, lambda_away, rho)
        matrix[(gh, ga)] = p_raw * tau

    # Normalizar (la corrección perturba ligeramente la suma)
    total = sum(matrix.values())
    if total > 0:
        matrix = {k: v / total for k, v in matrix.items()}

    return matrix


# ---------------------------------------------------------------------------
# Módulo 3 — Predicción de partido individual
# ---------------------------------------------------------------------------

def predict_match(name_home, name_away, conn=None, verbose=True, venue=None):
    """
    Predice el resultado de un partido con corrección Dixon-Coles.
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

    # Determinar sede si no se especifica
    if venue is None:
        venue = MATCH_VENUES.get((name_home, name_away), None)

    lh, la = compute_lambdas(th, ta, venue=venue)
    matrix = score_matrix_dc(lh, la)

    prob_home = sum(p for (gh, ga), p in matrix.items() if gh > ga)
    prob_draw = sum(p for (gh, ga), p in matrix.items() if gh == ga)
    prob_away = sum(p for (gh, ga), p in matrix.items() if gh < ga)

    # Top 3 marcadores más probables
    top3 = sorted(matrix.items(), key=lambda x: -x[1])[:3]
    # Top 5 para compatibilidad con código existente
    top5 = sorted(matrix.items(), key=lambda x: -x[1])[:5]

    best_score = top3[0][0]

    # Confianza basada en diferencia ELO
    elo_diff = abs(th["elo_rating"] - ta["elo_rating"])
    if elo_diff > 250:
        confidence = "alta"
    elif elo_diff > 100:
        confidence = "media"
    else:
        confidence = "baja"

    result = {
        "home":           th["name_es"] or th["name"],
        "away":           ta["name_es"] or ta["name"],
        "home_raw":       th["name"],
        "away_raw":       ta["name"],
        "elo_home":       th["elo_rating"],
        "elo_away":       ta["elo_rating"],
        "lambda_home":    round(lh, 3),
        "lambda_away":    round(la, 3),
        "best_score":     best_score,
        "prob_home_win":  round(prob_home * 100, 1),
        "prob_draw":      round(prob_draw * 100, 1),
        "prob_away_win":  round(prob_away * 100, 1),
        "top3_scores":    [(s, round(p * 100, 2)) for s, p in top3],
        "top5_scores":    [(s, round(p * 100, 2)) for s, p in top5],
        "confidence":     confidence,
        "style_home":     th.get("tactical_style", "?"),
        "style_away":     ta.get("tactical_style", "?"),
        "venue":          venue or "Desconocida",
    }

    if verbose:
        alt = VENUE_ALTITUDE.get(venue, 0) if venue else 0
        alt_m = altitude_multiplier(alt)
        print(f"\n{'='*60}")
        print(f"  {result['home']} (ELO {result['elo_home']:.0f})  vs  {result['away']} (ELO {result['elo_away']:.0f})")
        print(f"  Sede: {result['venue']} ({alt}m, factor ×{alt_m:.2f})")
        print(f"  Estilos: {result['style_home']} vs {result['style_away']}")
        print(f"  λ local={result['lambda_home']} | λ visitante={result['lambda_away']}")
        print(f"  Marcador más probable (DC): {best_score[0]}-{best_score[1]}")
        print(f"  Local: {result['prob_home_win']}% | Empate: {result['prob_draw']}% | Visitante: {result['prob_away_win']}%")
        print(f"  Top 3 marcadores: {[(f'{s[0]}-{s[1]}', f'{p}%') for s,p in result['top3_scores']]}")
        print(f"  Confianza: {confidence}")

    if close_conn:
        conn.close()

    return result


# ---------------------------------------------------------------------------
# Módulo 4 — Simulación Monte Carlo
# ---------------------------------------------------------------------------

def simulate_match_mc(lambda_home, lambda_away, n):
    """
    Simula n partidos usando numpy.random.poisson.
    Retorna arrays (goles_home, goles_away).
    """
    gh = np.random.poisson(lambda_home, n)
    ga = np.random.poisson(lambda_away, n)
    return gh, ga


def simulate_group_mc(group_name, conn, n_sims=N_SIMULATIONS):
    """
    Simula el grupo completo n_sims veces usando Monte Carlo.

    Retorna:
      - finish_counts: dict {team_name: [cnt_1st, cnt_2nd, cnt_3rd, cnt_4th]}
      - match_score_dist: dict {(home,away): Counter de marcadores}
      - teams_ordered: lista de nombres de equipos
    """
    cur = conn.cursor()

    # Obtener fixtures del grupo
    cur.execute("""
        SELECT team_home, team_away FROM recent_matches
        WHERE competition='GROUP_FIXTURE'
          AND team_home IN (SELECT name FROM teams WHERE group_name=?)
        ORDER BY date
    """, (group_name,))
    fixtures = cur.fetchall()

    # Obtener equipos del grupo
    cur.execute("SELECT name FROM teams WHERE group_name=? ORDER BY elo_rating DESC", (group_name,))
    team_names = [row[0] for row in cur.fetchall()]
    n_teams = len(team_names)
    team_idx = {name: i for i, name in enumerate(team_names)}

    # Pre-calcular lambdas para cada partido (costoso hacerlo en cada iteración)
    match_lambdas = []
    for home_name, away_name in fixtures:
        th = get_team(conn, home_name)
        ta = get_team(conn, away_name)
        venue = MATCH_VENUES.get((home_name, away_name), None)
        lh, la = compute_lambdas(th, ta, venue=venue)
        match_lambdas.append((home_name, away_name, lh, la))

    n_matches = len(match_lambdas)

    # Simular todos los goles de una sola vez (vectorizado)
    # Shape: (n_matches, n_sims)
    rng = np.random.default_rng(seed=2026)
    all_gh = np.zeros((n_matches, n_sims), dtype=np.int32)
    all_ga = np.zeros((n_matches, n_sims), dtype=np.int32)
    for i, (_, _, lh, la) in enumerate(match_lambdas):
        all_gh[i] = rng.poisson(lh, n_sims)
        all_ga[i] = rng.poisson(la, n_sims)

    # Acumular puntos, goles para cada simulación
    # pts[t, s], gf[t, s], ga_arr[t, s]
    pts_arr = np.zeros((n_teams, n_sims), dtype=np.int32)
    gf_arr  = np.zeros((n_teams, n_sims), dtype=np.int32)
    gc_arr  = np.zeros((n_teams, n_sims), dtype=np.int32)

    for i, (home_name, away_name, _, _) in enumerate(match_lambdas):
        h_idx = team_idx[home_name]
        a_idx = team_idx[away_name]
        gh = all_gh[i]  # shape (n_sims,)
        ga = all_ga[i]

        gf_arr[h_idx] += gh
        gc_arr[h_idx] += ga
        gf_arr[a_idx] += ga
        gc_arr[a_idx] += gh

        # Puntos: home win → h+3, draw → h+1,a+1, away win → a+3
        home_win = gh > ga
        draw     = gh == ga
        away_win = gh < ga

        pts_arr[h_idx] += home_win * 3 + draw * 1
        pts_arr[a_idx] += away_win * 3 + draw * 1

    # Clasificar en cada simulación
    # Criterio: pts DESC, DG DESC, GF DESC (sin desempate exacto para velocidad)
    dg_arr = gf_arr - gc_arr  # diferencia de goles

    # Construir clave de clasificación: pts*10000 + dg*100 + gf (escalar entero)
    # Suficiente para distinguir sin colisiones en grupos de 4 (máx 9 pts, DG ±12, GF ≈12)
    key_arr = pts_arr * 100000 + dg_arr * 100 + gf_arr  # (n_teams, n_sims)

    # Rank: argsort descendente por eje 0 (columna = simulación)
    # Truco: rank = argsort(argsort(-key_arr, axis=0), axis=0)
    ranks = np.argsort(-key_arr, axis=0)  # (n_teams, n_sims): índices ordenados
    positions = np.empty_like(ranks)
    for s in range(n_sims):
        positions[ranks[:, s], s] = np.arange(n_teams)  # 0=primero

    # Contar posiciones: finish_counts[t_idx][pos] = n veces
    finish_counts = {}
    for t_idx, name in enumerate(team_names):
        counts = [int(np.sum(positions[t_idx] == p)) for p in range(n_teams)]
        finish_counts[name] = counts

    # Distribución de marcadores por partido (sample de hasta 10k para frecuencia)
    match_score_dist = {}
    for i, (home_name, away_name, _, _) in enumerate(match_lambdas):
        # Contador de marcadores
        scores = list(zip(all_gh[i].tolist(), all_ga[i].tolist()))
        score_counter = {}
        for s in scores:
            score_counter[s] = score_counter.get(s, 0) + 1
        # Top 3 más frecuentes
        top3 = sorted(score_counter.items(), key=lambda x: -x[1])[:3]
        match_score_dist[(home_name, away_name)] = top3

    return finish_counts, match_score_dist, team_names


# ---------------------------------------------------------------------------
# Módulo 5 — Simulación determinista del grupo (marcador modal)
# ---------------------------------------------------------------------------

def simulate_group(group_name, conn=None, verbose=True):
    """
    Simula todos los partidos con el marcador más probable (Dixon-Coles).
    Compatibilidad con predictor.py original.
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

    cur.execute("SELECT name, name_es FROM teams WHERE group_name=? ORDER BY elo_rating DESC", (group_name,))
    teams_in_group = []
    for row in cur.fetchall():
        teams_in_group.append({
            "name": row[0], "name_es": row[1] or row[0],
            "pts": 0, "gf": 0, "ga": 0, "w": 0, "d": 0, "l": 0
        })

    standings = {t["name"]: t for t in teams_in_group}

    results = []
    for home_name, away_name in fixtures:
        r = predict_match(home_name, away_name, conn=conn, verbose=False)
        gh, ga = r["best_score"]
        results.append({
            "home":   r["home"],   "away":   r["away"],
            "score":  f"{gh}-{ga}",
            "prob_h": r["prob_home_win"],
            "prob_d": r["prob_draw"],
            "prob_a": r["prob_away_win"],
            "top3":   r["top3_scores"],
        })
        sh = standings[home_name]
        sa = standings[away_name]
        sh["gf"] += gh;  sh["ga"] += ga
        sa["gf"] += ga;  sa["ga"] += gh
        if gh > ga:
            sh["pts"] += 3; sh["w"] += 1; sa["l"] += 1
        elif gh == ga:
            sh["pts"] += 1; sh["d"] += 1
            sa["pts"] += 1; sa["d"] += 1
        else:
            sa["pts"] += 3; sa["w"] += 1; sh["l"] += 1

    sorted_teams = sorted(standings.values(),
                          key=lambda t: (t["pts"], t["gf"] - t["ga"], t["gf"]),
                          reverse=True)

    if verbose:
        print(f"\n{'='*60}")
        print(f"  GRUPO {group_name} — PARTIDOS")
        print(f"{'='*60}")
        for r in results:
            print(f"  {r['home']:20s} {r['score']:5s} {r['away']:20s}  ({r['prob_h']}% / {r['prob_d']}% / {r['prob_a']}%)")
        print(f"\n  TABLA FINAL GRUPO {group_name}")
        print(f"  {'Equipo':<22} {'PJ':>2} {'G':>2} {'E':>2} {'P':>2} {'GF':>3} {'GC':>3} {'DG':>4} {'PTS':>4}")
        print(f"  {'-'*55}")
        for i, t in enumerate(sorted_teams):
            marker = "  Q" if i < 2 else "   "
            print(f"{marker} {t['name_es']:<22} {3:>2} {t['w']:>2} {t['d']:>2} {t['l']:>2} {t['gf']:>3} {t['ga']:>3} {t['gf']-t['ga']:>4} {t['pts']:>4}")

    if close_conn:
        conn.close()

    return sorted_teams, results


# ---------------------------------------------------------------------------
# Módulo 6 — Reporte mejorado por grupo
# ---------------------------------------------------------------------------

def group_report(group_name, conn=None, n_sims=N_SIMULATIONS):
    """
    Imprime un reporte completo de un grupo con:
      - Tabla de posiciones con % de clasificación (Monte Carlo)
      - Marcadores predichos con los 3 más probables por partido
      - Intervalos de confianza para los % de clasificación
    """
    close_conn = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close_conn = True

    print(f"\n{'#'*65}")
    print(f"#  REPORTE GRUPO {group_name} — Monte Carlo ({n_sims:,} iteraciones)")
    print(f"{'#'*65}")

    # 1. Simulación Monte Carlo
    finish_counts, match_score_dist, team_names = simulate_group_mc(
        group_name, conn, n_sims=n_sims
    )

    # 2. Tabla determinista (para marcadores)
    cur = conn.cursor()
    cur.execute("""
        SELECT team_home, team_away FROM recent_matches
        WHERE competition='GROUP_FIXTURE'
          AND team_home IN (SELECT name FROM teams WHERE group_name=?)
        ORDER BY date
    """, (group_name,))
    fixtures = cur.fetchall()

    cur.execute("""
        SELECT name, name_es, elo_rating, confederation FROM teams
        WHERE group_name=?
        ORDER BY elo_rating DESC
    """, (group_name,))
    team_rows = cur.fetchall()
    team_info = {row[0]: {"name_es": row[1] or row[0], "elo": row[2], "conf": row[3]}
                 for row in team_rows}

    # 3. Tabla de posiciones con % de clasificación MC
    # Ordenar equipos por % de veces en 1er lugar (aproximación)
    def mc_rank_score(name):
        c = finish_counts[name]
        # Peso: 1° * 4 + 2° * 2 + 3° * 1
        return c[0] * 4 + c[1] * 2 + (c[2] if len(c) > 2 else 0)

    teams_by_mc = sorted(team_names, key=mc_rank_score, reverse=True)

    print(f"\n  {'Equipo':<22} {'ELO':>5}  {'1.°%':>6}  {'2.°%':>6}  {'3.°%':>6}  {'Clasif%':>8}")
    print(f"  {'-'*62}")
    for name in teams_by_mc:
        c = finish_counts[name]
        pct_1 = c[0] / n_sims * 100
        pct_2 = c[1] / n_sims * 100
        pct_3 = c[2] / n_sims * 100 if len(c) > 2 else 0.0
        pct_clasif = pct_1 + pct_2  # directo
        info = team_info.get(name, {})
        name_es = info.get("name_es", name)
        elo    = info.get("elo", 0)

        # Intervalo de confianza 95% (proporción binomial) para clasificación directa
        p_hat = pct_clasif / 100
        margin = 1.96 * math.sqrt(p_hat * (1 - p_hat) / n_sims) * 100
        ci_str = f"±{margin:.1f}%"

        marker = "  Q" if pct_clasif >= 50 else "   "
        print(f"{marker} {name_es:<22} {elo:>5.0f}  {pct_1:>5.1f}%  {pct_2:>5.1f}%  {pct_3:>5.1f}%  {pct_clasif:>6.1f}% {ci_str}")

    print(f"\n  {'Partido':<44} {'Marcador MC':>12}  {'Top 3 marcadores'}")
    print(f"  {'-'*85}")

    for home_name, away_name in fixtures:
        r = predict_match(home_name, away_name, conn=conn, verbose=False)
        venue = MATCH_VENUES.get((home_name, away_name), "N/A")
        alt   = VENUE_ALTITUDE.get(venue, 0)

        # Marcador más frecuente en MC
        mc_scores = match_score_dist.get((home_name, away_name), [])
        if mc_scores:
            mc_best_score, mc_count = mc_scores[0]
            mc_pct = mc_count / n_sims * 100
            mc_str = f"{mc_best_score[0]}-{mc_best_score[1]} ({mc_pct:.1f}%)"
        else:
            mc_str = "N/A"

        # Top 3 de DC analítico
        top3_str = "  |  ".join(
            [f"{s[0]}-{s[1]}({p:.1f}%)" for s, p in r["top3_scores"]]
        )

        home_es = team_info.get(home_name, {}).get("name_es", home_name)
        away_es = team_info.get(away_name, {}).get("name_es", away_name)
        match_str = f"{home_es} vs {away_es}"
        print(f"  {match_str:<44} {mc_str:>12}  {top3_str}")
        print(f"    Sede: {venue} ({alt}m) | "
              f"L:{r['prob_home_win']}% E:{r['prob_draw']}% V:{r['prob_away_win']}%")

    # 4. Probabilidad de que el 3° clasifique como mejor tercero
    # (se calcula correctamente solo con simulación full-tournament, pero
    #  aquí reportamos la distribución de puntos del 3° como aproximación)
    third_pts_dist = {}
    for name in team_names:
        c = finish_counts[name]
        if len(c) > 2:
            third_pts_dist[name] = c[2] / n_sims * 100

    best_third_candidate = max(third_pts_dist, key=third_pts_dist.get) if third_pts_dist else None
    if best_third_candidate:
        pct_3rd = third_pts_dist[best_third_candidate]
        name_es_3rd = team_info.get(best_third_candidate, {}).get("name_es", best_third_candidate)
        print(f"\n  Equipo mas frecuente en 3er lugar: {name_es_3rd} ({pct_3rd:.1f}% de simulaciones)")
        print(f"  (La clasificacion como mejor 3. depende de los otros grupos)")

    if close_conn:
        conn.close()


# ---------------------------------------------------------------------------
# Módulo 7 — Mejor tercero entre grupos (ranking global)
# ---------------------------------------------------------------------------

def rank_third_places(conn, n_sims=N_SIMULATIONS):
    """
    Simula todos los grupos y estima qué 8 terceros clasifican.
    Retorna dict {group: {team_name, pct_classify_as_best_third}}.
    """
    print(f"\n{'='*65}")
    print(f"  RANKING MEJORES TERCEROS (Monte Carlo {n_sims:,} iter.)")
    print(f"{'='*65}")

    # Para cada grupo, obtener la distribución de puntos/DG del 3er clasificado
    groups = list("ABCDEFGHIJKL")
    third_place_teams = []  # (group, team_name, pct_3rd_place)

    for g in groups:
        cur = conn.cursor()
        cur.execute("SELECT name, name_es FROM teams WHERE group_name=?", (g,))
        rows = cur.fetchall()
        team_info_local = {r[0]: r[1] or r[0] for r in rows}

        finish_counts, _, team_names = simulate_group_mc(g, conn, n_sims=n_sims)

        for name in team_names:
            c = finish_counts[name]
            pct_3 = c[2] / n_sims * 100 if len(c) > 2 else 0
            if pct_3 > 0:
                third_place_teams.append({
                    "group":    g,
                    "name":     name,
                    "name_es":  team_info_local.get(name, name),
                    "pct_3rd":  pct_3,
                })

    # Ordenar por % de veces en 3er lugar (proxy de fuerza del tercero)
    third_place_teams.sort(key=lambda x: -x["pct_3rd"])

    print(f"\n  {'Grupo':>6}  {'Equipo':<24}  {'% veces 3.°':>12}")
    print(f"  {'-'*48}")
    for i, t in enumerate(third_place_teams[:12]):
        marker = "  Q8" if i < 8 else "    "
        print(f"{marker} {t['group']:>4}  {t['name_es']:<24}  {t['pct_3rd']:>10.1f}%")


# ---------------------------------------------------------------------------
# Main — Reporte completo de los 12 grupos
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 65)
    print("  PREDICTOR V2 — Mundial 2026")
    print("  Poisson + Dixon-Coles + Monte Carlo + Altitud")
    print("=" * 65)

    # 1. Asegurar que la DB esté inicializada
    print("\n[1/3] Inicializando base de datos...")
    regenerate_db()

    conn = sqlite3.connect(DB_PATH)

    # 2. Reporte completo por grupo
    print("\n[2/3] Ejecutando reportes de grupo con Monte Carlo...")
    for g in "ABCDEFGHIJKL":
        group_report(g, conn=conn, n_sims=N_SIMULATIONS)

    # 3. Ranking de mejores terceros
    print("\n[3/3] Calculando ranking de mejores terceros...")
    rank_third_places(conn, n_sims=N_SIMULATIONS)

    conn.close()
    print("\n\nListo. Predictor v2 completado.")
