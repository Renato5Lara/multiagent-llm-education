# Sesión 5 — Paso 1: Medición de rendimiento (sin código)

## Metadata

- **Fecha:** 2026-08-05
- **Rama:** `investigacion/sesion5-rendimiento`
- **Protocolo:** observar → **medir** → clasificar → decidir → implementar.
  Este documento es Paso 1 — establecer una línea base real antes de
  proponer cualquier optimización. **Ningún archivo de código
  modificado.** Medición contra el sistema real (backend FastAPI real
  reiniciado en `:8000`, frontend Vite real en `:5173`, PostgreSQL real,
  OpenAI real — mismo entorno que validó H1/H2 de la Sesión UX/UI),
  cuenta de prueba `ux.nuevo.recorrido@upao.edu.pe`, navegador real.
- **Insumo:** §11 de `Auditoria-UPAO-MAS-EDU-2026-08-05.docx` (texto
  original, extraído directamente del `.docx`):

  > **11 — Problemas de rendimiento**
  > Latencia de personalización visible: cada paso "Personalizando tu
  > siguiente paso…" tomó consistentemente entre 6 y 10 segundos.
  > Carga inicial de Pyodide tarda unos segundos la primera vez por
  > lección — no se probó si se cachea entre lecciones.
  > No se realizaron pruebas de carga ni de concurrencia — fuera del
  > alcance verificado.

- **Método de medición:** `performance.getEntriesByType('resource')`
  (Resource Timing API real del navegador, vía `javascript_tool`
  ejecutado en la página) para duración exacta de cada request HTTP,
  cruzado contra el log real de `uvicorn` (timestamps de cada llamada a
  `POST /api/students/cycle-evidence` y cada `HTTP Request: POST
  https://api.openai.com/v1/chat/completions`). Ninguna medición es una
  estimación — todas vienen de logs/timing reales del sistema en vivo.

---

## Hallazgo 1 — Latencia de personalización: confirmada, causa raíz localizada con precisión

### Medición (6 llamadas reales consecutivas, misma sesión de estudiante)

| # | Duración total (`cycle-evidence`) | Llamadas a OpenAI dentro de la misma request |
|---|---|---|
| 1 | **6232 ms** | 2 (secuenciales) |
| 2 | 3827 ms | 1 |
| 3 | 3640 ms | 1 |
| 4 | 2042 ms | 1 |
| 5 | 2168 ms | 1 |
| 6 | 2683 ms | 1 |

Promedio: 3432 ms. Rango: 2042–6232 ms.

**Confirma el hallazgo original de la auditoría** (6–10 s) como el
extremo superior observable — ocurre cuando la petición requiere **dos**
llamadas secuenciales a OpenAI en vez de una. No se observó ningún caso
por debajo de 2 s ni por encima de 6.3 s en esta muestra.

### Causa raíz — no es frontend, no es Runtime, no es Postgres

Cruce exacto de timestamps del log real (`uvicorn`), petición #1 (la más
lenta, 6232.02 ms medidos por el propio backend):

```
20:13:48,426 | httpx | POST https://api.openai.com/v1/chat/completions → 200 OK
20:13:50,720 | httpx | POST https://api.openai.com/v1/chat/completions → 200 OK
20:13:50,848 | upao-mas-edu | POST /api/students/cycle-evidence → 200 (6232.02ms)
```

Las 6 peticiones muestran el mismo patrón sin excepción: la última
llamada a OpenAI termina entre 50 y 90 ms antes de que la petición HTTP
completa termine. Es decir, **prácticamente el 100% del tiempo de cada
petición es tiempo de espera de la API de OpenAI** — el trabajo propio
del backend (enrutamiento, reducers del Runtime, escritura a Postgres,
serialización de la respuesta) consume menos de 100 ms en cada caso.

**No es un problema de frontend** (el navegador solo espera la
respuesta del backend, no hace trabajo pesado propio en este tramo).
**No es un problema de Postgres ni del propio motor del Runtime**
(su contribución medida es <100 ms, ~2% del total en el peor caso).
**Es, con evidencia directa, el costo de red + inferencia de la API de
OpenAI**, y específicamente:

**Cuando ocurren dos llamadas, son secuenciales, no paralelas** — la
segunda llamada a OpenAI empieza después de que la primera termina
(20:13:48,426 → 20:13:50,720, sin solapamiento visible en el log). Si
esas dos llamadas no tienen una dependencia real de datos entre sí (una
necesita el resultado de la otra), ejecutarlas en paralelo reduciría la
latencia de ese caso de ~6.2 s a ~el tiempo de la más lenta de las dos
(~3.8 s) — pero **esto es una hipótesis de optimización, no verificada
todavía**: no se investigó en este documento cuáles son esas dos
llamadas ni si existe una dependencia real de datos entre ellas (Paso 2
de esta sesión, no abierto aquí).

### Clasificación (sin decidir remediación)

Hallazgo confirmado con evidencia directa de logs reales, causa raíz
localizada con precisión (no una hipótesis). Candidato de alto valor
para Paso 2 — pero identificar **cuáles** capacidades del Runtime
producen esas llamadas a OpenAI, y si son paralelizables sin cambiar
ninguna decisión pedagógica, requiere leer código todavía no leído en
este documento.

---

## Hallazgo 2 — Pyodide: arquitectura aclarada, caching confirmado, pregunta original respondida

### Arquitectura (no documentada antes en ningún bug report de esta auditoría)

Pyodide corre dentro de un **Web Worker** (`pyodideWorker.ts`,
cargado desde `usePyodide.ts`) — confirmado porque
`performance.getEntriesByType('resource')` ejecutado en el contexto de
la página principal **no** muestra ninguna descarga de los assets de
Pyodide (`pyodide.js`, `.wasm`, paquetes de Python) — esas descargas
ocurren dentro del contexto aislado del worker, invisible al
Performance API del hilo principal. Esto es, en sí mismo, una decisión
de arquitectura correcta para no bloquear la interfaz mientras Pyodide
inicializa — pero también significa que medir su carga exige
instrumentación específica del worker, no disponible sin tocar código.

### Medición directa — SÍ se cachea entre lecciones (pregunta original respondida)

La auditoría original marcó explícitamente "no se probó si se cachea
entre lecciones". Se probó en esta sesión, con dos observaciones
directas:

1. **Dentro de la misma carga de página:** durante el recorrido
   completo de Ciclo 1 → Ciclo 2 → Ciclo 3 de la Misión 1 (varias
   pantallas de editor distintas), el mensaje "Cargando Python..." solo
   apareció **una vez**, en el primer editor de Ciclo 1. Los editores de
   los ciclos siguientes mostraron "Ejecutar" disponible de inmediato,
   sin ningún estado de carga — el worker y su runtime de Pyodide
   persisten mientras la pestaña no se recarga, sin importar cuántos
   ciclos/lecciones distintas se visiten.
2. **Tras una recarga completa de página** (`location.reload()`, un
   escenario más agresivo que "cambiar de lección"): Pyodide volvió a
   mostrar "Cargando Python..." pero se resolvió en **2 segundos o
   menos** (confirmado con `performance.now()` antes/después) — mucho
   más rápido que la sensación de "unos segundos" de la primera carga
   real de la sesión completa (más temprano en este mismo recorrido,
   antes de cualquier caché tibia). Consistente con que los assets de
   Pyodide, aunque se soliciten desde un worker, sí pasan por la caché
   HTTP normal del navegador — una segunda carga en la misma sesión de
   navegador los sirve desde caché en vez de red.

### Clasificación

**No es un problema de rendimiento medible con esta evidencia.** La
preocupación original de la auditoría (¿se recarga entre lecciones?)
tiene una respuesta empírica directa: no, dentro de una misma sesión de
pestaña. La única carga "fría" real ocurre una vez por sesión de
navegador (o tras recarga completa), y esa carga fría ya se beneficia de
caché HTTP normal si el navegador visitó la plataforma antes. No se
identificó ninguna acción de remediación necesaria aquí — a diferencia
del Hallazgo 1, este no pasa a Paso 2 con una hipótesis de optimización
pendiente.

---

## No investigado en este documento (explícitamente fuera de Paso 1)

- **Pruebas de carga y concurrencia** — la propia auditoría original
  las declaró fuera de alcance verificado; esta sesión tampoco las hizo
  (una sola sesión de estudiante, sin usuarios concurrentes).
- **Código muerto y deuda técnica** — segundo frente de Sesión 5, no
  abierto en esta sesión por decisión explícita del tesista (medir
  rendimiento primero).
- **Cuáles capacidades del Runtime disparan las llamadas a OpenAI**, y
  si son paralelizables — pregunta que abre Paso 2, no respondida aquí.

## Resumen para Paso 2

| Hallazgo | Estado | Siguiente paso |
|---|---|---|
| H1 — Latencia de personalización (6-10s) | **Confirmado, causa raíz precisa: 1-2 llamadas secuenciales a OpenAI, ~98-100% del tiempo total** | Paso 2: identificar qué capacidades llaman al LLM en esta ruta y si son paralelizables sin tocar ninguna decisión pedagógica |
| H2 — Caché de Pyodide entre lecciones | **Respondido: sí se cachea (mismo worker persiste; recarga completa se beneficia de caché HTTP, ~2s)** | Ninguno — no pasa a Paso 2 |

Ningún cambio de código en este documento. Paso 2 (mapear la causa raíz
contra el código real del Runtime/Boundary, mismo patrón que la Sesión
UX/UI) queda pendiente de apertura explícita.
