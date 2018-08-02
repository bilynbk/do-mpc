#
#   This file is part of do-mpc
#
#   do-mpc: An environment for the easy, modular and efficient implementation of
#        robust nonlinear model predictive control
#
#   Copyright (c) 2014-2016 Sergio Lucia, Alexandru Tatulea-Codrean
#                        TU Dortmund. All rights reserved
#
#   do-mpc is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Lesser General Public License as
#   published by the Free Software Foundation, either version 3
#   of the License, or (at your option) any later version.
#
#   do-mpc is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Lesser General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with do-mpc.  If not, see <http://www.gnu.org/licenses/>.
#

import setup_nlp
import setup_mhe
from casadi import *
from casadi.tools import *
import data_do_mpc
import numpy as NP
from scipy.linalg import expm
import pdb
class ocp:
    """ A class that contains a full description of the optimal control problem and will be used in the model class. This is dependent on a specific element of a model class"""
    def __init__(self, param_dict, *opt):
        # Initial state and initial input
        self.x0 = param_dict["x0"]
        self.u0 = param_dict["u0"]

        # Bounds for the states
        self.x_lb = param_dict["x_lb"]
        self.x_ub = param_dict["x_ub"]
        # Bounds for the inputs
        self.u_lb = param_dict["u_lb"]
        self.u_ub = param_dict["u_ub"]

        # Scaling factors
        self.x_scaling = param_dict["x_scaling"]
        self.u_scaling = param_dict["u_scaling"]
        self.y_scaling = param_dict["y_scaling"]

        # Symbolic nonlinear constraints
        self.cons = param_dict["cons"]
        # Upper bounds (no lower bounds for nonlinear constraints)
        self.cons_ub = param_dict["cons_ub"]
        # Terminal constraints
        self.cons_terminal = param_dict["cons_terminal"]
        self.cons_terminal_lb = param_dict["cons_terminal_lb"]
        self.cons_terminal_ub = param_dict["cons_terminal_ub"]
        # Flag for soft constraints
        self.soft_constraint = param_dict["soft_constraint"]
        # Penalty term and maximum violation of soft constraints
        self.penalty_term_cons = param_dict["penalty_term_cons"]
        self.maximum_violation = param_dict["maximum_violation"]
        # Lagrange term, Mayer term, and term for input variations
        self.lterm = param_dict["lterm"]
        self.mterm = param_dict["mterm"]
        self.rterm = param_dict["rterm"]

class model:
    """A class for the definition model equations and optimal control problem formulation"""
    def __init__(self, param_dict, *opt):
        # Assert for define length of param_dict
        required_dimension = 27
        if not (len(param_dict) == required_dimension):            raise Exception("Model / OCP information is incomplete. The number of elements in the dictionary is not correct")
        # Assign the main variables describing the model equations
        self.x = param_dict["x"]
        self.u = param_dict["u"]
        self.y = param_dict["y"]
        self.p = param_dict["p"]
        self.z = param_dict["z"]
        self.rhs = param_dict["rhs"] # Right hand side of the DAE equations
        self.tv_p = param_dict["tv_p"]
         # Assign the main variables that describe the OCP
        self.ocp = ocp(param_dict)

    @classmethod
    def user_model(cls, param_dict, *opt):
        " This is open for the implementation of a user-defined model class"
        dummy = 1
        return cls(dummy)

class simulator:
    """A class for the definition model equations and optimal control problem formulation"""
    def __init__(self, model_simulator, param_dict, *opt):
        # Assert for define length of param_dict
        required_dimension = 10
        if not (len(param_dict) == required_dimension): raise Exception("Simulator information is incomplete. The number of elements in the dictionary is not correct")
        # Build the simulator for EKF
        rhs_unscaled = substitute(model_simulator.rhs, model_simulator.x, model_simulator.x * model_simulator.ocp.x_scaling)/model_simulator.ocp.x_scaling
        rhs_unscaled = substitute(rhs_unscaled, model_simulator.u, model_simulator.u * model_simulator.ocp.u_scaling)
        dae = {'x':model_simulator.x, 'p':vertcat(model_simulator.u,model_simulator.p, model_simulator.tv_p), 'ode':rhs_unscaled}
        opts = param_dict["integrator_opts"]
        simulator_do_mpc = integrator("simulator", param_dict["integration_tool"], dae,  opts)
        self.simulator = simulator_do_mpc
        self.plot_states = param_dict["plot_states"]
        self.plot_control = param_dict["plot_control"]
        self.plot_anim = param_dict["plot_anim"]
        self.export_to_matlab = param_dict["export_to_matlab"]
        self.export_name = param_dict["export_name"]
        self.p_real_now = param_dict["p_real_now"]
        self.tv_p_real_now = param_dict["tv_p_real_now"]
        self.t_step_simulator = param_dict["t_step_simulator"]
        self.t0_sim = 0
        self.tf_sim = param_dict["t_step_simulator"]
        # NOTE:  The same initial condition than for the optimizer is imposed
        self.x0_sim = model_simulator.ocp.x0 / model_simulator.ocp.x_scaling
        self.xf_sim = 0
        # This is an index to account for the MPC iteration. Starts at 1
        self.mpc_iteration = 1
    @classmethod
    def user_simulator(cls, param_dict, *opt):
        " This is open for the implementation of a user-defined simulator class"
        dummy = 1
        return cls(dummy)

    @classmethod
    def application(cls, param_dict, *opt):
        " This is open for the implementation of connection to a real plant"
        dummy = 1
        return cls(dummy)

class optimizer:
    '''This is a class that defines a do-mpc optimizer. The class uses a local model, which
    can be defined independetly from the other modules. The parameters '''
    def __init__(self, optimizer_model, param_dict, *opt):
        # Set the local model to be used by the model
        self.optimizer_model = optimizer_model
        # Assert for the required size of the parameters
        required_dimension = 16
        if not (len(param_dict) == required_dimension): raise Exception("The length of the parameter dictionary is not correct!")
        # Define optimizer parameters
        self.n_horizon = param_dict["n_horizon"]
        self.t_step = param_dict["t_step"]
        self.n_robust = param_dict["n_robust"]
        self.state_discretization = param_dict["state_discretization"]
        self.poly_degree = param_dict["poly_degree"]
        self.collocation = param_dict["collocation"]
        self.n_fin_elem = param_dict["n_fin_elem"]
        self.generate_code = param_dict["generate_code"]
        self.open_loop = param_dict["open_loop"]
        self.t_end = param_dict["t_end"]
        self.nlp_solver = param_dict["nlp_solver"]
        self.linear_solver = param_dict["linear_solver"]
        self.qp_solver = param_dict["qp_solver"]
        # Define model uncertain parameters
        self.uncertainty_values = param_dict["uncertainty_values"]
        # Define time varying optimizer parameters
        self.tv_p_values = param_dict["tv_p_values"]
        self.parameters_nlp = param_dict["parameters_nlp"]
        # Initialize empty methods for completion later
        self.solver = []
        self.arg = []
        self.nlp_dict_out = []
        self.opt_result_step = []
        self.u_mpc = optimizer_model.ocp.u0
    @classmethod
    def user_optimizer(cls, optimizer_model, param_dict, *opt):
        "This method is open for the impelmentation of a user defined optimizer"
        dummy = 1
        return cls(dummy)

class observer:
    """A class for the definition model equations and optimal control problem formulation"""
    def __init__(self, model_observer, param_dict, *opt):
        if not (len(param_dict) == 30):
            raise Exception("Observer information is incomplete!")
        if not (model_observer.y.size(1) == param_dict["mag"].shape[0]):
            raise Exception("The number of deviations and measurements do not correspond!")
        self.method = param_dict["method"]
        self.observer_model = model_observer
        self.uncertainty_values = param_dict["uncertainty_values"]
        self.tv_p_values = param_dict["tv_p_values"]
        self.x_init = param_dict["x_init"]

        if self.method == "MHE":
            self.n_horizon = param_dict["n_horizon"]
            self.t_step = param_dict["t_step"]
            self.n_robust = param_dict["n_robust"]
            self.state_discretization = param_dict["state_discretization"]
            self.poly_degree = param_dict["poly_degree"]
            self.collocation = param_dict["collocation"]
            self.n_fin_elem = param_dict["n_fin_elem"]
            self.generate_code = param_dict["generate_code"]
            self.nlp_solver = param_dict["nlp_solver"]
            self.linear_solver = param_dict["linear_solver"]
            self.qp_solver = param_dict["qp_solver"]
            self.P_states = param_dict["P_states"]
            self.P_inputs = param_dict["P_inputs"]
            self.P_param = param_dict["P_param"]
            self.P_meas = param_dict["P_meas"]
            self.tv_p = model_observer.tv_p
            self.u_lb = model_observer.ocp.u_lb
            self.u_ub = model_observer.ocp.u_ub
            self.x_lb = model_observer.ocp.x_lb
            self.x_ub = model_observer.ocp.x_ub
            self.solver = []
            self.arg = []
            self.nlp_dict_out = []
            self.opt_result_step = []

        elif self.method == "EKF":
            self.t_step_observer = param_dict["t_step_observer"]
            x = model_observer.x
            u = model_observer.u
            p = model_observer.p
            tv_p = model_observer.tv_p
            nx = model_observer.x.size(1)
            np = model_observer.p.size(1)
            f = model_observer.rhs
            f = vertcat(f,DM(NP.zeros(np)))
            h = model_observer.y
            # h = substitute(model_observer.y,u,u*model_observer.ocp.u_scaling)
            # h = substitute(h,x,x*model_observer.ocp.x_scaling)/model_observer.ocp.y_scaling
            self.Q = param_dict["Q"]
            self.R = param_dict["R"]
            self.h = Function("h",[x,u,p,tv_p],[model_observer.y])
            self.P = param_dict["P_init"]
            # simulator (integrator for states)
            dae = {'x':vertcat(x,p), 'p':vertcat(u,tv_p), 'ode':f}
            opts = param_dict["integrator_opts"]
            self.simulator = integrator("simulator", param_dict["integration_tool"], dae,  opts)
            # state transition matrix
            F = jacobian(f,vertcat(x,p))
            self.F = Function("F",[x,u,p,tv_p],[F])
            # observation matrix
            H = jacobian(h,vertcat(x,p))
            self.H = Function("H",[x,u,p,tv_p],[H])
            # integrator for covariance matrix
            P_var = SX.sym("P_var",nx+np,nx+np)
            F_var = SX.sym("F_var",nx+np,nx+np)
            Q_var = SX.sym("Q_var",nx+np,nx+np)
            # P_ode = mtimes(F_var,P_var) + mtimes(P_var,F_var.T) + Q_var
            # dae_P = {'x':P_var, 'p':vertcat(F_var,Q_var), 'ode':P_ode}
            # self.int_cov = integrator("int_cov", param_dict["integration_tool"], dae_P, opts)
            t_step = opts["tf"]
            # P_taylor = NP.diag(NP.ones(nx)) + F_var * t_step #+ mtimes(F_var,F_var.T) * t_step**2/2
            P_taylor = mtimes(mtimes(F_var,P_var),F_var.T)+Q_var
            self.P_fun = Function("P_fun",[P_var,F_var,Q_var],[P_taylor])
            # old estimation
            # self.x_hat = param_dict["x_init"]
            # self.x_hat = NP.vstack(model_observer.ocp.x0 ) * (1+NP.random.randn(nx+np)*0.0003)

        # if self.method == "UKF":
        #     nx = observer_model.x.size(1)
        #     ny = observer_model.y.size(1)
        #     alpha = param_dict["alpha"]
        #     beta = param_dict["beta"]
        #     kappa = param_dict["kappa"]
        #     self.L = 2*nx+ny
        #     self.lam = alpha**2*(L+kappa)-L
        #     # augmented state
        #     x0 = NP.reshape(,(-1,1))
        #     w0 = NP.zeros([nx,1])
        #     v0 = NP.zeros([ny,1])
        #     self.Xa0 = NP.vstack([x0,w0,v0])

        self.noise = param_dict["noise"]
        self.mag = param_dict["mag"]

        self.observed_states = NP.zeros(model_observer.x.size(1))
        self.meas_fcn = param_dict["meas_fcn"]
        self.open_loop = param_dict["open_loop"]


    @classmethod
    def user_observer(cls, param_dict, *opt):
        " This is open for the implementation of a user-defined estimator class"
        dummy = 1
        return cls(dummy)

class configuration:
    """ A class for the definition of a do-mpc configuration that
    contains a model, optimizer, observer and simulator module """
    def __init__(self, model, optimizer, observer, simulator):
        # The four modules
        self.model = model
        self.optimizer = optimizer
        self.observer = observer
        if self.observer.method == "MHE":
            self.setup_solver_mhe()
        self.simulator = simulator
        # The data structure
        self.mpc_data = data_do_mpc.mpc_data(self)
        # The solver
        self.setup_solver()

    def setup_solver(self):
        # Call setup_nlp to generate the NLP
        nlp_dict_out = setup_nlp.setup_nlp(self.model, self.optimizer)
        # Set options
        opts = {}
        opts["expand"] = True
        opts["ipopt.linear_solver"] = self.optimizer.linear_solver
        #NOTE: this could be passed as parameters of the optimizer class
        opts["ipopt.max_iter"] = 500
        opts["ipopt.tol"] = 1e-6
        # Setup the solver
        solver = nlpsol("solver", self.optimizer.nlp_solver, nlp_dict_out['nlp_fcn'], opts)
        arg = {}
        # Initial condition
        arg["x0"] = nlp_dict_out['vars_init']
        # Bounds on x
        arg["lbx"] = nlp_dict_out['vars_lb']
        arg["ubx"] = nlp_dict_out['vars_ub']
        # Bounds on g
        arg["lbg"] = nlp_dict_out['lbg']
        arg["ubg"] = nlp_dict_out['ubg']
        # NLP parameters
        nu = self.model.u.size(1)
        ntv_p = self.model.tv_p.size(1)
        nk = self.optimizer.n_horizon
        parameters_setup_nlp = struct_symMX([entry("uk_prev",shape=(nu)), entry("TV_P",shape=(ntv_p,nk))])
        param = parameters_setup_nlp(0)
        # First value of the nlp parameters
        param["uk_prev"] = self.model.ocp.u0
        param["TV_P"] = self.optimizer.tv_p_values[0]
        arg["p"] = param
        # Add new attributes to the optimizer class
        self.optimizer.solver = solver
        self.optimizer.arg = arg
        self.optimizer.nlp_dict_out = nlp_dict_out

    def setup_solver_mhe(self):
        # Call setup_nlp to generate the NLP
        nlp_dict_out = setup_mhe.setup_mhe(self.observer.observer_model, self.observer)
        # Set options
        opts = {}
        opts["expand"] = True
        opts["ipopt.linear_solver"] = self.observer.linear_solver
        #NOTE: this could be passed as parameters of the observer class
        opts["ipopt.max_iter"] = 500
        opts["ipopt.tol"] = 1e-6
        opts["ipopt.ma27_liw_init_factor"] =  100.0
        opts["ipopt.ma27_la_init_factor"] =  100.0
        opts["ipopt.ma27_meminc_factor"] =  2.0
        # Setup the solver
        solver = nlpsol("solver", self.observer.nlp_solver, nlp_dict_out['nlp_fcn'], opts)
        arg = {}
        # Initial condition
        arg["x0"] = nlp_dict_out['vars_init']
        # Bounds on x
        arg["lbx"] = nlp_dict_out['vars_lb']
        arg["ubx"] = nlp_dict_out['vars_ub']
        # Bounds on g
        arg["lbg"] = nlp_dict_out['lbg']
        arg["ubg"] = nlp_dict_out['ubg']
        # NLP parameters
        nx = self.model.x.size(1)
        nu = self.model.u.size(1)
        np = self.model.p.size(1)
        ntv_p = self.model.tv_p.size(1)
        ny = self.model.y.size(1)
        nk = self.observer.n_horizon
        parameters_setup_mhe = struct_symMX([entry("uk_prev",shape=(nu)), entry("TV_P",shape=(ntv_p,nk)),
                                             entry("Y_MEAS",shape=(ny,nk)), entry("X_EST",shape=(nx,1)),
                                             entry("U_MEAS", shape=(nu,nk)), entry("P_EST", shape=(np,1)),
                                             entry("ALPHA", shape=(nk)),
                                             entry("ALPHA_ARRIVAL", shape=(nk))])
        param = parameters_setup_mhe(0)
        # First value of the nlp parameters
        param["uk_prev"] = self.model.ocp.u0
        param["TV_P"] = NP.ones([ntv_p,nk]) #self.observer.tv_p_values[0]
        param["Y_MEAS"] = NP.ones([ny,nk])
        param["X_EST"] = NP.zeros([nx,1])
        # param["P_EST"] = 3
        param["U_MEAS"] = NP.zeros([nu,nk])
        param["ALPHA"] = NP.zeros(nk)
        param["ALPHA_ARRIVAL"] = NP.zeros(nk)
        arg["p"] = param
        # Add new attributes to the observer class
        self.observer.solver = solver
        self.observer.arg = arg
        self.observer.nlp_dict_out = nlp_dict_out

    def make_step_optimizer(self):
        arg = self.optimizer.arg
        result = self.optimizer.solver(x0=arg['x0'], lbx=arg['lbx'], ubx=arg['ubx'], lbg=arg['lbg'], ubg=arg['ubg'], p = arg['p'])
        # Store the full solution
        self.optimizer.opt_result_step = data_do_mpc.opt_result(result)
        # Extract the optimal control input to be applied
        nu = len(self.optimizer.u_mpc)
        U_offset = self.optimizer.nlp_dict_out['U_offset']
        v_opt = self.optimizer.opt_result_step.optimal_solution
        self.optimizer.u_mpc = NP.resize(NP.array(v_opt[U_offset[0][0]:U_offset[0][0]+nu]),(nu))

    def make_step_observer(self):
        if self.observer.method == "state-feedback":
            self.observer.observed_states = self.simulator.xf_sim
        else:
            # self.make_measurement()
            if self.observer.method == 'MHE':
                if self.simulator.mpc_iteration ==2:
                    self.init_mhe()
                X_offset = self.observer.nlp_dict_out['X_offset']
                nx = self.model.x.size(1)
                arg = self.observer.arg
                result = self.observer.solver(x0=arg['x0'], lbx=arg['lbx'], ubx=arg['ubx'], lbg=arg['lbg'], ubg=arg['ubg'], p = arg['p'])
                self.observer.observed_states = self.simulator.xf_sim
                self.observer.optimal_solution = result['x']
            elif self.observer.method == 'EKF':
                nx = self.observer.observer_model.x.size(1)
                np = self.observer.observer_model.p.size(1)
                rep = int(self.simulator.t_step_simulator/self.observer.t_step_observer)
                for bla in range(rep):
                    if self.simulator.mpc_iteration == 2:
                        p_nom = self.simulator.p_real_now(self.simulator.t0_sim)
                        # x_hat = self.model.ocp.x0*(1+NP.random.randn(nx)*0.00001)
                        x_hat = self.simulator.xf_sim + NP.random.randn(nx)*0.00001
                        self.observer.x_mean_sim = self.simulator.xf_sim
                        self.observer.x_hat_aug = NP.hstack([x_hat,p_nom])
                    if bla == 0:
                        self.observer.x_mean_sim = self.simulator.xf_sim
                    self.make_measurement()
                    # get current values and compute  current matrices
                    xk = NP.reshape(self.observer.x_hat_aug,(-1,1))
                    zk = NP.reshape(self.observer.measurement,(-1,1))
                    u_mpc = self.optimizer.u_mpc*self.observer.observer_model.ocp.u_scaling
                    # p_real = self.simulator.p_real_now(self.simulator.t0_sim)
                    # p_real = self.simulator.p_real_batch
                    tv_p_real = self.simulator.tv_p_real_now(self.simulator.t0_sim)
                    P_init = self.observer.P
                    R = self.observer.R
                    Q = self.observer.Q
                    # Predict states
                    result  = self.observer.simulator(x0 = xk, p = vertcat(u_mpc,tv_p_real))
                    xk = NP.squeeze(result['xf'])
                    xk_plain = xk[:nx]
                    p_real = xk[nx:nx+np]
                    # Predict covariance
                    H = self.observer.H(xk_plain,u_mpc,p_real,tv_p_real)
                    F = self.observer.F(xk_plain,u_mpc,p_real,tv_p_real)
                    # pdb.set_trace()
                    F = expm(self.observer.t_step_observer*NP.atleast_2d(F))
                    # P = self.observer.P_fun(P_init,F,Q)
                    P = mtimes(mtimes(F,P_init),F.T)+Q
                    # innovation
                    S = inv(mtimes(H,mtimes(P,H.T))+R)
                    # compute Kalman gain
                    K = mtimes(mtimes(P,H.T),S)
                    # pdb.set_trace()
                    # residual
                    yk = zk - self.observer.h(xk[:nx],u_mpc,xk[nx:nx+np],tv_p_real)
                    # update state estimate
                    xk = xk + mtimes(K,yk)
                    #update covariance estimate
                    self.observer.P = mtimes(NP.diag(NP.ones(nx+np))-mtimes(K,H),P)
                    # pdb.set_trace()
                    self.observer.x_hat_aug = NP.squeeze(xk)
                    # update simulation
                    sim_up = self.observer.simulator(x0 = vertcat(self.observer.x_mean_sim,p_real), p = vertcat(u_mpc,tv_p_real))
                    self.observer.x_mean_sim = NP.squeeze(sim_up['xf'][:nx])
                # self.observer.observed_states = self.observer.x_hat/self.model.ocp.x_scaling
                self.observer.observed_states = self.simulator.xf_sim

            # elif self.observer.method == "UKF":
            #     # calculate sigma points and weights
            #     L = self.observer.L
            #     lam = self.observer.lam
            #     alpha = self.observer.alpha
            #     beta = self.observer.beta
            #     kappa = self.observer.kappa
            #     gamma = NP.sqrt(L+lam)
            #     P = self.observer.P
            #     X = []
            #     W_c = []
            #     W_m = []
            #     x_bar = 1
            #     for i in range(L+1):
            #         if i == 0:
            #             X = x_bar
            #             W_m.append(lam/(L+lam))
            #             W_c.append(lam/(L+lam)+(1-alpha**2+beta))
            #         elif (i > 0) and (i <= nx):
            #             x_add = x_bar + NP.sqrt((i + lam)*P)[:,i]
            #             X.append(x_add)
            #             W = 1./(2*(L+lam))
            #             W_m.append(W)
            #             W_c.append(W)
            #         elif (i>nx):
            #             x_add = x_bar - NP.sqrt((i + lam)*P)[:,i-nx]
            #             X = NP.append([X,x_add],axis=1)
            #             W = 1./(2*(L+lam))
            #             W_m.append(W)
            #             W_c.append(W)
            #
            #     # time update
            #     u_mpc = self.optimizer.u_mpc*self.model.ocp.u_scaling
            #     X_new = []


    def init_mhe(self):
        nx = self.model.x.size(1)
        y_scaling = self.observer.observer_model.ocp.y_scaling
        nk = self.observer.n_horizon
        arg = self.observer.arg
        param = arg["p"]
        y_meas = NP.reshape(self.observer.measurement/y_scaling,(-1,1))
        param["Y_MEAS"] = NP.repeat(y_meas,nk,axis=1)
        self.mpc_data.mhe_y_meas = NP.repeat(y_meas,nk,axis=1)
        param["X_EST"] = self.observer.x_init
        u_meas = NP.reshape(self.optimizer.u_mpc,(-1,1))
        param["U_MEAS"] = NP.repeat(u_meas,nk,axis=1)
        self.mpc_data.mhe_u_meas = NP.repeat(u_meas,nk,axis=1)
        arg["p"] = param
        self.observer.arg = arg

    def make_step_simulator(self):
        # Extract the necessary information for the simulation
        u_mpc = self.optimizer.u_mpc
        # Use the real parameters
        # p_real = self.simulator.p_real_now(self.simulator.t0_sim)
        p_real = self.simulator.p_real_batch
        tv_p_real = self.simulator.tv_p_real_now(self.simulator.t0_sim)
        if self.optimizer.state_discretization == 'discrete-time':
            rhs_unscaled = substitute(self.model.rhs, self.model.x, self.model.x * self.model.ocp.x_scaling)/self.model.ocp.x_scaling
            rhs_unscaled = substitute(rhs_unscaled, self.model.u, self.model.u * self.model.ocp.u_scaling)
            rhs_fcn = Function('rhs_fcn',[self.model.x,vertcat(self.model.u,self.model.p)],[rhs_unscaled])
            x_next = rhs_fcn(self.simulator.x0_sim,vertcat(u_mpc,p_real))
            self.simulator.xf_sim = NP.squeeze(NP.array(x_next))
        else:
            result  = self.simulator.simulator(x0 = self.simulator.x0_sim, p = vertcat(u_mpc,p_real,tv_p_real))
            self.simulator.xf_sim = NP.squeeze(result['xf'])
        # Update the initial condition for the next iteration
        self.simulator.x0_sim = self.simulator.xf_sim
        # Correction for sizes of arrays when dimension is 1
        if self.simulator.xf_sim.shape ==  ():
            self.simulator.xf_sim = NP.array([self.simulator.xf_sim])
        # Update the mpc iteration index and the time
        self.simulator.mpc_iteration = self.simulator.mpc_iteration + 1
        self.simulator.t0_sim = self.simulator.tf_sim
        self.simulator.tf_sim = self.simulator.tf_sim + self.simulator.t_step_simulator

    def make_measurement(self):
        data = self.mpc_data
        nu = self.model.u.size(1)
        nx = self.model.x.size(1)
        ny = self.observer.observer_model.y.size(1)
        np = self.model.p.size(1)
        ntv_p = self.model.tv_p.size(1)
        nk = self.optimizer.n_horizon
        x = self.observer.x_mean_sim*self.model.ocp.x_scaling
        u_mpc = self.optimizer.u_mpc*self.model.ocp.u_scaling
        # p_real = self.simulator.p_real_now(self.simulator.t0_sim)
        p_real = self.simulator.p_real_batch
        tv_p_real = self.simulator.tv_p_real_now(self.simulator.t0_sim)
        mag = NP.reshape(self.observer.mag,(-1,1))
        res = self.observer.meas_fcn(x,u_mpc,p_real,tv_p_real)
        if self.observer.noise == "gaussian":
            res += NP.random.normal(NP.zeros([ny,1]),mag)
            self.observer.measurement = NP.squeeze(res)


        if self.observer.method == "MHE":
            nk_mhe = self.observer.n_horizon
            y_scaling = self.observer.observer_model.ocp.y_scaling
            self.mpc_data.mhe_y_meas = NP.roll(data.mhe_y_meas,-1,axis=1)
            self.mpc_data.mhe_y_meas[:,-1] = self.observer.measurement/y_scaling
            self.mpc_data.mhe_u_meas = NP.roll(data.mhe_u_meas,-1,axis=1)
            self.mpc_data.mhe_u_meas[:,-1] = self.optimizer.u_mpc

            step_index = int((self.simulator.t0_sim-self.simulator.t_step_simulator) / self.simulator.t_step_simulator)
            parameters_setup_mhe = struct_symMX([entry("uk_prev",shape=(nu)), entry("TV_P",shape=(ntv_p,nk_mhe)),
                                                 entry("Y_MEAS",shape=(ny,nk_mhe)), entry("X_EST",shape=(nx,1)),
                                                 entry("U_MEAS", shape=(nu,nk_mhe)), entry("P_EST", shape=(np,1)),
                                                 entry("ALPHA", shape=(nk_mhe)),
                                                 entry("ALPHA_ARRIVAL", shape=(nk_mhe))])
            param_mhe = parameters_setup_mhe(0)
            param_mhe["uk_prev"] = self.optimizer.u_mpc
            param_mhe["TV_P"] = self.observer.tv_p_values[step_index]
            iter = self.simulator.mpc_iteration - 2
            if (iter > 0) and (iter < self.observer.n_horizon):
                param_mhe["X_EST"] = self.mpc_data.mhe_est_states_shift[:,-iter]
            else:
                param_mhe["X_EST"] = self.mpc_data.mhe_est_states_shift[:,0]
            param_mhe["Y_MEAS"] = self.mpc_data.mhe_y_meas
            param_mhe["U_MEAS"] = self.mpc_data.mhe_u_meas
            alpha = self.observer.arg["p"]["ALPHA"]
            alpha = NP.roll(alpha,-1,axis=0)
            alpha[-1] = 1
            param_mhe["ALPHA"] = NP.squeeze(alpha)
            alpha_arrival = self.observer.arg["p"]["ALPHA_ARRIVAL"]
            if iter == 1:
                alpha_arrival[-1] = 1
            elif iter <= self.observer.n_horizon:
                alpha_arrival = NP.roll(alpha_arrival,-1,axis=0)
            param_mhe["ALPHA_ARRIVAL"] = NP.squeeze(alpha_arrival)
            self.observer.arg['p'] = param_mhe

            # include all inputs as constraints
            U_offset = self.observer.nlp_dict_out['U_offset']
            u_meas = self.mpc_data.mhe_u_meas
            for i in range(nk_mhe):
                self.observer.arg['lbx'][U_offset[i,0]:U_offset[i,0]+nu] = NP.squeeze(u_meas[:,i])
                self.observer.arg['ubx'][U_offset[i,0]:U_offset[i,0]+nu] = NP.squeeze(u_meas[:,i])

    def prepare_next_iter(self):
        observed_states = self.observer.observed_states
        # observed_param = self.observer.observed_param
        X_offset = self.optimizer.nlp_dict_out['X_offset']
        nx = self.model.x.size(1)
        nu = self.model.u.size(1)
        ny = self.model.y.size(1)
        ntv_p = self.model.tv_p.size(1)
        nk = self.optimizer.n_horizon
        np = self.model.p.size(1)
        parameters_setup_nlp = struct_symMX([entry("uk_prev",shape=(nu)), entry("TV_P",shape=(ntv_p,nk))])
        param = parameters_setup_nlp(0)
        # First value of the nlp parameters
        param["uk_prev"] = self.optimizer.u_mpc
        step_index = int(self.simulator.t0_sim / self.simulator.t_step_simulator)
        param["TV_P"] = self.optimizer.tv_p_values[step_index]
        # Enforce the observed states as initial point for next optimization
        self.optimizer.arg['lbx'][X_offset[0,0]:X_offset[0,0]+nx] = NP.squeeze(observed_states)
        self.optimizer.arg['ubx'][X_offset[0,0]:X_offset[0,0]+nx] = NP.squeeze(observed_states)
        self.optimizer.arg["x0"] = self.optimizer.opt_result_step.optimal_solution
        # Pass as parameter the used control input
        self.optimizer.arg['p'] = param

        # observer
        if self.observer.method == "MHE":
            self.observer.arg["x0"] = self.observer.optimal_solution

    def store_mpc_data(self):
        mpc_iteration = self.simulator.mpc_iteration - 1 #Because already increased in the simulator
        data = self.mpc_data
        data.mpc_states = NP.append(data.mpc_states, [self.simulator.xf_sim], axis = 0)
        data.mpc_control = NP.append(data.mpc_control, [self.optimizer.u_mpc], axis = 0)
        #data.mpc_alg = NP.append(data.mpc_alg, [NP.zeros(NP.size(self.model.z))], axis = 0) # TODO: To be completed for DAEs
        data.mpc_time = NP.append(data.mpc_time, [[self.simulator.t0_sim]], axis = 0)
        data.mpc_cost = NP.append(data.mpc_cost, self.optimizer.opt_result_step.optimal_cost, axis = 0)
        #data.mpc_ref = NP.append(data.mpc_ref, [[0]], axis = 0) # TODO: To be completed
        stats = self.optimizer.solver.stats()
        data.mpc_cpu = NP.append(data.mpc_cpu, [[stats['t_wall_solver']]], axis = 0)
        data.mpc_parameters = NP.append(data.mpc_parameters, [self.simulator.p_real_now(self.simulator.t0_sim)], axis = 0)
        # MHE
        if self.observer.method == "MHE":
            y_scaling = self.model.ocp.y_scaling
            X_offset = self.observer.nlp_dict_out['X_offset']
            U_offset = self.observer.nlp_dict_out['U_offset']
            nx = self.model.x.size(1)
            nu = self.model.u.size(1)
            x_val = NP.reshape(self.observer.optimal_solution[X_offset[-1][0]:X_offset[-1][0]+nx],(1,-1))
            u_val = NP.reshape(self.observer.optimal_solution[U_offset[-1][0]:U_offset[-1][0]+nu],(1,-1))
            data.mhe_est_states = NP.append(data.mhe_est_states,x_val, axis = 0)
            data.mhe_meas_val = NP.append(data.mhe_meas_val,[self.observer.measurement/y_scaling], axis = 0)
            data.mhe_est_states_shift = NP.roll(data.mhe_est_states_shift,-1,axis=1)
            data.mhe_est_states_shift[:,-1] = x_val
            data.mhe_y_meas = NP.roll(data.mhe_y_meas,-1,axis=1)
            data.mhe_y_meas[:,-1] = self.observer.measurement/y_scaling
            data.mhe_u_meas_val = NP.append(data.mhe_u_meas_val,u_val, axis = 0)
            # data.mhe_est_param = NP.roll(data.mhe_est_param,-1,axis=0)
            # data.mhe_est_param[-1,:] = self.observer.observed_param
            # data.mhe_u_meas = NP.roll(data.mhe_u_meas,-1,axis=0)
            # data.mhe_u_meas[-1,:] = self.observer.observed_inputs
        elif self.observer.method == "EKF":
            nx = self.model.x.size(1)
            np = self.model.p.size(1)
            x_val = NP.reshape(self.observer.x_hat_aug[:nx]/self.model.ocp.x_scaling,(1,-1))
            p_val = NP.reshape(self.observer.x_hat_aug[nx:nx+np],(1,-1))
            data.mhe_est_states = NP.append(data.mhe_est_states,x_val,axis=0)
            data.mhe_est_param = NP.append(data.mhe_est_param,p_val,axis=0)
