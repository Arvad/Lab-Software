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

    

    
    def setup(self):
        self.ser =self.serial_connection()
        #Setup PLL lock
        data = ''
        data += 'W' #Mode
        data += '{:02x}'.format(0b00000010) #Address
        data += '{:02x}'.format(0b00000011) # 31-24
        data += '{:02x}'.format(0b00111000) # 23-16
        data += '{:02x}'.format(0b00000001) # 15- 8
        data += '{:02x}'.format(0b11011100) #  7- 0
        data += '\r'
        print data
        self.ser.write(data)
        self.ser.write('U\r')
        #data = yield self.ser.read(3)
        #print data
        data = ''
        data += 'W' #Mode
        data += '{:02x}'.format(0b00000111) #Address
        data += '{:02x}'.format(0b01010101) # 31-24
        data += '{:02x}'.format(0b11111111) # 23-16
        data += '{:02x}'.format(0b11111111) # 15- 8
        data += '{:02x}'.format(0b01010101) #  7- 0
        data += '\r'
        self.ser.write(data)
        self.ser.write('U\r')
        print data
        #data = yield self.ser.read(3)
        #print data
    def serial_connection(self):
        ser = serial.Serial('COM3',9600,timeout=1)
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
        return self.ser.read(3)
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
        data =self.ser.read(4)
        return data

    @setting(4, 'Write to register')
    def write_to_register(self,c,data):
        self.ser.write(data)
        return self.ser.read()
    
    @setting(5, 'Update IO')
    def update_IO(self,c):
        self.ser.write('U\r')
        return self.ser.read(3)
    
    @setting(6, 'Reset IO')
    def reset_IO(self,c):
        self.ser.write('S\r')
        return self.ser.read(3)
    
if __name__ == "__main__":
    from labrad import util
    util.runServer(AD9910())