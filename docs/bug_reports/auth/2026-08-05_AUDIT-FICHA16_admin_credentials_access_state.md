# Ficha 16 — Estado de acceso de `admin@upao.edu.pe` (credencial documentada no coincide)

## Metadata

- **Fecha:** 2026-08-05 (hallazgo generado 2026-08-06 ~04:33 UTC,
  durante la validación E2E de Ficha 15)
- **Rama:** `feat/confidence-calibration-remediation-orientation`
- **Protocolo pedido:** (1) confirmar que el usuario existe en
  PostgreSQL; (2) comparar el hash bcrypt contra el valor documentado en
  `seed.py`; (3) revisar si hay lockout; (4) revisar logs de auth; (5)
  confirmar si afecta solo a Admin o a todos los roles. **Ningún archivo
  de código modificado. Ninguna contraseña reseteada ni reintentada.**
  Todas las consultas son de solo lectura contra Postgres real
  (`users`, `login_attempts`, `audit_logs`).
- **Origen:** durante Ficha 15 (Épica C), el login a
  `admin@upao.edu.pe` con la contraseña documentada
  (`backend/seed.py:355/677`, `CLAUDE.md`/memoria
  `research_implementation_mode.md`) devolvió "Credenciales
  incorrectas. Intentos restantes: 1" — se abandonó ese camino sin
  reintentar, y se registró como hallazgo separado.

---

## 1. ¿Existe el usuario en PostgreSQL?

**Sí, confirmado por consulta directa, no supuesto:**

```
id=fe6af4bf-2a7b-4f94-8246-dc7e9515fd02
email=admin@upao.edu.pe
role=UserRole.ADMIN
is_active=True
created_at=2026-06-21 21:40:32 UTC   (fecha original del seed)
updated_at=2026-08-05 21:00:21 UTC   (¡hoy, reciente!)
```

## 2. ¿Coincide el hash con la contraseña documentada?

**No.** `verify_password("Admin2026!", hash_actual)` → **`False`**.

Verificado contra las otras dos cuentas de referencia documentadas en la
misma fuente (memoria `research_implementation_mode.md`), como control:

| Cuenta | Contraseña documentada | `verify_password()` | `updated_at` |
|---|---|---|---|
| `docente@upao.edu.pe` | `Docente2026!` | ✅ `True` | 2026-06-21 (sin tocar desde el seed) |
| `estudiante3@upao.edu.pe` | `Student2026!` | ✅ `True` | 2026-06-21 (sin tocar desde el seed) |
| `admin@upao.edu.pe` | `Admin2026!` | ❌ `False` | **2026-08-05 21:00:21 (hoy)** |

**Solo el hash de `admin` fue modificado desde el seed original** — el
único de los tres cuya contraseña ya no coincide con la documentada, y
el único cuyo `updated_at` se movió.

## 3. ¿Hay lockout?

**Sí, y funcionó exactamente como está documentado —no es un bug del
mecanismo de lockout:**

`app/api/routes/auth.py:41`: *"Bloquea la cuenta tras 3 intentos
fallidos en 5 minutos."* `LOCKOUT_DURATION_MINUTES` en
`auth_service.py`. Mis 2 intentos fallidos (04:33:26 y 04:33:44 UTC)
dejaron correctamente "1 intento restante" antes del bloqueo de 3 — el
mensaje que vi durante Ficha 15 es el comportamiento diseñado, no un
error de UI ni de conteo.

## 4. Logs de autenticación — la contraseña SÍ funcionó hoy, hasta 5 horas antes de mi intento

`login_attempts` para `admin@upao.edu.pe` (más reciente primero):

```
2026-08-06 04:33:44 success=False   ← mi 2do intento
2026-08-06 04:33:26 success=False   ← mi 1er intento
2026-08-05 23:22:14 success=True    ← última sesión real exitosa, ~5h antes
2026-08-05 21:56:29 success=True
2026-08-05 21:47:56 success=True
2026-08-05 21:23:38 success=True
2026-08-05 21:23:35 success=True
2026-08-05 21:13:06 success=True
2026-08-05 21:12:26 success=True
2026-08-05 21:08:50 success=True
2026-08-05 21:05:10 success=True
2026-08-05 21:01:48 success=True    ← primer éxito tras el cambio de hash (21:00:21)
```

**Los 10 logins exitosos entre 21:01:48 y 23:22:14 ocurrieron TODOS
después de que el hash cambiara (21:00:21)** — confirma que existe una
contraseña real, distinta de `Admin2026!`, que se usó correctamente
muchas veces hoy mismo, incluida la sesión de creación de usuarios de
`ux.nuevo.recorrido@upao.edu.pe` y otras cuentas (`audit_logs`, acción
`crear_usuario`, mismo `admin_id`, 23:23:32 — inmediatamente después
del último login exitoso).

**`audit_logs` no registra ningún evento de cambio de contraseña cerca
de las 21:00:21** (revisadas las acciones distintas que existen en la
tabla: `actualizar_usuario`, `cambiar_rol`, `crear_usuario`,
`desactivar_usuario`, `reactivar_usuario`, `login`, entre otras — cero
entradas de ese tipo para el `admin_id` en esa ventana). El cambio de
hash **no pasó por el flujo auditado de la aplicación** (no hay
`actualizar_usuario` correspondiente) — ocurrió por una vía que la
aplicación no registra: probablemente una acción directa contra la base
de datos o un script fuera del API, no un endpoint de "cambiar
contraseña" de la plataforma.

## 5. ¿Afecta solo a Admin o a todos los roles?

**Solo a Admin, confirmado, no solo no observado.** `docente@upao.edu.pe`
y `estudiante3@upao.edu.pe` mantienen su contraseña documentada
funcionando y su `updated_at` intacto desde el seed original — ningún
indicio de que el mecanismo de lockout, autenticación o hash haya
cambiado de comportamiento general. Es un evento aislado a una sola
cuenta.

---

## Clasificación

**No es un defecto del sistema.** El lockout funcionó según su
contrato; el hash de `docente`/`estudiante` sigue siendo válido; no hay
ninguna señal de que la autenticación en general esté rota. Es una
**divergencia de documentación**: en algún momento de hoy
(2026-08-05, ~21:00 UTC), la contraseña real de `admin@upao.edu.pe`
cambió a un valor que **no** es `Admin2026!` — y que alguien (una
sesión real, no necesariamente esta) conoce y usó exitosamente 10 veces
después del cambio — sin que `seed.py`, `CLAUDE.md` ni la memoria del
proyecto se actualizaran para reflejarlo, y sin que el cambio quedara
registrado en `audit_logs` por la vía auditada de la aplicación.

**No se intentó identificar la contraseña actual** (no se prueban más
valores más allá de los ya descartados en la investigación previa) —
hacerlo sin conocer el valor real seguiría siendo adivinar, con el
mismo riesgo de bloqueo que motivó abrir esta ficha en primer lugar.
**No se resetea la contraseña ni se modifica ningún dato** — esta ficha
es diagnóstico puro.

## Pregunta abierta para el tesista (no técnica, no se decide aquí)

¿Esta sesión (u otra, en otro momento de hoy) cambió deliberadamente la
contraseña de `admin@upao.edu.pe`, por ejemplo directamente contra
Postgres o vía un script fuera del API? Si es así, la corrección es
solo documental: actualizar `seed.py`/`CLAUDE.md`/memoria con el valor
real. Si **no** fue una acción intencional conocida, el hallazgo merece
más atención — un cambio de contraseña de administrador que no pasó por
el flujo auditado de la aplicación, en un entorno de desarrollo local,
sin que nadie lo haya solicitado conscientemente.

---

## 6. Búsqueda del origen (solo lectura, sin modificar nada)

A pedido explícito, se investigaron los mecanismos disponibles en el
código actual que podrían explicar el cambio, antes de declarar "origen
no determinado":

- **`POST /api/auth/recover`** (`auth.py:143-155`) — descartado por
  código, no por suposición: su propio docstring dice *"Actualmente en
  modo mock: registra en logs"*, y `auth_service.recover_password()`
  (líneas 141-149) solo hace `logger.info(...)` y retorna `bool` — nunca
  toca `hashed_password`. No pudo ser el mecanismo.
- **Cualquier script propio del repo** — `grep -rn "hashed_password\s*="
  app/ scripts/` (excluyendo `models/user.py`, la definición de la
  columna) → **cero resultados**. Ningún script versionado en el
  repositorio escribe ese campo fuera de `seed.py`.
- **`seed.py`** — descartado por dos razones: (a) hardcodea
  `"Admin2026!"` literal (`seed.py:348`), no lee ningún valor de
  entorno — volver a ejecutarlo no podría producir una contraseña
  distinta; (b) es idempotente (`if not admin: ...` — si el usuario ya
  existe, no lo toca). `git log --since=2026-08-04 -- backend/seed.py`
  → sin commits, tampoco fue editado temporalmente.
- **Correlación temporal con el trabajo de auth de hoy** — el cambio
  de hash (16:00:21 hora local, `America/Lima`) cae dentro de la misma
  ventana de 20 minutos que el trabajo real sobre sesión/autenticación
  documentado en `2026-08-05_AUDIT-FICHA01-02_cross_tab_storage_
  revalidation_loop.md` (commits `a63597c`/`66c3f00`, 16:00-16:16) — se
  revisó ese documento específicamente por mención de contraseñas,
  `admin@upao.edu.pe`, hashes o `seed`: **cero coincidencias**. La
  correlación temporal no tiene respaldo causal en la documentación
  existente — es coincidencia de horario, no evidencia de mecanismo.

**Conclusión de esta búsqueda:** se agotaron las vías de bajo riesgo
disponibles sin escribir ni ejecutar nada nuevo contra producción/DB
más allá de las consultas ya hechas. Ningún mecanismo del código actual
explica el cambio, y no quedó rastro en la documentación de la sesión
cuyo horario coincide. **Cambio de credencial administrativa detectado
fuera del flujo auditado; origen no determinado.** La explicación más
probable, sin evidencia que la confirme, es un script ad-hoc de una
sesión anterior (mismo patrón que las consultas de solo lectura de esta
propia ficha, pero en modo escritura) que no se commiteó — no hay forma
de confirmarlo sin preguntarle directamente al tesista.

---

## 7. Resolución (2026-08-06, decisión explícita del tesista: Opción A)

El tesista, con las dos opciones planteadas (A: restaurar `Admin2026!`
y actualizar todo; B: mantener la contraseña real desconocida y
actualizar solo documentación), **eligió explícitamente la Opción A**
vía `AskUserQuestion` — permiso claro para modificar la credencial,
según la categoría "Explicit permission required" del harness
(cambio de configuración de cuenta).

**Reseteo controlado, no adivinado:**

```python
admin.hashed_password = get_password_hash("Admin2026!")  # misma función que seed.py:348
db.commit()
```

Ejecutado vía script de una sola vez contra `SessionLocal`/`User` (mismo
patrón que las consultas de solo lectura de esta ficha, ahora en modo
escritura, explícitamente autorizado) — no se recreó al usuario, no se
tocó `is_active`, `role` ni ningún otro campo; **solo `hashed_password`**.

**Verificación en dos capas, no solo `verify_password()`:**

1. `verify_password("Admin2026!", hash_nuevo)` → `True` (capa de
   librería, ya usada en el diagnóstico original).
2. **`POST /api/auth/login` real** contra el backend en ejecución
   (`localhost:8000`) con `{"identifier": "admin@upao.edu.pe",
   "password": "Admin2026!"}` → **HTTP 200**, `access_token` y
   `refresh_token` emitidos, `user.role: "admin"` — el mismo endpoint
   que falló durante Ficha 15 ahora acepta la contraseña documentada.
   Se verificó lockout previo (`is_account_locked()` → `False`) antes
   de intentar, para no repetir el riesgo que motivó esta ficha.

**`admin@upao.edu.pe` / `Admin2026!` vuelve a ser la contraseña real y
verificada del sistema — coincide otra vez con `seed.py:355/677`,
`CLAUDE.md` y la memoria del proyecto.** No fue necesario modificar
ningún documento adicional: la divergencia se cerró alineando la DB con
la documentación ya existente, no al revés.

**Lo que sigue sin resolverse, deliberadamente:** el origen del cambio
original (§6) sigue sin determinarse — restaurar la contraseña no
explica por qué cambió. Si vuelve a divergir, esta ficha ya documenta
el método de diagnóstico completo para repetirlo. La recomendación de
gobierno de cambios privilegiados (audit_log obligatorio para
password/rol/estado de cuentas ADMIN) sigue en pie como mejora futura,
sin implementar.
