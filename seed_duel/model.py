"""Immutable data structures shared by the rules engine, UI, and future AI."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class Phase(str, Enum):
    SELECT = "select"
    DROP_SKIP = "drop_skip"
    ROUND_END = "round_end"
    GAME_END = "game_end"


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
    round_starter: int = 0
    terminal_reason: str | None = None
    winner: int | None = None
    seeds_per_pit: int = 4
    owners: tuple[int, ...] = ()
    protected: tuple[bool, ...] = ()
    pending_protected: int | None = None
    round_positions: tuple[tuple[object, ...], ...] = ()
    settled_positions: tuple[tuple[object, ...], ...] = ()
    turn_seen: tuple[tuple[object, ...], ...] = ()

    def evolve(self, **changes: object) -> "GameState":
        return replace(self, **changes)

    @property
    def pit_count_per_player(self) -> int:
        return len(self.pits) // 2

    def owner_of(self, index: int) -> int:
        if self.owners:
            return self.owners[index]
        return 0 if index < self.pit_count_per_player else 1

    def original_owner_of(self, index: int) -> int:
        return 0 if index < self.pit_count_per_player else 1

    def is_protected(self, index: int) -> bool:
        return bool(self.protected and self.protected[index])

    def seed_total(self) -> int:
        return sum(self.pits) + self.hand + sum(self.captured) + sum(self.reserves)

    def assert_conserved(self) -> None:
        if self.seed_total() != self.initial_total:
            raise AssertionError(
                f"Seed conservation failed: {self.seed_total()} != {self.initial_total}"
            )
        if any(value < 0 for value in (*self.pits, *self.captured, *self.reserves, self.hand)):
            raise AssertionError("Seed counts cannot be negative")
        if self.owners and (len(self.owners) != len(self.pits) or any(owner not in (0, 1) for owner in self.owners)):
            raise AssertionError("Each pit must have a valid owner")
        if self.protected and len(self.protected) != len(self.pits):
            raise AssertionError("Each pit must have a protected flag")
