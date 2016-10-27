from PyQt4 import QtGui
from PyQt4.QtCore import QTimer, pyqtSignal, pyqtSlot, Qt, QEvent, QSettings, QVariant
from twisted.internet.defer import inlineCallbacks
from connection import connection

import sys
from LEDindicator import LEDindicator

debug = True

class AD9910client(QtGui.QMainWindow):

    def __init__(self,reactor,cnx=None):
        super(AD9910client, self).__init__()
        self.reactor = reactor
        self.cnx = cnx
        self.connect()
        self.initializeGUI()
        self.restore_GUI()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_pll)
        self.timer.start(10000)


    @inlineCallbacks
    def connect(self):
        if self.cnx is  None:
            self.cnx = connection()
            yield self.cnx.connect()
        self.context = yield self.cnx.context()
        yield self.setupListeners()

    def initializeGUI(self):
        mainwidget = QtGui.QWidget()
        self.frequency = QtGui.QDoubleSpinBox()
        frequencylabel = QtGui.QLabel('Frequency')
        tracking = QtGui.QCheckBox('Tracking Parameter number: ')
        self.trackingnum = QtGui.QSpinBox()
        trackinglabel = QtGui.QLabel('From ParameterVault (0. indexed)')
        self.PLLled = LEDindicator('PLL',offcolor='Red')

        self.trackingnum.setObjectName('Trackingnum')
        self.frequency.setObjectName('Frequency')

        self.frequency.setRange(0,1000)
        self.frequency.setSingleStep(1e-6)
        self.frequency.setSuffix(' MHz')
        self.frequency.setDecimals(6)

        self.frequency.editingFinished.connect(lambda :self.set_frequency(self.frequency.value()))

        tracking.stateChanged.connect(self.tracking_checked)



        trackinglayout = QtGui.QHBoxLayout()
        trackinglayout.addWidget(tracking)
        trackinglayout.addWidget(self.trackingnum)
        trackinglayout.addWidget(trackinglabel)
        trackinglayout.setSpacing(0)

        freqlayout = QtGui.QHBoxLayout()
        freqlayout.addWidget(frequencylabel)
        freqlayout.addWidget(self.frequency)

        layout = QtGui.QVBoxLayout()
        layout.addLayout(freqlayout)
        layout.addLayout(trackinglayout)
        layout.addWidget(self.PLLled)
        mainwidget.setLayout(layout)
        self.setCentralWidget(mainwidget)
        #self.restoreGui()
        self.show()

    @inlineCallbacks
    def set_frequency(self,freq):
        print self.cnx
        server = yield self.cnx.get_server('AD9910server')
        yield server.set_frequency(freq)

    @inlineCallbacks
    def update_pll(self):
        server = yield self.cnx.get_server('AD9910server')
        b = yield server.read_pll()
        self.PLLled.setState(b)

    def restore_GUI(self):
        settings = QSettings('ad9910clientsettings.ini',QSettings.IniFormat)
        settings.setFallbacksEnabled(False)

        for aspinbox in self.findChildren(QtGui.QDoubleSpinBox) + self.findChildren(QtGui.QSpinBox):
            name = aspinbox.objectName()
            if settings.contains(name):
                value= settings.value(name).toDouble()[0]
                aspinbox.setValue(value)
        
        if settings.contains('windowposition'):
            self.move(settings.value("windowposition").toPoint());
        if settings.contains('windowsize'):
            self.resize(settings.value("windowsize").toSize());

    def closeEvent(self,e):
        if self.timer.isActive():self.timer.stop()
        settings = QSettings('ad9910clientsettings.ini',QSettings.IniFormat)
        for aspinbox in self.findChildren(QtGui.QDoubleSpinBox) + self.findChildren(QtGui.QSpinBox):
            name = aspinbox.objectName()
            value= aspinbox.value()
            settings.setValue(name,value)
        
        settings.setValue('windowposition',self.pos())
        settings.setValue('windowsize',self.size())
        
        for asplitter in self.findChildren(QtGui.QSplitter):
            name = asplitter.objectName()
            value = asplitter.sizes()
            settings.setValue(name,value)
        settings.sync()

        self.reactor.stop()

    def tracking_checked(self,state):
        if state == 2: #being checked
            self.tracking = True
            self.frequency.setReadOnly(True)
            self.trackingnum.setReadOnly(True)
        else:
            self.tracking = False
            self.frequency.setReadOnly(False)
            self.trackingnum.setReadOnly(False)

    @inlineCallbacks
    def follow_parameterserver(self,x):
        print 'got here'            
        server = yield self.cnx.get_server('ParameterVault')
        value = [1,1]#yield pv.get_parameter('Raman','announce')
        freq = float(value[self.trackingnum.value])
        self.frequency.setText(freq)
        self.set_frequency(freq)


    @inlineCallbacks
    def setupListeners(self):
        server = yield self.cnx.get_server('ParameterVault')
        yield server.signal__parameter_change(112345, context = self.context)
        yield server.addListener(listener = self.follow_parameterserver, source = None, ID = 112345, context = self.context)


if __name__=="__main__":
    a = QtGui.QApplication( [] )
    import qt4reactor
    qt4reactor.install()
    from twisted.internet import reactor
    Widget = AD9910client(reactor)
    Widget.show()
    reactor.run()