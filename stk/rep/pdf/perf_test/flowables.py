"""
stk/rep/pdf/algo_test/flowables
-------------------------------

**Specialized Flowables for the AlgoTestReport:**

**Internal-API Interfaces**

    - `Overview`
    - `TestDescription`
    - `TestStatistic`
    - `SummaryResults`
    - `DetailedSummary`
    - `Testcase`
    - `RuntimeIncidentsTable`
    - `IncidentDetailsTables`
    - `TableOfContents`
    - `TableOfFigures`
    - `TableOfTables`

**User-API Interfaces**

    - `stk.rep` (complete package)

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.7 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/12/05 14:39:06CET $
"""
# Import Python Modules --------------------------------------------------------
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import reportlab.platypus as plat
from reportlab.lib import colors
from reportlab.lib.units import cm
from operator import attrgetter
import warnings

# Import STK Modules -----------------------------------------------------------
from ..base.flowables import TableBase, html_str, url_str, filter_cols, \
    build_table_row, build_table_header, NORMAL_STYLE
from ..algo_base.flowables import color_result
from ....val.asmt import ValAssessmentStates
from ....util.helper import sec_to_hms_string
from stk.util.helper import deprecated

pdfmetrics.registerFont(TTFont('Calibri', 'Calibri.ttf'))
# Defines ----------------------------------------------------------------------

# Table column width definitions
OVERVIEW_DESCR_WIDTH = 120
OVERVIEW_VALUE_WIDTH = 340

SUMMARY_ID_WIDTH = 190
SUMMARY_NAME_WIDTH = 190
SUMMARY_RESULT_WIDTH = 64

TEST_ID_WIDTH = 140
TEST_NAME_WIDTH = 100
TEST_MEAS_WIDTH = 60
TEST_RESULT_WIDTH = 64
TEST_FR_NUM_WIDTH = 46
TEST_DETAILS_WIDTHS = (TEST_ID_WIDTH, TEST_NAME_WIDTH, TEST_MEAS_WIDTH, TEST_MEAS_WIDTH,
                       TEST_RESULT_WIDTH, TEST_FR_NUM_WIDTH)

TESTCASE1_DESCR_WIDTH = 120
TESTCASE1_VALUE_WIDTH = 340
TESTCASE2_ID_WIDTH = 140
TESTCASE2_MEAS_WIDTH = 128
TESTCASE2_RESULT_WIDTH = 64

# max page width: 460
INCDNT_TASK_WIDTH = 40
INCDNT_ERROR_WIDTH = 70
INCDNT_DESC_WIDTH = 140
INCDNT_SOURCE_WIDTH = 210


# Functions --------------------------------------------------------------------

@deprecated('algo_base.flowables.color_result')
def ColorResult(result):  # pylint: disable=C0103
    """deprecated"""
    return color_result(result)


@deprecated('algo_base.flowables.build_table_header')
def BuildTableHeader(column_names):  # pylint: disable=C0103
    """deprecated"""
    return build_table_header(column_names)


@deprecated('algo_base.flowables.build_table_row')
def BuildTableRow(row_items):  # pylint: disable=C0103
    """deprecated"""
    return build_table_row(row_items)


# Classes ----------------------------------------------------------------------
# these table classes normally provide only a _create method,
# some also an Append to add a row
# pylint: disable=R0903
class Overview(TableBase):
    """
    **Test Overview Table**
    providing overview of test run with title, description, project etc.

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    def __init__(self):
        TableBase.__init__(self)

        self._name = "Test Overview Table"
        self.title = ""
        self.tr_id = ""
        self.description = ""
        self.project = ""
        self.component = ""
        self.test_checkpoint = ""
        self.sim_name = ""
        self.sim_version = ""
        self.val_sw_version = ""
        self.collection = ""
        self.user_account = ""
        self.test_spec = ""
        self.remarks = ""
        self._style = []
        # used for regression tests, but not in this class, just to satisfy pylint
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
        data = [build_table_row(["Test Title", html_str(self.title)]),
                build_table_row(["Test Description", html_str(self.description)]),
                build_table_row(["Project", html_str(self.project)]),
                build_table_row(["Component", html_str(self.component)]),
                build_table_row(["Simulation config", html_str(self.sim_name)]),
                build_table_row(["SIL version ", html_str(self.sim_version)]),
                build_table_row(["Validation SW version", html_str(self.val_sw_version)]),
                build_table_row(["Collection", html_str(self.collection)]),
                build_table_row(["User Account", str(self.user_account)]),
                build_table_row(["TestRun ID", html_str(self.tr_id)]),
                build_table_row(["Testers Remarks", html_str(self.remarks)])]

        story = []

        table = plat.Table(data, colWidths=[OVERVIEW_DESCR_WIDTH, OVERVIEW_VALUE_WIDTH], style=self._style)

        story.append(table)
        self.append_caption(story)

        return story

    @deprecated('_create')
    def _Create(self):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "_Create" is deprecated use "_create" instead', stacklevel=2)
        return self._create()


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
        """ add a new testcase to the list"""
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

    @deprecated('append')
    def Append(self, testcase):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "Append" is deprecated use "append" instead', stacklevel=2)
        return self.append(testcase)

    @deprecated('_create')
    def _Create(self):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "_Create" is deprecated use "_create" instead', stacklevel=2)
        return self._create()


class TestStatistic(TableBase):
    """
    **Test Statistics table**

    contains total distance and total time as default rows,
    can get additional user defined rows with result, value and unit triples

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

    @deprecated('set_testrun')
    def SetTestrun(self, testrun):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "SetTestrun" is deprecated use "set_testrun" instead', stacklevel=2)
        return self.set_testrun(testrun)

    @deprecated('append')
    def Append(self, statistic_row):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "Append" is deprecated use "append" instead', stacklevel=2)
        return self.append(statistic_row)

    @deprecated('_create')
    def _Create(self):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "_Create" is deprecated use "_create" instead', stacklevel=2)
        return self._create()


class SummaryResults(TableBase):
    """
    **Summary TestStep Results Table**
    with "TestStep_ID", "Name" and combined "Result" for each test step

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    def __init__(self):
        TableBase.__init__(self)

        self._name = "Summary Teststep Results"
        self._teststeps = []
        self._failed = 0
        self._passed = 0
        self._notassessed = 0
        self.summary = True

    def append(self, testcase):
        """
        Append one Statistic Data Set to the Table.
        This Method can be called multiple Times, to append more Data Sets.

        :param testcase: 2-Dimensional Table with the Statistic Data
                                 inside. The first row is used as title.
        """

        for teststep in testcase.test_steps:
            if teststep.test_result.upper() == ValAssessmentStates.PASSED.upper():
                self._passed += 1
            elif teststep.test_result.upper() == ValAssessmentStates.FAILED.upper():
                self._failed += 1
            else:
                self._notassessed += 1
            self._teststeps.append(teststep)

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

        # Add the Header to the data
        data.append(build_table_header(["Teststep_ID", "Name", "Result"]))

        for teststep in self._teststeps:
            data.append(build_table_row([url_str(teststep.id, teststep.doors_url),
                                         html_str(teststep.name),
                                         color_result(teststep.test_result)]))

        story = []

        table = plat.Table(data, colWidths=[SUMMARY_ID_WIDTH, SUMMARY_NAME_WIDTH, SUMMARY_RESULT_WIDTH], style=style)

        story.append(table)
        self.append_caption(story)
        story.append(plat.Spacer(1, 1 * cm))

        if(self.summary):
            data2 = []
            # Add the Header to the data
            data2.append(build_table_header(["Test(s) Performed",
                                             color_result(ValAssessmentStates.PASSED.upper()),
                                             color_result(ValAssessmentStates.FAILED.upper()),
                                             color_result(ValAssessmentStates.NOT_ASSESSED.upper())]))
            data2.append([self._passed + self._failed + self._notassessed,
                          self._passed, self._failed, self._notassessed])

            table2 = plat.Table(data2, style=style)

            story.append(table2)
            story.append(plat.Spacer(1, 1 * cm))

        return story

    @deprecated('append')
    def Append(self, testcase):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "Append" is deprecated use "append" instead', stacklevel=2)
        return self.append(testcase)

    @deprecated('_create')
    def _Create(self):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "_Create" is deprecated use "_create" instead', stacklevel=2)
        return self._create()


class SummaryTestcases(TableBase):
    """
    **Summary Testcase Results Table**
    with "Testcase_ID", "Name" and combined "Result" for each test case

    calculate test case result by checking results of test steps (done in `ValTestcase`):
      - one FAILED test step results in FAILED
      - one not PASSED and not FAILED test step (e.g. investigate) results in NOT_ASSESSED
      - only if all test steps are PASSED result will be PASSED

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    def __init__(self):
        TableBase.__init__(self)

        self._name = "Summary Testcase Results"
        self._testcases = []
        self._failed = 0
        self._passed = 0
        self._notassessed = 0
        self.summary = True

    def append(self, testcase):
        """
        Append one Statistic Data Set to the Table.
        This Method can be called multiple Times, to append more Data Sets.

        :param testcase: 2-Dimensional Table with the Statistic Data inside.
                                 The first row is used as title.
        """

        if testcase.test_result.upper() == ValAssessmentStates.PASSED.upper():
            self._passed += 1
        elif testcase.test_result.upper() == ValAssessmentStates.FAILED.upper():
            self._failed += 1
        else:
            self._notassessed += 1

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
        style = [('GRID', (0, 0), (-1, -1), 1.0, colors.black),
                 ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)]

        data = []

        # Add the Header to the data
        data.append(build_table_header(["Testcase_ID", "Name", "Result"]))

        for testcase in self._testcases:
            data.append(build_table_row([url_str(testcase.id, testcase.doors_url),
                                         html_str(testcase.name),
                                         color_result(testcase.test_result)]))

        story = []

        table = plat.Table(data, colWidths=[SUMMARY_ID_WIDTH, SUMMARY_NAME_WIDTH, SUMMARY_RESULT_WIDTH], style=style)

        story.append(table)
        self.append_caption(story)
        story.append(plat.Spacer(1, 1 * cm))

        if self.summary:
            data2 = []
            # Add the Header to the data
            data2.append(build_table_header(["Test(s) Performed",
                                             color_result(ValAssessmentStates.PASSED.upper()),
                                             color_result(ValAssessmentStates.FAILED.upper()),
                                             color_result(ValAssessmentStates.NOT_ASSESSED.upper())]))
            data2.append([self._passed + self._failed + self._notassessed,
                          self._passed, self._failed, self._notassessed])

            table2 = plat.Table(data2, style=style)

            story.append(table2)
            story.append(plat.Spacer(1, 1 * cm))

        return story

    @deprecated('append')
    def Append(self, testcase):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "Append" is deprecated use "append" instead', stacklevel=2)
        return self.append(testcase)

    @deprecated('_create')
    def _Create(self):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "_Create" is deprecated use "_create" instead', stacklevel=2)
        return self._create()


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
        self.with_name = False
        self.with_asmt = False
        # print out cols:id    name   expt  meas  res   asmt
        self.cols_out = [True, False, True, True, True, False]

    def append(self, testcase):
        """
        Append one Statstic Data Set to the Table.
        This Method can be called multiple Times, to append more Data Sets.

        Method checks for some columns if it should be printed:
        if column is empty for all teststeps/testcases it is not printed in the table

        :param testcase: 2-Dimensional Table with the Statistik Data inside.
                                 The first row is used as title.
        """
        # check if name and id are identical, if not the column 'name' has to be printed
        if testcase.name and testcase.name != testcase.id:
            self.cols_out[1] = True
        else:
            for step in testcase.test_steps:
                if step.name and step.name != step.id:
                    self.cols_out[1] = True
                    break
        # check issue / ASMT field : if filled column ASMT has to be printed
        for step in testcase.test_steps:
            if step.issue:
                self.cols_out[5] = True

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
        style = [('GRID', (0, 0), (-1, -1), 1.0, colors.black),
                 ('BACKGROUND', (0, 0), (-1, 0), colors.darkgrey)]

        data = []

        # Add the Header to the dat
        rowcount = 0
        for testcase in self._testcases:
            # Add TestCase information
            style.append(('BACKGROUND', (0, rowcount), (-1, rowcount), colors.darkgrey))
            data.append(build_table_row([url_str(testcase.id, testcase.doors_url), html_str(testcase.name),
                                        '', '', color_result(testcase.test_result), ''],
                                        self.cols_out))
            rowcount += 1
            style.append(('BACKGROUND', (0, rowcount), (-1, rowcount), colors.lightgrey))
            data.append(build_table_row(filter_cols(['Teststep_ID', 'Name', 'Expected Result',
                                                     'Measured Result', 'Test Result', 'ASMT'],
                                                    self.cols_out)))
            rowcount += 1
            # Ad Teststeps information
            for step in testcase.test_steps:
                data.append(build_table_row([url_str(step.id, step.doors_url), html_str(step.name),
                                             html_str(step.exp_result), html_str(step.meas_result),
                                             color_result(step.test_result), html_str(step.issue)],
                                            self.cols_out))
                rowcount += 1

        story = []

        # adjust column widths based on widths of table with all columns
        cadd = ((sum(TEST_DETAILS_WIDTHS) - sum(filter_cols(TEST_DETAILS_WIDTHS, self.cols_out)))
                / len(filter_cols(TEST_DETAILS_WIDTHS, self.cols_out)))
        col_widths = filter_cols([i + cadd for i in TEST_DETAILS_WIDTHS], self.cols_out)

        table = plat.Table(data, style=style, colWidths=col_widths)
        story.append(table)
        self.append_caption(story)
        story.append(plat.Spacer(1, 1 * cm))

        return story

    @deprecated('append')
    def Append(self, testcase):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "Append" is deprecated use "append" instead', stacklevel=2)
        return self.append(testcase)

    @deprecated('_create')
    def _Create(self):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "_Create" is deprecated use "_create" instead', stacklevel=2)
        return self._create()


class Testcase(TableBase):
    """
    **Detailed Summary Result** result for single Testcase

    two sectioned table showing
      - test case information like id, playlist and distance
      - test step details with name, expected and measured result and assessment

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    def __init__(self, testcase):
        TableBase.__init__(self)

        self._name = "Detailed Summary Result - %s" % html_str(testcase.id)
        self._testcase = testcase

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

        data = []
        data.append(build_table_row(['Testcase Name', html_str(self._testcase.name)]))
        data.append(build_table_row(['Testcase Identifier', url_str(self._testcase.id, self._testcase.doors_url)]))
        data.append(build_table_row(['Playlist/Recording', html_str(self._testcase.collection)]))
        # data.append(['Files Processed', self._testcase.processed_files]) #Todo: rh
        data.append(['Time Processed [H:M:S]', sec_to_hms_string(self._testcase.total_time)])
        data.append(['Distance Processed [km]', str(self._testcase.total_dist)])

        table = plat.Table(data, style=style, colWidths=[TESTCASE1_DESCR_WIDTH, TESTCASE1_VALUE_WIDTH])
        story.append(table)

        style = [('GRID', (0, 0), (-1, -1), 1.0, colors.black),
                 ('BACKGROUND', (0, 0), (3, 0), colors.lightgrey)]

        data = [build_table_header(['Teststep', 'Expected Result', 'Measured Result', 'Test Result'])]

        for step in self._testcase.test_steps:
            data.append(build_table_row([url_str(step.id, step.doors_url),
                                         html_str(step.exp_result),
                                         html_str(step.meas_result),
                                         color_result(step.test_result)]))

        table = plat.Table(data, style=style, colWidths=[TESTCASE2_ID_WIDTH, TESTCASE2_MEAS_WIDTH,
                                                         TESTCASE2_MEAS_WIDTH, TESTCASE2_RESULT_WIDTH])
        story.append(table)
        self.append_caption(story)

        story.append(plat.Spacer(1, 1 * cm))

        return story

    @deprecated('_create')
    def _Create(self):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "_Create" is deprecated use "_create" instead', stacklevel=2)
        return self._create()


class RuntimeIncidentsTable(TableBase):
    """
    **Runtime incidents table**
    providing overview of jobs/tasks executed and number of incidents during each job

    creates table with one row for each job added with `append`, sum of all tasks and incidents in last row

    .. python::
        runtime_statistic = flowables.RuntimeIncidentsTable()
        for job_details in job_list:
            runtime_statistic.Append(job_details)
        local_story.Append(runtime_statistic)

    :author:        Joachim Hospes
    :date:          30.01.2014
    """
    def __init__(self):
        TableBase.__init__(self)

        self._name = "Runtime Incidents Statistic table"
        self._runtime_details = []

    def append(self, rt_details):
        """
        Append one job resulting in one row with incident counters to the table.
        This Method can be called multiple Times, to append more Data Sets.

        :param rt_details: details of one job as in `RuntimeIncident`
        :type rt_details:  `RuntimeIncident`
        """

        self._runtime_details.append(rt_details)

    def _create(self):
        """
        Does the final creation of the Platypus Table object.
        Including a correct nummeration for the Table of Tables list.

        Typically this Method will be called by the _PreBuild-Method of
        the Story class.

        :return: story with all final objects for pdf rendering
        :rtype: list of platypus objects ready for rendering.
        """
        story = []

        style = [('GRID', (0, 0), (-1, -1), 1.0, colors.black),
                 ('BACKGROUND', (0, 0), (-1, 0), colors.darkgrey)]

        data = [build_table_header(['Job_ID', 'Crashes', 'Exceptions', 'Errors'])]
        all_err = 0
        all_exc = 0
        all_crs = 0
        for job in self._runtime_details:
            data.append([job.jobid, job.crash_count, job.exception_count, job.error_count])
            all_err += job.error_count
            all_exc += job.exception_count
            all_crs += job.crash_count

        data.append(['sum', all_crs, all_exc, all_err])
        style.append(('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey))
        table = plat.Table(data, style=style)
        # create table number, caption and add to summaries:
        story.append(table)
        self.append_caption(story)
        story.append(plat.Spacer(1, 1 * cm))

        return story

    @deprecated('append')
    def Append(self, rt_details):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "Append" is deprecated use "append" instead', stacklevel=2)
        return self.append(rt_details)

    @deprecated('_create')
    def _Create(self):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "_Create" is deprecated use "_create" instead', stacklevel=2)
        return self._create()


class IncidentDetailsTables(TableBase):
    """
    **Job Runtime table** with all incidents encountered during one job, filtered for given incident type.

    Add a table with caption for one job and one incident type by

    .. python::

       ic_table = flow.IncidentDetailsTables(job, itype)
       local_story.Append(ic_table)

    :author:        Joachim Hospes
    :date:          30.01.2014
    """
    def __init__(self, job_details, itype):
        """
        initialise section with incident table for one job and one incident type

        :param job_details: details of the job as defined in `val.runtime.RuntimeIncident`
        :type job_details:  `RuntimeIncident`
        """
        TableBase.__init__(self)

        self._name = "Job %s Runtime %s table" % (job_details.jobid, itype)
        self._job = job_details
        self._type = itype

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
                 ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)]

        data = [build_table_header(['TaskId', 'Error Code', 'Description', 'Details'])]

        for inct in sorted(self._job.incidents, key=attrgetter('task_id')):
            if inct.type == self._type:
                data.append(build_table_row([inct.task_id, inct.code, html_str(inct.desc), html_str(inct.src)]))

        table = plat.Table(data, style=style,
                           colWidths=[INCDNT_TASK_WIDTH, INCDNT_ERROR_WIDTH, INCDNT_DESC_WIDTH, INCDNT_SOURCE_WIDTH])
        story.append(table)
        self.append_caption(story)

        story.append(plat.Spacer(1, 1 * cm))

        return story

    @deprecated('_create')
    def _Create(self):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "_Create" is deprecated use "_create" instead', stacklevel=2)
        return self._create()


"""
CHANGE LOG:
-----------
$Log: flowables.py  $
Revision 1.7 2016/12/05 14:39:06CET Hospes, Gerd-Joachim (uidv8815) 
break text for collections in table field
Revision 1.6 2016/12/01 11:22:28CET Hospes, Gerd-Joachim (uidv8815)
fix docu errors
Revision 1.5 2016/11/17 11:20:22CET Hospes, Gerd-Joachim (uidv8815)
move table formatter methods to pdf.base to support line break for columns in base.flowable.Table
Revision 1.4 2016/07/22 15:54:02CEST Hospes, Gerd-Joachim (uidv8815)
new fields sim version and val sw version
Revision 1.3 2016/05/09 11:00:18CEST Hospes, Gerd-Joachim (uidv8815)
add new column REMARKS to val.db and to pfd reports as new overview table row
Revision 1.2 2015/10/29 17:46:25CET Hospes, Gerd-Joachim (uidv8815)
add collection and sim_name to reports
- Added comments -  uidv8815 [Oct 29, 2015 5:46:26 PM CET]
Change Package : 390799:1 http://mks-psad:7002/im/viewissue?selection=390799
Revision 1.1 2015/04/23 19:05:20CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/rep/pdf/perf_test/project.pj
Revision 1.6 2015/01/26 20:20:16CET Ellero, Stefano (uidw8660)
Removed all rep based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 26, 2015 8:20:17 PM CET]
Change Package : 296836:1 http://mks-psad:7002/im/viewissue?selection=296836
Revision 1.5 2015/01/19 17:10:49CET Mertens, Sven (uidv7805)
removing deprecated calls
--- Added comments ---  uidv7805 [Jan 19, 2015 5:10:49 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.4 2014/06/25 10:31:32CEST Hospes, Gerd-Joachim (uidv8815)
fix pylint warnings
--- Added comments ---  uidv8815 [Jun 25, 2014 10:31:32 AM CEST]
Change Package : 243858:1 http://mks-psad:7002/im/viewissue?selection=243858
Revision 1.3 2014/06/24 17:01:26CEST Hospes, Gerd-Joachim (uidv8815)
move table caption below table, extend some epydoc
--- Added comments ---  uidv8815 [Jun 24, 2014 5:01:26 PM CEST]
Change Package : 243858:1 http://mks-psad:7002/im/viewissue?selection=243858
Revision 1.2 2014/06/22 23:07:24CEST Hospes, Gerd-Joachim (uidv8815)
sync between templates and flowables,
algo_test.report generates perf, func and regr tests
algo_test template and flowable moved to perf_test
--- Added comments ---  uidv8815 [Jun 22, 2014 11:07:25 PM CEST]
Change Package : 241732:1 http://mks-psad:7002/im/viewissue?selection=241732
Revision 1.1 2014/06/18 15:23:48CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision, moved from stk/pdf/algo_test
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/rep/pdf/perf_test/project.pj
Revision 1.32 2014/06/17 16:21:08CEST Hospes, Gerd-Joachim (uidv8815)
print columns name and asmt only if filled in one test
--- Added comments ---  uidv8815 [Jun 17, 2014 4:21:09 PM CEST]
Change Package : 242882:1 http://mks-psad:7002/im/viewissue?selection=242882
Revision 1.31 2014/05/26 13:00:29CEST Hecker, Robert (heckerr)
Some BugFix to get test running again.
--- Added comments ---  heckerr [May 26, 2014 1:00:30 PM CEST]
Change Package : 239296:1 http://mks-psad:7002/im/viewissue?selection=239296
Revision 1.30 2014/05/20 13:18:29CEST Hospes, Gerd-Joachim (uidv8815)
add user_account to report, based on testrun or ifc definition, update test_report
--- Added comments ---  uidv8815 [May 20, 2014 1:18:30 PM CEST]
Change Package : 233145:1 http://mks-psad:7002/im/viewissue?selection=233145
Revision 1.29 2014/05/06 14:08:00CEST Hospes, Gerd-Joachim (uidv8815)
fix spelling errors
Revision 1.28 2014/04/25 13:45:23CEST Hospes, Gerd-Joachim (uidv8815)
add html link to doors url on test case/step id in all tables if url available
--- Added comments ---  uidv8815 [Apr 25, 2014 1:45:24 PM CEST]
Change Package : 227491:1 http://mks-psad:7002/im/viewissue?selection=227491
Revision 1.27 2014/04/09 13:00:15CEST Hospes, Gerd-Joachim (uidv8815)
order of incidents changed to Crash - Exception - Error
--- Added comments ---  uidv8815 [Apr 9, 2014 1:00:15 PM CEST]
Change Package : 230169:1 http://mks-psad:7002/im/viewissue?selection=230169
Revision 1.26 2014/04/09 09:49:53CEST Hospes, Gerd-Joachim (uidv8815)
minor style fixes, prep details table for reg test report
--- Added comments ---  uidv8815 [Apr 9, 2014 9:49:53 AM CEST]
Change Package : 227496:1 http://mks-psad:7002/im/viewissue?selection=227496
Revision 1.25 2014/04/07 14:10:01CEST Hospes, Gerd-Joachim (uidv8815)
pep8 & pylint fixes after adding new packages and splitting some modules
--- Added comments ---  uidv8815 [Apr 7, 2014 2:10:01 PM CEST]
Change Package : 227496:1 http://mks-psad:7002/im/viewissue?selection=227496
Revision 1.24 2014/04/04 17:39:52CEST Hospes, Gerd-Joachim (uidv8815)
removed algo_base commen classes and functions
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
