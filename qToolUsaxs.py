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

@TODO: in Table of Q positions, put scrollbar inside the box
'''


import datetime
import math
import os
import pprint
import sys
import wx
from wx.lib import scrolledpanel
from xml.dom import minidom
from xml.etree import ElementTree
import CaChannel


class qToolFrame(wx.Frame):
    '''
    USAXS qTool allows USAXS users to drive AR, AY, and DY based
    on the desired Q.  It provides a table of known positions and buttons
    to move each of the motors.
    '''

    def __init__(self, parent):
        '''create the GUI'''

        # define some things for the program
        self.__init_variables__()

        # build the GUI
        wx.Frame.__init__(self, parent=parent, id=wx.ID_ANY,
              style=wx.DEFAULT_FRAME_STYLE, title=self.TITLE)

        self.CreateStatusBar()
        self.__init_bsMain__(parent)
        self.__init_EPICS__()

        self.postMessage('startup is complete')
        name = "motor,AR,RBV"
        pv = self.XREF[name]
        value = self.db[pv]['ch'].getw()
        self.motorList['AR']['RBV'].SetValue(str(value))

    def __init_variables__(self, ):
        '''
        define the variables used by this class
        '''
        self.TOOL = u'qToolUsaxs'
        self.TITLE = u'USAXS Q positioner'
        self.SVN_ID = "$Id$"
        self.PRINT_LOG = False
        self.monitor_count = 0   # number of EPICS monitor events received
        self.basicFont = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL)
        self.GRAY = wx.ColorRGB(0xababab)
        self.MOVING_COLOR = wx.GREEN
        self.NOT_MOVING_COLOR = wx.LIGHT_GREY
        self.MOVN_COLORS = (self.NOT_MOVING_COLOR, self.MOVING_COLOR)
        self.LIGHTBLUE = wx.ColorRGB(0xffddcc)
        self.BISQUE = wx.ColorRGB(0xaaddee)
        self.COLOR_USER_ENTRY = self.BISQUE
        self.COLOR_CALCULATED = self.LIGHTBLUE
        self.COLOR_LIMITS_PROBLEM = wx.Colour(255,255,0)  # wx.YELLOW
        self.BUTTON_COLORS = {
              True: self.COLOR_CALCULATED,
              False: self.COLOR_LIMITS_PROBLEM
        }
        self.NUM_Q_ROWS = 30
        self.MAX_GUI_SIZE = (-1, -1)
        self.USER_HOME = os.getenv('USERPROFILE') or os.getenv('HOME') # windows or Linux/Mac
        self.RC_FILE = os.path.join(self.USER_HOME, '.qToolUsaxsrc')
        self.AXIS_NAMES = "AR AY DY".split()
        self.AXIS_LABELS = "motor readback target".split()
        self.AXIS_FIELDS = 'RBV VAL'.split()
        self.MOTOR_PV_FIELDS = "VAL DESC RBV STOP HLM LLM MOVN".split()
        self.EPICS_STOP_MOTOR_VALUE = 1
        self.PV_MAP = {
            'energy'        : '15IDA:BraggERdbkAO',
            'Q,Finish'      : '15iddLAX:USAXS:Finish',
            'AR,enc'        : '15iddLAX:aero:c0:m1.RBV',
            'AR,enc,center' : '15iddLAX:USAXS:Q.B',
            'SDD'           : '15iddLAX:USAXS:SDD.VAL',
            'SAD'           : '15iddLAX:USAXS:SAD.VAL',
            'AY0'           : '15iddLAX:USAXS:AY0.VAL',
            'DY0'           : '15iddLAX:USAXS:DY0.VAL',
            'motor,AR'      : '15iddLAX:aero:c0:m1',
            'motor,AY'      : '15iddLAX:m58:c1:m7',
            'motor,DY'      : '15iddLAX:m58:c2:m5'
        }

    def __init_EPICS__(self):
        '''
        start the EPICS connections
        '''
        self.CA_monitor_count = 0
        # poll EPICS ChannelAccess periodically for updates
        self.timer_interval_s = 0.05  # poll CA using a wxTimer for monitored events
        self.timer = wx.PyTimer(self.__poll_CA__)
        self.__start_Timer_Poll_CA__()

        self.db = {}  # dictionary for EPICS PV info

        errorList = {}  # dictionary of PVs that did not connect and reported status
        self.pvList = []     # complete list of PVs to connect
        self.XREF = {}       # cross-reference dictionary
        for item in self.PV_MAP:
            parts = item.split(",")
            if parts[0] == "motor":
                for field in self.MOTOR_PV_FIELDS:
                    fullpv = "%s.%s" % (self.PV_MAP[item], field)
                    fullitem = "%s,%s" % (item, field)
                    self.pvList.append(fullpv)
                    self.XREF[fullpv] = fullitem
                    self.XREF[fullitem] = fullpv
            else:
                self.pvList.append(self.PV_MAP[item])
                self.XREF[self.PV_MAP[item]] = item
                self.XREF[item] = self.PV_MAP[item]
        self.pvList.sort()

        mask = CaChannel.ca.DBE_VALUE
        self.pvList.append('S:SRcurrentAI')
        self.XREF['S:SRcurrentAI'] = 'APS,current,mA'
        self.XREF['APS,current,mA'] = 'S:SRcurrentAI'
        for pv in self.pvList:
            try:
                ch = CaChannel.CaChannel(str(pv))
                ch.searchw()
                ch.add_masked_array_event(None, None, mask, self.CA_event, pv)
                name = self.XREF[pv]
                self.db[pv] = {'pv': pv, 'ch': ch, 'value': None,
                               'count': 0, 'name': name}
            except CaChannel.CaChannelException, status:
                errorList[pv] = CaChannel.ca.message(status)
        if len(errorList) > 0:
            print "Problems connecting with EPICS PVs:"
            for pv in errorList:
                print "  %s: %s" % (pv, errorList[pv])
            self.__del__()
            exit(0)

    def __init_bsMain__(self, parent):
        '''
        main box sizer, outermost sizer of the GUI
        '''
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
        itemList.append([0, self.__init_motor_values__(self)])
        itemList.append([0, self.__init_parameters__(self)])
        itemList.append([1, self.__init_positions_controls__(self)])

        box = wx.BoxSizer(orient=wx.VERTICAL)
        for item in itemList:
            hint, widget = item
            box.Add(widget, hint, flag=wx.EXPAND)

        self.SetSizer(box)
        self.SetAutoLayout(True)
        size = (600, 600)
        self.SetSize(size)
        self.SetMinSize(size)
        self.SetMaxSize(self.MAX_GUI_SIZE)

    def __init_motor_values__(self, parent):
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
        for item in self.AXIS_LABELS:
            fgs.Add(
                 wx.StaticText(parent, wx.ID_ANY, item),
                 0, flag=wx.EXPAND)
        # one motor axis per row
        self.motorList = {}
        for axis in self.AXIS_NAMES:
            fgs.Add(
                 wx.StaticText(parent, wx.ID_ANY, axis, style=wx.ALIGN_RIGHT),
                 0, flag=wx.EXPAND)
            dict = {}
            for field in self.AXIS_FIELDS:
                text = '[%s].%s' % (axis, field)
                widget = wx.TextCtrl(parent, wx.ID_ANY, text, style=wx.TE_READONLY|wx.ALIGN_RIGHT)
                widget.SetBackgroundColour(self.NOT_MOVING_COLOR)
                widget.SetToolTipString("motor,%s,%s" % (axis, field))
                widget.SetFont(self.basicFont)
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
          ['AR,enc', 'AR encoder reading, degrees', self.COLOR_CALCULATED],
          ['AR,enc,center', 'AR encoder center, degrees', self.COLOR_CALCULATED],
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
            id = wx.NewId()
            widget = wx.TextCtrl(parent, id, "", style=wx.TE_PROCESS_ENTER)
            widget.SetBackgroundColour(color)
            widget.SetToolTipString("%s" % ( name))
            widget.SetFont(self.basicFont)
            widget.Bind(wx.EVT_TEXT_ENTER, self.caputParameter)
            fgs.Add(widget, 1, wx.EXPAND)
            self.parameterList[name] = { 'entry': widget, 'id': id }

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
        self.idList = {}  # use when responding to button presses to move a motor

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
            widget.SetFont(self.basicFont)
            fgs.Add(widget, 3, wx.EXPAND)
            dict['label'] = { 'entry': widget }

            widget = wx.TextCtrl(swin, wx.ID_ANY, "")
            widget.SetBackgroundColour(self.COLOR_USER_ENTRY)
            widget.SetToolTipString('Q value of this position (row)')
            widget.SetFont(self.basicFont)
            fgs.Add(widget, 2, wx.EXPAND)
            dict['Q'] = { 'entry': widget }

            for axis in self.AXIS_NAMES:
                label = "%s%d" % (axis, row+1)
                id = wx.NewId()
                widget = wx.Button(parent=swin, id=id, label=label )
                widget.SetBackgroundColour(self.COLOR_CALCULATED)
                widget.SetToolTipString('move ' + axis + ' to this value')
                widget.SetFont(self.basicFont)
                widget.Bind(wx.EVT_BUTTON, self.move_motor)
                #
                fgs.Add(widget, 2, wx.EXPAND)
                dict[axis] = { 'entry': widget, 'id': id }
                self.idList[id] = [row, axis]

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
            widget.SetFont(self.basicFont)
            self.bsButtons.Add(widget, 1, wx.EXPAND)
            dict = { 'button': widget }
            self.buttonList[label] = dict
        self.buttonList['stop']['button'].SetBackgroundColour(wx.RED)
        self.buttonList['stop']['button'].SetForegroundColour(wx.WHITE)
        self.buttonList['stop']['button'].Bind(wx.EVT_BUTTON, self.stop_motors)
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

    def __poll_CA__(self):
        '''Poll for changes in Channel Access'''
        CaChannel.ca.poll()

    def __start_Timer_Poll_CA__(self):
        '''start the timer that triggers CA polling'''
        self.running = True
        self.timer.Start(int(1000*self.timer_interval_s)) # use milliseconds

    def __stop_Timer_Poll_CA__(self):
        '''stop polling'''# only if wx was imported
        self.running = False
        self.timer.Stop()

    def __del__(self):
        '''
        Class delete event: don't leave timer hanging around!
        '''
        for pv in self.db.keys():     # release all the EPICS connections
            del self.db[pv]['ch']

        if self.timer.IsRunning():    # stop the wxTimer and dispose it
            self.timer.Stop()
        del self.timer

        CaChannel.ca.task_exit()      # stop the CaChannel task
        # @FIXME: sometimes, python still reports a seg fault on exit

    # ------------------------------------------

    def CA_event(self, epics_args, user_args):
        '''
        receive an EPICS event callback
        '''
        self.CA_monitor_count += 1
        pv = user_args[0]
        if pv in self.db:
            value = epics_args['pv_value']
            self.db[pv]['value'] = value
            self.db[pv]['count'] += 1
            name = self.db[pv]['name']
            try:
                msg = "%s %s: %s(%s)=%s" % (
                    'CA_event', self.CA_monitor_count, pv, name, value)
                self.postMessage(msg)
            except:
                message = "CA_event:\t Error: " + sys.exc_info()[1]
                self.postMessage(message)
            # perhaps a motor has been moving?
            parts = name.split(",")
            if len(parts) > 1 and parts[1] in self.motorList:
                m = self.motorList[parts[1]]
                if parts[2] == 'MOVN':  # is it moving or done?
                    m['RBV'].SetBackgroundColour(self.MOVN_COLORS[value])
                    m['VAL'].SetBackgroundColour(self.MOVN_COLORS[value])
                if parts[2] in m:       # a new value is reported
                    m[parts[2]].SetValue(str(value))
            # some user parameter has changed in EPICS?
            if name in self.parameterList:
                self.parameterList[name]['entry'].SetValue(str(value))
        self.recalc()       # recalculate all the buttons

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

            self.recalc()
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

    def stop_motors(self, event):
        '''
            sends a STOP to each EPICS motor
        '''
        self.postMessage('motors told to STOP')
        for axis in self.AXIS_NAMES:
            name = "motor,%s,STOP" % axis
            pv = self.XREF[name]
            ch = self.db[pv]['ch']
            ch.putw(self.EPICS_STOP_MOTOR_VALUE)

    def move_motor(self, event):
        '''
            sends a new position to the EPICS motor
        '''
        id = event.GetId()
        row, axis = self.idList[id]
        text = self.positionList[row][axis]['entry'].GetLabel()
        #text = event.GetEventObject().GetLabel()
        pv = self.XREF["motor,%s,VAL" % axis]
        try:
            value = float(text)
            if self.motorLimitsOK(axis, value):
                ch = self.db[pv]['ch']
                ch.putw(value)
        except:
            message = "move_motor: %s %s" % (axis, value)
            message += "\t Error: " + sys.exc_info()[1]
            self.postMessage(message)

    def caputParameter(self, event):
        '''
            sends the parameter to EPICS
        '''
        id = event.GetId()
        for item in self.parameterList:
            if id == self.parameterList[item]['id']:
                name = item
        try:
            value = self.parameterList[name]['entry'].GetValue()
            pv = self.XREF[name]
            self.db[pv]['ch'].putw(float(value))
            message = "caputParameter: caput %s %s" % (pv, value)
            self.postMessage(message)
        except:
            message = "caputParameter:\t Error: " + sys.exc_info()[1]
            self.postMessage(message)

    def motorLimitsOK(self, axis, value):
        '''
            tests if value is within the limits of the named motor axis
        '''
        if not axis in self.AXIS_NAMES:
            return False
        hlm = self.db[self.XREF["motor,%s,HLM" % axis]]['value']
        llm = self.db[self.XREF["motor,%s,LLM" % axis]]['value']
        result = (llm <= value) and (value <= hlm)
        return result

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

    def recalc(self):
        '''
            recalculate all the buttons
        '''
        A_keV = 12.3984244 # Angstrom * keV
        try:   # get initial parameters
            arEnc0 = float(self.parameterList['AR,enc,center']['entry'].GetValue())
            ar = float(self.motorList['AR']['RBV'].GetValue())
            arEnc = float(self.parameterList['AR,enc']['entry'].GetValue())
            ar0 = arEnc0 + ar - arEnc
            energy = float(self.parameterList['energy']['entry'].GetValue())
            lambda_over_4pi = A_keV / (energy * 4 * math.pi)
            sad = float(self.parameterList['SAD']['entry'].GetValue())
            sdd = float(self.parameterList['SDD']['entry'].GetValue())
            ay0 = float(self.parameterList['AY0']['entry'].GetValue())
            dy0 = float(self.parameterList['DY0']['entry'].GetValue())
        except:
            message = "recalc:  Error: " + str(sys.exc_info()[1])
            self.postMessage(message)
            return

        for row in range(len(self.positionList)):
            ar = 'ar ' + str(row)
            ay = 'ay ' + str(row)
            dy = 'dy ' + str(row)
            try:
                strQ = self.positionList[row]['Q']['entry'].GetValue()
                if len(strQ.strip()) > 0:
                    q = float(strQ)
                    x = -q * lambda_over_4pi
                    ar = ar0 + 2*math.degrees(math.asin( x ))
                    dy = dy0 + sdd * math.tan( x )
                    ay = ay0 + sad * math.tan( x )
                    # indicate limit problems with a yellow background
                    self.positionList[row]['AR']['entry'].SetBackgroundColour(
                        self.BUTTON_COLORS[self.motorLimitsOK("AR", ar)]
                    )
                    self.positionList[row]['AY']['entry'].SetBackgroundColour(
                        self.BUTTON_COLORS[self.motorLimitsOK("AY", ay)]
                    )
                    self.positionList[row]['DY']['entry'].SetBackgroundColour(
                        self.BUTTON_COLORS[self.motorLimitsOK("DY", dy)]
                    )
            except:
                message = "recalc:\t Error: " + sys.exc_info()[1]
                self.postMessage(message)
            # put the values into the button labels
            self.positionList[row]['AR']['entry'].SetLabel(str(ar))
            self.positionList[row]['AY']['entry'].SetLabel(str(ay))
            self.positionList[row]['DY']['entry'].SetLabel(str(dy))

def main():
    '''
        this runs the GUI program (standard wxPython procedure)
    '''
    app = wx.PySimpleApp()   # start wx with a 1 frame GUI
    qTool = qToolFrame(None) # build the GUI
    qTool.Show(True)         # make it visible
    app.MainLoop()           # run the GUI


if __name__ == '__main__':
    main()
