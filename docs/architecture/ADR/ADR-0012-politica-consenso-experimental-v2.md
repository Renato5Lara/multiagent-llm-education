# ADR-0012 — Política de consenso experimental "v2" (delta/theta no degenerados)

- **Estado:** Aceptado (2026-08-01)
- **Fecha:** 2026-08-01
- **Preserva:** `runtime/kernel/deliberation/mecanica.py` (mecánica de consenso D1/D2/D3,
  sin cambios), `runtime/kernel/deliberation/confianza.py` (axiomas A1-A8, sin cambios),
  `runtime/kernel/deliberation/politica.py` (`Politica`/`POLITICAS`, extendido sin
  romper `"v1"`)
- **Criterio de aceptación:** ver §4

## 1. Contexto

Una auditoría del mecanismo de consenso (2026-08-01) encontró que la política
`"v1"` — la única existente, gobernando producción — tiene sus seis parámetros
en el valor mínimo/degenerado posible: `delta=0`, `theta=0`, `pesos_asunto={}`,
`asuntos_reservados=∅`, `peso_refuerzo=peso_refutacion=peso_decaimiento=0`.
Documentado explícitamente en el propio módulo: bajo estos valores, las ramas
de aplazamiento (`Aplazada`) y escalada (`Escalada`) del mecanismo son
"estructuralmente inalcanzables" — toda tensión D1/D2 se resuelve en un solo
paso por "mayor confianza declarada gana".

La auditoría también confirmó, con datos reales (validación E2E previa), que
la rivalidad SÍ ocurre hoy: Orientar y Remediar producen propuestas rivales
sobre el mismo asunto (`siguiente-paso(sesion)`) cuando Diagnosticar interpreta
`dominada=False` — la "tensión canónica n.º 1" (documentada en los propios
productores). El mecanismo de deliberación se ejercita con evidencia real; lo
que nunca se ejercita es su capacidad de reconocer incertidumbre.

Pregunta de investigación: ¿una política con `delta`/`theta` no degenerados
produce comportamiento deliberativo observable (aplazamiento) ante la misma
evidencia que hoy se resuelve en un solo paso, sin modificar productores, sin
introducir azar ni LLM en la resolución?

## 2. Decisión

Se agrega `POLITICAS["v2"]` (`runtime/kernel/deliberation/politica.py`) como
una segunda entrada, **aditiva** — `"v1"` no se modifica, ningún productor,
`mecanica.py` ni `confianza.py` cambian:

```python
"v2": Politica(
    peso_refuerzo=Decimal("0"),
    peso_refutacion=Decimal("0"),
    peso_decaimiento=Decimal("0"),
    theta=Decimal("0.5"),
    delta=Decimal("0.10"),
    pesos_asunto={},
    asuntos_reservados=frozenset(),
    limite_reconvocatoria=2,
)
```

Única variable independiente deliberada: `delta` (con `theta` como ajuste
conservador de soporte). `pesos_asunto` y `asuntos_reservados` quedan en su
valor neutro de v1 a propósito — introducirlos mezclaría una segunda variable
pedagógica (ponderación por asunto, reserva de autoridad al docente) en un
experimento diseñado para aislar una sola.

## 3. Experimento y evidencia obtenida

Script aislado `backend/scripts/experimentos/consenso_politica_v1_vs_v2.py` —
NO usa `app/services/runtime_bridge.py` ni la selección global de política;
abre sus propias sesiones (`session_id` con timestamp, frescas en cada
corrida) contra el mismo almacén real, con `version_politica` explícito, y
llama `ejecutar_walkthrough` directo con los productores por defecto (regla).

**Amenaza a la validez interna detectada y controlada.** Este entorno tiene
`OPENAI_API_KEY` configurada; el camino de producción (`registrar_hecho`)
selecciona productores LLM automáticamente cuando esa credencial existe
(`runtime/boundary/inbound/productores.py`). Una primera corrida exploratoria
usó ese camino y obtuvo confianzas del LLM (0.85/0.95, margen 0.10) — que
cayó exactamente en el límite de `delta=0.10` y resolvió en vez de aplazar,
mezclando una segunda variable (productor regla vs. LLM) en el experimento.
Detectado, no forzado: se corrigió llamando `ejecutar_walkthrough` directo
para fijar los productores en su valor por defecto (regla, determinista, sin
red). Las dos sesiones exploratorias quedan sin borrar en el almacén
(`experimento:politica-{v1,v2}:tension-canonica-1`, sin sufijo) — documentadas
aquí como inválidas, no como residuo: evidencia del control de una variable
de confusión real durante el diseño experimental.

**Resultado (corrida determinista, run_id `20260801T094521`,
`backend/experiments/results/consenso_v1_vs_v2_20260801T094521.json`):**

| | v1 (delta=0) | v2 (delta=0.10) |
|---|---|---|
| Propuestas rivales | orientar:avanzar-con-andamiaje:0.75 / remediar:reforzar:0.82 | idénticas |
| Resultado | `RESUELTA` (regla `mayor-confianza-declarada`, gana Remediar) | `APLAZADA` |
| Detalle | diseño derivado: reforzar/visual/fundamentos | *"evidencia sobre 'siguiente-paso(sesion)' que discrimine entre T-000004/e1 y T-000005/e1: margen 0.07 < delta 0.10"* |
| Transiciones | 8 (llega hasta Adaptar) | 6 (se detiene esperando más evidencia) |

Hipótesis confirmada: misma evidencia, mismos productores, misma arquitectura
— únicamente `delta` distingue "una voz gana" de "el sistema declara qué
evidencia necesita para decidir".

### 3.1. Instrumentación con RFC-0007 — Paisaje y Consenso (adenda, 2026-08-02)

Una vez cerradas las métricas de Paisaje (H8) y Consenso (RFC-0007 §2.2,
mini-épicas separadas, commits `d0bacde..205afd2`), se repitió el mismo
Escenario A con `backend/scripts/experimentos/consenso_replay_v1_vs_v2.py`
— MISMA evidencia, MISMA metodología, MISMO criterio de éxito que §3 — y se
instrumentó cada réplica real con `derivar_paisaje`/`derivar_consenso` sobre
su propia historia, bajo su propia política (nunca recalculando una réplica
con la política de la otra: `calcular_confianza_efectiva` no depende de
`delta`/`theta`, así que esa recomputación habría sido numéricamente vacía
— ver el docstring del script). No es una ADR nueva: es la misma decisión
de §2, con más instrumento para observarla.

**Resultado (run_id `20260802T003351`,
`backend/experiments/results/consenso_replay_v1_vs_v2_20260802T003351.json`):**

| | v1 (delta=0) | v2 (delta=0.10) |
|---|---|---|
| Paisaje — `siguiente-paso(sesion)` | densidad 1, conflicto `{}`, entropía **0.0** | densidad 2, conflicto `latente`, entropía **0.9986** |
| Consenso | 1 convocatoria, 1 resuelta, margen 0.07 | 1 convocatoria, 1 aplazada, margen 0.07, cadena de reconvocatoria [1] |

El margen recalculado (0.07) coincide exactamente entre ambas políticas —
confirma por evidencia, no solo por argumento, que el margen es una
propiedad de la evidencia (los `ce` declarados), no de la política que lo
evalúa; lo que cambia es exclusivamente si `margen >= delta` admite avanzar
o no. La diferencia observable real está en el paisaje: v1 colapsa a
certeza (entropía 0, sin conflicto, el claim perdedor queda superseded por
la cascada hacia Adaptar); v2 preserva la tensión visible (entropía cercana
a 1 bit — dos rivales casi empatados —, conflicto `latente` con una
`Aplazada` abierta). Es la primera vez que el "colapso vs. preservación de
incertidumbre" que motiva H10 queda medido, no solo descrito en prosa.

## 4. Criterio de aceptación

- `POLITICAS["v2"]` agregada sin modificar `"v1"`, `mecanica.py`,
  `confianza.py` ni ningún productor — verificado por `git diff` y por la
  suite completa de tests de deliberación (`tests/runtime/deliberation/`,
  Parte 0/B/C/D/E/F + confianza A1-A7 + walkthrough aplazamiento/escalada):
  81 passed, cero regresión.
- Experimento reproducible: cada corrida abre sesiones frescas (timestamp) y
  exporta su resultado a JSON — no depende de estado persistido de una
  corrida anterior.
- Resultado obtenido y exportado, hipótesis confirmada con la ruta
  determinista (regla), amenaza de validez interna (selección automática de
  LLM) identificada, documentada y controlada.

## 5. Alcance NO cubierto por esta ADR (deliberado)

- `pesos_asunto` y `asuntos_reservados` — ponderación pedagógica por asunto y
  reserva de autoridad al docente (escalada real) quedan para un experimento
  posterior ("Escenario B", reconvocatoria y escalada por cadena de
  aplazamientos) — mezclar esas variables aquí habría invalidado el
  aislamiento de `delta` como única variable independiente.
- Ninguna capacidad (Tutorizar u otra) gana autoridad de propuesta nueva —
  eso es "Escenario C" y requeriría verificar contra RFC-0002 antes de
  siquiera diseñarse; explícitamente fuera de alcance de esta ADR.
- `version_politica` sigue siendo una constante fija (`"v1"`) en
  `app/services/runtime_connection.py` para todo el tráfico de producción —
  esta ADR no introduce selección por cohorte; el experimento vive en un
  script aislado, no en un camino de producción.
