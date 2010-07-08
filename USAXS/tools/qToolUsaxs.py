'''
Created on Jun 4, 2010

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

########### SVN repository information ###################
# $Date$
# $Author$
# $Revision$
# $URL$
# $Id$
########### SVN repository information ###################
'''


import os
#import wx
import wx.lib.scrolledpanel
import pvConnect




class qToolFrame(wx.Frame):
    '''define and operate the GUI'''

    def __init__(self, parent):
        '''create the GUI'''

        # define some things for the program
        self.SVN_ID = "$Id$"
        self.TITLE = u'USAXS Q positioner'
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
        # Tcl configuration items remaining
        #  PV,Q,Finish        15iddLAX:USAXS:Finish
        #  PV,AR,enc        15iddLAX:aero:c0:m1.RBV
        #  PV,AR,enc,center    15iddLAX:USAXS:Q.B
        #  PV,SDD        15iddLAX:USAXS:SDD.VAL
        #  PV,SAD        15iddLAX:USAXS:SAD.VAL
        #  PV,lambda        32ida:BraggLambdaRdbkAO
        #  PV,AR,motor        15iddLAX:aero:c0:m1
        #  PV,AY,motor        15iddLAX:m58:c1:m7
        #  PV,DY,motor        15iddLAX:m58:c2:m5
        #  motorPVfields        "VAL DESC RBV STOP HLM LLM MOVN"

        # build the GUI
        wx.Frame.__init__(self, parent=parent, id=wx.ID_ANY,
              style=wx.DEFAULT_FRAME_STYLE, title=self.TITLE)
        
        self.__init_statusBar__('status')
        self.__init_bsMain__(parent)
        self.SetStatusText('startup is complete')

    def __init_statusBar__(self, text):
        '''provides a status bar to say what is happening'''
        bar = wx.StatusBar(parent=self, id=wx.ID_ANY, style=0)
        bar.SetFieldsCount(1)
        bar.SetStatusText(number=0, text=text)
        bar.SetStatusWidths([-1])
        self.SetStatusBar(bar)

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
        fgs = wx.FlexGridSizer(rows=4, cols=3, hgap=10, vgap=5)
        
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
          ['lambda', 'wavelength, A', self.COLOR_CALCULATED]
        ]
        sbox = wx.StaticBox(parent, id=wx.ID_ANY,
              label='user parameters', style=0)
        sbs = wx.StaticBoxSizer(sbox, wx.VERTICAL)
        fgs = wx.FlexGridSizer(rows=len(config), cols=2, hgap=10, vgap=5)
        
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

        swin = wx.lib.scrolledpanel.ScrolledPanel(parent, wx.ID_ANY, style=wx.VSCROLL)

        sbox = wx.StaticBox(parent=swin, id=wx.ID_ANY, label="table of Q positions")
        fgs = wx.FlexGridSizer(rows=self.NUM_Q_ROWS, cols=len(labels), hgap=10, vgap=5)

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

    def read_rcfile(self, event):
        '''
            reads the resource configuration file
            writes the widget fields
        '''
        if os.path.exists(self.RC_FILE):
            for line in open(self.RC_FILE, 'r'):
                key = line.split()[0]
                value = " ".join(line.split()[1:])
                if value == '-':
                    value = ''
                splits = key.split(',')
                if len(splits) > 1:
                    # Q position table
                    row, item = splits
                    if int(row) <= self.NUM_Q_ROWS:
                        # only if row exists
                        self.positionList[int(row)-1][item]['entry'].SetValue(value)
                else:
                    # user parameter
                    self.parameterList[key]['entry'].SetValue(value)
            self.SetStatusText('loaded settings from: ' + self.RC_FILE)

    def save_rcfile(self, event):
        '''
            reads the widget fields
            writes the resource configuration file
        '''
        output = ""
        # user parameters
        for key in "AY0 DY0".split():
            value = self.parameterList[key]['entry'].GetValue()
            if len(value) == 0:
                value = "-"    # do not write empty strings
            output += "%s %s\n" % (key, value)
        # Q position table
        for row in range(self.NUM_Q_ROWS):
            for item in "label Q".split():
                value = self.positionList[row][item]['entry'].GetValue()
                if len(value) == 0:
                    value = "-"    # do not write empty strings
                output += "%d,%s %s\n" % (row+1, item, value)
        f = open(self.RC_FILE, 'w')
        f.write(output)
        f.close()
        self.SetStatusText('saved settings in: ' + self.RC_FILE)


if __name__ == '__main__':
    app = wx.PySimpleApp()
    frame = qToolFrame(None)
    frame.Show(True)
    app.MainLoop()

