"""
stk/rep/pdf/reg_test/flowables
-------------------------------

**Specialized Flowables for the RegTestReport:**

**Internal-API Interfaces**

    - `Overview`
    - `TestDescription`
    - `TestStatistic`
    - `SummaryResults`
    - `DetailedSummary`
    - `Testcase`
    - `TableOfContents`
    - `TableOfFigures`
    - `TableOfTables`

**User-API Interfaces**

    - `stk.rep` (complete package)

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.7 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/11/17 11:20:06CET $
"""
# pylint: disable=R0902
# - import Python modules ---------------------------------------------------------------------------------------------
import reportlab.platypus as plat
from reportlab.lib import colors
from reportlab.lib.units import cm
from copy import deepcopy

# - import STK modules ------------------------------------------------------------------------------------------------
from ..base.flowables import TableBase, NORMAL_STYLE, html_str, build_table_header, build_table_row
from ..algo_base.flowables import color_result
from ....val.asmt import ValAssessmentStates
from ....util.helper import sec_to_hms_string


# - defines -----------------------------------------------------------------------------------------------------------
# Table column width definitions
SUMMARY_ID_WIDTH = 160
SUMMARY_NAME_WIDTH = 160
SUMMARY_RESULT_WIDTH = 64

TEST_ID_WIDTH = 140
TEST_NAME_WIDTH = 100
TEST_MEAS_WIDTH = 60
TEST_RESULT_WIDTH = 64
TEST_FR_NUM_WIDTH = 46

TESTCASE1_DESCR_WIDTH = 128
TESTCASE1_VALUE_WIDTH = 352
TESTCASE2_ID_WIDTH = 128
TESTCASE2_EXPECT_WIDTH = 96
TESTCASE2_MEAS_WIDTH = 64
TESTCASE2_RESULT_WIDTH = 64


# - functions ---------------------------------------------------------------------------------------------------------
def upd_row_style(teststep, style, rowcount, to_passed=0, to_failed=0, to_other=0):
    """
    change background color if result is changed marking the new result and count changes
    (green: PASSED, red: FAILED, orange)

    also updates counters if provided

    :param teststep: teststep where to check the result
    :type  teststep: TestStep resp. ValTestcase
    :param style:    row style to append the color settings to
    :type  style:    list
    :param rowcount: row number to change the style
    :type  rowcount: int
    :returns: changed counters
    :rtype: int, int, int
    """
    if teststep.test_result.upper() == ValAssessmentStates.PASSED.upper():
        style.append(('BACKGROUND', (0, rowcount), (-1, rowcount),
                      colors.Whiter(colors.green, 0.1)))
        to_passed += 1
    elif teststep.test_result.upper() == ValAssessmentStates.FAILED.upper():
        style.append(('BACKGROUND', (0, rowcount), (-1, rowcount),
                      colors.Whiter(colors.red, 0.1)))
        to_failed += 1
    else:
        style.append(('BACKGROUND', (0, rowcount), (-1, rowcount),
                      colors.Whiter(colors.orange, 0.1)))
        to_other += 1
    return to_passed, to_failed, to_other


# - classes -----------------------------------------------------------------------------------------------------------
# these table classes normally provide only a _create method,
# some also an Append to add a row
class Overview(TableBase):
    """
    **Regresssion Overview Table**
    providing overview of test run with title, description, project etc.

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    # currently no chance to remove the number of instance attributes
    def __init__(self, name="Regression Overview Table"):
        TableBase.__init__(self)

        self._name = name
        self.title = ""
        self.description = ""
        self.project = ""
        self.component = ""
        self.sim_name = ""
        self.sim_version = ""
        self.val_sw_version = ""
        self.collection = ""
        self.test_spec = ""
        self.remarks = ""
        self._style = []
        self.tr_id = None
        self.test_checkpoint = ""
        self.user_account = ""
        self.ref_id = None
        self.ref_checkpoint = ""
        self.ref_user_account = ""

    def _create(self):
        """
        Does the final creation of the Platypus Table object.
        Including a correct numeration for the Table of Tables list.

        Typically this Method will be called by the _PreBuild-Method of
        the Story class.

        :return: story with all final objects for pdf rendering
        :rtype: list of platypus objects ready for rendering.
        """
        self._style = [('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                       ('GRID', (0, 0), (-1, -1), 1.0, colors.black)]

        data = [[plat.Paragraph("Test Title ", NORMAL_STYLE),
                 plat.Paragraph(str(self.title), NORMAL_STYLE)],
                [plat.Paragraph("Test Description ", NORMAL_STYLE),
                 plat.Paragraph(str(self.description), NORMAL_STYLE)],
                [plat.Paragraph("Project ", NORMAL_STYLE),
                 plat.Paragraph(str(self.project), NORMAL_STYLE)],
                [plat.Paragraph("Component ", NORMAL_STYLE),
                 plat.Paragraph(str(self.component), NORMAL_STYLE)],
                [plat.Paragraph("Simulation config", NORMAL_STYLE),
                 plat.Paragraph(str(self.sim_name), NORMAL_STYLE)],
                [plat.Paragraph("SIL version ", NORMAL_STYLE),
                 plat.Paragraph(str(self.sim_version), NORMAL_STYLE)],
                [plat.Paragraph("Valiation SW version", NORMAL_STYLE),
                 plat.Paragraph(str(self.val_sw_version), NORMAL_STYLE)],
                [plat.Paragraph("Collection ", NORMAL_STYLE),
                 plat.Paragraph(str(self.collection), NORMAL_STYLE)],
                [plat.Paragraph("Test Specification ", NORMAL_STYLE),
                 plat.Paragraph(str(self.test_spec), NORMAL_STYLE)],
                [plat.Paragraph("test TestRun ID", NORMAL_STYLE),
                 plat.Paragraph(str(self.tr_id), NORMAL_STYLE)],
                [plat.Paragraph("test Checkpoint", NORMAL_STYLE),
                 plat.Paragraph(str(self.test_checkpoint), NORMAL_STYLE)],
                [plat.Paragraph("Test run User Account", NORMAL_STYLE),
                 plat.Paragraph(str(self.user_account), NORMAL_STYLE)],
                [plat.Paragraph("Testers Remarks", NORMAL_STYLE),
                 plat.Paragraph(str(self.remarks), NORMAL_STYLE)],
                [plat.Paragraph("reference TestRun ID", NORMAL_STYLE),
                 plat.Paragraph(str(self.ref_id), NORMAL_STYLE)],
                [plat.Paragraph("reference Checkpoint", NORMAL_STYLE),
                 plat.Paragraph(str(self.ref_checkpoint), NORMAL_STYLE)],
                [plat.Paragraph("Reference run User Account ", NORMAL_STYLE),
                 plat.Paragraph(str(self.ref_user_account), NORMAL_STYLE)]]

        story = []

        table = plat.Table(data, style=self._style)

        story.append(table)
        self.append_caption(story)

        return story


class TestDescription(TableBase):
    """
    **Test Description table for the overview**
    listing all test cases with name and description

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    def __init__(self):
        TableBase.__init__(self)

        self._name = "Test Description"
        self._style = []
        self._testcases = []

    def append(self, testcase):
        """ add a new testcase to the list
        """
        self._testcases.append(testcase)

    def _create(self):
        """
        Does the final creation of the Platypus Table object.
        Including a correct numeration for the Table of Tables list.

        Typically this Method will be called by the _PreBuild-Method of
        the Story class.

        :return: story with all final objects for pdf rendering
        :rtype: list of platypus objects ready for rendering.
        """
        self._style = [('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
                       ('GRID', (0, 0), (-1, -1), 1.0, colors.black)]

        data = [build_table_header(['Testcase', 'Description'])]

        for testcase in self._testcases:
            data.append([plat.Paragraph(html_str(testcase.name), NORMAL_STYLE),
                         plat.Paragraph(html_str(testcase.description), NORMAL_STYLE)])

        story = []

        table = plat.Table(data, style=self._style)

        story.append(table)
        self.append_caption(story)

        return story


class TestStatistic(TableBase):
    """
    **Test Statistics table**

    contains total distance and total time as default rows,
    can get additional user defined rows with result, value and unit triples

    for first approach same class as in algo_test.flowables,
    will need to change if different lists of test steps are considered in the regression report as:

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    def __init__(self):
        TableBase.__init__(self)

        self._name = "Test Statistics table"
        self._testrun = None
        self._statistics = []

    def set_testrun(self, testrun):
        """
        set testrun attribute to read its statistic values

        :param testrun: TestRun of this report
        :type testrun:  `TestRun`
        """
        self._testrun = testrun

    def append(self, statistic_row):
        """
        Append one additional Statistic row to the Table.
        This Method can be called multiple Times, to append more Data Sets.

        :param statistic_row: list with result description, value and unit as strings.
        :type statistic_row:  list(string, string, string)
        """
        self._statistics.append(statistic_row)

    def _create(self):
        """
        Does the final creation of the Platypus Table object.
        Including a correct numeration for the Table of Tables list.

        Typically this Method will be called by the _PreBuild-Method of
        the Story class.

        :return: story with all final objects for pdf rendering
        :rtype: list of platypus objects ready for rendering.
        """
        style = [('GRID', (0, 0), (-1, -1), 1.0, colors.black),
                 ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)]

        data = [build_table_header(["Results", "Values", "Unit"])]

        # Add the Header to the data

        if self._testrun is not None:
            data.append(build_table_row(['processed distance', str(self._testrun.processed_distance), 'Kilometer']))
            data.append(build_table_row(['processed time', str(self._testrun.processed_time), 'H:M:S']))
            data.append(build_table_row(['processed files', str(self._testrun.processed_files), 'count']))
        for row in self._statistics:
            data.append(build_table_row(row))

        story = []

        table = plat.Table(data, style=style)

        story.append(table)
        self.append_caption(story)

        return story


class SummaryResults(TableBase):
    """
    **Summary TestStep Results Table**
    with "Teststep_ID", "Name" and one "Result" for test and reference of each test step

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    # currently no chance to remove the number of instance attributes
    def __init__(self):
        TableBase.__init__(self)

        self._name = "Summary Teststep Results"
        self._teststeps = []
        self._test_failed = 0
        self._test_passed = 0
        self._test_notassessed = 0
        self._refsteps = []
        self._ref_failed = 0
        self._ref_passed = 0
        self._ref_notassessed = 0
        self.summary = True

    def append(self, testcase):
        """
        Append one Statistic Data Set to the Table.
        This Method can be called multiple Times, to append more Data Sets.
        """

        for teststep in testcase.test_steps:
            if teststep.test_result.upper() == ValAssessmentStates.PASSED.upper():
                self._test_passed += 1
            elif teststep.test_result.upper() == ValAssessmentStates.FAILED.upper():
                self._test_failed += 1
            else:
                self._test_notassessed += 1
            self._teststeps.append(teststep)

    def append_ref(self, testcase):
        """
        Append one Reference Statistic Data Set to the Table.
        This Method can be called multiple Times, to append more Data Sets.
        """
        testrun_step_ids = [tst.id for tst in self._teststeps]
        for teststep in testcase.test_steps:
            # if reference step not in new testrun
            # add it to be listed but clean result
            if teststep.id not in testrun_step_ids:
                refstep = deepcopy(teststep)
                refstep.test_result = ''
                self._teststeps.append(refstep)
            if teststep.test_result.upper() == ValAssessmentStates.PASSED.upper():
                self._ref_passed += 1
            elif teststep.test_result.upper() == ValAssessmentStates.FAILED.upper():
                self._ref_failed += 1
            else:
                self._ref_notassessed += 1
            self._refsteps.append(teststep)

    def _create(self):
        """
        Does the final creation of the Platypus Table object.
        Including a correct numeration for the Table of Tables list.

        Typically this Method will be called by the _PreBuild-Method of
        the Story class.

        :return: story with all final objects for pdf rendering
        :rtype: list of platypus objects ready for rendering.
        """
        style = [('GRID', (0, 0), (-1, -1), 1.0, colors.black),
                 ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)]

        data = []

        to_passed = 0
        to_failed = 0
        to_other = 0
        # Add the Header to the data
        data.append(build_table_header(["Teststep_ID", "Name", "Reference Result", "Test Run Result"]))
        rowcount = 1
        for teststep in self._teststeps:
            found = False
            for refstep in self._refsteps:
                if teststep.id == refstep.id:
                    ref_result = refstep.test_result
                    if teststep.test_result.upper() != ref_result.upper():
                        to_passed, to_failed, to_other = upd_row_style(teststep, style, rowcount,
                                                                       to_passed, to_failed, to_other)

                    data.append(build_table_row([html_str(teststep.id),
                                                 html_str(teststep.name),
                                                 color_result(ref_result),
                                                 color_result(teststep.test_result)]))
                    rowcount += 1
                    found = True
            if not found:
                # new teststep not in reference
                to_passed, to_failed, to_other = upd_row_style(teststep, style, rowcount,
                                                               to_passed, to_failed, to_other)
                data.append(build_table_row([html_str(teststep.id),
                                             html_str(teststep.name),
                                             '',
                                             color_result(teststep.test_result)]))
                rowcount += 1

        story = []

        table = plat.Table(data, colWidths=[SUMMARY_ID_WIDTH, SUMMARY_NAME_WIDTH,
                                            SUMMARY_RESULT_WIDTH, SUMMARY_RESULT_WIDTH], style=style)

        story.append(table)
        self.append_caption(story)
        story.append(plat.Spacer(1, 1 * cm))

        if self.summary:
            data2 = []
            style = [('GRID', (0, 0), (-1, -1), 1.0, colors.black),
                     ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)]
            # ('LINEABOVE', (0, 3), (-1, 3), 2.0, colors.black)]
            # ('TEXTCOLOR', (0, 3), (-1, 3), colors.grey)]
            # Add the Header to the data
            data2.append(build_table_header(["Regression",
                                             "Test(s) Performed",
                                             color_result(ValAssessmentStates.PASSED.upper()),
                                             color_result(ValAssessmentStates.FAILED.upper()),
                                             color_result(ValAssessmentStates.NOT_ASSESSED.upper())]))
            data2.append(["reference", self._ref_passed + self._ref_failed + self._ref_notassessed,
                          self._ref_passed, self._ref_failed, self._ref_notassessed])
            data2.append(["test run", self._test_passed + self._test_failed + self._test_notassessed,
                          self._test_passed, self._test_failed, self._test_notassessed])
            # data2.append(["change: ref -> test", '', to_passed, to_failed, to_other])

            table2 = plat.Table(data2, style=style)

            story.append(table2)
            story.append(plat.Spacer(1, 1 * cm))

            data = []
            style = [('GRID', (0, 0), (-1, -1), 1.0, colors.black),
                     ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)]
            data.append(build_table_header(['changed',
                                            'to ' + color_result(ValAssessmentStates.PASSED.upper()),
                                            'to ' + color_result(ValAssessmentStates.FAILED.upper()),
                                            'to ' + color_result(ValAssessmentStates.NOT_ASSESSED.upper())]))
            data.append(["ref -> test", to_passed, to_failed, to_other])
            table = plat.Table(data, style=style)

            story.append(table)
            story.append(plat.Spacer(1, 1 * cm))

        return story


class SummaryTestcases(TableBase):
    """
    **Summary Testcase Results Table**
    with "Testcase_ID", "Name" and combined "Result" columns for test and reference of each test case

    test case result calculated while loading test run:
      - one FAILED test step results in FAILED
      - one not PASSED and not FAILED test step (e.g. investigate) results in NOT_ASSESSED
      - only if all test steps are PASSED result will be PASSED

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    # currently no chance to remove the number of instance attributes
    def __init__(self):
        TableBase.__init__(self)

        self._name = "Summary Testcase Results"
        self._testcases = []
        self._test_failed = 0
        self._test_passed = 0
        self._test_notassessed = 0
        self._refcases = []
        self._ref_failed = 0
        self._ref_passed = 0
        self._ref_notassessed = 0
        self.summary = True

    def append(self, testcase):
        """
        Append one Statistic Data Set to the Table.
        This Method can be called multiple Times, to append more Data Sets.
        """

        if testcase.test_result.upper() == ValAssessmentStates.PASSED.upper():
            self._test_passed += 1
        elif testcase.test_result.upper() == ValAssessmentStates.FAILED.upper():
            self._test_failed += 1
        else:
            self._test_notassessed += 1

        self._testcases.append(testcase)

    def append_ref(self, testcase):
        """
        Append one Statistic Data Set to the Table.
        This Method can be called multiple Times, to append more Data Sets.
        """

        if testcase.test_result.upper() == ValAssessmentStates.PASSED.upper():
            self._ref_passed += 1
        elif testcase.test_result.upper() == ValAssessmentStates.FAILED.upper():
            self._ref_failed += 1
        else:
            self._ref_notassessed += 1

        self._refcases.append(testcase)

    def _create(self):
        """
        Does the final creation of the Platypus Table object.
        Including a correct numeration for the Table of Tables list.

        Typically this Method will be called by the _PreBuild-Method of
        the Story class.

        :return: story with all final objects for pdf rendering
        :rtype: list of platypus objects ready for rendering.
        """
        style = [('GRID', (0, 0), (-1, -1), 1.0, colors.black),
                 ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)]

        data = []

        to_passed = 0
        to_failed = 0
        to_other = 0
        # Add the Header to the data
        data.append(build_table_header(["Teststep_ID", "Name", "Reference Result", "Test Run Result"]))
        rowcount = 1

        for testcase in self._testcases:
            ref_result = ""
            for refcase in self._refcases:
                if testcase.id == refcase.id:
                    ref_result = refcase.test_result
            if testcase.test_result.upper() != ref_result.upper():
                # change background color if result is changed marking the new result
                # (green: PASSED, red: FAILED, orange)
                if testcase.test_result.upper() == ValAssessmentStates.PASSED.upper():
                    style.append(('BACKGROUND', (0, rowcount), (-1, rowcount), colors.Whiter(colors.green, 0.1)))
                    to_passed += 1
                elif testcase.test_result.upper() == ValAssessmentStates.FAILED.upper():
                    style.append(('BACKGROUND', (0, rowcount), (-1, rowcount), colors.Whiter(colors.red, 0.1)))
                    to_failed += 1
                else:
                    style.append(('BACKGROUND', (0, rowcount), (-1, rowcount), colors.Whiter(colors.orange, 0.1)))
                    to_other += 1

            data.append(build_table_row([html_str(testcase.id),
                                         html_str(testcase.name),
                                         color_result(ref_result),
                                         color_result(testcase.test_result)]))
            rowcount += 1

        story = []

        table = plat.Table(data, colWidths=[SUMMARY_ID_WIDTH, SUMMARY_NAME_WIDTH,
                                            SUMMARY_RESULT_WIDTH, SUMMARY_RESULT_WIDTH], style=style)

        story.append(table)
        self.append_caption(story)
        story.append(plat.Spacer(1, 1 * cm))

        if self.summary:
            data2 = []
            style = [('GRID', (0, 0), (-1, -1), 1.0, colors.black),
                     ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)]
            # Add the Header to the data
            data2.append(build_table_header(["Regression",
                                             "Test(s) Performed",
                                             color_result(ValAssessmentStates.PASSED.upper()),
                                             color_result(ValAssessmentStates.FAILED.upper()),
                                             color_result(ValAssessmentStates.NOT_ASSESSED.upper())]))
            data2.append(["reference", self._ref_passed + self._ref_failed + self._ref_notassessed,
                          self._ref_passed, self._ref_failed, self._ref_notassessed])
            data2.append(["test run", self._test_passed + self._test_failed + self._test_notassessed,
                          self._test_passed, self._test_failed, self._test_notassessed])

            table2 = plat.Table(data2, style=style)

            story.append(table2)
            story.append(plat.Spacer(1, 1 * cm))

            data = []
            style = [('GRID', (0, 0), (-1, -1), 1.0, colors.black),
                     ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)]
            data.append(build_table_header(['changed',
                                            'to ' + color_result(ValAssessmentStates.PASSED.upper()),
                                            'to ' + color_result(ValAssessmentStates.FAILED.upper()),
                                            'to ' + color_result(ValAssessmentStates.NOT_ASSESSED.upper())]))
            data.append(["ref -> test", to_passed, to_failed, to_other])
            table = plat.Table(data, style=style)

            story.append(table)
            story.append(plat.Spacer(1, 1 * cm))

        return story


class DetailedSummary(TableBase):
    """
    **Detailed Summary Result table**
    listing all test cases with all their test steps and results

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    def __init__(self):
        TableBase.__init__(self)

        self._name = "Detailed Summary Result table"
        self._testcases = []
        self._refcases = []

    def append(self, testcase):
        """
        Append one Statstic Data Set to the Table.
        This Method can be called multiple Times, to append more Data Sets.
        """
        self._testcases.append(testcase)

    def append_ref(self, testcase):
        """
        Append one Statstic Data Set to the Table.
        This Method can be called multiple Times, to append more Data Sets.
        """
        self._refcases.append(testcase)

    def _create(self):
        """
        Does the final creation of the Platypus Table object.
        Including a correct numeration for the Table of Tables list.

        Typically this Method will be called by the _PreBuild-Method of
        the Story class.

        :return: story with all final objects for pdf rendering
        :rtype: list of platypus objects ready for rendering.
        """
        style = [('GRID', (0, 0), (-1, -1), 1.0, colors.black),
                 ('BACKGROUND', (0, 0), (-1, 0), colors.darkgrey)]

        data = []

        # Add the Header to the dat
        rowcount = 0
        for testcase in self._testcases:
            # find matching testcase in reference
            testcase_ref = None
            ref_result = ''
            teststeps_ref = []
            for case in self._refcases:
                if case.id == testcase.id:
                    ref_result = case.test_result
                    testcase_ref = case

                    # store all test steps only in reference test case,
                    # later we list all test steps of current run and add these only in reference
                    step_ids = [tst.id for tst in testcase.test_steps]
                    for ref_step in case.test_steps:
                        if ref_step.id not in step_ids:
                            teststeps_ref.append(ref_step)
                    break

            # Add TestCase information
            if testcase.test_result.upper() != ref_result.upper():
                if testcase.test_result.upper() == ValAssessmentStates.PASSED.upper():
                    style.append(('BACKGROUND', (0, rowcount), (-1, rowcount), colors.Blacker(colors.green, 0.8)))
                elif testcase.test_result.upper() == ValAssessmentStates.FAILED.upper():
                    style.append(('BACKGROUND', (0, rowcount), (-1, rowcount), colors.Blacker(colors.red, 0.8)))
            else:
                style.append(('BACKGROUND', (0, rowcount), (-1, rowcount), colors.darkgrey))
            style.append(('TEXTCOLOR', (0, rowcount), (2, rowcount), colors.white))
            data.append(build_table_row([html_str(testcase.id),
                                         html_str(testcase.name),
                                         color_result(ref_result),
                                         color_result(testcase.test_result)]))
            rowcount += 1
            style.append(('BACKGROUND', (0, rowcount), (-1, rowcount), colors.lightgrey))
            data.append(build_table_row(['Teststep_ID', 'Name', 'Reference Result', 'Test Run Result', 'ASMT']))
            rowcount += 1

            # Ad Teststeps information of all test steps in current test
            for teststep in testcase.test_steps:
                ref_result = ""
                if testcase_ref:
                    for ref_step in testcase_ref.test_steps:
                        if teststep.id == ref_step.id:
                            ref_result = ref_step.test_result
                            break
                if teststep.test_result.upper() != ref_result.upper():
                    upd_row_style(teststep, style, rowcount)

                data.append(build_table_row([html_str(teststep.id),
                                             html_str(teststep.name),
                                             color_result(ref_result),
                                             color_result(teststep.test_result)]))
                rowcount += 1
            # add test steps only in reference
            for ref_step in teststeps_ref:
                # color orange as test step not in current run
                style.append(('BACKGROUND', (0, rowcount), (-1, rowcount), colors.Whiter(colors.orange, 0.1)))

                data.append(build_table_row([html_str(ref_step.id),
                                             html_str(ref_step.name),
                                             color_result(ref_step.test_result), "", ""]))
                rowcount += 1

        story = []

        table = plat.Table(data, colWidths=[SUMMARY_ID_WIDTH, SUMMARY_NAME_WIDTH,
                                            SUMMARY_RESULT_WIDTH, SUMMARY_RESULT_WIDTH], style=style)

        story.append(table)
        self.append_caption(story)
        story.append(plat.Spacer(1, 1 * cm))

        return story


class Testcase(TableBase):
    """
    **Detailed Summary Result** result for single Testcase

    two sectioned table showing
      - test case information like id, playlist and distance
      - test step details with name, expected and measured result and assessment

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    def __init__(self, testcase, refcase):
        TableBase.__init__(self)

        self._name = "Detailed Summary Result - %s" % html_str(testcase.id)

        self._testcase = testcase
        self._teststeps = []
        self._refcase = refcase
        self._refsteps = []

        self.append(testcase)
        self.append_ref(refcase)

    def append(self, testcase):
        """
        Append one Statistic Data Set to the Table.
        This Method can be called multiple Times, to append more Data Sets.
        """
        for teststep in testcase.test_steps:
            self._teststeps.append(teststep)

    def append_ref(self, testcase):
        """
        Append one Reference Statistic Data Set to the Table.
        This Method can be called multiple Times, to append more Data Sets.
        """
        testrun_step_ids = [tst.id for tst in self._teststeps]
        for teststep in testcase.test_steps:
            # if reference step not in new testrun
            # add it to be listed but clean result
            if teststep.id not in testrun_step_ids:
                refstep = deepcopy(teststep)
                refstep.test_result = ''
                refstep.meas_result = ''
                self._teststeps.append(refstep)
            self._refsteps.append(teststep)

    def _create(self):
        """
        Does the final creation of the Platypus Table object.
        Including a correct numeration for the Table of Tables list.

        Typically this Method will be called by the _PreBuild-Method of
        the Story class.

        :return: story with all final objects for pdf rendering
        :rtype: list of platypus objects ready for rendering.
        """
        story = []

        style = [('GRID', (0, 0), (-1, -1), 1.0, colors.black),
                 ('BACKGROUND', (0, 0), (0, 6), colors.lightgrey)]

        data = [build_table_row(['Testcase Name', html_str(self._testcase.name)]),
                build_table_row(['Testcase Identifier', html_str(self._testcase.id)]),
                ['Playlist/Recording', html_str(self._testcase.collection)],
                ['Time Processed [H:M:S]', sec_to_hms_string(self._testcase.total_time)],
                ['Distance Processed [km]', str(self._testcase.total_dist)]]

        # data.append(['Files Processed', self._testcase.processed_files]) #Todo: rh

        table = plat.Table(data, style=style, colWidths=[TESTCASE1_DESCR_WIDTH, TESTCASE1_VALUE_WIDTH])
        story.append(table)

        style = [('GRID', (0, 0), (-1, -1), 1.0, colors.black),
                 ('BACKGROUND', (0, 0), (5, 0), colors.lightgrey)]
        data = [build_table_header(['Teststep', 'Expected Result', 'Reference Measured Result', 'Reference Result',
                                    'Test Run Measured Result ', 'Test Run Result'])]

        # Add the Header to the data
        rowcount = 1
        for teststep in self._teststeps:
            found = False
            for refstep in self._refsteps:
                if teststep.id == refstep.id:
                    ref_result = refstep.test_result
                    found = True
                    if teststep.test_result.upper() != ref_result.upper():
                        upd_row_style(teststep, style, rowcount)

                    data.append(build_table_row([html_str(teststep.id),
                                                 html_str(teststep.exp_result),
                                                 html_str(refstep.meas_result),
                                                 color_result(ref_result),
                                                 html_str(teststep.meas_result),
                                                 color_result(teststep.test_result)]))
                    rowcount += 1
            if not found:
                # new teststep not in reference
                upd_row_style(teststep, style, rowcount)
                data.append(build_table_row([html_str(teststep.id),
                                             html_str(teststep.exp_result),
                                             '',
                                             '',
                                             html_str(teststep.meas_result),
                                             color_result(teststep.test_result)]))
                rowcount += 1

        table = plat.Table(data, style=style, colWidths=[TESTCASE2_ID_WIDTH, TESTCASE2_EXPECT_WIDTH,
                                                         TESTCASE2_MEAS_WIDTH, TESTCASE2_RESULT_WIDTH,
                                                         TESTCASE2_MEAS_WIDTH, TESTCASE2_RESULT_WIDTH])
        story.append(table)
        self.append_caption(story)

        story.append(plat.Spacer(1, 1 * cm))

        return story


"""
CHANGE LOG:
-----------
$Log: flowables.py  $
Revision 1.7 2016/11/17 11:20:06CET Hospes, Gerd-Joachim (uidv8815) 
move table formatter methods to pdf.base to support line break for columns in base.flowable.Table
Revision 1.6 2016/07/22 15:54:01CEST Hospes, Gerd-Joachim (uidv8815)
new fields sim version and val sw version
Revision 1.5 2016/05/09 11:00:18CEST Hospes, Gerd-Joachim (uidv8815)
add new column REMARKS to val.db and to pfd reports as new overview table row
Revision 1.4 2015/11/20 17:39:29CET Hospes, Gerd-Joachim (uidv8815)
fix pep8 and pylint errors
- Added comments -  uidv8815 [Nov 20, 2015 5:39:30 PM CET]
Change Package : 398693:1 http://mks-psad:7002/im/viewissue?selection=398693
Revision 1.3 2015/11/20 11:19:32CET Hospes, Gerd-Joachim (uidv8815)
correct tables to list all test steps only in one testrun (ref or current)
--- Added comments ---  uidv8815 [Nov 20, 2015 11:19:32 AM CET]
Change Package : 382785:1 http://mks-psad:7002/im/viewissue?selection=382785
Revision 1.2 2015/10/29 17:48:06CET Hospes, Gerd-Joachim (uidv8815)
add collection and sim_name to reports
Revision 1.1 2015/04/23 19:05:23CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/rep/pdf/reg_test/project.pj
Revision 1.10 2015/01/20 16:26:44CET Mertens, Sven (uidv7805)
removing deprecated calls
--- Added comments ---  uidv7805 [Jan 20, 2015 4:26:44 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.9 2014/08/28 18:45:26CEST Zafar, Sohaib (uidu6396)
Regression Template extended
--- Added comments ---  uidu6396 [Aug 28, 2014 6:45:26 PM CEST]
Change Package : 250924:1 http://mks-psad:7002/im/viewissue?selection=250924
Revision 1.8 2014/07/28 19:22:39CEST Hospes, Gerd-Joachim (uidv8815)
add step only in one run to list, fix PASSED/FAILED counter
--- Added comments ---  uidv8815 [Jul 28, 2014 7:22:40 PM CEST]
Change Package : 246030:1 http://mks-psad:7002/im/viewissue?selection=246030
Revision 1.7 2014/06/24 17:01:25CEST Hospes, Gerd-Joachim (uidv8815)
move table caption below table, extend some epydoc
--- Added comments ---  uidv8815 [Jun 24, 2014 5:01:26 PM CEST]
Change Package : 243858:1 http://mks-psad:7002/im/viewissue?selection=243858
Revision 1.6 2014/06/22 23:07:23CEST Hospes, Gerd-Joachim (uidv8815)
sync between templates and flowables,
algo_test.report generates perf, func and regr tests
algo_test template and flowable moved to perf_test
--- Added comments ---  uidv8815 [Jun 22, 2014 11:07:23 PM CEST]
Change Package : 241732:1 http://mks-psad:7002/im/viewissue?selection=241732
Revision 1.5 2014/05/20 13:18:27CEST Hospes, Gerd-Joachim (uidv8815)
add user_account to report, based on testrun or ifc definition, update test_report
--- Added comments ---  uidv8815 [May 20, 2014 1:18:27 PM CEST]
Change Package : 233145:1 http://mks-psad:7002/im/viewissue?selection=233145
Revision 1.4 2014/05/06 14:07:50CEST Hospes, Gerd-Joachim (uidv8815)
fix spelling errors
--- Added comments ---  uidv8815 [May 6, 2014 2:07:51 PM CEST]
Change Package : 233144:1 http://mks-psad:7002/im/viewissue?selection=233144
Revision 1.3 2014/04/09 09:49:45CEST Hospes, Gerd-Joachim (uidv8815)
minor style fixes, prep details table for reg test report
--- Added comments ---  uidv8815 [Apr 9, 2014 9:49:45 AM CEST]
Change Package : 227496:1 http://mks-psad:7002/im/viewissue?selection=227496
Revision 1.2 2014/04/07 14:06:16CEST Hospes, Gerd-Joachim (uidv8815)
pep8 & pylint fixes after adding new packages and splitting some modules
--- Added comments ---  uidv8815 [Apr 7, 2014 2:06:16 PM CEST]
Change Package : 227496:1 http://mks-psad:7002/im/viewissue?selection=227496
Revision 1.1 2014/04/04 17:38:41CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
stk/rep/pdf/reg_test/project.pj
Revision 1.23 2014/03/28 11:32:43CET Hecker, Robert (heckerr)
commented out warnings.
--- Added comments ---  heckerr [Mar 28, 2014 11:32:44 AM CET]
Change Package : 228098:1 http://mks-psad:7002/im/viewissue?selection=228098
Revision 1.22 2014/03/28 10:25:50CET Hecker, Robert (heckerr)
Adapted to new coding guiedlines incl. backwardcompatibility.
--- Added comments ---  heckerr [Mar 28, 2014 10:25:50 AM CET]
Change Package : 228098:1 http://mks-psad:7002/im/viewissue?selection=228098
Revision 1.21 2014/03/27 12:29:06CET Hecker, Robert (heckerr)
Added six backwardcompatibility.
--- Added comments ---  heckerr [Mar 27, 2014 12:29:06 PM CET]
Change Package : 227240:2 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.20 2014/03/26 13:28:09CET Hecker, Robert (heckerr)
Added python 3 changes.
--- Added comments ---  heckerr [Mar 26, 2014 1:28:10 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.19 2014/03/25 15:23:16CET Hospes, Gerd-Joachim (uidv8815)
conversion to html_str added for test step ids, added unicode values to test
--- Added comments ---  uidv8815 [Mar 25, 2014 3:23:17 PM CET]
Change Package : 227369:1 http://mks-psad:7002/im/viewissue?selection=227369
Revision 1.18 2014/03/17 18:24:35CET Hospes, Gerd-Joachim (uidv8815)
add Heading4 and according style for TOC
--- Added comments ---  uidv8815 [Mar 17, 2014 6:24:35 PM CET]
Change Package : 224320:1 http://mks-psad:7002/im/viewissue?selection=224320
Revision 1.17 2014/03/14 10:29:08CET Hospes, Gerd-Joachim (uidv8815)
pylint fixes
--- Added comments ---  uidv8815 [Mar 14, 2014 10:29:08 AM CET]
Change Package : 221504:1 http://mks-psad:7002/im/viewissue?selection=221504
Revision 1.16 2014/03/13 19:06:20CET Hospes, Gerd-Joachim (uidv8815)
list results of testcases and teststeps seperatly
--- Added comments ---  uidv8815 [Mar 13, 2014 7:06:21 PM CET]
Change Package : 221504:1 http://mks-psad:7002/im/viewissue?selection=221504
Revision 1.15 2014/03/06 18:00:30CET Hospes, Gerd-Joachim (uidv8815)
add colWidths for all tables to get wordWrap active
--- Added comments ---  uidv8815 [Mar 6, 2014 6:00:30 PM CET]
Change Package : 223788:1 http://mks-psad:7002/im/viewissue?selection=223788
Revision 1.14 2014/03/04 16:15:39CET Hospes, Gerd-Joachim (uidv8815)
splitting long words in table columns
--- Added comments ---  uidv8815 [Mar 4, 2014 4:15:40 PM CET]
Change Package : 221501:1 http://mks-psad:7002/im/viewissue?selection=221501
Revision 1.13 2014/02/27 18:04:47CET Hospes, Gerd-Joachim (uidv8815)
remove tasks (holding number of tasks of a job) as not available on Hpc
Revision 1.12 2014/02/21 16:55:44CET Hospes, Gerd-Joachim (uidv8815)
add RotatedText() method for table cells in rep.pdf.algo_test.flowables
Revision 1.11 2014/02/20 17:44:17CET Hospes, Gerd-Joachim (uidv8815)
use new processed_<values> in pdf report
--- Added comments ---  uidv8815 [Feb 20, 2014 5:44:18 PM CET]
Change Package : 220099:1 http://mks-psad:7002/im/viewissue?selection=220099
Revision 1.10 2014/02/19 11:31:15CET Hospes, Gerd-Joachim (uidv8815)
add user and date of teststep and fix test results in xlsx and pdf
--- Added comments ---  uidv8815 [Feb 19, 2014 11:31:16 AM CET]
Change Package : 220000:1 http://mks-psad:7002/im/viewissue?selection=220000
Revision 1.9 2014/02/14 14:42:57CET Hospes, Gerd-Joachim (uidv8815)
epidoc and pep8/pylint fixes
Revision 1.8 2014/02/13 17:40:31CET Hospes, Gerd-Joachim (uidv8815)
add distance and time to testcases and statistic table, fix table style and '<' handling
--- Added comments ---  uidv8815 [Feb 13, 2014 5:40:31 PM CET]
Change Package : 218178:1 http://mks-psad:7002/im/viewissue?selection=218178
Revision 1.7 2014/02/12 18:34:56CET Hospes, Gerd-Joachim (uidv8815)
update table styles, use stk defines for assessment states, add table captions
--- Added comments ---  uidv8815 [Feb 12, 2014 6:34:57 PM CET]
Change Package : 218178:1 http://mks-psad:7002/im/viewissue?selection=218178
Revision 1.6 2014/02/05 13:58:22CET Hospes, Gerd-Joachim (uidv8815)
chapter Test Execution Details added to report with template, flowables and tests
--- Added comments ---  uidv8815 [Feb 5, 2014 1:58:23 PM CET]
Change Package : 214928:1 http://mks-psad:7002/im/viewissue?selection=214928
Revision 1.5 2014/02/03 11:39:22CET Hecker, Robert (heckerr)
Using TestResults defines now from ValAsessmentStates.
--- Added comments ---  heckerr [Feb 3, 2014 11:39:23 AM CET]
Change Package : 216738:1 http://mks-psad:7002/im/viewissue?selection=216738
Revision 1.4 2013/12/04 13:46:12CET Hecker, Robert (heckerr)
BugFixing.
--- Added comments ---  heckerr [Dec 4, 2013 1:46:13 PM CET]
Change Package : 209900:1 http://mks-psad:7002/im/viewissue?selection=209900
Revision 1.3 2013/10/25 09:02:31CEST Hecker, Robert (heckerr)
Removed Pep8 Issues.
--- Added comments ---  heckerr [Oct 25, 2013 9:02:31 AM CEST]
Change Package : 202843:1 http://mks-psad:7002/im/viewissue?selection=202843
Revision 1.2 2013/10/21 08:44:23CEST Hecker, Robert (heckerr)
updated doxygen description.
--- Added comments ---  heckerr [Oct 21, 2013 8:44:23 AM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.1 2013/10/18 17:45:12CEST Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/rep/pdf/algo_test/project.pj
"""
