# ADR-0014 — Persistencia del margen en `Resuelta`/`Aplazada`

- **Estado:** Aceptado (2026-08-04)
- **Fecha:** 2026-08-04
- **Preserva:** `runtime/kernel/deliberation/mecanica.py` (mecánica de consenso
  D1/D2/D3, ninguna rama ni condición cambia), `runtime/kernel/deliberation/
  confianza.py` (sin cambios), `runtime/kernel/deliberation/politica.py`
  (sin cambios), ADR-0001 (serialización canónica), ADR-0012/ADR-0013
  (sin cambios de comportamiento)
- **Criterio de aceptación:** ver §5

## 1. Contexto

`ADR-0013 §7` dejó registrado explícitamente como fuera de alcance: *"No
persiste margen ni razón en `DeliberacionEntry`/`DecisionEntry` — ADR
separado, toca un reducer del kernel."* Ese hueco es real: `convocar()`
(`mecanica.py`) ya calcula `margen = puntajes[ganador] - puntajes[rival]`
en cada resolución (línea 210), lo usa para decidir la rama (`Resuelta` /
`Resuelta` provisional / `Aplazada` / `Escalada`), y lo **descarta** —
salvo por `Aplazada.evidencia_faltante`, que lo embebe como texto libre
dentro de una oración, no como dato consultable.

Consecuencia práctica: hoy, reconstruir "por qué ganó" una decisión
requiere volver a ejecutar `derivar_consenso(replay, política)` sobre
toda la sesión (RFC-0007 §2.2) — el margen no es un atributo persistido
de la decisión, sino un valor recalculado en cada lectura. Para
explicabilidad ante jurado (`RuntimeConsole`, Modo Evidencia) esto ya
funciona, pero obliga a "reconstruir para explicar" en vez de "leer para
explicar".

Pregunta de investigación (extiende H10): dado que el margen ya se paga
computacionalmente en el momento de la deliberación, ¿debe persistirse
como parte del registro en vez de derivarse en cada lectura? Aplica la
Regla de derivación (CLAUDE.md) en su cláusula de excepción explícita:
*"salvo razón explícita de rendimiento o auditoría"* — la razón aquí es
auditoría/explicabilidad de tesis, exactamente el caso previsto.

## 2. Decisión

Agregar un campo opcional `margen: Decimal | None = None` a `Resuelta` y
a `Aplazada` (`runtime/kernel/state/entries.py`) y poblarlo en los tres
sitios donde `convocar()` ya calcula `margen` localmente
(`mecanica.py`, rama `Resuelta` por política, rama `Resuelta` provisional
por urgencia, rama `Aplazada`) — **cero cómputo nuevo**, mismo patrón que
Épica 4/Replay Cognitivo ("el cómputo ya se pagaba; solo dejó de
descartarse").

`Escalada` queda **fuera de esta decisión**: la vía RESERVA (`asunto in
politica.asuntos_reservados`) escala "sin computar resolución" — no hay
margen que persistir ahí por diseño (`mecanica.py` línea ~170). La vía
LÍMITE DE RECONVOCATORIA sí ocurre dentro del bloque donde `margen` está
definido, pero mezclar un campo presente-a-veces según la vía de
escalada es una segunda decisión (¿cuál margen, el de la última
`Aplazada` de la cadena?) que esta ADR no resuelve — se deja
explícitamente para una iteración futura si aparece necesidad concreta.

`Resuelta.regla` (`"mayor-confianza-declarada"` / `"provisional-por-
urgencia"`) y `Aplazada.evidencia_faltante` ya cumplen el rol de "razón"
— no se agrega un campo de texto adicional; sería un concepto duplicado
sin respaldo.

**Compatibilidad hacia atrás (obligatoria — hay sesiones reales en
Postgres con transiciones ya persistidas sin este campo):**
`margen: Decimal | None = None` es aditivo — `reconstruccion.py::
_resultado_deliberacion` lee `datos.get("margen")` y produce `None`
cuando la clave no existe en transiciones históricas. Verificado contra
`cadena.py::verificar()`: la integridad hash NUNCA re-serializa un
objeto reconstruido — recomputa el hash directamente sobre
`RegistroTransicion.canonico` (los bytes ya almacenados en el momento de
escritura). Añadir un campo a la forma actual del dataclass no altera ni
un byte de una transición ya encadenada; el campo nuevo solo aparece en
transiciones nuevas, escritas después de este cambio.

## 3. Engineering Gate (CLAUDE.md)

1. **¿Qué decisión implementa?** Cierra el hueco declarado por
   `ADR-0013 §7`. No responde a un RFC nuevo — persiste un valor que
   `RFC-0006 §4` (mecánica de margen/δ) y `RFC-0007 §2.2` (Consenso) ya
   definen conceptualmente; solo cambia CUÁNDO se fija.
2. **¿Introduce concepto nuevo?** No. `margen` ya es un concepto nombrado
   en `mecanica.py`, `ADR-0012` y `RFC-0007 §2.2` (`MetricasConsenso.
   margenes_resolucion`); se persiste, no se inventa.
3. **¿Rompe algún principio P1–P17?** No. No toca reducers de decisión
   (`DecisionEntry` sin cambios), no altera ninguna rama de `convocar()`
   (misma lógica, mismos resultados — el campo se agrega al valor que la
   rama ya construía), no depende de reloj ni azar (P12).
4. **¿Requiere modificar un RFC?** No. Es un campo persistido adicional
   sobre una estructura que RFC-0006/RFC-0007 ya especifican
   conceptualmente.

## 4. Alternativas consideradas

- **Persistir margen en `DecisionEntry` en vez de en `Resuelta`/
  `Aplazada`.** Rechazada: `DecisionEntry.confianza` ya se deriva de su
  `origen` (la deliberación) por diseño explícito de INV-6 ("no puede
  afirmar sobre su procedencia nada que su origen no sostenga") —
  duplicar el margen ahí sería copiar un dato que ya es alcanzable por
  `origen` sin romper esa regla, exactamente el caso que la Regla de
  derivación busca evitar salvo razón explícita, y aquí la razón
  (auditoría) ya está resuelta en el nivel correcto: la deliberación
  misma.
- **Persistir también en `Escalada`.** Rechazada por ahora (ver §2):
  la vía RESERVA no tiene margen; forzar un campo condicional habría
  sido una decisión de diseño adicional sin necesidad concreta que la
  motive hoy.
- **Reemplazar el texto de `evidencia_faltante` por uno generado desde
  el campo `margen`.** Rechazada: cambiaría el contrato de un campo ya
  usado por `INV-7` (`_validar_resultado` exige `evidencia_faltante` no
  vacío) y por tests existentes; el campo nuevo es aditivo, no
  reemplaza al texto narrativo.

## 5. Criterios de cierre

- `Resuelta`/`Aplazada` ganan `margen: Decimal | None = None` en
  `entries.py`.
- `convocar()` puebla `margen` en sus tres construcciones sin tocar
  ninguna condición existente.
- `reconstruccion.py::_resultado_deliberacion` reconstruye `margen`
  desde el canónico cuando existe, `None` cuando no (compatibilidad con
  sesiones reales ya persistidas).
- Test nuevo que verifica: (a) `convocar()` puebla `margen` con el valor
  correcto en `Resuelta` y `Aplazada`; (b) deserializar una transición
  SIN clave `margen` (forma histórica) produce `margen=None` sin error.
- Cero regresión en `tests/runtime/deliberation/`,
  `tests/runtime/invariants/test_INV_7_reducer_deliberaciones.py`,
  `tests/runtime/reconstruction/`.
- `POLITICAS["v1"]`/`POLITICAS["v2"]` resuelven exactamente igual que
  antes — este ADR no cambia comportamiento, solo lo hace legible sin
  recalcularlo.

## 6. Alcance NO cubierto (deliberado)

- No expone `margen` en ningún endpoint HTTP nuevo — los boundary
  surfaces de RFC-0007 (`consulta_traza`, `consulta_consenso`) ya
  exponen el resultado serializado; si `RuntimeConsole` debe resaltarlo
  visualmente es una pieza de frontend separada, no de este ADR.
- No toca `Escalada`, `DecisionEntry`, `mecanica.py` (lógica), `politica.py`
  ni `confianza.py`.
- No activa `POLITICAS["v2"]` en producción — sigue condicionado a un ADR
  propio, ahora con este trabajo de trazabilidad ya cerrado como
  precondición declarada por el tesista.

---

*Origen: brecha declarada explícitamente en ADR-0013 §7. Rama de
implementación: `feat/confidence-calibration-remediation-orientation`.*
