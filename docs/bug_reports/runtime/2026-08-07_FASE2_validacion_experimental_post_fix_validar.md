# Fase 2 — Validación experimental post-fix: Validar, confianza efectiva y deliberación real

## Metadata

- **Fecha:** 2026-08-07/08
- **Rama:** `investigacion/sesion5-rendimiento`
- **Continúa de:** Fase 1 (`docs/bug_reports/runtime/2026-08-07_FASE1_remediacion_validar_dataset_experimental.md`,
  commits `77515a5` + `9b08a94`)
- **Protocolo:** investigación causal → diseño experimental (Fases A/B/C, artefactos
  privados del tesista) → **ejecución controlada contra producción real** (este documento).
- **Alcance:** exclusivamente experimental. **Cero cambios de código, cero cambios a
  `POLITICAS`, cero migraciones.** Todo hallazgo que hubiera requerido tocar producción
  quedó documentado como limitación, no ejecutado.
- **Método:** tráfico HTTP real (`POST /api/users`, `/enroll`, `/students/cycle-evidence`)
  contra un backend FastAPI real levantado para esta fase, LLM real (`gpt-4o-mini`),
  Postgres real. Contrafactuales calculados en memoria con los reducers y funciones de
  confianza reales (`validar_decision`, `calcular_confianza_efectiva`), nunca persistidos.

---

## Pregunta experimental central

> Después del fix de `Validar` (`77515a5`), ¿un flujo real de aprendizaje produce
> evidencia de validación que modifique la confianza efectiva (`ce`) de una propuesta
> y pueda afectar una decisión posterior?

## Resultado, por experimento

### A1 — Validación positiva — **PASS**

Estudiante `exp-a1@upao.edu.pe`, competencia "Fundamentos de Python", dos llamadas reales
a `POST /api/students/cycle-evidence` (3 errores → 0 errores).

```
Validar → funciono=True, items_antes=3, items_despues=0
decisión → VALIDADA
ce (v2 real):        0.4385 → 0.4385   (idénticos, por diseño de v2)
ce (política prueba): 0.4385 → 0.5385   (+0.10, exacto)
```

Primer veredicto real de `Validar` en la historia del sistema (0 veredictos en 19,412
transiciones antes de `77515a5`, confirmado en la investigación de causa raíz previa).

### A2 — Validación negativa — **PASS**

Estudiante `exp-a2@upao.edu.pe`, competencia "Estructuras de control", dos llamadas
(3 errores → 3 errores, sin mejora).

```
Validar → funciono=False, items_antes=3, items_despues=3
decisión → VALIDADA
ce (v2 real):        0.4385 → 0.4385
ce (política prueba): 0.4385 → 0.3385   (−0.10, exacto)
```

A1+A2 aíslan las dos direcciones del mecanismo con evidencia simétrica y en la dirección
matemáticamente esperada.

### B0 — Primer intento de tensión D2 — **BLOQUEADO POR PRECONDICIÓN, correctamente explicado**

Estudiante `exp-b@upao.edu.pe`, `attempts=2, solved=true`. Sesión de 4 transiciones, sin
decisión. Causa exacta, verificada, no supuesta:

- `errores=1 < 2` → `dominada=True` (no `False` como se asumió en el diseño original).
- Solo Orientar dispara (Remediar exige `dominada=False` explícitamente).
- `ce=0.0945 < POLITICAS["v2"].theta = 0.5` (valor real, no verificado antes de este
  intento) → `derivar_decision_directa` no deriva nada.

Hallazgo derivado, verificado con `evidence_strength` real (sin llamadas HTTP): el techo
matemático de la confianza de Orientar es `0.2065` (en `attempts=1`), siempre por debajo
de `θ=0.5` — Orientar nunca puede derivar una decisión en solitario bajo `v2`.

### B2 — Tensión D2 real — **CONFIRMADO (B-1)**

Estudiante `exp-b2@upao.edu.pe`, competencia "Programación orientada a objetos",
`attempts=3, solved=true` (rediseñado tras B0, predicho analíticamente antes de
ejecutar y confirmado exacto contra producción):

```
Diagnosticar → dominada=False, errores=2
Remediar  propone (confianza=0.2077)
Orientar  propone (confianza=0.0615)
DeliberacionEntry: participantes=(Remediar, Orientar), margen=0.1462,
                    regla="mayor-confianza-declarada", aceptados=Remediar
Decisión → PENDIENTE_DE_VALIDACION (origen=Remediar)
```

Predicción teórica (Wilson, calculada antes de la ejecución) vs. observación real:
coincidencia exacta en las tres cifras (Remediar, Orientar, margen). Confirma que los
productores LLM reales de producción son fielmente modelables con `evidence_strength`.

### B-2 — Sensibilidad del margen — **CONFIRMADO**

Contrafactual analítico (reducer `validar_decision` real aplicado en memoria sobre el
estado persistido de B2, política de prueba `peso_refuerzo=0.10, delta=0.10` — igual
`delta` que v2, único cambio: los pesos):

```
Refuerzo de Remediar: ce 0.2077→0.3077, margen 0.1462→0.2462
regla: sin cambio (mayor-confianza-declarada), ganador: sin cambio (Remediar)
```

### B-3 — Cambio cualitativo de regla — **CONFIRMADO**

```
Refutación de Remediar: ce 0.2077→0.1077, margen 0.1462→0.0462
margen cruza δ=0.10 → regla: "mayor-confianza-declarada" → "provisional-por-urgencia"
ganador: sin cambio (Remediar)
```

Evidencia causal de que `ce` no solo desplaza una magnitud — puede desplazar la
**naturaleza** de la resolución (firme vs. provisional), con datos y reducers reales,
sin modificar `POLITICAS` de producción.

### Cambio de ganador (B-3b) — **No demostrado, deliberadamente no perseguido**

Construir un escenario donde Orientar gane exigía fabricar una decisión hipotética que
Orientar nunca originó en la traza real (perdió B2) y aplicarle un `Validar` que jamás
ocurrió — cruzar de "contrafactual sobre estado real" a "estado inventado". Se descartó
por decisión metodológica explícita, no por limitación técnica.

---

## Desviaciones de diseño encontradas y corregidas en el camino

1. **Producción usa los productores LLM (`_activo()`), no los de regla.** Confianzas
   dinámicas (`gpt-4o-mini`), no las constantes `0.82`/`0.75` asumidas en el diseño
   inicial de Fase C.
2. **Calibración por límite inferior de Wilson (95%)**, no confianza LLM cruda —
   `evidence_strength()`, ya usada desde la Iteración 5.5 (H10).
3. **`POLITICAS["v2"].theta = 0.5`**, no `0` — solo relevante en el camino de propuesta
   única (`derivar_decision_directa`); irrelevante para tensiones resueltas por
   `convocar()` (solo compara contra `delta`).
4. **`POLITICAS["v2"].delta = 0.10`** — confirmado con datos reales en B2/B-3.
5. **Orientar propone sin filtrar por `dominada`** (a diferencia de la versión de
   regla) — su confianza calibrada (Wilson sobre aciertos) lo descarta cuando la
   evidencia no lo sostiene, en vez de un guard rígido.
6. **Una decisión nueva sobre el mismo asunto supersede a la anterior** — descubierto
   al diseñar B, cambió el alcance de qué podía combinarse con A en una sola sesión.
7. **Error propio corregido antes de reportar:** el primer cálculo de B-3 usó una
   `Politica` de prueba con `delta=0` (heredada de Fase 1, donde era irrelevante),
   invalidando el resultado. Corregido a `delta=0.10` antes de presentar cifras.

## Integridad del dataset

| Punto de control | Resultado |
|---|---|
| `runtime.runtime_sessions` | 966 (inicio Fase 1) → 970 (cierre Fase 2), +4 sesiones, todas `CLEAN_REAL` |
| Sesiones huérfanas nuevas | 0 (verificado tras cada paso) |
| Datos históricos (902/966 sesiones previas) | Sin modificar |
| `POLITICAS["v2"]` | Sin modificar |
| Código de producción | Sin modificar desde el commit `9b08a94` |

Usuarios experimentales permanentes, `CLEAN_REAL`, no eliminados: `exp-a1@upao.edu.pe`,
`exp-a2@upao.edu.pe`, `exp-b@upao.edu.pe` (B0, bloqueado), `exp-b2@upao.edu.pe`.

## Conclusión citable

> El mecanismo de consenso implementado opera end-to-end sobre el runtime real: genera
> propuestas concurrentes a partir de evidencia, las somete a deliberación, selecciona
> una propuesta según confianza efectiva y margen, y modifica cualitativamente la regla
> de resolución cuando la evidencia contrafactual desplaza el margen a través de `δ`.

**Precisión académica que se conserva como límite explícito:** la experimentación
demuestra sensibilidad de la deliberación y de la regla de resolución a `ce`, pero no
demuestra experimentalmente un cambio de ganador entre agentes — ese resultado
requeriría, bajo el `v2` real, una secuencia de evidencia que Orientar nunca produjo en
estos experimentos, y fabricarlo artificialmente se descartó por decisión metodológica.

## Fuera de alcance de esta fase (no ejecutado, no evaluado)

Activación de una política experimental en `POLITICAS` de producción; multimodalidad;
nuevos agentes; `runtime_bridge.py` (confirmado sin necesidad de cambio en Fase 1);
limpieza de las 801 sesiones huérfanas (siguen clasificadas, no tocadas).

## Estado operativo al cierre

Backend de experimentación (`uvicorn`) apagado. Postgres (`upao_postgres`) sigue
corriendo, sin detener — mismo criterio que las fases anteriores.
