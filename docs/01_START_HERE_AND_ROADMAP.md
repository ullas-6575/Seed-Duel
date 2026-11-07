# Seed Duel: start here and finish the project

Course: Artificial Intelligence Laboratory, CSE 3210  
Team: Md Feroz Shah (2207087) and Ullas Biswas Shontu (2207086)  
Guide date: 28 October 2026  
Status: implementation guidance based on our discussion; no claim that the game has been built.

## What you are building

A local Python/Pygame strategy game for two players. Players sow seeds around a ring of pits, continue through relay pickups, and capture seeds. Rounds redistribute earnings into playable pits and reserves. In the full game, unfilled territory can become conquered territory, with protected seeds and an independent Drop/Skip choice on every encounter. The full-game goal is conquering all original opponent pits.

A **turn**, a **round**, and the **whole game** are different units. Build that distinction into every screen, function and explanation.

## Read these six files together

| File | What it controls |
| --- | --- |
| [02_RULES_AND_DECISIONS.md](02_RULES_AND_DECISIONS.md) | Confirmed rules, provisional rules, examples, decisions to settle |
| [03_TEAM_WORKFLOW.md](03_TEAM_WORKFLOW.md) | Who does what, integration and review |
| [04_ENGINE_AND_UI_ARCHITECTURE.md](04_ENGINE_AND_UI_ARCHITECTURE.md) | State, events, interfaces and animation |
| [05_AI_IMPLEMENTATION_AND_EXPERIMENTS.md](05_AI_IMPLEMENTATION_AND_EXPERIMENTS.md) | Baselines, search agents and fair evaluation |
| [06_TESTING_DEMO_AND_SUBMISSION.md](06_TESTING_DEMO_AND_SUBMISSION.md) | Exact fixtures, release checks, report and viva |

These are working documents. Update the rule decisions before changing the engine, then update the related tests. A slide or visual example is not an additional game rule.

## Two delivery levels

### Core submission: one complete round

- Configurable pit count and seeds per pit; default 5 pits per player and 4 seeds per pit.
- Correct sowing, relay pickup, capture and round settlement.
- Deterministic cycle detection that cannot freeze the program.
- Human vs Human and Human vs AI with a baseline and one search agent.
- A headless AI vs AI runner for reproducible experiments.
- Board animation, score display, clear turn/round messages, restart and result screen.
- Meaningful tests and a documented installation/demo procedure.

One-round winner-by-final-seed-total and equal-total draw are proposed standalone scoring conventions. Confirm them before freezing this mode.

### Full-game extension

- Reserves and redistribution between rounds.
- Ownership distinct from physical row.
- Protected conquered pits, independent Drop/Skip actions, correct owner settlement.
- Whole-game victory and later-round cycle handling.
- The same three player modes, with AI able to make mid-turn choices.

The general later-round redistribution and reclamation rules are not yet complete. Keep the core playable while you resolve them. Do not advertise an end-to-end full-game implementation until those decisions and tests exist.

## Milestone plan

This is a suggested sequence, not an assumed deadline. One work session can be about 2–3 focused hours. Adjust estimates after the first two sessions.

| Milestone | Suggested sessions | Exit evidence |
| --- | --- | --- |
| M0: agree rules and interfaces | 1–2 | Core decisions recorded; state/action contract agreed |
| M1: headless first-round engine | 3–4 | Exact ordinary-turn and 40-batch loop fixtures pass |
| M2: playable board | 3–4, partly alongside M1 | Two people complete a round; step and auto animation agree |
| M3: baseline and minimax | 3–4 | AI always returns legal actions; timing and match logs saved |
| M4: core release | 2 | Clean-machine demo and submission checklist pass |
| M5: ownership and round transition | 3–5 | Full-game decisions settled; transition and reserve fixtures pass |
| M6: mid-turn decisions and cycle policy | 3–5 | Drop/Skip and 28-batch avoidable-loop fixtures pass |
| M7: full-game release | 2–3 | Complete match, evaluation, report and rehearsal |
| Optional: MCTS/fuzzy enhancements | After stable core | Measured benefit or a documented comparison |

Both people work during each milestone; the estimates are elapsed work sessions, not per-person promises.

## First session checklist

- [ ] Read file 02 together and resolve core-blocking decisions.
- [ ] Agree who starts as engine lead and UI lead; use file 03's suggested split.
- [ ] Create one shared Git repository and a small issue board.
- [ ] Agree 0-based engine indices and 1-based displayed labels.
- [ ] Create the package skeleton from file 04.
- [ ] Implement initial state creation and the seed conservation assertion.
- [ ] Encode the ordinary-turn fixture from file 06 before adding graphics.
- [ ] Finish with a runnable command and a written next task for each person.

## Keep scope under control

If the schedule becomes tight, finish M4 and present the full-game work honestly as an extension. Cut optional effects, sounds and extra algorithms before cutting correctness, a runnable demo or evaluation. A working minimax agent is a stronger submission than three unfinished AI labels.

Do not start networking, accounts, online multiplayer, mobile packaging or a database for this lab project unless the teacher explicitly requires them.

## Status board to maintain

| Milestone | Status | Owner | Evidence / remaining blocker |
| --- | --- | --- | --- |
| M0 | Not assessed | Both | Fill after first meeting |
| M1–M4 | Not assessed | Both | Core implementation |
| M5–M7 | Not assessed | Both | Full-game implementation |

Allowed statuses: Not started, In progress, Blocked, In review, Done. Mark Done only when the milestone's exit evidence exists.
