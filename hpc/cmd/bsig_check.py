r"""
bsig_check.py
-------------

**Checks bisg files for their validity.**

**Features:**
    - Checks all bsig files from a given folder if they are readable / consistent.

**Usage:**

`C:\\>bsig_check.py J:\\luss021\\85585_DEV_ALL_LD_050561I02_Ori-Sim\\2_Output\\_data`

Parameters
----------
    | -P use print, not logger output
    | \<folder\> to scan through

"""
__all__ = ["bsig_check"]

# - Python imports ----------------------------------------------------------------------------------------------------
import sys
from os.path import abspath, join, dirname
from argparse import ArgumentParser, RawDescriptionHelpFormatter

# - HPC imports -------------------------------------------------------------------------------------------------------
HPC_FOLDER = abspath(join(dirname(abspath(__file__)), r"..\.."))
if HPC_FOLDER not in sys.path:
    sys.path.append(HPC_FOLDER)

from hpc.core.dicts import DefDict
from hpc.mts.bsig_check import bsig_check


# - functions ----------------------------------------------------------------------------------------------------------
def parse_args(args):  # pragma: nocover
    """parse arguments"""
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)

    opts.add_argument("-r", "--rectms", nargs='*', type=int, help="expected recording begin and end absolute timestamp")
    opts.add_argument("-d", "--recdiff", default=10, type=float, help="max allowed length difference")
    opts.add_argument("bsigs", type=str, help="check job file or folder and analize bsig file(s)")

    return opts.parse_args(args, namespace=DefDict(cmdline=True))


if __name__ == '__main__':
    try:
        sys.exit(bsig_check(**parse_args(None if sys.argv[1:] else ['-h'])))
    except KeyboardInterrupt:
        print("ctrl+c pressed.")
        sys.exit(-1)
