"""
Minimal OpenAI Gym-based Environment for Quadrotor UAV
"""

import gym
import gym_rotor
import numpy as np

if __name__ == "__main__":

    # OpenAI gym environment:
    env = gym.make('Quad-v0') 

    # Initialize environment:
    state = env.reset()
    done = False
    total_reward = 0

    # Training loop.
    while not done:
        # Select action randomly:
        action = env.action_space.sample() 

        # Perform action:
        next_state, reward, done, _ = env.step(action)
        total_reward += reward

        # Visualization:
        env.render()

        if done: 
            print(f"Total Reward: {total_reward:.3f}")

            # Reset environment and total reward.
            state = env.reset() 
            #done = False
            total_reward = 0 

    # Close environment:
    env.close()