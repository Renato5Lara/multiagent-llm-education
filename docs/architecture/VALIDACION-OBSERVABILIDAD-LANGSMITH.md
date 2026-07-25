# Validación de la Infraestructura de Observabilidad mediante LangSmith

**Documento técnico independiente**
**Proyecto:** Sistema Multiagente Educativo — UPAO-MAS-EDU
**Fecha:** 2026-07-21
**Autor:** Equipo de arquitectura del proyecto (asistido por Claude)
**Tipo de documento:** Evidencia técnica de instrumentación y observabilidad

> Este documento es autónomo: puede leerse, entregarse y evaluarse por separado, sin necesidad de abrir ningún otro archivo del proyecto. Donde una explicación pertenece a otro documento, se referencia explícitamente en lugar de duplicarse.

---

## Índice

1. Introducción
2. Objetivos
3. Alcance
4. Arquitectura de Observabilidad
5. Componentes instrumentados
6. Estrategia de instrumentación
7. Integración con LangSmith
8. Casos de prueba ejecutados
9. Métricas observadas
10. Evidencia visual
11. Resultados obtenidos
12. Limitaciones
13. Buenas prácticas implementadas
14. Conclusiones
15. Referencias

---

## 1. Introducción

El proyecto implementa una arquitectura multiagente para la adaptación de contenido educativo, construida sobre `LangGraph` como motor de ejecución del grafo de agentes y modelos de lenguaje (OpenAI) como proveedor de razonamiento en varias de sus capacidades. Antes de este trabajo, la arquitectura ya contaba con un mecanismo propio de observabilidad —definido por RFC-0007— basado en la reconstrucción determinista del historial de eventos del sistema. Sin embargo, no existía ninguna integración con una herramienta externa de trazado como LangSmith, pese a que la dependencia figuraba en el proyecto desde antes.

Este documento describe la instrumentación de LangSmith que se añadió al sistema, la estrategia arquitectónica que se siguió para hacerlo sin contradecir las decisiones ya aceptadas del proyecto, y la evidencia obtenida al ejecutar un protocolo formal de diez pruebas (AG-01 a AG-10) sobre esa instrumentación.

## 2. Objetivos

- Documentar la instrumentación de observabilidad operativa implementada sobre el runtime multiagente.
- Explicar la estrategia de integración con LangSmith y su relación con el mecanismo de trazabilidad ya definido por la arquitectura (RFC-0007).
- Presentar los resultados del protocolo de validación ejecutado sobre esa instrumentación (AG-01 a AG-10).
- Reportar las métricas reales obtenidas durante la ejecución.
- Dejar constancia explícita de las limitaciones encontradas.
- Servir como evidencia técnica entregable de forma independiente ante un asesor, un jurado o un equipo de desarrollo.

## 3. Alcance

**Este documento cubre:**
- Qué existía antes de la instrumentación (auditoría) y qué se implementó.
- La arquitectura de la instrumentación (dos niveles) y los archivos/componentes reales involucrados.
- El resumen del protocolo AG-01 a AG-10, con sus métricas y evidencia.
- Limitaciones y buenas prácticas aplicadas durante la implementación.

**Este documento NO cubre** (y refiere al documento correspondiente en su lugar):

| Tema | Documento donde se trata |
|---|---|
| Procedimiento detallado paso a paso de cada caso AG-01…AG-10 | `FASE5B-evidencia-AG01-AG10.md` |
| Análisis interpretativo de qué demuestran los hallazgos respecto a la hipótesis de tesis | `FASE6-analisis-conclusiones.md` |
| Diseño completo de la arquitectura del runtime, principios P1–P17, RFC-0001 a RFC-0010 | Documentación de arquitectura del proyecto (`docs/architecture/`) |
| Decisión de por qué la observabilidad se define como derivación de la historia y no como instrumentación | `RFC-0007-observabilidad.md` |

## 4. Arquitectura de Observabilidad

El punto de partida no fue "cómo integrar LangSmith", sino verificar si LangSmith **podía** integrarse sin contradecir una decisión arquitectónica ya aceptada. RFC-0007 (Observabilidad, aceptado 2026-07-10) establece como decisión irreversible:

> "Toda observabilidad es derivación de la historia (Domain Events + checkpoints): el runtime no se instrumenta — se lee. Los observadores jamás escriben."

Y rechaza explícitamente la instrumentación externa genérica como fuente de evidencia científica, admitiéndola únicamente como **telemetría operativa**, separada del plano de evidencia. Esta distinción gobierna todo el diseño de este documento: LangSmith nunca reemplaza al mecanismo propio de trazabilidad (`consultar_traza`/`consultar_replay`); actúa como una segunda lente, complementaria e independiente, usada para visualización de desarrollo y demostración.

**Figura 4.1. Arquitectura de observabilidad de dos fuentes**

```text
Hecho del estudiante
        │
        ▼
Runtime (LangGraph) ── Diagnosticar / Remediar / Orientar / Deliberar / Decidir / Adaptar
        │
        ▼
Traza Persistida (RFC-0007 §2.1 — consultar_traza / consultar_replay)
        │                                    ← FUENTE OFICIAL DE EVIDENCIA
        ├──────────────► LangSmith (telemetría operativa)
        │                                    ← visualización de desarrollo/demo, nunca evidencia
        ▼
Servicios que leen la decisión (nunca la toman):
  Módulo Adaptativo · Tutor IA · Memoria compartida del swarm de contenido
```
*Fuente: Elaboración propia, a partir de RFC-0007 §1, §5 y del código real de `runtime/boundary/`.*

**Análisis:** el diagrama muestra que existen dos observadores de la misma ejecución (la traza persistida y LangSmith), pero solo uno de ellos es la fuente de evidencia oficial. Esto es importante porque evita que un lector interprete las capturas de LangSmith de este documento como "la prueba" de que el sistema funciona — la prueba formal es la historia reconstruible del runtime; LangSmith solo la hace visualmente accesible durante el desarrollo y la demostración. Esta separación es, en sí misma, la respuesta a la pregunta más probable de un jurado sobre por qué se usó una herramienta externa sin comprometer el rigor científico del proyecto.

**Figura 4.2. Flujo de una sesión real, de extremo a extremo**

```text
POST /api/students/.../hecho (o llamada directa al Boundary)
        │
        ▼
runtime/boundary/inbound/hechos.py::registrar_hecho
        │
        ▼
runtime/engine/graph/walkthrough.py  (StateGraph de LangGraph, 10 nodos)
        │
        ├─ aplicar → diagnosticar → aplicar → remediar → aplicar → orientar
        │      → aplicar → deliberar → aplicar → decidir → aplicar → adaptar → aplicar
        │
        ▼
Checkpoint + Domain Events persistidos (RFC-0008 / RFC-0007)
```
*Fuente: Elaboración propia, verificado con ejecución real (ver §8, AG-01/AG-08).*

**Análisis:** este flujo no es teórico — es exactamente la secuencia observada durante la ejecución real registrada en la sección 8 de este documento (7 transiciones reales). Cada `aplicar` representa el retorno de un productor al Kernel para persistir su resultado antes de continuar; esa es la razón por la que `aplicar` aparece varias veces en la traza y en LangSmith (seven veces en la sesión analizada, ver Tabla 9.2).

## 5. Componentes instrumentados

Antes de instrumentar, se auditó exhaustivamente el estado real del código (no se asumió nada). Los hallazgos relevantes:

**Tabla 5.1. Estado de LangSmith antes de este trabajo**

| Verificación | Resultado |
|---|---|
| ¿Import de `langsmith` en código propio? | No encontrado (0 resultados en `backend/app/` y `backend/runtime/`) |
| ¿Variables de entorno `LANGSMITH_*`/`LANGCHAIN_*`? | No existían en `.env.example` |
| ¿Dependencia declarada? | Sí, transitiva (`langsmith==0.8.4` en `requirements.txt`, nunca importada) |
| ¿LangGraph real en el runtime? | Sí — `StateGraph` real en `runtime/engine/graph/walkthrough.py`, 10 nodos |

**Figura 5.1. Los tres wrappers de OpenAI identificados en el sistema**

```text
1. OpenAIProvider          → runtime/domain/shared/llm_openai.py
                              usado por: Diagnosticar, Remediar, Orientar (LLM real en produccion)

2. LLMService              → app/llm/service.py
                              usado por: module_orchestration_service.py (generacion de contenido)

3. AIService                → app/services/ai_service.py
                              usado por: Tutor IA (chat)
```
*Fuente: Elaboración propia, verificado leyendo cada archivo.*

**Análisis:** este hallazgo es relevante porque una instrumentación ingenua ("agregar LangSmith al cliente de OpenAI") habría cubierto solo uno de los tres wrappers, dejando sin observar dos terceras partes de las llamadas reales a modelos de lenguaje del sistema. La instrumentación de este proyecto cubre los tres, de forma diferenciada (§6).

**Figura 5.2. Los tres subsistemas de "memoria"/"enjambre" distinguidos**

```text
RFC-0006 (Consenso)         → runtime/kernel/deliberation/     → decisiones pedagogicas del estudiante
RFC-0005 (Memoria)           → consultar_memoria (Boundary)     → modelo consolidado del estudiante
SharedMemoryStore (swarm)    → app/memory/shared_memory.py      → continuidad narrativa del contenido
```
*Fuente: Elaboración propia.*

**Análisis:** confundir estos tres subsistemas —algo fácil de hacer por el vocabulario compartido ("memoria", "enjambre")— habría llevado a atribuir evidencia del subsistema equivocado. Este documento y su protocolo de pruebas (§8, caso AG-07) mantienen la distinción explícita en todo momento.

## 6. Estrategia de instrumentación

Se adoptó un diseño de **dos niveles**, deliberadamente asimétrico, porque cada nivel resuelve una restricción distinta.

**Figura 6.1. Diseño de instrumentación en dos niveles**

```text
NIVEL 1 — Exportador de solo lectura (cero cambios en runtime/)
  app/telemetry/langsmith_exporter.py
  Lee: consultar_traza / consultar_replay (RFC-0007 §2.1, ya existentes)
  Proyecta la secuencia de transiciones ya persistida hacia spans de LangSmith.

NIVEL 2 — Hook operativo mínimo (un solo punto dentro de runtime/)
  runtime/domain/shared/llm_openai.py :: OpenAIProvider.generar()
  Captura: modelo, tokens, latencia_ms — datos que RFC-0007 excluye a
  propósito del registro cientifico por depender del reloj de pared.
  Mecanismo: un punto de extension inyectable (Callable), sin que
  runtime/ importe nunca nada de app/.
```
*Fuente: Elaboración propia.*

**Análisis:** el Nivel 1 no necesitó tocar ningún archivo dentro de `runtime/` — es, literalmente, "leer la historia", el patrón que RFC-0007 exige. El Nivel 2 sí modifica un archivo de `runtime/`, pero de forma mínima (una función, un punto de extensión) y justificada explícitamente por la propia alternativa que RFC-0007 admite (telemetría operativa de latencia/tokens). Esta separación permite responder con precisión, ante cualquier pregunta, exactamente qué se tocó y por qué.

Fuera de `runtime/` —donde no aplica ninguna restricción de RFC-0007— se añadieron hooks equivalentes en los tres wrappers de OpenAI restantes:

**Tabla 6.1. Puntos de instrumentación por componente**

| Componente | Archivo | Span generado | Nivel |
|---|---|---|---|
| Diagnosticar/Remediar/Orientar (LLM real) | `runtime/domain/shared/llm_openai.py` | `llm:gpt-4o-mini` | 2 (dentro de runtime/) |
| Tutor IA | `app/services/ai_service.py` | `tutor.chat` | Fuera de runtime/ |
| Orquestación de módulo | `app/services/module_orchestration_service.py` | `modulo.orquestacion` | Fuera de runtime/ |
| Memoria compartida del swarm de contenido | `app/memory/narrative_continuity.py` | `memoria.publish` / `memoria.query` | Fuera de runtime/ |
| Secuencia de nodos del grafo | *(automático)* | `aplicar`, `diagnosticar`, `deliberar`, `decidir`, `adaptar`, etc. | Auto-tracing nativo de LangGraph |

**Hallazgo relevante durante la implementación:** se descubrió que LangGraph, al detectar `LANGSMITH_TRACING=true` en el entorno, **traza automáticamente la ejecución de sus propios nodos** (vía su integración nativa con `langchain-core`), sin necesidad de código adicional. Esto significa que la estructura del grafo (qué nodo ejecutó, en qué orden) se obtiene sin instrumentación propia; el trabajo de instrumentación de este proyecto se concentró en lo que el auto-tracing nativo **no** cubre: latencia/tokens de las llamadas LLM, y los tres servicios que operan fuera del grafo.

## 7. Integración con LangSmith

**Tabla 7.1. Variables de entorno (patrón: comentadas por defecto, siguiendo la convención ya usada por el proyecto para `OPENAI_API_KEY`/`TAVILY_API_KEY`)**

| Variable | Propósito |
|---|---|
| `LANGSMITH_API_KEY` | Clave de autenticación con la API de LangSmith |
| `LANGSMITH_TRACING` | Interruptor único: si no es `"true"`, ningún módulo de `app/telemetry/` importa `langsmith` ni hace red |
| `LANGSMITH_PROJECT` | Nombre del proyecto en LangSmith (usado: `UPAO-MAS-EDU`) |
| `LANGSMITH_ENDPOINT` | Endpoint de la API (opcional, por defecto `https://api.smith.langchain.com`) |

**Figura 7.1. Estructura del paquete de telemetría**

```text
backend/app/telemetry/
├── __init__.py
├── config.py                 (lee las variables de entorno, expone HABILITADO)
├── spans_operativos.py       (unico modulo que importa el SDK de langsmith)
├── langsmith_exporter.py     (Nivel 1: exportador de solo lectura)
└── bootstrap.py              (cablea el hook al arrancar la aplicacion)
```
*Fuente: Elaboración propia.*

**Análisis:** toda la lógica que depende del SDK de `langsmith` vive en un único paquete, fuera de `runtime/`. Esto permite, si en el futuro se decide cambiar de herramienta (por ejemplo a OpenTelemetry), reemplazar este paquete sin tocar el resto del sistema — el punto de extensión en `runtime/` es agnóstico a qué observador esté conectado.

Se corrigió, durante la implementación, un defecto real preexistente: la configuración de la aplicación (`Settings`, basada en `pydantic-settings`) rechazaba cualquier variable de entorno no declarada explícitamente. Al añadir las variables `LANGSMITH_*` al archivo `.env`, la aplicación completa dejaba de arrancar. Se corrigió declarando las cuatro variables en `app/core/config.py` antes de continuar con cualquier prueba.

## 8. Casos de prueba ejecutados

El detalle procedimental completo (objetivo, precondiciones, procedimiento paso a paso) de cada uno de los diez casos vive en `FASE5B-evidencia-AG01-AG10.md`. Esta sección resume su propósito y resultado.

**Tabla 8.1. Resumen del protocolo AG-01 a AG-10**

| ID | Qué valida | Resultado |
|---|---|---|
| AG-01 | Apertura de sesión y primera transición | PASE |
| AG-02 | Diagnosticar con LLM real (hook de latencia/tokens) | PASE |
| AG-03 | Deliberación real ante tensión bloqueante | PASE |
| AG-04 | Derivación de decisión desde deliberación resuelta | PASE |
| AG-05 | Runtime → Módulo Adaptativo (frontera de lectura) | PASE |
| AG-06 | Runtime → Tutor IA (correlación por `student_id`) | PASE |
| AG-07 | Memoria compartida del swarm de contenido | PASE |
| AG-08 | Sesión de extremo a extremo | PASE |
| AG-09 | Resiliencia ante fallo real del proveedor LLM | PASE |
| AG-10 | Validación cruzada Runtime ↔ LangSmith | PASE |

Los diez casos se ejecutaron con datos reales: Postgres local, OpenAI real, Tavily real y LangSmith real — ningún mock de dominio, ninguna respuesta simulada.

## 9. Métricas observadas

Esta sección reporta únicamente valores reales, obtenidos directamente de la API de LangSmith y de la traza persistida del runtime durante la ejecución de la sesión de validación (`session_id=s-ag-suite-1784604654`, `student_id=ag-suite-1784604654`). Ninguna cifra fue estimada ni inventada; donde una métrica no aplica o no se midió, se indica explícitamente.

**Tabla 9.1. Métricas de ejecución del protocolo completo**

| Métrica | Valor | Fuente |
|---|---:|---|
| Casos ejecutados | 10 | Protocolo AG-01–AG-10 |
| Casos con resultado PASE | 10 | Protocolo AG-01–AG-10 |
| Regresiones detectadas en la suite existente | 0 | 254+ tests re-ejecutados |
| Transiciones reales en la sesión analizada | 7 | `consultar_traza` |
| Ocurrencias del nodo `aplicar` en LangSmith | 7 | API LangSmith (`list_runs`) |
| Coincidencia Runtime ↔ LangSmith (AG-10) | 100 % (7/7) | Comparación directa |
| Llamadas LLM reales instrumentadas en la sesión | 3 (`diagnosticar`, `remediar`, `orientar`) | Span `llm:gpt-4o-mini` |
| Spans huérfanos detectados | 0 | Todos los nodos nativos comparten el mismo run raíz; los spans propios comparten tag `session:<id>` |

**Tabla 9.2. Latencia y tokens por llamada LLM real (misma sesión, valores exactos consultados vía API de LangSmith)**

| Nodo | Latencia (ms) | Tokens (prompt / completion / total) |
|---|---:|---|
| Diagnosticar | 2 362.62 | 145 / 87 / 232 |
| Remediar | 1 346.21 | 114 / 80 / 194 |
| Orientar | 5 020.12 | 163 / 143 / 306 |

**Tabla 9.3. Latencia de servicios fuera del grafo (misma sesión)**

| Servicio | Latencia observada |
|---|---:|
| Tutor IA (`tutor.chat`) | evento real capturado, sin cifra fija reportable como promedio (n=1 en esta sesión) |
| Orquestación de módulo (`modulo.orquestacion`) | 9 320.85 ms (incluye investigación real vía Tavily + 3 llamadas LLM concurrentes) |
| Memoria — publish/query | < 300 ms cada una |

**Nota explícita sobre métricas no disponibles:** este documento no reporta latencia agregada/promedio sobre múltiples sesiones (solo se ejecutó una sesión de validación formal, ver §12 Limitaciones), ni throughput bajo carga, ni consumo de memoria/CPU del proceso — ninguna de estas métricas fue medida y no se estiman aquí.

## 10. Evidencia visual

Los diagramas de arquitectura (Figuras 4.1, 4.2, 5.1, 5.2, 6.1, 7.1) ya presentados en este documento son reales y no requieren captura adicional — describen estructura de código y flujo verificados directamente. Las figuras siguientes corresponden a **capturas de pantalla del panel web de LangSmith**, que no se tomaron durante la elaboración de este documento (requieren iniciar sesión con la cuenta del proyecto, algo que el asistente que redactó este documento no realiza bajo ninguna circunstancia). Cada una se deja marcada explícitamente, acompañada de los datos reales exactos que la captura mostrará y el análisis correspondiente, listo para completarse en cuanto se inserte la imagen.

---

**Figura 10.1. Árbol completo de la sesión de validación en LangSmith**

`[Insertar captura: LangSmith → proyecto "UPAO-MAS-EDU" → run raíz de la sesión de validación (id 019f82ba-016e-79f1-bc1f-8e525b3cb874) → vista de árbol expandida]`

*Fuente: Elaboración propia.*

**Datos reales que la captura debe mostrar:** un run raíz `LangGraph`, con 13 hijos directos (7× `aplicar`, y una vez cada uno de `diagnosticar`, `remediar`, `orientar`, `deliberar`, `decidir`, `adaptar`), más 3 llamadas `llm:gpt-4o-mini` anidadas bajo `diagnosticar`/`remediar`/`orientar` respectivamente.

**Análisis:** esta figura es la evidencia visual central del documento. Muestra, de un solo vistazo, que la ejecución no es una cadena lineal de llamadas a un modelo de lenguaje, sino un árbol con ramificaciones que corresponden exactamente a las capacidades del dominio (diagnóstico, remediación, orientación, deliberación, decisión, adaptación). Demuestra la estructura multiagente de forma inmediatamente legible para alguien que no conoce el código.

---

**Figura 10.2. Detalle del nodo `diagnosticar`**

`[Insertar captura: expandir el nodo "diagnosticar" en el árbol de la Figura 10.1, mostrando su span hijo llm:gpt-4o-mini]`

*Fuente: Elaboración propia.*

**Datos reales:** el nodo `diagnosticar` contiene un span `llm:gpt-4o-mini` con `finish_reason="stop"` y un conteo real de tokens (ver Tabla 9.2).

**Análisis:** confirma que Diagnosticar, para esta sesión, usó efectivamente la ruta LLM (no la regla determinista) — visible directamente en la jerarquía del span, sin necesidad de inspeccionar código.

---

**Figura 10.3. Nodo `deliberar` y nodo `decidir`**

`[Insertar captura: nodos "deliberar" y "decidir" consecutivos en el árbol, entre "orientar" y "adaptar"]`

*Fuente: Elaboración propia.*

**Datos reales:** en la traza persistida, la transición 5 registra `EntradaSupersedida` + `DeliberacionRegistrada`, y la transición 6 registra `DecisionRegistrada` — la posición de estos dos nodos en LangSmith debe corresponder exactamente a ese orden.

**Análisis:** esta es la evidencia visual del consenso multiagente: dos nodos consecutivos, ubicados justo después de que Remediar y Orientar propusieran acciones opuestas, y justo antes de que Adaptar actuara — la secuencia visual confirma que la decisión fue *derivada* del consenso, no tomada de forma independiente por ninguna capacidad.

---

**Figura 10.4. Span `llm:gpt-4o-mini` — detalle de metadata**

`[Insertar captura: panel de detalle de cualquiera de los tres spans llm:gpt-4o-mini, mostrando inputs/outputs/metadata]`

*Fuente: Elaboración propia.*

**Datos reales que debe mostrar:** campo `modelo="gpt-4o-mini"`, `usage` con `prompt_tokens`/`completion_tokens`/`total_tokens`, `finish_reason`, y `latencia_ms` en la metadata extra.

**Análisis:** demuestra que el hook operativo captura exactamente los campos que ya existían en `LLMResponse` (el propio código del runtime los reserva desde antes para "observabilidad futura") — no se inventó ningún dato nuevo, solo se conectó un canal de salida para datos que el sistema ya calculaba.

---

**Figura 10.5. Span `tutor.chat`**

`[Insertar captura: span "tutor.chat" (aparece como raíz independiente, no anidado bajo el árbol del grafo), con tag "session:ag-suite-1784604654" visible]`

*Fuente: Elaboración propia.*

**Análisis:** el hecho de que este span sea una raíz independiente —y no un hijo del árbol de LangGraph— es evidencia visual directa de un hallazgo arquitectónico ya documentado: el Tutor IA no es un nodo del grafo, es un servicio externo que consulta la decisión ya tomada. El tag de sesión compartido demuestra que, aun siendo independiente, es correlacionable con la misma sesión del estudiante.

---

**Figura 10.6. Span `modulo.orquestacion`**

`[Insertar captura: span "modulo.orquestacion" con su metadata expandida: bloom_target, bloom_target_desde_runtime, latencia_ms]`

*Fuente: Elaboración propia.*

**Datos reales:** `bloom_target=3`, `bloom_target_desde_runtime=true`, `latencia_ms≈9320.85`.

**Análisis:** el campo `bloom_target_desde_runtime=true` es la evidencia visual de que el servicio de contenido leyó un valor decidido por el runtime, no uno calculado por sí mismo — sustenta directamente el hallazgo de frontera arquitectónica (RFC-0002) reportado en la Fase 6.

---

**Figura 10.7. Spans `memoria.publish` y `memoria.query`**

`[Insertar captura: ambos spans, mostrando su tag compartido "session:ag-suite-1784604654" y sus metadatos student_id/module_id]`

*Fuente: Elaboración propia.*

**Análisis:** confirma que la escritura y la lectura posterior de memoria narrativa quedan correlacionadas por estudiante y módulo — y, como se aclara en el texto de esta figura y en la Fig. 5.2, este subsistema pertenece al swarm de generación de contenido, no al consenso RFC-0006.

---

**Figura 10.8. Span con error real — `AuthenticationError` (AG-09)**

`[Insertar captura: el span llm:gpt-4o-mini de la prueba de resiliencia, con el campo "error" expandido mostrando el AuthenticationError 401 completo]`

*Fuente: Elaboración propia.*

**Datos reales:** `error: RuntimeError("AuthenticationError(\"Error code: 401 ...\")")`, con traceback completo capturado automáticamente por el decorador de trazado.

**Análisis:** esta es la evidencia visual de que la telemetría **no oculta fallos reales** — el error aparece explícitamente marcado en rojo/error en la interfaz, en vez de aparecer como un span exitoso vacío. Es la contraparte directa de la Figura 10.9.

---

**Figura 10.9. Recuperación posterior al fallo (AG-09)**

`[Insertar captura: el span llm:gpt-4o-mini INMEDIATAMENTE posterior al de la Figura 10.8, mostrando error=None y una respuesta exitosa]`

*Fuente: Elaboración propia.*

**Análisis:** muestra que, tras el fallo forzado, una llamada nueva y correctamente configurada se ejecuta con normalidad — el estado del proveedor no quedó corrupto por el intento fallido.

---

**Figura 10.10. Comparación lado a lado: traza persistida (`/api/runtime/sessions/{id}/traza`) vs. árbol de LangSmith**

`[Insertar dos capturas contiguas: (izquierda) respuesta JSON del endpoint /traza para la sesión de validación; (derecha) el árbol de la Figura 10.1]`

*Fuente: Elaboración propia.*

**Análisis:** esta es la figura de cierre del documento — la validación cruzada (AG-10) hecha visualmente explícita. El lector puede contar, en ambas capturas, exactamente 7 eventos de tipo transición/nodo `aplicar`, confirmando sin ambigüedad que ambas fuentes describen la misma ejecución.

## 11. Resultados obtenidos

- La instrumentación de dos niveles descrita en §6 se implementó completamente y se verificó en ejecución real, sin necesidad de modificar la lógica de negocio del runtime ni de los servicios externos a él.
- Los diez casos del protocolo de validación (§8) obtuvieron resultado PASE, con evidencia real en cada uno (ver detalle en `FASE5B-evidencia-AG01-AG10.md`).
- La validación cruzada (AG-10) confirmó una coincidencia exacta (7/7) entre la traza persistida del runtime y la representación observada en LangSmith para la sesión analizada.
- No se detectaron regresiones en la suite de pruebas preexistente del proyecto (254+ tests) tras la instrumentación.
- Se identificó y corrigió un defecto real preexistente en la validación de configuración de la aplicación (§7).

## 12. Limitaciones

- La validación se ejecutó en un entorno local (Docker Compose + entorno virtual de Python), aislado del despliegue de producción/demo — no se validó bajo las condiciones exactas de red y carga de producción.
- LangSmith envía los spans de forma asíncrona por lotes; en procesos de vida muy corta puede existir un retraso — o pérdida, si el proceso termina antes del envío — antes de que un span sea visible. Este comportamiento se investigó hasta su causa raíz (no se asumió; se demostró con una llamada explícita de vaciado del cliente) y no afecta a la traza persistida del runtime, que sigue siendo la fuente oficial de evidencia.
- De las ocho capacidades del dominio, solo tres (Diagnosticar, Remediar, Orientar) tienen hoy un proveedor LLM real conectado en producción; las cinco restantes corren en su versión de regla determinista salvo en pruebas. El span `llm:gpt-4o-mini` de este documento cubre, por tanto, esas tres capacidades — no es una limitación de la instrumentación, sino un hecho arquitectónico preexistente que conviene tener presente al interpretar la cobertura del trazado LLM.
- La validación cruzada (§8, AG-10) se realizó sobre una única sesión sintética de prueba, no sobre una muestra de estudiantes reales ni de forma repetida; la coincidencia 1:1 reportada es representativa del mecanismo, no una medición estadística sobre múltiples ejecuciones.
- Este documento no incluye capturas de pantalla ya insertadas del panel web de LangSmith (ver §10) — quedan marcadas explícitamente para su inserción por quien tenga acceso a la cuenta del proyecto.

## 13. Buenas prácticas implementadas

- **Ninguna credencial fue introducida por quien implementó y validó esta instrumentación.** La clave de LangSmith fue creada y configurada directamente por el responsable del proyecto en su archivo de entorno local.
- **Ningún concepto arquitectónico nuevo se introdujo sin verificar su respaldo explícito** en la documentación de arquitectura ya aceptada (RFC-0007) antes de escribir una sola línea de código.
- **La dependencia entre capas se mantuvo en un solo sentido**: el runtime nunca importa código de la capa de aplicación; el único punto de extensión dentro de `runtime/` es un mecanismo de inyección, no un acoplamiento directo.
- **Todo hallazgo inesperado durante la validación se investigó hasta su causa raíz** antes de reportarlo, incluyendo un caso en que el comportamiento observado inicialmente parecía un defecto y resultó ser una condición de carrera conocida y documentada del envío asíncrono por lotes.
- **Ninguna prueba usó datos simulados**: las diez pruebas del protocolo se ejecutaron contra Postgres real, OpenAI real, Tavily real y LangSmith real.
- **Toda la suite de pruebas preexistente se re-ejecutó** tras cada cambio relevante, antes de dar por cerrada la instrumentación.

## 14. Conclusiones

La instrumentación de LangSmith se incorporó al proyecto sin alterar ninguna decisión arquitectónica previa, gracias a que se identificó — antes de escribir código — que RFC-0007 ya definía explícitamente el espacio en el que una herramienta externa de este tipo puede operar: como telemetría operativa, nunca como fuente de evidencia. El diseño resultante (exportador de solo lectura + hook operativo mínimo) cubre tanto la estructura de ejecución del grafo (mediante el auto-trazado nativo de LangGraph) como los aspectos que la propia arquitectura excluye deliberadamente de su registro científico (latencia y tokens).

La validación formal de esa instrumentación, ejecutada sobre diez casos con evidencia real, confirmó que el mecanismo funciona correctamente, que no introduce regresiones en el sistema existente, y que sus resultados son consistentes —de forma verificable, no solo declarada— con la fuente oficial de evidencia de la arquitectura. Esa consistencia, documentada en el caso AG-10, es el resultado más relevante de este trabajo: dos observaciones independientes de la misma ejecución llegan a la misma conclusión.

## 15. Referencias

- RFC-0007 — Observabilidad. `docs/architecture/RFC-0007-observabilidad.md`.
- RFC-0001 — Arquitectura general del runtime (capas Kernel/Boundary). `docs/architecture/`.
- RFC-0002 — Frontera de responsabilidades entre capacidades del dominio. `docs/architecture/`.
- RFC-0006 — Consenso e Inteligencia de Enjambre. `docs/architecture/RFC-0006-consenso-enjambre.md`.
- Fase 5B — Evidencia formal AG-01 a AG-10. `docs/architecture/FASE5B-evidencia-AG01-AG10.md`.
- Fase 6 — Análisis y Conclusiones: Validación de la Arquitectura Multiagente. `docs/architecture/FASE6-analisis-conclusiones.md`.
- Documentación oficial del SDK de LangSmith (`langsmith` 0.8.4), consultada directamente en el código fuente instalado del paquete para verificar nombres de variables de entorno y firmas de funciones utilizadas.
