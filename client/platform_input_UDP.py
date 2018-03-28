"""
  PlatformInputUDP.py

  Receives UDP messages on port 10009
  Move messages are: "xyzrpy,x,y,z,r,p,y,\n"
  xyz (surge, sway, heave) are translations in mm
  rpy (roll, pitch, yaw) are rotations in radians
  however if self.is_normalized is set True, range for all fields is -1 to +1
  
  Command messages are:
  "command,enable,\n"   : activate the chair for movement
  "command,disable,\n"  : disable movement and park the chair
  "command,exit,\n"     : shut down the application
"""

import sys
import socket
from math import radians


class InputInterface(object):
    def __init__(self):
        self.USE_GUI = False  # set True if using tkInter
        self.rootTitle = "UDP Platform Interface"
        HOST, PORT = "localhost", 10009
        self.MAX_MSG_LEN = 80
        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.timeout = 2
        self.client.settimeout(self.timeout)
        self.client.bind((HOST, PORT))
        self.is_normalized = False
        print 'Platform Input is UDP with realworld parameters'

    def init_gui(self, root, limits):
        pass

    def chair_status_changed(self, chair_status):
        print(chair_status[0])

    def begin(self, cmd_func, move_func):
        self.cmd_func = cmd_func
        self.move_func = move_func

    def fin(self):
        # client exit code goes here
        pass

    def service(self):
        # block until a message is received from UDP
        # move request returns translations as mm and angles as radians
        print "Waiting for UDP message on port", 10009
        try:
            msg = self.client.recv(self.MAX_MSG_LEN)
            print "incoming msg:", msg
            fields = msg.split(",")
            field_list = list(fields)
            if field_list[0] == "xyzrpy":
                try:
                    r = [float(f) for f in field_list[1:7]]
                    r[3] = radians(r[3])
                    r[4] = radians(r[4])
                    r[5] = radians(r[5])
                    #  print r
                    self.move_func(r)
                except:  # if not a list of floats, process as command
                    e = sys.exc_info()[0]
                    print e
            elif field_list[0] == "command":
                #  print "command is {%s}, len = %d:" %( field_list[1], len(field_list[1]))
                self.cmd_func(field_list[1])
        except socket.timeout:
            pass
        except:
            e = sys.exc_info()[0]
            print e
