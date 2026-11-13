"""Monte Carlo tree search advisor for the deterministic Round-1 rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import log, sqrt
import random

from seed_duel.model import GameState, Phase
from seed_duel.rules import apply_select_pit, legal_actions, settle_round


@dataclass(frozen=True, slots=True)
class MCTSRecommendation:
    pit_index: int
    visits: int
    win_rate: float
    iterations: int


@dataclass(slots=True)
class _Node:
    state: GameState
    parent: _Node | None = None
    pit_index: int | None = None
    visits: int = 0
    value: float = 0.0
    untried: list[int] = field(default_factory=list)
    children: list[_Node] = field(default_factory=list)


def recommend_move(
    state: GameState,
    iterations: int = 1000,
    exploration: float = sqrt(2),
    rollout_limit: int = 100,
    seed: int | None = None,
) -> MCTSRecommendation | None:
    """Choose a legal pit using UCT and random complete-turn rollouts.

    ``win_rate`` is the estimated score fraction for the player at the root.
    A seed makes the randomized search repeatable.
    """
    actions = legal_actions(state)
    if not actions:
        return None
    if iterations < 1 or rollout_limit < 1:
        raise ValueError("iterations and rollout_limit must be at least 1")
    if exploration < 0:
        raise ValueError("exploration must be non-negative")

    rng = random.Random(seed)
    root_player = state.player
    root = _Node(state=state, untried=list(actions))

    for _ in range(iterations):
        node = root

        while node.state.phase is not Phase.ROUND_END and not node.untried and node.children:
            node = _select_child(node, root_player, exploration)

        if node.state.phase is not Phase.ROUND_END and node.untried:
            pit = rng.choice(node.untried)
            node.untried.remove(pit)
            child_state, _ = apply_select_pit(node.state, pit)
            node = _Node(child_state, parent=node, pit_index=pit)
            node.untried = list(legal_actions(child_state))
            node.parent.children.append(node)

        reward = _rollout(node.state, root_player, rollout_limit, rng)
        while node is not None:
            node.visits += 1
            node.value += reward
            node = node.parent

    best = max(root.children, key=lambda child: (child.visits, child.value / child.visits))
    return MCTSRecommendation(
        pit_index=best.pit_index,
        visits=best.visits,
        win_rate=best.value / best.visits,
        iterations=iterations,
    )


def _select_child(node: _Node, root_player: int, exploration: float) -> _Node:
    maximizing = node.state.player == root_player
    parent_log = log(node.visits)

    def score(child: _Node) -> float:
        mean = child.value / child.visits
        bonus = exploration * sqrt(parent_log / child.visits)
        return (mean if maximizing else -mean) + bonus

    return max(node.children, key=score)


def _rollout(state: GameState, root_player: int, limit: int, rng: random.Random) -> float:
    position = state
    # shortcut: score at the rollout limit; raise it if typical rounds exceed this depth.
    for _ in range(limit):
        if position.phase is Phase.ROUND_END:
            position, _ = settle_round(position)
            return _score_fraction(position, root_player)
        actions = legal_actions(position)
        if not actions:
            return _score_fraction(position, root_player)
        position, _ = apply_select_pit(position, rng.choice(actions))
    return _score_fraction(position, root_player)


def _score_fraction(state: GameState, root_player: int) -> float:
    if state.phase is Phase.ROUND_END:
        state, _ = settle_round(state)
    scores = list(state.captured)
    for index, seeds in enumerate(state.pits):
        scores[state.owner_of(index)] += seeds
    if state.initial_total == 0:
        return 0.5
    difference = scores[root_player] - scores[1 - root_player]
    return max(0.0, min(1.0, 0.5 + difference / (2 * state.initial_total)))
