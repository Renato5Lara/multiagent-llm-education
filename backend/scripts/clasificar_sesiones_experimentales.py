"""Clasificación reproducible de `runtime.runtime_sessions` por origen —
Objetivo D de la Fase 1 de remediación (investigación de causa raíz de
Validar/multimodalidad/scope, 2026-08-07).

100% lectura: solo `SELECT`, nunca `DELETE`/`UPDATE`/`TRUNCATE`. No
decide qué hacer con cada categoría — solo las distingue de forma
reproducible, para que Iteración 6.4 (y cualquier iteración H10 futura
que lea `runtime_sessions`) pueda filtrar antes de calcular estadísticas
en vez de tratar las 902 sesiones como una población homogénea.

Categorías (mutuamente excluyentes, en este orden de prioridad):

- CLEAN_REAL: `student_id` existe en `users` Y tiene al menos una
  inscripción real en `enrollments`.
- E2E_SEED: `student_id` existe en `users` pero sin inscripción real —
  o el propio `session_id` sigue el patrón `e2e-<numero>` de las
  suites E2E (aunque el estudiante sí tenga inscripciones, se marca
  aparte por ser tráfico de prueba, no orgánico).
- ORPHAN: `student_id` no corresponde a ninguna fila de `users`.

Origen investigado (no una acción de este script): el patrón dominante
de ORPHAN (`curso:<uuid>:estudiante:<uuid>`, la misma forma que
`app/services/runtime_bridge.py::_sesion_del_curso` produce en
producción) coincide con un bug ya documentado y corregido en
`app/services/runtime_connection.py` — lectura de variables de entorno
a nivel de módulo en vez de perezosa, que hacía que el aislamiento de
esquema de algunas suites de test de la Épica 2 nunca se aplicara de
verdad y el esquema `runtime` real acumulara sesiones de prueba. La fix
ya está en el código (lectura perezosa dentro de `almacenes()`); las
filas ORPHAN existentes son el residuo histórico de antes de ese fix,
no una fuga activa — no hay evidencia de que corran alto riesgo de
seguir creciendo hoy.

Uso: python scripts/clasificar_sesiones_experimentales.py
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from sqlalchemy import create_engine, text

from app.core.config import settings


@dataclass(frozen=True)
class SesionClasificada:
    session_id: str
    student_id: str
    categoria: str


_QUERY = text(
    """
    SELECT
        rs.session_id,
        rs.student_id,
        CASE
            WHEN u.id IS NULL THEN 'ORPHAN'
            WHEN rs.session_id LIKE 'e2e-%' THEN 'E2E_SEED'
            WHEN inscritos.n_inscripciones > 0 THEN 'CLEAN_REAL'
            ELSE 'E2E_SEED'
        END AS categoria
    FROM runtime.runtime_sessions rs
    LEFT JOIN users u ON u.id::text = rs.student_id
    LEFT JOIN (
        SELECT student_id::text AS student_id, count(*) AS n_inscripciones
        FROM enrollments
        GROUP BY student_id
    ) inscritos ON inscritos.student_id = rs.student_id
    ORDER BY rs.session_id
    """
)


def clasificar() -> list[SesionClasificada]:
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conexion:
        filas = conexion.execute(_QUERY).fetchall()
    return [
        SesionClasificada(session_id=f[0], student_id=f[1], categoria=f[2])
        for f in filas
    ]


def main() -> None:
    sesiones = clasificar()
    por_categoria: Counter[str] = Counter(s.categoria for s in sesiones)
    estudiantes_por_categoria: dict[str, set[str]] = {}
    for s in sesiones:
        estudiantes_por_categoria.setdefault(s.categoria, set()).add(s.student_id)

    print("=" * 78)
    print("CLASIFICACIÓN DE runtime.runtime_sessions — Objetivo D, Fase 1")
    print("=" * 78)
    print(f"Total de sesiones: {len(sesiones)}")
    print()
    print(f"{'Categoría':<12} {'Sesiones':>10} {'Estudiantes distintos':>24}")
    for categoria in ("CLEAN_REAL", "E2E_SEED", "ORPHAN"):
        n_sesiones = por_categoria.get(categoria, 0)
        n_estudiantes = len(estudiantes_por_categoria.get(categoria, set()))
        print(f"{categoria:<12} {n_sesiones:>10} {n_estudiantes:>24}")
    print()
    print(
        "CLEAN_REAL — candidatas a evidencia real de estudiantes de IS301 "
        "para recalibración de H10/6.4 (Objetivo E)."
    )
    print(
        "E2E_SEED — usuario real pero tráfico de prueba (E2E) o sin "
        "inscripción real; excluir de estadísticas poblacionales."
    )
    print(
        "ORPHAN — sin usuario real; residuo histórico del bug ya corregido "
        "en app/services/runtime_connection.py (Épica 2). No se borra aquí."
    )


if __name__ == "__main__":
    main()
