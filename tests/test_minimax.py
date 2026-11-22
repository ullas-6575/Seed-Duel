import unittest
from unittest.mock import patch

from seed_duel.ai.strategy import advance_round_for_search
from seed_duel.ai.minimax import recommend_move
from seed_duel.model import GameState
from seed_duel.rules import initial_state, legal_actions


class MinimaxAdvisorTests(unittest.TestCase):
    def test_recommendation_is_legal_and_does_not_change_state(self) -> None:
        state = initial_state()
        recommendation = recommend_move(state, depth=2)

        self.assertIsNotNone(recommendation)
        assert recommendation is not None
        self.assertIn(recommendation.pit_index, legal_actions(state))
        self.assertEqual(state, initial_state())
        self.assertGreater(recommendation.nodes, 0)

    def test_no_recommendation_without_a_legal_move(self) -> None:
        state = initial_state(seeds_per_pit=0)
        self.assertIsNone(recommend_move(state))

    def test_search_crosses_a_reached_round_boundary(self) -> None:
        state = GameState(pits=(1, 0, 0, 0), initial_total=1)
        with patch(
            "seed_duel.ai.minimax.advance_round_for_search",
            wraps=advance_round_for_search,
        ) as advance:
            recommendation = recommend_move(
                state, depth=1, round_lookahead=1
            )

        self.assertIsNotNone(recommendation)
        advance.assert_called()


if __name__ == "__main__":
    unittest.main()
