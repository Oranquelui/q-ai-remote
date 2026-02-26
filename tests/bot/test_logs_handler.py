from src.bot.templates import logs_text


def test_logs_template() -> None:
    text = logs_text('pln_x', 'EXECUTED', 'patch=1', 'a.jsonl', 'a.html')
    assert '実行ログ' in text
