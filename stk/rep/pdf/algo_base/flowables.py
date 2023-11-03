"""
stk/rep/pdf/algo_base/flowables
-------------------------------

**Specialized Base Flowables for the all Algo Reports:** like `AlgoTestReport` or `RegTestReport`

**Internal-API Interfaces**

    - `TableOfContents`
    - `TableOfFigures`
    - `TableOfTables`
    - `color_result` method

**User-API Interfaces**

    - `stk.rep` (complete package)

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.4 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/11/17 12:08:35CET $
"""
# Import Python Modules --------------------------------------------------------
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
import reportlab.platypus as plat
from reportlab.platypus.tableofcontents import TableOfContents as RepTOC

# Import STK Modules -----------------------------------------------------------
# allow unused imports of methods to stay backward compatible to stk < 2.3.31:
# pylint: disable=W0611
from ..base.flowables import build_table_header, build_table_row, html_str, url_str
from ....val.asmt import ValAssessmentStates
# from ....error import StkError # prepared for url_str to claim wrong link
from stk.util.helper import deprecated

pdfmetrics.registerFont(TTFont('Calibri', 'Calibri.ttf'))

# Defines ----------------------------------------------------------------------


# Functions --------------------------------------------------------------------
def color_result(result):
    """
    create html colored assessment string setting
      - PASSED to green
      - FAILED to red
      - NOT ASSESSED to orange
      - others to black

    :param result: sting to colour
    :type result:  string

    :returns: coloured string
    :rtype:   string with html markers
    """
    if result.upper() == ValAssessmentStates.PASSED.upper():
        return '<font color=green>' + ValAssessmentStates.PASSED.upper() + '</font>'
    elif result.upper() == ValAssessmentStates.FAILED.upper():
        return '<font color=red>' + ValAssessmentStates.FAILED.upper() + '</font>'
    elif result.upper() == ValAssessmentStates.NOT_ASSESSED.upper():
        return '<font color=orange>' + ValAssessmentStates.NOT_ASSESSED.upper() + '</font>'
    else:
        return '<font color=black>' + result + '</font>'


# Classes ----------------------------------------------------------------------
# these table classes normally provide only a _create method,
# some also an Append to add a row
class TableOfContents(RepTOC):
    """ general table of content class, base for table of figures and content """
    def __init__(self):
        RepTOC.__init__(self)

        self.toc_h1 = ParagraphStyle(name='Heading1', fontSize=14, fontName="Times-Bold", leftIndent=6)
        self.toc_h2 = ParagraphStyle(name='Heading2', fontSize=12, fontName="Times-Roman", leftIndent=12)
        self.toc_h3 = ParagraphStyle(name='Heading3', fontSize=11, fontName="Times-Roman", leftIndent=24)
        self.toc_h4 = ParagraphStyle(name='Heading4', fontSize=11, fontName="Times-Roman", leftIndent=32)

        self.levelStyles = [self.toc_h1, self.toc_h2, self.toc_h3, self.toc_h4]

    def _create(self):
        """ create the table with page break at the end """
        story = [plat.Paragraph("Table of Content", ParagraphStyle(name='Heading1', fontSize=0)), self,
                 plat.PageBreak()]

        return story


class TableOfFigures(TableOfContents):
    """ create the table of figures """
    figureTS = ParagraphStyle(name='FigureTitleStyle', fontName="Times-Roman", fontSize=10, leading=12)

    """ helper class to create a table of figures """
    def notify(self, kind, stuff):
        """ The notification hook called to register all kinds of events.
            Here we are interested in 'Figure' events only.
        """
        if kind == 'TOFigure':
            self.addEntry(*stuff)

    def _create(self):
        """ creation of the table with leading page break """
        story = [plat.PageBreak()]
        self.levelStyles = [self.figureTS]
        story.append(plat.Paragraph("Table of Figures", self.toc_h1))
        story.append(self)

        return story


class TableOfTables(TableOfContents):  # pylint: disable=W0142
    """ create table of tables """
    tableTS = ParagraphStyle(name='TableTitleStyle', fontName="Times-Roman", fontSize=10, leading=12)
    """ helper class to create a table of tables """
    def notify(self, kind, stuff):
        """ The notification hook called to register all kinds of events.
            Here we are interested in 'Table' events only.
        """
        if kind == 'TOTable':
            self.addEntry(*stuff)  # allow * magic here, W0142 disabled

    def _create(self):
        """ create the table with leading page break """
        story = [plat.PageBreak()]
        self.levelStyles = [self.tableTS]
        story.append(plat.Paragraph("Table of Tables", self.toc_h1))
        story.append(self)
        return story


"""
CHANGE LOG:
-----------
$Log: flowables.py  $
Revision 1.4 2016/11/17 12:08:35CET Hospes, Gerd-Joachim (uidv8815) 
fix pylint comments
Revision 1.3 2016/11/17 11:53:49CET Hospes, Gerd-Joachim (uidv8815)
pylint fixes, remove deprecated methods
Revision 1.2 2016/11/17 11:20:26CET Hospes, Gerd-Joachim (uidv8815)
move table formatter methods to pdf.base to support line break for columns in base.flowable.Table
Revision 1.1 2015/04/23 19:05:08CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/rep/pdf/algo_base/project.pj
Revision 1.9 2015/01/26 20:20:18CET Ellero, Stefano (uidw8660)
Removed all rep based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 26, 2015 8:20:18 PM CET]
Change Package : 296836:1 http://mks-psad:7002/im/viewissue?selection=296836
Revision 1.8 2015/01/20 17:01:30CET Mertens, Sven (uidv7805)
removing some more pylints
--- Added comments ---  uidv7805 [Jan 20, 2015 5:01:31 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.7 2015/01/20 16:57:42CET Mertens, Sven (uidv7805)
removing pep8
--- Added comments ---  uidv7805 [Jan 20, 2015 4:57:42 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.6 2014/07/28 19:17:20CEST Hospes, Gerd-Joachim (uidv8815)
fix tests steps only in one testrun, fix wrong PASSED/FAILED check
--- Added comments ---  uidv8815 [Jul 28, 2014 7:17:20 PM CEST]
Change Package : 246030:1 http://mks-psad:7002/im/viewissue?selection=246030
Revision 1.5 2014/07/24 10:36:50CEST Hospes, Gerd-Joachim (uidv8815)
add check for valid link in url_str
--- Added comments ---  uidv8815 [Jul 24, 2014 10:36:50 AM CEST]
Change Package : 250819:1 http://mks-psad:7002/im/viewissue?selection=250819
Revision 1.4 2014/06/17 16:21:09CEST Hospes, Gerd-Joachim (uidv8815)
print columns name and asmt only if filled in one test
--- Added comments ---  uidv8815 [Jun 17, 2014 4:21:09 PM CEST]
Change Package : 242882:1 http://mks-psad:7002/im/viewissue?selection=242882
Revision 1.3 2014/04/25 13:46:44CEST Hospes, Gerd-Joachim (uidv8815)
method url_str creating link with given name, url
--- Added comments ---  uidv8815 [Apr 25, 2014 1:46:45 PM CEST]
Change Package : 227491:1 http://mks-psad:7002/im/viewissue?selection=227491
Revision 1.2 2014/04/07 14:10:25CEST Hospes, Gerd-Joachim (uidv8815)
pep8 & pylint fixes after adding new packages and splitting some modules
--- Added comments ---  uidv8815 [Apr 7, 2014 2:10:25 PM CEST]
Change Package : 227496:1 http://mks-psad:7002/im/viewissue?selection=227496
Revision 1.1 2014/04/04 17:38:39CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision, parts copied from algo_test.flowables
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
stk/rep/pdf/algo_base/project.pj
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
