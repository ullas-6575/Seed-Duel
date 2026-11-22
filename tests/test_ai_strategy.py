import unittest
from random import Random
from unittest.mock import patch

from seed_duel.ai.mcts import _rollout
from seed_duel.ai.strategy import advance_round_for_search, strategic_value
from seed_duel.model import GameState, Phase
from seed_duel.rules import apply_select_pit


class RoundAwareStrategyTests(unittest.TestCase):
    def test_search_transition_settles_and_prepares_the_next_round(self) -> None:
        ended = GameState(
            pits=(0, 0, 0, 0, 0, 2, 1, 3, 0, 4),
            player=0,
            phase=Phase.ROUND_END,
            captured=(18, 12),
            initial_total=40,
            terminal_reason="no_legal_start",
        )

        next_round = advance_round_for_search(ended)

        self.assertEqual(next_round.round_number, 2)
        self.assertEqual(next_round.captured, (0, 0))
        self.assertEqual(next_round.seed_total(), 40)
        self.assertIn(next_round.phase, (Phase.SELECT, Phase.ROUND_END, Phase.GAME_END))

    def test_strategic_value_rewards_conquered_opponent_territory(self) -> None:
        neutral = GameState(
            pits=(4, 4, 4, 4),
            owners=(0, 0, 1, 1),
            protected=(False, False, False, False),
            initial_total=16,
        )
        invaded = neutral.evolve(
            owners=(0, 0, 0, 1),
            protected=(False, False, True, False),
        )

        self.assertGreater(
            strategic_value(invaded, 0),
            strategic_value(neutral, 0),
        )

    def test_projected_settlement_does_not_mutate_the_live_state(self) -> None:
        state = GameState(
            pits=(0, 4, 4, 4),
            captured=(4, 0),
            owners=(0, 0, 1, 1),
            protected=(False, False, False, False),
            initial_total=16,
        )
        original = state

        strategic_value(state, 0, project_settlement=True)

        self.assertEqual(state, original)

    def test_mcts_rollout_crosses_one_round_boundary(self) -> None:
        state = GameState(pits=(1, 0, 0, 0), initial_total=1)
        ended, _ = apply_select_pit(state, 0, auto_protected=False)
        self.assertIs(ended.phase, Phase.ROUND_END)

        with patch(
            "seed_duel.ai.mcts.advance_round_for_search",
            wraps=advance_round_for_search,
        ) as advance:
            reward = _rollout(ended, 0, 5, 1, Random(7))

        advance.assert_called_once()
        self.assertGreaterEqual(reward, 0.0)
        self.assertLessEqual(reward, 1.0)


if __name__ == "__main__":
    unittest.main()
