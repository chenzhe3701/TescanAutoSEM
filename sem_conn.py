#
# SharkSEM Script
# version 2.0.16
#
# Requires Python 3.x
#
# Copyright (c) 2014 TESCAN Brno, s.r.o.
# http://www.tescan.com
#

import socket
import string
import struct
import sys

#
# decode string (UTF-8)
#
def DecodeString(s_in):
    i = 0
    for i in range(0, len(s_in)):
        if s_in[i] == 0:
            break            
    return s_in[0:i].decode()

#
# SharkSEM data types
#
class ArgType:
    """SharkSEM data types

    Contains the common types used in the client-server communication.
    """
    Int, UnsignedInt, String, Float, ArrayInt, ArrayUnsignedInt, ArrayByte = range(7)
    

#
# SharkSEM connection
#
class SemConnection:
    """SEM Connection Class

    This object keeps the connection context, ie. the communication sockets,
    scannig buffers and other context variables. There are also methods for 
    argument marshaling (packing / unpacking).
    """
    
    def __init__(self):
        """ Constructor """
        self.socket_c = 0       # control connection
        self.socket_d = 0       # data connection
        self.wait_flags = 0     # wait flags (bits 5:0)
        
    def _SendStr(self, s):
        """ Blocking send """
        size = len(s)
        start = 0
        while start < size:
            res = self.socket_c.send(s[start:size])
            start = start + res
            
    def _RecvFully(self, sock, size):
        """ Blocking receive - wait for all data """
        received = 0
        str = b""
        while received < size:
            s = sock.recv(size - received)
            received = received + len(s)
            str = str + s
        return str
            
    def _RecvStrC(self, size):
        """ Blocking receive - control connection """
        return self._RecvFully(self.socket_c, size)
    
    def _RecvStrD(self, size):
        """ Blocking receive - data connection """
        return self._RecvFully(self.socket_d, size)
    
    def _TcpRegDataPort(self, port):
        """ Register data portn in the SharkSEM server """
        return self.RecvInt('TcpRegDataPort', (ArgType.Int, port))

    def Connect(self, address, port):
        """ Connect to the server """
        try:
            self.socket_c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_c.connect((address, port))
            self.socket_d = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_d.bind(('', 0))
            loc_ep = self.socket_d.getsockname()
            loc_port = loc_ep[1]
            self._TcpRegDataPort(loc_port)
            self.socket_d.connect((address, port + 1))
            return 0
        
        except:
            self.Disconnect()
            return -1
        
    def Disconnect(self):
        """ Close the connection(s) """
        try:
            if self.socket_c != 0:
                socket.close(self.socket_c)
                self.socket_c = 0
            if self.socket_d != 0:
                socket.close(self.socket_d)
                self.socket_d = 0
        except:
            pass
        
    def FetchImage(self, fn_name, channel, size):
        """ Fetch image. See Sem.FetchImage for details """
        img = b""
        img_sz = 0
        while img_sz < size:
            # receive, parse and verify the message header
            msg_name = self._RecvStrD(16)
            hdr = self._RecvStrD(16)
            v = struct.unpack("<IIHHI", hdr)
            body_size = v[0]
            
            # get fn name
            s = DecodeString(msg_name)
            
            # receive and parse the body
            body = self._RecvStrD(body_size)
            if s != fn_name:
                continue
            if body_size < 20:
                continue
            body_params = body[0:20]
            body_data = body[20:]
            v = struct.unpack("<IIIII", body_params)
            arg_frame_id = v[0]
            arg_channel = v[1]
            arg_index = v[2]
            arg_bpp = v[3]
            arg_data_size = v[4]
            if arg_channel != channel:
                continue
            if arg_index < img_sz:         # correct, can be sent more than once
                img = img[0:arg_index]
                img_sz = arg_index
            if arg_index > img_sz:         # data packet lost
                continue
            
            # append data
            if arg_bpp == 8:
                img = img + body_data[0:arg_data_size]
                img_sz = img_sz + arg_data_size
            else:
                n = arg_data_size / 2
                for i in range(0, n):
                    img = img + body_data[2 * i + 1]
                img_sz = img_sz + n
            
        # when we have complete image, terminate
        return img
      
    def FetchImageEx(self, fn_name, channel_list, pxl_size):
        """ Fetch image. See Sem.FetchImageEx for details """
        
        # create channel -> index look up table
        ch_lookup = []
        for i in range (0, 4):
            ch_lookup.append(-1)
        n_channels = 0
        for ch in channel_list:
            ch_lookup[ch] = n_channels
            n_channels = n_channels + 1 
        
        # create empty image
        img = []
        img_sz = []
        img_done = []
        for i in range(0, n_channels):
            img.append(b"")
            img_sz.append(0)
            img_done.append(False)
            
        # process data
        acq_done = False
        while not acq_done:
            # receive, parse and verify the message header
            msg_name = self._RecvStrD(16)
            hdr = self._RecvStrD(16)
            v = struct.unpack("<IIHHI", hdr)
            body_size = v[0]
            
            # get fn name
            s = DecodeString(msg_name)
            
            # receive and parse the body
            body = self._RecvStrD(body_size)
            if s != fn_name:
                continue
            if body_size < 20:
                continue
            body_params = body[0:20]
            body_data = body[20:]
            v = struct.unpack("<IIIII", body_params)
            arg_frame_id = v[0]
            arg_channel = v[1]
            arg_index = v[2]
            arg_bpp = v[3]
            bytes_pp = arg_bpp / 8  
            arg_data_size = v[4]
            channel_index = ch_lookup[arg_channel]
            if channel_index < 0:                                   # check if we read this image
                continue
            if arg_index * bytes_pp < img_sz[channel_index]:        # correct, can be sent more than once
                img[channel_index] = img[channel_index][0:(arg_index * bytes_pp)]
                img_sz[channel_index] = arg_index * bytes_pp
            if arg_index * bytes_pp > img_sz[channel_index]:        # data packet lost
                continue
            
            # append data
            img[channel_index] = img[channel_index] + body_data[0:arg_data_size]
            img_sz[channel_index] = img_sz[channel_index] + arg_data_size
            
            # eavluate acq_done
            if img_sz[channel_index] == pxl_size * bytes_pp:
                img_done[channel_index] = True
            acq_done = True
            for i in range(0, n_channels):
                acq_done = acq_done and img_done[i] 
            
        # when we have complete image, terminate
        return img

    def FetchCameraImage(self, channel):
        """ Fetch camera image. See Sem.FetchCameraImage for details """
        img = b""
        img_received = 0
        while not img_received:
            # receive, parse and verify the message header
            msg_name = self._RecvStrD(16)
            hdr = self._RecvStrD(16)
            v = struct.unpack("<IIHHI", hdr)
            body_size = v[0]
            
            # get fn name
            s = DecodeString(msg_name)
                                        
            # receive and parse the body
            body = self._RecvStrD(body_size)
            if s != 'CameraData':
                continue
            if body_size < 20:
                continue
            body_params = body[0:20]
            body_data = body[20:]
            v = struct.unpack("<IIIII", body_params)
            arg_channel = v[0]
            arg_bpp = v[1]
            arg_width = v[2]
            arg_height = v[3]
            arg_data_size = v[4]
            if arg_channel != channel:
                continue
            if arg_bpp != 8:
                continue
            
            img_received = 1
            
            # append data
            arg_img = body_data
            
        # when we have complete image, terminate
        return (arg_width, arg_height, arg_img)

    def Send(self, fn_name, *args):
        """ Send simple message (header + data), no response expected
        
        This call has variable number of input arguments. Wait flags are 
        taken from self.wait_flags.
        
        Following types are supported:
            ArgType.Int
            ArgType.UnsignedInt
            ArgType.String
            ArgType.Float
            ArgType.ArrayInt
            ArgType.ArrayUnsignedInt
            ArgType.ArrayByte
            
        The Int and UnsignedInt types are mapped to 32-bit int, StringType
        is a variable sized string, FloatType is send as SharkSEM floating
        point value (actually string).
        
        String is UFT-8 compatible, ArrayByte is binary buffer. 
        
        Each argument is a tuple consisting of two items - type and value.
        
        SharkSEM header restrictions:
            - Flags (except for Wait flags) are set to 0
            - Identification = 0
            - Queue = 0
        """
        
        # build message body
        body = b""                           	# variable of type 'bytes'
        for pair in args:
            pair_type, pair_value = pair
            
            if pair_type == ArgType.Int:   				# 32-bit integer
                body = body + struct.pack("<i", pair_value)
                
            if pair_type == ArgType.UnsignedInt:   		# 32-bit unsigned integer
                body = body + struct.pack("<I", pair_value)

            if pair_type == ArgType.Float:              # floating point
                s = (str(pair_value) + "\x00\x00\x00\x00").encode()
                l = (len(s) // 4) * 4
                body = body + struct.pack("<I", l) + s[0:l]
        
            if pair_type == ArgType.String:             # string
                s = (str(pair_value) + "\x00\x00\x00\x00").encode()
                l = (len(s) // 4) * 4
                body = body + struct.pack("<I", l) + s[0:l]
                
            if pair_type == ArgType.ArrayByte:          # byte array
                s = str(pair_value) + "\x00\x00\x00\x00"
                l = (len(s) // 4) * 4
                body = body + struct.pack("<I", l) + s[0:l]

            if pair_type == ArgType.ArrayInt:   		# array of 32-bit integers
                items = len(pair_value)
                body = body + struct.pack("<I%di" % (items), items * 4, *pair_value)
                
            if pair_type == ArgType.ArrayUnsignedInt:   # array of 32-bit unsigned integers
                items = len(pair_value)
                body = body + struct.pack("<I%dI" % (items), items * 4, *pair_value)

        # build message header
        s = fn_name.ljust(16, "\x00")                   # pad fn name (string)
        hdr = s.encode()                                # convert to bytes
        hdr = hdr + struct.pack("<IIHHI", len(body), 0, (self.wait_flags << 8), 0, 0)       # arguments
        
        try:
            self._SendStr(hdr)                          # send header
            self._SendStr(body)                         # send body
            
        except:
            pass
    
    def Recv(self, fn_name, retval, *args):
        """ Send message and receive response
        
        This call has variable number of input arguments.

        List containing the output arguments is returned. The output
        argument types are passed in the 'retval' list, which contains
        Python types.

        Following types are supported:
            ArgType.Int
            ArgType.UnsignedInt
            ArgType.String
            ArgType.Float
            ArgType.ArrayInt
            ArgType.ArrayUnsignedInt
            ArgType.ArrayByte
            
        If array is specified, it appears as a list object in the output list.
        """
        
        # send request
        self.Send(fn_name, *args)
        
        try:
            # receive header
            fn_recv = self._RecvStrC(16)
            hdr = self._RecvStrC(16)
            
            # parse header
            v = struct.unpack("<IIHHI", hdr)
            body_size = v[0]
            
            # receive body
            body = self._RecvStrC(body_size)
            
        except:
            return

        # parse return value
        l = []
        start = 0
        
        for t in retval:
                        
            if t == ArgType.Int:   				# 32-bit integer
                stop = start + 4
                v = struct.unpack("<i", body[start:stop])
                l.append(v[0])
                start = stop
                
            if t == ArgType.UnsignedInt:   		# 32-bit unsigned integer
                stop = start + 4
                v = struct.unpack("<I", body[start:stop])
                l.append(v[0])
                start = stop

            if t == ArgType.Float:              # floating point
                stop = start + 4
                v = struct.unpack("<I", body[start:stop])
                fl_size = v[0]
                start = stop
                stop = start + fl_size
                s = DecodeString(body[start:stop])
                l.append(float(s))
                start = (start + fl_size + 3) // 4 * 4
                
            if t == ArgType.String:             # string
                stop = start + 4
                v = struct.unpack("<I", body[start:stop])
                fl_size = v[0]
                start = stop
                stop = start + fl_size
                s = DecodeString(body[start:stop])
                l.append(s)
                start = (start + fl_size + 3) // 4 * 4

            if (t == ArgType.ArrayInt or t == ArgType.ArrayUnsignedInt):           # int array, unsigned int array
                stop = start + 4
                v = struct.unpack("<I", body[start:stop])
                cnt = v[0] // 4
                start = stop
                stop = start + 4 * cnt
                if t == ArgType.ArrayInt:
                    arr_l = struct.unpack("<%di" % (cnt), body[start:stop])
                else:
                    arr_l = struct.unpack("<%dI" % (cnt), body[start:stop])
                l.append(arr_l)
                start = stop

            if t == ArgType.ArrayByte:          # byte array
                stop = start + 4
                v = struct.unpack("<I", body[start:stop])
                fl_size = v[0]
                start = stop
                stop = start + fl_size
                l.append(body[start:stop])
                start = (start + fl_size + 3) // 4 * 4

        return l
                
    def RecvInt(self, fn_name, *args):
        """ Simple variant of Recv() - single int value is expected """
        v = self.Recv(fn_name, (ArgType.Int,), *args)
        return v[0]

    def RecvUInt(self, fn_name, *args):
        """ Simple variant of Recv() - single unsigned int value is expected """
        v = self.Recv(fn_name, (ArgType.UnsignedInt,), *args)
        return v[0]

    def RecvFloat(self, fn_name, *args):
        """ Simple variant of Recv() - single float value is expected """
        v = self.Recv(fn_name, (ArgType.Float,), *args)
        return v[0]

    def RecvString(self, fn_name, *args):
        """ Simple variant of Recv() - single string value is expected """
        v = self.Recv(fn_name, (ArgType.String,), *args)
        return v[0]
