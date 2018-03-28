"""
  PlatformInputTk.py

    The platform controller communicates with this client through calls
    to a function named service. This function recieves two parameters,
    the first is the function to be called to execute a command, the second
    parameter is the function to call with movement requests.


     x,y,z,r,p,y
    x is forward/back movement in millimeters (+ is forward)
    y is side to side movement in mm (+ is left)
    z is up/down movement in mm (+ is up)
    r is roll in degrees (+ is left up)
    p is pitch in degrees (+ is nose down)
    y is yaw in degrees (+ is CCW)

    The controller accepts move requests as either actual values (mm and radians)
    or normalized (ranging from -1 to +1). Normalized values are easier to use
    when interfacing to a simulator that has a range of movements greater than
    the platform can achieve. For example, a flight simulator can move forward
    many meters each frame, but the platform movement is limted to under 200mm.
    To use normalized values, send 1 for maximim positive movement and -1 for
    maximum movement in the opposite direction.

   If the application requires gain control or washout then normalized values
    must be used. For example,  norm,1,0,-0.5,0,0,0.10  moves the platform fully
    forward (positive x direction), halfway down (negative z direction), and
    10% positive (CCW) yaw

    To use real world values, send the values as mm and radians.  The range of
    real world values for the platform is passed to the begin function.
    for example :  real,100,0,-50,0,0,0.09 moves 100mm forward, 50mm down,
    0.09 radians (5 degrees) of positive (CCW) yaw
    Note that gain and washout are not available when using real world values

    The minimum interval between calls to receive requests is 50 milliseconds
"""

import sys
import traceback
import Tkinter as tk
import ttk

#  InputParmType = 'realworld'  #  can be 'realworld' or 'normalized'
InputParmType = 'normalized'


class InputInterface(object):
    USE_GUI=True

    def __init__(self):
        self.cmd_func = None
        self.move_func = None
        self.rootTitle = "Chair Test Client"

        if InputParmType == 'normalized':
            self.is_normalized = True
            print 'Expecting normalized input parameters'
        else:
            self.is_normalized = False
            print 'Expecting realworld input parameters'
        print
        #  additional client init code goes here

    def init_gui(self, master, limits):
        self.limits = limits    # note limits are in mm and radians
        self.master = master
        frame = tk.Frame(master)
        frame.pack()

        self.label0 = tk.Label(frame, text="Adjust Translation and Rotation")
        self.label0.pack(fill=tk.X, pady=10)
        self.levels = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        sLabels = ("X", "Y", "Z", "R", "P", "Y")
        for i in range(6):
            s = tk.Scale(frame, from_=1, to=-1, resolution=0.1, length=120,
                         command=lambda g, i=i: self._set_value(i, g), label=sLabels[i])
            s.set(0)
            s.pack(side=tk.LEFT, padx=(6, 4))

        frame2 = tk.Frame(master)
        frame2.pack(fill=tk.X, side=tk.BOTTOM, pady=10)

        self.chair_status_Label = tk.Label(frame2, text="Using Festo Controllers", fg="orange")
        self.chair_status_Label.pack()

        self.enableState = tk.StringVar()
        self.enableState.set('disable')
        self.enable_cb = tk.Checkbutton(frame2, text="Enable", command=self._enable,
                                        variable=self.enableState, onvalue='enable', offvalue='disable')
        self.enable_cb.pack(side=tk.LEFT, padx=220)

        self.close_button = tk.Button(frame2, text="Quit", command=self.quit)
        self.close_button.pack(side=tk.LEFT)

    def chair_status_changed(self, chair_status):
        self.chair_status_Label.config(text=chair_status[0], fg=chair_status[1])

    def _enable(self):
        if(self.cmd_func):
            self.master.update_idletasks()
            self.master.update()
            self.cmd_func(self.enableState.get())

    def quit(self):
        if(self.cmd_func):
            self.cmd_func("quit")

    def _set_value(self, idx, value):
        self.levels[idx] = float(value)
        if self.move_func:
            self.move_func(self.levels)

    def begin(self, cmd_func, move_func):
        self.cmd_func = cmd_func
        self.move_func = move_func

    def fin(self):
        # client exit code goes here
        pass

    def get_current_pos(self):
        return self.levels

    def service(self):
        #nothing to do here because TK updates trigger commands to controller
        pass





