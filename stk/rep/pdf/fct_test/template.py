"""
stk/rep/pdf/fct_test/template
------------------------------

**Template/Layout module of FctTestReport**

**Internal-API Interfaces**

    - `OverviewTemplate`

**User-API Interfaces**

    - `stk.rep` (complete package)

:org:           Continental AG
:author:        Joachim Hospes

:version:       $Revision: 1.2 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/12/01 11:22:53CET $
"""
# Import Python Modules --------------------------------------------------------
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
# needed when deprecation warnings are activated:
# import warnings

# Import STK Modules -----------------------------------------------------------
from ..base import template as temp
from ..base import pdf
from . import flowables as flow

pdfmetrics.registerFont(TTFont('Calibri', 'Calibri.ttf'))

# Defines ----------------------------------------------------------------------
REP_MANAGEMENT = 1
REP_DETAILED = 2
REP_DEVELOPER = 4

# Functions --------------------------------------------------------------------

# Classes ----------------------------------------------------------------------


class OverviewTemplate(object):
    '''
    template for chapter 1. Test Overview
    printing

      - Testrun names and details
      - Testcases of this Testrun
      - Statistics table with processed files, number of testcases
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
        # pylint disable=C0103
        self.overview_table = flow.Overview()
        self._mem_reduction = mem_reduction
        self.testrun_overview_details = pdf.Story(temp.Style(), self._mem_reduction)  # story elements of developer with further info
        self.test_description = flow.TestDescription()
        self.summary_results_table = flow.SummaryResults()
        self.summary_testcases_table = flow.SummaryTestcases()

    def _create(self, story):  # pylint: disable=W0613
        # W0613: argument 'story' is used, but pylint does not find it
        '''
        creates the pdf story, called during `report.Build`

        :param story: pdf story to add paragraphs to
        :type story:  list of `pdf.Story` elements
        '''
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

        local_story.add_heading("Summary Results of Testcases", 1)
        local_story.append(self.summary_testcases_table)

        local_story.add_heading("Summary Results of Teststeps", 1)
        local_story.append(self.summary_results_table)

        # local_story.add_page_break()

        story += local_story.story


"""
CHANGE LOG:
-----------
$Log: template.py  $
Revision 1.2 2016/12/01 11:22:53CET Hospes, Gerd-Joachim (uidv8815) 
fix docu errors
Revision 1.1 2015/04/23 19:05:18CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/rep/pdf/fct_test/project.pj
Revision 1.7 2015/03/06 15:39:35CET Ellero, Stefano (uidw8660)
Implemented the optional parameter "mem_reduction" in the base class for all report templates (stk.rep.pdf.base.pdf.Story) to reduce the memory usage during a pdf report generation.
--- Added comments ---  uidw8660 [Mar 6, 2015 3:39:36 PM CET]
Change Package : 307809:1 http://mks-psad:7002/im/viewissue?selection=307809
Revision 1.6 2014/07/25 14:17:45CEST Hospes, Gerd-Joachim (uidv8815)
epydoc description and some pylint errors fixed
--- Added comments ---  uidv8815 [Jul 25, 2014 2:17:45 PM CEST]
Change Package : 246025:1 http://mks-psad:7002/im/viewissue?selection=246025
Revision 1.5 2014/07/23 12:52:03CEST Hospes, Gerd-Joachim (uidv8815)
allow additional story to test overview wth test_overview_details
--- Added comments ---  uidv8815 [Jul 23, 2014 12:52:03 PM CEST]
Change Package : 246025:1 http://mks-psad:7002/im/viewissue?selection=246025
Revision 1.4 2014/06/22 23:07:33CEST Hospes, Gerd-Joachim (uidv8815)
sync between templates and flowables,
algo_test.report generates perf, func and regr tests
algo_test template and flowable moved to perf_test
--- Added comments ---  uidv8815 [Jun 22, 2014 11:07:33 PM CEST]
Change Package : 241732:1 http://mks-psad:7002/im/viewissue?selection=241732
Revision 1.3 2014/06/05 16:24:16CEST Hospes, Gerd-Joachim (uidv8815)
final fixes after approval from Zhang Luo: cleanup and epydoc, pylint and pep8
--- Added comments ---  uidv8815 [Jun 5, 2014 4:24:17 PM CEST]
Change Package : 237743:1 http://mks-psad:7002/im/viewissue?selection=237743
Revision 1.2 2014/06/03 18:47:10CEST Hospes, Gerd-Joachim (uidv8815)
pylint fixes
Revision 1.1 2014/06/03 17:38:57CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/rep/pdf/fct_test/project.pj

"""
