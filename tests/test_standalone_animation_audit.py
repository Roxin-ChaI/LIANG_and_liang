from tools.audit_standalone_animation import unexpected_restart


def test_duplicate_running_restart_detector():
    events = [
        {"type": "renderer", "row": 7, "frame": 2},
        {"type": "state", "reason": "test-work"},
        {"type": "renderer", "row": 7, "frame": 0},
    ]
    assert unexpected_restart(events, after=1)
    assert not unexpected_restart(events, after=3)
