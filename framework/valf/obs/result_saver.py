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

    - `framework.valf` (complete package)
    - `ResultSaver` (this module)

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/04/02 15:07:54CEST $
"""
# =============================================================================
# System Imports
# =============================================================================

# =============================================================================
# Local Imports
# =============================================================================
from framework.val.testrun import TestRun
from framework.val.results import ValTestcase, ValTestStep, ValAssessment, ValAssessmentWorkFlows, BaseUnit, BaseValue
import framework.valf.signal_defs as sd
import framework.rep as rep
from framework.valf import BaseComponentInterface


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
        BaseComponentInterface.__init__(self, data_manager, component_name, bus_name, version="$Revision: 1.2 $")

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
    def post_initialize(self):
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

        # # get flag if testrun should be saved in db or just provided on data bus
        # self._save_result_to_db = self._get_data('SaveResultToDb', self._bus_name, default=self._save_result_to_db)
        return sd.RET_VAL_OK

    def pre_terminate(self):
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
                res_ts = ValTestStep(tstep.get('name'),
                                     tag=tstep.get('id'),
                                     res_type=tstep.get('res_type'),
                                     unit=tstep.get('unit'),
                                     exp_res=tstep.get('exp_res'))
                res_ts.set_value(BaseValue('', BaseUnit(tstep.get('unit')), tstep.get('value')))
                res_ts.add_assessment(ValAssessment(wf_state=ValAssessmentWorkFlows.ASS_WF_AUTO,
                                                    ass_state=tstep.get('test_result'),
                                                    ass_comment=''))
                res_tc.add_test_step(res_ts)

            self.__testrun.add_test_case(res_tc)
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
Revision 1.2 2020/04/02 15:07:54CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:39:25CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/valf/obs/project.pj
"""
