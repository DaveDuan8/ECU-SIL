"""
stk/val/runtime.py
------------------

Subpackage for Handling Runtime incidents providing:

  - `RuntimeJob`
  - `RuntimeIncident`

:org:           Continental AG
:author:        Joachim Hospes

:version:       $Revision: 1.4 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2016/04/01 08:36:28CEST $
"""
# - import STK modules ------------------------------------------------------------------------------------------------
from stk.db.db_common import BaseDB
from stk.util.logger import Logger
from stk.util.helper import arg_trans

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
        opts = arg_trans((('node', 'LUSS010'), ('jobid', 0), ('taskid', 0),
                          'errtype', 'errcode', 'description', 'source'), *args, **kwargs)
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

    def LoadHpcIncidents(self):  # pylint: disable=C0103
        """Load all incidents with given JobId from HPC error Db
        """
        # Connect to the Hpc Error DB
        with BaseDB('HPC') as hpc:
            for i in hpc.execute("SELECT HPCTASKID, TYPENAME, CODE, DESCR, SRC "
                                 "FROM HPC_NODE INNER JOIN HPC_JOB USING(NODEID) "
                                 "INNER JOIN HPC_TASK USING(JOBID) "
                                 "INNER JOIN HPC_ERRORS USING(TASKID) "
                                 "INNER JOIN HPC_ERRTYPE USING(TYPEID) "
                                 "WHERE NODENAME = :node AND HPCJOBID = :job", node=self.__node, job=self.__jobid):
                self.__incidents.append(RuntimeIncident(self.__node, self.__jobid, i[0], i[1], i[2], i[3], i[4]))

        self.__error_count = self.CountIncidents(TYPE_ERROR)
        self.__exception_count = self.CountIncidents(TYPE_EXCEPTION)
        self.__crash_count = self.CountIncidents(TYPE_CRASH)

    def AddIncidents(self, incident_list):  # pylint: disable=C0103
        """
        **add list of incidents to the runtime job**
        and count occurrence of errors, exceptions and crashes

        job id needs to be equal to runtime job id for all incidents

        :param incident_list: list of incident dicts as returned by `HpcErrorDB`
        :type incident_list: [`RuntimeIncident`,...]
        """
        for incident in incident_list:
            if incident.job_id == self.__jobid:
                self.__incidents.append(RuntimeIncident(incident.node,
                                                        incident.job_id,
                                                        incident.task_id,
                                                        incident.type,
                                                        incident.code,
                                                        incident.desc,
                                                        incident.src))
            else:
                self._log.error('RuntimeJob list inconsistent, trying to add incident with different job id!! \n'
                                ' expct JobId: %s  added: %s' % (self.__jobid, incident.job_id))
                return False

        self.__error_count = self.CountIncidents(TYPE_ERROR)
        self.__exception_count = self.CountIncidents(TYPE_EXCEPTION)
        self.__crash_count = self.CountIncidents(TYPE_CRASH)
        return True

    def GetAllIncidents(self, itype=None):  # pylint: disable=C0103
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

    def CountIncidents(self, itype=None):  # pylint: disable=C0103
        """
        count the incidents for a given job id and opt. type

        :param itype: type of incident like 'Error', 'Crash',...
        :type itype: str
        :return: number of incidents
        :rtype: int
        """
        return len(self.GetAllIncidents(itype))

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
Revision 1.4 2016/04/01 08:36:28CEST Mertens, Sven (uidv7805) 
fix type
Revision 1.3 2016/04/01 08:18:28CEST Mertens, Sven (uidv7805)
we have some more types
Revision 1.2 2016/03/31 18:04:26CEST Mertens, Sven (uidv7805)
we don't need HPC interface
Revision 1.1 2015/04/23 19:05:39CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/val/project.pj
Revision 1.9 2015/03/09 08:29:58CET Mertens, Sven (uidv7805)
changing logger,
docu fixes
--- Added comments ---  uidv7805 [Mar 9, 2015 8:29:58 AM CET]
Change Package : 314290:1 http://mks-psad:7002/im/viewissue?selection=314290
Revision 1.8 2015/01/20 08:25:49CET Mertens, Sven (uidv7805)
changing to db submodule
Revision 1.7 2014/12/01 15:10:09CET Hospes, Gerd-Joachim (uidv8815)
fix check in AddIncident, add nightly test for it
--- Added comments ---  uidv8815 [Dec 1, 2014 3:10:10 PM CET]
Change Package : 286537:1 http://mks-psad:7002/im/viewissue?selection=286537
Revision 1.6 2014/08/04 15:14:14CEST Mertens, Sven (uidv7805)
adaptation for HPC head node
--- Added comments ---  uidv7805 [Aug 4, 2014 3:14:15 PM CEST]
Change Package : 253438:1 http://mks-psad:7002/im/viewissue?selection=253438
Revision 1.5 2014/02/27 18:06:39CET Hospes, Gerd-Joachim (uidv8815)
add LoadHpcIncidents, remove task number and cleanup
--- Added comments ---  uidv8815 [Feb 27, 2014 6:06:40 PM CET]
Change Package : 220009:1 http://mks-psad:7002/im/viewissue?selection=220009
Revision 1.4 2014/02/14 14:42:56CET Hospes, Gerd-Joachim (uidv8815)
epidoc and pep8/pylint fixes
--- Added comments ---  uidv8815 [Feb 14, 2014 2:42:57 PM CET]
Change Package : 218178:2 http://mks-psad:7002/im/viewissue?selection=218178
Revision 1.3 2014/02/06 16:31:13CET Hospes, Gerd-Joachim (uidv8815)
fix counters
--- Added comments ---  uidv8815 [Feb 6, 2014 4:31:13 PM CET]
Change Package : 214928:1 http://mks-psad:7002/im/viewissue?selection=214928
Revision 1.2 2014/02/05 18:20:00CET Hospes, Gerd-Joachim (uidv8815)
fix import temporarily
Revision 1.1 2014/02/05 14:31:35CET Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project
/nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/val/project.pj
"""
