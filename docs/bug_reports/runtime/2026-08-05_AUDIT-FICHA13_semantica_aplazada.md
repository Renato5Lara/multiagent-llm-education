# Ficha 13 — Semántica de `Aplazada` (continúa el Mecanismo A de Ficha 05)

## Metadata

- **Fecha:** 2026-08-05
- **Rama:** `feat/confidence-calibration-remediation-orientation`
- **Protocolo pedido (Fase 5):** (1) determinar la semántica actual de
  `Aplazada`; (2) revisar dónde se genera y dónde se consume; (3)
  confirmar si afecta decisiones del ConsensusEngine o solamente
  presentación/UI; (4) clasificar: estado válido del dominio / estado
  intermedio que requiere decisión / defecto funcional; (5) no
  implementar cambios hasta cerrar la decisión arquitectónica. **Ningún
  archivo de código modificado.**
- **Continúa (no repite):** `2026-08-05_FICHA05_entrega_diseno_none_
  investigacion.md` (commits `dc9136e`/`958158a`/`cd3f084`), que dejó
  explícitamente abierta una única pregunta: *"la pregunta sobre el
  aplazamiento (Mecanismo A) sigue abierta y no se investigó en esta
  fase"* — y señaló su propio prerrequisito sin cumplir: *"revisar
  RFC-0006 (consenso-enjambre) y CONCEPT-0002 (taxonomía del consenso)
  para la política esperada de `Aplazada`, ninguno de los dos releído a
  fondo con esta pregunta específica todavía"*. Esta ficha cumple ese
  prerrequisito y responde con esa lectura. Cero commits han tocado
  `mecanica.py`, `orientar/productor.py`, `remediar/productor.py` ni
  `productores.py` desde el cierre de Ficha 05 — el diagnóstico de base
  sigue vigente sin drift.

---

## 1. Semántica actual de `Aplazada` — lo que RFC-0006/CONCEPT-0002 ya definen

**No es una pregunta de arquitectura sin resolver — la arquitectura ya
la responde, con una regla condicional explícita, no con una respuesta
binaria "sí/no".**

`CONCEPT-0002-taxonomia-del-consenso.md` §4:

> "Se aplaza (...) cuando la regla de resolución no puede discriminar
> **y** existe un camino de evidencia (...) **Restricción pedagógica:**
> hay un estudiante esperando en la pantalla. Si la decisión no puede
> esperar el camino de evidencia, **no se aplaza**: se resuelve con la
> mejor confianza disponible como **decisión provisional** (...) **El
> aplazamiento es para el sistema; la provisionalidad es para el
> estudiante.**"

`RFC-0006-consenso-enjambre.md` §4:

> "**Margen < δ** → **aplazada**, registrando qué evidencia
> discriminaría (INV-7) — declaración accionable (...) **Decisión
> provisional** — si el slot es **urgente** (bloquea una entrega que el
> estudiante espera, atributo derivado de `ejecución`) y el margen < δ:
> se resuelve con el mejor claim disponible (...)"

Y CONCEPT-0002 §5 bis confirma que `aplazada` es uno de los resultados
del **espacio cerrado** de la deliberación — no una excepción, no un
estado degenerado: *"Toda deliberación termina exactamente en uno de
estos resultados"*.

**Conclusión de semántica: `Aplazada` es un estado válido y diseñado del
dominio — pero condicionado.** No es "final" en el sentido de
permanente (CONCEPT-0002 §5: se reconvoca cuando llega la evidencia
declarada faltante), ni "siempre debe producir una decisión
provisional" — depende exclusivamente de `urgente`, que la propia RFC
define con un criterio concreto: *"bloquea una entrega que el estudiante
espera"*.

Este es exactamente el criterio que Ficha 05 pidió como condición previa
a proponer cualquier remediación (*"si una deliberación aplazada debe
terminar siempre en una decisión provisional (...) o si el sistema
intencionalmente requiere múltiples agentes en conflicto"*) — la
respuesta de la arquitectura es: **ninguna de las dos por defecto; el
criterio que decide es si hay un estudiante esperando esa entrega
específica.**

---

## 2. Dónde se genera y dónde se consume (sin re-derivar, cita a Ficha 05)

**Generación** — `runtime/kernel/deliberation/mecanica.py:212-239`
(citado en Ficha 05, verificado sin drift):

```python
if margen >= politica.delta:
    resultado = Resuelta(regla=REGLA_POLITICA_V1, ...)
elif urgente:
    resultado = Resuelta(regla=REGLA_PROVISIONAL, ...)
elif _aplazamientos_en_cadena(...) >= politica.limite_reconvocatoria:
    resultado = Escalada()
else:
    resultado = Aplazada(...)
```

`urgente` es un parámetro externo inyectado por cada llamador del
Boundary (`registrar_evidencia_evaluacion(..., urgente=...)`) — decisión
ya cerrada en RFC-0006/4a (`estado.ejecucion` resultó ser un campo
muerto; la urgencia se resolvió como parámetro externo, no como campo
derivado internamente del estado). Esta ficha no reabre esa decisión.

**Consumo** — Ficha 05 §"Causa raíz mecánica" ya trazó la cadena
completa: una deliberación `Aplazada` no produce `DecisionEntry` →
`Adaptar` (que solo itera `estado.decisiones`) nunca ve nada que
adaptar → `proyectar_entrega` construye `Entrega(asunto=None,
diseno=None)` → `decision_adaptativa()` retorna `None` →
`LearningPath.tsx` no renderiza la tarjeta "Cómo aprenderás mejor".

---

## 3. ¿Afecta al ConsensusEngine o solo presentación/UI?

**Afecta al ConsensusEngine — el problema no es de presentación.**
`Aplazada` es una salida real del propio kernel de deliberación
(`mecanica.py`), no un dato que el frontend interprete mal. La ausencia
de tarjeta en `LearningPath.tsx` es la consecuencia visible correcta de
que, en efecto, **el kernel nunca produjo una decisión** para esa
sesión — no hay ninguna sincronización rota entre backend y frontend
que corregir en la capa de presentación (Ficha 05 ya descartó
`runtime_bridge.py` como causa).

Dicho lo cual, el alcance medido por Ficha 05 (Fase 2, datos reales) es
bajo: **3.4% de las sesiones reales con evidencia (1/29)**, consistente
con el 0.5% (3/660 deliberaciones) de la auditoría original. No es una
condición estructural del runtime — es un caso real, medido, pero
infrecuente.

---

## 4. Clasificación

Separando la pregunta en sus dos niveles, porque mezclarlos es lo que
la mantenía abierta:

### Nivel 1 — ¿Es `Aplazada` en sí misma un estado válido del dominio?

**Sí, sin ambigüedad.** RFC-0006 §4 y CONCEPT-0002 §4/§5 bis la diseñan
explícitamente como parte del espacio cerrado de resultados, con
propósito declarado ("el aplazamiento es productivo: dispara la
búsqueda de evidencia"). No es un defecto ni un estado intermedio sin
resolver conceptualmente — el diseño ya decidió qué es y cuándo ocurre.

### Nivel 2 — ¿Es correcto que EstudianteC (caso real) haya quedado en
`Aplazada` sin decisión provisional?

**Este es el nivel donde sí hay una discrepancia verificable, no una
pregunta filosófica abierta.** El criterio que la propia RFC-0006 fija
para `urgente` es *"bloquea una entrega que el estudiante espera"*. Los
3 call sites que dejaron a EstudianteC expuesta al Mecanismo A
(`student_service.py:155` diagnóstico VARK, `knowledge_test_service.py:
445` y `:488` evidencia de pre-test) usan el valor por defecto
`urgente=False` — pero la propia Ficha 05 trazó que su evidencia
alimenta directamente la tarjeta "Cómo aprenderás mejor" que el
estudiante ve de inmediato en `LearningPath.tsx` tras completar el
pre-test. Bajo la definición textual de la RFC, **esa entrega sí parece
ser una que el estudiante está esperando en pantalla** — el mismo
criterio que sí se aplicó correctamente a `cycle-evidence` y
`submit_evaluation` (`urgente=True` en ambos).

**No se afirma aquí que sea un defecto confirmado** — falta un paso que
esta ficha explícitamente no da: confirmar con el tesista/UX si el flujo
de pre-test realmente deja al estudiante "esperando en pantalla" esa
tarjeta específica de la misma forma síncrona que un ciclo de práctica,
o si el diseño de producto anticipa que esa tarjeta puede legítimamente
tardar hasta la primera práctica. Sin esa confirmación, clasificar los 3
call sites como "mal configurados" sería asumir sin verificar.

**Clasificación final:**

- **`Aplazada` como concepto: estado válido del dominio.** Cerrado, sin
  ambigüedad, con RFC/CONCEPT que lo respaldan.
- **El valor de `urgente=False` en los 3 call sites de VARK/pre-test:
  candidato a defecto funcional (posible discrepancia entre el criterio
  textual de RFC-0006 y su aplicación real), no un estado intermedio
  filosóficamente abierto.** Requiere una decisión de producto puntual
  — no una nueva RFC ni un cambio de arquitectura — antes de tocar
  código: ¿el pre-test es una de las "entregas que el estudiante
  espera"?

---

## 5. No se implementa ningún cambio en este documento

Confirmado: no se modificó `mecanica.py`, ningún `productor.py`, ni
`student_service.py`/`knowledge_test_service.py`. Si el tesista decide
que el pre-test sí cuenta como entrega urgente, la remediación
candidata sería mínima y ya está acotada por la investigación existente
(pasar `urgente=True` en los 3 call sites listados en Ficha 05 §"Causa
raíz mecánica") — pero esa decisión, y su propio Engineering Gate
(¿qué RFC la autoriza? ¿qué principio podría verse afectado al cambiar
la clasificación de urgencia de un flujo completo?), quedan
explícitamente fuera del alcance de esta ficha.
