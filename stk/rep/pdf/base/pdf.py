"""
stk/rep/pdf/base/pdf
--------------------

**Module for writing basic pdf Reports.**

**User-API Interfaces**

    - `.Pdf`  wrapper class to instantiate and build basic "freehand" pdf reports.
    - `Story` base class providing methods to fill/format the report.

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.6 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/08/25 15:47:07CEST $
"""
# Import Python Modules --------------------------------------------------------
from os import path, makedirs
from inspect import getsourcefile
from reportlab.lib.units import cm
import reportlab.platypus as plat
import reportlab.platypus.doctemplate as dtp
# import warnings when activating deprecation warnings

# Import STK Modules -----------------------------------------------------------
from . import flowables as flow
from . import template as template
from .template import PdfDocTemplate
from ..algo_base import flowables as algoflow
from ....error import StkError
from stk.util.helper import deprecated

# Defines ----------------------------------------------------------------------
PAGE_TEMPLATE_PORTRAIT = template.PAGE_TEMPLATE_PORTRAIT
PAGE_TEMPLATE_LANDSCAPE = template.PAGE_TEMPLATE_LANDSCAPE
BROKEN_IMAGE_PATH = path.join(path.abspath(path.dirname(getsourcefile(lambda: 0))),
                              '..', '..', 'image', 'broken_image.jpg')

# Functions --------------------------------------------------------------------


def create_dir(filepath):
    """
    if needed create the directory for the given filename incl. the path

    raises StkError if no dir could be found or created

    :param filepath: path and filename
    :type filepath: string
    """
    pathname = path.dirname(filepath)
    if not path.isdir(pathname):
        try:
            makedirs(pathname)
        except Exception:
            raise StkError("Error while creating folder: '%s'." % pathname)
    return

# Classes ----------------------------------------------------------------------


class Story(object):
    """
    **Wrapper class around the story list container.**

    Base class for all report templates. This container collects the whole pdf-story which
    will be rendered at a later point of time.

    **User-API Interfaces**

      Provides methods to fill/format the pdf document:

        - `add_heading()`
        - `add_paragraph()`
        - `add_table()`
        - `add_image()`
        - `add_space()`
        - `add_page_break()`
        - `add_table_of_content()`
        - `add_table_of_tables()`
        - `add_table_of_figures()`
        - `change_page_template()`

    **example**:

      .. python::

        doc = pdf.Pdf()

        doc.add_table_of_content()
        doc.add_heading("Chapter 1", 0)
        doc.add_heading("Chapter 1.1", 1)
        doc.add_heading("Chapter 1.1.1", 2)
        doc.add_paragraph("This is a basic pdf document")
        doc.add_space(0.7)
        doc.add_paragraph("text after the spacer.....")
        doc.add_table('My first table', [['a', 'b', 'c'], [1, 2, 3]],
                      header=['col a', 'col b', 'col c'], topHeader=True)
        doc.add_page_break()
        doc.add_image('Image from Disk', IMG_PATH)
        doc.add_table_of_figures()

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    def __init__(self, style, mem_reduction=False):
        """
        preset class internal variables

        :param mem_reduction: If True, PNG images are converted to JPEG format before passing them to the
                              reportlab.platypus.flowables.Image class.
                              Also, the lazy=2 argument is used to open the image when required then shut it.
                              If False, no image conversion is done and the lazy=1 argument is used when calling
                              reportlab.platypus.flowables.Image to not open the image until required.
        :type mem_reduction:  boolean, optional, default: False
        """
        self._story = []
        self.style = style
        self.styles = style.styles
        self._mem_reduction = mem_reduction

    def __get_story(self):
        ''' default __get, why is it needed here??? '''
        return self._story

    def __set_story(self, value):
        ''' default __set, why is it needed here??? '''
        self._story = value

    story = property(__get_story, __set_story)
    """
    Internal story, which will be stored for later usage.

    :type: list of pdf/helper objects.
    """

    def add_table_of_content(self):
        """
        **Add the Table Of Contents to the story.**

        Normally called at the beginning of the complete pdf (e.g. after title page).
        Adds page break at end of content table.

        :return:      -
        """
        toc = algoflow.TableOfContents()
        self._story += toc._create()  # pylint: disable=W0212

    def add_table_of_figures(self):
        """
        **Add the Table Of Figures to the story.**

        Usually placed at the end of the pdf. Adds page break at beginning of table.

        :return:      -
        """
        tof = algoflow.TableOfFigures()
        self._story += tof._create()  # pylint: disable=W0212

    def add_table_of_tables(self):
        """
        **Add the Table Of Tables to the story.**

        Usually placed at the end of the pdf. Adds page break at beginning of table.

        :return:      -
        """
        tot = algoflow.TableOfTables()
        self._story += tot._create()  # pylint: disable=W0212

    def add_paragraph(self, text, style='Normal'):
        """
        **Add a new Paragraph to the story.**

        taken from platypus.Paragraph documentation:

        The paragraph Text can contain XML-like markup including the tags::

            <b> ... </b> - bold
            <i> ... </i> - italics
            <u> ... </u> - underline
            <strike> ... </strike> - strike through
            <super> ... </super> - superscript
            <sub> ... </sub> - subscript
            <font name=fontfamily/fontname color=colorname size=float>
            <span name=fontfamily/fontname color=colorname backcolor=colorname size=float style=stylename>
            <onDraw name=callable label="a label"/>
            <index [name="callablecanvasattribute"] label="a label"/>
            <link>link text</link>
            attributes of links
            size/fontSize=num
            name/face/fontName=name
            fg/textColor/color=color
            backcolor/backColor/bgcolor=color
            dest/destination/target/href/link=target
            <a>anchor text</a>
            attributes of anchors
            fontSize=num
            fontName=name
            fg/textColor/color=color
            backcolor/backColor/bgcolor=color
            href=href

        **example:**

        .. python::

            doc = pdf.Pdf()

            doc.add_paragraph('''This text is written in one paragraph.
                              New line and additional spaces are ignored,
                              the text will be aligned to fit the page width.
                              The paragraph text can contain XML-like markup including the tags:
                              <b> bold text </b> and <i> italics text </i> can be used
                              inside a paragraph.''', style='Title')

        :param text: text, which must be added to the story.
        :type text: string
        :param style: style, which must be added to the story.
                      Examples of style: 'Title', 'BodyText', 'Italic', 'Heading1', 'Heading4', 'Heading6', ...
                      For more style options go to reportlab.lib.styles.getSampleStyleSheet.
        :type style: string
        :return:
        """
        self._story.append(plat.Paragraph(text, self.styles[style]))

    def add_page_break(self, break_to=None):
        """
        Add a new PageBreak to the story.

        :param break_to: next page number after break:
                         'odd' (front side of paper or left side in book) or
                         'even' (back side of paper or right side in book)
        :type  break_to: str
        :return:         -
        """
        if not break_to:
            self._story.append(plat.PageBreak())
        else:
            self._story.append(flow.RepPageBreak(break_to=break_to))

    def add_space(self, space):
        """
        Add a Space before the next Item of the story.

        :param space: wanted space in cm.
        :type space:  float
        :return:      -
        """
        self._story.append(plat.Spacer(1, space * cm))

    def add_table(self, name, data, **kwarg):
        """
        **Add a table with caption to the story.**

        If column widths are not defined it is set during rendering. If total width of table exceeds page width
        max page width is used for all columns together. Long words are not broken to fit in the column and
        can be extended over following column (see keyword `cellstyle` to switch on).

        To prevent overwriting next column define column width. Then long words will be broken at column end and
        continued in a new line.

        If the table name (caption) is set to 'None' no caption will be printed and in addition
        the table will not be listed in the 'Table of Tables' at the end of the document.

        **example:**

        .. python::

            doc = pdf.Pdf()
            TABLE_COLUMN = ['First Name', 'Last Name', 'Phone']
            TABLE_DATA = [['Arthur', 'Dent', '4242'],
                          ['Fort', 'Perfect', '500']]

            doc.add_table('My first table', TABLE_DATA, header=TABLE_COLUMN,
                          colWidths=[100, 100, 60], topHeader=True)

        :param name:       Name (caption) of table
        :type name:        string
        :param data:       values of the table
        :type data:        list[list[string]]
        :Param kwarg:      list of optional parameters
        :kwarg header:     separate headerline in standard format
        :type header:      list[strings]
        :kwarg colWidths:  specify the column With of every column
        :type colWidths:   list[float]
        :kwarg topHeader:  Used to specify a background for the header line
        :type topHeader:   `True` when header should have background color grey.
        :kwarg style:       pass lists with style settings for the columns, find examples at:
                http://www.blog.pythonlibrary.org/2010/09/21/reportlab-tables-creating-tables-in-pdfs-with-python/
        :type style:        list[list[name of setting, first cell, last cell, options]]
        :kwarg cellstyle:   platypus Paragraph style to be used for text in cells,
                            e.g. set to flow.NORMAL_SPLIT if you also want to wrap long strings to fit into the cell
        :type cellstyle:    platypus.ParagraphStyle
        :return:            -
        """
        table = flow.Table(name, data, **kwarg)

        self._story.append(table)

    def add_image(self, name, image, **kwarg):
        r"""
        **Add an Image to the story.**

        This method can append following images to the story:

          - Images given via file path (e.g.: c:/test.jpeg)
          - Images given as  as platypus.Image
          - Images created by `ValidationPlot`

        **example:**

        .. python::

            import reportlab.platypus as plat
            from stk.rep.pdf.base import pdf
            from stk.img import plot

            doc = pdf.Pdf()
            # add first image
            doc.add_image('imported image, smaller, set to right', r'file\plot.png',
                          width=250, hAlign='RIGHT')

            # platypus Image
            img = plat.Image(r'c:\project\image.png', width=450, height=200)
            doc.add_image('Image from Memory', img)

            # add image from plot module
            timestamps = range(5)
            values = [2.0, 3.2, 4.3, 4.1, 3.75]
            x_ext = [timestamps[0], timestamps[-1]]
            y_ext = [0, max(values) * 1.05]
            data = [zip(timestamps, values)]
            img = plot.ValidationPlot(OUT_FOLDER)
            img.generate_plot(data, [], "time [s]", "[m]", True, True,
                              title="Distance", x_axis_ext=x_ext, y_axis_ext=y_ext)
            drawing = img.get_drawing_from_buffer(img.get_plot_data_buffer(), "1", width=450, height=200)
            doc.add_image("image from plot module", drawing)

        :param name:    name or description to be added below the image
        :type name:     string
        :param image:   The image itself.
        :type image:    path (string) or platypus.Image
        :Param kwarg:   list of optional parameters
        :kwarg width:   width of image. (e.g. width=(15 * cm))
                        if width is specified aspect ratio will be kept.
                        width will only work, if image parameter is a path
                        to a file.
        :type width:    float
        :kwarg hAlign:  alignment of the image
        :type hAlign:   string 'LEFT', 'RIGHT' or 'CENTER'
        :return:        -
        """
        if type(image) is str and not path.isfile(image):
            # for missing file: replace image and give warning
            print("pdf story creation warning: can not read file %s!" % image)
            # broken = "missing file %s\n" % image
            name = name + "\nmissing file %s\n" % image
            image = BROKEN_IMAGE_PATH
        # Create Own Image Container for the Image
        img = flow.Image(name, image, self._mem_reduction, **kwarg)

        # Append Image Container to the story.
        self._story.append(img)

    def add_heading(self, heading, level):
        """
        **Add a new Heading to the story.**

        The indices are incremented according to the level of the heading.
        Currently 4 levels are supported for pdf reports, creating heading numbering from "1." to "1.1.1.1".

        :param heading:  the heading name which shall be printed.
        :type heading:   string
        :param level:    The level of the heading.
        :type level:     integer [0,1,2,3]
        :return:         -
        """
        head = flow.Heading(heading, level)
        self._story.append(head)

    def change_page_template(self, new_template):
        """
        **Method to switch between different supported PageTemplates.**

        Valid Templates are:

        - `PAGE_TEMPLATE_PORTRAIT`
        - `PAGE_TEMPLATE_LANDSCAPE`

        :param new_template: The Template which must be used for the following Pages.
        :type new_template:  stings as defined in `stk.pdf.base.template`
        :return:         -
        """
        # Check if we get a valid template
        if((new_template == PAGE_TEMPLATE_PORTRAIT) or
           (new_template == PAGE_TEMPLATE_LANDSCAPE)):
            # Set the Template
            self._story.append(dtp.NextPageTemplate(new_template))

    def _pre_build(self):
        """
        This Method is used to go through the whole story, and prepare
        the numeration for Headings, Tables and figures.

        :return:   story ready for a doc build.
        :rtype:    story (Paragraph object formatted in the correct way.)
        """
        # Initialize the new Story
        story = []
        # Reset all Counters for the "new" story
        flow.Numeration()._reset()  # pylint: disable=W0212

        for item in self._story:
            if isinstance(item, flow.Numeration):
                # Do the final Creation of the story object here.
                story += item._create()  # pylint: disable=W0212
            else:
                story.append(item)

        return story

    def append(self, story):
        """ append next flowable to the story list

        :param story: sub-story to add
        :type story:  story
        """
        self._story.append(story)

    @deprecated('append')
    def Append(self, story):  # pylint: disable=C0103
        """
        :deprecated: please use append() method instead
        """
        # warnings.warn('Method "Append" is deprecated use "append" instead', stacklevel=2)
        return self.append(story)

    @deprecated('add_paragraph')
    def AddParagraph(self, text):  # pylint: disable=C0103
        """
        :deprecated: please use add_paragraph() method instead
        """
        # warnings.warn('Method "AddParagraph" is deprecated use "add_paragraph" instead', stacklevel=2)
        return self.add_paragraph(text)

    @deprecated('add_page_break')
    def AddPageBreak(self):  # pylint: disable=C0103
        """
        :deprecated: please use add_page_break() method instead
        """
        # warnings.warn('Method "AddPageBreak" is deprecated use "add_page_break" instead', stacklevel=2)
        return self.add_page_break()

    @deprecated('add_space')
    def AddSpace(self, space):  # pylint: disable=C0103
        """
        :deprecated: please use add_space() method instead
        """
        # warnings.warn('Method "AddSpace" is deprecated use "add_space" instead', stacklevel=2)
        return self.add_space(space)

    @deprecated('add_table')
    def AddTable(self, name, data, **kwarg):  # pylint: disable=C0103
        """
        :deprecated: please use add_table() method instead
        """
        # warnings.warn('Method "AddTable" is deprecated use "add_table" instead', stacklevel=2)
        return self.add_table(name, data, **kwarg)

    @deprecated('add_image')
    def AddImage(self, name, image, **kwarg):  # pylint: disable=C0103
        """
        :deprecated: please use add_image() method instead
        """
        # warnings.warn('Method "AddImage" is deprecated use "add_image" instead', stacklevel=2)
        return self.add_image(name, image, **kwarg)

    @deprecated('add_heading')
    def AddHeading(self, heading, level):  # pylint: disable=C0103
        """
        :deprecated: please use add_heading() method instead
        """
        # warnings.warn('Method "AddHeading" is deprecated use "add_heading" instead', stacklevel=2)
        return self.add_heading(heading, level)

    @deprecated('change_page_template')
    def ChangePageTemplate(self, next_template):  # pylint: disable=C0103
        """
        :deprecated: please use change_page_template() method instead
        """
        # warnings.warn('Method "ChangePageTemplate" is deprecated use "change_page_template" instead', stacklevel=2)
        return self.change_page_template(next_template)

    @deprecated('_pre_build')
    def _PreBuild(self):  # pylint: disable=C0103
        """
        :deprecated: please use _pre_build() method instead
        """
        # warnings.warn('Method "_PreBuild" is deprecated use "_pre_build" instead', stacklevel=2)
        return self._pre_build()


class Pdf(Story):
    r"""
    **This is the main Interface for creating a pdf-document.**

    Use this class to create simple pdf - documents.

    Use this class as an example how following elements are connected together

    - Pdf class
    - `Story`
    - `BaseDocTemmplates` (internal API)
    - `PageTemplates` (internal API)
    - Helper classes like Numeration, Image, Heading, Table,......

    **example pdf**

    There are examples created by our module test:

     - blank report only using page sizes at basic.pdf_
     - blank report using base templates with page header and footer at basic_with_template.pdf_
     - both created by `STK\\05_Testing\\05_Test_Environment\\moduletest\\test_rep\\test_pdf\\test_base\\test_pdf.py`,
       please check the test for further code examples


    **Example:**

    .. python::

        # Import stk.rep
        import stk.rep

        # Create a instance of the Pdf class.
        doc = rep.Pdf()

        # Write Something into the pdf
        doc.add_paragraph("Hello World")

        # Render pdf story to file
        doc.build('out.pdf')

.. _basic.pdf: http://uud296ag:8080/job/STK_NightlyBuild/lastSuccessfulBuild/artifact/
               05_Testing/04_Test_Data/02_Output/rep/basic.pdf
.. _basic_with_template.pdf: http://uud296ag:8080/job/STK_NightlyBuild/lastSuccessfulBuild/artifact/
                             05_Testing/04_Test_Data/02_Output/rep/basic_with_template.pdf

    :author:        Robert Hecker
    :date:          22.09.2013
    """
    def __init__(self, cls_template=PdfDocTemplate, mem_reduction=False):
        """
        preset class internal variables

        :param mem_reduction: If True, PNG images are converted to JPEG format before passing them to the
                              reportlab.platypus.flowables.Image class.
                              Also, the lazy=2 argument is used to open the image when required then shut it.
                              If False, no image conversion is done and the lazy=1 argument is used when calling
                              reportlab.platypus.flowables.Image to not open the image until required.
        :type mem_reduction:  boolean, optional, default: False
        """
        self.style = template.Style()
        Story.__init__(self, self.style, mem_reduction)
        self._doc = None
        self.__cls_template = cls_template

    def build(self, filepath):
        """
        Build the final pdf document including following steps:

          - Creating a Template.
          - Prebuilding of the internal Story (assign of numerations)
          - Rendering of the document.

        :param filepath: whole path of the file which must be created.
        :type filepath:  str
        :return:         number of build passes

        :author:         Robert Hecker
        :date:           22.09.2013
        """
        res = None
        # Create a Instance of our Template Document class,
        # which is needed to create our Document
        self._doc = self.__cls_template(self.style, filepath)

        # First go through the whole story,
        # and Format the story in the wanted way.
        story = self._pre_build()

        # Do the final Creation of the pdf Docu rendering....
        try:
            res = self._doc.multiBuild(story)
        except Exception as err:
            print(err)
        return res

    @deprecated('build')
    def Build(self, filepath):  # pylint: disable=C0103
        """
        :deprecated: please use build() method instead
        """
        # warnings.warn('Method "Build" is deprecated use "build" instead', stacklevel=2)
        return self.build(filepath)

"""
CHANGE LOG:
-----------
$Log: pdf.py  $
Revision 1.6 2017/08/25 15:47:07CEST Hospes, Gerd-Joachim (uidv8815) 
static check fixes
Revision 1.5 2017/08/01 11:36:12CEST Hospes, Gerd-Joachim (uidv8815)
new error hints for wrong image path and type, module  test exrended
Revision 1.4 2017/01/23 15:47:53CET Hospes, Gerd-Joachim (uidv8815)
go back to former version but add cellstyle keyw. to Table, add test
Revision 1.3 2016/12/01 11:22:55CET Hospes, Gerd-Joachim (uidv8815)
fix docu errors
Revision 1.2 2016/02/09 09:51:32CET Mertens, Sven (uidv7805)
is it really true?
Revision 1.1 2015/04/23 19:05:14CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/rep/pdf/base/project.pj
Revision 1.22 2015/03/06 15:39:38CET Ellero, Stefano (uidw8660)
Implemented the optional parameter "mem_reduction" in the base class for all report templates
(stk.rep.pdf.base.pdf.Story) to reduce the memory usage during a pdf report generation.
--- Added comments ---  uidw8660 [Mar 6, 2015 3:39:40 PM CET]
Change Package : 307809:1 http://mks-psad:7002/im/viewissue?selection=307809
Revision 1.21 2015/01/27 21:20:10CET Ellero, Stefano (uidw8660)
Removed all rep based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 27, 2015 9:20:10 PM CET]
Change Package : 296836:1 http://mks-psad:7002/im/viewissue?selection=296836
Revision 1.20 2014/12/16 16:48:13CET Hospes, Gerd-Joachim (uidv8815)
add break_to feature to add_page_break()
--- Added comments ---  uidv8815 [Dec 16, 2014 4:48:14 PM CET]
Change Package : 292136:1 http://mks-psad:7002/im/viewissue?selection=292136
Revision 1.19 2014/11/25 17:15:49CET Ellero, Stefano (uidw8660)
To format a title page when using the basic report template, an additinal argument to set
the style of the paragraph was added to the add_paragraph() function in stk.rep.pdf.base.pdf.py.
Default style is set to 'Normal' to be backward compatible. The module test was updated to create a document title.
--- Added comments ---  uidw8660 [Nov 25, 2014 5:15:50 PM CET]
Change Package : 280072:1 http://mks-psad:7002/im/viewissue?selection=280072
Revision 1.18 2014/09/25 13:29:22CEST Hospes, Gerd-Joachim (uidv8815)
adapt stk.img files to style guide, new names used in all modules and tests except stk.img tests
--- Added comments ---  uidv8815 [Sep 25, 2014 1:29:23 PM CEST]
Change Package : 264203:1 http://mks-psad:7002/im/viewissue?selection=264203
Revision 1.17 2014/07/29 12:41:28CEST Hospes, Gerd-Joachim (uidv8815)
pep8 fixes of too long lines for http links, epydoc and pylint adjustments
--- Added comments ---  uidv8815 [Jul 29, 2014 12:41:28 PM CEST]
Change Package : 246030:1 http://mks-psad:7002/im/viewissue?selection=246030
Revision 1.16 2014/07/28 19:20:20CEST Hospes, Gerd-Joachim (uidv8815)
extend epydoc
--- Added comments ---  uidv8815 [Jul 28, 2014 7:20:21 PM CEST]
Change Package : 246030:1 http://mks-psad:7002/im/viewissue?selection=246030
Revision 1.15 2014/06/26 11:15:57CEST Hospes, Gerd-Joachim (uidv8815)
fine tuning of epydoc for AlgoTestReport and base
--- Added comments ---  uidv8815 [Jun 26, 2014 11:15:57 AM CEST]
Change Package : 243858:2 http://mks-psad:7002/im/viewissue?selection=243858
Revision 1.14 2014/06/25 10:31:32CEST Hospes, Gerd-Joachim (uidv8815)
fix pylint warnings
--- Added comments ---  uidv8815 [Jun 25, 2014 10:31:32 AM CEST]
Change Package : 243858:1 http://mks-psad:7002/im/viewissue?selection=243858
Revision 1.13 2014/06/24 17:01:29CEST Hospes, Gerd-Joachim (uidv8815)
move table caption below table, extend some epydoc
--- Added comments ---  uidv8815 [Jun 24, 2014 5:01:29 PM CEST]
Change Package : 243858:1 http://mks-psad:7002/im/viewissue?selection=243858
Revision 1.12 2014/06/16 14:57:53CEST Hospes, Gerd-Joachim (uidv8815)
add table_of_* to base report
--- Added comments ---  uidv8815 [Jun 16, 2014 2:57:54 PM CEST]
Change Package : 241724:1 http://mks-psad:7002/im/viewissue?selection=241724
Revision 1.11 2014/05/09 16:24:43CEST Hecker, Robert (heckerr)
Added possibility to define diferent template classes.
--- Added comments ---  heckerr [May 9, 2014 4:24:44 PM CEST]
Change Package : 236027:1 http://mks-psad:7002/im/viewissue?selection=236027
Revision 1.10 2014/05/06 10:53:16CEST Hospes, Gerd-Joachim (uidv8815)
add create_dir
--- Added comments ---  uidv8815 [May 6, 2014 10:53:17 AM CEST]
Change Package : 233144:1 http://mks-psad:7002/im/viewissue?selection=233144
Revision 1.9 2014/04/11 14:31:16CEST Mertens, Sven (uidv7805)
fix: Build returns from build, but build doesn't return anything from multibuild, but multibuild returns passes
--- Added comments ---  uidv7805 [Apr 11, 2014 2:31:16 PM CEST]
Change Package : 227498:2 http://mks-psad:7002/im/viewissue?selection=227498
Revision 1.8 2014/04/11 13:09:53CEST Mertens, Sven (uidv7805)
fix for table and image enumeration problem
--- Added comments ---  uidv7805 [Apr 11, 2014 1:09:53 PM CEST]
Change Package : 227498:1 http://mks-psad:7002/im/viewissue?selection=227498
Revision 1.7 2014/03/28 11:32:45CET Hecker, Robert (heckerr)
commented out warnings.
--- Added comments ---  heckerr [Mar 28, 2014 11:32:45 AM CET]
Change Package : 228098:1 http://mks-psad:7002/im/viewissue?selection=228098
Revision 1.6 2014/03/28 10:25:53CET Hecker, Robert (heckerr)
Adapted to new coding guiedlines incl. backwardcompatibility.
--- Added comments ---  heckerr [Mar 28, 2014 10:25:54 AM CET]
Change Package : 228098:1 http://mks-psad:7002/im/viewissue?selection=228098
Revision 1.5 2014/03/26 17:21:00CET Hospes, Gerd-Joachim (uidv8815)
add new option hAlign for Story.AddImage, tested in test_plot and test_report
--- Added comments ---  uidv8815 [Mar 26, 2014 5:21:00 PM CET]
Change Package : 224334:1 http://mks-psad:7002/im/viewissue?selection=224334
Revision 1.4 2013/10/25 09:02:36CEST Hecker, Robert (heckerr)
Removed Pep8 Issues.
--- Added comments ---  heckerr [Oct 25, 2013 9:02:36 AM CEST]
Change Package : 202843:1 http://mks-psad:7002/im/viewissue?selection=202843
Revision 1.3 2013/10/21 15:03:34CEST Hecker, Robert (heckerr)
Added the Append command;
updated epydoc.
--- Added comments ---  heckerr [Oct 21, 2013 3:03:34 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.2 2013/10/18 17:20:28CEST Hecker, Robert (heckerr)
Get AddImage and AddTable working.
--- Added comments ---  heckerr [Oct 18, 2013 5:20:28 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.1 2013/10/18 09:22:13CEST Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/rep/pdf/base/project.pj
"""
