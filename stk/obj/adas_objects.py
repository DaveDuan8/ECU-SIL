"""
stk/obj/adas_objects.py
-----------------------

 Classes for ADAS Object handling

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.4 $
:contact:       $Author: Hecker, Robert (heckerr) $ (last change)
:date:          $Date: 2017/05/05 09:58:09CEST $
"""

# Import Python Modules ---------------------
from os import path
from sys import path as sp
import math
import numpy.core as npc
from scipy import interpolate, unwrap
from random import shuffle
from abc import ABCMeta, abstractmethod
from collections import OrderedDict
from operator import itemgetter

# Import STK Modules -------------------------
DB_FOLDER = path.abspath(path.join(path.split(__file__)[0], '..'))
if DB_FOLDER not in sp:
    sp.append(DB_FOLDER)

from stk.db.obj.objdata import \
    COL_NAME_KINEMATICS_KINABSTS, COL_NAME_KINEMATICS_RELDISTX, \
    COL_NAME_KINEMATICS_RELDISTY, COL_NAME_KINEMATICS_RELVELX, \
    COL_NAME_KINEMATICS_RECTOBJID, COL_NAME_KINEMATICS_HEADINGOVERGND, \
    COL_NAME_ADMA_KINEMATICS_RELDISTX, COL_NAME_ADMA_KINEMATICS_RELDISTY, \
    COL_NAME_ADMA_KINEMATICS_RELVELX, COL_NAME_ADMA_KINEMATICS_RELVELY, \
    COL_NAME_ADMA_KINEMATICS_ARELX, COL_NAME_ADMA_KINEMATICS_ARELY, \
    COL_NAME_ADMA_KINEMATICS_HEADINGOG, \
    COL_NAME_ADMA_KINEMATICS_ADMAOK

from stk.db.db_sql import SQLBinaryExpr, OP_AS
from stk.obj.geo.rect import Rectangle
from stk.db.obj.objdata import COL_NAME_RECT_OBJ_RECTOBJID, \
    COL_NAME_RECT_OBJ_OBJLENGTH, \
    COL_NAME_RECT_OBJ_OBJWIDTH, \
    COL_NAME_RECT_OBJ_OBJCLASSID

from stk.util.logger import Logger
from stk.util.helper import deprecated

# Defines ------------------------------------
# OBJECT Definitions - Metadata
OBJ_OBJECT_INDEX = "Index"
OBJECT_PORT_NAME = "Objects"
OBJ_GLOBAL_ID = "GlobalObjectId"
OBJ_OBJECT_ID = "ObjectId"
OBJ_DYNAMIC_PROPERTY = "ucDynamicProperty"
OBJ_START_TIME = "StartTime"
OBJ_START_INDEX = "Index"
OBJ_TIME_STAMPS = "Timestamp"
OBJ_RECTOBJECT_ID = "RectObjId"
OBJ_CLASS = "Classification"

# OBJECT Definitions - Signal values
OBJ_DISTX = 'DistX'
OBJ_DISTX_STD = 'DistX_Std'
OBJ_DISTY = 'DistY'
OBJ_DISTY_STD = 'DistY_Std'
OBJ_VELX = 'VrelX'
OBJ_VELX_STD = 'VrelX_Std'
OBJ_VELY = 'VrelY'
OBJ_VELY_STD = 'VrelY_Std'
OBJ_ACCELX = 'AccelX'
OBJ_ACCELX_STD = 'AccelX_Std'
OBJ_ACCELY = 'AccelY'
OBJ_ACCELY_STD = 'AccelY_Std'
OBJ_ORIENT = 'Orient'
OBJ_ORIENT_STD = 'Orient_Std'
OBJ_FLAG = 'Flags'
OBJ_OBJECT_ID = 'ObjectId'
OBJ_LENGTH = 'Object_Length'
OBJ_WIDTH = 'Object_Width'
OBJ_CLASS = 'Object_Class'

GENERIC_OBJECT_SIGNAL_NAMES = [OBJ_DISTX, OBJ_DISTX_STD, OBJ_DISTY, OBJ_DISTY_STD, OBJ_VELX, OBJ_VELX_STD,
                               OBJ_VELY, OBJ_VELY_STD, OBJ_ACCELX, OBJ_ACCELX_STD, OBJ_ORIENT, OBJ_ORIENT_STD,
                               OBJ_LENGTH, OBJ_WIDTH]

LABEL_OBJECT_SIGNAL_NAMES_BASE = [COL_NAME_RECT_OBJ_OBJLENGTH, COL_NAME_RECT_OBJ_OBJWIDTH, COL_NAME_KINEMATICS_RELDISTX,
                                  COL_NAME_KINEMATICS_RELDISTY, COL_NAME_KINEMATICS_RELVELX,
                                  COL_NAME_KINEMATICS_HEADINGOVERGND, COL_NAME_KINEMATICS_RECTOBJID]

LABEL_OBJECT_SIGNAL_NAMES = [COL_NAME_RECT_OBJ_OBJLENGTH, COL_NAME_RECT_OBJ_OBJWIDTH, COL_NAME_KINEMATICS_RELDISTX,
                             COL_NAME_KINEMATICS_RELDISTY, COL_NAME_KINEMATICS_RELVELX,
                             COL_NAME_ADMA_KINEMATICS_RELVELY, COL_NAME_ADMA_KINEMATICS_ARELX,
                             COL_NAME_ADMA_KINEMATICS_ARELY,
                             COL_NAME_KINEMATICS_HEADINGOVERGND, COL_NAME_KINEMATICS_RECTOBJID]

DB_2_OBJ_NAME = {COL_NAME_RECT_OBJ_RECTOBJID: OBJ_RECTOBJECT_ID,
                 COL_NAME_RECT_OBJ_OBJLENGTH: OBJ_LENGTH,
                 COL_NAME_RECT_OBJ_OBJWIDTH: OBJ_WIDTH,
                 COL_NAME_RECT_OBJ_OBJCLASSID: OBJ_CLASS,
                 COL_NAME_KINEMATICS_RELDISTX: OBJ_DISTX,
                 COL_NAME_KINEMATICS_RELDISTY: OBJ_DISTY,
                 COL_NAME_KINEMATICS_RELVELX: OBJ_VELX,
                 COL_NAME_ADMA_KINEMATICS_RELVELY: OBJ_VELY,
                 COL_NAME_ADMA_KINEMATICS_ARELX: OBJ_ACCELX,
                 COL_NAME_ADMA_KINEMATICS_ARELY: OBJ_ACCELY,
                 COL_NAME_KINEMATICS_HEADINGOVERGND: OBJ_ORIENT,
                 COL_NAME_KINEMATICS_KINABSTS: OBJ_TIME_STAMPS}

OBJ_2_DB_NAME = {v: k for k, v in DB_2_OBJ_NAME.items()}

# Functions ---------------------------------

# Classes -----------------------------------


class ObjectProperty(dict):
    """
    ObjectProperty
    """
    OBJECT_PROPERTY_MOVING = 0,
    OBJECT_PROPERTY_STATIONARY = 1,
    OBJECT_PROPERTY_ONCOMING = 2,
    OBJECT_PROPERTY_STOPPED = 3,
    OBJECT_PROPERTY_FREE = 4,
    OBJECT_PROPERTY_UNDEFINED = 5

OBJ_TYPE_MAP = {ObjectProperty.OBJECT_PROPERTY_MOVING: 'OBJECT_PROPERTY_MOVING',
                ObjectProperty.OBJECT_PROPERTY_STATIONARY: 'OBJECT_PROPERTY_STATIONARY',
                ObjectProperty.OBJECT_PROPERTY_ONCOMING: 'OBJECT_PROPERTY_ONCOMING',
                ObjectProperty.OBJECT_PROPERTY_STOPPED: 'OBJECT_PROPERTY_STOPPED',
                ObjectProperty.OBJECT_PROPERTY_FREE: 'OBJECT_PROPERTY_FREE',
                ObjectProperty.OBJECT_PROPERTY_UNDEFINED: 'OBJECT_PROPERTY_UNDEFINED'
                }

DEBUG_PRINT_BOX_IMAGE = True

ADMA_VALID = "IsAdma"


KINEMATICS_SELECT_LIST = [SQLBinaryExpr(COL_NAME_KINEMATICS_KINABSTS, OP_AS, OBJ_TIME_STAMPS),
                          SQLBinaryExpr(COL_NAME_KINEMATICS_RELDISTX, OP_AS, OBJ_DISTX),
                          SQLBinaryExpr(COL_NAME_KINEMATICS_RELDISTY, OP_AS, OBJ_DISTY),
                          SQLBinaryExpr(COL_NAME_KINEMATICS_RELVELX, OP_AS, OBJ_VELX),
                          SQLBinaryExpr(COL_NAME_KINEMATICS_HEADINGOVERGND, OP_AS, OBJ_ORIENT)]

ADMA_KINEMATICS_SELECT_LIST = [SQLBinaryExpr(COL_NAME_KINEMATICS_KINABSTS, OP_AS, OBJ_TIME_STAMPS),
                               SQLBinaryExpr(COL_NAME_ADMA_KINEMATICS_RELDISTX, OP_AS, OBJ_DISTX),
                               SQLBinaryExpr(COL_NAME_ADMA_KINEMATICS_RELDISTY, OP_AS, OBJ_DISTY),
                               SQLBinaryExpr(COL_NAME_ADMA_KINEMATICS_RELVELX, OP_AS, OBJ_VELX),
                               SQLBinaryExpr(COL_NAME_ADMA_KINEMATICS_RELVELY, OP_AS, OBJ_VELY),
                               SQLBinaryExpr(COL_NAME_ADMA_KINEMATICS_HEADINGOG, OP_AS, OBJ_ORIENT),
                               SQLBinaryExpr(COL_NAME_ADMA_KINEMATICS_ARELX, OP_AS, OBJ_ACCELX),
                               SQLBinaryExpr(COL_NAME_ADMA_KINEMATICS_ADMAOK, OP_AS, ADMA_VALID)]

BOX_TOLERANCE = 0.1  # 10% Tolerance for the box
DX_OFFSET = 0.5  # 0.5m offset between reflection point and adma reference

TIME_CYCLE = 0
GLOBAL_INDEX = 1
OBJECTS = 2

GLB_INDX = 0
OBJ_INDX = 1
LIFE_COUNT = 2
OBJ = 3

INDEX = "Index"

# create a random color table
COLORS = []
for g_i in range(4):
    for g_j in range(4):
        for g_k in range(4):
            COLORS.append([g_i / 3.0, g_j / 3.0, g_k / 3.0])
shuffle(COLORS)

DEBUG_ENABLE = False
DEBUG_PLOT_ENABLE = False
USE_REFLECTION_POINT = False


class RadarObject(object):  # pylint: disable=R0904
    """
    Class holding a reference to a object in the object list, the object ID and
    global ID
    """
    def __init__(self, obj):
        """
        Constructor taking the distx, disty and the vrelx as argument

        :param obj: Reference to object in the list of objects
        """
        self.__object = obj
        self.__object_id = obj[OBJ_OBJECT_ID]
        self.__global_id = obj[OBJ_GLOBAL_ID]
        self.__obj_start_index = obj[OBJ_START_INDEX]
        self.__obj_stop_index = self.__obj_start_index + len(obj[OBJ_TIME_STAMPS])
        self.__obj_type = ObjectProperty.OBJECT_PROPERTY_UNDEFINED

    def __del__(self):
        self.__object = None
        # print "Event Object Reference destroyed"

    def __copy__(self):
        """
        Make a copy of the event object class

        The reference to the object is copied as well
        """
        cpy = RadarObject(self.get_object())
        return cpy

    def get_start_index(self):
        """
        Return the Startindex

        :return: Startindex of the object
        """
        return self.__obj_start_index

    def get_stop_index(self):
        """
        Return the Stopindex

        :return: Stopindex of the object
        """
        return self.__obj_stop_index

    def set_object_type(self, index):
        """
        Set the object type using the given index
        """
        self.__obj_type = self.__object[OBJ_DYNAMIC_PROPERTY][index]

    def get_object_type(self):
        """
        GetObjectType
        """
        return self.__obj_type

    def get_object_type_label(self):
        """
        Get the text label of the object type
        """
        return OBJ_TYPE_MAP[self.__obj_type]

    def get_global_id(self):
        """
        Return the global ID of the object

        :return The Global ID of the object
        """
        return self.__global_id

    def get_object_id(self):
        """ Return the object ID

        :return The Object ID
        """
        return self.__object_id

    def get_object(self):
        """
        Return the object

        :return The Object
        """
        return self.__object

    def get_start_time(self):
        """
        Return the Starttime of the Radar Object

        :return Get the Starttime of the Object
        """
        return self.__object[OBJ_START_TIME]

    def get_stop_time(self):
        """
        Return the Stoptime of the Object

        :return the stoptime of the object
        """
        obj_length = len(self.__object[OBJ_TIME_STAMPS])
        obj_endtime = self.__object[OBJ_TIME_STAMPS][obj_length - 1]
        return obj_endtime

    def get_signal_value_by_index(self, signal, index):
        """
        Get a signal value for the given array index
        If index exceeds, 0 will be returned.

        :return a signal value for the given index
        """
        if signal == OBJ_OBJECT_ID:
            return self.__object[signal]
        else:
            # if signal not in self.__Object:
            #     signal = "f" + signal
            if index < len(self.__object[signal]):
                return self.__object[signal][index]
            else:
                return 0

    def get_signal(self, signal, start_idx=None, end_idx=None):
        """
        Get Signal Values

        :return Return the values of the given signal
                if signal is not an array, just the value is returned
                if signal is an array, values are retuned according to start and stop index
        """
        is_array = isinstance(self.__object[signal], (list, tuple))

        if is_array:
            if start_idx is None:
                start_idx = 0
            if end_idx is None:
                end_idx = len(self.__object[signal])
            if start_idx == end_idx:
                signal_array = [self.__object[signal][start_idx]]
            else:
                signal_array = self.__object[signal][start_idx:end_idx]
            return signal_array
        else:
            return self.__object[signal]

    @deprecated('get_start_index')
    def GetStartIndex(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_start_index()

    @deprecated('set_object_type')
    def SetObjectType(self, index):  # pylint: disable=C0103
        """deprecated"""
        return self.set_object_type(index)

    @deprecated('get_object_type')
    def GetObjectType(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_object_type()

    @deprecated('get_object_type_label')
    def GetObjectTypeLabel(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_object_type_label()

    @deprecated('get_global_id')
    def GetGlobalID(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_global_id()

    @deprecated('get_object_id')
    def GetObjectID(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_object_id()

    @deprecated('get_object')
    def GetObject(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_object()

    @deprecated('get_start_time')
    def GetStartTime(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_start_time()

    @deprecated('get_stop_time')
    def GetStopTime(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_stop_time()

    @deprecated('get_signal_value_by_index')
    def GetSignalValueByIndex(self, signal, index):  # pylint: disable=C0103
        """deprecated"""
        return self.get_signal_value_by_index(signal, index)

    @deprecated('get_signal')
    def GetSignal(self, signal, start_idx=None, end_idx=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_signal(signal, start_idx, end_idx)


class RadarObjectList(object):  # pylint: disable=R0902,R0904
    """Class supporting operations on Object Lists
    """
    def __init__(self, objlist):
        """TOD

        :param objlist:
        :type objlist:
        """
        self.__objectlist = objlist
        self.__bestobjdist = []
        self.__reflection_point = []
        self.__best_obj_table = []
        self.__obj_ids = []
        self.__objects_in_rect = []
        self.__relevant_objects = []
        self.__best_objects = []
        self.__len_of_kinematics = 0

        """ TESTCODE ------------------------------------------------------ """
#        box = val_fc.BoxGetCorners(5,2)
#        box_car = val_fc.BoxGetCorners(5,2,tolerance = 0.0)
#        data_lines = []
#        legend_list = []
#        degree = 0;
#
#        legend_list.append("car")
#        data_lines.append(box_car)
#
#        for i in xrange(0,3):
#            legend_list.append("box{0}".format(degree))
#            box_rot = val_fc.GetRotatedBox(box, math.radians(degree))
#            box_rot_car = val_fc.GetRotatedBox(box_car, math.radians(degree))
#            val_fc.PolygonContainsPoint(box_rot, 3.0, 0)
#            val_fc.PolygonContainsPoint(box_rot, -1, 3.0)
#            data_lines.append(box_rot)
#            legend_list.append("point{0}".format(degree))
#            data_lines.append([val_fc.BoxCalcReflectionsPoint(box_rot_car,degree)])
#            degree += 90
#
#        plotter = ValidationPlot("d:/temp/")
#        plotter.get_scatter_plot(data_lines, legend_list, "distx","disty", True,
#                                 True, fig_width=11, fig_height=11, title = "Box")
#        img_data = plotter.get_plot_data_buffer()
        """ TESTCODE ------------------------------------------------------ """

    def __generate_relevant_object_list(self, rect_obj_ts):
        """
        __GenerateRelevantObjectList
        """
        self.__relevant_objects = []
        rel_obj_list = []
        for idx in xrange(0, len(rect_obj_ts)):
            temp_obj = [rect_obj_ts[idx], [], []]
            rel_obj_list.append(temp_obj)

        kin_end_index = len(rect_obj_ts) - 1

        for obj in self.__objectlist:  # for each object in the complete object list

            rad_obj = RadarObject(obj)
            obj_starttime = rad_obj.get_start_time()
            obj_endtime = rad_obj.get_stop_time()

            obj_ts = rad_obj.get_signal(OBJ_TIME_STAMPS)
            rad_obj_index = obj_ts.index(obj_starttime)

            if obj_starttime >= rect_obj_ts[kin_end_index]:
                continue
            if obj_endtime <= rect_obj_ts[0]:
                continue

            if obj_starttime < rect_obj_ts[0]:
                obj_starttime = rect_obj_ts[0]

            if obj_endtime > rect_obj_ts[kin_end_index]:
                obj_endtime = rect_obj_ts[kin_end_index]

            glb_start = rect_obj_ts.index(obj_starttime)
            glb_end = rect_obj_ts.index(obj_endtime)

            if glb_end - glb_start > 0:
                for idx_glb in range(glb_start, glb_end):
                    rel_obj_list[idx_glb][GLOBAL_INDEX].append(rad_obj_index)
                    rel_obj_list[idx_glb][OBJECTS].append(rad_obj)
                    rad_obj_index += 1

        self.__relevant_objects = rel_obj_list

    def get_best_objects_list(self, kin_ts, kin_data, rect_obj_properties,
                              crossing=False):
        """
        GetBestObjectsList
        """

        if USE_REFLECTION_POINT:
            self.get_best_objects_list_by_reflection_point(kin_ts, kin_data, rect_obj_properties)
        else:
            self.get_best_objects_list_by_gate(kin_ts, kin_data, crossing)

    def get_best_objects_list_by_gate(self, kin_ts, kin_data, crossing=False):  # pylint: disable=R0914,R0915
        """
        the best (closest) radar objects for each time cycle in adma is found
        """
        self.__best_objects = []

        # coarse gating for selection of ADMA object
        gate_dist_x = 3
        gate_dist_y = 6
        gate_vrel_x = 5

        # MAIN Mahalanobis gate for selection of adma object in [SIGMA]
        gate_stat_dist = 3

        # for crossing situation
        if crossing is True:
            gate_dist_x = 7
            gate_dist_y = 4
            gate_stat_dist = 4.5

        self.__len_of_kinematics = len(kin_ts)
        self.__generate_relevant_object_list(kin_ts)

        for idx_rel_obj, data in enumerate(self.__relevant_objects):  # for each sorted time cycle
            time_stamp = data[TIME_CYCLE]
            index_per_timecycle = data[GLOBAL_INDEX]
            obj_per_timecycle = data[OBJECTS]

            best_obj_per_timecycle = []  # stores all the best obj for each timecycle
            obj_ind_per_timecycle = []
            dist_per_timecycle = []
            dist_backup_timecycle = []

            for idx_obj_tc in range(len(obj_per_timecycle)):  # for each obect in a time cycle
                current_obj = obj_per_timecycle[idx_obj_tc]

                index = index_per_timecycle[idx_obj_tc]

                dis_x_ref = kin_data[OBJ_DISTX.upper()][idx_rel_obj]
                dis_y_ref = kin_data[OBJ_DISTY.upper()][idx_rel_obj]
                vel_x_ref = kin_data[OBJ_VELX.upper()][idx_rel_obj]

                diff_dist_x = current_obj.GetSignalValueByIndex(OBJ_DISTX, index) - dis_x_ref
                diff_dist_y = current_obj.GetSignalValueByIndex(OBJ_DISTY, index) - dis_y_ref
                diff_vrel_x = current_obj.GetSignalValueByIndex(OBJ_VELX, index) - vel_x_ref

                dist_x_var = math.pow(current_obj.GetSignalValueByIndex(OBJ_DISTX_STD, index), 2) + math.pow(0.8, 2)
                dist_y_var = math.pow(current_obj.GetSignalValueByIndex(OBJ_DISTY_STD, index), 2) + math.pow(0.8, 2)
                vrel_x_var = math.pow(current_obj.GetSignalValueByIndex(OBJ_VELX_STD, index), 2) + math.pow(0.8, 2)

                # Compute statistical distance of object to reference.
                object_dist_pow2 = (math.pow(diff_dist_x, 2) / dist_x_var + math.pow(diff_dist_y, 2) / dist_y_var +
                                    math.pow(diff_vrel_x, 2) / vrel_x_var)
                # Alternative witout standard deviations.
                object_dist = math.sqrt(object_dist_pow2)

                dist_backup_timecycle.append(object_dist)  # this is used in case there are no best object

                if ((abs(diff_dist_x) < gate_dist_x) and
                        (abs(diff_dist_y) < gate_dist_y) and
                        (abs(diff_vrel_x) < gate_vrel_x)):

                    if object_dist < gate_stat_dist and object_dist != -1:
                        best_obj_per_timecycle.append(current_obj)  # all the best objects for each TC is appended
                        obj_ind_per_timecycle.append(index)
                        dist_per_timecycle.append(object_dist)

            if len(best_obj_per_timecycle):
                min_index = dist_per_timecycle.index(min(dist_per_timecycle))
                self.__bestobjdist.append(dist_per_timecycle[min_index])
                # best object for each time cycle
                self.__best_objects.append([time_stamp, obj_ind_per_timecycle[min_index],
                                           best_obj_per_timecycle[min_index]])
            else:
                self.__best_objects.append([time_stamp, obj_ind_per_timecycle, best_obj_per_timecycle])
                if len(dist_backup_timecycle):
                    self.__bestobjdist.append(min(dist_backup_timecycle))
                else:
                    self.__bestobjdist.append(dist_backup_timecycle)

        self.get_best_object_combination()
        self.post_process_best_objects()

    def get_best_objects_list_by_reflection_point(self, kin_ts, kin_data,  # pylint: disable=C0103,R0914,R0915
                                                  rect_obj_properties):
        """the best (closest) radar objects for each time cycle in adma is found

        :param kin_ts:
        :param kin_data:
        :param rect_obj_properties:
        """

        self.__best_objects = []
        self.__reflection_point = []

        rect_length = rect_obj_properties[COL_NAME_RECT_OBJ_OBJLENGTH]
        rect_width = rect_obj_properties[COL_NAME_RECT_OBJ_OBJWIDTH]

        # coarse gating for selection of ADMA object
        gate_vrel_x = 5
        # MAIN Mahalanobis gate for selection of adma object in [SIGMA]
        gate_stat_dist = 3.5

        self.__len_of_kinematics = len(kin_ts)
        self.__generate_relevant_object_list(kin_ts)

        index_per_timecycle = []
        obj_per_timecycle = []
        # for each sorted time cycle
        for i, data in enumerate(self.__relevant_objects):

            # get timestamp and radar object
            time_stamp = data[TIME_CYCLE]
            index_per_timecycle = data[GLOBAL_INDEX]
            obj_per_timecycle = data[OBJECTS]

            # stores all the best obj for each timecycle
            best_obj_per_timecycle = []
            obj_ind_per_timecycle = []
            dist_per_timecycle = []

            # reference position (ADMA)
            ref_distx = kin_data[OBJ_DISTX.upper()][i]
            ref_disty = kin_data[OBJ_DISTY.upper()][i]
            ref_vrelx = kin_data[OBJ_VELX.upper()][i]
            ref_orient = kin_data[OBJ_ORIENT.upper()][i]

            # calculate the rotated ego vehicle box (assuming that the reference point is the mid of rearend)
            box_ego = Rectangle(rect_width * 0.5, rect_width * 0.5, rect_length, 0)
            box_ego.rotate(ref_orient)

            # calculate the rotated gating box (assuming that the reference point is the mid of rearend)
            box_gate = Rectangle(rect_width * 0.75, rect_width * 0.75, rect_length * 1.25, rect_length * 0.25)
            box_gate.rotate(ref_orient)

            # calculate the estimated radar reflection point
            refl_point = box_gate.calc_reflection_point()
            refl_distx = ref_distx + refl_point[0]
            refl_disty = ref_disty + refl_point[1]

            if DEBUG_ENABLE:
                debug_data = []

                # draw car box
                debug_data.append(box_ego.shift(ref_distx, ref_disty))
                debug_data.append({'color': 'b', 'linestyle': '-',
                                   'label': "car orient:: {0:5.1f}".format(ref_orient * 180 / 3.1415)})

                # draw gate box
                debug_data.append(box_gate.shift(ref_distx, ref_disty))
                debug_data.append({'color': 'r', 'linestyle': '-', 'label': "gate"})

                # draw reference point
                debug_data.append([[ref_distx, ref_disty]])
                debug_data.append({'color': 'b', 'linestyle': '-', 'marker': '+', 'markersize': 10})

                # draw reflection point
                debug_data.append([[ref_distx + refl_point[0], ref_disty + refl_point[1]]])
                debug_data.append({'color': 'g', 'linestyle': '-', 'marker': '.', 'markersize': 10})

                # draw field of view
                debug_data.append([[0, 0], [200, -40], [200, 40], [0, 0]])
                debug_data.append({'color': 'k', 'linestyle': '-'})

            # for each radar obect in a time cycle
            for j in range(len(obj_per_timecycle)):
                # get object data
                obj = obj_per_timecycle[j]
                index = index_per_timecycle[j]
                current_obj = RadarObject(obj)

                # get object kinematics
                rad_distx = current_obj.GetSignalValueByIndex(OBJ_DISTX, index)
                rad_disty = current_obj.GetSignalValueByIndex(OBJ_DISTY, index)
                rad_vrelx = current_obj.GetSignalValueByIndex(OBJ_VELX, index)

                # compute difference between radar object and reference
                diff_distx = rad_distx - ref_distx
                diff_disty = rad_disty - ref_disty
                diff_vrelx = rad_vrelx - ref_vrelx

                if DEBUG_ENABLE:
                    # draw objects in range
                    debug_data.append([[rad_distx, rad_disty]])
                    debug_data.append({'color': COLORS[obj['Index'] % len(COLORS)],
                                       'linestyle': '-', 'marker': '<', 'markersize': 8})

                # Make coarse box gating
                is_in_box = box_gate.inside(diff_distx, diff_disty)
                if (is_in_box and (abs(diff_vrelx) < gate_vrel_x)):

                    diff_distx = rad_distx - refl_distx
                    diff_disty = rad_disty - refl_disty

                    diff_distx_var = (math.pow(current_obj.GetSignalValueByIndex(OBJ_DISTX_STD, index), 2) +
                                      math.pow(0.8, 2))
                    diff_disty_var = (math.pow(current_obj.GetSignalValueByIndex(OBJ_DISTY_STD, index), 2) +
                                      math.pow(0.8, 2))
                    diff_vrelx_var = (math.pow(current_obj.GetSignalValueByIndex(OBJ_VELX_STD, index), 2) +
                                      math.pow(0.8, 2))

                    # Compute staistical distance of object to reference.
                    stat_obj_dist = ((diff_distx * diff_distx) / diff_distx_var
                                     + (diff_disty * diff_disty) / diff_disty_var
                                     + (diff_vrelx * diff_vrelx) / diff_vrelx_var)

                    # store all objects in the gating box + their statistical (mahalanobis) distance
                    if (stat_obj_dist < math.pow(gate_stat_dist, 2)):
                        best_obj_per_timecycle.append(obj)
                        obj_ind_per_timecycle.append(index)
                        dist_per_timecycle.append(stat_obj_dist)

            # store best objs for each time cycle
            self.__best_objects.append([time_stamp, obj_ind_per_timecycle, best_obj_per_timecycle, dist_per_timecycle])

            # store reflection point
            self.__reflection_point.append([refl_distx, refl_disty])

            # store stat dist of closes object
            if dist_per_timecycle:
                temp = min(dist_per_timecycle)
                self.__bestobjdist.append(temp)
            else:
                self.__bestobjdist.append(0)

#            if DEBUG_ENABLE:
#                # plot only if more than two objects (the two boxes) are available
#                if i > 50 and i < 25:
#                    plotter = ValidationPlot("d:/temp/")
#                    plotter.GenerateSimplePlot(debug_data, "Time","StatDist", True,
#                                               fig_width=11, fig_height=11, title = "StatDist")
#                    plotter.get_plot_data_buffer()
#                    os.rename("d:/temp/Temp_File.png", "d:/temp/scatter_{0:04d}.png".format(i))

        self.__obj_ids = [-1] * len(self.__best_objects)

        self.get_best_object_combination()
        self.post_process_best_objects()

    def get_objects_in_rect_object(self, kin_ts, kin_data, rect_obj_properties,  # pylint: disable=R0914,R0915
                                   obj_in_box=False):
        """
        return the list of object, closed to the refelection point for each time cycle

        The reflection point is defined by the labeled rectangular object

        :param kin_ts: object
        :param kin_data:
        :param rect_obj_properties:
        :param obj_in_box:
        """
        # ObjectsInRect = []

        rect_length = rect_obj_properties[COL_NAME_RECT_OBJ_OBJLENGTH]
        rect_width = rect_obj_properties[COL_NAME_RECT_OBJ_OBJWIDTH]

        # coarse gating for selection of ADMA object
        gate_vrel_x = 5

        self.__len_of_kinematics = len(kin_ts)
        self.__generate_relevant_object_list(kin_ts)
        self.__objects_in_rect = []

        index_per_timecycle = []
        obj_per_timecycle = []
        # for each sorted time cycle

        # calculate the rotated gating box (assuming that the reference point is the mid of the box)
        box_gate = Rectangle(rect_width / 2, rect_width / 2, rect_length / 2, rect_length / 2)

        for i, data in enumerate(self.__relevant_objects):

            # get timestamp and radar object
            time_stamp = data[TIME_CYCLE]
            index_per_timecycle = data[GLOBAL_INDEX]
            obj_per_timecycle = data[OBJECTS]

            # stores all the best obj for each timecycle
            object_idx_list = []
            object_list = []

            # reference position (ADMA)
            ref_distx = round(kin_data[OBJ_DISTX.upper()][i], 5)
            ref_disty = round(kin_data[OBJ_DISTY.upper()][i], 5)
            ref_vrelx = round(kin_data[OBJ_VELX.upper()][i], 5)
            ref_orient = round(kin_data[OBJ_ORIENT.upper()][i], 5)

            box_gate.rotate(ref_orient)

            # for each radar obect in a time cycle
            for j in range(len(obj_per_timecycle)):
                # get object data
                current_obj = obj_per_timecycle[j]
                index = index_per_timecycle[j]
                # obj_timecycles =
                current_obj.get_signal(OBJ_TIME_STAMPS)

                # get object kinematics
                rad_distx = round(current_obj.GetSignalValueByIndex(OBJ_DISTX, index), 5)
                rad_disty = round(current_obj.GetSignalValueByIndex(OBJ_DISTY, index), 5)
                rad_vrelx = round(current_obj.GetSignalValueByIndex(OBJ_VELX, index), 5)

                # compute difference between radar object and reference
                diff_distx = round(rad_distx - ref_distx, 5)
                diff_disty = round(rad_disty - ref_disty, 5)
                diff_vrelx = round(rad_vrelx - ref_vrelx, 5)

                # Make coarse box gating

                is_in_box = box_gate.inside(diff_distx, diff_disty)
                if is_in_box:
                # if len(current_obj.GetSignal("OOIHistory"))>0:

                    life_inside_box = False
                    obj_distx = current_obj.get_signal(OBJ_DISTX)
                    obj_disty = current_obj.get_signal(OBJ_DISTY)
                    try:

                        ref_distx_current = round(kin_data[OBJ_DISTX.upper()]
                                                          [current_obj.get_signal(OBJ_START_INDEX)], 5)
                        ref_disty_current = round(kin_data[OBJ_DISTY.upper()]
                                                          [current_obj.get_signal(OBJ_START_INDEX)], 5)
                        ref_orient_current = round(kin_data[OBJ_ORIENT.upper()]
                                                           [current_obj.get_signal(OBJ_START_INDEX)], 5)
                    except:

                        ref_distx_current = ref_distx
                        ref_disty_current = ref_disty
                        ref_orient_current = ref_orient
                    box_gate_current = Rectangle(rect_width / 2, rect_width / 2, rect_length / 2, rect_length / 2)
                    box_gate_current.rotate(ref_orient_current)

                    obj_startx = round(obj_distx[2], 5)
                    obj_starty = round(obj_disty[2], 5)
                    startinbox = box_gate_current.inside(round(obj_startx - ref_distx_current, 5),
                                                         round(obj_starty - ref_disty_current, 5))

                    obj_endx = round(obj_distx[-2], 5)
                    obj_endy = round(obj_disty[-2], 5)
                    stopinbox = box_gate_current.inside(round(obj_endx - ref_distx_current, 5),
                                                        round(obj_endy - ref_disty_current, 5))

                    if startinbox or stopinbox:
                        life_inside_box = True

                    if obj_in_box is False and (abs(diff_vrelx) < gate_vrel_x):
                        # if (is_in_box):
                        object_list.append(current_obj)
                        object_idx_list.append(index)
                    elif life_inside_box and obj_in_box:
                        object_list.append(current_obj)
                        object_idx_list.append(index)
                    # print "Index: {0} -> obj: {1}".format(index, current_obj.GetObjectID())

            # store best objs for each time cycle
            self.__objects_in_rect.append([time_stamp, object_idx_list, object_list])

        return 0

    @staticmethod
    def get_best_object_combination():
        """TODO

        :return:
        """
        pass
        # debug_data = []

        # creating object id list for calculating id changes
#        for i in range(50, 250):   #len(self.__best_objects)
#
#            dist_per_timecycle = self.__best_objects[i][OBJECTS+1]
#            obj_per_ts = self.__best_objects[i][OBJECTS]
#
#            if dist_per_timecycle:
#                for j in range(len(dist_per_timecycle)):
#                    obj_index = obj_per_ts[j]["Index"]
#                    if DEBUG_ENABLE:
#                        debug_data.append([[i,dist_per_timecycle[j]]])
#                        debug_data.append({'color':COLORS[obj_index%len(COLORS)], 'linestyle':'',
#                                           'marker':'.', 'markersize':8})

#        if DEBUG_ENABLE:
#            plotter = ValidationPlot("d:/temp/")
#            plotter.GenerateSimplePlot(debug_data, "Time","StatDist", True, fig_width=11,
#                                       fig_height=11, title = "StatDist")
#            plotter.get_plot_data_buffer()
#            os.rename("d:/temp/Temp_File.png", "d:/temp/__StatDist.png")
#            #sys.exit()

    def post_process_best_objects(self):
        """DODO

        :return:
        """
        prev_id = -1
        obj_start_indx = -1
        global_indx = 0
        life_count = 0
        best_objects_list = []
        stored_obj = None
        # creating object id list for calculating id changes
        for i in range(len(self.__best_objects)):

            obj_per_ts = self.__best_objects[i][OBJECTS]
            id_per_ts = -1

            if obj_per_ts:
                current_obj = obj_per_ts
                id_per_ts = current_obj.get_signal(OBJ_OBJECT_ID)

                # self.__obj_ids[i] = id_per_ts

            if prev_id != id_per_ts:
                # Change
                if life_count > 0:
                    raw = [global_indx, obj_start_indx, life_count, stored_obj]
                    best_objects_list.append(raw)
                    obj_start_indx = -1
                    life_count = 0

                if id_per_ts != -1:
                    obj_start_indx = self.__best_objects[i][GLOBAL_INDEX]
                    global_indx = i
                    stored_obj = current_obj
                    life_count = 0

            if obj_start_indx != -1:
                life_count += 1

            prev_id = id_per_ts

        if obj_start_indx != -1 and life_count > 0:
            raw = [global_indx, obj_start_indx, life_count, stored_obj]
            best_objects_list.append(raw)

        self.get_best_object_table(best_objects_list)

    def get_best_object_table(self, best_objects_list):
        """TODO

        :param best_objects_list:
        :type best_objects_list:
        :return:
        """
        # post processing of the best objects list
        total_length = len(best_objects_list)
        i = 0
        best_objects_list_filtered = []
        prev_raw_data = None

        while i < total_length:

            raw_data = best_objects_list[i]

            if prev_raw_data is None:
                if raw_data[LIFE_COUNT] >= 2:
                    best_objects_list_filtered.append(raw_data)
                    prev_raw_data = raw_data
            else:
                if prev_raw_data[OBJ].get_start_index() == raw_data[OBJ].get_start_index():  # same object ID ?
                    # merge object entries
                    prev_raw_data[LIFE_COUNT] = raw_data[GLB_INDX] + raw_data[LIFE_COUNT] - prev_raw_data[GLB_INDX]

                else:
                    if raw_data[LIFE_COUNT] > 3:  # ignore short lifecycle
                        best_objects_list_filtered.append(raw_data)
                        prev_raw_data = raw_data

            i += 1
        self.__best_obj_table = best_objects_list_filtered

        self.calculate_object_ids()
        self.calculate_min_dist()

        # clear temporary attributes
        self.__relevant_objects = []
        self.__best_objects = []

    def calculate_object_ids(self):
        """
        returns the object IDs of the best objects
        """

        self.__obj_ids = [-1] * len(self.__best_objects)

        for best_obj in self.__best_obj_table:
            start = best_obj[GLB_INDX]
            lifecount = best_obj[LIFE_COUNT]
            stop = start + lifecount - 1
            obj = best_obj[OBJ]

            for i in range(start, stop):
                self.__obj_ids[i] = obj.GetObjectID()

    def calculate_min_dist(self):
        """
        calculated the mindist for the best objects
        """
        mindist = [-1] * len(self.__best_objects)

        for best_obj in self.__best_obj_table:
            start = best_obj[GLB_INDX]
            lifecount = best_obj[LIFE_COUNT]
            stop = start + lifecount - 1

            mindist[start:stop] = [self.__bestobjdist[x] for x in range(start, stop)]
        self.__bestobjdist = []
        self.__bestobjdist = mindist

    @staticmethod
    def interpolate_adma_kinematics_for_time_shift(kinematic_data, adma_delay,  # pylint: disable=C0103
                                                   on_coming=False):
        """
        Correct the ADMA data for the 100ms time delay.
        """

        kin_time_stamps = kinematic_data[OBJ_TIME_STAMPS.upper()]
        kin_time_ar = npc.array(kin_time_stamps)
        kinematics_interp = {}

        # Remove the latency delay for each value by interpolation
        for sig in kinematic_data:
            # do not interpolate timestamp
            if sig == OBJ_TIME_STAMPS.upper():
                interp_sig = kinematic_data[sig]
            # flags are interpolated using 'nearest' method
            elif sig == ADMA_VALID.upper():
                func_interp = interpolate.interp1d(kin_time_stamps,  # pylint: disable=E1101
                                                   kinematic_data[sig], kind='nearest',
                                                   axis=-1, copy=True, bounds_error=False, fill_value=npc.nan)
                interp_sig = list(func_interp(kin_time_ar - adma_delay))
            # angles must be interpolated considering wrapping
            elif sig == OBJ_ORIENT.upper():
                func_interp = interpolate.interp1d(kin_time_stamps,  # pylint: disable=E1101
                                                   unwrap(kinematic_data[sig]), kind='linear',
                                                   axis=-1, copy=True, bounds_error=False, fill_value=npc.nan)
                interp_sig = list(func_interp(kin_time_ar - adma_delay))
#                 interp_sig = list(((interp_sig + math.pi) % (2 * math.pi)) - math.pi)  # wrap back to -pi...pi
            # continuous signals are interpolated lineary
            else:
                func_interp = interpolate.interp1d(kin_time_stamps,  # pylint: disable=E1101
                                                   kinematic_data[sig], kind='linear',
                                                   axis=-1, copy=True, bounds_error=False, fill_value=npc.nan)
                interp_sig = list(func_interp(kin_time_ar - adma_delay))

            # due to interpolation some data points are lost at the beginning/and of signal and filled with NaN
            # replace these values with uninterpolated data
            for iid in range(len(interp_sig)):
                if math.isnan(interp_sig[iid]):
                    interp_sig[iid] = kinematic_data[sig][iid]
                    # kinematic_data[upper(ADMA_VALID)][iid] = 0  # set adma flag to invalid

            # overwrite old data with compensated one
            kinematics_interp[sig] = interp_sig

            if on_coming is True and sig == OBJ_DISTX.upper():
                oncome_change = 5.0
                kinematics_interp[sig] = [value - oncome_change for value in kinematics_interp[sig]]
        return kinematics_interp

    def flags(self, flags_result_ar):  # pylint: disable=R0914
        """DODO

        :param flags_result_ar:
        :return:
        """
        sig_vec = [0] * self.__len_of_kinematics
        sig_vec_long = [0] * self.__len_of_kinematics  # default vector
        sig_vec_cross = [0] * self.__len_of_kinematics  # default vector
        sig_vec_oncome = [0] * self.__len_of_kinematics  # default vector
        sig_vec_ped = [0] * self.__len_of_kinematics  # default vector
        flags_total = 0
        flags_error = [0] * 4

        for i in range(len(self.__best_obj_table)):
            start = self.__best_obj_table[i][GLB_INDX]
            stop = start + self.__best_obj_table[i][LIFE_COUNT] - 1
            obj = self.__best_obj_table[i][OBJ]
            # obj_indx_start = self.__best_obj_table[i][1]
            start_indx = self.__best_obj_table[i][OBJ_INDX]
            stop_indx = start_indx + self.__best_obj_table[i][LIFE_COUNT] - 1
            if stop_indx > len(obj.get_signal(OBJ_FLAG)):
                return flags_total, flags_error, sig_vec_long, sig_vec_oncome, sig_vec_cross, sig_vec_ped

            sig_vec[start:stop] = obj.get_signal(OBJ_FLAG)[start_indx:stop_indx]

            for j in range(start, stop):
                pre_sel_flag = sig_vec[j]
                if pre_sel_flag != -1:
                    presel_flags = pre_sel_flag
                    flags_total += 1

                    if presel_flags & 0x1:
                        sig_vec_long[j] = 1
                    if presel_flags & 0x2:
                        sig_vec_oncome[j] = 1
                    if presel_flags & 0x4:
                        sig_vec_cross[j] = 1
                    if presel_flags & 0x8:
                        sig_vec_ped[j] = 1

                    flags_error[0] += int(bool(flags_result_ar[0]) ^ bool(sig_vec_long[j]))
                    flags_error[1] += int(bool(flags_result_ar[1]) ^ bool(sig_vec_oncome[j]))
                    flags_error[2] += int(bool(flags_result_ar[2]) ^ bool(sig_vec_cross[j]))
                    flags_error[3] += int(bool(flags_result_ar[3]) ^ bool(sig_vec_ped[j]))

                else:
                    presel_flags = 0
                # obj_indx_start = obj_indx_start+1

        return flags_total, flags_error, sig_vec_long, sig_vec_oncome, sig_vec_cross, sig_vec_ped

    def signal_of_best_object(self, signal, add_filter=None):
        """TODO

        :param signal:
        :param add_filter:
        :return:
        """
        sig_vec = [0] * self.__len_of_kinematics  # default vector
        filter_vec = [0] * len(sig_vec)
        # generate the signal vector
        # temp_sig_vec = obj[SIG_NAME_OBJ_FLAG][start:stop]

        for best_obj in self.__best_obj_table:
            start = best_obj[GLB_INDX]
            lifecount = best_obj[LIFE_COUNT]
            stop = start + lifecount - 1
            rel_start_indx = best_obj[OBJ_INDX]
            rel_stop_indx = rel_start_indx + lifecount - 1
            obj = best_obj[OBJ]

            if (signal == OBJ_OBJECT_ID):
                temp_sig = obj.get_signal(signal)
                return sig_vec
            elif signal == OBJ_ORIENT or signal == OBJ_ORIENT_STD:
                temp_sig = [math.degrees(x) for x in obj.get_signal(signal)[rel_start_indx:rel_stop_indx]]
            else:
                temp_sig = obj.get_signal(signal)[rel_start_indx:rel_stop_indx]

            sig_vec[start:stop] = temp_sig
            filter_vec[start:stop] = [1] * len(temp_sig)

        if add_filter:
            return sig_vec, filter_vec

        return sig_vec

    def error_of_best_object(self, signal, adma_datas):
        """TODO

        :param signal:
        :param adma_datas:
        :return:
        """

        radar_sig_vec, filter_vec = self.signal_of_best_object(signal, True)
        error_data = [0.0] * len(radar_sig_vec)

        try:
            for j in xrange(1, len(radar_sig_vec)):
                if filter_vec[j] == 1:
                    error_data[j] = math.fabs(adma_datas[j] - radar_sig_vec[j])
        except:
            print signal

        return error_data

    def get_object_ids(self):
        """TODO

        :return:
        """
        return self.__obj_ids

    def get_object_dist(self):
        """TODO

        :return:
        """
        return self.__bestobjdist

    def get_object_reflection_point(self):
        """TODO

        :return:
        """
        return self.__reflection_point

    def get_object_in_rect(self):
        """TODO

        :return:
        """
        return self.__objects_in_rect

    def get_id_changes(self):
        """TODO

        :return:
        """
        id_ch = 0

        if len(self.__best_obj_table) > 1:

            prev_indx = None
            for i, best_obj in enumerate(self.__best_obj_table):
                curr_indx = best_obj[GLB_INDX]

                if i == 1:
                    prev_indx = curr_indx
                elif prev_indx is not None:
                    if (curr_indx - prev_indx) < int(1000 / 0.060):
                        id_ch += 1

        return id_ch

    @deprecated('__generate_relevant_object_list')
    def __GenerateRelevantObjectList(self, rect_obj_ts):  # pylint: disable=C0103
        """deprecated"""
        return self.__generate_relevant_object_list(rect_obj_ts)

    @deprecated('get_best_objects_list')
    def GetBestObjectsList(self, kin_ts, kin_data, rect_obj_properties, crossing=False):  # pylint: disable=C0103
        """deprecated"""
        return self.get_best_objects_list(kin_ts, kin_data, rect_obj_properties, crossing)

    @deprecated('get_best_objects_list_by_gate')
    def GetBestObjectsListByGate(self, kin_ts, kin_data, crossing=False):  # pylint: disable=C0103
        """deprecated"""
        return self.get_best_objects_list_by_gate(kin_ts, kin_data, crossing)

    @deprecated('get_best_objects_list_by_reflection_point')
    def GetBestObjectsListByReflectionPoint(self, kin_ts, kin_data, rect_obj_properties):  # pylint: disable=C0103
        """deprecated"""
        return self.get_best_objects_list_by_reflection_point(kin_ts, kin_data, rect_obj_properties)

    @deprecated('get_objects_in_rect_object')
    def GetObjectsInRectObject(self, kin_ts, kin_data, rect_obj_properties, obj_in_box=False):  # pylint: disable=C0103
        """deprecated"""
        return self.get_objects_in_rect_object(kin_ts, kin_data, rect_obj_properties, obj_in_box)

    @deprecated('get_best_object_combination')
    def GetBestObjectCombination(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_best_object_combination()

    @deprecated('post_process_best_objects')
    def PostProcessBestObjects(self):  # pylint: disable=C0103
        """deprecated"""
        return self.post_process_best_objects()

    @deprecated('get_best_object_table')
    def GetBestObjectTable(self, best_objects_list):  # pylint: disable=C0103
        """deprecated"""
        return self.get_best_object_table(best_objects_list)

    @deprecated('calculate_object_ids')
    def CalculateObjectIds(self):  # pylint: disable=C0103
        """deprecated"""
        return self.calculate_object_ids()

    @deprecated('calculate_min_dist')
    def CalculateMinDist(self):  # pylint: disable=C0103
        """deprecated"""
        return self.calculate_min_dist()

    @deprecated('interpolate_adma_kinematics_for_time_shift')
    def InterpolateAdmaKinematicsForTimeShift(self, kinematic_data,  # pylint: disable=C0103
                                              adma_delay, on_coming=False):
        """deprecated"""
        return self.interpolate_adma_kinematics_for_time_shift(kinematic_data,
                                                               adma_delay,
                                                               on_coming)

    @deprecated('flags')
    def Flags(self, flags_result_ar):  # pylint: disable=C0103
        """deprecated"""
        return self.flags(flags_result_ar)

    @deprecated('signal_of_best_object')
    def SignalOfBestObject(self, signal, add_filter=None):  # pylint: disable=C0103
        """deprecated"""
        return self.signal_of_best_object(signal, add_filter)

    @deprecated('error_of_best_object')
    def ErrorOfBestObject(self, signal, adma_datas):  # pylint: disable=C0103
        """deprecated"""
        return self.error_of_best_object(signal, adma_datas)

    @deprecated('get_object_ids')
    def GetObjectIds(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_object_ids()

    @deprecated('get_object_dist')
    def GetObjectDist(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_object_dist()

    @deprecated('get_object_reflection_point')
    def GetObjectReflectionPoint(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_object_reflection_point()

    @deprecated('get_object_in_rect')
    def GetObjectInRect(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_object_in_rect()

    @deprecated('get_id_changes')
    def GetIdChanges(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_id_changes()


class ACCMatchObjectList_Class(object):  # pylint: disable=C0103,R0902
    """TODO
    """
    def __init__(self, event, dbobjectkin):
        """taking the event, database kinematics at specific timestamp as argument

        :param event: Event
        :param dbobjectkin: DatabaseKinematicsList (RECTOBJID, RELDISTX, RELDISTY, RELVELX) at specific timestamp
        """
        self.__best_db_object_id_table = []
        self.__event = event
        self.__db_object_kinematics = dbobjectkin
        self.__event_radar_object = self.__event.GetEventObject().get_object()
        self.__radar_object_start_index = None

        self.__set_best_db_object_id_table()

        self.__dx_gate = None
        self.__dy_gate = None
        self.__dvx_gate = None

    def __del__(self):
        self.__event = None
        self.__event_radar_object = None
        self.__radar_object_start_index = None

        self.__db_object_kinematics = None
        self.__dx_gate = None
        self.__dy_gate = None
        self.__dvx_gate = None

    def __calc_gates(self, db_object):
        """ Set dx-, dx-, dVxGate
        """
        ind_obj = self.__event.GetWStartIndex()

        self.__dx_gate = abs(db_object[COL_NAME_KINEMATICS_RELDISTX] -
                             self.__event_radar_object[OBJ_DISTX][ind_obj])
        self.__dy_gate = abs(db_object[COL_NAME_KINEMATICS_RELDISTY] -
                             self.__event_radar_object[OBJ_DISTY][ind_obj])
        self.__dvx_gate = abs(db_object[COL_NAME_KINEMATICS_RELVELX] -
                              self.__event_radar_object[OBJ_VELX][ind_obj])

    def __get_dist_between_objects(self):
        """ Return the EuclidDistance

        :return euclid_distance
        """
        return math.pow(self.__dx_gate, 2) + math.pow(self.__dy_gate, 2) + math.pow(self.__dvx_gate, 2)

    def __set_best_db_object_id_table(self):
        """ Set/ Add RectObjID's in a RectObjIDList, depends on calculations of euclid_distance and the Gates
        """
        best_object_euclid_distance = []

        for db_object in self.__db_object_kinematics:
            self.__calc_gates(db_object)

            euclid_distance = self.__get_dist_between_objects()

            if(self.__dx_gate < 1.5 and self.__dy_gate < 1.5 and
               self.__dvx_gate < 3 and euclid_distance < best_object_euclid_distance):
                self.__best_db_object_id_table.append(db_object[COL_NAME_KINEMATICS_RECTOBJID])
                best_object_euclid_distance = euclid_distance

    def get_best_db_object_id_table(self):
        """
        Return the List of the RectObjID which were matched with an RadarObject

        :return RectObjIDList
        """
        if len(self.__best_db_object_id_table):
            return self.__best_db_object_id_table[0]
        else:
            return []

    @deprecated('__calc_gates')
    def __CalcGates(self, db_object):  # pylint: disable=C0103
        """deprecated"""
        return self.__calc_gates(db_object)

    @deprecated('__get_dist_between_objects')
    def __GetDistBetweenObjects(self):  # pylint: disable=C0103
        """deprecated"""
        return self.__get_dist_between_objects()

    @deprecated('__set_best_db_object_id_table')
    def __SetBestDBObjectIDTable(self):  # pylint: disable=C0103
        """deprecated"""
        return self.__set_best_db_object_id_table()

    @deprecated('get_best_db_object_id_table')
    def GetBestDBObjectIDTable(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_best_db_object_id_table()


class BaseAdasObject(object):  # pylint: disable=R0921
    """
    base class for all adas objects
    """

    __metaclass__ = ABCMeta

    def __init__(self, obj_id, data_source, signal_names):
        """Constructor - this is an abstract class and can not be instantiated

        :param obj_id: object id
        :param data_source: data source e.g. DB or bin file
        :param signal_names: signal names to load
        """
        self._id = obj_id
        self._data_source = data_source
        # Signals
        self._signals = {}
        self.__class_norm = {}
        self._signal_names = signal_names
        self._log = Logger(self.__class__.__name__)

    def set_class_norm(self, ref_obj, filter_if, timestamp, class_norm):
        """
        Sets the classification norm

        :param ref_obj: reference object
        :param filter_if: object filter interface
        :param timestamp: timestamp
        :param class_norm: classification norm, abstracted term for distance to referece object
        """
        self.__class_norm[(ref_obj, filter_if, timestamp)] = class_norm

    def get_class_norm(self, ref_obj, filter_if, timestamp):
        """
        Gets the classification norm belonging to a
        (reference object, object filter interface, timestamp) triple

        :param ref_obj: reference object
        :param filter_if: object filter interface
        :param timestamp: timestamp
        :return: classification norm, abstracted term for distance to referece object
        """
        return self.__class_norm[(ref_obj, filter_if, timestamp)]

    def _get_subset_of_signals(self, startts=None, stopts=None):

        """Makes a subset of the signals within the time interval

        :param startts: start time stamp
        :param stopts: stop time stamp
        """
        subset_signals = {}
        for sig_name, sig_val in self._signals.iteritems():
            subset_signals[sig_name] = \
                sig_val.GetSubsetForTimeInterval(startts, stopts)
        return subset_signals

    @abstractmethod
    def get_subset(self, startts=None, stopts=None):
        """
        abstact method
        """
        pass

    def get_id(self):
        """
        Get Object Id
        """
        return self._id

    def get_start_time(self):
        """Get the Start Time of the Object

        :return: start time stamp or None if no signals
        """
        sig_names = self._signals.keys()
        if sig_names:
            return self._signals[sig_names[0]].GetStartTimestamp()
        else:
            self._log.error("No signals available")
            return None

    def get_end_time(self):
        """Get the Start Time of the Object
        @return: start time slot or None if no signals
        """
        sig_names = self._signals.keys()
        if sig_names:
            return self._signals[sig_names[0]].GetEndTimestamp()
        else:
            self._log.error("No signals available")
            return None

    def get_signal_value(self, signal_name, timestamp):
        """Get the Object Signal Value for the given Timestamp

        :return: signal value at the given time stamp (GetValueAtTimestamp) or None if no such signal
        """
        if signal_name in self._signals.keys():
            return self._signals[signal_name].GetValueAtTimestamp(timestamp)
        else:
            self._log.error("No such signal available")
            return None

    def get_signal(self, signal_name):
        """
        Gets signal by its name
        """
        ret = self._signals.get(signal_name)
        if ret is None:
            self._log.error("No such signal available")
        return ret

    def get_signals(self):
        """
        Returns all signals of the object
        """
        return self._signals

    @deprecated('_get_subset_of_signals')
    def _GetSubsetOfSignals(self, startts=None, stopts=None):  # pylint: disable=C0103
        """deprecated"""
        return self._get_subset_of_signals(startts, stopts)

    @deprecated('get_id')
    def GetId(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_id()

    @deprecated('get_start_time')
    def GetStartTime(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_start_time()

    @deprecated('get_end_time')
    def GetEndTime(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_end_time()

    @deprecated('get_signal_value')
    def GetSignalValue(self, signal_name, timestamp):  # pylint: disable=C0103
        """deprecated"""
        return self.get_signal_value(signal_name, timestamp)

    @deprecated('get_signal')
    def GetSignal(self, signal_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_signal(signal_name)

    @deprecated('get_signals')
    def GetSignals(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_signals()


class BaseObjectList(object):  # pylint: disable=R0921
    """Base Object List
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, data_source, sensor, list_name, object_filter_if, signal_names):  # pylint: disable=R0913
        """Initialize the Object List

        :param data_source: data source e.g. db
        :param sensor: Sensor Name (ARS4xx, ...)
        :param list_name: list name
        :param object_filter_if: filter object
        :param signal_names: list of names of signals to be loaded
        """
        self._data_source = data_source
        self.__sensor = sensor
        self.__list_name = list_name
        self.__object_filter_if = object_filter_if
        self._objects = []
        self._signal_names = signal_names

    def __str__(self):
        pass

    def get_sensor(self):
        """
        Get the sensor name

        :return: name of the sensor
        """
        return self.__sensor

    def get_name(self):
        """
        Get the list name

        :return: list name
        """
        return self.__list_name

    def get_object_by_id(self, obj_id):
        """Get the object

        :param obj_id: object id for lookup
        :return: list of objects where obj_id matches
        """
        return [x for x in self._objects if x.get_id() == obj_id]

    def get_objects(self):
        """
        Get all objects

        :return: list of adas objects
        """
        return self._objects

    def get_objects_by_time_stamp(self, ref_obj, startts=None, stopts=None, **kwargs):
        """
        GetObjectsByTimeStamp

        :param ref_obj: reference object
        :param startts: start time stamp
        :param stopts: stop time stamp
        :return: dictionary of matching objects (list) per time stamp(=key)
            {ts1:[obj1, obj2, obj3], ts2:[obj1, obj2]}
        """
        return self.__object_filter_if.get_filtered_objects(self._objects, ref_obj, startts, stopts, **kwargs)

    @staticmethod
    def __get_object_with_longest_track(best_tracked_obj_by_ts, distance_min=float('-inf'), distance_max=float('inf')):
        """
        Selects the object(s) with the longest track and within the given distance

        :param best_tracked_obj_by_ts: see GetBestTrackedObject()
        :param distance_min: min distance for the obj search
        :param distance_max: max distance for the obj search
        :return: list of best objects or empty list
        """
        best_objs = []
        obj_periods = {}
        obj_refs = {}
        for obj in best_tracked_obj_by_ts:
            startts = obj.get_start_time()
            endts = obj.get_end_time()
            x_min = obj.get_signal(OBJ_DISTX).GetMinValue()
            x_max = obj.get_signal(OBJ_DISTX).GetMaxValue()
            if x_min >= distance_min and x_max <= distance_max:
                if obj_periods.get(id(obj)):
                    obj_periods[id(obj)] += endts - startts
                else:
                    obj_periods[id(obj)] = endts - startts
                    obj_refs[id(obj)] = obj
        if obj_periods:
            sorted_obj_periods = sorted(obj_periods.iteritems(), key=itemgetter(1))
            # best_obj_ids = []
            best_time = 0.0
            for idx, sob in enumerate(reversed(sorted_obj_periods)):
                if idx == 0:
                    best_time = sob[1]
                if sob[1] == best_time:
                    best_objs.append(obj_refs[sob[0]])

        return best_objs

    def get_best_tracked_object(self, ref_obj, startts=None, stopts=None,   # pylint: disable=R0912,R0913,R0914
                                best_only=False, distance_min=float('-inf'), distance_max=float('inf'), **kwargs):
        """
        Selects the matching object(s) (with the longest track and within the given distance if best_only = True)

        :param ref_obj: reference object
        :param startts: start time stamp
        :param stopts: stop time stamp
        :param best_only: returns only the list of object(s) with the longest track and within the given distance
        :param distance_min: min distx allowed
        :param distance_max: max distx allowed
        :return:  [best_obj1, best_obj2] with Signals best_obj1: ts1..ts2 best_obj2: ts3..ts4 where ts2<ts3 etc. or []
        """
        objects_by_time_stamp = \
            self.get_objects_by_time_stamp(ref_obj, startts, stopts, **kwargs)

        prev_best_obj = None
        # dictionary of matching object (one single) per time stamp(=key)
        best_object_by_time_stamp = OrderedDict()
        for time_stamp, obj_list in objects_by_time_stamp.iteritems():
            if (len(obj_list) == 1):
                best_object_by_time_stamp[time_stamp] = obj_list[0]
            elif(len(obj_list) == 0):
                best_object_by_time_stamp[time_stamp] = None
            else:
                # select best object from multiple candidates based on the classification norm
                best_obj = None
                for obj in obj_list:
                    if best_obj is None:
                        best_obj = obj
                        # first obj in the dict is taken as the initial best object
                        best_obj_dist_to_ref_obj = obj.get_class_norm(ref_obj, self.__object_filter_if, time_stamp)
                    else:
                        curr_obj_dist_to_ref_obj = obj.get_class_norm(ref_obj, self.__object_filter_if, time_stamp)
                        # if obj is closer to ref_obj than the best in the candidate list until now,
                        # it is a better match, add as the best
                        if curr_obj_dist_to_ref_obj < best_obj_dist_to_ref_obj:
                            best_obj = obj
                        # if obj is as close to ref_obj as the best in the candidate list until now,
                        # it can win if it was also the best obj in the previous time stamp, ...
                        elif curr_obj_dist_to_ref_obj == best_obj_dist_to_ref_obj:
                            if (prev_best_obj is not None) and (obj == prev_best_obj):
                                best_obj = obj
                            # ...otherwise the first equally good candidate remains the winner
                        # obj is worse than the current best
                        else:
                            pass
                # assign best object to time_stamp
                prev_best_obj = best_obj
                best_object_by_time_stamp[time_stamp] = best_obj

        best_tracked_obj_by_ts = BaseObjectList.__create_obj_list_from_best_obj_per_ts(best_object_by_time_stamp)
        if best_only:
            return BaseObjectList.__get_object_with_longest_track(best_tracked_obj_by_ts,
                                                                  distance_min, distance_max)
        else:
            return best_tracked_obj_by_ts

    @staticmethod
    def __create_obj_list_from_best_obj_per_ts(best_object_by_time_stamp_ordered_dict):  # pylint: disable=C0103
        """
        best_object_by_time_stamp_ordered_dict must be an OrderedDict (ts1<ts2<ts3)

        Converts [ts1: [best_obj1], ts2: [best_obj2], ts3: [best_obj2]] to
                 [best_obj1, best_obj2] with Signals best_obj1: ts1, best_obj2: ts2..ts3
        """
        start_ts = None
        end_ts = None
        best_object_list = []
        prev_obj = None
        init_algo = False
        time_stamps = best_object_by_time_stamp_ordered_dict.keys()
        last_ts = max(time_stamps)
        for tstamp, obj in best_object_by_time_stamp_ordered_dict.iteritems():
            if obj is not None:
                if start_ts is None:
                    start_ts = tstamp
                # init
                if not init_algo:
                    start_ts = tstamp
                    prev_obj = obj
                    init_algo = True
                else:
                    # new track
                    if (obj is not prev_obj) and (prev_obj is not None):
                        best_object_list.append(prev_obj.get_subset(start_ts, end_ts))
                        start_ts = tstamp
                    # end of interval
                    if (tstamp == last_ts):
                        best_object_list.append(obj.get_subset(start_ts, tstamp))
                end_ts = tstamp
                prev_obj = obj
            else:
                if prev_obj is not None:
                    best_object_list.append(prev_obj.get_subset(start_ts, end_ts))
                    start_ts = None
                    prev_obj = None

        return best_object_list

    def set_filter(self, obj_filter_if):
        """
        Set Filter Object

        :param obj_filter_if: object filter
        """
        self.__object_filter_if = obj_filter_if

    @abstractmethod
    def load_objects(self, startts=None, stopts=None, **kwargs):
        """Load all tracked Objects in the given timespan.

        :param startts: Abs Start Timestamp
        :param stopts: Abs Stop Timestamp
        :param kwargs: optional arguments
        """
        pass

    @deprecated('get_sensor')
    def GetSensor(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_sensor()

    @deprecated('get_name')
    def GetName(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_name()

    @deprecated('get_object_by_id')
    def GetObjectById(self, obj_id):  # pylint: disable=C0103
        """deprecated"""
        return self.get_object_by_id(obj_id)

    @deprecated('get_objects')
    def GetObjects(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_objects()

    @deprecated('get_objects_by_time_stamp')
    def GetObjectsByTimeStamp(self, ref_obj, startts=None, stopts=None, **kwargs):  # pylint: disable=C0103
        """deprecated"""
        return self.get_objects_by_time_stamp(ref_obj, startts, stopts, **kwargs)

    @deprecated('get_best_tracked_object')
    def GetBestTrackedObject(self, *args, **kwargs):  # pylint: disable=C0103
        """deprecated"""
        return self.get_best_tracked_object(*args, **kwargs)

    @deprecated('__create_obj_list_from_best_obj_per_ts')
    def __CreateObjListFromBestObjPerTs(self, best_object_by_time_stamp_ordered_dict):  # pylint: disable=C0103
        """deprecated"""
        return self.__create_obj_list_from_best_obj_per_ts(best_object_by_time_stamp_ordered_dict)

    @deprecated('set_filter')
    def SetFilter(self, obj_filter_if):  # pylint: disable=C0103
        """deprecated"""
        return self.set_filter(obj_filter_if)

    @deprecated('load_objects')
    def LoadObjects(self, startts=None, stopts=None, **kwargs):  # pylint: disable=C0103
        """deprecated"""
        return self.load_objects(startts, stopts, **kwargs)


"""
$Log: adas_objects.py  $
Revision 1.4 2017/05/05 09:58:09CEST Hecker, Robert (heckerr) 
Made Changes as needed from Stefan04 Wagner.
Revision 1.3 2016/11/28 09:18:38CET Hospes, Gerd-Joachim (uidv8815) 
add stop index
Revision 1.2 2016/04/27 16:21:29CEST Mertens, Sven (uidv7805)
some cleanup
Revision 1.1 2015/04/23 19:04:45CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/obj/project.pj
Revision 1.43 2015/03/20 08:00:45CET Mertens, Sven (uidv7805)
docu fixes
--- Added comments ---  uidv7805 [Mar 20, 2015 8:00:45 AM CET]
Change Package : 319697:1 http://mks-psad:7002/im/viewissue?selection=319697
Revision 1.42 2015/03/19 16:57:37CET Mertens, Sven (uidv7805)
changing log to logger
--- Added comments ---  uidv7805 [Mar 19, 2015 4:57:37 PM CET]
Change Package : 318794:1 http://mks-psad:7002/im/viewissue?selection=318794
Revision 1.41 2015/02/06 16:46:26CET Ellero, Stefano (uidw8660)
No deprecated functions/methods of package obj must be used inside all STK and its module tests.
--- Added comments ---  uidw8660 [Feb 6, 2015 4:46:27 PM CET]
Change Package : 301801:1 http://mks-psad:7002/im/viewissue?selection=301801
Revision 1.40 2015/02/03 18:55:36CET Ellero, Stefano (uidw8660)
No deprecated functions/methods of package obj must be used inside all STK and its module tests.
--- Added comments ---  uidw8660 [Feb 3, 2015 6:55:37 PM CET]
Change Package : 301801:1 http://mks-psad:7002/im/viewissue?selection=301801
Revision 1.39 2014/11/21 13:49:01CET Hospes, Gerd-Joachim (uidv8815)
timestamp interpolation used for all objects (not only ADMA),
new signal definition
--- Added comments ---  uidv8815 [Nov 21, 2014 1:49:01 PM CET]
Change Package : 283590:1 http://mks-psad:7002/im/viewissue?selection=283590
Revision 1.38 2014/10/31 10:08:57CET Hospes, Gerd-Joachim (uidv8815)
fix pep8, pylints
--- Added comments ---  uidv8815 [Oct 31, 2014 10:08:58 AM CET]
Change Package : 276932:1 http://mks-psad:7002/im/viewissue?selection=276932
Revision 1.37 2014/10/30 16:29:36CET Hospes, Gerd-Joachim (uidv8815)
add time interpolation to ADMA, rename deprecated functions, adjust doc
--- Added comments ---  uidv8815 [Oct 30, 2014 4:29:36 PM CET]
Change Package : 276932:1 http://mks-psad:7002/im/viewissue?selection=276932
Revision 1.36 2014/09/25 13:29:11CEST Hospes, Gerd-Joachim (uidv8815)
adapt stk.img files to style guide, new names used in all modules and tests except stk.img tests
--- Added comments ---  uidv8815 [Sep 25, 2014 1:29:11 PM CEST]
Change Package : 264203:1 http://mks-psad:7002/im/viewissue?selection=264203
Revision 1.35 2014/08/14 14:46:11CEST Hospes, Gerd-Joachim (uidv8815)
changes by Miklos Sandor for faster object detection (>50 times)
--- Added comments ---  uidv8815 [Aug 14, 2014 2:46:12 PM CEST]
Change Package : 253112:2 http://mks-psad:7002/im/viewissue?selection=253112
Revision 1.34 2014/08/08 15:23:56CEST Sandor-EXT, Miklos (uidg3354)
to be checked yet!
--- Added comments ---  uidg3354 [Aug 8, 2014 3:23:56 PM CEST]
Change Package : 233779:1 http://mks-psad:7002/im/viewissue?selection=233779
Revision 1.32 2014/07/15 10:11:43CEST Hecker, Robert (heckerr)
Bug Fixed with calling deprecated Method.
--- Added comments ---  heckerr [Jul 15, 2014 10:11:43 AM CEST]
Change Package : 248697:1 http://mks-psad:7002/im/viewissue?selection=248697
Revision 1.31 2014/05/08 14:21:19CEST Hecker, Robert (heckerr)
Increased TestCoverage.
--- Added comments ---  heckerr [May 8, 2014 2:21:20 PM CEST]
Change Package : 234909:1 http://mks-psad:7002/im/viewissue?selection=234909
Revision 1.30 2014/05/06 13:16:00CEST Hecker, Robert (heckerr)
BugFix for missing @staticmethod property.
--- Added comments ---  heckerr [May 6, 2014 1:16:01 PM CEST]
Change Package : 234920:1 http://mks-psad:7002/im/viewissue?selection=234920
Revision 1.29 2014/04/30 16:58:06CEST Hecker, Robert (heckerr)
reduced pep8.
Revision 1.28 2014/04/29 10:26:31CEST Hecker, Robert (heckerr)
updated to new guidelines.
Revision 1.27 2014/04/14 10:42:06CEST Hecker, Robert (heckerr)
Added some needed bugfixes from Miklos.
--- Added comments ---  heckerr [Apr 14, 2014 10:42:07 AM CEST]
Change Package : 230893:1 http://mks-psad:7002/im/viewissue?selection=230893
Revision 1.26 2014/03/17 21:06:55CET Hecker, Robert (heckerr)
Did Extension.
--- Added comments ---  heckerr [Mar 17, 2014 9:06:55 PM CET]
Change Package : 225816:1 http://mks-psad:7002/im/viewissue?selection=225816
Revision 1.25 2014/03/17 13:46:36CET Ahmed, Zaheer (uidu7634)
bug fixed GetSignalValueByIndex()
--- Added comments ---  uidu7634 [Mar 17, 2014 1:46:37 PM CET]
Change Package : 224328:1 http://mks-psad:7002/im/viewissue?selection=224328
Revision 1.24 2014/02/06 16:15:50CET Sandor-EXT, Miklos (uidg3354)
OrderedDict
--- Added comments ---  uidg3354 [Feb 6, 2014 4:15:51 PM CET]
Change Package : 208827:2 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.23 2014/01/29 16:09:41CET Sandor-EXT, Miklos (uidg3354)
signal_names to be extracted added
--- Added comments ---  uidg3354 [Jan 29, 2014 4:09:41 PM CET]
Change Package : 208827:2 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.22 2014/01/24 10:52:34CET Sandor-EXT, Miklos (uidg3354)
global obj id added
--- Added comments ---  uidg3354 [Jan 24, 2014 10:52:35 AM CET]
Change Package : 208827:2 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.21 2014/01/16 16:40:22CET Sandor-EXT, Miklos (uidg3354)
rect_obj_properties removed from the signature of GetBestObjectsListByGate
--- Added comments ---  uidg3354 [Jan 16, 2014 4:40:23 PM CET]
Change Package : 208827:2 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.20 2013/12/16 15:47:24CET Sandor-EXT, Miklos (uidg3354)
width, length added
Revision 1.19 2013/12/16 14:08:45CET Sandor-EXT, Miklos (uidg3354)
docu and constants
--- Added comments ---  uidg3354 [Dec 16, 2013 2:08:46 PM CET]
Change Package : 208827:2 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.18 2013/12/05 07:34:20CET Sandor-EXT, Miklos (uidg3354)
commented out part was added again
--- Added comments ---  uidg3354 [Dec 5, 2013 7:34:20 AM CET]
Change Package : 208827:1 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.17 2013/12/03 17:52:06CET Sandor-EXT, Miklos (uidg3354)
commented out not implemented and used extensions because of coverage
--- Added comments ---  uidg3354 [Dec 3, 2013 5:52:06 PM CET]
Change Package : 208827:1 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.16 2013/12/03 17:22:50CET Sandor-EXT, Miklos (uidg3354)
pep8
--- Added comments ---  uidg3354 [Dec 3, 2013 5:22:51 PM CET]
Change Package : 208827:1 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.15 2013/12/03 13:47:38CET Sandor-EXT, Miklos (uidg3354)
object matching
--- Added comments ---  uidg3354 [Dec 3, 2013 1:47:38 PM CET]
Change Package : 208827:1 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.14 2013/04/05 07:04:58CEST Raedler, Guenther (uidt9430)
- fixed renaming error
--- Added comments ---  uidt9430 [Apr 5, 2013 7:04:59 AM CEST]
Change Package : 175136:1 http://mks-psad:7002/im/viewissue?selection=175136
Revision 1.13 2013/04/03 08:02:16CEST Mertens, Sven (uidv7805)
pylint: minor error, warnings fix
--- Added comments ---  uidv7805 [Apr 3, 2013 8:02:16 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.12 2013/03/28 15:25:15CET Mertens, Sven (uidv7805)
pylint: W0311 (indentation), string class
--- Added comments ---  uidv7805 [Mar 28, 2013 3:25:16 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.11 2013/03/28 14:43:06CET Mertens, Sven (uidv7805)
pylint: resolving some R0904, R0913, R0914, W0107
--- Added comments ---  uidv7805 [Mar 28, 2013 2:43:07 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.10 2013/03/28 14:20:07CET Mertens, Sven (uidv7805)
pylint: solving some W0201 (Attribute %r defined outside __init__) errors
Revision 1.9 2013/03/28 10:05:27CET Mertens, Sven (uidv7805)
removing unused imports
--- Added comments ---  uidv7805 [Mar 28, 2013 10:05:28 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.8 2013/03/28 09:33:17CET Mertens, Sven (uidv7805)
pylint: removing unused imports
--- Added comments ---  uidv7805 [Mar 28, 2013 9:33:17 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.7 2013/03/22 08:24:26CET Mertens, Sven (uidv7805)
aligning bulk of files again for peping 8
Revision 1.6 2013/03/01 15:52:54CET Hecker, Robert (heckerr)
Updates recording Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 1, 2013 3:52:54 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.5 2013/02/28 08:12:20CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:21 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2013/02/27 17:55:12CET Hecker, Robert (heckerr)
Removed all E000 - E200 Errors regarding Pep8.
--- Added comments ---  heckerr [Feb 27, 2013 5:55:12 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/27 16:19:57CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 27, 2013 4:19:58 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/26 20:14:24CET Raedler, Guenther (uidt9430)
- Updates after Pep8 Styleguides
--- Added comments ---  uidt9430 [Feb 26, 2013 8:14:24 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/02/11 10:49:59CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/obj/project.pj
------------------------------------------------------------------------------
-- from ETK/VPC/validation_radar_objects.py Archive
------------------------------------------------------------------------------
Revision 1.17 2012/11/23 11:00:52CET Hammernik-EXT, Dmitri (uidu5219)
- bugfix: added changes from revision 1.15
--- Added comments ---  uidu5219 [Nov 23, 2012 11:00:53 AM CET]
Change Package : 163367:1 http://mks-psad:7002/im/viewissue?selection=163367
Revision 1.16 2012/10/10 11:16:15CEST Hammernik-EXT, Dmitri (uidu5219)
- removed rectobjid attribute
--- Added comments ---  uidu5219 [Oct 10, 2012 11:16:15 AM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.15 2012/09/18 08:47:05CEST Sampat, Janani Vasumathy (uidu5218)
- bug fix for detecting objects inside the ROI that start and stop within
the ROI (GetObjectsInRectObject)
--- Added comments ---  uidu5218 [Sep 18, 2012 8:47:08 AM CEST]
Change Package : 148800:1 http://mks-psad:7002/im/viewissue?selection=148800
Revision 1.14 2012/09/13 12:20:04CEST Hammernik-EXT, Dmitri (uidu5219)
- bugfix in GetSignal: end_idx=len(self.__object[signal])
- added functionalty to get Signal information for same start and end index
--- Added comments ---  uidu5219 [Sep 13, 2012 12:20:04 PM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.13 2012/08/24 09:01:25CEST Hammernik-EXT, Dmitri (uidu5219)
- added rectobjid to the object
--- Added comments ---  uidu5219 [Aug 24, 2012 9:01:25 AM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.12 2012/08/10 10:35:01CEST Sampat-EXT, Janani Vasumathy (uidu5218)
- option to retrieve only objects inside a rectangular object that line inside
the rect
--- Added comments ---  uidu5218 [Aug 10, 2012 10:35:01 AM CEST]
Change Package : 110628:1 http://mks-psad:7002/im/viewissue?selection=110628
Revision 1.11 2012/07/02 13:51:00CEST Hammernik-EXT, Dmitri (uidu5219)
- defined get/set methods for rectobjid from DB
--- Added comments ---  uidu5219 [Jul 2, 2012 1:51:01 PM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.10 2012/04/17 17:44:04CEST Sampat-EXT, Janani Vasumathy (uidu5218)
- gating and box calulation changed
- values are rounded
--- Added comments ---  uidu5218 [Apr 17, 2012 5:44:06 PM CEST]
Change Package : 110628:1 http://mks-psad:7002/im/viewissue?selection=110628
Revision 1.9 2012/03/28 13:44:31CEST Sampat-EXT, Janani Vasumathy (uidu5218)
- enhanced GetSignal function to return a list with start and stop index
--- Added comments ---  uidu5218 [Mar 28, 2012 1:44:31 PM CEST]
Change Package : 97504:2 http://mks-psad:7002/im/viewissue?selection=97504
Revision 1.8 2012/03/27 16:26:24CEST Raedler-EXT, Guenther (uidt9430)
- added new function GetObjectsInRectObject() to find all objects which are
inside the given label
- use RadarObject class to encapsulate the object dictionary
- renamed some variables
--- Added comments ---  uidt9430 [Mar 27, 2012 4:26:25 PM CEST]
Change Package : 88554:1 http://mks-psad:7002/im/viewissue?selection=88554
Revision 1.7 2012/03/27 15:41:43CEST Raedler-EXT, Guenther (uidt9430)
- reintegrate branch into trunk
- add function GetBestObjectsListByReflectionPoint() for the new approach
- add function  GetBestObjectsListByGate() for the old approach
- use existing function GetBestObjectsList() as interface for existing observers
--- Added comments ---  uidt9430 [Mar 27, 2012 3:41:44 PM CEST]
Change Package : 88554:1 http://mks-psad:7002/im/viewissue?selection=88554
Revision 1.4.1.2 2012/01/24 16:48:44CET Oprisan, Dan (oprisand)
- further development of FindBestObject startegy
--- Added comments ---  oprisand [Jan 24, 2012 4:48:45 PM CET]
Change Package : 46865:30 http://mks-psad:7002/im/viewissue?selection=46865
Revision 1.4.1.1 2012/01/16 10:41:33CET Oprisan, Dan (oprisand)
- improvement of object selection (find best objects)
--- Added comments ---  oprisand [Jan 16, 2012 10:41:33 AM CET]
Change Package : 46865:30 http://mks-psad:7002/im/viewissue?selection=46865
Revision 1.6 2012/02/01 11:49:44CET Raedler-EXT, Guenther (uidt9430)
- change ObjectID change conditions
--- Added comments ---  uidt9430 [Feb 1, 2012 11:49:45 AM CET]
Change Package : 90579:1 http://mks-psad:7002/im/viewissue?selection=90579
Revision 1.5 2012/01/17 16:54:32CET Raedler-EXT, Guenther (uidt9430)
- fixed error in interpolation of the orientation signal
- improved best object selection
- fixed error in post processing
Revision 1.4 2011/11/29 13:11:33CET Sampat-EXT, Janani Vasumathy (uidu5218)
- Index list removed
- Best Objects complete calculation split into 3 functions
- Table column values are given generic names instead of numbers
--- Added comments ---  uidu5218 [Nov 29, 2011 1:11:33 PM CET]
Change Package : 88149:1 http://mks-psad:7002/im/viewissue?selection=88149
Revision 1.3 2011/11/25 09:57:17CET Raedler-EXT, Guenther (uidt9430)
- improved relevant object detection
- added oncoming
- changed gating
- fixed error in the best object detection
--- Added comments ---  uidt9430 [Nov 25, 2011 9:57:18 AM CET]
Change Package : 67780:7 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.2 2011/11/08 08:36:26CET Raedler Guenther (uidt9430) (uidt9430)
- started to implement GetBestObjectsList using Boxes and Reflectionpoints
(effective code is commented out)
--- Added comments ---  uidt9430 [Nov 8, 2011 8:36:26 AM CET]
Change Package : 67780:7 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.1 2011/10/27 15:38:30CEST Raedler Guenther (uidt9430) (uidt9430)
Initial revision
Member added to project /nfs/projekte1/PROJECTS/ARS301/06_Algorithm/
05_Testing/05_Test_Environment/algo/ars301_req_test/valf_tests/vpc/project.pj

"""
