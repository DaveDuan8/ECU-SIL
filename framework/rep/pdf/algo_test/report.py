"""
framework/rep/pdf/algo_test/report
----------------------------

**AlgoTestReport Module**

**User-API Interfaces**

    - `AlgoTestReport` (this module)
    - `framework.rep` (complete package)

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 09:20:05CEST $
"""
# Import Python Modules --------------------------------------------------------
# needed if deprecated warnings are activated:
# import warnings

# Import framework Modules -----------------------------------------------------------
from ..base import pdf
from ..base import template as temp
from ..algo_base import template as algotemp
from ..algo_base import flowables as algoflow
from ..perf_test import template as perftemp
from ..reg_test import template as regtemp

# Defines ----------------------------------------------------------------------
PAGE_TEMPLATE_PORTRAIT = algotemp.PAGE_TEMPLATE_PORTRAIT
PAGE_TEMPLATE_LANDSCAPE = algotemp.PAGE_TEMPLATE_LANDSCAPE

# Functions --------------------------------------------------------------------

# Classes ----------------------------------------------------------------------


class AlgoTestReport(pdf.Story):  # pylint: disable=R0902
    """
    **The AlgoTestReport class creates a Standard Report for the Algo-Validation
    for different Test-Types.**

    Class AlgoTestReport can be used in own scripts to create a report directly after a validation run
    or to add special Development Details (see code example below),
    or it can created any time after the validation run using the command line tool `framework.cmd.gen_report`.

    Based on the test_type in TestRun [1]_ it diverts to the special test report.
    The default type is "performance" test.

    **common options for all types**
        following options are available in all report types:

            - **chapter 1.1 Testrun Overview**: additional details can be added below the overview table.
              The attribute `testrun_overview_details` can be filled with pdf `Story` items
              like heading, paragraph, figure, table and other formatting elements.

            - section **'Development details'**: an additional chapter can be filled
              to give further information and details using an own script for report creation.
              The attribute `developer` can be filled with pdf `Story` items
              like heading, paragraph, figure, table and other formatting elements.
              The section 'Developer details' is only created if there are story items added,
              otherwise it is left out.

    **performance test report**
        A performance test report contains:

            1. section **'Test Overview'** with basic test run data, lists of test cases
            and test steps with their results (PASSED/FAILED) and a statistic table printing the
            overall processed distance, time and number of recordings for the complete test run.

            2. section **'Test Details'** with subsections for each test case listing the test steps and their
            expected and measured results, the test result (PASSED/FAILED) and additional data.
            It can also contain drawings to be printed below the test case table if these are stored
            with the TestCase object.

            3. section **'Runtime Execution Statistic'**: If an HPC jobId is set for the TestRun [1]_
            the report lists all issues claimed by HPC during that job.
            This section is only printed if a jobId is set, otherwise it is left out.

            4. section **'Development details'**: an additional chapter can be filled
            to give further information and details using an own script for report creation.
            The attribute `developer` can be filled with pdf `Story` items like heading, paragraph, figure, table
            and other formatting elements.

        Performance test reports allow to define a granularity:
            `REP_MANAGEMENT`
                Generate chapter 'Test Overview',
                chapter 'Test Details' listing all test cases and test steps in one table,
                and chapter 'Development Details'
            `REP_DETAILED`
                As before, but chapter 'Test Details' printing subsections for each test case,
                and optional chapter 'Runtime Execution Statistic'.

        The granularity is set when calling the `build` method, default value is ``REP_DETAILED``:

        .. code-block:: python

            report.build('filename', level=REP_DETAILED)

        **example pdf**

        There are examples created by our module test:

         - Performance test report with granularity REP_MANAGEMENT at PerfTestManagementRep.pdf_
         - Performance test report with granularity REP_DETAILED at PerfTestReport.pdf_

        **selecting**

        Performance test reports are default (`test_type` empty), and automatically selected
        if the TestRun [1]_ attribute `test_type` is set to 'performance':

        .. code-block:: python

            # Create a Testrun Object for performance type report
            testrun = val.testrun.TestRun(..., type="Performance")

    **functional test report**
        A functional test report currently contains:

            1. section **'Test Overview'** with basic test run data, lists of test cases
            and test steps with their results (PASSED/FAILED) but no statistic table.

            2. section **'Development details'**: an additional chapter can be filled
            to give further information and details using an own script for report creation.
            The attribute `developer` can be filled with pdf story items like heading, paragraph, figure, table
            and other formatting elements.

        **example pdf**

        There is an example created by our module test at FctTestReport.pdf_

        **selecting**

        A functional test report is generated
        if the TestRun [1]_ attribute `test_type` is set to 'functional'.

        .. code-block:: python

            # Create a Testrun Object for functional report
            testrun = val.testrun.TestRun(..., type="Functional")

    **regression test report**
        A regression test report allows to compare the test results of the main test with a given reference.

        For this report no test details of the test cases are printed (section 2.x),
        just the overview tables with the test results.
        It is possible to add a developer section to give more details about this comparison results.

        To get a regression test report the AlgoTestReport has to be initialised with two testrun Ids,
        one for a test and another for a reference, or call the method `set_reference()` to set the testrun Id
        of the reference testrun. The reference testrun Id has to be set before any testcase is added
        to the main test.

        **example pdf**

        There is an example created by our module test at RegTestReport.pdf_

        **selecting**

        To generate a regression test report initialise the report giving a testrun and reference value:

        .. code-block:: python

            report = AlgoTestReport(testrun1_id, reference=testrun2_id)

    .. [1] TestRun is basically defined in `framework.val.testrun.TestRun`,
           to get reports independent there is the interface class `framework.rep.ifc.TestRun`


    **Example:**

    .. code-block:: python

        import framework.rep as rep

        # Create a Testrun Object
        testrun = val.testrun.TestRun(name="SampleTestrunName",  checkpoint="AL_ARS4xx_00.00.00_INT-1",
                                      proj_name="ARS400", obs_name="S_Test", test_collection="ARS4xx_sample_col",
                                      type="Performance")

        # Fill in Data into the TestRun or load from valDb
        ...

        # Create an instance of the reporter class for the TestRun
        report = rep.AlgoTestReport(testrun)

        # Add details to 1.1 Testrun Overview
        report.testrun_overview_details.add_paragraph("These details can be added using the report attribute "
                                                      "'testrun_overview_details'. The usage is similar to "
                                                      "adding details to the chapter 'Development details'.")
        # Add Statistics  to the Statistic Table
        report.statistic_table.append(["my result", "12.34", "Meter"])

        # Fill project specific chapter "Development details"
        report.developer.add_paragraph("This is the developer chapter where testers can add text, tables and figures."
                                       " See below some possibilities that are used in framework"
                                       " test_rep.test_pdf.test_algo_test.test_report.py just to give some example.")
        report.developer.add_space(0.5)
        report.developer.add_table('table with RotatedText in header',
                                  [['result 1', '13', '14', '15'], ['result 2', '31', '41', '51']],
                                  header=['result', RotatedText('column 1'), RotatedText('column 2'), 42],
                                  colWidths=[200, 20, 20, 50])

        # Save the Report to Disk
        report.build("AlgoTestReport.pdf")
    """
    REP_MANAGEMENT = 1
    """
    Render only the chapters 'Test Overview' and 'Test Details' with the 'Detailed Summary Result table'
    inside the Report.
    If JobIds of an HPC job are stored in the `TestRun` the chapter 'Runtime Execution Statistic' will be added.
    """
    REP_DETAILED = 2
    """
    Render additional to `REP_MANAGEMENT` subsections for each test case in the 'Test Details' chapter
    into the Report.
    If the developer attribute is filled with additional `Story` items a chapter 'Development details'
    will be added to the report.
    """
    REP_DEVELOPER = 4
    """
    Granularity level not used currently.
    """

    def __init__(self, testrun=None, reference=None, mem_reduction=False, custom_page_header_text=None):
        """
        preset class internal variables

        some sections are only available for special test type and set to None.
        These attributes have to be checked each usage to prevent errors.

        :param testrun:  opt. set testrun directly during initialisation or call set_test_run() later
        :type testrun:  `ITestRun`
        :param reference: opt. set reference testrun id to create reference test report comparing two test runs
        :type reference: integer
        :param mem_reduction: If True, PNG images are converted to JPEG format before passing them to the
                              reportlab.platypus.flowables.Image class.
                              Also, the lazy=2 argument is used to open the image when required then shut it.
                              If False, no image conversion is done and the lazy=1 argument is used when calling
                              reportlab.platypus.flowables.Image to not open the image until required.
        :type mem_reduction:  boolean, optional, default: False
        :param custom_page_header_text: text displayed on the page header of the document;
                                        if not specified, the default page header text will be used
                                        (defined in DEFAULT_PAGE_HEADER_TEXT).
        :type custom_page_header_text:  string, optional, default: None
        """
        self.style = temp.Style()
        self._mem_reduction = mem_reduction
        self._custom_page_header_text = custom_page_header_text
        pdf.Story.__init__(self, self.style, self._mem_reduction)
        self._doc = None

        self._title_page = algotemp.TitlePageTemplate(algotemp.AlgoTestDocTemplate(self.style, "",
                                                                                   self._custom_page_header_text))
        self._status = 'final'

        self.__developer = algotemp.DeveloperTemplate(mem_reduction=self._mem_reduction)
        # following attributes might change after test run type is known (in set_test_run)

        self._test_details = None
        self._runtime_details = None
        self.__statistic_table = None
        if reference:
            self._overview = regtemp.OverviewTemplate()
            self.__statistic_table = self._overview.statistic_table
            self._test_details = regtemp.TestDetails(self._mem_reduction)
        else:
            # minimum needed, might be overwritten later
            self._overview = perftemp.OverviewTemplate(mem_reduction=self._mem_reduction)

        if testrun:
            self.set_test_run(testrun)
        if reference:
            self.__set_reference(reference)

    @property
    def testrun_overview_details(self):
        """ story elements for additional info below the table in chapter "Test Overview" """
        return self._overview.testrun_overview_details

    @property
    def developer(self):
        """ developer story of the report, empty chapter that can be filled with project specific information """
        return self.__developer

    @property
    def statistic_table(self):
        """
        access to statistic table listing processed time, distance and files,
        allows to append project specific lines of the TestRun
        """
        return self.__statistic_table

    @staticmethod
    def __create_table_of_content(story):  # pylint: disable=W0613
        # W0613: argument 'story' is used, but pylint does not find it
        """
        Append the Table Of Contents to the story.

        :param story: Pdf-story
        :type story:  list of platypus flowables
        :return:      -
        """
        toc = algoflow.TableOfContents()
        # protected member 'create' inherited from platypus
        story += toc.create()  # pylint: disable=W0212

    @staticmethod
    def __create_table_of_figures(story):  # pylint: disable=W0613
        # W0613: argument 'story' is used, but pylint does not find it
        """
        Append the Table Of Figures to the story.

        :param story: Pdf-story
        :type story:  list of platypus flowables
        :return:      -
        """
        tof = algoflow.TableOfFigures()
        # protected member 'create' inherited from platypus
        story += tof.create()  # pylint: disable=W0212

    @staticmethod
    def __create_table_of_tables(story):  # pylint: disable=W0613
        # W0613: argument 'story' is used, but pylint does not find it
        """
        Append the Table Of Tables to the story.

        :param story: Pdf-story
        :type story: list of platypus flowables
        :return:      -
        """
        tot = algoflow.TableOfTables()
        # protected member 'create' inherited from platypus
        story += tot.create()  # pylint: disable=W0212

    def set_test_run(self, testrun):
        """
        Specify a Component TestRun which is used to Build a Report.

        This method is used to create a TestReport on component Level
        with all the standardised output based on the type (performance, functional) of the test run.

        By setting the test run also the templates and table formats are selected.
        This includes that some sections might be available only in special types of reports: for example the
        statistical table providing processed distance and time does not make sense for functional tests
        and is therefore left out.

        The Developer Part of the Report is untouched by this.

        :param testrun: Complete TestRun for one Component.
        :type testrun:  `ITestRun`
        """
        if type(self._overview) is not regtemp.OverviewTemplate:
            # if testrun.test_type is 'functional':
            #     self._overview = fcttemp.OverviewTemplate()
            # else:
            self._overview = perftemp.OverviewTemplate(mem_reduction=self._mem_reduction)

            self._test_details = perftemp.TestDetails()
            self._runtime_details = perftemp.RuntimeDetails()
            self.__statistic_table = self._overview.statistic_table

        # Set Tile in Title Page
        self._title_page.title = testrun.name

        # Set Title in Overview Table
        self._overview.overview_table.title = testrun.name

        # Set Checkpoint
        self._title_page.checkpoint = testrun.checkpoint
        self._title_page.add_info = testrun.add_info
        self._overview.overview_table.test_checkpoint = testrun.checkpoint

        # Set status depending on lock status of testrun in db:
        if testrun.locked is False:
            self._status = "draft"
        else:
            self._status = "final"

        # Set Description
        self._overview.overview_table.description = testrun.description

        # Set Project
        self._overview.overview_table.project = testrun.project

        # Set Component Name
        self._overview.overview_table.component = testrun.component

        # Set User account who executed the testrun
        self._overview.overview_table.user_account = testrun.user_account

        # set valDb internal testrun id
        self._overview.overview_table.tr_id = testrun.id

        # set collection and simulation details rows
        self._overview.overview_table.collection = testrun.collection
        self._overview.overview_table.sim_name = testrun.sim_name
        self._overview.overview_table.sim_version = testrun.sim_version

        # set validation sw version
        self._overview.overview_table.val_sw_version = testrun.val_sw_version

        # set testers comment row
        self._overview.overview_table.remarks = testrun.remarks

        # prep Statistics table
        if self.__statistic_table:
            self.__statistic_table.set_testrun(testrun)
        self._overview.statistic_table.set_testrun(testrun)

        for testcase in sorted(testrun.test_cases, key=lambda i: i.id):
            self.__add_testcase(testcase)

        if self._runtime_details:
            for job in testrun.runtime_details:
                self._runtime_details.append(job)

    def __add_testcase(self, testcase):
        """
        Add a complete Testcase to the Report.
        This method can be called multiple times to add multiple Testcases to the Report.

        :param testcase: Complete Testcase Object including all depending Teststeps
        :type testcase:  Object of Type TestCase
        """
        # first sort the teststeps of the testcase reg. the id
        testcase.test_steps.sort(key=lambda i: i.id)
        # Get the Testcase Description out of the Testcase and feed them into Overview
        self._overview.test_description.append(testcase)

        # Create a entry for the Summary Result
        self._overview.summary_testcases_table.append(testcase)
        self._overview.summary_results_table.append(testcase)

        # Create a Entry for the Detailed Summary Results Table
        if self._test_details:
            self._test_details.summary_results.append(testcase)
            self._test_details.append(testcase)

    def __set_reference(self, testrun):
        """
        internal method: Specify a Reference TestRun which is compared to the main TestRun.

        :param testrun: Complete TestRun for one Component.
        :type testrun:  `ITestRun`
        """
        # Check Tile
        if self._overview.overview_table.title != testrun.name:
            self._overview.overview_table.title += ' <font color=red>(' + testrun.name + ')</font>'

        # Set Checkpoint
        self._overview.overview_table.ref_checkpoint = testrun.checkpoint

        # Check Description
        if self._overview.overview_table.description != testrun.description:
            self._overview.overview_table.description += ' <font color=red>(' + \
                                                         testrun.description + ')</font>'

        # Set Project
        if self._overview.overview_table.project != testrun.project:
            self._overview.overview_table.project += ' <font color=red>(' + testrun.project + ')</font>'

        # set Component
        if self._overview.overview_table.component != testrun.component:
            self._overview.overview_table.component += ' <font color=red>(' + testrun.component + ')</font>'

        # set collection and simulation rows
        if self._overview.overview_table.collection != testrun.collection:
            self._overview.overview_table.collection += ' <font color=red>(' + testrun.collection + ')</font>'
        if self._overview.overview_table.sim_name != testrun.sim_name:
            self._overview.overview_table.sim_name += ' <font color=red>(' + testrun.sim_name + ')</font>'
        if self._overview.overview_table.sim_version != testrun.sim_version:
            self._overview.overview_table.sim_version += ' <font color=red>(' + testrun.sim_version + ')</font>'

        # set validation sw version
        if self._overview.overview_table.val_sw_version != testrun.val_sw_version:
            self._overview.overview_table.val_sw_version += ' <font color=red>(' + testrun.val_sw_version + ')</font>'

        # Set User account who did executed the reference
        self._overview.overview_table.ref_user_account = testrun.user_account

        # Set test_spec
        self._overview.overview_table.ref_id = testrun.id

        # Set testers comment for the table
        if self._overview.overview_table.remarks != testrun.remarks:
            self._overview.overview_table.remarks += ' <font color=red>(' + testrun.remarks + ')</font>'

        # prep Statistics table
        self.statistic_table.set_testrun(testrun)

        for testcase in testrun.test_cases:
            self.__add_refcase(testcase)

    def __add_refcase(self, testcase):
        """
        Add a complete Testcase to the Report.
        This method can be called multiple times to add multiple Testcases to the Report.

        :param testcase: Complete Testcase Object including all depending Teststeps
        :type testcase:  Object of Type TestCase
        """
        # same list of TestCases is expected for test and reference,
        # so only test list of testcases will be printed, no need to setup overview.test_description for refcase

        # Create a entry for the Summary Result
        self._overview.summary_testcases_table.append_ref(testcase)
        self._overview.summary_results_table.append_ref(testcase)

        # Create a Entry for the Detailed Summary Results Table
        self._test_details.summary_results.append_ref(testcase)
        self._test_details.append_ref(testcase)

    def build(self, filepath, level=REP_DEVELOPER):
        """
        Render the complete AlgoTestReport and save it to file.

        :param filepath: path/name of the pdf report.
        :type filepath:  string
        :param level:    Specifies the detail level of the report
        :type level:     <`REP_MANAGEMENT` | `REP_DETAILED` | `REP_DEVELOPER`>
        """
        # first create output dir if needed
        pdf.create_dir(filepath)
        # Create a Instance of our Template Document class,
        # which is needed to create our Document
        self._doc = algotemp.AlgoTestDocTemplate(self.style, filepath, self._custom_page_header_text)

        self.story = []

        # Create the Title Page
        self._doc.pageTemplates[0].status = self._status
        self._title_page.create(self.story)  # pylint: disable=W0212

        # Create TableOfContent
        self.__create_table_of_content(self.story)

        # Create Overview Chapter
        self._overview.create(self.story)  # pylint: disable=W0212

        # Create Test Details Chapter
        if self._test_details:
            self._test_details.create(self.story)  # pylint: disable=W0212

        # self.append(self.__statistic_table.create())
        self.story += self._overview.statistic_table.create()
        # create RunTime Incidents chapter
        # noinspection PyProtectedMember
        if self._runtime_details and (level is self.REP_DEVELOPER or level is self.REP_DETAILED):
            # Create a RunTime Incidents chapter only if jobs are listed
            # noinspection PyProtectedMember
            if len(self._runtime_details._jobs) > 0:  # pylint: disable=W0212
                self._runtime_details.create(self.story)  # pylint: disable=W0212

        # Append the developer story to the main story
        if self.__developer and len(self.__developer.story) > 2:
            self.story += self.__developer.story

        # Append the Table of Figures to the story
        self.__create_table_of_figures(self.story)

        # Append the Table of Tables to the story
        self.__create_table_of_tables(self.story)

        # First go through the whole story, and Format the story in the wanted way.
        story = self._pre_build()

        # Do the final Creation of the pdf Doc rendering....
        self._doc.multiBuild(story)


"""
CHANGE LOG:
-----------
$Log: report.py  $
Revision 1.2 2020/03/31 09:20:05CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:25:59CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/rep/pdf/algo_test/project.pj
"""
