# Seed Duel

Seed Duel is a local, turn-based strategy game built with Python and Pygame. Play against another person, challenge an AI opponent, or watch two AI agents play. The game combines seed sowing and capture with round-by-round pit ownership and settlement.

## Game modes

- **Human vs Human** — take turns on the same computer.
- **Human vs AI** — Player 1 is human; Player 2 is AI.
- **AI vs AI** — choose a matchup and watch both agents play. The first listed agent controls Player 1.

## How to play

The board starts with ten pits: five per player, four seeds per pit. Player 1 starts. On your turn, select a highlighted, non-empty pit you own, pick up all its seeds, and sow them one at a time around the board.

When your hand is empty, inspect the next normal pit, skipping protected pits. If it contains seeds, pick them up and continue sowing. If it is empty, capture the seeds in the next normal pit and end your turn. An empty capture target awards no seeds.

When sowing reaches a protected pit, choose **Drop** to put one seed into it, or **Skip** to pass it without using a seed. Each encounter is a new choice. Protected pits cannot be used as starting pits, picked up for relaying, or captured. All AI levels consider both choices automatically.

## Rounds, settlement, and winning

- A round ends when the board is empty, the next player has no legal starting pit, or a complete between-turn position repeats.
- If the same hand-empty checkpoint repeats during a turn in Round 1, the round ends. In later rounds, the turn ends. A human can try the opposite Drop/Skip choice at the last protected pit or end and settle the round; if the alternate choice repeats, the prompt appears again. The prompt compares the current settlement totals with the immediate projection from the alternate choice. AI agents evaluate Drop and Skip themselves. Repetition detection follows the path actually played; it does not prove that every alternate path loops.
- At settlement, each player pools their captures, reserve, and seeds in pits they own. Original owners first reclaim lost pits they can afford, at four seeds per pit in pit order. Then each player's remaining owned pits refill in pit order, also at four seeds each. An unfilled pit transfers to the other player; pits held by someone other than their original owner are protected. Any leftover seeds stay in reserve. There is no donation, and total seeds are conserved.
- The next round starter alternates. A player who owns all ten pits after settlement wins. If neither player has a legal move after settlement, the player with more pits wins; equal pit counts are a draw. Reaching a previously settled complete position also ends the game in a draw.
- After settlement, choose **End Game** to finish by agreement or **Continue** to play the prepared next round. The final score reports each player's pooled totals across settled rounds. During a round, a draw can also be proposed; the other human can agree or decline, and an AI opponent agrees automatically.

## AI opponents

Choose **Play Against AI** and select a difficulty:

- **Easy — Greedy:** deterministic heuristic move selection with lookahead through up to six protected-pit choices.
- **Medium — MCTS:** Monte Carlo tree search with 250 iterations per decision, including Drop/Skip choices.
- **Hard — Minimax Alpha-Beta:** searches four completed turns ahead, evaluates protected-pit choices as decisions by the same player, and uses alpha-beta pruning with a separate bound on protected-choice search to keep decisions responsive.

AI vs AI matchups are **MCTS vs Minimax Alpha-Beta**, **Greedy vs MCTS**, and **Greedy vs Minimax Alpha-Beta**. Both agents choose pits and protected-pit actions automatically.

## Controls

- Use the mouse to select menu options, legal pits, and buttons. Menu choices can also be selected with the number keys shown on screen; press `Esc` or `0` to go back from a submenu.
- **Restart** starts the current mode or matchup over. **Back** returns to the previous setup page. **Resign & Leave** returns to the mode selection screen.
- During a round, use **Propose Draw** to offer a draw. At the round end, select **Settle Round**, then choose **End Game** or **Continue**.

## Install and run

Requires Python 3. From the project folder, create a virtual environment, install the dependency, and start the game:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On Windows, create the environment with `py -m venv .venv` and activate it with `.\.venv\Scripts\Activate.ps1` in PowerShell or `.venv\Scripts\activate.bat` in Command Prompt. Then run the same pip install and start commands.

Run the automated tests with:

```bash
python -m unittest discover -s tests
```

## Project structure

- `main.py` — application entry point
- `seed_duel/model.py` — shared game state, phases, and events
- `seed_duel/rules.py` — legal actions, turn transitions, repetition, and settlement
- `seed_duel/ai/` — Greedy, MCTS, and Minimax agents
- `seed_duel/ui/app.py` — Pygame menus, board, controls, and event animations
- `tests/` — automated rules, AI, and UI tests
