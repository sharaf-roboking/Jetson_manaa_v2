import socket
import time

import datetime
import subprocess
#result = subprocess.run(["sudo", "rmmod", "pmu_el0_cycle_counter"], capture_output=True, text=True);
#result = subprocess.run(["sudo", "insmod", "./pmu_el0_cycle_counter.ko"], capture_output=True, text=True);
#print(f"Return code: {result.returncode}");
#print(f"Output: {result.stdout}");
#if result.stderr:
#    print(f"Errors: {result.stderr}");
import ctypes
import numpy as np
lib = ctypes.CDLL("./lib_cc_access.so");
lib.read_cpu_cycle_counter.restype = ctypes.c_uint64;
start = ctypes.c_uint64(lib.read_cpu_cycle_counter());
image_index = 1;

HOST = '192.168.0.238'
PORT = 5005

timestr = time.strftime("%Y%m%d-%H%M%S");
#print timestr
from pathlib import Path
output_file_path = f"./results/inclinometer{timestr}/"
output_file_name = "angles_times.txt";
output_file = output_file_path+output_file_name;
cc_file = Path(output_file);
cc_file.parent.mkdir(exist_ok=True, parents=True);
cc_file.open('w');
cc_file.write_text("START:\n")
#cc_file = open("./results/angle_time.txt","w");
#cc_file.write("START:\n");
#cc_file.close();
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST,PORT));
    try:
        while True:
            s.listen();
            #print("Waiting for connection...");
            conn, addr = s.accept();
            with conn:
                #print(f"Connected by {addr}");
                while True:
                    cc_file = open(output_file,"a");
                    data = conn.recv(1024);
                    if not data:
                        #time.sleep(1);
                        #print("NoDATA");
                        break;
                    else:
                        print(f"Received: {data.decode()}");
                        check_me = False;
                        while not check_me:
                            try:
                                end = ctypes.c_uint64(lib.read_cpu_cycle_counter());
                                check_me = True;
                            except:
                                check_me = False;
                                s.close();
                                cc_file.close();
                        write_time = datetime.datetime.now();
                        formatted_write_time = write_time.strftime("%Y-%m-%d %H:%M:%S");
                        cc_file.write(f"{data.decode()}" + " captured on " + formatted_write_time + " and at CPU cycle:" + f"{end}" + "\n");
                        cc_file.close();
    except: # KeyboardInterrupt:
        s.close();
        cc_file.close();

