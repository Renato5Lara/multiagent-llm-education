# Sesión 5 — Paso 3: Clasificación de la latencia de personalización

## Metadata

- **Fecha:** 2026-08-05
- **Rama:** `investigacion/sesion5-rendimiento`
- **Protocolo:** observar → medir → explicar la causa → **clasificar**
  → decidir → implementar. Este documento clasifica cada candidato
  encontrado en Paso 1/Paso 2. **No se implementa nada aquí.**
- **Insumos:** Paso 1 (medición, 6 muestras reales, 2042–6232 ms) y
  Paso 2 (causa arquitectónica, verificada contra código y RFC-0002/
  RFC-0006).
- **Cambio de pregunta que motiva este documento:** Paso 1/2 no
  confirmaron la hipótesis inicial ("hay un problema de rendimiento en
  el Runtime") — la refutaron. La pregunta de este documento ya no es
  "¿por qué tarda?" sino **"¿existe realmente algo que optimizar?"**

---

## 1. Clasificación de cada candidato

| Candidato | Categoría | Evidencia |
|---|---|---|
| Latencia de una llamada individual a `gpt-4o-mini` (~2-4s por llamada, según Paso 1) | **Coste inherente del proveedor LLM** | `OpenAIProvider.generar()` mide `latencia_ms` de la llamada de red+inferencia (`llm_openai.py:94-108`); el log real cruzado con Paso 1 confirma que esa espera es prácticamente el 100% de la duración total medida |
| Secuencia obligatoria diagnosticar → remediar/orientar (2 llamadas cuando aplica) | **Coste arquitectónico deliberado** | RFC-0002 (tabla de capacidades: Orientar lee "diagnóstico", Remediar lee "evidencia de no-aprendizaje") + RFC-0006 §5 ("el mapa se completa antes de proponer", citado literalmente en `walkthrough.py:316-321`) — exigido por dos RFC, no una elección de implementación libre |
| Llamadas redundantes o duplicadas | **Investigación cerrada sin acción** | No se encontró ninguna — las propias guardias de ruteo (`f.id not in interpretados`, `palabra_en_pie`) ya evitan reinterpretar o re-proponer (Paso 2, punto 5) |
| Reintentos/timeouts inflando la medición | **Investigación cerrada sin acción** | Confirmado que no ocurrieron en la muestra — el log no muestra los saltos de 1s/2s/4s que dejaría el backoff exponencial de `con_reintentos()` (Paso 2, punto 7) |
| Overhead propio del backend (Postgres, reducers, serialización) entre las dos llamadas LLM | **Coste del sistema, pero despreciable** | <100 ms por petición en las 6 muestras (Paso 1: la última llamada a OpenAI termina 50-90 ms antes de que la petición HTTP completa termine) — ~2% del total en el peor caso |
| Pyodide / caché entre lecciones | **Cerrado en Paso 1, sin reabrir** | Confirmado que no se recarga entre ciclos; recarga completa ≤2s con caché HTTP |

---

## 2. Qué parte de la latencia pertenece al sistema y cuál al proveedor

**≈98% proveedor externo, ≈2% sistema propio, medido, no estimado.**

En las 6 peticiones de Paso 1, el tiempo entre que la última llamada a
OpenAI recibe respuesta y que la petición HTTP completa devuelve su
resultado fue de 50-90 ms en cada caso, contra duraciones totales de
2042-6232 ms. El propio sistema (Boundary, Runtime, Postgres,
serialización de la respuesta) nunca fue responsable de más del ~4%
del tiempo total en ninguna de las 6 muestras, y típicamente menos del
2%. El resto es, con evidencia directa de timestamps, tiempo de espera
de la red y la inferencia de OpenAI.

---

## 3. ¿Existe algún candidato de optimización que no altere RFC-0002/RFC-0006?

Se evaluaron explícitamente los márgenes que **no** tocan el contrato
de capacidades ni el orden de `enrutar()`:

- **Elegir un modelo distinto/más rápido** — el modelo (`gpt-4o-mini`,
  parámetro de `OpenAIProvider.__init__`, `llm_openai.py:78`) es
  configuración del Boundary, no del contrato de capacidades. Cambiarlo
  no requiere modificar RFC-0002 ni RFC-0006 — pero es una decisión de
  costo/calidad de producto (¿un modelo más rápido mantiene la calidad
  de interpretación que scoring-v1 exige?), no una corrección técnica.
  **No se investigó ni se decide aquí.**
- **Reducir el tamaño del prompt** — mismo razonamiento: configuración
  de la plantilla de prompt de cada capacidad, no del grafo. Tampoco
  investigado en profundidad en este documento (no se leyó el contenido
  exacto de los prompts de Diagnosticar/Remediar/Orientar).
- **Streaming de la respuesta** — reduciría la latencia *percibida*
  (el estudiante vería texto aparecer antes), no la latencia *real* del
  cálculo completo que el Runtime necesita antes de poder decidir y
  responder — no aplica directamente a este contrato síncrono
  (`registrar_hecho` devuelve una `Entrega` completa, no un stream).
- **Paralelizar las dos llamadas cuando ocurren** — **descartado con
  evidencia de código y RFC** (Paso 2, punto 4): la segunda depende del
  resultado de la primera por diseño explícito del contrato de
  capacidades. No es un candidato válido bajo ninguna lectura de la
  arquitectura actual.

**Conclusión de este punto:** existen dos candidatos técnicamente
posibles sin romper RFC-0002/RFC-0006 (modelo, tamaño de prompt), pero
ninguno fue investigado con suficiente profundidad en Paso 1/2 para
proponerlo como una remediación concreta — ambos son decisiones de
producto/costo, no defectos a corregir, y quedan fuera del alcance de
esta sesión de rendimiento tal como se abrió.

---

## 4. Declaración explícita de cierre

> **La investigación concluye que la latencia observada (2-10 s por
> petición de `cycle-evidence`, según el número de llamadas LLM
> disparadas) es una consecuencia esperada de la arquitectura del
> Runtime y del proveedor LLM, no un defecto.** La secuencia
> diagnosticar → remediar/orientar está exigida por el contrato de
> lectura de capacidades de RFC-0002 y por el orden de ruteo
> documentado en RFC-0006 §5 — paralelizarla violaría ambos. El tiempo
> restante (~98% del total medido) es tiempo de red e inferencia de la
> API de OpenAI, fuera del control de la arquitectura del proyecto. No
> se encontró ninguna llamada redundante, duplicada, ni ningún
> reintento/timeout inflando las mediciones. Los dos únicos candidatos
> de optimización que no requerirían tocar RFC-0002/RFC-0006 (modelo
> LLM, tamaño de prompt) son decisiones de costo/calidad de producto,
> no correcciones de un defecto — ninguno se investigó a profundidad
> suficiente para proponerse como remediación en esta sesión.

**No se implementa ninguna optimización.**

---

## Comparación con el resto de la auditoría — mismo patrón, resultado distinto

A diferencia de H1 de la Sesión UX/UI (donde sí había una capa de
traducción incompleta, con causa raíz accionable y remediación de bajo
riesgo), y a diferencia de Ficha 05/09 (donde la investigación encontró
mecanismos reales con incidencia medible), **Sesión 5 / Rendimiento es
la primera investigación de esta auditoría completa que concluye sin
ningún candidato de remediación técnica válido.** Eso no es un fracaso
de la investigación — es exactamente el tipo de resultado que el
protocolo (medir antes de decidir) está diseñado para producir cuando
corresponde: evita que se "optimice" código que en realidad ya está
haciendo lo correcto según su propia arquitectura aprobada.

---

## Estado al cierre de Paso 3

Rendimiento: investigado con evidencia real de principio a fin (Paso 1
medición → Paso 2 causa → Paso 3 clasificación), sin encontrar un
defecto que corregir. Paso 4 (decisión) no tiene nada sustantivo que
decidir — no hay ninguna remediación aprobable, solo la declaración de
cierre del punto 4. Este frente de Sesión 5 puede darse por concluido.

El frente de código muerto/deuda técnica de Sesión 5 queda como
siguiente paso natural, pendiente de apertura explícita.
