""" Platform Controller connects a selected client to chair.

"""

import sys
import time
import copy
import Tkinter as tk
import ttk
import tkMessageBox
import traceback
import numpy as np
from math import degrees

sys.path.insert(0, './client')  # the relative dir containing client files
sys.path.insert(0, './coaster')  # the relative dir containing coaster files

from platform_input_tk import InputInterface   #  tkinter gui
#  from platform_input import InputInterface    #  keyboard
#  from platform_input_UDP import InputInterface #  UDP
#  from platform_input_threadedUDP import InputInterface #  threaded UDP
#from coaster_client import InputInterface
from kinematics import Kinematics
from shape import Shape
from platform_output import OutputInterface

isActive = True  # set False to terminate
frameRate = 0.05

client = InputInterface()
chair = OutputInterface()
shape = Shape(frameRate)
k = Kinematics()


class Controller:

    def __init__(self):
        self.prevT = 0
        geometry = chair.get_geometry()
        k.set_geometry( geometry[0],geometry[1],geometry[2])
        shape.begin(chair.get_limits(), "shape.cfg")
        self.is_output_enabled = False

    def init_gui(self, root):
        self.root = root
        self.root.geometry("580x320")
        self.root.iconbitmap('images\ChairIcon3.ico')
        title = client.rootTitle + " for " + chair.get_platform_name()
        self.root.title(title)
        print title
        nb = ttk.Notebook(root)
        page1 = ttk.Frame(nb)  # client
        nb.add(page1, text='  Input  ')
        page2 = ttk.Frame(nb)  # shape
        nb.add(page2, text='  Shape  ')
        page3 = ttk.Frame(nb)  # output
        nb.add(page3, text='  Output ')
        nb.pack(expand=1, fill="both")

        client.init_gui(page1, chair.get_limits())  # give client: min max input values
        shape.init_gui(page2)
        chair.init_gui(page3)

    def update_gui(self):
        self.root.update_idletasks()
        self.root.update()

    def quit(self):
        if client.USE_GUI:
            result = tkMessageBox.askquestion("Shutting Down Platform Software", "Are You Sure you want to quit?", icon='warning')
            if result != 'yes':
                return
        global isActive
        isActive = False

    def enable_platform(self):
        pos = client.get_current_pos()
        actuator_lengths = k.inverse_kinematics(self.process_request(pos))
        #  print "cp", pos, "->",actuator_lengths
        chair.set_enable(True, actuator_lengths)
        self.is_output_enabled = True        
        #  print "enable", pos

    def disable_platform(self):             
        pos = client.get_current_pos()
        #  print "disable", pos
        actuator_lengths = k.inverse_kinematics(self.process_request(pos))
        chair.set_enable(False, actuator_lengths)
        self.is_output_enabled = False

    def swell_for_access(self):
        chair.swell_for_access(4)  # four seconds in up pos

    def process_request(self, request):
        #  print "in process"
        if client.is_normalized:
            #  print "pre shape", request,
            request = shape.shape(request)  # adjust gain & washout and convert from norm to real
            #  print "post",request       
        request = shape.smooth(request)
        ##if self.is_output_enabled:
        return request

    def move(self, position_request):
        #  position_requests are in mm and radians (not normalized)
        start = time.time()
        #  print "req= " + " ".join('%0.2f' % item for item in position_request)
        actuator_lengths = k.inverse_kinematics(position_request)
        if client.USE_GUI:           
            chair.show_muscles(position_request, actuator_lengths)
            controller.update_gui()
        chair.move_platform(actuator_lengths)

        #  print "dur =",  time.time() - start, "interval= ",  time.time() - self.prevT
        #  self.prevT =  time.time()

controller = Controller()


def cmd_func(cmd):  # command handler function cposition_requested from Platform input
    global isActive
    if cmd == "exit":
        isActive = False
    elif cmd == "enable":
        controller.enable_platform()
    elif cmd == "disable":
        controller.disable_platform()
    elif cmd == "swellForStairs":
        controller.swell_for_access()
    elif cmd == "quit":
        # prompts with tk msg box to confirm 
        controller.quit() 


def move_func(request):  # move handler position requested by Platform input
    #  print "request is trans/rot list:", request
    try:
        request = np.array(request)
        r = controller.process_request(request)
        controller.move(r)
    except:
        e = sys.exc_info()[0]  # report error
        s = traceback.format_exc()
        print e, s


def main():

    try:      
        if client.USE_GUI:
            root = tk.Tk()
            controller.init_gui(root)
    except NameError:
        client.USE_GUI = False
        print "GUI Disabled"

    client.begin(cmd_func, move_func)
    previous = time.time()
    chair_status = None
    while isActive:
        if client.USE_GUI:
            controller.update_gui()
        if(time.time() - previous > frameRate):
            previous = time.time()
            if chair_status != chair.get_output_status():
                chair_status = chair.get_output_status()
                client.chair_status_changed(chair_status)
            client.service()
            #  print "in controller, service took", time.time() - previous


if __name__ == "__main__":
    main()
    client.fin()
    chair.fin()
