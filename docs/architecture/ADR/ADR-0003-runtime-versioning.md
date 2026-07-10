# ADR-0003 — Runtime Versioning

- **Estado:** Aceptado (2026-07-10, Engineering Review — sin observaciones)
- **Fecha:** 2026-07-10
- **Preserva:** R4 (suficiencia), A3, P12; extiende la auditabilidad (P6)
- **Criterio de aceptación:** R1–R6 intactos (RFC-0008 §4)
- **Origen:** propuesto por el tesista en la aceptación de ADR-0001/0002

## Decisión

Toda ejecución declara bajo qué versiones ocurrió — no para reconstruir
(R4 ya lo garantiza con las versiones de configuración), sino para
**auditar y comparar experimentos** a lo largo del tiempo.

1. **Nivel sesión** (en `identidad`, ya normativo por RFC-0003 e INV-1,
   aquí se completa el conjunto): versión del student model, del banco de
   ítems, de la **política pedagógica** (pesos, curvas, δ, θ, escala de
   precisión — ADR-0001 §4) y, nuevo, la **versión del corpus de
   especificación** (`spec_version`: el tag o commit de
   `docs/architecture/` vigente al abrir la sesión). Estas versiones son
   inmutables durante la sesión (INV-2).
2. **Nivel transición** (en el registro de StateTransition): la
   **`runtime_version`** — el identificador del build del runtime que
   aplicó la transición. Es la única versión que legítimamente puede
   variar *dentro* de una sesión: una recuperación (R5) puede reanudar
   bajo un build más nuevo, y ese hecho debe quedar grabado — dos
   transiciones de la misma sesión aplicadas por builds distintos son
   información de auditoría de primer orden.
3. **Regla de comparabilidad:** dos sesiones (o dos re-derivaciones
   contrafactuales) son comparables como experimento si y solo si
   comparten `spec_version` y versión de política — o si la diferencia
   entre ellas es exactamente la variable del experimento (H10). El
   reporte de investigación (RFC-0007 §5) incluye siempre el vector de
   versiones.

## Alternativas rechazadas

- **Versionar solo la política:** insuficiente — un cambio de build del
  runtime con un bug de reducer produciría transiciones distintas bajo la
  "misma versión"; sin `runtime_version` por transición, ese caso es
  indistinguible del no-determinismo (falsa amenaza a P12).
- **Versión por transición para todo el vector:** redundante — todo lo
  que INV-2 congela por sesión no puede variar dentro de ella; repetirlo
  en cada fila es ruido sin información.
- **Derivar la versión del corpus del timestamp:** el reloj de pared no
  participa en nada normativo (A4); la `spec_version` es un identificador
  explícito, no una inferencia.

## Consecuencias

- El vector de versiones (`spec_version`, política, banco, student model,
  `runtime_version`) es parte del sobre de toda exportación de
  investigación y de todo reporte del Engineering Gate.
- ADR-0002: `runtime_sessions` gana las columnas de versión de sesión;
  `runtime_transitions` gana `runtime_version` (dentro de los bytes
  canónicos — participa del hash).
- La comparación de experimentos de la tesis cita versiones, no fechas.
