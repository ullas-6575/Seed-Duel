"""Computer-player and move-advisor algorithms for Seed Duel."""

from .minimax import Recommendation, recommend_move
from .mcts import MCTSRecommendation, recommend_move as recommend_mcts_move
from .greedy import choose_move as choose_greedy_move

__all__ = [
    "MCTSRecommendation",
    "Recommendation",
    "choose_greedy_move",
    "recommend_move",
    "recommend_mcts_move",
]
