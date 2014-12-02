#!/usr/bin/env python

'''
qToolUsaxs: provides table of Q values to position AR, AY, and DY

It provides a table of known positions and buttons
to move each of the motors.
'''


import epics
import math
import os
import sys
from PyQt4 import QtGui, uic

import bcdaqwidgets

import config
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
        self.motors = {motor: Motor() for motor in MOTOR_SYMBOLS}
        
        self.rcfile_name = config_file or DEFAULT_CONFIG_FILE
        self.rcfile = self.doReadConfig()

        self.ui = uic.loadUi(uifile)
        self._replace_standard_controls_()
        self._init_epics_controls_()
        self._init_actions_()
        self.connect_to_EPICS()
        
        self.ui.w_AY0_user.setText(self.rcfile.param.get('AY0', 0))
        self.ui.w_DY0_user.setText(self.rcfile.param.get('DY0', 0))
    
    def _init_actions_(self):
        '''connect buttons with handlers'''
        self.ui.actionAbout.triggered.connect(self.doAbout)
        self.ui.actionExit.triggered.connect(self.doClose)
        self.ui.actionRead.triggered.connect(self.doReadConfig)
        self.ui.actionSave.triggered.connect(self.doSaveConfig)
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
            # FIXME: when connected, motor PVs say "connected" and not the value
            # this is a problem in bcdaqwidgets
    
    def myCallback(self, *args, **kw):
        #print kw
        # print sorted(kw.keys())
        # pvname
        # value
        # status
        # char_value
        #self.text_cache = char_value         # cache the new text locally
        #self.labelSignal.newText.emit()      # threadsafe update of the widget
        #print 'monitor: pv=%s value=%s' % (kw['pvname'], kw['char_value'])
        pass
    
#     def myConnect(self, *args, **kw):
#         print kw['conn']
#         if kw.get('char_value', None) is not None:
#             pass
    
    def _replace_standard_controls_(self):
        '''replace standard controls with EPICS controls'''
        self._replace_tableview_(self.rcfile.toDataModel())
        
        layout = self.ui.layout_user_parameters
        
        def revise(widget, key, kind=None):
            kind = kind or bcdaqwidgets.BcdaQLabel
            row, _role = layout.getWidgetPosition(widget)
            lbl = layout.labelForField(widget)
            text = lbl.text()
            lbl.deleteLater()
            widget.deleteLater()
            widget = kind(pvname=PV_MAP[key])
            layout.insertRow(row, text, widget)
            return widget

        self.ui.w_ARenc = revise(self.ui.w_ARenc, 'AR,enc')
        self.ui.w_ARenc0 = revise(self.ui.w_ARenc0, 'AR,enc,center')
        self.ui.w_SAD = revise(self.ui.w_SAD, 'SAD', kind=bcdaqwidgets.BcdaQLineEdit)
        self.ui.w_SDD = revise(self.ui.w_SDD, 'SDD', kind=bcdaqwidgets.BcdaQLineEdit)
        self.ui.w_energy = revise(self.ui.w_energy, 'energy')

    def _replace_tableview_(self, q_table):
        '''install custom model-view support for Q table'''

        # these are the parents
        gb = self.ui.groupBox_tableView
        layout = self.ui.gridLayout_tableview
        
        # dispose the standard widget
        self.ui.tableView.deleteLater()

        # create the new content
        self.table = qTable.TableModel(q_table, parent=gb, recalc=self.recalculate)
        self.tableview = qTable.TableView(self.doMove)
        self.tableview.setModel(self.table)
        
        # a touch of configuration
        layout.setColumnStretch(0, 1)
        layout.addWidget(self.tableview)

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
        '''orderly exit'''
        self.setStatus('application exit requested')
        self.ui.close()
    
    def doStop(self, *args, **kw):
        '''stop all EPICS motors'''
        self.setStatus('STOP all motors requested')
        for motor in MOTOR_SYMBOLS:
            self.motors[motor].stop()
    
    def doShowConfigFileName(self, *args, **kw):
        '''display the config file name in the status text'''
        self.setStatus('config file: ' + self.rcfile_name)

    def doReadConfig(self):
        '''read the configuration file'''
        self.setStatus('read the config file: ' + self.rcfile_name)
        return config.ConfigFile(self.rcfile_name)

    def doSaveConfig(self):
        '''save the configuration file'''
        self.setStatus('write to the config file: ' + self.rcfile_name)
        self.rcfile.param['AY0'] = str(self.ui.w_AY0_user.text())
        self.rcfile.param['DY0'] = str(self.ui.w_DY0_user.text())
        self.rcfile.fromDataModel(self.table.model)

        self.rcfile.rc_write(self.rcfile_name)
    
    def doMove(self, motor, text_value, *args, **kw):
        '''move the motor'''
        # validate first
        motor = motor.lower()
        if motor not in MOTOR_SYMBOLS: return
        value, ok = text_value.toDouble()
        if not ok: return
        
        self.setStatus('moving ' + motor + ' motor to ' + str(value))
        self.motors[motor].move(value)

    def recalculate(self, Q, *args, **kw):
        '''recompute all terms'''
        self.setStatus('recalculating ...')
        
        # TODO: compute on update of user parameter (including EPICS PV monitor)
        # This code responds to qTable updates already
        
        try:   # get initial parameters from the GUI
            A_keV = 12.3984244 # Angstrom * keV
            ar = self.motors['ar'].pv.RBV
            ar0 = arEnc0 = float(self.ui.w_ARenc0.text())
            arEnc = float(self.ui.w_ARenc.text())
            sad = float(self.ui.w_SAD.text())
            sdd = float(self.ui.w_SDD.text())
            ay0 = float(self.ui.w_AY0_user.text())
            dy0 = float(self.ui.w_DY0_user.text())
            energy = float(self.ui.w_energy.text())
            lambda_over_4pi = A_keV / (energy * 4 * math.pi)
        except Exception, exc:
            self.setStatus('recalc exception 1: ' + str(exc))
            return None

        try:
            x = -Q * lambda_over_4pi
            ar = ar0 + 2*math.degrees(math.asin( x ))
            dy = dy0 + sdd * math.tan( x )
            ay = ay0 + sad * math.tan( x )
        except Exception, exc:
            self.setStatus('recalc exception 2: ' + str(exc))
            return None
        
        # TODO: indicate ar, ay, dy limit problems with a yellow button background

        self.setStatus('recalculated')
        return ar, ay, dy

    def setStatus(self, message):
        if hasattr(self, 'ui'):
            self.ui.statusBar().showMessage(str(message))


def main():
    app = QtGui.QApplication(sys.argv)
    view = USAXS_Q_tool(MAIN_UI_FILE)
    view.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
