from src.bot.templates import plan_text
from src.models.plan import Plan, PlanStatus, PolicySnapshot, RequestedBy, RiskLevel, RiskReport
from datetime import datetime, timedelta, timezone


def test_plan_template_is_summary_only() -> None:
    now = datetime.now(timezone.utc)
    plan = Plan(
        plan_id='pln_20260225abcdef',
        short_token='Abcd1234',
        status=PlanStatus.PENDING_APPROVAL,
        requested_by=RequestedBy(telegram_user_id=1, chat_id=1),
        request_text='x',
        created_at=now,
        expires_at=now + timedelta(minutes=30),
        policy_snapshot=PolicySnapshot(policy_id='pol_v1', allowed_path_prefixes=['docs/'], network_ops=False, shell_exec=False),
        ops=[{'op_id':'op_1','type':'read_file','path':'docs/a.md'}],
        risk=RiskReport(score=1, level=RiskLevel.LOW, reasons=[], blocked=False),
    )
    text = plan_text(plan)
    assert 'PENDING_APPROVAL' in text
    assert '/approve' in text
