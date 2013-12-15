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
import math
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
        self.compute_Q_and_R()
        self.rebin()
        #self.hdf.close()        # let the caller close the file
        
    def __str__(self):
        return self.hdf_filename
        
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
        
    def compute_Q_and_R(self, centroid = None):
        Qmin = 1e-6
        numpy_error_reporting = numpy.geterr()
        numpy.seterr(invalid='ignore')     # suppress messages
        if centroid is not None:
            self.ar_centroid = centroid
        else:
            numerator = numpy.ma.masked_invalid(self.ratio*self.ar)
            denominator = numpy.ma.masked_array(data=self.ratio, mask=numerator.mask)
            self.ar_centroid = numpy.sum(numerator) / numpy.sum(denominator)    # equi-spaced in AR
        wavelength = get_data(self.hdf['/entry/instrument/monochromator/DCM_wavelength'])
        d2r = math.pi/180
        q = (4 * math.pi / wavelength) * numpy.sin(d2r*(self.ar_centroid - self.ar))
        self.Q = numpy.ma.masked_less_equal( q, Qmin)
        # FIXME: blend self.R.mask and self.Q.mask
        QR_mask = self.Q.mask + self.ratio.mask
        self.R = numpy.ma.masked_array(data=self.ratio, mask=QR_mask, copy=True)
        # FIXME: what about dR?
        numpy.seterr(**numpy_error_reporting)

    def compute_range_change_mask(self):
        '''
        mask any channels associated with a range change
        
        (0.2 s before to 0.1 after, perhaps)
        the masking time could be range-change dependent (or learned from reqrange v. lurange or ...)
        '''
        # 1. determine channels with range change
        # 2. compute mask
        # 3. return the mask
        time_before = 0.2       # for starters, independent of range or range-change
        time_after = 0.3        # these values chosen by looking at 2013-12-09 data
        abs_time = numpy.cumsum(self.time)

        # Determine range changes by difference method
        # Changes occur when self.ranges[i] != shifted[i]
        old_range = numpy.insert(self.ranges, 0, -1)
        new_range = numpy.append(self.ranges, -2)
        lu_range_change_channels = numpy.nonzero(new_range - old_range)[0][1:-1]

        data_ok = numpy.ma.make_mask(self.ranges + 1) # initial mask all true
        size = abs_time.size
        for channel in lu_range_change_channels:
            data_ok[channel] = False
            t0 = abs_time[channel]
            t1 = t0 - time_before
            t2 = t0 + time_after
            
            # mask some channels just before the range change
            ch_1 = channel - 1
            while ch_1 > 0:
                if not data_ok[ch_1]:
                    break       # previously masked, no need to continue
                data_ok[ch_1] = False
                if abs_time[ch_1] < t1:
                    break       # end of masking range
                ch_1 -= 1
            
            # mask some channels just after the range change
            ch_n = channel + 1
            while ch_n < size:
                if not data_ok[ch_n]:
                    break       # previously masked, no need to continue
                data_ok[ch_n] = False
                if abs_time[ch_n] > t2:
                    break       # end of masking range
                ch_n += 1
        
        return data_ok
        
    def basic_reduction(self):
        '''straight USAXS data reduction to R(ar), no rebinning now'''
        numpy_error_reporting = numpy.geterr()
        numpy.seterr(divide='ignore', invalid='ignore')     # suppress messages
        ranges = numpy.divide(self.range_adjustment_constant * self.raw_ranges, self.raw_clock_pulses)
        self.ranges = ranges.astype(int)
        self.time = self.raw_clock_pulses / self.pulse_frequency
        
        self.range_change_mask = self.compute_range_change_mask()

        # get the table of amplifier gains and measured backgrounds
        meta = self.hdf['/entry/metadata']
        gains_db = [get_data(meta['upd_gain' + str(_)]) for _ in range(5)]
        bkg_db = [get_data(meta['upd_bkg' + str(_)]) for _ in range(5)]

        self.gain = numpy.zeros((self.num_points,), numpy.float32)
        self.bkg = self.raw_clock_pulses / self.pulse_frequency      # divide by 50 MHz frequency
        for i in range(self.num_points):
            self.gain[i] = gains_db[ self.ranges[i] ]
            self.bkg[i] *= bkg_db[ self.ranges[i] ]

        ratio = (self.raw_upd - self.bkg) / self.raw_I0 / self.gain
        # TODO: need error propagation
        self.ratio_unmasked = numpy.ma.masked_less_equal(ratio, 0)
        # FIXME: range change mask not propagating through to self.R
        self.ratio = self.ratio_unmasked * self.range_change_mask
        numpy.seterr(**numpy_error_reporting)

    def rebin(self, Qmin=1e-5, Qmax=1, number_bins = 2000):
        # basic rebinning strategy
        numpy_error_reporting = numpy.geterr()
        numpy.seterr(invalid='ignore')

        Qmin = max(Qmin, numpy.min(self.Q))
        Qmax = min(Qmax, numpy.max(self.Q))
        Q = numpy.exp(numpy.linspace(math.log(Qmin), math.log(Qmax), number_bins))
        R = numpy.zeros((number_bins), dtype='float')
        count = numpy.zeros((number_bins), dtype='int')

        indices = numpy.digitize(self.Q, Q)
        for i, ch in enumerate(indices):
            if not self.R.mask[i] and self.R[i] != numpy.nan and 0 < ch < number_bins:
                R[ch] += self.R[i]
                count[ch] += 1
        R = numpy.ma.masked_invalid(R / count)
        # TODO: error propagation
        
        Q_bin = []
        R_bin = []
        masked = R.mask
        for i, value in enumerate(R):
            # test if value is valid
            if not masked[i] and value != numpy.nan and value > 0:
                Q_bin.append(Q[i])
                R_bin.append(value)
        self.Q_binned = numpy.array(Q_bin)
        self.R_binned = numpy.array(R_bin)
        
        numpy.seterr(**numpy_error_reporting)

    def close_hdf_file(self):
        '''close the HDF5 data file'''
        if self.hdf is not None:
            self.hdf.close()
            self.hdf = None

    def save_results(self, nxdata):
        '''save computed results to an HDF5 file (nxdata) group'''
        eznx.makeDataset(nxdata, 'Q', self.Q, units='1/A')
        eznx.makeDataset(nxdata, 'R', self.R, units='a.u.',      signal=1, axes='Q')

        eznx.makeDataset(nxdata, 'Q_binned', self.Q_binned, units='1/A')
        eznx.makeDataset(nxdata, 'R_binned', self.R_binned, units='a.u.',      signal=1, axes='Q')
        
        eznx.makeDataset(nxdata, 'ar', self.ar, units='degrees')
        eznx.makeDataset(nxdata, 'ranges', self.ranges)
        eznx.makeDataset(nxdata, 'bkg', self.bkg, units='counts/s')
        eznx.makeDataset(nxdata, 'ratio', self.ratio, units='a.u.')
        eznx.makeDataset(nxdata, 'ratio_unmasked', self.ratio_unmasked, units='a.u.')
        eznx.makeDataset(nxdata, 'time', self.time, units='s')
        eznx.makeDataset(nxdata, 'gain', self.gain, units='V/A')
        eznx.makeDataset(nxdata, 'raw_upd', self.raw_upd, units='counts')
        eznx.makeDataset(nxdata, 'raw_I0', self.raw_I0, units='counts')
        eznx.makeDataset(nxdata, 'raw_clock_pulses', self.raw_clock_pulses, units='counts')
        eznx.makeDataset(nxdata, 'range_change_mask', self.range_change_mask, units='counts')

        wavelength = get_data(self.hdf['/entry/instrument/monochromator/DCM_wavelength'])
        eznx.makeDataset(nxdata, 'wavelength', [wavelength], units='A')

        energy = get_data(self.hdf['/entry/instrument/monochromator/DCM_energy'])
        eznx.makeDataset(nxdata, 'energy', [energy], units='keV')

        sdd = get_data(self.hdf['/entry/metadata/detector_distance'])
        eznx.makeDataset(nxdata, 'SDD', [sdd], units='mm')
        eznx.makeDataset(nxdata, 'ar_centroid', [self.ar_centroid], units='degrees')

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
