# Bug Report

## Metadata
- **ID:** BUG-003
- **Fecha:** 2026-05-27
- **Severidad:** HIGH
- **Categoría:** frontend/cache
- **Tipo:** frontend, runtime, observability
- **Estado:** FIXED

## Síntomas

1. Después del login, todas las queries de React Query se disparan simultáneamente
2. El dashboard de admin carga lentamente porque decenas de queries se fetchan desde cero
3. La query `['auth', 'me']` se dispara inmediatamente, compitiendo con `validateSession()`
4. El usuario ve un "flash" de datos vacíos antes de que lleguen las respuestas
5. En el panel de Red de DevTools: docenas de requests simultáneos después del login

## Root Cause

### Análisis forense

En `useAuth.ts:23`, el callback `onSuccess` del login mutation contenía:

```typescript
onSuccess: (data) => {
    storeLogin(data.access_token, data.refresh_token, data.user)
    queryClient.clear()  // ← ELIMINA TODO EL CACHE DE REACT QUERY
    const role = data.user.role
    if (role === 'admin') navigate('/admin')
    // ...
}
```

`queryClient.clear()` es el mecanismo de **reset total** de React Query. Su documentación dice:

> `clear()`: Removes all cached queries from memory. This will cause all active queries to be garbage collected and refetched if they are currently being used.

El problema es triple:

1. **Perder todo el cache:** Cualquier query que estuviera cacheadas (rol del usuario, datos del curso, perfil) se elimina, forzando un refetch completo

2. **Disparo masivo de refetches:** Todos los componentes montados que usen `useQuery` detectan que su cache fue eliminado y disparan refetches inmediatos. Si el dashboard de admin tiene 15 queries de datos, las 15 se disparan simultáneamente.

3. **Efecto dominó en auth:** La query `['auth', 'me']` pierde su cache y se dispara inmediatamente. Pero `validateSession()` también se dispara por el cambio de `token`. Dos calls concurrentes a `/api/auth/me` (ver BUG-002).

### La paradoja del cache

La intención original de `queryClient.clear()` era probablemente "limpiar datos viejos del usuario anterior antes de cargar los del nuevo usuario". Pero esto es innecesario porque:

- **React Query ya maneja stale state:** Las queries tienen `staleTime` configurado
- **Las queryKeys incluyen contexto:** Las queries deberían incluir `userId` o similar para evitar mezclar datos entre sesiones
- **navigate('/admin') re-monta componentes:** Al navegar, los componentes del dashboard se montan y sus queries se disparan con estado fresco

### Flujo exacto

```
T+0ms  storeLogin() → isAuthenticated=true, token=xxx
T+0ms  queryClient.clear()
       └── Elimina: ['auth', 'me'], ['courses'], ['students'], ['metrics'], etc.
T+1ms  authStore cambia → AuthProvider re-render
T+1ms  useEffect(token) → validateSession() → /api/auth/me
T+2ms  navigate('/admin') → se monta AdminLayout
T+2ms  meQuery: ['auth', 'me'] no está en cache → se dispara → /api/auth/me
T+3ms  AdminMetrics: ['metrics'] no está en cache → se dispara → /api/metrics
T+3ms  CoursesList: ['courses'] no está en cache → se dispara → /api/courses
T+3ms  StudentsTable: ['students'] no está en cache → se dispara → /api/students
T+3ms  UserProfile: ['profile'] no está en cache → se dispara → /api/profile
       ... más queries según el dashboard

       RESULTADO: 15+ requests concurrentes en los primeros 100ms después del login
```

## Flujo de reproducción

1. Configurar React Query DevTools
2. Hacer login con cualquier usuario
3. Observar en React Query DevTools: todas las queries aparecen como "fetching" simultáneamente
4. Observar en Network tab: múltiples requests saliendo en paralelo
5. Especialmente notable cuando hay datos cacheados de una sesión previa

## Riesgo arquitectónico

- **ALTO**: `queryClient.clear()` es una operación nuclear que no discrimina. Elimina queries que no tienen nada que ver con el login.
- Crea un **thundering herd problem**: todas las queries se disparan al mismo tiempo, potencialmente abrumando el backend
- Empeora la race condition de BUG-002 porque fuerza a `meQuery` a dispararse inmediatamente
- Elimina queries cacheadas intencionalmente (como `['course', '1']`) que no deberían cambiar por un login

## Impacto en swarm

- **MEDIO**: Los agentes del swarm que lean datos vía React Query (e.g., estado de sesión, métricas) recibirán datos inconsistentes durante el refetch masivo. Si un agente lee estado de sesión en el momento exacto del clear, puede obtener datos vacíos.

## Impacto en adaptación

- **MEDIO**: Las queries de adaptación (pathways, cognitive stage) pierden su cache. Si un estudiante inicia sesión después de haber sido evaluado, las evaluaciones previas deben refetchearse, causando latencia en la adaptación inicial.

## Impacto en consenso

- **BAJO**: El consenso opera sobre datos en memoria (agentes del swarm), no sobre datos cacheados en React Query.

## Impacto en resiliencia

- **BAJO-MEDIO**: No afecta la resiliencia del auth flow directamente, pero la tormenta de refetches puede causar timeouts en el backend si hay muchos usuarios logueándose simultáneamente.

## Impacto en shared memory

- **NULO**

## Fix implementado

### Estrategia: Eliminar `queryClient.clear()` completamente

El fix es eliminar la línea. No hay ninguna razón válida para borrar TODO el cache de React Query después de un login:

```typescript
onSuccess: (data) => {
    storeLogin(data.access_token, data.refresh_token, data.user)
    // ❌ ANTES: queryClient.clear()
    // ✅ DESPUÉS: no se limpia nada — las queries existentes tienen staleTime configurado
    //    y el navigate() al dashboard re-monta componentes que disparan sus propias queries.
    const role = data.user.role
    if (role === 'admin') navigate('/admin')
    // ...
}
```

### Comentario de advertencia agregado

Se agregó un comentario explícito para prevenir que alguien reintroduzca este patrón:

```typescript
// WARNING: do NOT call queryClient.clear() here — it wipes ALL cached
// queries and races meQuery against validateSession, causing intermittent
// logouts. The meQuery cache entry will naturally become stale.
```

## Tests agregados

### Test de integración necesario (pendiente)

```typescript
it('should NOT clear cache after login', async () => {
    // Pre: tener queries cacheadas
    queryClient.setQueryData(['courses'], mockCourses)
    
    // Hacer login
    await loginMutation.mutateAsync({ identifier: 'admin@upao.edu.pe', password: 'Admin2026!' })
    
    // Verificar: ['courses'] sigue en cache
    expect(queryClient.getQueryData(['courses'])).toEqual(mockCourses)
})
```

## Riesgos futuros

1. **Datos entre sesiones:** Si las queries no incluyen el userId en su queryKey, los datos de un usuario anterior pueden mostrarse brevemente antes de que el refetch los reemplace. Esto debería manejarse con queryKeys contextuales (e.g., `['courses', userId]`), no con `clear()`.
2. **Datos stale:** Si un admin modifica datos de otro usuario y luego hace login como ese usuario, los datos cacheados pueden estar desactualizados. Esto se maneja con `staleTime` (30s en la configuración actual) y `refetchOnMount: true` (por defecto en React Query).

## Observability recomendada

1. **Métrica de query cache size:** Monitorear el tamaño del cache de React Query. Un clear se detectaría como una caída a 0.
2. **Métrica de refetch storms:** Contar cuántas queries se disparan en los primeros 100ms después de un login. Si >3, alertar.
3. **Log de queryClient.clear():** Si alguien llama a `clear()`, loguear stack trace y contexto.

## Regression prevention

1. **Search-based code review:** Buscar `queryClient.clear()` en el codebase y requerir revisión obligatoria para cada uso
2. **Linting rule:** `no-restricted-calls` para `queryClient.clear()` con un mensaje que obligue a justificar su uso
3. **Test de snapshot del cache:** Test que verifique que después del login, el cache de React Query no se modifica

## Archivos afectados

| Archivo | Líneas | Cambio |
|---------|--------|--------|
| `frontend/src/hooks/useAuth.ts` | 23 | Eliminado queryClient.clear() y agregado comentario |

## Lecciones aprendidas

1. **`queryClient.clear()` es un code smell:** Su presencia indica que no se está manejando correctamente la granularidad del cache. Las queries deben invalidarse individualmente.
2. **Preferir `invalidateQueries` con filtro:** Si realmente se necesita refrescar datos después del login, usar `queryClient.invalidateQueries({ queryKey: ['auth'] })` en lugar de borrar todo.
3. **React Query tiene staleTime por una razón:** Usar `staleTime` para controlar cuándo los datos se consideran desactualizados, no `clear()` para reiniciar.
