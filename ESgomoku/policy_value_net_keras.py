from keras.engine.topology import Input
from keras.engine.training import Model
from keras.layers.convolutional import Conv2D
from keras.layers.core import Activation, Dense, Flatten, Dropout
from keras.layers.merge import Add
from keras.layers.normalization import BatchNormalization
from keras.regularizers import l2
from keras.optimizers import Adam, RMSprop
import keras.backend as K
from keras.models import load_model

from keras.utils import np_utils

import numpy as np

import csv

import tensorflow as tf
config = tf.ConfigProto()
#config.gpu_options.per_process_gpu_memory_fraction = 0.4
config.gpu_options.allow_growth = True
session = tf.Session(config=config)

class PolicyValueNet():
    """policy-value network"""
    def __init__(self, board_width, board_height, model_file=None):
        self.board_width = board_width
        self.board_height = board_height 
        self.l2_const = 1e-4  # coef of l2 penalty 

        if model_file:
            print("[Notice] load model from file")
            self.model = load_model(model_file)
        else:
            print("[Notice] create model")
            self.create_policy_value_net()   
        self._loss_train_op()
        
    def create_policy_value_net(self):
        """create the policy value network """   
        in_x = network = Input((6, self.board_width, self.board_height))

        # conv layers
        network = Conv2D(filters=32, kernel_size=(3, 3), padding="same", data_format="channels_first", activation="relu", kernel_regularizer=l2(self.l2_const))(network)
        network = Conv2D(filters=64, kernel_size=(3, 3), padding="same", data_format="channels_first", activation="relu", kernel_regularizer=l2(self.l2_const))(network)
        network = Conv2D(filters=128, kernel_size=(3, 3), padding="same", data_format="channels_first", activation="relu", kernel_regularizer=l2(self.l2_const))(network)
        # action policy layers
        # 輸出落子機率
        policy_net = Conv2D(filters=4, kernel_size=(1, 1), data_format="channels_first", activation="relu", kernel_regularizer=l2(self.l2_const))(network)
        policy_net = Flatten()(policy_net)
        self.policy_net = Dense(self.board_width*self.board_height, activation="softmax", kernel_regularizer=l2(self.l2_const))(policy_net)
        # state value layers
        # 輸出局面評分
        value_net = Conv2D(filters=2, kernel_size=(1, 1), data_format="channels_first", activation="relu", kernel_regularizer=l2(self.l2_const))(network)
        value_net = Flatten()(value_net)
        self.value_net = Dense(1, activation="tanh", kernel_regularizer=l2(self.l2_const))(value_net)

        self.model = Model(in_x, [self.policy_net, self.value_net])
        
    def policy_value(self, state_input):
        state_input_union = np.array(state_input)
        results = self.model.predict_on_batch(state_input_union)
        return results
        
    def policy_value_fn(self, board):
        """
        input: board
        output: a list of (action, probability) tuples for each available action and the score of the board state
        """
        legal_positions = board.availables
        current_state = board.current_state()
        #act_probs, value = self.policy_value(current_state.reshape(-1, 6, self.board_width, self.board_height))
        act_probs, value = self.policy_value(current_state.reshape(-1, 4, self.board_width, self.board_height))
        act_probs = zip(legal_positions, act_probs.flatten()[legal_positions])
        return act_probs, value[0][0]

    def _loss_train_op(self):
        """
        Three loss terms：
        loss = (z - v)^2 + pi^T * log(p) + c||theta||^2
        """

        # get the train op   
        opt = RMSprop()
        losses = ['categorical_crossentropy', 'mean_squared_error']
        self.model.compile(optimizer=opt, loss=losses)

    

    def train_step(self, state_input, mcts_probs, winner, learning_rate):
        state_input_union = np.array(state_input)
        mcts_probs_union = np.array(mcts_probs)
        winner_union = np.array(winner)
        loss = self.model.evaluate(state_input_union, [mcts_probs_union, winner_union], batch_size=len(state_input), verbose=0)
        action_probs, _ = self.model.predict_on_batch(state_input_union)
        
        def self_entropy(probs):
            return -np.mean(np.sum(probs * np.log(probs + 1e-10), axis=1))
        entropy = self_entropy(action_probs)
        
        K.set_value(self.model.optimizer.lr, learning_rate)
        self.model.fit(state_input_union, [mcts_probs_union, winner_union], batch_size=len(state_input), verbose=0)
        
        return loss[0], entropy

    def get_policy_param(self):
        net_params = self.model.get_weights()        
        return net_params

    def save_model(self, model_file):
        """ save model to file """
        print("save model file")
        self.model.save(model_file)
