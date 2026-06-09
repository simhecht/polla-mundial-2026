"""
update_all_teams.py
Aplica el research cualitativo completo (junio 2026) a la base de datos.
Fuente: investigación de planillas, jugadores y formas de los 48 equipos.
"""
import sqlite3
import sys
import os

DB_PATH = "/tmp/mundial_2026.db"

# (name, elo_rating, form_score, squad_depth_score, tactical_style, coach, notes)
UPDATES = [
    # ─── GRUPO A ───────────────────────────────────────────────────────────────
    ("Mexico",       1718, 7.0, 6.0, "counter",    "Javier Aguirre",
     "Ganó Nations League y Gold Cup 2025. Lozano excluido por indisciplina. 0-4 vs Colombia revela fragilidad. Aguirre prioriza organización defensiva; historial de caer en octavos."),
    ("South Korea",  1627, 6.0, 6.0, "counter",    "Hong Myung-bo",
     "Son Heung-min (32 años, LAFC) llegó con carga física alta. Dependencia total de él. Kim Min-jae (Bayern) sólido en defensa."),
    ("South Africa", 1521, 6.0, 4.0, "defensive",  "Hugo Broos",
     "Broos anuncia que será su último trabajo. Plantel mayoritariamente doméstico. Cuartos AFCON 2023 es su techo real."),
    ("Czechia",      1612, 6.0, 5.0, "mixed",      "Miroslav Koubek",
     "DT Koubek lleva solo 2 partidos al mando — enorme incógnita táctica. Schick (Leverkusen) puede definir el grupo solo. Vuelven al Mundial tras 20 años."),

    # ─── GRUPO B ───────────────────────────────────────────────────────────────
    ("Canada",       1703, 7.0, 7.0, "high_press", "Jesse Marsch",
     "Semifinal Copa América 2024. Davies (Bayern) no estará en el primer partido por lesión de isquiotibial — es su jugador más importante. Jonathan David (Atlético) en gran forma."),
    ("Bosnia",       1558, 6.0, 5.0, "mixed",      "Sergej Barbarez",
     "Eliminaron a Gales e Italia en playoffs vía penales. Džeko tiene 40 años. DT sin experiencia en torneos grandes. El milagro ya fue clasificar."),
    ("Qatar",        1447, 4.0, 4.0, "possession", "Julen Lopetegui",
     "Perdieron 1-0 ante Irlanda en última prueba. Lopetegui historial de fracasos clave. Liga local sin competitividad real. Plantel del ciclo 2022 ya envejecido."),
    ("Switzerland",  1718, 8.0, 7.0, "mixed",      "Murat Yakin",
     "Ganaron 4-1 ante Jordania (31 mayo). Cuartos Euro 2024 (eliminaron a Italia, cayeron ante Inglaterra en penales). Xhaka (Sunderland) y Akanji (Inter) de élite."),

    # ─── GRUPO C ───────────────────────────────────────────────────────────────
    ("Brazil",       1838, 6.0, 8.0, "possession", "Carlo Ancelotti",
     "Ancelotti nombrado tras campaña clasificatoria tortuosa. Neymar (34 años, Al-Nassr) forma física incierta. Rodrygo y Estêvão ausentes. Vini+Raphinha de clase mundial pero defensa inconsistente."),
    ("Morocco",      1747, 7.0, 7.0, "defensive",  "Mohamed Ouahbi",
     "Ouahbi nombrado en marzo 2026 (3 meses antes). Ex-DT Sub-20, ganó Mundial Sub-20 2025 vs Argentina. Hakimi (PSG) y Bounou clave. Cambio de DT es factor desestabilizador."),
    ("Haiti",        1374, 4.0, 3.0, "counter",    "Sébastien Migné",
     "Primera vez en un Mundial en 52 años. Solo un jugador de la liga local. Objetivo declarado: ganar un partido. Brecha técnica abismal con Brasil y Marruecos."),
    ("Scotland",     1631, 6.0, 5.0, "high_press", "Steve Clarke",
     "Primer Mundial desde 1998. Ganaron 4-1 ante Curazao (amistoso). Robertson (Liverpool) y McTominay (Nápoles) lideran. Gordon de portero tiene 43 años. Clarke nunca pasó fase de grupos."),

    # ─── GRUPO D ───────────────────────────────────────────────────────────────
    ("USA",          1752, 6.0, 7.5, "high_press", "Mauricio Pochettino",
     "Perdieron 5-2 vs Bélgica y 2-0 vs Portugal en amistosos — resultados preocupantes. Factor anfitrión y estadio lleno pesan. Pulisic (Milan) es la llave ofensiva. Pochettino mejora equipos en torneos."),
    ("Paraguay",     1569, 6.0, 5.5, "defensive",  "Gustavo Alfaro",
     "6tos en CONMEBOL con 28 pts. Enciso (Brighton) con potencial de desequilibrio individual. Alfaro sólido en torneos cortos con base defensiva."),
    ("Australia",    1628, 6.0, 5.0, "mixed",      "Tony Popovic",
     "Popovic generó 8 partidos invictos para clasificar. Derrotados 1-0 por México en amistoso previo. Leckie y Ryan veteranos con experiencia mundialista. Sin jugador desequilibrante de nivel mundial."),
    ("Turkey",       1680, 7.0, 7.0, "counter",    "Vincenzo Montella",
     "Primer Mundial desde el 3er puesto de 2002. Güler (Real Madrid) y Yıldız (Juventus) jóvenes brillantes. Çalhanoğlu (Inter) en pivote. Montella llevó Turquía a cuartos Euro 2024."),

    # ─── GRUPO E ───────────────────────────────────────────────────────────────
    ("Germany",      1853, 8.0, 8.5, "high_press", "Julian Nagelsmann",
     "5V en 6 partidos de clasificación. Euro 2024 perdido en cuartos vs España — sed de revancha. Musiala-Wirtz probablemente el mejor par creativo del torneo. Neuer regresa a los 40."),
    ("Curacao",      1371, 3.0, 3.0, "counter",    "Dick Advocaat",
     "Advocaat (78 años, el DT más viejo en historia del Mundial) renunció, lo reemplazó Rutten, que renunció, y Advocaat volvió. Escocia los derrotó 4-1. La nación más pequeña del torneo. Solo objetivo: no perder todos."),
    ("Ivory Coast",  1628, 7.0, 6.5, "high_press", "Emerse Faé",
     "Invictos y sin goles en contra en 10 partidos de clasificación africana. Amad Diallo (Man Utd) y Bonny (Inter) en ataque. Faé joven y dinámico. Cayeron en cuartos AFCON 2025 ante Egipto."),
    ("Ecuador",      1648, 8.0, 7.0, "defensive",  "Sebastián Beccacece",
     "Solo 1 derrota en 18 partidos bajo Beccacece. Mejor defensa CONMEBOL (5 goles en 18 partidos). Caicedo (Chelsea) y Pacho (PSG)/Hincapié (Arsenal) son de élite. Valencia 36 años, riesgo en ataque."),

    # ─── GRUPO F ───────────────────────────────────────────────────────────────
    ("Netherlands",  1836, 6.0, 7.0, "possession", "Ronald Koeman",
     "Memphis (Corinthians) apenas 2 apariciones por lesión — llegó sin ritmo. Timber (Arsenal) fuera desde marzo. Van Dijk, Simons, Reijnders y Dumfries sólidos. Koeman históricamente bueno en torneos cortos."),
    ("Japan",        1733, 9.0, 7.5, "high_press", "Hajime Moriyasu",
     "Ganaron en Wembley vs Inglaterra 1-0 en marzo (primera victoria asiática en el estadio). Perfecto en clasificación AFC. Mitoma (Brighton) lesionado — baja importante. El mejor Japón de la historia. Favoritos a sorprender en segunda ronda."),
    ("Sweden",       1648, 7.0, 8.0, "counter",    "Graham Potter",
     "Potter nombrado en octubre 2025 (solo 5 meses). Gyökeres (Arsenal) e Isak (Liverpool) uno de los mejores dúos de delanteros del torneo. Proyecto táctico en construcción."),
    ("Tunisia",      1536, 4.0, 4.0, "defensive",  "Sabri Lamouchi",
     "DT Lamouchi nombrado enero 2026, solo 2 partidos dirigidos. Solo 6 jugadores sobreviven del plantel 2022. Sin identidad táctica clara. Peor momento posible para afrontar a Países Bajos y Japón."),

    # ─── GRUPO G ───────────────────────────────────────────────────────────────
    ("Belgium",      1791, 6.0, 6.5, "mixed",      "Rudi Garcia",
     "Generación de oro en crepúsculo. Lukaku llegó con ~60 minutos de competición toda la temporada. De Bruyne (34) sigue siendo brillante. Garcia sin experiencia internacional en torneos cortos. Bélgica siempre decepciona cuando más importa."),
    ("Egypt",        1589, 6.0, 5.0, "counter",    "Hossam Hassan",
     "Salah (Liverpool) cumple 34 años el día del debut vs Bélgica. 17 de 26 jugadores del fútbol local árabe/egipcio. Dependencia total de Salah. Eliminados en semis AFCON 2025 por Senegal."),
    ("Iran",         1558, 5.0, 4.5, "defensive",  "Amir Ghalenoei",
     "Azmoun excluido polémicamente. Taremi (Inter) vivió temporada irregular. Ganaron 3-1 ante Gambia en amistoso. Irán defensivo e intenso pero nivel técnico insuficiente para superar el grupo."),
    ("New Zealand",  1357, 5.0, 3.5, "defensive",  "Darren Bazeley",
     "Rankeados ~85 en el mundo. Wood (Nottingham Forest, 45 goles, capitán) sigue relevante en Premier. Plantel restante de nivel Championship o inferior. Pasar de grupos sería logro histórico."),

    # ─── GRUPO H ───────────────────────────────────────────────────────────────
    ("Spain",        1913, 9.0, 10.0, "possession","Luis de la Fuente",
     "Campeones Euro 2024. Yamal (Barcelona) dudoso para debut por isquiotibial. Rodri vuelve de temporada interrumpida. Sin jugadores del Real Madrid. El mediocampo más profundo del torneo. Si llegan al 100%, favorito más claro."),
    ("Saudi Arabia", 1508, 3.0, 3.0, "defensive",  "Georgios Donis",
     "DT Donis nombrado el 24 de abril — solo 7 semanas antes del torneo. 25 de 26 jugadores de la Roshn Saudi League (menos competitiva de los 48 clasificados). Solo Saud Abdulhamid juega en Europa. Peores candidatos del grupo H."),
    ("Uruguay",      1762, 7.0, 7.5, "high_press", "Marcelo Bielsa",
     "Bielsa excluyó a Suárez (39 años). Darwin Núñez llega con bajo ritmo en Liverpool. Araujo-Giménez uno de los mejores dúos defensivos del torneo. Valverde (Real Madrid) en mediocampo. Candidatos claros a octavos."),
    ("Cabo Verde",   1489, 6.0, 3.5, "counter",    "Bubista",
     "Primera vez en un Mundial. Ganaron su grupo africano en octubre 2025. Bubista lleva 6.5 años en el cargo. Perdieron 4-2 vs Chile pero ganaron vs Finlandia en amistosos. Objetivo realista: ganar a Arabia Saudita."),

    # ─── GRUPO I ───────────────────────────────────────────────────────────────
    ("France",       1891, 8.0, 9.0, "counter",    "Didier Deschamps",
     "Número 1 FIFA. Dembélé ganó el Balón de Oro esta temporada. Deschamps su último torneo. Olise (Bayern) brillante. Sin Camavinga ni Kolo Muani. Vestuario siempre tensionado pero la calidad individual es aplastante."),
    ("Senegal",      1683, 8.0, 7.0, "counter",    "Pape Thiaw",
     "Invictos en clasificación africana. Mané (Al-Nassr) y Koulibaly (Al-Hilal) aún de clase mundial. Eliminaron a Egipto en semis AFCON 2025. El partido vs Francia el 16 de junio define el grupo."),
    ("Norway",       1730, 9.0, 8.0, "counter",    "Ståle Solbakken",
     "Clasificación perfecta (8V en 8, 37 goles — récord europeo). Haaland con 16 goles en clasificación. Ødegaard (Arsenal) campeón de la Premier League. Regresan al Mundial tras 28 años. La revelación más probable del torneo."),
    ("Iraq",         1389, 6.0, 4.0, "defensive",  "Graham Arnold",
     "Empate histórico 1-1 ante España en La Coruña el 5 de junio — mejor señal posible previo al torneo. Arnold experto en equipos 'underdog'. Iqbal (Man Utd) y Al-Hamadi (Watford) con nivel europeo. Objetivo: un punto ante Senegal o Noruega."),

    # ─── GRUPO J ───────────────────────────────────────────────────────────────
    ("Argentina",    1962, 7.0, 9.5, "possession", "Lionel Scaloni",
     "Campeones defensores. Messi con lesión de isquiotibial confirmada — no jugará amistosos previos. Sin Messi al 100% siguen siendo competitivos pero no favoritos globales. Enzo Fernández, Julián Álvarez y Mac Allister son el núcleo."),
    ("Algeria",      1589, 7.0, 6.5, "counter",    "Vladimir Petkovic",
     "Eliminaron a Países Bajos en amistoso el 3 de junio — resultado bombástico. Mahrez regresó de su retiro para el Mundial. Bennacer (Milan) en mediocampo. Petkovic mejoró la defensa significativamente."),
    ("Austria",      1720, 8.0, 7.0, "high_press", "Ralf Rangnick",
     "Ganaron su grupo europeo con 19 pts (6V en 8). Pressing intensísimo bajo Rangnick. Arnautović (37, primer Mundial) + Laimer + Schlager en mediocampo. Alaba regresa de lesión. Son el rival más peligroso de Argentina."),
    ("Jordan",       1443, 6.0, 3.5, "defensive",  "Jamal Sellami",
     "Primera aparición histórica en un Mundial. Al-Tamari (Rennes, 7G+11A) el jugador a seguir. Olwan lesionado. Plantel doméstico pesado. Final Arab Cup 2025 (no ganada). Objetivo: dar buena imagen."),

    # ─── GRUPO K ───────────────────────────────────────────────────────────────
    ("Portugal",     1856, 9.0, 9.0, "possession", "Roberto Martínez",
     "Campeones Nations League 2025 (vencieron a España en penales). 3+ goles por partido en clasificación. Ronaldo (41 años) es el símbolo pero puede ser distracción táctica. Bruno Fernández + Bernardo Silva = dúo técnicamente top del torneo."),
    ("DR Congo",     1432, 6.0, 5.0, "counter",    "Sébastien Desabre",
     "Gol en minuto 100 del repechaje ante Jamaica — la clasificación más dramática. Derrotaron a Nigeria y Camerún en clasificación. Wissa (Newcastle) y Lukébakio (Sevilla) con nivel europeo. Desabre ha construido equipo resiliente."),
    ("Uzbekistan",   1498, 5.0, 4.0, "mixed",      "Fabio Cannavaro",
     "Primera vez en un Mundial. Khusanov (Man City, 44M€) llegó sin minutos en la Premier. Shomurodov (Roma) capitán. Cannavaro tomó el equipo 8 meses antes. Salto de nivel enorme respecto a la AFC."),
    ("Colombia",     1738, 7.5, 7.5, "possession", "Néstor Lorenzo",
     "Finalistas Copa América 2024 (perdieron vs Argentina). Luis Díaz (Bayern Munich) en su mejor momento tras dejar Liverpool. James Rodríguez (4ta Copa) puede dominar partidos en torneos cortos. Arias y Ríos sólidos en mediocampo."),

    # ─── GRUPO L ───────────────────────────────────────────────────────────────
    ("England",      1842, 6.0, 8.5, "high_press", "Thomas Tuchel",
     "Tuchel excluyó a Foden y Palmer por malas temporadas en club. Perdieron vs Japón 1-0 en Wembley (histórico) y vs Uruguay en amistosos previos. Kane + Bellingham + Saka + Rice son el núcleo. Tuchel gana en torneos cortos (FA Cup, Champions)."),
    ("Croatia",      1698, 5.0, 5.0, "possession", "Zlatko Dalić",
     "Generación de 2018-2022 en su límite biológico. Modrić (40, AC Milan) aún domina pero no 90 min intensos. Kovačić llegó de lesión de Aquiles (toda la temporada). Gvardiol de fractura de tibia (dudoso). Pueden llegar a octavos pero no más."),
    ("Ghana",        1527, 4.0, 5.0, "counter",    "Carlos Queiroz",
     "Queiroz nombrado en abril 2026 — solo 2 meses antes. 4 derrotas consecutivas antes de su llegada. Kudus ausente sin explicación oficial. Williams (Athletic), Semenyo (Bournemouth), Sulemana (Southampton) tienen nivel. Caos institucional como problema central."),
    ("Panama",       1523, 6.0, 4.0, "defensive",  "Thomas Christiansen",
     "Segundo Mundial (primero fue Rusia 2018). Christiansen lleva 6 años construyendo cultura de equipo. Godoy (capitán, 157 caps). Compactos defensivamente pero limitados en ataque. Sorprender a Ghana o Croacia es el objetivo."),
]

def run():
    conn = sqlite3.connect(DB_PATH)
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
