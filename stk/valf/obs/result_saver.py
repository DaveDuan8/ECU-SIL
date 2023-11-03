"""
result_saver.py
---------------

Prepares validation result db interface and stores testrun from data bus to result db.

Observer should run as one of the last to give other observers time to prepare results
that should be stored.

used states:

    1) PostInitialize:

        setup TestRun instance based on values stored on DataBus

    2) PreTerminate:

        create all needed TestCase and TestStep instances and save in db,
        additionally it can create a pdf report.
        The saved results can also be controlled in Validation DB using Validation Assessmet Tool ``VAT``,

**User-API Interfaces**

    - `stk.valf` (complete package)
    - `ResultSaver` (this module)

:org:           Continental AG
:author:        Joachim Hospes, Zaheer Ahmed

:version:       $Revision: 1.5 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/02/02 15:37:28CET $
"""
# =============================================================================
# System Imports
# =============================================================================

# =============================================================================
# Local Imports
# =============================================================================
from stk.val.testrun import TestRun
from stk.val.results import ValTestcase, ValTestStep, ValAssessment, \
    ValAssessmentWorkFlows, ValSaveLoadLevel, BaseUnit, BaseValue
import stk.valf.signal_defs as sd
import stk.rep as rep
from stk.valf import BaseComponentInterface


# =============================================================================
# Class
# =============================================================================
class ResultSaver(BaseComponentInterface):
    """
    Observer to store minimum needed TestRun elements
    as used for doors export to the Val Result DB.

    The test run elements have to be provided on the data bus using following structure:

    ::

        tr = {"name": str,          # name of the testrun
              "description": str,   # description
              "checkpoint": str,    # Algo checkpoint of SW under test
              "component": str,     # name of component (function like EBA,ACC,SOD) as in gbl db
              "obs_name": str,      # Observer name as in val db
              "collection": str,    # Collection name used for these tests
              "project": str,       # Name of project
              "test_cases": list    # list of test case dictionaries (see below)
             }

    ::

        tc = {"name": str,              # name of testcase like 'Lane Detection in snow'
              "id": str,                # DOORS ID like 'MFC_TC_002_005'
              "collection": str,        # collection name
              "description": str,       # description of the testcase, printed in pdf report
              "exp_res": str,           # expected result pass/fail criteria TODO: exp_res for test case??????
              "test_result": ValAssessmentStates,     # passed/failed value
              "test_steps": list        # list of test step dictionaries (see below)
             }

    ::

        ts = {"name": str,          # name of the test step
              "id": str,            # DOORS ID of test Step
              "res_type": str,      # type of result
              "unit": GblUnits,     # The unit of value
              "exp_res": str,       # expected result pass/fail criteria like "avg delay <0.004"
              "value": number,      # measured result value
              "test_result": ValAssessmentStates    # pass/fail criteria
             }


    expected ports:

        - ``DataBaseObjects``, bus ``DBBus#1``:
                connection objects for cat, gbl and val db, e.g. as set by observer `db_linker`
                (instances of classes `BaseRecCatalogDB`, `BaseGblDB` and `BaseValResDB`)
        - ``SwVersion``, bus ``Global``:
                 SW version to validate
        - ``ProjectName``, own bus:
                name of customer project the results are stored for
        - ``TestRun``, own bus:
                dictionary with test run, test cases and test steps as listed above

    optional ports:

        - ``SaveResultToDb``, own bus:
                set to ``False`` to prevent saving results in db,
                **attention**: if results are not saved some names might not be set
                because they are only initialized while saving the testrun
        - ``ReportFileName``, own bus:
                path/filename of optional pdf report file, if not set or invald no report will be created,
                with test run stored to result db a pdf report can be created any time using `gen_report` script

    written ports:
        - ``TestRun``, own bus:
                if the test run is saved to db, the TestRun dictionary will be extended
                with the element 'tr_id' showing the db internal test run id and saved on the port again.
    """
    def __init__(self, data_manager, component_name, bus_name):
        """ Class initialisation.

        :param data_manager: data manager in use (self._data_manager)
        :param component_name: name of component as stated in config (self._component_name)
        :param bus_name: name of bus to use as stated in config (self._bus_name)
        """
        BaseComponentInterface.__init__(self, data_manager, component_name, bus_name, version="$Revision: 1.5 $")

        self._db_connections = None
        self._cat_db = None
        self._gbl_db = None
        self._val_db = None
        self._save_result_to_db = True
        self._outdir = None
        self._sw_version = None
        self.__testrun = TestRun()
        self.__coll_id = None

    # --- Framework functions. --------------------------------------------------
    def PostInitialize(self):
        """ **Setup TestRun**

        Get needed settings from data bus (see class description) and setup a testrun:

            - check needed data ports
            - create TestRun instance to add TestCases and TestSteps later
            - save and commit base TestRun in ResultDB

        If the test run is stored in the db (port SaveResultToDb: True)
        a 'tr_id' element is added to the dict stored on port ``TestRun``.
        """
        self._logger.debug()

        # Get the version of the algo being tested.
        self._sw_version = self._data_manager.get_data_port("SWVersion")

        # get flag if testrun should be saved in db or just provided on data bus
        self._save_result_to_db = self._get_data('SaveResultToDb', self._bus_name, default=self._save_result_to_db)

        # Get the database connection
        self._db_connections = self._get_data(sd.DATABASE_OBJECTS_PORT_NAME, 'dbbus')
        if self._db_connections:
            self._cat_db = self._db_connections.get('cat', None)
            self._gbl_db = self._db_connections.get('gbl', None)
            self._val_db = self._db_connections.get('val', None)

        save_tr = True
        if self._cat_db is None:
            self._logger.warning("Database connection to recfile catalogue could not be established")
            save_tr = False
        if self._gbl_db is None:
            self._logger.warning("Database connection to global data could not be established")
            save_tr = False
        if self._val_db is None:
            self._logger.warning("Database connection to validation results data could not be established")
            save_tr = False
        if save_tr is False:
            self._logger.warning("testrun will not be saved in Val DB because of missing db connections")
            self._save_result_to_db = False

        project_name = self._get_data('ProjectName', self._bus_name)

        # get testrun from port:
        #     tr = {"name": str,          # name of the testrun
        #           "description": str,   # description
        #           "checkpoint": str,    # Algo checkpoint of SW under test
        #           "component": str,     # name of component (function like EBA,ACC,SOD) as in db
        #           "obs_name": str,      # Observer name as in val db
        #           "collection": str,    # collection name used for these tests
        #           "project": str,       # name of project
        #           "test_cases": list    # list of test case dictionaries (see below)
        #          }
        tr = self._get_data('TestRun', self._bus_name)
        if type(tr) is not dict:
            self._logger.error("no test run defined on data port 'TestRun' with type dict!")
            return sd.RET_VAL_ERROR
        if tr.get('checkpoint') != self._sw_version:
            self._logger.warning("the testrun checkpoint {} differs from the sw version {} validated in this run!"
                                 .format(tr['checkpoint'], self._sw_version))

        # create testrun instance that can be saved in reslt db with values passed by data port TestRun
        self.__testrun = TestRun(name=tr.get('name'),                   # The name of the testrun
                                 desc=tr.get('description'),            # Test run description
                                 checkpoint=tr.get('checkpoint'),       # Algo checkpoint
                                 component=tr.get('component'),         # Component name (ACC,EBA,SOD)
                                 obs_name=tr.get('obs_name'),           # name of main observer as in db
                                 test_collection=tr.get('collection'),  # the name of collection
                                 replace=True,                          # Delete any existing testrun in database
                                 proj_name=project_name)                # The project
        if self._save_result_to_db:
            self.__coll_id = self._cat_db.get_collection_id(tr.get('collection'))
            self._logger.info("Now creating testrun {} in TestDatabase ...".format(self.__testrun.GetName()))
            self.__testrun.Save(self._val_db, self._gbl_db, level=ValSaveLoadLevel.VAL_DB_LEVEL_STRUCT)
            # a new testrun was created in db (perhaps the old overwritten), prevent overwriting it again:
            self.__testrun.SetReplace(False)
            # reload the testrun to get all entries filled automatically by the db save (e.g. the Id):
            self.__testrun.Load(self._val_db, self._gbl_db, self._cat_db, testrun_id=self.__testrun.GetId())
            # add 'tr_id' to the test run dict, update the port and commit all updated db fields to the db
            tr['tr_id'] = self.__testrun.GetId()
            self._set_data('TestRun', tr, self._bus_name)
            self._val_db.commit()
            self._logger.info("testrun committed to Val DB with id {}."
                              .format(self.__testrun.GetId()))

        return sd.RET_VAL_OK

    def PreTerminate(self):
        """ **store testrun structure to result db**

        If data port ``SaveResultToDb`` is set to False the testrun structure is only created but not saved.

        If data port ``ReportFileName`` is set to a path/filename a pdf report for the testrun is stored.

        """
        # check if save result to Db is enabled or not
        trun = self._data_manager.get_data_port("TestRun", self._bus_name)

        # if self._save_result_to_db:
        for tcase in trun.get('test_cases'):
            self._logger.debug('Starting to save testcase "{}" to TestDatabase ...;'.format(tcase.get('name')))
            # create test case instance for this
            res_tc = ValTestcase(tcase.get('name'),                  # name of the test case
                                 specification_tag=tcase.get('id'),  # DOOR ID
                                 coll_id=self.__coll_id,          # collection Id
                                 desc=tcase.get('description'),      # One sentence small description
                                 doors_url=tcase.get('doors_url'),   # location of test spec
                                 exp_res=tcase.get('exp_res'))       # pass fail criteria
            for tstep in tcase.get('test_steps'):
                # create test step and add to test case
                # from:
                # ts = {"name": str,          # name of the test step
                #       "id": str,            # DOORS ID of test Step
                #       "res_type": str,      # type of result
                #       "unit": GblUnits,     # The unit of value
                #       "exp_res": str,       # expected result pass/fail criteria like "avg delay <0.004"
                #       "value": number,      # measured result value
                #       "test_result": ValAssessmentStates    # pass/fail criteria
                # }
                res_ts = ValTestStep(tstep.get('name'),
                                     tag=tstep.get('id'),
                                     res_type=tstep.get('res_type'),
                                     unit=tstep.get('unit'),
                                     exp_res=tstep.get('exp_res'))
                res_ts.SetValue(BaseValue('', BaseUnit(tstep.get('unit')), tstep.get('value')))
                res_ts.AddAssessment(ValAssessment(wf_state=ValAssessmentWorkFlows.ASS_WF_AUTO,
                                                   ass_state=tstep.get('test_result'),
                                                   ass_comment=''))
                res_tc.AddTestStep(res_ts)

            # finally save this test case with complete structure
            if self._save_result_to_db:
                res_tc.Save(dbi_val=self._val_db,
                            dbi_gbl=self._gbl_db,
                            testrun_id=self.__testrun.GetId(),
                            obs_name=self.__testrun.GetObserverName(),
                            level=ValSaveLoadLevel.VAL_DB_LEVEL_ALL)
                # load the test case again to get the auto completed fields like names where only an id was passed
                res_tc.Load(dbi_val=self._val_db,
                            dbi_gbl=self._gbl_db,
                            dbi_cat=self._cat_db,
                            testrun_id=self.__testrun.GetId())
            # add saved test case to test run
            self.__testrun.AddTestCase(res_tc)
        # all test cases with test steps added now and already committed (in tc.Save)

        # create the pdf report if needed (path/name available on data port ReportFileName)
        report_file_name = self._data_manager.get_data_port('ReportFileName', self._bus_name)
        if report_file_name is not None:
            report = rep.AlgoTestReport(self.__testrun)
            report.build(report_file_name)

        return sd.RET_VAL_OK


"""
CHANGE LOG:
-----------
$Log: result_saver.py  $
Revision 1.5 2017/02/02 15:37:28CET Hospes, Gerd-Joachim (uidv8815) 
don't commit again, already in tc.save
Revision 1.4 2016/10/28 12:13:32CEST Hospes, Gerd-Joachim (uidv8815)
save test run on default, add 'tr_id', extend module tests
Revision 1.3 2016/04/15 17:48:46CEST Hospes, Gerd-Joachim (uidv8815)
pep8 fix
Revision 1.2 2016/04/15 17:38:09CEST Hospes, Gerd-Joachim (uidv8815)
pylint/pep8 fixes
Revision 1.1 2016/04/12 15:03:58CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/valf/obs/project.pj
"""
