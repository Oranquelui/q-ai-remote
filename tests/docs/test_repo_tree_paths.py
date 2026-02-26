from pathlib import Path


def test_repo_tree_doc_exists() -> None:
    assert Path("docs/repo_tree.md").exists()
