"""
hpc_defs.py
-----------

hpc_defs Module for Hpc.

**User-API Interfaces**

    - `JobState` (this module)
    - `JobUnitType` (this module)
    - `JobPriority` (this module)
    - `TaskState` (this module)
    - `TaskType` (this module)
"""
# pylint: disable=R0903
# - Python imports -----------------------------------------------------------------------------------------------------
from functools import total_ordering
from six import iteritems

# - import HPC modules -------------------------------------------------------------------------------------------------
from .convert import safe_eval


# - classes ------------------------------------------------------------------------------------------------------------
@total_ordering
class JobState(object):
    """
    JobStateEnumeration, defines the state of a job.
    see https://msdn.microsoft.com/en-us/library/microsoft.hpc.scheduler.properties.jobstate(v=vs.85).aspx
    """

    #: task states available:
    Configuring, Submitted, Validating, ExternalValidation, Queued, Running, Finishing, Finished, Failed, Canceled, \
        Canceling, All = [2 ** i for i in range(11)] + [2047]

    FinalStates = [Finished, Failed, Canceled]

    def __init__(self, value=2047):
        """
        Initialize state with given value.

        :param int value: initial value to set
        :raises ValueError: in case value out of range
        """
        self._states = {1: 'Configuring', 2: 'Submitted', 4: 'Validating', 8: 'ExternalValidation', 16: 'Queued',
                        32: 'Running', 64: 'Finishing', 128: 'Finished', 256: 'Failed', 512: 'Canceled',
                        1024: 'Canceling', 2047: 'All'}
        try:
            if isinstance(value, int):
                self._states[value]  # pylint: disable=W0104
                self._value = value
            else:
                self._value = next((i for i, k in self._states.items() if k == value), None)
                assert self._value in self._states
        except Exception:
            raise ValueError('JobState value: "{0}" not allowed'.format(value))

    def __int__(self):
        """
        :return: integer value
        :rtype: int
        """
        return self._value

    def __str__(self):
        """
        :return: string representation
        :rtype: str
        """
        return self._states[self._value]

    def __lt__(self, other):
        """
        :return: is less than other
        :rtype: bool
        """
        return self._value < int(other)

    def __eq__(self, other):
        """
        :return: is equal to other
        :rtype: bool
        """
        return self._value == int(other)


@total_ordering
class JobUnitType(object):
    """
    Determines whether cores, nodes, or sockets are used to allocate resources for the job.
    see http://msdn.microsoft.com/en-us/library/
    microsoft.hpc.scheduler.ischedulerjob.unittype(v=vs.85).aspx
    """

    Core, Socket, Node, GPU = list(range(4))

    def __init__(self, value=1):
        """init with lowest"""
        self._value = value
        assert value in range(4), "value not in range!"

    def __str__(self):
        """
        :return: string representation
        :rtype: str
        """
        return ["Core", "Socket", "Node", "GPU"][self._value]

    def __int__(self):
        """
        :return: integer value
        :rtype: int
        """
        return self._value

    def __lt__(self, other):
        """
        :return: is less than other
        :rtype: bool
        """
        return self._value < int(other)

    def __eq__(self, other):
        """
        :return: is equal to other
        :rtype: bool
        """
        return self._value == int(other)


JOB_PRIOS = {0: "Lowest", 1000: "BelowNormal", 2000: "Normal", 3000: "AboveNormal", 4000: "Highest"}


@total_ordering
class JobPriority(object):
    """
    Defines the priorities that you can specify for a job.
    see http://msdn.microsoft.com/en-us/library/microsoft.hpc.scheduler.properties.jobpriority(v=vs.85).aspx
    """

    #: job priorities you can use
    Lowest, BelowNormal, Normal, AboveNormal, Highest = sorted(JOB_PRIOS.keys())

    def __init__(self, value=0):
        """
        init with lowest by default

        :param int|str value: also e.g. 'BelowNormal+100' is allowed
        """
        self._value = str(value).lower()
        try:
            for k, v in JOB_PRIOS.items():
                self._value = self._value.replace(v.lower(), str(k))
            self._value = safe_eval(self._value)
        except Exception:
            self._value = -1

        assert 0 <= self._value <= 4000, "JobPriority value: \"{}\" not allowed".format(value)

    def __str__(self):  # pylint: disable=R1710
        """
        :return: string representation
        :rtype: str
        """
        if self._value in JOB_PRIOS.keys():
            return JOB_PRIOS[self._value]

        for k, v in iteritems(JOB_PRIOS):
            if k - 500 < self._value <= k + 500:
                return "{}{:+d}".format(v, self._value - k)

    def __int__(self):
        """
        :return: integer value
        :rtype: int
        """
        return self._value

    def __lt__(self, other):
        """
        :return: is less than other
        :rtype: bool
        """
        return self._value < int(other)

    def __eq__(self, other):
        """
        :return: is equal to other
        :rtype: bool
        """
        return self._value == int(other)


class TaskState(object):
    """
    TaskStateEnumeration, defines the state of a task.
    see https://msdn.microsoft.com/en-us/library/microsoft.hpc.scheduler.properties.taskstate(v=vs.85).aspx
    """

    #: task states available:
    Configuring, Submitted, Validating, Queued, Dispatching, Running, Finishing, Finished, Failed, Canceled, \
        Canceling, All = [2 ** i for i in range(11)] + [2047]

    def __init__(self, value=2047):
        """
        initialize the task's state

        :param int value: value to set
        :raises ValueError: once value is out of range
        """
        self._states = {1: 'Configuring', 2: 'Submitted', 4: 'Validating', 8: 'Queued', 16: 'Dispatching',
                        32: 'Running', 64: 'Finishing', 128: 'Finished', 256: 'Failed', 512: 'Canceled',
                        1024: 'Canceling', 2047: 'All'}
        try:
            self._states[value]  # pylint: disable=W0104
            self._value = value
        except Exception:
            raise ValueError('TaskState value: "{0}" not allowed'.format(value))

    def __int__(self):
        """
        :return: the value itself
        :rtype: int
        """
        return self._value

    def __str__(self):
        """return string representation of value"""
        return self._states[self._value]


class TaskType(object):
    """
    TaskTypeEnumeration, defines how to run the Command from a Task
    see http://msdn.microsoft.com/en-us/library/microsoft.hpc.scheduler.properties.tasktype(v=vs.85).aspx
    """

    Basic, ParametricSweep, NodePrep, NodeRelease, Service = list(range(5))
