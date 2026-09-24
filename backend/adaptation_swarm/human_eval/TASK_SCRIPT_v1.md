# Guion de tareas v1 (`task-script-v1`) — sesión de evaluación con docentes/ingenieros

Objetivo: que cada evaluador USE el artefacto antes de responder el SUS. Duración estimada: 25–30 min. Sin datos personales; identificar con un **seudónimo** (E01, E02…).

Preparación (la hace el investigador, no el evaluador): Redis y Postgres activos; para cada perfil de la sesión ejecutar
`python -m adaptation_swarm.run_slice --json salida_<perfil>.json` y abrir los artefactos de la versión de biblioteca (`datasets/adaptation_library/<lib-vN>/`)
junto con el JSON (perfil, W, convergencia del PSO, paquete, `correlation_id`). No existe todavía un visor HTML dedicado: si se requiere, es trabajo pendiente y no se declara implementado.

Tareas (el evaluador lee el informe y, si desea, repite con otro perfil):
1. Abrir la página del perfil **Visual-Dominante × Bucles** e identificar el vector W y qué modalidad domina.
2. Revisar el paquete entregado: código (Python y C++), diagrama (SVG), texto y escuchar el audio.
3. Ubicar en la gráfica de convergencia en qué iteración se detuvo el enjambre y por qué (`stop_reason`).
4. Recorrer la traza de mensajes y señalar qué agente respondió qué (AG1…AG4).
5. Repetir con el perfil **Lógico-Sintáctico × Funciones** y comparar qué cambia en el paquete.
6. Comprobar que las cuatro modalidades corresponden al mismo concepto.

Después: SUS (`SUS_INSTRUMENT_ES.md`), y —solo si el evaluador forma parte del panel— la valoración de la tabla gold (`PANEL_PROTOCOL.md`).
