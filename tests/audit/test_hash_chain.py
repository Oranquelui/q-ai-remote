from pathlib import Path

from src.audit.audit_logger import AuditLogger
from src.core.db import PlanStore
from src.models.plan import Plan, PlanStatus, PolicySnapshot, RequestedBy, RiskLevel, RiskReport
from datetime import datetime, timedelta, timezone


def test_hash_chain_advances(tmp_path: Path) -> None:
    db = PlanStore(tmp_path / 'test.sqlite3')
    db.apply_schema(Path('db/schema.sql').read_text(encoding='utf-8'))
    now = datetime.now(timezone.utc)
    db.insert_plan(
        Plan(
            plan_id='pln_123456',
            short_token='Abcd1234',
            status=PlanStatus.PENDING_APPROVAL,
            requested_by=RequestedBy(telegram_user_id=1, chat_id=1),
            request_text='seed',
            created_at=now,
            expires_at=now + timedelta(minutes=10),
            policy_snapshot=PolicySnapshot(
                policy_id='pol_v1',
                allowed_path_prefixes=['docs/'],
                network_ops=False,
                shell_exec=False,
            ),
            ops=[{'op_id': 'op_1', 'type': 'read_file', 'path': 'docs/a.md'}],
            risk=RiskReport(score=1, level=RiskLevel.LOW, reasons=[], blocked=False),
        )
    )

    logger = AuditLogger(tmp_path / 'jsonl', db)
    e1 = logger.append('pln_123456', 'X', 'OK', {'n': 1})
    e2 = logger.append('pln_123456', 'Y', 'OK', {'n': 2})
    assert e2.prev_hash == e1.event_hash
