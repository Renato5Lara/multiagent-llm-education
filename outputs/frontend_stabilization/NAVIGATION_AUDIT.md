# NAVIGATION AUDIT

## Problem
- `/swarm-demo` and `/replay` had no navigation links anywhere in the app
- Only accessible by typing the URL directly
- `/investigador` had no layout, sidebar, or navigation

## Fix

### New: InvestigadorLayout
Created `components/layout/InvestigadorLayout.tsx` following the same pattern as `AdminLayout.tsx`:

```
+-------------------------------------------------------+
|  UPAO-MAS-EDU · Demo                    [rol] [user]  |
|  +-------+                                            |
|  | 📊 Dashboard     |  → /investigador                |
|  | 🤖 Demo Multiag. |  → /swarm-demo                  |
|  | 🕐 Replay Cogn.  |  → /replay                      |
|  +-------+                                            |
|  |  Main Content Area  (Outlet)                       |
|  +----------------------------------------------------+
```

### Navigation items
| Icon | Label | Route | Visibility |
|------|-------|-------|------------|
| `LayoutDashboard` | Dashboard | `/investigador` | investigador role only |
| `Bot` | Demo Multiagente | `/swarm-demo` | investigador role only |
| `History` | Replay Cognitivo | `/replay` | investigador role only |

### Intentional constraints
- Links are **only** in the investigador layout sidebar
- **Not** added to Admin, Docente, or Estudiante layouts
- `/swarm-demo` and `/replay` remain publicly accessible (unprotected) for demo flexibility
- No new navigation infrastructure was created

## Sidebar key features
- 64px width, dark theme (`#002550`)
- Mobile responsive with hamburger + overlay
- Active state highlighting
- Title: "UPAO-MAS-EDU · Demo"

## Files changed
- `frontend/src/components/layout/InvestigadorLayout.tsx` — new file
- `frontend/src/App.tsx` — imported and wired InvestigadorLayout
