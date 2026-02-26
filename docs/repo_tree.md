# Repository Tree (MVP)

```text
.
├── .taskmaster/
│   ├── config.json
│   ├── docs/
│   │   └── prd.txt
│   └── tasks/
│       └── tasks.json
├── config/
│   └── policy.yaml
├── db/
│   └── schema.sql
├── docs/
│   ├── implementation_plan_10days.md
│   ├── mvp_requirements.md
│   ├── repo_tree.md
│   ├── security_test_items.md
│   └── telegram_templates.md
├── requirements.txt
├── schemas/
│   └── plan.schema.json
├── scripts/
│   └── export_plan_schema.py
├── src/
│   ├── main.py
│   ├── adapters/
│   │   └── codex_client.py
│   ├── audit/
│   │   ├── audit_logger.py
│   │   └── report_builder.py
│   ├── bot/
│   │   ├── handlers.py
│   │   └── templates.py
│   ├── core/
│   │   ├── approval_service.py
│   │   ├── db.py
│   │   ├── diff_service.py
│   │   ├── executor.py
│   │   ├── planner.py
│   │   └── runtime.py
│   ├── config/
│   │   ├── policy.py
│   │   └── secrets.py
│   ├── models/
│   │   └── plan.py
│   ├── secrets/
│   │   ├── base.py
│   │   ├── credman_store.py
│   │   ├── factory.py
│   │   └── keychain_store.py
│   └── security/
│       ├── path_guard.py
│       ├── rate_limit.py
│       └── risk_engine.py
└── tests/
    ├── audit/
    ├── bot/
    ├── config/
    ├── core/
    ├── db/
    ├── docs/
    ├── models/
    ├── schema/
    ├── secrets/
    └── security/
```

Notes:
- Runtime workspace paths in plans are always relative.
- `参考/` is read-only and not part of MVP runtime.
