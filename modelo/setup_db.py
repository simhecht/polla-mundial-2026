"""
setup_db.py
Inicializa la base de datos SQLite para la Polla Mundial 2026.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "mundial_2026.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (
    team_id     INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    name_es     TEXT,
    confederation TEXT,
    group_name  TEXT,
    elo_rating  REAL DEFAULT 1500,
    fifa_ranking INTEGER,
    coach       TEXT,
    tactical_style TEXT,
    avg_age     REAL,
    squad_depth_score REAL DEFAULT 5.0,
    form_score  REAL DEFAULT 5.0,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS recent_matches (
    match_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT,
    team_home   TEXT,
    team_away   TEXT,
    goals_home  INTEGER,
    goals_away  INTEGER,
    xg_home     REAL,
    xg_away     REAL,
    competition TEXT,
    neutral_venue INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS key_players (
    player_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id     INTEGER,
    name        TEXT,
    position    TEXT,
    club        TEXT,
    current_form REAL,
    is_starter  INTEGER DEFAULT 1,
    injury_risk TEXT DEFAULT 'low',
    notes       TEXT,
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS squad_depth (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id     INTEGER,
    position_group TEXT,
    depth_score REAL,
    notes       TEXT,
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS predictions (
    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_home_id  INTEGER,
    team_away_id  INTEGER,
    phase         TEXT,
    predicted_goals_home INTEGER,
    predicted_goals_away INTEGER,
    prob_home_win REAL,
    prob_draw     REAL,
    prob_away_win REAL,
    confidence    TEXT,
    notes         TEXT,
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_home_id) REFERENCES teams(team_id),
    FOREIGN KEY (team_away_id) REFERENCES teams(team_id)
);
"""

# 48 equipos con datos base
# ELO estimados a junio 2026 (fuente: eloratings.net + ajuste forma reciente)
TEAMS = [
    # (team_id, name, name_es, confederation, group, elo, fifa_rank, coach, style, avg_age, squad_depth, form_score, notes)
    # GRUPO A
    (1,  "Mexico",        "México",           "CONCACAF",  "A", 1718, 15,  "Javier Aguirre",    "counter",    26.8, 6.0, 6.0, ""),
    (2,  "South Korea",   "Corea del Sur",    "AFC",       "A", 1627, 23,  "Hong Myung-bo",     "high_press", 27.2, 6.5, 6.5, ""),
    (3,  "South Africa",  "Sudáfrica",        "CAF",       "A", 1521, 67,  "Hugo Broos",        "defensive",  27.0, 4.5, 5.5, ""),
    (4,  "Czechia",       "Chequia",          "UEFA",      "A", 1612, 36,  "Ivan Hasek",        "mixed",      27.5, 5.5, 6.0, "Clasificó via playoff UEFA D"),
    # GRUPO B
    (5,  "Canada",        "Canadá",           "CONCACAF",  "B", 1703, 46,  "Jesse Marsch",      "high_press", 26.5, 6.5, 7.0, ""),
    (6,  "Bosnia",        "Bosnia y Herz.",   "UEFA",      "B", 1558, 53,  "Sergej Barbarez",   "mixed",      28.0, 5.0, 6.0, "Clasificó via playoff UEFA A (venció a Italia)"),
    (7,  "Qatar",         "Catar",            "AFC",       "B", 1447, 58,  "Marquez Lopez",     "possession", 26.0, 4.5, 5.0, ""),
    (8,  "Switzerland",   "Suiza",            "UEFA",      "B", 1718, 19,  "Murat Yakin",       "defensive",  27.8, 7.0, 7.0, ""),
    # GRUPO C
    (9,  "Brazil",        "Brasil",           "CONMEBOL",  "C", 1838, 5,   "Dorival Junior",    "possession", 26.2, 8.0, 6.5, ""),
    (10, "Morocco",       "Marruecos",        "CAF",       "C", 1747, 14,  "Walid Regragui",    "defensive",  26.8, 7.5, 7.5, ""),
    (11, "Haiti",         "Haití",            "CONCACAF",  "C", 1374, 84,  "Marc Collat",       "counter",    25.5, 3.5, 4.5, ""),
    (12, "Scotland",      "Escocia",          "UEFA",      "C", 1631, 39,  "Steve Clarke",      "high_press", 28.5, 6.0, 6.0, ""),
    # GRUPO D
    (13, "USA",           "Estados Unidos",   "CONCACAF",  "D", 1752, 13,  "Mauricio Pochettino","high_press",25.8, 7.5, 7.5, ""),
    (14, "Paraguay",      "Paraguay",         "CONMEBOL",  "D", 1569, 61,  "Gustavo Alfaro",    "defensive",  27.5, 5.5, 5.5, ""),
    (15, "Australia",     "Australia",        "AFC",       "D", 1628, 24,  "Tony Popovic",      "mixed",      27.0, 6.0, 6.5, ""),
    (16, "Turkey",        "Turquía",          "UEFA",      "D", 1648, 29,  "Vincenzo Montella", "counter",    27.2, 6.5, 6.5, "Clasificó via playoff UEFA C"),
    # GRUPO E
    (17, "Germany",       "Alemania",         "UEFA",      "E", 1853, 12,  "Julian Nagelsmann", "high_press", 25.5, 8.5, 8.0, ""),
    (18, "Curacao",       "Curazao",          "CONCACAF",  "E", 1371, 76,  "Remko Bicentini",   "counter",    26.5, 3.5, 4.5, ""),
    (19, "Ivory Coast",   "Costa de Marfil",  "CAF",       "E", 1628, 55,  "Emerse Fae",        "counter",    27.8, 6.5, 6.5, ""),
    (20, "Ecuador",       "Ecuador",          "CONMEBOL",  "E", 1648, 42,  "Sebastian Beccacece","high_press",25.5, 6.5, 7.0, ""),
    # GRUPO F
    (21, "Netherlands",   "Países Bajos",     "UEFA",      "F", 1836, 7,   "Ronald Koeman",     "possession", 26.8, 8.0, 7.5, ""),
    (22, "Japan",         "Japón",            "AFC",       "F", 1733, 17,  "Hajime Moriyasu",   "high_press", 26.5, 7.5, 8.0, ""),
    (23, "Sweden",        "Suecia",           "UEFA",      "F", 1648, 25,  "Jon Dahl Tomasson", "mixed",      27.5, 6.5, 6.5, "Clasificó via playoff UEFA B"),
    (24, "Tunisia",       "Túnez",            "CAF",       "F", 1536, 32,  "Faouzi Benzarti",   "defensive",  27.0, 5.5, 5.5, ""),
    # GRUPO G
    (25, "Belgium",       "Bélgica",          "UEFA",      "G", 1791, 3,   "Rudi Garcia",       "possession", 28.5, 7.5, 6.5, "Generación de oro en declive"),
    (26, "Egypt",         "Egipto",           "CAF",       "G", 1589, 33,  "Hossam Hassan",     "defensive",  27.5, 6.0, 6.0, ""),
    (27, "Iran",          "Irán",             "AFC",       "G", 1558, 22,  "Amir Ghalenoei",    "defensive",  28.0, 5.5, 5.5, ""),
    (28, "New Zealand",   "Nueva Zelanda",    "OFC",       "G", 1357, 96,  "Darren Bazeley",    "defensive",  26.5, 3.5, 4.5, ""),
    # GRUPO H
    (29, "Spain",         "España",           "UEFA",      "H", 1913, 2,   "Luis de la Fuente", "possession", 25.8, 9.0, 9.0, "Campeona EURO 2024"),
    (30, "Saudi Arabia",  "Arabia Saudita",   "AFC",       "H", 1508, 56,  "Roberto Mancini",   "defensive",  27.0, 5.5, 5.5, ""),
    (31, "Uruguay",       "Uruguay",          "CONMEBOL",  "H", 1762, 18,  "Marcelo Bielsa",    "high_press", 26.5, 7.5, 7.5, ""),
    (32, "Cabo Verde",    "Cabo Verde",       "CAF",       "H", 1489, 73,  "Bubista",           "defensive",  27.5, 4.0, 5.0, ""),
    # GRUPO I
    (33, "France",        "Francia",          "UEFA",      "I", 1891, 2,   "Didier Deschamps",  "counter",    27.5, 9.0, 8.0, ""),
    (34, "Senegal",       "Senegal",          "CAF",       "I", 1683, 20,  "Aliou Cisse",       "mixed",      27.0, 7.0, 7.0, ""),
    (35, "Norway",        "Noruega",          "UEFA",      "I", 1658, 34,  "Stale Solbakken",   "mixed",      26.0, 6.5, 7.0, ""),
    (36, "Iraq",          "Irak",             "AFC",       "I", 1389, 63,  "Jesus Casas",       "defensive",  26.5, 3.5, 5.0, "Clasificó via repechaje"),
    # GRUPO J
    (37, "Argentina",     "Argentina",        "CONMEBOL",  "J", 1962, 1,   "Lionel Scaloni",    "possession", 27.8, 9.5, 9.0, "Campeona del mundo 2022"),
    (38, "Algeria",       "Argelia",          "CAF",       "J", 1589, 48,  "Vladimir Petkovic", "defensive",  28.0, 6.5, 6.0, ""),
    (39, "Austria",       "Austria",          "UEFA",      "J", 1693, 26,  "Ralf Rangnick",     "high_press", 26.5, 7.0, 7.5, ""),
    (40, "Jordan",        "Jordania",         "AFC",       "J", 1443, 87,  "Hussein Ammouta",   "defensive",  26.0, 4.0, 5.0, ""),
    # GRUPO K
    (41, "Portugal",      "Portugal",         "UEFA",      "K", 1856, 6,   "Roberto Martinez",  "possession", 27.2, 8.5, 8.5, ""),
    (42, "DR Congo",      "R.D. del Congo",   "CAF",       "K", 1432, 53,  "Sébastien Desabre", "counter",    27.5, 4.5, 5.5, "Clasificó via repechaje"),
    (43, "Uzbekistan",    "Uzbekistán",       "AFC",       "K", 1498, 69,  "Srecko Katanec",    "mixed",      25.5, 5.0, 5.5, ""),
    (44, "Colombia",      "Colombia",         "CONMEBOL",  "K", 1738, 11,  "Nestor Lorenzo",    "counter",    26.8, 7.5, 8.0, ""),
    # GRUPO L
    (45, "England",       "Inglaterra",       "UEFA",      "L", 1842, 4,   "Thomas Tuchel",     "high_press", 26.5, 9.0, 8.0, ""),
    (46, "Croatia",       "Croacia",          "UEFA",      "L", 1698, 10,  "Zlatko Dalic",      "possession", 29.5, 7.0, 6.5, "Plantilla envejecida"),
    (47, "Ghana",         "Ghana",            "CAF",       "L", 1527, 60,  "Otto Addo",         "counter",    26.0, 5.5, 5.5, ""),
    (48, "Panama",        "Panamá",           "CONCACAF",  "L", 1523, 72,  "Thomas Christiansen","defensive", 28.0, 5.0, 5.5, ""),
]

# Partidos de fase de grupos (fixture oficial)
GROUP_MATCHES = [
    # Grupo A
    ("2026-06-11", "Mexico",       "South Africa",  "A", 0),
    ("2026-06-11", "South Korea",  "Czechia",       "A", 1),
    ("2026-06-18", "Czechia",      "South Africa",  "A", 1),
    ("2026-06-18", "Mexico",       "South Korea",   "A", 0),
    ("2026-06-24", "Czechia",      "Mexico",        "A", 0),
    ("2026-06-24", "South Africa", "South Korea",   "A", 1),
    # Grupo B
    ("2026-06-12", "Canada",       "Bosnia",        "B", 0),
    ("2026-06-13", "Qatar",        "Switzerland",   "B", 1),
    ("2026-06-18", "Switzerland",  "Bosnia",        "B", 1),
    ("2026-06-18", "Canada",       "Qatar",         "B", 0),
    ("2026-06-24", "Switzerland",  "Canada",        "B", 1),
    ("2026-06-24", "Bosnia",       "Qatar",         "B", 1),
    # Grupo C
    ("2026-06-13", "Brazil",       "Morocco",       "C", 1),
    ("2026-06-13", "Haiti",        "Scotland",      "C", 1),
    ("2026-06-19", "Scotland",     "Morocco",       "C", 1),
    ("2026-06-19", "Brazil",       "Haiti",         "C", 1),
    ("2026-06-24", "Scotland",     "Brazil",        "C", 1),
    ("2026-06-24", "Morocco",      "Haiti",         "C", 1),
    # Grupo D
    ("2026-06-12", "USA",          "Paraguay",      "D", 0),
    ("2026-06-13", "Australia",    "Turkey",        "D", 1),
    ("2026-06-19", "Turkey",       "Paraguay",      "D", 1),
    ("2026-06-19", "USA",          "Australia",     "D", 0),
    ("2026-06-25", "Turkey",       "USA",           "D", 1),
    ("2026-06-25", "Paraguay",     "Australia",     "D", 1),
    # Grupo E
    ("2026-06-14", "Germany",      "Curacao",       "E", 0),
    ("2026-06-14", "Ivory Coast",  "Ecuador",       "E", 1),
    ("2026-06-20", "Germany",      "Ivory Coast",   "E", 0),
    ("2026-06-20", "Ecuador",      "Curacao",       "E", 1),
    ("2026-06-25", "Ecuador",      "Germany",       "E", 1),
    ("2026-06-25", "Curacao",      "Ivory Coast",   "E", 1),
    # Grupo F
    ("2026-06-14", "Netherlands",  "Japan",         "F", 0),
    ("2026-06-14", "Sweden",       "Tunisia",       "F", 0),
    ("2026-06-20", "Netherlands",  "Sweden",        "F", 0),
    ("2026-06-20", "Tunisia",      "Japan",         "F", 1),
    ("2026-06-25", "Japan",        "Sweden",        "F", 1),
    ("2026-06-25", "Tunisia",      "Netherlands",   "F", 1),
    # Grupo G
    ("2026-06-15", "Belgium",      "Egypt",         "G", 0),
    ("2026-06-15", "Iran",         "New Zealand",   "G", 1),
    ("2026-06-21", "Belgium",      "Iran",          "G", 0),
    ("2026-06-21", "New Zealand",  "Egypt",         "G", 1),
    ("2026-06-26", "Egypt",        "Iran",          "G", 1),
    ("2026-06-26", "New Zealand",  "Belgium",       "G", 1),
    # Grupo H
    ("2026-06-15", "Spain",        "Cabo Verde",    "H", 0),
    ("2026-06-15", "Saudi Arabia", "Uruguay",       "H", 1),
    ("2026-06-21", "Spain",        "Saudi Arabia",  "H", 0),
    ("2026-06-21", "Uruguay",      "Cabo Verde",    "H", 1),
    ("2026-06-26", "Cabo Verde",   "Saudi Arabia",  "H", 1),
    ("2026-06-26", "Uruguay",      "Spain",         "H", 1),
    # Grupo I
    ("2026-06-16", "France",       "Senegal",       "I", 0),
    ("2026-06-16", "Iraq",         "Norway",        "I", 1),
    ("2026-06-22", "France",       "Iraq",          "I", 0),
    ("2026-06-22", "Norway",       "Senegal",       "I", 1),
    ("2026-06-26", "Norway",       "France",        "I", 1),
    ("2026-06-26", "Senegal",      "Iraq",          "I", 1),
    # Grupo J
    ("2026-06-16", "Argentina",    "Algeria",       "J", 0),
    ("2026-06-16", "Austria",      "Jordan",        "J", 1),
    ("2026-06-22", "Argentina",    "Austria",       "J", 0),
    ("2026-06-22", "Jordan",       "Algeria",       "J", 1),
    ("2026-06-27", "Algeria",      "Austria",       "J", 1),
    ("2026-06-27", "Jordan",       "Argentina",     "J", 1),
    # Grupo K
    ("2026-06-17", "Portugal",     "DR Congo",      "K", 0),
    ("2026-06-17", "Uzbekistan",   "Colombia",      "K", 1),
    ("2026-06-23", "Portugal",     "Uzbekistan",    "K", 0),
    ("2026-06-23", "Colombia",     "DR Congo",      "K", 1),
    ("2026-06-27", "Colombia",     "Portugal",      "K", 1),
    ("2026-06-27", "DR Congo",     "Uzbekistan",    "K", 1),
    # Grupo L
    ("2026-06-17", "England",      "Croatia",       "L", 0),
    ("2026-06-17", "Ghana",        "Panama",        "L", 1),
    ("2026-06-23", "England",      "Ghana",         "L", 0),
    ("2026-06-23", "Panama",       "Croatia",       "L", 1),
    ("2026-06-27", "Panama",       "England",       "L", 0),
    ("2026-06-27", "Croatia",      "Ghana",         "L", 1),
]


def setup():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    cur.execute("DELETE FROM teams")
    cur.executemany("""
        INSERT INTO teams
        (team_id,name,name_es,confederation,group_name,elo_rating,fifa_ranking,coach,tactical_style,avg_age,squad_depth_score,form_score,notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, TEAMS)

    cur.execute("DELETE FROM recent_matches WHERE competition='GROUP_FIXTURE'")
    cur.executemany("""
        INSERT INTO recent_matches (date,team_home,team_away,competition,neutral_venue)
        VALUES (?,?,?,?,?)
    """, [(d,h,a,"GROUP_FIXTURE",n) for d,h,a,_,n in GROUP_MATCHES])

    conn.commit()
    conn.close()
    print(f"✅ Base de datos inicializada en {DB_PATH}")
    print(f"   {len(TEAMS)} equipos | {len(GROUP_MATCHES)} partidos de grupo cargados")


if __name__ == "__main__":
    setup()
