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
@license: scanTimeCalc is part of USAXS_tools; See LICENSE (included with this file) for full details.
@version: $Id$
@summary: USAXS scanTimeCalc estimates the time to complete a batch of scans.
@requires: wxPython
@requires: CaChannel (for EPICS)
@status: converted from the Tcl code

@TODO: manage the RC_FILE I/O
@TODO: complete the calculations
@TODO: differentiate EPICS PVs from local variables which might be updated from EPICS PVs
@TODO: Only update from EPICS PVs on request
@TODO: Respond to keyboard changes of user inputs
@TODO: show integer values as integers and not floats
'''


import math
import os
import pprint
import shlex
import subprocess
import wx
import pvConnect

connections = {}  # EPICS Channel Access connections, key is PV name
XREF = {}         # key is PV name, value is descriptive name
db = {}           # values, key is descriptive name
widget_list = {}  # widgets with values to get or set
qTool = None
update_count = 0
monitor_count = 0
updated_pvs = {}

RECALC_TIMER_INTERVAL_MS = 100
RECALC_TIMER_ID = 1941


class GUI(wx.App):
    '''class that runs the qToolFrame and sets up the EPICS PVs'''

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
            # TODO: for development only
            #cmd = shlex.split('caput %s.DESC "%s"' % (pv, name))
            #p = subprocess.Popen(cmd)
            #
            conn = pvConnect.EpicsPv(pv)
            conn.SetUserCallback(pv_monitor_handler)
            conn.SetUserArgs(pv)
            conn.connectw()
            conn.monitor()
            connections[pv] = conn
        #pprint.pprint(XREF)
        return True


def pv_monitor_handler(epics_args, user_args):
    '''EPICS monitor event received for this code'''
    global monitor_count
    global updated_pvs
    monitor_count += 1
    value = epics_args['pv_value']
    pv = user_args[0]
    name = XREF[pv]
    # pprint.pprint(epics_args)
    msg = "%s %s: %s(%s)=%s" % ('pv_monitor_handler', monitor_count, pv, name, value)
    #print msg
    qTool.SetStatusText(msg)
    db[name] = value
    #print "running?", qTool.timer.IsRunning()
    updated_pvs[name] = value
    #pprint.pprint(updated_pvs)
    widget_list['p_motion'].SetValue(str(monitor_count))
    if not qTool.timer.IsRunning():
        # queue the update to happen (can't call directly in callback handler)
        qTool.timer.Start(RECALC_TIMER_INTERVAL_MS)
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
          'PV,Energy,keV'       : '32ida:BraggEAO',
          'PV,Scan,Finish'      : '15iddLAX:USAXS:Finish',
          'PV,Scan,StartOffset' : '15iddLAX:USAXS:StartOffset',
          'PV,Scan,NumPoints'   : '15iddLAX:USAXS:NumPoints',
          'PV,Scan,CountTime'   : '15iddLAX:USAXS:CountTime',
          'PV,Scan,AR_center'   : '15iddLAX:USAXS:ARcenter'
        }
        # TODO: revise above list and remove list below once beamline has DCM support
        self.PV_LIST = {
          'PV,Energy,keV'       : '15iddLAX:float1',
          'PV,Scan,Q_max'       : '15iddLAX:float2',
          'PV,Scan,StartOffset' : '15iddLAX:float3',
          'PV,Scan,NumPoints'   : '15iddLAX:float4',
          'PV,Scan,CountTime'   : '15iddLAX:float5',
          'PV,Scan,AR_center'   : '15iddLAX:float6'
        }
        # these are fall-back values used to start the tool
        # they should be replaced quickly on startup by EPICS values
        db['PV,Scan,NumPoints']     = 150
        db['PV,Energy,keV']         = 11.05
        db['PV,Scan,StartOffset']     = -0.005   # was 10.523
        db['PV,Scan,Q_max']         = 1
        db['PV,Scan,CountTime'] = 5
        db['N_scans']        = 1
        db['VELO_step']     = 0.02
        db['VELO_return']   = 0.4
        db['ACCL']          = 0.2
        db['t_delay']       = 0.5
        db['t_tuning']      = 150
        db['A_keV']         = 12.3984244

        # build the GUI
        wx.Frame.__init__(self, parent=parent, id=wx.ID_ANY,
              style=wx.DEFAULT_FRAME_STYLE, title=self.TITLE)

        self.__init_statusBar__('status')
        self.__init_bsMain__(parent)
        self.SetStatusText('startup is complete')

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update, self.timer)
        self.timer.Start(RECALC_TIMER_INTERVAL_MS)

    def __del__(self):
        """ Class delete event: don't leave timer hanging around! """
        if self.timer.IsRunning():
            self.timer.Stop()
        del self.timer

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
          ['PV,Scan,NumPoints', '# of points', ''],
          ['PV,Energy,keV', 'energy', 'keV'],
          ['PV,Scan,StartOffset', 'AR_start_offset', 'degrees'],
          ['PV,Scan,Q_max', 'Q_max', '1/A'],
          ['PV,Scan,CountTime', 'count time', 'seconds'],
          ['N_scans', '# of scans', '']
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
            widget_list[name] = widget

            st = wx.StaticText(parent, wx.ID_ANY, units, style=wx.ALIGN_LEFT)
            fgs.Add(st, 0, flag=wx.EXPAND)

        config = [
          ['AR_start', 'AR start angle', 'degrees'],
          ['PV,Scan,AR_center', 'AR center angle', 'degrees'],
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
            widget_list[name] = widget

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
            widget_list[name] = widget

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
            widget_list[name] = widget

            st = wx.StaticText(parent, wx.ID_ANY, units, style=wx.ALIGN_LEFT)
            fgs.Add(st, 0, flag=wx.EXPAND)

            st = wx.TextCtrl(parent, wx.ID_ANY, pct, style=wx.ALIGN_LEFT)
            fgs.Add(st, 0, flag=wx.EXPAND)
            self.parameterList[pct] = { 'text': widget }
            st.SetToolTipString('parameter: ' + pct)
            widget_list[pct] = st

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

    def q2angle(self, q):
        '''convert Q (1/A) to degrees'''
        term = (q * db['A_keV']) / (4 * math.pi * db['PV,Energy,keV'])
        term = 2 * math.asin(term) * 180/math.pi
        #print "q=", q, "  angle=", term
        return term

    def s2HMS(self, seconds):
        '''convert seconds to H:M:S format'''
        f = seconds - int(seconds)
        s = int(seconds) % 60
        m = int(seconds/60) % 60
        h = int(seconds/60/60)
        return "%d:%02d:%02d" % (h, m, s)

    def update(self, event):
        '''responds to wx Event: recalculate and update the widgets when self.timer calls us'''
        global update_count
        update_count += 1
        self.timer.Stop()
        self.timer.Stop()
        self.recalc()
        self.fillWidgets()
        widget_list['p_count'].SetValue(str(update_count))
        #print "update", update_count

    def fillWidgets(self):
        '''place values in the widgets'''
        for name in db:
            if name in widget_list:
                widget = widget_list[name]
                text = str(db[name])
                #print "fill: ", name, text
                widget.SetValue(text)

    def recalc(self):
        '''
            recalculate the various values

             # starting and ending AR positions
             set db(AR_start) [expr $db(PV,Scan,StartOffset) + $db(PV,Scan,AR_center)]
             set db(AR_end)   [expr $db(PV,Scan,AR_center) - 2*asin( $db(PV,Scan,Q_max)*$db(A_keV)/(4 * $db(pi) * $db(PV,Energy,keV))  ) * (180/$db(pi))]
             # estimate the time to complete the set of scans here
             set db(s_motion) [expr abs($db(AR_start)-$db(AR_end))/$db(VELO_step)]
             set db(s_accl)   [expr 2*$db(ACCL)*$db(PV,Scan,NumPoints)]
             set db(s_delay)  [expr $db(t_delay)*$db(PV,Scan,NumPoints)]
             set db(s_count)  [expr $db(PV,Scan,CountTime)*$db(PV,Scan,NumPoints)]
             set db(s_return) [expr abs($db(AR_start)-$db(AR_end))/$db(VELO_return)]
             set db(s_scan)   [expr $db(s_motion)+$db(s_accl)+$db(s_delay)+$db(s_count)+$db(s_return)]
             set db(s_series) [expr ($db(s_scan)+$db(t_tuning))*$db(N_scans)]
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
        global widget_list
        global updated_pvs
        global db
        wlist = [
            'ACCL',
            'N_scans',
            'PV,Energy,keV',
            'PV,Scan,AR_center',
            'PV,Scan,CountTime',
            'PV,Scan,NumPoints',
            'PV,Scan,Q_max',
            'PV,Scan,StartOffset',
            't_delay',
            't_tuning',
            'VELO_return',
            'VELO_step',
        ]
        try:
            # first, grab non-EPICS widget values before calculating
            for item in wlist:
                db[item] = float(widget_list[item].GetValue())
            wlist = []

            # next, grab any new updates from EPICS
            for item in updated_pvs:
                db[item] = updated_pvs[item]
                if item in widget_list:
                    widget_list[item].SetValue(str(db[item]))
            updated_pvs = {}    # empty the update list now

            ########################
            # recalculate the values
            ########################

            # starting and ending AR positions
            db['AR_start'] = db['PV,Scan,StartOffset'] + db['PV,Scan,AR_center']
            wlist.append('AR_start')

            db['AR_end'] = db['PV,Scan,AR_center'] - self.q2angle( db['PV,Scan,Q_max'] )
            wlist.append('AR_end')

            # estimate the time to complete the set of scans here
            db['s_motion'] = math.fabs(db['AR_start']-db['AR_end'])/db['VELO_step']
            wlist.append('s_motion')

            db['s_accl'] = 2 * db['ACCL'] * db['PV,Scan,NumPoints']
            wlist.append('s_accl')

            db['s_delay'] = db['t_delay'] * db['PV,Scan,NumPoints']
            wlist.append('s_delay')

            db['s_count'] = db['PV,Scan,CountTime'] * db['PV,Scan,NumPoints']
            wlist.append('s_count')

            db['s_return'] = math.fabs(db['AR_start']-db['AR_end'])/db['VELO_return']
            wlist.append('s_return')

            seconds = 0
            for item in ['s_motion', 's_accl', 's_delay', 's_count', 's_return']:
                seconds += db[item]
            db['s_scan'] = seconds
            wlist.append('s_scan')

            db['s_series'] = (db['s_scan'] + db['t_tuning']) * db['N_scans']
            wlist.append('s_series')

            db['s_scan_HMS'] = self.s2HMS(db['s_scan'])
            wlist.append('s_scan_HMS')

            db['s_HMS'] = self.s2HMS(db['s_series'])
            wlist.append('s_HMS')

            # last, update the widgets with the newly-calculated values
            for item in wlist:
                widget_list[item].SetValue(str(db[item]))

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
