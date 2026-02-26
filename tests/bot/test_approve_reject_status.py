from src.bot.templates import approved_text


def test_approved_template() -> None:
    t = approved_text('pln_x')
    assert 'APPROVED -> EXECUTING' in t
