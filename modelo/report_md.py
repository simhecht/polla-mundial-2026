"""Regenera las secciones 4-6b de ESTADO_PROYECTO.md desde el modelo actual.

Uso (desde modelo/):
    python3 report_md.py              # actualiza ESTADO_PROYECTO.md (MC 20.000 sims)
    python3 report_md.py --n-sims 5000
    python3 report_md.py --dry-run    # imprime el markdown sin tocar el documento

Evita que las tablas del documento queden obsoletas tras cada cambio del modelo:
las secciones se reemplazan in-place entre los encabezados "## 4." y "## 7.".
"""
import argparse
import datetime
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from predictor_v3 import DB_PATH, get_team, simulate_group
from simulate_knockout import GROUPS, get_bracket_data, _rank_thirds
from dashboard import FLAG_EMOJIS

ESTADO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ESTADO_PROYECTO.md")
ROUND_TITLES = [("R32", "Dieciseisavos de final (R32)"), ("R16", "Octavos de final (R16)"),
                ("QF", "Cuartos de final"), ("SF", "Semifinales"), ("Final", "Final")]


def flag(raw_name):
    return FLAG_EMOJIS.get(raw_name, "🏳")


def fmt_score(m):
    pen = f" (pen: {m['advancer_es']})" if m["went_et"] else ""
    manual = " ✏️" if m.get("manual") else ""
    return f"{m['score']}{pen}{manual}"


def section_groups(conn):
    lines, qualified = [], {}
    for g in GROUPS:
        standings, results = simulate_group(g, conn=conn, verbose=False)
        qualified[g] = standings
        lines.append(f"### GRUPO {g}")
        lines.append("| Equipo | G | E | P | GF | GC | DG | PTS |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for i, t in enumerate(standings):
            name = f"{flag(t['name'])} **{t['name_es']}** ✅" if i < 2 else f"{flag(t['name'])} {t['name_es']}"
            pts = f"**{t['pts']}**" if i < 2 else str(t["pts"])
            lines.append(f"| {name} | {t['w']} | {t['d']} | {t['l']} | {t['gf']} | {t['ga']} "
                         f"| {t['gf']-t['ga']:+d} | {pts} |".replace("+0", "0"))
        partidos = " | ".join(
            f"{r['home']} {r['score']}{' ✏️' if r.get('manual') else ''} {r['away']} (EV {r['exp_pts']})"
            for r in results)
        lines.append("")
        lines.append(f"Partidos: {partidos}")
        lines.append("")
    return lines, qualified


def section_qualifiers(conn, qualified):
    lines = ["## 5. Los 32 clasificados a Dieciseisavos", "",
             "### Clasificados directos (24 = 2 por grupo):",
             "| Grupo | 1° | 2° |", "|---|---|---|"]
    thirds = []
    for g in GROUPS:
        st = qualified[g]
        lines.append(f"| {g} | {flag(st[0]['name'])} {st[0]['name_es']} | {flag(st[1]['name'])} {st[1]['name_es']} |")
        t3 = st[2]
        thirds.append({"group": g, "name": t3["name"], "name_es": t3["name_es"], "pts": t3["pts"],
                       "dg": t3["gf"] - t3["ga"], "gf": t3["gf"],
                       "elo": get_team(conn, t3["name"])["elo_rating"]})
    ranked = _rank_thirds(thirds)
    lines += ["", "### Mejores 8 terceros (ranking por pts → DG → GF → ELO):",
              "| Pos | Equipo | Grupo | Pts | DG | GF | ELO |", "|---|---|---|---|---|---|---|"]
    for i, t in enumerate(ranked[:8]):
        lines.append(f"| {i+1} ✅ | {flag(t['name'])} {t['name_es']} | {t['group']} | {t['pts']} "
                     f"| {t['dg']:+d} | {t['gf']} | {t['elo']:.0f} |".replace("+0", "0"))
    out = ", ".join(f"{t['name_es']} ({t['group']}, DG={t['dg']:+d}, GF={t['gf']}, ELO={t['elo']:.0f})"
                    for t in ranked[8:])
    lines += ["", f"**Eliminados (4 terceros que no clasifican):** {out}", ""]
    return lines


def section_bracket(bracket):
    lines = ["## 6. Bracket eliminatorio (escenario determinista — apuesta EV)", ""]
    for key, title in ROUND_TITLES:
        matches = bracket["rounds"][key]
        lines.append(f"### {title}")
        cols = "| Partido | Sede |" if key == "R32" else "| Sede |"
        lines.append(cols + " Local | Marcador | Visitante | Probs L/E/V | EV | Avanza |")
        lines.append("|---|---|---|---|---|---|---|" + ("---|" if key == "R32" else ""))
        for m in matches:
            pre = f"| {m['label'].split(' (')[0]} | {m['venue']} |" if key == "R32" else f"| {m['venue']} |"
            lines.append(f"{pre} {flag(m['home'])} {m['home_es']} | {fmt_score(m)} | {flag(m['away'])} {m['away_es']} "
                         f"| {m['prob_h']}%/{m['prob_d']}%/{m['prob_a']}% | {m['exp_pts']} | **{m['winner_es']}** |")
        lines.append("")
    lines.append(f"**🏆 Campeón predicho: {bracket['champion_es']}**")
    lines.append("")
    return lines


def section_mc(bracket, n_sims):
    lines = [f"## 6b. Probabilidades Monte Carlo ({n_sims:,} sims)".replace(",", "."), "",
             "| Equipo | P(Campeón) | ELO |", "|---|---|---|"]
    for t in bracket["mc_odds"]:
        lines.append(f"| {flag(t['name'])} {t['name_es']} | {t['prob']:.1f}% | {t['elo']:.0f} |")
    lines.append("")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-sims", type=int, default=20000)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(DB_PATH)
    fecha = datetime.date.today().strftime("%-d %B %Y")
    header = [f"## 4. Resultados fase de grupos (escenario determinista — apuesta EV)", "",
              f"_(Secciones 4-6b autogeneradas por `modelo/report_md.py` — {fecha}. "
              "EV = puntos esperados de la apuesta según el reglamento de la polla; "
              "✏️ = resultado fijado manualmente vía `override.py`.)_", ""]
    grupos, qualified = section_groups(conn)
    bracket = get_bracket_data(conn, n_sims=args.n_sims)
    md = "\n".join(header + grupos + ["---", ""] + section_qualifiers(conn, qualified)
                   + ["---", ""] + section_bracket(bracket) + ["---", ""]
                   + section_mc(bracket, args.n_sims))
    conn.close()

    if args.dry_run:
        print(md)
        return
    with open(ESTADO_PATH, encoding="utf-8") as f:
        doc = f.read()
    nuevo, n = re.subn(r"## 4\..*?(?=## 7\.)", md + "\n---\n\n", doc, flags=re.S)
    if n != 1:
        sys.exit("ERROR: no se encontraron los marcadores '## 4.' … '## 7.' en ESTADO_PROYECTO.md")
    with open(ESTADO_PATH, "w", encoding="utf-8") as f:
        f.write(nuevo)
    print(f"ESTADO_PROYECTO.md actualizado (secciones 4-6b, {args.n_sims} sims MC).")


if __name__ == "__main__":
    main()
