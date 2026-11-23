"""Small headless demonstration of the first engine milestone."""

from .rules import apply_select_pit, initial_state


#!/usr/bin/env python3
"""Small headless demonstration of the first engine milestone.
Now supports custom board sizes via command‑line arguments.
"""
import argparse
from .rules import apply_select_pit, initial_state


def parse_args():
    parser = argparse.ArgumentParser(description="Run Seed Duel with optional board size.")
    parser.add_argument("--pits", type=int, default=5,
                        help="Number of pits per player (default 5).")
    parser.add_argument("--seeds", type=int, default=4,
                        help="Seeds per pit (default 4).")
    return parser.parse_args()


def main() -> None:
    """Create a fresh game, make one move, and print a summary.
    The board size can be changed with ``--pits`` and ``--seeds``.
    """
    args = parse_args()
    # Create initial state using the requested dimensions.
    state = initial_state(pits_per_player=args.pits, seeds_per_pit=args.seeds)
    # Apply a move on the first legal pit (index 0 works for any board).
    state, events = apply_select_pit(state, 0)
    print("Events:", ", ".join(event.kind for event in events))
    print("Pits:", list(state.pits))
    print("Captured:", list(state.captured))
    print("Next player:", state.player + 1)


if __name__ == "__main__":
    main()

    state = initial_state()
    state, events = apply_select_pit(state, 0)
    print("Events:", ", ".join(event.kind for event in events))
    print("Pits:", list(state.pits))
    print("Captured:", list(state.captured))
    print("Next player:", state.player + 1)


if __name__ == "__main__":
    main()
