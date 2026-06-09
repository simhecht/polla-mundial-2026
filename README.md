# Polla Mundial 2026

Modelo de predicción de marcadores exactos para la Copa Mundial FIFA 2026 (USA/Canadá/México). Usa distribución de Poisson bivariada con corrección Dixon-Coles, ratings ELO, forma reciente, estilo táctico, altitud y ventaja de local anfitrión.

## Metodología

```
λ = 1.3 × (ELO_equipo / 1600)^2.8 × (1600 / ELO_rival)^2.1
      × form_factor × tactical_factor × altitude_factor × host_advantage
```

- **Dixon-Coles** ρ = −0.10: corrige la correlación 0-0 / 1-0 / 0-1 / 1-1 que Poisson independiente sobreestima
- **Form factor**: ±25% cap — `1.0 + (score−5)/5 × 0.25`
- **Host advantage**: México +20%, USA +13%, Canadá +10% (sobre 16 sedes)
- **Altitud**: ×1.12 (≥1800m) / ×1.06 (≥1000m) / ×1.02 (≥500m)
- **Exponentes ELO**: calibrados por grid search sobre 19 amistosos pre-Mundial + 12 cuotas de mercado

## Rendimiento (v3.1 — validado 9 jun 2026)

| Métrica | Resultado |
|---|---|
| Dirección correcta (ganó quien el modelo favorecía) | **15/19 = 79%** |
| Marcador real en top-3 predichos | **14/19 = 74%** |
| Marcador exacto predicho como #1 | **8/19 = 42%** |
| Desviación media vs cuotas de mercado (12 partidos) | **5.1 pp** |

## Estructura

```
polla/
├── modelo/
│   ├── predictor_v3.py      # Motor principal (usar este)
│   ├── setup_db.py          # Inicializa SQLite con 48 equipos + 72 fixtures
│   ├── update_all_teams.py  # Aplica ELO, forma y notas a los 48 equipos
│   ├── update_team.py       # CLI para actualizar un equipo individual
│   └── dashboard.py         # Genera el dashboard HTML
├── dashboard_mundial2026.html
└── ESTADO_PROYECTO.md       # Estado detallado, grupos simulados, pendientes
```

## Uso rápido

```python
import sys, sqlite3
sys.path.insert(0, 'modelo/')
import setup_db, update_all_teams
from predictor_v3 import predict_match, simulate_group, group_report

# Inicializar (obligatorio al inicio de cada sesión — DB en /tmp/)
setup_db.DB_PATH = '/tmp/mundial_2026.db'
setup_db.setup()
update_all_teams.run()

conn = sqlite3.connect('/tmp/mundial_2026.db')

# Partido individual
predict_match('Spain', 'Uruguay', conn=conn)

# Grupo completo (determinista)
simulate_group('H', conn=conn, verbose=True)

# Grupo con Monte Carlo (50k simulaciones)
group_report('H', conn=conn, n_sims=50_000)
```

```bash
# Actualizar datos de un equipo
python modelo/update_team.py "Costa de Marfil" --form 7.5 --notes "Nuevo texto"
python modelo/update_team.py --group E   # listar grupo E
```

## Notas de calibración

Los exponentes ELO (ATK=2.8, DEF=2.1) se calibraron el 9 de junio de 2026 mediante grid search comparando las predicciones contra 19 amistosos pre-Mundial y las probabilidades implícitas de 12 cuotas de mercado (FanDuel/Pinnacle). Versiones anteriores usaban 2.0/1.5 (v3) y 0.6/0.4 (v2).

Divergencias conocidas del modelo respecto al mercado:
- Brasil vs Marruecos: modelo ~14pp más conservador con Brasil
- Países Bajos vs Japón: modelo ~11pp más conservador con Países Bajos
