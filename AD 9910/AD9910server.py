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

debug = True

class AD9910(LabradServer):
    """
    Hardware Server for communicating with the AD9910 chip on the evaluation board
    """
    name = "AD9910server"
    def initServer(self):
        self.setup()

    

    @inlineCallbacks
    def setup(self):
        self.ser = yield self.serial_connection()
        #Setup PLL lock
        data = ''
        data += 'W' #Mode
        data += '03' #Address
        data += '{:02x}'.format(0b11001000) # 31-24
        data += '{:02x}'.format(0b01000001) # 23-16
        data += '{:02x}'.format(0b00111000) # 15- 8
        data += '{:02x}'.format(0b00010011) #  7- 0
        data += '\r'

        yield serial.write(data)

    def serial_connection(self,c):
        try:
            ser = serial.Serial('COM',9600)
        except Exception,e:
            print e
        return ser


    @setting(1,'Set Frequnecy', returns ='')
    def set_frequency(self,c,freq):
        data = ''
        data += 'W' #Mode
        data += '07' #address
        for i in range(3,-1,-1):
            data += '{:02x}'.format((freq//256**i)%256)
        data += '\r'
        self.ser.write(data)
        self.ser.write('U\r')

    @setting(2, 'Read serial', returns='s')
    def read_serial(self,c):
        length = self.ser.in_waiting()
        if length == 0:
            data = ''
        else:
            data = ""
            while length > 0:
                data += self.ser.read(1)
                length -= 1

        return data

    @setting(3, 'Read PLL', returns='s')
    def read_pll(self,c):
        self.ser.write('P')
        data =self.ser.read(2)
        return data




if __name__ == "__main__":
    from labrad import util
    util.runServer(AD9910())