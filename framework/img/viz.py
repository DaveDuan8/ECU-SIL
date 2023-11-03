"""
crt.ecu_sil.viz
---------------
Data plotting factories specialized for ECU-SIL plots: EM Birdseye, Signal Comparison, ...
"""
import logging
import os
import uuid
import types as types
import numpy as np
import pandas as pd
from matplotlib import gridspec, pylab as plt, path as mpath, patches as mpatches


__author__ = "Leidenberger, Ralf"
__copyright__ = "Copyright 2014, Continental AG"
__version__ = "$Revision: 1.1 $"
__maintainer__ = "$Author: Leidenberger, Ralf (uidq7596) $"
__date__ = "$Date: 2020/03/25 21:11:06CET $"


ZOOM = False
ZOOM_LIMITS = [100, 105]

TIME_SPAN = "time_span"


class ObjectPlotter(object):
    """ Factory for object info plot creation. """

    def __init__(self, outdir="."):
        """
        Initializes the plotter
        :param outdir: Output directory for the created plots
        """
        super(ObjectPlotter, self).__init__()
        self._output_directory = outdir

    def set_output_directory(self, path):
        """
        Sets the output directory.
        :param path: The new output directory path
        """
        self._output_directory = path

    def create_obj_info_plot(self, ecu_obj, sil_obj):
        """ Generates the object info plot for the two matched objects.
        :param ecu_obj: ECU object
        :param sil_obj: SIL Object
        :return: Filehandle to the saved plot
        """
        fig = self._obj_info_plot(ecu_obj, sil_obj)

        filename = "plot_{0:}.jpg".format(str(uuid.uuid1()))
        path = os.path.join(self._output_directory, filename)
        fig.savefig(path)
        plt.close(fig)
        return filename

    def _obj_info_plot(self, ecu_obj, sil_obj):
        """ Constructs the object info plot
        :param ecu_obj: ECU object
        :param sil_obj: SIL object
        :return: figure
        """
        gs = gridspec.GridSpec(3, 3)
        sc = 0.6
        fig = plt.figure(figsize=(36 * sc, 12 * sc), dpi=96, facecolor='w', edgecolor='k')

        # Birdseye
        ax1 = fig.add_subplot(gs[:, 0])
        self._birdseye_subplot(ax1)

        e_x = ecu_obj.get_signal("DistX")
        e_y = ecu_obj.get_signal("DistY")
        ax1.plot(e_y.values, e_x.values, linewidth=1, color="r", label="ECU")
        ax1.plot(e_y.values[0], e_x.values[0], linewidth=1, color="r", marker="o")

        s_x = sil_obj.get_signal("DistX")
        s_y = sil_obj.get_signal("DistY")
        ax1.plot(s_y.values, s_x.values, linewidth=1, color="b", label="SIL")
        ax1.plot(s_y.values[0], s_x.values[0], linewidth=1, color="b", marker="o")
        ax1.legend(loc='upper right', ncol=2)

        limits = [min(ecu_obj.start_time, sil_obj.start_time) - 10, max(ecu_obj.end_time, sil_obj.end_time) + 10]

        ax2 = fig.add_subplot(gs[0, 1:3])
        dx = (s_x - e_x)
        dy = (s_y - e_y)
        ax2.set_title("Spatial Distance")
        ax2.plot(dx.index.values, dx.values, "-b", label="DistX")
        ax2.plot(dy.index.values, dy.values, "-g", label="DistY")
        ax2.axhline(y=0.1, linewidth=1, color='r', label="Limits")
        ax2.axhline(y=-0.1, linewidth=1, color='r')
        # ax2.axhline(y=0.1, linewidth=1, color='r', linestyle=":", label="Limits")
        # ax2.axhline(y=-0.1, linewidth=1, color='r', linestyle=":")
        ax2.axvline(x=ecu_obj.start_time, linewidth=1, color='r', linestyle=":")
        ax2.axvline(x=ecu_obj.end_time, linewidth=1, color='r', linestyle=":")

        ax2.set_xlim(limits)
        # ax2.set_ylim([-0.5, 0.5])
        ax2.set_xlabel("Time [us]")
        ax2.set_ylabel("Delta [m]")
        ax2.grid()
        ax2.legend(loc="upper right", ncol=3)

        ax3 = fig.add_subplot(gs[1, 1:3])
        self._signal_subplot(ax3, ecu_obj, sil_obj, "Classification", limits)

        ax4 = fig.add_subplot(gs[2, 1:3])
        self._signal_subplot(ax4, ecu_obj, sil_obj, "ucEbaMovingObjQuality", limits)

        fig.set_tight_layout(True)
        return fig

    @staticmethod
    def _signal_subplot(ax, ecu_obj, sil_obj, title, limits=None):
        ax.set_title(title)
        ecu = ecu_obj.get_signal(title)
        sil = sil_obj.get_signal(title)
        ax.plot(sil.index.values, sil.values, color="b", label="SIL")
        ax.plot(ecu.index.values, ecu.values, linestyle=":", color="r", label="ECU")
        if limits:
            ax.set_xlim(limits)
        ax.grid()
        ax.set_xlabel("Time [us]")
        ax.set_ylabel("Value")
        ax.legend(loc="upper right", ncol=2)

    @staticmethod
    def _birdseye_subplot(ax):
        _Path = mpath.Path
        # Far scan range patch 9 deg opening reach 210
        path_data = [
            (_Path.MOVETO, (0.0, 0.0)),
            (_Path.LINETO, (-31.28, 190)),
            (_Path.CURVE3, (0, 210)),
            (_Path.CURVE3, (31.28, 190)),
            (_Path.CLOSEPOLY, (0, 0)),
            ]
        codes, verts = zip(*path_data)
        path = mpath.Path(verts, codes)
        patch = mpatches.PathPatch(path, facecolor='#f2f2f2', edgecolor="#f2f2f2", alpha=1)
        ax.add_patch(patch)

        # Near scan range patch 90 deg and 170 deg (check that)
        path_data = [
            (_Path.MOVETO, (0.0, 0.0)),
            (_Path.LINETO, (-15.49, 1.0)),
            (_Path.LINETO, (-49.49, 49.49)),
            (_Path.CURVE3, (0, 70)),
            (_Path.CURVE3, (49.49, 49.49)),
            (_Path.LINETO, (15.49, 1.0)),
            (_Path.CLOSEPOLY, (0, 0)),
            ]
        codes, verts = zip(*path_data)
        path = mpath.Path(verts, codes)
        patch = mpatches.PathPatch(path, facecolor='#f2f2f2', edgecolor="#f2f2f2", alpha=1)
        ax.add_patch(patch)

        ax.set_xlim([-55, 55])
        ax.set_ylim([-5, 245])
        ax.get_xticks()
        ax.grid()
        ax.invert_xaxis()
        # ax.axis('equal')
        ax.set_title("Birds Eye")
        ax.set_xlabel("DistY")
        ax.set_ylabel("DistX")

        return ax

    @staticmethod
    def dist_plot(ax):
        ax.plot([0, 1, 2, 3], [100, 95, 80, 60])
        ax.set_title("DistX")
        ax.set_xlabel("Time [s]")
        return ax


class PlotFactory(object):
    def __init__(self, outdir):
        super(PlotFactory, self).__init__()
        self.log = logging.getLogger(self.__class__.__name__)
        self.outdir = outdir

    def _calc_difference(self, signal_ref, signal):
        #print ("signal_ref.series", signal_ref.series)
        #print ("signal.series", signal.series)
        diff = signal_ref.series - signal.series
        #pd.isnull(diff.values).any()
        #diff[1:].fillna(0, inplace=True)
        #print(diff.ne(0).cumsum())

        #print("signal name viz", signal.name)
        #print("diff type viz", type(diff))
        #print( "diff in viz", diff)
        #pd.isnull(diff)
        #diff[0:].fillna(0, inplace=True)
        #diff[1:].fillna(0, inplace=True)
        diff.dropna(how='all')
        #print("diff fillna", diff.values)

        if True in pd.isnull(diff[10:-10000]).values:

                # Not all signal indexes are available, we will warn and remove incomparable
                # data points.
            self.log.warning("Missing indexes either in signal or reference signal.")
            #print(diff[pd.isnull(diff)])



        diff = diff[pd.isnull(diff) == False]

        name = "Delta {0:} and {1:}".format(signal.name, signal_ref.name)
        signal = AlgoSignal(name, diff, unit=signal.unit)
        return signal



    @staticmethod
    def _normalize_timestamp(signal, zero_index=None):
        """ Normalizes the micro second timestamp to seconds, and start
            with 0.0, or if zero_index is given uses this timestamp.
        """
        if zero_index is None:
            zero_index = signal.index.values[0]
        if not hasattr(signal, 'series'):
            return (signal.index.values - zero_index) * 1.e-6
        return (signal.series.index.values - zero_index) * 1.e-6

    def fct_plot(self, signal_ref, signal, delta):
        # Align all signals to a common normalized time
        first_common_ts = max(signal.index.values[0], signal_ref.index.values[0], delta.index.values[0])

        signal_ref_norm_ts = []
        signal_norm_ts = []
        delta_norm_ts = []
        # noinspection PyBroadException
        try:
            signal_ref_norm_ts = self._normalize_timestamp(signal_ref, first_common_ts)
            signal_norm_ts = self._normalize_timestamp(signal, first_common_ts)
            delta_norm_ts = self._normalize_timestamp(delta, first_common_ts)
        except:
            pass

        # Plot with 2 subplots
        plt.figure(num=None, figsize=(14, 6.2), dpi=240, facecolor='m', edgecolor='k')
        # Both signals
        plt.subplot(211)
        # plt.title(title)
        plt.plot(signal_ref_norm_ts, signal_ref.values, color="r", label=signal_ref.name, linewidth=0.5, linestyle="-")
        plt.plot(signal_norm_ts, signal.values, color="b", label=signal.name, linewidth=0.5, linestyle="-")
        plt.xlabel("Time [s]")
        plt.ylabel("{0:} [{1:}]".format(signal.name, signal.unit))
        plt.grid()
        plt.legend(loc='upper right', ncol=2)
        # plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=2,
        #            mode="expand", borderaxespad=0.)

        ampl = max(signal_ref.values) - min(signal_ref.values)
        ylim_lower = min(signal_ref.values) - 1.02 * ampl
        # if ylim_lower == 0:
        #     ylim_lower = -0.1 * max(signal_ref.values)
        ylim_upper = max(signal_ref.values) + 1.2 * ampl
        # if ylim_upper == 0:
        #     ylim_upper = 0.1
        plt.ylim([ylim_lower, ylim_upper])
        plt.xlim([signal_norm_ts[0], signal_norm_ts[-1]])
        # plt.xlim([200,signal_norm_ts[-1]])

        plt.subplot(212)
        plt.plot(delta_norm_ts, delta.values, color="b", label=delta.name, linewidth=0.5)

        plt.xlabel("Time [s]")
        plt.ylabel("{0:} [{1:}]".format("Difference", delta.unit))

        ampl = max(delta.values) - min(delta.values)
        ylim_lower = min(delta.values) - 1.02 * ampl
        # if ylim_lower == 0:
        #     ylim_lower = -0.1
        ylim_upper = max(delta.values) + 1.2 * ampl
        # if ylim_upper == 0:
        #     ylim_upper = 0.1
        plt.ylim([ylim_lower, ylim_upper])
        plt.xlim([signal_norm_ts[0], signal_norm_ts[-1]])
        # plt.xlim([200,signal_norm_ts[-1]])

        plt.grid()
        plt.legend(loc='upper right', ncol=2)

        plt.tight_layout()
        filename = "plot_{0:}.jpg".format(str(uuid.uuid1()))
        path = os.path.join(self.outdir, filename)
        plt.savefig(path)
        plt.close()

        return filename

    def difference_plot(self, signal_ref, signal, additional=None,
                        tolerance=None, title=""):
        """
        Produces an plot and a difference plot for the given signals.
        """

        diff = self._calc_difference(signal_ref, signal)

        # Align all signals to a common normalized time
        first_common_ts = max(signal.index.values[0],
                              signal_ref.index.values[0], diff.index.values[0])

        signal_norm_ts = []
        signal_ref_norm_ts = []
        diff_norm_ts = []
        # noinspection PyBroadException
        try:
            signal_norm_ts = self._normalize_timestamp(signal, first_common_ts)
            signal_ref_norm_ts = self._normalize_timestamp(signal_ref, first_common_ts)
            diff_norm_ts = self._normalize_timestamp(diff, first_common_ts)
        except:
            pass

        # Plot with 2 subplots
        plt.figure(num=None, figsize=(14, 6.2), dpi=240, facecolor='m', edgecolor='k')
        # Both signals
        plt.subplot(211)
        # plt.title(title)

        if ZOOM:
            mk = "x"
        else:
            mk = None

        plt.plot(signal_ref_norm_ts, signal_ref.values, color="r",
                 label=signal_ref.name, linewidth=0.5, linestyle="-", marker=mk, )
        plt.plot(signal_norm_ts, signal.values, color="b", label=signal.name,
                 linewidth=0.5, linestyle="-", marker=mk, )

        if additional is None:
            additional = []
        for a in additional:
            norm_ts = self._normalize_timestamp(a, first_common_ts)
            plt.plot(norm_ts, a.values, color="g", label=a.name, linewidth=0.5,
                     linestyle="-", marker=mk, )

        plt.xlabel("Time [s]")

        if signal.unit:
            plt.ylabel("[{0:}]".format(signal.unit))
        else:
            plt.ylabel("{0:}".format(title))
        # plt.xlim([signal_norm_ts[0],signal_norm_ts[-1]])

        if ZOOM:
            plt.xlim(ZOOM_LIMITS)
        else:
            plt.xlim([-0.2, signal_ref_norm_ts[-1] + 0.2])
        # plt.xlim([75, 85])

        # Calc the y-limits in a way that all data is displayed
        upper = max(max(signal.values), max(signal_ref.values))
        lower = min(min(signal.values), min(signal_ref.values))
        amplitude = upper - lower

        # 2.5% more
        upper += 0.28 * amplitude
        lower -= 0.05 * amplitude
        plt.ylim([lower, upper])
        plt.grid()
        plt.legend(loc='upper right', ncol=2 + len(additional))
        # plt.legend(bbox_to_anchor=(0., 1.03, 1., .102), loc=3, ncol=2,
        #            mode="expand", borderaxespad=0.01)

        plt.subplot(212)

        if ZOOM:
            mk = "x"
        else:
            mk = None
        plt.plot(diff_norm_ts, diff.values, color="b", label=diff.name,
                 linewidth=0.5, marker=mk, )

        if type(tolerance) is list:
            lbl = "Limits"
            for l in tolerance:
                plt.axhline(y=l, linewidth=1, color='r', linestyle="-",
                            label=lbl)
                lbl = None

        plt.xlabel("Time [s]")
        plt.ylabel("[{0:}]".format(diff.unit))

        if ZOOM:
            plt.xlim(ZOOM_LIMITS)
        else:
            plt.xlim([signal_norm_ts[0], signal_norm_ts[-1]])
        # plt.xlim([75, 85])

        # when limits are set only that data is relevant
        if tolerance is not None:
            upper = max(max(tolerance), diff.series.max())
            lower = min(min(tolerance), diff.series.min())
            amplitude = upper - lower

            upper += 0.28 * amplitude
            lower -= 0.05 * amplitude

            plt.ylim([lower, upper])

        plt.grid()
        plt.legend(loc='upper right', ncol=2)

        plt.tight_layout()
        filename = "plot_{0:}.jpg".format(str(uuid.uuid1()))
        path = os.path.join(self.outdir, filename)
        plt.savefig(path)
        plt.close()

        return filename

    @staticmethod
    def _shrink_signal(values, timestamp):
        """ Shrink the signal in the case, that there are multiply identical timestamps.
        :param values:
        :param timestamp:
        :return:
        """
        timestamp_1 = sorted(set(timestamp))

        if len(timestamp_1) == len(timestamp):
            return values, timestamp
        else:
            timestamp_2 = np.diff(timestamp)
            timestamp_3 = np.where(timestamp_2 != 0)
            values_1 = [values[0:timestamp_3[0][0]+1]]
            for ij in range(len(timestamp_3[0])-1):
                values_1.append(values[timestamp_3[0][ij]+1: timestamp_3[0][ij+1]+1])
            values_1.append(values[timestamp_3[0][-1]+1:])
            values_2 = []
            for ij in range(len(values_1)):
                values_2.append(values_1[ij][-1])                           # TEMPORARY SOLUTION FOR MULTIPLY TIMESTAMPS
            # diff_norm_ts2 = timestamp[timestamp_3[0]]
            # diff_norm_ts2 = np.append(diff_norm_ts2,timestamp[-1])

            return values_2, timestamp_1

    def histogram_plot(self, signal_ref, signal, signal_diff=None, additional=None, tolerance=None):
        """
        Produces a plot and a histogram plot for the given signals.
        """
        diff = self._calc_difference(signal_ref, signal)

        # Align all signals to a common normalized time
        first_common_ts = min(signal.index.values[0],
                              signal_ref.index.values[0])
        signal_norm_ts = []
        signal_ref_norm_ts = []
        diff_norm_ts = []
        # noinspection PyBroadException
        try:
            signal_norm_ts = self._normalize_timestamp(signal, first_common_ts)
            signal_ref_norm_ts = self._normalize_timestamp(signal_ref, first_common_ts)
            diff_norm_ts = self._normalize_timestamp(diff, first_common_ts)
        except:
            pass
        # Plot with 3 subplots
        plt.figure(num=None, figsize=(14, 8.7), dpi=240, facecolor='m', edgecolor='k')

        # Both signals
        plt.subplot(311)
        # plt.title(title)

        if ZOOM:
            mk = "x"
        else:
            mk = None

        # TEMPORARY SOLUTION FOR MULTIPLY TIMESTAMPS
        # ecu_signal, signal_ref_norm_ts = self._shrink_signal(signal_ref.values, signal_ref_norm_ts)
        # sil_signal, signal_norm_ts     = self._shrink_signal(signal.values,     signal_norm_ts)

        plt.plot(signal_ref_norm_ts, signal_ref.values, color="r",
                 label="ECU", linewidth=0.5, linestyle="-", marker=mk, )
        plt.plot(signal_norm_ts, signal.values, color="b",
                 label="SIL", linewidth=0.5, linestyle="-", marker=mk, )
        if additional is None:
            additional = []
        for a in additional:
            norm_ts = self._normalize_timestamp(a, first_common_ts)
            plt.plot(norm_ts, a.values, color="g", label=a.name, linewidth=0.5,
                     linestyle="-", marker=mk, )

        plt.xlabel("Time [s]")

        if signal.unit:
            plt.ylabel("{0:} [{1:}]".format(signal.name, signal.unit))
        else:
            plt.ylabel("{0:}".format(signal.name))

        if ZOOM:
            plt.xlim(ZOOM_LIMITS)
        else:
            plt.xlim([0, max(signal_ref_norm_ts[-1], signal_norm_ts[-1])])

        # Calc the y-limits in a way that all data is displayed
        upper = max(max(signal.values), max(signal_ref.values))
        lower = min(min(signal.values), min(signal_ref.values))
        amplitude = upper - lower

        # 2.5% more
        upper += 0.28 * amplitude
        lower -= 0.05 * amplitude
        plt.ylim([lower, upper])

        plt.grid()
        plt.legend(loc='upper right', ncol=2 + len(additional))

        # Diff-Plot
        plt.subplot(312)

        if ZOOM:
            mk = "x"
        else:
            mk = None

        # TEMPORARY SOLUTION FOR MULTIPLY TIMESTAMPS
        # diff_values, diff_index = self._shrink_signal(diff.values, diff_norm_ts)
        if signal_diff is not None:
            diff = signal_diff
            # noinspection PyBroadException
            try:
                diff_norm_ts = self._normalize_timestamp(diff, first_common_ts)
            except:
                pass

        if len(diff.values) > 0:

            diff_max = max(diff.values[50:-50])
            diff_min = min(diff.values[50:-50])

            tmp = sorted(diff[diff.values > 0])
            # diff_max = max(diff.values[50:-50])
            # diff_min = min(diff.values[50:-50])
            # tmp = sorted(diff[diff.values > 0])
            if len(tmp) > 0:
                diff_median_upper = tmp[(2*len(tmp)/3)]
            else:
                diff_median_upper = 0
            tmp = sorted(diff[diff.values < 0])
            if len(tmp) > 0:
                diff_median_lower = tmp[(2*len(tmp)/3)]
            else:
                diff_median_lower = 0
            diff_upper = min(diff_max+diff_max*0.05, max(diff_median_upper*len(diff[diff.values > 0])/len(diff),
                                                         max(min(4*diff_median_upper, 1), tolerance[1])))
            diff_lower = max(diff_min+diff_min*0.05, min(diff_median_lower*len(diff[diff.values < 0])/len(diff),
                                                         min(max(4*diff_median_lower, -1), tolerance[1])))
            tmp_upper = diff_upper
            tmp_lower = diff_lower
            if tmp_upper > 5 * abs(tmp_lower) and abs(tmp_lower) > 0:
                diff_upper = 5 * abs(tmp_lower)
            if abs(tmp_lower) > 5 * tmp_upper and tmp_upper > 0:
                diff_lower = 5 * tmp_upper
            min_l = 0
            max_l = 0
            if type(tolerance) is list:
                for l in tolerance:
                    if l < min_l:
                        min_l = l
                    if l > max_l:
                        max_l = l
                if min_l < max_l:
                    lbl = "Limits"
                    for l in tolerance:
                        plt.axhline(y=l, linewidth=1, color='r', linestyle="-", label=lbl)
                        lbl = None
            diff_upper = max(diff_upper, max_l * 1.25, 0.001)
            diff_lower = min(diff_lower, min_l * 1.25, -0.001)

            plt.plot(diff_norm_ts, diff.values, color="b", label="Delta", linewidth=0.5, marker=mk, )
            plt.ylim([diff_lower, diff_upper])

            plt.xlabel("Time [s]")

            plt.ylabel("Delta")
            diff_unit = "-"
            if ZOOM:
                plt.xlim(ZOOM_LIMITS)
            else:
                plt.xlim([0, max(signal_ref_norm_ts[-1], signal_norm_ts[-1])])

            if isinstance(diff, types.ListType):
                if diff.unit:
                    plt.ylabel("Delta [{0:}]".format(diff.unit))
                    diff_unit = diff.unit

            plt.grid()
            plt.legend(loc='upper right', ncol=2)

            # Histogram
            plt.subplot(313)

            if len(diff):
                if diff_min < diff_max:
                    plt.hist(diff.values, range=[diff_min, diff_max], align=u'left', color='g', bins=30,
                             normed=False, stacked=True, weights=None, log=True)
                else:
                    plt.plot([0, 0], [0, len(diff)], color="g", linewidth=3, linestyle="-")

                lower = min(diff.values)
                upper = max(diff.values)

            if type(tolerance) is list:
                for l in tolerance:
                    if l < min_l:
                        min_l = l
                    if l > max_l:
                        max_l = l
                if min_l < max_l:
                    lbl = "Limits"
                    for l in tolerance:
                        plt.axvline(x=l, linewidth=1, color='r', linestyle="-", label=lbl)
                        lbl = None
                        if l < lower:
                            lower = l
                        elif l > upper:
                            upper = l

            plt.xlabel("Delta ECU-SIL [{0:}]".format(diff_unit))
            plt.ylabel("Occurrences")

            plt.ylim(ymin=0.5)
            plt.grid()

            plt.tight_layout()
        filename = "histogram_plot_{0:}.jpg".format(str(uuid.uuid1()))
        path = os.path.join(self.outdir, filename)
        plt.rcParams["agg.path.chunksize"] = 10000
        plt.savefig(path)
        plt.close()

        return filename


class AlgoSignal(object):
    """
    Super simple plain object to shift data around
    """
    def __init__(self, name, values, index=None, unit=""):
        """ Constructs a signal. """
        super(AlgoSignal, self).__init__()
        self.log = logging.getLogger(self.__class__.__name__)
        self._name = name
        self._unit = unit
        if type(values) is pd.Series:
            self.series = values
        else:
            self.series = pd.Series(values, index=index)

    @property
    def name(self):
        """ Returns the signals name. """
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def values(self):
        """ Returns the signals values. """
        return self.series.values

    @property
    def index(self):
        """ Returns the signals index. """
        return self.series.index

    @property
    def unit(self):
        return self._unit

    def __add__(self, other):
        name = "{0:} + {1:}".format(self.name, other.name)
        series = self.series + other.series

        # since most of the time signals are time indexed we should take care of
        # missing timestamps in either self or other
        if True in pd.isnull(series):
            self.log.warning("Not all indexes are available in both signals. "
                             "Missing signals will be removed.")
            series = series[pd.isnull(series) == False]

        unit = self.unit
        return AlgoSignal(name, series, unit=unit)

    def __sub__(self, other):
        name = "{0:} - {1:}".format(self.name, other.name)
        series = self.series - other.series

        # since most of the time signals are time indexed we should take care of
        # missing timestamps in either self or other
        if True in pd.isnull(series):
            self.log.warning("Not all indexes are available in both signals. "
                             "Missing signals will be removed.")
            series[pd.isnull(series) == False] = -1

        unit = self.unit
        return AlgoSignal(name, series, unit=unit)

    def __abs__(self):
        return self.series.abs()

    def __len__(self):
        """ Override to allow to ask the container class directly for
            the number of objects, it has loaded.
        """
        return len(self.series)

    def __getitem__(self, item):
        """ Override to enable object iteration on the container itself,
            instead of calling container.objects or something.
        """
        return self.series.values[item]
