import unittest

from seed_duel.ai.greedy import choose_protected_choice as choose_greedy_choice
from seed_duel.ai.mcts import recommend_protected_choice as choose_mcts_choice
from seed_duel.ai.minimax import recommend_protected_choice as choose_minimax_choice
from seed_duel.model import GameState, Phase
from seed_duel.rules import apply_protected_choice, apply_select_pit


def protected_choice_fixture() -> GameState:
    """T06-style position stopped at the first protected encounter."""
    state = GameState(
        pits=(4, 4, 4, 4, 4, 0, 4, 4, 4, 4),
        owners=(0, 0, 0, 0, 0, 0, 1, 1, 1, 1),
        protected=(False, False, False, False, False, True, False, False, False, False),
        reserves=(4, 0),
        initial_total=40,
    )
    pending, _ = apply_select_pit(state, 4, auto_protected=False)
    assert pending.phase is Phase.DROP_SKIP
    return pending


class AiProtectedChoiceTests(unittest.TestCase):
    def test_engine_exposes_distinct_drop_and_skip_branches(self) -> None:
        state = protected_choice_fixture()
        dropped, drop_events = apply_protected_choice(state, drop=True)
        skipped, skip_events = apply_protected_choice(state, drop=False)

        self.assertNotEqual(dropped, skipped)
        self.assertEqual(dropped.pits[5], 1)
        self.assertEqual(skipped.pits[5], 0)
        drop_data = dict(drop_events[0].data)
        skip_data = dict(skip_events[0].data)
        self.assertEqual(drop_data["remaining_hand"], skip_data["remaining_hand"] - 1)
        self.assertEqual(state.pits[5], 0)

    def test_all_ai_levels_search_the_protected_choice(self) -> None:
        state = protected_choice_fixture()

        greedy_choice = choose_greedy_choice(state)
        minimax_choice = choose_minimax_choice(state, depth=2)
        mcts_choice = choose_mcts_choice(state, iterations=50, seed=1)

        # This fixture rewards preserving the seed in hand, so all three
        # algorithms choose Skip instead of using the former forced-Drop path.
        self.assertFalse(greedy_choice)
        self.assertIsNotNone(minimax_choice)
        self.assertIsNotNone(mcts_choice)
        assert minimax_choice is not None and mcts_choice is not None
        self.assertFalse(minimax_choice.drop)
        self.assertFalse(mcts_choice.drop)
        self.assertEqual(state, protected_choice_fixture())

    def test_choice_advisors_only_accept_a_pending_protected_choice(self) -> None:
        normal = GameState(pits=(1, 0), initial_total=1)
        self.assertIsNone(choose_greedy_choice(normal))
        self.assertIsNone(choose_minimax_choice(normal))
        self.assertIsNone(choose_mcts_choice(normal))


if __name__ == "__main__":
    unittest.main()
