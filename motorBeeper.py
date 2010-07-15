'''
########### SVN repository information ###################
# $Date$
# $Author$
# $Revision$
# $URL$
# $Id$
########### SVN repository information ###################

@author: Pete Jemian
@contact: jemian@anl.gov
@organization: Advanced Photon Source, Argonne National Laboratory
@license: motorBeeper is part of USAXS_tools; See LICENSE (included with this file) for full details.
@version: $Id$
@summary: .sound a beep when all motors have stopped moving
@requires: CaChannel (for EPICS, called from pvConnect)
@requires: pvConnect (for EPICS)
@status: converted from the Tcl code
'''


import pvConnect
import sys
import time


def monitor(epics_args, user_args):
    '''Example response to an EPICS monitor on the channel
       @param value: str(epics_args['pv_value'])'''
    global db
    value = epics_args['pv_value']
    pv = user_args[0]
    rec = db[pv]
    rec['last'] = rec['current']
    rec['current'] = value
    if (rec['current'] == 1) and (rec['last'] == 0):
        #print "\a",
        print chr(7) + chr(8),  # ASCII bell and backspace
        sys.stdout.flush()      # make sure it rings *now*


if __name__ == '__main__':
    if len(sys.argv) > 1:
        db = {}         # global data cache for EPICS data
        pvList = []     # list of successful PV connections
        errorList = []  # list of failed PV connections
        ch = None       # most recent PV connection (instance of pvConnect.EpicsPv)
        for pv in sys.argv[1:]:
            try:
                # in case the EPICS PV connection were to fail ...
                ch = pvConnect.EpicsPv(pv).MonitoredConnection(monitor)
                pvList.append(pv)
                db[pv] = {'ch' : ch, 'last' : 0, 'current' : 0}
            except:
                errorList.append(pv)
        if len(errorList) > 0:
            print "Problems connecting with these EPICS PVs: ", ", ".join(errorList)
            print "Cannot continue.  Please correct problems and restart motorBeeper.\n"
            exit(1)
        if not ch == None:
            print "ch == None: should not happen, cannot continue"
            exit(1)
        ch.chan.pend_event()
        while True:
            time.sleep(0.2)
            ch.chan.pend_event()
        for pv in pvList:
            ch = db[pv]['ch']
            time.sleep(1)
            ch.release()
        pvConnect.on_exit()
