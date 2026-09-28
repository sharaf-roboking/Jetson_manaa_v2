#include <stdio.h>
#include <stdint.h>
#include <time.h>

static inline uint64_t read_cpu_cycle_counter (void) {
    uint64_t val = 0;
    __asm__ volatile("mrs %0, cntvct_el0" : "=r"(val));
    return val;
}

int main() {
  uint64_t t0 = read_cpu_cycle_counter();
  printf("Hello World!\n");
  uint64_t t1 = read_cpu_cycle_counter();
  printf("Elapsed time: %llu\n", t1-t0);
  return 0;
}
