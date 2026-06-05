# ROUTING FIXES

## Issue: Missing `/replay` route in App.tsx

**Severity:** Critical (dead component)

**Before:** `ReplayDashboard.tsx` existed at `pages/replay/` but was neither imported nor registered in `App.tsx`.

**Fix:**
- Added lazy import: `const ReplayDashboard = lazy(() => import('@/pages/replay/ReplayDashboard'))`
- Added route: `<Route path="/replay" element={<ReplayDashboard />} />`
- Route placed alongside `/swarm-demo` as an unprotected demo route

## Issue: Inline JSX placeholder for `/investigador` route

**Severity:** Low (cosmetic/architecture)

**Before:**
```tsx
<Route path="/investigador" element={
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
            <h1 className="text-2xl font-bold mb-2">Panel del Investigador</h1>
            <p className="text-muted-foreground">Disponible en Fase 4</p>
        </div>
    </div>
} />
```

**Fix:**
- Created `pages/investigador/Dashboard.tsx` — a proper lazy-loaded component with navigation cards to `/swarm-demo` and `/replay`
- Route now uses `<InvestigadorDashboard />` component

## Files changed
- `frontend/src/App.tsx` — added 3 lazy imports + 2 routes + fixed investigador route structure
- `frontend/src/pages/investigador/Dashboard.tsx` — new file

## Validation
- `npm run build`: 0 errors, 920ms
- `npm run lint`: 0 errors, 1 pre-existing warning (React Hook Form / React Compiler)
- `ReplayDashboard` chunk: `dist/assets/ReplayDashboard-DE3u-9Hb.js` (23.99 kB)
- `SwarmDemo` chunk: `dist/assets/SwarmDemo-1HhKhU3m.js` (39.32 kB)
- `InvestigadorDashboard` chunk: bundled inline (minimal)
