r"""
env_collector.py
----------------

**Extract information about a task from DB.**

**Features:**
    - get command line info
    - get all details of a task and save to CSV
    - print stdout of a task to console
    - search with regex through stdout of a job
    - export measurements with certain exitcode to a bpl

**UseCase:**
 Used to save some information for IT, on job / task problems.

**Usage:**

`C:\\>python env_collector.py -h ...`
`C:\\>python env_collector.py search -h ...`
...
"""
__all__ = ["env_exporter", "env_log_print", "env_stdout_search", "env_export_bpl"]

# - import Python modules ----------------------------------------------------------------------------------------------
from sys import exit as sexit, path as spath, argv
from os.path import abspath, join, dirname
from argparse import ArgumentParser, RawDescriptionHelpFormatter

# - import HPC modules -------------------------------------------------------------------------------------------------
HPC_FOLDER = abspath(join(dirname(__file__), r"..\.."))
if HPC_FOLDER not in spath:
    spath.append(HPC_FOLDER)

from hpc.rdb.env_data import TASKSTATE, env_exporter, env_log_print, env_stdout_search, env_export_bpl, \
    env_bpl_filter, env_bpl_operation
from hpc.core.dicts import DefDict
from hpc.core.tds import DEFAULT_HEAD_NODE


# - functions ----------------------------------------------------------------------------------------------------------
def parse_args(args):  # pragma: nocover
    """parse arguments"""
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    sub = opts.add_subparsers(help='command')
    opts.add_argument("-d", "--db", type=str, help="use sqlite DB")

    # coll = sub.add_parser('collect', help="collect data into DB")
    # coll.set_defaults(func=env_collector)
    # coll.add_argument("jobid", type=int, help="id of hpc job")
    # coll.add_argument("taskid", type=int, help="id of hpc task")

    exp = sub.add_parser('export', help="export collected data into CSV")
    exp.set_defaults(func=env_exporter)
    exp.add_argument("-n", "--headnode", type=str, default=DEFAULT_HEAD_NODE, help="name of HPC head node")
    exp.add_argument("-j", "--jobid", type=int, required=True, help="id of hpc job")
    exp.add_argument("outfile", type=str, help="output file name")
    exp.add_argument("-s", "--sortcol", type=int, default=3, help="specify a column to sort (1 based)")

    log = sub.add_parser('log', help="print info from a job")
    log.set_defaults(func=env_log_print)
    log.add_argument("-n", "--headnode", type=str, default=DEFAULT_HEAD_NODE, help="name of HPC head node")
    log.add_argument("-j", "--jobid", type=int, required=True, help="id of hpc job")
    prn = log.add_mutually_exclusive_group(required=True)
    prn.add_argument("-s", "--stdout", default=False, action="store_true", help="print stdout")
    prn.add_argument("-u", "--submit", default=False, action="store_true", help="print submit log (stdout)")
    prn.add_argument("-c", "--commands", default=False, action="store_true", help="print commands executed")
    log.add_argument("taskid", type=int, nargs='?', help="id of hpc task")

    srch = sub.add_parser('search', help="search through stdout of a job by some pattern")
    srch.set_defaults(func=env_stdout_search)
    srch.add_argument("-n", "--headnode", type=str, default=DEFAULT_HEAD_NODE, help="name of HPC head node")
    srch.add_argument("-j", "--jobid", type=int, required=True, help="id of hpc job")
    srch.add_argument("pattern", type=str, help="regex pattern to search stdout")

    fail = sub.add_parser('bpl', help="export recordings to bpl which are of a certain state / exitcode")
    fail.set_defaults(func=env_export_bpl)
    fail.add_argument("-n", "--headnode", type=str, default=DEFAULT_HEAD_NODE, help="name of HPC head node")
    fail.add_argument("-j", "--jobid", type=int, required=True, help="id of hpc job")
    fail.add_argument("-b", "--bpl", default='<job_id>.bpl', help="specify the output file")
    fail.add_argument("-s", "--state", choices=list(TASKSTATE.keys()), default='Failed',
                      help="filter for a certain task state, [default='Failed']")
    fail.add_argument("-e", "--exitcode", type=int, default=None,
                      help="filter for a certain exitcode, [default='None']")

    fltr = sub.add_parser('filter', help="filter bpl for a location")
    fltr.set_defaults(func=env_bpl_filter)
    fltr.add_argument("-i", "--inbpl", required=True, help="input bpl file")
    fltr.add_argument("-o", "--outbpl", required=True, type=str, help="output bpl file")
    fltr.add_argument("-r", "--rest", help="output rest (what left over) to bpl file")
    fltr.add_argument("-l", "--location", choices=["LND", "lnd", "BLR", "blr", "ABH", "abh"], default='LND',
                      help="location recording belongs to")

    oper = sub.add_parser('operate', help="filter bpl for a location")
    oper.set_defaults(func=env_bpl_operation)
    oper.add_argument(dest="arith", choices=['xor', 'or', 'and', 'sub'], type=str,
                      help="what to do (diff,merge,common,only in 1st)?")
    oper.add_argument("-i", "--inbpls", nargs=2, help="input files to process")
    oper.add_argument("-o", "--outbpl", required=True, help="output file")

    args = opts.parse_args(args, namespace=DefDict())
    if args.db is None:
        args.pop("db")
    return args


def init_n_go(args):
    """init and go"""
    return args.func(**args)


# - main main ----------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    sexit(init_n_go(parse_args(None if argv[1:] else ['-h'])))
