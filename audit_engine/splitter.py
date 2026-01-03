from __future__ import annotations

from dataclasses import dataclass
import math
from typing import List, Optional

from .models import SplitPolicy


@dataclass(frozen=True)
class SplitResult:
    parts: List[int]
    status: str


def split_amount(total: int, policy: SplitPolicy) -> SplitResult:
    if total <= 0:
        return SplitResult(parts=[], status="not_needed")

    for n_parts in policy.try_n_parts:
        parts = _try_split(total, n_parts, policy)
        if parts is not None:
            return SplitResult(parts=parts, status="ok")

    return SplitResult(parts=[], status="split_failed")


def _try_split(total: int, n_parts: int, policy: SplitPolicy) -> Optional[List[int]]:
    min_part = math.ceil(total * policy.min_pct)
    max_part = math.floor(total * policy.max_pct)
    if min_part <= 0 or max_part <= 0:
        return None

    def valid(part: int) -> bool:
        if policy.parts_must_be_positive and part <= 0:
            return False
        return min_part <= part <= max_part

    if n_parts == 3:
        for p1 in range(min_part, max_part + 1):
            for p2 in range(p1 + 1, max_part + 1):
                p3 = total - p1 - p2
                if p3 <= p2:
                    continue
                parts = [p1, p2, p3]
                if not valid(p3):
                    continue
                if policy.require_distinct and len(set(parts)) != 3:
                    continue
                if sum(parts) == total:
                    return parts
        return None

    if n_parts == 4:
        for p1 in range(min_part, max_part + 1):
            for p2 in range(p1 + 1, max_part + 1):
                for p3 in range(p2 + 1, max_part + 1):
                    p4 = total - p1 - p2 - p3
                    if p4 <= p3:
                        continue
                    parts = [p1, p2, p3, p4]
                    if not valid(p4):
                        continue
                    if policy.require_distinct and len(set(parts)) != 4:
                        continue
                    if sum(parts) == total:
                        return parts
        return None

    raise ValueError(f"Unsupported n_parts: {n_parts}")
