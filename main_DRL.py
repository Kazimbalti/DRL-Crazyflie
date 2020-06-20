from DQN_agent import Agent
import numpy as np
import gym
from Utils import plotLearning
import tensorflow as tf
import gym_airsim.envs


if __name__ == '__main__':
    tf.compat.v1.disable_eager_execution()
    env_name = 'AirSimEnv-v42'
    env = gym.make(env_name)
    lr = 0.0005
    n_games = 200
    agent = Agent(gamma=0.99, epsilon=1.0, lr=lr, input_dims=env.observation_space.shape,
                  n_actions=env.action_space.n, mem_size=100000, batch_size=64,
                  epsilon_end=0.01, fname=env_name+'.h5')
    scores = []
    eps_history = []
    latest = tf.train.latest_checkpoint('checkpoints')
    agent.load_weights(latest)
    for i in range(n_games):
        done = False
        score = 0
        observation = env.reset()
        while not done:
            action = agent.choose_action(observation)
            observation_, reward, done, info = env.step(action)
            score += reward
            agent.store_transition(observation, action, reward, observation_, done)
            observation = observation_
            agent.learn()
        eps_history.append(agent.epsilon)
        scores.append(score)
        avg_score = np.mean(scores[-100:])
        print('episode: ', i, 'score %.2f' % score,
              'average_score %.2f' % avg_score,
              'epsilon %.2f' % agent.epsilon)
    agent.save_weights('episode' + str(i))

    filename = env_name + '.png'
    x = [i+1 for i in range(n_games)]
    plotLearning(x, scores, eps_history, filename)