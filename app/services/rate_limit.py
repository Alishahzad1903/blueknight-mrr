from collections import defaultdict, deque
from time import monotonic

_buckets: dict[int, deque[float]] = defaultdict(deque)


def check_and_record(user_id: int, max_calls: int = 10, window_s: int = 60) -> float | None:
    """Return None if allowed, or retry-after seconds if rate-limited."""
    now = monotonic()
    bucket = _buckets[user_id]
    while bucket and bucket[0] <= now - window_s:
        bucket.popleft()
    if len(bucket) >= max_calls:
        return window_s - (now - bucket[0])
    bucket.append(now)
    return None
