"""Round-1 rules. These functions deliberately have no Pygame dependency."""

from __future__ import annotations

from dataclasses import replace

from .model import Event, GameState, Phase


def initial_state(pits_per_player: int = 5, seeds_per_pit: int = 4) -> GameState:
    if pits_per_player <= 0 or seeds_per_pit < 0:
        raise ValueError("pits_per_player must be positive and seeds_per_pit non-negative")
    total = 2 * pits_per_player * seeds_per_pit
    return GameState(pits=(seeds_per_pit,) * (2 * pits_per_player), initial_total=total)


def legal_actions(state: GameState) -> tuple[int, ...]:
    """Return legal starting-pit indices for the current player."""
    if state.phase is not Phase.SELECT:
        return ()
    start = state.player * state.pit_count_per_player
    end = start + state.pit_count_per_player
    return tuple(index for index in range(start, end) if state.pits[index] > 0)


def begin_turn(state: GameState) -> tuple[GameState, tuple[Event, ...]]:
    """Check whether the current player can begin a turn.

    Calling this at the start of a round or after a turn prevents the UI or an
    AI runner from silently skipping a player with no playable pits.
    """
    if state.phase is not Phase.SELECT or legal_actions(state):
        return state, ()
    result = state.evolve(phase=Phase.ROUND_END, terminal_reason="no_legal_start")
    return result, (Event.create("RoundEnded", reason="no_legal_start"),)


def apply_select_pit(state: GameState, index: int) -> tuple[GameState, tuple[Event, ...]]:
    """Resolve one complete deterministic Round-1 turn from a selected pit.

    The returned state waits for the opponent's selection, or is at a round end.
    An illegal selection leaves the state untouched and reports an error event.
    """
    if index not in legal_actions(state):
        return state, (Event.create("IllegalAction", index=index),)

    events: list[Event] = [Event.create("PitSelected", index=index, player=state.player)]
    pits = list(state.pits)
    captured = list(state.captured)
    player = state.player
    cursor = index
    hand = 0
    seen: set[tuple[tuple[int, ...], int]] = set()

    while True:
        checkpoint = (tuple(pits), cursor)
        if checkpoint in seen:
            result = state.evolve(
                pits=tuple(pits), hand=0, cursor=cursor, captured=tuple(captured),
                phase=Phase.ROUND_END, terminal_reason="cycle",
            )
            events.append(Event.create("CycleDetected", cursor=cursor))
            events.append(Event.create("RoundEnded", reason="cycle"))
            result.assert_conserved()
            return result, tuple(events)
        seen.add(checkpoint)

        hand = pits[cursor]
        pits[cursor] = 0
        events.append(Event.create("SeedsPickedUp", index=cursor, amount=hand))

        while hand:
            cursor = (cursor + 1) % len(pits)
            pits[cursor] += 1
            hand -= 1
            events.append(Event.create("SeedDropped", index=cursor, remaining_hand=hand))

        inspect = (cursor + 1) % len(pits)
        events.append(Event.create("NextPitInspected", index=inspect, count=pits[inspect]))
        if pits[inspect] > 0:
            cursor = inspect
            continue

        capture_index = (inspect + 1) % len(pits)
        amount = pits[capture_index]
        pits[capture_index] = 0
        captured[player] += amount
        events.append(Event.create("SeedsCaptured", index=capture_index, amount=amount, player=player))

        next_player = 1 - player
        result = state.evolve(
            pits=tuple(pits), captured=tuple(captured), hand=0, cursor=cursor,
            player=next_player, phase=Phase.SELECT,
        )
        if not legal_actions(result):
            result = result.evolve(phase=Phase.ROUND_END, terminal_reason="no_legal_start")
            events.append(Event.create("RoundEnded", reason="no_legal_start"))
        else:
            events.append(Event.create("TurnEnded", player=player))
        result.assert_conserved()
        return result, tuple(events)


def settle_round(state: GameState) -> tuple[GameState, tuple[Event, ...]]:
    """Move remaining pits to their physical owners exactly once at a round boundary."""
    if state.phase is not Phase.ROUND_END:
        raise ValueError("Can only settle a round that has ended")

    captured = list(state.captured)
    for index, seeds in enumerate(state.pits):
        captured[state.owner_of(index)] += seeds
    result = replace(
        state, pits=(0,) * len(state.pits), captured=tuple(captured), hand=0,
        terminal_reason="settled",
    )
    result.assert_conserved()
    return result, (Event.create("SeedsSettled"),)
