#!/usr/bin/env python


'''save USAXS fly scan data to a NeXus file'''


import datetime
import os
import sys
import h5py
import numpy
import time

# matches IOC for big arrays
os.environ['EPICS_CA_MAX_ARRAY_BYTES'] = '1280000'    # was 200000000 

import epics		# PyEpics support
import eznx		# NeXus r/w support using h5py


mca_pv_list = '''
  15iddLAX:3820:mca1
  15iddLAX:3820:mca2 
  15iddLAX:3820:mca3 
  15iddLAX:3820:mca4'''.split()

metadata_dict = {
  'SR_current'  : 'S:SRcurrentAI',
  'ID_E'        : 'ID15:Energy',
  #'DCM_energy'  : '????',
  'string1'     : '15iddLAX:string1',
  'string19'    : '15iddLAX:string19',
  'string20'    : '15iddLAX:string20',
  'float1'      : '15iddLAX:float1',
  'float19'     : '15iddLAX:float19',
  'float20'     : '15iddLAX:float20',
}

TRIGGER_POLL_INTERVAL_S = 0.1
trigger_pv = '15iddLAX:bit2'
ACCEPTABLE_COMPLETION_VALUES = (0, 'Done')


class SaveFlyScan(object):
    '''watch USAXS fly scan, save data to NeXus file after scan is done'''
    
    def __init__(self, hdf5_file):
        self.hdf5_file_name = hdf5_file
        self.structure = {}
        self.mca = [epics.PV(pv) for pv in mca_pv_list]
        self.metadata = {}
        for key, value in metadata_dict.items():
            self.metadata[key] = epics.PV(value)
        self._createFile()

    def waitForData(self):
        '''wait until the data is ready, then save it'''
        trigger = epics.PV(trigger_pv)
        while trigger.get() not in ACCEPTABLE_COMPLETION_VALUES:
            time.sleep(TRIGGER_POLL_INTERVAL_S)
        self.saveFile()

    def saveFile(self):
        '''write all desired data to the file and exit this code'''
        t = datetime.datetime.now()
        timestamp = ' '.join((t.strftime("%Y-%m-%d"), t.strftime("%H:%M:%S")))
        eznx.addAttributes(self.structure['/'], timestamp = timestamp)
        
        self._save_maindata(self.structure['/entry/data'])
        self._save_metadata(self.structure['/entry/data/metadata'])
        
        self.structure['/'].close()    # be CERTAIN to close the file
  
    def _createFile(self):
        '''create the HDF5 file and structure'''
        # create the file and internal structure
        f = eznx.makeFile(self.hdf5_file_name,
          # the following are attributes to the root element of the HDF5 file
          file_name = self.hdf5_file_name,
          instrument = "APS USAXS at 15ID-D",
          scan_mode = 'USAXS fly scan',
          creator = '$Id$',
          HDF5_Version = h5py.version.hdf5_version,
          h5py_version = h5py.version.version,
        )
        self.structure['/'] = f
        self.structure['/entry'] = eznx.makeGroup(f, 'entry', 'NXentry')
        self.structure['/entry/data'] = eznx.makeGroup(self.structure['/entry'], 'data', 'NXdata')
        self.structure['/entry/data/metadata'] = eznx.makeGroup(self.structure['/entry/data'], 'metadata', 'NXcollection')

    def _attachEpicsAttributes(self, node, pv):
        '''attach common attributes from EPICS to the HDF5 tree node'''
        eznx.addAttributes(node, 
          epics_pv = pv.pvname,
          units = pv.units or '',
          epics_type = pv.type,
          epics_description = epics.caget(pv.pvname+'.DESC'),
        )
    
    def _save_maindata(self, group):
        # save the MCA data
        index = 0
        for mca in self.mca:
            index += 1        # 1-based indexing
            label = 'mca' + str(index)
            value = mca.get()
            #print mca.pvname, type(value)
            ds = eznx.makeDataset(group, label, value, epics_nelm = mca.nelm)
            self._attachEpicsAttributes(ds, mca)
            if index == 1:
                # NeXus requires that one (& only 1) dataset have this attribute
                eznx.addAttributes(ds, signal=1)
                # units='counts', signal=1, axes='two_theta'

    def _save_metadata(self, group):
        # save any metadata
        for key, pv in self.metadata.items():
            #cv = pv.get_ctrlvars()
            value = pv.get()
            if not isinstance(value, numpy.ndarray):
                value = [value]
            #print pv.pvname, type(value)
            #print key, pv, value, type(value)
            ds = eznx.makeDataset(group, key, value)
            self._attachEpicsAttributes(ds, pv)


def main():
    if len(sys.argv) != 2:
        msg = 'usage: saveFlyData.py /hdf5/file/to/save'
        raise RuntimeError, msg
    
    dataFile = sys.argv[1]
    if not os.path.exists(os.path.split(dataFile)[0]):
        msg = 'directory for that file does not exist: ' + dataFile
        raise RuntimeError, msg
    
    if os.path.exists(dataFile):
        msg = 'file exists: ' + dataFile
        raise RuntimeError, msg
    
    sfs = SaveFlyScan(dataFile)
    sfs.waitForData()
    print 'wrote file: ' + dataFile


if __name__ == '__main__':
    main()


########### SVN repository information ###################
# $Date$
# $Author$
# $Revision$
# $URL$
# $Id$
########### SVN repository information ###################

'''
alias EPD '/APSshare/epd/rh6-x86_64/bin/python '
cd /home/beams/S15USAXS/Documents/eclipse/USAXS/tools
EPD ./saveFlyData.py /tmp/test.h5
EPD ~/bin/h5toText.py /tmp/test.h5
'''
