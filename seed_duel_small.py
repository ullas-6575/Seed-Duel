#!/usr/bin/env python3
"""Launch Seed Duel with a 3‑pit, 2‑seed per pit board.
All core rules and AI behaviours remain unchanged – the engine dynamically
uses the supplied board dimensions, so the same AI modules (greedy, MCTS,
minimax, etc.) work out of the box.
"""
import sys
from seed_duel.rules import apply_select_pit, initial_state

def main() -> None:
    # Fixed small board: 3 pits per player, 2 seeds per pit.
    state = initial_state(pits_per_player=3, seeds_per_pit=2)
    # Perform a single move (pit index 0) just to demonstrate that the game starts.
    state, events = apply_select_pit(state, 0)
    print("Events:", ", ".join(e.kind for e in events))
    print("Pits:", list(state.pits))
    print("Captured:", list(state.captured))
    print("Next player:", state.player + 1)

if __name__ == "__main__":
    main()
