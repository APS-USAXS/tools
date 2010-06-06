'''
Created on Jun 4, 2010

@author: Pete Jemian
@contact: jemian@anl.gov
@organization: Advanced Photon Source, Argonne National Laboratory
@license: scanTimeCalc is part of USAXS_tools; See LICENSE (included with this file) for full details.
@version: $Id$
@summary: USAXS scanTimeCalc estimates the time to complete a batch of scans.
@requires: wxPython
@requires: CaChannel (for EPICS)
@status: converted from the Tcl code

@todo: finish building the GUI
@todo: manage the RC_FILE I/O
@todo: Calculations
@todo: Connect with EPICS variables

########### SVN repository information ###################
# $Date$
# $Author$
# $Revision$
# $URL$
# $Id$
########### SVN repository information ###################
'''


import os
import wx


class GUI(wx.App):
    '''class whose only purpose is to run the qToolFrame'''

    def OnInit(self):
        '''run the GUI, always returns True'''
        self.main = qToolFrame(None)
        self.main.Show()
        self.SetTopWindow(self.main)
        return True


class qToolFrame(wx.Frame):
    '''define and operate the GUI'''

    def __init__(self, parent):
        '''create the GUI'''

        # define some things for the program
        self.SVN_ID = "$Id$"
        self.TITLE = u'USAXS scan time calculator'
        self.GRAY = wx.ColorRGB(0xababab)
        self.MOVING_COLOR = wx.GREEN
        self.NOT_MOVING_COLOR = wx.LIGHT_GREY
        self.LIGHTBLUE = wx.ColorRGB(0xffddcc)
        self.BISQUE = wx.ColorRGB(0xaaddee)
        self.COLOR_USER_ENTRY = self.BISQUE
        self.COLOR_CALCULATED = self.LIGHTBLUE
        self.NUM_Q_ROWS = 30
        self.MIN_GUI_SIZE = (600, 600)    # the widgets just fit
        self.MAX_GUI_SIZE = (-1, -1)
        self.USER_HOME = os.getenv('USERPROFILE') or os.getenv('HOME') # windows or Linux/Mac
        self.RC_FILE = os.path.join(self.USER_HOME, '.scanTimeCalcrc')
        """
          PV,Lambda        32ida:BraggLambdaAO
          PV,Scan,Finish    32idbLAX:USAXS:Finish
          PV,Scan,StartOffset    32idbLAX:USAXS:StartOffset
          PV,Scan,NumPoints    32idbLAX:USAXS:NumPoints
          PV,Scan,CountTime    32idbLAX:USAXS:CountTime
          PV,Scan,AR_center     32idbLAX:USAXS:ARcenter 
            array set db {
                GUI_N          150
                AR_start       10.523
                AR_end         1
                GUI_CountTime  5
                N_samples      1
                VELO_step      0.02
                VELO_return    0.4
                ACCL           0.2
                t_delay        0.5
                t_tuning       150
                A_keV          12.3984244
            }
        """

        # build the GUI
        wx.Frame.__init__(self, parent=parent, id=wx.ID_ANY,
              style=wx.DEFAULT_FRAME_STYLE, title=self.TITLE,
              size=self.MIN_GUI_SIZE)
        
        self.SetMinSize(self.MIN_GUI_SIZE)
        self.SetMaxSize(self.MAX_GUI_SIZE)
        self.__init_statusBar__('status')
        self.__init_bsMain__(parent)
        self.SetStatusText('startup is complete')

    def __init_statusBar__(self, text):
        '''provides a status bar to say what is happening'''
        bar = wx.StatusBar(id=wx.ID_ANY,
              name='mainStatusBar', parent=self, style=0)
        bar.SetFieldsCount(1)
        bar.SetStatusText(number=0, text=text)
        bar.SetStatusWidths([-1])
        self.SetStatusBar(bar)

    def __init_bsMain__(self, parent):
        '''main box sizer, outermost sizer of the GUI'''
        # list of items to add to the main BoxSizer
        itemList = []

        self.title = self.__init_statictext__(
               name='title', text=self.TITLE, fontSize=20, tooltip='')
        
        itemList.append([0, self.title])

        self.subtitle = self.__init_statictext__(
               name='subtitle', text=self.SVN_ID, fontSize=8,
               tooltip='revision identifier from the version control system')
        itemList.append([0, self.subtitle])

        itemList.append([0, self.__init_parameters__()])

        box = wx.BoxSizer(orient=wx.VERTICAL)
        for item in itemList:
            hint, widget = item
            box.Add(widget, hint, flag=wx.EXPAND)
        
        self.SetSizer(box)
        self.FitInside()

    def __init_parameters__(self):
        '''
            create the table of user parameters, 
            defines parameterList dictionary, 
            returns FlexGridSizer object
        '''
        entryConfig = [
          ['GUI_N', '# of points', ''],
          ['GUI_keV', 'energy', 'keV'],
          ['GUI_Start', 'AR_start_offset', 'degrees'],
          ['GUI_Finish', 'Q_max', '1/A'],
          ['GUI_CountTime', 'count time', 'seconds'],
          ['N_samples', '# of samples', '']
        ]
        sbox = wx.StaticBox(id=wx.ID_ANY,
              label='user parameters', name='sbox',
              parent=self, style=0)
        sbs = wx.StaticBoxSizer(sbox, wx.VERTICAL)
        fgs = wx.FlexGridSizer(rows=len(entryConfig), cols=3, hgap=10, vgap=5)
        
        self.parameterList = {}
        for row in entryConfig:
            name, desc, units = row
            st = wx.StaticText(self, wx.ID_ANY, desc, style=wx.ALIGN_RIGHT)
            fgs.Add(st, 0, flag=wx.EXPAND)

            widget = wx.TextCtrl(self, wx.ID_ANY, "")
            widget.SetBackgroundColour(self.COLOR_USER_ENTRY)
            widget.SetToolTipString('value of ' + name + ' parameter')
            fgs.Add(widget, 1, wx.EXPAND)
            self.parameterList[name] = { 'entry': widget }

            st = wx.StaticText(self, wx.ID_ANY, units, style=wx.ALIGN_LEFT)
            fgs.Add(st, 0, flag=wx.EXPAND)

        fgs.AddGrowableCol(1)
        sbs.Add(fgs, 0, wx.EXPAND|wx.ALIGN_CENTRE|wx.ALL, 5)
        
        return sbs

    def __init_statictext__(self, name, text, tooltip='', fontSize=10, color=None):
        '''create a StaticText item'''
        item = wx.StaticText(id=wx.ID_ANY,
              label=text, name=name, parent=self,
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
                #
                # place the data into the widgets
                #
            self.SetStatusText('loaded settings from: ' + self.RC_FILE)

    def save_rcfile(self, event):
        '''
            reads the widget fields
            writes the resource configuration file
        '''
        output = ""
        #
        # pick data from the widgets and format for output to the RC_FILE
        #
        f = open(self.RC_FILE, 'w')
        f.write(output)
        f.close()
        self.SetStatusText('saved settings in: ' + self.RC_FILE)


if __name__ == '__main__':
    GUI(0).MainLoop()
