from src.bot.templates import free_text_routed_text, policy_text, start_text


def test_start_template_contains_commands() -> None:
    assert '/start' in start_text()


def test_policy_template_mentions_approve_shape() -> None:
    assert '/approve <plan_id> <short_token>' in policy_text()


def test_free_text_routed_template_mentions_plan_flow() -> None:
    assert '/task' in free_text_routed_text()
