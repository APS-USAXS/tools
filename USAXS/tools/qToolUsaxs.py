'''
########### SVN repository information ###################
# $Date$
# $Author$
# $Revision$
# $URL$
# $Id$
########### SVN repository information ###################

@author: Pete Jemian
@contact: jemian@anl.gov
@organization: Advanced Photon Source, Argonne National Laboratory
@copyright: Copyright (C) 2010, UChicago Argonne, LLC, All Rights Reserved
@license: qTool is part of USAXS_tools; See LICENSE (included with this file) for full details.
@version: $Id$
@summary: USAXS qTool allows USAXS users to drive AR, AY, and DY based
on the desired Q.  It provides a table of known positions and buttons
to move each of the motors.
@requires: wxPython
@requires: CaChannel (for EPICS)
@status: converted from the Tcl code

@TODO: Calculations
@TODO: Connect with EPICS variables
@TODO: in Table of Q positions, put scrollbar inside the box
'''


import datetime
import os
import sys
import wx
from wx.lib import scrolledpanel
from xml.dom import minidom
from xml.etree import ElementTree
import pvConnect


XREF = {}         # key is PV name, value is descriptive name
qTool = None      # pointer to the GUI


class qToolFrame(wx.Frame):
    '''
    USAXS qTool allows USAXS users to drive AR, AY, and DY based
    on the desired Q.  It provides a table of known positions and buttons
    to move each of the motors.
    '''

    def __init__(self, parent):
        '''create the GUI'''

        # define some things for the program
        self.TOOL = u'qToolUsaxs'
        self.TITLE = u'USAXS Q positioner'
        self.SVN_ID = "$Id$"
        self.PRINT_LOG = False
        self.monitor_count = 0   # number of EPICS monitor events received
        self.GRAY = wx.ColorRGB(0xababab)
        self.MOVING_COLOR = wx.GREEN
        self.NOT_MOVING_COLOR = wx.LIGHT_GREY
        self.LIGHTBLUE = wx.ColorRGB(0xffddcc)
        self.BISQUE = wx.ColorRGB(0xaaddee)
        self.COLOR_USER_ENTRY = self.BISQUE
        self.COLOR_CALCULATED = self.LIGHTBLUE
        self.NUM_Q_ROWS = 30
        self.MAX_GUI_SIZE = (-1, -1)
        self.USER_HOME = os.getenv('USERPROFILE') or os.getenv('HOME') # windows or Linux/Mac
        self.RC_FILE = os.path.join(self.USER_HOME, '.qToolUsaxsrc')
        self.AXIS_NAMES = "AR AY DY"
        self.AXIS_LABELS = "motor readback target"
        self.AXIS_FIELDS = 'RBV VAL'
        self.PV_MAP = {
            'energy'        : '15ida:BraggERdbkAO',
            'Q,Finish'      : '15iddLAX:USAXS:Finish',
            'AR,enc'        : '15iddLAX:aero:c0:m1.RBV',
            'AR,enc,center' : '15iddLAX:USAXS:Q.B',
            'SDD'           : '15iddLAX:USAXS:SDD.VAL',
            'SAD'           : '15iddLAX:USAXS:SAD.VAL',
            'motor,AR'      : '15iddLAX:aero:c0:m1',
            'motor,AY'      : '15iddLAX:m58:c1:m7',
            'motor,DY'      : '15iddLAX:m58:c2:m5'
        }
        self.PV_MAP['PV,energy'] = '15iddLAX:float1'   # @TODO: no DCM yet at 15ID
        self.MOTOR_PV_FIELDS = "VAL DESC RBV STOP HLM LLM MOVN".split()

        # build the GUI
        wx.Frame.__init__(self, parent=parent, id=wx.ID_ANY,
              style=wx.DEFAULT_FRAME_STYLE, title=self.TITLE)

        self.CreateStatusBar()
        self.__init_bsMain__(parent)

        self.postMessage('startup is complete')

    def __init_bsMain__(self, parent):
        '''main box sizer, outermost sizer of the GUI'''
        # list of items to add to the main BoxSizer
        itemList = []


        self.title = self.__init_statictext__(self,
                          text=self.TITLE, fontSize=20)
        itemList.append([0, self.title])

        self.subtitle = self.__init_statictext__(self,
               text=self.SVN_ID, fontSize=8,
               tooltip='revision identifier from the version control system')
        itemList.append([0, self.subtitle])

        itemList.append([0, self.__init_button_bar__(self)])
        itemList.append([0, self.__init_motor_controls__(self)])
        itemList.append([0, self.__init_parameters__(self)])
        itemList.append([1, self.__init_positions_controls__(self)])

        box = wx.BoxSizer(orient=wx.VERTICAL)
        for item in itemList:
            hint, widget = item
            box.Add(widget, hint, flag=wx.EXPAND)

        self.SetSizer(box)
        self.SetAutoLayout(True)
        #self.Fit()
        #size = self.GetSize()
        size = (600, 600)
        self.SetSize(size)
        self.SetMinSize(size)
        self.SetMaxSize(self.MAX_GUI_SIZE)

    def __init_motor_controls__(self, parent):
        '''
            create the control items,
            defines self.motorList dictionary,
            returns FlexGridSizer object
        '''
        sbox = wx.StaticBox(parent, id=wx.ID_ANY,
              label='watch EPICS motors', style=0)
        sbs = wx.StaticBoxSizer(sbox, wx.VERTICAL)
        fgs = wx.FlexGridSizer(rows=4, cols=3, hgap=4, vgap=4)

        # column labels
        for item in self.AXIS_LABELS.split():
            fgs.Add(
                 wx.StaticText(parent, wx.ID_ANY, item, style=wx.ALIGN_RIGHT),
                 0, flag=wx.EXPAND)
        # one motor axis per row
        self.motorList = {}
        for axis in self.AXIS_NAMES.split():
            fgs.Add(
                 wx.StaticText(parent, wx.ID_ANY, axis, style=wx.ALIGN_RIGHT),
                 0, flag=wx.EXPAND)
            dict = {}
            for field in self.AXIS_FIELDS.split():
                text = '[%s].%s' % (axis, field)
                widget = wx.StaticText(parent, wx.ID_ANY, text, style=wx.ALIGN_RIGHT)
                widget.SetBackgroundColour(self.NOT_MOVING_COLOR)
                widget.SetToolTipString('most recent EPICS value of ' + text + ' PV')
                fgs.Add(widget, 0, flag=wx.EXPAND)
                dict[field] = widget
            self.motorList[axis] = dict

        fgs.AddGrowableCol(1)
        fgs.AddGrowableCol(2)

        sbs.Add(fgs, 0, wx.EXPAND|wx.ALIGN_CENTRE|wx.ALL, 5)

        return sbs

    def __init_parameters__(self, parent):
        '''
            create the table of user parameters,
            defines parameterList dictionary,
            returns FlexGridSizer object
        '''
        config = [
          ['AY0', 'AY position at beam center, mm', self.COLOR_USER_ENTRY],
          ['DY0', 'DY position at beam center, mm', self.COLOR_USER_ENTRY],
          ['ARenc', 'AR encoder reading, degrees', self.COLOR_CALCULATED],
          ['ARenc0', 'AR encoder center, degrees', self.COLOR_CALCULATED],
          ['SDD', 'sample-detector distance, mm', self.COLOR_CALCULATED],
          ['SAD', 'sample-analyzer distance, mm', self.COLOR_CALCULATED],
          ['energy', 'X-ray photon energy, keV', self.COLOR_CALCULATED]
        ]
        sbox = wx.StaticBox(parent, id=wx.ID_ANY,
              label='user parameters', style=0)
        sbs = wx.StaticBoxSizer(sbox, wx.VERTICAL)
        fgs = wx.FlexGridSizer(rows=len(config), cols=2, hgap=4, vgap=4)

        self.parameterList = {}
        for row in config:
            name, desc, color = row
            fgs.Add(
                 wx.StaticText(parent, wx.ID_ANY, desc, style=wx.ALIGN_RIGHT),
                 0, flag=wx.EXPAND)
            widget = wx.TextCtrl(parent, wx.ID_ANY, "")
            widget.SetBackgroundColour(color)
            widget.SetToolTipString('value of ' + name + ' parameter')
            fgs.Add(widget, 1, wx.EXPAND)
            self.parameterList[name] = { 'entry': widget }

        fgs.AddGrowableCol(1)
        sbs.Add(fgs, 0, wx.EXPAND|wx.ALIGN_CENTRE|wx.ALL, 5)

        return sbs

    def __init_positions_controls__(self, parent):
        '''
            create the positions table
            defines self.positionList list
            returns container object
        '''
        labels = ['#', 'description', 'Q, 1/A', 'AR, degrees', 'AY, mm', 'DY, mm']

        swin = scrolledpanel.ScrolledPanel(parent, wx.ID_ANY, style=wx.TAB_TRAVERSAL|wx.VSCROLL)

        sbox = wx.StaticBox(parent=swin, id=wx.ID_ANY, label="table of Q positions")
        fgs = wx.FlexGridSizer(rows=self.NUM_Q_ROWS, cols=len(labels), hgap=4, vgap=4)

        #--- start of table
        for label in labels:
            st = wx.StaticText(swin, wx.ID_ANY, label, style=wx.ALIGN_RIGHT)
            fgs.Add(st, 0, flag=wx.EXPAND)

        self.positionList = []
        for row in range(self.NUM_Q_ROWS):
            dict = {}

            st = wx.StaticText(swin, wx.ID_ANY, str(row+1), style=wx.ALIGN_RIGHT|wx.EXPAND)
            fgs.Add(st, 0, flag=wx.EXPAND)

            widget = wx.TextCtrl(swin, wx.ID_ANY, "")
            widget.SetBackgroundColour(self.COLOR_USER_ENTRY)
            widget.SetToolTipString('user description of this position (row)')
            fgs.Add(widget, 3, wx.EXPAND)
            dict['label'] = { 'entry': widget }

            widget = wx.TextCtrl(swin, wx.ID_ANY, "")
            widget.SetBackgroundColour(self.COLOR_USER_ENTRY)
            widget.SetToolTipString('Q value of this position (row)')
            fgs.Add(widget, 2, wx.EXPAND)
            dict['Q'] = { 'entry': widget }

            for axis in self.AXIS_NAMES.split():
                label = "%s%d" % (axis, row+1)
                widget = wx.Button(parent=swin, id=wx.ID_ANY, label=label )
                widget.SetBackgroundColour(self.COLOR_CALCULATED)
                widget.SetToolTipString('move ' + axis + ' to this value')
                fgs.Add(widget, 2, wx.EXPAND)
                dict[axis] = { 'entry': widget }

            self.positionList.append(dict)

        for col in range(1, len(labels)):
            fgs.AddGrowableCol(col)
        #--- end of table

        sbs = wx.StaticBoxSizer(sbox, orient=wx.VERTICAL)
        sbs.Add(fgs, 0, wx.EXPAND|wx.ALIGN_CENTRE|wx.ALL, 5)
        sbox.SetAutoLayout(True)
        sbox.Fit()

        swin.SetupScrolling()
        swin.SetSizer(sbs)
        swin.SetAutoLayout(True)
        swin.Fit()

        return swin

    def __init_button_bar__(self, parent):
        '''
            create the button bar,
            defines buttonList dictionary,
            returns BoxSizer object
        '''
        labels = ['save settings', 'read settings', 'stop motors']

        self.bsButtons = wx.BoxSizer(orient=wx.HORIZONTAL)

        self.buttonList = {}
        for text in labels:
            label = text.split()[0]
            widget = wx.Button(parent, id=wx.ID_ANY, label=text)
            widget.SetBackgroundColour(self.COLOR_CALCULATED)
            widget.SetToolTipString(text)
            self.bsButtons.Add(widget, 1, wx.EXPAND)
            dict = { 'button': widget }
            self.buttonList[label] = dict
        self.buttonList['stop']['button'].SetBackgroundColour(wx.RED)
        self.buttonList['stop']['button'].SetForegroundColour(wx.WHITE)
        self.buttonList['save']['button'].Bind(wx.EVT_BUTTON, self.save_rcfile)
        self.buttonList['read']['button'].Bind(wx.EVT_BUTTON, self.read_rcfile)

        # queue it for writing to the main BoxSizer
        return self.bsButtons

    def __init_statictext__(self, parent, text, tooltip='', fontSize=10, color=None):
        '''create a StaticText item'''
        item = wx.StaticText(parent, id=wx.ID_ANY, label=text,
              style=wx.MAXIMIZE_BOX | wx.ALIGN_CENTRE | wx.EXPAND)
        item.SetFont(wx.Font(fontSize, wx.SWISS, wx.NORMAL, wx.NORMAL, False))
        item.SetAutoLayout(True)
        item.SetToolTipString(tooltip)
        item.Center(wx.HORIZONTAL)
        if color == None:
            color = self.GRAY
        item.SetBackgroundColour(color)
        return item

    def postMessage(self, message):
        '''
            post a message to the status line and the log
        '''
        datetime = self.timestamp()
        self.SetStatusText(message)
        try:
            self.message_count += 1
        except:
            self.message_count = 1  # only used here
        # post log datetime + ": " + message
        if self.PRINT_LOG:
            print "%s (%s) #%d: %s" % (datetime, self.TOOL, self.message_count, message)

    def yyyymmdd(self):
        '''
            return the current date as a string
        '''
        t = datetime.datetime.now()
        return t.strftime("%Y-%m-%d")

    def hhmmss(self):
        '''
            return the current time as a string
        '''
        t = datetime.datetime.now()
        return t.strftime("%H:%M:%S")

    def timestamp(self):
        '''
            return the current date and time as a string
        '''
        return self.yyyymmdd() + " " + self.hhmmss()

    def read_rcfile(self, event):
        '''
            reads the resource configuration file (XML)
            writes the widget fields
        '''
        if os.path.exists(self.RC_FILE):
            try:
                tree = ElementTree.parse(self.RC_FILE)
            except:
                self.postMessage('could not parse RC_FILE: ' + self.RC_FILE)
                return

            for key in tree.findall("//parameter"):
                name = key.get("name")
                value = key.text.strip()
                self.parameterList[name]['entry'].SetValue(value)

            for key in tree.findall("//position"):
                row = int(key.get("row"))
                label = key.get("label")
                Q = key.get("Q")
                self.positionList[row]['label']['entry'].SetValue(label)
                self.positionList[row]['Q']['entry'].SetValue(Q)

            self.postMessage('loaded settings from: ' + self.RC_FILE)

    def save_rcfile(self, event):
        '''
            reads the widget fields
            writes the resource configuration file (XML)
        '''
        f = open(self.RC_FILE, 'w')
        f.write(repr(self))
        f.close()
        self.postMessage('saved settings in: ' + self.RC_FILE)

    def MakePrettyXML(self, raw):
        '''
            make the XML look pretty to the eyes
        '''
        doc = minidom.parseString(ElementTree.tostring(raw))
        return doc.toprettyxml(indent = "  ")

    def __repr__(self):
        '''
            default representation of memory-resident data
        '''
        global widget_list
        global db
        t = datetime.datetime.now()
        yyyymmdd = t.strftime("%Y-%m-%d")
        hhmmss = t.strftime("%H:%M:%S")

        root = ElementTree.Element("qTool")
        root.set("version", "2.0")
        root.set("date", yyyymmdd)
        root.set("time", hhmmss)
        root.append(ElementTree.Comment("written by: " + self.SVN_ID))
        #root.append(ElementTree.ProcessingInstruction("example ProcessingInstruction()"))

        ####################################
        # add the items to the XML structure
        ####################################

        # user parameters
        for key in "AY0 DY0".split():
            value = self.parameterList[key]['entry'].GetValue()
            node = ElementTree.SubElement(root, "parameter")
            node.set("name", key)
            if len(value) > 0:
                node.text = value

        # Q position table
        for row in range(self.NUM_Q_ROWS):
            node = ElementTree.SubElement(root, "position")
            node.set("row", str(row))
            for item in "label Q".split():
                value = self.positionList[row][item]['entry'].GetValue()
                if len(value) == 0: value = ""
                node.set(item, value)

        return self.MakePrettyXML(root)



def pv_monitor_handler(epics_args, user_args):
    '''EPICS monitor event received for this code'''
    qTool.monitor_count += 1
    value = epics_args['pv_value']
    pv = user_args[0]
    msg = "%s %s: %s=%s" % ('pv_monitor_handler', qTool.monitor_count, pv, value)
    qTool.PRINT_LOG = True
    qTool.postMessage(msg)
    qTool.PRINT_LOG = False
    return True


def main():
    '''
        this routine sets up the GUI program,
        starts the EPICS connections,
        runs the GUI,
        then buttons things up at the end
    '''

    # start wx
    app = wx.PySimpleApp()

    # prepare ChannelAccess support
    if pvConnect.IMPORTED_CACHANNEL:
        capoll_timer = pvConnect.CaPollWx(0.1)
        capoll_timer.start()

    qTool = qToolFrame(None)
    qTool.Show(True)

    #@TODO: Can the EPICS connection be deferred?
    # Perhaps some seconds after the GUI is drawn?
    #
    #@TODO: Also, perhaps don't wait for each PV to connect, might make the startup faster

    errorList = []  # list of PVs that did not connect
    pvList = []     # complete list of PVs to connect
    for item in qTool.PV_MAP:
        parts = item.split(",")
        if parts[0] == "motor":
            for field in qTool.MOTOR_PV_FIELDS:
                pvList.append("%s.%s" % (qTool.PV_MAP[item], field) )
        else:
            pvList.append(qTool.PV_MAP[item])
    for pv in pvList:
        print "Seeking EPICS PV connection with", pv
        try:  # connect with EPICS now
            conn = pvConnect.EpicsPv(pv).MonitoredConnection(pv_monitor_handler)
            connections[pv] = conn
        except:
            errorList.append(pv)

    if len(errorList) > 0:
        print "Problems connecting these EPICS PVs:\n  " + "\n  ".join(errorList)
        exit(1)
    qTool.postMessage("EPICS connections established")

    # run the GUI
    app.MainLoop()


if __name__ == '__main__':
    main()

