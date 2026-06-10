"""
simulate_knockout.py — Fase eliminatoria Mundial 2026
Bracket FIFA 2026 oficial (R32 → R16 → QF → SF → Final).

Cambios v3.2:
  1. R32 DINÁMICO: los clasificados ya no están hardcodeados. Se derivan del
     escenario DETERMINISTA del modelo (simulate_group para los 12 grupos A-L):
     1.° y 2.° de cada grupo + los 8 mejores terceros.
  2. Mejores terceros: ranking por pts → DG → GF → ELO. Nota: FIFA usa
     fair play y sorteo como últimos criterios; aquí ELO los sustituye
     (el modelo no simula tarjetas).
  3. Asignación de terceros a slots: las combinaciones permitidas por slot
     se verificaron contra el bracket oficial FIFA 2026 (Annex C, vía
     Wikipedia "2026 FIFA World Cup knockout stage", jun 2026):
       M74: 1E vs 3.° de {A,B,C,D,F}     M81: 1D vs 3.° de {B,E,F,I,J}
       M77: 1I vs 3.° de {C,D,F,G,H}     M82: 1G vs 3.° de {A,E,H,I,J}
       M79: 1A vs 3.° de {C,E,F,H,I}     M85: 1B vs 3.° de {E,F,G,I,J}
       M80: 1L vs 3.° de {E,H,I,J,K}     M87: 1K vs 3.° de {D,E,I,J,L}
     APROXIMACIÓN: el Annex C real es una tabla de 495 combinaciones que fija
     una asignación única; aquí se usa backtracking determinista (slots en
     orden de cuadro, terceros probados en orden de ranking) que produce una
     asignación VÁLIDA según las restricciones, no necesariamente la misma
     fila exacta de la tabla FIFA.
  4. SEDES POR PARTIDO KO (verificadas con el calendario oficial FIFA 2026):
     host advantage y altitud ahora aplican en eliminatoria (ej. México en
     Ciudad de México en M79/M92; la final en New York/East Rutherford).
  5. ET_FACTOR = 1/3 (prórroga = 30 de 90 minutos; antes 0.50, erróneo).
  6. Monte Carlo muestrea desde score_matrix_dc (Dixon-Coles) en 90' y
     prórroga, consistente con el motor analítico. Penales: 76% conversión.
  7. predict_ko_match (v3.3) elige la apuesta (marcador 90' + advancer) que
     MAXIMIZA los puntos esperados de la polla (best_bet_ko). P(avanza local |
     empate) se calcula con la matriz de prórroga (λ × ET_FACTOR); los penales
     del modelo son simétricos → 0.5 del empate en prórroga.
  8. Overrides manuales (overrides.py): fijan marcador/advancer del escenario
     determinista; el Monte Carlo NO se toca (probabilidades del modelo).

λ × 0.90 para todos los partidos eliminatorios.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3, math
import numpy as np
from predictor_v3 import (
    get_team, compute_lambdas, score_matrix_dc, simulate_group,
    DB_PATH, regenerate_db
)
from polla_points import best_bet_ko, expected_points_ko
from overrides import ko_override

# ---------------------------------------------------------------------------
# Parámetros
# ---------------------------------------------------------------------------
KO_FACTOR    = 0.90       # λ × 0.90 en eliminatoria (partidos más cerrados)
ET_FACTOR    = 1.0 / 3.0  # prórroga: 30 min de un partido de 90 min → λ × 1/3
PEN_CONV     = 0.76       # conversión penalti élite
N_SIMS_MC    = 20_000

GROUPS = "ABCDEFGHIJKL"

# ---------------------------------------------------------------------------
# Plantilla del bracket R32 oficial FIFA 2026 (partidos 73-88).
# Orden de cuadro: las parejas consecutivas alimentan ADVANCEMENT["R16"].
#   índices 0-7  → mitad superior (QF 97/98 → SF 101)
#   índices 8-15 → mitad inferior (QF 99/100 → SF 102)
# Cada entrada: (match_id, seed_home, seed_away, venue)
#   seed: "1X"/"2X" = 1.°/2.° del grupo X; "3:ABCDF" = mejor tercero de esos grupos.
# Sedes oficiales mapeadas a los nombres EXACTOS de VENUE_ALTITUDE en
# predictor_v3 (Inglewood→Los Angeles, Foxborough→Boston, East Rutherford→
# New York, Arlington→Dallas, Santa Clara→San Francisco, Guadalupe→Monterrey,
# Miami Gardens→Miami, Mexico City→Ciudad de Mexico).
# ---------------------------------------------------------------------------
R32_TEMPLATE = [
    # --- Sección A (→ QF 97, Boston) ---
    ("M74", "1E", "3:ABCDF", "Boston"),            # → R16 M89
    ("M77", "1I", "3:CDFGH", "New York"),          # → R16 M89
    ("M73", "2A", "2B",      "Los Angeles"),       # → R16 M90
    ("M75", "1F", "2C",      "Monterrey"),         # → R16 M90
    # --- Sección B (→ QF 98, Los Angeles) ---
    ("M83", "2K", "2L",      "Toronto"),           # → R16 M93
    ("M84", "1H", "2J",      "Los Angeles"),       # → R16 M93
    ("M81", "1D", "3:BEFIJ", "San Francisco"),     # → R16 M94
    ("M82", "1G", "3:AEHIJ", "Seattle"),           # → R16 M94
    # --- Sección C (→ QF 99, Miami) ---
    ("M76", "1C", "2F",      "Houston"),           # → R16 M91
    ("M78", "2E", "2I",      "Dallas"),            # → R16 M91
    ("M79", "1A", "3:CEFHI", "Ciudad de Mexico"),  # → R16 M92
    ("M80", "1L", "3:EHIJK", "Atlanta"),           # → R16 M92
    # --- Sección D (→ QF 100, Kansas City) ---
    ("M86", "1J", "2H",      "Miami"),             # → R16 M95
    ("M88", "2D", "2G",      "Dallas"),            # → R16 M95
    ("M85", "1B", "3:EFGIJ", "Vancouver"),         # → R16 M96
    ("M87", "1K", "3:DEIJL", "Kansas City"),       # → R16 M96
]

# Cómo avanzan los ganadores de R32 → R16 → QF → SF → Final
# Cada tupla es (índice_match_A, índice_match_B) de la ronda anterior
ADVANCEMENT = {
    "R16":   [(0,1),(2,3),(4,5),(6,7),(8,9),(10,11),(12,13),(14,15)],
    "QF":    [(0,1),(2,3),(4,5),(6,7)],
    "SF":    [(0,1),(2,3)],
    "Final": [(0,1)],
}

# Sedes oficiales por ronda, en el orden de ADVANCEMENT (calendario FIFA 2026)
ROUND_VENUES = {
    # M89 Philadelphia, M90 Houston, M93 Dallas, M94 Seattle,
    # M91 New York, M92 Ciudad de Mexico, M95 Atlanta, M96 Vancouver
    "R16":   ["Philadelphia", "Houston", "Dallas", "Seattle",
              "New York", "Ciudad de Mexico", "Atlanta", "Vancouver"],
    # M97 Boston, M98 Los Angeles, M99 Miami, M100 Kansas City
    "QF":    ["Boston", "Los Angeles", "Miami", "Kansas City"],
    # M101 Dallas, M102 Atlanta
    "SF":    ["Dallas", "Atlanta"],
    # M104 New York (East Rutherford)
    "Final": ["New York"],
}

ROUND_LABELS = {
    "R16":   "OCTAVOS (R16)",
    "QF":    "CUARTOS DE FINAL",
    "SF":    "SEMIFINALES",
    "Final": "FINAL",
}

# ---------------------------------------------------------------------------
# Derivación dinámica del R32 desde el escenario determinista del modelo
# ---------------------------------------------------------------------------
def _rank_thirds(thirds):
    """Ranking de terceros: pts → DG → GF → ELO.
    ELO sustituye los criterios FIFA de fair play y sorteo."""
    return sorted(thirds, key=lambda t: (-t["pts"], -t["dg"], -t["gf"], -t["elo"]))


def _assign_thirds(best8, slots):
    """Asigna los 8 mejores terceros a los slots del bracket por backtracking
    determinista: slots en orden de cuadro, candidatos en orden de ranking.
    Retorna {match_id: third_dict}. Aproximación al Annex C (ver docstring)."""
    assignment, used = {}, set()

    def bt(i):
        if i == len(slots):
            return True
        match_id, allowed = slots[i]
        for t in best8:
            if t["group"] in allowed and t["group"] not in used:
                assignment[match_id] = t
                used.add(t["group"])
                if bt(i + 1):
                    return True
                del assignment[match_id]
                used.discard(t["group"])
        return False

    if not bt(0):
        # No debería ocurrir: el Annex C de FIFA cubre las 495 combinaciones
        # posibles. Fallback: asignación greedy ignorando restricciones.
        print("ADVERTENCIA: no existe matching válido de terceros; "
              "usando asignación greedy sin restricciones.")
        assignment = {match_id: t for (match_id, _), t in zip(slots, best8)}
    return assignment


def build_r32(conn, verbose=False):
    """Construye el R32 con los clasificados del escenario determinista
    (simulate_group para A-L). Retorna lista de 16 tuplas
    (home_name, away_name, label, venue) en orden de cuadro."""
    firsts, seconds, thirds = {}, {}, []
    for g in GROUPS:
        sorted_teams, _ = simulate_group(g, conn=conn, verbose=False)
        firsts[g]  = sorted_teams[0]["name"]
        seconds[g] = sorted_teams[1]["name"]
        t3 = sorted_teams[2]
        thirds.append({
            "group": g, "name": t3["name"],
            "pts": t3["pts"], "dg": t3["gf"] - t3["ga"], "gf": t3["gf"],
            "elo": get_team(conn, t3["name"])["elo_rating"],
        })

    ranked = _rank_thirds(thirds)
    best8  = ranked[:8]

    third_slots = [(mid, set(seed_a.split(":")[1]))
                   for (mid, _, seed_a, _) in R32_TEMPLATE
                   if seed_a.startswith("3:")]
    third_assignment = _assign_thirds(best8, third_slots)

    if verbose:
        print("\n  Mejores 8 terceros (pts → DG → GF → ELO):")
        for t in ranked:
            mark = "Q" if t in best8 else " "
            print(f"   {mark} 3{t['group']} {t['name']:<16} "
                  f"pts={t['pts']} dg={t['dg']:+d} gf={t['gf']} elo={t['elo']:.0f}")

    matches = []
    for mid, seed_h, seed_a, venue in R32_TEMPLATE:
        home = firsts[seed_h[1]] if seed_h[0] == "1" else seconds[seed_h[1]]
        if seed_a.startswith("3:"):
            third = third_assignment[mid]
            away  = third["name"]
            label = f"{mid} | {seed_h} vs 3{third['group']} (de {seed_a[2:]})"
        else:
            away  = firsts[seed_a[1]] if seed_a[0] == "1" else seconds[seed_a[1]]
            label = f"{mid} | {seed_h} vs {seed_a}"
        matches.append((home, away, label, venue))
    return matches


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def name_es(team_dict):
    return team_dict.get("name_es") or team_dict["name"]


def _load_teams(conn, r32):
    teams = {}
    for home_name, away_name, _, _ in r32:
        for n in (home_name, away_name):
            if n not in teams:
                teams[n] = get_team(conn, n)
    return teams


def predict_ko_match(th, ta, factor=KO_FACTOR, venue=None):
    """Predicción determinista para partido eliminatorio. Retorna dict con winner.
    Sede del partido → host advantage + altitud activos en eliminatoria.
    Regla de decisión (v3.3): apuesta (marcador 90' + advancer) que MAXIMIZA
    los puntos esperados de la polla (best_bet_ko sobre la grilla 0..6).
    P(avanza local | empate en 90') se calcula con la matriz de prórroga
    (λ × ET_FACTOR); los penales del modelo son simétricos (76% conversión
    ambos lados) → cuentan 0.5 del empate en prórroga.
    Override manual (overrides.ko_override): fija marcador/advancer del
    escenario determinista y el EV se recalcula para la apuesta forzada;
    las probabilidades siguen siendo del modelo."""
    lh, la = compute_lambdas(th, ta, venue=venue)
    lh *= factor
    la *= factor
    matrix = score_matrix_dc(lh, la)

    prob_h = sum(p for (gh, ga), p in matrix.items() if gh > ga)
    prob_d = sum(p for (gh, ga), p in matrix.items() if gh == ga)
    prob_a = sum(p for (gh, ga), p in matrix.items() if gh < ga)

    # P(local avanza | empate en 90'): prórroga Dixon-Coles + penales simétricos
    met = score_matrix_dc(lh * ET_FACTOR, la * ET_FACTOR)
    p_et_h = sum(p for (gh, ga), p in met.items() if gh > ga)
    p_et_d = sum(p for (gh, ga), p in met.items() if gh == ga)
    p_home_adv_draw = p_et_h + 0.5 * p_et_d

    best, adv_side, exp_pts = best_bet_ko(matrix, p_home_adv_draw)

    # Override manual: fija la apuesta y recalcula su EV real
    ov = ko_override(th["name"], ta["name"])
    manual = ov is not None
    if manual:
        best = ov["score"]
        if best[0] == best[1]:
            if ov["advancer"] == th["name"]:
                adv_side = "home"
            elif ov["advancer"] == ta["name"]:
                adv_side = "away"
            else:
                # Empate sin advancer en el override → favorito por prórroga
                adv_side = "home" if p_home_adv_draw >= 0.5 else "away"
        else:
            adv_side = "home" if best[0] > best[1] else "away"
        exp_pts = expected_points_ko(matrix, p_home_adv_draw, best, adv_side)

    # Si la apuesta es empate, el advancer define quién avanza (prórroga/penales)
    if best[0] == best[1]:
        winner, went_et = (th if adv_side == "home" else ta), True
    else:
        winner, went_et = (th if best[0] > best[1] else ta), False

    return {
        "home": th, "away": ta,
        "score": best,
        "went_et": went_et,
        "prob_h": round(prob_h*100,1),
        "prob_d": round(prob_d*100,1),
        "prob_a": round(prob_a*100,1),
        "p_adv_home_draw": round(p_home_adv_draw*100, 1),
        "exp_pts": round(exp_pts, 2),
        "winner": winner,
        "advancer": winner["name"],
        "manual": manual,
        "venue": venue,
        "elo_diff": abs(th["elo_rating"] - ta["elo_rating"]),
    }


def _ko_sampling_dists(th, ta, venue, factor, cache=None):
    """Distribuciones Dixon-Coles (90' y prórroga) listas para muestrear:
    (scores_arr, cum90, cum_et). Cacheables por (home, away, venue)."""
    key = (th["name"], ta["name"], venue, factor)
    if cache is not None and key in cache:
        return cache[key]
    lh, la = compute_lambdas(th, ta, venue=venue)
    lh *= factor
    la *= factor
    m90 = score_matrix_dc(lh, la)
    met = score_matrix_dc(lh * ET_FACTOR, la * ET_FACTOR)
    scores = list(m90.keys())
    scores_arr = np.array(scores, dtype=np.int32)
    cum90 = np.cumsum(np.array([m90[s] for s in scores], dtype=np.float64))
    cum_et = np.cumsum(np.array([met[s] for s in scores], dtype=np.float64))
    cum90 /= cum90[-1]
    cum_et /= cum_et[-1]
    dists = (scores_arr, cum90, cum_et)
    if cache is not None:
        cache[key] = dists
    return dists


def sim_ko_match_mc(th, ta, rng, factor=KO_FACTOR, venue=None, cache=None):
    """Simula un partido eliminatorio (90' → ET → pen). Retorna dict del ganador.
    Muestrea desde la distribución conjunta Dixon-Coles (score_matrix_dc),
    consistente con el motor analítico, tanto en 90' como en prórroga
    (λ escalados por ET_FACTOR)."""
    scores_arr, cum90, cum_et = _ko_sampling_dists(th, ta, venue, factor, cache)

    # 90 minutos (Dixon-Coles)
    idx = int(np.searchsorted(cum90, rng.random(), side="right"))
    gh, ga = int(scores_arr[idx, 0]), int(scores_arr[idx, 1])
    if gh != ga:
        return th if gh > ga else ta

    # Prórroga (Dixon-Coles con λ × ET_FACTOR)
    idx = int(np.searchsorted(cum_et, rng.random(), side="right"))
    gh += int(scores_arr[idx, 0])
    ga += int(scores_arr[idx, 1])
    if gh != ga:
        return th if gh > ga else ta

    # Penaltis (5 tiros cada uno, luego muerte súbita) — 76% conversión
    ph = int(np.sum(rng.random(5) < PEN_CONV))
    pa = int(np.sum(rng.random(5) < PEN_CONV))
    while ph == pa:
        ph += int(rng.random() < PEN_CONV)
        pa += int(rng.random() < PEN_CONV)
    return th if ph > pa else ta


# ---------------------------------------------------------------------------
# Predicción determinista del bracket completo
# ---------------------------------------------------------------------------
def bracket_deterministic(conn, r32=None):
    if r32 is None:
        r32 = build_r32(conn, verbose=True)
    teams = _load_teams(conn, r32)

    print("\n" + "="*70)
    print("  BRACKET ELIMINATORIO — PREDICCIONES DETERMINISTAS  (λ×0.90)")
    print("  Seeds: escenario determinista de fase de grupos (simulate_group)")
    print("="*70)

    # R32
    print("\n─── DIECISEISAVOS DE FINAL (R32) ────────────────────────────────────")
    r32_winners = []
    for home_name, away_name, label, venue in r32:
        r = predict_ko_match(teams[home_name], teams[away_name], venue=venue)
        gh, ga = r["score"]
        h_es = name_es(r["home"])
        a_es = name_es(r["away"])
        w_es = name_es(r["winner"])
        # Empate en 90' → avanza por prórroga/penales: el sufijo lo deja claro
        suffix = f" (pen: {w_es})" if r["went_et"] else ""
        manual_tag = " [manual]" if r["manual"] else ""
        print(f"  [{label:28s}] {venue:<17} {h_es:18} {gh}-{ga}{suffix} {a_es:18}  "
              f"{r['prob_h']}%/{r['prob_d']}%/{r['prob_a']}%  EV={r['exp_pts']:.2f}"
              f"  → {w_es}{manual_tag}")
        r32_winners.append(r["winner"]["name"])

    # R16 → Final
    current = r32_winners
    for round_key in ("R16", "QF", "SF", "Final"):
        label_str = ROUND_LABELS[round_key]
        print(f"\n─── {label_str} {'─'*(60-len(label_str))}")
        next_round = []
        for i, (idx_a, idx_b) in enumerate(ADVANCEMENT[round_key]):
            hn, an = current[idx_a], current[idx_b]
            venue = ROUND_VENUES[round_key][i]
            r = predict_ko_match(teams[hn], teams[an], venue=venue)
            gh, ga = r["score"]
            h_es = name_es(r["home"])
            a_es = name_es(r["away"])
            w_es = name_es(r["winner"])
            suffix = f" (pen: {w_es})" if r["went_et"] else ""
            manual_tag = " [manual]" if r["manual"] else ""
            print(f"  {venue:<17} {h_es:20} {gh}-{ga}{suffix}  {a_es:20}  "
                  f"{r['prob_h']}%/{r['prob_d']}%/{r['prob_a']}%  EV={r['exp_pts']:.2f}"
                  f"  → {w_es}{manual_tag}")
            next_round.append(r["winner"]["name"])
        current = next_round

    champion_name = current[0]
    champion_es   = name_es(teams[champion_name])
    print(f"\n{'='*70}")
    print(f"  🏆  CAMPEÓN PREDICHO: {champion_es}  (ELO {teams[champion_name]['elo_rating']:.0f})")
    print(f"{'='*70}")
    return champion_name


# ---------------------------------------------------------------------------
# Monte Carlo del bracket completo
# ---------------------------------------------------------------------------
def bracket_mc(conn, n_sims=N_SIMS_MC, r32=None):
    if r32 is None:
        r32 = build_r32(conn)
    teams = _load_teams(conn, r32)

    champion_counts = {n: 0 for n in teams}
    rng = np.random.default_rng(seed=2026)
    cache = {}  # distribuciones DC por (home, away, venue)

    r32_venues = [venue for (_, _, _, venue) in r32]

    for _ in range(n_sims):
        # R32
        current = []
        for (home_name, away_name, _, venue) in r32:
            w = sim_ko_match_mc(teams[home_name], teams[away_name], rng,
                                venue=venue, cache=cache)
            current.append(w["name"])

        # R16 → Final
        for round_key in ("R16", "QF", "SF", "Final"):
            next_round = []
            for i, (idx_a, idx_b) in enumerate(ADVANCEMENT[round_key]):
                hn, an = current[idx_a], current[idx_b]
                w = sim_ko_match_mc(teams[hn], teams[an], rng,
                                    venue=ROUND_VENUES[round_key][i], cache=cache)
                next_round.append(w["name"])
            current = next_round

        champion_counts[current[0]] = champion_counts.get(current[0], 0) + 1

    return {n: round(c/n_sims*100, 1) for n, c in champion_counts.items()}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _format_mc_odds(mc_probs, teams):
    """Formatea las probabilidades de campeón del Monte Carlo para el dashboard."""
    return sorted(
        [{"name": n, "name_es": name_es(teams.get(n, {"name_es": n, "name": n})),
          "prob": p, "elo": teams[n]["elo_rating"] if n in teams else 0}
         for n, p in mc_probs.items() if p >= 0.3],
        key=lambda x: -x["prob"]
    )


def compute_mc_odds(conn, n_sims=N_SIMS_MC, r32=None):
    """Monte Carlo del bracket → lista ordenada de probabilidades de campeón.
    Reutilizable por app.py para cachear el cálculo caro (el MC del bracket)
    y refrescarlo bajo demanda con el R32 vigente (overrides incluidos)."""
    if r32 is None:
        r32 = build_r32(conn)
    teams = _load_teams(conn, r32)
    mc_probs = bracket_mc(conn, n_sims=n_sims, r32=r32)
    return _format_mc_odds(mc_probs, teams)


def get_bracket_data(conn, n_sims=N_SIMS_MC, mc_odds=None):
    """Retorna datos estructurados del bracket para el dashboard (sin prints).
    Formato: {"rounds": {...}, "champion": str, "champion_es": str, "mc_odds": [...]}
    mc_odds: lista precalculada (cache de app.py). Si es None se corre el
    Monte Carlo completo del bracket (la parte cara)."""
    r32 = build_r32(conn)
    teams = _load_teams(conn, r32)

    rounds_data = {}

    # R32
    r32_matches, current = [], []
    for idx, (home_name, away_name, label, venue) in enumerate(r32):
        r = predict_ko_match(teams[home_name], teams[away_name], venue=venue)
        gh, ga = r["score"]
        winner_name = r["winner"]["name"]
        r32_matches.append({
            "home": home_name, "home_es": name_es(teams[home_name]),
            "away": away_name, "away_es": name_es(teams[away_name]),
            "score": f"{gh}-{ga}", "went_et": r["went_et"],
            "prob_h": r["prob_h"], "prob_d": r["prob_d"], "prob_a": r["prob_a"],
            "winner": winner_name, "winner_es": name_es(r["winner"]),
            "exp_pts": r["exp_pts"],
            "advancer": r["advancer"], "advancer_es": name_es(r["winner"]),
            "manual": r["manual"],
            "match_num": idx + 1,
            "label": label, "venue": venue,
        })
        current.append(winner_name)
    rounds_data["R32"] = r32_matches

    for round_key in ("R16", "QF", "SF", "Final"):
        matches, next_round = [], []
        for i, (idx_a, idx_b) in enumerate(ADVANCEMENT[round_key]):
            hn, an = current[idx_a], current[idx_b]
            venue = ROUND_VENUES[round_key][i]
            r = predict_ko_match(teams[hn], teams[an], venue=venue)
            gh, ga = r["score"]
            winner_name = r["winner"]["name"]
            matches.append({
                "home": hn, "home_es": name_es(teams[hn]),
                "away": an, "away_es": name_es(teams[an]),
                "score": f"{gh}-{ga}", "went_et": r["went_et"],
                "prob_h": r["prob_h"], "prob_d": r["prob_d"], "prob_a": r["prob_a"],
                "winner": winner_name, "winner_es": name_es(r["winner"]),
                "exp_pts": r["exp_pts"],
                "advancer": r["advancer"], "advancer_es": name_es(r["winner"]),
                "manual": r["manual"],
                "venue": venue,
            })
            next_round.append(winner_name)
        rounds_data[round_key] = matches
        current = next_round

    champion = current[0]

    # Monte Carlo (mismo R32 derivado, mismas sedes) — se omite si app.py
    # entrega mc_odds precalculado (cache del server interactivo).
    if mc_odds is None:
        mc_probs = bracket_mc(conn, n_sims=n_sims, r32=r32)
        mc_odds = _format_mc_odds(mc_probs, teams)

    return {
        "rounds": rounds_data,
        "champion": champion,
        "champion_es": name_es(teams.get(champion, {"name_es": champion})),
        "mc_odds": mc_odds,
    }


def main():
    print("Inicializando DB y datos...")
    regenerate_db()
    conn = sqlite3.connect(DB_PATH)

    print("\nDerivando clasificados (escenario determinista por grupo)...")
    r32 = build_r32(conn, verbose=True)

    champion = bracket_deterministic(conn, r32=r32)

    print(f"\nMonte Carlo ({N_SIMS_MC:,} simulaciones)...")
    probs = bracket_mc(conn, n_sims=N_SIMS_MC, r32=r32)

    try:
        teams_cache = {}
        for n in probs:
            try:
                teams_cache[n] = get_team(conn, n)
            except Exception:
                teams_cache[n] = {"name_es": n, "elo_rating": 0}
    except Exception:
        teams_cache = {}

    sorted_teams = sorted(probs.items(), key=lambda x: -x[1])
    print("\n─── PROBABILIDAD DE CAMPEÓN (Monte Carlo) ─────────────────────────")
    print(f"  {'Equipo':<25} {'P(Campeón)':>12}  {'ELO':>6}")
    print(f"  {'─'*48}")
    for name, prob in sorted_teams:
        if prob >= 0.3:
            td = teams_cache.get(name, {})
            es = td.get("name_es") or name
            elo = td.get("elo_rating", 0)
            bar = "█" * int(prob / 2)
            print(f"  {es:<25} {prob:>10.1f}%  {elo:>6.0f}  {bar}")

    conn.close()
    print("\nListo.")


if __name__ == "__main__":
    main()
