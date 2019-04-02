#!/usr/bin/env python

import epics
from lxml import etree


XML_FILE = 'saveFlyData.xml'
XSD_FILE = 'saveFlyData.xsd'

schema_tree = etree.parse(XSD_FILE)
schema = etree.XMLSchema(schema_tree)
parser = etree.XMLParser(schema = schema)

try:
  config = etree.parse(XML_FILE, parser)
  print XML_FILE, 'is valid against rules defined in', XSD_FILE
except Exception, exc:
  print XML_FILE, 'is not valid against rules defined in', XSD_FILE
  raise exc

epics.ca.DEFAULT_CONNECTION_TIMEOUT = 0.2

print '\n'*2
print 'check that all the defined PVs are actually available'
print '\n'*2
not_connected = []
for i, pv_node in enumerate(config.xpath('//PV')):
    pvname = pv_node.attrib['pvname'].strip()
    as_string = pv_node.attrib.get('string', "false").lower() in ('t', 'true')
    pv = epics.PV(pvname, verbose=False)    # control the output
    if pv.wait_for_connection():
        if as_string:
            v = pv.get(as_string=True)
        else:
            v = pv.get()
        print i, pvname, v
    else:
        print i, pvname, '!!!!!!!!! Could not connect'
        not_connected.append(pvname)

if len(not_connected) > 0:
    print '\n'*3
    print 'These PVs did not connect: \n*', '\n* '.join(not_connected)
else:
    print 'All PVs connected'
