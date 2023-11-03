"""
crt.ecu_sil.tc_generic_signals
------------------------------
Module to compare arbitrary signals and assess their equality as a deviance in percent.
"""
from __future__ import print_function

import math
import os
import re
from decimal import *

import numpy as np
import pandas as pd

from framework.util.gbl_defs import GblUnits
from framework.img.viz import AlgoSignal
from framework.io.signalreader import SignalReaderException
from framework.val.results import ValTestStep, ValAssessmentStates
from tc_common import BaseTest

DEBUG = 0
LIST_LIMIT_VALUE = 200
TOLERANCE = "tolerance"
CYCLE_TOLERANCE = "cycle_tolerance"
PERCENTAGE = "percentage"
UNIT = "unit"
NAME = "name"
SIGNAL = "signal"
SIGNAL_BASE_PATH = "signal_base_path"
SIL_PREFIX = "sil_prefix"
DEVICE_PREFIX = "device_prefix"
SIGNAL_LIST = "signal_list"
MTS_PACKAGE_TIME_STAMP = "MTS.Package.TimeStamp"
SIGNAL_LIST_SIZE = "signal_list_size"
SIGNAL_LIST_OFFSET = "signal_list_offset"
SIL_INDEX_OFFSET = "sil_index_offset"
ECU_INDEX_OFFSET = "ecu_index_offset"
INDEX_SIGNAL_PATH = "index_signal_path"
SIGNAL_INDEX = "signal_index"
DEFAULT = "default"
EXP_RES = "exp_res"
# SPEED = "speed_signal"

__author__ = "Leidenberger, Ralf"
__copyright__ = "Copyright 2020, Continental AG"
__version__ = "$Revision: 1.1 $"
__maintainer__ = "$Author: Leidenberger, Ralf (uidq7596) $"
__date__ = "$Date: 2020/03/25 20:56:44CET $"


class GenericSignalComparison(BaseTest):
    def __init__(self, data_manager, testcase, config):
        super(GenericSignalComparison, self).__init__(data_manager, testcase,
                                                      config)
        self.results = []
        self.events = []
        self.passed_events = []
        self.test_passed_events = []
        self.test_events = []
        self.test_results = []
        self.teststep = []
        self.measured_results = []
        self.messages = []
        self.exception_criteria = None
        self.sil_orig_index = None
        self.sil_rel_obj_id = None
        self.sil_index = None
        self.sil_list_limit = None
        self.sil_offset = None
        self.ecu_orig_index = None
        self.ecu_rel_obj_id = None
        self.ecu_index = None
        self.ecu_list_limit = None
        self.ecu_offset = None

    def _reindex(self, ecu, sil):
        """ Method to resample sil data to the ecu timestamp if available. """
        # make a series containing itself
        ecu_series = pd.Series(ecu, index=ecu)
        sil_series = pd.Series(sil, index=sil)
        missing_ts = ecu_series - sil_series
        # print("ecu_series,sil_series,missing_ts",ecu_series,sil_series,missing_ts)
        if True in pd.isnull(missing_ts).values:
            self._logger.warning("Some timestamps do not exists in SIL.")

            # Look in the subtraction of ecu and sil for the timestamps
            # which belong to sil and are NaN because there was no equal
            # index in the ecu series
            # noinspection PyBroadException
            try:
                # Terrible hack: In some rare cases, with stuck indexes
                # this operation fails, to prevent test abortion we return
                # the original index
                mm = missing_ts[sil_series]
            except Exception:
                self._logger.warning("Index error, returning raw signal")
                return sil

            # Work through the timestamps (worse case all) and try to find
            # a nearest right neighbor
            idx = None
            for idx in mm.index:
                if pd.isnull(mm[idx]):
                    loc = missing_ts.index.get_loc(idx)

                    if len(missing_ts) > loc + 1:
                        val = missing_ts.index.values[loc + 1]
                        if val in ecu_series.index:
                            mm[idx] = val
                else:
                    mm[idx] = idx

            mm[mm.index.values[-1]] = idx

            return mm.values
        return sil

    def post_initialize(self):
        # Add teststeps here instead in execute
        tmp_res_exp = self._config[EXP_RES]
        tmp_regex = re.compile("\d+(?:\.\d+)?")
        tmp = tmp_regex.findall(tmp_res_exp)
        self.exception_criteria = Decimal(tmp[0])
        if SIGNAL_LIST_SIZE in self._config:
            signal_list_size = self._config[SIGNAL_LIST_SIZE]
        else:
            signal_list_size = 1

        for m in range(len(self._config[SIGNAL_LIST])):
            entry = self._config[SIGNAL_LIST][m]
            for k in range(signal_list_size):
                if entry["key"] == 0:
                    continue
                elif entry["key"] == -1:
                    continue
                else:
                    # noinspection PyBroadException
                    try:
                        tag = "{0:}-{1:02d}".format(self.testcase.get_spe_tag(), entry["key"])
                    except:
                        tag = "{0:}-{1:02d}".format(self.testcase.get_spe_tag(), 1)
                    name = entry[NAME]
                    teststep = ValTestStep(name=name,
                                           res_type="Deviance",
                                           unit=GblUnits.UNIT_L_PERCENTAGE,
                                           tag=tag + ":\n" + entry[SIGNAL].format(k),
                                           exp_res=self._config[EXP_RES])
                    self.teststep.append(teststep)
                    self.test_results.append([])

    def execute(self, story):

        self._logger.info("{0:}".format(self._config[NAME]))

        # get index offset from the Test Configuration file
        if ECU_INDEX_OFFSET in self._config:
            self.ecu_offset = self._config[ECU_INDEX_OFFSET]
        else:
            self.ecu_offset = None

        if SIL_INDEX_OFFSET in self._config:
            self.sil_offset = self._config[SIL_INDEX_OFFSET]
        else:
            self.sil_offset = None

        # setup the signal name for the synchronization of the ECU and SIL BSIGs
        if INDEX_SIGNAL_PATH in self._config:
            ecu_index_name = (self._config[DEVICE_PREFIX] + self._config[INDEX_SIGNAL_PATH])
            ecu_index0 = np.fromiter(self._ecu_bsig_reader[ecu_index_name], np.int64)

            sil_index_name = (self._config[SIL_PREFIX] + self._config[INDEX_SIGNAL_PATH])
            sil_index0 = np.fromiter(self._sil_bsig_reader[sil_index_name], np.int64)
        else:
            data = self._ecu_bsig_reader[MTS_PACKAGE_TIME_STAMP]
            ecu_index0 = np.fromiter(data, np.long)
            data = self._sil_bsig_reader[MTS_PACKAGE_TIME_STAMP]
            self.sil_orig_index = np.fromiter(data, np.long)
            sil_index0 = self._reindex(ecu_index0, self.sil_orig_index)
            ecu_index_name = ""
            sil_index_name = ""

        # developer section header

        # get the max value in the timestamp and to calculate whether there's a jump
        # (from max value of "unsigned long" to 0) in the signal or not
        ecu_index_jump = np.where(np.diff(ecu_index0) < 0)

        # get the recording name
        crt_rec_file = os.path.split(self._data_manager.get_data_port("currentfile"))[1]
        # check if the Ref-BSIG contains a problem
        for ii in ecu_index_jump[0]:
            if ecu_index0[ii] < (4294967295 - 1):
                story.add_paragraph("<br/><font size='8'>A reset occurred in synchronization signal"
                                    " </font><b><font size='7'>'{}'</font></b>".format(ecu_index_name) +
                                    "<font size='8'> from the .bsig* file"
                                    " </font><b><font size='7'>'{}'</font></b>".format(crt_rec_file) +
                                    "<font size='8'> It makes no sense to execute the test for this recording.</font>")
                story.add_paragraph("<font size='8'>*) ECU signal is considered as reference.</font>")
                # return -1

        # just the same as the ecu signal about time-stamp signal
        sil_index_jump = np.where(np.diff(sil_index0) < 0)
        for iii in sil_index_jump[0]:
            if sil_index0[iii] < (4294967295 - 1):
                story.add_paragraph("<br/><font size='8'>A reset occurred in synchronization signal"
                                    " </font><b><font size='7'>'{}'</font></b>".format(sil_index_name) +
                                    "<font size='8'> from the .bsig** file </font><b>"
                                    "<font size='7'>'{}'</font></b>".format(crt_rec_file) +
                                    "<font size='8'> The reason should be analysed.</font>")
                story.add_paragraph("<font size='8'>**) SIL signal is considered as reference.</font>")

        for ii in ecu_index_jump[0]:
            # add the jump value to other timestamps from the jump point
            ecu_index0[(ii + 1):] = ecu_index0[(ii + 1):] + ecu_index0[ii]
        #for iii in sil_index_jump[0]:
            #sil_index0[(iii + 1):] = sil_index0[(iii + 1):] + sil_index0[iii]
        self.ecu_index = ecu_index0
        self.sil_index = sil_index0

        story.add_heading("Result plots for recording '{}'".format(os.path.split(
            self._data_manager.get_data_port("currentfile"))[1]), 2)

        only_rel_obj = False
        list_limit = False

        self.measured_results = []
        correction = 0
        for m in range(len(self._config[SIGNAL_LIST])):
            entry = self._config[SIGNAL_LIST][m]
            print("entry",entry)
            # key == 0 defines a reference signal which is used to sync REF and Test object with different ID
            # (e.g. EM objects over the ACC ID)
            n = m - correction
            if entry["key"] == 0:
                # noinspection PyBroadException
                try:
                    del self.ecu_rel_obj_id
                    del self.sil_rel_obj_id
                except:
                    pass
                ecu_rel_obj_id_name = self._get_signal_full_name(DEVICE_PREFIX, entry)
                self.ecu_rel_obj_id = self._read_signal(self._ecu_bsig_reader, ecu_rel_obj_id_name, entry[NAME],
                                                        entry[UNIT], self.ecu_index, index_offset=self.ecu_offset,
                                                        entry=entry, source='ECU')

                sil_rel_obj_id_name = self._get_signal_full_name(SIL_PREFIX, entry)
                self.sil_rel_obj_id = self._read_signal(self._sil_bsig_reader, sil_rel_obj_id_name, entry[NAME],
                                                        entry[UNIT], self.sil_index, index_offset=self.sil_offset,
                                                        entry=entry, source='SIL')

                only_rel_obj = True
                continue
            # key == -1 defines the counter signal to set an limit of a signal list which size is variable
            # e.g. for RSP number of clusters
            elif entry["key"] == -1:
                ecu_list_limit_name = self._get_signal_full_name(DEVICE_PREFIX, entry)
                self.ecu_list_limit = self._read_signal(self._ecu_bsig_reader, ecu_list_limit_name, entry[NAME],
                                                        entry[UNIT], self.ecu_index, index_offset=self.ecu_offset,
                                                        source='ECU')

                sil_list_limit_name = self._get_signal_full_name(SIL_PREFIX, entry)
                self.sil_list_limit = self._read_signal(self._sil_bsig_reader, sil_list_limit_name, entry[NAME],
                                                        entry[UNIT], self.sil_index, index_offset=self.sil_offset,
                                                        source='SIL')

                list_limit = True
                continue
            if only_rel_obj:
                n -= 1
            if list_limit:
                n -= 1

            self.results = []
            self.events = []
            self.passed_events = []

            executed = False
            if list_limit and not (SIGNAL_LIST_SIZE in self._config.keys()):
                for k in range(LIST_LIMIT_VALUE):
                    executed = self._compare_signal_list(story=story, entry=entry, k=k, only_rel_obj=only_rel_obj,
                                                         list_limit=list_limit)
            elif SIGNAL_LIST_SIZE in self._config.keys():
                # group signals
                if SIGNAL_LIST_OFFSET in self._config.keys():
                    offset = int(self._config[SIGNAL_LIST_OFFSET])
                else:
                    offset = 0
                for k in range(self._config[SIGNAL_LIST_SIZE]):
                    executed = self._compare_signal_list(story=story, entry=entry, k=k + offset,
                                                         only_rel_obj=only_rel_obj, list_limit=list_limit)
            else:
                # Single signals
                executed = self._compare_signal_list(story=story, entry=entry,
                                                     only_rel_obj=only_rel_obj, list_limit=list_limit)

            if executed:
                print(entry)
                # developer section header
                story.add_paragraph(
                    "Result plots for Teststep '{}' -- '{}'".format(self.teststep[n].id, self.teststep[n].name))
                if SIGNAL_LIST_SIZE in self._config:
                    signal_list_size = self._config[SIGNAL_LIST_SIZE]
                else:
                    signal_list_size = 1
                for k in range(signal_list_size):
                    self.test_events.append(float(self.events[k]))
                    self.test_passed_events.append(float(self.passed_events[k]))
                    # test_events[n] == -1 when signal n is not available
                    if self.events[k] == -1:
                        self.measured_results.append(-1)
                    # test_events[n] == -1 when signal n is flatline
                    elif self.events[k] == -2:
                        self.measured_results.append(-2)
                    else:
                        measured_events_avg = float(self.test_passed_events[-1]) / float(self.test_events[-1]) * 100.0
                        self.measured_results.append(measured_events_avg)
            else:
                correction += 0

    def pre_terminate(self):
        if SIGNAL_LIST_SIZE in self._config:
            signal_list_size = self._config[SIGNAL_LIST_SIZE]
        else:
            signal_list_size = 1
        for m in range(len(self._config[SIGNAL_LIST])):
            for k in range(signal_list_size):
                idx = m * signal_list_size + k
                self.measured_results[idx] = 100 - round(self.measured_results[idx], 4)
                if self.measured_results[idx] == 101:
                    self.teststep[idx].add_assessment(ValAssessmentStates.NOT_ASSESSED)
                    self.measured_results[idx] = "Signal not in export"
                elif self.measured_results[idx] == 102:
                    self.teststep[idx].add_assessment(ValAssessmentStates.PASSED)
                    self.measured_results[idx] = "0 [%]"#"Signal flat line"
                elif self.measured_results[idx] > self.exception_criteria:
                    self.teststep[idx].add_assessment(self._mk_assessment(ValAssessmentStates.FAILED))
                else:
                    self.teststep[idx].add_assessment(self._mk_assessment(
                        ValAssessmentStates.PASSED))
                self.teststep[idx].set_value(self.measured_results[idx])
                self.testcase.add_test_step(self.teststep[idx])

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
            values_1 = [signal.series.values[0:timestamp_3[0][0] + 1]]
            for ij in range(len(timestamp_3[0]) - 1):
                values_1.append(signal.series.values[timestamp_3[0][ij] + 1: timestamp_3[0][ij + 1] + 1])
            values_1.append(signal.series.values[timestamp_3[0][-1] + 1:])
            values_2 = []
            for ij in range(len(values_1)):
                values_2.append(values_1[ij][-1])
            # noinspection PyBroadException
            try:
                # noinspection PyProtectedMember
                return AlgoSignal(signal._name, values_2, timestamp_1, signal._unit)
            except:
                return signal

    def _read_signal(self, reader, signal, name, unit, index, index_offset=None, signal_index=None, entry=None,
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
            if self.messages:
                self.messages.append(msg)
            return

        if len(raw_data) == 0:
            msg = "Signal %s is empty, skipping" % signal
            self._logger.warn(msg)
            if self.messages:
                self.messages.append(msg)
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

    def _get_signal_full_name(self, prefix, entry):
        return self._config[prefix] + self._config[SIGNAL_BASE_PATH] + entry[SIGNAL]

    def _compare_signal_list(self, story, entry, k=None, only_rel_obj=False, list_limit=False):
        self.messages = []
        fh = None
        error_percentage = 0
        caption = ""
        if only_rel_obj:
            if self.ecu_rel_obj_id is not None or self.sil_rel_obj_id is not None:
                self._logger.info("Comparing the relevant object for '{0:}'".format(entry[NAME]))

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
                    except:
                        rel_ob_id = self.ecu_rel_obj_id[j]
                    if rel_ob_id == -1 or rel_ob_id == 255:
                        j += 1
                        continue
                    else:
                        ecu_signal_name = self._get_signal_full_name(DEVICE_PREFIX, entry).format(rel_ob_id)

                        if SIGNAL_INDEX in entry:
                            ecu_signal_temp = self._read_signal(self._ecu_bsig_reader, ecu_signal_name, entry[NAME],
                                                                entry[UNIT], self.ecu_index,
                                                                signal_index=entry[SIGNAL_INDEX],
                                                                index_offset=self.ecu_offset, entry=entry, source='ECU')
                        else:
                            ecu_signal_temp = self._read_signal(self._ecu_bsig_reader, ecu_signal_name, entry[NAME],
                                                                entry[UNIT], self.ecu_index,
                                                                index_offset=self.ecu_offset, entry=entry, source='ECU')

                        jj = j + 1
                        while True:
                            try:
                                if len(self.ecu_rel_obj_id[jj]) > 1:
                                    rel_ob_id_jj = self.ecu_rel_obj_id[jj][0]
                                else:
                                    rel_ob_id_jj = self.ecu_rel_obj_id[jj]
                            except:
                                if jj < len(self.ecu_rel_obj_id):
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
                    except:
                        rel_ob_id = self.sil_rel_obj_id[j]
                    if rel_ob_id == -1 or rel_ob_id == 255:
                        j += 1
                        continue
                    else:
                        sil_signal_name = self._get_signal_full_name(SIL_PREFIX, entry).format(rel_ob_id)

                        if SIGNAL_INDEX in entry:
                            sil_signal_temp = self._read_signal(self._sil_bsig_reader, sil_signal_name, entry[NAME],
                                                                entry[UNIT], self.sil_index,
                                                                signal_index=entry[SIGNAL_INDEX],
                                                                index_offset=self.sil_offset, entry=entry, source='SIL')
                        else:
                            sil_signal_temp = self._read_signal(self._sil_bsig_reader, sil_signal_name, entry[NAME],
                                                                entry[UNIT], self.sil_index,
                                                                index_offset=self.sil_offset, entry=entry, source='SIL')

                        jj = j + 1
                        while True:
                            try:
                                if len(self.sil_rel_obj_id[jj]) > 1:
                                    rel_ob_id_jj = self.sil_rel_obj_id[jj][0]
                                else:
                                    rel_ob_id_jj = self.sil_rel_obj_id[jj]
                            except:
                                if jj < len(self.sil_rel_obj_id):
                                    rel_ob_id_jj = self.sil_rel_obj_id[jj]
                            if jj == len(sil_signal):
                                break
                            elif rel_ob_id == rel_ob_id_jj:
                                jj += 1
                            else:
                                break

                        sil_signal.values[j:jj] = sil_signal_temp.values[j:jj]
                        j = jj

                diff = ecu_signal - sil_signal

                signal_name = (self._config[SIGNAL_BASE_PATH] + entry[SIGNAL]).format(":")
                caption = "ECU and SIL plots for {}".format(signal_name)
                tolerance = entry[TOLERANCE]
                if len(tolerance) == 2:
                    if tolerance[0] == tolerance[1]:
                        caption = "Bit exactness: ECU and SIL plots for {}".format(signal_name)

                fh = self.plot_factory.histogram_plot(ecu_signal, sil_signal,
                                                      tolerance=entry[TOLERANCE])

                deviancies = (len(diff[diff.values < entry[TOLERANCE][0]]) +
                              len(diff[diff.values > entry[TOLERANCE][1]]))
                error_percentage = (deviancies / float(len(diff))) * 100.0
                self.events.append(len(diff))
                self.passed_events.append(len(diff) - deviancies)
                self.results.append(error_percentage)
        elif list_limit:
            ecu_signal_name = self._get_signal_full_name(DEVICE_PREFIX, entry).format(k)
            if SIGNAL_INDEX in entry:
                ecu_signal = self._read_signal(self._ecu_bsig_reader, ecu_signal_name, entry[NAME], entry[UNIT],
                                               self.ecu_index, index_offset=self.ecu_offset,
                                               signal_index=entry[SIGNAL_INDEX], entry=entry, source='ECU')
                sig_idx = entry[SIGNAL_INDEX]
            else:
                ecu_signal = self._read_signal(self._ecu_bsig_reader, ecu_signal_name, entry[NAME], entry[UNIT],
                                               self.ecu_index, index_offset=self.ecu_offset, entry=entry, source='ECU')
                sig_idx = None

            sil_signal_name = self._get_signal_full_name(SIL_PREFIX, entry).format(k)
            if SIGNAL_INDEX in entry:
                sil_signal = self._read_signal(self._sil_bsig_reader, sil_signal_name, entry[NAME],
                                               entry[UNIT], self.sil_index, index_offset=self.sil_offset,
                                               signal_index=entry[SIGNAL_INDEX], entry=entry, source='SIL')
            else:
                sil_signal = self._read_signal(self._sil_bsig_reader, sil_signal_name, entry[NAME], entry[UNIT],
                                               self.sil_index, index_offset=self.sil_offset, entry=entry, source='SIL')

            if not sil_signal or not ecu_signal:
                self.results.append(-1)
                self.events.append(-1)
                self.passed_events.append(-1)
                return True

            # check first entry in the signal to see if it has the len attribute defined
            sig_idx_set_by_ecu_signal = False
            if ecu_signal is not None and hasattr(ecu_signal[0], "__len__"):
                # length attribute is defined, get the length of signal
                ecu_signal_struct_len = len(ecu_signal[0])
                # if signal is an array, but there is no 'signal_index' specified
                # default to 'signal_index=0' (sig_idx=0)
                # and then trigger a re-read of the signal with 'signal_index=0'
                if sig_idx is None and ecu_signal_struct_len > 0:
                    sig_idx = 0
                    sig_idx_set_by_ecu_signal = True
                    ecu_signal_struct_len = 0
                    ecu_signal = self._read_signal(self._ecu_bsig_reader, ecu_signal_name, entry[NAME], entry[UNIT],
                                                   self.ecu_index, index_offset=self.ecu_offset, signal_index=sig_idx,
                                                   entry=entry, source='ECU')
            # except:
            else:
                ecu_signal_struct_len = 0
            if sil_signal is not None and hasattr(sil_signal[0], "__len__"):
                # length attribute is defined, get the length of signal
                sil_signal_struct_len = len(sil_signal[0])
                # if signal is an array, but there is no 'signal_index' specified
                # default to 'signal_index=0' (sig_idx=0)
                # and then trigger a re-read of the signal with 'signal_index=0'
                if (sig_idx is None or sig_idx_set_by_ecu_signal is True) and sil_signal_struct_len > 0:
                    sig_idx = 0
                    sil_signal_struct_len = 0
                    sil_signal = self._read_signal(self._sil_bsig_reader, sil_signal_name, entry[NAME], entry[UNIT],
                                                   self.sil_index, index_offset=self.sil_offset, signal_index=sig_idx,
                                                   entry=entry, source='SIL')
            # except:
            else:
                sil_signal_struct_len = 0
            ignore_flat_line = False
            if "flat_line_test" in entry.keys():
                if entry["flat_line_test"] == 1:
                    ignore_flat_line = False
            if (ecu_signal[0] == sil_signal[0]) and ecu_signal_struct_len == 0 and sil_signal_struct_len == 0 and \
                    (np.all(np.diff(ecu_signal.values) == 0) == True) and \
                    (np.all(np.diff(sil_signal.values) == 0) == True) and ignore_flat_line:
                self.results.append(-2)
                self.events.append(-2)
                self.passed_events.append(-2)
                return True

            if ecu_signal is not None and sil_signal is not None:
                if ecu_signal.values is not None and sil_signal.values is not None:
                    if self.ecu_list_limit.values is not None and self.sil_list_limit.values is not None:
                        # if chosen (Pre)Cluster is not aktive, set value to Zero
                        ecu_signal.values[k >= self.ecu_list_limit.values] = 0
                        sil_signal.values[k >= self.sil_list_limit.values] = 0

                    # calculate the difference and the deviancies
                    i_ecu = 0
                    i_sil = 0
                    diff = []
                    deviancies = 0
                    while i_ecu < len(ecu_signal) and i_sil < len(sil_signal):
                        if ecu_signal.index[i_ecu] < sil_signal.index[i_sil]:
                            i_ecu += 1
                        elif ecu_signal.index[i_ecu] > sil_signal.index[i_sil]:
                            i_sil += 1
                        elif ecu_signal.index[i_ecu] == sil_signal.index[i_sil]:
                            if type(ecu_signal.values[i_ecu]) == list or type(sil_signal.values[i_sil]) == list:
                                tmp_diff = ecu_signal.values[i_ecu][0] - sil_signal.values[i_sil][0]
                            else:
                                tmp_diff = ecu_signal.values[i_ecu] - sil_signal.values[i_sil]
                            diff.append(tmp_diff)
                            if tmp_diff < entry[TOLERANCE][0] or tmp_diff > entry[TOLERANCE][1]:
                                deviancies += 1
                            i_ecu += 1
                            i_sil += 1

                    signal_name = (entry[SIGNAL]).format(k)
                    caption = "ECU and SIL plots for {}".format(signal_name)
                    tolerance = entry[TOLERANCE]
                    if len(tolerance) == 2:
                        if tolerance[0] == tolerance[1]:
                            caption = "Bit exactness: ECU and SIL plots for {}".format(signal_name)

                    fh = self.plot_factory.histogram_plot(ecu_signal, sil_signal,
                                                          tolerance=entry[TOLERANCE])
                    # tolerance = entry[TOLERANCE], title = entry[NAME])
                    error_percentage = (deviancies / float(len(diff))) * 100.0
                    self.events.append(len(diff))
                    self.passed_events.append(len(diff) - deviancies)
                    self.results.append(error_percentage)
        else:
            # read signals from bsig
            ecu_signal_name = self._get_signal_full_name(DEVICE_PREFIX, entry).format(k)
            sil_signal_name = self._get_signal_full_name(SIL_PREFIX, entry).format(k)

            if SIGNAL_INDEX in entry:
                sig_idx = entry[SIGNAL_INDEX]
            else:
                sig_idx = None

            ecu_signal = self._read_signal(self._ecu_bsig_reader, ecu_signal_name, entry[NAME], entry[UNIT],
                                           self.ecu_index, index_offset=self.ecu_offset, signal_index=sig_idx,
                                           entry=entry, source='ECU')

            # check first entry in the signal to see if it has the len attribute defined
            if ecu_signal is not None and hasattr(ecu_signal[0], "__len__"):
                # length attribute is defined, get the length of signal
                ecu_signal_struct_len = len(ecu_signal[0])
                # if signal is an array, but there is no 'signal_index' specified
                # default to 'signal_index=0' (sig_idx=0)
                # and then trigger a re-read of the signal with 'signal_index=0'
                if sig_idx is None and ecu_signal_struct_len > 0:
                    sig_idx = 0
                    ecu_signal_struct_len = 0
                    ecu_signal = self._read_signal(self._ecu_bsig_reader, ecu_signal_name, entry[NAME], entry[UNIT],
                                                   self.ecu_index, self.ecu_offset, signal_index=sig_idx, entry=entry,
                                                   source='ECU')
            # except:
            else:
                ecu_signal_struct_len = 0

            sil_signal = self._read_signal(self._sil_bsig_reader, sil_signal_name, entry[NAME], entry[UNIT],
                                           self.sil_index, index_offset=self.sil_offset, signal_index=sig_idx,
                                           entry=entry, source='SIL')

            if not sil_signal or not ecu_signal:
                self.results.append(-1)
                self.events.append(-1)
                self.passed_events.append(-1)
                return True

            ignore_flat_line = False
            if "flat_line_test" in entry.keys():
                if entry["flat_line_test"] == 1:
                    ignore_flat_line = False

            if (ecu_signal[0] == sil_signal[0]) and ecu_signal_struct_len == 0 and \
                    (np.all(np.diff(ecu_signal.values) == 0) == True) and \
                    (np.all(np.diff(sil_signal.values) == 0) == True) and ignore_flat_line:
                self.results.append(-2)
                self.events.append(-2)
                self.passed_events.append(-2)
                return True
            elif ecu_signal_struct_len >= 1:
                j = 0
                index = []
                diff = []
                deviancies = 0
                for i in range(len(ecu_signal[:])):
                    while j < len(sil_signal[:]) - 1 and ecu_signal.index[i] > sil_signal.index[j]:
                        j += 1
                    if ecu_signal.index[i] == sil_signal.index[j]:
                        index.append(ecu_signal.index[i])
                        for k in range(len(ecu_signal[0])):
                            tmp = ecu_signal[i][k] - sil_signal[j][k]
                            diff.append(tmp)
                            if tmp < entry[TOLERANCE][0] or tmp > entry[TOLERANCE][1]:
                                deviancies += 1

                passed_events = len(diff) - deviancies
                self.events.append(len(diff))
                self.passed_events.append(passed_events)

                fh = self.plot_factory.histogram_plot(ecu_signal, sil_signal,
                                                      tolerance=entry[TOLERANCE])
                error_percentage = (deviancies / float(len(diff))) * 100.0
                self.results.append(error_percentage)
            else:
                diff = ecu_signal.series - sil_signal.series
                if 'percentage' in entry:
                    if entry[PERCENTAGE] == 0:
                        deviancies = (len(diff[diff.values < entry[TOLERANCE][0]]) +
                                      len(diff[diff.values > entry[TOLERANCE][1]]))
                    else:
                        deviancies = 0
                        for i in range(0, len(diff)):
                            index = diff.index[i]
                            value = diff.values[i]
                            if value != 0 and not (math.isnan(value)):
                                if ecu_signal.series[index] == 0 and entry[TOLERANCE][1] / 100 < value < \
                                                entry[TOLERANCE][0] / 100:
                                    deviancies += 1
                                else:
                                    percent = (value * 100) / ecu_signal.series[index]
                                    if percent < entry[TOLERANCE][0] or percent > entry[TOLERANCE][1]:
                                        deviancies += 1
                else:
                    deviancies = (len(diff[diff.values < entry[TOLERANCE][0]]) +
                                  len(diff[diff.values > entry[TOLERANCE][1]]))

                passed_events = len(diff) - deviancies
                self.events.append(len(diff))
                self.passed_events.append(passed_events)

            if ecu_signal_struct_len == 0:
                fh = None
                # noinspection PyBroadException
                try:
                    fh = self.plot_factory.histogram_plot(ecu_signal, sil_signal, tolerance=entry[TOLERANCE])
                except:
                    pass

                if k is not None:
                    signal_name = (entry[SIGNAL] + " [{0:}]").format(k)
                else:
                    signal_name = entry[SIGNAL]
                caption = "ECU and SIL plots for {}".format(signal_name)
                tolerance = entry[TOLERANCE]
                if len(tolerance) == 2:
                    if tolerance[0] == tolerance[1]:
                        caption = "Bit exactness: ECU and SIL plots for {}".format(signal_name)

            try:
                fh = self.plot_factory.histogram_plot(ecu_signal, sil_signal,
                                                      tolerance=entry[TOLERANCE])
                try:
                    error_percentage = (deviancies / float(len(diff))) * 100.0
                except ZeroDivisionError:
                    error_percentage = (deviancies / float(len(diff[~np.isnan(diff)]))) * 100.0
                self.results.append(error_percentage)
            except ZeroDivisionError:
                error_percentage = 0
                self.results.append(error_percentage)
                pass

        if fh is not None:
            caption += " (pass rate: {0:3.2f} %)".format(100 - error_percentage)
            story.add_image(caption, os.path.join(self.out_directory, fh))

        # Warnings:
        if self.messages:
            story.add_heading("Signal Availability Warnings", 2)
            for msg in self.messages:
                story.add_paragraph(msg)
        return True

"""
CHANGE LOG:
-----------
$Log: tc_generic_signals.py  $
Revision 1.1 2020/03/25 20:56:44CET Leidenberger, Ralf (uidq7596)
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/test_cases/project.pj
"""
