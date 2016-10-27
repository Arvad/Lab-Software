from PyQt4 import QtGui
from PyQt4.QtCore import Qt
class LEDindicator(QtGui.QFrame):
    def __init__(self,name,state=False,offcolor = 'lightGray'):
        super(LEDindicator, self).__init__()
        self.led = QtGui.QWidget()
        self.offcolor = offcolor
        self.led.setAutoFillBackground(True)
        #self.setFrameStyle(1)
        self.label = QtGui.QLabel(name)
        #self.label.setWordWrap(True)
        #self.label.setMaximumWidth(40)
        self.label.setAlignment(Qt.AlignCenter)
        self.led.setMaximumSize(12,12)
        self.led.setMinimumSize(12,12)
        #self.label.setSizePolicy(QtGui.QSizePolicy.Ignored,QtGui.QSizePolicy.Ignored)
        layout = QtGui.QHBoxLayout()
        layout.setSpacing(2)
        layout.setMargin(2)
        layout.addWidget(self.led)
        layout.addWidget(self.label)
        layout.setAlignment(Qt.AlignLeft)
        self.setLayout(layout)
        self.State = state
        self.setState(state)


    def setOn(self):
        self.State = True
        pal = QtGui.QPalette()
        pal.setColor(self.led.backgroundRole(), Qt.green)
        self.led.setPalette(pal)
        self.update()

    def setState(self,state):
        if state:
            self.setOn()
        else:
            self.setOff()
            
    def getState(self):
        return self.State
        
    def setOff(self):
        self.State = False
        pal = QtGui.QPalette()
        pal.setColor(self.led.backgroundRole(), QtGui.QColor(self.offcolor))
        self.led.setPalette(pal)
    
    #def resizeEvent(self,event):
    #    font = self.label.font()
    #    h = self.label.height()*0.8
    #    font.setPixelSize(h)
    #    self.label.setFont(font)

if __name__== '__main__':
    import sys
    app = QtGui.QApplication( [])
    widget = LEDindicator('Busy')
    widget.show()
    sys.exit(app.exec_())