"""Shared full-game projections used by the computer players."""

from __future__ import annotations

from seed_duel.model import GameState, Phase
from seed_duel.rules import begin_turn, legal_actions, settle_round


WIN_VALUE = 10**9


def advance_round_for_search(state: GameState) -> GameState:
    """Settle a real round boundary and prepare the next round for search."""
    if state.phase is not Phase.ROUND_END:
        return state
    settled = state
    if state.terminal_reason != "settled":
        settled, _ = settle_round(state)
    if settled.phase is Phase.GAME_END:
        return settled
    next_round = settled.evolve(
        phase=Phase.SELECT,
        terminal_reason=None,
        round_number=settled.round_number + 1,
    )
    next_round, _ = begin_turn(next_round)
    return next_round


def strategic_value(
    state: GameState,
    root_player: int,
    *,
    project_settlement: bool = False,
) -> int:
    """Evaluate seeds plus the next-round territorial consequences.

    At a hand-empty Select state, ``project_settlement`` asks what ownership
    and reserves would look like if the round ended at that checkpoint. This
    is a heuristic projection, not a mutation of the live match.
    """
    evaluated = state
    if state.phase is Phase.ROUND_END:
        evaluated = advance_round_for_search(state)
    elif project_settlement and state.phase is Phase.SELECT and state.hand == 0:
        boundary = state.evolve(
            phase=Phase.ROUND_END,
            terminal_reason="search_projection",
            loop_resolution_available=False,
        )
        evaluated, _ = settle_round(boundary)

    if evaluated.phase is Phase.GAME_END:
        if evaluated.winner is None:
            return 0
        return WIN_VALUE if evaluated.winner == root_player else -WIN_VALUE

    opponent = 1 - root_player
    funds = [evaluated.captured[p] + evaluated.reserves[p] for p in (0, 1)]
    for index, seeds in enumerate(evaluated.pits):
        funds[evaluated.owner_of(index)] += seeds
    if evaluated.hand:
        funds[evaluated.player] += evaluated.hand

    territory = [sum(evaluated.owner_of(i) == p for i in range(len(evaluated.pits)))
                 for p in (0, 1)]
    invaded = [sum(
        evaluated.owner_of(i) == p and evaluated.original_owner_of(i) != p
        for i in range(len(evaluated.pits))
    ) for p in (0, 1)]
    protected = [sum(
        evaluated.owner_of(i) == p and evaluated.is_protected(i)
        for i in range(len(evaluated.pits))
    ) for p in (0, 1)]

    mobility = 0
    if evaluated.phase is Phase.SELECT:
        available = len(legal_actions(evaluated))
        mobility = available if evaluated.player == root_player else -available

    seed_balance = funds[root_player] - funds[opponent]
    territory_balance = territory[root_player] - territory[opponent]
    invasion_balance = invaded[root_player] - invaded[opponent]
    protected_balance = protected[root_player] - protected[opponent]
    reserve_balance = evaluated.reserves[root_player] - evaluated.reserves[opponent]
    return (
        seed_balance * 40
        + territory_balance * 600
        + invasion_balance * 900
        + protected_balance * 120
        + reserve_balance * 15
        + mobility * 8
    )
