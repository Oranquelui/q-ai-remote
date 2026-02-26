from pathlib import Path

from src.core.diff_service import DiffService


def test_diff_file_created(tmp_path: Path) -> None:
    svc = DiffService(tmp_path)
    art = svc.write_patch('pln_test', [('docs/a.txt', 'a\n', 'b\n')])
    assert art.path.exists()
    assert art.summary[0].rel_path == 'docs/a.txt'
