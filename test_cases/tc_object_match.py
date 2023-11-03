"""
crt.ecu_sil.tc_generic_signals
------------------------------
Module to compare arbitrary signals and assess their equality as a deviance in percent.
"""
from __future__ import print_function

import copy
import os
from time import *

import numpy as np
from matplotlib import pylab as plt

from framework.util.gbl_defs import GblUnits
from framework.img.viz import AlgoSignal
from framework.val.results import ValTestStep, ValAssessmentStates
from tc_common import BaseTest

DEBUG = 0
TOLERANCE = "tolerance"
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
TIME_TOLERANCE = "time_tolerance"
INDEX_SIGNAL_PATH = "index_signal_path"
SIGNAL_INDEX = "signal_index"
DEFAULT = "default"
EXP_RES = "exp_res"

TIMESTAMP = "time_stamp"
DIS_X = "dis_x"
DIS_Y = "dis_y"
COUNT_CYC = "count_cyc"
VEL_X = "vel_x"
VEL_Y = "vel_y"
ID = "id"
PROB_EXIST = "prob_exist"
REF_ID = "refID"
MATCH = "match"
EXIST = "exist"
M_DIS_X = "m_dis_x"
M_DIS_Y = "m_dis_y"
M_VEL_X = "m_vel_x"
M_VEL_Y = "m_vel_y"
DIF_POS_X = "dif_pos_x"
DIF_POS_Y = "dif_pos_y"
DIF_VEL_X = "dif_vel_x"
DIF_VEL_Y = "dif_vel_y"
DYN_PROP = "dyn_prob"
# INVALID_DIST = 1000  # sibiu
INVALID_DIST = 99999.

TOL_DIS_X = 0.001
TOL_DIS_Y = 0.001
TOL_VEL_X = 0.001
TOL_VEL_Y = 0.001
FACTOR_GATING = 1
LimitLC = 30  # <---- TO LARGE?????
DELTA_T = 60000
EXPAND_FACTOR = 0.1
EXPAND_LOOPS = 100

__author__ = "Ralf Leidenberger"
__copyright__ = "Copyright 2020, Continental AG"
__version__ = "$Revision: 1.1 $"
__maintainer__ = "$Author: Leidenberger, Ralf (uidq7596) $"
__date__ = "$Date: 2020/03/25 20:56:45CET $"


class ObjectMatchTest(BaseTest):

    # init the class
    def __init__(self, data_manager, testcase, config):
        super(ObjectMatchTest, self).__init__(data_manager, testcase, config)
        self.test_results = []
        self.teststep = []
        self.measured_results = []
        self.keys = [COUNT_CYC, TIMESTAMP, DIS_X, DIS_Y, VEL_X, VEL_Y, ID, DYN_PROP]
        self.ecu = {COUNT_CYC: [], TIMESTAMP: [], DIS_X: [], DIS_Y: [], VEL_X: [], VEL_Y: [], ID: [], DYN_PROP: []}
        self.sil = {COUNT_CYC: [], TIMESTAMP: [], DIS_X: [], DIS_Y: [], VEL_X: [], VEL_Y: [], ID: [], DYN_PROP: []}
        self._miss_match = 0
        self._possible_matches = 0
        self.zeros = []
        self._match = 0
        self._multi_match = 0
        self.offset = 0

        self._sync_offset_ecu = 0
        self._sync_offset_sil = 0
        self._sync_len = 0

        self.ecu_index = 0
        self.sil_index = 0
        self.ecu_rel_obj_id = 0
        self.sil_rel_obj_id = 0
        self.sil_orig_index = 0

        self.tol_dis_x = TOL_DIS_X
        self.tol_dis_y = TOL_DIS_Y
        self.tol_vel_x = TOL_VEL_X
        self.tol_vel_y = TOL_VEL_Y
        self.limit_lc = LimitLC
        self.expand_loops = EXPAND_LOOPS
        self.counter = 0

    # unchanged at the moment
    def post_initialize(self):
        # Add teststeps here instead in execute
        try:
            if "matching_factor" in self._config:
                self.expand_loops = int(max((int(self._config["matching_factor"])) / EXPAND_FACTOR, 1))
        except all:
            self.expand_loops = EXPAND_LOOPS
        for m in range(len(self._config["test_steps"])):
            entry = self._config["test_steps"][m]

            try:
                tag = "{0:}-{1:02d}".format(self.testcase.get_spe_tag(), entry["key"])
            except all:
                tag = "{0:}-{1:02d}".format(self.testcase.get_spe_tag(), 1)
            try:
                res_exp = entry["res_exp_operator"] + " " + str(entry["res_exp_value"]) + " " + entry["res_exp_unit"]
            except all:
                res_exp = " "
            name = "Result from: '{0:}'".format(entry[NAME])
            test_step = ValTestStep(name=name, res_type="Deviance", unit=GblUnits.UNIT_L_PERCENTAGE, tag=tag,
                                    exp_res=res_exp)

            self.teststep.append(test_step)

            self.test_results.append([])

    def execute(self, story):
        sil_objs_wo_match = 0
        self._logger.info("Executing New match. {0:}".format(self._config[NAME]))
        story.add_heading("Result plots for recording '{}'".format(os.path.split(
                                                            self._data_manager.get_data_port("currentfile"))[1]), 2)
        # get the ecu offset from cfg file
        if ECU_INDEX_OFFSET in self._config:
            ecu_offset = self._config[ECU_INDEX_OFFSET]
        else:
            ecu_offset = None

        # get the sil offset from cfg file
        if SIL_INDEX_OFFSET in self._config:
            sil_offset = self._config[SIL_INDEX_OFFSET]
        else:
            sil_offset = None

        # indexes
        if INDEX_SIGNAL_PATH in self._config:
            ecu_index_name = (self._config[DEVICE_PREFIX] + self._config[INDEX_SIGNAL_PATH])
            self.ecu_index = np.fromiter(self._ecu_bsig_reader[ecu_index_name], np.int64)
            sil_index_name = (self._config[SIL_PREFIX] + self._config[INDEX_SIGNAL_PATH])
            self.sil_index = np.fromiter(self._sil_bsig_reader[sil_index_name], np.int64)
        else:
            data = self._ecu_bsig_reader[MTS_PACKAGE_TIME_STAMP]
            self.ecu_index = np.fromiter(data, np.long)
            data = self._sil_bsig_reader[MTS_PACKAGE_TIME_STAMP]
            self.sil_orig_index = np.fromiter(data, np.long)
            self.sil_index = np.fromiter(data, np.long)

        # read test configuration
        try:
            tmp_limit_lc = self._config['limit_life_cycles']
            if tmp_limit_lc > 0:
                self.limit_lc = tmp_limit_lc
        except MemoryError:
            self.limit_lc = LimitLC

        # loop about all read signals
        for k in range(len(self._config[SIGNAL_LIST])):
            self.sil[self.keys[k]] = []
            self.ecu[self.keys[k]] = []
            entry = self._config[SIGNAL_LIST][k]
            # read the tolerance from the cfg-script
            if entry['name'] == "DistX":
                tmp_tol_dis_x = float(entry['tolerance'][0])
                if tmp_tol_dis_x > 0:
                    self.tol_dis_x = tmp_tol_dis_x
            elif entry['name'] == "DistY":
                tmp_tol_dis_y = float(entry['tolerance'][0])
                if tmp_tol_dis_y > 0:
                    self.tol_dis_y = tmp_tol_dis_y
            elif entry['name'] == "VrelX":
                tmp_tol_vel_x = float(entry['tolerance'][0])
                if tmp_tol_vel_x > 0:
                    self.tol_vel_x = tmp_tol_vel_x
            elif entry['name'] == "VrelY":
                tmp_tol_vel_y = float(entry['tolerance'][0])
                if tmp_tol_vel_y > 0:
                    self.tol_vel_y = tmp_tol_vel_y
            # sil object signals
            sil_signal_name = (self._config[SIL_PREFIX] + self._config[SIGNAL_BASE_PATH] + entry[SIGNAL])
            if sil_signal_name.find("[{0:}]") >= 0:
                obj_list_size = 0
                while obj_list_size >= 0:
                    if sil_signal_name.format(obj_list_size) in self._sil_bsig_reader.signal_names:
                        obj_list_size += 1
                    else:
                        break
                for l in range(0, obj_list_size):
                    tmp_sil_signal_name = sil_signal_name.format(l)
                    tmp = self._read_signal(self._sil_bsig_reader, tmp_sil_signal_name, entry[NAME],
                                            entry[UNIT], self.sil_index, index_offset=sil_offset,
                                            entry=entry)
                    self.sil[self.keys[k]].append(tmp)
            # sil single signals
            else:
                self.sil[self.keys[k]].append(self._read_signal(self._sil_bsig_reader, sil_signal_name, entry[NAME],
                                                                entry[UNIT], self.sil_index,
                                                                index_offset=sil_offset, entry=entry))

            # ecu object signals
            ecu_signal_name = (self._config[DEVICE_PREFIX] + self._config[SIGNAL_BASE_PATH] + entry[SIGNAL])
            if ecu_signal_name.find("[{0:}]") >= 0:
                obj_list_size = 0
                while obj_list_size >= 0:
                    if ecu_signal_name.format(obj_list_size) in self._ecu_bsig_reader.signal_names:
                        obj_list_size += 1
                    else:
                        break
                for l in range(0, obj_list_size):
                    tmp_ecu_signal_name = ecu_signal_name.format(l)
                    self.ecu_rel_obj_id = self._read_signal(self._ecu_bsig_reader, tmp_ecu_signal_name, entry[NAME],
                                                            entry[UNIT], self.ecu_index, index_offset=ecu_offset,
                                                            entry=entry)
                    self.ecu[self.keys[k]].append(self.ecu_rel_obj_id)
            # ecu single signales
            else:
                self.ecu[self.keys[k]].append(self._read_signal(self._ecu_bsig_reader, ecu_signal_name, entry[NAME],
                                              entry[UNIT], self.ecu_index,
                                              index_offset=ecu_offset, entry=entry))

        # automatic time & cycle sync
        # out commend for taskforce
        sync_state, sync_offset_ecu, sync_offset_sil, _len = self._sync(self.ecu[TIMESTAMP][0], self.sil[TIMESTAMP][0])
        self._sync_offset_ecu = sync_offset_ecu
        self._sync_offset_sil = sync_offset_sil
        self._sync_len = _len
        # _len = np.min([len(self.ecu[DIS_X]), len(self.sil[DIS_X])])
        # self._sync_len =  np.min([len(self.ecu[DIS_X]), len(self.sil[DIS_X])])

        # create & prepare index sets
        ids_sil = set(range(0, len(self.sil[DIS_X]), 1))
        ids_ecu = set(range(0, len(self.ecu[DIS_X]), 1))
        ids_sil_list = []
        ids_ecu_list = []
        tmp_sil_id_set = set(range(0, len(self.sil[DIS_X]), 1))
        tmp_ecu_id_set = set(range(0, len(self.ecu[DIS_X]), 1))

        # create Data fields and template for the data fiels
        sil_objs = []
        ecu_objs = []
        template = {EXIST: ([False] * _len), DIS_X: ([INVALID_DIST] * _len), DIS_Y: ([0.] * _len), VEL_X: ([0.] * _len),
                    VEL_Y: ([0.] * _len), MATCH: ([-1] * _len), M_DIS_X: ([0.] * _len), M_DIS_Y: ([0.] * _len),
                    M_VEL_X: ([0.] * _len), M_VEL_Y: ([0.] * _len), DIF_POS_X: ([0.] * _len), DIF_POS_Y: ([0.] * _len),
                    DIF_VEL_X: ([0.] * _len), DIF_VEL_Y: ([0.] * _len), ID: ([0] * _len), DYN_PROP: ([-1] * _len)}
        while len(sil_objs) < len(ids_sil):
            sil_objs.append(copy.deepcopy(template))
        while len(ecu_objs) < len(ids_ecu):
            ecu_objs.append(copy.deepcopy(template))

        # initialize the data fields
        time_stamp = []
        ecu_data_error = []
        miss_match_list = []
        for k in range(0, len(self.ecu[DIS_X]), 1):
            ecu_data_error.append([])
            miss_match_list.append([])
        for i in range(0, self._sync_len, 1):
            ids_sil_list.append(copy.deepcopy(tmp_sil_id_set))
            ids_ecu_list.append(copy.deepcopy(tmp_ecu_id_set))

            i_sil_time = i + self._sync_offset_sil
            i_ecu_time = i + self._sync_offset_ecu
            if self.ecu[TIMESTAMP][0][i_ecu_time] == self.sil[TIMESTAMP][0][i_sil_time]:
                time_stamp.append(self.ecu[TIMESTAMP][0][i_ecu_time])
            else:
                time_stamp.append(-1)
            for k in range(0, len(self.sil[DIS_X]), 1):
                if self._config['dynamic_properties'] != -1 and len(self.sil[DYN_PROP]) > 0:
                    if (self._config['dynamic_properties'] == 0 and self.sil[DYN_PROP][k][i_sil_time] == 1) or\
                       (self._config['dynamic_properties'] == 1 and self.sil[DYN_PROP][k][i_sil_time] != 1):
                        sil_objs[k][DIS_X][i] = self.sil[DIS_X][k][i_sil_time]
                        sil_objs[k][DIS_Y][i] = self.sil[DIS_Y][k][i_sil_time]
                        sil_objs[k][VEL_X][i] = self.sil[VEL_X][k][i_sil_time]
                        sil_objs[k][VEL_Y][i] = self.sil[VEL_Y][k][i_sil_time]
                        sil_objs[k][ID][i] = self.sil[ID][k][i_sil_time]
                        sil_objs[k][EXIST][i] = True
                else:
                    sil_objs[k][DIS_X][i] = self.sil[DIS_X][k][i_sil_time]
                    sil_objs[k][DIS_Y][i] = self.sil[DIS_Y][k][i_sil_time]
                    sil_objs[k][VEL_X][i] = self.sil[VEL_X][k][i_sil_time]
                    sil_objs[k][VEL_Y][i] = self.sil[VEL_Y][k][i_sil_time]
                    sil_objs[k][ID][i] = self.sil[ID][k][i_sil_time]
                    sil_objs[k][EXIST][i] = True
            for k in range(0, len(self.ecu[DIS_X]), 1):
                if self._config['dynamic_properties'] != -1 and len(self.sil[DYN_PROP]) > 0:
                    if (self._config['dynamic_properties'] == 0 and self.ecu[DYN_PROP][k][i_ecu_time] == 1) or\
                       (self._config['dynamic_properties'] == 1 and self.ecu[DYN_PROP][k][i_ecu_time] != 1):
                        ecu_objs[k][DIS_X][i] = self.ecu[DIS_X][k][i_ecu_time]
                        ecu_objs[k][DIS_Y][i] = self.ecu[DIS_Y][k][i_ecu_time]
                        ecu_objs[k][VEL_X][i] = self.ecu[VEL_X][k][i_ecu_time]
                        ecu_objs[k][VEL_Y][i] = self.ecu[VEL_Y][k][i_ecu_time]
                        ecu_objs[k][ID][i] = self.ecu[ID][k][i_ecu_time]
                        if self.ecu[DIS_X][k][i_ecu_time] != INVALID_DIST:
                            ecu_objs[k][EXIST][i] = True
                        else:
                            ecu_data_error[k].append(i)
                else:
                    ecu_objs[k][DIS_X][i] = self.ecu[DIS_X][k][i_ecu_time]
                    ecu_objs[k][DIS_Y][i] = self.ecu[DIS_Y][k][i_ecu_time]
                    ecu_objs[k][VEL_X][i] = self.ecu[VEL_X][k][i_ecu_time]
                    ecu_objs[k][VEL_Y][i] = self.ecu[VEL_Y][k][i_ecu_time]
                    ecu_objs[k][ID][i] = self.ecu[ID][k][i_ecu_time]
                    if self.ecu[DIS_X][k][i_ecu_time] != INVALID_DIST:
                        ecu_objs[k][EXIST][i] = True
                    else:
                        ecu_data_error[k].append(i)

        tmp_set1 = set()
        tmp_set3 = set()
        _before = 0

        # global match loop
        for i in range(0, self._sync_len, 1):
            # ignore invalid time stamps but but don't forget active matches
            if time_stamp[i] == -1:
                for k in ids_ecu_list[i]:
                    ecu_objs[k][EXIST][i] = False
                    ecu_objs[k][DIS_X][i] = INVALID_DIST
                    if ecu_objs[k][MATCH][_before] > 0:
                        ecu_objs[k][MATCH][i] = -ecu_objs[k][MATCH][_before] - 2
                    else:
                        ecu_objs[k][MATCH][i] = ecu_objs[k][MATCH][_before]
                _before = i
                continue

            for k in ids_ecu_list[i]:
                # if exist an previous match check if this is possible
                if ecu_objs[k][MATCH][_before] != -1 and ecu_objs[k][ID][i] == ecu_objs[k][ID][_before]:
                    match = ecu_objs[k][MATCH][_before]
                    if match < -1:
                        index = (match + 2) * -1
                    else:
                        index = match
                    factor = FACTOR_GATING
                    dif_pos_x = abs(sil_objs[index][DIS_X][i] - ecu_objs[k][DIS_X][i])
                    dif_pos_y = abs(sil_objs[index][DIS_Y][i] - ecu_objs[k][DIS_Y][i])
                    dif_vel_x = abs(sil_objs[index][VEL_X][i] - ecu_objs[k][VEL_X][i])
                    dif_vel_y = abs(sil_objs[index][VEL_Y][i] - ecu_objs[k][VEL_Y][i])

                    if (dif_pos_x < self.tol_dis_x*factor and dif_pos_y < self.tol_dis_y*factor and
                       dif_vel_x < self.tol_vel_x*factor and dif_vel_y < self.tol_vel_x*factor and
                       sil_objs[index][ID][i] == sil_objs[index][ID][_before]):
                        ecu_objs[k][MATCH][i] = index
                        ecu_objs[k][DIF_POS_X][i] = dif_pos_x
                        ecu_objs[k][DIF_POS_Y][i] = dif_pos_y
                        ecu_objs[k][DIF_VEL_X][i] = dif_vel_x
                        ecu_objs[k][DIF_VEL_Y][i] = dif_vel_y
                        ecu_objs[k][M_DIS_X][i] = sil_objs[index][DIS_X][i]
                        ecu_objs[k][M_DIS_Y][i] = sil_objs[index][DIS_Y][i]
                        ecu_objs[k][M_VEL_X][i] = sil_objs[index][VEL_X][i]
                        ecu_objs[k][M_VEL_Y][i] = sil_objs[index][VEL_Y][i]
                        tmp_set1.add(k)
                        tmp_set3.add(index)
                    elif (ecu_objs[k][DIS_X][i] == INVALID_DIST and
                          ecu_objs[k][ID][i] == ecu_objs[k][ID][_before] and
                          sil_objs[index][ID][i] == sil_objs[index][ID][_before]):
                        ecu_objs[k][MATCH][i] = index
                        ecu_objs[k][M_DIS_X][i] = sil_objs[index][DIS_X][i]
                        ecu_objs[k][M_DIS_Y][i] = sil_objs[index][DIS_Y][i]
                        ecu_objs[k][M_VEL_X][i] = sil_objs[index][VEL_X][i]
                        ecu_objs[k][M_VEL_Y][i] = sil_objs[index][VEL_Y][i]
                        tmp_set1.add(k)
                        tmp_set3.add(index)
            ids_ecu_list[i] = ids_ecu_list[i].difference(tmp_set1)
            ids_sil_list[i] = ids_sil_list[i].difference(tmp_set3)
            tmp_set1.clear()
            tmp_set3.clear()

            # remove all ecu objects which are not exist from the search set
            for k in ids_ecu_list[i]:
                if not ecu_objs[k][EXIST][i]:
                    ecu_objs[k][DIS_X][i] = INVALID_DIST
                    tmp_set1.add(k)
            ids_ecu_list[i] = ids_ecu_list[i].difference(tmp_set1)
            tmp_set1.clear()

            # remove all ecu object which exist less than self.limit_lc
            for k in ids_ecu_list[i]:
                counter = 1
                id_tmp = ecu_objs[k][ID][i]
                for l in range(i + 1, min(self._sync_len, i + 1*self.limit_lc), 1):
                    if ecu_objs[k][ID][l] == id_tmp:
                        counter += 1
                    else:
                        break
                for l in range(max(i-1, 0), max(0, i - 1*self.limit_lc), -1):
                    if ecu_objs[k][ID][l] == id_tmp:
                        counter += 1
                    else:
                        break
                if counter < self.limit_lc:
                    tmp_set1.add(k)
                    ecu_objs[k][EXIST][i] = False
                    ecu_objs[k][DIS_X][i] = INVALID_DIST
            ids_ecu_list[i] = ids_ecu_list[i].difference(tmp_set1)
            tmp_set1.clear()

            # remove all ecu objects which have no distance because this is an error in the datas
            for k in ids_ecu_list[i]:
                if ecu_objs[k][DIS_X][i] == INVALID_DIST:
                    tmp_set1.add(k)
            ids_ecu_list[i] = ids_ecu_list[i].difference(tmp_set1)
            tmp_set1.clear()

            # search for each unmatch ecu object an sil object

            tol_x = self.tol_dis_x * EXPAND_FACTOR
            tol_y = self.tol_dis_y * EXPAND_FACTOR
            v_tol_x = self.tol_vel_x * EXPAND_FACTOR
            v_tol_y = self.tol_vel_y * EXPAND_FACTOR
            # loop to expand the search area for each point, we start with a very small area to reduce wrong matches
            for j in range(0, self.expand_loops, 1):
                # loop about all ecu objects in the actual time step
                for k in ids_ecu_list[i]:
                    [ecu_objs[k][MATCH][i], ecu_objs[k][DIF_POS_X][i],  ecu_objs[k][DIF_POS_Y][i],
                     ecu_objs[k][DIF_VEL_X][i], ecu_objs[k][DIF_VEL_Y][i], ecu_objs[k][M_DIS_X][i],
                     ecu_objs[k][M_DIS_Y][i], ecu_objs[k][M_VEL_X][i], ecu_objs[k][M_VEL_Y][i]] = \
                        self.match(ecu_objs[k], sil_objs, ids_sil_list[i], i, tol_x, tol_y, v_tol_x, v_tol_y)
                    if ecu_objs[k][MATCH][i] != -1:
                        tmp_set1.add(k)
                        sil_objs[ecu_objs[k][MATCH][i]][MATCH][i] = 1
                        ids_sil_list[i].discard(ecu_objs[k][MATCH][i])
                # expand the tolerance
                tol_x += self.tol_dis_x * EXPAND_FACTOR
                tol_y += self.tol_dis_y * EXPAND_FACTOR
                v_tol_x += self.tol_vel_x * EXPAND_FACTOR
                v_tol_y += self.tol_vel_y * EXPAND_FACTOR
                ids_ecu_list[i] = ids_ecu_list[i].difference(tmp_set1)
                tmp_set1.clear()
            # collect all unmatched sil objects
            for k in ids_sil_list[i]:
                miss_match_list[k].append(i)
            _before = i

        # no start the evaluation of the match
        rate_list = []
        match_list = []
        no_match = 0
        incorrect_match = 0
        miss_match = 0
        possible_match = 0
        absolute_match = 0
        sum_objects = 0
        sum_matched = 0

        _len = len(time_stamp)
        time_miss_match = []
        counter = 0
        plot_time = []
        # interpolate, store & count the time miss matches / shift the start point to 0 / scale the time to seconds
        for i in range(0, _len, 1):
            if time_stamp[i] == -1:
                j = min(i+1, _len-1)
                while time_stamp[j] == -1:
                    j += 1
                    if j == _len:
                        break
                if j != 0 and j != _len:
                    time_stamp[i] = time_stamp[i - 1] + (time_stamp[j] - time_stamp[i - 1]) / (j - i)
                elif j == 0:
                    time_stamp[i] = max(time_stamp[j] - DELTA_T * (j - i), 0)
                else:
                    time_stamp[i] = time_stamp[i-1] + DELTA_T
                time_miss_match.append(float(time_stamp[i] - time_stamp[0]) / 1000000)
                counter += 1
            plot_time.append((time_stamp[i] - time_stamp[0]) * 1.e-6)
        tmp_list = []

        # loop to store all ecu data erros at the correct plot time
        for i in range(0, len(ecu_data_error), 1):
            for k in range(0, len(ecu_data_error[i]), 1):
                ecu_data_error[i][k] = plot_time[ecu_data_error[i][k]]

        # loop to store all miss matches at the correct plot time
        for i in range(0, len(miss_match_list), 1):
            for k in range(0, len(miss_match_list[i]), 1):
                miss_match_list[i][k] = plot_time[miss_match_list[i][k]]

        # loop to evaluate the and collect the data about all match results
        for l in ids_ecu:
            rate = self.check(ecu_objs[l])
            rate_list.append([float(rate[0]) / rate[3]*100, float(rate[1]) / rate[3]*100, float(rate[2]) / rate[3]*100,
                              float(rate[5]) / rate[3]*100, float(rate[6]) / rate[3]*100, float(rate[7]) / rate[3]*100,
                              float(rate[8]) / rate[3]*100, l])
            no_match += rate[0]             # ecu object points without an sil object point
            incorrect_match += rate[1]      # ecu point with match but the match do not passed the tolerance
            miss_match += rate[2]           # sum of no_match and incorrect_match
            possible_match += rate[3]       # all ecu objects
            absolute_match += rate[4]       # all ecu data points
            id_, s_id, e_id, match, s_match, e_match, id_match, s_id_match, e_id_match, match_rate, match_time_rate,\
                n_objects, n_matched = self.analyse_id(plot_time, ecu_objs[l])
            if n_objects == 0:
                continue
            match_list.append({ID: id_, 's_id': s_id, 'e_id': e_id, 'id_match': id_match, 's_id_match': s_id_match,
                               'e_id_match': e_id_match, 'match_rate': match_rate, 'match_time_rate': match_time_rate,
                               'index': l})
            sum_objects += n_objects                                           # sum of all ecu objects
            sum_matched += n_matched                                           # sum of all matched ecu objects
            sil_objs_wo_match += self.count_unmatched(plot_time, sil_objs[l])  # sum of sil objects with no ecu object

            last_id = -1
            # loop to collect all single objects
            for i in range(0, _len, 1):
                if ecu_objs[l][EXIST][i]:
                    if ecu_objs[l][ID][i] != last_id:
                        last_id = ecu_objs[l][ID][i]
                        tmp_list.append({'listID': l, 'start': i, 'end': i, 'correction': 0, 'rate': 0, 'rate_pos_x': 0,
                                         'rate_pos_y': 0, 'rate_vel_x': 0, 'rate_vel_y': 0})
                    else:
                        tmp_list[-1]['end'] = i
                        if ecu_objs[l][DIS_X][i] == INVALID_DIST:
                            tmp_list[-1]['correction'] += 1

        single_obj_list = []
        number_obj = 0
        # remove all single objects which exist shorter than  self.limit_lc
        for i in range(len(tmp_list)-1, -1, -1):
            if tmp_list[i]['end']-tmp_list[i]['start']+1 >= self.limit_lc:
                number_obj += 1
                single_obj_list.append(tmp_list[i])

        # loop to compute the match rates fpr all single objects
        for i in range(0, number_obj, 1):
            start = single_obj_list[i]['start']
            end = single_obj_list[i]['end']
            correction = single_obj_list[i]['correction']
            tmp = self.rate(ecu_objs[single_obj_list[i]['listID']], start, end)
            single_obj_list[i]['rate'] = float(tmp[2]) / (end - start + 1 - correction)*100
            single_obj_list[i]['rate_pos_x'] = float(tmp[5]) / (end - start + 1 - correction)*100
            single_obj_list[i]['rate_pos_y'] = float(tmp[6]) / (end - start + 1 - correction)*100
            single_obj_list[i]['rate_vel_x'] = float(tmp[7]) / (end - start + 1 - correction)*100
            single_obj_list[i]['rate_vel_y'] = float(tmp[8]) / (end - start + 1 - correction)*100

        match_result = sorted(match_list, key=lambda x: 100-x['match_rate'])

        # insert the test criteria in the report
        self.report_test_criteria(story)

        # check the test steps and insert the results in the report
        self.check_test_steps(story, sum_objects, possible_match, sum_matched, sil_objs_wo_match, no_match,
                              miss_match)

        # insert the best and worst object list entry in the report
        self.report_object_list(story, match_result, ecu_objs)

        for i in range(0, len(plot_time), 1):
            for k in range(0, len(ecu_objs), 1):

                if ecu_objs[k][ID][i] == 7 and 270 > plot_time[i] > 250 and ecu_objs[k][MATCH][i] != -1:
                    print('DIF_POS_X:', ecu_objs[k][DIF_POS_X][i], 'TIME_STAMP:', plot_time[i], 'ecu ID',
                          ecu_objs[k][ID][i], 'sil ID', ecu_objs[k][MATCH][i], ecu_objs[k][DIS_X][i],
                          ecu_objs[k][M_DIS_X][i])
                    for l in range(0, len(time_miss_match), 1):
                        if (plot_time[i] - 0.070) < time_miss_match[l] < (plot_time[i] + 0.070):
                            print(i, '---DIF_POS_X:', ecu_objs[k][DIF_POS_X][i], 'TIME_STAMP:', plot_time[i], 'ecu ID',
                                  ecu_objs[k][ID][i], 'sil ID', ecu_objs[k][MATCH][i], ecu_objs[k][DIS_X][i],
                                  ecu_objs[k][M_DIS_X][i])
        return

    @staticmethod
    def _sync(ecu, sil):
        sync_state = False
        sync_len = 0
        i = 0
        k = 0
        if sil is not None and ecu is not None:

            while not sync_state and i < len(ecu) and k < len(sil):
                if ecu[i] < sil[k]:
                    i += 1
                    continue
                if ecu[i] > sil[k]:
                    k += 1
                    continue
                if ecu[i] == sil[k]:
                    sync_state = True
            sync_len = np.min([len(ecu)-i, len(sil)-k])
        return sync_state, i, k, sync_len

    # function to read the signals selected signals
    def _read_signal(self, reader, signal, name, unit, index, index_offset=None, signal_index=None, entry=None):
        # noinspection PyBroadException
        try:
            raw_data = reader[signal]
            if signal_index is not None:
                raw_data = list(zip(*raw_data)[signal_index])
            if DEFAULT in entry:
                index = index[np.array(raw_data[:]) != entry[DEFAULT]]
                raw_data = list(np.array(raw_data)[np.array(raw_data[:]) != entry[DEFAULT]])
        except Exception:
            msg = "Signal '{0:}' not available in BSIG".format(signal)
            self._logger.warn(msg)
            return

        if index_offset:
            raw_data = raw_data[index_offset:]
            index = index[index_offset:]
            return AlgoSignal(name, raw_data, index, unit)

        if DEBUG:
            l = 0
            u = index.argmax() + 1
            return AlgoSignal(name, raw_data[l:u], index[l:u], unit)
        else:
            return AlgoSignal(name, raw_data, index, unit)

    # function to find an object match
    @staticmethod
    def match(element, ref, ref_set, index, tol_x, tol_y, v_tol_x, v_tol_y):
        candidates = []
        candidate = []
        # pre match loop match only possition
        for i in ref_set:
            norm_p_x = abs(element[DIS_X][index] - ref[i][DIS_X][index])
            norm_p_y = abs(element[DIS_Y][index] - ref[i][DIS_Y][index])
            if norm_p_x < tol_x and norm_p_y < tol_y:
                candidates.append({ID: i, 'norm_p_x': norm_p_x, 'norm_p_y': norm_p_y, 'norm_v_x': 0,
                                   'norm_v_y': 0,
                                   'norm': 0, DIS_X: ref[i][DIS_X][index], DIS_Y: ref[i][DIS_Y][index],
                                   VEL_X: ref[i][VEL_X][index], VEL_Y: ref[i][VEL_Y][index]})
        # match also with velocity (and position)
        if len(candidates) > 0:
            for e in candidates:
                norm_v_x = abs(e[VEL_X] - element[VEL_X][index])
                norm_v_y = abs(e[VEL_Y] - element[VEL_Y][index])
                if norm_v_x < v_tol_x and norm_v_y < v_tol_y:
                    e['norm'] = e['norm_p_x'] + e['norm_p_y'] + norm_v_x + norm_v_y
                    e['norm_v_x'] = norm_v_x
                    e['norm_v_y'] = norm_v_y
                    candidate.append(e)
            if len(candidate) > 0:
                match_object = sorted(candidate, key=lambda dist: dist["norm"])[0]
                # return the best match
                return [match_object[ID], match_object['norm_p_x'], match_object['norm_p_y'], match_object['norm_v_x'],
                        match_object['norm_v_y'], match_object[DIS_X], match_object[DIS_Y], match_object[VEL_X],
                        match_object[VEL_Y]]
        return [-1, -0.25, -0.25, -0.125, -0.125, 0, 0, 0, 0]

    def check(self, elements):
        return self.rate(elements, 0, len(elements[EXIST]) - 1)

    # function to compute the matching rates
    def rate(self, elements, start, end):
        no_match = 0
        incorrect_match = 0
        incorrect_pos_x = 0
        incorrect_pos_y = 0
        incorrect_vel_x = 0
        incorrect_vel_y = 0

        # possible_match = sum(e for e in elements[EXIST])
        possible_match = 0
        for i in range(start, end+1, 1):
            if elements[DIS_X][i] != INVALID_DIST:
                possible_match += 1
            else:
                continue
            if elements[DIF_POS_X][i] < 0 or elements[DIF_POS_Y][i] < 0 or\
               elements[DIF_VEL_X][i] < 0 or elements[DIF_VEL_Y][i] < 0:
                no_match += 1
                continue
            if elements[DIF_POS_X][i] > self.tol_dis_x or\
               elements[DIF_POS_Y][i] > self.tol_dis_y or\
               elements[DIF_VEL_X][i] > self.tol_vel_x or\
               elements[DIF_VEL_Y][i] > self.tol_vel_x:
                incorrect_match += 1
            if elements[DIF_POS_X][i] > self.tol_dis_x:
                incorrect_pos_x += 1
            if elements[DIF_POS_Y][i] > self.tol_dis_y:
                incorrect_pos_y += 1
            if elements[DIF_VEL_X][i] > self.tol_vel_x:
                incorrect_vel_x += 1
            if elements[DIF_VEL_Y][i] > self.tol_vel_x:
                incorrect_vel_y += 1
        if possible_match == 0:
            possible_match = 1
        return [no_match, incorrect_match, no_match+incorrect_match, possible_match, len(elements[EXIST]),
                incorrect_pos_x, incorrect_pos_y, incorrect_vel_x, incorrect_vel_y]

    def pre_terminate(self):
        self._logger.debug("PreTerminate - Generic Signals")

        for m in range(len(self._config["test_steps"])):
            entry = self._config["test_steps"][m]
            if self.measured_results[m] > entry["res_exp_value"]:
                self.teststep[m].add_assessment(self._mk_assessment(ValAssessmentStates.FAILED))
            else:
                self.teststep[m].add_assessment(self._mk_assessment(ValAssessmentStates.PASSED))

            self.teststep[m].set_value(self.measured_results[m])

            self.testcase.add_test_step(self.teststep[m])

    # function to compute the plot ranges
    @staticmethod
    def plot_range(elements_list):
        range_min = -1
        range_max = 1
        if len(elements_list[0]) > 0:
            range_min = min(elements_list[0])
            range_max = max(elements_list[0])

        for l in range(1, len(elements_list), 1):
            if len(elements_list[l]) > 0:
                range_min = min(range_min, min(elements_list[l]))
                range_max = max(range_max, max(elements_list[l]))

        delta_range = abs(range_max - range_min) * 0.02

        min_ = abs(range_min) * 0.02
        if min_ > 0:
            offset_min = min(delta_range, min)
        else:
            offset_min = delta_range

        max_ = abs(range_max) * 0.02
        if max_ > 0:
            offset_max = min(delta_range, max)
        else:
            offset_max = delta_range

        range_min = range_min - offset_min
        range_max = range_max + offset_max

        return [range_min, range_max]

    # function to plot the displacement
    def plot_displacement(self, x_values, y_values, x_label, y_label):
        # Plot with 2 subplots
        plt.figure(num=2, figsize=(9, 9), dpi=120, facecolor='w', edgecolor='k')
        # Both signals
        plt.plot([0, 1], [0, 1])
        plt.xlabel(y_label)
        plt.ylabel(x_label)
        plt.plot(y_values, x_values, label='', color='blue', linestyle='None', marker='x', markersize=2)
        plt.grid()
        plt.legend(loc='upper right')
        plt.xlim(self.plot_range([y_values]))
        plt.ylim(self.plot_range([x_values]))

        plt.tight_layout()
        filename = "match_plot_{0:}.jpg".format(str(time()))
        path = os.path.join(self.out_directory, filename)
        plt.savefig(path)
        plt.close()
        return filename

    # function to analyse the object matching and the time matching for an list entry
    def analyse_id(self, time_, ref):
        tmp_id = []
        tmp_id_match = []
        tmp_match = []
        tmp_orig_id = []
        time_id = []
        time_match = []
        time_id_match = []
        no_change = False
        # loop to collect all objects an find the matches of all objects
        for i in range(0, len(time_), 1):
            if ref[DIS_X][i] != INVALID_DIST:
                tmp_id.append(ref[ID][i])
                time_id.append(time_[i])
                no_change = True
                if ref[MATCH][i] >= 0:
                    tmp_id_match.append(ref[ID][i])
                    tmp_orig_id.append(ref[MATCH][i])
                    time_id_match.append(time_[i])
            elif len(time_id) > 0:
                if tmp_id[-1] == ref[ID][i] and no_change:
                    tmp_id.append(ref[ID][i])
                    time_id.append(time_[i])
                    if ref[MATCH][i] >= 0:
                        tmp_id_match.append(ref[ID][i])
                        tmp_orig_id.append(ref[MATCH][i])
                        time_id_match.append(time_[i])
                else:
                    no_change = False
            if ref[MATCH][i] >= 0:
                tmp_match.append(ref[MATCH][i])
                time_match.append(time_[i])
        if len(tmp_id) == 0 or len(tmp_match) == 0:
            return [], [], [], [], [], [], [], [], [], 0, 0, 0, 0
        id_ = [tmp_id[0]]
        start = [time_id[0]]
        end = [time_id[0]]
        # loop to concentrate the objects
        for i in range(1, len(tmp_id), 1):
            if id_[-1] == tmp_id[i]:
                end[-1] = time_id[i]
            else:
                id_.append(tmp_id[i])
                start.append(time_id[i])
                end.append(time_id[i])

        match = [tmp_match[0]]
        start_match = [time_match[0]]
        end_match = [time_match[0]]
        # loop to concentrate the match objects
        for i in range(1, len(tmp_match), 1):
            if match[-1] == tmp_match[i]:
                end_match[-1] = time_match[i]
            else:
                match.append(tmp_match[i])
                start_match.append(time_match[i])
                end_match.append(time_match[i])

        id_match = [tmp_id_match[0]]
        start_id_match = [time_id_match[0]]
        end_id_match = [time_id_match[0]]
        orig_id = [[tmp_orig_id[0]]]
        orig_change = [[time_id_match[0]]]
        # loop to concentrate the match objects with object ids
        for i in range(1, len(tmp_id_match), 1):
            if id_match[-1] == tmp_id_match[i]:
                end_id_match[-1] = time_id_match[i]
                if orig_id[-1][-1] != tmp_orig_id[i]:
                    orig_id[-1].append(tmp_orig_id[i])
                    orig_change[-1].append(time_id_match[i])
            else:
                id_match.append(tmp_id_match[i])
                orig_id.append([tmp_orig_id[i]])
                start_id_match.append(time_id_match[i])
                end_id_match.append(time_id_match[i])
                orig_change.append([time_id_match[i]])
                continue

        match_check = [0]*len(id_)
        match_passed = [False]*len(id_)
        id_duration = []
        pairs = []
        # loop to compute the time match
        for i in range(0, len(id_), 1):
            id_duration.append(end[i] - start[i])
            pairs.append([id_[i]])
            for k in range(0, len(end_id_match), 1):
                if start_id_match[k] >= start[i]:
                    if end_id_match[k] <= end[i]:
                        match_check[i] += end_id_match[k] - start_id_match[k]
                        match_passed[i] = True
                    else:
                        break
            if len(orig_id) > i:
                if len(orig_id[i]) > 1:
                    self.counter += 1
                    if id_[i] == 7:
                        print('The ECU ID', id_[i], ' is match with the ', len(orig_id[i]), 'SIL IDs:', orig_id[i],
                              ' about the time. Delta T:', start[i], orig_change[i], end[i]-start[i], self.counter)
        match_rate = float(sum(x for x in match_passed))/len(id_)*100
        match_time_rate = float(sum(x for x in match_check))/sum(x for x in id_duration)*100
        return id_, start, end, match, start_match, end_match, id_match, start_id_match, end_id_match, match_rate,\
            match_time_rate, len(id_), sum(x for x in match_passed)

    # function to count all Objects which exist more then LIMIT_LC which are unmatched
    def count_unmatched(self, time_, ref):
        tmp_unmatched = []
        time_unmatched = []
        for i in range(0, len(time_), 1):
            if ref[MATCH][i] < 0:
                tmp_unmatched.append(ref[ID][i])
                time_unmatched.append(time_[i])

        unmatched = [tmp_unmatched[0]]
        start = [time_unmatched[0]]
        end = [time_unmatched[0]]
        delta = [0]
        for i in range(1, len(tmp_unmatched), 1):
            if unmatched[-1] == tmp_unmatched[i]:
                end[-1] = time_unmatched[i]
                delta[-1] = (end[-1]-start[-1])/DELTA_T
            else:
                unmatched.append(tmp_unmatched[i])
                start.append(time_unmatched[i])
                end.append(time_unmatched[i])
                delta.append(0)

        counter_unmatched = 0
        for d in delta:
            if d > self.limit_lc:
                counter_unmatched += 1
        return counter_unmatched

    # function to insert the test criteria with the description
    def report_test_criteria(self, story):
        story.add_paragraph(" ")
        story.add_paragraph("The following table shows test configuration and the pass criteria.")
        story.add_paragraph(" ")
        if self._config['dynamic_properties'] == -1:
            dyn_description = "STANDING & MOVING"
        elif self._config['dynamic_properties'] == 0:
            dyn_description = "STANDING"
        elif self._config['dynamic_properties'] == 1:
            dyn_description = "MOVING"
        else:
            dyn_description = "undefined"

        header = ['Description',  'Configuration Value']
        data = [['Minimum life cycles of a considered Object', str(self.limit_lc)],
                ['Dynamic Properties of a considered Object', dyn_description]]
        story.add_table('Configured Filter criteria', data, header=header)
        story.add_paragraph("The 'Minimum life cycles of an Object' descripbs the number of the cycles which an (ECU)"
                            " Object have to exist that it is consider for the matching process.")
        story.add_paragraph("The Dynamic Properties allows to consider, all (moving & standing),"
                            " only moving, or only moving objects for the match algorithm")

        header = ['Description',  'Pass Tolerance', 'Match Tolernace', 'Unit']
        data = [['Minimum life cycles of an Object', str(self.limit_lc), '-', '-'],
                ['Tolerance - Distance x', str(self.tol_dis_x), str(self.tol_dis_x * self.expand_loops * EXPAND_FACTOR),
                 'm'],
                ['Tolerance - Distance y', str(self.tol_dis_y), str(self.tol_dis_y * self.expand_loops * EXPAND_FACTOR),
                 'm'],
                ['Tolerance - Velocity x', str(self.tol_vel_x), str(self.tol_vel_x * self.expand_loops * EXPAND_FACTOR),
                 'm/s'],
                ['Tolerance - Velocity y', str(self.tol_vel_y), str(self.tol_vel_y * self.expand_loops * EXPAND_FACTOR),
                 'm/s']]
        story.add_table('Configured Test criteria', data, header=header)

        story.add_paragraph("The 'Tolerance - Distance' describes the accepted tolerance for the local distance between"
                            " an ECU and a SIL object, so that the match is valid. There are different tolerances for"
                            " the x and y direction possible.")
        story.add_paragraph("The 'Tolerance - Velocity describes the accepted tolerance for the relative velocity"
                            " between an ECU and a SIL Object, so that the match is valid. There are different"
                            " tolerance for the relative x and y velocity possible.")
        story.add_paragraph("")
        story.add_paragraph(" The configuration is set in the loaded *.cfg file.")
        story.add_space(1)

    # function to check test steps
    def check_test_steps(self, story, sum_objects, possible_match, sum_matched, sil_objs_wo_match, no_match,
                         incorrect_match):
        story.add_paragraph("The table shows the absolute and relative values for the test steps with the pass"
                            " criteria.")
        header = ['Description',  'Value', 'Passed - Result', 'Passed - Tolerance']
        data1 = [['Number of objects', str(sum_objects), '-', '-']]
        data2 = [['Number of objects points', str(possible_match), '-', '-']]
        if sum_objects == 0:
            sum_objects = 1
        if possible_match == 0:
            possible_match = 1
        for m in range(len(self._config["test_steps"])):
            entry = self._config["test_steps"][m]
            type_ = entry["type"]
            if type_ == 1:
                tmp_value = round(100. - float(sum_matched) / sum_objects * 100, 4)
                self.teststep[m].set_value(tmp_value)
                data1.append(
                    ['Matched objects', str(sum_matched), str(round(float(sum_matched) / sum_objects * 100, 4)) + '%',
                     str(100 - entry['res_exp_value']) + '%'])
                if tmp_value <= entry['res_exp_value']:
                    assessment = ValAssessmentStates.PASSED
                else:
                    assessment = ValAssessmentStates.FAILED
            elif type_ == 2:
                tmp_value = round(float(sil_objs_wo_match) / sum_objects*100, 4)
                self.teststep[m].set_value(tmp_value)
                data1.append(['Number of unmatched SIL objects', str(sil_objs_wo_match),
                             str(round(100. - float(sil_objs_wo_match) / sum_objects * 100, 4)) + '%',
                             str(100 - entry['res_exp_value']) + '%'])
                if tmp_value <= entry['res_exp_value']:
                    assessment = ValAssessmentStates.PASSED
                else:
                    assessment = ValAssessmentStates.FAILED
            elif type_ == 3:
                tmp_value = round(float(no_match)/possible_match*100, 4)
                self.teststep[m].set_value(tmp_value)
                data2.append(['Matched object points', str(possible_match - no_match),
                             str(round(100. - float(no_match) / possible_match * 100, 4)) + '%',
                             str(100 - entry['res_exp_value']) + '%'])
                if tmp_value <= entry['res_exp_value']:
                    assessment = ValAssessmentStates.PASSED
                else:
                    assessment = ValAssessmentStates.FAILED
            elif type_ == 4:  # miss_match
                tmp_value = round(float(incorrect_match) / possible_match * 100, 4)
                self.teststep[m].set_value(tmp_value)
                data2.append(['Valid object points', str(possible_match - incorrect_match),
                             str(round(100. - float(incorrect_match) / possible_match * 100, 4)) + '%',
                             str(100 - entry['res_exp_value']) + '%'])
                if tmp_value <= entry['res_exp_value']:
                    assessment = ValAssessmentStates.PASSED
                else:
                    assessment = ValAssessmentStates.FAILED
            else:
                continue
            self.test_results[m].append(assessment)
            self.measured_results.append(tmp_value)
        story.add_paragraph(" ")
        data = []
        for l in data1:
            data.append(l)
        for l in data2:
            data.append(l)
        story.add_table('Results of the Object Match', data, header=header)
        story.add_space(1)

    # function to insert a the best an worst object list entry plot in the report
    def report_object_list(self, story, match_result, ecu_objs):
        if len(match_result) == 0:
            return
        dif_pos_x = []
        dif_pos_y = []
        dif_vel_x = []
        dif_vel_y = []
        for i in range(0, len(ecu_objs), 1):
            for j in range(0, len(ecu_objs[i][DIS_X]), 1):
                if ecu_objs[i][MATCH][j] >= 0:
                    tmp = ecu_objs[i][DIS_X][j] - ecu_objs[i][M_DIS_X][j]
                    dif_pos_x.append(tmp)
                    tmp = ecu_objs[i][DIS_Y][j] - ecu_objs[i][M_DIS_Y][j]
                    dif_pos_y.append(tmp)
                    tmp = ecu_objs[i][VEL_X][j] - ecu_objs[i][M_VEL_X][j]
                    dif_vel_x.append(tmp)
                    tmp = ecu_objs[i][VEL_Y][j] - ecu_objs[i][M_VEL_Y][j]
                    dif_vel_y.append(tmp)
        filename = self.plot_displacement(dif_pos_x, dif_pos_y, 'Displacement X', 'Displacement y')
        caption = "Distance displacemen of all objects"
        story.add_image(caption, os.path.join(self.out_directory, filename))

        filename = self.plot_displacement(dif_vel_x, dif_vel_y, 'Displacement X', 'Displacement y')
        caption = "Velocity displacemen of all objects"
        story.add_image(caption, os.path.join(self.out_directory, filename))

"""
CHANGE LOG:
-----------
"""
