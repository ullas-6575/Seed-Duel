# Seed Duel

## Description

Seed Duel is a local, turn-based seed-sowing strategy game built with Python and Pygame. Players sow seeds around a ten-pit board, capture seeds, and compete for pit ownership across rounds. It supports two people playing on one computer, a person playing against an AI, and AI-versus-AI matches. The game is intended for players who enjoy tactical board games and for developers exploring game rules and search-based opponents.

## Features

- Human vs Human, Human vs AI, and AI vs AI game modes.
- Three AI opponents: Greedy, Monte Carlo Tree Search (MCTS), and Minimax Alpha-Beta.
- On-demand AI suggestion (**Hint** lightbulb button) limited to 3 uses per player per round.
- Built-in sound chimes and visual highlights notifying human players when it is their turn to play or choose **Drop** / **Skip** (with a mute toggle button and `M` shortcut).
- Seed sowing, animated captures into per-player Account pits, protected pits with padlock icons and chains, and round settlement with contiguous pit ownership changes.
- Repetition detection and round/game end conditions.
- Draw proposals in human games and end-of-round controls.
- Mouse and keyboard menu controls.
- Browser-playable Docker setup using a virtual display and noVNC.

## Game Modes

When you launch Seed Duel, you start on the **Main Menu** where you choose how you want to play (click a button or press `1`, `2`, or `3`):

- **Human vs Human (`1`):** Two players take turns on the same computer.
- **Human vs AI (`2`):** Player 1 is human and Player 2 is controlled by the selected AI.
- **AI vs AI (`3`):** Select a matchup and watch both agents play. The first listed agent controls Player 1.

**Screen Type: Main Menu**

![Seed Duel main menu](screenshots/Screenshot%20from%202026-11-21%2000-04-35.png)

## How to Play (Step-by-Step Guide)

### 1. Board Setup & What to Do First

The board has ten pits arranged in a ring—five per player (`1–5` along the bottom row for Player 1, and `6–10` right-to-left along the top row for Player 2)—and begins with four seeds in each pit (40 seeds total). Player 1 starts.

- **Reading the board & Game Status panel:**
  - Each pit shows its pit number at the top, its current seed count at the bottom, and an ownership badge above it (`P1` in green or `P2` in red). Locked/protected pits also show a padlock, and consecutive locked pits are joined by a chain.
  - The right-hand **Game Status** panel tracks whose turn it is, total conserved seeds (`40 / 40`), reserves, pits owned, and active AI hint details (when requested). Each player has a separate **Account pit** in this panel; captured seeds visibly fly into the correct account and its count updates when the animation lands.
- **What to do:** When it becomes your turn, the game plays a soft two-note chime and briefly highlights the footer message box in green. Click any **highlighted, non-empty pit** that you own (`P1` for Player 1, `P2` for Player 2).
- **What happens:** You pick up all the seeds from that pit and sow them one at a time counter-clockwise (`1 → 2 → … → 10 → 1`) around the board.
- **Draws & Controls:** At any time during a human round, you can click **Propose Draw** (or use **Restart**, **Back**, or **Resign & Leave**). In Human vs Human, the other player clicks **Agree** or **Decline**; in Human vs AI, the draw is agreed immediately. When a draw is agreed, the game ends and prompts you to press **Restart** to play again.

**Screen Type: Human vs Human Gameplay (Starting Board & Draw Agreement)**

![Seed Duel Human vs Human gameplay](screenshots/Screenshot%20from%202026-11-21%2000-06-03.png)

### 2. Relaying, Capturing & Ending Your Turn

- Before picking up seeds, the engine checks for a repeated state.
- Seeds are dropped one at a time advancing around the board until your hand is empty.
- When your hand becomes empty, the game inspects the **next normal pit** (skipping over protected pits):
  - **If it contains seeds:** Pick them up automatically and continue sowing (relaying).
  - **If it is empty:** Capture all seeds from the **next normal pit** beyond the empty pit, and your turn ends (switching to the other player). An empty capture target awards no seeds.
- If the next player has no non-empty owned pit, or a complete state repeats, the **round ends** and proceeds to settlement.
- Protected pits (marked with a padlock icon and linked by metal chains when adjacent) cannot be selected as starting pits, picked up during relaying, or captured.

**Diagram Type: Turn Flow (Sowing, Relaying, Capturing & Round End)**

![Seed Duel turn flow diagram](screenshots/Screenshot%20from%202026-11-21%2000-27-56.png)

### 3. Protected Pits (Drop or Skip)

When sowing reaches a protected pit (marked with a padlock), the game pauses, plays a distinct three-tone alert chime, pulses a gold border around the footer message box, and highlights the **Drop** and **Skip** buttons to ask you what to do next:

- Choose **Drop** to place one seed into the protected pit.
- Choose **Skip** to pass over it without using a seed.

Make a choice each time your sowing encounters a protected pit.

### 4. On-Demand AI Hint (Idea Bulb)

During a human player's turn (in both Human vs AI and Human vs Human), AI suggestions do **not** appear automatically.

- **What to do:** Click the **Hint** lightbulb button in the top bar during your pit-selection turn if you want the AI (Minimax, depth 3) to recommend a move.
- **What happens:** The suggested pit is highlighted with a pulsing blue ring on the board, the **Game Status** panel displays the suggested pit and its Minimax score, and the message bar confirms the recommendation and remaining hints.
- **Limit:** Each player can use the AI suggestion **at most 3 times per round** (`Hint 3/3` → `Hint 2/3` → `Hint 1/3` → `Hint 0/3`). Clicking **Hint** again on the same turn while a suggestion is already active does not consume an extra hint. The counter resets to `3/3` at the start of each new round or game.

### 5. Rounds, Settlement & Winning (What to Do Next)

- **When a round ends:** A round ends when the board is empty, the next player has no legal starting pit, no normal (unprotected) pits remain, or a complete between-turn position repeats.
- **In-turn loops:** If a hand-empty checkpoint repeats during a turn in Round 1, the round ends. In later rounds, the turn ends. At the final protected-pit choice, a **Later-Round Loop Detected** dialog lets a human **Try Drop** / **Try Skip** (the opposite action from that checkpoint) or **End & Settle** the round immediately. If the alternate action repeats, the prompt appears again. The prompt compares current settlement totals with the immediate projection from the alternate action. AI agents evaluate both choices automatically. Repetition detection follows the path actually played and does not establish that every alternate path loops.
- **What to do at round end:** Click **Settle Round** to calculate totals and prepare the board for the next round.
- **How settlement works:**
  - Each player pools their captured seeds, reserve, and seeds in pits they own.
  - Original owners first reclaim lost pits they can afford at four seeds per pit, peeling back an invasion from its inner edge toward the boundary so remaining protected pits stay contiguous (reclaimed pits are refilled to four seeds and are no longer protected).
  - Each player then refills their remaining owned pits at four seeds per pit.
  - **Capturing an opponent's pit:** If a player cannot fill one of their pits, the opponent can only capture and take ownership of it if they have enough remaining seeds to **fill the pit fully** (four seeds placed into that pit). An invasion starts at either boundary of the opponent's original territory and expands consecutively from that same side; it cannot jump over a filled pit to capture an isolated interior pit. Captured pits held by someone other than their original owner become **protected**, display a padlock, and adjacent protected pits are joined by a chain.
  - **Fair remainder rule:** Any remaining seeds that neither player could use to fill a full pit are given back to the board—filling any remaining unfilled pits first (and distributing round-robin if any remain)—leaving reserves at `0 / 0` while conserving all 40 seeds.
- **Next round or end game:**
  - A round lead builds territory across rounds; the round result is not the final game result until the conquest goal is met or players choose to end.
  - The next round starter alternates.
  - A player who owns all ten pits after settlement wins immediately (**conquest**).
  - If neither player has a legal move after settlement, the player who owns more pits wins; equal pit counts result in a draw.
  - Otherwise, after settlement, choose **End Game** to finish by agreement or **Continue** to play the prepared next round (in Human vs Human, the other player confirms with **Agree** or **Decline**; in AI modes it applies immediately). The final score reports each player's pooled totals across settled rounds.
  - During a round, a draw can be proposed; the other human can accept or decline, and an AI opponent accepts automatically.

**Diagram Type: Round Settlement & Multi-Round Conquest Flow**

![Seed Duel round settlement and conquest flow diagram](screenshots/Screenshot%20from%202026-11-21%2000-36-16.png)

## AI Opponents

### Human vs AI (Difficulty Selection)

From the Main Menu, choose **Human vs AI** (`2`) and then select a difficulty (`1`, `2`, or `3`, or press `Esc` / `0` to go back):

- **Easy — Greedy:** Deterministic heuristic move selection with lookahead through up to six protected-pit choices (five additional choices during protected-pit decisions; ties keep the first pit in ring order / Drop).
- **Medium — Monte Carlo Tree Search (MCTS):** UCT search with 20 iterations per decision and random rollouts up to 100 steps. Rollouts may cross one settlement boundary into the prepared next round and include Drop/Skip choices.
- **Hard — Minimax (Minimax Alpha-Beta):** Searches five completed turns ahead, treats protected-pit choices as decisions by the same player, and uses alpha-beta pruning with a separate bound on protected-choice search (up to eight protected choices per search). At a reached round boundary it settles the round and evaluates/searches the prepared next round.

All three agents use a shared strategic projection that considers secured seeds, reserves, mobility, territory, captured original pits and conquest. In a local 30-seed paired Round-1 calibration (60 games with sides swapped), depth-5 Minimax recorded 32 wins, 27 losses and 1 draw against the 20-iteration MCTS configuration, with cumulative seed margin `+142`. This supports the current Medium/Hard product ordering for that configuration; it does not guarantee that Minimax wins every position.

**Screen Type: AI Difficulty Selection**

![AI difficulty selection screen](screenshots/Screenshot%20from%202026-11-21%2000-04-43.png)

**Screen Type: Human vs AI Gameplay with On-Demand AI Hint (Lightbulb Button)**

![Seed Duel Human vs AI gameplay with AI hint](screenshots/Screenshot%20from%202026-11-21%2000-05-18.png)

### AI vs AI (Matchup Selection & Spectating)

From the Main Menu, choose **AI vs AI** (`3`) to pick one of the available matchups:

- **MCTS vs Minimax Alpha-Beta**
- **Greedy vs MCTS**
- **Greedy vs Minimax Alpha-Beta**

**Screen Type: AI Matchup Selection**

![AI matchup selection screen](screenshots/Screenshot%20from%202026-11-21%2000-04-29.png)

Once a matchup starts, both agents choose pits and protected-pit actions automatically while you watch the animated moves, protected-pit padlocks and chains, and the animated Account pits in the Game Status panel. At round end, click **Settle Round**, then **Continue** or **End Game**.

**Screen Type: AI vs AI Gameplay (Later Round with Protected Pit & Drop Action)**

![Seed Duel AI vs AI gameplay](screenshots/Screenshot%20from%202026-11-21%2000-00-26.png)

## Controls

- Use the mouse to select menu options, legal pits, and buttons. Menu options can also be selected with their displayed number keys (`1`, `2`, `3`). Press `Esc` or `0` to return from a submenu.
- **Sound toggle (speaker icon)** or press **`M`** to mute or unmute turn and **Drop** / **Skip** notification chimes (on by default; visual cues remain active when muted or when no audio device is available).
- **Hint (lightbulb icon)** requests an on-demand AI move suggestion during your pit-selection turn (up to 3 per player per round).
- **Restart** starts the current mode, difficulty, or matchup over from Round 1. **Back** returns to the previous setup page. **Resign & Leave** returns directly to the Main Menu.
- During a round, select **Propose Draw** to offer a draw (confirmed with **Agree** / **Decline** in Human vs Human). When encountering a protected pit, select **Drop** or **Skip**. If a later-round loop dialog appears, choose **Try Drop** / **Try Skip** or **End & Settle**. At round end, select **Settle Round**, then choose **End Game** or **Continue**.

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

Use the mouse to select menu options and pits. Menu options may also be selected with the displayed number keys; press `Esc` or `0` to go back from a submenu. During play, choose a highlighted pit you own. When sowing reaches a protected pit, choose **Drop** or **Skip**. Use the **Sound** toggle (`M`), **Hint**, **Restart**, **Back**, or **Resign & Leave** as needed. At round end, settle the round and choose whether to continue or end the game.

To run the automated test suite locally (36 unit tests covering rules, AI strategy, and UI):

```bash
python -m unittest discover -s tests
```

You can also run a quick headless engine demo with:

```bash
python -m seed_duel
```

## Technologies Used

- **Language:** Python 3.12+
- **Game and graphics library:** Pygame 2.6.1
- **AI methods:** Greedy heuristic search, Monte Carlo Tree Search, and Minimax with Alpha-Beta pruning
- **Containerization:** Docker and Docker Compose
- **Container display:** Xvfb, x11vnc, noVNC, and websockify
- **Testing:** Python `unittest`

## Project Structure

```text
Seed-Duel/
├── seed_duel/
│   ├── ai/                 # Greedy, MCTS, Minimax, and shared strategy evaluation
│   ├── ui/                 # Pygame menus, board, animations, and sound chimes
│   ├── model.py            # Shared game state, phases, and events
│   └── rules.py            # Legal actions, turns, repetition, and settlement
├── screenshots/            # README UI screenshots and gameplay diagrams
├── tests/                  # Rules, AI, and UI tests
├── compose.yaml            # Docker Compose service
├── Dockerfile              # Container image definition
├── docker-entrypoint.sh    # Virtual display and noVNC startup
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
└── README.md
```
