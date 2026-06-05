# FINAL BUGS & KNOWN ISSUES

**Estado:** Post-sustentación — issues conocidos para backlog

---

## Bugs Confirmados

| ID | Severidad | Descripción | Archivo |
|----|-----------|-------------|---------|
| B1 | Media | `playMode` 'full' y 'week' tienen step=1 idénticos | ReplayDashboard.tsx:39 |

## Security Bypasses (aceptados)

| ID | Severidad | Descripción | Mitigación |
|----|-----------|-------------|------------|
| S1 | Alta | `__builtins__["__import__"]("os")` evade AST check | Runtime: builtins.__dict__ parcheado |
| S2 | Baja | Módulos network (telnetlib, smtplib, etc.) no bloqueados | Docker --network none |
| S3 | Baja | Módulos peligrosos (pickle, shelve, tempfile) no bloqueados | Docker --read-only |
| S4 | Baja | `[0] * 9999999999` (memory bomb) no bloqueado en AST | RLIMIT_AS en runner_payload |

## UX Issues

| ID | Severidad | Descripción |
|----|-----------|-------------|
| U1 | Media | Language mixing ES/EN sin estrategia de locale |
| U2 | Baja | SwarmDemo sin spinner de carga durante API call |
| U3 | Baja | Responsive sidebar con hardcoded 380px en lg |
| U4 | Media | AcademicGuard pasa silent en fallo de API |
| U5 | Baja | Password toggle sin aria-label |

## Mejoras Futuras

- Hardening: bloquear subscript access a __builtins__ en AST
- i18n: definir locale strategy (español)
- Loading states: skeletons en SwarmDemo
- Error boundaries por panel en swarm
- Tests E2E automatizados con Playwright/Cypress
