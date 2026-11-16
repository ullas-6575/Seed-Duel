# Seed Duel

Seed Duel is a local Python and Pygame strategy game. Play against another person or choose an AI opponent. Rounds redistribute seeds according to pit ownership, and pits that cannot be refilled transfer ownership and become protected.

## How to play

- The board starts with five pits per player and four seeds in each pit (40 seeds total).
- Player 1 goes first. Choose a non-empty pit on your side.
- Pick up all seeds in that pit and sow them one at a time around the board.
- If the pit after your last seed contains seeds, pick them up and continue sowing.
- If that next pit is empty, capture the seeds in the pit after it, then end your turn.
- At a protected pit, choose **Drop** to place a seed there or **Skip** to pass it without spending a seed. Protected pits cannot be picked up or captured.
- A round ends when the next player has no legal pit, the board is empty, or a position repeats. An exact repeated checkpoint during a turn also ends the round.
- Settle a round to pool each player's captures, reserve, and owned-pit seeds. Original owners get first chance to reclaim captured pits at four seeds each; remaining owned pits then refill in index order. Unfillable pits transfer to the other player and are protected until reclaimed. Remaining seeds stay in reserve. There is no donation.
- After settlement, choose **End Game** or **Continue** by agreement. Owning all ten pits wins immediately. If neither player can move after settlement, pit ownership decides the result.

## AI difficulty

Choose **Play Against AI** from the startup menu, then select a level:

- **Easy — Greedy:** chooses the move with the best immediate heuristic score.
- **Medium — MCTS:** uses Monte Carlo tree search with 250 iterations.
- **Hard — Minimax:** searches four turns ahead.

## Install and run

You need Python 3. From the project folder, create and activate a virtual environment, then install the requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Start the game:

```bash
python main.py
```

On Windows, create the environment with `py -m venv .venv`. Activate it in PowerShell with `.\.venv\Scripts\Activate.ps1`, or in Command Prompt with `.venv\Scripts\activate.bat`; then use the same pip install and run commands.

## Controls

- Use the mouse to select menu options and legal pits.
- You can also select menu options with the number keys shown on screen. On the AI level page, press `Esc` or `0` to go back.
- **Restart** starts the current mode and AI level over.
- **Back** returns to the previous setup page.
- **Resign & Leave** returns to the main mode selection.
- At the end of a round, click **Settle Round**, then choose **End Game** or **Continue**. End Game reports the score accumulated across settled rounds.
- During a round, click **Propose Draw**. In two-player mode the other player can agree or decline; an AI opponent agrees automatically.
- AI opponents automatically choose **Drop** when they encounter a protected pit. They do not search every possible Drop/Skip route for loops.

## Project layout

- `main.py` — application entry point
- `seed_duel/rules.py` — game rules and state transitions
- `seed_duel/ai/` — Greedy, Minimax, and MCTS agents
- `seed_duel/ui/app.py` — Pygame menus, board, and animation
- `docs/` — game decisions and implementation notes
