import os
import sys
sys.path.append(os.getcwd()+r'/commonroad-vehicle-models/Python')

from parameters_vehicle2 import parameters_vehicle2
from init_KS import init_KS
from vehicleDynamics_KS import vehicleDynamics_KS
from scipy.integrate import odeint

import numpy

import zmq
import struct
import time
import _thread

from math import radians, degrees

from cstate import CState

T_STEP = 0.01
MAX_STEERING_ANGLE = 15.0  # °
MAX_STEERING_ANGLE_RAD = radians(MAX_STEERING_ANGLE)

MAX_STEERING_ANGLE_VELOCITY_S = 45.0  # °/s
MAX_STEERING_ANGLE_STEP_RAD = radians(MAX_STEERING_ANGLE_VELOCITY_S * T_STEP)

port = "5556"

context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:%s" % port)

last_data = 0


def func_KS(x, t, u, p):
    f = vehicleDynamics_KS(x, u, p)
    return f


# load parameters
p = parameters_vehicle2()
g = 9.81  # [m/s^2]

# states
# x1 = x-position in a global coordinate system
# x2 = y-position in a global coordinate system
# x3 = steering angle of front wheels
# x4 = velocity in x-direction
# x5 = yaw angle

# u1 = steering angle velocity of front wheels
# u2 = longitudinal acceleration

delta0 = 0
vel0 = 15
Psi0 = 0
dotPsi0 = 0
beta0 = 0
sy0 = 0


class UserEntries:

    def __init__(self):
        self.running = True
        self.x_acc = 0.0
        self.steering_angle_target = 0.0

    def thread_func_zmq(self, thread_name, delay):

        port = "5557"

        # Socket to talk to server
        context = zmq.Context()
        socket = context.socket(zmq.SUB)

        socket.connect("tcp://localhost:%s" % port)
        socket.setsockopt_string(zmq.SUBSCRIBE, '')

        while self.running:
            msg = socket.recv()
            steering_angle_target_deg, self.x_acc = struct.unpack('dd', msg)
            self.steering_angle_target = radians(steering_angle_target_deg)

            if self.steering_angle_target > MAX_STEERING_ANGLE_RAD:
                self.steering_angle_target = MAX_STEERING_ANGLE_RAD
            elif self.steering_angle_target < -MAX_STEERING_ANGLE_RAD:
                self.steering_angle_target = -MAX_STEERING_ANGLE_RAD
            print('New values: steering_angle_target {}° and x_acc {} m/s2'.format(degrees(self.steering_angle_target), self.x_acc))
            # time.sleep(.1)

    def start_thread(self):
        try:
            _thread.start_new_thread(self.thread_func_zmq, ("Thread-1", 0.1,))
        except:
            print("Error: unable to start thread")


user_entries = UserEntries()
user_entries.start_thread()

state_crt = CState(0, 0, 0, 0, 0, 0)

t_last = 0.0

count = 0

while True:
    t_next = t_last + T_STEP
    t = numpy.array((t_last, t_next))
    t_last = t_next

    KS = init_KS(state_crt.arr_all_no_t())

    steering_angle_vel = 0
    if user_entries.steering_angle_target >= state_crt.steering_angle + MAX_STEERING_ANGLE_STEP_RAD:
        steering_angle_vel = MAX_STEERING_ANGLE_STEP_RAD
    elif user_entries.steering_angle_target > state_crt.steering_angle:
        steering_angle_vel = (user_entries.steering_angle_target - state_crt.steering_angle)/T_STEP
    elif user_entries.steering_angle_target <= state_crt.steering_angle - MAX_STEERING_ANGLE_STEP_RAD:
        steering_angle_vel = -MAX_STEERING_ANGLE_STEP_RAD
    elif user_entries.steering_angle_target < state_crt.steering_angle:
        steering_angle_vel = (user_entries.steering_angle_target - state_crt.steering_angle)/T_STEP

    if steering_angle_vel != 0:
        print(steering_angle_vel, degrees(state_crt.steering_angle))

    u_goal = [steering_angle_vel, user_entries.x_acc]

    out = odeint(func_KS, KS, t, args=(u_goal, p))

    out_right = out[-1]
    state_crt = CState(t_next, out_right[0], out_right[1], out_right[2], out_right[3], out_right[4], degrees(steering_angle_vel), user_entries.x_acc)

    count += 1
    if count == 10:
        socket.send_pyobj(state_crt)
        count = 0

    time.sleep(.01)
