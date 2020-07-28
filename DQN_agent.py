import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.models import load_model
import json


class ReplayBuffer:
    def __init__(self, max_size, input_dims):
        self.mem_size = max_size
        self.mem_cntr = 0

        self.state_memory = np.zeros((self.mem_size, *input_dims), dtype=np.float32)
        self.new_state_memory = np.zeros((self.mem_size, *input_dims), dtype=np.float32)
        self.action_memory = np.zeros(self.mem_size, dtype=np.int32)
        self.reward_memory = np.zeros(self.mem_size, dtype=np.float32)
        self.terminal_memory = np.zeros(self.mem_size, dtype=np.int32)

    def store_transition(self, state, action, reward, state_, done):
        index = self.mem_cntr % self.mem_size
        self.state_memory[index] = state
        self.new_state_memory[index] = state_
        self.reward_memory[index] = reward
        self.action_memory[index] = action
        self.terminal_memory[index] = 1 - int(done)
        self.mem_cntr += 1

    def sample_buffer(self, batch_size):
        max_mem = min(self.mem_cntr, self.mem_size)
        batch = np.random.choice(max_mem, batch_size, replace=False)

        states = self.state_memory[batch]
        states_ = self.new_state_memory[batch]
        rewards = self.reward_memory[batch]
        actions = self.action_memory[batch]
        terminal = self.terminal_memory[batch]

        return states, actions, rewards, states_, terminal

    def save_memory(self):
        data = {'states': self.state_memory.tolist(),
                'states_:': self.new_state_memory.tolist(),
                'rewards': self.reward_memory.tolist(),
                'actions': self.action_memory.tolist(),
                'terminal': self.terminal_memory.tolist()
                }
        with open('buffer.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_memory(self):
        with open('buffer.json') as json_data:
            data = json.load(json_data)
        self.state_memory = data['states']
        self.new_state_memory = data['states_']
        self.reward_memory = data['rewards']
        self.action_memory = data['actions']
        self.terminal_memory = data['terminal']



def build_dqn(lr, n_actions, input_dims, fc1_dims, fc2_dims):
    model = keras.Sequential([
        keras.Input(shape=input_dims),
        keras.layers.Dense(fc1_dims, activation='relu'),
        keras.layers.Dense(fc2_dims, activation='relu'),
        keras.layers.Dense(n_actions, activation=None)])
    model.compile(optimizer=Adam(learning_rate=lr), loss='mean_squared_error')

    return model


class Agent:
    def __init__(self, lr, gamma, n_actions, epsilon, batch_size,
                 input_dims, epsilon_dec=1e-3, epsilon_end=0.1,
                 mem_size=1000000, fname='dqn_model.h5'):
        self.action_space = [i for i in range(n_actions)]
        self.gamma = gamma
        self.epsilon = epsilon
        self.eps_dec = epsilon_dec
        self.eps_min = epsilon_end
        self.batch_size = batch_size
        self.model_file = fname
        self.memory = ReplayBuffer(mem_size, input_dims)
        self.q_eval = build_dqn(lr, n_actions, input_dims, 128, 128)
        self.target_net = build_dqn(lr, n_actions, input_dims, 128, 128)
        self.target_net.set_weights(self.q_eval.get_weights())


    def store_transition(self, state, action, reward, new_state, done):
        self.memory.store_transition(state, action, reward, new_state, done)

    def choose_action(self, observation):
        if np.random.random() < self.epsilon:
            action = np.random.choice(self.action_space)
        else:
            state = np.array([observation])
            actions = self.q_eval.predict(state)
            action = np.argmax(actions)

        return action

    def soft_update(self, tau):
        policy_net_variables = self.q_eval.variables
        target_net_variables = self.target_net.variables
        for policy_net_variable, target_net_variable in zip(policy_net_variables, target_net_variables):
            target_net_variable.assign(tau*policy_net_variable + (1-tau)*target_net_variable)

    def hard_update(self):
        self.target_net.set_weights(self.q_eval.get_weights())

    def learn(self):
        if self.memory.mem_cntr < self.batch_size:
            return

        states, actions, rewards, states_, dones = self.memory.sample_buffer(self.batch_size)
        q_eval = self.q_eval.predict(states)
        q_next = self.target_net.predict(states_)
        q_target = np.copy(q_eval)
        batch_index = np.arange(self.batch_size, dtype=np.int32)
        q_target[batch_index, actions] = rewards + self.gamma * np.max(q_next, axis=1)*dones
        self.q_eval.train_on_batch(states, q_target)
        # self.soft_update(0.01)

        # self.epsilon = self.epsilon - self.eps_dec if self.epsilon > self.eps_min else self.eps_min

    def save_weights(self, checkpoint_name):
        print('Saving Weights.....')
        self.q_eval.save_weights('./checkpoints/'+checkpoint_name)

    def load_weights(self, checkpoint_path):
        self.q_eval.load_weights(checkpoint_path)

    def save_model(self, episode):
        print('Saving Model.....')
        self.q_eval.save('./models/' + str(episode) + self.model_file)

    def load_model(self, model_name):
        self.q_eval = load_model(model_name)
