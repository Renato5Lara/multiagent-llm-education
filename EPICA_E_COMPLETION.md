# Épica E — Cierre

> "Cierre del ciclo de aprendizaje y consolidación del Design
> System". Documento de cierre corto — el detalle técnico vive en
> `ENGINEERING-GATE-EPICA-E.md`; la auditoría que definió el alcance
> vive en `EPICA_E_AUDIT.md`.

- **Fecha de cierre:** 2026-07-25
- **Punto de partida:** tag `epica-d-complete` (`e5306aa`).
- **Objetivo:** exponer los indicadores que el backend del Post-Test
  ya calculaba, dar al estudiante una retroalimentación de cierre
  propia del Tutor IA, y corregir la causa raíz del bug de
  invisibilidad de texto en componentes de UI compartidos. Ningún
  cambio de Runtime ni de contratos.

## Commits

```
epica-d-complete (e5306aa)
  └─ 8a86012  docs — auditoría previa (Post-Test end-to-end, causa raíz del bug visual)
  └─ 9e22932  EP-02 — corrige tabs.tsx, dropdown-menu.tsx, toaster.tsx
  └─ fcce163  EP-01 — enriquece el resultado del Post-Test + cierre del Tutor IA
```

Un único branch (`feature/epica-e-design-system`) en vez de dos
stackeados, dado que la auditoría redujo tanto el alcance de ambas
piezas que no ameritaban ramas separadas — decisión tomada al ver el
tamaño real del trabajo tras la auditoría, no una desviación del plan.

## Auditoría previa — por qué cambió el alcance original

El plan inicial asumía un Post-Test a medio construir y un problema
visual disperso en varias pantallas. La auditoría (`EPICA_E_AUDIT.md`)
encontró lo contrario en ambos casos:

- El Post-Test **ya funcionaba de punta a punta** (generación,
  respuestas, cálculo, comparación Pre/Post persistida con 9 campos,
  endpoint, pantalla de resultado real). La brecha real era de
  **presentación** (6 de 9 campos sin mostrar) y de **contenido**
  (recomendación del tutor redactada solo para pre-test).
- El bug visual tenía **causa raíz en 2-3 componentes compartidos**
  (`tabs.tsx`, `dropdown-menu.tsx`, `toaster.tsx`), no en veinte
  pantallas — corregir el componente resuelve todos sus consumidores
  a la vez, exactamente la filosofía de Épica D ("arreglar el
  sistema, no cada pantalla").

Esto redujo el riesgo de implementación drásticamente frente al plan
original, y dejó fuera —correctamente— una migración mucho mayor
(~60 archivos del sistema visual legacy) que habría inflado el
alcance sin necesidad.

## Cambios principales

- **EP-02**: `ui/tabs.tsx` (pestaña activa: `bg-white` + `text-foreground`,
  invisible en modo oscuro → `bg-white/[0.08]` + `text-neural-text`),
  `ui/dropdown-menu.tsx` (menú de tema claro → `glass-panel-elevated`),
  `ui/toaster.tsx` (mismo patrón). Corrección a la propia auditoría
  encontrada en la verificación: el consumidor real del bug de
  `Tabs` es Docente + Modo Evidencia, no Admin (el bug de Admin viene
  del dropdown del header) — documentado en el gate.
- **EP-01**: segunda fila de indicadores en la tarjeta de comparación
  del Post-Test (Nivel, Tiempo invertido, ganancia normalizada `g`
  con etiqueta cualitativa), `percent_gain` como dato secundario, y
  un panel nuevo "Tutor IA Multiagente — Cierre de tu aprendizaje"
  con redacción propia (nunca reutiliza el texto de pre-test "tu ruta
  empezará por X").

## Cambios deliberadamente excluidos

- **`group_label`** (cohorte Experimental/Control del experimento) —
  nunca se muestra al estudiante a propósito: revelar el grupo
  asignado a un participante podría sesgar su comportamiento,
  invalidando la medición. Reservado para vistas de investigador.
- **Integración del Post-Test con el motor adaptativo** — el
  post-test deliberadamente NO alimenta el Runtime (a diferencia del
  pre-test). Documentado como regla vigente, no reabierto.
- **Los ~60 archivos del sistema visual legacy** (`components/swarm/`,
  `components/observability/`, y el ya conocido
  `module/`/`learningJourney/`/`engage/`) — candidato a una épica
  futura de migración (Épica F o similar), demasiado grande para
  mezclar aquí.

## Riesgos conocidos

- **Verificación de EP-01 sin captura de pantalla en vivo**: se
  intentó reproducir un post-test fresco en una cuenta QA borrando su
  intento existente — la base de datos rechazó el borrado por la
  restricción de llave foránea hacia `experiment_results` (dato de
  experimento real, protegido correctamente). En su lugar se verificó
  contra la API real (valores reales de una estudiante con post-test
  ya completado) y se trazó el cálculo a mano contra el código. El
  build confirma que los 6 campos nuevos están correctamente
  tipados de punta a punta. Si se quiere una captura visual en vivo,
  hace falta un estudiante nuevo que complete pre-test → todas las
  misiones → post-test desde cero — no se hizo en esta sesión por el
  tiempo que exige recorrer un curso completo.
- El resto de "Tutor" (Widget/InsightsPanel/Presence) ya usaba
  correctamente el Design System — no requirió cambios.

## Validación (Release Gate)

| Área | Estado |
|---|---|
| Build (`tsc -b && vite build`) | ✅ Limpio en ambos commits |
| EP-02 — Admin (dropdown) | ✅ Verificado en navegador real |
| EP-02 — Docente (Tabs) | ✅ Verificado en navegador real (`/docente/panel-pedagogico`) |
| EP-01 — datos y lógica | ✅ Verificado contra API real + trazado a mano (sin captura en vivo, ver Riesgos) |
| Integridad de datos de experimento | ✅ La FK de `experiment_results` protegió el dato real cuando se intentó un borrado de prueba — ninguna mutación indebida ocurrió |
| `ENGINEERING-GATE-EPICA-E.md` | ✅ Completo |
| `EPICA_E_AUDIT.md` | ✅ Preserva el razonamiento previo a escribir código |

## Criterio de aceptación

Cumplido: la auditoría previa evitó sobre-alcance en ambas piezas;
cambios pequeños y reversibles; ningún cambio funcional del Runtime;
regla arquitectónica del Post-Test (no alimenta el motor adaptativo)
documentada explícitamente, no solo respetada implícitamente;
protección de datos de experimento verificada de forma real (no
supuesta); build limpio.

## Recomendación de merge

Integrar `feature/epica-e-design-system` hacia `runtime/architecture`
vía push directo (fast-forward) — mismo procedimiento que Épicas C y
D, dado que el checkout local de `runtime/architecture` en esta
máquina Windows sigue bloqueado por los nombres de archivo ilegales
ya documentados (`project_git_illegal_filename_windows`).

**Épica E — CERRADA**, pendiente del merge/push final y de un nuevo
tag (`epica-e-complete`, sugerido) si el tesista lo confirma.
