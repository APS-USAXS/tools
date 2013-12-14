#!/usr/bin/env python

'''reduce the fly scan data from the 2013-12-09 tests'''

# export EPD=/APSshare-ro/epd/rh6-x86_64/bin/python
# alias EPD '/APSshare-ro/epd/rh6-x86_64/bin/python '

data_files = '''
   Adam_120_1386638883.h5
   Adam_20_1386638251.h5
   Adam_30_1386638085.h5
   Adam_45_1386637699.h5
   Adam_60_1386638485.h5
   Blank_120_1386638732.h5
   Blank_20_1386638201.h5
   Blank_30_1386638026.h5
   Blank_45_1386637624.h5
   Blank_60_1386638396.h5
   PS_120_1386639035.h5
   PS_20_1386638301.h5
   PS_30_1386638146.h5
   PS_45_1386637773.h5
   PS_60_1386638575.h5
'''.split()
#  StruckSaveData_1386637624.dat
#  StruckSaveData_1386637699.dat
#  StruckSaveData_1386637773.dat
#  StruckSaveData_1386638025.dat
#  StruckSaveData_1386638085.dat
#  StruckSaveData_1386638145.dat
#  StruckSaveData_1386638201.dat
#  StruckSaveData_1386638250.dat
#  StruckSaveData_1386638300.dat
#  StruckSaveData_1386638396.dat
#  StruckSaveData_1386638484.dat
#  StruckSaveData_1386638575.dat
#  StruckSaveData_1386638732.dat
#  StruckSaveData_1386638883.dat
#  StruckSaveData_1386639035.dat


import os
import sys
import numpy
import h5py
import eznx


def get_data(dataset, astype=None):
    '''get the numpy data from the HDF5 dataset, option to return as different numpy data type'''
    dtype = dataset.dtype
    if astype is not None:
        dtype = astype
    if len(dataset.shape) > 1:
        raise RuntimeError, "unexpected %d-D data" % len(dataset.shape)
    if dataset.size > 1:
        return dataset[...].astype(dtype)   # as array
    else:
        return dataset[0].astype(dtype)     # as scalar


class UsaxsFlyScanData(object):
    '''contains data from one HDF5 file of fly scan raw data'''

    range_adjustment_constant = 500     # why this number?
    pulse_frequency = 50e6              # 50 MHz
    
    def __init__(self, hdf_filename):
        self.hdf_filename = hdf_filename
        if not os.path.exists(hdf_filename):
            raise RuntimeError, 'file not found: ' + hdf_filename
        
        self.hdf = h5py.File(hdf_filename, "r")
        self.read_raw_data()
        self.compute_ar()
        self.basic_reduction()
        #self.hdf.close()        # let the caller close the file
        
    def read_raw_data(self):
        nxdata = self.hdf['/entry/flyScan']
        self.raw_clock_pulses = get_data(nxdata['mca1'])
        self.raw_I0 = get_data(nxdata['mca2'])
        self.raw_upd = get_data(nxdata['mca3'])
        self.raw_ranges = get_data(nxdata['mca4'])

        self.num_points = get_data(nxdata['AR_pulses'])
        
    def compute_ar(self):
        '''compute the AR array from available information'''
        nxdata = self.hdf['/entry/flyScan']
        ar_start = get_data(nxdata['AR_start'])
        ar_step = get_data(nxdata['AR_increment'])
        last = ar_start - (self.num_points - 1) * ar_step
        
        # let Numpy create the ar array
        self.ar = numpy.linspace(ar_start, last, self.num_points)
        
    def basic_reduction(self):
        '''straight USAXS data reduction to R(ar), no rebinning now'''
        # FIXME: here are some tools
        #   list_of_zero_indices = numpy.where(self.raw_clock_pulses == 0)
        #   set_nonpositive_to_nan = np.select([X > 0], [X], default=np.nan)
        #   http://stackoverflow.com/questions/5927180/removing-data-from-a-numpy-array
        
        # TODO: suggest creating a mask array
        #  mask any channels with zero clock pulses
        #  mask any channels within specified time of a range change (0.2 s before to 0.1 after, perhaps)
        #  the masking time could be range-change dependent (or learned from reqrange v. lurange or ...)
        #  remove all masked points
        
        # TODO: work out a rebinning strategy
        
#         if self.raw_clock_pulses.min() == 0:    # trap and avoid divide-by-zero errors in Numpy
#             # TODO: learn how to continue processing past step this in numpy
#             raise ArithmeticError, "zero pulse values found"

        numpy_error_reporting = numpy.geterr()
        numpy.seterr(divide='ignore', invalid='ignore')     # suppress messages
        ranges = numpy.divide(self.range_adjustment_constant * self.raw_ranges, self.raw_clock_pulses)
        self.ranges = ranges.astype(int)
        self.time = self.raw_clock_pulses / self.pulse_frequency

        # get the table of amplifier gains and measured backgrounds
        meta = self.hdf['/entry/metadata']
        gains_db = [get_data(meta['upd_gain' + str(_)]) for _ in range(5)]
        bkg_db = [get_data(meta['upd_bkg' + str(_)]) for _ in range(5)]

        self.gain = numpy.zeros((self.num_points,), numpy.float32)
        self.bkg = self.raw_clock_pulses / self.pulse_frequency      # divide by 50 MHz frequency
        for i in range(self.num_points):
            self.gain[i] = gains_db[ self.ranges[i] ]
            self.bkg[i] *= bkg_db[ self.ranges[i] ]

        self.ratio = numpy.ma.masked_less_equal( (self.raw_upd - self.bkg) / self.raw_I0 / self.gain, 0)
        numpy.seterr(**numpy_error_reporting)

    def close_hdf_file(self):
        '''close the HDF5 data file'''
        if self.hdf is not None:
            self.hdf.close()
            self.hdf = None

    def save_results(self, nxdata):
        '''save computed results to an HDF5 file (nxdata) group'''
        eznx.makeDataset(nxdata, 'ar', self.ar)
        eznx.makeDataset(nxdata, 'ranges', self.ranges)
        eznx.makeDataset(nxdata, 'bkg', self.bkg)
        eznx.makeDataset(nxdata, 'ratio', self.ratio, signal=1, axes='ar')
        eznx.makeDataset(nxdata, 'time', self.time)
        eznx.makeDataset(nxdata, 'gain', self.gain)
        eznx.makeDataset(nxdata, 'raw_upd', self.raw_upd)
        eznx.makeDataset(nxdata, 'raw_I0', self.raw_I0)
        eznx.makeDataset(nxdata, 'raw_clock_pulses', self.raw_clock_pulses)

        wavelength = get_data(self.hdf['/entry/instrument/monochromator/DCM_wavelength'])
        eznx.makeDataset(nxdata, 'wavelength', [wavelength], units='A')

        energy = get_data(self.hdf['/entry/instrument/monochromator/DCM_energy'])
        eznx.makeDataset(nxdata, 'energy', [energy], units='keV')

        sdd = get_data(self.hdf['/entry/metadata/detector_distance'])
        eznx.makeDataset(nxdata, 'SDD', [sdd], units='mm')


def main():
    '''
    First, find the directory that exists on our computer.
    Since we develop and process on several computers, the data might
    exist on different file paths depending on the system.
    
    Next, try to load and process from all HDF5 files.  Leave the files open
    so the datasets remain accessible through the next step.  For now,
    no data rebinning is done.
    
    Once we have a list of fly scans that could be processed,
    create an HDF5/NeXus file for output of all results.

    Need to learn how to process the data when the pulse count for
    some channels is zero.  Learn how to avoid divide-by-zero errors
    in Numpy.  This will allow us to see the results from 20s fly scans.

    Place result for each fly scan in its own NXdata group under a
    single NXentry group.  (Could go in separate NXentry groups, 
    this is a simple matter to change.)
    
    After each fly scan is save to the output HDF5 file, close
    its HDF raw data file.
    
    Close the output HDF5 file.
    '''
    db = {}
    for filename in data_files:
#         try:
            hdf = UsaxsFlyScanData(filename)
            key = os.path.splitext(filename)[0]
            db[key] = hdf
#         except:
#             print 'error converting: ' + filename
    if len(db) > 0:
        out = eznx.makeFile('2013-12-09-reduced.h5')
        entry = eznx.makeGroup(out, 'fly_2013_12_09', 'NXentry')
        for key, hdf in sorted(db.items()):
            data = eznx.makeGroup(entry, key, 'NXdata')
            hdf.save_results(data)
            hdf.close_hdf_file()
        out.close()


if __name__ == '__main__':
    # different development directories
    dir_list = [
                r'/data/USAXS_data/struckData',
                r'C:\Users\Pete\Desktop\2013-12-09 USAXS fly scan data',
                r'/home/oxygen/JEMIAN/Documents/2013-12-09 USAXS fly scan data',
                ]
    for path in dir_list:
        if os.path.exists(path):
            os.chdir(path)
            main()
            break


########### SVN repository information ###################
# $Date$
# $Author$
# $Revision$
# $URL$
# $Id$
########### SVN repository information ###################
