#!/bin/bash

# Start inclinometer first
sudo sh ./start_inclinometer.sh &

# Give inclinometer time to connect and receive data
sleep 2

# Start camera
sudo sh ./start_camera_v4.sh
