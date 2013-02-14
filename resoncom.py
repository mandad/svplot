import HSTP.SetHSTPPath
import os, sys
import threading
import time

PathToApp = os.path.split(HSTP.SetHSTPPath.__file__)[0]+"/Pydro/" 
os.environ['PathToPydro']=PathToApp
print PathToApp
HSTP.SetHSTPPath.AddAll()

import sevenpy
import prr

class ResonComm:
    def __init__(self, reson_address, TCPport = 8888, comm_manager = None):
        self.reson_address = reson_address
        self.TCPport = TCPport
        self.comm_manager = comm_manager

    def runsonar(self):
        """Gets continuous data records from 7kcenter and prints the surface sv"""
        # Assumes own computer ip set to 192.168.0.20X
        self.reson = sevenpy.com7P(self.reson_address, 7125, '192.168.0.200')
        self.reson.stopUDP = False
        threading.Thread(target = self.reson.catchTCP, args = (self.TCPport,)).start()
        self.reson.command7P('recordrequest',(self.TCPport, 1, 2, 7000, 7006))
        
        self.reson.newdata = False

        # data_thread = threading.Thread(target = self.get_data_loop, args=(self.reson, comm_manager)).start()
        data_thread = threading.Thread(target = self.get_data_loop).start()
        # while datacount < 25:
        #     # This gets set by sevenpy when it recieves data
        #     if reson.newdata:
        #         # pull data from the data stream buffer
        #         data = reson.dataout
        #         reson.newdata = False
        #         if data.has_key('7006'):
        #             subpacket7006 = prr.Data7006(data['7006'][64:-4])
        #             print "Packet: %s, SV: %s" % (subpacket7006.header[1], subpacket7006.header[6])
        #             datacount += 1
        # time.sleep(20)

        # stop7kcenter(reson, TCPport)

    def print_sv(self, packet):
        print "Packet: %s, SV: %s" % (packet.header[1], packet.header[6])

    # def get_data_loop(reson, comm_manager):
    def get_data_loop(self):
        self.datacount = 0;
        try:
            while self.datacount < 40:
                if self.reson.newdata:
                    # pull data from the data stream buffer
                    data = self.reson.dataout
                    self.reson.newdata = False
                    if data.has_key('7006'):
                        subpacket7006 = prr.Data7006(data['7006'][64:-4])
                        if self.comm_manager is None:
                            self.print_sv(subpacket7006)
                        else:
                            self.comm_manager.new_data(['reson', subpacket7006])
                        # print "Packet: %s, SV: %s" % (subpacket7006.header[1], subpacket7006.header[6])
                        self.datacount += 1
        except KeyboardInterrupt:
            pass

    def stop7kcenter(self):
        """Stop the TCP data flow from the 7kcenter."""
        self.reson.stopTCP = True
        print "Stand by while properly closing connction to 7kcenter. """
        time.sleep(2)
        self.reson.command7P('stoprequest',(self.TCPport, 1))

def main():
    """Just run the program when used from the command line.  Optional seccond
    argument of port number"""
    if len(sys.argv) > 1:
        reson_comm = ResonComm('192.168.0.101', int(sys.argv[1]))
        reson_comm.runsonar()
    else:
        reson_comm = ResonComm('192.168.0.101')
        reson_comm.runsonar()

    time.sleep(20)
    reson_comm.stop7kcenter()

if __name__ == '__main__':
    main()