#!/usr/bin/env python

'''
qToolUsaxs: provides table of Q values to position AR, AY, and DY

It provides a table of known positions and buttons
to move each of the motors.
'''

import datetime
import epics
import os
import sys
from PyQt4 import QtGui, uic

import bcdaqwidgets

import qTable

__project_name__  = 'qToolUsaxs'
__version__       = '2014-11'
__author__        = 'Pete Jemian'
__contact__       = 'jemian@anl.gov'
__organization__  = 'Advanced Photon Source, Argonne National Laboratory'
__copyright__     = 'Copyright (C) 2009-2014, UChicago Argonne, LLC, All Rights Reserved'
__license__       = 'qToolUsaxs is part of USAXS_tools; See LICENSE (included with this file) for full details.'
__url__           = 'http://usaxs.xray.aps.anl.gov/livedata'

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
MAIN_UI_FILE = os.path.join(THIS_DIR, 'qToolUsaxs.ui')
ABOUT_UI_FILE = os.path.join(THIS_DIR, 'about.ui')
LOGO_FILE = os.path.join(THIS_DIR, 'epicslogo101.gif')
USER_HOME_DIR = os.getenv('USERPROFILE') or os.getenv('HOME') # windows or Linux/Mac
DEFAULT_CONFIG_FILE = os.path.join(USER_HOME_DIR, '.qToolUsaxsrc')

STOP_BUTTON_STYLES = '''
    QPushButton { 
        background-color: #f44;
        color: black;
        text-align: center;
    }
    QPushButton:hover { 
        background-color: #f11;
        color: yellow;
        font: bold;
        text-align: center;
    }
'''
PV_MAP = {      # FIXME: check these PV names
    'energy'        : '9IDA:BraggERdbkAO',
    'Q,Finish'      : '9idcLAX:USAXS:Finish',
    'AR,enc'        : '9idcLAX:aero:c0:m1.RBV',
    'AR,enc,center' : '9idcLAX:USAXS:Q.B',
    'SDD'           : '9idcLAX:USAXS:SDD.VAL',
    'SAD'           : '9idcLAX:USAXS:SAD.VAL',
    'AY0'           : '9idcLAX:USAXS:AY0.VAL',
    'DY0'           : '9idcLAX:USAXS:DY0.VAL',
    'motor,AR'      : '9idcLAX:aero:c0:m1',
    'motor,AY'      : '9idcLAX:m58:c0:m6',
    'motor,DY'      : '9idcLAX:m58:c2:m4'
}
PV_MAP = {      # developer PV names
    'energy'        : 'vbox:userCalc1.A',
    'Q,Finish'      : 'vbox:userCalc1.B',
    'AR,enc'        : 'vbox:m1.RBV',
    'AR,enc,center' : 'vbox:userCalc1.C',
    'SDD'           : 'vbox:userCalc1.D',
    'SAD'           : 'vbox:userCalc1.E',
    'AY0'           : 'vbox:userCalc1.F',
    'DY0'           : 'vbox:userCalc1.G',
    'motor,AR'      : 'vbox:m1',
    'motor,AY'      : 'vbox:m2',
    'motor,DY'      : 'vbox:m3'
}
MOTOR_SYMBOLS = ('ar', 'ay', 'dy')


class Motor(object):
    
    pv = None
    pvname = None
    w_RBV = None
    w_VAL = None

    def connect(self, pvname):
        '''connect with EPICS'''
        if pvname is not None:
            self.pvname = pvname
            self.pv = epics.Motor(pvname)
    
    def move(self, value):
        if self.pv is not None:
            self.pv.move(value)
    
    def stop(self):
        if self.pvname is not None:
            self.pv.stop()


class USAXS_Q_tool(object):
    '''show the UI file'''

    def __init__(self, uifile, config_file = None):
        self.config_file = config_file or DEFAULT_CONFIG_FILE
        
        self.motors = {motor: Motor() for motor in MOTOR_SYMBOLS}

        self.ui = uic.loadUi(uifile)
        self._replace_standard_controls_()
        self._init_epics_controls_()
        self._init_actions_()
        # TODO: read configuration file
        # TODO: connect user parameters
        self.connect_to_EPICS()
    
    def _init_actions_(self):
        '''connect buttons with handlers'''
        self.ui.actionAbout.triggered.connect(self.doAbout)
        self.ui.actionExit.triggered.connect(self.doClose)
        self.ui.actionConfig_File_name.triggered.connect(self.doShowConfigFileName)

        self.ui.pb_stop.clicked.connect(self.doStop)
        self.ui.pb_stop.setStyleSheet(STOP_BUTTON_STYLES)
    
    def _init_epics_controls_(self):
        '''install EPICS motor controls'''
        layout = self.ui.layout_motors
        
        def build_motor_widgets(motor, column):
            w = bcdaqwidgets.BcdaQLabel()
            layout.addWidget(w, 1, column)
            self.motors[motor].w_RBV = w

            w = bcdaqwidgets.BcdaQLineEdit()
            layout.addWidget(w, 2, column)
            self.motors[motor].w_VAL = w
        
        for col, motor in enumerate(MOTOR_SYMBOLS):
            build_motor_widgets(motor, col+1)
    
    def connect_to_EPICS(self):
        for motor in MOTOR_SYMBOLS:
            obj = self.motors[motor]
            pvname = PV_MAP['motor,' + motor.upper()]
            obj.connect(pvname)
            obj.w_RBV.ca_connect(pvname+'.RBV', ca_callback=self.myCallback)
            obj.w_VAL.ca_connect(pvname+'.VAL')
    
    def myCallback(self, *args, **kw):
        #print kw
        # print sorted(kw.keys())
        # pvname
        # value
        # status
        # char_value
        #self.text_cache = char_value         # cache the new text locally
        #self.labelSignal.newText.emit()      # threadsafe update of the widget
        pass
    
#     def myConnect(self, *args, **kw):
#         print kw['conn']
#         if kw.get('char_value', None) is not None:
#             pass
    
    def _replace_standard_controls_(self):
        '''replace standard controls with EPICS controls'''
        self._replace_tableview_(None)
        # TODO: replace ARenc label
        # TODO: replace ARenc0 label
        # TODO: replace SAD label
        # TODO: replace SDD label
        # TODO: replace energy label

    def _replace_tableview_(self, q_table):
        '''install custom model-view support for Q table'''
        self.ui.tableView.deleteLater()
        gb = self.ui.groupBox_tableView
        layout = gb.layout()
        layout.setColumnStretch(0, 1)
        self.table = qTable.TableModel(q_table, parent=gb)
        self.tableview = qTable.TableView(self.doMove)
        layout.addWidget(self.tableview)
        self.tableview.setModel(self.table)

    def show(self):
        '''convenience method, hides .ui file implementation'''
        self.ui.show()

    def doAbout(self, *args, **kw):
        '''show the About box'''
        about = uic.loadUi(ABOUT_UI_FILE)
        about.icon.setPixmap(QtGui.QPixmap(LOGO_FILE))
        about.copyright.setText(__copyright__)
        about.url.setText(__url__)

        # feed the status message
        msg = 'About: '
        msg += __project_name__ 
        msg += ', v' + __version__
        msg += ', PID=' + str(os.getpid())
        self.setStatus(msg)
        about.show()
        about.exec_()

    def doClose(self, *args, **kw):
        self.setStatus('application exit requested')
        self.ui.close()
    
    def doStop(self, *args, **kw):
        '''stop all EPICS motors'''
        self.setStatus('STOP all motors requested')
        for motor in MOTOR_SYMBOLS:
            self.motors[motor].stop()
    
    def doShowConfigFileName(self, *args, **kw):
        '''display the config file name in the status text'''
        self.setStatus('config file: ' + self.config_file)

    def doReadConfig(self, config_file):
        '''read the configuration file'''
        if not os.path.exists(config_file):
            pass

    def doSaveConfig(self, config_file):
        '''save the configuration file'''
        pass
    
    def doMove(self, motor, text_value, *args, **kw):
        '''move the motor'''
        # validate first
        motor = motor.lower()
        if motor not in MOTOR_SYMBOLS: return
        value, ok = text_value.toDouble()
        if not ok: return
        
        self.setStatus('moving ... ' + motor + ' to ' + str(value))
        self.motors[motor].move(value)

    def recalculate(self, *args, **kw):
        '''recompute all terms'''
        self.setStatus('recalculating ...')
        # TODO: implement
#### wxPython code
#         A_keV = 12.3984244 # Angstrom * keV
#         try:   # get initial parameters
#             arEnc0 = float(self.parameterList['AR,enc,center']['entry'].GetValue())
#             ar = float(self.motorList['AR']['RBV'].GetValue())
#             arEnc = float(self.parameterList['AR,enc']['entry'].GetValue())
#             ar0 = arEnc0
#             energy = float(self.parameterList['energy']['entry'].GetValue())
#             lambda_over_4pi = A_keV / (energy * 4 * math.pi)
#             sad = float(self.parameterList['SAD']['entry'].GetValue())
#             sdd = float(self.parameterList['SDD']['entry'].GetValue())
#             ay0 = float(self.parameterList['AY0']['entry'].GetValue())
#             dy0 = float(self.parameterList['DY0']['entry'].GetValue())
#         except:
#             message = "recalc:  Error: " + str(sys.exc_info()[1])
#             self.postMessage(message)
#             return
# 
#         for row in range(len(self.positionList)):
#             ar = 'ar ' + str(row)
#             ay = 'ay ' + str(row)
#             dy = 'dy ' + str(row)
#             try:
#                 strQ = self.positionList[row]['Q']['entry'].GetValue()
#                 if len(strQ.strip()) > 0:
#                     q = float(strQ)
#                     x = -q * lambda_over_4pi
#                     ar = ar0 + 2*math.degrees(math.asin( x ))
#                     dy = dy0 + sdd * math.tan( x )
#                     ay = ay0 + sad * math.tan( x )
#                     # indicate limit problems with a yellow background
#                     self.positionList[row]['AR']['entry'].SetBackgroundColour(
#                         self.BUTTON_COLORS[self.motorLimitsOK("AR", ar)]
#                     )
#                     self.positionList[row]['AY']['entry'].SetBackgroundColour(
#                         self.BUTTON_COLORS[self.motorLimitsOK("AY", ay)]
#                     )
#                     self.positionList[row]['DY']['entry'].SetBackgroundColour(
#                         self.BUTTON_COLORS[self.motorLimitsOK("DY", dy)]
#                     )
#             except:
#                 message = "recalc:\t Error: " + sys.exc_info()[1]
#                 self.postMessage(message)
#             # put the values into the button labels
#             self.positionList[row]['AR']['entry'].SetLabel(str(ar))
#             self.positionList[row]['AY']['entry'].SetLabel(str(ay))
#             self.positionList[row]['DY']['entry'].SetLabel(str(dy))

    def setStatus(self, message):
        # ts = str(datetime.datetime.now())
        self.ui.statusBar().showMessage(str(message))


def main():
    app = QtGui.QApplication(sys.argv)
    view = USAXS_Q_tool(MAIN_UI_FILE)
    view.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
