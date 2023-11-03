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
:author:        Leidenberger, Ralf

:version:       $Revision: 1.1 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/25 21:28:03CET $
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
from PIL import Image as pilImage

# needed when deprecation warnings are activated:
# import warnings

# Import STK Modules -----------------------------------------------------------

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

    def create(self):
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

    def create(self):
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
                    jpeg_image = pilImage.open(self._image)
                    jpeg_image = jpeg_image.convert("RGB")
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

    def create(self):
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
        # noinspection PyTypeChecker,PyCallByClass
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

    def wrap(self, avail_width, avail_height):  # pylint: disable=W0613
        """
        overloaded wrap method

        :param avail_width: not used here
        :param avail_height: not used here
        :return: real width and height of the flowable
        :rtype:  set(integer, integer)
        """
        canv = self.canv
        if type(self.para) == str:
            # noinspection PyProtectedMember
            return canv._leading, canv.stringWidth(self.para)  # pylint: disable=W0212
        else:
            # noinspection PyProtectedMember
            return canv._leading, canv.stringWidth(self.para.getPlainText(),  # pylint: disable=W0212
                                                   self.para.style.fontName, self.para.style.fontSize)


class RepPageBreak(FrameActionFlowable):
    """
    own report class for conditional page breaks

    adds action to the current frame called during build
    """

    def __init__(self, template_name=None, break_to='any'):
        """template_name switches the page template starting in the
        next page.

        break_to can be 'any' 'even' or 'odd'.

        'even' will break one page if the current page is odd
        or two pages if it's even. That way the next flowable
        will be in an even page.

        'odd' is the opposite of 'even'

        'any' is the default, and means it will always break
        only one page.

        """
        # FrameActionFlowable is abstract and has no callable __init__
        # pylint: disable=W0231
        FrameActionFlowable.__init__(self)
        self.template_name = template_name
        self.break_to = break_to
        self.forced = False
        self.extra_content = []

    def frameAction(self, frame):
        """
        overwritten method to set new template during build

        :param frame: element holding several flowables that should be printed
        :type  frame: instance of platypus.frames.Frame
        """
        # platypus uses access to protected members:
        # pylint: disable=W0212
        frame._generated_content = []
        if self.break_to == 'any':  # Break only once. None if at top of page
            # noinspection PyProtectedMember
            if not frame._atTop:
                frame._generated_content.append(SetNextTemplate(self.template_name))
                frame._generated_content.append(plat.PageBreak())
        elif self.break_to == 'odd':    # Break once if on even page, twice
                                        #  on odd page, none if on top of odd page
            # noinspection PyProtectedMember
            if self.canv._pageNumber % 2:  # odd pageNumber
                # noinspection PyProtectedMember
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
        elif self.break_to == 'even':  # Break once if on odd page, twice on even page, none if on top of even page
            # noinspection PyProtectedMember
            if self.canv._pageNumber % 2:  # odd pageNumber
                frame._generated_content.append(SetNextTemplate(self.template_name))
                frame._generated_content.append(plat.PageBreak())
            else:  # even
                # noinspection PyProtectedMember
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
        # noinspection PyTypeChecker,PyCallByClass
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
        # noinspection PyTypeChecker,PyCallByClass
        plat.Flowable.__init__(self)

    def draw(self):
        """
        added draw method to Flowable to switch templates, called during Stroy.Build
        """
        self.canv.template_name, self.canv.old_template_name = self.canv.old_template_name, self.canv.template_name

    # disabling pylint check for unused arguments, defined in original Flowable.wrap
    def wrap(self, width, high):  # pylint: disable=W0613
        """
        overloaded wrap method returns actual width and high of the template switch
        """
        return 0, 0


"""
CHANGE LOG:
-----------
$Log: flowables.py  $
Revision 1.1 2020/03/25 21:28:03CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/rep/pdf/base/project.pj
"""
