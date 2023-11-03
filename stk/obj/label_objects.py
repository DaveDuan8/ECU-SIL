"""
stk/obj/label_objects.py
------------------------

Base implementations of the object filters

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.13 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/10/20 12:04:43CEST $
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from operator import itemgetter
# import math
from scipy import interpolate
from numpy import radians as npradians, fromiter as npfromiter, float as npfloat, where as npwhere
from sys import maxint

# - import STK modules -------------------------------------------------------------------------------------------------
from stk.obj.adas_objects import BaseAdasObject, BaseObjectList, OBJ_2_DB_NAME, DB_2_OBJ_NAME, OBJ_RECTOBJECT_ID, \
    OBJ_DISTX, OBJ_DISTY, OBJ_VELX, OBJ_ORIENT, OBJ_LENGTH, OBJ_WIDTH
from stk.val.result_types import Signal
from stk.obj.error import AdasObjectLoadError
from ..util.helper import deprecated
from stk.db.obj.objdata import ASSOCIATION_TYPE_TABLE_NAME_FEATURE

from stk.obj.adas_objects import OBJ_TIME_STAMPS, LABEL_OBJECT_SIGNAL_NAMES

import stk.obj.geo.utils as utils
from stk.util.logger import Logger

from stk.db.obj.objdata import COL_NAME_RECT_OBJ_MEASID, COL_NAME_ASSOC_TYPE_TABLE, \
    COL_NAME_RECT_OBJ_ASSOCTYPEID, COL_NAME_RECT_OBJ_RECTOBJ_IS_DELETED, COL_NAME_RECT_OBJ_OBJCLASSID, \
    COL_NAME_RECT_OBJ_CLSLBLSTATEID, COL_NAME_RECT_OBJ_CLSLBLTIME, COL_NAME_RECT_OBJ_CLSLBLBY, \
    COL_NAME_RECT_OBJ_OBJWIDTH, COL_NAME_RECT_OBJ_OBJLENGTH, COL_NAME_RECT_OBJ_OBJHEIGHT, \
    COL_NAME_RECT_OBJ_DIMLBLSTATEID, COL_NAME_RECT_OBJ_DIMLBLTIME, COL_NAME_RECT_OBJ_DIMLBLBY, \
    COL_NAME_RECT_OBJ_ZLAYER, COL_NAME_RECT_OBJ_ZOVERGROUND, COL_NAME_RECT_OBJ_ZOLBLSTATEID, \
    COL_NAME_RECT_OBJ_ZOLBLBY, COL_NAME_RECT_OBJ_ZOLBLTIME, COL_NAME_RECT_OBJ_KINLBLSTATEID, \
    COL_NAME_RECT_OBJ_KINLBLMODTIME, COL_NAME_RECT_OBJ_LBLBY, COL_NAME_KINEMATICS_KINABSTS, \
    COL_NAME_KINEMATICS_RECTOBJID, COL_NAME_KINEMATICS_RELDISTX, COL_NAME_KINEMATICS_RELDISTY, \
    COL_NAME_KINEMATICS_RELVELX, COL_NAME_KINEMATICS_HEADINGOVERGND, COL_NAME_ADMA_KINEMATICS_RECTOBJID, \
    COL_NAME_ADMA_KINEMATICS_KINABSTS, COL_NAME_ADMA_KINEMATICS_RELDISTX, COL_NAME_ADMA_KINEMATICS_RELDISTY, \
    COL_NAME_ADMA_KINEMATICS_RELVELX, COL_NAME_ADMA_KINEMATICS_RELVELY, COL_NAME_ADMA_KINEMATICS_ARELX, \
    COL_NAME_ADMA_KINEMATICS_ARELY, COL_NAME_ADMA_KINEMATICS_HEADINGOG, COL_NAME_ADMA_KINEMATICS_ADMAOK, \
    COL_NAME_TEST_CASES_BEGINABSTS, COL_NAME_TEST_CASES_ENDABSTS

# - defines ------------------------------------------------------------------------------------------------------------

DEFAULT_RECT_OBJ_RECORD_TEMPLATE = {COL_NAME_RECT_OBJ_MEASID: 0,
                                    COL_NAME_RECT_OBJ_ASSOCTYPEID: 2,
                                    COL_NAME_RECT_OBJ_RECTOBJ_IS_DELETED: 0,
                                    COL_NAME_RECT_OBJ_OBJCLASSID: 1,
                                    COL_NAME_RECT_OBJ_CLSLBLSTATEID: 1,
                                    COL_NAME_RECT_OBJ_CLSLBLTIME: 1,
                                    COL_NAME_RECT_OBJ_CLSLBLBY: 30,
                                    COL_NAME_RECT_OBJ_OBJWIDTH: 1,
                                    COL_NAME_RECT_OBJ_OBJLENGTH: 1,
                                    COL_NAME_RECT_OBJ_OBJHEIGHT: 1,
                                    COL_NAME_RECT_OBJ_DIMLBLSTATEID: 1,
                                    COL_NAME_RECT_OBJ_DIMLBLTIME: 1,
                                    COL_NAME_RECT_OBJ_DIMLBLBY: 30,
                                    COL_NAME_RECT_OBJ_ZLAYER: 5,
                                    COL_NAME_RECT_OBJ_ZOVERGROUND: 1,
                                    COL_NAME_RECT_OBJ_ZOLBLSTATEID: 1,
                                    COL_NAME_RECT_OBJ_ZOLBLBY: 30,
                                    COL_NAME_RECT_OBJ_ZOLBLTIME: 1,
                                    COL_NAME_RECT_OBJ_KINLBLSTATEID: 1,
                                    COL_NAME_RECT_OBJ_KINLBLMODTIME: 1,
                                    COL_NAME_RECT_OBJ_LBLBY: 30}

DEFAULT_OBJ_KINEMATICS_TEMPLATE = {COL_NAME_KINEMATICS_KINABSTS: 0,
                                   COL_NAME_KINEMATICS_RELDISTX: 0,
                                   COL_NAME_KINEMATICS_RELDISTY: 0,
                                   COL_NAME_KINEMATICS_RELVELX: 0,
                                   COL_NAME_KINEMATICS_HEADINGOVERGND: 0}

DEFAULT_OBJ_ADMA_KINEMATICS_TEMPLATE = {COL_NAME_ADMA_KINEMATICS_RECTOBJID: 0,
                                        COL_NAME_ADMA_KINEMATICS_KINABSTS: 0,
                                        COL_NAME_ADMA_KINEMATICS_RELDISTX: 0,
                                        COL_NAME_ADMA_KINEMATICS_RELDISTY: 0,
                                        COL_NAME_ADMA_KINEMATICS_RELVELX: 0,
                                        COL_NAME_ADMA_KINEMATICS_RELVELY: 0,
                                        COL_NAME_ADMA_KINEMATICS_ARELX: 0,
                                        COL_NAME_ADMA_KINEMATICS_ARELY: 0,
                                        COL_NAME_ADMA_KINEMATICS_HEADINGOG: 0,
                                        COL_NAME_ADMA_KINEMATICS_ADMAOK: 0}

DEFAULT_ASSOC_TYPE_ADMA = 2

LABELING_TYPE_RECT = 0  # autolabel (rectangle)
LABELING_TYPE_ROI = 1  # manual (roi)
LABELING_TYPE_ADMA = 2  # d-GPS reference system adma
LABELING_TYPE_RTRANGE = 3  # d-GPS reference system rt-range
DEFAULT_LABELING_TYPE = LABELING_TYPE_ROI

# defines for OBJ_ASSOCIATIONTYPE table to map to correct kinematics tables
# set table names to be backward compatible, 5 type entries for 2 tables in db during that time:
OLD_ASSOC_TABLE_NAMES = ["OBJ_KINEMATICS", "OBJ_KINEMATICS",
                         "OBJ_KINEMATICSADMA", "OBJ_KINEMATICSADMA", "OBJ_KINEMATICSADMA"]

def get_range(values):
    """
    return min/max range (maxint, inf) according the type of the value or value in the list

    with implementation of strict type checking for Signal types some usage of the Signal type in this module
    causes problems: the range was simply set to float(+-inf) which caused warnings if int values are stored,

    :param values: list of values or single value
    :return: min_range, max_range
    """
    valtype = type(values)
    if hasattr(values, '__iter__'):  # works with all iterable types like list, np array, ValueVector...
        valtype = type(values[0])

    if valtype == int:
        return -maxint - 1, maxint
    else:
        return float('-inf'), float('inf')


# - classes ------------------------------------------------------------------------------------------------------------
class DbObjectList(BaseObjectList):
    """
    DbObjectList
    """
    def __init__(self, data_source, meas_id, sensor, list_name, object_filter_if,
                 signal_names=None, generic_objects=None):
        """
        :param data_source: = (stk.db.connect.DBConnect()).Connect(stk.db.obj.objdata)
        :param meas_id: measurement identifier
        :type meas_id: integer
        :param sensor: name of the sensor
        :param list_name: name of the list
        :param object_filter_if: ObjectFilterIf, e.g. ObjectByGateFilter
        :param signal_names: list of names of signals to be loaded, default is LABEL_OBJECT_SIGNAL_NAMES
        :param generic_objects:
        """
        if signal_names is None:
            signal_names = LABEL_OBJECT_SIGNAL_NAMES
        BaseObjectList.__init__(self, data_source, sensor, list_name, object_filter_if, signal_names)

        self.__meas_id = meas_id
        if generic_objects is not None:
            self.__fill_objects_from_generic_object_list(data_source, generic_objects)
        self._log = Logger(self.__class__.__name__)

    def load_objects(self, startts=None, stopts=None, load_manual_labels_only=False, testcase_scenarios=None):
        """
        Load all tracked Objects in the given timespan for given measid

        :param startts: absolute start time stamp
        :type startts: long
        :param stopts: absolute stop time stamp
        :type stopts: long
        :param load_manual_labels_only: load only manually labeled or reviewed objects
        :param testcase_scenarios: list of test case scenarios e.g. ['following', 'oncoming']
        :return: True when the query has been successful, otherwise False
        """

        # clear objects:
        self._objects = []

        # get all manual labeled or reviewed rectangular objects for the given meas id
        if load_manual_labels_only:
            object_id_list = self._data_source.get_rect_object_ids(self.__meas_id, incl_deleted=False,
                                                                   cls_lblstateids=[2, 3])
        # get all existing rectangular objects for the given meas id
        else:
            object_id_list = self._data_source.get_rect_object_ids(self.__meas_id)

        # create LabelRectObject:
        for obj_id in object_id_list:
            oid = obj_id[OBJ_2_DB_NAME[OBJ_RECTOBJECT_ID]]
            if testcase_scenarios is None or not testcase_scenarios:
                self._objects.append(LabelRectObject(oid, startts, stopts, self._data_source, self._signal_names))
            else:
                for scenario in testcase_scenarios:
                    testcase_obj_sections = self._data_source.get_object_test_cases(oid, scenario)
                    for tc_sec in testcase_obj_sections:
                        startts = tc_sec[COL_NAME_TEST_CASES_BEGINABSTS]
                        stopts = tc_sec[COL_NAME_TEST_CASES_ENDABSTS]
                        # tc_type = tc_sec[COL_NAME_TEST_CASES_TYPEID]
                        self._objects.append(LabelRectObject(oid, startts, stopts, self._data_source,
                                                             self._signal_names, signals=None, labeling_type=None,
                                                             scenario=scenario))

    def filter_labels(self, fov_bin_func=None, obj_algo_gate=None, ego_speed_per_ts=None):
        """
        Filters the list of label objects so that only the field of view (fov) is considered

        If there are more than one sections in the label which are valid separated by invalid gaps,
        it splits the objects to objects sections accordingly, e.g.:

        label for obj#1, * means: out of fov::

          |****------**--------|

        after filtering:

        obj#1, section#1, obj#1, section#2::

              |------| |--------|

        If you get the objects from db object list with get_objects(), it will have 2 obj#1 in the list,
        and the list can be iterated trough as before, and both sections can be used e.g. for object matching.

        Usage example:

        .. python::

            ADMA_LATENCY = 120#ms
            ego_speed_per_ts = OrderedDict()
            timestamps = self._data_manager.GetDataPort(val_gd.TIMESTAMP_PORT_NAME, self._bus_name)
            vdy_data = self._data_manager.GetDataPort(val_gd.VDYDATA_PORT_NAME, self._bus_name)
            ego_speed = vdy_data[sd.PORT_VDY_VEHICLE_SPEED]
            for idx, ts in enumerate(timestamps):
                ego_speed_per_ts[ts] = ego_speed[idx]
            fov = FieldOfView(FieldOfView.PREMIUM_SENSOR)
            db_object_list.interpolate_to_time_system(timestamps, ADMA_LATENCY)
            db_obj_list.filter_labels(fov.is_point_in_fov, fov.is_object_detecteble, ego_speed_per_ts)

            or

            def is_obj_in(x, y):
                FOV_ANGLE = 60.0
                fova = math.radians(FOV_ANGLE)
                if x <= 0 or x > distance:
                    return False
                elif math.fabs(float(y) / float(x)) < math.tan(fova):
                    return True
                else:
                    return False
            db_obj_list.filter_labels(is_obj_in)

        :param fov_bin_func: binary function with distx, disty and a boolean return value
        :type fov_bin_func: function pointer (x,y), return True/False e.g. see below
        :param obj_algo_gate: binary function with ego speed, distx and a boolean return value
        :type fov_bin_func: function pointer (x,y), return True/False e.g. see below
        :param ego_speed_per_ts: ego_speed
        :type ego_speed_per_ts: OrderedDict()


        """

        if fov_bin_func is None and obj_algo_gate is None:
            return

        def default_fov_bin_func(dummy_distx, dummy_disty):
            """default function if no fov_bin_func is passed"""
            return True

        def default_obj_algo_gate(dummy_ego_speed, dummy_distx):
            """default function if no obj_algo_gate is passed"""
            return True

        if fov_bin_func is None:
            fov_bin_func = default_fov_bin_func
        if obj_algo_gate is None or ego_speed_per_ts is None or len(ego_speed_per_ts) == 0:
            obj_algo_gate = default_obj_algo_gate

        new_objects = []
        for lab_obj in self._objects:
            sections = []
            section_open_ts = None
            section_close_ts = None
            distxl = lab_obj.get_signal(OBJ_DISTX).GetValue()
            distyl = lab_obj.get_signal(OBJ_DISTY).GetValue()
            timestampl = lab_obj.get_signal(OBJ_DISTX).GetTimestamps()
            max_idx = len(timestampl) - 1
            for idx, timestamp in enumerate(timestampl):
                distx = distxl[idx]
                disty = distyl[idx]
                ego_speed = None
                if ego_speed_per_ts is not None:
                    ego_speed = ego_speed_per_ts.get(timestamp)
                    if ego_speed is None:
                        self._log.error("time stamp not found, ts of label differs from ts of bsig. "
                                        "please use interpolate_to_time_system before filter_labels")
                if fov_bin_func(distx, disty) and obj_algo_gate(ego_speed, distx):
                    if section_open_ts is None:
                        # open section
                        section_open_ts = timestamp
                    else:
                        # do nothing
                        pass
                    # extend section
                    section_close_ts = timestamp
                else:
                    if section_open_ts is None:
                        # do nothing
                        pass
                    else:
                        # close section
                        sections.append((section_open_ts, section_close_ts))
                        section_open_ts = None
                        section_close_ts = None
                if idx == max_idx and section_open_ts is not None:
                    # close section
                    sections.append((section_open_ts, section_close_ts))
                    section_open_ts = None
                    section_close_ts = None

            # create new sections
            for section in sections:
                new_objects.append(lab_obj.get_subset(startts=section[0], stopts=section[1]))

        # replace objects with the new object section list
        del self._objects
        self._objects = new_objects

    def adjust_label_distance(self, correction_func=utils.adjust_distance_adma):
        """
        the reflection point needs to determined for e.g. ADMA objects
        and the distance x and y is updated to that reflection point (instead of location of GPS device)


        :param correction_func: corr_distx, corr_disty = correction_func(distx, disty, length, width, orient)
        """
        for lab_obj in self._objects:
            lab_obj.adjust_label_distance(correction_func)

    def interpolate_to_time_system(self, new_timestamps, latency=0.0):
        """
        the timestamps need to interpolated to the measurement for e.g. ADMA objects
        all signals incl values and timestamps are updated accordingly

        :param new_timestamps: new_timestamps from the measurement
        :param latency: time in milliseconds, it will be substracted from reference object time
        :type latency: float
        """
        for lab_obj in self._objects:
            lab_obj.interpolate_to_time_system(new_timestamps, latency)

    def get_adma_objects(self):
        """
        returns only the adma objects
        """

        all_obj = self.get_objects()
        adma = []
        for obj in all_obj:
            if obj.get_labeling_type() == self._data_source.get_adma_associated_type_id():
                adma.append(obj)
        return adma

    def write_objects_into_db(self, assoc_type=DEFAULT_ASSOC_TYPE_ADMA,
                              rect_obj_record_template=None,
                              obj_kinematics_template=None):
        """
        Writes the objects into the DB / data source

        :param assoc_type: association type from DB ASSOCTYPEID, default is DEFAULT_ASSOC_TYPE_ADMA
        :param rect_obj_record_template: rect_obj_record_template from DB, default is DEFAULT_RECT_OBJ_RECORD_TEMPLATE
        :param obj_kinematics_template: obj_kinematics_template from DB, default is DEFAULT_OBJ_KINEMATICS_TEMPLATE
        """
        if rect_obj_record_template is None:
            rect_obj_record_template = DEFAULT_RECT_OBJ_RECORD_TEMPLATE
        if obj_kinematics_template is None:
            obj_kinematics_template = DEFAULT_OBJ_KINEMATICS_TEMPLATE
        for obj in self._objects:
            obj.write_object_into_db(self.__meas_id, assoc_type, rect_obj_record_template, obj_kinematics_template)

    def __fill_objects_from_generic_object_list(self, data_source, generic_object_list):
        """
        Load Objects from GenericObjectList

        :param data_source:
        :param generic_object_list: GenericObjectList
        """
        # clear objects:
        self._objects = []
        for gen_obj in generic_object_list:
            self._objects.append(LabelRectObject(gen_obj.get_id(), None, None, data_source, self._signal_names,
                                                 gen_obj.get_signals(), DEFAULT_LABELING_TYPE))

    @deprecated('write_objects_into_db')
    def WriteObjectsIntoDB(self, assoc_type=DEFAULT_ASSOC_TYPE_ADMA,  # pylint: disable=C0103
                           rect_obj_record_template=None,
                           obj_kinematics_template=None):
        """
        :deprecated: use `write_objects_into_db` instead
        """
        if rect_obj_record_template is None:
            rect_obj_record_template = DEFAULT_RECT_OBJ_RECORD_TEMPLATE
        if obj_kinematics_template is None:
            obj_kinematics_template = DEFAULT_OBJ_KINEMATICS_TEMPLATE
        return self.write_objects_into_db(assoc_type,
                                          rect_obj_record_template,
                                          obj_kinematics_template)


class LabelRectObject(BaseAdasObject):
    """
    Object in the label database
    """
    def __init__(self, obj_id, startts, stopts, data_source, signal_names=None, signals=None,
                 labeling_type=None, scenario=None):
        """
        Constructor creating a rectangular object either from data_source or from signals if specified

        :param obj_id: object id
        :param startts: absolute start time stamp
        :type startts: long
        :param stopts: absolute stop time stamp
        :type stopts: long
        :param data_source: data source, e.g. DB
        :param signal_names: list of names of signals, default is LABEL_OBJECT_SIGNAL_NAMES
        :param signals: if this is specified, signals are directly filled with it; data source is not used for filling
        :param labeling_type: labeling type as in DB table OBJ_ASSOCIATED_TYPES
        :param scenario: following, oncoming, etc. from OBJ_TESTCASETYPE
        """
        if signal_names is None:
            signal_names = LABEL_OBJECT_SIGNAL_NAMES
        BaseAdasObject.__init__(self, obj_id, data_source, signal_names)
        self.__labeling_type = labeling_type
        self.__scenario = scenario
        if signals is not None:
            self._signals = signals
        elif data_source is not None:
            self.__fill_object_data(obj_id, startts, stopts)
        else:
            raise AdasObjectLoadError("LabelRectObject initialization error: neither data_source nor signals are\
                                       specified")

    def get_scenario(self):
        """
        return internal scenario: following, oncoming, etc. from OBJ_TESTCASETYPE

        :return: scenario
        :rtype:  string
        """
        return self.__scenario

    @deprecated('get_subset')
    def GetSubset(self, startts=None, stopts=None):  # pylint: disable=C0103
        """
        :deprecated: use `get_subset` instead
        """
        return self.get_subset(startts, stopts)

    def get_subset(self, startts=None, stopts=None):
        """
        Makes a subset of the signals within the time interval

        :param startts: start time slot
        :param stopts: stop time slot
        """
        return LabelRectObject(self.get_id(), startts, stopts, self._data_source, self._signal_names,
                               self._get_subset_of_signals(startts, stopts), self.get_labeling_type(), self.__scenario)

    def get_labeling_type(self):
        """
        Returns the labeling type as in DB table OBJ_ASSOCIATED_TYPES.

        0: auto-labeling: rectobject: reference point is on the middle of objects side towards personal view
        1: manual labeling: roi: reference point is in the middle of the rectangular box
        """
        return self.__labeling_type

    def adjust_label_distance(self, correction_func=utils.adjust_distance_adma):
        """
        the reflection point needs to determined for e.g. ADMA objects
        and the distance x and y is updated to that reflection point (instead of location of GPS device)

        :param correction_func: corr_distx, corr_disty = correction_func(distx, disty, length, width, orient)
        """
        if self.__labeling_type == self._data_source.get_adma_associated_type_id():
            # corrected_distx = []
            distxl = self._signals[OBJ_DISTX].GetValue()
            timestamps = self._signals[OBJ_DISTX].GetTimestamps()
            distyl = self._signals[OBJ_DISTY].GetValue()
            orientl = self._signals[OBJ_ORIENT].GetValue()
            width = self._signals[OBJ_WIDTH].GetValue()[0]
            length = self._signals[OBJ_LENGTH].GetValue()[0]
            for idx, _ in enumerate(timestamps):
                distx = distxl[idx]
                disty = distyl[idx]
                orient = npradians(orientl[idx])
                corr_distx, corr_disty = correction_func(distx, disty, length, width, orient)
                self._signals[OBJ_DISTX].SetValue(idx, corr_distx)
                self._signals[OBJ_DISTY].SetValue(idx, corr_disty)

    def interpolate_to_time_system(self, new_timestamps, adma_latency=0.0):
        """
        timestamps and all signals need to be interpolated to the measurement's time system

        :param new_timestamps: timestamps
        :type new_timestamps: list of float
        :param adma_latency: time in milliseconds, it will be added to reference object time, only for adma objects
        :type adma_latency: float
        """
        def get_start_stop_interval_idxs(timestamps_, new_timestamps_):
            """
            returns the new_timestamps start and stop indexes inside the timestamps interval
            """
            nts = npfromiter(new_timestamps_, npfloat)
            nts = npwhere((nts >= timestamps_[0]) & (nts <= timestamps_[-1]))[0]
            if nts.size != 0:
                return nts[0], nts[-1]
            else:
                return None, None

        if self.__labeling_type == self._data_source.get_adma_associated_type_id():
            latency = adma_latency * 1000.0
        else:
            latency = 0.0

        for signal_name in self._signals.keys():
            signal_values = self._signals[signal_name].GetValue()
            timestamps_orig = self._signals[signal_name].GetTimestamps()
            timestamps = [ts + latency for ts in timestamps_orig]
            # print "signal name: " + signal_name
            # print "timestamps before: " + str(timestamps)
            # print "signal_values before: " + str(signal_values)
            start_idx_new, stop_idx_new = get_start_stop_interval_idxs(timestamps, new_timestamps)
            if len(timestamps) > 1 and start_idx_new is not None and stop_idx_new is not None:
                new_time_interval = new_timestamps[start_idx_new:stop_idx_new + 1]
                func_time = interpolate.interp1d(timestamps, timestamps)
                func_signal = interpolate.interp1d(timestamps, signal_values)
                new_time = func_time(new_time_interval).tolist()
                new_signal_values = func_signal(new_time_interval).tolist()
                # print "timestamps after: " + str(new_time)
                # print "signal_values after: " + str(new_signal_values)
                range_min, range_max = get_range(new_signal_values)
                self._signals[signal_name] = None
                self._signals[signal_name] = Signal(signal_name, None, new_signal_values, new_time,
                                                    range_min, range_max)  # float('-inf'), float('inf'))

    def __fill_object_data(self, obj_id, startts, stopts):
        """
        Fills in signals from DB within the time interval

        :param obj_id: object id
        :param startts: start time slot
        :param stopts: stop time slot
        """
        # get all kinematics records belonging to the rectangular object id
        # obj_rec = self._data_source.GetRectObjectById(obj_id)
        obj_rec = self._data_source.get_rect_object_by_rect_obj_id(obj_id)

        kin_records = self._data_source.get_rect_object_kinematics(obj_id)
        # exception handling
        if (len(obj_rec) == 0) or (len(obj_rec) > 1) or (not kin_records):
            raise AdasObjectLoadError("Database query returned not a single entry: {}".format(len(obj_rec)))
        else:
            obj_rec = obj_rec[0]

        # set the labeling type for object matching
        self.__labeling_type = obj_rec[COL_NAME_RECT_OBJ_ASSOCTYPEID]

        # filter out kinetic records according to startts and stopts if specified
        filtered_kin_records = [rec for rec in kin_records if not
                                (((startts is not None) and (rec[OBJ_2_DB_NAME[OBJ_TIME_STAMPS]] < startts)) or
                                 ((stopts is not None) and (rec[OBJ_2_DB_NAME[OBJ_TIME_STAMPS]] > stopts)))]

        # sort kinetic records according to time
        filtered_kin_records_by_time = sorted(filtered_kin_records, key=itemgetter(OBJ_2_DB_NAME[OBJ_TIME_STAMPS]))

        # ordered list of all time slots occurring in the kinetics table
        time_slot_seq = [d[OBJ_2_DB_NAME[OBJ_TIME_STAMPS]] for d in filtered_kin_records_by_time]

        # convert static parameters of rectangular object into Signals
        # value is the same for all time slots
        rect_obj_stat_signals = {}
        for name, val in obj_rec.iteritems():
            # RECTOBJID is not to be converted to a new signal
            if name in self._signal_names:
                rect_obj_stat_signals[DB_2_OBJ_NAME[name]] = Signal(DB_2_OBJ_NAME[name], None,
                                                                    [val] * len(time_slot_seq),
                                                                    time_slot_seq,
                                                                    min(val) if hasattr(val, '__iter__') else val,
                                                                    max(val) if hasattr(val, '__iter__') else val)

        # convert kinetic parameters belonging to a rectangular object into Signals
        # value can vary depending on the time slot
        rect_obj_kin_signals = {}
        tmp_value_dict_list = {}
        for kin_rec in filtered_kin_records_by_time:
            for field_name, value in kin_rec.iteritems():
                if field_name in tmp_value_dict_list:
                    tmp_value_dict_list[field_name].append(value)
                else:
                    # KINABSTS is not to be converted to a new signal, it is represented as time_slot_seq above
                    if field_name != OBJ_2_DB_NAME[OBJ_TIME_STAMPS]:
                        tmp_value_dict_list[field_name] = [value]
        for name, val in tmp_value_dict_list.iteritems():
            if name in self._signal_names:
                range_min, range_max = get_range(val)
                rect_obj_kin_signals[DB_2_OBJ_NAME[name]] = Signal(DB_2_OBJ_NAME[name], None, val,
                                                                   time_slot_seq, range_min, range_max)

        # join static and kinetic signals
        rect_object_complete_signals = rect_obj_stat_signals
        rect_object_complete_signals.update(rect_obj_kin_signals)
        self._signals = rect_object_complete_signals

        return True

    def write_object_into_db(self, meas_id, assoc_type=DEFAULT_ASSOC_TYPE_ADMA,
                             rect_obj_record_template=None,
                             obj_kinematics_template=None, db_source=None):
        """
        Fills in signals from DB within the time interval

        Do not use of Oracle DB. Default to be changed

        :param meas_id: measurement id
        :param assoc_type: association type from DB ASSOCTYPEID, default is DEFAULT_ASSOC_TYPE_ADMA
        :param rect_obj_record_template: rect_obj_record_template from DB, default is DEFAULT_RECT_OBJ_RECORD_TEMPLATE
        :param obj_kinematics_template: obj_kinematics_template from DB, default is DEFAULT_OBJ_KINEMATICS_TEMPLATE
        :param db_source: DbConnection to allow ad hoc usage of different db, default: data_source as initiated
        :return rectobj_id: the id of the object assigned during the DB insertion
        """
        if obj_kinematics_template is None:
            obj_kinematics_template = DEFAULT_OBJ_KINEMATICS_TEMPLATE

        if rect_obj_record_template is None:
            rect_obj_record_template = DEFAULT_RECT_OBJ_RECORD_TEMPLATE
        rect_obj_record_template[COL_NAME_RECT_OBJ_MEASID] = meas_id
        rect_obj_record_template[COL_NAME_RECT_OBJ_ASSOCTYPEID] = assoc_type

        if db_source is None:
            source = self._data_source
        else:
            source = db_source
        ass_obj = source.get_object_association(typeid=assoc_type)
        if len(ass_obj)<>1:
            raise(AdasObjectLoadError, "no (unique) object association for type {}".format(assoc_type))
        if source.sub_scheme_version >= ASSOCIATION_TYPE_TABLE_NAME_FEATURE:
            table_name = ass_obj[0][COL_NAME_ASSOC_TYPE_TABLE]
        else:
            table_name = OLD_ASSOC_TABLE_NAMES[assoc_type]
        length_vector = self._signals[OBJ_LENGTH].GetValue()
        width_vector = self._signals[OBJ_WIDTH].GetValue()
        rect_obj_record_template[COL_NAME_RECT_OBJ_OBJLENGTH] = sum(length_vector) / len(length_vector)
        rect_obj_record_template[COL_NAME_RECT_OBJ_OBJWIDTH] = sum(width_vector) / len(width_vector)
        rectobj_id = source.add_rectangular_object(rect_obj_record_template)
        obj_kinematics_template[COL_NAME_KINEMATICS_RECTOBJID] = rectobj_id
        self._id = rectobj_id

        timestamps = self._signals[OBJ_DISTX].GetTimestamps()
        for tstamp in timestamps:
            obj_kinematics_template[COL_NAME_KINEMATICS_KINABSTS] = tstamp
            obj_kinematics_template[OBJ_2_DB_NAME[OBJ_DISTX]] = self._signals[OBJ_DISTX].GetValueAtTimestamp(tstamp)
            obj_kinematics_template[OBJ_2_DB_NAME[OBJ_DISTY]] = self._signals[OBJ_DISTY].GetValueAtTimestamp(tstamp)
            obj_kinematics_template[OBJ_2_DB_NAME[OBJ_VELX]] = self._signals[OBJ_VELX].GetValueAtTimestamp(tstamp)
            obj_kinematics_template[OBJ_2_DB_NAME[OBJ_ORIENT]] = self._signals[OBJ_ORIENT].GetValueAtTimestamp(tstamp)
            source.add_kinematics(obj_kinematics_template, table_name)

        return rectobj_id

    @deprecated('get_labeling_type')
    def GetLabelingType(self):  # pylint: disable=C0103
        """
        :deprecated: use `get_labeling_type` instead
        """
        return self.get_labeling_type()

    @deprecated('write_object_into_db')
    def WriteObjectIntoDB(self, meas_id, assoc_type=DEFAULT_ASSOC_TYPE_ADMA,  # pylint: disable=C0103
                          rect_obj_record_template=None,
                          obj_kinematics_template=None, db_source=None):
        """
        :deprecated: use `write_object_into_db` instead
        """
        if obj_kinematics_template is None:
            obj_kinematics_template = DEFAULT_OBJ_KINEMATICS_TEMPLATE
        if rect_obj_record_template is None:
            rect_obj_record_template = DEFAULT_RECT_OBJ_RECORD_TEMPLATE

        return self.write_object_into_db(meas_id, assoc_type,
                                         rect_obj_record_template,
                                         obj_kinematics_template, db_source)


"""
$Log: label_objects.py  $
Revision 1.13 2017/10/20 12:04:43CEST Hospes, Gerd-Joachim (uidv8815) 
add usage of new table column obj_table_name
Revision 1.12 2015/12/14 14:39:22CET Hospes, Gerd-Joachim (uidv8815)
pylint fixes
Revision 1.11 2015/12/14 09:51:24CET Hospes, Gerd-Joachim (uidv8815)
M.Sandor: STK OBJ DB labels are adjusted so that intervals are cut out,
where distx>100m and Vego<65kmh, similarily to the field of view implementation,
where intervals are cut out from labels, where the target car is out of the field of view.
Revision 1.10 2015/12/07 11:17:13CET Mertens, Sven (uidv7805)
fixing an pep8
Revision 1.9 2015/09/24 15:31:39CEST Hospes, Gerd-Joachim (uidv8815)
put back doc lines
- Added comments -  uidv8815 [Sep 24, 2015 3:31:39 PM CEST]
Change Package : 380001:1 http://mks-psad:7002/im/viewissue?selection=380001
Revision 1.8 2015/09/24 15:25:25CEST Hospes, Gerd-Joachim (uidv8815)
fix paste error during checkin
Revision 1.7 2015/09/24 14:37:06CEST Hospes, Gerd-Joachim (uidv8815)
new method get_range to return correct type for range
Revision 1.6 2015/09/14 17:14:42CEST Hospes, Gerd-Joachim (uidv8815)
fix pep8 warnings, rem wrong comment
--- Added comments ---  uidv8815 [Sep 14, 2015 5:14:43 PM CEST]
Change Package : 376619:1 http://mks-psad:7002/im/viewissue?selection=376619
Revision 1.5 2015/09/14 10:52:33CEST Hospes, Gerd-Joachim (uidv8815)
range of rect_obj_stat_signals in __fill_object_data() changed from inf to min/max
--- Added comments ---  uidv8815 [Sep 14, 2015 10:52:33 AM CEST]
Change Package : 376619:1 http://mks-psad:7002/im/viewissue?selection=376619
Revision 1.4 2015/09/11 13:35:32CEST Hospes, Gerd-Joachim (uidv8815)
set min/max range to current min/max when filling the LabelRectObject
--- Added comments ---  uidv8815 [Sep 11, 2015 1:35:33 PM CEST]
Change Package : 373636:2 http://mks-psad:7002/im/viewissue?selection=373636
Revision 1.3 2015/09/08 16:42:45CEST Mertens, Sven (uidv7805)
define extention
--- Added comments ---  uidv7805 [Sep 8, 2015 4:42:45 PM CEST]
Change Package : 369827:1 http://mks-psad:7002/im/viewissue?selection=369827
Revision 1.2 2015/06/18 13:19:01CEST Ahmed, Zaheer (uidu7634)
needed to raise AdasObjectLoadError on calling load_objects() if not rectobject found
--- Added comments ---  uidu7634 [Jun 18, 2015 1:19:01 PM CEST]
Change Package : 348861:1 http://mks-psad:7002/im/viewissue?selection=348861
Revision 1.1 2015/04/23 19:04:49CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/obj/project.pj
Revision 1.28 2015/02/06 16:45:34CET Ellero, Stefano (uidw8660)
No deprecated functions/methods of package obj must be used inside all STK and its module tests.
--- Added comments ---  uidw8660 [Feb 6, 2015 4:45:35 PM CET]
Change Package : 301801:1 http://mks-psad:7002/im/viewissue?selection=301801
Revision 1.27 2015/02/03 18:55:40CET Ellero, Stefano (uidw8660)
No deprecated functions/methods of package obj must be used inside all STK and its module tests.
--- Added comments ---  uidw8660 [Feb 3, 2015 6:55:41 PM CET]
Change Package : 301801:1 http://mks-psad:7002/im/viewissue?selection=301801
Revision 1.26 2015/01/23 14:18:03CET Mertens, Sven (uidv7805)
deprecating 2 methods
--- Added comments ---  uidv7805 [Jan 23, 2015 2:18:04 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.25 2014/12/16 19:22:58CET Ellero, Stefano (uidw8660)
Remove all db.obj based deprecated function usage inside STK and module tests.
--- Added comments ---  uidw8660 [Dec 16, 2014 7:22:58 PM CET]
Change Package : 281278:1 http://mks-psad:7002/im/viewissue?selection=281278
Revision 1.24 2014/12/04 14:34:47CET Hospes, Gerd-Joachim (uidv8815)
latency added to interpolation, tests missing
--- Added comments ---  uidv8815 [Dec 4, 2014 2:34:48 PM CET]
Change Package : 288130:1 http://mks-psad:7002/im/viewissue?selection=288130
Revision 1.23 2014/11/21 13:49:02CET Hospes, Gerd-Joachim (uidv8815)
timestamp interpolation used for all objects (not only ADMA),
new signal definition
--- Added comments ---  uidv8815 [Nov 21, 2014 1:49:03 PM CET]
Change Package : 283590:1 http://mks-psad:7002/im/viewissue?selection=283590
Revision 1.22 2014/10/31 10:08:58CET Hospes, Gerd-Joachim (uidv8815)
fix pep8, pylints
--- Added comments ---  uidv8815 [Oct 31, 2014 10:08:59 AM CET]
Change Package : 276932:1 http://mks-psad:7002/im/viewissue?selection=276932
Revision 1.21 2014/10/30 16:29:37CET Hospes, Gerd-Joachim (uidv8815)
add time interpolation to ADMA, rename deprecated functions, adjust doc
--- Added comments ---  uidv8815 [Oct 30, 2014 4:29:38 PM CET]
Change Package : 276932:1 http://mks-psad:7002/im/viewissue?selection=276932
Revision 1.20 2014/09/26 12:59:31CEST Hecker, Robert (heckerr)
.
--- Added comments ---  heckerr [Sep 26, 2014 12:59:31 PM CEST]
Change Package : 267232:1 http://mks-psad:7002/im/viewissue?selection=267232
Revision 1.19 2014/09/09 16:07:36CEST Hecker, Robert (heckerr)
Updates from Miklos.
Revision 1.18 2014/08/05 13:14:37CEST Hecker, Robert (heckerr)
Added Feature from miklos.
--- Added comments ---  heckerr [Aug 5, 2014 1:14:37 PM CEST]
Change Package : 254242:1 http://mks-psad:7002/im/viewissue?selection=254242
Revision 1.17 2014/08/04 10:57:27CEST Hecker, Robert (heckerr)
Added necessary updates from Miklos.
--- Added comments ---  heckerr [Aug 4, 2014 10:57:27 AM CEST]
Change Package : 253139:1 http://mks-psad:7002/im/viewissue?selection=253139
Revision 1.16 2014/07/29 18:25:34CEST Hospes, Gerd-Joachim (uidv8815)
fix pylint error W0102 and some others
--- Added comments ---  uidv8815 [Jul 29, 2014 6:25:34 PM CEST]
Change Package : 250927:1 http://mks-psad:7002/im/viewissue?selection=250927
Revision 1.15 2014/07/25 13:23:23CEST Hecker, Robert (heckerr)
Added the needed modifications form Miklos.
--- Added comments ---  heckerr [Jul 25, 2014 1:23:23 PM CEST]
Change Package : 251715:1 http://mks-psad:7002/im/viewissue?selection=251715
Revision 1.14 2014/07/10 13:58:57CEST Hecker, Robert (heckerr)
Check in needed updates for Sohaib.
--- Added comments ---  heckerr [Jul 10, 2014 1:58:58 PM CEST]
Change Package : 247710:1 http://mks-psad:7002/im/viewissue?selection=247710
Revision 1.13 2014/06/26 14:25:06CEST Hecker, Robert (heckerr)
New Version from Miklos.
--- Added comments ---  heckerr [Jun 26, 2014 2:25:06 PM CEST]
Change Package : 244732:1 http://mks-psad:7002/im/viewissue?selection=244732
Revision 1.12 2014/05/08 14:21:21CEST Hecker, Robert (heckerr)
Increased TestCoverage.
--- Added comments ---  heckerr [May 8, 2014 2:21:22 PM CEST]
Change Package : 234909:1 http://mks-psad:7002/im/viewissue?selection=234909
Revision 1.11 2014/04/30 16:58:07CEST Hecker, Robert (heckerr)
reduced pep8.
--- Added comments ---  heckerr [Apr 30, 2014 4:58:08 PM CEST]
Change Package : 233703:1 http://mks-psad:7002/im/viewissue?selection=233703
Revision 1.10 2014/04/29 10:26:28CEST Hecker, Robert (heckerr)
updated to new guidelines.
--- Added comments ---  heckerr [Apr 29, 2014 10:26:28 AM CEST]
Change Package : 233703:1 http://mks-psad:7002/im/viewissue?selection=233703
Revision 1.9 2014/04/25 09:26:31CEST Hecker, Robert (heckerr)
updated needed files for Miklos.
--- Added comments ---  heckerr [Apr 25, 2014 9:26:32 AM CEST]
Change Package : 233045:1 http://mks-psad:7002/im/viewissue?selection=233045
Revision 1.8 2014/02/24 14:50:22CET Sandor-EXT, Miklos (uidg3354)
return rectobj_id in WriteObjectIntoDB()
--- Added comments ---  uidg3354 [Feb 24, 2014 2:50:22 PM CET]
Change Package : 208827:2 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.7 2014/02/21 17:17:26CET Sandor-EXT, Miklos (uidg3354)
write to DB updates
Revision 1.6 2014/01/29 16:09:43CET Sandor-EXT, Miklos (uidg3354)
signal_names to be extracted added
--- Added comments ---  uidg3354 [Jan 29, 2014 4:09:43 PM CET]
Change Package : 208827:2 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.5 2013/12/16 15:47:25CET Sandor-EXT, Miklos (uidg3354)
width, length added
Revision 1.4 2013/12/16 14:06:42CET Sandor-EXT, Miklos (uidg3354)
write objs in DB
--- Added comments ---  uidg3354 [Dec 16, 2013 2:06:42 PM CET]
Change Package : 208827:2 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.3 2013/12/03 13:47:38CET Sandor-EXT, Miklos (uidg3354)
object matching
--- Added comments ---  uidg3354 [Dec 3, 2013 1:47:39 PM CET]
Change Package : 208827:1 http://mks-psad:7002/im/viewissue?selection=208827
"""
