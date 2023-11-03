"""
stk/obj/adas_object_filters.py
-------------------

Base implementations of the object filters

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.2 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2016/04/27 16:21:00CEST $
"""
# Import Python Modules -------------------------------------------------------
from abc import ABCMeta, abstractmethod
import math
from collections import OrderedDict
# import datetime
# import os

# Import STK Modules ----------------------------------------------------------
import stk.util.logger as log
from stk.obj.geo.rect import Rectangle
from stk.obj.adas_objects import OBJ_LENGTH, OBJ_WIDTH, OBJ_DISTX, OBJ_DISTY, OBJ_VELX, OBJ_ORIENT
from stk.obj.label_objects import LABELING_TYPE_ROI, DEFAULT_LABELING_TYPE
from stk.img.plot import ValidationPlot
from stk.util.helper import deprecated


# Class Implementations -------------------------------------------------------
class ObjectFilterIf(object):
    """ Object filter interface """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self):
        """ Constructor abstractmethod"""
        pass

    @abstractmethod
    def get_filtered_objects(self, obj_list, ref_obj, startts=None, stopts=None,
                             **kwargs):
        """ GetFilteredObjects abstractmethod"""
        pass


class ObjectByGateFilter(ObjectFilterIf):
    """ Object filter by gate """
    def __init__(self):
        """ Constructor """
        ObjectFilterIf.__init__(self)

    def get_filtered_objects(self, obj_list, ref_obj,
                             startts=None, stopts=None,
                             **kwargs):
        """
        Returns a best matching object list to ref_obj
        from the obj_list for each time slot {ts1:[obj1, obj2, obj3], ts2:[obj1, obj2]}
        if ref_obj=None, it returns all object ids in time slot 0
        :param obj_list: object list from which to select
        :param ref_obj: reference object
        :param startts: start time slot
        :param stopts: stop time slot
        :param gate_dist_x: (kwarg) gate value for x distance (diff to ref obj must be less)
        :param gate_dist_y: (kwarg) gate value for y distance (diff to ref obj must be less)
        :param gate_vrelx: (kwarg) gate value for x velocity (diff to ref obj must be less)
        @return: OrderedDict() {ts0:[obj0,obj1,...], ts1:[obj0,obj1,...],...} where ts0 < ts1
                 The objects itself are assigned a classification norm (~distance),
                 which can be used in further matching/tracking algorithms
INPUT:
--------------------------------------------------------
distance from the ref_obj for a given time slot:
d(obj1) < d(obj2) < d(obj3), gate_x, gate_y, gate_vel


|--0--||--1--||--2--||--3--||--4--||--5--|   => startts = 0, stopts = 5

       |-----||-----||-----||-----|          => ref_obj
              |-----||-----|                 => obj1
|-----||-----||-----||-----|                 => obj2
|-----||-----||-----||-----||-----|          => obj3

CASE1: OUTPUT: best_object_list
--------------------------------------------------------
       |-----|                               => obj2
              |-----||-----|                 => obj1
                            |-----|          => obj3

        """

        gate_dist_x = 3
        gate_dist_y = 6
        gate_vrelx = 5
        if "gate_dist_x" in kwargs.keys():
            gate_dist_x = kwargs["gate_dist_x"]
        if "gate_dist_y" in kwargs.keys():
            gate_dist_y = kwargs["gate_dist_y"]
        if "gate_vrelx" in kwargs.keys():
            gate_vrelx = kwargs["gate_vrelx"]

        best_object_list_for_all_ts = OrderedDict()
        # find the best matching object
        # within the timespan of the ref_obj for each time slot
        ref_obj_distx_sig = ref_obj.get_signal(OBJ_DISTX).GetSubsetForTimeInterval(startts, stopts)
        ref_obj_disty_sig = ref_obj.get_signal(OBJ_DISTY).GetSubsetForTimeInterval(startts, stopts)
        ref_obj_velx_sig = ref_obj.get_signal(OBJ_VELX).GetSubsetForTimeInterval(startts, stopts)

        # find startts and stopts of ref_obj and
        # filter out the other objects for this interval
        ref_obj_timestamps = ref_obj_distx_sig.GetTimestamps()

        for tstamp in ref_obj_timestamps:
            # best_obj_distance_in_ts = None
            best_obj_list = []
            ref_obj_distx = ref_obj_distx_sig.GetValueAtTimestamp(tstamp)
            ref_obj_disty = ref_obj_disty_sig.GetValueAtTimestamp(tstamp)
            ref_obj_velx = ref_obj_velx_sig.GetValueAtTimestamp(tstamp)
            for obj in obj_list:
                obj_distx = obj.get_signal(OBJ_DISTX).GetValueAtTimestamp(tstamp)
                obj_disty = obj.get_signal(OBJ_DISTY).GetValueAtTimestamp(tstamp)
                obj_velx = obj.get_signal(OBJ_VELX).GetValueAtTimestamp(tstamp)

                if (obj_distx is not None) and \
                   (obj_disty is not None) and \
                   (obj_velx is not None):

                    # get all objects in the gate and calculate distance
                    if (ObjectByGateFilter.__is_obj_in_gate(obj_distx, obj_disty, obj_velx,
                                                            ref_obj_distx, ref_obj_disty, ref_obj_velx,
                                                            gate_dist_x, gate_dist_y, gate_vrelx)):

                        curr_obj_distance = ObjectByGateFilter.euclidean_distance_2d(obj_distx, obj_disty,
                                                                                     ref_obj_distx, ref_obj_disty)
                        obj.set_class_norm(ref_obj, self, tstamp, curr_obj_distance)
                        best_obj_list.append(obj)
                        # # if only the best distance would be selected
                        # if (best_obj_distance_in_ts is None):
                        #    best_obj_distance_in_ts = curr_obj_distance
                        #    best_obj_list.append(obj)
                        # elif (best_obj_distance_in_ts == curr_obj_distance):
                        #    best_obj_list.append(obj)
                        # elif (best_obj_distance_in_ts > curr_obj_distance):
                        #    best_obj_distance_in_ts = curr_obj_distance
                        #    best_obj_list = []
                        #    best_obj_list.append(obj)

            best_object_list_for_all_ts[tstamp] = best_obj_list

        return best_object_list_for_all_ts

    @staticmethod
    def euclidean_distance_2d(xc1, yc1, xc2, yc2):
        """ Euclidean Distance between two signals in 2D """
        # ..or numpy.linalg.norm( array([x1,y1], array([x2, y2]) )
        return math.sqrt(math.pow(xc1 - xc2, 2) + math.pow(yc1 - yc2, 2))

    @staticmethod
    def __is_obj_in_gate(obj_x, obj_y, obj_velx, ref_obj_x,
                         ref_obj_y, ref_obj_velx,
                         gate_dist_x, gate_dist_y, gate_vrelx):
        # pylint: disable=R0913
        """ distance is smaller than threshold for the whole list"""
        return ((math.fabs(obj_x - ref_obj_x) < gate_dist_x) and
                (math.fabs(obj_y - ref_obj_y) < gate_dist_y) and
                (math.fabs(obj_velx - ref_obj_velx) < gate_vrelx))

    @deprecated('get_filtered_objects')
    def GetFilteredObjects(self, obj_list, ref_obj, startts=None, stopts=None, **kwargs):  # pylint: disable=C0103
        """deprecated"""
        return self.get_filtered_objects(obj_list, ref_obj, startts, stopts, **kwargs)

    @deprecated('__is_obj_in_gate')
    def __IsObjInGate(self, obj_x, obj_y, obj_velx, ref_obj_x, ref_obj_y, ref_obj_velx,  # pylint: disable=C0103
                      gate_dist_x, gate_dist_y, gate_vrelx):
        """deprecated"""
        return self.__is_obj_in_gate(obj_x, obj_y, obj_velx,
                                     ref_obj_x, ref_obj_y, ref_obj_velx,
                                     gate_dist_x, gate_dist_y, gate_vrelx)


class ObjectByReflectionPoint(ObjectFilterIf):
    """ Object Filter by Reflexionpoint """
    def __init__(self):
        """ Constructor """
        ObjectFilterIf.__init__(self)

    def get_filtered_objects(self, obj_list, ref_obj,
                             startts=None, stopts=None, **kwargs):
        pass

    @deprecated('get_filtered_objects')
    def GetFilteredObjects(self, obj_list, ref_obj,  # pylint: disable=C0103
                           startts=None, stopts=None, **kwargs):
        """deprecated"""
        return self.get_filtered_objects(obj_list, ref_obj,
                                         startts, stopts, kwargs)


class ObjectInRectangle(ObjectFilterIf):
    """
    Object Filter in Rectangle
    """
    def __init__(self, label_rectangle_enlarge_multiplier=1.0):
        """
        Constructor
        :param label_rectangle_enlarge_multiplier: size of label rectangle will be multiplied with this parameter
        """
        ObjectFilterIf.__init__(self)
        self.__logger = log.Logger(self.__class__.__name__)
        self.enlarge = label_rectangle_enlarge_multiplier

    def get_filtered_objects(self, obj_list, ref_obj,
                             startts=None, stopts=None, **kwargs):
        """
        Returns an object list from the obj_list for each time slot
        which objects are in the Region of Interest (ROI) = ref_obj
        if ref_obj=None, it returns all object ids in time slot 0
        :param obj_list: object list from which to select
        :param ref_obj: reference object
        :param startts: start time slot
        :param stopts: stop time slot
        @return: OrderedDict() {ts0:[obj0,obj1,...], ts1:[obj0,obj1,...],...} where ts0 < ts1
                 The objects itself are assigned a classification norm (~distance),
                 which can be used in further matching/tracking algorithms
        INPUT:
        --------------------------------------------------------
        distance from the ref_obj for a given time slot:
        ref_obj is a ROI (Region of Interrest), it is chekced, whether all objects are within the ROI

        |--0--||--1--||--2--||--3--||--4--||--5--|   => startts = 0, stopts = 5

               |-----||-----||-----||-----|          => ref_obj
                      |-----||-----|                 => obj1
        |-----||-----||-----||-----|                 => obj2
        |-----||-----||-----||-----||-----|          => obj3

        OUTPUT: for ObjectInRect
        --------------------------------------------------------
                      |-----||-----|                 => obj1
               |-----||-----||-----|                 => obj2
               |-----||-----||-----|                 => obj3 (moved out of ROI for ts4)

        """

        object_in_ref_obj_list_for_all_ts = OrderedDict()
        # find the best matching object
        # within the timespan of the ref_obj for each time slot
        ref_obj_distx_sig = ref_obj.get_signal(OBJ_DISTX).GetSubsetForTimeInterval(startts, stopts)
        ref_obj_disty_sig = ref_obj.get_signal(OBJ_DISTY).GetSubsetForTimeInterval(startts, stopts)
        ref_obj_head_sig = ref_obj.get_signal(OBJ_ORIENT).GetSubsetForTimeInterval(startts, stopts)
        ref_obj_length_sig = ref_obj.get_signal(OBJ_LENGTH).GetSubsetForTimeInterval(startts, stopts)
        ref_obj_width_sig = ref_obj.get_signal(OBJ_WIDTH).GetSubsetForTimeInterval(startts, stopts)

        # find startts and stopts of ref_obj and filter out the other objects for this interval
        # new_startts = ref_obj_distx_sig.GetStartTimestamp()
        # new_stopts  = ref_obj_distx_sig.GetEndTimestamp()
        ref_obj_timestamps = ref_obj_distx_sig.GetTimestamps()

        # self.__logger.info("--- START " + datetime.datetime.now().time().isoformat())
        # self.__logger.info("ref obj start ts: " + str(ref_obj_timestamps[0]))
        # self.__logger.info("ref obj end ts: " + str(ref_obj_timestamps[-1]))
        # self.__logger.info("len ts: " + str(len(ref_obj_timestamps)))
        # self.__logger.info("interval in sec: " + str((ref_obj_timestamps[-1] - ref_obj_timestamps[0]) / 1000000.0))
        # self.__logger.info("nr of objects: " + str(len(obj_list)))
        count_obj_have_values_in_ref_all = 0
        count_obj_matches_all = 0
        count_obj_doesnothave_values_in_ref_all = 0

        if hasattr(ref_obj, "GetLabelingType"):
            ref_obj_labeling_type = ref_obj.get_labeling_type()
        else:
            ref_obj_labeling_type = LABELING_TYPE_ROI
            self.__logger.error("Object with id: " + str(ref_obj.get_id()) +
                                " had no labeling type, using default: " + str(DEFAULT_LABELING_TYPE))

        # TODO set/unset debug
        debug_on = False
        flag = None
        for idx, tstamp in enumerate(ref_obj_timestamps):
            # if tstamp == 3362083655:  # 735516672.0:
            #    pass
            object_in_ref_obj_list = []
            ref_obj_distx = ref_obj_distx_sig.GetValueAtTimestamp(tstamp)
            ref_obj_disty = ref_obj_disty_sig.GetValueAtTimestamp(tstamp)
            ref_obj_head = ref_obj_head_sig.GetValueAtTimestamp(tstamp)
            ref_obj_length = ref_obj_length_sig.GetValueAtTimestamp(tstamp)
            ref_obj_width = ref_obj_width_sig.GetValueAtTimestamp(tstamp)

            if ref_obj_labeling_type == 0:
                box_gate = Rectangle(ref_obj_width * 0.5 * self.enlarge,
                                     ref_obj_width * 0.5 * self.enlarge,
                                     ref_obj_length * 0.5 * self.enlarge,
                                     ref_obj_length * 0.5 * self.enlarge)

                label_type = "RECT"
                # 30 April 2014: Matlab autolabel tool lblt_db_insert_rectangularobjects_from_export.m ver. 1.8
                # sets label type to rect and center of rectangle to distx, disty
                # refl_point = box_gate.CalcReflectionsPoint()
                # ref_obj_distx = ref_obj_distx + refl_point[0]
                # ref_obj_disty = ref_obj_disty + refl_point[1]
            else:
                # if ref_obj_labeling_type == LABELING_TYPE_ROI:
                box_gate = Rectangle(ref_obj_width * 0.5 * self.enlarge,
                                     ref_obj_width * 0.5 * self.enlarge,
                                     ref_obj_length * 0.5 * self.enlarge,
                                     ref_obj_length * 0.5 * self.enlarge)

                label_type = "ROI"
                pass  # see exception handling above

            box_gate.rotate(ref_obj_head)

            for obj in obj_list:
                obj_distx = obj.get_signal(OBJ_DISTX).GetValueAtTimestamp(tstamp)
                obj_disty = obj.get_signal(OBJ_DISTY).GetValueAtTimestamp(tstamp)
                obj_orient = obj.get_signal(OBJ_ORIENT).GetValueAtTimestamp(tstamp)
                obj_velx = obj.get_signal(OBJ_VELX).GetValueAtTimestamp(tstamp)
                if debug_on:
                    obj_width = obj.get_signal(OBJ_WIDTH).GetValueAtTimestamp(tstamp)
                    obj_length = obj.get_signal(OBJ_LENGTH).GetValueAtTimestamp(tstamp)
                    if hasattr(obj, "get_object_id"):
                        moid = obj.get_object_id()
                    else:
                        moid = obj.get_id()
                    loid = ref_obj.get_id()

                if (obj_distx is not None) and (obj_disty is not None) and (obj_velx is not None):
                    count_obj_have_values_in_ref_all += 1
                    diff_distx = obj_distx - ref_obj_distx
                    diff_disty = obj_disty - ref_obj_disty
                    if debug_on:
                        xdev = str(round(100 * diff_distx / ref_obj_width, 2))
                        ydev = str(round(100 * diff_disty / ref_obj_length, 2))
                        xdiff = str(round(diff_distx, 2))
                        ydiff = str(round(diff_disty, 2))

                    if box_gate.inside(diff_distx, diff_disty):
                        count_obj_matches_all += 1
                        # if in the box, dist is set to zero. could be refined in the future
                        curr_obj_distance = 0
                        obj.set_class_norm(ref_obj, self, tstamp, curr_obj_distance)
                        object_in_ref_obj_list.append(obj)

                    else:
                        pass
                    if debug_on:  # and loid == 161443:and (moid == 8 or moid == 5):  # and obj_distx > 170.0:
                        box_radar = Rectangle(obj_width * 0.5,
                                              obj_width * 0.5,
                                              obj_length * 0.5,
                                              obj_length * 0.5)
                        box_radar.rotate(obj_orient)

                        if flag is None:
                            self.__logger.info("Used labeling type for oid " +
                                               str(ref_obj.get_id()) +
                                               ' is: ' + label_type)
                            flag = True

                        self.__draw_rectangels(moid, loid, box_radar, obj_distx,
                                               obj_disty, obj_orient, box_gate,
                                               ref_obj_distx, ref_obj_disty,
                                               ref_obj_head, int(tstamp))
                else:
                    count_obj_doesnothave_values_in_ref_all += 1

            object_in_ref_obj_list_for_all_ts[tstamp] = object_in_ref_obj_list

        # self.__logger.info("count_obj_matches_all: " + str(count_obj_matches_all))
        # self.__logger.info("count_obj_have_values_in_ref_all: " + str(count_obj_have_values_in_ref_all))
        # tmp = "count_obj_doesnothave_values_in_ref_all: " + str(count_obj_doesnothave_values_in_ref_all)
        # self.__logger.info(tmp)
        # self.__logger.info("--- END " + datetime.datetime.now().time().isoformat())

        return object_in_ref_obj_list_for_all_ts

    def __draw_rectangels(self, moid, loid, box_radar, distx, disty, heading,
                          box_gate, ref_distx, ref_disty, ref_orient, ts):

        # draw car box
        be = [(p[0] + distx, p[1] + disty) for p in box_radar._Rectangle__point_list[0:5]]
        xvals = [i[0] for i in be]
        yvals = [i[1] for i in be]

        # draw gate box

        bg = [(p[0] + ref_distx, p[1] + ref_disty) for p in box_gate._Rectangle__point_list[0:5]]
        xvals += [i[0] for i in bg]
        yvals += [i[1] for i in bg]
        debug_data = [be, bg, [(distx, disty)]]

        # plot
        plotter = ValidationPlot("d:/tmp/kino")
        # plotter.generate_figure()
        # debug_data = [[(1, 2), (1, 3)], [(10, 12), (10, 13)]]
        x_ext = [min(xvals) - 1, max(xvals) + 1]
        y_ext = [min(yvals) - 1, max(yvals) + 1]
        plotter.generate_plot(data=debug_data, data_names=['radar', 'label'], x_axis_name="distX", y_axis_name="distY",
                              bool_line=True, bool_legend=True, fig_width=11, fig_height=11, title="StatDist",
                              x_axis_ext=x_ext, y_axis_ext=y_ext)

        # plotter.get_plot_data_buffer()
        plotter.get_drawing_from_buffer(plotter.get_plot_data_buffer(),
                                        'lbl_oid_' + str(loid) + '___bin_oid' +
                                        str(moid) + '___ts_' + str(ts) +
                                        '_matching', width=11, height=11)
        # os.rename("d:/tmp/kino/Valf_File.png", "d:/temp/kino/scatter_{0:04d}.png".format(ts))

    @deprecated('get_filtered_objects')
    def GetFilteredObjects(self, obj_list, ref_obj,  # pylint: disable=C0103
                           startts=None, stopts=None, **kwargs):
        """deprecated"""
        return self.get_filtered_objects(obj_list, ref_obj,
                                         startts, stopts, **kwargs)

"""
$Log: adas_object_filters.py  $
Revision 1.2 2016/04/27 16:21:00CEST Mertens, Sven (uidv7805) 
type should be the define
Revision 1.1 2015/04/23 19:04:45CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/obj/project.pj
Revision 1.19 2015/02/06 16:48:37CET Ellero, Stefano (uidw8660)
No deprecated functions/methods of package obj must be used inside all STK and its module tests.
--- Added comments ---  uidw8660 [Feb 6, 2015 4:48:37 PM CET]
Change Package : 301801:1 http://mks-psad:7002/im/viewissue?selection=301801
Revision 1.18 2015/02/03 18:55:36CET Ellero, Stefano (uidw8660)
No deprecated functions/methods of package obj must be used inside all STK and its module tests.
Revision 1.17 2015/01/26 14:19:59CET Mertens, Sven (uidv7805)
removing deprecated call
--- Added comments ---  uidv7805 [Jan 26, 2015 2:20:00 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.16 2014/09/25 13:29:12CEST Hospes, Gerd-Joachim (uidv8815)
adapt stk.img files to style guide, new names used in all modules and tests except stk.img tests
--- Added comments ---  uidv8815 [Sep 25, 2014 1:29:12 PM CEST]
Change Package : 264203:1 http://mks-psad:7002/im/viewissue?selection=264203
Revision 1.15 2014/08/14 14:46:08CEST Hospes, Gerd-Joachim (uidv8815)
changes by Miklos Sandor for faster object detection (>50 times)
--- Added comments ---  uidv8815 [Aug 14, 2014 2:46:08 PM CEST]
Change Package : 253112:2 http://mks-psad:7002/im/viewissue?selection=253112
Revision 1.14 2014/08/08 15:23:55CEST Sandor-EXT, Miklos (uidg3354)
to be checked yet!
--- Added comments ---  uidg3354 [Aug 8, 2014 3:23:56 PM CEST]
Change Package : 233779:1 http://mks-psad:7002/im/viewissue?selection=233779
Revision 1.13 2014/04/30 16:58:05CEST Hecker, Robert (heckerr)
reduced pep8.
--- Added comments ---  heckerr [Apr 30, 2014 4:58:05 PM CEST]
Change Package : 233703:1 http://mks-psad:7002/im/viewissue?selection=233703
Revision 1.12 2014/04/30 12:12:00CEST Hecker, Robert (heckerr)
Get modifications from Miklos.
Revision 1.11 2014/04/29 10:26:32CEST Hecker, Robert (heckerr)
updated to new guidelines.
--- Added comments ---  heckerr [Apr 29, 2014 10:26:32 AM CEST]
Change Package : 233703:1 http://mks-psad:7002/im/viewissue?selection=233703
Revision 1.10 2014/04/28 17:24:39CEST Hecker, Robert (heckerr)
some updates.
--- Added comments ---  heckerr [Apr 28, 2014 5:24:39 PM CEST]
Change Package : 233593:1 http://mks-psad:7002/im/viewissue?selection=233593
Revision 1.9 2014/04/25 16:26:57CEST Hecker, Robert (heckerr)
update with Miklos.
--- Added comments ---  heckerr [Apr 25, 2014 4:26:58 PM CEST]
Change Package : 228373:1 http://mks-psad:7002/im/viewissue?selection=228373
Revision 1.8 2014/04/25 09:26:30CEST Hecker, Robert (heckerr)
updated needed files for Miklos.
--- Added comments ---  heckerr [Apr 25, 2014 9:26:30 AM CEST]
Change Package : 233045:1 http://mks-psad:7002/im/viewissue?selection=233045
Revision 1.6 2014/02/06 16:15:49CET Sandor-EXT, Miklos (uidg3354)
OrderedDict
--- Added comments ---  uidg3354 [Feb 6, 2014 4:15:49 PM CET]
Change Package : 208827:2 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.5 2014/01/24 10:54:07CET Sandor-EXT, Miklos (uidg3354)
todo added for python 2.6->2.7
--- Added comments ---  uidg3354 [Jan 24, 2014 10:54:07 AM CET]
Change Package : 208827:2 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.4 2013/12/16 14:07:31CET Sandor-EXT, Miklos (uidg3354)
mapping adjustments
--- Added comments ---  uidg3354 [Dec 16, 2013 2:07:31 PM CET]
Change Package : 208827:2 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.3 2013/12/03 17:22:49CET Sandor-EXT, Miklos (uidg3354)
pep8
--- Added comments ---  uidg3354 [Dec 3, 2013 5:22:49 PM CET]
Change Package : 208827:1 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.2 2013/12/03 13:46:53CET Sandor-EXT, Miklos (uidg3354)
object matching
--- Added comments ---  uidg3354 [Dec 3, 2013 1:46:53 PM CET]
Change Package : 208827:1 http://mks-psad:7002/im/viewissue?selection=208827
"""
