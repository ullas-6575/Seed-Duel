"""Seed Duel's headless rules engine."""

from .model import GameState, Phase
from .rules import apply_select_pit, begin_turn, initial_state, legal_actions, settle_round

__all__ = [
    "GameState",
    "Phase",
    "apply_select_pit",
    "begin_turn",
    "initial_state",
    "legal_actions",
    "settle_round",
]
