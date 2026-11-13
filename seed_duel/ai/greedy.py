"""One-turn greedy opponent for the Round-1 rules."""

from __future__ import annotations

from seed_duel.model import GameState, Phase
from seed_duel.rules import apply_select_pit, legal_actions, settle_round


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
        next_state, _ = apply_select_pit(state, move)
        score = _evaluate(next_state, root_player)
        if best_score is None or score > best_score:
            best_move, best_score = move, score
    return best_move


def _evaluate(state: GameState, player: int) -> int:
    if state.phase is Phase.ROUND_END:
        state, _ = settle_round(state)
        return (state.captured[player] - state.captured[1 - player]) * 1000

    own_board = sum(seeds for index, seeds in enumerate(state.pits) if state.owner_of(index) == player)
    other_board = sum(seeds for index, seeds in enumerate(state.pits) if state.owner_of(index) != player)
    captured_balance = state.captured[player] - state.captured[1 - player]
    board_balance = own_board - other_board
    mobility = len(legal_actions(state)) * (1 if state.player == player else -1)
    return captured_balance * 20 + board_balance * 2 + mobility
