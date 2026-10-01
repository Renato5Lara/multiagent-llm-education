"""Locust — pruebas de carga de `POST /api/adaptation` (asesoría §3.4.2/§4.3).

Escenarios de concurrencia fijados por la asesoría: 1, 10, 25, 50 y 100 usuarios simultáneos.
Definición de L_resp (DECISION-CLOSURE §9.2): envío de la petición HTTP → último byte del cuerpo JSON con
el paquete completo (4 piezas). Excluye la descarga del audio (GET separado). Sin think-time.

Entorno esperado:
    SWARM_API_KEY=<clave>  uvicorn app.main:app --port 8000        (Redis y Postgres en marcha)
Ejecución de un escenario (ver run_scenarios.sh):
    locust -f loadtest/locustfile.py --headless -u 25 -r 25 -t 60s --host http://localhost:8000 --csv out/u25
"""

import json
import os
import random
from pathlib import Path

from locust import HttpUser, constant, events, task

DATASET = Path(__file__).resolve().parents[2] / "datasets" / "synthetic_profiles" / "profiles-v1.jsonl"
PROFILES = [json.loads(l) for l in DATASET.read_text(encoding="utf-8").splitlines() if l.strip()]
KEY = os.environ.get("SWARM_API_KEY", "")
BATCH_SEED = int(os.environ.get("SWARM_LOAD_BATCH_SEED", "20260923"))
SYSTEM = os.environ.get("SWARM_LOAD_SYSTEM", "swarm")      # OE2: swarm (propuesta) | rules | bruteforce (sistemas convencionales, mismo servidor y mismo paquete)


class AdaptationUser(HttpUser):
    wait_time = constant(0)

    def on_start(self):
        self.rng = random.Random(BATCH_SEED + id(self) % 10_000)

    @task
    def adapt(self):
        profile = self.rng.choice(PROFILES)
        with self.client.post(
            f"/api/adaptation?batch_seed={BATCH_SEED}&replicate={self.rng.randint(0, 10**6)}" if SYSTEM == "swarm"
            else f"/api/adaptation/baseline/{SYSTEM}", json=profile,
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
