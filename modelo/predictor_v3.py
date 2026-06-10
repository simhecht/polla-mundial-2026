"""
predictor_v3.py
Motor de predicción Poisson — versión 3 (calibrada).

Correcciones sobre v2:
  1. rho = -0.10 (de -0.13): calibrado para fútbol internacional, no de clubes.
  2. Exponentes ELO: ataque=2.0, defensa=1.5 (de 0.6/0.4) → spread real entre fuertes y débiles.
  3. form_factor: capped ±25% (antes sin límite: form=9 generaba ×1.8).
  4. depth_factor: eliminado (exponent 0.2 lo hacía prácticamente inerte, rango 0.87-1.15).
  5. tactical_edge: desviaciones escaladas al 50% → rango ±6% máximo.
  6. host_advantage: México (+20%/-13%), USA (+13%/-6%), Canadá (+10%/-5%).
     La penalización de México es mayor para que no quede anulada por el boost
     de altitud (×1.12 en CDMX) y siempre reduzca el lambda rival vs. sede neutral.
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
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "mundial_2026.db")
WORLD_CUP_AVG_GOALS = 1.3   # por equipo, por partido (promedio grupos ~2.7 total)
N_SIMULATIONS      = 50_000
DIXON_COLES_RHO    = -0.10  # calibrado para fútbol internacional (v2 usaba -0.13, clubs ingleses)

# ELO exponents — mayor exponente = más spread entre fuertes y débiles
# v3.1 (9 jun 2026): 2.0/1.5 → 2.8/2.1 tras grid search sobre 19 amistosos + 12 cuotas de mercado
# Resultado: Dir 79%→79%, Top3 68%→74%, Exact 37%→42%, ΔMercado 10.6pp→5.1pp
ATK_EXP = 2.8   # (era 2.0 en v3, 0.6 en v2)
DEF_EXP = 2.1   # (era 1.5 en v3, 0.4 en v2)
AVG_ELO = 1600

# Form factor: ±25% máximo desde la media (5.0)
# form=3 → ×0.90, form=5 → ×1.00, form=9 → ×1.20
FORM_CAP = 0.25   # 0.05 por punto de desviación respecto a 5.0 (rango ±25% total)

# v3.2: selección de marcador result-first
# Si la diferencia entre prob_local y prob_visitante < este umbral,
# el partido se trata como empate (demasiado equilibrado para distinguir ganador).
RESULT_MARGIN_PP = 5.0

# ---------------------------------------------------------------------------
# Ventaja de local para las tres naciones anfitrionas
# boost: multiplicador adicional a lambda del equipo anfitrión
# penalty: multiplicador de reducción a lambda del rival
# La ventaja aplica cuando el venue pertenece al país del equipo
# ---------------------------------------------------------------------------
HOST_ADVANTAGE = {
    "Mexico": {
        "boost":   0.20,
        # 0.13 (era 0.08): debe superar el boost de altitud de CDMX (×1.12) para
        # que el rival siempre reciba MENOS lambda que en sede neutral.
        # Umbral: 1 - 1/1.12 ≈ 10.7%; con el caso 'away en DB' (85% de la
        # penalización) se requiere > 0.107/0.85 ≈ 12.6% → 0.13.
        # Net CDMX: 1.12×0.87 = 0.974 (host como home) | 1.12×0.8895 = 0.996 (away en DB).
        "penalty": 0.13,
        "venues":  {"Ciudad de Mexico", "Guadalajara", "Monterrey"},
    },
    "USA": {
        "boost":   0.13,
        "penalty": 0.06,
        "venues":  {
            "Dallas", "Los Angeles", "Houston", "Kansas City",
            "Seattle", "San Francisco", "Miami", "Atlanta",
            "Boston", "Philadelphia", "New York",
        },
    },
    "Canada": {
        "boost":   0.10,
        "penalty": 0.05,
        "venues":  {"Vancouver", "Toronto"},
    },
}

# ---------------------------------------------------------------------------
# Altitud por sede
# ---------------------------------------------------------------------------
VENUE_ALTITUDE = {
    "Ciudad de Mexico": 2240, "Guadalajara": 1540, "Monterrey": 540,
    "Atlanta": 313, "Dallas": 200, "Houston": 15, "Kansas City": 266,
    "Los Angeles": 71, "Miami": 2, "Philadelphia": 12, "Boston": 9,
    "Seattle": 56, "San Francisco": 16, "New York": 10,
    "Vancouver": 2, "Toronto": 76,
}

def altitude_multiplier(altitude_m):
    if altitude_m >= 1800: return 1.12
    elif altitude_m >= 1000: return 1.06
    elif altitude_m >= 500:  return 1.02
    else:                    return 1.00

# ---------------------------------------------------------------------------
# Fixtures → sede
# ---------------------------------------------------------------------------
MATCH_VENUES = {
    ("Mexico","South Africa"): "Ciudad de Mexico",
    ("South Korea","Czechia"): "Guadalajara",
    ("Czechia","South Africa"): "Guadalajara",
    ("Mexico","South Korea"): "Ciudad de Mexico",
    ("Czechia","Mexico"): "Ciudad de Mexico",
    ("South Africa","South Korea"): "Guadalajara",
    ("Canada","Bosnia"): "Toronto",
    ("Qatar","Switzerland"): "Vancouver",
    ("Switzerland","Bosnia"): "Vancouver",
    ("Canada","Qatar"): "Toronto",
    ("Switzerland","Canada"): "Toronto",
    ("Bosnia","Qatar"): "Toronto",
    ("Brazil","Morocco"): "Philadelphia",
    ("Haiti","Scotland"): "Atlanta",
    ("Scotland","Morocco"): "Atlanta",
    ("Brazil","Haiti"): "Miami",
    ("Scotland","Brazil"): "Miami",
    ("Morocco","Haiti"): "Philadelphia",
    ("USA","Paraguay"): "Dallas",
    ("Australia","Turkey"): "Houston",
    ("Turkey","Paraguay"): "Houston",
    ("USA","Australia"): "Kansas City",
    ("Turkey","USA"): "Dallas",
    ("Paraguay","Australia"): "Kansas City",
    ("Germany","Curacao"): "Dallas",
    ("Ivory Coast","Ecuador"): "Atlanta",
    ("Germany","Ivory Coast"): "Kansas City",
    ("Ecuador","Curacao"): "Houston",
    ("Ecuador","Germany"): "Dallas",
    ("Curacao","Ivory Coast"): "Miami",
    ("Netherlands","Japan"): "Los Angeles",
    ("Sweden","Tunisia"): "San Francisco",
    ("Netherlands","Sweden"): "Seattle",
    ("Tunisia","Japan"): "Los Angeles",
    ("Japan","Sweden"): "San Francisco",
    ("Tunisia","Netherlands"): "Los Angeles",
    ("Belgium","Egypt"): "Miami",
    ("Iran","New Zealand"): "Kansas City",
    ("Belgium","Iran"): "Kansas City",
    ("New Zealand","Egypt"): "Houston",
    ("Egypt","Iran"): "Houston",
    ("New Zealand","Belgium"): "Atlanta",
    ("Spain","Cabo Verde"): "Miami",
    ("Saudi Arabia","Uruguay"): "Philadelphia",
    ("Spain","Saudi Arabia"): "Boston",
    ("Uruguay","Cabo Verde"): "New York",
    ("Cabo Verde","Saudi Arabia"): "Boston",
    ("Uruguay","Spain"): "Philadelphia",
    ("France","Senegal"): "New York",
    ("Iraq","Norway"): "Boston",
    ("France","Iraq"): "New York",
    ("Norway","Senegal"): "Philadelphia",
    ("Norway","France"): "Boston",
    ("Senegal","Iraq"): "Philadelphia",
    ("Argentina","Algeria"): "Dallas",
    ("Austria","Jordan"): "Atlanta",
    ("Argentina","Austria"): "Dallas",
    ("Jordan","Algeria"): "Houston",
    ("Algeria","Austria"): "Atlanta",
    ("Jordan","Argentina"): "Dallas",
    ("Portugal","DR Congo"): "Boston",
    ("Uzbekistan","Colombia"): "New York",
    ("Portugal","Uzbekistan"): "Philadelphia",
    ("Colombia","DR Congo"): "New York",
    ("Colombia","Portugal"): "Boston",
    ("DR Congo","Uzbekistan"): "Philadelphia",
    ("England","Croatia"): "San Francisco",
    ("Ghana","Panama"): "Seattle",
    ("England","Ghana"): "Los Angeles",
    ("Panama","Croatia"): "Los Angeles",
    ("Panama","England"): "San Francisco",
    ("Croatia","Ghana"): "Seattle",
}


def get_venue(home, away):
    """Lookup venue tolerante al orden: prueba (home, away) y luego (away, home)."""
    return MATCH_VENUES.get((home, away)) or MATCH_VENUES.get((away, home))


# ---------------------------------------------------------------------------
# Matriz táctica — desviaciones escaladas al 50% (rango ±6% máximo)
# Fórmula: new = 1.0 + (old - 1.0) × 0.5
# ---------------------------------------------------------------------------
def _scale_tact(v):
    return round(1.0 + (v - 1.0) * 0.5, 4)

TACTICAL_EDGE = {
    ("high_press", "possession"): _scale_tact(1.08),   # 1.04
    ("high_press", "defensive"):  _scale_tact(0.92),   # 0.96
    ("high_press", "counter"):    _scale_tact(1.05),   # 1.025
    ("high_press", "high_press"): 1.00,
    ("high_press", "mixed"):      _scale_tact(1.02),   # 1.01
    ("possession", "defensive"):  _scale_tact(0.90),   # 0.95
    ("possession", "counter"):    _scale_tact(1.05),   # 1.025
    ("possession", "high_press"): _scale_tact(1.05),   # 1.025
    ("possession", "possession"): 1.00,
    ("possession", "mixed"):      1.00,
    ("counter",    "possession"): _scale_tact(1.12),   # 1.06
    ("counter",    "defensive"):  _scale_tact(0.95),   # 0.975
    ("counter",    "high_press"): _scale_tact(0.98),   # 0.99
    ("counter",    "counter"):    1.00,
    ("counter",    "mixed"):      _scale_tact(1.03),   # 1.015
    ("defensive",  "possession"): _scale_tact(0.85),   # 0.925
    ("defensive",  "defensive"):  _scale_tact(0.90),   # 0.95
    ("defensive",  "counter"):    _scale_tact(0.92),   # 0.96
    ("defensive",  "high_press"): _scale_tact(0.95),   # 0.975
    ("defensive",  "mixed"):      _scale_tact(0.88),   # 0.94
    ("mixed",      "possession"): _scale_tact(0.98),   # 0.99
    ("mixed",      "defensive"):  _scale_tact(0.95),   # 0.975
    ("mixed",      "counter"):    1.00,
    ("mixed",      "high_press"): _scale_tact(0.98),   # 0.99
    ("mixed",      "mixed"):      1.00,
}

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def regenerate_db():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    import importlib, setup_db as _setup_db, update_all_teams as _uat
    orig = _setup_db.DB_PATH
    _setup_db.DB_PATH = DB_PATH
    try:
        _setup_db.setup()
    finally:
        _setup_db.DB_PATH = orig
    _uat.run(db_path=DB_PATH)

def get_team(conn, name):
    cur = conn.cursor()
    cur.execute("SELECT * FROM teams WHERE name=? OR name_es=?", (name, name))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Equipo no encontrado: {name}")
    return dict(zip([d[0] for d in cur.description], row))

# ---------------------------------------------------------------------------
# Lambdas (goles esperados)
# ---------------------------------------------------------------------------
def compute_lambdas(team_home, team_away, venue=None):
    """
    λ = BASE × atk(equipo)^ATK_EXP × def(rival)^DEF_EXP × form × tactic × altitude × host_advantage

    atk = elo / AVG_ELO (>1 para equipos sobre la media)
    def = AVG_ELO / elo_rival (>1 cuando el rival es débil → goles esperados suben)

    Cambios v3:
    - ATK_EXP=2.0, DEF_EXP=1.5 generan un spread real entre favoritos y débiles
    - form_factor capped ±25%
    - sin depth_factor (era inerte con exp 0.2)
    - tactical ±6% máximo
    - host advantage para México, USA, Canadá
    """
    # ---- ELO factors ----
    atk_home = (team_home["elo_rating"] / AVG_ELO) ** ATK_EXP
    def_away  = (AVG_ELO / team_away["elo_rating"]) ** DEF_EXP
    atk_away  = (team_away["elo_rating"] / AVG_ELO) ** ATK_EXP
    def_home  = (AVG_ELO / team_home["elo_rating"]) ** DEF_EXP

    # ---- Form factor (±25% cap) ----
    form_home = 1.0 + (team_home["form_score"] - 5.0) / 5.0 * FORM_CAP
    form_away = 1.0 + (team_away["form_score"] - 5.0) / 5.0 * FORM_CAP
    form_home = max(0.60, min(1.40, form_home))  # hard clamp por seguridad
    form_away = max(0.60, min(1.40, form_away))

    # ---- Tactical factor ----
    style_h = team_home.get("tactical_style", "mixed") or "mixed"
    style_a = team_away.get("tactical_style", "mixed") or "mixed"
    tact_home = TACTICAL_EDGE.get((style_h, style_a), 1.0)
    tact_away = TACTICAL_EDGE.get((style_a, style_h), 1.0)

    # ---- Altitude factor ----
    altitude_m  = VENUE_ALTITUDE.get(venue, 50) if venue else 50
    alt_factor  = altitude_multiplier(altitude_m)

    # ---- Base lambdas ----
    lh = WORLD_CUP_AVG_GOALS * atk_home * def_away * form_home * tact_home * alt_factor
    la = WORLD_CUP_AVG_GOALS * atk_away * def_home * form_away * tact_away * alt_factor

    # ---- Host advantage (crowd + referee + familiarity) ----
    # Aplica cuando el venue pertenece al país del equipo (sea local o visitante en DB)
    if venue:
        for host_name, hdata in HOST_ADVANTAGE.items():
            if venue in hdata["venues"]:
                boost   = hdata["boost"]
                penalty = hdata["penalty"]
                if team_home["name"] == host_name:
                    # Equipo anfitrión listado como 'home' → boost completo
                    lh *= (1.0 + boost)
                    la *= (1.0 - penalty)
                elif team_away["name"] == host_name:
                    # Equipo anfitrión listado como 'away' en DB pero juega en casa
                    # (ej: "Czechia vs Mexico" en Ciudad de Mexico)
                    la *= (1.0 + boost * 0.85)   # 85% del boost al ser 'away' en DB
                    lh *= (1.0 - penalty * 0.85)
                break  # solo un host por venue

    return max(lh, 0.05), max(la, 0.05)  # floor para evitar división/log problemas

# ---------------------------------------------------------------------------
# Poisson + Dixon-Coles
# ---------------------------------------------------------------------------
def dixon_coles_tau(gh, ga, mu, nu, rho):
    if gh == 0 and ga == 0: return 1.0 - mu * nu * rho
    elif gh == 1 and ga == 0: return 1.0 + nu * rho
    elif gh == 0 and ga == 1: return 1.0 + mu * rho
    elif gh == 1 and ga == 1: return 1.0 - rho
    else: return 1.0

def poisson_prob(lam, k):
    if lam <= 0: return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def score_matrix_dc(lambda_home, lambda_away, max_goals=6, rho=DIXON_COLES_RHO):
    matrix = {}
    for gh, ga in product(range(max_goals + 1), repeat=2):
        p_raw = poisson_prob(lambda_home, gh) * poisson_prob(lambda_away, ga)
        tau   = dixon_coles_tau(gh, ga, lambda_home, lambda_away, rho)
        matrix[(gh, ga)] = p_raw * tau
    total = sum(matrix.values())
    if total > 0:
        matrix = {k: v / total for k, v in matrix.items()}
    return matrix


def best_score_result_first(matrix):
    """
    Elige el marcador dentro del resultado dominante (v3.2).

    Pasos:
    1. Calcula prob acumulada: victoria local, empate, victoria visitante.
    2. Determina el resultado dominante (mayor prob acumulada).
    3. Si local o visitante es dominante pero la diferencia entre ambas prob de
       victoria es menor a RESULT_MARGIN_PP puntos porcentuales, se trata como
       empate (partido demasiado equilibrado para elegir ganador).
    4. Retorna el marcador individual de mayor probabilidad dentro de esa categoría.
    """
    prob_h = sum(p for (gh, ga), p in matrix.items() if gh > ga)
    prob_d = sum(p for (gh, ga), p in matrix.items() if gh == ga)
    prob_a = sum(p for (gh, ga), p in matrix.items() if gh < ga)

    dominant = max(
        [('home', prob_h), ('draw', prob_d), ('away', prob_a)],
        key=lambda x: x[1]
    )[0]

    if dominant in ('home', 'away'):
        if abs(prob_h - prob_a) * 100 < RESULT_MARGIN_PP:
            dominant = 'draw'

    if dominant == 'home':
        candidates = {s: p for s, p in matrix.items() if s[0] > s[1]}
    elif dominant == 'draw':
        candidates = {s: p for s, p in matrix.items() if s[0] == s[1]}
    else:
        candidates = {s: p for s, p in matrix.items() if s[0] < s[1]}

    return max(candidates, key=candidates.get)

# ---------------------------------------------------------------------------
# Predicción de partido
# ---------------------------------------------------------------------------
def predict_match(name_home, name_away, conn=None, verbose=True, venue=None):
    close_conn = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH); close_conn = True
    try:
        th = get_team(conn, name_home)
        ta = get_team(conn, name_away)
    except ValueError as e:
        if close_conn: conn.close()
        raise e

    if venue is None:
        venue = get_venue(name_home, name_away)

    lh, la = compute_lambdas(th, ta, venue=venue)
    matrix  = score_matrix_dc(lh, la)

    prob_home = sum(p for (gh, ga), p in matrix.items() if gh > ga)
    prob_draw = sum(p for (gh, ga), p in matrix.items() if gh == ga)
    prob_away = sum(p for (gh, ga), p in matrix.items() if gh < ga)

    top5 = sorted(matrix.items(), key=lambda x: -x[1])[:5]
    top3 = top5[:3]

    # best_score: marcador más probable CONDICIONADO al resultado más probable.
    # Si P(victoria local) es máximo → el marcador modal entre gh>ga.
    # Si P(empate) es máximo → el marcador modal entre gh==ga.
    # Si P(victoria visitante) es máximo → el marcador modal entre gh<ga.
    # top3_scores y top5_scores siguen siendo los modos crudos (informativos).
    probs = {"home": prob_home, "draw": prob_draw, "away": prob_away}
    dominant = max(probs, key=probs.__getitem__)
    if dominant == "home":
        cond_items = [(s, p) for (s, p) in matrix.items() if s[0] > s[1]]
    elif dominant == "draw":
        cond_items = [(s, p) for (s, p) in matrix.items() if s[0] == s[1]]
    else:
        cond_items = [(s, p) for (s, p) in matrix.items() if s[0] < s[1]]
    best_score = max(cond_items, key=lambda x: x[1])[0] if cond_items else top3[0][0]

    elo_diff = abs(th["elo_rating"] - ta["elo_rating"])
    confidence = "alta" if elo_diff > 250 else "media" if elo_diff > 100 else "baja"

    result = {
        "home": th["name_es"] or th["name"],
        "away": ta["name_es"] or ta["name"],
        "home_raw": th["name"], "away_raw": ta["name"],
        "elo_home": th["elo_rating"], "elo_away": ta["elo_rating"],
        "lambda_home": round(lh, 3), "lambda_away": round(la, 3),
        "best_score": best_score,
        "prob_home_win": round(prob_home * 100, 1),
        "prob_draw":     round(prob_draw * 100, 1),
        "prob_away_win": round(prob_away * 100, 1),
        "top3_scores":  [(s, round(p * 100, 2)) for s, p in top3],
        "top5_scores":  [(s, round(p * 100, 2)) for s, p in top5],
        "confidence":   confidence,
        "style_home":   th.get("tactical_style", "?"),
        "style_away":   ta.get("tactical_style", "?"),
        "venue":        venue or "N/D",
    }

    if verbose:
        alt   = VENUE_ALTITUDE.get(venue, 0) if venue else 0
        alt_m = altitude_multiplier(alt)
        # Host boost display
        host_info = ""
        if venue:
            for hn, hd in HOST_ADVANTAGE.items():
                if venue in hd["venues"]:
                    if th["name"] == hn:
                        host_info = f" | 🏠 {hn} +{hd['boost']*100:.0f}%"
                    elif ta["name"] == hn:
                        host_info = f" | 🏠 {hn} (visitante) +{hd['boost']*85:.0f}%"
                    break
        print(f"\n{'='*62}")
        print(f"  {result['home']} (ELO {result['elo_home']:.0f})  vs  {result['away']} (ELO {result['elo_away']:.0f})")
        print(f"  Sede: {result['venue']} ({alt}m, ×{alt_m:.2f}){host_info}")
        print(f"  Estilos: {result['style_home']} vs {result['style_away']}")
        print(f"  λ local={result['lambda_home']} | λ visit={result['lambda_away']}")
        print(f"  Marcador: {best_score[0]}-{best_score[1]}")
        print(f"  L:{result['prob_home_win']}% E:{result['prob_draw']}% V:{result['prob_away_win']}%")
        print(f"  Top 3: {[(f'{s[0]}-{s[1]}', f'{p}%') for s,p in result['top3_scores']]}")
        print(f"  Confianza ELO: {confidence}")

    if close_conn: conn.close()
    return result

# ---------------------------------------------------------------------------
# Simulación Monte Carlo del grupo
# ---------------------------------------------------------------------------
def simulate_group_mc(group_name, conn, n_sims=N_SIMULATIONS):
    cur = conn.cursor()
    cur.execute("""
        SELECT team_home, team_away FROM recent_matches
        WHERE competition='GROUP_FIXTURE'
          AND team_home IN (SELECT name FROM teams WHERE group_name=?)
        ORDER BY date
    """, (group_name,))
    fixtures = cur.fetchall()

    cur.execute("SELECT name FROM teams WHERE group_name=? ORDER BY elo_rating DESC", (group_name,))
    team_names = [r[0] for r in cur.fetchall()]
    n_teams    = len(team_names)
    team_idx   = {n: i for i, n in enumerate(team_names)}

    match_lambdas = []
    for home_name, away_name in fixtures:
        th  = get_team(conn, home_name)
        ta  = get_team(conn, away_name)
        ven = get_venue(home_name, away_name)
        lh, la = compute_lambdas(th, ta, venue=ven)
        match_lambdas.append((home_name, away_name, lh, la))

    rng   = np.random.default_rng(seed=2026)
    n_m   = len(match_lambdas)
    all_gh = np.zeros((n_m, n_sims), dtype=np.int32)
    all_ga = np.zeros((n_m, n_sims), dtype=np.int32)
    for i, (_, _, lh, la) in enumerate(match_lambdas):
        # Muestreo desde la distribución conjunta Dixon-Coles (consistente con
        # el motor analítico score_matrix_dc).
        dc_matrix = score_matrix_dc(lh, la)
        scores = list(dc_matrix.keys())
        probs  = np.array([dc_matrix[s] for s in scores], dtype=np.float64)
        probs /= probs.sum()   # renormalizar para evitar errores de punto flotante
        indices = rng.choice(len(scores), size=n_sims, p=probs)
        scores_arr = np.array(scores, dtype=np.int32)  # shape (N, 2)
        all_gh[i] = scores_arr[indices, 0]
        all_ga[i] = scores_arr[indices, 1]

    pts_arr = np.zeros((n_teams, n_sims), dtype=np.int32)
    gf_arr  = np.zeros((n_teams, n_sims), dtype=np.int32)
    gc_arr  = np.zeros((n_teams, n_sims), dtype=np.int32)

    for i, (home_name, away_name, _, _) in enumerate(match_lambdas):
        hi, ai = team_idx[home_name], team_idx[away_name]
        gh, ga  = all_gh[i], all_ga[i]
        gf_arr[hi] += gh; gc_arr[hi] += ga
        gf_arr[ai] += ga; gc_arr[ai] += gh
        hw = gh > ga; dr = gh == ga; aw = gh < ga
        pts_arr[hi] += hw * 3 + dr * 1
        pts_arr[ai] += aw * 3 + dr * 1

    dg_arr  = gf_arr - gc_arr
    key_arr = pts_arr * 100000 + dg_arr * 100 + gf_arr
    ranks   = np.argsort(-key_arr, axis=0)
    positions = np.empty_like(ranks)
    for s in range(n_sims):
        positions[ranks[:, s], s] = np.arange(n_teams)

    finish_counts = {}
    for t_idx, name in enumerate(team_names):
        finish_counts[name] = [int(np.sum(positions[t_idx] == p)) for p in range(n_teams)]

    match_score_dist = {}
    for i, (hn, an, _, _) in enumerate(match_lambdas):
        score_counter = {}
        for s in zip(all_gh[i].tolist(), all_ga[i].tolist()):
            score_counter[s] = score_counter.get(s, 0) + 1
        match_score_dist[(hn, an)] = sorted(score_counter.items(), key=lambda x: -x[1])[:3]

    return finish_counts, match_score_dist, team_names

# ---------------------------------------------------------------------------
# Simulación determinista del grupo
# ---------------------------------------------------------------------------
def simulate_group(group_name, conn=None, verbose=True):
    close_conn = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH); close_conn = True

    cur = conn.cursor()
    cur.execute("""
        SELECT team_home, team_away FROM recent_matches
        WHERE competition='GROUP_FIXTURE'
          AND team_home IN (SELECT name FROM teams WHERE group_name=?)
        ORDER BY date
    """, (group_name,))
    fixtures = cur.fetchall()

    cur.execute("SELECT name, name_es FROM teams WHERE group_name=? ORDER BY elo_rating DESC", (group_name,))
    teams_in_group = [{"name": r[0], "name_es": r[1] or r[0],
                       "pts": 0, "gf": 0, "ga": 0, "w": 0, "d": 0, "l": 0}
                      for r in cur.fetchall()]
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
            "top3":   r["top3_scores"],
        })
        sh, sa = standings[home_name], standings[away_name]
        sh["gf"] += gh; sh["ga"] += ga
        sa["gf"] += ga; sa["ga"] += gh
        if   gh > ga: sh["pts"] += 3; sh["w"] += 1; sa["l"] += 1
        elif gh == ga: sh["pts"] += 1; sh["d"] += 1; sa["pts"] += 1; sa["d"] += 1
        else:          sa["pts"] += 3; sa["w"] += 1; sh["l"] += 1

    sorted_teams = sorted(standings.values(),
                          key=lambda t: (t["pts"], t["gf"] - t["ga"], t["gf"]),
                          reverse=True)
    if verbose:
        print(f"\n{'='*62}")
        print(f"  GRUPO {group_name} — PARTIDOS (predictor v3)")
        for r in results:
            print(f"  {r['home']:22s} {r['score']:5s} {r['away']:22s}"
                  f"  ({r['prob_h']}%/{r['prob_d']}%/{r['prob_a']}%)")
        print(f"\n  {'Equipo':<24} {'G':>2} {'E':>2} {'P':>2} {'GF':>3} {'GC':>3} {'DG':>4} {'PTS':>4}")
        for i, t in enumerate(sorted_teams):
            m = "  Q" if i < 2 else "   "
            print(f"{m} {t['name_es']:<24} {t['w']:>2} {t['d']:>2} {t['l']:>2}"
                  f" {t['gf']:>3} {t['ga']:>3} {t['gf']-t['ga']:>4} {t['pts']:>4}")

    if close_conn: conn.close()
    return sorted_teams, results

# ---------------------------------------------------------------------------
# Reporte completo del grupo (Monte Carlo + determinista)
# ---------------------------------------------------------------------------
def group_report(group_name, conn=None, n_sims=N_SIMULATIONS):
    close_conn = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH); close_conn = True

    print(f"\n{'#'*65}")
    print(f"#  REPORTE GRUPO {group_name} — Monte Carlo ({n_sims:,} iters) [v3]")
    print(f"{'#'*65}")

    finish_counts, match_score_dist, team_names = simulate_group_mc(group_name, conn, n_sims)

    cur = conn.cursor()
    cur.execute("""
        SELECT team_home, team_away FROM recent_matches
        WHERE competition='GROUP_FIXTURE'
          AND team_home IN (SELECT name FROM teams WHERE group_name=?)
        ORDER BY date
    """, (group_name,))
    fixtures = cur.fetchall()

    cur.execute("SELECT name, name_es, elo_rating, confederation FROM teams WHERE group_name=? ORDER BY elo_rating DESC", (group_name,))
    team_info = {r[0]: {"name_es": r[1] or r[0], "elo": r[2], "conf": r[3]} for r in cur.fetchall()}

    def mc_rank_score(name):
        c = finish_counts[name]
        return c[0]*4 + c[1]*2 + (c[2] if len(c)>2 else 0)

    teams_by_mc = sorted(team_names, key=mc_rank_score, reverse=True)
    print(f"\n  {'Equipo':<22} {'ELO':>5}  {'1.°%':>6}  {'2.°%':>6}  {'3.°%':>6}  {'Clasif%':>8}")
    print(f"  {'-'*60}")
    for name in teams_by_mc:
        c = finish_counts[name]
        p1 = c[0]/n_sims*100; p2 = c[1]/n_sims*100
        p3 = c[2]/n_sims*100 if len(c)>2 else 0
        pc = p1+p2
        info = team_info.get(name, {})
        ph = pc/100; margin = 1.96*math.sqrt(ph*(1-ph)/n_sims)*100
        m = "  Q" if pc >= 50 else "   "
        print(f"{m} {info.get('name_es',name):<22} {info.get('elo',0):>5.0f}"
              f"  {p1:>5.1f}%  {p2:>5.1f}%  {p3:>5.1f}%  {pc:>6.1f}% ±{margin:.1f}%")

    print(f"\n  {'Partido':<44} {'MC mejor':>10}  Top 3 marcadores (DC analítico)")
    print(f"  {'-'*90}")
    for hn, an in fixtures:
        r   = predict_match(hn, an, conn=conn, verbose=False)
        ven = get_venue(hn, an) or "N/A"
        alt = VENUE_ALTITUDE.get(ven, 0)
        mc_scores = match_score_dist.get((hn, an), [])
        mc_str = f"{mc_scores[0][0][0]}-{mc_scores[0][0][1]}({mc_scores[0][1]/n_sims*100:.1f}%)" if mc_scores else "N/A"
        top3_str = "  |  ".join(f"{s[0]}-{s[1]}({p:.1f}%)" for s,p in r["top3_scores"])
        he = team_info.get(hn,{}).get("name_es",hn)
        ae = team_info.get(an,{}).get("name_es",an)
        # Agregar indicador de ventaja local
        host_flag = ""
        if ven:
            for hn2, hd in HOST_ADVANTAGE.items():
                if ven in hd["venues"] and (hn==hn2 or an==hn2):
                    host_flag = f" 🏠{hn2[:3]}"
                    break
        print(f"  {he} vs {ae:<35} {mc_str:>10}  {top3_str}")
        print(f"    {ven}({alt}m){host_flag} | L:{r['prob_home_win']}% E:{r['prob_draw']}% V:{r['prob_away_win']}%"
              f" | λ={r['lambda_home']:.2f}/{r['lambda_away']:.2f}")

    if close_conn: conn.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 65)
    print("  PREDICTOR V3 — Mundial 2026")
    print("  Poisson + Dixon-Coles (rho=-0.10) + ELO^2.0 + Host Adv.")
    print("=" * 65)
    print("\n[1/2] Inicializando DB + datos cualitativos...")
    regenerate_db()
    conn = sqlite3.connect(DB_PATH)
    print("\n[2/2] Reportes por grupo...")
    for g in "ABCDEFGHIJKL":
        group_report(g, conn=conn, n_sims=N_SIMULATIONS)
    conn.close()
    print("\nListo.")
