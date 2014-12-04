
'''
manage the resource configuration file for the qToolUsaxs program
'''


import datetime
import os
from lxml import etree

CONFIG_FILE_VERSION = '2.1'


class Position(object):
    '''placeholder for each table row'''
    
    def __init__(self, Q='', label=''):
        self.Q = Q
        self.label = label
        
    def __str__(self):
        return self.label + ': ' + self.Q


class ConfigFile(object):
    '''in-memory representation of .rc file'''
    
    def __init__(self, fname=None):
        self.fname = fname
        self.param = {}
        self.positions = []
        self.pvmap = {}
        if os.path.exists(fname):
            self.rc_read()
    
    def toDataModel(self):
        '''write positions to list for use as data model in GUI'''
        return [[pos.label, pos.Q] for pos in self.positions]
    
    def fromDataModel(self, model):
        '''get positions from GUI data model'''
        self.positions = []
        for row in model:
            label, Q = row[0:2]
            self.positions.append(Position(Q, label))
    
    def rc_read(self):
        '''read the configuration from the resource configuration XML file'''
        root = etree.parse(self.fname)
        for node in root.xpath('//parameter'):
            param_name = node.attrib['name'].strip()
            value = node.text.strip()
            self.param[param_name] = value
        for node in root.xpath('//position'):
            Q = node.attrib['Q'].strip()
            label = node.attrib['label'].strip()
            # _row = node.attrib['row'].strip()
            position = Position(Q, label)
            # ignore _row
            self.positions.append(position)
        for node in root.xpath('//EPICS_PV'):
            pv = node.attrib['pv'].strip()
            label = node.attrib['name'].strip()
            self.pvmap[label] = pv
    
    def rc_write(self, fname=None):
        '''write the configuration to the resource configuration XML file'''
        if fname is None: return
        
        t = datetime.datetime.now()
        yyyymmdd = t.strftime("%Y-%m-%d")
        hhmmss = t.strftime("%H:%M:%S")

        root = etree.Element('qTool')
        root.set("version", CONFIG_FILE_VERSION)
        root.set("date", yyyymmdd)
        root.set("time", hhmmss)
        root.append(etree.Comment(" written by: " + 'qToolUsaxs.config.py '))
        #root.append(ElementTree.ProcessingInstruction("example ProcessingInstruction()"))
 
        ####################################
        # add the items to the XML structure
        ####################################

        # user parameters
        for key in sorted(self.param.keys()):
            value = self.param[key]
            node = etree.SubElement(root, "parameter")
            node.set("name", key)
            if len(value) > 0:
                node.text = str(value)

        # Q position table
        for row, pos in enumerate(self.positions):
            node = etree.SubElement(root, "position")
            # node.set("row",   str(row+1))
            for key in "label Q".split():
                #value = pos._get(key)
                value = pos.__getattribute__(key)
                if len(value) == 0: value = ''
                node.set(key, value)

        # PV map
        for label, pv in sorted(self.pvmap.items()):
            node = etree.SubElement(root, "EPICS_PV")
            node.set('name', label)
            node.set('pv', pv)
        
        # pretty print to the XML file: fname
        if fname is not None:
            f = open(fname, 'w')
            f.write(etree.tostring(root, pretty_print=True))
            f.close()


if __name__ == '__main__':
    # developer use
    cf = ConfigFile('qToolUsaxsrc.xml')
    print cf.param
    print cf.positions
    import qToolUsaxs
    cf.pvmap = qToolUsaxs.PV_MAP
    print cf.pvmap
    cf.rc_write('test.xml')
    
    model = cf.toDataModel()
    print model
    cf.fromDataModel(model)
