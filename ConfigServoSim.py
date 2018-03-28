"""
Created 1 july 2017
@author: mem 
configuration for Servo simulator
"""


import math 
import copy
import numpy 
import matplotlib.pyplot as plt    #for testing  

PLATFORM_NAME = "SERVO_SIM"      

OutSerialPort = 'COM9'

# the next two are not used for servo
PLATFORM_UNLOADED_WEIGHT = 45  # weight of moving platform without 'passenger' in killograms   
DEFAULT_PAYLOAD_WEIGHT = 65    # weight of 'passenger' 

MIN_ACTUATOR_LEN  = 180
MAX_ACTUATOR_LEN =  215   # total actuator distance inclduing fixing hardware 

MAX_ACTUATOR_RANGE =  MAX_ACTUATOR_LEN - MIN_ACTUATOR_LEN
MID_ACTUATOR_LEN  =  MIN_ACTUATOR_LEN + (MAX_ACTUATOR_RANGE/2)


#uncomment this to define attachment locations using angles and distance from origin (vectors)
#only the left side is needed (as viewed facing the chair), the other side is calculated for you

_baseAngles    = [302, 295, 185]   # enter angles from origin to attach point
_baseMagnitude = [67, 67, 67]

#Platform attachment vectors
_platformAngles    = [355, 245, 240] # enter angles from origin to attach point
_platformMagnitude = [65, 65, 65] # enter distance from origin to attach point 

#convert to radians and calculate x and y coordinates using sin and cos of angles
_baseAngles  = [math.radians(x) for x in _baseAngles]
base_pos     = [[m*math.cos(a),m*math.sin(a),0]  for a,m in zip(_baseAngles,_baseMagnitude)]

_platformAngles  = [math.radians(x) for x in _platformAngles]
platform_pos     = [[m*math.cos(a),m*math.sin(a),0]  for a,m in zip(_platformAngles,_platformMagnitude)]

"""

#uncomment this to enter hard coded coordinates

# input x and y coordinates with origin as center of the base plate
# the z value should be zero for both base and platform
# only -Y side is needed as other side is symmetrical (see figure)
basePos     = [
                 [ 331.2 -530.   0. ],  #first upper attachment point 
                 [ 264.1 -566.4  0. ],
                 [-622.6  -54.5  0. ]
                       
              ] 
          
platformPos = [
                 [ 622.6  -54.5  0. ]
                 [-264.1 -566.4  0. ]
                 [-312.5 -541.3  0. ]             
              ]

"""

#todo can we calculate the following?
platform_1dof_limits = [60,60,25,math.radians(25),math.radians(25),math.radians(20)] # the max movement in a single DOF 
platform_6dof_limits = [30,30,12,math.radians(12),math.radians(12),math.radians(10)] # limits at extremes of movement

