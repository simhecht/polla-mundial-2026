"""
simulate_knockout.py — Fase eliminatoria Mundial 2026
Bracket FIFA 2026 oficial (R32 → R16 → QF → SF → Final).
Annex C aplicado para combinación de terceros B,C,D,E,F,G,I,L.
λ × 0.90 para todos los partidos eliminatorios.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3, math
import numpy as np
from predictor_v3 import (
    get_team, compute_lambdas, score_matrix_dc, best_score_result_first,
    DB_PATH, regenerate_db
)

# ---------------------------------------------------------------------------
# Parámetros
# ---------------------------------------------------------------------------
KO_FACTOR    = 0.90   # λ × 0.90 en eliminatoria (partidos más cerrados)
ET_FACTOR    = 0.50   # λ × KO × ET_FACTOR para tiempo extra (30 min ≈ 50% de 60 min)
PEN_CONV     = 0.76   # conversión penalti élite
N_SIMS_MC    = 20_000

# ---------------------------------------------------------------------------
# Bracket R32 — 16 partidos en orden de cuadro
# (local, visitante, etiqueta)
# Sección A → QF1, Sección B → QF2, Sección C → QF3, Sección D → QF4
# ---------------------------------------------------------------------------
R32 = [
    # --- Sección A (→ QF1) ---
    ("Germany",       "Bosnia",        "M01 | 1E vs 3BCDF"),   # Alemania vs Bosnia
    ("France",        "Australia",     "M02 | 1I vs 3CDFG"),   # Francia vs Australia
    ("South Korea",   "Switzerland",   "M03 | 2A vs 2B"),      # Corea del Sur vs Suiza
    ("Netherlands",   "Morocco",       "M04 | 1F vs 2C"),      # Países Bajos vs Marruecos
    # --- Sección B (→ QF2) ---
    ("Colombia",      "Croatia",       "M05 | 2K vs 2L"),      # Colombia vs Croacia
    ("Spain",         "Austria",       "M06 | 1H vs 2J"),      # España vs Austria
    ("USA",           "Sweden",        "M07 | 1D vs 3BEFI"),   # USA vs Suecia
    ("Belgium",       "Ivory Coast",   "M08 | 1G vs 3AEHI"),   # Bélgica vs C. de Marfil
    # --- Sección C (→ QF3) ---
    ("Brazil",        "Japan",         "M09 | 1C vs 2F"),      # Brasil vs Japón
    ("Ecuador",       "Norway",        "M10 | 2E vs 2I"),      # Ecuador vs Noruega
    ("Mexico",        "Scotland",      "M11 | 1A vs 3CEFI"),   # México vs Escocia
    ("England",       "Senegal",       "M12 | 1L vs 3EHIJ"),   # Inglaterra vs Senegal
    # --- Sección D (→ QF4) ---
    ("Argentina",     "Uruguay",       "M13 | 1J vs 2H"),      # Argentina vs Uruguay
    ("Turkey",        "Egypt",         "M14 | 2D vs 2G"),      # Turquía vs Egipto
    ("Canada",        "Iran",          "M15 | 1B vs 3EFGI"),   # Canadá vs Irán
    ("Portugal",      "Panama",        "M16 | 1K vs 3DEIL"),   # Portugal vs Panamá
]

# Cómo avanzan los ganadores de R32 → R16 → QF → SF → Final
# Cada tupla es (índice_match_A, índice_match_B) de la ronda anterior
ADVANCEMENT = {
    "R16":   [(0,1),(2,3),(4,5),(6,7),(8,9),(10,11),(12,13),(14,15)],
    "QF":    [(0,1),(2,3),(4,5),(6,7)],
    "SF":    [(0,1),(2,3)],
    "Final": [(0,1)],
}

ROUND_LABELS = {
    "R16":   "OCTAVOS (R16)",
    "QF":    "CUARTOS DE FINAL",
    "SF":    "SEMIFINALES",
    "Final": "FINAL",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def name_es(team_dict):
    return team_dict.get("name_es") or team_dict["name"]


def predict_ko_match(th, ta, factor=KO_FACTOR):
    """Predicción determinista para partido eliminatorio. Retorna dict con winner."""
    lh, la = compute_lambdas(th, ta)
    lh *= factor
    la *= factor
    matrix = score_matrix_dc(lh, la)

    prob_h = sum(p for (gh, ga), p in matrix.items() if gh > ga)
    prob_d = sum(p for (gh, ga), p in matrix.items() if gh == ga)
    prob_a = sum(p for (gh, ga), p in matrix.items() if gh < ga)
    best   = best_score_result_first(matrix)

    # Determinar ganador a partir del marcador elegido (result-first v3.2)
    if best[0] == best[1]:
        # Empate en 90' → prórroga; avanza el favorito
        winner = th if prob_h >= prob_a else ta
    else:
        winner = th if best[0] > best[1] else ta

    return {
        "home": th, "away": ta,
        "score": best,
        "prob_h": round(prob_h*100,1),
        "prob_d": round(prob_d*100,1),
        "prob_a": round(prob_a*100,1),
        "winner": winner,
        "elo_diff": abs(th["elo_rating"] - ta["elo_rating"]),
    }


def sim_ko_match_mc(th, ta, rng, factor=KO_FACTOR):
    """Simula un partido eliminatorio (90' → ET → pen). Retorna dict del ganador."""
    lh, la = compute_lambdas(th, ta)
    lh *= factor
    la *= factor

    # 90 minutos
    gh = rng.poisson(lh)
    ga = rng.poisson(la)
    if gh != ga:
        return th if gh > ga else ta

    # Tiempo extra (30 min ≈ KO_FACTOR × ET_FACTOR)
    gh += rng.poisson(lh * ET_FACTOR)
    ga += rng.poisson(la * ET_FACTOR)
    if gh != ga:
        return th if gh > ga else ta

    # Penaltis (5 tiros cada uno, luego muerte súbita)
    ph = int(np.sum(rng.random(5) < PEN_CONV))
    pa = int(np.sum(rng.random(5) < PEN_CONV))
    while ph == pa:
        ph += int(rng.random() < PEN_CONV)
        pa += int(rng.random() < PEN_CONV)
    return th if ph > pa else ta


# ---------------------------------------------------------------------------
# Predicción determinista del bracket completo
# ---------------------------------------------------------------------------
def bracket_deterministic(conn):
    # Precargar equipos
    teams = {}
    for home_name, away_name, _ in R32:
        for n in (home_name, away_name):
            if n not in teams:
                teams[n] = get_team(conn, n)

    print("\n" + "="*70)
    print("  BRACKET ELIMINATORIO — PREDICCIONES DETERMINISTAS  (λ×0.90)")
    print("="*70)

    # R32
    print("\n─── DIECISEISAVOS DE FINAL (R32) ────────────────────────────────────")
    r32_winners = []
    for i, (home_name, away_name, label) in enumerate(R32):
        r = predict_ko_match(teams[home_name], teams[away_name])
        gh, ga = r["score"]
        suffix = "(ET)" if gh == ga else ""
        marker = "→"
        h_es = name_es(r["home"])
        a_es = name_es(r["away"])
        w_es = name_es(r["winner"])
        print(f"  [{label:20s}]  {h_es:22} {gh}-{ga}{suffix} {a_es:22}  "
              f"{r['prob_h']}%/{r['prob_d']}%/{r['prob_a']}%  {marker} {w_es}")
        r32_winners.append(r["winner"]["name"])

    # R16 → Final
    current = r32_winners
    for round_key in ("R16", "QF", "SF", "Final"):
        label_str = ROUND_LABELS[round_key]
        print(f"\n─── {label_str} {'─'*(60-len(label_str))}")
        pairs = ADVANCEMENT[round_key]
        next_round = []
        for idx_a, idx_b in pairs:
            hn, an = current[idx_a], current[idx_b]
            r = predict_ko_match(teams[hn], teams[an])
            gh, ga = r["score"]
            suffix = "(ET)" if gh == ga else ""
            h_es = name_es(r["home"])
            a_es = name_es(r["away"])
            w_es = name_es(r["winner"])
            print(f"  {h_es:22} {gh}-{ga}{suffix}  {a_es:22}  "
                  f"{r['prob_h']}%/{r['prob_d']}%/{r['prob_a']}%  → {w_es}")
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
def bracket_mc(conn, n_sims=N_SIMS_MC):
    teams = {}
    for home_name, away_name, _ in R32:
        for n in (home_name, away_name):
            if n not in teams:
                teams[n] = get_team(conn, n)

    champion_counts = {n: 0 for n in teams}
    rng = np.random.default_rng(seed=2026)

    for _ in range(n_sims):
        # R32
        current = []
        for home_name, away_name, _ in R32:
            w = sim_ko_match_mc(teams[home_name], teams[away_name], rng)
            current.append(w["name"])

        # R16 → Final
        for round_key in ("R16", "QF", "SF", "Final"):
            next_round = []
            for idx_a, idx_b in ADVANCEMENT[round_key]:
                hn, an = current[idx_a], current[idx_b]
                w = sim_ko_match_mc(teams[hn], teams[an], rng)
                next_round.append(w["name"])
            current = next_round

        champion_counts[current[0]] = champion_counts.get(current[0], 0) + 1

    return {n: round(c/n_sims*100, 1) for n, c in champion_counts.items()}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def get_bracket_data(conn, n_sims=N_SIMS_MC):
    """Retorna datos estructurados del bracket para el dashboard (sin prints)."""
    teams = {}
    for home_name, away_name, _ in R32:
        for n in (home_name, away_name):
            if n not in teams:
                teams[n] = get_team(conn, n)

    rounds_data = {}

    # R32
    r32_matches, current = [], []
    for idx, (home_name, away_name, label) in enumerate(R32):
        r = predict_ko_match(teams[home_name], teams[away_name])
        gh, ga = r["score"]
        winner_name = r["winner"]["name"]
        r32_matches.append({
            "home": home_name, "home_es": name_es(teams[home_name]),
            "away": away_name, "away_es": name_es(teams[away_name]),
            "score": f"{gh}-{ga}", "went_et": gh == ga,
            "prob_h": r["prob_h"], "prob_d": r["prob_d"], "prob_a": r["prob_a"],
            "winner": winner_name, "winner_es": name_es(r["winner"]),
            "match_num": idx + 1,
        })
        current.append(winner_name)
    rounds_data["R32"] = r32_matches

    for round_key in ("R16", "QF", "SF", "Final"):
        matches, next_round = [], []
        for idx_a, idx_b in ADVANCEMENT[round_key]:
            hn, an = current[idx_a], current[idx_b]
            r = predict_ko_match(teams[hn], teams[an])
            gh, ga = r["score"]
            winner_name = r["winner"]["name"]
            matches.append({
                "home": hn, "home_es": name_es(teams[hn]),
                "away": an, "away_es": name_es(teams[an]),
                "score": f"{gh}-{ga}", "went_et": gh == ga,
                "prob_h": r["prob_h"], "prob_d": r["prob_d"], "prob_a": r["prob_a"],
                "winner": winner_name, "winner_es": name_es(r["winner"]),
            })
            next_round.append(winner_name)
        rounds_data[round_key] = matches
        current = next_round

    champion = current[0]

    # Monte Carlo
    mc_probs = bracket_mc(conn, n_sims=n_sims)
    mc_odds = sorted(
        [{"name": n, "name_es": name_es(teams.get(n, {"name_es": n, "name": n})),
          "prob": p, "elo": teams[n]["elo_rating"] if n in teams else 0}
         for n, p in mc_probs.items() if p >= 0.3],
        key=lambda x: -x["prob"]
    )

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

    champion = bracket_deterministic(conn)

    print(f"\nMonte Carlo ({N_SIMS_MC:,} simulaciones)...")
    probs = bracket_mc(conn, n_sims=N_SIMS_MC)

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
