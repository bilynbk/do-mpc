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

# This is the main path of your do-mpc installation relative to the execution folder
path_do_mpc = '../../'
# Add do-mpc path to the current directory
import sys
sys.path.insert(0,path_do_mpc+'code')
# Do not write bytecode to maintain clean directories
sys.dont_write_bytecode = True

# Start CasADi
from casadi import *
# Import do-mpc core functionalities
import core_do_mpc
# Import do-mpc plotting and data managament functions
import data_do_mpc
import numpy as NP
import pdb
"""
-----------------------------------------------
do-mpc: Definition of the do-mpc configuration
-----------------------------------------------
"""

# Import the user defined modules
import template_model
import template_model_observer
import template_optimizer
import template_observer
import template_EKF
import template_MHE
import template_simulator

# Create the objects for each module
model_1 = template_model.model()
# model_observer = template_model_observer.model()
# Create an optimizer object based on the template and a model
optimizer_1 = template_optimizer.optimizer(model_1)
# Create an observer object based on the template and a model
# observer_1 = template_observer.observer(model_1)
# observer_1 = template_EKF.observer(model_observer)
# pdb.set_trace()
observer_1 = template_MHE.observer(model_1)
# Create a simulator object based on the template and a model
simulator_1 = template_simulator.simulator(model_1)
# Create a configuration
configuration_1 = core_do_mpc.configuration(model_1, optimizer_1, observer_1, simulator_1)

"""
----------------------------
do-mpc: MPC loop
----------------------------
"""
while (configuration_1.simulator.t0_sim + configuration_1.simulator.t_step_simulator < configuration_1.optimizer.t_end):

    """
    ----------------------------
    do-mpc: Optimizer
    ----------------------------
    """
    # Make one optimizer step (solve the NLP)
    if configuration_1.simulator.t0_sim == 0:
        configuration_1.make_step_optimizer()
    # The input in this case are the perfect masurements acc1, gyr1, acc2, gyr2
    configuration_1.optimizer.u_mpc = configuration_1.simulator.tv_u_real_now(configuration_1.simulator.t0_sim)[0]
    # For the estimation we use measurements with noise
    configuration_1.optimizer.u_mpc_meas = configuration_1.simulator.tv_u_real_now(configuration_1.simulator.t0_sim)[1]
    """
    ----------------------------
    do-mpc: Simulator
    ----------------------------
    """
    # Simulate the system one step using the solution obtained in the optimization
    # configuration_1.make_step_simulator()

    """
    ----------------------------
    do-mpc: Observer
    ----------------------------
    """
    # Make one observer step
    configuration_1.make_step_observer()

    """
    ------------------------------------------------------
    do-mpc: Prepare next iteration and store information
    ------------------------------------------------------
    """
    # Store the information
    configuration_1.store_mpc_data()

    # Set initial condition constraint for the next iteration
    configuration_1.prepare_next_iter()

    print("current time:", configuration_1.simulator.t0_sim)
    """
    ------------------------------------------------------
    do-mpc: Plot MPC animation if chosen by the user
    ------------------------------------------------------
    """
    # Plot animation if chosen in by the user
    data_do_mpc.plot_animation(configuration_1)

"""
------------------------------------------------------
do-mpc: Plot the closed-loop results
------------------------------------------------------
"""

# Export to matlab if wanted
data_do_mpc.export_to_matlab(configuration_1)

data_do_mpc.plot_mpc(configuration_1)

input("Press Enter to exit do-mpc...")
