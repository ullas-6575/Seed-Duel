"""Round-1 minimax advisor with alpha-beta pruning.

The advisor uses the same pure engine transition as the UI. It never changes
the live state; it only evaluates copies returned by ``apply_select_pit``.
"""

from __future__ import annotations

from dataclasses import dataclass

from seed_duel.model import GameState, Phase
from seed_duel.rules import apply_select_pit, legal_actions, settle_round


@dataclass(frozen=True, slots=True)
class Recommendation:
    pit_index: int
    score: int
    depth: int
    nodes: int


def recommend_move(state: GameState, depth: int = 3) -> Recommendation | None:
    """Return the strongest legal starting pit for the player whose turn it is.

    Depth counts complete turns, not individual seed drops. Ties retain the
    first pit in ring order, so the recommendation is deterministic.
    """
    actions = legal_actions(state)
    if not actions:
        return None
    if depth < 1:
        raise ValueError("depth must be at least 1")

    root_player = state.player
    nodes = 0

    def search(position: GameState, remaining: int, alpha: int, beta: int) -> int:
        nonlocal nodes
        nodes += 1
        if position.phase is Phase.ROUND_END:
            settled, _ = settle_round(position)
            return _terminal_value(settled, root_player)
        if remaining == 0:
            return _heuristic_value(position, root_player)

        moves = legal_actions(position)
        if not moves:
            return _heuristic_value(position, root_player)

        maximizing = position.player == root_player
        if maximizing:
            value = -10**9
            for move in moves:
                child, _ = apply_select_pit(position, move)
                value = max(value, search(child, remaining - 1, alpha, beta))
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value

        value = 10**9
        for move in moves:
            child, _ = apply_select_pit(position, move)
            value = min(value, search(child, remaining - 1, alpha, beta))
            beta = min(beta, value)
            if alpha >= beta:
                break
        return value

    best_pit = actions[0]
    best_score = -10**9
    alpha, beta = -10**9, 10**9
    for move in actions:
        child, _ = apply_select_pit(state, move)
        score = search(child, depth - 1, alpha, beta)
        if score > best_score:
            best_pit, best_score = move, score
        alpha = max(alpha, best_score)
    return Recommendation(best_pit, best_score, depth, nodes)


def _terminal_value(state: GameState, root_player: int) -> int:
    opponent = 1 - root_player
    return (state.captured[root_player] - state.captured[opponent]) * 1000


def _heuristic_value(state: GameState, root_player: int) -> int:
    """A conservative nonterminal estimate from the root player's viewpoint."""
    opponent = 1 - root_player
    root_board = sum(seed for index, seed in enumerate(state.pits) if state.owner_of(index) == root_player)
    opponent_board = sum(seed for index, seed in enumerate(state.pits) if state.owner_of(index) == opponent)
    captured_balance = state.captured[root_player] - state.captured[opponent]
    board_balance = root_board - opponent_board
    mobility_balance = len(legal_actions(state)) if state.player == root_player else -len(legal_actions(state))
    return captured_balance * 20 + board_balance * 2 + mobility_balance
