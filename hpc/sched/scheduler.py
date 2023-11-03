"""
scheduler.py
------------

abstract interface scheduler.
Currently a "local" scheduler, MS HPC (.NET based) and RestAPI scheduler is implemented.
"""
__all__ = ["Scheduler"]
# - import modules -----------------------------------------------------------------------------------------------------
from getpass import getpass

# - import HPC modules -------------------------------------------------------------------------------------------------
from ..core import UID_NAME
from ..core.tds import HPC_STORAGE_MAP
from ..core.logger import HpcPassword
from .sched_local import LocalScheduler
from .sched_mshpc import MsHpcScheduler
from .sched_rest import RestScheduler


# - classes ------------------------------------------------------------------------------------------------------------
class Scheduler(object):  # pylint: disable=R0903
    """Scheduler interface to the outside world"""

    def __new__(cls, head, *args, **kwargs):
        """
        overwrite to return related instance

        for JobSim we've simply using the local scheduler class
        for Job, we're having a look if on Linux or going via RestAPI (as a user wish)
        """
        if kwargs.get('sim', False) or head not in HPC_STORAGE_MAP.keys():
            return LocalScheduler("OTHER", *args, **kwargs)

        if not kwargs.get("restsched"):
            return MsHpcScheduler(head, *args, **kwargs)

        with HpcPassword() as hset:
            if not hset[UID_NAME]:
                hset[UID_NAME] = getpass("enter {}'s password: ".format(UID_NAME))

        return RestScheduler(head, *args, **kwargs)
