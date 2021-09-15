from tkinter import *
from tkinter import messagebox, filedialog
from PIL import Image
import os
import time
import math
from sem import Sem
from pynput.mouse import Button as MouseButton
from pynput.mouse import Controller as MouseController
from pynput.keyboard import Key 
from pynput.keyboard import Controller as KeyboardController
import win32gui
import subprocess
import time


class SemControl(Sem):
    
    # const wait flags, A: e-beam scanning, B: stage, C: e-beam optics, D: e-beam automatic procedure
    wtflgA = 0b1
    wtflgB = 0b10
    wtflgC = 0b100
    wtflgD = 0b1000
    wtflgAll = 0b1111
    
    # use channel=0, for SE detector (# will be found, usually 0), use 16-bit image for SEM-DIC with Vic2D
    channel = 0
    detector = 0
    nbits_image = 16
    image_mode = "I;16"
    dtype = 'uint16'
    
    # These can be read from the SEM setting for live imaging
    scan_speed = 2
    beam_intensity = 10
    voltage = 15000.0
    
    # use single frame for image capture
    single_frame_TF = 1
    
    # Key settings for imaging, can input using SEM control GUI App
    view_field = 0.40
    dwell_ns = 100    
    image_resolution = 4096
    sample_name = ''
    folder_name = ''
    external_exe_name = 'D:\\p\\c++\\External_Scan_Insitu_Test\\build\\ExternalScan.exe'

    # these should be defined in the app
    image_adjust_option = ''
    image_capture_option = ''
        
    # Define scan area and grids
    nR = 2
    nC = 2
    iR = 0
    iC = 0
    pos_upper_left = [0, 0]
    pos_upper_right = [0.2, 0]
    pos_lower_left = [0, 0.2]
    pos_lower_right = [0.2, 0.2]
    WD_upper_left = 90
    WD_upper_right = 90
    WD_lower_left = 90
    WD_lower_right = 90
    
    def __init__(self, channel):
        Sem.__init__(self)
        
        self.channel = channel
        
        # define the IP address of the SEM
        sem_ip = "localhost"
        sem_port = 8300
        
        # connecting to the microscope via SharkSEM protocol
        res = self.Connect(sem_ip, sem_port)
        # handling the output
        if res < 0:
            raise RuntimeError("Unable to connect SEM/FIB at {}:{}".format(sem_ip, sem_port))
        else:
            print("SEM connected at {}:{}".format(sem_ip, sem_port))
        
        # check the detector configuration. Note the last item is " "
        dt_list = self.DtEnumDetectors().split('\n')
        # select detector with name = 'SE'
        ind = 0
        while ind < len(dt_list)-1:
            if dt_list[ind].split('=')[1] == 'SE':
                dtn = int(dt_list[ind+1].split('=')[1])
                self.detector = dtn
                print("SE detector number = {}".format(self.detector))
                break
            ind += 1
        else:
            raise RuntimeError("Could not find SE detector")
        
        # check vacuum
        vac = self.VacGetStatus()
        if vac != 0:
            raise RuntimeError("Vaccum Not Ready")
        else:
            print("Vacuum ready")   
    
        self.DtSelect(self.channel, self.detector) # channel (0), assign deterctor (0=SE) 
        self.DtEnable(self.channel, 1, self.nbits_image) # channel(0), enbale(1) for acquisition with nbits_image data stream

        
    # determine stage position for index (iR,iC)
    def get_position_iRiC(self,iR,iC):
        nR = self.nR
        nC = self.nC
        px = 1/(nR-1)/(nC-1) * ((nR-1-iR) * (nC-1-iC) * self.pos_upper_left[0] 
                        + (nR-1-iR) * iC * self.pos_upper_right[0] 
                        + iR * (nC-1-iC) * self.pos_lower_left[0]
                        + iR * iC * self.pos_lower_right[0])
        py = 1/(nR-1)/(nC-1) * ((nR-1-iR) * (nC-1-iC) * self.pos_upper_left[1] 
                        + (nR-1-iR) * iC * self.pos_upper_right[1] 
                        + iR * (nC-1-iC) * self.pos_lower_left[1]
                        + iR * iC * self.pos_lower_right[1])
        print("iR={},iC={},px={},py={}".format(iR,iC,px,py))
        
        WD_target = 1/(nR-1)/(nC-1) * ((nR-1-iR) * (nC-1-iC) * self.WD_upper_left 
                + (nR-1-iR) * iC * self.WD_upper_right
                + iR * (nC-1-iC) * self.WD_lower_left
                + iR * iC * self.WD_lower_right)
        return (px,py,WD_target)  
    
    # move to imaging position for iR,iC
    def move_to_iRiC(self):
        px,py,WD_target = self.get_position_iRiC(self.iR, self.iC)
        self.SetWaitFlags(self.wtflgB)
        self.StgMoveTo(px,py)    
        self.WD_target = WD_target
    
    # update iR,iC for next imaging position
    def update_next_iRiC(self):
        # (1) If iR is even, (1.1) if iC < iC_max, then iC += 1; (1.2) else, iR += 1
        # (2) Else iR is odd, (2.1) if iC > iC_min, then iC -= 1; (2.2) else, iR += 1
        if math.fmod(self.iR,2) == 0:
            if self.iC < (self.nC-1):
                self.iC += 1
            else:
                self.iR += 1    
        else:
            if self.iC > 0:
                self.iC -= 1
            else:
                self.iR += 1
        
        # if not out of bound, move. Else, end.
        if self.iR <= (self.nR-1):
            return True
        else:
            self.iR = 0
            self.iC = 0
            print("Reached end of imaging position, change (iR,iC) to (0,0)")
            return False
    
    
    # show window
    def make_window_front(self, wnd_name):
        hwnd = win32gui.FindWindow(0,wnd_name)
        # 3 = maximize, 5 = show where it was, 9 = restore
        win32gui.ShowWindow(hwnd, 5)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(1)    
    
    # set for live imaging using preferred setting
    def live_imaging(self):
        self.SetWaitFlags(self.wtflgC)
        self.HVSetVoltage(self.voltage)
        self.SetPCContinual(21-self.beam_intensity)
        self.ScSetSpeed(self.scan_speed)
        self.HVBeamOn()
        self.GUISetScanning(1)
    
    # Modify some super class functions. add wait and wait flags
    def GUISetScanning(self, enableTF):
        super().GUISetScanning(enableTF)
        time.sleep(0.5)
    
    def ScStopScan(self):
        self.SetWaitFlags(self.wtflgC)
        super().ScStopScan()
    
    def DtAutoSignal(self, channel):
        print("Auto Signal(B&C) ...")
        self.ScStopScan()
        self.SetWaitFlags(self.wtflgD) # need wtflgD 
        super().DtAutoSignal(channel)
        self.GetWD() # need this to block progress until finish
        self.GUISetScanning(1)
    
    def AutoWD(self, *arg):
        print("Auto Focus(WD) at WD: " + str(self.GetWD()))
        self.ScStopScan()
        self.SetWaitFlags(self.wtflgD)
        super().AutoWD(*arg)
        self.GetWD() # need this to block progress until finish
        print("WD changed to: " + str(self.GetWD()))
        self.GUISetScanning(1)
        
    def SetWD(self, *arg):
        print("Set Focus(WD) to (mm): " + str(self.WD_target))
        self.SetWaitFlags(self.wtflgC)
        super().SetWD(*arg)
        self.GetWD() # need this to block progress until finish
        print("Double check, Focus(WD) changed to: " + str(self.GetWD()))
        self.GUISetScanning(1)
        
    def SetViewField(self, vf):
        print("Setting view field to " + str(vf) + " mm")
        self.SetWaitFlags(self.wtflgC)
        super().SetViewField(vf)
        self.GUISetScanning(1)
        
    def AutoStig(self, wait_time, window_name_str):       
        # (0) left click at a target_pos
        target_pos = [256, 256]
        mouse = MouseController()
        mouse.move(target_pos[0]-mouse.position[0], target_pos[1]-mouse.position[1])
        mouse.click(MouseButton.left)
        
        # (1) make MiraTC window front
        self.make_window_front(window_name_str)
        time.sleep(0.5)
        print("Auto Stig ...")
        self.GetWD() # make sure to block
        
        # (2) right click at a target_pos
        target_pos = [256, 256]
        mouse.move(target_pos[0]-mouse.position[0], target_pos[1]-mouse.position[1])
        mouse.click(MouseButton.right)
        time.sleep(0.5)        
        # (3) move to position "Auto Stigmation"
        mouse.move(40,80)
        time.sleep(0.5)        
        # (4) right click
        mouse.click(MouseButton.left)
        time.sleep(0.5)
        
        # (6) wait for auto stigmation to finish
        print("Wait {} seconds for auto stig to finish".format(wait_time))
        self.GUISetScanning(1)
        time.sleep(wait_time)
        
    
    # adjust brightness, contrast, focus, stigmation
    def adjust_imaging(self):
        # set to target view field, stop scan before auto adjustment
        self.SetViewField(self.view_field)
        
        # (1) Auto B&C
        self.DtAutoSignal(self.channel)
        
        if self.image_adjust_option.get() == 'manual':
            messagebox.showinfo('Message','Adjust focus, stigmation, then continue', icon='warning')
        elif self.image_adjust_option.get() == 'interp':
            self.SetWD(self.WD_target)
        elif self.image_adjust_option.get() == 'auto':
            # (2) Auto focus after zoom in
            self.SetViewField(self.view_field/10)
            wd = self.GetWD()
            self.AutoWD(self.channel, wd-1, wd+1)

            # (3) Auto stigmation. 
            # Note (a) if we set vf between AutoWD and AutoStig, then stig finish early bad
            # (b) if we GUISetScanning(1), sometime we cannot find window
            self.AutoStig(15, "MiraTC")
        
        # (4) Change back to desired view_field to image
        self.SetViewField(self.view_field)
        
    # capture a single image
    def capture_image(self):  
        if self.image_capture_option.get() == 'auto':
            width = self.image_resolution
            height = self.image_resolution
            left = 0
            top = 0
            right = self.image_resolution - 1
            bottom = self.image_resolution- 1
            frameid = 0

            self.ScStopScan()
            self.SetWaitFlags(self.wtflgB)
            self.ScScanXY(frameid, width, height, left, top, right, bottom, self.single_frame_TF, self.dwell_ns)

            img_str = self.FetchImageEx([self.channel], int(width * height))[0]
            self.ScStopScan()

            img = Image.frombuffer(mode=self.image_mode, size=(width,height), data=img_str, decoder_name='raw')
            fp = self.folder_name + '\\'+ self.sample_name + '_r' + str(self.iR) + 'c' + str(self.iC) + '.tiff'
            # if exist, save image pair as '...A.tiff'
            if os.path.exists(fp):
                fp = fp.split('.tiff')[0] + '_A.tiff'
            img.save(fp)

        elif self.image_capture_option.get() == 'external':
            width = self.image_resolution
            height = self.image_resolution
            dwell_us = self.dwell_ns/1000  # the external scan needs dwell input as micro-seconds

            self.ScSetExternal(1)

            print('Imaging ...')
            # Call externalscan.exe, compiled from cpp, to run external scan controller for imaging
            args = self.external_exe_name + " -w " + str(width) + " -h " + str(height) + " -s " + str(dwell_us) + " -o " + self.folder_name + '\\'+ self.sample_name + '_r' + str(self.iR) + 'c' + str(self.iC) + '.tiff'
            
            success = 0
            while(not success):
                try:                     
                    subprocess.run(args, check=True)
                    success = 1
                    print('\n finished imaging')
                except subprocess.CalledProcessError:
                    success = 0
                    time.sleep(1)
                    print('\n error, will retry ')
            
            self.ScSetExternal(0)

        elif self.image_capture_option.get() == 'built-in':
            self.make_window_front('MiraTC')
            
            keyboard = KeyboardController()
            # press 'shift + a'
            time.sleep(2)
            with keyboard.pressed(Key.shift):
                keyboard.press('a')
                keyboard.release('a')
            
            # detect window, then click 'enter' to save
            time.sleep(2)
            while not win32gui.FindWindow(0,'Header of Save Window'):
                time.sleep(1)
            
            self.make_window_front('Header of Save Window')
            time.sleep(1)
            keyboard.press(Key.enter)
            keyboard.release(Key.enter)
            time.sleep(1)

            
        elif self.image_capture_option.get() == 'manual':
            messagebox.showinfo('Message','Capture and save image manually, then continue', icon='warning')
        
    def build_app(self):
        self.app = Tk()
        self.app.title("SEM Control")
        
        # some inputs
        nR_label = Label(self.app, text = "nR (total # rows) = ")
        nR_label.grid(row = 0, column = 0, padx = 5, pady = 5, sticky = 'E')
        self.nR_input = Entry(self.app, width = 10, borderwidth = 5)
        self.nR_input.grid(row = 0, column = 1, padx = 5, pady = 5, sticky = 'W')
        self.nR_input.insert(0, '2')
        
        nC_label = Label(self.app, text = 'nC (total # cols) = ')
        nC_label.grid(row = 1, column = 0, padx = 5, pady = 5, sticky = 'E')
        self.nC_input = Entry(self.app, width = 10, borderwidth = 5)
        self.nC_input.grid(row = 1, column = 1, padx = 5, pady = 5, sticky = 'W')
        self.nC_input.insert(0, '2')
        
        view_field_label = Label(self.app, text = 'View field (mm) = ')
        view_field_label.grid(row = 2, column = 0, padx = 5, pady = 5, sticky = 'E')
        self.view_field_input = Entry(self.app, width = 10, borderwidth = 5)
        self.view_field_input.grid(row = 2, column = 1, padx = 5, pady = 5, sticky = 'W')
        self.view_field_input.insert(0, '0.06')
        
        dwell_label = Label(self.app, text = "Dwell time (ns) = ")
        dwell_label.grid(row = 3, column = 0, padx = 5, pady = 5, sticky = 'E')
        self.dwell_input = Entry(self.app, width = 10, borderwidth = 5)
        self.dwell_input.grid(row = 3, column = 1, padx = 5, pady = 5, sticky = 'W')
        self.dwell_input.insert(0, '1000')
        
        resolution_label = Label(self.app, text = "Image resolution (pxl) = ")
        resolution_label.grid(row = 4, column = 0, padx = 5, pady = 5, sticky = 'E')
        self.resolution_input = Entry(self.app, width = 10, borderwidth = 5)
        self.resolution_input.grid(row = 4, column = 1, padx = 5, pady = 5, sticky = 'W')
        self.resolution_input.insert(0, '4096')
        
        iR_label = Label(self.app, text = "iR (current row #) = ")
        iR_label.grid(row = 5, column = 0, padx = 5, pady = 5, sticky = 'E')
        self.iR_input = Entry(self.app, width = 10, borderwidth = 5)
        self.iR_input.grid(row = 5, column = 1, padx = 5, pady = 5, sticky = 'W')
        self.iR_input.insert(0, '0')
        
        iC_label = Label(self.app, text = "iC (current col #) = ")
        iC_label.grid(row = 6, column = 0, padx = 5, pady = 5, sticky = 'E')
        self.iC_input = Entry(self.app, width = 10, borderwidth = 5)
        self.iC_input.grid(row = 6, column = 1, padx = 5, pady = 5, sticky = 'W')
        self.iC_input.insert(0, '0')
        
        # Image adjust option
        Label(self.app, text = "Image adjust option").grid(row = 7, column = 0, padx = 5, pady = 5, sticky = 'E')
        self.image_adjust_option = StringVar(self.app)
        self.image_adjust_option.set('interp')
        self.image_adjust_option_menu = OptionMenu(self.app, self.image_adjust_option, 'auto', 'interp', 'manual')
        self.image_adjust_option_menu.grid(row = 7, column = 1, columnspan = 2, ipadx = 15, pady = 5, sticky = 'W')
        
        # Image capture option
        Label(self.app, text = "Image capture option").grid(row = 7, column = 5, padx = 5, pady = 5, sticky = 'E')
        self.image_capture_option = StringVar(self.app)
        self.image_capture_option.set('auto')
        self.image_capture_option_menu = OptionMenu(self.app, self.image_capture_option, 'auto', 'built-in', 'manual', 'external')
        self.image_capture_option_menu.grid(row = 7, column = 6, columnspan = 2, ipadx = 15, pady = 5, sticky = 'W')
        
        name_label = Label(self.app, text = "Image name prefix = ")
        name_label.grid(row = 11, column = 0, padx = 5, pady = 5, sticky = 'E')
        self.sample_name_input = Entry(self.app, width = 75, borderwidth = 5)
        self.sample_name_input.grid(row = 11, column = 1, columnspan = 9, padx = 5, pady = 5, sticky = 'W')
        self.sample_name_input.insert(0, 'Mg_Sample_1')
        
        folder_name_button = Button(self.app, text = "Select folder to save", command = self.click_for_folder_name)
        folder_name_button.grid(row = 12, column = 0, ipadx = 10, pady = 5, sticky = 'E')
        self.folder_name_input = Entry(self.app, width = 75, bd = 5)
        self.folder_name_input.grid(row = 12, column = 1, columnspan = 9, padx = 5, pady = 5, sticky = 'W')
        self.folder_name_input.insert(0, os.getcwd())
        
        external_exe_name_button = Button(self.app, text = "Select ExternalScan exe", command = self.click_for_external_exe_name)
        external_exe_name_button.grid(row = 13, column = 0, ipadx = 3, pady = 5, sticky = 'E')
        self.external_exe_name_input = Entry(self.app, width = 75, borderwidth = 5)
        self.external_exe_name_input.grid(row = 13, column = 1, columnspan = 9, padx = 5, pady = 5, sticky = 'W')
        self.external_exe_name_input.insert(0, self.external_exe_name)

        # 4 corner positions 
        # frame-1: upper left
        frame_1 = Frame(self.app, bd = 5, relief = "groove")
        frame_1.grid(row = 14, column = 0, columnspan = 5, padx = 5, pady = 5)
        
        Label(frame_1, text = "Upper left").grid(row = 0, column = 0, padx = 5, pady = 5)
        Label(frame_1, text = "X = ").grid(row = 0, column = 1)
        self.x_upper_left_input = Entry(frame_1, width = 10, borderwidth = 5)
        self.x_upper_left_input.grid(row = 0, column = 2, padx = 5, pady = 5)
        Label(frame_1, text = "Y = ").grid(row = 0, column = 3)
        self.y_upper_left_input = Entry(frame_1, width = 10, borderwidth = 5)
        self.y_upper_left_input.grid(row = 0, column = 4)
        
        self.upper_left_read_button = Button(frame_1, text = "Set as current", command = lambda: self.read_position('ul'))
        self.upper_left_read_button.grid(row = 1, column = 0, columnspan = 2, padx = 5, pady = 5)
        
        self.upper_left_goto_button = Button(frame_1, text = "Go to", command = lambda: self.go_to_position('ul'))
        self.upper_left_goto_button.grid(row = 1, column = 2, columnspan = 3, ipadx = 40, pady = 5)
        
        # frame-2: upper right
        frame_2 = Frame(self.app, bd = 5, relief = "groove")
        frame_2.grid(row = 14, column = 5, columnspan = 5, padx = 5, pady = 5)
        
        Label(frame_2, text = "Upper right").grid(row = 0, column = 0, padx = 5, pady = 5)
        Label(frame_2, text = "X = ").grid(row = 0, column = 1)
        self.x_upper_right_input = Entry(frame_2, width = 10, borderwidth = 5)
        self.x_upper_right_input.grid(row = 0, column = 2, padx = 5, pady = 5)
        Label(frame_2, text = "Y = ").grid(row = 0, column = 3)
        self.y_upper_right_input = Entry(frame_2, width = 10, borderwidth = 5)
        self.y_upper_right_input.grid(row = 0, column = 4)
        
        self.upper_right_read_button = Button(frame_2, text = "Set as current", command = lambda: self.read_position('ur'))
        self.upper_right_read_button.grid(row = 1, column = 0, columnspan = 2, padx = 5, pady = 5)
        
        self.upper_right_goto_button = Button(frame_2, text = "Go to", command = lambda: self.go_to_position('ur'))
        self.upper_right_goto_button.grid(row = 1, column = 2, columnspan = 3, ipadx = 40, pady = 5)
    
        # frame-3: lower left
        frame_3 = Frame(self.app, bd = 5, relief = "groove")
        frame_3.grid(row = 15, column = 0, columnspan = 5, padx = 5, pady = 5)
        
        Label(frame_3, text = "Lower left").grid(row = 0, column = 0, padx = 5, pady = 5)
        Label(frame_3, text = "X = ").grid(row = 0, column = 1)
        self.x_lower_left_input = Entry(frame_3, width = 10, borderwidth = 5)
        self.x_lower_left_input.grid(row = 0, column = 2, padx = 5, pady = 5)
        Label(frame_3, text = "Y = ").grid(row = 0, column = 3)
        self.y_lower_left_input = Entry(frame_3, width = 10, borderwidth = 5)
        self.y_lower_left_input.grid(row = 0, column = 4)
        
        self.lower_left_read_button = Button(frame_3, text = "Set as current", command = lambda: self.read_position('ll'))
        self.lower_left_read_button.grid(row = 1, column = 0, columnspan = 2, padx = 5, pady = 5)
        
        self.lower_left_goto_button = Button(frame_3, text = "Go to", command = lambda: self.go_to_position('ll'))
        self.lower_left_goto_button.grid(row = 1, column = 2, columnspan = 3, ipadx = 40, pady = 5)
        
        # frame-4: lower right
        frame_4 = Frame(self.app, bd = 5, relief = "groove")
        frame_4.grid(row = 15, column = 5, columnspan = 5, padx = 5, pady = 5)
        
        Label(frame_4, text = "Lower right").grid(row = 0, column = 0, padx = 5, pady = 5)
        Label(frame_4, text = "X = ").grid(row = 0, column = 1)
        self.x_lower_right_input = Entry(frame_4, width = 10, borderwidth = 5)
        self.x_lower_right_input.grid(row = 0, column = 2, padx = 5, pady = 5)
        Label(frame_4, text = "Y = ").grid(row = 0, column = 3)
        self.y_lower_right_input = Entry(frame_4, width = 10, borderwidth = 5)
        self.y_lower_right_input.grid(row = 0, column = 4)
        
        self.lower_right_read_button = Button(frame_4, text = "Set as current", command = lambda: self.read_position('lr'))
        self.lower_right_read_button.grid(row = 1, column = 0, columnspan = 2, padx = 5, pady = 5)
        
        self.lower_right_goto_button = Button(frame_4, text = "Go to", command = lambda: self.go_to_position('lr'))
        self.lower_right_goto_button.grid(row = 1, column = 2, columnspan = 3, ipadx = 40, pady = 5)
        
        # some indicator, currently set to non-editable
        channel_label = Label(self.app, text = "Channel = ")
        channel_label.grid(row = 0, column = 5, padx = 5, pady = 5, sticky = 'E')
        self.channel_input = Entry(self.app, width = 10, borderwidth = 5)
        self.channel_input.grid(row = 0, column = 6, padx = 5, pady = 5, sticky = 'W')
        self.channel_input.insert(0, '0')
        self.channel_input.configure(state = 'readonly')
        
        detector_label = Label(self.app, text = "Detector (SE) = ")
        detector_label.grid(row = 1, column = 5, padx = 5, pady = 5, sticky = 'E')
        self.detector_input = Entry(self.app, width = 10, borderwidth = 5)
        self.detector_input.grid(row = 1, column = 6, padx = 5, pady = 5, sticky = 'W')
        self.detector_input.insert(0, '0')
        self.detector_input.configure(state = 'readonly')
        
        nbits_label = Label(self.app, text = "# bits per pxl = ")
        nbits_label.grid(row = 2, column = 5, padx = 5, pady = 5, sticky = 'E')
        self.nbits_input = Entry(self.app, width = 10, borderwidth = 5)
        self.nbits_input.grid(row = 2, column = 6, padx = 5, pady = 5, sticky = 'W')
        self.nbits_input.insert(0, '0')
        self.nbits_input.configure(state = 'readonly')
        
        scan_speed_label = Label(self.app, text = "Live scan speed = ")
        scan_speed_label.grid(row = 3, column = 5, padx = 5, pady = 5, sticky = 'E')
        self.scan_speed_input = Entry(self.app, width = 10, borderwidth = 5)
        self.scan_speed_input.grid(row = 3, column = 6, padx = 5, pady = 5, sticky = 'W')
        self.scan_speed_input.insert(0, '0')
        self.scan_speed_input.configure(state = 'readonly')
        
        beam_intensity_label = Label(self.app, text = "Beam intensity = ")
        beam_intensity_label.grid(row = 4, column = 5, padx = 5, pady = 5, sticky = 'E')
        self.beam_intensity_input = Entry(self.app, width = 10, borderwidth = 5)
        self.beam_intensity_input.grid(row = 4, column = 6, padx = 5, pady = 5, sticky = 'W')
        self.beam_intensity_input.insert(0, '0')
        self.beam_intensity_input.configure(state = 'readonly')
        
        voltage_label = Label(self.app, text = "High voltage (V) = ")
        voltage_label.grid(row = 5, column = 5, padx = 5, pady = 5, sticky = 'E')
        self.voltage_input = Entry(self.app, width = 10, borderwidth = 5)
        self.voltage_input.grid(row = 5, column = 6, padx = 5, pady = 5, sticky = 'W')
        self.voltage_input.insert(0, '0')
        self.voltage_input.configure(state = 'readonly')
        
        # some buttons to update, excute, etc
        # update SEM setting, and send some to GUI
        update_button = Button(self.app, text = "Update SEM Setting", command = self.click_to_update)
        update_button.grid(row = 6, column = 5, columnspan = 5, ipadx = 40, pady = 5)
        
        # start multi-tile imaging
        start_button = Button(self.app, text = "Start multi-tile imaging", command = self.start_imaging, bd = 5)
        start_button.grid(row = 16, column = 0, columnspan = 2, ipadx = 2, ipady = 20, pady = 10)
        
        # take calibration pairs
        calibration_button = Button(self.app, text = "Start calibration pairs", command = self.start_calibration, bd = 5)
        calibration_button.grid(row = 16, column = 3, columnspan = 3, ipadx = 5, ipady = 20, pady = 10)
        
        # start
        stop_button = Button(self.app, text = "Stop", command = self.stop_app, bd = 5)
        stop_button.grid(row = 16, column = 6, columnspan = 4, ipadx = 30, ipady = 20, pady = 10)
    
    # click button to get folder name
    def click_for_folder_name(self):
        self.folder_name = filedialog.askdirectory()
        self.folder_name_input.delete(0, END)
        self.folder_name_input.insert(0, self.folder_name)
        
    # click button to get exe name
    def click_for_external_exe_name(self):
        self.external_exe_name = filedialog.askopenfilename()
        self.external_exe_name_input.delete(0, END)
        self.external_exe_name_input.insert(0, self.external_exe_name)

    # click a button in the App to update SEM parameter indications, based on readout from SEM    
    def click_to_update(self):
        # update inputs
        self.nR = int(self.nR_input.get())
        self.nC = int(self.nC_input.get())
        self.view_field = float(self.view_field_input.get())
        self.dwell_ns = float(self.dwell_input.get())
        self.image_resolution = int(self.resolution_input.get())
        self.iR = int(self.iR_input.get())
        self.iC = int(self.iC_input.get())
        
        self.image_adjust_option
        self.image_capture_option
        self.sample_name = self.sample_name_input.get()
        self.folder_name = self.folder_name_input.get()
        self.external_exe_name = self.external_exe_name_input.get()
    
        # update read-onlys
        self.scan_speed = self.ScGetSpeed()
        self.scan_speed_input.configure(state = 'normal')
        self.scan_speed_input.delete(0, END)        
        self.scan_speed_input.insert(0, self.scan_speed)
        self.scan_speed_input.configure(state = 'readonly')
        
        self.beam_intensity = 21 - self.GetPCIndex()
        self.beam_intensity_input.configure(state = 'normal')
        self.beam_intensity_input.delete(0, END)        
        self.beam_intensity_input.insert(0, self.beam_intensity)
        self.beam_intensity_input.configure(state = 'readonly')
        
        self.voltage = self.HVGetVoltage()
        self.voltage_input.configure(state = 'normal')
        self.voltage_input.delete(0, END)        
        self.voltage_input.insert(0, self.voltage)
        self.voltage_input.configure(state = 'readonly')
        
    # read current stage position, and put it into the App
    def read_position(self, pos_str):
        if pos_str == 'ul':
            pos = self.StgGetPosition()
            self.pos_upper_left = [pos[0], pos[1]]
            self.x_upper_left_input.delete(0, END)
            self.x_upper_left_input.insert(0, pos[0])
            self.y_upper_left_input.delete(0, END)
            self.y_upper_left_input.insert(0, pos[1]) 
            self.WD_upper_left = self.GetWD()
        elif pos_str == 'ur':
            pos = self.StgGetPosition()
            self.pos_upper_right = [pos[0], pos[1]]
            self.x_upper_right_input.delete(0, END)
            self.x_upper_right_input.insert(0, pos[0])
            self.y_upper_right_input.delete(0, END)
            self.y_upper_right_input.insert(0, pos[1])
            self.WD_upper_right = self.GetWD()
        elif pos_str == 'll':
            pos = self.StgGetPosition()
            self.pos_lower_left = [pos[0], pos[1]]
            self.x_lower_left_input.delete(0, END)
            self.x_lower_left_input.insert(0, pos[0])
            self.y_lower_left_input.delete(0, END)
            self.y_lower_left_input.insert(0, pos[1])
            self.WD_lower_left = self.GetWD()
        elif pos_str == 'lr':
            pos = self.StgGetPosition()
            self.pos_lower_right = [pos[0], pos[1]]
            self.x_lower_right_input.delete(0, END)
            self.x_lower_right_input.insert(0, pos[0])
            self.y_lower_right_input.delete(0, END)
            self.y_lower_right_input.insert(0, pos[1])
            self.WD_lower_right = self.GetWD()
    
    # move stage to position indicated in the App
    def go_to_position(self, pos_str):
        if pos_str == 'ul':
            px = self.x_upper_left_input.get()
            py = self.y_upper_left_input.get()
            self.SetWaitFlags(self.wtflgB)
            self.StgMoveTo(px, py)
        elif pos_str == 'ur':
            px = self.x_upper_right_input.get()
            py = self.y_upper_right_input.get()
            self.SetWaitFlags(self.wtflgB)
            self.StgMoveTo(px, py)
        elif pos_str == 'll':
            px = self.x_lower_left_input.get()
            py = self.y_lower_left_input.get()
            self.SetWaitFlags(self.wtflgB)
            self.StgMoveTo(px, py)
        elif pos_str == 'lr':
            px = self.x_lower_right_input.get()
            py = self.y_lower_right_input.get()
            self.SetWaitFlags(self.wtflgB)
            self.StgMoveTo(px, py)
    
    # start
    def start_imaging(self):
        # update settings
        self.pos_upper_left = [float(self.x_upper_left_input.get()), float(self.y_upper_left_input.get())]
        self.pos_upper_right = [float(self.x_upper_right_input.get()), float(self.y_upper_right_input.get())]
        self.pos_lower_left = [float(self.x_lower_left_input.get()), float(self.y_lower_left_input.get())]
        self.pos_lower_right = [float(self.x_lower_right_input.get()), float(self.y_lower_right_input.get())]
        self.click_to_update()
        
        # iterate all positions to image
        self.live_imaging()
        continueTF = True
        while continueTF:
            self.move_to_iRiC()
            self.adjust_imaging()
            self.capture_image()
            self.live_imaging()
            continueTF = self.update_next_iRiC()

        self.move_to_iRiC()   
        self.HVBeamOff()
    
    # calibration
    def start_calibration(self):
        # update settings
        self.pos_upper_left = [float(self.x_upper_left_input.get()), float(self.y_upper_left_input.get())]
        self.click_to_update()
        step_size = self.view_field/20
        
        px = self.pos_upper_left[0]
        py = self.pos_upper_left[1]
        self.iC = 0
        self.iR = 0
        
        while True:
            self.StgMoveTo(px + step_size * self.iC, py + step_size * self.iR)
            # capture twice
            self.adjust_imaging()
            # This is for debugging
            self.image_capture_option.set('auto')
            self.capture_image()
            self.capture_image()
            self.image_capture_option.set('manual')
            self.capture_image()
            self.capture_image()
            
            self.live_imaging()
            
            # update for next position
            if self.iC < 1:
                self.iC += 1
            elif self.iR < 1:
                self.iR += 1
            else:
                print("End of calibration image pairs, move back")
                self.iR = 0
                self.iC = 0
                self.StgMoveTo(px, py)
                break
                
    # quit
    def stop_app(self):
        pass
    
def main():
    m = SemControl(channel = 0)
    m.build_app()
    m.app.mainloop()

if __name__ == "__main__":
    main()