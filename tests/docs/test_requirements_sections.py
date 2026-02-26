from pathlib import Path


def test_requirements_sections_exist() -> None:
    path = Path("docs/mvp_requirements.md")
    text = path.read_text(encoding="utf-8")
    for key in ["Purpose", "Non-goals", "User Flow", "Prohibitions", "Acceptance Criteria"]:
        assert key in text
