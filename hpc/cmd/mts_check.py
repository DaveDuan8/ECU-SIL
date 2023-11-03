r"""
mts_check.py
------------

**Checks after MTS Crashdumps, Errors and Exception in \*.xlog files.**

**Features:**
    - Printing of Error Statistic Output from HPCErrorDB (Oracle)
    - Scanning of a given Folder for Chrashdumps and xlog-Error File Entries.
    - Scanning xlog-Error files for MTS Errors, Exceptions and ...
    - Writing all found errors into the Oracle Error DB.

**UseCase:**
    Typically used as SubTask in the MTSTaskFactory for error checking.

**Usage:**

    - `C:\\>python mts_check.py check \\\\LIFS010\\hpc\\liss006\\3511_MFC3B0_JointSim\\2_Output\\T00008`
    - `C:\\>python mts_check.py stat 3511`
    - | scan for db file and add rec file mapping entries:
      | `C:\\>python mts_check.py check \\\\LIFS010\\hpc\\liss006\\3511_MFC3B0_JointSim -d`

Parameters
----------
    check \<folder\>
        The given Input Folder URL which is used to scan after some errornous stuff.
    stat \<jobid\>
        JobId which must be used for getting the Error info out from the Oracle DB.

"""
__all__ = ["print_logs"]

# - import Python modules ---------------------------------------------------------------------------------------------
from sys import exit as sexit, path as spath, argv
from os.path import abspath, join, dirname
from argparse import ArgumentParser, RawDescriptionHelpFormatter

# - add HPC folder ----------------------------------------------------------------------------------------------------
HPC_FOLDER = abspath(join(dirname(abspath(__file__)), "..", ".."))
if HPC_FOLDER not in spath:
    spath.append(HPC_FOLDER)

# - import HPC modules ------------------------------------------------------------------------------------------------
from hpc.mts.mts_check import mts_log_check, mts_check, mts_recheck, print_statistic, print_logs
from hpc.mts.parser import XlogHandler
from hpc.core.dicts import DefDict
from hpc.core.tds import DEFAULT_HEAD_NODE


# - functions ---------------------------------------------------------------------------------------------------------
def parse_args(args):  # pragma: nocover
    """parse arguments"""
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)

    opts.add_argument("-n", "--hpc-node", dest="head_node", type=str, default=DEFAULT_HEAD_NODE,
                      help="HPC head node name, defaults back to SIL head on your location")
    opts.add_argument("-P", "--use-print", default=False, action="store_true", help="use print instead of logger")

    sub = opts.add_subparsers(help='command')

    chk = sub.add_parser('check', help="check mts error outputs")
    chk.set_defaults(func=mts_check)
    chk.add_argument("folder", type=str, help="check job folder for mts log files to be stored to DB")
    chk.add_argument("-d", "--db-scan", dest="scan", default=False, action="store_true",
                     help="check job folder for mts log files to be stored to DB")
    chk.add_argument("-l", "--level", choices=list(range(len(XlogHandler.levels))), default=1, type=int,
                     help="minimum logging level (-> HPC_ERRTYPE)")
    chk.add_argument("-D", "--dry-run", default=False, action="store_true", help="dry run: do not save DB items")
    chk.add_argument("-p", "--purge", default=False, action="store_true", help="purge all DB entries before")
    chk.add_argument("-v", "--verbose", default=False, action="store_true", help="be a bit more verbose: print logs")

    clc = sub.add_parser('log_check', help="check mts error outputs")
    clc.set_defaults(func=mts_log_check, cmdline=True)
    clc.add_argument("folder", type=str, help="check job folder for mts log files and errors")
    clc.add_argument("-g", "--gpu", default=False, action="store_true", help="check GPU related messages")
    clc.add_argument("-l", "--level", choices=list(range(len(XlogHandler.levels))), default=1, type=int,
                     help="minimum logging level (-> HPC_ERRTYPE)")

    stat = sub.add_parser('stat', help="print out statistic for a certain hpc job")
    stat.set_defaults(func=print_statistic)
    stat.add_argument("jobid", type=int, help="id of hpc job")
    stat.add_argument("taskid", nargs='?', default=None, help="the task id of the job")

    logs = sub.add_parser('logs', help="print out log information for a certain hpc job (/ task)")
    logs.set_defaults(func=print_logs)
    logs.add_argument("jobid", type=int, help="id of hpc job")
    logs.add_argument("taskid", nargs='*', type=int, help="id(s) of hpc task")

    rechk = sub.add_parser('recheck', help="print out log information for a certain hpc job (/ task)")
    rechk.set_defaults(func=mts_recheck)
    rechk.add_argument("jobrange", type=str, help="range of job id's to rescan")
    rechk.add_argument("-e", "--exitcode", type=int, default=None, help="care only about those with specific exit code")

    return opts.parse_args(args, namespace=DefDict())


# - main ---------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    pargs = parse_args(None if argv[1:] else ['-h'])  # pylint: disable=C0103
    sexit(pargs.func(**pargs))
