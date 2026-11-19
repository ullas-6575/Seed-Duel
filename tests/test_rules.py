import unittest

from seed_duel import Phase
from seed_duel.model import GameState
from seed_duel.rules import (
    apply_protected_choice,
    apply_select_pit,
    begin_turn,
    end_round_after_later_cycle,
    initial_state,
    legal_actions,
    settle_round,
)


def later_round_loop_fixture() -> GameState:
    return GameState(
        pits=(3, 1, 0, 1, 0, 0, 2, 1, 0, 0),
        player=0,
        captured=(12, 12),
        reserves=(8, 0),
        owners=(0, 0, 0, 0, 0, 0, 1, 1, 1, 0),
        protected=(False, False, False, False, False, True, False, False, False, True),
        initial_total=40,
        round_number=2,
    )


class RulesTests(unittest.TestCase):
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

        self.assertEqual(settled.pits, (4, 4, 4, 4, 0, 4, 4, 4, 4, 4))
        self.assertEqual(settled.captured, (0, 0))
        self.assertEqual(settled.reserves, (2, 2))
        self.assertEqual(settled.owners, (0, 0, 0, 0, 1, 1, 1, 1, 1, 1))
        self.assertTrue(settled.protected[4])
        settled.assert_conserved()

    def test_illegal_selection_does_not_change_state(self) -> None:
        state = initial_state()
        result, events = apply_select_pit(state, 7)
        self.assertEqual(result, state)
        self.assertEqual(events[0].kind, "IllegalAction")

    def test_t02_round_one_repeat_ends_the_round(self) -> None:
        state = GameState(
            pits=(1, 0, 2, 1, 2, 1, 0, 2, 1, 0),
            player=0,
            captured=(16, 14),
            initial_total=40,
            round_number=1,
        )
        result, events = apply_select_pit(state, 4, auto_protected=False)

        self.assertIs(result.phase, Phase.ROUND_END)
        self.assertEqual(result.terminal_reason, "in_turn_repeat")
        self.assertEqual(result.pits, state.pits)
        self.assertEqual(sum(event.kind == "SeedsPickedUp" for event in events), 40)
        self.assertEqual(sum(event.kind == "SeedDropped" for event in events), 70)
        self.assertEqual(dict(events[-2].data)["outcome"], "round_ended")
        result.assert_conserved()

    def test_t09_later_round_repeat_ends_only_the_current_turn(self) -> None:
        state = later_round_loop_fixture()
        result, first_events = apply_select_pit(state, 1, auto_protected=False)
        events = list(first_events)

        choices = 0
        while result.phase is Phase.DROP_SKIP and choices < 100:
            result, new_events = apply_protected_choice(result, drop=False)
            events.extend(new_events)
            choices += 1

        self.assertLess(choices, 100)
        self.assertIs(result.phase, Phase.SELECT)
        self.assertIsNone(result.terminal_reason)
        self.assertEqual(result.player, 1)
        self.assertEqual(result.pits, state.pits)
        self.assertEqual(sum(event.kind == "SeedsPickedUp" for event in events), 28)
        self.assertTrue(any(event.kind == "CycleDetected" for event in events))
        self.assertEqual(events[-1].kind, "TurnEnded")
        self.assertFalse(any(event.kind == "RoundEnded" for event in events))
        self.assertTrue(result.loop_resolution_available)
        result.assert_conserved()

    def test_human_can_end_and_settle_after_a_later_round_loop(self) -> None:
        state = later_round_loop_fixture()
        result, _ = apply_select_pit(state, 1, auto_protected=False)
        while result.phase is Phase.DROP_SKIP:
            result, _ = apply_protected_choice(result, drop=False)

        ended, events = end_round_after_later_cycle(result)

        self.assertIs(ended.phase, Phase.ROUND_END)
        self.assertEqual(ended.terminal_reason, "later_loop_settled")
        self.assertFalse(ended.loop_resolution_available)
        self.assertEqual(events[-1].kind, "RoundEnded")
        ended.assert_conserved()

    def test_t09_drop_branch_escapes_the_later_round_loop(self) -> None:
        state = later_round_loop_fixture()
        pending, _ = apply_select_pit(state, 1, auto_protected=False)
        self.assertIs(pending.phase, Phase.DROP_SKIP)

        result, events = apply_protected_choice(pending, drop=True)

        self.assertIs(result.phase, Phase.SELECT)
        self.assertEqual(result.player, 1)
        self.assertEqual(result.pits, (0, 1, 2, 1, 0, 1, 0, 0, 1, 0))
        self.assertEqual(result.captured, (14, 12))
        self.assertEqual(events[-1].kind, "TurnEnded")
        result.assert_conserved()


if __name__ == "__main__":
    unittest.main()
