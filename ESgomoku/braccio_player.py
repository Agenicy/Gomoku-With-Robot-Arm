import sys
sys.path.extend(['./serial', './Braccio'])
from usb import usb
from solver import solver
from time import sleep
from math import sqrt, atan, pi
import numpy as np
from pygame import mixer
# 常數修正項 ------------------------------------------------------
x_offset = 140 # 棋盤第一排中點左右偏差值 (絕對值)
block_length = 280/9 # 棋盤格子長度
block_width = 262/9

# 以下 板子正中央為 90 deg
waiting_action = [30, 0, 64, 178, 179, 0, 38] # 落子後的待機位置

ang_90 = 85 # 用90為基準修正，想要轉90度時的實際角度
y_center = 95 # 轉軸正中央相對於基準面的高度
y_150 = 108 # 用0為基準修正，150.0時相對於基準面的高度
y_400 = 118 # 用0為基準修正，400.0時相對於基準面的高度
y_board = -95 + 50 # 落子的高度
y_board_chess = -95 + 26 # 夾棋子的高度

# -----------------------------------------------------------------

s = solver()
u = usb()

#! port here
class Global():
    @staticmethod
    def port():
        return 'COM4'

def init(testMode):
    global u
    u.AddClient(Global.port(), 9600, show = False, testMode = testMode)
    u.Run()
    u.UserSend(data = waiting_action, port = Global.port())
    u.Wait(port=Global.port())

def EXcalibration():
    def ok(x):
        return x == 'Y'
    if not ok(input('Resetting Board, enter Y to continue:')):
        return
    
    if ok(input('校準高度嗎? (Y/N)')):
        start = True
        while start:
            global ang_90,y_center,y_150,y_400,y_board,y_board_chess,x_offset,block_length,block_width,wid_0,wid_8
            
            prepare = MakeData(x = -150, y= 0 ,ang = 90, catch = 1, EXC = True)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
            
            y_150 = int(input('請測量高度: ')) # 用0為基準修正，150.0時相對於基準面的高度
            
            
            prepare = MakeData(x = -400, y= 0 ,ang = 90, catch = 1, EXC = True)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
            y_400 = int(input('請測量高度:')) # 用0為基準修正，400.0時相對於基準面的高度
            
            y_board = -95 + 50 # 落子的高度
            prepare = MakeData(x = -200, y= y_board ,ang = 90, catch = 1)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
            while not ok(input('這樣的落子高度可以嗎? (Y/N)')):
                
                prepare = MakeData(x = -150, y= 0 ,ang = 90, catch = 1, EXC = True)
                u.UserSend(data = prepare, port = Global.port())
                u.Wait(port=Global.port())
                
                y_board = -95 + int(input(f'請輸入新的高度(剛才為{y_board+95}): '))
                prepare = MakeData(x = -200, y= y_board ,ang = 90, catch = 1)
                u.UserSend(data = prepare, port = Global.port())
                u.Wait(port=Global.port())
                
            
            y_board_chess = -95 + 30 # 夾棋子的高度
            prepare = MakeData(x = -150, y= y_board_chess ,ang = 90, catch = 1)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
            while not ok(input('這樣的夾棋子高度可以嗎? (Y/N)')):
                
                prepare = MakeData(x = -150, y= 0 ,ang = 90, catch = 1, EXC = True)
                u.UserSend(data = prepare, port = Global.port())
                u.Wait(port=Global.port())
                
                y_board_chess = -95 + int(input(f'請輸入新的高度(剛才為{y_board_chess+95}): '))
                prepare = MakeData(x = -150, y= y_board_chess ,ang = 90, catch = 1)
                u.UserSend(data = prepare, port = Global.port())
                u.Wait(port=Global.port())
                
            print('驗證結果')
            sleep(1)
            prepare = MakeData(x = -150, y=  y_board ,ang = 90, catch = 1)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
            sleep(1)
            prepare = MakeData(x = -400, y= y_board ,ang = 90, catch = 1)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
            sleep(1)
            if not ok(input('需要重新校準嗎? (Y/N)')):
                start = False
                    
    if ok(input('校準角度嗎? (Y/N)')):
        start = True
        while start:
            prepare = MakeData(x = -200, y= y_board ,ang = 0, catch = 1)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
            prepare = MakeData(x = -200, y= y_board ,ang = 90, catch = 1)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
            ang_90 = int(input('請輸入現在角度: ')) # 用90為基準修正，想要轉90度時的實際角度
            
            prepare = MakeData(x = -200, y= y_board + 40 ,ang = ang_function(0), catch = 1)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
            
            prepare = MakeData(x = -200, y= y_board + 40 ,ang = ang_function(90), catch = 1)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
            
            if ok(input('現在轉到90度了嗎? (Y/N)')):
                start = False
                        
    if ok(input('垂直距離校準嗎? (Y/N)')):
        x_offset = 150 # 棋盤第一排中點左右偏差值 (絕對值)
        print(f"x,y = {-x_offset}, {y_board}")
        prepare = MakeData(x = -x_offset, y= y_board ,ang = ang_function(90), catch = 1)
        u.UserSend(data = prepare, port = Global.port())
        u.Wait(port=Global.port())
        
        while not ok(input('現在到達「棋盤離手臂最近的那一列」的中央了嗎? (Y/N)')):
            prepare = MakeData(x = -150, y= 0 ,ang = ang_function(90), catch = 1, EXC = True)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
            
            x_offset = int(input(f'請輸入新的位置 (剛才為 {x_offset})')) # 棋盤第一排中點左右偏差值 (絕對值)
            
            prepare = MakeData(x = -x_offset, y= y_board+40 ,ang = ang_function(90), catch = 1)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
        
        
        block_length = 250/9 # 棋盤格子長度
        
        prepare = MakeData(x = -x_offset - 9 * block_length, y= y_board + 40 ,ang = ang_function(90), catch = 1)
        u.UserSend(data = prepare, port = Global.port())
        u.Wait(port=Global.port())
        
        while not ok(input('現在到達「棋盤離手臂最遠的那一列」的中央了嗎? (Y/N)')):
            prepare = MakeData(x = -300, y= 0 ,ang = ang_function(90), catch = 1, EXC = True)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
            
            block_length = -(int(input(f'請輸入新的位置 (剛才為 { x_offset - block_length * 9 })')) + x_offset)/9 # 棋盤第一排中點左右偏差值 (絕對值)
            print(f'新的棋盤格長度: {block_length}')
            
            prepare = MakeData(x = -x_offset - 9 * block_length, y= y_board + 40 ,ang = ang_function(90), catch = 1)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
            
        print('垂直校準結束')
       
    if ok(input('橫向距離校準嗎? (Y/N)')): 
        start = True
        while start:
            block_width = block_length # 棋盤格子寬度
            
            prepare = MakeData(x = -x_offset - 4 * block_length, y= y_board ,ang = ang_function(90), catch = 1)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
            
            if not ok(input('現在到達棋盤中央了嗎? (Y/N)')):
                print('請重新較驗棋盤長度')
                raise Exception('較驗失敗')
            
            def an(i):
                r, ang = LocToRec([i,0], EXC = True)
                prepare = MakeData(x = -r, y= y_board + 40,ang = ang, catch = 1)
                u.UserSend(data = prepare, port = Global.port())
                u.Wait(port=Global.port())
                x_at_0 = int(input('請輸入當前水平誤差(向外為正): '))
                
                r, ang = LocToRec([i,8], EXC = True)
                prepare = MakeData(x = -r, y= y_board + 40,ang = ang, catch = 1)
                u.UserSend(data = prepare, port = Global.port())
                u.Wait(port=Global.port())
                x_at_8 = int(input('請輸入當前水平誤差(向外為正): '))
                
                return x_at_0 + x_at_8
            
            wid_0 += -an(0)
            wid_8 += -an(8)
            print(f'棋盤寬度: 在第0列為{wid_0}, 第8列為{wid_8}')
            
            r, ang = LocToRec([0,0])
            prepare = MakeData(x = -r, y= 40,ang = ang, catch = 1)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
            r, ang = LocToRec([0,8])
            prepare = MakeData(x = -r, y= 40,ang = ang, catch = 1)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
            r, ang = LocToRec([8,0])
            prepare = MakeData(x = -r, y= 40,ang = ang, catch = 1)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
            r, ang = LocToRec([8,8])
            prepare = MakeData(x = -r, y= 40,ang = ang, catch = 1)
            u.UserSend(data = prepare, port = Global.port())
            u.Wait(port=Global.port())
            
            if ok(input('重新校準嗎? (Y/N)')):
                start = False
    
    print(f"""
          y_150 = {y_150}
          y_400 = {y_400}
          y_board = {y_board}
          y_board_chess = {y_board_chess}
          ang_90 = {ang_90}
          x_offset = {x_offset}
          block_length = {block_length}
          wid_0 = {wid_0}
          wid_8 = {wid_8}
          """)
    
    if not ok(input('儲存結果嗎? (Y/N)')):
        return
 
def y_function(x, y):
    return y - (x - (-150)) * (y_400 - y_150) / ((-400) - (-150)) - (y_150 - y_center) # Δy - Δx * 修正函數(實驗求得)

def MakeData(x, y,ang = 90,catch=0,time=20,EXC = False):
    """將距離xy轉換為指令"""
    if not EXC:
        y = y_function(x, y)
    t, o, p = s.Calc(x, y)
    if t != 0:
        return [time, ang, t, o, p, 0 , 30 + catch*30]
    else:
        return False
    
def ang_function(ang):
    return ang + (90-ang_90)

def LocToRec(loc = list, EXC = False):
    """
        將座標點轉換為機械手臂指令
        
        初始輸入 [y, x]:
        3*3 board's moves like:
            6 7 8
            3 4 5
            0 1 2
        and move 5's location is (1,2)
        
        (手臂的左上方[y, x]為[0, 8] 右上方為[0, 0]，向手臂為y pos)
        
        x轉為: 手臂左右位移
        y轉為: 手臂前後位移
    """
    
    x, y = loc[1], 8 - loc[0] # x, y swap
    x = x - 4 # 以手臂左方為正, 中央為 0
    x , y = int(x * block_width ), int(y * block_length) # 轉換為mm
    print(f'[LocToRec] x = {x}, y = {y}')
    y = x_offset + y # 轉換為 (板子)前後偏移量 + loc y 位移 
    
    r = sqrt(pow(x,2)+pow(y,2)) # 平面半徑
    if x == 0:
        # 正中央
        ang = ang_function(90)
    else:
        ang = ang_function(atan(y/x)*180/pi)
        if ang < 0:
            ang += 180
        if ang > 130:
            ang = 130
        elif ang < 50:
            ang = 50
            
    return r, ang # 弳度轉弧度
    

def catch(ang):
    # 夾棋子 --------------------------------------------------------------------
    # move
    x_0 = -150
    angle_0 = 0
    prepare = MakeData(x = x_0, y= y_board_chess ,ang = ang_function(angle_0), catch = 0, time = 10)
    u.UserSend(data = prepare, port = Global.port())
    u.Wait(port=Global.port())
    sleep(0.5) # wait for thread
    
    # catch
    prepare = MakeData(x = x_0, y= y_board_chess ,ang = ang_function(angle_0), catch = 1, time = 10)
    u.UserSend(data = prepare, port = Global.port())
    u.Wait(port=Global.port())
    sleep(0.5) # wait for thread
    
    # take up
    prepare = MakeData(x = x_0 - 15 , y= y_board + 40 ,ang = ang_function(angle_0), catch = 1)
    u.UserSend(data = prepare, port = Global.port())
    u.Wait(port=Global.port())
    sleep(0.5) # wait for thread
    
    # ready
    u.UserSend(data = MakeData(x = x_0, y= y_board + 40 ,ang = ang, catch = 1), port = Global.port())
    u.Wait(port=Global.port())
    sleep(0.1) # wait for thread
    # --------------------------------------------------------------------------

from mcts_alphaZero import MCTS, TreeNode, softmax
class BraccioPlayer(object):
    """AI player based on MCTS, act with braccio"""

    def __init__(self, policy_value_function,
                 c_puct=5, n_playout=2000, is_selfplay=0):
        self.mcts = MCTS(policy_value_function, c_puct, n_playout)
        self._is_selfplay = is_selfplay
        self.tag = 'AI'

    def set_player_ind(self, p):
        self.player = p

    def reset_player(self):
        self.mcts.update_with_move(-1)

    def get_action(self, board, temp=1e-2, return_prob=0):
        mixer.Channel(2).play(mixer.Sound('./Resources/ROBOT_SE/ai_turn.ogg'))
        sensible_moves = board.availables
        # the pi vector returned by MCTS as in the alphaGo Zero paper
        move_probs = np.zeros(board.width*board.height)
        if len(sensible_moves) > 0:
            acts, probs = self.mcts.get_move_probs(board, temp)
            move_probs[list(acts)] = probs
            if self._is_selfplay:
                # add Dirichlet Noise for exploration (needed for
                # self-play training)
                move = np.random.choice(
                    acts,
                    p=0.75*probs + 0.25*np.random.dirichlet(0.3*np.ones(len(probs)))
                )
                # update the root node and reuse the search tree
                self.mcts.update_with_move(move)
            else:
                # with the default temp=1e-3, it is almost equivalent
                # to choosing the move with the highest prob
                move = np.random.choice(acts, p=probs)
                # reset the root node
                self.mcts.update_with_move(-1)
#                location = board.move_to_location(move)
#                print("AI move: %d,%d\n" % (location[0], location[1]))

            def move_to_location(move):
                """
                3*3 board's moves like:
                6 7 8
                3 4 5
                0 1 2
                and move 5's location is (1,2)
                """
                h = move // 9
                w = move % 9
                return [h, w]
            
            print('braccio move: {}'.format(move_to_location(move)))
            
            self.Action(move_to_location(move))
            u.Wait(port=Global.port())

            if return_prob:
                return move, move_probs
            else:
                return move
        else:
            print("WARNING: the board is full")

    def __str__(self):
        return "MCTS {}".format(self.player)

    def Action(self, loc = list):
        """落子"""
        if u.client[Global.port()].state == 2:
            r, ang = LocToRec(loc)
            print(f'[LocToRec]:\n    r: {r} ang: {ang}')
            catch(ang)
            
            print("[Action]\n")
            serial = MakeData(x = -r, y= y_board ,ang = ang, catch = 1)
            
            if serial != False:
                u.UserSend(data = serial, port = Global.port())
                u.Wait(port=Global.port())
                sleep(0.1) # wait for thread
                
                serial2 = MakeData(x = -r, y= y_board ,ang = ang, catch = 0, time = 10)
                u.UserSend(data = serial2, port = Global.port())
                u.Wait(port=Global.port())
                sleep(0.1) # wait for thread
                
                end_action = MakeData(x = -r, y= y_board + 60 ,ang = ang, catch = 0, time = 10)
                u.UserSend(data = end_action, port = Global.port())
                u.Wait(port=Global.port())
                sleep(0.1) # wait for thread
            else:
                print("[ERROR] Position Invalid")
            u.UserSend(data = waiting_action, port = Global.port())
            u.Wait(port=Global.port())
        else:
            while u.client[Global.port()].state != 2:
                print(f"[ERROR] can't send because {port}.state is {self.client[Global.port()].state}")
                sleep(0.5)
            self.Action(loc)
    

if __name__ == '__main__':
    b = BraccioPlayer(None)
    init(False)
    debug_mode = False
    while True:
        if not debug_mode:
            word = input(f'Enter Data (y, x), use dot(".") to seprate...\n')
            try:
                word = word.replace('\n','').split('.')
                loc = [int(word[0]), int(word[1])]
                b.Action(loc)
            except Exception as e:
                if word == ['debug']:
                    debug_mode = True
                elif word == ['show']:
                    for x in range(0,9):
                        d = x%2
                        for y in range(d,9,2):
                            print(f'\n\n{x},{y}:\n')
                            b.Action([x,y])
                elif word == ['EXC']:
                    EXcalibration()
                            
            #word = input(f'Enter Data (y, x, ang), use dot(".") to seprate...').replace('\n','').split('.')
            #u.UserSend(data = MakeData(x = int(word[0]), y= int(word[1]) ,ang = int(word[2]), catch = int(word[3])), port = Global.port())
        else:
            debug = input('[DEBUG] enter(x.catch.ang)').replace('\n','')
            if debug != ['exit']:
                debug = debug.split('.')
                x_0 = int(debug[0])
                y = y_board if debug[1] == '0' else y_board_chess
                angle_0 = int(debug[2])
                prepare = MakeData(x = x_0 , y= y ,ang = ang_function(angle_0), catch = 0, time = 30)
                u.UserSend(data = prepare, port = Global.port())
                u.Wait(port=Global.port())
            else:
                debug_mode = False
                
            
    