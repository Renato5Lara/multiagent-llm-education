# Bug Report

## Metadata
- **ID:** BUG-006
- **Fecha:** 2026-05-27
- **Severidad:** LOW
- **Categoría:** frontend/ux
- **Tipo:** frontend, runtime, observability
- **Estado:** FIXED

## Síntomas

1. Cuando el IP rate limiter bloquea un login (429), el mensaje mostrado dice "5 minutos" pero el bloqueo real es de 60 segundos
2. Cuando el account lockout bloquea un login (429), el mensaje mostrado dice "5 minutos" (correcto) pero no muestra el tiempo exacto restante
3. El usuario ve un mensaje genérico que no refleja la causa real del bloqueo ni el tiempo de espera exacto
4. No hay diferenciación visual entre IP rate limit (defensa secundaria, 60s) vs account lockout (defensa primaria, 5 min)

## Root Cause

### Análisis forense

En `Login.tsx:63-68`, el bloque de 429 tenía un mensaje hardcodeado:

```tsx
{loginError && axios.isAxiosError(loginError) && loginError.response?.status === 429 && (
    <div className="flex items-start gap-3 p-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm">
        <Clock className="h-5 w-5 mt-0.5 shrink-0 text-red-500" />
        <span>Cuenta bloqueada temporalmente por múltiples intentos fallidos. Intente de nuevo en 5 minutos.</span>
    </div>
)}
```

El problema es que el backend tiene DOS mecanismos que retornan 429 con diferentes tiempos de espera:

| Mecanismo | Código HTTP | `detail.code` | Tiempo de espera | Mensaje |
|-----------|------------|---------------|-------------------|---------|
| IP Rate Limiter | 429 | `IP_RATE_LIMITED` | 60 segundos | "Demasiados intentos. Intenta de nuevo en 60 segundos." |
| Account Lockout | 429 | `ACCOUNT_LOCKED` | 5 minutos | "Cuenta bloqueada temporalmente..." |

El frontend hardcodeaba "5 minutos" para AMBOS casos, lo que es incorrecto para el IP rate limiter (60s ≠ 5min).

Además, el `detail` del IP rate limiter originalmente era un string (no un objeto con `message`), lo que hacía imposible extraer el tiempo de espera sin parsear el string:

```python
# IP rate limiter (ANTES):
return JSONResponse(
    content={
        "detail": "Demasiados intentos...",    # ← STRING, no objeto
        "status_code": 429,
        "retry_after_seconds": 60,
    }
)

# Account lockout:
raise HTTPException(
    detail={
        "message": "Cuenta bloqueada...",      # ← OBJETO con .message
        "retry_after_minutes": 5,
        "code": "ACCOUNT_LOCKED",
    }
)
```

La inconsistencia en el formato del `detail` (string vs objeto) impedía que el frontend procesara ambos casos unificadamente.

## Flujo de reproducción

1. Configurar el IP rate limiter para bloquear rápidamente
2. Hacer 6 login attempts incorrectos desde la misma IP
3. Observar: mensaje "Cuenta bloqueada... Intente de nuevo en 5 minutos"
4. Esperar 60 segundos (el bloqueo real del IP rate limiter expira)
5. Intentar login nuevamente → funciona
6. **El mensaje mintió:** dijo "5 minutos" pero el bloqueo real fue de 60 segundos

```
T+0s: 6 intentos fallidos → 429 "5 minutos"
T+0s: Real bloqueo: IP rate limiter (60s)
T+60s: IP rate limiter expira → se puede reintentar ✓
T+60s: usuario cree que son 5 minutos → espera innecesariamente hasta T+300s
```

## Riesgo arquitectónico

- **BAJO**: No afecta la funcionalidad del sistema, solo la UX
- Pero la desinformación al usuario puede causar:
  - Soporte técnico innecesario ("la página dice 5 minutos pero me deja entrar en 1 minuto")
  - Frustración por esperar más de lo necesario
  - Desconfianza en los mensajes del sistema

## Impacto en swarm

- **NULO**

## Impacto en adaptación

- **NULO**

## Impacto en consenso

- **NULO**

## Impacto en resiliencia

- **NULO**

## Impacto en shared memory

- **NULO**

## Fix implementado

### Estrategia: Mensaje dinámico basado en el response del backend

Se reemplazó el mensaje hardcodeado con lógica que lee `detail.code`, `detail.retry_after_seconds`, y `detail.retry_after_minutes` del servidor:

```tsx
{loginError && axios.isAxiosError(loginError) && loginError.response?.status === 429 && (
    <div className="flex items-start gap-3 p-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm">
        <Clock className="h-5 w-5 mt-0.5 shrink-0 text-red-500" />
        <span>
            {(() => {
                const detail = loginError.response?.data?.detail
                if (typeof detail === 'object' && detail?.message) {
                    const retryAfter = detail.retry_after_seconds
                        ?? (detail.retry_after_minutes ? detail.retry_after_minutes * 60 : null)
                    const retryText = retryAfter
                        ? retryAfter >= 120
                            ? `Intente de nuevo en ${Math.round(retryAfter / 60)} minutos.`
                            : `Intente de nuevo en ${retryAfter} segundos.`
                        : ''
                    return `${detail.message} ${retryText}`
                }
                if (typeof detail === 'string') return detail
                return 'Demasiados intentos. Intente de nuevo más tarde.'
            })()}
        </span>
    </div>
)}
```

Además, el IP rate limiter se modificó para que su `detail` sea un objeto con formato consistente (como el account lockout):

```python
# IP rate limiter (DESPUÉS):
{
    "detail": {
        "message": "Demasiados intentos...",
        "retry_after_seconds": 60,
        "code": "IP_RATE_LIMITED",
    }
}
```

### Archivos modificados

1. `frontend/src/pages/Login.tsx:63-68` — Mensaje dinámico basado en response
2. `backend/app/middleware/rate_limit.py:56-62` — detail como objeto (consistente con account lockout)

## Tests agregados

No se agregaron tests automatizados. Verificación manual:

1. Inducir IP rate limit → mensaje muestra "Demasiados intentos. Intente de nuevo en 60 segundos."
2. Inducir account lockout → mensaje muestra "Cuenta bloqueada... Intente de nuevo en 5 minutos."
3. Verificar que el icono Clock aparece en ambos casos

## Riesgos futuros

1. Si el backend agrega un tercer tipo de 429 con otro formato, el frontend necesita actualización.
2. La lógica de conversión `retry_after_minutes * 60` asume que minutos es el formato del account lockout. Si esto cambia, la conversion es incorrecta.
3. **Fallback:** Si `detail` no tiene `message` ni `retry_after_*`, se muestra un mensaje genérico, lo cual es aceptable.

## Observability recomendada

1. **Métrica de 429 por tipo:** Contar 429 separados por `detail.code` (IP_RATE_LIMITED vs ACCOUNT_LOCKED)
2. **User feedback:** Monitorear cuántos usuarios ven cada tipo de mensaje para entender el ratio real de bloqueos IP vs account
3. **Log de UX confusión:** Si un usuario recibe un 429 y luego logra login exitoso en menos del tiempo indicado, loguear para revisar precisión del mensaje

## Regression prevention

1. **API contract test:** Test que verifica que `POST /api/auth/login` retorna `detail` como objeto con `message`, `code`, y campos de tiempo
2. **TypeScript type:** Definir un tipo `Login429Response` con `detail: { message: string; code: string; retry_after_seconds?: number; retry_after_minutes?: number }` para tipado estático
3. **Schema validation:** Usar Pydantic en el backend para validar que el response de error tiene formato consistente

## Archivos afectados

| Archivo | Líneas | Cambio |
|---------|--------|--------|
| `frontend/src/pages/Login.tsx` | 63-68 | Mensaje dinámico desde response |
| `backend/app/middleware/rate_limit.py` | 56-62 | detail como objeto con formato consistente |

## Lecciones aprendidas

1. **API contract consistency:** Los mensajes de error deben tener un formato consistente, especialmente cuando el mismo código HTTP (429) se usa para diferentes mecanismos.
2. **Frontend defensivo:** El frontend nunca debe hardcodear mensajes que dependen de lógica del backend. Siempre debe leer la respuesta del servidor.
3. **Tiempo de espera preciso:** Mostrar el tiempo de espera exacto mejora la UX y reduce tickets de soporte.
4. **No asumir formato:** Cuando se usa `typeof detail === 'string'` como fallback, se asume que el backend podría enviar string u objeto. Es mejor estandarizar a objeto siempre.
