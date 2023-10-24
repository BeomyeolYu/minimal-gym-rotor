# minimal-gym-rotor
Minimal OpenAI Gym-based environments for a quadrotor UAV

<img src="https://github.com/fdcl-gwu/gym-rotor/assets/50692767/4434e07f-48ae-4d96-8407-3d815e913ca7" width=50%>


### ***Learn by Doing***

This repository contains OpenAI Gym-based environments for low-level control of quadrotor unmanned aerial vehicles (UAVs).
This repo is designed to serve as an educational platform for those interested in building Gym-based environments.
To better understand **What Deep RL Do**, see [OpenAI Spinning UP](https://spinningup.openai.com/en/latest/index.html).
Please feel free to create new issues or pull requests for any suggestions and corrections. 


## Installation
It is recommended to create [Anaconda](https://www.anaconda.com/) environment with Python 3.
The official installation guide is available [here](https://docs.anaconda.com/anaconda/install/).
Also, [Visual Studio Code](https://code.visualstudio.com/) in ``Anaconda Navigator`` is highly recommended.

1. Open your ``Anaconda Prompt`` and install major packages.
```bash
conda install -c conda-forge gymnasium
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
conda install -c conda-forge vpython
```
> Check out [Gym](https://anaconda.org/conda-forge/gym), [Pytorch](https://pytorch.org/), and [Vpython](https://anaconda.org/conda-forge/vpython).

2. Clone the repositroy.
```bash
git clone https://github.com/BeomyeolYu/minimal-gym-rotor.git
```

## Environments
Consider a quadrotor UAV below:

<img src="https://github.com/fdcl-gwu/gym-rotor/assets/50692767/7d683754-fd60-41e0-a29f-12e26ea279a8" width=40%>

The position and the velocity of the quadrotor are represented by $x \in \mathbb{R}^3$ and $v \in \mathbb{R}^3$, respectively.
The attitude is defined by the rotation matrix $R \in SO(3) = \lbrace R \in \mathbb{R}^{3\times 3} | R^T R=I_{3\times 3}, \mathrm{det}[R]=1 \rbrace$, that is the linear transformation of the representation of a vector from the body-fixed frame $\lbrace \vec b_{1},\vec b_{2},\vec b_{3} \rbrace$ to the inertial frame $\lbrace \vec e_1,\vec e_2,\vec e_3 \rbrace$. 
The angular velocity vector is denoted by $\Omega \in \mathbb{R}^3$.
From the thrust of each motor $(T_1,T_2,T_3,T_4)$, the total thrust $f = \sum{}_{i=1}^{4} T_i \in \mathbb{R}$ and the total moment $M \in \mathbb{R}^3$ resolved in the body-fixed frame can be represented.

| Env IDs | Description |
| :---: | --- |
| `Quad-v0` | The state and the action are given by $s = (e_x, e_v, R, \Omega)$ and $a = (T_1, T_2, T_3, T_4)$.|

where the error terms $e_x, e_v$, and $e_\Omega$ represent the errors in position, velocity, and angular velocity, respectively.

## Training RL Agents
If you're interested in training RL agents in the quadrotor environments provided here, we recommend visiting [github.com/fdcl-gwu/gym-rotor](https://github.com/fdcl-gwu/gym-rotor).
This companion repository focuses on training RL agents using PyTorch implementations of DDPG and TD3 and offers additional resources for in-depth experimentation.


## Reference:
- https://github.com/openai/gym
- https://github.com/ethz-asl/reinmav-gym
