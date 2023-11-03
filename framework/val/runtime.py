"""
framework/val/runtime.py
------------------

Subpackage for Handling Runtime incidents providing:

  - `RuntimeJob`
  - `RuntimeIncident`

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 09:24:01CEST $
"""
# - import framework modules ------------------------------------------------------------------------------------------------
# from framework.db.db_common import BaseDB
from framework.util.logger import Logger
from framework.util.helper import arg_trans

# - defines -----------------------------------------------------------------------------------------------------------
# supported incident types in this module:
TYPE_ERROR = 'Error'
TYPE_EXCEPTION = 'Exception'
TYPE_CRASH = 'Crash'
TYPE_ALERT = 'Alert'
TYPE_WARNING = 'Warning'
TYPE_INFORMATION = 'Information'
TYPE_DEBUG = 'Debug'

TYPELIST = (TYPE_DEBUG, TYPE_INFORMATION, TYPE_WARNING, TYPE_ALERT, TYPE_ERROR, TYPE_EXCEPTION, TYPE_CRASH)


# - classes -----------------------------------------------------------------------------------------------------------
class RuntimeIncident(object):
    """
    container for information about the incidents encountered during simulation/validation run
    """
    def __init__(self, *args, **kwargs):
        """ new incident

        :keyword jobid: HPC JobId
        :type jobid:  integer
        :keyword taskid: HPC TaskId of the incident
        :type taskid:  integer
        :keyword errtype: error type as defined in `HpcErrorDB` ERR_TYPES
        :type errtype:  string
        :keyword errcode: error code as returned by the tool (compiler etc.)
        :type errcode:  integer
        :keyword description: short description of the incident like 'file not found'
        :type description:  string
        :keyword source: detailed source of incident like trace back
        :type source:  string
        """
        kwargs['default'] = ''
        opts = arg_trans([('node', 'LUSS010'), ('jobid', 0), ('taskid', 0),
                          'errtype', 'errcode', 'description', 'source'], *args, **kwargs)
        self.__jobid = opts['jobid']
        self.__taskid = opts['taskid']
        # if type(errtype) is str:

        self.__type = opts['errtype']
        self.__code = opts['errcode']
        self.__desc = opts['description']
        self.__source = opts['source']
        self.__node = opts['node']

    def __repr__(self):
        return repr((self.__node, self.__jobid, self.__taskid, self.__type, self.__code, self.__desc, self.__source))

    @property
    def node(self):
        """AlgoTestReport Interface overloaded attribute, returnsHPC node as string.
        """
        return self.__node

    @property
    def job_id(self):
        """AlgoTestReport Interface overloaded attribute, returns HPC job id as int.
        """
        return self.__jobid

    @property
    def task_id(self):
        """AlgoTestReport Interface overloaded attribute, returns HPC task id as int.
        """
        return self.__taskid

    @property
    def type(self):
        """AlgoTestReport Interface overloaded attribute, returns incident type as defined for HPC ErrorDb as string.
        """
        # desc = self.__type
        return self.__type

    @property
    def code(self):
        """AlgoTestReport Interface overloaded attribute, returns code of incident (error code etc.) as int.
        """
        return self.__code

    @property
    def desc(self):
        """AlgoTestReport Interface overloaded attribute, returns description of the incident as string.
        """
        return self.__desc

    @property
    def src(self):
        """AlgoTestReport Interface overloaded attribute, returns source of incident as string.
        """
        return self.__source


class RuntimeJob(object):
    """
    **job details for runtime class**

    A Job is a sequence of tasks executed to get simulation or validation results,
    for one complete testrun several jobs might be needed.
    Inside the ResultDb the RuntimeJobs are linked to the according `TestRun`.

    From Jobs executed on HPC cloud we'll get some runtime results of its tasks
    together with the reported incidents using a copy method.

    incidents provided by `HpcErrorDB` interface with
      - COL_NAME_RTL_JOBID:  jobid,
      - COL_NAME_RTL_TASKID: taskid,
      - COL_NAME_RTL_TYPE:   errtype,
      - COL_NAME_RTL_CODE:   errcode,
      - COL_NAME_RTL_DESCRIPTION: desc,
      - COL_NAME_RTL_SOURCE: src
      - COL_NAME_RTL_NODE: node

    methods to get filtered extracts
    """

    def __init__(self, node, jobid):
        """ initialize the incident

        :param jobid: JobId of the HPC job run for the TestRun
        :type jobid:  integer
        """
        self.__node = node
        self.__jobid = jobid
        self.__error_count = 0
        self.__exception_count = 0
        self.__crash_count = 0
        self.__incidents = []
        self._log = Logger(self.__class__.__name__)

    def get_all_incidents(self, itype=None):  # pylint: disable=C0103
        """
        return list of all incidents for given type

        :param itype: type of incident like 'Error', 'Crash',...
        :type itype:  str
        :return: all incidents of a given type or all for no type sorted by task_id
        :rtype:  list(`RuntimeIncident`)
        """
        rlist = self.__incidents
        if itype is not None:
            rlist = [x for x in rlist if x.type == itype]

        return rlist

    def count_incidents(self, itype=None):  # pylint: disable=C0103
        """
        count the incidents for a given job id and opt. type

        :param itype: type of incident like 'Error', 'Crash',...
        :type itype: str
        :return: number of incidents
        :rtype: int
        """
        return len(self.get_all_incidents(itype))

    @property
    def node(self):
        """AlgoTestReport Interface overloaded attribute, returns name of HPC node as string.
        """
        return self.__node

    @property
    def jobid(self):
        """AlgoTestReport Interface overloaded attribute, returns id of this job as provided by HPC as int.
        """
        return self.__jobid

    @property
    def error_count(self):
        """AlgoTestReport Interface overloaded attribute, returns number of Errors reported for this job as int.
        """
        return self.__error_count

    @property
    def exception_count(self):
        """AlgoTestReport Interface overloaded attribute, returns number of Exceptions reported for this job as int.
        """
        return self.__exception_count

    @property
    def crash_count(self):
        """AlgoTestReport Interface overloaded attribute, return number of Exceptions reported for this job as int.
        """
        return self.__crash_count

    @property
    def incidents(self):
        """AlgoTestReport Interface overloaded attribute, returns number of Crashes reported for this job as int.
        """
        return self.__incidents


"""
CHANGE LOG:
-----------
$Log: runtime.py  $
Revision 1.2 2020/03/31 09:24:01CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:34:09CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/val/project.pj
"""
