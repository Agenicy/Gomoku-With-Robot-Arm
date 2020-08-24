from game_engine import *
import numpy as np
from raw_dataset.see_raw_data import Analyze


class Human(object):
    """
    human player
    """

    def __init__(self):
        self.player = None

    def set_player_ind(self, p):
        self.player = p

    def get_action(self, board):
        try:
            location = input("Your move: ")
            if isinstance(location, str):  # for python3
                location = [int(n, 10) for n in location.split(",")]
            move = board.location_to_move(location)
        except Exception as e:
            move = -1
        if move == -1 or move not in board.availables:
            print(f"invalid move:{move}")
            move = self.get_action(board)
        return move

    def __str__(self):
        return "Human {}".format(self.player)

class DataPlayer(object):
    """
    dataset player
    """
    ana = Analyze()

    def __init__(self):
        self.player = None

    def set_player_ind(self, p):
        self.player = p

    def get_action(self, board):
        try:
            next = self.ana.Shot()
            if(next[0] == 0):
                input( "winner is {}".format( {0:"black",1:"white"}.get(next[1]) ) )
            elif(next[0] == -1):
                input('No More Steps.')
            else:
                location = next
            if isinstance(location, str):  # for python3
                location = [int(n, 10) for n in location.split(",")]
            move = board.location_to_move(location)
        except Exception as e:
            move = -1
        if move == -1 or move not in board.availables:
            print(f"invalid move: {move}")
            move = self.get_action(board)
        return move

    def __str__(self):
        return "Human {}".format(self.player)

def run():
    n = 5
    width, height = 9,9
    try:
        board = Board(width=width, height=height, n_in_row=n)
        game = Game(board)

        # set start_player=0 for human first
        game.start_play(Human(), Human(), start_player=1, is_shown=1)
    except KeyboardInterrupt:
        print('\n\rquit')


if __name__ == '__main__':
    run()
