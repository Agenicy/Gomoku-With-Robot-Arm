
import numpy as np

class const():
    #default
    default_width = 9
    default_height = 9
    default_n_in_row = 5

    #nn input
    #black, white, last, who_first
    num_of_input_array = 4

    #ui
    black_chess = 'X'
    white_chess = 'O'
    empty_place = '-'
    space = ' '
    row_col = ['0','1','2','3','4','5','6','7','8','9','A','B','C','D','E','F']
    
    #AI
    deep = 1



class Board(object):
    """internal board for the game"""

    def __init__(self, **kwargs):
        self.width = int(kwargs.get('width', const.default_width))
        self.height = int(kwargs.get('height', const.default_height))
        # board states stored as a dict,
        # key: move as location on the board,
        # value: player as pieces type
        self.states = {}
        # need how many pieces in a row to win
        self.n_in_row = int(kwargs.get('n_in_row', const.default_n_in_row))
        self.players = [1, 2]  # player1 and player2

    def init_board(self, start_player=0):
        if self.width < self.n_in_row or self.height < self.n_in_row:
            raise Exception('board width and height can not be '
                            'less than {}'.format(self.n_in_row))
        self.current_player = self.players[start_player]  # start player
        # keep available moves in a list
        self.availables = list(range(self.width * self.height))
        self.states = {}
        self.last_move = -1

    def move_to_location(self, move):
        """
        3*3 board's moves like:
        6 7 8
        3 4 5
        0 1 2
        and move 5's location is (1,2)
        """
        h = move // self.width
        w = move % self.width
        return [h, w]

    def location_to_move(self, location):
        if len(location) != 2:
            return -1
        h = location[0]
        w = location[1]
        move = h * self.width + w
        if move not in range(self.width * self.height):
            return -1
        return move

    def current_state(self):
        """return the board state from the perspective of the current player.
        state shape: ( const.num_of_input_array )*width*height
        """

        square_state = np.zeros((const.num_of_input_array , self.width, self.height))
        if self.states:
            moves, players = np.array(list(zip(*self.states.items())))
            move_curr = moves[players == self.current_player]
            move_oppo = moves[players != self.current_player]
            square_state[0][move_curr // self.width,
                            move_curr % self.height] = 1.0
            square_state[1][move_oppo // self.width,
                            move_oppo % self.height] = 1.0
            # indicate the last move location
            square_state[2][self.last_move // self.width,
                            self.last_move % self.height] = 1.0
        if len(self.states) % 2 == 0:
            square_state[3][:, :] = 1.0  # indicate the colour to play
        return square_state[:, ::-1, :]

    def do_move(self, move):
        self.states[move] = self.current_player
        self.availables.remove(move)
        self.current_player = (
            self.players[0] if self.current_player == self.players[1]
            else self.players[1]
        )
        self.last_move = move

    def has_a_winner(self):
        width = self.width
        height = self.height
        states = self.states
        n = self.n_in_row

        moved = list(set(range(width * height)) - set(self.availables))
        if len(moved) < self.n_in_row *2-1:
            return False, -1

        for m in moved:
            h = m // width
            w = m % width
            player = states[m]

            if (w in range(width - n + 1) and
                    len(set(states.get(i, -1) for i in range(m, m + n))) == 1):
                return True, player

            if (h in range(height - n + 1) and
                    len(set(states.get(i, -1) for i in range(m, m + n * width, width))) == 1):
                return True, player

            if (w in range(width - n + 1) and h in range(height - n + 1) and
                    len(set(states.get(i, -1) for i in range(m, m + n * (width + 1), width + 1))) == 1):
                return True, player

            if (w in range(n - 1, width) and h in range(height - n + 1) and
                    len(set(states.get(i, -1) for i in range(m, m + n * (width - 1), width - 1))) == 1):
                return True, player

        return False, -1

    def game_end(self):
        """Check whether the game is ended or not"""
        win, winner = self.has_a_winner()
        if win:
            return True, winner
        elif not len(self.availables):
            return True, -1
        return False, -1

    def get_current_player(self):
        return self.current_player


class Game(object):
    """game server"""
    # 用於停止thread
    running = True
    def Stop(self):
        self.running = False

    def isNotRunning(self):
        return not self.running

    def __init__(self, board, **kwargs):
        self.board = board

    def graphic(self, board, player1, player2):
        """Draw the board and show game info"""
        width = board.width
        height = board.height

        print("Player", player1, "with X".rjust(3))
        print("Player", player2, "with O".rjust(3))
        print('')
        for x in range(width):
            print("{}{}{}".format(const.space,const.space,const.row_col[x]), end='')
        print('\r\n')
        for i in range(height - 1, -1, -1):
            print("{}".format(const.row_col[i]), end='')
            for j in range(width):
                loc = i * width + j
                p = board.states.get(loc, -1)
                if p == player1:
                    print('{}{}{}'.format(const.space,const.black_chess,const.space), end='')
                elif p == player2:
                    print('{}{}{}'.format(const.space,const.white_chess,const.space), end='')
                else:
                    print('{}{}{}'.format(const.space,const.empty_place,const.space), end='')
            print('\r\n')

    def start_play(self, player1, player2, start_player=0, is_shown=1, send_step = None):
        """start a game between two players"""
        if start_player not in (0, 1):
            raise Exception('start_player should be either 0 (player1 first) '
                            'or 1 (player2 first)')
        self.start_player = start_player # for restart game
        self.board.init_board(start_player)
        p1, p2 = self.board.players
        player1.set_player_ind(p1)
        player2.set_player_ind(p2)
        players = {p1: player1, p2: player2}
        if is_shown:
            self.graphic(self.board, player1.player, player2.player)
        while self.running:
            try:
                current_player = self.board.get_current_player()
                player_in_turn = players[current_player]
                move = player_in_turn.get_action(self.board)
                self.board.do_move(move)
                
                if player_in_turn.tag == 'AI':
                    location = f'{int((move - move % const.default_width) /const.default_width)},{move % const.default_width}'
                    
                    ret_probs = ''
                    for prob in player_in_turn.mcts.probs:
                        for p in prob.tolist():
                            ret_probs += f'{p},'
                    
                    send_step(location, ret_probs[:-1] )
                
                if is_shown:
                    self.graphic(self.board, player1.player, player2.player)
                end, winner = self.board.game_end()
                if end:
                    if is_shown:
                        if winner != -1:
                            print("Game end. Winner is", players[winner])
                        else:
                            print("Game end. Tie")
                    return winner
            except KeyboardInterrupt:
                return 'duel'
