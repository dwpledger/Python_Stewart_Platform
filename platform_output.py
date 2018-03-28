"""
platform_output module drives chair with Festo UDP messages

Old and New Festo controllers are supported
The module can also drive a serial platform for testing or demo

Muscle calculations use the following formula to convert % contraction to pressure:
  pressure = 35 * percent*percent + 15 * percent + .03  # assume 25 Newtons for now
percent is calculated as follows:
 percent =  1- (distance + MAX_MUSCLE_LEN - MAX_ACTUATOR_LEN)/ MAX_MUSCLE_LEN
"""

import sys
import socket
import traceback
import math
import time
import copy
import numpy as np
from output_gui import OutputGui
#  import matplotlib.pyplot as plt    #  only for testing

TESTING = False
if not TESTING:
    sys.path.insert(0, './fstlib')
    from fstlib import easyip

"""
  Import platform configuration
"""
#  from ConfigV1 import *
from ConfigV2 import *
#  from ConfigServoSim import *
#  from ConfigServoSimChair import *

PRINT_MUSCLES = False

OLD_FESTO_CONTROLLER = True

if TESTING:
    print "THIS IS TESTING MODE, no output to Festo!!!"
    FST_ip = 'localhost'

print "starting", PLATFORM_NAME
if PLATFORM_NAME == "SERVO_SIM":
    IS_SERIAL = True
    import serial
else:
    IS_SERIAL = False
    if not TESTING:
        if OLD_FESTO_CONTROLLER:
            FST_port = 991
            FST_ip = '192.168.10.10'
            print "opening old controller socket at",  FST_ip, FST_port
        else:
            # Set the socket parameters
            FST_ip = '192.168.0.10'
            FST_port = 1000 + easyip.EASYIP_PORT
            bufSize = 1024
            print "opening new controller socket at",  FST_ip, FST_port


class OutputInterface(object):

    #  IS_SERIAL is set True if using serial platform simulator for testing
    global IS_SERIAL

    def __init__(self):
        np.set_printoptions(precision=2, suppress=True)
        self._calculate_geometry()
        self.LIMITS = platform_1dof_limits  # max movement in a single dof
        self.platform_disabled_pos = np.empty(6)   # position when platform is disabled
        self.platform_disabled_pos.fill(DISABLED_LEN)
        self.platform_winddown_pos = np.empty(6)  # position for attaching stairs
        self.platform_winddown_pos.fill(WINDDOWN_LEN)
        self.isEnabled = False  # platform disabled if False
        self.loaded_weight = PLATFORM_UNLOADED_WEIGHT + DEFAULT_PAYLOAD_WEIGHT
        self.prev_pos = [0, 0, 0, 0, 0, 0]  # requested distances stored here
        self.requested_pressures = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.actual_pressures = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.prev_time = time.clock()
        if IS_SERIAL:
            #  configure the serial connection
            try:
                self.ser = serial.Serial(port=OutSerialPort, baudrate=57600, timeout=1)
                print "Out simulator opened on ", OutSerialPort
            except:
                print "unable to open Out simulator serial port", OutSerialPort
        elif not TESTING:
            self.FSTs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.FST_addr = (FST_ip, FST_port)
            if not OLD_FESTO_CONTROLLER:
                self.FSTs.bind(('0.0.0.0', 0))
                self.FSTs.settimeout(1)  # timout after 1 second if no response
        print ""
        self.prevMsg = []
        self.gui = OutputGui()
        
    def init_gui(self, master):
        self.gui.init_gui(master, MIN_ACTUATOR_LEN, MAX_ACTUATOR_LEN)
         
    def fin(self):
        """
        free resources used by ths module
        """
        if IS_SERIAL:
            try:
                if self.ser and self.ser.isOpen():
                    self.ser.close()
            except:
                pass
        else:
            if not TESTING:
                self.FSTs.close()
                
    def get_platform_name(self):
         return PLATFORM_NAME

    def get_geometry(self):
        """
        get coordinates of fixed and moving attachment points and mid height
        """
        return base_pos, platform_pos, self.platform_mid_height 

    def get_platform_pos(self):
        """
        get coordinates of fixed platform attachment points
        """
        return platform_pos

    def get_output_status(self):
        """
        return string describing output status
        """
        if TESTING:
            return ("Test mode, no output to Festo", "red")
        if OLD_FESTO_CONTROLLER:
            return ("Old Festo Controller", "green3")
        else:
            if position_request(v == 0 for v in self.actual_pressures):
                return ("Festo Pressure is Zero", "orange")
            else:
                return ("Festo Pressure is Good", "green3")  # todo, also check if pressure is low

    def get_platform_mid_height(self):
        """
        get actuater lengths in mid (ready for ride) position
        """
        return self.platform_mid_height  # height in mm from base at mid position

    def get_limits(self):
        """
        provide limit of movement in all 6 DOF from imported platform config file
        """
        return self.LIMITS

    def set_payload(self, payload_kg):
        """
        set passenger weight in killograms
        """
        self.loaded_weight = PLATFORM_UNLOADED_WEIGHT + payload_kg

    def set_enable(self, state, actuator_lengths):
        """
        enable platform if True, disable if False
        
        actuator_lengths are those needed to achieve current client orientation
        """
        if self.isEnabled != state:
            self.isEnabled = state
            print "Platform enabled state is", state
            if state:
                self._slow_move(self.platform_disabled_pos, actuator_lengths, 1000)
            else:
                self._slow_move(actuator_lengths, self.platform_disabled_pos, 1000)
            
    def move_to_limits(self, pos):
        """
        + or - 1 in [x,y,z,ax,ay,az] moves to that limit, 0 to middle
        Args:
           pos is list of translations and rotations
        """
        self.moveTo([p*l for p, l in zip(pos, self.limits)])

    def swell_for_access(self, interval):
        """
        Briefly raises platform high enough to insert access stairs
        
        moves even if disabled
        Args:
          interval (int): time in ms before dropping back to start pos
        """       
        self._slow_move(self.platform_disabled_pos, self.platform_winddown_pos, 1000)
        time.sleep(interval)
        self._slow_move(self.platform_winddown_pos, self.platform_disabled_pos, 1000)

    def move_platform(self, lengths):  # lengths is list of 6 actuator lengths as millimeters
        """
        Move all platform actuators to the given lengths
        
        Args:
          lengths (float): numpy array comprising 6 actuator lengths
        """
        clipped = []
        for idx, l in enumerate(lengths):
            if l < MIN_ACTUATOR_LEN:
                lengths[idx] = MIN_ACTUATOR_LEN
                clipped.append(idx)
            elif l > MAX_ACTUATOR_LEN:
                lengths[idx] = MAX_ACTUATOR_LEN
                clipped.append(idx)
        if len(clipped) > 0:
            pass
            #  print "Warning, actuators", clipped, "were clipped"
        if self.isEnabled:
            if IS_SERIAL:
                self._move_to_serial(lengths)
            else:
                self._move_to(lengths)  # only fulfill request if enabled
        """
        else:
            print "Platform Disabled"
        """

    def show_muscles(self,position_request, muscles):
        self.gui.show_muscles(position_request, muscles)
        
    #  private methods
    def _slow_move(self, start, end, duration):
        if IS_SERIAL:
            move_func = self._move_to_serial
        else:
            move_func = self._move_to
       
        #  caution, this moves even if disabled
        interval = 50  # time between steps in ms
        steps = duration / interval
        if steps < 1:
            self.move(end)
        else:
            current = start
            print "moving from", start, "to", end, "steps", steps
            delta = [float(e - s)/steps for s, e in zip(start, end)]
            for step in xrange(steps):
                current = [x + y for x, y in zip(current, delta)]                
                move_func(copy.copy(current))
                self.show_muscles([0,0,0,0,0,0], current)
                time.sleep(interval / 1000.0)

    def _calculate_geometry(self):
        #  reflect around X axis to generate right side coordinates
        global base_pos, platform_pos
        otherSide = copy.deepcopy(base_pos[::-1])  # order reversed
        for inner in otherSide:
            inner[1] = -inner[1]   # negate Y values
        base_pos.extend(otherSide)

        otherSide = copy.deepcopy(platform_pos[::-1])  # order reversed
        for inner in otherSide:
            inner[1] = -inner[1]   # negate Y values
        platform_pos.extend(otherSide)

        base_pos = np.array(base_pos)
        platform_pos = np.array(platform_pos)

        #  print "\nPlatformOutput using %s configuration" %(PLATFORM_NAME)
        #  print "Actuator lengths: Min %d, Max %d, mid %d" %( MIN_ACTUATOR_LEN, MAX_ACTUATOR_LEN, MID_ACTUATOR_LEN)

        #  use actuator length and the distance between attachment points to calculate height extents
        a = np.linalg.norm(base_pos[1]-platform_pos[1])  # distance between consecutive platform attachmment points

        b = MIN_ACTUATOR_LEN
        platforMin = math.sqrt(b * b - a * a)  # the min vertical movement from center to top or bottom
        #  print "min height", round(platforMin)

        b = MID_ACTUATOR_LEN
        self.platform_mid_height = math.sqrt(b * b - a * a)  # the mid vertical movement from center to top or bottom
        #  print "mid height", round(self.platform_mid_height)

        b = MAX_ACTUATOR_LEN
        platformMax = math.sqrt(b * b - a * a)  # the max vertical movement from center to top or bottom
        #  print "max height", round(platformMax)

        #  uncomment this section to plot the array coordinates
        """
        bx= base_pos[:,0]
        by = base_pos[:,1]
        plt.scatter(bx,by)
        px= platform_pos[:,0]
        py = platform_pos[:,1]
        plt.axis('equal')
        plt.scatter(px,py)
        plt.show()
        """

        #  print "base_pos:\n",base_pos
        #  print "platform_pos:\n",platform_pos

    def _move_to_serial(self, lengths):
        """ temp hack tpo produce norm output"""
        #  msg = 'jsonrpc:,method":"moveEvent","rawArgs"' + ':'.join([str(self.normalize(item)) for item in lengths]) + ']}'
        #  msg = "rawArgs," + ",".join([str(self.normalize(item)) for item in lengths])

        msg = "rawArgs," + ",".join([str(round(item)) for item in lengths])
        if msg != self.prevMsg:
            #  print msg
            self.prevMsg = msg
        if self.ser.isOpen():
            self.ser.write(msg + '\n')
            #  print self.ser.readline()
        else:
            print "serial not open"

    def _move_to(self, lengths):
        now = time.clock()
        timeDelta = now - self.prev_time
        self.prev_time = now
        load_per_muscle = self.loaded_weight / 6  # if needed we could calculate individual muscle loads
        pressure = []
        for idx, distance in enumerate(lengths):
            pressure.append(int(1000*self._convert_MM_to_pressure(idx, distance, timeDelta, load_per_muscle)))
        self._send(pressure)

    def _convert_MM_to_pressure(self, idx, distance, timeDelta, load):
        #  global MAX_MUSCLE_LEN, MAX_ACTUATOR_LEN
        #  calculate the percent of muscle contraction to give the desired distance
        percent = 1-(distance + MAX_MUSCLE_LEN - MAX_ACTUATOR_LEN) / MAX_MUSCLE_LEN
        #  check for range between 0 and .25
        #  print "distance =", distance, percent
        if percent < 0 or percent > 0.25:
            print "%.2f percent contraction out of bounds for distance %.1f" % (percent, distance)
        distDelta = distance-self.prev_pos[idx]  # the change in distance from the previous position
        accel = (distDelta/1000) / timeDelta  # accleration units are meters per sec

        if distDelta < 0:
            force = load * (1-accel)  # TODO  here we assume force is same magnitude as expanding muscle ???
            #  TODO modify formula for force
            #  pressure = 30 * percent*percent + 12 * percent + .01  # assume 25 Newtons for now
            pressure = 35 * percent*percent + 15 * percent + .03  # assume 25 Newtons for now
            if PRINT_MUSCLES:
                print("muscle %d contracting %.1f mm to %.1f, accel is %.2f, force is %.1fN, pressure is %.2f"
                      % (idx, distDelta, distance, accel, force, pressure))
        else:
            force = load * (1+accel)  # force in newtons not yet used
            #  TODO modify formula for expansion
            pressure = 35 * percent*percent + 15 * percent + .03  # assume 25 Newtons for now
            if PRINT_MUSCLES:
                print("muscle %d expanding %.1f mm to %.1f, accel is %.2f, force is %.1fN, pressure is %.2f"
                      % (idx, distDelta, distance, accel, force, pressure))

        self.prev_pos[idx] = distance  # store the distance
        return pressure

    def _send(self, muscle_pressures):
        self.requested_pressures = muscle_pressures  # store this for display if reqiured
        if not TESTING:
            try:
                if not OLD_FESTO_CONTROLLER:
                    packet = easyip.Factory.send_flagword(0, muscle_pressures)
                    try:
                        self._send_packet(packet)
                        self.actual_pressures = self._get_pressure()
                    except socket.timeout:
                        print "timeout waiting for replay from", self.FST_addr

                else:
                    for idx, muscle in enumerate(muscle_pressures):
                        maw = int(muscle*1000)
                        maw = max(min(6000, muscle), 0)  # limit range to 0 to 6000
                        command = "maw"+str(64+idx)+"="+str(maw)
                        #  print command,
                        command = command + "\r\n"
                        self.FSTs.sendto(command, self.FST_addr)
            except:
                e = sys.exc_info()[0]
                s = traceback.format_exc()
                print "error sending to Festo", e, s

    def _send_packet(self, packet):
        if not TESTING:
            data = packet.pack()
            self.FSTs.sendto(data, self.FST_addr)
            #  print "sending to", self.FST_addr
            print "in sendpacket,waiting for response..."
            data, srvaddr = self.FSTs.recvfrom(bufSize)
            resp = easyip.Packet(data)
            print "in senddpacket, response from Festo", resp
            if packet.response_errors(resp) is None:
                print "No send Errors"
            else:
                print "errors=%r" % packet.response_errors(resp)
            return resp

    def _get_pressure(self):
        # fist arg is the number of requests your making. Leave it as 1 always
        # Second arg is number of words you are requesting (probably 6, or 16)
        # third arg is the offset.
        # words 0-5 are what you sent it.
        # words 6-9 are not used
        # words 10-15 are the current values of the presures
        # packet = easyip.Factory.req_flagword(1, 16, 0)
        if TESTING:
            return self.requested_pressures  # TEMP for testing
        print "attempting to get pressure"
        try:
            packet = easyip.Factory.req_flagword(1, 6, 10)
            resp = self._send_packet(packet)
            values = resp.decode_payload(easyip.Packet.DIRECTION_REQ)
            return list(values)
        except timeout:
            print "timeout waiting for Pressures from Festo at", self.addr
        return None
