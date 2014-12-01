#!/usr/bin/env python

'''
scanTimeCalc: estimates the time to complete a series of scans
'''

import datetime
import os
import sys
from PyQt4 import QtGui, uic

import bcdaqwidgets

__project_name__  = 'scanTimeCalc'
__version__       = '2014-11'
__author__        = 'Pete Jemian'
__contact__       = 'jemian@anl.gov'
__organization__  = 'Advanced Photon Source, Argonne National Laboratory'
__copyright__     = 'Copyright (C) 2009-2014, UChicago Argonne, LLC, All Rights Reserved'
__license__       = 'scanTimeCalc is part of USAXS_tools; See LICENSE (included with this file) for full details.'
__url__           = 'http://usaxs.xray.aps.anl.gov/livedata'

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
MAIN_UI_FILE = os.path.join(THIS_DIR, 'scanTimeCalc.ui')
ABOUT_UI_FILE = os.path.join(THIS_DIR, 'about.ui')
LOGO_FILE = os.path.join(THIS_DIR, 'epicslogo101.gif')
USER_HOME_DIR = os.getenv('USERPROFILE') or os.getenv('HOME') # windows or Linux/Mac
DEFAULT_CONFIG_FILE = os.path.join(USER_HOME_DIR, '.scanTimeCalcrc')


class Calculator(object):
    '''show the UI file'''

    def __init__(self, uifile, config_file = None):
        self.config_file = config_file or DEFAULT_CONFIG_FILE

        self.ui = uic.loadUi(uifile)

    def show(self):
        '''convenience method, hides .ui file implementation'''
        self.ui.show()

    def doClose(self, *args, **kw):
        self.setStatus('application exit requested')
        self.ui.close()

    def setStatus(self, message):
        # ts = str(datetime.datetime.now())
        self.ui.statusBar().showMessage(str(message))


def main():
    app = QtGui.QApplication(sys.argv)
    view = Calculator(MAIN_UI_FILE)
    view.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
