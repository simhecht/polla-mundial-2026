"""
update_team.py
Herramienta para actualizar datos cualitativos de un equipo mientras analizamos cada grupo.
Uso:  python update_team.py <nombre_equipo> [--elo X] [--form X] [--depth X] [--style X] [--notes "..."]
"""
import sqlite3
import sys
import argparse
import os

DB_PATH = "/tmp/mundial_2026.db"


def update_team(name, **kwargs):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT team_id, name_es, elo_rating, form_score, squad_depth_score, tactical_style FROM teams WHERE name=? OR name_es=?", (name, name))
    row = cur.fetchone()
    if not row:
        print(f"❌ Equipo '{name}' no encontrado.")
        conn.close()
        return

    team_id, name_es, elo, form, depth, style = row
    updates = []
    values = []
    for field, val in kwargs.items():
        if val is not None:
            updates.append(f"{field}=?")
            values.append(val)

    if updates:
        values.append(team_id)
        cur.execute(f"UPDATE teams SET {', '.join(updates)} WHERE team_id=?", values)
        conn.commit()
        print(f"✅ {name_es or name} actualizado: {kwargs}")
    else:
        print(f"ℹ️  {name_es or name}: ELO={elo}, forma={form}, profundidad={depth}, estilo={style}")

    conn.close()


def list_group(group):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""SELECT name_es, elo_rating, form_score, squad_depth_score, tactical_style, coach, notes
                   FROM teams WHERE group_name=? ORDER BY elo_rating DESC""", (group,))
    rows = cur.fetchall()
    print(f"\n{'='*70}")
    print(f"  GRUPO {group}")
    print(f"{'='*70}")
    print(f"  {'Equipo':<22} {'ELO':>6} {'Forma':>6} {'Profund':>7} {'Estilo':<14} {'DT'}")
    print(f"  {'-'*70}")
    for r in rows:
        print(f"  {r[0]:<22} {r[1]:>6.0f} {r[2]:>6.1f} {r[3]:>7.1f} {(r[4] or '?'):<14} {r[5] or '?'}")
        if r[6]:
            print(f"    📝 {r[6]}")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Actualizar datos de equipo")
    parser.add_argument("team", nargs="?", help="Nombre del equipo")
    parser.add_argument("--group", "-g", help="Listar equipo del grupo X")
    parser.add_argument("--elo",   type=float)
    parser.add_argument("--form",  type=float, help="Forma 1-10")
    parser.add_argument("--depth", type=float, help="Profundidad plantilla 1-10")
    parser.add_argument("--style", help="Estilo táctico: possession/counter/high_press/defensive/mixed")
    parser.add_argument("--notes", help="Notas cualitativas")
    parser.add_argument("--coach", help="Nombre del DT")
    args = parser.parse_args()

    if args.group:
        list_group(args.group.upper())
    elif args.team:
        update_team(args.team,
                    elo_rating=args.elo,
                    form_score=args.form,
                    squad_depth_score=args.depth,
                    tactical_style=args.style,
                    notes=args.notes,
                    coach=args.coach)
    else:
        parser.print_help()
