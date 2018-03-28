""" kinematics

finds actuator lengths L such that the platform is in position defined by
    a = [surge, sway, heave, roll, pitch yaw]
"""

import math
import copy
import numpy as np


class Kinematics(object):
    def __init__(self):
        pass

    def set_geometry(self, base_pos, platform_pos, platform_mid_height):
        self.base_pos = base_pos
        self.platform_pos = platform_pos
        self.platform_mid_height = platform_mid_height

    """ 
    returns numpy array of actuator lengths for given request orientation
    """
    def inverse_kinematics(self, request):
        adj_req = copy.copy(request)
        adj_req[2] = self.platform_mid_height - adj_req[2]  # z axis displacement value is offset from center 
        a = np.array(adj_req).transpose()
        roll = a[3]  # positive roll is right side down
        pitch = -a[4]  # positive pitch is nose down
        yaw = a[5]  # positive yaw is CCW
        #  Translate platform coordinates into base coordinate system
        #  Calculate rotation matrix elements
        cos_roll = math.cos(roll)
        sin_roll = math.sin(roll)
        cos_pitch = math.cos(pitch)
        sin_pitch = math.sin(pitch)
        cos_yaw = math.cos(yaw)
        sin_yaw = math.sin(yaw)
        #  calculate rotation matrix
        #  Note that it is a 3-2-1 rotation matrix
        Rzyx = np.array([[cos_yaw*cos_pitch, cos_yaw*sin_pitch*sin_roll - sin_yaw*cos_roll, cos_yaw*sin_pitch*cos_roll + sin_yaw*sin_roll],
                         [sin_yaw*cos_pitch, sin_yaw*sin_pitch*sin_roll + cos_yaw*cos_roll, sin_yaw*sin_pitch*cos_roll - cos_yaw*sin_roll],
                         [-sin_pitch, cos_pitch*sin_roll, cos_pitch*cos_roll]])
        #  platform actuators points with respect to the base coordinate system
        xbar = a[0:3] - self.base_pos

        #  orientation of platform wrt base

        uvw = np.zeros(self.platform_pos.shape)
        for i in xrange(6):
            uvw[i, :] = np.dot(Rzyx, self.platform_pos[i, :])

        #  leg lengths are the length of the vector (xbar+uvw)
        L = np.sum(np.square(xbar + uvw), 1)
        return np.sqrt(L)
