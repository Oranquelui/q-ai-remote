from pathlib import Path

from src.core.db import PlanStore


def test_schema_apply(tmp_path: Path) -> None:
    db = PlanStore(tmp_path / "test.sqlite3")
    schema_sql = Path("db/schema.sql").read_text(encoding="utf-8")
    db.apply_schema(schema_sql)
    assert (tmp_path / "test.sqlite3").exists()
