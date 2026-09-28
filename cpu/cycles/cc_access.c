#include <stdint.h>
uint64_t read_cpu_cycle_counter(void) {
    uint64_t val;
    asm volatile("mrs %0, cntvct_el0" : "=r"(val)); //pmccntr_el0
    return val;
}
