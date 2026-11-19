import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from seed_duel.model import GameState, Phase
from seed_duel.rules import apply_protected_choice, apply_select_pit
from seed_duel.ui.app import SeedDuelApp


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
        for _ in range(30):
            app._advance_animation()
            if app.current_step:
                app.step_started_at = -10_000
            app._advance_animation()
            if not app.current_step and not app.animation_steps:
                break

        self.assertEqual(app.display_state, final)

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


if __name__ == "__main__":
    unittest.main()
