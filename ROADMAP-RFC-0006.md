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
| RFC-0006/1 — Cimientos | 0 + A | `ce` calculable y testeado contra A1-A8, política versionada con un sitio real donde vivir. Sin cambios de comportamiento visible todavía. **CERRADO.** |
| RFC-0006/2 — Detección y clasificación | B | D1 se detecta y clasifica por primera vez (inerte hoy — ningún productor la activa); la tensión D2 real (Remediar/Orientar) se preserva bit a bit. |
| RFC-0006/3 — Propuesta única y θ | C | Una propuesta débil sin rival ya no deriva decisión sola — primer camino real de insuficiencia D3. |
| RFC-0006/4 — Resolución completa | D + E (tras levantar el bloqueo de `ejecucion`) | `politica-v2` resuelve con margen real; aplazamiento y provisional existen de verdad. |
| RFC-0006/5 — Escalada y orden | F + G | S2 empieza a mostrar escaladas reales sin sembrado manual; H7 verificado. |
| RFC-0006/6 — Cierre | H + I | Validación E2E completa, sembrado manual retirado, RFC-0006 cerrado. |

> **Nota (2026-07-12):** RFC-0006/2 originalmente agrupaba B+C. El
> Engineering Gate reveló que Parte C requiere construir un camino de
> enrutamiento que hoy no existe (blast radius real sobre `enrutar()`,
> precedente `GraphRecursionError`) — se dividió en 2+3, corriendo la
> numeración de las mini-épicas siguientes. Ver la nota al inicio de la
> ficha RFC-0006/2 y la ficha RFC-0006/3 más abajo.

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
2. **Parte E — Engineering Review dedicada, antes de esa parte, no
   dentro de ella.** El vacío de `estado.ejecucion` (RFC-0004 §2) no se
   resuelve sobre la marcha. Antes de abrir RFC-0006/4 (Resolución
   completa, D+E — numeración corrida por la división de RFC-0006/2 en
   2+3, ver ficha de RFC-0006/2) corre una revisión propia con su
   propio objetivo: ¿qué representa `ejecucion`
   realmente?, ¿quién lo escribe?, ¿quién lo consume?, ¿cuál es su
   ciclo de vida (persistente o efímero)?, ¿qué invariantes debe
   cumplir? Solo con esas respuestas se implementa "urgente" en Parte E.

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

### RFC-0006/1A — Engineering Review previa (solo Parte A, sin código)

Antes de escribir `confianza.py`, una revisión dedicada que traduce
A1-A8 (RFC-0006 §1) a un contrato computable — entrada, salida,
propiedad demostrable, caso borde, test asociado, por axioma. Vive en
`CONTRACT-A1-A8.md` (documento de trabajo temporal, no un RFC ni un
ADR — puede eliminarse una vez que su contenido esté absorbido por el
código y los tests). **RFC-0006/1 (la implementación, Parte 0 + Parte
A) no empieza hasta que este documento esté aprobado.**

### Ficha — RFC-0006/1: Cimientos

```
Objetivo:        Confianza efectiva (ce) calculable y demostrada contra
                 A1-A8; la política versionada tiene un sitio real
                 donde vivir. Sin cambio de comportamiento visible.
Partes:          0 + A
Dependencias:    RFC-0006/1A (CONTRACT-A1-A8.md) aprobado
Riesgos:         Altos ambas partes — 0 decide un mecanismo no
                 especificado; A es la pieza más delicada del RFC
                 completo (violar A5/A6/A7 sin darse cuenta) — mitigado
                 por RFC-0006/1A.
Motor:           Cambia — `kernel/deliberation/politica.py` (Parte 0:
                 diccionario de constantes `POLITICAS = {"v1": ...,
                 "v2": ...}`, sin Protocol — no hay evidencia hoy de
                 que el dominio necesite polimorfismo; se introduce
                 solo si aparece una política calculada dinámicamente)
                 + `kernel/deliberation/confianza.py` (Parte A,
                 `calcular_confianza_efectiva()`, según CONTRACT-A1-A8.md).
                 mecanica.py NO se toca todavía (v1 intacta).
Boundary:        No cambia.
HTTP:            No cambia.
Frontend:        No cambia.
E2E:             No cambia — ce no es observable desde ninguna
                 categoría de runtime_completo.py hasta que Parte D la
                 conecte a mecanica.py (RFC-0006/4 tras la renumeración
                 de 2026-07-12, antes "RFC-0006/3" — ver ficha de
                 RFC-0006/2).

No debe cambiar: politica-v1 / mecanica.py, kernel/reducers/ (ningún
                 reducer nuevo — ce es una proyección, no una
                 mutación), boundary/, app/api/routes/, frontend/,
                 RFC-0010 (ninguna surface nueva ni modificada),
                 backend/e2e/ (ningún ajuste — nada observable cambia).

Context Budget:  CONTRACT-A1-A8.md (una vez aprobado), RFC-0006,
                 CONCEPT-0002, ROADMAP-RFC-0006.md,
                 kernel/deliberation/mecanica.py (leer, no tocar),
                 kernel/state/entries.py, kernel/state/state.py,
                 kernel/reducers/ (leer, no tocar),
                 tests/runtime/ (para el patrón de test real existente).
                 No abrir boundary/, app/, frontend/ salvo que el
                 propio Gate revele que algo ahí es necesario — y si
                 aparece, justificar antes de abrir, no abrir primero.

Criterios de cierre — CERRADO 2026-07-12:
  ✓ A1-A7 tienen test dedicado (A1/A5/A6 con más de uno donde hacía
    falta demostrar más de una propiedad — p.ej. A6 necesitó un test
    sin ancla y otro anclado tras validación para no ser trivial),
    contra Postgres real, siguiendo CONTRACT-A1-A8.md. A8 no tiene test
    directo en confianza.py (es una precondición del llamador, no un
    caso que la función valide) — su garantía se testea cuando Parte D
    conecte `ce` a mecanica.py (RFC-0006/4 tras la renumeración) contra
    el filtro real de vigencia.
  ✓ v1 (politica-v1 / mecanica.py) sigue produciendo exactamente las
    mismas decisiones — mecanica.py no se tocó (0 líneas), y
    runtime_completo.py corrió el walkthrough real end-to-end
    (Adaptar → "modalidad(COMP-2)" vía LLM real) con el mismo resultado
    ya documentado antes de este cambio.
  ✓ El mecanismo de política versionada permite que "v2" exista sin
    tocar una línea de "v1" (test_una_politica_nueva_no_toca_v1)
  ✓ confianza.py no importa mecanica.py (test estructural)
  ✓ mecanica.py no importa confianza.py (test estructural, mismo patrón
    que reconstruccion.py)
  ✓ Toda la Parte A se prueba sin ejecutar LangGraph — LearningState
    construido a mano vía reducers puros, sin walkthrough ni productores
  ✓ Ninguna API HTTP cambió (0 archivos en app/api/ ni boundary/)
  ✓ Ninguna surface Boundary cambió
  ✓ runtime_completo.py sigue en 9/9 PASS, sin categoría nueva
  ✓ No aparecen TODO/FIXME nuevos
  ✓ Cobertura: 281 tests (260 previos + 21 nuevos: 7 Parte 0 + 14 Parte A)
  ✓ CONTRACT-A1-A8.md reducido a una línea de referencia — verificado
    con una Engineering Review de cierre dedicada (2026-07-12,
    segunda ronda): la primera reducción fue prematura, dejaba A1, A2,
    A3 y la garantía central de A5 sin restated en ningún docstring
    (solo mencionados tangencialmente) y 5 referencias colgantes a
    "CONTRACT-A1-A8.md" en confianza.py/politica.py/tests apuntando a
    un documento ya vacío. Corregido: confianza.py tiene ahora una
    sección "Garantías" explícita con las ocho, cada clase de test
    A1-A7 tiene su enunciado en el docstring (legible sin el documento
    viejo), y las 5 referencias colgantes se reemplazaron por punteros
    al código real. 281/281 tests siguen en verde tras el cambio.

Corrección encontrada durante la implementación (registrada, no
oculta): el contrato original de A4/A6 (`estado.transicion -
claim.id.transicion`, edad medida desde el ORIGEN del claim) violaba
A7 — un test real (`TestA7_LocalidadCausal`) lo probó: actividad en un
asunto ajeno decaía un claim que nunca tocó. Corregido a "edad medida
desde la última validación DENTRO de la cadena causal del claim, o 0 si
nunca hubo ninguna" — ver la sección "Garantías" del docstring de
módulo de `confianza.py` y el docstring de `Politica` en `politica.py`
(CONTRACT-A1-A8.md, el documento temporal donde se descubrió esto, ya
está retirado). Efecto colateral: la invariante
`peso_refuerzo >= peso_decaimiento` en `Politica.__post_init__` dejó de
ser matemáticamente necesaria bajo el diseño corregido (una validación
recién aplicada tiene edad lógica 0 en su propio tick) y se retiró.
```

---

## Ficha — RFC-0006/2: Detección y clasificación (D1/D2)

> **Nota de proceso (2026-07-12):** esta ficha originalmente agrupaba
> B + C ("Convocatoria real"). El Engineering Gate reveló que Parte C
> no es "agregar un chequeo" — requiere construir un camino que hoy no
> existe (ver la ficha RFC-0006/3 más abajo), con blast radius real
> sobre `enrutar()` (precedente `GraphRecursionError`). Se dividió en
> dos mini-épicas más pequeñas, manteniendo la disciplina de "un
> concepto nuevo por commit" en vez de expandir el alcance a mitad de
> la implementación — la numeración de mini-épicas posteriores (antes
> RFC-0006/3..5) se corrió en consecuencia (§3, tabla actualizada).

```
Objetivo:        La tensión D1 (interpretaciones rivales del mismo
                 asunto) se detecta y se clasifica explícitamente como
                 D1, distinta de D2 (propuestas rivales, ya detectada
                 hoy) — sin tocar cómo se resuelve ninguna de las dos
                 todavía (eso es Parte D).
Partes:          B (únicamente — C se movió a RFC-0006/3)
Dependencias:    RFC-0006/1 (Cimientos) cerrado — `ce` y `Politica` ya
                 existen y están probados. (No depende de `ce`
                 directamente: B es lógica de predicado sobre
                 `TipoClaim`, no de cálculo — la dependencia es de
                 orden, no técnica.)
Riesgos:         Medio (tabla §6) — es cobertura, no dificultad
                 técnica: verificar contra las 3 tensiones canónicas de
                 CONCEPT-0002 §1 sin dejar un cuarto caso sin
                 clasificar. Bajo blast radius: NO toca `enrutar()`
                 (ver Motor).

Auditoría previa (estado actual, verificado leyendo código, no
supuesto): hoy `tension_bloqueante()` (mecanica.py) solo mira claims
`PROPUESTA` — nunca detecta rivalidad entre `INTERPRETACION`. Y NINGÚN
productor real conectado al grafo (`diagnosticar/productor.py`,
`diagnosticar/productor_llm.py`, ambos auditados línea por línea) puede
hoy producir más de una `INTERPRETACION` por asunto: los dos tienen la
guardia `ya_interprete` (si ya existe una interpretación vigente de
Diagnosticar, no producen otra) y ambos `return` dentro del primer
`for` que encuentra un fact — como máximo un intent por invocación. Esto
significa: **la tensión D1 es estructuralmente imposible de producir
hoy en el walkthrough real** — no es que no ocurra por casualidad, es
que ningún camino del código puede generarla.

Auditoría adicional — la tensión D2 SÍ es real y SÍ está viva hoy: en
`"siguiente-paso(sesion)"`, Orientar propone incondicionalmente
"avanzar-con-andamiaje" en cuanto existe alguna interpretación vigente
(`orientar/productor.py`), y Remediar propone cuando
`dominada=False` (`remediar/productor.py`) — ambas comparten
literalmente el mismo asunto (`ASUNTO_SIGUIENTE_PASO =
"siguiente-paso(sesion)"` en los dos archivos). Cuando ambas disparan
en el mismo walkthrough, `tension_bloqueante()` YA las detecta hoy y
`convocar()` YA las resuelve por `mayor-confianza-declarada` — esta es
la tensión canónica #1 de CONCEPT-0002 §1 ("¿avanzar o reforzar?", D2
pura), en vivo, no hipotética. **Esta es la superficie de regresión
real de esta mini-épica**: el refactor de `tension_bloqueante()` debe
preservar bit a bit esta detección/resolución existente — la Garantía
de activación de abajo cubre D1 (inerte), no D2 (vivo y debe mantenerse
idéntico).

**Garantía de activación — D1 (propiedad verificable, no solo
observación):** aunque la detección D1 exista tras RFC-0006/2, ningún
recorrido del walkthrough actual puede activarla, porque ningún
productor conectado genera interpretaciones rivales. Cualquier
diferencia observable en `runtime_completo.py` atribuible a D1 durante
esta mini-épica constituye una regresión, no un efecto secundario
aceptable.

Motor:           Cambia — `kernel/deliberation/mecanica.py` únicamente.
                 `tension_bloqueante()` extiende su retorno de
                 `(asunto, participantes)` a `(tipo, asunto,
                 participantes)`, con `tipo` ∈ {"D1", "D2"} — escanea
                 primero `INTERPRETACION` (D1) y luego `PROPUESTA` (D2)
                 por asunto, mismo criterio de rivalidad que hoy (≥2
                 vigentes). `convocar()` desempaqueta el 3-tuple y
                 descarta `tipo` por ahora (ignora la clasificación,
                 usa `participantes` exactamente como hoy — resolución
                 sin cambios, es Parte D). `enrutar()` en
                 `walkthrough.py` **NO cambia**: su chequeo
                 `tension_bloqueante(estado) is not None` sigue
                 funcionando sin modificación con el 3-tuple — inventar
                 una rama nueva ahí sería adelantar comportamiento de
                 Parte D que todavía no existe.
Boundary:        No cambia.
HTTP:            No cambia.
Frontend:        No cambia.
E2E:             `runtime_completo.py` no gana categoría nueva.
                 Categoría Runtime debe seguir en verde con el MISMO
                 resultado — es la prueba de que la tensión D2 viva
                 (Remediar/Orientar) sigue resolviéndose exactamente
                 igual tras el refactor.

No debe cambiar: `enrutar()` / `engine/graph/walkthrough.py` (ningún
                 archivo de grafo se toca en esta mini-épica — el
                 3-tuple es compatible con el chequeo `is not None`
                 existente sin editar una línea ahí), `confianza.py`
                 (Parte A ya cerrada), `politica.py` (theta es Parte C,
                 no esta ficha), `derivar_decision()` (Parte D),
                 cualquier lógica de margen δ o resolución D1-vs-D2 con
                 peso distinto (Parte D), boundary/, app/api/routes/,
                 frontend/, REGLA_POLITICA_V1 =
                 "mayor-confianza-declarada" (sigue siendo la única
                 regla de resolución; D1/D2 se clasifican pero ambas
                 siguen resolviéndose igual hasta Parte D).

Context Budget:  ROADMAP-RFC-0006.md (este documento), RFC-0006 §3,
                 CONCEPT-0002 §1 (las 3 tensiones canónicas),
                 kernel/deliberation/mecanica.py,
                 kernel/state/entries.py,
                 runtime/domain/diagnosticar/,
                 runtime/domain/remediar/productor.py,
                 runtime/domain/orientar/productor.py (los tres, leer
                 no tocar — ya auditados: confirman D1 inalcanzable y
                 D2 real/vivo), tests/runtime/deliberation/ (patrón ya
                 establecido). No abrir engine/graph/,
                 kernel/deliberation/politica.py, boundary/, app/,
                 frontend/ — nada de esto cambia en esta ficha.

Criterios de cierre — CERRADO 2026-07-12:
  ✓ tension_bloqueante() clasifica explícitamente cada tensión
    encontrada como D1 o D2 — 3 tensiones canónicas de CONCEPT-0002 §1
    (avanzar-vs-reforzar D2 real, modalidad D2, dominó-el-objetivo D1) +
    1 caso de control sin tensión (test_parteB_deteccion_tension.py)
  ✓ La tensión D2 viva (Remediar vs Orientar en
    "siguiente-paso(sesion)") se detecta y resuelve exactamente igual
    que antes del refactor — test explícito construido con los
    productores reales (no una fixture inventada), Y confirmado en el
    E2E real: `runtime_completo.py` produjo exactamente 7 transiciones
    (fact→diagnosticar→remediar→orientar→deliberación→decisión→adaptar),
    idéntico al recorrido pre-Parte-B
  ✓ convocar() sigue produciendo el mismo TransitionIntent — mismo
    ganador (Remediar, 0.82), misma regla (mayor-confianza-declarada)
  ✓ enrutar() / walkthrough.py: 0 líneas modificadas (verificado con
    test estructural: ni "D1" ni "D2" aparecen en walkthrough.py)
  ✓ politica-v1 sigue produciendo exactamente las mismas decisiones —
    runtime_completo.py 9/9 PASS, categoría Runtime idéntica
    (entrega=modalidad(COMP-2), mismo shape de traza)
  ✓ Toda la Parte B se prueba sin ejecutar LangGraph — LearningState a
    mano o productores reales invocados directamente, sin walkthrough
  ✓ Ninguna API HTTP cambia
  ✓ Ninguna surface Boundary cambia
  ✓ No aparecen TODO/FIXME nuevos
  ✓ Cobertura: 288 tests (281 previos + 7 nuevos de Parte B)
  ✓ Ningún documento temporal nuevo abierto en esta ficha
```

---

## Ficha — RFC-0006/3: Propuesta única, θ e insuficiencia (D3)

> Separada de RFC-0006/2 por el Engineering Gate (nota arriba). No
> escribir código de esta ficha hasta cerrar y aprobar RFC-0006/2.

```
Objetivo:        Una propuesta sin rival (slot pendiente con un único
                 claim) deriva su decisión directamente si `ce` alcanza
                 el umbral θ de la política — y esa derivación queda
                 registrada como "no-convocatoria" (RFC-0006 §3, P6:
                 "decidió una capacidad sola porque nadie podía
                 disentir"). Si `ce` no alcanza θ: NO deriva decisión —
                 se activa el camino de evidencia.
Partes:          C
Dependencias:    RFC-0006/2 (Detección y clasificación) cerrado.

Auditoría previa (estado actual — hallazgo del Gate de RFC-0006/2,
verificado leyendo código, no supuesto): **hoy NO existe ningún camino
para que una propuesta única derive una decisión.** `registrar_decision`
solo se invoca desde `derivar_decision()` (mecanica.py), que solo lee
`estado.deliberaciones` buscando una `Resuelta` — nunca examina un
claim-propuesta sin rival directamente. El motivo por el que esto no se
había notado: en el único slot de decisión real del walkthrough actual
(`"siguiente-paso(sesion)"`), Orientar SIEMPRE propone en cuanto existe
alguna interpretación vigente, así que ese slot tiene rivalidad
(Remediar vs Orientar) por construcción del par de productores
actuales, no por diseño del mecanismo — la "propuesta única" nunca se
ejerce hoy, no porque sea imposible (a diferencia de D1 en RFC-0006/2),
sino porque los dos únicos productores de ese slot resultan estar
diseñados para competir siempre. RFC-0003/RFC-0006 SÍ contemplan
"propuesta única deriva directa" como caso normativo (`registrar_decision`
ya soporta un origen `ClaimEntry` directo — INV-6 — sin que nada del
grafo lo invoque hoy). Esta mini-épica construye el primer camino real
para ese caso, no lo modifica.

Riesgos:         Alto — mayor que lo que la ficha original de
                 RFC-0006/2 asumía. No es "agregar un chequeo dentro de
                 convocar()": es una rama de enrutamiento nueva en
                 `enrutar()` (`engine/graph/walkthrough.py`), el mismo
                 archivo del `GraphRecursionError` de HITL. Riesgo
                 específico: una guardia mal puesta en esta rama puede
                 crear un ciclo aplicar→enrutar sin avance (mismo tipo
                 de bug que las guardias PR-2..PR-5 ya existentes en
                 ese archivo previenen para otros nodos) — replicar el
                 mismo patrón de guardia, no inventar uno nuevo.

Motor:           Cambia — `kernel/deliberation/politica.py` (nuevo
                 campo `theta: Decimal`; `theta_v1` se decide en el
                 Gate de esta ficha, demostrado por la suite, no
                 asumido de antemano) + `kernel/deliberation/mecanica.py`
                 (nueva función — p. ej. `derivar_directa()` o nombre
                 que decida el Gate — que localiza una PROPUESTA vigente
                 sin rival y sin decisión ya derivada de su asunto, y
                 devuelve un intent de decisión si `ce >= theta`, o
                 nada si no) + `engine/graph/walkthrough.py` (`enrutar()`
                 gana la rama de insuficiencia — con guardia segura,
                 mismo patrón que las guardias PR-2..PR-5 existentes,
                 para no repetir el riesgo de GraphRecursionError).
Boundary:        No cambia (a confirmar en el Gate — si D3 necesita ser
                 observable, podría tocar RFC-0007, no esta ficha).
HTTP:            No cambia.
Frontend:        No cambia.
E2E:             runtime_completo.py, categoría Runtime: DEBE seguir
                 produciendo el mismo resultado si theta_v1 se elige
                 correctamente — validación obligatoria, no opcional.

No debe cambiar: `tension_bloqueante()` / clasificación D1/D2 (RFC-0006/2
                 ya cerrada, no se reabre), `confianza.py` (Parte A),
                 resolución con margen δ (Parte D), REGLA_POLITICA_V1,
                 boundary/, app/api/routes/, frontend/.

Context Budget:  ROADMAP-RFC-0006.md (este documento), RFC-0006 §3
                 completo, CONCEPT-0002 §1/§3,
                 kernel/deliberation/mecanica.py,
                 kernel/deliberation/politica.py,
                 kernel/reducers/decisiones.py (ya soporta origen
                 ClaimEntry directo — leer antes de tocar),
                 engine/graph/walkthrough.py completo (leer entero antes
                 de tocar una línea — precedente GraphRecursionError),
                 runtime/domain/remediar/, runtime/domain/orientar/
                 (leer, no tocar), tests/runtime/deliberation/,
                 tests de grafo existentes (patrón de guardias
                 PR-2..PR-5). No abrir boundary/, app/, frontend/ salvo
                 que el Gate lo justifique explícitamente antes de
                 abrir.

Criterios de cierre:
  □ Existe un camino real (no solo una función pura sin wiring) para
    que una propuesta única derive decisión cuando ce >= theta
  □ Existe una función de insuficiencia D3 que compara `ce` contra
    `politica.theta` y decide NO derivar cuando no se alcanza
  □ La decisión derivada de propuesta única queda registrada de forma
    que "decidió una capacidad sola porque nadie podía disentir" sea
    verificable sin ambigüedad (P6) — usando el mecanismo que ya
    distingue origen ClaimEntry vs DeliberacionEntry, sin campo nuevo
    salvo que el Gate demuestre que hace falta
  □ Bajo política v1, la incorporación de θ no modifica ninguna decisión
    observable existente — el criterio es el comportamiento, no el
    valor concreto de `theta_v1`
  □ enrutar() usa una guardia seria (mismo patrón que PR-2..PR-5) — test
    explícito de que no introduce un ciclo aplicar→enrutar sin avance
  □ politica-v1 sigue produciendo exactamente las mismas decisiones —
    runtime_completo.py 9/9 PASS, categoría Runtime sin cambio de
    resultado observable
  □ Ninguna API HTTP cambia (salvo que el Gate lo justifique)
  □ Ninguna surface Boundary cambia (salvo que el Gate lo justifique)
  □ No aparecen TODO/FIXME nuevos
  □ No baja la cobertura de tests
  □ Ningún documento temporal nuevo queda abierto sin retirar al cerrar
```
