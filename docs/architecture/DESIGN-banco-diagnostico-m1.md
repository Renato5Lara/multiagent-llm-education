# Especificación del banco de diagnóstico de M1 (Pre/Post-Test, versión 4)

- **Estado:** Propuesta — decisiones de fondo, las cuatro decisiones de
  diseño previas a los ítems (§11) y los **ocho ítems** (diseñados y
  aprobados uno a uno; su texto no vive aquí, §13 fija su mapeo) confirmados
  por el tesista (2026-09-19); sin implementar. Toda cifra estadística de este documento es **modelada**,
  no observada en estudiantes.
- **Fecha:** 2026-09-19 (decisiones de implementación: 2026-09-20)
- **Pregunta que responde (y que ningún otro documento responde):** ¿qué
  debe cumplir una versión del banco `IS301` para poder emitir el claim de
  dominio provisional de M1 y, con él, la suficiencia para comenzar M2?
- **No implica:** cambios al runtime (`backend/runtime/`), a ningún
  RFC/ADR, a θ, a Wilson, a `errores < 2` ni a `calibrar_confianza_nueva`.
  No modifica el esquema de BD (usa columnas existentes). **No escribe las
  preguntas**: fija el contrato que cada pregunta debe cumplir.

## Documentos relacionados

- `Documentos de tesis/Deliberacion - Cruce Auditoria 01 x Auditoria 02.md`
  (fuera del repo; copia canónica de la deliberación curricular): 8 módulos,
  32 conceptos, D1 (M1), D2 (M2), 2C-3.16, reglas C1-C4. **Fuente del
  catálogo de M1 y de los tres pilares del módulo.**
- `docs/architecture/ADR/ADR-0010-asunto-desde-modulo.md`: `asunto` =
  slug del título del módulo.
- `docs/architecture/ADR/ADR-0013`, `ADR-0015`, `ADR-0016`: calibración de
  confianza y política v2 (θ = 0.5, δ = 0.10).
- `docs/architecture/DESIGN-orientar-ruta-completa.md`: desbloqueo por
  objetivo (`avance_por_objetivo`).
- `backend/app/data/knowledge_test_bank.py` (banco vigente, v3) y
  `backend/app/services/knowledge_test_service.py`.

Las deliberaciones D4-D8 que originan este documento se realizaron en
sesión; **este documento es su primer registro escrito**. La deliberación
canónica de la carpeta de tesis no se actualiza aquí.

---

## 1. Decisiones de origen (confirmadas)

| # | Decisión | Efecto en el banco |
|---|---|---|
| D4-Q1 | El pre-test produce un claim de dominio sobre M1, "dominio provisional de entrada" | Todo ítem evidencia M1; el claim se emite con el conjunto completo |
| D4-Q2 | Conserva su papel de "antes" natural de Validar para M1 | El hecho a nivel de objetivo mantiene su forma (`competencia` + `items_incorrectos` + `items_totales`) |
| D4-Q3 | "Avanzar" = suficiencia para comenzar M2 en paralelo (M1 sigue disponible; no acredita dominio; se calcula al crear la ruta) | "Ejecutar" (M1.4 + M1.5) condiciona el desbloqueo |
| D5 | El pre-test evalúa **M1 solamente**; no hay ítems de M2 | `module_number = 1` en todos los ítems |
| D6 | Cobertura **por funciones** (concebir, representar, ejecutar); M1.6 fuera del claim | Ver §3 |
| D7 | **n = 8**, distribución mínima **(2, 2, 4)** | Ver §3-§4. **Diseño adoptado, a validar con datos reales; no "estadísticamente óptimo"** |
| D8 | El post-test se conserva; **mismo instrumento** (misma versión); se habilita al **completar M1** | Una sola versión de banco para ambos; la puerta es un cambio de código futuro (§8) |

## 2. Semántica del instrumento

- El claim `dominio(M1)` significa **"dominio provisional de entrada de M1
  en sus tres funciones nucleares: concebir la solución, representarla y
  ejecutarla en Python"**, y **nombra que excluye M1.6**.
- La **suficiencia para comenzar M2** es un subconjunto del claim
  (función "ejecutar"). No se declara como dominio.
- El runtime emite `dominio(M1)` con cualquier evidencia que reciba. **La
  protección contra sobreafirmar el claim es una propiedad del banco, no
  del runtime**: no puede existir una versión válida que produzca el claim
  sin haber observado las tres funciones (§7, invariantes).

## 3. Cobertura y estructura

Los tres pilares provienen de la descripción aprobada de M1 (D1): diseñar la
solución antes de escribirla, representarla de forma comunicable y
traducirla en un programa ejecutable con resultado observable.

| Función | Conceptos | Bloom del concepto (D1) | Ítems mínimos |
|---|---|---|---|
| **Concebir** | M1.1 Algoritmo; M1.2 Pensamiento computacional | 2; 3 | **2** |
| **Representar** | M1.3 Representación de algoritmos | 2 | **2** |
| **Ejecutar** | M1.4 Estructura y sintaxis; M1.5 `print` | 3; 3 | **4** |
| *(fuera del claim)* | M1.6 Qué es un lenguaje | 2 | 0 |
| **Total** | | | **8** |

### Por qué esa distribución (modelado)

Supuestos: ítems de 4 opciones; quien no sabe responde al azar; respuestas
independientes; "descuido" del 5 % o 10 % en quien sí sabe.

- Bajo `errores < 2`, una función con **un solo ítem nunca puede bloquear**:
  cobertura ≠ detectabilidad. Probabilidad de detectar una laguna
  sistemática con k ítems: k=2 → 0.56; k=3 → 0.84; k=4 → 0.95.
- Con n = 8 total, repartir (3, 2, 3) deja pasar una laguna en "ejecutar"
  con probabilidad 9.7 %; repartir **(2, 2, 4)**, 3.4 %. La distribución
  protege el desbloqueo más que el `n` total.
- n = 8 es el primer `n` donde **un error** alcanza θ = 0.5 (Wilson 0.53).
  Con n ≤ 6, un estudiante con un error queda "dominado" pero sin decisión
  derivada.
- El falso bloqueo de quien sí sabe crece con `n` (`errores < 2` es un
  conteo absoluto): n = 8 → 6 % (descuido 5 %) o 19 % (10 %). Su costo es
  bajo: M1 sigue disponible y M2 solo se abre en paralelo.
- **Limitación reconocida:** con (2, 2, 4), Concebir y Representar detectan
  solo ~56 % de las lagunas. El claim es *provisional* y solo "ejecutar"
  condiciona M2; la redacción del claim debe decirlo.

## 4. Reglas de evidencia

1. **Un ítem cuenta una vez** en `items_totales`, aunque observe dos
   conceptos. La evidencia compartida ahorra conceptos, no `n`.
2. **Atribución asimétrica.** El **éxito** en un concepto dependiente
   evidencia también al prerrequisito (Algoritmo → Representación;
   Sintaxis → `print`); el **fallo** no se atribuye automáticamente.
3. **Nivel de Bloom.** `bloom_level` es **obligatorio en todos los ítems de
   la versión 4** (se exige por invariante, §7; la columna sigue siendo
   nullable y ningún consumidor del API o del servicio lo lee). El
   `bloom_level` de un ítem debe ser ≥ al del concepto al que se atribuye su
   éxito (D1). Un ítem de comprensión no evidencia un concepto de Aplicar.
   Para **atribuir un fallo**, conviene que sea igual al del concepto: un
   ítem de nivel superior (p. ej. depuración, Bloom 4, sobre M1.4, Bloom 3)
   es válido, pero su fallo es menos atribuible.
4. **Estructura mínima por función:**
   - *Concebir (2):* un ítem **Bloom 3 aplicado** (pensamiento
     computacional; su éxito implica Algoritmo) y un ítem **Bloom 2** de
     Algoritmo (su fallo sí se atribuye a M1.1).
   - *Representar (2):* dos ítems, uno en **pseudocódigo** y otro en
     **diagrama de flujo**, réplicas de un mismo concepto (D6: no hay
     diferencia pedagógica demostrable entre notaciones). Formato adoptado:
     **opción múltiple de 4 alternativas donde cada alternativa es una
     representación algorítmica completa y verificable** (pseudocódigo o
     diagrama de flujo), no una descripción de lo que debería contener. El
     ítem plantea un problema o algoritmo descrito y pide elegir la
     representación que le corresponde. El diagrama de flujo se expresa en
     **notación textual** (nodos y flechas por línea): el esquema del ítem
     es solo texto. **Condición:** requiere renderizado multilínea de las
     opciones (§8); hasta entonces estos ítems no pueden servirse.
   - *Ejecutar (4):* al menos **un ítem que observe sintaxis sin depender
     de `print`** (su fallo se atribuye a M1.4) y al menos **uno a nivel
     de programa** (su éxito implica M1.4 y M1.5).
5. Ningún ítem se atribuye a M1.6 ni a conceptos de M2 o posteriores.
6. Distractores: cada distractor debe evidenciar **un único** error
   conceptual real y distinto dentro del ítem (práctica vigente del banco).
7. **Posición de la respuesta correcta.** Las opciones **no se barajan** al
   servirse, y en v3 `correct_index` es 0 en 8 de 12 ítems y 1 en 4 (nunca 2
   ni 3): un patrón predecible que rompe el supuesto de azar del 25 % con que
   se modelaron las cifras de §3. **Objetivo de diseño para v4: 2 respuestas
   correctas en cada posición (0, 1, 2 y 3) entre los 8 ítems.** Es un
   objetivo, no una obligación rígida: si un ítem pedagógicamente mejor exige
   desviarse, se consulta al tesista antes de hacerlo.
8. **Criterio de revisión de calidad (no invariante).** La opción correcta no
   debería ser sistemáticamente la más larga ni la más corta del ítem; se
   revisa ítem por ítem como señal de que la longitud no delata la respuesta.
9. **No reutilizar literalmente cadenas ni fragmentos de código entre ítems.**
   Una cadena repetida (p. ej. el mismo texto bien escrito en un ítem y mal
   escrito en otro) permite resolver por comparación entre ítems. Se
   comprueba en la revisión transversal. La dependencia local que queda,
   inevitable porque el único código de M1 es `print`, es la de §9.9.

### Convención textual del diagrama de flujo (adoptada en el ítem de "representar" con diagrama)

| Elemento | Notación |
|---|---|
| Inicio y fin | `( texto )` |
| Acción o proceso | `[ texto ]` |
| Entrada o salida de datos | `/ texto /` |
| Sentido del flujo | `↓`, en una línea sola entre dos nodos |

Reglas: un nodo por línea; lectura de arriba abajo; sin sangría; todo diagrama
parte de `( Inicio )`; **sin decisiones ni repeticiones** en M1 (son de M4 y
M5); la leyenda de símbolos va **dentro del enunciado**, para que el ítem mida
interpretación y no memoria de formas. Se descartó una notación horizontal en
una sola línea con `→` (no depende del renderizado multilínea, pero el texto
se parte sin control). Al validar el frontend, comprobar que `↓` se ve bien
en la fuente usada.

## 5. Contrato técnico del banco (verificado contra el código)

| Aspecto | Hecho verificado | Consecuencia para v4 |
|---|---|---|
| Identidad del ítem | `_question_id` = `uuid5(curso, versión, topic, order)` (`knowledge_test_bank.py:567`). **No** usa `module_number` | La clave única es **(topic, order)**. Un par repetido genera el mismo ID y rompe la siembra |
| `module_number` | CHECK 1-9 (`models/knowledge_test.py`) | Todos los ítems llevan **1** |
| Opciones | 4 por ítem (test vigente) | 4 opciones, un solo `correct_index` |
| `difficulty`, `bloom_level` | `String(20)` / `Integer` nullable | Se conservan; `bloom_level` es **obligatorio en v4** (regla §4.3), exigido por invariante y no por esquema |
| Renderizado de un ítem (`KnowledgeTest.tsx`) | El **enunciado** usa `whitespace-pre-line` + fuente monoespaciada: conserva saltos de línea pero **colapsa la sangría**. Las **opciones** se muestran en un `<span>` normal: **los saltos de línea se aplanan** y no hay monoespaciado | Las alternativas multilínea de "representar" exigen un ajuste de frontend (§8). Hallazgo colateral: la sangría de los ítems de v3 con código ya se pierde |
| Versión | `BANK_VERSION = 3`; siembra idempotente al arrancar (`main.py:122`); versiones viejas quedan `is_active` y solo se sirve la vigente | `BANK_VERSION = 4`; filas nuevas; **no se toca ninguna fila anterior** |
| Intentos | Único `(student, course, kind)`; guardan `bank_version` y `question_order` | Los intentos históricos permanecen íntegros |
| Metadatos función/concepto | El modelo **no tiene** columna para ello | Se llevan **sin cambio de esquema** en un diccionario clave `(topic, order)` en el módulo del banco, como ya hace `MENTAL_MODELS_BY_COMPETENCY` |
| Modelos mentales | `mental_model_for`/`MENTAL_MODEL_CATALOG` **no tienen consumidor** fuera del archivo del banco (su consumidor declarado, el agente evaluador, fue retirado, ADR-0011) | **Decisión M (tesista, 2026-09-20): v4 no declara modelos mentales.** Cada ítem lleva `mental_models = {}`; no se crean entradas de catálogo. La misconception de cada distractor se documenta como comentario en el banco |

### Efecto sobre el defecto de atribución original

`submit_attempt` registra un hecho global con **todos** los ítems bajo el
primer objetivo (`_evidencia_global`). Con un banco donde todo ítem es de M1,
esa celda **es** la evidencia de M1 por construcción: el error de atribución
que motivó esta línea de trabajo desaparece **sin modificar `submit_attempt`**.

## 6. Auditoría de `COMP-*`

`topic` lleva la competencia cognitiva (COMP-0..5). Debe seguir siendo una
COMP: `compute_competency_profile` **ignora** los `topic` que no estén en
`COMPETENCY_LABELS`, y `runtime_bridge` los usa para excluir asuntos COMP de
los temas mostrados al estudiante.

| COMP | Etiqueta / prioridad | Qué medía en v3 | Encaje candidato con M1 |
|---|---|---|---|
| COMP-0 | Comprensión del problema · crítica | Datos y entrada→proceso→salida | **Concebir** |
| COMP-1 | Comprensión computacional · alta | Variables y tipos (contenido de M2) | Sin contenido natural en M1 |
| COMP-2 | Interpretación de código · crítica | Leer un fragmento | **Representar** (interpretar una representación) y **Ejecutar** (leer estructura). Extensión semántica de la etiqueta: *decisión pendiente* |
| COMP-3 | Simulación mental · crítica | Trazar una ejecución | **Ejecutar** (predecir salida con `print`) |
| COMP-4 | Construcción algorítmica · alta | Ordenar pasos | **Concebir** |
| COMP-5 | Razonamiento computacional · media-alta | Depurar un error | **Ejecutar** (detectar un error de sintaxis) |

### Hallazgos de la auditoría

1. **Cada COMP usada debe tener ≥ 2 ítems.** El runtime registra un hecho por
   `topic`. Con 1 solo ítem, `errores < 2` es siempre verdadero: un ítem
   **fallado** produciría `dominada = True` con confianza 0. Es ruido
   semántico, no una decisión, pero se evita exigiendo ≥ 2 por COMP usada.
2. **Con n ≤ 2 por COMP, esos hechos son inertes bajo θ** (fuerza máxima
   0.34): ya ocurría en v3 y no cambia.
3. **El perfil por competencia omite** las COMP sin ítems; la UI recorre la
   lista devuelta. Con 4 COMP usadas el perfil mostrará 4.
4. **Las 36 filas históricas** `pretest_competency_profile` y las 26 de
   `knowledge_assessment` no se reinterpretan.

### Asignación adoptada

Respeta §4, `(topic, order)` único y ≥ 2 ítems por COMP usada. El criterio
de la elección es **cubrir las funciones de M1**, no mantener la cobertura
uniforme del perfil histórico de seis competencias.

| Función | Ítems | COMP | `order` (posición de servicio) |
|---|--:|---|---|
| Concebir | 2 | COMP-0 × 2 | 0, 1 |
| Representar | 2 | COMP-2 × 2 | 2, 3 |
| Ejecutar | 4 | COMP-5 × 2 y COMP-3 × 2 | COMP-5: 4, 5; COMP-3: 6, 7 |

**Decisión O = B (tesista, 2026-09-20): `order` es la posición de servicio
global (0 a 7), única en todo el banco**, y no un índice por competencia. Se
aprobó cambiar así los `order` que el diseño había fijado en 0 y 1 por
competencia (ítems 3 a 8), para que `get_bank_questions` (que no se modifica)
sirva los ítems en una secuencia determinista: **1, 2, 3, 4, 7, 8, 5, 6**
(números de ítem). Motivo: el ítem 7 (sintaxis sin `print`) debe servirse antes
que los ítems 5, 6 y 8, que muestran `print("...")` correcto (§9.9). `(topic,
order)` sigue siendo único, y `order` solo interviene en el ID del ítem, en el
orden de servicio y en una clave de modelos mentales que v4 no usa.

Consecuencia declarada y aceptada: **COMP-1 y COMP-4 dejan de medirse** en
v4; el perfil por competencia mostrará cuatro. Las filas históricas no se
reinterpretan, y **no se comparan competencias entre versiones del banco**.

### Cláusula de COMP-2 (alcance ampliado, significado intacto)

COMP-2, *Interpretación de código*, **mantiene su significado y su etiqueta**.
Su alcance se amplía **explícitamente** para incluir la interpretación de
**representaciones algorítmicas** (pseudocódigo y diagrama de flujo en
notación textual) **cuando corresponda a la función "representar" de M1**.
No se convierte en una competencia genérica de interpretación visual.

- **La etiqueta no puede cambiar:** `COMPETENCY_LABELS[COMP_2]` se normaliza
  a un `asunto` del runtime (`normalizar_asunto`), y renombrarla alteraría
  ese identificador.
- Efecto aceptado: el estudiante verá el ítem de pseudocódigo o diagrama
  bajo la etiqueta "Interpretación de código".

## 7. Invariantes verificables (tests requeridos)

Cada test debe citar la norma de este documento que implementa:

1. Hay exactamente **8** ítems activos de la versión 4 (§3).
2. Todos con `module_number = 1` (D5).
3. Cada ítem tiene función, concepto(s) y `bloom_level` en la tabla de mapeo
   (§13), y esa tabla no tiene ítems ni claves de más ni de menos que el banco (§5).
4. Conteo por función ≥ (2, 2, 4) (§3), calculado desde la tabla de mapeo.
5. Ejecutar contiene ≥ 1 ítem con la etiqueta `sintaxis_sin_print` y ≥ 1 con
   la etiqueta `nivel_programa` (§4, §13). Las etiquetas solo aparecen en
   ítems de Ejecutar.
6. Ningún ítem atribuido a M1.6 ni a M2+ (§4).
7. `(topic, order)` único y `order` **global único** en 0 a 7 (§5, §6, §13).
8. Cada `topic` usado pertenece a `COMPETENCY_LABELS` y tiene ≥ 2 ítems (§6).
9. `bloom_level` **no nulo** en todos los ítems y ≥ Bloom del concepto
   atribuido (§4.3).
10. 4 opciones y un `correct_index` válido por ítem.
11. Los `topic` usados son exactamente COMP-0, COMP-2, COMP-3 y COMP-5, con
    2 ítems cada uno (asignación adoptada, §6).
12. Actualizar el contrato vigente de `tests/test_knowledge_test.py`
    (`modules == {1, 2, 4}` → `{1}`; conteos ligados a `len(QUESTION_BANK)`).
13. La secuencia de servicio (orden creciente de `order`) es, por ítem,
    1, 2, 3, 4, 7, 8, 5, 6 (§6, §9.10).
14. Con `white-space: pre-line` (colapsar espacios y conservar saltos de
    línea), ninguna pareja de opciones de un mismo ítem se ve igual (§8,
    decisión T2).

El reparto de `correct_index` (§4.7) y el criterio de longitud (§4.8) son
**objetivos de diseño con revisión manual**, no invariantes automáticos.

Los ítems de "representar" (§4.4) se revisan además con una lista de
comprobación de diseño, no automatizable: cada alternativa es una
representación completa y verificable, y exactamente una corresponde al
algoritmo descrito.

## 8. Compatibilidad y contratos que no deben romperse

| Contrato | Regla |
|---|---|
| Reconciliador (`reconciliar_legacy_runtime.py`) | Formato de claves `runtime-evidencia-pretest[-objetivo]:…` y campos del snapshot (`items_*`, `modalidad_estudiante`, `clasificacion`, `objetivo_titulo`, `objetivo_order`) sin cambios |
| `LearningPath.knowledge_level` | Sigue escribiéndose no nulo (marca de `sanitize_learning_paths.py`) |
| `module_breakdown` | Tendrá **una sola clave** (`"1"`). La UI que lee `["2"]` no encuentra dato (hoy sin consumidor: M2 no tiene experiencia) |
| `attempt.level` | Se calcula sobre los 8 ítems (umbrales 70/40) |
| Intentos en curso | Hoy 0. Antes de subir `BANK_VERSION`, verificar que siga siendo 0: un intento abierto cae en `ordered or questions` y se corrige silenciosamente contra el banco nuevo |
| Renderizado de ítems (`frontend/src/pages/estudiante/KnowledgeTest.tsx`) | **Requisito duro de implementación y validación, aceptado por el tesista (2026-09-19): el nuevo banco NO debe activarse (subir `BANK_VERSION` ni sembrar) hasta que el frontend renderice opciones multilínea.** No es solo estético: los ítems de "representar" (pseudocódigo y diagrama) y los de predecir salida de "ejecutar" usan alternativas de varias líneas, y con el renderizado actual (que aplana los saltos de línea) el ítem de predicción de salida con "todo en una línea" frente a "tres líneas" muestra **dos opciones idénticas** y es **irrespondible**. Las alternativas **no se simplifican** para evitar la dependencia. Criterio de validación antes de activar: comprobar en pantalla, para cada ítem con opciones multilínea, que ninguna pareja de opciones se ve igual. Las opciones deben mostrarse con saltos de línea y fuente monoespaciada (`whitespace-pre-line` + `font-mono`, o `pre-wrap` si se necesita sangría). Es la misma pantalla para pre y post. Es un cambio de código futuro; no se realiza aquí |
| Post-test | **Decisión P1 (tesista, 2026-09-20):** el post se sirve con la **versión de banco del pre del estudiante** (D8: mismo instrumento) y no se migra a nadie de v2 o v3 a v4, para conservar comparables los pares históricos (hay 29 estudiantes con pre antiguo y sin post). La puerta depende de esa versión: v2 y v3 mantienen **2 módulos**; v4 pasa a **completar M1**. La regla actual (`POST_TEST_REFERENCE_MODULE_LIMIT = 2`, acoplada a `REFERENCE_MODULE_MODE`) quedaría inalcanzable con la ruta de 8 módulos. Son cambios de código futuros (commits 5 y 4 del plan) |

## 9. Riesgos y tensiones conocidas (no se resuelven con el banco)

1. **Con n = 8, dos errores = 75 %.** El canal de UI (`pct ≥ 70`) y el
   respaldo de desbloqueo (`MASTERY_THRESHOLD_PCT = 75`) darían "dominio"
   mientras el runtime (`errores < 2`) marca no dominada y propone reforzar.
   Es la discrepancia entre umbrales ya registrada, ahora localizada en dos
   errores. **No se corrige aquí.**
2. **Un solo error en "ejecutar" permite avanzar** (`errores < 2`). El diseño
   (2, 2, 4) reduce el riesgo, no lo elimina. Si la validación real lo
   confirma, es evidencia para revisar la política de decisión, no para
   cambiarla ahora.
3. **"Provisional" no tiene efecto en el runtime.** La evaluación de módulo
   real es de 2 ítems (fuerza máxima 0.34): con un pre-test de n ≥ 5 no
   puede revertir su claim ni desplazarlo por D1. Dependencia de política.
4. **"Reforzar" casi nunca deriva decisión** bajo θ = 0.5 (requiere ≥ 7
   errores de 8). Asimetría previa, sin cambio.
5. **`module1.ts` enseña Instrucciones precisas + Variables + Input** (el M1
   anterior), no el catálogo de 6 conceptos. El "antes" se mide contra el
   catálogo.
6. **Relación `Concept` ↔ `asunto`** (alternativas A/B/C) sigue abierta.
7. **COMP-5 evidencia M1.4 con menor precisión de atribución.** En v3 sus
   ítems eran Bloom 4 (depuración); un fallo puede deberse al razonamiento y
   no a la sintaxis. Se mitiga con el ítem de "sintaxis sin `print`" y con
   `bloom_level` explícito por ítem (§4.3).
8. **Efecto de repetición:** pre y post usan los mismos ítems; la ganancia
   es un indicador descriptivo del producto, no una medida controlada.
   `compute_experiment_result` no valida que ambos intentos sean de la misma
   versión (dependencia).
9. **Dependencia local entre ítems de "ejecutar" (limitación del
   instrumento, aceptada por el tesista, 2026-09-19).** Los ítems 5, 6, 7 y 8
   muestran código `print("...")` correcto, de modo que la forma correcta de
   escribirlo se ve en varios ítems y puede servir de pista para resolver los
   de sintaxis y depuración (7 y 8). Debilita el supuesto de independencia con
   el que se modeló la detectabilidad de lagunas en "ejecutar" (§3). **No
   obliga a rediseñar los ítems**: el único código de M1 es `print`, así que
   es inevitable por construcción. Se registra como limitación. Se **eliminó**
   la parte evitable, la reutilización literal de cadenas entre ítems (§4.9),
   y se mitiga con el orden de servicio (punto siguiente): el ítem 7 se sirve antes que el 5, el 6 y el 8.
   Sensibilidad modelada de la probabilidad de desbloquear M2 con una laguna
   en "ejecutar" (estudiante fuerte en lo demás): 3.4 % si los 4 ítems
   informan; 9.7 % si uno de ellos queda "regalado" por pistas; 25.5 % si dos.
   Son casos extremos, no lo esperable.
10. **Orden de servicio: resuelto con la decisión O = B (tesista,
    2026-09-20).** `get_bank_questions` ordena por `(module_number, order)`;
    con `order` 0 o 1 repetido entre competencias el orden dentro de cada
    grupo no estaba determinado. Se asigna un `order` global único (§6, §13),
    de modo que el orden de servicio es determinista: 1, 2, 3, 4, 7, 8, 5, 6.
    `get_bank_questions` **no se modifica**. Alternativas consideradas y
    descartadas: aceptar el orden arbitrario (el 7 no siempre precedería al
    5); un desempate por `topic` (no puede producir una secuencia útil: sirve
    Ejecutar antes que Concebir); una lista explícita de orden (añade
    estructura y cambia código). El orden queda fijado por intento en
    `question_order`, así que el post repite la secuencia del pre.

## 10. Validación posterior (con datos reales)

Adoptado como diseño, no como resultado. Antes de darlo por bueno, medir:
distribución de errores por función; concordancia entre desbloqueo de M2 y
desempeño posterior en M2; tasa de "dominada" frente a la de "avanzar" con
decisión derivada; efecto de la longitud (8 ítems) en abandono y tiempo.
Requiere estudiantes reales y separar cuentas de prueba.

## 11. Decisiones de diseño previas a los ítems

**Cerradas (tesista, 2026-09-19):**

1. **Asignación de COMP:** Concebir = COMP-0 × 2; Representar = COMP-2 × 2;
   Ejecutar = COMP-3 × 2 + COMP-5 × 2. COMP-1 y COMP-4 dejan de medirse (§6).
2. **COMP-2:** alcance ampliado de forma explícita y acotada, sin cambiar su
   significado ni su etiqueta (§6).
3. **`bloom_level`:** obligatorio en todos los ítems de v4 (§4.3, §7).
4. **Representar:** opción múltiple de 4 alternativas con representaciones
   completas y verificables, **condicionada** al ajuste de renderizado de
   opciones (§4.4, §8). Se mantuvo la selección de representaciones frente a
   la alternativa de poner la representación en el enunciado.

**Resueltos con el diseño de los ocho ítems (2026-09-19):**

1. Convención de **notación textual** del diagrama de flujo: registrada en §4.
2. Tabla de mapeo ítem → función → concepto(s) → COMP → `order` →
   `bloom_level` → etiquetas: registrada en §13.

**Decisiones de implementación (tesista, 2026-09-20):**

1. **P = P1:** el post usa la versión de banco del pre y la puerta depende de
   esa versión (§8). No se migran pares históricos.
2. **O = B:** `order` global 0 a 7 (§6, §9.10); `get_bank_questions` no se
   modifica. Modifica explícitamente los `order` diseñados antes.
3. **M:** sin modelos mentales en v4 (§5).
4. **T = T2 + T3:** test de datos en el backend (invariante 14) y validación
   visual real en navegador de los ítems 3, 4, 5 y 6; sin añadir Vitest ni
   Testing Library por ahora (el frontend no tiene runner de pruebas).
5. **R:** rama dedicada; stage solo de archivos concretos (nunca `git add .`
   ni `git commit -a`), porque el árbol de trabajo tiene cambios ajenos.

**Pendientes antes de activar v4 (no bloquean el diseño de los ítems):**

1. Renderizado multilínea de opciones en el frontend (§8, requisito duro).
2. Integridad de versión y puerta del post-test (§8, decisión P1).
3. Definir `BANK_VERSION = 4`, la siembra y actualizar los tests (§7).

## 12. Fuera de alcance

Redacción de los 8 ítems, alternativas y distractores; dificultad concreta;
orden de aparición; cambios de código (puerta del post-test, validación de
versión, suficiencia propia de "ejecutar"); cualquier cambio de política.

## 13. Tabla de mapeo de los ocho ítems (normativa)

Esta tabla es el contenido normativo del diccionario de mapeo descrito en §5
(clave `(topic, order)`). **`order` es la posición de servicio global** (decisión
O = B, §6): 0 a 7, único en el banco. Los invariantes de §7 se comprueban contra ella. Los
enunciados, alternativas y distractores **no** viven en este documento.

| Ítem | Función | Conceptos cuyo éxito evidencia | Fallo atribuible | `topic` | `order` | `bloom_level` | `difficulty` | `correct_index` | Etiquetas |
|--:|---|---|---|---|--:|--:|---|--:|---|
| 1 | Concebir | M1.1 | M1.1 | `comp_0_problema` | 0 | 2 | basico | 2 | — |
| 2 | Concebir | M1.2, M1.1 | ninguno automático | `comp_0_problema` | 1 | 3 | intermedio | 3 | — |
| 3 | Representar | M1.3, M1.1 | ninguno automático | `comp_2_interpretacion` | 2 | 2 | basico | 0 | `opciones_multilinea` |
| 4 | Representar | M1.3, M1.1 | ninguno automático | `comp_2_interpretacion` | 3 | 2 | intermedio | 1 | `opciones_multilinea` |
| 5 | Ejecutar | M1.4, M1.5 | ninguno automático | `comp_3_simulacion` | 6 | 3 | intermedio | 3 | `nivel_programa`, `opciones_multilinea` |
| 6 | Ejecutar | M1.4, M1.5 | ninguno automático | `comp_3_simulacion` | 7 | 3 | intermedio | 0 | `nivel_programa`, `opciones_multilinea` |
| 7 | Ejecutar | M1.4 | M1.4 | `comp_5_razonamiento` | 4 | 3 | intermedio | 2 | `sintaxis_sin_print` |
| 8 | Ejecutar | M1.4, M1.5 | ninguno automático | `comp_5_razonamiento` | 5 | 3 | intermedio | 1 | `nivel_programa` |

Definición de las etiquetas:

- **`nivel_programa`**: el ítem exige ejecutar o leer un programa de varias
  instrucciones; su éxito implica M1.4 y M1.5.
- **`sintaxis_sin_print`**: el enunciado explica solo la **semántica** de
  `print` (no su forma de escribirse), de modo que el fallo se atribuye a M1.4
  y no a M1.5.
- **`opciones_multilinea`**: al menos una alternativa contiene saltos de línea.
  Sirve para la validación previa a la activación (§8): en cada ítem con esta
  etiqueta, ninguna pareja de opciones debe verse igual con el renderizado
  final. Con `white-space: pre-line` no colisiona ninguna en los ocho ítems.

Reglas de consistencia (verificadas en la revisión transversal): `correct_index`
2-2-2-2; dos ítems por COMP usada; `(topic, order)` único y `order` global único
en 0 a 7 (secuencia de servicio por ítem: 1, 2, 3, 4, 7, 8, 5, 6); conteo por función
(2, 2, 4); ítem con `nivel_programa` solo en Ejecutar (5, 6, 8); un único ítem
`sintaxis_sin_print` (7).
