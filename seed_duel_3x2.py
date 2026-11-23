#!/usr/bin/env python3
"""Launch Seed Duel with a 3‑pit, 2‑seed per pit board.
All core rules, AI, and UI remain unchanged – the engine dynamically
uses the supplied board dimensions, so existing AI modules work out of the
box.
"""
import sys
from seed_duel.rules import apply_select_pit, initial_state

def main() -> None:
    # Fixed board: 3 pits per player, 2 seeds per pit.
    state = initial_state(pits_per_player=3, seeds_per_pit=2)
    # Demonstrate one move.
    state, events = apply_select_pit(state, 0)
    print("Events:", ", ".join(e.kind for e in events))
    print("Pits:", list(state.pits))
    print("Captured:", list(state.captured))
    print("Next player:", state.player + 1)

if __name__ == "__main__":
    main()
