# ROADMAP — RFC-0006 (Consenso e Inteligencia de Enjambre)

> Documento de planificación, no de arquitectura. No introduce ni
> propone ningún concepto nuevo — cada pieza cita la sección exacta de
> RFC-0006 o CONCEPT-0002 que la respalda. **No implementar nada de
> este documento sin aprobación explícita, parte por parte.**

- **Fecha:** 2026-07-12
- **Propietario:** RFC-0006 (gobernado por CONCEPT-0001 §E1-E6,
  CONCEPT-0002, P5/P7/P8/P12/P15)
- **Motivo:** RFC-0006 es, con diferencia, la pieza de diseño más
  grande que queda sin implementar. Implementarla "abriendo el RFC y
  escribiendo" (el método usado hasta ahora) arriesga repetir el
  patrón que llevó a la migración de BaseAgent a durar más de lo
  necesario: mucho código sin mapa. Este documento es ese mapa.

---

## 0. Auditoría — qué existe hoy contra qué exige el RFC

`kernel/deliberation/mecanica.py` es la **única** implementación real
de RFC-0006 — `politica-v1`, deliberadamente minimal (ver su propio
docstring). Auditoría línea por línea contra el RFC:

| Exigencia del RFC | Estado real |
|---|---|
| Confianza efectiva `ce` (§1, A1-A8) | **No existe.** Todo el código usa `claim.confianza` (la declarada), nunca una proyección. |
| Campo `asunto` (§2) | ✅ Ya existe en `ClaimEntry` (RFC-0003 rev. 5). |
| Detección de tensión D1 (interpretación) | **No existe.** `tension_bloqueante()` solo mira claims `TipoClaim.PROPUESTA` — una tensión D1 (dos interpretaciones vigentes incompatibles) nunca se detecta ni se convoca hoy. |
| Insuficiencia D3 / umbral θ | **No existe.** No hay ningún umbral; una decisión se deriva en cuanto existe UNA propuesta, sin comprobar que su confianza baste. |
| Resolución D1 vs D2 distinta | **No existe.** `convocar()` aplica siempre la misma regla (`mayor-confianza-declarada`), sin distinguir tipo. |
| Umbral de discriminación δ / margen | **No existe.** Nunca se compara un margen contra nada; siempre hay ganador. |
| Aplazamiento (`Aplazada`) | Tipo de dato existe (`kernel/state/entries.py`); **nunca se produce**. |
| Decisión provisional | **No existe** ningún concepto de "urgencia". `estado.ejecucion` (el campo del que RFC-0006 §4 dice que se deriva "urgente") **está vacío en todo el código base** — ningún escritor, ningún lector, en ningún módulo. Es un campo fantasma. |
| Escalada orgánica (política + reconvocatoria) | Tipo de dato existe (`Escalada`); **nunca se produce**. Toda escalada usada hasta ahora (Plataforma Operativa 4) fue sembrada a mano contra los reducers — explícitamente fuera de alcance de esa épica. |
| Regla de la raíz / orden multi-tensión (§5, H7) | **No existe.** `tension_bloqueante()` devuelve como mucho UNA tensión (la primera por orden alfabético de asunto); nunca hay más de una deliberación pendiente de convocar a la vez. |
| Política versionada (parámetros) | **No existe mecanismo.** `identidad.version_politica` es un string que viaja pero nada lo lee para resolver parámetros — es un campo decorativo hoy. |

**Conclusión de la auditoría:** RFC-0006 no está "parcialmente
implementado" — está **implementado en su forma (los tipos, la
validación estructural de los reducers) pero no en su mecánica**. Todo
lo que seleccioné como "ya existe" en épicas anteriores (HITL,
Boundary) fue construido *alrededor* de este vacío, nunca dentro de
él — y eso fue la decisión correcta en su momento (evitó bloquear HITL
esperando esto). Ahora sí toca llenarlo.

---

## 1. Riesgo transversal — el que ninguna de las partes resuelve por sí sola

**Replay de sesiones ya persistidas.** `politica-v1` ya tiene sesiones
reales en Postgres (las que se usaron para validar Observabilidad,
Replay y HITL a lo largo de esta conversación). A3 (determinismo) y
P12 exigen que el replay de esas sesiones reproduzca *exactamente* lo
que ya ocurrió — con la regla `mayor-confianza-declarada`, sin
umbrales, sin ce. **Ninguna parte de este roadmap puede modificar
`politica-v1` en el sitio.** Cada pieza nueva es una **política nueva,
versionada** (`politica-v2` o superior) que convive con `politica-v1`;
`identidad.version_politica` ya es el mecanismo de selección (RFC-0003
INV-1) — hoy simplemente nadie lo consulta. Esto no es una parte más:
es una restricción de diseño que las Partes 0 y D deben resolver
explícitamente antes de que exista una segunda política.

---

## 2. Las partes — dependencias reales, dificultad, riesgo

Los nombres de parte citan la sección de RFC-0006/CONCEPT-0002 que
implementan — ninguno es un nombre inventado para este roadmap.

### Parte 0 — Dónde vive la política versionada (infraestructura)

**Qué hace:** define el mecanismo por el que `version_politica` deja
de ser decorativo: un módulo/tabla de configuración versionada que
`mecanica.py` puede consultar para obtener pesos, curvas, θ, δ, N de
reconvocatoria y asuntos reservados al docente — "ningún número mágico
en el Kernel" (RFC-0006, Consecuencias).

**Depende de:** nada — es la base de todas las demás.
**De qué depende:** Partes A, C, D, F, G la necesitan para leer sus
parámetros.
**Dificultad:** Media. **Riesgo:** Alto — es la única parte que decide
una forma de implementación no especificada por el RFC (delegada a
"la política", sin mecanismo concreto). Candidata real a **Engineering
Review / mini-ADR** antes de escribir código (Engineering Gate,
pregunta 4: "¿requiere modificar/ampliar un RFC/ADR?" — aquí
probablemente sí, un ADR nuevo, no una enmienda).

### Parte A — Confianza efectiva: el álgebra A1-A8 (§1)

**Qué hace:** `calcular_confianza_efectiva(claim, estado, política) ->
Decimal`, función pura que demuestre los 8 axiomas. Reemplaza el uso
directo de `claim.confianza` en cualquier lugar que necesite comparar
claims.

**Depende de:** Parte 0 (pesos/curvas de refuerzo-decaimiento son
parámetros de política).
**De qué depende:** Partes D, E, F, G — todas comparan `ce`, no
confianza declarada.
**Dificultad:** Alta. **Riesgo:** Alto — es la pieza más delicada del
RFC completo. A5 (monotonicidad) y A6 (decaimiento sin refuerzo) son
fáciles de violar por accidente si el cálculo toca algo fuera de la
cadena causal del claim (violaría A7). Necesita su propia suite de
tests por axioma, uno por uno, contra escenarios reales — no una sola
prueba de humo.

### Parte B — Detección real de tensión D1 y clasificación D1/D2 (§3, CONCEPT-0002 §1)

**Qué hace:** extiende `tension_bloqueante()` para detectar tensiones
entre claims `INTERPRETACION` (D1), no solo `PROPUESTA` (D2); clasifica
cada tensión encontrada como D1 o D2 explícitamente (hoy el código no
distingue ninguna).

**Depende de:** nada nuevo estructuralmente (usa lo que Parte 0/A ya
exponen, pero es lógica de predicado, no de cálculo).
**De qué depende:** Partes D (resolución distinta por tipo) y G (regla
de la raíz necesita saber qué es D1 y qué es D2).
**Dificultad:** Media. **Riesgo:** Medio — el riesgo no es técnico, es
de cobertura: hay que verificar contra las tres tensiones canónicas
que CONCEPT-0002 §1 ya nombra (¿avanzar o reforzar? / ¿qué modalidad? /
¿dominó el objetivo?) para no dejar un cuarto caso sin clasificar.

### Parte C — Umbral θ e insuficiencia D3 (§3)

**Qué hace:** cuando el mejor claim de un slot pendiente no alcanza θ,
NO se convoca deliberación — se enruta hacia la capacidad que puede
producir evidencia (p. ej. Evaluar). Hoy no existe ningún umbral: una
propuesta única siempre deriva decisión.

**Depende de:** Parte 0 (θ es parámetro de política), Parte A (θ se
compara contra `ce`, no confianza declarada).
**De qué depende:** ninguna parte posterior depende de esta
directamente, pero es la que MÁS toca el enrutamiento del grafo
(`enrutar()` en `engine/graph/walkthrough.py`) — cambia una condición
de "¿hay al menos una propuesta?" a "¿hay una propuesta que además
alcanza θ?".
**Dificultad:** Media. **Riesgo:** Medio — blast radius mayor de lo
que parece: toca el mismo archivo que ya causó el bug de
`GraphRecursionError` en la épica de HITL (una guardia mal puesta aquí
puede volver a colgar el grafo).

### Parte D — Resolución D1 vs D2 con margen (§4)

**Qué hace:** reemplaza `mayor-confianza-declarada` con las dos reglas
reales — D1 gana por `ce` si el margen sobre el rival supera δ; D2
pondera `ce × peso de política pedagógica`. Es, literalmente,
`politica-v2`: la primera política real, coexistiendo con `politica-v1`
(ver §1 de este documento).

**Depende de:** Partes 0, A, B, C.
**De qué depende:** Partes E, F (aplazamiento/escalada son lo que pasa
cuando D no puede resolver).
**Dificultad:** Alta. **Riesgo:** Alto — es donde el riesgo transversal
(§1) se materializa: el primer punto donde de verdad existen dos
políticas simultáneas, y donde un bug de selección de versión
correría silenciosamente sobre sesiones reales.

### Parte E — Aplazamiento y Decisión provisional (§4, CONCEPT-0002 §4)

**Qué hace:** cuando el margen no alcanza δ, produce `Aplazada`
declarando qué evidencia falta (ya es un tipo existente, nunca
poblado). Si el slot es "urgente", en cambio resuelve con la mejor
confianza disponible como decisión provisional (INV-12 ya la marca
para validación prioritaria).

**Depende de:** Parte D.
**De qué depende:** Parte F (la escalada por reconvocatoria cuenta
aplazamientos — sin esta parte no hay nada que contar).
**Dificultad:** Media-Alta. **Riesgo:** Alto y **sin resolver en este
documento**: "urgente" es "atributo derivado de `ejecución`" según el
propio RFC — pero `estado.ejecucion` está vacío en todo el código base
hoy (auditado en §0). Antes de implementar esta parte hace falta
decidir, en una Engineering Review propia, qué puebla `ejecucion` y
qué lo convierte en "urgente" — ese vacío pertenece a RFC-0004 §2, no
a RFC-0006, y no está en el alcance de este roadmap resolverlo aquí.
Marcado explícitamente como **bloqueo a levantar antes de esta parte**,
no una tarea de la parte misma.

### Parte F — Escalada orgánica: reserva de política + límite de reconvocatoria (§4)

**Qué hace:** las dos vías reales de escalada — asuntos que la
política reserva al docente (lista de configuración), y una tensión
aplazada/reconvocada N veces sin discriminar (cuenta la cadena de
deliberaciones enlazadas, CONCEPT-0002 §5). Es el motivo original por
el que se abrió esta conversación sobre RFC-0006: hasta esta parte, S2
(`consultar_escaladas_pendientes`) sigue sin tener nada real que
mostrar sin sembrado manual.

**Depende de:** Partes 0, D, E (reconvocatoria cuenta aplazamientos
reales).
**De qué depende:** nada posterior — es el final de la cadena de
resolución.
**Dificultad:** Alta. **Riesgo:** Medio-Alto — contar una cadena de
reconvocatoria correctamente (seguir `enlaza_a` hacia atrás, sin
confundir una cadena larga con N tensiones distintas del mismo asunto)
es fácil de hacer mal de forma sutil; necesita tests contra cadenas de
3+ reconvocatorias, no solo 1.

### Parte G — Regla de la raíz y orden multi-tensión (§5, H7)

**Qué hace:** cuando hay más de una tensión bloqueante a la vez,
ordena D1 antes que las D2 que dependen de ella, luego FIFO por orden
de llegada, luego prioridad pedagógica como desempate. Hoy
`tension_bloqueante()` **nunca ve más de una tensión** — devuelve la
primera y se detiene.

**Depende de:** Parte B (clasificación D1/D2) — es, en los hechos, la
parte que más veces va a tocar `engine/graph/walkthrough.py` (el nodo
`_nodo_deliberar` asume implícitamente una convocatoria a la vez).
**De qué depende:** nada.
**Dificultad:** Alta. **Riesgo:** Alto — mismo motivo que Parte C:
toca el motor de enrutamiento, el archivo con más blast radius de todo
`runtime/engine/`. Es candidata a ser la parte que MÁS tests de
regresión necesita contra todo lo ya construido (HITL, Replay,
Observabilidad ya validados con el enrutamiento actual).

### Parte H — Boundary, HTTP, Frontend (validación, no diseño nuevo)

**Qué hace:** una vez F produce escaladas orgánicas, valida que las
piezas YA CONSTRUIDAS (S2 `consultar_escaladas_pendientes`, E3
`resolver_escalada`, `RuntimeHitlPanel`) siguen funcionando sin
cambios contra datos reales — el diseño de Boundary para HITL ya está
cerrado (RFC-0010 completo). **Explícitamente fuera de alcance:**
cualquier enriquecimiento de explicabilidad (mostrar el margen, el
umbral, por qué se aplazó) — eso es RFC-0007 §2.3 (explicaciones),
la épica siguiente en el orden que ya se acordó, no esta.

**Depende de:** Parte F.
**Dificultad:** Baja. **Riesgo:** Bajo.

### Parte I — E2E: retirar el sembrado manual

**Qué hace:** el criterio de cierre más concreto de todo este roadmap.
`backend/e2e/runtime_completo.py::_sembrar_escalada` y el mismo
patrón en `test_E3_resolver_escalada.py` fueron construidos
explícitamente como sustituto temporal (ver Plataforma Operativa 4,
alcance recortado aprobado). El día que un escenario **orgánico**
(reconvocatoria real, o un asunto reservado por política) reemplaza
ese sembrado — sin tocar reducers a mano — es el día que RFC-0006 está
verdaderamente cerrado, no antes.

**Depende de:** Parte F.
**Dificultad:** Baja. **Riesgo:** Bajo.

---

## 3. Orden propuesto

Las dependencias reales (arriba) ya casi no dejan margen de
paralelismo — es, en la práctica, una cadena:

```
Parte 0 (política versionada — posible mini-ADR)
    ↓
Parte A (confianza efectiva, A1-A8)
    ↓
Parte B (D1 se detecta, D1/D2 se clasifica)
    ↓
Parte C (umbral θ, insuficiencia D3)
    ↓
Parte D (resolución D1/D2 con margen δ — nace politica-v2)
    ↓
Parte E (aplazamiento + provisional) ← BLOQUEADA por "ejecucion" vacío (§0)
    ↓
Parte F (escalada orgánica: reserva + reconvocatoria)
    ↓
Parte G (regla de la raíz, orden multi-tensión) — puede intercambiarse con F,
    │   ambas dependen solo de B/D, no una de la otra
    ↓
Parte H (validación Boundary/Frontend, sin diseño nuevo)
    ↓
Parte I (retirar sembrado manual — criterio de cierre)
```

Única flexibilidad real: **F y G no dependen entre sí** (F depende de
D+E; G depende solo de B), así que su orden es intercambiable — el
resto es estrictamente secuencial. Propongo agrupar F antes de G
porque F es el motivo original de esta conversación (HITL orgánico);
si prefieres cerrar primero el orden determinista (H7, Parte G) y
dejar la escalada real para el final, dímelo y cambio el orden.

**Agrupación en mini-épicas** (para que cada una cierre con su propio
Engineering Gate de 6 puntos, motor→boundary→HTTP→frontend→E2E→commit,
igual que las anteriores — nunca un PR de 10 partes junto):

| Mini-épica | Partes | Resultado observable al cerrar |
|---|---|---|
| RFC-0006/1 — Cimientos | 0 + A | `ce` calculable y testeado contra A1-A8, política versionada con un sitio real donde vivir. Sin cambios de comportamiento visible todavía. |
| RFC-0006/2 — Convocatoria real | B + C | D1 se detecta por primera vez; una propuesta débil ya no deriva decisión sola. |
| RFC-0006/3 — Resolución completa | D + E (tras levantar el bloqueo de `ejecucion`) | `politica-v2` resuelve con margen real; aplazamiento y provisional existen de verdad. |
| RFC-0006/4 — Escalada y orden | F + G | S2 empieza a mostrar escaladas reales sin sembrado manual; H7 verificado. |
| RFC-0006/5 — Cierre | H + I | Validación E2E completa, sembrado manual retirado, RFC-0006 cerrado. |

---

## 4. Fuera de alcance (explícito, para que no se cuele durante la implementación)

- **H8 (métricas del paisaje) y H9 (decision debt inter-sesión):**
  pertenecen a RFC-0007 (Observabilidad avanzada), la épica que sigue
  a esta en el orden acordado — no a RFC-0006.
- **"Aprobación requerida"** (la tercera entrada de HITL, RFC-0009 §2):
  es un gating de política en S1 (`proyectar_entrega`), independiente
  de que exista consenso orgánico o no. Sigue diferida.
- **Reputación de capacidad:** RFC-0006 la registra como "extensión,
  no diseñada aquí, depende de RFC-0005" — no entra en ninguna parte.
- **Cualquier enriquecimiento de UI/explicabilidad** más allá de que
  la Runtime Console siga funcionando: es RFC-0007 §2.3.

---

## 5. Pregunta abierta antes de aprobar

Dos decisiones que este documento deliberadamente NO toma porque son
tuyas:

1. **Parte 0 (dónde vive la política versionada) probablemente exige
   un Engineering Review/mini-ADR propio** antes de tocar código — no
   está especificado por RFC-0006. ¿Lo abro como su propio paso previo
   a RFC-0006/1, o prefieres que proponga una opción concreta dentro
   de esa misma mini-épica?
2. **Parte E está bloqueada** por un vacío real de RFC-0004 §2
   (`estado.ejecucion` nunca poblado — necesario para "urgente"). ¿Lo
   resuelvo como su propia Engineering Review dirigida cuando llegue
   el momento, o prefieres decidir ahora qué debería poblar
   `ejecucion` para no descubrirlo a mitad de RFC-0006/3?

No implemento nada hasta que confirmes el orden de la Parte 3 y
respondas estas dos preguntas.
