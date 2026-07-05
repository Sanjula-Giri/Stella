"""
LiveKit job entrypoint. One handler processes every inbound call regardless
of vertical — which business is being called is resolved from job metadata
(or a CLI flag for local prototyping) and loaded via config/schema.py.

Run locally for prototyping:
    python -m app.server --business config/businesses/clinic_example.yaml

In production, `--business` is replaced by reading the dialed number /
job metadata to pick the right config file per inbound call.
"""
from __future__ import annotations

import argparse
import os
import uuid

from dotenv import load_dotenv
from livekit.agents import AgentSession, JobContext, WorkerOptions, cli
from livekit.plugins import openai

from app.agent import Receptionist
from config.schema import load_business_config

load_dotenv()


async def handle_call(ctx: JobContext, business_config_path: str) -> None:
    cfg = load_business_config(business_config_path)
    call_id = str(uuid.uuid4())

    await ctx.connect()

    agent = Receptionist(cfg, call_id)

    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-realtime",
            api_key=os.environ["OPENAI_API_KEY"],
            voice=os.environ.get("STELLA_VOICE", "alloy"),
        ),
    )

    # Safety nets from the TRD: silence timeout + max call duration.
    session.on_silence_timeout(seconds=cfg.silence_timeout_seconds, action="prompt_then_transfer")
    session.on_max_duration(minutes=cfg.max_call_duration_minutes, action="wrap_up_and_end")

    await session.start(agent=agent, room=ctx.room)

    if cfg.recording.enabled:
        # Spoken consent preamble is already baked into build_system_prompt
        # via cfg.recording.consent_preamble if you want it read aloud;
        # actual recording start/stop against ctx.room is TODO — depends on
        # whether you're using LiveKit Egress or local capture.
        pass


def _entrypoint_factory(business_config_path: str):
    async def _entrypoint(ctx: JobContext) -> None:
        await handle_call(ctx, business_config_path)

    return _entrypoint


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--business",
        required=True,
        help="Path to a business YAML config, e.g. config/businesses/clinic_example.yaml",
    )
    args, remaining = parser.parse_known_args()

    cli.run_app(
        WorkerOptions(entrypoint_fnc=_entrypoint_factory(args.business)),
    )
