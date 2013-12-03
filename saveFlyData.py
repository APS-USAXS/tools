#!/usr/bin/env python


'''save USAXS fly scan data to a NeXus file'''


import datetime
import os
import sys
import h5py

# matches IOC for big arrays
os.environ['EPICS_CA_MAX_ARRAY_BYTES'] = '200000000'

import epics		# PyEpics support
import eznx		# NeXus r/w support using h5py


mca_pv_list = "15iddLAX:3820:mca1 15iddLAX:3820:mca2 15iddLAX:3820:mca3 15iddLAX:3820:mca4".split()


class SaveFlyScan(object):
  '''watch USAXS fly scan, save data to NeXus file after scan is done'''

  def __init__(self, hdf5_file):
    self.hdf5_file = hdf5_file
    self.mca = [epics.PV(pv) for pv in mca_pv_list]
    self.saveFile()	# development version

  def saveFile(self):
    t = datetime.datetime.now()
    timestamp = ' '.join((t.strftime("%Y-%m-%d"), t.strftime("%H:%M:%S")))

    # create the file and internal structure
    f = eznx.makeFile(self.hdf5_file,
      file_name = self.hdf5_file,
      timestamp = timestamp,
      instrument = "APS USAXS at 15ID-C",
      creator = '$Id$',
      HDF5_Version = h5py.version.hdf5_version,
      h5py_version = h5py.version.version,
    )
    nxentry = eznx.makeGroup(f, 'entry', 'NXentry')
    nxdata = eznx.makeGroup(nxentry, 'data', 'NXdata')
    nxcollection = eznx.makeGroup(nxdata, 'metadata', 'NXcollection')
    
    # save any metadata

    # save the MCA data
    index = 0
    for mca in self.mca:
      index += 1		# 1-based indexing
      label = 'mca' + str(index)
      ds = eznx.makeDataset(nxdata, label, mca.get(), 
        epics_pv = mca.pvname,
	epics_units = mca.units,
        epics_nelm = mca.nelm,
	epics_description = epics.caget(mca.pvname+'.DESC'),
      )
      if index == 1:
        eznx.addAttributes(ds, {'signal': 1})
	# units='counts', signal=1, axes='two_theta'

    f.close()	# be CERTAIN to close the file


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
