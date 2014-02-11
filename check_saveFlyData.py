#!/usr/bin/env python

import epics
from lxml import etree


XML_FILE = 'saveFlyData.xml'
XSD_FILE = 'saveFlyData.xsd'

schema_tree = etree.parse(XSD_FILE)
schema = etree.XMLSchema(schema_tree)
parser = etree.XMLParser(schema = schema)

try:
  valid = etree.parse(XML_FILE, parser)
  print XML_FILE, 'is valid against rules defined in', XSD_FILE
except Exception, exc:
  print XML_FILE, 'is not valid against rules defined in', XSD_FILE
  raise exc

print '\n'*2
print 'check that all the defined PVs are actually available'
print '\n'*2
doc = etree.parse(XML_FILE)
for i, pv_node in enumerate(doc.xpath('//PV')):
  pvname = pv_node.attrib['pvname'].strip()
  print i, pvname, epics.caget(pvname)
