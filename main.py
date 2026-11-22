"""Launch the Seed Duel Pygame application."""

import argparse

from seed_duel.ui.app import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch Seed Duel.")
    parser.add_argument(
        "--small",
        "--mini",
        action="store_true",
        help="Start with the smaller 4-pit, 3-seed board variant selected.",
    )
    args = parser.parse_args()
    if args.small:
        run(pits_per_player=4, seeds_per_pit=3)
    else:
        run()


if __name__ == "__main__":
    main()
