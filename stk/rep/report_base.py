"""
stk/db/db_sql.py
-------------------

This class provides basic reporting functionality.

This class should only be used as a base class for a report class.

:org:           Continental AG
:author:        Christoph Castell

:version:       $Revision: 1.3 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/12/01 11:22:31CET $
"""
# pylint: disable=C0103
# - import Python modules ---------------------------------------------------------------------------------------------
from os import path, getcwd, environ
from time import asctime
from sys import argv
from textwrap import wrap
from base64 import b64decode
from PIL import Image as PImage
import io
# ReportLab imports for PDF report generation.
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus.flowables import Flowable
from reportlab.platypus.doctemplate import BaseDocTemplate, PageTemplate, Frame
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Spacer, PageBreak, Table, Image, KeepTogether

# - defines -----------------------------------------------------------------------------------------------------------
# Page definitions
PAGE_LEFT_MARGIN = 1.8 * cm
PAGE_RIGHT_MARGIN = 1.8 * cm
PAGE_BOTTOM_MARGIN = 1.8 * cm
PAGE_WIDTH = A4[0]
PAGE_HEIGHT = A4[1]

DOC_STYLE_SHEET = getSampleStyleSheet()
TITLE_STYLE = DOC_STYLE_SHEET["Title"]
HEADING_STYLE1 = DOC_STYLE_SHEET["Heading1"]
HEADING_STYLE2 = DOC_STYLE_SHEET["Heading2"]
HEADING_STYLE3 = DOC_STYLE_SHEET["Heading3"]
NORMAL_STYLE = DOC_STYLE_SHEET["Normal"]
CODE_STYLE = DOC_STYLE_SHEET["Code"]

# Column Widths
COL_WIDTH_05 = 0.5 * inch
COL_WIDTH_08 = 0.8 * inch
COL_WIDTH_10 = 1.0 * inch
COL_WIDTH_15 = 1.5 * inch
COL_WIDTH_20 = 2.0 * inch
COL_WIDTH_25 = 2.5 * inch
COL_WIDTH_30 = 3.0 * inch
COL_WIDTH_35 = 3.5 * inch
COL_WIDTH_40 = 4.0 * inch
COL_WIDTH_45 = 4.5 * inch
COL_WRAP_10 = 15
COL_WRAP_20 = 30
COL_WRAP_30 = 45
COL_WRAP_35 = 52
COL_WRAP_40 = 58
COL_WRAP_45 = 62
SPACER_01 = 0.1 * inch
SPACER_02 = 0.2 * inch
SPACER_04 = 0.4 * inch

STR_PASSED = " PASSED "
STR_FAILED = " FAILED "
STR_SUSPECT = " TO BE VERIFIED "

# Test statistics definitions
TEST_STAT_RESULT_TYPES = "Type"
TEST_STAT_RESULT_STATES = "States"
TEST_STAT_VALUE = "Value"
TEST_STAT_DISTANCE = "Distance"
TEST_STAT_VELOCITY = "Velocity"
TEST_STAT_EXPECTED = "Expected"
TEST_STAT_UNIT = "Unit"

TEST_STAT_RESULTS = "Results"
TEST_STAT_RESULTS_DIST = "Total distance"
TEST_STAT_RESULTS_TIME = "Total time"
TEST_STAT_RESULTS_MEANVELO = "Total mean velocity"
TEST_STAT_RESULTS_FRAMES = "Total no frames"
TEST_STAT_RESULTS_FILES = "Files Processed"
TEST_STAT_ROAD_TYPE = "Road Type"
TEST_STAT_LIGHT_COND = "Light Conditions"
TEST_STAT_WEATHER_COND = "Weather Conditions"
TEST_STAT_COUNTRIES = "Countries"
TEST_STAT_ROAD_COND = "Road Conditions"
TEST_STAT_SPEED = "Speed"
TEST_STAT_NO_PED = "No Pedestrian"
TEST_STAT_DB_TYPE_STREET = "street"
TEST_STAT_DB_TYPE_LIGHT = "light"
TEST_STAT_DB_TYPE_ROADTYPE = "roadtype"
TEST_STAT_DB_TYPE_WEATHER = "weather"
TEST_STAT_DB_TYPE_NOPED = "noped"
TEST_STAT_DB_TYPE_COUNTRY = "country"
TEST_STAT_DB_TYPE_NO_PED = "noped"


# The draft statement to be written on the title page
DRAFT_STATEMENT = "DRAFT"
# The confidential levels and statements to be written on the title page
CONF_STATEMENT_UNCLASSIFIED = "- Unclassified -"
CONF_STATEMENT_CONFIDENTIAL = "- Confidential -"
CONF_STATEMENT_STRICTLY = "- Strictly Confidential -"

CONF_LEVEL_UNCLASSIFIED = 0
CONF_LEVEL_CONFIDENTIAL = 1
CONF_LEVEL_STRICTLY = 2

DEFAULT_OUTPUT_DIR_PATH = getcwd()

# Section types:
#
# SECTION_TYPE_NONE            - No section
# SECTION_TYPE_SECTION         - Section
# SECTION_TYPE_SUBSECTION      - Sub-section
# SECTION_TYPE_SUBSUBSECTION   - Sub-sub-section
SECTION_TYPE_NONE = -1
SECTION_TYPE_SECTION = 0
SECTION_TYPE_SUBSECTION = 1
SECTION_TYPE_SUBSUBSECTION = 2
# last section type
SECTION_TYPE_LAST_TYPE = SECTION_TYPE_SUBSUBSECTION

# Table caption
TABLE_CAPTION = "Table"
FIGURE_CAPTION = "Fig."

# Helper list of upper-case ASCII letters
ASCII_UPPER_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                       'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']

CONTI_LOGO_SIZE = (412, 77)
CONTI_CORP_LOGO = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAZwAAABNCAMAAACliiI1AAAABGdBTUEAALGPC/xhBQAAAwBQTFRF95Yt////AAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP5r+vQAAAAlwSFlzAAAOwgAADsIBFS"
    "hKgAAAABl0RVh0U29mdHdhcmUAUGFpbnQuTkVUIHYzLjUuNUmK/OAAAAchSURBVHhe7VzbltsgDEz//6e7iS+ANCMNmKTelD70dB0hpBndwNk+/qw"
    "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"
    "uhD4C5EBUsyx6PXXAAAAAElFTkSuQmCC"
)

# ====================================================================
# Module global variables
# ====================================================================

# Report auxiliary information
GLOB_TITLE = None
GLOB_AUTHOR = environ["USERNAME"]
GLOB_SUBJECT = None
GLOB_DATE = asctime()
GLOB_DRAFT = False
# Page definitions
GLOB_PAGE_HEIGHT = 25 * cm
GLOB_PAGE_WIDTH = 15 * cm
GLOB_PAGE_LEFT_MARGIN = 1.8 * cm
GLOB_PAGE_RIGHT_MARGIN = 1.8 * cm
GLOB_PAGE_TOP_MARGIN = 1.8 * cm
GLOB_PAGE_BOTTOM_MARGIN = 1.8 * cm


# - functions ---------------------------------------------------------------------------------------------------------
# ====================================================================
# Helper functions for page formating
# ====================================================================
def onFirstPage(canvas, doc):
    """This function is used to write the first page of the document.
    :param canvas: -- widget that provides structured graphics facilities
    :param doc: -- document template
    """
    canvas.saveState()
    if GLOB_TITLE is not None:
        canvas.setTitle(GLOB_TITLE)
    if GLOB_AUTHOR is not None:
        canvas.setAuthor(GLOB_AUTHOR)
    if GLOB_SUBJECT is not None:
        canvas.setSubject(GLOB_SUBJECT)
    if GLOB_DRAFT:
        canvas.setFillColor(colors.gray)
        canvas.setStrokeColor(colors.gray)
        canvas.setFont("Helvetica-Bold", 85)
        canvas.drawCentredString(2.75 * cm, 12 * cm, DRAFT_STATEMENT)
    canvas.restoreState()


def onLaterPages(canvas, doc):
    """This function is uses to write pages.
    :param canvas: -- widget that provides structured graphics facilities
    :param doc: -- document template
    """
    canvas.saveState()
    canvas.setLineWidth(0.2)
    canvas.line(GLOB_PAGE_LEFT_MARGIN, GLOB_PAGE_BOTTOM_MARGIN + 9,
                GLOB_PAGE_WIDTH - GLOB_PAGE_LEFT_MARGIN, GLOB_PAGE_BOTTOM_MARGIN + 9)
    canvas.setFont('Times-Roman', 9)
    canvas.drawString(GLOB_PAGE_LEFT_MARGIN, GLOB_PAGE_BOTTOM_MARGIN, "Page %d - %s, %s, %s" %
                      (doc.page, GLOB_TITLE, GLOB_AUTHOR, GLOB_DATE))
    canvas.restoreState()


def _doNothing(canvas, doc):  # pylint: disable=W0621,W0613,C0103
    """Dummy callback for onPage"""
    pass


# - classes -----------------------------------------------------------------------------------------------------------
class RotadedText(Flowable):
    """
    Rotates a text in a table cell.

    :deprecated: Please use `stk.rep.pdf.base` classes instead
    """
    def __init__(self, text):
        Flowable.__init__(self)
        self.text = text

    def draw(self):
        """ Draw the rotated text on the canvas. """
        canvas = self.canv
        canvas.rotate(90)
        fs = canvas._fontsize
        canvas.translate(1, -fs / 1.2)  # canvas._leading?
        canvas.drawString(0, 0, self.text)

    def wrap(self, aW, aH):  # pylint: disable=W0613
        """ overwrite, Draw the rotated text on the canvas.
        :param aW: Width to wrap. not used here
        :param aH: Height to wrap. not used here
        :return: Canvas info.
        """
        canv = self.canv
        fn, fs = canv._fontname, canv._fontsize
        return canv._leading, 1 + canv.stringWidth(self.text, fn, fs)


class RotatedParagraph(Flowable):
    """
    Rotates a paragraph in a table cell.

    :deprecated: Please use `stk.rep.pdf.base` classes instead
    """
    def __init__(self, text):
        Flowable.__init__(self)
        self.text = text

    def draw(self):  # pylint: disable=C0103
        """ Draw the rotated paragraph on the canvas. """
        canvas = self.canv
        canvas.rotate(90)
        canvas.translate(1, -self.height)
        self.text.canv = canvas
        try:
            self.text.draw()
        finally:
            del self.text.canv

    def wrap(self, aW, aH):
        """ Wrap the rotated paragraph.
        :param aW: Width to wrap.
        :param aH: Height to wrap.
        :return: Height and width.
        """
        ww, hw = self.text.wrap(aH, aW)
        self.width, self.height = hw, ww
        return hw, ww


# ====================================================================
# Report document template class
# ====================================================================
class BaseReportTemplate(BaseDocTemplate):
    """
    Defines base layout of reports

    :deprecated: Please use `stk.rep.pdf.base` classes instead
    """

    _invalidInitArgs = ('pageTemplates',)

    def __init__(self, filename, **kw):
        self.allowSplitting = 0
        BaseDocTemplate.__init__(*(self, filename), **kw)
        template = PageTemplate('normal', [Frame(GLOB_PAGE_LEFT_MARGIN, GLOB_PAGE_TOP_MARGIN,
                                                 GLOB_PAGE_WIDTH, GLOB_PAGE_HEIGHT, id='F1')])
        self.addPageTemplates(template)

    def handle_pageBegin(self):
        """override base method to add a change of page template after the firstpage.
        """
        self._handle_pageBegin()
        self._handle_nextPageTemplate('Later')

    def afterFlowable(self, flowable):
        """Registers TOC entries."""
        if flowable.__class__.__name__ == 'Paragraph':
            text = flowable.getPlainText()
            style = flowable.style.name
            if style == 'Heading1':
                key = 'h1-%s' % self.seq.nextf('heading1')
                self.canv.bookmarkPage(key)
                self.notify('TOCEntry', (0, text, self.page, key))
                self.canv.addOutlineEntry(text, key, 0)
            if style == 'Heading2':
                key = 'h2-%s' % self.seq.nextf('heading2')
                self.canv.bookmarkPage(key)
                self.notify('TOCEntry', (1, text, self.page, key))
                self.canv.addOutlineEntry(text, key, 1, closed=1)
            if style == 'Heading3':
                key = 'h3-%s' % self.seq.nextf('heading3')
                self.canv.bookmarkPage(key)
                self.notify('TOCEntry', (2, text, self.page, key))
                self.canv.addOutlineEntry(text, key, 2, closed=1)

    def multiBuild(self, flowables, onFirstPage=_doNothing, onLaterPages=_doNothing, canvasmaker=canvas.Canvas):
        """Build the document using the flowables. Annotate the first page using the onFirstPage
            function and later pages using the onLaterPages function.
        """
        self._calc()  # in case we changed margins sizes etc
        frameT = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='normal')
        self.addPageTemplates([PageTemplate(id='First', frames=frameT, onPage=onFirstPage, pagesize=self.pagesize),
                               PageTemplate(id='Later', frames=frameT, onPage=onLaterPages, pagesize=self.pagesize)])
        if onFirstPage is _doNothing and hasattr(self, 'onFirstPage'):
            self.pageTemplates[0].beforeDrawPage = self.onFirstPage
        if onLaterPages is _doNothing and hasattr(self, 'onLaterPages'):
            self.pageTemplates[1].beforeDrawPage = self.onLaterPages
        BaseDocTemplate.multiBuild(self, flowables, canvasmaker=canvasmaker)


# ====================================================================
# Report class
# ====================================================================
class BaseReportGenerator(object):
    """
    Base class for report generation.

    :deprecated: Please use `stk.rep.pdf.base` classes instead
    """
    def __init__(self, out_filename, title, author, subject=None,
                 date=asctime(), generator=argv[0],
                 generator_rev="$Revision: 1.3 $",
                 confidential_level=CONF_LEVEL_STRICTLY, draft=False, additional_title_info=None):
        """Initialize new report.
        :param out_filename: The file name of the report.
        :param title: The report title.
        :param date: The report date.
        :param author: The name of the report author.
        :param generator: The name of the generator software.
        :param generator_rev: The generator software revision string.
        :param confidential: Set True, if the document shall have a confidential statement.
        :param draft: Set True, if the document shall have a draft statement.
        :param additional_title_info: Additional information displayed in the title page table. Dictionary that maps
        item name to the value.
        """
        global GLOB_TITLE, GLOB_AUTHOR, GLOB_DATE, GLOB_SUBJECT, GLOB_DRAFT

        # the current section type
        self._current_section_type = SECTION_TYPE_NONE
        self._appendix = False
        # the section, table, figure numbers
        self._section_numbers = [0, 0, 0]
        self._table_number = 1
        self._fig_number = 1
        # the report output file
        self._out_filename = out_filename
        # the report settings
        self._title = title
        self._author = author
        self._subject = subject
        self._date = date
        self._generator = generator
        self._generator_rev = generator_rev
        self._confidential_level = confidential_level
        self._draft = draft
        if additional_title_info:
            self._additional_title_info = additional_title_info
        else:
            self._additional_title_info = {}
        # global settings
        GLOB_TITLE = self._title
        GLOB_AUTHOR = self._author
        GLOB_DATE = self._date
        GLOB_SUBJECT = self._subject
        GLOB_DRAFT = self._draft
        # maximum text width
        self._max_text_width = 70

    def Build(self):
        """Build the actual report file
        """
        pass

    def Appendix(self):
        """Starts the appendix"""
        self._appendix = True
        for idx in range(SECTION_TYPE_LAST_TYPE + 1):
            self._section_numbers[idx] = 0

    def Section(self, sectionName, pageBreak):  # pylint: disable=W0613
        """Start a new section (aka chapter)
        :param pageBreak: when set True, performs a page break
        :param sectionName: The name of the section (unused)
        """
        self._GotoNextSection(SECTION_TYPE_SECTION)

    def Subsection(self, sectionName):  # pylint: disable=W0613
        """Start a new subsection
        :param sectionName: name of subsection.
        """
        self._GotoNextSection(SECTION_TYPE_SUBSECTION)

    def Subsubsection(self, sectionName):  # pylint: disable=W0613
        """Start a new sub-subsection
        :param sectionName: name of sub-subsection.
        """
        self._GotoNextSection(SECTION_TYPE_SUBSUBSECTION)

    def Paragraph(self, text):
        """start a new paragraph
        :param text: The paragraph text
        """
        pass

    def InsertObject(self, obj):
        """Insert a new object
        :param obj: The object to insert.
        """
        pass

    # ====================================================================
    # Internal helper methods
    # ====================================================================

    def _GotoNextSection(self, section_type):
        """Goto next section type. Handles all counters
        :param section_type: The started section type.
        """
        self._current_section_type = section_type
        # increment section counter
        for idx in range(section_type, SECTION_TYPE_LAST_TYPE + 1):
            if idx == section_type:
                self._section_numbers[idx] = self._section_numbers[idx] + 1
            else:
                self._section_numbers[idx] = 0
        # reset figure and table counter
        self._table_number = 1
        self._fig_number = 1

    def _BuildSectionString(self, section_name):
        """Builds the section string
        :return: section string for current section
        """
        return "%s %s" % (self._BuildSectionNumberString(), section_name)

    def _BuildSectionNumberString(self):
        """Builds a string that represents the current section numbers
        :return: section number string
        """
        number_str = ""
        if self._current_section_type > SECTION_TYPE_NONE:
            for idx in range(self._current_section_type + 1):
                if self._appendix and (idx == 0):
                    number_str = number_str + ("%s" % ASCII_UPPER_LETTERS[self._section_numbers[idx] - 1])
                else:
                    number_str = number_str + ("%d" % self._section_numbers[idx])
                if idx < self._current_section_type:
                    number_str = number_str + '.'
        # done
        return number_str


class BaseReportLabGenerator(BaseReportGenerator):
    """
    Base class for report generation using ReportLab

    :deprecated: Please use `stk.rep.pdf.base` classes instead
    """
    def __init__(self, out_filename, title, author, subject=None, date=asctime(),
                 generator=argv[0], generator_rev="$Revision: 1.3 $",
                 confidential_level=CONF_LEVEL_STRICTLY, draft=False, additional_title_info=None):
        """Initialize new report.
        :param out_filename: The file name of the report.
        :param title: The report title.
        :param date: The report date.
        :param author: The name of the report author.
        :param generator: The name of the generator software.
        :param generator_rev: The generator software revision string.
        :param confidential_level: Set True, if the document shall have a confidential statement.
        :param draft: Set True, if the document shall have a draft statement.
        :param additional_title_info: Additional information displayed in the title page table. Dictionary that maps
        item name to the value.
        """
        global GLOB_PAGE_HEIGHT, GLOB_PAGE_WIDTH

        if additional_title_info is None:
            additional_title_info = {}
        BaseReportGenerator.__init__(self, out_filename, title, author, subject,
                                     date, generator, generator_rev, confidential_level,
                                     draft, additional_title_info)
        # create actual report
        self._doc = BaseReportTemplate(self._out_filename)
        self._report = []

        self.h1 = ParagraphStyle(name='Heading1', fontSize=16,
                                 fontName="Times-Bold",
                                 leading=22)
        self.notoc_h1 = ParagraphStyle(name='NoTOCHeading1', fontSize=16,
                                       fontName="Times-Bold",
                                       leading=22)
        self.toc_h1 = ParagraphStyle(name='Heading1',
                                     fontSize=14,
                                     fontName="Times-Bold")
        self.h2 = ParagraphStyle(name='Heading2', fontSize=14,
                                 fontName="Times-Roman",
                                 leading=18)
        self.notoc_h2 = ParagraphStyle(name='NoTOCHeading2',
                                       fontSize=14,
                                       fontName="Times-Roman",
                                       leading=18)
        self.toc_h2 = ParagraphStyle(name='Heading2', fontSize=12,
                                     fontName="Times-Roman",
                                     leftIndent=12)
        self.h3 = ParagraphStyle(name='Heading3', fontSize=12,
                                 fontName="Times-Roman",
                                 leading=12)
        self.notoc_h3 = ParagraphStyle(name='NoTOCHeading3', fontSize=12,
                                       fontName="Times-Roman",
                                       leading=12)
        self.toc_h3 = ParagraphStyle(name='Heading3', fontSize=11,
                                     fontName="Times-Roman",
                                     leftIndent=32)

    def Build(self):
        """Build the actual report file
        """
        BaseReportGenerator.Build(self)
        self._doc.multiBuild(self._report, onFirstPage=onFirstPage, onLaterPages=onLaterPages)

    def MakeTitle(self):
        """Create title page.
        """

        # add logo
        self._report.append(Image(io.BytesIO(CONTI_CORP_LOGO),
                            width=CONTI_LOGO_SIZE[0] * 0.5, height=CONTI_LOGO_SIZE[1] * 0.5))
        self._report.append(Spacer(1, 2 * cm))

        # add title
        doc_style_sheet = getSampleStyleSheet()
        style = doc_style_sheet["Title"]
        title_str = Paragraph(self._title, style)
        self._report.append(title_str)
        self._report.append(Spacer(1, 2 * cm))

        # confidence statement
        conf_stmt = None
        if self._confidential_level == CONF_LEVEL_UNCLASSIFIED:
            conf_stmt = CONF_STATEMENT_UNCLASSIFIED
        elif self._confidential_level == CONF_LEVEL_CONFIDENTIAL:
            conf_stmt = CONF_STATEMENT_CONFIDENTIAL
        else:
            conf_stmt = CONF_STATEMENT_STRICTLY
        self._report.append(Paragraph('<para alignment="center">%s</para>' % conf_stmt, style))
        self._report.append(Spacer(1, 3 * cm))

        # collect table data
        style = doc_style_sheet["Normal"]
        data = []
        if self._date is not None:
            data.append(["Date", self._date])
        if self._author is not None:
            data.append(["Author", Paragraph("<br/>".join(wrap(self._author, self._max_text_width)), style)])
        if self._generator is not None:
            data.append(["Generator", Paragraph("<br/>".join(wrap(self._generator, self._max_text_width)), style)])
        if self._generator_rev is not None:
            data.append(["Generator Revision", self._generator_rev])

        # add the additional title information
        for key in self._additional_title_info:
            data.append([str(key), Paragraph("<br/>".join(wrap(str(self._additional_title_info[key]),
                                                               self._max_text_width)), style)])
        # set table
        table = Table(data, colWidths=[100, 300], style=[('GRID', (0, 0), (-1, -1), 1.0, colors.black),
                                                         ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey)])
        self._report.append(table)

        self._report.append(PageBreak())

    def MakeTableOfContent(self):
        """Create TOC page.
        """
        toc = TableOfContents()
        toc.levelStyles = [self.toc_h1, self.toc_h2, self.toc_h3]
        self._report.append(Paragraph("Table of Content", self.notoc_h1))
        self._report.append(toc)

    def Appendix(self):
        """Starts the appendix"""
        BaseReportGenerator.Appendix(self)
        # write appendix
        self._report.append(PageBreak())
        self._report.append(Paragraph("Appendix", self.notoc_h1))

        # logging.info("Appendix")

    def Section(self, sectionName, pageBreak=True):
        """Start a new section (performs a page break)

        :param sectionName: The name of the section.
        """
        BaseReportGenerator.Section(self, sectionName, pageBreak)

        if pageBreak:
            self._report.append(PageBreak())
        title_str = Paragraph(self._BuildSectionString(sectionName), self.h1)
        self._report.append(title_str)

        # logging.info("S '%s'" % section_name)

    def Subsection(self, sectionName):
        """Start a new subsection

        :param sectionName: The name of the subsection.
        """
        self._report.append(Spacer(1, 2 * cm))
        BaseReportGenerator.Subsection(self, sectionName)
        title_str = Paragraph(self._BuildSectionString(sectionName), self.h2)
        self._report.append(title_str)

        # logging.info("SS '%s'" % subsection_name)

    def Subsubsection(self, sectionName):
        """Start a new sub-subsection

        :param sectionName: The name of the sub-subsection.
        """
        self._report.append(Spacer(1, 2 * cm))
        BaseReportGenerator.Subsubsection(self, sectionName)
        title_str = Paragraph(self._BuildSectionString(sectionName), self.h3)
        self._report.append(title_str)

        # logging.info("SSS '%s'" % subsubsection_name)

    def PageBreak(self):
        """Performs a page break
        """
        self._report.append(PageBreak())

    def Paragraph(self, text):
        """Start a new paragraph

        :param text: The paragraph text
        """
        BaseReportGenerator.Paragraph(self, text)

        doc_style_sheet = getSampleStyleSheet()
        style = doc_style_sheet["Normal"]
        self._report.append(Paragraph(text, style))

    def InsertObject(self, obj):
        """Insert a new object

        :param obj: The object to insert.
        """
        BaseReportGenerator.InsertObject(self, obj)
        self._report.append(obj)

    def InsertTable(self, table_name, table, spacer=True):
        """Inserts a table into the report at the current position (Appends the table to the end of the report.
        Appends space below table.)

        :param table_name: The name of the table.
        :param table: The actual table to insert.
        :param spacer: flag to add free space below the table
        """
        if table_name is not None:
            # logging.info("T '%s'" % table_name)
            table_name = self.ReplaceHTMLChars(table_name)
            doc_style_sheet = getSampleStyleSheet()
            self._report.append(Paragraph("<b>%s %s.%d</b>: %s" % (TABLE_CAPTION, self._BuildSectionNumberString(),
                                                                   self._table_number, table_name),
                                          doc_style_sheet["Normal"]))
            self._table_number += 1
        self._report.append(table)
        if spacer is True:
            self._report.append(Spacer(1, 1 * cm))

    def InsertFigure(self, figure_name, figure):
        """Inserts a figure into the report at the current position. (Appends the table to the end of the report.
        Appends space below table.)

        :param figure_name: The name of the figure.
        :param figure: The actual table to insert.
        """
        flowables = [Spacer(1, 1 * cm)]
        if figure_name is not None:
            # logging.info("F '%s'" % figure_name)
            figure_name = self.ReplaceHTMLChars(figure_name)
            doc_style_sheet = getSampleStyleSheet()
            flowables.append(Paragraph("<b>%s %s.%d</b>: %s" % (FIGURE_CAPTION, self._BuildSectionNumberString(),
                                                                self._fig_number, figure_name),
                                       doc_style_sheet["Normal"]))
            self._fig_number = self._fig_number + 1

        flowables.append(figure)
        flowables.append(Spacer(1, 1 * cm))
        self._report.append(KeepTogether(flowables))

    # ====================================================================
    # Internal helper methods
    # ====================================================================

    def GetImageDimensions(self, img_filename):
        """Get the usable page are for an image

        :param img_filename: The file name of the image file.
        :return: Returns the usable page width and height for the image.
        """
        try:
            avail_width = (GLOB_PAGE_WIDTH)  # - GLOB_PAGE_LEFT_MARGIN - GLOB_PAGE_RIGHT_MARGIN)
            avail_height = (GLOB_PAGE_HEIGHT)  # - GLOB_PAGE_TOP_MARGIN - GLOB_PAGE_BOTTOM_MARGIN)

            img = PImage.open(path.abspath(img_filename))
            img_size = img.size

            img_width = float(img_size[0])
            img_height = float(img_size[1])

            use_width = img_width
            use_height = img_height

            if avail_width < img_width:
                use_width = min(img_width, avail_width)
                use_height = img_height * use_width / img_width
            else:
                use_height = min(img_height, avail_height)
                use_width = img_width * use_height / img_height
        except:
            # logging.exception("GetImageDimensions failed: IMG='%s'" % img_filename)
            raise
        # Done
        return use_width, use_height

    def ReplaceHTMLChars(self, text):
        """Replace HTML Characters, e.g. needed for Paragraphs"""

        # replace html characters
        text = text.replace('&', '&amp')
        text = text.replace('<', '&lt')
        text = text.replace('>', '&gt')

        return text


# ====================================================================
# Validation report class
# ====================================================================
class PdfReport(object):
    """
    Base class for report generation in all validation projects

    :deprecated: Please use `stk.rep.pdf.base.pdf` instead
    """
    def __init__(self, report_title,
                 outfile_path_name,
                 report_subject=None,
                 date=asctime(),
                 generator=argv[0],
                 generator_rev="$Revision: 1.3 $",
                 confidential_level=CONF_LEVEL_STRICTLY,
                 make_title=True,
                 make_table_of_content=False,
                 additional_info=None):
        """Constructor"""
        if additional_info is None:
            additional_info = {}
        self.__report_outfile_pathname = path.join(DEFAULT_OUTPUT_DIR_PATH, outfile_path_name)

        # create report generator
        self.__report = BaseReportLabGenerator(self.__report_outfile_pathname, report_title,
                                               environ["USERNAME"], report_subject, date, generator,
                                               generator_rev.partition(':')[2].strip('$ '),
                                               confidential_level=confidential_level,
                                               additional_title_info=additional_info)

        if make_title is True:
            self.__report.MakeTitle()

        if make_table_of_content is True:
            self.__report.MakeTableOfContent()

    def BuildReport(self):
        """build the report"""
        self.__report.Build()

    # ====================================================================
    # Getters/setters
    # ====================================================================

    def SetReportFilePath(self, outfile_path_name):
        """Set the output path name

        :param outfile_path_name: The name of the output file path.
        """
        self.__report_outfile_pathname = outfile_path_name

    def GetReportFilePath(self):
        """Returns the output path name

        :return: name of the output path.
        """
        return self.__report_outfile_pathname

    # ====================================================================
    # Report generation
    # ====================================================================

    def wrap_paragraph(self, text, font_size):
        """ Wrap Paragraph
        """
        return Paragraph(text.replace("&", "&amp;"), ParagraphStyle({'wordWrap': True, 'fontSize': font_size}))

    def format_paragraph(self, text, color, style="Normal"):
        """ Format Paragraph
        """
        doc_style_sheet = getSampleStyleSheet()
        cell_style = doc_style_sheet[style]
        return Paragraph("<b><font face=\"times\" color=\"%s\">%s</font></b>" % (color, text), cell_style)

    def __BuildTableHeader(self, column_name_list):
        """Builds a ReportLab table header a given column descriptor list.

        :param column_name_list: List of column names.
        :return: ReportLab table header
        """
        doc_style_sheet = getSampleStyleSheet()
        hdr_style = doc_style_sheet["Normal"]
        header_list = []
        for column_name in column_name_list:
            header_list.append(Paragraph("<b>%s</b>" % column_name, hdr_style))
        return header_list

    def AddSection(self, sectionName, pageBreak=True):
        """ add a new top level section (aka chapter)

        :param sectionName: name of section
        :param pageBreak: begins the new chapter with a new page
        """
        self.__report.Section(sectionName, pageBreak)

    def AddSubSection(self, sectionName):
        """ add a new sub-section, e.g. 1.2, 1.3, etc

        :param sectionName: name of 2nd level section
        """
        self.__report.Subsection(sectionName)

    def AddSubSubSection(self, sectionName):
        """ add a new sub-sub-section, e.g. 1.2.1, 1.2.2, etc
        :param sectionName: name of 3rd level section
        """
        self.__report.Subsubsection(sectionName)

    def AddPageBreak(self):
        """ add a page break
        """
        self.__report.PageBreak()

    def InsertTable(self, tableName, columnNameList, valueList, colWidths=None, topHeader=True, spacer=True, **kwargs):
        """Builds a ReportLab table.

        :param tableName: name of table
        :param columnNameList: list of column names (aka header) to use from input
        :type  columnNameList: [key1, key3, ...]
        :param valueList: list of values to enter into table
        :type  valueList: [{key1: value1a, key2: value2a, key3: value3a, ...},
                           {key1: value1b, key2: value2b, key3: value3b, ...}]
        :param colWidths: widths of columns
        :param topHeader: True if table header are on top, False when on left side
        :param spacer: flag to add free space below the table
        :return: ReportLab table for columns and results
        """

        if "style" not in kwargs:
            kwargs["style"] = [('GRID', (0, 0), (-1, -1), 1.0, colors.black),
                               ('BACKGROUND', (0, 0), (-1, 0) if topHeader else (0, -1), colors.lavender)]

        # TODO: why forcing to set columnNameList? could do: None = keys from dict?

        data = [self.__BuildTableHeader(columnNameList)]
        for value in valueList:
            data_row = []
            for column_name in columnNameList:
                if column_name in value:
                    data_row.append(value[column_name])
            data.append(data_row)

        if colWidths is not None:
            return self.__report.InsertTable(tableName, Table(data, colWidths=colWidths, repeatRows=1, **kwargs),
                                             spacer)
        else:
            return self.__report.InsertTable(tableName, Table(data, repeatRows=1, **kwargs), spacer)

    def InsertImage(self, imageDesc, image):
        """Inserts an image into the report

        :param imageDesc: name or description to be added below the image
        :param image: The image itself.
        """
        if image is not None:
            return self.__report.InsertFigure(imageDesc, image)

        return None

    def InsertParagraph(self, text):
        """ insert a new paragraph

        :param text: paragraph text
        """
        self.__report.Paragraph(text)


"""
CHANGE LOG:
-----------
$Log: report_base.py  $
Revision 1.3 2016/12/01 11:22:31CET Hospes, Gerd-Joachim (uidv8815) 
fix docu errors
Revision 1.2 2015/12/07 14:29:25CET Mertens, Sven (uidv7805)
removing pep8 errors
Revision 1.1 2015/04/23 19:05:01CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/
    04_Engineering/01_Source_Code/stk/rep/project.pj
Revision 1.39 2014/11/06 14:29:25CET Mertens, Sven (uidv7805)
object update
--- Added comments ---  uidv7805 [Nov 6, 2014 2:29:26 PM CET]
Change Package : 278229:1 http://mks-psad:7002/im/viewissue?selection=278229
Revision 1.38 2014/07/29 18:25:36CEST Hospes, Gerd-Joachim (uidv8815)
fix pylint error W0102 and some others
--- Added comments ---  uidv8815 [Jul 29, 2014 6:25:37 PM CEST]
Change Package : 250927:1 http://mks-psad:7002/im/viewissue?selection=250927
Revision 1.37 2014/05/12 09:48:03CEST Hecker, Robert (heckerr)
Added new JobSimFeature.
--- Added comments ---  heckerr [May 12, 2014 9:48:03 AM CEST]
Change Package : 236158:1 http://mks-psad:7002/im/viewissue?selection=236158
Revision 1.36 2014/03/28 10:42:16CET Hecker, Robert (heckerr)
Added pylint exception for old style Method-Names.
--- Added comments ---  heckerr [Mar 28, 2014 10:42:16 AM CET]
Change Package : 228098:1 http://mks-psad:7002/im/viewissue?selection=228098
Revision 1.35 2014/03/26 13:28:10CET Hecker, Robert (heckerr)
Added python 3 changes.
--- Added comments ---  heckerr [Mar 26, 2014 1:28:10 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.34 2014/03/25 08:59:32CET Hecker, Robert (heckerr)
Adaption to python 3.
--- Added comments ---  heckerr [Mar 25, 2014 8:59:32 AM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.33 2014/02/28 12:49:27CET Hecker, Robert (heckerr)
Removed some deprecated warnings, which was wrong.
--- Added comments ---  heckerr [Feb 28, 2014 12:49:27 PM CET]
Change Package : 221473:1 http://mks-psad:7002/im/viewissue?selection=221473
Revision 1.32 2014/02/24 17:53:44CET Hospes, Gerd-Joachim (uidv8815)
reinsert warnings because onFirstPage, onLaterPages could not be removed
--- Added comments ---  uidv8815 [Feb 24, 2014 5:53:45 PM CET]
Change Package : 219922:1 http://mks-psad:7002/im/viewissue?selection=219922
Revision 1.31 2014/02/24 16:18:29CET Hospes, Gerd-Joachim (uidv8815)
deprecated classes/methods/functions removed (planned for 2.0.9)
--- Added comments ---  uidv8815 [Feb 24, 2014 4:18:29 PM CET]
Change Package : 219922:1 http://mks-psad:7002/im/viewissue?selection=219922
Revision 1.30 2014/01/21 17:43:23CET Skerl, Anne (uid19464)
*change InsertTable() of PdfReport: add spacer parameter, add documentation
of input format
--- Added comments ---  uid19464 [Jan 21, 2014 5:43:23 PM CET]
Change Package : 198254:13 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.29 2013/07/10 09:14:10CEST Raedler, Guenther (uidt9430)
- added deprecated warnings
--- Added comments ---  uidt9430 [Jul 10, 2013 9:14:10 AM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.28 2013/04/29 12:03:22CEST Mertens, Sven (uidv7805)
color change on table header,
more description for epydoc
--- Added comments ---  uidv7805 [Apr 29, 2013 12:03:23 PM CEST]
Change Package : 179495:6 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.27 2013/04/26 15:20:46CEST Mertens, Sven (uidv7805)
nearly final image, as I was told, "future in motion" should
only be used for advertisements...,
using b64encode only, image can be opened several times,
as StringIO needs to be seeked again.
--- Added comments ---  uidv7805 [Apr 26, 2013 3:20:47 PM CEST]
Change Package : 179495:6 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.25 2013/04/19 13:30:09CEST Hecker, Robert (heckerr)
reverted to revision 1.19. Added pylint improvements.
--- Added comments ---  heckerr [Apr 19, 2013 1:30:09 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.24 2013/04/19 13:03:56CEST Hecker, Robert (heckerr)
Reverted to Revision 1.19. (excluding epydoc comments)
--- Added comments ---  heckerr [Apr 19, 2013 1:03:56 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.23 2013/04/15 12:08:44CEST Mertens, Sven (uidv7805)
small bugfixes
--- Added comments ---  uidv7805 [Apr 15, 2013 12:08:44 PM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.22 2013/04/12 14:39:58CEST Mertens, Sven (uidv7805)
inverting image, bugfixing StringIO problem
Revision 1.21 2013/04/11 10:17:01CEST Mertens, Sven (uidv7805)
fixing some pylint errors
--- Added comments ---  uidv7805 [Apr 11, 2013 10:17:02 AM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.20 2013/04/11 09:35:04CEST Mertens, Sven (uidv7805)
inserting official logo from http://c-inside.conti.de/intranet/c-inside/
Surf_Regions/en_US/corporation/communications/040_departments/
20_internal_communications/060_products/ci_online/strategy/hidden/
2013_03_01_neue_unternehmensmarke_en.html,
removing some pylint warnings / errors
--- Added comments ---  uidv7805 [Apr 11, 2013 9:35:05 AM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.19 2013/04/10 09:32:31CEST Mertens, Sven (uidv7805)
changing to new logo valid from May, 1st,
extra JPG image not needed any longer
--- Added comments ---  uidv7805 [Apr 10, 2013 9:32:31 AM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.18 2013/04/03 08:02:21CEST Mertens, Sven (uidv7805)
pylint: minor error, warnings fix
--- Added comments ---  uidv7805 [Apr 3, 2013 8:02:21 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.17 2013/03/28 15:48:29CET Mertens, Sven (uidv7805)
fixing origin of Image
Revision 1.16 2013/03/28 15:25:15CET Mertens, Sven (uidv7805)
pylint: W0311 (indentation), string class
Revision 1.15 2013/03/28 14:43:05CET Mertens, Sven (uidv7805)
pylint: resolving some R0904, R0913, R0914, W0107
--- Added comments ---  uidv7805 [Mar 28, 2013 2:43:06 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.14 2013/03/28 13:31:25CET Mertens, Sven (uidv7805)
minor pep8
Revision 1.13 2013/03/27 13:51:23CET Mertens, Sven (uidv7805)
pylint: bugfixing and error reduction
--- Added comments ---  uidv7805 [Mar 27, 2013 1:51:24 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.12 2013/03/22 09:20:53CET Mertens, Sven (uidv7805)
last pep8 update on non-trailing white space errors
Revision 1.11 2013/03/22 08:24:38CET Mertens, Sven (uidv7805)
aligning bulk of files again for peping 8
--- Added comments ---  uidv7805 [Mar 22, 2013 8:24:38 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.10 2013/03/19 13:13:37CET Raedler, Guenther (uidt9430)
- changed some comments (reported by Anne)
- remved unused method _doNothing() (reported by Anne)
--- Added comments ---  uidt9430 [Mar 19, 2013 1:13:37 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.9 2013/03/13 11:00:09CET Raedler, Guenther (uidt9430)
- merged from cgeb_report_generator.py (1.35)
  * conti image on first page
  * hyperlinks in the table of content
  * fixed some dublicate imports
--- Added comments ---  uidt9430 [Mar 13, 2013 11:00:09 AM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.8 2013/03/12 16:51:12CET Raedler, Guenther (uidt9430)
- integrated stk_report_generator (1.9) and fixed pep8 failures
--- Added comments ---  uidt9430 [Mar 12, 2013 4:51:12 PM CET]
Change Package : 174667:1 http://mks-psad:7002/im/viewissue?selection=174667
Revision 1.7 2013/03/01 15:44:28CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 1, 2013 3:44:28 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.6 2013/02/28 08:12:30CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:30 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.5 2013/02/27 17:55:13CET Hecker, Robert (heckerr)
Removed all E000 - E200 Errors regarding Pep8.
--- Added comments ---  heckerr [Feb 27, 2013 5:55:14 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2013/02/27 16:20:03CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 27, 2013 4:20:03 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/26 20:15:43CET Raedler, Guenther (uidt9430)
- Updates after Pep8 Styleguides
--- Added comments ---  uidt9430 [Feb 26, 2013 8:15:43 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.2 2013/02/13 12:50:10CET Raedler, Guenther (uidt9430)
- fixed wrong import
- moved some defines from validation_global_def into base_report
--- Added comments ---  uidt9430 [Feb 13, 2013 12:50:11 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/02/11 10:53:09CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/rep/project.pj
------------------------------------------------------------------------------
-- From etk/vpc Archive
------------------------------------------------------------------------------
Revision 1.20 2012/07/30 14:20:14CEST Ahmed-EXT, Zaheer (uidu7634)
Added _GetHeading() method
- to create hyperlinked/bookmarked headings
  for table of content and outline navigation bar
Added ValDocTemplate class
- to support Table of Content generation on report build
- to support outline navigation bar
Added ValTableOfContent class
- for table of content feature in Base Validation Report
--- Added comments ---  uidu7634 [Jul 30, 2012 2:20:18 PM CEST]
Change Package : 146627:1 http://mks-psad:7002/im/viewissue?selection=146627
Revision 1.19 2012/07/06 15:00:30CEST Spruck, Jochen (spruckj)
Move collection distance summary calculation to val
--- Added comments ---  spruckj [Jul 6, 2012 3:00:31 PM CEST]
Change Package : 98074:5 http://mks-psad:7002/im/viewissue?selection=98074
Revision 1.18 2012/05/24 15:48:40CEST Sampat-EXT, Janani Vasumathy (uidu5218)
- added functionarz in the report module to make the first line hightlighting optional
--- Added comments ---  uidu5218 [May 24, 2012 3:48:41 PM CEST]
Change Package : 90317:1 http://mks-psad:7002/im/viewissue?selection=90317
Revision 1.17 2012/04/17 17:40:43CEST Sampat-EXT, Janani Vasumathy (uidu5218)
- class for generating overall summary table
- class for generating testcase summary
--- Added comments ---  uidu5218 [Apr 17, 2012 5:40:43 PM CEST]
Change Package : 110628:1 http://mks-psad:7002/im/viewissue?selection=110628
$Log: validation_report_baRevision 1.16 2012/04/13 09:38:57CEST Spruck, Jochen (spruckj)
$Log: validation_report_ba- Sort test statistics
$Log: validation_report_ba- Additional collums could be added to test statistics table
$Log: validation_report_ba--- Added comments ---  spruckj [Apr 13, 2012 9:38:58 AM CEST]
$Log: validation_report_baChange Package : 98074:2 http://mks-psad:7002/im/viewissue?selection=98074
Revision 1.15 2012/03/20 11:33:47CET Spruck, Jochen (spruckj)
Add recording driven distances for different types to the base report
--- Added comments ---  spruckj [Mar 20, 2012 11:33:47 AM CET]
Change Package : 98074:2 http://mks-psad:7002/im/viewissue?selection=98074
Revision 1.13 2011/12/07 11:02:31CET Sampat-EXT, Janani Vasumathy (uidu5218)
- added another level in the function write_s_n
--- Added comments ---  uidu5218 [Dec 7, 2011 11:02:31 AM CET]
Change Package : 88149:1 http://mks-psad:7002/im/viewissue?selection=88149
Revision 1.12 2011/11/18 13:44:50CET Castell Christoph (uidt6394) (uidt6394)
Removed "DRAFT" statement from report.
--- Added comments ---  uidt6394 [Nov 18, 2011 1:44:50 PM CET]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.11 2011/10/20 13:03:31CEST Raedler Guenther (uidt9430) (uidt9430)
- fixed printout error in report
--- Added comments ---  uidt9430 [Oct 20, 2011 1:03:31 PM CEST]
Change Package : 67780:6 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.10 2011/09/09 08:18:35CEST Spruck Jochen (spruckj) (spruckj)
Add some option to the create table functions (rotating heading, fontsize, ...)
--- Added comments ---  spruckj [Sep 9, 2011 8:18:35 AM CEST]
Change Package : 69027:1 http://mks-psad:7002/im/viewissue?selection=69027
Revision 1.9 2011/09/02 13:55:39CEST Castell Christoph (uidt6394) (uidt6394)
Added COL_WRAP_30.
--- Added comments ---  uidt6394 [Sep 2, 2011 1:55:39 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.8 2011/09/02 11:36:56CEST Castell Christoph (uidt6394) (uidt6394)
Fixed database_filename bug and changed test_design to collection.
Revision 1.7 2011/09/01 12:25:03CEST Raedler Guenther (uidt9430) (uidt9430)
-- support vertical and horizontal headline formating in a table
--- Added comments ---  uidt9430 [Sep 1, 2011 12:25:03 PM CEST]
Change Package : 62766:1 http://mks-psad:7002/im/viewissue?selection=62766
Revision 1.6 2011/08/11 10:49:50CEST Raedler Guenther (uidt9430) (uidt9430)
-- added suspect result
-- check for None
--- Added comments ---  uidt9430 [Aug 11, 2011 10:49:50 AM CEST]
Change Package : 67780:5 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.5 2011/08/04 10:30:06CEST Raedler Guenther (uidt9430) (uidt9430)
-- extended generic report table
--- Added comments ---  uidt9430 [Aug 4, 2011 10:30:06 AM CEST]
Change Package : 67780:5 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.4 2011/08/01 09:23:36CEST Castell Christoph (uidt6394) (uidt6394)
Fixed comments, added text rotation, added global defs import.
--- Added comments ---  uidt6394 [Aug 1, 2011 9:23:36 AM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.3 2011/07/26 14:58:36CEST Raedler Guenther (uidt9430) (uidt9430)
-- add generic function to handle sting fields
-- extended _writeconfiguration
--- Added comments ---  uidt9430 [Jul 26, 2011 2:58:36 PM CEST]
Change Package : 67780:5 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.2 2011/07/22 08:42:28CEST Raedler Guenther (uidt9430) (uidt9430)
-- moved methos to correct class
-- changed logo path
--- Added comments ---  uidt9430 [Jul 22, 2011 8:42:28 AM CEST]
Change Package : 67780:5 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.1 2011/07/21 16:38:42CEST Raedler Guenther (uidt9430) (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/EM_EnvironmentModel/05_Testing/05_Test_Environment/algo/em_req_test/valf_tests/vpc/project.pj
Revision 1.6 2011/07/01 13:06:44CEST Castell Christoph (uidt6394) (uidt6394)
Added functionality Page X of Y.
--- Added comments ---  uidt6394 [Jul 1, 2011 1:06:44 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.5 2011/06/01 15:38:37CEST HeldC (HeldC)
Added import for blockage report.
--- Added comments ---  HeldC [Jun 1, 2011 3:40:31 PM CEST]
Change Package : 69035:1 http://mks-psad:7002/im/viewissue?selection=69035
Revision 1.4 2011/04/13 14:29:09CEST Castell Christoph (uidt6394) (uidt6394)
Added configuration function to em_report_base.
--- Added comments ---  uidt6394 [Apr 13, 2011 2:29:09 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.3 2011/03/31 08:57:27CEST Castell Christoph (uidt6394) (uidt6394)
Fixed relative path to Continental logo.
--- Added comments ---  uidt6394 [Mar 31, 2011 8:57:27 AM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.2 2011/03/30 13:47:11CEST Castell Christoph (uidt6394) (uidt6394)
Changed width of COL_WRAP_45 define.
Revision 1.1 2011/03/28 10:47:21CEST Castell Christoph (uidt6394) (uidt6394)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/EM_EnvironmentModel/05_Testing/05_Test_Environment/algo/em_req_test/valf_tests/em/common/project.pj

"""
