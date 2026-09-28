so inclinometer needs the raspi hat and the stack service running as well as a sending program through RJ45
set the wire ethernet IP into the same as the wifi is
ifconfig -a
sudo ifconfig eth0 192.168.1.10 netmask 255.255.255.0  # On sending Pi 1
sudo ifconfig eth0 192.168.1.11 netmask 255.255.255.0  # On receiving Jetson/ Pi 2
and then adjust ip and port accordingly in the python files

1. Server Configuration
On the Pi designated as the time source:

Install the NTP daemon:
sudo apt-get install ntp

Edit the configuration file:
sudo nano /etc/ntp.conf

Add or modify the following lines to allow local network access and define the local clock source:
# Allow local subnet (adjust IP range as needed)
restrict 192.168.1.0 mask 255.255.255.0 nomodify notrap nopeer
restrict 127.0.0.1
restrict ::1

# Use local hardware clock as a fallback/primary source
server 127.127.1.0
fudge 127.127.1.0 stratum 3

Restart the service:
sudo service ntp restart

2. Client Configuration
On the second Pi:

Ensure ntp is installed.
Edit /etc/ntp.conf and replace default internet servers with the Server Pi's IP address:
server <SERVER_IP_ADDRESS> iburst
restrict <SERVER_IP_ADDRESS> nomodify notrap nopeer

Restart the service:
sudo service ntp restart

3. Verification
Run the following command on the Client Pi to verify synchronization:

ntpq -p

Look for the server IP in the output with an asterisk (*) indicating it is the active time source. If the time difference is large initially, you may need to manually set the time close to the server before NTP can adjust it gradually.









To transfer data between two Raspberry Pi devices via an RJ45 cable using Python, you must first establish a network connection by assigning static IP addresses to both devices' eth0 interfaces. You can then use Python's built-in socket library to create a client-server architecture for sending and receiving data directly over the Ethernet link.

1. Network Configuration
Connect the two Pis with an Ethernet cable. Since there is no DHCP server, you must assign static IP addresses to ensure they can communicate. Run the following commands on each Pi (use different IPs for each):

sudo ifconfig eth0 192.168.1.10 netmask 255.255.255.0  # On Pi 1
sudo ifconfig eth0 192.168.1.11 netmask 255.255.255.0  # On Pi 2

Note: To make these settings persistent across reboots, add static ip_address=192.168.1.10/24 (or the respective IP) to /etc/dhcpcd.conf on each device.

2. Python Implementation
Use the socket module to handle TCP communication. One Pi acts as the Server (listener), and the other acts as the Client (sender).

Server Code (e.g., on Pi 2 - 192.168.1.11):

import socket

HOST = '0.0.0.0'  # Bind to all interfaces
PORT = 5005       # Port to listen on

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print("Waiting for connection...")
    conn, addr = s.accept()
    with conn:
        print(f"Connected by {addr}")
        while True:
            data = conn.recv(1024)
            if not data:
                break
            print(f"Received: {data.decode()}")

Client Code (e.g., on Pi 1 - 192.168.1.10):

import socket

HOST = '192.168.1.11'  # IP of the Server Pi
PORT = 5005

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    message = "Hello from Pi 1"
    s.sendall(message.encode())
    print("Data sent successfully")

3. Alternative Methods
SCP/SFTP: If you prefer file-based transfers over socket programming, enable SSH on both Pis and use the scp command or libraries like paramiko in Python to copy files directly.
Web Server: You can run a simple Python HTTP server on one Pi (python3 -m http.server) and use requests or wget on the other to fetch data.







lsof -i 
kill -9 PIDNRO
