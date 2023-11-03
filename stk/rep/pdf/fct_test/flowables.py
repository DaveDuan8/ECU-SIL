"""
stk/rep/pdf/fct_test/flowables
-------------------------------

**Specialized Flowables for the FctTestReport:**

**Internal-API Interfaces**

    - `Overview`
    - `TestDescription`
    - `SummaryResults`
    - `SummaryTestcases`
    - `TableOfContents`
    - `TableOfFigures`
    - `TableOfTables`

**User-API Interfaces**

    - `stk.rep` (complete package)

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.6 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/12/01 11:22:29CET $
"""
# Import Python Modules --------------------------------------------------------
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import reportlab.platypus as plat
from reportlab.lib import colors
from reportlab.lib.units import cm

# Import STK Modules -----------------------------------------------------------
from ..base.flowables import TableBase, html_str, url_str, build_table_row, build_table_header, NORMAL_STYLE
from ..algo_base.flowables import color_result
from ....val.asmt import ValAssessmentStates

pdfmetrics.registerFont(TTFont('Calibri', 'Calibri.ttf'))
# Defines ----------------------------------------------------------------------

# Table column width definitions
SUMMARY_ID_WIDTH = 190
SUMMARY_NAME_WIDTH = 190
SUMMARY_RESULT_WIDTH = 64


# Functions --------------------------------------------------------------------

# Classes ----------------------------------------------------------------------
# these table classes normally provide only a _create method,
# some also an Append to add a row
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
        self.tr_id = None
        self.title = ""
        self.description = ""
        self.project = ""
        self.component = ""
        self.sim_name = ""
        self.sim_version = ""
        self.val_sw_version = ""
        self.collection = ""
        self.test_checkpoint = ""
        self.user_account = ""
        self.remarks = ""
        self._style = []
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
                 plat.Paragraph(html_str(self.title), NORMAL_STYLE)],
                [plat.Paragraph("Test Description ", NORMAL_STYLE),
                 plat.Paragraph(html_str(self.description), NORMAL_STYLE)],
                [plat.Paragraph("Project ", NORMAL_STYLE),
                 plat.Paragraph(html_str(self.project), NORMAL_STYLE)],
                [plat.Paragraph("Component ", NORMAL_STYLE),
                 plat.Paragraph(html_str(self.component), NORMAL_STYLE)],
                [plat.Paragraph("Simulation config", NORMAL_STYLE),
                 plat.Paragraph(html_str(self.sim_name), NORMAL_STYLE)],
                [plat.Paragraph("SIL version ", NORMAL_STYLE),
                 plat.Paragraph(html_str(self.sim_version), NORMAL_STYLE)],
                [plat.Paragraph("Valiation SW version", NORMAL_STYLE),
                 plat.Paragraph(html_str(self.val_sw_version), NORMAL_STYLE)],
                [plat.Paragraph("Collection ", NORMAL_STYLE),
                 plat.Paragraph(html_str(self.collection), NORMAL_STYLE)],
                [plat.Paragraph("User Account", NORMAL_STYLE),
                 plat.Paragraph(str(self.user_account), NORMAL_STYLE)],
                [plat.Paragraph("Testers Remarks", NORMAL_STYLE),
                 plat.Paragraph(html_str(self.remarks), NORMAL_STYLE)]]

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
        ''' add a new testcase to the list '''
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

        data = []
        data.append(build_table_header(['Testcase', 'Description']))

        for testcase in self._testcases:
            data.append([plat.Paragraph(html_str(testcase.name), NORMAL_STYLE),
                         plat.Paragraph(html_str(testcase.description), NORMAL_STYLE)])

        story = []

        table = plat.Table(data, style=self._style)

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
        :type  testcase: TestCase
        """

        for teststep in testcase.test_steps:
            if(teststep.test_result.upper() == ValAssessmentStates.PASSED.upper()):
                self._passed += 1
            elif(teststep.test_result.upper() == ValAssessmentStates.FAILED.upper()):
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
        :type  testcase:
        """

        if(testcase.test_result.upper() == ValAssessmentStates.PASSED.upper()):
            self._passed += 1
        elif(testcase.test_result.upper() == ValAssessmentStates.FAILED.upper()):
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


"""
CHANGE LOG:
-----------
$Log: flowables.py  $
Revision 1.6 2016/12/01 11:22:29CET Hospes, Gerd-Joachim (uidv8815) 
fix docu errors
Revision 1.5 2016/11/17 11:20:24CET Hospes, Gerd-Joachim (uidv8815)
move table formatter methods to pdf.base to support line break for columns in base.flowable.Table
Revision 1.4 2016/07/22 15:54:02CEST Hospes, Gerd-Joachim (uidv8815)
new fields sim version and val sw version
Revision 1.3 2016/05/09 11:00:17CEST Hospes, Gerd-Joachim (uidv8815)
add new column REMARKS to val.db and to pfd reports as new overview table row
Revision 1.2 2015/10/29 17:46:18CET Hospes, Gerd-Joachim (uidv8815)
add collection and sim_name to reports
- Added comments -  uidv8815 [Oct 29, 2015 5:46:19 PM CET]
Change Package : 390799:1 http://mks-psad:7002/im/viewissue?selection=390799
Revision 1.1 2015/04/23 19:05:17CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/rep/pdf/fct_test/project.pj
Revision 1.5 2014/06/24 17:01:27CEST Hospes, Gerd-Joachim (uidv8815)
move table caption below table, extend some epydoc
--- Added comments ---  uidv8815 [Jun 24, 2014 5:01:27 PM CEST]
Change Package : 243858:1 http://mks-psad:7002/im/viewissue?selection=243858
Revision 1.4 2014/06/22 23:07:26CEST Hospes, Gerd-Joachim (uidv8815)
sync between templates and flowables,
algo_test.report generates perf, func and regr tests
algo_test template and flowable moved to perf_test
--- Added comments ---  uidv8815 [Jun 22, 2014 11:07:26 PM CEST]
Change Package : 241732:1 http://mks-psad:7002/im/viewissue?selection=241732
Revision 1.3 2014/06/05 16:24:17CEST Hospes, Gerd-Joachim (uidv8815)
final fixes after approval from Zhang Luo: cleanup and epydoc, pylint and pep8
--- Added comments ---  uidv8815 [Jun 5, 2014 4:24:18 PM CEST]
Change Package : 237743:1 http://mks-psad:7002/im/viewissue?selection=237743
Revision 1.2 2014/06/03 18:47:08CEST Hospes, Gerd-Joachim (uidv8815)
pylint fixes
--- Added comments ---  uidv8815 [Jun 3, 2014 6:47:09 PM CEST]
Change Package : 237743:1 http://mks-psad:7002/im/viewissue?selection=237743
Revision 1.1 2014/06/03 17:38:56CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/rep/pdf/fct_test/project.pj
"""
