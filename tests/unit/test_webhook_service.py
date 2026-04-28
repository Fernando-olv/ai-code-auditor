from app.services.webhook_service import pull_request_action_triggers_analysis


def test_pull_request_action_triggers_analysis_core_actions() -> None:
    assert pull_request_action_triggers_analysis("opened") is True
    assert pull_request_action_triggers_analysis("synchronize") is True
    assert pull_request_action_triggers_analysis("reopened") is True


def test_pull_request_action_triggers_analysis_ignores_noise() -> None:
    assert pull_request_action_triggers_analysis("labeled") is False
    assert pull_request_action_triggers_analysis("edited") is False
    assert pull_request_action_triggers_analysis("closed") is False
