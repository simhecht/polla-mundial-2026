# Evaluación post-torneo — Mundial 2026

_Generado por `modelo/evaluate.py`. Modelo v3.5 **pre-torneo** (sin resultados reales ni overrides) contra los 104 partidos reales. En eliminatoria se predice el cruce que realmente se jugó, con marcador a 90'. Fuente: openfootball/worldcup.json, verificada contra martj42/international_results._

## Resumen

| Fase | Partidos | 1X2 acertado | Marcador exacto | Brier | Log loss | Puntos polla | Baseline 1-0 favorito ELO |
|---|---|---|---|---|---|---|---|
| Grupos (72) | 72 | 43 (60%) | 7 (10%) | 0.503 | 0.851 | 183 (2.54/partido) | 189 (2.62/partido) |
| Eliminatoria (32) | 32 | 20 (62%) | 8 (25%) | 0.535 | 0.906 | 107 (3.34/partido) | 92 (2.88/partido) |
| Total (104) | 104 | 63 (61%) | 15 (14%) | 0.513 | 0.868 | 290 (2.79/partido) | 281 (2.70/partido) |

- Referencia sin información (1/3 cada resultado): Brier 0.667, log loss 1.099.
- Eliminatoria: el modelo acertó quién avanzaba en **24/32** cruces.
- Apuestas reales jugadas en grupos (modelo + overrides manuales, `results.json`): **188 pts** en 72 partidos, vs **183 pts** del modelo puro.

## Proyección pre-torneo

- Clasificados a dieciseisavos acertados: **26/32**.
- Campeón del escenario determinista: **Argentina**. Campeón real: **España**.
- Monte Carlo pre-torneo (20.000 simulaciones): España tenía **13.4%** (puesto 2 de 32).
- Top 5 del Monte Carlo: Argentina 14.3%, España 13.4%, Francia 9.7%, Portugal 9.2%, Alemania 7.7%.

## Eliminatoria, partido a partido

| Ronda | Partido | L / E / V (%) | Apuesta modelo | Real 90' | Avanzó | Pts |
|---|---|---|---|---|---|---|
| Dieciseisavos | Sudáfrica vs Canadá | 20 / 27 / 53 | 0-1 | 0-1 | Canadá | 6 |
| Dieciseisavos | Alemania vs Paraguay | 64 / 22 / 14 | 2-0 | 1-1 | Paraguay ✗ | 0 |
| Dieciseisavos | Países Bajos vs Marruecos | 42 / 28 / 29 | 1-1 | 1-1 | Marruecos ✗ | 6 |
| Dieciseisavos | Brasil vs Japón | 41 / 27 / 32 | 1-1 | 2-1 | Brasil | 1 |
| Dieciseisavos | Francia vs Suecia | 60 / 23 / 17 | 2-0 | 3-0 | Francia | 4 |
| Dieciseisavos | Costa de Marfil vs Noruega | 26 / 26 / 48 | 1-2 | 1-2 | Noruega | 6 |
| Dieciseisavos | México vs Ecuador | 54 / 24 / 22 | 2-1 | 2-0 | México | 4 |
| Dieciseisavos | Inglaterra vs R.D. del Congo | 74 / 18 / 8 | 2-0 | 2-1 | Inglaterra | 4 |
| Dieciseisavos | Estados Unidos vs Bosnia y Herz. | 60 / 24 / 16 | 1-0 | 2-0 | Estados Unidos | 4 |
| Dieciseisavos | Bélgica vs Senegal | 42 / 28 / 30 | 1-1 | 2-2 | Bélgica | 6 |
| Dieciseisavos | Portugal vs Croacia | 56 / 24 / 19 | 1-0 | 2-1 | Portugal | 3 |
| Dieciseisavos | España vs Austria | 56 / 23 / 21 | 2-1 | 3-0 | España | 3 |
| Dieciseisavos | Suiza vs Argelia | 49 / 27 / 24 | 1-0 | 2-0 | Suiza | 4 |
| Dieciseisavos | Argentina vs Cabo Verde | 79 / 15 / 6 | 2-0 | 1-1 | Argentina | 0 |
| Dieciseisavos | Colombia vs Ghana | 60 / 24 / 16 | 1-0 | 1-0 | Colombia | 6 |
| Dieciseisavos | Australia vs Egipto | 38 / 30 / 32 | 1-1 | 1-1 | Egipto ✗ | 6 |
| Octavos | Paraguay vs Francia | 11 / 20 / 68 | 0-2 | 0-1 | Francia | 4 |
| Octavos | Canadá vs Marruecos | 31 / 29 / 40 | 1-1 | 0-3 | Marruecos | 0 |
| Octavos | Brasil vs Noruega | 41 / 27 / 32 | 1-1 | 1-2 | Noruega ✗ | 1 |
| Octavos | México vs Inglaterra | 37 / 26 / 37 | 1-1 | 2-3 | Inglaterra | 0 |
| Octavos | Portugal vs España | 32 / 26 / 42 | 1-2 | 0-1 | España | 3 |
| Octavos | Estados Unidos vs Bélgica | 39 / 28 / 33 | 1-1 | 1-4 | Bélgica ✗ | 1 |
| Octavos | Argentina vs Egipto | 70 / 19 / 11 | 2-0 | 3-2 | Argentina | 3 |
| Octavos | Suiza vs Colombia | 35 / 28 / 38 | 1-1 | 0-0 | Suiza ✗ | 3 |
| Cuartos | Francia vs Marruecos | 51 / 26 / 23 | 2-1 | 2-0 | Francia | 4 |
| Cuartos | España vs Bélgica | 52 / 25 / 23 | 2-1 | 2-1 | España | 6 |
| Cuartos | Noruega vs Inglaterra | 30 / 27 / 43 | 1-1 | 1-1 | Inglaterra | 9 |
| Cuartos | Argentina vs Suiza | 57 / 24 / 19 | 2-1 | 1-1 | Argentina | 1 |
| Semifinal | Francia vs España | 35 / 25 / 40 | 1-1 | 0-2 | España | 0 |
| Semifinal | Inglaterra vs Argentina | 26 / 26 / 48 | 1-2 | 1-2 | Argentina | 6 |
| Tercer puesto | Francia vs Inglaterra | 42 / 27 / 31 | 1-1 | 4-6 | Inglaterra ✗ | 0 |
| Final | España vs Argentina | 36 / 26 / 38 | 1-1 | 0-0 | España ✗ | 3 |
