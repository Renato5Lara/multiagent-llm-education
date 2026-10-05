"""Secuencia DETERMINISTA de perfiles de la carga HTTP (Fase B.2): depende únicamente de `batch_seed`, del índice de trabajador (`worker_index`), del índice de usuario virtual y de la POSICIÓN de la petición.
No usa `id()`, memoria, marcas de tiempo, el orden de ejecución ni el sistema bajo prueba: la misma configuración produce exactamente la misma secuencia para `swarm` y para `decision_table`.

Por usuario virtual `u` (trabajador `w`): `rng = Random(sha256(f"{batch_seed}|{w}|{u}"))`; en cada petición, en este orden FIJO y sea cual sea el sistema, se sortean (1) el índice de perfil y (2) la réplica (semilla del
enjambre; el convencional la ignora pero la sortea igual para no desalinear la secuencia). `loadtest/locustfile.py` usa estas mismas funciones; el plan de campaña registra el hash de la secuencia esperada.
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Sequence

ALGORITHM = "profile-sequence-v1"
REPLICATE_MAX = 10**6


def user_rng(batch_seed: int, worker_index: int, user_index: int) -> random.Random:
    digest = hashlib.sha256(f"{ALGORITHM}|{batch_seed}|{worker_index}|{user_index}".encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def next_request(rng: random.Random, n_profiles: int) -> tuple[int, int]:
    """(índice de perfil, réplica) de la siguiente petición del usuario. Orden de sorteo fijo."""
    if n_profiles < 1:
        raise ValueError("n_profiles >= 1")
    return rng.randrange(n_profiles), rng.randint(0, REPLICATE_MAX)


def user_sequence(batch_seed: int, worker_index: int, user_index: int, n_requests: int, profile_ids: Sequence[str]) -> list[tuple[str, int]]:
    """Las primeras `n_requests` peticiones (perfil, réplica) del usuario `user_index`."""
    rng = user_rng(batch_seed, worker_index, user_index)
    out = []
    for _ in range(n_requests):
        i, rep = next_request(rng, len(profile_ids))
        out.append((profile_ids[i], rep))
    return out


def expected_sequence(batch_seed: int, users: int, n_requests: int, profile_ids: Sequence[str], worker_index: int = 0) -> dict[int, list[tuple[str, int]]]:
    return {u: user_sequence(batch_seed, worker_index, u, n_requests, profile_ids) for u in range(users)}


def sequence_sha256(batch_seed: int, users: int, n_requests: int, profile_ids: Sequence[str], worker_index: int = 0) -> str:
    """Hash canónico de la secuencia esperada (registrado en el plan y en la provenance). Mismos argumentos ⇒ mismo hash; no depende del sistema."""
    seq = expected_sequence(batch_seed, users, n_requests, profile_ids, worker_index)
    payload = {"algorithm": ALGORITHM, "batch_seed": batch_seed, "worker_index": worker_index, "users": users, "n_requests": n_requests,
               "sequence": {str(u): [[p, r] for p, r in v] for u, v in sorted(seq.items())}}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def check_logged(logged: Sequence[dict], batch_seed: int, profile_ids: Sequence[str], worker_index: int = 0) -> dict:
    """Compara lo REGISTRADO por el generador (user_index, seq_pos, profile_id) con la secuencia esperada: `mismatches` debe ser 0. No supone nada: lo que no trae índice se cuenta como `unindexed`."""
    max_pos: dict[int, int] = {}
    for r in logged:
        if r.get("user_index") is not None and r.get("seq_pos") is not None:
            max_pos[r["user_index"]] = max(max_pos.get(r["user_index"], -1), r["seq_pos"])
    cache = {u: user_sequence(batch_seed, worker_index, u, m + 1, profile_ids) for u, m in max_pos.items()}
    checked = mismatches = unindexed = 0
    for r in logged:
        if r.get("user_index") is None or r.get("seq_pos") is None or not r.get("profile_id"):
            unindexed += 1
            continue
        checked += 1
        mismatches += cache[r["user_index"]][r["seq_pos"]][0] != r["profile_id"]
    return {"checked": checked, "mismatches": mismatches, "unindexed": unindexed}
