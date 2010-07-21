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

@TODO: make an event log (preparation is started: logs to stdout)
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


XREF = {}         # key is PV name, value is descriptive name
stcTool = None    # pointer to the GUI


class scanTimeCalcToolFrame(wx.Frame):
    '''define and operate the GUI'''

    def __init__(self, parent):
        '''create the GUI'''

        # define some things for the program
        self.TOOL = u'scanTimeCalc'
        self.TITLE = u'USAXS scan time calculator'
        self.SVN_ID = "$Id$"
        self.PRINT_LOG = False

        self.db = {}           # values, key is descriptive name
        self.type_list = {}    # ['int', 'float', 'string'] for each widget
        self.widget_list = {}  # widgets with values to get or set

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
        self.RECALC_TIMER_INTERVAL_MS = 100
        self.TYPE_FORMATS = {'int' : '%d', 'float': '%g', 'string': '%s'}
        self.TIP_STR_FMT = "parameter: %s\npress [ENTER] to commit new values and recalculate"
        self.monitor_count = 0 # number of EPICS monitor events
        self.update_count = 0  # number of recalculation events
        self.PV_LIST = {
          'PV,Energy,keV'       : '15ida:BraggEAO',
          'PV,Scan,Q_max'       : '15iddLAX:USAXS:Finish',
          'PV,Scan,StartOffset' : '15iddLAX:USAXS:StartOffset',
          'PV,Scan,NumPoints'   : '15iddLAX:USAXS:NumPoints',
          'PV,Scan,CountTime'   : '15iddLAX:USAXS:CountTime',
          'PV,Scan,AR_center'   : '15iddLAX:USAXS:ARcenter'
        }
        self.PV_LIST['PV,Energy,keV'] = '15iddLAX:float1'   # TODO: revise once beamline has DCM
        # these are fall-back values used to start the tool
        # they should be replaced quickly on startup by EPICS values
        self.db['GUI,N']             = 150
        self.db['GUI,energy']        = 11.05
        self.db['GUI,StartOffset']   = -0.005   # was 10.523
        self.db['GUI,Q_max']         = 1
        self.db['GUI,CountTime']     = 5
        self.db['GUI,AR_center']     = 13.0
        self.db['N_scans']           = 1
        self.db['VELO_step']         = 0.02
        self.db['VELO_return']       = 0.4
        self.db['ACCL']              = 0.2
        self.db['t_delay']           = 0.5
        self.db['t_tuning']          = 150
        self.db['A_keV']             = 12.3984244

        # build the GUI
        wx.Frame.__init__(self, parent=parent, id=wx.ID_ANY,
              style=wx.DEFAULT_FRAME_STYLE, title=self.TITLE)

        self.CreateStatusBar()
        self.__init_bsMain__(parent)
        self.postMessage('starting: ' + self.SVN_ID)
        self.postMessage('GUI created')

        w = self.widget_list['GUI,energy']     # GUI,energy
        w.SetToolTipString(
            "TODO: revise energy PV once beamline has DCM\n"
             + "============================================\n"
             + w.GetToolTip().GetTip()
        )

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update, self.timer)

        self.read_rcfile()
        self.postMessage('startup is complete')

    def __del__(self):
        """ Class delete event: don't leave timer hanging around! """
        if self.timer.IsRunning():
            self.timer.Stop()
        del self.timer

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
            widget.SetToolTipString(self.TIP_STR_FMT % name)
            fgs.Add(widget, 1, wx.EXPAND|wx.ALL)
            widget.Bind(wx.EVT_TEXT_ENTER, self.OnEnterKey)
            self.parameterList[name] = { 'entry': widget }
            self.widget_list[name] = widget
            self.type_list[name] = type

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
            widget.SetToolTipString(self.TIP_STR_FMT % name)
            widget.SetBackgroundColour(self.COLOR_EPICS_MONITOR)
            fgs.Add(widget, 1, wx.EXPAND)
            widget.Bind(wx.EVT_TEXT_ENTER, self.OnEnterKey)
            self.parameterList[name] = { 'entry': widget }
            self.widget_list[name] = widget
            self.type_list[name] = type

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
            widget.SetToolTipString(self.TIP_STR_FMT % name)
            fgs.Add(widget, 1, wx.EXPAND)
            widget.Bind(wx.EVT_TEXT_ENTER, self.OnEnterKey)
            self.parameterList[name] = { 'entry': widget }
            self.widget_list[name] = widget
            self.type_list[name] = type

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
            widget.SetToolTipString('parameter: ' + name + '\ncalculated (read-only)')
            fgs.Add(widget, 1, wx.EXPAND)
            widget.Bind(wx.EVT_TEXT_ENTER, self.OnEnterKey)
            self.parameterList[name] = { 'entry': widget }
            self.widget_list[name] = widget
            self.type_list[name] = type

            st = wx.StaticText(parent, wx.ID_ANY, units, style=wx.ALIGN_LEFT)
            fgs.Add(st, 0, flag=wx.EXPAND)

            st = wx.TextCtrl(parent, wx.ID_ANY, pct,
                             style=wx.ALIGN_LEFT|wx.TE_READONLY)
            fgs.Add(st, 0, flag=wx.EXPAND)
            self.parameterList[pct] = { 'text': widget }
            st.SetToolTipString('parameter: ' + pct + '\ncalculated (read-only)')
            self.widget_list[pct] = st
            self.type_list[pct] = 'string'

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
            reads the resource configuration file (XML)
            writes the widget fields
        '''
        if os.path.exists(self.RC_FILE):
            try:
                tree = ElementTree.parse(self.RC_FILE)
            except:
                self.postMessage('could not parse RC_FILE: ' + self.RC_FILE)
                return

            for key in tree.findall("//data"):
                name = key.get("name")
                value = key.get("value")
                if name in self.widget_list:
                    self.widget_list[name].SetValue(value)

            self.postMessage('loaded settings from: ' + self.RC_FILE)
        else:
            self.postMessage('RC_FILE does not exist: ' + self.RC_FILE)

    def save_rcfile(self, event):
        '''
            reads the widget fields
            writes the resource configuration file (XML)
        '''
        output = repr(self)
        if len(output) > 0:
            f = open(self.RC_FILE, 'w')
            f.write(output)
            f.close()
            self.postMessage('saved settings in: ' + self.RC_FILE)
        else:
            self.postMessage('internal ERROR: len(output)==0, will not write RC_FILE')

    def MakePrettyXML(self, raw):
        '''
            make the XML look pretty to the eyes
        '''
        doc = minidom.parseString(ElementTree.tostring(raw))
        return doc.toprettyxml(indent = "  ")

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

    def __repr__(self):
        '''
            default representation of memory-resident data
        '''
        yyyymmdd = self.yyyymmdd()
        hhmmss = self.hhmmss()

        root = ElementTree.Element("scanTimeCalc")
        root.set("version", "2.0")
        root.set("date", yyyymmdd)
        root.set("time", hhmmss)
        root.append(ElementTree.Comment("written by: " + self.SVN_ID))
        #root.append(ElementTree.ProcessingInstruction("example ProcessingInstruction()"))

        # build list of items to be recorded
        keylist = sorted(set(self.widget_list.keys() + self.db.keys()))

        # add the items to the XML structure
        for item in keylist:
            node = ElementTree.SubElement(root, "data")
            node.set("name", item)
            if item == "A_keV":     # special case, show the constant
                 node.set("value_constant", str(self.db[item]))
            if item in self.widget_list:
                node.set("value", self.widget_list[item].GetValue())
            if item in self.PV_LIST:
                node.set("pv", str(self.PV_LIST[item]))
                if item in self.db:
                    node.set("pv_VAL", str(self.db[item]))

        return self.MakePrettyXML(root)

    def q2angle(self, q):
        '''convert Q (1/A) to degrees'''
        db = self.db
        term = (q * db['A_keV']) / (4 * math.pi * db['GUI,energy'])
        term = 2 * math.asin(term) * 180/math.pi
        return term

    def s2HMS(self, seconds):
        '''convert seconds to H:MM:SS format'''
        #f = seconds - int(seconds)
        s = int(seconds) % 60
        m = int(seconds/60) % 60
        h = int(seconds/60/60)
        return "%d:%02d:%02d" % (h, m, s)

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

    def OnEnterKey(self, event):
        '''responds to wx Event: enter key pressed in wx.TextCtrl()'''
        if not self.timer.IsRunning():
            # queue an update to happen
            self.timer.Start(self.RECALC_TIMER_INTERVAL_MS)
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
            if (map[key] in self.db) and (key in self.db):
                self.db[map[key]] = self.db[key]
                wlist.append(map[key])

        if len(wlist) == 0:
            self.postMessage("no values to copy from EPICS --> local")
        else:
            # last, update the widgets with the EPICS values
            # but only if something has been copied
            self.postMessage("EPICS --> local")
            for key in wlist:
                text = str(self.db[key])
                if key in self.type_list:
                    text = self.TYPE_FORMATS[self.type_list[key]] % self.db[key]
                self.widget_list[key].SetValue(text)
            self.update(event)
            event.Skip()

    def update(self, event):
        '''responds to wx Event: recalculate and update the widgets when called'''
        self.update_count += 1
        self.postMessage("update #%d" % self.update_count)
        self.timer.Stop()
        self.recalc()

        #place values in the widgets
        keyList = self.db.keys()
        keyList.sort()
        for item in keyList:
            if item in self.widget_list:
                widget = self.widget_list[item]
                text = str(self.db[item])
                if item in self.type_list:
                    text = self.TYPE_FORMATS[self.type_list[item]] % self.db[item]
                widget.SetValue(text)

        tester = self.widget_list['AR_start'].GetValue()
        if len(tester) > 0:
            # only write this if AR_start has some value
            self.save_rcfile(None)  # save to the RC file

    def recalc(self):
        '''
            recalculate the various values
        '''
        db = self.db
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
                value = self.widget_list[item].GetValue()
                if self.type_list[item] == 'int':
                    value = int(value)
                if self.type_list[item] == 'float':
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

        except:
            message = "recalc:\t Error: " + sys.exc_info()[1]
            self.postMessage(message)


def pv_monitor_handler(epics_args, user_args):
    '''EPICS monitor event received for this code'''
    stcTool.monitor_count += 1
    value = epics_args['pv_value']
    pv = user_args[0]
    name = XREF[pv]
    stcTool.db[name] = value
    msg = "%s %s: %s(%s)=%s" % ('pv_monitor_handler', stcTool.monitor_count, pv, name, value)
    stcTool.postMessage(msg)
    return True


def on_exit(timer):
    '''
        Exit handler to stop the ca.poll()
        @param timer: CaPollWx object
    '''
    if pvConnect.IMPORTED_CACHANNEL:
        pvConnect.on_exit(timer)


def main():
    '''
        this routine sets up the GUI program,
        starts the EPICS connections,
        runs the GUI,
        then buttons things up at the end
    '''
    global stcTool

    # start wx
    app = wx.PySimpleApp()

    # prepare ChannelAccess support
    if pvConnect.IMPORTED_CACHANNEL:
        capoll_timer = pvConnect.CaPollWx(0.1)
        capoll_timer.start()

    # build the GUI
    stcTool = scanTimeCalcToolFrame(None)
    stcTool.Show(True)

    connections = {}  # EPICS Channel Access connections, key is PV name
    try:
        # connect with EPICS now
        for name in stcTool.PV_LIST:
            pv = stcTool.PV_LIST[name]
            XREF[pv] = name
            #
            conn = pvConnect.EpicsPv(pv).MonitoredConnection(pv_monitor_handler)
            connections[pv] = conn
        stcTool.postMessage("EPICS connections established")
    except:
        stcTool.postMessage("Problems establishing connections with EPICS")

    # queue an update to the calculated values
    if not stcTool.timer.IsRunning():
        stcTool.timer.Start(stcTool.RECALC_TIMER_INTERVAL_MS)

    # run the GUI
    app.MainLoop()
    if pvConnect.IMPORTED_CACHANNEL:
        on_exit(capoll_timer)


if __name__ == '__main__':
    main()
