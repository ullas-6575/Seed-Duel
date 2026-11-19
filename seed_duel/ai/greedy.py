"""One-turn greedy opponent for the Round-1 rules."""

from __future__ import annotations

from seed_duel.model import GameState, Phase
from seed_duel.rules import (
    apply_protected_choice,
    apply_select_pit,
    legal_actions,
    round_earnings,
)


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
    if state.phase is Phase.ROUND_END:
        scores = round_earnings(state)
        return (scores[player] - scores[1 - player]) * 1000

    own_board = sum(seeds for index, seeds in enumerate(state.pits) if state.owner_of(index) == player)
    other_board = sum(seeds for index, seeds in enumerate(state.pits) if state.owner_of(index) != player)
    own_secured = state.captured[player] + state.reserves[player]
    other_secured = state.captured[1 - player] + state.reserves[1 - player]
    if state.player == player:
        own_secured += state.hand
    else:
        other_secured += state.hand
    captured_balance = own_secured - other_secured
    board_balance = own_board - other_board
    mobility = len(legal_actions(state)) * (1 if state.player == player else -1)
    return captured_balance * 20 + board_balance * 2 + mobility
