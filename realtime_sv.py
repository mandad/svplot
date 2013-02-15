"""
Damian Manda <damian.manda@noaa.gov>
06 Feb 2013
Some WxWindows code based on John Bender, CWRU, 10 Sep 08
"""

import matplotlib
matplotlib.interactive(True)
matplotlib.use('WXAgg')

import numpy as np
import wx
import time
import threading
import resoncom
import hypackcom
from svplot import calc_scaling_limits

class SVFrame(wx.Frame):
    """Define the fram into which the graph canvas is inserted"""
    title = 'Surface Sound Speed Map'
    
    def __init__(self):
        wx.Frame.__init__(self, None, -1, self.title, size=(600,600))
        
        # Set Up Menu
        self.menu_bar = wx.MenuBar( 0 )
        self.run_menu = wx.Menu()
        self.run_start = wx.MenuItem( self.run_menu, wx.ID_ANY, u"Start", wx.EmptyString, wx.ITEM_NORMAL )
        self.run_menu.AppendItem(self.run_start)
        self.Bind(wx.EVT_MENU, self.start_comm, id = self.run_start.GetId())
        
        self.run_stop = wx.MenuItem(self.run_menu, wx.ID_ANY, u"Stop", wx.EmptyString, wx.ITEM_NORMAL)
        self.run_menu.AppendItem(self.run_stop)
        self.Bind(wx.EVT_MENU, self.stop_comm, id = self.run_stop.GetId())
        
        self.menu_bar.Append(self.run_menu, u"Run") 
        self.SetMenuBar(self.menu_bar)
        
        # Set up panel
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel = UpdatePlotPanel(self)
        sizer.Add( self.panel, 1, wx.EXPAND |wx.ALL, 5 )

        self.SetSizer(sizer)
        self.Layout()
        self.Centre(wx.BOTH)

        # Set Up Other events
        self.Bind( wx.EVT_CLOSE, self._on_close )
        # self.counter = 0
        # self.redraw_timer = wx.Timer(self)
        # self.Bind(wx.EVT_TIMER, self.stop_comm, self.redraw_timer)
        # self.redraw_timer.Start(1000, True)

        # wx.CallAfter(self.start_comm)
        self.comm_manager = CommunicationManager(self.panel, '192.168.0.101', 9888)

    def start_comm(self, event = None):
        self.comm_manager.start_communication()

    def stop_comm(self, event):
        self.comm_manager.stop_communication()

    def _on_close(self, event):
        with threading.Lock():
            if self.comm_manager.comm_active:
                self.comm_manager.stop_communication()
            self.Destroy()

class PlotPanel(wx.Panel):
    """The PlotPanel has a Figure and a Canvas. OnSize events simply set a 
    flag, and the actual resizing of the figure is triggered by an Idle event."""
    def __init__(self, parent, color=None, dpi=None, **kwargs):
        from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
        from matplotlib.figure import Figure

        self.parent = parent

        # initialize Panel
        if 'id' not in kwargs.keys():
            kwargs['id'] = wx.ID_ANY
        if 'style' not in kwargs.keys():
            kwargs['style'] = wx.NO_FULL_REPAINT_ON_RESIZE
        wx.Panel.__init__(self, parent, **kwargs)

        # initialize matplotlib stuff
        self.figure = Figure(None, dpi)
        self.canvas = FigureCanvasWxAgg(self, -1, self.figure)
        self.SetColor(color) 

        self._SetSize()
        self.initial_draw()

        self._resizeflag = False
        self._redrawflag = False

        self.Bind(wx.EVT_IDLE, self._onIdle)
        self.Bind(wx.EVT_SIZE, self._onSize)

    def SetColor(self, rgbtuple=None):
        """Set figure and canvas colours to be the same."""
        if rgbtuple is None:
            rgbtuple = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get()
        clr = [c/255. for c in rgbtuple]
        self.figure.set_facecolor(clr)
        self.figure.set_edgecolor(clr)
        self.canvas.SetBackgroundColour(wx.Colour(*rgbtuple))

    def _onSize(self, event):
        self._resizeflag = True

    def _onIdle(self, evt):
        if self._resizeflag:
            self._resizeflag = False
            self._SetSize()
        if self._redrawflag:
            self._redrawflag = False
            self.canvas.draw()

    def _SetSize(self):
        pixels = tuple(self.parent.GetClientSize())
        self.SetSize(pixels)
        self.canvas.SetSize(pixels)
        self.figure.set_size_inches(float(pixels[0])/self.figure.get_dpi(),
                                     float(pixels[1])/self.figure.get_dpi())

    def initial_draw(self): pass # abstract, to be overridden by child classes

class UpdatePlotPanel(PlotPanel):
    """Plots with an update mechanism"""
    def __init__( self, parent, **kwargs ):
        self.parent = parent

        # initiate plotter
        PlotPanel.__init__(self, parent, **kwargs)
        self.SetColor((255,255,255))
        self.plot_data = None
        
        self.recalc_count = 0
        # ssp_val = np.arange(1400,1550)
        # ssp_count = np.zeros_like(ssp_val)
        # # Yes, I could just subtract 1400 and use it as an index...
        # self.sv_hist = dict(zip(ssp_val, ssp_count))
        self.ssp_hist = np.zeros(151)
        self.ssp_vals = []
        print 'Using Update Data Method'

    def initial_draw(self):
        """Draw data."""
        if not hasattr(self, 'axes'):
            self.axes = self.figure.add_subplot(111, aspect='equal') # xlim=(0,101), ylim=(0,101))

        #self.plot_data = self.axes.scatter([],[], c='r')

    def update_plot(self, new_data_x, new_data_y, ssp = None):
        if ssp is None:
            # ssp = np.random.standard_normal() * 30 + 1480
            ssp = 1400 + len(self.ssp_vals) * 0.25
        if ssp >= 1400 and ssp < 1550:
            self.ssp_hist[np.around(ssp) - 1400] += 1
            self.ssp_vals = np.append(self.ssp_vals, ssp)
        elif ssp < 1400:
            self.ssp_vals = np.append(self.ssp_vals, 1400)
        else:
            self.ssp_vals = np.append(self.ssp_vals, 1550)

        self.recalc_count += 1
        if self.plot_data is None:
            self.plot_data = self.axes.scatter([new_data_x],[new_data_y], c='r')
        else:
            pts = self.plot_data.get_offsets()
            max_pts = pts.max(axis=0)
            min_pts = pts.min(axis=0)

            # num_pts = len(pts) + 1
            self.plot_data.set_offsets(np.append(self.plot_data.get_offsets(), (new_data_x, new_data_y)))
            self.axes.set_xlim(min_pts[0] - 5, max_pts[0] + 5)
            self.axes.set_ylim(min_pts[1] - 5, max_pts[1] + 5)

            if self.recalc_count > 0:
                ssp_hist_masked = np.ma.masked_less(self.ssp_hist, self.ssp_hist.sum() * 0.001, False)
                ssp_limits = np.ma.flatnotmasked_edges(ssp_hist_masked)
                ssp_min = 1400 + ssp_limits[0]
                ssp_max = 1400 + ssp_limits[1]

                if ssp_min == ssp_max:
                    ssp_max = ssp_min + 0.01

                scaled_val = (self.ssp_vals - ssp_min) / (ssp_max - ssp_min)
                scaled_val = scaled_val.clip(min = 0, max = 1)
                scaled_val *= 0.9  #Prevents it from wrapping around to red again
                colors = np.ones((len(scaled_val),1,3))
                colors[:,0,0] = scaled_val
                colors = matplotlib.colors.hsv_to_rgb(colors)
                # print colors, scaled_val
                self.recalc_count = 0
                self.plot_data.set_color(colors[:,0,:])


            

        # colors = plot.get_facecolor()
        # if colors.shape[0] == 1:
        #     newcolors = np.tile(colors, (2, 1))
        # else:
        #     newcolors = colors

        # if num_pts > 1:
        #     frac = float(num_pts)/100
        #     # print frac
        #     colors = np.vstack((colors, [0, frac, 0, 1]))

        # plot.set_color(colors)

        # either way works, one uses more CPU but one redraws faster...
        self.canvas.draw()
        # self._redrawflag = True

class CommunicationManager():
    def __init__(self, frame, sonar_address = '192.168.0.101', hypack_port = 9888):
        self.sonar_address = sonar_address
        self.hypack_port = hypack_port

        self.plot_panel = frame

        self.has_pos = False
        self.has_ssp = False
        self.comm_active = False

    def start_communication(self):
        print "Initializing Communication"
        self.hc = hypackcom.HypackCom('UDP', self.hypack_port, self)
        self.hc.run()

        # self.rc = resoncom.ResonComm(self.sonar_address, comm_manager=self)
        # self.rc.runsonar()

        self.comm_active = True

    def new_data(self, data):
        """Callback for data when received by a communications source
        Format of data is [data_type, data_information]"""
        
        if data[0] == 'hypack':
            addr = data[1][0]
            postext = data[1][1]
            if addr[0] == '127.0.0.1' and len(postext) == 41:
                self.has_pos = True
                self.last_pos = [float(pos) for pos in postext.split(' ')[:2]]
                print self.last_pos
        elif data[0] == 'reson':
            self.has_ssp = True
            self.last_ssp = data[1].header[6]
            print "Packet: %s, SV: %s" % (data[1].header[1], data[1].header[6])

        with threading.Lock():
            if self.has_pos:
                self.has_pos = False
                self.plot_panel.update_plot(float(self.last_pos[0]), float(self.last_pos[1]))

    def stop_communication(self):
        print "Stopping Communication"
        # self.rc.stop7kcenter()
        self.hc.stop()
        self.comm_active = False



if __name__ == '__main__':
    app = wx.App(0)
    app.frame = SVFrame()
    app.frame.Show()
    app.MainLoop()