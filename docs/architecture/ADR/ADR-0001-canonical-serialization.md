# ADR-0001 — Serialización Canónica

- **Estado:** Aceptado (2026-07-10, Engineering Review — con la escala
  concreta degradada a política de precisión, por orden del tesista)
- **Fecha:** 2026-07-10
- **Preserva:** R3/R4 (RFC-0008), P12, P14, INV-11
- **Criterio de aceptación:** R1–R6 intactos (RFC-0008 §4)

## Decisión

Definir la forma canónica única en que el registro de una StateTransition
se serializa, de modo que la igualdad de R3 sea bit a bit verificable y la
historia sea hasheable.

1. **Formato:** JSON canónico según las reglas de JCS (RFC 8785): UTF-8,
   claves ordenadas lexicográficamente, sin espacio no significativo,
   números en forma canónica. Strings normalizadas NFC. `NaN`/`Infinity`
   prohibidos en cualquier payload.
2. **Identificadores deterministas:** los IDs los asigna el Kernel al
   aplicar, secuenciales por sesión — transición `T-000042`, entrada
   `T-000042/e1`. Nada de UUIDs aleatorios en el registro: un ID aleatorio
   es no-determinismo no grabado como tal (violaría A3). Los IDs son parte
   de la historia: legibles en trazas, estables en replay.
3. **Tiempo:** el tiempo lógico es el índice de transición (ya normativo,
   A4). El reloj de pared solo puede aparecer *dentro de payloads* como
   dato grabado (telemetría, ISO-8601 UTC) y jamás participa en
   derivaciones.
4. **Números de confianza:** *el contrato* es que las confianzas
   (declaradas y de resolución) se representan como **decimales exactos de
   escala fija** y las funciones de política operan en aritmética decimal
   — la coma flotante binaria es un riesgo de reproducibilidad entre
   plataformas (A3). *La escala concreta* pertenece a la política de
   precisión del runtime (valor inicial: 4 decimales) y puede evolucionar
   mediante un ADR de ingeniería siempre que preserve la serialización
   canónica y R1–R6. La escala vigente queda registrada como versión de
   configuración (R4: nada externo hace falta para reconstruir).
5. **Cadena de integridad:** cada transición serializada lleva
   `hash = SHA-256(forma canónica)` y `prev_hash` de su predecesora.
   La historia queda encadenada estilo ledger: **P14 deja de ser una
   promesa y se vuelve verificable** — cualquier alteración retrospectiva
   rompe la cadena, y la verificación es un recorrido. Consecuencia
   explícita (Engineering Review del tesista): **el runtime posee una
   prueba criptográfica de integridad histórica.** No es blockchain ni
   pretende serlo — no hay consenso distribuido ni minería —: es una
   cadena de integridad. Para la sustentación: evidencia demostrablemente
   no manipulada.

## Alternativas rechazadas

- **Pickle / serialización binaria del lenguaje:** atada a versión de
  runtime de Python; irreproducible a largo plazo e ilegible como
  evidencia.
- **JSON sin canonicalizar + comparación estructural:** la igualdad "según
  el parser" no es bit a bit; imposibilita el hash estable.
- **UUIDv4 para entradas:** no-determinismo gratuito dentro del registro.

## Consecuencias

- La forma canónica es la fuente para hash, comparación de replay (R3) y
  firma de integridad; cualquier otra representación es proyección.
- ADR-0002 debe almacenar los bytes canónicos tal cual (el hash se calcula
  sobre ellos).
