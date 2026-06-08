# Bug Report

## Metadata
- **ID:** BUG-001
- **Fecha:** 2026-05-27
- **Severidad:** CRITICAL
- **Categoría:** backend/auth
- **Tipo:** auth, runtime
- **Estado:** FIXED

## Síntomas

1. Usuario ingresa contraseña correcta pero recibe HTTP 429 "Demasiados intentos"
2. Usuario debe esperar 60 segundos incluso con credenciales válidas
3. El rate limiter bloquea usuarios legítimos después de 5 intentos totales (no 5 fallidos)
4. Confusión entre rate limit por IP vs account lockout por credenciales: el usuario no entiende por qué lo bloquean si la contraseña es correcta

## Root Cause

### Análisis forense

El `AuthRateLimiter.check()` en `rate_limit.py:29-31` implementaba un sliding window counter que SIEMPRE hacía `bucket.append(now)` en cada llamada, **antes** de que el backend procesara la solicitud:

```python
def check(self, ip: str) -> bool:
    now = time.monotonic()
    window_start = now - self.window_seconds
    bucket = self._buckets[ip]
    bucket[:] = [t for t in bucket if t > window_start]
    if len(bucket) >= self.max_requests:
        return False
    bucket.append(now)  # <--- SIEMPRE incrementa, incluso si el login es exitoso
    return True
```

El middleware en `make_auth_rate_limit_middleware()` llamaba `_limiter.check(ip)` antes de `await call_next(request)`, sin inspeccionar el código de respuesta. Esto significa que cada `POST /api/auth/login` consumía un slot del rate limiter independientemente del resultado.

### Flujo de reproducción exacto

```
T=0s  Usuario envía "admin@upao.edu.pe" + "Admin2026!"       → check("192.168.1.1") → 1/5 slots
T=5s  Usuario escribe mal "Admin2025!" (typo)                  → check("192.168.1.1") → 2/5 slots
T=10s Usuario escribe mal "admin2026!" (case error)            → check("192.168.1.1") → 3/5 slots
T=15s Usuario corrige y envía "Admin2026!" correcta           → check("192.168.1.1") → 4/5 slots ✓ login exitoso
T=20s Usuario recarga página, reintenta "Admin2026!" correcta → check("192.168.1.1") → 5/5 slots ✓ login exitoso
T=25s Usuario recarga, reintenta "Admin2026!"                 → check("192.168.1.1") → 6/5 slots → 429 BLOQUEADO
```

El usuario queda bloqueado **60 SEGUNDOS** con la contraseña correcta. La experiencia es: "me pide la contraseña, la pongo bien, me bloquea, espero, la pongo bien otra vez, me bloquea otra vez."

### Impacto arquitectónico

Este bug invalida completamente el propósito del rate limiter: proteger contra brute force sin afectar usuarios legítimos. Al contar requests exitosos, el rate limiter se convierte en un **ataque de denegación de servicio contra usuarios legítimos**. Es peor que no tener rate limiter.

### Diferenciación con account lockout

El sistema tiene DOS mecanismos de defensa:
1. **IP Rate Limiter** (5 requests/minuto, IP-based) — defensa secundaria contra brute force masivo
2. **Account Lockout** (3 fallos/5 minutos, por cuenta) — defensa primaria

BUG-001 hacía que el #1 bloqueara ANTES que el #2, anulando el account lockout como defensa primaria.

## Flujo de reproducción

1. Configurar `AuthRateLimiter(max_requests=3, window_seconds=60)`
2. Hacer 3 login attempts con contraseña incorrecta desde misma IP
3. Hacer 1 login attempt con contraseña correcta (esperar 200 OK)
4. Hacer 1 login attempt más con contraseña correcta (esperar 200 OK)
5. **Resultado:** 5º intento — 429 aunque credenciales correctas

## Riesgo arquitectónico

- **ALTO**: El rate limiter como denial-of-service para usuarios legítimos
- La separación de concerns entre rate limiting (IP-based) y account lockout (credential-based) se rompe porque el primero se dispara antes
- En producción con múltiples usuarios detrás de NAT corporativa, una sola IP compartida puede quedar bloqueada para todos

## Impacto en swarm

Indirecto: si los agentes del swarm intentan autenticarse (e.g., para reportar métricas vía API), pueden ser bloqueados por el rate limiter, causando:
- Pérdida de telemetría
- Fallos en la recolección de diagnóstico
- Timeouts en operaciones swarm-to-backend

## Impacto en adaptación

- Bajo: no afecta directamente la lógica de adaptación de pathways
- Pero usuarios frustrados que no pueden loguearse no pueden acceder a rutas adaptativas

## Impacto en consenso

- Nulo: el consenso es intra-swarm, no depende de auth externo

## Impacto en resiliencia

- **ALTO**: El rate limiter reduce la resiliencia del sistema porque un usuario legítimo es tratado como atacante
- La aplicación no puede distinguir entre un ataque real y un usuario que cometió 3 errores tipográficos

## Impacto en shared memory

- Nulo

## Fix implementado

### Estrategia: Separa consulta de incremento

Se refactorizó `AuthRateLimiter` para usar dos métodos:

```python
def is_allowed(self, ip: str) -> bool:
    # Solo consulta el estado del bucket, NO incrementa
    ...

def increment(self, ip: str) -> None:
    # Incrementa el contador (solo llamado explícitamente)
    ...
```

### Middleware modificado

```python
if not _limiter.is_allowed(ip):
    return 429  # Bloqueo preventivo

response = await call_next(request)

# Solo contamos los FAILED attempts (401) contra el rate limit
if response.status_code == 401:
    _limiter.increment(ip)
```

### Detalles del cambio

- **Antes:** middleware + check() → incremento incondicional
- **Después:** middleware + is_allowed() → solo incrementa en 401
- Los logins exitosos (200) ya no consumen slots
- Los logins fallidos (401) sí consumen slots
- El account lockout (3 fallos/5min) sigue siendo el mecanismo principal

### Archivos modificados

1. `backend/app/middleware/rate_limit.py:19-39` — Refactor `check()` → `is_allowed()` + `increment()`
2. `backend/app/middleware/rate_limit.py:49-71` — Middleware: solo incrementa tras 401

## Tests agregados

Los tests existentes en `test_session_flow.py:25-53` se actualizaron para usar la nueva API:
- `test_allows_within_limit`: ahora llama `is_allowed()` + `increment()` explícitamente
- `test_blocks_exceeding_limit`: mismo patrón
- `test_different_ips_independent`: mismo patrón
- `test_window_expires`: mismo patrón
- `test_rate_limiter_thread_safety`: mismo patrón (thread safety validada con 100 threads concurrentes)

## Riesgos futuros

1. **Race condition en middleware:** Si `is_allowed()` retorna True pero otro request incrementa antes de que este request llegue a `increment()`, el contador puede exceder `max_requests` por 1. Esto es aceptable (no es un safety issue, solo un slot extra).
2. **In-memory state:** `_buckets` es un `defaultdict(list)`. En reinicio del servidor, se pierde todo el estado. Aceptable para single-instance.
3. **Sin límite de memoria:** Teóricamente, un atacante con IPs rotativas podría llenar `_buckets` con entradas. En la práctica, el cleanup de `window_start` mantiene el tamaño acotado.

## Observability recomendada

1. **Métrica de rate limit hits:** Contador de cuántas veces se bloquea por IP rate limit vs account lockout
2. **Log estructurado:** Cada 429 debe loguear `ip`, `remaining`, `window_size`, `is_account_lockout`
3. **Dashboard:** Ratio de bloqueos legítimos vs ataques (basado en si el intento posterior con misma IP fue exitoso)
4. **Alerta:** Si mismo IP recibe >10 rate limits en 1 hora, alertar

## Regression prevention

1. **Test de middleware end-to-end:** Test que envía requests reales al endpoint `/api/auth/login` y verifica que logins exitosos NO cuentan contra el rate limit
2. **Test de integración account lockout + rate limiter:** Verificar que 3 fallos + 1 éxito + 2 fallos = bloqueo por account (429 con code=ACCOUNT_LOCKED), no por rate limit
3. **Property-based test:** Generar secuencias aleatorias de éxito/fallo y verificar que el rate limit nunca excede max_requests para fallos consecutivos
4. **Chaos engineering test:** Inyectar delays en el middleware para verificar que no hay race conditions entre is_allowed() e increment()

## Archivos afectados

| Archivo | Líneas | Cambio |
|---------|--------|--------|
| `backend/app/middleware/rate_limit.py` | 19-39 | Refactor: check() → is_allowed() + increment() |
| `backend/app/middleware/rate_limit.py` | 49-71 | Middleware: solo incrementa en 401 |
| `backend/tests/test_session_flow.py` | 27-103 | Tests actualizados a nueva API |

## Lecciones aprendidas

1. **Principio de menor sorpresa:** Un rate limiter no debería contar requests exitosos. El nombre "rate limit" implica límite de TASA, no de éxito.
2. **Separación de concerns:** Rate limiting por IP y account lockout por credenciales son MECANISMOS DISTINTOS con OBJETIVOS DISTINTOS. No deben compartir contadores.
3. **Test de integración:** Tests unitarios del rate limiter aislado no detectan este bug. Se necesita un test end-to-end que envíe requests reales al endpoint para verificar el comportamiento combinado.
