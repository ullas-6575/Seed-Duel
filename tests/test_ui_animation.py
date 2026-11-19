import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from seed_duel.model import GameState, Phase
from seed_duel.rules import apply_select_pit
from seed_duel.ui.app import SeedDuelApp


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


if __name__ == "__main__":
    unittest.main()
