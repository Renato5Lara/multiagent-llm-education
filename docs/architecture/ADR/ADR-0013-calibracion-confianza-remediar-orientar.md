# ADR-0013 — Calibración de confianza declarada para Remediar y Orientar

- **Estado:** Aceptado (2026-08-04)
- **Fecha:** 2026-08-04
- **Preserva:** `runtime/kernel/deliberation/mecanica.py` (mecánica de consenso
  D1/D2/D3, sin cambios), `runtime/kernel/deliberation/confianza.py` (axiomas
  A1-A8, sin cambios), `runtime/kernel/deliberation/politica.py`
  (`POLITICAS["v1"]`/`POLITICAS["v2"]`, sin cambios), P3 (independencia de
  productores, sin cambios), `runtime/domain/diagnosticar/calibracion.py`
  (`calibrar_confianza_nueva`, sin cambios de comportamiento).
- **Criterio de aceptación:** ver §6.

## 1. Contexto

Una cadena de cinco auditorías (2026-08-04, misma sesión) sobre el motor de
consenso encontró una asimetría concreta entre las tres capacidades que
participan en la deliberación de `"siguiente-paso(sesion)"`:

| Capacidad | Confianza declarada | ¿Refleja evidencia real? |
|---|---|---|
| Diagnosticar | Calibrada desde H10 (Iteración 5.8): `evidence_strength` + `calibrar_confianza_nueva` | Sí — medido: 0.30 / 0.15 / 0.51 según severidad del caso |
| Remediar | Cruda del LLM, sin calibrar | Parcial — señal (0.0166 entre perfiles) menor que ruido de muestreo (0.0289 intra-perfil) |
| Orientar | Cruda del LLM, sin calibrar | No — constante en 0.85 en 9/9 corridas, incluida la transición `dominada: True → False` |

Evidencia de ejecución real (no simulada), contra los productores LLM reales
(`OpenAIProvider`, `temperature=0`), tres perfiles de estudiante genuinamente
distintos (fallo leve 1/4, dominio marginal 2/4 en el umbral exacto, fallo
severo 4/4):
`backend/scripts/experimentos/consenso_remediar_orientar_llm_por_perfil.py`,
salida `backend/experiments/results/consenso_remediar_orientar_llm_por_perfil_20260804T003355.json`
(commit `783a744`, tag `audit-baseline-v1`).

**Esta asimetría ya había sido detectada una vez, parcialmente, en
`ADR-0012` §3** — como amenaza a la validez interna de un experimento
determinista: *"una primera corrida exploratoria usó [el camino LLM] y
obtuvo confianzas del LLM (0.85/0.95, margen 0.10) — que cayó exactamente en
el límite de `delta=0.10`"*. En ese momento se trató como un confusor a
controlar (se cambió el experimento al camino de regla). La auditoría de
2026-08-04 muestra que **no es un confusor de laboratorio — es el
comportamiento real** en el camino que un estudiante usa hoy, porque este
entorno tiene `OPENAI_API_KEY` configurada y `boundary/inbound/productores.py`
activa los productores LLM automáticamente cuando esa credencial existe.

**Consecuencia si no se corrige antes de activar cualquier política con
`delta`/`theta` no degenerados:** el sistema aplazaría o resolvería según si
una corrida particular del LLM devolvió 0.90 o 0.95 — indistinguible de
muestreo del proveedor — produciendo una apariencia de sensibilidad al
contexto que en realidad es ruido. Más engañoso para una defensa de tesis
que no tocar nada.

## 2. Decisión

**Corrección de diseño respecto al borrador inicial de este ADR**, tras leer
`runtime/domain/diagnosticar/calibracion.py` completo: `evidence_strength`
(límite inferior de Wilson sobre `soporte/total`) es matemática pura, sin
conocimiento de dominio — reutilizable tal cual. `calibrar_confianza_nueva`
NO lo es: su lógica de mejora/retroceso compara la evidencia nueva contra un
**claim vigente del mismo asunto a través del tiempo** — un concepto que
pertenece al modelo temporal de Diagnosticar (un `dominio(competencia)`
puede reinterpretarse sesión tras sesión) y que no aplica a Remediar/
Orientar, que no reinterpretan su propio historial: compiten **una vez, en
la misma ronda de deliberación D2**, contra la propuesta rival de la otra
capacidad — esa comparación ya la resuelve `mecanica.convocar()`, no debe
duplicarse dentro del productor.

Decisión final, en dos partes:

**2.1 — Mover `evidence_strength` a infraestructura compartida.**
`runtime/domain/shared/calibracion.py` (nuevo módulo, mismo patrón que
`llm_roundtrip.py`/`propuestas.py`/`objetivos.py` ya en `domain/shared/`:
infraestructura sin conocimiento de dominio). `diagnosticar/calibracion.py`
re-exporta `evidence_strength` desde ahí (`from
runtime.domain.shared.calibracion import evidence_strength`) — cero cambio
de comportamiento, cero import roto (`tests/runtime/domain/diagnosticar/
test_calibracion.py` sigue importando desde `diagnosticar.calibracion` sin
modificarse).

**2.2 — Calibrar Remediar y Orientar con `evidence_strength` directo, sin
`calibrar_confianza_nueva`.** Cada productor deriva su confianza de la
MISMA evidencia que ya lee para decidir su acción — el `fact` original al
que apunta `claim.respaldo[0]` (`claim` es la interpretación de Diagnosticar
que cada uno respalda), vía `estado.buscar(...)`:

```python
# Remediar (respalda "reforzar" quiere: cuánta evidencia sostiene el fallo)
fact = estado.buscar(claim.respaldo[0])
total = fact.contenido.get("items_totales") if fact is not None else 0
total = total or 0
confianza_final = evidence_strength(soporte=errores, total=total)

# Orientar (respalda "avanzar-con-andamiaje": cuánta evidencia sostiene el dominio)
aciertos = total - errores
confianza_final = evidence_strength(soporte=aciertos, total=total)
```

Alcance: **solo `productor_llm.py`** de Remediar y Orientar (ambas ramas,
sesión y por-objetivo) — `productor.py` (regla) de ambas capacidades NO se
toca, porque `diagnosticar/productor.py` (regla) tampoco calibra: usa una
constante fija (`Decimal("0.78")`). Ese es el patrón ya vigente en el
proyecto — calibración es un problema del camino LLM (confianza no
confiable declarada por un modelo de lenguaje), no del camino regla
(confianza fija por convención, sobre una regla 100% determinista sin
gradiente de incertidumbre propio).

El campo `"confianza"` sigue siendo parte del JSON que el LLM debe declarar
(`campos_requeridos`, prompts sin cambios) — se descarta el valor, igual que
ya hace Diagnosticar-LLM, para no tocar el contrato de prompt ya validado
empíricamente (M3 PR-2/PR-3/PR-4).

**No forma parte de esta decisión** (deliberadamente, ver §7): tocar
`mecanica.py`, `confianza.py`, `politica.py`, activar `POLITICAS["v2"]` en
producción, ni ningún principio P1–P17.

## 3. Engineering Gate (CLAUDE.md)

1. **¿Qué decisión implementa?** Generaliza el patrón de calibración que la
   Iteración 5.8 (H10) ya introdujo y dejó en producción para Diagnosticar
   — no responde a un RFC nuevo, extiende una decisión ya vigente.
2. **¿Introduce concepto nuevo?** No. `evidence_strength` ya existe, está en
   producción y probada; se relocaliza, no se reinventa.
3. **¿Rompe algún principio P1–P17?** No. Verificado explícitamente contra
   P3: cada productor sigue leyendo únicamente su propia evidencia
   respaldante (`claim.respaldo[0]` → `estado.buscar(...)`) y el estado
   compartido — nunca la propuesta ni la confianza del otro productor. La
   resolución de la tensión D2 sigue ocurriendo exclusivamente en
   `mecanica.convocar()`, sin duplicarse dentro de Remediar/Orientar.
4. **¿Requiere modificar un RFC?** No. `evidence_strength` es matemática
   pura sin acoplamiento a ningún RFC; `calibrar_confianza_nueva`
   (específica de Diagnosticar) no se toca ni se reutiliza.

## 4. Las cinco preguntas del tesista

1. **¿Qué problema resuelve?** Que Orientar declare confianza constante
   (0.85, sin relación con la evidencia) y que la variación de Remediar sea
   indistinguible del ruido de muestreo del LLM (σ=0.0289 vs. señal=0.0166).
2. **¿Por qué no se modifica la arquitectura de enjambre?** El cambio ocurre
   enteramente dentro de cada productor, sobre su propia evidencia — ninguno
   pasa a leer al otro. La coordinación sigue siendo estigmérgica (P3).
3. **¿Qué patrón existente se reutiliza?** `evidence_strength(soporte,
   total)`, relocalizada a `domain/shared/` — sin duplicar
   `calibrar_confianza_nueva`, que es específica de Diagnosticar (§2).
4. **¿Qué métricas demostrarán mejora?** Reproducir
   `consenso_remediar_orientar_llm_por_perfil.py` tras el cambio. Criterio
   numérico: la diferencia entre medias de perfiles debe superar la
   desviación estándar intra-perfil; Orientar debe dejar de ser constante
   ante `dominada: True` vs. `False`.
5. **¿Qué tests protegen el comportamiento actual?** `POLITICAS["v1"]` no
   se toca, así que la suite de deliberación no debería requerir cambios.
   Los dos tests sensibles identificados en Auditoría 3
   (`test_evidencia_de_evaluacion_produce_una_entrega_de_adaptar`,
   `test_decision_adaptativa_deriva_de_la_entrega_del_runtime`, en
   `backend/tests/test_runtime_bridge.py`) usan el camino de **regla**
   (no tocado) — protegidos por diseño, no por casualidad.

## 5. Alternativas consideradas

- **Reutilizar `calibrar_confianza_nueva` tal cual para Remediar/Orientar.**
  Rechazada tras leer el código: su semántica de mejora/retroceso asume un
  claim vigente del MISMO asunto en el tiempo — Remediar/Orientar no tienen
  ese concepto, compiten una vez por ronda vía `mecanica.convocar()`.
  Forzar el patrón habría sido inventar una comparación redundante con la
  que el kernel ya hace.
- **Activar `POLITICAS["v2"]` en producción sin calibrar antes.** Rechazada
  — Auditoría 5 demuestra con datos reales que produce apariencia de
  sensibilidad al contexto que en realidad es ruido de muestreo del LLM.
- **Calibrar solo Remediar.** Rechazada como alcance completo — dejaría a
  Orientar con varianza cero, el hallazgo más severo de los dos.
- **Dejar `evidence_strength` solo en `diagnosticar/calibracion.py` e
  importarla desde ahí en Remediar/Orientar.** Rechazada — sería un import
  cruzado entre capacidades (Remediar dependiendo del paquete de
  Diagnosticar) por una función que no tiene nada de específico de
  Diagnosticar; se relocaliza a `domain/shared/` en su lugar (§2.1).

## 6. Criterios de cierre

- `evidence_strength` vive en `runtime/domain/shared/calibracion.py`;
  `diagnosticar/calibracion.py` la re-exporta sin cambiar su propia API.
- Remediar-LLM y Orientar-LLM (sesión y por-objetivo) declaran confianza
  vía `evidence_strength` sobre su evidencia real, no el valor crudo del
  LLM.
- Reproducir `consenso_remediar_orientar_llm_por_perfil.py` tras el cambio:
  la señal (diferencia entre medias de perfiles) supera al ruido
  (desviación intra-perfil) para ambos productores; Orientar deja de ser
  constante ante `dominada: True` vs. `False`.
- Cero regresiones en `tests/runtime/deliberation/`,
  `tests/runtime/walkthrough/test_P13_{remediar,orientar}_reglas_vs_llm.py`,
  `tests/runtime/walkthrough/test_orientar_remediar_por_objetivo.py`,
  `tests/runtime/walkthrough/test_FIX_remediar_dominada_true_no_hace_loop.py`,
  `tests/runtime/domain/diagnosticar/test_calibracion.py`, y los dos tests
  de `test_runtime_bridge.py` citados en §4.5.
- `POLITICAS["v1"]` sigue resolviendo exactamente igual para los casos ya
  cubiertos por tests existentes.

## 7. Alcance NO cubierto por este ADR (deliberado)

- No activa pesos de política v2, ni introduce una `POLITICAS["v3"]` —
  condicionado explícitamente a que este se cierre y se re-mida primero
  (secuencia acordada en el documento de decisión post-auditoría,
  2026-08-04).
- No persiste margen ni razón en `DeliberacionEntry`/`DecisionEntry` — ADR
  separado, toca un reducer del kernel.
- No conecta `evidence_service.py` a `estado.deliberaciones` — otro
  ADR/commit separado.
- No modifica `mecanica.py`, `confianza.py`, ningún principio P1–P17, ni el
  contrato de `LLMProvider`.

---

*Origen: cadena de Auditorías 2–5 (2026-08-04) sobre el motor de consenso.
Rama de implementación: `feat/confidence-calibration-remediation-orientation`.
Baseline: tag `audit-baseline-v1` (commit `783a744`).*
