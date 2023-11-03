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
:author:        Leidenberger, Ralf

:version:       $Revision: 1.1 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/25 21:28:54CET $
"""
# Import Python Modules --------------------------------------------------------
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import reportlab.platypus as plat
from reportlab.lib import colors
from reportlab.lib.units import cm
from operator import attrgetter

# Import STK Modules -----------------------------------------------------------
from ..base.flowables import TableBase, html_str, url_str, filter_cols, \
    build_table_row, build_table_header, NORMAL_STYLE
from ..algo_base.flowables import color_result
from ....val.asmt import ValAssessmentStates
from ....util.helper import sec_to_hms_string

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
TEST_DETAILS_WIDTHS = [TEST_ID_WIDTH, TEST_NAME_WIDTH, TEST_MEAS_WIDTH, TEST_MEAS_WIDTH,
                       TEST_RESULT_WIDTH, TEST_FR_NUM_WIDTH]

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


# Classes ----------------------------------------------------------------------
# these table classes normally provide only a create method,
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

    def create(self):
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
                build_table_row(["User Account", str(self.user_account)])]

        story = []

        table = plat.Table(data, colWidths=[OVERVIEW_DESCR_WIDTH, OVERVIEW_VALUE_WIDTH], style=self._style)

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
        """ add a new testcase to the list"""
        self._testcases.append(testcase)

    def create(self):
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

    def create(self):
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

    def create(self):
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

        # Add the Header to the data
        data = [build_table_header(["Teststep_ID", "Name", "Result"])]

        for teststep in self._teststeps:
            data.append(build_table_row([url_str(teststep.id, teststep.doors_url),
                                         html_str(teststep.name),
                                         color_result(teststep.test_result)]))

        story = []

        table = plat.Table(data, colWidths=[SUMMARY_ID_WIDTH, SUMMARY_NAME_WIDTH, SUMMARY_RESULT_WIDTH], style=style)

        story.append(table)
        self.append_caption(story)
        story.append(plat.Spacer(1, 1 * cm))

        if self.summary:
            # Add the Header to the data
            data2 = [build_table_header(["Test(s) Performed", color_result(ValAssessmentStates.PASSED.upper()),
                                         color_result(ValAssessmentStates.FAILED.upper()),
                                         color_result(ValAssessmentStates.NOT_ASSESSED.upper())]),
                     [self._passed + self._failed + self._notassessed, self._passed, self._failed, self._notassessed]]

            table2 = plat.Table(data2, style=style)

            story.append(table2)
            story.append(plat.Spacer(1, 1 * cm))

        return story


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

    def create(self):
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

        # Add the Header to the data
        data = [build_table_header(["Testcase_ID", "Name", "Result"])]

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
            # Add the Header to the data
            data2 = [build_table_header(["Test(s) Performed", color_result(ValAssessmentStates.PASSED.upper()),
                                         color_result(ValAssessmentStates.FAILED.upper()),
                                         color_result(ValAssessmentStates.NOT_ASSESSED.upper())]),
                     [self._passed + self._failed + self._notassessed, self._passed, self._failed, self._notassessed]]

            table2 = plat.Table(data2, style=style)

            story.append(table2)
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

    def create(self):
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
        cadd = ((sum(TEST_DETAILS_WIDTHS) - sum(filter_cols(TEST_DETAILS_WIDTHS, self.cols_out))) /
                len(filter_cols(TEST_DETAILS_WIDTHS, self.cols_out)))
        col_widths = filter_cols([i + cadd for i in TEST_DETAILS_WIDTHS], self.cols_out)

        table = plat.Table(data, style=style, colWidths=col_widths)
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
    def __init__(self, testcase):
        TableBase.__init__(self)

        self._name = "Detailed Summary Result - %s" % html_str(testcase.id)
        self._testcase = testcase

    def create(self):
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
                build_table_row(['Testcase Identifier', url_str(self._testcase.id, self._testcase.doors_url)]),
                build_table_row(['Playlist/Recording', html_str(self._testcase.collection)]),
                ['Time Processed [H:M:S]', sec_to_hms_string(self._testcase.total_time)],
                ['Distance Processed [km]', str(self._testcase.total_dist)]]

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


class RuntimeIncidentsTable(TableBase):
    """
    **Runtime incidents table**
    providing overview of jobs/tasks executed and number of incidents during each job

    creates table with one row for each job added with `append`, sum of all tasks and incidents in last row

    .. code-block:: python

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

    def create(self):
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


class IncidentDetailsTables(TableBase):
    """
    **Job Runtime table** with all incidents encountered during one job, filtered for given incident type.

    Add a table with caption for one job and one incident type by

    .. code-block:: python

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

    def create(self):
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


"""
$Log: flowables.py  $
Revision 1.1 2020/03/25 21:28:54CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/rep/pdf/perf_test/project.pj
"""
