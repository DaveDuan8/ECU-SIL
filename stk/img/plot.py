"""
stk/img/__init__.py
-------------------

Generate Plots and reload images from database

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.7.1.2 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/08/21 20:20:51CEST $
"""
# pylint: disable=R0902,R0912,R0913,R0914,E1103

# - import Python modules ---------------------------------------------------------------------------------------------
from PIL import Image as Img
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.backends.backend_ps import papersize
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
from matplotlib import mlab
from numpy.ma import MaskedArray
from os import path as opath, unlink, makedirs
from reportlab.graphics.shapes import Image, Drawing
from math import fabs, ceil, exp, sqrt, pi
import matplotlib
import matplotlib.pyplot as pltt
import numpy
from tempfile import gettempdir, NamedTemporaryFile
from uuid import uuid4
# import warnings
import imghdr

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.util import Logger
from stk.util.helper import deprecated

# - defines -----------------------------------------------------------------------------------------------------------
DRAWING_W = 450
DRAWING_H = 100

PLOT_W = DRAWING_W * 0.75  # DRAWING_W - DRAWING_W / 5
PLOT_H = DRAWING_H - DRAWING_H / 5
LEGEND_X = DRAWING_W * 0.85  # DRAWING_W - DRAWING_W / 10
LEGEND_Y = DRAWING_H * 0.8
TEXT_SIZE = 7
DEFAULT_OUTPUT_FILEEXT = "png"

PLOT_BAR = "Bar"
PLOT_SCATTER = "Scatter"

DEF_COLORS = ["b", "r", "g", "orange", "magenta", "cyan", "k", "y", "b", "r", "g",
              "orange", "magenta", "cyan", "k", "y"]
DEF_LINE_STYLES = ["-", "--", "-.", ":", "", "+"]
DEF_LINE_MARKERS = ["None", "+", "*", ",", ".", "<", ">", "+", "*", ",", ".", "<", ">", "+", "*", ",", ".", "<", ">"]


# - classes -----------------------------------------------------------------------------------------------------------
class PlotException(Exception):
    """Plot exception Class"""
    def __init__(self, description):
        """ Constructor """
        Exception.__init__(self)
        self._description = str(description)

    def __str__(self):
        """ Return the plot exception string """
        return str(self._description)


class ValidationFigure(object):
    """Figure class used by ValidationPlot class"""
    def __init__(self, subplots=None, fig_width=10, fig_height=3, show_grid=True):
        """ Create initial Figure ValidationPlot with subplot feature

        multiple subplots are support through list of int or tuple

        :param subplots: specified subplots per figure
        :type subplots:  list of int or tuple
        :param fig_width: width of the figure
        :type fig_width: int
        :param fig_height: height of the figure
        :type fig_height: int
        :param show_grid: flag to show or hide grid
        :type show_grid: boolean
        """
        self.__plot = pltt
        self.__fig = pltt.figure(figsize=(fig_width, fig_height))
        self.__width = fig_width
        self.__height = fig_height
        self.__show_grid = show_grid
        self.__subplots = subplots
        self.__axes = None
        self.__initialize()

    def __initialize(self):
        """Initialize the attribute when the constructor is called

        creates the subplot if values are passed in constructor """
        self.__plot.clf()
        if self.__subplots is None:
            self.__axes = self.__fig.add_subplot(111)
            self.__axes.grid(self.__show_grid)
        else:
            self.__axes = []
            for i in range(len(self.__subplots)):
                if type(self.__subplots[i]) is tuple:
                    self.__axes.append(self.__fig.add_subplot(self.__subplots[i][0],
                                                              self.__subplots[i][1],
                                                              self.__subplots[i][2]))
                else:
                    self.__axes.append(self.__fig.add_subplot(self.__subplots[i]))
                self.__axes[i].grid(self.__show_grid[i])

    def add_subplot(self, subplots, show_grid=True):
        """
        Add subplots in the existing figure

        :param subplots: specify subplots to be added
        :type subplots: list of integer or tuple
        :param show_grid: flag to show or hide grid
        :type show_grid: boolean
        """
        if self.__subplots is not None:
            self.__subplots += subplots

        for i in range(len(subplots)):
            if type(self.__subplots[i]) is tuple:
                self.__axes.append(self.__fig.add_subplot(self.__subplots[i][0],
                                                          self.__subplots[i][1],
                                                          self.__subplots[i][2]))
            else:
                self.__axes.append(self.__fig.add_subplot(subplots[i]))
            self.__axes[i].grid(show_grid[i])

    def get_fig(self):
        """
        Get Property function to get Figure
        """
        return self.__fig

    def get_plot(self):
        """
        Get Property function to get plot
        """
        return self.__plot

    def get_width(self):
        """
        Get Property function to get Figure width
        """
        return self.__width

    def get_height(self):
        """
        Get Property function to get Figure width
        """
        return self.__height

    def get_axes(self):
        """
        Get Property function to get Axes
        """
        return self.__axes

    def get_show_grid(self):
        """
        Get Property function to get grid flag
        """
        return self.__show_grid

    def get_subplots(self):
        """
        Get property function for subplots attribute
        """
        return self.__subplots

# deprecated methods of class ValidationFigure to keep compatibility,
# should be removed in next major release (stk 02.02.01)

    @deprecated('__initialize')
    def __Initialize(self):  # pylint: disable=C0103
        """method name deprecated, please use __initialize instead

        :deprecated: please use __initialize() instead
        """
        self.__initialize()

    @deprecated('add_subplot')
    def AddSubplot(self, subplots, show_grid=True):  # pylint: disable=C0103
        """method name deprecated, please use add_subplot() instead

        :deprecated: name changed to add_subplot()
        """
        self.add_subplot(subplots, show_grid)

    @deprecated('get_fig')
    def GetFig(self):  # pylint: disable=C0103
        """method name deprecated, please use get_fig() instead

        :deprecated: name changed to get_fig()
        """
        return self.get_fig()

    @deprecated('get_plot')
    def GetPlot(self):  # pylint: disable=C0103
        """method name deprecated, please use get_plot() instead

        :deprecated: name changed to get_plot()
        """
        return self.get_plot()

    @deprecated('get_width')
    def GetWidth(self):  # pylint: disable=C0103
        """method name deprecated, please use get_width() instead

        :deprecated: name changed to get_width()
        """
        return self.get_width()

    @deprecated('get_height')
    def GetHeight(self):  # pylint: disable=C0103
        """method name deprecated, please use get_height() instead

        :deprecated: name changed to get_hight()
        """
        return self.get_height()

    @deprecated('get_axes')
    def GetAxes(self):  # pylint: disable=C0103
        """method name deprecated, please use get_axes() instead

        :deprecated: name changed to get_axes()
        """
        return self.get_axes()

    @deprecated('get_show_grid')
    def GetShowGrid(self):  # pylint: disable=C0103
        """method name deprecated, please use get_show_grid() instead

        :deprecated: name changed to get_show_grid()
        """
        return self.get_show_grid()

    @deprecated('get_subplots')
    def GetSubplots(self):  # pylint: disable=C0103
        """method name deprecated, please use get_subplots() instead

        :deprecated: name changed to get_subplots()
        """
        return self.get_subplots()


class BasePlot(object):
    """ Base Class for plotting functions using matplot lib

    find detailed info about used methods in matplot
    """
    def __init__(self, figure=None, position=None, figsize=(8, 6), fontsize=8,
                 show_grid=True):
        """ Constructor """
        self.__figure = figure

        if not self.__figure:
            self.__figure = Figure(figsize=figsize, facecolor='#ddddee')

        self.__show_grid = show_grid

        self._canvas = FigureCanvas(self.__figure)

        if position and self.__figure:
            self.__axes = self.__figure.add_axes(position)
        else:
            self.__axes = self.__figure.gca()

        self.__fontsize = fontsize

        # Set\Re-set grid
        self.__axes.grid(show_grid)

        # set axis labels
        label_list = self.__axes.get_xticklabels() + self.__axes.get_yticklabels()
        for label in label_list:
            label.set_size(self.__fontsize)

        self.__lines = []
        self.__vlines = []
        self.__texts = []
        self.__legends = []

        self.__styles = "line dashed dotted dashdot".split()
        self.__color_map = "blue green red black cyan magenta orange purple yellow pink".split()
        self.__lsalias = {"line": [1, 0],
                          "dashdot": [4, 2, 1, 2],
                          "dashed": [4, 2, 4, 2],
                          "dotted": [1, 2],
                          "dashdotdot": [4, 2, 1, 2, 1, 2],
                          "dashdashdot": [4, 2, 4, 2, 1, 2]}

        self.__color = 0
        self.__linestyle = 0
        self.__line_attributes = {}
        self.__text_attributes = {}
        self.__legend_loc = 0

        self.__background = None

        tstyle = []
        for line_style in self.__styles:
            if line_style in self.__lsalias:
                tstyle.append(self.__lsalias.get(line_style))
            else:
                tstyle.append("-")

        self.__linestyles = tstyle

        self.__set_draw_mode = False

    def add_patch(self, patch):
        """
        Add a patch (some given figure) to the plot.

        params from `matplotlib.add_patch`:

        Add a :class:`~matplotlib.patches.Patch` *p* to the list of
        axes patches; the clipbox will be set to the Axes clipping
        box.  If the transform is not set, it will be set to
        :attr:`transData`.

        :param patch: figure
        """
        self.__axes.add_patch(patch)

    def set_xticklabels(self, labels=""):
        """ Set the xtick labels
        """
        self.__axes.set_xticklabels(labels, visible=False)

    def set_label2(self, text):
        """ Set the x axes label """
        self.__axes.set_xlabel(text)

    def set_patch(self, patch):
        """
        Sets an existing patch
        """
        if not self.__set_draw_mode:
            self._canvas.draw()
            self.__set_draw_mode = True

        # self.__axes.set_xy(vertices)
        self.__axes.draw_artist(patch)

    def set_title(self, *args, **kwargs):
        """
        Sets the title of the plot. Use the previous title if omitted.

        additional parameters like fontdict, loc or text properties in matplotlib.Axes.set_title

        :param label: title text
        :type  label: str
        """
        self.__axes.set_title(*args, **kwargs)

    def set_grid(self, show_grid):
        """ Enable or Disable the grid

        :param show_grid: flag to show grid (True, default in BasePlot) or suppress (False)
        :type  show_grid: boolean
        """
        self.__axes.grid(show_grid)

    def get_image(self):
        """ returns the plot as a PIL image
        """
        self.__figure.canvas.draw()
        image_size = self.__figure.canvas.get_width_height()
        image_rgb = self.__figure.canvas.tostring_rgb()
        return Img.frombytes("RGB", image_size, image_rgb)

    @deprecated('get_image')
    def getImage(self):  # pylint: disable=C0103
        """method name deprecated, please use get_image() instead

        :deprecated: use get_image() instead
        """
        return self.get_image()

    @property
    def canvas(self):
        """returns canvas"""
        self.__figure.canvas.draw()
        return self.__figure.canvas

    def save_plot(self, filename):
        """
        Save the plot to a file.

        :param filename: The name of the output file.
        """
        self.__figure.canvas.draw()
        image_size = self.__figure.canvas.get_width_height()
        image_rgb = self.__figure.canvas.tostring_rgb()
        pil_image = Img.frombytes("RGB", image_size, image_rgb)
        pil_image.save(filename, "JPEG")

    def save(self, filename=None, orientation=None, dpi=None, papertype=None):
        """
        Save the plot to a file.

        :param filename: The name of the output file.  The image format is determined
        from the file suffix: 'png', 'ps', and 'eps' are recognized.  If no
        file name is specified 'yyyymmdd_hhmmss.png' is created in the current
        directory.
        :param orientation: Orientation of the plot for 'ps' files: [ 'landscape' | 'portrait' ]
        :param dpi: Resolution !! not used anymore
        :param papertype: Papertype 'A4' for 'ps' files
        """
        if papertype is None:
            papertype = "A4"

        if filename is None:
            raise PlotException("Filename not specified.")

        file_ext = ['png', '.ps', 'eps']

        filename = opath.expandvars(filename)
        if filename[-3:].lower() in file_ext:
            try:
                if filename[-3:].lower() == ".ps":

                    fig_weight = self.__figure.get_figwidth()
                    fig_height = self.__figure.get_figheight()

                    if orientation is None:
                        # oriented
                        if fig_weight > fig_height:
                            orientation = 'landscape'
                        else:
                            orientation = 'portrait'

                    paper_weight, paper_height = papersize[papertype.lower()]
                    dscale = None
                    if orientation == 'landscape':
                        dscale = min(paper_height / fig_weight, paper_weight / fig_height)
                    else:
                        dscale = min(paper_weight / fig_weight, paper_height / fig_height)
                    owidth = dscale * fig_weight
                    ohight = dscale * fig_height
                    self.__figure.set_size_inches((owidth, ohight))
                    self.__figure.savefig(filename, orientation=orientation,
                                          papertype=papertype.lower())
                    self.__figure.set_size_inches((fig_weight, fig_height))
                else:
                    self.__figure.savefig(filename)

            except IOError as err:
                raise PlotException("Failed to save '%s' due to\n%s" % (filename, err))
        else:
            raise PlotException("Invalid image type. Valid types are: 'ps', 'eps', 'png'")

        return filename

    def set_font_size(self, fontsize):
        """ Set the Font size """
        label_list = self.__axes.get_xticklabels() + self.__axes.get_yticklabels()
        for label in label_list:
            label.set_size(fontsize)

    def get_axes_limits(self):
        """ Return the limits of the axes """
        return [self.__axes.get_xlim(), self.__axes.get_ylim()]

    def set_limits(self, xlim=None, ylim=None):
        """
        Set x, y limits of the plot, to leave one value unchanged use 'None' for it: xlim=[None, 2.0]

        :param xlim: list of [xmin, xmax]
        :param ylim: list of [ymin, ymax]
        """
        old_xlim = list(self.__axes.get_xlim())
        old_ylim = list(self.__axes.get_ylim())

        if xlim:
            for i in range(min(len(xlim), 2)):
                if xlim[i] is not None:
                    old_xlim[i] = xlim[i]

        if ylim:
            for i in range(min(len(ylim), 2)):
                if ylim[i] is not None:
                    old_ylim[i] = ylim[i]

        self.__axes.set_xlim(old_xlim)
        self.__axes.set_ylim(old_ylim)

    def axes_yticks(self):
        """ Get the y ticks """
        return self.__axes.get_yticks()

    def set_ylabel1_on(self, val):
        """ Set the y label """
        ticks = self.__axes.get_yticklabels()
        for tick in ticks:
            tick.label1On = val
            tick.tick1On = val

    @deprecated('set_ylabel1_on')
    def set_ylabel1On(self, val):  # pylint: disable=C0103
        """method name deprecated, please use set_ylabel1_on() instead

        :deprecated: use set_ylabel1_on instead
        """
        self.set_ylabel1_on(val)

    def set_xlabel1_on(self, val=False):
        """ Set the x label """
        ticks = self.__axes.get_xticklabels()
        for tick in ticks:
            tick.set_visible(val)

    @deprecated('set_xlabel1_on')
    def set_xlabel1On(self, val):  # pylint: disable=C0103
        """method name deprecated, please use set_xlabel1_on instead

        :deprecated: use set_xlabel1_on instead
        """
        self.set_xlabel1_on(val)

    def hide_yticklabels(self):
        """ Hide the y tick labels """
        self.__axes.get_yticklabels().set_visible(False)

    def get_axes(self):
        """ Get the axes """
        return self.__axes

    def set_legend(self, labels, legend_number=0):
        """ Set the legend """
        texts = self.__legends[legend_number].get_texts()
        if len(texts) != len(labels):
            return

        for idx in range(0, len(texts)):
            texts[idx].set_text(labels[idx])
            ytmp = texts[idx].get_position()[1]
            texts[idx].set_y(ytmp - 0.1)

    def add_legend(self, labels, colors, fontsize="xx-small", **kwargs):
        """
        Add a legend to the plot.

        :param labels: list of labels to be added
        :param colors: list of colors (one for each label)
        :param fontsize: size in points or string from 'xx-small', 'x-small' ... to 'xx-large'
        :param kwargs: additional keywords as used in called method `matplotlib.axes.Axes.legend`
        :keyword loc: location of the legend, possible values:
                1: upper right
                2: upper left
                3: lower left
                4: lower right
                5: right
                6: center left
                7: center right
                8: lower center
                9: upper center
                10: center
        """
        if not isinstance(labels, list):
            labels = list(labels)

        if not isinstance(colors, list):
            colors = list(colors)

        if len(labels) != len(colors):
            return

        # rects = []
        lines = []
        for color in colors:
            line = matplotlib.lines.Line2D([0], [0], marker='o', color=color)
            lines.append(line)

        legend = self.__axes.legend(lines, labels, **kwargs)

        # Set fontsize
        texts = legend.get_texts()
        for text in texts:
            text.set_size(fontsize)

        legend.draw_frame(False)

        self.__legends.append(legend)

    # disabling C0103: invalid name for parameters x,y; can't be changed as belong to API
    def plot(self, x=None, y=None, fmt=None, add=None, **kwargs):  # pylint: disable=C0103
        """
        Plot a line using the current line attributes
        """
        if x is None:
            if y is None:
                return
            x = list(range(len(y)))
        elif y is None:
            y = x
            x = list(range(len(y)))

        if fmt is None:
            line = self.__axes.plot(x, y, **kwargs)
        else:
            line = self.__axes.plot(x, y, fmt, **kwargs)

        self.__axes.grid(self.__show_grid)
        # Add to an existing line?

        if add is None or len(self.__lines) < add < 0:
            self.__lines.append(line)
        else:
            if add == 0:
                add = len(self.__lines)
                self.__lines[add - 1].extended(line)

        return line

    # disabling C0103: invalid name for parameter x; can't be changed as belongs to API
    def add_vline(self, x, **kwargs):  # pylint: disable=C0103
        """
        Adds a vertical line at x position.
        """
        plot = self.__axes.axvline(x, **kwargs)
        self.__vlines.append(plot)

    # disabling C0103: invalid name for parameter x; can't be changed as belongs to API
    def set_vline(self, x, line_number):  # pylint: disable=C0103
        """
        Sets an existing vertical line.
        """
        if 0 <= line_number < len(self.__vlines):
            self.__vlines[line_number].set_xdata([x, x])

    # disabling C0103: invalid name for parameters x,y; can't be changed as belong to API
    def add_text(self, x, y, text, *args, **kwargs):  # pylint: disable=C0103
        """
        Add text to the axes.
        """
        text = self.__axes.text(x, y, text, *args, **kwargs)
        self.__texts.append(text)

        return text

    def remove_texts(self):
        """
        Deletes all texts from the plot.

        Text numbering will be reset to 0.
        """
        for text_number in range(0, len(self.__texts)):
            self._remove_text(text_number)

        self.__texts = []

    def _remove_text(self, text_numbers=None):
        """
        Delete the 0-relative text number, default is to delete the last one.

        The remainning text(s) are not re-numbered
        """
        if text_numbers is None:
            text_numbers = [len(self.__texts) - 1]

        if not hasattr(text_numbers, '__iter__'):
            text_numbers = [text_numbers]

        for text_number in text_numbers:
            if 0 <= text_number < len(self.__texts):
                if self.__texts[text_number] is not None:
                    for text in self.__texts[text_number]:
                        text.set_text('None')
                        # self.__text[text_number] = None

    def set_major_locator(self, size):
        """ Set the mayor locator """
        if not size:
            return

        self.__axes.yaxis.set_major_locator(MaxNLocator(size))

    def draw(self):
        """ Draw canvas """
        # self._canvas.draw()
        self._canvas.draw()
        self._canvas.blit(self.__axes.bbox)

    def set_text(self, text_number=None, **kwargs):
        """
        Set attributes for specified text number

        number_number is 0-relative number of a text that already been plotted.
        If no text exists, attributes will be used for the next text(s).
        """
        if not self.__set_draw_mode:
            self._canvas.draw()
            self.__set_draw_mode = True

        redraw = False
        for keyw, val in kwargs.items():
            keyw = keyw.lower()
            if keyw == "colour":
                keyw = "color"

            if 0 <= text_number < len(self.__texts):
                if self.__texts[text_number]:
                    text = self.__texts[text_number]
                    getattr(text, "set_%s" % keyw)(val)
                    redraw = True

            else:
                if not val:
                    del self.__text_attributes[keyw]
                else:
                    self.__text_attributes[keyw] = val

            if redraw:
                self.__axes.draw_artist(self.__texts[text_number])

    def set_line(self, line_number=None, **kwargs):
        """
        Set attributes for specified line

        line_number is 0-relative number of a line that already been plotted.
        If no line exists, attributes will be used for the next line(s).
        """
        if not self.__set_draw_mode:
            self._canvas.draw()
            self.__set_draw_mode = True

        redraw = False
        for keyw, val in kwargs.items():
            keyw = keyw.lower()
            if keyw == "colour":
                keyw = "color"

            if 0 <= line_number < len(self.__lines):
                if self.__lines[line_number]:
                    for line in self.__lines[line_number]:
                        getattr(line, "set_%s" % keyw)(val)
                    redraw = True
            else:
                if not val:
                    del self.__line_attributes[keyw]
                else:
                    self.__line_attributes[keyw] = val

            if redraw:
                for segment in self.__lines[line_number]:
                    self.__axes.draw_artist(segment)
                # self.show(hardrefresh = False)

    def remove_lines(self):
        """
        Deletes all lines from the plot.

        Line numbering will be reset to 0.
        """
        for line_number in range(0, len(self.__lines)):
            self._remove_line(line_number)

        self.__axes.clear()
        self.__lines = []

    def clear(self):
        """ Clear local variables """
        self.__axes.clear()
        self.__lines = []
        self.__vlines = []
        self.__texts = []
        self.__legends = []

    def _remove_line(self, line_numbers=None):
        """
        Delete the 0-relative line number, default is to delete the last one.

        The remaining line(s) are not re-numbered
        """
        if line_numbers is None:
            line_numbers = [len(self.__lines) - 1]

        if not hasattr(line_numbers, '__iter__'):
            line_numbers = [line_numbers]

        for line_number in line_numbers:
            if 0 <= line_number < len(self.__lines):
                if self.__lines[line_number] is not None:
                    for line in self.__lines[line_number]:
                        line.set_linestyle('None')
                        self.__lines[line_number] = None
        # self._show()

    # there is no test for this method, couldn't work out the needed parameters to create valid input
    # does it work at all? still needed?
    # disabling C0103: invalid name for parameters x,y; can't be changed as belong to API
    def histogram(self, x=None, y=None, fmt=None, add=None):  # pylint: disable=C0103
        """
        Plot a histogram.

        :param x: histogram bin
        :param y: main histogram bin, x can be created as index
        :param fmt: Line style
        :param add:
        """

        if x is None:
            if y is None:
                return
            x = list(range(len(y)))

        if len(x) != len(y):
            return

        len2 = 2 * len(x)
        xlst2 = list(range(len2))
        ylst2 = list(range(len2))
        mlst2 = list(range(len2))

        if hasattr(y, "raw_mask"):
            y_mask = y.raw_mask()
            y_dat = y.raw_data()
        else:
            y_mask = y.mask
            y_dat = y.dat

        for i in range(len2):
            xlst2[i] = x[i / 2]
            mlst2[i] = y_mask[i / 2]

        ylst2[0] = 0.0

        for i in range(1, len2):
            ylst2[i] = y_dat[(i - 1) / 2]

        self.plot(xlst2, MaskedArray(ylst2, mask=mlst2, copy=0), fmt, add)

    def save_background(self):
        """ set the background """
        self.__background = self._canvas.copy_from_bbox(self.__axes.bbox)

    def restore_background(self):
        """ restore the background """
        if not self.__background:
            return
        self._canvas.restore_region(self.__background)

    def show(self, hardrefresh=True):
        """ show the drawing """
        if not hardrefresh:
            return
        self._canvas.draw()
        self.get_image().show()  # canvas.show() not supported in current matplotlib


# deprecated methods cause R0904 'too many public instances'
class ValidationPlot(object):
    """
    Provides common plot class for generating plots

    **1. Example:**

    .. python::
        # importing val_plot module
        import stk.img as val_plot

        # import python module for getting PointPair
                import stk.obj.geo as pp
        # Create instance of validation plot and with output directory passed as argument
        plotter = val_plot.ValidationPlot(self.__outdir)
        xlabel = 'x-axis [unit]'
        ylabel = 'y-axis [unit]'
        # list of time stamp
        timestamps = range(0, 101)
        # just a loop to show example to generate plot in bulk e.g here 50 plots are produced
        for count  in range(50):
            values = []
            for i in range(len(timestamps)):
                # generate some random values as example for plot demo
                values.append(random.uniform (3, 5))

            # create point pare list from timpestamp and values list
            data = [pp.GetPointPairList(timestamps, values)]
            # calling generate plot function to produce plot
            plotter.generate_plot(data, ['Using ScatterPlot'], xlabel, ylabel, False, True, line_colors=['r'])

            # getDrawing buffer to place the plot on PDF report
            drawing3 = plotter.get_drawing_from_buffer(plotter.get_plot_data_buffer(), None, width=300, height=90)
    """

    def __init__(self, path=None, title=None, width=None, height=None):
        """ Constructor to create ValidationPlot instance

        :param path: file path to store the plot into image file
        :type path: str
        :param title: Plot title
        :type title: str
        :param width: figure wdith
        :type width: int
        :param height: figure height
        :type height: int
        """
        self._log = Logger(self.__class__.__name__)
        self.__title = title
        self.__file_counter = 0
        if width is not None or height is not None:
            self.__valfig = ValidationFigure(fig_width=width, fig_height=height)
        else:
            self.__valfig = None

        self.__img_data = None
        if path is None:
            self.__out_path = gettempdir()
        else:
            if len(path) >= 255:
                self._log.info("Path >= 255 characters is used")
                path = "\\\\?\\" + path

            if not opath.exists(path):
                makedirs(path)
            self.__out_path = path

    def __str__(self):
        """ Get String representing the information of the instance """
        if self.__title is not None:
            if self.get_width() is not None and self.get_height():
                return self.__title + " (%dx%d) " % (self.get_width(), self.get_height())
            else:
                return self.__title
        else:
            return "Plot"

    def get_width(self):
        """ Get the width """
        return self.__valfig.get_width()

    def get_height(self):
        """ Get the height """
        return self.__valfig.get_height()

    def get_title(self):
        """ Get the title """
        return self.__title

    def generate_figure(self, subplots=None, fig_width=10, fig_height=3, show_grid=True):
        """ Generates a matplotlib figure

        :param subplots: List of subplots, ex: [221, 222, 223, 224]
        :type subplots: list of int
        :param fig_width: figure's width, default value is 10
        :type fig_width: int
        :param fig_height: figure's height, default value is 3
        :type fig_height: int
        :param show_grid: flag to display grid default is true
        :type show_grid: if boolean --> apply same flag to all subplots
                         if list of boolean --> each value in list enable/disable grid
                         of indivdual subplots
        """
        if subplots is not None and type(subplots) is list:
            if type(show_grid) is bool:
                show_grid = len(subplots) * [show_grid]

            if type(show_grid) is list:
                if len(subplots) != len(show_grid):
                    raise Exception("Length of show_grid is not equal to list of subplots")

        self.__valfig = ValidationFigure(subplots=subplots, fig_width=fig_width,
                                         fig_height=fig_height, show_grid=show_grid)
        return self.__valfig.get_axes()

    def get_bar_chart(self, axes, data, xlabel=None, ylabel=None, title=None, legend=None, rotate=None, size=10,
                      rwidth=0.8, xticks=None, xticks_labels=None, x_axis_ext=None, yticks=None, yticks_labels=None,
                      y_axis_ext=None, colors=None, extra_lines=None, extra_line_colors=None, bar_pos=None,
                      bar_orientation='vertical', **kwargs):
        """ **Plots a bar chart.**

        Bars can be stacked and/or grouped depending on input data.

        :param axes: matplotlib axes handle
        :param data: list of list of lists containing the already calculated histogram (frequencies)
            example data:
            3 bars/bins, no stacks/groups:    [[[1,2,3]]]
            2 bars/bins, stacked (2 classes) and grouped (2 sets): [[[1,5],[2,6]],[[4,8],[3,7]]]
            2 bars/bins, stacked (3 classes): [[[2,3],[3,2],[2,2]]]
            3 bars/bins, groups (3 sets):     [[[1,2,3]],[[5,4,3]],[[1,2,1]]]
        :param xlabel: label for the x-axis
        :param ylabel: label for the y-axis
        :param title: a title for the figure
        :param legend: a list of strings with the labels
        :param rotate: rotate tick labels (angle in degrees or one of the following keywords:
                       'horizontal' / 'vertical').
        :param size: size of the tick labels
        :param rwidth: relative width of the bar, compared to the width of the bin

        :param xticks: list of numbers that give the position of the ticks (marks) on the x-axis
        :param xticks_labels: list of strings or numbers used to set labels for the ticks in the x-axis
        :param x_axis_ext: list of two numbers to set the limits of the x-axis
        :param yticks: list of numbers that give the position of the ticks (marks) on the y-axis
        :param yticks_labels: list of strings or numbers used to set labels for the ticks in the y-axis
        :param y_axis_ext: list of two numbers to set the limits of the y-axis

        :param colors: list of lists of colors - according to number of sets and classes
        :param extra_lines: list of values; adds horizontal lines, one for each bar at the height
                            of the according value
        :param extra_line_colors: (optional) list of colors for extra lines
        :param bar_pos: list of custom position values for the positions of the bars (i.e. the bar groups)
        :param bar_orientation: choose if 'horizontal' or 'vertical' (normal) bar chart
        :param **kwargs: keyword arguments for the matplotlib bar function only!

        To set the values and colors follow these examples:

        .. Python::

            ax1 = generate_figure(fig_width=4.5, fig_height=2, show_grid=True)

            # several bars, all same color:
            data = [[[1, 2, 3, 4, 5]]]
            colors = [['yellow']]

            # 3 groups with 3 bars in red,green,blue
            #   |rd 1|gr 5|bl 1|  |rd 2|gr 4|bl 2|  |rd 3|gr 3|bl 1|
            data = [[[1, 2, 3]], [[5, 4, 3]], [[1, 2, 1]]]
            colors = [['red'], ['green'], ['blue']]

            # 2 groups with 2 bars, each with 2 stacks
            #    |gr 2|ye 3|   |gr 6|ye 7|
            #    |rd 1|bl 4|   |rd 5|bl 8|
            data = [[[1, 5], [2, 6]], [[4, 8], [3, 7]]]
            colors = [['red', 'green'], ['blue', 'yellow']]

            get_bar_chart(ax1, data, colors=colors)

        """

        # Adapt interface
        axes = self._get_appropriate_axes(axes)
        try:
            try:
                _ = len(data[0])
            except TypeError:
                data = [data]

            _ = len(data[0][0])
        except TypeError:
            data = [data]

        no_of_sets = len(data)
        no_of_classes_per_set = len(data[0])

        # check if number of bar groups is consistent for the data
        tmp_lens = []
        # check within a set
        for i in range(len(data)):
            for j in range(len(data[i])):
                if j == 0:
                    continue
                if len(data[i][j]) == len(data[i][j - 1]):
                    continue
                else:  # no_of_bar_groups is different for the classes/sets
                    return
            tmp_lens.append(len(data[i][0]))

        # check in between sets
        for i in range(len(tmp_lens)):
            if i == 0:
                continue
            if tmp_lens[i] == tmp_lens[i - 1]:
                continue
            else:  # no_of_bar_groups is different for the classes/sets
                return

        if colors is None or len(colors) != no_of_sets or len(colors[0]) != no_of_classes_per_set:
            colors = []
            cur_set = 0
            counter = 0
            while counter < no_of_sets:  # taking default colors
                colors.append(DEF_COLORS[cur_set:cur_set + no_of_classes_per_set])
                cur_set += no_of_classes_per_set
                counter += 1

        no_of_bar_groups = len(data[0][0])
        # check if number of custom bar_pos is consistent for the data
        if bar_pos is not None:
            if len(bar_pos) != no_of_bar_groups:
                bar_pos = None

        bar_group_range = numpy.arange(no_of_bar_groups)
        bar_width = rwidth / no_of_sets

        # Create actual bar for all bins/bar groups, for all sets, for all classes
        for bar_group in range(no_of_bar_groups):
            for cur_set in range(no_of_sets):
                last_height = 0
                for cur_class in range(no_of_classes_per_set):
                    if bar_pos is None:
                        bargroup_left = (bar_group + cur_set * bar_width)
                    else:
                        bargroup_left = (bar_pos[bar_group] + cur_set * bar_width)
                    if bar_orientation == 'vertical':
                        axes.bar(left=bargroup_left, height=data[cur_set][cur_class][bar_group], width=bar_width,
                                 color=colors[cur_set][cur_class], bottom=last_height, **kwargs)
                    else:
                        axes.barh(bargroup_left, data[cur_set][cur_class][bar_group], height=bar_width,
                                  color=colors[cur_set][cur_class], left=last_height, **kwargs)
                    last_height += data[cur_set][cur_class][bar_group]

        # add axis-labels, title and legend
        if xlabel is not None:
            axes.set_xlabel(xlabel, size=size)
        if ylabel is not None:
            axes.set_ylabel(ylabel, size=size)
        if title is not None:
            axes.set_title(title, size=size)
        if legend is not None:
            leg = axes.legend(legend, loc=1, prop={'size': size})
            leg.get_frame().set_alpha(0.5)

        # add x tick labels
        if xticks_labels is not None:
            if xticks is None:
                if bar_orientation == 'vertical':
                    lab_ind = []
                    if len(xticks_labels) == no_of_bar_groups:
                        # if every bar group should have a label
                        lab_ind.append(bar_group_range + .5 * no_of_sets * bar_width)
                    else:
                        # if every bar should have a label
                        for j in range(no_of_sets):
                            lab_ind.append(bar_group_range + (j + .5) * bar_width)
                    xticks = numpy.vstack(lab_ind).transpose().ravel()  # flatten the array for the label positions
            # add xticks_labels
            if xticks is not None:
                axes.set_xticks(xticks)
            axes.set_xticklabels(xticks_labels, rotation=rotate, size=size)
        # add y tick labels
        if yticks_labels is not None:
            if yticks is None:
                if bar_orientation == 'horizontal':
                    lab_ind = []
                    if len(yticks_labels) == no_of_bar_groups:
                        # if every bar group should have a label
                        lab_ind.append(bar_group_range + .5 * no_of_sets * bar_width)
                    else:
                        # if every bar should have a label
                        for j in range(no_of_sets):
                            lab_ind.append(bar_group_range + (j + .5) * bar_width)
                    yticks = numpy.vstack(lab_ind).transpose().ravel()  # flatten the array for the label positions
            # add xticks_labels
            if yticks is not None:
                axes.set_yticks(yticks)
            axes.set_yticklabels(yticks_labels)

        if extra_line_colors is None or extra_line_colors == [] or len(extra_line_colors) != no_of_bar_groups:
            extra_line_colors = ['Blue'] * no_of_bar_groups

        # add extra lines
        # (they only work properly for default xlim/ylim currently)
        if extra_lines is not None and len(extra_lines) == no_of_bar_groups:
            for i, res in enumerate(extra_lines):
                line_min = float(i) / no_of_bar_groups
                line_max = float(i + rwidth * 1.05) / no_of_bar_groups
                if bar_orientation == 'vertical' and x_axis_ext is None:
                    axes.axhline(y=res, xmin=line_min, xmax=line_max,
                                 linewidth=3, color=extra_line_colors[i])
                elif bar_orientation == 'horizontal' and y_axis_ext is None:
                    axes.axvline(x=res, ymin=line_min, ymax=line_max,
                                 linewidth=3, color=extra_line_colors[i])

        # fit data limits to given data (if x_axis_ext / y_axis_ext is None)
        stackheights = [0]
        for bar_group in range(no_of_bar_groups):
            for cur_set in range(no_of_sets):
                cur_height = 0
                for cur_class in range(no_of_classes_per_set):
                    cur_height += data[cur_set][cur_class][bar_group]
                stackheights.append(cur_height)
        if extra_lines is not None:  # consider case that extra_lines exceed the data
            stackheights.append(max(extra_lines))
            stackheights.append(min(extra_lines))
            delta = 0.0
        else:
            delta = 0.05
            # margin over highest value
            stackheights.append(max(stackheights) + 0.1 * fabs(max(stackheights) - min(stackheights)))

        if bar_pos is None:
            if rwidth < 1 and extra_lines is None:
                bar_pos = [0, no_of_bar_groups - (1 - rwidth)]
            else:
                bar_pos = [0, no_of_bar_groups]
        else:
            bar_pos.append(max(bar_pos) + rwidth)
        if bar_orientation == 'vertical':
            axes.set_xlim(self._limit_from_ext(x_axis_ext, bar_pos, delta))
            axes.set_ylim(self._limit_from_ext(y_axis_ext, stackheights))
        else:
            axes.set_xlim(self._limit_from_ext(x_axis_ext, stackheights))
            axes.set_ylim(self._limit_from_ext(y_axis_ext, bar_pos, delta))

        return pltt, bar_group_range

    @staticmethod
    def _limit_from_ext(axis_ext, data, delta=0):
        """
        Method for get_bar_chart

        :param axis_ext: parameter for the limits of the figure
        :param data: input data for the bar chart
        :param delta: the percentage value for the margin
        """
        data_max = numpy.amax(data)
        data_min = numpy.amin(data)

        if axis_ext is None:
            margin = delta * fabs(data_max - data_min)
            lim = [data_min - margin, data_max + margin]
        elif len(axis_ext) == 2:
            lim = axis_ext
        else:
            lim = [data_min, data_max]
        return lim

    def get_histogram(self, axes, data, binning, xlabel, ylabel, title, legend=None, tick_labels=None, rotate=None,
                      size=None, normed=1, rwidth=0.9, **kwargs):
        """ Calculates and plots a histogram

        :param axes: axes handle.
        :param data: List of lists containing the already calculated histogram (frequencies).
        :param binning: List of values for the x-axis.
        :param legend: a list of strings with the bar names.
        :param xlabel: label for the x-axis.
        :param ylabel: label for the y-axis.
        :param title: a title for the figure.
        :param tick_labels: List of strings or numbers used to set labels for the ticks in the x-axis.
        :param rotate: rotate tick labels (angle in degrees or one of the following keywords:
                       'horizontal' / 'vertical').
        :param size: size of the tick labels.
        :param rwidth: relative width of the bar, compared to the width of the bin.
        :param align: Controls how the histogram is plotted. 'left', 'mid' or 'right'.
        :param **kwargs: keyword arguments for the hist function only!
        """
        axes = self._get_appropriate_axes(axes)
        # Formatting the input data for the hist function
        inarr = numpy.array(data).T
        # Calculating the histogram
        if legend is not None:
            _, bins, _ = axes.hist(inarr, binning, normed=normed, label=legend, rwidth=rwidth, **kwargs)
        else:
            _, bins, _ = axes.hist(inarr, binning, normed=normed, rwidth=rwidth, **kwargs)
        # Setting the labels and legend
        axes.set_ylabel(ylabel, size=size)
        axes.set_xlabel(xlabel, size=size)
        axes.set_title(title, size=size)
        axes.set_xticks(bins)
        if tick_labels is not None:
            axes.set_xticklabels(tick_labels, rotation=rotate, size=size)
        # Setting the legend
        if legend is not None:
            axes.legend()

        return pltt, bins

    # disable C0103: invalid name; param 'mu' in API, can't be changed
    def get_normal_pdf(self, axes, bins, sigma, mu, legend=None, draw_lines=True, write_text=None,
                       gauss_color='orange', line_colors=None, tick_labels=None, title=None, xlabel=None,
                       ylabel=None):
        """ Plot the Probability Density Function of Normal distribution

        :param axes: axes handle.
        :param bins: List of values for which the gauss pdf is calculated.
        :param sigma: Standard deviation of the distribution
        :param mu: Mean value of the distribution
        :param legend(optional): A string for the label
        :param draw_lines(optional): Draw lines at mu-sigma, sigma, sigma+mu. Deactivated by default
        :param write_text(optional): Writes down the values of sigma and mu.
               Input is the location in the vertical axis, 1 being the top of the axes and 0 the bottom.
        :param gauss_color(optional): Color of tha gaussian plot.
        :param line_colors(optional): Color of the [mu-sigma, sigma, sigma+mu] lines
        :param tick_labels(optional): List of strings or numbers used to set labels for the ticks in the x-axis.
        :param title(optional): A title for the figure, if only a gauss plot has to be plotted for instance.
        :param xlabel(optional): A label for the x-axis, if only a gauss plot has to be plotted for instance.
        :param ylabel(optional): A label for the y-axis, if only a gauss plot has to be plotted for instance.
        """
        axes = self._get_appropriate_axes(axes)
        if not line_colors:
            line_colors = DEF_COLORS

        # Only display Gauss curve with a standard deviation bigger than 0
        if abs(sigma) > 0.0:
            # Get value for every x position of the bins vector
            yvals = mlab.normpdf(bins, mu, sigma)
            # Plot the gaussian distribution
            if legend is not None:
                axes.plot(bins, yvals, gauss_color, label=legend)
                pltt.legend()
            else:
                axes.plot(bins, yvals, gauss_color)
            if draw_lines is True:
                # Draw a vertical line at the mu position
                line = Line2D([mu, mu], [0, numpy.max(yvals)], color=line_colors[1], label=r'$\mu$', alpha=0.5, lw=1.5)
                axes.add_line(line)
                if abs(sigma) > 0.0:
                    # Draw a vertical line at the (mu - sigma) position
                    line = Line2D([mu - sigma, mu - sigma], [0, self._calc_gauss([mu - sigma], mu, sigma)[0]],
                                  color=line_colors[0], label=r'$\mu$' + ' - ' + r'$\sigma$', alpha=0.5, lw=1.5)
                    axes.add_line(line)
                    # Draw a vertical line at the (mu + sigma) position
                    line = Line2D([mu + sigma, mu + sigma], [0, self._calc_gauss([mu + sigma], mu, sigma)[0]],
                                  color=line_colors[2], label=r'$\mu$' + ' + ' + r'$\sigma$', alpha=0.5, lw=1.5)
                    axes.add_line(line)
        # otherwise just draw a line at the mean value
        else:
            if draw_lines is True:
                # Draw a vertical line at the mu position
                line = Line2D([mu, mu], [0, 1], color=line_colors[1], label=r'$\mu$', alpha=0.5, lw=1.5)
                axes.add_line(line)

        if write_text is not None:
            # Write down the values for mu and sigma
            axes.text(0.01, write_text,
                      r'$\mu$' + ' = ' + "%0.2f" % mu + ', ' + r'$\sigma$' + ' = ' + "%0.2f" %
                      sigma, transform=axes.transAxes)
        if tick_labels is not None:
            axes.set_xticklabels(tick_labels)
        # Setting axis labels and title if provided
        if ylabel is not None:
            axes.set_ylabel(ylabel)
        if xlabel is not None:
            axes.set_xlabel(xlabel)
        if title is not None:
            axes.set_title(title)
        pltt.axis('tight')
        return pltt

    def get_scatter_plot(self, data, data_names, x_axis_name, y_axis_name, bool_line, bool_legend, x_value_step=0,
                         y_value_step=0, line_colors=None, line_styles=None, fig_width=10, fig_height=3, title=None,
                         line_markers=None, line_width=None, x_axis_ext=None, y_axis_ext=None, xticks_labels=None,
                         yticks_labels=None, axes=None):
        """ Create a plot with two lines.

        :param data: Array of pair point lists representing data lines
        :param data_names: Name of the data lines
        :param x_axis_name: Name written on the x-axis.
        :param y_axis_name: Name written on the y-axis.
        :param bool_line: True for a line plot, False for a scatter plot.
        :param bool_legend: True for a legend and False for no legend.
        :param x_value_step: Value step on the x-axis. Default automatic.
        :param y_value_step: Value step on the y-axis. Default automatic.
        :param line_colors: Array of line colors (lenth of data needs to be equal) defined in DEF_COLORS
        :param line_styles: Array of line styles (lenth of data needs to be equal) defines in DEF_LINE_STYLES
        :param fig_width: The width of the figure (default = 10)
        :param fig_height: The height of the figure (default = 3)
        :param title: Title of the figure to be added
        :param line_markers: Array of line markers (lenth of data needs to be equal) defines in DEF_LINE_MARKERS
        :param y_axis_ext: By default extends by 10% of the maximum. If the min and max values are passed as a list,
                           this new list is taken as the limit [min,max]. Anyother value performs no extension
        :param x_axis_ext: Extend the x-axis scaling by 10% of the maximum.
        :param xticks_labels: List of strings labeling the ticks for the x-axis.
        :param yticks_labels: List of strings labeling the ticks for the y-axis.
        """
        _ = y_axis_ext  # Just fixed pylint unsed warning
        axes = self._get_appropriate_axes(axes, fig_width=fig_width, fig_height=fig_height)

        self.generate_plot(data, data_names, x_axis_name, y_axis_name,
                           bool_line, bool_legend,
                           x_value_step, y_value_step,
                           line_colors, line_styles,
                           fig_width, fig_height, title,
                           line_markers, line_width, x_axis_ext, y_axis_ext=None, plot_type=None, bar_width=None,
                           xticks_labels=xticks_labels, yticks_labels=yticks_labels, axes=axes)
        return self.__valfig.get_plot()

    def generate_plot(self, data, data_names, x_axis_name, y_axis_name, bool_line, bool_legend, x_value_step=0,
                      y_value_step=0, line_colors=None, line_styles=None, fig_width=10, fig_height=3, title=None,
                      line_markers=None, line_width=None, x_axis_ext=None, y_axis_ext=None, plot_type=None,
                      bar_width=None, xticks_labels=None, yticks_labels=None, axes=None):
        """ Create a scatter or bar plot .

        :param data: Array of pair point lists representing data lines
        :param data_names: Name of the data lines
        :param x_axis_name: Name written on the x-axis.
        :param y_axis_name: Name written on the y-axis.
        :param bool_line: True for a line plot, False for a scatter plot.
        :param bool_legend: True for a legend and False for no legend.
        :param x_value_step: Value step on the x-axis. Default automatic.
        :param y_value_step: Value step on the y-axis. Default automatic.
        :param line_colors: Array of line colors (lenth of data needs to be equal) defined in DEF_COLORS
        :param line_styles: Array of line styles (lenth of data needs to be equal) defines in DEF_LINE_STYLES
        :param fig_width: The width of the figure (default = 10)
        :param fig_height: The height of the figure (default = 3)
        :param title: Title of the figure to be added
        :param line_markers: Array of line markers (lenth of data needs to be equal) defines in DEF_LINE_MARKERS
        :param x_axis_ext: Extend the x-axis scaling by 10% of the maximum.
        :param y_axis_ext: By default extends by 10% of the maximum. If the min and max values are passed as a list,
                           this new list is taken as the limit [min,max]. Anyother value performs no extension
        :param plot_type: List of plottypes ("Bar" or "Scatter")
        :param xticks_labels: List of strings labeling the ticks for the x-axis.
        :param yticks_labels: List of strings labeling the ticks for the y-axis.
        """
        _, _ = x_value_step, y_value_step

        mins_x = []
        mins_y = []
        maxs_x = []
        maxs_y = []
        if axes is not None:
            xlim = axes.get_xlim()
            mins_x.append(xlim[0])
            maxs_x.append(xlim[1])

            ylim = axes.get_ylim()
            mins_y.append(ylim[0])
            maxs_y.append(ylim[1])

        axes = self._get_appropriate_axes(axes, fig_width=fig_width, fig_height=fig_height)

        if line_colors is not None and len(line_colors) != len(data):
            line_colors = None
        if line_styles is not None and len(line_styles) != len(data):
            line_styles = None
        if line_markers is not None and len(line_markers) != len(data):
            line_markers = None
        if line_width is not None and len(line_width) != len(data):
            line_width = None

        keyw = {}

        for i in range(len(data)):
            keyw = {}
            xdata, ydata = zip(*data[i])

            if xdata is None or len(xdata) == 0:
                continue
            mins_x.append(min(xdata))
            mins_y.append(min(ydata))
            maxs_x.append(max(xdata))
            maxs_y.append(max(ydata))
            if i < len(data_names):
                keyw['label'] = data_names[i]
            else:
                try:
                    keyw.pop('label')
                except KeyError:
                    pass

            if line_colors is not None:
                keyw['color'] = line_colors[i]
            else:
                keyw['color'] = DEF_COLORS[i % len(DEF_COLORS)]

            if line_styles is not None:
                keyw['linestyle'] = line_styles[i]

            if line_width is not None:
                keyw['linewidth'] = line_width[i]

            if line_markers is not None and line_markers[i] != "None":
                keyw['marker'] = line_markers[i]
                keyw['markerfacecolor'] = keyw['color']
                keyw['markeredgecolor'] = keyw['color']
                keyw['markersize'] = 3
            else:
                if bool_line is False:
                    keyw['marker'] = DEF_LINE_MARKERS[1:][i % (len(DEF_LINE_MARKERS) - 1)]

            if bool_line is False:
                keyw['linestyle'] = DEF_LINE_STYLES[4]

            if plot_type is not None:
                if plot_type[i] == "Bar":
                    if bar_width is not None:
                        keyw['width'] = bar_width[i]
                    else:
                        keyw['width'] = 5
                    axes.bar(xdata, ydata, **keyw)
                else:
                    axes.plot(xdata, ydata, **keyw)
            else:
                if len(xdata) == 1:
                    keyw['marker'] = DEF_LINE_MARKERS[(i % (len(DEF_LINE_MARKERS) - 1)) + 1]
                    keyw['linestyle'] = DEF_LINE_STYLES[4]
                axes.plot(xdata, ydata, **keyw)

        if len(mins_x) == 0 or len(mins_y) == 0 or len(maxs_x) == 0 or len(maxs_y) == 0:
            raise PlotException("Input Data not valid.")
        else:
            min_x = min(mins_x)
            min_y = min(mins_y)
            max_x = max(maxs_x)
            max_y = max(maxs_y)

        if y_axis_ext is None:
            delta_y = 0.1 * fabs(max_y - min_y)
            ylim = [min_y - delta_y, max_y + delta_y]
        elif len(y_axis_ext) == 2:
            ylim = y_axis_ext
        else:
            ylim = [min_y, max_y]

        if x_axis_ext is None:
            # Do a x axis scaling extension
            delta_x = 0.1 * fabs(max_x - min_x)
            xlim = [min_x - delta_x, max_x + delta_x]
        elif len(x_axis_ext) == 2:
            xlim = x_axis_ext
        else:
            xlim = [min_x, max_x]

        axes.set_xlim(xlim)
        axes.set_ylim(ylim)

        axes.set_xlabel(x_axis_name, fontsize=8, verticalalignment='center')
        axes.set_ylabel(y_axis_name, fontsize=8)
        if xticks_labels is not None:
            axes.set_xticklabels(xticks_labels)
        if yticks_labels is not None:
            axes.set_yticklabels(yticks_labels)

        if title is not None:
            axes.set_title(title, fontsize=8)

        if bool_legend and 'label' in keyw:
            font_prop = FontProperties(size=8)
            leg = axes.legend(ncol=min(len(data_names), 4), prop=font_prop, loc='best')
            leg.get_frame().set_alpha(0.5)  # set transparency

        return self.__valfig.get_plot()

    def get_median_plot(self, axes, data, x_axis_name, y_axis_name, title=None,
                        xticks_labels=None, y_axis_ext=None,
                        box_width=0.5, whisker_box_ratio=1.5, notched_box=False,
                        outlier_sym='+', vert_orientation=True, box_color=None, **kwargs):
        """ Generate a Media Plot of the given data

        :param axes: Axes of the figure
        :type axes: Axes or ValdationFigure
        :param data: plot data
        :type data: list of name
        :param x_axis_name: label of x-axis
        :type x_axis_name: str
        :param y_axis_name: label for y-axis
        :type y_axis_name: str
        :param title: title of the plot
        :type title: str
        :param xticks_labels: TODO
        :type xticks_labels: TODO
        :param y_axis_ext: addtional extension to y-axis typically max value of the y axis
        :type y_axis_ext: int
        :param box_width: width of the box
        :type box_width: int
        :param whisker_box_ratio: plot whisker ratio
        :type whisker_box_ratio: int
        :param notched_box: flag to control notch for box plot
        :param outlier_sym: outline symbol e.g. '+' '-'  '*'
        :type outlier_sym: char
        :param vert_orientation: plot orientiation flag
        :type vert_orientation: boolean
        :param box_color: TODO
        :type box_color: TODO
        """
        axes = self._get_appropriate_axes(axes)
        # boxplot crashes if the given data vector is empty
        if len(data) > 0:
            bp = axes.boxplot(data, notch=notched_box, sym=outlier_sym, vert=vert_orientation,
                              whis=whisker_box_ratio, widths=box_width, **kwargs)
            if type(data[0]) is list:
                if box_color is None:
                    for i, _ in enumerate(bp['boxes']):
                        color = DEF_COLORS[i]
                        bp['boxes'][i].set(color=color)
                else:
                    for idx, col in enumerate(box_color):
                        bp['boxes'][idx].set(color=col)

        if type(data[0]) is list:
            max_val = []
            min_val = []
            for i in data:
                max_val.append(max(i))
                min_val.append(min(i))
            if y_axis_ext is None:
                max_y = max(max_val)
                min_y = min(min_val)
                delta_y = 0.05 * fabs(max_y - min_y)
                ylim = [min_y - delta_y, max_y + delta_y]
            elif len(y_axis_ext) == 2:
                ylim = y_axis_ext
            else:
                ylim = [min(data), max(data)]
        else:
            if title is not None:
                axes.set_title(title, fontsize=8)
            axes.set_xlabel(x_axis_name, fontsize=8, verticalalignment='center')
            axes.set_ylabel(y_axis_name, fontsize=8)

            if y_axis_ext is None:
                max_y = max(data)
                min_y = min(data)
                delta_y = 0.05 * fabs(max_y - min_y)
                ylim = [min_y - delta_y, max_y + delta_y]
            elif len(y_axis_ext) == 2:
                ylim = y_axis_ext
            else:
                ylim = [min(data), max(data)]

        axes.set_ylim(ylim)

        if xticks_labels is not None:
            axes.set_xticklabels(xticks_labels, fontsize=8)

        return self.__valfig.get_plot()

    def get_pie_chart(self, axes, data, title=None, labels=None, legend=None, colors=None, labels_fontsize=None,
                      legend_fontsize=6, title_fontsize=12, **kwargs):
        """ Plots a pie chart.

        :param axes: axes handle
        :type axes: ValidationFigure or axes
        :param data: List of values; The fractional area of each wedge is given by x/sum(x)
        :param title: a title for the figure
        :param labels: list of strings as a description of the wedges (must be same length as data)
        :param legend: if set True: labels are given as a legend if list of strings: custom legend
        :param colors: list of colors for the wedges
        :param labels_fontsize: size for the labels
        :param legend_fontsize: size for the legend , by default the value is 6
        :param title_fontsize: size for the legend , by default the value is 12
        :param kwargs: keyword arguments for the matplotlib pie function
            e.g. explode (a len(data) array which specifies the fraction of the radius with which to offset each wedge)
            e.g. shadow (False or True)
            note: startangle -> not in matplotlib 1.0.1
        """
        axes = self._get_appropriate_axes(axes)

        if labels is not None:
            if len(labels) != len(data):
                labels = None

        if colors is None or len(colors) != len(data):
            colors = []
            for i, _ in enumerate(data):
                colors.append(DEF_COLORS[i])

        # ret = pltt.pie(data, labels=labels, colors=colors, **kwargs)
        ret = axes.pie(data, labels=labels, colors=colors, **kwargs)
        # print(ret)
        texts = ret[1]
        # print(texts)
        if labels_fontsize is not None:
            for text in texts:
                text.set_fontsize(labels_fontsize)

        if title is not None:
            # pltt.title(title, bbox={'facecolor': '0.8', 'pad': 5})
            axes.set_title(title, size=title_fontsize)

        if len(data) > 1:
            no_of_col = int(ceil(float(len(data)) / 2))
        else:
            no_of_col = len(data)

        if legend is not None and legend is not True:
            leg = axes.legend(legend, bbox_to_anchor=(1.05, 1.10), loc=1,
                              prop={'size': legend_fontsize}, ncol=no_of_col)
            leg.get_frame().set_alpha(0.5)
        elif legend and labels:
            leg = axes.legend(labels, bbox_to_anchor=(1.05, 1.10), loc=1,
                              prop={'size': legend_fontsize}, ncol=no_of_col)
            leg.get_frame().set_alpha(0.5)

        return self.__valfig.get_plot()

    def set_image_data_buffer(self, img_data):
        """Set the Image DataBuffer loaded from DB

        :param img_data: buffer of the image data
        :type img_data: buffer
        """
        self.__img_data = img_data

    def get_plot_data_buffer(self, pltt_=None, grid=None, fontsize=8):
        """ Get a buffer containing the plot image

        :param pltt_: plot (if 'None', the stored plot is used)
        :param grid:
        :return: Buffer of data
        """
        _ = pltt_  # unsed parameter warning Fix
        plot_for_saving = BasePlot(figure=self.__valfig.get_fig(), fontsize=fontsize)
        if grid is not None:
            plot_for_saving.set_grid(grid)
        else:
            plot_for_saving.set_grid(self.__valfig.get_show_grid())

        filepointer = NamedTemporaryFile(mode='r+b', suffix="." + DEFAULT_OUTPUT_FILEEXT,
                                         prefix='Valf_' + "_%s" % str(uuid4()),
                                         dir=self.__out_path, delete=False)
        plot_for_saving.save(filepointer.name, dpi=400, papertype=None)
        buf = buffer(filepointer.read())
        filepointer.close()
        unlink(filepointer.name)
        self.__valfig.get_plot().close()
        subplots = self.__valfig.get_subplots()
        fig_width = self.__valfig.get_width()
        fig_height = self.__valfig.get_height()
        show_grid = self.__valfig.get_show_grid()
#         self.__valfig = None
#         self.generate_figure(subplots, fig_width, fig_height, show_grid)
        return buf

    def get_drawing(self, file_name=None, width=DRAWING_W, height=DRAWING_H):
        """Get the drawing of the stored image of the current plot

        :param file_name: file name
        :type file_name: str
        :param width: width of the drawing
        :type width: int
        :param height: height of the drawing
        :type height: int
        """

        if self.__img_data is not None:
            return self.get_drawing_from_buffer(self.__img_data,
                                                file_name=file_name,
                                                width=width, height=height)
        else:
            img_data = self.get_plot_data_buffer()
            return self.get_drawing_from_buffer(img_data, file_name=file_name,
                                                width=width, height=height)

    def get_drawing_from_buffer(self, draw_data, file_name=None, width=None, height=None):
        """ Converts the given Drawing object into a string

        :param draw_data: Drawing as Buffer
        :param file_name: File name extension
        :param width: Width of the new drawing (optional)
        :param height: Height of the new drawing (optional)
        """
        if self.__valfig is not None:
            if width is None:
                width = self.get_width() * self.__valfig.get_fig().dpi
            if height is None:
                height = width * self.get_height() / self.get_width()

        if width is None and height is None:
            return None

        if draw_data is not None:
            # get drawing format
            file_ext = imghdr.what('', draw_data)
            if file_ext is None:
                file_ext = DEFAULT_OUTPUT_FILEEXT

            # store the file into the temp output path
            if file_name is not None:
                if len(file_name) > 100:
                    self._log.info("image file name >= 100 characters will be truncated")
                    file_name = file_name[0:96] + "_" + str(self.__file_counter)
                    self.__file_counter += 1
                filename = opath.join(self.__out_path, "%s.%s" % (file_name, file_ext))
                if len(filename) >= 255:
                    self._log.info("Path to image file >= 255 characters is used")
                    filename = "\\\\?\\" + filename
                    ofile = file(filename, "wb")
                else:
                    ofile = file(filename, "wb")
            else:
                ofile = NamedTemporaryFile(mode='w+b', suffix="." + file_ext,
                                           prefix='ValfReport_' + "_%s" % str(uuid4()),
                                           dir=self.__out_path, delete=False)
                filename = ofile.name

            ofile.write(draw_data)
            ofile.close()
            # image from file
            drw = Drawing(width, height)
            inpath = str(filename)
            img = Image(0, 0, width, height, inpath)
            drw.add(img)
            return drw
        return None

    @staticmethod
    def get_subplot_grid(row=None, column=None, subplots_count=None):
        """
        Generate list of subplot to use for Figure Generation.

        Atleast any two argument must be pass in this function

        :param row: no. of rows
        :type row: int
        :param column: no. of column
        :type column: int
        :param subplots_count: total no. of subplots in a grid
        :type subplots_count: int
        """
        subplots = []
        if row is not None and column is not None and subplots_count is None:
            subplots_count = row * column
        elif row is None and column is not None and subplots_count is not None:
            row = int(ceil(subplots_count / float(column)))

        elif row is not None and column is None and subplots_count is not None:
            column = int(ceil(subplots_count / float(row)))

        if row is not None and column is not None and subplots_count is not None:
            for i in range(1, subplots_count + subplots_count/10 + 1):
                if i % 10 != 0:  # newer matplot checks for num>0
                    subplots.append((row * 100) + (column * 10) + i)
        else:
            raise Exception("You must pass atleast two argument")

        return subplots

    def _get_appropriate_axes(self, axes, fig_width=10, fig_height=3):
        """Get the appropriate reference of Axes with following precedence sequence

        *    axes from ValidationFigure
        *    axes from last generated ValidationFigure
        *    axes from new ValidationFigure

        :param axes: existing axes
        :type axes: can be matplot Axes/None/ValdiationFigure
        :param fig_width: width of figure
        :param fig_height: height of the figure
        :return axes: Return Axes
        :type axes: matplot Axes
        """
        if type(axes) == ValidationFigure:
            axes = axes.get_axes()
        elif self.__valfig is not None and axes is None:
            axes = self.__valfig.get_axes()
        elif axes is None:
            axes = self.generate_figure(fig_width=fig_width, fig_height=fig_height)
        return axes

    @staticmethod
    def _calc_gauss(value, mean_val, std_dev):
        """Calculate the gaussian function

            Function is deprecated - do not use

        :param value: list of value
        :type value: list of int
        :param mean_val: mean value
        :type mean_val: int
        :param std_dev: standard deviation
        :type std_dev: int
        :return gauss: list of values represing gaussian curve
        :rtype: list of int
        """

        if (abs(std_dev) > 0.0):
            gauss = [exp(-1 * (pow((v - mean_val), 2) / (2 * pow(std_dev, 2)))) /
                     (std_dev * sqrt(2 * pi)) for v in value]
        else:
            gauss = [0 for v in value]
        return gauss

# deprecated methods of class ValidationPlot to keep compatibility,
# should be removed in next major release (stk 02.02.01)

    @deprecated('get_width')
    def GetWidth(self):  # pylint: disable=C0103
        """method name deprecated, please use get_width() instead

        :deprecated: name changed to get_width()
        """
        return self.get_width()

    @deprecated('get_height')
    def GetHeight(self):  # pylint: disable=C0103
        """method name deprecated, please use get_height() instead

        :deprecated: name changed to get_height()
        """
        return self.get_height()

    @deprecated('get_title')
    def GetTitle(self):  # pylint: disable=C0103
        """method name deprecated, please use get_title() instead

        :deprecated: name changed to get_title()
        """
        return self.get_title()

    @deprecated('generate_figure')
    def GenerateFigure(self, subplots=None, fig_width=10, fig_height=3, show_grid=True):  # pylint: disable=C0103
        """method name deprecated, please use generate_figure() instead

        :deprecated: name changed to generate_figure()
        """
        return self.generate_figure(subplots, fig_width, fig_height, show_grid)

    @deprecated('get_bar_chart')
    def GetBarChart(self, axes, data, xlabel=None, ylabel=None, title=None, legend=None,  # pylint: disable=C0103,R0913
                    rotate=None, size=10, rwidth=0.8, xticks=None, xticks_labels=None, x_axis_ext=None, yticks=None,
                    yticks_labels=None, y_axis_ext=None, colors=None, extra_lines=None, bar_pos=None,
                    bar_orientation='vertical', **kwargs):
        """method name deprecated, please use get_bar_chart() instead

        :deprecated: name changed to get_bar_chart()
        """
        return self.get_bar_chart(axes, data, xlabel, ylabel, title, legend, rotate, size, rwidth,
                                  xticks, xticks_labels, x_axis_ext, yticks, yticks_labels,
                                  y_axis_ext, colors, extra_lines, bar_pos, bar_orientation)

    @deprecated('get_histogram')
    def GetHistogram(self, axes, data, binning, xlabel, ylabel, title, legend=None,  # pylint: disable=C0103,R0913
                     tick_labels=None, rotate=None, size=None, normed=1,
                     rwidth=0.9, **kwargs):
        """method name deprecated, please use get_histogram() instead

        :deprecated: name changed to get_histogram()
        """
        return self.get_histogram(axes, data, binning, xlabel, ylabel, title, legend,
                                  tick_labels, rotate, size, normed, rwidth, **kwargs)

    @deprecated('get_normal_pdf')
    def GetNormalPdf(self, axes, bins, sigma, mu, legend=None, draw_lines=True,  # pylint: disable=W0102,C0103,R0913
                     write_text=None, gauss_color='orange',
                     line_colors=DEF_COLORS, tick_labels=None,
                     title=None, xlabel=None,
                     ylabel=None):
        """method name deprecated, please use get_normal_pdf() instead

        :deprecated: name changed to get_normal_pdf()
        """
        return self.get_normal_pdf(axes, bins, sigma, mu, legend, draw_lines,
                                   write_text, gauss_color, line_colors, tick_labels,
                                   title, xlabel, ylabel)

    @deprecated('get_scatter_plot')
    def GetScatterPlot(self, data, data_names, x_axis_name, y_axis_name,  # pylint: disable=W0613,R0913,R0914,C0103
                       bool_line, bool_legend, x_value_step=0, y_value_step=0,
                       line_colors=None, line_styles=None,
                       fig_width=10, fig_height=3, title=None,
                       line_markers=None, line_width=None,
                       x_axis_ext=None, y_axis_ext=None,
                       xticks_labels=None, yticks_labels=None, axes=None):
        """method name deprecated, please use get_scatter_plot() instead

        :deprecated: name changed to get_scatter_plot()
        """
        return self.get_scatter_plot(data, data_names, x_axis_name, y_axis_name,
                                     bool_line, bool_legend, x_value_step, y_value_step,
                                     line_colors, line_styles,
                                     fig_width, fig_height, title,
                                     line_markers, line_width,
                                     x_axis_ext, y_axis_ext,
                                     xticks_labels, yticks_labels, axes)

    @deprecated('generate_plot')
    def GeneratePlot(self, data, data_names, x_axis_name, y_axis_name, bool_line,  # pylint: disable=R0914,R0913,C0103
                     bool_legend, x_value_step=0, y_value_step=0, line_colors=None, line_styles=None,
                     fig_width=10, fig_height=3, title=None, line_markers=None, line_width=None,
                     x_axis_ext=None, y_axis_ext=None, plot_type=None, barWidth=None,
                     xticks_labels=None, yticks_labels=None, axes=None):
        """method name deprecated, please use generate_plot() instead

        param name barWidth changed also to bar_width in generate_plot

        :deprecated: name changed to generate_plot()
        """
        return self.generate_plot(data, data_names, x_axis_name, y_axis_name, bool_line,
                                  bool_legend, x_value_step, y_value_step, line_colors, line_styles,
                                  fig_width, fig_height, title, line_markers, line_width,
                                  x_axis_ext, y_axis_ext, plot_type, barWidth,
                                  xticks_labels, yticks_labels, axes)

    @deprecated('get_bar_chart')
    def GetBarPlot(self, axes, bar_data, bar_pos, x_axis_name, y_axis_name,  # pylint: disable=R0914,R0913,C0103
                   title=None, xticks=None, xticks_labels=None, x_axis_ext=None,
                   yticks=None, yticks_labels=None, y_axis_ext=None, bar_width=0.9,
                   bar_orientation='vertical', **kwargs):
        """method name deprecated, please use get_bar_chart() instead
        Interface Wrapper of Method GetBarPlot for backward compatibility

        use get_bar_chart instead

        :deprecated: use `get_bar_chart()` instead
        """
        # handle bar_pos
        _, _ = self.get_bar_chart(axes, bar_data, xlabel=x_axis_name, ylabel=y_axis_name,
                                  title=title, xticks=xticks, xticks_labels=xticks_labels,
                                  x_axis_ext=x_axis_ext, yticks=yticks, yticks_labels=yticks_labels,
                                  y_axis_ext=y_axis_ext, rwidth=bar_width, bar_pos=bar_pos,
                                  bar_orientation=bar_orientation, **kwargs)

        return self.__valfig.get_plot()

    @deprecated('get_median_plot')
    def GetMedianPlot(self, axes, data, x_axis_name, y_axis_name, title=None,  # pylint: disable=R0914,R0913,C0103
                      xticks_labels=None, y_axis_ext=None,
                      box_width=0.5, whisker_box_ratio=1.5, notched_box=False,
                      outlier_sym='+', vert_orientation=True, **kwargs):
        """method name deprecated, please use get_median_plot() instead

        :deprecated: name changed to get_median_plot()
        """
        return self.get_median_plot(axes, data, x_axis_name, y_axis_name, title,
                                    xticks_labels, y_axis_ext,
                                    box_width, whisker_box_ratio, notched_box,
                                    outlier_sym, vert_orientation, **kwargs)

    @deprecated('get_pie_chart')
    def GetPieChart(self, axes, data, title=None, labels=None, legend=None,  # pylint: disable=R0914,R0913,C0103
                    colors=None, labels_fontsize=None, legend_fontsize=6, title_fontsize=12, **kwargs):
        """method name deprecated, please use get_pie_chart() instead

        :deprecated: name changed to get_pie_chart()
        """
        return self.get_pie_chart(axes, data, title, labels, legend, colors, labels_fontsize,
                                  legend_fontsize, title_fontsize, **kwargs)

    @deprecated('set_image_data_buffer')
    def SetImageDataBuffer(self, img_data):  # pylint: disable=C0103
        """method name deprecated, please use set_image_data_buffer() instead

        :deprecated: name changed to set_image_data_buffer()
        """
        return self.set_image_data_buffer(img_data)

    @deprecated('get_plot_data_buffer')
    def GetPlotDataBuffer(self, pltt_=None, grid=None, fontsize=8):  # pylint: disable=C0103
        """method name deprecated, please use get_plot_data_buffer() instead

        :deprecated: name changed to get_plot_data_buffer()
        """
        return self.get_plot_data_buffer(pltt_, grid, fontsize)

    @deprecated('get_drawing')
    def GetDrawing(self, file_name=None, width=DRAWING_W, height=DRAWING_H):  # pylint: disable=C0103
        """method name deprecated, please use get_drawing() instead

        :deprecated: name changed to get_drawing()
        """
        return self.get_drawing(file_name, width, height)

    @deprecated('get_drawing_from_buffer')
    def GetDrawingFromBuffer(self, draw_data, file_name=None, width=None, height=None):  # pylint: disable=C0103
        """method name deprecated, please use get_drawing_from_buffer() instead

        :deprecated: name changed to get_drawing_from_buffer()
        """
        return self.get_drawing_from_buffer(draw_data, file_name, width, height)

    @deprecated('get_subplot_grid')
    def GetSubplotGrid(self, row=None, column=None, subplots_count=None):  # pylint: disable=R0201,C0103
        """method name deprecated, please use get_subplot_grid() instead

        :deprecated: name changed to get_subplot_grid()
        """
        return self.get_subplot_grid(row, column, subplots_count)


"""
 $Log: plot.py  $
 Revision 1.7.1.2 2017/08/21 20:20:51CEST Hospes, Gerd-Joachim (uidv8815) 
 correct num of columns if not set, prevent '0'
 Revision 1.7.1.1 2017/07/26 16:52:53CEST Hospes, Gerd-Joachim (uidv8815)
 replace deprecated fromstring with frombyte, add SetUp in test to create out folder
 Revision 1.7 2016/01/26 15:32:31CET Hospes, Gerd-Joachim (uidv8815)
 rem BasePlot.add_texts(), error for more than a year now, seemed not to be used
 Revision 1.6 2016/01/26 11:52:42CET Hospes, Gerd-Joachim (uidv8815)
 set_limits() fixed, also some other errors found during testing (like PlotException, show),
 more module tests added
 Revision 1.5 2015/12/07 11:44:57CET Mertens, Sven (uidv7805)
 removing some pep8 errors
 Revision 1.4 2015/12/04 17:37:54CET Hospes, Gerd-Joachim (uidv8815)
 expand docu at get_bar_chart()
 Revision 1.3 2015/07/30 10:43:16CEST Ahmed, Zaheer (uidu7634)
 bug fix to avoid blank axis at the time of saving or finalizing Validation Plot
 - Added comments -  uidu7634 [Jul 30, 2015 10:43:17 AM CEST]
 Change Package : 362594:1 http://mks-psad:7002/im/viewissue?selection=362594
 Revision 1.2 2015/07/27 11:28:41CEST Ahmed, Zaheer (uidu7634)
 if the legends are more than 4 then put them in new line
 --- Added comments ---  uidu7634 [Jul 27, 2015 11:28:41 AM CEST]
 Change Package : 359588:1 http://mks-psad:7002/im/viewissue?selection=359588
 Revision 1.1 2015/04/23 19:04:27CEST Hospes, Gerd-Joachim (uidv8815)
 Initial revision
 Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/img/project.pj
 Revision 1.57 2015/02/26 17:33:25CET Ahmed, Zaheer (uidu7634)
 added support for mulitple boxplot on same axis with different colors
 --- Added comments ---  uidu7634 [Feb 26, 2015 5:33:26 PM CET]
 Change Package : 310109:1 http://mks-psad:7002/im/viewissue?selection=310109
 Revision 1.56 2015/01/28 17:42:06CET Ellero, Stefano (uidw8660)
 Removed all img and plot based deprecated function usage inside stk and module tests.
 --- Added comments ---  uidw8660 [Jan 28, 2015 5:42:07 PM CET]
 Change Package : 296835:1 http://mks-psad:7002/im/viewissue?selection=296835
 Revision 1.55 2015/01/20 20:57:38CET Mertens, Sven (uidv7805)
 removing deprecated calls
 --- Added comments ---  uidv7805 [Jan 20, 2015 8:57:39 PM CET]
 Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
 Revision 1.54 2015/01/20 16:07:05CET Mertens, Sven (uidv7805)
 removing deprecated calls
 Revision 1.53 2014/09/29 15:37:13CEST Mertens, Sven (uidv7805)
 removing VAT import problem as plot functionality not needed any longer
 --- Added comments ---  uidv7805 [Sep 29, 2014 3:37:14 PM CEST]
 Change Package : 267610:1 http://mks-psad:7002/im/viewissue?selection=267610
 Revision 1.52 2014/09/25 13:29:17CEST Hospes, Gerd-Joachim (uidv8815)
 adapt stk.img files to style guide, new names used in all modules and tests except stk.img tests
 --- Added comments ---  uidv8815 [Sep 25, 2014 1:29:17 PM CEST]
 Change Package : 264203:1 http://mks-psad:7002/im/viewissue?selection=264203
 Revision 1.51 2014/09/10 09:00:44CEST Ahmed, Zaheer (uidu7634)
 close all the figures and generate new figure same as last after disposing it
 --- Added comments ---  uidu7634 [Sep 10, 2014 9:00:45 AM CEST]
 Change Package : 241665:2 http://mks-psad:7002/im/viewissue?selection=241665
 Revision 1.50 2014/09/09 16:38:42CEST Hecker, Robert (heckerr)
 BugFix for freeing the Memory.
 --- Added comments ---  heckerr [Sep 9, 2014 4:38:43 PM CEST]
 Change Package : 262935:1 http://mks-psad:7002/im/viewissue?selection=262935
 Revision 1.49 2014/07/03 17:18:04CEST Ahmed, Zaheer (uidu7634)
 changes made to provide flexiblity to set the axes limit manually for
 the last GeneratPlot() call inside
 ValidationPlot Class
 --- Added comments ---  uidu7634 [Jul 3, 2014 5:18:05 PM CEST]
 Change Package : 238568:1 http://mks-psad:7002/im/viewissue?selection=238568
 Revision 1.48 2014/05/23 10:11:40CEST Ahmed, Zaheer (uidu7634)
 Auto Axis Adjustment bug fix
 --- Added comments ---  uidu7634 [May 23, 2014 10:11:40 AM CEST]
 Change Package : 235087:1 http://mks-psad:7002/im/viewissue?selection=235087
 Revision 1.47 2014/05/22 17:10:32CEST Ahmed, Zaheer (uidu7634)
 Example Code written in Doc String to generate plot inside loop
 --- Added comments ---  uidu7634 [May 22, 2014 5:10:32 PM CEST]
 Change Package : 235086:1 http://mks-psad:7002/im/viewissue?selection=235086
 Revision 1.46 2014/05/08 10:47:20CEST Mertens, Sven (uidv7805)
 - moving logging to stk.util.Logger,
 - using fallback logger when plot is included elsewhere, e.g. inside VAT,
 - pep8 / pylint fixes
 --- Added comments ---  uidv7805 [May 8, 2014 10:47:21 AM CEST]
 Change Package : 233133:1 http://mks-psad:7002/im/viewissue?selection=233133
 Revision 1.45 2014/04/11 14:06:10CEST Ahmed, Zaheer (uidu7634)
 pep8 fixes
 --- Added comments ---  uidu7634 [Apr 11, 2014 2:06:10 PM CEST]
 Change Package : 230922:1 http://mks-psad:7002/im/viewissue?selection=230922
 Revision 1.44 2014/04/11 13:59:42CEST Ahmed, Zaheer (uidu7634)
 Added GetSubplotGrid() to get subplots automatically useful to create figure
 Fixe legend size font in GeneratePlot()
 --- Added comments ---  uidu7634 [Apr 11, 2014 1:59:42 PM CEST]
 Change Package : 227490:1 http://mks-psad:7002/im/viewissue?selection=227490
 Revision 1.43 2014/03/26 17:17:48CET Hecker, Robert (heckerr)
 Removed commented code....
 --- Added comments ---  heckerr [Mar 26, 2014 5:17:48 PM CET]
 Change Package : 227802:1 http://mks-psad:7002/im/viewissue?selection=227802
 Revision 1.42 2014/03/26 17:05:50CET Hecker, Robert (heckerr)
 Throwing now the correct Exception. :-)
 --- Added comments ---  heckerr [Mar 26, 2014 5:05:50 PM CET]
 Change Package : 227802:1 http://mks-psad:7002/im/viewissue?selection=227802
 Revision 1.41 2014/03/26 16:53:14CET Hecker, Robert (heckerr)
 BugFix applied.
 --- Added comments ---  heckerr [Mar 26, 2014 4:53:14 PM CET]
 Change Package : 227802:1 http://mks-psad:7002/im/viewissue?selection=227802
 Revision 1.40 2014/03/26 16:44:04CET Hecker, Robert (heckerr)
 BugFix.
 --- Added comments ---  heckerr [Mar 26, 2014 4:44:04 PM CET]
 Change Package : 221549:1 http://mks-psad:7002/im/viewissue?selection=221549
 Revision 1.39 2014/03/26 15:13:54CET Hecker, Robert (heckerr)
 Added support for python 3.
 Revision 1.38 2014/03/17 13:39:21CET Ahmed, Zaheer (uidu7634)
 Remove length Check is restored after fixing problem in moduletest
 --- Added comments ---  uidu7634 [Mar 17, 2014 1:39:21 PM CET]
 Change Package : 224333:1 http://mks-psad:7002/im/viewissue?selection=224333
 Revision 1.37 2014/03/17 11:06:39CET Ahmed, Zaheer (uidu7634)
 Remove length Check temporary
 --- Added comments ---  uidu7634 [Mar 17, 2014 11:06:39 AM CET]
 Change Package : 224333:1 http://mks-psad:7002/im/viewissue?selection=224333
 Revision 1.36 2014/03/17 10:58:27CET Ahmed, Zaheer (uidu7634)
 bug fix for checking length GenerateFigure()
 --- Added comments ---  uidu7634 [Mar 17, 2014 10:58:28 AM CET]
 Change Package : 224333:1 http://mks-psad:7002/im/viewissue?selection=224333
 Revision 1.35 2014/03/17 10:35:22CET Ahmed, Zaheer (uidu7634)
 if show_grid is boolean then it is applicable to all subplots if it is list
 then each value is applicable to indvidual subplot
 --- Added comments ---  uidu7634 [Mar 17, 2014 10:35:22 AM CET]
 Change Package : 224333:1 http://mks-psad:7002/im/viewissue?selection=224333
 Revision 1.34 2014/02/27 10:43:11CET Skerl, Anne (uid19464)
 *GeneratePlot(): set legend to transparent and position to "best"
 *GetPieChart(): use given axes to enable subplots
 --- Added comments ---  uid19464 [Feb 27, 2014 10:43:11 AM CET]
 Change Package : 221988:1 http://mks-psad:7002/im/viewissue?selection=221988
 Revision 1.33 2014/02/24 16:18:27CET Hospes, Gerd-Joachim (uidv8815)
 deprecated classes/methods/functions removed (planned for 2.0.9)
 --- Added comments ---  uidv8815 [Feb 24, 2014 4:18:27 PM CET]
 Change Package : 219922:1 http://mks-psad:7002/im/viewissue?selection=219922
 Revision 1.32 2014/01/21 10:40:53CET Weinhold, Oliver (uidg4236)
 Changed ValidationPlot.GeneratePlot() to enable large axis
 values as for example microsecond timestamps.
 --- Added comments ---  uidg4236 [Jan 21, 2014 10:40:53 AM CET]
 Change Package : 213501:1 http://mks-psad:7002/im/viewissue?selection=213501
 Revision 1.31 2013/10/30 17:48:32CET Hecker, Robert (heckerr)
 Fixed wrong usage of logger module.
 --- Added comments ---  heckerr [Oct 30, 2013 5:48:32 PM CET]
 Change Package : 204146:1 http://mks-psad:7002/im/viewissue?selection=204146
 Revision 1.30 2013/10/23 13:30:18CEST Raedler, Guenther (uidt9430)
 - fixed barchart and getDrawing from buffer (by JW and AV)
 --- Added comments ---  uidt9430 [Oct 23, 2013 1:30:18 PM CEST]
 Change Package : 191955:1 http://mks-psad:7002/im/viewissue?selection=191955
 Revision 1.29 2013/09/19 13:30:09CEST Ahmed-EXT, Zaheer (uidu7634)
 -- New Class added ValidationFigure the functionality of figure handling
    from ValidationPlot moved to new class
   - added __GetAppropriateAxes() in ValdiationPlot
    - bugfix for showgrid in GetPlotDataBuffer
     - Added feature of height and width adjustment in GetDrawingBuffer to be
       taken from figure or provided as arguement
 --Improved documentation
 --removed commented code
 --fixed pep8 and pylint errors
 --- Added comments ---  uidu7634 [Sep 19, 2013 1:30:09 PM CEST]
 Change Package : 196580:2 http://mks-psad:7002/im/viewissue?selection=196580
 Revision 1.28 2013/09/12 17:52:32CEST Verma-EXT, Ajitesh (uidv5394)
 changes in legends:
 - adding the legends fontsize
 - no of coloumns in legends
 --- Added comments ---  uidv5394 [Sep 12, 2013 5:52:32 PM CEST]
 Change Package : 196582:1 http://mks-psad:7002/im/viewissue?selection=196582
 --- Added comments ---  uidv5394 [Sep 12, 2013 5:53:49 PM CEST]
 change in GetPieChart function
 Revision 1.27 2013/09/12 14:02:13CEST Raedler, Guenther (uidt9430)
 - fixed problem if filename is not given in (GetDrawingFromBuffer)
 - implememt automatic scaling of images
 --- Added comments ---  uidt9430 [Sep 12, 2013 2:02:13 PM CEST]
 Change Package : 191955:1 http://mks-psad:7002/im/viewissue?selection=191955
 Revision 1.26 2013/09/06 12:58:12CEST Raedler, Guenther (uidt9430)
 - fixed error for default condition
 --- Added comments ---  uidt9430 [Sep 6, 2013 12:58:12 PM CEST]
 Change Package : 191955:1 http://mks-psad:7002/im/viewissue?selection=191955
 Revision 1.25 2013/08/09 16:10:08CEST Raedler, Guenther (uidt9430)
 - improved bar plot functions (changes by JW)
 --- Added comments ---  uidt9430 [Aug 9, 2013 4:10:08 PM CEST]
 Change Package : 191955:1 http://mks-psad:7002/im/viewissue?selection=191955
 Revision 1.24 2013/08/06 16:30:12CEST Raedler, Guenther (uidt9430)
 - fixed BarPlot issues
 --- Added comments ---  uidt9430 [Aug 6, 2013 4:30:12 PM CEST]
 Change Package : 191955:1 http://mks-psad:7002/im/viewissue?selection=191955
 Revision 1.23 2013/08/06 10:54:24CEST Dintzer, Philippe (dintzerp)
 - handle long paths > 255 chars
 --- Added comments ---  dintzerp [Aug 6, 2013 10:54:25 AM CEST]
 Change Package : 175136:3 http://mks-psad:7002/im/viewissue?selection=175136
 Revision 1.22 2013/08/02 12:49:20CEST Raedler, Guenther (uidt9430)
 - created method GetPieChart()
 --- Added comments ---  uidt9430 [Aug 2, 2013 12:49:20 PM CEST]
 Change Package : 191955:1 http://mks-psad:7002/im/viewissue?selection=191955
 Revision 1.21 2013/07/30 14:08:32CEST Raedler, Guenther (uidt9430)
 - added documentation
 - revert removal of __CalcGauss
 --- Added comments ---  uidt9430 [Jul 30, 2013 2:08:32 PM CEST]
 Change Package : 191955:1 http://mks-psad:7002/im/viewissue?selection=191955
 Revision 1.20 2013/07/30 08:17:33CEST Raedler, Guenther (uidt9430)
 - extended GetBarChart()
   * changed data interface
   * support stacked bar charts
   * support regression bar charts including req value line
 - fixed wrong default value in GeneratePlot()
 - use numpy.mlab to calc. norm pdf  in GetNormalPdf()
 - use GetBarPlot() as wrapper funktion. Internally we use the GetBarChart
 - removed unused methods sd() and __CalcGauss()
 - started implementing module tests
 --- Added comments ---  uidt9430 [Jul 30, 2013 8:17:33 AM CEST]
 Change Package : 191955:1 http://mks-psad:7002/im/viewissue?selection=191955
 Revision 1.19 2013/07/15 15:34:52CEST Raedler, Guenther (uidt9430)
 - optimized file handling
 - fixed marker issue
 --- Added comments ---  uidt9430 [Jul 15, 2013 3:34:52 PM CEST]
 Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
 Revision 1.18 2013/07/03 07:39:41CEST Raedler, Guenther (uidt9430)
 - added new methods GetBarPlot() and GetMedianPlot()
 - fixed errors in GeneratePlot
 - improved save plot using pil.image
 --- Added comments ---  uidt9430 [Jul 3, 2013 7:39:41 AM CEST]
 Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
 Revision 1.17 2013/06/14 09:31:12CEST Mertens, Sven (uidv7805)
 method for retrieving pure PIL image from plot needed
 --- Added comments ---  uidv7805 [Jun 14, 2013 9:31:12 AM CEST]
 Change Package : 185933:2 http://mks-psad:7002/im/viewissue?selection=185933
 Revision 1.16 2013/06/05 16:22:30CEST Raedler, Guenther (uidt9430)
 - exended interface of Validation Plot to support the class as result_type
  * added __str__(), GetWidth(), GetHeight(), GetTitle(), SetImageDataBuffer(),
  GetDrawing()
 --- Added comments ---  uidt9430 [Jun 5, 2013 4:22:31 PM CEST]
 Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
 Revision 1.15 2013/05/28 07:40:10CEST Raedler, Guenther (uidt9430)
 - fixed wrong path ussage due to pylint corrections
 --- Added comments ---  uidt9430 [May 28, 2013 7:40:10 AM CEST]
 Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
 Revision 1.14 2013/05/24 14:14:44CEST Raedler, Guenther (uidt9430)
 - use tempfile from os to store output image
 - improved x-axis handling
 - avoid div 0
 --- Added comments ---  uidt9430 [May 24, 2013 2:14:45 PM CEST]
 Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
 Revision 1.13 2013/05/17 13:08:20CEST Raedler, Guenther (uidt9430)
 - fixed gaussian calc function
 - fixed pylint warning error
 - added documentation
 --- Added comments ---  uidt9430 [May 17, 2013 1:08:20 PM CEST]
 Change Package : 183302:1 http://mks-psad:7002/im/viewissue?selection=183302
 Revision 1.12 2013/03/28 14:20:08CET Mertens, Sven (uidv7805)
 pylint: solving some W0201 (Attribute %r defined outside __init__) errors
 --- Added comments ---  uidv7805 [Mar 28, 2013 2:20:08 PM CET]
 Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
 Revision 1.11 2013/03/27 13:51:25CET Mertens, Sven (uidv7805)
 pylint: bugfixing and error reduction
 Revision 1.10 2013/03/22 09:20:51CET Mertens, Sven (uidv7805)
 last pep8 update on non-trailing white space errors
 Revision 1.9 2013/03/22 08:24:31CET Mertens, Sven (uidv7805)
 aligning bulk of files again for peping 8
 --- Added comments ---  uidv7805 [Mar 22, 2013 8:24:31 AM CET]
 Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
 Revision 1.8 2013/03/05 11:09:43CET Raedler, Guenther (uidt9430)
 - revert unexpected changes for pep8 checks
 --- Added comments ---  uidt9430 [Mar 5, 2013 11:09:44 AM CET]
 Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
 Revision 1.7 2013/03/04 13:35:01CET Raedler, Guenther (uidt9430)
 - fixed failure after pep8 updates in version 1.2
 --- Added comments ---  uidt9430 [Mar 4, 2013 1:35:02 PM CET]
 Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
 Revision 1.6 2013/03/01 09:42:49CET Hecker, Robert (heckerr)
 Updates regarding Pep8 Styleguide.
 --- Added comments ---  heckerr [Mar 1, 2013 9:42:49 AM CET]
 Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
 Revision 1.5 2013/02/28 08:12:27CET Hecker, Robert (heckerr)
 Updates regarding Pep8 StyleGuide (partly).
 --- Added comments ---  heckerr [Feb 28, 2013 8:12:28 AM CET]
 Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
 Revision 1.4 2013/02/27 17:55:13CET Hecker, Robert (heckerr)
 Removed all E000 - E200 Errors regarding Pep8.
 --- Added comments ---  heckerr [Feb 27, 2013 5:55:13 PM CET]
 Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
 Revision 1.3 2013/02/27 16:20:00CET Hecker, Robert (heckerr)
 Updates regarding Pep8 StyleGuide (partly).
 --- Added comments ---  heckerr [Feb 27, 2013 4:20:00 PM CET]
 Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
 Revision 1.2 2013/02/26 20:13:10CET Raedler, Guenther (uidt9430)
 - Updates after Pep8 Styleguides
 --- Added comments ---  uidt9430 [Feb 26, 2013 8:13:11 PM CET]
 Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
 Revision 1.1 2013/02/11 10:13:49CET Raedler, Guenther (uidt9430)
 Initial revision
 Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
 05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/img/project.pj
 ------------------------------------------------------------------------------
-- Merge from stkPlot and ETK/VPC Archive
------------------------------------------------------------------------------
 Revision 1.18 2012/11/15 10:24:58CET Hammernik-EXT, Dmitri (uidu5219)
 - added additional argument to GetPlotDataBuffer
 --- Added comments ---  uidu5219 [Nov 15, 2012 10:25:02 AM CET]
 Change Package : 163367:1 http://mks-psad:7002/im/viewissue?selection=163367
 Revision 1.17 2012/08/24 09:03:34CEST Hammernik-EXT, Dmitri (uidu5219)
 - added posibility to draw bars with overlaping
 --- Added comments ---  uidu5219 [Aug 24, 2012 9:03:34 AM CEST]
 Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
 Revision 1.16 2012/08/08 11:25:20CEST Ibrouchene-EXT, Nassim (uidt5589)
 Created new functions for plotting histograms, bar charts and normal
 distributions.
 Added GenerateFigure() method, which shall be used before using any
 plotting functions.
 Supports subplotting.
 --- Added comments ---  uidt5589 [Aug 8, 2012 11:25:20 AM CEST]
 Change Package : 151927:1 http://mks-psad:7002/im/viewissue?selection=151927
 Revision 1.15 2012/06/28 13:49:27CEST Sampat-EXT, Janani Vasumathy (uidu5218)
 - gauss plots updated
 --- Added comments ---  uidu5218 [Jun 28, 2012 1:49:27 PM CEST]
 Change Package : 97504:2 http://mks-psad:7002/im/viewissue?selection=97504
 Revision 1.14 2012/04/17 17:45:07CEST Sampat-EXT, Janani Vasumathy (uidu5218)
 - added histogram calulation and plotting
 - added gaussian plot calulation and plotting
 --- Added comments ---  uidu5218 [Apr 17, 2012 5:45:07 PM CEST]
 Change Package : 110628:1 http://mks-psad:7002/im/viewissue?selection=110628
 Revision 1.13 2011/12/07 11:00:43CET Sampat-EXT, Janani Vasumathy (uidu5218)
 - included y-axis extension
 - increases width of the bar in bar plot
 --- Added comments ---  uidu5218 [Dec 7, 2011 11:00:44 AM CET]
 Change Package : 88149:1 http://mks-psad:7002/im/viewissue?selection=88149
 Revision 1.12 2011/11/29 13:07:27CET Sampat-EXT, Janani Vasumathy (uidu5218)
 - scatter plot condition improved
 Revision 1.11 2011/11/10 15:37:58CET Raedler-EXT, Guenther (uidt9430)
 - support bar plot again
 --- Added comments ---  uidt9430 [Nov 10, 2011 3:37:59 PM CET]
 Change Package : 67780:7 http://mks-psad:7002/im/viewissue?selection=67780
 Revision 1.10 2011/11/09 12:51:51CET Raedler Guenther (uidt9430) (uidt9430)
 - fixed corrupted plots by using stk plot again
 --- Added comments ---  uidt9430 [Nov 9, 2011 12:51:51 PM CET]
 Change Package : 67780:7 http://mks-psad:7002/im/viewissue?selection=67780
 Revision 1.9 2011/11/08 08:18:58CET Raedler Guenther (uidt9430) (uidt9430)
 - introduced new derived method to support both scatter and bar plots
 - added gaussplot method (to be moved into the stationary obstacle report)
 --- Added comments ---  uidt9430 [Nov 8, 2011 8:18:59 AM CET]
 Change Package : 67780:7 http://mks-psad:7002/im/viewissue?selection=67780
 Revision 1.8 2011/11/03 13:32:29CET Ibrouchene Nassim (uidt5589) (uidt5589)
 Added the GetBarChart() function for drawing bar charts.
 --- Added comments ---  uidt5589 [Nov 3, 2011 1:32:30 PM CET]
 Change Package : 84651:1 http://mks-psad:7002/im/viewissue?selection=84651
 Revision 1.7 2011/10/27 15:36:06CEST Raedler Guenther (uidt9430) (uidt9430)
 - don't break if data is empty or None
 --- Added comments ---  uidt9430 [Oct 27, 2011 3:36:06 PM CEST]
 Change Package : 67780:7 http://mks-psad:7002/im/viewissue?selection=67780
 Revision 1.6 2011/10/13 13:55:59CEST Raedler Guenther (uidt9430) (uidt9430)
 - added line_width and line_marker option to plot
 --- Added comments ---  uidt9430 [Oct 13, 2011 1:55:59 PM CEST]
 Change Package : 67780:6 http://mks-psad:7002/im/viewissue?selection=67780
 Revision 1.5 2011/09/09 08:17:43CEST Spruck Jochen (spruckj) (spruckj)
 cast the filename for the image because filename from oracle db is unicode
 and reportlab checks filename for type string
 --- Added comments ---  spruckj [Sep 9, 2011 8:17:44 AM CEST]
 Change Package : 69027:1 http://mks-psad:7002/im/viewissue?selection=69027
 Revision 1.4 2011/09/05 15:59:50CEST Raedler Guenther (uidt9430) (uidt9430)
 -- added title for graphic plot
 --- Added comments ---  uidt9430 [Sep 5, 2011 3:59:50 PM CEST]
 Change Package : 67780:5 http://mks-psad:7002/im/viewissue?selection=67780
 Revision 1.3 2011/08/11 10:50:52CEST Raedler Guenther (uidt9430) (uidt9430)
 -- extended plot function
 -- updates to support new stk_plot revision
 --- Added comments ---  uidt9430 [Aug 11, 2011 10:50:53 AM CEST]
 Change Package : 67780:5 http://mks-psad:7002/im/viewissue?selection=67780
 Revision 1.2 2011/08/02 07:12:59CEST Raedler Guenther (uidt9430) (uidt9430)
 change axis max and min in plots
 --- Added comments ---  uidt9430 [Aug 2, 2011 7:12:59 AM CEST]
 Change Package : 67780:5 http://mks-psad:7002/im/viewissue?selection=67780
 Revision 1.1 2011/07/21 16:38:41CEST Raedler Guenther (uidt9430) (uidt9430)
 Initial revision
 Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
 05_Algorithm/EM_EnvironmentModel/05_Testing/05_Test_Environment/algo/
 em_req_test/valf_tests/vpc/project.pj
"""
