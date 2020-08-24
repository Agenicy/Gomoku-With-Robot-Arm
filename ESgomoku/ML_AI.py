import numpy as np

from policy_value_net_keras import PolicyValueNet  # Keras
from mcts_alphaZero import MCTSPlayer

class ML_AI(object):
    """
    AI player, use CNN
    """

    def __init__(self):
        self.player = None

    def set_player_ind(self, p):
        self.player = p

    def get_action(self, board):
        print("AI's turn")
        try:
            model_file = './best_model_9_9_5.h5'
            best_policy = PolicyValueNet(9, 9, model_file = model_file)
            mcts_player = MCTSPlayer(best_policy.policy_value_fn, c_puct=5, n_playout=400)

        except Exception as e:
            print(e)
            move = -1
        if move == -1 or move not in board.availables:
            print(f"invalid move: {move}")
            move = self.get_action(board)
        return move

    def __str__(self):
        return "AI {}".format(self.player)