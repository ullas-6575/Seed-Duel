"""Computer-player and move-advisor algorithms for Seed Duel."""

from .minimax import (
    ProtectedChoiceRecommendation,
    Recommendation,
    recommend_move,
    recommend_protected_choice,
)
from .mcts import (
    MCTSProtectedChoiceRecommendation,
    MCTSRecommendation,
    recommend_move as recommend_mcts_move,
    recommend_protected_choice as recommend_mcts_protected_choice,
)
from .greedy import (
    choose_move as choose_greedy_move,
    choose_protected_choice as choose_greedy_protected_choice,
)

__all__ = [
    "MCTSRecommendation",
    "MCTSProtectedChoiceRecommendation",
    "ProtectedChoiceRecommendation",
    "Recommendation",
    "choose_greedy_move",
    "choose_greedy_protected_choice",
    "recommend_move",
    "recommend_mcts_move",
    "recommend_mcts_protected_choice",
    "recommend_protected_choice",
]
