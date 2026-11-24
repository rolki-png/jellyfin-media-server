"""Release custom-format score algebra for the Xbox Direct Play target.

accept iff sum(assigned scores) >= MIN_FORMAT_SCORE.
Every negative term in this policy is HARD_REJECT (-10000), so a single reject
cannot clear a floor of 0 unless bonuses sum to at least +10000.
"""

from __future__ import annotations

from typing import NamedTuple

from stack_policy.playback_compat import HARD_REJECT, MIN_FORMAT_SCORE


class ReleaseScore(NamedTuple):
    trash_ids: tuple[str, ...]
    total: int
    accepted: bool


def total_score(scores: list[int]) -> int:
    return sum(scores)


def is_accepted(scores: list[int], *, minimum: int = MIN_FORMAT_SCORE) -> bool:
    return total_score(scores) >= minimum


def score_release(scores: list[int], trash_ids: tuple[str, ...] = ()) -> ReleaseScore:
    total = total_score(scores)
    return ReleaseScore(trash_ids=trash_ids, total=total, accepted=total >= MIN_FORMAT_SCORE)


def hard_reject_cannot_clear_floor(
    scores: list[int], *, minimum: int = MIN_FORMAT_SCORE
) -> bool:
    """True when the stack is correctly rejected (any HARD_REJECT → not accepted)."""
    if HARD_REJECT not in scores:
        return True
    return not is_accepted(scores, minimum=minimum)


def require_floor_blocks_hard_reject_plus_bonus(minimum: int = MIN_FORMAT_SCORE) -> None:
    if minimum != 0:
        raise AssertionError(
            f"MIN_FORMAT_SCORE must be 0 so HARD_REJECT+bonus cannot clear; saw {minimum}"
        )
