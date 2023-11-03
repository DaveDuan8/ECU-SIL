"""
stk/rep/pdf.py
-------------------

This class provides basic reporting functionality.

:org:           Continental AG
:author:        Sven Mertens

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:00CEST $
"""

# pylint: disable=R0201,E1101,C0103

__all__ = ['Pdf', 'RotatedText']

# Import Python Modules -------------------------------------------------------
from os import path as oPath, environ, makedirs
from sys import maxint
from textwrap import wrap
from time import asctime
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Spacer, PageBreak, Table, Image, KeepTogether, TableStyle
from reportlab.platypus.doctemplate import BaseDocTemplate, PageTemplate, NextPageTemplate, Frame
from reportlab.platypus.flowables import Flowable
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot, ScatterPlot
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.textlabels import Label
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.graphics.shapes import Drawing, String
import warnings

# Import STK Modules ----------------------------------------------------------
from stk.rep.pdf_defs import CONTI_CORP_LOGO, DRAFT_STATEMENT, GLOB_PAGE_BOTTOM_MARGIN, CONTI_LOGO_SIZE, \
    GLOB_PAGE_TOP_MARGIN, CONF_LEVEL_STRICTLY, SECTION_TYPE_NONE, DEFAULT_OUTPUT_DIR_PATH, CONF_STATEMENT, \
    SECTION_TYPE_LAST_TYPE, ASCII_UPPER_LETTERS, TABLE_CAPTION, FIGURE_CAPTION, FIRST_PAGE_LEFT_MARGIN, \
    GLOB_PAGE_HEIGHT, GLOB_PAGE_WIDTH, TITLE_STYLE, NORMAL_STYLE, PDF_CHART_COLORS, PDF_LINE_MARKERS
from stk.util.helper import deprecation

# Defines ---------------------------------------------------------------------
pdfmetrics.registerFont(TTFont('Calibri', 'Calibri.ttf'))
HTMLREPL = {"\r": "", "\n": "<br/>"}

# Functions -------------------------------------------------------------------


# Classes -------------------------------------------------------------------------------------------------------------

class PlaceHolder(object):  # pylint: disable=R0903
    """placeholder for a paragraph to be inserted afterwards.
    Well, tables and images are going through here as well
    """
    def __init__(self, idx, sect, desc, obj):
        """store details"""
        self.idx = idx
        self.sect = sect
        self.desc = desc
        self.obj = obj


class PdfBase(BaseDocTemplate):  # pylint: disable=R0904
    """Defines base layout of reports
    Don't use. Pdf class below is your user interface!

    :deprecated: Please use `stk.rep.pdf.base` classes instead
    """

    _invalidInitArgs = ('pageTemplates',)

    def __init__(self, filename, headerInfo, **kw):
        self.allowSplitting = 0
        try:
            makedirs(oPath.dirname(filename))
        except:  # pylint: disable=W0702
            pass
        BaseDocTemplate.__init__(self, filename, **kw)
        # apply(BaseDocTemplate.__init__, (self, filename), **kw)
        f0 = Frame(FIRST_PAGE_LEFT_MARGIN, GLOB_PAGE_TOP_MARGIN, GLOB_PAGE_WIDTH, GLOB_PAGE_HEIGHT, id='F0')
        f1 = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='F1')  # pylint: disable=E1101
        fL = Frame(self.leftMargin, self.bottomMargin, self.height, self.width, id='FL')  # pylint: disable=E1101
        self.addPageTemplates([PageTemplate('first', [f0], onPage=self.onFirstPage,
                                            pagesize=self.pagesize),  # pylint: disable=E1101
                               PageTemplate('portrait', [f1], onPage=self.onLaterPages,
                                            pagesize=self.pagesize),  # pylint: disable=E1101
                               PageTemplate('landscape', [fL], onPage=self.onLaterPages,
                                            pagesize=(self.pagesize[1], self.pagesize[0]))])  # pylint: disable=E1101
        self.numPages = 1
        self._lastnumPages = 2

        self._headerInfo = headerInfo

    def afterFlowable(self, flowable):
        self.numPages = max(self.canv.getPageNumber(), self.numPages)

        "Registers TOC entries."
        if flowable.__class__.__name__ == 'Paragraph':
            text = flowable.getPlainText()
            style = flowable.style.name
            if style == 'Heading1':
                key = 'h1-%s' % self.seq.nextf('heading1')
                self.canv.bookmarkPage(key)
                self.notify('TOCEntry', (0, text, self.page, key))
                self.canv.addOutlineEntry(text, key, 0)
            elif style == 'Heading2':
                key = 'h2-%s' % self.seq.nextf('heading2')
                self.canv.bookmarkPage(key)
                self.notify('TOCEntry', (1, text, self.page, key))
                self.canv.addOutlineEntry(text, key, 1)
            elif style == 'Heading3':
                key = 'h3-%s' % self.seq.nextf('heading3')
                self.canv.bookmarkPage(key)
                self.notify('TOCEntry', (2, text, self.page, key))
                self.canv.addOutlineEntry(text, key, 2)
            elif style == 'TableTitleStyle':
                key = 't-%s' % self.seq.nextf('tabletitlestyle')
                self.canv.bookmarkPage(key)
                self.notify('TOTable', (1, text, self.page, key))
                self.canv.addOutlineEntry(text, key, 1)
            elif style == 'FigureTitleStyle':
                key = 'f-%s' % self.seq.nextf('figuretitlestyle')
                self.canv.bookmarkPage(key)
                self.notify('TOFigure', (1, text, self.page, key))
                self.canv.addOutlineEntry(text, key, 1)

    def multiBuild(self, flowables, canvasmaker=canvas.Canvas):
        """Build the document using the flowables. Annotate the first page using the onFirstPage
            function and later pages using the onLaterPages function.
        """
        self._calc()  # in case we changed margins sizes etc
        return BaseDocTemplate.multiBuild(self, flowables, canvasmaker=canvasmaker)

    def _allSatisfied(self):
        """ Called by multi-build - are all cross-references resolved? """
        if self._lastnumPages < self.numPages:
            return 0
        return BaseDocTemplate._allSatisfied(self)

    def pageIndexString(self):
        """Return page index string for the footer."""
        if self.page < self.numPages:
            self._lastnumPages += 1

        return 'page %(current_page)d of %(total_pages)d' % {'current_page': self.page, 'total_pages': self.numPages}

    def onFirstPage(self, canv, doc):  # pylint: disable=W0613
        """This function is used to write the first page of the document.
        :param canv: -- widget that provides structured graphics facilities
        :param doc: -- document template
        """
        canv.saveState()
        canv.setTitle(self._headerInfo[0])  # title
        if self._headerInfo[1] is not None:  # author
            canv.setAuthor(self._headerInfo[1])
        if self._headerInfo[2] is not None:  # subject
            canv.setSubject(self._headerInfo[2])
        if self._headerInfo[4] == "draft":
            canv.setFillColor(colors.gray)
            canv.setStrokeColor(colors.gray)
            canv.setFont("Helvetica-Bold", 85)
            canv.drawCentredString(10.5 * cm, 8 * cm, DRAFT_STATEMENT)
        canv.restoreState()
        self.handle_nextPageTemplate('portrait')

    def onLaterPages(self, canv, doc):
        """This function is uses to write pages.
        :param canv: -- widget that provides structured graphics facilities
        :param doc: -- document template
        """
        canv.saveState()
        portrait = self.pageTemplate.id == "portrait"

        pl = Paragraph("Continental<br/>ADAS",
                       ParagraphStyle(name="plb", fontSize=8, fontName="Calibri", alignment=TA_CENTER,
                                      leading=(12 if portrait else 8)))
        pc = Paragraph("COPYRIGHT. CONFIDENTIAL AND PROPRIETARY. ALL RIGHTS RESERVED - Property of Continental AG. "
                       "This information carrier and the information it contains are the property of Continental AG. "
                       "Any reproduction, disclosure or use of either is prohibited without the prior written consent "
                       "of Continental AG. Continental AG reserves worldwide all rights also in the case of industrial"
                       " property rights being granted. The same provisions apply to any oral communications related"
                       " thereto accordingly.",
                       ParagraphStyle(name="pcb", fontSize=6, fontName="Calibri", alignment=TA_CENTER, leading=5))
        ww = (10 if portrait else 18.7) * cm
        _, hh = pc.wrap(ww, doc.bottomMargin)
        pr = Paragraph("%s" % (doc.pageIndexString()),  # doc.page
                       ParagraphStyle(name="pr", fontSize=8, fontName="Calibri", alignment=TA_CENTER))
        tf = Table([[pl, pc, pr]], [3.2 * cm, ww, 3.2 * cm], ident="bottomTable")
        tf.setStyle(TableStyle([('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                ('BOX', (0, 0), (-1, -1), 0.25, colors.black), ]))
        tf.wrapOn(canv, ww, hh)
        tf.drawOn(canv, doc.leftMargin, GLOB_PAGE_BOTTOM_MARGIN - 0.2 * cm)

        pl = Image(BytesIO(CONTI_CORP_LOGO), 4 * cm, 4 * cm * CONTI_LOGO_SIZE[1] / float(CONTI_LOGO_SIZE[0]))
        ps = ParagraphStyle(name="pst", fontSize=14, FontName="Calibri", alignment=TA_CENTER)
        pc = Paragraph("Algorithm Test Results", ps)
        # pr = Paragraph(self._headerInfo[4], ps)
        tf = Table([[pl, pc]], [4.2 * cm, (12.2 if portrait else 20.9) * cm], ident="topTable")
        tf.setStyle(TableStyle([('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ]))
        tf.wrapOn(canv, 10 * cm, hh)
        tf.drawOn(canv, doc.leftMargin, (GLOB_PAGE_HEIGHT + 2.4 * cm) if portrait else (GLOB_PAGE_WIDTH + 3.5 * cm))
        canv.restoreState()


class TableOfFigures(TableOfContents):
    """
    helper class to create a table of figure

    :deprecated: Please use `stk.rep.pdf.base` classes instead
    """
    def notify(self, kind, stuff):
        """ The notification hook called to register all kinds of events.
            Here we are interested in 'Figure' events only.
        """
        if kind == 'TOFigure':
            self.addEntry(*stuff)  # pylint: disable=W0142


class TableOfTables(TableOfContents):
    """
    helper class to create a table of tables

    :deprecated: Please use `stk.rep.pdf.base` classes instead
    """
    def notify(self, kind, stuff):
        """ The notification hook called to register all kinds of events.
            Here we are interested in 'Figure' events only.
        """
        if kind == 'TOTable':
            self.addEntry(*stuff)  # pylint: disable=W0142


class RotatedText(Flowable):
    """"
    rotates a text intended for a table cell

    :deprecated: Please use `stk.rep.pdf.base` classes instead
    """
    def __init__(self, para):
        """take over either a Paragraph or raw text"""
        Flowable.__init__(self)
        self.para = para
        if type(self.para) != str and self.para.text.startswith('<b>') and self.para.text.endswith('</b>'):
            self.para.text = self.para.text[3:-4]
            if not self.para.style.fontName.endswith('-Bold'):
                self.para.style.fontName += '-Bold'

    def draw(self):
        """overload"""
        canv = self.canv
        canv.saveState()
        canv.rotate(90)
        if type(self.para) == str:
            canv.drawString(0, -3, self.para)
        else:
            canv.setFont(self.para.style.fontName, self.para.style.fontSize, self.para.style.leading)
            canv.drawString(0, -3, self.para.getPlainText())
        canv.restoreState()

    def wrap(self, aW, aH):  # pylint: disable=W0613
        """overload"""
        canv = self.canv
        if type(self.para) == str:
            return canv._leading, canv.stringWidth(self.para)  # pylint: disable=W0212
        else:
            return canv._leading, canv.stringWidth(self.para.getPlainText(),  # pylint: disable=W0212
                                                   self.para.style.fontName, self.para.style.fontSize)


class Pdf(object):  # pylint: disable=R0902
    """Base class for report generation in all validation projects"""
    def __init__(self, outfileName, reportTitle, *args, **kwargs):
        """Initialize new report.
        :param outfileName: The file name of the report.
        :param reportTitle: The report title.
        :param reportSubject: The subject of document.
        :param date: The report date.
        :param generator: deprecated
        :param generator_rev: deprecated
        :param confidential_level: Set True, if the document shall have a confidential statement.
        :param draft: wether 'draft' or 'released' should be written on header
        :param makeTitle: wether to create a title page or not
        :param makeTableOfContent: wether to create a table of content page or not
        :param makeTableOfFigures: wether to create a table of figures (images) or not
        :param makeTableOfTables: wether to create a table of tables or not
        :param additional_title_info: Additional information displayed in the title page table. Dictionary that maps
        item name to the value.
        """
        # the current section type
        self._currentSectionType = SECTION_TYPE_NONE
        self._appendix = False
        # the section, table, figure numbers
        self._sectionNumbers = [0, 0, 0]
        # the report settings
        subj = args[0] if len(args) > 0 else kwargs.pop('reportSubject', None)
        date = args[1] if len(args) > 1 else kwargs.pop('date', asctime())

        # generator and generatorRev is ignored as agreed (old args 2 and 3)
        if 'generator' in kwargs or 'generatorRev' in kwargs or len(args) > 2:
            deprecation("don't use generator and generatorRev option any longer, it's deprecated!")

        self._confidentialLevel = args[4] if len(args) > 4 else kwargs.pop('confidentialLevel', CONF_LEVEL_STRICTLY)
        draft = "draft" if (args[5] if len(args) > 5 else kwargs.pop('draft', False)) else "released"
        self._headerInfo = [self.replaceHTMLChars(i) for i in [reportTitle, environ["USERNAME"], subj, date, draft]]

        self._additionalTitleInfo = args[10] if len(args) > 10 else kwargs.pop('additional_info', {})

        # maximum text width
        self._maxTextWidth = 70

        # create actual report
        self._doc = PdfBase(oPath.join(DEFAULT_OUTPUT_DIR_PATH, outfileName), self._headerInfo)
        self._report = []

        self.header = [ParagraphStyle(name='Heading1', fontSize=16, fontName="Times-Bold", leading=22),
                       ParagraphStyle(name='Heading2', fontSize=14, fontName="Times-Roman", leading=18),
                       ParagraphStyle(name='Heading3', fontSize=12, fontName="Times-Roman", leading=12)]

        self.notoc_h1 = ParagraphStyle(name='NoTOCHeading1', fontSize=16, fontName="Times-Bold", leading=22)
        self.toc_h1 = ParagraphStyle(name='Heading1', fontSize=14, fontName="Times-Bold", leftIndent=6)
        self.notoc_h2 = ParagraphStyle(name='NoTOCHeading2', fontSize=14, fontName="Times-Roman", leading=18)
        self.toc_h2 = ParagraphStyle(name='Heading2', fontSize=12, fontName="Times-Roman", leftIndent=12)
        self.notoc_h3 = ParagraphStyle(name='NoTOCHeading3', fontSize=12, fontName="Times-Roman", leading=12)
        self.toc_h3 = ParagraphStyle(name='Heading3', fontSize=11, fontName="Times-Roman", leftIndent=32)

        # False = portrait, True = landscape
        self._orientation = False

        self.figureTS = ParagraphStyle(name='FigureTitleStyle', fontName="Times-Roman", fontSize=10, leading=12)
        self.tableTS = ParagraphStyle(name='TableTitleStyle', fontName="Times-Roman", fontSize=10, leading=12)

        if (args[6] if len(args) > 6 else kwargs.pop('makeTitle', True)):
            self._makeTitle()

        if (args[7] if len(args) > 7 else kwargs.pop('makeTableOfContent', True)):
            self.makeTableOfContent()

        self._doTableOfFigures = args[8] if len(args) > 8 else kwargs.pop('makeTableOfFigures', False)
        self._doTableOfTables = args[9] if len(args) > 9 else kwargs.pop('makeTableOfTables', False)

        self._reportBuild = False

    def close(self):
        """clean up if neccessary"""
        if not self._reportBuild:
            self.buildReport()

    def _makeTitle(self):
        """Create title page.
        """
        # add logo
        self._report.append(Image(BytesIO(CONTI_CORP_LOGO),
                            width=CONTI_LOGO_SIZE[0] * 0.5, height=CONTI_LOGO_SIZE[1] * 0.5))
        self._report.append(Spacer(1, 2 * cm))

        # add title
        title_str = Paragraph(self._headerInfo[0], TITLE_STYLE)
        self._report.append(title_str)
        self._report.append(Spacer(1, 2 * cm))

        # confidence statement
        self._report.append(Paragraph('<para alignment="center">%s</para>' %
                                      CONF_STATEMENT[self._confidentialLevel], TITLE_STYLE))
        self._report.append(Spacer(1, 3 * cm))

        # collect table data
        data = []
        if self._headerInfo[3] is not None:
            data.append(["Date", self._headerInfo[3]])
        if self._headerInfo[1] is not None:
            data.append(["Author", Paragraph("<br/>".join(wrap(self._headerInfo[1], self._maxTextWidth)),
                                             NORMAL_STYLE)])

        # add the additional title information
        for key in self._additionalTitleInfo:
            data.append([str(key), Paragraph("<br/>".join(wrap(str(self._additionalTitleInfo[key]),
                                                               self._maxTextWidth)), NORMAL_STYLE)])
        # set table
        table = Table(data, colWidths=[100, 300], style=[('GRID', (0, 0), (-1, -1), 1.0, colors.black),
                                                         ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey)])
        self._report.append(table)

        self._report.append(PageBreak())

    def makeTableOfContent(self):
        """create a TOC page
        """
        toc = TableOfContents()
        toc.levelStyles = [self.toc_h1, self.toc_h2, self.toc_h3]
        # needs to be 'invisible' as otherwise would be double header
        # this is just needed to get the TOC added to the bookmark page
        self._report.append(Paragraph("Table of Content", ParagraphStyle(name='Heading1', fontSize=0)))
        self._report.append(toc)

    def makeTableOfFigures(self):
        """create a TOI page (-> table of content)
        """
        self._report.append(PageBreak())
        tof = TableOfFigures()
        tof.levelStyles = [self.figureTS]
        self._report.append(Paragraph("Table of Figures", self.toc_h1))
        self._report.append(tof)
        self._doTableOfFigures = False

    def makeTableOfTables(self):
        """create a TOT page (-> table of content)
        """
        self._report.append(PageBreak())
        tot = TableOfTables()
        tot.levelStyles = [self.tableTS]
        self._report.append(Paragraph("Table of Tables", self.toc_h1))
        self._report.append(tot)
        self._doTableOfTables = False

    #====================================================================
    # Report generation
    #====================================================================

    # build the report
    def buildReport(self):
        """Build the actual report file
        """
        if self._doTableOfFigures:
            self.makeTableOfFigures()
        if self._doTableOfTables:
            self.makeTableOfTables()

        self._reportBuild = True

        # replace placeholders by real things
        repLen = len(self._report)
        i = 0
        currSection = None
        tableNumber = 0
        imageNumber = 0
        while i < repLen:
            if isinstance(self._report[i], PlaceHolder):
                if self._report[i].obj is None:  # wasn't replaced ;-(
                    self._report.pop(i)
                    repLen -= 1

                elif isinstance(self._report[i], Paragraph):  # insert text
                    self._report[i] = self._report[i].obj

                else:
                    if currSection != self._report[i].sect:
                        currSection = self._report[i].sect
                        tableNumber = 0
                        imageNumber = 0

                    if isinstance(self._report[i].obj, Table):  # format the table
                        tblPH = self._report[i]
                        self._report[i] = Spacer(1, 1 * cm)
                        self._report.insert(i, tblPH.obj)
                        repLen += 1

                        tableNumber += 1
                        if tblPH.desc is not None:
                            tp = Paragraph("<b>%s %s.%d</b>: %s" % (TABLE_CAPTION, currSection, tableNumber,
                                                                    self.replaceHTMLChars(tblPH.desc)), self.tableTS)
                            tp.keepWithNext = True

                            self._report.insert(i, tp)
                            repLen += 1

                    elif isinstance(self._report[i].obj, Flowable):  # format the image
                        imgPH = self._report[i]

                        imgFlow = [Spacer(1, 1 * cm), imgPH.obj]
                        imageNumber += 1
                        if imgPH.desc is not None:
                            imgFlow.append(Paragraph("<b>%s %s.%d</b>: %s" % (FIGURE_CAPTION, currSection,
                                                                              imageNumber, imgPH.desc),
                                                     # self.replaceHTMLChars(imgPH.desc)
                                                     self.figureTS))
                            imgFlow.append(Spacer(1, 1 * cm))

                        self._report[i] = KeepTogether(imgFlow)

            i += 1

        return self._doc.multiBuild(self._report)
        # , onFirstPage=self._doc.onFirstPage, onLaterPages=self._doc.onLaterPages)

    def replaceHTMLChars(self, text):
        """Replace HTML Characters, e.g. needed for Paragraphs"""
        return escape(text, HTMLREPL) if type(text) == str else text

    def addSection(self, sectionName, pageBreak=True, level=0):
        """ add a new top level section (aka chapter)
        :param sectionName: name of section
        :param pageBreak: begins the new chapter with a new page
        :param level: at which level the new section should be inserted
        """
        self._currentSectionType = level
        # increment section counter
        for idx in xrange(level, SECTION_TYPE_LAST_TYPE + 1):
            if idx == level:
                self._sectionNumbers[idx] += 1
            else:
                self._sectionNumbers[idx] = 0

        if pageBreak:
            self._report.append(PageBreak())

        if level > 0:
            self._report.append(Spacer(1, 1.5 * cm))

        self._report.append(Paragraph("%s %s" % (self._BuildSectionNumberString(), sectionName), self.header[level]))

    def addSubSection(self, sectionName):
        """ add a new sub-section, e.g. 1.2, 1.3, etc
        :param sectionName: name of 2nd level section
        """
        self.addSection(sectionName, False, 1)

    def addSubSubSection(self, sectionName):
        """ add a new sub-sub-section, e.g. 1.2.1, 1.2.2, etc
        :param sectionName: name of 3rd level section
        """
        self.addSection(sectionName, False, 2)

    def addPageBreak(self):
        """ add a page break
        """
        self._report.append(PageBreak())

    def append(self, paragraph):
        """just appends the raw paragraph
        This could be used to build up a private reportlab component to be inserted directly here,
        what Pdf class is not capable to do by now or not supporting.
        :param paragraph: a reportlab component to append
        """
        self._report.append(paragraph)

    def insertSpace(self, centiMeters):
        """inserts some centi meters of space
        :param centiMeters: the amount of cm to be used
        """
        self._report.append(Spacer(1, centiMeters * cm))

    def _BuildSectionNumberString(self):
        """Builds a string that represents the current section numbers
        :return: section number string
        """
        number_str = ""
        if self._currentSectionType > SECTION_TYPE_NONE:
            for idx in xrange(self._currentSectionType + 1):
                if self._appendix and (idx == 0):
                    number_str += ("%s" % ASCII_UPPER_LETTERS[self._sectionNumbers[idx] - 1])
                else:
                    number_str += ("%d" % self._sectionNumbers[idx])
                if idx < self._currentSectionType:
                    number_str += '.'
        # done
        return number_str

    def insertTable(self, tableName, columnNameList, valueList, **kwargs):
        """Builds a ReportLab table.
        :param tableName: name of table
        :param columnNameList: list of column names (aka header) to use
        :param valueList: list of values to enter into table
        :param colWidths: widths of columns
        :param topHeader: True when table header background should be done
        :param insert: False when table should be returned instead of being inserted
        :return: ReportLab table for columns and results
        """
        style = kwargs.pop('style', [])
        if "GRID" not in [i[0] for i in style]:
            style.append(('GRID', (0, 0), (-1, -1), 1.0, colors.black))
        if kwargs.pop('topHeader', True):
            style.insert(0, ('BACKGROUND', (0, 0), (-1, 0), colors.lavender))
        kwargs['style'] = style

        if type(columnNameList[0]) == str:
            data = [[Paragraph("<b>%s</b>" % colName, NORMAL_STYLE) for colName in columnNameList]]
        else:
            data = [columnNameList]

        if type(valueList[0]) == dict:
            for value in valueList:
                data_row = []
                for column_name in columnNameList:
                    if column_name in value:
                        data_row.append(value[column_name])
                data.append(data_row)
        else:
            data.extend(valueList)

        insert = kwargs.pop('insert', True)

        table = Table(data, colWidths=kwargs.pop('colWidths', None), repeatRows=1, **kwargs)

        if insert:
            self._report.append(PlaceHolder(None, self._BuildSectionNumberString(), tableName, table))
        else:
            return table

    def insertImage(self, imageDesc, image, **kwargs):
        """inserts an image into the report
        :param imageDesc: name or description to be added below the image
        :param image: The image itself.
        :param insert: False when image should be returned instead of being inserted
        """
        if not isinstance(image, Image) and type(image) == str and oPath.isfile(image):
            image = Image(image)

        if kwargs.pop('insert', True):
            self._report.append(PlaceHolder(None, self._BuildSectionNumberString(), imageDesc, image))
        else:
            return image

    def placeHolder(self, idx, desc, obj):
        """insert a Placeholder for later insertion,
        if obj ist still None when building final PDF, nothing will be inserted.
        :param idx: placeholder index (incease it on your own outside)
        :param desc: a descriptive name for e.g. an table or image to be named
        :param obj: the object, can be a text (paragraph), an image or a table
        """
        if obj is None:
            self._report.append(PlaceHolder(idx, self._BuildSectionNumberString(), desc, obj))
        else:
            for i in xrange(len(self._report)):
                if isinstance(self._report[i], PlaceHolder) and self._report[i].idx == idx:
                    self._report[i].desc = desc
                    self._report[i].obj = obj
                    break

    def insertParagraph(self, text, **kwargs):
        """insert a new paragraph
        :param text: paragraph text
        """
        prgf = Paragraph(text, kwargs.pop("style", NORMAL_STYLE))

        if kwargs.pop('insert', True):
            self._report.append(prgf)
        else:
            return prgf

    def changeOrientation(self, mode=None):
        """ changes from portrait to landscape and vice versa
        :param mode: can be 'portrait' or 'landscape' otherwise toggles the mode
        """
        if mode == 'portrait':
            self._orientation = False
        elif mode == 'landscape':
            self._orientation = True
        else:
            self._orientation = not self._orientation
        self._report.append(NextPageTemplate("landscape" if self._orientation else "portrait"))

    def pieChart(self, data, **kwargs):
        """ creates a pie chart

        :param data: 1d array of data, e.g. [5, 10, 20, ...]
        :param labels: 1d array of labels
        :param lblFrmt: how to format the data, e.g. 5%
        :param plotSize: size in pixels, e.g. (400, 200)
        :param title: title of pie chart
        :param legend: true/false, when true, labels are displayed here, when false added to the pie
        """
        class PieDrawing(Drawing):  # pylint: disable=R0904
            """ pie charting """
            def __init__(self, data, **kw):
                """everything is done here
                """
                title = kw.pop('title', None)
                labels = kw.pop('labels', '%.1f%%')
                lblFrmt = kw.pop('lblFrmt', '%.1f%%')
                legend = kw.pop('legend', False)
                size = kw.pop('plotSize', (18 * cm, 9 * cm))

                Drawing.__init__(self, size[0], size[1])
                self.add(Pie(), name='chart')

                for key, val in kw.items():
                    setattr(self.chart, key, val)

                self.chart.x = 10
                self.chart.y = (self.height - self.chart.height) / 2
                self.chart.slices.strokeWidth = 1
                # self.chart.slices.popout = 1
                self.chart.direction = 'clockwise'
                self.chart.width = self.chart.height
                self.chart.startAngle = 90
                # self.chart.slices[0].popout = 10
                for i in xrange(len(data)):
                    self.chart.slices[i].fillColor = HexColor(PDF_CHART_COLORS[i % len(PDF_CHART_COLORS)])

                self.chart.data = data
                self.chart.labels = [(lblFrmt % i) for i in self.chart.data]
                self.chart.checkLabelOverlap = True

                if title is not None:
                    self.add(String(20, size[1] - 20, title), name='title')
                    self.chart.y -= 10

                if legend:
                    self.add(Legend(), name='legend')
                    self.legend.boxAnchor = 'w'
                    self.legend.x = self.chart.width + 40
                    self.legend.y = self.height / 2
                    self.legend.subCols[1].align = 'right'
                    self.legend.alignment = 'right'
                    self.legend.columnMaximum = 7
                    if labels is not None:
                        self.legend.colorNamePairs = [(self.chart.slices[i].fillColor, labels[i])
                                                      for i in xrange(len(labels))]
                elif labels is not None:
                    for i in xrange(min([len(labels), len(data)])):
                        self.chart.labels[i] = labels[i]

        if kwargs.pop('insert', True):
            self.insertImage(kwargs.pop('title', None), PieDrawing(data, **kwargs))
        else:
            return PieDrawing(data, **kwargs)

    def barChart(self, data, labels, **kwargs):  # pylint: disable=R0912,R0915
        """ creates a bar chart

        :param data: contains a two dimentional array of values, e.g. [[d11, d21, x1], [d12, d22, x2]]
        :param labels: can contain, but must not ["xlabel", "ylabel", ["data label0", ...]]
                       third item can also be an interger stating the iteration start as label
        :param ylim: limit the y axis to these values, e.g. (0, 100)
        :param bars: list of colors we should use for the bars, refer to PDF_CHART_COLORS as an example
        :param size: size in pixels, e.g. (8 * cm, 4 * cm) or pixels, e.g. (400, 200)
        :param title: title of bar chart
        :param stacked: wether to do a stacked bar plot or std column plot
        :param insert: if true it directly inserts the graphic into PDF otherwise returns the 'paragraph'
        """
        class BarDrawing(Drawing):  # pylint: disable=R0904
            """ bar charting """
            def __init__(self, data, labels, **kw):  # pylint: disable=R0915
                """ everything is done here
                """
                title = kw.pop('title', None)
                stacked = kw.pop('stacked', False)
                bars = kw.pop('bars', PDF_CHART_COLORS)
                size = kw.pop('plotSize', (18 * cm, 9 * cm))
                ylim = kw.pop('ylim', None)

                Drawing.__init__(self, size[0], size[1])
                self.add(VerticalBarChart(), name='chart')

                for key, val in kw.items():
                    setattr(self.chart, key, val)

                if title is not None:
                    self.add(String(20, size[1] - 20, title), name='title')
                    self.chart.y -= 10

                self.chart.width = self.width - 20
                self.chart.height = self.height - 40

                self.chart.data = data
                maxY = 0
                minY = maxint
                for i in xrange(len(data)):
                    self.chart.bars[i].fillColor = HexColor(bars[i % len(bars)])
                    maxY = max(data[i] + [maxY])
                    minY = min(data[i] + [minY])
                self.chart.valueAxis.valueMax = maxY * 1.1
                self.chart.valueAxis.valueMin = minY * 0.9

                if ylim is not None:
                    self.chart.valueAxis.valueMin = ylim[0]
                    self.chart.valueAxis.valueMax = ylim[1]

                if len(data) > 1:
                    self.chart.barSpacing = 2

                if labels is not None:
                    if len(labels) > 0:
                        self.add(Label(), name="xlabel")
                        self.xlabel._text = labels[0]  # pylint: disable=W0212
                        self.xlabel.textAnchor = 'middle'
                        self.xlabel.x = self.width / 2
                        self.xlabel.y = 0
                        self.chart.y += 15
                    if len(labels) > 1:
                        self.add(Label(), name="ylabel")
                        self.ylabel._text = labels[1]  # pylint: disable=W0212
                        self.xlabel.textAnchor = 'middle'
                        self.ylabel.angle = 90
                        self.ylabel.x = 0
                        self.ylabel.y = self.height / 2
                        self.chart.x += 10
                    if len(labels) > 2:
                        if len(labels[2]) == max([len(x) for x in data]):
                            self.chart.categoryAxis.categoryNames = labels[2]
                            self.chart.categoryAxis.labels.angle = 30
                        elif type(labels[2]) == int:
                            self.chart.categoryAxis.categoryNames = xrange(labels[2], max([len(x) for x in data]) +
                                                                           labels[2])

                if stacked:
                    self.chart.categoryAxis.style = 'stacked'
                # chart.valueAxis.valueMin = 0

        if kwargs.pop('insert', True):
            self.insertImage(kwargs.pop('title', None), BarDrawing(data, labels, **kwargs))
        else:
            return BarDrawing(data, labels, **kwargs)

    def lineChart(self, data, labels, **kwargs):  # pylint: disable=R0912,R0915
        """ Create a scatter or bar plot
        below arguments are used directly by this method, more are pushed through to
        reportlab's drawing for construction...

        :param data: contains a three dimentional array of values (list of lists of points)
                     or just a list of datapoint lists (it will be auto-transposed to start at 0)
        :param labels: can contain, but must not ["xlabel", "ylabel", ["data label0", ...]]
                       third item can also be an interger stating the iteration start as label
                       when of same size as data, then a legend is added instead
        :param xlim: limit the x axis to these values, e.g. (0, 100)
        :param ylim: limit the y axis to these values, e.g. (0, 50)
        :param size: size in pixels, e.g. (18*cm, 9*cm)
        :param title: title of bar chart
        :param lines: list of colors we should use to paint lines
        :param markers: list of markers we should use to draw markers
        :param scatter: wether to do a scatter plot or line chart
        :param insert: if true it directly inserts the graphic into PDF otherwise returns the 'paragraph'
        """
        class LineDrawing(Drawing):  # pylint: disable=R0904
            """ line / marker charting """
            def __init__(self, data, labels, **kw):  # pylint: disable=R0912,R0915
                """ everything is done here
                """
                title = kw.pop('title', None)
                scatter = kw.pop('scatter', False)
                size = kw.pop('plotSize', (18 * cm, 9 * cm))
                lines = kw.pop('lines', PDF_CHART_COLORS)
                markers = kw.pop('markers', PDF_LINE_MARKERS)
                xlim = kw.pop('xlim', None)
                ylim = kw.pop('ylim', None)

                Drawing.__init__(self, size[0], size[1])
                self.add(ScatterPlot() if scatter else LinePlot(), name='chart')

                for key, val in kw.items():
                    setattr(self.chart, key, val)

                if title is not None:
                    self.add(String(20, size[1] - 10, title), name='title')
                    self.chart.y -= 10

                self.chart.width = self.width - 20
                self.chart.height = self.height - 40
                self.chart.x = 10
                self.chart.y = 10

                self.chart.data = data if type(data[0][0]) in (tuple, list) else [zip(xrange(len(i)), i) for i in data]

                maxY = 0
                minY = maxint
                for i in xrange(len(data)):
                    self.chart.lines[i].strokeColor = HexColor(lines[i % len(lines)])
                    if markers is not None:
                        self.chart.lines[i].symbol = makeMarker(markers[i % len(markers)])
                        self.chart.lines[i].symbol.size = 3
                    maxY = max([k[1] for k in self.chart.data[i]] + [maxY])
                    minY = min([k[1] for k in self.chart.data[i]] + [minY])
                self.chart.yValueAxis.valueMax = maxY * 1.1
                self.chart.yValueAxis.valueMin = minY * 0.9

                self.chart.xValueAxis.visibleGrid = True
                self.chart.yValueAxis.visibleGrid = True

                if xlim is not None:
                    self.chart.xValueAxis.valueMin = xlim[0]
                    self.chart.xValueAxis.valueMax = xlim[1]
                if ylim is not None:
                    self.chart.yValueAxis.valueMin = ylim[0]
                    self.chart.yValueAxis.valueMax = ylim[1]

                if scatter:
                    self.chart.xLabel = ''
                    self.chart.yLabel = ''
                    self.chart.y -= 10
                    self.chart.lineLabelFormat = None

                if labels is not None:
                    if len(labels) > 0:
                        self.add(Label(), name="xlabel")
                        self.xlabel._text = labels[0]  # pylint: disable=W0212
                        self.xlabel.textAnchor = 'middle'
                        self.xlabel.x = self.width / 2
                        self.xlabel.y = 5
                        self.chart.y += 15
                    if len(labels) > 1:
                        self.add(Label(), name="ylabel")
                        self.ylabel._text = labels[1]  # pylint: disable=W0212
                        self.xlabel.textAnchor = 'middle'
                        self.ylabel.angle = 90
                        self.ylabel.x = 0
                        self.ylabel.y = self.height / 2
                        self.chart.width -= 14
                        self.chart.x += 24
                    if len(labels) > 2:
                        # when labels are of same size as max nr of data point, use as x axis labels
                        if len(labels[2]) == max([len(x) for x in data]):
                            self.chart.categoryAxis.categoryNames = labels[2]
                            self.chart.xValueAxis.labels.angle = 30
                        # otherwise when integer use the counter
                        elif type(labels[2]) == int:
                            self.chart.categoryAxis.categoryNames = xrange(labels[2], max([len(x) for x in data]) +
                                                                           labels[2])
                        # or we could add a legend when of same size as data
                        elif len(labels[2]) == len(data):
                            self.add(Legend(), name='legend')
                            self.chart.height -= 8
                            self.chart.y += 8
                            self.xlabel.y += 8
                            self.legend.boxAnchor = 'sw'
                            self.legend.x = self.chart.x + 8
                            self.legend.y = -2
                            self.legend.columnMaximum = 1
                            self.legend.deltax = 50
                            self.legend.deltay = 0
                            self.legend.dx = 10
                            self.legend.dy = 1.5
                            self.legend.fontSize = 7
                            self.legend.alignment = 'right'
                            self.legend.dxTextSpace = 5
                            self.legend.colorNamePairs = [(HexColor(lines[i]), labels[2][i])
                                                          for i in xrange(len(self.chart.data))]
                            self.legend.strokeWidth = 0

        if kwargs.pop('insert', True):
            self.insertImage(kwargs.pop('title', None), LineDrawing(data, labels, **kwargs))
        else:
            return LineDrawing(data, labels, **kwargs)


"""
CHANGE LOG:
-----------
$Log: pdf_old.py  $
Revision 1.1 2015/04/23 19:05:00CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/rep/project.pj
Revision 1.22 2014/11/06 14:42:34CET Mertens, Sven (uidv7805) 
object update
--- Added comments ---  uidv7805 [Nov 6, 2014 2:42:34 PM CET]
Change Package : 278229:1 http://mks-psad:7002/im/viewissue?selection=278229
Revision 1.21 2014/05/12 09:48:04CEST Hecker, Robert (heckerr)
Added new JobSimFeature.
--- Added comments ---  heckerr [May 12, 2014 9:48:05 AM CEST]
Change Package : 236158:1 http://mks-psad:7002/im/viewissue?selection=236158
Revision 1.20 2014/03/28 10:42:16CET Hecker, Robert (heckerr)
Added pylint exception for old style Method-Names.
--- Added comments ---  heckerr [Mar 28, 2014 10:42:16 AM CET]
Change Package : 228098:1 http://mks-psad:7002/im/viewissue?selection=228098
Revision 1.19 2014/03/26 13:28:10CET Hecker, Robert (heckerr)
Added python 3 changes.
--- Added comments ---  heckerr [Mar 26, 2014 1:28:10 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.18 2014/03/24 09:13:40CET Hecker, Robert (heckerr)
marked pdf class as deprecated.
--- Added comments ---  heckerr [Mar 24, 2014 9:13:40 AM CET]
Change Package : 224335:1 http://mks-psad:7002/im/viewissue?selection=224335
Revision 1.17 2013/07/17 09:28:52CEST Mertens, Sven (uidv7805)
- removing generator and generatorRev as agreed,
- adding RotatedText for being able to create shorter tables
--- Added comments ---  uidv7805 [Jul 17, 2013 9:28:52 AM CEST]
Change Package : 185933:2 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.16 2013/07/11 13:46:32CEST Mertens, Sven (uidv7805)
removing undocumented, using all instead
--- Added comments ---  uidv7805 [Jul 11, 2013 1:46:32 PM CEST]
Change Package : 185933:2 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.15 2013/07/11 13:29:54CEST Mertens, Sven (uidv7805)
testing undocumented flag
--- Added comments ---  uidv7805 [Jul 11, 2013 1:29:54 PM CEST]
Change Package : 185933:2 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.14 2013/07/10 09:45:16CEST Mertens, Sven (uidv7805)
added xlim / ylim parameters to bar and line charts
--- Added comments ---  uidv7805 [Jul 10, 2013 9:45:16 AM CEST]
Change Package : 185933:2 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.13 2013/07/08 12:59:34CEST Mertens, Sven (uidv7805)
enabling direct image file insertion,
charting options opened finally
--- Added comments ---  uidv7805 [Jul 8, 2013 12:59:34 PM CEST]
Change Package : 185933:2 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.12 2013/07/05 15:05:07CEST Mertens, Sven (uidv7805)
table header background should be preserved
--- Added comments ---  uidv7805 [Jul 5, 2013 3:05:07 PM CEST]
Change Package : 185933:1 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.11 2013/07/05 09:02:12CEST Mertens, Sven (uidv7805)
adding legend to lineChart method,
generic method 'append' can be used to insert any reportlab item
--- Added comments ---  uidv7805 [Jul 5, 2013 9:02:13 AM CEST]
Change Package : 185933:3 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.10 2013/06/13 13:59:46CEST Mertens, Sven (uidv7805)
added new features for pie, bar, line and scatter drawings based on reportlab
--- Added comments ---  uidv7805 [Jun 13, 2013 1:59:46 PM CEST]
Change Package : 185933:2 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.9 2013/06/03 15:03:07CEST Mertens, Sven (uidv7805)
now, orientation can be changed on each page
--- Added comments ---  uidv7805 [Jun 3, 2013 3:03:07 PM CEST]
Change Package : 179495:9 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.8 2013/05/29 13:18:10CEST Mertens, Sven (uidv7805)
removing unused paragraph method
--- Added comments ---  uidv7805 [May 29, 2013 1:18:10 PM CEST]
Change Package : 179495:6 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.7 2013/05/29 09:16:49CEST Mertens, Sven (uidv7805)
using local pylint ignores
--- Added comments ---  uidv7805 [May 29, 2013 9:16:49 AM CEST]
Change Package : 179495:7 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.6 2013/05/27 16:14:15CEST Mertens, Sven (uidv7805)
moving front page to right a bit using new definition
--- Added comments ---  uidv7805 [May 27, 2013 4:14:15 PM CEST]
Change Package : 179495:6 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.5 2013/05/22 11:16:35CEST Mertens, Sven (uidv7805)
fixes for
- keeping table and name together,
- catching exception when folder already exists
--- Added comments ---  uidv7805 [May 22, 2013 11:16:35 AM CEST]
Change Package : 179495:6 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.4 2013/05/21 13:55:39CEST Mertens, Sven (uidv7805)
new method: insertSpacer,
folder is created if not existing,
topHeader only changes 1st row background
--- Added comments ---  uidv7805 [May 21, 2013 1:55:39 PM CEST]
Change Package : 179495:6 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.3 2013/05/03 13:36:52CEST Hecker, Robert (heckerr)
Added Log Keword at the end of file.
--- Added comments ---  heckerr [May 3, 2013 1:36:52 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
"""
