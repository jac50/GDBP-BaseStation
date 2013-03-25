# -*- coding: cp1252 -*-
from threading import *
import time
import wx
from collections import namedtuple
EVT_RESULT_ID=wx.NewId()
def EVT_RESULT(win,func):
        win.Connect(-1,01,EVT_RESULT_ID,func)
     
DataPacket = namedtuple("DataPacket","BatteryVoltage BatteryCurrent BatteryPower DischargeCycles BatteryTemp SystemTemp Altitude ParachuteStatus LEDStatus OptoKineticStatus")                

class ResultEvent(wx.PyEvent):
        def __init__(self,data):
                wx.PyEvent.__init__(self)
                self.SetEventType(EVT_RESULT_ID)
                self.data = data
class FlareDataWorker(Thread):
        def __init__(self,wxObject):
                Thread.__init__(self)
                self.wxObject = wxObject
                self.start() #starts on creation
        def run(self):
                self.packet = DataPacket(50,30,1500,2,50,70,800,False,True,True)
                #Receive Data
                #unpack packet and add to DataPacket Variable declared above.
                wx.PostEvent(self.wxObject,ResultEvent(self.packet))#send to GUI
                # wx.PostEvent(self.wxObject,ResultEvent(self.packet)) - when used twice, the colours update. I think text is updating then colour is computed on original numbers
                
                
        def unpackPacket(self):
                #This is the code to decode the data packet
                foo = 1
        def RequestForData(self):
                #might not need this..
                foo = 1
        def abort(self):
                self._want_abort = 1
        
        
class MyFrame(wx.Frame):
        def __init__(self,parent,title):
                super(MyFrame,self).__init__(parent,title=title,size=(550,350))
                self.worker = None # No worker thread yet
                self.InitUI()
                
                self.populateGUI()
                EVT_RESULT(self,self.updateDisplay)
                self.updateGUI(0)
                self.Show()
           

        def OnStart(self,event):
                if self.StartButton.GetLabel() == "Start":
                        if not self.worker:
                                self.StatusBar.SetStatusText('Starting to collect data')
                                self.worker=FlareDataWorker(self)
                                self.StartButton.SetLabel('Stop')
                        else :
                                print "yes?"
                                
                     

                elif self.StartButton.GetLabel() == "Stop":
                        self.StatusBar.SetStatusText('Ready')
                        self.StartButton.SetLabel('Start')
                
        def updateDisplay(self,msg):
                t = msg.data
                self.StatusBar.SetStatusText('Updating GUI...')
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
                self.updateGUI(0)
                       
        def OnCloseWindow(self,event):
                self.Destroy()

        def InitUI(self):
                panel = wx.Panel(self)
                panel.SetBackgroundColour('#FFFFFF')
                
                #---- Need Title and Image -----
                
                #Battery Information

                self.BatteryVoltageLabel = wx.StaticText(panel,label='Voltage (V)',style=wx.ALIGN_CENTRE,pos=(300,40))
                self.BatteryVoltageValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,40),size=(50,15))
                self.BatteryCurrentLabel = wx.StaticText(panel,label='Current (I)',style=wx.ALIGN_CENTRE,pos=(300,60))
                self.BatteryCurrentValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,60),size=(50,15))
                self.BatteryPowerLabel = wx.StaticText(panel,label='Power (W)', style=wx.ALIGN_CENTRE,pos = (300,80))
                self.BatteryPowerValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,80),size=(50,15))
                self.BatteryDischargesLabel = wx.StaticText(panel,label='Number of Discharge Cycles',style=wx.ALIGN_CENTRE,pos = (300,100))
                self.BatteryDischargesValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,100),size=(50,15))
                self.BatteryTemperatureLabel = wx.StaticText(panel,label='Temperature (°C)',style=wx.ALIGN_CENTRE, pos = (300,120))
                self.BatteryTemperatureValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,120),size=(50,15))
                self.BatteryStaticBox = wx.StaticBox(panel,label = 'Battery Information',pos=(290,20),size=(225,120))

                #System Information
                
                self.SystemTemperatureLabel = wx.StaticText(panel,label='System Temperature (°C)',style=wx.ALIGN_CENTRE,pos = (300,170))
                self.SystemTemperatureValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,170),size=(50,15))
                self.AltitudeLabel = wx.StaticText(panel,label='Altitude (m)',style=wx.ALIGN_CENTRE,pos = (300,190))
                self.AltitudeValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,190),size=(50,15))
                self.ParachuteStatusLabel = wx.StaticText(panel,label='Parachute Status',style=wx.ALIGN_CENTRE, pos = (300,210))
                self.ParachuteStatusValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,210),size=(50,15))
                self.SystemStaticBox = wx.StaticBox(panel,label='System Information',pos = (290,150), size=(225,120))
                self.LEDStatusLabel = wx.StaticText(panel,label='LED Status',style=wx.ALIGN_CENTRE,pos= (300,230))
                self.LEDStatusValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE ,pos=(450,230),size=(50,15))
                self.OptoKineticStatusLabel = wx.StaticText(panel,label = 'Optokinetic Nystagmus', style = wx.ALIGN_CENTRE,pos = (300,250))
                self.OptoKineticStatusValue = wx.StaticText(panel,style = wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE, pos = (450,250), size = (50,15))
                self.ControlStaticBox = wx.StaticBox(panel,label='Control',pos=(5,20),size=(270,250))

                #Control Parameters

                self.ParachuteLabel = wx.StaticText(panel,label = 'Parachute Status:',pos=(10,52))
                self.ParachuteBtn = wx.Button(panel,label='Open Parachute',pos=(160,50),size=(100,20))
                self.LEDLabel = wx.StaticText(panel,label = 'LED Status:',pos=(10,72))
                self.LEDBtn = wx.Button(panel,label='Turn On',pos=(160,70),size=(50,20))
                self.OptoKineticLabel = wx.StaticText(panel,label = 'Opto-Kinetic Nystagmus Mode',pos=(10,90))
                self.OptoKineticBtn = wx.Button(panel,label = 'Turn On',pos=(160,90),size=(50,20))
                self.LightIntensityLabel = wx.StaticText(panel,label = 'Light Intensity', pos=(10,112))
                self.LightIntensitySlider = wx.Slider(panel,-1,25,0,100,(160,110),(100,-1),wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS)
                self.ightIntensityBtn = wx.Button(panel, label = 'Turn On',pos = (110,110), size = (50,20))
                self.DirectionalityLabel = wx.StaticText(panel,label = 'Directionality', pos=(10,162))
                #self.DirectionalityBtn
                
                
                #Event Listeners
                self.Bind(wx.EVT_BUTTON,self.ParachuteBtnPress,self.ParachuteBtn)
                self.Bind(wx.EVT_BUTTON,self.FlareBtnPress,self.LEDBtn)
                
                #Start Button
                self.StartButton = wx.Button(panel,label = 'Start',pos=(465,270),size=(50,20))
                self.Bind(wx.EVT_BUTTON,self.OnStart,self.StartButton)
                self.StatusBar = self.CreateStatusBar()
                self.StatusBar.SetStatusText('Ready')
                self.SetTitle('Base Station V1')

                #Update Button
                self.UpdateButton = wx.Button(panel,label = 'Update GUI',size=(90,20),pos=(375,270))
                self.Bind(wx.EVT_BUTTON,self.updateGUI,self.UpdateButton)
                
                #Map Button

                self.MapButton = wx.Button(panel,label = 'Map', pos=(320,270),size = (50,20))
                self.Bind(wx.EVT_BUTTON,self.openMap,self.MapButton)

        def populateGUI(self):
                #Temporary Function to initially populate values to test colours etc.
                self.BatteryVoltageValue.SetLabel('50')
                self.BatteryCurrentValue.SetLabel('100')
                self.BatteryPowerValue.SetLabel('5000')
                self.BatteryDischargesValue.SetLabel('5')
                self.BatteryTemperatureValue.SetLabel('40')
                self.SystemTemperatureValue.SetLabel('35')
                self.AltitudeValue.SetLabel('1000')
                self.ParachuteStatusValue.SetLabel('CLOSE')
                self.LEDStatusValue.SetLabel('OFF')
                self.OptoKineticStatusValue.SetLabel('OFF')
        def ParachuteBtnPress(self,evt):
                if self.ParachuteStatusValue.GetLabel() == 'OPEN':
                        self.StatusBar.SetStatusText('Parachute is already opened')
                elif self.ParachuteStatusValue.GetLabel() == 'CLOSE':
                        self.StatusBar.SetStatusText('Parachute Deploy Command Sent')
                        self.ParachuteStatusValue.SetLabel('OPEN')
        def FlareBtnPress(self,evt):
                self.StatusBar.SetStatusText('Power of The Sun has been turned on')
        def openMap(self,evt):
                self.StatusBar.SetStatusText('Test')
        def updateGUI(self,evt):
                        #Update GUI Values

                #Update Box Colours

                #---- ALL OF THE FIGURES HERE ARE ARBITARY ------ 
                if self.BatteryVoltageValue.GetLabel() < '30' : # Slightly cheating here as I'm checking the ASCII value of the label is lower than the ASCII value of '30'. will change it 
                    self.BatteryVoltageValue.SetBackgroundColour('#FF0000')
                else:
                    self.BatteryVoltageValue.SetBackgroundColour('#00FF00')
                if self.BatteryCurrentValue.GetLabel() > '200' : 
                    self.BatteryCurrentValue.SetBackgroundColour('#FF0000')
                else:   
                    self.BatteryCurrentValue.SetBackgroundColour('#00FF00')
                if self.BatteryPowerValue.GetLabel() < '1000000' : 
                    self.BatteryPowerValue.SetBackgroundColour('#FF0000')
                else:
                    self.BatteryPowerValue.SetBackgroundColour('#00FF00')
                if self.BatteryDischargesValue.GetLabel() > '50' : 
                    self.BatteryDischargesValue.SetBackgroundColour('#FF0000')
                else: self.BatteryDischargesValue.SetBackgroundColour('#00FF00')     
                if self.BatteryTemperatureValue.GetLabel() > '80' : 
                    self.BatteryTemperatureValue.SetBackgroundColour('#FF0000')
                else:
                    self.BatteryTemperatureValue.SetBackgroundColour('#00FF00')
                if self.SystemTemperatureValue.GetLabel() > '60' : 
                    self.SystemTemperatureValue.SetBackgroundColour('#FF0000')
                else:
                    self.SystemTemperatureValue.SetBackgroundColour('#00FF00')

                #Altitude Value - This needs to be adapted so the value colour will only change to red if the flare is in at an incorrect altitude (IE parachute not launched and rapidly falling)
                    
                if self.AltitudeValue.GetLabel() < '10' : 
                    self.AltitudeValue.SetBackgroundColour('#FF0000')
                else:
                    self.AltitudeValue.SetBackgroundColour('#00FF00')
                    
                if self.ParachuteStatusValue.GetLabel() == 'CLOSE' : 
                    self.ParachuteStatusValue.SetBackgroundColour('#FF0000')
                else:
                    self.ParachuteStatusValue.SetBackgroundColour('#00FF00')
                if self.LEDStatusValue.GetLabel() == "OFF" : 
                    self.LEDStatusValue.SetBackgroundColour('#FF0000')
                else:
                    self.LEDStatusValue.SetBackgroundColour('#00FF00')
                if self.OptoKineticStatusValue.GetLabel() == "ON":
                        self.OptoKineticStatusValue.SetBackgroundColour('#00FF00')
                else:
                        self.OptoKineticStatusValue.SetBackgroundColour('#FF0000')

        
if __name__ == '__main__':
    app = wx.App(0)
    window = MyFrame(None, title = "Base Station V1") 
    app.MainLoop()

    
