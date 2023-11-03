"""
stk/rep/pdf/algo_base/template
------------------------------

**Template/Layout module of Algo Documents**

**Internal-API Interfaces**

    - `DeveloperTemplate`
    - `TitlePageTemplate`
    - `PortraitTemplate`
    - `LandscapePageTemplate`

**User-API Interfaces**

    - `AlgoDocTemplate`
    - `stk.rep` (complete package)

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:26CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
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

# - import STK modules ------------------------------------------------------------------------------------------------
from ..base import template as temp
from ...image import logo
from stk.util.helper import deprecated

pdfmetrics.registerFont(TTFont('Calibri', 'Calibri.ttf'))

# - defines -----------------------------------------------------------------------------------------------------------
PAGE_TEMPLATE_TITLE_PAGE = 'TitlePageTemplate'
COPYRIGHT = "COPYRIGHT. CONFIDENTIAL AND PROPRIETARY. ALL RIGHTS RESERVED - Property of Continental AG. " \
            "This information carrier and the information it contains are the property of Continental AG. " \
            "Any reproduction, disclosure or use of either is prohibited without the prior written consent " \
            "of Continental AG. Continental AG reserves worldwide all rights also in the case of industrial" \
            " property rights being granted. The same provisions apply to any oral communications related" \
            " thereto accordingly."

PAGE_TEMPLATE_PORTRAIT = temp.PAGE_TEMPLATE_PORTRAIT
PAGE_TEMPLATE_LANDSCAPE = temp.PAGE_TEMPLATE_LANDSCAPE


# - classes -----------------------------------------------------------------------------------------------------------
class TitlePageTemplate(dtp.PageTemplate):
    """
    template for title page
    """
    CONF_LEVEL_UNCLASSIFIED = "- Unclassified -"
    CONF_LEVEL_CONFIDENTIAL = "- Confidential -"
    CONF_LEVEL_STRICTLY = "- Strictly Confidential -"
    DRAFT_STATEMENT = "DRAFT"
    DOC_STYLE_SHEET = getSampleStyleSheet()
    TITLE_STYLE = DOC_STYLE_SHEET["Title"]
    NORMAL_STYLE = DOC_STYLE_SHEET["Normal"]
    ID = PAGE_TEMPLATE_TITLE_PAGE

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
        self.CENTER_STYLE = self.NORMAL_STYLE
        self.CENTER_STYLE.alignment = 1
        self.frames = [dtp.Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='F0')]
        dtp.PageTemplate.__init__(self, self.ID, self.frames, onPage=self.on_page, pagesize=doc.pagesize)

    def on_page(self, canv, _):
        """
        overwritten Callback Method, which will be called during the rendering process,
        to draw on every page identical items, like header of footers.
        """
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
        """
        creates the pdf story, called during `report.Build`

        :param story: pdf story to add paragraphs to
        :type story:  list of `pdf.Story` elements
        """
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

        # add checkpoint
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
    def OnPage(self, canv, doc):  # pylint: disable=C0103
        """deprecated"""
        return self.on_page(canv, doc)


class PortraitPageTemplate(temp.PortraitPageTemplate):
    """
    base template for portrait page giving heigh, width and header, footer etc.
    """
    GLOB_PAGE_BOTTOM_MARGIN = 1.8 * cm
    GLOB_PAGE_HEIGHT = 25 * cm
    GLOB_PAGE_WIDTH = 15 * cm

    def __init__(self, doctemplate):
        temp.PortraitPageTemplate.__init__(self, doctemplate)

    def on_page(self, canv, doc):
        """This function is used to write pages.
        :param canv: -- widget that provides structured graphics facilities
        :param doc: -- document template
        """
        canv.saveState()

        plp = plat.Paragraph("Continental<br/>ADAS",
                             ParagraphStyle(name="plb", fontSize=8, fontName="Calibri",
                                            alignment=TA_CENTER, leading=12))

        pcp = plat.Paragraph(COPYRIGHT, ParagraphStyle(name="pcb", fontSize=6, fontName="Calibri",
                                                       alignment=TA_CENTER, leading=5))
        www = 10 * cm
        _, hhh = pcp.wrap(www, doc.bottomMargin)
        prp = plat.Paragraph("%s" % (doc.build_page_index_string()),  # doc.page
                             ParagraphStyle(name="pr", fontSize=8, fontName="Calibri", alignment=TA_CENTER))

        tft = plat.Table([[plp, pcp, prp]], [3.2 * cm, www, 3.2 * cm], ident="bottomTable")
        tft.setStyle(plat.TableStyle([('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                     ('BOX', (0, 0), (-1, -1), 0.25, colors.black), ]))
        tft.wrapOn(canv, www, hhh)
        tft.drawOn(canv, doc.leftMargin, self.GLOB_PAGE_BOTTOM_MARGIN - 0.2 * cm)

        plp = plat.Image(io.BytesIO(logo.CONTI_CORP_LOGO),
                         4 * cm, 4 * cm * logo.CONTI_LOGO_SIZE[1] / float(logo.CONTI_LOGO_SIZE[0]))
        pss = ParagraphStyle(name="pst", fontSize=14, FontName="Calibri", alignment=TA_CENTER)
        pcp = plat.Paragraph("Algorithm Report", pss)
        # pr = Paragraph(self._headerInfo[4], ps)
        tft = plat.Table([[plp, pcp]], [4.2 * cm, 12.2 * cm], ident="topTable")
        tft.setStyle(plat.TableStyle([('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                     ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                     ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                     ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ]))
        tft.wrapOn(canv, 10 * cm, hhh)
        tft.drawOn(canv, doc.leftMargin, self.GLOB_PAGE_HEIGHT + 2.4 * cm)
        canv.restoreState()

    @deprecated('on_page')
    def OnPage(self, canv, doc):  # pylint: disable=C0103
        """deprecated"""
        return self.on_page(canv, doc)


class LandscapePageTemplate(temp.LandscapePageTemplate):
    """
    base template for landscape page giving height, width and header, footer etc.
    """

    GLOB_PAGE_BOTTOM_MARGIN = 1.8 * cm
    GLOB_PAGE_HEIGHT = 25 * cm
    GLOB_PAGE_WIDTH = 15 * cm

    def __init__(self, doctemplate):
        temp.LandscapePageTemplate.__init__(self, doctemplate)

    def on_page(self, canv, doc):
        """This function is used to write pages.
        :param canv: -- widget that provides structured graphics facilities
        :param doc: -- document template
        """
        canv.saveState()

        plp = plat.Paragraph("Continental<br/>ADAS",
                             ParagraphStyle(name="plb", fontSize=8, fontName="Calibri",
                                            alignment=TA_CENTER, leading=8))

        pcp = plat.Paragraph(COPYRIGHT, ParagraphStyle(name="pcb", fontSize=6, fontName="Calibri",
                                                       alignment=TA_CENTER, leading=5))
        www = 18.7 * cm
        _, hhh = pcp.wrap(www, doc.bottomMargin)
        prr = plat.Paragraph("%s" % (doc.build_page_index_string()),  # doc.page
                             ParagraphStyle(name="pr", fontSize=8, fontName="Calibri", alignment=TA_CENTER))
        tft = plat.Table([[plp, pcp, prr]], [3.2 * cm, www, 3.2 * cm], ident="bottomTable")
        tft.setStyle(plat.TableStyle([('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                     ('BOX', (0, 0), (-1, -1), 0.25, colors.black), ]))
        tft.wrapOn(canv, www, hhh)
        tft.drawOn(canv, doc.leftMargin, self.GLOB_PAGE_BOTTOM_MARGIN - 0.2 * cm)

        plp = plat.Image(io.BytesIO(logo.CONTI_CORP_LOGO),
                         4 * cm, 4 * cm * logo.CONTI_LOGO_SIZE[1] / float(logo.CONTI_LOGO_SIZE[0]))
        pss = ParagraphStyle(name="pst", fontSize=14, FontName="Calibri", alignment=TA_CENTER)
        pcp = plat.Paragraph("Algorithm Report", pss)
        # pr = Paragraph(self._headerInfo[4], ps)
        tft = plat.Table([[plp, pcp]], [4.2 * cm, 20.9 * cm], ident="topTable")
        tft.setStyle(plat.TableStyle([('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                      ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                      ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                      ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ]))
        tft.wrapOn(canv, 10 * cm, hhh)
        tft.drawOn(canv, doc.leftMargin, self.GLOB_PAGE_WIDTH + 3.5 * cm)
        canv.restoreState()

    @deprecated('on_page')
    def OnPage(self, canv, doc):  # pylint: disable=C0103
        """deprecated"""
        return self.on_page(canv, doc)


class AlgoDocTemplate(dtp.BaseDocTemplate):
    """
    **main template for algo test report**
    as used in `AlgoTestReport` and `RegressionReport`

    defining style of headings, table of content, figure caption style etc.
    """
    def __init__(self, style, filepath):
        dtp.BaseDocTemplate.__init__(self, filepath)
        self._style = style
        # names inherited from BaseDocTemplate
        self._maxTextWidth = 70
        self._lastnumPages = 2
        self.numPages = 1

        self.addPageTemplates([TitlePageTemplate(self), PortraitPageTemplate(self), LandscapePageTemplate(self)])

    def afterFlowable(self, flowable):
        """ overwriting BaseDocTemplate method, setting own parameters """
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
        """ Return page index string for the footer. """
        if self.page < self.numPages:
            self._lastnumPages += 1

        return 'page %(current_page)d of %(total_pages)d' % {'current_page': self.page, 'total_pages': self.numPages}

    @deprecated('build_page_index_string')
    def BuildPageIndexString(self):  # pylint: disable=C0103
        """deprecated"""
        return self.build_page_index_string()


"""
CHANGE LOG:
-----------
$Log: algo_doc.py  $
Revision 1.1 2015/04/23 19:05:26CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/rep/pdf/tpl/project.pj
Revision 1.4 2015/01/29 17:43:36CET Hospes, Gerd-Joachim (uidv8815) 
add 'add_info' to report top page
--- Added comments ---  uidv8815 [Jan 29, 2015 5:43:37 PM CET]
Change Package : 298621:1 http://mks-psad:7002/im/viewissue?selection=298621
Revision 1.3 2015/01/27 13:30:31CET Mertens, Sven (uidv7805)
removing deprecated calls
--- Added comments ---  uidv7805 [Jan 27, 2015 1:30:32 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.2 2015/01/26 20:20:19CET Ellero, Stefano (uidw8660)
Removed all rep based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 26, 2015 8:20:20 PM CET]
Change Package : 296836:1 http://mks-psad:7002/im/viewissue?selection=296836
Revision 1.1 2014/05/09 16:23:56CEST Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/
    04_Engineering/stk/rep/pdf/tpl/project.pj
"""
