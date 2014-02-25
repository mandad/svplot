"""
par.py
G.Rice 6/20/2012
V0.2.1 7/1/2013

Intended to read Kongsberg/Simrad *.all files.
"""

import numpy as np
from numpy import sin, cos, pi
from matplotlib import pyplot as plt
import struct
import mmap
import datetime as dtm
import pickle
import sys, os

try:
    import svp
    have_svp_module = True
except ImportError:
    have_svp_module = False

class allRead:
    """
    The class for handling the file.
    """
    def __init__(self, infilename, verbose = False, byteswap = False):
        """Make a instance of the allRead class."""
        self.infilename = infilename
        self.byteswap = byteswap
        # tempfile = open(infilename, 'r+b')
        # self.infile = mmap.mmap(tempfile.fileno(), 0)
        # tempfile.close()
        self.infile = open(infilename, 'rb')
        self.mapped = False
        self.packet_read = False
        self.eof = False
        self.error = False
        self.infile.seek(0,2)
        self.filelen = self.infile.tell()
        self.infile.seek(0)
        
    def close(self):
        self.infile.close()
        
    def read(self):
        """
        Reads the header.
        """
        if self.infile.tell() == self.filelen:
                self.eof = True
        if not self.eof:
            if self.byteswap:
                packetsize = 4 + np.fromfile(self.infile, dtype=np.uint32, count=1)[0].newbyteorder()
            else:
                packetsize = 4 + np.fromfile(self.infile, dtype=np.uint32, count=1)[0]
            self.infile.seek(-4, 1)
            if self.filelen >= self.infile.tell() + packetsize:
                self.packet = Datagram(self.infile.read(packetsize), self.byteswap)
                self.packet_read = True
                if not self.packet.valid:
                    self.error = True
                    print "Record without proper STX or ETX found."
            else:
                self.eof = True
                self.error = True
                print "Broken packet found at", self.infile.tell()
                print "Final packet size", packetsize
        
    def get(self):
        """
        Decodes the data section of the datagram if a packet has been read but
        not decoded.  If excecuted the packet_read flag is set to False.
        """
        if self.packet_read and not self.packet.decoded:
            self.packet.decode()
            self.packet_read = False
        
    def mapfile(self, verbose = False):
        """
        Maps the datagrams in the file.
        """
        progress = 0
        if not self.mapped:
            self.map = mappack()
            self.reset()
            print 'Mapping file;           ',
            while not self.eof:
                loc = self.infile.tell()
                self.read()
                dtype = self.packet.header[2]
                time = self.packet.gettime()
                self.map.add(str(dtype), loc, time)
                current = 100 * loc / self.filelen
                if current - progress >= 1 and verbose:
                    progress = current
                    sys.stdout.write('\b\b\b\b\b\b\b\b\b\b%(percent)02d percent' %{'percent':progress})
            self.reset()
            # make map into an array and sort by the time stamp
            self.map.finalize()
            if self.error:
                print
            else:
                print '\b\b\b\b\b\b\b\b\b\b\b\b finished mapping file.'
            if verbose:
                self.map.printmap()
            self.mapped = True
        else:
            pass
        
    def loadfilemap(self, mapfilename = ''):
        """
        Loads the packdir if the map object packdir has been saved previously.
        """
        if mapfilename == '':
            mapfilename = self.infilename[:-3] + 'par'
        try:
            self.map = mappack()
            self.map.load(mapfilename)
            self.mapped = True
            print 'loaded file map ' + mapfilename
        except IOError:
            print mapfilename + ' map file not found.'
            
    def savefilemap(self):
        """
        Saves the mappack packdir dictionary for faster operations on a file in
        the future.  The file is saved under the same name as the loaded file
        but with a 'par' extension.
        """
        if self.mapped:
            mapfilename = self.infilename[:-3] + 'par'
            self.map.save(mapfilename)
            print 'file map saved to ' + mapfilename
        else:
            print 'no map to save.'
            
        
    def getrecord(self, recordtype, recordnum):
        """
        Gets the record number of the described record type.
        """
        if not self.mapped:
            self.mapfile()
        if self.map.packdir.has_key(str(recordtype)):
            loc = self.map.packdir[str(recordtype)][recordnum][0]
            self.infile.seek(loc)
            self.read()
            self.get()
        else:
            print "record " + str(recordtype) + " not available."
            
    def findpacket(self, recordtype, verbose = False):
        """
        Find the next record of the requested type.
        """
        self.read()
        while not self.eof:
            if verbose:
                print self.packet.dtype
            if recordtype == self.packet.dtype:
                break
            else:
                self.read()
        self.get()
        
    def getwatercolumn(self,recordnum):
        """
        This method is designed to get a watercolumn packet by the ping number
        where ping 0 is the first in the file.  Separate records are
        reassembled for the whole ping and stored as the current subpack class
        as if it were a single record.
        """
        if not self.mapped:
            self.mapfile()
        timelist = list(set(self.map.packdir['107'][:,1]))
        timelist.sort()
        time = timelist[recordnum]
        inx = np.nonzero(self.map.packdir['107'][:,1] == time)[0]
        self.getrecord(107,inx[0])
        numbeams = self.packet.subpack.header['Total#Beams']
        totalsamples, subbeams = self.packet.subpack.ampdata.shape
        rx = np.zeros(numbeams, dtype = Data107.nrx_dtype)
        ampdata = np.zeros((totalsamples, numbeams), dtype = 'b')
        rx[:subbeams] = self.packet.subpack.rx
        ampdata[:,:subbeams] = self.packet.subpack.ampdata
        beamcount = subbeams
        if len(inx) > 1:
            for n in inx[1:]:
                self.getrecord(107, n)
                numsamples, subbeams = self.packet.subpack.ampdata.shape
                if numsamples > totalsamples:
                    temp = np.zeros((numsamples - totalsamples, numbeams), dtype = 'b')
                    ampdata = np.append(ampdata, temp, axis = 0)
                    totalsamples = numsamples
                rx[beamcount:beamcount+subbeams] = self.packet.subpack.rx
                ampdata[:numsamples,beamcount:beamcount+subbeams] = self.packet.subpack.ampdata
                beamcount += subbeams
        self.packet.subpack.rx = rx
        self.packet.subpack.ampdata = ampdata
        self.packet.subpack.header[2] = 1
        self.packet.subpack.header[3] = 1
            
    def display(self):
        """
        Prints the current record header and record type header to the command
        window.  If the record type header display method also contains a plot
        function a plot will also be displayed.
        """
        if self.packet_read:
            self.packet.display()
        elif self.__dict__.has_key('packet'):
            self.packet.display()
            if self.packet.decoded:
                self.packet.subpack.display()
        else:
            print 'No record currently read.'
        
    def reset(self):
        """
        Puts the file pointer to the start and the eof to False.
        """
        self.infile.seek(0)
        self.packet_read = False
        self.eof = False
        if self.__dict__.has_key('packet'):
            del self.packet
        
    def getnav(self, tstamps, postype = 80, att_type = 65, degrees = True):
        """
        For each provided time stamp (single or array) an array
        of navigation data is returned for each of the provided time stamps.
        The returned array set consists of time, x(deg), y(deg), roll (deg), 
        pitch(deg), heave (meters), and heading (deg).  Time stamps are to be
        POSIX time stamps, and are assumed to be in UTC. Set the 'degrees'
        keyword to False have the returned attitude informaiton in radians.
        """
        # make incoming tstamp shape more flexible
        tstamps = np.asarray(tstamps)
        ndim = tstamps.shape
        if len(ndim) == 0:
            tstamps = np.array([tstamps])
        elif len(ndim) == 2:
            tstamps = tstamps[0]
        numpts = len(tstamps)
        # make an array of all the needed data
        if not self.__dict__.has_key('navarray'):
            self.build_navarray()
        # find bounding times for getting all needed nav data
        if self.navarray.has_key(str(att_type)) and self.navarray.has_key(str(postype)):
            mintime = max(self.navarray[str(att_type)][0,0], self.navarray[str(postype)][0,0])
            maxtime = min(self.navarray[str(att_type)][-1,0], self.navarray[str(postype)][-1,0])
            navpts = np.zeros((numpts,7))
            # look for time stamps in the time range
            idx_range = np.nonzero((tstamps <= maxtime) & (tstamps >= mintime))[0]
            if len(idx_range) > 0:
                pos = self.navarray[str(postype)]
                att = self.navarray[str(att_type)]
                # for time stamps in the time range, find that nav and att
                for i in idx_range:
                    ts = tstamps[i]
                    prev = np.nonzero(pos[:,0] <= ts)[0][-1]
                    navpts[i,:3] = self._interp_points(tstamps[i], pos[prev,:], pos[prev + 1,:])
                    prev = np.nonzero(att[:,0] <= tstamps[i])[0][-1]
                    navpts[i,3:] = self._interp_points(tstamps[i], att[prev,:], att[prev + 1,:])[1:]
            # convert roll(3), pitch(4) and heading(6) into radians 
            if not degrees:
                navpts[:,[3,4,6]] = np.deg2rad(navpts[:,[3,4,6]])
            return navpts
                
    def _interp_points(self, tstamp, pt1, pt2):
        """
        Performs an interpolation for the points given and returns the
        interpolated points.  The first field of each point array is assumed to
        be the time stamp, and all other values in the array are interpolated.
        """
        delta = pt2 - pt1
        result = pt1 + (tstamp - pt1[0]) * delta / delta[0]
        return result
            
    def build_navarray(self):
        """
        The objective is to do the work of building an array of the navigation
        data to speed up processing later.  It is stored in a dictionary of
        arrays for each navigation datagram.  Position information is in arrays
        ordered as time, latitude, longitude.  Attitude information is in
        arrays ordered as time, roll, pitch, heave, heading.
        """
        self.navarray = {}
        if not self.mapped:
            self.mapfile()
        if self.map.packdir.has_key('80'):
            print 'creating position array'
            numpos = len(self.map.packdir['80'])
            self.navarray['80'] = np.zeros((numpos,3))
            for i in range(numpos):
                self.getrecord(80, i)
                self.navarray['80'][i,0] = self.packet.time
                self.navarray['80'][i,1] = self.packet.subpack.header[2]
                self.navarray['80'][i,2] = self.packet.subpack.header[3]
        if self.map.packdir.has_key('65'):
            print 'creating attitude array (65)'
            time = []
            roll = []
            pitch = []
            heave = []
            heading = []
            numatt = len(self.map.packdir['65'])
            for i in range(numatt):
                self.getrecord(65, i)
                time += list(self.packet.subpack.data['Time'])
                roll += list(self.packet.subpack.data['Roll'])
                pitch += list(self.packet.subpack.data['Pitch'])
                heave += list(self.packet.subpack.data['Heave'])
                heading += list(self.packet.subpack.data['Heading'])
            self.navarray['65'] = np.asarray(zip(time,roll,pitch,heave,heading))
        if self.map.packdir.has_key('110'):
            print 'creating attitude array (110)'
            time = []
            roll = []
            pitch = []
            heave = []
            heading = []
            numatt = len(self.map.packdir['110'])
            for i in range(numatt):
                self.getrecord(110, i)
                time += list(self.packet.subpack.data['Time'])
                roll += list(self.packet.subpack.data['Roll'])
                pitch += list(self.packet.subpack.data['Pitch'])
                heave += list(self.packet.subpack.data['Heave'])
                heading += list(self.packet.subpack.data['Heading'])
            self.navarray['110'] = np.asarray(zip(time,roll,pitch,heave,heading))
            
class Datagram:
    """
    The datagram holder.  Reads the header section of the provided memory
    block and holds a list with the datagram information through the time
    stamp.  Also, the datagram type is stored in variable 'dtype'.  Flags
    are set to indicate whether the rest of the datagram has been decoded,
    and the decoded data is stored in a datagram specific object called
    'subpack'. The maketime method is called upon decoding the record, and
    a 'time' variable is created containing a POSIX time with the packet
    time. 'valid' indicates whether the sync pattern is present, 'decoded'
    indicated if the datagram has been decoded, and 'checksum' contains the
    checksum field.
    Note: While not required of these datagrams, the size of the datagram, as
    if coming from a file, is expected at the beginning of these datablocks.
    """
    
    hdr_dtype = np.dtype([('Bytes','I'),('Start','B'),('Type','B'),
        ('Model','H'),('Date','I'),('Time','I')])
    
    def __init__(self, fileblock, byteswap = False):
        """Reads the header section, which is the first 16 bytes, of the
        given memory block."""
        self.byteswap = byteswap
        hdr_sz = Datagram.hdr_dtype.itemsize
        self.header = np.frombuffer(fileblock[:hdr_sz], dtype = Datagram.hdr_dtype)
        if byteswap:
            self.header = self.header.byteswap()
        self.header = self.header[0]
        self.decoded = False
        if self.header[1] == 2:
            self.valid = True
        else:
            self.valid = False
        self.datablock = fileblock[hdr_sz:-3]
        etx = np.frombuffer(fileblock[-3:-2], dtype=np.uint8, count=1)[0]
        if etx != 3:
            self.valid = False
        if byteswap:
            self.checksum = np.frombuffer(fileblock[-2:], dtype=np.uint16, count=1)[0].newbyteorder()
        else:
            self.checksum = np.frombuffer(fileblock[-2:], dtype=np.uint16, count=1)[0]
        self.dtype = self.header[2]
        try:
            self.maketime()
        except ValueError:
            pass
        
    def decode(self):
        """
        Directs to the correct decoder.
        """
        if self.dtype == 49:
            self.subpack = Data49(self.datablock, self.byteswap)
        elif self.dtype == 65:
            self.subpack = Data65(self.datablock, self.time, self.byteswap)
        elif self.dtype == 67:
            self.subpack = Data67(self.datablock, self.byteswap)
        elif self.dtype == 68:
            self.subpack = Data68(self.datablock, self.byteswap)
        elif self.dtype == 71:
            self.subpack = Data71(self.datablock, self.time, self.byteswap)
        elif self.dtype == 73:
            self.subpack = Data73(self.datablock, self.byteswap)
        elif self.dtype == 78:
            self.subpack = Data78(self.datablock, self.byteswap)
        elif self.dtype == 79:
            self.subpack = Data79(self.datablock, self.byteswap)
        elif self.dtype == 80:
            self.subpack = Data80(self.datablock, self.byteswap)
        elif self.dtype == 82:
            self.subpack = Data82(self.datablock, self.byteswap)
        elif self.dtype == 83:
            self.subpack = Data83(self.datablock, self.byteswap)
        elif self.dtype == 85:
            self.subpack = Data85(self.datablock, self.byteswap)
        elif self.dtype == 88:
            self.subpack = Data88(self.datablock, self.byteswap)
        elif self.dtype == 89:
            self.subpack = Data89(self.datablock, self.byteswap)
        elif self.dtype == 102:
            self.subpack = Data102(self.datablock, self.byteswap)
        elif self.dtype == 105:
            #same definition for this data type
            self.subpack = Data73(self.datablock, self.byteswap)
        elif self.dtype == 107:
            self.subpack = Data107(self.datablock, self.byteswap)
        elif self.dtype == 109:
            self.subpack = Data109(self.datablock, self.byteswap)
        elif self.dtype == 110:
            self.subpack = Data110(self.datablock, self.time, self.byteswap)
        else:
            print "Data record " + str(self.dtype) + " decoding is not yet supported."
        self.decoded = True

    def maketime(self):
        """
        Makes the time stamp of the current packet as a POSIX time stamp.
        UTC is assumed.
        """
        date = str(self.header[-2])
        year = int(date[:4])
        month = int(date[4:6])
        day = int(date[6:])
        numdays = dtm.date(year, month, day).toordinal() - dtm.date(1970,1,1).toordinal()
        dayseconds = self.header[-1] * 0.001
        self.time = numdays * 24 * 60 * 60 + dayseconds
        
    def gettime(self):
        """
        Calls the method "maketime" if needed and returns the POSIX time stamp.
        """
        if not self.__dict__.has_key('time'):
            self.maketime()
        return self.time
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
            

class Data49:
    """
    PU Status datagram 0x31 / '1' / 49.
    """
    
    hdr_dtype = np.dtype([('StatusDatagramCount','H'),('SystemSerialNum','H'),
        ('PingRate',"f"),('PingCounter','H'),('SwathDistance','B'),
        ('SensorInputStatusUDP2','I'),('SensorInputStatusSerial1','I'),
        ('SensorInputStatusSerial2','I'),('SensorInputStatusSerial3','I'),
        ('SensorInputStatusSerial4','I'),('PPSstatus','b'),
        ('PositionStatus','b'),('AttitudeStatus','b'),('ClockStatus','b'),
        ('HeadingStatus','b'),('PUstatus','B'),('LastHeading',"f"),
        ('LastRoll',"f"),('LastPitch',"f"),('LastSonarHeave',"f"),
        ('TransducerSoundSpeed',"f"),('LastDepth',"f"),('ShipVelocity',"f"),
        ('AttitudeVelocityStatus','B'),('MammalProtectionRamp','B'),
        ('BackscatterOblique','b'),('BackscatterNormal','b'),('FixedGain','b'),
        ('DepthNormalIncidence','B'),('RangeNormalIncidence','H'),
        ('PortCoverage','B'),('StarboardCoverage','B'),
        ('TransducerSoundSpeedFromProfile',"f"),('YawStabAngle',"f"),
        ('PortCoverageORAbeamVelocity','h'),
        ('StarboardCoverageORDownVelocity','h'),('EM2040CPUTemp','b')])
        
    def __init__(self, datablock, byteswap = False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        
        hdr_dtype = np.dtype([('StatusDatagramCount','H'),('SystemSerialNum','H'),
            ('PingRate',"H"),('PingCounter','H'),('SwathDistance','B'),
            ('SensorInputStatusUDP2','I'),('SensorInputStatusSerial1','I'),
            ('SensorInputStatusSerial2','I'),('SensorInputStatusSerial3','I'),
            ('SensorInputStatusSerial4','I'),('PPSstatus','b'),
            ('PositionStatus','b'),('AttitudeStatus','b'),('ClockStatus','b'),
            ('HeadingStatus','b'),('PUstatus','B'),('LastHeading',"H"),
            ('LastRoll',"h"),('LastPitch',"h"),('LastSonarHeave',"h"),
            ('TransducerSoundSpeed',"H"),('LastDepth',"I"),('ShipVelocity',"h"),
            ('AttitudeVelocityStatus','B'),('MammalProtectionRamp','B'),
            ('BackscatterOblique','b'),('BackscatterNormal','b'),('FixedGain','b'),
            ('DepthNormalIncidence','B'),('RangeNormalIncidence','H'),
            ('PortCoverage','B'),('StarboardCoverage','B'),
            ('TransducerSoundSpeedFromProfile',"H"),('YawStabAngle',"h"),
            ('PortCoverageORAbeamVelocity','h'),
            ('StarboardCoverageORDownVelocity','h'),('EM2040CPUTemp','b')])
        hdr_sz = hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype=hdr_dtype)[0]
        print '*Warning: This datagram is not currently decoded correctly!*'
        print hdr_sz,len(datablock)
        # self.header = self.header.astype(Data49.hdr_dtype)
        # self.header['PingRate'] *= 0.01
        # self.header['LastHeading'] *= 0.01
        # self.header['LastRoll'] *= 0.01
        # self.header['LastPitch'] *= 0.01
        # self.header['LastSonarHeave'] *= 0.01
        # self.header['TransducerSoundSpeed'] *= 0.1
        # self.header['LastDepth'] *= 0.01
        # self.header['ShipVelocity'] *= 0.01
        # self.header['TransducerSoundSpeedFromProfile'] *= 0.01
        # self.header['YawStabAngle'] *= 0.01
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
        
        
class Data65:
    """
    Attitude datagram 0x41/'A'/65. Data can be found in the array 'data' and
    is stored as time (POSIX), roll(deg), pitch(deg), heave(m), 
    heading(deg).  sensor_descriptor does not appear to parse correctly... 
    Perhaps it is not included in the header size so it is not sent to this
    object in the datablock?
    """
    
    hdr_dtype = np.dtype([('Counter','H'),('Seriel#','H'),('NumEntries','H')])
    att_dtype = np.dtype([('Time','d'),('Status','H'),('Roll','f'),('Pitch','f'),
        ('Heave','f'),('Heading','f')])
        
    def __init__(self, datablock, POSIXtime, byteswap = False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        self.time = POSIXtime
        hdr_sz = Data65.hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype=Data65.hdr_dtype)[0]
        self.sensor_descriptor = np.frombuffer(datablock[-1:], dtype=np.uint8)[0]
        self.read(datablock[hdr_sz:])
        
    def read(self, datablock):
        """
        Reads the data section of the record.  Time is in POSIX time,
        angles are in degrees, distances in meters.
        """
        att_file_dtype = np.dtype([('Time','H'),('Status','H'),('Roll','h'),('Pitch','h'),
            ('Heave','h'),('Heading','H')])
        self.data = np.frombuffer(datablock[:-1], dtype=att_file_dtype)
        self.data = self.data.astype(Data65.att_dtype)
        self.data['Time'] = self.data['Time'] * 0.001 + self.time
        self.data['Roll'] *= 0.01
        self.data['Pitch'] *= 0.01
        self.data['Heave'] *= 0.01
        self.data['Heading'] *= 0.01
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
        print 'Sensor Descriptor : ' + str(self.sensor_descriptor)

     
class Data67:
    """
    Clock datagram 043h / 67d / 'C'. Date is YYYYMMDD. Time is in miliseconds
    since midnight.
    """
    hdr_dtype = np.dtype([('ClockCounter','H'),('SystemSerial#','H'),
        ('Date','I'),('Time','I'),('1PPS','B')])
    def __init__(self,datablock, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_sz = Data67.hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], 
            dtype = Data67.hdr_dtype)[0]
        if len(datablock) > hdr_sz:
            print len(datablock), hdr_sz
            
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
        
        
class Data68:
    """
    XYZ datagram 044h / 68d / 'D'. All values are converted to meters, degrees,
    or whole units.  The header sample rate may not be correct, but is 
    multiplied by 4 to make the one way travel time per beam appear correct. The
    detection window length per beam is in its raw form...
    """
    hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
        ('VesselHeading',"f"),('SoundSpeed',"f"),('TransducerDepth',"f"),
        ('MaximumBeams','B'),('ValidBeams','B'),('Zresolution',"f"),
        ('XYresolution',"f"),('SampleRate','f')])
    xyz_dtype = np.dtype([('Depth',"f"),('AcrossTrack',"f"),('AlongTrack',"f"),
        ('BeamDepressionAngle',"f"),('BeamAzimuthAngle',"f"),
        ('OneWayRange',"f"),('QualityFactor','B'),
        ('DetectionWindowLength',"f"),('Reflectivity',"f"),('BeamNumber','B')])
        
    def __init__(self,datablock, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
            ('VesselHeading',"H"),('SoundSpeed',"H"),('TransducerDepth',"H"),
            ('MaximumBeams','B'),('ValidBeams','B'),('Zresolution',"B"),
            ('XYresolution',"B"),('SampleRate','H')])
        hdr_sz = hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = hdr_dtype)[0]
        self.header = self.header.astype(Data68.hdr_dtype)
        self.header[2] *= 0.01
        self.header[3] *= 0.1
        self.header[4] *= 0.01
        self.header[7] *= 0.01
        self.header[8] *= 0.01
        self.header[-1] *= 4    # revisit this number... it makes the range work but may not be correct
        self.depthoffsetmultiplier = np.frombuffer(datablock[-1:], dtype = 'b')[0] * 65536
        self.header[4] += self.depthoffsetmultiplier
        self.read(datablock[hdr_sz:-1])
    
    def read(self, datablock):
        """
        Decodes the repeating data section, and shifts all values into meters,
        degrees, or whole units.
        """
        xyz_dtype = np.dtype([('Depth',"h"),('AcrossTrack',"h"),('AlongTrack',"h"),
            ('BeamDepressionAngle',"h"),('BeamAzimuthAngle',"H"),
            ('OneWayRange',"H"),('QualityFactor','B'),
            ('DetectionWindowLength',"B"),('Reflectivity',"b"),('BeamNumber','B')])       
        self.data = np.frombuffer(datablock, dtype = xyz_dtype)
        self.data = self.data.astype(Data68.xyz_dtype)
        self.data['Depth'] *= self.header['Zresolution']
        self.data['AcrossTrack'] *= self.header['XYresolution']
        self.data['AlongTrack'] *= self.header['XYresolution']
        self.data['BeamDepressionAngle'] *= 0.01
        self.data['BeamAzimuthAngle'] *= 0.01
        self.data['OneWayRange'] /= self.header['SampleRate']
        #self.data['DetectionWindowLength'] *= 4    # not sure what this is for or what it means
        self.data['Reflectivity'] *= 0.5
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
        print 'TransducerDepthOffsetMultiplier : ' + str(self.depthoffsetmultiplier)
            
    
class Data71:
    """
    Surface Sound Speed datagram 047h / 71d / 'G'.  Time is in POSIX time and
    sound speed is in meters per second.
    """
    hdr_dtype = np.dtype([('SoundSpeedCounter','H'),('SystemSerial#','H'),
        ('NumEntries','H')])
    data_dtype = np.dtype([('Time','d'),('SoundSpeed','f')])
    
    def __init__(self, datablock, POSIXtime, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        data_dtype = np.dtype([('Time','H'),('SoundSpeed','H')])
        hdr_sz = Data71.hdr_dtype.itemsize
        data_sz = data_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], 
            dtype = Data71.hdr_dtype)[0]
        self.data = np.frombuffer(datablock[hdr_sz:-1], dtype = data_dtype)
        self.data = self.data.astype(Data71.data_dtype)
        self.data['Time'] += POSIXtime
        self.data['SoundSpeed'] *= 0.1
            
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
        
        
class Data73:
    """
    Installation parameters datagram 049h (start) / 73d / 'I', 069h(stop)/ 105d
    / 'I' or 70h(remote) / 112d / 'r'.  There is a short header section and the
    remainder of the record is ascii, comma delimited.
    """
    hdr_dtype = np.dtype([('SurveyLine#','H'),('Serial#','H'),('Serial#2','H')])
    
    def __init__(self, datablock, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_sz = Data73.hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz],
            dtype = Data73.hdr_dtype)[0]
        temp = datablock[hdr_sz:].split(',')
        self.settings = {}
        for entry in temp:
            data = entry.split('=')
            if len(data) == 2:
                self.settings[entry[:3]] = data[1]
                
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
        keys = self.settings.keys()
        keys.sort()
        for key in keys:
            print key + ' : ' + str(self.settings[key])
    
    
class Data78:
    """
    Raw range and angle datagram, aka 'N'/'4eh'/78d.  All data is contained
    in the header, rx, and tx arrays. the rx and tx arrays are ordered as in
    the data defintion document, but have been converted to degrees, dB,
    meters, etc.
    """
    
    hdr_dtype = np.dtype([('Counter','H'),('Serial#','H'),('SoundSpeed','f'),
        ('Ntx','H'),('Nrx','H'),('Nvalid','H'),('SampleRate','f'),('Dscale','I')])
    ntx_dtype = np.dtype([('TiltAngle','f'),('Focusing','f'),('Pulse','f'),('Delay','f'),
        ('Frequency','f'),('AbsorptionCoef','f'),('WaveformID','B'),
        ('TransmitSector#','B'),('Bandwidth','f')])
    nrx_dtype = np.dtype([('BeamPointingAngle','f'),('TransmitSectorID','B'),('DetectionInfo','B'),
        ('WindowLength','H'),('QualityFactor','B'),('Dcorr','b'),('TravelTime','f'),
        ('Reflectivity','f'),('CleaningInfo','b'),('Spare','B')])
    
    def __init__(self, datablock, byteswap = False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        hdr_dtype = np.dtype([('Counter','H'),('Serial#','H'),('SoundSpeed','H'),
            ('Ntx','H'),('Nrx','H'),('Nvalid','H'),('SampleRate','f'),('Dscale','I')])
        hdr_sz = hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype=hdr_dtype)[0]
        self.header = self.header.astype(Data78.hdr_dtype)
        self.header[2] *= 0.1  # sound speed to convert to meters/second
        self.read(datablock[hdr_sz:])

    def read(self, datablock):
        """Decodes the repeating parts of the record."""
        ntx_file_dtype = np.dtype([('TiltAngle','h'),('Focusing','H'),('Pulse','f'),('Delay','f'),
            ('Frequency','f'),('AbsorptionCoef','H'),('WaveformID','B'),
            ('TransmitSector#','B'),('Bandwidth','f')])
        ntx_file_sz = ntx_file_dtype.itemsize
        nrx_file_dtype = np.dtype([('BeamPointingAngle','h'),('TransmitSectorID','B'),('DetectionInfo','B'),
            ('WindowLength','H'),('QualityFactor','B'),('Dcorr','b'),('TravelTime','f'),
            ('Reflectivity','h'),('CleaningInfo','b'),('Spare','B')])
        nrx_file_sz = nrx_file_dtype.itemsize
        ntx = self.header[3]
        nrx = self.header[4]
        self.tx = np.frombuffer(datablock[:ntx*ntx_file_sz], dtype = ntx_file_dtype)
        self.tx = self.tx.astype(Data78.ntx_dtype)
        self.tx['TiltAngle'] *= 0.01  # convert to degrees
        self.tx['Focusing'] *= 0.1   # convert to meters
        self.tx['AbsorptionCoef'] *= 0.01  # convert to dB/km
        self.rx = np.frombuffer(datablock[ntx*ntx_file_sz:-1], dtype = nrx_file_dtype)
        self.rx = self.rx.astype(Data78.nrx_dtype)
        self.rx['BeamPointingAngle'] *= 0.01  # convert to degrees
        self.rx['Reflectivity'] *= 0.1   # convert to dB
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
        
    
class Data79:
    """
    Quality factor datagram 4fh / 79d / 'O'.
    """
    hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
        ('Nrx','H'),('Npar','H')]) # The data format has a Spare Byte here...
    qf_dtype = np.dtype([('QualityFactor','f4')])
    
    def __init__(self, datablock, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_sz = Data79.hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = Data79.hdr_dtype)[0]
        if self.header['Npar'] > 1:
            print "Warning: Datagram has expanded and may not parse correctly."
        self.read(datablock[hdr_sz:-1])
            
    def read(self, datablock):
        """
        Reads the Quality Factor Datagram.
        """
        if self.header['Npar'] == 1:
            self.data = np.frombuffer(datablock, dtype = Data79.qf_dtype)
        else:
            print "Only parsing original IFREMER quality factor"
            step = 4 * self.header['Nrx'] * self.header['Npar']
            self.data = np.zeros(self.header['Nrx'], dtype = Data79.qf_dtype)
            for n in range(self.header['Nrx']):
                self.data = np.frombuffer(datablock[n*step:n*step+4],
                    dtype = Data79.qf_dtype)
                    
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
    
    
class Data80:
    """
    Position datagram, 0x50 / 'P' / 80. Available data is in the header
    list, and all data has been converted to degrees or meters.
    """
    
    hdr_dtype = np.dtype([('Counter','H'),('Serial#','H'),('Latitude','d'),
        ('Longitude','d'),('Quality','f'),('Speed','f'),('Course','f'),
        ('Heading','f'),('System','B'),('NumberInputBytes','B')])
    
    def __init__(self, datablock, byteswap = False):
        """Catches the binary datablock and decodes the record."""
        hdr_dtype = np.dtype([('Counter','H'),('Serial#','H'),('Latitude','i'),
            ('Longitude','i'),('Quality','H'),('Speed','H'),('Course','H'),
            ('Heading','H'),('System','B'),('NumberInputBytes','B')])
        hdr_sz = hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = hdr_dtype)[0]
        # read the original datagram, of which the size is the last part of the header.
        self.origdata = datablock[hdr_sz:hdr_sz+self.header[-1]]
        self.header = self.header.astype(Data80.hdr_dtype)
        self.header[2] /= 20000000.  # convert to degrees
        self.header[3] /= 10000000.  # convert to degrees
        self.header[4] *= 0.01       # convert to meters
        self.header[5] *= 0.01       # convert to meters/second
        self.header[6] *= 0.01       # convert to degrees
        self.header[7] *= 0.01       # convert to degrees
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
        
        
class Data82:
    """
    Runtime parameters datagram, 0x52 / 'R' / 82.
    """
    
    hdr_dtype = np.dtype([('Counter','H'),('SystemSerial#','H'),
        ('OperatorStationStatus','B'),('ProcessingUnitStatus','B'),
        ('BSPStatus','B'),('SonarHeadOrTransceiverStatus','B'),
        ('Mode','B'),('FilterID','B'),('MinDepth','H'),('MaxDepth','H'),
        ('AbsorptionCoefficent','H'),('TransmitPulseLength','H'),
        ('TransmitBeamWidth','H'),('TransmitPower','b'),
        ('ReceiveBeamWidth','B'),('ReceiveBeamWidth50Hz','B'),
        ('ReceiverFixedGain','B'),('TVGlawCrossoverAngle','B'),
        ('SourceOfSoundSpeed','B'),('MaxPortSwathWidth','H'),
        ('BeamSpacing','B'),('MaxPortCoverage','B'),
        ('YawAndPitchStabilization','B'),('MaxStarboardCoverage','B'),
        ('MaxStarboardSwathWidth','H'),('TransmitAlongTilt','h'),
        ('HiLoFrequencyAbsorptionCoeffRatio','B')])
    
    def __init__(self, datablock, byteswap = False):
        """Catches the binary datablock and decodes the record."""
        hdr_sz = Data82.hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = Data82.hdr_dtype)[0]
        
    def print_byte(self, field_number):
        """
        Prints the given 1 bite field in a binary form.
        """
        if type(self.header[field_number]) == np.uint8:
            print np.binary_repr(self.header[field_number], width = 8)
            
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        bitfields = np.array([2,3,4,5,6,7,18,20,22,26])
        for n,name in enumerate(self.header.dtype.names):
            if np.any(bitfields == n):
                print name + ' : ' + np.binary_repr(self.header[n], width = 8)
            else:
                print name + ' : ' + str(self.header[n])
                
                
class Data83:
    """
    Seabed Imagary datagram 053h / 83d / 'Seabed image data'.  All data is
    converted into whole units of degrees, meters, dB, etc, except Oblique
    Backscatter and Normal Backscatter which are in their raw form.
    """
    hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
        ('MeanAbsorption',"f"),('PulseLength',"f"),('RangeToNormal','H'),
        ('StartRangeSampleOfTVG','H'),('StopRangeSampleOfTVG','H'),
        ('NormalIncidenceBS',"f"),('ObliqueBS',"f"),('TxBeamwidth',"f"),
        ('TVGLawCrossoverAngle',"f"),('NumberValidBeams','B')])
    beaminfo_dtype = np.dtype([('BeamIndexNumber','B'),('SortingDirection','b'),
        ('#SamplesPerBeam','H'),('CenterSample#','H')])
    
    def __init__(self, datablock, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
            ('MeanAbsorption',"H"),('PulseLength',"H"),('RangeToNormal','H'),
            ('StartRangeSampleOfTVG','H'),('StopRangeSampleOfTVG','H'),
            ('NormalIncidenceBS',"b"),('ObliqueBS',"b"),('TxBeamwidth',"H"),
            ('TVGLawCrossoverAngle',"B"),('NumberValidBeams','B')])
        hdr_sz = hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = hdr_dtype)[0]
        self.header = self.header.astype(Data83.hdr_dtype)
        self.header[2] *= 0.01
        self.header[3] *= 10**-6
        self.header[7] *= 1  # check this
        self.header[8] *= 1  # check this
        self.header[9] *= 0.1  
        self.header[10] *= 0.1
        numbeams = self.header[-1]
        self._read(datablock[hdr_sz:], numbeams)
    
    def _read(self, datablock, numbeams):
        """
        Reads the data section of the record.
        """
        beaminfo_sz = Data89.beaminfo_dtype.itemsize
        samples_dtype = np.dtype([('Amplitude',"b")])    
        samples_sz = samples_dtype.itemsize
        p = beaminfo_sz*numbeams
        self.beaminfo = np.frombuffer(datablock[:p],
            dtype = Data89.beaminfo_dtype)
        maxsamples = self.beaminfo['#SamplesPerBeam'].max()
        self.samples = np.zeros((numbeams,maxsamples), dtype = 'float')
        for n in range(numbeams):
            numsamples = self.beaminfo[n]['#SamplesPerBeam']
            temp = np.frombuffer(datablock[p:p+numsamples*samples_sz],
                dtype = samples_dtype)
            p += numsamples*samples_sz
            #startsample = self.beaminfo[n]['CenterSample#']
            self.samples[n,:numsamples] = temp.astype('float')[:]
        self.samples *= 0.5  # check this

        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])

            
class Data85:
    """
    Sound Speed datagram 055h / 85d / 'U'. Time is in POSIX, depth
    is in meters, sound speed is in meters per second.
    """
    hdr_dtype = np.dtype([('ProfileCounter','H'),('SystemSerial#','H'),
        ('Date','I'),('Time',"d"),('NumEntries','H'),('DepthResolution','H')])
    data_dtype = np.dtype([('Depth','d'),('SoundSpeed','f')])
    
    def __init__(self, datablock, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_dtype = np.dtype([('ProfileCounter','H'),('SystemSerial#','H'),
            ('Date','I'),('Time',"I"),('NumEntries','H'),
            ('DepthResolution','H')])
        hdr_sz = hdr_dtype.itemsize
        data_dtype = np.dtype([('Depth','I'),('SoundSpeed','I')])
        data_sz = data_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], 
            dtype = hdr_dtype)[0]
        self.header = self.header.astype(Data85.hdr_dtype)
        self.header['Time'] = self.maketime(self.header['Date'], self.header['Time'])
        depth_resolution = self.header['DepthResolution'] * 0.01
        self.data = np.frombuffer(datablock[hdr_sz:-1], dtype = data_dtype)
        self.data = self.data.astype(Data85.data_dtype)
        self.data['Depth'] *= depth_resolution
        self.data['SoundSpeed'] *= 0.1
        
    def maketime(self, date, time):
        """
        Makes the time stamp of the current packet as a POSIX time stamp.
        UTC is assumed.
        """
        date = str(date)
        year = int(date[:4])
        month = int(date[4:6])
        day = int(date[6:])
        numdays = dtm.date(year, month, day).toordinal() - dtm.date(1970,1,1).toordinal()
        dayseconds = time * 0.001
        return numdays * 24 * 60 * 60 + dayseconds
        
    def plot(self):
        """
        Creates a simple plot of the cast.
        """
        plt.figure()
        plt.plot(self.data['SoundSpeed'],self.data['Depth'])
        plt.ylim((self.data['Depth'].max(), self.data['Depth'].min()))
        plt.xlabel('Sound Speed (m/s)')
        plt.ylabel('Depth (m)')
        plt.title('Cast at POSIX time ' + str(self.header['Time']))
        plt.draw()
            
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
        
         
class Data88:
    """
    XYZ datagram, 0x58 / 'X' / 88.  All data is in the header list or
    stored in the 'data' array.  Values have been converted to degrees and
    dB.
    """
    
    hdr_dtype = np.dtype([('Counter','H'),('Serial#','H'),('Heading','f'),
        ('SoundSpeed','f'),('TransmitDepth','f'),('NumBeams','H'),
        ('NumValid','H'),('SampleFrequency','f'),('Spare','i')])
    xyz_dtype = np.dtype([('Depth','f'),('AcrossTrack','f'),('AlongTrack','f'),
        ('WindowLength','H'),('QualityFactor','B'),('IncidenceAngleAdjustment','f'),
        ('Detection','B'),('Cleaning','b'),('Reflectivity','f')])
    
    def __init__(self, datablock, byteswap = False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        hdr_file_dtype = np.dtype([('Counter','H'),('Serial#','H'),('Heading','H'),
            ('SoundSpeed','H'),('TransmitDepth','f'),('NumBeams','H'),
            ('NumValid','H'),('SampleFrequency','f'),('Spare','i')])
        hdr_sz = hdr_file_dtype.itemsize
        header = np.frombuffer(datablock[:hdr_sz], dtype = hdr_file_dtype)[0]
        self.header = header.astype(Data88.hdr_dtype)
        self.header['Heading'] *= 0.01  # convert to degrees
        self.header['SoundSpeed'] *= 0.1   # convert to m/s
        self.read(datablock[hdr_sz:])
        
    def read(self, datablock):
        """
        Reads the data section of the record.
        """
        xyz_file_dtype = np.dtype([('Depth','f'),('AcrossTrack','f'),('AlongTrack','f'),
            ('WindowLength','H'),('QualityFactor','B'),('IncidenceAngleAdjustment','b'),
            ('Detection','B'),('Cleaning','b'),('Reflectivity','h')])
        xyz_sz = xyz_file_dtype.itemsize
        #buffer length goes to -1 because of the uint8 buffer before etx
        self.data = np.frombuffer(datablock[:-1], dtype = xyz_file_dtype)
        self.data = self.data.astype(Data88.xyz_dtype)
        self.data['IncidenceAngleAdjustment'] *= 0.1  # convert to degrees
        self.data['Reflectivity'] *= 0.1 # convert to dB

    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
            
            
class Data89:
    """
    Seabed Image datagram 059h / 89d / 'Y'.
    """
    
    hdr_dtype = np.dtype([('PingCount','H'),('SystemSerial#','H'),
        ('SamplingFreq','f'),('RangeToNormal','H'),('NormalBackscatter',"f"),
        ('ObliqueBackscatter',"f"),('TXBeamWidth',"f"),('TVGCrossover',"f"),
        ('NumberValidBeams','H')])
    beaminfo_dtype = np.dtype([('SortingDirection','b'),('DetectionInfo','B'),
        ('#SamplesPerBeam','H'),('CenterSample#','H')])
    
    def __init__(self, datablock, byteswap = False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        hdr_dtype = np.dtype([('PingCount','H'),('SystemSerial#','H'),
            ('SamplingFreq','f'),('RangeToNormal','H'),('NormalBackscatter',"h"),
            ('ObliqueBackscatter',"h"),('TXBeamWidth',"H"),('TVGCrossover',"H"),
            ('NumberValidBeams','H')])
        hdr_sz = hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = hdr_dtype)[0]
        self.header = self.header.astype(Data89.hdr_dtype)
        self.header['NormalBackscatter'] *= 0.1
        self.header['ObliqueBackscatter'] *= 0.1
        self.header['TXBeamWidth'] *= 0.1
        self.header['TVGCrossover'] *= 0.1
        numbeams = self.header[-1]
        self._read(datablock[hdr_sz:], numbeams)
    
    def _read(self, datablock, numbeams):
        """
        Reads the data section of the record.
        """
        beaminfo_sz = Data89.beaminfo_dtype.itemsize
        samples_dtype = np.dtype([('Amplitude',"h")])    
        samples_sz = samples_dtype.itemsize
        p = beaminfo_sz*numbeams
        self.beaminfo = np.frombuffer(datablock[:p],
            dtype = Data89.beaminfo_dtype)
        maxsamples = self.beaminfo['#SamplesPerBeam'].max()
        self.samples = np.zeros((numbeams,maxsamples), dtype = 'float')
        for n in range(numbeams):
            numsamples = self.beaminfo[n]['#SamplesPerBeam']
            temp = np.frombuffer(datablock[p:p+numsamples*samples_sz],
                dtype = samples_dtype)
            p += numsamples*samples_sz
            #startsample = self.beaminfo[n]['CenterSample#']
            self.samples[n,:numsamples] = temp.astype('float')[:]
        self.samples *= 0.1
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
            
            
class Data102:
    """
    Range and angle datagram, 66h / 102 / 'f'.  All values are converted to
    whole units, meaning meters, seconds, degrees, Hz, etc.
    """
    hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
        ('Ntx','H'),('Nrx','H'),('SamplingFrequency',"f"),('Depth',"f"),
        ('SoundSpeed',"f"),('MaximumBeams','H'),('Spare1','H'),('Spare2','H')])
    ntx_dtype = np.dtype([('TiltAngle',"f"),('FocusRange',"f"),
        ('SignalLength',"f"),('Delay',"f"),
        ('CenterFrequency','I'),('Bandwidth',"I"),('SignalWaveformID','B'),
        ('TransmitSector#','B')])
    nrx_dtype = np.dtype([('BeamPointingAngle',"f"),('Range',"f"),
        ('TransmitSectorID','B'),('Reflectivity',"f"),('QualityFactor','B'),
        ('DetectionWindowLength','B'),('BeamNumber','h'),('Spare','H')])
   
    def __init__(self, datablock, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
            ('Ntx','H'),('Nrx','H'),('SamplingFrequency',"I"),('Depth',"i"),
            ('SoundSpeed',"H"),('MaximumBeams','H'),('Spare1','H'),
            ('Spare2','H')])
        hdr_sz = hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = hdr_dtype)[0]
        self.header = self.header.astype(Data102.hdr_dtype)
        self.header['SoundSpeed'] *= 0.1
        self.header['SamplingFrequency'] *= 0.01
        self.header['Depth'] *= 0.01
        self.read(datablock[hdr_sz:-1])

    def read(self, datablock):
        """
        Reads the data section of the record and converts values to whole
        units.
        """
        # declare ntx stuff
        ntx_dtype = np.dtype([('TiltAngle',"h"),('FocusRange',"H"),
            ('SignalLength',"I"),('Delay',"I"),
            ('CenterFrequency','I'),('Bandwidth',"H"),('SignalWaveformID','B'),
            ('TransmitSector#','B')])
        ntx_sz = ntx_dtype.itemsize
        ntx = self.header['Ntx']
        # declare nrx stuff
        nrx_dtype = np.dtype([('BeamPointingAngle',"h"),('Range',"H"),
            ('TransmitSectorID','B'),('Reflectivity',"b"),('QualityFactor','B'),
            ('DetectionWindowLength','B'),('BeamNumber','h'),('Spare','H')])
        nrx_sz = nrx_dtype.itemsize
        nrx = self.header['Nrx']
        # read ntx
        self.tx = np.frombuffer(datablock[:ntx * ntx_sz], 
            dtype = ntx_dtype)
        self.tx = self.tx.astype(Data102.ntx_dtype)
        self.tx['TiltAngle'] *= 0.01
        self.tx['FocusRange'] *= 0.1
        self.tx['SignalLength'] *= 10**-6
        self.tx['Delay'] *= 10**-6
        self.tx['Bandwidth'] *= 10
        # read nrx
        self.rx = np.frombuffer(datablock[ntx * ntx_sz:], dtype = nrx_dtype)
        self.rx = self.rx.astype(Data102.nrx_dtype)
        self.rx['BeamPointingAngle'] *= 0.01
        self.rx['Range'] *= 0.25
        self.rx['Reflectivity'] *= 0.5
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
        
            
class Data107:
    """
    The water column datagram, 6Bh / 107d / 'k'.  The receiver beams are roll
    stablized.  Units have been shifted to whole units as in hertz, meters, 
    seconds, etc.
    """
    hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
        ('#OfDatagrams','H'),('Datagram#','H'),('#TxSectors','H'),
        ('Total#Beams','H'),('NumberBeamsInDatagram','H'),('SoundSpeed',"f"),
        ('SamplingFrequency',"d"),('TxHeave',"f"),('TVGfunction','B'),
        ('TVGoffset','b'),('ScanningInfo','B'),('Spare','3B')])
    ntx_dtype = np.dtype([('TiltTx',"f"),('CenterFrequency',"I"),
        ('TransmitSector#','B'),('Spare','B')])
    nrx_dtype = np.dtype([('BeamPointingAngle',"h"),('StartRangeSample#','H'),
        ('NumberSamples','H'),('DetectedRange','H'),('TransmitSector#','B'),
        ('Beam#','B')])
        
    def __init__(self, datablock, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
            ('#OfDatagrams','H'),('Datagram#','H'),('#TxSectors','H'),
            ('Total#Beams','H'),('NumberBeamsInDatagram','H'),('SoundSpeed',"H"),
            ('SamplingFrequency',"I"),('TxHeave',"h"),('TVGfunction','B'),
            ('TVGoffset','b'),('ScanningInfo','B'),('Spare','3B')])
        hdr_sz = hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = hdr_dtype)[0]
        self.header = self.header.astype(Data107.hdr_dtype)
        self.header['SoundSpeed'] *= 0.1
        self.header['SamplingFrequency'] *= 0.01
        self.header['TxHeave'] *= 0.01
        self.read(datablock[hdr_sz:])
        
    def read(self, datablock):
        """
        Reads the varable section of the datagram.
        """
        # declare tx stuff
        ntx_dtype = np.dtype([('TiltTx',"h"),('CenterFrequency',"H"),
            ('TransmitSector#','B'),('Spare','B')])
        ntx_sz = ntx_dtype.itemsize    
        ntx = self.header[4]
        # declare rx stuff
        nrx_dtype = np.dtype([('BeamPointingAngle',"h"),
            ('StartRangeSample#','H'),('NumberSamples','H'),
            ('DetectedRange','H'),('TransmitSector#','B'),
            ('Beam#','B')])
        nrx_sz = nrx_dtype.itemsize
        nrx = self.header[6]
        self.rx = np.zeros(nrx, dtype = nrx_dtype)
        # declare amplitudes stuff
        numamp = len(datablock) - ntx_sz * ntx - nrx_sz * nrx
        amp_dtype = np.dtype([('SampleAmplitude',"b")])
        tempamp = np.zeros(numamp, dtype = amp_dtype)
        # get the tx data
        self.tx = np.frombuffer(datablock[:ntx*ntx_sz], dtype = ntx_dtype)
        p = ntx*ntx_sz
        self.tx = self.tx.astype(Data107.ntx_dtype)
        self.tx['TiltTx'] *= 0.01
        self.tx['CenterFrequency'] *= 10
        # get the rx and amplitude data
        pamp = 0
        for n in range(nrx):
            self.rx[n] = np.frombuffer(datablock[p:p+nrx_sz], 
                dtype = nrx_dtype)
            p += nrx_sz
            # the number of samples for this beam
            beamsz = self.rx[n][2]
            tempamp[pamp:pamp+beamsz] = \
                np.frombuffer(datablock[p:p+beamsz], dtype = amp_dtype)
            p += beamsz
            pamp += beamsz
        self.rx = self.rx.astype(Data107.nrx_dtype)
        self.rx['BeamPointingAngle'] *= 0.01
        # unwined the beam data into an array
        numsamples = self.rx['NumberSamples']
        self.ampdata = np.zeros((numsamples.max(), nrx))
        pamp = 0
        for n in range(nrx):
            self.ampdata[:numsamples[n],n] = tempamp[pamp:pamp+numsamples[n]]
            pamp += numsamples[n]
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
        
        
class Data109:
    """
    The Stave Data Datagram, 6Dh / 109d / 'm'.  This data definition does not
    exist in the normal documentation.  All values are converted to whole
    units.
    """
    
    hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
        ('#Datagrams','H'),('Datagram#','H'),('RxSamplingFrequency',"f"),
        ('SoundSpeed',"f"),('StartRangeRefTx','H'),('TotalSample','H'),
        ('#SamplesInDatagram','H'),('Stave#','H'),('#StavesPerSample','H'),
        ('RangeToNormal','H'),('Spare','H')])
        
    def __init__(self, datablock, byteswap = False):
        """
        Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record.
        """
        hdr_dtype = np.dtype([('PingCounter','H'),('SystemSerial#','H'),
            ('#Datagrams','H'),('Datagram#','H'),('RxSamplingFrequency',"I"),
            ('SoundSpeed',"H"),('StartRangeRefTx','H'),('TotalSample','H'),
            ('#SamplesInDatagram','H'),('Stave#','H'),('#StavesPerSample','H'),
            ('RangeToNormal','H'),('Spare','H')])
        hdr_sz = hdr_dtype.itemsize
        self.header = np.frombuffer(datablock[:hdr_sz],
            dtype = hdr_dtype)[0]
        self.header = self.header.astype(Data109.hdr_dtype)
        self.header['RxSamplingFrequency'] *= 0.01
        self.header['SoundSpeed'] *= 0.1
        self.read(datablock[hdr_sz:])
        
    def read(self, datablock):
        """
        Reads the data portion of this datablock.  Data formats are defined
        after the header is read to accomidate sizes defined in the header.
        All values are converted to whole units.
        """
        Ns = self.header['#SamplesInDatagram']
        Ne = self.header['#StavesPerSample']
        read_fmt = str(Ne) + 'b'
        used_fmt = str(Ne) + 'f'
        read_dtype = np.dtype([('Sample#','H'),('TvgGain',"h"),
            ('StaveBackscatter',read_fmt)])
        read_sz = read_dtype.itemsize
        used_dtype = np.dtype([('Sample#','H'),('TvgGain',"f"),
            ('StaveBackscatter',read_fmt)])
        self.data = np.frombuffer(datablock[:Ns*read_sz],
            dtype = read_dtype)
        self.data = self.data.astype(used_dtype)
        self.data['TvgGain'] *= 0.01
        self.data['StaveBackscatter'] *= 0.5
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
        
        
class Data110:
    """
    The Network Attitiude Datagram, 6Eh / 110d / 'n'.  Data is found in the header
    and in the 'data' array.  All values are in degrees, and meters.  The raw
    data is being discarded at this point.
    """
    
    hdr_dtype = np.dtype([('Counter','H'),('Serial#','H'),('NumEntries','H'),
        ('Sensor','B'),('Spare','B')])
    att_dtype = np.dtype([('Time','d'),('Roll','f'),('Pitch','f'),('Heave','f'),
        ('Heading','f')])
    
    def __init__(self, datablock, POSIXtime, byteswap = False):
        """Catches the binary datablock and decodes the first section and calls
        the decoder for the rest of the record."""
        hdr_sz = Data110.hdr_dtype.itemsize
        self.time = POSIXtime
        self.header = np.frombuffer(datablock[:hdr_sz], dtype = Data110.hdr_dtype)[0]
        self.read(datablock[hdr_sz:])
        
    def read(self, datablock):
        """Reads the data section of the record.  Time is POSIX time,
        angles are in degrees, distances in meters."""
        att_file_dtype = np.dtype([('Time','H'),('Roll','h'),('Pitch','h'),('Heave','h'),
            ('Heading','H'),('NumBytesInput','B')])
        att_sz = att_file_dtype.itemsize
        self.numrecords = self.header[2]
        self.data = np.zeros(self.numrecords, dtype = Data110.att_dtype)
        datap = 0
        for i in range(self.numrecords):
            temp = np.frombuffer(datablock[datap:att_sz+datap],
                dtype = att_file_dtype)
            datap += att_sz + temp['NumBytesInput'][0]
            self.data[i] = temp[['Time','Roll','Pitch','Heave', 'Heading']].astype(Data110.att_dtype)
        self.data['Time'] = self.data['Time'] * 0.001 + self.time
        self.data['Roll'] *= 0.01
        self.data['Pitch'] *= 0.01
        self.data['Heave'] *= 0.01
        self.data['Heading'] *= 0.01
        
    def display(self):
        """
        Displays contents of the header to the command window.
        """
        for n,name in enumerate(self.header.dtype.names):
            print name + ' : ' + str(self.header[n])
            
            
class mappack:
    """
    Container for the file packet map.
    """
    def __init__(self):
        """Constructor creates a packmap dictionary"""
        self.packdir = {}
        self.dtypes = {
            68 : 'Old Depth',
            88 : 'New Depth',
            102 : 'Old Range/Angle',
            78 : 'New Rangle/Angle',
            83 : 'Old Seabed Imagry',
            89 : 'New Seabead Imagry',
            107 : 'Watercolumn',
            79 : 'Quality Factor',
            65 : 'Serial Attitude',
            110 : 'Network Attitude',
            67 : 'Clock',
            72 : 'Heading',
            80 : 'Postion',
            71 : 'Surface Sound Speed',
            85 : 'Sound Speed Profile',
            73 : 'Start Parameters',
            105 : 'Stop Parameters',
            112 : 'Remote Parameters',
            82 : 'Runtime Parameters'
            }
            
        
    def add(self, type, location=0, time=0):
        """Adds the location (byte in file) to the tuple for the value type"""
        if type in self.packdir:
            self.packdir[type].append([location,time])
        else:
            self.packdir[type] = []
            self.packdir[type].append([location,time])
            
    def finalize(self):
        for key in self.packdir.keys():
            temp = np.asarray(self.packdir[key])
            tempindx = temp[:,1].argsort()
            self.packdir[key] = temp[tempindx,:]
        
    def printmap(self):
        keys = []
        for i,v in self.packdir.iteritems():
            keys.append((int(i),len(v)))
        keys.sort()
        for key in keys:
            dtype = self.gettype(key[0])
            print dtype + ' ' + str(key[0]) + ' (' + hex(int(key[0])) + ') has ' + str(key[1]) + ' packets'
            
    def save(self, outfilename):
        outfile = open(outfilename, 'wb')
        pickle.dump(self.packdir, outfile)
        outfile.close()
        
    def gettype(self, dtype):
        if self.dtypes.has_key(int(dtype)):
            out = self.dtypes[int(dtype)]
        else:
            out = ''
        return out
        
    def load(self,infilename):
        infile = open(infilename, 'rb')
        self.packdir = pickle.load(infile)
        infile.close()
        
        
class resolve_file_depths:
    """
    This class treats each file as an object for creating resolved depths. 
    
    The steps here follow the process outlined in "Application of Surface Sound
    Speed Measurements in Post-Processing for Multi-Sector Multibeam 
    Echosounders" by J.D. Beaudion, J. E. Hughes Clarke, and J.E. Barlett, 
    International Hydrographic Review, v.5, no.3, p.26-31.
    http://www.omg.unb.ca/omg/papers/beaudoin_IHR_nov2004.pdf
    """
    def __init__(self, primaryfile, pre = None, post = None):
        """
        Open an All file, map it and make the navigation array. Maybe at some
        point having the previous and post files will help with resolving
        depths that fall outside the navigation for the primary file.
        """
        self.have_ssp_file = False
        self.have_patchtest = False
        self.p = allRead(primaryfile)
        if os.path.isfile(primaryfile[:-3] + 'par'):
            self.p.loadfilemap()
        else:
            self.p.mapfile()
            self.p.savefilemap()
        self.p.build_navarray()
        
        # set whether to applying heading, or keep the output in the sonar ref frame
        self.apply_heading = False
        self.apply_xducer_depth = False
        
    def set_patch_test_values(self, roll_offset=0, pitch_offset=0, heading_offset=0, position_delay=0, attitude_delay=0):
        """
        This method is used for setting the classes patch test values as
        derived from a patch test. Provide the orentation offsets in degrees,
        and the time offsets in seconds.
        """
        self.roll_offset = roll_offset
        self.pitch_offset = pitch_offset
        self.heading_offset = heading_offset
        self.position_delay = position_delay
        self.attitude_delay = attitude_delay
        
        self.have_patchtest = True
        
    def resolve_all_pings(self, ssp_filename):
        """
        still working this out.
        """
        self.ssp_filename = ssp_filename
        numpings = len(self.p.map.packdir['78'])
        for ping in range(numpings):
            self.resolve_ping(ping)
        
    def resolve_ping(self, recordnum, ssp_filename = None):
        """
        First hack at resolving a depth... not sure how this is going to work.
        Figuring it out as I go.  Need to add a better way for checking to see
        if a file is loaded, replacing a file, etc.
        """
        # set the ssp filename
        if ssp_filename is not None:
            self.ssp_filename = ssp_filename
            self.have_ssp_file = True
        elif self.have_ssp_file:
            pass
        else:
            self.have_ssp_file = False
            
        if not self.have_patchtest:
            self.set_patch_test_values()
            
        self.get_supporting_data(recordnum)
        tstamp, rxnav, twtt, azimuth, beam_depression, heave = self.get_ping_angle_bearing(recordnum)
        #get which side the pings are on
        swathside = np.sign(beam_depression)
        # get cast for the first sounding in the ping
        casttime = dtm.datetime.utcfromtimestamp(tstamp[0])
        # h_range is from the transducer.
        h_range, depth = self.raytrace(twtt, beam_depression, self.xducer_depth, self.surface_ss, casttime)
        h_range *= swathside
        # return the depth measurement to being referenced to the transducer.
        if not self.apply_xducer_depth:
            depth -= self.xducer_depth
        
        x = h_range * cos(np.deg2rad(azimuth)) + self.txoffset[1]
        y = h_range * sin(np.deg2rad(azimuth)) + self.txoffset[0]
        
        if self.apply_heading:
            h = rxnav[:,6]  # get the heading
            x += self.txoffset[0]*np.sin(h) + self.txoffset[1]*np.cos(h)
            y += self.txoffset[0]*np.cos(h) - self.txoffset[1]*np.sin(h)
        else:
            x += self.txoffset[0]
            y += self.txoffset[1]
        
        return tstamp, x, y, depth
    
    def get_supporting_data(self, recordnum):
        """
        Gets the supporting navigation, sounds speed, vessel offsets to support
        the process of resolving a depths.
        """
        # installation information
        self.p.getrecord('73', 0)
        settings = self.p.packet.subpack.settings
        self.settings = settings
        self.txoffset = np.asarray([settings['S1X'], settings['S1Y'], settings['S1Z']], 
            dtype = 'float')
        self.txrot = np.asarray([settings['S1R'], settings['S1P'], settings['S1H']], 
            dtype = 'float')
        self.rxoffset = np.asarray([settings['S2X'], settings['S2Y'], settings['S2Z']], 
            dtype = 'float')
        self.rxrot = np.asarray([settings['S2R'], settings['S2P'], settings['S2H']], 
            dtype = 'float')
        self.xducer_depth = float(settings['S1Z']) - float(settings['WLZ'])
        
        # ping information
        if self.p.map.packdir.has_key('78'):
            self.p.getrecord('78', recordnum)
        else:
            self.p.getrecord('102', recordnum)
        self.tstamp = self.p.packet.time
        self.header = self.p.packet.subpack.header
        self.tx = self.p.packet.subpack.tx
        self.rx = self.p.packet.subpack.rx
        self.surface_ss = self.header['SoundSpeed']
    
    def get_ping_angle_bearing(self, recordnum):
        """
        Do all the rotation stuff.
        """        
        # TX is reverse mounted: subtract 180 from heading installation angle,
        # and flip sign of the pitch offset.
        # RX is reverse mounted: subtract 180 from heading installation angle,
        # and flip the sign of the beam steering angles and the sign of the
        # receiver roll offset.  ~ per Jonny B 20120928
        
        if np.abs(self.txrot[2]) > 90:
            txo = -1
        else: txo = 1
        if np.abs(self.rxrot[2]) > 90:
            rxo = -1
        else: rxo = 1
        
        tx_vector = txo * np.mat([1,0,0]).T
        rx_vector = rxo * np.mat([0,1,0]).T

        txnum = self.tx['TransmitSector#'].argsort()  # this is getting the transmit # order
        
        # form array of transmit times
        if self.header['Ntx'] > 1:
            txtimes = []
            for indx in txnum:
                txtimes.append(self.tstamp + self.tx['Delay'][indx])
        else:
            txtimes = [self.tstamp + self.tx['Delay'][0]]
        txnav = self.p.getnav(txtimes)  # this is in tx sector order

        # make a TX rotation matrix for each sector in the "ping"
        TX = []
        # the alignment matrix
        TXa = self.rot_mat(self.txrot[0], self.txrot[1], self.txrot[2])
        for entry in txnav:
            # the orientation matrix for each sector
            TXo = self.rot_mat(entry[3],entry[4],entry[6])
            TX.append(TXo * TXa * tx_vector)
        # get receive times to get navigation information
        rxtimes = np.zeros(len(self.rx))
        if self.p.map.packdir.has_key('78'):
            twowaytraveltimes = self.rx['TravelTime']
        else:
            twowaytraveltimes = self.rx['Range']/ self.header['SamplingFrequency']
        for i, txtime in enumerate(txtimes):
            # this gets the index of all rx beams belonging to a particular tx
            rxnums = np.nonzero(self.rx['TransmitSectorID'] == i)[0]
            # then it adds the tx offset to that particular group of rx
            rxtimes[rxnums] = twowaytraveltimes[rxnums].astype(np.float64) + txtime
        
        # find the beam pointing vector for each beam
        beam_depression = np.zeros(len(self.rx))
        azimuth = np.zeros(len(self.rx))
        
        # the rx alignment matrix
        RXa = self.rot_mat(self.rxrot[0], self.rxrot[1], self.rxrot[2])
        # get the nav for all rx times in this ping
        rxnav = self.p.getnav(rxtimes)
        heave = np.zeros(len(self.rx))
        for i, entry in enumerate(rxnav):
            # the orientation matrix for each receive beam
            RXo = self.rot_mat(entry[3] + self.roll_offset, 
                entry[4]+self.pitch_offset, entry[6]+self.heading_offset)
            RX = RXo * RXa * rx_vector
            tx_indx = int(self.rx['TransmitSectorID'][i])  # get the tx number
            heave[i] = (rxnav[i][-2] + txnav[tx_indx][-2])/2
            # this section of code is in radians
            rx_steer = np.deg2rad(self.rx['BeamPointingAngle'][i]) * rxo
            tx_steer = np.deg2rad(self.tx['TiltAngle'][txnum[tx_indx]]) * txo
            misalign = np.arccos(TX[tx_indx].T * RX) - pi/2
            x = sin(tx_steer)
            y1 = -sin(rx_steer) / cos(misalign)
            y2 = x * np.tan(misalign)
            y = y1 + y2
            z = np.sqrt(1 - x**2 - y**2)
            BVp = np.array([x,y,z])
            Xp = TX[tx_indx].T
            Zp = np.cross(Xp,RX.T)
            Yp = np.cross(Zp,Xp)
            Rgeo = np.array([Xp,Yp,Zp]).T
            BV = np.dot(Rgeo,BVp.T)
            beam_depression[i] = np.arctan2(BV[2],np.sqrt(BV[0]**2 + BV[1]**2))
            azimuth[i] = np.arctan2(BV[1],BV[0])
            # end radians section of code
            if i == 0:
                print 'TX, RX'
                print TX[tx_indx]
                print RX
                print 'txsteer, rxsteer, misalign'
                print np.rad2deg([tx_steer, rx_steer])
                print misalign
                print 'heave, draft of xducer'
                print txnav[tx_indx][-2]
                print str(self.xducer_depth + heave[i])
                print 'x,y1,y2,y,z'
                print x, y1, y2, y, z
                print 'Xp,Yp,Zp'
                print Xp
                print Yp
                print Zp
                print 'BVp, Rgeo, BV'
                print BVp
                print Rgeo
                print BV
                print 'beam depression 0, azimuth 0'
                print np.rad2deg(beam_depression[0])
                print np.rad2deg(azimuth[0])
                
           
        beam_depression = np.rad2deg(beam_depression)
        azimuth = np.rad2deg(azimuth)
        if not self.apply_heading:
            azimuth -= rxnav[:,6]
        morethan360 = np.nonzero(azimuth > 360)[0]
        azimuth[morethan360] -= 360
        lessthanzero = np.nonzero(azimuth < 0)[0]
        azimuth[lessthanzero] += 360
        
        return rxtimes, rxnav, twowaytraveltimes, azimuth, beam_depression, heave
    
    def rot_mat(self, theta, phi, gamma, degrees = True):
        """
        Make the rotation matrix for a set of angles and return the matrix.
        All file angles are in degrees, so incoming angles are degrees.
        """
        if degrees == True:
            t,p,g = np.deg2rad([theta,phi,gamma])
        else:
            t,p,g = theta, phi, gamma
        rmat = np.mat(
            [[cos(p)*cos(g), sin(t)*sin(p)*cos(g) - cos(t)*sin(g), cos(t)*sin(p)*cos(g) + sin(p)*sin(g)],
            [cos(p)*sin(g), sin(t)*sin(p)*sin(g) + cos(t)*cos(g), cos(t)*sin(p)*sin(g) - sin(t)*cos(g)],
            [-sin(p), sin(t)*cos(p), cos(t)*cos(p)]]
            )
        return rmat
        
    def raytrace(self, twowaytraveltimes, beam_depression, xducer_depth, surface_ss, casttime):
        """
        Calls Jonny B's SV class to do the ray trace if possible, otherwise just assumes
        surface_ss for whole water column.  Need to make this so it does not load a new file
        if the file name is the same.  This might also require updates to JB's code...
        """
        
        if have_svp_module and self.have_ssp_file:
            y = np.zeros(len(beam_depression))
            z = np.zeros(len(beam_depression))
            profile = svp.SV()
            profile.read_hips(self.ssp_filename, time = casttime)
            indx = 0
            for twtt,angle in zip(twowaytraveltimes,beam_depression):
                if not np.isnan(angle):
                    y[indx], z[indx] = profile.raytrace(xducer_depth, angle, surface_ss, twtt)
                    indx +=1

        else:
            print 'Unable to use Jonny B svp module.  Assuming surface sound speed throughout watercolumn!'
            y = surface_ss/2 * twowaytraveltimes * cos(np.deg2rad(beam_depression))
            z = xducer_depth + surface_ss/2 * twowaytraveltimes * sin(np.deg2rad(beam_depression))
            
        return y, z
            
    def compare_to_xyz(self, recordnum, svfile = None):
        """
        Plots the results of resolve_ping(recordnum) to the xyz record(88 or 68).
        """
        if self.p.map.packdir.has_key('88'):
            self.p.getrecord(88, recordnum)
        else:
            self.p.getrecord(68, recordnum)
        za = self.p.packet.subpack.data['Depth']
        ya = self.p.packet.subpack.data['AcrossTrack']
        xa = self.p.packet.subpack.data['AlongTrack']
        
        # to compare, make sure heading is not being applied.
        temp = self.apply_heading, self.apply_xducer_depth
        self.apply_heading = False
        self.apply_xducer_depth = False
        tstamp, xb, yb, zb = self.resolve_ping(recordnum, svfile)
        # reset the apply_heading default
        self.apply_heading, self.apply_xducer_depth = temp
        
        plt.ion()
        plt.figure()
        plt.subplot(311)
        plt.plot(xa, 'g.', xb, 'b.')
        plt.legend(('xyz datagram','range/angle datagram'))
        plt.ylabel(('x(m)'))
        plt.subplot(312)
        plt.plot(ya, 'g.', yb, 'b.')
        plt.ylabel(('y(m)'))
        plt.subplot(313)
        plt.plot(za, 'g.', zb, 'b.')
        plt.ylabel(('z(m)'))
        plt.xlabel(('Beam #'))
        plt.suptitle(('record ' + str(recordnum)))
        
        plt.figure()
        plt.subplot(311)
        plt.plot(xa-xb, 'r.')
        plt.ylabel(('delta x(m)'))
        plt.subplot(312)
        plt.plot(ya-yb, 'r.')
        plt.ylabel(('delta y(m)'))
        plt.subplot(313)
        plt.plot(za-zb, 'r.')
        plt.ylabel(('delta Z(m)'))
        plt.xlabel(('Beam #'))
        plt.suptitle(('xyz - resolved for record ' + str(recordnum)))
        plt.draw()

        
def main():        
    if len(sys.argv) > 1:
        a = allRead(sys.argv[1])
        a.mapfile(True)
        a.close()
    else:
        print "No filename provided."
        
if __name__ == '__main__':
    main()