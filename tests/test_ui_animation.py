import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from seed_duel.model import GameState, Phase
from seed_duel.rules import apply_protected_choice, apply_select_pit
from seed_duel.ui.app import (
    ACCOUNT_PIT_CENTERS,
    BOARD_RECT,
    PLAYER_LABEL_POSITIONS,
    SeedDuelApp,
)


def later_loop_and_last_choice() -> tuple[GameState, GameState]:
    state = GameState(
        pits=(3, 1, 0, 1, 0, 0, 2, 1, 0, 0),
        player=0,
        captured=(12, 12),
        reserves=(8, 0),
        owners=(0, 0, 0, 0, 0, 0, 1, 1, 1, 0),
        protected=(False, False, False, False, False, True, False, False, False, True),
        initial_total=40,
        round_number=2,
    )
    result, _ = apply_select_pit(state, 1, auto_protected=False)
    last_choice = result
    while result.phase is Phase.DROP_SKIP:
        last_choice = result
        result, _ = apply_protected_choice(result, drop=False)
    return result, last_choice


class UiAnimationTests(unittest.TestCase):
    def tearDown(self) -> None:
        pygame.quit()

    def test_turn_events_play_back_to_the_final_engine_state(self) -> None:
        app = SeedDuelApp()
        before = app.state
        final, events = apply_select_pit(before, 0)
        app.state = final
        app._queue_turn_animation(before, final, events)

        # Selection, two pickups, eight drops and one capture are animated.
        self.assertEqual(len(app.animation_steps), 12)
        capture_step = app.animation_steps[-1]
        self.assertEqual(capture_step.event.kind, "SeedsCaptured")
        self.assertEqual(capture_step.source_index, 1)
        self.assertGreater(capture_step.duration_ms, 360)
        for _ in range(30):
            app._advance_animation()
            if app.current_step:
                app.step_started_at = -10_000
            app._advance_animation()
            if not app.current_step and not app.animation_steps:
                break

        self.assertEqual(app.display_state, final)

    def test_protected_pits_render_with_locks_and_chains(self) -> None:
        app = SeedDuelApp()
        app.display_state = app.state.evolve(
            owners=(0, 0, 0, 1, 1, 1, 1, 1, 1, 1),
            protected=(False, False, False, True, True, False, False, False, False, False),
        )

        app._draw_board()

        first = app._pit_by_index(3).center
        second = app._pit_by_index(4).center
        midpoint = ((first[0] + second[0]) // 2, (first[1] + second[1]) // 2)
        self.assertNotEqual(app.screen.get_at(midpoint)[:3], (207, 220, 196))

    def test_captured_seeds_fly_into_the_acting_players_account_pit(self) -> None:
        app = SeedDuelApp()
        before = app.state
        final, events = apply_select_pit(before, 0)
        app.state = final
        app._queue_turn_animation(before, final, events)
        capture_step = app.animation_steps[-1]
        app.current_step = capture_step
        app.animation_steps = []
        app.display_state = capture_step.before
        app.step_started_at = pygame.time.get_ticks() - capture_step.duration_ms // 2

        with patch.object(app, "_draw_seed_flight") as draw_flight:
            app._draw_flying_seed()

        self.assertTrue(draw_flight.called)
        self.assertTrue(
            all(call.args[1] == ACCOUNT_PIT_CENTERS[0] for call in draw_flight.call_args_list)
        )

    def test_ai_executes_its_protected_skip_choice(self) -> None:
        app = SeedDuelApp()
        state = GameState(
            pits=(4, 4, 4, 4, 4, 0, 4, 4, 4, 4),
            player=1,
            owners=(0, 0, 0, 0, 1, 1, 1, 1, 1, 1),
            protected=(False, False, False, False, False, True, False, False, False, False),
            reserves=(4, 0),
            initial_total=40,
        )
        # Stop Player 2's legal turn at that encounter, then let Easy AI choose.
        pending, _ = apply_select_pit(state, 4, auto_protected=False)
        self.assertIs(pending.phase, Phase.DROP_SKIP)

        app.state = pending
        app.display_state = pending
        app.ai_level = "easy"
        app.game_started = True
        app._play_ai_turn()

        self.assertTrue(any(event.kind == "ProtectedPitSkipped" for event in app.events))
        self.assertIn("Skip", app.message)

    def test_human_loop_dialog_can_try_the_alternate_choice(self) -> None:
        app = SeedDuelApp()
        loop_state, checkpoint = later_loop_and_last_choice()
        app.state = loop_state
        app.display_state = loop_state
        app.loop_avoid_state = checkpoint
        app.loop_previous_choice = False

        app._open_later_loop_dialog_if_available()

        self.assertTrue(app.loop_choice_offer)
        self.assertIn("Settling now gives", app.loop_dialog_message)
        self.assertIn("currently projects", app.loop_dialog_message)
        app._resolve_later_loop_offer(avoid=True)
        self.assertFalse(app.loop_choice_offer)
        self.assertIs(app.state.phase, Phase.SELECT)
        self.assertFalse(app.state.loop_resolution_available)
        self.assertTrue(
            any(event.kind == "LoopAvoidanceSelected" for event in app.events)
        )

    def test_human_loop_dialog_can_end_and_settle_immediately(self) -> None:
        app = SeedDuelApp()
        loop_state, checkpoint = later_loop_and_last_choice()
        app.state = loop_state
        app.display_state = loop_state
        app.loop_avoid_state = checkpoint
        app.loop_previous_choice = False
        app._open_later_loop_dialog_if_available()

        app._resolve_later_loop_offer(avoid=False)

        self.assertFalse(app.loop_choice_offer)
        self.assertIn(app.state.phase, (Phase.ROUND_END, Phase.GAME_END))
        self.assertFalse(app.state.loop_resolution_available)
        self.assertGreater(sum(app.round_scores), 0)
        self.assertTrue(any(event.kind == "SeedsSettled" for event in app.events))

    def test_player_board_labels_are_visible_and_do_not_overlap_pits(self) -> None:
        app = SeedDuelApp()
        for matchup in (None, ("mcts", "minimax"), ("greedy", "minimax")):
            app.ai_matchup = matchup
            for player in (0, 1):
                label = app._player_name(player).upper()
                width, height = app.font.size(label)
                x, y = PLAYER_LABEL_POSITIONS[player]
                label_rect = pygame.Rect(x, y, width, height)
                self.assertTrue(BOARD_RECT.contains(label_rect))
                for pit in app.pits:
                    shadow_rect = pit.rect.move(0, 10)
                    marker_rect = pygame.Rect(pit.center[0] - 22, pit.rect.y - 13, 44, 20)
                    self.assertFalse(label_rect.colliderect(pit.rect))
                    self.assertFalse(label_rect.colliderect(shadow_rect))
                    self.assertFalse(label_rect.colliderect(marker_rect))

    def test_ai_hint_is_manual_and_limited_to_three_per_round(self) -> None:
        app = SeedDuelApp()
        app._start_game(ai_level="easy")

        # Advice does not appear automatically.
        self.assertIsNone(app.advice)
        self.assertEqual(app.hints_remaining, [3, 3])

        # Clicking the hint button once gives advice and consumes 1 hint.
        app._handle_click(app.hint_rect.center)
        self.assertIsNotNone(app.advice)
        self.assertEqual(app.hints_remaining[0], 2)

        # Clicking again on the same turn does not consume another hint.
        app._handle_click(app.hint_rect.center)
        self.assertEqual(app.hints_remaining[0], 2)

        # Consume remaining 2 hints on subsequent turns in the same round.
        app.advice = None
        app._handle_click(app.hint_rect.center)
        self.assertEqual(app.hints_remaining[0], 1)
        app.advice = None
        app._handle_click(app.hint_rect.center)
        self.assertEqual(app.hints_remaining[0], 0)

        # 4th request in the same round is blocked.
        app.advice = None
        app._handle_click(app.hint_rect.center)
        self.assertIsNone(app.advice)
        self.assertEqual(app.hints_remaining[0], 0)
        self.assertIn("no AI suggestions left", app.message)

        # Continuing to a new round resets hints to 3.
        app._apply_round_choice("continue")
        self.assertIsNone(app.advice)
        self.assertEqual(app.hints_remaining, [3, 3])


if __name__ == "__main__":
    unittest.main()
