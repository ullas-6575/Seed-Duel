# Seed Duel

## Description

Seed Duel is a local, turn-based seed-sowing strategy game built with Python and Pygame. Players sow seeds around a ten-pit board, capture seeds, and compete for pit ownership across rounds. It supports two people playing on one computer, a person playing against an AI, and AI-versus-AI matches. The game is intended for players who enjoy tactical board games and for developers exploring game rules and search-based opponents.

## Features

- Human vs Human, Human vs AI, and AI vs AI game modes.
- Three AI opponents: Greedy, Monte Carlo Tree Search (MCTS), and Minimax Alpha-Beta.
- Seed sowing, captures, protected pits, and round settlement with pit ownership changes.
- Repetition detection and round/game end conditions.
- Draw proposals in human games and end-of-round controls.
- Mouse and keyboard menu controls.
- Browser-playable Docker setup using a virtual display and noVNC.

## Game Modes

- **Human vs Human:** Two players take turns on the same computer.
- **Human vs AI:** Player 1 is human and Player 2 is controlled by the selected AI.
- **AI vs AI:** Select a matchup and watch both agents play. The first listed agent controls Player 1.

## How to Play

The board has ten pits, five per player, and begins with four seeds in each pit. Player 1 starts. On your turn, choose a highlighted, non-empty pit that you own. Pick up all its seeds and sow them one at a time around the board.

When your hand is empty, inspect the next normal pit, skipping protected pits. If it contains seeds, pick them up and continue sowing. If it is empty, capture the seeds from the next normal pit and end your turn. An empty capture target awards no seeds. Protected pits cannot be selected as starting pits, picked up during relaying, or captured.

When sowing reaches a protected pit, choose **Drop** to put one seed into it, or **Skip** to pass over it without using a seed. Make a choice each time you encounter a protected pit.

### Rounds and winning

- A round ends when the board is empty, the next player has no legal starting pit, or a complete between-turn position repeats.
- If a hand-empty checkpoint repeats during a turn in Round 1, the round ends. In later rounds, the turn ends. At the final protected-pit choice, a human may try the opposite **Drop** or **Skip** action, or end and settle the round. If the alternate action repeats, the prompt appears again. The prompt compares current settlement totals with the immediate projection from the alternate action. AI agents evaluate both choices automatically. Repetition detection follows the path actually played and does not establish that every alternate path loops.
- At settlement, each player pools their captured seeds, reserve, and seeds in pits they own. Original owners reclaim lost pits they can afford at four seeds per pit, then each player refills their other owned pits at four seeds per pit. An unfilled pit transfers to the other player. Any remaining seeds stay in reserve.
- Pits held by someone other than their original owner are protected. Settlement has no donation step, and the total number of seeds is conserved.
- The next round starter alternates. A player who owns all ten pits after settlement wins. If neither player has a legal move after settlement, the player who owns more pits wins; equal pit counts result in a draw. Reaching a previously settled complete position also ends the game in a draw.
- After settlement, choose **End Game** to finish by agreement or **Continue** to play the prepared next round. The final score reports each player's pooled totals across settled rounds. During a round, a draw can be proposed; the other human can accept or decline, and an AI opponent accepts automatically.

## AI Opponents

Choose **Play Against AI** and select a difficulty:

- **Easy — Greedy:** Deterministic heuristic move selection with lookahead through up to six protected-pit choices.
- **Medium — MCTS:** Monte Carlo Tree Search with 250 iterations per decision, including Drop/Skip choices.
- **Hard — Minimax Alpha-Beta:** Searches four completed turns ahead, treats protected-pit choices as decisions by the same player, and uses alpha-beta pruning with a separate bound on protected-choice search.

Available AI matchups are **MCTS vs Minimax Alpha-Beta**, **Greedy vs MCTS**, and **Greedy vs Minimax Alpha-Beta**. Both agents choose pits and protected-pit actions automatically.

## Controls

- Use the mouse to select menu options, legal pits, and buttons. Menu options can also be selected with their displayed number keys. Press `Esc` or `0` to return from a submenu.
- **Restart** starts the current mode or matchup over. **Back** returns to the previous setup page. **Resign & Leave** returns to the mode selection screen.
- During a round, select **Propose Draw** to offer a draw. At round end, select **Settle Round**, then choose **End Game** or **Continue**.

## Installation

### Prerequisites

- Python 3.12 or later for a local installation.
- Docker Desktop with Docker Compose for a containerized installation.
- Git, if cloning the repository.

Clone the repository and enter its directory:

```bash
git clone <repository-url>
cd Seed-Duel
```

### Local installation

Create and activate a virtual environment, then install the Python dependency:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS or Linux, use:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Docker installation

From the project directory, build the image and start the container:

```powershell
docker compose up --build
```

## Usage

### Play with Docker

Leave `docker compose up --build` running, then open [http://localhost:6080/vnc.html?autoconnect=1](http://localhost:6080/vnc.html?autoconnect=1) in a browser. Choose a game mode, then follow the on-screen prompts. Stop the container with `Ctrl+C` in the terminal.

To start the already-built container later, run `docker compose up` from the project directory. To run it in the background, use `docker compose up -d`; stop it with `docker compose down`.

### Play locally

After completing the local installation, start the game with:

```bash
python main.py
```

Use the mouse to select menu options and pits. Menu options may also be selected with the displayed number keys; press `Esc` or `0` to go back from a submenu. During play, choose a highlighted pit you own. When sowing reaches a protected pit, choose **Drop** or **Skip**. Use **Restart**, **Back**, or **Resign & Leave** as needed. At round end, settle the round and choose whether to continue or end the game.

To run the automated test suite locally:

```bash
python -m unittest discover -s tests
```

## Technologies Used

- **Language:** Python 3.12+
- **Game and graphics library:** Pygame 2.6.1
- **AI methods:** Greedy heuristic search, Monte Carlo Tree Search, and Minimax with Alpha-Beta pruning
- **Containerization:** Docker and Docker Compose
- **Container display:** Xvfb, x11vnc, noVNC, and websockify
- **Testing:** Python `unittest`

## Screenshots

Screenshots of the menus and gameplay are shown below. Each link points to the supplied image in the `screenshots/` folder.

### Main menu

![Seed Duel main menu](screenshots/Screenshot%202026-11-20%20155149.png)

### AI difficulty selection

![AI difficulty selection screen](screenshots/Screenshot%202026-11-20%20155244.png)

### AI matchup selection

![AI matchup selection screen](screenshots/Screenshot%202026-11-20%20155158.png)

### Human vs Human gameplay

![Seed Duel Human vs Human gameplay](screenshots/Screenshot%202026-11-20%20155303.png)

### AI vs AI gameplay

![Seed Duel AI vs AI gameplay](screenshots/Screenshot%202026-11-20%20155218.png)

## Project Structure

```text
Seed-Duel/
├── seed_duel/
│   ├── ai/                 # Greedy, MCTS, and Minimax agents
│   ├── ui/                 # Pygame menus, board, and event animations
│   ├── model.py            # Shared game state, phases, and events
│   └── rules.py            # Legal actions, turns, repetition, and settlement
├── screenshots/            # README UI screenshots
├── tests/                  # Rules, AI, and UI tests
├── compose.yaml            # Docker Compose service
├── Dockerfile              # Container image definition
├── docker-entrypoint.sh    # Virtual display and noVNC startup
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
└── README.md
```

## License

No license has been specified for this project yet.
