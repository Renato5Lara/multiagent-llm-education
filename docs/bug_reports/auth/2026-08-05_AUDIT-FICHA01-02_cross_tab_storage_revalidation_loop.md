# Bug Report

## Metadata
- **ID:** AUDIT-FICHA-01 / AUDIT-FICHA-02 (Auditoría-UPAO-MAS-EDU-2026-08-05.docx)
- **Fecha:** 2026-08-05
- **Severidad:** CRÍTICO (ambas)
- **Categoría:** frontend/auth
- **Tipo:** auth, multi-tab, race condition
- **Estado:** Ficha 02 FIXED · Ficha 01 FIXED (ver "Resolución final" — el
  gap residual documentado más abajo quedó cerrado)
- **Commits:** `a63597c` (fix inicial, rama `fix/auth-cross-tab-storage-loop`)
  · `66c3f00` (resolución final, rama `fix/session-storage-isolation`)
- **Relacionado:** [[BUG-002]] (race condition validateSession/meQuery),
  [[BUG-015]] (multi-tab storage event race, forense 2026-05-27)

## Síntomas (evidencia de la auditoría)

1. **Ficha 02** — `GET /api/auth/me` en ráfagas de ~70/s sostenidas mientras
   dos pestañas del mismo navegador tienen sesiones de usuarios distintos.
   ~10,816 líneas de log en 86 min durante la sesión de la auditoría. La
   pestaña se vuelve intermitentemente no interactiva (clics sobre botones
   visibles sin efecto, referencias de elementos invalidadas en milisegundos).
2. **Ficha 01** — una recarga completa de la pestaña de Admin, en medio de
   ese ciclo, la muestra autenticada como un estudiante distinto
   (`EstudianteA BajoVisual`), sin login, sin error. El JWT persistido tiene
   `iat` posterior al login del Admin.

## Root Cause

### Cadena causal (demostrada por lectura de código, no hipótesis)

```
Tab A (Admin)                                Tab B (EstudianteA)
──────────────                               ────────────────────
login → authStore.login() → persist
  → localStorage['upao-auth'] = {token: A, user: Admin}
                                              (Tab B ya logueada como EstudianteA)
  └──────────► evento 'storage' en Tab B
                   parsed.token !== token(B)? → SÍ
                   validateSession()  [AuthProvider.tsx]
                   GET /api/auth/me  (con el token PROPIO de Tab B)
                   setUser(EstudianteA) → persist
                   → localStorage['upao-auth'] = {token: B, user: EstudianteA}
    ◄──────────────┘ evento 'storage' de vuelta en Tab A
    parsed.token !== token(A)? → SÍ
    validateSession() → GET /api/auth/me (token propio de Tab A)
    setUser(Admin) → persist → localStorage = {token: A, user: Admin}
    └─────────────► evento 'storage' en Tab B (vuelve a empezar)

    se repite indefinidamente — cada vuelta cuesta solo la latencia de
    un GET local (3-6 ms medidos, ~70/s observadas)
```

En cualquier instante de ese ciclo, `localStorage['upao-auth']` contiene la
identidad de cualquiera de las dos pestañas — el último escritor. Una
recarga completa de Tab A en ese instante rehidrata zustand desde lo que
sea que haya ahí en ese milisegundo → Ficha 01.

### Código responsable

`frontend/src/providers/AuthProvider.tsx`, listener `storage` (antes de
este fix): ante **cualquier** cambio ajeno de `localStorage['upao-auth']`
con un token distinto al propio, llamaba a `validateSession()` — que hace
`GET /api/auth/me` con el token de la pestaña que recibe el evento y luego
`setUser(resp.data)`, lo cual persiste de nuevo el store y retrigger el
mismo evento en la otra pestaña.

### Origen histórico (git log, `frontend/src/providers/AuthProvider.tsx`)

| Commit | Cambio |
|---|---|
| `8a23b44` (creación) | Único propósito original del listener: `if (!e.newValue) logout()` — sincronizar **logout** entre pestañas. Nada más. |
| `fc45fcc` ("verificar expiración de JWT...") | Agrega la rama `else` de re-validación ("login en otra pestaña → re-validate"), de polizón dentro de un commit cuyo mensaje no la menciona. |
| `5a1fb44` ("phase 1 critical async runtime fixes") | Elimina un *segundo* efecto duplicado con el mismo objetivo, con el comentario: *"raced with meQuery in useAuth, causing intermittent logouts"* — el mecanismo ya había causado un bug antes de esta auditoría. |

`BUG-015` (`2026-05-27_FORENSIC_AUTH_AUDIT.md`) documentó este mismo
listener **cuando solo tenía la rama de logout** (antes de `fc45fcc`). Su
fix recomendado — *"use `useRef` for navigate"* — es una estabilización de
esa rama, no una petición de agregar re-validación de login. La rama que
causó el ciclo nunca fue un requerimiento tracked en ningún RFC/ADR/
CLAUDE.md.

## Fix

**Archivo:** `frontend/src/providers/AuthProvider.tsx`, función
`handleStorageChange` — único cambio.

- Si el `user.id` del token entrante difiere del usuario actual de la
  pestaña → `storeLogout()` + `navigate('/login')` explícito. Nunca se
  vuelve a llamar a `validateSession()`/`GET /api/auth/me` desde este
  listener.
- Si es el mismo usuario → no se re-valida. Cada pestaña refresca su
  propio token de forma independiente vía el interceptor de axios
  (`lib/api.ts`) ante su primer 401 — ya documentado como intencional en
  [[BUG-002]] ("Riesgos futuros" #2: *"Token refresh no dispara
  re-validación... esto es intencional — el refresh ya validó la
  sesión"*).
- La rama de logout cross-tab (`!e.newValue`) — el propósito original del
  listener desde `8a23b44` — queda intacta.

## Validación E2E (navegador real, Postgres real, cuentas de la auditoría)

Reproducido con el código original vía `git stash` antes de implementar,
y de nuevo después vía `git stash pop`, en el mismo entorno (backend
`uvicorn` real + frontend `vite` real + `upao_postgres` real).

| Prueba | Antes | Después |
|---|---|---|
| `GET /api/auth/me` tras login de 2 usuarios distintos en 2 pestañas | 3,676 peticiones en <2 min (~60-80/s) | 1 petición |
| Recarga completa de Tab Admin en medio del ciclo | Muestra "EstudianteA BajoVisual" (`sub` idéntico al de la Ficha 01, `iat` posterior al login del Admin) | Ver "Gap residual" abajo |
| Mismo usuario en 2 pestañas (login+login) | — | Ambas quedan logueadas, sin logout forzado, sin ráfaga (+4 peticiones normales) |

### Gap residual (Ficha 01 — PARCIALMENTE RESUELTO)

El fix cierra la vía **reactiva** (mientras la pestaña sigue montada, ya
no opera en silencio bajo una identidad ajena — se desloguea
explícitamente). **No cierra la vía de hidratación fresca**: una recarga
completa *posterior* de la pestaña ya deslogueada todavía puede
rehidratar la sesión de la otra pestaña, porque ambas siguen compartiendo
la misma clave física `localStorage['upao-auth']`. Verificado en vivo:
tras el fix, una recarga completa de Tab Admin (ya deslogueada) hacia
`/admin/roles` volvió a mostrar "EstudianteA BajoVisual", con el token
completo de EstudianteA en `localStorage`.

Cerrar esto por completo requiere una decisión arquitectónica —
`sessionStorage` (aislado por pestaña, sin clave física compartida) vs.
`BroadcastChannel`/`SharedWorker` vs. otra — deliberadamente **diferida a
un Engineering Gate propio** ("Persistencia de autenticación entre
pestañas"), no incluida en este fix por decisión explícita: mezclar un
bugfix con un cambio de arquitectura de persistencia dificulta aislar
regresiones.

## Resolución final (Ficha 01 — commit `66c3f00`)

### Causa raíz del gap residual

El gap descrito arriba ("Gap residual") no era un defecto del guard de
identidad de `handleStorageChange` — ese guard es correcto para la vía
**reactiva** (mientras la pestaña sigue montada). El gap vivía un nivel
más abajo: `localStorage` es una única clave física **compartida entre
todas las pestañas del mismo origen**, sin importar cuántos guards
reactivos existan sobre ella. La hidratación inicial de zustand
(`onRehydrateStorage`) lee esa clave física directamente, sin pasar por
ningún guard — por diseño, una recarga completa de cualquier pestaña
adopta lo último que haya en esa clave, sea de quien sea.

### Decisión

`persist.storage` de zustand (`frontend/src/stores/authStore.ts`) pasa
de `localStorage` a `sessionStorage` vía `createJSONStorage(() =>
sessionStorage)`. `sessionStorage` está aislado por pestaña por
especificación del navegador — no hay clave física compartida que leer
en la hidratación, así que no hay nada que "adoptar" de otra pestaña.

**Alternativas evaluadas y descartadas:** `BroadcastChannel`/
`SharedWorker` para sincronizar `localStorage` entre pestañas de forma
explícita y controlada — descartado por mayor complejidad e introducir
una responsabilidad nueva (un canal de mensajería activo) para resolver
lo que `sessionStorage` resuelve de forma pasiva y sin superficie
adicional.

**Trade-off de UX aceptado, no un bug:** una pestaña nueva (`Ctrl+T`, o
`Ctrl+clic` en un enlace) ya no hereda la sesión activa de otra pestaña
— debe loguearse. No hay evidencia de que "sesión compartida entre
pestañas nuevas" fuera un requerimiento real del producto (no aparece en
ningún RFC/ADR/CLAUDE.md); es un efecto colateral de haber usado
`localStorage` por defecto, no una decisión de diseño original.

### Validación en vivo (Postgres real, cuenta de prueba Admin)

- `localStorage['upao-auth']` = `null` tras login; `sessionStorage
  ['upao-auth']` poblado.
- Pestaña nueva hacia `/admin`: **no** hereda la sesión, redirige a
  `/login` desde cero — la pestaña original permanece intacta con su
  propia sesión (aislamiento real, no solo teórico).
- Recorrido normal de un actor (login → navegación entre `/admin`,
  `/admin/roles`, `/admin/users`, `/evidencia/runtime` → logout) sin
  regresiones.
- `tsc`: 0 errores. `eslint`: 0 issues en el archivo modificado.

### Impacto en la sección "Gap residual" de arriba

Queda resuelto: ya no existe una clave física compartida de la que una
recarga completa pueda leer la identidad de otra pestaña.

## Hallazgo aparte, NO corregido aquí (fuera de alcance)

La propagación de logout entre pestañas del **mismo** usuario (rama
`!e.newValue`, el propósito original de este listener) no funciona en la
práctica: `logout()` en `authStore.ts` nunca llama a
`localStorage.removeItem` — solo escribe `{token:null,...}` (un JSON
válido no vacío), así que `e.newValue` nunca es falsy y esa rama nunca se
alcanza. Preexistente en ambas versiones del código (antes y después de
este fix), no introducido ni agravado aquí.
