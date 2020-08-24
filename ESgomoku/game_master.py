import socketio
import eventlet
eventlet.monkey_patch()

import eventlet.wsgi
from flask import Flask
import threading, time
BlockingThread = True

from game_engine import *

from mcts_alphaZero import MCTSPlayer
from policy_value_net_keras import PolicyValueNet  # Keras


now_pl, next_pl = 0, 1

# server
sio = socketio.Server()
app = Flask(__name__)

# thread
t = []

# client input queue
loc = []


# main game
game = None


def Reset():
    global t, loc, game, now_pl, next_pl, BlockingThread
    print("game restart.")
    score = None
    
    if len(t) > 0:
        BlockingThread = False
    game.board.__init__()
    game.board.current_player = game.board.players[game.start_player]  # start player
    loc = []
    now_pl, next_pl = 0, 1

# 連接成功
@sio.on('connect')
def on_connect(sid, environ):   
    global t, loc, BlockingThread
    print("connect ", sid)
    if len(t) == 0:
        print('new game.')
        t.append(threading.Thread(target=run))
        BlockingThread = True
        t[0].start()
    else:
        Reset()
        pass

# 斷開連結
@sio.on('disconnect')
def disconnect(sid):   
    global game, t
    print("disconnect ", sid)

@sio.on('restart')
def restart(sid, data):    
    Reset()

# 電腦落子
def send_step(location): 
    """傳遞location給unity
    
    Arguments:
        location {string}} -- 'x,y' 格式的字串
    """
    print(f'send step: {location}')   
    sio.emit(
        'ai_move', 
        data = {'loc':location}, 
        skip_sid=True) 
    eventlet.sleep(1)

# 冠軍出爐
def has_winner(winner): 
    print(winner)
    sio.emit(
        'winner', 
        data = {'winner':"winner is :{}".format(winner)}, 
        skip_sid=True) 
    eventlet.sleep(0)

# 玩家落子
@sio.on('pl_move')
def pl_move(sid, data):    
    if data:
        global loc
        print ('pl_move : {}'.format(data['loc'])) # loc
        loc.append(data['loc'])
    else:
        print ('Recieved Empty Data!')

# 允許玩家落子
def call_player():
    sio.emit(
        'pl_turn', 
        data = {}, # location = AI move (format: '5,5')
        skip_sid=True) 
    eventlet.sleep(0)

# 等待並從佇列中讀取玩家落子
def wait_client():
    global loc
    while len(loc) == 0:
        call_player()
        eventlet.sleep(1)
    else:
        ret = loc.pop(0) # loc
        after_get_loc(ret)
        
        return ret

def after_get_loc(loc):
    """任一方回傳落子後
    """
    # 交換先後手
    now_pl, next_pl = next_pl, now_pl


class Client(object):
    """
    human player, at Client
    """

    def __init__(self):
        self.player = None
        self.tag = 'Client'

    def set_player_ind(self, p):
        self.player = p

    def get_action(self, board):
        print("player's turn")
        try:
            location = wait_client()

            if isinstance(location, str):  # for python3
                location = [int(n, 10) for n in location.split(",")]
            move = board.location_to_move(location)

        except Exception as e:
            print(e)
            move = -1
        if move == -1 or move not in board.availables:
            print(f"invalid move: {move}")
            move = self.get_action(board)
        return move

    def __str__(self):
        return "Human {}".format(self.player)

def run():
    n = 5
    width, height = 9, 9
    model_file = './current_model_9_9_5.h5'
    try:
        global winner, game, BlockingThread
        board = Board(width=width, height=height, n_in_row=n)
        game = Game(board)

        # USE ML
        best_policy = PolicyValueNet(width, height, model_file = model_file)
        mcts_player = MCTSPlayer(best_policy.policy_value_fn, c_puct=5, n_playout=400)
        ###
        
        while True:
            BlockingThread = True # blocking
            print("new game starts")
            # set start_player=0 for human first
            winner = game.start_play(Client(), mcts_player, start_player=0, is_shown=1, send_step = send_step)
            has_winner(winner)
            eventlet.sleep(1)
            print("game end")
            while BlockingThread: # blocking
                eventlet.sleep(2)

    except KeyboardInterrupt:
        print('\n\rquit')

if __name__ == '__main__':
    app = socketio.Middleware(sio, app)
    eventlet.wsgi.server(eventlet.listen(('', 4567)), app)
