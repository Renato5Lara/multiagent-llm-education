# Taxonomía del Consenso en UPAO-MAS-EDU

- **Estado:** Aceptado (2026-07-10 — con la regla de oro del espacio de
  resultados y H9 registrada en la aceptación)
- **Gobernado por:** CONCEPT-0001 (criterios E1–E6), P5, P7, P8, P14,
  RFC-0003 (INV-7, INV-8, INV-12), RFC-0004

Este documento no diseña el consenso: clasifica sus situaciones. Si el
RFC-0006 encuentra un caso que esta taxonomía no describe, la taxonomía
se corrige primero.

## 1. Tipos de desacuerdo

El paisaje cognitivo puede contener tres situaciones distintas que el
lenguaje coloquial llama "desacuerdo". No deben tratarse igual:

**D1 — Desacuerdo interpretativo** (sobre la realidad). Dos claims de tipo
*interpretación*, vigentes e incompatibles, sobre el mismo aspecto:
*"el error es conceptual"* vs *"el error es de atención"*. Se resuelve por
peso de evidencia: gana la lectura mejor respaldada por facts.

**D2 — Desacuerdo prescriptivo** (sobre la acción). Dos claims de tipo
*propuesta*, vigentes y mutuamente excluyentes, para la misma decisión:
*avanzar* vs *reforzar*. Se resuelve por evidencia **y** política
pedagógica: qué se prioriza cuando ambas lecturas son legítimas.

**D3 — Insuficiencia** (incertidumbre). No hay claims incompatibles: hay
un paisaje demasiado débil — ninguna propuesta alcanza la confianza que la
decisión exige. No es un desacuerdo entre capacidades; es un desacuerdo
entre el paisaje y el umbral de decisión. Su salida natural no es
deliberar: es **obtener evidencia**.

**Regla de la raíz:** los desacuerdos prescriptivos suelen tener raíz
interpretativa (se proponen acciones distintas porque se lee la realidad
distinto). La deliberación ataca la raíz: se resuelve D1 antes que D2 —
resolver la acción con la realidad en disputa es votar a ciegas. (Esta
regla es, en sí misma, una política de orden: conecta con H7.)

**Tensión latente vs bloqueante.** No todo conflicto convoca deliberación.
Una tensión es **bloqueante** si afecta una decisión pendiente ahora;
es **latente** si el paisaje la contiene pero ninguna decisión la
necesita. Las tensiones latentes pueden vivir en el paisaje — son
información, no emergencia. Solo lo bloqueante se delibera (P8).

Mapa de las tensiones canónicas (RFC-0002 §4): *¿avanzar o reforzar?* es
D2 pura; *¿qué modalidad?* es D2 con raíz D1 (perfil histórico vs señales
de sesión); *¿dominó el objetivo?* es D1 pura.

## 2. Cuándo se convoca deliberación (y cuándo no)

Se convoca cuando se cumplen las tres condiciones a la vez:

1. existen ≥ 2 claims vigentes incompatibles sobre la misma pregunta o el
   mismo slot de decisión (D1 o D2);
2. la tensión es **bloqueante** — una decisión la está esperando;
3. la evidencia disponible no la disuelve sola — si un fact nuevo basta
   para que el autor de un claim lo supersede, no hubo nada que deliberar.

No se convoca cuando: hay propuesta única sin oposición (deriva directa,
INV-6); la tensión es latente; el caso es D3 (el remedio es evidencia, no
debate). Cada no-convocatoria es tan registrable como una convocatoria:
"decidió una capacidad sola porque nadie podía disentir" es parte de la
explicación (P6).

## 3. Qué significa "resolver"

**La deliberación selecciona; jamás crea.** Resolver es: aplicar la regla
de resolución sobre los claims participantes, aceptar uno (o un
subconjunto compatible), superseder los rivales, y registrar regla,
posiciones y **confianza de la resolución** (INV-7). El Kernel registra;
no opina (es física, no reina — P5).

Si la resolución correcta fuera una **síntesis** ("ni avanzar ni reforzar:
avanzar con andamiaje de refuerzo"), la deliberación no la redacta: la
síntesis es una nueva propuesta, y las propuestas las autoran capacidades.
El resultado de la deliberación puede ser *reconvocar* a una capacidad con
el paisaje enriquecido por las posiciones registradas — y la nueva
propuesta entra al proceso como cualquier otra. Autorizar al mecanismo a
crear contenido sería cognición central disfrazada (anti-definición,
CONCEPT-0001).

## 4. Cuándo se aplaza

Se aplaza (resultado `aplazada`, RFC-0003 §4.1) cuando la regla de
resolución no puede discriminar **y** existe un camino de evidencia:

- la deliberación registra **qué evidencia falta** (INV-7), y esa
  declaración es accionable — puede activar a quien la obtenga (una
  micro-actividad de Evaluar, una señal de sesión de Tutorizar). El
  aplazamiento es productivo: *"saber que no se sabe"* dispara la
  búsqueda.
- **Restricción pedagógica:** hay un estudiante esperando en la pantalla.
  Si la decisión no puede esperar el camino de evidencia, no se aplaza:
  se resuelve con la mejor confianza disponible como **decisión
  provisional** — que no es un concepto nuevo: es una decisión con
  confianza de resolución baja, que INV-12 ya obliga a validar y que
  Validar vigila con prioridad. El aplazamiento es para el sistema; la
  provisionalidad es para el estudiante.

## 5. Cuándo se "reabre" (nunca: se convoca de nuevo)

La historia es inmutable (INV-3, P14): una deliberación cerrada no se
edita. Lo que ocurre es una **nueva deliberación que referencia a la
anterior**, convocada por los mismos mecanismos de enrutamiento cuando:

- llega la evidencia declarada faltante por una `aplazada`;
- un claim participante de una `resuelta` es supersedido por nueva
  evidencia;
- aparece una nueva propuesta rival sobre el mismo slot;
- Validar refuta la decisión derivada (el veredicto negativo es un fact +
  claim nuevos que reconfiguran el paisaje).

La cadena `deliberación → deliberación'` es, ella misma, evidencia
longitudinal: muestra al sistema cambiando de opinión con razones.

## 5 bis. Regla de oro del espacio de resultados

> **Toda deliberación termina exactamente en uno de estos resultados:
> (1) selección de una propuesta existente — resolución plena o
> provisional —; (2) declaración explícita de la evidencia que falta —
> aplazamiento —; (3) escalada a un humano. Nada más. Y en particular:
> jamás en la creación de una propuesta nueva.**

*Nota de reconciliación del arquitecto:* la formulación original del
tesista enumeraba tres salidas (selección, insuficiencia, provisional).
La decisión provisional no es un resultado distinto de la selección — es
una selección con confianza de resolución baja —, y faltaba la **escalada**,
que INV-7 y el RFC-0009 ya reconocen. Puede leerse también así: la
escalada es el aplazamiento cuyo camino de evidencia es una persona. El
espacio queda cerrado en tres salidas y una prohibición.

## 6. El papel de las hipótesis registradas

| Hipótesis | Lugar en esta taxonomía |
|-----------|--------------------------|
| Knowledge Claim (RFC-0002) | Ya es la sustancia: se delibera sobre afirmaciones (INV-8) y las decisiones derivan de las aceptadas. El RFC-0006 formaliza su adopción semántica. |
| H4 — Intent → Resolution → Execution | La cadena ya existe: claims-propuesta (intención) → deliberación resuelta (resolución) → decisión + entrega (ejecución). El RFC-0006 decide si merece nomenclatura propia. |
| H6 — Clases de intent | Se corresponde con D1/D2: lo interpretativo se resuelve por evidencia; lo prescriptivo por evidencia + política. La taxonomía confirma que el consenso NO debe tratarlas igual — H6 llega al RFC-0006 fortalecida. |
| H7 — Scheduler Policy | La regla de la raíz (D1 antes que D2) es un caso de política de orden; el resto de H7 (orden entre intents válidos) se evalúa junto a ella, bajo la restricción P12 ya registrada. |
| H8 — Landscape Metrics | El conflicto y la entropía del paisaje son exactamente lo que las condiciones de convocatoria (§2) leen; las métricas pueden parametrizar umbrales — siempre como función determinista del estado. Evaluación en RFC-0007. |

## 7. Verificación

- Contra las **tensiones canónicas**: las tres quedan clasificadas (§1) y
  ninguna exigió un tipo de desacuerdo nuevo.
- Contra **E1–E6** (CONCEPT-0001): nada en esta taxonomía introduce
  referencias entre capacidades (E1), atribución unipersonal en tensión
  (E2), secuencias codificadas (E3), señales inmunes a la evidencia (E4),
  dependencia de una capacidad (E5) ni decisiones no derivables del
  paisaje (E6).
- **Conceptos que surgieron y NO requieren enmendar RFCs**: tensión
  latente/bloqueante (propiedad del paisaje), "la deliberación selecciona,
  jamás crea" (corolario de P5 + anti-definición), decisión provisional
  (caso de INV-12 con confianza baja), reapertura como nueva deliberación
  enlazada (corolario de INV-3/P14). Todos son vocabulario nuevo sobre
  estructura existente — señal de que el modelo aguanta.

## Registro — H9: Decision Debt

Propuesta del tesista en la aceptación (REGISTRADA, no incorporada): toda
decisión provisional o `pendiente-de-validación` constituye una **deuda**:
el sistema "debe" revisarla hasta saldarla (validación, refutación o
expiración explícita). INV-12 ya la materializa parcialmente; la hipótesis
es si la deuda merece representación y métricas propias (deuda abierta,
edad media, tasa de pago) y si cruza sesiones. **Se evalúa en el RFC-0005**
(¿la deuda viaja por memoria?) **y el RFC-0007** (métricas).

## Consecuencia para el RFC-0006

El RFC-0006 hereda una agenda cerrada: (1) la dinámica del paisaje
(refuerzo/decaimiento de confianza con la evidencia validada); (2) las
reglas de resolución por tipo (D1 por evidencia, D2 por evidencia +
política pedagógica); (3) los umbrales de convocatoria y de insuficiencia
(D3); (4) la política de orden (regla de la raíz + H7, bajo P12); (5) el
veredicto sobre Knowledge Claims, H4 y H6. Todo ello juzgado contra E1–E6.
