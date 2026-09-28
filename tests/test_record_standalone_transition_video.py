import pytest
from tools.record_standalone_transition_video import observed_gif_durations


def test_gif_pacing_uses_observed_intervals_not_uniform_transition_duration():
    assert observed_gif_durations([1000, 1043, 1102, 1226]) == [40, 60, 120, 100]


def test_bad_capture_order_cannot_be_reported_as_real_time_recording():
    for times in ([], [1], [1, 1], [3, 2]):
        with pytest.raises(ValueError):
            observed_gif_durations(times)
