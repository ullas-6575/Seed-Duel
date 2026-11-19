"""Round-1 minimax advisor with alpha-beta pruning.

The advisor uses the same pure engine transition as the UI. It never changes
the live state; it only evaluates copies returned by ``apply_select_pit``.
"""

from __future__ import annotations

from dataclasses import dataclass

from seed_duel.model import GameState, Phase
from seed_duel.rules import (
    apply_protected_choice,
    apply_select_pit,
    legal_actions,
    round_earnings,
)


@dataclass(frozen=True, slots=True)
class Recommendation:
    pit_index: int
    score: int
    depth: int
    nodes: int


@dataclass(frozen=True, slots=True)
class ProtectedChoiceRecommendation:
    drop: bool
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
    nodes = [0]
    best_pit = actions[0]
    best_score = -10**9
    alpha, beta = -10**9, 10**9
    for move in actions:
        child, _ = apply_select_pit(state, move, auto_protected=False)
        remaining = max(0, depth - int(_turn_completed(state, child)))
        score = _search(child, remaining, 8, root_player, nodes, alpha, beta)
        if score > best_score:
            best_pit, best_score = move, score
        alpha = max(alpha, best_score)
    return Recommendation(best_pit, best_score, depth, nodes[0])


def recommend_protected_choice(
    state: GameState, depth: int = 3
) -> ProtectedChoiceRecommendation | None:
    """Search both Drop and Skip without changing players mid-turn.

    Depth still counts completed turns. A protected decision only consumes
    depth if its continuation actually completes the current turn.
    """
    if state.phase is not Phase.DROP_SKIP:
        return None
    if depth < 1:
        raise ValueError("depth must be at least 1")

    root_player = state.player
    nodes = [0]
    best_drop = True
    best_score = -10**9
    alpha, beta = -10**9, 10**9
    for drop in (True, False):
        child, _ = apply_protected_choice(state, drop=drop)
        remaining = max(0, depth - int(_turn_completed(state, child)))
        score = _search(child, remaining, 7, root_player, nodes, alpha, beta)
        if score > best_score:
            best_drop, best_score = drop, score
        alpha = max(alpha, best_score)
    return ProtectedChoiceRecommendation(best_drop, best_score, depth, nodes[0])


def _search(
    position: GameState,
    remaining: int,
    protected_remaining: int,
    root_player: int,
    nodes: list[int],
    alpha: int,
    beta: int,
) -> int:
    nodes[0] += 1
    if position.phase in (Phase.ROUND_END, Phase.GAME_END):
        return _terminal_value(position, root_player)
    # A pending protected choice belongs to the current turn and must be
    # resolved even when the completed-turn depth has reached zero.
    if ((remaining == 0 and position.phase is not Phase.DROP_SKIP)
            or protected_remaining == 0):
        return _heuristic_value(position, root_player)

    if position.phase is Phase.DROP_SKIP:
        actions: tuple[int | bool, ...] = (True, False)
    else:
        actions = legal_actions(position)
    if not actions:
        return _heuristic_value(position, root_player)

    maximizing = position.player == root_player
    value = -10**9 if maximizing else 10**9
    for action in actions:
        if position.phase is Phase.DROP_SKIP:
            child, _ = apply_protected_choice(position, drop=bool(action))
        else:
            child, _ = apply_select_pit(position, int(action), auto_protected=False)
        child_remaining = max(0, remaining - int(_turn_completed(position, child)))
        child_protected_remaining = (
            protected_remaining - 1
            if position.phase is Phase.DROP_SKIP
            else protected_remaining
        )
        child_value = _search(
            child,
            child_remaining,
            child_protected_remaining,
            root_player,
            nodes,
            alpha,
            beta,
        )
        if maximizing:
            value = max(value, child_value)
            alpha = max(alpha, value)
        else:
            value = min(value, child_value)
            beta = min(beta, value)
        if alpha >= beta:
            break
    return value


def _turn_completed(before: GameState, after: GameState) -> bool:
    return (
        after.phase in (Phase.ROUND_END, Phase.GAME_END)
        or (after.phase is Phase.SELECT and after.player != before.player)
    )


def _terminal_value(state: GameState, root_player: int) -> int:
    if state.winner is not None:
        return 10**9 if state.winner == root_player else -(10**9)
    if state.phase is Phase.GAME_END:
        return 0
    opponent = 1 - root_player
    scores = round_earnings(state)
    return (scores[root_player] - scores[opponent]) * 1000


def _heuristic_value(state: GameState, root_player: int) -> int:
    """A conservative nonterminal estimate from the root player's viewpoint."""
    opponent = 1 - root_player
    root_board = sum(seed for index, seed in enumerate(state.pits) if state.owner_of(index) == root_player)
    opponent_board = sum(seed for index, seed in enumerate(state.pits) if state.owner_of(index) == opponent)
    root_secured = state.captured[root_player] + state.reserves[root_player]
    opponent_secured = state.captured[opponent] + state.reserves[opponent]
    if state.player == root_player:
        root_secured += state.hand
    else:
        opponent_secured += state.hand
    captured_balance = root_secured - opponent_secured
    board_balance = root_board - opponent_board
    mobility_balance = len(legal_actions(state)) if state.player == root_player else -len(legal_actions(state))
    return captured_balance * 20 + board_balance * 2 + mobility_balance
