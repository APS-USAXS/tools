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

@TODO: make a bargraph behind the percentage widgets to show fractional time in each row
@TODO: make an event log
'''


import datetime
import math
import os
import pprint
import shlex
import subprocess
import wx
from xml.dom import minidom
from xml.etree import ElementTree
import pvConnect

connections = {}  # EPICS Channel Access connections, key is PV name
XREF = {}         # key is PV name, value is descriptive name
db = {}           # values, key is descriptive name
widget_list = {}  # widgets with values to get or set
type_list = {}    # ['int', 'float', 'string'] for each widget
qTool = None      # pointer to the GUI
update_count = 0  # number of recalculation events
monitor_count = 0 # number of EPICS monitor events
TIP_STR_FMT = "parameter: %s\npress [ENTER] to commit a new value"

RECALC_TIMER_INTERVAL_MS = 100
RECALC_TIMER_ID = 1941
TYPE_FORMATS = {'int' : '%d', 'float': '%g', 'string': '%s'}


class GUI(wx.App):
    '''class that runs the qToolFrame and sets up the EPICS PVs'''

    def OnInit(self):
        '''run the GUI, always returns True'''
        global qTool
        # prepare ChannelAccess support
        if pvConnect.IMPORTED_CACHANNEL:
            capoll_timer = pvConnect.CaPollWx(0.1)
            capoll_timer.start()

        # build the GUI now
        qTool = qToolFrame(None)
        qTool.Show()
        self.SetTopWindow(qTool)

        # connect with EPICS now
        for name in qTool.PV_LIST:
            pv = qTool.PV_LIST[name]
            XREF[pv] = name
            #
            conn = pvConnect.EpicsPv(pv)
            conn.SetUserCallback(pv_monitor_handler)
            conn.SetUserArgs(pv)
            conn.connectw()
            conn.monitor()
            connections[pv] = conn

        # queue an update to the calculated values
        if not qTool.timer.IsRunning():
            qTool.timer.Start(RECALC_TIMER_INTERVAL_MS)
        return True


def pv_monitor_handler(epics_args, user_args):
    '''EPICS monitor event received for this code'''
    global monitor_count
    monitor_count += 1
    value = epics_args['pv_value']
    pv = user_args[0]
    name = XREF[pv]
    db[name] = value
    msg = "%s %s: %s(%s)=%s" % ('pv_monitor_handler', monitor_count, pv, name, value)
    qTool.SetStatusText(msg)
    return True


class qToolFrame(wx.Frame):
    '''define and operate the GUI'''

    def __init__(self, parent):
        '''create the GUI'''

        # define some things for the program
        self.TITLE = u'USAXS scan time calculator'
        self.SVN_ID = "$Id$"
        self.GRAY = wx.ColorRGB(0xababab)
        self.MOVING_COLOR = wx.GREEN
        self.NOT_MOVING_COLOR = wx.LIGHT_GREY
        self.LIGHTBLUE = wx.ColorRGB(0xffddcc)
        self.BISQUE = wx.ColorRGB(0xaaddee)
        self.MINTCREAM = wx.ColorRGB(0xe5ffea)
        self.COLOR_CALCULATED = self.LIGHTBLUE
        self.COLOR_EPICS_MONITOR = self.LIGHTBLUE
        self.COLOR_USER_ENTRY = self.BISQUE
        self.USER_HOME = os.getenv('USERPROFILE') or os.getenv('HOME') # windows or Linux/Mac
        self.RC_FILE = os.path.join(self.USER_HOME, '.scanTimeCalcrc')
        self.PV_LIST = {
          'PV,Energy,keV'       : '32ida:BraggEAO',
          'PV,Scan,Q_max'       : '15iddLAX:USAXS:Finish',
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
        db['GUI,N']             = 150
        db['GUI,energy']        = 11.05
        db['GUI,StartOffset']   = -0.005   # was 10.523
        db['GUI,Q_max']         = 1
        db['GUI,CountTime']     = 5
        db['GUI,AR_center']     = 13.0
        db['N_scans']           = 1
        db['VELO_step']         = 0.02
        db['VELO_return']       = 0.4
        db['ACCL']              = 0.2
        db['t_delay']           = 0.5
        db['t_tuning']          = 150
        db['A_keV']             = 12.3984244

        # build the GUI
        wx.Frame.__init__(self, parent=parent, id=wx.ID_ANY,
              style=wx.DEFAULT_FRAME_STYLE, title=self.TITLE)

        self.__init_statusBar__('status')
        self.__init_bsMain__(parent)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update, self.timer)
        
        self.read_rcfile()
        self.SetStatusText('startup is complete')

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
          ['GUI,N', '# of points', '', 'int'],
          ['GUI,energy', 'energy', 'keV', 'float'],
          ['GUI,StartOffset', 'AR_start_offset', 'degrees', 'float'],
          ['GUI,Q_max', 'Q_max', '1/A', 'float'],
          ['GUI,CountTime', 'count time', 'seconds', 'float'],
          ['N_scans', '# of scans', '', 'int']
        ]
        sbox = wx.StaticBox(parent, id=wx.ID_ANY,
              label='user parameters', style=0)
        sbs = wx.StaticBoxSizer(sbox, wx.VERTICAL)
        fgs = wx.FlexGridSizer(rows=len(config), cols=3, hgap=10, vgap=5)

        self.parameterList = {}
        for row in config:
            name, desc, units, type = row
            st = wx.StaticText(parent, wx.ID_ANY, desc, style=wx.ALIGN_RIGHT)
            fgs.Add(st, 0, flag=wx.EXPAND)

            widget = wx.TextCtrl(parent, wx.ID_ANY, "", 
                                 style=wx.SUNKEN_BORDER|wx.TE_PROCESS_ENTER)
            widget.SetBackgroundColour(self.COLOR_USER_ENTRY)
            widget.SetToolTipString(TIP_STR_FMT % name)
            fgs.Add(widget, 1, wx.EXPAND|wx.ALL)
            widget.Bind(wx.EVT_TEXT_ENTER, self.OnEnterKey)
            self.parameterList[name] = { 'entry': widget }
            widget_list[name] = widget
            type_list[name] = type

            st = wx.StaticText(parent, wx.ID_ANY, units, style=wx.ALIGN_LEFT)
            fgs.Add(st, 0, flag=wx.EXPAND)

        config = [
          ['AR_start', 'AR start angle', 'degrees', 'float'],
          ['GUI,AR_center', 'AR center angle', 'degrees', 'float'],
          ['AR_end', 'AR end angle', 'degrees', 'float']
        ]
        fgs.SetRows(fgs.GetRows() + len(config))
        for row in config:
            name, desc, units, type = row
            st = wx.StaticText(parent, wx.ID_ANY, desc, style=wx.ALIGN_RIGHT)
            fgs.Add(st, 0, flag=wx.EXPAND)

            widget = wx.TextCtrl(parent, wx.ID_ANY, "", 
                                 style=wx.SIMPLE_BORDER|wx.TE_PROCESS_ENTER)
            widget.SetToolTipString(TIP_STR_FMT % name)
            widget.SetBackgroundColour(self.COLOR_EPICS_MONITOR)
            fgs.Add(widget, 1, wx.EXPAND)
            widget.Bind(wx.EVT_TEXT_ENTER, self.OnEnterKey)
            self.parameterList[name] = { 'entry': widget }
            widget_list[name] = widget
            type_list[name] = type

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
        self.Bind(wx.EVT_BUTTON, self.OnCopyButton, button)

        return button


    def __init_others__(self, parent):
        '''
            create the table of other user parameters,
            defines otherList dictionary,
            returns container object
        '''
        config = [
          ['VELO_step', 'AR step-scan speed', 'degrees/second', 'float'],
          ['VELO_return', 'AR return speed', 'degrees/second', 'float'],
          ['ACCL', 'AR acceleration time', 'seconds', 'float'],
          ['t_delay', 'delay time/point', 'seconds', 'float'],
          ['t_tuning', 'tuning and dark current time', 'seconds', 'float']
        ]
        sbox = wx.StaticBox(parent, id=wx.ID_ANY,
              label='other user parameters', style=0)
        sbs = wx.StaticBoxSizer(sbox, wx.VERTICAL)
        fgs = wx.FlexGridSizer(rows=len(config), cols=3, hgap=10, vgap=5)

        self.otherList = {}

        for row in config:
            name, desc, units, type = row
            st = wx.StaticText(parent, wx.ID_ANY, desc, style=wx.ALIGN_RIGHT)
            fgs.Add(st, 0, flag=wx.EXPAND)

            widget = wx.TextCtrl(parent, wx.ID_ANY, "", 
                                 style=wx.SUNKEN_BORDER|wx.TE_PROCESS_ENTER)
            widget.SetBackgroundColour(self.COLOR_USER_ENTRY)
            widget.SetToolTipString(TIP_STR_FMT % name)
            fgs.Add(widget, 1, wx.EXPAND)
            widget.Bind(wx.EVT_TEXT_ENTER, self.OnEnterKey)
            self.parameterList[name] = { 'entry': widget }
            widget_list[name] = widget
            type_list[name] = type

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
          ['s_motion', 'AR motor step time', 'seconds', 'p_motion', 'float'],
          ['s_count', 'counting time', 'seconds', 'p_count', 'float'],
          ['s_delay', 'delay time', 'seconds', 'p_delay', 'float'],
          ['s_accl', 'AR motor acceleration time', 'seconds', 'p_accl', 'float'],
          ['s_return', 'AR motor return time', 'seconds', 'p_return', 'float'],
          ['s_scan', 'one sample scan time', 'seconds/scan', 's_scan_HMS', 'float'],
          ['s_series', 'total time complete series', 'seconds/series', 's_HMS', 'float']
        ]
        sbox = wx.StaticBox(parent, id=wx.ID_ANY,
              label='calculated values', style=0)
        sbs = wx.StaticBoxSizer(sbox, wx.VERTICAL)
        fgs = wx.FlexGridSizer(rows=len(config), cols=4, hgap=10, vgap=5)

        self.resultsList = {}

        for row in config:
            name, desc, units, pct, type = row
            st = wx.StaticText(parent, wx.ID_ANY, desc, style=wx.ALIGN_RIGHT)
            fgs.Add(st, 0, flag=wx.EXPAND)

            widget = wx.TextCtrl(parent, wx.ID_ANY, "", 
                                 style=wx.SUNKEN_BORDER|wx.TE_READONLY)
            widget.SetBackgroundColour(self.COLOR_CALCULATED)
            widget.SetToolTipString('parameter: ' + name)
            fgs.Add(widget, 1, wx.EXPAND)
            widget.Bind(wx.EVT_TEXT_ENTER, self.OnEnterKey)
            self.parameterList[name] = { 'entry': widget }
            widget_list[name] = widget
            type_list[name] = type

            st = wx.StaticText(parent, wx.ID_ANY, units, style=wx.ALIGN_LEFT)
            fgs.Add(st, 0, flag=wx.EXPAND)

            st = wx.TextCtrl(parent, wx.ID_ANY, pct, 
                             style=wx.ALIGN_LEFT|wx.TE_READONLY)
            fgs.Add(st, 0, flag=wx.EXPAND)
            self.parameterList[pct] = { 'text': widget }
            st.SetToolTipString('parameter: ' + pct)
            widget_list[pct] = st
            type_list[pct] = 'string'

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

    def read_rcfile(self):
        '''
            reads the resource configuration file
            writes the widget fields
        '''
        global db
        global type_list
        if os.path.exists(self.RC_FILE):
            tree = ElementTree.parse(self.RC_FILE)
            keys = tree.findall("//data")   # use XPATH reference
            for key in keys:
                name = key.get("name")
                value = str(key.findtext('widget_list')).strip()
                if name in widget_list:
                    widget_list[name].SetValue(value)
                if name in type_list:
                    if type_list[name] == 'int':   value = int(value)
                    if type_list[name] == 'float': value = float(value)
                    db[name] = value

            self.SetStatusText('loaded settings from: ' + self.RC_FILE)

    def save_rcfile(self, event):
        '''
            reads the widget fields
            writes the resource configuration file
        '''
        f = open(self.RC_FILE, 'w')
        f.write(repr(self))
        f.close()
        self.SetStatusText('saved settings in: ' + self.RC_FILE)

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

        root = ElementTree.Element("scanTimeCalc")
        root.set("version", "2.0")
        root.set("date", yyyymmdd)
        root.set("time", hhmmss)
        root.append(ElementTree.Comment("written by: " + self.SVN_ID))
        #root.append(ElementTree.ProcessingInstruction("example ProcessingInstruction()"))

        # build list of items to be recorded
        # TODO: Is there a faster, simpler method to do this?
        master = {}
        for item in widget_list:
            master[item] = 1
        for item in db:
            master[item] = 2
        keys = master.keys()
        keys.sort()
        # add the items to the XML structure
        for item in keys:
            node = ElementTree.SubElement(root, "data")
            node.set("name", item)
            if item in widget_list:
                subnode = ElementTree.SubElement(node, "widget_list")
                subnode.text = widget_list[item].GetValue()
            if item in db:
                node.set("db", str(db[item]))
            if item in self.PV_LIST:
                node.set("pv", str(self.PV_LIST[item]))

        return self.MakePrettyXML(root)

    def q2angle(self, q):
        '''convert Q (1/A) to degrees'''
        term = (q * db['A_keV']) / (4 * math.pi * db['GUI,energy'])
        term = 2 * math.asin(term) * 180/math.pi
        return term

    def s2HMS(self, seconds):
        '''convert seconds to H:MM:SS format'''
        f = seconds - int(seconds)
        s = int(seconds) % 60
        m = int(seconds/60) % 60
        h = int(seconds/60/60)
        return "%d:%02d:%02d" % (h, m, s)

    def OnEnterKey(self, event):
        '''responds to wx Event: enter key pressed in wx.TextCtrl()'''
        self.SetStatusText("enter key pressed: " + str(event))
        if not self.timer.IsRunning():
            # queue an update to happen
            self.timer.Start(RECALC_TIMER_INTERVAL_MS)
        event.Skip()

    def OnCopyButton(self, event):
        '''responds to wx Event: copies EPICS PVs from cache to user variables'''
        map = {
          'PV,Energy,keV'       : 'GUI,energy',
          'PV,Scan,Q_max'       : 'GUI,Q_max',
          'PV,Scan,StartOffset' : 'GUI,StartOffset',
          'PV,Scan,NumPoints'   : 'GUI,N',
          'PV,Scan,CountTime'   : 'GUI,CountTime',
          'PV,Scan,AR_center'   : 'GUI,AR_center'
        }
        wlist = []
        for key in map:
            #print key, db[map[key]], db[key]
            db[map[key]] = db[key]
            wlist.append(map[key])
        self.SetStatusText("EPICS --> local")

        # last, update the widgets with the EPICS values
        for key in wlist:
            text = str(db[key])
            if key in type_list:
                text = TYPE_FORMATS[type_list[key]] % db[key]
            widget_list[key].SetValue(text)
        self.update(event)
        event.Skip()

    def update(self, event):
        '''responds to wx Event: recalculate and update the widgets when called'''
        global update_count
        update_count += 1
        self.SetStatusText("update #%d" % update_count)
        self.timer.Stop()
        self.recalc()

        #place values in the widgets
        for item in db:
            if item in widget_list:
                widget = widget_list[item]
                text = str(db[item])
                if item in type_list:
                    text = TYPE_FORMATS[type_list[item]] % db[item]
                widget.SetValue(text)

    def recalc(self):
        '''
            recalculate the various values
        '''
        global db
        global widget_list
        wlist = [
            'ACCL',
            'GUI,CountTime',
            'GUI,energy',
            'GUI,N',
            'GUI,Q_max',
            'GUI,StartOffset',
            'N_scans',
            'GUI,AR_center',
            't_delay',
            't_tuning',
            'VELO_return',
            'VELO_step',
        ]
        try:
            # first, grab non-EPICS widget values before calculating
            for item in wlist:
                value = widget_list[item].GetValue()
                if type_list[item] == 'int':
                    value = int(value)
                if type_list[item] == 'float':
                    value = float(value)
                db[item] = value
            wlist = []

            ########################
            # recalculate the values
            ########################

            # starting and ending AR positions
            db['AR_start'] = db['GUI,StartOffset'] + db['GUI,AR_center']
            wlist.append('AR_start')

            db['AR_end'] = db['GUI,AR_center'] - self.q2angle( db['GUI,Q_max'] )
            wlist.append('AR_end')

            # estimate the time to complete the set of scans here
            db['s_motion'] = math.fabs(db['AR_start']-db['AR_end'])/db['VELO_step']
            wlist.append('s_motion')

            db['s_accl'] = 2 * db['ACCL'] * db['GUI,N']
            wlist.append('s_accl')

            db['s_delay'] = db['t_delay'] * db['GUI,N']
            wlist.append('s_delay')

            db['s_count'] = db['GUI,CountTime'] * db['GUI,N']
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

            # percentage of total time in each activity
            db['p_motion'] = "%.2f%%" % (db['s_motion'] * 100/db['s_scan'])
            wlist.append('p_motion')

            db['p_accl'] = "%.2f%%" % (db['s_accl']   * 100/db['s_scan'])
            wlist.append('p_accl')

            db['p_delay'] = "%.2f%%" % (db['s_delay']  * 100/db['s_scan'])
            wlist.append('p_delay')

            db['p_count'] = "%.2f%%" % (db['s_count']  * 100/db['s_scan'])
            wlist.append('p_count')

            db['p_return'] = "%.2f%%" % (db['s_return'] * 100/db['s_scan'])
            wlist.append('p_return')

            # last, update the widgets with the newly-calculated values
            for item in wlist:
                text = str(db[item])
                if item in type_list:
                    itemtype = type_list[item]
                    fmt = TYPE_FORMATS[itemtype]
                    text = fmt % db[item]
                if item in widget_list:
                    widget_list[item].SetValue(text)

            tester = widget_list['AR_start'].GetValue()
            if len(tester) > 0:
                # only write this if AR_start has some value
                self.save_rcfile(None)  # save to the RC file

        except:
            pass


def on_exit(timer, epics_db):
    '''Exit handler to stop the ca.poll()
        @param timer: CaPollWx object
        @param epics_db: Python list of pvConnect.EpicsPv objects to be released'''
    if pvConnect.IMPORTED_CACHANNEL:
        pvConnect.on_exit(timer)


if __name__ == '__main__':
    capoll_timer = None
    GUI(0).MainLoop()
    on_exit(capoll_timer, None)
