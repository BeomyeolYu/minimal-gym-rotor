"""
Minimal OpenAI Gym-based Environment for Quadrotor UAV
"""

import gymnasium as gym  # import gymnasium library for Gym environments.
import gym_rotor  # import your custom environment.

if __name__ == "__main__":

    # Make OpenAI Gym environment:
    env = gym.make('Quad-v0', render_mode="human")

    # Initialize environment:
    state = env.reset()  # reset the environment and obtain the initial state.
    done = False  # set done flag to False.
    total_reward = 0.  # Initialize the total reward.
    total_timesteps = 0  # Initialize the total steps

    # Training loop:
    while not done:
        total_timesteps += 1

        # Select action randomly from the action space:
        action = env.action_space.sample()  # TODO: This line should be replaced with your RL algos.

        # Take the action in the environment, observe next state, reward, and done flag:
        next_state, reward, done, _, _ = env.step(action)  # perform action.
        total_reward += reward  # accumulate the reward.

        # Visualization:
        env.render()  # render the current state of the environment (if rendering is enabled).

        if done:  # when the episode is complete,
            # Display the total accumulated reward:
            print(f"Total timestpes: {total_timesteps+1}, total Reward: {total_reward:.3f}")

            # Reset environment and total reward:
            state, done = env.reset(), False
            total_reward = 0 

    # Close environment:
    env.close()