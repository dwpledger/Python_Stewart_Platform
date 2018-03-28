# Python Motion Platform Controller
This software enables a motion simulator or other client to control movement of the Middlesex University motion platform.

### Installation
Install the software by copying all the files including the two subdirectories (client and fstlib) directories to your PC.  The software can run in any directory and no registry entries are needed. Install Python 2.7 if not already installed.
The following python modules are required to run with the example clients:
  `sys, time,  math, copy, numpy,  collections, traceback,  socket, TKinter,  tkMessageBox, ttk, pillow`
The threaded client example also requires:
  `Queue, threading`

Note the roller coaster client code in coaster directory will not be publically distributed. This software requires a licensed version of NoLimits2 and the following python modules:
  `serial, win32gui, win32api, win32con, ctypes`

### Software Overview
All activity is driven from the controller module through service calls that poll the client every 50 milliseconds. The client responds with orientation requests and/ or system commands. Orientation requests are in the form surge, sway, heave, roll, pitch, and yaw. These can be either real world values (mm and radians) or normalized values (values between -1 and 1 representing the maximum range of movement of the platform for each degree of freedom).  

Note that the system needs most of the 50ms interval between service requests to calculate and drive the output; therefore the client must return promptly from the service calls. If necessary, the client can use the threaded client example as a model to decouple client processing from the system service routine.

 ### The software consists of the following elements:
 (see comments in source code for more details)
##### Client examples:
+ `platform_input.py`  - keyboard input of orientation values
+ `platform_input_tk.py`  - tkinter gui input of orientation values, also include graphical display of output 
+ `platform_input_UDP.py`  - orientation values sent as USP messages
+ `platform_input_threadedUDP.py` – as above but UDP socket is on separate thread 

##### Controller
+ `platform_controller.py` - the main system module
+ `shape.py` - controls gain, washout and smoothing
+ `shape.cfg` - stores saved settings
+ `kinematics.py` - calculates platform actuator lengths from orientation requests
+ `moving_average.py` - smooths data

##### Output
+  `platform_output.py` - converts actuator requests to festo commands
+  `output_gui.py` – optional  tkinter display of output state

 Platform  Config files: - these contain information on the physical properties of the  platform   
+  `ConfigV1.py `– config for original motion platform
+  `ConfigV2.py` - config for the second generation platform

##### Images
Contains the icons and images used in the TK GUI

##### Fstlib
Contains the festo driver software

##### Coaster Client code (not for public distribution):
+ `coaster_client.py`
+ `coaster_gui.py`
+ `coaster_interface.py`
+ `quaternion.py`
+ `serial_remote.py`
+ `MoveState.py`
