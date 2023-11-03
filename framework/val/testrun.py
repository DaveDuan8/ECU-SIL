"""
framework/val/testrun.py
-------------------

    Testrun API class and Testrun Manager implementation

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 09:24:02CEST $
"""
# - imports -----------------------------------------------------------------------------------------------------------
from os import environ
# noinspection PyProtectedMember
# from sys import _getframe

from framework.util.logger import Logger
from framework.util.gbl_defs import GblTestType

from framework.val.results import ValTestcase
from framework.valf import BaseComponentInterface as bci
from framework.util import defines as defs
from framework.util.helper import sec_to_hms_string

# Defines ---------------------------------------------------------------------
NEW_TRUN_CFG_PORT_NAME = 'testruns'
TESTRUN_PORT_NAME = 'trun'

# Classes ---------------------------------------------------------------------


class TestRun(object):  # pylint: disable=R0902,R0904
    """ Testrun Class supporting the interface to the result database """

    def __init__(self, name=None, desc=None, checkpoint=None, user=None,  # pylint: disable=R0913
                 obs_name=None, test_collection=None, parent=None, replace=False, proj_name=None, component=None,
                 remarks=None,sim_name=None, sim_version=None, sw_version=None):
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
        self.__sim_name = sim_name
        self.__sim_version = sim_version
        self.__val_sw_version = sw_version
        self.__remarks = remarks
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

    def add_test_case(self, testcase):  # pylint: disable=C0103
        """Add test cases

        :param testcase: in a list
        """

        if isinstance(testcase, ValTestcase):
            self.__testcase_list.append(testcase)

    def get_runtime_jobs(self, node="LUSS010", jobid=None):  # pylint: disable=C0103
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

    def get_child_test_runs(self):  # pylint: disable=C0103
        """Get the list of child testruns
        """
        return self.__child_tr

    def get_testcases(self, inc_child_tr=True):  # pylint: disable=C0103
        """Get the list of child testruns

        :param inc_child_tr:
        """
        if inc_child_tr:
            tc_list = []
            for tcase in self.__testcase_list:
                tc_list.append(tcase)
            for ctr in self.get_child_test_runs():
                for tcase in ctr.get_testcases():
                    tc_list.append(tcase)
            return tc_list

        else:
            return self.__testcase_list

    def get_id(self):  # pylint: disable=C0103
        return self.__tr_id

    def get_test_type(self):  # pylint: disable=C0103
        """ Return the type of the executed test like 'performance', 'functional'
        default return is 'performance' if not set
        """
        if self.__test_type is None:
            return GblTestType.TYPE_PERFORMANCE
        return self.__test_type

    def get_name(self):  # pylint: disable=C0103
        """
        Return the Testrun Name of the DB
        An error log will be generated, if it is not set
        """
        if self.__name is None:
            self._log.error("Testrun Name is None")
        return self.__name

    def get_checkpoint(self):  # pylint: disable=C0103
        """
        Return the Testrun checkpoint label
        An error log will be generated, if it is not set
        """
        if self.__checkpoint is None:
            self._log.error("Testrun Name is None")
        return self.__checkpoint

    def get_observer_name(self):  # pylint: disable=C0103
        """
        Return the Testrun Observer Name
        An error log will be generated, if it is not set
        """
        if self.__obs_name is None:
            self._log.error("Observer Name is None")
        return self.__obs_name

    def set_replace(self, replace):  # pylint: disable=C0103
        """Set Testrun  replace flag of the test run

        :param replace:
        """
        self.__replace = replace

    def get_project_name(self):  # pylint: disable=C0103
        """
        Get project name of the test run
        """
        return self.__proj_name

    def get_component_name(self):  # pylint: disable=C0103
        """
        Get component name
        """
        return str(self.__component).upper()

    def get_user_account(self):  # pylint: disable=C0103
        """
        Get the account of the user executing the TestRun
        """
        return self.__user

    def get_distance_process(self):  # pylint: disable=C0103
        """
        Get Distance processed by test run

        :return: Total distance in Kilometer
        :rtype:  int
        """
        return self.__processed_distance

    def get_time_process(self):  # pylint: disable=C0103
        """
        Get Time processed by test run

        :return: Total Time in Second, Duration with format HH:MM:SS
        :rtype:  int, string
        """
        return self.__processed_time, sec_to_hms_string(self.__processed_time)

    def get_file_processed(self):  # pylint: disable=C0103
        """
        Get No. of files processed by test run

        :return: Total no. of files
        :rtype:  int
        """
        return self.__processed_files

    def is_locked(self):  # pylint: disable=C0103
        """
        Get Testrun Lock status

        :return: Lock status of testrun with boolean flag
                 True  ==> Testrun is locked
                 False ==> Testrun is unlocked
        :rtype:  bool
        """
        return self.__lock

    def lock(self, recursive=True):  # pylint: disable=C0103
        """
        Lock testrun

        :param recursive: Apply lock recursively to all child testruns below given testrun
        :type recursive: bool
        """

        if recursive:
            for child in self.__child_tr:
                child.lock(recursive=recursive)
        self.__lock = True

    def unlock(self, recursive=True):  # pylint: disable=C0103
        """
        Unlock testrun

        :param recursive: Remove lock recursively from all child testruns below given testrun
        :type recursive: bool
        """
        if recursive:
            for child in self.__child_tr:
                child.unlock(recursive=recursive)
        self.__lock = False

    @property
    def name(self):
        """AlgoTestReport Interface overloaded attribute, returning Name of Testrun as string.
        """
        return self.get_name()

    @property
    def checkpoint(self):
        """AlgoTestReport Interface overloaded attribute, returning Checkpoint Name as string.
        """
        return self.get_checkpoint()

    @property
    def description(self):
        """AlgoTestReport Interface overloaded attribute, returning Description of the Testrun as string.
        """
        return self.__desc

    @property
    def project(self):
        """AlgoTestReport Interface overloaded attribute, returning ProjectName as string.
        """
        return self.get_project_name()

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
        return self.get_user_account()

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
        return str(self.get_id())

    @property
    def test_type(self):
        """AlgoTestReport Interface overloaded attribute, returning type of test executed for this Testrun,
        e.g. 'performance', 'functional' as string.
        """
        return str(self.get_test_type())

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
        return self.is_locked()

    @property
    def test_cases(self):
        """AlgoTestReport Interface overloaded attribute, returning List of Testcases as list[`TestCase`,...].
        """
        return self.get_testcases()

    @property
    def processed_distance(self):
        """AlgoTestReport Interface overloaded attribute, returning overall distance processed, unique recordings
        (measid)! as int.
        """
        return self.get_distance_process()

    @property
    def processed_time(self):
        """AlgoTestReport Interface overloaded attribute, returning overall time processed, unique recordings
        (measid)! as string ("hh:mm:ss").
        """
        return self.get_time_process()[1]

    @property
    def processed_files(self):
        """AlgoTestReport Interface overloaded attribute, returning overall number of unique recordings (measid)
        used as int.
        """
        return self.get_file_processed()

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
    def __init__(self, data_manager, component_name, bus_name="BASE_BUS"):
        """ Contructor """
        # noinspection PyCallByClass,PyTypeChecker
        bci.__init__(self, data_manager, component_name, bus_name, "$Revision: 1.2 $")

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
    def initialize(self):
        """ Initialize. Called once. """
        # self._logger.debug(str(_getframe().f_code.co_name) + "()" + " called.")
        #
        # # get the database object list
        # self.__databaseobjects = self._data_manager.get_data_port("DataBaseObjects", "DBBus#1")
        # if self.__databaseobjects is None:
        #     self._logger.info("'DataBaseObjects' port was not set.")
        # elif type(self.__databaseobjects) is list:
        #     # testrun observer was called before DbLinker, so we still can add needed connections
        #     # set the requested data base objects to the connection list
        #     self.__databaseobjects.append(db_gbl)
        #     self.__databaseobjects.append(db_val)
        return bci.RET_VAL_OK

    def post_initialize(self):
        ret = self.__process_test_runs()
        self._data_manager.set_data_port(TESTRUN_PORT_NAME, self.__main_test_run)
        return ret

    def terminate(self):
        """ Terminate. Called once. """
        # self._logger.debug(str(_getframe().f_code.co_name) + "()" + " called.")

        self.__new_testruns = None
        self.__main_test_run = None
        return bci.RET_VAL_OK

    def __process_test_runs(self):  # pylint: disable=C0103
        """ Process given testrun structure
        """
        ret = bci.RET_VAL_OK
        self.__checkpoint = self._data_manager.get_data_port(defs.SWVERSION_PORT_NAME)
        self.__checkpoint_ref = self._data_manager.get_data_port(defs.SWVERSION_REG_PORT_NAME)
        self.__proj_name = self._data_manager.get_data_port("ProjectName")
        self.__comp_name = self._data_manager.get_data_port("FunctionName")
        self.__sim_name = self._data_manager.get_data_port("sim_name")
        self.__collection_name = self._data_manager.get_data_port(defs.COLLECTION_NAME_PORT_NAME)
        self.__new_testruns = self._data_manager.get_data_port(NEW_TRUN_CFG_PORT_NAME, self._bus_name)
        main_test_run = self.__decode_test_run_config(self.__new_testruns)

        self.__main_test_run = main_test_run

        return ret

    def __decode_test_run_config(self, testrun_list):  # pylint: disable=C0103,R0914
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
            description = item['description']
            if is_active:
                cpp = self.__checkpoint
                if use_ref:
                    cpp = self.__checkpoint_ref

                trr = TestRun(name=name, desc=description, checkpoint=cpp,
                              user=environ["USERNAME"], obs_name=val_obs_name,
                              test_collection=self.__collection_name, parent=None, replace=replace,
                              proj_name=self.__proj_name, component=self.__comp_name, sim_name=self.__sim_name,
                              sim_version=self.__checkpoint, sw_version=self.__checkpoint_ref)
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
Revision 1.2 2020/03/31 09:24:02CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:34:09CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/val/project.pj
"""
