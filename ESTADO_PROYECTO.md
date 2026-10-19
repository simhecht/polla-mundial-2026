# Polla Mundial 2026 — Estado del Proyecto
**Última actualización:** 10 junio 2026  
**Modelo activo:** predictor_v3.py (v3.3 — apuesta por valor esperado + overrides manuales)  
**Dashboard:** dashboard_mundial2026.html (en /polla/)

---

## 1. Objetivo

Predecir el marcador exacto de cada partido del Mundial USA/Canadá/México 2026, simular las 12 llaves de grupos, determinar los 8 mejores terceros, armar el bracket completo de eliminación directa y llegar al campeón.

---

## 2. Archivos del proyecto

Todos en `modelo/`:

| Archivo | Función |
|---|---|
| `setup_db.py` | Inicializa SQLite en `modelo/data/mundial_2026.db`. Contiene 48 equipos + 72 fixtures. **Los datos cualitativos (ELO, forma, notas) ya están embebidos aquí**; no es necesario correr `update_all_teams` después. |
| `update_all_teams.py` | Re-aplica los datos cualitativos de `setup_db.TEAMS` a la DB (verificación idempotente, útil si se editó la DB manualmente). Ya no es obligatorio tras `setup_db.setup()`. |
| `predictor_v3.py` | Motor principal — Poisson + Dixon-Coles (ρ=−0.10) + ELO^2.8/2.1 + host advantage. **Usar este, no v1 ni v2.** |
| `simulate_knockout.py` | Bracket eliminatorio R32→Final. Deriva los 32 clasificados dinámicamente de `simulate_group`. |
| `polla_points.py` | Reglamento de puntos de la polla + optimizador de apuesta por valor esperado (`best_bet_group`, `best_bet_ko`). Tests: `python3 test_polla_points.py`. |
| `overrides.py` + `override.py` | Overrides manuales de resultados (persisten en `modelo/data/overrides.json`); cascadean a tabla → terceros → bracket. CLI: `set`, `set-ko --advancer`, `list`, `clear`. |
| `report_md.py` | Regenera las secciones 4-6b de ESTADO_PROYECTO.md desde el modelo (evita tablas obsoletas). |
| `app.py` | Mini-app local: sirve el dashboard con edición de overrides en vivo (✏️ por partido, barra de overrides, recálculo MC bajo demanda). `python3 app.py [--port 8765] [--n-sims 5000]`. El HTML estático de `dashboard.py` no incluye la UI de edición. |
| `load_history.py` | Carga `data/raw/*.csv` (dataset martj42/international_results) en la DB: `intl_matches` (49.472 partidos 1872→2026), `intl_shootouts` (678 penales) y `team_name_map` (48 equipos → nombre del dataset). Base para la recalibración pendiente. ⚠️ Los fixtures futuros vienen con marcador NULL: filtrar `home_score IS NOT NULL`. |
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

## 3. Metodología del modelo (v3.3 — actualizada 10 jun 2026)

### Lambda (goles esperados por equipo):
```
λ = 1.3 × (ELO_equipo / 1600)^2.8 × (1600 / ELO_rival)^2.1
      × form_factor × tactical_factor × altitude_factor × host_advantage
```

### Cambios clave v3.2 → v3.3 (10 jun 2026):
- **Regla de decisión por valor esperado:** el marcador apostado ya no es el modal condicionado al resultado dominante, sino `argmax E[puntos polla]` sobre la grilla 0..6 (`polla_points.best_bet_group/best_bet_ko`), con el reglamento real de la polla: 6 pts exacto / 4 pts ganador + goles de un equipo / 3 pts ganador o empate no exacto / 1 pt goles de un equipo con ganador incorrecto.
- **KO con apuesta de avance:** la apuesta KO es marcador en 90' + quién avanza (9 pts empate exacto + advancer correcto; 6 pts empate exacto sin advancer o empate no exacto + advancer; 3 pts empate no exacto sin advancer). El techo de 9 pts hace que en cruces parejos convenga apostar empate + ganador de penales: el bracket v3.3 apuesta `1-1 (pen)` en 8 de 31 cruces. P(avanza | empate 90') = P(gana prórroga) + 0.5·P(empate en prórroga).
- **Overrides manuales** (`override.py`): fijan la apuesta de cualquier partido y cascadean automáticamente a la tabla del grupo, el ranking de terceros y el bracket (vía `build_r32`). No alteran el Monte Carlo: las probabilidades siguen siendo del modelo.
- Eliminados `best_score_result_first` y `RESULT_MARGIN_PP` (obsoletos con la regla EV).
- `predict_match` y `predict_ko_match` exponen `exp_pts` y `manual`; KO además `advancer` y `p_adv_home_draw`.

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

### Decisión de diseño: el ELO NO se actualiza con resultados reales (congelado)

El `elo_rating` es un **valor fijo de entrada**, no evoluciona partido a partido. Solo se
escribe manualmente (`setup_db.py` siembra, `update_all_teams.py` / `update_team.py` editan).
Ingresar un resultado real (`results.py`) **no toca el ELO**: solo fija el marcador en el
escenario determinista, condiciona el Monte Carlo (los jugados se fijan, se re-simula lo que
falta) y congela la apuesta para los puntos de la polla.

**Por qué se deja congelado (decisión, no bug):**
- Un torneo es corto (máx. 7 partidos). Un ELO bien calibrado pre-torneo predice mejor que
  uno que reacciona con ruido a 1-2 resultados.
- El ELO está diseñado para no sobrerreaccionar. Ejemplo real — empate España (1913) vs Cabo
  Verde (1489): con K=40, `ΔR = 40·(0.5 − 0.92) ≈ −17 pts` → España 1913→1896 (−0.9%). En el
  λ eso es `(1913/1600)² → (1896/1600)²` ≈ **−1.8%** en el factor de ataque. Casi nada.
- El riesgo de actualizar en automático es el lado feo: castigar a un equipo por un empate de
  rotación / partido basura justo antes de una ronda decisiva, sin muestra para promediar el ruido.
- El efecto del resultado sobre *quién clasifica* (pts, DG, GF, posiciones) ya se captura vía
  el escenario determinista + Monte Carlo. Lo único que no se mueve es el estimador de fuerza.

**Cuándo SÍ ajustar:** solo cuando un resultado revele información *real* (lesión de figura,
colapso táctico, equipo sobrevalorado en la carga inicial), y hacerlo **a mano con criterio**:
`python update_team.py "Spain" --elo 1890 --form <nuevo>`. La fórmula ciega no distingue
"empate por rotación" de "empate porque está mal de verdad"; el juicio humano sí.

---

## 4. Resultados fase de grupos (escenario determinista — apuesta EV)

_(Secciones 4-6b autogeneradas por `modelo/report_md.py` — 29 June 2026. EV = puntos esperados de la apuesta según el reglamento de la polla; ✏️ = resultado fijado manualmente vía `override.py`.)_

### GRUPO A
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇲🇽 **México** ✅ | 3 | 0 | 0 | 6 | 0 | +6 | **9** |
| 🇿🇦 **Sudáfrica** ✅ | 1 | 1 | 1 | 2 | 3 | -1 | **4** |
| 🇰🇷 Corea del Sur | 1 | 0 | 2 | 2 | 3 | -1 | 3 |
| 🇨🇿 Chequia | 0 | 1 | 2 | 2 | 6 | -4 | 1 |

Partidos: México 2-0 Sudáfrica (EV 2.86) | Corea del Sur 2-1 Chequia (EV 1.84) | Chequia 1-1 Sudáfrica (EV 1.63) | México 1-0 Corea del Sur (EV 2.41) | Chequia 0-3 México (EV 2.39) | Sudáfrica 1-0 Corea del Sur (EV 1.39)

### GRUPO B
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇨🇭 **Suiza** ✅ | 2 | 1 | 0 | 7 | 3 | +4 | **7** |
| 🇨🇦 **Canadá** ✅ | 1 | 1 | 1 | 8 | 3 | +5 | **4** |
| 🇧🇦 Bosnia y Herz. | 1 | 1 | 1 | 5 | 6 | -1 | 4 |
| 🇶🇦 Catar | 0 | 1 | 2 | 2 | 10 | -8 | 1 |

Partidos: Canadá 1-1 Bosnia y Herz. (EV 1.45) | Catar 1-1 Suiza (EV 1.3) | Suiza 4-1 Bosnia y Herz. (EV 2.15) | Canadá 6-0 Catar (EV 2.64) | Suiza 2-1 Canadá (EV 1.71) | Bosnia y Herz. 3-1 Catar (EV 2.02)

### GRUPO C
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇧🇷 **Brasil** ✅ | 2 | 1 | 0 | 7 | 1 | +6 | **7** |
| 🇲🇦 **Marruecos** ✅ | 2 | 1 | 0 | 6 | 3 | +3 | **7** |
| 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Escocia | 1 | 0 | 2 | 1 | 4 | -3 | 3 |
| 🇭🇹 Haití | 0 | 0 | 3 | 2 | 8 | -6 | 0 |

Partidos: Brasil 1-1 Marruecos (EV 1.62) | Haití 0-1 Escocia (EV 2.82) | Escocia 0-1 Marruecos (EV 2.19) | Brasil 3-0 Haití (EV 3.32) | Escocia 0-3 Brasil (EV 2.25) | Marruecos 4-2 Haití (EV 2.52)

### GRUPO D
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇺🇸 **Estados Unidos** ✅ | 2 | 0 | 1 | 8 | 4 | +4 | **6** |
| 🇦🇺 **Australia** ✅ | 1 | 1 | 1 | 2 | 2 | 0 | **4** |
| 🇵🇾 Paraguay | 1 | 1 | 1 | 2 | 4 | -2 | 4 |
| 🇹🇷 Turquía | 1 | 0 | 2 | 3 | 5 | -2 | 3 |

Partidos: Estados Unidos 4-1 Paraguay (EV 2.28) | Australia 2-0 Turquía (EV 1.37) | Turquía 0-1 Paraguay (EV 1.35) | Estados Unidos 2-0 Australia (EV 2.36) | Turquía 3-2 Estados Unidos (EV 1.17) | Paraguay 0-0 Australia (EV 1.48)

### GRUPO E
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇩🇪 **Alemania** ✅ | 2 | 0 | 1 | 10 | 4 | +6 | **6** |
| 🇨🇮 **Costa de Marfil** ✅ | 2 | 0 | 1 | 4 | 2 | +2 | **6** |
| 🇪🇨 Ecuador | 1 | 1 | 1 | 2 | 2 | 0 | 4 |
| 🇨🇼 Curazao | 0 | 1 | 2 | 1 | 9 | -8 | 1 |

Partidos: Alemania 7-1 Curazao (EV 2.92) | Costa de Marfil 1-0 Ecuador (EV 1.61) | Alemania 2-1 Costa de Marfil (EV 2.55) | Ecuador 0-0 Curazao (EV 1.29) | Ecuador 2-1 Alemania (EV 1.15) | Curazao 0-2 Costa de Marfil (EV 2.95)

### GRUPO F
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇳🇱 **Países Bajos** ✅ | 2 | 1 | 0 | 10 | 4 | +6 | **7** |
| 🇯🇵 **Japón** ✅ | 1 | 2 | 0 | 7 | 3 | +4 | **5** |
| 🇸🇪 Suecia | 1 | 1 | 1 | 7 | 7 | 0 | 4 |
| 🇹🇳 Túnez | 0 | 0 | 3 | 2 | 12 | -10 | 0 |

Partidos: Países Bajos 2-2 Japón (EV 1.34) | Suecia 5-1 Túnez (EV 1.94) | Países Bajos 5-1 Suecia (EV 1.98) | Túnez 0-4 Japón (EV 2.41) | Japón 1-1 Suecia (EV 1.49) | Túnez 1-3 Países Bajos (EV 2.61)

### GRUPO G
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇧🇪 **Bélgica** ✅ | 1 | 2 | 0 | 6 | 2 | +4 | **5** |
| 🇪🇬 **Egipto** ✅ | 1 | 2 | 0 | 5 | 3 | +2 | **5** |
| 🇮🇷 Irán | 0 | 3 | 0 | 3 | 3 | 0 | 3 |
| 🇳🇿 Nueva Zelanda | 0 | 1 | 2 | 4 | 10 | -6 | 1 |

Partidos: Bélgica 1-1 Egipto (EV 1.5) | Irán 2-2 Nueva Zelanda (EV 1.26) | Bélgica 0-0 Irán (EV 1.33) | Nueva Zelanda 1-3 Egipto (EV 2.42) | Egipto 1-1 Irán (EV 1.72) | Nueva Zelanda 1-5 Bélgica (EV 2.79)

### GRUPO H
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇪🇸 **España** ✅ | 2 | 1 | 0 | 5 | 0 | +5 | **7** |
| 🇨🇻 **Cabo Verde** ✅ | 0 | 3 | 0 | 2 | 2 | 0 | **3** |
| 🇺🇾 Uruguay | 0 | 2 | 1 | 3 | 4 | -1 | 2 |
| 🇸🇦 Arabia Saudita | 0 | 2 | 1 | 1 | 5 | -4 | 2 |

Partidos: España 0-0 Cabo Verde (EV 0.91) | Arabia Saudita 1-1 Uruguay (EV 1.39) | España 4-0 Arabia Saudita (EV 3.2) | Uruguay 2-2 Cabo Verde (EV 1.1) | Cabo Verde 0-0 Arabia Saudita (EV 1.65) | Uruguay 0-1 España (EV 2.22)

### GRUPO I
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇫🇷 **Francia** ✅ | 3 | 0 | 0 | 10 | 2 | +8 | **9** |
| 🇳🇴 **Noruega** ✅ | 2 | 0 | 1 | 8 | 7 | +1 | **6** |
| 🇸🇳 Senegal | 1 | 0 | 2 | 8 | 6 | +2 | 3 |
| 🇮🇶 Irak | 0 | 0 | 3 | 1 | 12 | -11 | 0 |

Partidos: Francia 3-1 Senegal (EV 2.35) | Irak 1-4 Noruega (EV 2.8) | Francia 3-0 Irak (EV 3.44) | Noruega 3-2 Senegal (EV 1.74) | Noruega 1-4 Francia (EV 2.02) | Senegal 5-0 Irak (EV 2.61)

### GRUPO J
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇦🇷 **Argentina** ✅ | 3 | 0 | 0 | 8 | 2 | +6 | **9** |
| 🇦🇹 **Austria** ✅ | 1 | 1 | 1 | 6 | 6 | 0 | **4** |
| 🇩🇿 Argelia | 1 | 1 | 1 | 6 | 7 | -1 | 4 |
| 🇯🇴 Jordania | 0 | 0 | 3 | 3 | 8 | -5 | 0 |

Partidos: Argentina 3-1 Argelia (EV 2.82) | Austria 3-1 Jordania (EV 2.63) | Argentina 2-0 Austria (EV 2.39) | Jordania 1-2 Argelia (EV 2.31) | Argelia 3-3 Austria (EV 1.01) | Jordania 1-3 Argentina (EV 3.15)

### GRUPO K
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🇨🇴 **Colombia** ✅ | 2 | 1 | 0 | 4 | 1 | +3 | **7** |
| 🇵🇹 **Portugal** ✅ | 1 | 2 | 0 | 6 | 1 | +5 | **5** |
| 🇨🇩 R.D. del Congo | 1 | 1 | 1 | 4 | 3 | +1 | 4 |
| 🇺🇿 Uzbekistán | 0 | 0 | 3 | 2 | 11 | -9 | 0 |

Partidos: Portugal 1-1 R.D. del Congo (EV 0.95) | Uzbekistán 1-3 Colombia (EV 2.55) | Portugal 5-0 Uzbekistán (EV 2.88) | Colombia 1-0 R.D. del Congo (EV 2.8) | Colombia 0-0 Portugal (EV 1.16) | R.D. del Congo 3-1 Uzbekistán (EV 1.38)

### GRUPO L
| Equipo | G | E | P | GF | GC | DG | PTS |
|---|---|---|---|---|---|---|---|
| 🏴󠁧󠁢󠁥󠁮󠁧󠁿 **Inglaterra** ✅ | 2 | 1 | 0 | 6 | 2 | +4 | **7** |
| 🇭🇷 **Croacia** ✅ | 2 | 0 | 1 | 5 | 5 | 0 | **6** |
| 🇬🇭 Ghana | 1 | 1 | 1 | 2 | 2 | 0 | 4 |
| 🇵🇦 Panamá | 0 | 0 | 3 | 0 | 4 | -4 | 0 |

Partidos: Inglaterra 4-2 Croacia (EV 1.87) | Ghana 1-0 Panamá (EV 1.72) | Inglaterra 0-0 Ghana (EV 1.19) | Panamá 0-1 Croacia (EV 2.35) | Panamá 0-2 Inglaterra (EV 2.78) | Croacia 2-1 Ghana (EV 2.32)

---

## 5. Los 32 clasificados a Dieciseisavos

### Clasificados directos (24 = 2 por grupo):
| Grupo | 1° | 2° |
|---|---|---|
| A | 🇲🇽 México | 🇿🇦 Sudáfrica |
| B | 🇨🇭 Suiza | 🇨🇦 Canadá |
| C | 🇧🇷 Brasil | 🇲🇦 Marruecos |
| D | 🇺🇸 Estados Unidos | 🇦🇺 Australia |
| E | 🇩🇪 Alemania | 🇨🇮 Costa de Marfil |
| F | 🇳🇱 Países Bajos | 🇯🇵 Japón |
| G | 🇧🇪 Bélgica | 🇪🇬 Egipto |
| H | 🇪🇸 España | 🇨🇻 Cabo Verde |
| I | 🇫🇷 Francia | 🇳🇴 Noruega |
| J | 🇦🇷 Argentina | 🇦🇹 Austria |
| K | 🇨🇴 Colombia | 🇵🇹 Portugal |
| L | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra | 🇭🇷 Croacia |

### Mejores 8 terceros (ranking por pts → DG → GF → ELO):
| Pos | Equipo | Grupo | Pts | DG | GF | ELO |
|---|---|---|---|---|---|---|
| 1 ✅ | 🇨🇩 R.D. del Congo | K | 4 | +1 | 4 | 1432 |
| 2 ✅ | 🇸🇪 Suecia | F | 4 | 0 | 7 | 1648 |
| 3 ✅ | 🇪🇨 Ecuador | E | 4 | 0 | 2 | 1648 |
| 4 ✅ | 🇬🇭 Ghana | L | 4 | 0 | 2 | 1527 |
| 5 ✅ | 🇩🇿 Argelia | J | 4 | -1 | 6 | 1589 |
| 6 ✅ | 🇧🇦 Bosnia y Herz. | B | 4 | -1 | 5 | 1558 |
| 7 ✅ | 🇵🇾 Paraguay | D | 4 | -2 | 2 | 1569 |
| 8 ✅ | 🇸🇳 Senegal | I | 3 | +2 | 8 | 1683 |

**Eliminados (4 terceros que no clasifican):** Irán (G, DG=+0, GF=3, ELO=1558), Corea del Sur (A, DG=-1, GF=2, ELO=1627), Escocia (C, DG=-3, GF=1, ELO=1631), Uruguay (H, DG=-1, GF=3, ELO=1762)

---

## 6. Bracket eliminatorio (escenario determinista — apuesta EV)

### Dieciseisavos de final (R32)
| Partido | Sede | Local | Marcador | Visitante | Probs L/E/V | EV | Avanza |
|---|---|---|---|---|---|---|---|
| M74 | 1E vs 3D | Boston | 🇩🇪 Alemania | 2-0 | 🇵🇾 Paraguay | 64.1%/22.3%/13.6% | 2.75 | **Alemania** |
| M77 | 1I vs 3F | New York | 🇫🇷 Francia | 2-0 | 🇸🇪 Suecia | 60.2%/23.0%/16.8% | 2.55 | **Francia** |
| M73 | 2A vs 2B | Los Angeles | 🇿🇦 Sudáfrica | 0-1 | 🇨🇦 Canadá | 19.8%/27.0%/53.2% | None | **Canadá** |
| M75 | 1F vs 2C | Monterrey | 🇳🇱 Países Bajos | 1-1 (pen: Países Bajos) | 🇲🇦 Marruecos | 42.5%/28.5%/29.0% | 2.15 | **Países Bajos** |
| M83 | 2K vs 2L | Toronto | 🇵🇹 Portugal | 1-0 | 🇭🇷 Croacia | 56.4%/24.5%/19.0% | 2.44 | **Portugal** |
| M84 | 1H vs 2J | Los Angeles | 🇪🇸 España | 2-1 | 🇦🇹 Austria | 56.1%/23.3%/20.7% | 2.42 | **España** |
| M81 | 1D vs 3B | San Francisco | 🇺🇸 Estados Unidos | 1-0 | 🇧🇦 Bosnia y Herz. | 60.5%/23.8%/15.7% | 2.62 | **Estados Unidos** |
| M82 | 1G vs 3I | Seattle | 🇧🇪 Bélgica | 1-1 (pen: Bélgica) | 🇸🇳 Senegal | 42.4%/27.7%/30.0% | 2.09 | **Bélgica** |
| M76 | 1C vs 2F | Houston | 🇧🇷 Brasil | 1-1 (pen: Brasil) | 🇯🇵 Japón | 41.1%/26.8%/32.1% | 2.03 | **Brasil** |
| M78 | 2E vs 2I | Dallas | 🇨🇮 Costa de Marfil | 1-2 | 🇳🇴 Noruega | 25.8%/26.5%/47.7% | 2.15 | **Noruega** |
| M79 | 1A vs 3E | Ciudad de Mexico | 🇲🇽 México | 2-1 | 🇪🇨 Ecuador | 53.8%/24.2%/22.0% | 2.35 | **México** |
| M80 | 1L vs 3K | Atlanta | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra | 2-0 | 🇨🇩 R.D. del Congo | 74.2%/17.8%/8.0% | 3.15 | **Inglaterra** |
| M86 | 1J vs 2H | Miami | 🇦🇷 Argentina | 2-0 | 🇨🇻 Cabo Verde | 78.7%/14.7%/6.5% | 3.24 | **Argentina** |
| M88 | 2D vs 2G | Dallas | 🇦🇺 Australia | 1-1 (pen: Australia) | 🇪🇬 Egipto | 38.3%/29.6%/32.1% | 2.2 | **Australia** |
| M85 | 1B vs 3J | Vancouver | 🇨🇭 Suiza | 1-0 | 🇩🇿 Argelia | 49.3%/26.7%/24.1% | 2.22 | **Suiza** |
| M87 | 1K vs 3L | Kansas City | 🇨🇴 Colombia | 1-0 | 🇬🇭 Ghana | 59.9%/24.2%/15.9% | 2.62 | **Colombia** |

### Octavos de final (R16)
| Sede | Local | Marcador | Visitante | Probs L/E/V | EV | Avanza |
|---|---|---|---|---|---|---|
| Philadelphia | 🇩🇪 Alemania | 1-1 (pen: Francia) | 🇫🇷 Francia | 34.7%/26.4%/38.9% | 1.99 | **Francia** |
| Houston | 🇨🇦 Canadá | 1-2 | 🇳🇱 Países Bajos | 26.9%/26.9%/46.2% | 2.1 | **Países Bajos** |
| Dallas | 🇵🇹 Portugal | 1-2 | 🇪🇸 España | 32.2%/25.6%/42.2% | 1.96 | **España** |
| Seattle | 🇺🇸 Estados Unidos | 1-1 (pen: Estados Unidos) | 🇧🇪 Bélgica | 38.9%/28.1%/33.0% | 2.11 | **Estados Unidos** |
| New York | 🇧🇷 Brasil | 1-1 (pen: Brasil) | 🇳🇴 Noruega | 40.9%/26.7%/32.5% | 2.02 | **Brasil** |
| Ciudad de Mexico | 🇲🇽 México | 1-1 (pen: Inglaterra) | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra | 36.7%/26.0%/37.3% | 1.94 | **Inglaterra** |
| Atlanta | 🇦🇷 Argentina | 2-0 | 🇦🇺 Australia | 67.4%/20.6%/12.1% | 2.84 | **Argentina** |
| Vancouver | 🇨🇭 Suiza | 1-1 (pen: Colombia) | 🇨🇴 Colombia | 34.7%/27.7%/37.6% | 2.08 | **Colombia** |

### Cuartos de final
| Sede | Local | Marcador | Visitante | Probs L/E/V | EV | Avanza |
|---|---|---|---|---|---|---|
| Boston | 🇫🇷 Francia | 2-1 | 🇳🇱 Países Bajos | 45.7%/26.0%/28.3% | 2.08 | **Francia** |
| Los Angeles | 🇪🇸 España | 2-1 | 🇺🇸 Estados Unidos | 50.4%/24.8%/24.8% | 2.24 | **España** |
| Miami | 🇧🇷 Brasil | 1-1 (pen: Inglaterra) | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra | 35.4%/27.7%/36.9% | 2.07 | **Inglaterra** |
| Kansas City | 🇦🇷 Argentina | 2-1 | 🇨🇴 Colombia | 55.6%/24.3%/20.1% | 2.41 | **Argentina** |

### Semifinales
| Sede | Local | Marcador | Visitante | Probs L/E/V | EV | Avanza |
|---|---|---|---|---|---|---|
| Dallas | 🇫🇷 Francia | 1-1 (pen: España) | 🇪🇸 España | 35.1%/25.4%/39.5% | 1.91 | **España** |
| Atlanta | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra | 1-2 | 🇦🇷 Argentina | 26.2%/25.9%/48.0% | 2.16 | **Argentina** |

### Final
| Sede | Local | Marcador | Visitante | Probs L/E/V | EV | Avanza |
|---|---|---|---|---|---|---|
| New York | 🇪🇸 España | 1-1 (pen: Argentina) | 🇦🇷 Argentina | 35.7%/26.2%/38.1% | 1.97 | **Argentina** |

**🏆 Campeón predicho: Argentina**

---

## 6b. Probabilidades Monte Carlo (20.000 sims)

| Equipo | P(Campeón) | ELO |
|---|---|---|
| 🇦🇷 Argentina | 21.4% | 1962 |
| 🇪🇸 España | 11.1% | 1913 |
| 🇫🇷 Francia | 9.6% | 1891 |
| 🇩🇪 Alemania | 7.6% | 1853 |
| 🇵🇹 Portugal | 6.9% | 1856 |
| 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra | 6.5% | 1842 |
| 🇺🇸 Estados Unidos | 4.2% | 1752 |
| 🇧🇷 Brasil | 4.1% | 1838 |
| 🇳🇱 Países Bajos | 3.7% | 1836 |
| 🇨🇴 Colombia | 3.2% | 1738 |
| 🇲🇽 México | 2.7% | 1718 |
| 🇳🇴 Noruega | 2.6% | 1730 |
| 🇯🇵 Japón | 2.5% | 1733 |
| 🇧🇪 Bélgica | 2.4% | 1791 |
| 🇨🇭 Suiza | 2.4% | 1718 |
| 🇨🇦 Canadá | 2.2% | 1703 |
| 🇲🇦 Marruecos | 1.7% | 1747 |
| 🇦🇹 Austria | 1.1% | 1720 |
| 🇸🇳 Senegal | 1.0% | 1683 |
| 🇭🇷 Croacia | 0.5% | 1698 |
| 🇨🇮 Costa de Marfil | 0.5% | 1628 |
| 🇪🇨 Ecuador | 0.5% | 1648 |
| 🇦🇺 Australia | 0.5% | 1628 |
| 🇸🇪 Suecia | 0.4% | 1648 |
| 🇩🇿 Argelia | 0.3% | 1589 |

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

Para fijar un resultado a mano (cascadea a tabla → terceros → bracket; acepta `name` o `name_es`):
```bash
python3 override.py set "South Korea" Czechia 0-2          # fase de grupos
python3 override.py set-ko Spain Argentina 2-2 --advancer Spain
python3 override.py list
python3 override.py clear --all                            # o clear HOME AWAY
```

Tras cualquier cambio (override, forma, ELO), regenerar salidas:
```bash
python3 dashboard.py     # dashboard HTML
python3 report_md.py     # secciones 4-6b de este documento
```

Modo app (edición de overrides desde el navegador, recomendado):
```bash
python3 app.py           # sirve el dashboard en http://localhost:8765 con botones ✏️
```

La DB no está en git (regenerable). Reconstrucción desde cero:
`setup_db.setup()` → `python3 load_history.py` (los CSV crudos sí están en `data/raw/`).
