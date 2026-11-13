import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

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


if __name__ == "__main__":
    unittest.main()
