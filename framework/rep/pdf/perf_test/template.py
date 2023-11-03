"""
stk/rep/pdf/algo_test/template
------------------------------

**Template/Layout module of AlgoTestReport**

**Internal-API Interfaces**

    - `TestDetails`
    - `RuntimeDetails`
    - `OverviewTemplate`

**User-API Interfaces**

    - `stk.rep` (complete package)

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.1 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/25 21:28:55CET $
"""
# Import Python Modules --------------------------------------------------------
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import reportlab.platypus as plat
# needed when deprecation warnings are activated:
# import warnings

# Import STK Modules -----------------------------------------------------------
from ..base import template as temp
from ..base import pdf
from . import flowables as flow
from framework.val import Histogram
from framework.img.plot import ValidationPlot


pdfmetrics.registerFont(TTFont('Calibri', 'Calibri.ttf'))
# Defines ----------------------------------------------------------------------
REP_MANAGEMENT = 1
REP_DETAILED = 2
REP_DEVELOPER = 4

# Functions --------------------------------------------------------------------

# Classes ----------------------------------------------------------------------


class TestDetails(object):  # pylint: disable=R0903
    """
    template for chapter 2. Test Details

    printing

      - 'Overview' with table of all TestCases and TestSteps
      - chapters 'Testcase' for each TestCase with

        - TestCase description (if available) and
        - table with TestCase details and executed TestSteps
        - histograms and Graphs (if available)
    """
    def __init__(self, mem_reduction=False):
        """
        preset class internal variables

        :param mem_reduction: If True, PNG images are converted to JPEG format before passing them to the
                              reportlab.platypus.flowables.Image class.
                              Also, the lazy=2 argument is used to open the image when required then shut it.
                              If False, no image conversion is done and the lazy=1 argument is used when calling
                              reportlab.platypus.flowables.Image to not open the image until required.
        :type mem_reduction:  boolean, optional, default: False
        """
        self.summary_results = flow.DetailedSummary()  # pylint: disable=C0103

        self._testcases = []

        self._mem_reduction = mem_reduction

    def append(self, testcase):
        """
        add a TestCase to the overview table and a chapter with description,
        table and graphs

        :param testcase: TestCase to add
        :type testcase:  `TestCase`
        """
        self._testcases.append(testcase)

    def create(self, story, level=REP_DEVELOPER):  # pylint: disable=W0613
        """
        creates the pdf story, called during `report.Build`

        :param story: pdf story to add paragraphs to
        :type story:  list of `pdf.Story` elements
        :param level:
        """
        local_story = pdf.Story(temp.Style(), self._mem_reduction)

        local_story.add_heading("Test Details", 0)

        if len(self._testcases):
            if level is REP_MANAGEMENT:
                local_story.add_heading("Overview", 1)
                local_story.add_space(1)

                local_story.append(self.summary_results)
                local_story.add_space(1)
            else:
                for testcase in self._testcases:
                    local_story.add_heading('Testcase ' + testcase.name, 1)
                    local_story.add_space(1)
                    local_story.add_paragraph(str(testcase.description))
                    local_story.add_space(1)
                    # Create Table and add Table to Report
                    tc_table = flow.Testcase(testcase)
                    local_story.append(tc_table)
                    # plot graphics stored as TestCaseResult
                    for plot in testcase.summery_plots:
                        if type(plot.meas_result) is Histogram:
                            drawing, _ = plot.meas_result.plot_histogram()
                            local_story.add_image(plot.name, drawing)
                        if type(plot.meas_result) is ValidationPlot:
                            drawing = plot.meas_result.get_drawing()
                            local_story.add_image(plot.name, drawing)
        else:
            local_story.add_paragraph("No Testcases Specified")

        story += local_story.story


class RuntimeDetails(object):  # pylint: disable=R0903
    """
    adds chapter Test Execution Details with Overview and tables for all entered incident types
    to the global pdf story list
    """
    def __init__(self, mem_reduction=False):
        """
        preset class internal variables

        :param mem_reduction: If True, PNG images are converted to JPEG format before passing them to the
                              reportlab.platypus.flowables.Image class.
                              Also, the lazy=2 argument is used to open the image when required then shut it.
                              If False, no image conversion is done and the lazy=1 argument is used when calling
                              reportlab.platypus.flowables.Image to not open the image until required.
        :type mem_reduction:  boolean, optional, default: False
        """
        self.runtime_statistic = flow.RuntimeIncidentsTable()

        self._jobs = []
        # get all different issue types and add to job instance
        self._itype_list = ['Crash', 'Exception', 'Error']
        self._mem_reduction = mem_reduction

    def append(self, job_details):
        """ for each job (row in table) this methods prepares the content

        :param job_details: details of the job
        :type job_details:  `RuntimeJob`
        """
        self._jobs.append(job_details)
        self.runtime_statistic.append(job_details)

    def create(self, story):  # pylint: disable=W0613
        """
        creates the pdf story, called during `report.Build`

        :param story: pdf story to add paragraphs to
        :type story:  list of `pdf.Story` elements
        """
        local_story = pdf.Story(temp.Style(), self._mem_reduction)
        local_story.append(plat.PageBreak())

        local_story.add_heading("Test Execution Statistic", 0)
        local_story.add_heading("Overview", 1)
        local_story.add_space(1)

        local_story.append(self.runtime_statistic)
        local_story.add_space(1)

        for job in self._jobs:
            local_story.add_heading('Runtime Issues job ' + str(job.jobid), 1)
            local_story.add_space(1)
            job_itypes = set(x.type for x in job.incidents)
            # get all different issue types and add to job instance
            for itype in self._itype_list:
                local_story.add_heading('%s list of job %s' % (itype, str(job.jobid)), 2)
                local_story.add_space(1)
                if itype in job_itypes:
                    local_story.add_paragraph('Issues of type "%s" raised during execution of job %s:'
                                              % (itype, str(job.jobid)))
                    local_story.add_space(1)
                    # Create Table and add Table to Report
                    ic_table = flow.IncidentDetailsTables(job, itype)
                    local_story.append(ic_table)
                else:
                    local_story.add_paragraph('No issues of type "%s" reported.' % itype)
                    local_story.add_space(1)

        story += local_story.story


class OverviewTemplate(object):  # pylint: disable=R0903
    """
    template for chapter 1. Test Overview

    printing

      - Testrun names and details
      - Testcases of this Testrun
      - Statistics table with processed distance, time, files
      - TestResults of TestCases
      - TestResults of TestSteps
    """
    def __init__(self, mem_reduction=False):
        """
        preset class internal variables

        :param mem_reduction: If True, PNG images are converted to JPEG format before passing them to the
                              reportlab.platypus.flowables.Image class.
                              Also, the lazy=2 argument is used to open the image when required then shut it.
                              If False, no image conversion is done and the lazy=1 argument is used when calling
                              reportlab.platypus.flowables.Image to not open the image until required.
        :type mem_reduction:  boolean, optional, default: False
        """
        # pylint: disable=C0103
        self.overview_table = flow.Overview()
        self._mem_reduction = mem_reduction
        self.testrun_overview_details = pdf.Story(temp.Style(), self._mem_reduction)
        self.test_description = flow.TestDescription()
        self.statistic_table = flow.TestStatistic()
        self.summary_results_table = flow.SummaryResults()
        self.summary_testcases_table = flow.SummaryTestcases()

    def create(self, story):  # pylint: disable=W0613
        """
        creates the pdf story, called during `report.Build`

        :param story: pdf story to add paragraphs to
        :type story:  list of `pdf.Story` elements
        """
        local_story = pdf.Story(temp.Style(), self._mem_reduction)

        local_story.add_heading("Test Overview", 0)
        local_story.add_heading("Testrun Overview", 1)
        local_story.add_space(1)

        local_story.append(self.overview_table)
        local_story.add_space(0.5)
        for st_el in self.testrun_overview_details.story:
            local_story.append(st_el)

        local_story.add_heading("Testcases", 1)
        local_story.add_space(1)
        local_story.append(self.test_description)

        local_story.add_heading("Test Statistics", 1)
        local_story.add_space(1)

        local_story.append(self.statistic_table)

        local_story.add_heading("Summary Results of Testcases", 1)
        local_story.append(self.summary_testcases_table)

        local_story.add_heading("Summary Results of Teststeps", 1)
        local_story.append(self.summary_results_table)

        local_story.add_page_break()

        story += local_story.story


"""
CHANGE LOG:
-----------
$Log: template.py  $
Revision 1.1 2020/03/25 21:28:55CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/rep/pdf/perf_test/project.pj
"""
