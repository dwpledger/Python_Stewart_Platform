"""
 coaster_client control module for NoLimits2.
 
 module coordinates chair activity with logical coaster state 
 NL2 coaster should be at station in manual mode at startup
"""

import sys
import socket
import time
import win32gui, win32api, win32con, ctypes
import tkMessageBox

from coaster_interface import CoasterInterface
from coaster_gui import CoasterGui
from MoveState import MoveState
from serial_remote import SerialRemote


class CoasterEvent:
    ACTIVATED, DISABLED, PAUSED, UNPAUSED, DISPATCHED, ESTOPPED, STOPPED, RESETEVENT = range(8)


#  this state machine determines current coaster state from button and telemetry events
class State(object):
    def __init__(self, position_requestCB):
        self._state = None
        self._state = MoveState.UNKNOWN
        self.position_requestCB = position_requestCB
        self.is_chair_active = False
        self.prev_event = None  # only used for debug

    @property
    def state(self):
        """the 'state' property."""
        return self._state

    @state.setter
    def state(self, value):
        self._state = value

    def set_is_chair_active(self, isActive):
        self.is_chair_active = isActive

    def __str__(self):
        return self.string(self._state)

    @staticmethod
    def string(state):
        return ("Unknown", "ReadyForDispatch", "Running", "Paused",
                "EmergencyStopped", "Resetting")[state]

    def coaster_event(self, event):
        if event != self.prev_event:
            self.prev_event = event

        if self.is_chair_active:
            if event == CoasterEvent.STOPPED and self._state != MoveState.READY_FOR_DISPATCH:
                # here if stopped at station
                self._state = MoveState.READY_FOR_DISPATCH
                self._state_change()
            elif event == CoasterEvent.DISPATCHED and self._state != MoveState.RUNNING:
                self._state = MoveState.RUNNING
                self._state_change()
            elif event == CoasterEvent.PAUSED and self._state != MoveState.PAUSED:
                self._state = MoveState.PAUSED
                self._state_change()
            elif event == CoasterEvent.UNPAUSED and self._state == MoveState.PAUSED:
                self._state = MoveState.RUNNING
                self._state_change()
            elif event == CoasterEvent.DISABLED and self._state != EMERGENCY_STOPPED:
                self._state = MoveState.EMERGENCY_STOPPED
                self._state_change()

        else:
            #  things to do if chair has been disabled:
            if event == CoasterEvent.RESETEVENT and self._state != MoveState.RESETTING:
                #  print "got reset event"
                self._state = MoveState.RESETTING
                self._state_change()
            elif event == CoasterEvent.ESTOPPED and self._state != MoveState.EMERGENCY_STOPPED:
                self._state = MoveState.EMERGENCY_STOPPED
                self._state_change()
            if event == CoasterEvent.STOPPED and self._state != MoveState.READY_FOR_DISPATCH:
                #  here if stopped at station
                self._state = MoveState.READY_FOR_DISPATCH
                self._state_change()

    def _state_change(self):
        if self.position_requestCB is not None:
            self.position_requestCB(self._state)  # tell user interface that state has changed


class InputInterface(object):
    USE_GUI = True

    def __init__(self):
        self.cmd_func = None
        self.is_normalized = True
        self.current_pos = []
        self.is_chair_activated = False
        self.coaster = CoasterInterface()
        self.gui = CoasterGui(self.dispatch, self.pause, self.reset, self.set_activate_state, self.quit)
        actions = {'detected remote': self.detected_remote, 'activate': self.activate,
                   'deactivate': self.deactivate, 'pause': self.pause, 'dispatch': self.dispatch,
                   'reset': self.reset, 'emergency_stop': self.emergency_stop}
        self.RemoteControl = SerialRemote(actions)
        self.prev_movement_time = 0  # holds the time of last reported movement from NoLimits
        self.isNl2Paused = False
        self.coasterState = State(self.process_state_change)
        self.rootTitle = "NL2 Coaster Ride Controller"  # the display name in tkinter

    def init_gui(self, master, limits):
        self.gui.init_gui(master, limits)
        self.master = master

    def _sleep_func(self, duration):
        start = time.time()
        while time.time() - start < duration:
            self.master.update_idletasks()
            self.master.update()
            win32gui.PumpWaitingMessages()

    def check_is_stationary(self, speed):
        if speed < 0.001:
            if time.time() - self.prev_movement_time > 3:
                return True
        else:
            self.prev_movement_time = time.time()
        return False

    def command(self, cmd):
        if self.cmd_func is not None:
            print "Requesting command with", cmd
            self.cmd_func(cmd)

    def dispatch(self):
        if self.is_chair_activated and self.coasterState.state == MoveState.READY_FOR_DISPATCH:
            print 'dispatch'
            self.coasterState.coaster_event(CoasterEvent.DISPATCHED)
            self.coaster.close_harness()
            #  self.command("activate")
            self._sleep_func(2)
            self.coaster.dispatch()
            self.prev_movement_time = time.time()  # set time that train started to move

    def pause(self):
        if self.coasterState.state in (MoveState.RUNNING, MoveState.PAUSED, MoveState.EMERGENCY_STOPPED):
            self.coaster.toggle_pause()

    def reset(self):
        if self.coasterState.state == MoveState.EMERGENCY_STOPPED:
            #  here after disabling while coaster is RUNNING
            self.coaster.toggle_pause()
            if self.is_chair_activated is True:
                self.command("disable")  # should already be deactivated but to be sure
            self.coasterState.coaster_event(CoasterEvent.RESETEVENT)
            #  self.openHarness()
            print 'Moving train to station at high speed'
            self.coaster.increase_speed(4)  # 4x is max speed
        elif self.coasterState.state == MoveState.RESETTING or self.coasterState.state == MoveState.READY_FOR_DISPATCH:
            #  here if reset pressed after estop and before dispatching
            print "command in PlatformOutput to move from current to wind down, wait, then back to current pos"
            self.command("swellForStairs")

    def emergency_stop(self):
        print "legacy emergency stop callback"
        self.deactivate()

    def set_activate_state(self, state):
        #  print "in setActivatedState", state
        if state:
            self.activate()
        else:
            self.deactivate()

    def activate(self):
        #  only activate if coaster is ready for dispatch
        if self.coasterState.state == MoveState.READY_FOR_DISPATCH:
            #  print "in activate "
            self.is_chair_activated = True
            self.coasterState.set_is_chair_active(True)
            self.command("enable")
            self.gui.set_activation_buttons(True)
            self.gui.process_state_change(self.coasterState.state, True)
            self.coaster.set_normal_speed()  # sets speed to 1 if set higher after estop
        else:
            print "Not activating because not ready for dispatch"

    def deactivate(self):
        #  print "in deactivate "
        self.command("disable")
        self.gui.set_activation_buttons(False)
        self.is_chair_activated = False
        self.coasterState.set_is_chair_active(False)
        if self.coasterState.state == MoveState.RUNNING:
            self.pause()
            print 'emergency stop '
            self.coasterState.coaster_event(CoasterEvent.ESTOPPED)
        else:
            self.coasterState.coaster_event(CoasterEvent.DISABLED)
        self.gui.process_state_change(self.coasterState.state, False)

    def quit(self):
        self.command("quit")

    def detected_remote(self, info):
        if "Detected Remote" in info:
            self.set_remote_status_label((info, "green3"))
        elif "Looking for Remote" in info:
            self.set_remote_status_label((info, "orange"))
        else:
            self.set_remote_status_label((info, "red"))

    def set_coaster_connection_label(self, label):
        self.gui.set_coaster_connection_label(label)

    def chair_status_changed(self, chair_status):
        self.gui.chair_status_changed(chair_status)

    def set_remote_status_label(self, label):
        self.gui.set_remote_status_label(label)

    def process_state_change(self, new_state):
        if new_state == MoveState.READY_FOR_DISPATCH and self.is_chair_activated:
            #  here at the end of a ride
            self.command("disembark")
        self.gui.process_state_change(new_state, self.is_chair_activated)

    def begin(self, cmd_func, move_func):
        self.cmd_func = cmd_func
        self.move_func = move_func
        self.coaster.begin()
        while not self.coaster.is_NL2_accessable():
            self.master.update_idletasks()
            self.master.update()
            result = tkMessageBox.askquestion("Waiting for NoLimits Coaster", "Coaster Sim not found, Start NoLimits and press Yes to retry, No to quit", icon='warning')
            if result == 'no':
                sys.exit(0)

        while True:
            self.master.update_idletasks()
            self.master.update()
            if self.coaster.connect_to_coaster():
                #  print "connected"
                self.coaster.set_manual_mode()
                break
            else:
                print "Failed to connect to coaster"
                print "Use shortcut to run NoLimits2 in Telemetry mode"

        if self.coaster.is_NL2_accessable():
            self.gui.set_coaster_connection_label(("Coaster Software Connected", "green3"))
        else:
            self.gui.set_coaster_connection_label(("Coaster Software Not Found"
                                                "(start NL2 or maximize window if already started)", "red"))

    def fin(self):
        # client exit code goes here
        pass

    def get_current_pos(self):
        return self.current_pos
        
    def service(self):      
        self.RemoteControl.service()
        input_field = self.coaster.get_telemetry()
        #print "data from coaster", input_field
        if self.coaster.get_telemetry_status() and input_field and len(input_field) == 3:
            self.gui.set_coaster_connection_label(("Receiving Coaster Telemetry", "green3"))
            isRunning = input_field[0]
            speed = float(input_field[1])
            self.isNl2Paused = not isRunning
            if isRunning:
                if self.check_is_stationary(speed):
                    self.coasterState.coaster_event(CoasterEvent.STOPPED)
                    #  here if coaster not moving and not paused
                    #  print "Auto Reset"
                else:
                    if self.coasterState.state == MoveState.UNKNOWN:
                        # coaster is moving at startuo
                        self.coasterState.coaster_event(CoasterEvent.RESETEVENT)
                    else:
                        self.coasterState.coaster_event(CoasterEvent.UNPAUSED)
 

            else:
                self.coasterState.coaster_event(CoasterEvent.PAUSED)
            #  print isRunning, speed
            
            if len(input_field[2]) == 6:
                self.current_pos = [float(f) for f in input_field[2]]                
            if self.is_chair_activated and self.coasterState.state != MoveState.READY_FOR_DISPATCH:
                # only send if activated and not waiting in station 
                if self.move_func is not None:                
                    self.move_func(self.current_pos)
        else:
            errMsg = format("Telemetry error: %s" % self.coaster.get_telemetry_err_str())
            #  print errMsg
            self.gui.set_coaster_connection_label((errMsg, "red"))
