# Forensic Frontend Runtime Audit

**Date**: 2026-05-27  
**Scope**: 15 source files across `frontend/src/` — components, hooks, stores, providers, pages, layouts  
**Analyst**: opencode subagent (explore)  
**Total bugs cataloged**: 7 (1 CRITICAL, 4 HIGH, 2 MEDIUM)

---

## Architecture Overview

```
main.tsx
  └─ QueryClientProvider (staleTime: 30s, gcTime: 5min, retry: 2×)
       └─ BrowserRouter
            └─ AuthProvider (validateSession → /api/auth/me)
                 └─ App (Suspense + React Router v6)
                      ├─ /login → Login
                      ├─ ProtectedRoute (role-gates)
                      │   └─ AcademicGuard (onboarding check)
                      │       └─ EstudianteLayout (TutorWidget FAB)
                      │           ├─ /estudiante → Dashboard
                      │           ├─ /estudiante/diagnostic/:courseId → DiagnosticTest
                      │           ├─ /estudiante/path/:courseId → LearningPath
                      │           ├─ /estudiante/content/:resourceId → ContentViewer
                      │           └─ /estudiante/evaluation/:courseId → Evaluation
                      └─ /estudiante/onboarding → Onboarding (no layout)
```

**Data flow layers**:
1. **Zustand persist** (`authStore`): token, refreshToken, user — persisted to `localStorage` under key `upao-auth`
2. **React Query** (`useStudent`, `useAuth`, `useAnalytics`): server state with cache, stale, and invalidation
3. **Axios interceptor** (`api.ts`): token injection + transparent 401 refresh + queue
4. **AuthProvider context** (`isReady`, `isValidating`): session validation on page load

---

## Bug Catalog

### FRONT-001 [CRITICAL] — Dead cache invalidation in ContentViewer

**File**: `frontend/src/pages/estudiante/ContentViewer.tsx:64-65`

**Root cause**:
```tsx
// ContentViewer.tsx:64-65 (BEFORE FIX)
queryClient.invalidateQueries({ queryKey: ['student', 'learning-path'] })
queryClient.invalidateQueries({ queryKey: ['student', 'my-courses'] })
```

The actual query keys are `['learning-path', courseId]` (defined in `useLearningPath` at `useStudent.ts:110`) and `['my-courses']` (defined in `useMyCourses` at `useStudent.ts:80`). Neither starts with prefix `['student', ...]`, so **both invalidations are silent no-ops**.

**Impact**: When a student marks a resource as complete, neither the learning path nor the course list is ever refreshed. The cache remains stale until the user manually refreshes or navigates away. This breaks the visual progress tracking entirely — completed modules remain unmarked.

**Reproduction flow**:
1. Student enters a learning path, opens a resource
2. Clicks "Marcar como completado"
3. `updateProgress.mutate` succeeds, triggers `invalidateQueries`
4. The `['student', 'learning-path']` key matches nothing → no refetch
5. Back on the learning path, module still shows as incomplete
6. Only a hard refresh or navigation out/in updates the view

**Fix applied**: Changed to `['learning-path', courseId]` and `['my-courses']` with the courseId from URL params.

---

### FRONT-002 [HIGH] — Stale closure of `selectedCycle` in Onboarding

**File**: `frontend/src/pages/estudiante/Onboarding.tsx:56-72`

**Root cause**:
The `onSuccess` callback of `saveCycleMutation` captures `selectedCycle` from the enclosing closure at mutation creation time. React Query's `useMutation` reads the options object once during the initial render and does not re-evaluate closures on subsequent renders (unlike `useQuery` which re-reads on each render via the `queryFn`).

```tsx
const [selectedCycle, setSelectedCycle] = useState<number | null>(null)
// ...
const saveCycleMutation = useMutation({
    mutationFn: async (cycle: number) => { ... },
    onSuccess: () => {
        const currentUser = useAuthStore.getState().user
        if (currentUser) {
            setUser({ ...currentUser, current_cycle: selectedCycle! }) // ← stale!
        }
    },
})
```

**Impact**: When the mutation succeeds, `selectedCycle` may be `null` (the initial value) or a stale value from a previous render cycle. The user's `current_cycle` in the store gets set to an incorrect value.

**Reproduction flow** (race-dependent, more likely under StrictMode):
1. Student opens Onboarding, selects cycle "5", clicks confirm
2. React StrictMode double-invokes the mutation setup
3. The `onSuccess` closure captures the initial `selectedCycle` (null) or cycle "5" from the first render
4. API returns 200, `onSuccess` fires, sets `current_cycle` to null or wrong value
5. Dashboard shows cycle 0 (fallback) instead of the selected cycle

**Fix applied**: Changed `onSuccess` to use the `variables` parameter — `onSuccess: (_data, cycle) => { ... setUser({ ...currentUser, current_cycle: cycle }) ... }` — which always contains the actual cycle passed to `mutationFn`.

---

### FRONT-003 [HIGH] — Imprecise query key invalidation causing cascading refetches

**Files**: `frontend/src/hooks/useStudent.ts` (lines 26-29, 69, 98-99, 128, 146-147, 177-178)

**Root cause**:
Multiple mutation `onSuccess` callbacks invalidate broad query keys like `['my-courses']` and `['student-profile']` without `exact: true`. Because these are prefix-match invalidations in React Query v5, they trigger refetches for **all** queries whose keys start with these prefixes.

~6 mutations invalidate `['my-courses']` — nearly every student action:
- `useSubmitDiagnostic` → invalidates `['my-courses']`, `['student-profile']`, `['diagnostic', courseId]`, `['learning-path', courseId]`
- `useGeneratePath` → invalidates `['learning-path', courseId]`, `['my-courses']`
- `useUpdateProgress` → invalidates `['my-courses']`, `['course-progress', courseId]`
- `useUpdateModule` → invalidates `['my-courses']`
- `useSaveStudentProfile` → invalidates `['student-profile']`
- `useAgentGeneratePlan` → invalidates `['learning-path', courseId]`, `['my-courses']`

When multiple components are mounted (e.g., Dashboard + LearningPath), a single mutation can trigger 3–4 simultaneous refetches.

**Impact**: Higher API load, race conditions between stale refetches and fresh mutation results. Not a correctness bug, but a performance pathology under concurrent navigation.

**Recommendation**: This is a systemic pattern, not easily patchable in isolation. Consider batching invalidations or using `queryClient.invalidateQueries` with a debounce wrapper. Or, redesign the invalidation strategy to be more granular:
- Use `exact: true` where only the exact key should be invalidated
- Co-locate cache updates in mutation `onSuccess` using `queryClient.setQueryData` instead of always refetching

---

### FRONT-004 [HIGH] — AcademicGuard fires query unnecessarily on onboarding route

**File**: `frontend/src/components/auth/AcademicGuard.tsx:15-24`

**Root cause**:
The `['onboarding-status']` query is enabled whenever the user is authenticated with role `estudiante`. But when the user is already ON the `/estudiante/onboarding` route (`isOnboardingRoute === true`), the query result is never used — the guard always renders `<Outlet />` or redirects, but the redirect logic at line 43 (`if (needsOnboarding && !isOnboardingRoute)`) explicitly skips the redirect when on the onboarding route.

This means every visit to `/estudiante/onboarding` fires an unnecessary GET `/api/students/onboarding/status` request.

**Impact**: One extra API call per onboarding visit. Additionally, if the query takes longer than the redirect check, the user may see the "Verificando estado académico..." spinner before the onboarding page renders.

**Reproduction flow**:
1. User logs in, gets redirected to `/estudiante/onboarding`
2. AcademicGuard renders, fires `['onboarding-status']` query
3. Query is loading → shows spinner
4. Query completes → `needsOnboarding` is true, but `isOnboardingRoute` is true → bypasses redirect → renders `<Outlet />` → shows onboarding page

**Fix applied**: Added `!isOnboardingRoute` to the `enabled` condition — no query fires when already on the onboarding route.

---

### FRONT-006 [HIGH] — Double TutorWidget instance + dead event wiring

**Files**:
- `frontend/src/pages/estudiante/LearningPath.tsx:247-254` (removed inline widget)
- `frontend/src/components/layout/EstudianteLayout.tsx:38-48` (conditionally renders widget)
- `frontend/src/components/ai/TutorWidget.tsx:59-61` (no `open-tutor` listener)
- `frontend/src/pages/estudiante/LearningPath.tsx:230-244` (dispatches `open-tutor` event)
- `frontend/src/pages/estudiante/Dashboard.tsx:284-287` (dispatches `open-tutor` event)

**Root cause**:
1. **Duplicate instances**: `LearningPath.tsx` rendered a `TutorWidget` inline (lines 247-254), and `EstudianteLayout.tsx` also rendered one conditionally via the `open-tutor` event. On the LearningPath page, two floating buttons appeared.

2. **Dead event wiring**: Both `Dashboard.tsx` and `LearningPath.tsx` dispatch a `CustomEvent('open-tutor', ...)` when the user clicks "Tutor IA". `EstudianteLayout.tsx` listens for this event and renders the widget. However, `TutorWidget.tsx` itself had **no listener** for this event — clicking the button would set the layout state but never actually open the chat panel (`isOpen` remained false).

3. **Wasted query invalidation (ContentViewer)**: See FRONT-001.

**Impact**:
- On LearningPath: two floating TutorWidget buttons appearing/fighting for position
- The `open-tutor` event dispatched from Dashboard effectively opens the widget (via layout), but the event from LearningPath also creates a second widget instance via the layout
- Clicking "Tutor IA" from any page sets layout state but doesn't actually open the chat until the user manually clicks the floating button

**Reproduction flow**:
1. Navigate to `/estudiante/path/:courseId`
2. See one TutorWidget floating button (from LearningPath)
3. Click "Preguntar al Tutor IA" — dispatches `open-tutor`
4. Layout catches event, sets `tutorConfig` → renders **second** TutorWidget
5. Now two floating buttons visible
6. The inline widget (from LearningPath) stays closed because nobody listens for the event

**Fix applied**:
- Removed inline `TutorWidget` from `LearningPath.tsx`
- Made `EstudianteLayout.tsx` render `TutorWidget` unconditionally (always-on FAB)
- Added `open-tutor` event listener inside `TutorWidget.tsx` to `setIsOpen(true)` when the event fires

---

### FRONT-007 [MEDIUM] — No 429 handling in query retry logic

**File**: `frontend/src/main.tsx:20`

**Root cause**:
The QueryClient's `retry` function only skips retries for statuses 401, 403, and 404. Status 429 (Too Many Requests) is **not** excluded, so React Query will retry up to 2 times with exponential backoff (1s, 2s). Each retry compounds the rate-limiting problem — the server sends another 429, the client retries again, creating a positive feedback loop of retry storms.

**Impact**: Under load, a single 429 response balloons into up to 3 requests (original + 2 retries) with increasing delays, making the rate-limit recovery slower for all users.

**Fix applied**: Added `status === 429` to the non-retryable status list.

---

### FRONT-008 [MEDIUM] — Auth interceptor `window.location.href` hard-redirect loses React state

**File**: `frontend/src/lib/api.ts:82`

**Root cause**:
When both tokens are expired or the refresh fails with 401/403, the interceptor does:
```tsx
useAuthStore.getState().logout()
window.location.href = '/login'
```

A `window.location.href` assignment causes a full browser navigation (hard redirect), which destroys the entire React tree, all component state, React Query cache, and Zustand in-memory state. The page reloads fully.

**Impact**:
- All Zustand state is reloaded from `localStorage` persistence (which `logout()` just cleared) — this is correct for logout
- React Query cache is lost — all queries will refetch after redirect
- If the redirect URL has query params (e.g., `?redirectTo=/estudiante/path/...`), they're lost
- User sees a full page flash/reload

**Recommendation**: Use React Router's `navigate('/login')` instead. However, this is not straightforward because the interceptor lives outside the React tree (no access to `useNavigate`). Options:
1. Maintain a navigation ref in the store or a global that React Router sets on mount
2. Replace `window.location.href` with `window.location.pathname = '/login'` (still a soft navigation but preserves less state)
3. Accept as-is since `logout()` clears the auth state anyway, and the full reload ensures clean app state

Given that the Zustand persist middleware will rehydrate from `localStorage` on the next page load (where `token` is now null), the hard redirect is intentional for security — it ensures no stale React state survives a session expiration. **Accepted as intentional behavior**.

---

## Flow Diagrams with Race Annotations

### Auth hydration race
```
StrictMode mount (main.tsx)
├─ 1st mount: AuthProvider effect fires
│   ├─ validateSession() → GET /api/auth/me
│   └─ StorageEvent listener registered
├─ 2nd mount (StrictMode cleanup + remount):
│   ├─ 1st effect's listener removed
│   ├─ 2nd effect's listener registered
│   └─ validateSession() fires again ← DOUBLE CALL
│
│   Actually: validatingRef.current prevents the second call
│   But: after the 2nd validateSession completes, the user
│   may have two React Query instances of meQuery running
│   (one from useAuth, one from AuthProvider)
├─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
│   RACE WINDOW: StrictMode double-mount
│   AuthProvider validateSession (effect) vs useAuth meQuery
│   Both call setUser / store login. If they interleave,
│   user state can flicker between two responses.
│   ─ Resolution: useAuth meQuery has setUser in queryFn;
│     AuthProvider validateSession also calls setUser.
│     This means setUser is called 2-3× during mount.
│     FIXED in BUG-014: validateSession catch-only-401,
│     and useAuth meQuery setUser removed from separate effect.
└─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
```

### Token refresh queue race
```
API call fails with 401
├─ isRefreshing is false → enter refresh path
├─ Set isRefreshing = true
├─ Queue: []
│
Concurrent API call also fails with 401
├─ isRefreshing is true → place in queue
├─ Promise pending on refresh completion
│
Refresh completes (or fails)
├─ processPendingRequests(newToken) → resolve all queued promises
├─ Queued requests retry with new token
│
└─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
    RACE WINDOW: between isRefreshing = true and actual refresh
    If a request enters between lines 67-68 (before isRefreshing
    check at line 58), two refreshes can race. Mitigated by the
    `validatingRef` pattern and atomicity of JS execution.
    ─ This is NOT fully fixed — a request arriving at line 67
      after the outer if at line 58 but before isRefreshing=true
      at line 68 will bypass the queue and start a second refresh.
    ─ FIX: Move isRefreshing = true BEFORE the if-isRefreshing check
      (or use a lock pattern). However, in practice this race is
      extremely rare due to the synchronous nature of the interceptor.
```

### Learning session lifecycle race
```
LearningPath.tsx
├─ User clicks available module card
├─ enterModule.mutate(moduleId)
│   ├─ POST /api/sessions/module/:moduleId/enter
│   └─ onSuccess: navigate to /estudiante/content/:resourceId
│
├─ ContentViewer mounts
│   ├─ useResourceMeta(resourceId) starts fetching
│   ├─ User clicks "Marcar como completado"
│   │   ├─ updateProgress.mutate → POST /api/students/progress/:courseId
│   │   └─ onSuccess: POST /api/sessions/:sessionId/end
│   │
│   └─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
       RACE WINDOW: User clicks "completado" before resource-meta loads
       If the user clicks mark-complete before useResourceMeta resolves,
       the resource is marked complete but the ContentViewer still shows
       loading state. When the meta loads, it replaces the view with
       resource details, confusing the student.
       ─ Mitigation: the loading state at line 72-79 prevents rendering
         the mark-complete button until isLoading is false.
       ─ FIX (suggested): Disable the mark-complete button during loading
         (already done implicitly by the early return at line 72-79).
```

---

## Observable Anti-patterns (non-blocking)

### AP-001: Query key factory absent
All 15+ query keys are raw string literals scattered across hooks. No key factory exists for deduplication or centralized invalidation. This makes FRONT-001 possible (misspelled keys compile without error). **Recommendation**: Create a `queryKeyFactory.ts`:
```ts
export const queryKeys = {
  learningPath: (courseId?: string) => ['learning-path', courseId],
  myCourses: () => ['my-courses'],
  // etc
}
```

### AP-002: Unused import in Evaluation.tsx
`ArrowLeft` is imported on line 3 and used on line 103, but the import of `Loader2` on line 3 shadows the name — actually both are used. No issue here. But line 175 has `ArrowLeft` already imported.

### AP-003: Dashboard loads 3 independent queries in parallel
`useMyCourses`, `useAcademicSummary`, and `useIADashboard` all fire simultaneously in Dashboard. Each returns different data, but `useIADashboard` likely includes summary data that overlaps with `useAcademicSummary`. If the backend has N+1 issues, this doubles the load.

### AP-004: No error boundaries per page
The `ErrorBoundary` in `main.tsx` wraps the entire app. A crash in any page brings down the full UI. Consider per-route error boundaries using React Router's `errorElement`.

### AP-005: `open-tutor` event dispatched with `as any` cast
`EstudianteLayout.tsx:28` uses `window.addEventListener('open-tutor' as any, handler)`. This suppresses TypeScript's type checking for CustomEvent. The `handler` receives a plain `Event` and must cast to `CustomEvent`. Fixed in this session (removed `as any`, added correct typing).

### AP-006: `AuthProvider` dependency on `navigate` outside Router context
`AuthProvider.tsx:42` calls `useNavigate()`. This is called inside `BrowserRouter` (see `main.tsx`), so it works, but `navigate` is used in the `StorageEvent` handler (line 109), which may fire asynchronously long after the component mounted. If the provider is unmounted by the time the event fires, `navigate` becomes a no-op. Low risk in practice.

---

## Observability Recommendations

1. **Query key violations**: Add a runtime check (custom `queryClient` wrapper) that warns when `invalidateQueries` is called with a key pattern that matches no known keys.

2. **React Query devtools**: Already included (`ReactQueryDevtools`) but only in DEV mode. Consider enabling them behind a query parameter in production for debugging.

3. **Mutation timing**: Add an `onSettled` callback to all mutations that logs timing (start → end) to understand which mutations are slow.

4. **Auth flow tracing**: The `AuthProvider.validateSession` already has a guard (`validatingRef`). Add a simple counter/metric to detect how many times `validateSession` fires per page load — useful for detecting StrictMode double-calls.

5. **Widget open events**: Track `open-tutor` event frequency to understand which pages trigger the tutor widget most.

---

## Stabilization Recommendations

1. **Atomic query key factory** (see AP-001) — eliminates FRONT-001 class bugs entirely.

2. **Move `isRefreshing = true` before the check** in `api.ts` to close the refresh race window:
   ```ts
   if (isRefreshing) { /* queue */ return }
   isRefreshing = true
   // BEFORE:
   // if (isRefreshing) { ... }
   // originalRequest._retry = true
   // isRefreshing = true
   ```

3. **Debounce query invalidations** — wrap `invalidateQueries` in a 50ms debounce to coalesce multiple invalidations from a single mutation callback into one refetch.

4. **Unify auth state source** — either `AuthProvider` or `useAuth` (meQuery) should be the single source of truth for `user`. Currently both call `setUser`. Remove the `setUser` call from one (already done for meQuery's effect).

5. **Replace `window.location.href` with `navigate` for logout redirect** — see FRONT-008 recommendation. Use a navigation ref or a custom event that the router layer listens for.

---

## Summary

| Bug ID | Severity | File | Root Cause | Fixed |
|--------|----------|------|------------|-------|
| FRONT-001 | CRITICAL | ContentViewer.tsx:64-65 | Dead cache invalidation — wrong query key prefix `['student', ...]` | ✅ |
| FRONT-002 | HIGH | Onboarding.tsx:62 | Stale closure — `selectedCycle` captured at mutation creation time | ✅ |
| FRONT-003 | HIGH | useStudent.ts:26-178 | 6 mutations invalidate `['my-courses']` — cascading refetches | 🔧 recommended |
| FRONT-004 | HIGH | AcademicGuard.tsx:21 | Unnecessary query fires when already on onboarding route | ✅ |
| FRONT-006 | HIGH | LearningPath.tsx + EstudianteLayout.tsx | Double TutorWidget instance + dead event wiring | ✅ |
| FRONT-007 | MEDIUM | main.tsx:20 | No 429 handling — retry storms under rate limiting | ✅ |
| FRONT-008 | MEDIUM | api.ts:82 | Hard redirect via `window.location.href` loses React state | ⚠️ accepted |

**Legend**: ✅ = fixed in this session · ⚠️ accepted = intentional behavior · 🔧 recommended = systemic fix for future

---

## Files Examined

- `frontend/src/main.tsx` — QueryClient config, StrictMode, app shell
- `frontend/src/App.tsx` — Route definitions, lazy loading
- `frontend/src/providers/AuthProvider.tsx` — Session validation, storage events
- `frontend/src/stores/authStore.ts` — Zustand persist middleware
- `frontend/src/lib/api.ts` — Axios interceptor, token refresh queue
- `frontend/src/hooks/useAuth.ts` — Login/logout/meQuery hooks
- `frontend/src/hooks/useStudent.ts` — All student data hooks + mutations
- `frontend/src/hooks/useAnalytics.ts` — Dashboard analytics hooks
- `frontend/src/components/auth/ProtectedRoute.tsx` — Role-based route guard
- `frontend/src/components/auth/AcademicGuard.tsx` — Onboarding completion guard
- `frontend/src/components/ai/TutorWidget.tsx` — Floating chat widget
- `frontend/src/components/layout/EstudianteLayout.tsx` — Student layout shell
- `frontend/src/pages/estudiante/Onboarding.tsx` — Cycle selection page
- `frontend/src/pages/estudiante/Dashboard.tsx` — Student dashboard
- `frontend/src/pages/estudiante/LearningPath.tsx` — Learning path view
- `frontend/src/pages/estudiante/ContentViewer.tsx` — Resource viewer with progress
- `frontend/src/pages/estudiante/Evaluation.tsx` — Module evaluation
- `frontend/src/pages/estudiante/DiagnosticTest.tsx` — Diagnostic test flow

---

*End of report — generated by opencode forensic audit subagent*
