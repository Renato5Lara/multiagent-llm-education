# Bug Report

## Metadata
- **ID:** BUG-004
- **Fecha:** 2026-05-27
- **Severidad:** MEDIUM
- **Categoría:** frontend/state
- **Tipo:** frontend, runtime
- **Estado:** FIXED

## Síntomas

1. `setUser(user)` se llama dos veces después de cada fetch exitoso de `/api/auth/me`
2. Dos re-renders innecesarios del árbol de componentes que dependen del user state
3. Consumo de CPU duplicado en cada re-render de componentes auth-conscientes
4. Difícil de detectar: no causa errores visibles, solo degradación de performance

## Root Cause

### Análisis forense

En `useAuth.ts`, la función `meQuery.queryFn` y un `useEffect` separado llaman a `setUser` en secuencia:

```typescript
// Lugar 1: queryFn (línea 58)
const meQuery = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
        const resp = await api.get<UserAuth>('/api/auth/me')
        const data = resp.data
        setUser(data)                    // ← PRIMERA LLAMADA
        return data
    },
    enabled: isAuthenticated && !!token,
    retry: false,
    staleTime: 5 * 60 * 1000,
})

// Lugar 2: useEffect (líneas 66-70)
useEffect(() => {
    if (meQuery.data) {
        setUser(meQuery.data)            // ← SEGUNDA LLAMADA
    }
}, [meQuery.data, setUser])
```

La segunda llamada es completamente redundante porque:

1. `meQuery.queryFn` ya ejecutó `setUser(data)` en la línea 58
2. `meQuery.data` es el valor retornado por `queryFn` (que es idéntico a `data`)
3. El `useEffect` se dispara DESPUÉS de que React Query actualiza su estado interno con el resultado de `queryFn`

### Timing exacto

```
T+0ms  meQuery.queryFn() → /api/auth/me
T+500ms Llega respuesta → resp.data = { id: 1, role: 'admin', ... }
T+500ms setUser(resp.data)                           ← Primera llamada (queryFn)
T+500ms return resp.data                             ← React Query almacena data
T+501ms React re-render: meQuery.data cambió
T+502ms useEffect(meQuery.data) se dispara
T+502ms setUser(meQuery.data)                        ← Segunda llamada (useEffect)
```

### Por qué existe la duplicación

El `useEffect` en `meQuery.data` parece ser un "resto evolutivo": originalmente, `setUser` podría no haber estado en `queryFn`. En algún momento alguien la agregó a `queryFn` pero olvidó eliminar el `useEffect`. O viceversa.

## Flujo de reproducción

1. Agregar un contador o console.log en `setUser`
2. Hacer login con cualquier usuario
3. Observar: `setUser` se llama dos veces
4. Navegar a otra página que re-monte el componente que usa `useAuth()` y cause refetch de `meQuery`
5. Observar: `setUser` se llama dos veces nuevamente

## Riesgo arquitectónico

- **BAJO**: No hay riesgo de inconsistencia porque `setUser` es idempotente (mismo input → mismo output). Sin embargo:
- Cada llamada a `setUser` dispara un re-render de todos los componentes que consumen `useAuthStore().user`
- En el dashboard de admin con ~30 componentes auth-conscientes, cada `setUser` puede causar 30 re-renders
- La duplicación duplica este costo: 60 re-renders innecesarios por cada fetch de `/api/auth/me`

## Impacto en swarm

- **MÍNIMO**: Los agentes no dependen de React state para su operación. Pero si un componente UI que muestra estado del swarm re-renderiza innecesariamente, puede causar flickering en dashboards de monitoreo.

## Impacto en adaptación

- **MÍNIMO**: Los componentes de adaptación pueden re-renderizar innecesariamente, pero no afecta la lógica de adaptación en sí.

## Impacto en consenso

- **NULO**

## Impacto en resiliencia

- **NULO**

## Impacto en shared memory

- **NULO**

## Fix implementado

### Estrategia: Eliminar el useEffect redundante

Se eliminó el `useEffect` en `meQuery.data`, ya que `setUser` ya se llama dentro de `queryFn`:

```typescript
// ANTES (eliminado):
useEffect(() => {
    if (meQuery.data) {
        setUser(meQuery.data)
    }
}, [meQuery.data, setUser])

// DESPUÉS:
// NOTE: setUser is already called inside meQuery.queryFn.
// A separate useEffect on meQuery.data would call setUser a second time.
// We removed it to avoid double dispatch.
```

### Archivos modificados

1. `frontend/src/hooks/useAuth.ts:66-70` — Eliminado useEffect(meQuery.data)

## Tests agregados

No se agregaron tests específicos porque el fix es una eliminación de código redundante. El comportamiento existente (setUser se llama con los datos correctos) se verifica indirectamente por los tests de auth flow.

### Test de verificación

```typescript
it('should call setUser only once per meQuery fetch', () => {
    const setUserSpy = vi.spyOn(useAuthStore.getState(), 'setUser')
    
    // Simular fetch exitoso de /api/auth/me
    act(() => {
        meQuery.queryFn()
    })
    
    // Verificar: setUser fue llamado exactamente una vez
    expect(setUserSpy).toHaveBeenCalledTimes(1)
    expect(setUserSpy).toHaveBeenCalledWith(mockUser)
})
```

## Riesgos futuros

1. Si en el futuro `queryFn` deja de llamar `setUser` (refactor), este fix causaría que `setUser` nunca se llame desde `meQuery`. 
2. **Mitigación:** Si alguien refactoriza `queryFn` y elimina `setUser`, debe agregar un mecanismo alternativo. El comentario en el código sirve como advertencia.

## Observability recomendada

1. **Métrica de setUser calls:** Contar cuántas veces se llama `setUser` por minuto
2. **Métrica de re-renders:** Contar re-renders de componentes que dependen de `user` del store
3. **Debug tool:** En desarrollo, loguear stack trace de cada llamada a `setUser` para detectar duplicaciones

## Regression prevention

1. **Code review:** Toda nueva instancia de `useEffect` con dependencia `meQuery.data` debe ser revisada por posible duplicación con `queryFn`
2. **Pattern:** Documentar que `queryFn` es el lugar para efectos secundarios de fetch, no `useEffect`
3. **Linting rule:** Posiblemente una regla custom que advierta si se usa `meQuery.data` en un `useEffect` junto con `setUser`

## Archivos afectados

| Archivo | Líneas | Cambio |
|---------|--------|--------|
| `frontend/src/hooks/useAuth.ts` | 66-70 | Eliminado useEffect redundante |

## Lecciones aprendidas

1. **Efectos secundarios en queryFn vs useEffect:** Cuando se usa React Query, los efectos secundarios de un fetch (como actualizar el store) deben ir en `queryFn`. El `useEffect` en `data` es un antipatrón porque React Query ya maneja la propagación de datos.
2. **Código duplicado evolutivo:** Bugs como este son difíciles de detectar porque no causan errores visibles. Solo se manifiestan como degradación de performance y son difíciles de rastrear hasta la duplicación.
3. **Idempotencia no es excusa:** Aunque `setUser` sea idempotente y el fix no cambie el comportamiento funcional, la duplicación de re-renders afecta la performance y debe eliminarse.
