"""IT-02 -- Integracion API <-> Servicio <-> PostgreSQL.

Componentes reales: app/api/routes/courses.py -> app/services/course_service.py
-> app/models/course.py (SQLAlchemy) -> PostgreSQL real. Se crea un curso via
HTTP real y se verifica su persistencia con una consulta SQL directa e
independiente de la propia API, para descartar que la API este devolviendo
un eco en memoria sin haber escrito realmente en la base de datos.
"""
import uuid

import requests

from tests.integration.conftest import BASE_URL, auth_header


def test_crear_curso_via_api_y_verificar_persistencia_directa_en_postgresql(docente_session, pg_conn):
    codigo = f"IT02-{uuid.uuid4().hex[:8].upper()}"
    payload = {"code": codigo, "name": "Curso de Integracion IT-02", "cycle": 1, "year": 2026}

    print(f"[IT-02] POST {BASE_URL}/api/courses payload={payload}")
    resp = requests.post(f"{BASE_URL}/api/courses", json=payload, headers=auth_header(docente_session), timeout=10)
    print(f"[IT-02] status={resp.status_code} body={resp.text[:300]}")
    assert resp.status_code in (200, 201), "app/services/course_service.create_course debio insertar el curso"
    curso = resp.json()
    curso_id = curso["id"]

    print(f"[IT-02] GET {BASE_URL}/api/courses/{curso_id} (lectura via API)")
    resp2 = requests.get(f"{BASE_URL}/api/courses/{curso_id}", headers=auth_header(docente_session), timeout=10)
    print(f"[IT-02] status={resp2.status_code} body={resp2.text[:300]}")
    assert resp2.status_code == 200
    assert resp2.json()["code"] == codigo

    print(f"[IT-02] SELECT directo a PostgreSQL (bypass total de la API) para confirmar persistencia real")
    with pg_conn.cursor() as cur:
        cur.execute("SELECT code, name, cycle FROM courses WHERE id = %s", (curso_id,))
        fila = cur.fetchone()
    print(f"[IT-02] fila real en PostgreSQL: {fila}")
    assert fila is not None, "El curso debe existir en la tabla courses independientemente de la API"
    assert fila[0] == codigo
