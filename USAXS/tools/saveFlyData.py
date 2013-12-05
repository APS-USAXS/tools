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


SVN_ID = '$Id$'
XML_CONFIGURATION_FILE = 'saveFlyData.xml'
XSD_SCHEMA_FILE = 'saveFlyData.xsd'

dir_registry = {}       # key: HDF5 absolute path, value: Dir_Specification object
pv_registry = {}       # key: node/@label, value: PV_Specification object


def getDirObjectByXmlNode(xml_node):
    '''locate a Dir_Specification object by matching its xml_node'''
    for dir_spec_obj in dir_registry.values():
        if dir_spec_obj.xml_node == xml_node:
            return dir_spec_obj
    return None


class Dir_Specification(object):
    
    def __init__(self, xml_element_node):
        self.hdf5_path = None
        self.xml_node = xml_element_node
        self.hdf5_group = None
        self.name = xml_element_node.attrib['name']
        self.nx_class = xml_element_node.attrib['class']

        xml_parent_node = xml_element_node.getparent()
        self.dir_children = {}
        if xml_parent_node.tag == 'dir':
            # identify our parent
            self.dir_parent = getDirObjectByXmlNode(xml_parent_node)
            # next, find our HDF5 path from our parent
            path = self.dir_parent.hdf5_path
            if not path.endswith('/'):
                path += '/'
            self.hdf5_path = path + self.name
            # finally, declare ourself to be a child of that parent
            self.dir_parent.dir_children[self.hdf5_path] = self
        elif xml_parent_node.tag == 'NX_structure':
            self.dir_parent = None
            self.hdf5_path = '/'
        if self.hdf5_path in dir_registry:
            msg = "Cannot create duplicate HDF5 path names: " + self.hdf5_path
            raise RuntimeError, msg
        dir_registry[self.hdf5_path] = self
    
    def __str__(self):
        return self.hdf5_path or 'Dir_Specification object'


class PV_Specification(object):
    
    def __init__(self, xml_element_node):
        self.xml_node = xml_element_node
        self.label = xml_element_node.attrib['label']
        if self.label in pv_registry:
            msg = "Cannot use PV label more than once: " + self.label
            raise RuntimeError, msg
        self.pvname = xml_element_node.attrib['pvname']
        self.pv = None
        self.attrib = {}
        self.length_limit = xml_element_node.get('length_limit', None)
        for node in xml_element_node.xpath('attribute'):
            self.attrib[node.attrib['name']] = node.attrib['value']
        
        # identify our parent
        xml_parent_node = xml_element_node.getparent()
        self.dir_parent = getDirObjectByXmlNode(xml_parent_node)
        # finally, declare ourself to be a child of that parent
        self.hdf5_path = self.dir_parent.hdf5_path + '/' + self.label
        self.dir_parent.dir_children[self.hdf5_path] = self
        pv_registry[self.label] = self
    
    def __str__(self):
        try:
            nm = self.label + ' <' + self.pvname + '>'
        except:
            nm = 'PV_Specification object'
        return nm


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
        self._prepare_to_acquire()

    def waitForData(self):
        '''wait until the data is ready, then save it'''
        self.completion_signal = False
        self.trigger = epics.PV(self.trigger_pv, callback=self.triggerHandler)
        while not self.completion_signal:
            time.sleep(self.trigger_poll_interval_s)
        self.saveFile()
    
    def triggerHandler(self, **keys):
        '''receive the EPICS CA monitor on the trigger PV and save the data at the right time'''
        if self.trigger.get() in self.trigger_accepted_values:
            self.completion_signal = True

    def saveFile(self):
        '''write all desired data to the file and exit this code'''
        t = datetime.datetime.now()
        timestamp = ' '.join((t.strftime("%Y-%m-%d"), t.strftime("%H:%M:%S")))
        eznx.addAttributes(self.structure['/'].hdf5_group, timestamp = timestamp)

        for pv_spec in self.pvdb.values():
            value = pv_spec.pv.get()
            if not isinstance(value, numpy.ndarray):
                value = [value]
            else:
                if pv_spec.length_limit and pv_spec.length_limit in pv_registry:
                    length_limit = pv_registry[pv_spec.length_limit].pv.get()
                    if len(value) > length_limit:
                        value = value[:length_limit]
            hdf5_parent = pv_spec.dir_parent.hdf5_group
            ds = eznx.makeDataset(hdf5_parent, pv_spec.label, value)
            self._attachEpicsAttributes(ds, pv_spec.pv)
            eznx.addAttributes(ds, **pv_spec.attrib)
        
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
        #       <xs:attribute name="poll_time_s" use="optional" type="xs:decimal" default="0.1"/>
        # use an XPath search to get the node from xmlschema_doc
        default_value = self.trigger_poll_interval_s
        self.trigger_poll_interval_s = node.get('poll_time_s', default_value)
        
        nx_structure = root.xpath('/saveFlyData/NX_structure')[0]
        for node in nx_structure.xpath('//dir'):
            Dir_Specification(node)
        
        for node in nx_structure.xpath('//PV'):
            PV_Specification(node)
    
    def _get_support_code_dir(self):
        return os.path.split(os.path.abspath(__file__))[0]
  
    def _prepare_to_acquire(self):
        '''connect to EPICS and create the HDF5 file and structure'''
        # connect to EPICS PVs
        for pv_spec in pv_registry.values():
            pv_spec.pv = epics.PV(pv_spec.pvname)

        # create the file
        for key, xture in sorted(dir_registry.items()):
            if key == '/':
                # create the file and internal structure
                f = eznx.makeFile(self.hdf5_file_name,
                  # the following are attributes to the root element of the HDF5 file
                  file_name = self.hdf5_file_name,
                  instrument = "APS USAXS at 15ID-D",
                  scan_mode = 'USAXS fly scan',
                  creator = __file__,
                  creator_version = self.creator_version,
                  svn_id = SVN_ID,
                  HDF5_Version = h5py.version.hdf5_version,
                  h5py_version = h5py.version.version,
                )
                xture.hdf5_group = f
            else:
                hdf5_parent = xture.dir_parent.hdf5_group
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
    path = os.path.split(dataFile)[0]
    if len(path) > 0 and not os.path.exists(path):
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
    main()	# production system

    # code development
#     sfs = SaveFlyScan('test.h5', XML_CONFIGURATION_FILE)
#     sfs.waitForData()


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
