from PyQt4 import QtGui
from PyQt4.QtCore import QTimer, pyqtSignal, pyqtSlot, Qt, QEvent, QSettings, QVariant, QProcess, QObject
from subprocess import Popen, PIPE
import os
import sys
import labrad

class ServerItem():
    def __init__(self,aname,apath):
        self.name = aname
        self.path = apath
        self.textfield = None
        self.process = None

       
class serverclient(QtGui.QWidget):

    def __init__(self):
        super(serverclient, self).__init__()
        self.setWindowTitle("Labrad WatchDog")
        self.labradpath = 'C:\Users\Katori\Desktop\Labrad\LabRAD-v1.1.3.exe'
        self.highfinesspath = 'C:\Program Files\HighFinesse\Wavelength Meter WS Ultimate 1362\wlm_wsu.exe'
        self.wavemeterwidgetpath ='C:\Users\Katori\Desktop\Wavemeter\wavemeterwidget.pyw'
        self.serverlist = [('DDS556','C:\Users\Katori\Desktop\Labrad\servers\AD9910556\AD9910server.py'),
                           ('ParameterVault','C:\Users\Katori\Desktop\Labrad\servers\ParameterVault\parameter_vault.py')]
        
        self.serverwidgetlist = []
        self.applicationprocesslist = []
        self.initializeGUI()
        sys.stdout = EmittingStream(textWritten = self.write_output)
        sys.stderr = EmittingStream(textWritten = self.write_output)

    def initializeGUI(self):
        initpanel = self.make_initializationwidget()
        serverpanel = self.make_serverpanel()
        ownoutput = self.make_ownputputwidget()
        mainlayout = QtGui.QHBoxLayout()

        mainlayout.addWidget(initpanel)
        mainlayout.addWidget(serverpanel)
        mainlayout.addWidget(ownoutput)
        
        self.setLayout(mainlayout)
        self.show()

    def make_serverpanel(self):
        serverframe = QtGui.QFrame()
        serverlabel = QtGui.QLabel('Labrad Servers')
        serverlayout = QtGui.QVBoxLayout()
        layout = QtGui.QHBoxLayout()
        for aserver in self.serverlist:
            name,path = aserver
            awidget = serverwidget(name,path)
            layout.addWidget(awidget)
            self.serverwidgetlist.append(awidget)
        serverlayout.addWidget(serverlabel)
        serverlayout.addLayout(layout)
        serverframe.setLayout(serverlayout)
        return serverframe

    def make_initializationwidget(self):
        widget = QtGui.QFrame()
        label = QtGui.QLabel('Initialization steps')
        labradbutton = QtGui.QPushButton('1. Start labrad manager')
        allserversbutton = QtGui.QPushButton('2. Start all servers')
        highfinessbutton = QtGui.QPushButton('3. Start High Finesse Wavemeter')
        wavemeterwidgetbutton = QtGui.QPushButton('4. Start Wavemeter widget')

        labradbutton.pressed.connect(lambda :self.start_program(self.labradpath))
        allserversbutton.pressed.connect(self.start_all_servers)
        highfinessbutton.pressed.connect(lambda: self.start_program(self.highfinesspath))
        wavemeterwidgetbutton.pressed.connect(lambda : self.start_program(self.wavemeterwidgetpath))

        layout = QtGui.QVBoxLayout()
        layout.addWidget(labradbutton)
        layout.addWidget(allserversbutton)
        layout.addWidget(highfinessbutton)
        layout.addWidget(wavemeterwidgetbutton)
        widget.setLayout(layout)
        return widget
         
    def make_ownputputwidget(self):
        thiswidget = QtGui.QFrame()
        label = QtGui.QLabel('ServerWatchDog output')
        self.textfield = QtGui.QTextEdit()
        self.textfield.setReadOnly(True)
        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.textfield)
        thiswidget.setLayout(layout)
        return thiswidget

    def start_program(self,path):
        process = QProcess()
        print os.path.dirname(path)
        process.setWorkingDirectory(os.path.dirname(path))
        print process.workingDirectory()
        if os.path.splitext(path)[1] == '.pyw':
            process.startDetached('pythonw',[path],os.path.dirname(path))
        else:
            process.startDetached(path,[],os.path.dirname(path))
        print 'Started {:}'.format(os.path.basename(path))

    def start_all_servers(self):
        for aserver in self.serverwidgetlist:
            aserver.start_server()
        print 'Started all servers'

    def write_output(self,text):
        self.textfield.moveCursor(QtGui.QTextCursor.End)
        self.textfield.insertPlainText( text )
     
    def closeEvent(self,event):
        for awidget in self.serverwidgetlist:
            awidget.kill_server()

class EmittingStream(QObject):
    textWritten = pyqtSignal(str)
    
    def write(self,text):
        self.textWritten.emit(str(text))

class serverwidget(QtGui.QFrame):

    def __init__(self,aname,apath):
        super(serverwidget, self).__init__()
        self.process = None
        self.path = apath
        self.name = aname
        self.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        title = QtGui.QLabel(self.name)
        startbutton = QtGui.QPushButton('START')
        killbutton = QtGui.QPushButton('TERMINATE')
        pingbutton = QtGui.QPushButton('PING')
        self.textfield = QtGui.QTextEdit()
        self.textfield.setReadOnly(True)
        startbutton.pressed.connect(self.start_server)
        killbutton.pressed.connect(self.kill_server)
        pingbutton.pressed.connect(self.ping_server)
        
        sublayout = QtGui.QVBoxLayout()
        sublayout.addWidget(title)
        sublayout.addWidget(startbutton)
        sublayout.addWidget(killbutton)
        sublayout.addWidget(pingbutton)
        sublayout.addWidget(self.textfield)
        self.setLayout(sublayout)
        
    def start_server(self):
        if self.process is None:
            self.process = QProcess()
            self.process.readyReadStandardOutput.connect(self.read_output)
            self.process.started.connect(lambda : self.write_message('Server started')) 
            self.process.finished.connect(lambda : self.write_message('Server stopped'))
            self.process.setProcessChannelMode(QProcess.MergedChannels)
            self.process.setWorkingDirectory(os.path.dirname(self.path))
            self.process.start('python',[self.path])
        else:
            self.textfield.append('Cannot start "{:}", as it is already running'.format(self.name))

    def kill_server(self):
        if self.process is not None:
            self.process.terminate()
            self.process = None
        else:
            self.textfield.append('Cannot terminate "{:}", as it is not running'.format(self.name))

    def ping_server(self):
        if self.process is not None:
            state = self.process.state()
            msg = "PING: "
            if state == 0:
                msg +='Process died'
            elif state == 1:
                msg +='Process is starting up'
            elif state == 2:
                msg += 'Process is alive'
            self.textfield.append(msg)
            cnx = labrad.connect()
            labradserver = eval('cnx.{:}'.format(self.name))
            msg = 'PING: Labradserver is ' + labradserver.echo('alive')
            self.textfield.append(msg)
            cnx.disconnect()
        else:
            self.textfield.append('Cannot ping a server that is not started')

    def read_output(self):
        data = self.process.readAllStandardOutput()
        self.textfield.append(str(data))        

    def write_message(self,message):
        self.textfield.append(message)


def logo():
    logostring = ["40 40 4 1","   c #FFFFFF",".  c #000000","+  c #AE7C3C","@  c #FF1E00",
                  "                                        ","                                        ","            ................            ","       .....               +.....       ","       .....               +.....       ",
                  "    .....++++              ++++.....    ","   .+++++++++            +++++++++++.   ","   .+++++++++            +++++++++++.   "," ..+++++++              +++++++++++++.. ",".++++++..             +++++++++..++++++.",
                  ".++++++..             +++++++++..++++++.",".++++++..            ++++++++++..++++++.",".++++++..      ...   +++...++++..++++++.",".++++++..      ...   +++...++++..++++++.",".++++++..      ...   +++...++++..++++++.",
                  " ..++++..            ++++++++++..++++.. "," ..++++..            ++++++++++..++++.. ","   .+++..            ++++++++++..+++.   ","   .+++..             +++++++++..+++.   ","   .+++..             +++++++++..+++.   ",
                  "   .+++..               +++++++..+++.   ","   .+++..               +++++++..+++.   ","   .+++..               +++++++..+++.   ","    ...  ...   ..........  +...  ...    ","          ..   ..........   ..          ",
                  "          ..   ..........   ..          ","          ..   ..........   ..          ","          ..      ....      ..          ","          ..      ....      ..          ","          ..      ....      ..          ",
                  "          ...              ...          ","          ...              ...          ","            ...          ...            ","             ..............             ","             ..............             ",
                  "                ..@@@@..                ","                ..@..@..                ","                ..@..@..                ","                ........                ","                                        "]
    return logostring

if __name__=="__main__":
    a = QtGui.QApplication( [] )
    a.setWindowIcon(QtGui.QIcon(QtGui.QPixmap(logo())))
    import ctypes
    myappid = u'mycompany.myproduct.subproduct.version' # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    pl = serverclient()
    sys.exit(a.exec_())



