"""
framework/val/result_types.py
-----------------------

basic result type classes

**User-API Interfaces**

  - `framework.val` (complete package)
  - `BaseUnit` units used in `Signal` class
  - `Signal`   class to store, calculate, compare and plot signal values and their timestamps
  - `BinarySignal` Signal derived class with binary type, values of type [0 | 1]
  - `Histogram` providing different type of histogram plots


:org:           Continental AG
:author:        Leidenberger, Ralf

:version    :       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 09:24:01CEST $
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from numpy import array as narray, insert as ninsert, min as nmin, max as nmax, abs as nabs, mean, delete, \
    std, ones as npones, searchsorted as npsearchsorted, unique as npunique, concatenate as npconcatenate, \
    in1d as npin1d, where as npwhere, append as npappend, logical_not, fabs, isnan as npisnan, maximum as npmaximum, \
    minimum as npminimum, nanmax as npnanmax, nanmin as npnanmin, nan_to_num, logical_and as nplogical_and, \
    logical_or as nplogical_or, logical_xor as nplogical_xor, issubdtype, ndarray as npndarray, iinfo, \
    int64 as npint64, float64 as npfloat64

from sympy import Symbol
from uuid import uuid4
from sys import float_info


# - import framework modules -------------------------------------------------------------------------------------------------
# import framework.db.gbl.gbl as db_gbl
# from framework.db.gbl.gbl import COL_NAME_UNIT_ID, COL_NAME_UNIT_NAME, COL_NAME_UNIT_TYPE, COL_NAME_UNIT_LABEL
from framework.util import Logger
from framework.util.gbl_defs import GblUnits
from framework.img.plot import ValidationPlot

NPINT_MAX = iinfo(npint64).max
NPINT_MIN = iinfo(npint64).min + 1


# - classes ------------------------------------------------------------------------------------------------------------
class ValSaveLoadLevel(object):
    """ Database load and save level definitions

    set in save and load methods to define what should be processed:

        VAL_DB_LEVEL_STRUCT: only the base structure like name, description etc.
        VAL_DB_LEVEL_BASIC:  add basic results (assessment state, results and events), walk tree down to test steps,
        VAL_DB_LEVEL_INFO:   add measurement results and events,
        VAL_DB_LEVEL_ALL:    complete structure with all sub elements
    """
    VAL_DB_LEVEL_1 = int(1)  # includes the description level
    VAL_DB_LEVEL_2 = int(2)  # includes the basic results
    VAL_DB_LEVEL_3 = int(4)  # includes the assessment level
    VAL_DB_LEVEL_4 = int(8)  # includes images, detailed results

    VAL_DB_LEVEL_STRUCT = VAL_DB_LEVEL_1
    VAL_DB_LEVEL_BASIC = VAL_DB_LEVEL_STRUCT + VAL_DB_LEVEL_2
    VAL_DB_LEVEL_INFO = VAL_DB_LEVEL_BASIC + VAL_DB_LEVEL_3
    VAL_DB_LEVEL_ALL = VAL_DB_LEVEL_INFO + VAL_DB_LEVEL_4

    def __init__(self):
        pass


class BaseUnit(object):
    """ Unit class """

    UNIT_LABEL_MAP = {GblUnits.UNIT_L_MM: Symbol("mm"),
                      GblUnits.UNIT_L_M: Symbol("m"),
                      GblUnits.UNIT_L_KM: Symbol("km"),
                      GblUnits.UNIT_L_US: Symbol("us"),
                      GblUnits.UNIT_L_MS: Symbol("ms"),
                      GblUnits.UNIT_L_S: Symbol("s"),
                      GblUnits.UNIT_L_H: Symbol("h"),
                      GblUnits.UNIT_L_MPS: Symbol("m") / Symbol("s"),
                      GblUnits.UNIT_L_KMPH: Symbol("km") / Symbol("h"),
                      GblUnits.UNIT_L_DEG: Symbol("deg"),
                      GblUnits.UNIT_L_RAD: Symbol("rad"),
                      GblUnits.UNIT_L_MPS2: Symbol("m") / (Symbol("s") ** 2),
                      GblUnits.UNIT_L_DEGPS: Symbol("deg") / Symbol("s"),
                      GblUnits.UNIT_L_RADPS: Symbol("rad") / Symbol("s"),
                      GblUnits.UNIT_L_CURVE: 1 / Symbol("m"),
                      GblUnits.UNIT_L_NONE: Symbol("none"),
                      GblUnits.UNIT_L_BINARY: Symbol("0-1"),
                      GblUnits.UNIT_L_PERCENTAGE: Symbol("%"),
                      GblUnits.UNIT_M_KILOGRAM: Symbol("kg"),
                      GblUnits.UNIT_A_DECIBEL: Symbol("db")}

    def __init__(self, name, label="", dbi_gbl=None):
        self._log = Logger(self.__class__.__name__)
        self.__name = name
        if isinstance(label, basestring):
            self.__label = Symbol(label)
        else:
            self.__label = label

        self.__type = None
        self.__id = None
        if dbi_gbl is None:
            if name in self.UNIT_LABEL_MAP:
                self.__label = self.UNIT_LABEL_MAP[name]

    def __str__(self):
        """ Unit string """
        return "[" + str(self.__label) + "]"

    def __mul__(self, other):
        """ Overload * operator """
        if isinstance(other, BaseUnit):
            mult_unit = BaseUnit(self.get_name() + "_x_" + other.get_name(), self.__label * other.get_label())
        else:
            mult_unit = None
            self._log.error("Only BaseUnit multiplication is supported: %s" % str(other))
        return mult_unit

    def __pow__(self, other):
        """ Overload ^ operator """
        if isinstance(other, (int, float)):
            pow_unit = BaseUnit(self.get_name() + "_^_" + str(other), self.__label ** str(other))
        else:
            pow_unit = None
            self._log.error("Exponent must be of integer or float type: %s" % str(other))
        return pow_unit

    def __div__(self, other):
        """ Overload / operator """
        return self.__truediv__(other)

    def __truediv__(self, other):
        if isinstance(other, BaseUnit):
            div_unit = BaseUnit(str(self.get_name()) + "_/_" + str(other.get_name()),
                                str(self.__label / other.get_label()))
        else:
            div_unit = None
            self._log.error("Only BaseUnit division is supported: %s" % str(other))
        return div_unit

    def __floordiv__(self, other):
        """ Overload // operator """
        return self.__truediv__(other)

    def get_name(self):  # pylint: disable=C0103
        """ Get the unit name """
        return self.__name

    def get_label(self):  # pylint: disable=C0103
        """ Get the unit label """
        return self.__label

    def get_id(self):  # pylint: disable=C0103
        """ Get the unit id """
        return self.__id


class BaseValue(object):
    """ Base Value class supporting unit and name

    base class to store result values with name, unit and the single value.

    str() will return name and unit, '-base_val' is also supported.

    Used for other classes like ValueVector, Histogram etc.
    """
    def __init__(self, name, unit=None, value=None):
        """ Base Value initialisation

        :param name: name of the BaseValue
        :type  name: str
        :param unit: unit of stored value
        :type  unit: BaseUnit
        :param value: value of BaseValue, will be stored as float
        :type  value: Float or Integer
        """
        self._log = Logger(self.__class__.__name__)
        self._name = name
        self._unit = unit if unit else BaseUnit("none", "", None)
        try:
            self._value = float(value)
        except StandardError:
            self._value = None

    def __str__(self):
        return str(self._value) + " " + str(self._unit)

    def __neg__(self):
        """ Overload - unary operator """
        return BaseValue("-" + self.get_name(), self.get_unit(), -self.get_value())

    def db_pack(self):
        """ pack values to save in db

        DB saves either a simple result value or list of values,
        the interpretation is defined in the pack/unpack functions.

        E.g. for a ValueVector the max and min are added in the beginning of the list.

        returns either the simple value or a list with the result values (number).

        :return: single number or list of values and list of messages to be stored
        """
        return self.get_value(), []

    def get_unit(self):  # pylint: disable=C0103
        """ Get the unit string """
        return self._unit

    def get_name(self):  # pylint: disable=C0103
        """ Get the Name of the Value """
        return self._name

    def set_name(self, name):  # pylint: disable=C0103
        """ Get the Name of the Value

        :param name: name of this binary signal
        :type  name: str
        """
        self._name = name

    def get_value(self, **kwargs):  # pylint: disable=C0103
        """ Get the Value """
        return self._value


class BaseMessage(str):
    """
    class represent String data type in Result API
    """
    MAX_DB_STR_LENGTH = 1000

    def __init__(self, name, str_value):
        str.__init__(str_value)
        self._name = name

    def __new__(cls, name, str_value):
        cls._name = name
        return str.__new__(cls, str_value)

    def get_value(self):  # pylint: disable=C0103
        """
        Get value of BaseMessage
        """
        return str(self)

    def get_name(self):  # pylint: disable=C0103
        """
        Get name of BaseMessage
        """
        return self._name


class ValueVector(BaseValue):
    """ Value Vector supporting unit and name for an array of values

    during modification of the vector the allowed range of the new value is tested.

    If the vector is initiated with list containing values outside the defined range
    RemoveOutRangeValues() can be used to clean it up.
    """

    def __init__(self, name="", unit=None, value_vect=None, range_min=None, range_max=None):
        """ initialize the value array

        :param name: name of the vector
        :type  name: str
        :param unit: BaseUnit class instance
        :type  unit: BaseUnit, None
        :param value_vect: vector of values
        :type  value_vect: list, None
        :param range_min: Minimal Value
        :type  range_min: float, int, None
        :param range_max: Maximal Value
        :type  range_max: float, int, None
        """
        BaseValue.__init__(self, name, unit, None)
        if value_vect is not None:
            if type(value_vect) is list or type(value_vect) is tuple:
                self._value_vector = narray(value_vect)
            else:
                self._value_vector = value_vect
        else:
            self._value_vector = []
        if range_min is None or range_max is None:
            self._log.exception("Range min/max must be defined for ValueVector {}!"
                                " Code will break with error!".format(name))
        self._value_range_min = range_min
        self._value_range_max = range_max

    def __str__(self):
        """ Value Vector as string """
        # str(narray) does not reduce the number of digits if possible for the value, so
        #   in numpy.array a value 2.1 is stored as 2.100000000001 but treated and printed as 2.1,
        #   but this doesn't work for str(numpy.array), that will return "[2.10000000001, ...]" in this Python version
        # so we have to create the array stings by hand:
        if type(self.get_value(as_list=False)) is npndarray:
            return "[{}]".format(", ".join([str(a) for a in self.get_value(as_list=False)]))
        return str(self.get_value())

    def __len__(self):
        """ return length of the vector """
        return len(self._value_vector)

    def __getitem__(self, index):
        """ overloaded [] operator for getting """
        if index <= -len(self._value_vector) or index >= len(self._value_vector):
            raise IndexError()
        return self.get_value(index)

    # return self._value_vector[index]

    def __setitem__(self, index, value):
        """ overloaded [] operator for setting """
        self.set_value(index, value)

    # def db_pack(self):
    #     """ pack values to save in db
    #
    #     DB saves simple result value or list of values,
    #     the interpretation is defined in the pack/unpack functions.
    #
    #     For a ValueVector the max and min are added in the beginning of the list.
    #
    #     :return: list of values and list of messages (for compatibility with other classes) to be stored
    #     """
    #     val = self.get_value()
    #     values = [self.get_range_min(), self.get_range_max()]
    #     values.extend(val)
    #     return values, []

    def get_mean_value(self):  # pylint: disable=C0103
        """ Get the arithmetic mean value """
        try:
            mean_val = mean(self._value_vector)
            if npisnan(mean_val):
                self._log.error("RuntimeWarning while calculating mean of signal '%s'" % self._name)
                mean_val = None
        except (TypeError, ValueError):
            self._log.error("mean value of signal '%s' could not be calculated, e.g. signal empty" % self._name)
            mean_val = None
        return mean_val

    def get_standard_deviation(self):  # pylint: disable=C0103
        """ Get the standard deviation of the value vector"""
        try:
            std_dev = std(self._value_vector)
            if npisnan(std_dev):
                self._log.error("RuntimeWarning while calculating deviation of signal '%s'" % self._name)
                std_dev = None
        except (TypeError, ValueError) as err:
            self._log.error("deviation of signal '%s' could not be calculated, e.g. signal empty: %s"
                            % (self._name, str(err)))
            std_dev = None
        return std_dev

    def get_max_value(self):  # pylint: disable=C0103
        """ Get the max value """
        try:
            max_vcal = nmax(self._value_vector)
        except (TypeError, ValueError):
            self._log.error("max value of signal '%s' could not be calculated, e.g. signal empty" % self._name)
            max_vcal = None
        return max_vcal

    def get_min_value(self):  # pylint: disable=C0103
        """ Get the min value """
        try:
            res = nmin(self._value_vector)
        except (TypeError, ValueError):
            self._log.error("min value of signal '%s' could not be calculated, e.g. signal empty" % self._name)
            res = None
        return res

    def get_range_min(self):  # pylint: disable=C0103
        """ Get the minimal possible value for the signal """
        return self._value_range_min

    def get_range_max(self):  # pylint: disable=C0103
        """ Get the maximal possible value for the signal """
        return self._value_range_max

    def get_value(self, index=None, as_list=True):  # pylint: disable=C0103
        """ Get the vector of values

        :param index: opt index if only one value should be returned
        :type  index: int, None
        :param as_list: opt flag to convert value to list type, otherwise it will be returned as stored
        :type  as_list: bool
        """
        if index is None:
            if as_list:
                vect = list(self._value_vector)
            else:
                vect = self._value_vector
        elif index < len(self):
            vect = self._value_vector[index]
        else:
            vect = None
        return vect

    def set_value(self, index, value):  # pylint: disable=C0103
        """
        Set Value (overwrite) at given index

        Value will only be modified if the new is in defined range!

        :param index: Index position of value to be assigned
        :type index: Integer
        :param value: Value to assign
        :type value: Float or Integer
        """
        if index < len(self):
            if (value >= self._value_range_min) & (value <= self._value_range_max):
                self._value_vector[index] = value

    def insert_value(self, value, index=None):  # pylint: disable=C0103
        """
        Insert Value at the given index.

        Value will only be inserted if fitting into defined range.
        All the values after the given index will be shifted to right.

        :param value: Value to to insert
        :type value: Float, Integer or ValueVector
        :param index: if index is None then the value will be appended at the end of vector
        :type index: Integer
        :return: True if value is in range and was inserted, False otherwise
        """
        """ Insert a new Value """
        ret = False

        if index is None:
            index = len(self)
        if type(value) is ValueVector:
            value = list(value.get_value())
        else:  # type(value) is float, int or number:
            value = [value]
        values = list(filter(lambda i: self._value_range_min <= i <= self._value_range_max, value))

        if len(values) != len(value):
            self._log.error("value(s) exceeding min max value range are not inserted for vector '%s'\n"
                            "Value: %s Limits: [%s, %s]"
                            % (self.get_name(), value, self._value_range_min, self._value_range_max))
        if len(values) > 0:
            self._value_vector = ninsert(self._value_vector, index, values)
            ret = True
        return ret

    def append_value(self, value):  # pylint: disable=C0103
        """ Append a single value or an array of values

        Append Value to the vector if it fits into the defined range.

        :param value: Value to to insert
        :type value: Float, Integer or ValueVector
        :return: True if value is in range and was inserted, False otherwise
        """
        return self.insert_value(value)

    def delete_value(self, index):  # pylint: disable=C0103
        """
        Delete element at the given index

        index value could be negative as per python indexing standard

        :param index: index position
        :type index: Integer
        """
        if abs(index) < len(self._value_vector):
            self._value_vector = delete(self._value_vector, index)

    # def GetFirstValueOverThres(self, threshold=None):  # pylint: disable=C0103
    #     """
    #     Get the first value exceeding the passed threshold
    #
    #     :param threshold: threshold value, if not given then Minimum Range value will be taken as threshold
    #     :type threshold: Integer or Float
    #     :return: index of first value > threshold, None if all values are below
    #     :rtype: int or None
    #     """
    #     """ Get the first value exceeding the given threshold """
    #     if threshold is None:
    #         threshold = self.GetRangeMin()
    #     if len(self._value_vector):
    #         index = argmax(self._value_vector > threshold)
    #         first_value = self._value_vector[index]
    #     else:
    #         first_value = None
    #
    #     return first_value if first_value > threshold else None

    # def GetLastValueOverThres(self, threshold=None):  # pylint: disable=C0103
    #     """
    #     Get the last value exceeding the passed threshold
    #
    #     :param threshold: threshold value, if not given then Minimum Range value will be taken as threshold
    #     :type threshold: Integer or Float
    #     :return: index of last value > threshold, None if all values are below
    #     :rtype: int or None
    #     """
    #     # Get the first value exceeding the given threshold
    #     if threshold is None:
    #         threshold = self.GetRangeMin()
    #
    #     if len(self._value_vector):
    #         revese_vect = self._value_vector[::-1]
    #         index = argmax(revese_vect > threshold)
    #         last_value = revese_vect[index]
    #     else:
    #         last_value = None
    #
    #     return last_value if last_value > threshold else None

    # def GetLastStableSliceOverThres(self, threshold=None, bridgeable_gap=0):  # pylint: disable=C0103
    #     """ Get the last stable slice over the given threshold
    #
    #     :param threshold: opt. min value to filter, default: min of ValueVector
    #     :type  threshold: int, None
    #     :param bridgeable_gap: ?
    #     :type  bridgeable_gap: int, None
    #     """
    #     array_id = 0
    #     if threshold is None:
    #         threshold = self.GetRangeMin()
    #
    #     valindexoverthres = [i for i, val in enumerate(self._value_vector) if val > threshold]
    #
    #     if len(valindexoverthres) > 1:
    #         # reverse the index list since we look for the last stable slice over threshold
    #         valindexoverthres.reverse()
    #         for array_id, val in enumerate(valindexoverthres[:-1]):
    #             if (val - valindexoverthres[array_id + 1]) > (bridgeable_gap + 1):
    #                 break
    #         else:
    #             array_id += 1
    #         slice_ = ValueVector(self.GetName() + "_StableSlice", self.GetUnit(),
    #                              self._value_vector[valindexoverthres[array_id]:(valindexoverthres[0] + 1)],
    #                              self.GetRangeMin(),
    #                              self.GetRangeMax())
    #     elif len(valindexoverthres) == 1:
    #         slice_ = ValueVector(self.GetName() + "_StableSlice", self.GetUnit(),
    #                              [self._value_vector[valindexoverthres[0]]],
    #                              self.GetRangeMin(),
    #                              self.GetRangeMax())
    #     else:
    #         slice_ = ValueVector(self.GetName() + "_StableSlice", self.GetUnit(),
    #                              [],
    #                              self.GetRangeMin(),
    #                              self.GetRangeMax())
    #     return slice_

    # def GetHistogram(self, bins=10, norm=False):  # pylint: disable=C0103
    #     """ Get the histogram of the values
    #
    #     The size of the bins can be defined:
    #         - If bins is an int, it defines the number of equal-width bins in the given range (10, by default).
    #         - If bins is a sequence, it defines the bin edges, including the rightmost edge,
    #           allowing for non-uniform bin widths
    #
    #     :param bins: int or sequence of scalars, optional
    #     :param norm: optional flag to calculate Normalized value for histogram in Percentage
    #     """
    #     hist = Histogram(self.GetName(), self.GetUnit())
    #     hist.get_histogram(self, bins, norm=norm)
    #     return hist

    # def PlotMedian(self, out_path=None, box_size=0.5, whisker_ratio=1.5, outlier_symbol='+',  # pylint: disable=C0103
    #                bnotched_box=False, y_axis_ext=None):
    #     """ Plot the median of the value vector
    #
    #     return a ValidationPlot with the vertical box plot of the value vector
    #
    #     usage example:
    #
    #     .. code-block:: python
    #
    #         value = [7.0, 9.62, 9.76, 10.32, 10.68, 10.96, 11.46, 12.20, 8.5]
    #         vv = ValueVector("graph heading", BaseUnit(GblUnits.UNIT_L_M, label="m"),
    #                          value, min(value), max(value))
    #         median_plot, _ = vv.PlotMedian(out_path=r"testPlotMedian.png",
    #                                        y_axis_ext=[min(value) - 1, max(value) + 2])
    #
    #     When setting the range for the y-axis add some space to clearly show the values at the boarder.
    #     The returned value can directly be added to the pdf report.
    #
    #     For more detailed description of the parameters see function header of matplotlib.axes.boxplot()
    #     called by `framework.img.plot.get_median_plot`.
    #
    #     :param out_path: path/file name if the should be saved
    #     :type  out_path: str
    #     :param box_size: width of the box
    #     :type  box_size: int
    #     :param whisker_ratio: plot whisker ratio
    #     :type whisker_ratio: int
    #     :param outlier_symbol: symbol to plot values outside the quartile
    #     :type  outlier_symbol: str
    #     :param bnotched_box: flag to control notch for box plot
    #     :type  bnotched_box: bool
    #     :param y_axis_ext: additional extension to y-axis typically [min,max] value of the y axis
    #     :type  y_axis_ext: list
    #     """
    #     if y_axis_ext is None:
    #         y_axis_ext = [self.GetMinValue(), self.GetMaxValue()]
    #     plotter = ValidationPlot(out_path)
    #     axes = plotter.generate_figure(fig_width=2, fig_height=5, show_grid=False)
    #
    #     plotter.get_median_plot(axes, self.get_value(), x_axis_name="", y_axis_name=str(self.GetUnit()),
    #                             title=self.GetName(), xticks_labels=None,
    #                             y_axis_ext=y_axis_ext, box_width=box_size,
    #                             whisker_box_ratio=whisker_ratio, notched_box=bnotched_box,
    #                             outlier_sym=outlier_symbol, vert_orientation=True)
    #
    #     return plotter.get_drawing_from_buffer(plotter.get_plot_data_buffer(),
    #                                            "Median_" + self.GetName().replace(' ', '_') + "_%s" % str(uuid4()),
    #                                            width=100, height=300), plotter

    # def RemoveOutRangeValues(self):  # pylint: disable=C0103
    #     """
    #     Remove all the value which are outside the min and max range
    #     """
    #     if not (self.GetMinValue() >= self._value_range_min and self.GetMaxValue() <= self._value_range_max):
    #         bool_vector1 = self._value_vector >= self._value_range_min
    #         bool_vector2 = self._value_vector <= self._value_range_max
    #         return self.RemoveValues(bool_vector1 * bool_vector2)

    # def RemoveValues(self, bool_list):  # pylint: disable=C0103
    #     """
    #     Remove Values selected valuesspecified by boo_list i.e. values with False entry at the index
    #     :param bool_list:
    #     :type bool_list:
    #     """
    #     """
    #     Remove all the values which located at the same indexwhich are outside the min and max range
    #     """
    #     ret = False
    #     if len(self._value_vector) == len(bool_list):
    #         self._value_vector = self._value_vector[bool_list]
    #         ret = True
    #     return ret


class NumpySignal(ValueVector):
    """
    **NumpySignal Class is a Signal class which uses Numpy Methods**

    base class for `Signal`, find more detailed docu there

    """

    def __init__(self, name, unit=None, value_vect=None, ts_vect=None, range_min=0, range_max=0, default_value=None):
        """ Initialize the  Signal

        :param name: name of the vector
        :type  name: str
        :param unit: BaseUnit class instance or unit name
        :type  unit: BaseUnit, None
        :param value_vect: vector of values
        :type  value_vect: list, int, None
        :param ts_vect: timestamp vector
        :type  ts_vect: list, None
        :param range_min: Minimal Value
        :type  range_min: int, float
        :param range_max: Maximal Value
        :type  range_max: int, float
        :param default_value: value used to create signals where no value is provided (e.g. in ChangeTimeRange)
        :type  default_value: int, float
        """
        if not (isinstance(unit, BaseUnit)):
            unit = BaseUnit(unit)

        if default_value is None:
            self._default_value = range_min
        else:
            if default_value > range_max:
                self._default_value = range_max
            elif default_value < range_min:
                self._default_value = range_min
            else:
                self._default_value = default_value

        if isinstance(value_vect, (float, int)):
            ValueVector.__init__(self, name, unit, [value_vect] * len(ts_vect), range_min, range_max)

        elif isinstance(value_vect, BaseValue):
            ValueVector.__init__(self, name, unit, [value_vect.get_value()] * len(ts_vect), range_min, range_max)

        elif len(value_vect) == len(ts_vect):
            if len(value_vect) > 0:
                ValueVector.__init__(self, name, unit, value_vect, range_min, range_max)
            else:
                # trick numpy to create an empty value_vect array storing planned type
                # as 'array([], <type>) does not work, the empty array still has no dtype defined
                ValueVector.__init__(self, name, unit, [self._default_value], range_min, range_max)
                self.delete_value(0)
        elif len(value_vect) < len(ts_vect):
            ValueVector.__init__(self, name, unit, value_vect, range_min, range_max)
            self._log.error("Each timestamp shall have a value: signal '%s' is reduced to %i values"
                            % (name, len(value_vect)))
            ts_vect = ts_vect[:len(value_vect)]
        else:  # len(value_vect) > len(ts_vect):
            ValueVector.__init__(self, name, unit, value_vect[:len(ts_vect)], range_min, range_max)
            self._log.error("Each value shall have a timestamp: signal '%s' is reduced to %i values"
                            % (name, len(ts_vect)))
        self._ts_vect = narray(ts_vect)

        # correct ts/values regarding defined type of default value:
        if issubdtype(type(self.get_default_value()), float) and issubdtype(self.get_value(as_list=False).dtype, int):
            # no info lost, just store it with warning:
            self._log.warning("values of signal '%s' stored as float following the type of default value %s" %
                              (self._name, str(self._default_value)))
        elif issubdtype(type(self.get_default_value()), int) and issubdtype(self.get_value(as_list=False).dtype, float):
            # info of some values lost, drop them out to prevent errors
            self._log.error("some float values of signal '%s' are dropped because default value %s is defined as int" %
                            (self._name, str(self._default_value)))
            int_vals = narray(value_vect[:len(self.get_value())], dtype=int)
            valid_idcs = npin1d(value_vect, int_vals)
            ValueVector.__init__(self, name, unit, int_vals[valid_idcs], range_min, range_max)
            self._ts_vect = self._ts_vect[valid_idcs]

    def __str__(self):
        """ Print snap shot vector
        """
        return str(zip(self.get_timestamps(), self.get_value()))

    def db_pack(self):
        """ pack values to save in db

        DB saves simple result value or list of values,
        the interpretation is defined in the pack/unpack functions.

        For a NumpySignal the max and min are added in the beginning of the list.

        :return: list of values to be stored
        """
        val = self.get_value()
        values = [self.get_range_min(), self.get_range_max()]
        values.extend(val)
        return values, []

    def get_timestamps(self, as_list=False):  # pylint: disable=C0103
        """
        Get the Timestamp range of the signal

        :param as_list: opt flag to convert value to list type, otherwise it will be returned as stored
        :type  as_list: bool
        :return: Times of the signal
        :rtype : numpy array
        """
        if as_list:
            return self._ts_vect.tolist()
        return self._ts_vect

    def get_start_timestamp(self):  # pylint: disable=C0103
        """ Get the Start Timestamp """
        if len(self._ts_vect) > 0:
            time_stamp = nmin(self._ts_vect)
        else:
            time_stamp = 0
        return time_stamp

    def __lt__(self, other):
        """ Override the Equal '<' operator """
        return self.__comparision(other, "lt")

    def __le__(self, other):
        """ Override the Equal '<=' operator """
        return self.__comparision(other, "le")

    def __eq__(self, other):
        """ Override the Equal '==' operator """
        return self.__comparision(other, "eq")

    def __ne__(self, other):
        """ Override the not Equal '!=' operator """
        return self.__comparision(other, "ne")

    def __ge__(self, other):
        """ Override the Greater or Equal '>=' operator """
        return self.__comparision(other, "ge")

    def __gt__(self, other):
        """ Override the Greater Than '>' operator """
        return self.__comparision(other, "gt")

    def get_value(self, index=None, as_list=False):  # pylint: disable=C0103
        return super(NumpySignal, self).get_value(index, as_list=as_list)

    def __comparision(self, other, comparitor):
        """ Generic function to override Override '<' '<='  '==' '!=' '>=' '>' max() operator """

        if type(other) is BaseValue:
            other = other.get_value()

        if isinstance(other, (int, float)):
            other = NumpySignal(str(other), self.get_unit(), other,
                                self.get_timestamps(), other, other)

        if type(other) in (NumpySignal, Signal):
            combined_ts, common_value_indxs = self._get_common_timestamps(other)
            out_ts = combined_ts[common_value_indxs]
            # common values of self and other:
            this_val = self.get_value(as_list=False)[npin1d(self._ts_vect, other._ts_vect)]
            other_val = other.get_value(as_list=False)[npin1d(other._ts_vect, self._ts_vect)]

            value = None
            if comparitor == 'lt':
                value = this_val < other_val
            elif comparitor == 'le':
                value = this_val <= other_val
            elif comparitor == 'eq':
                value = this_val == other_val
            elif comparitor == 'ne':
                value = this_val != other_val
            elif comparitor == 'ge':
                value = this_val >= other_val
            elif comparitor == 'gt':
                value = this_val > other_val

            sig_out = BinarySignal(self.get_name() + " %s " % comparitor + other.get_name(), int(value), out_ts)
        else:
            self._log.error("Comparison are only possible with type BaseValue, Signal, Int or float: %s" % str(other))
            sig_out = None

        return sig_out

    def _get_combined_timestamps(self, other):  # pylint: disable=C0103
        """ Create a combine timestamp vector of the two signals"""

        time_stamp = npconcatenate([self.get_timestamps(), other.get_timestamps()])
        return npunique(time_stamp)

    def _get_common_timestamps(self, other):  # pylint: disable=C0103
        """ Create the combined timestamp vector of the two signals and a list of indices for common timestamps

        :param other: signal to combine with self
        :type  other: NumpySignal
        :return: list of combined timestamps, list with indices of common timestamps
        """
        combined_ts = self._get_combined_timestamps(other)

        other_ts = other.get_timestamps()
        this_ts = self.get_timestamps()

        common_values_ts_bool = npin1d(combined_ts, this_ts) * npin1d(combined_ts, other_ts)
        return combined_ts, npwhere(common_values_ts_bool)[0]

    def __cmp__(self, _):
        self._log.error("__cmp__ is deprecated it should not be used")

    def get_value_at_timestamp(self, ts):  # pylint: disable=C0103
        """ Return the value at the given timestamp

        :param ts: time stamp of value
        :type  ts: int
        """
        idx = self.__get_index_from_timestamp(ts)
        if idx < len(self) and ts == self._ts_vect[idx]:
            val = self[idx]
        else:
            val = None
        return val

    def __get_index_from_timestamp(self, ts):  # pylint: disable=C0103
        """ Get the array index where the given timestamp exists or can be inserted
        :param ts: time stamp of value
        :type  ts: int"""
        return npsearchsorted(self._ts_vect, [ts])

    def get_end_timestamp(self):  # pylint: disable=C0103
        """ Get the end TimeStamp """
        if len(self._ts_vect) > 0:
            time_stamp = nmax(self._ts_vect)
        else:
            time_stamp = 0
        return time_stamp

    def get_default_value(self):  # pylint: disable=C0103
        """ Get Default Value"""
        return self._default_value

    def change_time_in_sec(self, timestamp_origin=0):  # pylint: disable=C0103
        """
        Change time values from microsecond to second
        """
        timestamps = self.get_timestamps()
        timestamps_in_sec = []
        time_base2sec = 1000000.0
        for timestamp in timestamps:
            timestamps_in_sec.append(round((timestamp - timestamp_origin) / time_base2sec, 2))
        sig = NumpySignal(self.get_name(), self.get_unit(), self.get_value(), timestamps_in_sec,
                          self.get_range_min(), self.get_range_max())
        return sig

    # def RemoveOutRangeValues(self):  # pylint: disable=C0103
    #     """
    #     Remove all the value which are outside the min and max range
    #     """
    #     sig_values = self.GetValue(as_list=False)
    #     sig_min_value = self.GetMinValue()
    #     sig_max_value = self.GetMaxValue()
    #     sig_min_range_value = self.GetRangeMin()
    #     sig_max_range_value = self.GetRangeMax()
    #
    #     if not (sig_min_value >= sig_min_range_value and sig_max_value <= sig_max_range_value):
    #         bool_vector1 = sig_values >= sig_min_range_value
    #         bool_vector2 = sig_values <= sig_max_range_value
    #         bool_vector3 = bool_vector1 * bool_vector2
    #         del bool_vector1
    #         del bool_vector2
    #         self.RemoveValues(bool_vector3)
    #         self._ts_vect = self._ts_vect[bool_vector3]

    def __arithmatic(self, other, operator):
        if type(other) is BaseValue:
            other = other.get_value()

        if isinstance(other, (int, float)):
            other = NumpySignal(str(other), self.get_unit(), other, self.get_timestamps(), other, other)

        if isinstance(other, Signal):
            other = other.signal_to_numpy()

        if type(other) is NumpySignal:
            combined_ts, common_value_indxs = self._get_common_timestamps(other)
            out_ts = combined_ts[common_value_indxs]
            # common values of self and other:
            this_val = self.get_value(as_list=False)[npin1d(self._ts_vect, other._ts_vect)]
            other_val = other.get_value(as_list=False)[npin1d(other._ts_vect, self._ts_vect)]

            sig_name = self.get_name() + ("_%s_" % operator) + other.get_name()

            if operator == "*":
                limits = [self.get_range_max() * other.get_range_max(), self.get_range_min() * other.get_range_max(),
                          self.get_range_max() * other.get_range_min(), self.get_range_min() * other.get_range_min()]
                value = this_val * other_val
            elif operator == "-":
                limits = [self.get_range_max() - other.get_range_max(), self.get_range_min() - other.get_range_max(),
                          self.get_range_max() - other.get_range_min(), self.get_range_min() - other.get_range_min()]
                value = this_val - other_val
            elif operator == "+":
                limits = [self.get_range_max() + other.get_range_max(), self.get_range_min() + other.get_range_max(),
                          self.get_range_max() + other.get_range_min(), self.get_range_min() + other.get_range_min()]
                value = this_val + other_val
            elif operator == "max":
                # installed propagating NaN: returning NaN if one value is Nan
                limits = [self.get_range_max(), other.get_range_max(), self.get_range_min(), other.get_range_min()]
                sig_name = "max(%s,%s)" % (self.get_name(), other.get_name())
                value = npmaximum(this_val, other_val)
            elif operator == "min":
                # installed propagating NaN: returning NaN if one value is Nan
                limits = [nmin([self.get_range_max(), other.get_range_max()]),
                          nmin([self.get_range_min(), other.get_range_min()])]
                sig_name = "min(%s,%s)" % (self.get_name(), other.get_name())
                value = npminimum(this_val, other_val)
            else:
                return None
            # numpy.isnan does not handle too big number, therefore we turn long int to float
            nlimits = []
            for l in limits:
                if isinstance(l, (long, int)) and (l > NPINT_MAX or l < NPINT_MIN):
                    l = npfloat64(l)
                nlimits.append(l)
            new_max = npnanmax(nlimits)
            new_min = npnanmin(nlimits)

            sig_out = NumpySignal(sig_name, self.get_unit(), value, out_ts, new_min, new_max)
            return sig_out

    def __add__(self, other):
        return self.__arithmatic(other, "+")

    def __sub__(self, other):
        return self.__arithmatic(other, "-")

    def __mul__(self, other):
        return self.__arithmatic(other, "*")

    def __div__(self, other):
        """ Override the Div '/' operator """
        return self.__truediv__(other)

    def __truediv__(self, other):
        """ Override the Div '/' operator """
        if isinstance(other, Signal):
            other = other.signal_to_numpy()
        if isinstance(other, NumpySignal):
            # recalculate the limits
            limits = []
            if (other.get_range_min() < 0) and (other.get_range_max() > 0):
                other_abs = NumpySignal.abs(other)
                min_div = other_abs.when(other_abs > 0).get_min_value()
                limits.extend([self.get_range_max() / other.get_range_max(), self.get_range_min() /
                               other.get_range_max()])
                limits.extend([self.get_range_max() / other.get_range_min(), self.get_range_min() /
                               other.get_range_min()])
                limits.extend([self.get_range_max() / min_div, self.get_range_min() / min_div])
                limits.extend([-self.get_range_max() / min_div, -self.get_range_min() / min_div])
            elif (other.get_range_min() > 0) or (other.get_range_max() < 0):
                limits.extend([self.get_range_max() / other.get_range_max(), self.get_range_min() /
                               other.get_range_max()])
                limits.extend([self.get_range_max() / other.get_range_min(), self.get_range_min() /
                               other.get_range_min()])
            else:
                limits.extend([float_info.max, -float_info.max])

            new_max = npnanmax(limits)
            new_min = npnanmin(limits)

            sig_out = NumpySignal("(" + self.get_name() + "_/_" + other.get_name() + ")",
                                  self.get_unit() / other.get_unit(),
                                  [], [], new_min, new_max)
            timestamp_out, timestamp_index = self._get_common_timestamps(other)
            for time in timestamp_out[timestamp_index]:
                val1 = self.get_value_at_timestamp(time)
                val2 = other.get_value_at_timestamp(time)
                if nabs(val2) > 0:
                    sig_out.add_timestamp_and_value(time, val1 / val2)
        elif isinstance(other, BaseValue):
            if other.get_value() > 0:
                sig_out = NumpySignal("(" + self.get_name() + "_/_" + str(other.get_value()) + ")",
                                      self.get_unit() / other.get_unit(),
                                      [], [], self.get_range_min() / other.get_value(),
                                      self.get_range_max() / other.get_value())
                for time in self.get_timestamps():
                    sig_out.add_timestamp_and_value(time, self.get_value_at_timestamp(time) / other.get_value())
            elif other.get_value() < 0:
                sig_out = NumpySignal("(" + self.get_name() + "_/_" + str(other.get_value()) + ")",
                                      self.get_unit() / other.get_unit(),
                                      [], [], self.get_range_max() / other.get_value(),
                                      self.get_range_min() / other.get_value())
                for time in self.get_timestamps():
                    sig_out.add_timestamp_and_value(time, self.get_value_at_timestamp(time) / other.get_value())
            else:
                sig_out = None
                self._log.error("Division by 0 is not defined: %s" %
                                "_/_".join([self.get_name(), str(other.get_value())]))
        elif isinstance(other, (int, float)):
            if other > 0:
                sig_out = NumpySignal("(" + self.get_name() + "_/_" + str(other) + ")", self.get_unit(), [], [],
                                      self.get_range_min() / other, self.get_range_max() / other)
                for time in self.get_timestamps():
                    sig_out.add_timestamp_and_value(time, self.get_value_at_timestamp(time) / other)
            elif other < 0:
                sig_out = NumpySignal("(" + self.get_name() + "_/_" + str(other) + ")", self.get_unit(), [], [],
                                      self.get_range_max() / other, self.get_range_min() / other)
                for time in self.get_timestamps():
                    sig_out.add_timestamp_and_value(time, self.get_value_at_timestamp(time) / other)
            else:
                sig_out = None
                self._log.error("Division by 0 is not defined: %s" % "_/_".join([self.get_name(), str(other)]))
        else:
            sig_out = None
            self._log.error("Division is only possible with BaseValue, NumpySignal, Int or float: signal '%s'" %
                            "_/_".join([self.get_name(), str(other)]))
        return sig_out

    def __floordiv__(self, other):
        """ Override the integer Div '//' operator """
        if isinstance(other, Signal):
            other = other.signal_to_numpy()

        if isinstance(other, NumpySignal):
            # recalculate the limits
            limits = []
            if (other.get_range_min() > 0) or (other.get_range_max() < 0):
                limits.extend([self.get_range_max() // other.get_range_max(),
                               self.get_range_min() // other.get_range_max()])
                limits.extend([self.get_range_max() // other.get_range_min(),
                               self.get_range_min() // other.get_range_min()])
            else:
                # other range spreads over '0', so we possibly get infinite values
                limits.extend([float_info.max, -float_info.max])

            # get new range, if limits contains 'np.inf' translate it to float max
            new_max = nan_to_num(npnanmax(limits))
            new_min = nan_to_num(npnanmin(limits))

            sig_out = NumpySignal("(" + self.get_name() + "_//_" + other.get_name() + ")",
                                  self.get_unit() // other.get_unit(), [], [], int(new_min), int(new_max),
                                  self.get_default_value())
            timestamp_out, timestamp_index = self._get_common_timestamps(other)
            for time in timestamp_out[timestamp_index]:
                val1 = self.get_value_at_timestamp(time)
                val2 = other.get_value_at_timestamp(time)
                if nabs(val2) > 0:
                    sig_out.add_timestamp_and_value(time, val1 // val2)
                else:
                    self._log.error("Division by 0 skipped for '%s' at timestamp %f" % (sig_out.get_name(), time))
        elif isinstance(other, BaseValue):
            if other.get_value() > 0:
                sig_out = NumpySignal("(" + self.get_name() + "_//_" + str(other.get_value()) + ")",
                                      self.get_unit() // other.get_unit(), [], [],
                                      self.get_range_min() // other.get_value(),
                                      self.get_range_max() // other.get_value())
                for time in self.get_timestamps():
                    sig_out.add_timestamp_and_value(time, self.get_value_at_timestamp(time) // other.get_value())
            elif other.get_value() < 0:
                sig_out = NumpySignal("(" + self.get_name() + "_//_" + str(other.get_value()) + ")",
                                      self.get_unit() // other.get_unit(), [], [],
                                      self.get_range_max() // other.get_value(),
                                      self.get_range_min() // other.get_value())
                for time in self.get_timestamps():
                    sig_out.add_timestamp_and_value(time, self.get_value_at_timestamp(time) // other.get_value())
            else:
                sig_out = None
                self._log.error("Division by 0 is not defined: %s" %
                                "_//_".join([self.get_name(), str(other.get_value())]))
        elif isinstance(other, (int, float)):
            if other > 0:
                sig_out = NumpySignal("(" + self.get_name() + "_//_" + str(other) + ")", self.get_unit(), [], [],
                                      self.get_range_min() // other, self.get_range_max() // other)
                for time in self.get_timestamps():
                    sig_out.add_timestamp_and_value(time, self.get_value_at_timestamp(time) // other)
            elif other < 0:
                sig_out = NumpySignal("(" + self.get_name() + "_//_" + str(other) + ")", self.get_unit(), [], [],
                                      self.get_range_max() // other, self.get_range_min() // other)
                for time in self.get_timestamps():
                    sig_out.add_timestamp_and_value(time, self.get_value_at_timestamp(time) // other)
            else:
                sig_out = None
                self._log.error("Division by 0 is not defined: %s" % "_//_".join([self.get_name(), str(other)]))
        else:
            self._log.error("Integer Division is only possible with BaseValue, NumpySignal, Int or float: signal '%s'"
                            % "_//_".join([self.get_name(), str(other)]))
            sig_out = None
        return sig_out

    def __pow__(self, other):
        """ Override the Pow '**' operator """
        if isinstance(other, ValueVector):
            self._log.error("Power/Exponent operation is not possible with an array type as exponent: signal '%s'"
                            % str(other))
            sig_out = None
        else:
            other_nam = str(other)
            if isinstance(other, BaseValue):
                other = other.get_value()
            if isinstance(other, (int, float)):
                min_range = self.get_range_min() ** other
                max_range = self.get_range_max() ** other
                new_max = npnanmax([0, min_range, max_range])
                new_min = npnanmin([0, min_range, max_range])

                sig_out = NumpySignal("(" + self.get_name() + "_**_" + other_nam + ")",
                                      self.get_unit(), self.get_value(as_list=False) ** other, self._ts_vect,
                                      new_min, new_max)
            else:
                self._log.error("Power/Exponent operation is only possible with BaseValue, Int or float: signal '%s'"
                                % str(other))
                sig_out = None
        return sig_out

    def __neg__(self):
        """ Override the negation '-' operator """
        return NumpySignal('_neg_', self.get_unit(), 0, self.get_timestamps(), self.get_range_min(),
                           self.get_range_max()).\
            __arithmatic(self, "-")

    def __pos__(self):
        """ Override the positive '+' operator """
        return self.__arithmatic(0, "+")

    def when(self, bin_sig):  # pylint: disable=C0103
        """ filter values and timestamps of the signal where given BinarySignal is '1' (similar to Numpy Where() )

        can also be used with a comparison for the BinarySignal like
        - sig = sig1.When(sig2<=3.0)

        returns NumpySignal[ val, ts when bin_sig == 1 ] for common timestamps

        :param bin_sig: filter signal
        :type  bin_sig: BinarySignal
        :return: filtered signal
        :rtype: NumpySignal
        """
        if not (isinstance(bin_sig, BinarySignal)):
            self._log.error("Condition vector should be of type BinarySignal: %s" % str(bin_sig))
            sig_out = None
        else:
            # common timestamps and values of self and bin_sig:
            combined_ts, common_value_indxs = self._get_common_timestamps(bin_sig)
            out_ts = combined_ts[common_value_indxs]
            this_val = self.get_value(as_list=False)[npin1d(self._ts_vect, bin_sig._ts_vect)]
            bin_sig_val = bin_sig.get_value(as_list=False)[npin1d(bin_sig._ts_vect, self._ts_vect)]
            sig_out = NumpySignal(self.get_name() + "_when_" + bin_sig.get_name(), self.get_unit(),
                                  this_val[npwhere(bin_sig_val)], out_ts[npwhere(bin_sig_val)],
                                  self.get_range_min(), self.get_range_max(), self.get_default_value())
        return sig_out

    def split_slice_over_thres(self, signal_threshold=None, _=0):  # pylint: disable=C0103
        """TODO"""
        sig_slice_list = []
        sig_out_temp = None

        if signal_threshold is None:
            signal_threshold = self.get_range_min()

        for time in self.get_timestamps():
            val = self.get_value_at_timestamp(time)
            if val > signal_threshold:
                if sig_out_temp is None:
                    if isinstance(self, BinarySignal):

                        sig_out_temp = BinarySignal(self.get_name(), [val], [time])
                    else:
                        sig_out_temp = NumpySignal(self.get_name(), self.get_unit(), [val], [time],
                                                   self.get_range_min(),
                                                   self.get_range_max(), self.get_default_value())
                else:
                    sig_out_temp.add_timestamp_and_value(time, self.get_value_at_timestamp(time))
            else:
                if sig_out_temp is not None:
                    sig_slice_list.append(sig_out_temp)
                    sig_out_temp = None
        else:
            if sig_out_temp is not None:
                sig_slice_list.append(sig_out_temp)
        if type(self) is NumpySignal:
            return narray(sig_slice_list)
        else:
            # this for Signal/BinarySignal class
            return sig_slice_list

    def max(self, other):  # pylint: disable=C0103
        """ Get the max value of the signals for each timestamp """

        return self.__arithmatic(other, "max")

    def min(self, other):  # pylint: disable=C0103
        """ Get the min value of the signals for each timestamp """

        return self.__arithmatic(other, "min")

    def abs(self):  # pylint: disable=C0103
        """ Get the absolute value of the signals for each timestamp """
        value = self.get_value()
        abs_value = fabs(value)
        if len(abs_value) > 0:
            min_range = nmin(abs_value)
        else:
            min_range = self.get_range_min()

        return NumpySignal("Abs(%s)" % (self.get_name()), self.get_unit(), abs_value, self.get_timestamps(),
                           min_range, fabs(self.get_range_max()))

    # def Interpolate(self, _):  # pylint: disable=C0103
    #     """ Interpolate the signal """
    #     self._log.error("Method not implemented")
    #     return []

    #
    def change_time_range(self, timestamps, default_value=None):  # pylint: disable=C0103
        """ Change the time range on which the signal is defined.

        The passed timestamps will be stored as new timestamp list of the signal,
        at timestamps where values exist in the original signal these are copied to the new,
        original values without timestamps are dropped.

        At new timestamps where the signal is not defined a default value will be stored.
        If no default value is passed the initiated default value (or range min if not defined there) is used.

        Example:

        .. code-block:: python

            val1 = [1, 2, 3.1, 4.5]
            sig1 = Signal("sig1", unit, val1, [100, 200, 300, 400], 0.0, 10.0)
            sig = sig1.ChangeTimeRange([90, 200, 201, 400, 500], 10.0)
            sig.GetValue()
            >> {list}[10., 2., 10., 4.5, 10.]

        The default value has to be of similar type (int, float) as the values of the original signal.
        To prevent changing values to a different type
        (e.g. as int but original values as float, based on the default value)
        an error is logged in case of different types and ''None'' will be returned.

        The default value has to be in the allowed range of the original signal.

        :param timestamps: new timestamps
        :type  timestamps: list
        :param default_value: optional value to set at new timestamps, default as defined during initialisation
        :type  default_value: int, float, number
        :return: signal with new timestamps
        """
        tmp_u = BaseUnit(GblUnits.UNIT_L_US, "")
        tmp_ts = ValueVector("", tmp_u, timestamps, 0.0, 0.0)
        if not default_value:
            default_value = self._default_value

        if not issubdtype(self.get_value(as_list=False).dtype, type(default_value)):
            self._log.error("ChangeTimeRange type of default value differs from signal value type for signal '%s'"
                            % self._name)
            sig_out = None
        elif not self.get_range_min() <= default_value <= self.get_range_max():
            self._log.error("ChangeTimeRange default value is not in the range of signal '%s'"
                            % self._name)
            sig_out = None

        elif timestamps is None:
            sig_out = None
        elif tmp_ts == ValueVector("", tmp_u, self.get_timestamps(), 0.0, 0.0):
            sig_out = self
        else:
            if isinstance(self, BinarySignal):
                sig_out = BinarySignal(self.get_name(), [default_value] * len(timestamps), timestamps)
            else:
                sig_out = NumpySignal(self.get_name(), self.get_unit(), [default_value] * len(timestamps),
                                      timestamps, self.get_range_min(), self.get_range_max())
            for timestamp in timestamps:
                val = self.get_value_at_timestamp(timestamp)
                if val is not None:
                    sig_out.set_value_at_timestamp(timestamp, val)

        return sig_out

    def get_subset_for_time_interval(self, startts=None, stopts=None):  # pylint: disable=C0103
        """ Returns a Signal for a selected time interval between start and stop time slot

        - if startts is larger than largest value of the time slot list, returning None
        - if stopts is less than smallest value of the time slot list, returning None

        Similar function as `ChangeTimeRange` with difference that for last one can also single values
        can be returned. Here always all values between given ts are returned.

        :param startts: start time slot
        :param stopts: stop time slot
        :return: subset of signal
        :rtype:  NumpySignal
        """

        time_slots = self._ts_vect
        values = self.get_value(as_list=False)

        max_idx = len(time_slots) - 1
        if (startts is None or startts <= time_slots[0]) and (stopts is None or stopts >= time_slots[max_idx]):
            return self

        if startts is None or startts < time_slots[0]:
            startts = time_slots[0]
        elif startts > time_slots[-1]:
            self._log.error("startts (%d) is larger than max(time slots) in signal '%s', returning None" %
                            (startts, self._name))
            return None

        if (stopts is None) or (stopts > time_slots[max_idx]):
            stopts = time_slots[max_idx]
        elif stopts < time_slots[0]:
            self._log.error("stopts (%d) is less than min(time slots) in signal '%s', returning None" %
                            (stopts, self._name))
            return None

        if startts is not None and startts >= time_slots[0]:
            bool_vector1 = time_slots >= startts
        else:
            bool_vector1 = npones(len(time_slots), dtype=bool)

        if stopts is not None and stopts <= time_slots[max_idx]:
            bool_vector2 = time_slots <= stopts
        else:
            bool_vector2 = npones(len(time_slots), dtype=bool)
        time_slots = time_slots[bool_vector1 * bool_vector2]

        values = values[bool_vector1 * bool_vector2]

        ret_signal = NumpySignal(self.get_name(), self.get_unit(), values,
                                 time_slots, self.get_min_value(), self.get_max_value())
        return ret_signal

    def add_timestamp_and_value(self, timestamp, value):  # pylint: disable=C0103
        """ Add a new timestamp and the corresponding value to the signal

        A signal is sorted based on the timestamp array, so this method inserts the new timestamp and value
        at the appropriate location.

        Values at already existing timestamps are not changed, use ``SetValueAtTimestamp`` to replace values

        **If the signal is empty the first value added with this method defines the type of the array!**

        Meaning:

        - if the first value is an integer following floats will cause an TypeError,
        - if the first value is a float following integers will be stored as float

        :param timestamp: timestamp to insert the new value to
        :type  timestamp: int, float
        :param value:     value to insert
        :return: True if passed, False on error
        """
        ret = False
        if isinstance(value, (list, tuple,)):
            self._log.error("value list added to signal '%s' for same timestamp" % self._name)
        elif not issubdtype(self.get_value(as_list=False).dtype, type(value)):
            if issubdtype(type(value), int):
                self._log.warning("Added int value %s stored as float to signal '%s'" %
                                  (str(value), self._name))
                timestamp = [timestamp]
                value = [value]
            else:
                self._log.error("Value %s not added to signal '%s', no int type!" % (str(value), self._name))
                value = []
        else:
            timestamp = [timestamp]
            value = [value]

        for id_ in range(len(value)):
            idx = self.__get_index_from_timestamp(timestamp[id_])

            if idx < len(self):
                if float(self._ts_vect[idx]) != float(timestamp[id_]):
                    if self.insert_value(value[id_], idx):
                        self._ts_vect = ninsert(self._ts_vect, idx, timestamp[id_])
                        ret = True
                else:
                    self._log.warning("Timestamp %s already exists for signal '%s', value not changed!" %
                                      (str(self._ts_vect[idx]), self._name))
            else:
                if self.append_value(value[id_]):
                    # np.append seems to select float type for an empty array to store all possible future values
                    # (empty arrays don't have a defined dtype), so also int time stamps are converted to float;
                    # to use the provided timestamp type of the first element we split here:
                    if len(self._ts_vect) > 0:
                        self._ts_vect = npappend(self._ts_vect, [timestamp[id_]])
                    else:
                        self._ts_vect = narray([timestamp[id_]])
                    ret = True
        return ret

    def set_value_at_timestamp(self, ts, val):  # pylint: disable=C0103
        """ Set the Value at the given timestamp """
        idx = self.__get_index_from_timestamp(ts)
        ret = False
        if idx < len(self):
            self[idx] = val
            ret = True
        else:
            if self.insert_value(val, idx):
                self._ts_vect = ninsert(self._ts_vect, ts, idx)
                ret = True
        return ret

    def numpytosignal(self):
        """
        Convert this NumpySignal instance to Signal

        :return: Return instace of Signal representing the same value
        :rtype: Signal
        """
        # NumpySignal(self.GetName(), self.GetUnit(), [self._default_value] * len(timestamps),timestamps,
        # self.GetRangeMin(), self.GetRangeMax())

        return Signal(self.get_name(), self.get_unit(), self.get_value(), self.get_timestamps(), self.get_range_min(),
                      self.get_range_max())

    def numpytobinary(self):
        """
        Convert this NumpySignal instance to BinarySignal

        :return: Return Binary signal containing values either 0 or 1
        :rtype: BinarySignal
        """
        #    All the non zero value should be consider as 1
        value_vect = narray(self.get_value(), dtype=int)

        value_vect[value_vect != BinarySignal.SIG_FALSE] = BinarySignal.SIG_TRUE
        return BinarySignal(self.get_name(), value_vect.tolist(), self.get_timestamps())

#    Commented by Zaheer. To be use as reference for extending new function with numpy
#     def GetHysteresis1(self, catch, drop):
#         """get hysteresis depending upon the catch and drop value/signal
#         """
#         # for catchval>dropval
#         def check_hysteresis_sup(catchval, dropval):
#             sigval = self.GetValueAtTimestamp(time)
#             global b_in_hysteresis
#             if (sigval is not None):
#                 if(sigval > catchval):
#                     b_in_hysteresis = True
#                     SigOut.AddTimestampAndValue(time, BinarySignal.SIG_TRUE)
#                 elif(sigval < dropval):
#                     b_in_hysteresis = False
#                     SigOut.AddTimestampAndValue(time, BinarySignal.SIG_FALSE)
#                 else:
#                     if(b_in_hysteresis == True):
#                         SigOut.AddTimestampAndValue(time, BinarySignal.SIG_TRUE)
#                     else:
#                         SigOut.AddTimestampAndValue(time, BinarySignal.SIG_FALSE)
#
#         # for catchval<dropval
#         def check_hysteresis_inf(catchval, dropval):
#             global b_in_hysteresis
#             sigval = self.GetValueAtTimestamp(time)
#             if (sigval is not None):
#                 if(sigval < catchval):
#                     b_in_hysteresis = True
#                     SigOut.AddTimestampAndValue(time, BinarySignal.SIG_TRUE)
#                 elif(sigval > dropval):
#                     b_in_hysteresis = False
#                     SigOut.AddTimestampAndValue(time, BinarySignal.SIG_FALSE)
#                 else:
#                     if(b_in_hysteresis == True):
#                         SigOut.AddTimestampAndValue(time, BinarySignal.SIG_TRUE)
#                     else:
#                         SigOut.AddTimestampAndValue(time, BinarySignal.SIG_FALSE)
#
#         b_in_hysteresis = False
#         global b_in_hysteresis
#         if((isinstance(catch, Signal)) and (isinstance(drop, Signal))):
#             SigOut = BinarySignal(self.GetName() + "_in_hysteresis_between_" + catch.GetName() + "_and_" +
#                                   drop.GetName(), [], [])
#             TimestampsOut1 = self._GetCombinedTimestamps(catch)
#             TimestampsOut2 = self._GetCombinedTimestamps(drop)
#             TimestampsOut = list(set(TimestampsOut1).intersection(set(TimestampsOut2)))
#             for time in TimestampsOut:
#                 catch_value = catch.GetValueAtTimestamp(time)
#                 drop_value = drop.GetValueAtTimestamp(time)
#                 if ((catch_value is not None) and (drop_value is not None)):
#                     if(b_in_hysteresis == False):
#                         if catch_value > drop_value:
#                             check_hysteresis_sup(catch_value, drop_value)
#                         elif drop_value < catch_value:
#                             check_hysteresis_inf(catch_value, drop_value)
#
#         elif((isinstance(catch, BaseValue)) and (isinstance(drop, BaseValue))):
#             SigOut = BinarySignal(self.GetName(), [], [])
#             catch_value = catch.GetValue()
#             drop_value = drop.GetValue()
#             if catch_value > drop_value:
#                 for time in self.GetTimestamps():
#                     check_hysteresis_sup(catch_value, drop_value)
#             elif drop_value < catch_value:
#                 for time in self.GetTimestamps():
#                     check_hysteresis_inf(catch_value, drop_value)
#             else:
#                 SigOut = self > catch_value
#         elif((isinstance(catch, (int, float))) and (isinstance(drop, (int, float)))):
#             SigOut = BinarySignal(self.GetName() + "_in_hysteresis_between_" + str(catch) + "_and_" +
#                                   str(drop), [], [])
#             if catch > drop:
#                 for time in self.GetTimestamps():
#                     check_hysteresis_sup(catch, drop)
#             elif drop < catch:
#                 for time in self.GetTimestamps():
#                     check_hysteresis_inf(catch, drop)
#             else:
#                 SigOut = self > catch
#         else:
#             self._log.error("Comparison are only possible with type BaseValue, Signal, Int or float: %s" %
#                             str(catch) + "_and_" + str(drop))
#             SigOut = None
#         return SigOut


class Signal(NumpySignal):
    """ **Signal class**

    Stores numpy arrays for values and time stamps and provides functions and methods
    to calculate and compare signals with others, single values or BaseValue types if reasonable.

    Signals also store range for values and the `BaseUnit` of the values.

    A default value defines the type of all values to be stored (see below).
    It is used for time stamps where no value is given (as in `ChangeTimeRange`).
    If no default value is defined the min range will be used as default value.

    **Values that are out of given range are not stored.**

    example 1:

    ..  code-block:: python

        values = [1, 2, 3.0, 4.0]
        ts = [10100, 10200, 10300, 10400]

        sig1 = Signal("distx", BaseUnit(GblUnits.UNIT_L_M, "", self.__gbldb), values, ts, 0.0, 5.0)

        sig1
        >> {Signal}[(10100, 1.0), (10200, 2.0), (10300, 3.0), (10400, 4.0)]
        sig1.GetValue()
        >> {list}[1., 2., 3., 4.]
        sig1.GetValue(as_list=False)
        >> {np.array}[ 1.  2.  3.  4.]


    **arithmetic**

    Arithmetic functions are defined to work on each value of the signal, expressions of two signals are executed
    only for common timestamps.
    If the timestamps are not matching a shorter signal than the operators will be returned, signal values where
    only one signal is defined are dropped for the result.

    The units are calculated similar, so the resulting signal will provide the correct unit (e.g. m/s).

    **comparison**

    Comparison functions work on each value of the signals returning a ``BinarySignal``
    with [0, 1] values for False/True comparison of the respective value.

    Comparison of two signals is executed only for common timestamps.
    If the timestamps are not matching a shorter signal than the operators will be returned, signal values where
    only one signal is defined are dropped for the result.

    example 2:

    .. code-block:: python

        # compare two signals [1.0, 1.1, 2.0,      3.0, 4.0]
        #                     [1.1,      2.1, 2.0, 3.0, 3.9, 5.1]
        sig = sig1 >= sig2
        sig.GetValue()
        >> {list}[0.0, 0.0, 1.0, 1.0]

    For more examples see module test `testSignal_Compare
    <http://uud296ag:8080/view/STK_checkin_tests/job/STK_NightlyBuild/ws/05_Testing/05_Test_Environment/moduletest/\
    test_val/test_result_types.py>`_.

    **type of value and timestamps in array**

    The type of the value is selected based of the type of the default value
    (numpy uses C arrays with well defined types). Extending the signal will adapt the types of new values
    to the values of the array if possible (int -> float),
    otherwise an error is logged and the value will be dropped.

    see example 1:

    - the min range (no default value) given as float numpy defines an array with float64 values.
    - All timestamps are defined as int so the numpy array uses int32 types.

    When initialising an empty signal the optional default value defines the types of values to be stored.
    If no default value is passed the min range is used as default value and that is defining the type
    of values to be stored in the signal later.

    example 3:

    .. code-block:: python

        empty_sig = Signal("test_empty_sig", BaseUnit(GblUnits.UNIT_L_M, "", self.__gbldb), [], [], 0, 3)
        empty_sig.AddTimestampAndValue(105, 2.1)
        >> ERROR: Value 2.1 not added to signal 'test_empty_sig', no int type!

    Range is defined with integer values, so signal values are expected to be integers.
    Adding value '2.1' fails with the logged error as it is of float type.


    """

    def __init__(self, name, unit, value_vect, ts_vect, range_min, range_max, default_value=None):
        """ Initialize the  Signal

        The default value type defines the type of values to be stored.
        If no default value is defined min range is used for it.

        Values with different type are not stored if info is lost, otherwise a warning will be logged.
        If no default value is given the min or max range are used as default value.


        :param name: name of the vector
        :type  name: str
        :param unit: BaseUnit class instance or unit name
        :type  unit: BaseUnit
        :param value_vect: vector of values
        :type  value_vect: list
        :param ts_vect: timestamp vector
        :type  ts_vect: list
        :param range_min: Minimal Value
        :type  range_min: int, float
        :param range_max: Maximal Value
        :type  range_max: int, float
        :param default_value: value used to create signals where no value is provided (e.g. in ChangeTimeRange)
        :type  default_value: int, float
        """
        super(Signal, self).__init__(name, unit, value_vect, ts_vect, range_min, range_max, default_value)

    def __str__(self):
        """ Print snap shot vector
        """
        return str(zip(self.get_timestamps(), self.get_value()))

    def get_timestamps(self, as_list=True):  # pylint: disable=C0103
        """
        Get the Timestamp range of the signal

        :return : Timestamps of the signal
        :type   : list or numpy array based on as_list
        """
        if as_list:
            return super(Signal, self).get_timestamps().tolist()
        return super(Signal, self).get_timestamps()

    def signal_to_numpy(self):
        """
        returns a NumpySignal type of the signal.

        :return: Numpy signal
        :rtype: NumpySignal
        """
        return NumpySignal(self.get_name(), self.get_unit(), self.get_value(), super(Signal, self).get_timestamps(),
                           self.get_range_min(), self.get_range_max())

    def __add__(self, other):
        sig = super(Signal, self).__add__(other)
        return sig.numpytosignal()

    def __sub__(self, other):
        sig = super(Signal, self).__sub__(other)
        return sig.numpytosignal()

    def __mul__(self, other):
        sig = super(Signal, self).__mul__(other)
        return sig.numpytosignal()

    def __div__(self, other):
        sig = super(Signal, self).__div__(other)
        return sig.numpytosignal() if sig is not None else None

    def __truediv__(self, other):
        sig = super(Signal, self).__truediv__(other)
        return sig.numpytosignal() if sig is not None else None

    def __floordiv__(self, other):
        sig = super(Signal, self).__floordiv__(other)
        return sig.numpytosignal() if sig is not None else None

    def __pow__(self, other):
        sig = super(Signal, self).__pow__(other)
        if sig is not None:
            return sig.numpytosignal()
        else:
            return None

    def __neg__(self):
        sig = super(Signal, self).__neg__()
        return sig.numpytosignal()

    def __pos__(self):
        sig = super(Signal, self).__pos__()
        return sig.numpytosignal()

    def split_slice_over_thres(self, signal_threshold=None, _=0):  # pylint: disable=C0103
        """TODO"""
        return super(Signal, self).split_slice_over_thres(signal_threshold=signal_threshold)

    def change_time_range(self, timestamps, default_value=None):  # pylint: disable=C0103
        """TODO"""
        sig = super(Signal, self).change_time_range(timestamps, default_value)
        return sig.numpytosignal() if sig else None

    def abs(self):  # pylint: disable=C0103
        """TODO"""
        return super(Signal, self).abs().numpytosignal()

    def max(self, other):  # pylint: disable=C0103
        """TODO"""
        return super(Signal, self).max(other).numpytosignal()

    def min(self, other):  # pylint: disable=C0103
        """TODO"""
        return super(Signal, self).min(other).numpytosignal()

    def get_subset_for_time_interval(self, startts=None, stopts=None):  # pylint: disable=C0103
        """TODO"""
        sig = super(Signal, self).get_subset_for_time_interval(startts, stopts)
        if sig is not None:
            return sig.numpytosignal()
        else:
            return None

    def get_value(self, index=None, as_list=True):  # pylint: disable=C0103
        """TODO"""
        return super(Signal, self).get_value(index, as_list=as_list)

    def change_time_in_sec(self, timestamp_origin=0):  # pylint: disable=C0103
        """TODO"""
        return super(Signal, self).change_time_in_sec(timestamp_origin).numpytosignal()

    def when(self, bin_sig):  # pylint: disable=C0103
        """ filter values and timestamps of the signal with given BinarySignal (similar to Numpy Where() )

        returns Signal[ val, ts when bin_sig == 1 ]

        :param bin_sig: filter signal
        :type  bin_sig: BinarySignal
        :return: filtered signal
        :rtype: Signal
        """
        sig = super(Signal, self).when(bin_sig)
        return sig.numpytosignal()


class BinarySignal(Signal):
    """ Value Vector taking binary values (0 or 1)

    """
    SIG_TRUE = 1
    SIG_FALSE = 0

    def __init__(self, name, value_vect, ts_vect, dbi_gbl=None):
        """ Initialize the binary value vector

        :param name: name of the vector
        :param value_vect: vector of values (list)
        :param ts_vect: Timestamp vector
        :param dbi_gbl: Database interface to GBL Subscheme (optional)
        """
        unit = BaseUnit(GblUnits.UNIT_L_BINARY, dbi_gbl=dbi_gbl)
        Signal.__init__(self, name, unit, value_vect, ts_vect, self.SIG_FALSE, self.SIG_TRUE)

    def __logical(self, other, operator):

        if isinstance(other, BinarySignal):
            combined_ts, common_value_indxs = self._get_common_timestamps(other)
            out_ts = combined_ts[common_value_indxs]
            # common values of self and other:
            this_val = self.get_value(as_list=False)[npin1d(self.get_timestamps(), other.get_timestamps())]
            other_val = other.get_value(as_list=False)[npin1d(other.get_timestamps(), self.get_timestamps())]

            if operator == 'and':
                value = nplogical_and(this_val, other_val)
            elif operator == 'or':
                value = nplogical_or(this_val, other_val)
            elif operator == 'xor':
                value = nplogical_xor(this_val, other_val)
            else:
                return None

            sig_out = BinarySignal(self.get_name() + "_%s_" % operator + other.get_name(), value.astype(int), out_ts)
            return sig_out

    def __and__(self, other):
        return self.__logical(other, "and")

    def __or__(self, other):
        return self.__logical(other, "or")

    def __xor__(self, other):
        return self.__logical(other, "xor")

    def __invert__(self):
        """ Override the inversion  '~' operator """

        val_vect = narray(logical_not(self.get_value(as_list=False)), dtype=int)
        sig_out = BinarySignal("not_" + self.get_name(), val_vect, self.get_timestamps())
        return sig_out

    def __lt__(self, _):
        """ Override the Less Than '<' operator """
        self._log.error("Operation is not possible for BinarySignals")

    def __le__(self, _):
        """ Override the Less or Equal '<=' operator """
        self._log.error("Operation is not possible for BinarySignals")

    def __eq__(self, _):
        """ Override the Equal '==' operator """
        self._log.error("Operation is not possible for BinarySignals")

    def __ne__(self, _):
        self._log.error("Operation is not possible for BinarySignals")

    def __ge__(self, _):
        """ Override the Greater or Equal '>=' operator """
        self._log.error("Operation is not possible for BinarySignals")

    def __gt__(self, _):
        """ Override the Greater Than '>' operator """
        self._log.error("Operation is not possible for BinarySignals")

    def __add__(self, _):
        """ Override the Add '+' operator """
        self._log.error("Operation is not possible for BinarySignals")

    def __sub__(self, _):
        """ Override the Sub '-' operator """
        self._log.error("Operation is not possible for BinarySignals")

    def __mul__(self, _):
        """ Override the Mul '*' operator """
        self._log.error("Operation is not possible for BinarySignals")

    def __div__(self, _):
        """ Override the Div '/' operator """
        self._log.error("Operation is not possible for BinarySignals")

    def __truediv__(self, _):
        """ Override the Div '/' operator """
        self._log.error("Operation is not possible for BinarySignals")

    def __floordiv__(self, _):
        """ Override the integer Div '//' operator """
        self._log.error("Operation is not possible for BinarySignals")

    def __pow__(self, _):
        """ Override the Pow '^' operator """
        self._log.error("Operation is not possible for BinarySignals")

    def __neg__(self):
        """ Override the negation '-' operator """
        self._log.error("Operation is not possible for BinarySignals")

    def __pos__(self):
        """ Override the positive '+' operator """
        self._log.error("Operation is not possible for BinarySignals")

    def max(self, _):  # pylint: disable=C0103
        """ Get the max value of the signals for each timestamp """
        self._log.error("Operation is not possible for BinarySignals")

    def min(self, _):  # pylint: disable=C0103
        """ Get the min value of the signals for each timestamp """
        self._log.error("Operation is not possible for BinarySignals")

    def change_time_range(self, timestamps, default_value=None):  # pylint: disable=C0103
        """Change the time range on which the signal is defined.

        see main docu: `NumpySignal.ChangeTimeRange`

        Be aware that default value for BinarySignal can only be 0 or 1.
        For other values this method returns ``None``.

        :param timestamps: new timestamps
        :type  timestamps: list
        :param default_value: optional value to set at new timestamps [0|1], default as defined during initialisation
        :type  default_value: int
        :return: signal with new timestamps
        """
        if not default_value or default_value in [0, 1]:
            sig = super(BinarySignal, self).change_time_range(timestamps, default_value)
            return sig.numpytobinary() if sig else sig
        else:
            self._log.error("ChangeTimeRange for binary signal '%s' not allowed with value %s (only 0 or 1)"
                            % (self._name, str(default_value)))
        return None

    def when(self, bin_sig):  # pylint: disable=C0103
        """ filter values and timestamps of the signal with given BinarySignal (similar to Numpy Where() )

        returns Signal[ val, ts when bin_sig == 1 ]

        :param bin_sig: filter signal
        :type  bin_sig: BinarySignal
        :return: filtered signal
        :rtype: BinarySignal
        """
        sig = super(BinarySignal, self).when(bin_sig)
        return sig.numpytobinary()


class PercentageSignal(Signal):
    """ Value Vector taking percentage values in the range 0..100

        Unit instance must be given

        ---> THIS Method is intended to be removed. Please clarify status with Guenther Raedler <----
    """
    def __init__(self, name, value_vect, ts_vect, dbi_gbl=None):
        """ Initialize the percentage value vector

        :param name: name of the vector
        :param value_vect: vector of values (list)
        :param ts_vect: Timestamp vector
        :param dbi_gbl: Database interface to GBL Subscheme (optional)
        """
        unit = BaseUnit(GblUnits.UNIT_L_PERCENTAGE, dbi_gbl=dbi_gbl)
        Signal.__init__(self, name, unit, value_vect, ts_vect, 0, 100)

    def __neg__(self):
        """ Override the negation '-' operator """
        self._log.error("Operation is not possible for PercentageSignals")

    def __pos__(self):
        """ Override the positive '+' operator """
        self._log.error("Operation is not possible for PercentageSignals")


class Histogram(BaseValue):
    """
    Validation Result Histogram class

    The class contains calculated histogram values including the binnings used. The
    original values are not stored within the class.

    The config is stored and saved as internal list of parameters for the given type of histogram.
    The parameters can be given as str values in a list, if list is not complete default settings are used:

        .. code-block:: python

            vv = ValueVector("hist_in", unit, values_a, 0.0, 5.0)
            hist2 = vv.GetHistogram(values_ts)
            config = ['pie', 'pie hist title','True','10', '7', 'True']
            config.extend(['label 1', 'label 2', 'label 3', 'label 4')
            hist2.SetHistogramConfig(config)


    supported histogram types and their config:

        - bar chart (default): options see `PlotHistogramBarChart`
            0 type: 'bar'
            # title
            # label_rotation
            # label_size
            # relative_bar_size
            # bar_orientation
            # label_list

        - pie chart: options see `PlotHistogramPieChart`
            0 type: 'pie'
            # title
            # legend_flag
            # labels_fontsize
            # legend_fontsize
            # optimised_view
            # label_names...

        - distribution chart: options see `PlotHistogramDistribution`
            0 type: 'pie'
            # title
            # draw_lines
            # write_text
            # x_label
            # y_label
            # legend
    """
    def __init__(self, name, unit, value_vect=None, bins=10):
        """ Constructor of the histogram class

        :param name: name of histogram
        :type  name: str
        :param unit: unit of values
        :type  unit: BaseUnit
        :param value_vect: list of values to display, optional, can be set later
        :type  value_vect: list
        :param bins: bin counts used for x-axis
        :type  bins: int
        """
        BaseValue.__init__(self, name, unit, 0.0)
        self._hist_values = []
        self._max = None
        self._min = None
        self._step = None
        self._hist = None
        self._pattern = None
        self._sigma = None
        self._mean = None
        self._plotcfg = None  # ("bar",bar_orientiation)  ("pie", optimize_flag)  ("distribution",drawl_line_flag)
        # self._labels = None  # [(labelx1 labely1), (labelx2 labely2), (labelx2 labely2)........]
        if value_vect is not None:
            self.get_histogram(value_vect, bins)

    def __str__(self):
        """Value Vector as sting
        """
        return str(self.get_value())

    def db_pack(self):
        """ pack values to save in db

        DB saves simple result value or list of values,
        the interpretation is defined in the pack/unpack functions.

        For a Histogram the tuples are unziped for the list and the config is stored as a list of strings.

        :return: list of values and list of messages to be stored
        """
        values = []
        for xyz in self.get_value():
            values.append(xyz[0])
            values.append(xyz[1])

        messages = self.get_histogram_config()
        return values, messages

    # def db_unpack(self, values=None, messages=None):
    #     """ unpack values from db to internal structure
    #
    #     DB saves only simple value or list of values,
    #     the interpretation is defined in the pack/unpack functions.
    #
    #     For a Histogram the tuples are unzip from the list and the config is taken from the messages.
    #
    #     :param values: list of values as stored in db
    #     :param messages: list of str as stored in db
    #     """
    #     if values is None:
    #         values = []
    #     if messages is None:
    #         messages = []
    #     itr = iter(values)
    #     self.set_value(zip(itr, itr))
    #     hist_cfg = []
    #     for i in range(len(messages)):
    #         hist_cfg.append(messages[i])
    #     if len(hist_cfg):
    #         self.SetHistogramConfig(hist_cfg)
    #     self._unit = BaseUnit(self._unit)

    def get_value(self, index=None, **kwargs):  # pylint: disable=C0103
        """Get the vector of values

        retrns the list of values or just the one at given index

        :param index: index of value to return
        :type  index: int, None
        """
        if index is None:
            return self._hist_values
        else:
            if index < len(self._hist_values):
                return self._hist_values[index]
            else:
                return None

    def get_pattern(self, index=None):  # pylint: disable=C0103
        """Get the x-axis value i.e. bins

        returns list of x-axis values or just the one at given index

        :param index: index of value to return
        :type  index: int, None
        """
        if index is None:
            return self._pattern
        else:
            if index < len(self._pattern):
                return self._pattern[index]
            else:
                return None

    def set_histogram_config(self, info):  # pylint: disable=C0103
        """ This is function which used internally by ResultAPI to load plot configuration
            for report generator to use Generic PlotHisogram()

            :param info: list of configuration parameters
            :type  info: list(str)
        """
        self._plotcfg = info

    def get_histogram_config(self):  # pylint: disable=C0103
        """ This is function which used internally by ResultAPI to save plot configuration
        """
        return self._plotcfg

    def get_hist(self, index=None):  # pylint: disable=C0103
        """Get the y-axis value

        if no index is given return complete list of y-axis values, otherwise the requested y value

        :param index: optional index of Histogram list to return
        :type  index: int, None
        """
        if index is None:
            return self._hist
        else:
            if index < len(self._hist):
                return self._hist[index]
            else:
                return None

    def set_value(self, hist_values):  # pylint: disable=C0103
        """
        Set the vector of histogram value tuples

        this method is used in load method of ValResult for Histogram

        :param hist_values: list of values to draw in Histogram
        :type  hist_values: list, None
        """
        if hist_values is not None:
            self._pattern = []
            self._hist = []
            self._hist_values = hist_values
            self._pattern, self._hist = list(zip(*hist_values[2:])[0]), list(zip(*hist_values[2:-1])[1])
            self._max = hist_values[0][0]
            self._min = hist_values[0][1]
            self._sigma = hist_values[1][0]
            self._mean = hist_values[1][1]

    @staticmethod
    def __calc_histogram(values, bins):  # pylint: disable=C0103
        """ Calculate the Histogram values
        """
        try:
            bins = int(bins)
            step = (max(values) - min(values)) / bins
            pattern = [(min(values) + (x + 1) * step) for x in range(bins)]
        except ZeroDivisionError:
            pattern = bins

        hist = [0] * (len(pattern) - 1)

        for val in values:
            if val >= pattern[0]:
                for ibin, ibinthres in enumerate(pattern[1:]):
                    if val < ibinthres:
                        hist[ibin] += 1
                        break

        return pattern, hist

    def get_histogram(self, value_vect, bins, update=True, norm=False):  # pylint: disable=C0103
        """Get the histogram of the values

        :param value_vect: values for histogram calculation with datatype list or ValueVector
        :param bins: list or bin counts used for x-axis
        :param update: flag to update the hist and pattern value
        :param norm: flag to calculate Normalized value for histogram in Percentage
        """
        # pattern, hist = [], []
        if isinstance(value_vect, list):
            value_vect = ValueVector("", None, value_vect, min(value_vect) - 5, max(value_vect) + 5)

        if isinstance(value_vect, ValueVector):
            pattern, hist = self.__calc_histogram(value_vect.get_value(), bins)
            total_values = len(value_vect)
        else:
            raise StandardError("Only Value Vector or List data types are allowed")

        if update:
            if norm:
                self._hist = []
                for hist_entry in hist:
                    self._hist.append(abs(float(hist_entry) / total_values) * 100)
                hist = self._hist
            else:
                self._hist = hist

            self._pattern = pattern
            self._max = value_vect.get_max_value()
            self._min = value_vect.get_min_value()
            self._sigma = value_vect.get_standard_deviation()
            self._mean = value_vect.get_mean_value()
            self._hist_values = [(self._max, self._min), (self._sigma, self._mean)]
            self._hist_values += zip(self._pattern, self._hist + [0])

        return pattern, hist

    def plot_histogram_bar_chart(self, out_path=None, label_list=None, label_rotation=None,  # pylint: disable=C0103
                                 label_size=None, relative_bar_size=0.9, bar_orientation='vertical'):
        """Plot the bar chart of the histogram values

        :param out_path: Outputpath location where image file will be created
        :type out_path: string, None
        :param label_list: list of labels representing each bar
        :type label_list: list of string, None
        :param label_rotation: rotation of label bar angle in degree
        :type label_rotation: integer, None
        :param label_size: font size of the label
        :type label_size: float, None
        :param relative_bar_size: size of the bar
        :type relative_bar_size: float
        :param bar_orientation: bar orientiation default = vertical other possible value is horizontal
        :type bar_orientation: string
        """
        plotter = ValidationPlot(out_path)
        axes = plotter.generate_figure(fig_width=5, fig_height=5, show_grid=False)

#        data_vectors = self._hist_values

        min_tick_width = min([n1 - n for n1, n in zip(self._pattern[1:], self._pattern[:-1])])
        bar_middlepos = [n + ((n1 - n) / 2.0) for n1, n in zip(self._pattern[1:], self._pattern[:-1])]
        axis_ext = [min(self._pattern), max(self._pattern)]

        if bar_orientation == 'vertical':
            plotter.get_bar_chart(axes, self._hist, xlabel=self.get_unit().get_name(), ylabel='', title=self.get_name(),
                                  xticks=self._pattern, xticks_labels=label_list, rotate=label_rotation,
                                  x_axis_ext=axis_ext, yticks=None, yticks_labels=None, y_axis_ext=None,
                                  rwidth=relative_bar_size * min_tick_width, bar_pos=bar_middlepos,
                                  bar_orientation=bar_orientation, align='center')
        else:
            plotter.get_bar_chart(axes, self._hist, xlabel='', ylabel=self.get_unit().get_name(), title=self.get_name(),
                                  xticks=None, xticks_labels=None, rotate=label_rotation, x_axis_ext=None,
                                  yticks=self._pattern, yticks_labels=label_list, y_axis_ext=axis_ext,
                                  rwidth=relative_bar_size * min_tick_width, bar_pos=bar_middlepos,
                                  bar_orientation=bar_orientation, align='center')

        args = [label_rotation, label_size, relative_bar_size, bar_orientation]
        if type(label_list) is list:
            args += label_list
        self.__prepare_histogram_config(plottype="bar", title=self.get_name(), args=args)
        # Plot the Graph into a picture and return it as a binary buffer
        return plotter.get_drawing_from_buffer(plotter.get_plot_data_buffer(),
                                               "Hist_" + self.get_name().replace(' ', '_') + "_%s" % str(uuid4()),
                                               width=300, height=300), plotter

    def plot_histogram_distribution(self, out_path=None, title=None, x_label=None, y_label=None,
                                    legend=None, draw_lines=False, write_text=None):
        """
         Plot the bar chart of the histogram values

        :param out_path: Outputpath location where image file will be created
        :type out_path: string
        :param title:    Title of the plot place at the top of the figure
        :type title:    string
        :param x_label: Label for X-Axis
        :type x_label: string
        :param y_label: Label for Y-Axis
        :type y_label: string
        :param legend: Legend for line
        :type legend: string
        :param draw_lines: Flag to draw vertical for Sigma(std deviation) and mean value
        :type draw_lines: Boolean
        :param write_text: location with respect to the height of the figure in % between 0 to 1
                            0 means at the botton 0.50 means in the middle 1 means at the top of the figure
        :type write_text: float
        """

        plotter = ValidationPlot(out_path)
        axes = plotter.generate_figure(fig_width=5, fig_height=5, show_grid=False)

        plotter.get_normal_pdf(axes, self._pattern, self._sigma, self._mean, legend=legend, draw_lines=draw_lines,
                               write_text=write_text, title=title,
                               xlabel=x_label, ylabel=y_label)
        args = [draw_lines, write_text, x_label, y_label, legend]
        self.__prepare_histogram_config(plottype="distribution", title=title, args=args)

        return plotter.get_drawing_from_buffer(plotter.get_plot_data_buffer(),
                                               "Hist_" + self.get_name().replace(' ', '_') + "_%s" % str(uuid4()),
                                               width=300, height=300), plotter

    def plot_histogram(self, output_path=None):  # pylint: disable=C0103
        """
        Generic Wrapper Function to plot Histogram for loaded data for simplified interface

        The default Histogram type is bar

        :param output_path: Output File path
        :type output_path: string
        """

        plotter = None
        if self._plotcfg is None:
            plotter = self.plot_histogram_bar_chart(out_path=output_path, label_list=None,
                                                    label_rotation=None, label_size=None,
                                                    relative_bar_size=0.9, bar_orientation='vertical')
        else:
            plottype = self._plotcfg[0]
            title = self._plotcfg[1]
            if plottype == "bar":
                label_rotation = None if self._plotcfg[2] == "None" else float(self._plotcfg[2])
                label_size = None if self._plotcfg[3] == "None" else float(self._plotcfg[3])
                relative_bar_size = float(self._plotcfg[4])
                bar_orientation = self._plotcfg[5]
                label_list = None if len(self._plotcfg[6:]) == 0 else self._plotcfg[6:]
                plotter = self.plot_histogram_bar_chart(out_path=output_path, label_list=label_list,
                                                        label_rotation=label_rotation, label_size=label_size,
                                                        relative_bar_size=relative_bar_size,
                                                        bar_orientation=bar_orientation)
            elif plottype == "distribution":
                draw_lines = True if self._plotcfg[2] == "True" else False
                write_text = None if self._plotcfg[3] == "None" else float(self._plotcfg[3])
                x_label = None if self._plotcfg[4] == "None" else self._plotcfg[4]
                y_label = None if self._plotcfg[5] == "None" else self._plotcfg[5]
                legend = None if self._plotcfg[6] == "None" else self._plotcfg[6]
                plotter = self.plot_histogram_distribution(out_path=output_path, title=title, x_label=x_label,
                                                           y_label=y_label, legend=legend,
                                                           draw_lines=draw_lines, write_text=write_text)
        return plotter

    def __prepare_histogram_config(self, plottype, title, args):  # pylint: disable=C0103
        """
        Prepare the arguement list to be store in database

        :param plottype: type of plot e.g. "bar", "pie" or "distribution"
        :type plottype: string
        :param title: title of the plot
        :type title: string
        :param args: list of argument
        :type args: list
        """
        if self._plotcfg is None:
            self._plotcfg = [plottype, title]
            str_args = []
            for arg in args:
                str_args.append(str(arg))
            self._plotcfg += str_args


"""
CHANGE LOG:
-----------
$Log: result_types.py  $
Revision 1.2 2020/03/31 09:24:01CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:34:08CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/val/project.pj
"""
