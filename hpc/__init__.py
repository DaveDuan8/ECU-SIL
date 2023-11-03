"""
.. _starting-point:

hpc
---

Subpackage for Handling the ADAS HPC Cluster.

This package provides a complete Interface to the Cluster to submit Jobs.

**Following Classes are available for the User-API:**

    `HpcError`, `Job`, `JobSim`, `TaskFactory`, `TaskFactoryMTS`, `SubTaskFactory`, `SubTaskFactoryMTS`,
    `SubTaskFactorySILLite`, `Bpl`, `Signal`, `SignalException`,
    `CollManager`, `Collection`, `Recording`, `CollException`

**Following Defines (classes) are available for the User-API:**

    `JobState`, `JobPriority`, `JobUnitType`

**To get more information about the usage of the HPC Cluster, you can also check following link(s):**

    https://confluence.auto.continental.cloud/display/GITTE/High+Performance+Computing

**To use the hpc package from your code do following**::

    from hpc import Job, ...

    # Create a instance of the Hpc class.
    with hpc.Job(SERVER, name='SMFC4B0_HLA_ECU-SIL-Test', project='SMFC4B0', template='Default', ...) as job:
        # add tasks here....

    ...

**Attention**:

    **do not manipulate the HPC package, risks are on your side!!!**

    rather write a ticket on `HPC github repo <https://github-am.geo.conti.de/ADAS/HPC_two/issues>`_
    or write a `Jira ticket <https://jira-adas.zone2.agileci.conti.de/secure/CreateIssueDetails!init.jspa?pid=12326
    &issuetype=10000&priority=3&summary=[issue+description]&assignee=uidv7805&customfield_10114=13464>`_
    or contact `TDM team via mail <mailto:07WWMGADASTDMService@conti.de>`_


"""
# pylint: disable=C0413

__all__ = ["__version__", "__short_version__", "HpcError", "error", "Job", "JobSim", "JobState", "TaskState",
           "JobPriority", "JobUnitType", "TaskFactory", "TaskFactoryMTS", "SubTaskFactory", "SubTaskFactoryMTS",
           "SubTaskFactorySILLite", "Signal", "SignalException", "Bpl", "DEFAULT_HEAD_NODE", "DATA_PATH", "PY_2_EXE",
           "PY_3_EXE", "PY_36_EXE", "PY_38_EXE", "LIN_3_EXE", "CollManager", "Collection", "Recording", "CollException",
           "articopy"]

# - prevent Py2.7 32bit usages -----------------------------------------------------------------------------------------
from struct import calcsize
from six import PY2
if PY2 and calcsize("P") * 8 == 32:
    raise AssertionError("Python 2.7 32bit is not supported at all.")

# - HPC imports --------------------------------------------------------------------------------------------------------
from .version import VERSION

# - defines ------------------------------------------------------------------------------------------------------------
__version__ = VERSION
__short_version__ = '{:0>2}{:0>2}{:0>2}I00'.format(*__version__.split('.'))
__mks_version__ = '{}.hpc_two'.format(__version__)

# - import user interfaces ---------------------------------------------------------------------------------------------
from .core import error
from .core.error import HpcError
from .core.artifact import articopy
from .core.hpc_defs import JobState, JobPriority, JobUnitType, TaskState
from .sbmt.job import Job
from .sbmt.job_sim import JobSim
# from .apps import App, Mts
from .sbmt.task_factory import TaskFactory
from .sbmt.subtask_factory import SubTaskFactory
from .sbmt.task_factory_mts import TaskFactoryMTS
from .sbmt.subtask_factory_mts import SubTaskFactoryMTS
from .sbmt.subtask_factory_sil_lite import SubTaskFactorySILLite

# some defines
from .core.tds import DEFAULT_HEAD_NODE, DATA_PATH, LIN_3_EXE, PY_2_EXE, PY_3_EXE, PY_36_EXE, PY_38_EXE, PY_310_EXE

# misc
from .bpl import Bpl, BplException
from .mts.signal import Signal, SignalException
from .rdb.base import BaseDB
from .rdb.catalog import CollManager, Collection, Recording, CollException
from .sched.sched_mshpc import HpcSched

from .core.easter import this, that
