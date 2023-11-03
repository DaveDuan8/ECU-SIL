"""
stk/rep/pdf/reg_test/template
------------------------------

**Template/Layout module of RegTestReport**

**Internal-API Interfaces**

    - `TestDetails`
    - `RuntimeDetails`
    - `OverviewTemplate`

**User-API Interfaces**

    - `stk.rep` (complete package)

:org:           Continental AG
:author:        Joachim Hospes

:version:       $Revision: 1.2 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/12/01 11:22:52CET $
"""
# Import Python Modules --------------------------------------------------------
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Import STK Modules -----------------------------------------------------------
from ..base import template as temp
from ..base import pdf
from . import flowables as flow
from stk.val import Histogram
from stk.img.plot import ValidationPlot

pdfmetrics.registerFont(TTFont('Calibri', 'Calibri.ttf'))
# Defines ----------------------------------------------------------------------

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
        self._refcases = []
        self._mem_reduction = mem_reduction

    def append(self, testcase):
        """
        add a TestCase to the overview table and a chapter with description,
        table and graphs

        :param testcase: TestCase to add
        :type testcase:  `TestCase`
        """
        self._testcases.append(testcase)

    def append_ref(self, testcase):
        """
        add a TestCase to the overview table and a chapter with description,
        table and graphs

        :param testcase: TestCase to add
        :type testcase:  `TestCase`
        """
        self._refcases.append(testcase)

    def _create(self, story, level=None):  # pylint: disable=W0613
        """
        creates the pdf story, called during `report.Build`

        :param story: pdf story to add paragraphs to
        :type story:  list of `pdf.Story` elements
        :param level: not used parameter to set granularity level, set for compatibility with other templates
        """
        local_story = pdf.Story(temp.Style(), self._mem_reduction)

        local_story.add_heading("Test Details", 0)
        local_story.add_heading("Overview", 1)
        local_story.add_space(1)

        if(len(self._testcases)):
            local_story.append(self.summary_results)
            local_story.add_space(1)

            for testcase in self._testcases:
                for refcase in self._refcases:
                    if testcase.id == refcase.id:
                        local_story.add_heading('Testcase ' + testcase.name, 1)
                        local_story.add_space(1)
                        local_story.add_paragraph(str(testcase.description))
                        local_story.add_space(1)
                        # Create Table and add Table to Report
                        tc_table = flow.Testcase(testcase, refcase)
                        local_story.append(tc_table)
                        # plot graphics stored as TestCaseResult
                        for plot in testcase.summery_plots:
                            if type(plot.meas_result) is Histogram:
                                drawing, _ = plot.meas_result.PlotHistogram()
                                local_story.add_image(plot.name, drawing)
                            if type(plot.meas_result) is ValidationPlot:
                                drawing = plot.meas_result.get_drawing()
                                local_story.add_image(plot.name, drawing)

        else:
            local_story.add_paragraph("No Testcases Specified")

        story += local_story.story


class OverviewTemplate(object):  # pylint: disable=R0903
    '''
    template for chapter 1. Test Overview

    printing

      - Testrun names and details
      - Testcases of this Testrun
      - Statistics table with processed distance, time, files
      - TestResults of TestCases
      - TestResults of TestSteps
    '''
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
        self.testrun_overview_details = pdf.Story(temp.Style(), self._mem_reduction)  # story elements of developer with further info
        self.test_description = flow.TestDescription()
        self.statistic_table = flow.TestStatistic()
        self.summary_results_table = flow.SummaryResults()
        self.summary_testcases_table = flow.SummaryTestcases()

    def _create(self, story, level=None):  # pylint: disable=W0613
        '''
        creates the pdf story, called during `report.Build`

        :param story: pdf story to add paragraphs to
        :type story:  list of `pdf.Story` elements
        :param level: not used parameter to set granularity level, set for compatibility with other templates
        '''
        local_story = pdf.Story(temp.Style(), self._mem_reduction)

        local_story.add_heading("Test Overview", 0)
        local_story.add_heading("Regression Test Overview", 1)
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
Revision 1.2 2016/12/01 11:22:52CET Hospes, Gerd-Joachim (uidv8815) 
fix docu errors
Revision 1.1 2015/04/23 19:05:24CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/rep/pdf/reg_test/project.pj
Revision 1.11 2015/03/06 15:39:33CET Ellero, Stefano (uidw8660)
Implemented the optional parameter "mem_reduction" in the base class for all report templates (stk.rep.pdf.base.pdf.Story) to reduce the memory usage during a pdf report generation.
--- Added comments ---  uidw8660 [Mar 6, 2015 3:39:34 PM CET]
Change Package : 307809:1 http://mks-psad:7002/im/viewissue?selection=307809
Revision 1.10 2015/01/27 21:20:09CET Ellero, Stefano (uidw8660)
Removed all rep based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 27, 2015 9:20:10 PM CET]
Change Package : 296836:1 http://mks-psad:7002/im/viewissue?selection=296836
Revision 1.9 2014/09/25 13:29:19CEST Hospes, Gerd-Joachim (uidv8815)
adapt stk.img files to style guide, new names used in all modules and tests except stk.img tests
--- Added comments ---  uidv8815 [Sep 25, 2014 1:29:20 PM CEST]
Change Package : 264203:1 http://mks-psad:7002/im/viewissue?selection=264203
Revision 1.8 2014/08/28 18:46:19CEST Zafar, Sohaib (uidu6396)
Regression Template extended
--- Added comments ---  uidu6396 [Aug 28, 2014 6:46:19 PM CEST]
Change Package : 250924:1 http://mks-psad:7002/im/viewissue?selection=250924
Revision 1.7 2014/07/28 19:23:06CEST Hospes, Gerd-Joachim (uidv8815)
change overview heading to Regression Test Overview
--- Added comments ---  uidv8815 [Jul 28, 2014 7:23:06 PM CEST]
Change Package : 246030:1 http://mks-psad:7002/im/viewissue?selection=246030
Revision 1.6 2014/07/25 14:17:44CEST Hospes, Gerd-Joachim (uidv8815)
epydoc description and some pylint errors fixed
--- Added comments ---  uidv8815 [Jul 25, 2014 2:17:44 PM CEST]
Change Package : 246025:1 http://mks-psad:7002/im/viewissue?selection=246025
Revision 1.5 2014/07/23 12:52:05CEST Hospes, Gerd-Joachim (uidv8815)
allow additional story to test overview wth test_overview_details
--- Added comments ---  uidv8815 [Jul 23, 2014 12:52:05 PM CEST]
Change Package : 246025:1 http://mks-psad:7002/im/viewissue?selection=246025
Revision 1.4 2014/06/22 23:07:32CEST Hospes, Gerd-Joachim (uidv8815)
sync between templates and flowables,
algo_test.report generates perf, func and regr tests
algo_test template and flowable moved to perf_test
--- Added comments ---  uidv8815 [Jun 22, 2014 11:07:32 PM CEST]
Change Package : 241732:1 http://mks-psad:7002/im/viewissue?selection=241732
Revision 1.3 2014/05/06 14:07:37CEST Hospes, Gerd-Joachim (uidv8815)
add developer section again, fix spelling errors
--- Added comments ---  uidv8815 [May 6, 2014 2:07:37 PM CEST]
Change Package : 233144:1 http://mks-psad:7002/im/viewissue?selection=233144
Revision 1.2 2014/04/07 14:12:06CEST Hospes, Gerd-Joachim (uidv8815)
pep8 & pylint fixes after adding new packages and splitting some modules
--- Added comments ---  uidv8815 [Apr 7, 2014 2:12:06 PM CEST]
Change Package : 227496:1 http://mks-psad:7002/im/viewissue?selection=227496
Revision 1.1 2014/04/04 17:38:42CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
stk/rep/pdf/reg_test/project.pj
"""
