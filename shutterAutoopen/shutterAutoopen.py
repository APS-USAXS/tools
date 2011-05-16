'''
########### SVN repository information ###################
# $Date$
# $Author$
# $Revision$
# $URL$
# $Id$
########### SVN repository information ###################

@author: Peter Beaucage
@contact: pbeaucage@aps.anl.gov
@organization: Advanced Photon Source, Argonne National Laboratory
@license: shutterAutoopen is part of USAXS_tools; See LICENSE (included with this file) for full details.
@version: $Id$
@summary: when hutch is not beam active, push "open shutter" button PV until it is beam active
@requires: CaChannel (for EPICS, called from pvConnect)
@requires: pvConnect (for EPICS)
@status: converted from the Tcl code
'''


import sys
import time
from CaChannel import *


if __name__ == '__main__':
        pvList = []     # list of successful PV connections
        errorList = []  # list of failed PV connections
        try:
                # in case the EPICS PV connection were to fail ...
		ashutterctrl = CaChannel()
		bshutterctrl = CaChannel()
		ashutterrdbk = CaChannel()
		bshutterrdbk = CaChannel()
		beamready = CaChannel()
		beamactive = CaChannel()
		dstationsearched = CaChannel()
	        beamready.searchw("PA:15ID:D_BEAM_READY.VAL")
	        print "Connected to BR PV"
		beamactive.searchw("PA:15ID:D_BEAM_ACTIVE.VAL")
	        print "Connected to BA PV"
		ashutterrdbk.searchw("PA:15ID:A_SHTRS_CLOSED.VAL")
		bshutterrdbk.searchw("PA:15ID:B_SHTRS_CLOSED.VAL")
		print "Connected to shutter rdbk"
		ashutterctrl.searchw("15IDA:shutter_in1.VAL")
		bshutterctrl.searchw("15IDA:shutter_in2.VAL")
		print "Connected to shutter ctrl"
		dstationsearched.searchw("PA:15ID:D_SEARCHED.VAL")
		print "Connected to SS PV"
        except:
                print "Problems connecting."
                print "Cannot continue.  Please correct problems and restart shutterAutoopen.\n"
                exit(1)
        while True:
	    if beamready.getw() and not beamactive.getw():
                print "Lost beam!"
		if ashutterrdbk.getw():
			print "Lost beam after A"
			ashutterctrl.putw(0)
                	time.sleep(5)
                	ashutterctrl.putw(1)
		if bshutterrdbk.getw():
			print "Lost beam after B"
			bshutterctrl.putw(0)
			print("Door opening...waiting 20s...")
			time.sleep(20)
			while not dstationsearched.getw():
				#print("Waiting for D station to be searched...")
				time.sleep(0.5)
			bshutterctrl.putw(1)
			print("Opened B shutter")
		time.sleep(10) #prevent feedback loops
            time.sleep(1)
        pvConnect.on_exit()
