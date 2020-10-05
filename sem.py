#
# SharkSEM Script
# version 2.0.16
#
# Requires Python 3.x
#
# Copyright (c) 2014 TESCAN Brno, s.r.o.
# http://www.tescan.com
#

#
# main SEM interface class
#

import sem_conn

class Sem:
    """Tescan SEM Control Class
    
    Main purpose is to provide a wrapper which allows any Python application 
    to control Tescan SEM. Internaly, there is a wrapper around the SharkSEM
    remote control protocol.
    
    Your Python script requires only this class.
    
    See SharkSEM documentation for more information.
    """
    
    def __init__(self):
        """Constructor"""
        self.connection = sem_conn.SemConnection()
        
    def _CInt(self, arg):
        return (sem_conn.ArgType.Int, int(arg))
        
    def _CArrayInt(self, arg):
        return (sem_conn.ArgType.ArrayInt, arg)

    def _CUnsigned(self, arg):
        return (sem_conn.ArgType.UnsignedInt, int(arg))

    def _CArrayUnsigned(self, arg):
        return (sem_conn.ArgType.ArrayUnsignedInt, arg)

    def _CFloat(self, arg):
        return (sem_conn.ArgType.Float, float(arg))
    
    def _CString(self, arg):
        return (sem_conn.ArgType.String, str(arg))
        
    def _CArrayByte(self, arg):
        return (sem_conn.ArgType.ArrayByte, arg)

#
# session management
#    

    def Connect(self, address, port):
        """ Connect to SEM
        
        Connection must be established before the first call of a SharkSEM function.
        
        == 0        ok
        < 0         error occured
        """
        return self.connection.Connect(address, port)
        
    def Disconnect(self):
        """ Disconnect SEM
        
        Opposite to Connect()
        """
        self.connection.Disconnect()
        
    def SetWaitFlags(self, flags):
        """ Set wait condition 
        
        SharkSEM request header contains set of flags, which specify 
        conditions to execute the request.
        
        bit 0       Wait A (SEM scanning)
        bit 1       Wait B (SEM stage)
        bit 2       Wait C (SEM optics)
        bit 3       Wait D (SEM automatic procedure)
        bit 4       Wait E (FIB scanning)
        bit 5       Wait F (FIB optics)
        bit 6       Wait G (FIB automatic procedure)
        """
        self.connection.wait_flags = flags
        
    def FetchImage(self, channel, size):
        """ Read single image
        
        channel     input video channel
        size        number of image pixels (bytes)        
        
        Scanning should be initiated first. Then, call this blocking function. During
        the call, messages from data connection are collected, decoded and image is
        stored as a 'bytes' type. The resulting image is passed as a return value.
        
        Image is converted to 8-bit, even if 16-bit channel is configured.
        """
        return self.connection.FetchImage('ScData', channel, size)

    def FetchImageEx(self, channel_list, pxl_size):
        """ Read multiple images
        
        This extends FetchImage() capabilities. More image channels can be processed,
        16-bit images are supported. 
        
        channel_list    zero-based list of input video channels
        pxl_size        number of image pixels (pixels)        
        
        Scanning should be initiated first. Then, call this blocking function. During
        the call, messages from data connection are collected, decoded and images are
        stored as a ('bytes', 'bytes', ...) type, each string contains one channel.
        The resulting images are returned as a list of byte strings containing pixles.
        
        Both 8-bit and 16-bit data are supported. In case of 16-bit image, each pixel
        occupies 2 bytes in the output buffer (instead of one byte). The byte order
        is little-endian.
        """
        return self.connection.FetchImageEx('ScData', channel_list, pxl_size)

    def FetchCameraImage(self, channel):
        """ Read single image from camera (wait till it comes)
        
        channel     input video channel
        
        Camera must be activated first. Then, call this blocking function, which
        returns the image as a return value. The value has three components -
        width, height, data.
        """
        return self.connection.FetchCameraImage(channel)
        
################################################################################
#
# Electron Optics
#    

    def AutoColumn(self, channel):
        self.connection.Send('AutoColumn', self._CInt(channel))

    def AutoGun(self, channel):
        self.connection.Send('AutoGun', self._CInt(channel))
        
    def AutoWD(self, *arg):
        if len(arg) == 1:
            self.connection.Send('AutoWD', self._CInt(arg[0]))
        if len(arg) == 3:
            self.connection.Send('AutoWD', self._CInt(arg[0]), self._CFloat(arg[1]), self._CFloat(arg[2]))

    def Degauss(self):
        self.connection.Send('Degauss')

    def EnumCenterings(self):
        return self.connection.RecvString('EnumCenterings')
        
    def EnumGeometries(self):
        return self.connection.RecvString('EnumGeometries')

    def EnumPCIndexes(self):
        return self.connection.RecvString('EnumPCIndexes')

    def Get3DBeam(self):
        return self.connection.Recv('Get3DBeam', (sem_conn.ArgType.Float, sem_conn.ArgType.Float))

    def GetCentering(self, index):
        return self.connection.Recv('GetCentering', (sem_conn.ArgType.Float, sem_conn.ArgType.Float), self._CInt(index))

    def GetGeometry(self, index):
        return self.connection.Recv('GetGeometry', (sem_conn.ArgType.Float, sem_conn.ArgType.Float), self._CInt(index))
    
    def GetIAbsorbed(self):
        return self.connection.RecvFloat('GetIAbsorbed')
        
    def GetImageShift(self):
        return self.connection.Recv('GetImageShift', (sem_conn.ArgType.Float, sem_conn.ArgType.Float))

    def GetPCFine(self):
        return self.connection.RecvFloat('GetPCFine')

    def GetPCContinual(self):
        return self.connection.RecvFloat('GetPCContinual')

    def GetPCIndex(self):
        return self.connection.RecvInt('GetPCIndex')

    def GetSpotSize(self):
        return self.connection.RecvFloat('GetSpotSize')

    def GetViewField(self):
        return self.connection.RecvFloat('GetViewField')
        
    def GetWD(self):
        return self.connection.RecvFloat('GetWD')
    
    def Set3DBeam(self, alpha, beta):
        self.connection.Send('Set3DBeam', self._CFloat(alpha), self._CFloat(beta))
        
    def SetCentering(self, index, x, y):
        self.connection.Send('SetCentering', self._CInt(index), self._CFloat(x), self._CFloat(y))

    def SetGeometry(self, index, x, y):
        self.connection.Send('SetGeometry', self._CInt(index), self._CFloat(x), self._CFloat(y))
        
    def SetImageShift(self, x, y):
        self.connection.Send('SetImageShift', self._CFloat(x), self._CFloat(y))
    
    def SetPCIndex(self, index):
        self.connection.Send('SetPCIndex', self._CInt(index))

    def SetPCContinual(self, pc_continual):
        self.connection.Send('SetPCContinual', self._CFloat(pc_continual))

    def SetViewField(self, vf):
        self.connection.Send('SetViewField', self._CFloat(vf))

    def SetWD(self, wd):
        self.connection.Send('SetWD', self._CFloat(wd))

################################################################################
#
# Manipulators - enumeration, configuration
#

    def ManipGetCount(self):
        return self.connection.RecvInt('ManipGetCount')

    def ManipGetCurr(self):
        return self.connection.RecvInt('ManipGetCurr')

    def ManipSetCurr(self, index):
        self.connection.Send('ManipSetCurr', self._CInt(index))
        
    def ManipGetConfig(self, index):
        return self.connection.RecvString('ManipGetConfig', self._CInt(index))

################################################################################
#
# Stage Control
#

    def StgCalibrate(self):
        self.connection.Send('StgCalibrate')

    def StgGetPosition(self):
        return self.connection.Recv('StgGetPosition', (sem_conn.ArgType.Float, sem_conn.ArgType.Float, sem_conn.ArgType.Float, sem_conn.ArgType.Float, sem_conn.ArgType.Float))

    def StgIsBusy(self):
        return self.connection.RecvInt('StgIsBusy')

    def StgIsCalibrated(self):
        return self.connection.RecvInt('StgIsCalibrated')

    def StgMoveTo(self, *arg):
        f_arg = []
        for p in arg:
            f_arg.append(self._CFloat(p))
        self.connection.Send('StgMoveTo', *f_arg)

    def StgMove(self, *arg):
        f_arg = []
        for speed in arg:
            f_arg.append(self._CFloat(speed))
        self.connection.Send('StgMove', *f_arg)

    def StgStop(self):
        self.connection.Send('StgStop')

################################################################################
#
# Input Channels And Detectors
#

    def DtAutoSignal(self, channel):
        self.connection.Send('DtAutoSignal', self._CInt(channel))
    
    def DtEnable(self, channel, enable, bpp = -1):
        if (bpp == -1):
            self.connection.Send('DtEnable', self._CInt(channel), self._CInt(enable))
        else:
            self.connection.Send('DtEnable', self._CInt(channel), self._CInt(enable), self._CInt(bpp))

    def DtEnumDetectors(self):
        return self.connection.RecvString('DtEnumDetectors')

    def DtGetChannels(self):
        return self.connection.RecvInt('DtGetChannels')

    def DtGetEnabled(self, channel):
        return self.connection.Recv('DtGetEnabled', (sem_conn.ArgType.Int, sem_conn.ArgType.Int), self._CInt(channel))

    def DtGetGainBlack(self, detector):
        return self.connection.Recv('DtGetGainBlack', (sem_conn.ArgType.Float, sem_conn.ArgType.Float), self._CInt(detector))

    def DtGetSelected(self, channel):
        return self.connection.RecvInt('DtGetSelected', self._CInt(channel))
        
    def DtSelect(self, channel, detector):
        self.connection.Send('DtSelect', self._CInt(channel), self._CInt(detector))

    def DtSetGainBlack(self, detector, gain, black):
        self.connection.Send('DtSetGainBlack', self._CInt(detector), self._CFloat(gain), self._CFloat(black))

################################################################################
#
# Scanning
#

    def ScEnumSpeeds(self):
        return self.connection.RecvString('ScEnumSpeeds')

    def ScGetBlanker(self, blanker):
        return self.connection.RecvInt('ScGetBlanker', self._CInt(blanker))

    def ScGetExternal(self):
        return self.connection.RecvInt('ScGetExternal')
    
    def ScGetSpeed(self):
        return self.connection.RecvInt('ScGetSpeed')

    def ScScanLine(self, frameid, width, height, x0, y0, x1, y1, dwell_time, pixel_count, single):
        return self.connection.RecvInt('ScScanLine', self._CInt(0), self._CInt(width), self._CInt(height), self._CInt(x0), self._CInt(y0), self._CInt(x1), self._CInt(y1), self._CInt(dwell_time), self._CInt(pixel_count), self._CInt(single))

    # frameid, width, height, left, top, right, bottom, single <, dwell>
    def ScScanXY(self, *arg):
        if len(arg) == 8:
            return self.connection.RecvInt('ScScanXY', self._CUnsigned(arg[0]), self._CUnsigned(arg[1]), self._CUnsigned(arg[2]), self._CUnsigned(arg[3]), self._CUnsigned(arg[4]), self._CUnsigned(arg[5]), self._CUnsigned(arg[6]), self._CInt(arg[7]))
        if len(arg) == 9:
            return self.connection.RecvInt('ScScanXY', self._CUnsigned(arg[0]), self._CUnsigned(arg[1]), self._CUnsigned(arg[2]), self._CUnsigned(arg[3]), self._CUnsigned(arg[4]), self._CUnsigned(arg[5]), self._CUnsigned(arg[6]), self._CInt(arg[7]), self._CUnsigned(arg[8]))
        
    def ScScanEDXXY(self, frameid, width, height, x1, y1, x2, y2, 
            channel, thr_low, thr_high, wait_dwell, wait_count, sync_mode, 
            dwell_dark, dwell_bright, send_data, single):
        return self.connection.Send('ScScanEDXXY',
                    self._CUnsigned(frameid), 
                    self._CUnsigned(width), 
                    self._CUnsigned(height), 
                    self._CUnsigned(x1), 
                    self._CUnsigned(y1), 
                    self._CUnsigned(x2),
                    self._CUnsigned(y2),
                    self._CUnsigned(channel),
                    self._CUnsigned(thr_low),
                    self._CUnsigned(thr_high),
                    self._CUnsigned(wait_dwell),
                    self._CUnsigned(wait_count),
                    self._CUnsigned(sync_mode),
                    self._CUnsigned(dwell_dark),
                    self._CUnsigned(dwell_bright),
                    self._CInt(send_data),
                    self._CInt(single))
                
    def ScScanEDXLine(self, frameid, width, height, x0, y0, x1, y1, pixel_count, 
            channel, thr_low, thr_high, wait_dwell, wait_count, sync_mode, 
            dwell_dark, dwell_bright, send_data, single):
        return self.connection.Send('ScScanEDXLine',
                    self._CUnsigned(frameid), 
                    self._CUnsigned(width), 
                    self._CUnsigned(height), 
                    self._CUnsigned(x0), 
                    self._CUnsigned(y0), 
                    self._CUnsigned(x1),
                    self._CUnsigned(y1),
                    self._CUnsigned(pixel_count),
                    self._CUnsigned(channel),
                    self._CUnsigned(thr_low),
                    self._CUnsigned(thr_high),
                    self._CUnsigned(wait_dwell),
                    self._CUnsigned(wait_count),
                    self._CUnsigned(sync_mode),
                    self._CUnsigned(dwell_dark),
                    self._CUnsigned(dwell_bright),
                    self._CInt(send_data),
                    self._CInt(single))

    def ScScanEDXMap(self, frameid, width, height, 
            channel, thr_low, thr_high, wait_dwell, wait_count, sync_mode, 
            dwell_dark, dwell_bright, point_list, send_data, single):
        return self.connection.Send('ScScanEDXMap',
                    self._CUnsigned(frameid), 
                    self._CUnsigned(width), 
                    self._CUnsigned(height), 
                    self._CUnsigned(channel),
                    self._CUnsigned(thr_low),
                    self._CUnsigned(thr_high),
                    self._CUnsigned(wait_dwell),
                    self._CUnsigned(wait_count),
                    self._CUnsigned(sync_mode),
                    self._CUnsigned(dwell_dark),
                    self._CUnsigned(dwell_bright),
                    self._CArrayUnsigned(point_list),
                    self._CInt(send_data),
                    self._CInt(single))

    def ScScanEDXPart(self, frameid, width, height, center_x, center_y, diameter, 
            n_pixels, channel, thr_low, thr_high, wait_dwell, wait_count, sync_mode, 
            dwell_dark, dwell_bright, send_data, single):
        return self.connection.Send('ScScanEDXPart',
                    self._CUnsigned(frameid), 
                    self._CUnsigned(width), 
                    self._CUnsigned(height), 
                    self._CUnsigned(center_x), 
                    self._CUnsigned(center_y), 
                    self._CUnsigned(diameter),
                    self._CUnsigned(n_pixels),
                    self._CUnsigned(channel),
                    self._CUnsigned(thr_low),
                    self._CUnsigned(thr_high),
                    self._CUnsigned(wait_dwell),
                    self._CUnsigned(wait_count),
                    self._CUnsigned(sync_mode),
                    self._CUnsigned(dwell_dark),
                    self._CUnsigned(dwell_bright),
                    self._CInt(send_data),
                    self._CInt(single))

    def ScSetBlanker(self, blanker, mode):
        self.connection.Send('ScSetBlanker', self._CInt(blanker), self._CInt(mode))

    def ScSetExternal(self, enable):
        self.connection.Send('ScSetExternal', self._CInt(enable))

    def ScSetSpeed(self, speed):
        self.connection.Send('ScSetSpeed', self._CInt(speed))

    def ScStopScan(self):
        self.connection.Send('ScStopScan')
        
    def ScSetBeamPos(self, x, y):
        self.connection.Send('ScSetBeamPos', self._CFloat(x), self._CFloat(y))

    def ScSetBeamPosGSR(self, x, y, ind_map, ind_sticky, img_channel):
        self.connection.Send('ScSetBeamPosGSR', self._CFloat(x), self._CFloat(y), self._CInt(ind_map), self._CInt(ind_sticky), self._CInt(img_channel))

    def ScReadImageADC(self, channel):
        return self.connection.RecvInt('ScReadImageADC', self._CInt(channel))
        
    def ScLUTParSet(self, channel, lut_min, lut_max, lut_gamma):
        self.connection.Send('ScLUTParSet', self._CInt(channel), self._CFloat(lut_min), self._CFloat(lut_max), self._CFloat(lut_gamma))

    def ScLUTParGet(self, channel):
        return self.connection.Recv('ScLUTParGet', (sem_conn.ArgType.Float, sem_conn.ArgType.Float, sem_conn.ArgType.Float), self._CInt(channel))

    def ScLUTSrcSet(self, lut_src):
        self.connection.Send('ScLUTSrcSet', self._CInt(lut_src))

    def ScLUTSrcGet(self):
        return self.connection.RecvInt('ScLUTSrcGet')

################################################################################
#
# Scanning Mode
#

    def SMEnumModes(self):
        return self.connection.RecvString('SMEnumModes')
    
    def SMGetMode(self):
        return self.connection.RecvInt('SMGetMode')
        
    def SMSetMode(self, mode):
        self.connection.Send('SMSetMode', self._CInt(mode))

################################################################################
#
# Vacuum
#

    def VacGetPressure(self, gauge):
        return self.connection.RecvFloat('VacGetPressure', self._CInt(gauge))

    def VacGetStatus(self):
        return self.connection.RecvInt('VacGetStatus')

    def VacGetVPMode(self):
        return self.connection.RecvInt('VacGetVPMode')

    def VacGetVPPress(self):
        return self.connection.RecvFloat('VacGetVPPress')

    def VacPump(self):
        self.connection.Send('VacPump')

    def VacSetVPMode(self, vpmode):
        self.connection.Send('VacSetVPMode', self._CInt(vpmode))

    def VacSetVPPress(self, pressure):
        self.connection.Send('VacSetVPPress', self._CFloat(pressure))

    def VacVent(self):
        self.connection.Send('VacVent')
        
################################################################################
#
# Airlock - general purpose
#

    def ArlGetType(self):
        return self.connection.RecvInt('ArlGetType')

################################################################################
#
# Airlock 1 - manual
#

    def ArlGetStatus(self):
        return self.connection.RecvInt('ArlGetStatus')
    
    def ArlPump(self):
        self.connection.Send('ArlPump')
    
    def ArlVent(self):
        self.connection.Send('ArlVent')

    def ArlOpenValve(self):
        self.connection.Send('ArlOpenValve')

    def ArlCloseValve(self):
        self.connection.Send('ArlCloseValve')
        
################################################################################
#
# Airlock 2 - motorized
#

    def Arl2GetStatus(self):
        return self.connection.Recv('Arl2GetStatus', (sem_conn.ArgType.Int, sem_conn.ArgType.Int))
    
    def Arl2MoveStop(self):
        self.connection.Send('Arl2MoveStop')
    
    def Arl2Recovery(self):
        self.connection.Send('Arl2Recovery')

    def Arl2Calibrate(self):
        self.connection.Send('Arl2Calibrate')

    def Arl2Load(self):
        self.connection.Send('Arl2Load')

    def Arl2Unload(self):
        self.connection.Send('Arl2Unload')

    def Arl2Pump(self):
        self.connection.Send('Arl2Pump')

    def Arl2Vent(self):
        self.connection.Send('Arl2Vent')

################################################################################
#
# High Voltage
#
    def HVAutoHeat(self, channel):
        self.connection.Send('HVAutoHeat', self._CInt(channel))

    def HVBeamOff(self):
        self.connection.Send('HVBeamOff')
    
    def HVBeamOn(self):
        self.connection.Send('HVBeamOn')

    def HVEnumIndexes(self):
        return self.connection.RecvString('HVEnumIndexes')

    def HVGetBeam(self):
        return self.connection.RecvInt('HVGetBeam')

    def HVGetEmission(self):
        return self.connection.RecvFloat('HVGetEmission')

    def HVGetFilTime(self):
        return self.connection.RecvInt('HVGetFilTime')

    def HVGetHeating(self):
        return self.connection.RecvFloat('HVGetHeating')

    def HVGetIndex(self):
        return self.connection.RecvInt('HVGetIndex')

    def HVGetVoltage(self):
        return self.connection.RecvFloat('HVGetVoltage')

    # change variable name from async to p_async
    def HVSetIndex(self, index, p_async = -1):
        if p_async == -1:
            self.connection.Send('HVSetIndex', self._CInt(index))
        else:
            self.connection.Send('HVSetIndex', self._CInt(index), self._CInt(p_async))

    def HVSetVoltage(self, voltage, p_async = -1):
        if p_async == -1:
            self.connection.Send('HVSetVoltage', self._CFloat(voltage))
        else:
            self.connection.Send('HVSetVoltage', self._CFloat(voltage), self._CInt(p_async))


################################################################################
#
# SEM GUI Control
#

    def GUIGetScanning(self):
        return self.connection.RecvInt('GUIGetScanning')
    
    def GUISetScanning(self, enable):
        self.connection.Send('GUISetScanning', self._CInt(enable))

    def HVStopAsyncProc(self):
        self.connection.Send('HVStopAsyncProc')

################################################################################
#
# Camera
#
    def CameraEnable(self, channel, zoom, fps, compression):
        return self.connection.Send('CameraEnable', self._CInt(channel), self._CFloat(zoom), self._CFloat(fps), self._CInt(compression))

    def CameraDisable(self):
        return self.connection.Send('CameraDisable')

    def CameraGetStatus(self, channel):
        return self.connection.Recv('CameraGetStatus', (sem_conn.ArgType.Int, sem_conn.ArgType.Float, sem_conn.ArgType.Float, sem_conn.ArgType.Int), self._CInt(channel))


################################################################################
#
# RCA - Rotating Chord Algorithm
#

    def RCAGetDACRange(self):
        return self.connection.RecvInt('RCAGetDACRange')

    def RCAInit(self, detector, max_particle_size, ppm_resolution, x1, y1, x2, y2, 
                    search_dwell, search_thr_low, search_thr_high, meas_dwell, meas_thr_low,
                    meas_thr_high, meas_step):
        return self.connection.Send('RCAInit',
					self._CInt(detector),
					self._CUnsigned(max_particle_size),
					self._CUnsigned(ppm_resolution),
					self._CUnsigned(x1),
					self._CUnsigned(y1),
					self._CUnsigned(x2),
					self._CUnsigned(y2),
					self._CUnsigned(search_dwell),
					self._CUnsigned(search_thr_low),
					self._CUnsigned(search_thr_high),
					self._CUnsigned(meas_dwell),
					self._CUnsigned(meas_thr_low),
					self._CUnsigned(meas_thr_high),
					self._CUnsigned(meas_step))

    def RCASetCbMask(self, cb_mask):
        return self.connection.Send('RCASetCbMask', self._CUnsigned(cb_mask))

    def RCASetOption(self, option, value):
        return self.connection.Send('RCASetOption', self._CString(option), self._CUnsigned(value))

    def RCANextParticle(self, single_rca, edx_mode, edx_param):
        return self.connection.Send('RCANextParticle', self._CInt(single_rca), self._CInt(edx_mode), self._CInt(edx_param))

    def RCASkipParticle(self, particle_ind):
        return self.connection.Send('RCASkipParticle', self._CUnsigned(particle_ind))

    def RCAFinish(self):
        return self.connection.Send('RCAFinish')


################################################################################
#
# Nose space guard
#

    def NGuardTest(self, module):
        return self.connection.RecvInt('NGuardTest', self._CString(module))
        
    def NGuardLock(self, module):
        return self.connection.RecvInt('NGuardLock', self._CString(module))
        
    def NGuardUnlock(self, module):
        self.connection.Send('NGuardUnlock', self._CString(module))
        
    def NGuardGetStatus(self):
        return self.connection.RecvString('NGuardGetStatus')
        

################################################################################
#
# Detector nose manipulation
#
    def NoseCalibrate(self, nose):
        return self.connection.RecvInt('NoseCalibrate', self._CInt(nose))

    def NoseGetPosition(self, nose):
        return self.connection.Recv('NoseGetPosition', (sem_conn.ArgType.Float, sem_conn.ArgType.Float, sem_conn.ArgType.Float), self._CInt(nose))
        
    def NoseMoveToPos(self, *arg):
        f_arg = []
        i = 0
        for p in arg:
            if i == 0:
                f_arg.append(self._CInt(p))             # nose
            else:
                f_arg.append(self._CFloat(p))           # position, at least one float value
            i = i + 1
        return self.connection.RecvInt('NoseMoveToPos', *f_arg)
        
    def NoseMoveToMem(self, nose, mem):
        return self.connection.RecvInt('NoseMoveToMem', self._CInt(nose), self._CInt(mem))
        
    def NoseStop(self, nose):
        self.connection.Send('NoseStop', self._CInt(nose))
        
    def NoseIsBusy(self, nose):
        return self.connection.RecvInt('NoseIsBusy', self._CInt(nose))
    
    def NoseIsCalib(self, nose):
        return self.connection.RecvInt('NoseIsCalib', self._CInt(nose))

    def NoseGetConfig(self, nose):
        return self.connection.RecvString('NoseGetConfig', self._CInt(nose))


################################################################################
#
# DrawBeam
#
    def DrwGetConfig(self):
        return self.connection.RecvInt('DrwGetConfig')
        
    def DrwGetStatus(self):
        return self.connection.Recv('DrwGetStatus', (sem_conn.ArgType.Int, sem_conn.ArgType.Float, sem_conn.ArgType.Float))
        
    def DrwStart(self, layer):
        return self.connection.RecvInt('DrwStart', self._CInt(layer))

    def DrwStop(self):
        return self.connection.RecvInt('DrwStop')

    def DrwPause(self):
        return self.connection.RecvInt('DrwPause')

    def DrwResume(self):
        return self.connection.RecvInt('DrwResume')

    def DrwLoadLayer(self, layer, xml):
        return self.connection.RecvInt('DrwLoadLayer', self._CInt(layer), self._CString(xml))

    def DrwUnloadLayer(self, layer):
        return self.connection.RecvInt('DrwUnloadLayer', self._CInt(layer))

    def DrwEstimateTime(self, layer):
        return self.connection.Recv('DrwEstimateTime', (sem_conn.ArgType.Int, sem_conn.ArgType.Float), self._CInt(layer))


################################################################################
#
# Remote process progress indicator
#

    def ProgressShow(self, title, text, hide_button, marquee, progress_min, progress_max):
        self.connection.Send('ProgressShow', self._CString(title), self._CString(text), self._CInt(hide_button), self._CInt(marquee), self._CInt(progress_min), self._CInt(progress_max))

    def ProgressHide(self):
        self.connection.Send('ProgressHide')

    def ProgressText(self, text):
        self.connection.Send('ProgressText', self._CString(text))

    def ProgressPerc(self, progress_position):
        self.connection.Send('ProgressPerc', self._CInt(progress_position))


################################################################################
#
# SEM power saving mode
#

    def PowerStateSet(self, mode):
        self.connection.Send('PowerStateSet', self._CUnsigned(mode))

    def PowerStateGet(self):
        return self.connection.RecvInt('PowerStateGet')

    def PowerStateEnum(self):
        return self.connection.RecvUInt('PowerStateEnum')


################################################################################
#
# SEM stage layout
#

    def SmplEnum(self, coord_system):
        return self.connection.RecvString('SmplEnum', self._CInt(coord_system))
        
    def SmplGetCount(self):
        return self.connection.RecvInt('SmplGetCount')

    def SmplGetHldrName(self):
        return self.connection.RecvString('SmplGetHldrName')

    def SmplGetId(self, index):
        return self.connection.RecvString('SmplGetId', self._CInt(index))

    def SmplGetType(self, index):
        return self.connection.RecvInt('SmplGetType', self._CInt(index))

    def SmplGetPosition(self, index, coord_system):
        return self.connection.Recv('SmplGetPosition', (sem_conn.ArgType.Float, sem_conn.ArgType.Float, sem_conn.ArgType.Float), self._CInt(index), self._CInt(coord_system))

    def SmplGetShape(self, index):
        return self.connection.Recv('SmplGetShape', (sem_conn.ArgType.Int, sem_conn.ArgType.Float, sem_conn.ArgType.Float, sem_conn.ArgType.Float), self._CInt(index))

    def SmplGetLabel(self, index):
        return self.connection.RecvString('SmplGetLabel', self._CInt(index))
        
    def SmplSetLabel(self, index, label):
        return self.connection.Send('SmplSetLabel', self._CInt(index), self._CString(label))
        
        
################################################################################
#
# Autoloader
#

    def ALIsInstalled(self):
        return self.connection.RecvInt('ALIsInstalled')

    def ALGetConfig(self):
        return self.connection.Recv('ALGetConfig', (sem_conn.ArgType.Int, sem_conn.ArgType.String))

    def ALGetStatus(self):
        return self.connection.Recv('ALGetStatus', (sem_conn.ArgType.Int, sem_conn.ArgType.Int, sem_conn.ArgType.ArrayInt, sem_conn.ArgType.ArrayInt))

    def ALSelectSamples(self, start, count):
        return self.connection.RecvInt('ALSelectSamples', self._CInt(start), self._CInt(count))

    def ALSwapSamples(self, pos_load, pos_unload):
        return self.connection.RecvInt('ALSwapSamples', self._CInt(pos_load), self._CInt(pos_unload))

    def ALPickNext(self):
        return self.connection.RecvInt('ALPickNext')

    def ALDropSample(self):
        return self.connection.RecvInt('ALDropSample')

    def ALManualEnable(self, enable):
        return self.connection.RecvInt('ALManualEnable', self._CInt(enable))
        
    def ALIsManEnabled(self):
        return self.connection.RecvInt('ALIsManEnabled')
        
    def ALCamStart(self, channel, recognize):
        return self.connection.RecvInt('ALCamStart', self._CInt(channel), self._CInt(recognize))

    def ALCamFetch(self):
        return self.connection.Recv('ALCamFetch', (sem_conn.ArgType.Int, sem_conn.ArgType.ArrayByte, sem_conn.ArgType.String, sem_conn.ArgType.Float))

################################################################################
#
# Miscellaneous
#

    def TcpGetVersion(self):
        return self.connection.RecvString('TcpGetVersion')

    def TcpGetSWVersion(self):
        return self.connection.RecvString('TcpGetSWVersion')

    def ChamberLed(self, onoff):
        self.connection.Send('ChamberLed', self._CInt(onoff))

    def Delay(self, delay):
        self.connection.Send('Delay', self._CInt(delay))

    def TcpGetDevice(self):
        return self.connection.RecvString('TcpGetDevice')

    def IsLicenseValid(self, module):
        return self.connection.RecvInt('IsLicenseValid', self._CString(module))

    def GetUPSStatus(self):
        return self.connection.RecvInt('GetUPSStatus')
        
    def GetDeviceParams(self, param_set):
        return self.connection.RecvString('GetDeviceParams', self._CUnsigned(param_set))
 
    def IsBusy(self, flags):
        return self.connection.RecvInt('IsBusy', self._CUnsigned(flags))

################################################################################
#
# Experimental / debugging
#

    def DbgFibConGet(self):
        return self.connection.RecvFloat('DbgFibConGet')

    def DbgFibObjGet(self):
        return self.connection.RecvFloat('DbgFibObjGet')

    def DbgFibConSet(self, v):
        self.connection.Send('DbgFibConSet', self._CFloat(v))

    def DbgFibObjSet(self, v):
        self.connection.Send('DbgFibObjSet', self._CFloat(v))

    def DbgFibTrcInfo(self):
        return self.connection.RecvString('DbgFibTrcInfo')

    def DbgSetLensCurr(self, lens, curr):
        self.connection.Send('DbgSetLensCurr', self._CInt(lens), self._CFloat(curr))

    def DbgGetLensCurr(self, lens):
        return self.connection.RecvFloat('DbgGetLensCurr', self._CInt(lens))

    def DbgDegaussEx(self, lenses, centering):
        self.connection.Send('DbgDegaussEx', self._CInt(lenses), self._CInt(centering))

    def DbgGetOptPar(self):
        return self.connection.RecvString('DbgGetOptPar')
