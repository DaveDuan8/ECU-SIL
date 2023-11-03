"""
sched_defs.py
-------------

scheduler global variables
"""
# - Python imports -----------------------------------------------------------------------------------------------------
from os.path import join

# - defines ------------------------------------------------------------------------------------------------------------
LOCAL_NET_PATH = r"D:\data\_hpc_base"
INPUT_PATH = "1_Input"
OUTPUT_PATH = "2_Output"
OUTPUT_DATA_PATH = join(OUTPUT_PATH, "_data")

STD_TASK_RUNTIME = 75.  # hours
MAX_TASK_RUNTIME = 170.  # hours
SHORT_TEST_RUNTIME = 0.9  # hours
STD_SWEEP_RUNTIME = 0.08  # [h] = 288 seconds
MAX_SWEEP_RUNTIME = 0.95  # close to an hour
