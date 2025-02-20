import binascii
import socket
import time
import struct
import dwaTools as dwa
import DwaConfigFile as dcf

# Should the socket be created and then closed/opened
# vs. re-creating each time in tcpOpen()?

PORT = 7

class DwaMicrozed():

    def __init__(self, ip=None):
        self.verbose = 1
        if self.verbose > 0:
            print("DwaMicrozed()")
        self.ip = ip
        self.port = PORT
        self.sock = None
        self.timeout = 2.0 # seconds
        self.sleepPostWrite = 0.05  # seconds
        self.sleepPostOpen = 0.2   # seconds
        self.closeTcpWhenDone = False
        
    def setIp(self, ip, port=None):
        """ Set the IP Address of Microzed board 
        Args:
            ip (str): ip address of microzed board
        
        Returns:
    
        Example:
        setIp('149.130.136.211')
        #HOST = '140.247.132.37' # NW Lab
        #HOST = '140.247.123.186'     # J156Lab
        #HOST = '149.130.136.211' # Wellesley DWA (MAC 0x84, 0x2b, 0x2b, 0x97, 0xda, 0x03)
        """
        self.ip = ip
        if port == None:
            self.port = PORT

    def _tcpOpen(self, persist=False, sleep=None):
        """ Open a tcp/ip connection to the microzed
        persist: if True, then require force=True for _tcpClose() 
        """

        # FIXME: what should we actually do if socket already open
        # (or not None, at least)?
        if self.sock != None:
            print("Warning: socket already exists")
            return

        if self.sock == None and not persist:
            self.closeTcpWhenDone = True
        
        try:
            # FIXME: should we use socket.SOCK_DGRAM instead of SOCK_STREAM?
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM )
            self.sock.setblocking(True)  # default should be blocking...
            self.sock.settimeout(self.timeout)
            #self.sock.settimeout(None)
        except socket.error:
            print("Failed to create socket")
            self.sock = None
        else:
            if (self.verbose > 0): print("Socket created")
            
        try:
            if self.verbose > 1:
                print("  self.sock.connect: ")
                print(f"   self.ip   = {self.ip}")
                print(f"   self.port = {self.port}")
                print(f"   self.sock.gettimeout() = {self.sock.gettimeout()}")
            self.sock.connect( (self.ip, self.port) )
        except socket.gaierror:
            print("Hostname could not be resolved. Exiting")
            self._tcpClose() # FIXME: does this work if connect failed?
        else:
            print(f"Socket connected to {self.ip}")

        if sleep != None:
            time.sleep(self.sleepPostOpen)
            

    def _tcpClose(self, force=False):
        # https://docs.python.org/3/library/socket.html#socket.socket.shutdown

        # how = socket.SHUT_RD or socket.SHUT_WR or socket.SHUT_RDWR
        # ss.shutdown(how)  

        if self.closeTcpWhenDone or force:
            self.sock.close()
            self.sock = None
            self.closeTcpWhenDone = False
            if (self.verbose > 0): print("Socket closed")

        
    def reset(self):
        if self.verbose > 0:
            print("DwaMicrozed.reset()")
            print(f"self.sock = {self.sock}")

        self._tcpOpen()
        #fromDaqReg.reset          <= slv_reg0(0)= '1';
        self._regWrite('00000000', '00000001')
        time.sleep(self.sleepPostWrite)
        self._tcpClose()

    def hvEnable(self):
        self._hvControl('00000000')
        
    def hvDisable(self):
        self._hvControl('00000001')
        
    def _hvControl(self, val):
        # It is accomplished by writing 1 to register address 0x38 (the HV-disable register).
        # Writing 0 to it reenables the HV to reach the wires.
        # val is a string: '00000001' or '00000000'
        self._tcpOpen()
        self._regWrite('00000038', val)
        time.sleep(self.sleepPostWrite)
        self._tcpClose()
        pass
    
    def scanConfig(self, cfg):
        self.config(cfg)
        
    def scanConfigMulti(self, cfg):
        self.configMulti(cfg)

    def configMulti(self, cfg):
        """ set multiple registers in a single tcp/ip call
        """
        addVals = []  # list of lists [ [address0,data0], [address1,data1], ... [addressN,dataN] ]
        print(f"verbose = {self.verbose}")
        
        # is this saying sweep vs. fixed freq?
        #fromDaqReg.auto           <= slv_reg1(0)= '1';
        addVals += [ ['00000001', cfg["auto"]] ]
        addVals += self.stimParamData(cfg)
        addVals += self.mainsSubtractionData(cfg)
        addVals += self.relayData(cfg)
        addVals += self.digipotData(cfg["digipot"])
        if (self.verbose > 0):
            print(addVals)

        self._tcpOpen(persist=True, sleep=self.sleepPostOpen)
        self._regWriteMulti(addVals)
        self._tcpClose(force=True)

        
    def config(self, cfg):
        """
        Args:
            config (dict): dictionary containing scan configuration parameters
        
        Returns:
    
        Example:
        """
        print(f"verbose = {self.verbose}")
    
        self._tcpOpen(persist=True, sleep=self.sleepPostOpen)
    
        #fromDaqReg.auto           <= slv_reg1(0)= '1';
        # is this saying sweep vs. fixed freq?
        self._regWrite('00000001', cfg["auto"])
        time.sleep(self.sleepPostWrite)

        self.setStimParams(cfg)
        self.setMainsSubtraction(cfg)
        self.setRelays(cfg)
        #self.setUdpAddress(cfg["client_IP"])
        self.setDigipots(cfg["digipot"])
    
        self._tcpClose(force=True)

    def start(self):
        #fromDaqReg.ctrlStart      <= slv_reg0(1)= '1';
        self._tcpOpen()
        self._regWrite('00000000', '00000002')
        time.sleep(self.sleepPostWrite)
        self._tcpClose()

    def abort(self):

        self._tcpOpen()
        self._regWrite('00000000', '00000008')
        time.sleep(self.sleepPostWrite)
        self._tcpClose()

            
    #### GET STATUS (DEFUNCT?) ###
    def stat(self):
    
        self._tcpOpen()
    
        # acStim_nPeriod
        self._regRead('0000000F')
        time.sleep(self.sleepPostWrite)
        # acStimX200_nPeriod
        self._regRead('00000010')
        time.sleep(self.sleepPostWrite)
        # ctrl busy
        self._regRead('00000011')
        time.sleep(self.sleepPostWrite)
        # constant
        self._regRead('00000012')
        time.sleep(self.sleepPostWrite)
        # fifoAutoDC_ff fifoAutoDC_ef
        self._regRead('0000001B')
        time.sleep(self.sleepPostWrite)
    
        self._tcpClose()
    
    def setStatusFramePeriod(self, statusPeriod):
        if self.verbose > 0:
            print(f"Setting STATUS frame period to {statusPeriod}")

        self._tcpOpen()
        self._regWrite('00000035', statusPeriod)
        time.sleep(self.sleepPostWrite)
        self._tcpClose()
        

    def stimParamData(self, cfg):
        return [ ['00000003', cfg["stimFreqReq"]],  #fromDaqReg.stimFreqReq  <= unsigned(slv_reg3(23 downto 0));
                 ['00000004', cfg["stimFreqMin"]],  #fromDaqReg.stimFreqMin  <= unsigned(slv_reg4(23 downto 0));
                 ['00000005', cfg["stimFreqMax"]],  #fromDaqReg.stimFreqMax  <= unsigned(slv_reg5(23 downto 0));
                 ['00000006', cfg["stimFreqStep"]], #fromDaqReg.stimFreqStep <= unsigned(slv_reg6(23 downto 0));
                 ['00000007', cfg["stimTime"]],     #fromDaqReg.stimRampTime <= unsigned(slv_reg7(23 downto 0));
                 ['00000008', cfg["stimMag"]],      #fromDaqReg.stimMag      <= unsigned(slv_reg8(23 downto 0));
                 ['0000002C', cfg["stimTimeInitial"]],   # stimTimeInit
                 ['0000000A', cfg["cyclesPerFreq"]], #fromDaqReg.nAdcStimPeriod <= unsigned(slv_reg10(23 downto 0));
                 ['0000000B', cfg["adcSamplesPerCycle"]] #fromDaqReg.nAdcStimPeriodSamp <= unsigned(slv_reg11(23 downto 0));
                 ]

    
    def setStimParams(self, cfg):

        print("Setting stimFreq parameters")
        self._tcpOpen(sleep=self.sleepPostOpen)

        #fromDaqReg.stimFreqReq  <= unsigned(slv_reg3(23 downto 0));
        self._regWrite('00000003', cfg["stimFreqReq"])
        time.sleep(self.sleepPostWrite)
        #fromDaqReg.stimFreqMin  <= unsigned(slv_reg4(23 downto 0));
        self._regWrite('00000004', cfg["stimFreqMin"])
        time.sleep(self.sleepPostWrite)
        #fromDaqReg.stimFreqMax  <= unsigned(slv_reg5(23 downto 0));
        self._regWrite('00000005', cfg["stimFreqMax"])
        time.sleep(self.sleepPostWrite)
        #fromDaqReg.stimFreqStep <= unsigned(slv_reg6(23 downto 0));
        self._regWrite('00000006', cfg["stimFreqStep"])
        time.sleep(self.sleepPostWrite)

        print("Setting stimTime, stimMag, and stimTimeInitial")
        #fromDaqReg.stimRampTime   <= unsigned(slv_reg7(23 downto 0));
        self._regWrite('00000007', cfg["stimTime"])
        time.sleep(self.sleepPostWrite)
        #fromDaqReg.stimMag        <= unsigned(slv_reg8(23 downto 0));
        self._regWrite('00000008', cfg["stimMag"])
        time.sleep(self.sleepPostWrite)
        # stimTimeInit
        self._regWrite('0000002C', cfg["stimTimeInitial"])
        time.sleep(self.sleepPostWrite)

        print("Setting cyclesPerFreq and adcSamplesPerCycle")
        #fromDaqReg.nAdcStimPeriod <= unsigned(slv_reg10(23 downto 0));
        self._regWrite('0000000A', cfg["cyclesPerFreq"])
        time.sleep(self.sleepPostWrite)
        #fromDaqReg.nAdcStimPeriodSamp <= unsigned(slv_reg11(23 downto 0));
        self._regWrite('0000000B', cfg["adcSamplesPerCycle"])
        time.sleep(self.sleepPostWrite)

        self._tcpClose()
            
    def mainsSubtractionData(self, cfg):
        return [ ['00000019', cfg["noiseFreqMin"]], #fromDaqReg.noiseFreqMin  <= unsigned(slv_reg25(23 downto 0));
                 ['0000001A', cfg["noiseFreqMax"]], #fromDaqReg.noiseFreqMax  <= unsigned(slv_reg26(23 downto 0));
                 ['0000001C', cfg["noiseSamplingPeriod"]], #fromDaqReg.noiseSampPer  <= unsigned(slv_reg28(23 downto 0));
                 ['0000001D', cfg["noiseAdcSamplesPerFreq"]], #fromDaqReg.noiseNCnv     <= unsigned(slv_reg29(23 downto 0));
                 ['0000001E', cfg["noiseSettlingTime"]], #fromDaqReg.noiseBpfSetTime <= unsigned(slv_reg30(23 downto 0));
                ]
        
    def setMainsSubtraction(self, cfg):

        print("Setting mains subtraction parameters")

        self._tcpOpen(sleep=self.sleepPostOpen)

        #fromDaqReg.noiseFreqMin  <= unsigned(slv_reg25(23 downto 0));
        self._regWrite('00000019', cfg["noiseFreqMin"])
        time.sleep(self.sleepPostWrite)
        #fromDaqReg.noiseFreqMax  <= unsigned(slv_reg26(23 downto 0));
        self._regWrite('0000001A', cfg["noiseFreqMax"])
        time.sleep(self.sleepPostWrite)
        #fromDaqReg.noiseSampPer  <= unsigned(slv_reg28(23 downto 0));
        self._regWrite('0000001C', cfg["noiseSamplingPeriod"])
        time.sleep(self.sleepPostWrite)
        #fromDaqReg.noiseNCnv     <= unsigned(slv_reg29(23 downto 0));
        self._regWrite('0000001D', cfg["noiseAdcSamplesPerFreq"])
        time.sleep(self.sleepPostWrite)
        #fromDaqReg.noiseBpfSetTime <= unsigned(slv_reg30(23 downto 0));
        self._regWrite('0000001E', cfg["noiseSettlingTime"])
        time.sleep(self.sleepPostWrite)

        self._tcpClose()


    def disableAllRelays(self):
        """ set all relays to be inactive (no connection from input to output) 
        via a single TCP/IP transmission
        """
        print("DwaMicrozed: disableAllRelaysOneAtATime")
        offState = '0000'
        relayCfg = {
            "relayWireBot0":offState,
            "relayWireBot1":offState,
            "relayWireBot2":offState,
            "relayWireBot3":offState,
            "relayBusBot0":offState,
            "relayBusBot1":offState,
            "relayWireTop0":offState,
            "relayWireTop1":offState,
            "relayWireTop2":offState,
            "relayWireTop3":offState,
            "relayBusTop0":offState,
            "relayBusTop1":offState
        }
        
        addVals = []  # list of lists [ [address0,data0], [address1,data1], ... [addressN,dataN] ]
        addVals += self.relayData(relayCfg)

        if (self.verbose > 0):
            print(addVals)

        self._tcpOpen(sleep=self.sleepPostOpen)
        self._regWriteMulti(addVals)
        self._tcpClose(force=True)

        
    def disableAllRelaysOneAtATime(self):
        """ set all relays to be inactive (no connection from input to output) """
        print("DwaMicrozed: disableAllRelaysOneAtATime")
        offState = '0000'
        relayCfg = {
            "relayWireBot0":offState,
            "relayWireBot1":offState,
            "relayWireBot2":offState,
            "relayWireBot3":offState,
            "relayBusBot0":offState,
            "relayBusBot1":offState,
            "relayWireTop0":offState,
            "relayWireTop1":offState,
            "relayWireTop2":offState,
            "relayWireTop3":offState,
            "relayBusTop0":offState,
            "relayBusTop1":offState
        }
        self.setRelays(relayCfg)

    def relayData(self, cfg):
        return [ ['00000020', cfg["relayWireBot0"]], 
                 ['00000021', cfg["relayWireBot1"]],
                 ['00000022', cfg["relayWireBot2"]],
                 ['00000023', cfg["relayWireBot3"]],
                 # relayBusBot
                 ['00000024', cfg["relayBusBot0"]], 
                 ['00000025', cfg["relayBusBot1"]],
                 # relayWireTop
                 ['00000026', cfg["relayWireTop0"]],
                 ['00000027', cfg["relayWireTop1"]],
                 ['00000028', cfg["relayWireTop2"]],
                 ['00000029', cfg["relayWireTop3"]],
                 # relayBusTop
                 ['0000002A', cfg["relayBusTop0"]],
                 ['0000002B', cfg["relayBusTop1"]],
                 # OK to write
                 # The "update relays" signal is the third bit in register 0
                 # This bit just needs to be written and not cleared.
                 ['00000000', '00000004']
                 ]

        
    def setRelays(self, cfg):
        # Relays
        #v3 relays.  16bits each relayWireBot(0), ... relayWireBot(3)
        # relayWireTop(0), ..., relayWireTop(3)
        # relayBusBot(0), relayBusBot(1)
        # relayBusTop(0), relayBusTop(1)
        # relayWireBot
        
        print("Setting v3 relays")

        self._tcpOpen(sleep=self.sleepPostOpen)
        self._regWrite('00000020', cfg["relayWireBot0"])
        time.sleep(self.sleepPostWrite)
        self._regWrite('00000021', cfg["relayWireBot1"])
        time.sleep(self.sleepPostWrite)
        self._regWrite('00000022', cfg["relayWireBot2"])
        time.sleep(self.sleepPostWrite)
        self._regWrite('00000023', cfg["relayWireBot3"])
        time.sleep(self.sleepPostWrite)
        # relayBusBot
        self._regWrite('00000024', cfg["relayBusBot0"])
        time.sleep(self.sleepPostWrite)
        self._regWrite('00000025', cfg["relayBusBot1"])
        time.sleep(self.sleepPostWrite)
        # relayWireTop
        self._regWrite('00000026', cfg["relayWireTop0"])
        time.sleep(self.sleepPostWrite)
        self._regWrite('00000027', cfg["relayWireTop1"])
        time.sleep(self.sleepPostWrite)
        self._regWrite('00000028', cfg["relayWireTop2"])
        time.sleep(self.sleepPostWrite)
        self._regWrite('00000029', cfg["relayWireTop3"])
        time.sleep(self.sleepPostWrite)
        # relayBusTop
        self._regWrite('0000002A', cfg["relayBusTop0"])
        time.sleep(self.sleepPostWrite)
        self._regWrite('0000002B', cfg["relayBusTop1"])
        time.sleep(self.sleepPostWrite)
        # OK to write
        # The "update relays" signal is the third bit in register 0
        # This bit just needs to be written and not cleared.
        self._regWrite('00000000', '00000004')
        time.sleep(self.sleepPostWrite)

        self._tcpClose()
        
    def setUdpAddress(self, address):
        # IP address where the UDP data will be sent (e.g. IP address of the DAQ computer)
    
        # "address" can either be an IP string like 149.130.136.84
        # or it can be a 32-bit hex representation of that string like '95828854'

        print("Setting UDP address")

        self._tcpOpen(sleep=self.sleepPostOpen)
        
        if address.find('.') > -1:
            address = dwa.ipAddressToHexStr(address)
    
        self._regComm(payload_header='abcd1234', payload_type='FE170003', address=address)

        self._tcpClose()

   
    def digipotData(self, cfgstr):
        cfgEven  = cfgstr[2:4]+cfgstr[6:8]+cfgstr[10:12]+cfgstr[14:16]
        cfgOdd = cfgstr[0:2]+cfgstr[4:6]+cfgstr[8:10]+cfgstr[12:14]
        print(f"cfgEven = {cfgEven}")
        print(f"cfgOdd  = {cfgOdd}")
        return [ ['0000000F', cfgEven], # Even digipots
                 ['00000010', cfgOdd]   # Odd digipots
                 ]

        
    def setDigipots(self, cfgstr):
        """ cfgstr is an 8-channel string: 8 x 8-bit values, one per digipot
        e.g. cfgstr = '0706050403020100'
        where '00' is a hex string to configure digipot 0
        where '01' is a hex string to configure digipot 1
        ...
        where '07' is a hex string to configure digipot 7
        
        The cfgstr has been validated elsewhere (see dwaValidateConfigParams() )
        """
    
        # Construct the register values for the digipot
        # self._regWrite("F", "0F0F0F0F0F")
        # 
        # The association between digipots and register is even channels
        # (0, 2, 4, 6) on register 0xF and odd channels (1, 3, 5, 7) on
        # register 0x10. Within a register value, the ordering of the
        # digipots follows 0xDDCCBBAA, where AA is the 8-bit value for
        # channel 0 or 1, BB for channel 2 or 3, CC for channel 4 or 5 and
        # DD for channel 6 or 7.

        print("Setting Digipots")

        self._tcpOpen(sleep=self.sleepPostOpen)
        
        cfgEven  = cfgstr[2:4]+cfgstr[6:8]+cfgstr[10:12]+cfgstr[14:16]
        cfgOdd = cfgstr[0:2]+cfgstr[4:6]+cfgstr[8:10]+cfgstr[12:14]
        print(f"cfgEven = {cfgEven}")
        print(f"cfgOdd  = {cfgOdd}")
        # Even digipots
        self._regWrite('0000000F', cfgEven)
        # Odd digipots
        self._regWrite('00000010', cfgOdd)
        time.sleep(self.sleepPostWrite)

        self._tcpClose()

    def readValue(self, address):
        print("====readValue")
        self._tcpOpen(sleep=self.sleepPostOpen)
        print("====_regRead")
        val = self._regRead(address)
        time.sleep(self.sleepPostWrite)
        #print(f"val = {val}")
        print("====_tcpClose()")
        self._tcpClose()
        return val
        
    def _regComm(self, payload_header='abcd1234', payload_type=None, 
                   address=None, value=None):
    
        if payload_type == None:
            print("_regComm: ERROR -- must specify payload_type")
            #sys.exit()
        if address == None:
            print("_regComm: ERROR -- must specify address")
            #sys.exit()
        
        if value == None:
            # This is a reg read or a UDP IP address set
            # https://docs.python.org/2/library/struct.html#byte-order-size-and-alignment
            # '!' means network byte order (big-endian)
            # '>' means big-endian
            packerString = "!L L L"
            values = ( int(payload_header,16), int(payload_type, 16), int(address, 16) )
        else:
            # This a reg write, with a "value" entry
            packerString = "!L L L L"
            values = ( int(payload_header,16), int(payload_type, 16), int(address, 16), int(value, 16) )
    
        try :
            packer = struct.Struct(packerString)
            packed_data = packer.pack(*values)
            #print('PAYLOAD_HEADER = {0:s}'.format(payload_header))
            #print('PAYLOAD_TYPE = {0:s}'.format(payload_type)) 
            #print('ADDRESS = {0:s}'.format(address))
            #print('values = {}'.format(values))
            print(f'PAYLOAD_HEADER, PAYLOAD_TYPE, ADDRESS, values = {payload_header}, {payload_type}, {address}, {values}')
            #
            print('Sending...',end='')
            self.sock.sendall(packed_data)
            time.sleep(self.sleepPostWrite)
            #FIXME: don't actually know if msg is sent successfully...
            print('Message sent successfully')
        except socket.error:
            #Send failed
            print('Send failed')
            print(socket.error)
            #sys.exit()
        
        #get reply and print
        if payload_type != 'FE170003':
            #print(self._recvTimeout(timeout=2))
            return self._recvTimeout(timeout=2)
        
    
    def _regRead(self, address):
        print(f'self.sock = {self.sock}')
        return self._regComm(payload_header='abcd1234', payload_type='FE170001',
                             address=address)
    
    def _recvTimeout(self, timeout=2):
        # FIXME: there is not actually a timeout!!!!
    
        # make socket non blocking
        # https://docs.python.org/2/library/socket.html#socket.socket.setblocking
        # FIXME: should this be non-blocking???
        #self.sock.setblocking(0)
        self.sock.setblocking(True)
    
        # receive/unpack
        unpacker = struct.Struct('!L L L')
        data = self.sock.recv(unpacker.size)
        # Data arrives in 4-byte chunks
        # First 4-Byte chunk is F1000000
        # Second 4-Byte chunk specifies which register address was read e.g. '00000000'
        # Third 4-Byte chunk contains the data at that address (e.g. 'A1000000')
        #
        # This assumes that we will only get three 4-byte chunks...
        header_bin = data[0:4]   # first  4 bytes
        address_bin = data[4:8]  # second 4 bytes
        data_bin = data[8:]      # third  4 bytes
    
        # FIXME: add verbose check
        #print('type(data) = {}'.format(type(data)))
        #print('binascii.hexlify(header_bin) = {}'.format(binascii.hexlify(header_bin)))
        #print('binascii.hexlify(address_bin) = {}'.format(binascii.hexlify(address_bin)))
        #print('binascii.hexlify(data_bin) = {}'.format(binascii.hexlify(data_bin)))
        print(f'binascii.hexlify: header_bin, address_bin, data_bin: {binascii.hexlify(header_bin)}, {binascii.hexlify(address_bin)}, {binascii.hexlify(data_bin)}')

        unpacked_data = unpacker.unpack(data)
        print(f'received, unpacked: {binascii.hexlify(data)}, {unpacked_data}')
        #print('unpacked:')
        #print(unpacked_data)
    
        return(unpacked_data)
    

    def _regWriteMulti(self, cmds):
        # cmds is a list of lists with following format:
        # [ [address0, value0], [address1, value1], ..., [addressN, valueN] ]
        
        PAYLOAD_HEADER = 'abcd1234'
        PAYLOAD_TYPE = 'FE170002'      # For writing register

        cmds_flat = [item for sublist in cmds for item in sublist]
        cmds_flat.insert(0, PAYLOAD_TYPE)
        cmds_flat.insert(0, PAYLOAD_HEADER)
        #print("cmds_flat (strings) = ")
        cmds_flat = [int(x, 16) for x in cmds_flat]  # convert to hex integers
        
        cmds_flat = tuple(cmds_flat)
        #print("cmds = ")
        #print(cmds)
        #print("cmds_flat = ")
        #print(cmds_flat)
        #values = ( int(PAYLOAD_HEADER,16), int(PAYLOAD_TYPE,16), 

        structFmt = '!'+"L "*len(cmds_flat)
        #print(f"pre-strip:  [{structFmt}]")
        structFmt = structFmt.rstrip()
        #print(f"post-strip: [{structFmt}]")

        try:
            packer = struct.Struct(structFmt)
            msg = packer.pack(*cmds_flat)
            if (self.verbose > 0):
                print(f'PAYLOAD_HEADER, PAYLOAD_TYPE = {PAYLOAD_HEADER}, {PAYLOAD_TYPE}')
                print(f'  cmds      = {cmds}')
                print(f'  cmds_flat = {cmds_flat}')
                
            if (self.verbose > 0): print('Sending...', end='')
            self.sock.sendall(msg)
            time.sleep(0.2)
            if (self.verbose > 0): print('Message sent successfully')
        except socket.error:
            #Send failed
            print('_regWriteMulti(): Send failed')
            #sys.exit()
        
    def _regWrite(self, address, value):
        # address   Register address to write to 8 element hex string (e.g. '00000000')
        # value     Value to write to that address. 8 element hex string (e.g. 'A1000000')
    
        # Specific values for DWA FPGA
        # FIXME: put these somewhere more global?
        PAYLOAD_HEADER = 'abcd1234'
        PAYLOAD_TYPE = 'FE170002'      # For writing register
    
        #Send some data to remote server
        # Send binary data via socket
        try:
            values = ( int(PAYLOAD_HEADER,16), int(PAYLOAD_TYPE, 16), int(address, 16), int(value, 16) )
    
            # '!' means network byte order (big-endian)
            # '>' means big-endian
            # https://docs.python.org/2/library/struct.html#byte-order-size-and-alignment
            packer = struct.Struct('!L L L L')
    
            msg = packer.pack(*values)
            if (self.verbose > 0):
                print(f'PAYLOAD_HEADER, PAYLOAD_TYPE, ADDRESS, values = {PAYLOAD_HEADER}, {PAYLOAD_TYPE}, {address}, {value}, {values}')
                #print('PAYLOAD_HEADER = {0:s}'.format(PAYLOAD_HEADER))
                #print('PAYLOAD_TYPE = {0:s}'.format(PAYLOAD_TYPE))
                #print('ADDRESS = {0:s}'.format(address))
                #print('VALUE = {0:s}'.format(value))
                #print('values = {}'.format(values))
            
            if (self.verbose > 0): print('Sending...', end='')
            self.sock.sendall(msg)
            time.sleep(0.2)
            if (self.verbose > 0): print('Message sent successfully')
        except socket.error:
            #Send failed
            print('_regWrite(): Send failed')
            #sys.exit()
    
        #print("FIXME: SHOULD WE READ AFTER WRITE?")
        #get reply and print
        #print recv_timeout(s)


    def setVerbose(self, verbose):
        self.verbose=verbose

    
#    def _dwaRegRead2(self, address):
#        try :
#            # Send binary data via socket
#            # FIXME: put these somewhere more global?
#            PAYLOAD_HEADER = 'abcd1234'
#            PAYLOAD_TYPE = 'FE170001'
#    
#            # For reading register
#            values = ( int(PAYLOAD_HEADER,16), int(PAYLOAD_TYPE, 16), int(address, 16) )
#    
#            # https://docs.python.org/2/library/struct.html#byte-order-size-and-alignment
#            # '!' means network byte order (big-endian)
#            # '>' means big-endian
#            packer = struct.Struct('!L L L')
#            packed_data = packer.pack(*values)
#            print('PAYLOAD_HEADER = {0:s}'.format(PAYLOAD_HEADER))
#            print('PAYLOAD_TYPE = {0:s}'.format(PAYLOAD_TYPE))
#            print('ADDRESS = {0:s}'.format(address))
#            print('values = {}'.format(values))
#            #
#            print('Sending...')
#            self.sock.sendall(packed_data)
#            time.sleep(0.25)
#            #FIXME: don't actually know if msg is sent successfully...
#            print('Message sent successfully')
#        except socket.error:
#            #Send failed
#            print('Send failed')
#            sys.exit()
#        
#        #get reply and print
#        print(self.dwaRecvTimeout(ss, timeout=2))


        
    def dwaInitialize(self, serial_number: str, ip_address: str, mac_address_msb: str, mac_address_lsb: str):
        '''Initialize MAC address and IP address of DWA by writing to memory on analog board.'''
        
        self._tcpOpen(sleep=self.sleepPostOpen)
        
        # Set memory address to beginning
        self._regWrite('00000031', '00000000')
        time.sleep(self.sleepPostWrite)
        
        # Set DWA serial number
        self._regWrite('00000032', serial_number)
        time.sleep(self.sleepPostWrite)
        
        # Set local IP address
        self._regWrite('00000032', ip_address)
        time.sleep(self.sleepPostWrite)        
        
        # Set MSBs of MAC address
        self._regWrite('00000032', mac_address_msb)
        time.sleep(self.sleepPostWrite)
        
        # Set LSBs of MAC address
        self._regWrite('00000032', mac_address_lsb)
        time.sleep(self.sleepPostWrite)

        # Reset memory address to beginning
        self._regWrite('00000031', '00000000')
        time.sleep(self.sleepPostWrite)

        self._tcpClose()

    def setStimMag(self, gain):
        '''Set stimMag parameter.'''
        self._tcpOpen(sleep=self.sleepPostOpen)

        self._regWrite('00000008', gain)
        time.sleep(self.sleepPostWrite)

        self._tcpClose()
