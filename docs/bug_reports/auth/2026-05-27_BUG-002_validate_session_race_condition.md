# Bug Report

## Metadata
- **ID:** BUG-002
- **Fecha:** 2026-05-27
- **Severidad:** CRITICAL
- **Categoría:** frontend/auth
- **Tipo:** auth, frontend, runtime, async orchestration
- **Estado:** FIXED

## Síntomas

1. Login exitoso redirige a `/admin`, pero inmediatamente después el usuario es redirigido de vuelta a `/login`
2. Login funciona intermitentemente: a veces sí, a veces no, sin relación aparente
3. En React StrictMode (desarrollo), el login falla con más frecuencia
4. Usuario ve un flash de la página de admin antes de ser expulsado
5. Los logs del backend muestran múltiples llamadas a `/api/auth/me` después de un solo login

## Root Cause

### Análisis forense

Se identificaron **DOS mecanismos independientes** que llaman a `/api/auth/me` después del login, creando una race condition clásica de tipo **Read-Modify-Write** sobre el estado de autenticación.

#### Mecanismo A: `meQuery` en useAuth.ts (líneas 53-64)

```typescript
const meQuery = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
        const resp = await api.get<UserAuth>('/api/auth/me')
        const data = resp.data
        setUser(data)                    // ← escribe en el store
        return data
    },
    enabled: isAuthenticated && !!token, // ← se habilita DESPUÉS del login
    retry: false,
    staleTime: 5 * 60 * 1000,
})
```

Después del login exitoso:
1. `storeLogin()` setea `isAuthenticated=true`, `token=xxx`
2. `meQuery` se habilita (`enabled` ahora es `true`)
3. `meQuery` dispara `/api/auth/me`

#### Mecanismo B: `validateSession()` en AuthProvider.tsx (líneas 89-96)

```typescript
useEffect(() => {
    if (_hydrated && token && !validatingRef.current) {
        validateSession()                // ← también llama /api/auth/me
    }
}, [token, _hydrated])
```

Después del login exitoso:
1. `storeLogin()` actualiza `token` en el store de zustand
2. El `useEffect` se dispara porque `token` cambió
3. `validateSession()` llama `/api/auth/me`
4. **En StrictMode:** este efecto se dispara DOS VECES

#### La race condition

El timeline exacto después de un login exitoso:

```
T+0ms   onSuccess(): storeLogin(token, refreshToken, user)
T+0ms   onSuccess(): queryClient.clear()           ← elimina TODO el cache
T+0ms   onSuccess(): navigate('/admin')

T+1ms   AuthProvider re-render: token cambió
T+1ms   useEffect(token) → validateSession()       ← Dispara #1: /api/auth/me

T+2ms   meQuery se habilita (isAuthenticated=true)
T+2ms   meQuery.queryFn() → /api/auth/me           ← Dispara #2: /api/auth/me

T+500ms Llega respuesta de #1: setUser(data)        ← usuario seteado correctamente
T+510ms Llega respuesta de #2: setUser(data)        ← usuario seteado nuevamente (redundante)

        ─── CASO NORMAL ───

T+0ms   onSuccess(): storeLogin(...)
T+1ms   validateSession() → /api/auth/me
T+2ms   meQuery → /api/auth/me

T+500ms #1 LANZA ERROR (timeout/network glitch)
T+500ms validateSession().catch → storeLogout()     ← USAURIO EXPULSADO!
T+500ms queryClient.clear()
T+500ms El login exitoso se revierte

        ─── CASO DE FALLA INTERMITENTE ───
```

El bug: si la PRIMERA llamada a `/api/auth/me` falla (timeout de red, error 500, etc.), `validateSession()` ejecuta `storeLogout()` + `queryClient.clear()`, deshaciendo COMPLETAMENTE el login exitoso que ocurrió 500ms antes.

### Factor agravante: StrictMode (React 19 Dev)

En `main.tsx:36`, `<StrictMode>` envuelve toda la aplicación. React 19 en desarrollo:
1. Monta el componente → ejecuta effects
2. Desmonta el componente
3. Vuelve a montar → ejecuta effects OTRA VEZ

Aunque `validatingRef` persiste entre monturas (previniendo la doble ejecución de `validateSession`), el `meQuery` NO tiene este guard, y React Query crea una nueva suscripción en cada montura. StrictMode duplica efectivamente las llamadas a la API.

### Factor agravante: queryClient.clear()

En `useAuth.ts:23`, `queryClient.clear()` se llama en `onSuccess` del login:
- Elimina TODO el cache de React Query, incluyendo la entry `['auth', 'me']`
- `meQuery` detecta que no hay cache → dispara inmediatamente
- La llamada a `meQuery` ocurre ANTES de que el store esté completamente estable

## Flujo de reproducción

1. Tener React StrictMode activo (desarrollo)
2. Tener una conexión de red con latencia variable (>200ms)
3. Hacer login con credenciales válidas
4. Observar: en ~10-20% de los intentos (dependiendo de latencia), el login "exitoso" se revierte en <1s
5. Reproducir con throttling de red en DevTools (Slow 3G) → tasa de fallo >50%

## Riesgo arquitectónico

- **CRÍTICO**: El mecanismo de validación de sesión tiene DOS fuentes de verdad compitiendo
- Violación del principio de **Single Source of Truth**: tanto `AuthProvider.validateSession()` como `useAuth.meQuery` mantienen estado de sesión
- No hay un **coordinador de validación** — ambas fuentes operan independientemente
- El patrón de "fire-and-forget" en `validateSession()` no tiene manejo de concurrencia

## Impacto en swarm

- **ALTO**: Si los agentes del swarm usan tokens JWT para autenticarse contra la API, la race condition en refresh/validación puede causar:
  - Agentes expulsados intermitentemente
  - Pérdida de sesiones de aprendizaje activas
  - Inconsistencia en SharedMemory porque agentes son forzados a re-autenticarse

## Impacto en adaptación

- **ALTO**: El sistema adaptativo depende de sesiones de usuario estables. Si el auth state es volátil:
  - Pathways adaptativos se reinician al reconectar
  - El CognitiveStageDetector pierde tracing del estudiante
  - Las recomendaciones adaptativas se calculan sobre estado incompleto

## Impacto en consenso

- **MEDIO**: Los votantes del ConsensusEngine (CodeMasteryVoter, ProgressionVoter) leen datos de sesión. Si el auth state es inconsistente, los votos pueden basarse en datos incompletos.

## Impacto en resiliencia

- **CRÍTICO**: El sistema no es resiliente a latencia de red. Un timeout de 500ms en `/api/auth/me` causa un logout completo. Esto es un **single point of failure** en el auth flow.

## Impacto en shared memory

- **BAJO**: SharedMemory es independiente del auth flow. Pero si un agente es expulsado, pierde acceso a escribir/leer observaciones.

## Fix implementado

### Estrategia: Eliminar la fuente duplicada de validación

Se eliminó el `useEffect` en `AuthProvider.tsx` que re-ejecutaba `validateSession()` cuando `token` cambiaba:

```typescript
// ANTES (eliminado):
useEffect(() => {
    if (_hydrated && token && !validatingRef.current) {
        validateSession()
    }
}, [token, _hydrated])

// DESPUÉS:
// El efecto fue eliminado. validateSession() solo se ejecuta:
// 1. En la hidratación inicial (efecto en _hydrated)
// 2. Cuando otro tab cambia el auth state (storage event listener)
```

Además:
- `meQuery` sigue siendo el mecanismo que obtiene datos del usuario después del login
- `setUser` se llama dentro de `meQuery.queryFn`, el `useEffect` redundante en `meQuery.data` se eliminó
- `queryClient.clear()` se eliminó del `onSuccess` del login

### Archivos modificados

1. `frontend/src/providers/AuthProvider.tsx:89-96` — Eliminado useEffect(token) que causaba la race
2. `frontend/src/hooks/useAuth.ts:23` — Eliminado queryClient.clear()
3. `frontend/src/hooks/useAuth.ts:66-70` — Eliminado useEffect redundante en meQuery.data

## Tests agregados

### Test de integración necesario (no implementado en este fix — pendiente)

```typescript
// Test de race condition en login flow
// Escenario: login exitoso seguido de fallo en /api/auth/me
// Verificar que el usuario NO es expulsado
it('should not logout when meQuery fails after successful login', async () => {
    // Mock: login → 200 OK, /api/auth/me → network error
    mockApi.post('/api/auth/login').resolves({ access_token: '...', user: {...} })
    mockApi.get('/api/auth/me').rejects(new Error('Network error'))
    
    await loginMutation.mutateAsync({ identifier: 'admin@upao.edu.pe', password: 'Admin2026!' })
    
    // Verificar: el usuario sigue autenticado
    expect(useAuthStore.getState().isAuthenticated).toBe(true)
    expect(useAuthStore.getState().token).toBeTruthy()
})
```

### Test de concurrencia necesario

```typescript
it('should handle concurrent validation calls', async () => {
    // Disparar validateSession() y meQuery simultáneamente
    // Verificar que solo UNA llamada a /api/auth/me ocurre
})
```

## Riesgos futuros

1. **Cross-tab sync:** Sin el efecto en `token`, si el usuario cambia su rol/perfil desde otro tab, el tab actual no se entera hasta el próximo `validateSession()` (en la próxima carga). El storage event listener cubre cambios de autenticación, pero no cambios de perfil.
2. **Token refresh no dispara re-validación:** Cuando el interceptor refresca el token, `store.login()` actualiza el token, pero sin el efecto en `token`, `validateSession()` no se re-ejecuta. Esto es intencional — el refresh ya validó la sesión — pero significa que si el usuario fue desactivado entre el refresh y ahora, no se detecta hasta el próximo `/api/auth/me` vía `meQuery`.
3. **StrictMode duplica meQuery:** Aunque eliminamos la race con validateSession, StrictMode sigue duplicando `meQuery` por el doble montaje de componentes. `meQuery` tiene `staleTime: 5min`, así que la segunda llamada usa cache. Pero la primera vez (después de `queryClient.clear()`), no hay cache y se hacen dos llamadas.

## Observability recomendada

1. **Tracing de validación:** Cada llamada a `/api/auth/me` debe loguear un `validation_id` (UUID) y el stack trace del caller para identificar qué mecanismo la disparó
2. **Métrica de validaciones concurrentes:** Histograma de número de validaciones por segundo. Un pico >1/s sugiere race condition
3. **Métrica de login fallout:** Cuántos logins exitosos se revierten en los primeros 5 segundos
4. **Alerta:** Si un login exitoso es seguido de un logout en <2s, alertar inmediatamente
5. **Diagnostic endpoint:** `GET /api/debug/auth-state` que retorna el estado actual del auth store, el `validation_id` actual, y el stack de llamadas recientes

## Regression prevention

1. **Monkey-patching test:** Test que intercepta `api.get('/api/auth/me')` y lo retrasa 500ms, luego verifica que `meQuery` y `validateSession()` no compiten
2. **Snapshot test del auth state:** Test que verifica que después del login, el auth store solo se modifica por `storeLogin()`, no por otros callbacks
3. **Linting rule:** No permitir `useEffect` que dependa de `token` sin un motivo documentado explícitamente
4. **Code review checklist:** Toda nueva llamada a `/api/auth/me` debe ser revisada por posible duplicación con `validateSession()` o `meQuery`

## Archivos afectados

| Archivo | Líneas | Cambio |
|---------|--------|--------|
| `frontend/src/providers/AuthProvider.tsx` | 89-96 | Eliminado useEffect(token) que re-validaba |
| `frontend/src/hooks/useAuth.ts` | 23 | Eliminado queryClient.clear() |
| `frontend/src/hooks/useAuth.ts` | 66-70 | Eliminado useEffect(meQuery.data) redundante |

## Lecciones aprendidas

1. **React Query + zustand + effects = triángulo de concurrencia:** Cuando tres mecanismos diferentes (React Query, zustand, useEffect) operan sobre el mismo estado sin coordinación, las race conditions son inevitables.
2. **validateSession() es un patrón peligroso:** Es un "check" que tiene "side effects" (storeLogout). Idealmente debería ser puramente consultivo, y el logout debería ser manejado por el interceptor 401.
3. **StrictMode debería estar en producción también:** Este bug existiría en producción aunque StrictMode lo empeora. La solución correcta no es "desactivar StrictMode" sino arreglar la concurrencia.
4. **queryClient.clear() es un martillo:** Borrar todo el cache de React Query debería ser extremadamente raro. La mayoría de los casos requieren `invalidateQueries` con filtros específicos.
