#!/usr/bin/env python3
"""Export deterministic JSON schema for the Plan model."""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.plan import Plan  # noqa: E402


def main() -> None:
    schema = Plan.model_json_schema()
    out_dir = ROOT / "schemas"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "plan.schema.json"
    out_path.write_text(
        json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
