"""
error.py
--------

This module contains error handling class and defines for all HPC errors.
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from sys import _getframe
from os.path import basename

# - HPC error codes ----------------------------------------------------------------------------------------------------
# they need to be aligned with DB entries: HPC_EXITCODES
ERR_OK = 0
ERR_UNSPECIFIED = 1

# - application specific error codes -----------------------------------------------------------------------------------
ERR_PYTHON_UNSPECIFIED_ERROR_FOUND = 200
# more custom error codes are 201 to 219
# ERR_PSEUDO_SKIPON = 256

# - HPC internal error codes
ERR_HPC_UNSPECIFIED_ERROR_FOUND = 20
ERR_HPC_APPLICATION_NOT_LOCAL = 21
ERR_HPC_WRONG_ARG = 22
ERR_HPC_USER_CANCEL_TASK_DETECTED = 23
ERR_HPC_DATABASE = 24
ERR_HPC_PID_INVALID = 26
ERR_HPC_INTERNAL_ERROR = 27
ERR_HPC_CYCLIC_ADMIN_JOB_FAILED = 28
ERR_HPC_APPLICATION_NOT_FOUND = 29
ERR_HPC_SCRIPT_MALFUNCTION = 30
ERR_HPC_LOW_DISK_SPACE = 31

# - application specific error codes -----------------------------------------------------------------------------------
ERR_APPLICATION_UNSPECIFIED_ERROR_FOUND = 40
ERR_APPLICATION_CPU_IDLE = 41
ERR_APPLICATION_IO_IDLE = 42
ERR_APPLICATION_PRN_IDLE = 43
ERR_APPLICATION_TIMEOUT = 46
# ERR_APPLICATION_IPV4_RETRANSMITRATE = 47
# ERR_APPLICATION_IPV6_RETRANSMITRATE = 48
ERR_APPLICATION_HANG = 49
ERR_APPLICATION_WRAPPER = 50
ERR_APPLICATION_LOW_MEM = 51
ERR_APPLICATION_LOW_CPU = 52
ERR_APPLICATION_HIGH_MEM = 53
ERR_APPLICATION_FATAL = 54

# - floating point exceptions ------------------------------------------------------------------------------------------
ERR_APP_FP_EXCEPTION_INVALID_OP = 60
ERR_APP_FP_EXCEPTION_DIVISION_BY_ZERO = 61
ERR_APP_FP_EXCEPTION_OVERFLOW = 62
ERR_APP_FP_EXCEPTION_UNDERFLOW = 63
ERR_APP_FP_EXCEPTION_INEXACT = 64
ERR_APP_FP_EXCEPTION_DENORMAL_OP = 65
ERR_APP_FP_EXCEPTION_STACK_CHECK = 66

# - crash exceptions ---------------------------------------------------------------------------------------------------
ERR_APP_CRASH_ACCESS_VIOLATION = 70
ERR_APP_CRASH_INVALID_PARAMETER = 71
ERR_APP_CRASH_ARRAY_BOUNDS_EXCEEDED = 72
ERR_APP_CRASH_BREAKPOINT = 73
ERR_APP_CRASH_FLT_DIVIDE_BY_ZERO = 74
ERR_APP_CRASH_FLT_INVALID_OPERATION = 75
ERR_APP_CRASH_GUARD_PAGE = 76
ERR_APP_CRASH_ILLEGAL_INSTRUCTION = 77
ERR_APP_CRASH_INT_DIVIDE_BY_ZERO = 78
ERR_APP_CRASH_INT_OVERFLOW = 79
ERR_APP_CRASH_INVALID_HANDLE = 80
ERR_APP_CRASH_PRIV_INSTRUCTION = 81
ERR_APP_CRASH_SINGLE_STEP = 82
ERR_APP_CRASH_STACK_BUFFER_OVERRUN = 83
ERR_APP_CRASH_FATAL_APP_EXIT = 84
ERR_APP_CRASH_THREAD_ACTIVATION_CONTEXT = 85

# 350 - 399 error codes are for log errors
ERR_APP_EXC_NEAR_SCAN_PEAK_ERROR = 90
ERR_APP_EXC_FAR_SCAN_PEAK_ERROR = 91
ERR_APP_EXC_PEAK_ERROR_AT_POSITION = 92
ERR_APP_EXC_ACCESS_VIOLATION = 93
ERR_APP_EXC_INCONSISTENT_DATA_STRUCTURE = 94
ERR_APP_EXC_CONFIG_OF_MO_MISSING = 95
ERR_APP_EXC_MO_CODE_ERROR = 96
ERR_APP_EXC_BMW_RADOME_CORRECTION = 97
ERR_APP_EXC_UNKNOWN_EXCEPTION = 98
ERR_APP_EXC_UNHANDLED_EXCEPTION = 99

# this indicates an exception that was NOT covered with the previous ones and is completely new
ERR_APP_EXC_UNKNOWN = 100

ERR_APP_ERR_NETWORK_UNAVAILABLE = 110
ERR_APP_ERR_RECORDING_CORRUPT = 111
ERR_APP_BSIG_CORRUPT = 112
ERR_APP_BSIG_DURATION_DIFFERS = 113
ERR_APP_BSIG_TIME_JUMPS = 114
ERR_APP_BSIG_MISSING = 115

# - MTS application specific error codes -------------------------------------------------------------------------------
ERR_MTS_UNSPECIFIED_ERROR_FOUND = 120
ERR_MTS_CRASH_DUMP_FOUND = 121
ERR_MTS_CORRUPT_XLOG_FOUND = 122
ERR_MTS_BLOCKED_TERMINATED_CACHING_THREAD_FOUND = 123
ERR_MTS_APPLICATION_ERR_DETECTED = 124
ERR_MTS_UNKNOWN_ERROR = 125
ERR_MTS_LOG_EXCEPTION_FOUND = 126
ERR_MTS_LOG_ERROR_FOUND = 127
ERR_MTS_LOG_ALERT_FOUND = 128
ERR_MTS_LOG_WARNING_FOUND = 129
ERR_MTS_LOG_INFO_FOUND = 130
ERR_MTS_LOG_DEBUG_FOUND = 131
ERR_MTS_CORRUPT_CRASH_FOUND = 132
ERR_MTS_OLD_DLL_DETECTED = 133
ERR_MTS_MEM_LEAK_FOUND = 134
ERR_MTS_NO_XLOG_AVAILABLE = 135
ERR_MTS_ERR_SIDE_BY_SIDE = 136
ERR_MTS_READ_CONFIG = 137
ERR_MTS_READ_REC_FAILED = 138
ERR_MTS_RECOVERING_DATA = 139
ERR_MTS_REPORT_ERROR = 140
ERR_MTS_OUTPUT_CREATED = 141
ERR_MTS_GPU_EXEC = 142
ERR_MTS_INVALID_BLOCK = 143
ERR_MTS_LOW_VIRT_MEM = 144
ERR_MTS_NO_ERRLOG = 145
ERR_MTS_MERGE_REC = 146

# - IT environment specific error codes --------------------------------------------------------------------------------
ERR_INFRASTRUCTURE_UNSPECIFIC_ERROR_FOUND = 150
ERR_INFRASTRUCTURE_FAILED_TO_COPY_DATA = 152
ERR_INFRASTRUCTURE_RECORDING_UNAVAILABLE = 155
ERR_INFRASTRUCTURE_DATA_OUTPUT_OVERWRITE = 156
ERR_INFRASTRUCTURE_RECORDING_ARCHIVED = 157
ERR_INFRASTRUCTURE_FAILED_TO_CREATE_DATA = 158
ERR_INFRASTRUCTURE_GPU_EXEC = 159

# - MTS mapping tables
# also review MTS_exitcode.txt
MTS_LOOKUP_EXITCODE = {0: ERR_OK, 1: ERR_OK, 2: ERR_MTS_REPORT_ERROR, 3: ERR_MTS_NO_ERRLOG,
                       4: ERR_MTS_READ_REC_FAILED, 5: ERR_MTS_APPLICATION_ERR_DETECTED,
                       6: ERR_MTS_APPLICATION_ERR_DETECTED, 7: ERR_MTS_APPLICATION_ERR_DETECTED,
                       8: ERR_MTS_APPLICATION_ERR_DETECTED, 9: ERR_MTS_REPORT_ERROR,
                       10: ERR_MTS_APPLICATION_ERR_DETECTED, -306: ERR_APPLICATION_HANG,
                       -1073741819: ERR_APP_CRASH_ACCESS_VIOLATION, -1073741818: ERR_MTS_UNKNOWN_ERROR,
                       ERR_APPLICATION_CPU_IDLE: ERR_APPLICATION_CPU_IDLE,
                       ERR_APPLICATION_IO_IDLE: ERR_APPLICATION_IO_IDLE,
                       ERR_APPLICATION_TIMEOUT: ERR_APPLICATION_TIMEOUT,
                       ERR_APPLICATION_HANG: ERR_APPLICATION_HANG}
MTS_LOOKUP_EXITMSG = {0: "normal exit", 1: "normal exit", 2: "error or exception happened",
                      3: "initialization of error monitor", 4: "reading recording failed",
                      5: "compatibility error", 6: "AllowMultipleInstances in not enabled",
                      7: "exception happened", 8: "alert, error or exception happened",
                      9: "warning, alert, error or exception happened", 10: "error with a specific error code",
                      ERR_APPLICATION_CPU_IDLE: "CPU was idle", ERR_APPLICATION_IO_IDLE: "I/O was idle",
                      ERR_APPLICATION_TIMEOUT: "application timed out",
                      ERR_APPLICATION_HANG: "application didn't react",
                      -306: "application hang", -1073741819: "crash due to access violation",
                      -1073741818: "unknown error happened"}

# - map old exit codes to let users know about transition
EXIT_MAP = {20: -200, 21: -201, 22: -202, 23: -203, 24: -205, 26: -207, 27: -208, 28: -210, 29: -211, 30: -299,
            40: -300, 41: -301, 42: -302, 46: -303, 47: -304, 48: -305, 49: -306, 51: -308, 52: -309, 60: -310,
            61: -311, 62: -312, 63: -313, 64: -314, 65: -315, 66: -316, 70: -320, 71: -321, 72: -322, 73: -323,
            74: -324, 75: -325, 76: -326, 77: -327, 78: -328, 79: -329, 80: -330, 81: -331, 82: -332, 83: -333,
            84: -334, 85: -335, 90: -350, 91: -351, 92: -352, 93: -353, 94: -354, 95: -355, 96: -356, 97: -357,
            98: -358, 99: -359, 100: -399, 110: -360, 111: -361, 112: -370, 113: -371, 120: -10000, 121: -401,
            123: -403, 124: -404, 125: -405, 126: -412, 127: -414, 128: -413, 129: -416, 130: -417, 131: -418,
            132: -419, 133: -420, 134: -421, 135: -422, 136: -423, 137: -424, 138: -425, 139: -426, 150: -500,
            152: -502, 155: -506, 156: -507, 157: -508, 158: -509, 159: -510}

# - more defaults ------------------------------------------------------------------------------------------------------
UNFAILING_EXITCODES = [ERR_OK, ERR_HPC_DATABASE, ERR_APPLICATION_LOW_MEM, ERR_APPLICATION_LOW_CPU,
                       ERR_APP_EXC_NEAR_SCAN_PEAK_ERROR, ERR_APP_EXC_FAR_SCAN_PEAK_ERROR,
                       ERR_APP_EXC_PEAK_ERROR_AT_POSITION, ERR_APP_EXC_INCONSISTENT_DATA_STRUCTURE,
                       ERR_APP_EXC_CONFIG_OF_MO_MISSING, ERR_APP_EXC_MO_CODE_ERROR, ERR_APP_EXC_BMW_RADOME_CORRECTION,
                       ERR_APP_BSIG_CORRUPT, ERR_APP_BSIG_DURATION_DIFFERS, ERR_APP_BSIG_TIME_JUMPS,
                       ERR_APP_BSIG_MISSING, ERR_MTS_LOG_WARNING_FOUND, ERR_MTS_LOG_INFO_FOUND, ERR_MTS_LOG_DEBUG_FOUND,
                       ERR_INFRASTRUCTURE_DATA_OUTPUT_OVERWRITE, ERR_MTS_OLD_DLL_DETECTED]

SKIP_EXITCODES = [ERR_MTS_READ_REC_FAILED, ERR_INFRASTRUCTURE_RECORDING_ARCHIVED]


# - classes ------------------------------------------------------------------------------------------------------------
class HpcError(Exception):
    """Exception Class for all HPC Exceptions."""

    def __init__(self, msg, errno=ERR_HPC_UNSPECIFIED_ERROR_FOUND, dpth=2):
        """
        HPC error class

        :param str msg:   message to announce
        :param int errno: related error number
        :param int dpth:  starting frame depth for error trace, increase by 1 for each subclass level of `HpcError`
        """
        Exception.__init__(self, msg)
        frame = _getframe(dpth)
        self._msg = msg
        self._errno = errno
        self._error = "'%s' (%d): %s (line %d) attr: %s" \
                      % (msg, errno, basename(frame.f_code.co_filename), frame.f_lineno, frame.f_code.co_name)

    def __str__(self):
        """
        :return: our own string representation
        :rtype: str
        """
        return self._error

    @property
    def message(self):
        """raw message of myself without the traceback overhead"""
        return self._msg

    @property
    def error(self):
        """
        :return: error number of exception
        :rtype: int
        """
        return self._errno
