#!/usr/bin/env python


'''save USAXS fly scan data to a NeXus file'''


import datetime
import os
import sys
import h5py
import numpy
import time
from lxml import etree as lxml_etree

# matches IOC for big arrays
os.environ['EPICS_CA_MAX_ARRAY_BYTES'] = '1280000'    # was 200000000 

import epics		# PyEpics support
import eznx		# NeXus r/w support using h5py


XML_CONFIGURATION_FILE = 'saveFlyData.xml'
XSD_SCHEMA_FILE = 'saveFlyData.xsd'


# TODO: refactor to identify parents and children
dir_registry = {}
class NX_structure(object):
    
    def __init__(self, parent_path, xml_element_node):
        self.xml_node = xml_element_node
        self.hdf5_group = None
        self.name = xml_element_node.attrib['name']
        self.nx_class = xml_element_node.attrib['class']
        #node = xml_element_node.getparent()
        if self.name != '/' and not parent_path.endswith('/'):
            parent_path += '/'
        self.hdf5_path = parent_path + self.name


# TODO: refactor to identify parents
pv_registry = {}
class PV_specification(object):
    
    def __init__(self, xml_element_node):
        self.hdf5_path = None
        self.xml_node = xml_element_node
        self.label = xml_element_node.attrib['label']
        self.pvname = xml_element_node.attrib['pvname']
        self.pv = epics.PV(self.pvname)
        self.attrib = {}
        for node in xml_element_node.xpath('attribute'):
            self.attrib[node.attrib['name']] = node.attrib['value']
    
    def parentDir(self):
        # TODO: implement
        raise NotImplementedError


class SaveFlyScan(object):
    '''watch USAXS fly scan, save data to NeXus file after scan is done'''
    trigger_pv = '15iddLAX:USAXSfly:Start'
    trigger_accepted_values = (0, 'Done')
    trigger_poll_interval_s = 0.1
    creator_version = 'unknown'
    
    def __init__(self, hdf5_file, config_file = None):
        self.hdf5_file_name = hdf5_file
        path = self._get_support_code_dir()
        self.config_file = config_file or os.path.join(path, XML_CONFIGURATION_FILE)
        self._read_configuration()

        self._createFile()

    def waitForData(self):
        '''wait until the data is ready, then save it'''
        trigger = epics.PV(self.trigger_pv)
        # TODO: convert this polling loop to a PV monitor callback
        while trigger.get() not in self.trigger_accepted_values:
            time.sleep(self.trigger_poll_interval_s)
        self.saveFile()

    def saveFile(self):
        '''write all desired data to the file and exit this code'''
        t = datetime.datetime.now()
        timestamp = ' '.join((t.strftime("%Y-%m-%d"), t.strftime("%H:%M:%S")))
        eznx.addAttributes(self.structure['/'].hdf5_group, timestamp = timestamp)

        for key, spec in self.pvdb.items():
            #print key, spec
            hdf5_parent = self._get_hdf5_parent_object(spec.xml_node)
            value = spec.pv.get()
            if not isinstance(value, numpy.ndarray):
                value = [value]
            #print pv.pvname, type(value)
            #print key, pv, value, type(value)
            ds = eznx.makeDataset(hdf5_parent, spec.label, value)
            self._attachEpicsAttributes(ds, spec.pv)
            eznx.addAttributes(ds, **spec.attrib)
        
        self.structure['/'].hdf5_group.close()    # be CERTAIN to close the file
    
    def _read_configuration(self):
        # first, validate configuration file against an XML Schema
        path = self._get_support_code_dir()
        xml_schema_file = os.path.join(path, XSD_SCHEMA_FILE)
        xmlschema_doc = lxml_etree.parse(xml_schema_file)
        xmlschema = lxml_etree.XMLSchema(xmlschema_doc)

        config = lxml_etree.parse(self.config_file)
        if not xmlschema.validate(config):
            # XML file is not valid, let lxml report what is wrong as an exception
            #log = xmlschema.error_log    # access more details
            xmlschema.assertValid(config)   # basic exception report

        # safe to proceed parsing the file
        root = config.getroot()
        if root.tag != "saveFlyData":
            raise RuntimeError, "XML file not valid for configuring saveFlyData"
        
        self.creator_version = root.attrib['version']
        
        node = root.xpath('/saveFlyData/triggerPV')[0]
        self.trigger_pv = node.attrib['pvname']
        acceptable_values = (int(node.attrib['done_value']), node.attrib['done_text'])
        self.trigger_accepted_values = acceptable_values
        
        # TODO: figure how to pull default value from XML Schema
        default_value = self.trigger_poll_interval_s
        self.trigger_poll_interval_s = node.get('poll_time_s', default_value)
        
        nx_structure = root.xpath('/saveFlyData/NX_structure')[0]
        self.structure = {}
        for node in nx_structure.xpath('//dir'):
            parent = node.getparent()
            if parent.tag == 'NX_structure':
                hdf5_path = ''
            else:
                hdf5_path = self._get_parent_path(node)
            xture = NX_structure(hdf5_path, node)
            self.structure[xture.hdf5_path] = xture
        
        self.pvdb = {}
        for node in root.xpath('//PV'):
            spec = PV_specification(node)
            spec.hdf5_path = self._get_parent_path(node)
            self.pvdb[spec.label] = spec
    
    def _get_parent_path(self, xml_node):
        parent = xml_node.getparent()
        hdf5_path = None
        for s in self.structure.values():
            if s.xml_node == parent:
                hdf5_path = s.hdf5_path
                break
        return hdf5_path
    
    def _get_hdf5_parent_object(self, xml_node):
        return self.structure[self._get_parent_path(xml_node)].hdf5_group
    
    def _get_support_code_dir(self):
        return os.path.split(os.path.abspath(__file__))[0]
  
    def _createFile(self):
        '''create the HDF5 file and structure'''
        for key, xture in sorted(self.structure.items()):
            if key == '/':
                # create the file and internal structure
                f = eznx.makeFile(self.hdf5_file_name,
                  # the following are attributes to the root element of the HDF5 file
                  file_name = self.hdf5_file_name,
                  instrument = "APS USAXS at 15ID-D",
                  scan_mode = 'USAXS fly scan',
                  creator = '$Id$',
                  creator_version = self.creator_version,
                  HDF5_Version = h5py.version.hdf5_version,
                  h5py_version = h5py.version.version,
                )
                xture.hdf5_group = f
            else:
                hdf5_parent = self._get_hdf5_parent_object(xture.xml_node)
                xture.hdf5_group = eznx.makeGroup(hdf5_parent, xture.name, xture.nx_class)

    def _attachEpicsAttributes(self, node, pv):
        '''attach common attributes from EPICS to the HDF5 tree node'''
        eznx.addAttributes(node, 
          epics_pv = pv.pvname,
          units = pv.units or '',
          epics_type = pv.type,
          epics_description = epics.caget(pv.pvname+'.DESC'),
        )


def main():
    if len(sys.argv) != 3:
        msg = 'usage: saveFlyData.py /hdf5/file/to/save /path/to/xml/config/file.xml'
        raise RuntimeError, msg
    
    dataFile = sys.argv[1]
    if not os.path.exists(os.path.split(dataFile)[0]):
        msg = 'directory for that file does not exist: ' + dataFile
        raise RuntimeError, msg
    
    if os.path.exists(dataFile):
        msg = 'file exists: ' + dataFile
        raise RuntimeError, msg

    configFile = sys.argv[2]
    if not os.path.exists(configFile):
        msg = 'config file not found: ' + configFile
        raise RuntimeError, msg
    
    sfs = SaveFlyScan(dataFile, configFile)
    sfs.waitForData()
    print 'wrote file: ' + dataFile


if __name__ == '__main__':
    if os.environ.get('HOST', '') == 'usaxscontrols2.cars.aps.anl.gov':
        # production system
        main()
    else:
        # code development
        sfs = SaveFlyScan('/tmp/test.h5', XML_CONFIGURATION_FILE)
        sfs.waitForData()


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
EPD ./saveFlyData.py /tmp/test.h5 ./saveFlyData.xml
EPD ~/bin/h5toText.py /tmp/test.h5
'''
