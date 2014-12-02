
'''
manage the configuration file
'''


import datetime
import os
import sys
from lxml import etree

CONFIG_FILE_VERSION = '2.0'


class Position(object):
    
    def __init__(self, Q='', label=''):
        self.Q = Q
        self.label = label
        
    def __str__(self):
        return self.label + ': ' + self.Q


class ConfigFile(object):
    """
    in-memory representation of .rc file
    """
    
    def __init__(self, fname=None):
        if not os.path.exists(fname):
            raise RuntimeError('Cannot find config file: ' + str(fname))
        self.fname = fname
        self.param = {}
        self.positions = []
        self.rc_read()
    
    def rc_read(self):
        root = etree.parse(self.fname)
        for node in root.xpath('//parameter'):
            param_name = node.attrib['name'].strip()
            value = float(node.text.strip())
            self.param[param_name] = value
        for node in root.xpath('//position'):
            Q = node.attrib['Q'].strip()
            label = node.attrib['label'].strip()
            _row = node.attrib['row'].strip()
            position = Position(Q, label)
            # ignore _row
            self.positions.append(position)
    
    def rc_write(self, fname=None):
        t = datetime.datetime.now()
        yyyymmdd = t.strftime("%Y-%m-%d")
        hhmmss = t.strftime("%H:%M:%S")

        root = etree.ElementTree.Element("qTool")
        root.set("version", CONFIG_FILE_VERSION)
        root.set("date", yyyymmdd)
        root.set("time", hhmmss)
        root.append(etree.ElementTree.Comment("written by: " + 'qToolUsaxs.config.py'))
        #root.append(ElementTree.ProcessingInstruction("example ProcessingInstruction()"))
 
        ####################################
        # add the items to the XML structure
        ####################################

        # user parameters
        for key in sorted(self.param.keys()):
            value = self.param[key]
            node = etree.ElementTree.SubElement(root, "parameter")
            node.set("name", key)
            if len(value) > 0:
                node.text = str(value)

        # Q position table
        for row, pos in enumerate(self.positions):
            node = etree.ElementTree.SubElement(root, "position")
            node.set("row",   str(row))
            for key in "label Q".split():
                value = pos.get(key)
                if len(value) == 0: value = ''
                node.set(key, value)
        
        # TODO: pretty print to the XML file: fname


if __name__ == '__main__':
    # developer use
    cf = ConfigFile('qToolUsaxsrc.xml')
    print cf.param
    print cf.positions
