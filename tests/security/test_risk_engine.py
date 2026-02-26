from pathlib import Path

from src.config.policy import load_policy
from src.models.plan import PlanOp
from src.security.risk_engine import RiskEngine


def test_risk_engine_scores_write_higher() -> None:
    policy = load_policy(Path("config/policy.yaml"))
    engine = RiskEngine(policy)
    read = engine.evaluate_ops([PlanOp(op_id='op_1', type='read_file', path='docs/a.txt')])
    write = engine.evaluate_ops([PlanOp(op_id='op_1', type='create_file', path='docs/a.txt', content='x')])
    assert write.score > read.score
