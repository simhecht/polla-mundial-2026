"""
Evaluación post-torneo: el modelo PRE-Mundial vs los 104 resultados reales.

- Modelo puro: se ignoran results.json y overrides.json, así que cada
  predicción es la que el modelo habría hecho antes del 11 jun 2026
  (setup_db/predictor_v3 no cambiaron después del inicio del torneo).
- KO: se predice el cruce REAL que se jugó (en la polla se apuesta partido a
  partido), con la sede real. Marcador a 90' + quién avanza.
- Resultados reales: data/wc2026_real.json (openfootball/worldcup.json,
  verificado contra martj42/international_results: 104/104 coinciden).

Uso: python3 evaluate.py   → imprime y escribe ../EVALUACION.md
"""
import contextlib, io, json, math, os, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import overrides, results
_NONE = os.path.join(results.DATA_DIR, "__sin_datos__.json")
results.RESULTS_PATH = overrides.OVERRIDES_PATH = _NONE   # modelo puro

import setup_db
from predictor_v3 import DB_PATH, get_team, predict_match
from simulate_knockout import build_r32, bracket_deterministic, bracket_mc, predict_ko_match
from polla_points import points_group, points_ko

HERE = os.path.dirname(os.path.abspath(__file__))
REAL = json.load(open(os.path.join(HERE, "data", "wc2026_real.json"), encoding="utf-8"))
OUT_MD = os.path.join(HERE, "..", "EVALUACION.md")
STAGE_ES = {"R32": "Dieciseisavos", "R16": "Octavos", "QF": "Cuartos", "SF": "Semifinal",
            "3P": "Tercer puesto", "Final": "Final"}


def sign(h, a):
    return (h > a) - (h < a)          # 1 local, 0 empate, -1 visita


def side(score, advancer, home):
    if score[0] != score[1]:
        return "home" if score[0] > score[1] else "away"
    return "home" if advancer == home else "away"


def evaluate(conn):
    rows = []
    for e in REAL:
        h, a, ft = e["home"], e["away"], tuple(e["ft"])
        ko = "advancer" in e
        th, ta = get_team(conn, h), get_team(conn, a)
        if ko:
            r = predict_ko_match(th, ta, venue=e["venue"])
            p = (r["prob_h"], r["prob_d"], r["prob_a"])
            bet, bet_side = tuple(r["score"]), side(r["score"], r["advancer"], h)
            real_side = side(ft, e["advancer"], h)
            pts = points_ko(bet, bet_side, ft, real_side)
            fav_side = "home" if th["elo_rating"] >= ta["elo_rating"] else "away"
            base_bet = (1, 0) if fav_side == "home" else (0, 1)
            base = points_ko(base_bet, fav_side, ft, real_side)
            adv_ok = bet_side == real_side
        else:
            r = predict_match(h, a, conn=conn, verbose=False)
            p = (r["prob_home_win"], r["prob_draw"], r["prob_away_win"])
            bet = tuple(r["best_score"])
            pts = points_group(bet, ft)
            base_bet = (1, 0) if th["elo_rating"] >= ta["elo_rating"] else (0, 1)
            base = points_group(base_bet, ft)
            adv_ok = None
        p = [x / 100 for x in p]
        outcome = {1: 0, 0: 1, -1: 2}[sign(*ft)]
        rows.append({
            **e, "ko": ko, "bet": bet, "p": p, "pts": pts, "base": base, "adv_ok": adv_ok,
            "hit_1x2": max(range(3), key=lambda i: p[i]) == outcome,
            "exact": bet == ft,
            "brier": sum((p[i] - (i == outcome)) ** 2 for i in range(3)),
            "logloss": -math.log(max(p[outcome], 1e-9)),
            "h_es": th["name_es"] or h, "a_es": ta["name_es"] or a,
        })
    return rows


def summary(rows):
    n = len(rows)
    return {
        "n": n,
        "hit": sum(r["hit_1x2"] for r in rows),
        "exact": sum(r["exact"] for r in rows),
        "brier": sum(r["brier"] for r in rows) / n,
        "logloss": sum(r["logloss"] for r in rows) / n,
        "pts": sum(r["pts"] for r in rows),
        "base": sum(r["base"] for r in rows),
    }


def user_group_points(rows):
    """Puntos con las apuestas que de verdad se jugaron (results.json, con overrides)."""
    with open(os.path.join(results.DATA_DIR, "results.json"), encoding="utf-8") as f:
        played = json.load(f)["groups"]
    real = {frozenset((r["home"], r["away"])): r for r in rows if not r["ko"]}
    total = 0
    for g in played:
        r = real[frozenset((g["home"], g["away"]))]
        ft = tuple(r["ft"]) if r["home"] == g["home"] else tuple(r["ft"][::-1])
        total += points_group(tuple(g["bet"]), ft)
    return total, len(played)


def pretournament_bracket(conn):
    with contextlib.redirect_stdout(io.StringIO()):
        r32 = build_r32(conn)
        champ = bracket_deterministic(conn, r32=r32)
    mc = bracket_mc(conn, n_sims=20_000, r32=r32)
    pred_q = {t for m in r32 for t in m[:2]}
    real_q = {t for e in REAL if e["stage"] == "R32" for t in (e["home"], e["away"])}
    return pred_q, real_q, champ, mc


def fmt_table(head, body):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
                     + ["| " + " | ".join(map(str, b)) + " |" for b in body])


def report(rows, conn):
    grp, ko = [r for r in rows if not r["ko"]], [r for r in rows if r["ko"]]
    S = {"Grupos (72)": summary(grp), "Eliminatoria (32)": summary(ko), "Total (104)": summary(rows)}
    user_pts, user_n = user_group_points(rows)
    pred_q, real_q, champ, mc = pretournament_bracket(conn)
    real_champ = next(e["advancer"] for e in REAL if e["stage"] == "Final")
    rank = sorted(mc, key=lambda t: -mc[t])
    name = lambda t: get_team(conn, t)["name_es"] or t
    adv_ok = sum(r["adv_ok"] for r in ko)

    md = ["# Evaluación post-torneo — Mundial 2026",
          "",
          "_Generado por `modelo/evaluate.py`. Modelo v3.5 **pre-torneo** (sin resultados reales ni "
          "overrides) contra los 104 partidos reales. En eliminatoria se predice el cruce que realmente "
          "se jugó, con marcador a 90'. Fuente: openfootball/worldcup.json, verificada contra "
          "martj42/international_results._",
          "",
          "## Resumen",
          "",
          fmt_table(
              ["Fase", "Partidos", "1X2 acertado", "Marcador exacto", "Brier", "Log loss",
               "Puntos polla", "Baseline 1-0 favorito ELO"],
              [[k, s["n"], f"{s['hit']} ({s['hit']/s['n']:.0%})", f"{s['exact']} ({s['exact']/s['n']:.0%})",
                f"{s['brier']:.3f}", f"{s['logloss']:.3f}", f"{s['pts']} ({s['pts']/s['n']:.2f}/partido)",
                f"{s['base']} ({s['base']/s['n']:.2f}/partido)"] for k, s in S.items()]),
          "",
          f"- Referencia sin información (1/3 cada resultado): Brier 0.667, log loss {math.log(3):.3f}.",
          f"- Eliminatoria: el modelo acertó quién avanzaba en **{adv_ok}/{len(ko)}** cruces.",
          f"- Apuestas reales jugadas en grupos (modelo + overrides manuales, `results.json`): "
          f"**{user_pts} pts** en {user_n} partidos, vs **{S['Grupos (72)']['pts']} pts** del modelo puro.",
          "",
          "## Proyección pre-torneo",
          "",
          f"- Clasificados a dieciseisavos acertados: **{len(pred_q & real_q)}/32**.",
          f"- Campeón del escenario determinista: **{name(champ)}**. Campeón real: **{name(real_champ)}**.",
          f"- Monte Carlo pre-torneo (20.000 simulaciones): {name(real_champ)} tenía "
          f"**{mc.get(real_champ, 0):.1f}%** (puesto {rank.index(real_champ) + 1 if real_champ in rank else '—'} de {len(rank)}).",
          "- Top 5 del Monte Carlo: " + ", ".join(f"{name(t)} {mc[t]:.1f}%" for t in rank[:5]) + ".",
          "",
          "## Eliminatoria, partido a partido",
          "",
          fmt_table(["Ronda", "Partido", "L / E / V (%)", "Apuesta modelo", "Real 90'", "Avanzó", "Pts"],
                    [[STAGE_ES[r["stage"]], f"{r['h_es']} vs {r['a_es']}",
                      " / ".join(f"{x*100:.0f}" for x in r["p"]),
                      f"{r['bet'][0]}-{r['bet'][1]}", f"{r['ft'][0]}-{r['ft'][1]}",
                      name(r["advancer"]) + ("" if r["adv_ok"] else " ✗"), r["pts"]] for r in ko]),
          ""]
    return "\n".join(md)


if __name__ == "__main__":
    with contextlib.redirect_stdout(io.StringIO()):
        setup_db.setup()
    conn = sqlite3.connect(DB_PATH)
    md = report(evaluate(conn), conn)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
