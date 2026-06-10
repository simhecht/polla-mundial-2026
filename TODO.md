# TODO — Observaciones pendientes (post-corrección v3.2, 10 jun 2026)

Pendientes que quedaron del levantamiento y de las correcciones del 9-10 de junio.
Lo estructural (Dixon-Coles completo, MC consistente, bracket dinámico, sedes en KO,
datos unificados, capa de decisión) ya está resuelto y verificado.

## Alta prioridad — afectan la calidad de la predicción

- [ ] **Recalibrar con datos serios y validar out-of-sample.** Los exponentes ELO
  (ATK=2.8, DEF=2.1) y las métricas del README (79% dirección, 74% top-3) salen de los
  mismos 19 amistosos usados para el grid search → son in-sample y optimistas.
  Calibrar sobre un dataset histórico de partidos internacionales (hay datasets públicos
  con miles de partidos + ELO histórico), optimizando log-loss o RPS, con conjunto de
  test separado. Re-reportar métricas honestas.

- [ ] **Adaptar la capa de decisión al esquema de puntos real de la polla.** Hoy el
  marcador apostado es "el más probable condicionado al resultado más probable"
  (default defendible). Si la polla pondera distinto (ej. X pts marcador exacto,
  Y pts resultado), el marcador óptimo es `argmax(X·P(marcador) + Y·P(resultado))`.
  Falta conocer el reglamento de la polla para implementarlo.

- [ ] **Propagar la incertidumbre de grupos al bracket.** Las probabilidades de campeón
  (Argentina 14.5%) condicionan sobre UN solo bracket (el del escenario determinista).
  Simular el torneo completo (grupos + terceros + Annex C + bracket) en cada iteración
  Monte Carlo daría probabilidades de campeón no condicionadas.

- [ ] **Revisar doble conteo de factores.** Los ELO de partida ya incluyen "ajuste por
  forma reciente" (comentario en setup_db) y encima se multiplica form_factor (±25%).
  Además el host advantage (+20%/+13%/+10%) se suma a ELOs que ya absorben resultados
  como local. Decidir dónde vive cada efecto y eliminar la superposición.

## Media prioridad — fidelidad a las reglas FIFA

- [ ] **Annex C exacto.** La asignación de terceros a slots del R32 usa backtracking
  determinista que respeta las restricciones de grupos permitidos por slot, pero no
  replica la tabla oficial FIFA de combinaciones. Si FIFA publica la tabla completa
  utilizable, reemplazar la aproximación (documentada en simulate_knockout.py).

- [ ] **Tiebreakers FIFA completos.** El ranking de grupos (determinista y MC) usa
  pts → DG → GF y desempata por ELO; FIFA usa head-to-head entre empatados, fair play
  y sorteo antes que cualquier proxy. Relevante: en el escenario determinista los 12
  terceros quedan con 3 pts, así que el corte de los 8 mejores depende fuerte del
  criterio de desempate.

- [ ] **Partido por el 3er puesto (M103, Miami) no se modela.** Agregar si la polla
  lo puntúa.

## Baja prioridad — limpieza y refinamientos

- [ ] **Esquema muerto en la DB:** tablas `key_players`, `squad_depth`, `predictions`
  y campos xG nunca se usan. `squad_depth_score` se sigue manteniendo para 48 equipos
  pero el modelo lo eliminó en v3. Usar o borrar.

- [ ] **Matriz táctica sin calibrar:** los valores de TACTICAL_EDGE son juicio experto
  escalado a ±6% (dentro del ruido). Calibrarla con datos o eliminarla.

- [ ] **Asimetría de exponentes (2.8/2.1):** predice partidos élite-vs-élite MÁS
  goleadores (λ=1.47 c/u a ELO 1900 vs 1.18 a ELO 1400); empíricamente en mundiales
  los cruces entre élites tienden a ser más cerrados. Revisar al recalibrar.

- [ ] **Penales:** conversión fija 76% para todos; no distingue arqueros ni pateadores.
  Refinamiento posible con datos por selección.

- [ ] **ELO estático durante el torneo:** el modelo no actualiza ratings con los
  resultados simulados de rondas previas. Para una polla entregada de antemano es
  aceptable; si se permite re-pronosticar ronda a ronda, agregar actualización ELO.

- [ ] **Commitear v3.2:** los 14 archivos corregidos están en el working tree sin
  commitear, pendiente de revisión del dashboard.
