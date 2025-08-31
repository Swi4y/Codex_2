from dataclasses import dataclass, field
from typing import List


@dataclass
class Entry:
    id: int
    timestamp: str
    text: str
    threads: List[str] = field(default_factory=list)
