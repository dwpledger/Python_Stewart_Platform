"""
  platform_input_threadedUDP.py

  Receives UDP messages on port 10009
  Move messages are: "xyzrpy,x,y,z,r,p,y,\n"
  xyz are translations in mm, rpy are roatations in radians
  however if self.is_normalized is set True, range for all fields is -1 to +1
  
  Command messages are:
  "command,enable,\n"   : activate the chair for movement
  "command,disable,\n"  : disable movement and park the chair
  "command,exit,\n"     : shut down the application
"""

import sys
import socket
from math import radians
import threading
from Queue import Queue
import traceback


class InputInterface(object):
    def __init__(self):
        self.USE_GUI = True  # set True if using tkInter
        #  set True if input range is -1 to +1
        self.is_normalized = False
        if self.is_normalized:
            print 'Platform Input is UDP with normalized parameters'
        else:
            print 'Platform Input is UDP with realworld parameters'
        self.rootTitle = "UDP Platform Interface"
        self.inQ = Queue()
        t = threading.Thread(target=self.listener_thread, args=(self.inQ,))
        t.daemon = True
        t.start()

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
        # move request returns translations as mm and angles as radians
        msg = None
        # throw away all but most recent message
        while not self.inQ.empty():
            msg = self.inQ.get()
        if msg is not None:
            msg = msg.rstrip()
            print msg
            fields = msg.split(",")
            field_list = list(fields)
            if field_list[0] == "xyzrpy":
                try:
                    r = [float(f) for f in field_list[1:7]]
                    # remove next 3 lines if angles passed as radians 
                    r[3] = radians(r[3])
                    r[4] = radians(r[4])
                    r[5] = radians(r[5])
                    #  print r
                    if move_func:
                        self.move_func(r)
                except:  # if not a list of floats, process as command
                    e = sys.exc_info()[0]
                    print "UDP svc err", e
            elif field_list[0] == "command":
                print "command is {%s}:" % (field_list[1])
                if self.cmd_func:
                    self.cmd_func(field_list[1])

    def listener_thread(self, inQ):
        HOST, PORT = "localhost", 10009
        self.MAX_MSG_LEN = 80
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client.bind((HOST, PORT))
        print "opening socket on", PORT
        self.inQ = inQ
        while True:
            try:
                msg = client.recv(self.MAX_MSG_LEN)
                self.inQ.put(msg)
            except:
                e = sys.exc_info()[0]
                s = traceback.format_exc()
                print "listener err", e, s
