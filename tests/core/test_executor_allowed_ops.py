from src.models.plan import PlanOp


def test_allowed_ops_literal() -> None:
    PlanOp(op_id='op_1', type='list_dir', path='docs')
    PlanOp(op_id='op_2', type='read_file', path='docs/a.txt')
