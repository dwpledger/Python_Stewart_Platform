"""shape module controls gain and washout.

  Shape method expects only normalized values
  and returns actual lengths (using range passed in begin method)

  Smooth method takes either norm or real values and returns moving average
"""

import traceback
import numpy as np
import Tkinter as tk
from moving_average import MovingAverage


class Shape(object):

    def __init__(self, frame_rate):
        #  init code goes here
        self.frame_rate = frame_rate

        # These default values are overwritten with values in config file
        self.moving_average = []
        self.gains = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0])  # xyzrpy gains
        self.master_gain = 1.0
        #  washout_time is number of seconds to decay below 2%
        self.washout_time = [12, 12, 12, 12, 0, 12]        
        self.washout_factor = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        #self.washout_enable = np.array([0, 0, 0, 0, 0, 0])
        for idx, t in enumerate(self.washout_time):
            self.set_washout(idx, self.washout_time[idx])
        self.ma_samples  = [1, 1, 1, 1, 1, 1]
        self.prev_washed = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # previous washout values
        self.prev_value = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # previous request

    #  method to init gui is called after begin method
    def init_gui(self, master):
        self.master = master
        frame = tk.Frame(master)
        frame.pack()

        """
        GUI code below for shape control of ride intensity and washout
        """

        self.label0 = tk.Label(frame, text="Ride Intensity").pack(fill=tk.X, pady=5)

        sLabels = ("X", "Y", "Z", "R", "P", "Y")
        for i in range(6):
            s = tk.Scale(frame, from_=2, to=0, resolution=0.1, length=120,
                         command=lambda g, i=i: self.set_gain(i, g), label=sLabels[i])
            #  print "g=",self.gains[i], "<"
            s.set(float(self.gains[i]))
            s.pack(side=tk.LEFT, padx=(6, 4))

        s = tk.Scale(frame, from_=2, to=0, resolution=0.1, length=120,
                     command=self.set_master_gain, label="Master")
        s.set(self.master_gain)

        s.pack(side=tk.LEFT, padx=(12, 4))

        frame1 = tk.Frame(master)
        frame1.pack(fill=tk.X, side=tk.TOP, pady=2)
        self.label0 = tk.Label(frame1, text="Washout Duration in Seconds    (0 disables washout)           .")
        self.label0.pack(fill=tk.X, pady=2)
        tk.Label(frame1, text="").pack(side=tk.LEFT, padx=(20, 2))
        self.wash_entry_widget = []
        for i in range(6):
            #  washVars.append(StringVar())
            t = tk.Entry(frame1, width=4, validate="focusout",
                         vcmd=lambda i=i: self.set_washout(i, int(self.wash_entry_widget[i].get())))
            self.wash_entry_widget.append(t)
            #  t.set(float(washout_time))
            t.delete(0, tk.END)              # delete current text
            t.insert(0, int(self.washout_time[i]))
            t.pack(side=tk.LEFT, padx=(13, 30))

        frame2 = tk.Frame(master)
        frame2.pack(fill=tk.X, side=tk.BOTTOM, pady=12)
        self.label0 = tk.Label(frame2, text="Moving average Samples    (set in shape.cfg)                  .")
        self.label0.pack(fill=tk.X, pady=2)

        tk.Label(frame2, text="").pack(side=tk.LEFT, padx=(20, 2))
        self.smooth_widget = []
        for i in range(6):
            t = tk.Entry(frame2, width=4)
            self.smooth_widget.append(t)
            t.delete(0, tk.END)              # delete current text
            t.insert(0, self.ma_samples[i])
            t.pack(side=tk.LEFT, padx=(13, 30))
            t.config(state='disabled', justify='center')

        self.update_button = tk.Button(frame2, height=2, width=6, text="Update",
                                       command=self.update_washouts)
        self.update_button.pack(side=tk.LEFT, padx=(0, 4))

        self.save_button = tk.Button(frame2, height=2, width=5, text="Save",
                                     command=self.save_config)
        self.save_button.pack(side=tk.LEFT, padx=(2, 4))

    def begin(self, range, config_fname):
        self.range = range
        self.config_fname = config_fname

        options = self.read_shape_config()
        for option in options:
            if option == 'gains':
                self.gains = [float(i) for i in options['gains']]
                self.gains = np.array(self.gains)
                #  print gains
                #  gains = options['gains']
            elif option == 'master_gain':
                self.master_gain = float(options['master_gain'][0])
                #  print master_gain
            elif option == 'washouts':
                washout_time = [int(i) for i in options['washouts']]
                for idx, t in enumerate(washout_time):
                    self.set_washout(idx, washout_time[idx])
                #  print washout_time
            elif option == 'moving_averages':
                self.ma_samples = [int(i) for i in options['moving_averages']]
                for count in self.ma_samples:
                    self.moving_average.append(MovingAverage(count))

    def fin(self):
        #  exit code goes here
        pass

    def set_gain(self, idx, value):
        self.gains[idx] = value
        #  print "in shape", idx, " gain set to ", value

    def set_master_gain(self, value):
        self.master_gain = float(value)
        #  print "in shape, master gain set to ", value

    def get_master_gain(self):
        return self.master_gain

    def set_washout(self, idx, value):
        #  expects washout duration (time to decay below 2%)
        #  zero disables washout
        self.washout_time[idx] = value
        if value == 0:
            self.washout_factor[idx] = 0
        else:
            self.washout_factor[idx] = 1.0 - self.frame_rate / value * 4
            #  print "in shape", idx, " washout time set to ", value, "decay factor=", self.washout_factor[idx]

    def get_washouts(self):
        #  print "in shape", self.washout_time
        return self.washout_time

    def shape(self, request):
        #  use gain setting to increase or decrease values
        #  print request
        # print "in shape", request, self.gains, self.master_gain
        r = np.multiply(request, self.gains) * self.master_gain

        np.clip(r, -1, 1, r)  # clip normalized values
        #  print "clipped", r       
        for idx, f in enumerate(self.washout_factor):
            #  if washout enabled and request is less than prev washed value, decay more
            if f != 0 and abs(request[idx]) < abs(self.prev_value[idx]):
                #  here if washout is enabled
                r[idx] =  self.prev_value[idx] * self.washout_factor[idx]
        self.prev_value = r       
        #  convert from normalized to real world values
        r = np.multiply(r, self.range)  
        #print "real",r, self.range
        return r

    def smooth(self, request):
        for idx, count in enumerate(self.ma_samples):
            if count > 1:
                request[idx] = self.moving_average[idx].next(request[idx])
        return request

    def update_washouts(self):
        for i in range(6):
            self.set_washout(i, int(self.wash_entry_widget[i].get()))

    def read_shape_config(self):
        options = {}
        try:
            with open(self.config_fname) as f:
                #  config = f.readlines()
                self.config = f.read().splitlines()
                #  print self.config
                for line in self.config:
                    #  First, remove comments:
                    if '#' in line:
                        #  split on comment char, keep only the part before
                        line, comment = line.split('#', 1)
                    #  Second, find lines with an option=value:
                    if '=' in line:
                        #  split on equals:
                        option, value = line.split('=', 1)
                        #  strip spaces:
                        option = option.strip()
                        value = value.strip()
                        value = list(value.split(','))
                        #  print " in parse", option, value
                        #  store in dictionary:
                        options[option] = value
        except IOError:
            print "Unable to open config file:", self.config_fname, "- using default values"

        return options

    def save_config(self):
        with open(self.config_fname, "w") as outfile:
            for line in self.config:
                #  First, remove comments:
                if '#' in line:
                    #  split on comment char, keep only the part before
                    line, comment = line.split('#', 1)
                    outfile.write("#" + comment + "\n")
                #  Second, find lines with an option=value:
                if '=' in line:
                    #  split on equals:
                    option, value = line.split('=', 1)
                    #  strip spaces:
                    option = option.strip()
                    #  print "option=", option
                    if option == 'gains':
                        outfile.write("gains=" + ', '.join(str(g) for g in self.gains) + "\n")
                    elif option == 'master_gain':
                        outfile.write("master_gain=" + str(self.get_master_gain()) + "\n")
                    elif option == 'washouts':
                        outfile.write("washouts=" + ', '.join(str(w) for w in self.get_washouts()) + "\n")
                    elif option == 'moving_averages':
                        outfile.write("moving_averages=" + ', '.join(str(w) for w in self.ma_samples) + "\n")
