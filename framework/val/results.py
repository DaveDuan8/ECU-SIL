"""
stk/val/results.py
------------------

Subpackage for Handling Basic Validation Results.

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.1 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/25 21:34:08CET $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from re import compile as recomp, IGNORECASE, DOTALL

# - import STK modules ------------------------------------------------------------------------------------------------

from framework.val.asmt import ValAssessment, ValAssessmentStates, ValAssessmentWorkFlows
from framework.util.gbl_defs import GblUnits
from framework.val.result_types import BaseUnit, BaseValue, BaseMessage
from framework.img import ValidationPlot
from framework.val.events import ValEventList
from framework.val.ego import EgoMotion
from framework.util.helper import sec_to_hms_string
from framework.util.logger import Logger


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
        for res in self.get_results(None):
            txt += str(res)
        return txt

    def get_name(self):  # pylint: disable=C0103
        """ Get the Name of the testcase e.g. "Dropin Rate", "EOL initialzation"

        :return: name of the test case as String e.g. "ALN EOL State"
        """

        return self.__name

    def get_spe_tag(self):  # pylint: disable=C0103
        """
        Get Doors ID of the testcase also known as Test Case identifier e.g. "ACC_TC_001_001"

        :return: Specification tag as String
        """
        return self.__spec_tag

    def get_collection_name(self):  # pylint: disable=C0103
        """
        Get Collectionname associated with Testcase e.g. "ARS400_acc_endurance"

        :return: Collection as String
        """
        return self.__coll_name

    def get_doors_url(self):  # pylint: disable=C0103
        """
        Get Doors URL
        e.g. "doors://rbgs854a:40000/?version=2&prodID=0&urn=urn:telelogic::1-503e822e5ec3651e-M-0001cbf1"

        :return: DOORS URL as String
        """
        return self.__doors_url

    def get_description(self):  # pylint: disable=C0103
        """
        Get Testcase Description text

        :return: Test case Description as String
        """
        return self.__desc

    def get_assessment(self):  # pylint: disable=C0103
        """
        Get Assessment of the testcase which evaluated based on the Assessment of TestSteps

        The testcase Assessment is not Stored or Loaded from Database
        """
        if len(self.__teststeps) > 0:
            self.__asses = self.__evaluate_assessment()
        else:
            self.__asses = ValAssessment(user_id=None,
                                         wf_state=ValAssessmentWorkFlows.ASS_WF_AUTO,
                                         ass_state=ValAssessmentStates.NOT_ASSESSED,
                                         ass_comment="Couldnt Evaluated Assessment because"
                                         "teststep are not loaded or available",
                                         issue="Issues to be assigned in invidual Teststeps if needed")
        return self.__asses

    def __evaluate_assessment(self):  # pylint: disable=C0103,R0912
        """
        Automatic Assessment evaluate function for TestCase
        """
        ts_ass_states = []
        comment = ""
        asses_date = None
        userid = None
        for teststep in self.__teststeps:
            assess = teststep.get_assessment()
            if assess is None:
                ts_ass_states.append(ValAssessmentStates.NOT_ASSESSED)
                comment += "teststep: %s has no Assessment available\n" % teststep.get_name()
            else:
                if assess.ass_state == ValAssessmentStates.FAILED:
                    comment += "teststep: %s is Failed\n" % teststep.get_name()
                elif assess.ass_state == ValAssessmentStates.NOT_ASSESSED:
                    comment += "teststep: %s is Not Assessed\n" % teststep.get_name()
                elif assess.ass_state == ValAssessmentStates.INVESTIGATE:
                    comment += "teststep: %s has pending investigation\n" % teststep.get_name()
                elif assess.ass_state == ValAssessmentStates.PASSED:
                    comment += "teststep: %s is Passed\n" % teststep.get_name()
                else:
                    comment += "teststep: %s Assessment is Unkown \n" % teststep.get_name()
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
            #asses_state = ValAssessmentStates.NOT_ASSESSED
            asses_state = ValAssessmentStates.PASSED
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

    def add_meas_result(self, result):  # pylint: disable=C0103
        """
        Add a new result for a measurement

        The result is normally available on development level and takes measurement specific results

        Note: Read the Documentation of `ValResult` Class

        :param result: Result of type `ValResult` containing value which
                       could be `ValidationPlot`, Histogram, image, ValueVector, BaseValue
        :type result: ValResult
        """
        if issubclass(result.__class__, ValResult):
            if result.get_meas_id() is not None:
                self.__measresults.append(result)
            else:
                raise StandardError("Measid is mandatory for Measurement Results")

    def get_results(self, measid=None, name=None):  # pylint: disable=C0103
        """
        Get the results of the Testcase fulfilling input argument criteria

        if both are passed then it will be AND relation

        :param measid: Measurement ID if measid provide then only list of results(MeasResult) specific to measid return
                       otherwise List of TestCaseResult will be return
        :type measid: int, None
        :param name: Result Name
        :type name: string, None
        """
        return self.__get_generic_results(measid, name, self.__testresults)

    def get_summary_results(self, name=None):  # pylint: disable=C0103
        """
        Get the summary result of the Testcase fulfilling input argument criteria

        if name is None then the list of all summary detail results will be returned

        :param name: Result Name
        :type name: string
        """
        return self.__get_generic_results(None, name, self.__testsummarydetails)

    @staticmethod
    def __get_generic_results(measid, name, result_list):  # pylint: disable=C0103
        """
        Generic function to Get the result(s) of the Testcase fulfilling input argument criteria

        if both (measid and name) are passed then it will be AND relation

        :param measid: Measurement ID if measid provide then only list of results(MeasResult) specific to measid return
                       otherwise List of TestCaseResult will be return
        :type measid: int, None
        :param name: Result Name
        :type name: string, None
        :param result_list: list of result entries
        :type  result_list: list
        """
        # pylint: disable= R0201
        res_list = []
        if measid is not None and name is None:
            for tc_res in result_list:
                if tc_res.get_meas_id() == measid:
                    res_list.append(tc_res)
            return res_list
        elif measid is None and name is not None:
            for tc_res in result_list:
                if tc_res.get_name() == name:
                    res_list.append(tc_res)
            return res_list
        elif measid is not None and name is not None:
            for tc_res in result_list:
                if tc_res.get_name() == name and tc_res.get_meas_id() == measid:
                    res_list.append(tc_res)
            return res_list
        else:
            return result_list

    def add_test_step(self, test_step):  # pylint: disable=C0103
        """
        Add TestSTep to Test case

        :param test_step: object of teststep class
        :type test_step: ValTestStep
        """
        if isinstance(test_step, ValTestStep):
            if test_step.get_assessment() is None:
                comment = "default automatically assigned - Not assessed."
                assessment = ValAssessment(user_id=None,
                                           wf_state=ValAssessmentWorkFlows.ASS_WF_AUTO,
                                           ass_state=ValAssessmentStates.NOT_ASSESSED,
                                           ass_comment=comment)
                test_step.add_assessment(assessment)
            self.__teststeps.append(test_step)
        else:
            raise StandardError("Instance of ValTestStep was expected in arguement")

    def add_meas_dist_time_process(self, measid, ego_motion=None, distance=None, time=None):  # pylint: disable=C0103
        """
        Add DistanceTimeProcess for measurement under each test case.

        The total Time and
        Distance processed under each test will be Available as additional TestcaseResult
        on Loading the testcase

        :param measid: Measurement ID if argument given then return measurement specific events
                        otherwise return all events for the testcase
        :type measid: int, None
        :param ego_motion: instance of EgoMotion Class. if the argument is passed then
                            it has Precedence over distance, time argument will be ignore
        :type ego_motion: EgoMotion, None
        :param distance: Distance Process(Kilometer) will be used if ego_motion is not provided
        :type distance: int, None
        :param time: Time Process(Seconds) will be used if ego_motion is not provided
        :type time: int, None
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
            dist_res.set_value(BaseValue("", BaseUnit(GblUnits.UNIT_L_M, label="km"), distance))
#           dist_res.set_value(distance)
            self.add_meas_result(dist_res)
            self.__total_dist += distance

        if time is not None:
            time_res = ValResult(name=self.__mestime_ressname, res_type=self.MEAS_TIME_PROCESS, meas_id=measid,
                                 unit=GblUnits.UNIT_L_S, tag="", parent=None)
            time_res.set_value(BaseValue("", BaseUnit(GblUnits.UNIT_L_S, label="s"), time))
#            time_res.set_value(time)
            self.add_meas_result(time_res)
            self.__add_measid(measid)
            self.__total_time += time

    def get_meas_distance_process(self, measid):  # pylint: disable=C0103
        """
        Get Distance Process for specific to measurement in Kilometer return Int

        :param measid: measurement Id
        :type measid: int
        :return: if exist Distance Value return distance in KM otherwise None
        """
        for meas_res in self.__measresults:
            if meas_res.get_type() == self.MEAS_DIST_PROCESS and \
                    meas_res.get_name() == self.__name and meas_res.get_meas_id() == measid:
                if type(meas_res.get_value()) == BaseValue:
                    return meas_res.get_value().get_value()
        return None

    def get_meas_time_process(self, measid):  # pylint: disable=C0103
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
            if meas_res.get_type() == self.MEAS_TIME_PROCESS and meas_res.get_name() == self.__name and \
                    meas_res.get_meas_id() == measid:
                if type(meas_res.get_value()) == BaseValue:
                    return meas_res.get_value().get_value(), sec_to_hms_string(meas_res.get_value().get_value())
        return None, None

    def get_distance_process(self):  # pylint: disable=C0103
        """
        Get The total Driven Distance for the test case

        :return: Total Distance in Kilometer
        :rtype: int
        """
        return self.__total_dist

    def get_time_process(self):  # pylint: disable=C0103
        """
        Get The total Time processed for the test case

        :return: Total Time in Second as Integer and Duration as String with format HH:MM:SS
        :rtype: int     str
        """
        return self.__total_time, sec_to_hms_string(self.__total_time)

    def get_measurement_ids(self):  # pylint: disable=C0103
        """Returns list of measurements Id for which results is saved
        """
        return self.__measid

    def __add_measid(self, measid):  # pylint: disable=C0103
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
        return self.get_name()

    @property
    def description(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns description of the TestCase as string.
        """
        return self.get_description()

    @property
    def id(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns Id of the TestCase as string.
        """
        return self.get_spe_tag()

    @property
    def doors_url(self):
        """AlgoTestReport Interface overloaded attribute, returns URL of the testcase in doors as string.
        """
        return str(self.get_doors_url())

    @property
    def collection(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns CollectionName of the Testcase as string.
        """
        return self.get_collection_name()

    @property
    def test_result(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns combined result (assessment) of all Teststeps
        of the Testcase as string.
        """
        return str(self.get_assessment().ass_state)

    @property
    def summery_plots(self):
        """AlgoTestReport Interface overloaded attribute, returns list of plots for detailed summery report.
        """
        return self.get_summary_results()

    @property
    def total_dist(self):
        """AlgoTestReport Interface overloaded attribute, returns total distance in km driven for this test case as
        int.
        """
        return self.get_distance_process()

    @property
    def total_time(self):
        """AlgoTestReport Interface overloaded attribute, returns total time in seconds driven for this test case
        as int.
        """
        return self.get_time_process()[0]

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
        :type name: str, None
        :param res_type: Result Type (Distance, KPI, Image Plot, ...)
        :type res_type: str, None
        :param meas_id: Measurement Identifier
        :type meas_id: int, None
        :param unit: Unit Name (Meter, ...)
        :type unit: str, None
        :param tag: Reference Tag (link to doors testspecification)
        :type tag: str
        :param parent: Parent Result (support to link results to a testcase)
        :type parent: int, None
        :param doors_url: url to doors test result
        :type  doors_url: str
        :param exp_res: expected result description
        :type  exp_res: str
        :param desc: opt. description for this result
        :type  desc: str
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

    def get_name(self):  # pylint: disable=C0103
        """ Get the Name of the testcase """
        return self.__name

    def get_spec_tag(self):  # pylint: disable=C0103
        """
        Get Specification Identifier
        """
        return self.__ref_tag

    def get_description(self):  # pylint: disable=C0103
        """
        Get Description text of the result
        """
        return self.__desc

    def get_expected_result(self):  # pylint: disable=C0103
        """
        Get Expected Result
        """
        return self.__exp_res

    def get_doors_url(self):  # pylint: disable=C0103
        """
        Get Doors URLS
        """
        return self.__doors_url

    def set_value(self, value):  # pylint: disable=C0103
        """ Set Result Value Object of the result

        """
        if isinstance(value, BaseValue) or isinstance(value, ValidationPlot):
            # includes: ValueVector, Histogram, ValidationPlot, BaseMessage
            self.__value = value
        elif isinstance(value, str):
            self.__value = BaseMessage("", value)
        else:
            self.__value = BaseValue("", BaseUnit(self.__unit, "", None), value)

        self.__class_name = type(self.__value).__name__

        return True  # needed for backwards compatibility

    def get_value(self):  # pylint: disable=C0103
        """ return the value object of the result
        """
        return self.__value

    def get_meas_id(self):  # pylint: disable=C0103
        """ Get the Measid of the result """
        return self.__meas_id

    def add_assessment(self, assessment):  # pylint: disable=C0103
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

    def get_assessment(self):  # pylint: disable=C0103
        """ Return the Assessment

        :return: Assessment instance
        """
        return self.__assessment

    @property
    def id(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns id string
        """
        return self.get_spec_tag()

    @property
    def doors_url(self):
        """AlgoTestReport Interface overloaded attribute, returns URL of this test step in doors
        """
        return str(self.get_doors_url())

    @property
    def name(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns name of test step
        """
        return self.get_name()

    @property
    def test_result(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns test_result as string.
        """
        if self.get_assessment() is None:
            return ""
        else:
            return str(self.get_assessment().ass_state)

    @property
    def exp_result(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns expected result as string.
        """
        return self.get_expected_result()

    @property
    def meas_result(self):  # pylint: disable=C0103
        """AlgoTestReport Interface overloaded attribute, returns measured result as string.
        """
        return self.get_value()

    @property
    def date(self):
        """AlgoTestReport Interface overloaded attribute, returns date when assessment was changes last time as string.
        """
        if self.get_assessment() is None:
            return ""
        else:
            return str(self.get_assessment().date)

    @property
    def user_account(self):
        """AlgoTestReport Interface overloaded attribute, returns user account of the last assessment change as string.
        """
        if self.get_assessment() is None:
            return ""
        else:
            return str(self.get_assessment().user_account)

    @property
    def issue(self):
        """AlgoTestReport Interface overloaded attribute, returns issue entered for this assessment as string.
        """
        if self.get_assessment() is None:
            return ""
        else:
            return str(self.get_assessment().issue)


class ValTestStep(ValResult):  # pylint: disable=R0904
    """Classs to ValTestStep

    assessment states ('Passed', 'Failed' etc.) defined in `ValAssessmentStates`
    """
    def __init__(self, name=None, res_type=None,
                 unit=None, tag="", parent=None, doors_url="", exp_res="", desc=""):
        # pylint: disable= R0913

        ValResult.__init__(self, name=name, res_type=res_type, unit=unit, tag=tag, parent=parent,
                           doors_url=doors_url, exp_res=exp_res, desc=desc)

    @staticmethod
    def __check_test_step_spec_tag(tag):  # pylint: disable=C0103
        """
        Check if the specification tag is matching DOORS format

        :param tag: Doors ID
        :type tag: str
        """
        #               1        2   3  4   5   6   7  8   9   10  11 12  13   14
        pattern = r"((^[a-z]{2,3}_[a-z]{2,3}|^[a-z]{2,3}))_TC_(\d{3})(_)(\d{3})(-)(\d{2})$"

        match = recomp(pattern, IGNORECASE | DOTALL).search(tag)
        if match is not None:
            return True
        else:
            return False

    # This Function is suppressed for ValTestStep from its parent because it doesn't make sense for TestSteps
    def get_meas_id(self):  # pylint: disable=C0103
        """
        Suppressing the Parent class method which are not valid
        """
        raise StandardError("GetMeasId is not valid Method for ValTestStep Class")


"""
CHANGE LOG:
-----------
$Log: results.py  $
Revision 1.1 2020/03/25 21:34:08CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/val/project.pj
"""
