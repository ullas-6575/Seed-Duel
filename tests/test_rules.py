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

        self.assertEqual(settled.pits, (4, 4, 4, 4, 4, 4, 4, 4, 4, 4))
        self.assertEqual(settled.captured, (0, 0))
        self.assertEqual(settled.reserves, (0, 0))
        self.assertEqual(settled.owners, (0, 0, 0, 0, 0, 1, 1, 1, 1, 1))
        self.assertFalse(settled.protected[4])
        settled.assert_conserved()

    def test_opponent_captures_pit_only_when_able_to_fill_it_fully(self) -> None:
        state = GameState(
            pits=(0, 0, 0, 0, 0, 2, 1, 3, 0, 4), player=0,
            captured=(16, 14), initial_total=40,
        )
        ended, _ = begin_turn(state)
        settled, _ = settle_round(ended)

        self.assertEqual(settled.pits, (4, 4, 4, 4, 4, 4, 4, 4, 4, 4))
        self.assertEqual(settled.captured, (0, 0))
        self.assertEqual(settled.reserves, (0, 0))
        self.assertEqual(settled.owners, (0, 0, 0, 0, 1, 1, 1, 1, 1, 1))
        self.assertTrue(settled.protected[4])
        settled.assert_conserved()

    def test_captured_pits_expand_consecutively_from_one_boundary(self) -> None:
        state = GameState(
            pits=(0,) * 10,
            captured=(8, 32),
            initial_total=40,
            phase=Phase.ROUND_END,
            terminal_reason="test_boundary",
        )

        settled, _ = settle_round(state)

        self.assertEqual(settled.owners, (0, 0, 1, 1, 1, 1, 1, 1, 1, 1))
        self.assertEqual(
            settled.protected,
            (False, False, True, True, True, False, False, False, False, False),
        )
        settled.assert_conserved()

    def test_captured_pits_do_not_jump_over_a_filled_boundary_pit(self) -> None:
        state = GameState(
            pits=(0,) * 10,
            captured=(32, 8),
            initial_total=40,
            phase=Phase.ROUND_END,
            terminal_reason="test_boundary",
        )

        settled, _ = settle_round(state)

        self.assertEqual(settled.owners, (0, 0, 0, 0, 0, 1, 1, 0, 0, 0))
        self.assertEqual(
            settled.protected,
            (False, False, False, False, False, False, False, True, True, True),
        )
        settled.assert_conserved()

    def test_reclaim_peels_chain_from_inner_edge(self) -> None:
        state = GameState(
            pits=(0,) * 10,
            captured=(4, 36),
            owners=(1, 1, 1, 0, 0, 1, 1, 1, 1, 1),
            protected=(True, True, True, False, False, False, False, False, False, False),
            initial_total=40,
            phase=Phase.ROUND_END,
            terminal_reason="test_boundary",
        )

        settled, _ = settle_round(state)

        self.assertEqual(settled.owners[:5], (1, 1, 0, 0, 0))
        self.assertEqual(settled.protected[:5], (True, True, False, False, False))
        settled.assert_conserved()

    def test_repeating_a_settled_position_does_not_force_a_draw(self) -> None:
        boundary = initial_state().evolve(
            phase=Phase.ROUND_END,
            terminal_reason="test_boundary",
        )
        first, _ = settle_round(boundary)
        repeated_boundary = first.evolve(
            phase=Phase.ROUND_END,
            terminal_reason="test_boundary",
        )

        repeated, events = settle_round(repeated_boundary)

        self.assertIs(repeated.phase, Phase.ROUND_END)
        self.assertEqual(repeated.terminal_reason, "settled")
        self.assertIsNone(repeated.winner)
        self.assertFalse(any(event.kind == "DrawDetected" for event in events))
        repeated.assert_conserved()

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

    def test_small_four_pit_three_seed_variant_rules_and_settlement(self) -> None:
        state = initial_state(pits_per_player=4, seeds_per_pit=3)
        self.assertEqual(len(state.pits), 8)
        self.assertEqual(state.pits, (3,) * 8)
        self.assertEqual(state.initial_total, 24)
        self.assertEqual(state.seeds_per_pit, 3)
        self.assertEqual(legal_actions(state), (0, 1, 2, 3))

        after, _ = apply_select_pit(state, 0, auto_protected=False)
        after.assert_conserved()
        self.assertEqual(after.player, 1)

        # Settlement with 4 pits x 3 seeds: P2 has 15 seeds (3 extra = 1 full pit),
        # so P2 captures P1's boundary pit and fills it with 3 seeds (not 4).
        round_end = GameState(
            pits=(0, 0, 0, 0, 0, 1, 2, 0),
            player=0,
            captured=(9, 12),
            owners=(0, 0, 0, 0, 1, 1, 1, 1),
            protected=(False,) * 8,
            initial_total=24,
            seeds_per_pit=3,
        )
        ended, _ = begin_turn(round_end)
        settled, _ = settle_round(ended)
        self.assertEqual(settled.pits, (3,) * 8)
        self.assertEqual(settled.reserves, (0, 0))
        self.assertEqual(settled.owners.count(0), 3)
        self.assertEqual(settled.owners.count(1), 5)
        self.assertEqual(sum(settled.protected), 1)
        settled.assert_conserved()

        # With only 2 extra seeds (14 vs 10), P2 cannot fill a 3-seed pit, so no capture occurs.
        no_capture_end = GameState(
            pits=(0, 0, 0, 0, 0, 2, 0, 0),
            player=0,
            captured=(10, 12),
            owners=(0, 0, 0, 0, 1, 1, 1, 1),
            protected=(False,) * 8,
            initial_total=24,
            seeds_per_pit=3,
        )
        ended2, _ = begin_turn(no_capture_end)
        settled2, _ = settle_round(ended2)
        self.assertEqual(settled2.pits, (3,) * 8)
        self.assertEqual(settled2.owners, (0, 0, 0, 0, 1, 1, 1, 1))
        self.assertEqual(settled2.protected, (False,) * 8)
        settled2.assert_conserved()

        # Full conquest in 4x3: 24 seeds fills all 8 pits with 3 seeds each.
        conquest_end = GameState(
            pits=(0, 0, 0, 0, 0, 0, 0, 0),
            player=0,
            captured=(24, 0),
            owners=(0, 0, 0, 0, 1, 1, 1, 1),
            protected=(False,) * 8,
            initial_total=24,
            seeds_per_pit=3,
        )
        ended3, _ = begin_turn(conquest_end)
        settled3, _ = settle_round(ended3)
        self.assertIs(settled3.phase, Phase.GAME_END)
        self.assertEqual(settled3.terminal_reason, "conquest")
        self.assertEqual(settled3.winner, 0)
        self.assertEqual(settled3.pits, (3,) * 8)
        self.assertEqual(settled3.owners, (0,) * 8)
        settled3.assert_conserved()


if __name__ == "__main__":
    unittest.main()
