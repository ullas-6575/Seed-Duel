"""Small headless demonstration of the first engine milestone."""

from .rules import apply_select_pit, initial_state


def main() -> None:
    state = initial_state()
    state, events = apply_select_pit(state, 0)
    print("Events:", ", ".join(event.kind for event in events))
    print("Pits:", list(state.pits))
    print("Captured:", list(state.captured))
    print("Next player:", state.player + 1)


if __name__ == "__main__":
    main()
