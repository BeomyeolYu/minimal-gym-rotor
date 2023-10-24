import argparse

# Hyperparameters:
def create_parser():
    parser = argparse.ArgumentParser(description='Multi-agents Reinforcement Learning for Quadrotor UAV Control')
    parser.add_argument('--seed', default=1234, type=int, metavar='N', help='Random seed of Gym, PyTorch and Numpy (default: 1234)') 
    parser.add_argument('--max_steps', default=5000, type=int, help='Maximum number of steps in each episode (default: 2000)')
    parser.add_argument('--max_timesteps', default=int(5e6), type=int, help='Number of total timesteps (default: 7e6)')
    parser.add_argument("--eval_freq", default=1e4, type=int, help='How often (time steps) evaluate our trained model (default: 1e4)')       
    parser.add_argument('--render', default=False, type=bool, help='Simulation visualization (default: False)')
    # Coefficients in reward function:
    parser.add_argument('--Cx', default=7.0, type=float, metavar='G', help='Position coeff. (default: )')
    parser.add_argument('--Cv', default=0.25, type=float, metavar='G', help='Velocity coeff. (default: )')
    parser.add_argument('--CR', default=3.5, type=float, metavar='G', help='Attitude coeff. (default: )')
    parser.add_argument('--CW', default=0.25, type=float, metavar='G', help='Angular velocity coeff. (default: )')

    return parser