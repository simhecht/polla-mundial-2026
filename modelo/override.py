"""
override.py
===========
CLI para gestionar overrides manuales del escenario determinista.

Uso:
    python override.py set HOME AWAY GH-GA
        Fija el marcador de un partido de fase de grupos.
    python override.py set-ko HOME AWAY GH-GA [--advancer EQUIPO]
        Fija el marcador (90') de un partido eliminatorio. Si es empate,
        --advancer es obligatorio (quién avanza por prórroga/penales).
    python override.py list
        Muestra los overrides activos.
    python override.py clear HOME AWAY
    python override.py clear --all
        Elimina overrides (de un par, o todos).

Los nombres se validan contra la tabla `teams` (acepta `name` o `name_es`,
sin distinguir mayúsculas). Internamente se guardan los nombres raw (`name`).
"""

import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from predictor_v3 import DB_PATH
import overrides


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _connect():
    if not os.path.exists(DB_PATH):
        sys.exit(f"Error: no existe la DB en {DB_PATH}. "
                 f"Inicialízala con: python -c \"import setup_db; setup_db.setup()\"")
    return sqlite3.connect(DB_PATH)


def resolve_team(conn, name):
    """Resuelve un nombre (name o name_es, case-insensitive) al nombre raw.
    Termina con error claro si el equipo no existe."""
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM teams WHERE name=? COLLATE NOCASE "
        "OR name_es=? COLLATE NOCASE", (name, name))
    row = cur.fetchone()
    if not row:
        sys.exit(f"Error: equipo '{name}' no existe en la tabla teams "
                 f"(ni como name ni como name_es).")
    return row[0]


def parse_score(score_str):
    """Parsea 'GH-GA' a (gh, ga). Termina con error claro si es inválido."""
    parts = score_str.split("-")
    if len(parts) != 2:
        sys.exit(f"Error: marcador inválido '{score_str}'. Formato esperado: GH-GA (ej: 2-1).")
    try:
        gh, ga = int(parts[0]), int(parts[1])
    except ValueError:
        sys.exit(f"Error: marcador inválido '{score_str}'. Los goles deben ser enteros.")
    if gh < 0 or ga < 0:
        sys.exit("Error: los goles no pueden ser negativos.")
    if gh > 6 or ga > 6:
        print(f"Advertencia: marcador {gh}-{ga} fuera de la grilla del modelo (0..6); "
              f"el EV calculado puede no ser representativo.")
    return gh, ga


def is_group_fixture(conn, home, away):
    """True si el par existe como GROUP_FIXTURE en recent_matches (cualquier orientación)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM recent_matches
        WHERE competition='GROUP_FIXTURE'
          AND ((team_home=? AND team_away=?) OR (team_home=? AND team_away=?))
        LIMIT 1
    """, (home, away, away, home))
    return cur.fetchone() is not None


def name_es_of(conn, raw):
    cur = conn.cursor()
    cur.execute("SELECT name_es FROM teams WHERE name=?", (raw,))
    row = cur.fetchone()
    return (row[0] if row and row[0] else raw)


# ---------------------------------------------------------------------------
# Subcomandos
# ---------------------------------------------------------------------------
def cmd_set(args):
    conn = _connect()
    home = resolve_team(conn, args.home)
    away = resolve_team(conn, args.away)
    gh, ga = parse_score(args.score)
    if not is_group_fixture(conn, home, away):
        print(f"Advertencia: '{home}' vs '{away}' no figura como partido de "
              f"fase de grupos (GROUP_FIXTURE) en la DB. El override se guarda "
              f"igual, pero no afectará ninguna tabla de grupo.")
    overrides.set_group_override(home, away, gh, ga)
    print(f"Override de grupo guardado: {name_es_of(conn, home)} {gh}-{ga} "
          f"{name_es_of(conn, away)}  [{home} vs {away}]")
    conn.close()


def cmd_set_ko(args):
    conn = _connect()
    home = resolve_team(conn, args.home)
    away = resolve_team(conn, args.away)
    gh, ga = parse_score(args.score)
    advancer = None
    if gh == ga:
        if not args.advancer:
            sys.exit("Error: el marcador es empate; debes indicar quién avanza "
                     "con --advancer EQUIPO.")
        advancer = resolve_team(conn, args.advancer)
        if advancer not in (home, away):
            sys.exit(f"Error: el advancer '{advancer}' debe ser uno de los dos "
                     f"equipos del partido ({home} o {away}).")
    elif args.advancer:
        print("Advertencia: el marcador no es empate; --advancer se ignora "
              "(avanza el ganador del marcador).")
    overrides.set_ko_override(home, away, gh, ga, advancer=advancer)
    adv_str = f" (avanza: {name_es_of(conn, advancer)})" if advancer else ""
    print(f"Override KO guardado: {name_es_of(conn, home)} {gh}-{ga} "
          f"{name_es_of(conn, away)}{adv_str}  [{home} vs {away}]")
    conn.close()


def cmd_list(args):
    data = overrides.load_overrides()
    if not data["groups"] and not data["ko"]:
        print("No hay overrides activos.")
        return
    if data["groups"]:
        print("Overrides de fase de grupos:")
        for e in data["groups"]:
            print(f"  {e['home']} {e['score'][0]}-{e['score'][1]} {e['away']}")
    if data["ko"]:
        print("Overrides de eliminatoria:")
        for e in data["ko"]:
            adv = f"  (avanza: {e['advancer']})" if e.get("advancer") else ""
            print(f"  {e['home']} {e['score'][0]}-{e['score'][1]} {e['away']}{adv}")


def cmd_clear(args):
    if args.all:
        n = overrides.clear_overrides()
        print(f"Eliminados {n} override(s). No quedan overrides activos.")
        return
    if len(args.teams) != 2:
        sys.exit("Error: indica el par de equipos (clear HOME AWAY) o usa --all.")
    conn = _connect()
    home = resolve_team(conn, args.teams[0])
    away = resolve_team(conn, args.teams[1])
    conn.close()
    n = overrides.clear_overrides(home, away)
    if n:
        print(f"Eliminados {n} override(s) para {home} vs {away}.")
    else:
        print(f"No había overrides para {home} vs {away}.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Gestiona overrides manuales del escenario determinista "
                    "(fase de grupos y eliminatoria).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_set = sub.add_parser("set", help="Fija el marcador de un partido de grupos")
    p_set.add_argument("home", help="Equipo local (name o name_es)")
    p_set.add_argument("away", help="Equipo visitante (name o name_es)")
    p_set.add_argument("score", help="Marcador GH-GA (ej: 2-1)")
    p_set.set_defaults(func=cmd_set)

    p_ko = sub.add_parser("set-ko", help="Fija el marcador (90') de un partido KO")
    p_ko.add_argument("home", help="Equipo local (name o name_es)")
    p_ko.add_argument("away", help="Equipo visitante (name o name_es)")
    p_ko.add_argument("score", help="Marcador a 90' GH-GA (ej: 1-1)")
    p_ko.add_argument("--advancer", help="Quién avanza si el marcador es empate "
                                         "(obligatorio en ese caso)")
    p_ko.set_defaults(func=cmd_set_ko)

    p_list = sub.add_parser("list", help="Muestra los overrides activos")
    p_list.set_defaults(func=cmd_list)

    p_clear = sub.add_parser("clear", help="Elimina overrides (de un par o todos)")
    p_clear.add_argument("teams", nargs="*", help="HOME AWAY (par a limpiar)")
    p_clear.add_argument("--all", action="store_true", help="Elimina TODOS los overrides")
    p_clear.set_defaults(func=cmd_clear)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
