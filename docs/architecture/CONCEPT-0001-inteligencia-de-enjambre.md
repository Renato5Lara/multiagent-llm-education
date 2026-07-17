# ¿Qué entendemos por inteligencia de enjambre en UPAO-MAS-EDU?

- **Estado:** Aceptado (2026-07-10, rev. 2 — fundamento obligatorio y
  criterio normativo del RFC-0006)

## La pregunta

> ¿Qué convierte una colección de capacidades independientes en un
> verdadero sistema multiagente colaborativo, en lugar de un simple
> conjunto de productores concurrentes?

## Definición

**En UPAO-MAS-EDU, inteligencia de enjambre es la coordinación
estigmérgica adaptativa de capacidades cognitivas heterogéneas sobre un
estado compartido, en la que emerge un paisaje cognitivo colectivo — el
conjunto vigente de afirmaciones respaldadas — del cual derivan las
decisiones pedagógicas, reguladas por retroalimentación de evidencia
validada y sin cognición central.**

Cuatro propiedades la componen; ninguna es opcional:

1. **Coordinación estigmérgica.** Ninguna capacidad conoce a otra ni le
   habla. Colaboran como las hormigas de Grassé: dejando rastros en un
   medio compartido. El medio es el `LearningState`; los rastros son los
   claims. Una capacidad no responde a otra capacidad: responde al estado
   que otra modificó.
2. **Coordinación adaptativa.** Los rastros no solo existen: **cambian
   según la validación**. Un claim cuya decisión derivada funcionó se
   refuerza; uno refutado por la evidencia decae o es supersedido. La
   colonia no aprende porque las hormigas piensen mejor: aprende porque
   los rastros que llevan a comida se intensifican y los demás se
   evaporan.
3. **Cognición descentralizada, consistencia centralizada.** Ningún
   componente posee la decisión. El Kernel es central, pero es *física*,
   no *reina*: valida invariantes y aplica transiciones sin opinar sobre
   pedagogía — igual que el mundo físico de una colonia evapora feromonas
   sin decidir la ruta.
4. **Emergencia.** Ni la secuencia pedagógica ni las decisiones están
   codificadas. Emergen de reglas locales sobre el estado. Qué emerge
   exactamente, lo define la siguiente sección — porque "emerge una
   decisión" es una respuesta filosófica, y este documento debe una
   operacional.

## Qué emerge exactamente

**La decisión no emerge directamente. Lo que emerge primero es el paisaje
cognitivo** (*belief landscape*): el conjunto de claims vigentes — con sus
confianzas, sus respaldos y sus tensiones — en un momento dado. El paisaje
es la percepción colectiva del sistema sobre el estudiante y su
aprendizaje: ninguna capacidad lo posee, ninguna lo diseñó, y sin embargo
existe y es consultable. Las decisiones son consecuencia del paisaje: se
derivan de él (propuesta única sin oposición) o se resuelven sobre él
(deliberación cuando el paisaje contiene rastros en conflicto).

```
Facts            →  Claims        →  Paisaje cognitivo  →  Decisión
(percepción del     (rastros          (percepción           (camino
 entorno)            individuales)     colectiva)             colectivo)
```

**Precisión arquitectónica obligatoria:** el paisaje **no es una nueva
sección del `LearningState`**. Es una *proyección de lectura* sobre la
sección `claims` (su subconjunto vigente). El RFC-0003 prohíbe secciones
nuevas, y esta definición lo respeta: el paisaje es una vista, no un
almacén. Una implementación que lo materialice como almacén separado viola
simultáneamente esta definición y aquella prohibición — sería una segunda
fuente de verdad.

## La analogía con la colonia, completa

| Colonia | UPAO-MAS-EDU |
|---------|--------------|
| entorno físico | facts (percepción del entorno) |
| feromona depositada | claim vigente |
| intensidad de la feromona | confianza del claim |
| refuerzo del rastro | validación positiva (Validar) |
| evaporación | supersesión / decaimiento de confianza |
| paisaje de feromonas | paisaje cognitivo (claims vigentes) |
| camino colectivo que emerge | decisión pedagógica |
| física del mundo | Kernel (invariantes y transiciones) |

## Definición operacional (criterios verificables)

El sistema exhibe inteligencia de enjambre —en el sentido definido— si y
solo si:

| # | Criterio | Cómo se verifica |
|---|----------|------------------|
| E1 | Ninguna capacidad referencia a otra | inspección estática del diseño y del código (P3) |
| E2 | En decisiones con tensión, la decisión no es atribuible a una capacidad única | trazas de deliberación en el estado |
| E3 | Las mismas reglas producen secuencias observadas distintas ante estudiantes distintos | comparación de sesiones sin cambio de configuración |
| E4 | La influencia de una señal cambia con la evidencia validada | evolución medible de confianzas y del student model |
| E5 | El silencio o error de una capacidad degrada la calidad, jamás la consistencia | separación razonamiento/consistencia (RFC-0004 §2) |
| E6 | Toda decisión es derivable del paisaje vigente en su momento | reconstrucción del paisaje desde el estado (vigencias + INV-6) y replay |

Estos seis criterios son la vara del RFC-0006 y, después, del capítulo de
Resultados: no se afirma el enjambre — se demuestra.

## Anti-definición: lo que NO cuenta como enjambre

- **N muestras del mismo modelo promediadas** (self-consistency): no hay
  perspectivas heterogéneas ni medio compartido; es reducción de varianza.
- **Un orquestador que consulta agentes y decide**: cognición central con
  escenografía de agentes.
- **Handoffs conversacionales**: coordinación directa — prohibida
  (RFC-0001, alt. 3).
- **Un sistema de reglas con votación** (agente A + agente B + agente C →
  `vote()` → resultado): una votación puntual sin un estado compartido que
  evolucione no construye conocimiento colectivo — cuenta opiniones. Aquí
  la coordinación es un paisaje que evoluciona; la votación, cuando
  ocurre, es el episodio, no el sistema.
- **Deliberaciones simuladas**: prohibidas por P7.

Si el RFC-0006 produjera cualquiera de estas cosas con otro nombre, habrá
fallado esta definición.

## Honestidad académica: dónde nos apartamos del enjambre clásico

El enjambre canónico tiene miles de agentes homogéneos y simples; nosotros
tenemos ocho capacidades heterogéneas y cognitivamente ricas, y una
deliberación explícita que ninguna colonia tiene. La defensa es de
principio, no de población: **lo definitorio del enjambre en la literatura
no es cuántos agentes hay, sino cómo se coordinan** — estigmergia,
autoorganización, retroalimentación, ausencia de control central. Y la
deliberación explícita no es una traición al enjambre: es la extensión que
exige la ciencia — un enjambre clásico no puede explicarse a sí mismo; el
nuestro está obligado a hacerlo (P6, P7).

Formulación para la sustentación: *no afirmamos haber construido una
colonia de hormigas; afirmamos haber construido un sistema cuyas
decisiones se coordinan por los mismos principios — rastros en un medio
compartido, refuerzo por resultados, ausencia de cognición central — y
que, a diferencia de una colonia, puede demostrar cada decisión entrada
por entrada.*

## Hipótesis operacional

> **La hipótesis arquitectónica de UPAO-MAS-EDU es que la calidad de la
> adaptación pedagógica mejora cuando las decisiones se derivan de un
> paisaje cognitivo construido colectivamente sobre evidencia validada,
> en lugar de provenir de un único agente o de una votación aislada.**

No se afirma: se somete a prueba. Sus instrumentos ya existen en el plano —
los criterios E1–E6, las métricas de la `base` (RFC-0004), la evolución de
confianzas (RFC-0007) — y su grupo de control también: el **Legacy Runtime
archivado**, cuyo pipeline de agente único es exactamente el término de
comparación que esta hipótesis necesita. Si las decisiones derivadas del
paisaje no superan a las del pipeline, la hipótesis se refuta — y la
arquitectura está construida para poder medirlo.

## Consecuencia directa para el RFC-0006

**El consenso no es el enjambre: es su episodio agudo.** La coordinación
estigmérgica adaptativa opera continuamente — el paisaje se construye, se
refuerza y decae —; la deliberación se convoca solo cuando el paisaje
contiene rastros en conflicto (P8). El RFC-0006 debe diseñar **ambas
cosas**: la dinámica del paisaje (cómo la confianza se refuerza y decae
con la evidencia — donde convergen Knowledge Claims, H4 y H6) y el
episodio (la regla de resolución, la política de aplazamiento y
reapertura, y H7). Un RFC-0006 que solo diseñe la votación habrá
construido coordinación distribuida sofisticada — exactamente lo que esta
página existe para impedir.

## Registro — H8: Landscape Metrics

Propuesta del tesista en la aceptación de este documento (REGISTRADA, no
incorporada): ahora que el paisaje existe como proyección lógica, emergen
métricas propias — densidad (claims vigentes), estabilidad (cambio entre
transiciones), conflicto (claims incompatibles), entropía (grado de
incertidumbre), tiempo medio de estabilización. **Se evalúan en el
RFC-0007** (son métricas del paisaje, no del consenso), como candidatas a
instrumentos de la hipótesis operacional.

## Cierre

> **En UPAO-MAS-EDU, la inteligencia de enjambre no se define por el
> número de agentes ni por el algoritmo de consenso utilizado. Se define
> por la existencia de un conocimiento colectivo que evoluciona mediante
> evidencia, retroalimentación y validación, y del cual emergen las
> decisiones pedagógicas del sistema.**

**Esta definición constituye el criterio normativo con el que se evaluará
el RFC-0006. Cualquier mecanismo de consenso que no satisfaga los
criterios E1–E6 no implementa la noción de inteligencia de enjambre
adoptada por UPAO-MAS-EDU, independientemente del algoritmo utilizado.**
