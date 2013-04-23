# -*- coding: cp1252 -*-
from threading import *
import wx
from collections import namedtuple
import crcmod
import serial
import urllib

#---- Declare new Event IDs so Data can be passed to the GUI thread from other threads -----
EVT_RESULT_ID=wx.NewId()
EVT_UPDATESTATUS_ID = wx.NewId()
EVT_UPDATECONNECTIONSTATUS_ID = wx.NewId()
EVT_UPDATEGPSLOCK_ID = wx.NewId()
EVT_UPDATEMAPGUI_ID = wx.NewId()

DataPacket = namedtuple("DataPacket","FlareID PrimBatteryVoltage AuxBatteryVoltage PrimBatteryCurrent AuxBatteryCurrent PrimBatteryPower AuxBatteryPower PrimDischargeCycles AuxDischargeCycles PrimBatteryTemp AuxBatteryTemp SystemTemp LEDLeftTemp LEDRightTemp OutsideTemp Altitude ParachuteStatus LEDStatus LEDBrightness OptoKineticStatus Acceleration ErrorStates BaseTime BaseLong BaseLat")                
ControlParameters = namedtuple("ControlParameters", "LEDCommand LEDIntensity OptoKinetic Directionality ParachuteCommand")

#---- Classes and Functions used for the new Event IDs ----
def EVT_RESULT(win,func):
        win.Connect(-1,01,EVT_RESULT_ID,func)
def EVT_UPDATESTATUS(win,func):        
        win.Connect(-1,01,EVT_UPDATESTATUS_ID,func)
def EVT_UPDATECONNECTIONSTATUS(win,func):
        win.Connect(-1,01,EVT_UPDATECONNECTIONSTATUS_ID,func)
def EVT_UPDATEGPSLOCK(win,func):
        win.Connect(-1,01,EVT_UPDATEGPSLOCK_ID,func)
def EVT_UPDATEMAPGUI(win,func):
        win.Connect(-1,01,EVT_UPDATEMAPGUI_ID,func)
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
class UpdateGPSLock(wx.PyEvent):
        def __init__(self,data):
                wx.PyEvent.__init__(self)
                self.SetEventType(EVT_UPDATEGPSLOCK_ID)
                self.data = data
class UpdateMapGUI(wx.PyEvent):
        def __init__(self,data):
                wx.PyEvent.__init__(self)
                self.SetEventType(EVT_UPDATEMAPGUI_ID)
                self.data = data
class FlareDataWorker(Thread):
        ExitCode = 0
        allowed = True
        FlareData = DataPacket(1,40,5,30,5,1200,25,2,0,50,30,70,65,65,15,800,True,True,50,False, 25,0b0000000000000000,0,0,0)
        rFlareData = DataPacket(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)
        port = serial.Serial() #9600, 8, N, 1
        port.port = 5 #Device is on Port 3. Zero Indexed. Port 6 on Netbook
        port.baudrate = 9600
        def __init__(self,wxObject,wxObjectMap):
                Thread.__init__(self)
                self.wxObject = wxObject
                self.wxObjectMap = wxObjectMap
                self.start()
                self.ExitCode = 0
                self.rpacket = 0b0
                self.gpsData = 0b0
        def unpackGPS(self):
                #----- Format of gpsDataArray -------
                # Element 0 : Packet Type. In Normal operation it will be $GPGGA
                # Element 1 : Time
                #         2 : Latitude
                #         3 : N/S Indicactor
                #         4 : Longitude
                #         5 : E/WIndicactor
                #         6 : Position Fix Indicator
                #         7 : Satellites Used
                #         8 : HDOP
                #         9 : MSL Altitude
                #         10: Units
                #         11: Geoid Seperation
                #         12: Units
                #         13: Age of Diff Corr.
                #         14: Checksum
                #         15: End of Message
                
                self.gpsDataArray = [x.strip() for x in self.gpsData.split(',')] # Strips commas from the CSV line received by the GPS module

                # ---- Format Time -----
                time_int = int(float(self.gpsDataArray[1])) # Essentially floors the time to the nearest second
                
                time_list = list(str(time_int)) #Seperates the time into a list. For example, 104256 (10:42:56) will be '1','0','4','2','5','6'
                if len(time_list) == 5: # If the time starts with a 0, it will be dropped (0940 for example). If length == 5, add an extra 0 to make it 6 long
                        time_list.insert(0,'0') #Add an extra 0 so the time is 
                time_list.insert(2,':') #Adds in the colon seperators in the time. Inserts the : before time_list[2]
                time_list.insert(5,':')
                time_list.append(' (UTC)') 
                time_str = "".join(time_list) #Converts list to a string
                
                self.rFlareData = self.rFlareData._replace(BaseTime = time_str,
                                                           BaseLat = self.gpsDataArray[2] + self.gpsDataArray[3],
                                                           BaseLong = self.gpsDataArray[4] +self.gpsDataArray[5],
                                                         )
                
                # Check if there is GPS Lock
                if self.gpsDataArray[2] == '': #If a null string, GPS lock has not been achieved
                        wx.PostEvent(self.wxObject,UpdateGPSLock(False))
                        print self.gpsData
                else:
                        wx.PostEvent(self.wxObject,UpdateGPSLock(True))
                        wx.PostEvent(self.wxObjectMap,UpdateMapGUI(self.gpsDataArray))
                
                        
        def UnpackPacket(self):
                
                # Packet Shape
                # Start Sequence           :1001
                # Flare ID                 :4 bit
                # Primary Voltage          :8 bit
                # Aux. Voltage             :8 bit
                # Primary Current          :8 bit
                # Aux. Current             :8 bit                
                # PrimaryDischargeCycles   :8 bit
                # PrimaryBatteryTemp       :8 bit
                # AuxBatteryTemp           :8 bit
                # SystemTemp               :8 bit
                # LED Left Wing Temp       :8 bit
                # LED Right Wing Temp      :8 bit
                # Outside Temp             :8 bit
                # Altitude                 :12 bit
                # ParachuteStatus          :4 bit
                # LEDStatus                :4 bit
                # OptoKineticStatus        :4 bit                      
                # ErrorStateFlags          :10 bit
                # CRC                      :32bit
                # End Sequence             :1010               
                # Total Size               :166 bit
                          
                self.rpacket = self.rpacket >> 4
                crcrec = self.rpacket & 0b11111111111111111111111111111111
                #Calculate CRC and check if it's equal.
                self.rpacket = self.rpacket >> 32
                dataToCRC = self.rpacket & 0x0000CFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
                crc32_func = crcmod.mkCrcFun(0x104c11db7, initCrc=0, xorOut=0xFFFFFFFF)
                crccalc = crc32_func(str(dataToCRC))
                if crccalc!=crcrec:
                        print "There has been an error. Discard Data"
                        return -1
                # Need conditions to see when these are true or false when 1111 or 0000 
                self.rFlareData = self.rFlareData._replace(ErrorStates = self.rpacket & 0b1111111111)
                self.rpacket = self.rpacket >> 10
                self.rFlareData = self.rFlareData._replace(OptoKineticStatus = self.rpacket & 0b1111)            
                self.rpacket = self.rpacket >> 4
                self.rFlareData = self.rFlareData._replace(LEDBrightness = self.rpacket & 0b11111111)
                self.rpacket = self.rpacket >> 8
                self.rFlareData = self.rFlareData._replace(LEDStatus = self.rpacket & 0b1111)
                self.rpacket = self.rpacket >> 4
                self.rFlareData = self.rFlareData._replace(ParachuteStatus = self.rpacket & 0b1111)
                self.rpacket = self.rpacket >> 4
                self.rFlareData = self.rFlareData._replace(Altitude = self.rpacket & 0b111111111111)
                self.rpacket = self.rpacket >> 12
                self.rFlareData = self.rFlareData._replace(OutsideTemp = self.rpacket & 0b11111111)
                self.rpacket = self.rpacket >> 8
                self.rFlareData = self.rFlareData._replace(LEDRightTemp = self.rpacket & 0b11111111)
                self.rpacket = self.rpacket >> 8
                self.rFlareData = self.rFlareData._replace(LEDLeftTemp = self.rpacket & 0b11111111)
                self.rpacket = self.rpacket >> 8
                self.rFlareData = self.rFlareData._replace(SystemTemp = self.rpacket & 0b11111111)
                self.rpacket = self.rpacket >> 8
                self.rFlareData = self.rFlareData._replace(AuxBatteryTemp = self.rpacket & 0b11111111)
                self.rpacket = self.rpacket >> 8
                self.rFlareData = self.rFlareData._replace(PrimBatteryTemp = self.rpacket & 0b11111111)
                self.rpacket = self.rpacket >> 8
                self.rFlareData = self.rFlareData._replace(AuxDischargeCycles = self.rpacket & 0b11111111)
                self.rpacket = self.rpacket >> 8
                self.rFlareData = self.rFlareData._replace(PrimDischargeCycles = self.rpacket & 0b11111111)
                self.rpacket = self.rpacket >> 8
                self.rFlareData = self.rFlareData._replace(AuxBatteryCurrent = self.rpacket & 0b11111111)
                self.rpacket = self.rpacket >> 8
                self.rFlareData = self.rFlareData._replace(PrimBatteryCurrent = self.rpacket & 0b11111111)
                self.rpacket = self.rpacket >> 8
                self.rFlareData = self.rFlareData._replace(AuxBatteryVoltage = self.rpacket & 0b11111111)
                self.rpacket = self.rpacket >> 8
                self.rFlareData = self.rFlareData._replace(PrimBatteryVoltage = self.rpacket & 0b11111111)
                self.rpacket = self.rpacket >> 8                
                self.rFlareData = self.rFlareData._replace(FlareID = self.rpacket & 0b1111)
                self.rpacket = self.rpacket >> 4                
                self.unpackGPS()

        def run(self):
                while (self.ExitCode == 0):   
                        self.ReceiveData() 
                        error = self.UnpackPacket()
                        if error == -1:
                                print "Packet is Ignored"
                                continue
                        wx.PostEvent(self.wxObject,ResultEvent(self.rFlareData))#send to GUI                                               
                        
        def ReceiveData(self):
               # ---- Function used to retrieve and format the received signal correctly ----
        
               if (self.allowed): #self.allowed is a variable used when a command is waiting to be sent
                       try:
                               self.port.open()
                       except serial.SerialException as e:
                               print "Error({0}): {1}".format(e.errno,e.strerror)
                               wx.PostEvent(self.wxObject,UpdateConnectionStatus(False))
                       else:
                               handshake = '0110001'
                               self.port.write(handshake)
                               response = self.port.read(7)
                               wx.PostEvent(self.wxObject,UpdateConnectionStatus(True))
                               self.rpacket = int(self.port.read(55))
                               self.gpsData = self.port.readline()
                               
                               
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
        port.port = 5 #Device is on Port 3. Zero indexed. Port 6 on netbook
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
                wx.PostEvent(self.wxObject,UpdateStatusEvent("Sending Packet"))
                
        def PackPacket(self):
                # Packet Shape
                # Start flag          : 1100
                # LEDCommands Flag    : 2 bit
                # Light Intensity Flag : 4 bit
                # OptoKineticFlag     : 2 bit
                # Directionality Flag : 8 bit
                # Parachute Flag      : 2 bit
                # CRC                :
                # End Flag           : 0011
               # Need to have if statements for LED command, parachute, and optokinetic.
               # if LED command == True: + 11 else 00
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
                super(MyFrame,self).__init__(parent,title=title,size=(760,350),style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)
                self.worker = None # No worker thread yet
                self.controlparameters = ControlParameters(False,False,False,0,0)
                self.InitUI()
                self.populateGUI()
                self.MapWindow = MapFrame()
                EVT_RESULT(self,self.updateDisplay)
                EVT_UPDATESTATUS(self,self.UpdateStatus)
                EVT_UPDATECONNECTIONSTATUS(self,self.UpdateConnectionStatus)
                EVT_UPDATEGPSLOCK(self,self.UpdateGPSLock)
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
        def UpdateGPSLock(self,msg):
                t = msg.data
                if (t==True):
                        self.GPSStatusValue.SetLabel("GPS Lock")
                else:
                        self.GPSStatusValue.SetLabel("No GPS Lock")
                
        
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
                self.StatusBar.SetStatusText('Localisation Map has been opened')
                self.MapWindow.Show()
                
        def OnStart(self,event):
                if self.StartButton.GetLabel() == "Start":
                        if not self.worker:
                                self.StatusBar.SetStatusText('Starting to collect data')
                                self.worker=FlareDataWorker(self,self.MapWindow)
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
                self.FlareIDValue.SetLabel(str(t.FlareID))
                self.PrimBatteryVoltageValue.SetLabel(str(t.PrimBatteryVoltage))
                self.PrimBatteryCurrentValue.SetLabel(str(t.PrimBatteryCurrent))
                self.PrimBatteryPowerValue.SetLabel(str(t.PrimBatteryVoltage * t.PrimBatteryCurrent))
                self.PrimBatteryDischargesValue.SetLabel(str(t.PrimDischargeCycles))
                self.PrimBatteryTemperatureValue.SetLabel(str(t.PrimBatteryTemp))                
                self.AuxBatteryVoltageValue.SetLabel(str(t.AuxBatteryVoltage))
                self.AuxBatteryCurrentValue.SetLabel(str(t.AuxBatteryCurrent))
                self.AuxBatteryPowerValue.SetLabel(str(t.AuxBatteryVoltage * t.AuxBatteryCurrent))
                self.AuxBatteryDischargesValue.SetLabel(str(t.AuxDischargeCycles))
                self.AuxBatteryTemperatureValue.SetLabel(str(t.AuxBatteryTemp))
                self.AltitudeValue.SetLabel(str(t.Altitude))
                self.LEDBrightnessValue.SetLabel(str(t.LEDBrightness))
                self.AccelerationValue.SetLabel(str(t.Acceleration))
                self.SystemTemperatureValue.SetLabel(str(t.SystemTemp))
                self.LEDLeftValue.SetLabel(str(t.LEDLeftTemp))
                self.LEDRightValue.SetLabel(str(t.LEDRightTemp))
                self.OutsideValue.SetLabel(str(t.OutsideTemp))
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
                self.BaseLatValue.SetLabel(str(t.BaseLat))
                self.BaseLongValue.SetLabel(str(t.BaseLong))
                self.TimeValue.SetLabel(str(t.BaseTime))
                self.StatusBar.SetStatusText('Ready')
                self.updateGUI(0,t.ErrorStates)
        def SendCommandFnc(self,evt):
                self.StatusBar.SetStatusText('Collating Commands to Send')
                if self.worker != None:             
                        self.worker.ToggleAllowed()
                self.controlthread = ControlWorker(self,self.controlparameters)
                if self.worker !=None:
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
                
                self.BatteryStaticBox = wx.StaticBox(panel,label = 'Battery Information',pos=(290,20),size=(275,120))
                self.PrimBatteryLabel = wx.StaticText(panel,label='Primary',pos=(460,25))
                self.PrimBatteryVoltageLabel = wx.StaticText(panel,label='Voltage (V)',style=wx.ALIGN_CENTRE,pos=(300,40))
                self.PrimBatteryVoltageValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,40),size=(50,15))
                self.PrimBatteryCurrentLabel = wx.StaticText(panel,label='Current (I)',style=wx.ALIGN_CENTRE,pos=(300,60))
                self.PrimBatteryCurrentValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,60),size=(50,15))
                self.PrimBatteryPowerLabel = wx.StaticText(panel,label='Power (W)', style=wx.ALIGN_CENTRE,pos = (300,80))
                self.PrimBatteryPowerValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,80),size=(50,15))
                self.PrimBatteryDischargesLabel = wx.StaticText(panel,label='Number of Discharge Cycles',style=wx.ALIGN_CENTRE,pos = (300,100))
                self.PrimBatteryDischargesValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,100),size=(50,15))
                self.PrimBatteryTemperatureLabel = wx.StaticText(panel,label='Temperature (°C)',style=wx.ALIGN_CENTRE, pos = (300,120))
                self.PrimBatteryTemperatureValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,120),size=(50,15))
                
                self.PrimBatteryVoltageLabel.SetFont(standardfont)
                self.PrimBatteryVoltageValue.SetFont(standardfont)
                self.PrimBatteryCurrentLabel.SetFont(standardfont)
                self.PrimBatteryCurrentValue.SetFont(standardfont)
                self.PrimBatteryPowerLabel.SetFont(standardfont)
                self.PrimBatteryPowerValue.SetFont(standardfont)
                self.PrimBatteryDischargesLabel.SetFont(standardfont)
                self.PrimBatteryDischargesValue.SetFont(standardfont)
                self.PrimBatteryTemperatureLabel.SetFont(standardfont)

                #Location Information

                self.LocationBox = wx.StaticBox(panel,label = 'Location Information',pos=(570,20),size=(170,120))
                self.BaseLatLabel = wx.StaticText(panel,label = 'Base Latitude',pos = (580,40),style = wx.ALIGN_CENTRE)
                self.BaseLatValue = wx.StaticText(panel,style = wx.ALIGN_CENTER | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos = (660,40),size=(70,15))
                self.BaseLongLabel = wx.StaticText(panel,label = 'Base Longitude',pos = (580,60),style = wx.ALIGN_CENTRE)
                self.BaseLongValue = wx.StaticText(panel,style = wx.ALIGN_CENTER | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos = (660,60),size=(70,15))
                self.FlareLatLabel = wx.StaticText(panel,label = 'Flare Latitude',pos = (580,80),style = wx.ALIGN_CENTRE)
                self.FlareLatValue = wx.StaticText(panel,style = wx.ALIGN_CENTER | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos = (660,80),size=(70,15))
                self.FlareLongLabel = wx.StaticText(panel,label = 'Flare Longitude',pos = (580,100),style = wx.ALIGN_CENTRE)
                self.FlareLongValue = wx.StaticText(panel,style = wx.ALIGN_CENTER | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos = (660,100),size=(70,15))

                self.BaseLatLabel.SetFont(standardfont)
                self.BaseLatValue.SetFont(standardfont)
                self.BaseLongLabel.SetFont(standardfont)
                self.BaseLongValue.SetFont(standardfont)
                self.FlareLatLabel.SetFont(standardfont)
                self.FlareLatValue.SetFont(standardfont)
                self.FlareLongLabel.SetFont(standardfont)
                self.FlareLongValue.SetFont(standardfont)
                
                
                
                #Auxilary Battery Information

                self.AuxBatteryLabel = wx.StaticText(panel,label='Auxillary',pos=(515,25))
                self.AuxBatteryVoltageValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(510,40),size=(50,15))
                self.AuxBatteryCurrentValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(510,60),size=(50,15))
                self.AuxBatteryPowerValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(510,80),size=(50,15))
                self.AuxBatteryDischargesValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(510,100),size=(50,15))
                self.AuxBatteryTemperatureValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(510,120),size=(50,15))
                
                self.AuxBatteryVoltageValue.SetFont(standardfont)
                self.AuxBatteryCurrentValue.SetFont(standardfont)
                self.AuxBatteryPowerValue.SetFont(standardfont)
                self.AuxBatteryDischargesValue.SetFont(standardfont)
                self.AuxBatteryTemperatureValue.SetFont(standardfont)
                
                #System Information

                self.SystemStaticBox = wx.StaticBox(panel,label='System Information',pos = (290,150), size=(225,140))
                self.AltitudeLabel = wx.StaticText(panel,label='Altitude (m)',style=wx.ALIGN_CENTRE,pos = (300,170))
                self.AltitudeValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,170),size=(50,15))
                self.ParachuteStatusLabel = wx.StaticText(panel,label='Parachute Status',style=wx.ALIGN_CENTRE, pos = (300,190))
                self.ParachuteStatusValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,190),size=(50,15))
                self.LEDStatusLabel = wx.StaticText(panel,label='LED Status',style=wx.ALIGN_CENTRE,pos= (300,210))
                self.LEDStatusValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE ,pos=(450,210),size=(50,15))
                self.LEDBrightnessLabel = wx.StaticText(panel,label='LED Brightness',style=wx.ALIGN_CENTRE,pos=(300,230))
                self.LEDBrightnessValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(450,230),size=(50,15))
                self.OptoKineticStatusLabel = wx.StaticText(panel,label = 'Optokinetic Nystagmus', style = wx.ALIGN_CENTRE,pos = (300,250))
                self.OptoKineticStatusValue = wx.StaticText(panel,style = wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE, pos = (450,250), size = (50,15))
                self.AccelerationLabel= wx.StaticText(panel,label = 'Acceleration (ms-1)',style = wx.ALIGN_CENTRE, pos = (300,270))
                self.AccelerationValue = wx.StaticText(panel,style = wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE, pos = (450,270), size = (50,15))
                
                self.AltitudeLabel.SetFont(standardfont)
                self.AltitudeValue.SetFont(standardfont)
                self.ParachuteStatusLabel.SetFont(standardfont)
                self.ParachuteStatusValue.SetFont(standardfont)
                self.LEDStatusLabel.SetFont(standardfont)
                self.LEDStatusValue.SetFont(standardfont)
                self.OptoKineticStatusLabel.SetFont(standardfont)
                self.OptoKineticStatusValue.SetFont(standardfont)
                self.AccelerationLabel.SetFont(standardfont)
                self.AccelerationValue.SetFont(standardfont)

                #Temperature
                self.TemperatureStaticBox=wx.StaticBox(panel,label='Temperatures',pos=(525,150),size=(225,120))
                self.SystemTemperatureLabel = wx.StaticText(panel,label='System Temperature (°C)',style=wx.ALIGN_CENTRE,pos = (535,170))
                self.SystemTemperatureValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(695,170),size=(50,15))
                self.LEDLeftLabel = wx.StaticText(panel,label='LED Left Wing Temperature (°C)',style=wx.ALIGN_CENTRE,pos=(535,190))
                self.LEDLeftValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(695,190),size=(50,15))
                self.LEDRightLabel = wx.StaticText(panel,label='LED Right Wing Temperature (°C)',style=wx.ALIGN_CENTRE,pos=(535,210))
                self.LEDRightValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(695,210),size=(50,15))
                self.OutsideLabel = wx.StaticText(panel,label='Outside Temperature (°C)',style=wx.ALIGN_CENTRE,pos=(535,230))
                self.OutsideValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(695,230),size=(50,15))
                
                

                self.SystemTemperatureLabel.SetFont(standardfont)
                self.SystemTemperatureValue.SetFont(standardfont)
                self.LEDLeftLabel.SetFont(standardfont)
                self.LEDLeftValue.SetFont(standardfont) 
                self.LEDRightLabel.SetFont(standardfont)
                self.LEDRightValue.SetFont(standardfont)
                self.OutsideLabel.SetFont(standardfont)
                self.OutsideValue.SetFont(standardfont)
                #Control Parameters

                self.ControlStaticBox = wx.StaticBox(panel,label='Control',pos=(5,20),size=(270,270))
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
                self.StartButton = wx.Button(panel,label = 'Start',pos=(700,270),size=(50,20))
                self.MapButton = wx.Button(panel,label = 'Map', pos=(650,270),size = (50,20))
                self.SendCommandBtn = wx.Button(panel,label = 'Send Commands',pos = (145,240),size = (125,25))
                

                self.StartButton.SetFont(standardfont)
                self.MapButton.SetFont(standardfont)
                self.SendCommandBtn.SetFont(standardfont)

                #Connection Status
                self.ConnectionStatusLabel = wx.StaticText(panel,label = 'Connection Status:',pos=(320,5))
                self.ConnectionStatusValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE ,pos=(420,5),size=(100,15))
                self.ConnectionStatusLabel.SetFont(standardfont)
                self.ConnectionStatusValue.SetFont(standardfont)

                #GPS Status
                self.GPSStatusLabel = wx.StaticText(panel,label = 'GPS Status:',pos = (530,5))
                self.GPSStatusValue = wx.StaticText(panel,style = wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(590,5),size=(100,15))
                                                    

                #Event Listeners
                
                self.Bind(wx.EVT_TOGGLEBUTTON,self.ParachuteBtnPress,self.ParachuteBtn)
                self.Bind(wx.EVT_TOGGLEBUTTON,self.LEDBtnPress,self.LEDBtn)
                self.Bind(wx.EVT_TOGGLEBUTTON,self.OptoKineticBtnPress,self.OptoKineticBtn)
                self.Bind(wx.EVT_SLIDER,self.LightIntensitySliderUpdate,self.LightIntensitySlider)
                self.Bind(wx.EVT_SLIDER,self.DirectionalitySliderUpdate,self.DirectionalitySlider)
                self.Bind(wx.EVT_BUTTON,self.openMap,self.MapButton)
                self.Bind(wx.EVT_BUTTON,self.SendCommandFnc,self.SendCommandBtn)
                self.Bind(wx.EVT_BUTTON,self.OnStart,self.StartButton)
                
                #Machine ID
                self.FlareIDLabel = wx.StaticText(panel,label = 'Flare ID:', pos=(10,5))
                self.FlareIDValue= wx.ComboBox(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE ,pos=(70,2),size=(100,15))
                self.FlareIDLabel.SetFont(standardfont)
                self.FlareIDValue.SetFont(standardfont) 
                #Time

                self.TimeLabel = wx.StaticText(panel,label = 'Time:', pos = (180,5))
                self.TimeValue = wx.StaticText(panel,style = wx.ALIGN_CENTRE, pos=(210,5), size = (50,15))
                #Status Bar
                self.StatusBar = self.CreateStatusBar()
                self.StatusBar.SetStatusText('Ready')
                
        def populateGUI(self):
                #Temporary Function to initially populate values to test colours etc.
                self.PrimBatteryVoltageValue.SetLabel('-')
                self.PrimBatteryCurrentValue.SetLabel('-')
                self.PrimBatteryPowerValue.SetLabel('-')
                self.PrimBatteryDischargesValue.SetLabel('-')
                self.PrimBatteryTemperatureValue.SetLabel('-')
                self.SystemTemperatureValue.SetLabel('-')
                self.AltitudeValue.SetLabel('-')
                self.ParachuteStatusValue.SetLabel('-')
                self.LEDStatusValue.SetLabel('-')
                self.LEDBrightnessValue.SetLabel('-')
                self.OptoKineticStatusValue.SetLabel('-')
                self.AccelerationValue.SetLabel('-')
                self.AuxBatteryVoltageValue.SetLabel('-')
                self.AuxBatteryCurrentValue.SetLabel('-')
                self.AuxBatteryPowerValue.SetLabel('-')
                self.AuxBatteryDischargesValue.SetLabel('-')
                self.AuxBatteryTemperatureValue.SetLabel('-')
                self.LEDLeftValue.SetLabel('-')
                self.LEDRightValue.SetLabel('-')
                self.OutsideValue.SetLabel('-')
                self.BaseLatValue.SetLabel('-')
                self.BaseLongValue.SetLabel('-')
                self.FlareLatValue.SetLabel('-')
                self.FlareLongValue.SetLabel('-')
                self.GPSStatusValue.SetLabel('No GPS Lock')
                self.ConnectionStatusValue.SetLabel('Not Connected')
                self.FlareIDValue.SetLabel('Not Connected')
                         
        def updateGUI(self,evt,error):
                # ----- Error State Flags ------
                # Bit 0: Primary Battery Voltage Error
                # Bit 1: Primary Battery Current Error
                # Bit 2: Primary Battery Power Error
                # Bit 3: Primary Battery Discharge Value Error
                # Bit 4: Primary Battery Temperature Error
                # Bit 5: Aux Battery Voltage Error
                # Bit 6: Aux Battery Current Error
                # Bit 7: Aux Battery Power Error
                # Bit 8: Aux Battery Discharge Value Error
                # Bit 9: Aux Battery Temperature Error
                # Bit 10:
                # Bit 11
                
                #Update Box Colours
                if self.PrimBatteryVoltageValue.GetLabel() !='-':
                        if (error & 0b10000000000000000000) :
                                self.PrimBatteryVoltageValue.SetBackgroundColour('#FF0000')
                        else:
                                self.PrimBatteryVoltageValue.SetBackgroundColour('#00FF00')
                if self.PrimBatteryCurrentValue.GetLabel() !='-':
                        if (error & 0b01000000000000000000) : 
                                self.PrimBatteryCurrentValue.SetBackgroundColour('#FF0000')
                        else:   
                                self.PrimBatteryCurrentValue.SetBackgroundColour('#00FF00')
                if self.PrimBatteryPowerValue.GetLabel() != '-':
                         if (error & 0b00100000000000000000) :
                                    self.PrimBatteryPowerValue.SetBackgroundColour('#FF0000')
                         else:
                                    self.PrimBatteryPowerValue.SetBackgroundColour('#00FF00')
                if self.PrimBatteryDischargesValue.GetLabel() !='-':
                        if (error & 0b000100000000000000000) : 
                                self.PrimBatteryDischargesValue.SetBackgroundColour('#FF0000')
                        else:
                                self.PrimBatteryDischargesValue.SetBackgroundColour('#00FF00')     
                if self.PrimBatteryTemperatureValue.GetLabel() != '-':
                        if (error & 0b000010000000000000000) : 
                                self.PrimBatteryTemperatureValue.SetBackgroundColour('#FF0000')
                        else:
                                self.PrimBatteryTemperatureValue.SetBackgroundColour('#00FF00')
                if self.AuxBatteryVoltageValue.GetLabel()!='-':
                        if (error &  0b000001000000000000000):
                                self.AuxBatteryVoltageValue.SetBackgroundColour('#FF0000')
                        else:
                                self.AuxBatteryVoltageValue.SetBackgroundColour('#00FF00')
                if self.AuxBatteryCurrentValue.GetLabel() !='-':
                        if (error &  0b00000010000000000000) : 
                                self.AuxBatteryCurrentValue.SetBackgroundColour('#FF0000')
                        else:   
                                self.AuxBatteryCurrentValue.SetBackgroundColour('#00FF00')
                if self.AuxBatteryPowerValue.GetLabel() != '-':
                         if (error & 0b00000001000000000000) :
                                    self.AuxBatteryPowerValue.SetBackgroundColour('#FF0000')
                         else:
                                self.AuxBatteryPowerValue.SetBackgroundColour('#00FF00')
                if self.AuxBatteryDischargesValue.GetLabel() !='-':
                        if (error &  0b00000000100000000000) : 
                                self.AuxBatteryDischargesValue.SetBackgroundColour('#FF0000')
                        else:
                                self.AuxBatteryDischargesValue.SetBackgroundColour('#00FF00')     
                if self.AuxBatteryTemperatureValue.GetLabel() != '-':
                        if (error &  0b00000000010000000000) : 
                                self.AuxBatteryTemperatureValue.SetBackgroundColour('#FF0000')
                        else:
                                self.AuxBatteryTemperatureValue.SetBackgroundColour('#00FF00')
                if self.SystemTemperatureValue.GetLabel() != '-':
                        if (error & 0b00000000001000000000) : 
                                self.SystemTemperatureValue.SetBackgroundColour('#FF0000')
                        else:
                                self.SystemTemperatureValue.SetBackgroundColour('#00FF00')
                if self.LEDLeftValue.GetLabel() != '-':
                        if (error & 0b0000000000100000000) : 
                                self.LEDLeftValue.SetBackgroundColour('#FF0000')
                        else:
                                self.LEDLeftValue.SetBackgroundColour('#00FF00')
                if self.LEDRightValue.GetLabel() != '-':
                        if (error & 0b000000000010000000) : 
                                self.LEDRightValue.SetBackgroundColour('#FF0000')
                        else:
                                self.LEDRightValue.SetBackgroundColour('#00FF00')
                if self.OutsideValue.GetLabel() != '-':
                        if (error & 0b00000000001000000) : 
                                self.OutsideValue.SetBackgroundColour('#FF0000')
                        else:
                                self.OutsideValue.SetBackgroundColour('#00FF00')
                if self.AltitudeValue.GetLabel()!='-':
                        if (error & 0b00000000000100000) : 
                                self.AltitudeValue.SetBackgroundColour('#FF0000')
                        else:
                                self.AltitudeValue.SetBackgroundColour('#00FF00')
                    
                if self.ParachuteStatusValue.GetLabel()!='-':
                        if (error & 0b00000000000010000) : 
                                self.ParachuteStatusValue.SetBackgroundColour('#FF0000')
                        else:
                                self.ParachuteStatusValue.SetBackgroundColour('#00FF00')
                if self.LEDStatusValue.GetLabel()!='-':
                        if (error & 0b00000000000001000) : 
                                self.LEDStatusValue.SetBackgroundColour('#FF0000')
                        else:
                                self.LEDStatusValue.SetBackgroundColour('#00FF00')
                if self.LEDBrightnessValue.GetLabel()!='-':
                        if (error & 0b00000000000000100) : 
                                self.LEDBrightnessValue.SetBackgroundColour('#FF0000')
                        else:
                                self.LEDBrightnessValue.SetBackgroundColour('#00FF00')
                if self.OptoKineticStatusValue.GetLabel()!='-':
                        if (error & 0b000000000000000010):
                                self.OptoKineticStatusValue.SetBackgroundColour('#FF0000')
                        else:
                                self.OptoKineticStatusValue.SetBackgroundColour('#00FF00')
                if self.AccelerationValue.GetLabel()!='-':
                        if (error & 0b0000000000000000001):
                                self.AccelerationValue.SetBackgroundColour('#FF0000')
                        else:
                                self.AccelerationValue.SetBackgroundColour('#00FF00')
                if self.ConnectionStatusValue.GetLabel() == "Not Connected":
                        self.ConnectionStatusValue.SetBackgroundColour('#FF0000')
                else:
                        self.ConnectionStatusValue.SetBackgroundColour('#00FF00')

                if self.FlareIDLabel.GetLabel() == "Not Connected":
                        self.FlareIDValue.SetBackgroundColour('#FF0000')
                else: 
                        self.FlareIDValue.SetBackgroundColour('#00FF00')
                if self.GPSStatusValue.GetLabel()=="No GPS Lock":
                        self.GPSStatusValue.SetBackgroundColour('#FF0000')
                else:
                        self.GPSStatusValue.SetBackgroundColour('#00FF00')
                self.Refresh() # have to force a refresh or the colours won't update
class MapFrame(wx.Frame):
        title = "Localisation Map Window"
        def __init__(self):
                wx.Frame.__init__(self,wx.GetApp().TopWindow,title = self.title,size=(800,350),style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)
                self.initUI()
                EVT_UPDATEMAPGUI(self,self.UpdateMapGUI)                
        def initUI(self):
                panel = wx.Panel(self)
                panel.SetBackgroundColour('#FFFFFF')
                imageFile = 'C:\Users\James\Documents\Github\TestImage.jpg'
                png = wx.Image(imageFile,wx.BITMAP_TYPE_ANY).ConvertToBitmap()
                self.imageMap = wx.StaticBitmap(panel,-1,png,(10,5),(png.GetWidth(),png.GetHeight()),style = wx.BORDER_SIMPLE)
                self.imageMap.Hide()
                #Legend
                baseStationBox = wx.StaticBox(panel, label = 'Base Station Information (B)',pos = (620,5),size=(150,50))
                baseAltitudeLabel = wx.StaticText(panel,label = 'Altitude (m)',pos = (630,30),style = wx.ALIGN_CENTRE)
                self.baseAltitudeValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(690,30),size=(50,15))
                

                flareBox= wx.StaticBox(panel,label = 'Flare Information (F)',pos = (620,70),size = (135,50))
                baseAltitudeLabel = wx.StaticText(panel,label = 'Altitude (m)',pos = (630,95),style = wx.ALIGN_CENTRE)
                self.baseAltitudeValue = wx.StaticText(panel,style=wx.ALIGN_CENTRE | wx.BORDER_SIMPLE | wx.ST_NO_AUTORESIZE,pos=(690,95),size=(50,15))
                
                
        def UpdateMapGUI(self,msg):
                t = msg.data
                t[2] = float(t[2]) / 100;
                if t[3] == "S":
                         t[2] = - t[2]
                t[4] = float(t[4]) / 100;
                if t[5] == "W":
                        t[4] = - t[4]

                markerBase = str(t[2]) + ',' + str(t[4])
                markerFlare = ''
                self.generateURL(markerBase, markerFlare)
                self.updateMap()
                
                
        def generateURL(self,markersBase="51.3794,-2.3656",markersFlare="51.3740,-2.3656"): #Default values used for testing
                url = "http://maps.googleapis.com/maps/api/staticmap?&zoom=13&size=600x300&maptype=terrain&key=AIzaSyDwM32NaJvF8682ThC_5zJp3V2deqHfyGo&sensor=true"
                url+="&markers=color:blue%7Clabel:B%7C" + markersBase
                url+= "&markers=color:red%7Clabel:F%7C" + markersFlare
                urllib.urlretrieve(url,'NewMapV2.png')
        def updateMap(self):
                directory = 'C:\Users\James\Documents\Github\GDBP-BaseStation\NewMapV2.png'
                newMap = wx.Image(directory,wx.BITMAP_TYPE_ANY).ConvertToBitmap()
                self.imageMap.SetBitmap(newMap)
                self.imageMap.Show()
                
if __name__ == '__main__':
    app = wx.App(0)
    window = MyFrame(None, title = "Base Station V1") 
    app.MainLoop()

    
