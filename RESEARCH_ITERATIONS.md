# RESEARCH_ITERATIONS.md — Iteraciones de Investigación

> Registro vivo de las iteraciones de investigación de la Fase 2+.
> Este documento NO es documentación de software: es evidencia de investigación,
> redactada para poder trasladarse casi directamente al capítulo de
> Resultados y Discusión de la tesis.
>
> Obliga a toda IA que trabaje en este proyecto (Claude, Antigravity, ChatGPT).

---

## Regla maestra

> **Ninguna funcionalidad nueva se implementa si antes no puede justificarse
> como evidencia de la hipótesis de investigación.**

Hipótesis: una arquitectura de orquestación pedagógica multimodal basada en
enjambre de agentes — mediante memoria compartida, consenso determinista y
calibración taxonómica Bloom — genera instrucciones de contenido educativo
adaptadas al perfil del aprendiz con trazabilidad completa, logrando mayor
riqueza y adaptabilidad que un sistema de agente único.

## Puerta de entrada (antes de implementar cualquier cambio)

Responder obligatoriamente las cinco preguntas. Si alguna no tiene respuesta,
**no se implementa**:

1. ¿Qué pregunta de investigación responde?
2. ¿Qué parte de la hipótesis fortalece?
3. ¿Qué variable afecta?
4. ¿Cómo se observará durante la demo?
5. ¿Cómo aparecerá luego en Resultados y Discusión?

## Plantilla de iteración

```
ITERACIÓN DE INVESTIGACIÓN N.n — <nombre>

Pregunta de investigación   (observable, nunca subjetiva)
Hipótesis parcial           (si <intervención>, entonces <efecto observable>)
Implementación              (qué se construyó; commits)
Evidencia observable        (qué puede verse en la demo sin explicación verbal)
Variables fortalecidas      (independiente / dependiente)
Amenazas a la validez       (lo que esta iteración NO demuestra)
Evidencia que deberá recolectarse  (observables del diseño experimental)
Resultado
Estado                      (EN PREPARACIÓN / EN CONSTRUCCIÓN / EN VALIDACIÓN / CONSOLIDADO)
```

---

# ITERACIÓN DE INVESTIGACIÓN 2.1 — La hipótesis hecha visible

## Pregunta de investigación

¿El estudiante puede comprender, sin ayuda del expositor, por qué su
experiencia de aprendizaje es diferente y a qué se debe cada decisión
pedagógica del sistema?

## Hipótesis parcial

Si cada decisión adaptativa del sistema (secuencia, modalidad, momento de
evaluación) se explica en el lenguaje del estudiante y en el momento en que
puede preguntársela, entonces el estudiante comprenderá que su recorrido fue
organizado a partir de su perfil, sin necesidad de exponer la arquitectura
técnica del enjambre.

## Implementación

Commit `055080e` (más base de `d9eba07`, Fase 1):

- **FiveEProgressBar** — recorrido 5E narrado (Descubre → Explora → Comprende
  → Practica → Demuestra) con hilo conductor siempre visible que conecta la
  historia ("Ya construiste el concepto. Ahora se convierte en herramienta.").
- **Banner de modalidad** — origen → detección → beneficio, anclado al
  diagnóstico real (`dominantModality`), con badge de confianza. Lenguaje
  centrado en la adaptación, no en el actor.
- **PhaseTransitionOverlay** — ritual de cruce de fase con presencia discreta
  del enjambre.
- **AdaptationEcho** — causa → consecuencia tras cada paso interactivo, según
  tipo de paso y calidad de la respuesta.
- **StepContextTag** — "¿por qué ahora?" solo cuando agrega contexto,
  incluida la evaluación.
- **Milestones 25/50/75%** — checklist de logro del estudiante.

Reglas de diseño consolidadas: regla del 20% (máximo un quinto de la pantalla
es "meta"), cada mensaje responde exactamente una pregunta, protagonista el
estudiante, la IA como buen profesor y no como personaje.

## Evidencia observable

En los primeros 60 segundos de la demo, sin explicación verbal: el banner
declara el porqué de la organización del módulo; las pills 5E y el hilo
conductor sitúan la fase pedagógica; cada actividad se justifica al aparecer;
cada respuesta produce una consecuencia explicada.

## Variables fortalecidas

- Independiente: ✔ adaptación multimodal · ✔ arquitectura multiagente
  (presencia) · ✖ inteligencia de enjambre como proceso colectivo observable
  (pendiente, iteración 2.2).
- Dependiente: ✔ experiencia personalizada · ✔ percepción de adaptación ·
  ◐ comprensión del estudiante (habilitada; su medición corresponde a 2.3).

## Amenazas a la validez

Lo que esta iteración NO demuestra:

- No demuestra que el aprendizaje mejore.
- No demuestra mejor rendimiento académico ni retención.
- No demuestra que la adaptación continúe durante el recorrido (solo al inicio).
- El feed de agentes del overlay es presentacional, no trazabilidad en tiempo
  real (esa corresponde al Swarm Monitor del Modo Evidencia).

Solo demuestra que el estudiante puede comprender por qué su experiencia es
diferente.

## Evidencia que deberá recolectarse

Durante la experimentación se observará:

- □ Tiempo hasta identificar que el contenido fue personalizado.
- □ Capacidad del estudiante para explicar por qué está viendo esa secuencia.
- □ Diferenciación respecto a un LMS tradicional.
- □ Comprensión del modelo pedagógico sin ayuda del expositor.

## Resultado

La adaptación multimodal y el modelo 5E pasaron de afirmaciones documentales a
experiencias observables en la interfaz del estudiante. Ante la pregunta del
jurado "¿dónde se evidencia la adaptación?", la respuesta ya no requiere abrir
el Swarm Monitor.

## Estado

**CONSOLIDADO** (commit `055080e`). Validación observacional en navegador
pendiente con la checklist de "Evidencia que deberá recolectarse".

### Congelado tras esta iteración

No modificar salvo error crítico: Momento 1 · Banner de adaptación · Modelo 5E
(pills y fases) · Hilo conductor · StepContextTag · AdaptationEcho ·
Milestones · PhaseTransitionOverlay.

---

# ITERACIÓN DE INVESTIGACIÓN 2.2 — Evidencias de adaptación continua

## Pregunta de investigación

¿El estudiante puede percibir evidencias de que el sistema sigue adaptando el
aprendizaje durante el recorrido?

## Hipótesis parcial

Si el sistema hace visibles las decisiones adaptativas durante el recorrido,
entonces el estudiante reconocerá que la adaptación continúa durante el
aprendizaje y no solo al inicio del módulo.

## Criterio de éxito único

El estudiante debe poder responder, sin ayuda:

> "¿Cómo sabes que el sistema sigue adaptando tu aprendizaje?"

## Restricciones (contrato)

- No modificar nada de la iteración 2.1.
- No mejorar componentes existentes.
- No rediseñar interfaces.
- Solo añadir evidencias discretas de adaptación continua.

## Estado

**EN PREPARACIÓN** — inicia tras la validación observacional de la iteración 2.1.

---

# REORGANIZACIÓN ARQUITECTÓNICA R1 — Modo Evidencia (2026-07-02)

No es una iteración de funcionalidad: es una depuración del modelo de
actores, aprobada explícitamente por el tesista. **No se implementó ni se
eliminó ninguna funcionalidad**; solo se reorganizó el acceso y la narrativa.

## Decisión

El rol **Investigador se elimina como usuario de negocio**. Todas sus
herramientas (Demo Multiagente, Replay Cognitivo, Decision Trace, consenso,
métricas) se conservan íntegras agrupadas bajo el **Modo Evidencia**: una
capacidad de observabilidad del sistema destinada a la evaluación y
validación experimental de la hipótesis durante la sustentación.

Modelo de actores resultante:

- **Estudiante** → aprende (protagonista).
- **Docente** → acompaña.
- **Administrador** → administra.
- **Modo Evidencia** → demuestra científicamente cómo el sistema decidió.

## Justificación (puerta de las 5 preguntas)

1. **Pregunta de investigación:** ¿puede el jurado observar cómo el sistema
   adaptó el aprendizaje y por qué tomó esas decisiones? (reemplaza a
   "¿funciona el panel del investigador?").
2. **Hipótesis:** fortalece la trazabilidad completa — la observabilidad
   pasa de "pantalla de un rol artificial" a propiedad de la arquitectura.
3. **Variable:** trazabilidad (dependiente); no altera la adaptación.
4. **Observable en demo:** durante el recorrido del estudiante se activa el
   Modo Evidencia ("Permítanme mostrar qué está ocurriendo internamente").
5. **En Resultados y Discusión:** "la plataforma incorpora un Modo Evidencia
   destinado a visualizar el proceso interno de adaptación con fines de
   evaluación y validación experimental".

## Hallazgo que motivó la decisión

La auditoría de código confirmó que el rol ya era una cáscara: su dashboard
solo enlazaba a /swarm-demo y /replay (rutas ya públicas), y el guard
backend `get_current_investigador` no protegía ningún endpoint.

## Cambios

- Frontend: ruta pública `/evidencia` (EvidenceHub + EvidenceLayout);
  acceso "Modo Evidencia" en sidebars de admin y docente; rol retirado de
  selectores de administración y redirecciones (usuarios legado aterrizan
  en /evidencia). Eliminados InvestigadorLayout y pages/investigador.
- Backend: guards muertos retirados de deps.py; `UserRole.INVESTIGADOR` se
  conserva en el enum solo por compatibilidad con filas existentes (sin
  migración destructiva).
- Documentos canónicos actualizados: CLAUDE.md, THESIS_SCOPE_FREEZE.md,
  ROADMAP_THESIS_FOCUS.md, FLOW_AUDIT.md (Recorrido 4 → Modo Evidencia).

## Estado

**CONSOLIDADO.** El Recorrido 4 (FLOW_AUDIT.md) valida el Modo Evidencia
con su nueva pregunta de investigación.
