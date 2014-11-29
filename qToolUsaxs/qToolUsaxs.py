
'''
qToolUsaxs: provides table of Q values to position AR, AY, and DY

It provides a table of known positions and buttons
to move each of the motors.
'''

import datetime
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


class USAXS_Q_tool(object):
    '''show the UI file'''

    def __init__(self, uifile, config_file = None):
        self.config_file = config_file or DEFAULT_CONFIG_FILE

        self.ui = uic.loadUi(uifile)
        self._replace_standard_controls_()
        self._init_epics_controls_()
        self._init_actions_()
        # TODO: read configuration file
        # TODO: connect EPICS PVs
    
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
        
        column = 1
        self.ar_rbv = bcdaqwidgets.BcdaQLabel()
        layout.addWidget(self.ar_rbv, 1, column)
        self.ar_val = bcdaqwidgets.BcdaQLineEdit()
        layout.addWidget(self.ar_val, 2, column)
        
        column = 2
        self.ay_rbv = bcdaqwidgets.BcdaQLabel()
        layout.addWidget(self.ay_rbv, 1, column)
        self.ay_val = bcdaqwidgets.BcdaQLineEdit()
        layout.addWidget(self.ay_val, 2, column)
        
        column = 3
        self.dy_rbv = bcdaqwidgets.BcdaQLabel()
        layout.addWidget(self.dy_rbv, 1, column)
        self.dy_val = bcdaqwidgets.BcdaQLineEdit()
        layout.addWidget(self.dy_val, 2, column)
    
    def _replace_standard_controls_(self):
        '''replace standard controls with EPICS controls'''
        self._replace_tableview_()
        # TODO: replace ARenc label
        # TODO: replace ARenc0 label
        # TODO: replace SAD label
        # TODO: replace SDD label
        # TODO: replace energy label

    def _replace_tableview_(self):
        '''install custom model-view support for Q table'''
        self.ui.tableView.deleteLater()
        gb = self.ui.groupBox_tableView
        layout = gb.layout()
        layout.setColumnStretch(0, 1)
        self.table = qTable.TableModel(None, parent=gb)
        self.tableview = qTable.TableView(gb)
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
        # TODO: implement
    
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
