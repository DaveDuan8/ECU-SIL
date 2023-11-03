"""
proc_vals.py
------------

process values
"""
# - defines ------------------------------------------------------------------------------------------------------------
# following defines are used for watching client
# current values are tuned to cancel when the process tree fulfills one of the following:
#   - no CPU usage for about 5 min or less then 2%
#     on a one core basis for a longer time
#   - less then 6 kb/s I/O traffic for 30 min
FILTER_STRENGTH_CPU = 0.3  # factor for new value to be combined with the old
FILTER_STRENGTH_IO = 0.11   # factor for new value to be combined with the old
FILTER_STRENGTH_PRN = 0.05  # factor for new value to be combined with the old

CPU_CONFIDENCE_THRESHOLD = 2.1  # threshold for cpu idle detection in [%]
IO_CONFIDENCE_THRESHOLD = 5.0  # threshold for i/o idle detection in [%]
PRN_CONFIDENCE_THRESHOLD = 3.0  # threshold for prn idle detection in [%]
FILTER_THRESHOLD_IO = 6  # i/o threshold for setting new filter value to 0 or 1 [kB/s]

FAIL_THRESHOLD = 5  # amount of tolerated wmi request fails in a row

# define APP_EXIT_CODE_MULTIPLE_INSTANCE_NOT_ALLOWED 6
MIN_NET_THROUGHPUT = 11000000
MIN_MEM_FREE = 3300000000
MIN_VIRT_FREE = MIN_MEM_FREE * 20
MAX_CPU_USAGE = 80.
D_FREE_THRESHOLD = 128000000
