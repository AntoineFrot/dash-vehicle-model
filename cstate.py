
class CState(object):
    def __init__(self, t=0, x_pos=0, y_pos=0, steering_angle=0, x_vel=0, yaw_angle=0, steering_angle_vel=0, x_acc=0):
        self.t = t
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.steering_angle = steering_angle
        self.x_vel = x_vel
        self.yaw_angle = yaw_angle
        self.steering_angle_vel = steering_angle_vel
        self.x_acc = x_acc

    def arr_pos_vel(self):
        return [self.x_pos, self.y_pos, self.steering_angle, self.x_vel, self.yaw_angle]


    def arr_acc(self):
        return [self.steering_angle_vel, self.x_acc]

    def arr_all_no_t(self):
        return self.arr_pos_vel() + self.arr_acc()

    def arr_all_t(self):
        return [self.t] + self.arr_pos_vel() + self.arr_acc()
