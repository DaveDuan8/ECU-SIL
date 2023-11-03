"""
stk/val/testrun.py
-------------------

    Testrun API class and Testrun Manager implementation

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.12.1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/02/02 15:31:45CET $
"""
# - imports -----------------------------------------------------------------------------------------------------------
from os import environ
from sys import _getframe

from stk.util.logger import Logger
import stk.valf.db_connector as db_con
from stk.db.gbl import gbl as db_gbl
from stk.db.val import val as db_val
from stk.db.gbl import GblTestType

from stk.db.val.val import COL_NAME_TR_ID, COL_NAME_TR_NAME, COL_NAME_TR_CHECKPOINT, COL_NAME_TR_DESC, \
    COL_NAME_TR_PARENT, COL_NAME_TR_TYPE_ID, COL_NAME_TR_USERID, COL_NAME_TR_COLL_NAME, COL_NAME_TR_CMPID, \
    COL_NAME_RES_RESDESC_ID, COL_NAME_TR_PID, COL_NAME_JOBS_JBID, COL_NAME_JOBS_HPCJOBID, TRUN_LOCK_VALUE, \
    COL_NAME_TR_TTID, COL_NAME_TR_ADD_INFO, COL_NAME_TR_SIM_NAME, COL_NAME_TR_SIM_VERSION, COL_NAME_TR_VAL_SW_VERSION, \
    COL_NAME_TR_REMARKS
from stk.db.gbl.gbl import COL_NAME_USER_LOGIN, COL_NAME_VO_TYPE_NAME, COL_NAME_USER_NAME
from stk.valf.signal_defs import DBVAL, DBGBL

from stk.val.results import ValSaveLoadLevel, ValTestcase
from stk.val.runtime import RuntimeJob
from stk.valf import BaseComponentInterface as bci
from stk.valf import signal_defs as sd
from stk.util.helper import sec_to_hms_string, deprecated

# Defines ---------------------------------------------------------------------
NEW_TRUN_CFG_PORT_NAME = 'testruns'
TESTRUN_PORT_NAME = 'trun'

# Classes ---------------------------------------------------------------------


class TestRun(object):  # pylint: disable=R0902,R0904
    """ Testrun Class supporting the interface to the result database """

    def __init__(self, name=None, desc=None, checkpoint=None, user=None,  # pylint: disable=R0913
                 obs_name=None, test_collection=None, parent=None, replace=False, proj_name=None, component=None):
        """
        constructor of the testrun class

        :param name: Name of the Testrun
        :type name: str
        :param desc: Description of the Testrun
        :type desc: str
        :param checkpoint: Software Release checkpont from MKS
        :type checkpoint: str
        :param user: Testers login name
        :type user: str
        :param obs_name: Observer name
        :type obs_name: str
        :param test_collection: Collection used to run the tests
        :type test_collection: str
        :param parent: Parent TestRun Id
        :type parent: int
        :param replace: flag to delete the exisiting testrun
        :type replace: bool
        :param proj_name: Project name
        :type proj_name: str
        :param component: Component name
        :type component: str
        """
        self.__name = name
        self.__desc = desc
        self.__checkpoint = checkpoint
        self.__user = user
        self.__user_id = None
        self.__obs_name = obs_name
        self.__obs_type_id = None
        self.__test_collection = test_collection
        self.__parent_id = parent
        self.__child_tr = []
        self.__tr_id = None
        self.__test_type = None
        self.__testcase_list = []
        self.__replace = replace
        self.__proj_name = proj_name
        self.__pid = None
        self.__user_name = None
        self.__processed_files = None
        self.__processed_time = None
        self.__processed_distance = None
        self.__runtime_jobs = []
        self.__lock = False
        self.__component = None
        self.__add_info = ""
        self.__sim_name = ""
        self.__sim_version = ""
        self.__val_sw_version = ""
        self.__remarks = ""
        if component is not None:
            self.__component = component.lower()
        self._log = Logger(self.__class__.__name__)

    def __str__(self):
        """
        return string text summary of the testrun
        """
        txt = "Testrun: " + str(self.__name) + \
              " CP: " + str(self.__checkpoint)
        return txt

    def Load(self,  # pylint: disable=C0103,R0912,R0913,R0914,R0915
             dbi_val,
             dbi_gbl,
             dbi_cat,
             testrun_id=None,
             level=ValSaveLoadLevel.VAL_DB_LEVEL_BASIC):
        """ Load the testrun from database

        :param dbi_val: Validation Database interface
        :param dbi_gbl: Global Database interface
        :param dbi_cat: Catalog Database interface
        :param testrun_id: Testrun Identifier
        :param level: Database load/store level
        """
        if not issubclass(dbi_val.__class__, db_val.BaseValResDB):
            self._log.error("VAL Database interface undefined")
            return False

        if not issubclass(dbi_gbl.__class__, db_gbl.BaseGblDB):
            self._log.error("GBL Database interface undefined")
            return False

        if self.__tr_id is not None:
            testrun_id = self.__tr_id

        # check if testrun exists
        if testrun_id is None:
            if self.__proj_name is not None:
                self.__pid = dbi_gbl.get_project_id(self.__proj_name)
                if self.__pid is None:
                    raise StandardError("Project Name %s doesn't exist in the database" % self.__proj_name)
            else:
                raise StandardError("Project name is mandatory")
        tr_rec = dbi_val.get_testrun(self.__name, self.__checkpoint,
                                     self.__obs_type_id, self.__user_id,
                                     testrun_id, self.__parent_id, self.__pid)

        if COL_NAME_TR_ID in tr_rec:
            self.__tr_id = tr_rec[COL_NAME_TR_ID]
            self.__name = tr_rec[COL_NAME_TR_NAME]
            self.__desc = tr_rec[COL_NAME_TR_DESC]
            self.__checkpoint = tr_rec[COL_NAME_TR_CHECKPOINT]
            self.__user_id = tr_rec[COL_NAME_TR_USERID]
            self.__obs_type_id = tr_rec[COL_NAME_TR_TYPE_ID]
            self.__test_collection = tr_rec[COL_NAME_TR_COLL_NAME]
            self.__lock = int(dbi_val.get_testrun_lock(tr_id=self.__tr_id)) == TRUN_LOCK_VALUE
            self.__parent_id = tr_rec[COL_NAME_TR_PARENT]
            self.__pid = tr_rec[COL_NAME_TR_PID]
            # for following settings: declared value updated only if column is available and not None
            if tr_rec.get(COL_NAME_TR_CMPID) is not None:
                self.__component = dbi_gbl.get_component_name(tr_rec[COL_NAME_TR_CMPID])
            if tr_rec.get(COL_NAME_TR_TTID) is not None:
                self.__test_type = dbi_gbl.get_test_type_name(tr_rec[COL_NAME_TR_TTID])
            if tr_rec.get(COL_NAME_TR_ADD_INFO) is not None:
                self.__add_info = tr_rec.get(COL_NAME_TR_ADD_INFO)
            if tr_rec.get(COL_NAME_TR_SIM_NAME) is not None:
                self.__sim_name = tr_rec.get(COL_NAME_TR_SIM_NAME)
            if tr_rec.get(COL_NAME_TR_SIM_VERSION) is not None:
                self.__sim_version = tr_rec.get(COL_NAME_TR_SIM_VERSION)
            if tr_rec.get(COL_NAME_TR_VAL_SW_VERSION) is not None:
                self.__val_sw_version = tr_rec.get(COL_NAME_TR_VAL_SW_VERSION)
            if tr_rec.get(COL_NAME_TR_REMARKS) is not None:
                self.__remarks = tr_rec.get(COL_NAME_TR_REMARKS)
            self.__proj_name = dbi_gbl.get_project_name(self.__pid)

            # Load Runtime JobIds
            trun_joblist = dbi_val.get_hpc_jobs_for_testrun(self.__tr_id)
            for trun_job in trun_joblist:
                hpcjobid = dbi_val.get_job(jbid=trun_job[COL_NAME_JOBS_JBID])[COL_NAME_JOBS_HPCJOBID]
                self.__runtime_jobs.append(RuntimeJob("LUSS010", hpcjobid))

            rec = dbi_gbl.get_val_observer_type(type_id=self.__obs_type_id)

            if COL_NAME_VO_TYPE_NAME in rec:
                self.__obs_name = rec[COL_NAME_VO_TYPE_NAME]

            rec = dbi_gbl.get_user(user_id=self.__user_id)
            if COL_NAME_USER_LOGIN in rec:
                self.__user = rec[COL_NAME_USER_LOGIN]
                self.__user_name = rec[COL_NAME_USER_NAME]
            self.__child_tr = []
            for ctr_id in dbi_val.get_testrun_ids_for_parent(self.__tr_id):
                trun = TestRun()
                if trun.Load(dbi_val, dbi_gbl, dbi_cat, ctr_id) is True:
                    self.__child_tr.append(trun)
                else:
                    self._log.error("Testrun could not be loaded with all child testruns")
                    return False

            if level & ValSaveLoadLevel.VAL_DB_LEVEL_2:
                self.__testcase_list = []
                rd_info = dbi_val.get_result_descriptor_info_for_testrun(self.__name, self.__checkpoint,
                                                                         ValTestcase.TESTCASE_TYPE)

                for item in rd_info:
                    rd_id = item[COL_NAME_RES_RESDESC_ID]
                    tcase = ValTestcase()
                    if tcase.Load(dbi_val, dbi_gbl, dbi_cat, self.__tr_id,
                                  level=level,
                                  rd_id=rd_id) is True:
                        self.__testcase_list.append(tcase)

                self.__processed_distance = dbi_val.get_test_run_time_distance(self.__tr_id,
                                                                               ValTestcase.MEAS_DIST_PROCESS)
                if self.__processed_distance is not None:
                    self.__processed_files = len(dbi_val.get_test_run_time_distance
                                                 (self.__tr_id, ValTestcase.MEAS_DIST_PROCESS, sum=False))
                else:
                    self.__processed_files = None

                self.__processed_time = dbi_val.get_test_run_time_distance(self.__tr_id, ValTestcase.MEAS_TIME_PROCESS)

#             # store Runtime JobIds,
#             # details of job incidents can be loaded with RuntimeJob.LoadHpcIncidents()
#             for job in joblist_from_db:
#                 self.AddRuntimeJob(job)
        else:
            self._log.error("Testrun with give id does not exist")
            return False

        return True

    def Save(self,  # pylint: disable=C0103,R0912,R0915
             dbi_val, dbi_gbl, parent_id=None, level=ValSaveLoadLevel.VAL_DB_LEVEL_BASIC):
        """ Save the Testrun to the data using the given load/store level

        :param dbi_val: Validation Database interface
        :param dbi_gbl: Global Database interface
        :param parent_id: ID of parent
        :param level: Database load/store level
        """
        if not issubclass(dbi_val.__class__, db_val.BaseValResDB):
            self._log.error("VAL Database interface undefined")
            return False

        if not issubclass(dbi_gbl.__class__, db_gbl.BaseGblDB):
            self._log.error("GBL Database interface undefined")
            return False

        # load oberserver type and user identifiers
        if self.__obs_type_id is None:
            self.__obs_type_id = dbi_gbl.get_val_observer_type_id(self.__obs_name)
            if self.__obs_type_id is None:
                self._log.error("Observer Type does not exist in the GBL database. Contact the DB Admin")
                return False

        if self.__user_id is None:
            if self.__user is None:
                self.__user = environ["USERNAME"]
            self.__user_id = dbi_gbl.current_gbluserid
            if self.__user_id is None:
                self._log.error("The user id for the Windows login name %s is not defined in the global users "
                                "(GBL_USERS) table of the Val Result Database!" % self.__user)
                return False

        if self.__desc is None or self.__desc == "":
            self.__desc = str(self)

        if self.__component is not None:
            cmpid = dbi_gbl.get_component_id(self.__component)
            if cmpid is None:
                self._log.warning("Component for testrun is not Register in Database.")
        else:
            cmpid = None

        if self.__test_type is not None:
            ttypeiid = dbi_gbl.get_test_typeid(self.__test_type)
            if ttypeiid is None:
                self._log.warning("Test is not Registered in Database.")
        else:
            ttypeiid = None

        if self.__proj_name is not None:
            self.__pid = dbi_gbl.get_project_id(self.__proj_name)
            if self.__pid is None:
                raise StandardError("Project Name %s doesn't exist in the database" % self.__proj_name)

        else:
            # Commented Additional function to support ARS projects which is not valid MFC
            # for project_name in dbi_gbl.GetAllProjectName():
            # if project_name.upper() in self.__name.upper():
            #     self.__proj_name = project_name
            #     break
            # if self.__proj_name is not None:
            #     self.__pid = dbi_gbl.GetProjectId(self.__proj_name)
            # else:
            #     raise StandardError("Project Name is mandatory for TestRun e.g. ARS400, MFC400")
            raise StandardError("Project Name is mandatory for TestRun e.g. ARS400, MFC400")

        tr_rec = {COL_NAME_TR_NAME: self.__name,
                  COL_NAME_TR_DESC: self.__desc,
                  COL_NAME_TR_CHECKPOINT: self.__checkpoint,
                  COL_NAME_TR_COLL_NAME: self.__test_collection,
                  COL_NAME_TR_USERID: self.__user_id,
                  COL_NAME_TR_TYPE_ID: self.__obs_type_id,
                  COL_NAME_TR_PID: self.__pid,
                  COL_NAME_TR_CMPID: cmpid,
                  COL_NAME_TR_TTID: ttypeiid,
                  COL_NAME_TR_ADD_INFO: self.__add_info,
                  COL_NAME_TR_SIM_NAME: self.__sim_name,
                  COL_NAME_TR_SIM_VERSION: self.__sim_version,
                  COL_NAME_TR_VAL_SW_VERSION: self.__val_sw_version,
                  COL_NAME_TR_REMARKS: self.__remarks
                  }

        # overwrite parentid --> parent might be new
        if parent_id is not None:
            tr_rec[COL_NAME_TR_PARENT] = parent_id
            self.__parent_id = parent_id

        elif self.__parent_id is not None:
            tr_rec[COL_NAME_TR_PARENT] = self.__parent_id

        self.__tr_id = dbi_val.add_testrun(tr_rec, self.__replace)
        # save Runtime JobIds
        for job in self.__runtime_jobs:
            serverid = dbi_gbl.get_hpc_server_id()  # Get Default Server Id of the HPC Cluster
            dbi_val.add_hpc_job_for_testrun(self.__tr_id, dbi_val.add_job(serverid, job.jobid))

            # save all child testrun recursive
        for trun in self.__child_tr:
            if self.GetProjectName() == trun.GetProjectName():
                trun.Save(dbi_val, dbi_gbl, self.__tr_id)
            else:
                raise StandardError("Child testrun project must same as its Parent Testrun")

        if level & ValSaveLoadLevel.VAL_DB_LEVEL_4:
            # save all test cases with their test steps, events, results, ...
            for tc in self.test_cases:
                tc.Save(dbi_val, dbi_gbl, self.__tr_id, self.__obs_name, level)

        dbi_val.commit()
        return True

    @deprecated("update_testrun_lock")
    def Upate(self, dbi_val, dbi_gbl, level=ValSaveLoadLevel.VAL_DB_LEVEL_BASIC):
        """
        :deprecated: only Testrun lock is supported, use ``update_testrun_lock`` instead

        """
        if self.__lock:
            dbi_val.update_testrun_lock(tr_id=self.__tr_id, lock=self.__lock)
        else:
            dbi_val.update_testrun_lock(tr_id=self.__tr_id, unlock=not self.__lock)
        for trun in self.__child_tr:
            if self.GetProjectName() == trun.GetProjectName():
                trun.Upate(dbi_val, dbi_gbl, level=level)
        return True

    def AddChildTestRun(self, child_object):  # pylint: disable=C0103
        """Add a child testrun

        :param child_object: TODO
        """
        self.__child_tr.append(child_object)

    def AddTestCase(self, testcase):  # pylint: disable=C0103
        """Add test cases

        :param testcase: in a list
        """

        if isinstance(testcase, ValTestcase):
            self.__testcase_list.append(testcase)

    def AddRuntimeJob(self, node="LUSS010", job=None):  # pylint: disable=C0103
        """Add the Runtime job
        containing the base information about one job executed to get the results,
        Runtime job incidents have to be loaded separately by `RuntimJob.LoadHpcIncidents()` for each job

        :param node: node name
        :param job: one RuntimeJob or just its JobId of this testrun
        :type job:  `RuntimeJob` or integer (hpc JobId)
        """
        if type(job) == RuntimeJob:
            if self.GetRuntimeJobs(node, job.jobdid) is None:  # Avoid duplication
                self.__runtime_jobs.append(job)
        elif type(job) == int:
            if self.GetRuntimeJobs(node, job) is None:  # Avoid duplication
                self.__runtime_jobs.append(RuntimeJob(node, job))
        return

    def GetRuntimeJobs(self, node="LUSS010", jobid=None):  # pylint: disable=C0103
        """Get job executed for the testrun

        :param node:
        :param jobid:
        """
        if jobid is None:
            return self.__runtime_jobs
        else:
            for runtime_job in self.__runtime_jobs:
                if jobid == runtime_job.jobid and runtime_job.node == node:
                    return runtime_job
            return None

    def GetChildTestRuns(self):  # pylint: disable=C0103
        """Get the list of child testruns
        """
        return self.__child_tr

    def GetTestcases(self, inc_child_tr=True):  # pylint: disable=C0103
        """Get the list of child testruns

        :param inc_child_tr:
        """
        if inc_child_tr:
            tc_list = []
            for tcase in self.__testcase_list:
                tc_list.append(tcase)
            for ctr in self.GetChildTestRuns():
                for tcase in ctr.GetTestcases():
                    tc_list.append(tcase)
            return tc_list

        else:
            return self.__testcase_list

    def GetTestCase(self, name=None, spectag=None):  # pylint: disable=C0103
        """Get TestCase by Name or TestCaseIdentifier/DOORS Id

        :param name: TestCase Name
        :type name: String
        :param spectag:
        :return: Instance of ValTestCase
        """
        for tcase in self.__testcase_list:
            if name is not None and spectag is None:
                if tcase.GetName() == name:
                    return tcase
            elif name is None and spectag is not None:
                if tcase.GetSpecTag() == spectag:
                    return tcase
            elif name is not None and spectag is not None:
                if tcase.GetName() == name and tcase.GetSpecTag() == spectag:
                    return tcase
        return None

    def GetId(self):  # pylint: disable=C0103
        """Return the Testrun ID of the DB
        An error log will be generated, if it is not set
        """
        if self.__tr_id is None:
            self._log.error("Testrun ID is None")
        return self.__tr_id

    def GetTestType(self):  # pylint: disable=C0103
        """ Return the type of the executed test like 'performance', 'functional'
        default return is 'performance' if not set
        """
        if self.__test_type is None:
            return GblTestType.TYPE_PERFORMANCE
        return self.__test_type

    def GetName(self):  # pylint: disable=C0103
        """
        Return the Testrun Name of the DB
        An error log will be generated, if it is not set
        """
        if self.__name is None:
            self._log.error("Testrun Name is None")
        return self.__name

    def GetCheckpoint(self):  # pylint: disable=C0103
        """
        Return the Testrun checkpoint label
        An error log will be generated, if it is not set
        """
        if self.__checkpoint is None:
            self._log.error("Testrun Name is None")
        return self.__checkpoint

    def GetCollectionName(self):  # pylint: disable=C0103
        """
        Return the Testrun Collection Name
        An error log will be generated, if it is not set
        """
        if self.__test_collection is None:
            self._log.error("Collection Name is None")
        return self.__test_collection

    def GetObserverName(self):  # pylint: disable=C0103
        """
        Return the Testrun Observer Name
        An error log will be generated, if it is not set
        """
        if self.__obs_name is None:
            self._log.error("Observer Name is None")
        return self.__obs_name

    def SetTestType(self, testtype):  # pylint: disable=C0103
        """Set Testrun  type e.g. 'performance' 'functional'

        :param testtype:
        """
        self.__test_type = testtype

    def SetReplace(self, replace):  # pylint: disable=C0103
        """Set Testrun  replace flag of the test run

        :param replace:
        """
        self.__replace = replace

    def GetProjectName(self):  # pylint: disable=C0103
        """
        Get project name of the test run
        """
        return self.__proj_name

    def GetComponentName(self):  # pylint: disable=C0103
        """
        Get component name
        """
        return str(self.__component).upper()

    def GetUserAccount(self):  # pylint: disable=C0103
        """
        Get the account of the user executing the TestRun
        """
        return self.__user

    def GetDistanceProcess(self):  # pylint: disable=C0103
        """
        Get Distance processed by test run

        :return: Total distance in Kilometer
        :rtype:  int
        """
        if self.__processed_distance is None:
            self._CalulateFromTestCases()

        return self.__processed_distance

    def GetTimeProcess(self):  # pylint: disable=C0103
        """
        Get Time processed by test run

        :return: Total Time in Second, Duration with format HH:MM:SS
        :rtype:  int, string
        """
        if self.__processed_time is None:
            self._CalulateFromTestCases()

        return self.__processed_time, sec_to_hms_string(self.__processed_time)

    def GetFileProcessed(self):  # pylint: disable=C0103
        """
        Get No. of files processed by test run

        :return: Total no. of files
        :rtype:  int
        """
        if self.__processed_files is None:
            self._CalulateFromTestCases()

        return self.__processed_files

    def IsLocked(self):  # pylint: disable=C0103
        """
        Get Testrun Lock status

        :return: Lock status of testrun with boolean flag
                 True  ==> Testrun is locked
                 False ==> Testrun is unlocked
        :rtype:  bool
        """
        return self.__lock

    def Lock(self, recursive=True):  # pylint: disable=C0103
        """
        Lock testrun

        :param recursive: Apply lock recursively to all child testruns below given testrun
        :type recursive: bool
        """

        if recursive:
            for child in self.__child_tr:
                child.Lock(recursive=recursive)
        self.__lock = True

    def Unlock(self, recursive=True):  # pylint: disable=C0103
        """
        Unlock testrun

        :param recursive: Remove lock recursively from all child testruns below given testrun
        :type recursive: bool
        """
        if recursive:
            for child in self.__child_tr:
                child.Unlock(recursive=recursive)
        self.__lock = False

    def _CalulateFromTestCases(self):  # pylint: disable=C0103
        """
        Calculate testrun statistics from testcases object.
        This function is called for unsaved testrun
        """
        meas_done = []
        self.__processed_distance = 0.0
        self.__processed_time = 0.0
        for tcc in self.__testcase_list:
            measids = tcc.GetMeasurementIds()
            for measid in measids:
                if measid not in meas_done:
                    meas_done.append(measid)
                    dist = tcc.GetMeasDistanceProcess(measid)
                    time, _ = tcc.GetMeasTimeProcess(measid)
                    if dist is not None:
                        self.__processed_distance += dist
                        self.__processed_time += time

        self.__processed_files = len(meas_done)

    @property
    def name(self):
        """AlgoTestReport Interface overloaded attribute, returning Name of Testrun as string.
        """
        return self.GetName()

    @property
    def checkpoint(self):
        """AlgoTestReport Interface overloaded attribute, returning Checkpoint Name as string.
        """
        return self.GetCheckpoint()

    @property
    def description(self):
        """AlgoTestReport Interface overloaded attribute, returning Description of the Testrun as string.
        """
        return self.__desc

    @property
    def project(self):
        """AlgoTestReport Interface overloaded attribute, returning ProjectName as string.
        """
        return self.GetProjectName()

    @property
    def component(self):
        """AlgoTestReport Interface overloaded attribute, returning Component tested in TestRun, valid strings in
        ValDb as string.
        """
        return str(self.__component).upper()

    @property
    def user_account(self):
        """AlgoTestReport Interface overloaded attribute, returning user account executed the TestRun as string.
        """
        return self.GetUserAccount()

    @property
    def user_name(self):
        """AlgoTestReport Interface overloaded attribute, returning user name executed the TestRun, not printed in
        report as string.
        """
        return self.__user_name

    @property
    def id(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returning ID of Testrun as string
        """
        return str(self.GetId())

    @property
    def test_type(self):
        """AlgoTestReport Interface overloaded attribute, returning type of test executed for this Testrun,
        e.g. 'performance', 'functional' as string.
        """
        return str(self.GetTestType())

    @property
    def collection(self):
        """AlgoTestReport Interface overloaded attribute, returning collection executed for this Testrun,

        :return: name of collection
        :rtype: str
        """
        return str(self.__test_collection)

    @property
    def locked(self):
        """AlgoTestReport Interface overloaded attribute, returning status of testrun to mark report as draft
        (locked=False) as bool.
        """
        return self.IsLocked()

    @property
    def test_cases(self):
        """AlgoTestReport Interface overloaded attribute, returning List of Testcases as list[`TestCase`,...].
        """
        return self.GetTestcases()

    @property
    def processed_distance(self):
        """AlgoTestReport Interface overloaded attribute, returning overall distance processed, unique recordings
        (measid)! as int.
        """
        return self.GetDistanceProcess()

    @property
    def processed_time(self):
        """AlgoTestReport Interface overloaded attribute, returning overall time processed, unique recordings
        (measid)! as string ("hh:mm:ss").
        """
        return self.GetTimeProcess()[1]

    @property
    def processed_files(self):
        """AlgoTestReport Interface overloaded attribute, returning overall number of unique recordings (measid)
        used as int.
        """
        return self.GetFileProcessed()

    @property
    def runtime_details(self):
        """AlgoTestReport Interface overloaded attribute, returning list of Runtime Jobs as list [`RuntimeJob`,...].
        """
        return self.__runtime_jobs

    @property
    def add_info(self):
        """AlgoTestReport Interface overloaded attribute, returning Additional Information as string.
        """
        return self.__add_info if self.__add_info is not None else ""

    @add_info.setter
    def add_info(self, add_info):
        """Set Additional Information

        :param add_info: Additional Information
        :type add_info: String
        """

        self.__add_info = add_info if add_info is not None else ""

    @property
    def sim_name(self):
        """AlgoTestReport Interface overloaded attribute, returning Simulation name as string.
        """
        return self.__sim_name if self.__sim_name is not None else ""

    @sim_name.setter
    def sim_name(self, sim_name):
        """set name of simulation, e.g. sim_all, sim_<fct>, name of cfg file or free text

        :param sim_name: simulation name
        :type  sim_name: str
        """
        self.__sim_name = sim_name if sim_name is not None else ''

    @property
    def sim_version(self):
        """AlgoTestReport Interface overloaded attribute, returning Simulation version as string.
        """
        return self.__sim_version if self.__sim_version is not None else ""

    @sim_version.setter
    def sim_version(self, sim_version):
        """set version of simulation, e.g. checkpoint label or id of sil config file or free text

        :param sim_version: simulation version
        :type  sim_version: str
        """
        self.__sim_version = sim_version if sim_version is not None else ''

    @property
    def val_sw_version(self):
        """AlgoTestReport Interface overloaded attribute, returning validation sw version as string.
        """
        return self.__val_sw_version if self.__val_sw_version is not None else ""

    @val_sw_version.setter
    def val_sw_version(self, val_sw_version):
        """set version of validation script, e.g. checkpoint label or id from mks or free text

        :param val_sw_version: validation script version as stored in configuiration management
        :type  val_sw_version: str
        """
        self.__val_sw_version = val_sw_version if val_sw_version is not None else ''

    @property
    def remarks(self):
        """AlgoTestReport Interface overloaded attribute, returning testers remarks for testrun as string.
        """
        return self.__remarks if self.__remarks is not None else ""

    @remarks.setter
    def remarks(self, remarks):
        """Set testers remarks

        :param remarks: testers remarks for testrun
        :type remarks: String
        """

        self.__remarks = remarks if remarks is not None else ""


class TestRunManager(bci):  # pylint: disable= R0902
    """TestrunManager Plugin using the Testrun Class
    """
    def __init__(self, data_manager, component_name, bus_name=["BASE_BUS"]):
        """ Contructor """
        bci.__init__(self, data_manager, component_name, bus_name, "$Revision: 1.12.1.1 $")

        # database
        self.__valresdb = None
        self.__gbldb = None
        self.__databaseobjects = None
        self.__databaseobjectsconnections = None

        # signals from Databus
        self.__checkpoint = None
        self.__checkpoint_ref = None
        self.__comp_name = None
        self.__new_testruns = None
        self.__collection_name = None
        self.__main_test_run = None
        self.__proj_name = None

    # --- Framework functions. --------------------------------------------------
    def Initialize(self):
        """ Initialize. Called once. """
        self._logger.debug(str(_getframe().f_code.co_name) + "()" + " called.")

        # get the database object list
        self.__databaseobjects = self._data_manager.get_data_port("DataBaseObjects", "DBBus#1")
        if self.__databaseobjects is None:
            self._logger.info("'DataBaseObjects' port was not set.")
        elif type(self.__databaseobjects) is list:
            # testrun observer was called before DbLinker, so we still can add needed connections
            # set the requested data base objects to the connection list
            self.__databaseobjects.append(db_gbl)
            self.__databaseobjects.append(db_val)
        return bci.RET_VAL_OK

    def PostInitialize(self):
        """ PostInitialize. Called once. """
        self._logger.debug(str(_getframe().f_code.co_name) + "()" + " called.")
        databaseobjectsconnections = self._data_manager.get_data_port(db_con.DATABASE_OBJECTS_CONN_PORT_NAME,
                                                                      "DBBus#1")
        databaseobjects = self._data_manager.get_data_port(sd.DATABASE_OBJECTS_PORT_NAME, "DBBus#1")
        if databaseobjectsconnections is not None:
            for connobject in databaseobjectsconnections:
                if connobject.ident_str == DBVAL:
                    self.__valresdb = connobject
                elif connobject.ident_str == DBGBL:
                    self.__gbldb = connobject
        elif databaseobjects is not None and type(databaseobjects) is dict:
            # use connection provided by DbLinker
            self.__valresdb = self._get_data(sd.DATABASE_OBJECTS_PORT_NAME, self._bus_name).get('val')
            self.__gbldb = self._get_data(sd.DATABASE_OBJECTS_PORT_NAME, self._bus_name).get('gbl')
        else:
            self._logger.error("No DataBase connection found! "
                               "Use DbLinker to set 'DataBaseObjects' "
                               "or old DBConnector setting 'DataBaseObjectsConnections'.")

        if self.__valresdb is None:
            self._logger.error("Database connection to validation results could not be established")
        if self.__gbldb is None:
            self._logger.error("Database connection to global could not be established")

        ret = self.__ProcessTestRuns()
        self._data_manager.set_data_port(TESTRUN_PORT_NAME, self.__main_test_run)
        return ret

    def Terminate(self):
        """ Terminate. Called once. """
        self._logger.debug(str(_getframe().f_code.co_name) + "()" + " called.")

        self.__new_testruns = None
        self.__main_test_run = None
        return bci.RET_VAL_OK

    def __ProcessTestRuns(self):  # pylint: disable=C0103
        """ Process given testrun structure
        """
        ret = bci.RET_VAL_OK
        self.__checkpoint = self._data_manager.get_data_port(sd.SWVERSION_PORT_NAME)
        self.__checkpoint_ref = self._data_manager.get_data_port(sd.SWVERSION_REG_PORT_NAME)
        self.__proj_name = self._data_manager.get_data_port("ProjectName")
        self.__comp_name = self._data_manager.get_data_port("FunctionName")
        self.__collection_name = self._data_manager.get_data_port(sd.COLLECTION_NAME_PORT_NAME)
        self.__new_testruns = self._data_manager.get_data_port(NEW_TRUN_CFG_PORT_NAME, self._bus_name)
        save_to_db = self._data_manager.get_data_port(sd.SAVE_RESULT_IN_DB)
        # self.__readTestRunConfig()
        main_test_run = self.__DecodeTestRunConfig(self.__new_testruns)

        if save_to_db is None:
            save_to_db = True

        if main_test_run is not None and save_to_db is True:
            if main_test_run.Save(self.__valresdb, self.__gbldb) is True:
                self.__valresdb.commit()
            else:
                self._logger.error("Root Testrun could not be saved. Check error log")
                ret = bci.RET_VAL_ERROR

        self.__main_test_run = main_test_run

        return ret

    def __DecodeTestRunConfig(self, testrun_list):  # pylint: disable=C0103,R0914
        """ Decode the Testrun Configuration list

        :param testrun_list: List of testrun Configuration items
        """
        root_tr = None
        parent_key_names = {}
        tr_dict = {}

        for item in testrun_list:
            key = item['cfg_name']
            is_active = bool(item['active'] == 'True')
            name = item['tr_name']
            val_obs_name = item['val_obs_name']
            parent_key = item['parent_cfg_name']
            level = int(item['level'])
            use_ref = bool(item['use_ref'] == 'True')
            replace = bool(item['replace'] == 'True')

            if is_active:
                cpp = self.__checkpoint
                if use_ref:
                    cpp = self.__checkpoint_ref

                trr = TestRun(name=name, desc="", checkpoint=cpp,
                              user=environ["USERNAME"], obs_name=val_obs_name,
                              test_collection=self.__collection_name, parent=None, replace=replace,
                              proj_name=self.__proj_name, component=self.__comp_name)
                # add the testrun to the dictionary
                if key not in tr_dict:
                    tr_dict[key] = trr
                    parent_key_names[key] = parent_key
                else:
                    self._logger.error(" The testrun name key is already in use. Check your config file")

                # check the root testrun
                if level == 0:
                    if root_tr is None:
                        root_tr = trr
                    else:
                        self._logger.error(" The root testrun is defined twice. Check your config file")
                        raise

        # map the testruns
        for key, trr in tr_dict.iteritems():
            if parent_key_names[key] is not None and trr is not root_tr:
                if key in tr_dict:
                    tr_dict[parent_key_names[key]].AddChildTestRun(trr)
                else:
                    self._logger.error("Parent name key not found: '%s'. Check your config file" % key)
                    raise

        return root_tr


"""
CHANGE LOG:
-----------
$Log: testrun.py  $
Revision 1.12.1.1 2017/02/02 15:31:45CET Hospes, Gerd-Joachim (uidv8815) 
port level during load to test steps
Revision 1.12 2016/10/28 13:37:31CEST Hospes, Gerd-Joachim (uidv8815)
fix pylint errors
Revision 1.11 2016/10/28 12:18:35CEST Hospes, Gerd-Joachim (uidv8815)
save complete test run for VAL_DB_LEVEL_ALL
Revision 1.10 2016/09/15 15:05:24CEST Hospes, Gerd-Joachim (uidv8815)
merged 2.3.27-2 and 2.3.26-2 branch, deprecate Upate
Revision 1.9 2016/07/26 15:54:37CEST Hospes, Gerd-Joachim (uidv8815)
fix component usage in save and load
Revision 1.8 2016/07/22 15:54:09CEST Hospes, Gerd-Joachim (uidv8815)
new fields sim version and val sw version
Revision 1.7.1.2 2016/07/28 19:52:54CEST Hospes, Gerd-Joachim (uidv8815)
fix cut/merge error
Revision 1.7.1.1 2016/07/28 19:06:34CEST Hospes, Gerd-Joachim (uidv8815)
fix component usage in save and load
Revision 1.7 2016/05/09 11:00:21CEST Hospes, Gerd-Joachim (uidv8815)
add new column REMARKS to val.db and to pfd reports as new overview table row
Revision 1.6 2015/10/29 17:46:37CET Hospes, Gerd-Joachim (uidv8815)
add collection and sim_name to reports
- Added comments -  uidv8815 [Oct 29, 2015 5:46:37 PM CET]
Change Package : 390799:1 http://mks-psad:7002/im/viewissue?selection=390799
Revision 1.5 2015/10/29 14:54:16CET Ahmed, Zaheer (uidu7634)
changes made to load and save sim_name property into database
get set property method for sim_name
--- Added comments ---  uidu7634 [Oct 29, 2015 2:54:17 PM CET]
Change Package : 390794:1 http://mks-psad:7002/im/viewissue?selection=390794
Revision 1.4 2015/10/05 12:56:18CEST Ahmed, Zaheer (uidu7634)
Update() method for ValTestRun class to update lock flag in database
--- Added comments ---  uidu7634 [Oct 5, 2015 12:56:19 PM CEST]
Change Package : 376758:1 http://mks-psad:7002/im/viewissue?selection=376758
Revision 1.3 2015/05/05 14:42:09CEST Ahmed, Zaheer (uidu7634)
grab primary key for current user value db interface property no more query
--- Added comments ---  uidu7634 [May 5, 2015 2:42:09 PM CEST]
Change Package : 318797:5 http://mks-psad:7002/im/viewissue?selection=318797
Revision 1.2 2015/04/30 11:09:33CEST Hospes, Gerd-Joachim (uidv8815)
merge last changes
--- Added comments ---  uidv8815 [Apr 30, 2015 11:09:33 AM CEST]
Change Package : 330394:1 http://mks-psad:7002/im/viewissue?selection=330394
Revision 1.1 2015/04/23 19:05:39CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/val/project.pj
Revision 1.53 2015/04/27 14:47:26CEST Mertens, Sven (uidv7805)
ident string fix
--- Added comments ---  uidv7805 [Apr 27, 2015 2:47:27 PM CEST]
Change Package : 329312:2 http://mks-psad:7002/im/viewissue?selection=329312
Revision 1.52 2015/03/12 09:19:23CET Ahmed, Zaheer (uidu7634)
bug fix to ensure the add_info property never return None
--- Added comments ---  uidu7634 [Mar 12, 2015 9:19:24 AM CET]
Change Package : 316185:1 http://mks-psad:7002/im/viewissue?selection=316185
Revision 1.51 2015/03/09 09:26:04CET Mertens, Sven (uidv7805)
changing logger,
docu fixes
--- Added comments ---  uidv7805 [Mar 9, 2015 9:26:04 AM CET]
Change Package : 314290:1 http://mks-psad:7002/im/viewissue?selection=314290
Revision 1.50 2015/02/26 16:29:25CET Ahmed, Zaheer (uidu7634)
bug fix to check if the distance stats is available
before calculating total distance
--- Added comments ---  uidu7634 [Feb 26, 2015 4:29:26 PM CET]
Change Package : 310109:1 http://mks-psad:7002/im/viewissue?selection=310109
Revision 1.49 2015/02/19 15:11:53CET Hospes, Gerd-Joachim (uidv8815)
fix empty add_info field, add tests
--- Added comments ---  uidv8815 [Feb 19, 2015 3:11:54 PM CET]
Change Package : 308892:1 http://mks-psad:7002/im/viewissue?selection=308892
Revision 1.48 2015/01/27 14:12:27CET Ahmed, Zaheer (uidu7634)
Add new projerty add_info to tesrun class and also adaption in Save Load methods
--- Added comments ---  uidu7634 [Jan 27, 2015 2:12:28 PM CET]
Change Package : 298628:1 http://mks-psad:7002/im/viewissue?selection=298628
Revision 1.47 2015/01/20 10:46:59CET Mertens, Sven (uidv7805)
removing deprecated calls
--- Added comments ---  uidv7805 [Jan 20, 2015 10:47:00 AM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.46 2014/12/17 14:32:07CET Ellero, Stefano (uidw8660)
Removed all db.obj based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Dec 17, 2014 2:32:08 PM CET]
Change Package : 281278:1 http://mks-psad:7002/im/viewissue?selection=281278
Revision 1.45 2014/12/04 19:23:49CET Ellero, Stefano (uidw8660)
An additional check on the Windows login name was added to the Save method of the Testrun API class.
When the Windows login name is not defined in the global users (GBL_USERS) table of the Val Result Database,
an error will be logged and the method will return False.
A new test case in the related module test was added to check this kind of error.
Revision 1.44 2014/10/22 11:47:46CEST Ahmed, Zaheer (uidu7634)
Removed deprecated method usage
--- Added comments ---  uidu7634 [Oct 22, 2014 11:47:47 AM CEST]
Change Package : 267593:5 http://mks-psad:7002/im/viewissue?selection=267593
Revision 1.43 2014/10/21 21:01:34CEST Ahmed, Zaheer (uidu7634)
Add commit statement save method of testrun to reduce risk of tables
--- Added comments ---  uidu7634 [Oct 21, 2014 9:01:34 PM CEST]
Change Package : 273583:1 http://mks-psad:7002/im/viewissue?selection=273583
Revision 1.42 2014/08/04 15:14:11CEST Mertens, Sven (uidv7805)
adaptation for HPC head node
--- Added comments ---  uidv7805 [Aug 4, 2014 3:14:12 PM CEST]
Change Package : 253438:1 http://mks-psad:7002/im/viewissue?selection=253438
Revision 1.41 2014/06/19 12:20:27CEST Ahmed, Zaheer (uidu7634)
Support load store of testtype for testrun which use by report librart to choose apprioate template
--- Added comments ---  uidu7634 [Jun 19, 2014 12:20:27 PM CEST]
Change Package : 241731:1 http://mks-psad:7002/im/viewissue?selection=241731
Revision 1.40 2014/06/18 13:07:00CEST Hospes, Gerd-Joachim (uidv8815)
added property test_type and its method GetTestType
--- Added comments ---  uidv8815 [Jun 18, 2014 1:07:01 PM CEST]
Change Package : 241732:1 http://mks-psad:7002/im/viewissue?selection=241732
Revision 1.39 2014/05/28 16:16:00CEST Ahmed, Zaheer (uidu7634)
pylint fixes
--- Added comments ---  uidu7634 [May 28, 2014 4:16:00 PM CEST]
Change Package : 239969:1 http://mks-psad:7002/im/viewissue?selection=239969
Revision 1.38 2014/05/28 13:51:33CEST Ahmed, Zaheer (uidu7634)
Backward compatiblity for testrun.Load() method to check component column is return from database
--- Added comments ---  uidu7634 [May 28, 2014 1:51:33 PM CEST]
Change Package : 239969:1 http://mks-psad:7002/im/viewissue?selection=239969
Revision 1.37 2014/05/22 15:12:13CEST Ahmed, Zaheer (uidu7634)
warning message more clear information
--- Added comments ---  uidu7634 [May 22, 2014 3:12:13 PM CEST]
Change Package : 235884:1 http://mks-psad:7002/im/viewissue?selection=235884
Revision 1.36 2014/05/22 13:04:10CEST Ahmed, Zaheer (uidu7634)
Backward compatibilty support
Revision 1.35 2014/05/22 09:57:49CEST Ahmed, Zaheer (uidu7634)
return property function in upper case
--- Added comments ---  uidu7634 [May 22, 2014 9:57:50 AM CEST]
Change Package : 235884:1 http://mks-psad:7002/im/viewissue?selection=235884
Revision 1.34 2014/05/22 09:12:16CEST Ahmed, Zaheer (uidu7634)
New Property Component added to TestRun class
TestRunManager to Get Component name from VALF bus global at port FunctionName
--- Added comments ---  uidu7634 [May 22, 2014 9:12:16 AM CEST]
Change Package : 235884:1 http://mks-psad:7002/im/viewissue?selection=235884
Revision 1.33 2014/05/20 13:18:47CEST Hospes, Gerd-Joachim (uidv8815)
add user_account to report, based on testrun or ifc definition, update test_report
--- Added comments ---  uidv8815 [May 20, 2014 1:18:47 PM CEST]
Change Package : 233145:1 http://mks-psad:7002/im/viewissue?selection=233145
Revision 1.32 2014/05/15 17:24:29CEST Hospes, Gerd-Joachim (uidv8815)
add property component
--- Added comments ---  uidv8815 [May 15, 2014 5:24:30 PM CEST]
Change Package : 233146:1 http://mks-psad:7002/im/viewissue?selection=233146
Revision 1.31 2014/05/09 17:23:23CEST Hospes, Gerd-Joachim (uidv8815)
property method for testrun.locked
--- Added comments ---  uidv8815 [May 9, 2014 5:23:24 PM CEST]
Change Package : 233144:2 http://mks-psad:7002/im/viewissue?selection=233144
Revision 1.30 2014/05/06 11:49:31CEST Ahmed, Zaheer (uidu7634)
Provide Lock(), Unlock() and IsLocked()
function for testrun lock feature
--- Added comments ---  uidu7634 [May 6, 2014 11:49:32 AM CEST]
Change Package : 233264:1 http://mks-psad:7002/im/viewissue?selection=233264
Revision 1.29 2014/03/12 14:29:42CET Ahmed, Zaheer (uidu7634)
Implmented Load Save of RuntimeJob data added protection against duplicate entry
--- Added comments ---  uidu7634 [Mar 12, 2014 2:29:42 PM CET]
Change Package : 221470:1 http://mks-psad:7002/im/viewissue?selection=221470
Revision 1.28 2014/02/27 18:07:52CET Hospes, Gerd-Joachim (uidv8815)
fix usage of RuntimeJob and prep save/load with testrun
--- Added comments ---  uidv8815 [Feb 27, 2014 6:07:52 PM CET]
Change Package : 220009:1 http://mks-psad:7002/im/viewissue?selection=220009
Revision 1.27 2014/02/21 16:00:17CET Ahmed, Zaheer (uidu7634)
bug fix if the stats doesnt it exist then process_files is None
--- Added comments ---  uidu7634 [Feb 21, 2014 4:00:17 PM CET]
Change Package : 220098:3 http://mks-psad:7002/im/viewissue?selection=220098
Revision 1.26 2014/02/21 15:48:47CET Ahmed, Zaheer (uidu7634)
bug fix if the stats doesnt it exist then process_files are zero
--- Added comments ---  uidu7634 [Feb 21, 2014 3:48:47 PM CET]
Change Package : 220098:3 http://mks-psad:7002/im/viewissue?selection=220098
Revision 1.25 2014/02/21 15:27:07CET Ahmed, Zaheer (uidu7634)
Changes to make test statitic available for saved test run as well
--- Added comments ---  uidu7634 [Feb 21, 2014 3:27:07 PM CET]
Change Package : 220098:3 http://mks-psad:7002/im/viewissue?selection=220098
Revision 1.24 2014/02/20 17:48:20CET Hospes, Gerd-Joachim (uidv8815)
add property methods processed_<values> for report
--- Added comments ---  uidv8815 [Feb 20, 2014 5:48:20 PM CET]
Change Package : 220099:1 http://mks-psad:7002/im/viewissue?selection=220099
Revision 1.23 2014/02/20 14:28:36CET Ahmed, Zaheer (uidu7634)
GetDistanceProcess(), GetTimeProcess(), GetFileProcessed funcation are addded
to get distance time and file processed over testrun
--- Added comments ---  uidu7634 [Feb 20, 2014 2:28:36 PM CET]
Change Package : 220098:1 http://mks-psad:7002/im/viewissue?selection=220098
Revision 1.22 2014/02/20 12:57:02CET Hospes, Gerd-Joachim (uidv8815)
print user accunt instead of db internal userid
--- Added comments ---  uidv8815 [Feb 20, 2014 12:57:03 PM CET]
Change Package : 220000:1 http://mks-psad:7002/im/viewissue?selection=220000
Revision 1.21 2014/02/06 16:31:34CET Hospes, Gerd-Joachim (uidv8815)
only one runtime job for each testrun
--- Added comments ---  uidv8815 [Feb 6, 2014 4:31:35 PM CET]
Change Package : 214928:1 http://mks-psad:7002/im/viewissue?selection=214928
Revision 1.20 2014/02/05 17:43:03CET Hospes, Gerd-Joachim (uidv8815)
new testrun attrib for runtime job list
--- Added comments ---  uidv8815 [Feb 5, 2014 5:43:03 PM CET]
Change Package : 214928:1 http://mks-psad:7002/im/viewissue?selection=214928
Revision 1.19 2013/12/15 21:22:04CET Hecker, Robert (heckerr)
Corrected Description
--- Added comments ---  heckerr [Dec 15, 2013 9:22:05 PM CET]
Change Package : 210873:1 http://mks-psad:7002/im/viewissue?selection=210873
Revision 1.18 2013/12/15 20:23:54CET Hecker, Robert (heckerr)
Added Interface for AlgoTestReport.
--- Added comments ---  heckerr [Dec 15, 2013 8:23:54 PM CET]
Change Package : 210873:1 http://mks-psad:7002/im/viewissue?selection=210873
Revision 1.17 2013/11/25 09:41:46CET Ahmed-EXT, Zaheer (uidu7634)
Get Testcases more procise with arguement to get testcases including childs tr or the testcase from current testrun
improve GetTestCase function with additional creteria of DOORS ID to get specific testcase
--- Added comments ---  uidu7634 [Nov 25, 2013 9:41:47 AM CET]
Change Package : 203293:1 http://mks-psad:7002/im/viewissue?selection=203293
Revision 1.16 2013/11/11 15:20:54CET Ahmed-EXT, Zaheer (uidu7634)
fix pep8 and pylint
Added GetTestCase(name) function to get test name by given name
Revision 1.15 2013/11/05 15:09:05CET Ahmed-EXT, Zaheer (uidu7634)
LoadLevel testcases set to Basic for Testrun.Load()
Commented extraction of ProjectName  from Testrun name functionality
--- Added comments ---  uidu7634 [Nov 5, 2013 3:09:05 PM CET]
Change Package : 203293:1 http://mks-psad:7002/im/viewissue?selection=203293
Revision 1.14 2013/11/04 10:27:52CET Ahmed-EXT, Zaheer (uidu7634)
Pep8 fix
--- Added comments ---  uidu7634 [Nov 4, 2013 10:27:52 AM CET]
Change Package : 203293:1 http://mks-psad:7002/im/viewissue?selection=203293
Revision 1.13 2013/10/31 17:50:33CET Ahmed-EXT, Zaheer (uidu7634)
Added support for Project ID as manadatory field in Testrun and TestManager class
Revision 1.12 2013/10/30 19:46:41CET Hecker, Robert (heckerr)
Removed indirect usage of logging module.
--- Added comments ---  heckerr [Oct 30, 2013 7:46:41 PM CET]
Change Package : 204155:1 http://mks-psad:7002/im/viewissue?selection=204155
Revision 1.11 2013/10/01 10:36:22CEST Raedler, Guenther (uidt9430)
- added new option to save the testruns into the DB
- set dataport with main testrun
--- Added comments ---  uidt9430 [Oct 1, 2013 10:36:22 AM CEST]
Change Package : 197855:1 http://mks-psad:7002/im/viewissue?selection=197855
Revision 1.10 2013/08/07 12:53:36CEST Ahmed-EXT, Zaheer (uidu7634)
GetObserverName and GetCollectionName function Added into TestRun Class
--- Added comments ---  uidu7634 [Aug 7, 2013 12:53:36 PM CEST]
Change Package : 192688:1 http://mks-psad:7002/im/viewissue?selection=192688
Revision 1.9 2013/07/25 10:08:47CEST Raedler, Guenther (uidt9430)
- use testrun name and checkpoint for database selection
--- Added comments ---  uidt9430 [Jul 25, 2013 10:08:48 AM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.8 2013/07/15 09:53:28CEST Raedler, Guenther (uidt9430)
- add a Testcase to the testrun
--- Added comments ---  uidt9430 [Jul 15, 2013 9:53:28 AM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.7 2013/05/23 11:41:17CEST Mertens, Sven (uidv7805)
aligning imports and stk.db connections
--- Added comments ---  uidv7805 [May 23, 2013 11:41:18 AM CEST]
Change Package : 179495:7 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.6 2013/05/13 14:50:49CEST Ahmed-EXT, Zaheer (uidu7634)
Fixed reloading bug and create testrun without replacement to mantain hirachechal tree
added SetReplace method
--- Added comments ---  uidu7634 [May 13, 2013 2:50:50 PM CEST]
Change Package : 178419:4 http://mks-psad:7002/im/viewissue?selection=178419
Revision 1.5 2013/05/07 12:53:12CEST Ahmed-EXT, Zaheer (uidu7634)
Changes according to new structure of test run manager input config
--- Added comments ---  uidu7634 [May 7, 2013 12:53:12 PM CEST]
Change Package : 178419:4 http://mks-psad:7002/im/viewissue?selection=178419
Revision 1.4 2013/05/03 14:10:23CEST Ahmed-EXT, Zaheer (uidu7634)
Changes according to TestRunManager Apporach Added replace flag for invidual checkpoint entry
--- Added comments ---  uidu7634 [May 3, 2013 2:10:23 PM CEST]
Change Package : 178419:2 http://mks-psad:7002/im/viewissue?selection=178419
Revision 1.3 2013/04/23 15:00:17CEST Raedler, Guenther (uidt9430)
- implemented parser for testrun manager
- fixed minor errors in testrun class
--- Added comments ---  uidt9430 [Apr 23, 2013 3:00:18 PM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.2 2013/04/22 16:33:27CEST Raedler, Guenther (uidt9430)
- added new class testrun
- added usage of testrun class in testrun manager
--- Added comments ---  uidt9430 [Apr 22, 2013 4:33:27 PM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.1 2013/04/16 13:08:46CEST Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/FCT_Function/
05_Testing/05_Test_Environment/algo/stk/val/project.pj
"""
