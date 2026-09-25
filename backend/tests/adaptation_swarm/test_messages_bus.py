"""Contrato de mensajes (`swarm-msg-v1`, FIPA-ACL compatible) y bus REAL de Redis: serialización,
topología, idempotencia, persistencia en log y fallo explícito sin Redis."""

import asyncio
import uuid

import pytest
from pydantic import ValidationError

from adaptation_swarm.bus.redis_bus import RedisBus
from adaptation_swarm.schemas.errors import BusError
from adaptation_swarm.schemas.ids import content_id, derive_seed, package_id
from adaptation_swarm.schemas.messages import (
    SCHEMA_VERSION, AgentId, BusMessage, MessageType, Performative,
)


def msg(**kw):
    base = dict(correlation_id="corr-1", cycle_id="cyc-1", sender=AgentId.AG0, receiver=AgentId.AG1,
                message_type=MessageType.PROFILE_REQUEST, payload={"profile": {"a": 1}})
    base.update(kw)
    return BusMessage(**base)


def test_required_fields_and_json_roundtrip():
    m = msg()
    d = m.model_dump()
    for f in ("message_id", "correlation_id", "sender", "receiver", "message_type", "timestamp", "payload", "schema_version"):
        assert f in d and d[f] is not None
    assert d["schema_version"] == SCHEMA_VERSION == "swarm-msg-v1"
    back = BusMessage.from_json(m.to_json())
    assert back == m and back.performative is Performative.REQUEST


def test_fipa_performatives():
    assert msg().performative is Performative.REQUEST
    ready = msg(sender=AgentId.AG1, receiver=AgentId.AG0, message_type=MessageType.W_READY)
    assert ready.performative is Performative.INFORM
    err = msg(sender=AgentId.AG2, receiver=AgentId.AG0, message_type=MessageType.ERROR, status="error",
              error={"code": "X", "message": "y"})
    assert err.performative is Performative.FAILURE


@pytest.mark.parametrize("sender,receiver,mtype", [
    (AgentId.AG0, AgentId.AG1, MessageType.PROFILE_REQUEST), (AgentId.AG1, AgentId.AG0, MessageType.W_READY),
    (AgentId.AG0, AgentId.AG2, MessageType.CODE_REQUEST), (AgentId.AG2, AgentId.AG0, MessageType.CODE_READY),
    (AgentId.AG0, AgentId.AG3, MessageType.DIAGRAM_REQUEST), (AgentId.AG3, AgentId.AG0, MessageType.DIAGRAM_READY),
    (AgentId.AG0, AgentId.AG4, MessageType.TEXT_REQUEST), (AgentId.AG4, AgentId.AG0, MessageType.TEXT_READY),
    (AgentId.AG4, AgentId.AG0, MessageType.AUDIO_READY),
])
def test_allowed_topology(sender, receiver, mtype):
    assert msg(sender=sender, receiver=receiver, message_type=mtype).message_type is mtype


@pytest.mark.parametrize("kw", [
    dict(sender=AgentId.AG2, receiver=AgentId.AG1),                       # AG2 no puede pedirle a AG1
    dict(receiver=AgentId.AG3),                                            # PROFILE_REQUEST solo va a AG1
    dict(message_type=MessageType.ERROR, sender=AgentId.AG1, receiver=AgentId.AG2, status="error", error={"code": "e", "message": "m"}),
    dict(message_type=MessageType.ERROR, sender=AgentId.AG1, receiver=AgentId.AG0),   # ERROR sin `error`
    dict(schema_version="swarm-msg-v0"),
])
def test_invalid_messages_rejected(kw):
    with pytest.raises((ValidationError, ValueError)):
        msg(**kw)


def test_ids_are_deterministic_and_distinct():
    assert derive_seed(1, "p", 0) == derive_seed(1, "p", 0)
    assert len({derive_seed(1, "p", 0), derive_seed(2, "p", 0), derive_seed(1, "q", 0), derive_seed(1, "p", 1)}) == 4
    assert 0 <= derive_seed(1, "p", 0) < 2 ** 64
    assert content_id("c", "a", "code", "c0", "g") == content_id("c", "a", "code", "c0", "g")
    assert content_id("c", "a", "code", "c0", "g") != content_id("c", "a", "code", "c1", "g")
    assert package_id("cy", "a", "b", "c", "d") != package_id("cy", "a", "b", "c", "e")


async def test_redis_is_really_used_publish_read_ack(bus: RedisBus):
    await bus.ensure_group(AgentId.AG1)
    m = msg()
    await bus.publish(m)
    entries = await bus.read(AgentId.AG1, "c1", block_ms=500)
    assert len(entries) == 1 and entries[0][1].message_id == m.message_id
    assert await bus.redis.xlen(bus.stream_key(AgentId.AG1)) == 1        # el mensaje vive en un stream de Redis
    await bus.ack(AgentId.AG1, entries[0][0])
    assert (await bus.redis.xpending(bus.stream_key(AgentId.AG1), bus.group_name(AgentId.AG1)))["pending"] == 0
    assert await bus.read(AgentId.AG1, "c1", block_ms=50) == []


async def test_unacked_messages_are_redelivered_as_pending(bus: RedisBus):
    await bus.ensure_group(AgentId.AG2)
    m = msg(receiver=AgentId.AG2, message_type=MessageType.CODE_REQUEST, payload={"concept_id": "c", "variant": 0})
    await bus.publish(m)
    first = await bus.read(AgentId.AG2, "worker-a", block_ms=500)
    assert len(first) == 1                                               # entregado, no confirmado (crash simulado)
    again = await bus.read(AgentId.AG2, "worker-a", pending=True)
    assert [e[1].message_id for e in again] == [m.message_id]


async def test_idempotency_claim_and_release(bus: RedisBus):
    assert await bus.claim(AgentId.AG1, "m-1") is True
    assert await bus.claim(AgentId.AG1, "m-1") is False                  # duplicado
    assert await bus.claim(AgentId.AG2, "m-1") is True                   # otro agente: independiente
    await bus.release(AgentId.AG1, "m-1")
    assert await bus.claim(AgentId.AG1, "m-1") is True


async def test_publish_writes_cycle_log_and_shared_state(bus: RedisBus):
    await bus.ensure_group(AgentId.AG1)
    a = msg(cycle_id="cy-log")
    b = msg(cycle_id="cy-log", sender=AgentId.AG1, receiver=AgentId.AG0, message_type=MessageType.W_READY, in_reply_to=a.message_id)
    await bus.publish(a)
    await bus.publish(b)
    log = await bus.read_log("cy-log")
    assert [m.message_id for m in log] == [a.message_id, b.message_id]
    assert await bus.redis.ttl(bus.log_key("cy-log")) > 0
    await bus.set_state("cy-log", {"k": 3, "gbest_S": [1, 2], "status": "running"})
    assert await bus.get_state("cy-log") == {"k": 3, "gbest_S": [1, 2], "status": "running"}


async def test_consumer_groups_are_per_agent(bus: RedisBus):
    for a in (AgentId.AG1, AgentId.AG2):
        await bus.ensure_group(a)
    await bus.publish(msg())
    assert await bus.read(AgentId.AG2, "x", block_ms=50) == []          # AG2 no recibe lo de AG1
    assert len(await bus.read(AgentId.AG1, "x", block_ms=500)) == 1


async def test_bus_unavailable_raises_explicit_error():
    dead = RedisBus(url="redis://localhost:6390/0", prefix="swarm-test-dead:")
    with pytest.raises(BusError):
        await dead.connect()
    unconnected = RedisBus(prefix="swarm-test-x:")
    with pytest.raises(BusError):
        await unconnected.publish(msg())


async def test_purge_prefix_refuses_production_prefix():
    b = await RedisBus(prefix="swarm:").connect()
    try:
        with pytest.raises(BusError):
            await b.purge_prefix()
    finally:
        await b.close()
