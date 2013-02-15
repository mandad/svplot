import os
import sys
import threading
import socket
import time

class HypackCom(object):
    def __init__(self, protocol, port, communicator = None):
        self.print_count = 0
        self.communicator = communicator
        if protocol == 'UDP':
            self.net_client = UDPClient(port)
        else:
            self.net_client = TCPClient(port)

    def run_diag(self):
        self.net_client.create_socket()
        threading.Thread(target=self.net_client.collect_data, args=(self.print_diag, )).start()

    def run(self):
        self.net_client.create_socket()
        threading.Thread(target=self.net_client.collect_data, args=(self.report_info, )).start()

    def stop(self):
        self.net_client.stop()
        self.net_client.close_socket()

    def print_diag(self, data, addr):
        # Print some info about the data
        print 'Data from' + str(addr) + ' - ' + data.decode('ascii')
        print 'Data Length: %s'  % len(data)

        # Stop after 10 records
        self.inc_stop(10)

    def print_pos(self, data, addr, autostop = True):
        if addr[0] == '127.0.0.1' and len(data) == 41:
            print [float(pos) for pos in data.split(' ')[:2]]
            if autostop:
                self.inc_stop(5)

    def inc_stop(self, maxcount):
        self.print_count += 1
        if self.print_count > maxcount:
            self.net_client.stop()

    def report_info(self, data, addr):
        if self.communicator is not None:
            self.communicator.new_data(['hypack', (addr, data)]) 

class NetworkClient(object):
    def __init__(self, port):
        self.port = port
        self.stop_data = False

    def stop(self):
        self.stop_data = True

class UDPClient(NetworkClient):
    def __init__(self, port):
        NetworkClient.__init__(self, port)

    def create_socket(self, bind_address='127.0.0.1'):
        self.net_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.net_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.net_socket.settimeout(5)
        self.net_socket.bind((bind_address, self.port)) # binding should only be necessary for server

    def collect_data(self, process_function):
        self.stop_data = False
        while not self.stop_data:
            try:
                data,addr = self.net_socket.recvfrom(100)
                # The flag may have been set while waiting for data
                if not self.stop_data:
                    process_function(data, addr)
            except socket.timeout:
                print "No data received from server."
                break
        self.close_socket()

    def close_socket(self):
        self.net_socket.close()

# Note that this class was written for the sake of completeness, it is not used
# at the moment and has not been tested
class TCPClient(NetworkClient):
    def __init__(self, port):
        NetworkClient.__init__(self, port)

    def create_socket(self, server_address='127.0.0.1'):
        self.net_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.net_socket.settimeout(5)
        self.server_addr = server_address
        self.net_socket.connect((server_address, self.port))

    def collect_data(self, process_function):
        self.stop_data = False
        while not self.stop_data:
            try:
                data = self.net_socket.recv(100)
                process_function(data, self.server_addr)
            except socket.timeout:
                print "No data received from server."
                break
        self.net_socket.close()
        time.sleep(1)


def main():
    if len(sys.argv) > 1:
        hc = HypackCom('UDP', sys.argv[1])
    else:
        hc = HypackCom('UDP', 9888)
    hc.run_diag()

if __name__ == '__main__':
    main()
