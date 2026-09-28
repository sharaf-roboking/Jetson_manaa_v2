sudo modprobe usbserial vendor=0x1546 product 0x0509
sudo modprobe ftdi_sio vendor=0x1546 product 0x0509
echo "1546 0509" | sudo tee /sys/bus/usb-serial/drivers/ftdi_sio/new_id
sudo python3 ./ublox/DUAL_UBOLX_RECORD_FINAL.py
