from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.core.approval_service import ApprovalService
from src.core.db import PlanStore
from src.models.plan import Plan, PlanStatus, PolicySnapshot, RequestedBy, RiskLevel, RiskReport


def _make_plan() -> Plan:
    now = datetime.now(timezone.utc)
    return Plan(
        plan_id='pln_20260225aabbcc',
        short_token='Abcd1234',
        status=PlanStatus.PENDING_APPROVAL,
        requested_by=RequestedBy(telegram_user_id=1, chat_id=1),
        request_text='test',
        created_at=now,
        expires_at=now + timedelta(minutes=5),
        policy_snapshot=PolicySnapshot(
            policy_id='pol_v1',
            allowed_path_prefixes=['docs/'],
            network_ops=False,
            shell_exec=False,
        ),
        ops=[{'op_id':'op_1','type':'read_file','path':'docs/a.md'}],
        risk=RiskReport(score=10, level=RiskLevel.LOW, reasons=[], blocked=False),
    )


def test_approve_success(tmp_path: Path) -> None:
    store = PlanStore(tmp_path / 'db.sqlite3')
    store.apply_schema(Path('db/schema.sql').read_text(encoding='utf-8'))
    svc = ApprovalService(store)
    plan = _make_plan()
    svc.create_pending_plan(plan)
    out = svc.approve(plan.plan_id, plan.short_token)
    assert out.status == 'APPROVED'
