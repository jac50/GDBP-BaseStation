# -*- coding: cp1252 -*-
from threading import *
import time
import wx
from collections import namedtuple
import crcmod
import serial



EVT_RESULT_ID=wx.NewId()
EVT_UPDATESTATUS_ID = wx.NewId()
EVT_UPDATECONNECTIONSTATUS_ID = wx.NewId()
DataPacket = namedtuple("DataPacket","BatteryVoltage BatteryCurrent BatteryPower DischargeCycles BatteryTemp SystemTemp Altitude ParachuteStatus LEDStatus OptoKineticStatus ErrorStates")                
ControlParameters = namedtuple("ControlParameters", "LEDCommand LEDIntensity OptoKinetic Directionality ParachuteCommand")


def EVT_RESULT(win,func):
        win.Connect(-1,01,EVT_RESULT_ID,func)
def EVT_UPDATESTATUS(win,func):        
        win.Connect(-1,01,EVT_UPDATESTATUS_ID,func)
def EVT_UPDATECONNECTIONSTATUS(win,func):
        win.Connect(-1,01,EVT_UPDATECONNECTIONSTATUS_ID,func)
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
class UpdateConnectionStatus(wx.PyEvent):
        def __init__(self,data):
                wx.PyEvent.__init__(self)
                self.SetEventType(EVT_UPDATECONNECTIONSTATUS_ID)
                self.data = data                
class FlareDataWorker(Thread):
        ExitCode = 0
        allowed = True
        FlareData = DataPacket(40,30,1200,2,50,70,800,True,True,False, 0b0000000000)
        port = serial.Serial() #9600, 8, N, 1
        port.port = 5 #Device is on Port 3. Zero Indexed. Port 6 on Netbook
        port.baudrate = 9600
        def __init__(self,wxObject):
                Thread.__init__(self)
                self.wxObject = wxObject
                self.start()
                self.ExitCode = 0
                self.rpacket = 0b0
        def UnpackPacket(self):
                # Packet Shape
                # Start Sequence    :1001
                # Voltage           :8 bit
                # Current           :8 bit
                # Power             :12 bit
                # DischargeCycles   :8 bit
                # BatteryTemp       :8 bit
                # SystemTemp        :8 bit
                # Altitude          :12 bit
                # ParachuteStatus   :4 bit
                # LEDStatus         :4 bit
                # OptoKineticStatus :4 bit                      
                # ErrorStateFlags   :10 bit
                # CRC               :32bit
                # End Sequence      :1010               
                # Total Size        :116 bit
                
                self.rpacket = self.rpacket >> 4
                crcrec = self.rpacket & 0b11111111111111111111111111111111
                #Calculate CRC and check if it's equal.
                self.rpacket = self.rpacket >> 32
                dataToCRC = self.rpacket & 0b00001111111111111111111111111111111111111111111111111111111111111111111111111111111111111
                crc32_func = crcmod.mkCrcFun(0x104c11db7, initCrc=0, xorOut=0xFFFFFFFF)
                crccalc = crc32_func(str(dataToCRC))
                if crccalc!=crcrec:
                        print "There has been an error. Discard Data"
                        return -1
                # Need conditions to see when these are true or false when 1111 or 0000 
                errorstate = self.rpacket & 0b1111111111
                self.rpacket = self.rpacket >> 10
                opto = self.rpacket & 0b1111            
                self.rpacket = self.rpacket >> 4                                                                                                                                        
                ledstatus = self.rpacket & 0b1111
                self.rpacket = self.rpacket >> 4
                parachute = self.rpacket & 0b1111
                self.rpacket = self.rpacket >> 4
                altitude = self.rpacket & 0b111111111111
                self.rpacket = self.rpacket >> 12
                SystemTemp = self.rpacket & 0b11111111
                self.rpacket = self.rpacket >> 8
                BatteryTemp = self.rpacket & 0b11111111
                self.rpacket = self.rpacket >> 8
                DischargeCycles = self.rpacket & 0b11111111
                self.rpacket = self.rpacket >> 8
                Power = self.rpacket & 0b1111111111111
                self.rpacket = self.rpacket >> 12
                Current = self.rpacket & 0b11111111
                self.rpacket = self.rpacket >> 8
                Voltage = self.rpacket & 0b11111111
                self.rpacket = self.rpacket >> 4

        def run(self):
                while (self.ExitCode == 0):                 
                        #Receive Data
                        #unpack packet and add to DataPacket Variable declared above.
                                               
                        self.ReceiveData() #commented until transceiver has been built
                        error = self.UnpackPacket()
                        if error == -1:
                                print "Packet is Ignored"
                                continue
                        wx.PostEvent(self.wxObject,ResultEvent(self.FlareData)) #send to GUI                                               
                        time.sleep(1)

        def ReceiveData(self):
               # ---- Function used to retrieve and format the received signal correctly ----
                if (self.allowed):
                        try:
                               self.port.open()
                        except serial.SerialException as e :
                               print "Error({0}): {1}".format(e.errno,e.strerror)
                               wx.PostEvent(self.wxObject,UpdateConnectionStatus(False))
                        else:
                               handshake = '0110001'
                               self.port.write(handshake) #Handshake
                               response = self.port.read(7)         
                               wx.PostEvent(self.wxObject,UpdateConnectionStatus(True))
                               self.rpacket = int(self.port.read(38))                       
                               self.port.close()
        def ToggleAllowed(self):
                if self.allowed:
                        self.allowed = False
                else:
                        self.allowed = True
      

        def Abort(self):
                self.ExitCode = 1
class ControlWorker(Thread):
        Commands = ControlParameters(0b11,0b1111,0b11,0b00001111,0b11) 
        port = serial.Serial()
        port.baudrate = 9600
        port.port = 5 #Device is on Port 3. Zero Indexed. Port 6 on Netbook
        port.timeout = 0.05   
        def __init__(self,wxObject,args):
                Thread.__init__(self)
                self.wxObject = wxObject
                self.commands = args
                self.start()
                self.cpacket = 0b00
        def run(self):
                wx.PostEvent(self.wxObject,UpdateStatusEvent("Packing Packet"))
                self.PackPacket()
                self.SendPacket()
                wx.PostEvent(self.wxObject,UpdateStatusEvent("Packet Sent"))
        def PackPacket(self):
                # Packet Shape
                # Start flag          : 1100
                # LEDCommands Flag    : 2 bit
                # Light Intenisty Flag : 4 bit
                # OptoKineticFlag     : 2 bit
                # Directionality Flag : 8 bit
                # Parachute Flag      : 2 bit
                # CRC                :
                # End Flag           : 0011

               self.cpacket = 0b1100
               self.cpacket =  self.cpacket << 2
               self.cpacket = self.cpacket + self.Commands.LEDCommand
               self.cpacket = self.cpacket << 4
               self.cpacket = self.cpacket + self.Commands.LEDIntensity
               self.cpacket = self.cpacket << 2
               self.cpacket = self.cpacket + self.Commands.OptoKinetic
               self.cpacket = self.cpacket << 8
               self.cpacket = self.cpacket + self.Commands.Directionality
               self.cpacket = self.cpacket << 2
               self.cpacket = self.cpacket + self.Commands.ParachuteCommand
               # Generate CRC
               data = 0b0000111111111111111111
               crc32_func = crcmod.mkCrcFun(0x104c11db7, initCrc=0, xorOut=0xFFFFFFFF)
               crc = crc32_func(str(data))
               self.cpacket =  self.cpacket << 32
               self.cpacket = self.cpacket + crc
               self.cpacket = self.cpacket << 4
               self.cpacket = self.cpacket + 0b0011
        def SendPacket(self):
                try:
                       self.port.open()
                except serial.SerialException as e :
                       print "Error({0}): {1}".format(e.errno,e.strerror)
                       wx.PostEvent(self.wxObject,UpdateConnectionStatus(False))
                else:
                        handshake = '1001110'
                        self.port.write(handshake) #Handshake
                        response = self.port.read(7)
                        wx.PostEvent(self.wxObject,UpdateConnectionStatus(True))
                        self.port.write(self.cpacket)
                        self.response = self.port.readline()                                                                      
                        print self.response
                        self.port.close()

class MyFrame(wx.Frame):
        def __init__(self,parent,title):
                super(MyFrame,self).__init__(parent,title=title,size=(550,350),style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)
                self.worker = None # No worker thread yet
                self.controlparameters = ControlParameters(False,False,False,0,0)
                self.InitUI()
                self.populateGUI()
                EVT_RESULT(self,self.updateDisplay)
                EVT_UPDATESTATUS(self,self.UpdateStatus)
                EVT_UPDATECONNECTIONSTATUS(self,self.UpdateConnectionStatus)
                self.Show() 
        def UpdateStatus(self,msg):
                t = msg.data
                self.StatusBar.SetStatusText(t)
        def UpdateConnectionStatus(self,msg):
                t = msg.data
                if (t==True):
                        self.ConnectionStatusValue.SetLabel("Connected")
                else:
                        self.ConnectionStatusValue.SetLabel("Not Connected")
        
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
                self.controlparameters = self.controlparameters._replace(LEDIntensity = self.LightIntensitySlider.GetValue())
        def DirectionalitySliderUpdate(self,evt):
                self.controlparameters = self.controlparameters._replace(Directionality = self.DirectionalitySlider.GetValue())
        def updateDisplay(self,msg):
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
                        self.ParachuteBtn.Disable()
                else: 
                        self.ParachuteStatusValue.SetLabel('CLOSE')
                        self.ParachuteBtn.Enable()
                if t.LEDStatus:
                        self.LEDStatusValue.SetLabel('ON')
                        self.LEDBtn.SetLabel('Turn Off')
                else: 
                        self.LEDStatusValue.SetLabel('OFF')
                        self.LEDBtn.SetLabel('Turn On')
                if t.OptoKineticStatus:
                        self.OptoKineticStatusValue.SetLabel('ON')
                        self.OptoKineticBtn.SetLabel('Turn Off')            
                else:
                        self.OptoKineticStatusValue.SetLabel('OFF')
                        self.OptoKineticBtn.SetLabel('Turn On')
                self.StatusBar.SetStatusText('Ready')
                self.updateGUI(0,t.ErrorStates)
        def SendCommandFnc(self,evt):
                self.StatusBar.SetStatusText('Collating Commands to Send')
                self.worker.ToggleAllowed()
                self.controlthread = ControlWorker(self,self.controlparameters)
                self.worker.ToggleAllowed()
                self.StatusBar.SetStatusText('Commands Sent to Background Thread')
                
                #Logic to Disable buttons after commands have been sent
                
                if (self.controlparameters.ParachuteCommand):
                        self.ParachuteBtn.Disable()
                
                
        def OnCloseWindow(self,event):
                self.worker.Abort()
                self.controlthread.Abort()
                self.Destroy()

        def InitUI(self):
                panel = wx.Panel(self)
                panel.SetBackgroundColour('#FFFFFF')
                
                #---- Need Title and Image -----
                standardfont = wx.Font(8,wx.SWISS,wx.NORMAL,wx.NORMAL)
                #Battery Information
                
                self.BatteryStaticBox = wx.StaticBox(panel,label = 'Battery Information',pos=(290,20),size=(225,120))
                self.BatteryVoltageLabel = wx.StaticText(panel,label='Voltage (V)',style=wx.ALIGN_CENTRE,pos=(300,40))
                self.BatteryVoltageValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,40),size=(50,15))
                self.BatteryCurrentLabel = wx.StaticText(panel,label='Current (I)',style=wx.ALIGN_CENTRE,pos=(300,60))
                self.BatteryCurrentValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,60),size=(50,15))
                self.BatteryPowerLabel = wx.StaticText(panel,label='Power (W)', style=wx.ALIGN_CENTRE,pos = (300,80))
                self.BatteryPowerValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,80),size=(50,15))
                self.BatteryDischargesLabel = wx.StaticText(panel,label='Number of Discharge Cycles',style=wx.ALIGN_CENTRE,pos = (300,100))
                self.BatteryDischargesValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,100),size=(50,15))
                self.BatteryTemperatureLabel = wx.StaticText(panel,label='Temperature (C)',style=wx.ALIGN_CENTRE, pos = (300,120))
                self.BatteryTemperatureValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,120),size=(50,15))
                
                self.BatteryVoltageLabel.SetFont(standardfont)
                self.BatteryVoltageValue.SetFont(standardfont)
                self.BatteryCurrentLabel.SetFont(standardfont)
                self.BatteryCurrentValue.SetFont(standardfont)
                self.BatteryPowerLabel.SetFont(standardfont)
                self.BatteryPowerValue.SetFont(standardfont)
                self.BatteryDischargesLabel.SetFont(standardfont)
                self.BatteryDischargesValue.SetFont(standardfont)
                self.BatteryTemperatureLabel.SetFont(standardfont)
                self.BatteryTemperatureValue.SetFont(standardfont)
                
                
                #System Information
                self.ControlStaticBox = wx.StaticBox(panel,label='Control',pos=(5,20),size=(270,250))
                self.SystemTemperatureLabel = wx.StaticText(panel,label='System Temperature (C)',style=wx.ALIGN_CENTRE,pos = (300,170))
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
                
                self.SystemTemperatureLabel.SetFont(standardfont)
                self.SystemTemperatureValue.SetFont(standardfont)
                self.AltitudeLabel.SetFont(standardfont)
                self.AltitudeValue.SetFont(standardfont)
                self.ParachuteStatusLabel.SetFont(standardfont)
                self.ParachuteStatusValue.SetFont(standardfont)
                self.LEDStatusLabel.SetFont(standardfont)
                self.LEDStatusValue.SetFont(standardfont)
                self.SystemTemperatureLabel.SetFont(standardfont)
                self.SystemTemperatureValue.SetFont(standardfont)

                #Control Parameters

                self.ParachuteLabel = wx.StaticText(panel,label = 'Parachute Status:',pos=(10,52))
                self.ParachuteBtn = wx.ToggleButton(panel,label='Open',pos=(160,50),size=(80,25))
                self.LEDLabel = wx.StaticText(panel,label = 'LED Status:',pos=(10,82))
                self.LEDBtn = wx.ToggleButton(panel,label='Turn On',pos=(160,80),size=(80,25))
                self.OptoKineticLabel = wx.StaticText(panel,label = 'Opto-Kinetic Nystagmus Mode',pos=(10,112))
                self.OptoKineticLabel.Wrap(120)
                self.OptoKineticBtn = wx.ToggleButton(panel,label = 'Turn On',pos=(160,110),size=(80,25))
                self.LightIntensityLabel = wx.StaticText(panel,label = 'Light Intensity', pos=(10,150))
                self.LightIntensitySlider = wx.Slider(panel,-1,25,0,100,(160,140),(100,-1),wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS)
                self.DirectionalityLabel = wx.StaticText(panel,label = 'Directionality', pos=(10,180))
                self.DirectionalitySlider = wx.Slider(panel,-1,0,-90,90,(160,170),(100,-1),wx.SL_AUTOTICKS | wx.SL_HORIZONTAL | wx.SL_LABELS)
                
                self.ParachuteLabel.SetFont(standardfont)
                self.ParachuteBtn.SetFont(standardfont)
                self.LEDLabel.SetFont(standardfont)
                self.LEDBtn.SetFont(standardfont)
                self.OptoKineticLabel.SetFont(standardfont)
                self.OptoKineticBtn.SetFont(standardfont)
                self.LightIntensityLabel.SetFont(standardfont)
                self.LightIntensitySlider.SetFont(standardfont)
                self.DirectionalityLabel.SetFont(standardfont)
                self.DirectionalitySlider.SetFont(standardfont)
                                    
                #Buttons
                self.StartButton = wx.Button(panel,label = 'Start',pos=(465,270),size=(50,20))
                self.UpdateButton = wx.Button(panel,label = 'Update GUI',size=(90,20),pos=(375,270))
                self.MapButton = wx.Button(panel,label = 'Map', pos=(320,270),size = (50,20))
                self.SendCommandBtn = wx.Button(panel,label = 'Send Commands',pos = (145,240),size = (125,25))
                

                self.StartButton.SetFont(standardfont)
                self.UpdateButton.SetFont(standardfont)
                self.MapButton.SetFont(standardfont)
                self.SendCommandBtn.SetFont(standardfont)

                #Connection Status
                self.ConnectionStatusLabel = wx.StaticText(panel,label = 'Connection Status:',pos=(320,5))
                self.ConnectionStatusValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE ,pos=(420,5),size=(100,15))

                

                #Event Listeners
                
                self.Bind(wx.EVT_TOGGLEBUTTON,self.ParachuteBtnPress,self.ParachuteBtn)
                self.Bind(wx.EVT_TOGGLEBUTTON,self.LEDBtnPress,self.LEDBtn)
                self.Bind(wx.EVT_TOGGLEBUTTON,self.OptoKineticBtnPress,self.OptoKineticBtn)
                self.Bind(wx.EVT_SLIDER,self.LightIntensitySliderUpdate,self.LightIntensitySlider)
                self.Bind(wx.EVT_SLIDER,self.DirectionalitySliderUpdate,self.DirectionalitySlider)
                self.Bind(wx.EVT_BUTTON,self.updateGUI,self.UpdateButton)
                self.Bind(wx.EVT_BUTTON,self.openMap,self.MapButton)
                self.Bind(wx.EVT_BUTTON,self.SendCommandFnc,self.SendCommandBtn)
                self.Bind(wx.EVT_BUTTON,self.OnStart,self.StartButton)

                
                #Status Bar
                self.StatusBar = self.CreateStatusBar()
                self.StatusBar.SetStatusText('Ready')
                
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
                
        
        def updateGUI(self,evt,error):
                
                #Update Box Colours
                if self.BatteryVoltageValue.GetLabel() !='-':
                        if (error & 0b1000000000) :
                                self.BatteryVoltageValue.SetBackgroundColour('#FF0000')
                        else:
                                self.BatteryVoltageValue.SetBackgroundColour('#00FF00')
                if self.BatteryCurrentValue.GetLabel() !='-':
                        if (error & 0b0100000000) : 
                                self.BatteryCurrentValue.SetBackgroundColour('#FF0000')
                        else:   
                                self.BatteryCurrentValue.SetBackgroundColour('#00FF00')
                if self.BatteryPowerValue.GetLabel() != '-':
                         if (error & 0b0010000000) :
                                    self.BatteryPowerValue.SetBackgroundColour('#FF0000')
                         else:
                                self.BatteryPowerValue.SetBackgroundColour('#00FF00')
                if self.BatteryDischargesValue.GetLabel() !='-':
                        if (error & 0b0001000000) : 
                                self.BatteryDischargesValue.SetBackgroundColour('#FF0000')
                        else: self.BatteryDischargesValue.SetBackgroundColour('#00FF00')     
                if self.BatteryTemperatureValue.GetLabel() != '-':
                        if (error & 0b0000100000) : 
                                self.BatteryTemperatureValue.SetBackgroundColour('#FF0000')
                        else:
                                self.BatteryTemperatureValue.SetBackgroundColour('#00FF00')
                if self.SystemTemperatureValue.GetLabel() != '-':
                        if (error & 0b0000010000) : 
                                self.SystemTemperatureValue.SetBackgroundColour('#FF0000')
                        else:
                                self.SystemTemperatureValue.SetBackgroundColour('#00FF00')

                if self.AltitudeValue.GetLabel()!='-':
                        if (error & 0b0000001000) : 
                                self.AltitudeValue.SetBackgroundColour('#FF0000')
                        else:
                                self.AltitudeValue.SetBackgroundColour('#00FF00')
                    
                if self.ParachuteStatusValue.GetLabel()!='-':
                        if (error & 0b0000000100) : 
                                self.ParachuteStatusValue.SetBackgroundColour('#FF0000')
                        else:
                                self.ParachuteStatusValue.SetBackgroundColour('#00FF00')
                if self.LEDStatusValue.GetLabel()!='-':
                        if (error & 0b0000000010) : 
                                self.LEDStatusValue.SetBackgroundColour('#FF0000')
                        else:
                                self.LEDStatusValue.SetBackgroundColour('#00FF00')
                if self.OptoKineticStatusValue.GetLabel()!='-':
                        if (error & 0b0000000001):
                                self.OptoKineticStatusValue.SetBackgroundColour('#FF0000')
                        else:
                                self.OptoKineticStatusValue.SetBackgroundColour('#00FF00')
                if self.ConnectionStatusValue.GetLabel() == "Not Connected":
                        self.ConnectionStatusValue.SetBackgroundColour('#FF0000')
                else:
                        self.ConnectionStatusValue.SetBackgroundColour('#00FF00')
                self.Refresh() # have to force a refresh or the colours won't update
        
if __name__ == '__main__':
    app = wx.App(0)
    window = MyFrame(None, title = "Base Station V1") 
    app.MainLoop()

    
