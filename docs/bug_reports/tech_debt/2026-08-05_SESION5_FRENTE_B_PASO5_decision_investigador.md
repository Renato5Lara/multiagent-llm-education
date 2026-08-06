# Sesión 5, Frente B — Paso 5: Decisión sobre el rol "Investigador"

## Metadata

- **Fecha:** 2026-08-05
- **Rama:** `investigacion/sesion5-rendimiento`
- **Continúa:** el "Pendiente arquitectónico independiente" registrado
  en `AUDIT-2026-08-05_REMEDIATION_STATUS.md` tras Paso 4.
- **Nota sobre el nombre de este documento:** se evaluó abrir
  `ADR-0016-estado-rol-investigador.md` y se descartó por la misma
  razón que ya bloqueó `ADR-0012` en Fichas 01/02 de esta misma
  auditoría: (a) `ADR-0016` ya existe (política de consenso v2,
  aceptada) — colisión de número; (b) el namespace `docs/architecture/
  ADR/` gobierna exclusivamente `backend/runtime/` (kernel/
  deliberación/memoria/consenso del runtime LangGraph) — una decisión
  sobre un rol de plataforma no pertenece ahí. Este documento continúa
  la cadena ya abierta de Sesión 5, Frente B, en su lugar.
- **Protocolo:** las 5 preguntas exactas pedidas antes de decidir.
  **Ningún archivo de código modificado.**

---

## Las 5 preguntas, respondidas con evidencia directa

### 1. ¿Existe una funcionalidad real que lo use?

**Sí — Modo Evidencia / Runtime Console.**
`aget_authorized_evidence_viewer()` (`backend/app/api/routes/runtime.py:51-73`):

```python
"""Las surfaces S3 de solo lectura (traza/estado/memoria/replay/paisaje/
consenso/escaladas) las lee: el estudiante dueño, el docente (RFC-0009
§1: es el humano del loop), y Admin/Investigador — Modo Evidencia
(CLAUDE.md) es la superficie de observabilidad que aloja Runtime
Console, y su backend no puede rechazar al rol que la aloja (auditoría
2026-08-05, Ficha 06)."""
if current_user.role not in (
    UserRole.ESTUDIANTE, UserRole.DOCENTE, UserRole.ADMIN,
    UserRole.INVESTIGADOR,
):
    raise HTTPException(status_code=403, ...)
```

Este acceso fue **reforzado hoy mismo por Ficha 06** de esta misma
auditoría (commit `6eaf14b`) — la propia investigación que llevó a
descubrir la contradicción ya había ampliado, no reducido, el alcance
funcional real de Investigador.

### 2. ¿Tiene permisos diferentes?

**Sí, pero acotados con precisión** — únicamente las 7 rutas de
observabilidad de Runtime Console (`/traza`, `/estado`, `/memoria`,
`/replay`, `/paisaje`, `/consenso`, `/escaladas`). Barrido completo del
backend (`grep -rn "INVESTIGADOR" backend/app`) confirma que son las
**únicas** 3 líneas de código que mencionan el rol en todo el backend
— ningún otro permiso elevado: no administra usuarios, no ve paneles
docentes, no accede a nada fuera de esas 7 rutas.

### 3. ¿Aparece en JWT?

**Sí, sin exclusión especial** — `auth_service.py` codifica
`"role": user.role.value` de forma genérica para cualquier rol
(3 ocurrencias, líneas 81/117/135), Investigador incluido.

### 4. ¿Hay endpoints protegidos para ese rol?

**Sí — los mismos 7 de Runtime Console** del punto 1, confirmados
también en `_verificar_pertenencia` (`runtime.py:284`):
`if current_user.role in (UserRole.DOCENTE, UserRole.ADMIN,
UserRole.INVESTIGADOR)`.

### 5. ¿Hay usuarios históricos con ese rol en BD?

**Sí — 1 cuenta real**, consultada directamente contra Postgres:

```
investigador@upao.edu.pe (Ana Torres), creada 2026-06-28
Distribución total de roles: admin=1, docente=5, estudiante=46, investigador=1
```

**No es una cuenta olvidada** — tiene historial de uso real:

```
login_attempts:
  2026-06-28 14:30:44 → SUCCESS (primer login, el mismo día de creación)
  2026-07-16 00:01:53 → FAILED
  2026-07-23 09:34:02 → FAILED
audit_logs: 1 entrada "login" el 2026-06-28, coincide con el login exitoso
```

Alguien intentó volver a entrar con esta cuenta **dos veces, semanas
después de creada** (16 y 23 de julio) — intención de uso recurrente,
no un registro de prueba abandonado.

---

## Hallazgo adicional — el "legado" está en los comentarios, no en el código

Barrido completo del frontend (`grep -rn "investigador" frontend/src`)
encuentra **routing dedicado y completamente funcional**, no vestigios:

- `App.tsx:47`, `ProtectedRoute.tsx:26`, `useAuth.ts:30` — los tres
  redirigen específicamente `investigador` → `/evidencia` (Modo
  Evidencia) tras login, con lógica propia, distinta de `/admin`,
  `/docente`, `/estudiante`.
- `UserForm.tsx:124` — incluso el propio `SelectItem` deshabilitado
  muestra el texto **"Investigador (legado)"** en la UI del admin.

Pero la palabra "legado" aparece **seis veces, en cuatro archivos**
(`models/user.py`, `types/auth.ts`, `ProtectedRoute.tsx`, `App.tsx`,
`UserForm.tsx` ×2) — siempre como comentario o etiqueta, **nunca como
una restricción real de comportamiento**: en ningún punto el código
bloquea, oculta o deshabilita algo por ser Investigador; al contrario,
Ficha 06 (hoy) le **amplió** acceso.

**Lectura más probable de la evidencia:** en algún momento anterior a
esta auditoría, Investigador sí estuvo inerte (de ahí el comentario
"legado" original) — y en algún punto posterior (probablemente cuando
se construyó Modo Evidencia) volvió a activarse funcionalmente sin que
nadie actualizara los seis comentarios que seguían describiéndolo como
retirado. **No está demostrado con certeza absoluta** (no se revisó el
historial completo de commits de cada comentario) — pero es la
explicación que mejor encaja con toda la evidencia reunida.

---

## Las dos opciones, sin elegir todavía

**Opción A — Mantenerlo (activo, vigente).**
Consistente con: Ficha 06 (hoy), Modo Evidencia (CLAUDE.md, capacidad
canónica del sistema), el único usuario real con intentos de login
recurrentes, y el routing frontend ya completamente funcional.
Implicaría: `Roles.tsx` queda como está; `UserForm.tsx` se alinea
(`SelectItem` incondicional, quitar "(legado)"); corregir los 6
comentarios/docstrings que dicen lo contrario.

**Opción B — Declararlo legado (retirado, congelado).**
Consistente con: la intención textual original de los 6 comentarios
existentes, si esa intención sigue siendo la vigente y Ficha 06 fue un
error de alcance (concedió acceso a un rol que debía seguir sin
permisos).
Implicaría: revertir/restringir `Roles.tsx` para que coincida con
`UserForm.tsx`; posiblemente revisar si Ficha 06 debió excluir a
Investigador del Runtime Console (cambio de mayor alcance, tocaría una
decisión ya cerrada de esta misma auditoría).

**La evidencia recogida pesa con fuerza hacia la Opción A** — no hay
ninguna señal de código que trate a Investigador como retirado; solo
comentarios que lo dicen y que el propio comportamiento del sistema
contradice. Pero la decisión de negocio final (¿debería existir este
actor en la tesis? ¿es coherente con los "tres actores" que CLAUDE.md
declara — Estudiante, Docente, Administrador?) le corresponde al
tesista, no a esta investigación.

**No se implementa nada en este documento.**
