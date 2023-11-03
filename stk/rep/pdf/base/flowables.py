"""
stk/rep/pdf/base/flowables
--------------------------

layout Module for pdf Reports

Module which contains the needed interfaces to:

**User-API Interfaces**

    - `Table` (this module)
    - `Image` (this module)
    - `Heading` (this module)
    - `RotatedText` (this module)
    - `build_table_header` (this module)
    - `build_table_row` (this module)
    - `stk.rep` (complete package)

**Internal-API Interfaces**

    - `Numeration`
    - `TableBase`

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.9 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/08/25 15:47:08CEST $
"""
# Import Python Modules --------------------------------------------------------
import os
import six
import copy
from re import compile as recompile
from xml.sax.saxutils import escape
import reportlab.platypus as plat
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib import utils
from reportlab.platypus.doctemplate import FrameActionFlowable
from imghdr import what as what_image_type
from PIL import Image as pil_image

# needed when deprecation warnings are activated:
# import warnings

# Import STK Modules -----------------------------------------------------------
from ....util.helper import deprecated

# Defines ----------------------------------------------------------------------
DOC_STYLE_SHEET = getSampleStyleSheet()
NORMAL_STYLE = DOC_STYLE_SHEET["Normal"]
# normal style with splitting option for long words, used in table columns
NORMAL_SPLIT = copy.copy(NORMAL_STYLE)
NORMAL_SPLIT.wordWrap = 'CJK'

DOORS_URL_REGEXP = r'^(doors|http|ftp):[/][/][&/\w\d?:=-]*'
DOORS_URL_MATCH = recompile(DOORS_URL_REGEXP)

HTMLREPL = {"\r": "", "\n": "<br/>"}


# Functions --------------------------------------------------------------------
def filter_cols(row, col_map):
    """
    return columns of row if col_map element is True, complete list if col_map is empty or None

    :param row: list to filter
    :type row:  list
    :param col_map: list if column should be added
    :type col_map:  list of True/False for each column
    :return: filtered list
    """
    if col_map:
        return [row[i] for i in range(len(row)) if col_map[i] is True]
    else:
        return row


def build_table_header(column_names, style=NORMAL_STYLE):
    """
    Create the Table Header Paragraph object.

    :param column_names: names of columns in header line
    :type column_names:  list[string,...]
    :param style: ReportLab style for the header column
    :type  style: ReportLab ParagraphStyle
    :return: ReportLab table header
    :rtype:  list[Paragraph]
    """
    header = []

    for col_name in column_names:
        # header.append(plat.Paragraph("<b>%s</b>" % col_name, NORMAL_STYLE))
        if type(col_name) in (str, int, float, complex) or isinstance(col_name, six.integer_types):
            header.append(plat.Paragraph("<b>%s</b>" % str(col_name), style))
        else:
            header.append(col_name)
    return header


def build_table_row(row_items, col_filter=None, style=NORMAL_SPLIT):
    """
    Create one row with given item, format to fit into column

    internal: creates platypus.Paragraph for each str entry using given style
    that allows to get word wrap active in the cells

    :param row_items: list of items to format in columns of a row
    :type row_items:  list[item, ...]
    :param col_filter: opt filter list to leave out columns (see `filter_cols()`)
    :type  col_filter: list[True, False, ...]
    :param style: opt style setting, default: NORMAL_STYLE
    :type  style: platypus.ParagraphStyle

    :return: ReportLab table row
    :rtype:  list[Paragraph]
    """
    row = []
    for item in filter_cols(row_items, col_filter):
        if type(item) in (int, float, complex) or isinstance(item, six.integer_types):
            row.append(plat.Paragraph(str(item), style))
        elif type(item) is str:
            row.append(plat.Paragraph(item, style))
        else:
            row.append(item)
    return row


def html_str(text):  # pylint: disable=C0103
    r"""return string with HTML Characters, e.g. needed for Paragraphs

    :param text: object with <, >, & or \n to be replaced
    :type  text: object with str() method
    :return: html compatible string
    :rtype:  string
    """
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br />')


def url_str(text, url):
    """ return text with underlying url

    if an url is inside the text place html tags to show it accordingly with <a href="url">url</a>

    :param url: url to link to
    :type url:  string
    :param text: text to display for link
    :type text:  string

    :return: html compatible sting
    :rtype:  string
    """
    if url:
        if DOORS_URL_MATCH.match(url):
            return '<a href="%s">%s</a>' % (url, html_str(text))
#         else:
#             raise StkError('URL "%s" for "%s" does not start with "doors" or "http"' % (url, text))
    return html_str(text)


def replace_html_chars(text):
    r"""
    Replace HTML Characters, e.g. needed for Paragraphs

    e.g. replacing "\r" with "" and "\n": "<br/>"

    :param text: string to convert
    :type  text: str
    :return: text with replaced chars
    :rtype: str
    """
    return escape(text, HTMLREPL) if type(text) == str else text


# Classes ----------------------------------------------------------------------
class Numeration(object):  # pylint: disable=R0903
    """
    **Basic Numeration class which manages all continuous number items in a normal or merged pdf document.**

    Other story objects which need to have a numeration inside the report must be derived from this class.

    Currently following classes are depending on Numeration:

    - `Heading`
    - `Image`
    - `Heading`

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    _section = [0]
    _fig_num = 0
    _table_num = 0
    _last_level = 0

    def __init__(self):
        pass

    @staticmethod
    def _reset():
        """
        Possibility to Reset all internal numeration counters.

        :return:         -
        """
        Numeration._section = [0]
        Numeration._fig_num = 0
        Numeration._table_num = 0
        Numeration._last_level = 0

    @staticmethod
    def _build_section_number_string(level):
        """
        Build a numeration string for a current heading
        with a given level.

        :param level: Defines the Heading level
        :type level:  integer
        :return:      NumerationString (e.g. '1.1.2')
        :rtype:       string
        """
        # Remember the level for later usage
        Numeration._last_level = level

        # reset table and figure number as new chapter
        Numeration._fig_num = 0
        Numeration._table_num = 0

        # add next level if not yet there
        while level >= len(Numeration._section):
            Numeration._section.append(0)

        # Increase the correct level-number
        Numeration._section[level] += 1

        # And Reset More detailed Level numbers
        for lev in range(level + 1, len(Numeration._section)):
            Numeration._section[lev] = 0

        return ".".join([str(n) for n in Numeration._section if n != 0])

    def _build_figure_number_string(self):
        """
        Build a numeration string for the current figure.

        :return:      NumerationString (e.g. '1.1.2')
        :rtype:       string
        """
        Numeration._fig_num += 1
        return self._build_number_string(Numeration._fig_num)

    def _build_table_number_string(self):
        """
        Build a numeration string for the current Table.

        :return:      NumerationString (e.g. '1.1.2')
        :rtype:       string
        """
        Numeration._table_num += 1
        return self._build_number_string(Numeration._table_num)

    def _build_number_string(self, what):
        """
        Build numeration string for the current.

        :return:      NumerationString (e.g. '1.1.2')
        :rtype:       string
        """
        return "%s.%d" % (".".join([str(n) for i, n in enumerate(Numeration._section) if i <= self._last_level]), what)

    @deprecated('_reset')
    def _Reset(self):  # pylint: disable=C0103
        """deprecated"""
        return self._reset()

    @deprecated('_build_section_number_string')
    def _BuildSectionNumberString(self, level):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "_BuildSectionNumberString" is deprecated use "_build_section_number_string" instead',
        # stacklevel=2)
        return self._build_section_number_string(level)

    @deprecated('_build_figure_number_string')
    def _BuildFigureNumberString(self):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "_BuildFigureNumberString" is deprecated use "_build_figure_number_string" instead',
        # stacklevel=2)
        return self._build_figure_number_string()

    @deprecated('_build_table_number_string')
    def _BuildTableNumberString(self):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "_BuildTableNumberString" is deprecated use "_build_table_number_string" instead',
        # stacklevel=2)
        return self._build_table_number_string()


class TableBase(Numeration):
    """
    **Basic Table with integrated Numeration possibility.**

    This Table must be used for all other Table classes as parent class.

    :author:        Robert Hecker
    :date:          09.10.2013
    """
    TABLE_CAPTION = "Table"
    STYLE = ParagraphStyle(name='TableTitleStyle',
                           fontName="Times-Roman",
                           fontSize=10, leading=12)

    def __init__(self):
        Numeration.__init__(self)
        self._name = ""

    def append_caption(self, story):
        """ append caption of table to the story

        :param story: list of platypus flowables building the pdf
        :type story: list
        """
        if self._name is not None:
            tpar = plat.Paragraph("<b>%s %s</b>: %s" % (self.TABLE_CAPTION, self._build_table_number_string(),
                                                        replace_html_chars(self._name)), self.STYLE)
            # tpar.keepWithNext = True
            story.append(tpar)

    @deprecated('append_caption')
    def AppendCaption(self, story):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "AppendCaption" is deprecated use "append_caption" instead', stacklevel=2)
        return self.append_caption(story)


class Table(TableBase):  # pylint: disable=R0903
    """
    **Basic Table with integrated Numeration possibility.**

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    def __init__(self, name, data, **kwargs):
        TableBase.__init__(self)
        self._name = name
        self._data = data

        self._kwargs = kwargs

        # Process all kwargs and add some default settings if necessary
        style = kwargs.pop('style', [])
        if "GRID" not in [i[0] for i in style]:
            style.append(('GRID', (0, 0), (-1, -1), 1.0, colors.black))
        if kwargs.pop('topHeader', True):
            style.insert(0, ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey))
        self._kwargs['style'] = style
        self._cellstyle = kwargs.pop('cellstyle', None)
        self._header = kwargs.pop('header', None)
        self._styles = getSampleStyleSheet()

    def _create(self):
        """
        Does the final creation of the Platypus Table object.
        Including a correct numeration for the Table of Tables list.

        Typically this Method will be called by the _PreBuild-Method of
        the Story class.

        :return: story with all final objects for pdf rendering
        :rtype: list of platypus objects ready for rendering.
        """
        story = []
        data = []

        if self._header is not None:
            data.append(build_table_header(self._header))

        if self._cellstyle:
            data += [build_table_row(f, style=self._cellstyle) for f in self._data]
        else:
            data += self._data

        table = plat.Table(data, repeatRows=1, **self._kwargs)

        table.keepWithNext = True
        story.append(plat.Spacer(1, 0.2 * cm))
        story.append(table)
        # story.append(plat.Spacer(1, 1 * cm))

        self.append_caption(story)

        return story


class Image(Numeration):  # pylint: disable=R0903
    """
    **Basic Image with integrated Numeration possibility.**

    initialize with name (caption) of figure, the image object
    (plat drawing or loaded image) and optional width and hAlign

    Numeration uses chapter number (e.g. 2.1.3)
    with additional increasing index (2.1.3.1 ff)

    space of 1cm is added before and after the image

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    FIGURE_CAPTION = "Fig."
    STYLE = ParagraphStyle(name='FigureTitleStyle',
                           fontName="Times-Roman",
                           fontSize=10, leading=12)

    def __init__(self, name, image, mem_reduction=False, **kwargs):
        """
        preset class internal variables

        :param mem_reduction: If True, PNG images are converted to JPEG format before passing them to the
                              reportlab.platypus.flowables.Image class.
                              Also, the lazy=2 argument is used to open the image when required then shut it.
                              If False, no image conversion is done and the lazy=1 argument is used when calling
                              reportlab.platypus.flowables.Image to not open the image until required.
        :type mem_reduction:  boolean, optional, default: False
        """
        Numeration.__init__(self)
        self._name = name
        self._image = image
        self._width = kwargs.pop('width', (15 * cm))
        self._halign = kwargs.pop('hAlign', None)
        self._mem_reduction = mem_reduction

    def _create(self):
        """
        Does the final creation of the Platypus Image object.
        Including a correct numeration for the Figures list.

        Typically this Method will be called by the _PreBuild-Method of
        the Story class.

        :return: story with all final objects for pdf rendering
        :rtype: list of platypus objects ready for rendering.
        """
        story = []

        # Check if image is stored on disk
        if isinstance(self._image, basestring) and (os.path.isfile(self._image)):
            # Create a Platypus Image from the given image path
            img = utils.ImageReader(self._image)
            imgw, imgh = img.getSize()
            aspect = imgh / float(imgw)

            lazy_value = 1
            img_path = self._image
            if self._mem_reduction is True:
                # value 2 means "open the image when required then shut it"
                lazy_value = 2
                # the image is converted to JPEG only if it is a PNG
                if what_image_type(self._image) is "png":
                    base_file_name_without_ext = os.path.splitext(os.path.basename(self._image))[0]
                    full_dir_path = os.path.dirname(self._image)
                    img_path_jpeg = os.path.join(full_dir_path, base_file_name_without_ext + "." + "jpeg")
                    jpeg_image = pil_image.open(self._image)
                    jpeg_image.save(img_path_jpeg, "JPEG")
                    img_path = img_path_jpeg

            img = plat.Image(img_path, width=self._width,
                             height=(self._width * aspect), lazy=lazy_value)
        elif hasattr(self._image, 'wrapOn'):
            img = self._image
        else:
            # unknown image or image with unsupported type
            print("pdf build warning: unknown image type for image with caption: %s" % self._name)
            img = plat.Paragraph("unknown image type", NORMAL_STYLE)
            self._halign = None

        # align horizontally TO 'LEFT', 'CENTER' (default) or
        # 'RIGHT' as supported by plat.Flowable
        # use already set value if no change requested
        if self._halign:
            img.hAlign = self._halign

        # Add Image
        flowables = [plat.Spacer(1, 1 * cm), img]

        # Add Title
        if self._name is not None:
            flowables.append(plat.Paragraph("<b>%s %s</b>: %s" %
                                            (self.FIGURE_CAPTION, self._build_figure_number_string(),
                                             replace_html_chars(self._name)), self.STYLE))
            flowables.append(plat.Spacer(1, 1 * cm))

        # Add everything to story
        story.append(plat.KeepTogether(flowables))

        return story

    @deprecated('_create')
    def _Create(self):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "_Create" is deprecated use "_create" instead', stacklevel=2)
        return self._create()


class Heading(Numeration):  # pylint: disable=R0902, R0903
    """
    **Basic Headings with integrated Numeration possibility.**

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    def __init__(self, heading="", level=0):
        Numeration.__init__(self)
        self.heading = heading
        self.level = level

        self.header = [ParagraphStyle(name='Heading1', fontSize=16, fontName="Times-Bold", leading=22),
                       ParagraphStyle(name='Heading2', fontSize=14, fontName="Times-Roman", leading=18),
                       ParagraphStyle(name='Heading3', fontSize=12, fontName="Times-Roman", leading=12),
                       ParagraphStyle(name='Heading4', fontSize=11, fontName="Times-Roman", leading=11)]

        self.notoc_h1 = ParagraphStyle(name='NoTOCHeading1', fontSize=16, fontName="Times-Bold", leading=22)
        self.toc_h1 = ParagraphStyle(name='Heading1', fontSize=14, fontName="Times-Bold", leftIndent=6)
        self.notoc_h2 = ParagraphStyle(name='NoTOCHeading2', fontSize=14, fontName="Times-Roman", leading=18)
        self.toc_h2 = ParagraphStyle(name='Heading2', fontSize=12, fontName="Times-Roman", leftIndent=12)
        self.notoc_h3 = ParagraphStyle(name='NoTOCHeading3', fontSize=12, fontName="Times-Roman", leading=12)
        self.toc_h3 = ParagraphStyle(name='Heading3', fontSize=11, fontName="Times-Roman", leftIndent=32)
        self.notoc_h4 = ParagraphStyle(name='NoTOCHeading4', fontSize=10, fontName="Times-Roman", leading=10)
        self.toc_h4 = ParagraphStyle(name='Heading4', fontSize=11, fontName="Times-Roman", leftIndent=32)

    def _create(self):
        """
        Does the final creation of the Platypus Heading object.
        Including a correct numeration for the headings.

        Typically this Method will be called by the _PreBuild-Method of
        the Story class.

        :return: story with all final objects for pdf rendering
        :rtype: list of platypus objects ready for rendering.
        """
        story = []

        # if pageBreak:
        #    self._story.append(PageBreak())

        if self.level > 0:
            story.append(plat.Spacer(1, 1.5 * cm))

        # Get Current Section Number
        num = self._build_section_number_string(self.level)

        story.append(plat.Paragraph(num + " " + self.heading, self.header[self.level if self.level < 4 else 3]))

        return story

    @deprecated('_create')
    def _Create(self):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "_Create" is deprecated use "_create" instead', stacklevel=2)
        return self._create()


class RotatedText(plat.Flowable):
    """
    **rotates a text or paragraph 90 deg left**

    intended for a table cell (graph and chart have own methods)
    """
    def __init__(self, para):
        """
        take over either a Paragraph or raw text

        :param para: text to rotate
        :type para:  string or Paragraph
        """
        plat.Flowable.__init__(self)
        self.para = para
        if type(self.para) != str and self.para.text.startswith('<b>') and self.para.text.endswith('</b>'):
            self.para.text = self.para.text[3:-4]
            if not self.para.style.fontName.endswith('-Bold'):
                self.para.style.fontName += '-Bold'

    def draw(self):
        """
        added method to draw the rotated text,
        will be called during `Story.Build`
        """
        canv = self.canv
        canv.saveState()
        canv.rotate(90)
        if type(self.para) == str:
            canv.drawString(0, -3, self.para)
        else:
            canv.setFont(self.para.style.fontName, self.para.style.fontSize, self.para.style.leading)
            canv.drawString(0, -3, self.para.getPlainText())
        canv.restoreState()

    def wrap(self, availWidth, availHeight):  # pylint: disable=W0613
        """
        overloaded wrap method

        :param availWidth: not used here
        :param availHeight: not used here
        :return: real width and height of the flowable
        :rtype:  set(integer, integer)
        """
        canv = self.canv
        if type(self.para) == str:
            return canv._leading, canv.stringWidth(self.para)  # pylint: disable=W0212
        else:
            return canv._leading, canv.stringWidth(self.para.getPlainText(),  # pylint: disable=W0212
                                                   self.para.style.fontName, self.para.style.fontSize)


class RepPageBreak(FrameActionFlowable):
    '''
    own report class for conditional page breaks

    adds action to the current frame called during build
    '''

    def __init__(self, template_name=None, break_to='any'):
        '''template_name switches the page template starting in the
        next page.

        break_to can be 'any' 'even' or 'odd'.

        'even' will break one page if the current page is odd
        or two pages if it's even. That way the next flowable
        will be in an even page.

        'odd' is the opposite of 'even'

        'any' is the default, and means it will always break
        only one page.

        '''
        # FrameActionFlowable is abstract and has no callable __init__
        # pylint: disable=W0231

        self.template_name = template_name
        self.break_to = break_to
        self.forced = False
        self.extra_content = []

    def frameAction(self, frame):
        '''
        overwritten method to set new template during build

        :param frame: element holding several flowables that should be printed
        :type  frame: instance of platypus.frames.Frame
        '''
        # platypus uses access to protected members:
        # pylint: disable=W0212

        frame._generated_content = []
        if self.break_to == 'any':  # Break only once. None if at top of page
            if not frame._atTop:
                frame._generated_content.append(SetNextTemplate(self.template_name))
                frame._generated_content.append(plat.PageBreak())
        elif self.break_to == 'odd':    # Break once if on even page, twice
                                        #  on odd page, none if on top of odd page
            if self.canv._pageNumber % 2:  # odd pageNumber
                if not frame._atTop:
                    # Blank pages get no heading or footer
                    frame._generated_content.append(SetNextTemplate(self.template_name))
                    frame._generated_content.append(SetNextTemplate('emptyPage'))
                    frame._generated_content.append(plat.PageBreak())
                    frame._generated_content.append(ResetNextTemplate())
                    frame._generated_content.append(plat.PageBreak())
            else:  # even
                frame._generated_content.append(SetNextTemplate(self.template_name))
                frame._generated_content.append(plat.PageBreak())
        elif self.break_to == 'even':  # Break once if on odd page, twice
                                   # on even page, none if on top of even page
            if self.canv._pageNumber % 2:  # odd pageNumber
                frame._generated_content.append(SetNextTemplate(self.template_name))
                frame._generated_content.append(plat.PageBreak())
            else:  # even
                if not frame._atTop:
                    # Blank pages get no heading or footer
                    frame._generated_content.append(SetNextTemplate(self.template_name))
                    frame._generated_content.append(SetNextTemplate('emptyPage'))
                    frame._generated_content.append(plat.PageBreak())
                    frame._generated_content.append(ResetNextTemplate())
                    frame._generated_content.append(plat.PageBreak())


class SetNextTemplate(plat.Flowable):
    """Set canv.template_name when drawing.

    rep uses that to switch page templates.

    """

    def __init__(self, template_name=None):
        self.template_name = template_name
        plat.Flowable.__init__(self)

    def draw(self):
        """
        added method to switch to the set template,
        will be called during `Story.Build`
        """
        if self.template_name:
            try:
                self.canv.old_template_name = self.canv.template_name
            except AttributeError:
                self.canv.old_template_name = 'oneColumn'
            self.canv.template_name = self.template_name


class ResetNextTemplate(plat.Flowable):
    """Go back to the previous template.

    rep uses that to switch page templates back when
    temporarily it needed to switch to another template.

    For example, after an OddPageBreak, there can be a totally
    blank page. Those have to use coverPage as a template,
    because they must not have headers or footers.

    And then we need to switch back to whatever was used.

    """
    def __init__(self):
        plat.Flowable.__init__(self)

    def draw(self):
        '''
        added draw method to Flowable to switch templates, called during Stroy.Build
        '''
        self.canv.template_name, self.canv.old_template_name = self.canv.old_template_name, self.canv.template_name

    # disabling pylint check for unused arguments, defined in original Flowable.wrap
    def wrap(self, width, high):  # pylint: disable=W0613
        '''
        overloaded wrap method returns actual width and high of the template switch
        '''
        return 0, 0


"""
CHANGE LOG:
-----------
$Log: flowables.py  $
Revision 1.9 2017/08/25 15:47:08CEST Hospes, Gerd-Joachim (uidv8815) 
static check fixes
Revision 1.8 2017/08/01 11:36:13CEST Hospes, Gerd-Joachim (uidv8815)
new error hints for wrong image path and type, module  test exrended
Revision 1.7 2017/01/23 15:47:54CET Hospes, Gerd-Joachim (uidv8815)
go back to former version but add cellstyle keyw. to Table, add test
Revision 1.6 2016/12/01 11:22:30CET Hospes, Gerd-Joachim (uidv8815)
fix docu errors
Revision 1.5 2016/11/30 16:07:42CET Hospes, Gerd-Joachim (uidv8815)
fix table generation with non text content
Revision 1.4 2016/11/17 11:20:25CET Hospes, Gerd-Joachim (uidv8815)
move table formatter methods to pdf.base to support line break for columns in base.flowable.Table
Revision 1.3 2015/08/26 16:53:49CEST Hospes, Gerd-Joachim (uidv8815)
table caption below the table
- Added comments -  uidv8815 [Aug 26, 2015 4:53:50 PM CEST]
Change Package : 371081:1 http://mks-psad:7002/im/viewissue?selection=371081
Revision 1.2 2015/06/11 11:00:56CEST Hospes, Gerd-Joachim (uidv8815)
headings extended
--- Added comments ---  uidv8815 [Jun 11, 2015 11:00:56 AM CEST]
Change Package : 346795:1 http://mks-psad:7002/im/viewissue?selection=346795
Revision 1.22 2015/03/06 15:39:10CET Ellero, Stefano (uidw8660)
Implemented the optional parameter "mem_reduction" in the base class for all report templates
(stk.rep.pdf.base.pdf.Story) to reduce the memory usage during a pdf report generation.
--- Added comments ---  uidw8660 [Mar 6, 2015 3:39:24 PM CET]
Change Package : 307809:1 http://mks-psad:7002/im/viewissue?selection=307809
Revision 1.21 2015/01/26 20:20:17CET Ellero, Stefano (uidw8660)
Removed all rep based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 26, 2015 8:20:17 PM CET]
Change Package : 296836:1 http://mks-psad:7002/im/viewissue?selection=296836
Revision 1.20 2015/01/22 20:34:12CET Ellero, Stefano (uidw8660)
Removed all util based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 22, 2015 8:34:13 PM CET]
Change Package : 296837:1 http://mks-psad:7002/im/viewissue?selection=296837
Revision 1.19 2014/12/16 16:48:11CET Hospes, Gerd-Joachim (uidv8815)
add break_to feature to add_page_break()
--- Added comments ---  uidv8815 [Dec 16, 2014 4:48:12 PM CET]
Change Package : 292136:1 http://mks-psad:7002/im/viewissue?selection=292136
Revision 1.18 2014/06/26 11:15:58CEST Hospes, Gerd-Joachim (uidv8815)
fine tuning of epydoc for AlgoTestReport and base
--- Added comments ---  uidv8815 [Jun 26, 2014 11:15:58 AM CEST]
Change Package : 243858:2 http://mks-psad:7002/im/viewissue?selection=243858
Revision 1.17 2014/06/25 10:31:33CEST Hospes, Gerd-Joachim (uidv8815)
fix pylint warnings
--- Added comments ---  uidv8815 [Jun 25, 2014 10:31:33 AM CEST]
Change Package : 243858:1 http://mks-psad:7002/im/viewissue?selection=243858
Revision 1.16 2014/06/24 17:01:27CEST Hospes, Gerd-Joachim (uidv8815)
move table caption below table, extend some epydoc
--- Added comments ---  uidv8815 [Jun 24, 2014 5:01:27 PM CEST]
Change Package : 243858:1 http://mks-psad:7002/im/viewissue?selection=243858
Revision 1.15 2014/04/25 09:34:36CEST Hecker, Robert (heckerr)
Get new Update from Sven.
--- Added comments ---  heckerr [Apr 25, 2014 9:34:37 AM CEST]
Change Package : 233054:1 http://mks-psad:7002/im/viewissue?selection=233054
Revision 1.14 2014/04/11 13:09:52CEST Mertens, Sven (uidv7805)
fix for table and image enumeration problem
--- Added comments ---  uidv7805 [Apr 11, 2014 1:09:52 PM CEST]
Change Package : 227498:1 http://mks-psad:7002/im/viewissue?selection=227498
Revision 1.13 2014/04/07 14:09:24CEST Hospes, Gerd-Joachim (uidv8815)
pep8 & pylint fixes after adding new packages and splitting some modules
--- Added comments ---  uidv8815 [Apr 7, 2014 2:09:25 PM CEST]
Change Package : 227496:1 http://mks-psad:7002/im/viewissue?selection=227496
Revision 1.12 2014/03/28 11:32:44CET Hecker, Robert (heckerr)
commented out warnings.
--- Added comments ---  heckerr [Mar 28, 2014 11:32:44 AM CET]
Change Package : 228098:1 http://mks-psad:7002/im/viewissue?selection=228098
Revision 1.11 2014/03/28 10:25:49CET Hecker, Robert (heckerr)
Adapted to new coding guiedlines incl. backwardcompatibility.
--- Added comments ---  heckerr [Mar 28, 2014 10:25:49 AM CET]
Change Package : 228098:1 http://mks-psad:7002/im/viewissue?selection=228098
Revision 1.10 2014/03/27 12:24:46CET Hecker, Robert (heckerr)
Added backwardcompatibility with six.
--- Added comments ---  heckerr [Mar 27, 2014 12:24:46 PM CET]
Change Package : 227240:2 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.9 2014/03/26 17:23:23CET Hospes, Gerd-Joachim (uidv8815)
new option hAlign for Story.AddImage, tested in test_report and test_plot
--- Added comments ---  uidv8815 [Mar 26, 2014 5:23:23 PM CET]
Change Package : 224334:1 http://mks-psad:7002/im/viewissue?selection=224334
Revision 1.8 2014/03/26 13:28:09CET Hecker, Robert (heckerr)
Added python 3 changes.
--- Added comments ---  heckerr [Mar 26, 2014 1:28:09 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.7 2014/03/17 18:24:33CET Hospes, Gerd-Joachim (uidv8815)
add Heading4 and according style for TOC
--- Added comments ---  uidv8815 [Mar 17, 2014 6:24:34 PM CET]
Change Package : 224320:1 http://mks-psad:7002/im/viewissue?selection=224320
Revision 1.6 2014/03/12 14:09:29CET Hospes, Gerd-Joachim (uidv8815)
fix numeration of figures, starting with x.y.1 for each new chapter
--- Added comments ---  uidv8815 [Mar 12, 2014 2:09:29 PM CET]
Change Package : 221503:1 http://mks-psad:7002/im/viewissue?selection=221503
Revision 1.5 2014/02/28 10:54:54CET Hospes, Gerd-Joachim (uidv8815)
new rotated text feature added to epidoc for algo_test_report
--- Added comments ---  uidv8815 [Feb 28, 2014 10:54:55 AM CET]
Change Package : 219820:2 http://mks-psad:7002/im/viewissue?selection=219820
Revision 1.4 2014/02/21 16:55:43CET Hospes, Gerd-Joachim (uidv8815)
add RotatedText() method for table cells in rep.pdf.algo_test.flowables
--- Added comments ---  uidv8815 [Feb 21, 2014 4:55:43 PM CET]
Change Package : 219820:1 http://mks-psad:7002/im/viewissue?selection=219820
Revision 1.3 2013/10/25 09:02:29CEST Hecker, Robert (heckerr)
Removed Pep8 Issues.
--- Added comments ---  heckerr [Oct 25, 2013 9:02:30 AM CEST]
Change Package : 202843:1 http://mks-psad:7002/im/viewissue?selection=202843
Revision 1.2 2013/10/18 17:21:43CEST Hecker, Robert (heckerr)
Get Image class and Table class working.
--- Added comments ---  heckerr [Oct 18, 2013 5:21:43 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.1 2013/10/18 09:22:13CEST Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/rep/pdf/base/project.pj
"""
