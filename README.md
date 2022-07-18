# minimal-gym-rotor
Minimal OpenAI Gym-based environments for a quadrotor UAV

### ***Learn by Doing***

This repository contains OpenAI Gym-based environments for low-level control of quadrotor unmanned aerial vehicles. 
PyTorch implementations of DDPG and TD3 with ``gym-rotor`` can be found in [this repo](https://github.com/fdcl-gwu/gym-rotor).
To better understand **What Deep RL Do**, see [OpenAI Spinning UP](https://spinningup.openai.com/en/latest/index.html).
Please feel free to create new issues or pull requests for any suggestions and corrections. 


## Installation
It is recommended to create [Anaconda](https://www.anaconda.com/) environment with Python 3.
The official installation guide is available [here](https://docs.anaconda.com/anaconda/install/).
[Visual Studio Code](https://code.visualstudio.com/) in ``Anaconda Navigator`` is highly recommended.

1. Open your ``Anaconda Prompt`` and install major packages.
```bash
conda install -c conda-forge gym 
conda install pytorch torchvision torchaudio cudatoolkit=11.3 -c pytorch 
conda install -c conda-forge vpython
```
> Check out [Gym](https://anaconda.org/conda-forge/gym), [Pytorch](https://pytorch.org/), and [Vpython](https://anaconda.org/conda-forge/vpython).

2. Clone the repositroy.
```bash
git clone https://github.com/BeomyeolYu/minimal-gym-rotor.git
```


## TODO:
- [ ] Update README.md
- [ ] Tensorboard
- [ ] Gym Wrappers
- [ ] Evaluate un/pre-trained policy
- [ ] Test trained policy
- [ ] Plot graphs from saved data
- [ ] Resume training


## Reference:
- https://github.com/openai/gym
- https://github.com/ethz-asl/reinmav-gym
