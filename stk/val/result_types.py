"""
stk/val/result_types.py
-----------------------

basic result type classes

**User-API Interfaces**

  - `stk.val` (complete package)
  - `BaseUnit` units used in `Signal` class
  - `Signal`   class to store, calculate, compare and plot signal values and their timestamps
  - `BinarySignal` Signal derived class with binary type, values of type [0 | 1]
  - `Histogram` providing different type of histogram plots


:org:           Continental AG
:author:        Guenther Raedler

:version    :       $Revision: 1.26.1.6 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/10/19 14:32:12CEST $
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from numpy import array as narray, insert as ninsert, min as nmin, max as nmax, abs as nabs, mean, delete, \
    std, argmax, ones as npones, searchsorted as npsearchsorted, unique as npunique, concatenate as npconcatenate, \
    in1d as npin1d, where as npwhere, append as npappend, logical_not, fabs, isnan as npisnan, maximum as npmaximum, \
    minimum as npminimum, nanmax as npnanmax, nanmin as npnanmin, nan_to_num, logical_and as nplogical_and, \
    logical_or as nplogical_or, logical_xor as nplogical_xor, issubdtype, number, ndarray as npndarray, iinfo, \
    int32 as npint32, int64 as npint64, float64 as npfloat64

from sympy import Symbol
from uuid import uuid4
from sys import float_info
from re import match


# - import STK modules -------------------------------------------------------------------------------------------------
from stk.db.db_common import BaseDB
import stk.db.gbl.gbl as db_gbl
from stk.db.gbl.gbl import COL_NAME_UNIT_ID, COL_NAME_UNIT_NAME, COL_NAME_UNIT_TYPE, COL_NAME_UNIT_LABEL
from stk.util import Logger
from stk.db.gbl.gbl_defs import GblUnits
from stk.img.plot import ValidationPlot

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
        if dbi_gbl is not None:
            self.Load(dbi_gbl)
        else:
            if name in self.UNIT_LABEL_MAP:
                self.__label = self.UNIT_LABEL_MAP[name]

    def __str__(self):
        """ Unit string """
        return "[" + str(self.__label) + "]"

    def __mul__(self, other):
        """ Overload * operator """
        if isinstance(other, BaseUnit):
            mult_unit = BaseUnit(self.GetName() + "_x_" + other.GetName(), self.__label * other.GetLabel())
        else:
            mult_unit = None
            self._log.error("Only BaseUnit multiplication is supported: %s" % str(other))
        return mult_unit

    def __pow__(self, other):
        """ Overload ^ operator """
        if isinstance(other, (int, float)):
            pow_unit = BaseUnit(self.GetName() + "_^_" + str(other), self.__label ** other)
        else:
            pow_unit = None
            self._log.error("Exponent must be of integer or float type: %s" % str(other))
        return pow_unit

    def __div__(self, other):
        """ Overload / operator """
        return self.__truediv__(other)

    def __truediv__(self, other):
        if isinstance(other, BaseUnit):
            div_unit = BaseUnit(str(self.GetName()) + "_/_" + str(other.GetName()),
                                str(self.__label / other.GetLabel()))
        else:
            div_unit = None
            self._log.error("Only BaseUnit division is supported: %s" % str(other))
        return div_unit

    def __floordiv__(self, other):
        """ Overload // operator """
        return self.__truediv__(other)

    def GetName(self):  # pylint: disable=C0103
        """ Get the unit name """
        return self.__name

    def GetLabel(self):  # pylint: disable=C0103
        """ Get the unit label """
        return self.__label

    def GetId(self):  # pylint: disable=C0103
        """ Get the unit id """
        return self.__id

    def Load(self, dbi_gbl, uid=None):  # pylint: disable=C0103
        """ Load the Unit class from DB """

        if not issubclass(dbi_gbl.__class__, db_gbl.BaseGblDB):
            self._log.error("GBL Database interface undefined: %s" % str(dbi_gbl))
            return False

        if uid is not None:
            unit_rec = dbi_gbl.get_unit(uid=uid)
        else:
            unit_rec = dbi_gbl.get_unit(name=self.__name)

        if unit_rec is not None:
            self.__name = unit_rec[COL_NAME_UNIT_NAME]
            self.__label = Symbol(unit_rec[COL_NAME_UNIT_LABEL])
            self.__type = unit_rec[COL_NAME_UNIT_TYPE]
            self.__id = unit_rec[COL_NAME_UNIT_ID]
            return True

        return False


class BaseValue(object):
    """ Base Value class supporting unit and name

    base class to store result values with name, unit and the single value.

    str() will return name and unit, '-base_val' is also supported.

    Used for other classes like ValueVector, Histogram etc.
    """
    def __init__(self, name, unit, value):
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
        self.__unit = unit
        try:
            self.__value = float(value)
        except StandardError:
            self.__value = None

    def __str__(self):
        return str(self.__value) + " " + str(self.__unit)

    def __neg__(self):
        """ Overload - unary operator """
        return BaseValue("-" + self.GetName(), self.GetUnit(), -self.GetValue())

    def GetUnit(self):  # pylint: disable=C0103
        """ Get the unit string """
        return self.__unit

    def GetName(self):  # pylint: disable=C0103
        """ Get the Name of the Value """
        return self._name

    def SetName(self, name):  # pylint: disable=C0103
        """ Get the Name of the Value """
        self._name = name

    def GetValue(self):  # pylint: disable=C0103
        """ Get the Value """
        return self.__value


class BaseMessage(str):
    """
    class represent String data type in Result API
    """
    MAX_DB_STR_LENGTH = 1000

    def __new__(cls, name, str_value):
        cls.__name = name
        return str.__new__(cls, str_value)

    def GetValue(self):  # pylint: disable=C0103
        """
        Get value of BaseMessage
        """
        return str(self)

    def GetName(self):  # pylint: disable=C0103
        """
        Get name of BaseMessage
        """
        return self.__name


class ValueVector(BaseValue):
    """ Value Vector supporting unit and name for an array of values

    during modification of the vector the allowed range of the new value is tested.

    If the vector is initiated with list containing values outside the defined range
    RemoveOutRangeValues() can be used to clean it up.
    """

    def __init__(self, name, unit, value_vect, range_min, range_max):
        """ initialize the value array

        :param name: name of the vector
        :type  name: str
        :param unit: BaseUnit class instance
        :type  unit: BaseUnit
        :param value_vect: vector of values
        :type  value_vect: list
        :param range_min: Minimal Value
        :type  range_min: Float or Integer
        :param range_max: Maximal Value
        :type  range_max: Float or Integer
        """
        BaseValue.__init__(self, name, unit, None)
        if value_vect is not None:
            if type(value_vect) is list or type(value_vect) is tuple:
                self.__value_vector = narray(value_vect)
            else:
                self.__value_vector = value_vect
        else:
            self.__value_vector = []
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
        if type(self.GetValue(as_list=False)) is npndarray:
            return "[{}]".format(", ".join([str(a) for a in self.GetValue(as_list=False)]))
        return str(self.GetValue())

    def __len__(self):
        """ return length of the vector """
        return len(self.__value_vector)

    def __getitem__(self, index):
        """ overloaded [] operator for getting """
        if index <= -len(self.__value_vector) or index >= len(self.__value_vector):
            raise IndexError()
        return self.GetValue(index)

    # return self.__value_vector[index]

    def __setitem__(self, index, value):
        """ overloaded [] operator for setting """
        self.SetValue(index, value)

    def GetMeanValue(self):  # pylint: disable=C0103
        """ Get the arithmetic mean value """
        try:
            mean_val = mean(self.__value_vector)
            if npisnan(mean_val):
                self._log.error("RuntimeWarning while calculating mean of signal '%s'" % self._name)
                mean_val = None
        except (TypeError, ValueError):
            self._log.error("mean value of signal '%s' could not be calculated, e.g. signal empty" % self._name)
            mean_val = None
        return mean_val

    def GetStandardDeviation(self):  # pylint: disable=C0103
        """ Get the standard deviation of the value vector"""
        try:
            std_dev = std(self.__value_vector)
            if npisnan(std_dev):
                self._log.error("RuntimeWarning while calculating deviation of signal '%s'" % self._name)
                std_dev = None
        except (TypeError, ValueError) as err:
            self._log.error("deviation of signal '%s' could not be calculated, e.g. signal empty: %s"
                            % (self._name, str(err)))
            std_dev = None
        return std_dev

    def GetMaxValue(self):  # pylint: disable=C0103
        """ Get the max value """
        try:
            max_vcal = nmax(self.__value_vector)
        except (TypeError, ValueError):
            self._log.error("max value of signal '%s' could not be calculated, e.g. signal empty" % self._name)
            max_vcal = None
        return max_vcal

    def GetMinValue(self):  # pylint: disable=C0103
        """ Get the min value """
        try:
            res = nmin(self.__value_vector)
        except (TypeError, ValueError):
            self._log.error("min value of signal '%s' could not be calculated, e.g. signal empty" % self._name)
            res = None
        return res

    def GetRangeMin(self):  # pylint: disable=C0103
        """ Get the minimal possible value for the signal """
        return self._value_range_min

    def GetRangeMax(self):  # pylint: disable=C0103
        """ Get the maximal possible value for the signal """
        return self._value_range_max

    def GetValue(self, index=None, as_list=True):  # pylint: disable=C0103
        """ Get the vector of values """
        if index is None:
            if as_list:
                vect = list(self.__value_vector)
            else:
                vect = self.__value_vector
        elif index < len(self):
            vect = self.__value_vector[index]
        else:
            vect = None
        return vect

    def SetValue(self, index, value):  # pylint: disable=C0103
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
                self.__value_vector[index] = value

    def InsertValue(self, value, index=None):  # pylint: disable=C0103
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
            value = list(value.GetValue())
        else:  # type(value) is float, int or number:
            value = [value]
        values = list(filter(lambda i: self._value_range_min <= i <= self._value_range_max, value))

        if len(values) != len(value):
            self._log.error("value(s) exceeding min max value range are not inserted for vector '%s'\n"
                            "Value: %s Limits: [%s, %s]"
                            % (self.GetName(), value, self._value_range_min, self._value_range_max))
        if len(values) > 0:
            self.__value_vector = ninsert(self.__value_vector, index, values)
            ret = True
        return ret

    def AppendValue(self, value):  # pylint: disable=C0103
        """ Append a single value or an array of values

        Append Value to the vector if it fits into the defined range.

        :param value: Value to to insert
        :type value: Float, Integer or ValueVector
        :return: True if value is in range and was inserted, False otherwise
        """
        return self.InsertValue(value)

    def DeleteValue(self, index):  # pylint: disable=C0103
        """
        Delete element at the given index

        index value could be negative as per python indexing standard

        :param index: index position
        :type index: Integer
        """
        if abs(index) < len(self.__value_vector):
            self.__value_vector = delete(self.__value_vector, index)

    def GetFirstValueOverThres(self, threshold=None):  # pylint: disable=C0103
        """
        Get the first value exceeding the passed threshold

        :param threshold: threshold value, if not given then Minimum Range value will be taken as threshold
        :type threshold: Integer or Float
        :return: index of first value > threshold, None if all values are below
        :rtype: int or None
        """
        """ Get the first value exceeding the given threshold """
        if threshold is None:
            threshold = self.GetRangeMin()
        if len(self.__value_vector):
            index = argmax(self.__value_vector > threshold)
            first_value = self.__value_vector[index]
        else:
            first_value = None

        return first_value if first_value > threshold else None

    def GetLastValueOverThres(self, threshold=None):  # pylint: disable=C0103
        """
        Get the last value exceeding the passed threshold

        :param threshold: threshold value, if not given then Minimum Range value will be taken as threshold
        :type threshold: Integer or Float
        :return: index of last value > threshold, None if all values are below
        :rtype: int or None
        """
        # Get the first value exceeding the given threshold
        if threshold is None:
            threshold = self.GetRangeMin()

        if len(self.__value_vector):
            revese_vect = self.__value_vector[::-1]
            index = argmax(revese_vect > threshold)
            last_value = revese_vect[index]
        else:
            last_value = None

        return last_value if last_value > threshold else None

    def GetLastStableSliceOverThres(self, threshold=None, bridgeable_gap=0):  # pylint: disable=C0103
        """ Get the last stable slice over the given threshold """
        array_id = 0
        if threshold is None:
            threshold = self.GetRangeMin()

        valindexoverthres = [i for i, Val in enumerate(self.__value_vector) if Val > threshold]

        if len(valindexoverthres) > 1:
            # reverse the index list since we look for the last stable slice over threshold
            valindexoverthres.reverse()
            for array_id, Val in enumerate(valindexoverthres[:-1]):
                if (Val - valindexoverthres[array_id + 1]) > (bridgeable_gap + 1):
                    break
            else:
                array_id += 1
            slice_ = ValueVector(self.GetName() + "_StableSlice", self.GetUnit(),
                                 self.__value_vector[valindexoverthres[array_id]:(valindexoverthres[0] + 1)],
                                 self.GetRangeMin(),
                                 self.GetRangeMax())
        elif len(valindexoverthres) == 1:
            slice_ = ValueVector(self.GetName() + "_StableSlice", self.GetUnit(),
                                 [self.__value_vector[valindexoverthres[0]]],
                                 self.GetRangeMin(),
                                 self.GetRangeMax())
        else:
            slice_ = ValueVector(self.GetName() + "_StableSlice", self.GetUnit(),
                                 [],
                                 self.GetRangeMin(),
                                 self.GetRangeMax())
        return slice_

    def GetHistogram(self, bins=10, norm=False):  # pylint: disable=C0103
        """ Get the histogram of the values

        The size of the bins can be defined:
            - If bins is an int, it defines the number of equal-width bins in the given range (10, by default).
            - If bins is a sequence, it defines the bin edges, including the rightmost edge,
              allowing for non-uniform bin widths

        :param bins: int or sequence of scalars, optional
        """
        hist = Histogram(self.GetName(), self.GetUnit())
        hist.GetHistogram(self, bins, norm=norm)
        return hist

    def PlotMedian(self, out_path=None, box_size=0.5, whisker_ratio=1.5, outlier_symbol='+',  # pylint: disable=C0103
                   bnotched_box=False, y_axis_ext=None):
        """ Plot the median of the value vector

        return a ValidationPlot with the vertical box plot of the value vector

        usage example:

        .. python::

            value = [7.0, 9.62, 9.76, 10.32, 10.68, 10.96, 11.46, 12.20, 8.5]
            vv = ValueVector("graph heading", BaseUnit(GblUnits.UNIT_L_M, label="m"),
                             value, min(value), max(value))
            median_plot, _ = vv.PlotMedian(out_path=r"testPlotMedian.png",
                                           y_axis_ext=[min(value) - 1, max(value) + 2])

        When setting the range for the y-axis add some space to clearly show the values at the boarder.
        The returned value can directly be added to the pdf report.

        For more detailed description of the parameters see function header of matplotlib.axes.boxplot()
        called by `stk.img.plot.get_median_plot`.

        :param out_path: path/file name if the should be saved
        :type  out_path: str
        :param box_size: width of the box
        :type  box_size: int
        :param whisker_ratio: plot whisker ratio
        :type whisker_ratio: int
        :param outlier_symbol: symbol to plot values outside the quartile
        :type  outlier_symbol: str
        :param bnotched_box: flag to control notch for box plot
        :type  bnotched_box: bool
        :param y_axis_ext: additional extension to y-axis typically [min,max] value of the y axis
        :type  y_axis_ext: list
        """
        if y_axis_ext is None:
            y_axis_ext = [self.GetMinValue(), self.GetMaxValue()]
        plotter = ValidationPlot(out_path)
        axes = plotter.generate_figure(fig_width=2, fig_height=5, show_grid=False)

        plotter.get_median_plot(axes, self.GetValue(), x_axis_name="", y_axis_name=str(self.GetUnit()),
                                title=self.GetName(), xticks_labels=None,
                                y_axis_ext=y_axis_ext, box_width=box_size,
                                whisker_box_ratio=whisker_ratio, notched_box=bnotched_box,
                                outlier_sym=outlier_symbol, vert_orientation=True)

        return plotter.get_drawing_from_buffer(plotter.get_plot_data_buffer(),
                                               "Median_" + self.GetName().replace(' ', '_') + "_%s" % str(uuid4()),
                                               width=100, height=300), plotter

    def RemoveOutRangeValues(self):  # pylint: disable=C0103
        """
        Remove all the value which are outside the min and max range
        """
        if not (self.GetMinValue() >= self._value_range_min and self.GetMaxValue() <= self._value_range_max):
            bool_vector1 = self.__value_vector >= self._value_range_min
            bool_vector2 = self.__value_vector <= self._value_range_max
            return self.RemoveValues(bool_vector1 * bool_vector2)

    def RemoveValues(self, bool_list):  # pylint: disable=C0103
        """
        Remove Values selected valuesspecified by boo_list i.e. values with False entry at the index
        :param bool_list:
        :type bool_list:
        """
        """
        Remove all the values which located at the same indexwhich are outside the min and max range
        """
        ret = False
        if len(self.__value_vector) == len(bool_list):
            self.__value_vector = self.__value_vector[bool_list]
            ret = True
        return ret


class NumpySignal(ValueVector):
    """
    **NumpySignal Class is a Signal class which uses Numpy Methods**

    base class for `Signal`, find more detailed docu there

    """

    def __init__(self, name, unit, value_vect, ts_vect, range_min, range_max, default_value=None):
        """ Initialize the  Signal

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
        if not (isinstance(unit, BaseUnit)):
            unit = BaseUnit(unit)

        if default_value is None:
            self.__default_value = range_min
        else:
            if default_value > range_max:
                self.__default_value = range_max
            elif default_value < range_min:
                self.__default_value = range_min
            else:
                self.__default_value = default_value

        if isinstance(value_vect, (float, int, number)):
            ValueVector.__init__(self, name, unit, [value_vect] * len(ts_vect), range_min, range_max)

        elif isinstance(value_vect, BaseValue):
            ValueVector.__init__(self, name, unit, [value_vect.GetValue()] * len(ts_vect), range_min, range_max)

        elif len(value_vect) == len(ts_vect):
            if len(value_vect) > 0:
                ValueVector.__init__(self, name, unit, value_vect, range_min, range_max)
            else:
                # trick numpy to create an empty value_vect array storing planned type
                # as 'array([], <type>) does not work, the empty array still has no dtype defined
                ValueVector.__init__(self, name, unit, [self.__default_value], range_min, range_max)
                self.DeleteValue(0)
        elif len(value_vect) < len(ts_vect):
            ValueVector.__init__(self, name, unit, value_vect, range_min, range_max)
            self._log.error("Each timestamp shall have a value: signal '%s' is reduced to %i values"
                            % (name, len(value_vect)))
            ts_vect = ts_vect[:len(value_vect)]
        else:  # len(value_vect) > len(ts_vect):
            ValueVector.__init__(self, name, unit, value_vect[:len(ts_vect)], range_min, range_max)
            self._log.error("Each value shall have a timestamp: signal '%s' is reduced to %i values"
                            % (name, len(ts_vect)))
        self.__ts_vect = narray(ts_vect)

        # correct ts/values regarding defined type of default value:
        if issubdtype(type(self.GetDefaultValue()), float) and issubdtype(self.GetValue(as_list=False).dtype, int):
            # no info lost, just store it with warning:
            self._log.warning("values of signal '%s' stored as float following the type of default value %s" %
                              (self._name, str(self.__default_value)))
        elif issubdtype(type(self.GetDefaultValue()), int) and issubdtype(self.GetValue(as_list=False).dtype, float):
            # info of some values lost, drop them out to prevent errors
            self._log.error("some float values of signal '%s' are dropped because default value %s is defined as int" %
                            (self._name, str(self.__default_value)))
            int_vals = narray(value_vect[:len(self.GetValue())], dtype=int)
            valid_idcs = npin1d(value_vect, int_vals)
            ValueVector.__init__(self, name, unit, int_vals[valid_idcs], range_min, range_max)
            self.__ts_vect = self.__ts_vect[valid_idcs]

    def __str__(self):
        """ Print snap shot vector
        """
        return str(zip(self.GetTimestamps(), self.GetValue()))

    def GetTimestamps(self, as_list=False):  # pylint: disable=C0103
        """
        Get the Timestamp range of the signal

        :return Times of the signal
        :return type : numpyarray
        """
        if as_list:
            return self.__ts_vect.tolist()
        return self.__ts_vect

    def GetStartTimestamp(self):  # pylint: disable=C0103
        """ Get the Start Timestamp """
        if len(self.__ts_vect) > 0:
            time_stamp = nmin(self.__ts_vect)
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

    def GetValue(self, index=None, as_list=False):  # pylint: disable=C0103
        return super(NumpySignal, self).GetValue(index, as_list=as_list)

    def __comparision(self, other, comparitor):
        """ Generic function to override Override '<' '<='  '==' '!=' '>=' '>' max() operator """

        if type(other) is BaseValue:
            other = other.GetValue()

        if isinstance(other, (int, float, number)):
            other = NumpySignal(str(other), self.GetUnit(), other,
                                self.GetTimestamps(), other, other)

        if type(other) in (NumpySignal, Signal):
            combined_ts, common_value_indxs = self._GetCommonTimestamps(other)
            out_ts = combined_ts[common_value_indxs]
            # common values of self and other:
            this_val = self.GetValue(as_list=False)[npin1d(self.__ts_vect, other.__ts_vect)]
            other_val = other.GetValue(as_list=False)[npin1d(other.__ts_vect, self.__ts_vect)]

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

            sig_out = BinarySignal(self.GetName() + " %s " % comparitor + other.GetName(), value.astype(int), out_ts)
        else:
            self._log.error("Comparison are only possible with type BaseValue, Signal, Int or float: %s" % str(other))
            sig_out = None

        return sig_out

    def _GetCombinedTimestamps(self, other):  # pylint: disable=C0103
        """ Create a combine timestamp vector of the two signals"""

        time_stamp = npconcatenate([self.GetTimestamps(), other.GetTimestamps()])
        return npunique(time_stamp)

    def _GetCommonTimestamps(self, other):  # pylint: disable=C0103
        """ Create the combined timestamp vector of the two signals and a list of indices for common timestamps

        :param other: signal to combine with self
        :type  other: NumpySignal
        :return: list of combined timestamps, list with indices of common timestamps
        """
        combined_ts = self._GetCombinedTimestamps(other)

        other_ts = other.GetTimestamps()
        this_ts = self.GetTimestamps()

        common_values_ts_bool = npin1d(combined_ts, this_ts) * npin1d(combined_ts, other_ts)
        return combined_ts, npwhere(common_values_ts_bool)[0]

    def __cmp__(self, _):
        self._log.error("__cmp__ is deprecated it should not be used")

    def GetValueAtTimestamp(self, ts):  # pylint: disable=C0103
        """ Return the value at the given timestamp """
        idx = self.__GetIndexFromTimestamp(ts)
        if idx < len(self) and ts == self.__ts_vect[idx]:
            val = self[idx]
        else:
            val = None
        return val

    def __GetIndexFromTimestamp(self, ts):  # pylint: disable=C0103
        """ Get the array index where the given timestamp exists or can be inserted"""
        return npsearchsorted(self.__ts_vect, ts)

    def GetEndTimestamp(self):  # pylint: disable=C0103
        """ Get the end TimeStamp """
        if len(self.__ts_vect) > 0:
            time_stamp = nmax(self.__ts_vect)
        else:
            time_stamp = 0
        return time_stamp

    def GetDefaultValue(self):  # pylint: disable=C0103
        """ Get Default Value"""
        return self.__default_value

    def ChangeTimeInSec(self, timestamp_origin=0):  # pylint: disable=C0103
        """
        Change time values from microsecond to second
        """
        timestamps = self.GetTimestamps()
        timestamps_in_sec = []
        time_base2sec = 1000000.0
        for timestamp in timestamps:
            timestamps_in_sec.append(round((timestamp - timestamp_origin) / time_base2sec, 2))
        sig = NumpySignal(self.GetName(), self.GetUnit(), self.GetValue(), timestamps_in_sec,
                          self.GetRangeMin(), self.GetRangeMax())
        return sig

    def RemoveOutRangeValues(self):  # pylint: disable=C0103
        """
        Remove all the value which are outside the min and max range
        """
        sig_values = self.GetValue(as_list=False)
        sig_min_value = self.GetMinValue()
        sig_max_value = self.GetMaxValue()
        sig_min_range_value = self.GetRangeMin()
        sig_max_range_value = self.GetRangeMax()

        if not (sig_min_value >= sig_min_range_value and sig_max_value <= sig_max_range_value):
            bool_vector1 = sig_values >= sig_min_range_value
            bool_vector2 = sig_values <= sig_max_range_value
            bool_vector3 = bool_vector1 * bool_vector2
            del bool_vector1
            del bool_vector2
            self.RemoveValues(bool_vector3)
            self.__ts_vect = self.__ts_vect[bool_vector3]

    def __arithmatic(self, other, operator):
        if type(other) is BaseValue:
            other = other.GetValue()

        if isinstance(other, (int, float, number)):
            other = NumpySignal(str(other), self.GetUnit(), other, self.GetTimestamps(), other, other)

        if isinstance(other, Signal):
            other = other.signal_to_numpy()

        if type(other) is NumpySignal:
            combined_ts, common_value_indxs = self._GetCommonTimestamps(other)
            out_ts = combined_ts[common_value_indxs]
            # common values of self and other:
            this_val = self.GetValue(as_list=False)[npin1d(self.__ts_vect, other.__ts_vect)]
            other_val = other.GetValue(as_list=False)[npin1d(other.__ts_vect, self.__ts_vect)]

            sig_name = self.GetName() + ("_%s_" % operator) + other.GetName()
            limits = []
            if operator == "*":
                limits = [self.GetRangeMax() * other.GetRangeMax(), self.GetRangeMin() * other.GetRangeMax(),
                          self.GetRangeMax() * other.GetRangeMin(), self.GetRangeMin() * other.GetRangeMin()]
                value = this_val * other_val
            elif operator == "-":
                limits = [self.GetRangeMax() - other.GetRangeMax(), self.GetRangeMin() - other.GetRangeMax(),
                          self.GetRangeMax() - other.GetRangeMin(), self.GetRangeMin() - other.GetRangeMin()]
                value = this_val - other_val
            elif operator == "+":
                limits = [self.GetRangeMax() + other.GetRangeMax(), self.GetRangeMin() + other.GetRangeMax(),
                          self.GetRangeMax() + other.GetRangeMin(), self.GetRangeMin() + other.GetRangeMin()]
                value = this_val + other_val
            elif operator == "max":
                # installed propagating NaN: returning NaN if one value is Nan
                limits = [self.GetRangeMax(), other.GetRangeMax(), self.GetRangeMin(), other.GetRangeMin()]
                sig_name = "max(%s,%s)" % (self.GetName(), other.GetName())
                value = npmaximum(this_val, other_val)
            elif operator == "min":
                # installed propagating NaN: returning NaN if one value is Nan
                limits = [nmin([self.GetRangeMax(), other.GetRangeMax()]),
                          nmin([self.GetRangeMin(), other.GetRangeMin()])]
                sig_name = "min(%s,%s)" % (self.GetName(), other.GetName())
                value = npminimum(this_val, other_val)
            # numpy.isnan does not handle too big number, therefore we turn long int to float
            nlimits = []
            for l in limits:
                if isinstance(l, (long, int)) and (l > NPINT_MAX or l < NPINT_MIN):
                        l = npfloat64(l)
                nlimits.append(l)
            new_max = npnanmax(nlimits)
            new_min = npnanmin(nlimits)

            sig_out = NumpySignal(sig_name, self.GetUnit(), value, out_ts, new_min, new_max)
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
            if (other.GetRangeMin() < 0) and (other.GetRangeMax() > 0):
                other_abs = NumpySignal.Abs(other)
                min_div = other_abs.When(other_abs > 0).GetMinValue()
                limits.extend([self.GetRangeMax() / other.GetRangeMax(), self.GetRangeMin() / other.GetRangeMax()])
                limits.extend([self.GetRangeMax() / other.GetRangeMin(), self.GetRangeMin() / other.GetRangeMin()])
                limits.extend([self.GetRangeMax() / min_div, self.GetRangeMin() / min_div])
                limits.extend([-self.GetRangeMax() / min_div, -self.GetRangeMin() / min_div])
            elif (other.GetRangeMin() > 0) or (other.GetRangeMax() < 0):
                limits.extend([self.GetRangeMax() / other.GetRangeMax(), self.GetRangeMin() / other.GetRangeMax()])
                limits.extend([self.GetRangeMax() / other.GetRangeMin(), self.GetRangeMin() / other.GetRangeMin()])
            else:
                limits.extend([float_info.max, -float_info.max])

            new_max = npnanmax(limits)
            new_min = npnanmin(limits)

            sig_out = NumpySignal("(" + self.GetName() + "_/_" + other.GetName() + ")",
                                  self.GetUnit() / other.GetUnit(),
                                  [], [], new_min, new_max)
            timestamp_out, timestamp_index = self._GetCommonTimestamps(other)
            for time in timestamp_out[timestamp_index]:
                val1 = self.GetValueAtTimestamp(time)
                val2 = other.GetValueAtTimestamp(time)
                if nabs(val2) > 0:
                    sig_out.AddTimestampAndValue(time, val1 / val2)
        elif isinstance(other, BaseValue):
            if other.GetValue() > 0:
                sig_out = NumpySignal("(" + self.GetName() + "_/_" + str(other.GetValue()) + ")",
                                      self.GetUnit() / other.GetUnit(),
                                      [], [], self.GetRangeMin() / other.GetValue(),
                                      self.GetRangeMax() / other.GetValue())
                for time in self.GetTimestamps():
                    sig_out.AddTimestampAndValue(time, self.GetValueAtTimestamp(time) / other.GetValue())
            elif other.GetValue() < 0:
                sig_out = NumpySignal("(" + self.GetName() + "_/_" + str(other.GetValue()) + ")",
                                      self.GetUnit() / other.GetUnit(),
                                      [], [], self.GetRangeMax() / other.GetValue(),
                                      self.GetRangeMin() / other.GetValue())
                for time in self.GetTimestamps():
                    sig_out.AddTimestampAndValue(time, self.GetValueAtTimestamp(time) / other.GetValue())
            else:
                sig_out = None
                self._log.error("Division by 0 is not defined: %s" %
                                "_/_".join([self.GetName(), str(other.GetValue())]))
        elif isinstance(other, (int, float)):
            if other > 0:
                sig_out = NumpySignal("(" + self.GetName() + "_/_" + str(other) + ")", self.GetUnit(), [], [],
                                      self.GetRangeMin() / other, self.GetRangeMax() / other)
                for time in self.GetTimestamps():
                    sig_out.AddTimestampAndValue(time, self.GetValueAtTimestamp(time) / other)
            elif other < 0:
                sig_out = NumpySignal("(" + self.GetName() + "_/_" + str(other) + ")", self.GetUnit(), [], [],
                                      self.GetRangeMax() / other, self.GetRangeMin() / other)
                for time in self.GetTimestamps():
                    sig_out.AddTimestampAndValue(time, self.GetValueAtTimestamp(time) / other)
            else:
                sig_out = None
                self._log.error("Division by 0 is not defined: %s" % "_/_".join([self.GetName(), str(other)]))
        else:
            sig_out = None
            self._log.error("Division is only possible with BaseValue, NumpySignal, Int or float: signal '%s'" %
                            "_/_".join([self.GetName(), str(other)]))
        return sig_out

    def __floordiv__(self, other):
        """ Override the integer Div '//' operator """
        if isinstance(other, Signal):
            other = other.signal_to_numpy()

        if isinstance(other, NumpySignal):
            # recalculate the limits
            limits = []
            if (other.GetRangeMin() > 0) or (other.GetRangeMax() < 0):
                limits.extend([self.GetRangeMax() // other.GetRangeMax(), self.GetRangeMin() // other.GetRangeMax()])
                limits.extend([self.GetRangeMax() // other.GetRangeMin(), self.GetRangeMin() // other.GetRangeMin()])
            else:
                # other range spreads over '0', so we possibly get infinite values
                limits.extend([float_info.max, -float_info.max])

            # get new range, if limits contains 'np.inf' translate it to float max
            new_max = nan_to_num(npnanmax(limits))
            new_min = nan_to_num(npnanmin(limits))

            sig_out = NumpySignal("(" + self.GetName() + "_//_" + other.GetName() + ")",
                                  self.GetUnit() // other.GetUnit(), [], [], int(new_min), int(new_max),
                                  self.GetDefaultValue())
            timestamp_out, timestamp_index = self._GetCommonTimestamps(other)
            for time in timestamp_out[timestamp_index]:
                val1 = self.GetValueAtTimestamp(time)
                val2 = other.GetValueAtTimestamp(time)
                if nabs(val2) > 0:
                    sig_out.AddTimestampAndValue(time, val1 // val2)
                else:
                    self._log.error("Division by 0 skipped for '%s' at timestamp %f" % (sig_out.GetName(), time))
        elif isinstance(other, BaseValue):
            if other.GetValue() > 0:
                sig_out = NumpySignal("(" + self.GetName() + "_//_" + str(other.GetValue()) + ")",
                                      self.GetUnit() // other.GetUnit(), [], [],
                                      self.GetRangeMin() // other.GetValue(),
                                      self.GetRangeMax() // other.GetValue())
                for time in self.GetTimestamps():
                    sig_out.AddTimestampAndValue(time, self.GetValueAtTimestamp(time) // other.GetValue())
            elif other.GetValue() < 0:
                sig_out = NumpySignal("(" + self.GetName() + "_//_" + str(other.GetValue()) + ")",
                                      self.GetUnit() // other.GetUnit(), [], [],
                                      self.GetRangeMax() // other.GetValue(),
                                      self.GetRangeMin() // other.GetValue())
                for time in self.GetTimestamps():
                    sig_out.AddTimestampAndValue(time, self.GetValueAtTimestamp(time) // other.GetValue())
            else:
                sig_out = None
                self._log.error("Division by 0 is not defined: %s" %
                                "_//_".join([self.GetName(), str(other.GetValue())]))
        elif isinstance(other, (int, float)):
            if other > 0:
                sig_out = NumpySignal("(" + self.GetName() + "_//_" + str(other) + ")", self.GetUnit(), [], [],
                                      self.GetRangeMin() // other, self.GetRangeMax() // other)
                for time in self.GetTimestamps():
                    sig_out.AddTimestampAndValue(time, self.GetValueAtTimestamp(time) // other)
            elif other < 0:
                sig_out = NumpySignal("(" + self.GetName() + "_//_" + str(other) + ")", self.GetUnit(), [], [],
                                      self.GetRangeMax() // other, self.GetRangeMin() // other)
                for time in self.GetTimestamps():
                    sig_out.AddTimestampAndValue(time, self.GetValueAtTimestamp(time) // other)
            else:
                sig_out = None
                self._log.error("Division by 0 is not defined: %s" % "_//_".join([self.GetName(), str(other)]))
        else:
            self._log.error("Integer Division is only possible with BaseValue, NumpySignal, Int or float: signal '%s'"
                            % "_//_".join([self.GetName(), str(other)]))
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
                other = other.GetValue()
            if isinstance(other, (int, float, number)):
                min_range = self.GetRangeMin() ** other
                max_range = self.GetRangeMax() ** other
                new_max = npnanmax([0, min_range, max_range])
                new_min = npnanmin([0, min_range, max_range])

                sig_out = NumpySignal("(" + self.GetName() + "_**_" + other_nam + ")",
                                      self.GetUnit(), self.GetValue(as_list=False) ** other, self.__ts_vect,
                                      new_min, new_max)
            else:
                self._log.error("Power/Exponent operation is only possible with BaseValue, Int or float: signal '%s'"
                                % str(other))
                sig_out = None
        return sig_out

    def __neg__(self):
        """ Override the negation '-' operator """
        return NumpySignal('_neg_', self.GetUnit(), 0, self.GetTimestamps(), self.GetRangeMin(), self.GetRangeMax()).\
            __arithmatic(self, "-")

    def __pos__(self):
        """ Override the positive '+' operator """
        return self.__arithmatic(0, "+")

    def When(self, bin_sig):  # pylint: disable=C0103
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
            combined_ts, common_value_indxs = self._GetCommonTimestamps(bin_sig)
            out_ts = combined_ts[common_value_indxs]
            this_val = self.GetValue(as_list=False)[npin1d(self.__ts_vect, bin_sig.__ts_vect)]
            bin_sig_val = bin_sig.GetValue(as_list=False)[npin1d(bin_sig.__ts_vect, self.__ts_vect)]
            sig_out = NumpySignal(self.GetName() + "_when_" + bin_sig.GetName(), self.GetUnit(),
                                  this_val[npwhere(bin_sig_val)], out_ts[npwhere(bin_sig_val)],
                                  self.GetRangeMin(), self.GetRangeMax(), self.GetDefaultValue())
        return sig_out

    def SplitSliceOverThres(self, signal_threshold=None, _=0):  # pylint: disable=C0103
        """TODO"""
        sig_slice_list = []
        sig_out_temp = None

        if signal_threshold is None:
            signal_threshold = self.GetRangeMin()

        for time in self.GetTimestamps():
            val = self.GetValueAtTimestamp(time)
            if val > signal_threshold:
                if sig_out_temp is None:
                    if isinstance(self, BinarySignal):

                        sig_out_temp = BinarySignal(self.GetName(), [val], [time])
                    else:
                        sig_out_temp = NumpySignal(self.GetName(), self.GetUnit(), [val], [time], self.GetRangeMin(),
                                                   self.GetRangeMax(), self.GetDefaultValue())
                else:
                    sig_out_temp.AddTimestampAndValue(time, self.GetValueAtTimestamp(time))
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

    def Max(self, other):  # pylint: disable=C0103
        """ Get the max value of the signals for each timestamp """

        return self.__arithmatic(other, "max")

    def Min(self, other):  # pylint: disable=C0103
        """ Get the min value of the signals for each timestamp """

        return self.__arithmatic(other, "min")

    def Abs(self):  # pylint: disable=C0103
        """ Get the absolute value of the signals for each timestamp """
        value = self.GetValue()
        abs_value = fabs(value)
        if len(abs_value) > 0:
            min_range = nmin(abs_value)
        else:
            min_range = self.GetRangeMin()

        return NumpySignal("Abs(%s)" % (self.GetName()), self.GetUnit(), abs_value, self.GetTimestamps(),
                           min_range, fabs(self.GetRangeMax()))

    def Interpolate(self, _):  # pylint: disable=C0103
        """ Interpolate the signal """
        self._log.error("Method not implemented")
        return []

    #
    def ChangeTimeRange(self, timestamps, default_value=None):  # pylint: disable=C0103
        """ Change the time range on which the signal is defined.

        The passed timestamps will be stored as new timestamp list of the signal,
        at timestamps where values exist in the original signal these are copied to the new,
        original values without timestamps are dropped.

        At new timestamps where the signal is not defined a default value will be stored.
        If no default value is passed the initiated default value (or range min if not defined there) is used.

        Example:

        .. python::

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
            default_value = self.__default_value

        if not issubdtype(self.GetValue(as_list=False).dtype, type(default_value)):
            self._log.error("ChangeTimeRange type of default value differs from signal value type for signal '%s'"
                            % self._name)
            sig_out = None
        elif not self.GetRangeMin() <= default_value <= self.GetRangeMax():
            self._log.error("ChangeTimeRange default value is not in the range of signal '%s'"
                            % self._name)
            sig_out = None

        elif timestamps is None:
            sig_out = None
        elif tmp_ts == ValueVector("", tmp_u, self.GetTimestamps(), 0.0, 0.0):
            sig_out = self
        else:
            if isinstance(self, BinarySignal):
                sig_out = BinarySignal(self.GetName(), [default_value] * len(timestamps), timestamps)
            else:
                sig_out = NumpySignal(self.GetName(), self.GetUnit(), [default_value] * len(timestamps),
                                      timestamps, self.GetRangeMin(), self.GetRangeMax())
            for timestamp in timestamps:
                val = self.GetValueAtTimestamp(timestamp)
                if val is not None:
                    sig_out.SetValueAtTimestamp(timestamp, val)

        return sig_out

    def Plot(self, signal_list=None, timestamps=None, out_path=None, bline=True,  # pylint: disable=C0103
             marker_list=None, color_list=None, linesytle_list=None):
        """ Plot the signal vector as master and add other vectors if they are compatible

        uses `stk.plot.plot` to generate and save plots, see plot details there

        :param signal_list: opt. additional signals to plot (default: none)
        :type  signal_list: list
        :param timestamps:  opt. times for which the signal should be plotted (default: all)
        :type  timestamps:  list
        :param out_path:    opt. path to plot the signal to (default: temp dir?)
        :type  out_path:    str
        :param bline:       opt. line plot (True, default) or scatter plot (False)
        :type  bline:       bool
        :param marker_list: used markers for different signals, as defined in `plot.DEF_LINE_MARKERS`
        :type  marker_list: list
        :param color_list:  colors to be used for different signals as defined in `plot.DEF_COLORS`
        :type  color_list:  list
        :param linesytle_list: line style (dotted, solid etc) for signals as defined in `plot.DEF_LINE_STYLES`
        :type  linesytle_list: list
        """
        plotter = ValidationPlot(out_path)

        # Compute the master signal to be plotted
        if timestamps is None:
            master_sig = self
        else:
            master_sig = self.ChangeTimeRange(timestamps)

        if len(master_sig.GetTimestamps()) > 0:
            data = [zip(master_sig.GetTimestamps(), master_sig.GetValue())]

            if signal_list is not None:
                title = None
                display_legend = True
                legend = [master_sig.GetName()]
                max_range = master_sig.GetRangeMax()
                min_range = master_sig.GetRangeMin()

                if timestamps is None:
                    timebase = master_sig.GetTimestamps()
                else:
                    timebase = timestamps

                for more_signal in signal_list:
                    if str(more_signal.GetUnit()) == str(master_sig.GetUnit()):
                        plot_sig = more_signal.ChangeTimeRange(timebase)
                        data.append(zip(plot_sig.GetTimestamps(), plot_sig.GetValue()))
                        legend.append(plot_sig.GetName())
                        max_range = npnanmax([max_range, plot_sig.GetRangeMax()])
                        min_range = npnanmin([min_range, plot_sig.GetRangeMin()])
                    else:
                        self._log.warning('NumpySignal ' + more_signal.GetName() +
                                          ' has different unit than master NumpySignal '
                                          'and will not be added to the plot')
            else:
                title = master_sig.GetName()
                legend = [title]
                display_legend = False
                max_range = master_sig.GetRangeMax()
                min_range = master_sig.GetRangeMin()

            # Set global Graph property
            x_ext = [master_sig.GetStartTimestamp(), master_sig.GetEndTimestamp()]
            if display_legend:
                y_ext = [min_range - 0.05 * (max_range - min_range), max_range + 0.15 * (max_range - min_range)]
            else:
                y_ext = [min_range - 0.05 * (max_range - min_range), max_range + 0.05 * (max_range - min_range)]

            # Generate the Graph
            plotter.generate_plot(data, legend, "time [s]", str(master_sig.GetUnit()), bline, display_legend,
                                  title=title, x_axis_ext=x_ext, y_axis_ext=y_ext,
                                  line_styles=linesytle_list, line_colors=color_list, line_markers=marker_list)
            # Plot the Graph into a picture and return it as a binary buffer
            return plotter.get_drawing_from_buffer(plotter.get_plot_data_buffer(),
                                                   ("Signal_" + '_'.join(legend)).replace(' ', '_')), plotter
        else:
            return None, None

    def GetHysteresis(self, catch, drop):  # pylint: disable=C0103
        """
        Get Hysteresis Signal based on given catch and drop value

        :param catch: Catch Value
        :type catch: BaseValue, int, long, float, Signal
        :param drop: Drop Value
        :type drop: BaseValue, int, long, float, Signal
        :return: Return Hysteresis signal
        :rtype: BinarySignal
        """
        if isinstance(catch, (BaseValue, int, float, long)) and isinstance(drop, (BaseValue, int, float, long)):
            if type(catch) is BaseValue:
                catch_value = catch.GetValue()
            else:
                catch_value = catch
            if type(drop) is BaseValue:
                drop_value = drop.GetValue()
            else:
                drop_value = drop

            le_catch_sig = self <= catch_value
            gt_catch_sig = self > catch_value
            btw_catch_drop = self <= catch_value and self >= drop_value
            if catch_value > drop_value:
                for i in npwhere(le_catch_sig.GetValue(as_list=False))[0]:
                    if i > 0:
                        gt_catch_sig.SetValue(i, gt_catch_sig.GetValue(i - 1) and btw_catch_drop.GetValue(i))

                sig_out = BinarySignal(self.GetName() + "_in_hysteresis_between_" +
                                       str(catch_value) + "_and_" + str(drop_value),
                                       gt_catch_sig.GetValue(),
                                       gt_catch_sig.GetTimestamps())
                return sig_out

            elif drop_value > catch_value:
                self._log.error("drop_value > catch_value is not implemented yet!")

            else:
                return self > catch_value

        elif isinstance(catch, NumpySignal) and isinstance(drop, NumpySignal):
            self._log.error("catch and drop with type Signal is not implemented yet!")

        elif isinstance(catch, Signal) and isinstance(drop, Signal):
            self._log.error("catch and drop with type Signal is not implemented yet!")
        else:
            self._log.error("Comparison are only possible with type BaseValue, Signal, " +
                            "Int or float: %s" % str(catch) + "_and_" + str(drop))
        return None

    def PlotXy(self, signal_list, out_path=None, bline=True, marker_list=None, color_list=None,  # pylint: disable=C0103
               linesytle_list=None):
        """ Plot the signal on x-axis and the signal list on the y-axis.

        Match signals using the timestamps.

        :param signal_list: opt. additional signals to plot (default: none)
        :type  signal_list: list
        :param out_path:    opt. path to plot the signal to (default: temp dir?)
        :type  out_path:    str
        :param bline:       opt. line plot (True, default) or scatter plot (False)
        :type  bline:       bool
        :param marker_list: used markers for different signals, as defined in `plot.DEF_LINE_MARKERS`
        :type  marker_list: list
        :param color_list:  colors to be used for different signals as defined in `plot.DEF_COLORS`
        :type  color_list:  list
        :param linesytle_list: line style (dotted, solid etc) for signals as defined in `plot.DEF_LINE_STYLES`
        :type  linesytle_list: list
        """
        data = []
        legend = []
        markers = []
        colors = []
        linestyles = []
        plotter = ValidationPlot(out_path)
        master_timestamps = set(self.GetTimestamps())
        common_unit_name = str(signal_list[0].GetUnit()).lower()
        min_range = []
        max_range = []
        for signal_order, plot_signal in enumerate(signal_list):
            if str(plot_signal.GetUnit()).lower() == common_unit_name:
                plot_signal_timestamps = set(plot_signal.GetTimestamps())
                common_timestamps = sorted(list(set(plot_signal_timestamps & master_timestamps)))
                if len(common_timestamps) > 0:
                    x_signal = self.ChangeTimeRange(common_timestamps)
                    y_signal = plot_signal.ChangeTimeRange(common_timestamps)
                    min_range.append(y_signal.GetRangeMin())
                    max_range.append(y_signal.GetRangeMax())
                    data.append(zip(x_signal.GetValue(), y_signal.GetValue()))
                    legend.append(y_signal.GetName())
                    if marker_list is not None:
                        markers.append(marker_list[signal_order])
                    if color_list is not None:
                        colors.append(color_list[signal_order])
                    if linesytle_list is not None:
                        linestyles.append(linesytle_list[signal_order])
            else:
                self._log.warning('All signals on y-axis shall have same units')

        if len(data) > 0:
            min_range = min(min_range)
            max_range = min(max_range)

            # Set global Graph property
            x_ext = [self.GetMinValue(), self.GetMaxValue()]
            y_ext = [min_range - 0.05 * (max_range - min_range), max_range + 0.15 * (max_range - min_range)]

            # Generate the Graph
            plotter.generate_plot(data, legend, self.GetName() + ' ' + str(self.GetUnit()),
                                  common_unit_name, bline, True,
                                  x_axis_ext=x_ext, y_axis_ext=y_ext,
                                  line_styles=linestyles, line_colors=colors, line_markers=markers)

            # Plot the Graph into a picture and return it as a binary buffer
            return plotter.get_drawing_from_buffer(plotter.get_plot_data_buffer(),
                                                   ("Signal_" + '_'.join(legend)).replace(' ', '_')), plotter
        else:
            self._log.error("Provided signals do not have a common timestamp basis")
            return None, None

    def GetSubsetForTimeInterval(self, startts=None, stopts=None):  # pylint: disable=C0103
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

        time_slots = self.__ts_vect
        values = self.GetValue(as_list=False)

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

        ret_signal = NumpySignal(self.GetName(), self.GetUnit(), values,
                                 time_slots, self.GetMinValue(), self.GetMaxValue())
        return ret_signal

    def AddTimestampAndValue(self, timestamp, value):  # pylint: disable=C0103
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
        elif not issubdtype(self.GetValue(as_list=False).dtype, type(value)):
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
            idx = self.__GetIndexFromTimestamp(timestamp[id_])

            if idx < len(self):
                if float(self.__ts_vect[idx]) != float(timestamp[id_]):
                    if self.InsertValue(value[id_], idx):
                        self.__ts_vect = ninsert(self.__ts_vect, idx, timestamp[id_])
                        ret = True
                else:
                    self._log.warning("Timestamp %s already exists for signal '%s', value not changed!" %
                                      (str(self.__ts_vect[idx]), self._name))
            else:
                if self.AppendValue(value[id_]):
                    # np.append seems to select float type for an empty array to store all possible future values
                    # (empty arrays don't have a defined dtype), so also int time stamps are converted to float;
                    # to use the provided timestamp type of the first element we split here:
                    if len(self.__ts_vect) > 0:
                        self.__ts_vect = npappend(self.__ts_vect, [timestamp[id_]])
                    else:
                        self.__ts_vect = narray([timestamp[id_]])
                    ret = True
        return ret

    def SetValueAtTimestamp(self, ts, val):  # pylint: disable=C0103
        """ Set the Value at the given timestamp """
        idx = self.__GetIndexFromTimestamp(ts)
        ret = False
        if idx < len(self):
            self[idx] = val
            ret = True
        else:
            if self.InsertValue(val, idx):
                self.__ts_vect = ninsert(self.__ts_vect, ts, idx)
                ret = True
        return ret

    def numpytosignal(self):
        """
        Convert this NumpySignal instance to Signal

        :return: Return instace of Signal representing the same value
        :rtype: Signal
        """
        # NumpySignal(self.GetName(), self.GetUnit(), [self.__default_value] * len(timestamps),timestamps,
        # self.GetRangeMin(), self.GetRangeMax())

        return Signal(self.GetName(), self.GetUnit(), self.GetValue(), self.GetTimestamps(), self.GetRangeMin(),
                      self.GetRangeMax())

    def numpytobinary(self):
        """
        Convert this NumpySignal instance to BinarySignal

        :return: Return Binary signal containing values either 0 or 1
        :rtype: BinarySignal
        """
        #    All the non zero value should be consider as 1
        value_vect = narray(self.GetValue(), dtype=int)

        value_vect[value_vect != BinarySignal.SIG_FALSE] = BinarySignal.SIG_TRUE
        return BinarySignal(self.GetName(), value_vect.tolist(), self.GetTimestamps())

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

    ..  python::

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

    .. python::

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
    otherwise an error is loggged and the value will be dropped.

    see example 1:

    - the min range (no default value) given as float numpy defines an array with float64 values.
    - All timestamps are defined as int so the numpy array uses int32 types.

    When initialising an empty signal the optional default value defines the types of values to be stored.
    If no default value is passed the min range is used as default value and that is defining the type
    of values to be stored in the signal later.

    example 3:

    .. python::

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
        return str(zip(self.GetTimestamps(), self.GetValue()))

    def GetTimestamps(self, as_list=True):  # pylint: disable=C0103
        """
        Get the Timestamp range of the signal

        :return : Timestamps of the signal
        :type   : list or numpy array based on as_list

        """
        if as_list:
            return super(Signal, self).GetTimestamps().tolist()
        return super(Signal, self).GetTimestamps()

    def signal_to_numpy(self):
        """
        returns a NumpySignal type of the signal.

        :return: Numpy signal
        :rtype: NumpySignal
        """
        return NumpySignal(self.GetName(), self.GetUnit(), self.GetValue(), super(Signal, self).GetTimestamps(),
                           self.GetRangeMin(), self.GetRangeMax())

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

    def SplitSliceOverThres(self, signal_threshold=None, _=0):  # pylint: disable=C0103
        """TODO"""
        return super(Signal, self).SplitSliceOverThres(signal_threshold=signal_threshold)

    def ChangeTimeRange(self, timestamps, default_value=None):  # pylint: disable=C0103
        """TODO"""
        sig = super(Signal, self).ChangeTimeRange(timestamps, default_value)
        return sig.numpytosignal() if sig else None

    def Abs(self):  # pylint: disable=C0103
        """TODO"""
        return super(Signal, self).Abs().numpytosignal()

    def Max(self, other):  # pylint: disable=C0103
        """TODO"""
        return super(Signal, self).Max(other).numpytosignal()

    def Min(self, other):  # pylint: disable=C0103
        """TODO"""
        return super(Signal, self).Min(other).numpytosignal()

    def GetSubsetForTimeInterval(self, startts=None, stopts=None):  # pylint: disable=C0103
        """TODO"""
        sig = super(Signal, self).GetSubsetForTimeInterval(startts, stopts)
        if sig is not None:
            return sig.numpytosignal()
        else:
            return None

    def GetValue(self, index=None, as_list=True):  # pylint: disable=C0103
        """TODO"""
        return super(Signal, self).GetValue(index, as_list=as_list)

    def ChangeTimeInSec(self, timestamp_origin=0):  # pylint: disable=C0103
        """TODO"""
        return super(Signal, self).ChangeTimeInSec(timestamp_origin).numpytosignal()

    def When(self, bin_sig):  # pylint: disable=C0103
        """ filter values and timestamps of the signal with given BinarySignal (similar to Numpy Where() )

        returns Signal[ val, ts when bin_sig == 1 ]

        :param bin_sig: filter signal
        :type  bin_sig: BinarySignal
        :return: filtered signal
        :rtype: Signal
        """
        sig = super(Signal, self).When(bin_sig)
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
            combined_ts, common_value_indxs = self._GetCommonTimestamps(other)
            out_ts = combined_ts[common_value_indxs]
            # common values of self and other:
            this_val = self.GetValue(as_list=False)[npin1d(self.GetTimestamps(), other.GetTimestamps())]
            other_val = other.GetValue(as_list=False)[npin1d(other.GetTimestamps(), self.GetTimestamps())]

            if operator == 'and':
                value = nplogical_and(this_val, other_val)
            elif operator == 'or':
                value = nplogical_or(this_val, other_val)
            elif operator == 'xor':
                value = nplogical_xor(this_val, other_val)

            sig_out = BinarySignal(self.GetName() + "_%s_" % operator + other.GetName(), value.astype(int), out_ts)

            return sig_out

    def __and__(self, other):
        return self.__logical(other, "and")

    def __or__(self, other):
        return self.__logical(other, "or")

    def __xor__(self, other):
        return self.__logical(other, "xor")

    def __invert__(self):
        """ Override the inversion  '~' operator """

        val_vect = narray(logical_not(self.GetValue(as_list=False)), dtype=int)
        sig_out = BinarySignal("not_" + self.GetName(), val_vect, self.GetTimestamps())
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

    def Max(self, _):  # pylint: disable=C0103
        """ Get the max value of the signals for each timestamp """
        self._log.error("Operation is not possible for BinarySignals")

    def Min(self, _):  # pylint: disable=C0103
        """ Get the min value of the signals for each timestamp """
        self._log.error("Operation is not possible for BinarySignals")

    def ChangeTimeRange(self, timestamps, default_value=None):  # pylint: disable=C0103
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
            sig = super(BinarySignal, self).ChangeTimeRange(timestamps, default_value)
            return sig.numpytobinary() if sig else sig
        else:
            self._log.error("ChangeTimeRange for binary signal '%s' not allowed with value %s (only 0 or 1)"
                            % (self._name, str(default_value)))
        return None

    def When(self, bin_sig):  # pylint: disable=C0103
        """ filter values and timestamps of the signal with given BinarySignal (similar to Numpy Where() )

        returns Signal[ val, ts when bin_sig == 1 ]

        :param bin_sig: filter signal
        :type  bin_sig: BinarySignal
        :return: filtered signal
        :rtype: BinarySignal
        """
        sig = super(BinarySignal, self).When(bin_sig)
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
    """ Validation Result Histogram class

        The class contains calculated histogram values including the binnings used. The
        original values are not stored within the class
    """
    def __init__(self, name, unit, value_vect=None, bins=10):
        """ Constructor of the histogram class """
        BaseValue.__init__(self, name, unit, 0.0)
        self.__hist_values = []
        self.__max = None
        self.__min = None
        self.__step = None
        self.__hist = None
        self.__pattern = None
        self.__sigma = None
        self.__mean = None
        self.__plotcfg = None  # ("bar",bar_orientiation)  ("pie", optimize_flag)  ("distribution",drawl_line_flag)
        # self.__labels = None  # [(labelx1 labely1), (labelx2 labely2), (labelx2 labely2)........]
        if value_vect is not None:
            self.GetHistogram(value_vect, bins)

    def __str__(self):
        """Value Vector as sting
        """
        return str(self.GetValue())

    def GetValue(self, index=None):  # pylint: disable=C0103
        """Get the vector of values
        """
        if index is None:
            return self.__hist_values
        else:
            if index < len(self.__hist_values):
                return self.__hist_values[index]
            else:
                return None

    def GetPattern(self, index=None):  # pylint: disable=C0103
        """Get the x-axis value i.e. bins
        """
        if index is None:
            return self.__pattern
        else:
            if index < len(self.__pattern):
                return self.__pattern[index]
            else:
                return None

    def SetHistogramConfig(self, info):  # pylint: disable=C0103
        """ This is function which used internally by ResultAPI to load plot configuration
            for report generator to use Generic PlotHisogram()
        """
        self.__plotcfg = info

    def GetHistogramConfig(self):  # pylint: disable=C0103
        """ This is function which used internally by ResultAPI to save plot configuration
        """
        return self.__plotcfg

    def GetHist(self, index=None):  # pylint: disable=C0103
        """Get the y-axis value
        """
        if index is None:
            return self.__hist
        else:
            if index < len(self.__hist):
                return self.__hist[index]
            else:
                return None

    def GetMinValue(self):  # pylint: disable=C0103
        """Get min value of the ValueVector
        """
        return self.__min

    def GetMaxValue(self):  # pylint: disable=C0103
        """Get max value of the ValueVector
        """
        return self.__max

    def GetStandardDeviation(self):  # pylint: disable=C0103
        """Get standard Deviation of the ValueVector
        """
        return self.__sigma

    def GetMeanValue(self):  # pylint: disable=C0103
        """Get mean value of the ValueVector
        """
        return self.__mean

    def SetValue(self, hist_values):  # pylint: disable=C0103
        """ Set the vector of histogram value tuples
            this method is used in load method of ValResult for Histogram
        """
        if hist_values is not None:
            self.__pattern = []
            self.__hist = []
            self.__hist_values = hist_values
            self.__pattern, self.__hist = list(zip(*hist_values[2:])[0]), list(zip(*hist_values[2:-1])[1])
            self.__max = hist_values[0][0]
            self.__min = hist_values[0][1]
            self.__sigma = hist_values[1][0]
            self.__mean = hist_values[1][1]

    def __CalcHistogram(self, values, bins):  # pylint: disable=C0103
        """ Calculate the Histogram values
        """
        try:
            bins = int(bins)
            step = (max(values) - min(values)) / bins
            pattern = [(min(values) + (x + 1) * step) for x in range(bins)]
        except:
            pattern = bins

        hist = [0] * (len(pattern) - 1)

        for val in values:
            if val >= pattern[0]:
                for iBin, iBinThres in enumerate(pattern[1:]):
                    if val < iBinThres:
                        hist[iBin] += 1
                        break

        return pattern, hist

    def GetHistogram(self, value_vect, bins, update=True, norm=False):  # pylint: disable=C0103
        """Get the histogram of the values

        :param value_vect: values for histogram calculation with datatype list or ValueVector
        :param bins: list or bin counts used for x-axis
        :param update: flag to update the hist and pattern value
        :param norm: flag to calculate Normalized value for histogram in Percentage
        """
        pattern, hist = [], []
        if isinstance(value_vect, list):
            value_vect = ValueVector("", "", value_vect, min(value_vect) - 5, max(value_vect) + 5)

        if isinstance(value_vect, ValueVector):
            pattern, hist = self.__CalcHistogram(value_vect.GetValue(), bins)
            total_values = len(value_vect)
        else:
            raise StandardError("Only Value Vector or List data types are allowed")

        if update:
            if norm:
                self.__hist = []
                for hist_entry in hist:
                    self.__hist.append(abs(float(hist_entry) / total_values) * 100)
                hist = self.__hist
            else:
                self.__hist = hist

            self.__pattern = pattern
            self.__max = value_vect.GetMaxValue()
            self.__min = value_vect.GetMinValue()
            self.__sigma = value_vect.GetStandardDeviation()
            self.__mean = value_vect.GetMeanValue()
            self.__hist_values = [(self.__max, self.__min), (self.__sigma, self.__mean)]
            self.__hist_values += zip(self.__pattern, self.__hist + [0])

        return pattern, hist

    def CompareHist(self, hist_ref, out_path=None):  # pylint: disable=C0103
        """TODO"""
        plotter = ValidationPlot(out_path)
        title = 'sample'
        axes = plotter.generate_figure(fig_width=5, fig_height=5, show_grid=False)
        hist_value_all = self.__hist

        hist_value_ref = hist_ref.GetHist()
        hist_ref.GetPattern()

        hist_values_list = [hist_value_all, hist_value_ref]
        pltt, _ = plotter.get_bar_chart(axes, hist_values_list, bar_orientation='horizontal')

        buf = plotter.get_plot_data_buffer(pltt, fontsize=20)
        plotter.get_drawing_from_buffer(buf, "%s" % title, width=450, height=180)
        print 'reached'

    def PlotHistogramBarChart(self, out_path=None, label_list=None, label_rotation=None,  # pylint: disable=C0103
                              label_size=None, relative_bar_size=0.9, bar_orientation='vertical'):
        """Plot the bar chart of the histogram values

        :param out_path: Outputpath location where image file will be created
        :type out_path: string
        :param label_list: list of labels representing each bar
        :type label_list: list of string
        :param label_rotation: rotation of label bar angle in degree
        :type label_rotation: integer
        :param label_size: font size of the label
        :type label_size: float
        :param relative_bar_size: size of the bar
        :type relative_bar_size: float
        :param bar_orientation: bar orientiation default = vertical other possible value is horizontal
        :type bar_orientation: string
        """
        plotter = ValidationPlot(out_path)
        axes = plotter.generate_figure(fig_width=5, fig_height=5, show_grid=False)

#        data_vectors = self.__hist_values

        min_tick_width = min([n1 - n for n1, n in zip(self.__pattern[1:], self.__pattern[:-1])])
        bar_middlepos = [n + ((n1 - n) / 2.0) for n1, n in zip(self.__pattern[1:], self.__pattern[:-1])]
        axis_ext = [min(self.__pattern), max(self.__pattern)]

        if bar_orientation == 'vertical':
            plotter.get_bar_chart(axes, self.__hist, xlabel=self.GetUnit().GetName(), ylabel='', title=self.GetName(),
                                  xticks=self.__pattern, xticks_labels=label_list, rotate=label_rotation,
                                  x_axis_ext=axis_ext, yticks=None, yticks_labels=None, y_axis_ext=None,
                                  rwidth=relative_bar_size * min_tick_width, bar_pos=bar_middlepos,
                                  bar_orientation=bar_orientation, align='center')
        else:
            plotter.get_bar_chart(axes, self.__hist, xlabel='', ylabel=self.GetUnit().GetName(), title=self.GetName(),
                                  xticks=None, xticks_labels=None, rotate=label_rotation, x_axis_ext=None,
                                  yticks=self.__pattern, yticks_labels=label_list, y_axis_ext=axis_ext,
                                  rwidth=relative_bar_size * min_tick_width, bar_pos=bar_middlepos,
                                  bar_orientation=bar_orientation, align='center')

        args = [label_rotation, label_size, relative_bar_size, bar_orientation]
        if type(label_list) is list:
            args += label_list
        self.__PrepareHistogramConfig(plottype="bar", title=self.GetName(), args=args)
        # Plot the Graph into a picture and return it as a binary buffer
        return plotter.get_drawing_from_buffer(plotter.get_plot_data_buffer(),
                                               "Hist_" + self.GetName().replace(' ', '_') + "_%s" % str(uuid4()),
                                               width=300, height=300), plotter

    def PlotHistogramPieChart(self, out_path=None, title=None, label_list=None, legend=None,  # pylint: disable=C0103
                              labels_fontsize=None, legend_fontsize=6, optimised_view=False):
        """
         Plot the pie chart of the histogram values

        :param out_path: Outputpath location where image file will be created
        :type out_path: string
        :param title: title of the figure
        :type title: string
        :param label_list: a list of all the labels for data values... ["sample1", "sample2"....]
        :type label_list: list of string
        :param legend: if True then Xlabel will be used as legends
                       if list of string passed then use them as values for legend
        :type legend: Boolean or List of String
        :param labels_fontsize: font size for labels
        :type labels_fontsize: float
        :param legend_fontsize: font size for Legends
        :type legend_fontsize: flaot
        :param optimised_view:  if true will display three largest values on the pie
                             chart and rest of the values will merge as others
        :type optimised_view: boolean
        """

        plotter = ValidationPlot(out_path)
        pie_axes = plotter.generate_figure(fig_width=5, fig_height=5, show_grid=False)
        data_values = self.__hist
        args = [False, labels_fontsize, legend_fontsize, optimised_view]

        if type(legend) is list:
            args[0] = False  # Flag value False means legend list additionally provided
            if len(legend) == len(label_list):
                for i in range(len(legend)):
                    args.append(label_list[i])
                    args.append(legend[i])
        else:
            args[0] = True  # Flag value True means Use the label_list as legends
            args += label_list
        self.__PrepareHistogramConfig(plottype="pie", title=title, args=args)

        if optimised_view is True:
            zip_values = zip(data_values, label_list)
            tmp = sorted(zip_values)  # Sorts the data values in ascending order
            if len(tmp) > 3:
                # Group lower values together
                lower_vals = 0
                for i in range(0, len(tmp) - 3):
                    lower_vals += tmp[i][0]
                data_values = []
                label_list = []
                for i in range(len(tmp) - 3, len(tmp)):
                    data_values.append(tmp[i][0])
                    label_list.append(tmp[i][1])
                data_values.append(lower_vals)
                label_list.append("Others")

        plotter.get_pie_chart(axes=pie_axes, data=data_values, title=title, labels=label_list, legend=legend,
                              labels_fontsize=labels_fontsize, legend_fontsize=legend_fontsize)
        return plotter.get_drawing_from_buffer(plotter.get_plot_data_buffer(),
                                               "Hist_" + self.GetName().replace(' ', '_') + "_%s" % str(uuid4()),
                                               width=300, height=300), plotter

    def PlotHistogramDistribution(self, out_path=None, title=None, x_label=None, y_label=None,  # pylint: disable=C0103
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

        plotter.get_normal_pdf(axes, self.__pattern, self.__sigma, self.__mean, legend=legend, draw_lines=draw_lines,
                               write_text=write_text, title=title,
                               xlabel=x_label, ylabel=y_label)
        args = [draw_lines, write_text, x_label, y_label, legend]
        self.__PrepareHistogramConfig(plottype="distribution", title=title, args=args)

        return plotter.get_drawing_from_buffer(plotter.get_plot_data_buffer(),
                                               "Hist_" + self.GetName().replace(' ', '_') + "_%s" % str(uuid4()),
                                               width=300, height=300), plotter

    def PlotHistogram(self, output_path=None):  # pylint: disable=C0103
        """
        Generic Wrapper Function to plot Histogram for loaded data for simplified interface
        The default Histogram type is bar

        :param output_path: Output File path
        :type output_path: string
        """

        plotter = None
        if self.__plotcfg is None:
            plotter = self.PlotHistogramBarChart(out_path=output_path, label_list=None,
                                                 label_rotation=None, label_size=None,
                                                 relative_bar_size=0.9, bar_orientation='vertical')
        else:
            plottype = self.__plotcfg[0]
            title = self.__plotcfg[1]
            if plottype == "bar":
                label_rotation = None if self.__plotcfg[2] == "None" else float(self.__plotcfg[2])
                label_size = None if self.__plotcfg[3] == "None" else float(self.__plotcfg[3])
                relative_bar_size = float(self.__plotcfg[4])
                bar_orientation = self.__plotcfg[5]
                label_list = None if len(self.__plotcfg[6:]) == 0 else self.__plotcfg[6:]
                plotter = self.PlotHistogramBarChart(out_path=output_path, label_list=label_list,
                                                     label_rotation=label_rotation, label_size=label_size,
                                                     relative_bar_size=relative_bar_size,
                                                     bar_orientation=bar_orientation)
            elif plottype == "pie":
                legend_flag = True if self.__plotcfg[2] == "True" else False
                # labels_fontsize = float(self.__plotcfg[3])
                labels_fontsize = None if self.__plotcfg[3] == "None" else float(self.__plotcfg[3])
                legend_fontsize = float(self.__plotcfg[4])
                optimised_view = True if self.__plotcfg[5] == "True" else False
                if legend_flag:
                    legend = True
                    label_list = self.__plotcfg[6:]
                else:
                    label_list = self.__plotcfg[6:][0::2]
                    legend = self.__plotcfg[6:][1::2]
                plotter = self.PlotHistogramPieChart(out_path=output_path, title=title, label_list=label_list,
                                                     legend=legend, labels_fontsize=labels_fontsize,
                                                     legend_fontsize=legend_fontsize, optimised_view=optimised_view)
            elif plottype == "distribution":
                draw_lines = True if self.__plotcfg[2] == "True" else False
                write_text = None if self.__plotcfg[3] == "None" else float(self.__plotcfg[3])
                x_label = None if self.__plotcfg[4] == "None" else self.__plotcfg[4]
                y_label = None if self.__plotcfg[5] == "None" else self.__plotcfg[5]
                legend = None if self.__plotcfg[6] == "None" else self.__plotcfg[6]
                plotter = self.PlotHistogramDistribution(out_path=output_path, title=title, x_label=x_label,
                                                         y_label=y_label, legend=legend,
                                                         draw_lines=draw_lines, write_text=write_text)
        return plotter

    def __PrepareHistogramConfig(self, plottype, title, args):  # pylint: disable=C0103
        """
        Prepare the arguement list to be store in database

        :param plottype: type of plot e.g. "bar", "pie" or "distribution"
        :type plottype: string
        :param title: title of the plot
        :type title: string
        :param args: list of argument
        :type args: list
        """
        if self.__plotcfg is None:
            self.__plotcfg = [plottype, title]
            str_args = []
            for arg in args:
                str_args.append(str(arg))
            self.__plotcfg += str_args


"""
CHANGE LOG:
-----------
$Log: result_types.py  $
Revision 1.26.1.6 2017/10/19 14:32:12CEST Hospes, Gerd-Joachim (uidv8815) 
fix remove of number in imports
Revision 1.26.1.5 2017/10/17 12:29:35CEST Hospes, Gerd-Joachim (uidv8815)
back to const for message length
Revision 1.26.1.4 2017/08/25 15:47:08CEST Hospes, Gerd-Joachim (uidv8815)
static check fixes
Revision 1.26.1.3 2017/08/18 19:25:35CEST Hospes, Gerd-Joachim (uidv8815)
fix numpy.nanmin error of new numpy
Revision 1.26.1.2 2017/07/03 08:57:11CEST Mertens, Sven (uidv7805)
let's see if this can work
Revision 1.26.1.1 2017/02/02 15:34:57CET Hospes, Gerd-Joachim (uidv8815)
add log.exception if range for ValueVector is set to None
Revision 1.26 2015/12/07 12:09:15CET Mertens, Sven (uidv7805)
removing some pep8 errors
Revision 1.25 2015/12/01 18:58:03CET Hospes, Gerd-Joachim (uidv8815)
fix accidental change of Histogram Min/Max values
Revision 1.24 2015/12/01 18:35:50CET Hospes, Gerd-Joachim (uidv8815)
add option to set y axis in PlotMedian
Revision 1.23 2015/12/01 11:46:40CET Hospes, Gerd-Joachim (uidv8815)
create str(array) for ValueVector for each element
Revision 1.22 2015/11/06 13:48:24CET Hospes, Gerd-Joachim (uidv8815)
fix using <= for catch in hyst, new test added
--- Added comments ---  uidv8815 [Nov 6, 2015 1:48:25 PM CET]
Change Package : 394479:1 http://mks-psad:7002/im/viewissue?selection=394479
Revision 1.21 2015/09/11 13:17:11CEST Hospes, Gerd-Joachim (uidv8815)
close check for types of values: dropping values with wrong type during init and in AddTimestampAndValue,
extended docu, enhanced test to check value types
--- Added comments ---  uidv8815 [Sep 11, 2015 1:17:12 PM CEST]
Change Package : 372589:1 http://mks-psad:7002/im/viewissue?selection=372589
Revision 1.20 2015/09/08 17:58:40CEST Hospes, Gerd-Joachim (uidv8815)
add possible default value to ChangeTimeRange, adapt type check for it and create module tests
--- Added comments ---  uidv8815 [Sep 8, 2015 5:58:41 PM CEST]
Change Package : 373847:1 http://mks-psad:7002/im/viewissue?selection=373847
$LRevision 1.19 2015/09/04 17:49:50CEST Hospes, Gerd-Joachim (uidv8815)
$Lfix array type handling and add description of it
Revision 1.18 2015/09/03 16:12:17CEST Hospes, Gerd-Joachim (uidv8815)
use nanmin/nanmax for range calc, rewrite __pow__ to keep types, extend tests for calc to use inf
--- Added comments ---  uidv8815 [Sep 3, 2015 4:12:17 PM CEST]
Change Package : 373636:1 http://mks-psad:7002/im/viewissue?selection=373636
Revision 1.17 2015/09/02 16:16:32CEST Hospes, Gerd-Joachim (uidv8815)
new When implementation and extended tests, extend GetTimestamps with as_list option
--- Added comments ---  uidv8815 [Sep 2, 2015 4:16:32 PM CEST]
Change Package : 372889:1 http://mks-psad:7002/im/viewissue?selection=372889
Revision 1.16 2015/09/01 19:00:51CEST Hospes, Gerd-Joachim (uidv8815)
remove duplicated lines
--- Added comments ---  uidv8815 [Sep 1, 2015 7:00:52 PM CEST]
Change Package : 372585:1 http://mks-psad:7002/im/viewissue?selection=372585
Revision 1.15 2015/08/31 17:13:29CEST Hospes, Gerd-Joachim (uidv8815)
fix types for results in When, Abs, Max/Min
--- Added comments ---  uidv8815 [Aug 31, 2015 5:13:29 PM CEST]
Change Package : 371927:1 http://mks-psad:7002/im/viewissue?selection=371927
Revision 1.14 2015/08/28 15:31:52CEST Hospes, Gerd-Joachim (uidv8815)
pep8/pylint fixes
--- Added comments ---  uidv8815 [Aug 28, 2015 3:31:52 PM CEST]
Change Package : 368827:1 http://mks-psad:7002/im/viewissue?selection=368827
Revision 1.13 2015/08/27 18:13:11CEST Hospes, Gerd-Joachim (uidv8815)
extend warnings, use more numpy methods, floordiv update
--- Added comments ---  uidv8815 [Aug 27, 2015 6:13:12 PM CEST]
Change Package : 368827:1 http://mks-psad:7002/im/viewissue?selection=368827
Revision 1.12 2015/08/25 14:44:45CEST Hospes, Gerd-Joachim (uidv8815)
optimize _arithmatic and _comparison using narray functions
--- Added comments ---  uidv8815 [Aug 25, 2015 2:44:46 PM CEST]
Change Package : 368827:1 http://mks-psad:7002/im/viewissue?selection=368827
Revision 1.11 2015/08/24 18:13:57CEST Hospes, Gerd-Joachim (uidv8815)
fix min/max/mean/std_dev to support None values and empty signals
--- Added comments ---  uidv8815 [Aug 24, 2015 6:13:57 PM CEST]
Change Package : 370325:1 http://mks-psad:7002/im/viewissue?selection=370325
Revision 1.10 2015/08/21 18:12:54CEST Hospes, Gerd-Joachim (uidv8815)
optimize with common_ts
--- Added comments ---  uidv8815 [Aug 21, 2015 6:12:55 PM CEST]
Change Package : 368827:1 http://mks-psad:7002/im/viewissue?selection=368827
Revision 1.9 2015/08/20 11:05:09CEST Hospes, Gerd-Joachim (uidv8815)
fix __logical to only compare values with timestamps, test updated
--- Added comments ---  uidv8815 [Aug 20, 2015 11:05:10 AM CEST]
Change Package : 368827:1 http://mks-psad:7002/im/viewissue?selection=368827
Revision 1.8 2015/08/19 13:55:16CEST Ahmed, Zaheer (uidu7634)
bug fix in numpyto binary
--- Added comments ---  uidu7634 [Aug 19, 2015 1:55:17 PM CEST]
Change Package : 368823:1 http://mks-psad:7002/im/viewissue?selection=368823
Revision 1.7 2015/08/19 09:20:54CEST Ahmed, Zaheer (uidu7634)
bug fixes in logical operators for BinarySignal
added new function numpy to BinarySignal
--- Added comments ---  uidu7634 [Aug 19, 2015 9:20:54 AM CEST]
Change Package : 368823:1 http://mks-psad:7002/im/viewissue?selection=368823
Revision 1.6 2015/08/13 16:30:39CEST Mertens, Sven (uidv7805)
- fix for GetTimestamps call,
- pylint fixes
--- Added comments ---  uidv7805 [Aug 13, 2015 4:30:40 PM CEST]
Change Package : 366613:1 http://mks-psad:7002/im/viewissue?selection=366613
Revision 1.5 2015/07/02 10:37:39CEST Hospes, Gerd-Joachim (uidv8815)
pep8 error fixes
--- Added comments ---  uidv8815 [Jul 2, 2015 10:37:39 AM CEST]
Change Package : 350826:1 http://mks-psad:7002/im/viewissue?selection=350826
Revision 1.4 2015/06/01 11:49:59CEST Ahmed, Zaheer (uidu7634)
bugfixes in GetFirstValueOverThres() ,GetLastValueOverThres() for empty values in ValueVector class
Override methods to return instance of Signal method instead of NumpySignal
--- Added comments ---  uidu7634 [Jun 1, 2015 11:49:59 AM CEST]
Change Package : 342925:1 http://mks-psad:7002/im/viewissue?selection=342925
Revision 1.3 2015/05/08 13:36:10CEST Ahmed, Zaheer (uidu7634)
fixes in binarySignal class
--- Added comments ---  uidu7634 [May 8, 2015 1:36:10 PM CEST]
Change Package : 328909:1 http://mks-psad:7002/im/viewissue?selection=328909
Revision 1.2 2015/05/08 12:49:34CEST Ahmed, Zaheer (uidu7634)
intial merge
--- Added comments ---  uidu7634 [May 8, 2015 12:49:34 PM CEST]
Change Package : 328909:1 http://mks-psad:7002/im/viewissue?selection=328909
Revision 1.1.1.1 2015/05/08 10:09:00CEST Ahmed, Zaheer (uidu7634)
Sundarah Intial revision
--- Added comments ---  uidu7634 [May 8, 2015 10:09:00 AM CEST]
Change Package : 328909:1 http://mks-psad:7002/im/viewissue?selection=328909
Revision 1.46.1.1 2015/04/10 10:22:28CEST Amancharla, Sundaranataraja (uidj8906)
Created New Numpy Class
--- Added comments ---  uidj8906 [Apr 10, 2015 10:22:28 AM CEST]
Change Package : 310108:1 http://mks-psad:7002/im/viewissue?selection=310108
Revision 1.46 2015/03/12 09:20:21CET Ahmed, Zaheer (uidu7634)
empty signal with abs() crash prevention
--- Added comments ---  uidu7634 [Mar 12, 2015 9:20:21 AM CET]
Change Package : 310358:1 http://mks-psad:7002/im/viewissue?selection=310358
Revision 1.45 2015/02/25 19:58:40CET Ahmed, Zaheer (uidu7634)
bug fix to prevent crash for empty ValueVector for GetLastValueOverThres() and GetFirstValueOverThres()
--- Added comments ---  uidu7634 [Feb 25, 2015 7:58:40 PM CET]
Change Package : 310109:1 http://mks-psad:7002/im/viewissue?selection=310109
Revision 1.44 2015/02/25 14:00:05CET Ahmed, Zaheer (uidu7634)
added new funciton GetHystersis()
--- Added comments ---  uidu7634 [Feb 25, 2015 2:00:05 PM CET]
Change Package : 310109:1 http://mks-psad:7002/im/viewissue?selection=310109
Revision 1.43 2015/01/30 09:56:18CET Ahmed, Zaheer (uidu7634)
added new unit decibel (db)
--- Added comments ---  uidu7634 [Jan 30, 2015 9:56:19 AM CET]
Change Package : 279151:2 http://mks-psad:7002/im/viewissue?selection=279151
Revision 1.42 2014/12/17 14:57:47CET Ellero, Stefano (uidw8660)
Removed all db.obj based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Dec 17, 2014 2:57:47 PM CET]
Change Package : 281278:1 http://mks-psad:7002/im/viewissue?selection=281278
Revision 1.41 2014/11/24 15:30:48CET Ahmed, Zaheer (uidu7634)
interface adjustment to return python list as default for Signal GetTimestamps()
--- Added comments ---  uidu7634 [Nov 24, 2014 3:30:49 PM CET]
Change Package : 271286:1 http://mks-psad:7002/im/viewissue?selection=271286
Revision 1.40 2014/11/24 14:57:54CET Ahmed, Zaheer (uidu7634)
Signal class optimized using Numpy internally for calculation
--- Added comments ---  uidu7634 [Nov 24, 2014 2:57:55 PM CET]
Change Package : 271286:1 http://mks-psad:7002/im/viewissue?selection=271286
Revision 1.39 2014/11/14 10:55:07CET Ahmed, Zaheer (uidu7634)
Add Kilogram unit
--- Added comments ---  uidu7634 [Nov 14, 2014 10:55:08 AM CET]
Change Package : 279153:1 http://mks-psad:7002/im/viewissue?selection=279153
Revision 1.38 2014/10/22 10:48:47CEST Ahmed, Zaheer (uidu7634)
Add xlabel and ylabel to have unit name for plothistogrambarchart()
Revision 1.37 2014/10/14 15:29:42CEST Ahmed, Zaheer (uidu7634)
pep8 fixes
--- Added comments ---  uidu7634 [Oct 14, 2014 3:29:42 PM CEST]
Change Package : 268541:1 http://mks-psad:7002/im/viewissue?selection=268541
Revision 1.36 2014/09/25 13:29:18CEST Hospes, Gerd-Joachim (uidv8815)
adapt stk.img files to style guide, new names used in all modules and tests except stk.img tests
--- Added comments ---  uidv8815 [Sep 25, 2014 1:29:19 PM CEST]
Change Package : 264203:1 http://mks-psad:7002/im/viewissue?selection=264203
Revision 1.35 2014/09/19 22:38:20CEST Ahmed, Zaheer (uidu7634)
remvoe wrong ascii character error from doc string
--- Added comments ---  uidu7634 [Sep 19, 2014 10:38:24 PM CEST]
Change Package : 264277:2 http://mks-psad:7002/im/viewissue?selection=264277
Revision 1.33 2014/09/19 16:01:04CEST Ahmed, Zaheer (uidu7634)
add uuid into output file for plot median function
--- Added comments ---  uidu7634 [Sep 19, 2014 4:01:05 PM CEST]
Change Package : 265571:1 http://mks-psad:7002/im/viewissue?selection=265571
Revision 1.32 2014/05/21 09:53:13CEST Ahmed, Zaheer (uidu7634)
Inherting BaseMessage Class from from str instead of BaseValue to get more features from python str
--- Added comments ---  uidu7634 [May 21, 2014 9:53:14 AM CEST]
Change Package : 235091:2 http://mks-psad:7002/im/viewissue?selection=235091
Revision 1.31 2014/05/19 17:21:21CEST Hospes, Gerd-Joachim (uidv8815)
extend ValueVector.__getitem__ to raise IndexError, add fixes in Signal.GetSubsetForTimeInterval, add tests for loops
--- Added comments ---  uidv8815 [May 19, 2014 5:21:22 PM CEST]
Change Package : 235082:1 http://mks-psad:7002/im/viewissue?selection=235082
Revision 1.30 2014/05/19 11:28:48CEST Ahmed, Zaheer (uidu7634)
New class BaseMessage Representing String in API
--- Added comments ---  uidu7634 [May 19, 2014 11:28:49 AM CEST]
Change Package : 235091:1 http://mks-psad:7002/im/viewissue?selection=235091
Revision 1.29 2014/04/29 09:06:31CEST Mertens, Sven (uidv7805)
- object inheritance,
- proper logger usage,
- import tuning
--- Added comments ---  uidv7805 [Apr 29, 2014 9:06:32 AM CEST]
Change Package : 233154:1 http://mks-psad:7002/im/viewissue?selection=233154
Revision 1.28 2014/04/11 14:06:08CEST Ahmed, Zaheer (uidu7634)
pep8 fixes
--- Added comments ---  uidu7634 [Apr 11, 2014 2:06:09 PM CEST]
Change Package : 230922:1 http://mks-psad:7002/im/viewissue?selection=230922
Revision 1.27 2014/04/11 13:58:32CEST Ahmed, Zaheer (uidu7634)
Added DeleteValue, CompareHist,
Add RemoveOutRangeValues from Signal and ValueVector
use uuid to ensure unique file name generation to prevent overwrite
--- Added comments ---  uidu7634 [Apr 11, 2014 1:58:32 PM CEST]
Change Package : 230922:1 http://mks-psad:7002/im/viewissue?selection=230922
Revision 1.26 2014/03/10 12:25:59CET Hecker, Robert (heckerr)
Bug Fix in Vertical Plot.
--- Added comments ---  heckerr [Mar 10, 2014 12:25:59 PM CET]
Change Package : 224151:1 http://mks-psad:7002/im/viewissue?selection=224151
Revision 1.25 2014/02/20 17:50:23CET Ahmed, Zaheer (uidu7634)
pep8 fixes
--- Added comments ---  uidu7634 [Feb 20, 2014 5:50:24 PM CET]
Change Package : 220098:2 http://mks-psad:7002/im/viewissue?selection=220098
Revision 1.24 2014/02/14 16:18:51CET Ahmed, Zaheer (uidu7634)
Added new Function SetHistogramConfig() get_histogramConfig()
Changes made to save Histogram plot configuration
Added Genertic function PlotHistogram() for report generator to automatically produce Histogram plot
without known the type of plot
--- Added comments ---  uidu7634 [Feb 14, 2014 4:18:51 PM CET]
Change Package : 214642:1 http://mks-psad:7002/im/viewissue?selection=214642
Revision 1.23 2013/12/03 17:03:55CET Sandor-EXT, Miklos (uidg3354)
pep8 fixes
--- Added comments ---  uidg3354 [Dec 3, 2013 5:03:55 PM CET]
Change Package : 208827:1 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.22 2013/12/03 14:46:12CET Sandor-EXT, Miklos (uidg3354)
GetSubsetForTimeInterval added
--- Added comments ---  uidg3354 [Dec 3, 2013 2:46:12 PM CET]
Change Package : 208827:1 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.21 2013/10/30 17:22:49CET Hecker, Robert (heckerr)
removed try except block.
--- Added comments ---  heckerr [Oct 30, 2013 5:22:50 PM CET]
Change Package : 196568:1 http://mks-psad:7002/im/viewissue?selection=196568
Revision 1.20 2013/09/19 13:32:11CEST Ahmed-EXT, Zaheer (uidu7634)
Added better handling of unxpected datatype  for valuevector in get_histogram() with raising Exception
--- Added comments ---  uidu7634 [Sep 19, 2013 1:32:11 PM CEST]
Change Package : 196580:1 http://mks-psad:7002/im/viewissue?selection=196580
Revision 1.19 2013/09/13 16:30:45CEST Ahmed-EXT, Zaheer (uidu7634)
Add Get function for pattern, hist, min, max, StandardDeviation, mean
added mean and sigma storage
improve code reusability get_histogram() in value_vect
--- Added comments ---  uidu7634 [Sep 13, 2013 4:30:46 PM CEST]
Change Package : 196580:1 http://mks-psad:7002/im/viewissue?selection=196580
Revision 1.18 2013/09/12 17:39:11CEST Verma-EXT, Ajitesh (uidv5394)
added function:
- PlotHistogramPieChart
- PlotHistogramDistribution
--- Added comments ---  uidv5394 [Sep 12, 2013 5:39:11 PM CEST]
Change Package : 196582:1 http://mks-psad:7002/im/viewissue?selection=196582
Revision 1.17 2013/09/10 14:19:30CEST Ahmed-EXT, Zaheer (uidu7634)
Support for normalize historgram
--- Added comments ---  uidu7634 [Sep 10, 2013 2:19:30 PM CEST]
Change Package : 196580:1 http://mks-psad:7002/im/viewissue?selection=196580
Revision 1.16 2013/09/10 10:02:30CEST Ahmed-EXT, Zaheer (uidu7634)
Seperated the hist_Value arrays into pattern and hist
added min and max
Interface change in get_histogram: returns pattern, hist
--- Added comments ---  uidu7634 [Sep 10, 2013 10:02:31 AM CEST]
Change Package : 196580:1 http://mks-psad:7002/im/viewissue?selection=196580
Revision 1.15 2013/08/09 16:10:07CEST Raedler, Guenther (uidt9430)
- improved bar plot functions (changes by JW)
--- Added comments ---  uidt9430 [Aug 9, 2013 4:10:07 PM CEST]
Change Package : 191955:1 http://mks-psad:7002/im/viewissue?selection=191955
Revision 1.14 2013/08/09 15:32:29CEST Raedler, Guenther (uidt9430)
- fixed errors for pow(signal) when implementing the module test
--- Added comments ---  uidt9430 [Aug 9, 2013 3:32:30 PM CEST]
Change Package : 190322:1 http://mks-psad:7002/im/viewissue?selection=190322
Revision 1.13 2013/08/08 13:35:08CEST Raedler, Guenther (uidt9430)
- fixed errors in module test of baseunit
- removed pep8 warnings
- improved module test coverage
--- Added comments ---  uidt9430 [Aug 8, 2013 1:35:08 PM CEST]
Change Package : 190322:1 http://mks-psad:7002/im/viewissue?selection=190322
Revision 1.12 2013/08/06 16:13:22CEST Raedler, Guenther (uidt9430)
- one more
--- Added comments ---  uidt9430 [Aug 6, 2013 4:13:23 PM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.11 2013/08/06 16:10:45CEST Raedler, Guenther (uidt9430)
- wrong import
--- Added comments ---  uidt9430 [Aug 6, 2013 4:10:45 PM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.10 2013/08/06 15:59:34CEST Raedler, Guenther (uidt9430)
- generate warning, if sympy is not installed. if ValBaseUnit is used, sympy is mandatory.
- remove tailing whitespaces
--- Added comments ---  uidt9430 [Aug 6, 2013 3:59:35 PM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.9 2013/08/06 10:47:04CEST Dintzer, Philippe (dintzerp)
- add not equal operator for Signals
--- Added comments ---  dintzerp [Aug 6, 2013 10:47:04 AM CEST]
Change Package : 175136:3 http://mks-psad:7002/im/viewissue?selection=175136
Revision 1.8 2013/08/02 12:50:48CEST Raedler, Guenther (uidt9430)
- use sympy for units
--- Added comments ---  uidt9430 [Aug 2, 2013 12:50:48 PM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.7 2013/07/16 07:51:57CEST Raedler, Guenther (uidt9430)
- add GetId into BaseUnit class
--- Added comments ---  uidt9430 [Jul 16, 2013 7:51:57 AM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.6 2013/07/16 07:28:28CEST Raedler, Guenther (uidt9430)
- fixed error when comparing two timestamp vectors (use ValueVector)
--- Added comments ---  uidt9430 [Jul 16, 2013 7:28:28 AM CEST]
Change Package : 180569:1 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.5 2013/07/11 15:37:46CEST Dintzer, Philippe (dintzerp)
add small bug fixes
add security checks
--- Added comments ---  dintzerp [Jul 11, 2013 3:37:46 PM CEST]
Change Package : 175155:10 http://mks-psad:7002/im/viewissue?selection=175155
Revision 1.4 2013/07/10 09:26:23CEST Raedler, Guenther (uidt9430)
- extensions of math and validation functions for classes Signal(), BaseUnit(), BinarySignal()
- added plot functions for Signal(), ValueVector(), Histogram
Changes implemented by P.Dintzer
--- Added comments ---  uidt9430 [Jul 10, 2013 9:26:23 AM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.3 2013/06/05 16:26:18CEST Raedler, Guenther (uidt9430)
- added Histogram class
- moved some plot functions from ValueVector into Histogram
- changed return values of plot functions
- changed default values for True and False in BinarySignal class
--- Added comments ---  uidt9430 [Jun 5, 2013 4:26:18 PM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.2 2013/05/29 10:23:58CEST Raedler, Guenther (uidt9430)
- prepared several override methods to be implemented for signals
- prepared added plot methods for signals and value vectors (histrograms)
- implemented several override methods for binary signals which creates a warning in the log
--- Added comments ---  uidt9430 [May 29, 2013 10:23:59 AM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.1 2013/05/29 08:02:43CEST Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/
04_Engineering/stk/val/project.pj
"""
