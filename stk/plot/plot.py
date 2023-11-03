"""
stk/plot/plot.py
----------------

Main Plot Module which contains the Plot-class.

**This module/class helps you to:**
  - Do the first steps with a plotting API.
  - get some basic plots like described in the example below.
  - extend in an easy way your plot with original api-commands from matplotlib.


For not directly supported functions, you can use the original commands from
matplotlib, and mix them with this API.


**To use the plot package from your code do following:**

  .. python::

    # Import stk.plot
    from stk import plot

    # Create a instance of the Plot class.
    plt = plot.Plot()

    plt.plot([1, 2, 3, 4], [1, 4, 9, 16], 'ro')
    plt.axis([0, 5, 0, 20])
    plt.savefig('plot_xydata.png')

    ...


:org:           Continental AG
:author:        Robert Hecker
:date:          08.07.2014

:version:       $Revision: 1.2 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2015/12/07 13:30:57CET $
"""

# pylint: disable=E1103,C0103,R0912,R0913

# Import Python Modules --------------------------------------------------------
from PIL import Image as Img
from reportlab.graphics.shapes import Image, Drawing

from reportlab.platypus import Flowable
from pdfrw import PdfReader
from pdfrw.buildxobj import pagexobj
from pdfrw.toreportlab import makerl
from matplotlib import pyplot
from matplotlib import gridspec
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import io

# Import STK Modules -----------------------------------------------------------

# Defines ----------------------------------------------------------------------

# Functions --------------------------------------------------------------------


# Classes ----------------------------------------------------------------------
class PdfPlot(Flowable):
    """
    PdfPlot wraps the first page from a PDF file as a Flowable
    which can be included into a ReportLab Platypus document.
    Based on the vectorpdf extension in rst2pdf
    (http://code.google.com/p/rst2pdf/)
    """
    def __init__(self, filename_or_object, width=None,
                 height=None, kind='direct'):
        # from reportlab.lib.units import inch
        # If using StringIO buffer, set pointer to begining
        Flowable.__init__(self)

        if hasattr(filename_or_object, 'read'):
            filename_or_object.seek(0)
        page = PdfReader(filename_or_object, decompress=False).pages[0]
        self.xobj = pagexobj(page)
        self.image_width = width
        self.image_height = height
        x1, y1, x2, y2 = self.xobj.BBox

        self._w, self._h = x2 - x1, y2 - y1
        if not self.image_width:
            self.image_width = self._w
        if not self.image_height:
            self.image_height = self._h

        self.__ratio = float(self.image_width) / self.image_height
        if kind in ['direct', 'absolute'] or width is None or height is None:
            self.draw_width = width or self.image_width
            self.draw_height = height or self.image_height
        elif kind in ['bound', 'proportional']:
            factor = min(float(width) / self._w, float(height) / self._h)
            self.draw_width = self._w * factor
            self.draw_height = self._h * factor

    def wrap(self, aW, aH):
        return self.draw_width, self.draw_height

    def drawOn(self, canv, x, y, _sW=0):
        if _sW > 0 and hasattr(self, 'hAlign'):
            hor_align = self.hAlign
            if hor_align in ('CENTER', 'CENTRE', TA_CENTER):
                x += 0.5 * _sW
            elif hor_align in ('RIGHT', TA_RIGHT):
                x += _sW
            elif hor_align not in ('LEFT', TA_LEFT):
                raise ValueError("Bad hAlign value " + str(hor_align))

        xobj = self.xobj
        xobj_name = makerl(canv._doc, xobj)

        xscale = self.draw_width / self._w
        yscale = self.draw_height / self._h

        x -= xobj.BBox[0] * xscale
        y -= xobj.BBox[1] * yscale

        canv.saveState()
        canv.translate(x, y)
        canv.scale(xscale, yscale)
        canv.doForm(xobj_name)
        canv.restoreState()


GridSpec = gridspec.GridSpec


class Plot(object):
    """
    Plot Class with multiple Plot functions

    Provides Methos to create different kind of Plots like:
      - BarPlots
      - PiePlots
      - HistogramPlots
      - Graphs
      - ...

    :org:           Continental AG
    :author:        Robert Hecker
    :date:          08.07.2014
    """
    def __init__(self, num=None, figsize=(15, 5), dpi=None, facecolor=None,
                 edgecolor=None, frameon=True, FigureClass=pyplot.Figure,
                 **kwargs):

        self._fig = pyplot.figure(num, figsize, dpi, facecolor, edgecolor,
                                  frameon, FigureClass, **kwargs)
        self.__xdata = None
        self.__ydata = None

    def plot(self, *args, **kwargs):
        """
        Plot lines and/or markers to the Axes.
        args is a variable length argument, allowing for multiple x, y pairs
        with an optional format string. For example,
        each of the following usage is possible:

        .. python::

            plot(x, y)        # plot x and y using default line style and color
            plot(x, y, 'bo')  # plot x and y using blue circle markers
            plot(y)           # plot y using x as index array 0..N-1
            plot(y, 'r+')     # ditto, but with red plusses

        If x and/or y is 2-dimensional, then the corresponding columns will be
        plotted. An arbitrary number of x, y,
        fmt groups can be specified, as in:

        .. python::

            a.plot(x1, y1, 'g^', x2, y2, 'g-')

        By default, each line is assigned a different color specified by a
        `color cycle` To change this behavior, you can edit the
        axes.color_cycle rcParam.
        Alternatively, you can use set_default_color_cycle().

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.plot
        """
        self.__xdata = args[0]
        try:
            self.__ydata = args[1]
        except IndexError:
            pass

        return pyplot.plot(*args, **kwargs)

    @staticmethod
    def bar(left, height, width=0.8, bottom=None, hold=None, **kwargs):
        """
        Plot a stacked or grouped bar chart.

        :param left:   the x coordinates of the left sides of the bars
        :type left:    sequence of scalars
        :param height: the heights of the bars
        :type height:  sequence of scalars
        :param width:  the width(s) of the bars
        :type width:   scalar or array-like, optional, default:0.8
        :param bottom: the y-coordinate(s) of the bars
        :type bottom:  scalar or array-like, optional, default:None
        :param hold:   TBD
        :type hold:    TBD
        :return:       instance of class.
        :rtype:        `matplotlib.patches.Rectangle`

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.bar
        """
        return pyplot.bar(left, height, width, bottom, hold, **kwargs)

    @staticmethod
    def hist(x, bins=10, range=None, normed=False, weights=None,
             cumulative=False, bottom=None, histtype='bar', align='mid',
             orientation='vertical', rwidth=None, log=False, color=None,
             label=None, stacked=False, hold=None, **kwargs):
        """
        Plot a histogram.
        Compute and draw the histogram of x. The return value is a tuple
        (n, bins, patches) or ([n0, n1, ...], bins, [patches0, patches1,...])
        if the input contains multiple data.
        Multiple data can be provided via x as a list of datasets of potentially
        different length ([x0, x1, ...]), or as a 2-D ndarray in which each
        column is a dataset. Note that the ndarray form is transposed
        relative to the list form.
        Masked arrays are not supported at present.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.hist

        :param x: Input values.
        :type x:  array_like, shape (n, )
        :param bins: If an integer is given, bins + 1 bin edges are returned,
                     consistently with numpy.histogram() for
                     numpy version >= 1.3.
                     Unequally spaced bins are supported if bins is a sequence.
        :type bins:  integer or array_like, optional, default: 10
        :param range: The lower and upper range of the bins. Lower and upper
                      outliers are ignored. If not provided, range is
                      (x.min(), x.max()). Range has no effect if bins is a
                      sequence. If bins is a sequence or range is specified,
                      autoscaling is based on the specified bin range instead
                      of the range of x.
        :type range:  tuple, optional, default: None
        :param normed: If True, the first element of the return tuple will be
                       the counts normalized to form a probability density,
                       i.e., n/(len(x)`dbin), ie the integral of the histogram
                       will sum to 1. If stacked is also True, the sum of the
                       histograms is normalized to 1.
        :type normed:  boolean, optional, default: False
        :param weights: An array of weights, of the same shape as x. Each value
                        in x only contributes its associated weight towards the
                        bin count (instead of 1). If normed is True, the weights
                        are normalized, so that the integral of the density
                        over the range remains 1.
        :type weights:  array_like, shape (n, ), optional, default: None
        :param cumulative: If True, then a histogram is computed where each bin
                           gives the counts in that bin plus all bins for
                           smaller values. The last bin gives the total number
                           of datapoints. If normed is also True then the
                           histogram is normalized such that the last bin equals
                           1. If cumulative evaluates to less than 0 (e.g., -1),
                           the direction of accumulation is reversed.
                           In this case, if normed is also True, then the
                           histogram is normalized such that the first
                           bin equals 1.
        :type cumulative: boolean, optional, default
        :param histtype: The type of histogram to draw.
        :type histtype:  ['bar' | 'barstacked' | 'step' | 'stepfilled'],optional
                        1. 'bar' is a traditional bar-type histogram.
                            If multiple data are given the bars are aranged
                            side by side.
                        2. 'barstacked' is a bar-type histogram where multiple
                            data are stacked on top of each other.
                        3. 'step' generates a lineplot that is by default
                            unfilled.
                        4. 'stepfilled' generates a lineplot that is by default
                            filled.
        :param align: Controls how the histogram is plotted.
        :type align: ['left' | 'mid' | 'right'], optional, default: 'mid'
                     -'left': bars are centered on the left bin edges.
                     -'mid': bars are centered between the bin edges.
                     -'right': bars are centered on the right bin edges.
        :param orientation: If 'horizontal', barh will be used for bar-type
                            histograms and the bottom kwarg will be the
                            left edges.
        :type orientation: ['horizontal' | 'vertical'], optional
        :param rwidth: The relative width of the bars as a fraction of the bin
                       width. If None, automatically compute the width.
                       Ignored if histtype = 'step' or 'stepfilled'.
        :type rwidth: scalar, optional, default: None
        :param log: If True, the histogram axis will be set to a log scale.
                    If log is True and x is a 1D array, empty bins will be
                    filtered out and only the non-empty (n, bins, patches) will
                    be returned.
        :type log: boolean, optional, default
        :param color: Color spec or sequence of color specs, one per dataset.
                      Default (None) uses the standard line color sequence.
        :type color: color or array_like of colors, optional, default: None
        :param label: String, or sequence of strings to match multiple datasets.
                      Bar charts yield multiple patches per dataset, but only
                      the first gets the label, so that the legend command will
                      work as expected.
        :type label: string, optional, default: ""
        :param stacked: If True, multiple data are stacked on top of each other
                        If False multiple data are aranged side by side if
                        histtype is 'bar' or on top of each other if histtype
                        is 'step'
        :type stacked: boolean, optional, default
        """
        return pyplot.hist(x, bins=bins, range=range, normed=normed,
                           weights=weights, cumulative=cumulative,
                           bottom=bottom, histtype=histtype, align=align,
                           orientation=orientation, rwidth=rwidth, log=log,
                           color=color, label=label, stacked=stacked,
                           hold=hold, **kwargs)

    @staticmethod
    def pie(values, explode=None, labels=None, colors=None, autopct=None,
            pctdistance=0.6, shadow=False, labeldistance=1.1, startangle=None,
            radius=None, hold=None):
        """
        Plot a pie chart.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.pie

        :param values: TBD
        :type values: TBD
        :param explode: If not None, is a len(x) array which specifies the
                        fraction of the radius with which to offset each wedge
        :type explode:  [None | list[float]]
        :param colors:  A sequence of matplotlib color args through which the
                        pie chart will cycle.
        :type colors:   [None | list[color]]
        :param labels:  A sequence of strings providing the labels for each
                        wedge
        :type labels:   [None | list[string]]
        :param autopct: If not None, is a string or function used to label the
                        wedges with their numeric value. The label will be
                        placed inside the wedge. If it is a format string, the
                        label will be fmt%pct. If it is a function,
                        it will be called.
        :type autopct:  [None | format string | format function]
        :param pctdistance: The ratio between the center of each pie slice and
                            the start of the text generated by autopct.
                            Ignored if autopct is None; default is 0.6.
        :type pctdistance:  scalar
        :param labeldistance: The radial distance at which the pie labels are
                              drawn.
        :type labeldistance:  scalar
        :param shadow:       Draw a shadow beneath the pie.
        :type shadow:         [False | True]
        :param startangle:    If not None, rotates the start of the pie chart by
                              angle degrees counterclockwise from the x-axis.
        :type startangle:     [None | Offset angle]
        :param radius:        The radius of the pie, if radius is None it will
                              be set to 1.
        :type radius:         [None | scalar]
        """
        return pyplot.pie(values, explode, labels, colors, autopct, pctdistance,
                          shadow, labeldistance, startangle, radius, hold)

    @staticmethod
    def boxplot(self, x, notch=False, sym='b+', vert=True, whis=1.5,
                positions=None, widths=None, patch_artist=False,
                bootstrap=None, usermedians=None, conf_intervals=None,
                hold=None):
        """
        Make a box and whisker plot.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.boxplot
        """

        return pyplot.boxplot(x, notch, sym, vert, whis, positions,
                              widths, patch_artist, bootstrap,
                              usermedians, conf_intervals, hold)

    @staticmethod
    def clear():
        """
        clear the content of the current plot
        """
        pyplot.cla()  # Clear axis

    @staticmethod
    def xlabel(label, *args, **kwargs):
        """
        Set the *x*-axis label of the current axis.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.xlabel

        :param label: x-axis label
        :type label:  string
        """
        return pyplot.xlabel(label, *args, **kwargs)

    @staticmethod
    def ylabel(label, *args, **kwargs):
        """
        Set the *y*-axis label of the current axis.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.ylabel

        :param label: y-axis label
        :type label:  string
        """
        return pyplot.ylabel(label, *args, **kwargs)

    @staticmethod
    def text(xpos, ypos, text, fontdict=None, withdash=False, **kwargs):
        """
        Add additional text to the plot.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.text

        :param xpos:     xpos-coordinate of starting point for text.
        :type xpos:      float
        :param ypos:     ypos-coordinate of starting point for text.
        :type ypos:      float
        :param text:     Text, you want to print in figure.
        :type text:      string
        :param fontdict: TBD
        :type fontdict:  dictionary
        :param withdash: Creates a TextWithDash instance instead of a
                         Text instance.
        :type withdash:  boolean
        """
        return pyplot.text(xpos, ypos, text, fontdict, withdash, **kwargs)

    @staticmethod
    def axis(*v, **kwargs):
        """
        Convenience method to get or set axis properties.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.axis

        Set the range of the x-axis and y-axis.
        [xmin, xmax, ymin, ymax]
        """
        return pyplot.axis(*v, **kwargs)

    @staticmethod
    def twinx(ax=None):
        """
        Create Twin X-Scale.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.twinx
        """
        return pyplot.twinx(ax)

    @staticmethod
    def gca(**kwargs):
        """
        Get Current Axis.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.gca
        """
        return pyplot.gca(**kwargs)

    @staticmethod
    def sca(ax):
        """
        Set Current Axis.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.sca
        """
        return pyplot.sca(ax)

    @staticmethod
    def subplot(*args, **kwargs):
        """
        Return a subplot axes positioned by the given grid definition.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.subplot
        """
        return pyplot.subplot(*args, **kwargs)

    def subplots(self, nrows=1, ncols=1, sharex=False, sharey=False,
                 squeeze=True, subplot_kw=None, **fig_kw):
        """
        Create a figure with a set of subplots already made.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.subplots
        """
        self._fig, self._ax = pyplot.subplots(nrows, ncols, sharex, sharey,
                                              squeeze, subplot_kw, **fig_kw)

        return self._fig, self._ax

    @staticmethod
    def tight_layout(pad=1.08, h_pad=None, w_pad=None, rect=None):
        """
        Automatically adjust subplot parameters to give specified padding.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.tight_layout
        """
        return pyplot.tight_layout(pad, h_pad, w_pad, rect)

    @staticmethod
    def legend(*args, **kwargs):
        """
        Place a legend on the current axes.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.legend
        """
        return pyplot.legend(*args, **kwargs)

    @staticmethod
    def title(s, *args, **kwargs):
        """
        Set a title of the current axes.

        Set one of the three available axes titles.
        The available titles are positioned above the axes in the center,
        flush with the left edge, and flush with the right edge.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.title

        :param s: titel
        :type s: string
        """
        return pyplot.title(s, *args, **kwargs)

    @staticmethod
    def grid(b=None, which='major', axis='both', **kwargs):
        """
        Turn the axes grids on or off.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.grid
        """
        return pyplot.grid(b, which, axis, **kwargs)

    @staticmethod
    def xticks(*args, **kwargs):
        """
        Get or set the x-limits of the current tick locations and labels.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.xticks

        :param fontsize: Fontsize in pixel
        :type fontsize: integer
        """
        return pyplot.xticks(*args, **kwargs)

    @staticmethod
    def yticks(*args, **kwargs):
        """
        Get or set the y-limits of the current tick locations and labels.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.yticks

        :keyword fontsize: Fontsize in pixel
        :type fontsize: integer

        :raise Exception: Hugo
        """
        return pyplot.yticks(*args, **kwargs)

    @staticmethod
    def xlim(*args, **kwargs):
        """
        Get or set the x limits of the current axes.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.xlim
        """
        return pyplot.xlim(*args, **kwargs)

    @staticmethod
    def ylim(*args, **kwargs):
        """
        Get or set the y limits of the current axes.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.ylim
        """
        return pyplot.ylim(*args, **kwargs)

    @staticmethod
    def figtext(*args, **kwargs):
        """
        Add text to figure.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.figtext
        """
        return pyplot.figtext(*args, **kwargs)

    @staticmethod
    def annotate(*args, **kwargs):
        """
        Add text to figure.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.figtext
        """
        return pyplot.annotate(*args, **kwargs)

    @staticmethod
    def savefig(*args, **kwargs):
        """
        Save the current figure.

        Please see also the original matplotlib docu:
        http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.savefig
        """
        return pyplot.savefig(*args, **kwargs)

    @staticmethod
    def subplots_adjust(*args, **kwargs):
        """

        :return:
        """
        return pyplot.subplots_adjust(*args, **kwargs)

    def get_pdf(self, width=None, height=None):
        """
        Get the current figure as pdf.

        :param width:
        :type width
        """
        imgdata = io.BytesIO()
        self._fig.savefig(imgdata, format='PDF')
        return PdfPlot(imgdata, width=width, height=height)

#     def get_img(self):
#         """
#         """
#         image_file = io.BytesIO()
#         self._fig.savefig(image_file, format='PNG')
#         im = Img.open(image_file)
#         d = Drawing(width, height)
#         img = Image(im)
#         d.add(img)
#
#         return d


"""
 $Log: plot.py  $
 Revision 1.2 2015/12/07 13:30:57CET Mertens, Sven (uidv7805) 
 removing last pep8 errors
 Revision 1.1 2015/04/23 19:04:57CEST Hospes, Gerd-Joachim (uidv8815)
 Initial revision
 Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/plot/project.pj
 Revision 1.4 2015/02/14 17:56:11CET Hospes, Gerd-Joachim (uidv8815)
 add subplots_adjust, merged from hpc
 --- Added comments ---  uidv8815 [Feb 14, 2015 5:56:11 PM CET]
 Change Package : 306571:1 http://mks-psad:7002/im/viewissue?selection=306571
 Revision 1.3 2015/01/20 16:49:43CET Mertens, Sven (uidv7805)
 changing None comparison
 --- Added comments ---  uidv7805 [Jan 20, 2015 4:49:44 PM CET]
 Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
 Revision 1.2 2014/07/24 15:17:51CEST Hecker, Robert (heckerr)
 added two methods.
 --- Added comments ---  heckerr [Jul 24, 2014 3:17:51 PM CEST]
 Change Package : 251317:1 http://mks-psad:7002/im/viewissue?selection=251317
 Revision 1.1 2014/07/14 12:00:23CEST Hecker, Robert (heckerr)
 Initial revision
 Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
 05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/plot/project.pj

"""
