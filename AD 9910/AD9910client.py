from PyQt4 import QtGui
from PyQt4.QtCore import QTimer, pyqtSignal, pyqtSlot, Qt, QEvent, QSettings, QVariant
import labrad
import sys
import LEDindicator

debug = True

class AD9910client(QtGui.QMainWindow):

    def __init__(self):
        super(AD9910client,self).__init__()
        if not debug:
            pass
        self.initialize()


    def initialize(self):
        mainwidget = QtGui.QWidget()
        frequency = QtGui.QDoubleSpinBox()
        frequencylabel = QtGui.QLabel('Frequency')
        tracking = QtGui.QCheckBox('Tracking Parameter ')
        trackingvar = QtGui.QLineEdit()
        trackinglabel = QtGui.QLabel('From ParameterVault')

        trackinglayout = QtGui.QHBoxLayout()
        trackinglayout.addWidget(tracking)
        trackinglayout.addWidget(trackingvar)
        trackinglayout.addWidget(trackinglabel)
        trackinglayout.setSpacing(0)

        freqlayout = QtGui.QHBoxLayout()
        freqlayout.addWidget(frequencylabel)
        freqlayout.addWidget(frequency)

        layout = QtGui.QVBoxLayout()
        layout.addLayout(freqlayout)
        layout.addLayout(trackinglayout)
        mainwidget.setLayout(layout)
        self.setCentralWidget(mainwidget)
        #self.restoreGui()
        self.show()

if __name__=="__main__":
    a = QtGui.QApplication( [] )
    pl = AD9910client()
    sys.exit(a.exec_())