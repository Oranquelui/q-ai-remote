import pytest

from src.security.rate_limit import LimitPolicy, RateLimitExceeded, RateLimiter


def test_rate_limit_blocks_over_threshold() -> None:
    rl = RateLimiter()
    policy = LimitPolicy(max_events=1, window_sec=60)
    rl.check(user_id=1, channel='plan', policy=policy)
    with pytest.raises(RateLimitExceeded):
        rl.check(user_id=1, channel='plan', policy=policy)
