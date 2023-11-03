"""
set_hpc_creds.py
----------------

set password for all head nodes
"""
# pragma: nocover
# - import Python modules ----------------------------------------------------------------------------------------------
import sys
from os.path import abspath, join, dirname
from getpass import getpass
from threading import Thread
from argparse import ArgumentParser, RawDescriptionHelpFormatter

# - import HPC modules -------------------------------------------------------------------------------------------------
HPC_FOLDER = abspath(join(dirname(__file__), r"..\.."))
if HPC_FOLDER not in sys.path:
    sys.path.append(HPC_FOLDER)

from hpc import HpcSched  # pylint: disable=E0401
from hpc.core import UID_NAME
from hpc.core.logger import HpcPassword  # pylint: disable=E0401
from hpc.core.tds import HPC_STORAGE_MAP  # pylint: disable=E0401

# - defines ------------------------------------------------------------------------------------------------------------
CLUS_HEADS = set(HPC_STORAGE_MAP.keys()) - {"ITAS004A_CSCT"}


# - functions ----------------------------------------------------------------------------------------------------------
def _update_cred(clus, usr, pwd):
    """update your cread on a head"""
    try:
        with HpcSched(clus) as sched:
            sched.SetCachedCredentials(usr, pwd)
    except Exception as ex:
        print("ERROR: {!s}".format(ex))
    else:
        print("{}: done".format(clus))


def _set_creds(args):
    """update hpc folder and DB"""
    print("your password will be set on those head nodes: {}".format(", ".join(CLUS_HEADS)))
    pwd = getpass("enter {}'s password: ".format(args.user))

    with HpcPassword() as hset:
        hset[args.user] = pwd

    threads = []
    for clus in CLUS_HEADS:
        thread = Thread(target=_update_cred, args=(clus, args.user, pwd,))
        thread.daemon = True
        thread.start()
        threads.append(thread)

    for i in threads:
        i.join()

    return 0


def parse_args():
    """parse the arguments"""
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    opts.add_argument("-u", "--user", type=str, default=UID_NAME, help="domain\\username if different than current")
    return opts.parse_args()


# - main main ----------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        sys.exit(_set_creds(parse_args()))
    except KeyboardInterrupt:
        print("alright, let's leave it...")
        sys.exit(1)
