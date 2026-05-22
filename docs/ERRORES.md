# Registro de Errores, Bugs y Complicaciones

> Bitácora técnica de problemas encontrados durante el desarrollo de UPAO-MAS-EDU.
> Cada entrada documenta: síntoma, causa raíz, solución y archivos modificados.

---

## Índice

| # | Área | Severidad | Fecha | Descripción |
|---|------|-----------|-------|-------------|
| 1 | Backend | 🔴 Crítico | May 2026 | `login_attempts` table not found → 500 en login |
| 2 | Backend | 🔴 Crítico | May 2026 | Alembic `connect_args` serializado como JSON string → `ValueError` |
| 3 | Backend | 🔴 Crítico | May 2026 | ENUM values en mayúsculas en migración vs minúsculas en modelos Python |
| 4 | Backend | 🔴 Crítico | May 2026 | `use_enum_values` no funcionaba sin `values_callable` |
| 5 | Backend | 🔴 Crítico | May 2026 | `DATABASE_URL` con schema `postgres://` no reconocido por SQLAlchemy 2.x |
| 6 | Infra | 🔴 Crítico | May 2026 | `render.yaml` dentro de `backend/` no era encontrado por Render |
| 7 | Infra | 🔴 Crítico | May 2026 | Render mostraba startCommand viejo pese a `render.yaml` nuevo |
| 8 | Backend | 🟡 Medio | May 2026 | `alembic.ini` sin `sqlalchemy.url` placeholder |
| 9 | Backend | 🟡 Medio | May 2026 | `env.py` seteaba URL al nivel del módulo, no dentro de `run_migrations_online()` |
| 10 | Backend | 🟡 Medio | May 2026 | `Base.metadata.create_all()` no estaba en el lifespan de FastAPI |
| 11 | Frontend | 🔴 Crítico | May 2026 | `DiagnosticTest.tsx`: estado de éxito falso por `catch {}` vacío |
| 12 | Frontend | 🔴 Crítico | May 2026 | `AuthProvider` reemplazaba `logout` del store con navegación forzada |
| 13 | Frontend | 🟡 Medio | May 2026 | `getErrorMessage` exportado desde `api.ts` → hooks importaban from ubicación incorrecta |
| 14 | Frontend | 🟡 Medio | May 2026 | Falta de ErrorBoundary global |
| 15 | Frontend | 🟡 Medio | May 2026 | Sin refresh automático de token JWT |
| 16 | Frontend | 🟢 Bajo | May 2026 | `LearningPath.tsx`: URL con `?courseId=undefined` |
| 17 | Frontend | 🟢 Bajo | May 2026 | Sidebar no responsive en mobile |
| 18 | Frontend | 🟢 Bajo | May 2026 | Sin skeleton loaders ni empty states |
| 19 | Frontend | 🟢 Bajo | May 2026 | Sin detección de offline |
| 20 | Backend | 🟢 Bajo | May 2026 | Pool de conexiones PostgreSQL excedía límite de Render free (3 conexiones) |

---

## Detalle de cada error

---

### 🔴 1. `login_attempts` table not found → 500 en login

**Síntoma:** `POST /api/auth/login` retornaba 500 con `relation "login_attempts" does not exist`

**Causa raíz:** `Base.metadata.create_all(bind=engine)` nunca se llamaba en el startup de FastAPI. Las tablas eran creadas solo por Alembic, pero Alembic nunca se ejecutaba en Render.

**Solución:**
- Agregar `Base.metadata.create_all(bind=engine)` dentro del `lifespan` en `main.py`
- Agregar `alembic upgrade head` al `startCommand` de Render

**Archivos:**
- `backend/app/main.py` — línea 61: `Base.metadata.create_all(bind=engine)`
- `backend/render.yaml` → `render.yaml` — startCommand con `alembic upgrade head`

---

### 🔴 2. Alembic `connect_args` serializado como JSON string → `ValueError`

**Síntoma:** `alembic upgrade head` fallaba con `ValueError: dictionary update sequence element #0 has length 1; 2 is required`

**Causa raíz:** En `alembic/env.py`:
```python
cfg["sqlalchemy.connect_args"] = json.dumps({"sslmode": "require"})
```
Esto guardaba un string JSON en la sección de config. `engine_from_config` luego hacía `dict(string)` → iteraba sobre caracteres → error.

**Solución:** Pasar `connect_args` como kwarg directo a `engine_from_config`:
```python
connectable = engine_from_config(
    config.get_section(config.config_ini_section),
    prefix="sqlalchemy.",
    poolclass=pool.NullPool,
    connect_args=connect_args,
)
```

**Archivos:**
- `backend/alembic/env.py` — eliminado `json.dumps`, agregado `connect_args=connect_args`

---

### 🔴 3. ENUM values en mayúsculas en migración vs minúsculas en modelos

**Síntoma:** `alembic upgrade head` creaba ENUMs con `'ADMIN'`, `'DOCENTE'` (mayúsculas) pero los modelos Python tenían `ADMIN = "admin"` (minúsculas). En insert, PostgreSQL rechazaba los valores.

**Causa raíz:** La migración inicial definió los ENUMs con mayúsculas:
```sql
CREATE TYPE userrole AS ENUM ('ADMIN', 'DOCENTE', ...)
```
Mientras los modelos usaban string values en minúscula.

**Solución:** Cambiar todos los valores ENUM en la migración a minúsculas para coincidir con los modelos.

**Archivos:**
- `backend/alembic/versions/83058a18afd3_initial_models.py` — 5 bloques `CREATE TYPE` + 5 columnas `postgresql.ENUM`

---

### 🔴 4. `use_enum_values` no prevenía envío del `.name` del Enum

**Síntoma:** `role='ADMIN'` en vez de `role='admin'` al insertar, incluso con `use_enum_values=True`

**Causa raíz:** En SQLAlchemy 2.0, `use_enum_values=True` afecta la conversión DB→Python (result_processor), no Python→DB. Para DB→Python, el `_db_value_for_elem` usa `_valid_lookup` que mapea el enum member al `.name` por defecto. Sin `values_callable`, el lookup retorna `'ADMIN'` (el name), no `'admin'` (el value).

**Solución:** Agregar `values_callable=lambda x: [e.value for e in x]` a TODAS las columnas Enum:
```python
role = Column(Enum(UserRole, name="userrole", use_enum_values=True, values_callable=lambda x: [e.value for e in x]))
```

**Archivos:**
- `backend/app/models/user.py` — línea 32
- `backend/app/models/course.py` — línea 33
- `backend/app/models/enrollment.py` — línea 33
- `backend/app/models/resource.py` — línea 39
- `backend/app/models/competency.py` — línea 30

---

### 🔴 5. `DATABASE_URL` con schema `postgres://` no reconocido por SQLAlchemy 2.x

**Síntoma:** Alembic moría silenciosamente sin ningún traceback. Render log: `==> Exited with status 1` sin mensaje de error.

**Causa raíz:** Render inyecta `DATABASE_URL` con schema `postgres://user:pass@...`. SQLAlchemy 2.x requiere `postgresql://`. El schema `postgres` no es reconocido, el engine falla al conectar, y como el error ocurre antes de inicializar logging en Alembic, no se imprime nada.

**Solución:** Agregar un `@field_validator` en `Settings` que convierta automáticamente:
```python
@field_validator("DATABASE_URL")
@classmethod
def fix_postgres_scheme(cls, v: str) -> str:
    if v.startswith("postgres://"):
        return v.replace("postgres://", "postgresql://", 1)
    return v
```

**Archivos:**
- `backend/app/core/config.py` — líneas 28-33

---

### 🔴 6. `render.yaml` dentro de `backend/` no encontrado por Render

**Síntoma:** Render ejecutaba `pip install -r requirements.txt` desde la raíz del repo, pero el archivo estaba en `backend/`.

**Causa raíz:** `render.yaml` estaba en `backend/render.yaml`. Render busca `render.yaml` SOLO en la raíz del repositorio, no en subdirectorios. Aunque tuviera `rootDir: backend`, el archivo mismo debía estar en la raíz.

**Solución:** Mover `render.yaml` de `backend/` a la raíz del repo:
```
multiagent-llm-education/
├── render.yaml          ← aquí
├── backend/
│   ├── app/
│   ├── alembic/
│   └── requirements.txt
```

**Archivos:**
- `backend/render.yaml` → eliminado
- `render.yaml` → creado en raíz

---

### 🔴 7. Render mostraba startCommand viejo pese a `render.yaml` nuevo

**Síntoma:** Render log mostraba `Running 'alembic upgrade head && uvicorn ...'` (formato antiguo con `&&`) en lugar del nuevo multiline con `python seed.py`.

**Causa raíz:** Render NO detecta automáticamente cambios en `render.yaml` para servicios existentes. Requiere acción manual en el Dashboard.

**Solución:** Instrucción manual:
1. Render Dashboard → Service Settings → "Use render.yaml" activado
2. "Sync with render.yaml"
3. Manual Deploy → "Clear build cache & deploy"

---

### 🟡 8. `alembic.ini` sin `sqlalchemy.url` placeholder

**Síntoma:** Posible fallo silencioso si `env.py` no alcanzaba a setear la URL antes de que Alembic intentara leerla.

**Causa raíz:** La línea `sqlalchemy.url` estaba comentada:
```ini
# sqlalchemy.url = driver://user:pass@localhost/dbname
```

**Solución:** Agregar un placeholder:
```ini
sqlalchemy.url = postgresql://placeholder
```

**Archivos:**
- `backend/alembic.ini` — línea 89

---

### 🟡 9. `env.py` seteaba URL al nivel del módulo

**Síntoma:** Estilo inconsistente y riesgo de que `run_migrations_offline` usara `config.get_main_option` en vez de `settings.DATABASE_URL`.

**Causa raíz:** El URL se seteaba fuera de las funciones de migración:
```python
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
```

**Solución:** Mover la asignación dentro de `run_migrations_online()`:
```python
def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.DATABASE_URL
    ...
```
Y en `run_migrations_offline()` usar `url = settings.DATABASE_URL` directamente.

**Archivos:**
- `backend/alembic/env.py` — reestructuración completa

---

### 🟡 10. `Base.metadata.create_all()` no estaba en el startup

**Síntoma:** Tablas faltantes en producción si Alembic no se ejecutaba.

**Causa raíz:** El `lifespan` de FastAPI no llamaba a `create_all()`, por lo que las tablas solo se creaban vía Alembic.

**Solución:** Agregar `Base.metadata.create_all(bind=engine)` en el bloque `lifespan` antes del `yield`.

**Archivos:**
- `backend/app/main.py` — línea 61

---

### 🔴 11. `DiagnosticTest.tsx`: estado de éxito falso

**Síntoma:** El usuario veía "Test completado! Tu ruta ha sido generada" aunque las APIs fallaran (500, network error, etc.)

**Causa raíz:**
```tsx
setCompleted(true)          // ← éxito ANTES de las APIs
try {
    await api.call1()       // ← puede fallar
    await api.call2()       // ← puede fallar
} catch {}                  // ← traga TODOS los errores silenciosamente
```

**Solución:**
- Mover `setCompleted(true)` DESPUÉS de ambas llamadas exitosas
- Capturar error y mostrar UI de error con botón reintentar
- Toast de error para feedback inmediato

**Archivos:**
- `frontend/src/pages/estudiante/DiagnosticTest.tsx` — refactor completo de `handleNext()`

---

### 🔴 12. `AuthProvider` reemplazaba `logout` del store con navegación forzada

**Síntoma:** Llamar `useAuthStore.getState().logout()` desde el interceptor de Axios disparaba navegación a `/login`, duplicando redirects.

**Causa raíz:**
```tsx
useAuthStore.setState({ logout: logoutAndRedirect })
```
Esto reemplazaba runtime la función `logout` del store por una que incluía `navigate('/login')`.

**Solución:** Eliminar el override. Cada caller maneja su propia navegación.

**Archivos:**
- `frontend/src/providers/AuthProvider.tsx` — eliminado bloque `useEffect` con `setState`

---

### 🟡 13. `getErrorMessage` exportado desde `api.ts`

**Síntoma:** 7 hooks importaban `{ getErrorMessage } from '@/lib/api'` pero la función se movió a `@/lib/errors`.

**Causa raíz:** Refactor de separación de responsabilidades: `api.ts` ya no debía exportar utilidades de error.

**Solución:** Cambiar imports en todos los hooks:
```ts
// Antes:
import api, { getErrorMessage } from '@/lib/api'
// Después:
import api from '@/lib/api'
import { getErrorMessage } from '@/lib/errors'
```

**Archivos:**
- `frontend/src/hooks/useAuth.ts`
- `frontend/src/hooks/useCompetencies.ts`
- `frontend/src/hooks/useCourses.ts`
- `frontend/src/hooks/useObjectives.ts`
- `frontend/src/hooks/useResources.ts`
- `frontend/src/hooks/useStudent.ts`
- `frontend/src/hooks/useUsers.ts`

---

### 🟡 14. Falta de ErrorBoundary global

**Síntoma:** Cualquier error de React en runtime mostraba pantalla blanca sin recuperación.

**Causa raíz:** No existía un `ErrorBoundary` envolviendo la aplicación.

**Solución:** Crear `ErrorBoundary` component con UI de error + botón reintentar + detalles técnicos colapsables. Envolver toda la app en `main.tsx`.

**Archivos:**
- `frontend/src/components/ErrorBoundary.tsx` — nuevo
- `frontend/src/main.tsx` — envuelve `<App />`

---

### 🟡 15. Sin refresh automático de token JWT

**Síntoma:** Token expiraba a los 60 minutos y el usuario era forzado a login sin posibilidad de renovación automática.

**Causa raíz:** No existía lógica de refresh token en el interceptor de Axios ni en el proveedor de autenticación.

**Solución:**
- Interceptor de Axios: si recibe 401, intenta `/api/auth/refresh` antes de hacer logout
- Refresh queue: si múltiples requests reciben 401 simultáneamente, solo una hace refresh, las demás esperan
- AuthProvider: valida sesión al startup con `/api/auth/me`

**Archivos:**
- `frontend/src/lib/api.ts` — interceptor con refresh queue
- `frontend/src/providers/AuthProvider.tsx` — validación startup + multi-tab sync

---

### 🟢 16. `LearningPath.tsx`: URL con `?courseId=undefined`

**Síntoma:** Si `courseId` era `undefined` (parámetro de ruta faltante), la URL de navegación contenía `?courseId=undefined`.

**Causa raíz:** Sin guard contra `undefined`:
```tsx
navigate(`/estudiante/content/${id}?courseId=${courseId}`)
```

**Solución:** Agregar condición `courseId`:
```tsx
if (item.status === 'available' && item.resource_id && courseId) {
```

**Archivos:**
- `frontend/src/pages/estudiante/LearningPath.tsx` — línea 132

---

### 🟢 17. Sidebar no responsive en mobile

**Síntoma:** En pantallas pequeñas (< 1024px), la sidebar ocupaba 256px fijos y no había forma de ocultarla.

**Causa raíz:** `Sidebar.tsx` usaba `fixed inset-y-0 left-0 w-64` sin variante responsive.

**Solución:** Sidebar colapsable:
- Mobile: hamburger menu + overlay + slide-in animación
- Desktop: sidebar fija como antes
- Scroll lock cuando sidebar abierta en mobile

**Archivos:**
- `frontend/src/components/layout/Sidebar.tsx` — rewrite completo
- `frontend/src/components/layout/AdminLayout.tsx` — `lg:ml-64`, `pt-16 lg:pt-6`
- `frontend/src/components/layout/DocenteLayout.tsx` — responsive padding
- `frontend/src/components/layout/EstudianteLayout.tsx` — responsive padding

---

### 🟢 18. Sin skeleton loaders ni empty states

**Síntoma:** Las páginas mostraban pantalla en blanco mientras cargaban datos, y listas vacías sin mensaje informativo.

**Causa raíz:** Ausencia de componentes de loading y empty state.

**Solución:** Crear componentes reutilizables:
- `PageLoading` — layout completo con skeletons
- `TableLoading` — filas esqueleto para tablas
- `CardGridLoading` — grid de cards esqueleto
- `EmptyState` — icono + título + descripción + acción

**Archivos:**
- `frontend/src/components/ui/page-loading.tsx` — nuevo
- `frontend/src/components/ui/empty-state.tsx` — nuevo

---

### 🟢 19. Sin detección de offline

**Síntoma:** Si el usuario perdía conexión, las requests fallaban silenciosamente sin indicación visual.

**Causa raíz:** No se monitoreaba el estado `navigator.onLine`.

**Solución:**
- `useOnlineStatus` hook que escucha eventos `online`/`offline`
- `OfflineBanner` componente fijo en parte superior con icono WiFi-off

**Archivos:**
- `frontend/src/hooks/useOnlineStatus.ts` — nuevo
- `frontend/src/components/ui/OfflineBanner.tsx` — nuevo
- `frontend/src/main.tsx` — render condicional del banner

---

### 🟢 20. Pool de conexiones PostgreSQL excedía límite de Render free

**Síntoma:** Posible error de conexión en Render free tier (límite 3 conexiones simultáneas).

**Causa raíz:** `session.py` configuraba `pool_size=5, max_overflow=10` incluso en producción.

**Solución:** Usar pool más pequeño en producción:
```python
if settings.is_production:
    engine = create_engine(
        ...,
        pool_size=2,
        max_overflow=1,
        pool_recycle=300,
    )
```

**Archivos:**
- `backend/app/db/session.py` — pool config condicional

---

## Estadísticas

| Métrica | Valor |
|---------|-------|
| Total errores documentados | 20 |
| 🔴 Críticos | 7 |
| 🟡 Medios | 6 |
| 🟢 Bajos | 7 |
| Frontend | 10 |
| Backend | 8 |
| Infraestructura | 2 |
| Commits asociados | 12 |

## Commits por fase

```
1b17546 → Fix postgres:// scheme, .env.production
1c66286 → Fix postgres:// to postgresql:// in DATABASE_URL
6319d5b → Move render.yaml to repo root
88dc798 → Fix enum mismatch in postgres migrations
a334139 → Fix critical bugs: DiagnosticTest, AuthProvider, LearningPath URL
8a23b44 → Phase 1-2: AuthProvider, ErrorBoundary, interceptors, responsive
adcc1ee → Fix Alembic production SSL config
d72f988 → Fix alembic.ini placeholder + clean env.py
b30c1fa → Fix Render rootDir
```

> Última actualización: 22 de mayo de 2026
