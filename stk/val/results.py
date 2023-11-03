"""
stk/val/results.py
------------------

Subpackage for Handling Basic Validation Results.

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.11 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/04/12 15:07:52CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from re import compile as recomp, IGNORECASE, DOTALL

# - import STK modules ------------------------------------------------------------------------------------------------
import stk.db.gbl.gbl as db_gbl
import stk.db.val.val as db_val
import stk.db.cat.cat as db_cat

from stk.db.val.val import COL_NAME_RES_ID, COL_NAME_RES_TESTRUN_ID, COL_NAME_RES_RESDESC_ID, COL_NAME_RES_VALUE, \
    COL_NAME_RES_MEASID, COL_NAME_RES_RESASSID, COL_NAME_RESULTTYPE_NAME, COL_NAME_RESULTTYPE_DESC, \
    COL_NAME_RESULTTYPE_CLASS, COL_NAME_RESDESC_NAME, COL_NAME_RESDESC_COLLID, COL_NAME_RESDESC_UNIT_ID, \
    COL_NAME_RESDESC_PARENT, COL_NAME_RESDESC_REFTAG, COL_NAME_RESVAL_ID, COL_NAME_RESVAL_SUBID, \
    COL_NAME_RESVAL_VALUE, COL_NAME_RESIMG_ID, COL_NAME_RESIMG_IMAGE, COL_NAME_RESIMG_TITLE, \
    COL_NAME_RESIMG_FORMAT, COL_NAME_RESDESC_ID, COL_NAME_RESDESC_DOORS_URL, COL_NAME_RESDESC_EXPECTRES, \
    COL_NAME_RESDESC_DESCRIPTION, COL_NAME_RESMESS_SUBID, COL_NAME_RESMESS_ID, COL_NAME_RESMESS_MESS, \
    COL_NAME_RES_TESTRUN_ID

from stk.db.gbl.gbl import COL_NAME_UNIT_NAME, COL_NAME_UNIT_LABEL
from stk.val.asmt import ValAssessment, ValAssessmentStates, ValAssessmentWorkFlows
from stk.db.gbl import GblUnits
from stk.val.result_types import BaseUnit, BaseValue, ValueVector, Signal, Histogram, ValSaveLoadLevel, BaseMessage
from stk.img import ValidationPlot
# from base_events import ValBaseEvent
from stk.val.events import ValEventList
from stk.obj.ego import EgoMotion
from stk.util.helper import sec_to_hms_string
from stk.util.logger import Logger


# - classes -----------------------------------------------------------------------------------------------------------
class ValTestcase(object):
    """ Testcase Class

    example::

        # Result descriptor tree stored inside the database
        # the links a build by a parent relation
        RD(1): VAL_TESTCASE
        |
        +-> RD(3): Testcase result 1
        +-> RD(4): Testcase result 2
        +-> RD(2): VAL_TESTCASE_SUB_MEASRES -- for measurement results
        |
        +-> RD(5) file result 1
        +-> RD(6) file result 2
        +-> RD(7): VAL_TESTCASE_SUB_EVENTS -- for event results
        +-> RD(8) event description
        #
        # Result tree example with two measurements
        TR -> Res(1) -> RD(1)
           -> Res(2) -> RD(3)
           -> Res(3) -> RD(4)
           -> Res(4) -> RD(5) -> measid(0)
           -> Res(5) -> RD(5) -> measid(1)
           -> Res(6) -> RD(6) -> measid(0)
           -> Res(7) -> RD(6) -> measid(1)
           ...
           -> Res(8) -> RD(7)

    """
    #  pylint: disable=R0904, R0902
    TESTCASE_TYPE = "VAL_TESTCASE"
    TESTCASE_UNIT = "none"
    SUB_MEASRES = "VAL_TESTCASE_SUB_MEASRES"
    SUB_EVENTS = "VAL_TESTCASE_SUB_EVENTS"
    TEST_STEP = "VAL_TESTSTEP"
    SUB_TEST_STEP = "VAL_TESTSTEP_SUB"
    SUB_TEST_DETAIL = "VAL_TESTDETAIL_SUB"

    MEAS_DIST_PROCESS = SUB_MEASRES + "_DIST_PROC"
    MEAS_TIME_PROCESS = SUB_MEASRES + "_TIME_PROC"

    def __init__(self, name=None, coll_id=None, specification_tag=None,  # pylint: disable=R0913
                 doors_url="", exp_res="", desc=""):
        """ initialize base class for the testcase prepare all locals

        :param name: Testcase Name e.g. "ALN EOL State"
        :type name: String
        :param coll_id: Testcase Collection Identifier
        :type coll_id: int
        :param specification_tag: Doors Specification ID also known as Test Case identifier
                                  e.g. "ACC_TC_001_001", "ALN_TC_004_005"
        :type specification_tag: String
        :param doors_url: Doors URL link to Test case specification
            e.g. "doors://rbgs854a:40000/?version=2&prodID=0&urn=urn:telelogic::1-503e822e5ec3651e-M-0001cbf1"
        :type doors_url: String
        :param exp_res: Expected result e.g. "average error < .053"
        :type exp_res: String
        :param desc: Description text of the Testcase
        :type desc: String
        """
        self._log = Logger(self.__class__.__name__)
        self.__testresults = []  # List of Testcase Results
        self.__testsummarydetails = []  # List of TestCase Summary Detail
        self.__measresults = []  # List of File Results
        self.__teststeps = []  # List of teststeps
        self.__teststepsub_id = None  # parent of teststeps
        self.__testdetailsub_id = None  # parent of test detail summary
        self.__events = ValEventList()  # Class managing events
        self.__name = name  # Unique Testcase Name
        self.__spec_tag = specification_tag  # Specification ID (Doors)
        self.__coll_id = coll_id
        self.__coll_name = None
        self.__rd_id = None
        self.__rd_meas_sub_id = None
        self.__rd_ev_sub_id = None
        self.__doors_url = doors_url
        self.__exp_res = exp_res
        self.__desc = desc
        self.__asses = None
        self.__total_time = float(0)
        self.__total_dist = float(0)
        self.__mesdist_ressname = None
        self.__mestime_ressname = None
        self.__measid = []

    def __str__(self):
        """ return string text summary of the testcase
        """
        txt = "Testcase: '" + self.__name + "' DoorsId: '" + self.__spec_tag + "' \n"
        for res in self.GetResults(None):
            txt += str(res)
        return txt

    def GetName(self):  # pylint: disable=C0103
        """ Get the Name of the testcase e.g. "Dropin Rate", "EOL initialzation"

        :return: name of the test case as String e.g. "ALN EOL State"
        """

        return self.__name

    def GetSpecTag(self):  # pylint: disable=C0103
        """
        Get Doors ID of the testcase also known as Test Case identifier e.g. "ACC_TC_001_001"

        :return: Specification tag as String
        """
        return self.__spec_tag

    def GetCollectionName(self):  # pylint: disable=C0103
        """
        Get Collectionname associated with Testcase e.g. "ARS400_acc_endurance"

        :return: Collection as String
        """
        return self.__coll_name

    def GetDoorsURL(self):  # pylint: disable=C0103
        """
        Get Doors URL
        e.g. "doors://rbgs854a:40000/?version=2&prodID=0&urn=urn:telelogic::1-503e822e5ec3651e-M-0001cbf1"

        :return: DOORS URL as String
        """
        return self.__doors_url

    def GetExpectedResult(self):  # pylint: disable=C0103
        """
        Get Expected Result of the testcase
        e.g. "average error < .053" , "dropin rate< 1.55"

        :return: Expected result of the testcase as String
        """
        return self.__exp_res

    def GetDescription(self):  # pylint: disable=C0103
        """
        Get Testcase Description text

        :return: Test case Description as String
        """
        return self.__desc

    def GetTestSteps(self, name=None, spectag=None):  # pylint: disable=C0103
        """
        Get list of teststeps under the current Testcase or a specific
        teststep based on filter criteria of passed argument

        :param name:TestStep Name
        :type name: String
        :param spectag: TestpStep Specification Tag from DOORS
        :type spectag: String
        """
        if name is None and spectag is None:
            return self.__teststeps
        else:
            for teststep in self.__teststeps:
                if name is not None and spectag is None:
                    if name == teststep.GetName():
                        return teststep
                if name is None and spectag is not None:
                    if spectag == teststep.GetSpecTag():
                        return teststep
                if name is not None and spectag is not None:
                    if name == teststep.GetName() and spectag == teststep.GetSpecTag():
                        return teststep
            return None

    def GetAssessment(self):  # pylint: disable=C0103
        """
        Get Assessment of the testcase which evaluated based on the Assessment of TestSteps
        The testcase Assessment is not Stored or Loaded from Database
        """
        if len(self.__teststeps) > 0:
            self.__asses = self.__EvaluateAssessment()
        else:
            self.__asses = ValAssessment(user_id=None,
                                         wf_state=ValAssessmentWorkFlows.ASS_WF_AUTO,
                                         ass_state=ValAssessmentStates.NOT_ASSESSED,
                                         ass_comment="Couldnt Evaluated Assessment because"
                                         + "teststep are not loaded or available",
                                         issue="Issues to be assigned in invidual Teststeps if needed")
        return self.__asses

    def __EvaluateAssessment(self):  # pylint: disable=C0103,R0912
        """
        Automatic Assessment evaluate function for TestCase
        """
        ts_ass_states = []
        comment = ""
        asses_date = None
        userid = None
        for teststep in self.__teststeps:
            assess = teststep.GetAssessment()
            if assess is None:
                ts_ass_states.append(ValAssessmentStates.NOT_ASSESSED)
                comment += "teststep: %s has no Assessment available\n" % teststep.GetName()
            else:
                if assess.ass_state == ValAssessmentStates.FAILED:
                    comment += "teststep: %s is Failed\n" % teststep.GetName()
                elif assess.ass_state == ValAssessmentStates.NOT_ASSESSED:
                    comment += "teststep: %s is Not Assessed\n" % teststep.GetName()
                elif assess.ass_state == ValAssessmentStates.INVESTIGATE:
                    comment += "teststep: %s has pending investigation\n" % teststep.GetName()
                elif assess.ass_state == ValAssessmentStates.PASSED:
                    comment += "teststep: %s is Passed\n" % teststep.GetName()
                else:
                    comment += "teststep: %s Assessment is Unkown \n" % teststep.GetName()
                    ts_ass_states.append(ValAssessmentStates.FAILED)
                ts_ass_states.append(assess.ass_state)
                if asses_date is not None:
                    dates = [asses_date, assess.date]  # Take max from last two dates
                    last_date = max(dates)
                    if dates.index(last_date) > 0:  # If there is new max update userid and date
                        asses_date = last_date
                        userid = assess.user_id
                else:
                    asses_date = assess.date  # The 1st userid and date to be taken
                    userid = assess.user_id

        if ValAssessmentStates.FAILED in ts_ass_states:
            asses_state = ValAssessmentStates.FAILED
        elif ValAssessmentStates.NOT_ASSESSED in ts_ass_states:
            asses_state = ValAssessmentStates.NOT_ASSESSED
        elif ValAssessmentStates.INVESTIGATE in ts_ass_states:
            asses_state = ValAssessmentStates.INVESTIGATE
        else:
            asses_state = ValAssessmentStates.PASSED

        return ValAssessment(user_id=userid,
                             wf_state=ValAssessmentWorkFlows.ASS_WF_AUTO,
                             ass_state=asses_state,
                             ass_comment=comment,
                             date_time=asses_date,
                             issue="Issues to be assigned in invidual Teststeps if needed")

    def __IsSubType(self, dbi_val, rdid):  # pylint: disable=R0201,C0103
        """ Is the result descriptor a sub-type

        :param dbi_val: Validation Database interface
        :type dbi_val: database interface object which is instance of OracleValResDB or  SQLite3ValResDB
                        to target Database oracle or sqlite respectively
        :param rdid: Result Descriptor Identifier to be checked
        :type rdid: int
        :return: True on match otherwise False
        """
        sub_type_list = [ValTestcase.SUB_MEASRES, ValTestcase.SUB_EVENTS]

        rec_rd = dbi_val.get_result_descriptor_with_id(rdid)
        if rec_rd is not None:
            type_name = rec_rd["TYPE_" + COL_NAME_RESULTTYPE_NAME]
            if type_name in sub_type_list:
                return True
        return False

    def Load(self,  # pylint: disable=C0103,R0912,R0913,R0915
             dbi_val, dbi_gbl, dbi_cat,
             testrun_id,
             obs_name=None,
             level=ValSaveLoadLevel.VAL_DB_LEVEL_BASIC,
             cons_key=None,
             rd_id=None):
        """ Load the testcase settings from database

        Note: Events and File results under the testcase are loaded separately
        with additional Load methods LoadEvents() and LoadFileResults() respectively

        :param dbi_val: Validation Database interface
        :type dbi_val: database interface object which is instance of OracleValResDB or  SQLite3ValResDB
                        to target Database oracle or sqlite respectively
        :param dbi_gbl: Global Database interface
        :type dbi_gbl:  database interface object which is instance of  OracleGblDB or SQLite3GblDB
                        to target Database oracle or sqlite respectively
        :param dbi_cat: Catalog Database interface
        :type dbi_cat: database interface object which is instance of OracleRecCatalogDB or  OracleRecCatalogDB
                        to target Database oracle or sqlite respectively
        :param testrun_id: id of testrun
        :param obs_name: Observer Name e.g. "ACC_DROPIN_OBSERVER"
        :type obs_name:  String
        :param level: Database load/store level e.g. `ValSaveLoadLevel.VAL_DB_LEVEL_INFO`
                      default is VAL_DB_LEVEL_BASIC:

                        VAL_DB_LEVEL_BASIC
                            --> Load only Test case basic information,
                            e.g. specification doors url and test case name, test case result, expected result
                        VAL_DB_LEVEL_INFO
                            --> include load of VAL_DB_LEVEL_BASIC and additionally load
                            TestSteps under the given Testcase and their assessment
                        VAL_DB_LEVEL_ALL
                            --> include load of VAL_DB_LEVEL_INFO and additionally load plot,
                            images and complete detail associated with test case result

        :type level: int
        :param cons_key: constraint key for future purpose
        :param rd_id: Result Descriptor Identifier for direct load (optional)
        :type rd_id: string
        :return: True for successful Load, False for failed Load,
                 Exception will be thrown in case of insufficient mandatory parameter
        """
        if self.__CheckDBI(dbi_val, dbi_gbl, dbi_cat) is False:
            return False

        if level & ValSaveLoadLevel.VAL_DB_LEVEL_1:
            if rd_id is not None:
                self.__rd_id = rd_id
                if self.__name is None or self.__coll_id is None or self.__spec_tag is None:
                    rd_rec = dbi_val.get_result_descriptor_with_id(self.__rd_id)
                    if COL_NAME_RESDESC_NAME in rd_rec:
                        self.__name = rd_rec[COL_NAME_RESDESC_NAME]
                        self.__coll_id = rd_rec[COL_NAME_RESDESC_COLLID]
                        self.__spec_tag = rd_rec[COL_NAME_RESDESC_REFTAG]
                        self.__doors_url = rd_rec[COL_NAME_RESDESC_DOORS_URL]
                        self.__exp_res = rd_rec[COL_NAME_RESDESC_EXPECTRES]
                        self.__desc = rd_rec[COL_NAME_RESDESC_DESCRIPTION]

            else:
                rd_rec = dbi_val.get_result_descriptor(self.__coll_id, self.__name,
                                                       ev_type_name=self.TESTCASE_TYPE)
                if len(rd_rec) == 1:
                    rd_rec = rd_rec[0]
                    self.__rd_id = rd_rec[COL_NAME_RESDESC_ID]
                    self.__spec_tag = rd_rec[COL_NAME_RESDESC_REFTAG]
                    self.__doors_url = rd_rec[COL_NAME_RESDESC_DOORS_URL]
                    self.__exp_res = rd_rec[COL_NAME_RESDESC_EXPECTRES]
                    self.__desc = rd_rec[COL_NAME_RESDESC_DESCRIPTION]

            res = ValResult(self.__name, self.TESTCASE_TYPE, None, self.TESTCASE_UNIT, self.__spec_tag)
            if not res.Load(dbi_val, dbi_gbl, testrun_id=testrun_id, coll_id=self.__coll_id, rd_id=self.__rd_id,
                            obs_name=obs_name, level=ValSaveLoadLevel.VAL_DB_LEVEL_BASIC, cons_key=cons_key):
                return False

            if self.__mesdist_ressname is None:
                self.__mesdist_ressname = self.__name

            if self.__mestime_ressname is None:
                self.__mestime_ressname = self.__name

            if self.__coll_name is None:
                self.__coll_name = dbi_cat.get_collection_name(self.__coll_id)

            if self.__rd_id is None:
                self._log.error("Testcase unknown, check the settings")
                return False

            rd_list = dbi_val.get_resuls_descriptor_child_list(self.__rd_id)
            self.__testresults = []
            for rdid in rd_list:
                rd_rec = dbi_val.get_result_descriptor_with_id(rdid)
                try:
                    if self.__IsSubType(dbi_val, rdid) is False:
                        res = ValResult()
                        if res.Load(dbi_val, dbi_gbl, testrun_id, self.__coll_id, rd_id=rdid,
                                    obs_name=obs_name, level=level, cons_key=cons_key) is True:
                            self.__testresults.append(res)
                except StandardError:
                    pass

        if level & ValSaveLoadLevel.VAL_DB_LEVEL_3:
            if rd_id is not None:
                self.__rd_id = rd_id
            else:
                self.__rd_id = dbi_val.get_result_descriptor_id(self.__coll_id, self.__name,
                                                                ev_type_name=self.TESTCASE_TYPE)
            rd_list = dbi_val.get_resuls_descriptor_child_list(self.__rd_id)

            # clean up the existing list of testcase results
#            self.__teststep_ids = []
            self.__testresults = []

            for rdid in rd_list:
                try:
                    rdi = dbi_val.get_result_descriptor_with_id(rdid)
                    rd_type_name = rdi["TYPE_" + COL_NAME_RESULTTYPE_NAME]
                    if self.SUB_MEASRES in rd_type_name:  # Don't add result for meas file sub Struct
                        self.__rd_meas_sub_id = rdid  # Sub Struct. for File Result Descriptors
                    elif self.SUB_EVENTS in rd_type_name:
                        self.__rd_ev_sub_id = rdid  # Sub Struct. for Event Result Descriptors
                    elif self.SUB_TEST_STEP in rd_type_name:
                        self.__teststepsub_id = rdid
                    elif self.SUB_TEST_DETAIL in rd_type_name:
                        self.__testdetailsub_id = rdid
                    else:
                        res = ValResult()
                        res.Load(dbi_val, dbi_gbl, testrun_id, self.__coll_id, rd_id=rdid,
                                 obs_name=obs_name, level=level, cons_key=cons_key)
                        self.__testresults.append(res)
                except StandardError:
                    pass

            self.__total_dist = dbi_val.get_test_run_sum_value(testrun_id, self.__mesdist_ressname,
                                                               self.MEAS_DIST_PROCESS, [self.__coll_id],
                                                               meas_id=None)
            self.__total_time = dbi_val.get_test_run_sum_value(testrun_id, self.__mestime_ressname,
                                                               self.MEAS_TIME_PROCESS, [self.__coll_id],
                                                               meas_id=None)
            self.LoadTestSteps(dbi_val, dbi_gbl, dbi_cat, testrun_id, coll_id=self.__coll_id,
                               obs_name=obs_name, level=level)
            self.LoadTestDetailSummary(dbi_val, dbi_gbl, dbi_cat, testrun_id, coll_id=self.__coll_id,
                                       obs_name=obs_name, level=level)

        return True

    def LoadFileResults(self,  # pylint: disable=C0103,R0913
                        dbi_val, dbi_gbl, dbi_cat,
                        testrun_id,
                        obs_name=None,
                        level=ValSaveLoadLevel.VAL_DB_LEVEL_BASIC,
                        cons_key=None, measid=None):
        """ Load the file results under the testcase from database

        :param dbi_val: Validation Database interface
        :type dbi_val: database interface object which is instance of OracleValResDB or  SQLite3ValResDB
                        to target Database oracle or sqlite respectively
        :param dbi_gbl: Global Database interface
        :type dbi_gbl:  database interface object which is instance of  OracleGblDB or SQLite3GblDB
                        target Database oracle or sqlite respectively
        :param dbi_cat: Catalog Database interface
        :type dbi_cat: database interface object which is instance of OracleRecCatalogDB or  OracleRecCatalogDB
                        to target Database oracle or sqlite respectively
        :param testrun_id: Testrun Identifier
        :type testrun_id: int
        :param obs_name: Observer Name  e.g. "ACC_DROPIN_OBSERVER"
        :type obs_name: string
        :param level: Database load/store level e.g. `ValSaveLoadLevel.VAL_DB_LEVEL_INFO` default is VAL_DB_LEVEL_BASIC

                      VAL_DB_LEVEL_BASIC
                        --> Load only basic information e.g. specification tag(if exist) doors url (if exist),
                        result name, result value, expected result(if exist)
                      VAL_DB_LEVEL_INFO
                        --> include load of VAL_DB_LEVEL_BASIC and additionally load its assessments
                      VAL_DB_LEVEL_ALL
                        --> include load of VAL_DB_LEVEL_INFO and additionally load Plots images and
                        array of result values i.e. complete detail measurement results
        :type  level: int
        :param cons_key: contraint key for future purpose
        """
        if self.__CheckDBI(dbi_val, dbi_gbl, dbi_cat) is False:
            return False

        # load measurement ids and name of the collection
        if measid is None:
            rec_files = dbi_cat.get_collection_measurements(self.__coll_id, False, True, True)
        else:
            rec_files = {str(measid): measid}

        # clean up the existing list of files results
        self.__measresults = []
        self.__measid = []
        if self.__rd_meas_sub_id is not None:
            rd_list = dbi_val.get_resuls_descriptor_child_list(self.__rd_meas_sub_id)
            for rdid in rd_list:
                for mid in rec_files.itervalues():
                    try:
                        res = ValResult()
                        if res.Load(dbi_val, dbi_gbl, testrun_id, self.__coll_id, meas_id=mid, rd_id=rdid,
                                    obs_name=obs_name, level=level, cons_key=cons_key):
                            self.__measresults.append(res)
                            self.__measid.append(res.GetMeasId())
                    except StandardError:
                        pass
        self.__measid = list(set(self.__measid))  # remove duplicates
        return True

    def LoadEvents(self, dbi_val, dbi_gbl, dbi_cat, testrun_id,  # pylint: disable=C0103
                   obs_name=None, level=ValSaveLoadLevel.VAL_DB_LEVEL_BASIC, cons_key=None,
                   event_search_path=None, event_filter=None, beginabsts=None, endabsts=None,
                   asmt_state=None, filter_cond=None, measid=None):
        # pylint: disable= R0913
        """
        Load Events Under the test case

        :param dbi_val: Validation Database interface
        :type dbi_val: database interface object which is instance of OracleValResDB or  SQLite3ValResDB
                       to target Database oracle or sqlite respectively
        :param dbi_gbl: Global Database interface
        :type dbi_gbl: database interface object which is instance of  OracleGblDB or SQLite3GblDB
                       to target Database oracle or sqlite respectively
        :param dbi_cat: Catalog Database interface
        :type dbi_cat: database interface object which is instance of OracleRecCatalogDB or  OracleRecCatalogDB
                       to target Database oracle or sqlite respectively
        :param testrun_id: Testrun Identifier
        :type testrun_id: int
        :param obs_name: Observer Name  e.g. "ACC_DROPIN_OBSERVER"
        :type obs_name: string
        :param level: Database load/store level e.g. `ValSaveLoadLevel.VAL_DB_LEVEL_INFO` default is VAL_DB_LEVEL_BASIC

                      VAL_DB_LEVEL_BASIC
                        --> Load only basic information of Events
                      VAL_DB_LEVEL_INFO
                        --> include load of VAL_DB_LEVEL_BASIC and additionally load its assessments
                      VAL_DB_LEVEL_ALL
                        --> include load of VAL_DB_LEVEL_INFO and additionally load all the Event
                        Attributes values

        :param cons_key: For Future Purpose
        :param event_search_path: list of Directory path where python Module
                                  containing Event Classes definition. If the value is not passed then
                                  typed class will be generated runtime inherited from `ValBaseEvent`. This improve
                                  performance and avoid unnecessary python module import.
                                  Use this argument only if you have defined additional method to.
        :type event_search_path: list
        :param event_filter: Instance of ValEventFilter class used to apply complex
                             filter criteria on Event Attribute values, Assessment state,
                             BeginAbsts, Endabsts time stamps;
                             Read Documentation of `ValEventFilter` Class for further details;
                             Default value None which makes depending on basic filter criteria parameters given below
        :type event_filter: ValEventFilter
        :param beginabsts: basic filter criteria to load event(s) with given Begin Timestamp
        :type beginabsts: int
        :param endabsts: basic filter criteria of End Timestamp of to load event(s)
                         which has End Timestamp to specific value
        :type endabsts: int
        :param asmt_state: Basic Filter criteria to Load Event having Specific
                           Assessment state e.g. "Invalid", "Not Assessed"
        :type asmt_state: string
        :param filter_cond: Filter map name is written in Filter config XML file e.g. "Dropout_rate_filter"
                           parameter event_filter must be set as prerequiste which manages the Complex Filter
        :type filter_cond: String

        Note: If the event_filter, beginabsts, endabsts, asmt_state and filter_cond are None
        then No Filter criteria will be applied and All the Events Under testcase will be loaded
        """

        if self.__CheckDBI(dbi_val, dbi_gbl, dbi_cat) is False:
            return False

        self.__events = ValEventList(event_search_path, event_filter)

        return self.__events.Load(dbi_val, dbi_gbl, testrun_id, self.__coll_id, measid, self.__rd_ev_sub_id,
                                  obs_name, level, beginabsts, endabsts, asmt_state, filter_cond, cons_key)

    def LoadTestSteps(self, dbi_val, dbi_gbl, dbi_cat, testrun_id, coll_id=None,  # pylint: disable=C0103,R0913
                      obs_name=None, level=ValSaveLoadLevel.VAL_DB_LEVEL_BASIC):
        """
        Load TestSteps under the current test case

        :param dbi_val: Validation Database interface
        :type dbi_val: database interface object which is instance of OracleValResDB or  SQLite3ValResDB
                       to target Database oracle or sqlite respectively
        :param dbi_gbl: Global Database interface
        :type dbi_gbl: database interface object which is instance of  OracleGblDB or SQLite3GblDB
                       to target Database oracle or sqlite respectively
        :param dbi_cat: Catalog Database interface
        :type dbi_cat: database interface object which is instance of OracleRecCatalogDB or  OracleRecCatalogDB
                       to target Database oracle or sqlite respectively
        :param testrun_id: Testrun Identifier
        :type testrun_id: int
        :param obs_name: Observer Name  e.g. "ACC_DROPIN_OBSERVER"
        :type obs_name: string
        :param level: Database load/store level e.g. `ValSaveLoadLevel.VAL_DB_LEVEL_INFO` default is VAL_DB_LEVEL_BASIC

                      VAL_DB_LEVEL_BASIC
                        --> Load only basic information e.g. specification tag(if exist) doors url (if exist),
                        Test step name, TestStep value, expected result(if exist)
                      VAL_DB_LEVEL_INFO
                        --> include load of VAL_DB_LEVEL_BASIC and additionally load its assessments
                      VAL_DB_LEVEL_ALL
                        --> include load of VAL_DB_LEVEL_INFO and additionally load Plots images and
                        array of the Test Step i.e. complete detail of Test Step

        """
        sub_list = self.__LoadTestCaseSub(dbi_val, dbi_gbl, dbi_cat, testrun_id, coll_id, obs_name,
                                          level, self.__teststepsub_id)
        if type(sub_list) is list:
            self.__teststeps = sub_list
        else:
            return sub_list

    def LoadTestDetailSummary(self, dbi_val, dbi_gbl, dbi_cat, testrun_id, coll_id=None,  # pylint: disable=C0103,R0913
                              obs_name=None, level=ValSaveLoadLevel.VAL_DB_LEVEL_BASIC):
        """
        Load Detail Summary under the current test case

        :param dbi_val: Validation Database interface
        :type dbi_val: database interface object which is instance of OracleValResDB or  SQLite3ValResDB
                       to target Database oracle or sqlite respectively
        :param dbi_gbl: Global Database interface
        :type dbi_gbl: database interface object which is instance of  OracleGblDB or SQLite3GblDB
                       to target Database oracle or sqlite respectively
        :param dbi_cat: Catalog Database interface
        :type dbi_cat: database interface object which is instance of OracleRecCatalogDB or  OracleRecCatalogDB
                       to target Database oracle or sqlite respectively
        :param testrun_id: Testrun Identifier
        :type testrun_id: int
        :param coll_id: id of collection
        :param obs_name: Observer Name  e.g. "ACC_DROPIN_OBSERVER"
        :type obs_name: string
        :param level: Database load/store level e.g. `ValSaveLoadLevel.VAL_DB_LEVEL_INFO` default is VAL_DB_LEVEL_BASIC

                      VAL_DB_LEVEL_BASIC
                        --> Load only basic information e.g. specification tag(if exist) doors url(
                        if exist),Summary result name, value, expected result(if exist)
                      VAL_DB_LEVEL_INFO
                        --> include load of VAL_DB_LEVEL_BASIC and additionally load its assessments
                      VAL_DB_LEVEL_ALL
                        --> include load of VAL_DB_LEVEL_INFO and additionally load Plots images and
                        array of the summary result i.e. complete detail of Summary Result
        """
        sub_list = self.__LoadTestCaseSub(dbi_val, dbi_gbl, dbi_cat, testrun_id, coll_id,
                                          obs_name, level, self.__testdetailsub_id, subtype="ValResult")
        if type(sub_list) is list:
            self.__testsummarydetails = sub_list
        else:
            return sub_list

    def __LoadTestCaseSub(self, dbi_val, dbi_gbl, dbi_cat, testrun_id, coll_id,  # pylint: disable=C0103,R0913
                          obs_name, level, parent_id, subtype="ValTestStep"):

        """
        Generic Load function to load list of results under the given parent_id

        :param dbi_val: Validation Database interface
        :type dbi_val: database interface object which is instance of OracleValResDB or  SQLite3ValResDB
                       to target Database oracle or sqlite respectively
        :param dbi_gbl: Global Database interface
        :type dbi_gbl: database interface object which is instance of  OracleGblDB or SQLite3GblDB
                       to target Database oracle or sqlite respectively
        :param dbi_cat: Catalog Database interface
        :type dbi_cat: database interface object which is instance of OracleRecCatalogDB or  OracleRecCatalogDB
                        to target Database oracle or sqlite respectively
        :param testrun_id: Testrun Identifier
        :type testrun_id: int
        :param obs_name: Observer Name  e.g. "ACC_DROPIN_OBSERVER"
        :type obs_name: string
        :param level: Database load/store level e.g. `ValSaveLoadLevel.VAL_DB_LEVEL_INFO` default is VAL_DB_LEVEL_BASIC

                      VAL_DB_LEVEL_BASIC
                          --> Load only basic information e.g. specification tag(if exist) doors url(
                          if exist), result name, value, expected result(if exist)
                      VAL_DB_LEVEL_INFO
                          --> include load of VAL_DB_LEVEL_BASIC and additionally load its assessments
                      VAL_DB_LEVEL_ALL
                          --> include load of VAL_DB_LEVEL_INFO and additionally load Plots images and
                          array of the result i.e. complete detail of  Result

        :param parent_id: parent id representing location in hierarchy
        :type parent_id: int
        """
        # pylint: disable= R0913
        sub_list = []
        if self.__CheckDBI(dbi_val, dbi_gbl, dbi_cat) is False:
            return False

        if parent_id is not None:
            rd_list = dbi_val.get_resuls_descriptor_child_list(parent_id)
            for rd_id in rd_list:
                if subtype == "ValTestStep":
                    sub_res = ValTestStep()
                    if sub_res.Load(dbi_val, dbi_gbl, testrun_id, coll_id=coll_id, rd_id=rd_id,
                                    obs_name=obs_name, level=level) is True:
                        sub_list.append(sub_res)
                else:
                    sub_res = ValResult()
                    sub_res.Load(dbi_val, dbi_gbl, testrun_id, coll_id=coll_id, rd_id=rd_id,
                                 obs_name=obs_name, level=level)
                    sub_list.append(sub_res)

        return sub_list

    def Save(self,  # pylint: disable=C0103,R0912,R0913,R0914,R0915
             dbi_val,
             dbi_gbl,
             testrun_id,
             obs_name=None,
             level=ValSaveLoadLevel.VAL_DB_LEVEL_BASIC,
             cons_key=None):
        """ Save the TestCase to the database using the given load/store level

        :param dbi_val: Validation Database interface
        :type dbi_val: database interface object which is instance of OracleValResDB or  SQLite3ValResDB
                       to target Database oracle or sqlite respectively
        :param dbi_gbl: Global Database interface
        :type dbi_gbl: database interface object which is instance of  OracleGblDB or SQLite3GblDB
                       to target Database oracle or sqlite respectively
        :param testrun_id: Testrun Identifier
        :type testrun_id: int
        :param obs_name: Observer Name  e.g. "ACC_DROPIN_OBSERVER"
        :type obs_name: string
        :param level: Database load/store level e.g. `ValSaveLoadLevel.VAL_DB_LEVEL_INFO` default is VAL_DB_LEVEL_BASIC

                      VAL_DB_LEVEL_BASIC
                          --> Save only basic information e.g. specification tag(if exist) doors url(if exist),
                          Test steps, expected result(if exist), TestCase results its assessments Test Steps
                          and Test Case results
                      VAL_DB_LEVEL_INFO
                          --> include save operation of VAL_DB_LEVEL_BASIC and additionally save
                              TestSteps under the given Testcase and their assessment
                      VAL_DB_LEVEL_ALL
                          --> include Save operation of VAL_DB_LEVEL_INFO and additionally save Plots
                          images and array of the Test Case results, TesSteps and also save File results
                          and their plot, images i.e. complete detail Result data which includes under Test Case
                          including the Assessment

        :param cons_key: For Future Purpose
        """
        if self.__CheckDBI(dbi_val, dbi_gbl, None) is False:
            return False

        if dbi_val.get_testrun_lock(tr_id=testrun_id) == 1:
            self._log.error("Test Case %s save is failed due to locked testrun " % (self.__name))
            return False
        # load the result descriptor. If not exist, generate a new one
        self.__rd_id = dbi_val.get_result_descriptor_id(self.__coll_id, self.__name, ev_type_name=self.TESTCASE_TYPE)
        if self.__rd_id is None:
            unit_id = dbi_gbl.get_unit_id_by_name(self.TESTCASE_UNIT)
            if self.GetSpecTag() == "":
                raise StandardError("Door ID is mandatory e.g. EM_TC_001_001")
            else:
                if self.__CheckTestCaseSpecTag(self.__spec_tag) is False:
                    raise StandardError("Door ID is Not matching Standard format e.g. EM_TC_001_001")

            self.__rd_id = dbi_val.add_result_descriptor(self.TESTCASE_TYPE, self.__name,
                                                         self.__coll_id, unit_id,
                                                         self.__spec_tag, None,
                                                         self.__doors_url, self.__exp_res,
                                                         self.__desc)

        # Sub Results for the Measurements
        res_type_id = dbi_val.get_result_type_id(self.SUB_MEASRES)
        if res_type_id is None:
            result_type = {COL_NAME_RESULTTYPE_NAME: self.SUB_MEASRES,
                           COL_NAME_RESULTTYPE_DESC: 'Measurement Specific Substruct',
                           COL_NAME_RESULTTYPE_CLASS: 'None'}
            dbi_val.add_result_type(result_type)
            res_type_id = dbi_val.get_result_type_id(self.SUB_MEASRES)

        rd_id_meas_sub = dbi_val.get_result_descriptor_id(self.__coll_id, self.__name, ev_type_id=res_type_id)
        if rd_id_meas_sub is None:
            unit_id = dbi_gbl.get_unit_id_by_name(self.TESTCASE_UNIT)
            rd_id_meas_sub = dbi_val.add_result_descriptor(self.SUB_MEASRES, self.__name,
                                                           self.__coll_id, unit_id,
                                                           None, self.__rd_id)
        # Sub Events for the Measurements
        if len(self.__events.GetEvents()) > 0:
            ev_type_id = dbi_val.get_result_type_id(self.SUB_EVENTS)
            if ev_type_id is None:
                result_type = {COL_NAME_RESULTTYPE_NAME: self.SUB_EVENTS,
                               COL_NAME_RESULTTYPE_DESC: 'Measurement Specific Events',
                               COL_NAME_RESULTTYPE_CLASS: 'None'}
                dbi_val.add_result_type(result_type)
                ev_type_id = dbi_val.get_result_type_id(self.SUB_EVENTS)

            rd_id_ev_sub = dbi_val.get_result_descriptor_id(self.__coll_id, self.__name, ev_type_id=ev_type_id)
            if rd_id_ev_sub is None:
                unit_id = dbi_gbl.get_unit_id_by_name(self.TESTCASE_UNIT)
                rd_id_ev_sub = dbi_val.add_result_descriptor(self.SUB_EVENTS,
                                                             self.__name,
                                                             self.__coll_id,
                                                             unit_id,
                                                             None, self.__rd_id)
        if len(self.__teststeps) > 0:
            ts_type_id = dbi_val.get_result_type_id(self.SUB_TEST_STEP)
            if ts_type_id is None:
                result_type = {COL_NAME_RESULTTYPE_NAME: self.SUB_TEST_STEP,
                               COL_NAME_RESULTTYPE_DESC: 'Test Steps under Testcase',
                               COL_NAME_RESULTTYPE_CLASS: 'None'}
                dbi_val.add_result_type(result_type)
                ts_type_id = dbi_val.get_result_type_id(self.SUB_TEST_STEP)
            self.__teststepsub_id = dbi_val.get_result_descriptor_id(self.__coll_id, self.__name,
                                                                     ev_type_id=ts_type_id)
            if self.__teststepsub_id is None:
                unit_id = dbi_gbl.get_unit_id_by_name(self.TESTCASE_UNIT)
                self.__teststepsub_id = dbi_val.add_result_descriptor(self.SUB_TEST_STEP,
                                                                      self.__name,
                                                                      self.__coll_id,
                                                                      unit_id,
                                                                      None, self.__rd_id)
        if len(self.__testsummarydetails) > 0:
            td_type_id = dbi_val.get_result_type_id(self.SUB_TEST_DETAIL)
            if td_type_id is None:
                result_type = {COL_NAME_RESULTTYPE_NAME: self.SUB_TEST_DETAIL,
                               COL_NAME_RESULTTYPE_DESC: 'Test Detail under Testcase',
                               COL_NAME_RESULTTYPE_CLASS: 'None'}
                dbi_val.add_result_type(result_type)
                td_type_id = dbi_val.get_result_type_id(self.SUB_TEST_DETAIL)
            self.__testdetailsub_id = dbi_val.get_result_descriptor_id(self.__coll_id, self.__name,
                                                                       ev_type_id=td_type_id)
            if self.__testdetailsub_id is None:
                unit_id = dbi_gbl.get_unit_id_by_name(self.TESTCASE_UNIT)
                self.__testdetailsub_id = dbi_val.add_result_descriptor(self.SUB_TEST_DETAIL, self.__name,
                                                                        self.__coll_id, unit_id,
                                                                        None, self.__rd_id)

        if level & ValSaveLoadLevel.VAL_DB_LEVEL_2:
            # Save a default result to get the link to the testrun
            res = ValResult(self.__name, self.TESTCASE_TYPE, None, self.TESTCASE_UNIT, self.__spec_tag, None)
            res.Save(dbi_val, dbi_gbl, testrun_id, self.__coll_id, None, obs_name, None, level, cons_key)

            for tc_res in self.__testresults:
                tc_res.Save(dbi_val, dbi_gbl,
                            testrun_id, self.__coll_id, None,
                            obs_name, self.__rd_id, level, cons_key)
            for test_step in self.__teststeps:
                test_step.Save(dbi_val, dbi_gbl, testrun_id, self.__coll_id, obs_name=obs_name,
                               parent_id=self.__teststepsub_id, level=level, cons_key=cons_key)

            for test_sumdetail in self.__testsummarydetails:
                test_sumdetail.Save(dbi_val, dbi_gbl, testrun_id, self.__coll_id, obs_name=obs_name,
                                    parent_id=self.__testdetailsub_id, level=level, cons_key=cons_key)

        if level & ValSaveLoadLevel.VAL_DB_LEVEL_3:
            # save the measurements specific sub results
            for meas_res in self.__measresults:
                meas_res.Save(dbi_val, dbi_gbl,
                              testrun_id, self.__coll_id, None,
                              obs_name, rd_id_meas_sub, level, cons_key)
            # save the events
            if len(self.__events.GetEvents()) > 0:
                self.__events.Save(dbi_val, dbi_gbl, testrun_id, self.__coll_id,
                                   obs_name, rd_id_ev_sub, level, cons_key)
        dbi_val.commit()

    def Update(self, dbi_val, dbi_gbl, obs_name=None,  # pylint: disable=C0103,R0913
               level=ValSaveLoadLevel.VAL_DB_LEVEL_BASIC, cons_key=None):
        """
        Update Existing testcase which was loaded or saved earlier.

        This will only update the assessment and values
        of TestSteps, SummaryDetails and Testcase Results. Measurement Results must updated individually with
        Update method from ValResult Class.

        Event update is not support at the moment

        :param dbi_val: Validation Database interface
        :type dbi_val: database interface object which is instance of OracleValResDB or  SQLite3ValResDB
                        to target Database oracle or sqlite respectively
        :param dbi_gbl: Global Database interface
        :type dbi_gbl:  database interface object which is instance of  OracleGblDB or SQLite3GblDB
                        to target Database oracle or sqlite respectively
        :param obs_name: Observer Name  e.g. "ACC_DROPIN_OBSERVER"
        :type obs_name: string
        :param level: Database load/store level e.g. `ValSaveLoadLevel.VAL_DB_LEVEL_INFO` default is VAL_DB_LEVEL_BASIC

                      VAL_DB_LEVEL_ALL
                                          --> include Save operation of VAL_DB_LEVEL_INFO and additionally save
                                          Plots images and array of the Test Case results, TesSteps
                                          and also save File results and their plot, images,
                                          i.e. complete detail Result data which includes under Test
                                          Case including the Assessment

        :param cons_key: Not Used at the moment
        :type cons_key: None
        """
        _ = cons_key

        if level & ValSaveLoadLevel.VAL_DB_LEVEL_2:
            for tc_res in self.__testresults:
                tc_res.Update(dbi_val, dbi_gbl, obs_name, level=level)

            for test_step in self.__teststeps:
                test_step.Update(dbi_val, dbi_gbl, obs_name, level=level)

            for test_sumdetail in self.__testsummarydetails:
                test_sumdetail.Update(dbi_val, dbi_gbl, obs_name, level=level)

            dbi_val.commit()

#        To be extended for Measurment results and Events if need based on user Change request
            if level & ValSaveLoadLevel.VAL_DB_LEVEL_3:
                pass

    def AddSummaryDetailResult(self, result):  # pylint: disable=C0103
        """
        Add result to be include in Summary section of the report

        :param result: result contain different values
        :type result: ValResult
        """
        if issubclass(result.__class__, ValResult):
            self.__testsummarydetails.append(result)
        else:
            raise StandardError("Instance of ValResult was expected in arguement")

    def AddResult(self, result):  # pylint: disable=C0103
        """
        Add a new result to the Testcase
        """

        if issubclass(result.__class__, ValResult):
            if result.GetAssessment() is None:
                comment = "default automatically assigned - Not assessed."
                assessment = ValAssessment(user_id=None,
                                           wf_state=ValAssessmentWorkFlows.ASS_WF_AUTO,
                                           ass_state=ValAssessmentStates.NOT_ASSESSED,
                                           ass_comment=comment)
                self._log.warning("Default Assesssment: not Assessed added for Testcase result" +
                                  " %s will be saved" % result.GetName())
                result.AddAssessment(assessment)
            self.__testresults.append(result)
        else:
            raise StandardError("Instance of ValResult was expected in arguement")

    def AddMeasResult(self, result):  # pylint: disable=C0103
        """
        Add a new result for a measurement

        The result is normally available on development level and takes measurement specific results

        Note: Read the Documentation of `ValResult` Class

        :param result: Result of type `ValResult` containing value which
                       could be `ValidationPlot`, Histogram, image, ValueVector, BaseValue
        :type result: ValResult
        """
        if issubclass(result.__class__, ValResult):
            if result.GetMeasId() is not None:
                self.__measresults.append(result)
            else:
                raise StandardError("Measid is mandatory for Measurement Results")

    def GetResults(self, measid=None, name=None):  # pylint: disable=C0103
        """
        Get the results of the Testcase fulfilling input argument criteria

        if both are passed then it will be AND relation

        :param measid: Measurement ID if measid provide then only list of results(MeasResult) specific to measid return
                       otherwise List of TestCaseResult will be return
        :type measid: int
        :param name: Result Name
        :type name: string
        """
        return self.__GetGenericResults(measid, name, self.__testresults)

    def GetSummaryResults(self, name=None):  # pylint: disable=C0103
        """
        Get the summary result of the Testcase fulfilling input argument criteria

        if name is None then the list of all summary detail results will be returned

        :param name: Result Name
        :type name: string
        """
        return self.__GetGenericResults(None, name, self.__testsummarydetails)

    def __GetGenericResults(self, measid, name, result_list):  # pylint: disable=C0103
        """
        Generic function to Get the result(s) of the Testcase fulfilling input argument criteria

        if both (measid and name) are passed then it will be AND relation

        :param measid: Measurement ID if measid provide then only list of results(MeasResult) specific to measid return
                       otherwise List of TestCaseResult will be return
        :type measid: int
        :param name: Result Name
        :type name: string
        """
        # pylint: disable= R0201
        res_list = []
        if measid is not None and name is None:
            for tc_res in result_list:
                if tc_res.GetMeasId() == measid:
                    res_list.append(tc_res)
            return res_list
        elif measid is None and name is not None:
            for tc_res in result_list:
                if tc_res.GetName() == name:
                    res_list.append(tc_res)
            return res_list
        elif measid is not None and name is not None:
            for tc_res in result_list:
                if tc_res.GetName() == name and tc_res.GetMeasId() == measid:
                    res_list.append(tc_res)
            return res_list
        else:
            return result_list

    def AddEvent(self, event):  # pylint: disable=C0103
        """ Add a new event result to the Testcase """
        return self.__events.AddEvent(event)

    def GetEvents(self, measid=None):  # pylint: disable=C0103
        """ Get the events of the Testcase

        :param measid: Measurement ID if argument given then return measurement specific events
                        otherwise return all events for the testcase
        :type measid: int
        """
        event_list = []

        if measid is None or measid == -1:
            return self.__events.GetEvents()
        else:
            for tc_event in self.__events.GetEvents():
                event_meas_id = tc_event.GetMeasId()
                if int(event_meas_id) == int(measid):
                    event_list.append(tc_event)

        return event_list

    def AddTestStep(self, test_step):  # pylint: disable=C0103
        """
        Add TestSTep to Test case

        :param test_step: object of teststep class
        :type test_step: ValTestStep
        """
        if isinstance(test_step, ValTestStep):
            if test_step.GetAssessment() is None:
                comment = "default automatically assigned - Not assessed."
                assessment = ValAssessment(user_id=None,
                                           wf_state=ValAssessmentWorkFlows.ASS_WF_AUTO,
                                           ass_state=ValAssessmentStates.NOT_ASSESSED,
                                           ass_comment=comment)
                test_step.AddAssessment(assessment)
            self.__teststeps.append(test_step)
        else:
            raise StandardError("Instance of ValTestStep was expected in arguement")

    def AddMeasDistTimeProcess(self, measid, ego_motion=None, distance=None, time=None):  # pylint: disable=C0103
        """
        Add DistanceTimeProcess for measurement under each test case.

        The total Time and
        Distance processed under each test will be Available as additional TestcaseResult
        on Loading the testcase

        :param ego_motion: instance of EgoMotion Class. if the argument is passed then
                            it has Precedence over distance, time argument will be ignore
        :type ego_motion: EgoMotion
        :param time: Time Process(Seconds) will be used if ego_motion is not provided
        :type time: int
        :param distance: Distance Process(Kilometer) will be used if ego_motion is not provided
        :type distance: int
        """
        if ego_motion is not None:
            if isinstance(ego_motion, EgoMotion):
                # Get Total Time in Seconds
                _, _, _, _, time = ego_motion.get_cycle_time_statistic()
                # Get Total Distance  and converted into KiloMeter
                distance = ego_motion.get_driven_distance() / 1000
#                distance = ego_motion.GetCycleTimeStatistic() / 1000
            else:
                raise StandardError("Instance of EgoMotion was expected in arguement")

        if self.__mesdist_ressname is None:
            self.__mesdist_ressname = self.__name

        if self.__mestime_ressname is None:
            self.__mestime_ressname = self.__name

        if distance is not None:
            dist_res = ValResult(name=self.__mesdist_ressname, res_type=self.MEAS_DIST_PROCESS, meas_id=measid,
                                 unit=GblUnits.UNIT_L_M, tag="", parent=None)
            dist_res.SetValue(BaseValue("", BaseUnit(GblUnits.UNIT_L_M, label="km"), distance))
#           dist_res.SetValue(distance)
            self.AddMeasResult(dist_res)
            self.__total_dist += distance

        if time is not None:
            time_res = ValResult(name=self.__mestime_ressname, res_type=self.MEAS_TIME_PROCESS, meas_id=measid,
                                 unit=GblUnits.UNIT_L_S, tag="", parent=None)
            time_res.SetValue(BaseValue("", BaseUnit(GblUnits.UNIT_L_S, label="s"), time))
#            time_res.SetValue(time)
            self.AddMeasResult(time_res)
            self.__AddMeasid(measid)
            self.__total_time += time

    def GetMeasDistanceProcess(self, measid):  # pylint: disable=C0103
        """
        Get Distance Process for specific to measurement in Kilometer return Int

        :param measid: measurement Id
        :type measid: int
        :return: if exist Distance Value return distance in KM otherwise None
        """
        for meas_res in self.__measresults:
            if meas_res.GetType() == self.MEAS_DIST_PROCESS and \
                    meas_res.GetName() == self.__name and meas_res.GetMeasId() == measid:
                if type(meas_res.GetValue()) == BaseValue:
                    return meas_res.GetValue().GetValue()
        return None

    def GetMeasTimeProcess(self, measid):  # pylint: disable=C0103
        """
        Get Time Process for specific to measurement in Seconds  as Int and  String

        representing duration format HH:MM:SS which
        useful for support reporting

        :param measid: measurement Id
        :type measid: int
        :return: if exist Time process(second) Value and duration format
                 HH:MM:SS e.g. 124, "00:2:04" otherwise return None,None
        """
        for meas_res in self.__measresults:
            if meas_res.GetType() == self.MEAS_TIME_PROCESS and meas_res.GetName() == self.__name and \
                    meas_res.GetMeasId() == measid:
                if type(meas_res.GetValue()) == BaseValue:
                    return meas_res.GetValue().GetValue(), sec_to_hms_string(meas_res.GetValue().GetValue())
        return None, None

    def GetMeasResult(self, measid=None, name=None, result_type=None):  # pylint: disable=C0103,R0912
        """
        Get Measurement Result list with following filter Criteria on result name and measurementId:

          if both argument (measid, name) are passed
              --> return result with specific name and measurement Id
          if only measid is passed
              --> return All results specific to measurement Id
          if only name is passed
              --> return Result with specific name for All measurement Id
          if no argument is passed
              --> Return all the measurement Results under the current test case i.e. No filter

        Don't use GetMeasResult() to Get Distance and Time process for measid under testcase,
        Use `GetMeasTimeProcess`  or `GetMeasDistanceProcess` instead

        :param measid: measurement Id
        :type measid: int
        :param name: Result Name e.g. "EOL_STD_ERROR", "ACC_OBJ_TESTCASE_LANE_ID"
        :type name: String
        :param result_type: Result Name e.g. "EOL_STD_ERROR", "ACC_OBJ_TESTCASE_LANE_ID"
        :type result_type: String
        :return: list of ValResult
        """

        meas_results = []
        for meas_res in self.__measresults:
            type_res = meas_res.GetType()
            not_dist_time = (type_res not in self.MEAS_DIST_PROCESS + self.MEAS_TIME_PROCESS)
            if not_dist_time:

                if measid is not None and name is not None and result_type is not None:
                    if (meas_res.GetMeasId() == measid and meas_res.GetName() == name and
                            meas_res.GetType() == result_type):
                        meas_results.append(meas_res)
                elif measid is not None and name is not None and result_type is None:
                    if meas_res.GetMeasId() == measid and meas_res.GetName() == name:
                        meas_results.append(meas_res)
                elif measid is not None and name is None and result_type is not None:
                    if meas_res.GetMeasId() == measid and meas_res.GetType() == result_type:
                        meas_results.append(meas_res)
                elif measid is not None and name is None and result_type is None:
                    if meas_res.GetMeasId() == measid:
                        meas_results.append(meas_res)
                elif measid is None and name is not None and result_type is not None:
                    if meas_res.GetName() == name and meas_res.GetType() == result_type:
                        meas_results.append(meas_res)
                elif measid is None and name is not None and result_type is None:
                    if meas_res.GetName() == name:
                        meas_results.append(meas_res)
                elif measid is None and name is None and result_type is not None:
                    if meas_res.GetType() == result_type:
                        meas_results.append(meas_res)
                else:
                    meas_results.append(meas_res)
        return meas_results

    def GetDistanceProcess(self):  # pylint: disable=C0103
        """
        Get The total Driven Distance for the test case

        :return: Total Distance in Kilometer
        :rtype: int
        """
        return self.__total_dist

    def GetTimeProcess(self):  # pylint: disable=C0103
        """
        Get The total Time processed for the test case

        :return: Total Time in Second as Integer and Duration as String with format HH:MM:SS
        :rtype: int     str
        """
        return self.__total_time, sec_to_hms_string(self.__total_time)

    def GetMeasurementIds(self):  # pylint: disable=C0103
        """Returns list of measurements Id for which results is saved
        """
        return self.__measid

    def __CheckDBI(self, dbi_val, dbi_gbl, dbi_cat):  # pylint: disable=C0103
        """ Check the Database interface

        :param dbi_val: Validation Database interface
        :param dbi_gbl: Global Database interface
        :param dbi_cat: Catalog Database interface
        """
        # pylint: disable= R0201
        if dbi_val is not None and not issubclass(dbi_val.__class__, db_val.BaseValResDB):
            self._log.error("VAL Database interface undefined")
            return False

        if dbi_gbl is not None and not issubclass(dbi_gbl.__class__, db_gbl.BaseGblDB):
            self._log.error("GBL Database interface undefined")
            return False

        if dbi_cat is not None and not issubclass(dbi_cat.__class__, db_cat.BaseRecCatalogDB):
            self._log.error("CAT Database interface undefined")
            return False

        return True

    def __CheckTestCaseSpecTag(self, tag):  # pylint: disable=C0103
        """
        Check if the specification tag is matching DOORS format

        :param tag: Doors ID
        :type tag: String
        """
        # pylint: disable= R0201
        #                   1        2   3  4   5   6   7  8   9   10  11
        pattern = r"((^[a-z]{2,3}_[a-z]{2,3}|^[a-z]{2,3}))_TC_(\d{3})(_)(\d{3})$"
        match = recomp(pattern, IGNORECASE | DOTALL).search(tag)
        if match:
            return True
        else:
            return False

    def __AddMeasid(self, measid):  # pylint: disable=C0103
        """
        Internal function to mantain list of measid processed by testcase
        :param measid: measurement Id
        :type measid: int
        """
        if measid not in self.__measid:
            self.__measid.append(measid)

    @property
    def test_steps(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns list of Teststeps as list[`TestStep`,...]
        """
        return self.__teststeps

    @property
    def name(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute returns name of the TestCase as string.
        """
        return self.GetName()

    @property
    def description(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns description of the TestCase as string.
        """
        return self.GetDescription()

    @property
    def id(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns Id of the TestCase as string.
        """
        return self.GetSpecTag()

    @property
    def doors_url(self):
        """AlgoTestReport Interface overloaded attribute, returns URL of the testcase in doors as string.
        """
        return str(self.GetDoorsURL())

    @property
    def collection(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns CollectionName of the Testcase as string.
        """
        return self.GetCollectionName()

    @property
    def test_result(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns combined result (assessment) of all Teststeps
        of the Testcase as string.
        """
        return str(self.GetAssessment().ass_state)

    @property
    def summery_plots(self):
        """AlgoTestReport Interface overloaded attribute, returns list of plots for detailed summery report.
        """
        return self.GetSummaryResults()

    @property
    def total_dist(self):
        """AlgoTestReport Interface overloaded attribute, returns total distance in km driven for this test case as
        int.
        """
        return self.GetDistanceProcess()

    @property
    def total_time(self):
        """AlgoTestReport Interface overloaded attribute, returns total time in seconds driven for this test case
        as int.
        """
        return self.GetTimeProcess()[0]

    @property
    def coll_id(self):
        """Property to return collection as int
        """
        return self.__coll_id


class ValResult(object):  # pylint: disable= R0902,R0904
    """ Base class for testresults
    """
    def __init__(self, name=None, res_type=None, meas_id=None, unit=None, tag="",
                 parent=None, doors_url="", exp_res="", desc=""):
        # pylint: disable= R0913
        """
        Inialize Result Class

        :param name: Result Name (Unique Identifier, Signal, Image, ...)
        :type name: str
        :param res_type: Result Type (Distance, KPI, Image Plot, ...)
        :type res_type: str
        :param meas_id: Measurement Identifier
        :type meas_id: int
        :param unit: Unit Name (Meter, ...)
        :type unit: str
        :param tag: Reference Tag (link to doors testspecification)
        :type tag: str
        :param parent: Parent Result (support to link results to a testcase)
        :type parent: int
        """
        self._log = Logger(self.__class__.__name__)
        self.__name = name
        self.__type = res_type
        self.__unit = unit
        self.__value = None
        self.__ref_tag = tag
        self.__parent = parent
        self.__assessment = None
        self.__rd_id = None
        self.__meas_id = meas_id
        self.__coll_id = None
        self.__unit_rec = None
        self.__class_name = None
        self.__id = None
        self.__coll_name = None
        self.__doors_url = doors_url
        self.__exp_res = exp_res
        self.__desc = desc

    def __str__(self):
        """ Basic Result Info as string """
        txt = "Result: "
        txt += self.__name
        if self.__assessment is not None:
            txt += " ASMT: " + str(self.__assessment)
        return txt + "\n"

    def GetName(self):  # pylint: disable=C0103
        """ Get the Name of the testcase """
        return self.__name

    def GetSpecTag(self):  # pylint: disable=C0103
        """
        Get Specification Identifier
        """
        return self.__ref_tag

    def GetDescription(self):  # pylint: disable=C0103
        """
        Get Description text of the result
        """
        return self.__desc

    def GetExpectedResult(self):  # pylint: disable=C0103
        """
        Get Expected Result
        """
        return self.__exp_res

    def GetDoorsURL(self):  # pylint: disable=C0103
        """
        Get Doors URLS
        """
        return self.__doors_url

    def GetCollectionName(self):  # pylint: disable=C0103
        """
        Get Collection
        """
        return self.__coll_name

    def Load(self,  # pylint: disable=C0103,R0912,R0913,R0914,R0915
             dbi_val,
             dbi_gbl,
             testrun_id,
             coll_id=None,
             meas_id=None,
             rd_id=None,
             obs_name=None,
             level=ValSaveLoadLevel.VAL_DB_LEVEL_BASIC,
             cons_key=None):
        """
        Load the result

        :param dbi_val: Validation Database interface
        :type dbi_val: child of BaseValResDB
        :param dbi_gbl: Global Database interface
        :type dbi_gbl: child of BaseGblDB
        :param testrun_id: Testrun Identifier
        :type testrun_id: int
        :param coll_id: collection Identifier
        :type coll_id: int
        :param meas_id: Measurement Identifier
        :type meas_id: int
        :param rd_id: Result Descriptor Identifier
        :type rd_id: int
        :param obs_name: Observer Name
        :type obs_name: str
        :param level: Database load/store level
        :type level: int
        :param cons_key: constraint key
        :type cons_key: Not used currently
        """
        _ = cons_key
        ret = False

        if not issubclass(dbi_val.__class__, db_val.BaseValResDB):
            self._log.error("VAL Database interface undefined")
            return False

        if not issubclass(dbi_gbl.__class__, db_gbl.BaseGblDB):
            self._log.error("GBL Database interface undefined")
            return False

        if rd_id is None:
            self.__rd_id = dbi_val.get_result_descriptor_id(coll_id, self.__name, ev_type_name=self.__type)
        else:
            self.__rd_id = rd_id

        if self.__meas_id is not None:
            meas_id = self.__meas_id

        if level & ValSaveLoadLevel.VAL_DB_LEVEL_1:
            # load the result description and unit information
            rd_rec = dbi_val.get_result_descriptor_with_id(self.__rd_id)
            if COL_NAME_RESDESC_NAME in rd_rec:
                self.__name = rd_rec[COL_NAME_RESDESC_NAME]
                self.__type = rd_rec["TYPE_" + COL_NAME_RESULTTYPE_NAME]
                self.__coll_id = rd_rec[COL_NAME_RESDESC_COLLID]
                self.__parent = rd_rec[COL_NAME_RESDESC_PARENT]
                self.__ref_tag = rd_rec[COL_NAME_RESDESC_REFTAG]
                self.__class_name = rd_rec[COL_NAME_RESULTTYPE_CLASS]
                self.__doors_url = rd_rec[COL_NAME_RESDESC_DOORS_URL]
                self.__exp_res = rd_rec[COL_NAME_RESDESC_EXPECTRES]
                self.__desc = rd_rec[COL_NAME_RESDESC_DESCRIPTION]
                unit_id = rd_rec[COL_NAME_RESDESC_UNIT_ID]
                self.__unit_rec = dbi_gbl.get_unit(uid=unit_id)
                self.__unit = self.__unit_rec[COL_NAME_UNIT_NAME]
                if level < ValSaveLoadLevel.VAL_DB_LEVEL_2:
                    ret = True

        if level & ValSaveLoadLevel.VAL_DB_LEVEL_2:
            res_rec = dbi_val.get_result(testrun_id, self.__rd_id, meas_id)
            if COL_NAME_RES_VALUE in res_rec:
                self.__value = res_rec[COL_NAME_RES_VALUE]
                self.__meas_id = res_rec[COL_NAME_RES_MEASID]
                self.__id = res_rec[COL_NAME_RES_ID]
                ass_id = res_rec[COL_NAME_RES_RESASSID]
                if level < ValSaveLoadLevel.VAL_DB_LEVEL_3:
                    ret = True
            else:
                return False

        if level & ValSaveLoadLevel.VAL_DB_LEVEL_3:
            # load the assessment
            try:
                if ass_id is not None:
                    ass = ValAssessment()
                    ass.load(ass_id, dbi_val, dbi_gbl, obs_name)
                    self.__assessment = ass

                if level < ValSaveLoadLevel.VAL_DB_LEVEL_4:
                    ret = True

            except StandardError:
                pass
        if level & ValSaveLoadLevel.VAL_DB_LEVEL_4:
            if self.__value is not None:
                if str(self.__class_name) == "None":
                    ret = True
                elif self.__class_name == 'BaseValue':
                    self.__value = BaseValue("", BaseUnit(self.__unit, "", None), self.__value)
                    ret = True
                elif self.__class_name == 'ValueVector':
                    if self.__id is not None:
                        values = dbi_val.get_list_of_results(self.__id)
                        min_rg = values[0]
                        max_rg = values[1]
                        val_vec = values[2:]
                        unit = BaseUnit(self.__unit)
                        self.__value = ValueVector(self.__name, unit, val_vec, min_rg, max_rg)
                        ret = True
                elif self.__class_name == 'Histogram':
                    if self.__id is not None:
                        values = dbi_val.get_list_of_results(self.__id)

                        i = 0
                        j = 0
                        hist_x = [0] * int(len(values) / 2)
                        hist_y = [0] * int(len(values) / 2)
                        while i < len(values):
                            hist_x[j] = values[i]
                            hist_y[j] = values[i + 1]
                            j += 1
                            i += 2
                        unit = BaseUnit(self.__unit)
                        self.__value = Histogram(self.__name, unit)
                        self.__value.SetValue(zip(hist_x, hist_y))
                        res_msgs = dbi_val.get_list_of_result_messages(self.__id)
                        hist_cfg = []
                        for i in range(len(res_msgs)):
                            hist_cfg.append(res_msgs[i])
                        if len(hist_cfg):
                            self.__value.SetHistogramConfig(hist_cfg)
                        ret = True
                elif self.__class_name == 'ValidationPlot':
                    if self.__id is not None:
                        values = dbi_val.get_list_of_results(self.__id)
                        width = values[0]
                        heigth = values[1]
                        img_rec = dbi_val.get_result_image(self.__id)
                        if COL_NAME_RESIMG_IMAGE in img_rec:
                            title = img_rec[COL_NAME_RESIMG_TITLE]
                            img_data = img_rec[COL_NAME_RESIMG_IMAGE]
                            val_plt = ValidationPlot(title=title, width=width, height=heigth)
                            val_plt.set_image_data_buffer(img_data)
                            self.__value = val_plt
                            ret = True
                elif self.__class_name == 'BaseMessage':
                    if self.__id is not None:
                        values = dbi_val.get_array_of_result_messages(self.__id)
                        if len(values) == 1:
                            self.__value = BaseMessage(self.__name, values[0])
                        ret = True
        return ret

    def Save(self,  # pylint: disable=C0103,R0912,R0913,R0914,R0915
             dbi_val,
             dbi_gbl,
             testrun_id,
             coll_id,
             meas_id=None,
             obs_name=None,
             parent_id=None,
             level=ValSaveLoadLevel.VAL_DB_LEVEL_BASIC,
             cons_key=None):
        """
        Save the result

        :param parent_id:
        :param dbi_val: Validation Database interface
        :type dbi_val: child of BaseValResDB
        :param dbi_gbl: Global Database interface
        :type dbi_gbl: child of BaseGblDB
        :param testrun_id: Testrun identifier
        :type testrun_id: int
        :param coll_id: CAT Collection ID
        :type coll_id: int
        :param meas_id: Measurement Identifier
        :type meas_id: int
        :param obs_name: Observer Name (registered in GBL)
        :type obs_name: str
        :param level: Save level,

                VAL_DB_LEVEL_STRUCT:
                  Result Descriptor only,
                VAL_DB_LEVEL_BASIC:
                  Result Descriptor and result,
                VAL_DB_LEVEL_INFO:
                  Result Descriptor, Result and Assessment
                VAL_DB_LEVEL_ALL:
                  Result with images and all messages

        :type level: int
        :param cons_key: contraint key -- for future use
        :type cons_key: currently not in used
        """
        _ = cons_key
        res = False
        msg = None

        if not issubclass(dbi_val.__class__, db_val.BaseValResDB):
            self._log.error("VAL Database interface undefined")
            return res

        if not issubclass(dbi_gbl.__class__, db_gbl.BaseGblDB):
            self._log.error("GBL Database interface undefined")
            return res

        if self.__unit is None:
            self._log.error("Unit is not defined for the result")

        unit_id = dbi_gbl.get_unit_id_by_name(self.__unit)
        if unit_id is None:
            self._log.error("Unit is not defined in the GBL Database")
            return res

        if dbi_val.get_testrun_lock(tr_id=testrun_id) == 1:
            self._log.error("Result or Test Step %s Save is failed due to locked testrun " % (self.__name))
            return res

        if self.__meas_id is not None:
            meas_id = self.__meas_id

        if level & ValSaveLoadLevel.VAL_DB_LEVEL_1:
            if dbi_val.get_result_type_id(self.__type) is None:
                if self.__class_name is not None:
                    cls_name = self.__class_name
                else:
                    cls_name = "None"
                res_type = {COL_NAME_RESULTTYPE_NAME: self.__type, COL_NAME_RESULTTYPE_DESC: "",
                            COL_NAME_RESULTTYPE_CLASS: cls_name}
                dbi_val.add_result_type(res_type)

            # use the parent id of the testcase
            if self.__parent is None:
                self.__parent = parent_id
            self.__rd_id = dbi_val.get_result_descriptor_id(coll_id, self.__name, ev_type_name=self.__type,
                                                            parent_id=self.__parent)

            if self.__rd_id is None:

                # generate a new descriptor
                self.__rd_id = dbi_val.add_result_descriptor(self.__type, self.__name, coll_id, unit_id,
                                                             self.__ref_tag, self.__parent,
                                                             self.__doors_url, self.__exp_res,
                                                             self.__desc)

                if level < ValSaveLoadLevel.VAL_DB_LEVEL_2:
                    res = True

        if level & ValSaveLoadLevel.VAL_DB_LEVEL_2:
            ass_id = None
            # if an assessement exists, save it
            if level & ValSaveLoadLevel.VAL_DB_LEVEL_3:
                if self.__assessment is not None:
                    self.__assessment.save(dbi_val, dbi_gbl, obs_name)
                    ass_id = self.__assessment.ass_id

            # check if the result is already in the DB
            res_rec = dbi_val.get_result(testrun_id, self.__rd_id, meas_id)
            if COL_NAME_RES_ID not in res_rec:
                res_rec = {COL_NAME_RES_TESTRUN_ID: testrun_id,
                           COL_NAME_RES_RESDESC_ID: self.__rd_id,
                           COL_NAME_RES_MEASID: meas_id}
                if ass_id is not None:
                    res_rec[COL_NAME_RES_RESASSID] = ass_id
                res = self.__SaveResultValues(dbi_val, res_rec)
            else:
                # update the result only with new assessment results
                if ass_id is not None:
                    res_rec[COL_NAME_RES_RESASSID] = ass_id
                    dbi_val.update_result(res_rec)
                    res = True
                else:
                    msg = "Result %s could not be stored. Its already in the Database" % self.GetName()

        if res is True:
            pass

#            dbi_val.commit()
#            dbi_gbl.commit()
        else:
            if msg is None:
                self._log.error("Result %s could not be stored" % self.GetName())
            else:
                self._log.error(msg)

        return res

    def __SaveResultValues(self, dbi_val, res_rec, update=False):  # pylint: disable=R0912,R0915,C0103
        """ Save the results """
        res = False

        if update:
            dbi_val.delete_result_value({COL_NAME_RESVAL_ID: self.__id})
            dbi_val.delete_result_message({COL_NAME_RESVAL_ID: self.__id})
            dbi_val.delete_result_image({COL_NAME_RESVAL_ID: self.__id})

        if self.__value is None:
            res_rec[COL_NAME_RES_VALUE] = 0.0
            if not update:
                self.__id = dbi_val.add_result(res_rec)
            else:
                dbi_val.update_result(res_rec)
            res = True
        elif isinstance(self.__value, Signal):
            # not supported
            res = False
        elif isinstance(self.__value, ValueVector):
            if len(self.__value) > 400:
                self._log.warning("Length Value Vector %s is too high, please check the design"
                                  % self.__value.GetName())
            val = self.__value.GetValue()
            if val is not None:
                res_rec[COL_NAME_RES_VALUE] = len(val)
                if not update:
                    self.__id = dbi_val.add_result(res_rec)
                else:
                    dbi_val.update_result(res_rec)

                # First store min and max of range
                res_dat = {COL_NAME_RESVAL_ID: self.__id, COL_NAME_RESVAL_SUBID: 0,
                           COL_NAME_RESVAL_VALUE: self.__value.GetRangeMin()}
                dbi_val.add_result_value(res_dat)
                res_dat[COL_NAME_RESVAL_SUBID] = 1
                res_dat[COL_NAME_RESVAL_VALUE] = self.__value.GetRangeMax()
                dbi_val.add_result_value(res_dat)

                # store all values
                for i in range(len(val)):
                    res_dat[COL_NAME_RESVAL_SUBID] = i + 2
                    res_dat[COL_NAME_RESVAL_VALUE] = val[i]
                    dbi_val.add_result_value(res_dat)

            res = True
        elif isinstance(self.__value, ValidationPlot):
            val = self.__value
            img_data = val.get_plot_data_buffer()  # pylint: disable=E1103
            res_rec[COL_NAME_RES_VALUE] = 0
            if not update:
                self.__id = dbi_val.add_result(res_rec)
            else:
                dbi_val.update_result(res_rec)

            res_dat = {COL_NAME_RESVAL_ID: self.__id}

            # store additional data containing the figure sizes
            if val.get_width() is not None:  # pylint: disable=E1103
                res_dat[COL_NAME_RESVAL_SUBID] = 0
                res_dat[COL_NAME_RESVAL_VALUE] = val.get_width()  # pylint: disable=E1103
                dbi_val.add_result_value(res_dat)
            if val.get_height() is not None:  # pylint: disable=E1103
                res_dat[COL_NAME_RESVAL_SUBID] = 1
                res_dat[COL_NAME_RESVAL_VALUE] = val.get_height()  # pylint: disable=E1103
                dbi_val.add_result_value(res_dat)

            # Add the image
            if img_data is not None:
                res_img = {}
                res_img[COL_NAME_RESIMG_ID] = self.__id
                res_img[COL_NAME_RESIMG_IMAGE] = img_data
                title = val.get_title()  # pylint: disable=E1103
                if title is None:
                    # create a new title
                    title = self.__name
                    if self.__meas_id is not None:
                        title += "_%d" % self.__meas_id
                res_img[COL_NAME_RESIMG_TITLE] = title
                res_img[COL_NAME_RESIMG_FORMAT] = 'png'
                dbi_val.add_result_image(res_img)
            res = True
        elif isinstance(self.__value, Histogram):
            val = self.__value.GetValue()

            if val is not None:
                res_rec[COL_NAME_RES_VALUE] = len(val)
                if not update:
                    self.__id = dbi_val.add_result(res_rec)
                else:
                    dbi_val.update_result(res_rec)

                res_dat = {COL_NAME_RESVAL_ID: self.__id}
                i = 0
                for xyz in val:
                    res_dat[COL_NAME_RESVAL_SUBID] = i
                    res_dat[COL_NAME_RESVAL_VALUE] = xyz[0]
                    dbi_val.add_result_value(res_dat)
                    res_dat[COL_NAME_RESVAL_SUBID] = i + 1
                    res_dat[COL_NAME_RESVAL_VALUE] = xyz[1]
                    dbi_val.add_result_value(res_dat)
                    i += 2
                hist_cfg = self.__value.GetHistogramConfig()
                res_msg_dat = {COL_NAME_RESMESS_ID: self.__id}
                if hist_cfg is not None:
                    for i in range(len(hist_cfg)):
                        res_msg_dat[COL_NAME_RESMESS_SUBID] = i
                        res_msg_dat[COL_NAME_RESMESS_MESS] = hist_cfg[i]
                        dbi_val.add_result_message(res_msg_dat)

            res = True

        elif isinstance(self.__value, BaseMessage):
            val = self.__value.GetValue()
            if val is not None and type(val) == str:
                res_rec[COL_NAME_RES_VALUE] = 0
                if not update:
                    self.__id = dbi_val.add_result(res_rec)
                else:
                    dbi_val.update_result(res_rec)

                if len(val) <= BaseMessage.MAX_DB_STR_LENGTH:
                    res_msg_rec = {COL_NAME_RESMESS_ID: self.__id,
                                   COL_NAME_RESMESS_SUBID: 0,
                                   COL_NAME_RESMESS_MESS: val}
                    dbi_val.add_result_message(res_msg_rec)
                    res = True
                else:
                    self._log.error("Result %s could not be stored, Value Exceed the limit of BaseMessage"
                                    % self.__value.GetName())
            else:
                self._log.error("Result %s could not be stored, value not defined" % self.__value.GetName())

        elif isinstance(self.__value, BaseValue):
            val = self.__value.GetValue()
            if val is not None:
                res_rec[COL_NAME_RES_VALUE] = val
                if not update:
                    self.__id = dbi_val.add_result(res_rec)
                else:
                    dbi_val.update_result(res_rec)

                res = True
            else:
                self._log.error("Result %s could not be stored, value not defined" % self.__value.GetName())
        return res

    def Update(self, dbi_val, dbi_gbl, obs_name, level=ValSaveLoadLevel.VAL_DB_LEVEL_BASIC):  # pylint: disable=C0103
        """Update the result value into database which was saved earlier

        :param dbi_val: Validation Database interface
        :type dbi_val: child of BaseValResDB
        :param dbi_gbl: Global Database interface
        :type dbi_gbl: child of BaseGblDB
        :param obs_name: Observer Name
        :type obs_name: String
        :param level: Save level

                        VAL_DB_LEVEL_INFO:
                          Result Descriptor, Result and Assessment
                        VAL_DB_LEVEL_ALL:
                          Result with images, messages and list of values
        """
        if self.__id is not None and self.__rd_id is not None:
            res_rec = dbi_val.get_result(res_id=self.__id)
            if dbi_val.get_testrun_lock(tr_id=res_rec[COL_NAME_RES_TESTRUN_ID]) == 1:
                self._log.error("Update of Result/Teststep %s Failed due to locked testrun " % (self.__name))
                return False

            if level & ValSaveLoadLevel.VAL_DB_LEVEL_2:
                if self.__assessment is not None:
                    if self.__assessment.ass_id is not None:
                        self.__assessment.update(dbi_val, dbi_gbl, obs_name)
                if COL_NAME_RES_ID in res_rec:
                    return self.__SaveResultValues(dbi_val, res_rec, update=True)
        else:
            self._log.error("Cannot update saved Result")

        return False

    def GetType(self):  # pylint: disable=C0103
        """ Get the Result Name
        """
        return self.__type

    def GetUnit(self):  # pylint: disable=C0103
        """ Get the Result Unit
        """
        return self.__unit

    def GetUnitLabel(self):  # pylint: disable=C0103
        """ Get the Unit Label
        """
        if self.__unit_rec is not None:
            return self.__unit_rec[COL_NAME_UNIT_LABEL]
        return ""

    def SetValue(self, value):  # pylint: disable=C0103
        """ Set Result Value Object of the result

        """
        res = False
        if type(value) is BaseValue:
            res = True
            self.__class_name = "BaseValue"
        elif type(value) is ValueVector:
            res = True
            self.__class_name = "ValueVector"
        elif type(value) is Histogram:
            res = True
            self.__class_name = "Histogram"
#        elif isinstance(value, Signal):
#            res = True
        elif type(value) is ValidationPlot:
            res = True
            self.__class_name = "ValidationPlot"
        elif type(value) is BaseMessage:
            res = True
            self.__class_name = "BaseMessage"
        elif type(value) is str:
            res = True
            self.__class_name = "BaseMessage"
            value = BaseMessage("", value)
        else:
            value = BaseValue("", BaseUnit(self.__unit, "", None), value)
            res = True
            self.__class_name = "BaseValue"

        if res is True:
            self.__value = value
        else:
            self._log.error("result type is not supported")

        return res

    def GetValue(self):  # pylint: disable=C0103
        """ return the value object of the result
        """
        return self.__value

    def GetMeasId(self):  # pylint: disable=C0103
        """ Get the Measid of the result """
        return self.__meas_id

    def AddAssessment(self, assessment):  # pylint: disable=C0103
        """ Add Assessment Instance to the result

        :param assessment: Assessment instance
        :type assessment: ValAssessment
        :return: True if passed, False on Error
        """
        if not issubclass(assessment.__class__, ValAssessment):
            self._log.error("Not a Assessment Class Instance")
            return False

        self.__assessment = assessment
        return True

    def GetAssessment(self):  # pylint: disable=C0103
        """ Return the Assessment

        :return: Assessment instance
        """
        return self.__assessment

    def GetResultId(self):  # pylint: disable=C0103
        """ Get the Result ID

        :return: Return the Result ID of the Database or None
        """
        return self.__id

    def GetResultDescriptorId(self):  # pylint: disable=C0103
        """ Get the Result Descriptor ID

        :return: Return the ResultDescriptor ID of the Database or None
        """
        return self.__rd_id

    @property
    def id(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns id string
        """
        return self.GetSpecTag()

    @property
    def doors_url(self):
        """AlgoTestReport Interface overloaded attribute, returns URL of this test step in doors
        """
        return str(self.GetDoorsURL())

    @property
    def name(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns name of test step
        """
        return self.GetName()

    @property
    def test_result(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns test_result as string.
        """
        if self.GetAssessment() is None:
            return ""
        else:
            return str(self.GetAssessment().ass_state)

    @property
    def exp_result(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns expected result as string.
        """
        return self.GetExpectedResult()

    @property
    def meas_result(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns measured result as string.
        """
        return self.GetValue()

    @property
    def date(self):
        """AlgoTestReport Interface overloaded attribute, returns date when assessment was changes last time as string.
        """
        if self.GetAssessment() is None:
            return ""
        else:
            return str(self.GetAssessment().date)

    @property
    def user_account(self):
        """AlgoTestReport Interface overloaded attribute, returns user account of the last assessment change as string.
        """
        if self.GetAssessment() is None:
            return ""
        else:
            return str(self.GetAssessment().user_account)

    @property
    def issue(self):
        """AlgoTestReport Interface overloaded attribute, returns issue entered for this assessment as string.
        """
        if self.GetAssessment() is None:
            return ""
        else:
            return str(self.GetAssessment().issue)


class ValTestStep(ValResult):  # pylint: disable=R0904
    """Classs to ValTestStep

    assessment states ('Passed', 'Failed' etc.) defined in `ValAssessmentStates`
    """
    def __init__(self, name=None, res_type=None,
                 unit=None, tag="", parent=None, doors_url="", exp_res="", desc=""):
        # pylint: disable= R0913

        ValResult.__init__(self, name=name, res_type=res_type, unit=unit, tag=tag, parent=parent,
                           doors_url=doors_url, exp_res=exp_res, desc=desc)

    def Load(self,  # pylint: disable=R0913
             dbi_val,
             dbi_gbl,
             testrun_id,
             coll_id=None,
             rd_id=None,
             obs_name=None,
             level=ValSaveLoadLevel.VAL_DB_LEVEL_BASIC,
             cons_key=None):
        """ Load the ValTestSTep

        :param dbi_val: Validation Database interface
        :type dbi_val: child of BaseValResDB
        :param dbi_gbl: Global Database interface
        :type dbi_gbl: child of BaseGblDB
        :param testrun_id: Testrun Identifier
        :type testrun_id: int
        :param coll_id: collection Identifier
        :type coll_id: int
        :param rd_id: Result Descriptor Identifier
        :type rd_id: int
        :param obs_name: Observer Name
        :type obs_name: str
        :param level: Database load / store level
        :type level: int
        :param cons_key: constraint key
        :type cons_key:
        """

        return ValResult.Load(self, dbi_val, dbi_gbl, testrun_id,
                              coll_id=coll_id, rd_id=rd_id, obs_name=obs_name,
                              level=level,
                              cons_key=cons_key)

    def Save(self, dbi_val, dbi_gbl, testrun_id, coll_id, obs_name=None, parent_id=None,  # pylint: disable=R0913
             level=ValSaveLoadLevel.VAL_DB_LEVEL_BASIC, cons_key=None):
        """ Save the TestStep

        :param dbi_val: Validation Database interface
        :type dbi_val: child of BaseValResDB
        :param dbi_gbl: Global Database interface
        :type dbi_gbl: child of BaseGblDB
        :param testrun_id: Testrun identifier
        :type testrun_id: int
        :param coll_id: CAT Collection ID
        :type coll_id: int
        :param obs_name: Observer Name (registered in GBL)
        :type obs_name: str
        :param level: Save level,

                        VAL_DB_LEVEL_STRUCT:
                          Result Descriptor only,
                        VAL_DB_LEVEL_BASIC:
                          Result Descriptor and result,
                        VAL_DB_LEVEL_INFO:
                          Result Descriptor, Result and Assessment
                        VAL_DB_LEVEL_ALL:
                          Result with images and all messages

        :type level: int
        :param cons_key: constraint key -- for future use
        :type cons_key: currently not in use
        """

        if self.GetSpecTag() == "":
            raise StandardError("Door ID e.g. EM_TC_001_001 is mandatory")

        if self.GetExpectedResult() == "":
            raise StandardError("Expected result data is mandatory e.g. angle> 30")

        if self.__CheckTestStepSpecTag(self.GetSpecTag()) is False:
            raise StandardError("Door ID {} is Not matching Standard format  e.g. ACC_TC_001_001-01"
                                .format(self.GetSpecTag()))
        ValResult.Save(self, dbi_val, dbi_gbl, testrun_id, coll_id, obs_name=obs_name,
                       parent_id=parent_id, level=level,
                       cons_key=cons_key)

    @staticmethod
    def __CheckTestStepSpecTag(tag):  # pylint: disable=C0103
        """
        Check if the specification tag is matching DOORS format

        :param tag: Doors ID
        :type tag: Str
        """
        #               1        2   3  4   5   6   7  8   9   10  11 12  13   14
        pattern = r"((^[a-z]{2,3}_[a-z]{2,3}|^[a-z]{2,3}))_TC_(\d{3})(_)(\d{3})(-)(\d{2})$"

        match = recomp(pattern, IGNORECASE | DOTALL).search(tag)
        if match is not None:
            return True
        else:
            return False

    # This Function is supressed for ValTestStep from its parent because it doenst make sense for TestSteps
    def GetMeasId(self):  # pylint: disable=C0103
        """
        Suppressing the Parent class method which are not valid
        """
        raise StandardError("GetMeasId is not valid Method for ValTestStep Class")


"""
CHANGE LOG:
-----------
$Log: results.py  $
Revision 1.11 2016/04/12 15:07:52CEST Hospes, Gerd-Joachim (uidv8815) 
extend error msg
Revision 1.10 2016/02/05 18:25:07CET Hospes, Gerd-Joachim (uidv8815)
rel 2.3.18
Revision 1.9 2016/02/05 11:03:37CET Hospes, Gerd-Joachim (uidv8815)
pep8/pylint fixes
Revision 1.8 2016/02/04 16:33:45CET Ahmed, Zaheer (uidu7634)
documentation improvement. plugin folder is optional in results.py for loading events
Revision 1.7 2015/10/05 13:37:18CEST Ahmed, Zaheer (uidu7634)
pep8 fixes
--- Added comments ---  uidu7634 [Oct 5, 2015 1:37:19 PM CEST]
Change Package : 376758:1 http://mks-psad:7002/im/viewissue?selection=376758
Revision 1.6 2015/10/05 12:51:19CEST Ahmed, Zaheer (uidu7634)
Check if the tesrun is not locked before saving/updating ValTestCase, ValResult
--- Added comments ---  uidu7634 [Oct 5, 2015 12:51:19 PM CEST]
Change Package : 376758:1 http://mks-psad:7002/im/viewissue?selection=376758
Revision 1.5 2015/09/10 10:05:58CEST Ahmed, Zaheer (uidu7634)
load result descriptor with parent_id for ensure precise loading
--- Added comments ---  uidu7634 [Sep 10, 2015 10:05:59 AM CEST]
Change Package : 375792:1 http://mks-psad:7002/im/viewissue?selection=375792
Revision 1.4 2015/09/09 15:44:57CEST Ahmed, Zaheer (uidu7634)
avoid loading testcase and teststep which were not executed in the run
--- Added comments ---  uidu7634 [Sep 9, 2015 3:44:58 PM CEST]
Change Package : 369148:1 http://mks-psad:7002/im/viewissue?selection=369148
Revision 1.3 2015/05/19 12:58:13CEST Ahmed, Zaheer (uidu7634)
added property to get collection Id in ValTestCase
--- Added comments ---  uidu7634 [May 19, 2015 12:58:14 PM CEST]
Change Package : 338368:1 http://mks-psad:7002/im/viewissue?selection=338368
Revision 1.2 2015/05/18 14:43:26CEST Ahmed, Zaheer (uidu7634)
remove other commits
one commit at the end of testcase Save method is sufficient
--- Added comments ---  uidu7634 [May 18, 2015 2:43:27 PM CEST]
Change Package : 338368:1 http://mks-psad:7002/im/viewissue?selection=338368
Revision 1.1 2015/04/23 19:05:38CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/val/project.pj
Revision 1.59 2015/03/09 08:18:59CET Mertens, Sven (uidv7805)
more docu update
--- Added comments ---  uidv7805 [Mar 9, 2015 8:19:00 AM CET]
Change Package : 314290:1 http://mks-psad:7002/im/viewissue?selection=314290
Revision 1.58 2015/03/06 15:20:51CET Mertens, Sven (uidv7805)
docu update
--- Added comments ---  uidv7805 [Mar 6, 2015 3:20:53 PM CET]
Change Package : 314290:1 http://mks-psad:7002/im/viewissue?selection=314290
$Log: results.pyRevision 1.57 2015/03/06 15:14:04CET Mertens, Sven (uidv7805)
$Log: results.pychanging logger
$Log: results.py--- Added comments ---  uidv7805 [Mar 6, 2015 3:14:06 PM CET]
$Log: results.pyChange Package : 314290:1 http://mks-psad:7002/im/viewissue?selection=314290
Revision 1.56 2015/02/06 16:45:35CET Ellero, Stefano (uidw8660)
No deprecated functions/methods of package obj must be used inside all STK and its module tests.
--- Added comments ---  uidw8660 [Feb 6, 2015 4:45:36 PM CET]
Change Package : 301801:1 http://mks-psad:7002/im/viewissue?selection=301801
Revision 1.55 2015/01/23 14:25:38CET Mertens, Sven (uidv7805)
removing even another 2 calls
--- Added comments ---  uidv7805 [Jan 23, 2015 2:25:39 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.54 2015/01/20 13:38:31CET Mertens, Sven (uidv7805)
removing some more deprecated calls
Revision 1.53 2015/01/19 16:56:36CET Mertens, Sven (uidv7805)
removing deprecated calls
--- Added comments ---  uidv7805 [Jan 19, 2015 4:56:37 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.52 2015/01/19 14:42:04CET Mertens, Sven (uidv7805)
even more deprecation adaptation
Revision 1.51 2014/12/18 01:12:44CET Hospes, Gerd-Joachim (uidv8815)
remove deprecated methods based on db.val
--- Added comments ---  uidv8815 [Dec 18, 2014 1:12:44 AM CET]
Change Package : 281282:1 http://mks-psad:7002/im/viewissue?selection=281282
Revision 1.50 2014/10/22 11:47:34CEST Ahmed, Zaheer (uidu7634)
Removed deprecated method usage
--- Added comments ---  uidu7634 [Oct 22, 2014 11:47:35 AM CEST]
Change Package : 267593:5 http://mks-psad:7002/im/viewissue?selection=267593
Revision 1.49 2014/10/21 21:01:17CEST Ahmed, Zaheer (uidu7634)
Add commit statement save method of testcase to reduce risk of tables
loading of events for individual measurment is possible for better memeory management
--- Added comments ---  uidu7634 [Oct 21, 2014 9:01:17 PM CEST]
Change Package : 273583:1 http://mks-psad:7002/im/viewissue?selection=273583
Revision 1.48 2014/10/09 20:44:09CEST Hecker, Robert (heckerr)
Example usage and change for deprecated porperty.
--- Added comments ---  heckerr [Oct 9, 2014 8:44:09 PM CEST]
Change Package : 270819:1 http://mks-psad:7002/im/viewissue?selection=270819
Revision 1.47 2014/09/26 12:10:36CEST Ahmed, Zaheer (uidu7634)
updated documentation
--- Added comments ---  uidu7634 [Sep 26, 2014 12:10:36 PM CEST]
Change Package : 260444:3 http://mks-psad:7002/im/viewissue?selection=260444
Revision 1.46 2014/09/25 13:29:00CEST Hospes, Gerd-Joachim (uidv8815)
adapt stk.img files to style guide, new names used in all modules and tests
except stk.img tests
--- Added comments ---  uidv8815 [Sep 25, 2014 1:29:01 PM CEST]
Change Package : 264203:1 http://mks-psad:7002/im/viewissue?selection=264203
Revision 1.45 2014/09/04 11:04:10CEST Ahmed, Zaheer (uidu7634)
update feature introduced for ValResult and TestSTep
--- Added comments ---  uidu7634 [Sep 4, 2014 11:04:11 AM CEST]
Change Package : 253432:1 http://mks-psad:7002/im/viewissue?selection=253432
Revision 1.44 2014/09/01 17:45:06CEST Ahmed, Zaheer (uidu7634)
Bug fix on loading summary detail result
--- Added comments ---  uidu7634 [Sep 1, 2014 5:45:07 PM CEST]
Change Package : 260437:1 http://mks-psad:7002/im/viewissue?selection=260437
Revision 1.43 2014/07/28 10:34:12CEST Ahmed, Zaheer (uidu7634)
Bug fixed. Dont set plot config with empty list
--- Added comments ---  uidu7634 [Jul 28, 2014 10:34:12 AM CEST]
Change Package : 251180:1 http://mks-psad:7002/im/viewissue?selection=251180
Revision 1.42 2014/06/08 15:54:31CEST Ahmed, Zaheer (uidu7634)
improved documentation
Add result_type arugment in testcase.GetMeasResults()
--- Added comments ---  uidu7634 [Jun 8, 2014 3:54:32 PM CEST]
Change Package : 235089:1 http://mks-psad:7002/im/viewissue?selection=235089
Revision 1.41 2014/05/21 09:53:11CEST Ahmed, Zaheer (uidu7634)
Inherting BaseMessage Class from from str instead of BaseValue to get more
features from python str
--- Added comments ---  uidu7634 [May 21, 2014 9:53:12 AM CEST]
Change Package : 235091:2 http://mks-psad:7002/im/viewissue?selection=235091
Revision 1.40 2014/05/20 10:26:19CEST Ahmed, Zaheer (uidu7634)
ValResult.SetValue() can accpet string datatype as well
Revision 1.39 2014/05/19 11:13:23CEST Ahmed, Zaheer (uidu7634)
Added support for load and Store of BaseMessage in ValResult Class
--- Added comments ---  uidu7634 [May 19, 2014 11:13:23 AM CEST]
Change Package : 235091:1 http://mks-psad:7002/im/viewissue?selection=235091
Revision 1.38 2014/05/05 11:31:32CEST Ahmed, Zaheer (uidu7634)
improved documenation
--- Added comments ---  uidu7634 [May 5, 2014 11:31:33 AM CEST]
Change Package : 233151:1 http://mks-psad:7002/im/viewissue?selection=233151
Revision 1.37 2014/04/25 10:54:22CEST Hospes, Gerd-Joachim (uidv8815)
doors_url added to testcase and teststep
--- Added comments ---  uidv8815 [Apr 25, 2014 10:54:23 AM CEST]
Change Package : 227491:1 http://mks-psad:7002/im/viewissue?selection=227491
Revision 1.36 2014/03/27 13:48:35CET Ahmed, Zaheer (uidu7634)
Introduced GetTestStep Filter Criteria
Added Default Assessment State not Assessed for TestStep
--- Added comments ---  uidu7634 [Mar 27, 2014 1:48:35 PM CET]
Change Package : 224336:1 http://mks-psad:7002/im/viewissue?selection=224336
Revision 1.35 2014/03/12 14:10:14CET Hospes, Gerd-Joachim (uidv8815)
add ValTestCase.summery_plots property for pdf report
--- Added comments ---  uidv8815 [Mar 12, 2014 2:10:15 PM CET]
Change Package : 221503:1 http://mks-psad:7002/im/viewissue?selection=221503
Revision 1.34 2014/03/07 11:31:20CET Ahmed, Zaheer (uidu7634)
New feature of summary detail introduced to put plot or histogram under
testcase table in report
improved doucmentation removed unused import
pep8 and pylint fix
--- Added comments ---  uidu7634 [Mar 7, 2014 11:31:20 AM CET]
Change Package : 221506:1 http://mks-psad:7002/im/viewissue?selection=221506
Revision 1.33 2014/02/21 15:25:54CET Ahmed, Zaheer (uidu7634)
added attribute to hold measurement Ids for the testcase
Added GetMeasurementIds() to get list of measurementid undertest
for which driven distance/time was added
--- Added comments ---  uidu7634 [Feb 21, 2014 3:25:55 PM CET]
Change Package : 220098:3 http://mks-psad:7002/im/viewissue?selection=220098
Revision 1.32 2014/02/20 15:12:26CET Hospes, Gerd-Joachim (uidv8815)
fix method name to user_account for report
--- Added comments ---  uidv8815 [Feb 20, 2014 3:12:27 PM CET]
Change Package : 220000:1 http://mks-psad:7002/im/viewissue?selection=220000
Revision 1.31 2014/02/20 12:57:01CET Hospes, Gerd-Joachim (uidv8815)
print user accunt instead of db internal userid
--- Added comments ---  uidv8815 [Feb 20, 2014 12:57:02 PM CET]
Change Package : 220000:1 http://mks-psad:7002/im/viewissue?selection=220000
Revision 1.30 2014/02/19 15:00:47CET Hospes, Gerd-Joachim (uidv8815)
add properties for report
--- Added comments ---  uidv8815 [Feb 19, 2014 3:00:48 PM CET]
Change Package : 220000:1 http://mks-psad:7002/im/viewissue?selection=220000
Revision 1.29 2014/02/18 16:26:43CET Ahmed, Zaheer (uidu7634)
Initialize the missing userid and date for TestCase Assessment which taken
from last modified TestStep
--- Added comments ---  uidu7634 [Feb 18, 2014 4:26:43 PM CET]
Change Package : 220023:1 http://mks-psad:7002/im/viewissue?selection=220023
Revision 1.28 2014/02/14 16:14:55CET Ahmed, Zaheer (uidu7634)
ValTestCase.GetResults() bug fixed, added name filter criteria
added new feature ValResult.Save() to load and save Legend and x-ticks
y-ticks label for Histogram
--- Added comments ---  uidu7634 [Feb 14, 2014 4:14:55 PM CET]
Change Package : 214642:1 http://mks-psad:7002/im/viewissue?selection=214642
Revision 1.27 2014/02/13 17:43:07CET Hospes, Gerd-Joachim (uidv8815)
add total_time and total_distance properties for report
--- Added comments ---  uidv8815 [Feb 13, 2014 5:43:07 PM CET]
Change Package : 218178:1 http://mks-psad:7002/im/viewissue?selection=218178
Revision 1.26 2014/02/12 18:34:55CET Hospes, Gerd-Joachim (uidv8815)
update table styles, use stk defines for assessment states, add table captions
--- Added comments ---  uidv8815 [Feb 12, 2014 6:34:55 PM CET]
Change Package : 218178:1 http://mks-psad:7002/im/viewissue?selection=218178
Revision 1.25 2014/01/27 11:37:00CET Ahmed, Zaheer (uidu7634)
Added Default Assessment Not Assessed for TestCase Result
--- Added comments ---  uidu7634 [Jan 27, 2014 11:37:01 AM CET]
Change Package : 214643:1 http://mks-psad:7002/im/viewissue?selection=214643
Revision 1.24 2014/01/24 15:05:18CET Ahmed, Zaheer (uidu7634)
TestStep Supports all dataype include Histogram, Validation Plot, BaseValue,
ValueVector
--- Added comments ---  uidu7634 [Jan 24, 2014 3:05:19 PM CET]
Change Package : 214643:1 http://mks-psad:7002/im/viewissue?selection=214643
Revision 1.23 2013/12/15 20:27:35CET Hecker, Robert (heckerr)
Added AlgoTestReport Interface.
--- Added comments ---  heckerr [Dec 15, 2013 8:27:36 PM CET]
Change Package : 210873:1 http://mks-psad:7002/im/viewissue?selection=210873
Revision 1.22 2013/12/11 16:31:11CET Bratoi-EXT, Bogdan-Horia (uidu8192)
- adding a function
--- Added comments ---  uidu8192 [Dec 11, 2013 4:31:12 PM CET]
Change Package : 193409:1 http://mks-psad:7002/im/viewissue?selection=193409
Revision 1.21 2013/12/09 18:16:07CET Ahmed-EXT, Zaheer (uidu7634)
pep8 fix
--- Added comments ---  uidu7634 [Dec 9, 2013 6:16:07 PM CET]
Change Package : 210017:3 http://mks-psad:7002/im/viewissue?selection=210017
Revision 1.20 2013/12/09 18:07:13CET Ahmed-EXT, Zaheer (uidu7634)
Added GetAssessment() for ValTestcase and automatic evaluation of Assessment
Rollbacked Testcase result
--- Added comments ---  uidu7634 [Dec 9, 2013 6:07:14 PM CET]
Change Package : 210017:3 http://mks-psad:7002/im/viewissue?selection=210017
Revision 1.19 2013/11/28 12:29:40CET Ahmed-EXT, Zaheer (uidu7634)
Bug fix for oracle Exceeding Distand Time process result descriptor
modification in testcase structure to make Distance and Time process not the part of
standard  Measurement Result
--- Added comments ---  uidu7634 [Nov 28, 2013 12:29:40 PM CET]
Change Package : 203293:1 http://mks-psad:7002/im/viewissue?selection=203293
Revision 1.18 2013/11/25 09:39:57CET Ahmed-EXT, Zaheer (uidu7634)
Fixed bug for Level3 Load and Distance evaluation from EgoMotion object
--- Added comments ---  uidu7634 [Nov 25, 2013 9:39:58 AM CET]
Change Package : 203293:1 http://mks-psad:7002/im/viewissue?selection=203293
Revision 1.17 2013/11/18 15:55:40CET Ahmed-EXT, Zaheer (uidu7634)
Buf fixed for LoadTestStep under Testcase Load
--- Added comments ---  uidu7634 [Nov 18, 2013 3:55:41 PM CET]
Change Package : 203293:1 http://mks-psad:7002/im/viewissue?selection=203293
Revision 1.16 2013/11/11 15:16:47CET Ahmed-EXT, Zaheer (uidu7634)
Fix pylint and pep8
testresult is deprecrated and replace by ValTestStep
Improved Documentation format
--- Added comments ---  uidu7634 [Nov 11, 2013 3:16:47 PM CET]
Change Package : 203293:1 http://mks-psad:7002/im/viewissue?selection=203293
Revision 1.15 2013/11/11 08:30:14CET Ahmed-EXT, Zaheer (uidu7634)
Added GetMeasResult()
Deprecated  GetResult() --> use new function GetMeasResult() or GetTestSteps()
Remove total time and distance procoess saving
Fixed bug in ValResult.Load() --> Level4 with class_name "None" should return
True without anything
--- Added comments ---  uidu7634 [Nov 11, 2013 8:30:15 AM CET]
Change Package : 203293:1 http://mks-psad:7002/im/viewissue?selection=203293
Revision 1.14 2013/11/06 16:49:03CET Ahmed-EXT, Zaheer (uidu7634)
Added Functionality of Time and Distance process on testcase and meas level
--- Added comments ---  uidu7634 [Nov 6, 2013 4:49:03 PM CET]
Change Package : 203293:1 http://mks-psad:7002/im/viewissue?selection=203293
Revision 1.13 2013/11/05 15:13:55CET Ahmed-EXT, Zaheer (uidu7634)
Fixed Regular Expression check for ValTestStep and ValTestCase
Improved Documentation
Revision 1.12 2013/11/04 10:27:42CET Ahmed-EXT, Zaheer (uidu7634)
Added DOORS ID format standard check in ValTestStep and ValTestCase class
Revision 1.11 2013/10/31 17:46:07CET Ahmed-EXT, Zaheer (uidu7634)
Added ValTestStep
Added functionality of Door URL expected result and Description support in
ValTestcase and ValResult classes
--- Added comments ---  uidu7634 [Oct 31, 2013 5:46:07 PM CET]
Change Package : 203293:1 http://mks-psad:7002/im/viewissue?selection=203293
Revision 1.10 2013/10/30 19:39:23CET Hecker, Robert (heckerr)
Removed indirect logging usage.
--- Added comments ---  heckerr [Oct 30, 2013 7:39:23 PM CET]
Change Package : 204154:1 http://mks-psad:7002/im/viewissue?selection=204154
Revision 1.9 2013/10/25 16:26:25CEST Hospes, Gerd-Joachim (uidv8815)
remove 'import stk' and replace missing dependencies
--- Added comments ---  uidv8815 [Oct 25, 2013 4:26:25 PM CEST]
Change Package : 203191:1 http://mks-psad:7002/im/viewissue?selection=203191
Revision 1.8 2013/09/10 10:06:36CEST Ahmed-EXT, Zaheer (uidu7634)
GetEvents function modified to support filter eventlist for measid
SetValue() method changed fix ambigous Resultvalues instance changed
isInstance() --> type()
--- Added comments ---  uidu7634 [Sep 10, 2013 10:06:36 AM CEST]
Change Package : 196580:1 http://mks-psad:7002/im/viewissue?selection=196580
Revision 1.7 2013/08/21 13:24:39CEST Ahmed-EXT, Zaheer (uidu7634)
bug fixed for GetAssessment method return statement missing
pep8 and pylint fix
--- Added comments ---  uidu7634 [Aug 21, 2013 1:24:39 PM CEST]
Change Package : 192688:1 http://mks-psad:7002/im/viewissue?selection=192688
Revision 1.6 2013/07/29 13:03:18CEST Raedler, Guenther (uidt9430)
- check sub structure type to avoid warnings
--- Added comments ---  uidt9430 [Jul 29, 2013 1:03:18 PM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.5 2013/07/10 09:32:17CEST Raedler, Guenther (uidt9430)
- added basic support of testcase events
- added methods AddEvent(), GetEvents(), LoadEvents()
- moved ValSaveLoadLevel() into result_types.py
Note: VAL database update is required (new column rdid in VAL_Events table)
--- Added comments ---  uidt9430 [Jul 10, 2013 9:32:18 AM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.4 2013/06/05 16:28:47CEST Raedler, Guenther (uidt9430)
- added support of loading and storing result_types BaseValue, ValueVector,
ValidationPlot, Histogram
- improved error handling
--- Added comments ---  uidt9430 [Jun 5, 2013 4:28:47 PM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.3 2013/05/29 09:10:33CEST Raedler, Guenther (uidt9430)
- bug fix of GetValue()
- minor preparations
--- Added comments ---  uidt9430 [May 29, 2013 9:10:34 AM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.2 2013/04/22 16:31:03CEST Raedler, Guenther (uidt9430)
- changed docu tags
- load testcase with given rd_id
--- Added comments ---  uidt9430 [Apr 22, 2013 4:31:04 PM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.1 2013/04/22 13:01:01CEST Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/val/project.pj
"""
