# TODO — Observaciones pendientes (post-v3.3, 10 jun 2026)

Pendientes que quedaron del levantamiento y de las correcciones del 9-10 de junio.
Lo estructural (Dixon-Coles completo, MC consistente, bracket dinámico, sedes en KO,
datos unificados, capa de decisión EV con reglamento real, overrides manuales) ya
está resuelto y verificado.

## Alta prioridad — afectan la calidad de la predicción

- [ ] **Recalibrar con datos serios y validar out-of-sample.** Los exponentes ELO
  (ATK=2.8, DEF=2.1) y las métricas del README (79% dirección, 74% top-3) salen de los
  mismos 19 amistosos usados para el grid search → son in-sample y optimistas.
  Calibrar sobre un dataset histórico de partidos internacionales (hay datasets públicos
  con miles de partidos + ELO histórico), optimizando log-loss o RPS, con conjunto de
  test separado. Re-reportar métricas honestas.
  **Avance 10 jun:** los datos ya están en la DB local (`intl_matches`, 49.472 partidos
  1872→2026, con `team_name_map` para nuestros 48 equipos; ver `load_history.py`).
  Falta: ELO histórico (computable desde el propio dataset con K estándar) y el
  pipeline de calibración. Filtrar `home_score IS NOT NULL` (fixtures futuros vienen
  vacíos).

- [x] **Adaptar la capa de decisión al esquema de puntos real de la polla.** ✅ v3.3
  (10 jun): reglamento implementado en `polla_points.py` (6/4/3/1 en grupos; 9/6/6/3
  con advancer en KO); `predict_match` y `predict_ko_match` apuestan
  `argmax E[puntos]`. Derivado nuevo a validar: en cruces KO parejos el óptimo es
  apostar empate + ganador de penales (8 de 31 cruces en el bracket actual) — esa
  apuesta depende de que P(empate 90') del modelo esté bien calibrada (ver
  recalibración arriba).

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
  Refinamiento posible con datos por selección — ya hay 678 definiciones históricas
  cargadas en `intl_shootouts` (load_history.py).

- [ ] **ELO estático durante el torneo:** el modelo no actualiza ratings con los
  resultados simulados de rondas previas. Para una polla entregada de antemano es
  aceptable; si se permite re-pronosticar ronda a ronda, agregar actualización ELO.

- [x] **Commitear v3.2:** ✅ commiteado (4b656fe, 8934192). Pendiente nuevo: commitear
  v3.3 (capa de decisión EV + overrides + dashboard + docs).
