# Python Coaster client GUI

import Tkinter as tk
import tkMessageBox
import ttk
from MoveState import MoveState


class CoasterGui(object):

    def __init__(self, dispatch, pause, reset, activate_callback_request, quit_callback):
        self.dispatch = dispatch
        self.pause = pause
        self.reset = reset
        self.activate_callback_request = activate_callback_request
        self.quit = quit_callback

    def init_gui(self, master, limits):
        self.master = master
        frame = tk.Frame(master)
        frame.grid()

        spacer_frame = tk.Frame(master, pady=4)
        spacer_frame.grid(row=0, column=0)
        self.label0 = tk.Label(spacer_frame, text="").grid(row=0)

        self.dispatch_button = tk.Button(master, height=2, width=16, text="Dispatch",
                                         command=self.dispatch, underline=0)
        self.dispatch_button.grid(row=1, column=0, padx=(24, 4))

        self.pause_button = tk.Button(master, height=2, width=16, text="Pause", command=self.pause, underline=0)
        self.pause_button.grid(row=1, column=2, padx=(30))

        self.reset_button = tk.Button(master, height=2, width=16, text="Return to Start",
                                      command=self.reset, underline=0)
        self.reset_button.grid(row=1, column=3, padx=(24))

        label_frame = tk.Frame(master, pady=20)
        label_frame.grid(row=3, column=0, columnspan=4)

        self.coaster_status_label = tk.Label(label_frame, text="Waiting for Coaster Status", font=(None, 24),)
        self.coaster_status_label.grid(row=0, columnspan=2, ipadx=16, sticky=tk.W)

        self.coaster_connection_label = tk.Label(label_frame, fg="red", font=(None, 12),
               text="Coaster Software Not Found (start NL2 or maximize window if already started)")
        self.coaster_connection_label.grid(row=1, columnspan=2, ipadx=16, sticky=tk.W)

        self.remote_status_label = tk.Label(label_frame, font=(None, 12),
                 text="Looking for Remote Control", fg="orange")
        self.remote_status_label.grid(row=2, columnspan=2, ipadx=16, sticky=tk.W)

        self.chair_status_Label = tk.Label(label_frame, font=(None, 12),
                 text="Using Festo Controllers", fg="orange")
        self.chair_status_Label.grid(row=3, column=0, columnspan=2, ipadx=16, sticky=tk.W)

        bottom_frame = tk.Frame(master, pady=16)
        bottom_frame.grid(row=4, columnspan=3)

        self.is_chair_activated = tk.IntVar()
        self.is_chair_activated.set(0)  # disable by default

        self.activation_button = tk.Button(master, underline=0, command=self._enable_pressed)
        self.activation_button.grid(row=4, column=1)
        self.deactivation_button = tk.Button(master, command=self._disable_pressed)
        self.deactivation_button.grid(row=4, column=2)
        self.set_activation_buttons(False)

        self.close_button = tk.Button(master, text="Shut Down and Exit", command=self.quit)
        self.close_button.grid(row=4, column=3)

        self.label1 = tk.Label( bottom_frame, text="     ").grid(row=0, column=1)

        self.org_button_color = self.dispatch_button.cget("background")

        master.bind("<Key>", self.hotkeys)

    def _enable_pressed(self):
        #  self.set_activation_buttons(True)
        self.activate_callback_request(True)

    def _disable_pressed(self):
        #  self.set_activation_buttons(False)
        self.activate_callback_request(False)

    def set_activation_buttons(self, isEnabled):  # callback from Client
        if isEnabled:
            self.activation_button.config(text="Activated ", relief=tk.SUNKEN)
            self.deactivation_button.config(text="Deactivate", relief=tk.RAISED)
        else:
            self.activation_button.config(text="Activate ", relief=tk.RAISED)
            self.deactivation_button.config(text="Deactivated", relief=tk.SUNKEN)

    def set_coaster_connection_label(self, label):
        self.coaster_connection_label.config(text=label[0], fg=label[1])

    def chair_status_changed(self, chair_status):
        self.chair_status_Label.config(text=chair_status[0], fg=chair_status[1])

    def set_remote_status_label(self, label):
        self.remote_status_label.config(text=label[0], fg=label[1])

    def hotkeys(self, event):
        print "pressed", repr(event.char)
        if event.char == 'd':  # ignore case
            self.dispatch()
        if event.char == 'p':
            self.pause()
        if event.char == 'r':
            self.reset()
        if event.char == 'e':
            self.emergency_stop()
        """ todo ?
        if event.char == 'a':
            if self.isActivated():
                #print "in hotkeys, cposition_requesting deactivate"
                self.deactivate()
            else:
                #print "in hotkeys, cposition_requesting activate"
                self.activate()
        """
    def process_state_change(self, new_state, isActivated):
        #  print "in process state change, new state is", new_state
        if new_state == MoveState.READY_FOR_DISPATCH:
            if isActivated:
                print "Coaster is Ready for Dispatch"
                self.dispatch_button.config(relief=tk.RAISED, state=tk.NORMAL)
                self.coaster_status_label.config(text="Coaster is Ready for Dispatch", fg="green3")
            else:
                print "Coaster at Station but deactivated"
                self.dispatch_button.config(relief=tk.RAISED, state=tk.DISABLED)
                self.coaster_status_label.config(text="Coaster at Station but deactivated", fg="orange")

            self.pause_button.config(relief=tk.RAISED, state=tk.DISABLED)
            self.reset_button.config(relief=tk.RAISED, state=tk.DISABLED)

        elif new_state == MoveState.RUNNING:
            self.dispatch_button.config(relief=tk.SUNKEN, state=tk.DISABLED)
            self.pause_button.config(relief=tk.RAISED, state=tk.NORMAL)
            self.reset_button.config(relief=tk.RAISED, state=tk.DISABLED)
            self.coaster_status_label.config(text="Coaster is Running", fg="green3")
        elif new_state == MoveState.PAUSED:
            self.dispatch_button.config(relief=tk.SUNKEN, state=tk.DISABLED)
            self.pause_button.config(relief=tk.SUNKEN, state=tk.NORMAL)
            self.reset_button.config(relief=tk.RAISED, state=tk.NORMAL)
            self.coaster_status_label.config(text="Coaster is Paused", fg="orange")
        elif new_state == MoveState.EMERGENCY_STOPPED:
            self.dispatch_button.config(relief=tk.SUNKEN, state=tk.DISABLED)
            self.pause_button.config(relief=tk.SUNKEN, state=tk.DISABLED)
            self.reset_button.config(relief=tk.RAISED, state=tk.NORMAL)
            self.coaster_status_label.config(text="Emergency Stop", fg="red")
        elif new_state == MoveState.RESETTING:
            self.dispatch_button.config(relief=tk.SUNKEN, state=tk.DISABLED)
            self.pause_button.config(relief=tk.RAISED, state=tk.DISABLED)
            self.reset_button.config(relief=tk.SUNKEN, state=tk.DISABLED)
            self.coaster_status_label.config(text="Coaster is returning to station", fg="blue")
