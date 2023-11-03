"""
stk/rep/pdf/algo_test/report
----------------------------

**AlgoTestReport Module**

**User-API Interfaces**

    - `AlgoTestReport` (this module)
    - `stk.rep` (complete package)

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.8 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/10/28 12:18:04CEST $
"""
# Import Python Modules --------------------------------------------------------
# needed if deprecated warnings are activated:
# import warnings

# Import STK Modules -----------------------------------------------------------
from ..base import pdf
from ..base import template as temp
from ..algo_base import template as algotemp
from ..algo_base import flowables as algoflow
from ..perf_test import template as perftemp
from ..fct_test import template as fcttemp
from ..reg_test import template as regtemp
from stk.util.helper import deprecated

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
    or it can created any time after the validation run using the command line tool `stk.cmd.gen_report`.

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

        .. python::

            report.build('filename', level=REP_DETAILED)

        **example pdf**

        There are examples created by our module test:

         - Performance test report with granularity REP_MANAGEMENT at PerfTestManagementRep.pdf_
         - Performance test report with granularity REP_DETAILED at PerfTestReport.pdf_

        **selecting**

        Performance test reports are default (`test_type` empty), and automatically selected
        if the TestRun [1]_ attribute `test_type` is set to 'performance':

        .. python::

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

        .. python::

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

        .. python::

            report = AlgoTestReport(testrun1_id, reference=testrun2_id)

    .. [1] TestRun is basically defined in `stk.val.testrun.TestRun`,
           to get reports independent there is the interface class `stk.rep.ifc.TestRun`


    **Example:**

    .. python::

        import stk.rep as rep

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
                                       " See below some possibilities that are used in stk"
                                       " test_rep.test_pdf.test_algo_test.test_report.py just to give some example.")
        report.developer.add_space(0.5)
        report.developer.add_table('table with RotatedText in header',
                                  [['result 1', '13', '14', '15'], ['result 2', '31', '41', '51']],
                                  header=['result', RotatedText('column 1'), RotatedText('column 2'), 42],
                                  colWidths=[200, 20, 20, 50])

        # Save the Report to Disk
        report.build("AlgoTestReport.pdf")

        ...

.. _PerfTestManagementRep.pdf: http://uud296ag:8080/job/STK_NightlyBuild/lastSuccessfulBuild/artifact/
                               05_Testing/04_Test_Data/02_Output/rep/PerfTestManagementRep.pdf
.. _PerfTestReport.pdf: http://uud296ag:8080/job/STK_NightlyBuild/lastSuccessfulBuild/artifact/
                        05_Testing/04_Test_Data/02_Output/rep/PerfTestReport.pdf
.. _FctTestReport.pdf: http://uud296ag:8080/job/STK_NightlyBuild/lastSuccessfulBuild/artifact/
                       05_Testing/04_Test_Data/02_Output/rep/FctTestReport.pdf
.. _RegTestReport.pdf: http://uud296ag:8080/job/STK_NightlyBuild/lastSuccessfulBuild/artifact/
                       05_Testing/04_Test_Data/02_Output/rep/RegTestReport.pdf

    :author:        Robert Hecker
    :date:          22.01.2012
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
        ''' story elements for additional info below the table in chapter "Test Overview" '''
        return self._overview.testrun_overview_details

    @property
    def developer(self):
        ''' developer story of the report, empty chapter that can be filled with project specific information '''
        return self.__developer

    @property
    def statistic_table(self):
        '''
        access to statistic table listing processed time, distance and files,
        allows to append project specific lines of the TestRun
        '''
        return self.__statistic_table

    @property
    @deprecated('developer')
    def Developer(self):
        """
        :deprecated: use `developer` instead
        """
        # warnings.warn('Attribute "Developer" is deprecated use "developer" instead', stacklevel=2)
        return self.developer

    @property
    @deprecated('statistic_table')
    def StatisticTable(self):
        """
        :deprecated: use `statistic_table` instead
        """
        # warnings.warn('Attribute "StatisticTable" is deprecated use "statistic_table" instead', stacklevel=2)
        return self.statistic_table

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
        # protected member '_create' inherited from platypus
        story += toc._create()  # pylint: disable=W0212

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
        # protected member '_create' inherited from platypus
        story += tof._create()  # pylint: disable=W0212

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
        # protected member '_create' inherited from platypus
        story += tot._create()  # pylint: disable=W0212

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
            if testrun.test_type is 'functional':
                self._overview = fcttemp.OverviewTemplate()
            else:
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
        self._title_page._create(self.story)  # pylint: disable=W0212

        # Create TableOfContent
        self.__create_table_of_content(self.story)

        # Create Overview Chapter
        self._overview._create(self.story)  # pylint: disable=W0212

        # Create Test Details Chapter
        if self._test_details:
            self._test_details._create(self.story, level)  # pylint: disable=W0212

        # create RunTime Incidents chapter
        if (self._runtime_details and (level is self.REP_DEVELOPER or level is self.REP_DETAILED)):
            # Create a RunTime Incidents chapter only if jobs are listed
            if len(self._runtime_details._jobs) > 0:  # pylint: disable=W0212
                self._runtime_details._create(self.story)  # pylint: disable=W0212

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

    @deprecated('set_test_run')
    def SetTestRun(self, testrun):
        """
        :deprecated: use `set_test_run` instead
        """
        # warnings.warn('Method "SetTestRun" is deprecated use "set_test_run" instead', stacklevel=2)
        return self.set_test_run(testrun)

    @deprecated('build')
    def Build(self, filepath, level=REP_DEVELOPER):
        """
        :deprecated: use `build` instead
        """
        # warnings.warn('Method "Build" is deprecated use "build" instead', stacklevel=2)
        return self.build(filepath, level)


"""
CHANGE LOG:
-----------
$Log: report.py  $
Revision 1.8 2016/10/28 12:18:04CEST Hospes, Gerd-Joachim (uidv8815) 
fix docu passing test run
Revision 1.7 2016/07/22 15:54:09CEST Hospes, Gerd-Joachim (uidv8815)
new fields sim version and val sw version
Revision 1.6 2016/05/09 11:00:15CEST Hospes, Gerd-Joachim (uidv8815)
add new column REMARKS to val.db and to pfd reports as new overview table row
Revision 1.5 2016/04/12 15:08:20CEST Hospes, Gerd-Joachim (uidv8815)
fix pylint errors
Revision 1.4 2015/10/29 17:46:35CET Hospes, Gerd-Joachim (uidv8815)
add collection and sim_name to reports
- Added comments -  uidv8815 [Oct 29, 2015 5:46:36 PM CET]
Change Package : 390799:1 http://mks-psad:7002/im/viewissue?selection=390799
Revision 1.3 2015/09/18 17:42:34CEST Hospes, Gerd-Joachim (uidv8815)
fix sorting test steps
--- Added comments ---  uidv8815 [Sep 18, 2015 5:42:35 PM CEST]
Change Package : 376761:2 http://mks-psad:7002/im/viewissue?selection=376761
Revision 1.2 2015/09/17 16:48:31CEST Hospes, Gerd-Joachim (uidv8815)
sort test cases and steps before creating report
Revision 1.1 2015/04/23 19:05:11CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/rep/pdf/algo_test/project.pj
Revision 1.34 2015/03/10 16:48:25CET Ellero, Stefano (uidw8660)
Each page of the pdf report starts with the hard coded header "Algo Validation Report".
A variable is introduced to set this header to another string, if needed; default is the existing one.
This internal variable is set during initialization of the report class
using an option named: "custom_page_header_text".
--- Added comments ---  uidw8660 [Mar 10, 2015 4:48:26 PM CET]
Change Package : 314895:1 http://mks-psad:7002/im/viewissue?selection=314895
Revision 1.33 2015/03/06 15:39:31CET Ellero, Stefano (uidw8660)
Implemented the optional parameter "mem_reduction" in the base class for all report templates
(stk.rep.pdf.base.pdf.Story) to reduce the memory usage during a pdf report generation.
--- Added comments ---  uidw8660 [Mar 6, 2015 3:39:32 PM CET]
Change Package : 307809:1 http://mks-psad:7002/im/viewissue?selection=307809
Revision 1.32 2015/01/29 17:43:35CET Hospes, Gerd-Joachim (uidv8815)
add 'add_info' to report top page
--- Added comments ---  uidv8815 [Jan 29, 2015 5:43:35 PM CET]
Change Package : 298621:1 http://mks-psad:7002/im/viewissue?selection=298621
Revision 1.31 2015/01/27 21:20:05CET Ellero, Stefano (uidw8660)
Removed all rep based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 27, 2015 9:20:06 PM CET]
Change Package : 296836:1 http://mks-psad:7002/im/viewissue?selection=296836
Revision 1.30 2014/08/29 11:53:47CEST Zafar, Sohaib (uidu6396)
Regression Report Template
--- Added comments ---  uidu6396 [Aug 29, 2014 11:53:48 AM CEST]
Change Package : 250924:1 http://mks-psad:7002/im/viewissue?selection=250924
Revision 1.29 2014/07/29 12:41:24CEST Hospes, Gerd-Joachim (uidv8815)
pep8 fixes of too long lines for http links, epydoc and pylint adjustments
--- Added comments ---  uidv8815 [Jul 29, 2014 12:41:25 PM CEST]
Change Package : 246030:1 http://mks-psad:7002/im/viewissue?selection=246030
Revision 1.28 2014/07/28 19:19:20CEST Hospes, Gerd-Joachim (uidv8815)
correct links to pdf examples
--- Added comments ---  uidv8815 [Jul 28, 2014 7:19:20 PM CEST]
Change Package : 246030:1 http://mks-psad:7002/im/viewissue?selection=246030
Revision 1.27 2014/07/25 14:17:46CEST Hospes, Gerd-Joachim (uidv8815)
epydoc description and some pylint errors fixed
--- Added comments ---  uidv8815 [Jul 25, 2014 2:17:46 PM CEST]
Change Package : 246025:1 http://mks-psad:7002/im/viewissue?selection=246025
Revision 1.26 2014/07/23 12:52:02CEST Hospes, Gerd-Joachim (uidv8815)
allow additional story to test overview wth test_overview_details
--- Added comments ---  uidv8815 [Jul 23, 2014 12:52:02 PM CEST]
Change Package : 246025:1 http://mks-psad:7002/im/viewissue?selection=246025
Revision 1.25 2014/06/26 11:15:58CEST Hospes, Gerd-Joachim (uidv8815)
fine tuning of epydoc for AlgoTestReport and base
--- Added comments ---  uidv8815 [Jun 26, 2014 11:15:58 AM CEST]
Change Package : 243858:2 http://mks-psad:7002/im/viewissue?selection=243858
Revision 1.24 2014/06/22 23:07:31CEST Hospes, Gerd-Joachim (uidv8815)
sync between templates and flowables,
algo_test.report generates perf, func and regr tests
algo_test template and flowable moved to perf_test
--- Added comments ---  uidv8815 [Jun 22, 2014 11:07:31 PM CEST]
Change Package : 241732:1 http://mks-psad:7002/im/viewissue?selection=241732
Revision 1.23 2014/05/20 13:18:44CEST Hospes, Gerd-Joachim (uidv8815)
add user_account to report, based on testrun or ifc definition, update test_report
--- Added comments ---  uidv8815 [May 20, 2014 1:18:45 PM CEST]
Change Package : 233145:1 http://mks-psad:7002/im/viewissue?selection=233145
Revision 1.22 2014/05/15 13:42:57CEST Hospes, Gerd-Joachim (uidv8815)
introduce testrun.component to pdf reports
--- Added comments ---  uidv8815 [May 15, 2014 1:42:57 PM CEST]
Change Package : 233146:1 http://mks-psad:7002/im/viewissue?selection=233146
Revision 1.21 2014/05/09 17:23:02CEST Hospes, Gerd-Joachim (uidv8815)
set DRAFT depending on testrun.locked
--- Added comments ---  uidv8815 [May 9, 2014 5:23:03 PM CEST]
Change Package : 233144:2 http://mks-psad:7002/im/viewissue?selection=233144
Revision 1.20 2014/05/09 12:56:24CEST Hospes, Gerd-Joachim (uidv8815)
report either details overview or detailed development table
--- Added comments ---  uidv8815 [May 9, 2014 12:56:24 PM CEST]
Change Package : 233158:1 http://mks-psad:7002/im/viewissue?selection=233158
Revision 1.19 2014/05/06 10:54:20CEST Hospes, Gerd-Joachim (uidv8815)
update creating output dir
--- Added comments ---  uidv8815 [May 6, 2014 10:54:21 AM CEST]
Change Package : 233144:1 http://mks-psad:7002/im/viewissue?selection=233144
Revision 1.18 2014/05/05 19:31:33CEST Hospes, Gerd-Joachim (uidv8815)
add creation of path and its test
--- Added comments ---  uidv8815 [May 5, 2014 7:31:33 PM CEST]
Change Package : 233144:1 http://mks-psad:7002/im/viewissue?selection=233144
Revision 1.17 2014/04/07 14:11:00CEST Hospes, Gerd-Joachim (uidv8815)
pep8 & pylint fixes after adding new packages and splitting some modules
--- Added comments ---  uidv8815 [Apr 7, 2014 2:11:00 PM CEST]
Change Package : 227496:1 http://mks-psad:7002/im/viewissue?selection=227496
Revision 1.16 2014/04/04 17:39:52CEST Hospes, Gerd-Joachim (uidv8815)
removed algo_base commen classes and functions
Revision 1.15 2014/03/28 11:32:46CET Hecker, Robert (heckerr)
commented out warnings.
--- Added comments ---  heckerr [Mar 28, 2014 11:32:46 AM CET]
Change Package : 228098:1 http://mks-psad:7002/im/viewissue?selection=228098
Revision 1.14 2014/03/28 10:25:52CET Hecker, Robert (heckerr)
Adapted to new coding guiedlines incl. backwardcompatibility.
Revision 1.13 2014/03/14 10:29:08CET Hospes, Gerd-Joachim (uidv8815)
pylint fixes
--- Added comments ---  uidv8815 [Mar 14, 2014 10:29:09 AM CET]
Change Package : 221504:1 http://mks-psad:7002/im/viewissue?selection=221504
Revision 1.12 2014/03/13 19:06:21CET Hospes, Gerd-Joachim (uidv8815)
list results of testcases and teststeps seperatly
Revision 1.11 2014/02/28 10:54:55CET Hospes, Gerd-Joachim (uidv8815)
new rotated text feature added to epidoc for algo_test_report
--- Added comments ---  uidv8815 [Feb 28, 2014 10:54:56 AM CET]
Change Package : 219820:2 http://mks-psad:7002/im/viewissue?selection=219820
Revision 1.10 2014/02/20 17:44:19CET Hospes, Gerd-Joachim (uidv8815)
use new processed_<values> in pdf report
Revision 1.9 2014/02/14 15:36:57CET Hospes, Gerd-Joachim (uidv8815)
activate runtime incident tables if jobs are listed in testrun
--- Added comments ---  uidv8815 [Feb 14, 2014 3:36:57 PM CET]
Change Package : 214928:2 http://mks-psad:7002/im/viewissue?selection=214928
Revision 1.8 2014/02/13 17:41:56CET Hospes, Gerd-Joachim (uidv8815)
add distance and time to statistic table, method for user to add stistic table rows
--- Added comments ---  uidv8815 [Feb 13, 2014 5:41:57 PM CET]
Change Package : 218178:1 http://mks-psad:7002/im/viewissue?selection=218178
Revision 1.7 2014/02/12 18:34:57CET Hospes, Gerd-Joachim (uidv8815)
update table styles, use stk defines for assessment states, add table captions
--- Added comments ---  uidv8815 [Feb 12, 2014 6:34:57 PM CET]
Change Package : 218178:1 http://mks-psad:7002/im/viewissue?selection=218178
Revision 1.6 2014/02/05 13:58:24CET Hospes, Gerd-Joachim (uidv8815)
chapter Test Execution Details added to report with template, flowables and tests
--- Added comments ---  uidv8815 [Feb 5, 2014 1:58:24 PM CET]
Change Package : 214928:1 http://mks-psad:7002/im/viewissue?selection=214928
Revision 1.5 2013/12/04 13:46:13CET Hecker, Robert (heckerr)
BugFixing.
--- Added comments ---  heckerr [Dec 4, 2013 1:46:14 PM CET]
Change Package : 209900:1 http://mks-psad:7002/im/viewissue?selection=209900
Revision 1.4 2013/10/25 09:02:33CEST Hecker, Robert (heckerr)
Removed Pep8 Issues.
--- Added comments ---  heckerr [Oct 25, 2013 9:02:33 AM CEST]
Change Package : 202843:1 http://mks-psad:7002/im/viewissue?selection=202843
Revision 1.3 2013/10/22 14:27:12CEST Hecker, Robert (heckerr
modified parameter type.
--- Added comments ---  heckerr [Oct 22, 2013 2:27:12 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.2 2013/10/21 08:44:24CEST Hecker, Robert (heckerr)
updated doxygen description.
--- Added comments ---  heckerr [Oct 21, 2013 8:44:24 AM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.1 2013/10/18 17:45:13CEST Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/rep/pdf/algo_test/project.pj
"""
