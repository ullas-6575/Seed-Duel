"""Round-aware Monte Carlo tree search advisor."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import log, sqrt
import random

from seed_duel.model import GameState, Phase
from seed_duel.rules import (
    apply_protected_choice,
    apply_select_pit,
    legal_actions,
)
from seed_duel.ai.strategy import advance_round_for_search, strategic_value


@dataclass(frozen=True, slots=True)
class MCTSRecommendation:
    pit_index: int
    visits: int
    win_rate: float
    iterations: int


@dataclass(frozen=True, slots=True)
class MCTSProtectedChoiceRecommendation:
    drop: bool
    visits: int
    win_rate: float
    iterations: int


@dataclass(slots=True)
class _Node:
    state: GameState
    parent: _Node | None = None
    action: int | bool | None = None
    visits: int = 0
    value: float = 0.0
    untried: list[int | bool] = field(default_factory=list)
    children: list[_Node] = field(default_factory=list)


def recommend_move(
    state: GameState,
    iterations: int = 1000,
    exploration: float = sqrt(2),
    rollout_limit: int = 100,
    seed: int | None = None,
    round_lookahead: int = 1,
) -> MCTSRecommendation | None:
    """Choose a legal pit using UCT and random complete-turn rollouts.

    ``win_rate`` is the estimated score fraction for the player at the root.
    A seed makes the randomized search repeatable.
    """
    if state.phase is not Phase.SELECT or not legal_actions(state):
        return None
    best = _recommend_action(
        state, iterations, exploration, rollout_limit, round_lookahead, seed
    )
    if best is None:
        return None
    action, node = best
    assert not isinstance(action, bool)
    return MCTSRecommendation(
        pit_index=action,
        visits=node.visits,
        win_rate=node.value / node.visits,
        iterations=iterations,
    )


def recommend_protected_choice(
    state: GameState,
    iterations: int = 1000,
    exploration: float = sqrt(2),
    rollout_limit: int = 100,
    seed: int | None = None,
    round_lookahead: int = 1,
) -> MCTSProtectedChoiceRecommendation | None:
    """Use MCTS to choose Drop or Skip at the current protected pit."""
    if state.phase is not Phase.DROP_SKIP:
        return None
    best = _recommend_action(
        state, iterations, exploration, rollout_limit, round_lookahead, seed
    )
    if best is None:
        return None
    action, node = best
    assert isinstance(action, bool)
    return MCTSProtectedChoiceRecommendation(
        drop=action,
        visits=node.visits,
        win_rate=node.value / node.visits,
        iterations=iterations,
    )


def _recommend_action(
    state: GameState,
    iterations: int,
    exploration: float,
    rollout_limit: int,
    round_lookahead: int,
    seed: int | None,
) -> tuple[int | bool, _Node] | None:
    actions = _available_actions(state)
    if not actions:
        return None
    if iterations < 1 or rollout_limit < 1:
        raise ValueError("iterations and rollout_limit must be at least 1")
    if exploration < 0:
        raise ValueError("exploration must be non-negative")
    if round_lookahead < 0:
        raise ValueError("round_lookahead cannot be negative")

    rng = random.Random(seed)
    root_player = state.player
    root = _Node(state=state, untried=list(actions))

    for _ in range(iterations):
        node = root

        while node.state.phase not in (Phase.ROUND_END, Phase.GAME_END) and not node.untried and node.children:
            node = _select_child(node, root_player, exploration)

        if node.state.phase not in (Phase.ROUND_END, Phase.GAME_END) and node.untried:
            action = rng.choice(node.untried)
            node.untried.remove(action)
            child_state = _apply_action(node.state, action)
            node = _Node(child_state, parent=node, action=action)
            node.untried = list(_available_actions(child_state))
            node.parent.children.append(node)

        reward = _rollout(
            node.state, root_player, rollout_limit, round_lookahead, rng
        )
        while node is not None:
            node.visits += 1
            node.value += reward
            node = node.parent

    best = max(root.children, key=lambda child: (child.visits, child.value / child.visits))
    assert best.action is not None
    return best.action, best


def _available_actions(state: GameState) -> tuple[int | bool, ...]:
    if state.phase is Phase.DROP_SKIP:
        return (True, False)
    if state.phase is Phase.SELECT:
        return legal_actions(state)
    return ()


def _apply_action(state: GameState, action: int | bool) -> GameState:
    if state.phase is Phase.DROP_SKIP:
        result, _ = apply_protected_choice(state, drop=bool(action))
    else:
        result, _ = apply_select_pit(state, int(action), auto_protected=False)
    return result


def _select_child(node: _Node, root_player: int, exploration: float) -> _Node:
    maximizing = node.state.player == root_player
    parent_log = log(node.visits)

    def score(child: _Node) -> float:
        mean = child.value / child.visits
        bonus = exploration * sqrt(parent_log / child.visits)
        return (mean if maximizing else -mean) + bonus

    return max(node.children, key=score)


def _rollout(
    state: GameState,
    root_player: int,
    limit: int,
    round_lookahead: int,
    rng: random.Random,
) -> float:
    position = state
    rounds_crossed = 0
    for _ in range(limit):
        if position.phase is Phase.GAME_END:
            return _score_fraction(position, root_player)
        if position.phase is Phase.ROUND_END:
            if rounds_crossed >= round_lookahead:
                return _score_fraction(position, root_player)
            position = advance_round_for_search(position)
            rounds_crossed += 1
            continue
        actions = _available_actions(position)
        if not actions:
            return _score_fraction(position, root_player)
        position = _apply_action(position, rng.choice(actions))
    return _score_fraction(position, root_player)


def _score_fraction(state: GameState, root_player: int) -> float:
    value = strategic_value(state, root_player, project_settlement=True)
    if value >= 10**8:
        return 1.0
    if value <= -(10**8):
        return 0.0
    return max(0.0, min(1.0, 0.5 + value / 40_000))
