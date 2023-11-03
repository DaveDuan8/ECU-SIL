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
:author:        Leidenberger, Ralf

:version:       $Revision: 1.1 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/25 21:24:38CET $
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
from ....val.asmt import ValAssessmentStates

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
        # type: () -> object
        # type: () -> object
        # noinspection PyCallByClass
        RepTOC.__init__(self)

        self.toc_h1 = ParagraphStyle(name='Heading1', fontSize=14, fontName="Times-Bold", leftIndent=6)
        self.toc_h2 = ParagraphStyle(name='Heading2', fontSize=12, fontName="Times-Roman", leftIndent=12)
        self.toc_h3 = ParagraphStyle(name='Heading3', fontSize=11, fontName="Times-Roman", leftIndent=24)
        self.toc_h4 = ParagraphStyle(name='Heading4', fontSize=11, fontName="Times-Roman", leftIndent=32)

        self.levelStyles = [self.toc_h1, self.toc_h2, self.toc_h3, self.toc_h4]

    def create(self):
        """ create the table with page break at the end """
        story = [plat.Paragraph("Table of Content", ParagraphStyle(name='Heading1', fontSize=0)), self,
                 plat.PageBreak()]

        return story


class TableOfFigures(TableOfContents):
    """ create the table of figures """
    figureTS = ParagraphStyle(name='FigureTitleStyle', fontName="Times-Roman", fontSize=10, leading=12)

    def __init__(self):
        TableOfContents.__init__(self)

    """ helper class to create a table of figures """
    def notify(self, kind, stuff):
        """ The notification hook called to register all kinds of events.
            Here we are interested in 'Figure' events only.
        """
        if kind == 'TOFigure':
            self.addEntry(*stuff)

    # noinspection PyTypeChecker
    def create(self):
        """ creation of the table with leading page break """
        story = [plat.PageBreak()]
        self.levelStyles = [self.figureTS]
        story.append(plat.Paragraph("Table of Figures", self.toc_h1))
        story.append(self)

        return story


class TableOfTables(TableOfContents):  # pylint: disable=W0142
    """ create table of tables """
    tableTS = ParagraphStyle(name='TableTitleStyle', fontName="Times-Roman", fontSize=10, leading=12)

    def __init__(self):
        TableOfContents.__init__(self)

    """ helper class to create a table of tables """
    def notify(self, kind, stuff):
        """ The notification hook called to register all kinds of events.
            Here we are interested in 'Table' events only.
        """
        if kind == 'TOTable':
            self.addEntry(*stuff)  # allow * magic here, W0142 disabled

    # noinspection PyTypeChecker
    def create(self):
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
Revision 1.1 2020/03/25 21:24:38CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/rep/pdf/algo_base/project.pj
"""
