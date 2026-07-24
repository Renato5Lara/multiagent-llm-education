# ADENDA B al Documento 5 — Semántica del Rechazo

**Parte de la Arquitectura Pedagógica v1.0.** Cierra el vacío detectado durante el
stress-test de escenarios de cierre (2026-07-23): la Política de Consentimiento
Adaptativo (Doc 5 §4.1) define cuándo se requiere consentimiento, pero no qué
significa que el estudiante lo niegue.

---

> **Un rechazo no interrumpe el Ciclo, no se fuerza una segunda vez dentro del
> mismo Ciclo, y no se traduce automáticamente en un hecho nuevo del runtime.**

1. **El Ciclo continúa.** El estudiante permanece en el Momento 6 sin la forma
   rechazada — el reto sigue siendo el mismo, nada se abandona por su cuenta.
2. **No genera un fact/claim nuevo del runtime.** Tratar el rechazo como evidencia
   formal (que Tutorizar o Diagnosticar lo consuman) introduciría un concepto de
   dominio que ninguno de los ocho productores modela hoy — excede esta adenda; si se
   decide más adelante, exige RFC sobre `backend/runtime/`, no un apunte aquí.
3. **Sí queda registrado en Memoria** (Doc 6 §1) — la misma forma rechazada no se
   reofrece de inmediato dentro del mismo Ciclo. Es una extensión directa de PP5
   (no-repetición de forma): un rechazo se trata con el mismo respeto que un intento
   fallido.
4. **Puede volver a ofrecerse en un Momento 5 posterior**, si una decisión nueva lo
   amerita (otro Ciclo, otra competencia) — nunca insistiendo dentro del mismo.

**Lo que esta adenda NO decide (correctamente, es decisión de producto):** cuántas
veces re-ofrecer ayuda a lo largo de una sesión completa, o si existe un límite.
Queda para el prototipado.
