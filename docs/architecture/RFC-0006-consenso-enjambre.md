# RFC-0006 — Consenso e Inteligencia de Enjambre

- **Estado:** Aceptado (2026-07-10, rev. 2 — con el álgebra A1–A8 exigida
  por el tesista; H10 registrada en la aceptación)
- **Autor:** Equipo de arquitectura (Claude + tesista)
- **Fecha:** 2026-07-10
- **Aprueba:** Renato Lara (tesista / Product Owner)
- **Gobernado por:** CONCEPT-0001 (criterio normativo, E1–E6), CONCEPT-0002
  (taxonomía y regla de oro), FOUNDATIONAL_PRINCIPLES.md (P5, P7, P8, P12),
  RFC-0003, RFC-0004
- **Capa (RFC-0001 §1):** Kernel (mecánica) + política pedagógica
  versionada en `identidad` (parámetros)
- **Runtime Contract:** hace ejecutable la pregunta 4 (¿por qué eligió
  una?) y gobierna la 3 (cómo compiten las alternativas)

## Objetivo

Diseñar el comportamiento colectivo del sistema: la dinámica continua del
paisaje cognitivo (cómo la confianza se refuerza y decae) y el episodio de
deliberación (convocatoria, resolución por tipo, aplazamiento, escalada y
orden). Emitir el veredicto sobre las hipótesis Knowledge Claim, H4, H6 y
H7. Todo, juzgado contra E1–E6.

## Decisión irreversible

> **El consenso opera sobre la confianza efectiva — una proyección
> determinista del estado cuya álgebra (A1–A8, §1) es normativa — y su
> espacio de resultados es cerrado (regla de oro). Ninguna deliberación
> muta claims ni crea contenido (P15).**

De aquí se deriva todo: el paisaje evoluciona sin editar la historia
(INV-3), el replay reproduce el consenso exactamente (P12), y el mecanismo
no puede convertirse en superagente. **Lo que este RFC congela es el
álgebra; lo que la política calibra son las funciones que la satisfacen.**

## Contexto

- Agenda heredada (CONCEPT-0002): dinámica del paisaje, resolución por
  tipo (D1/D2/D3), umbrales, orden (regla de la raíz + H7), veredictos.
- Restricciones activas: la convocatoria es enrutamiento puro (RFC-0004);
  los facts no se deliberan (INV-8); toda deliberación registra regla,
  posiciones y confianza de resolución (INV-7); la política de orden debe
  preservar P12 (registro de H7).
- Relación con la hipótesis de la tesis: este RFC ES la variable
  independiente — define el mecanismo cuya superioridad sobre el pipeline
  del Legacy (grupo de control) afirma la hipótesis operacional.

## Propuesta

### 1. El mecanismo continuo: el álgebra de la confianza efectiva

**Qué es (y qué no es).** La confianza efectiva es una **medida de
respaldo**: cuánto sostiene el estado actual a un claim vigente. No es una
probabilidad (no afirmamos calibración frecuentista — sería inverificable)
ni una utilidad (no codifica preferencia — la preferencia pedagógica vive
en los pesos de política de D2). Por eso la resolución usa comparaciones y
márgenes, nunca el valor absoluto como apuesta.

**Firma.**

```
ce : Claim vigente × Estado × Política versionada → [0, 1]
```

**Axiomas (A1–A8).** Toda función que la política proponga debe
demostrarlos; son el criterio de aceptación de cualquier configuración:

| # | Axioma |
|---|--------|
| A1 | **Acotación**: ce ∈ [0, 1]. |
| A2 | **Anclaje**: en el estado en que el claim fue aplicado, ce = confianza declarada. |
| A3 | **Determinismo y pureza**: ce es función de (claim, estado, política versionada) y de nada más. Computarla jamás invoca un modelo, un reloj o el azar. |
| A4 | **Tiempo lógico**: ce solo puede cambiar entre estados por transiciones aplicadas; toda noción de "edad" se mide en transiciones — nunca en reloj de pared. |
| A5 | **Monotonicidad ante evidencia**: una validación positiva en la cadena del claim no la disminuye; una refutación no la aumenta; un fact contradictorio con su respaldo no la aumenta. |
| A6 | **Decaimiento sin refuerzo**: sin evidencia nueva en su cadena, ce es no-creciente respecto de la edad lógica de su respaldo. Nada se refuerza espontáneamente. |
| A7 | **Localidad causal**: ce depende únicamente de la cadena causal del claim (su respaldo hacia atrás; las decisiones y validaciones derivadas hacia adelante) y de los facts de su asunto. Toda ce es explicable exhibiendo esas entradas (P6). |
| A8 | **La vigencia domina**: un claim supersedido sale del paisaje; ninguna ce lo devuelve. |

**Transformaciones prohibidas** (violan el álgebra sea cual sea la
política): mutar la confianza declarada (INV-3); dependencia de reloj de
pared, azar o evaluación por LLM; influencia de entradas fuera de la
cadena causal y del asunto ("estado de ánimo global"); valores fuera de
[0, 1]; resurrección de supersedidos.

**Forma ilustrativa** (no normativa — cualquier función que satisfaga
A1–A8 es admisible):

```
ce = f( confianza_declarada,
        refuerzos      — validaciones positivas en su cadena (Validar),
        refutaciones   — veredictos negativos en esa cadena,
        decaimiento    — edad lógica del respaldo (transiciones),
        contradicción  — facts nuevos incompatibles con su respaldo )
```

**Reparto de responsabilidades**: el RFC congela A1–A8; la política
pedagógica versionada en `identidad` elige pesos y curvas concretas —
cambiar parámetros es nueva versión registrada, y el replay usa la versión
grabada. Nada se escribe: la proyección se computa donde se necesita, y el
paisaje sigue siendo una vista (CONCEPT-0001).

**Frontera de sesión**: el refuerzo intra-sesión es del paisaje; su
consolidación inter-sesión viaja por `salidas` → memoria (RFC-0005).
*Extensión registrada, no diseñada aquí:* reputación por capacidad —
depende del RFC-0005.

A5 + A6 satisfacen E4 por construcción: la influencia de una señal cambia
con la evidencia validada, sin tocar una sola entrada.

### 2. El requisito del asunto ⚠

Para que la convocatoria sea una función pura del estado, el Kernel debe
poder detectar que dos claims **hablan de lo mismo** sin interpretar
payloads (interpretarlos exigiría un LLM en el enrutamiento — prohibido
por la regla de control). Por tanto:

> Todo claim declara su **asunto**: el identificador normalizado de la
> pregunta que responde (`modalidad(objetivo-X)`, `dominio(COMP-2)`,
> `siguiente-paso(sesión)`) y, dentro del asunto, una **posición**
> comparable.

Dos claims vigentes con el mismo asunto y posiciones incompatibles = una
tensión. Si además un slot de decisión los espera, es bloqueante (§3).

**Impacto sobre RFC-0003 — un campo, no un concepto:** la taxonomía ya
hablaba de "el mismo aspecto" y "el mismo slot"; este RFC lo formalizó
como campo del `ClaimEntry`. **Enmienda aprobada por el tesista y aplicada
en RFC-0003 rev. 5** (sobre + INV-5). Fue la única modificación al modelo
que este diseño necesitó — no una sorpresa conceptual, sino la
formalización de algo que la taxonomía ya usaba.

### 3. Convocatoria y umbrales

Predicados puros sobre el estado (implementados como reglas de
enrutamiento, RFC-0004 §4):

- **Tensión**: ≥ 2 claims vigentes, mismo asunto, posiciones
  incompatibles.
- **Bloqueante**: existe un slot de decisión pendiente cuyo asunto es el
  de la tensión. Solo entonces se convoca (P8). Las tensiones latentes
  permanecen en el paisaje.
- **Insuficiencia (D3)**: un slot pendiente cuyo mejor claim no alcanza el
  umbral de decisión θ de la política. No se convoca deliberación: se
  activa el camino de evidencia (la regla enruta hacia la capacidad que
  puede producirla — p. ej. Evaluar con una micro-actividad).
- **No-convocatoria registrada**: cuando una decisión deriva de propuesta
  única, el registro de la decisión lo hace constar (P6): *decidió una
  capacidad sola porque nadie podía disentir*.

### 4. Resolución por tipo

Sobre los claims participantes, con sus confianzas efectivas:

- **D1 (interpretativo)** — gana la evidencia: se acepta el claim con
  mayor confianza efectiva **si** el margen sobre el rival supera el
  umbral de discriminación δ (política). Confianza de resolución =
  función del margen normalizado.
- **D2 (prescriptivo)** — evidencia + política: puntaje = confianza
  efectiva × peso de política pedagógica para ese asunto (p. ej.
  "prioridad a brecha en competencia crítica sobre avance"). Los pesos
  son configuración versionada; la regla aplicada queda registrada
  (INV-7). Margen → confianza de resolución.
- **Margen < δ** → **aplazada**, registrando qué evidencia
  discriminaría (INV-7) — declaración accionable (CONCEPT-0002 §4).
- **Decisión provisional** — si el slot es urgente (bloquea una entrega
  que el estudiante espera, atributo derivado de `ejecución`) y el margen
  < δ: se resuelve con el mejor claim disponible y confianza de
  resolución baja; INV-12 la marca para validación prioritaria.
- **Escalada** — dos vías, ambas de política: casos que la política
  reserva al humano, y el **límite de reconvocatoria**: una tensión
  aplazada y reconvocada N veces (política) sin discriminar escala al
  docente — ninguna deliberación puede diferirse para siempre.
- **Espacio cerrado**: estos son TODOS los resultados (regla de oro,
  CONCEPT-0002 §5 bis). La síntesis reconvoca a una capacidad; el
  mecanismo jamás redacta (**P15**).

### 5. Orden (veredicto sobre H7)

Política de orden adoptada, determinista y P12-segura:

1. **Regla de la raíz**: deliberaciones D1 antes que las D2 cuyos
   participantes se respaldan en los claims en disputa.
2. **Entre pares**: orden de llegada registrado (FIFO lógico sobre el
   índice de transición).
3. **Desempate**: prioridad pedagógica del asunto según la política
   versionada.

El orden resultante es función del estado más el registro de llegada —
el replay lo reproduce. **H7 queda RESUELTA con esta política**; futuras
políticas más ricas son nuevas versiones de configuración, no enmiendas.

### 6. Veredictos sobre las hipótesis

- **Knowledge Claim (RFC-0002): ADOPTADA.** El consenso valida
  afirmaciones y las decisiones derivan de las aceptadas — ya era la
  estructura; este RFC la hace semántica oficial.
- **H6 (clases de intent): ADOPTADA sin nuevo vocabulario.** La distinción
  observacional/decisional ES `tipo: interpretación | propuesta` (campo
  existente), y las reglas D1/D2 los tratan distinto — exactamente lo que
  H6 pedía. No se añade ninguna estructura.
- **H4 (Intent → Resolution → Execution): PARCIALMENTE ADOPTADA.** Se
  adopta **"resolución"** como término oficial del resultado de una
  deliberación (INV-7 ya hablaba de "regla de resolución"). Se **rechaza**
  renombrar la sección `decisiones` del estado: el costo (enmendar el
  vocabulario normativo de RFC-0003 y todo lo que lo cita) supera el
  beneficio, y la distinción decisión/ejecución ya es expresable
  (decisión + fact de entrega, Walkthrough-0001).

### 7. Verificación contra E1–E6

| Criterio | Cómo lo satisface este diseño |
|----------|-------------------------------|
| E1 | La deliberación lee el estado; ningún participante conoce a otro — las "posiciones" son claims, no interlocutores |
| E2 | Toda resolución registra ≥ 2 posiciones, regla y margen; la atribución es al episodio, no a una capacidad |
| E3 | Umbrales y pesos son política sobre reglas puras; ninguna secuencia se codifica |
| E4 | La confianza efectiva §1 evoluciona con la validación por construcción |
| E5 | Una capacidad ausente = menos claims en el paisaje; los predicados §3 siguen siendo válidos y el sistema decide con lo que hay |
| E6 | Toda resolución es función de confianzas efectivas, que son proyección del paisaje vigente — reconstruible y replayable |

### 8. Hipótesis registrada

**H10 — Confidence Calibration (REGISTRADA, no incorporada):** propuesta
del tesista en la aceptación de este RFC: *la política pedagógica puede
calibrar la función de confianza sin modificar el runtime*. Es la
hipótesis de la etapa experimental: distintas versiones de política
(pesos, curvas, δ, θ) que satisfagan A1–A8 producen dinámicas de
adaptación medibles y comparables — incluso sobre las mismas sesiones,
vía replay con política alternativa. **Se evalúa en el diseño experimental
de la tesis**, con los instrumentos del RFC-0007.

## Alternativas consideradas y rechazadas

1. **Votación por mayoría entre N agentes**: prohibida por la
   anti-definición (CONCEPT-0001) — cuenta opiniones, no construye
   conocimiento colectivo.
2. **Juez LLM** (un modelo árbitro lee las posiciones y decide): traslada
   el control al modelo (viola la regla de control y P12) y reintroduce
   cognición central — el superagente con toga.
3. **Debate conversacional multi-ronda** (agentes argumentando por
   turnos): handoffs disfrazados (P3), coste por ronda, y el resultado
   depende del orden de los turnos — irreproducible.
4. **Confianza mutable in situ** (actualizar el campo del claim):
   viola INV-3; la proyección §1 logra la misma dinámica sin tocar la
   historia.
5. **Protocolos bizantinos / quórum**: resuelven nodos adversarios no
   confiables — un problema que no tenemos (las capacidades no son
   adversarias) — al precio de una complejidad que nada de la hipótesis
   necesita.

## Ventajas / Riesgos / Impacto / Complejidad

- **Ventajas:** dinámica de enjambre real (refuerzo/decaimiento) sin
  mutar historia; consenso 100 % replayable; parámetros como política
  versionada = experimentos comparables (misma sesión, políticas
  distintas); los veredictos cierran cuatro hipótesis abiertas.
- **Riesgos:** (1) calibración de δ, θ y pesos — mitigación: son política
  versionada, ajustables sin tocar diseño, y su calibración ES un
  experimento de la tesis; (2) asuntos mal normalizados que oculten
  tensiones — mitigación: el catálogo de asuntos se deriva del vocabulario
  de RFC-0002 (competencias, objetivos, modalidades) y se fija en la
  política; (3) proyección costosa — mitigación: se computa sobre el
  subconjunto vigente del asunto en cuestión, no sobre todo el paisaje.
- **Impacto:** enmienda menor a RFC-0003 (campo `asunto`, pendiente de
  autorización); RFC-0005 hereda la consolidación inter-sesión del
  refuerzo y la extensión de reputación; RFC-0007 hereda H8/H9 y las
  métricas de resolución (márgenes, tasas de aplazamiento, cadenas de
  reconvocatoria); RFC-0009 hereda los dos disparadores de escalada.
- **Complejidad:** conceptual ya pagada (CONCEPT-0001/0002); de diseño
  media; de implementación acotada al Kernel + configuración.

## Recomendación

Aceptar el diseño. Las dos decisiones que acompañaban a este RFC ya
fueron tomadas por el tesista: la enmienda `asunto` está aplicada
(RFC-0003 rev. 5) y «la deliberación selecciona, jamás crea» fue elevada
y generalizada como **P15** (Constitución rev. 2). Queda una sola
decisión: si el álgebra A1–A8 es el contrato con el que quieres que toda
implementación de la confianza efectiva sea juzgada.

## Consecuencias

- Vocabulario normativo nuevo: **confianza efectiva** (medida de respaldo
  con álgebra A1–A8), **asunto**, **posición**, **umbral de decisión θ**,
  **umbral de discriminación δ**, **límite de reconvocatoria**,
  **resolución** (el resultado de una deliberación).
- Toda función de confianza propuesta por una política debe demostrar
  A1–A8 antes de activarse; los parámetros viven exclusivamente en la
  política versionada — ningún número mágico en el Kernel.
- H6 y H7 quedan resueltas; H4 parcialmente adoptada; Knowledge Claim
  adoptada; P15 elevado. Permanecen abiertas: P14 (elevación, →
  RFC-0007), H5 y H8 (→ RFC-0007), H9 (→ RFC-0005/0007), reputación de
  capacidad (→ RFC-0005).
