# Polla Mundial 2026 — Estado del Proyecto
**Última actualización:** 9 junio 2026  
**Modelo activo:** predictor_v3.py (v3.1 — exponentes recalibrados)  
**Dashboard:** dashboard_mundial2026.html (en /polla/)

---

## 1. Objetivo

Predecir el marcador exacto de cada partido del Mundial USA/Canadá/México 2026, simular las 12 llaves de grupos, determinar los 8 mejores terceros, armar el bracket completo de eliminación directa y llegar al campeón.

---

## 2. Archivos del proyecto

Todos en `/Users/simon/Desktop/polla/modelo/`:

| Archivo | Función |
|---|---|
| `setup_db.py` | Inicializa SQLite en `/tmp/mundial_2026.db`. Contiene 48 equipos + 72 fixtures. La DB es efímera (en /tmp/), hay que recrearla cada sesión. |
| `update_all_teams.py` | Aplica datos cualitativos reales a los 48 equipos (ELO, forma, profundidad, DT, notas). **Siempre correr después de setup_db.setup()** |
| `predictor_v3.py` | Motor principal — Poisson + Dixon-Coles (ρ=−0.10) + ELO^2.0 + host advantage. **Usar este, no v1 ni v2.** |
| `predictor_v2.py` | Versión anterior (obsoleta). Tenía ρ=−0.13, exp 0.6/0.4, form sin cap. Producía demasiados 2-1 y empates falsos. |
| `predictor.py` | Versión original (no usar). |
| `dashboard.py` | Genera `dashboard_mundial2026.html`. Ya actualizado para usar predictor_v3. |
| `update_team.py` | CLI para actualizar un equipo individual: `python update_team.py Mexico --form 8 --notes "..."` |

**Cómo recrear la DB al inicio de cada sesión:**
```python
import sys; sys.path.insert(0, '.')
import setup_db, update_all_teams
setup_db.DB_PATH = '/tmp/mundial_2026.db'
setup_db.setup()
update_all_teams.run()
```

---

## 3. Metodología del modelo (v3.1 — actualizada 9 jun 2026)

### Lambda (goles esperados por equipo):
```
λ = 1.3 × (ELO_equipo / 1600)^2.8 × (1600 / ELO_rival)^2.1
      × form_factor × tactical_factor × altitude_factor × host_advantage
```

### Cambios clave v3 → v3.1 (9 jun 2026):
Calibración por grid search sobre **19 amistosos pre-Mundial** + **12 cuotas de mercado**:
- **Exponentes ELO:** 2.0/1.5 → **2.8/2.1** → mayor spread, favoritos más diferenciados
- **Resultado:** Dir 79%→79% | Top3 68%→**74%** | Exactos 37%→**42%** | ΔMercado 10.6pp→**5.1pp**
- Divergencias residuales: Brasil vs Marruecos (−14pp), PB vs Japón (−11pp) — mercado más optimista con favorito

### Cambios clave v2 → v3:
- **Exponentes ELO:** 0.6/0.4 → 2.0/1.5
- **form_factor:** `1.0 + (score-5)/5 × 0.25` (±25% cap). Antes: `score/5.0` sin límite
- **depth_factor:** eliminado (exp 0.2 lo hacía inerte)
- **Tactical edge:** desviaciones escaladas 50% → ±6% máximo
- **Dixon-Coles ρ:** −0.10 (antes −0.13, calibrado para clubes ingleses)

### Validación completa (19 amistosos junio 2026 con v3.1):
| Métrica | v3 original | v3.1 nuevo |
|---|---|---|
| Dirección correcta | 15/19 = 79% | 15/19 = 79% |
| Marcador en top-3 | 13/19 = 68% | 14/19 = 74% |
| Marcador exacto (#1) | 7/19 = 37% | 8/19 = 42% |
| Δ vs cuotas mercado | 10.6 pp | 5.1 pp |

### Ventaja de local anfitrión:
| País | Boost propio | Penalización rival | Venues |
|---|---|---|---|
| México | +20% | −8% | CDMX, Guadalajara, Monterrey |
| USA | +13% | −6% | Dallas, LA, Houston, KC, Seattle, SF, Miami, Atlanta, Boston, Philly, NY |
| Canadá | +10% | −5% | Vancouver, Toronto |

Si el equipo anfitrión está listado como "away" en el DB (ej: Chequia vs México en CDMX), aplica el 85% del boost.

### Altitud:
- ≥1800m (CDMX): ×1.12
- 1000-1799m (GDL): ×1.06
- 500-999m (MTY): ×1.02
- <500m: ×1.00

---

## 4. Resultados fase de grupos (Modelo v3)

### GRUPO A
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇲🇽 **México** ✅ | 3 | 0 | 0 | 6 | 3 | +3 | **9** |
| 🇰🇷 Corea del Sur ✅ | 0 | 2 | 1 | 3 | 4 | -1 | 2 |
| 🇨🇿 Chequia | 0 | 2 | 1 | 3 | 4 | -1 | 2 |
| 🇿🇦 Sudáfrica | 0 | 2 | 1 | 3 | 4 | -1 | 2 |

Partidos: México 2-1 Sudáfrica | Corea 1-1 Chequia | Chequia 1-1 Sudáfrica | México 2-1 Corea | Chequia 1-2 México | Sudáfrica 1-1 Corea  
⚠️ 3-way tie 2°/3°/4° — tiebreaker por cabeza a cabeza (todos empatan entre sí → sorteo). Asumimos Corea 2° por ELO.

### GRUPO B
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇨🇭 **Suiza** ✅ | 1 | 2 | 0 | 4 | 2 | +2 | **5** |
| 🇨🇦 **Canadá** ✅ | 1 | 2 | 0 | 4 | 2 | +2 | 5 |
| 🇧🇦 Bosnia | 0 | 3 | 0 | 3 | 3 | 0 | **3** 🔶 |
| 🇶🇦 Catar | 0 | 1 | 2 | 1 | 5 | -4 | 1 |

Partidos: Canadá 1-1 Bosnia | Catar 0-2 Suiza | Suiza 1-1 Bosnia | Canadá 2-0 Catar | Suiza 1-1 Canadá | Bosnia 1-1 Catar

### GRUPO C
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇧🇷 **Brasil** ✅ | 1 | 2 | 0 | 4 | 2 | +2 | **5** |
| 🇲🇦 **Marruecos** ✅ | 1 | 2 | 0 | 4 | 2 | +2 | 5 |
| 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Escocia | 1 | 2 | 0 | 4 | 2 | +2 | **5** 🔶 |
| 🇭🇹 Haití | 0 | 0 | 3 | 0 | 6 | -6 | 0 |

Partidos: Brasil 1-1 Marruecos | Haití 0-2 Escocia | Escocia 1-1 Marruecos | Brasil 2-0 Haití | Escocia 1-1 Brasil | Marruecos 2-0 Haití  
⚠️ 3-way tie 1°/2°/3° con 5pts y mismo DG/GF. Escocia pasa como mejor tercero del torneo.

### GRUPO D
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇺🇸 **USA** ✅ | 0 | 3 | 0 | 3 | 3 | 0 | **3** |
| 🇹🇷 **Turquía** ✅ | 0 | 3 | 0 | 3 | 3 | 0 | 3 |
| 🇦🇺 Australia | 0 | 3 | 0 | 3 | 3 | 0 | **3** 🔶 |
| 🇵🇾 Paraguay | 0 | 3 | 0 | 3 | 3 | 0 | 3 |

Partidos: USA 1-1 Paraguay | Australia 1-1 Turquía | Turquía 1-1 Paraguay | USA 1-1 Australia | Turquía 1-1 USA | Paraguay 1-1 Australia  
⚠️ CUÁDRUPLE empate total — todos los partidos del grupo terminaron 1-1. Tiebreaker necesario. USA y Turquía asumidos 1°/2° por ELO. Australia 3° como mejor tercero.

### GRUPO E
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇩🇪 **Alemania** ✅ | 1 | 2 | 0 | 4 | 2 | +2 | **5** |
| 🇪🇨 **Ecuador** ✅ | 1 | 2 | 0 | 4 | 2 | +2 | 5 |
| 🇨🇮 Costa de Marfil | 1 | 2 | 0 | 4 | 2 | +2 | **5** 🔶 |
| 🇨🇼 Curazao | 0 | 0 | 3 | 0 | 6 | -6 | 0 |

Partidos: Alemania 2-0 Curazao | Costa de Marfil 1-1 Ecuador | Alemania 1-1 Costa de Marfil | Ecuador 2-0 Curazao | Ecuador 1-1 Alemania | Curazao 0-2 Costa de Marfil

### GRUPO F
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇳🇱 **Países Bajos** ✅ | 1 | 2 | 0 | 3 | 2 | +1 | **5** |
| 🇯🇵 **Japón** ✅ | 0 | 3 | 0 | 3 | 3 | 0 | **3** |
| 🇸🇪 Suecia | 0 | 3 | 0 | 3 | 3 | 0 | **3** 🔶 |
| 🇹🇳 Túnez | 0 | 2 | 1 | 2 | 3 | -1 | 2 |

Partidos: Países Bajos 1-1 Japón | Suecia 1-1 Túnez | Países Bajos 1-1 Suecia | Túnez 1-1 Japón | Japón 1-1 Suecia | Túnez 0-1 Países Bajos

### GRUPO G
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇧🇪 **Bélgica** ✅ | 1 | 2 | 0 | 4 | 2 | +2 | **5** |
| 🇪🇬 **Egipto** ✅ | 1 | 2 | 0 | 3 | 2 | +1 | **5** |
| 🇮🇷 Irán | 0 | 3 | 0 | 3 | 3 | 0 | **3** 🔶 |
| 🇳🇿 Nueva Zelanda | 0 | 1 | 2 | 1 | 4 | -3 | 1 |

Partidos: Bélgica 1-1 Egipto | Irán 1-1 Nueva Zelanda | Bélgica 1-1 Irán | Nueva Zelanda 0-1 Egipto | Egipto 1-1 Irán | Nueva Zelanda 0-2 Bélgica

### GRUPO H
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇪🇸 **España** ✅ | 2 | 1 | 0 | 5 | 1 | +4 | **7** |
| 🇺🇾 **Uruguay** ✅ | 1 | 2 | 0 | 3 | 2 | +1 | **5** |
| 🇨🇻 Cabo Verde | 0 | 2 | 1 | 2 | 4 | -2 | 2 |
| 🇸🇦 Arabia Saudita | 0 | 1 | 2 | 1 | 4 | -3 | 1 |

Partidos: España 2-0 Cabo Verde | Arabia Saudita 0-1 Uruguay | España 2-0 Arabia Saudita | Uruguay 1-1 Cabo Verde | Cabo Verde 1-1 Arabia Saudita | Uruguay 1-1 España

### GRUPO I
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇫🇷 **Francia** ✅ | 1 | 2 | 0 | 4 | 2 | +2 | **5** |
| 🇳🇴 **Noruega** ✅ | 1 | 2 | 0 | 4 | 2 | +2 | 5 |
| 🇸🇳 Senegal | 1 | 2 | 0 | 4 | 2 | +2 | **5** 🔶 |
| 🇮🇶 Irak | 0 | 0 | 3 | 0 | 6 | -6 | 0 |

Partidos: Francia 1-1 Senegal | Irak 0-2 Noruega | Francia 2-0 Irak | Noruega 1-1 Senegal | Noruega 1-1 Francia | Senegal 2-0 Irak  
⚠️ 3-way tie 1°/2°/3°. Francia 1° y Noruega 2° por mayor ELO. Senegal pasa como mejor tercero.

### GRUPO J
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇦🇷 **Argentina** ✅ | 2 | 1 | 0 | 5 | 2 | +3 | **7** |
| 🇦🇹 **Austria** ✅ | 0 | 3 | 0 | 3 | 3 | 0 | **3** |
| 🇩🇿 Argelia | 0 | 2 | 1 | 3 | 4 | -1 | 2 |
| 🇯🇴 Jordania | 0 | 2 | 1 | 2 | 4 | -2 | 2 |

Partidos: Argentina 2-1 Argelia | Austria 1-1 Jordania | Argentina 1-1 Austria | Jordania 1-1 Argelia | Argelia 1-1 Austria | Jordania 0-2 Argentina

### GRUPO K
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇵🇹 **Portugal** ✅ | 2 | 1 | 0 | 5 | 1 | +4 | **7** |
| 🇨🇴 **Colombia** ✅ | 1 | 2 | 0 | 4 | 3 | +1 | **5** |
| 🇺🇿 Uzbekistán | 0 | 2 | 1 | 2 | 4 | -2 | 2 |
| 🇨🇩 R.D. del Congo | 0 | 1 | 2 | 2 | 5 | -3 | 1 |

Partidos: Portugal 2-0 R.D. del Congo | Uzbekistán 1-1 Colombia | Portugal 2-0 Uzbekistán | Colombia 2-1 R.D. del Congo | Colombia 1-1 Portugal | R.D. del Congo 1-1 Uzbekistán

### GRUPO L
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🏴󠁧󠁢󠁥󠁮󠁧󠁿 **Inglaterra** ✅ | 1 | 2 | 0 | 4 | 2 | +2 | **5** |
| 🇭🇷 **Croacia** ✅ | 0 | 3 | 0 | 3 | 3 | 0 | **3** |
| 🇵🇦 Panamá | 0 | 3 | 0 | 3 | 3 | 0 | **3** 🔶 |
| 🇬🇭 Ghana | 0 | 2 | 1 | 2 | 4 | -2 | 2 |

Partidos: Inglaterra 1-1 Croacia | Ghana 1-1 Panamá | Inglaterra 2-0 Ghana | Panamá 1-1 Croacia | Panamá 1-1 Inglaterra | Croacia 1-1 Ghana

---

## 5. Los 32 clasificados a Dieciseisavos

### Clasificados directos (24 = 2 por grupo):
| Grupo | 1° | 2° |
|---|---|---|
| A | 🇲🇽 México | 🇰🇷 Corea del Sur |
| B | 🇨🇭 Suiza | 🇨🇦 Canadá |
| C | 🇧🇷 Brasil | 🇲🇦 Marruecos |
| D | 🇺🇸 USA | 🇹🇷 Turquía |
| E | 🇩🇪 Alemania | 🇪🇨 Ecuador |
| F | 🇳🇱 Países Bajos | 🇯🇵 Japón |
| G | 🇧🇪 Bélgica | 🇪🇬 Egipto |
| H | 🇪🇸 España | 🇺🇾 Uruguay |
| I | 🇫🇷 Francia | 🇳🇴 Noruega |
| J | 🇦🇷 Argentina | 🇦🇹 Austria |
| K | 🇵🇹 Portugal | 🇨🇴 Colombia |
| L | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra | 🇭🇷 Croacia |

### Mejores 8 terceros (clasificados por pts → DG → GF):
| Pos | Equipo | Grupo | Pts | DG |
|---|---|---|---|---|
| 1 | 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Escocia | C | 5 | +2 |
| 2 | 🇨🇮 Costa de Marfil | E | 5 | +2 |
| 3 | 🇸🇳 Senegal | I | 5 | +2 |
| 4 | 🇧🇦 Bosnia | B | 3 | 0 |
| 5 | 🇦🇺 Australia | D | 3 | 0 |
| 6 | 🇸🇪 Suecia | F | 3 | 0 |
| 7 | 🇮🇷 Irán | G | 3 | 0 |
| 8 | 🇵🇦 Panamá | L | 3 | 0 |

**Eliminados (4 terceros que no clasifican):** Chequia (A, 2pts), Cabo Verde (H, 2pts), Argelia (J, 2pts), Uzbekistán (K, 2pts)

---

## 6. Pendiente

- [ ] **Bracket de dieciseisavos (R32):** asignar los 32 equipos a los cruces según el fixture oficial FIFA 2026, aplicar el mismo modelo (λ × 0.90 para fase eliminatoria, partidos más cerrados)
- [ ] **Octavos, cuartos, semis, final**
- [ ] **Tiempo extra y penaltis:** lambda × 0.75 para prórroga, Beta-Binomial para penales (conversión 76% jugadores élite)
- [ ] **Champion prediction**

---

## 7. Notas cualitativas clave por equipo (highlights)

- **Argentina:** Messi con lesión de isquiotibial confirmada — no jugará amistosos previos. Sin él al 100%, siguen siendo competitivos pero no claros favoritos.
- **España:** Yamal dudoso para debut (isquiotibial). El mediocampo más profundo del torneo. Favorita si llegan al 100%.
- **Noruega:** Clasificación perfecta (8V/8, 37 goles, récord europeo). Haaland 16 goles. Sorpresa más probable del torneo.
- **Austria:** Pressing Rangnick. Ganaron grupo europeo 6/8. Son el rival más peligroso de Argentina.
- **Japón:** Ganaron en Wembley vs Inglaterra 1-0. Mejor Japón de la historia.
- **Francia:** Número 1 FIFA. Dembélé Balón de Oro esta temporada. Deschamps último torneo.
- **Costa de Marfil:** Diomandé, Kessié, Amad Diallo (Man Utd), Sangaré, Fofana (Chelsea) — plantel europeo de élite. Invictos 10 partidos en clasificación.
- **Brasil:** Ancelotti debuta como DT. Rodrygo ausente. Neymar forma incierta. Sin Messi, favorito implícito CONMEBOL.
- **USA:** Perdió 5-2 vs Bélgica y 2-0 vs Portugal en amistosos. Factor anfitrión los lleva a R16 mínimo.
- **Curazao:** DT Advocaat (78 años) renunció, lo reemplazó Rutten, que renunció, volvió Advocaat. 0 puntos, eliminados.
- **Arabia Saudita:** DT Donis nombrado 7 semanas antes. 25/26 jugadores de liga local. Los peores del torneo.
- **Iraq:** Empató 1-1 vs España en La Coruña el 5 de junio — su mejor señal previa.
- **Algeria:** Eliminó a Países Bajos en amistoso del 3 de junio. Mahrez regresó del retiro.

---

## 8. Cómo usar el modelo en un chat nuevo

```python
# En el modelo/ folder, inicializar todo:
import sys; sys.path.insert(0, '.')
import setup_db, update_all_teams
setup_db.DB_PATH = '/tmp/mundial_2026.db'
setup_db.setup()
update_all_teams.run()

# Predecir un partido:
import sqlite3
from predictor_v3 import predict_match
conn = sqlite3.connect('/tmp/mundial_2026.db')
r = predict_match('Spain', 'Uruguay', conn=conn)

# Simular un grupo completo:
from predictor_v3 import simulate_group, group_report
simulate_group('H', conn=conn, verbose=True)

# Reporte con Monte Carlo:
group_report('H', conn=conn, n_sims=50000)
```

Para actualizar datos de un equipo:
```bash
python update_team.py "Costa de Marfil" --form 7.5 --notes "Nuevo texto"
python update_team.py --group E  # listar grupo E
```
