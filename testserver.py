import socket
import time
import random
import numpy as np

# Code for the reson server
# np.random.standard_normal() * 30 + 1480

send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

pos = [416619.57, 4941931.56]

while True:
    try:
        send_string = '%.2f %.2f 4437.5541 12403.0662' % (pos[0], pos[1])
        # print send_string
        send_socket.sendto(send_string, ('127.0.0.1', 9888))
        # pos[0] = pos[0] + (random.random() * 2 - 1)
        pos[0] = pos[0] + np.random.standard_normal() * 0.8
        # pos[1] = pos[1] + random.random()
        pos[1] = pos[1] + (np.random.standard_normal() + 1) * 0.8
        time.sleep(0.01)
    except KeyboardInterrupt:
        break

print "Closing Server"
send_socket.close()
