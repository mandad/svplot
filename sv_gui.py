# -*- coding: utf-8 -*- 

###########################################################################
## Python code generated with wxFormBuilder (version Nov  6 2013)
## http://www.wxformbuilder.org/
##
## PLEASE DO "NOT" EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc

###########################################################################
## Class SVFrame
###########################################################################

class SVFrame ( wx.Frame ):
	
	def __init__( self, parent ):
		wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = wx.EmptyString, pos = wx.DefaultPosition, size = wx.Size( 500,300 ), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )
		
		self.SetSizeHintsSz( wx.DefaultSize, wx.DefaultSize )
		
		self.m_menubar1 = wx.MenuBar( 0 )
		self.run_menu = wx.Menu()
		self.run_start = wx.MenuItem( self.run_menu, wx.ID_ANY, u"Start", wx.EmptyString, wx.ITEM_NORMAL )
		self.run_menu.AppendItem( self.run_start )
		
		self.run_stop = wx.MenuItem( self.run_menu, wx.ID_ANY, u"Stop", wx.EmptyString, wx.ITEM_NORMAL )
		self.run_menu.AppendItem( self.run_stop )
		
		self.m_menubar1.Append( self.run_menu, u"Run" ) 
		
		self.SetMenuBar( self.m_menubar1 )
		
		bSizer1 = wx.BoxSizer( wx.VERTICAL )
		
		self.PlotPanel = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
		bSizer1.Add( self.PlotPanel, 1, wx.EXPAND |wx.ALL, 5 )
		
		
		self.SetSizer( bSizer1 )
		self.Layout()
		
		self.Centre( wx.BOTH )
		
		# Connect Events
		self.Bind( wx.EVT_CLOSE, self._OnClose )
		self.Bind( wx.EVT_MENU, self.start_comm, id = self.run_start.GetId() )
		self.Bind( wx.EVT_MENU, self.stop_comm, id = self.run_stop.GetId() )
	
	def __del__( self ):
		pass
	
	
	# Virtual event handlers, overide them in your derived class
	def _OnClose( self, event ):
		event.Skip()
	
	def start_comm( self, event ):
		event.Skip()
	
	def stop_comm( self, event ):
		event.Skip()
	

###########################################################################
## Class Process Frame
###########################################################################

class Process Frame ( wx.Frame ):
	
	def __init__( self, parent ):
		wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = u"Process Surface SV", pos = wx.DefaultPosition, size = wx.Size( 301,221 ), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )
		
		self.SetSizeHintsSz( wx.DefaultSize, wx.DefaultSize )
		
		bSizer3 = wx.BoxSizer( wx.VERTICAL )
		
		self.m_notebook3 = wx.Notebook( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.page_read = wx.Panel( self.m_notebook3, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
		fgSizer3 = wx.FlexGridSizer( 0, 1, 0, 0 )
		fgSizer3.AddGrowableRow( 3 )
		fgSizer3.SetFlexibleDirection( wx.BOTH )
		fgSizer3.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )
		
		self.fp_hsx_files = wx.FilePickerCtrl( self.page_read, wx.ID_ANY, wx.EmptyString, u"Select a file", u"*.HSX", wx.DefaultPosition, wx.Size( 200,-1 ), wx.FLP_DEFAULT_STYLE )
		fgSizer3.Add( self.fp_hsx_files, 0, wx.ALL, 5 )
		
		self.dp_hsx_dir = wx.DirPickerCtrl( self.page_read, wx.ID_ANY, wx.EmptyString, u"Select a folder of HSX Files", wx.DefaultPosition, wx.Size( 200,-1 ), wx.DIRP_DEFAULT_STYLE )
		fgSizer3.Add( self.dp_hsx_dir, 0, wx.ALL, 5 )
		
		self.btn_read_sv = wx.Button( self.page_read, wx.ID_ANY, u"Read SV Values", wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer3.Add( self.btn_read_sv, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL|wx.ALIGN_BOTTOM, 5 )
		
		self.m_gauge1 = wx.Gauge( self.page_read, wx.ID_ANY, 100, wx.DefaultPosition, wx.Size( 250,-1 ), wx.GA_HORIZONTAL )
		self.m_gauge1.SetValue( 0 ) 
		fgSizer3.Add( self.m_gauge1, 0, wx.ALL, 5 )
		
		
		self.page_read.SetSizer( fgSizer3 )
		self.page_read.Layout()
		fgSizer3.Fit( self.page_read )
		self.m_notebook3.AddPage( self.page_read, u"Read SV", False )
		self.page_display = wx.Panel( self.m_notebook3, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
		fgSizer2 = wx.FlexGridSizer( 0, 1, 0, 0 )
		fgSizer2.AddGrowableCol( 0 )
		fgSizer2.SetFlexibleDirection( wx.BOTH )
		fgSizer2.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )
		
		self.fp_process_file = wx.FilePickerCtrl( self.page_display, wx.ID_ANY, wx.EmptyString, u"Select a file", u"*.*", wx.DefaultPosition, wx.DefaultSize, wx.FLP_DEFAULT_STYLE )
		fgSizer2.Add( self.fp_process_file, 0, wx.ALL, 5 )
		
		self.btn_map = wx.Button( self.page_display, wx.ID_ANY, u"Create Map", wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer2.Add( self.btn_map, 0, wx.ALL, 5 )
		
		
		self.page_display.SetSizer( fgSizer2 )
		self.page_display.Layout()
		fgSizer2.Fit( self.page_display )
		self.m_notebook3.AddPage( self.page_display, u"Create Map", True )
		
		bSizer3.Add( self.m_notebook3, 1, wx.EXPAND |wx.ALL, 5 )
		
		
		self.SetSizer( bSizer3 )
		self.Layout()
		
		self.Centre( wx.BOTH )
		
		# Connect Events
		self.btn_read_sv.Bind( wx.EVT_BUTTON, self.btn_read_click )
		self.btn_map.Bind( wx.EVT_BUTTON, self.create_map_click )
	
	def __del__( self ):
		pass
	
	
	# Virtual event handlers, overide them in your derived class
	def btn_read_click( self, event ):
		event.Skip()
	
	def create_map_click( self, event ):
		event.Skip()
	

