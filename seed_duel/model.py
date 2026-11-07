"""Immutable data structures shared by the rules engine, UI, and future AI."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class Phase(str, Enum):
    SELECT = "select"
    ROUND_END = "round_end"


@dataclass(frozen=True, slots=True)
class Event:
    """A rule event suitable for replay, tests, or future Pygame animation."""

    kind: str
    data: tuple[tuple[str, int | str], ...] = ()

    @classmethod
    def create(cls, kind: str, **data: int | str) -> "Event":
        return cls(kind, tuple(data.items()))


@dataclass(frozen=True, slots=True)
class GameState:
    pits: tuple[int, ...]
    player: int = 0
    phase: Phase = Phase.SELECT
    captured: tuple[int, int] = (0, 0)
    reserves: tuple[int, int] = (0, 0)
    hand: int = 0
    cursor: int | None = None  # Last pit visited; next pit is cursor + 1.
    initial_total: int = 40
    round_number: int = 1
    terminal_reason: str | None = None

    def evolve(self, **changes: object) -> "GameState":
        return replace(self, **changes)

    @property
    def pit_count_per_player(self) -> int:
        return len(self.pits) // 2

    def owner_of(self, index: int) -> int:
        return 0 if index < self.pit_count_per_player else 1

    def seed_total(self) -> int:
        return sum(self.pits) + self.hand + sum(self.captured) + sum(self.reserves)

    def assert_conserved(self) -> None:
        if self.seed_total() != self.initial_total:
            raise AssertionError(
                f"Seed conservation failed: {self.seed_total()} != {self.initial_total}"
            )
        if any(value < 0 for value in (*self.pits, *self.captured, *self.reserves, self.hand)):
            raise AssertionError("Seed counts cannot be negative")
