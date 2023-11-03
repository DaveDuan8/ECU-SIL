"""
crt.ecu_sil.tc_fct2.py
---------------------

Imporoved gating

ECU SIL test case to compare FCT(e.g. EBA) signals.
Pretty similar to the generic signal comparison with a few differences:
 * FTC signals are assumed digital, or at least with only a few different
 states.
 * A deviance in time is allowed, but limited to an interval of configuration
 parameter 'cycle tolerance'.

Differences in event activation greater than the configured cycle tolerance
are displayed as deviance, and will result in a failed test.
"""
from __future__ import print_function

import os

import numpy as np
import pandas as pd

from framework.util.gbl_defs import GblUnits
from framework.img.viz import AlgoSignal
from framework.io.signalreader import SignalReaderException
from framework.val.results import ValTestStep, ValAssessmentStates
from tc_common import BaseTest


__author__ = "Leidenberger, Ralf"
__copyright__ = "Copyright 2020, Continental AG"
__version__ = "$Revision: 1.1 $"
__maintainer__ = "$Author: Leidenberger, Ralf (uidq7596) $"
__date__ = "$Date: 2020/03/25 20:56:44CET $"

DEBUG = 0
TOLERANCE = "tolerance"
CYCLE_TOLERANCE = "cycle_tolerance"
UNIT = "unit"
NAME = "name"
SIGNAL = "signal"
SIGNAL_BASE_PATH = "signal_base_path"
SIL_PREFIX = "sil_prefix"
DEVICE_PREFIX = "device_prefix"
SIGNAL_LIST = "signal_list"
MTS_PACKAGE_TIME_STAMP = "MTS.Package.TimeStamp"
SIGNAL_LIST_SIZE = "signal_list_size"
SIL_INDEX_OFFSET = "sil_index_offset"
ECU_INDEX_OFFSET = "ecu_index_offset"
INDEX_SIGNAL_PATH = "index_signal_path"
EXP_RES = "exp_res"
DEFAULT = "default"
SIGNAL_INDEX = "signal_index"


class FctComparisonTests(BaseTest):
    """ Testcase class to perform test on FCT signals, mostly CGEB
    related signals such as "Prefill", "PreCrash", ...
    In opposite to the other tests this test allows for cycle deviance,
    which can be configured through the configuration file.
    """
    def __init__(self, data_manager, testcase, config):
        """ Initiliazes the testcase
        :param data_manager: The datamanager
        :param testcase: The ValTestcase
        :param config: configuration section from the config file
        """
        super(FctComparisonTests, self).__init__(data_manager, testcase, config)
        self.results = []

        self.test_results = []

        self.teststep = []

        self.measured_results = []
        self.warnings = None
        self.sil_rel_obj_id = None
        self.ecu_rel_obj_id = None
        self.signal_list_size = None
        self.val_exp_res = 0.0
        self.sil_offset = None
        self.ecu_offset = None
        self.sil_index = None
        self.ecu_index = None
        self.sil_list_limit = None
        self.ecu_list_limit = None

    def ecu_signal(self, signal):
        """ Returns the signal data from bsig
        :param signal: Signal name
        :return: list of signal data
        """
        return self._ecu_bsig_reader[signal]

    def sil_signal(self, signal):
        """ Returns the signal data from bsig
        :param signal: Signal name
        :return: list of signal data
        """
        return self._sil_bsig_reader[signal]

    def post_initialize(self):
        # extract exception resolution
        s_exp_res = self._config[EXP_RES]
        # noinspection PyBroadException
        try:
            i_exp_res_be = s_exp_res.find('<')+1
            i_exp_res_en = s_exp_res.find('[')-1
            self.val_exp_res = float(s_exp_res[i_exp_res_be: i_exp_res_en])
        except:
            self.val_exp_res = 0.0

        # Add teststeps here instead in execute
        if SIGNAL_LIST_SIZE in self._config:
            self.signal_list_size = self._config[SIGNAL_LIST_SIZE]
        else:
            self.signal_list_size = 1
        for m in range(len(self._config[SIGNAL_LIST])):
            entry = self._config[SIGNAL_LIST][m]
            for k in range(self.signal_list_size):
                if entry["key"] == 0:
                    continue
                elif entry["key"] == -1:
                    continue
                else:
                    tag = "{0:}-{1:02d}".format(self.testcase.get_spe_tag(), entry["key"])
                    name = "Signal Comparison for '{0:}'".format(entry[NAME])
                    teststep = ValTestStep(name=name,
                                           res_type="Violations",
                                           unit=GblUnits.UNIT_L_PERCENTAGE,
                                           # tag=tag,
                                           tag=tag + ":\n" + entry["signal"],
                                           exp_res=self._config[EXP_RES])

                    self.teststep.append(teststep)
                    self.test_results.append([])

    def execute(self, story):
        """ Performs the actual test.
        :param story: A part of a pdf report.
        """
        self._logger.debug("Executing FCT signal comparison.")

        meas_file = self._data_manager.get_data_port("currentfile")
        head, tail = os.path.split(meas_file)
        story.add_heading("{0:}".format(tail), 2)

        if INDEX_SIGNAL_PATH in self._config:
            ecu_timestamp = self.ecu_signal(self._config[DEVICE_PREFIX] + self._config[INDEX_SIGNAL_PATH])
            ecu_index0 = np.fromiter(ecu_timestamp, np.long)
            sil_timestamp = self.sil_signal(self._config[SIL_PREFIX] + self._config[INDEX_SIGNAL_PATH])
            sil_index0 = np.fromiter(sil_timestamp, np.long)
        else:
            mts_timestamp = self.ecu_signal(MTS_PACKAGE_TIME_STAMP)
            ecu_index0 = np.fromiter(mts_timestamp, np.long)
            mts_timestamp = self.sil_signal(MTS_PACKAGE_TIME_STAMP)
            sil_index0 = np.fromiter(mts_timestamp, np.long)

        # get the max value in the timestamp and to calculate whether there's a jump
        # (from max value of "unsigned long" to 0) in the signal or not
        ecu_index_jump = np.where(np.diff(ecu_index0) < 0)

        # just the same as the ecu signal about time-stamp signal
        for ii in ecu_index_jump[0]:
            # add the jump value to other timestamps from the jump point
            ecu_index0[(ii+1):] = ecu_index0[(ii+1):] + ecu_index0[ii]
            sil_index0[(ii+1):] = sil_index0[(ii+1):] + ecu_index0[ii]
        self.ecu_index = ecu_index0
        self.sil_index = sil_index0

        self.warnings = []
        only_rel_obj = False

        if ECU_INDEX_OFFSET in self._config:
            self.ecu_offset = self._config[ECU_INDEX_OFFSET]
        else:
            self.ecu_offset = None

        if SIL_INDEX_OFFSET in self._config:
            self.sil_offset = self._config[SIL_INDEX_OFFSET]
        else:
            self.sil_offset = None
        list_limit = False
        for m in range(len(self._config[SIGNAL_LIST])):
            # story.add_paragraph("Result plot for Teststep '{}'".format(self.teststep[m].id))
            entry = self._config[SIGNAL_LIST][m]
            # Evaluate only the relevant object
            if entry["key"] == 0:
                # noinspection PyBroadException
                try:
                    del self.ecu_rel_obj_id
                    del self.sil_rel_obj_id
                except:
                    pass
                ecu_rel_obj_name = self._config[DEVICE_PREFIX] + self._config[SIGNAL_BASE_PATH] + entry[SIGNAL]
                self.ecu_rel_obj_id = self.read_signal(self._ecu_bsig_reader, ecu_rel_obj_name, entry[NAME],
                                                       entry[UNIT], self.ecu_index, index_offset=self.ecu_offset)
                sil_rel_obj_name = self._config[SIL_PREFIX] + self._config[SIGNAL_BASE_PATH] + entry[SIGNAL]
                self.sil_rel_obj_id = self.read_signal(self._sil_bsig_reader, sil_rel_obj_name, entry[NAME],
                                                       entry[UNIT], self.sil_index, index_offset=self.sil_offset)
                only_rel_obj = True
                continue
            elif entry["key"] == -1:
                ecu_list_limit_name = self._config[DEVICE_PREFIX] + self._config[SIGNAL_BASE_PATH] + entry[SIGNAL]
                self.ecu_list_limit = self.read_signal(self._ecu_bsig_reader, ecu_list_limit_name, entry[NAME],
                                                       entry[UNIT], self.ecu_index, index_offset=self.ecu_offset,
                                                       source='ECU')

                sil_list_limit_name = self._config[SIL_PREFIX] + self._config[SIGNAL_BASE_PATH] + entry[SIGNAL]
                self.sil_list_limit = self.read_signal(self._sil_bsig_reader, sil_list_limit_name, entry[NAME],
                                                       entry[UNIT], self.sil_index, index_offset=self.sil_offset,
                                                       source='SIL')
                list_limit = True
                continue
            n = m
            if list_limit:
                n -= 1
            if only_rel_obj:
                n -= 1
                ecu_signal = AlgoSignal(entry[NAME], len(self.ecu_index[self.ecu_offset:]) * [0.],
                                        self.ecu_index[self.ecu_offset:], entry[UNIT])
                sil_signal = AlgoSignal(entry[NAME], len(self.sil_index[self.sil_offset:]) * [0.],
                                        self.sil_index[self.sil_offset:], entry[UNIT])

                j = 0
                while j < len(ecu_signal) and j < len(self.ecu_rel_obj_id):
                    try:
                        if len(self.ecu_rel_obj_id[j]) > 1:
                            rel_ob_id = self.ecu_rel_obj_id[j][0]
                        else:
                            rel_ob_id = self.ecu_rel_obj_id[j]
                    except IndexError:
                        rel_ob_id = self.ecu_rel_obj_id[j]
                    if rel_ob_id == -1 or rel_ob_id == 255:
                        j += 1
                        continue
                    else:
                        ecu_signal_name = (self._config[DEVICE_PREFIX] + self._config[SIGNAL_BASE_PATH] +
                                           entry[SIGNAL]).format(rel_ob_id)

                        if SIGNAL_INDEX in entry:
                            ecu_signal_temp = self.read_signal(self._ecu_bsig_reader, ecu_signal_name, entry[NAME],
                                                               entry[UNIT], self.ecu_index,
                                                               signal_index=entry[SIGNAL_INDEX],
                                                               index_offset=self.ecu_offset, entry=entry, source='ECU')
                        else:
                            ecu_signal_temp = self.read_signal(self._ecu_bsig_reader, ecu_signal_name, entry[NAME],
                                                               entry[UNIT], self.ecu_index,
                                                               index_offset=self.ecu_offset, entry=entry, source='ECU')

                        jj = j + 1
                        while True:
                            try:
                                if len(self.ecu_rel_obj_id[jj]) > 1:
                                    rel_ob_id_jj = self.ecu_rel_obj_id[jj][0]
                                else:
                                    rel_ob_id_jj = self.ecu_rel_obj_id[jj]
                            except IndexError:
                                rel_ob_id_jj = self.ecu_rel_obj_id[jj]
                            if jj == len(ecu_signal):
                                break
                            elif rel_ob_id == rel_ob_id_jj:
                                jj += 1
                            else:
                                break

                        ecu_signal.values[j:jj] = ecu_signal_temp.values[j:jj]
                        j = jj

                j = 0
                while j < len(sil_signal) and j < len(self.sil_rel_obj_id):
                    try:
                        if len(self.sil_rel_obj_id[j]) > 1:
                            rel_ob_id = self.sil_rel_obj_id[j][0]
                        else:
                            rel_ob_id = self.sil_rel_obj_id[j]
                    except IndexError:
                        rel_ob_id = self.sil_rel_obj_id[j]
                    if rel_ob_id == -1 or rel_ob_id == 255:
                        j += 1
                        continue
                    else:
                        sil_signal_name = (self._config[SIL_PREFIX] + self._config[SIGNAL_BASE_PATH] +
                                           entry[SIGNAL]).format(rel_ob_id)

                        if SIGNAL_INDEX in entry:
                            sil_signal_temp = self.read_signal(self._sil_bsig_reader, sil_signal_name, entry[NAME],
                                                               entry[UNIT], self.sil_index,
                                                               signal_index=entry[SIGNAL_INDEX],
                                                               index_offset=self.sil_offset, entry=entry, source='SIL')
                        else:
                            sil_signal_temp = self.read_signal(self._sil_bsig_reader, sil_signal_name, entry[NAME],
                                                               entry[UNIT], self.sil_index,
                                                               index_offset=self.sil_offset, entry=entry, source='SIL')

                        jj = j + 1
                        while True:
                            try:
                                if len(self.sil_rel_obj_id[jj]) > 1:
                                    rel_ob_id_jj = self.sil_rel_obj_id[jj][0]
                                else:
                                    rel_ob_id_jj = self.sil_rel_obj_id[jj]
                            except IndexError:
                                rel_ob_id_jj = self.sil_rel_obj_id[jj]
                            if jj == len(sil_signal):
                                break
                            elif rel_ob_id == rel_ob_id_jj:
                                jj += 1
                            else:
                                break

                        sil_signal.values[j:jj] = sil_signal_temp.values[j:jj]
                        j = jj

                if not ecu_signal or not sil_signal:
                    self.measured_results.append(-1)
                    self.test_results[m].append(-1)
                    continue
                elif self._compare_signal_list(ecu_signal, sil_signal, story, entry, n) == 0:
                    self.measured_results.append(-2)
                    self.test_results[m].append(-2)
                    continue

            elif SIGNAL_LIST_SIZE in self._config.keys():
                # group signals
                for k in range(self.signal_list_size):
                    idx = n * self.signal_list_size + k
                    sig_name = (self._config[DEVICE_PREFIX] + self._config[SIGNAL_BASE_PATH] + entry[SIGNAL]).format(k)
                    ecu_signal = self.read_signal(self._ecu_bsig_reader, sig_name, entry[NAME], entry[UNIT],
                                                  self.ecu_index, index_offset=self.ecu_offset)
                    sig_name = (self._config[SIL_PREFIX] + self._config[SIGNAL_BASE_PATH] + entry[SIGNAL]).format(k)
                    sil_signal = self.read_signal(self._sil_bsig_reader, sig_name, entry[NAME], entry[UNIT],
                                                  self.sil_index, index_offset=self.sil_offset)
                    if not ecu_signal or not sil_signal:
                        self.measured_results.append(-1)
                        self.test_results[m].append(-1)
                        continue
                    elif self._compare_signal_list(ecu_signal, sil_signal, story, entry, idx, k=k) == 0:
                        self.measured_results.append(-2)
                        self.test_results[m].append(-2)
                        continue
            else:
                sig_name = self._config[DEVICE_PREFIX] + self._config[SIGNAL_BASE_PATH] + entry[SIGNAL]
                ecu_signal = self.read_signal(self._ecu_bsig_reader, sig_name, entry[NAME], entry[UNIT], self.ecu_index,
                                              index_offset=self.ecu_offset)
                sig_name = self._config[SIL_PREFIX] + self._config[SIGNAL_BASE_PATH] + entry[SIGNAL]
                sil_signal = self.read_signal(self._sil_bsig_reader, sig_name, entry[NAME], entry[UNIT], self.sil_index,
                                              index_offset=self.sil_offset)
                if not ecu_signal or not sil_signal:
                    self.measured_results.append(-1)
                    self.test_results[m].append(-1)
                    continue
                elif self._compare_signal_list(ecu_signal, sil_signal, story, entry, n) == 0:
                    self.measured_results.append(-2)
                    self.test_results[m].append(-2)
                    continue

            story.add_paragraph("Result plots for Teststep '{}' -- '{}'".format(self.teststep[n].id,
                                                                                self.teststep[n].name))

        # Warnings:
        if self.warnings:
            story.add_heading("Signal Availability Warnings", 2)
            for msg in self.warnings:
                story.add_paragraph(msg)

    def pre_terminate(self):
        self._logger.debug("PreTerminate - FCT")
        for m in range(len(self._config[SIGNAL_LIST])):
            for k in range(self.signal_list_size):
                idx = m * self.signal_list_size + k

                if len(self.test_results[idx]) == 0:
                    continue
                if self.measured_results[idx] == -1:
                    self.teststep[idx].add_assessment(self._mk_assessment(ValAssessmentStates.NOT_ASSESSED))
                    self.measured_results[idx] = "Signal not in export"
                elif self.measured_results[idx] == -2:
                    self.teststep[idx].add_assessment(self._mk_assessment(ValAssessmentStates.PASSED))
                    self.measured_results[idx] = "0 [%]"#"Signal flat line"
                else:
                    self.measured_results[idx] = round(self.measured_results[idx] / float(len(self.test_results[idx])),
                                                       4)
                    if self.measured_results[m] > self.val_exp_res:
                        self.teststep[idx].add_assessment(self._mk_assessment(ValAssessmentStates.FAILED))
                    else:
                        self.teststep[idx].add_assessment(self._mk_assessment(ValAssessmentStates.PASSED))

                self.teststep[idx].set_value(self.measured_results[idx])
                self.testcase.add_test_step(self.teststep[idx])

    @staticmethod
    def _analyze(ref_edge_ts, edges, ref_edges, lower_tol, upper_tol):
        """ Checks if the reference edge can be found in SIL within the
        given time tolerance
        :param ref_edge_ts: timestamp of the edge
        :param edges: all edges from SIL
        :param ref_edges: all edges from REF/ECU
        :param lower_tol: early deviance in milli seconds
        :param upper_tol: late deviance in milli seconds
        :return:
        """
        lower_bound = ref_edge_ts + lower_tol * 1.e3
        upper_bound = ref_edge_ts + upper_tol * 1.e3

        caught_edges = edges[(edges.index < upper_bound) &
                             (edges.index > lower_bound)]
        if len(caught_edges) == 0:
            return 1, (abs(lower_tol) + abs(upper_tol))

        best_matching_idx = None
        best_matching_delta = float("inf")
        abs_best_matching_delta = abs(best_matching_delta)
        for c in caught_edges.index.values:
            if abs(c - ref_edge_ts) < abs_best_matching_delta:
                best_matching_idx = c
                best_matching_delta = c - ref_edge_ts
                abs_best_matching_delta = abs(best_matching_delta)

        other_edges_within_tol = ref_edges[(ref_edges.index < upper_bound) &
                                           (ref_edges.index > lower_bound)]
        if len(other_edges_within_tol):

            for o in other_edges_within_tol.index.values:
                if abs(o - best_matching_idx) < abs_best_matching_delta:
                    return 1, (abs(lower_tol) + abs(upper_tol))

        return 0, best_matching_delta

    @staticmethod
    def _find_edges(signal):
        """ Calculates the first derivative of the given signal and returns
        a series of raising and a series of falling edges.
        :param signal:
        :return:
        """
        derivative = np.diff(signal.values.astype(float))
        all_edges = pd.Series(derivative, index=signal.index.values[1:])

        raising_edges = all_edges[all_edges > 0]
        falling_edges = all_edges[all_edges < 0]

        return raising_edges, falling_edges

    # def read_signal(self, reader, signal_prefix, signal_name,
    #                 name, unit, index, k=None, index_offset=None):
    #     fqn = (signal_prefix + self._config[SIGNAL_BASE_PATH] + signal_name).format(k)
    #     try:
    #         raw_data = reader[fqn]
    #     except SignalReaderException:
    #         msg = "Signal '{0:}' not available in BSIG".format(fqn)
    #         self._logger.warn(msg)
    #         self.warnings.append(msg)
    #         return
    #
    #     if index_offset:
    #         raw_data = raw_data[index_offset:]
    #         index = index[index_offset:]
    #         return AlgoSignal(name, raw_data, index, unit)
    #
    #     if DEBUG:
    #         l = 0
    #         u = index.argmax() + 1
    #         return AlgoSignal(name, raw_data[l:u], index[l:u], unit)
    #     else:
    #         return AlgoSignal(name, raw_data, index, unit)

    def read_signal(self, reader, signal, name, unit, index, index_offset=None, signal_index=None, entry=None,
                    source=None):

        try:
            raw_data = reader[signal]
            if signal_index is not None:
                raw_data = list(zip(*raw_data)[signal_index])
                if hasattr(self, "ecu_rel_obj_id"):
                    rel_obj_id = self.ecu_rel_obj_id
                    if source == 'SIL':
                        rel_obj_id = self.sil_rel_obj_id
                    # np.array([item in self.sil_rel_obj_id.index for item in index])
                    raw_data = list(np.array(raw_data)[np.in1d(index, rel_obj_id.index)])
                    index = index[np.in1d(index, rel_obj_id.index)]

            if entry is not None:
                if DEFAULT in entry:
                    index = index[np.array(raw_data[:]) != entry[DEFAULT]]
                    raw_data = list(np.array(raw_data)[np.array(raw_data[:]) != entry[DEFAULT]])
        except SignalReaderException:
            msg = "Signal %s is not present in .bsig file, skipping" % signal
            self._logger.warn(msg)
            return

        if len(raw_data) == 0:
            msg = "Signal %s is empty, skipping" % signal
            self._logger.warn(msg)
            return

        # method to handle multiple timestamps
        signal = self._shrink_signal(AlgoSignal(name, raw_data, index, unit))
        raw_data = signal.series.values
        index = signal.series.index

        if index_offset:
            # return AlgoSignal(name, raw_data[index_offset-1:], index[:-index_offset+1], unit)
            raw_data = raw_data[index_offset:]
            index = index[index_offset:]
            return AlgoSignal(name, raw_data, index, unit)

        if DEBUG:
            l = 0
            u = index.argmax() + 1
            return AlgoSignal(name, raw_data[l:u], index[l:u], unit)
        else:
            return AlgoSignal(name, raw_data, index, unit)

    @staticmethod
    def _shrink_signal(signal):
        """ Shrink the signal in the case, that there are multiply identical timestamps.
        :param signal:
        :return:
        """
        timestamp_1 = sorted(set(signal.series.index))

        if len(timestamp_1) == len(signal):
            return signal
        else:
            timestamp_2 = np.diff(np.array(signal.series.index))
            timestamp_3 = np.where(timestamp_2 != 0)
            values_1 = [signal.series.values[0:timestamp_3[0][0]+1]]
            for ij in range(len(timestamp_3[0])-1):
                values_1.append(signal.series.values[timestamp_3[0][ij]+1: timestamp_3[0][ij+1]+1])
            values_1.append(signal.series.values[timestamp_3[0][-1]+1:])
            values_2 = []
            for ij in range(len(values_1)):
                values_2.append(values_1[ij][-1])

            # noinspection PyProtectedMember
            return AlgoSignal(signal._name, values_2, timestamp_1, signal._unit)

    def _compare_signal_list(self, ecu_signal, sil_signal, story, entry, m, k=None):
        ecu_raising_edges, ecu_falling_edges = self._find_edges(ecu_signal)
        sil_raising_edges, sil_falling_edges = self._find_edges(sil_signal)
        ignore_flat_line = False
        if "flat_line_test" in entry.keys():
            if entry["flat_line_test"] == 1:
                ignore_flat_line = False

        if ecu_raising_edges.values.size == 0 and ecu_falling_edges.values.size == 0 and\
           sil_raising_edges.values.size == 0 and sil_falling_edges.values.size == 0 and ignore_flat_line:
            self._logger.debug("Flatline", ecu_signal, "skipping")
            # noinspection PyBroadException
            try:
                self.measured_results[m] += 0.
            except:
                self.measured_results.append(0.)
            return 0

        lower_tol, upper_tol = entry[CYCLE_TOLERANCE]

        unmatched_ecu_events = pd.Series(np.zeros(ecu_signal.values.shape), ecu_signal.index.values)
        diff_ecu_events = pd.Series(np.zeros(ecu_signal.values.shape), ecu_signal.index.values)

        count = 0
        for idx in ecu_raising_edges.index:
            r, delta = self._analyze(idx, sil_raising_edges, ecu_raising_edges, lower_tol, upper_tol)
            unmatched_ecu_events[idx] = float(r)
            diff_ecu_events[idx] = delta
            count += 1
        for idx in ecu_falling_edges.index:
            # self._logger.debug("Falling edge at '{}'".format(idx))
            r, delta = self._analyze(idx, sil_falling_edges, ecu_falling_edges, lower_tol, upper_tol)
            unmatched_ecu_events[idx] = -float(r)
            diff_ecu_events[idx] = delta
            count += 1

        if count:
            unmatched_ecu_events_percent = float(len(set((unmatched_ecu_events[abs(unmatched_ecu_events) >
                                                                               0.0]).index))) / float(count) * 100.0
        else:
            # if no events in ECU, then to check whether there're events in SIL
            for idx in sil_raising_edges.index:
                r, delta = self._analyze(idx, ecu_raising_edges, sil_raising_edges, lower_tol, upper_tol)
                unmatched_ecu_events[idx] = float(r)
                count += 1

            for idx in sil_falling_edges.index:
                # self._logger.debug("Falling edge at '{}'".format(idx))

                r, delta = self._analyze(idx, ecu_falling_edges, sil_falling_edges, lower_tol, upper_tol)
                unmatched_ecu_events[idx] = -float(r)
                count += 1

            if count:
                unmatched_ecu_events_percent = float(len(set((unmatched_ecu_events[abs(unmatched_ecu_events) >
                                                                                   0.0]).index))) /\
                                               float(count) * 100.0
            else:
                unmatched_ecu_events_percent = 0.

        # Assess results
        if unmatched_ecu_events_percent > self.val_exp_res:
            assessment = ValAssessmentStates.FAILED
        else:
            assessment = ValAssessmentStates.PASSED
        self.test_results[m].append(assessment)

        self.teststep[m].set_value(unmatched_ecu_events_percent)

        # noinspection PyBroadException
        try:
            # noinspection PyProtectedMember
            self.measured_results[m] += self.teststep[m].meas_result._value
        except:
            # noinspection PyProtectedMember
            self.measured_results.append(self.teststep[m].meas_result._value)

        fh = self.plot_factory.histogram_plot(ecu_signal, sil_signal, signal_diff=diff_ecu_events,
                                              tolerance=entry[CYCLE_TOLERANCE])
        # fh = self.plot_factory.histogram_plot(ecu_signal, sil_signal, tolerance=entry[CYCLE_TOLERANCE])

        if k is None:
            caption = "ECU and SIL plots for {0:} (pass rate: {1:3.2f} %)".format(entry[NAME],
                                                                                  100 - unmatched_ecu_events_percent)
        else:
            signal_name = (entry[SIGNAL] + ' [{0:}]').format(k)
            caption = "ECU and SIL plots for {0:} (pass rate: {1:3.2f} %)".format(signal_name,
                                                                                  100 - unmatched_ecu_events_percent)
        if fh is not None:
            story.add_image(caption, os.path.join(self.out_directory, fh))

        return 1
