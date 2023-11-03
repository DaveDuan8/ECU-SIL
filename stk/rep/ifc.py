"""
stk/rep/ifc.py
--------------

**Interface Module for the AlgoTestReport**

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.6 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/07/22 15:54:03CEST $
"""


# Classes ----------------------------------------------------------------------
# classes are pure attribute interface classes,
# not planned to provide any methods here
# pylint: disable=R0903
class TestSuite(object):
    """
    **This is the TestSuite Interface between different stk packages.**

    All needed TestSuite Information is stored inside this class,
    and can be used as data exchange between following Classes:

    - `AlgoTestReport`
    - (not used currently)

    :author:        Robert Hecker
    :date:          09.10.2012
    """

    def __init__(self):
        self.name = ""
        """
        :ivar: TestSuite name (same as in DOORS)
        :type: str
        """

        self.id = ""
        """
        :ivar: TestRunView ID from DOORS.
               Format: <Project>_yyyy_CWxx_<Reason>_L3
        :type: str
        """

        self.description = ""
        """
        :ivar: TestSuite Description (same as in DOORS)
        :type: str
        """

        self.project = ""
        """
        :ivar: Project Name of TestObject
        :type: str
        """

        self.checkpoint = ""
        """
        :ivar: AlgoCheckpoint which is used in this TestSuite
        :type: str
        """

        self.date = ""
        """
        :ivar: Date, when TestSuite was created.
        :type: str
        """

        self.test_runs = []
        """
        :ivar: TestRuns which are connected to this TestSuite.
        :type: `TestRun`
        """


class TestRun(object):
    """
    **This is the Testrun Interface between different stk packages.**

    All needed TestRun Information is stored inside this class,
    and can be used as data exchange between following Classes:

    - `AlgoTestReport`
    - `val.testrun.TestRun`

    :author:        Robert Hecker
    :date:          09.10.2012
    """
    # this interface class has more than 7 instance attributes
    # pylint: disable=R0902
    def __init__(self):
        self.name = ""
        """
        :ivar: TestRun name (same as in DOORS)
        :type: str
        """

        self.id = ""
        """
        :ivar: ValDB internal TestRun ID
        :type: str
        """

        self.test_type = "performance"
        """
        :ivar: test type of this TestRun like 'performance', 'functional'
        :type: str
        """

        self.description = ""
        """
        :ivar: TestRun Description (same as in DOORS)
        :type: str
        """

        self.project = ""
        """
        :ivar: Project Name of TestObject, e.g. SMFC4B0
        :type: str
        """

        self.locked = ""
        """
        :ivar: status of testrun resulting in draft state of document - False: unlocked in db -> DRAFT status
        :type: bool
        """

        self.checkpoint = ""
        """
        :ivar: ComponentCheckpoint which is used in this TestRun
        :type: str
        """

        self.add_info = ""
        """
        :ivar: Additional info (e.g. 'Part 1', 'for SW nnn.xx') about the checkpoint printed on top page
        :type: str
        """

        self.user_account = ""
        """
        :ivar: account of user who executed the TestRun
        :type: str
        """

        self.user_name = ""
        """
        :ivar: name of user who executed the TestRun, not used in rep as customer should not call executer directly
        :type: str
        """

        self.remarks = ""
        """
        :ivar: testers remarks for the TestRun, printed in overview table of report
        :type: str
        """

        self.collection = ""
        """
        :ivar: Collection/BPL file name which is used in this TestRun, collection name with checkpoint
        :type: str
        """

        self.processed_files = 0
        """
        :ivar: Number of processed files in this TestRun, unique recordings
        :type: int
        """

        self.processed_time = ""
        """
        :ivar: Needed Processing time to execute this TestRun, unique recordings
        :type: str <hour:minute:second>
        """

        self.processed_distance = 0
        """
        :ivar: Processed distance inside the playlist, unique recordings
        :type: str <km>
        """

        self.test_cases = []
        """
        :ivar: TestCases connected to this TestRun.
        :type: `TestCase`
        """

        self.runtime_details = []
        """
        :ivar: list of HPC jobs used to create this TestRun
        :type: [`RuntimeJob`,...]
        """

        self.component = ""
        """
        :ivar: component tested in testrun selected from ValDb component table
        :type: str
        """

        self.sim_name = ""
        """
        :ivar: name of executed simulation setup/config, e.g. sim_all, sim_<fct>, config file name or free text
        :type: str
        """

        self.sim_version = ""
        """
        :ivar: version of the used simulation config / system
        :type: str
        """

        self.val_sw_version = ""
        """
        :ivar: version of the validation sw used for the test
        :type: str
        """


class TestCase(object):
    """
    **This is the Testcase Interface between different stk packages.**

    All needed TestCase Information is stored inside this class,
    and can be used as data exchange between following Classes:

    - `AlgoTestReport`
    - `val.results.ValTestCase`

    :author:        Robert Hecker
    :date:          09.10.2012
    """
    # this interface class has more than 7 instance attributes
    # pylint: disable=R0902
    def __init__(self):

        self.name = ""
        """
        :ivar: Testcase name (as stored in DOORS)
        :type: str
        """

        self.id = ""
        """
        :ivar: Testcase Identifier (as stored in DOORS)
               Format <PRJ acronym>_TC_###_###
        :type: str like ACC_TC_001_003
        """

        self.description = ""
        """
        :ivar: Testcase Description (as stored in DOORS)
        :type: str
        """

        self.doors_url = ""
        """
        :ivar: URL of testcase in doors
        :type: str
        """

        self.collection = ""
        """
        :ivar: used collection/playlist for this Testcase
        :type: str
        """

        self.test_result = ""
        """
        :ivar: calculated result over all test steps like PASSED, FAILED
        :type: str
        """

        self.summery_plots = []
        """
        :ivar: list of plots for detailed summery report
        :type: list
        """

        self.test_steps = []
        """
        :ivar: all connected Test Steps to this TestCase.
        :type: `TestStep`
        """

        self.total_dist = 0
        """
        :ivar: total distance in km driven for this test case
        :type: str
        """

        self.total_time = 0
        """
        :ivar: total time in Seconds driven for this test case
        :type: int
        """


class TestStep(object):
    """
    **This is the Teststep Interface between different stk packages.**

    All needed Teststep Information is stored inside this class,
    and can be used as data exchange between following Classes:

    - `AlgoTestReport`
    - `val.results.ValTestStep`
    - `val.results.ValResult`

    :author:        Robert Hecker
    :date:          09.10.2012
    """
    # this interface class has more than 7 instance attributes
    # pylint: disable=R0902
    PASSED = 'PASSED'
    """
    :cvar: Predefined test_result (passed)
    :type: str
    """

    FAILED = 'FAILED'
    """
    :cvar: Predefined test_result (failed)
    :type: str
    """

    SUSPECT = 'TO BE VERIFIED'
    """
    :cvar: Predefined test_result (to be verified), DEPRECATED Mar.2014, not used in assmt.py since 08.2013
    :type: str
    """

    INVESTIGATE = "Investigate"
    """
    :cvar: Predefined test_result (investigate)
    :type: str
    """

    NOT_ASSESSED = "Not Assessed"
    """
    :cvar: Predefined test_result (not assessed)
    :type: str
    """

    def __init__(self):
        self.name = ""
        """
        :ivar: human readable name of the teststep
        :type: str
        """

        self.id = ""
        """
        :ivar: Unique Identifier (as stored in DOORS)
               Format: <PRJ acronym>_TC_###_###-##
        :type: str
        """

        self.doors_url = ""
        """
        :ivar: URL of this teststep in doors
        :type: str
        """

        self.exp_result = ""
        """
        :ivar: Expected Test Result
        :type: str
        """

        self.meas_result = ""
        """
        :ivar: Measured Test Result:
        :type: use string type, original based on
               result type ['BaseValue', 'ValueVector', 'Histogram', 'ValidationPlot'] as used in `ValResult`
        """

        self.test_result = ""
        """
        :ivar: Test Result (`PASSED`, `FAILED`, `INVESTIGATE` or 'NOT_ASSESSED')
        :type: str
        """

        self.date = ""
        """
        :ivar: date when assessment was changes last time
        :type: str
        """

        self.user_account = ""
        """
        :ivar: user account of the last assessment change
        :type: str
        """

        self.issue = ""
        """
        :ivar: issue entered for this assessment
        :type: str
        """


class RuntimeJob(object):
    """
    **This is the Runtime Interface between different stk packages.**

    All needed RunTime Details Information is stored inside this class,
    and can be used as data exchange between following Classes:

    - `AlgoTestReport`
    - `val.runtime.RuntimeJob`

    :author:        Joachim Hospes
    :date:          30.01.2014
    """
    def __init__(self):

        self.jobId = 0
        """
        :ivar: JobId HPC job run for the TestRun
        :type: int
        """

        self.error_count = 0
        """
        :ivar: number of Errors reported for this job
        :type: int
        """

        self.exception_count = 0
        """
        :ivar: number of Exceptions reported for this job
        :type: int
        """

        self.crash_count = 0
        """
        :ivar: number of Crashes reported for this job
        :type: int
        """

        self.incidents = []
        """
        :ivar: list of RunTimeLog incidents reported for this TestRun.
        :type: [`RuntimeIncident`,...]
        """


class RuntimeIncident(object):
    """
    **This is the Runtime Interface between different stk packages.**

    All needed RunTimeLog Incident Information is stored inside this class,
    and can be used as data exchange between following Classes:

    - `AlgoTestReport`
    - `val.runtime.RuntimeIncident`

    :author:        Joachim Hospes
    :date:          30.01.2014
    """
    def __init__(self):
        self.job_id = 0
        """
        :ivar: JobId from HPC where this incident was reported
        :type: int
        """

        self.task_id = 0
        """
        :ivar: TaskId from HPC of the simulation/validation task
        :type: int
        """

        self.type = ""
        """
        :ivar: type of incident ('Error', 'Exception', 'Crash')
        :type: str
        """

        self.code = 0
        """
        :ivar: incident code as reported by the claiming tool (e.g. compiler error code)
        :type: int
        """

        self.desc = ""
        """
        :ivar: description of the incident
        :type: str
        """

        self.src = ""
        """
        :ivar: source code, backtrace or other details of the incident
        :type: str
        """


"""
CHANGE LOG:
-----------
$Log: ifc.py  $
Revision 1.6 2016/07/22 15:54:03CEST Hospes, Gerd-Joachim (uidv8815) 
new fields sim version and val sw version
Revision 1.5 2016/05/09 11:00:19CEST Hospes, Gerd-Joachim (uidv8815)
add new column REMARKS to val.db and to pfd reports as new overview table row
Revision 1.4 2015/12/07 15:39:14CET Mertens, Sven (uidv7805)
removing pep8 errors
Revision 1.3 2015/12/07 14:29:24CET Mertens, Sven (uidv7805)
removing pep8 errors
Revision 1.2 2015/10/29 17:46:26CET Hospes, Gerd-Joachim (uidv8815)
add collection and sim_name to reports
- Added comments -  uidv8815 [Oct 29, 2015 5:46:26 PM CET]
Change Package : 390799:1 http://mks-psad:7002/im/viewissue?selection=390799
Revision 1.1 2015/04/23 19:05:00CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/
    04_Engineering/01_Source_Code/stk/rep/project.pj
Revision 1.7 2015/01/29 17:43:37CET Hospes, Gerd-Joachim (uidv8815)
add 'add_info' to report top page
--- Added comments ---  uidv8815 [Jan 29, 2015 5:43:38 PM CET]
Change Package : 298621:1 http://mks-psad:7002/im/viewissue?selection=298621
Revision 1.6 2014/06/22 23:07:27CEST Hospes, Gerd-Joachim (uidv8815)
sync between templates and flowables,
algo_test.report generates perf, func and regr tests
algo_test template and flowable moved to perf_test
--- Added comments ---  uidv8815 [Jun 22, 2014 11:07:27 PM CEST]
Change Package : 241732:1 http://mks-psad:7002/im/viewissue?selection=241732
Revision 1.5 2014/05/20 13:18:48CEST Hospes, Gerd-Joachim (uidv8815)
add user_account to report, based on testrun or ifc definition, update test_report
--- Added comments ---  uidv8815 [May 20, 2014 1:18:49 PM CEST]
Change Package : 233145:1 http://mks-psad:7002/im/viewissue?selection=233145
Revision 1.4 2014/05/15 13:42:57CEST Hospes, Gerd-Joachim (uidv8815)
introduce testrun.component to pdf reports
--- Added comments ---  uidv8815 [May 15, 2014 1:42:58 PM CEST]
Change Package : 233146:1 http://mks-psad:7002/im/viewissue?selection=233146
Revision 1.3 2014/05/09 17:23:36CEST Hospes, Gerd-Joachim (uidv8815)
add testrun.locked
--- Added comments ---  uidv8815 [May 9, 2014 5:23:36 PM CEST]
Change Package : 233144:2 http://mks-psad:7002/im/viewissue?selection=233144
Revision 1.2 2014/04/25 10:54:23CEST Hospes, Gerd-Joachim (uidv8815)
doors_url added to testcase and teststep
--- Added comments ---  uidv8815 [Apr 25, 2014 10:54:23 AM CEST]
Change Package : 227491:1 http://mks-psad:7002/im/viewissue?selection=227491
Revision 1.1 2014/04/04 17:35:27CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
    stk/rep/project.pj
Revision 1.13 2014/03/28 10:25:50CET Hecker, Robert (heckerr)
Adapted to new coding guiedlines incl. backwardcompatibility.
--- Added comments ---  heckerr [Mar 28, 2014 10:25:50 AM CET]
Change Package : 228098:1 http://mks-psad:7002/im/viewissue?selection=228098
Revision 1.12 2014/03/26 12:17:50CET Hospes, Gerd-Joachim (uidv8815)
set SUSPECT to deprecated and insert INVESTIGATE and NOT_ASSESSED, update test_report
--- Added comments ---  uidv8815 [Mar 26, 2014 12:17:50 PM CET]
Change Package : 227370:1 http://mks-psad:7002/im/viewissue?selection=227370
Revision 1.11 2014/03/12 14:07:32CET Hospes, Gerd-Joachim (uidv8815)
add TestCase.summery_plots
--- Added comments ---  uidv8815 [Mar 12, 2014 2:07:32 PM CET]
Change Package : 221503:1 http://mks-psad:7002/im/viewissue?selection=221503
Revision 1.10 2014/02/27 18:04:47CET Hospes, Gerd-Joachim (uidv8815)
remove tasks (holding number of tasks of a job) as not available on Hpc
--- Added comments ---  uidv8815 [Feb 27, 2014 6:04:48 PM CET]
Change Package : 220009:1 http://mks-psad:7002/im/viewissue?selection=220009
Revision 1.9 2014/02/20 17:44:18CET Hospes, Gerd-Joachim (uidv8815)
use new processed_<values> in pdf report
Revision 1.8 2014/02/20 15:12:28CET Hospes, Gerd-Joachim (uidv8815)
fix method name to user_account for report
--- Added comments ---  uidv8815 [Feb 20, 2014 3:12:29 PM CET]
Change Package : 220000:1 http://mks-psad:7002/im/viewissue?selection=220000
Revision 1.7 2014/02/19 11:31:17CET Hospes, Gerd-Joachim (uidv8815)
add user and date of teststep and fix test results in xlsx and pdf
--- Added comments ---  uidv8815 [Feb 19, 2014 11:31:17 AM CET]
Change Package : 220000:1 http://mks-psad:7002/im/viewissue?selection=220000
Revision 1.6 2014/02/14 14:42:58CET Hospes, Gerd-Joachim (uidv8815)
epidoc and pep8/pylint fixes
Revision 1.5 2014/02/13 17:40:34CET Hospes, Gerd-Joachim (uidv8815)
add distance and time to testcases and statistic table, fix table style and '<' handling
--- Added comments ---  uidv8815 [Feb 13, 2014 5:40:35 PM CET]
Change Package : 218178:1 http://mks-psad:7002/im/viewissue?selection=218178
Revision 1.4 2014/02/05 13:58:24CET Hospes, Gerd-Joachim (uidv8815)
chapter Test Execution Details added to report with template, flowables and tests
--- Added comments ---  uidv8815 [Feb 5, 2014 1:58:25 PM CET]
Change Package : 214928:1 http://mks-psad:7002/im/viewissue?selection=214928
Revision 1.3 2013/10/25 09:02:32CEST Hecker, Robert (heckerr)
Removed Pep8 Issues.
--- Added comments ---  heckerr [Oct 25, 2013 9:02:33 AM CEST]
Change Package : 202843:1 http://mks-psad:7002/im/viewissue?selection=202843
"""
