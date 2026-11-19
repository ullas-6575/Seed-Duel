"""Seed Duel's headless rules engine."""

from .model import GameState, Phase
from .rules import (
    apply_protected_choice, apply_select_pit, begin_turn,
    end_round_after_later_cycle, initial_state, legal_actions, settle_round,
)

__all__ = [
    "GameState",
    "Phase",
    "apply_select_pit",
    "apply_protected_choice",
    "begin_turn",
    "end_round_after_later_cycle",
    "initial_state",
    "legal_actions",
    "settle_round",
]
