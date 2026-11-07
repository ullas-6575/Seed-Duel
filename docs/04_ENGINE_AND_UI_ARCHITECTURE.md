# Seed Duel: engine and Pygame architecture

The architecture below is a proposed implementation contract. Module names and commands are targets to create, not claims about existing source files.

## 1. Suggested repository layout

| Path | Responsibility |
| --- | --- |
| `seed_duel/model.py` | State, configuration, actions and events |
| `seed_duel/rules.py` | Legal actions and pure single-step transitions |
| `seed_duel/rounds.py` | Settlement and confirmed redistribution policy |
| `seed_duel/cycles.py` | Checkpoint keys and cycle analysis |
| `seed_duel/ai/` | Random, heuristic, minimax, optional fuzzy/MCTS |
| `seed_duel/ui/` | Board rendering, input, event playback, result screens |
| `seed_duel/runner.py` | Headless matches, budgets and logs |
| `seed_duel/__main__.py` | App entry point |
| `tests/` and `tests/fixtures/` | Unit, integration and replay cases |
| `docs/` | These six guides |
| `results/` | Versioned experiment summaries and reproducible configuration |

Keep generated caches and virtual environments out of Git. Keep useful fixtures and compact benchmark evidence in Git.

## 2. State model

| Field | Meaning |
| --- | --- |
| `pits: tuple[int, ...]` | Ordered board counts |
| `original_owner` | Fixed physical side for each pit |
| `owner` | Current owner for settlement and conquest |
| `protected` | Whether each pit is unavailable for pickup/capture |
| `player` | Player currently acting |
| `phase` | Select, pickup, sow, drop/skip choice, inspect, capture, turn end, round end, setup, game end |
| `cursor` | Document whether it means last visited or next destination in each phase |
| `hand` | Seeds held during sowing |
| `captured` | Seeds held in each player's current round capture account |
| `reserves` | Seeds outside active board play |
| `round_number` | Current round |
| `initial_total` | Conservation target |
| `rule_version` | Rules/decisions used for this match |

Use immutable or safely copied search states. Do not share mutable pit lists between search branches. Keep elapsed animation time and screen coordinates out of rule state.

If setup uses an explicit `available_funds` account, zero the old live capture/reserve accounts when transferring into it and include available funds in the invariant. Never keep both as spendable balances.

## 3. Core interfaces

Use these as pseudocode signatures and agree exact return types together:

```python
legal_actions(state) -> tuple[Action, ...]
apply_action(state, action) -> Transition
advance_automatic(state) -> Transition
run_to_decision(state, budget) -> DecisionResult
settle_round(state) -> Transition
state_key(state) -> Hashable
```

`Transition` should contain the new state and an ordered event list. A `DecisionResult` distinguishes waiting for input, terminal, and computation-limit/unknown results. Illegal actions must leave the state unchanged and return a clear error.

Player actions include `SelectPit(index)`, `DropProtected` and `SkipProtected`. UI controls such as Pause, Next Step and Speed are playback controls, not game moves.

## 4. State-machine sequence

| Current phase | Action or check | Next phase |
| --- | --- | --- |
| Select | Own normal nonempty pit selected | Pickup |
| Pickup | Check repetition; transfer all seeds to hand | Sow |
| Sow | Advance to ordinary pit and drop one | Sow or inspect if hand empty |
| Sow | Next destination is protected | Wait for Drop/Skip |
| Drop/Skip | Drop spends one; Skip spends none | Continue sowing or inspect |
| Inspect | Pass protected pits; normal next pit nonempty | Pickup |
| Inspect | Normal next pit empty | Capture |
| Capture | Pass protected targets; apply confirmed D01 | Turn end |
| Turn end | Next player has a legal start | Select for next player |
| Turn end | Next player has no legal start | Round end |
| Round end | Transfer board by current owner once | Result or setup |
| Setup | Apply confirmed full-game policy; check victory | New round or game end |

A search expansion may process many automatic steps, but UI playback should retain the individual events. Guard every traversal against “no eligible normal pit” rather than spinning forever.

## 5. Events for animation and debugging

Suggested events: `PitSelected`, `SeedsPickedUp`, `SeedDropped`, `ProtectedPitEncountered`, `ProtectedPitSkipped`, `NextPitInspected`, `SeedsCaptured`, `TurnEnded`, `CycleDetected`, `RoundEnded`, `SeedsSettled`, `DonationApplied`, `ReserveUpdated`, `OwnershipChanged`, `GameWon`.

Each event carries the relevant indices and before/after counts. Associate it with a state snapshot or enough data to derive one deterministically. The event log is also the replay and test evidence.

Example ordinary-turn events: select display pit 1; pickup 4; drop in pits 2–5; inspect pit 6; pickup 4; drop in pits 7–10; inspect empty pit 1; capture pit 2; end turn.

## 6. UI behavior

- Keep the cream, dark brown and muted gold theme from the proposal.
- Display seeds, hand, captured accounts, reserves, player, round and current action.
- Mark protection with a lock/label as well as color. Ownership must be readable independently of the physical row.
- Highlight only legal starting pits. During sowing, disable unrelated board clicks.
- Pause at each protected-pit encounter for the acting human's Drop/Skip choice.
- In AI mode, display the selected decision before continuing playback.
- Offer Next Step, Auto, Pause, Speed, Restart and Exit.
- Use a distinct Round Result and Game Winner screen.
- Include a short on-screen explanation: “Next normal pit empty: capture, then turn ends.”

The UI consumes the same event stream whether stepping manually or auto-playing. Changing speed must never alter the final board or rules. Use a timer/event queue; do not block the entire Pygame loop with long sleeps.

## 7. Keeping the app responsive

Headless engine and AI modules must not import Pygame. For longer searches, use a bounded worker or incremental search task and keep event handling responsive. Pass an immutable snapshot to the worker. Attach a position/version token to results so an answer from before Restart cannot be applied to a new game.

Cancellation and timeout should return a legal fallback when a decision is required. They must not mutate the real board while searching.

## 8. Replay and reproducibility

Store configuration, rule version, RNG seed, initial complete state, player actions and terminal reason. On replay, reconstruct each event and verify the final state hash. Preserve the seed counts and ownership, not just screenshots.

Cycle history is part of the search context when it changes future outcomes. Do not reuse a cached result from an incompatible repetition history. Start without a transposition table if you have not solved that distinction.

## 9. Environment and run targets

Use one mutually agreed Python version that works on both machines. Create a virtual environment, install Pygame and a test framework, and record the tested dependencies in `requirements.txt`. Do not label untested versions as supported.

```bash
python -m venv .venv
# Activate .venv using your operating system's command.
python -m pip install -r requirements.txt
python -m pytest
python -m seed_duel
```

Create and document these entry points during implementation. Test installation from a clean checkout before submission. A packaged executable is optional unless the teacher requires it; a reliable source-based launch is the minimum.

## 10. Current implementation handoff

- `seed_duel/rules.py` owns all currently implemented Round-1 logic. Do not duplicate sowing, relay, capture or settlement in the UI.
- `seed_duel/ui/app.py` renders `GameState`, calls `apply_select_pit(state, index)` after a board click, and displays the returned event list.
- Run the visual application with `python main.py`; run the headless engine demo with `python -m seed_duel`; run tests with `python -m unittest discover -v`.
- The UI currently applies a complete deterministic turn immediately and shows its events in the status panel. Timed, one-event-at-a-time animation is a later M2 task.
