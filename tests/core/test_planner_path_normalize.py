from src.core.planner import _normalize_rel_path


def test_normalize_rel_path_trims_trailing_slash() -> None:
    assert _normalize_rel_path("docs/") == "docs"
    assert _normalize_rel_path("docs/sub/") == "docs/sub"


def test_normalize_rel_path_rewrites_backslash() -> None:
    assert _normalize_rel_path(r"docs\\guide.md") == "docs/guide.md"
