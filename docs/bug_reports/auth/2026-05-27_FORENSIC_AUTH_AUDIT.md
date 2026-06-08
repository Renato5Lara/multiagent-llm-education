# Forensic Auth Audit — Multiagent-LLM-Education

## Executive Summary

**Audit date:** 2026-05-27  
**Scope:** Full auth stack (backend JWT + frontend React/zustand/React Query)  
**Files examined:** 27 (12 backend + 15 frontend)  
**Bugs found:** 21 (6 fixed in prior session, 15 newly identified)  
**Open CRITICAL:** 3 (BUG-014, BUG-022, BUG-023)  
**Open HIGH:** 4 (BUG-018, BUG-024, BUG-025, BUG-026)

---

## 1. Auth Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                         │
│                                                                 │
│  ┌───────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │ Zustand    │  │ AuthProvider │  │ React Query              │ │
│  │ Store     ◄──┤ Context      ◄──┤ meQuery                  │ │
│  │ (persist)  │  │ validateSess │  │ loginMutation            │ │
│  │            │  │ storageSync  │  │ logoutMutation           │ │
│  └─────┬─────┘  └──────┬───────┘  └────────┬─────────────────┘ │
│        │               │                   │                   │
│        ▼               ▼                   ▼                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Axios Interceptor (api.ts)                   │  │
│  │  request → attach Bearer token                            │  │
│  │  response → 401 → refresh queue → retry                  │  │
│  └─────────────────────┬────────────────────────────────────┘  │
│                        │ HTTP                                  │
└────────────────────────┼────────────────────────────────────────┘
                         │
┌────────────────────────┼────────────────────────────────────────┐
│                  BACKEND (FastAPI)                               │
│                        ▼                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Rate Limiter │  │ Auth Routes  │  │ Auth Service          │  │
│  │ (middleware) │──►│ /login      │──►│ authenticate_user    │  │
│  │ IP-based     │  │ /refresh    │  │ create_user_tokens    │  │
│  │ 5/60s        │  │ /me         │  │ is_account_locked     │  │
│  └──────────────┘  └──────┬───────┘  └──────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Dependencies (deps.py)                                   │  │
│  │  get_current_user → decode_token → query User by sub     │  │
│  │  get_current_admin → role check                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Security (core/security.py)                              │  │
│  │  create_access_token (exp: 60 min)                       │  │
│  │  create_refresh_token (exp: 7 days, type: refresh)        │  │
│  │  decode_token → JWTError → None                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Full JWT Lifecycle Trace

### Phase 1: Creation

```
POST /api/auth/login
  │
  ├─ auth_service.authenticate_user()
  │   ├─ query User by (email == identifier) OR (institutional_code == identifier)
  │   ├─ verify_password(plain, hashed) via bcrypt.checkpw
  │   └─ _record_attempt(success=True/False)
  │
  ├─ auth_service.create_user_tokens(user)
  │   ├─ payload = {"sub": user.id, "email": user.email, "role": user.role.value}
  │   ├─ create_access_token(data=payload)
  │   │   └─ jwt.encode(payload + {"exp": now + 60min}, SECRET_KEY, HS256)
  │   └─ create_refresh_token(data=payload)
  │       └─ jwt.encode(payload + {"exp": now + 7d, "type": "refresh"}, SECRET_KEY, HS256)
  │
  └─ RETURN TokenResponse { access_token, refresh_token, token_type, user }
```

### Phase 2: Storage (Frontend)

```
loginMutation.onSuccess(data)
  │
  ├─ storeLogin(data.access_token, data.refresh_token, data.user)
  │   └─ zustand set({ token, refreshToken, user, isAuthenticated: true })
  │       └─ persist middleware writes to localStorage "upao-auth"
  │           └─ partialize: { token, refreshToken, user, isAuthenticated }
  │
  └─ navigate('/admin')  // React Router navigation
```

### Phase 3: Request Authentication

```
Axios request interceptor
  │
  ├─ useAuthStore.getState().token → "eyJhbG..."
  ├─ config.headers.Authorization = "Bearer eyJhbG..."
  └─ RETURN config
```

### Phase 4: Token Validation (Backend)

```
get_current_user(token)
  │
  ├─ decode_token(token)
  │   ├─ jwt.decode(token, SECRET_KEY, algorithms=[HS256])
  │   ├─ JWTError → raise 401
  │   └─ RETURN payload = { sub, email, role, exp }
  │
  ├─ query User by id = payload.sub
  ├─ user.is_active == False → raise 403
  └─ RETURN user
```

### Phase 5: Token Refresh

```
Axios response interceptor (HTTP 401)
  │
  ├─ Check: is this /api/auth/refresh? → skip (infinite loop guard)
  ├─ Check: already retrying? → queue request
  ├─ isRefreshing = true
  │
  ├─ Read refreshToken from zustand store
  ├─ isTokenExpired(refreshToken, buffer=30s)? → logout + redirect
  │
  ├─ POST /api/auth/refresh { refresh_token }
  │   ├─ decode_token(refresh_token)
  │   ├─ check type == "refresh"
  │   ├─ query User by sub
  │   ├─ create new access + refresh tokens
  │   └─ RETURN { access_token, refresh_token, user }
  │
  ├─ store.login(new_access, new_refresh, user)
  ├─ processPendingRequests(new_access)
  ├─ retry original request with new token
  │
  └─ FAIL: clearPendingRequests → logout + window.location.href = '/login'
```

### Phase 6: Session Validation (on page load)

```
AuthProvider mount
  │
  ├─ Wait for zustand hydrate (_hydrated)
  ├─ Check: useAuthStore.getState().token exists?
  │   NO → setIsReady(true), done
  │   YES → continue
  │
  ├─ Check: both tokens expired locally?
  │   YES → storeLogout(), setIsReady(true), done
  │   NO → continue
  │
  ├─ api.get('/api/auth/me')
  │   ├─ Interceptor attaches Bearer token
  │   ├─ Token EXPIRED → interceptor refreshes (Phase 5)
  │   ├─ Token VALID → return user
  │   └─ ERROR → storeLogout(), queryClient.clear()
  │
  ├─ setUser(resp.data)
  ├─ setIsValidating(false), setIsReady(true)
  └─ DONE
```

---

## 3. Bug Catalog — All 21 Findings

### Already Fixed (BUG-001 through BUG-006)

| ID | Bug | Severity | Status |
|----|-----|----------|--------|
| BUG-001 | IP rate limiter counted ALL requests, not just failures | CRITICAL | FIXED |
| BUG-002 | Race condition: validateSession vs meQuery double /api/auth/me | CRITICAL | FIXED |
| BUG-003 | queryClient.clear() wiped all cache on every login | HIGH | FIXED |
| BUG-004 | setUser called twice via meQuery.queryFn + useEffect | MEDIUM | FIXED |
| BUG-005 | is_account_locked identifier format mismatch (code: prefix) | MEDIUM | FIXED |
| BUG-006 | Hardcoded 429 message "5 minutos" for all rate limit types | LOW | FIXED |

### Newly Discovered (BUG-014 through BUG-028)

---

#### BUG-014 (CRITICAL) — validateSession logs out on ANY error

**File:** `AuthProvider.tsx:67-77`

```tsx
try {
    const resp = await api.get<UserAuth>('/api/auth/me')
    setUser(resp.data)
} catch {
    storeLogout()       // ← Runs on network timeout, 500, DNS failure, etc.
    queryClient.clear()
}
```

**Root cause:** The `catch` block unconditionally executes `storeLogout()`. If the server is temporarily unreachable (e.g., network blip, backend restart), the user is forcibly logged out. This is indistinguishable from an actual expired session to the user.

**Severity:** CRITICAL — causes false-positive session terminations under any transient fault.

**Fix:** Only log out on 401/403 errors. For transient errors, keep the session:

```ts
} catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 401) {
        storeLogout()
        queryClient.clear()
    } else {
        // Transient error — don't log out
        logger.warn('Session validation failed transiently:', err)
    }
}
```

---

#### BUG-015 (HIGH) — AuthProvider multi-tab storage event race

**File:** `AuthProvider.tsx:98-122`

```tsx
useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
        if (e.key !== 'upao-auth') return
        if (!e.newValue) {
            storeLogout()
            queryClient.clear()
            navigate('/login')    // ← RACE: navigate outside event cycle
        }
    }
    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
}, [storeLogout, queryClient, navigate, token, validateSession])
```

**Root cause:** `navigate('/login')` is called inside the storage event handler, which runs outside React's batching. This can cause a stale closure on `navigate` if the effect re-runs while the handler is registered. The `useEffect` dependency array includes `navigate`, `token`, and `validateSession` — changing any of these re-registers the handler, but there's a gap between the old handler being removed and the new one being added where a storage event could be missed.

**Impact:** HIGH — intermittent failure of cross-tab logout sync.

---

#### BUG-016 (HIGH) — 401 interceptor adds latency to login error responses

**File:** `api.ts:51-124`

When `POST /api/auth/login` returns 401 (wrong password), the interceptor:

1. Catches the 401 (line 51)
2. Checks if URL includes `/api/auth/refresh` — no, it's `/api/auth/login` (line 53)
3. Checks `isRefreshing` — false (line 57)
4. Sets `isRefreshing = true` (line 67)
5. Reads `refreshToken` from store — null (line 72)
6. Throws "No refresh token available" (line 74)
7. Catch block: checks `axiosError.response?.status` — but it's a thrown Error, not an axios error (line 107)
8. Falls through to `return Promise.reject(refreshError)` (line 110)
9. Login mutation's `onError` finally fires

**Total latency added:** ~2-5ms (negligible). But the REAL issue: the interceptor modifies global state (`isRefreshing = true` at line 67, then `false` at line 113). Between these two lines, ANY other 401 response from a concurrent request will be queued instead of triggering its own refresh. If a concurrent request gets 401 during this window, it's queued. At line 113, `isRefreshing = false`, and at line 114, orphaned requests with length > 0 would try to resolve, but the queue was cleared by `clearPendingRequests` at line 105. So the concurrent request's 401 is lost — the request hangs indefinitely.

**Fix:** Skip the 401 interceptor for auth endpoints:

```ts
if (originalRequest.url?.includes('/api/auth/login')) {
    return Promise.reject(error)  // Don't try to refresh
}
```

---

#### BUG-017 (MEDIUM) — Queue race during token refresh

**File:** `api.ts:114-121`

```tsx
finally {
    isRefreshing = false
    if (pendingRequests.length > 0) {
        const token = useAuthStore.getState().token
        if (token) {
            const orphaned = pendingRequests.splice(0)
            orphaned.forEach((p) => p.resolve(token))
        } else {
            clearPendingRequests(new Error('Session expired'))
        }
    }
}
```

**Race window:** Between `processPendingRequests(access_token)` (line 101) and `isRefreshing = false` (line 113), new 401 requests see `isRefreshing === true` and queue themselves. But the `finally` block at line 114 checks `pendingRequests.length > 0` — these newly queued requests ARE resolved with the fresh token. This is correct in the success path.

**But in the FAILURE path:** `clearPendingRequests(refreshError)` clears the queue at line 105. Then `isRefreshing = false` at line 113. Then `pendingRequests.length > 0` — it's 0 because it was cleared. New 401 requests arriving after `isRefreshing = false` but before the next request reads `isRefreshing` see `isRefreshing === false` and start a NEW refresh cycle. This is correct behavior — no bug here.

However, there IS a bug in the failure path: the `finally` block's orphaned handler fires AFTER `clearPendingRequests`. If a new request arrives between `clearPendingRequests` (line 105) and the orphaned check (line 114), and the refresh failed (token is still the expired one), the orphaned handler resolves with the EXPIRED token. The retry gets 401 again. This time, `originalRequest._retry` is already `true` (set at line 66), so the interceptor skips retry and the 401 propagates to the caller. The caller gets an unexpected 401. This is a MEDIUM severity bug — it causes intermittent 401 errors after a failed refresh.

---

#### BUG-018 (MEDIUM) — `ProtectedRoute` reads from two reactivity sources

**File:** `ProtectedRoute.tsx`

```tsx
export default function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { isReady, isValidating } = useAuthContext()
  const { isAuthenticated, user } = useAuthStore()
  // ...
}
```

**Root cause:** Reading `isAuthenticated` and `user` from `useAuthStore()` instead of from `useAuthContext()` creates two separate React subscriptions. The context's `isAuthenticated` (line 131 of AuthProvider) comes from the store, but goes through an extra render cycle (store → AuthProvider re-render → context update → ProtectedRoute re-render). When both update simultaneously, there's a micro-window where `useAuthStore()` has updated but `useAuthContext()` hasn't (or vice versa).

**Impact:** MEDIUM — causes a brief flash of incorrect auth state (e.g., showing the login page for a frame before redirecting to the dashboard).

**Fix:** Read all auth state from the context:

```tsx
const { isReady, isValidating, isAuthenticated, user } = useAuthContext()
```

---

#### BUG-019 (MEDIUM) — Logout causes double navigation

**File:** `useAuth.ts:46-51` and `api.ts:108-109`

```tsx
// useAuth.ts
onSettled: () => {
    storeLogout()
    queryClient.clear()
    navigate('/login')   // ← React Router navigation
},

// api.ts (on refresh failure)
useAuthStore.getState().logout()
window.location.href = '/login'   // ← Hard redirect
```

**Root cause:** When a concurrent API call fails with 401 during logout, the interceptor ALSO redirects to `/login` via `window.location.href`. This creates a double navigation: first React Router's `navigate('/login')`, then the hard redirect. The hard redirect causes a full page reload, losing all React state and triggering a second hydration cycle.

**Impact:** MEDIUM — causes unnecessary full page reload. In development with StrictMode, this triggers double effects, potentially causing a validation loop.

**Fix:** The interceptor should not hard-redirect. Instead, rely on React Router navigation from the calling code:

```ts
// In api.ts, instead of window.location.href:
useAuthStore.getState().logout()
// React Router's ProtectedRoute will redirect to /login
```

---

#### BUG-020 (MEDIUM) — Interceptor skips login endpoint whitelist

**File:** `api.ts:53`

```tsx
if (originalRequest.url?.includes('/api/auth/refresh')) {
    return Promise.reject(error)  // Skip refresh for refresh endpoint
}
```

**Missing:** `/api/auth/login` should also be skipped. The login endpoint is unauthenticated. If it returns 401 (wrong credentials), the interceptor should NOT attempt to refresh tokens.

**Fix:** Add login to the skip list:

```tsx
if (originalRequest.url?.includes('/api/auth/refresh') ||
    originalRequest.url?.includes('/api/auth/login')) {
    return Promise.reject(error)
}
```

---

#### BUG-021 (MEDIUM) — `AcademicGuard` query unmounts during onboarding redirect

**File:** `components/auth/AcademicGuard.tsx`

```tsx
const { data: onboardingStatus, isLoading, isError } = useQuery({
    queryKey: ['onboarding-status'],
    queryFn: async () => {
        const resp = await api.get('/api/students/onboarding/status')
        return resp.data
    },
    enabled: isAuthenticated && user?.role === 'estudiante',
    retry: false,
    staleTime: 30000,
})

if (needsOnboarding && !isOnboardingRoute) {
    return <Navigate to="/estudiante/onboarding" replace />
}
```

**Root cause:** The `useQuery` for `onboarding-status` fires on every render where `isAuthenticated && user?.role === 'estudiante'`. If the API call is slow, the component renders the loading state. Then when the data arrives, it renders `isError → <Outlet />` or `needsOnboarding → <Navigate>`. The `<Navigate>` unmounts AcademicGuard, which cancels the React Query subscription. This is correct, but the query's `staleTime: 30000` means it won't re-fetch for 30 seconds — even if the navigation back to the dashboard happens within that window, stale data is used.

**Impact:** MEDIUM — minor UX glitch where onboarding status might be stale on rapid navigation.

---

#### BUG-022 (CRITICAL) — `Onboarding.tsx` has a stale closure in setUser

**File:** `pages/estudiante/Onboarding.tsx:91-93`

```tsx
onSuccess: () => {
    if (user) {
        setUser({ ...user, current_cycle: selectedCycle! })
    }
    toast({ title: '¡Ciclo asignado exitosamente!' })
    navigate('/estudiante')
},
```

**Root cause:** The `user` variable is captured at render time (line 67). If the mutation takes time to resolve, `user` might be stale. Using `setUser({ ...user, ... })` with a stale `user` object means the entire user object is rewritten with potentially outdated fields. If the user's data changed on the server (e.g., admin updated their profile), those changes are overwritten by the stale frontend state.

**Worse:** `selectedCycle!` uses the non-null assertion operator. If `selectedCycle` is somehow null when `handleConfirm` fires (e.g., a race condition where the user deleted their selection), `current_cycle` is set to undefined. But `selectedCycle` is checked against null in the button's `disabled={!selectedCycle}`, so this shouldn't happen through the normal UI flow.

**Fix:** Use the server response to set user data, and read from the store dynamically:

```tsx
onSuccess: (data) => {
    const currentUser = useAuthStore.getState().user
    if (currentUser) {
        setUser({ ...currentUser, current_cycle: data.cycle ?? selectedCycle! })
    }
}
```

---

#### BUG-023 (CRITICAL) — No auth event tracing or observability

**File:** Whole system

**Impact:** There is zero observability into the auth flow. When a user reports "I can't log in," there's no way to:
1. Trace the login request through the system
2. See why the refresh failed
3. Correlate frontend auth state with backend events
4. Measure login latency
5. Detect retry storms
6. Monitor session validation failures

**Fix:** Implement structured auth tracing using the existing `CorrelationEngine`:

```tsx
// In api.ts interceptor:
import { correlationEngine } from '@/tracing/correlation'

api.interceptors.request.use((config) => {
    config.headers['X-Correlation-ID'] = correlationEngine.generateId()
    return config
})
```

And on the backend, the existing `SwaggerDiagnosticsMiddleware` should emit `auth:*` events.

---

#### BUG-024 (HIGH) — JWT payload hardening

**File:** `core/security.py:30-36`

```python
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

**Issues:**
1. No `iat` (issued at) claim — can't track when the token was created
2. No `jti` (JWT ID) claim — can't revoke individual tokens
3. No `nbf` (not before) claim — token is valid immediately, even if created with a future `exp` due to clock skew
4. Access token doesn't have a `type` claim (unlike refresh tokens) — harder to distinguish in logs
5. Refresh token includes ROLE in payload — if a user's role changes, the old refresh token still has the old role until it expires (7 days)

**Fix:**

```python
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    to_encode.update({
        "exp": now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)),
        "iat": now,
        "jti": str(uuid.uuid4()),
        "nbf": now,
        "type": "access",
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

---

#### BUG-025 (HIGH) — Token refresh creates brand-new refresh token (rotation issue)

**File:** `auth_service.py:77-83`

```python
def refresh_user_token(...):
    new_payload = {"sub": user.id, "email": user.email, "role": user.role.value}
    new_access = create_access_token(data=new_payload)
    new_refresh = create_refresh_token(data=new_payload)
    return new_access, new_refresh, user
```

**Root cause:** Every refresh creates a NEW refresh token. The old refresh token remains valid until it expires (7 days). This means a stolen refresh token can be used for 7 days even after the user refreshes. This violates the OWASP recommendation for refresh token rotation (old token should be invalidated).

**Also:** There's no refresh token reuse detection. If an attacker steals a refresh token and uses it, the legitimate user's next refresh also succeeds — both tokens work concurrently.

**Fix:** Implement refresh token versioning on the User model:

```python
# On refresh:
user.token_version += 1
db.commit()

# Include version in token:
new_payload = {
    "sub": user.id,
    "email": user.email,
    "role": user.role.value,
    "ver": user.token_version,
}
```

And validate the version on each request.

---

#### BUG-026 (HIGH) — `decode_token` returns None for ALL JWT errors, masking specific failures

**File:** `core/security.py:60-71`

```python
def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
```

**Root cause:** `JWTError` is the base class for ALL python-jose exceptions (expired, bad signature, malformed, etc.). Returning `None` for all failures makes it impossible to distinguish between:
- Token expired (expected — should trigger refresh)
- Token malformed (bug or attack — should log)
- Token bad signature (attack — should alert)
- Token wrong algorithm (misconfiguration — should alert)

**Impact:** HIGH — the system silently treats expired tokens the same as attack attempts. Security incidents are invisible.

**Fix:** Return different error types:

```python
from enum import Enum

class TokenValidationError(Enum):
    EXPIRED = "expired"
    MALFORMED = "malformed"
    BAD_SIGNATURE = "bad_signature"
    INVALID = "invalid"

def decode_token(token: str) -> tuple[Optional[dict], Optional[TokenValidationError]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, TokenValidationError.EXPIRED
    except jwt.JWTError:
        return None, TokenValidationError.INVALID
```

---

#### BUG-027 (MEDIUM) — No rate limiting on `/api/auth/refresh`

**File:** `middleware/rate_limit.py:49`

The rate limiter only applies to `POST /api/auth/login`. The `/api/auth/refresh` endpoint has no rate limiting. An attacker who obtains a valid refresh token can call `/api/auth/refresh` repeatedly, generating unlimited new token pairs.

**Impact:** MEDIUM — token abuse. Each call creates a new access + refresh token pair. While the old tokens remain valid (BUG-025), this multiplies the attack surface.

**Fix:** Extend rate limiter to cover `/api/auth/refresh`:

```python
if request.url.path in ("/api/auth/login", "/api/auth/refresh") and request.method == "POST":
```

---

#### BUG-028 (LOW) — `get_current_user` queries DB on EVERY request

**File:** `deps.py:35-55`

```python
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
```

**Root cause:** Every authenticated API call queries the database for the user. For high-traffic endpoints, this creates unnecessary DB load. The JWT payload already contains all the information needed for most operations (user_id, role, email).

**Impact:** LOW — performance issue, not a correctness issue. Every API call adds ~1-5ms DB query latency.

**Alternative:** Cache the user in-memory with a short TTL (e.g., 60 seconds). Or use a JWT-only validation for read-only endpoints.

---

## 4. Auth Flow Diagram — Login

```
User                Login.tsx          useAuth               api.ts               Backend
 │                    │                  │                     │                    │
 │  click Submit      │                  │                     │                    │
 │───────────────────►│                  │                     │                    │
 │                    │                  │                     │                    │
 │                    │ validate()       │                     │                    │
 │                    │─────────────────►│                     │                    │
 │                    │◄──────────────── │                     │                    │
 │                    │                  │                     │                    │
 │                    │ login(data)      │                     │                    │
 │                    │─────────────────►│                     │                    │
 │                    │                  │  POST /api/auth/    │                    │
 │                    │                  │  login              │                    │
 │                    │                  │────────────────────►│                    │
 │                    │                  │                     │  Rate limit check  │
 │                    │                  │                     │────────────────────►│
 │                    │                  │                     │◄─────────────────── │
 │                    │                  │                     │                    │
 │                    │                  │                     │  Account lockout   │
 │                    │                  │                     │  check             │
 │                    │                  │                     │────────────────────►│
 │                    │                  │                     │◄─────────────────── │
 │                    │                  │                     │                    │
 │                    │                  │                     │  authenticate_user │
 │                    │                  │                     │────────────────────►│
 │                    │                  │                     │◄─────────────────── │
 │                    │                  │                     │                    │
 │                    │                  │                     │  TokenResponse ◄───│
 │                    │                  │                     │◄────────────────────│
 │                    │                  │◄─────────────────────│                    │
 │                    │                  │                     │                    │
 │  BUG-018:          │    onSuccess     │                     │                    │
 │  Interceptor       │◄─────────────────│                     │                    │
 │  tries refresh     │                  │                     │                    │
 │  on 401 HERE       │                  │                     │                    │
 │                    │  storeLogin()    │                     │                    │
 │                    │  navigate()      │                     │                    │
 │                    │──────────────────│                     │                    │
 │                    │                  │                     │                    │
 │  BUG-002 (FIXED):  │  useEffect      │                     │                    │
 │  AuthProvider      │  validateSession│  GET /api/auth/me   │                    │
 │  fires             │─────────────────►│────────────────────►│                    │
 │                    │                  │  meQuery fires      │                    │
 │                    │                  │────────────────────►│                    │
 │                    │                  │                     │                    │
 │                    │  REDIRECT to     │                     │                    │
 │                    │  /admin          │                     │                    │
 │◄───────────────────│                  │                     │                    │
```

## 5. Auth Flow Diagram — Token Refresh (Race Detail)

```
Time    api.ts Interceptor
 │
 │  Request A → 401
 │    originalRequest._retry = true
 │    isRefreshing = true
 │    refreshToken = "..."
 │
 ├── POST /api/auth/refresh { refresh_token }
 │     │
 │     │    Request B → 401 (concurrent)
 │     │      isRefreshing? YES → queue
 │     │      pendingRequests.push({ resolve, reject })
 │     │
 │     ├── Refresh SUCCEEDS
 │     │    store.login(new_token)
 │     │    processPendingRequests(new_token)  → Request B resumes
 │     │    originalRequest.headers.Auth = new_token
 │     │    retry Request A with new_token
 │     │
 │     │    ★ BUG-016: race here:
 │     │    processPendingRequests runs
 │     │    THEN Request C gets 401, sees isRefreshing=true, queues
 │     │    THEN finally: isRefreshing=false
 │     │    THEN finally: pendingRequests has Request C → resolved with new_token ✓
 │     │
 │     └── Refresh FAILS
 │          clearPendingRequests(error) → Request B rejected
 │          isRefreshing = false
 │          ★ BUG-017: if Request C arrived between clear and finally,
 │            and token is still old/expired, Request C gets expired token
 │          ★ then Request C retries with expired token → 401 again
 │          ★ but _retry=true already → 401 propagates to caller → unexpected error
```

## 6. Observability Strategy

### 6.1 Auth-Specific Trace Events

Create structured auth events emitted to the existing `SwarmDiagnosticsEngine`:

| Event Type | When | Payload |
|-----------|------|---------|
| `auth:login:attempt` | User submits login form | `{ identifier_type, ip, correlation_id }` |
| `auth:login:success` | Server validates credentials | `{ user_id, role, login_latency_ms }` |
| `auth:login:failed` | Wrong credentials | `{ remaining_attempts, lockout_active }` |
| `auth:login:rate_limited` | IP or account blocked | `{ block_type: ip|account, retry_after_s }` |
| `auth:token:refresh` | Interceptor refreshes token | `{ old_token_exp, new_token_exp }` |
| `auth:token:refresh_failed` | Refresh endpoint fails | `{ reason }` |
| `auth:session:validate` | AuthProvider checks /me | `{ valid, error }` |
| `auth:session:logout` | User logs out or session expires | `{ reason: manual|expired|error }` |
| `auth:role:check` | Route guard checks role | `{ required, actual, allowed }` |

### 6.2 Metrics to Collect

```
auth_login_total{status="success|failure|rate_limited"}
auth_login_duration_ms{status="success|failure"}     // histogram
auth_token_refresh_total{status="success|failure"}
auth_token_refresh_duration_ms                        // histogram
auth_session_validation_total{status="valid|invalid|error"}
auth_concurrent_sessions                              // gauge per user
auth_rate_limit_remaining{type="ip|account"}          // gauge per IP
```

### 6.3 Frontend Auth Logging

Add a `logger` module for the frontend that sends auth events to the backend via the existing `audit_service` endpoint:

```tsx
// frontend/src/lib/auth-logger.ts
export function logAuthEvent(event: string, payload: Record<string, unknown>) {
    // In production, POST to /api/audit/auth-events
    // In development, console.debug with trace info
    if (import.meta.env.DEV) {
        console.debug(`[AUTH] ${event}`, payload)
    }
}
```

### 6.4 Dashboard: Auth Health

Expose auth metrics at `GET /api/auth/health`:

```json
{
    "rate_limiter": { "active_buckets": 42, "total_blocked_today": 156 },
    "account_lockouts": { "active_lockouts": 3, "total_today": 12 },
    "token_refresh": { "total": 1423, "failed": 12, "success_rate": 0.992 },
    "active_sessions": { "unique_users": 87, "total_tokens": 174 }
}
```

---

## 7. Regression Prevention Recommendations

### 7.1 Auth Integration Tests

```python
# Required new tests:
def test_login_success_does_not_count_against_rate_limit()
def test_transient_network_error_does_not_logout_user()
def test_concurrent_token_refresh_only_makes_one_refresh_call()
def test_auth_middleware_skips_login_endpoint_refresh()
def test_refresh_token_rotation_invalidates_old_token()
def test_auth_event_emitted_on_every_auth_operation()
def test_auth_metrics_updated_on_login_refresh_logout()
def test_concurrent_login_attempts_same_ip_rate_limited()
def test_account_lockout_by_code_and_email_both_work()
```

### 7.2 Auth Fuzzing Tests

```python
def test_malformed_token_returns_401_not_500()
def test_expired_token_returns_401_with_proper_header()
def test_wrong_algorithm_token_rejected()
def test_token_with_missing_sub_rejected()
def test_refresh_token_without_type_field_rejected()
def test_replayed_refresh_token_detected()
```

### 7.3 Code Review Checklist

For every auth-related PR:

- [ ] Does the change add a new API call that could return 401? → Add interceptor exception handling
- [ ] Does the change modify auth state? → Update both zustand store AND React Query cache
- [ ] Does the change add a new auth route? → Add rate limiting + auth event emission
- [ ] Does the change read user role? → Read from JWT payload, not just from DB
- [ ] Does the change make an auth decision? → Log the decision with correlation ID
- [ ] Does the change handle concurrent auth ops? → Verify thread safety (backend) + ref stability (frontend)

### 7.4 Monitoring Alerts

| Condition | Alert | Action |
|-----------|-------|--------|
| >10 auth failures/user/min | `auth_brute_force_attempt` | Block IP, notify security |
| Token refresh success rate <95% | `auth_refresh_failure_rate` | Investigate backend health |
| `auth:session:validate` errors >1/min | `auth_validation_errors` | Check backend /me endpoint |
| Concurrent sessions/user >5 | `auth_session_piggyback` | Investigate token sharing |
| Rate limiter bucket count >1000 | `auth_rate_limiter_memory` | Scale or clean up buckets |

---

## 8. Auth Stability Recommendations

### 8.1 Critical (Fix Immediately)

1. **BUG-014:** Fix `validateSession()` to only logout on 401, not on transient errors
2. **BUG-022:** Fix `Onboarding.tsx` stale closure — use `useAuthStore.getState().user`
3. **BUG-023:** Implement basic auth event tracing using existing `CorrelationEngine`

### 8.2 High (Fix This Week)

4. **BUG-024:** Add `iat`, `jti`, `nbf`, `type` claims to JWT
5. **BUG-025:** Implement refresh token rotation + versioning
6. **BUG-026:** Return structured errors from `decode_token` (distinguish expired vs malformed)
7. **BUG-018:** Skip 401 interceptor for `/api/auth/login`
8. **BUG-027:** Add rate limiting to `/api/auth/refresh`

### 8.3 Medium (Fix This Sprint)

9. **BUG-015:** Stabilize multi-tab storage event handling — use `useRef` for navigate
10. **BUG-017:** Fix orphaned request race in `finally` block — add lock
11. **BUG-019:** Remove `window.location.href` from interceptor — let React Router handle navigation
12. **BUG-020:** Add `/api/auth/login` to the interceptor skip list
13. **BUG-021:** Add keepPreviousData or disable the AcademicGuard query when navigating away

### 8.4 Low (Fix When Time)

14. **BUG-028:** Add user caching layer for `get_current_user`
15. **BUG-016:** Minor latency reduction in 401 handling for login endpoint
16. Remove `decodeJwtPayload` and use proper JWT verification for client-side checks
17. Add hierarchical role system (admin inherits all roles, etc.)

### 8.5 Architecture Recommendations

1. **Consolidate auth state sources:** Currently three sources compete (zustand store, AuthContext, React Query). Consolidate to ONE source of truth (zustand) and derive everything else.

2. **Implement auth state machine:** Model auth as a state machine (Unauthenticated → Authenticating → Authenticated → Refreshing → Expired → Unauthenticated). Every transition emits an event.

3. **Add token introspection endpoint:** `POST /api/auth/introspect` that returns token metadata (issued_at, expires_at, scopes, user_id, role). Use this from the frontend instead of client-side JWT decoding.

4. **Replace `window.location.href` with event-driven navigation:** Create an `AuthEventBus` that components subscribe to. When a session expires, emit `auth:expired` → ProtectedRoute navigates to `/login`.

5. **Add request idempotency for auth endpoints:** Login requests should be idempotent (using the existing `IdempotencyKey` infrastructure) to prevent duplicate account lockout increments on retry.

6. **Implement progressive token expiry:** Instead of jumping from 60min to expired, warn the user at 50min that the session will expire soon. This prevents surprise logouts during active use.
