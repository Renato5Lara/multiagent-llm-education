"""Precondición mínima de la migración PREEXISTENTE d6e7f8a9b0c1 (datos): curso IS301 y 4 objetivos legados con ids fijos.
Se ejecuta entre `alembic upgrade c5d6e7f8a9b0` y `alembic upgrade head` (ver scripts/repro_db_bootstrap.sh)."""

from sqlalchemy import text

from app.db.session import SessionLocal

COURSE = "0fbe4f4c-1520-4ecc-ac84-cf0fed353eb0"
LEGACY = [("f71448b7-01f3-45ba-9fc6-8d168f6a4517", "Fundamentos de Python", 2, 1),
          ("d15bae53-e32d-4fc0-9341-1dc6f039344f", "Estructuras de control", 3, 2),
          ("6839a0cb-fd3b-4dc6-b7ae-309bd31a1247", "Funciones y módulos", 3, 3),
          ("8a68447a-9844-4ef3-81d8-0fe6db36d321", "Programación orientada a objetos", 3, 4)]


def main() -> None:
    """Único punto con efectos sobre la base: importar el módulo NO abre ninguna conexión."""
    with SessionLocal() as s:
        s.execute(text("insert into courses (id, code, name, cycle, year, status, created_at, updated_at, is_institutional) "
                       "values (:i,'IS301','Fundamentos de Programación',3,2026,'publicado',now(),now(),false) on conflict do nothing"),
                  {"i": COURSE})
        for lid, title, bloom, order in LEGACY:
            s.execute(text("insert into learning_objectives (id, course_id, title, description, bloom_level, \"order\") "
                           "values (:i,:c,:t,'legado',:b,:o) on conflict do nothing"),
                      {"i": lid, "c": COURSE, "t": title, "b": bloom, "o": order})
        s.commit()
    print("precondiciones de d6e7f8a9b0c1 listas")


if __name__ == "__main__":
    main()
