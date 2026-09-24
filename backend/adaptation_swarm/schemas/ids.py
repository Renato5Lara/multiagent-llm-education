"""Identificadores, hashes y semilla determinista (DECISION-CLOSURE §5.1, §9.1)."""

from __future__ import annotations

import hashlib
import uuid


def new_id() -> str:
    return str(uuid.uuid4())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def derive_seed(batch_seed: int, profile_id: str, replicate: int) -> int:
    """`seed = f(batch_seed, profile_id, replicate)` — determinista, 64 bits."""
    digest = hashlib.sha256(f"{batch_seed}|{profile_id}|{replicate}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def content_id(
    concept_id: str, anchor_version: str, modality: str, variant_key: str, generator_version: str
) -> str:
    """`sha256(concept_id ‖ anchor_version ‖ modalidad ‖ variante ‖ generator_version)`."""
    return sha256_text("‖".join((concept_id, anchor_version, modality, variant_key, generator_version)))


def package_id(cycle_id: str, code_sha: str, diagram_sha: str, text_sha: str, audio_sha: str) -> str:
    return sha256_text("‖".join((cycle_id, code_sha, diagram_sha, text_sha, audio_sha)))
