"""
sched_local.py
--------------

Interface to a "local" scheduler, usuallly used to simulate first task on local PC.
"""
# - Python imports ----------------------------------------------------------------------------------------------------
from os import makedirs, listdir

# - HPC imports -------------------------------------------------------------------------------------------------------
from ..core.convert import toint
from .base import SchedulerBase
from .sched_defs import LOCAL_NET_PATH


# - classes / functions -----------------------------------------------------------------------------------------------
class LocalScheduler(SchedulerBase):
    """
    Class, which reflects local scheduler interface,
    used for compatibility reasons for JobSim class
    """

    def __init__(self, headnode, **kwargs):
        """init local scheduler"""
        SchedulerBase.__init__(self, headnode, **kwargs)
        self._location = None

        self._base_dir = LOCAL_NET_PATH

        # just in case it doesn't exist yet (first time user?)
        try:
            makedirs(self._base_dir)
        except Exception:
            pass

        # find out what ID is next
        self._jobid = max([0] + [toint(i) for i in listdir(self._base_dir) if toint(i)]) + 1
        self.name = kwargs.get('name')

    def __str__(self):
        """
        :return: nice representation
        :rtype: str
        """
        return "<local scheduler: id={}, name={}>".format(self._jobid, self.name)
