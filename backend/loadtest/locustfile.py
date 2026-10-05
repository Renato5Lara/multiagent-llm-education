"""Locust — pruebas de carga de `POST /api/adaptation` (asesoría §3.4.2/§4.3).

Escenarios de concurrencia fijados por la asesoría: 1, 10, 25, 50 y 100 usuarios simultáneos.
Definición de L_resp (DECISION-CLOSURE §9.2): envío de la petición HTTP → último byte del cuerpo JSON con
el paquete completo (4 piezas). Excluye la descarga del audio (GET separado). Sin think-time.

Entorno esperado:
    SWARM_API_KEY=<clave>  uvicorn app.main:app --port 8000        (Redis y Postgres en marcha)
Ejecución de un escenario (ver run_scenarios.sh):
    locust -f loadtest/locustfile.py --headless -u 25 -r 25 -t 60s --host http://localhost:8000 --csv out/u25
"""

import hashlib
import json
import os
import random
from pathlib import Path

from locust import HttpUser, constant, events, task

DATASET = Path(__file__).resolve().parents[2] / "datasets" / "synthetic_profiles" / "profiles-v1.jsonl"
PROFILES = [json.loads(l) for l in DATASET.read_text(encoding="utf-8").splitlines() if l.strip()]
KEY = os.environ.get("SWARM_API_KEY", "")
BATCH_SEED = int(os.environ.get("SWARM_LOAD_BATCH_SEED", "20260923"))
SYSTEM = os.environ.get("SWARM_LOAD_SYSTEM", "swarm")      # OE2: swarm (propuesta) | decision_table (convencional independiente) | rules (ablación) | bruteforce (referencia); mismo servidor y mismo paquete
WORKER_INDEX = int(os.environ.get("SWARM_LOAD_WORKER_INDEX", "0"))


# SECUENCIA DETERMINISTA de perfiles (OE2, Fase B.2). Copia AUTOCONTENIDA (solo stdlib) de `adaptation_swarm/oe/profile_sequence.py`, que es la versión canónica; un test comprueba que ambas producen la misma secuencia.
# Depende solo de batch_seed, índice de trabajador, índice de usuario y posición de la petición: no usa id(), memoria ni marcas de tiempo, y NO depende del sistema bajo prueba.
SEQUENCE_ALGORITHM = "profile-sequence-v1"
REPLICATE_MAX = 10**6


def _user_rng(batch_seed, worker_index, user_index):
    digest = hashlib.sha256(f"{SEQUENCE_ALGORITHM}|{batch_seed}|{worker_index}|{user_index}".encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _next_request(rng, n_profiles):
    return rng.randrange(n_profiles), rng.randint(0, REPLICATE_MAX)       # orden de sorteo FIJO; el convencional ignora la réplica pero la sortea igual


class AdaptationUser(HttpUser):
    wait_time = constant(0)
    _created = 0                                  # índice de usuario virtual = orden de creación (Locust los crea en orden): determinista, a diferencia de id(self)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_index = AdaptationUser._created
        AdaptationUser._created += 1
        self.seq_pos = 0
        self.rng = _user_rng(BATCH_SEED, WORKER_INDEX, self.user_index)

    @task
    def adapt(self):
        i, replicate = _next_request(self.rng, len(PROFILES))
        profile = PROFILES[i]
        context = {"user_index": self.user_index, "seq_pos": self.seq_pos, "profile_id": profile.get("profile_id")}      # lo registra el log HTTP (secuencia verificable)
        self.seq_pos += 1
        with self.client.post(
            f"/api/adaptation?batch_seed={BATCH_SEED}&replicate={replicate}" if SYSTEM == "swarm"
            else f"/api/adaptation/baseline/{SYSTEM}", json=profile, context=context,
            headers={"X-Swarm-Key": KEY}, name="POST /api/adaptation", catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"HTTP {resp.status_code}")
                return
            pkg = resp.json().get("package") or {}
            if not (pkg.get("code", {}).get("source") and pkg.get("diagram", {}).get("mermaid")
                    and pkg.get("text", {}).get("text") and pkg.get("audio", {}).get("url")) or not pkg.get("chain_valid"):
                resp.failure("paquete multimodal incompleto")
            else:
                resp.success()
