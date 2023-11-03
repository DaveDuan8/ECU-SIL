"""
upgrade.py
----------

provides auto upgrade functionality of HPC package
"""
# - Python imports -----------------------------------------------------------------------------------------------------
from __future__ import print_function
import sys
from os import getenv
from os.path import join, dirname, abspath, exists
from argparse import ArgumentParser, RawDescriptionHelpFormatter
try:
    from git import Repo
except ImportError:
    Repo = None

# - HPC imports --------------------------------------------------------------------------------------------------------
HPC_FOLDER = abspath(join(dirname(abspath(__file__)), r"..\.."))
if HPC_FOLDER not in sys.path:
    sys.path.append(HPC_FOLDER)

from hpc.core.tds import head_name


# - classes / functions ------------------------------------------------------------------------------------------------
def _upgrade(_args):
    """check for an available update of hpc package"""
    # check if we're on hpc, then continue
    if head_name() or getenv("CCP_JOBID"):
        return 0

    if "\\lib\\site-packages\\" in dirname(__file__).lower():
        print("please, use pip to upgrade your installation instead!")
        return 0

    hpc_path = join(HPC_FOLDER, "hpc")

    if Repo is None or not exists(join(hpc_path, ".git")):
        print("please, use 'git pull' or 'git clone git@github-am.geo.conti.de:ADAS/HPC_two.git hpc' manually.")
        return 0

    upg = Repo(hpc_path).remotes.origin.pull()
    if upg:
        print("hpc 2 package upgraded successfully: {}".format(", ".join([i.name for i in upg])))
    else:
        print("no upgrade needed")

    return 0


def _parse_args():
    """parse arguments"""
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    return opts.parse_args()


# - entry point --------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(_upgrade(_parse_args()))
