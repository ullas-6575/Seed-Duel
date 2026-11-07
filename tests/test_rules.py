import unittest

from seed_duel import Phase
from seed_duel.model import GameState
from seed_duel.rules import apply_select_pit, begin_turn, initial_state, legal_actions, settle_round


class RoundOneRulesTests(unittest.TestCase):
    def test_t01_ordinary_turn(self) -> None:
        state, events = apply_select_pit(initial_state(), 0)

        self.assertEqual(state.pits, (0, 0, 5, 5, 5, 0, 5, 5, 5, 5))
        self.assertEqual(state.captured, (5, 0))
        self.assertEqual(state.player, 1)
        self.assertEqual(state.phase, Phase.SELECT)
        self.assertEqual(sum(event.kind == "SeedDropped" for event in events), 8)
        self.assertEqual(sum(event.kind == "SeedsPickedUp" for event in events), 2)
        state.assert_conserved()

    def test_empty_capture_target_adds_zero_and_ends_turn(self) -> None:
        state = GameState(pits=(1, 0, 0, 0), initial_total=1)
        result, _ = apply_select_pit(state, 0)

        self.assertEqual(result.pits, (0, 1, 0, 0))
        self.assertEqual(result.captured, (0, 0))
        self.assertEqual(result.phase, Phase.ROUND_END)
        self.assertEqual(result.terminal_reason, "no_legal_start")
        result.assert_conserved()

    def test_t03_no_legal_start_ends_round_then_settles(self) -> None:
        state = GameState(
            pits=(0, 0, 0, 0, 0, 2, 1, 3, 0, 4), player=0,
            captured=(18, 12), initial_total=40,
        )
        self.assertEqual(legal_actions(state), ())
        ended, events = begin_turn(state)
        self.assertEqual(events[0].kind, "RoundEnded")
        settled, _ = settle_round(ended)

        self.assertEqual(settled.pits, (0,) * 10)
        self.assertEqual(settled.captured, (18, 22))
        settled.assert_conserved()

    def test_illegal_selection_does_not_change_state(self) -> None:
        state = initial_state()
        result, events = apply_select_pit(state, 7)
        self.assertEqual(result, state)
        self.assertEqual(events[0].kind, "IllegalAction")


if __name__ == "__main__":
    unittest.main()
