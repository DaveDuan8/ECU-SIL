"""
stk/rep/pdf/reg_test/report.py
------------------------------

**RegressionTestReport Module**

**User-API Interfaces**

    - `RegTestReport` (this module)
    - `stk.rep` (complete package)

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.1 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/25 21:30:54CET $
"""
# - import STK modules ------------------------------------------------------------------------------------------------
from ..base import pdf
from ..base import template as temp
from ..algo_base import template as algotemp
from ..algo_base import flowables as algoflow
from . import template

# - defines -----------------------------------------------------------------------------------------------------------
PAGE_TEMPLATE_PORTRAIT = algotemp.PAGE_TEMPLATE_PORTRAIT
PAGE_TEMPLATE_LANDSCAPE = algotemp.PAGE_TEMPLATE_LANDSCAPE


# - classes -----------------------------------------------------------------------------------------------------------
class RegTestReport(pdf.Story):  # pylint: disable=R0902
    """
    This class is deprecated and will be removed in future, please use class `AlgoTestReport`.

    The RegTestReport class creates a Standard Regression Report for two Algo-TestRuns

    **Following Features are included:**

    1. Posibility to define the granularity of the Report with
       `REP_MANAGEMENT` | `REP_DETAILED` | `REP_DEVELOPER`
    2. Generic `Testcase` and `Teststep` Interface
    3. Possibility to insert into the Developer Chapter every pdf-platypus
       element you want.

    **Example:**

    .. code-block:: python

        # Import stk.rep
        import stk.rep as rep

        # Create a Testrun Object
        testrun = val.testrun.TestRun(name="SampleTestrunName",  checkpoint="AL_ARS4xx_00.00.00_INT-1",
                                      proj_name="ARS400", obs_name="S_Test", test_collection="ARS4xx_sample_col")

        # Fill in Data into the TestRun or load from val db
        ...

        # Create a Reference Testrun Object
        reference = val.testrun.TestRun()

        # Load Data into the ref. TestRun
        ...

        # Create an instance of the reporter class for the TestRun and its Reference
        # (testrun and reference optional, can be added later calling `set_test_run()` resp. `set_reference()`).
        report = rep.AlgoTestReport(testrun, reference)

        # Save the Report to Disk
        report.build("RegTestReport.pdf")

        ...

    :author:        Joachim Hospes
    :date:          02.04.2014
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

    def __init__(self, testrun=None, reference=None, mem_reduction=False, custom_page_header_text=None):
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

        self._title_page = algotemp.TitlePageTemplate(algotemp.AlgoTestDocTemplate(self.style, "",
                                                                                   self._custom_page_header_text))
        self._overview = template.OverviewTemplate()

        self._test_details = template.TestDetails(self._mem_reduction)

        self.__developer = algotemp.DeveloperTemplate(mem_reduction=self._mem_reduction)
        self.__statistic_table = self._overview.statistic_table

        if testrun:
            self.set_test_run(testrun)
        if reference:
            self.set_reference(reference)

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
    def __create_table_of_content(story):
        """
        Append the Table Of Contents to the story.

        :param story: Pdf-story
        """
        # argument 'story' used, but pylint does not find it
        # pylint: disable=W0613
        toc = algoflow.TableOfContents()
        # noinspection PyUnresolvedReferences
        story += toc.create()  # pylint: disable=W0212

    @staticmethod
    def __create_table_of_figures(story):  # pylint: disable=W0613,R0201
        """
        Append the Table Of Figures to the story.

        :param story: Pdf-story
        """
        tof = algoflow.TableOfFigures()
        story += tof.create()  # pylint: disable=W0212

    @staticmethod
    def __create_table_of_tables(story):  # pylint: disable=W0613,R0201
        """
        Append the Table Of Tables to the story.

        :param story: Pdf-story
        """
        tot = algoflow.TableOfTables()
        story += tot.create()  # pylint: disable=W0212

    def set_test_run(self, testrun):
        """
        Specify a Component TestRun which is used to Build a Report.

        This method is used to create a AlgoTestReport on component Level
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
        self._title_page.test_checkpoint = testrun.checkpoint
        self._title_page.add_info = testrun.add_info
        self._overview.overview_table.test_checkpoint = testrun.checkpoint

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

        # Set User account executing the testrun
        self._overview.overview_table.user_account = testrun.user_account

        # Set test_spec
        self._overview.overview_table.tr_id = testrun.id

        # set testers comment row
        self._overview.overview_table.remarks = testrun.remarks

        # prep Statistics table
        self.statistic_table.set_testrun(testrun)

        for testcase in testrun.test_cases:
            self.__add_testcase(testcase)

    def __add_testcase(self, testcase):
        """
        Add a complete Testcase to the Report.

        This method can be called multiple times to add multiple Testcases to the Report.

        :param testcase: Complete Testcase Object including all depending Teststeps
        :type  testcase: Object of Type TestCase
        """
        # Get the Testcase Description out of the Testcase and feed them into Overview
        self._overview.test_description.append(testcase)

        # Create a entry for the Summary Result
        self._overview.summary_testcases_table.append(testcase)
        self._overview.summary_results_table.append(testcase)

        # Create a Entry for the Detailed Summary Results Table
        self._test_details.summary_results.append(testcase)

        self._test_details.append(testcase)

    def set_reference(self, testrun):
        """
        Specify a Reference TestRun which is compared to the main TestRun.

        This method is used to create a AlgoTestReport on component Level
        with all the standardized output.
        The Developer Part of the Report is untouched by this.

        :param testrun: Complete TestRun for one Component.
        :type  testrun: Object of Type `ITestRun`
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

        # set collection and simulation details rows
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
        # same list of TestCases is expected for test and reference, only test list will be printed
        # self._overview.TestDescription.append_ref(testcase)

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
        pdf.create_dir(filepath)
        # Create a Instance of our Template Document class,
        # which is needed to create our Document
        self._doc = algotemp.AlgoTestDocTemplate(self.style, filepath, self._custom_page_header_text)

        self.story = []

        # Create the Title Page
        self._title_page.create(self.story)  # pylint: disable=W0212

        # Create TableOfContent
        self.__create_table_of_content(self.story)

        # Create Overview Chapter
        self._overview.create(self.story)  # pylint: disable=W0212

        if level is self.REP_DEVELOPER or level is self.REP_DETAILED:
            # Create Test Details Chapter
            self._test_details.create(self.story)  # pylint: disable=W0212

        if level is self.REP_DEVELOPER:
            # Append the developer story to the main story
            # if it contains more than two entries (page break and heading as default)
            # if len(self.Developer.story) > 2:
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
Revision 1.1 2020/03/25 21:30:54CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/rep/pdf/reg_test/project.pj
Revision 1.7 2018/08/10 17:36:15CEST Hospes, Gerd-Joachim (uidv8815)
use .. code-block::  for sphinx
Revision 1.6 2016/12/01 11:22:50CET Hospes, Gerd-Joachim (uidv8815)
fix docu errors
Revision 1.5 2016/07/22 15:54:07CEST Hospes, Gerd-Joachim (uidv8815)
new fields sim version and val sw version
Revision 1.4 2016/05/09 11:00:19CEST Hospes, Gerd-Joachim (uidv8815)
add new column REMARKS to val.db and to pfd reports as new overview table row
Revision 1.3 2015/12/07 14:31:16CET Mertens, Sven (uidv7805)
removing pep8 errors
Revision 1.2 2015/10/29 17:48:10CET Hospes, Gerd-Joachim (uidv8815)
add collection and sim_name to reports
- Added comments -  uidv8815 [Oct 29, 2015 5:48:10 PM CET]
Change Package : 390799:1 http://mks-psad:7002/im/viewissue?selection=390799
Revision 1.1 2015/04/23 19:05:23CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/
    04_Engineering/01_Source_Code/stk/rep/pdf/reg_test/project.pj
Revision 1.15 2015/03/10 16:48:24CET Ellero, Stefano (uidw8660)
Each page of the pdf report starts with the hard coded header "Algo Validation Report".
A variable is introduced to set this header to another string, if needed; default is the existing one.
This internal variable is set during initialization of the report class using an option named: "custom_page_header_text"
--- Added comments ---  uidw8660 [Mar 10, 2015 4:48:24 PM CET]
Change Package : 314895:1 http://mks-psad:7002/im/viewissue?selection=314895
Revision 1.14 2015/03/06 15:39:27CET Ellero, Stefano (uidw8660)
Implemented the optional parameter "mem_reduction" in the base class for all report templates (stk.rep.pdf.base.pdf.
    Story) to reduce the memory usage during a pdf report generation.
--- Added comments ---  uidw8660 [Mar 6, 2015 3:39:29 PM CET]
Change Package : 307809:1 http://mks-psad:7002/im/viewissue?selection=307809
Revision 1.13 2015/02/03 17:44:32CET Hospes, Gerd-Joachim (uidv8815)
changed to tr_id and document as deprecated
(not marked as deprecated as AlgoTestReport has no SetReference)
--- Added comments ---  uidv8815 [Feb 3, 2015 5:44:33 PM CET]
Change Package : 301807:1 http://mks-psad:7002/im/viewissue?selection=301807
Revision 1.12 2015/01/29 17:43:18CET Hospes, Gerd-Joachim (uidv8815)
add 'add_info' to report top page
Revision 1.11 2014/08/28 18:45:51CEST Zafar, Sohaib (uidu6396)
Regression Template extended
--- Added comments ---  uidu6396 [Aug 28, 2014 6:45:52 PM CEST]
Change Package : 250924:1 http://mks-psad:7002/im/viewissue?selection=250924
Revision 1.10 2014/07/15 12:49:52CEST Hospes, Gerd-Joachim (uidv8815)
fix typo, add tests for RegTestReport
--- Added comments ---  uidv8815 [Jul 15, 2014 12:49:52 PM CEST]
Change Package : 248703:1 http://mks-psad:7002/im/viewissue?selection=248703
Revision 1.9 2014/06/24 17:01:28CEST Hospes, Gerd-Joachim (uidv8815)
move table caption below table, extend some epydoc
--- Added comments ---  uidv8815 [Jun 24, 2014 5:01:28 PM CEST]
Change Package : 243858:1 http://mks-psad:7002/im/viewissue?selection=243858
Revision 1.8 2014/06/22 23:07:29CEST Hospes, Gerd-Joachim (uidv8815)
sync between templates and flowables,
algo_test.report generates perf, func and regr tests
algo_test template and flowable moved to perf_test
--- Added comments ---  uidv8815 [Jun 22, 2014 11:07:29 PM CEST]
Change Package : 241732:1 http://mks-psad:7002/im/viewissue?selection=241732
Revision 1.7 2014/05/20 13:18:40CEST Hospes, Gerd-Joachim (uidv8815)
add user_account to report, based on testrun or ifc definition, update test_report
--- Added comments ---  uidv8815 [May 20, 2014 1:18:40 PM CEST]
Change Package : 233145:1 http://mks-psad:7002/im/viewissue?selection=233145
Revision 1.6 2014/05/15 13:42:56CEST Hospes, Gerd-Joachim (uidv8815)
introduce testrun.component to pdf reports
--- Added comments ---  uidv8815 [May 15, 2014 1:42:57 PM CEST]
Change Package : 233146:1 http://mks-psad:7002/im/viewissue?selection=233146
Revision 1.5 2014/05/06 13:35:35CEST Hospes, Gerd-Joachim (uidv8815)
activate developer section again
--- Added comments ---  uidv8815 [May 6, 2014 1:35:36 PM CEST]
Change Package : 233144:1 http://mks-psad:7002/im/viewissue?selection=233144
Revision 1.4 2014/05/06 13:25:49CEST Hospes, Gerd-Joachim (uidv8815)
update epidoc description
--- Added comments ---  uidv8815 [May 6, 2014 1:25:49 PM CEST]
Change Package : 233144:1 http://mks-psad:7002/im/viewissue?selection=233144
Revision 1.3 2014/05/06 10:53:53CEST Hospes, Gerd-Joachim (uidv8815)
update test for missing output dir
--- Added comments ---  uidv8815 [May 6, 2014 10:53:54 AM CEST]
Change Package : 233144:1 http://mks-psad:7002/im/viewissue?selection=233144
Revision 1.2 2014/04/07 14:10:42CEST Hospes, Gerd-Joachim (uidv8815)
pep8 & pylint fixes after adding new packages and splitting some modules
--- Added comments ---  uidv8815 [Apr 7, 2014 2:10:42 PM CEST]
Change Package : 227496:1 http://mks-psad:7002/im/viewissue?selection=227496
Revision 1.1 2014/04/04 17:38:41CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
stk/rep/pdf/reg_test/project.pj
"""
