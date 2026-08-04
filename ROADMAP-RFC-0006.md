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

### Parte E — Aplazamiento y Decisión provisional (§4, CONCEPT-0002 §4) — CERRADA (ver §8, RFC-0006/4b)

**Qué hace:** cuando el margen no alcanza δ, produce `Aplazada`
declarando qué evidencia falta. Si el slot es "urgente", en cambio
resuelve con la mejor confianza disponible como decisión provisional
(INV-12 ya la marca para validación pendiente).

**Depende de:** Parte D.
**De qué depende:** Parte F (la escalada por reconvocatoria cuenta
aplazamientos — sin esta parte no hay nada que contar).
El bloqueo original ("urgente" derivado de `estado.ejecucion`, campo
muerto) quedó resuelto en §5/2 antes de abrirse: `urgente` es parámetro
externo del Boundary, igual que `politica`.

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
Parte E (aplazamiento + provisional) — CERRADA (RFC-0006/4b, §8)
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
| RFC-0006/1 — Cimientos | 0 + A | `ce` calculable y testeado contra A1-A8, política versionada con un sitio real donde vivir. Sin cambios de comportamiento visible todavía. **CERRADO.** |
| RFC-0006/2 — Detección y clasificación | B | D1 se detecta y clasifica por primera vez (inerte hoy — ningún productor la activa); la tensión D2 real (Remediar/Orientar) se preserva bit a bit. **CERRADO.** |
| RFC-0006/3 — Propuesta única y θ | C | Una propuesta débil sin rival ya no deriva decisión sola — primer camino real de insuficiencia D3, Y corrige un bug real preexistente (INV-6): la rama `dominada=True` dejaba de llegar a Adaptar. **CERRADO.** |
| RFC-0006/4a — Resolución D1/D2 con margen | D | D1 por `ce`, D2 por `ce×peso` — margen δ real. **CERRADO** (solo Parte D; ver §8 — E se desacopló tras resolver que `estado.ejecucion` está muerto). |
| RFC-0006/4b — Aplazamiento y decisión provisional | E | `Aplazada` poblada por primera vez (margen < δ declara la evidencia que falta); decisión provisional bajo urgencia (`urgente` = parámetro externo del Boundary); tensión abierta deja de ser bloqueante (anti-ciclo/anti-bypass). **CERRADO.** |
| RFC-0006/5 — Escalada y orden | F + G | S2 empieza a mostrar escaladas reales sin sembrado manual; H7 verificado. |
| RFC-0006/6 — Cierre | H + I | Validación E2E completa, sembrado manual retirado, RFC-0006 cerrado. |

> **Nota (2026-07-12):** RFC-0006/2 originalmente agrupaba B+C. El
> Engineering Gate reveló que Parte C requiere construir un camino de
> enrutamiento que hoy no existe (blast radius real sobre `enrutar()`,
> precedente `GraphRecursionError`) — se dividió en 2+3, corriendo la
> numeración de las mini-épicas siguientes. Ver §8 (resumen de
> mini-épicas cerradas) para el detalle de ambas.

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

## 5. Decisiones (resueltas 2026-07-12)

1. **Parte 0 — sin ADR propio.** No hay varias alternativas
   arquitectónicas en juego (eso es lo que justificaría un ADR): es la
   implementación de un mecanismo que RFC-0003 (`version_politica`) ya
   previó. Se documenta dentro del propio Engineering Gate de
   RFC-0006/1 — el "Contrato" (punto 3 del Gate) es donde se fija
   concretamente dónde vive la configuración versionada.
2. **Parte E — RESUELTO (2026-07-12, auditoría corta antes de RFC-0006/4a,
   sin documento nuevo — ver §8).** `estado.ejecucion` nunca se usó; su
   propósito original (RFC-0004 §5, interrupción pendiente) ya lo
   resuelve HITL por otro camino (`Escalada`+S2). "Urgencia" (RFC-0006
   §4) es información del Boundary (¿hay estudiante esperando en vivo?),
   no del Kernel — Parte E la recibirá como parámetro externo, igual
   que `politica`, nunca leyendo `estado.ejecucion`. Parte D (RFC-0006/4a)
   no la necesitaba en absoluto y ya está cerrada sin tocar este campo.

## 6. Riesgo, dependencias y tamaño por parte

Para decidir dónde conviene cortar en commits más pequeños dentro de
cada mini-épica — no es documentación adicional, es la señal de dónde
ir con más cuidado.

| Parte | Riesgo | Depende de | Tamaño |
|---|---|---|---|
| 0 — Política versionada | Alto (decide un mecanismo no especificado por el RFC) | — | Medio |
| A — Confianza efectiva (A1-A8) | Alto (la más delicada: violar un axioma sin darse cuenta) | 0 | Alto |
| B — Detección D1 + clasificación | Medio (cobertura, no dificultad técnica) | — | Bajo-Medio |
| C — Umbral θ / insuficiencia D3 | Medio (toca `enrutar()`, mismo archivo del bug de HITL) | 0, A | Bajo |
| D — Resolución D1/D2 con margen δ | Alto (aquí nace `politica-v2`, conviven dos políticas) | 0, A, B, C | Alto |
| E — Aplazamiento + provisional | Muy alto (bloqueado por vacío externo, RFC-0004 §2) | D + Engineering Review previa | Medio |
| F — Escalada orgánica | Medio-Alto (contar cadenas de reconvocatoria correctamente) | 0, D, E | Medio-Alto |
| G — Regla de la raíz / orden | Alto (motor de enrutamiento, máximo blast radius) | B | Medio |
| H — Boundary/Frontend (validación) | Bajo | F | Bajo |
| I — Retirar sembrado manual | Bajo | F | Bajo |

## 7. Estructura fija por mini-épica

Cada mini-épica se recorre siempre por las mismas seis capas — no
porque todas cambien siempre, sino para verificar explícitamente cuáles
sí y cuáles no, en vez de asumirlo:

```
Motor → Boundary → HTTP → Frontend → E2E → Documentación
```

Y se abre con una **ficha de una página** (objetivo, dependencias,
riesgos, criterio de cierre) que sirve de contrato de esa mini-épica —
evita que el alcance crezca a mitad de la implementación. Plantilla:

```
## Ficha — RFC-0006/N: <nombre>

Objetivo:        <una frase — qué capacidad nueva existe al cerrar>
Partes:          <letras de este roadmap>
Dependencias:    <mini-épicas previas que deben estar cerradas>
Riesgos:         <de la tabla §6, más cualquier riesgo específico>
Motor:           <cambia / no cambia — qué archivo>
Boundary:        <cambia / no cambia>
HTTP:            <cambia / no cambia>
Frontend:        <cambia / no cambia>
E2E:             <qué categoría de runtime_completo.py se ve afectada>

No debe cambiar: <lista explícita — todo lo que "ya que estoy aquí"
                 podría tentar a tocar y que está fuera del contrato>

Context Budget:  <archivos que esta mini-épica necesita abrir; no abrir
                 nada fuera de esta lista salvo que el propio Gate lo exija>
                 Si durante el Gate aparece un archivo fuera de esta
                 lista: NO abrirlo — primero justificar por qué hace
                 falta, y solo entonces ampliar el presupuesto.

Criterios de cierre (todos, no "aproximadamente"):
  □ <criterio funcional medible 1>
  □ <criterio funcional medible 2>
  □ politica-v1 sigue produciendo exactamente las mismas decisiones
  □ Ninguna API HTTP cambia (salvo que la ficha lo liste arriba)
  □ Ninguna surface Boundary cambia (salvo que la ficha lo liste arriba)
  □ runtime_completo.py sigue en verde
  □ No aparecen TODO/FIXME nuevos
  □ No baja la cobertura de tests
  □ Todo documento temporal que esta mini-épica haya abierto (CONTRACT-*,
    fichas de Engineering Review previas) está retirado o reducido a una
    referencia de una línea — su conocimiento ya vive en código/tests/RFC
```

## 8. Mini-épicas cerradas (resumen compacto)

Las fichas completas (auditoría paso a paso, Context Budget, criterios
de cierre uno por uno) vivieron aquí durante la implementación de cada
mini-épica — retiradas a este resumen una vez cerradas, siguiendo la
misma regla que ya se aplicó a `CONTRACT-A1-A8.md`: el conocimiento
detallado vive en el código y los tests, no en un documento paralelo
que hay que mantener sincronizado. Lo que sigue es lo que no se puede
reconstruir leyendo solo el código: qué se decidió y por qué.

### RFC-0006/1 — Cimientos (Parte 0 + A) — CERRADO, commit `c1358cc`

`ce` calculable y demostrada contra A1-A8; política versionada con
sitio real (`politica.py`). Sin cambio de comportamiento — `mecanica.py`
no se tocó. 281/281 tests. Detalle: sección "Garantías" del docstring
de módulo de `confianza.py`, docstring de `Politica`,
`tests/runtime/deliberation/{test_parte0_politica,test_A1_A7_confianza_efectiva}.py`.

Hallazgo no obvio: el contrato original de "edad lógica" (A4/A6) violaba
A7 (localidad causal) — un test real lo probó; corregido a anclar por la
última validación DENTRO de la cadena causal del claim, nunca por el
origen del claim ni por `estado.transicion` en bruto.
`CONTRACT-A1-A8.md` (RFC-0006/1A, la Engineering Review previa a esta
parte) está retirado — su contenido vive en el código citado arriba.

### RFC-0006/2 — Detección y clasificación D1/D2 (Parte B) — CERRADO, commit `d769ddf`

`tension_bloqueante()` clasifica D1/D2; `convocar()` sigue resolviendo
ambas igual (resolución por tipo es Parte D). `enrutar()`: 0 líneas
modificadas. 288/288 tests, `runtime_completo.py` 9/9 con el mismo
shape de traza. Detalle: `mecanica.py`,
`tests/runtime/deliberation/test_parteB_deteccion_tension.py`.

Hallazgo no obvio: esta ficha originalmente agrupaba B+C; el Engineering
Gate reveló que C necesitaba un camino de enrutamiento que no existía
— se dividió en 2+3 en vivo (tabla de mini-épicas en §3 ya refleja la
numeración corrida). La tensión D2 (Remediar vs Orientar, ambos sobre
`"siguiente-paso(sesion)"`) es real y está viva en el walkthrough hoy,
no es hipotética — es la superficie de regresión real que RFC-0006/2 y
/3 debían preservar.

### RFC-0006/3 — Propuesta única bajo θ (Parte C), fix de INV-6 — CERRADO, commit `ad3facb`

`Politica.theta` + `derivar_decision_directa()` (D3), cableado real en
`enrutar()`/`_nodo_decidir`. 296/296 tests, `runtime_completo.py` 9/9
mismo shape. Detalle: `mecanica.py`, `walkthrough.py`,
`tests/runtime/walkthrough/test_FIX_remediar_dominada_true_no_hace_loop.py`.

Hallazgo real (bug preexistente de INV-6/RFC-0003, no un hueco nuevo de
RFC-0006): cuando `dominada=True`, Orientar propone sin rival, nunca se
derivaba decisión, y como Adaptar exige una decisión para actuar, nunca
se activaba — un estudiante que respondía bien no llegaba a ninguna
Entrega, en silencio. `runtime_completo.py` nunca lo detectó porque su
fixture siempre fuerza `dominada=False`. `theta_v1=0` es una prueba
matemática vía A1 (`ce >= 0` siempre), no un valor empírico. Efecto
colateral encontrado durante la implementación: 19 archivos de test
tenían `version_politica="politica-v1"`, nunca antes validado —
corregido a `"v1"`, el valor real.

### RFC-0006/4a — Resolución D1/D2 con margen δ (Parte D) — CERRADO

`Politica.delta` + `Politica.pesos_asunto`; `convocar()` resuelve D1 por
`ce` directo y D2 por `ce×peso`, difiere si el margen no alcanza δ (D2
del margen es literalmente el gate; el aplazamiento real es Parte E,
sin construir). 307/307 tests, `runtime_completo.py` 9/9 mismo shape.
`Resuelta.confianza` guarda el `ce` crudo del ganador, nunca el puntaje
ponderado (evita violar el rango [0,1] de INV-7 si un peso > 1 se
registrara algún día). Detalle: `mecanica.py`,
`tests/runtime/deliberation/test_parteD_resolucion_margen.py`.

Antes de escribir código: auditoría corta (no un documento nuevo,
resuelta en el chat) de `estado.ejecucion` — su propósito original
(RFC-0004 §5, tracking de interrupción pendiente) ya lo resuelve HITL
por otro camino (`Escalada` + S2), y "urgencia" (RFC-0006 §4, la Parte
E que falta) es información que solo tiene el Boundary (¿hay un
estudiante esperando en vivo?), no el Kernel — no debería derivarse de
`estado.ejecucion`. Decisión: desacoplar D de E; D no necesita
urgencia en absoluto. E queda pendiente, con esta pregunta ya resuelta
para cuando se abra.

Hallazgo de diseño (no bug): un peso por asunto (`pesos_asunto`)
pondera a TODOS los rivales de ese asunto por igual — matemáticamente
no puede cambiar quién gana entre dos rivales directos (escalar dos
puntajes por la misma constante preserva su orden). Sí cambia si el
margen escalado alcanza δ. Su uso real (desempatar prioridad ENTRE
asuntos distintos) es Parte G (regla de la raíz), no esta pieza.

### RFC-0006/4b — Aplazamiento y decisión provisional (Parte E) — CERRADO

`convocar(estado, politica, urgente)`: margen < δ ya no devuelve
silencio — aplaza (`Aplazada` poblada por primera vez, con declaración
accionable de qué evidencia discriminaría, INV-7) o, si el slot es
urgente, resuelve provisional (`REGLA_PROVISIONAL =
"provisional-por-urgencia"`, mismo estatus de "nombre de regla del
catálogo" que `"decision-humana"`; confianza = `ce` del ganador, "la
mejor confianza disponible"). `urgente` es parámetro externo del
Boundary (§5/2): `PeticionHechoDelMundo.urgente`, y `POST /hechos`
(estudiante en vivo, síncrono) lo fija en `True`; `hechos-docente`
queda en `False`. 304/304 tests (`tests/runtime`), `runtime_completo.py`
9/9 mismo shape. Detalle: `mecanica.py`, `walkthrough.py` (`enrutar`),
`tests/runtime/deliberation/test_parteE_aplazamiento_provisional.py`,
`tests/runtime/walkthrough/test_parteE_walkthrough_aplazamiento.py`.

Hallazgo real (bug latente preexistente, no solo Parte E): `enrutar`
hacía `if estado.deliberaciones: return "decidir"` — con cualquier
deliberación sin decisión derivable (una `Escalada` pendiente sembrada
+ un hecho nuevo del estudiante bastaban HOY) el grafo ciclaba
decidir→aplicar→decidir hasta `GraphRecursionError`. Corregido con la
guardia "misma función que el nodo" (`derivar_decision(estado) is not
None`). Consecuencia obligada: `tension_bloqueante` ahora excluye
asuntos con deliberación abierta (aplazada/escalada sin `enlaza_a`
posterior) — sin esa exclusión, quitar el cortocircuito habría dejado
a la mecánica reconvocar y resolver sola una tensión que espera al
docente (bypass de RFC-0009 §3). La reconvocatoria legítima (con
evidencia nueva, contada para escalar) sigue siendo Parte F.


### RFC-0006/5 — Escalada orgánica (Parte F) — CERRADO, commits `ee98360`+`200c4a5`+`b39cda1`

Las dos vías de RFC-0006 §4 viven en `convocar()`: RESERVA
(`politica.asuntos_reservados` — se escala sin computar resolución, y
la urgencia NO devuelve la autoridad reservada: anti-bypass RFC-0009
§3) y LÍMITE (`politica.limite_reconvocatoria` — la cadena `enlaza_a`
que acumula N `Aplazada` sin discriminar escala; la urgencia sí precede
al límite: "la provisionalidad es para el estudiante"). La
reconvocatoria (CONCEPT-0002 §5) también nació aquí: una tensión
aplazada vuelve a ser bloqueante solo cuando el conjunto de rivales
vigentes difiere de los participantes registrados en su cabeza
(anti-churn: con paisaje idéntico la resolución se reproduciría bit a
bit); la deliberación nueva nace `enlaza_a` la cabeza, jamás
reapertura. Una tensión escalada jamás vuelve a ser bloqueante — solo
el docente (E3) la cierra. 338/338 tests, `runtime_completo.py` 9/9.
Detalle: `mecanica.py` (`_cabezas_abiertas`, `_aplazamientos_en_cadena`),
`tests/runtime/deliberation/test_parteF_escalada_organica.py`,
`tests/runtime/walkthrough/test_parteF_escalada_organica_grafo.py`
(grafo real: S2 recibe la escalada SIN sembrado manual — la deuda
original de esta parte — y la resolución del docente continúa hasta
Adaptar/Entrega en ambas vías).

Hallazgo no obvio (dependencia futura declarada, no pendiente
silencioso): bajo los productores de REGLAS que hoy corren en vivo,
las confianzas son constantes (Diagnosticar 0.78 para toda
interpretación, Remediar 0.82, Orientar 0.75) — los márgenes son fijos
(D1 = 0.00, D2 = 0.07) y por tanto NO existe ningún δ > 0 que produzca
aplazamientos orgánicos sin apagar a la vez la auto-resolución de toda
D1 (el ciclo adaptativo continuo del 2026-07-13 depende de que las D1
empatadas se resuelvan). La activación de la Parte F en producción no
es un valor de configuración: requiere confianzas que varíen con la
evidencia (productores LLM en el walkthrough vivo — ya construidos y
probados en M3 — o una regla de scoring sensible a la evidencia). La
política v2 se decide cuando esa migración ocurra; hasta entonces
producción sigue en v1 y la Parte F queda lista y probada, igual que
quedó la Parte E.

### Estado de la arquitectura deliberativa (2026-08-04)

La migración que la nota anterior esperaba **ya ocurrió**
(`ADR-0013`, calibración de confianza declarada de Diagnosticar/
Remediar/Orientar-LLM). `POLITICAS["v2"]` (`ADR-0012`) se activó una
primera vez brevemente y se revirtió el mismo día (`ADR-0015`, gap de
`urgente` real encontrado en esa activación); cerrada la precondición
que dejó pendiente, se reactivó de forma permanente en esta misma
sesión (`ADR-0016` + commit `82df22b`). Estado actual:

- **`ADR-0016` Aceptada** (`docs/architecture/ADR/ADR-0016-
  reactivacion-politica-v2-con-soporte-aplazada.md`, misma sesión) —
  gate técnico cerrado a tres niveles (llamada directa, HTTP real,
  navegador real bajo `v2` real) y §6 (¿distinguir "sin evidencia" de
  "evidencia aplazada/insuficiente"?) resuelta explícitamente como
  fuera de alcance: son en realidad **tres** caminos que colapsan en
  la misma `Entrega` vacía (sin evidencia, `Aplazada` D1/D2,
  D3-insuficiencia por `θ`), y modelar esa distinción queda registrado
  como evolución futura, no como deuda de esta ADR.
- **`POLITICAS["v2"]` activada operativamente en producción**, commit
  `82df22b` — cambio separado de la ADR, con su propio smoke test
  (sesión nueva sin overrides nace bajo `v2`; sesiones ya abiertas
  bajo `v1` permanecen `v1`, INV-1/INV-2). `urgente` propagado desde
  `app/services/runtime_bridge.py` (tabla de clasificación abajo) y
  los dos consumidores app-level de `Entrega`
  (`module_orchestration_service.py`, `pedagogy_runtime_bridge.py`)
  probados contra una `Aplazada` real (`tests/test_aplazada_
  consumidores_boundary.py`). Cadena completa: `ADR-0015` (rollback
  `v1`) → `4fd6ed8` (gap `urgente`) → `e0a83ff` (consumidores) →
  `ADR-0016` (Aceptada) → `82df22b` (activación permanente).

### Contrato de `urgente` por consumidor — preparación de ADR-0016 (2026-08-04)

Auditoría dirigida (Engineering Gate previo a la Fase 2 de `ADR-0016`,
sin tocar código): de los 4 sitios de producción que construyen
`PeticionHechoDelMundo` (`runtime.py:237`, `runtime.py:465`,
`runtime_bridge.py:110`, `runtime_bridge.py:441`), solo uno tiene el
hueco real que `ADR-0015 §8` encontró —`runtime_bridge.py:110`
(`registrar_evidencia_evaluacion`). Los otros tres ya son correctos:
dos por diseño explícito ya documentado en su propio comentario
(`hecho_docente` — RFC-0009 §3, el docente no es participante de
consenso; `registrar_pregunta_tutor` — la plataforma redacta la
respuesta del chat, nunca la `Entrega`) y uno es la referencia
canónica (`POST /hechos`, `urgente=True` con el razonamiento citado
en `runtime.py:242-247`).

`registrar_evidencia_evaluacion` no toma `urgente` en absoluto y tiene
4 llamadores de producción con semánticas distintas. El criterio de
`runtime.py:243` ("¿hay un estudiante esperando esta entrega en la
pantalla?") se precisa así, para que sea aplicable sin ambigüedad a
cualquier consumidor futuro:

> `urgente=True` ⇔ la `Entrega`/decisión deliberativa de esta llamada
> forma parte de la respuesta síncrona que desbloquea la siguiente
> acción del usuario — no "se ejecuta durante una interacción del
> estudiante" (los 4 llamadores lo hacen por igual), sino que su
> resultado se lee y se usa dentro de esa misma respuesta HTTP.

| Flujo | ¿Entrega dentro de la respuesta síncrona? | `urgente` |
|---|---|---|
| `POST /hechos` (`runtime.py:237`) | Sí — RFC-0006 §4 Parte E, ya `True` | ✅ `True` (sin cambio) |
| `submit_evaluation` (`students.py:989`) | Sí — `runtime_decision` viaja en el JSON de respuesta (líneas 1054/1064) | ✅ `True` (Fase 2) |
| `submit_cycle_evidence` (`students.py:541`) | Sí — `entrega.diseno` decide `forma` y dispara generación de recurso en la misma respuesta (líneas 566-622) | ✅ `True` (Fase 2) |
| `_registrar_diagnostico_en_runtime` (`student_service.py:127`) | No — retorno descartado (línea 155) | ❌ `False` (default, sin cambio) |
| `submit_attempt` (`knowledge_test_service.py:277`) | No — retorno descartado en ambas llamadas (líneas 396, 439); la función devuelve el `attempt` de SQLAlchemy | ❌ `False` (default, sin cambio) |
| `registrar_pregunta_tutor` (`runtime_bridge.py:441`) | No — ya documentado en su propio docstring | ❌ `False` (sin cambio, ya correcto) |
| `hecho_docente` (`runtime.py:465`) | No — ya documentado en su propio comentario | ❌ `False` (sin cambio, ya correcto) |

**Decisión explícita — diagnóstico y pre-test permanecen `False`.**
Ninguna pantalla del estudiante lee la `Entrega` de esas 2 funciones
(3 llamadas) en la misma respuesta que las dispara — el flujo
continúa hacia la siguiente pantalla sin mostrarla. Tratarlas como
urgentes extendería el contrato de "el estudiante espera esta entrega
en pantalla" a "el estudiante está en medio de cualquier interacción
evaluativa", una afirmación distinta y más amplia que `runtime.py:243`
no hace. Si esta decisión cambia en el futuro, se abre por su propio
RFC/ADR — no se infiere de esta auditoría.

Esto acota el diff mínimo de la Fase 2 de `ADR-0016` a: (1) un
parámetro `urgente: bool = False` en `registrar_evidencia_evaluacion`
propagado a su `PeticionHechoDelMundo`; (2) `urgente=True` explícito
en las dos llamadas de `submit_evaluation` y `submit_cycle_evidence`.
Cero cambios en `_registrar_diagnostico_en_runtime`, `submit_attempt`,
`registrar_pregunta_tutor` ni `hecho_docente`.
