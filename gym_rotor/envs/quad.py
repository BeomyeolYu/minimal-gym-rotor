import gym
from gym import spaces
from gym.utils import seeding

import numpy as np
from numpy import linalg
from numpy.linalg import inv
from math import cos, sin, atan2, sqrt, pi
from scipy.integrate import odeint, solve_ivp

class QuadEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self): 

        # Quadrotor parameters:
        self.m = 1.735 # mass of quad, [kg]
        self.d = 0.228 # arm length, [m]
        self.J = np.diag([0.02, 0.02, 0.04]) # inertia matrix of quad, [kg m2]
        self.C_TQ = 0.0135 # torques and thrusts coefficients
        self.g = 9.81  # standard gravity

        # Force and Moment:
        self.f = self.m * self.g # magnitude of total thrust to overcome  
                                 # gravity and mass (No air resistance), [N]
        self.f_each = self.m * self.g / 4.0 # thrust magnitude of each motor, [N]
        self.min_force = 1.0 # minimum thrust of each motor, [N]
        self.max_force = 2 * self.f_each # maximum thrust of each motor, [N]
        self.f1 = self.f_each # thrust of each 1st motor, [N]
        self.f2 = self.f_each # thrust of each 2nd motor, [N]
        self.f3 = self.f_each # thrust of each 3rd motor, [N]
        self.f4 = self.f_each # thrust of each 4th motor, [N]

        self.M  = np.zeros(3) # magnitude of moment on quadrotor, [Nm]

        # Simulation parameters:
        self.dt = 0.005 # discrete time step, t(2) - t(1), [sec]
        self.ode_integrator = "solve_ivp" # or "euler", ODE solvers
        self.R2D = 180/pi # [rad] to [deg]
        self.D2R = pi/180 # [deg] to [rad]
        self.e3 = np.array([0.0, 0.0, 1.0])[np.newaxis].T 

        # Commands:
        self.xd     = np.array([0.0, 0.0, -2.0]) # desired tracking position command, [m] 
        self.xd_dot = np.array([0.0, 0.0, 0.0])  # [m/s]
        self.b1d    = np.array([1.0, 0.0, 0.0])  # desired heading direction        

        # limits of states:
        self.x_max_threshold = 3.0  # [m]
        self.v_max_threshold = 10.0 # [m/s]
        self.W_max_threshold = 3.0  # [rad/s]
        self.euler_max_threshold = 80 * self.D2R # [rad]

        self.limits_x     = np.array([self.x_max_threshold, self.x_max_threshold, self.x_max_threshold]) # [m]
        self.limits_v     = np.array([self.v_max_threshold, self.v_max_threshold, self.v_max_threshold]) # [m/s]
        self.limits_R_vec = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
        self.limits_W     = np.array([self.W_max_threshold, self.W_max_threshold, self.W_max_threshold]) # [rad/s]

        self.low = np.concatenate([-self.limits_x,  
                                   -self.limits_v,
                                   -self.limits_R_vec,
                                   -self.limits_W])
        self.high = np.concatenate([self.limits_x,  
                                    self.limits_v,
                                    self.limits_R_vec,
                                    self.limits_W])

        # Observation space:
        self.observation_space = spaces.Box(
            self.low, 
            self.high, 
            dtype=np.float64
        )
        # Action space:
        self.action_space = spaces.Box(
            low=self.min_force, 
            high=self.max_force, 
            shape=(4,),
            dtype=np.float64
        ) 

        # Init:
        self.state = None
        self.viewer = None
        self.render_quad1  = None
        self.render_quad2  = None
        self.render_rotor1 = None
        self.render_rotor2 = None
        self.render_rotor3 = None
        self.render_rotor4 = None
        self.render_ref = None
        self.render_force_rotor1 = None
        self.render_force_rotor2 = None
        self.render_force_rotor3 = None
        self.render_force_rotor4 = None
        self.render_index = 1 

        self.seed()
        self.reset()


    def step(self, action):

        # Saturated actions:
        self.f1 = np.clip(action[0], self.min_force, self.max_force) # [N]
        self.f2 = np.clip(action[1], self.min_force, self.max_force) 
        self.f3 = np.clip(action[2], self.min_force, self.max_force)
        self.f4 = np.clip(action[3], self.min_force, self.max_force)

        ForceMoment = np.array([[       1.0,       1.0,        1.0,       1.0],
                                [       0.0,   -self.d,        0.0,    self.d],
                                [    self.d,       0.0,    -self.d,       0.0],
                                [-self.C_TQ, self.C_TQ, -self.C_TQ, self.C_TQ]]) \
                    @ np.array([self.f1, self.f2, self.f3, self.f4])[np.newaxis].T
        self.f = ForceMoment[0]   # [N]
        self.M = ForceMoment[1:4] # [Nm]

        # States: (x[0:3]; v[3:6]; R_vec[6:15]; W[15:18])
        _state = (self.state).flatten()

        x = np.array([_state[0], _state[1], _state[2]]).flatten() # [m]
        v = np.array([_state[3], _state[4], _state[5]]).flatten() # [m/s]
        R_vec = np.array([_state[6],  _state[7],  _state[8],
                          _state[9],  _state[10], _state[11],
                          _state[12], _state[13], _state[14]]).flatten() 
        R = R_vec.reshape(3, 3, order='F')
        W = np.array([_state[15], _state[16], _state[17]]).flatten() # [rad/s]
        _state = np.concatenate((x, v, R_vec, W), axis=0)
        
        # Solve ODEs.
        if self.ode_integrator == "euler": # solve w/ Euler's Method
            # Equations of motion of the quadrotor UAV
            x_dot = v
            v_dot = self.g*self.e3 - self.f*R@self.e3/self.m
            R_vec_dot = (R@self.hat(W)).reshape(9, 1, order='F')
            W_dot = inv(self.J)@(-self.hat(W)@self.J@W[np.newaxis].T + self.M)
            state_dot = np.concatenate([x_dot.flatten(), 
                                        v_dot.flatten(),                                                                          
                                        R_vec_dot.flatten(),
                                        W_dot.flatten()])
            self.state = _state + state_dot * self.dt
        elif self.ode_integrator == "solve_ivp": # solve w/ 'solve_ivp' Solver
            # method= 'RK45', 'LSODA', 'BDF', 'LSODA', ...
            sol = solve_ivp(self.EoM, [0, self.dt], _state, method='DOP853')
            self.state = sol.y[:,-1]
         
        # Next states:
        x = np.array([self.state[0], self.state[1], self.state[2]]).flatten() # [m]
        v = np.array([self.state[3], self.state[4], self.state[5]]).flatten() # [m/s]
        R_vec = np.array([self.state[6], self.state[7], self.state[8],
                          self.state[9], self.state[10], self.state[11],
                          self.state[12], self.state[13], self.state[14]]).flatten()
        W = np.array([self.state[15], self.state[16], self.state[17]]).flatten() # [rad/s]

        # Re-orthonormalize:
        ''' https://www.codefull.net/2017/07/orthonormalize-a-rotation-matrix/ '''
        R = R_vec.reshape(3, 3, order='F')
        u, s, vh = linalg.svd(R, full_matrices=False)
        R = u @ vh
        R_vec = R.reshape(9, 1, order='F').flatten()
        self.state = np.concatenate((x, v, R_vec, W), axis=0)

        # Reward function:
        C_X = 2.0  # pos coef.
        C_V = 0.15 # vel coef.
        C_W = 0.2  # ang_vel coef.

        eX = x - self.xd     # position error
        eX /= self.x_max_threshold # normalization
        eV = v - self.xd_dot # velocity error
                    
        reward = C_X*max(0, 1.0 - linalg.norm(eX, 2)) \
                - C_V * linalg.norm(eV, 2) - C_W * linalg.norm(W, 2)

        # Convert rotation matrix to Euler angles:
        eulerAngles = self.rotationMatrixToEulerAngles(R)

        # Terminal condition:
        done = False
        done = bool(
               (abs(x) >= self.limits_x).any() # [m]
            or x[2] >= 0.0 # crashed
            or (abs(v) >= self.limits_v).any() # [m/s]
            or (abs(W) >= self.limits_W).any() # [rad/s]
            or abs(eulerAngles[0]) >= self.euler_max_threshold # phi
            or abs(eulerAngles[1]) >= self.euler_max_threshold # theta
        )

        # Compute the thrust of each motor from the total force and moment
        ''' 
        ForceMoment =  (0.25 * np.array([[ 1.0,         0.0,   2.0/self.d, -1.0/self.C_TQ],
                                         [ 1.0, -2.0/self.d,        0.0,    1.0/self.C_TQ],
                                         [ 1.0,         0.0,  -2.0/self.d, -1.0/self.C_TQ],
                                         [ 1.0,  2.0/self.d,        0.0,    1.0/self.C_TQ]])) \
                    @ np.array([self.f, self.M[0], self.M[1], self.M[2]], dtype=object)[np.newaxis].T
        self.f1 = ForceMoment[0] # [N]
        self.f2 = ForceMoment[1]
        self.f3 = ForceMoment[2]
        self.f4 = ForceMoment[3]
        '''

        return np.array(self.state), reward, done, {}


    def reset(self):
        # Reset states:
        self.state = np.array(np.zeros(18))
        self.state[6:15] = np.eye(3).reshape(1,9, order='F')
        _error = 0.0 # initial error

        # x, position:
        self.state[0] = np.random.uniform(size = 1, low = -1.5, high = 1.5) 
        self.state[1] = np.random.uniform(size = 1, low = -1.5, high = 1.5)  
        self.state[2] = np.random.uniform(size = 1, low = -0.1, high = -1.5) 

        # v, velocity:
        self.state[3] = np.random.uniform(size = 1, low = -_error, high = _error) 
        self.state[4] = np.random.uniform(size = 1, low = -_error, high = _error) 
        self.state[5] = np.random.uniform(size = 1, low = -_error, high = _error)

        # R, attitude:
        # https://cse.sc.edu/~yiannisr/774/2014/Lectures/15-Quadrotors.pdf
        phi   = np.random.uniform(size = 1, low = -_error, high = _error)
        theta = np.random.uniform(size = 1, low = -_error, high = _error)
        psi   = np.random.uniform(size = 1, low = -_error, high = _error)
        self.state[6]  = cos(psi)*cos(theta)
        self.state[7]  = sin(psi)*cos(theta) 
        self.state[8]  = -sin(theta)  
        self.state[9]  = cos(psi)*sin(theta)*sin(phi) - sin(psi)*cos(phi) 
        self.state[10] = sin(psi)*sin(theta)*sin(phi) + cos(psi)*cos(phi)
        self.state[11] = cos(theta)*sin(phi) 
        self.state[12] = cos(psi)*sin(theta)*cos(phi) + sin(psi)*sin(phi)
        self.state[13] = sin(psi)*sin(theta)*cos(phi) - cos(psi)*sin(phi)
        self.state[14] = cos(theta)*cos(phi)

        # W, angular velocity:
        self.state[15] = np.random.uniform(size = 1, low = -_error, high = _error) 
        self.state[16] = np.random.uniform(size = 1, low = -_error, high = _error) 
        self.state[17] = np.random.uniform(size = 1, low = -_error, high = _error) 

        # Reset forces & moments:
        self.f  = self.m * self.g
        self.f1 = self.f_each
        self.f2 = self.f_each
        self.f3 = self.f_each
        self.f4 = self.f_each
        self.M  = np.zeros(3)

        return np.array(self.state)


    def render(self, mode='human', close=False):
        from vpython import box, sphere, color, vector, rate, canvas, cylinder, ring, arrow, scene, textures

        # Rendering state:
        state_vis = (self.state).flatten()

        x = np.array([state_vis[0], state_vis[1], state_vis[2]]).flatten() # [m]
        v = np.array([state_vis[3], state_vis[4], state_vis[5]]).flatten() # [m/s]
        R_vec = np.array([state_vis[6], state_vis[7], state_vis[8],
                          state_vis[9], state_vis[10], state_vis[11],
                          state_vis[12], state_vis[13], state_vis[14]]).flatten()
        W = np.array([state_vis[15], state_vis[16], state_vis[17]]).flatten() # [rad/s]

        quad_pos = x # [m]
        cmd_pos  = self.xd # [m]

        # Axis:
        x_axis = np.array([state_vis[6], state_vis[7], state_vis[8]]).flatten()
        y_axis = np.array([state_vis[9], state_vis[10], state_vis[11]]).flatten()
        z_axis = np.array([state_vis[12], state_vis[13], state_vis[14]]).flatten()

        # Init:
        if self.viewer is None:
            # Canvas.
            self.viewer = canvas(title = 'Quadrotor with RL', width = 1024, height = 768, \
                                 center = vector(0, 0, cmd_pos[2]), background = color.white, \
                                 forward = vector(1, 0.3, 0.3), up = vector(0, 0, -1)) # forward = view point
            
            # Quad body.
            self.render_quad1 = box(canvas = self.viewer, pos = vector(quad_pos[0], quad_pos[1], quad_pos[2]), \
                                    axis = vector(x_axis[0], x_axis[1], x_axis[2]), \
                                    length = 0.2, height = 0.05, width = 0.05) # vector(quad_pos[0], quad_pos[1], 0)
            self.render_quad2 = box(canvas = self.viewer, pos = vector(quad_pos[0], quad_pos[1], quad_pos[2]), \
                                    axis = vector(y_axis[0], y_axis[1], y_axis[2]), \
                                    length = 0.2, height = 0.05, width = 0.05)
            # Rotors.
            rotors_offest = 0.02
            self.render_rotor1 = cylinder(canvas = self.viewer, pos = vector(quad_pos[0], quad_pos[1], quad_pos[2]), \
                                          axis = vector(rotors_offest*z_axis[0], rotors_offest*z_axis[1], rotors_offest*z_axis[2]), \
                                          radius = 0.2, color = color.blue, opacity = 0.5)
            self.render_rotor2 = cylinder(canvas = self.viewer, pos = vector(quad_pos[0], quad_pos[1], quad_pos[2]), \
                                          axis = vector(rotors_offest*z_axis[0], rotors_offest*z_axis[1], rotors_offest*z_axis[2]), \
                                          radius = 0.2, color = color.cyan, opacity = 0.5)
            self.render_rotor3 = cylinder(canvas = self.viewer, pos = vector(quad_pos[0], quad_pos[1], quad_pos[2]), \
                                          axis = vector(rotors_offest*z_axis[0], rotors_offest*z_axis[1], rotors_offest*z_axis[2]), \
                                          radius = 0.2, color = color.blue, opacity = 0.5)
            self.render_rotor4 = cylinder(canvas = self.viewer, pos = vector(quad_pos[0], quad_pos[1], quad_pos[2]), \
                                          axis = vector(rotors_offest*z_axis[0], rotors_offest*z_axis[1], rotors_offest*z_axis[2]), \
                                          radius = 0.2, color = color.cyan, opacity = 0.5)

            # Force arrows.
            self.render_force_rotor1 = arrow(pos = vector(quad_pos[0], quad_pos[1], quad_pos[2]), \
                                             axis = vector(z_axis[0], z_axis[1], z_axis[2]), \
                                             shaftwidth = 0.05, color = color.blue)
            self.render_force_rotor2 = arrow(pos = vector(quad_pos[0], quad_pos[1], quad_pos[2]), \
                                             axis = vector(z_axis[0], z_axis[1], z_axis[2]), \
                                             shaftwidth = 0.05, color = color.cyan)
            self.render_force_rotor3 = arrow(pos = vector(quad_pos[0], quad_pos[1], quad_pos[2]), \
                                             axis = vector(z_axis[0], z_axis[1], z_axis[2]), \
                                             shaftwidth = 0.05, color = color.blue)
            self.render_force_rotor4 = arrow(pos = vector(quad_pos[0], quad_pos[1], quad_pos[2]), \
                                             axis = vector(z_axis[0], z_axis[1], z_axis[2]), \
                                             shaftwidth = 0.05, color = color.cyan)
                                    
            # Commands.
            self.render_ref = sphere(canvas = self.viewer, pos = vector(cmd_pos[0], cmd_pos[1], cmd_pos[2]), \
                                     radius = 0.07, color = color.red, \
                                     make_trail = True, trail_type = 'points', interval = 50)									
            
            # Inertial axis.				
            self.e1_axis = arrow(pos = vector(2.5, -2.5, 0), axis = 0.5*vector(1, 0, 0), \
                                 shaftwidth = 0.04, color=color.blue)
            self.e2_axis = arrow(pos = vector(2.5, -2.5, 0), axis = 0.5*vector(0, 1, 0), \
                                 shaftwidth = 0.04, color=color.green)
            self.e3_axis = arrow(pos = vector(2.5, -2.5, 0), axis = 0.5*vector(0, 0, 1), \
                                 shaftwidth = 0.04, color=color.red)

            # Body axis.				
            self.render_b1_axis = arrow(canvas = self.viewer, 
                                        pos = vector(quad_pos[0], quad_pos[1], quad_pos[2]), \
                                        axis = vector(x_axis[0], x_axis[1], x_axis[2]), \
                                        shaftwidth = 0.02, color = color.blue,
                                        make_trail = True, trail_color = color.yellow)
            self.render_b2_axis = arrow(canvas = self.viewer, 
                                        pos = vector(quad_pos[0], quad_pos[1], quad_pos[2]), \
                                        axis = vector(y_axis[0], y_axis[1], y_axis[2]), \
                                        shaftwidth = 0.02, color = color.green)
            self.render_b3_axis = arrow(canvas = self.viewer, 
                                        pos = vector(quad_pos[0], quad_pos[1], quad_pos[2]), \
                                        axis = vector(z_axis[0], z_axis[1], z_axis[2]), \
                                        shaftwidth = 0.02, color = color.red)

            # Floor.
            self.render_floor = box(pos = vector(0,0,0),size = vector(5,5,0.05), axis = vector(1,0,0), \
                                    opacity = 0.2, color = color.black)


        # Update visualization component:
        if self.state is None: 
            return None

        # Update quad body.
        self.render_quad1.pos.x = quad_pos[0]
        self.render_quad1.pos.y = quad_pos[1]
        self.render_quad1.pos.z = quad_pos[2]
        self.render_quad2.pos.x = quad_pos[0]
        self.render_quad2.pos.y = quad_pos[1]
        self.render_quad2.pos.z = quad_pos[2]

        self.render_quad1.axis.x = x_axis[0]
        self.render_quad1.axis.y = x_axis[1]	
        self.render_quad1.axis.z = x_axis[2]
        self.render_quad2.axis.x = y_axis[0]
        self.render_quad2.axis.y = y_axis[1]
        self.render_quad2.axis.z = y_axis[2]

        self.render_quad1.up.x = z_axis[0]
        self.render_quad1.up.y = z_axis[1]
        self.render_quad1.up.z = z_axis[2]
        self.render_quad2.up.x = z_axis[0]
        self.render_quad2.up.y = z_axis[1]
        self.render_quad2.up.z = z_axis[2]

        # Update rotors.
        rotors_offest = -0.02
        rotor_pos = 0.5*x_axis
        self.render_rotor1.pos.x = quad_pos[0] + rotor_pos[0]
        self.render_rotor1.pos.y = quad_pos[1] + rotor_pos[1]
        self.render_rotor1.pos.z = quad_pos[2] + rotor_pos[2]
        rotor_pos = 0.5*y_axis
        self.render_rotor2.pos.x = quad_pos[0] + rotor_pos[0]
        self.render_rotor2.pos.y = quad_pos[1] + rotor_pos[1]
        self.render_rotor2.pos.z = quad_pos[2] + rotor_pos[2]
        rotor_pos = (-0.5)*x_axis
        self.render_rotor3.pos.x = quad_pos[0] + rotor_pos[0]
        self.render_rotor3.pos.y = quad_pos[1] + rotor_pos[1]
        self.render_rotor3.pos.z = quad_pos[2] + rotor_pos[2]
        rotor_pos = (-0.5)*y_axis
        self.render_rotor4.pos.x = quad_pos[0] + rotor_pos[0]
        self.render_rotor4.pos.y = quad_pos[1] + rotor_pos[1]
        self.render_rotor4.pos.z = quad_pos[2] + rotor_pos[2]

        self.render_rotor1.axis.x = rotors_offest*z_axis[0]
        self.render_rotor1.axis.y = rotors_offest*z_axis[1]
        self.render_rotor1.axis.z = rotors_offest*z_axis[2]
        self.render_rotor2.axis.x = rotors_offest*z_axis[0]
        self.render_rotor2.axis.y = rotors_offest*z_axis[1]
        self.render_rotor2.axis.z = rotors_offest*z_axis[2]
        self.render_rotor3.axis.x = rotors_offest*z_axis[0]
        self.render_rotor3.axis.y = rotors_offest*z_axis[1]
        self.render_rotor3.axis.z = rotors_offest*z_axis[2]
        self.render_rotor4.axis.x = rotors_offest*z_axis[0]
        self.render_rotor4.axis.y = rotors_offest*z_axis[1]
        self.render_rotor4.axis.z = rotors_offest*z_axis[2]

        self.render_rotor1.up.x = y_axis[0]
        self.render_rotor1.up.y = y_axis[1]
        self.render_rotor1.up.z = y_axis[2]
        self.render_rotor2.up.x = y_axis[0]
        self.render_rotor2.up.y = y_axis[1]
        self.render_rotor2.up.z = y_axis[2]
        self.render_rotor3.up.x = y_axis[0]
        self.render_rotor3.up.y = y_axis[1]
        self.render_rotor3.up.z = y_axis[2]
        self.render_rotor4.up.x = y_axis[0]
        self.render_rotor4.up.y = y_axis[1]
        self.render_rotor4.up.z = y_axis[2]

        # Update force arrows.
        rotor_pos = 0.5*x_axis
        self.render_force_rotor1.pos.x = quad_pos[0] + rotor_pos[0]
        self.render_force_rotor1.pos.y = quad_pos[1] + rotor_pos[1]
        self.render_force_rotor1.pos.z = quad_pos[2] + rotor_pos[2]
        rotor_pos = 0.5*y_axis
        self.render_force_rotor2.pos.x = quad_pos[0] + rotor_pos[0]
        self.render_force_rotor2.pos.y = quad_pos[1] + rotor_pos[1]
        self.render_force_rotor2.pos.z = quad_pos[2] + rotor_pos[2]
        rotor_pos = (-0.5)*x_axis
        self.render_force_rotor3.pos.x = quad_pos[0] + rotor_pos[0]
        self.render_force_rotor3.pos.y = quad_pos[1] + rotor_pos[1]
        self.render_force_rotor3.pos.z = quad_pos[2] + rotor_pos[2]
        rotor_pos = (-0.5)*y_axis
        self.render_force_rotor4.pos.x = quad_pos[0] + rotor_pos[0]
        self.render_force_rotor4.pos.y = quad_pos[1] + rotor_pos[1]
        self.render_force_rotor4.pos.z = quad_pos[2] + rotor_pos[2]

        force_offest = -0.05
        self.render_force_rotor1.axis.x = force_offest * self.f1 * z_axis[0] 
        self.render_force_rotor1.axis.y = force_offest * self.f1 * z_axis[1]
        self.render_force_rotor1.axis.z = force_offest * self.f1 * z_axis[2]
        self.render_force_rotor2.axis.x = force_offest * self.f2 * z_axis[0]
        self.render_force_rotor2.axis.y = force_offest * self.f2 * z_axis[1]
        self.render_force_rotor2.axis.z = force_offest * self.f2 * z_axis[2]
        self.render_force_rotor3.axis.x = force_offest * self.f3 * z_axis[0]
        self.render_force_rotor3.axis.y = force_offest * self.f3 * z_axis[1]
        self.render_force_rotor3.axis.z = force_offest * self.f3 * z_axis[2]
        self.render_force_rotor4.axis.x = force_offest * self.f4 * z_axis[0]
        self.render_force_rotor4.axis.y = force_offest * self.f4 * z_axis[1]
        self.render_force_rotor4.axis.z = force_offest * self.f4 * z_axis[2]

        # Update commands.
        self.render_ref.pos.x = cmd_pos[0]
        self.render_ref.pos.y = cmd_pos[1]
        self.render_ref.pos.z = cmd_pos[2]

        # Update body axis.
        axis_offest = 0.8
        self.render_b1_axis.pos.x = quad_pos[0]
        self.render_b1_axis.pos.y = quad_pos[1]
        self.render_b1_axis.pos.z = quad_pos[2]
        self.render_b2_axis.pos.x = quad_pos[0]
        self.render_b2_axis.pos.y = quad_pos[1]
        self.render_b2_axis.pos.z = quad_pos[2]
        self.render_b3_axis.pos.x = quad_pos[0]
        self.render_b3_axis.pos.y = quad_pos[1]
        self.render_b3_axis.pos.z = quad_pos[2]

        self.render_b1_axis.axis.x = axis_offest * x_axis[0] 
        self.render_b1_axis.axis.y = axis_offest * x_axis[1] 
        self.render_b1_axis.axis.z = axis_offest * x_axis[2] 
        self.render_b2_axis.axis.x = axis_offest * y_axis[0] 
        self.render_b2_axis.axis.y = axis_offest * y_axis[1] 
        self.render_b2_axis.axis.z = axis_offest * y_axis[2] 
        self.render_b3_axis.axis.x = (axis_offest/2) * z_axis[0] 
        self.render_b3_axis.axis.y = (axis_offest/2) * z_axis[1]
        self.render_b3_axis.axis.z = (axis_offest/2) * z_axis[2]

        # Screen capture:
        """
        if (self.render_index % 5) == 0:
            self.viewer.capture('capture'+str(self.render_index))
        self.render_index += 1        
        """

        rate(30) # FPS

        return True


    def close(self):
        if self.viewer:
            self.viewer = None


    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]


    def EoM(self, t, state):
        # https://youtu.be/iS5JFuopQsA
        x = np.array([state[0], state[1], state[2]]).flatten() # [m]
        v = np.array([state[3], state[4], state[5]]).flatten() # [m/s]
        R_vec = np.array([state[6], state[7], state[8],
                          state[9], state[10], state[11],
                          state[12], state[13], state[14]]).flatten()
        R = R_vec.reshape(3, 3, order='F')
        W = np.array([state[15], state[16], state[17]]).flatten() # [rad/s]

        # Equations of motion of the quadrotor UAV
        x_dot = v
        v_dot = self.g*self.e3 - self.f*R@self.e3/self.m
        R_vec_dot = (R@self.hat(W)).reshape(9, 1, order='F')
        W_dot = inv(self.J)@(-self.hat(W)@self.J@W[np.newaxis].T + self.M)

        state_dot = np.concatenate([x_dot.flatten(), 
                                    v_dot.flatten(),                                                                          
                                    R_vec_dot.flatten(),
                                    W_dot.flatten()])

        return np.array(state_dot)


    def hat(self, x):
        hat_x = np.array([[0.0, -x[2], x[1]], \
                          [x[2], 0.0, -x[0]], \
                          [-x[1], x[0], 0.0]])
                        
        return np.array(hat_x)


    def vee(self, M):
        # vee map: inverse of the hat map
        vee_M = np.array([[M[2,1]], \
                          [M[0,2]], \
                          [M[1,0]]])

        return np.array(vee_M)


    def eulerAnglesToRotationMatrix(self, theta) :
        # Calculates Rotation Matrix given euler angles.
        R_x = np.array([[1,              0,               0],
                        [0,  cos(theta[0]),  -sin(theta[0])],
                        [0,  sin(theta[0]),   cos(theta[0])]])

        R_y = np.array([[ cos(theta[1]),   0,  sin(theta[1])],
                        [             0,   1,              0],
                        [-sin(theta[1]),   0,  cos(theta[1])]])

        R_z = np.array([[cos(theta[2]),  -sin(theta[2]),  0],
                        [sin(theta[2]),   cos(theta[2]),  0],
                        [            0,               0,  1]])

        R = np.dot(R_z, np.dot( R_y, R_x ))

        return R


    def isRotationMatrix(self, R):
        # Checks if a matrix is a valid rotation matrix.
        Rt = np.transpose(R)
        shouldBeIdentity = np.dot(Rt, R)
        I = np.identity(3, dtype = R.dtype)
        n = np.linalg.norm(I - shouldBeIdentity)
        return n < 1e-6


    def rotationMatrixToEulerAngles(self, R):
        # Calculates rotation matrix to euler angles
        # The result is the same as MATLAB except the order
        # of the euler angles ( x and z are swapped ).

        assert(self.isRotationMatrix(R))

        sy = sqrt(R[0,0] * R[0,0] +  R[1,0] * R[1,0])

        singular = sy < 1e-6

        if  not singular:
            x = atan2(R[2,1] , R[2,2])
            y = atan2(-R[2,0], sy)
            z = atan2(R[1,0], R[0,0])
        else:
            x = atan2(-R[1,2], R[1,1])
            y = atan2(-R[2,0], sy)
            z = 0

        return np.array([x, y, z])