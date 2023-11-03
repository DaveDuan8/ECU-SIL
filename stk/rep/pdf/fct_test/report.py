"""
stk/rep/pdf/fct_test/report
----------------------------

**FctTestReport Module**

**User-API Interfaces**

    - `FctTestReport` (this module)
    - `stk.rep` (complete package)

:org:           Continental AG
:author:        Joachim Hospes

:version:       $Revision: 1.7 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/12/01 11:22:51CET $
"""
# Import Python Modules --------------------------------------------------------
# needed if deprecated warnings are activated:
# import warnings

# Import STK Modules -----------------------------------------------------------
from ..base import pdf
from ..base import template as temp
from ..algo_base import template as algotemp
from ..algo_base import flowables as algoflow
from . import template

# Defines ----------------------------------------------------------------------
PAGE_TEMPLATE_PORTRAIT = algotemp.PAGE_TEMPLATE_PORTRAIT
PAGE_TEMPLATE_LANDSCAPE = algotemp.PAGE_TEMPLATE_LANDSCAPE

# Functions --------------------------------------------------------------------

# Classes ----------------------------------------------------------------------


class FctTestReport(pdf.Story):
    """
    The FctTestReport class creates a Function Test Report for the Algo-Validation.

    **Following Features are included:**

    1. Possibility to define the granularity of the Report with
       `REP_MANAGEMENT` | `REP_DETAILED` | `REP_DEVELOPER`
    2. Generic `Testcase` and `Teststep` Interface
    3. Possibility to insert into the Developer Chapter every pdf-platypus
       element you want.

    **Example:**

    .. python::

        # Import stk.rep
        import stk.rep as rep

        # Create a Testrun Object
        testrun = val.testrun.TestRun(name="SampleTestrunName",  checkpoint="AL_ARS4xx_00.00.00_INT-1",
                                      proj_name="ARS400", obs_name="S_Test", test_collection="ARS4xx_sample_col")

        # Fill in Data into the TestRun or load from valDb
        ...

        # Create an instance of the reporter class for the TestRun
        report = rep.AlgoTestReport(testrun)

        # Fill project specific chapter "Development details"
        report.developer.add_paragraph("This is the developer chapter where testers can add text, tables and figures. "
                                       "See below some possibilities that are used in stk "
                                       "test_rep.test_pdf.test_algo_test.test_report.py just to give some example.")
        report.developer.add_space(0.5)
        report.developer.add_table('table with RotatedText in header',
                                  [['result 1', '13', '14', '15'], ['result 2', '31', '41', '51']],
                                  header=['result', RotatedText('column 1'), RotatedText('column 2'), 42],
                                  colWidths=[200, 20, 20, 50])

        # Save the Report to Disk
        report.build("FctTestReport.pdf")

        ...

    :author:        Joachim Hospes
    :date:          03.06.13
    """
    REP_MANAGEMENT = 1
    """
    Render only the Management Part inside the Report
    """
    REP_DETAILED = 2
    """
    Render additional to `REP_MANAGEMENT` the Detailed Chapter into the Report
    """
    REP_DEVELOPER = 4
    """
    Render additional to `REP_DETAILED` the Developer Chapter into the Report
    """

    def __init__(self, testrun=None, mem_reduction=False, custom_page_header_text=None):
        """
        preset class internal variables

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

        self._title_page = algotemp.TitlePageTemplate(algotemp.AlgoTestDocTemplate(self.style, "", self._custom_page_header_text))
        self._status = 'final'
        self._overview = template.OverviewTemplate()

        self.__developer = algotemp.DeveloperTemplate(mem_reduction=self._mem_reduction)

        if testrun:
            self.set_test_run(testrun)

    @property
    def developer(self):
        ''' developer story of the report, empty chapter that can be filled with project specific information '''
        return self.__developer

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

        This method is used to create a FctTestReport on component Level
        with all the standardized output.

        The Developer Part of the Report is untouched by this.

        :param testrun: Complete TestRun for one Component.
        :type testrun:  Object of Type `ITestRun`
        """
        # Set Tile in Title Page
        self._title_page.title = testrun.name

        # Set Title in Overview Table
        self._overview.overview_table.title = testrun.name

        # Set Checkpoint
        self._title_page.checkpoint = testrun.checkpoint
        self._title_page.add_info = testrun.add_info

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

        # set collection and simulation details rows
        self._overview.overview_table.collection = testrun.collection
        self._overview.overview_table.sim_name = testrun.sim_name
        self._overview.overview_table.sim_version = testrun.sim_version

        # set validation sw version
        self._overview.overview_table.val_sw_version = testrun.val_sw_version

        # Set User account who executed the testrun
        self._overview.overview_table.user_account = testrun.user_account

        # set valDb internal testrun id
        self._overview.overview_table.tr_id = testrun.id

        # set testers comment row
        self._overview.overview_table.remarks = testrun.remarks

        for testcase in sorted(testrun.test_cases, key=lambda i: i.id):
            self.__add_testcase(testcase)

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

    def build(self, filepath):
        """
        Render the complete FctTestReport and save it to file.

        :param filepath: path/name of the pdf report.
        :type filepath:  string
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

        # Append the developer story to the main story
        self.story += self.developer.story

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
Revision 1.7 2016/12/01 11:22:51CET Hospes, Gerd-Joachim (uidv8815) 
fix docu errors
Revision 1.6 2016/07/22 15:54:08CEST Hospes, Gerd-Joachim (uidv8815)
new fields sim version and val sw version
Revision 1.5 2016/05/09 11:00:17CEST Hospes, Gerd-Joachim (uidv8815)
add new column REMARKS to val.db and to pfd reports as new overview table row
Revision 1.4 2015/10/29 17:46:36CET Hospes, Gerd-Joachim (uidv8815)
add collection and sim_name to reports
- Added comments -  uidv8815 [Oct 29, 2015 5:46:37 PM CET]
Change Package : 390799:1 http://mks-psad:7002/im/viewissue?selection=390799
Revision 1.3 2015/09/18 17:44:54CEST Hospes, Gerd-Joachim (uidv8815)
fix sorting test steps
--- Added comments ---  uidv8815 [Sep 18, 2015 5:44:55 PM CEST]
Change Package : 376761:2 http://mks-psad:7002/im/viewissue?selection=376761
Revision 1.2 2015/09/17 16:48:31CEST Hospes, Gerd-Joachim (uidv8815)
sort test cases and steps before creating report
Revision 1.1 2015/04/23 19:05:17CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/rep/pdf/fct_test/project.pj
Revision 1.8 2015/03/10 16:48:24CET Ellero, Stefano (uidw8660)
Each page of the pdf report starts with the hard coded header "Algo Validation Report".
A variable is introduced to set this header to another string, if needed; default is the existing one.
This internal variable is set during initialization of the report class using an option named: "custom_page_header_text".
--- Added comments ---  uidw8660 [Mar 10, 2015 4:48:25 PM CET]
Change Package : 314895:1 http://mks-psad:7002/im/viewissue?selection=314895
Revision 1.7 2015/03/06 15:39:29CET Ellero, Stefano (uidw8660)
Implemented the optional parameter "mem_reduction" in the base class for all report templates (stk.rep.pdf.base.pdf.Story) to reduce the memory usage during a pdf report generation.
--- Added comments ---  uidw8660 [Mar 6, 2015 3:39:30 PM CET]
Change Package : 307809:1 http://mks-psad:7002/im/viewissue?selection=307809
Revision 1.6 2015/01/29 17:43:19CET Hospes, Gerd-Joachim (uidv8815)
add 'add_info' to report top page
--- Added comments ---  uidv8815 [Jan 29, 2015 5:43:20 PM CET]
Change Package : 298621:1 http://mks-psad:7002/im/viewissue?selection=298621
Revision 1.5 2014/06/24 17:01:29CEST Hospes, Gerd-Joachim (uidv8815)
move table caption below table, extend some epydoc
--- Added comments ---  uidv8815 [Jun 24, 2014 5:01:29 PM CEST]
Change Package : 243858:1 http://mks-psad:7002/im/viewissue?selection=243858
Revision 1.4 2014/06/22 23:07:30CEST Hospes, Gerd-Joachim (uidv8815)
sync between templates and flowables,
algo_test.report generates perf, func and regr tests
algo_test template and flowable moved to perf_test
--- Added comments ---  uidv8815 [Jun 22, 2014 11:07:30 PM CEST]
Change Package : 241732:1 http://mks-psad:7002/im/viewissue?selection=241732
Revision 1.3 2014/06/05 16:24:18CEST Hospes, Gerd-Joachim (uidv8815)
final fixes after approval from Zhang Luo: cleanup and epydoc, pylint and pep8
--- Added comments ---  uidv8815 [Jun 5, 2014 4:24:18 PM CEST]
Change Package : 237743:1 http://mks-psad:7002/im/viewissue?selection=237743
Revision 1.2 2014/06/03 18:47:09CEST Hospes, Gerd-Joachim (uidv8815)
pylint fixes
--- Added comments ---  uidv8815 [Jun 3, 2014 6:47:10 PM CEST]
Change Package : 237743:1 http://mks-psad:7002/im/viewissue?selection=237743
Revision 1.1 2014/06/03 17:38:57CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/rep/pdf/fct_test/project.pj
"""
