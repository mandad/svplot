import socket
import time

send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

pos = [416619.57, 4941931.56]

while True:
    try:
        send_string = '%.2f %.2f 4437.5541 12403.0662' % (pos[0], pos[1])
        # print send_string
        send_socket.sendto(send_string, ('127.0.0.1', 9888))
        pos[0] = pos[0] + 1
        pos[1] = pos[1] + 1
        time.sleep(1)
    except KeyboardInterrupt:
        break

print "Closing Server"
send_socket.close()
