from pathlib import Path

import yaml


def test_policy_has_required_sections() -> None:
    path = Path('config/policy.yaml')
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    for key in ['instance', 'engine', 'telegram', 'users', 'rate_limit', 'plan', 'executor', 'risk', 'storage']:
        assert key in data
