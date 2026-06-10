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

# 48 equipos con datos junio 2026 (fuente canónica)
# (team_id, name, name_es, confederation, group, elo, fifa_rank, coach, style, avg_age, squad_depth, form_score, notes)
TEAMS = [
    # GRUPO A
    (1,  "Mexico",       "México",           "CONCACAF",  "A", 1718, 15,  "Javier Aguirre",    "counter",    26.8, 6.0, 7.0,
     "Ganó Nations League y Gold Cup 2025. Lozano excluido por indisciplina. 0-4 vs Colombia revela fragilidad. Aguirre prioriza organización defensiva; historial de caer en octavos."),
    (2,  "South Korea",  "Corea del Sur",    "AFC",       "A", 1627, 23,  "Hong Myung-bo",     "counter",    27.2, 6.0, 6.0,
     "Son Heung-min (32 años, LAFC) llegó con carga física alta. Dependencia total de él. Kim Min-jae (Bayern) sólido en defensa."),
    (3,  "South Africa", "Sudáfrica",        "CAF",       "A", 1521, 67,  "Hugo Broos",        "defensive",  27.0, 4.0, 6.0,
     "Broos anuncia que será su último trabajo. Plantel mayoritariamente doméstico. Cuartos AFCON 2023 es su techo real."),
    (4,  "Czechia",      "Chequia",          "UEFA",      "A", 1612, 36,  "Miroslav Koubek",   "mixed",      27.5, 5.0, 6.0,
     "DT Koubek lleva solo 2 partidos al mando — enorme incógnita táctica. Schick (Leverkusen) puede definir el grupo solo. Vuelven al Mundial tras 20 años."),
    # GRUPO B
    (5,  "Canada",       "Canadá",           "CONCACAF",  "B", 1703, 46,  "Jesse Marsch",      "high_press", 26.5, 7.0, 7.0,
     "Semifinal Copa América 2024. Davies (Bayern) no estará en el primer partido por lesión de isquiotibial — es su jugador más importante. Jonathan David (Atlético) en gran forma."),
    (6,  "Bosnia",       "Bosnia y Herz.",   "UEFA",      "B", 1558, 53,  "Sergej Barbarez",   "mixed",      28.0, 5.0, 6.0,
     "Eliminaron a Gales e Italia en playoffs vía penales. Džeko tiene 40 años. DT sin experiencia en torneos grandes. El milagro ya fue clasificar."),
    (7,  "Qatar",        "Catar",            "AFC",       "B", 1447, 58,  "Julen Lopetegui",   "possession", 26.0, 4.0, 4.0,
     "Perdieron 1-0 ante Irlanda en última prueba. Lopetegui historial de fracasos clave. Liga local sin competitividad real. Plantel del ciclo 2022 ya envejecido."),
    (8,  "Switzerland",  "Suiza",            "UEFA",      "B", 1718, 19,  "Murat Yakin",       "mixed",      27.8, 7.0, 8.0,
     "Ganaron 4-1 ante Jordania (31 mayo). Cuartos Euro 2024 (eliminaron a Italia, cayeron ante Inglaterra en penales). Xhaka (Sunderland) y Akanji (Inter) de élite."),
    # GRUPO C
    (9,  "Brazil",       "Brasil",           "CONMEBOL",  "C", 1838, 5,   "Carlo Ancelotti",   "possession", 26.2, 8.0, 6.0,
     "Ancelotti nombrado tras campaña clasificatoria tortuosa. Neymar (34 años, Al-Nassr) forma física incierta. Rodrygo y Estêvão ausentes. Vini+Raphinha de clase mundial pero defensa inconsistente."),
    (10, "Morocco",      "Marruecos",        "CAF",       "C", 1747, 14,  "Mohamed Ouahbi",    "defensive",  26.8, 7.0, 7.0,
     "Ouahbi nombrado en marzo 2026 (3 meses antes). Ex-DT Sub-20, ganó Mundial Sub-20 2025 vs Argentina. Hakimi (PSG) y Bounou clave. Cambio de DT es factor desestabilizador."),
    (11, "Haiti",        "Haití",            "CONCACAF",  "C", 1374, 84,  "Sébastien Migné",   "counter",    25.5, 3.0, 4.0,
     "Primera vez en un Mundial en 52 años. Solo un jugador de la liga local. Objetivo declarado: ganar un partido. Brecha técnica abismal con Brasil y Marruecos."),
    (12, "Scotland",     "Escocia",          "UEFA",      "C", 1631, 39,  "Steve Clarke",      "high_press", 28.5, 5.0, 6.0,
     "Primer Mundial desde 1998. Ganaron 4-1 ante Curazao (amistoso). Robertson (Liverpool) y McTominay (Nápoles) lideran. Gordon de portero tiene 43 años. Clarke nunca pasó fase de grupos."),
    # GRUPO D
    (13, "USA",          "Estados Unidos",   "CONCACAF",  "D", 1752, 13,  "Mauricio Pochettino","high_press", 25.8, 7.5, 6.0,
     "Perdieron 5-2 vs Bélgica y 2-0 vs Portugal en amistosos — resultados preocupantes. Factor anfitrión y estadio lleno pesan. Pulisic (Milan) es la llave ofensiva. Pochettino mejora equipos en torneos."),
    (14, "Paraguay",     "Paraguay",         "CONMEBOL",  "D", 1569, 61,  "Gustavo Alfaro",    "defensive",  27.5, 5.5, 6.0,
     "6tos en CONMEBOL con 28 pts. Enciso (Brighton) con potencial de desequilibrio individual. Alfaro sólido en torneos cortos con base defensiva."),
    (15, "Australia",    "Australia",        "AFC",       "D", 1628, 24,  "Tony Popovic",      "mixed",      27.0, 5.0, 6.0,
     "Popovic generó 8 partidos invictos para clasificar. Derrotados 1-0 por México en amistoso previo. Leckie y Ryan veteranos con experiencia mundialista. Sin jugador desequilibrante de nivel mundial."),
    (16, "Turkey",       "Turquía",          "UEFA",      "D", 1680, 29,  "Vincenzo Montella", "counter",    27.2, 7.0, 7.0,
     "Primer Mundial desde el 3er puesto de 2002. Güler (Real Madrid) y Yıldız (Juventus) jóvenes brillantes. Çalhanoğlu (Inter) en pivote. Montella llevó Turquía a cuartos Euro 2024."),
    # GRUPO E
    (17, "Germany",      "Alemania",         "UEFA",      "E", 1853, 12,  "Julian Nagelsmann", "high_press", 25.5, 8.5, 8.0,
     "5V en 6 partidos de clasificación. Euro 2024 perdido en cuartos vs España — sed de revancha. Musiala-Wirtz probablemente el mejor par creativo del torneo. Neuer regresa a los 40."),
    (18, "Curacao",      "Curazao",          "CONCACAF",  "E", 1371, 76,  "Dick Advocaat",     "counter",    26.5, 3.0, 3.0,
     "Advocaat (78 años, el DT más viejo en historia del Mundial) renunció, lo reemplazó Rutten, que renunció, y Advocaat volvió. Escocia los derrotó 4-1. La nación más pequeña del torneo. Solo objetivo: no perder todos."),
    (19, "Ivory Coast",  "Costa de Marfil",  "CAF",       "E", 1628, 55,  "Emerse Faé",        "high_press", 27.8, 6.5, 7.0,
     "Invictos y sin goles en contra en 10 partidos de clasificación africana. Amad Diallo (Man Utd) y Bonny (Inter) en ataque. Faé joven y dinámico. Cayeron en cuartos AFCON 2025 ante Egipto."),
    (20, "Ecuador",      "Ecuador",          "CONMEBOL",  "E", 1648, 42,  "Sebastián Beccacece","defensive", 25.5, 7.0, 8.0,
     "Solo 1 derrota en 18 partidos bajo Beccacece. Mejor defensa CONMEBOL (5 goles en 18 partidos). Caicedo (Chelsea) y Pacho (PSG)/Hincapié (Arsenal) son de élite. Valencia 36 años, riesgo en ataque."),
    # GRUPO F
    (21, "Netherlands",  "Países Bajos",     "UEFA",      "F", 1836, 7,   "Ronald Koeman",     "possession", 26.8, 7.0, 6.0,
     "Memphis (Corinthians) apenas 2 apariciones por lesión — llegó sin ritmo. Timber (Arsenal) fuera desde marzo. Van Dijk, Simons, Reijnders y Dumfries sólidos. Koeman históricamente bueno en torneos cortos."),
    (22, "Japan",        "Japón",            "AFC",       "F", 1733, 17,  "Hajime Moriyasu",   "high_press", 26.5, 7.5, 9.0,
     "Ganaron en Wembley vs Inglaterra 1-0 en marzo (primera victoria asiática en el estadio). Perfecto en clasificación AFC. Mitoma (Brighton) lesionado — baja importante. El mejor Japón de la historia. Favoritos a sorprender en segunda ronda."),
    (23, "Sweden",       "Suecia",           "UEFA",      "F", 1648, 25,  "Graham Potter",     "counter",    27.5, 8.0, 7.0,
     "Potter nombrado en octubre 2025 (solo 5 meses). Gyökeres (Arsenal) e Isak (Liverpool) uno de los mejores dúos de delanteros del torneo. Proyecto táctico en construcción."),
    (24, "Tunisia",      "Túnez",            "CAF",       "F", 1536, 32,  "Sabri Lamouchi",    "defensive",  27.0, 4.0, 4.0,
     "DT Lamouchi nombrado enero 2026, solo 2 partidos dirigidos. Solo 6 jugadores sobreviven del plantel 2022. Sin identidad táctica clara. Peor momento posible para afrontar a Países Bajos y Japón."),
    # GRUPO G
    (25, "Belgium",      "Bélgica",          "UEFA",      "G", 1791, 3,   "Rudi Garcia",       "mixed",      28.5, 6.5, 6.0,
     "Generación de oro en crepúsculo. Lukaku llegó con ~60 minutos de competición toda la temporada. De Bruyne (34) sigue siendo brillante. Garcia sin experiencia internacional en torneos cortos. Bélgica siempre decepciona cuando más importa."),
    (26, "Egypt",        "Egipto",           "CAF",       "G", 1589, 33,  "Hossam Hassan",     "counter",    27.5, 5.0, 6.0,
     "Salah (Liverpool) cumple 34 años el día del debut vs Bélgica. 17 de 26 jugadores del fútbol local árabe/egipcio. Dependencia total de Salah. Eliminados en semis AFCON 2025 por Senegal."),
    (27, "Iran",         "Irán",             "AFC",       "G", 1558, 22,  "Amir Ghalenoei",    "defensive",  28.0, 4.5, 5.0,
     "Azmoun excluido polémicamente. Taremi (Inter) vivió temporada irregular. Ganaron 3-1 ante Gambia en amistoso. Irán defensivo e intenso pero nivel técnico insuficiente para superar el grupo."),
    (28, "New Zealand",  "Nueva Zelanda",    "OFC",       "G", 1357, 96,  "Darren Bazeley",    "defensive",  26.5, 3.5, 5.0,
     "Rankeados ~85 en el mundo. Wood (Nottingham Forest, 45 goles, capitán) sigue relevante en Premier. Plantel restante de nivel Championship o inferior. Pasar de grupos sería logro histórico."),
    # GRUPO H
    (29, "Spain",        "España",           "UEFA",      "H", 1913, 2,   "Luis de la Fuente", "possession", 25.8, 10.0, 9.0,
     "Campeones Euro 2024. Yamal (Barcelona) dudoso para debut por isquiotibial. Rodri vuelve de temporada interrumpida. Sin jugadores del Real Madrid. El mediocampo más profundo del torneo. Si llegan al 100%, favorito más claro."),
    (30, "Saudi Arabia", "Arabia Saudita",   "AFC",       "H", 1508, 56,  "Georgios Donis",    "defensive",  27.0, 3.0, 3.0,
     "DT Donis nombrado el 24 de abril — solo 7 semanas antes del torneo. 25 de 26 jugadores de la Roshn Saudi League (menos competitiva de los 48 clasificados). Solo Saud Abdulhamid juega en Europa. Peores candidatos del grupo H."),
    (31, "Uruguay",      "Uruguay",          "CONMEBOL",  "H", 1762, 18,  "Marcelo Bielsa",    "high_press", 26.5, 7.5, 7.0,
     "Bielsa excluyó a Suárez (39 años). Darwin Núñez llega con bajo ritmo en Liverpool. Araujo-Giménez uno de los mejores dúos defensivos del torneo. Valverde (Real Madrid) en mediocampo. Candidatos claros a octavos."),
    (32, "Cabo Verde",   "Cabo Verde",       "CAF",       "H", 1489, 73,  "Bubista",           "counter",    27.5, 3.5, 6.0,
     "Primera vez en un Mundial. Ganaron su grupo africano en octubre 2025. Bubista lleva 6.5 años en el cargo. Perdieron 4-2 vs Chile pero ganaron vs Finlandia en amistosos. Objetivo realista: ganar a Arabia Saudita."),
    # GRUPO I
    (33, "France",       "Francia",          "UEFA",      "I", 1891, 2,   "Didier Deschamps",  "counter",    27.5, 9.0, 8.0,
     "Número 1 FIFA. Dembélé ganó el Balón de Oro esta temporada. Deschamps su último torneo. Olise (Bayern) brillante. Sin Camavinga ni Kolo Muani. Vestuario siempre tensionado pero la calidad individual es aplastante."),
    (34, "Senegal",      "Senegal",          "CAF",       "I", 1683, 20,  "Pape Thiaw",        "counter",    27.0, 7.0, 8.0,
     "Invictos en clasificación africana. Mané (Al-Nassr) y Koulibaly (Al-Hilal) aún de clase mundial. Eliminaron a Egipto en semis AFCON 2025. El partido vs Francia el 16 de junio define el grupo."),
    (35, "Norway",       "Noruega",          "UEFA",      "I", 1730, 34,  "Ståle Solbakken",   "counter",    26.0, 8.0, 9.0,
     "Clasificación perfecta (8V en 8, 37 goles — récord europeo). Haaland con 16 goles en clasificación. Ødegaard (Arsenal) campeón de la Premier League. Regresan al Mundial tras 28 años. La revelación más probable del torneo."),
    (36, "Iraq",         "Irak",             "AFC",       "I", 1389, 63,  "Graham Arnold",     "defensive",  26.5, 4.0, 6.0,
     "Empate histórico 1-1 ante España en La Coruña el 5 de junio — mejor señal posible previo al torneo. Arnold experto en equipos 'underdog'. Iqbal (Man Utd) y Al-Hamadi (Watford) con nivel europeo. Objetivo: un punto ante Senegal o Noruega."),
    # GRUPO J
    (37, "Argentina",    "Argentina",        "CONMEBOL",  "J", 1962, 1,   "Lionel Scaloni",    "possession", 27.8, 9.5, 7.0,
     "Campeones defensores. Messi con lesión de isquiotibial confirmada — no jugará amistosos previos. Sin Messi al 100% siguen siendo competitivos pero no favoritos globales. Enzo Fernández, Julián Álvarez y Mac Allister son el núcleo."),
    (38, "Algeria",      "Argelia",          "CAF",       "J", 1589, 48,  "Vladimir Petkovic", "counter",    28.0, 6.5, 7.0,
     "Eliminaron a Países Bajos en amistoso el 3 de junio — resultado bombástico. Mahrez regresó de su retiro para el Mundial. Bennacer (Milan) en mediocampo. Petkovic mejoró la defensa significativamente."),
    (39, "Austria",      "Austria",          "UEFA",      "J", 1720, 26,  "Ralf Rangnick",     "high_press", 26.5, 7.0, 8.0,
     "Ganaron su grupo europeo con 19 pts (6V en 8). Pressing intensísimo bajo Rangnick. Arnautović (37, primer Mundial) + Laimer + Schlager en mediocampo. Alaba regresa de lesión. Son el rival más peligroso de Argentina."),
    (40, "Jordan",       "Jordania",         "AFC",       "J", 1443, 87,  "Jamal Sellami",     "defensive",  26.0, 3.5, 6.0,
     "Primera aparición histórica en un Mundial. Al-Tamari (Rennes, 7G+11A) el jugador a seguir. Olwan lesionado. Plantel doméstico pesado. Final Arab Cup 2025 (no ganada). Objetivo: dar buena imagen."),
    # GRUPO K
    (41, "Portugal",     "Portugal",         "UEFA",      "K", 1856, 6,   "Roberto Martínez",  "possession", 27.2, 9.0, 9.0,
     "Campeones Nations League 2025 (vencieron a España en penales). 3+ goles por partido en clasificación. Ronaldo (41 años) es el símbolo pero puede ser distracción táctica. Bruno Fernández + Bernardo Silva = dúo técnicamente top del torneo."),
    (42, "DR Congo",     "R.D. del Congo",   "CAF",       "K", 1432, 53,  "Sébastien Desabre", "counter",    27.5, 5.0, 6.0,
     "Gol en minuto 100 del repechaje ante Jamaica — la clasificación más dramática. Derrotaron a Nigeria y Camerún en clasificación. Wissa (Newcastle) y Lukébakio (Sevilla) con nivel europeo. Desabre ha construido equipo resiliente."),
    (43, "Uzbekistan",   "Uzbekistán",       "AFC",       "K", 1498, 69,  "Fabio Cannavaro",   "mixed",      25.5, 4.0, 5.0,
     "Primera vez en un Mundial. Khusanov (Man City, 44M€) llegó sin minutos en la Premier. Shomurodov (Roma) capitán. Cannavaro tomó el equipo 8 meses antes. Salto de nivel enorme respecto a la AFC."),
    (44, "Colombia",     "Colombia",         "CONMEBOL",  "K", 1738, 11,  "Néstor Lorenzo",    "possession", 26.8, 7.5, 7.5,
     "Finalistas Copa América 2024 (perdieron vs Argentina). Luis Díaz (Bayern Munich) en su mejor momento tras dejar Liverpool. James Rodríguez (4ta Copa) puede dominar partidos en torneos cortos. Arias y Ríos sólidos en mediocampo."),
    # GRUPO L
    (45, "England",      "Inglaterra",       "UEFA",      "L", 1842, 4,   "Thomas Tuchel",     "high_press", 26.5, 8.5, 6.0,
     "Tuchel excluyó a Foden y Palmer por malas temporadas en club. Perdieron vs Japón 1-0 en Wembley (histórico) y vs Uruguay en amistosos previos. Kane + Bellingham + Saka + Rice son el núcleo. Tuchel gana en torneos cortos (FA Cup, Champions)."),
    (46, "Croatia",      "Croacia",          "UEFA",      "L", 1698, 10,  "Zlatko Dalić",      "possession", 29.5, 5.0, 5.0,
     "Generación de 2018-2022 en su límite biológico. Modrić (40, AC Milan) aún domina pero no 90 min intensos. Kovačić llegó de lesión de Aquiles (toda la temporada). Gvardiol de fractura de tibia (dudoso). Pueden llegar a octavos pero no más."),
    (47, "Ghana",        "Ghana",            "CAF",       "L", 1527, 60,  "Carlos Queiroz",    "counter",    26.0, 5.0, 4.0,
     "Queiroz nombrado en abril 2026 — solo 2 meses antes. 4 derrotas consecutivas antes de su llegada. Kudus ausente sin explicación oficial. Williams (Athletic), Semenyo (Bournemouth), Sulemana (Southampton) tienen nivel. Caos institucional como problema central."),
    (48, "Panama",       "Panamá",           "CONCACAF",  "L", 1523, 72,  "Thomas Christiansen","defensive", 28.0, 4.0, 6.0,
     "Segundo Mundial (primero fue Rusia 2018). Christiansen lleva 6 años construyendo cultura de equipo. Godoy (capitán, 157 caps). Compactos defensivamente pero limitados en ataque. Sorprender a Ghana o Croacia es el objetivo."),
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
