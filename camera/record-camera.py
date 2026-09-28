import time
import datetime
import subprocess
#result = subprocess.run(["sudo","rm", "./capture_preview.jpg"], capture_output=True, text=True);
#print(f"Return code: {result.returncode}");
#print(f"Output: {result.stdout}");
#if result.stderr:
#    print(f"Errors: {result.stderr}");
#result = subprocess.run(["sudo","rm", "./tmp*"], capture_output=True, text=True);
#print(f"Return code: {result.returncode}");
#print(f"Output: {result.stdout}");
#if result.stderr:
#    print(f"Errors: {result.stderr}");
    
result = subprocess.run(["sudo", "rmmod", "pmu_el0_cycle_counter"], capture_output=True, text=True);
result = subprocess.run(["sudo", "insmod", "./camera/pmu_el0_cycle_counter.ko"], capture_output=True, text=True);
print(f"Return code: {result.returncode}");
print(f"Output: {result.stdout}");
if result.stderr:
    print(f"Errors: {result.stderr}");
import ctypes
import numpy as np
lib = ctypes.CDLL("./camera/lib_cc_access.so");
lib.read_cpu_cycle_counter.restype = ctypes.c_uint64;
start = ctypes.c_uint64(lib.read_cpu_cycle_counter());
image_index = 1;
timestr = time.strftime("%Y%m%d-%H%M%S");
#print timestr
from pathlib import Path
output_file_path = f"./results/camera{timestr}/"
output_file_name = "imgs_times.txt";
output_file = output_file_path+output_file_name;
cc_file = Path(output_file);
cc_file.parent.mkdir(exist_ok=True, parents=True);
cc_file.open('w');
cc_file.write_text("START:\n")
#cc_file.close();
#cc_file = open(f"./results{}/img_time.txt","w");
#cc_file.write("START\n");
#cc_file.close();
try:
    while True:
        cc_file = open(output_file,"a");
        print(image_index);
        subprocess.call(["sudo", "/home/manaa/Downloads/camera/gphoto2/gphoto2/gphoto2", "--capture-preview"]);
        temp_out = output_file_path + f"img{image_index}.jpg"
        #output_filename = f"./results/img{image_index}.jpg";
        print(temp_out);
        subprocess.call(["mv", "capture_preview.jpg", temp_out]);
        check_me = False;
        while not check_me:
            try:
                end = ctypes.c_uint64(lib.read_cpu_cycle_counter());
                check_me = True;
            except:
                check_me = False;
                #result = subprocess.run(["rm", "./capture_preview.jpg"], capture_output=True, text=True);
                #print(f"Return code: {result.returncode}");
                #print(f"Output: {result.stdout}");
                #if result.stderr:
                #    print(f"Errors: {result.stderr}");
        write_time = datetime.datetime.now();
        formatted_write_time = write_time.strftime("%Y-%m-%d %H:%M:%S");
        cc_file.write("img" + f"{image_index}" + " captured on " + formatted_write_time + " and at CPU cycle:" + f"{end}" + "\n");
        time.sleep(1);
        image_index = image_index +1;
        cc_file.close();
except:
    #result = subprocess.run(["rm", "./capture_preview.jpg"], capture_output=True, text=True);
    #print(f"Return code: {result.returncode}");
    #print(f"Output: {result.stdout}");
    #if result.stderr:
    #    print(f"Errors: {result.stderr}");
    cc_file.close();
#except KeyboardInterrupt:
#    cc_file.close();

