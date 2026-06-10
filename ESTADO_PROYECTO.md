# Polla Mundial 2026 — Estado del Proyecto
**Última actualización:** 9 junio 2026  
**Modelo activo:** predictor_v3.py (v3.2 — bracket eliminatorio dinámico)  
**Dashboard:** dashboard_mundial2026.html (en /polla/)

---

## 1. Objetivo

Predecir el marcador exacto de cada partido del Mundial USA/Canadá/México 2026, simular las 12 llaves de grupos, determinar los 8 mejores terceros, armar el bracket completo de eliminación directa y llegar al campeón.

---

## 2. Archivos del proyecto

Todos en `/Users/simon/Desktop/polla/modelo/`:

| Archivo | Función |
|---|---|
| `setup_db.py` | Inicializa SQLite en `modelo/data/mundial_2026.db`. Contiene 48 equipos + 72 fixtures. **Los datos cualitativos (ELO, forma, notas) ya están embebidos aquí**; no es necesario correr `update_all_teams` después. |
| `update_all_teams.py` | Re-aplica los datos cualitativos de `setup_db.TEAMS` a la DB (verificación idempotente, útil si se editó la DB manualmente). Ya no es obligatorio tras `setup_db.setup()`. |
| `predictor_v3.py` | Motor principal — Poisson + Dixon-Coles (ρ=−0.10) + ELO^2.8/2.1 + host advantage. **Usar este, no v1 ni v2.** |
| `simulate_knockout.py` | Bracket eliminatorio R32→Final. Deriva los 32 clasificados dinámicamente de `simulate_group`. |
| `predictor_v2.py` | Versión anterior (obsoleta). Tenía ρ=−0.13, exp 0.6/0.4, form sin cap. |
| `predictor.py` | Versión original (no usar). |
| `dashboard.py` | Genera `dashboard_mundial2026.html`. Usa predictor_v3 y simulate_knockout. |
| `update_team.py` | CLI para actualizar un equipo individual: `python update_team.py Mexico --form 8 --notes "..."` |

**Cómo inicializar al inicio de cada sesión:**
```python
import sys; sys.path.insert(0, '.')
import setup_db
setup_db.setup()
# update_all_teams.run() es opcional — los datos ya vienen de setup_db
```

---

## 3. Metodología del modelo (v3.2 — actualizada 9 jun 2026)

### Lambda (goles esperados por equipo):
```
λ = 1.3 × (ELO_equipo / 1600)^2.8 × (1600 / ELO_rival)^2.1
      × form_factor × tactical_factor × altitude_factor × host_advantage
```

### Cambios clave v3.1 → v3.2 (9 jun 2026):
- **Bracket R32 dinámico:** los clasificados ya no están hardcodeados. Se derivan del escenario determinista del modelo (`simulate_group` para A-L): 1° y 2° de cada grupo + los 8 mejores terceros (ranking por pts → DG → GF → ELO).
- **Sedes en eliminatoria:** host advantage y altitud aplican en todos los partidos KO según el calendario oficial FIFA 2026.
- **ET_FACTOR = 1/3** (prórroga = 30 de 90 minutos; antes 0.50, erróneo).
- **Monte Carlo KO** muestrea desde `score_matrix_dc` (Dixon-Coles) en 90' y prórroga, consistente con el motor analítico.
- **Regla de decisión del marcador (predict_ko_match):** igual que `predict_match`, el marcador predicho es el más probable CONDICIONADO al resultado más probable (victoria local, empate o victoria visitante). Esto evita el sesgo modal a 1-1 que producía predict_match en versiones anteriores.

### Cambios clave v3 → v3.1 (9 jun 2026):
Calibración por grid search sobre **19 amistosos pre-Mundial** + **12 cuotas de mercado**:
- **Exponentes ELO:** 2.0/1.5 → **2.8/2.1** → mayor spread, favoritos más diferenciados
- **Resultado:** Dir 79%→79% | Top3 68%→**74%** | Exactos 37%→**42%** | ΔMercado 10.6pp→**5.1pp**
- **Corrección Dixon-Coles completa:** τ(1,1) = 1−ρ (antes implementación incompleta)
- Divergencias residuales: Brasil vs Marruecos (−14pp), PB vs Japón (−11pp) — mercado más optimista con favorito

### Cambios clave v2 → v3:
- **Exponentes ELO:** 0.6/0.4 → 2.0/1.5
- **form_factor:** `1.0 + (score-5)/5 × 0.25` (±25% cap). Antes: `score/5.0` sin límite
- **depth_factor:** eliminado (exp 0.2 lo hacía inerte)
- **Tactical edge:** desviaciones escaladas 50% → ±6% máximo
- **Dixon-Coles ρ:** −0.10 (antes −0.13, calibrado para clubes ingleses)

### Validación (19 amistosos junio 2026 con v3.1):
| Métrica | v3 original | v3.1 nuevo |
|---|---|---|
| Dirección correcta | 15/19 = 79% | 15/19 = 79% |
| Marcador en top-3 | 13/19 = 68% | 14/19 = 74% |
| Marcador exacto (#1) | 7/19 = 37% | 8/19 = 42% |
| Δ vs cuotas mercado | 10.6 pp | 5.1 pp |

⚠️ **Advertencia:** estas métricas se midieron sobre los mismos 19 amistosos usados para calibrar (in-sample), por lo que son optimistas.

### Ventaja de local anfitrión:
| País | Boost propio | Penalización rival | Venues |
|---|---|---|---|
| México | +20% | −13% | CDMX, Guadalajara, Monterrey |
| USA | +13% | −6% | Dallas, LA, Houston, KC, Seattle, SF, Miami, Atlanta, Boston, Philly, NY |
| Canadá | +10% | −5% | Vancouver, Toronto |

Si el equipo anfitrión está listado como "away" en el DB (ej: Chequia vs México en CDMX), aplica el 85% del boost y de la penalización.

La penalización de México (−13%) está fijada por encima del umbral 1 − 1/1.12 ≈ 10.7% (y 0.107/0.85 ≈ 12.6% para el caso "away en DB") para que el boost de altitud de CDMX (×1.12) nunca deje al rival con más lambda que en sede neutral.

### Altitud:
- ≥1800m (CDMX): ×1.12
- 1000-1799m (GDL): ×1.06
- 500-999m (MTY): ×1.02
- <500m: ×1.00

---

## 4. Resultados fase de grupos (Modelo v3.2 — salida real 9 jun 2026)

### GRUPO A
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇲🇽 **México** ✅ | 3 | 0 | 0 | 6 | 2 | +4 | **9** |
| 🇰🇷 **Corea del Sur** ✅ | 2 | 0 | 1 | 5 | 4 | +1 | **6** |
| 🇨🇿 Chequia | 1 | 0 | 2 | 4 | 5 | −1 | 3 |
| 🇿🇦 Sudáfrica | 0 | 0 | 3 | 2 | 6 | −4 | 0 |

Partidos: México 2-0 Sudáfrica | Corea 2-1 Chequia | Chequia 2-1 Sudáfrica | México 2-1 Corea | Chequia 1-2 México | Sudáfrica 1-2 Corea

### GRUPO B
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇨🇦 **Canadá** ✅ | 3 | 0 | 0 | 6 | 2 | +4 | **9** |
| 🇨🇭 **Suiza** ✅ | 2 | 0 | 1 | 5 | 3 | +2 | **6** |
| 🇧🇦 Bosnia y Herz. | 1 | 0 | 2 | 3 | 4 | −1 | 3 |
| 🇶🇦 Catar | 0 | 0 | 3 | 0 | 5 | −5 | 0 |

Partidos: Canadá 2-1 Bosnia | Catar 0-2 Suiza | Suiza 2-1 Bosnia | Canadá 2-0 Catar | Suiza 1-2 Canadá | Bosnia 1-0 Catar

### GRUPO C
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇧🇷 **Brasil** ✅ | 3 | 0 | 0 | 6 | 2 | +4 | **9** |
| 🇲🇦 **Marruecos** ✅ | 2 | 0 | 1 | 5 | 3 | +2 | **6** |
| 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Escocia | 1 | 0 | 2 | 4 | 4 | 0 | 3 |
| 🇭🇹 Haití | 0 | 0 | 3 | 0 | 6 | −6 | 0 |

Partidos: Brasil 2-1 Marruecos | Haití 0-2 Escocia | Escocia 1-2 Marruecos | Brasil 2-0 Haití | Escocia 1-2 Brasil | Marruecos 2-0 Haití

### GRUPO D
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇺🇸 **Estados Unidos** ✅ | 3 | 0 | 0 | 6 | 2 | +4 | **9** |
| 🇹🇷 **Turquía** ✅ | 2 | 0 | 1 | 5 | 4 | +1 | **6** |
| 🇦🇺 Australia | 1 | 0 | 2 | 3 | 4 | −1 | 3 |
| 🇵🇾 Paraguay | 0 | 0 | 3 | 1 | 5 | −4 | 0 |

Partidos: USA 2-0 Paraguay | Australia 1-2 Turquía | Turquía 2-1 Paraguay | USA 2-1 Australia | Turquía 1-2 USA | Paraguay 0-1 Australia

### GRUPO E
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇩🇪 **Alemania** ✅ | 3 | 0 | 0 | 7 | 2 | +5 | **9** |
| 🇪🇨 **Ecuador** ✅ | 2 | 0 | 1 | 5 | 3 | +2 | **6** |
| 🇨🇮 Costa de Marfil | 1 | 0 | 2 | 4 | 4 | 0 | 3 |
| 🇨🇼 Curazao | 0 | 0 | 3 | 0 | 7 | −7 | 0 |

Partidos: Alemania 3-0 Curazao | Costa de Marfil 1-2 Ecuador | Alemania 2-1 Costa de Marfil | Ecuador 2-0 Curazao | Ecuador 1-2 Alemania | Curazao 0-2 Costa de Marfil

### GRUPO F
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇳🇱 **Países Bajos** ✅ | 3 | 0 | 0 | 6 | 2 | +4 | **9** |
| 🇯🇵 **Japón** ✅ | 2 | 0 | 1 | 5 | 3 | +2 | **6** |
| 🇸🇪 Suecia | 1 | 0 | 2 | 3 | 4 | −1 | 3 |
| 🇹🇳 Túnez | 0 | 0 | 3 | 0 | 5 | −5 | 0 |

Partidos: Países Bajos 2-1 Japón | Suecia 1-0 Túnez | Países Bajos 2-1 Suecia | Túnez 0-2 Japón | Japón 2-1 Suecia | Túnez 0-2 Países Bajos

### GRUPO G
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇧🇪 **Bélgica** ✅ | 3 | 0 | 0 | 6 | 1 | +5 | **9** |
| 🇪🇬 **Egipto** ✅ | 2 | 0 | 1 | 4 | 2 | +2 | **6** |
| 🇮🇷 Irán | 1 | 0 | 2 | 1 | 3 | −2 | 3 |
| 🇳🇿 Nueva Zelanda | 0 | 0 | 3 | 0 | 5 | −5 | 0 |

Partidos: Bélgica 2-1 Egipto | Irán 1-0 Nueva Zelanda | Bélgica 2-0 Irán | Nueva Zelanda 0-2 Egipto | Egipto 1-0 Irán | Nueva Zelanda 0-2 Bélgica

### GRUPO H
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇪🇸 **España** ✅ | 3 | 0 | 0 | 7 | 1 | +6 | **9** |
| 🇺🇾 **Uruguay** ✅ | 2 | 0 | 1 | 5 | 2 | +3 | **6** |
| 🇨🇻 Cabo Verde | 1 | 0 | 2 | 1 | 5 | −4 | 3 |
| 🇸🇦 Arabia Saudita | 0 | 0 | 3 | 0 | 5 | −5 | 0 |

Partidos: España 3-0 Cabo Verde | Arabia Saudita 0-2 Uruguay | España 2-0 Arabia Saudita | Uruguay 2-0 Cabo Verde | Cabo Verde 1-0 Arabia Saudita | Uruguay 1-2 España

### GRUPO I
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇫🇷 **Francia** ✅ | 3 | 0 | 0 | 7 | 2 | +5 | **9** |
| 🇳🇴 **Noruega** ✅ | 2 | 0 | 1 | 5 | 3 | +2 | **6** |
| 🇸🇳 Senegal | 1 | 0 | 2 | 4 | 4 | 0 | 3 |
| 🇮🇶 Irak | 0 | 0 | 3 | 0 | 7 | −7 | 0 |

Partidos: Francia 2-1 Senegal | Irak 0-2 Noruega | Francia 3-0 Irak | Noruega 2-1 Senegal | Noruega 1-2 Francia | Senegal 2-0 Irak

### GRUPO J
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇦🇷 **Argentina** ✅ | 3 | 0 | 0 | 6 | 1 | +5 | **9** |
| 🇦🇹 **Austria** ✅ | 2 | 0 | 1 | 5 | 3 | +2 | **6** |
| 🇩🇿 Argelia | 1 | 0 | 2 | 2 | 4 | −2 | 3 |
| 🇯🇴 Jordania | 0 | 0 | 3 | 0 | 5 | −5 | 0 |

Partidos: Argentina 2-0 Argelia | Austria 2-0 Jordania | Argentina 2-1 Austria | Jordania 0-1 Argelia | Argelia 1-2 Austria | Jordania 0-2 Argentina

### GRUPO K
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇵🇹 **Portugal** ✅ | 3 | 0 | 0 | 7 | 1 | +6 | **9** |
| 🇨🇴 **Colombia** ✅ | 2 | 0 | 1 | 5 | 2 | +3 | **6** |
| 🇺🇿 Uzbekistán | 1 | 0 | 2 | 1 | 4 | −3 | 3 |
| 🇨🇩 R.D. del Congo | 0 | 0 | 3 | 0 | 6 | −6 | 0 |

Partidos: Portugal 3-0 R.D. del Congo | Uzbekistán 0-2 Colombia | Portugal 2-0 Uzbekistán | Colombia 2-0 R.D. del Congo | Colombia 1-2 Portugal | R.D. del Congo 0-1 Uzbekistán

### GRUPO L
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🏴󠁧󠁢󠁥󠁮󠁧󠁿 **Inglaterra** ✅ | 3 | 0 | 0 | 6 | 1 | +5 | **9** |
| 🇭🇷 **Croacia** ✅ | 2 | 0 | 1 | 3 | 2 | +1 | **6** |
| 🇵🇦 Panamá | 1 | 0 | 2 | 1 | 3 | −2 | 3 |
| 🇬🇭 Ghana | 0 | 0 | 3 | 0 | 4 | −4 | 0 |

Partidos: Inglaterra 2-1 Croacia | Ghana 0-1 Panamá | Inglaterra 2-0 Ghana | Panamá 0-1 Croacia | Panamá 0-2 Inglaterra | Croacia 1-0 Ghana

---

## 5. Los 32 clasificados a Dieciseisavos

### Clasificados directos (24 = 2 por grupo):
| Grupo | 1° | 2° |
|---|---|---|
| A | 🇲🇽 México | 🇰🇷 Corea del Sur |
| B | 🇨🇦 Canadá | 🇨🇭 Suiza |
| C | 🇧🇷 Brasil | 🇲🇦 Marruecos |
| D | 🇺🇸 Estados Unidos | 🇹🇷 Turquía |
| E | 🇩🇪 Alemania | 🇪🇨 Ecuador |
| F | 🇳🇱 Países Bajos | 🇯🇵 Japón |
| G | 🇧🇪 Bélgica | 🇪🇬 Egipto |
| H | 🇪🇸 España | 🇺🇾 Uruguay |
| I | 🇫🇷 Francia | 🇳🇴 Noruega |
| J | 🇦🇷 Argentina | 🇦🇹 Austria |
| K | 🇵🇹 Portugal | 🇨🇴 Colombia |
| L | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra | 🇭🇷 Croacia |

### Mejores 8 terceros (ranking por pts → DG → GF → ELO):
| Pos | Equipo | Grupo | Pts | DG | GF | ELO |
|---|---|---|---|---|---|---|
| 1 ✅ | 🇸🇳 Senegal | I | 3 | 0 | 4 | 1683 |
| 2 ✅ | 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Escocia | C | 3 | 0 | 4 | 1631 |
| 3 ✅ | 🇨🇮 Costa de Marfil | E | 3 | 0 | 4 | 1628 |
| 4 ✅ | 🇨🇿 Chequia | A | 3 | −1 | 4 | 1612 |
| 5 ✅ | 🇸🇪 Suecia | F | 3 | −1 | 3 | 1648 |
| 6 ✅ | 🇦🇺 Australia | D | 3 | −1 | 3 | 1628 |
| 7 ✅ | 🇧🇦 Bosnia y Herz. | B | 3 | −1 | 3 | 1558 |
| 8 ✅ | 🇩🇿 Argelia | J | 3 | −2 | 2 | 1589 |

**Eliminados (4 terceros que no clasifican):** Irán (G, DG=−2, GF=1, ELO=1558), Panamá (L, DG=−2, GF=1, ELO=1523), Uzbekistán (K, DG=−3), Cabo Verde (H, DG=−4)

---

## 6. Bracket eliminatorio (v3.2 — salida real 9 jun 2026)

### Dieciseisavos de final (R32)
Los seeds "3X" se asignan a los slots del bracket por backtracking según las restricciones de posición del Annex C FIFA 2026 (aproximación determinista, no la tabla exacta).

| Partido | Sede | Local | Marcador | Visitante | Probs L/E/V | Ganador |
|---|---|---|---|---|---|---|
| M74 \| 1E vs 3C | Boston | Alemania | 2-0 | Escocia | 59.5%/23.7%/16.9% | **Alemania** |
| M77 \| 1I vs 3F | New York | Francia | 2-0 | Suecia | 60.2%/23.0%/16.8% | **Francia** |
| M73 \| 2A vs 2B | Los Ángeles | Corea del Sur | 1-2 | Suiza | 25.9%/27.4%/46.8% | **Suiza** |
| M75 \| 1F vs 2C | Monterrey | Países Bajos | 1-0 | Marruecos | 42.5%/28.5%/29.0% | **Países Bajos** |
| M83 \| 2K vs 2L | Toronto | Colombia | 1-0 | Croacia | 42.8%/28.4%/28.8% | **Colombia** |
| M84 \| 1H vs 2J | Los Ángeles | España | 2-1 | Austria | 56.1%/23.3%/20.7% | **España** |
| M81 \| 1D vs 3B | San Francisco | Estados Unidos | 2-0 | Bosnia y Herz. | 60.5%/23.8%/15.7% | **Estados Unidos** |
| M82 \| 1G vs 3A | Seattle | Bélgica | 1-0 | Chequia | 51.8%/26.8%/21.4% | **Bélgica** |
| M76 \| 1C vs 2F | Houston | Brasil | 2-1 | Japón | 41.1%/26.8%/32.1% | **Brasil** |
| M78 \| 2E vs 2I | Dallas | Ecuador | 1-2 | Noruega | 27.2%/27.1%/45.7% | **Noruega** |
| M79 \| 1A vs 3I | Ciudad de México | México | 2-1 | Senegal | 50.3%/24.5%/25.3% | **México** |
| M80 \| 1L vs 3E | Atlanta | Inglaterra | 1-0 | Costa de Marfil | 53.8%/25.8%/20.4% | **Inglaterra** |
| M86 \| 1J vs 2H | Miami | Argentina | 2-1 | Uruguay | 54.0%/24.4%/21.6% | **Argentina** |
| M88 \| 2D vs 2G | Dallas | Turquía | 1-0 | Egipto | 45.4%/28.3%/26.3% | **Turquía** |
| M85 \| 1B vs 3J | Vancouver | Canadá | 2-1 | Argelia | 52.8%/25.8%/21.3% | **Canadá** |
| M87 \| 1K vs 3D | Kansas City | Portugal | 2-0 | Australia | 62.0%/22.5%/15.4% | **Portugal** |

### Octavos de final (R16)
| Sede | Local | Marcador | Visitante | Probs L/E/V | Ganador |
|---|---|---|---|---|---|---|
| Philadelphia | Alemania | 1-2 | Francia | 34.7%/26.4%/38.9% | **Francia** |
| Houston | Suiza | 1-2 | Países Bajos | 28.7%/27.4%/43.9% | **Países Bajos** |
| Dallas | Colombia | 1-2 | España | 21.0%/24.0%/54.9% | **España** |
| Seattle | Estados Unidos | 2-1 | Bélgica | 38.9%/28.1%/33.0% | **Estados Unidos** |
| New York | Brasil | 2-1 | Noruega | 40.9%/26.7%/32.5% | **Brasil** |
| Ciudad de México | México | 1-2 | Inglaterra | 36.7%/26.0%/37.3% | **Inglaterra** |
| Atlanta | Argentina | 2-1 | Turquía | 61.2%/22.3%/16.5% | **Argentina** |
| Vancouver | Canadá | 1-2 | Portugal | 26.1%/25.1%/48.8% | **Portugal** |

### Cuartos de final
| Sede | Local | Marcador | Visitante | Probs L/E/V | Ganador |
|---|---|---|---|---|---|---|
| Boston | Francia | 2-1 | Países Bajos | 45.7%/26.0%/28.3% | **Francia** |
| Los Ángeles | España | 2-1 | Estados Unidos | 50.4%/24.8%/24.8% | **España** |
| Miami | Brasil | 1-2 | Inglaterra | 35.4%/27.7%/36.9% | **Inglaterra** |
| Kansas City | Argentina | 2-1 | Portugal | 43.1%/26.0%/30.9% | **Argentina** |

### Semifinales
| Sede | Local | Marcador | Visitante | Probs L/E/V | Ganador |
|---|---|---|---|---|---|---|
| Dallas | Francia | 1-2 | España | 35.1%/25.4%/39.5% | **España** |
| Atlanta | Inglaterra | 1-2 | Argentina | 26.2%/25.9%/48.0% | **Argentina** |

### Final (New York)
| Local | Marcador | Visitante | Probs L/E/V | Ganador |
|---|---|---|---|---|
| España | 1-2 | **Argentina** | 35.7%/26.2%/38.1% | **🏆 Argentina** |

---

## 6b. Probabilidades Monte Carlo (20,000 sims)

| Equipo | P(Campeón) | ELO |
|---|---|---|
| 🇦🇷 Argentina | **14.5%** | 1962 |
| 🇪🇸 España | **12.8%** | 1913 |
| 🇫🇷 Francia | **9.8%** | 1891 |
| 🇵🇹 Portugal | **9.3%** | 1856 |
| 🇩🇪 Alemania | **7.5%** | 1853 |
| 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra | 5.4% | 1842 |
| 🇺🇸 Estados Unidos | 4.6% | 1752 |
| 🇧🇷 Brasil | 4.4% | 1838 |
| 🇳🇱 Países Bajos | 4.1% | 1836 |
| 🇧🇪 Bélgica | 3.0% | 1791 |
| 🇳🇴 Noruega | 2.6% | 1730 |
| 🇯🇵 Japón | 2.5% | 1733 |
| 🇲🇽 México | 2.5% | 1718 |
| 🇺🇾 Uruguay | 2.2% | 1762 |
| 🇨🇦 Canadá | 2.0% | 1703 |
| 🇨🇭 Suiza | 1.9% | 1718 |
| 🇨🇴 Colombia | 1.9% | 1738 |
| 🇲🇦 Marruecos | 1.8% | 1747 |
| 🇦🇹 Austria | 1.4% | 1720 |
| 🇸🇳 Senegal | 0.9% | 1683 |
| 🇹🇷 Turquía | 0.9% | 1680 |
| 🇪🇨 Ecuador | 0.8% | 1648 |
| 🇭🇷 Croacia | 0.7% | 1698 |
| 🇸🇪 Suecia | 0.4% | 1648 |
| 🇨🇮 Costa de Marfil | 0.4% | 1628 |
| 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Escocia | 0.3% | 1631 |
| 🇰🇷 Corea del Sur | 0.3% | 1627 |
| 🇨🇿 Chequia | 0.3% | 1612 |
| 🇦🇺 Australia | 0.3% | 1628 |

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
- **USA:** Perdió 5-2 vs Bélgica, 2-0 vs Portugal y 1-2 vs Alemania en amistosos. Factor anfitrión los lleva a R16 mínimo.
- **Curazao:** DT Advocaat (78 años) renunció, lo reemplazó Rutten, que renunció, volvió Advocaat. 0 puntos, eliminados.
- **Arabia Saudita:** DT Donis nombrado 7 semanas antes. 25/26 jugadores de liga local. Los peores del torneo.
- **Iraq:** Empató 1-1 vs España en La Coruña el 5 de junio — su mejor señal previa.
- **Algeria:** Eliminó a Países Bajos en amistoso del 3 de junio. Mahrez regresó del retiro.

---

## 8. Cómo usar el modelo en un chat nuevo

```python
# En el modelo/ folder, inicializar todo:
import sys; sys.path.insert(0, '.')
import setup_db
setup_db.setup()
# update_all_teams ya no es obligatorio — datos embebidos en setup_db.TEAMS

# Conectar a la DB (ruta canónica en modelo/data/mundial_2026.db):
import sqlite3
from predictor_v3 import DB_PATH, predict_match
conn = sqlite3.connect(DB_PATH)

# Predecir un partido:
r = predict_match('Spain', 'Uruguay', conn=conn)

# Simular un grupo completo:
from predictor_v3 import simulate_group, group_report
simulate_group('H', conn=conn, verbose=True)

# Reporte con Monte Carlo:
group_report('H', conn=conn, n_sims=50000)

# Bracket eliminatorio completo:
from simulate_knockout import main as ko_main
ko_main()
```

Para actualizar datos de un equipo:
```bash
python update_team.py "Costa de Marfil" --form 7.5 --notes "Nuevo texto"
python update_team.py --group E  # listar grupo E
```
