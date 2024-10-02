import socket
import sys

# Ensure that the IP is provided as a command-line argument
if len(sys.argv) < 2:
    print("Usage: python script.py <MY_IP>")
    sys.exit(1)

# Assign the first argument to MY_IP
MY_IP = sys.argv[1]

# Ports to scan
ports = [80, 443, 8080]

# Scan the ports
for port in ports:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex((MY_IP, port))
    if result == 0:
        print("Port {} is open".format(port))
    else:
        print("Port {} is closed".format(port))
    sock.close()
