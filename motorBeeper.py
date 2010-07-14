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
@license: scanTimeCalc is part of USAXS_tools; See LICENSE (included with this file) for full details.
@version: $Id$
@summary: .sound a beep when all motors have stopped moving
@requires: CaChannel (for EPICS, called from pvConnect)
@requires: pvConnect (for EPICS)
@status: converted from the Tcl code
'''


import pvConnect
import sys


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
        print "\a",
	sys.stdout.flush()


if __name__ == '__main__':
    if len(sys.argv) > 1:
	db = {}
	pvList = sys.argv[1:]
	for pv in pvList:
	    ch = pvConnect.EpicsPv(pv)
 	    ch.connectw()
 	    ch.SetUserCallback(monitor)
 	    ch.SetUserArgs(pv)
 	    ch.monitor()
	    db[pv] = {'ch' : ch, 'last' : 0, 'current' : 0}
 	ch.chan.pend_event()
 	import time
	while True:
 	    time.sleep(0.2)
 	    ch.chan.pend_event()
	for pv in pvList:
	    ch = db[pv]['ch']
	    time.sleep(1)
	    ch.release()
 	pvConnect.on_exit()
