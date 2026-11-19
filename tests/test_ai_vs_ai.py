import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from seed_duel.ui.app import AI_MATCHUPS, SeedDuelApp


class AiVsAiUiTests(unittest.TestCase):
    def tearDown(self) -> None:
        pygame.quit()

    def test_required_matchups_map_both_players_to_the_right_algorithms(self) -> None:
        expected = (
            ("mcts", "minimax"),
            ("greedy", "mcts"),
            ("greedy", "minimax"),
        )
        self.assertEqual(AI_MATCHUPS, expected)

        app = SeedDuelApp()
        for matchup in expected:
            app.ai_matchup = matchup
            app.ai_level = None
            self.assertEqual(app._algorithm_for_player(0), matchup[0])
            self.assertEqual(app._algorithm_for_player(1), matchup[1])

    def test_ai_vs_ai_starts_p1_and_automatically_hands_off_to_p2(self) -> None:
        app = SeedDuelApp()
        app.menu_page = "matchup"
        app._start_game(ai_matchup=("greedy", "mcts"))

        self.assertTrue(app.game_started)
        self.assertEqual(app.ai_matchup, ("greedy", "mcts"))
        selected_players = [
            dict(event.data)["player"]
            for event in app.events
            if event.kind == "PitSelected"
        ]
        self.assertEqual(selected_players, [0])
        self.assertTrue(app.animation_steps)

        for _ in range(100):
            app._advance_animation()
            if app.current_step is not None:
                app.step_started_at = -10_000
            app._advance_animation()
            selected_players = [
                dict(event.data)["player"]
                for event in app.events
                if event.kind == "PitSelected"
            ]
            if selected_players == [0, 1]:
                break

        self.assertEqual(selected_players, [0, 1])
        self.assertIn("MCTS", app.message)

    def test_restart_keeps_the_selected_ai_matchup(self) -> None:
        app = SeedDuelApp()
        matchup = ("greedy", "minimax")
        app._start_game(ai_matchup=matchup)

        app._start_game(app.ai_level, app.ai_matchup)

        self.assertEqual(app.ai_matchup, matchup)
        self.assertEqual(app._algorithm_for_player(0), "greedy")
        self.assertEqual(app._algorithm_for_player(1), "minimax")


if __name__ == "__main__":
    unittest.main()
