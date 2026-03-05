"""Shared timeout helpers for Marlowe -> Move lowering."""

from __future__ import annotations

ABSOLUTE_TIME_MIN_SEC = 946684800  # 2000-01-01T00:00:00Z
ABSOLUTE_TIME_MIN_MS = ABSOLUTE_TIME_MIN_SEC * 1000


def normalize_timeout_to_ms(timeout: int) -> int:
    """Normalize Marlowe timeout into milliseconds.

    Accepts:
    - millisecond UNIX timestamps (13+ digits)
    - legacy second UNIX timestamps (10 digits), converted to ms
    """
    if not isinstance(timeout, int):
        raise ValueError(f"timeout must be integer, got: {type(timeout)}")

    if timeout >= ABSOLUTE_TIME_MIN_MS:
        return timeout

    if timeout >= ABSOLUTE_TIME_MIN_SEC:
        return timeout * 1000

    raise ValueError(f"timeout is not an absolute UNIX timestamp: {timeout}")

