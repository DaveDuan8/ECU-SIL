"""
stk/rep/pdf/algo_base/template
------------------------------

**base Template/Layout module of Algo Reports**

**Internal-API Interfaces**

    - `DeveloperTemplate`
    - `TitlePageTemplate`
    - `PortraitTemplate`
    - `LandscapePageTemplate`
    - `AlgoTestDocTemplate`

**User-API Interfaces**

    - `stk.rep` (complete package)

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.2 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/12/01 11:22:54CET $
"""
# Import Python Modules --------------------------------------------------------
import os
import time
import io
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.styles import ParagraphStyle
import reportlab.platypus.doctemplate as dtp
import reportlab.platypus as plat
import warnings

# Import STK Modules -----------------------------------------------------------
from ..base import template as temp
from ..base import pdf
from stk.rep.image import logo
from stk.util.helper import deprecated

pdfmetrics.registerFont(TTFont('Calibri', 'Calibri.ttf'))

# Defines ----------------------------------------------------------------------
PAGE_TEMPLATE_TITLE_PAGE = 'TitlePageTemplate'
COPYRIGHT = "COPYRIGHT. CONFIDENTIAL AND PROPRIETARY. ALL RIGHTS RESERVED - Property of Continental AG. " \
            "This information carrier and the information it contains are the property of Continental AG. " \
            "Any reproduction, disclosure or use of either is prohibited without the prior written consent " \
            "of Continental AG. Continental AG reserves worldwide all rights also in the case of industrial" \
            " property rights being granted. The same provisions apply to any oral communications related" \
            " thereto accordingly."
DEFAULT_PAGE_HEADER_TEXT = "Algorithm Test Results"

# Functions --------------------------------------------------------------------
PAGE_TEMPLATE_PORTRAIT = temp.PAGE_TEMPLATE_PORTRAIT
PAGE_TEMPLATE_LANDSCAPE = temp.PAGE_TEMPLATE_LANDSCAPE


# Classes ----------------------------------------------------------------------
class DeveloperTemplate(pdf.Story):
    '''
    template for chapter Development details
    can be filled by developers during report generation using own generation script
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
        self.style = temp.Style()
        pdf.Story.__init__(self, self.style, mem_reduction)

        self.add_page_break()
        self.add_heading("Development details", 0)


class TitlePageTemplate(dtp.PageTemplate):  # pylint: disable=R0902
    '''
    template for title page
    '''
    CONF_LEVEL_UNCLASSIFIED = "- Unclassified -"
    CONF_LEVEL_CONFIDENTIAL = "- Confidential -"
    CONF_LEVEL_STRICTLY = "- Strictly Confidential -"
    DRAFT_STATEMENT = "DRAFT"
    DOC_STYLE_SHEET = getSampleStyleSheet()
    TITLE_STYLE = DOC_STYLE_SHEET["Title"]
    NORMAL_STYLE = DOC_STYLE_SHEET["Normal"]
    ID = PAGE_TEMPLATE_TITLE_PAGE  # pylint: disable=C0103

    def __init__(self, doc):
        self._doc = doc
        self.title = "Not Set"
        self.checkpoint = "AL_SMFC4B0_00.00.00"
        self.add_info = ""
        self.author = os.environ["USERNAME"]
        self.subject = "Unknown"
        self.status = ""
        self.date = time.asctime()
        self.confidential_level = self.CONF_LEVEL_STRICTLY
        self.CENTER_STYLE = self.NORMAL_STYLE  # pylint: disable=C0103
        self.CENTER_STYLE.alignment = 1
        self.frames = [dtp.Frame(doc.leftMargin, doc.bottomMargin,  # pylint: disable=E1101
                                 doc.width, doc.height, id='F0')]  # pylint: disable=E1101
        dtp.PageTemplate.__init__(self, self.ID, self.frames, onPage=self.on_page, pagesize=doc.pagesize)

    def on_page(self, canv, doc):  # pylint: disable=W0613
        '''
        overwritten Callback Method, which will be called during the rendering process,
        to draw on every page identical items, like header of footers.
        '''
        canv.saveState()
        canv.setTitle(self.title)
        if self.author is not None:
            canv.setAuthor(self.author)
        if self.subject is not None:
            canv.setSubject(self.subject)
        if self.status == "draft":
            canv.setFillColor(colors.gray)
            canv.setStrokeColor(colors.gray)
            canv.setFont("Helvetica-Bold", 85)
            canv.drawCentredString(10.5 * cm, 8 * cm, self.DRAFT_STATEMENT)
        canv.restoreState()
        self._doc.handle_nextPageTemplate(temp.PAGE_TEMPLATE_PORTRAIT)

    def _create(self, story):
        '''
        creates the pdf story, called during `report.Build`

        :param story: pdf story to add paragraphs to
        :type story:  list of `Story` elements
        '''
        # add logo
        story.append(plat.Image(io.BytesIO(logo.CONTI_CORP_LOGO),
                     width=logo.CONTI_LOGO_SIZE[0] * 0.5, height=logo.CONTI_LOGO_SIZE[1] * 0.5))
        story.append(plat.Spacer(1, 2 * cm))

        # add title
        story.append(plat.Paragraph(self.title, self.TITLE_STYLE))
        story.append(plat.Spacer(1, 1 * cm))

        # add title
        story.append(plat.Paragraph("for", self.TITLE_STYLE))
        story.append(plat.Spacer(1, 1 * cm))

        # add checkpoint and additional info
        story.append(plat.Paragraph(self.checkpoint, self.TITLE_STYLE))
        story.append(plat.Paragraph(self.add_info, self.TITLE_STYLE))
        story.append(plat.Spacer(1, 3 * cm))

        # confidence statement
        story.append(plat.Paragraph('<para alignment="center">%s</para>' % self.confidential_level, self.TITLE_STYLE))
        story.append(plat.Spacer(1, 3 * cm))

        # Add Date
        story.append(plat.Spacer(1, 7 * cm))
        story.append(plat.Paragraph(self.date, self.CENTER_STYLE))

        story.append(plat.PageBreak())

    @deprecated('on_page')
    def OnPage(self, canv, doc):  # pylint: disable=W0613,C0103
        """
        :deprecated: use `on_page` instead
        """
        return self.on_page(canv, doc)

    @deprecated('_create')
    def _Create(self, story):  # pylint: disable=C0103
        """
        :deprecated: use `_create` instead
        """
        return self._create(story)


class PortraitPageTemplate(temp.PortraitPageTemplate):
    '''
    base template for portrait page giving heigh, width and header, footer etc.
    '''
    GLOB_PAGE_BOTTOM_MARGIN = 1.8 * cm
    GLOB_PAGE_HEIGHT = 25 * cm
    GLOB_PAGE_WIDTH = 15 * cm

    def __init__(self, doctemplate, custom_page_header_text=None):
        """
        preset class internal variables

        :param custom_page_header_text: text displayed on the page header of the document;
                                        if not specified, the default page header text will be used
                                        (defined in DEFAULT_PAGE_HEADER_TEXT).
        :type custom_page_header_text:  string, optional, default: None
        """
        temp.PortraitPageTemplate.__init__(self, doctemplate)

        self._custom_page_header_text = custom_page_header_text

    def on_page(self, canv, doc):
        """This function is used to write pages.

        :param canv: -- widget that provides structured graphics facilities
        :param doc: -- document template
        """
        canv.saveState()

        pleft = plat.Paragraph("Continental<br/>ADAS",
                               ParagraphStyle(name="plb", fontSize=8, fontName="Calibri",
                                              alignment=TA_CENTER, leading=12))

        pcenter = plat.Paragraph(COPYRIGHT, ParagraphStyle(name="pcb", fontSize=6, fontName="Calibri",
                                                           alignment=TA_CENTER, leading=5))
        wwidth = 10 * cm
        _, hhigh = pcenter.wrap(wwidth, doc.bottomMargin)
        pright = plat.Paragraph("%s" % (doc.build_page_index_string()),  # doc.page
                                ParagraphStyle(name="pright", fontSize=8, fontName="Calibri", alignment=TA_CENTER))

        tflow = plat.Table([[pleft, pcenter, pright]], [3.2 * cm, wwidth, 3.2 * cm], ident="bottomTable")
        tflow.setStyle(plat.TableStyle([('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                        ('BOX', (0, 0), (-1, -1), 0.25, colors.black), ]))
        tflow.wrapOn(canv, wwidth, hhigh)
        tflow.drawOn(canv, doc.leftMargin, self.GLOB_PAGE_BOTTOM_MARGIN - 0.2 * cm)

        pleft = plat.Image(io.BytesIO(logo.CONTI_CORP_LOGO),
                           4 * cm, 4 * cm * logo.CONTI_LOGO_SIZE[1] / float(logo.CONTI_LOGO_SIZE[0]))
        pstyle = ParagraphStyle(name="pst", fontSize=14, FontName="Calibri", alignment=TA_CENTER)
        if self._custom_page_header_text is None:
            page_header_text = DEFAULT_PAGE_HEADER_TEXT
        else:
            page_header_text = self._custom_page_header_text
        pcenter = plat.Paragraph(page_header_text, pstyle)
        # pr = Paragraph(self._headerInfo[4], ps)
        tflow = plat.Table([[pleft, pcenter]], [4.2 * cm, 12.2 * cm], ident="topTable")
        tflow.setStyle(plat.TableStyle([('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                        ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ]))
        tflow.wrapOn(canv, 10 * cm, hhigh)
        tflow.drawOn(canv, doc.leftMargin, self.GLOB_PAGE_HEIGHT + 2.4 * cm)
        canv.restoreState()

    @deprecated('on_page')
    def OnPage(self, canv, doc):  # pylint: disable=C0103
        """
        :deprecated: use `on_page` instead
        """
        return self.on_page(canv, doc)


class LandscapePageTemplate(temp.LandscapePageTemplate):
    '''
    base template for landscape page giving height, width and header, footer etc.
    '''

    GLOB_PAGE_BOTTOM_MARGIN = 1.8 * cm
    GLOB_PAGE_HEIGHT = 25 * cm
    GLOB_PAGE_WIDTH = 15 * cm

    def __init__(self, doctemplate, custom_page_header_text=None):
        """
        preset class internal variables

        :param custom_page_header_text: text displayed on the page header of the document;
                                        if not specified, the default page header text will be used
                                        (defined in DEFAULT_PAGE_HEADER_TEXT).
        :type custom_page_header_text:  string, optional, default: None
        """
        temp.LandscapePageTemplate.__init__(self, doctemplate)

        self._custom_page_header_text = custom_page_header_text

    def on_page(self, canv, doc):
        """This function is used to write pages.

        :param canv: -- widget that provides structured graphics facilities
        :param doc: -- document template
        """
        canv.saveState()

        pleft = plat.Paragraph("Continental<br/>ADAS",
                               ParagraphStyle(name="plb", fontSize=8, fontName="Calibri",
                                              alignment=TA_CENTER, leading=8))

        pcenter = plat.Paragraph(COPYRIGHT, ParagraphStyle(name="pcb", fontSize=6, fontName="Calibri",
                                                           alignment=TA_CENTER, leading=5))
        wwidth = 18.7 * cm
        _, hhigh = pcenter.wrap(wwidth, doc.bottomMargin)
        pright = plat.Paragraph("%s" % (doc.build_page_index_string()),  # doc.page
                                ParagraphStyle(name="pright", fontSize=8, fontName="Calibri", alignment=TA_CENTER))
        tflow = plat.Table([[pleft, pcenter, pright]], [3.2 * cm, wwidth, 3.2 * cm], ident="bottomTable")
        tflow.setStyle(plat.TableStyle([('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                        ('BOX', (0, 0), (-1, -1), 0.25, colors.black), ]))
        tflow.wrapOn(canv, wwidth, hhigh)
        tflow.drawOn(canv, doc.leftMargin, self.GLOB_PAGE_BOTTOM_MARGIN - 0.2 * cm)

        pleft = plat.Image(io.BytesIO(logo.CONTI_CORP_LOGO),
                           4 * cm, 4 * cm * logo.CONTI_LOGO_SIZE[1] / float(logo.CONTI_LOGO_SIZE[0]))
        pstyle = ParagraphStyle(name="pst", fontSize=14, FontName="Calibri", alignment=TA_CENTER)
        if self._custom_page_header_text is None:
            page_header_text = DEFAULT_PAGE_HEADER_TEXT
        else:
            page_header_text = self._custom_page_header_text
        pcenter = plat.Paragraph(page_header_text, pstyle)
        # pr = Paragraph(self._headerInfo[4], ps)
        tflow = plat.Table([[pleft, pcenter]], [4.2 * cm, 20.9 * cm], ident="topTable")
        tflow.setStyle(plat.TableStyle([('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                        ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ]))
        tflow.wrapOn(canv, 10 * cm, hhigh)
        tflow.drawOn(canv, doc.leftMargin, self.GLOB_PAGE_WIDTH + 3.5 * cm)
        canv.restoreState()

    @deprecated('on_page')
    def OnPage(self, canv, doc):  # pylint: disable=C0103
        """
        :deprecated: use `on_page` instead
        """
        return self.on_page(canv, doc)


class AlgoTestDocTemplate(dtp.BaseDocTemplate):  # pylint: disable=R0904
    '''
    **main template for algo test report**

    as used in `AlgoTestReport` and `RegressionReport`

    defining style of headings, table of content, figure caption style etc.
    '''
    def __init__(self, style, filepath, custom_page_header_text=None):
        """
        preset class internal variables

        :param custom_page_header_text: text displayed on the page header of the document;
                                        if not specified, the default page header text will be used
                                        (defined in DEFAULT_PAGE_HEADER_TEXT).
        :type custom_page_header_text:  string, optional, default: None
        """
        dtp.BaseDocTemplate.__init__(self, filepath)
        self._style = style
        # names inherited from BaseDocTemplate
        self._maxTextWidth = 70  # pylint: disable=C0103
        self._lastnumPages = 2  # pylint: disable=C0103
        self.numPages = 1  # pylint: disable=C0103

        self.addPageTemplates([TitlePageTemplate(self), PortraitPageTemplate(self, custom_page_header_text), LandscapePageTemplate(self, custom_page_header_text)])

    def afterFlowable(self, flowable):
        ''' overwriting BaseDocTemplate method, setting own parameters '''
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
            elif style == 'Heading4':
                key = 'h4-%s' % self.seq.nextf('heading4')
                self.canv.bookmarkPage(key)
                self.notify('TOCEntry', (3, text, self.page, key))
                self.canv.addOutlineEntry(text, key, 3)
            elif style == 'TableTitleStyle':
                key = 't-%s' % self.seq.nextf('tabletitlestyle')
                self.canv.bookmarkPage(key)
                self.notify('TOTable', (1, text, self.page, key))
            elif style == 'FigureTitleStyle':
                key = 'f-%s' % self.seq.nextf('figuretitlestyle')
                self.canv.bookmarkPage(key)
                self.notify('TOFigure', (1, text, self.page, key))

    def build_page_index_string(self):
        """Return page index string for the footer."""
        if self.page < self.numPages:
            self._lastnumPages += 1

        return 'page %(current_page)d of %(total_pages)d' % {'current_page': self.page, 'total_pages': self.numPages}

    @deprecated('build_page_index_string')
    def BuildPageIndexString(self):  # pylint: disable=C0103
        """
        :deprecated: use `build_page_index_string` instead
        """
        # warnings.warn('Method "BuildPageIndexString" is deprecated use "build_page_index_string" instead',
        #               stacklevel=2)
        return self.build_page_index_string()


"""
CHANGE LOG:
-----------
$Log: template.py  $
Revision 1.2 2016/12/01 11:22:54CET Hospes, Gerd-Joachim (uidv8815) 
fix docu errors
Revision 1.1 2015/04/23 19:05:08CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/rep/pdf/algo_base/project.pj
Revision 1.9 2015/03/10 16:48:22CET Ellero, Stefano (uidw8660)
Each page of the pdf report starts with the hard coded header "Algo Validation Report".
A variable is introduced to set this header to another string, if needed; default is the existing one.
This internal variable is set during initialization of the report class using an option named: "custom_page_header_text".
--- Added comments ---  uidw8660 [Mar 10, 2015 4:48:23 PM CET]
Change Package : 314895:1 http://mks-psad:7002/im/viewissue?selection=314895
Revision 1.8 2015/03/06 15:39:37CET Ellero, Stefano (uidw8660)
Implemented the optional parameter "mem_reduction" in the base class for all report templates (stk.rep.pdf.base.pdf.Story) to reduce the memory usage during a pdf report generation.
--- Added comments ---  uidw8660 [Mar 6, 2015 3:39:38 PM CET]
Change Package : 307809:1 http://mks-psad:7002/im/viewissue?selection=307809
Revision 1.7 2015/01/29 17:43:16CET Hospes, Gerd-Joachim (uidv8815)
add 'add_info' to report top page
--- Added comments ---  uidv8815 [Jan 29, 2015 5:43:17 PM CET]
Change Package : 298621:1 http://mks-psad:7002/im/viewissue?selection=298621
Revision 1.6 2015/01/27 21:20:06CET Ellero, Stefano (uidw8660)
Removed all rep based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 27, 2015 9:20:07 PM CET]
Change Package : 296836:1 http://mks-psad:7002/im/viewissue?selection=296836
Revision 1.5 2015/01/27 16:16:40CET Ellero, Stefano (uidw8660)
Removed all rep based deprecated function usage inside stk and module tests.
Revision 1.4 2014/07/29 12:41:27CEST Hospes, Gerd-Joachim (uidv8815)
pep8 fixes of too long lines for http links, epydoc and pylint adjustments
--- Added comments ---  uidv8815 [Jul 29, 2014 12:41:28 PM CEST]
Change Package : 246030:1 http://mks-psad:7002/im/viewissue?selection=246030
Revision 1.3 2014/05/09 17:21:28CEST Hospes, Gerd-Joachim (uidv8815)
set titlepage default status to ""
--- Added comments ---  uidv8815 [May 9, 2014 5:21:28 PM CEST]
Change Package : 233144:2 http://mks-psad:7002/im/viewissue?selection=233144
Revision 1.2 2014/04/07 14:12:18CEST Hospes, Gerd-Joachim (uidv8815)
pep8 & pylint fixes after adding new packages and splitting some modules
--- Added comments ---  uidv8815 [Apr 7, 2014 2:12:18 PM CEST]
Change Package : 227496:1 http://mks-psad:7002/im/viewissue?selection=227496
Revision 1.1 2014/04/04 17:38:40CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision with parts copied from algo_test.template
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
stk/rep/pdf/algo_base/project.pj
"""
