
# load module that can access cpu performance counters
import subprocess
# run command and capture output
result = subprocess.run(["sudo", "insmod", "../armv8_pmu_cycle_counter_el0/pmu_el0_cycle_counter.ko"], capture_output=True, text=True)
print(f"Return code: {result.returncode}")
print(f"Output: {result.stdout}")
if result.stderr:
    print(f"Errors: {result.stderr}")

# import cpu cycle reader function
import ctypes
import numpy as np
# load the shared library
lib = ctypes.CDLL("./lib_cc_access.so")
lib.read_cpu_cycle_counter.restype = ctypes.c_uint64
# read the cycle counter
start = ctypes.c_uint64(lib.read_cpu_cycle_counter())
cc_file = open("cpu_cycle_count.txt","w")
while True:
    print('Hello World!');
    end = ctypes.c_uint64(lib.read_cpu_cycle_counter());
    cc_file.write(f"{start}" + " to " + f"{end}" + "\n");
    print('Bye World!')

cc_file.close()
