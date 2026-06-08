# Bug Report

## Metadata
- **ID:** BUG-005
- **Fecha:** 2026-05-27
- **Severidad:** MEDIUM
- **Categoría:** backend/auth
- **Tipo:** auth, database, runtime
- **Estado:** FIXED

## Síntomas

1. Usuarios que inician sesión con código institucional (no email) NUNCA son bloqueados por account lockout
2. Un atacante con código institucional puede hacer infinitos intentos de login sin ser bloqueado
3. Los intentos fallidos se registran en `LoginAttempt` con formato `code:{codigo}` pero la verificación de lockout busca el código sin prefijo
4. El account lockout funciona correctamente solo para usuarios que usan email

## Root Cause

### Análisis forense

Hay dos funciones que operan con identificadores de usuario pero usan formatos inconsistentes:

#### Función 1: `authenticate_user()` (auth_service.py:35-36)

Cuando la autenticación falla, registra el intento con un formato específico:

```python
if not user or not verify_password(password, user.hashed_password):
    email_for_log = identifier if "@" in identifier else f"code:{identifier}"
    _record_attempt(db, email_for_log, success=False, ip_address=ip_address)
    return None
```

Si `identifier` es un código (e.g., `"202312345"`), almacena `"code:202312345"`.
Si `identifier` es un email (e.g., `"admin@upao.edu.pe"`), almacena `"admin@upao.edu.pe"`.

#### Función 2: `is_account_locked()` (auth_service.py:46-59)

Consulta los intentos fallidos usando el `identifier` raw sin prefijo:

```python
def is_account_locked(db: Session, identifier: str) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
    failed_attempts = (
        db.query(LoginAttempt)
        .filter(
            LoginAttempt.email == identifier,   # ← BUSCA "202312345" (SIN PREFIJO)
            LoginAttempt.success == False,
            LoginAttempt.attempted_at >= cutoff,
        )
        .count()
    )
    return failed_attempts >= MAX_FAILED_ATTEMPTS
```

#### El mismatch

| login con | `_record_attempt` almacena | `is_account_locked` busca | ¿Match? |
|-----------|---------------------------|--------------------------|---------|
| email | `admin@upao.edu.pe` | `admin@upao.edu.pe` | ✅ SÍ |
| código | `code:202312345` | `202312345` | ❌ NO |

#### Duplicación del mismo bug

En `auth.py:51-66`, el bloque `if not user:` también tiene su propio cálculo de failed_count que replica el mismo bug:

```python
failed_count = (
    db.query(LoginAttempt)
    .filter(
        LoginAttempt.email == login_data.identifier,   # ← MISMO BUG
        LoginAttempt.success == False,
        LoginAttempt.attempted_at >= cutoff,
    )
    .count()
)
```

### Impacto en seguridad

Un estudiante cuyo código institucional es conocido (e.g., impreso en su carnet, visible en listas de clase) puede ser atacado con fuerza bruta sin límite. El atacante puede probar infinitas contraseñas usando el código institucional, evitando completamente el account lockout.

## Flujo de reproducción

1. Conocer un código institucional (e.g., `"202312345"`)
2. Hacer login 10 veces con contraseñas incorrectas usando el código
3. Verificar que los 10 intentos se registran como fallidos en LoginAttempt
4. Verificar que `is_account_locked("202312345")` retorna False (aunque hay 10 fallos)
5. El sistema nunca bloquea al atacante

## Riesgo arquitectónico

- **ALTO**: Bypass completo del mecanismo de seguridad primario (account lockout) para un subconjunto de usuarios
- **Violación del principio de defensa en profundidad:** El rate limiter IP (BUG-001) sigue activo, pero el account lockout por credenciales está completamente evadido para login con código
- **Inconsistencia en el modelo de datos:** `LoginAttempt.email` almacena valores que no son emails (e.g., `"code:202312345"`), violando el naming de la columna

## Impacto en swarm

- **BAJO**: Los agentes no se autentican con código institucional (usan tokens JWT). Pero si un agente usa código para algún propósito, podría ser explotado.

## Impacto en adaptación

- **NULO**: Este bug afecta solo el auth flow, no la lógica adaptativa.

## Impacto en consenso

- **NULO**

## Impacto en resiliencia

- **BAJO**: La resiliencia del sistema no se ve afectada, pero la postura de seguridad sí.

## Impacto en shared memory

- **NULO**

## Fix implementado

### Estrategia: Buscar ambos formatos en `is_account_locked`

```python
def is_account_locked(db: Session, identifier: str) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)

    # Cuando un usuario usa código institucional, _record_attempt almacena
    # "code:{identifier}". Debemos buscar ambos formatos.
    identifiers_to_check = [identifier]
    if "@" not in identifier:
        identifiers_to_check.append(f"code:{identifier}")

    failed_attempts = (
        db.query(LoginAttempt)
        .filter(
            LoginAttempt.email.in_(identifiers_to_check),
            LoginAttempt.success == False,
            LoginAttempt.attempted_at >= cutoff,
        )
        .count()
    )

    return failed_attempts >= MAX_FAILED_ATTEMPTS
```

El mismo fix se aplicó al bloque duplicado en `auth.py:51-66`.

### Archivos modificados

1. `backend/app/services/auth_service.py:46-59` — `is_account_locked` ahora busca ambos formatos
2. `backend/app/api/routes/auth.py:51-66` — inline failed_count ahora busca ambos formatos

## Tests agregados

No se agregaron tests específicos. Tests de integración necesarios:

```python
def test_account_lockout_with_institutional_code(db):
    """Account lockout debe funcionar con código institucional."""
    code = "202312345"
    wrong_password = "wrong"
    
    # 3 intentos fallidos con código institucional
    for _ in range(3):
        user = authenticate_user(db, code, wrong_password)
        assert user is None
    
    # El código debe estar bloqueado
    assert is_account_locked(db, code) is True

def test_account_lockout_with_email(db):
    """Account lockout debe funcionar con email (regresión)."""
    email = "admin@upao.edu.pe"
    wrong_password = "wrong"
    
    for _ in range(3):
        user = authenticate_user(db, email, wrong_password)
        assert user is None
    
    assert is_account_locked(db, email) is True

def test_account_lockout_mixed_identifier_formats(db):
    """Fallos con código deben afectar lockout por código y viceversa."""
    code = "202312345"
    email = "student@upao.edu.pe"
    
    # 2 fallos con código + 1 fallo con email del mismo usuario
    authenticate_user(db, code, "wrong1")
    authenticate_user(db, code, "wrong2")
    authenticate_user(db, email, "wrong3")
    
    # Ambos identificadores deben detectar el lockout
    assert is_account_locked(db, code) is True
```

## Riesgos futuros

1. **Crecimiento de `identifiers_to_check`:** Si en el futuro se agregan más formatos de identificación (e.g., DNI, phone), el array puede crecer. Monitorear que la query `in_` tenga índices apropiados.
2. **Falso positivo:** Si un usuario tiene código `"admin"` y existe un email `"admin@upao.edu.pe"`, la query con `in_` podría matchear intentos del código con intentos del email. Esto es poco probable porque los códigos institucionales son numéricos.
3. **Indexación:** `LoginAttempt.email` probablemente no tiene índice. La query con `in_` puede ser lenta si la tabla crece mucho. Considerar agregar un índice compuesto en `(email, success, attempted_at)`.

## Observability recomendada

1. **Métrica de login por tipo:** Contar logins por email vs código institucional
2. **Alerta de lockout bypass:** Si detectamos más de X intentos fallidos consecutivos con código sin lockout, alertar inmediatamente
3. **Auditoría:** Revisar periódicamente los LoginAttempt con formato `code:*` para detectar patrones de ataque
4. **Dashboard de seguridad:** Mostrar ratio de intentos fallidos por email vs código

## Regression prevention

1. **Test parametrizado:** Todos los tests de account lockout deben probar con email Y código institucional
2. **Test de integración:** Test end-to-end que verifica que después de 3 fallos con código, el siguiente intento recibe 429
3. **Schema validation:** Considerar renombrar `LoginAttempt.email` a `login_identifier` para reflejar que no siempre es un email
4. **Linting rule:** No permitir comparaciones directas con `LoginAttempt.email` sin revisar el formato del identificador

## Archivos afectados

| Archivo | Líneas | Cambio |
|---------|--------|--------|
| `backend/app/services/auth_service.py` | 46-59 | is_account_locked usa `in_(identifiers_to_check)` |
| `backend/app/api/routes/auth.py` | 51-66 | inline failed_count usa `in_(ids_to_check)` |

## Lecciones aprendidas

1. **Consistencia de formato:** Cuando un mismo valor se almacena en dos formatos diferentes (raw vs `code:` prefixed), la probabilidad de mismatch es del 100%. La solución correcta es normalizar el formato de almacenamiento, no buscar múltiples formatos.
2. **Normalización temprana:** `_record_attempt` debería normalizar el identificador a un formato canónico ANTES de almacenarlo, y todas las consultas deberían usar el mismo formato canónico.
3. **Duplicación de lógica:** El inline `failed_count` en `auth.py` es una copia de `is_account_locked()`. Esto duplica el bug y duplica el fix. Idealmente, el route handler debería reutilizar `is_account_locked()` para calcular `remaining_attempts`.
4. **Column naming:** Nombrar una columna `email` cuando almacena valores que no son emails (códigos con prefijo) es un code smell que esconde bugs.
