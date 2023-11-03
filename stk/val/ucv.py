"""
stk/val/ucv
-----------

Module for the UseCaseValidation.

usage Constraint Load over MeasID or ConstraintName
---------------------------------------------------
.. python::

    #Create Instance of Use Case Validator
    ucv = UseCaseValidator()

    #Load constraints based on a given measurement file or constraint name
    # and retrieve a class containing information on constraints,
    # which are needed to perform the UseCaseValidation
    # do either:
    MeasID = 35287
    CompData = ucv.loadConstraintsByMeasID(MeasID)

    # or:
    ConstraintName = "HLA_Blend_Time_CL"
    CompData = ucv.loadConstraintsByName(ConstraintName)

    # Now, get the Signal Data from VALF, BSIG, etc.
    # and fill it into the CompareData's class (Signal), e.g.:
    for idx in range(len(CompData.ID)):
        CompData.Signal[idx] = bsig.get_signal_by_name2(CompData.Signal[idx], CompData.Length[idx]):

    # Feed the SignalData back into the UseCaseValidation
    # and do the final compare.
    result = ucv.compare(CompData)

    if(result is True):
        print "Test passed!"
    else:
        print "Test failed!"


:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.7 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/05/09 10:40:10CEST $
"""

# pylint: disable=W0141,W0102,C0103,C0111

# SMe: C0111 = missing docstrings, W0102 = dangerous defaults

# Import Python Modules -----------------------------------------------------------------------------------------------
import numpy as np
import uuid
import os
import tempfile

# from matplotlib.pylab import plt
from matplotlib import gridspec, pylab as pyplt, path as mpath, patches as mpatches

# Local Imports -----------------------------------------------------------------------------------------------

import stk.db.cl.cl as cl
import stk.img.plot as stk_plot
from stk.util.helper import deprecation
from stk.util import Logger

# from stk.val.result_types import Signal

# Defines -------------------------------------------------------------------------------------------------------------

SHOW_PLOTS_DEFAULT = False

# Classes -------------------------------------------------------------------------------------------------------------

#  CompData class looks like following:
# class CompareData(object):
#     def __init__(self):
#         self.ID = []
#         self.MeasID = []
#         self.SigName = []
#         self.StartTS = []
#         self.EndTS = []
#         self.Signal = []
# Whereas each constraint is organized along one index,
# e.g. all data at index 0 belongs to first constraint.


class UseCaseValidator(object):
    """class for being able to validate use cases

    TODO: add more description...
    """

    def __init__(self, cl_connection, cat_connection=None):
        """
        UseCaseValidator uses BaseCLDB, which needs to be initialized outside.

        :param cl_connection: represents BaseCLDB object
        :param cat_connection: deprecated: represents BaseRecCatalogDB object
        """
        self._log = Logger(self.__class__.__name__)
        self._cld = cl_connection
        self._consSet = None

        self.__RecCatDB = cat_connection
        if self.__RecCatDB is not None:
            deprecation("Deprecated. Using catalogue and loading constraints by RecFileID will be removed.")

    def loadConstraintsByName(self, consSetName):
        """
        Load the Constraints from the Constraint DataBase.

        :param consSetName: constraint set name [str] or ID [int] or None.
        :return: True/False for successfull loading.
        """
        return self.loadConstraints(consSet=consSetName)

    def loadConstraintsByMeasID(self, measID):
        """
        Load the Constraints from the Constraint DataBase.

        :param measID: measurement to reference on. Integer = CAT number, str = recfilename.
        :return: True/False for successfull loading.
        """

        return self.loadConstraints(measid=measID)

    def loadConstraints(self, consSet=None, measid=None):
        """
        Load the Constraints from the Constraint DataBase.
        The selection for the correct ConstraintSet will be done via
        the MeasID or constraint set name.

        :param consSet: constraint set name [str] or ID [int] or None.
        :param measid: measurement to reference on. Integer = CAT number, deprecated: str = recfilename.
        :return: True/False for successfull loading.
        """
        if isinstance(measid, str):
            if self.__RecCatDB is None:
                measid = None
                deprecation("Deprecated. Catalogue connection missing. RecFileID is ignored. Please provide measid.")

            else:
                measid = self.__RecCatDB.GetMeasurementID(measid)
                deprecation("Deprecated. RecFileID converted to measid, but please provide measid in the future!")
        try:
            self._consSet = self._cld.get_constraints(consSet, measid)
        except cl.BaseCLDBException:
            self._consSet = []

        value_dict = {}
        for consSet in self._consSet:
            value_dict[consSet.ident] = {}
            value_dict[consSet.ident][cl.KID_NAME_SETID] = consSet.ident
            value_dict[consSet.ident][cl.KID_NAME_KIDIDS] = consSet.all_kid_ids
            value_dict[consSet.ident].update(consSet.value)

        # sigcons = type('CompareData', (), value_dict)
        sigcons = value_dict

        return sigcons

    def getConstraintSignals(self):
        """
        Get all signal ids and names that belong to the current constraint set

        :return: signals {dict}
        """
        signals = {}
        for cons_set in self._consSet:
            for values_per_subset in cons_set.values:

                # get constraints
                # TODO: replace magic numbers
                constr_list = values_per_subset[1][cl.KID_VALUENAME_CONSTRAINTS]
                for constr in constr_list:

                    # get one signal
                    sig_id = constr[cl.COL_NAME_SIGCON_SIGNALID]
                    if not sig_id in signals:
                        sig_details = self._cld.get_cons_signal(sig_id)
                        signals[sig_id] = sig_details[0][cl.COL_NAME_CONSIG_NAME]

        return signals

    def compare(self):
        """
        Perform a comparision between the internal loaded constraints
        and the Signal Data

        :return: True/False (Comparision Result)
        """
        result = []

        # evaluate kids
        for cons_index in range(len(self._consSet)):
            self._consSet[cons_index].eval_kids(self.checkConstrSet)
            result.append(self._consSet[cons_index].result)

        return result

    def addCompareData(self, compData):
        """Add given input data to Trie

        :compData: input data to compare [dict]
        """

        # check data format
        trigger_length = len(compData[cl.KID_VALUENAME_SIGNALS][cl.SIGCON_DEFAULT_TRIGGER])
        signals = compData[cl.KID_VALUENAME_SIGNALS].keys()
        signals.remove(cl.SIGCON_DEFAULT_TRIGGER)
        for signal in signals:
            signal_length = len(compData[cl.KID_VALUENAME_SIGNALS][signal])
            if not signal_length == trigger_length:
                self._log.warning('Signal %s has only %d elements, but %d expected'
                                  % (signal, signal_length, trigger_length))

        # append the signal from compData to the kid
        # TODO: what if compData belongs only to special kid?
        # for idx in xrange(len(compData.ID)):
        for cons_index in range(len(self._consSet)):
            for set_id in self._consSet[cons_index].all_ids:
                # if compData.Signal != []:
                    # self._consSet.appendValue(compData.ID[idx], compData.Signal[idx])
                self._consSet[cons_index].append_value(set_id, compData)

        return

    def _getCompareResultDetails(self, consSets):
        """generate overview about all compare results and its logical operant in one constraint set

        :param consSets: constraint set from with get its detailed results [trie object]
        :return details: compare result details [dict]
        """
        details = []

        for consSet in consSets:
            details.append({})

            operant = cl.CL_OP_NAME_MAP[consSet.value[cl.KID_VALUENAME_OPERANT]]
            sum_ = consSet.value[cl.KID_VALUENAME_COMP_RESULTS][cl.KID_VALUENAME_COMP_SUM]
            comp_ = consSet.value[cl.KID_VALUENAME_COMP_RESULTS][cl.KID_VALUENAME_COMP_DETAILS]
            details[-1][consSet.ident] = {cl.KID_VALUENAME_OPERANT: operant,
                                          cl.KID_VALUENAME_CONSTRAINTS: {},
                                          cl.KID_VALUENAME_COMP_SUM: sum_,
                                          cl.KID_VALUENAME_COMP_DETAILS: comp_}

            for constraint in consSet.value[cl.KID_VALUENAME_CONSTRAINTS]:

                constr_info = {constraint[cl.COL_NAME_SIGCON_CONSID]: {constraint[cl.COL_NAME_CONSIG_NAME]:
                                                                       constraint[cl.KID_VALUENAME_COMP_RESULTS]}}

                details[-1][consSet.ident][cl.KID_VALUENAME_CONSTRAINTS].update(constr_info)

            for kid in consSet.kids:
                details[-1][consSet.ident][cl.KID_VALUENAME_COMP_DETAILS].append({kid.ident: kid.result})
                details[-1].update(self._getCompareResultDetails([kid])[0])

        return details

    def getCompareResultDetails(self):
        """
        Return a List of classes with details of every constrain set.

        Every Class should contain:
            - Constriaint ID
            - Pass/Fail Result
            - Timestamp info where first failed happened.
            - .....

        :return: List of Classes
        """
        # TODO: depends on the outcome of checkConstraint

        details = self._getCompareResultDetails(self._consSet)

        return details

    def checkConstraint(self, consSet_values):  # pylint: disable=R0201
        """check all constraints of one set

        :param consSet_values: one set to compare
        :return: true/false or None if compare was not performed properly
        :TODO in future:
                0 - passed
                1 - ... TODO
                etc
        """
        # TODO: WARNING: consSet_values is a reference to self._consSet.value - that is used to return check results!

        return_result = None
        check_results = []

        for cons in consSet_values[cl.KID_VALUENAME_CONSTRAINTS]:

            cons_signal_name = self._cld.get_cons_signal(cons[cl.COL_NAME_SIGCON_SIGNALID])
            cons_signal_name = cons_signal_name[0][cl.COL_NAME_CONSIG_NAME]

            if cons_signal_name in consSet_values[cl.KID_VALUENAME_SIGNALS]:

                # build up comp_signal = input signal
                cons_begin_time = cons[cl.COL_NAME_SIGCON_BEGINTS]
                cons_end_time = cons[cl.COL_NAME_SIGCON_ENDTS]

                # use this if timestamp is not matching exactly
                time = np.array(consSet_values[cl.KID_VALUENAME_SIGNALS][cl.SIGCON_DEFAULT_TRIGGER])

                try:
                    begin_index = (consSet_values[cl.KID_VALUENAME_SIGNALS][cl.SIGCON_DEFAULT_TRIGGER]
                                   .index(cons_begin_time))
                except ValueError:  # exact cons_begin_time not in list
                    after_begin = np.where(time >= cons_begin_time)
                    if len(after_begin[0]) < 1:
                        begin_index = None
                    else:
                        begin_index = after_begin[0][0]

                try:
                    end_index = (consSet_values[cl.KID_VALUENAME_SIGNALS][cl.SIGCON_DEFAULT_TRIGGER]
                                 .index(cons_end_time))
                except ValueError:  # exact cons_end_time not in list
                    before_end = np.where(time <= cons_end_time)
                    if len(before_end[0]) < 1:
                        end_index = None
                    else:
                        end_index = before_end[0][-1]

                if begin_index is None or end_index is None or begin_index > end_index:
                    self._log.warning('base signal "%s" has no overlap with constraint %d - investigate'
                                      % (cl.SIGCON_DEFAULT_TRIGGER, cons[cl.COL_NAME_SIGCON_CONSID]))

                    check_results.append(None)
                    cons[cl.KID_VALUENAME_COMP_RESULTS] = None
                    continue

                comp_signal = consSet_values[cl.KID_VALUENAME_SIGNALS][cons_signal_name][begin_index:end_index + 1]

                if len(comp_signal) == 0:
                    self._log.warning('signal "%s" has no overlap with constraint %d - investigate'
                                      % (cons_signal_name, cons[cl.COL_NAME_SIGCON_CONSID]))

                    check_results.append(None)
                    cons[cl.KID_VALUENAME_COMP_RESULTS] = None
                    continue

                # degenerate constraint - usually means ground truth trouble
                if begin_index == end_index:
                    self._log.warning('degenerate constraint %d - investigate'
                                      % cons[cl.COL_NAME_SIGCON_CONSID])
                    check_results.append(None)
                    cons[cl.KID_VALUENAME_COMP_RESULTS] = None
                    continue

                # build up cons_signal = constraint signal
                slope = float(cons[cl.COL_NAME_SIGCON_COEFA])
                y_intercept = float(cons[cl.COL_NAME_SIGCON_COEFB])
                cons_signal = np.zeros(len(comp_signal))
                # TODO: change calculation of cons_signal to use timestamps instead of indexes
                for i in range(len(cons_signal)):
                    cons_signal[i] = slope * i + y_intercept

                # evaluate upper and lower boundary

                # problem with upper / lower bounds with extreme slope
                # we could use e.g. constraint[2|3] = ca / math.cos(math.atan(constraint[2|3]))
                # where constraint[2] = cons[cl.COL_NAME_SIGCON_UPPERTOL]
                #       constraint[3] = cons[cl.COL_NAME_SIGCON_LOWERTOL]
                uCons = cons_signal + cons[cl.COL_NAME_SIGCON_UPPERTOL]
                lCons = cons_signal - cons[cl.COL_NAME_SIGCON_LOWERTOL]

                # compare if each value of comp_signal is in range of lower and upper bound
                cmpRes = (lCons <= comp_signal) & (comp_signal <= uCons)

                # evaluate min and max valid consecutive samples
                min_samples = cons[cl.COL_NAME_SIGCON_MINSAMPLES]
                max_samples = cons[cl.COL_NAME_SIGCON_MAXSAMPLES]

                # TODO: both 0 or both None?
                if min_samples + max_samples == 0:  # if not given, all values must be in range
                    result = sum(cmpRes) == len(comp_signal)

                else:
                    # check min and max of consecutives
                    cmpRes = np.convolve(cmpRes, np.concatenate([np.ones(min_samples, dtype=int),
                                                                 np.zeros(len(comp_signal) - min_samples, dtype=int)]))
                    mx = cmpRes.max()  # max lenght of consecutive samples inside bounds
                    result = mx == min_samples and (cmpRes == mx).sum() + mx - 1 <= max_samples

                # collect results of each constraint in this set
                check_results.append(result)
                cons[cl.KID_VALUENAME_COMP_RESULTS] = bool(result)

            else:
                self._log.warning('signal "%s" to compare not given, skip the constraint %d'
                                  % (cons_signal_name, cons[cl.COL_NAME_SIGCON_CONSID]))

                # collect results of each constraint in this set
                check_results.append(None)
                cons[cl.KID_VALUENAME_COMP_RESULTS] = None

        # get overall result
        if len(check_results) > 0 and not None in check_results:
            return_result = eval(cl.CL_OP_FUNC_MAP[consSet_values[cl.KID_VALUENAME_OPERANT]] % check_results)
        else:
            return_result = None

        # save results to self
        consSet_values[cl.KID_VALUENAME_COMP_RESULTS][cl.KID_VALUENAME_COMP_DETAILS] = check_results
        consSet_values[cl.KID_VALUENAME_COMP_RESULTS][cl.KID_VALUENAME_COMP_SUM] = return_result

        # return
        return return_result

    def checkConstrSet(self, constr_set_trie):
        """check all constraints in a trie

        :param constr_set_trie: one trie to compare
        :return: true/false
        :TODO in future:
                0 - passed
                1 - ... TODO
                etc
        """

        self.checkConstraint(constr_set_trie.value)
        details = constr_set_trie.value[cl.KID_VALUENAME_COMP_RESULTS][cl.KID_VALUENAME_COMP_DETAILS]

        kid_results = []
        all_kids = constr_set_trie.kids
        for kid in all_kids:
            kid_results.append(kid.result)

        all_results = details + kid_results

        # get overall result
        if len(all_results) > 0 and not None in all_results:
            return_result = eval(cl.CL_OP_FUNC_MAP[constr_set_trie.value[cl.KID_VALUENAME_OPERANT]] % all_results)
        else:
            return_result = None

        return return_result

    # =================================================================================================================
    # constraint handling
    # =================================================================================================================

    def retrieveConstraints(self, measID):
        """retrieves all constraints by given measurement id

        :param measID: measurement ID
        """
        return self._cld.getConstraintsByMeas(measID)


class UcvPlot(UseCaseValidator):
    """
    Visualize constraints only.  No handling of signals.  Connection to a DB is necessary to get a grip on constraint
    sets, since they don't have a python representation like single constraints do (single constraints are lists of
    dicts).  Relies heavily on the stk ValidationPlot class.  Matplotlib axes resp. stk_plot.ValidationPlot instances
    can be passed to most functions (as parameter axes resp. plotter) to add constraint visualization to these
    axes/plots.  Check test_add_constraint_plot_to_signal_plot from test_ucv_plot.py for an example.
    """

    def __init__(self, cl_connection):
        UseCaseValidator.__init__(self, cl_connection)
        self.constraint_line_color = ['b']
        self.constraint_line_style = ['--']
        self._db = cl_connection

    def __del__(self):
        pass

    def GetTableData(self, data_dicts, head_dict):  # pylint: disable=R0201
        """Choose only data given in head_dict from data_dicts and change names in data for "nice names" for report.

        :param data_dicts: all data
        :format [{key1: value1a, key2: value2a, key3: value3a, ...},
                 {key1: value1b, key2: value2b, key3: value3b, ...}]
        :param head_dict: dict with keys to use from data_dicts and names to use in table
        :format {key1_nice: key1, key3_nice: key3, ...}
        :return table_data: data to show in table
        :format [{key1_nice: value1a, key3_nice: value3a, ...},
                 {key1_nice: value1b, key3_nice: value3b, ...}]
        """
        table_data = []

        for data_dict in data_dicts:
            row_dict = {}
            for head_key in head_dict:
                row_dict[head_key] = data_dict[head_dict[head_key]]
            table_data.append(row_dict)

        return table_data

    def GetConstraintLineColor(self):
        return self.constraint_line_color

    def GetConstraintLineStyle(self):
        return self.constraint_line_style

    def SetConstraintLineColor(self, index):
        self.constraint_line_color = stk_plot.DEF_COLORS[index]

    def SetConstraintLineStyle(self, index):
        self.constraint_line_style = stk_plot.DEF_LINE_STYLES[index]

    def PlotConstrSetCheckAll(self, measid=None, show_plots=SHOW_PLOTS_DEFAULT, ttc_info=None):
        """
        :param ttc_info: optional: list with timestamp and ttc values - if None given deactivated
        :format [[timestamp1, timestamp2, timestamp3, ...],
                 [ttc1, ttc2, ttc3, ...]]
        """
        drawings = []

        for cons_set in self._consSet:
            constr_list = cons_set.value[cl.KID_VALUENAME_CONSTRAINTS]

            for cntr, constr in enumerate(constr_list):
                signal_name = constr[cl.COL_NAME_CONSIG_NAME]

                data_missing = False
                if signal_name in cons_set.value[cl.KID_VALUENAME_SIGNALS]:
                    signal_values = cons_set.value[cl.KID_VALUENAME_SIGNALS][signal_name]
                else:
                    data_missing = True
                if cl.SIGCON_DEFAULT_TRIGGER in cons_set.value[cl.KID_VALUENAME_SIGNALS]:
                    time_values = cons_set.value[cl.KID_VALUENAME_SIGNALS][cl.SIGCON_DEFAULT_TRIGGER]
                else:
                    data_missing = True

                if not data_missing:

                    if measid:
                        plot_title = '%s_measurement_%d_cons-id_%d' % (signal_name, measid,
                                                                       constr[cl.COL_NAME_SIGCON_CONSID])
                    else:
                        plot_title = '%s_cons-id_%d' % (signal_name, constr[cl.COL_NAME_SIGCON_CONSID])

                    self._log.debug("Creating fresh figure instance.")
                    gs = gridspec.GridSpec(1, 1)
                    figure = pyplt.figure(figsize=(10, 3), dpi=96, facecolor='w', edgecolor='k')
                    ax = figure.add_subplot(gs[0, 0])

                    # ax.set_title(plot_title)
                    ax.set_xlabel('MTS.Package.TimeStamp')
                    ax.xaxis.set_label_coords(0.5, -0.155)

                    ax.grid(color="#333333", linestyle='-', linewidth=0.5)
                    ax.grid(which="minor", color="#666666", linestyle='-', linewidth=0.25)

                    # Plot the constraint
                    x, y = self.ConstructConstraintBox(constr, True)
                    path = mpath.Path
                    path_data = [
                        (path.MOVETO, (x[0], y[0])),
                        (path.LINETO, (x[1], y[1])),
                        (path.LINETO, (x[2], y[2])),
                        (path.LINETO, (x[3], y[3])),
                        (path.CLOSEPOLY, (x[0], y[0])),
                    ]
                    codes, verts = zip(*path_data)
                    path = mpath.Path(verts, codes)
                    patch = mpatches.PathPatch(path, fill=True, edgecolor="#FF0000", facecolor='#FF0000',
                                               alpha=0.5, linewidth=0.5)
                    ax.add_patch(patch)

                    ax.plot(time_values, signal_values)

                    # Create the limits based on the constraint boundaries
                    ax.set_xlim([min(x) - 0.5 * 1e6, max(x) + 0.5 * 1e6])
                    ax.set_ylim([min(y) - 0.5, max(y) + 0.5])

                    if ttc_info is not None:

                        ax2 = ax.twiny()
                        ax1Xs = ax.get_xticks()

                        ax2Xs = []
                        for X in ax1Xs:
                            ttc_np = np.array(ttc_info[0])
                            time_idx = (np.abs(ttc_np - X)).argmin()
                            ax2Xs.append(ttc_info[1][time_idx])

                        ax2.set_xticks(ax1Xs)
                        ax2.tick_params(pad=2)  # set space between tick and ticklabel
                        ax2.set_xbound(ax.get_xbound())
                        ax2.set_xticklabels(ax2Xs)
                        ax2.set_xlabel('TTC [s]')
                        ax2.xaxis.set_label_coords(0.5, 1.155)

                    img_filename = "{}.jpeg".format(uuid.uuid1())
                    out_path = os.path.join(tempfile.gettempdir(), img_filename)
                    figure.set_tight_layout(True)
                    figure.savefig(out_path, format="jpeg")

                    if show_plots:
                        pyplt.show()
                    pyplt.close()

                    # Add to drawings for compatibility
                    drawings.append((out_path, plot_title, None))

        return drawings

    def PlotConstraints(self, constraint_list, constraint_names=[], x_label='t [s]',  # pylint: disable=R0913
                        y_label='tbd', titles=[''], show_grid=False, show_plots=SHOW_PLOTS_DEFAULT,
                        single_figures=False, keep_time_offset=True, axes=None, plotter=None):
        """
        Plot boxes to visualize constraints.

        :param constraint_list: the constraints.
        :type constraint_list: list of lists of dict
        :param constraint_names: names for legend
        :param x_label: x-axis label
        :param y_label: y-axis label
        :param titles: list of plot titles (list with one item if single_figures == False)
        :param show_grid: figure property for grid display
        :param show_plots: show the figure or figures
        :param single_figures: True gives one figure window per constraint,
            False gives one plot with ALL constraints combined
        :param keep_time_offset: if true use original constraint time stamps,
            else plot in interval [0, endts - begints]
        :param axes: axis on which the plot is fixed, necessary for connection to self.SubplotConstraints()
        :param plotter: stk_plot.ValidationPlot() object for which the plot is generated, necessary for connection to
            self.SubplotConstraints()
        """
        bool_legend = False
        if constraint_names:
            bool_legend = True
        if single_figures:
            if plotter is None:
                plotter = stk_plot.ValidationPlot()
            for i, single_constraint in enumerate(constraint_list):
                x, y = self.ConstructConstraintBox(single_constraint, keep_time_offset)
                if axes is None:
                    axes_new = plotter.generate_figure(show_grid=show_grid)
                else:
                    axes_new = axes
                plt = plotter.generate_plot([zip(x, y)], [constraint_names[i]], x_label, y_label, bool_line=True,
                                            title=titles[i], bool_legend=bool_legend,
                                            line_colors=self.constraint_line_color,
                                            line_styles=self.constraint_line_style, axes=axes_new)
        else:  # not single_figures
            if plotter is None:
                plotter = stk_plot.ValidationPlot()
            data = []
            for single_constraint in constraint_list:
                xx, yy = self.ConstructConstraintBox(single_constraint, keep_time_offset)
                data.append([(xx[i], yy[i]) for i in range(len(xx))])
            if axes is None:
                axes = plotter.generate_figure(show_grid=show_grid)
            plt = plotter.generate_plot(data, constraint_names, x_label, y_label, title=titles[0], bool_line=True,
                                        bool_legend=bool_legend, line_colors=len(data) * self.constraint_line_color,
                                        line_styles=len(data) * self.constraint_line_style, axes=axes)
# adding the autoscale command gives extra empty figures!
#        plt.autoscale(tight=True)
        if show_plots:
            plt.show()

        return plt

    def SubplotConstraints(self, constraint_list, n_rows=1, n_cols=1, n_plots_per_subplot=[1],  # pylint: disable=R0913
                           constraint_names=[[]], x_labels=['t [s]'], y_labels=['tbd'], show_grid=[False],
                           show_plots=SHOW_PLOTS_DEFAULT, keep_time_offset=True,  # pylint: disable=W0613
                           plotter=None):
        """
        Visualize a list of linear constraints in one figure with subplots.  Input parameters are lists of input
        parameters for self.PlotConstraints().  Figure title is the concatenation of constraint names.

        :param constraint_list: list of lists of linear constraints, one list of constraints for each subplot
        :type constraint_list: list of list of list of dict
        :type constraint_names: list of lists
        :type x_labels: list of strings
        :type y_labels: list of strings
        :param n_rows: number of rows for the figure
        :param n_cols: number of columns for the figure
        :param n_plots_per_subplot: number of plots for each subplot
        :type n_plots_per_subplot: list of ints
        :param show_grid: list bools to show grids or not
        :param show_plots: show the figure or not
        :param keep_time_offset: if true use original constraint time stamps,
            else plot in interval [0, endts - begints]
        :param plotter: stk_plot.ValidationPlot() object for which the plot is generated, necessary for connection to
            self.PlotConstraints()
        """
        # TODO: HOW MUCH DO I HAVE TO CATCH??
        for i, n_plots in enumerate(n_plots_per_subplot):
            if constraint_names and n_plots != len(constraint_names[i]):
                raise IndexError('Number of plots does not match number of constraint names! ' +
                                 'n_plots_per_subplot[i] must equal len(constraint_names[i])')
            if n_plots != len(constraint_list[i]):
                raise IndexError('Number of plots does not match number of constraints! ' +
                                 'n_plots_per_subplot[i] must equal len(constraint_list[i])')

        subplot_layout = [100 * n_rows + 10 * n_cols + i for i in range(1, n_rows * n_cols + 1)]
        if plotter is None:
            plotter = stk_plot.ValidationPlot()
        axes = plotter.generate_figure(subplots=subplot_layout, show_grid=show_grid)
        if constraint_names:
            # bool_legend = True
            pass
        else:
            # bool_legend = True
            concat_title = ''
            constraint_names = [[] for i in range(len(axes))]

        for i in range(len(constraint_list)):
            concat_title = [constraint_name_list for constraint_name_list in constraint_names[i]]
            plt = self.PlotConstraints(constraint_list[i], constraint_names=constraint_names[i],
                                       x_label=x_labels[i], y_label=y_labels[i], titles=[concat_title],
                                       show_plots=False, single_figures=False,
                                       keep_time_offset=False, axes=axes[i], plotter=plotter)
        if show_plots:
            plt.show()

        return plt

    def SubplotConstraints_via_ids(self, constraint_ids_list, n_plots_per_subplot, show_plots=SHOW_PLOTS_DEFAULT,
                                   single_figures=False, keep_time_offset=True):  # pylint: disable=W0613
        """
        Like self.SubplotConstraints(), with constraint IDs instead of a constraint list.

        :type constraint_ids_list: list of int
        """
        constraint_list = []
        constraint_names = []
        x_labels = []
        y_labels = []
        for _, single_constraint_id in enumerate(constraint_ids_list):
            single_constraint = self._db.get_sig_constraint(single_constraint_id)
            # each constraint fills only one subplot, so it is the only item in the list representing that subplot
            constraint_list.append([single_constraint])
            constraint_names.append([str(single_constraint[0][cl.COL_NAME_SIGCON_CONSID])])
            x_labels.append('t [ms]')
            y_labels.append('tbd')

        plt = self.SubplotConstraints(constraint_list=constraint_list,
                                      n_rows=len(constraint_list), n_cols=1, n_plots_per_subplot=n_plots_per_subplot,
                                      constraint_names=constraint_names, x_labels=x_labels, y_labels=y_labels,
                                      show_grid=len(constraint_list) * [False], show_plots=show_plots,
                                      keep_time_offset=keep_time_offset)
        return plt

    def PlotConstraintsViaIds(self):
        pass

    def PlotConstraintSet(self):
        pass

    def SubplotConstraintSet(self, constraint_set_id, keep_time_offset=True, show_plots=SHOW_PLOTS_DEFAULT):
        """
        Use the information contained in a constraint set to plot all signal constraints contained in the set.  Child
        sets are not taken care of.

        In lack of better ideas, the figure that is constructed here consists of one column of subplots, one subplot
        for each constraint.

        :param constraint_set_id: get this from a DB, e.g. using cl.getConstraintSetIDs()
        :param keep_time_offset: if true use original constraint time stamps,
            else plot in interval [0, endts - begints]
        :param show_plots: switch this off to not call show() from the matplotlib.pyplot handle
        """
        constraint_set_maps = self._db.get_cons_map(constraint_set_id, col=cl.COL_NAME_CONMAP_SETID)
        constraint_list = []
        constraint_names = []
        x_labels = []
        y_labels = []
        for _, constraint_set_map in enumerate(constraint_set_maps):
            single_constraint_id = constraint_set_map[cl.COL_NAME_CONMAP_CONSID]
            single_constraint = self._db.get_sig_constraint(single_constraint_id)
            # each constraint fills only one subplot, so it is the only item in the list representing that subplot
            constraint_list.append([single_constraint])
            constraint_names.append([str(single_constraint[0][cl.COL_NAME_SIGCON_CONSID])])
            x_labels.append('t [ms]')
            y_labels.append('tbd')

        # OLIVER: for now, make one figure with subplots in one column
        plt = self.SubplotConstraints(constraint_list=constraint_list,
                                      n_rows=len(constraint_list), n_cols=1,
                                      n_plots_per_subplot=len(constraint_list) * [1],
                                      constraint_names=constraint_names, x_labels=x_labels, y_labels=y_labels,
                                      show_grid=len(constraint_list) * [False], show_plots=show_plots,
                                      keep_time_offset=keep_time_offset)
        return plt

    def ConstructConstraintBox(self, single_constraint, keep_time_offset):
        """
        Construct the data field for the generate_plot function of class ucv_plot
        for visualizing a constraint as a box, something like this:                 +----------+
                                                                                    |          |
                                                                                    |          |
                                                                                    +----------+

        :param single_constraint: the constraint to visualize
        :type single_constraint: list of dict, e.g. [{'LOWERTOL': 0.0, 'COEFFB': ...}]
        :param keep_time_offset: True to plot from begints to endts, False to plot starting at 0
        """
        # TODO: why using list as single_constraint?
        if isinstance(single_constraint, list):
            single_constraint = single_constraint[0]

        if not isinstance(single_constraint, dict):
            self._log.warning('Input format no list or dict: %s. Might lead to errors.' % single_constraint)

        begints = single_constraint[cl.COL_NAME_SIGCON_BEGINTS]
        endts = single_constraint[cl.COL_NAME_SIGCON_ENDTS]
        coeffa = single_constraint[cl.COL_NAME_SIGCON_COEFA]
        coeffb = single_constraint[cl.COL_NAME_SIGCON_COEFB]
        uppertol = single_constraint[cl.COL_NAME_SIGCON_UPPERTOL]
        lowertol = single_constraint[cl.COL_NAME_SIGCON_LOWERTOL]
        if keep_time_offset:
            x = [begints, begints, endts, endts, begints]
            y = [coeffb + uppertol, coeffb - lowertol,
                 coeffa * endts + coeffb - lowertol, coeffa * endts + coeffb + uppertol,
                 coeffb + uppertol]
        else:
            t_end = endts - begints
            x = [0, 0, t_end, t_end, 0]
            y = [coeffb + uppertol, coeffb - lowertol,
                 coeffa * t_end + coeffb - lowertol, coeffa * t_end + coeffb + uppertol,
                 coeffb + uppertol]
        return x, y


"""
CHANGE LOG:
-----------
$Log: ucv.py  $
Revision 1.7 2016/05/09 10:40:10CEST Hospes, Gerd-Joachim (uidv8815) 
fix memory problem by closing figure, 
change name of imported module plt, 
user tested (no module test)
Revision 1.6 2015/12/14 10:03:50CET Hospes, Gerd-Joachim (uidv8815)
back to rev. 1.2 without plot optimisation, but leaving pep8/pylint fixes
Revision 1.5 2015/12/09 17:16:59CET Hospes, Gerd-Joachim (uidv8815)
pep8 fix
Revision 1.4 2015/12/09 17:04:25CET Hospes, Gerd-Joachim (uidv8815)
remove setting y-axis to dynamic boundaries again, only needed for VW
Revision 1.3 2015/12/07 17:09:55CET Mertens, Sven (uidv7805)
removing last pep8 errors
Revision 1.2 2015/07/09 18:17:02CEST Hospes, Gerd-Joachim (uidv8815)
update y-axis to dynamic boundaries
- Added comments -  uidv8815 [Jul 9, 2015 6:17:03 PM CEST]
Change Package : 355746:1 http://mks-psad:7002/im/viewissue?selection=355746
Revision 1.1 2015/04/23 19:05:40CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/val/project.pj
Revision 1.53 2015/01/28 18:19:26CET Ellero, Stefano (uidw8660)
Removed all img and plot based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 28, 2015 6:19:27 PM CET]
Change Package : 296835:1 http://mks-psad:7002/im/viewissue?selection=296835
Revision 1.52 2015/01/23 21:44:19CET Ellero, Stefano (uidw8660)
Removed all util based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 23, 2015 9:44:20 PM CET]
Change Package : 296837:1 http://mks-psad:7002/im/viewissue?selection=296837
Revision 1.51 2014/12/16 19:22:59CET Ellero, Stefano (uidw8660)
Remove all db.obj based deprecated function usage inside STK and module tests.
--- Added comments ---  uidw8660 [Dec 16, 2014 7:23:00 PM CET]
Change Package : 281278:1 http://mks-psad:7002/im/viewissue?selection=281278
Revision 1.50 2014/12/10 16:28:46CET Ellero, Stefano (uidw8660)
Remove all db.cl based deprecated function usage inside stk and module tests
--- Added comments ---  uidw8660 [Dec 10, 2014 4:28:47 PM CET]
Change Package : 281274:1 http://mks-psad:7002/im/viewissue?selection=281274
Revision 1.49 2014/11/20 13:47:01CET Baust, Philipp (uidg5548)
Fix: Plot signal in PlotConstrSetCheckAll
--- Added comments ---  uidg5548 [Nov 20, 2014 1:47:02 PM CET]
Change Package : 281165:1 http://mks-psad:7002/im/viewissue?selection=281165
Revision 1.48 2014/10/20 13:08:51CEST Skerl, Anne (uid19464)
*bugfix in PlotConstrSetCheckAll, avoid double plotnames if several sets are given
--- Added comments ---  uid19464 [Oct 20, 2014 1:08:52 PM CEST]
Change Package : 271545:1 http://mks-psad:7002/im/viewissue?selection=271545
Revision 1.47 2014/10/16 18:54:34CEST Skerl, Anne (uid19464)
*from UseCaseValidator.compare() return result as list to be able to handle several constraint sets per recording
--- Added comments ---  uid19464 [Oct 16, 2014 6:54:35 PM CEST]
Change Package : 271545:1 http://mks-psad:7002/im/viewissue?selection=271545
Revision 1.46 2014/10/14 19:16:24CEST Skerl, Anne (uid19464)
*add option in PlotConstrSetCheckAll() to show TTC values on upper x axis
--- Added comments ---  uid19464 [Oct 14, 2014 7:16:25 PM CEST]
Change Package : 271543:1 http://mks-psad:7002/im/viewissue?selection=271543
Revision 1.45 2014/09/25 13:29:05CEST Hospes, Gerd-Joachim (uidv8815)
adapt stk.img files to style guide, new names used in all modules and tests except stk.img tests
--- Added comments ---  uidv8815 [Sep 25, 2014 1:29:06 PM CEST]
Change Package : 264203:1 http://mks-psad:7002/im/viewissue?selection=264203
Revision 1.44 2014/09/18 11:11:36CEST Hospes, Gerd-Joachim (uidv8815)
fix to get correct warning for degenerated constraints, added test
--- Added comments ---  uidv8815 [Sep 18, 2014 11:11:36 AM CEST]
Change Package : 264200:1 http://mks-psad:7002/im/viewissue?selection=264200
Revision 1.43 2014/08/13 11:34:34CEST Weinhold, Oliver (uidg4236)
Handle degenerate constraints (begin ts == end ts): set result to None.
--- Added comments ---  uidg4236 [Aug 13, 2014 11:34:34 AM CEST]
Change Package : 244342:16 http://mks-psad:7002/im/viewissue?selection=244342
Revision 1.41 2014/05/08 16:14:44CEST Skerl, Anne (uid19464)
*change PlotConstrSetCheckAll(): change creation of plot name generation
*add comment
--- Added comments ---  uid19464 [May 8, 2014 4:14:44 PM CEST]
Change Package : 234186:1 http://mks-psad:7002/im/viewissue?selection=234186
Revision 1.40 2014/05/08 15:55:02CEST Skerl, Anne (uid19464)
*change PlotConstrSetCheckAll(): add counter to constraint plot names to ensure unique names
--- Added comments ---  uid19464 [May 8, 2014 3:55:02 PM CEST]
Change Package : 234186:1 http://mks-psad:7002/im/viewissue?selection=234186
Revision 1.39 2014/05/06 15:40:52CEST Skerl, Anne (uid19464)
*substract lower tolerance -> value in db must be positive
*change calculation of signal slice to validate
Revision 1.38 2014/04/30 18:18:14CEST Skerl, Anne (uid19464)
class UseCaseValidator, checkConstraint():
*set result of the constraint to "None" if no data available
*set result of the constraint set to "None" if one single result is "None"

class UcvPlot, PlotConstrSetCheckAll():
*limit signal plot to real min/max values
*return also ValidationPlot object to add to result API
--- Added comments ---  uid19464 [Apr 30, 2014 6:18:15 PM CEST]
Change Package : 234186:1 http://mks-psad:7002/im/viewissue?selection=234186
Revision 1.37 2014/02/19 17:56:57CET Skerl, Anne (uid19464)
*use dicts as Trie-values
*close plots
--- Added comments ---  uid19464 [Feb 19, 2014 5:56:57 PM CET]
Change Package : 220258:1 http://mks-psad:7002/im/viewissue?selection=220258
Revision 1.36 2014/02/19 10:17:01CET Mertens, Sven (uidv7805)
signalCompare removed as inside ECU/SIL test now,
fixation of additional pylint and pep8 errors/warnings
--- Added comments ---  uidv7805 [Feb 19, 2014 10:17:01 AM CET]
Change Package : 219912:1 http://mks-psad:7002/im/viewissue?selection=219912
Revision 1.35 2014/02/14 13:18:31CET Skerl, Anne (uid19464)
*delete magic signal cutting in PlotConstrSetCheckAll()
--- Added comments ---  uid19464 [Feb 14, 2014 1:18:32 PM CET]
Change Package : 198254:14 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.34 2014/02/13 18:03:25CET Skerl, Anne (uid19464)
*bugfix at _getCompareResultDetails for subsets
--- Added comments ---  uid19464 [Feb 13, 2014 6:03:25 PM CET]
Change Package : 198254:14 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.33 2014/02/13 15:04:07CET Skerl, Anne (uid19464)
*add PlotConstrSetCheckAll() for validation report
*use numpy.where to find correct timestamp
*add data to _getCompareResultDetails()
*import numpy as np instead of each single method
--- Added comments ---  uid19464 [Feb 13, 2014 3:04:07 PM CET]
Change Package : 198254:14 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.32 2014/02/10 09:37:06CET Weinhold, Oliver (uidg4236)
Adapt to ConstructConstraintBox being a member.
--- Added comments ---  uidg4236 [Feb 10, 2014 9:37:06 AM CET]
Change Package : 213341:9 http://mks-psad:7002/im/viewissue?selection=213341
Revision 1.31 2014/02/07 11:03:18CET Weinhold, Oliver (uidg4236)
time stamp matching
--- Added comments ---  uidg4236 [Feb 7, 2014 11:03:18 AM CET]
Change Package : 213341:9 http://mks-psad:7002/im/viewissue?selection=213341
Revision 1.30 2014/01/21 17:46:51CET Skerl, Anne (uid19464)
*add GetTableData()
*add workaround at ConstructConstraintBox() and add comment
--- Added comments ---  uid19464 [Jan 21, 2014 5:46:51 PM CET]
Change Package : 198254:13 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.29 2014/01/09 13:21:34CET Skerl, Anne (uid19464)
*remove CAT connection from ucv, set it to deprecated
--- Added comments ---  uid19464 [Jan 9, 2014 1:21:35 PM CET]
Change Package : 198254:11 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.28 2013/12/18 18:17:50CET Skerl, Anne (uid19464)
*bugfix getConstraintSignals(): adapt to list output of getConstraints()
--- Added comments ---  uid19464 [Dec 18, 2013 6:17:50 PM CET]
Change Package : 198254:5 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.27 2013/12/18 16:48:55CET Skerl, Anne (uid19464)
*pylint
--- Added comments ---  uid19464 [Dec 18, 2013 4:48:55 PM CET]
Change Package : 198254:10 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.26 2013/12/18 16:08:14CET Skerl, Anne (uid19464)
*pep8
--- Added comments ---  uid19464 [Dec 18, 2013 4:08:14 PM CET]
Change Package : 198254:9 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.25 2013/12/18 13:50:34CET Skerl, Anne (uid19464)
*adapt to list output of getConstraints()
--- Added comments ---  uid19464 [Dec 18, 2013 1:50:34 PM CET]
Change Package : 198254:6 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.24 2013/12/10 15:21:08CET Skerl, Anne (uid19464)
*add _getCompareResultDetails() to get all compare results of trie
*remove getConstraintPlotLines()
--- Added comments ---  uid19464 [Dec 10, 2013 3:21:08 PM CET]
Change Package : 198254:5 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.23 2013/12/06 14:50:06CET Weinhold, Oliver (uidg4236)
Adapt UcvPlot to new signature of UseCaseValidator.__init__()
--- Added comments ---  uidg4236 [Dec 6, 2013 2:50:06 PM CET]
Change Package : 208496:1 http://mks-psad:7002/im/viewissue?selection=208496
Revision 1.22 2013/12/05 17:02:46CET Skerl, Anne (uid19464)
*change back UseCaseValidator interface
--- Added comments ---  uid19464 [Dec 5, 2013 5:02:46 PM CET]
Change Package : 198254:5 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.21 2013/12/05 14:13:51CET Weinhold, Oliver (uidg4236)
Add the UcvPlot class for constraint visualization.
--- Added comments ---  uidg4236 [Dec 5, 2013 2:13:52 PM CET]
Change Package : 208496:1 http://mks-psad:7002/im/viewissue?selection=208496
Revision 1.20 2013/12/04 18:46:39CET Skerl, Anne (uid19464)
*enable loadConstraints() to work with rec file name
*add method getConstraintSignals()
--- Added comments ---  uid19464 [Dec 4, 2013 6:46:40 PM CET]
Change Package : 198254:5 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.19 2013/11/29 16:40:16CET Skerl, Anne (uid19464)
*pep8
--- Added comments ---  uid19464 [Nov 29, 2013 4:40:17 PM CET]
Change Package : 198254:3 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.18 2013/11/29 15:22:16CET Skerl, Anne (uid19464)
*bugfix loadConstraints()
*make it nicer
--- Added comments ---  uid19464 [Nov 29, 2013 3:22:17 PM CET]
Change Package : 198254:3 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.17 2013/11/26 13:40:43CET Skerl, Anne (uid19464)
*remove: self._consJoin
*bugfix: addCompareData also to parent
*change checkConstraint: adapt to changed structure of trie values
*add: checkConstrSet
--- Added comments ---  uid19464 [Nov 26, 2013 1:40:44 PM CET]
Change Package : 198254:2 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.16 2013/11/22 11:18:00CET Skerl, Anne (uid19464)
*remove saving of input compare data from compare() to addCompareData()
--- Added comments ---  uid19464 [Nov 22, 2013 11:18:01 AM CET]
Change Package : 198254:1 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.15 2013/11/21 15:22:58CET Skerl, Anne (uid19464)
*extend checkConstraint() to check all constraints in one ConstraintSet
--- Added comments ---  uid19464 [Nov 21, 2013 3:22:58 PM CET]
Change Package : 198254:1 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.14 2013/11/18 16:51:46CET Skerl, Anne (uid19464)
*remove: import of cgeb file, index settings for contraint values
--- Added comments ---  uid19464 [Nov 18, 2013 4:51:47 PM CET]
Change Package : 198254:1 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.13 2013/11/13 18:19:19CET Skerl, Anne (uid19464)
*change: loadConstraints(self, consSet) -> loadConstraints(self, consSet=None, measid=None)
*change: write values of Trie kids as list of dicts
--- Added comments ---  uid19464 [Nov 13, 2013 6:19:19 PM CET]
Change Package : 198254:1 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.12 2013/11/04 16:55:23CET Skerl, Anne (uid19464)
*change: comment out try/except, maybe delete it in next revision?
*change: checkConstraint() for signals based on TimeStamp
*add: TODOs
*add: getConstraintPlotLines(), but not finished
--- Added comments ---  uid19464 [Nov 4, 2013 4:55:23 PM CET]
Change Package : 198254:1 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.11 2013/07/17 09:30:20CEST Mertens, Sven (uidv7805)
removing 0 alignment as signals should be proper by default
--- Added comments ---  uidv7805 [Jul 17, 2013 9:30:20 AM CEST]
Change Package : 185933:3 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.10 2013/07/05 13:36:03CEST Mertens, Sven (uidv7805)
fixing 2 errors:
- constraint compare was only able to test against 2 signals,
- signalCompare expects numpy.array
--- Added comments ---  uidv7805 [Jul 5, 2013 1:36:04 PM CEST]
Change Package : 185933:3 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.9 2013/06/28 11:39:46CEST Mertens, Sven (uidv7805)
added new signalCompare function to get signals compared
--- Added comments ---  uidv7805 [Jun 28, 2013 11:39:46 AM CEST]
Change Package : 185933:3 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.8 2013/03/22 08:24:22CET Mertens, Sven (uidv7805)
aligning bulk of files again for peping 8
--- Added comments ---  uidv7805 [Mar 22, 2013 8:24:22 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.7 2013/03/15 10:01:20CET Mertens, Sven (uidv7805)
added addConstraint method to add new constrain set with details
--- Added comments ---  uidv7805 [Mar 15, 2013 10:01:21 AM CET]
Change Package : 176171:8 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.6 2013/03/06 10:21:23CET Mertens, Sven (uidv7805)
done, pep8 styling
--- Added comments ---  uidv7805 [Mar 6, 2013 10:21:23 AM CET]
Change Package : 176171:7 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.4 2013/03/01 10:29:41CET Mertens, Sven (uidv7805)
bugfixing STK imports
--- Added comments ---  uidv7805 [Mar 1, 2013 10:29:41 AM CET]
Change Package : 176171:2 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.3 2013/02/28 17:12:40CET Mertens, Sven (uidv7805)
first working version of constraint related things
--- Added comments ---  uidv7805 [Feb 28, 2013 5:12:40 PM CET]
Change Package : 176171:1 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.1 2013/02/21 11:07:10CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk
    /val/project.pj
"""
