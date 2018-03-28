""" Serial remote control """

import sys
import serial
import time
import serial.tools.list_ports
import threading
from Queue import Queue


class SerialRemote(object):
    """ provide action strings associated with buttons on serial remote control."""
    auto_conn_str = "MdxRemote_V1"  # remote responds with this when promted for version

    def __init__(self, actions):
        """ Call with dictionary of action strings.
 
        Keys are the strings sent by the remote,
        values are the functons to be called for the given key.
        """
        self.ser = None
        self.ser_buffer = ""
        self.baud_rate = 57600
        self.timeout_period = 1
        self.is_connected = False
        self.actions = actions
        self.RxQ = Queue()
        t = threading.Thread(target=self.rx_thread, args=(self.ser, self.RxQ,))
        t.daemon = True
        t.start()

    def rx_thread(self, ser, RxQ):
        """ Auto detect com port and put data in given que."""

        self.RxQ = RxQ
        self.ser = ser
        for p in sorted(list(serial.tools.list_ports.comports())):
            self.RxQ.put("Looking for Remote on %s" % p[0])
            if self._connect(p[0]):
                #  print "found remote on ",p[0]
                self.RxQ.put("Detected Remote Control on %s" % p[0])
                while True:
                    #  wait forever for data to forward to client
                    try:
                        result = self.ser.readline()
                        if len(result) > 0:
                            self.RxQ.put(result)
                    except:
                        print "serial error, trying to reconnect"
                        self.RxQ.put("Reconnect Remote Control")
                        while True:
                            if self._connect(p[0]):
                                print "sending detected msg"
                                self.RxQ.put("Detected Remote Control on %s" % p[0])
                                break

    def _connect(self, portName):
        # Private method try and connect to the given portName.

        self.connected = False
        self.ser = None
        result = ""
        try:
            self.ser = serial.Serial()
            self.ser.port = portName
            self.ser.baudrate = self.baud_rate
            self.ser.timeout = self.timeout_period
            self.ser.setDTR(False)
            self.ser.open()
            if not self.ser.isOpen():
                print "Connection failed:", portName, "has already been opened by another process"
                self.ser = None
                return False
            self.ser.flush()
            print "Looking for Remote control on ", portName
            time.sleep(1)
            self.ser.write('V')

            while True:
                result = self.ser.readline()
                if SerialRemote.auto_conn_str in result or "deactivate" in result:
                    self.connected = True
                    return True
                if len(result) < 1:
                    break
            self.ser.close()
        except:
            self.ser = None
            pass
        return False

    def _send_serial(self, toSend):
        # private method sends given string to serial port
        if self.ser:
            if self.ser.writable:
                self.ser.write(toSend)
                self.ser.flush()
                return True
        return False

    def service(self):
        """ Poll to service remote control requests."""

        while not self.RxQ.empty():
            msg = self.RxQ.get().rstrip()
            if "Detected Remote" in msg or "Reconnect Remote" in msg or "Looking for Remote" in msg:
                self.actions['detected remote'](msg)
            elif SerialRemote.auto_conn_str not in msg:  # ignore remote ident
                self.actions[msg]()
