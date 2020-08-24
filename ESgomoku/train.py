import numpy as np
import random
from collections import defaultdict, deque # defaultdict = dict ; deque = double linked list
from game import Board, Game
from mcts_pure import MCTSPlayer as MCTS_Pure
from mcts_alphaZero import MCTSPlayer
from policy_value_net_keras import PolicyValueNet # Keras
import os, csv
import time


def send_msg(msg):
    with open(r'C:/Users/user/Documents/Github/DiscordBot/bot/msg.txt', 'a', encoding='utf8') as f:
        f.write('ml->' + msg + '\n')
send_msg('機器學習監督員開始監工喵!')

# TrainPipeline -------------------------------------------------
class TrainPipeline:
    def __init__(self):
        """
        關於訓練的初始設置
        
        *補充說明
        kl 用於計算 lr (learning rate)
        """
        # run() -----------------------------------------------------------------------------------
        self.game_batch_num = -1  # 跑一次訓練的重複次數，負值代表不限制
        self.play_batch_size = 1    # 自我訓練的執行次數
        self.batch_size = 4096      # 每次要訓練的資料量，當 data_buffer 的資料累積到超過本數值就會更新 policy
        self.check_freq = 500        # 每訓練 ( check_freq ) 次就會與MCTS比賽
        self.save_freq = 50 # 每訓練 ( save_freq ) 次就會存檔
        
        # collect_selfplay_data() -----------------------------------------------------------------
        self.buffer_size = 10000
        self.data_buffer = deque(maxlen=self.buffer_size)
        self.kl_targ = 0.02
        
        # policy_update() -------------------------------------------------------------------------
        self.epochs = 20            # 每次更新 lr 前應嘗試的訓練次數
        
        # board -----------------------------------------------------------------------------------
        self.board_width = 13        # 寬度
        self.board_height = 13       # 高度
        self.n_in_row = 5           # 多少顆連成一線獲得勝利
        self.board = Board(width=self.board_width,
                            height=self.board_height,
                            n_in_row=self.n_in_row)
        self.game = Game(self.board)
        
        # keras -----------------------------------------------------------------------------------
        self.learn_rate = 2e-3
        self.lr_multiplier = 1.0    # 基於KL自適應調整學習率
        self.temp = 2.0             # 溫度參數，太小會導致訓練不夠全面
        
        file_folder = './n400'
        model_tag = '13_13_5'
        self.current_model= f'{file_folder}/current_model_{model_tag}.h5'
        self.best_model= f'{file_folder}/best_model_{model_tag}.h5'
        init_model = self.current_model
        
        self.policy_value_net = PolicyValueNet(self.board_width,
                                        self.board_height,
                                        model_file = init_model if os.path.exists(init_model) else None)
        
        self.progress = file_folder + '/progress.csv'
        self.evaluate_path = file_folder + '/evaluate.csv'
        
        self.history_path = file_folder + '/history.csv'
        self.history = []
        
        # MCTS ------------------------------------------------------------------------------------
        self.c_puct = 5    # MCTS的搜索偏好
        self.n_playout = 400 # 神經網路每一步的模擬次數，越大代表結果越依賴MCTS的技巧，否則依靠神經網路的判斷
        
        self.loss_goal = 4.0 # 直到 loss 小於此值才會與MCTS比較，以節省訓練時間
        self.pure_mcts_playout_num = 1000   # MCTS每一步的模擬次數，隨著模型強度提升
        self.pure_mcts_playout_num_upgrade = 500   # MCTS隨著模型強度提升的模擬次數
        self.best_win_ratio = 0.0
        self.mcts_player = MCTSPlayer(self.policy_value_net.policy_value_fn,
                                        c_puct=self.c_puct,
                                        n_playout=self.n_playout,
                                        is_selfplay=1)
        
        self.flush_gate = [5.5, 5.0, 4.4, 4.0, 3.6, 3.2, 2.8, 2.6, 2.4, 2.2] # 當 loss 降低到一定程度後，清空之前舊模型生成的爛數據，以新數據重新訓練
        self.flushTimes = 0
        # -----------------------------------------------------------------------------------------
        
        
    def run(self):  
        try:
            reset = False
            if os.path.exists(self.progress) and os.path.exists(self.history_path) and not reset:
                with open( self.progress, 'r', newline='') as f:
                    rows = csv.DictReader(f)
                    for row in rows:
                        self.i = int(row['i'])
                        self.pure_mcts_playout_num = int(row['pure_mcts_playout_num'])
                        self.best_win_ratio = float(row['best_win_ratio'])
                        self.flushTimes = int(row['flushTimes'])
                    print(f'continue training: i = {self.i}, pure_mcts_playout_num = {self.pure_mcts_playout_num}, best_win_ratio = {self.best_win_ratio}, flushTimes = {self.flushTimes}')
            else:
                self.i = 0
                self.save_progress()
                with open(self.history_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['i',
                                    'kl',
                                    'lr_multiplier',
                                    'loss',
                                    'entropy',
                                    'explained_var_old',
                                    'explained_var_new'])
            
            while(self.i != self.game_batch_num):
                self.i += 1
                self.collect_selfplay_data(self.play_batch_size)
                print("batch i:{}, episode_len:{}".format(
                        self.i, self.episode_len))
                
                # 資料累積足夠，開始訓練
                if len(self.data_buffer) > self.batch_size:
                    # 更新 policy 並計算 loss
                    self.loss, entropy = self.policy_update()
                                    
                    if (self.i) % self.save_freq == 0:
                        # save
                        self.policy_value_net.save_model(self.current_model)
                        with open( self.history_path, 'a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerows( self.history)
                        self.history = []
                        self.save_progress()
                        
                    # 檢查當前模型的性能，並保存模型參數
                    if (self.i) % self.check_freq == 0 and self.loss < self.loss_goal:
                        print("current self-play batch: {}".format(self.i))
                        win_ratio = self.policy_evaluate()
                        if win_ratio > self.best_win_ratio:
                            print("New best policy!!!!!!!!")
                            self.best_win_ratio = win_ratio
                            # update the best_policy
                            self.policy_value_net.save_model(self.best_model)
                            if (self.best_win_ratio == 1.0 and
                                    self.pure_mcts_playout_num < 5000):
                                self.pure_mcts_playout_num += self.pure_mcts_playout_num_upgrade
                                self.best_win_ratio = 0.0
                        # save
                        self.policy_value_net.save_model(self.current_model)
                        with open( self.history_path, 'a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerows( self.history)
                        self.history = []
                        self.save_progress()
                        
                    # 清空爛數據
                    if self.flushTimes < len(self.flush_gate):
                        if self.loss < self.flush_gate[self.flushTimes]:
                            print(f'loss {self.loss} < flush gate {self.flush_gate[self.flushTimes]}, clear old data')
                            self.data_buffer.clear() # 清空 data buffer
                            self.flushTimes += 1
                else:
                    # 還未開始訓練，本次不算數
                    self.i -= 1
                
        except KeyboardInterrupt:
            print('\n\rquit')
                
    def collect_selfplay_data(self, n_games=1):
        """收集自我訓練數據進行訓練"""
        self.episode_len = []
        for i in range(n_games):
            winner, play_data = self.game.start_self_play(self.mcts_player,
                                                            temp=self.temp)
            # todo: 解析比賽資料的內容
            play_data = list(play_data)[:] # deepcopy 一個 play_data
            self.episode_len.append(len(play_data)) # 統計 episode_len
            # augment the data
            play_data = self.get_equi_data(play_data) # 對稱/鏡像複製，增加資料量
            self.data_buffer.extend(play_data) # 將 play_data 新增至 deque 右方
        self.episode_len = np.array(self.episode_len).mean() # 計算 episode_len 為所有 episode_len 的平均值 (用途?)

    def get_equi_data(self, play_data):
        """通過旋轉和翻轉增強數據集
        play_data：[（狀態，mcts_prob，winner_z），...，...]
        """
        extend_data = []
        for state, mcts_porb, winner in play_data:
            for i in [1, 2, 3, 4]:
                # rotate counterclockwise
                equi_state = np.array([np.rot90(s, i) for s in state])
                equi_mcts_prob = np.rot90(np.flipud(
                    mcts_porb.reshape(self.board_height, self.board_width)), i)
                extend_data.append((equi_state,
                                    np.flipud(equi_mcts_prob).flatten(),
                                    winner))
                # flip horizontally
                equi_state = np.array([np.fliplr(s) for s in equi_state])
                equi_mcts_prob = np.fliplr(equi_mcts_prob)
                extend_data.append((equi_state,
                                    np.flipud(equi_mcts_prob).flatten(),
                                    winner))
        return extend_data

    def policy_update(self):
        """更新價值網路， 回傳新的 loss, entropy"""
        mini_batch = random.sample(self.data_buffer, self.batch_size)
        
        # 分類資料 -----------------------------------------
        state_batch      = [data[0] for data in mini_batch]
        mcts_probs_batch = [data[1] for data in mini_batch]
        winner_batch     = [data[2] for data in mini_batch]
        # -------------------------------------------------
        
        old_probs, old_v = self.policy_value_net.policy_value(state_batch)
        """
            * 簡言之 old_probs, old_v = model.predict_on_batch(state_input)
            
            * predict_on_batch is a keras function
            > Returns predictions for a single batch of samples.

            > Arguments
            >     x: Input samples, as a Numpy array.

            > Returns
            >     Numpy array(s) of predictions.
        """
        
        for i in range(self.epochs):
            # 計算 loss 和 entropy
            loss, entropy = self.policy_value_net.train_step(
                    state_batch,
                    mcts_probs_batch,
                    winner_batch,
                    self.learn_rate*self.lr_multiplier)
            new_probs, new_v = self.policy_value_net.policy_value(state_batch)
            kl = np.mean(np.sum(old_probs * (
                    np.log(old_probs + 1e-10) - np.log(new_probs + 1e-10)),
                    axis=1)
            )
            if kl > self.kl_targ * 4:  # early stopping if D_KL diverges badly
                break
        # 自適應調整學習率
        if kl > self.kl_targ * 2 and self.lr_multiplier > 0.1:
            self.lr_multiplier /= 1.5
        elif kl < self.kl_targ / 2 and self.lr_multiplier < 10:
            self.lr_multiplier *= 1.5

        explained_var_old = (1 -
                                np.var(np.array(winner_batch) - old_v.flatten()) /
                                np.var(np.array(winner_batch)))
        explained_var_new = (1 -
                                np.var(np.array(winner_batch) - new_v.flatten()) /
                                np.var(np.array(winner_batch)))
        self.history.append([self.i,
                            kl,
                            self.lr_multiplier,
                            loss,
                            entropy,
                            explained_var_old,
                            explained_var_new])
        print(("kl:{:.5f},"
                "lr_multiplier:{:.3f},"
                "loss:{:.8f},"
                "entropy:{:.5f},"
                "explained_var_old:{:.3f},"
                "explained_var_new:{:.3f}"
                ).format(kl,
                        self.lr_multiplier,
                        loss,
                        entropy,
                        explained_var_old,
                        explained_var_new))
        return loss, entropy

    def policy_evaluate(self, n_games=10):
        """
        通過與純MCTS玩家對戰來評估經過培訓的策略網路
        注意：這僅用於監視培訓進度
        """
        current_mcts_player = MCTSPlayer(self.policy_value_net.policy_value_fn,
                                            c_puct=self.c_puct,
                                            n_playout=self.n_playout)
        pure_mcts_player = MCTS_Pure(c_puct=5,
                                        n_playout=self.pure_mcts_playout_num)
        win_cnt = defaultdict(int)
        for i in range(n_games):
            winner = self.game.start_play(current_mcts_player,
                                            pure_mcts_player,
                                            start_player=i % 2,
                                            is_shown=0)
            win_cnt[winner] += 1
        win_ratio = 1.0*(win_cnt[1] + 0.5*win_cnt[-1]) / n_games
        print("num_playouts:{}, win: {}, lose: {}, tie:{}".format(
                self.pure_mcts_playout_num,
                win_cnt[1], win_cnt[2], win_cnt[-1]))
        
        send_msg("num_playouts:{}, win: {}, lose: {}, tie:{}".format(
                self.pure_mcts_playout_num,
                win_cnt[1], win_cnt[2], win_cnt[-1]))
        
        if not os.path.exists(self.evaluate_path):
            with open( self.evaluate_path, 'w') as f:
                f.write('i, num_playouts, win, lose, tie')
        with open( self.evaluate_path, 'a') as f:
            f.write(f'{self.i}, {self.pure_mcts_playout_num}, {win_cnt[1]}, {win_cnt[2]}, {win_cnt[-1]}\n')
        return win_ratio

    def save_progress(self):
        with open( self.progress, 'w', newline='') as f:
            table = [['i', 'pure_mcts_playout_num', 'best_win_ratio', 'flushTimes'],
                    [self.i, self.pure_mcts_playout_num, self.best_win_ratio, self.flushTimes]]
            writer = csv.writer(f)
            writer.writerows(table)

if __name__ == '__main__':
    training_pipeline = TrainPipeline()
    training_pipeline.run()