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
        
    def getOtherListeners(self,c):
        notified = self.listeners.copy()
        notified.remove(c.ID)
        return notified

    def serial_connection(self):
        self.ser = serial.Serial('COM3',19200,timeout=10)
        print self._read()

    @setting(1,'Set Frequency')
    def set_frequency(self,c,freq):
        Fmax = 1100.
        FTW = int(round(2**32*(freq/Fmax)))
        data = ''
        data += 'E' #Mode
        data += '07' #address
        data += 'ffffffff' #amplitude scaling - is actually disabled, but is set high
        for i in range(3,-1,-1):
            data += '{:02x}'.format((FTW//256**i)%256)
        data += '\r'
        self.ser.write(data)
        print data
        #self.ser.write('U\r')
        #print self._read()
        
    @setting(2, 'Read serial', returns='s')
    def read_serial(self,c):
        return self._read()

    @setting(3, 'Read PLL', returns='b')
    def read_pll(self,c):
        self.ser.write('P')
        back = self._read()
        back = back.split('P.')
        return bool(int(back[len(back)-2][-1]))

    @setting(4, 'Write to register')
    def write_to_register(self,c,data):
        self.ser.write(data)
        return self._read()
    
    @setting(5, 'Update IO')
    def update_IO(self,c):
        self.ser.write('U\r')
        return self._read()
    
    @setting(6, 'Reset IO')
    def reset_IO(self,c):
        self.ser.write('S\r')
        return self._read()

    def _read(self):
        data = ""
        data += self.ser.read(1)
        while self.ser.in_waiting:
            data +=self.ser.read()
        return data
    
if __name__ == "__main__":
    from labrad import util
    util.runServer(AD9910())