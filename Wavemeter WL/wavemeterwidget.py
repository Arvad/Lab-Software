#!/usr/bin/env python
#########################################################################
####                                                                 ####
####                  Wavemeter interfacing software                 #### 
####                                                                 ####
#########################################################################
__author__ = "Asbjorn Arvad Jorgensen"
__version__ = "1.1"
__email__ = "Arvad91@gmail.com"



from PyQt4 import QtGui
from PyQt4.QtCore import QTimer, pyqtSignal, pyqtSlot, Qt, QEvent, QSettings, QVariant
import pyqtgraph as pg
import sys
from os import listdir
import ctypes
import os
import re
import random
import numpy as np
import time
import datetime
import inspect
import labrad

debug = True
def sqr(a): return a*a

class wavemeterwidget(QtGui.QMainWindow):
    
    def __init__(self):
        super(wavemeterwidget,self).__init__()
        if not debug:
            self.wavemeter = wlm()
        self.settings = QSettings('settings.ini',QSettings.IniFormat)
        self.setWindowTitle("Wavemeter widget")
        self.settings.setFallbacksEnabled(False)
        self.timer = QTimer()    
        self.timer.timeout.connect(self.update)
        self.debugint = 0
        self.updatespeed = 25
        self.plotspeed = 1
        self.channellist = []
        self.warning = False
        self.logging = False
        self.connection = None
        self.errorserver = None
        if not os.path.isdir("./wavemeterlogging"):
            os.mkdir("wavemeterlogging")
        self.logfile = None
        for i in range(8):
            self.channellist.append(channelinformation(i+1))
        self.initialize()
            
    #Creating the different GUI elements of the main window and joining them together
    def initialize(self):
        mainwidget = QtGui.QWidget()

        ########################################################
        #######    create gui widget elements
        ########################################################
        readingswidget = self.makeReadingswidget()
        graphswidget = self.makeGraphsWidget()
        self.settingswidget = self.makeSettingswidget()

        ########################################################
        #######    Create main window buttons and warningsbox
        ########################################################
        buttonspanel = QtGui.QWidget()
        startbutton = QtGui.QPushButton('Start')
        stopbutton = QtGui.QPushButton('Stop')
        configbutton = QtGui.QPushButton('Config')
        resetallbutton = QtGui.QPushButton('Reset All')
        resetwarningbutton = QtGui.QPushButton('Reset Warning')
        autoscaletimebutton = QtGui.QPushButton('Autoscale Time')
        logwarning = QtGui.QCheckBox('Log warnings')
        logstatuslabel = QtGui.QLabel()
        self.warningtext = QtGui.QTextEdit()
        self.warningtext.setMaximumHeight(resetwarningbutton.sizeHint().height()*3)
        self.warningtext.setReadOnly(True)

        panellayout = QtGui.QGridLayout()
        panellayout.addWidget(logwarning,0,0,1,1)
        panellayout.addWidget(logstatuslabel,0,1,1,5)
        panellayout.addWidget(self.warningtext,1,0,3,4)
        panellayout.addWidget(startbutton,1,4)
        panellayout.addWidget(stopbutton,1,5)
        panellayout.addWidget(configbutton,2,4)
        panellayout.addWidget(resetallbutton,2,5)
        panellayout.addWidget(resetwarningbutton,3,4)
        panellayout.addWidget(autoscaletimebutton,3,5)
        buttonspanel.setLayout(panellayout)
        panellayout.setSpacing(0)
        panellayout.setContentsMargins(0,0,0,0)

        ########################################################
        ####### Join all widgets together    
        ########################################################
        layout = QtGui.QVBoxLayout()
        layout.addWidget(buttonspanel)
        layout.addWidget(graphswidget)
        mainwidget.setLayout(layout)
        self.addDockWidget(Qt.DockWidgetArea(1),readingswidget)
        self.addDockWidget(Qt.DockWidgetArea(2),self.settingswidget)
        self.settingswidget.setFloating(True) #makes the settingswindow appear floating when it is unhidden
                

        ########################################################
        #######    Event Handlers
        ########################################################
        startbutton.pressed.connect(self.start_pressed)
        stopbutton.pressed.connect(self.stop_pressed)
        configbutton.pressed.connect(self.config_pressed)
        resetallbutton.pressed.connect(self.resetall_pressed)
        resetwarningbutton.pressed.connect(self.resetwarning_pressed)
        autoscaletimebutton.pressed.connect(self.autoscalex_pressed)
        self.warningtext.contextMenuEvent = self.warningtext_contextmenu
        logwarning.stateChanged.connect( lambda state=1: self.logwarning_toggled(state,logstatuslabel))

        ########################################################
        #######    show the window
        ########################################################
        self.setCentralWidget(mainwidget)
        self.restoreGui()
        self.show()

    def restoreGui(self):
        settings = QSettings('settings.ini',QSettings.IniFormat)
        settings.setFallbacksEnabled(False)

        for aspinbox in self.findChildren(QtGui.QDoubleSpinBox) + self.findChildren(QtGui.QSpinBox):
            name = aspinbox.objectName()
            value= settings.value(name).toFloat()[0]

            aspinbox.setValue(value)

        readingslist = ["Readingsaction{:}".format(i) for i in range(8)]
        plotslist = ["Plotsaction{:}".format(i) for i in range(8)]
        for anAction in self.findChildren(QtGui.QAction):
            name = anAction.objectName()
            state=settings.value(name).toBool()
            if len(name) > 0:
                if not state:
                    try:
                        if name in readingslist:
                            ind = int(name[-1])
                            self.channellist[ind].readingswidget.setHidden(not state)
                            anAction.toggle()
                        elif name in plotslist:
                            ind = int(name[-1])
                            self.channellist[ind].plotwidget.setHidden(not state)
                            anAction.toggle()
                    except Exception,e:
                        print e
        sfreqlist = ["Showfreq{:}".format(i) for i in range(8)]
        ssiglist = ["Showsig{:}".format(i) for i in range(8)]
        limfreqlist = ["Usefreqlim{:}".format(i) for i in range(8)]
        limsiglist = ["Usesiglim{:}".format(i) for i in range(8)]
        for aBox in self.findChildren(QtGui.QCheckBox):
            name = aBox.objectName()
            state=settings.value(name).toBool()
            if len(name) > 0:
                if state:
                    try:
                        ind = int(name[-1])
                        aBox.setChecked(state)
                        if name in sfreqlist:
                            self.channellist[ind].plotwidget.showfreq_toggled(2)
                        elif name in ssiglist:
                            self.channellist[ind].plotwidget.showsig_toggled(2)
                        elif name in limfreqlist:
                            self.channellist[ind].freqlim = state
                        elif name in limsiglist:
                            self.channellist[ind].siglim = state
                    except Exception,e:
                        print e

    def closeEvent(self,event):
        settings = QSettings('settings.ini',QSettings.IniFormat)
        for aspinbox in self.findChildren(QtGui.QDoubleSpinBox) + self.findChildren(QtGui.QSpinBox):
            name = aspinbox.objectName()
            value= aspinbox.value()
            settings.setValue(name,value)

        for aAction in self.findChildren(QtGui.QAction):
            name = aAction.objectName()
            state = aAction.isChecked()
            settings.setValue(name,state)

        for aBox in self.findChildren(QtGui.QCheckBox):
            name = aBox.objectName()
            state = aBox.isChecked()
            settings.setValue(name,state)
        settings.sync()

        for awidget in QtGui.QApplication.instance().topLevelWidgets():
            awidget.close()


    ########################################################
    #######    Event functions for the main window
    ########################################################
    #Starts the magic (the process)
    def start_pressed(self):
        self.timestart = time.time()
        self.timestamp = 0
        self.timer.start(self.updatespeed)

    #Stops the process
    def stop_pressed(self):
        self.timer.stop()

    #Resets the warnings and clears the warningsbox
    def resetwarning_pressed(self):
        for i in self.channellist:
            i.plotwidget.setbackground('default')
            i.readingswidget.setbackground('default')
     
    #Resets all plots   
    def resetall_pressed(self):
        for i in self.channellist:
            i.plotwidget.reset_plots()

    #Toggles the settingswindow 
    def config_pressed(self):
        self.settingswidget.setHidden(not self.settingswidget.isHidden())

        # Scales all xaxis to autoscaling
    def autoscalex_pressed(self):
        plotlist = []
        for achannel in self.channellist: 
            if achannel.plotwidget.showfreq:
                plotlist.append(achannel.plotwidget.freqplot)
            if achannel.plotwidget.showsig:
                 plotlist.append(achannel.plotwidget.sigplot)

        for aplot in plotlist:
            aplot.getViewBox().enableAutoRange(aplot.getViewBox().XAxis)

    def warningtext_contextmenu(self,event):
        self.menu = QtGui.QMenu(self)
        clearAction = QtGui.QAction('clear',self)
        clearAction.triggered.connect(lambda : self.warningtext.setText(""))
        self.menu.addAction(clearAction)
        self.menu.popup(QtGui.QCursor.pos())

    def logwarning_toggled(self,state,lbl):
        if state == 2:
            if self.connection is None:
                try:
                    self.connection = labrad.connect()
                except Exception,e:
                    lbl.setText(str(e))
           
            self.errorserver = self.connection.ParameterVault
            if not self.errorserver.check_error_log()[0]:
                filename = self.errorserver.start_error_log()
                lbl.setText(filename)
            else:
                lbl.setText("File already running")
        else:
            lbl.setText("")
            if self.connection is not None:
                self.errorserver.stop_error_log()
                self.errorserver = None
                self.connection.disconnect()
                self.connection = None
           


    ########################################################
    #######    Graphicswidget, which contains a plotarea for
    #######       each channel
    ########################################################
    def makeGraphsWidget(self):
        widget = QtGui.QSplitter(Qt.Vertical)
        for i in range(8):
            self.channellist[i].plotwidget = signalwindow(i+1)
            self.channellist[i].newminmax = True
            widget.addWidget(self.channellist[i].plotwidget)
        return widget

    ########################################################
    #######    Readingswidget, which contains a panel for 
    #######       each channel
    ########################################################
    def makeReadingswidget(self):
        self.expotimereading = readingsbox(99)
        dockwidget = QtGui.QDockWidget('Readings')
        widget = QtGui.QWidget()
        toolbar = QtGui.QToolBar()
        toolbar.setStyleSheet('QToolButton::checked {border: inset; border-width: 1px}')
        layout = QtGui.QVBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(toolbar)
        for i in range(8):
            #A sneaky way to save space and still make clicking the toolbar hide or show the relevant panel
            toolbar.addAction('{:}'.format(i+1), lambda who=i: self.channellist[who].readingswidget.setHidden(not self.channellist[who].readingswidget.isHidden()))
            self.channellist[i].readingswidget = readingsbox(i+1)
        # Add exposure reading
        toolbar.addAction('ms',lambda :self.expotimereading.setHidden(not self.expotimereading.isHidden()))
        #Make all buttons clickable, and make all clicked (by default all channels are shown)
        cnt = 0
        for i in toolbar.actions(): 
            i.setCheckable(True)
            i.setChecked(True)
            i.setObjectName("Readingsaction{:}".format(cnt))
            cnt += 1
        #Add widgets to layout
        for i in self.channellist:
            layout.addWidget(i.readingswidget)
        layout.addWidget(self.expotimereading)
        widget.setLayout(layout)
        dockwidget.setWidget(widget)
        dockwidget.setFeatures(QtGui.QDockWidget.DockWidgetFloatable | QtGui.QDockWidget.DockWidgetMovable)
        return dockwidget
        
########################################################################
#########                                                      #########
#########    Make a settingswidget, which contains multiple    #########
#########       tab panels. its implemented as a dockwidget    #########
#########        that starts hidden and floating               #########
#########                                                      #########
########################################################################
    #Main widget
    def makeSettingswidget(self):
        dockwidget = QtGui.QDockWidget('Settings')
        widget = QtGui.QTabWidget()
        generalpanel = self.makeGeneralPanel()
        regulationpanel = self.makeRegulationPanel()
        widget.addTab(generalpanel,'General')
        widget.addTab(regulationpanel,'Regulation')
        dockwidget.setWidget(widget)
        dockwidget.setFeatures(QtGui.QDockWidget.DockWidgetFloatable | QtGui.QDockWidget.DockWidgetMovable)
        dockwidget.setHidden(True) #So it starts hidden
        return dockwidget

    #General tab
    def makeGeneralPanel(self):
        widget = QtGui.QWidget()
        layout = QtGui.QVBoxLayout()
        ratepanel = self.makeratepanel()
        channeltoolbar = self.makechanneltoolbar()
        plotsettings = self.makeplotsettings()
        layout.addWidget(ratepanel)
        layout.addWidget(channeltoolbar)
        layout.addWidget(plotsettings)
        widget.setLayout(layout)
        return widget

    #Controls updaterates and random buttons
    def makeratepanel(self):
        widget = QtGui.QWidget()
        #Create gui elements
        linkview = QtGui.QCheckBox('Link xaxis')
        updatelabel = QtGui.QLabel('Update speed')
        update = QtGui.QSpinBox()
        plotlabel = QtGui.QLabel('Plot speed')
        plot = QtGui.QDoubleSpinBox()
        logbutton = QtGui.QPushButton('Start Logging')
        logfilename = QtGui.QLineEdit()

        #Modify elements
        plotlabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        updatelabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        update.setValue(25)
        update.setObjectName('Updaterate')
        update.setSingleStep(5)
        update.setSuffix(' ms')
        update.setRange(1,10000)
        plot.setSuffix(' s')
        plot.setObjectName('Plotrate')
        plot.setValue(1)
        plot.setSingleStep(0.25)
        plot.setRange(0.001,300)
        logfilename.setPlaceholderText('<current timestamp> +')

        #Connect events
        linkview.stateChanged.connect(self.linkview_toggled)
        update.valueChanged.connect(self.updatevalue_changed)
        plot.valueChanged.connect(lambda val: setattr(self,'plotspeed',val))
        logbutton.pressed.connect(lambda : self.logbutton_pressed(logfilename))

        #Create layout
        layout = QtGui.QGridLayout()
        layout.addWidget(linkview,0,0)
        layout.addWidget(updatelabel,0,2)
        layout.addWidget(update,0,3)
        layout.addWidget(plotlabel,1,2)
        layout.addWidget(plot,1,3)
        layout.addWidget(logbutton,1,0)
        layout.addWidget(logfilename,1,1)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        widget.setLayout(layout)
        return widget

    #Toolbar to select plots to show
    def makechanneltoolbar(self):
        toolbar = QtGui.QToolBar()
        toolbar.addWidget(QtGui.QLabel('Channels to display:'))
        toolbar.addSeparator()
        for i in range(8):
            toolbar.addAction('{:}'.format(i+1), lambda who=i: self.channellist[who].plotwidget.setHidden(not self.channellist[who].plotwidget.isHidden()))
            toolbar.actions()[i+2].setCheckable(True)
            toolbar.actions()[i+2].setObjectName('Plotsaction{:}'.format(i))
            toolbar.actions()[i+2].setChecked(True)
        return toolbar

    #Plot settings
    def makeplotsettings(self):
        widget = QtGui.QWidget()
        layout = QtGui.QGridLayout()
        for i in range(8):
            #Create elements
            miniwidget = QtGui.QFrame()
            framelayout = QtGui.QGridLayout()
            freq = QtGui.QCheckBox('Freq')
            sig = QtGui.QCheckBox('Sig')
            channellabel = QtGui.QLabel('Chan {:}'.format(i+1))
            minfreq = QtGui.QDoubleSpinBox()
            maxfreq = QtGui.QDoubleSpinBox()
            minsig = QtGui.QDoubleSpinBox()
            maxsig = QtGui.QDoubleSpinBox()
            freqlim = QtGui.QCheckBox('Use limits')
            siglim = QtGui.QCheckBox('Use limit')
            minfreqlabel = QtGui.QLabel('Min')
            maxfreqlabel = QtGui.QLabel('Max')
            minsiglabel = QtGui.QLabel('Min')
            maxsiglabel = QtGui.QLabel('Max')
            dologging = QtGui.QCheckBox('Log')
            
            #Modify elements
            for k in [minfreq,maxfreq]:
                k.setRange(0,1000)
                k.setDecimals(6)
                k.setSingleStep(0.000001)
                k.setSuffix(' THz')
            for k in [minsig,maxsig]:
                k.setRange(-10000,10000)
                k.setDecimals(0)
                k.setSingleStep(10)
                k.setSuffix(' mV')
            minfreq.setObjectName('Channel{:}minfreq'.format(i));maxfreq.setObjectName('Channel{:}maxfreq'.format(i))
            minsig.setObjectName('Channel{:}minsig'.format(i));maxsig.setObjectName('Channel{:}maxsig'.format(i))
            freq.setObjectName('Showfreq{:}'.format(i));sig.setObjectName('Showsig{:}'.format(i))
            freqlim.setObjectName('Usefreqlim{:}'.format(i));siglim.setObjectName('Usesiglim{:}'.format(i))
            #Create handlers
            minfreq.valueChanged.connect(lambda val, who=i: setattr(self.channellist[who],'freqlimmin',val))
            maxfreq.valueChanged.connect(lambda val, who=i: setattr(self.channellist[who],'freqlimmax',val))
            minsig.valueChanged.connect(lambda val, who=i: setattr(self.channellist[who],'siglimmin',val))
            maxsig.valueChanged.connect(lambda val, who=i: setattr(self.channellist[who],'siglimmax',val))
            freq.stateChanged.connect(lambda state,who = i: self.channellist[who].plotwidget.showfreq_toggled(state))
            freqlim.stateChanged.connect(lambda state, who=i: setattr(self.channellist[who],'freqlim',True if state == 2 else False))
            sig.stateChanged.connect(lambda state, who=i: self.channellist[who].plotwidget.showsig_toggled(state))
            siglim.stateChanged.connect(lambda state, who=i: setattr(self.channellist[who],'siglim',True if state == 2 else False))
            dologging.stateChanged.connect(lambda state,who=i: setattr(self.channellist[who],'logging',True if state == 2 else False))
            
            #Create layout
            framelayout.addWidget(freq,0,1)
            framelayout.addWidget(minfreqlabel,0,2)
            framelayout.addWidget(minfreq,0,3)
            framelayout.addWidget(maxfreq,0,4)
            framelayout.addWidget(maxfreqlabel,0,5)
            framelayout.addWidget(freqlim,0,6)
            framelayout.addWidget(sig,1,1)
            framelayout.addWidget(minsiglabel,1,2)
            framelayout.addWidget(minsig,1,3)
            framelayout.addWidget(maxsig,1,4)
            framelayout.addWidget(maxsiglabel,1,5)
            framelayout.addWidget(siglim,1,6)
            framelayout.setAlignment(Qt.AlignCenter)
            miniwidget.setLayout(framelayout)
            miniwidget.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
            layout.addWidget(channellabel,3*i+1,0)
            layout.addWidget(dologging,3*i+2,0)
            layout.addWidget(miniwidget,3*i,1,3,1)
        widget.setLayout(layout)
        return widget

    # Panel for the regulation settings
    def makeRegulationPanel(self):
        widget = QtGui.QWidget()
        layout = QtGui.QGridLayout()
        for i in range(8):
            #Create elements
            miniwidget = QtGui.QFrame()
            framelayout = QtGui.QGridLayout()
            targetlabel = QtGui.QLabel('Target Value')
            plabel = QtGui.QLabel('P')
            ilabel = QtGui.QLabel('I')
            dlabel = QtGui.QLabel('D')
            outputlabel = QtGui.QLabel('Output')
            senslabel = QtGui.QLabel('Sensitivity')
            senslabel2 = QtGui.QLabel('(V/GHz)')
            targetvalue = QtGui.QDoubleSpinBox()
            pvalue = QtGui.QDoubleSpinBox()
            ivalue = QtGui.QDoubleSpinBox()
            dvalue = QtGui.QDoubleSpinBox()
            sensitivity = QtGui.QDoubleSpinBox()
            outputchannel = QtGui.QSpinBox()
            regulate = QtGui.QCheckBox("Chan {:}".format(i+1))
            steplimitvalue = QtGui.QSpinBox()
            steplimitlabel = QtGui.QLabel('Steplimit')
            polaritylabel = QtGui.QLabel('Polarity')
            polaritysign = MyComboBox()
            #Modify elements
            targetvalue.setDecimals(6)
            targetvalue.setRange(0,1000)
            outputchannel.setRange(1,8)
            outputchannel.setValue(i+1)
            steplimitvalue.setRange(1,1000)
            steplimitvalue.setSuffix(' MHz')
            steplimitvalue.setSingleStep(1)
            steplimitvalue.setValue(10)
            polaritysign.addItems(['Neg','Pos'])
            for abox in [pvalue, ivalue, dvalue]:
                abox.setSingleStep(0.1)
            pvalue.setObjectName('Channel{:}pvalue'.format(i+1))
            ivalue.setObjectName('Channel{:}ivalue'.format(i+1))
            dvalue.setObjectName('Channel{:}dvalue'.format(i+1))
            sensitivity.setObjectName('Channel{:}sensitivity'.format(i+1))
            targetvalue.setObjectName('Channel{:}target'.format(i+1))
            outputchannel.setObjectName('Channel{:}outputchannel'.format(i+1))
            steplimitvalue.setObjectName('Channel{:}steplimit'.format(i+1))
            polaritysign.setObjectName('Channel{:}polarity'.format(i+1))

            # Connect events
            pvalue.valueChanged.connect(lambda val, who= i: setattr(self.channellist[who],'pvalue',val))
            ivalue.valueChanged.connect(lambda val, who=i: setattr(self.channellist[who],'ivalue',val))
            dvalue.valueChanged.connect(lambda val, who=i: setattr(self.channellist[who],'dvalue',val))
            targetvalue.valueChanged.connect(lambda val, who=i: setattr(self.channellist[who],'targetvalue',val))
            sensitivity.valueChanged.connect(lambda val, who=i: setattr(self.channellist[who],'sensitivity',val))
            regulate.stateChanged.connect(lambda state, who=i: self.regulate_toggled(state,who))
            steplimitvalue.valueChanged.connect(lambda val, who=i: setattr(self.channellist[who],'steplimitvalue',val/100.))
            polaritysign.currentIndexChanged.connect(lambda val,who=i: setattr(self.channellist[who],"pospolarity",val))
            # Add to layout grid
            framelayout.addWidget(targetlabel,0,1)
            framelayout.addWidget(targetvalue,1,1)
            framelayout.addWidget(outputlabel,0,3)
            framelayout.addWidget(outputchannel,1,3)
            framelayout.addWidget(plabel,2,0)
            framelayout.addWidget(pvalue,2,1)
            framelayout.addWidget(ilabel,2,2)
            framelayout.addWidget(ivalue,2,3)
            framelayout.addWidget(dlabel,2,4)
            framelayout.addWidget(dvalue,2,5)
            framelayout.addWidget(steplimitlabel,0,5)
            framelayout.addWidget(steplimitvalue,1,5)
            framelayout.addWidget(senslabel,0,6)
            framelayout.addWidget(senslabel2,1,6)
            framelayout.addWidget(sensitivity,2,6)
            framelayout.addWidget(polaritylabel,1,7)
            framelayout.addWidget(polaritysign,2,7)
            framelayout.setAlignment(Qt.AlignCenter)
            miniwidget.setLayout(framelayout)
            miniwidget.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
            layout.addWidget(regulate,i,0)
            layout.addWidget(miniwidget,i,1)
        widget.setLayout(layout)
        return widget

    ########################################################
    #######    Event functions for the settings window
    ########################################################
    #Links all xaxis together
    def linkview_toggled(self,state):
        print "Disabled - broken ATM"
        '''
        plotlist = []
        for achannel in self.channellist: #Get a list of all plots currently displayed
            if achannel.plotwidget.showfreq:
                plotlist.append(achannel.plotwidget.freqplot)
            if achannel.plotwidget.showsig:
                 plotlist.append(achannel.plotwidget.sigplot)

        for i in range(len(plotlist)):
            for j in range(i,len(plotlist)):
                if i == j:
                    continue
                else:
                    if state == 2:
                        plotlist[i].setXLink(plotlist[j]) #link the plot with all the rest
                    else:
                        plotlist[i].setXLink(plotlist[i].getViewBox()) #link the plot with itself
        '''
                        
    # activates or disactivates regulation, also clears the integrator                  
    def regulate_toggled(self,state,num):
        self.channellist[num].regulate = True if state == 2 else False
        self.channellist[num].lasterror = 0
        self.channellist[num].integratederror = 0
        self.channellist[num].regulationsignal = 0
    
    # Changes the updatespeed  (updates from the wavemeter)     
    def updatevalue_changed(self,newvalue):
        self.updatespeed = newvalue
        if self.timer.isActive():
            self.timer.start(newvalue)

    def logbutton_pressed(self,fnamefield):
        sender = self.sender()
        timestr = datetime.datetime.today().strftime("%Y%m%d_%H%M%S")
        fname = fnamefield.text()
        if len(fname)>0:
            fname = "_" + fname
        fname += ".csv"
        fname = unicode(timestr + fname)
        if self.logging:
            sender.setText('Start logging')
            fnamefield.setText("")
            fnamefield.setReadOnly(False)
            self.logging = False
            fnamefield.setStyleSheet("background-color:white")
            self.logfilename = None
            if self.logfile:
                self.logfile.close()
                self.logfile = None
        else:
            self.logfile = open("./wavemeterlogging/"+fname,'w')
            string = "Timestamp,"
            for i in range(8):
                string += "Chan{0} Avg Freq[THz],Chan{0} std Freq[THz],Chan{0} Avg Reg [mV],Chan{0} std Reg [mV]".format(i+1,i+1)
            self.logfile.write(string + "\n")
            sender.setText('Stop logging')
            fnamefield.setReadOnly(True)
            fnamefield.setText(fname)
            self.logging = True
            fnamefield.setStyleSheet("background-color:lightgrey")

    
########################################################################
#########                                                      #########
#########    Updatefunctions for reading from the wavemeter    #########
#########       and doing the PID calculations                 #########
#########                                                      #########
#########                                                      #########
########################################################################
    #Main reading from wavemeter and upate everything else
    def update(self):
        plotupdate = False
        updated = False
        dtime = time.time()-self.timestamp
        logstring = ""
        totalexptime = 0 #Counter for total exposure tume
        #Checks if plottime has passed, so the plot should update again. Prevents the plot from updating every wavemeterreading
        if dtime> self.plotspeed:
            self.timestamp = time.time()
            logstring += datetime.datetime.fromtimestamp(self.timestamp).strftime("%Y%m%d %H:%M:%S")
            logstring += ","
            plotupdate = True
        for i in range(8):
            channel = self.channellist[i]
            ########################################################
            #######    Get data from the wavemeter
            ########################################################
            if not debug:
                #Check if channel is active
                used = self.wavemeter.getUsed(i+1)
                if used:
                    freq = self.wavemeter.getFrequency(i+1)
                    expo = self.wavemeter.getFullExposure(i+1)
                    amp = self.wavemeter.getAmplitudes(i+1)
                    if channel.regulate and channel.regulationsignal is not None:
                        sig = channel.regulationsignal
                    else:
                        sig = self.wavemeter.getDeviation(i+1)
                    if freq != channel.prefreq:
                        updated = True
                #If channel is not used, set everything to zero.
                else: 
                    freq = 0; sig = 0;  expo = 0; amp = (0,0)
                totalexptime += expo
            else:
                used = True
                updated = True
                freq = random.random() + self.debugint + 100
                sig=random.random() +2
                amp = (random.random(),random.random())
                expo = random.random()+20
                self.debugint += 0.001
            
            if used and updated:
                channel.sumfreq += freq
                channel.sumsquarefreq += sqr(freq)
                channel.sumsig += sig
                channel.sumsquaresig += sqr(sig)
                channel.sumint += 1
                freqavg = channel.sumfreq/float(channel.sumint)
                freqstd = np.sqrt(channel.sumsquarefreq/float(channel.sumint)-sqr(freqavg))
                sigavg = channel.sumsig/float(channel.sumint)
                sigstd = np.sqrt(channel.sumsquaresig/float(channel.sumint)-sqr(sigavg))

                if channel.logging:
                    logstring += "{:},{:},{:},{:}".format(freqavg,freqstd,sigavg,sigstd)
                else:
                    logstring += ",,"

                ########################################################
                #######    Update minmax values
                ########################################################
                if channel.newminmax: #If the current minmax value has been plotted, we need a new one
                    channel.freqmin,channel.freqmax = [freq,freq]
                    channel.sigmin,channel.sigmax = [sig,sig]
                    channel.newminmax = False
                    channel.sumfreq = 0.0; channel.sumsig = 0.0
                    channel.sumsquarefreq = 0.0; channel.sumsquaresig = 0.0
                    channel.sumint = 0
                else: # Else update the minmax values
                    channel.freqmin = min(freq,channel.freqmin)
                    channel.freqmax = max(freq,channel.freqmax)
                    channel.sigmin = min(sig,channel.sigmin)
                    channel.sigmax = max(sig,channel.sigmax)

                #Update the minmax values
                minfreq,maxfreq = [channel.freqlimmin,channel.freqlimmax]
                minsig,maxsig = [channel.siglimmin,channel.siglimmax]
                        
                ########################################################
                #######    Check limits, use previous value to only 
                #######    write log on crossings
                #######    This happens on wavemeterupdatespeed, not
                #######    plotspeed
                ########################################################
                prefreq = channel.prefreq  
                presig = channel.presig
                warning = False
                crossingwarning = False
                tmptxt = datetime.datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")
                tmpstr = ""

                #Check all the limits and previous values
                if channel.freqlim and minfreq > freq:
                    warning = True
                    if prefreq > minfreq:
                        crossingwarning = True
                        tmpstr +=tmptxt + ": Freq {:} went below limit ({:.9})\n".format(i+1,freq)
 
                if channel.freqlim and maxfreq < freq:
                    warning = True
                    if prefreq<maxfreq:
                        crossingwarning = True
                        tmpstr += tmptxt +": Freq {:} went above limit ({:.9})\n".format(i+1,freq)
                    
                if channel.siglim and minsig  > sig and presig > minsig:
                    warning = True
                    if presig>minsig:
                        crossingwarning = True
                        tmpstr += tmptxt + ": Sig {:} went below limit ({:.9})\n".format(i+1,sig) 
                if channel.siglim and maxsig  < sig:
                    warning = True
                    if presig < maxsig:
                        crossingwarning = True
                        tmpstr += tmptxt + ": Sig {:} went below limit ({:.9})\n".format(i+1,sig) 

                #Color plot and reading red
                if warning:
                    channel.plotwidget.setbackground('r')
                    channel.readingswidget.setbackground('red')
                    if crossingwarning:
                        tmpstr = tmpstr[:-1]
                        self.warningtext.append(tmpstr)
                        if self.errorserver is not None:
                            self.errorserver.write_error(tmpstr)

                #Update prevvalues to be used in next iteration
                channel.prefreq = freq
                channel.presig = sig
            else:
                    logstring += ",,"
            ########################################################
            #######    Update readings, plots and regulations
            #######     if they are not hidden and/or active
            ########################################################
            if not channel.readingswidget.isHidden():
                channel.readingswidget.update_reading(freq)
                channel.readingswidget.update_amp(amp)
                channel.readingswidget.update_expos(expo)
            
            if plotupdate and used:
                channel.newminmax = True
                channel.plotwidget.update(self.timestamp,channel)

            if channel.regulate and used:
                self.updateregulation(channel,self.timestamp,freq)
        
        #Placed out here because its not part of the 8 channel loop
        if not self.expotimereading.isHidden():
            self.expotimereading.update_reading(totalexptime)
        if plotupdate and self.logfile is not None:
            self.logfile.write(logstring + "\n")


    ########################################################
    #######    PID loop function
    ########################################################
    def updateregulation(self,channel,timestamp,freq):
        signum = channel.channel # wavemeter function wants 1-8 not 0-7
        p = channel.pvalue
        i = channel.ivalue
        d = channel.dvalue
        target = channel.targetvalue
        sensitivity = channel.sensitivity
        steplimitMHz = channel.steplimitvalue
        interr = channel.integratederror
        lasterror = channel.lasterror
        pospol = channel.pospolarity
        firstglitch = channel.firstglitch
        error = freq-target
        pval = p * error 
        ival = i * (interr + error)
        dval = d * (error-lasterror)

        steplimitV = steplimitMHz/1000.*sensitivity*1000

        diff = lasterror-error
        if abs(diff) > steplimitV:
            if firstglitch:
                error = 0
                firstglitch = False
            else:
                error = steplimitV * ( -1 if error < 0 else 1)
        else:
            firstglitch = True
        
        regulationsignal = (pval + ival + dval) * sensitivity * 1000 #since sensitivty is in V/GHz

        channel.integratederror += error
        channel.lasterror = error
        
        #Truncate to +- 10000 mV
        if abs(regulationsignal) > 10000:
            regulationsignal = 10000 if regulationsignal > 0 else -10000
        if not pospol:
            regulationsignal = regulationsignal* -1
        channel.regulationsignal = regulationsignal
        if not debug:
            self.wavemeter.setRegulation(signum,regulationsignal)

########################################################################
#########                                                      #########
#########    Helper classes used to store data, control        #########
#########       plots and so on...                             #########
#########                                                      #########
########################################################################

########################################################
#######    Information storing class
########################################################
class channelinformation:
    def __init__(self,channel):
        self.channel = channel # channelnumber 1-8

        #plot and readingswidget for this channel
        self.readingswidget = None;  self.plotwidget = None

        #Bools
        self.freq = False; self.sig = False # Show plots or not
        self.newminmax = False # New minimum/maximum value, because the last got plotted
        self.freqlim = False; self.siglim = False #Use limits or not
        self.regulate = False  #Regulate or not
        self.logging = False #log data or not
        
        #Variables for plotting
        #for mimimum/maximum calculation
        self.prefreq = 0; self.presig = 0
        self.freqmin = 0; self.freqmax = 0; self.sigmin = 0; self.sigmax = 0;
        #Mimimum/maximum limits
        self.freqlimmin = 0; self.freqlimmax = 0; self.siglimmin = 0; self.siglimmax = 0
        #for average determination
        self.sumfreq = 0 ; self.sumsig = 0;
        self.sumsquarefreq = 0; self.sumsquaresig = 0;
        self.sumint = 0

        #PID variables
        self.pvalue = 0; self.ivalue = 0; self.dvalue = 0
        self.targetvalue = 0; self.sensitivity = 0
        self.steplimitvalue = 0.1 #Limit on how large steps can be made
        self.lasterror = 0; self.integratederror = 0
        self.pospolarity = 0
        self.regulationsignal = 0
        self.firstglitch = True # Used to make the PID loop ignore single value large changes

########################################################
#######    Plotting class, which also stores all the data
#######    Data is stored in a buffer, which, when full
#######    bins the lower half and stores at a much lower
#######    resolution (currently 100s vs 1s)
########################################################
class signalwindow(pg.GraphicsLayoutWidget):
    def __init__(self,channel,useOpenGL=True):
        super(signalwindow,self).__init__()
        self.channel = channel
        self.showfreq = False
        self.showsig = False
        textitem = pg.TextItem('Channel '+str(self.channel)) #Channellabel
        font = QtGui.QFont()
        font.setWeight(99)
        textitem.setFont(font)
        self.setContentsMargins(0,0,0,0)
        self.scene().addItem(textitem)
        self.freqplot = pg.PlotItem(axisItems={'bottom':DateAxis(orientation='bottom')})
        self.sigplot = pg.PlotItem(axisItems={'bottom':DateAxis(orientation='bottom')})
        self.initialize()
   
    #Initializes all buffers
    def initialize(self):
        self.highresbuffer = 10000
        self.longtermres = 100
        self.timedata = [None] * self.highresbuffer
        self.freqmindata = [None] * self.highresbuffer; self.freqmaxdata = [None] * self.highresbuffer
        self.sigmindata  = [None] * self.highresbuffer;  self.sigmaxdata = [None] * self.highresbuffer
        self.timedatalongterm = []; 
        self.freqmindatalongterm = []; self.freqmaxdatalongterm = []; 
        self.sigmindatalongterm  = [];  self.sigmaxdatalongterm = []        
        self.counter = 0

    #Used to color the background of the plots in case of warnings
    def setbackground(self,colorstring):
        self.setBackground(colorstring)

    #To show the frequency plot or not
    def showfreq_toggled(self,event):
        if event == 2:
            self.addItem(self.freqplot)
            self.showfreq = True
        else:
            self.removeItem(self.freqplot)
            self.showfreq = False

    #To show the signal plot or not
    def showsig_toggled(self,event):
        if event == 2:
            self.addItem(self.sigplot)
            self.showsig = True
        else:
            self.removeItem(self.sigplot)
            self.showsig = False

    #When frequency is reset
    def reset_plots(self):
        self.initialize()
        self.freqplot.clear()
        self.sigplot.clear()
    
    #Update plot with the data currently in the freqmin/freqmax/sigmin/sigmax variable
    def update(self,timestamp,channel):

        #In case of buffer overflow, compress half of buffer to lower resolution
        if self.counter == self.highresbuffer:
            ind = self.highresbuffer/2
            for i in range(0,ind,self.longtermres):
                timeslice = self.timedata[i:i+self.longtermres]
                freqminslice = self.freqmindata[i:i+self.longtermres]
                freqmaxslice = self.freqmaxdata[i:i+self.longtermres]
                sigminslice = self.sigmindata[i:i+self.longtermres]
                sigmaxslice = self.sigmaxdata[i:i+self.longtermres]

                self.timedatalongterm.append(np.mean(timeslice))
                self.freqmindatalongterm.append(min(freqminslice))
                self.freqmaxdatalongterm.append(max(freqmaxslice))
                self.sigmindatalongterm.append(min(sigminslice))
                self.sigmaxdatalongterm.append(max(sigmaxslice))
            self.timedata[:ind] = self.timedata[ind:]
            self.freqmindata[:ind] = self.freqmindata[ind:]
            self.freqmaxdata[:ind] = self.freqmaxdata[ind:]
            self.sigmindata[:ind] = self.sigmindata[ind:]
            self.sigmaxdata[:ind] = self.sigmaxdata[ind:]

            self.counter = ind

        #Get the new values to plot
        self.timedata[self.counter] = timestamp
        self.freqmindata[self.counter] = channel.freqmin
        self.freqmaxdata[self.counter] = channel.freqmax
        self.sigmindata[self.counter] = channel.sigmin
        self.sigmaxdata[self.counter] = channel.sigmax
        if self.showfreq:
            self.freqplot.clear() #Clear plot of previous items, to prevent accumulating points
            one = pg.PlotCurveItem(self.timedatalongterm + self.timedata[:self.counter],self.freqmindatalongterm + self.freqmindata[:self.counter],pen='w')
            two = pg.PlotCurveItem(self.timedatalongterm + self.timedata[:self.counter],self.freqmaxdatalongterm + self.freqmaxdata[:self.counter],pen='w')
            self.freqplot.addItem(one)
            self.freqplot.addItem(two)
            #If limits are used, draw lines to indicate them
            if channel.freqlim: 
                self.freqplot.addItem(pg.InfiniteLine(channel.freqlimmin,angle=0,pen=pg.mkPen('w',style=Qt.DashLine)))
                self.freqplot.addItem(pg.InfiniteLine(channel.freqlimmax,angle=0,pen=pg.mkPen('w',style=Qt.DashLine)))
        if self.showsig:
            self.sigplot.clear()
            one = pg.PlotCurveItem(self.timedatalongterm + self.timedata[:self.counter],self.sigmindatalongterm + self.sigmindata[:self.counter],pen='y')
            two = pg.PlotCurveItem(self.timedatalongterm + self.timedata[:self.counter],self.sigmaxdatalongterm + self.sigmaxdata[:self.counter],pen='y')
            self.sigplot.addItem(one)
            self.sigplot.addItem(two)
            #If limits are used, draw lines to indicate them
            if channel.siglim:
                self.sigplot.addItem(pg.InfiniteLine(channel.siglimmin,angle=0,pen=pg.mkPen('y',style=Qt.DashLine)))
                self.sigplot.addItem(pg.InfiniteLine(channel.siglimmax,angle=0,pen=pg.mkPen('y',style=Qt.DashLine)))
        self.counter += 1

########################################################
#######    Class to create axis with datestrings
########################################################
class DateAxis(pg.AxisItem):
    prevticks = [] #used to save a working set of ticks

    #Overrides original function
    def tickValues(self,minVal,maxVal,size):
        tmpticks = super(DateAxis,self).tickValues(minVal,maxVal,size)
        for i in tmpticks: #handles when the spacing becomes weird and the marks bug out.
            if len(i[1]) == 0:
                tmpticks = self.prevticks
                break
        self.prevticks = tmpticks
        return tmpticks

    #Overrides original function
    def tickStrings(self, values, scale, spacing):
        strns = []

        rng = max(values)-min(values)

        if rng < 3600*24:
            string = '%H:%M:%S'
            label1 = '%b %d -'
            label2 = ' %b %d, %Y'
        elif rng >= 3600*24 and rng < 3600*24*30:
            string = '%d'
            label1 = '%b - '
            label2 = '%b, %Y'
        elif rng >= 3600*24*30 and rng < 3600*24*30*24:
            string = '%b'
            label1 = '%Y -'
            label2 = ' %Y'
        elif rng >=3600*24*30*24:
            string = '%Y'
            label1 = ''
            label2 = ''
        for x in values:
            try:
                strns.append(time.strftime(string, time.localtime(x)))
            except ValueError:  ## Windows can't handle dates before 1970
                strns.append('')
        try:
            label = time.strftime(label1, time.localtime(min(values)))+time.strftime(label2, time.localtime(max(values)))
        except ValueError:
            label = ''
        return strns    

########################################################
#######
#######    Class for displaying the readings
#######    
########################################################
class readingsbox(QtGui.QFrame):
    def __init__(self,label):
        super(readingsbox,self).__init__()
        self.channel = int(label)
        self.setFrameStyle(QtGui.QFrame.Box)
        self.ampbar = None
        labelpanel = QtGui.QWidget()

        #Create GUI elements
        if label == 99: # label 99 means its exposure
            self.channel = 99
            self.label = QtGui.QLabel("Exposure")
            self.reading = QtGui.QLabel('200 ms')
            self.exposurelabel = QtGui.QLabel()
            self.amplabel = QtGui.QLabel()
        else:
            self.label = QtGui.QLabel("Channel "+str(label))
            self.reading = QtGui.QLabel('399.442424')
            self.exposurelabel = QtGui.QLabel('32 ms')
            self.amplabel = QtGui.QLabel('0%/0%')
        self.default_style = self.label.styleSheet()
        self.reading.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        
        #Create handlers
        self.label.mouseDoubleClickEvent = self.change_label
        self.amplabel.mouseDoubleClickEvent = self.show_ampbar

        #layout elements
        labellayout = QtGui.QHBoxLayout()
        labellayout.setContentsMargins(0,0,0,0)
        labellayout.addWidget(self.label)
        labellayout.addWidget(self.exposurelabel)
        labellayout.addWidget(self.amplabel)
        labelpanel.setLayout(labellayout)

        layout = QtGui.QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(labelpanel,4,Qt.AlignTop)
        layout.addWidget(self.reading,Qt.AlignTop)
        self.setLayout(layout)
        self.reading.setSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Ignored)

    #Used to color the background of the reading in the case of a warning
    def setbackground(self,colorstring):
        if colorstring == 'default':
            self.reading.setStyleSheet(self.default_style)
        else:
            self.reading.setStyleSheet("QLabel {background-color:"+colorstring + "}")

    #Used to make the reading resize to larger fontsizes
    def resizeEvent(self, event):
        #--- fetch current parameters ----
        f = self.reading.font()
        cr = self.reading.contentsRect()
        #--- iterate to find the font size that fits the contentsRect ---
        dw = event.size().width() - event.oldSize().width()   # width change
        dh = event.size().height() - event.oldSize().height() # height change

        fs = max(f.pixelSize(), 1)        
        while True:
            f.setPixelSize(fs)
            br =  QtGui.QFontMetrics(f).boundingRect(self.reading.text())
            if dw >= 0 and dh >= 0: # label is expanding
                if br.height() <= cr.height() and br.width() <= cr.width():
                    fs += 1
                else:
                    f.setPixelSize(max(fs - 1, 1)) # backtrack
                    break                    
            else: # label is shrinking
                if br.height() > cr.height() or br.width() > cr.width():
                    fs -= 1
                else:
                    break
            if fs < 1: break
        #--- update font size ---           
        self.reading.setFont(f)  

    #Updates the reading
    def update_reading(self,value):
        if self.channel == 99:
            self.reading.setText("{:3.0f} ms".format(value))
        elif value == 0:
            self.reading.setText("         ")
        else:
            self.reading.setText("{:.6f}".format(value))

    #Updates the exposuretime label
    def update_expos(self,value):
        self.exposurelabel.setText("{:3.0f} ms".format(value))

    #Updates the amplitude label
    def update_amp(self,values):
        self.amplabel.setText("{:.0%}/{:.0%}".format(values[0],values[1]))
        if self.ampbar is not None:
            self.ampbar.values = values
            self.ampbar.repaint()

    def change_label(self,event):
        string, ok = QtGui.QInputDialog.getText(self,'Text input','Enter text to display:',text = "Channel "+str(self.channel))

        if ok:
            self.label.setText(string)

    def show_ampbar(self,event):
        self.ampbar = QtGui.QWidget()
        self.ampbar.resize(250,600)
        self.ampbar.paintEvent = self.ampbar_paint
        self.ampbar.values = (0.8,0.9)

        self.ampbar.show()

    def ampbar_paint(self,event):
        painter = QtGui.QPainter()
        values = self.ampbar.values
        cstring1 = 'red' if values[0]< 0.05 or values[0]>0.95 else "green"
        cstring2 = 'red' if values[1]< 0.05 or values[1]>0.95 else "green"

        painter.begin(self.ampbar)
        painter.setFont(QtGui.QFont('Decorative',30))
        height = self.ampbar.frameGeometry().height()
        width = self.ampbar.frameGeometry().width()
        barwidth = 0.35*width
        bartop1 = 0.8*height*(1-values[0])+0.1*height
        bartop2 = 0.8*height*(1-values[1])+0.1*height
        barbot1 = 0.8*height*values[0]
        barbot2 = 0.8*height*values[1]
        x1=0.1*width
        x2 = 0.55*width

        painter.fillRect(x1,bartop1,barwidth,barbot1,QtGui.QColor(cstring1))
        painter.fillRect(x2,bartop2,barwidth,barbot2,QtGui.QColor(cstring2))
        painter.drawText(x1,0*height,barwidth,0.1*height,Qt.AlignCenter,'{:.0%}'.format(values[0]))
        painter.drawText(x2,0*height,barwidth,0.1*height,Qt.AlignCenter,'{:.0%}'.format(values[1]))


########################################################
#######   Super silly class, only defined to override
#######    mousewheel events to prevent polarity to
#######    change rapidly if anybody uses the mousewheel
########################################################
class MyComboBox(QtGui.QComboBox):
    def wheelEvent(self,event):
        pass


########################################################
#######   
#######   Wavemeter class
#######     handles talking to the wavemeter DLL
#######
########################################################
class wlm:
    def __init__(self, dllpath="C:\Windows\System32\wlmData.dll"):
        """
        Wavelength meter class. 
        Argument: Optional path to the dll. Default: "C:\Windows\System32\wlmData.dll"
        """

        self.dllpath = dllpath
        if not os.path.isfile(dllpath):
            print 'cant find the file ', dllpath
        
        self.dll = ctypes.WinDLL(dllpath)
        self.freq = self.dll.GetFrequencyNum
        self.freq.restype = ctypes.c_double
        
        self.dev = self.dll.GetDeviationSignalNum
        self.dev.restype = ctypes.c_double

        self.exp = self.dll.GetExposureNum
        self.exp.restype = ctypes.c_long

        self.power = self.dll.GetPowerNum
        self.power.restype = ctypes.c_double
        
        self.amp = self.dll.GetAmplitudeNum
        self.amp.restype = ctypes.c_long
        
        self.getswitchersignalstates = self.dll.GetSwitcherSignalStates
        
        self.setDev = self.dll.SetDeviationSignalNum
    
    def getFrequency(self,channel):
        return self.freq(ctypes.c_long(channel),ctypes.c_double(0))
    
    def getDeviation(self,channel):
        return self.dev(ctypes.c_long(channel),ctypes.c_double(0))

    def getFullExposure(self,channel):
        return self.exp(ctypes.c_long(channel),ctypes.c_long(1),ctypes.c_long(0)) + self.exp(ctypes.c_long(channel),ctypes.c_long(2),ctypes.c_long(0))

    def getPower(self,channel):
        return self.power(ctypes.c_long(channel),ctypes.c_double(0))
        
    def getAmplitudes(self,channel):
        one = self.amp(ctypes.c_long(channel),ctypes.c_long(2),ctypes.c_long(0))
        two = self.amp(ctypes.c_long(channel),ctypes.c_long(3),ctypes.c_long(0))
        return (one/4000.,two/4000.) #converted to percentage
        
    def getUsed(self,channel):
        usedstate = ctypes.c_long()
        showedstate = ctypes.c_long()
        self.getswitchersignalstates(ctypes.c_long(channel),ctypes.byref(usedstate),ctypes.byref(showedstate))
        return usedstate.value

    def setRegulation(self,channel,val):
        self.setDev(ctypes.c_long(channel),ctypes.c_double(val))

if __name__=="__main__":
    a = QtGui.QApplication( [] )
    pl = wavemeterwidget()
    sys.exit(a.exec_())