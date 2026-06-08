from __future__ import annotations

import argparse
import os
import sys

import requests


def main() -> int:
    parser = argparse.ArgumentParser(description="Trigger a Level 1 swarm demonstration session.")
    parser.add_argument("--api", default=os.getenv("SWARM_DEMO_API", "http://localhost:8000"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    os.environ.setdefault("OLLAMA_NUM_PARALLEL", "1")
    os.environ.setdefault("OLLAMA_MAX_LOADED_MODELS", "1")

    try:
        response = requests.post(
            f"{args.api.rstrip('/')}/api/swarm/demo/run",
            json={"seed": args.seed},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"No pude iniciar la demo en {args.api}: {exc}", file=sys.stderr)
        print("Verifica que el backend FastAPI este corriendo en localhost:8000.", file=sys.stderr)
        return 1

    data = response.json()
    print("Swarm demo iniciada")
    print(f"session_id: {data['session_id']}")
    print(f"dashboard:  http://localhost:5173/swarm-demo?session={data['session_id']}")
    api = args.api.rstrip("/")
    print(f"sse:        {api}{data['events_url']}")
    print(f"replay:     {api}{data['replay_url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
