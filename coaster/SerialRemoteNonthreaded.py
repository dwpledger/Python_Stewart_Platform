import sys
import serial
import time
import serial.tools.list_ports

_ports = list(serial.tools.list_ports.comports())

class SerialRemote(object):
    def __init__(self, actions):
        self.ser = None
        self.serBuffer = ""
        self.baud_rate = 57600
        self.timeout_period = 5
        self.isConnected = False
        self.actions = actions # { 'pause' : self.pause, 'dispatch' : self.dispatch,  'reset' : self.reset, 'emergencyStop' : self.emergencyStop}
        import serial.tools.list_ports
        self.ports = list(serial.tools.list_ports.comports())
        print self.ports


    def begin(self):
        for p in self.ports:
            if self.connect(p[0]):
                print "found remote on ",p[0]
                return True
        print "Unable to find Serial remote control"
        return False

    def connect(self, portName):
    #connect to a specifically named port
        self.connected = False
        self.ser = None
        autoConnStr =  "MdxRemote_V1"
        result = ""
        try:
            self.ser = serial.Serial(portName, baudrate=self.baud_rate, timeout=self.timeout_period, writeTimeout=self.timeout_period)
            if not self.ser.isOpen():
                print "Connection failed:",portName,"has already been opened by another process"
                self.ser = None
                return False
            self.ser.flush()
            time.sleep(3)
            print "Looking for Remote control on ", portName
            self.ser.write('V')
            result = self.ser.readline()
            if autoConnStr in result:
                self.connected = True
                return True
        except:
            self.ser = None
            pass
        return False

    def sendSerial(self, toSend):
        if self.ser:
            if self.ser.writable:
                self.ser.write(toSend)
                self.ser.flush()
                return True
        return False

    def poll(self):
        if self.ser and self.ser.isOpen():
            try:
                while True:
                    c = self.ser.read() # attempt to read a character from Serial
                    #was anything read?
                    if len(c) >  0:
                        # check if character is a delimiter
                        if c == '\r':
                            c = '' # ignore CR
                        elif c == '\n':
                            self.actions[self.serBuffer]()
                            self.serBuffer = '' # empty the buffer
                        else:
                            self.serBuffer += c # add to the buffer
            except (OSError, serial.SerialException):
                self.serBuffer = 'ERROR'




# for testing
if __name__ == '__main__':
    exitFlag = False

    def dispatch():
        print "dispatch"

    def pause():
       print "pause"

    def reset():
        print "reset"
        exitFlag = True

    def emergencyStop():
         print "emergencyStop"

    sr = SerialRemote({  'pause' : pause, 'dispatch' : dispatch,  'reset' : reset, 'emergencyStop' : emergencyStop})
    if sr.begin():
       while True:
            sr.poll()
            if exitFlag:
                break