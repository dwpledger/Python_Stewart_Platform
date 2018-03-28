"""
coaster_interface module provides control to and telemetry from coaster.

config nl2:
in setup enable ShowCursor (use M key)
Dispatch key should be I
Day nite cycle to 99999 minutes
"""

import socket
from time import time,sleep
from struct import *
import collections
from quaternion import Quaternion
from math import pi, degrees
import sys
import threading
#  import  binascii  # only for debug

import win32gui, win32api, win32con, ctypes


class CoasterInterface():

    N_MSG_OK = 1
    N_MSG_ERROR = 2
    N_MSG_GET_VERSION = 3
    N_MSG_VERSION = 4
    N_MSG_GET_TELEMETRY = 5
    N_MSG_TELEMETRY = 6
    N_MSG_SET_MANUAL_MODE = 16
    N_MSG__DISPATCH = 17
    c_nExtraSizeOffset = 9  # Start of extra size data within message

    telemetryMsg = collections.namedtuple('telemetryMsg', 'state, frame, viewMode, coasterIndex,\
                                           coasterStyle, train, car, seat, speed, posX, posY,\
                                           posZ, quatX, quatY, quatZ, quatW, gForceX, gForceY, gForceZ')

    def __init__(self):
        self.coaster_buffer_size = 1024
        self.coaster_ip_addr = 'localhost'
        self.coaster_port = 15151
        self.interval = .05  # time in seconds between telemetry requests
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.id = 1
        #  self.client.send(self._create_simple_message(self.id, self.N_MSG_GET_VERSION))
        #  following is for windows interface
        self.nl2Hwnd = None
        self.speed_multiplier = 0  # 0 is normal speed, changed to 4 when running to station at high speed
        self.telemetry_err_str = "Waiting to connect to NoLimits Coaster"
        self.telemetry_status_ok = False
        self.prev_yaw = None
        self.prev_time = time()
        self.lift_height = 32  # max height in meters

    def begin(self):
        windowClass = "NL3D_MAIN_{7F825CE1-21E4-4C1B-B657-DE6FCD9AEB12}"
        self.nl2Hwnd = win32gui.FindWindow(windowClass, None)  # store the window handle
        #  print "nl2 handle = ", self.nl2Hwnd
        self.guiHwnd = win32gui.FindWindow(None, "NL2 Coaster Ride Controller")
        #  print "gui window is ", self.guiHwnd

    def is_NL2_accessable(self):
        windowClass = "NL3D_MAIN_{7F825CE1-21E4-4C1B-B657-DE6FCD9AEB12}"
        self.nl2Hwnd = win32gui.FindWindow(windowClass, None)  # store the window handle
        #print "NL2 window is ", self.nl2Hwnd, self.nl2Hwnd != 0
        return self.nl2Hwnd != 0

    def send_windows_key(self, scancode, key):
        #  print scancode, key
        lparam = 1 + (scancode << 16)
        win32api.SendMessage(self.nl2Hwnd, win32con.WM_KEYDOWN, key, lparam)
        win32api.SendMessage(self.nl2Hwnd, win32con.WM_CHAR, key, lparam)
        win32api.SendMessage(self.nl2Hwnd, win32con.WM_KEYUP, key, lparam)

    def increase_speed(self, steps):
        for _ in range(steps):
            self.send_windows_key(0x4e, ord(' '))   # num+
            #  self.sleepFunc(.1)
        self.speed_multiplier = steps
        #  print  "in inc, speed_multiplier",self.speed_multiplier

    def decrease_speed(self, steps):
        for _ in range(steps):
            self.send_windows_key(0x4a, ord(' '))   # num+
            #  self.sleepFunc(.1)
        self.speed_multiplier = self.speed_multiplier - steps
        #  print  "in dec speed_multiplier",self.speed_multiplier

    def set_normal_speed(self):
        while self.speed_multiplier:
            self.send_windows_key(0x4a, ord(' '))  # num+
            #  self.sleepFunc(.1)
            self.speed_multiplier = self.speed_multiplier - 1
            print "in set norm speed, speed_multiplier", self.speed_multiplier

    def toggle_pause(self):
        print 'pause'
        self.send_windows_key(0x19, ord('P'))

    def dispatch(self):
        if self.speed_multiplier > 0:
            print "speed_multiplier", self.speed_multiplier
            self.decrease_speed(self.speed_multiplier)
        msg = pack('>ii', 0, 0)  # coaster, station
        r = self._create_NL2_message(self.N_MSG__DISPATCH, 9, msg)
        #  print "dispatch msg",  binascii.hexlify(msg),len(msg), "full", binascii.hexlify(r)
        self.client.send(r)

        #  self.send_windows_key(0x17, ord('I'))

    def open_harness(self):
        print 'Opening Harness'
        self.send_windows_key(0x48, ord('8'))

    def close_harness(self):
        print 'Closing Harness'
        self.send_windows_key(0x50, ord('2'))

    def set_manual_mode(self):
        msg = pack('>ii?', 0, 0, True)  # coaster, car, True sets manual mode, false sets auto
        r = self._create_NL2_message(self.N_MSG_SET_MANUAL_MODE, 0, msg)
        #  print "set mode msg", binascii.hexlify(r)
        self.client.send(r)

    def get_telemetry(self):
            #  returns err
            self.client.send(self._create_simple_message(self.id, self.N_MSG_GET_TELEMETRY))
            data = self.client.recv(self.coaster_buffer_size)
            if data and len(data) >= 10:
                #  print "data len",len(data)
                msg, requestId, size = (unpack('>HIH', data[1:9]))
                #  print msg, requestId, size
                if msg == self.N_MSG_VERSION:
                    v0, v1, v2, v3 = unpack('cccc', data[self.c_nExtraSizeOffset:self.c_nExtraSizeOffset+4])
                    print 'NL2 version', chr(ord(v0)+48), chr(ord(v1)+48), chr(ord(v2)+48), chr(ord(v3)+48)
                    self.client.send(self._create_simple_message(self.id, self.N_MSG_GET_TELEMETRY))
                elif msg == self.N_MSG_TELEMETRY:
                    if size == 76:
                        t = (unpack('>IIIIIIIIfffffffffff', data[self.c_nExtraSizeOffset:self.c_nExtraSizeOffset+76]))
                        tm = self.telemetryMsg._make(t)
                        #print "tm", tm
                        formattedData = self._process_telemetry_msg(tm)
                        self.telemetry_status_ok = True
                        return formattedData
                    else:
                        print 'invalid msg len expected 76, got ', size
                    sleep(self.interval)
                    self.client.send(self._create_simple_message(self.id, self.N_MSG_GET_TELEMETRY))
                elif msg == self.N_MSG_OK:
                    self.telemetry_status_ok = True
                    pass
                elif msg == self.N_MSG_ERROR:
                    self.telemetry_status_ok = False
                    self.telemetry_err_str = data[self.c_nExtraSizeOffset:-1]
                    #  print "err:", self.telemetry_err_str
                else:
                    print 'unhandled message', msg

    def get_telemetry_err_str(self):
        return self.telemetry_err_str

    def get_telemetry_status(self):
        return self.telemetry_err_str

    def _process_telemetry_msg(self, msg):
        #  this version only creates a normalized message
        if(msg.state & 1):  # only process if coaster is in play
            if(False):
                #  code here is non-normalized (real) translation and rotation messages
                quat = Quaternion(msg.quatX, msg.quatY, msg.quatZ, msg.quatW)
                pitch = degrees(quat.toPitchFromYUp())
                yaw = degrees(quat.toYawFromYUp())
                roll = degrees(quat.toRollFromYUp())
                #print format("telemetry %.2f, %.2f, %.2f" % (roll, pitch, yaw))
            else:  # normalize
                quat = Quaternion(msg.quatX, msg.quatY, msg.quatZ, msg.quatW)
                roll = quat.toRollFromYUp() / pi
                pitch = -quat.toPitchFromYUp()  # / pi               
                yaw = -quat.toYawFromYUp() 
                if self.prev_yaw != None:
                    delta = time() - self.prev_time
                    self.prev_time = time()
                    yaw_rate = (self.prev_yaw - yaw) / delta
                else:
                    yaw_rate = 0
                self.prev_yaw = yaw
                #data = [msg.gForceX, msg.posX, msg.gForceY-1, msg.posY, msg.gForceZ, msg.posZ]
                data = [msg.gForceX, msg.gForceY-1, msg.gForceZ]
                
                #  y from coaster is vertical
                #  z forward
                #  x side               
                if msg.posY > self.lift_height:
                   self.lift_height = msg.posY
                surge = max(min(1.0, msg.gForceZ), -1)
                sway = max(min(1.0, msg.gForceX), -1)
                heave = ((msg.posY * 2) / self.lift_height) -1
                #print "heave", heave

                data = [surge, sway, heave, roll, pitch, yaw_rate]
                formattedData = ['%.3f' % elem for elem in data]
                isRunning = msg.state == 3        # 3 is running, 7 is paused
                status = [isRunning, msg.speed]
                #print "formatteddata", formattedData
                #  self.coaster_msg_q.put(formattedData)
                return [isRunning, msg.speed, formattedData]

            ##if( msg.posX != 0 and msg.posY !=0):
            ##print msg.posX, msg.posY, msg.posZ, pitch, yaw, roll
            #print "pitch=", degrees( quat.toPitchFromYUp()),quat.toPitchFromYUp(), "roll=" ,degrees(quat.toRollFromYUp()),quat.toRollFromYUp()

    #  see NL2TelemetryClient.java in NL2 distribution for message format
    def _create_simple_message(self, requestId, msg):  # message with no data
        result = pack('>cHIHc', 'N', msg, requestId, 0, 'L')
        return result

    def _create_NL2_message(self, msgId, requestId, msg):  # message is packed
        #  fields are: N Message Id, reqest Id, data size, L
        start = pack('>cHIH', 'N', msgId, requestId, len(msg))
        end = pack('>c', 'L')
        result = start + msg + end
        return result

    def connect_to_coaster(self):
        try:
            self.client.connect((self.coaster_ip_addr, self.coaster_port))
            return True
        except socket.error, e:
            return False


if __name__ == "__main__":
    #  identifyConsoleApp()
    coaster = CoasterInterface()
    coaster_thread = threading.Thread(target=coaster.get_telemetry)
    coaster_thread.daemon = True
    coaster_thread.start()

    while True:
        if raw_input('\nType quit to stop this script') == 'quit':
            break
