"""
### BEGIN NODE INFO
[info]
name = AD9910server
version = 0.1
description = 
instancename = AD9910server

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

### END NODE INFO
"""

from labrad.server import LabradServer, setting, Signal
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall
import serial
import time

debug = True

class AD9910(LabradServer):
    """
    Hardware Server for communicating with the AD9910 chip on the evaluation board
    """
    name = "AD9910server"
    def initServer(self):
        self.listeners = set()
        self.setup()
    
    def setup(self):
        self.serial_connection()

    def initContext(self, c):
        """Initialize a new context object."""
        self.listeners.add(c.ID)
    
    def expireContext(self, c):
        self.listeners.remove(c.ID)   
        
    def getOtherListeners(self):
        notified = self.listeners.copy()
        return notified
 
    def serial_connection(self):
        self.ser = serial.Serial('COM3',19200,timeout=10)
 
    @setting(1,'Set Frequency')
    def set_frequency(self,c,freq):
        Fmax = 1100. # Max frecuency
        if freq<0 or freq > Fmax/2:
            return
        FTW = int(round(2**32*(freq/Fmax)))
        data = ''
        data += 'W' #Mode
        data += '0e' #address
        data += 'ffffffff' #amplitude scaling - is actually disabled, but is set high
        for i in range(3,-1,-1):
            data += '{:02x}'.format((FTW//256**i)%256)
        data += '\r'
        self.ser.write(data)
        self.ser.write('U\r') #UpdateIO command

    @setting(2, 'Read serial', returns='s')
    def read_serial(self,c):
        return self._read()

    @setting(3, 'Read PLL', returns='b')
    def read_pll(self,c):
        self.ser.write('P')
        back = self.ser.read(3)
        back = bool(back[0])
        return back

    @setting(4, 'Write',string='s')
    def write(self,c,string):
        self.ser.write(string)
    
    @setting(5, 'Update IO')
    def update_IO(self,c):
        self.ser.write('U\r')
    
    @setting(6, 'Reset IO')
    def reset_IO(self,c):
        self.ser.write('S\r')

    def _read(self):
        data = ""
        data += self.ser.read(1)
        while self.ser.in_waiting:
            data +=self.ser.read()
        return data
    
if __name__ == "__main__":
    from labrad import util
    util.runServer(AD9910())