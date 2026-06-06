# Bug Report

## Metadata
- **ID:** BUG-032
- **Title:** validateSession() catch unconditionally logs out on transient errors
- **Date:** 2026-05-27
- **Severity:** CRITICAL
- **Category:** auth
- **Status:** FIXED
- **Commit:** `pending-BUG-014-fix`

## Síntomas

- Network timeout during page load terminates the session
- 500 error from /api/auth/me causes logout
- DNS failure triggers false-positive logout
- Transient faults indistinguishable from auth failures

## Root Cause

validateSession() catch block calls storeLogout() and queryClient.clear() for ANY error without checking if it is a 401/403 auth failure

## Flujo de reproducción

1. User has valid token in localStorage
2. AuthProvider mounts, calls validateSession()
3. /api/auth/me request fails with network timeout (no response)
4. catch block unconditionally calls storeLogout()
5. User is logged out despite having valid credentials

## Riesgo arquitectónico

Every page load becomes a single point of failure for session termination. A flaky network at the wrong moment destroys the user session, requiring re-login.

## Impacto en swarm

If swarm agents depend on auth state, a transient failure during agent coordination could terminate all agent sessions.

## Impacto en adaptación

Adaptive systems that retry on transient errors would conflict with this unconditional logout behavior.

## Impacto en consenso

Consensus rounds that span multiple requests risk session termination from a single transient failure.

## Impacto en resiliencia

Zero resilience to transient faults in the auth validation path.

## Impacto en shared memory

Cross-tab session invalidation from one tab could be triggered by a transient /api/auth/me failure in another tab.









## Archivos afectados

| Archivo | Líneas | Cambio |
|--------|--------|--------|
|  | 67-77 |  |




