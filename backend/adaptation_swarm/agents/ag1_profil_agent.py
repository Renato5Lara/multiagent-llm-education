"""AG1 — Profil-Agent (asesoría §3.3.1): parsea el perfil (RF01) y genera
W = [w_v, w_a, w_t, w_c] (RF02). Determinista: misma entrada → misma W.
"""

from __future__ import annotations

from adaptation_swarm.agents.base import SwarmAgent
from adaptation_swarm.profiles.models import ProfileRequest
from adaptation_swarm.profiles.w_mapping import RULE_VERSION, compute_weights, heuristic_start
from adaptation_swarm.schemas.errors import ProfileError
from adaptation_swarm.schemas.messages import AgentId, BusMessage, MessageType


class ProfilAgent(SwarmAgent):
    agent_id = AgentId.AG1

    def build_weights(self, raw_profile: dict) -> dict:
        try:
            profile = ProfileRequest.model_validate(raw_profile)
        except Exception as exc:
            raise ProfileError(f"perfil inválido (RF01): {exc}") from exc
        w = compute_weights(profile)
        return {
            "profile_id": profile.profile_id,
            "archetype": profile.archetype.value if profile.archetype else None,
            "difficulty": profile.difficulty.value if profile.difficulty else None,
            "concept_id": profile.concept_id,
            "W": {"w_v": w.w_v, "w_a": w.w_a, "w_t": w.w_t, "w_c": w.w_c},
            "W_list": w.as_list(),
            "heuristic_start": list(heuristic_start(w)),
            "generation": {
                "rule_version": RULE_VERSION, "agent": self.agent_id.value,
                "agent_version": self.version, "nivel": profile.nivel,
                "tasa_error_previa": profile.tasa_error_previa,
                "estilo": profile.estilo.model_dump(),
            },
        }

    async def handle(self, msg: BusMessage) -> list[BusMessage]:
        if msg.message_type is not MessageType.PROFILE_REQUEST:
            raise ProfileError(f"AG1 no maneja {msg.message_type.value}")
        return [self.reply(msg, MessageType.W_READY, self.build_weights(msg.payload["profile"]))]
