from pathlib import Path


def test_schema_file_exists() -> None:
    path = Path("schemas/plan.schema.json")
    assert path.exists()
    assert "plan_id" in path.read_text(encoding="utf-8")
