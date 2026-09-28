
"tested to be working on raspberry pi5 (raspbian) and jetson orin nano (ubuntu)"

"fetch performance counters module from https://github.com/jerinjacobk/armv8_pmu_cycle_counter_el0"
git clone https://github.com/jerinjacobk/armv8_pmu_cycle_counter_el0
cd armv8_pmu_cycle_counter_el0
"and compile"
# If compiling natively on ARMv8 host
make
# If cross compiling pass arguments as make arguments, not env vars
make CROSS_COMPILE={cross_compiler_prefix} ARCH=arm64 KDIR=/path/to/kernel/sources

"compile cc_access.c to enable c function to access the cpu cycle counter using"
gcc -O2 -shared -o lib_cc_access.so -fPIC cc_access.c

"check the armv8 pmu cycle counter el0 module path is correct in hello.py"
"run"
sudo python3 hello.py

"result is saved in cc_cycle_count.txt"

c file example on how to use in ustrain folder
python example in ublox, inclinometer and camera folders

