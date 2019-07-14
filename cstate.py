# -*- coding: utf-8 -*-


class CState(object):
    """
    State class for vehicle model from CommonRoad
    """
    def __init__(self, t=0, x_pos=0, y_pos=0, steering_angle=0, x_vel=0, yaw_angle=0, steering_angle_vel=0, x_acc=0):
        """
        :param t: current time (in sec)
        :param x_pos: vehicle absolute x position
        :param y_pos: vehicle absolute y position
        :param steering_angle: vehicle steering angle
        :param x_vel: vehicle x velocity
        :param yaw_angle: vehicle yaw angle
        :param steering_angle_vel: vehicle steering angle velocity
        :param x_acc: ehicle x acceleration
        """
        self.t = t
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.steering_angle = steering_angle
        self.x_vel = x_vel
        self.yaw_angle = yaw_angle
        self.steering_angle_vel = steering_angle_vel
        self.x_acc = x_acc

    def arr_pos_vel(self):
        """
        :return: vehicle model outputs only
        """
        return [self.x_pos, self.y_pos, self.steering_angle, self.x_vel, self.yaw_angle]


    def arr_acc(self):
        """
        :return: vehicle model inputs only
        """
        return [self.steering_angle_vel, self.x_acc]

    def arr_all_no_t(self):
        """
        :return: vehicle model outputs and inputs
        """
        return self.arr_pos_vel() + self.arr_acc()

    def arr_all_t(self):
        """
        :return: current time followed by vehicle model outputs and inputs
        """
        return [self.t] + self.arr_pos_vel() + self.arr_acc()
