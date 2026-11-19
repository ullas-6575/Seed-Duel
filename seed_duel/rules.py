"""Pure game rules for Seed Duel."""

from __future__ import annotations

from .model import Event, GameState, Phase


def initial_state(pits_per_player: int = 5, seeds_per_pit: int = 4) -> GameState:
    if pits_per_player <= 0 or seeds_per_pit < 0:
        raise ValueError("pits_per_player must be positive and seeds_per_pit non-negative")
    count = 2 * pits_per_player
    state = GameState(
        pits=(seeds_per_pit,) * count,
        initial_total=count * seeds_per_pit,
        owners=tuple(0 if i < pits_per_player else 1 for i in range(count)),
        protected=(False,) * count,
        seeds_per_pit=seeds_per_pit,
    )
    key = position_key(state)
    return state.evolve(round_positions=(key,), settled_positions=(key,))


def position_key(state: GameState) -> tuple[object, ...]:
    """Complete between-turn position; the round counter is intentionally excluded."""
    return (state.pits, state.owners, state.protected, state.captured, state.reserves,
            state.player, state.round_starter, state.seeds_per_pit)


def round_earnings(state: GameState) -> tuple[int, int]:
    funds = [state.captured[p] + state.reserves[p] for p in (0, 1)]
    for i, seeds in enumerate(state.pits):
        funds[state.owner_of(i)] += seeds
    return funds[0], funds[1]


def legal_actions(state: GameState) -> tuple[int, ...]:
    if state.phase is not Phase.SELECT:
        return ()
    return tuple(
        i for i, seeds in enumerate(state.pits)
        if state.owner_of(i) == state.player and not state.is_protected(i) and seeds > 0
    )


def _next_normal(state: GameState, index: int) -> int | None:
    for step in range(1, len(state.pits) + 1):
        candidate = (index + step) % len(state.pits)
        if not state.is_protected(candidate):
            return candidate
    return None


def _end_round(state: GameState, reason: str) -> tuple[GameState, tuple[Event, ...]]:
    result = state.evolve(
        phase=Phase.ROUND_END,
        terminal_reason=reason,
        hand=0,
        pending_protected=None,
        loop_resolution_available=False,
    )
    result.assert_conserved()
    return result, (Event.create("RoundEnded", reason=reason),)


def _end_later_round_turn_on_cycle(
    state: GameState,
    pits: tuple[int, ...],
    cursor: int,
) -> tuple[GameState, tuple[Event, ...]]:
    """End only the current turn when a later-round chosen path repeats."""
    player = state.player
    result = state.evolve(
        pits=pits,
        player=1 - player,
        phase=Phase.SELECT,
        hand=0,
        cursor=cursor,
        pending_protected=None,
        turn_seen=(),
        loop_resolution_available=True,
    )
    key = position_key(result)
    repeated_between_turns = key in state.round_positions
    result = result.evolve(round_positions=state.round_positions + (key,))
    events: list[Event] = [Event.create("CycleDetected", cursor=cursor, outcome="turn_ended")]

    if not any(pits):
        ended, end_events = _end_round(result, "empty_board")
        return ended, tuple(events + list(end_events))
    if repeated_between_turns:
        ended, end_events = _end_round(result, "repeated_position")
        return ended, tuple(events + [Event.create("PositionRepeated")] + list(end_events))
    if not legal_actions(result):
        ended, end_events = _end_round(result, "no_legal_start")
        return ended, tuple(events + list(end_events))

    result.assert_conserved()
    events.append(Event.create("TurnEnded", player=player, reason="chosen_path_repeat"))
    return result, tuple(events)


def begin_turn(state: GameState) -> tuple[GameState, tuple[Event, ...]]:
    if state.phase is not Phase.SELECT:
        return state, ()
    if any(state.pits):
        if legal_actions(state):
            return state, ()
        return _end_round(state, "no_legal_start")
    return _end_round(state, "empty_board")


def apply_select_pit(
    state: GameState, index: int, *, auto_protected: bool = True
) -> tuple[GameState, tuple[Event, ...]]:
    """Resolve until the turn ends or a protected choice needs an answer.

    ``auto_protected`` is a deterministic Drop shortcut for simple headless
    callers. Interactive play and AI search pass False and branch explicitly.
    """
    if index not in legal_actions(state):
        return state, (Event.create("IllegalAction", index=index),)
    started = state.evolve(
        cursor=index,
        hand=0,
        turn_seen=(),
        loop_resolution_available=False,
    )
    events = [Event.create("PitSelected", index=index, player=state.player)]
    return _continue_turn(started, events, auto_protected)


def apply_protected_choice(state: GameState, drop: bool) -> tuple[GameState, tuple[Event, ...]]:
    if state.phase is not Phase.DROP_SKIP or state.pending_protected is None:
        return state, (Event.create("IllegalAction", index=-1),)
    index = state.pending_protected
    pits = list(state.pits)
    hand, cursor = state.hand, index
    if drop:
        pits[index] += 1
        hand -= 1
        event = Event.create("ProtectedPitDropped", index=index, remaining_hand=hand)
    else:
        event = Event.create("ProtectedPitSkipped", index=index, remaining_hand=hand)
    updated = state.evolve(
        pits=tuple(pits), hand=hand, cursor=cursor, phase=Phase.SELECT,
        pending_protected=None, loop_resolution_available=False,
    )
    return _continue_turn(updated, [event], False, start_at_pickup=False)


def _continue_turn(
    state: GameState, events: list[Event], auto_protected: bool, *, start_at_pickup: bool = True
) -> tuple[GameState, tuple[Event, ...]]:
    pits = list(state.pits)
    cursor, hand, player = state.cursor, state.hand, state.player
    seen = set(state.turn_seen)
    pick_up = start_at_pickup
    while True:
        # A checkpoint is the complete hand-empty state immediately before pickup.
        if pick_up and hand == 0 and cursor is not None:
            key = (tuple(pits), state.owners, state.protected, state.captured,
                   state.reserves, player, cursor)
            if key in seen:
                repeated_pits = tuple(pits)
                if state.round_number > 1:
                    ended, end_events = _end_later_round_turn_on_cycle(
                        state, repeated_pits, cursor
                    )
                    return ended, tuple(events + list(end_events))
                ended, end_events = _end_round(
                    state.evolve(pits=repeated_pits, cursor=cursor),
                    "in_turn_repeat",
                )
                return ended, tuple(
                    events
                    + [Event.create("CycleDetected", cursor=cursor, outcome="round_ended")]
                    + list(end_events)
                )
            seen.add(key)
            hand = pits[cursor]
            pits[cursor] = 0
            events.append(Event.create("SeedsPickedUp", index=cursor, amount=hand))
        pick_up = False

        while hand:
            target = (cursor + 1) % len(pits)
            if state.is_protected(target):
                if auto_protected:
                    # Deterministic shortcut for callers that do not model choices.
                    pits[target] += 1
                    hand -= 1
                    cursor = target
                    events.append(Event.create("ProtectedPitDropped", index=target, remaining_hand=hand))
                    continue
                pending = state.evolve(
                    pits=tuple(pits), hand=hand, cursor=cursor, phase=Phase.DROP_SKIP,
                    pending_protected=target, turn_seen=tuple(seen),
                )
                events.append(Event.create("ProtectedPitEncountered", index=target, remaining_hand=hand))
                pending.assert_conserved()
                return pending, tuple(events)
            cursor = target
            pits[cursor] += 1
            hand -= 1
            events.append(Event.create("SeedDropped", index=cursor, remaining_hand=hand))

        inspect = _next_normal(state, cursor)
        if inspect is None:
            ended, end_events = _end_round(
                state.evolve(pits=tuple(pits), cursor=cursor, captured=state.captured), "no_normal_pits"
            )
            return ended, tuple(events + list(end_events))
        events.append(Event.create("NextPitInspected", index=inspect, count=pits[inspect]))
        if pits[inspect] > 0:
            cursor = inspect
            pick_up = True
            continue

        capture_index = _next_normal(state.evolve(pits=tuple(pits)), inspect)
        captured = list(state.captured)
        amount = pits[capture_index] if capture_index is not None else 0
        if capture_index is not None:
            pits[capture_index] = 0
        captured[player] += amount
        events.append(Event.create("SeedsCaptured", index=capture_index if capture_index is not None else -1,
                                   amount=amount, player=player))

        next_player = 1 - player
        result = state.evolve(
            pits=tuple(pits), captured=tuple(captured), hand=0, cursor=cursor,
            player=next_player, phase=Phase.SELECT, pending_protected=None,
            turn_seen=(),
            loop_resolution_available=False,
        )
        key = position_key(result)
        repeated = key in state.round_positions
        positions = state.round_positions + (key,)
        result = result.evolve(round_positions=positions)
        if not any(pits):
            result, end_events = _end_round(result, "empty_board")
        elif repeated:
            result, end_events = _end_round(result, "repeated_position")
            events.append(Event.create("PositionRepeated"))
        elif not legal_actions(result):
            result, end_events = _end_round(result, "no_legal_start")
        else:
            events.append(Event.create("TurnEnded", player=player))
            result.assert_conserved()
            return result, tuple(events)
        return result, tuple(events + list(end_events))


def settle_round(state: GameState) -> tuple[GameState, tuple[Event, ...]]:
    if state.phase is not Phase.ROUND_END:
        raise ValueError("Can only settle a round that has ended")

    funds = list(round_earnings(state))
    owners = list(state.owners or tuple(state.owner_of(i) for i in range(len(state.pits))))
    protected = list(state.protected or (False,) * len(state.pits))
    pits = [0] * len(state.pits)
    round_totals = tuple(funds)
    events: list[Event] = [Event.create("SeedsSettled", player1=round_totals[0], player2=round_totals[1])]

    # Original owners get the first chance to reclaim captured pits, at the usual fill cost.
    reclaimed: set[int] = set()
    for player in (0, 1):
        for i in range(len(pits)):
            if (state.original_owner_of(i) == player and owners[i] != player
                    and funds[player] >= state.seeds_per_pit):
                owners[i] = player
                protected[i] = False
                pits[i] = state.seeds_per_pit
                funds[player] -= state.seeds_per_pit
                reclaimed.add(i)
                events.append(Event.create("PitReclaimed", index=i, owner=player))

    previous_owners = tuple(owners)
    for player in (0, 1):
        for i in range(len(pits)):
            if previous_owners[i] != player or i in reclaimed:
                continue
            if funds[player] >= state.seeds_per_pit:
                pits[i] = state.seeds_per_pit
                funds[player] -= state.seeds_per_pit
            else:
                owners[i] = 1 - player
                protected[i] = owners[i] != state.original_owner_of(i)
                events.append(Event.create("OwnershipChanged", index=i, owner=owners[i]))
    next_player = 1 - state.round_starter
    settled = state.evolve(
        pits=tuple(pits), owners=tuple(owners), protected=tuple(protected),
        captured=(0, 0), reserves=tuple(funds), player=next_player,
        round_starter=next_player,
        phase=Phase.ROUND_END, terminal_reason="settled", pending_protected=None,
        round_positions=(), turn_seen=(),
        loop_resolution_available=False,
    )

    if owners and (all(owner == 0 for owner in owners) or all(owner == 1 for owner in owners)):
        winner = owners[0]
        settled = settled.evolve(phase=Phase.GAME_END, terminal_reason="conquest", winner=winner)
        events.append(Event.create("GameWon", player=winner))
    else:
        key = position_key(settled)
        if key in state.settled_positions:
            settled = settled.evolve(phase=Phase.GAME_END, terminal_reason="repeated_settlement", winner=None)
            events.append(Event.create("DrawDetected"))
        else:
            settled = settled.evolve(settled_positions=state.settled_positions + (key,), round_positions=(key,))
            can_move = [any(
                owners[i] == p and not protected[i] and pits[i] > 0
                for i in range(len(pits))
            ) for p in (0, 1)]
            if not any(can_move):
                territories = [owners.count(p) for p in (0, 1)]
                winner = 0 if territories[0] > territories[1] else 1 if territories[1] > territories[0] else None
                settled = settled.evolve(phase=Phase.GAME_END,
                                         terminal_reason="territory" if winner is not None else "territory_draw",
                                         winner=winner)
                events.append(Event.create("TerritoryResult", player=winner if winner is not None else "draw"))
    settled.assert_conserved()
    return settled, tuple(events)


def end_round_after_later_cycle(
    state: GameState,
) -> tuple[GameState, tuple[Event, ...]]:
    """Accept settlement after a human-visible later-round cycle prompt."""
    if (
        state.round_number <= 1
        or state.phase is not Phase.SELECT
        or not state.loop_resolution_available
    ):
        raise ValueError("No later-round cycle is available to settle")
    return _end_round(state, "later_loop_settled")
