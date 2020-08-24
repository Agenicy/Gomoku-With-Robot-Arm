import numpy as np
import random
from collections import defaultdict, deque # defaultdict = dict ; deque = double linked list
from game import Board, Game
from mcts_pure import MCTSPlayer as MCTS_Pure
from mcts_alphaZero import MCTSPlayer
from policy_value_net_keras import PolicyValueNet # Keras
import os, csv


# TrainPipeline -------------------------------------------------
class TrainPipeline:
    def current_model_now(self):
        return self.current_model.replace('.h5',f'_{self.i}.h5')
    
    def MCTS_levelup(self):
        self.mcts_player = MCTSPlayer(self.policy_value_net.policy_value_fn,
                                        c_puct=self.c_puct,
                                        n_playout=self.n_playout_training,
                                        is_selfplay=1)
    
    def __init__(self):
        """
        關於訓練的初始設置
        
        *補充說明
        kl 用於計算 lr (learning rate)
        """
        # run() -----------------------------------------------------------------------------------
        self.game_batch_num = -1  # 跑一次訓練的重複次數，負值代表不限制
        self.play_batch_size = 1    # 自我訓練的執行次數
        self.batch_size = 1024     # 每次要訓練的資料量，當 data_buffer 的資料累積到超過本數值就會更新 policy
        self.check_freq = 50        # 每訓練 ( check_freq ) 次就會與MCTS比賽
        self.save_freq = 50 # 每訓練 ( save_freq ) 次就會存檔
        
        # collect_selfplay_data() -----------------------------------------------------------------
        self.buffer_size = 10000
        self.data_buffer = deque(maxlen=self.buffer_size)
        self.kl_targ = 0.02
        
        # policy_update() -------------------------------------------------------------------------
        self.epochs = 5            # 每次更新的 epochs 數
        
        # board -----------------------------------------------------------------------------------
        self.board_width = 9        # 寬度
        self.board_height = 9       # 高度
        self.n_in_row = 5           # 多少顆連成一線獲得勝利
        self.board = Board(width=self.board_width,
                            height=self.board_height,
                            n_in_row=self.n_in_row)
        self.game = Game(self.board)
        
        # keras -----------------------------------------------------------------------------------
        self.learn_rate = 2e-3
        self.lr_multiplier = 1.0    # 基於KL自適應調整學習率
        self.temp = 1.0             # 溫度參數，太小會導致訓練不夠全面
        
        file_folder = './n400-o'
        model_tag = '9_9_5_o'
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
        self.loss_goal = 0 #! 存檔時 loss 小於此值會增加訓練時的 n_playout 次數
        self.pure_mcts_playout_num = 1000   # MCTS每一步的模擬次數，隨著模型強度提升
        self.pure_mcts_playout_num_upgrade = 1000   # MCTS隨著模型強度提升的模擬次數
        self.best_win_ratio = 0.0
        
        self.n_playout = 400 # 神經網路每一步的模擬次數，越大代表結果越依賴MCTS的技巧，否則依靠神經網路的判斷
        self.n_playout_training = 400 
        self.n_playout_growth = 0
        self.n_playout_limit = 2000
        self.MCTS_levelup()
        # -----------------------------------------------------------------------------------------
        
    def run(self):  
        try:
            reset = False
            if os.path.exists(self.progress) and os.path.exists(self.history_path) and not reset:
                with open( self.progress, 'r', newline='') as f:
                    rows = csv.DictReader(f)
                    for row in rows:
                        self.i = int(row['i'])
                        self.n_playout_training = int(row['n_playout'])
                        self.pure_mcts_playout_num = int(row['pure_mcts_playout_num'])
                        self.best_win_ratio = float(row['best_win_ratio'])
                    print(f'continue training: i = {self.i}, n_playout = {self.n_playout_training}, pure_mcts_playout_num = {self.pure_mcts_playout_num}, best_win_ratio = {self.best_win_ratio}')
            else:
                self.i = 0
                self.save_progress()
                with open(self.history_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['i',
                                    'n_playout',
                                    'kl',
                                    'lr_multiplier',
                                    'loss',
                                    'entropy',
                                    'explained_var_old',
                                    'explained_var_new'])
            
            print('model will be saved as: {}'.format(self.current_model_now()))
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
                        self.policy_value_net.save_model(self.current_model_now())
                        
                        with open( self.history_path, 'a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerows( self.history)
                        self.history = []
                        self.save_progress()
                    
                        if self.loss < self.loss_goal and self.pure_mcts_playout_num >= 5000:
                            #! MCTS 成長
                            self.n_playout_training += self.n_playout_growth
                            if self.n_playout_training > self.n_playout_limit:
                                self.n_playout_training = self.n_playout_limit
                            self.MCTS_levelup()
                            
                    # 檢查當前模型的性能，並保存模型參數
                    if (self.i) % self.check_freq == 0:
                        print("current self-play batch: {}".format(self.i))
                        win_ratio = self.policy_evaluate()
                        if win_ratio > self.best_win_ratio:
                            print("New best policy!!!!!!!!")
                            self.best_win_ratio = win_ratio
                            # update the best_policy
                            self.policy_value_net.save_model(self.best_model)
                            if (self.best_win_ratio == 1.0 and
                                    self.pure_mcts_playout_num < 10000):
                                self.pure_mcts_playout_num += self.pure_mcts_playout_num_upgrade
                                self.best_win_ratio = 0.0
                        # save
                        self.policy_value_net.save_model(self.current_model)
                        with open( self.history_path, 'a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerows( self.history)
                        self.history = []
                        self.save_progress()
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
            # todo: 解析這一段，原文位於 policy_value_net_keras 第93行
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
                             self.n_playout_training,
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
        
        if not os.path.exists(self.evaluate_path):
            with open( self.evaluate_path, 'w') as f:
                f.write('i,n_playout_training, num_playouts, win, lose, tie\n')
        with open( self.evaluate_path, 'a') as f:
            f.write(f'{self.i}, {self.n_playout_training}, {self.pure_mcts_playout_num}, {win_cnt[1]}, {win_cnt[2]}, {win_cnt[-1]}\n')
        return win_ratio

    def save_progress(self):
        with open( self.progress, 'w', newline='') as f:
            table = [['i', 'n_playout', 'pure_mcts_playout_num', 'best_win_ratio'],
                    [self.i, self.n_playout_training, self.pure_mcts_playout_num, self.best_win_ratio]]
            writer = csv.writer(f)
            writer.writerows(table)

if __name__ == '__main__':
    training_pipeline = TrainPipeline()
    training_pipeline.run()
    