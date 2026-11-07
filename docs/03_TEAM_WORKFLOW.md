# Seed Duel: two-person workflow

## Suggested initial ownership

This is a proposed division, not an assumption about either person's skills. Swap the leads if you prefer. Both people must understand the engine and AI before the viva.

| Area | Implementation lead | Reviewer / integration partner |
| --- | --- | --- |
| Rule state, sowing, capture, settlement | Feroz | Ullas |
| Pygame board, controls, animations | Ullas | Feroz |
| Core fixtures and invariants | Feroz | Ullas writes additional edge cases |
| Baseline and minimax | Feroz | Ullas verifies behavior and timing |
| Match runner and result summaries | Ullas | Feroz checks fairness and metrics |
| Ownership / reserve integration | Feroz | Ullas verifies visible accounting |
| Drop/Skip interaction and replay | Ullas | Feroz checks engine contract |
| Report, slides and viva | Both | Each reviews the other's explanation |

MCTS and fuzzy enhancements are optional. Assign them only after the core and benchmark runner work. Do not leave one teammate responsible only for formatting the report.

## Work in small vertical slices

One slice should include behavior, a test and visible or logged evidence. Example: “select pit 1, pick up 4 seeds, show hand = 4” is a better issue than “finish backend.”

Suggested early parallel work:

- Feroz implements `GameState`, legal actions and ordinary sowing against fixtures.
- Ullas builds a board renderer from fixture snapshots, without duplicating rule logic.
- Both agree event names and coordinate mapping before integrating.
- Replace fixtures with real events once the engine tests pass.

## Repository conventions

Keep the six guides under `docs/`. Use one repository, one protected-by-team-agreement main branch and short feature branches. A paid branch-protection feature is not required; the team can follow the same review discipline manually.

Examples: `engine/relay`, `ui/drop-skip`, `ai/minimax`, `tests/loop-fixtures`.

Before starting a task, pull the current main branch and create a branch. Avoid two people editing the same core module simultaneously. If that is necessary, agree the exact functions each owns.

Commit messages should name behavior: `Handle protected capture targets`, `Add fixed-seed paired matches`. Commit a runnable increment rather than unrelated changes.

## Definition of ready

An issue is ready when it has:

- A specific before/after behavior.
- The rule decision or requirement it implements.
- An owner and reviewer.
- A small acceptance example.
- Dependencies and whether it touches a shared interface.

## Definition of done

- The intended behavior runs.
- Relevant tests pass, including the conservation assertion for engine changes.
- The other person reviewed the change.
- The UI and headless engine agree where both are affected.
- No new unconfirmed rule was inserted.
- Documentation and a replay/demo fixture are updated when needed.
- The branch is integrated and main remains runnable.

## Integration agreement

Engine outputs state transitions and events; UI displays them. AI calls engine logic, not Pygame functions. Neither teammate implements a separate “simplified capture rule” in their module.

When an interface changes, update a tiny integration fixture immediately. Example: a `Drop` event contains pit index, before count, after count and remaining hand. Both authors review changes to this structure before building on it.

Use a short handoff note:

```text
Completed:
Branch / commit:
How to run or reproduce:
Tests / evidence:
Interface changes:
Known issue:
Next smallest task:
```

## End-of-session check-in: 10 minutes

1. Each shows something running or explains the exact blocker.
2. Check the milestone exit criteria in file 01.
3. Identify interface conflicts before the next session.
4. Assign one main task to each person.
5. Record new rule decisions in file 02.

For a bug, record a board and action sequence instead of only “capture is wrong.” Include rule version, player, hand, cursor, phase, owners, protected pits, captures and reserves.

## Using an AI coding assistant

Give it the relevant guides and a bounded issue. Suggested instruction:

> Read docs/02_RULES_AND_DECISIONS.md and docs/04_ENGINE_AND_UI_ARCHITECTURE.md. Implement only issue [ID]. Preserve the engine/UI boundary. Do not decide unresolved rules. Add the named acceptance fixture and run the relevant tests. Report changed behavior, verification and remaining limitations.

Review generated code together. Ask either teammate to explain why a test passes. Do not claim to understand or implement an algorithm solely because generated code runs.

## If one person gets blocked

The other continues independent work against the agreed interface. Pair on rule ambiguity and shared-engine bugs. After a lengthy unsuccessful debugging session, reduce the bug to the smallest board and replay instead of making many speculative changes.

## Shared submission responsibility

Each person should be able to install the project, run all modes, explain one full turn, distinguish the two loop examples, describe minimax and interpret the experiment table. Keep contribution notes based on actual commits and work, not the proposed split above.
