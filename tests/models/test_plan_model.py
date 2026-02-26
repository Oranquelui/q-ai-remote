from datetime import datetime, timedelta, timezone

import pytest

from src.models.plan import Plan, PlanOp, PolicySnapshot, RequestedBy, RiskLevel, RiskReport


def _base_payload() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "plan_id": "pln_20260225abcd12",
        "short_token": "Abc12345",
        "requested_by": {"telegram_user_id": 1, "chat_id": 1},
        "request_text": "test",
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=10)).isoformat(),
        "policy_snapshot": {
            "policy_id": "pol_v1",
            "allowed_path_prefixes": ["docs/"],
            "network_ops": False,
            "shell_exec": False,
        },
        "ops": [
            {"op_id": "op_1", "type": "read_file", "path": "docs/README.md"},
        ],
        "risk": {
            "score": 10,
            "level": "LOW",
            "reasons": [],
            "blocked": False,
        },
    }


def test_plan_accepts_relative_path() -> None:
    Plan.model_validate(_base_payload())


def test_plan_rejects_absolute_path() -> None:
    payload = _base_payload()
    payload["ops"][0]["path"] = "/etc/passwd"
    with pytest.raises(Exception):
        Plan.model_validate(payload)


def test_plan_rejects_placeholder_path() -> None:
    payload = _base_payload()
    payload["ops"][0]["path"] = "docs/<generated_file>"
    with pytest.raises(Exception):
        Plan.model_validate(payload)
