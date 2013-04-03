# -*- coding: cp1252 -*-
from threading import *
import time
import wx
from collections import namedtuple
#import usb
#import packet
EVT_RESULT_ID=wx.NewId()
EVT_UPDATESTATUS_ID = wx.NewId()
DataPacket = namedtuple("DataPacket","BatteryVoltage BatteryCurrent BatteryPower DischargeCycles BatteryTemp SystemTemp Altitude ParachuteStatus LEDStatus OptoKineticStatus")                
ControlParameters = namedtuple("ControlParameters", "LEDCommand ParachuteCommand OptoKinetic LightIntensity Directionality")
def EVT_RESULT(win,func):
        win.Connect(-1,01,EVT_RESULT_ID,func)
def EVT_UPDATESTATUS(win,func):        
        win.Connect(-1,01,EVT_UPDATESTATUS_ID,func)
class ResultEvent(wx.PyEvent):
        def __init__(self,data):
                wx.PyEvent.__init__(self)
                self.SetEventType(EVT_RESULT_ID)
                self.data = data
class UpdateStatusEvent(wx.PyEvent):
        def __init__(self,data):
                wx.PyEvent.__init__(self)
                self.SetEventType(EVT_UPDATESTATUS_ID)
                self.data = data
                
class FlareDataWorker(Thread):
        ExitCode = 0
        FlareData = DataPacket(40,30,1200,2,50,70,800,False,False,False)
        def __init__(self,wxObject):
                Thread.__init__(self)
                self.wxObject = wxObject
                self.start()
                self.ExitCode = 0
        def UnpackPacket(self):
                # This is the code to decode the data packet
                # Used to edit the FlareData packet for testing
                foo = 1
                        
        def run(self):
                x = 0
                while (self.ExitCode == 0):                 
                        #Receive Data
                        #unpack packet and add to DataPacket Variable declared above.
                        self.UnpackPacket()
                        self.FlareData = self.FlareData._replace(DischargeCycles = self.FlareData.DischargeCycles + 1) #Used for Testing
                        wx.PostEvent(self.wxObject,ResultEvent(self.FlareData))#send to GUI                                                  
                        time.sleep(1)                   
        
                
        def RequestForData(self):
                #might not need this..
                foo = 1
        def Abort(self):
                self.ExitCode = 1
class ControlWorker(Thread):
        def __init__(self,wxObject,args):
                Thread.__init__(self)
                self.wxObject = wxObject
                self.commands = args
                self.start()
        def run(self):
                wx.PostEvent(self.wxObject,UpdateStatusEvent("Packing Packet"))
                self.PackPacket()
                wx.PostEvent(self.wxObject,UpdateStatusEvent("Sending Packet"))
                
        def PackPacket(self):
                #Pack Packet here
                #Use import packet to pack the packet. or maybe do it myself.
                time.sleep(0.5)
class MyFrame(wx.Frame):
        def __init__(self,parent,title):
                super(MyFrame,self).__init__(parent,title=title,size=(550,350))
                self.worker = None # No worker thread yet
                self.controlparameters = ControlParameters(False,False,False,0,0)
                self.InitUI()
                self.populateGUI()
                EVT_RESULT(self,self.updateDisplay)
                EVT_UPDATESTATUS(self,self.UpdateStatus)
                self.updateGUI(0)
                self.Show() 
        def UpdateStatus(self,msg):
                t = msg.data
                self.StatusBar.SetStatusText(t)
        def ParachuteBtnPress(self,evt):
                if self.ParachuteStatusValue.GetLabel() == "OPEN":
                        self.StatusBar.SetStatusText('Parachute is already opened')
                else:
                        self.controlparameters = self.controlparameters._replace(ParachuteCommand = True)
                        self.StatusBar.SetStatusText('Parachute Deploy Command primed')
        def LEDBtnPress(self,evt):
                if self.LEDBtn.GetLabel() == 'Turn On':
                        self.controlparameters = self.controlparameters._replace(LEDCommand = True)
                        self.StatusBar.SetStatusText('Power of The Sun has been turned on')
                        self.LEDBtn.SetLabel('Turn Off')
                else:
                        self.controlparameters = self.controlparameters._replace(LEDCommand = False)
                        self.StatusBar.SetStatusText('Power of The Sun has been turned off')
                        self.LEDBtn.SetLabel('Turn On')
        def OptoKineticBtnPress(self,evt):
                if self.OptoKineticBtn.GetLabel() == 'Turn On':
                        self.controlparameters = self.controlparameters._replace(OptoKinetic = True)
                        self.StatusBar.SetStatusText('OptoKinetic Nystagmus Mode ON command has been sent')
                        self.OptoKineticBtn.SetLabel('Turn Off')
                else:
                        self.controlparameters = self.controlparameters._replace(OptoKinetic = False)
                        self.StatusBar.SetStatusText('OptoKinetic Nystagmus Mode OFF command has been sent')
                        self.OptoKineticBtn.SetLabel('Turn On')
   
        def openMap(self,evt):
                # ------ Need to work on this --------
                self.StatusBar.SetStatusText('Localisation Map has been opened')
        def OnStart(self,event):
                if self.StartButton.GetLabel() == "Start":
                        if not self.worker:
                                self.StatusBar.SetStatusText('Starting to collect data')
                                self.worker=FlareDataWorker(self)
                                self.StartButton.SetLabel('Stop')                                               
                elif self.StartButton.GetLabel() == "Stop":
                        self.StatusBar.SetStatusText('Updating Stopped')
                        self.worker.Abort()
                        self.worker = None
                        self.StartButton.SetLabel('Start')
        def LightIntensitySliderUpdate(self,evt):
                self.controlparameters = self.controlparameters._replace(LightIntensity = self.LightIntensitySlider.GetValue())
        def DirectionalitySliderUpdate(self,evt):
                self.controlparameters = self.controlparameters._replace(Directionality = self.DirectionalitySlider.GetValue())
        def updateDisplay(self,msg):
                self.updateGUI(1)
                t = msg.data
                self.StatusBar.SetStatusText('Data Received')
                self.BatteryVoltageValue.SetLabel(str(t.BatteryVoltage))
                self.BatteryCurrentValue.SetLabel(str(t.BatteryCurrent))
                self.BatteryPowerValue.SetLabel(str(t.BatteryPower))
                self.BatteryDischargesValue.SetLabel(str(t.DischargeCycles))
                self.BatteryTemperatureValue.SetLabel(str(t.BatteryTemp))
                self.SystemTemperatureValue.SetLabel(str(t.SystemTemp))
                self.AltitudeValue.SetLabel(str(t.Altitude))
                if t.ParachuteStatus:
                        self.ParachuteStatusValue.SetLabel('OPEN')
                else: self.ParachuteStatusValue.SetLabel('CLOSE')
                if t.LEDStatus:
                        self.LEDStatusValue.SetLabel('ON')
                else: self.LEDStatusValue.SetLabel('OFF')
                if t.OptoKineticStatus:
                        self.OptoKineticStatusValue.SetLabel('ON')
                else: self.OptoKineticStatusValue.SetLabel('OFF')
                self.StatusBar.SetStatusText('Ready')
                self.updateGUI(1)
        def SendCommandFnc(self,evt):
                self.StatusBar.SetStatusText('Collating Commands to Send')                
                self.controlthread = ControlWorker(self,self.controlparameters)
                self.StatusBar.SetStatusText('Commands Sent to Background Thread')
                
        def OnCloseWindow(self,event):
                self.worker.Abort()
                self.controlthread.Abort()
                self.Destroy()

        def InitUI(self):
                panel = wx.Panel(self)
                panel.SetBackgroundColour('#FFFFFF')
                panelsizer = wx.BoxSizer(wx.VERTICAL)
                #---- Need Title and Image -----
                
                
		#Connection Status
		constatussizer = wx.BoxSizer(wx.HORIZONTAL)
                self.ConnectionStatusLabel = wx.StaticText(panel,label = 'Connection Status:')
                self.ConnectionStatusValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE)
		constatussizer.Add(self.ConnectionStatusLabel,border = 20)		
		constatussizer.Add(self.ConnectionStatusValue, border = 20)
		panelsizer.Add(constatussizer,flag=wx.ALIGN_RIGHT|wx.TOP | wx.RIGHT, border=10)

		
		#Battery Information
		battinfo = wx.FlexGridSizer(5,2,5,8)
		

                self.BatteryVoltageLabel = wx.StaticText(panel,label='Voltage (V)',style=wx.ALIGN_CENTRE)
                self.BatteryVoltageValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE)
                self.BatteryCurrentLabel = wx.StaticText(panel,label='Current (I)',style=wx.ALIGN_CENTRE)
                self.BatteryCurrentValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE)
                self.BatteryPowerLabel = wx.StaticText(panel,label='Power (W)', style=wx.ALIGN_CENTRE)
                self.BatteryPowerValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE)
                self.BatteryDischargesLabel = wx.StaticText(panel,label='Number of Discharge Cycles',style=wx.ALIGN_CENTRE)
                self.BatteryDischargesValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE)
                self.BatteryTemperatureLabel = wx.StaticText(panel,label='Temperature (oC)',style=wx.ALIGN_CENTRE)
                self.BatteryTemperatureValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE)
                
		BatteryStaticBox = wx.StaticBox(panel,label = 'Battery Information')
		BatteryBox = wx.StaticBoxSizer(BatteryStaticBox,wx.HORIZONTAL)		
				
		battinfo.AddMany([(self.BatteryVoltageLabel),(self.BatteryVoltageValue,1,wx.EXPAND),
				(self.BatteryCurrentLabel),(self.BatteryCurrentValue,1,wx.EXPAND),
				(self.BatteryPowerLabel),(self.BatteryPowerValue,1,wx.EXPAND),
				(self.BatteryDischargesLabel),(self.BatteryDischargesValue,1,wx.EXPAND),
				(self.BatteryTemperatureLabel),(self.BatteryTemperatureValue,1,wx.EXPAND)])
		
		BatteryBox.Add(battinfo,proportion = 1, flag = wx.ALL | wx.EXPAND, border = 10)			
		panelsizer.Add(BatteryBox,flag=wx.ALIGN_RIGHT|wx.RIGHT, border=10)			  
							     
                #System Information
		sysinfo = wx.FlexGridSizer(5,2,5,8) 
		self.SystemTemperatureLabel = wx.StaticText(panel,label='System Temperature (oC)',style=wx.ALIGN_CENTRE)
		self.SystemTemperatureValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE)
		self.AltitudeLabel = wx.StaticText(panel,label='Altitude (m)',style=wx.ALIGN_CENTRE)
		self.AltitudeValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE)
		self.ParachuteStatusLabel = wx.StaticText(panel,label='Parachute Status',style=wx.ALIGN_CENTRE)
		self.ParachuteStatusValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE)
		
		self.LEDStatusLabel = wx.StaticText(panel,label='LED Status',style=wx.ALIGN_CENTRE)
		self.LEDStatusValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE)
		self.OptoKineticStatusLabel = wx.StaticText(panel,label = 'Optokinetic Nystagmus', style = wx.ALIGN_CENTRE)
		self.OptoKineticStatusValue = wx.StaticText(panel,style = wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE)
		
		SystemStaticBox = wx.StaticBox(panel,label='System Information')
		SystemBox = wx.StaticBoxSizer(SystemStaticBox,wx.HORIZONTAL)

		sysinfo.AddMany([(self.SystemTemperatureLabel),(self.SystemTemperatureValue,1,wx.EXPAND),
				(self.AltitudeLabel),(self.AltitudeValue,1,wx.EXPAND),
				(self.ParachuteStatusLabel),(self.ParachuteStatusValue,1,wx.EXPAND),
				(self.LEDStatusLabel),(self.LEDStatusValue,1,wx.EXPAND),
				(self.OptoKineticStatusLabel),(self.OptoKineticStatusValue,1,wx.EXPAND)])
		
		
		SystemBox.Add(sysinfo,proportion = 1, flag = wx.ALL | wx.EXPAND, border = 10)
		panelsizer.Add(SystemBox,flag=wx.ALIGN_RIGHT|wx.RIGHT, border=10)
		
		
                #Control Parameters
		self.ControlStaticBox = wx.StaticBox(panel,label='Control',pos=(5,20),size=(270,250))
                self.ParachuteLabel = wx.StaticText(panel,label = 'Parachute Status:',pos=(10,52))
                self.ParachuteBtn = wx.ToggleButton(panel,label='OPEN',pos=(160,50),size=(50,20))
                self.LEDLabel = wx.StaticText(panel,label = 'LED Status:',pos=(10,72))
                self.LEDBtn = wx.ToggleButton(panel,label='Turn On',pos=(160,70),size=(50,20))
                self.OptoKineticLabel = wx.StaticText(panel,label = 'Opto-Kinetic Nystagmus Mode',pos=(10,90))
                self.OptoKineticBtn = wx.ToggleButton(panel,label = 'Turn On',pos=(160,90),size=(50,20))
                self.LightIntensityLabel = wx.StaticText(panel,label = 'Light Intensity', pos=(10,112))
                self.LightIntensitySlider = wx.Slider(panel,-1,25,0,100,(160,110),(100,-1),wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS)
                self.DirectionalityLabel = wx.StaticText(panel,label = 'Directionality', pos=(10,162))
                self.DirectionalitySlider = wx.Slider(panel,-1,0,-90,90,(160,162),(100,-1),wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS)
                                    
                
                
		#Buttons
		btnsizer = wx.BoxSizer(wx.HORIZONTAL)
                self.StartButton = wx.Button(panel,label = 'Start')
                self.UpdateButton = wx.Button(panel,label = 'Update GUI')
                self.MapButton = wx.Button(panel,label = 'Map')
		btnsizer.AddMany([(self.StartButton),(self.UpdateButton),(self.MapButton)])
		panelsizer.Add(btnsizer,flag=wx.ALIGN_RIGHT|wx.RIGHT, border=10)
		
                #Update Button

               
                
                
                #Map Button

                
                
		
                

                #Send Commands Button

                self.SendCommandBtn = wx.Button(panel,label = 'Send Commands',pos = (170,240),size = (100,20))
                
		
		#Event Listeners
                
                self.Bind(wx.EVT_TOGGLEBUTTON,self.ParachuteBtnPress,self.ParachuteBtn)
                self.Bind(wx.EVT_TOGGLEBUTTON,self.LEDBtnPress,self.LEDBtn)
                self.Bind(wx.EVT_TOGGLEBUTTON,self.OptoKineticBtnPress,self.OptoKineticBtn)
                self.Bind(wx.EVT_SLIDER,self.LightIntensitySliderUpdate,self.LightIntensitySlider)
                self.Bind(wx.EVT_SLIDER,self.DirectionalitySliderUpdate,self.DirectionalitySlider)
		self.Bind(wx.EVT_BUTTON,self.OnStart,self.StartButton)
		self.Bind(wx.EVT_BUTTON,self.updateGUI,self.UpdateButton)
		self.Bind(wx.EVT_BUTTON,self.openMap,self.MapButton)
		self.Bind(wx.EVT_BUTTON,self.SendCommandFnc,self.SendCommandBtn)
		
		#Status Bar
		self.StatusBar = self.CreateStatusBar()
                self.StatusBar.SetStatusText('Ready')
		#Other
		panel.SetSizer(panelsizer)
                self.SetTitle('Base Station V1')
        def populateGUI(self):
                #Temporary Function to initially populate values to test colours etc.
                self.BatteryVoltageValue.SetLabel('-')
                self.BatteryCurrentValue.SetLabel('-')
                self.BatteryPowerValue.SetLabel('-')
                self.BatteryDischargesValue.SetLabel('-')
                self.BatteryTemperatureValue.SetLabel('-')
                self.SystemTemperatureValue.SetLabel('-')
                self.AltitudeValue.SetLabel('-')
                self.ParachuteStatusValue.SetLabel('-')
                self.LEDStatusValue.SetLabel('-')
                self.OptoKineticStatusValue.SetLabel('-')
                self.ConnectionStatusValue.SetLabel('Not Connected')
                
        
        def updateGUI(self,evt):
                
                #Update Box Colours
                
                #---- ALL OF THE FIGURES HERE ARE ARBITARY ------ 
                if self.BatteryVoltageValue.GetLabel() !='-':
                        if int(self.BatteryVoltageValue.GetLabel()) < 30 :  
                                self.BatteryVoltageValue.SetBackgroundColour('#FF0000')
                        else:
                                self.BatteryVoltageValue.SetBackgroundColour('#00FF00')
                if self.BatteryCurrentValue.GetLabel() !='-':
                        if int(self.BatteryCurrentValue.GetLabel()) > 200 : 
                                self.BatteryCurrentValue.SetBackgroundColour('#FF0000')
                        else:   
                                self.BatteryCurrentValue.SetBackgroundColour('#00FF00')
                if self.BatteryPowerValue.GetLabel() != '-':
                        if int(self.BatteryPowerValue.GetLabel()) < 1000000 : 
                                self.BatteryPowerValue.SetBackgroundColour('#FF0000')
                        else:
                                self.BatteryPowerValue.SetBackgroundColour('#00FF00')
                if self.BatteryDischargesValue.GetLabel() !='-':
                        if int(self.BatteryDischargesValue.GetLabel()) > 50 : 
                                self.BatteryDischargesValue.SetBackgroundColour('#FF0000')
                        else: self.BatteryDischargesValue.SetBackgroundColour('#00FF00')     
                if self.BatteryTemperatureValue.GetLabel() != '-':
                        if int(self.BatteryTemperatureValue.GetLabel()) > 80 : 
                                self.BatteryTemperatureValue.SetBackgroundColour('#FF0000')
                        else:
                                self.BatteryTemperatureValue.SetBackgroundColour('#00FF00')
                #if self.SystemTemperatureValue.GetLabel() != '-':
                 #       if int(self.SystemTemperatureValue.GetLabel()) > 60 : 
                  #              self.SystemTemperatureValue.SetBackgroundColour('#FF0000')
                   #     else:
                    #            self.SystemTemperatureValue.SetBackgroundColour('#00FF00')

                #Altitude Value - This needs to be adapted so the value colour will only change to red if the flare is in at an incorrect altitude (IE parachute not launched and rapidly falling)
                #if self.AltitudeValue.GetLabel()!='-':
                 #       if int(self.AltitudeValue.GetLabel()) < 10 : 
                  #              self.AltitudeValue.SetBackgroundColour('#FF0000')
                   #     else:
                    #            self.AltitudeValue.SetBackgroundColour('#00FF00')
                    
                #if self.ParachuteStatusValue.GetLabel()!='-':
                 #       if self.ParachuteStatusValue.GetLabel() == 'CLOSE' : 
                  #              self.ParachuteStatusValue.SetBackgroundColour('#FF0000')
                   #     else:
                    #            self.ParachuteStatusValue.SetBackgroundColour('#00FF00')
                #if self.LEDStatusValue.GetLabel()!='-':
                 #       if self.LEDStatusValue.GetLabel() == "OFF" : 
                  #              self.LEDStatusValue.SetBackgroundColour('#FF0000')
                   #     else:
                    #            self.LEDStatusValue.SetBackgroundColour('#00FF00')
                #if self.OptoKineticStatusValue.GetLabel()!='-':
                 #       if self.OptoKineticStatusValue.GetLabel() == "ON":
                  #              self.OptoKineticStatusValue.SetBackgroundColour('#00FF00')
                   #     else:
                    #            self.OptoKineticStatusValue.SetBackgroundColour('#FF0000')
                #if self.ConnectionStatusValue.GetLabel() == "Not Connected":
                 #       self.ConnectionStatusValue.SetBackgroundColour('#FF0000')
                #else:
                #        self.ConnectionStatusValue.SetBackgroundColour('#00FF00')

        
if __name__ == '__main__':
    app = wx.App(0)
    window = MyFrame(None, title = "Base Station V1") 
    app.MainLoop()

    
