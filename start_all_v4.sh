
#!/bin/bash

# Start inclinometer first
sudo sh ./start_inclinometer.sh &

# Give inclinometer time to connect and receive data
sleep 0.4

# Start camera
sudo sh ./start_camera_v4.sh &
sleep 0.4
sudo sh ./start_imu.sh &
sleep 0.4
sudo sh ./start_ublox.sh
