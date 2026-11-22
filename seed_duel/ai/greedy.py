"""One-turn greedy opponent with a next-round settlement projection."""

from __future__ import annotations

from seed_duel.model import GameState, Phase
from seed_duel.rules import (
    apply_protected_choice,
    apply_select_pit,
    legal_actions,
)
from seed_duel.ai.strategy import strategic_value


def choose_move(state: GameState) -> int | None:
    """Choose the legal pit with the best immediate heuristic score.

    Ties keep the first pit in ring order, making this easy opponent deterministic.
    """
    actions = legal_actions(state)
    if not actions:
        return None

    root_player = state.player
    best_move = actions[0]
    best_score: int | None = None
    for move in actions:
        next_state, _ = apply_select_pit(state, move, auto_protected=False)
        score = _best_protected_route_value(next_state, root_player, 6)
        if best_score is None or score > best_score:
            best_move, best_score = move, score
    return best_move


def choose_protected_choice(state: GameState) -> bool | None:
    """Choose Drop (True) or Skip (False) at a protected-pit encounter.

    Greedy explores both continuations through the end of the current turn and
    keeps Drop on an exact tie so its behaviour remains deterministic.
    """
    if state.phase is not Phase.DROP_SKIP:
        return None

    root_player = state.player
    drop_state, _ = apply_protected_choice(state, drop=True)
    skip_state, _ = apply_protected_choice(state, drop=False)
    drop_value = _best_protected_route_value(drop_state, root_player, 5)
    skip_value = _best_protected_route_value(skip_state, root_player, 5)
    return drop_value >= skip_value


def _best_protected_route_value(
    state: GameState, player: int, remaining_choices: int
) -> int:
    """Look ahead through a bounded number of same-turn protected choices."""
    if state.phase is not Phase.DROP_SKIP or remaining_choices == 0:
        return _evaluate(state, player)
    drop_state, _ = apply_protected_choice(state, drop=True)
    skip_state, _ = apply_protected_choice(state, drop=False)
    return max(
        _best_protected_route_value(drop_state, player, remaining_choices - 1),
        _best_protected_route_value(skip_state, player, remaining_choices - 1),
    )


def _evaluate(state: GameState, player: int) -> int:
    return strategic_value(state, player, project_settlement=True)
