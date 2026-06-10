"""
load_history.py
Carga el dataset histórico de partidos internacionales (martj42/international_results)
en la base de datos local `data/mundial_2026.db`, dejándola lista para recalibrar
el modelo ELO y el estimador de penales.

Tablas creadas (DROP + CREATE, idempotente):
  - intl_matches   : todos los partidos desde 1872 (results.csv)
  - intl_shootouts : definiciones por penales (shootouts.csv)
  - team_name_map  : mapeo our_name → dataset_name para los 48 equipos del torneo

Orden de reconstrucción de la DB:
  1. setup_db.setup()      — crea teams, recent_matches, key_players, squad_depth,
                             predictions con IF NOT EXISTS; borra y repopula solo la
                             tabla `teams` (DELETE FROM teams) y los fixtures de grupo
                             (DELETE FROM recent_matches WHERE competition='GROUP_FIXTURE').
                             NO borra el archivo ni hace DROP de tablas.
  2. update_all_teams.run() — actualiza columnas de teams.
  3. load_history.run()    — crea/repopula las tablas históricas.

  IMPORTANTE: setup_db.setup() y regenerate_db() de predictor_v3 NO eliminan el
  archivo .db ni hacen DROP de las tablas históricas (intl_matches, intl_shootouts,
  team_name_map). Por lo tanto, si se ejecuta setup_db.setup() sobre una DB que ya
  tiene los datos históricos cargados, éstos SE CONSERVAN. Solo es necesario
  re-ejecutar load_history.run() si se borra manualmente el archivo de la DB.

Fuentes:
  data/raw/results.csv      — https://raw.githubusercontent.com/martj42/international_results/master/results.csv
  data/raw/shootouts.csv    — https://raw.githubusercontent.com/martj42/international_results/master/shootouts.csv
  data/raw/former_names.csv — https://raw.githubusercontent.com/martj42/international_results/master/former_names.csv
"""

import csv
import os
import sqlite3
import sys

# ---------------------------------------------------------------------------
# Rutas canónicas
# ---------------------------------------------------------------------------
_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_DIR, "data", "mundial_2026.db")
RAW_DIR = os.path.join(_DIR, "data", "raw")
RESULTS_CSV    = os.path.join(RAW_DIR, "results.csv")
SHOOTOUTS_CSV  = os.path.join(RAW_DIR, "shootouts.csv")


# ---------------------------------------------------------------------------
# Mapeos manuales confirmados empíricamente:
# nuestro nombre (tabla `teams`) → nombre en el dataset martj42
# Solo se listan los que difieren; los 43 restantes coinciden exactamente.
# ---------------------------------------------------------------------------
MANUAL_MAP = {
    "Bosnia":    "Bosnia and Herzegovina",
    "Cabo Verde": "Cape Verde",
    "Curacao":   "Curaçao",
    "Czechia":   "Czech Republic",
    "USA":       "United States",
}


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------
DDL = """
DROP TABLE IF EXISTS intl_matches;
DROP TABLE IF EXISTS intl_shootouts;
DROP TABLE IF EXISTS team_name_map;

CREATE TABLE intl_matches (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT    NOT NULL,
    home_team    TEXT    NOT NULL,
    away_team    TEXT    NOT NULL,
    home_score   INTEGER,
    away_score   INTEGER,
    tournament   TEXT,
    city         TEXT,
    country      TEXT,
    neutral      INTEGER NOT NULL DEFAULT 0   -- 0 = local, 1 = campo neutro
);
CREATE INDEX idx_intl_matches_date      ON intl_matches(date);
CREATE INDEX idx_intl_matches_home      ON intl_matches(home_team);
CREATE INDEX idx_intl_matches_away      ON intl_matches(away_team);

CREATE TABLE intl_shootouts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    date           TEXT NOT NULL,
    home_team      TEXT NOT NULL,
    away_team      TEXT NOT NULL,
    winner         TEXT,
    first_shooter  TEXT
);
CREATE INDEX idx_intl_shootouts_date ON intl_shootouts(date);

CREATE TABLE team_name_map (
    our_name     TEXT PRIMARY KEY,
    dataset_name TEXT NOT NULL
);
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_dataset_teams(results_path: str) -> set:
    """Retorna el conjunto de nombres únicos de equipos en el dataset."""
    teams = set()
    with open(results_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            teams.add(row["home_team"])
            teams.add(row["away_team"])
    return teams


def _build_name_map(our_teams: list, dataset_teams: set) -> dict:
    """
    Construye el mapeo our_name → dataset_name para los 48 equipos.
    Falla con SystemExit si algún equipo no puede mapearse.
    """
    name_map = {}
    unmapped = []

    for our_name in our_teams:
        if our_name in MANUAL_MAP:
            ds_name = MANUAL_MAP[our_name]
            if ds_name not in dataset_teams:
                unmapped.append(
                    f"  '{our_name}' → '{ds_name}' NO encontrado en el dataset"
                )
            else:
                name_map[our_name] = ds_name
        elif our_name in dataset_teams:
            name_map[our_name] = our_name
        else:
            unmapped.append(
                f"  '{our_name}' no tiene coincidencia exacta ni mapeo manual"
            )

    if unmapped:
        print("ERROR: Los siguientes equipos no pudieron mapearse al dataset:", file=sys.stderr)
        for msg in unmapped:
            print(msg, file=sys.stderr)
        sys.exit(1)

    return name_map


def _neutral_flag(val: str) -> int:
    return 1 if val.strip().upper() in ("TRUE", "1", "YES") else 0


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------
def run(db_path: str = DB_PATH) -> None:
    """
    Crea las tablas históricas y las llena con los CSV descargados.
    Idempotente: DROP + CREATE en cada llamada.
    """
    # -- Verificar archivos CSV -----------------------------------------------
    for path in (RESULTS_CSV, SHOOTOUTS_CSV):
        if not os.path.exists(path):
            print(
                f"ERROR: Archivo no encontrado: {path}\n"
                "Ejecuta primero:\n"
                "  curl -fSL https://raw.githubusercontent.com/martj42/international_results/master/results.csv "
                "-o modelo/data/raw/results.csv\n"
                "  curl -fSL https://raw.githubusercontent.com/martj42/international_results/master/shootouts.csv "
                "-o modelo/data/raw/shootouts.csv",
                file=sys.stderr,
            )
            sys.exit(1)

    # -- Conectar a la DB ------------------------------------------------------
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # -- Leer equipos de la tabla `teams` --------------------------------------
    cur.execute("SELECT name FROM teams ORDER BY team_id")
    our_teams = [row[0] for row in cur.fetchall()]
    if not our_teams:
        print(
            "ERROR: La tabla `teams` está vacía. Ejecuta setup_db.setup() primero.",
            file=sys.stderr,
        )
        conn.close()
        sys.exit(1)

    # -- Construir mapa de nombres ---------------------------------------------
    dataset_teams = _load_dataset_teams(RESULTS_CSV)
    name_map = _build_name_map(our_teams, dataset_teams)

    # -- Crear tablas (DDL idempotente) ----------------------------------------
    conn.executescript(DDL)

    # -- Cargar results.csv → intl_matches -------------------------------------
    matches_rows = []
    with open(RESULTS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                hs = int(row["home_score"]) if row["home_score"].strip() else None
                as_ = int(row["away_score"]) if row["away_score"].strip() else None
            except ValueError:
                hs = as_ = None
            matches_rows.append((
                row["date"],
                row["home_team"],
                row["away_team"],
                hs,
                as_,
                row["tournament"],
                row["city"],
                row["country"],
                _neutral_flag(row["neutral"]),
            ))

    # -- Cargar shootouts.csv → intl_shootouts ---------------------------------
    shootouts_rows = []
    with open(SHOOTOUTS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            shootouts_rows.append((
                row["date"],
                row["home_team"],
                row["away_team"],
                row["winner"],
                row["first_shooter"],
            ))

    # -- Insertar todo en una sola transacción ---------------------------------
    with conn:
        cur.executemany(
            "INSERT INTO intl_matches "
            "(date,home_team,away_team,home_score,away_score,tournament,city,country,neutral) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            matches_rows,
        )
        cur.executemany(
            "INSERT INTO intl_shootouts (date,home_team,away_team,winner,first_shooter) "
            "VALUES (?,?,?,?,?)",
            shootouts_rows,
        )
        cur.executemany(
            "INSERT INTO team_name_map (our_name, dataset_name) VALUES (?,?)",
            list(name_map.items()),
        )

    # -- Resumen ---------------------------------------------------------------
    cur.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM intl_matches")
    m_count, m_min, m_max = cur.fetchone()

    cur.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM intl_shootouts")
    s_count, s_min, s_max = cur.fetchone()

    # Partidos desde 2020 que involucran a alguno de nuestros 48 equipos
    ds_names = list(name_map.values())
    placeholders = ",".join("?" * len(ds_names))
    cur.execute(
        f"""
        SELECT COUNT(*) FROM intl_matches
        WHERE date >= '2020-01-01'
          AND (home_team IN ({placeholders}) OR away_team IN ({placeholders}))
        """,
        ds_names * 2,
    )
    recent_count = cur.fetchone()[0]

    conn.close()

    print("=" * 60)
    print("RESUMEN CARGA HISTÓRICA")
    print("=" * 60)
    print(f"  intl_matches   : {m_count:>6} filas | {m_min} → {m_max}")
    print(f"  intl_shootouts : {s_count:>6} filas | {s_min} → {s_max}")
    print(f"  team_name_map  : {len(name_map):>6} filas (48 equipos)")
    print()
    print(f"  Partidos desde 2020 con equipos del Mundial 2026: {recent_count}")
    print()

    # Mostrar solo los mapeos no triviales (donde difieren)
    non_trivial = [(k, v) for k, v in sorted(name_map.items()) if k != v]
    if non_trivial:
        print("  Mapeos no triviales (our_name → dataset_name):")
        for our, ds in non_trivial:
            print(f"    {our!r:18} → {ds!r}")
    else:
        print("  Todos los nombres coinciden exactamente con el dataset.")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run()
