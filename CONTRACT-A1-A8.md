# CONTRACT-A1-A8 — Formalización computable de la Confianza Efectiva

> Documento de trabajo temporal (RFC-0006/1A). No es un RFC ni un ADR
> — no introduce vocabulario nuevo, solo traduce RFC-0006 §1 (los
> axiomas A1-A8, ya normativos) a un contrato que se pueda testear
> directamente. Una vez absorbido por el código y los tests de
> RFC-0006/1, este documento puede eliminarse.
>
> **Cero código en este documento.** Esto es el "qué debe cumplirse",
> no el "cómo" — el cómo (la función `f` ilustrativa de RFC-0006 §1)
> se decide al implementar, dentro de lo que este contrato permite.

## Firma única

```
ce : (claim: ClaimEntry, estado: LearningState, politica: Politica) -> Decimal
```

Todo lo demás en este documento restringe esta firma. Ninguna otra
entrada, ninguna otra salida.

---

## A1 — Acotación

**Enunciado (RFC-0006 §1):** `ce ∈ [0, 1]`.

- **Entrada:** cualquier `(claim, estado, politica)` válido según A2-A8.
- **Salida:** `Decimal` tal que `Decimal("0") <= ce <= Decimal("1")`,
  **siempre**, sin excepción — ni un solo camino de la función puede
  devolver fuera de rango.
- **Propiedad demostrable:** ∀ input válido, la salida está acotada.
  No es "normalmente acotada" — es una invariante dura, igual que
  INV-7 ya exige para la confianza de resolución.
- **Caso borde:** un claim en el límite exacto (`confianza_declarada`
  = `Decimal("0")` o `Decimal("1")`) no puede desbordar por refuerzo
  (no puede superar 1) ni por decaimiento (no puede bajar de 0) —
  la función debe saturar, no truncar con error.
- **Test asociado:** para un conjunto fijo de escenarios reales
  (Postgres real) que cubran refuerzo extremo, decaimiento extremo y
  los dos límites de `confianza_declarada`, verificar `0 <= ce <= 1`
  en cada uno.

## A2 — Anclaje

**Enunciado:** en el estado en que el claim fue aplicado, `ce` =
confianza declarada.

- **Entrada:** `claim`, y `estado` reconstruido exactamente en
  `estado.transicion == claim.id.transicion` (el instante inmediato
  después de que el reducer registró el claim — antes de cualquier
  transición posterior).
- **Salida:** `ce(claim, estado, politica) == claim.confianza`
  (igualdad `Decimal` exacta, no aproximada — ADR-0001 §4 ya exige
  exactitud decimal en todo el proyecto).
- **Propiedad demostrable:** en el instante de origen, `ce` no añade
  ni quita nada sobre lo declarado — el álgebra empieza donde el
  reducer lo dejó.
- **Caso borde:** un claim que nace ya supersedido en la MISMA
  transición no puede ocurrir (INV-3/la reducción no lo permite) — no
  hace falta cubrirlo.
- **Test asociado:** reconstruir el estado justo en la transición de
  origen del claim, calcular `ce`, comparar con `==` estricto contra
  `claim.confianza`.

## A3 — Determinismo y pureza

**Enunciado:** `ce` es función de `(claim, estado, política
versionada)` y de nada más. Computarla jamás invoca un modelo, un
reloj o el azar.

- **Entrada:** el triple exacto de la firma — ningún parámetro
  implícito (sin variables de entorno, sin `datetime.now()`, sin
  `random`, sin cliente HTTP/LLM).
- **Salida:** el mismo valor, bit a bit, para el mismo triple, sin
  importar cuándo ni cuántas veces se invoque.
- **Propiedad demostrable:** pureza funcional total — mismo criterio
  que ya rige `reconstruir()` (ADR-0007: "el LLM nunca es la fuente de
  un dato que el sistema ya determinó").
- **Caso borde:** llamar la función dos veces seguidas, con reloj de
  pared real avanzando entre medio (`time.sleep` real en el test), con
  el mismo `(claim, estado, politica)` — debe dar resultado idéntico.
- **Test asociado:** (a) llamar dos veces con el mismo input, separadas
  por una espera real, comparar igualdad exacta; (b) test **estructural**
  (mismo patrón que `test_BLUEPRINT_reglas_de_importacion.py` y el test
  de `reconstruccion.py` que prohíbe importar `runtime.domain`): el
  código fuente de `confianza.py` no puede importar `datetime` (salvo
  tipos, nunca `.now()`), `random`, ni ningún cliente LLM/HTTP.

## A4 — Tiempo lógico

**Enunciado:** `ce` solo puede cambiar entre estados por transiciones
aplicadas; toda noción de "edad" se mide en transiciones — nunca en
reloj de pared.

- **Entrada:** `estado.transicion` (ya existe, es el índice del tiempo
  lógico — A4 no pide ningún campo nuevo).
- **Salida:** cualquier cómputo interno de "edad" usa exclusivamente
  `estado.transicion - claim.id.transicion` (resta de enteros).
- **Propiedad demostrable:** `ce(claim, estado, politica)` es
  invariante ante el reloj de pared real — solo cambia si
  `estado.transicion` (o el contenido causal, A7) cambia.
- **Caso borde:** `estado.transicion == claim.id.transicion` → edad
  lógica = 0 (recién nacido, coincide con A2).
- **Test asociado:** calcular `ce` en un snapshot de estado, esperar
  con reloj real, recalcular `ce` sobre el MISMO snapshot (no una
  reconstrucción nueva) → debe ser idéntico. Ya cubierto en la práctica
  por el test de A3(a); aquí se enfatiza que la "edad" en concreto usa
  el índice, no un timestamp — verificable inspeccionando qué campos
  de `estado`/`claim` toca la función (test estructural adicional si
  se detecta algún campo de fecha real en `FactEntry`/`ClaimEntry` —
  auditar durante la implementación si existe alguno).

## A5 — Monotonicidad ante evidencia

**Enunciado:** una validación positiva en la cadena del claim no la
disminuye; una refutación no la aumenta; un fact contradictorio con su
respaldo no la aumenta.

- **Entrada:** dos estados `E1`, `E2` donde `E2` es `E1` más UNA
  transición que agrega evidencia en la cadena causal del claim
  (validación positiva, validación negativa, o fact contradictorio).
- **Salida:** tres propiedades direccionales distintas, no una sola:
  1. validación positiva nueva → `ce(claim, E2) >= ce(claim, E1)`
  2. validación negativa (refutación) nueva → `ce(claim, E2) <= ce(claim, E1)`
  3. fact contradictorio con el respaldo → `ce(claim, E2) <= ce(claim, E1)`
- **Propiedad demostrable:** el signo del cambio en `ce` está
  determinado por el signo de la evidencia nueva — nunca al revés.
- **Caso borde — abierto, a decidir en la implementación, no aquí:**
  RFC-0006 no cubre evidencia **ambigua** (ni claramente positiva ni
  negativa). El contrato de este documento no exige un tercer
  comportamiento para ese caso — solo que ninguna de las tres
  propiedades de arriba se viole cuando SÍ hay evidencia claramente
  clasificable.
- **Test asociado:** tres tests, uno por dirección — construir un
  claim, aplicar la transición de evidencia correspondiente
  (`validar_decision` con veredicto positivo/negativo; un fact
  contradictorio real), comparar `ce` antes/después con la desigualdad
  correspondiente. Postgres real, secuencia real de reducers — no un
  mock de "evidencia positiva".

## A6 — Decaimiento sin refuerzo

**Enunciado:** sin evidencia nueva en su cadena, `ce` es no-creciente
respecto de la edad lógica de su respaldo. Nada se refuerza
espontáneamente.

- **Entrada:** dos estados `E1`, `E2` (`E2` posterior a `E1` en
  transiciones) donde NINGUNA transición nueva toca la cadena causal
  del claim ni los facts de su asunto.
- **Salida:** `ce(claim, E2, politica) <= ce(claim, E1, politica)`.
- **Propiedad demostrable:** el paso del tiempo lógico, por sí solo
  (sin evidencia), nunca puede subir `ce` — complementa A5 (que cubre
  qué pasa CON evidencia).
- **Caso borde:** `E1 == E2` (cero transiciones adicionales) → `ce`
  debe ser exactamente igual, no decae "de golpe" sin que pase tiempo
  lógico.
- **Test asociado:** construir un claim, avanzar el estado con
  transiciones ajenas a su cadena y a su asunto (otro asunto por
  completo), verificar `ce` no-creciente en cada paso intermedio — no
  solo comparar el primero contra el último.

## A7 — Localidad causal

**Enunciado:** `ce` depende únicamente de la cadena causal del claim
(su respaldo hacia atrás; las decisiones y validaciones derivadas hacia
adelante) y de los facts de su asunto. Toda `ce` es explicable
exhibiendo esas entradas (P6).

- **Entrada:** el estado completo (`LearningState`), pero la función
  solo puede LEER el subconjunto: `claim.respaldo` (recursivo hacia
  atrás), las decisiones/validaciones que lo referencian (hacia
  adelante), y los facts cuyo `asunto` coincide.
- **Salida:** invariante ante cualquier cambio en el estado que quede
  FUERA de ese subconjunto.
- **Propiedad demostrable:** `ce(claim, estado, politica) ==
  ce(claim, estado_con_ruido_ajeno, politica)` para cualquier
  `estado_con_ruido_ajeno` que solo añada entradas de otros asuntos, no
  relacionadas causalmente.
- **Caso borde:** dos claims sobre asuntos totalmente distintos en el
  mismo estado — modificar el paisaje de uno no puede afectar el `ce`
  del otro. Este es, en los hechos, el mismo caso borde que A6 usa para
  su propio test, pero la propiedad que demuestra es distinta
  (localidad, no monotonicidad).
- **Test asociado:** calcular `ce` de un claim, añadir facts/claims de
  un asunto totalmente distinto al estado, recalcular `ce`, verificar
  igualdad exacta (no solo desigualdad — exactitud total).

## A8 — La vigencia domina

**Enunciado:** un claim supersedido sale del paisaje; ninguna `ce` lo
devuelve.

- **Entrada:** `calcular_confianza_efectiva()` opera **únicamente
  sobre claims vigentes** — la vigencia es una **precondición del
  llamador**, no un caso que la función misma valide, filtre o
  reporte. Un claim con `vigencia.superseded_por is not None` está
  **fuera del dominio de la función**, en el mismo sentido en que
  `sqrt(-1)` está fuera del dominio de una raíz cuadrada real: no es
  un input inválido que la función deba reconocer, es un input que
  nunca debería llegar — porque quien llama ya lo filtró.
- **Salida:** sin contrato. La selección/validación de qué claims son
  vigentes y participan en una comparación de `ce` pertenece a la
  mecánica de deliberación (`mecanica.py`, RFC-0006/3) — el mismo
  patrón que hoy ya usa `_propuestas_vigentes()` para filtrar antes de
  comparar. `confianza.py` no importa `mecanica.py` (ya es criterio de
  cierre de RFC-0006/1) y por tanto no puede imponerle nada a su
  llamador más allá de documentar la precondición. Un `assert` interno
  es aceptable como ayuda de desarrollo, pero **no es parte del
  contrato público** — no se testea como comportamiento observable.
- **Propiedad demostrable:** dentro de su dominio (claims vigentes),
  ningún claim supersedido puede intervenir en el cálculo — está
  garantizado por construcción, porque nunca es un input válido, no
  porque la función lo detecte y lo rechace.
- **Caso borde:** un claim vigente cuyo RESPALDO incluye un claim ya
  supersedido (la cadena causal pasa por una entrada no vigente) — A8
  restringe qué claims pueden ser el PRIMER argumento de `ce`, no qué
  puede aparecer dentro de la cadena causal que A7 recorre. Verificar
  que A7 sigue aplicando normalmente en ese caso.
- **Test asociado:** ninguno directo en `confianza.py` — todos los
  tests de Parte A construyen y usan exclusivamente claims vigentes;
  no existe un test que le pase un claim supersedido a `ce()`, porque
  eso sería testear un comportamiento fuera de contrato. La garantía
  de que un supersedido nunca llega a `ce()` se testea en RFC-0006/3,
  contra `mecanica.py` (el filtro real), no aquí.

---

## Resumen — decisiones (resueltas 2026-07-12)

1. **A5 — sin regla nueva.** "Evidencia ambigua" no es todavía un
   concepto del dominio (RFC-0006 solo habla de evidencia que valida,
   refuta o contradice) — definir un comportamiento para una cuarta
   categoría sería inventar semántica antes de que exista un caso de
   uso real. El contrato queda limitado a los tres casos normativos.
   Si en RFC-0006/3 aparece un caso real inclasificable, se abre su
   propia Engineering Review en ese momento — no se anticipa aquí.
2. **A8 — precondición del llamador, no excepción de `confianza.py`.**
   La vigencia se filtra ANTES de invocar `ce()`, en la mecánica de
   deliberación (RFC-0006/3) — no dentro de la función matemática.
   `confianza.py` no valida, no lanza `ValueError`, no conoce el
   ciclo de vida de un claim: opera sobre un dominio ya restringido a
   claims vigentes, por definición del contrato, no por chequeo en
   tiempo de ejecución. Esto mantiene `confianza.py` como un
   componente puramente matemático, independiente del ciclo de vida de
   los claims — esa independencia es, en sí misma, evidencia adicional
   de por qué "`confianza.py` no importa `mecanica.py`" (criterio de
   cierre ya existente de RFC-0006/1) es la decisión correcta.

## Resumen — lo que este documento NO decide (a propósito)

La forma concreta de `f` (RFC-0006 §1, "forma ilustrativa, no
normativa") — qué peso tiene cada refuerzo, qué curva de decaimiento,
qué tan rápido decae — es política versionada (Parte 0), no parte de
este contrato. Este documento solo fija qué debe ser cierto de `ce`
sea cual sea `f`; la política v2 elige una `f` concreta que lo
satisfaga.
