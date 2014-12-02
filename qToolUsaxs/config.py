
'''
manage the configuration file
'''


import os
import sys
from lxml import etree


class Position(object):
    
    def __init__(self, Q='', label=''):
        self.Q = Q
        self.label = label
        
    def __str__(self):
        return self.label + ': ' + self.Q


class ConfigFile(object):
    """
    in-memory representation
    """
    
    def __init__(self, fname=None):
        if not os.path.exists(fname):
            raise RuntimeError('Cannot find config file: ' + str(fname))
        self.fname = fname
        self.param = {}
        self.positions = []
        self.readfile()
    
    def readfile(self):
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
    
    def writefile(self, fname=None):
        pass


if __name__ == '__main__':
    # developer use
    cf = ConfigFile('qToolUsaxsrc.xml')
    print cf.param
    print cf.positions
