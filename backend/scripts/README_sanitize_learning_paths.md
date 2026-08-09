# sanitize_learning_paths.py

## Qué problema resuelve

Antes del 2026-07-20, crear o editar un estudiante con Ciclo desde
Administrador disparaba `academic_activation_pipeline.activate_student()`
(pipeline legado de matrícula por malla curricular), que generaba un
`LearningPath` de inmediato — incluyendo, si el ciclo coincidía, uno para
IS301 (Fundamentos de Programación) — sin que el estudiante hubiera rendido
nunca el pre-test.

`knowledge_test_service.get_test_status()` exige `not has_learning_path`
para exigir el pre-test, así que esos estudiantes quedaron con
`pretest_required=False` para siempre: el pre-test nunca aparecía.

El fix de código (`user_service.py`, 2026-07-20) desacopló Ciclo del
pipeline legado — ningún flujo vivo crea ya un `LearningPath` así. Este
script limpia los `LearningPath` que ya habían quedado contaminados en la
base de datos **antes** de ese fix.

## Qué hace

1. Busca candidatos: `LearningPath` del curso `IS301` con `knowledge_level
   IS NULL` (marca del creador legado — el creador moderno,
   `generate_learning_path_adaptive`, siempre lo puebla) y `generated_at`
   anterior al cutoff.
2. Excluye cualquier candidato donde haya evidencia de que el estudiante ya
   interactuó con la ruta: módulos con `status` distinto de
   `locked`/`available`, `completed_at` o `score` no nulos, o referenciados
   desde `evaluation_attempts`, `engagement_sessions` o `learning_sessions`.
   Estos NO se tocan — son estudiantes que ya usaban la plataforma antes de
   que existiera el pre-test (caso legítimo, exento por diseño, no basura).
3. Excluye también cualquier candidato con un `KnowledgeTestAttempt(kind='pre',
   status='completed')` ya registrado — si existe, el `knowledge_level NULL`
   tiene otra causa y no se debe tocar a ciegas.
4. Exporta **todo** lo encontrado (aceptados y excluidos, con la razón de
   exclusión) a un JSON en `backend/backups/` antes de borrar nada.
5. Solo borra si se pasa `--apply`. Sin ese flag es dry-run: audita y
   respalda, no modifica la base de datos.
6. Tras aplicar, reconsulta `knowledge_test_service.get_test_status()` para
   cada estudiante afectado y escribe un segundo JSON de verificación
   confirmando que `pretest_required` volvió a `True`.

## Qué NO hace

- No toca ninguna cuenta con progreso real, aunque su `LearningPath` tenga
  `knowledge_level NULL` (ver punto 2 arriba).
- No toca otros cursos (`EST201`, `MAT201`, etc.) — el pre-test solo aplica
  a IS301, y el resto del pipeline multi-curso es legado fuera de alcance.
- No borra `Enrollment`, `User`, `DiagnosticResult` ni ninguna otra tabla —
  solo `LearningPath` y sus `PathModule` hijos, y solo de los candidatos
  aceptados.
- No corre automáticamente. No hay cron ni hook — es manual, a propósito.

## Tablas que modifica (solo con `--apply`)

- `learning_paths` (DELETE, solo filas candidatas aceptadas)
- `path_modules` (DELETE, solo los hijos de esas filas)

## Tablas que lee pero nunca modifica

`courses`, `users`, `knowledge_test_attempts`, `evaluation_attempts`,
`engagement_sessions`, `learning_sessions`.

## Cómo ejecutar

Desde `backend/`, con el venv activado:

```bash
# 1. Dry run — audita y respalda, no borra nada. Ejecutar siempre primero.
python scripts/sanitize_learning_paths.py

# 2. Revisar el reporte impreso y el JSON en backend/backups/ antes de aplicar.

# 3. Aplicar
python scripts/sanitize_learning_paths.py --apply

# Opcional: fijar un cutoff exacto en vez de "ahora"
python scripts/sanitize_learning_paths.py --cutoff 2026-07-20
```

## Cómo restaurar (rollback)

El script no ofrece un `--restore` automático — el respaldo es la fuente de
verdad para reconstruir manualmente si hiciera falta. Cada
`learning_path_sanitization_<timestamp>.json` en `backend/backups/` trae,
por cada `LearningPath` borrado: `learning_path_id`, `student_id`,
`course_id`, `total_modules`, `generated_at` y la lista de `module_ids`
que tenía. Para restaurar una fila, recrear el
`LearningPath` con esos mismos valores (nunca tenían `knowledge_level` ni
módulos con contenido real — eran huérfanos vacíos, así que no hay datos de
usuario que reconstruir más allá de esos campos).

## Ejemplo de salida (dry run)

```
=== Saneamiento de LearningPath contaminados (curso IS301) ===
Cutoff: 2026-07-21T01:09:00+00:00
Candidatos a eliminar (huerfanos, sin pre-test, sin avance): 12
Excluidos para revision manual: 23
  - EXCLUIDO estudiante3@upao.edu.pe: 4 modulo(s) de la ruta ya fueron tocados...
  ...
Respaldo completo escrito en: backend/backups/learning_path_sanitization_...json

DRY RUN: no se elimino nada. Ejecuta con --apply para aplicar el saneamiento.
```
