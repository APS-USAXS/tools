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


import math
import os
import wx
import pvConnect
import pprint

connections = {}  # EPICS Channel Access connections, key is PV name
XREF = {}         # key is PV name, value is descriptive name
db = {}           # values, key is descriptive name
widget_list = {}  # widgets with values to get or set
qTool = None


class GUI(wx.App):
    '''class whose only purpose is to run the qToolFrame'''

    def OnInit(self):
        '''run the GUI, always returns True'''
 	global qTool
	if pvConnect.IMPORTED_CACHANNEL:
 	    capoll_timer = pvConnect.CaPollWx(0.1)
 	    capoll_timer.start()
	qTool = qToolFrame(None)
        qTool.Show()
        self.SetTopWindow(qTool)
	for name in qTool.PV_LIST:
	    pv = qTool.PV_LIST[name]
	    XREF[pv] = name
	    conn = pvConnect.EpicsPv(pv)
	    conn.SetUserCallback(_main_callback)
	    conn.SetUserArgs(pv)
	    conn.connectw()
	    conn.monitor()
	    connections[pv] = conn
        pprint.pprint(XREF)
	return True


def _main_callback(epics_args, user_args):
    '''EPICS monitor event received for this code'''
    value = epics_args['pv_value']
    pv = user_args[0]
    # pprint.pprint(epics_args)
    print '_main_callback:', pv, value
    name = XREF[pv]
    db[name] = value
    # should not do this in an event handler
    qTool.update()
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
        self.MINTCREAM = wx.ColorRGB(0xe5ffea)
        self.COLOR_CALCULATED = self.LIGHTBLUE
        self.COLOR_EPICS_MONITOR = self.LIGHTBLUE
        self.COLOR_USER_ENTRY = self.BISQUE
        self.NUM_Q_ROWS = 30
        self.USER_HOME = os.getenv('USERPROFILE') or os.getenv('HOME') # windows or Linux/Mac
        self.RC_FILE = os.path.join(self.USER_HOME, '.scanTimeCalcrc')
	self.PV_LIST = {
          'PV,Lambda'		: '32ida:BraggLambdaAO',
          'PV,Scan,Finish'	: '15iddLAX:USAXS:Finish',
          'PV,Scan,StartOffset' : '15iddLAX:USAXS:StartOffset',
          'PV,Scan,NumPoints'	: '15iddLAX:USAXS:NumPoints',
          'PV,Scan,CountTime'	: '15iddLAX:USAXS:CountTime',
          'PV,Scan,AR_center'	: '15iddLAX:USAXS:ARcenter'
	}
	# TODO: revise above list and remove list below once beamline has DCM support
	self.PV_LIST = {
          'PV,Lambda'		: '15iddLAX:float1',
          'PV,Scan,Finish'	: '15iddLAX:float2',
          'PV,Scan,StartOffset' : '15iddLAX:float3',
          'PV,Scan,NumPoints'	: '15iddLAX:float4',
          'PV,Scan,CountTime'	: '15iddLAX:float5',
          'AR_center'	: '15iddLAX:float6'
	}
	# these are fall-back values used to start the tool
	# they should be replaced quickly on startup by EPICS values
	db['GUI_N']	    = 150
	db['GUI_keV']       = 11.05
	db['GUI_Start']     = -0.005   # was 10.523
	db['GUI_Finish']    = 1
	db['GUI_CountTime'] = 5
	db['N_samples']     = 1
	db['VELO_step']     = 0.02
	db['VELO_return']   = 0.4
	db['ACCL']	    = 0.2
	db['t_delay']	    = 0.5
	db['t_tuning']	    = 150
	db['A_keV']	    = 12.3984244

	self.triggerUpdates = False
        # build the GUI
        wx.Frame.__init__(self, parent=parent, id=wx.ID_ANY,
              style=wx.DEFAULT_FRAME_STYLE, title=self.TITLE)
        
        self.__init_statusBar__('status')
        self.__init_bsMain__(parent)
        self.SetStatusText('startup is complete')

	# supply default values to the widgets
	self.triggerUpdates = True

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

        self.title = self.__init_statictext__(
               text=self.TITLE, fontSize=18)
        
        itemList.append([0, self.title])

        self.subtitle = self.__init_statictext__(
               text=self.SVN_ID, fontSize=8,
               tooltip='revision identifier from the version control system')
        itemList.append([0, self.subtitle])

        itemList.append([0, self.__init_parameters__(self)])
        itemList.append([0, self.__init_copy_button__(self)])
        itemList.append([0, self.__init_others__(self)])
        itemList.append([0, self.__init_results__(self)])

        box = wx.BoxSizer(orient=wx.VERTICAL)
        for item in itemList:
            hint, widget = item
            box.Add(widget, hint, flag=wx.EXPAND)
        
        self.SetSizer(box)
        #self.SetAutoLayout(True)
        self.Fit()
        size = self.GetSize()
        self.SetMinSize(size)
        self.SetMaxSize((-1, size[1]))  # only expand horizontally

    def __init_parameters__(self, parent):
        '''
            create the table of user parameters, 
            defines parameterList dictionary, 
            returns container object
        '''
        config = [
          ['GUI_N', '# of points', ''],
          ['GUI_keV', 'energy', 'keV'],
          ['GUI_Start', 'AR_start_offset', 'degrees'],
          ['GUI_Finish', 'Q_max', '1/A'],
          ['GUI_CountTime', 'count time', 'seconds'],
          ['N_samples', '# of samples', '']
        ]
        sbox = wx.StaticBox(parent, id=wx.ID_ANY,
              label='user parameters', style=0)
        sbs = wx.StaticBoxSizer(sbox, wx.VERTICAL)
        fgs = wx.FlexGridSizer(rows=len(config), cols=3, hgap=10, vgap=5)
        
        self.parameterList = {}
        for row in config:
            name, desc, units = row
            st = wx.StaticText(parent, wx.ID_ANY, desc, style=wx.ALIGN_RIGHT)
            fgs.Add(st, 0, flag=wx.EXPAND)

            widget = wx.TextCtrl(parent, wx.ID_ANY, "", style=wx.SUNKEN_BORDER)
            widget.SetBackgroundColour(self.COLOR_USER_ENTRY)
            widget.SetToolTipString('parameter: ' + name)
            fgs.Add(widget, 1, wx.EXPAND|wx.ALL)
            self.parameterList[name] = { 'entry': widget }
	    widget_list[name] = widget.SetValue

            st = wx.StaticText(parent, wx.ID_ANY, units, style=wx.ALIGN_LEFT)
            fgs.Add(st, 0, flag=wx.EXPAND)

        config = [
          ['AR_start', 'AR start angle', 'degrees'],
          ['AR_center', 'AR center angle', 'degrees'],
          ['AR_end', 'AR end angle', 'degrees']
        ]
        fgs.SetRows(fgs.GetRows() + len(config))
        for row in config:
            name, desc, units = row
            st = wx.StaticText(parent, wx.ID_ANY, desc, style=wx.ALIGN_RIGHT)
            fgs.Add(st, 0, flag=wx.EXPAND)

            widget = wx.TextCtrl(parent, wx.ID_ANY, "", style=wx.SIMPLE_BORDER)
            widget.SetToolTipString('parameter: ' + name)
            widget.SetBackgroundColour(self.COLOR_EPICS_MONITOR)
            fgs.Add(widget, 1, wx.EXPAND)
            self.parameterList[name] = { 'entry': widget }
	    widget_list[name] = widget.SetValue

            st = wx.StaticText(parent, wx.ID_ANY, units, style=wx.ALIGN_LEFT)
            fgs.Add(st, 0, flag=wx.EXPAND)

        fgs.AddGrowableCol(1)
        sbs.Add(fgs, 0, wx.EXPAND|wx.ALIGN_CENTRE|wx.ALL, 5)
        sbox.FitInside()
        
        return sbs

    def __init_copy_button__(self, parent):
        '''
            create the EPICS sync button, 
            defines copyList dictionary, 
            returns container object
        '''
        self.copyList = {}

        # copy button
        button = wx.Button(parent, id=wx.ID_ANY, 
           label="copy EPICS PVs to table" )
        button.SetBackgroundColour(wx.BLACK)
        button.SetForegroundColour(wx.WHITE)
        button.SetToolTipString('copy EPICS PVs to table values')
        self.copyList["copy"] = { 'button': button }

        return button


    def __init_others__(self, parent):
        '''
            create the table of other user parameters, 
            defines otherList dictionary, 
            returns container object
        '''
        config = [
          ['VELO_step', 'AR step-scan speed', 'degrees/second'],
          ['VELO_return', 'AR return speed', 'degrees/second'],
          ['ACCL', 'AR acceleration time', 'seconds'],
          ['t_delay', 'delay time/point', 'seconds'],
          ['t_tuning', 'tuning and dark current time', 'seconds']
        ]
        sbox = wx.StaticBox(parent, id=wx.ID_ANY,
              label='other user parameters', style=0)
        sbs = wx.StaticBoxSizer(sbox, wx.VERTICAL)
        fgs = wx.FlexGridSizer(rows=len(config), cols=3, hgap=10, vgap=5)
        
        self.otherList = {}

        for row in config:
            name, desc, units = row
            st = wx.StaticText(parent, wx.ID_ANY, desc, style=wx.ALIGN_RIGHT)
            fgs.Add(st, 0, flag=wx.EXPAND)

            widget = wx.TextCtrl(parent, wx.ID_ANY, "", style=wx.SUNKEN_BORDER)
            widget.SetBackgroundColour(self.COLOR_USER_ENTRY)
            widget.SetToolTipString('parameter: ' + name)
            fgs.Add(widget, 1, wx.EXPAND)
            self.parameterList[name] = { 'entry': widget }
	    widget_list[name] = widget.SetValue

            st = wx.StaticText(parent, wx.ID_ANY, units, style=wx.ALIGN_LEFT)
            fgs.Add(st, 0, flag=wx.EXPAND)

        fgs.AddGrowableCol(1)
        sbs.Add(fgs, 0, wx.EXPAND|wx.ALIGN_CENTRE|wx.ALL, 5)
        sbox.FitInside()
        
        return sbs

    def __init_results__(self, parent):
        '''
            create the table of calculated results, 
            defines resultsList dictionary, 
            returns container object
        '''
        config = [
          ['s_motion', 'AR motor step time', 'seconds', 'p_motion'],
          ['s_count', 'counting time', 'seconds', 'p_count'],
          ['s_delay', 'delay time', 'seconds', 'p_delay'],
          ['s_accl', 'AR motor acceleration time', 'seconds', 'p_accl'],
          ['s_return', 'AR motor return time', 'seconds', 'p_return'],
          ['s_scan', 'one sample scan time', 'seconds/scan', 's_scan_HMS'],
          ['s_series', 'total time complete series', 'seconds/series', 's_HMS']
        ]
        sbox = wx.StaticBox(parent, id=wx.ID_ANY,
              label='calculated values', style=0)
        sbs = wx.StaticBoxSizer(sbox, wx.VERTICAL)
        fgs = wx.FlexGridSizer(rows=len(config), cols=4, hgap=10, vgap=5)
        
        self.resultsList = {}

        for row in config:
            name, desc, units, pct = row
            st = wx.StaticText(parent, wx.ID_ANY, desc, style=wx.ALIGN_RIGHT)
            fgs.Add(st, 0, flag=wx.EXPAND)

            widget = wx.TextCtrl(parent, wx.ID_ANY, "", style=wx.SUNKEN_BORDER)
            widget.SetBackgroundColour(self.COLOR_CALCULATED)
            widget.SetToolTipString('parameter: ' + name)
            fgs.Add(widget, 1, wx.EXPAND)
            self.parameterList[name] = { 'entry': widget }
	    widget_list[name] = widget.SetValue

            st = wx.StaticText(parent, wx.ID_ANY, units, style=wx.ALIGN_LEFT)
            fgs.Add(st, 0, flag=wx.EXPAND)

            st = wx.TextCtrl(parent, wx.ID_ANY, pct, style=wx.ALIGN_LEFT)
            fgs.Add(st, 0, flag=wx.EXPAND)
            self.parameterList[pct] = { 'text': widget }
            st.SetToolTipString('parameter: ' + pct)
	    widget_list[pct] = st.SetValue

        fgs.AddGrowableCol(1)
        fgs.AddGrowableCol(3)
        sbs.Add(fgs, 0, wx.EXPAND|wx.ALIGN_CENTRE|wx.ALL, 5)
        sbox.FitInside()
        
        return sbs

    def __init_statictext__(self, text, tooltip='', fontSize=10, color=None):
        '''create a StaticText item'''
        item = wx.StaticText(parent=self, id=wx.ID_ANY, label=text,
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

    def update(self):
	'''recalculate and update the widgets'''
	if self.triggerUpdates:
	    self.recalc()
	    self.fillWidgets()

    def fillWidgets(self):
	'''place values in the widgets'''
	print "filling ..."
	for name in db:
	    if name in widget_list:
	        widget = widget_list[name]
		text = str(db[name])
		#print name, text
		widget(text)

    def recalc(self):
    	'''
    	    recalculate the various values

    	     # starting and ending AR positions
    	     set db(AR_start) [expr $db(GUI_Start) + $db(AR_center)]
    	     set db(AR_end)   [expr $db(AR_center) - 2*asin( $db(GUI_Finish)*$db(A_keV)/(4 * $db(pi) * $db(GUI_keV))  ) * (180/$db(pi))]
    	     # estimate the time to complete the set of scans here
    	     set db(s_motion) [expr abs($db(AR_start)-$db(AR_end))/$db(VELO_step)]
    	     set db(s_accl)   [expr 2*$db(ACCL)*$db(GUI_N)]
    	     set db(s_delay)  [expr $db(t_delay)*$db(GUI_N)]
    	     set db(s_count)  [expr $db(GUI_CountTime)*$db(GUI_N)]
    	     set db(s_return) [expr abs($db(AR_start)-$db(AR_end))/$db(VELO_return)]
    	     set db(s_scan)   [expr $db(s_motion)+$db(s_accl)+$db(s_delay)+$db(s_count)+$db(s_return)]
    	     set db(s_series) [expr ($db(s_scan)+$db(t_tuning))*$db(N_samples)]
    	     set db(p_motion) [expr $db(s_motion) * 100.0/$db(s_scan)]
    	     set db(p_accl)   [expr $db(s_accl)   * 100.0/$db(s_scan)]
    	     set db(p_delay)  [expr $db(s_delay)  * 100.0/$db(s_scan)]
    	     set db(p_count)  [expr $db(s_count)  * 100.0/$db(s_scan)]
    	     set db(p_return) [expr $db(s_return) * 100.0/$db(s_scan)]
    	     foreach item [array names db p_*] {
    	       catch {$tool($item) configure -text [format %.2f%% $db($item)]}
    	     }
    	     set db(s_HMS) [calc_HMS $db(s_series)]
    	     set db(s_scan_HMS) [calc_HMS $db(s_scan)]
    	     catch {$tool(s_HMS) configure -text $db(s_HMS)}
    	     catch {$tool(s_scan_HMS) configure -text $db(s_scan_HMS)}
    	     save_rcfile
    	'''
	try:
	    print "recalculating ..."
	    db['AR_start'] = db['GUI_Start'] + db['AR_center']
	    print db['AR_start']
 	    wavelength = db['A_keV'] / db['GUI_keV']
 	    pi4 = 4 * math.pi
 	    r2d = 180/math.pi
 	    db['AR_end'] = db['AR_center'] - 2*math.asin( db['GUI_Finish'] * wavelength/pi4 ) * r2d
	    print db['AR_end']
	    db['s_motion'] = math.fabs(db['AR_start']-db['AR_end'])/db['VELO_step']
	    print db['s_motion']
	except:
	    pass


def on_exit(timer, epics_db):
    '''Exit handler to stop the ca.poll()
        @param timer: CaPollWx object
        @param epics_db: Python list of pvConnect.EpicsPv objects to be released'''
    #print __name__, "exit handler"
    #for item in epics_db:
    #    item.release()
    if pvConnect.IMPORTED_CACHANNEL:
        pvConnect.on_exit(timer)


if __name__ == '__main__':
    capoll_timer = None
    GUI(0).MainLoop()
    on_exit(capoll_timer, None)
