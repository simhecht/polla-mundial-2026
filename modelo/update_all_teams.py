"""
update_all_teams.py
Aplica el research cualitativo completo (junio 2026) a la base de datos.
Los datos canónicos viven en setup_db.TEAMS; este módulo los re-aplica como
verificación idempotente (útil si la DB fue editada manualmente).
"""
import sqlite3
import os
import sys

# Importar desde setup_db para mantener una única fuente de verdad
sys.path.insert(0, os.path.dirname(__file__))
import setup_db

DB_PATH = setup_db.DB_PATH

# Construir UPDATES desde setup_db.TEAMS para eliminar duplicación.
# Campos: (name, elo_rating, form_score, squad_depth_score, tactical_style, coach, notes)
UPDATES = [
    (t[1], t[5], t[11], t[10], t[8], t[7], t[12])
    for t in setup_db.TEAMS
]


def run(db_path=None):
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    updated = 0
    not_found = []
    for row in UPDATES:
        name, elo, form, depth, style, coach, notes = row
        cur.execute("""UPDATE teams SET elo_rating=?, form_score=?, squad_depth_score=?,
                       tactical_style=?, coach=?, notes=?
                       WHERE name=?""",
                    (elo, form, depth, style, coach, notes, name))
        if cur.rowcount == 0:
            not_found.append(name)
        else:
            updated += 1
    conn.commit()
    conn.close()
    print(f"✅ {updated} equipos actualizados con datos cualitativos reales")
    if not_found:
        print(f"⚠️  No encontrados: {not_found}")


if __name__ == "__main__":
    run()
