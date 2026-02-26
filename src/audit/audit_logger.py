"""JSONL audit logging with hash-chain."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.core.db import PlanStore


@dataclass(frozen=True)
class AuditEvent:
    ts: str
    event_id: str
    plan_id: str
    event_type: str
    status: str
    payload: dict[str, Any]
    prev_hash: str
    event_hash: str


class AuditLogger:
    def __init__(self, out_dir: Path, store: PlanStore) -> None:
        self._out_dir = out_dir
        self._out_dir.mkdir(parents=True, exist_ok=True)
        self._store = store

    def jsonl_path_for(self, plan_id: str) -> Path:
        return self._out_dir / f"{plan_id}.jsonl"

    def append(
        self,
        plan_id: str,
        event_type: str,
        status: str,
        payload: dict[str, Any],
        op_id: Optional[str] = None,
        op_type: Optional[str] = None,
        target_path: Optional[str] = None,
    ) -> AuditEvent:
        path = self.jsonl_path_for(plan_id)
        prev_hash = self._last_hash(path)
        ts = datetime.now(timezone.utc).isoformat()
        event_id = f"evt_{uuid.uuid4().hex}"

        canonical = {
            "ts": ts,
            "event_id": event_id,
            "plan_id": plan_id,
            "event_type": event_type,
            "status": status,
            "payload": payload,
            "prev_hash": prev_hash,
        }
        event_hash = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, ensure_ascii=True).encode("utf-8")
        ).hexdigest()

        event = AuditEvent(
            ts=ts,
            event_id=event_id,
            plan_id=plan_id,
            event_type=event_type,
            status=status,
            payload=payload,
            prev_hash=prev_hash,
            event_hash=event_hash,
        )

        line = {
            "ts": event.ts,
            "event_id": event.event_id,
            "plan_id": event.plan_id,
            "event_type": event.event_type,
            "status": event.status,
            "payload": event.payload,
            "prev_hash": event.prev_hash,
            "event_hash": event.event_hash,
        }
        with path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(line, ensure_ascii=True) + "\n")

        self._store.insert_event(
            event_id=event.event_id,
            plan_id=event.plan_id,
            event_type=event.event_type,
            status=event.status,
            payload_json=json.dumps(event.payload, ensure_ascii=True),
            prev_hash=event.prev_hash,
            event_hash=event.event_hash,
            op_id=op_id,
            op_type=op_type,
            target_path=target_path,
        )
        return event

    def last_hash_for(self, plan_id: str) -> str:
        return self._last_hash(self.jsonl_path_for(plan_id))

    @staticmethod
    def _last_hash(path: Path) -> str:
        if not path.exists():
            return "GENESIS"
        last: Optional[str] = None
        with path.open("r", encoding="utf-8") as fp:
            for line in fp:
                row = json.loads(line)
                last = row.get("event_hash")
        return last or "GENESIS"
