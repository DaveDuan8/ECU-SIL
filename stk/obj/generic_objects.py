"""
stk/obj/generic_objects.py
-------------------

Base implementations of the object filters

:org:           Continental AG
:author:        Miklos Sandor

:version:       $Revision: 1.5 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2015/12/07 13:30:58CET $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
import numpy as np

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.util.helper import deprecated
from stk.obj.adas_objects import BaseAdasObject, BaseObjectList
from stk.val.result_types import Signal
from stk.obj.error import AdasObjectLoadError

# from stk.db.obj.objdata import COL_NAME_KINEMATICS_KINABSTS, COL_NAME_KINEMATICS_RELDISTX, \
#                               COL_NAME_KINEMATICS_RELDISTY, COL_NAME_KINEMATICS_RELVELX

from stk.obj.adas_objects import OBJECT_PORT_NAME, OBJ_TIME_STAMPS, \
    OBJ_GLOBAL_ID, OBJ_OBJECT_ID, GENERIC_OBJECT_SIGNAL_NAMES, \
    OBJ_DISTX, OBJ_DISTY, OBJ_VELX
from stk.util.logger import Logger, INFO


# - classes -----------------------------------------------------------------------------------------------------------
class GenObjList(object):
    """
    GenObjList is lightweight version of GenericObjectList for fast object matching

    E.g.::
        generic_object_list = GenObjList(data_manager, bus_name, sig_names=MY_BIN_SIGNALS)
        best_obj = generic_object_list.get_best_tracked_object(ref_obj)
    """
    def __init__(self, data_manager, bus_name, sig_names=None, distx_sig_name=None, disty_sig_name=None,
                 velx_sig_name=None):
        """
        :param data_manager: data_manager
        :param bus_name: bus_name
        :param sig_names: names of the signals to be extracted, default: [OBJ_DISTX, OBJ_DISTY, OBJ_VELX]
        :param distx_sig_name: distx_sig_name, default: OBJ_DISTX
        :param disty_sig_name: disty_sig_name, default: OBJ_DISTX
        :param velx_sig_name: velx_sig_name, default: OBJ_VELX
        """
        self.objects = []
        self.data_manager = data_manager
        self.bus_name = bus_name
        self.logger = Logger(self.__class__.__name__)

        if sig_names is None:
            self.sig_names = [OBJ_DISTX, OBJ_DISTY, OBJ_VELX]
        else:
            self.sig_names = sig_names
        if distx_sig_name is None:
            self.distx_sig_name = OBJ_DISTX
        else:
            self.distx_sig_name = distx_sig_name
        if disty_sig_name is None:
            self.disty_sig_name = OBJ_DISTY
        else:
            self.disty_sig_name = disty_sig_name
        if velx_sig_name is None:
            self.velx_sig_name = OBJ_VELX
        else:
            self.velx_sig_name = velx_sig_name

        self.disty_sig_name = disty_sig_name
        self.velx_sig_name = velx_sig_name
        self.load()

    def load(self):
        """
        loads objects from signal extractor objects port
        """
        objects = self.data_manager.GetDataPort(OBJECT_PORT_NAME, self.bus_name)
        for idx, obj_dict in enumerate(objects):
            self.objects.append(GenObj(obj_dict[OBJ_OBJECT_ID], obj_dict[OBJ_GLOBAL_ID], idx,
                                       obj_dict[OBJ_TIME_STAMPS][0], obj_dict[OBJ_TIME_STAMPS][-1]))

    @staticmethod
    def get_overlap(ref_startts, ref_stopts, my_startts, my_stopts):
        """
        Gets the overlapping time interval between reference and candidate object

        :param ref_startts: ref_startts
        :param ref_stopts: ref_stopts
        :param my_startts: my_startts
        :param my_stopts: my_stopts
        """
        if my_startts <= ref_startts:
            if my_stopts >= ref_startts:
                startts = ref_startts
                stopts = min(my_stopts, ref_stopts)
                return startts, stopts
        else:
            if my_startts <= ref_stopts:
                startts = my_startts
                stopts = min(my_stopts, ref_stopts)
                return startts, stopts
        return None, None

    def get_best_tracked_object(self, ref_obj, min_nr_ts=50, min_nr_lifetime_full_overlap=50, max_norm=1.0,
                                get_lightweight_obj=False, get_all_objects=False):
        """
        gets a GenericRectObject (,GenObj) with the best track based on best norm an min number of timestamps

        :param ref_obj: ref_oid from the object DB
        :param min_nr_ts: minimum number of overlapping time slots considered for matching
        :param min_nr_lifetime_full_overlap: objects having a full overlap during their whole lifetime are selected.
                                             this parameter limit the minimum required lifetime for this kind of selection
        :param max_norm: maximum norm (root mean square deviation of distance and velocity) considered for matching
        :param get_lightweight_obj: return also lightweight GenObj
        :param get_all_objects: returns all objects which fulfill minimum criteria
        :return: best obj as GenericRectObject/None or if get_lightweight_obj: GenericRectObject, GenObj or None, None
                 if get_all_objects: [(GenericRectObject1, GenObj1), (GenericRectObject2, GenObj2)]
        """
        # The typical accuracy of the sensor may be taken from the OD requirement specification:
        # doors://rbgs854a:40000/?version=2&prodID=0&view=00000001&urn=urn:telelogic::1-503e822e5ec3651e-O-352-000221c5
        std_err_x_off = 0.15
        std_err_y_off = 0.23
        std_err_y_prop_x = 0.0044
        std_err_v_off = 0.2

        ret_objects = []
        rts = ref_obj.get_signal(OBJ_DISTX).GetTimestamps()
        rdx = ref_obj.get_signal(OBJ_DISTX).GetValue()
        rdy = ref_obj.get_signal(OBJ_DISTY).GetValue()
        rvx = ref_obj.get_signal(OBJ_VELX).GetValue()
        ref_timestamp = np.fromiter(rts, np.float)
        ref_distx = np.fromiter(rdx, np.float)
        ref_disty = np.fromiter(rdy, np.float)
        ref_velx = np.fromiter(rvx, np.float)
        ref_startts = ref_obj.get_start_time()
        ref_stopts = ref_obj.get_end_time()

        # compute cycle time from the first 2 timestamps difference
        if len(rts) > 2:
            cycle_time = rts[1] - rts[0]
        else:
            cycle_time = 60000

        min_length_ts = cycle_time * min_nr_ts

        best_obj = None
        best_norm = None
        best_ol_startts = None
        best_ol_stopts = None
        # self.logger.debug("ref oid: " + str(ref_obj.get_id()))
        sig_length_error = False
        for co in self.objects:
            ol_starts, ol_stopts = self.get_overlap(ref_startts, ref_stopts, co.startts, co.stopts)
            # Reduce the minimum overlapping time for objects which spent their whole life in the label
            min_time_in_label = max(cycle_time * min_nr_lifetime_full_overlap, (co.stopts - co.startts) - 1)
            # For other objects a minimum overlapping time is required
            min_time_in_label = min(min_time_in_label, min_length_ts)
            if ol_starts is not None and ol_stopts is not None and (ol_stopts - ol_starts) > min_time_in_label:
                # determine start and stop indexes of reference and candidate objects
                cots, codx, cody, covx = co.get_ts_distx_disty_velx(self.data_manager, self.bus_name)
                obj_timestamp = np.fromiter(cots, np.float)
                r_start_idx = np.where(ref_timestamp == ol_starts)[0]
                r_stop_idx = np.where(ref_timestamp == ol_stopts)[0]
                co_start_idx = np.where(obj_timestamp == ol_starts)[0]
                co_stop_idx = np.where(obj_timestamp == ol_stopts)[0]
                # if indexes were found:
                if r_start_idx.size != 0 and r_stop_idx.size != 0 and co_start_idx.size != 0 and co_stop_idx.size != 0:
                    r_start_idx = r_start_idx[0]
                    r_stop_idx = r_stop_idx[0]
                    co_start_idx = co_start_idx[0]
                    co_stop_idx = co_stop_idx[0]
                    sig_length_ref = r_stop_idx - r_start_idx + 1
                    sig_length_co = co_stop_idx - co_start_idx + 1
                    # if index lengths are the same:
                    if sig_length_ref == sig_length_co:
                        # candidate object signals
                        obj_timestamp = obj_timestamp[co_start_idx:co_stop_idx + 1]
                        co_distx = np.fromiter(codx, np.float)[co_start_idx:co_stop_idx + 1]
                        co_disty = np.fromiter(cody, np.float)[co_start_idx:co_stop_idx + 1]
                        co_velx = np.fromiter(covx, np.float)[co_start_idx:co_stop_idx + 1]
                        # reference object signals
                        r_distx = ref_distx[r_start_idx:r_stop_idx + 1]
                        r_disty = ref_disty[r_start_idx:r_stop_idx + 1]
                        r_velx = ref_velx[r_start_idx:r_stop_idx + 1]
                        if (len(co_distx) != len(r_distx) or len(co_disty) != len(r_disty) or
                                len(co_velx) != len(r_velx)):
                            self.logger.error("signal length check failed for global oid: " + str(co.global_oid))
                        else:
                            # if ref_obj.get_id() == 161443:
                            #    pass
                            # see formula definition in EM/OD Design specification
                            std_err_x = np.array([std_err_x_off] * sig_length_ref)
                            std_err_y = np.array([std_err_y_off] * sig_length_ref) + std_err_y_prop_x * co_distx
                            std_err_v = np.array([std_err_v_off] * sig_length_ref)
                            norm = np.linalg.norm([(co_distx - r_distx) / std_err_x, (co_disty - r_disty) / std_err_y,
                                                   (co_velx - r_velx) / std_err_v])
                            norm_norm = norm / np.float(sig_length_ref)
                            is_norm_ok = norm_norm < max_norm
                            if get_all_objects:
                                # self.logger.debug("OK oid: " + str(co.oid) + " goid: " + str(co.global_oid) +
                                #                  " norm: " + str(norm_norm))
                                if is_norm_ok:
                                    # print "ref oid: " + str(ref_obj.get_id())
                                    # print "OK oid: " + str(co.oid) + " goid: " + str(co.global_oid)
                                    # print "norm: " + str(norm_norm)
                                    if get_lightweight_obj:
                                        ret_objects.append((co.get(self.sig_names, ol_starts, ol_stopts,
                                                                   self.data_manager, self.bus_name), co))
                                    else:
                                        ret_objects.append(co.get(self.sig_names, ol_starts, ol_stopts,
                                                                  self.data_manager, self.bus_name))
                            else:
                                if (best_norm is None or norm_norm < best_norm) and is_norm_ok:
                                    best_norm = norm_norm
                                    best_obj = co
                                    best_ol_startts = ol_starts
                                    best_ol_stopts = ol_stopts
                    else:
                        # self.logger.debug("signal lengths are not equal, reference / candidate obj: " +
                        #                  str(sig_length_co) + '/' + str(sig_length_ref))
                        # self.logger.debug("ref timestamps: " +
                        #                  str(ref_timestamp[r_start_idx:r_stop_idx + 1].tolist()))
                        # self.logger.debug("obj timestamps: " +
                        #                  str(obj_timestamp[co_start_idx:co_stop_idx + 1].tolist()))
                        sig_length_error = True
                else:
                    # self.logger.debug( "no overlap" )
                    pass
        if sig_length_error:
            self.logger.error("length of reference object signals were not equal to the measurement object signals" +
                              " use DbObjectList:interpolate_to_time_system() to have" +
                              " the same time stamps for the reference objects that the measurement has")
        # return only the best
        if not get_all_objects:
            if best_obj is None:
                if get_lightweight_obj:
                    return None, None
                else:
                    return None
            else:
                if get_lightweight_obj:
                    return best_obj.get(self.sig_names, best_ol_startts, best_ol_stopts, self.data_manager,
                                        self.bus_name), best_obj
                else:
                    return best_obj.get(self.sig_names, best_ol_startts, best_ol_stopts, self.data_manager,
                                        self.bus_name)
        # return all
        else:
            return ret_objects


class GenObj(object):
    """
    Lightweight Generic Object, contains only indexes, instead of complete signal values
    """
    def __init__(self, oid, global_oid, index, startts, stopts):
        """
        :param oid: oid index from bsig file
        :param global_oid: global oid from signal extractor
        :param index: index in the object list from signal extractor
        :param startts: startts
        :param stopts: stopts
        """
        self.oid = oid
        self.global_oid = global_oid
        self.startts = startts
        self.stopts = stopts
        self.index = index

    def get(self, signals, startts, stopts, data_manager, bus):
        """
        gets a GenericRectObject with Signals

        :param signals: signal names
        :param startts: startts
        :param stopts: stopts
        :param data_manager: data_manager
        :param bus: bus name
        """
        return GenericRectObject(self.global_oid, self.oid, startts, stopts, data_manager, bus, signals)

    def get_ts_distx_disty_velx(self, data_manager, bus_name):
        """
        gets a distx, disty, velx for the object from the Signal Extractor dict
        :param data_manager: data_manager
        :param bus_name: bus_name
        """
        objects = data_manager.GetDataPort(OBJECT_PORT_NAME, bus_name)
        myobj = objects[self.index]
        if myobj is not None:
            return myobj[OBJ_TIME_STAMPS], myobj[OBJ_DISTX], myobj[OBJ_DISTY], myobj[OBJ_VELX]


class GenericObjectList(BaseObjectList):
    """
    Generic object list loaded from a binary file
    """
    def __init__(self, data_source, sensor, list_name, object_filter_if,
                 bus="Bus#1", signal_names=None, objects=None):
        """
        :param data_source: data_manager initialized with binary data.
                            must have e.g. GetDataPort("objects" , "Bus#1")
        :param sensor: name of the sensor
        :param list_name: name of the list
        :param object_filter_if: ObjectFilterIf, e.g. ObjectByGateFilter
        :param bus: bus pertaining to DataManager GetDataPort
        :param signal_names: list of names of signals to be loaded,
                             default is GENERIC_OBJECT_SIGNAL_NAMES
        """
        if signal_names is None:
            signal_names = GENERIC_OBJECT_SIGNAL_NAMES

        BaseObjectList.__init__(self, data_source, sensor,
                                list_name, object_filter_if, signal_names)

        self._logger = Logger(self.__class__.__name__, level=INFO)

        if objects is None:
            self._objects = []
        else:
            self._objects = objects

        self.__bus = bus

    @staticmethod
    def __load_needed(ref_startts, ref_stopts, my_startts, my_stopts):
        """
        if there is an overlap between reference and candidate object time intervals

        :param ref_startts: reference startts
        :type ref_stopts: reference stopts
        :param my_startts: my startts
        :type my_stopts: my stopts
        """
        if ref_startts is None and ref_stopts is None:
            return True
        elif ref_startts is not None and ref_stopts is None:
            if my_stopts >= ref_startts:
                return True
            else:
                return False
        elif ref_startts is None and ref_stopts is not None:
            if my_startts <= ref_stopts:
                return True
            else:
                return False
        else:  # ref_startts is not None and ref_stopts is not None:
            if my_startts <= ref_stopts and my_stopts >= ref_startts:
                return True
            else:
                return False

    def load_objects(self, startts=None, stopts=None, ignore_error=False):
        """
        LoadObjects into GenericObjectList. It may raise AdasObjectLoadError

        :param startts: absolute start time stamp
        :type startts: long
        :param stopts: absolute stop time stamp
        :type stopts: long
        :param ignore_error: TODO
        :type ignore_error: TODO
        """
        # clear objects:
        del self._objects[:]
        self._objects = []

        # get objects
        objects = self._data_source.GetDataPort(OBJECT_PORT_NAME, self.__bus)

        if objects is None:
            raise AdasObjectLoadError("Binary file query returned None")

        for obj_dict in objects:
            try:
                my_startts = obj_dict[OBJ_TIME_STAMPS][0]
                my_stopts = obj_dict[OBJ_TIME_STAMPS][-1]
                if self.__load_needed(startts, stopts, my_startts, my_stopts):
                    self._objects.append(GenericRectObject(obj_dict[OBJ_GLOBAL_ID],
                                                           obj_dict[OBJ_OBJECT_ID],
                                                           startts,
                                                           stopts,
                                                           self._data_source,
                                                           self.__bus,
                                                           self._signal_names,
                                                           None,
                                                           ignore_error,
                                                           obj_dict))
            except AdasObjectLoadError, ex:
                msg = "Object %s could not be loaded from binary. EX:" % str(obj_dict[OBJ_GLOBAL_ID])
                msg += str(ex)
                self._logger.error(msg)

        return True

    @deprecated('load_objects')
    def LoadObjects(self, startts=None, stopts=None, ignore_error=False):  # pylint: disable=C0103
        """
        :deprecated: use `load_objects` instead
        """
        return self.load_objects(startts, stopts, ignore_error)


class GenericRectObject(BaseAdasObject):
    """
    Generic rectangular object from a binary file
    """
    def __init__(self, global_obj_id, obj_id, startts, stopts, data_source, bus,
                 signal_names=None, signals=None,
                 ignore_error=False, obj=None):
        """
        Constructor creating a rectangular object either from data_source
        or from signals if specified

        :param global_obj_id: global object id from bin file
        :param obj_id: object id from bin file
        :param startts: absolute start time stamp
        :type startts: long
        :param stopts: absolute stop time stamp
        :type stopts: long
        :param data_source: dictionary from the bin file containing data
        :type data_source: DataManager
        :param bus: bus pertaining to DataManager GetDataPort
        for one single obj, e.g. [{'Index': 2, 'VrelX': [-37.20 etc.
        :param signal_names: list of names of signals, default is GENERIC_OBJECT_SIGNAL_NAMES
        :param signals: if this is specified, signals are directly filled with it; data source is not used for filling
        :param obj: Raw object data as dict, as put on the bus by classic signal extractor
        """
        if signal_names is None:
            signal_names = GENERIC_OBJECT_SIGNAL_NAMES
        BaseAdasObject.__init__(self, global_obj_id, data_source, signal_names)
        self.__ignore_error = ignore_error
        self.__obj_id = obj_id
        self.__bus = bus
        self._logger = Logger(self.__class__.__name__)
        if signals is not None:
            self._signals = signals
        else:
            self.__fill_object_data(global_obj_id, startts, stopts, bus, obj)

    def get_subset(self, startts=None, stopts=None):
        """
        Makes a subset of the signals within the time interval

        :param startts: start time stamp
        :param stopts: stop time stamp
        """
        return GenericRectObject(self.get_id(), self.__obj_id, startts, stopts,
                                 self._data_source, self.__bus,
                                 self._signal_names,
                                 self._get_subset_of_signals(startts, stopts))

    def get_object_id(self):
        """
        Get Object Id
        """
        return self.__obj_id

    def __fill_object_data(self, obj_id, startts, stopts, bus, obj=None):
        """Fills in signals from bin file within the time interval
        :param obj_id: object id
        :param startts: start time slot
        :param stopts: stop time slot
        :param bus: name of the bus
        """

        self._signals = {}
        if obj:
            # Used when loaded through signal extractor gen obj loader
            myobj = obj
        else:
            objects = self._data_source.GetDataPort(OBJECT_PORT_NAME, bus)
            myobj = None
            for obj in objects:
                if obj[OBJ_GLOBAL_ID] == obj_id:
                    myobj = obj
                    break
        if myobj is None:
            raise AdasObjectLoadError("Binary file does not contain object id")
        tstamp = myobj[OBJ_TIME_STAMPS]

        for sig in self._signal_names:
            if sig in myobj:
                sig_vec = myobj[sig]
                time_stamp = tstamp
                if self.__ignore_error:
                    if len(sig_vec) != len(tstamp):
                        self._logger.error("Fixing signal: " + sig +
                                           " length of timestamp vector: " +
                                           str(len(tstamp)) +
                                           " length of signal value vector: " +
                                           str(len(sig_vec)))
                        min_length = min(len(tstamp), len(sig_vec))
                        sig_vec = sig_vec[0:min_length]
                        time_stamp = tstamp[0:min_length]
                        self._logger.error("Fixed signal: " + sig +
                                           " length of timestamp vector: " + str(len(time_stamp)) +
                                           " length of signal value vector: " + str(len(sig_vec)))

                if time_stamp is not None and sig_vec is not None and len(sig_vec) == len(time_stamp):
                    complete_signal = Signal(sig, None, sig_vec, time_stamp, min(sig_vec), max(sig_vec))
                    self._signals[sig] = complete_signal.GetSubsetForTimeInterval(startts, stopts)
                else:
                    self._logger.error("Signal: " + sig +
                                       " length of timestamp vector: " + str(len(time_stamp)) +
                                       " length of signal value vector: " + str(len(sig_vec)))
                    raise AdasObjectLoadError("Length of signal values and time_stamp is not equal")
            else:
                raise AdasObjectLoadError("Required Signal" + sig + " not found. Please check the configuration")

        return True

    @deprecated('get_subset')
    def GetSubset(self, startts=None, stopts=None):  # pylint: disable=C0103
        """
        :deprecated: use `get_subset` instead
        """
        return self.get_subset(startts, stopts)

    @deprecated('get_object_id')
    def GetObjectId(self):  # pylint: disable=C0103
        """
        :deprecated: use `get_object_id` instead
        """
        return self.get_object_id()

    @deprecated('__fill_object_data')
    def __FillObjectData(self, obj_id, startts, stopts, bus, obj=None):  # pylint: disable=C0103
        """
        :deprecated: use `__fill_object_data` instead
        """
        return self.__fill_object_data(obj_id, startts, stopts, bus, obj)


"""
$Log: generic_objects.py  $
Revision 1.5 2015/12/07 13:30:58CET Mertens, Sven (uidv7805) 
removing last pep8 errors
Revision 1.4 2015/12/07 11:30:18CET Mertens, Sven (uidv7805)
fix for some pep8 errors
Revision 1.3 2015/10/08 17:32:16CEST Hospes, Gerd-Joachim (uidv8815)
fix get_best_tracked_object as provided by P.Dintzer
- Added comments -  uidv8815 [Oct 8, 2015 5:32:17 PM CEST]
Change Package : 380885:1 http://mks-psad:7002/im/viewissue?selection=380885
Revision 1.2 2015/05/13 16:11:25CEST Hospes, Gerd-Joachim (uidv8815)
fix Logger initialisation problem, allow modul test to crash to show error
--- Added comments ---  uidv8815 [May 13, 2015 4:11:26 PM CEST]
Change Package : 338345:1 http://mks-psad:7002/im/viewissue?selection=338345
Revision 1.1 2015/04/23 19:04:48CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/obj/project.pj
Revision 1.26 2015/03/19 17:02:47CET Mertens, Sven (uidv7805)
moving log to logger
--- Added comments ---  uidv7805 [Mar 19, 2015 5:02:48 PM CET]
Change Package : 318794:1 http://mks-psad:7002/im/viewissue?selection=318794
Revision 1.25 2015/02/06 16:45:36CET Ellero, Stefano (uidw8660)
No deprecated functions/methods of package obj must be used inside all STK and its module tests.
--- Added comments ---  uidw8660 [Feb 6, 2015 4:45:36 PM CET]
Change Package : 301801:1 http://mks-psad:7002/im/viewissue?selection=301801
Revision 1.24 2015/02/03 18:55:39CET Ellero, Stefano (uidw8660)
No deprecated functions/methods of package obj must be used inside all STK and its module tests.
--- Added comments ---  uidw8660 [Feb 3, 2015 6:55:39 PM CET]
Change Package : 301801:1 http://mks-psad:7002/im/viewissue?selection=301801
Revision 1.23 2015/01/22 10:31:50CET Mertens, Sven (uidv7805)
minor update to pylint
--- Added comments ---  uidv7805 [Jan 22, 2015 10:31:51 AM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.22 2014/11/21 13:49:01CET Hospes, Gerd-Joachim (uidv8815)
timestamp interpolation used for all objects (not only ADMA),
new signal definition
--- Added comments ---  uidv8815 [Nov 21, 2014 1:49:02 PM CET]
Change Package : 283590:1 http://mks-psad:7002/im/viewissue?selection=283590
Revision 1.21 2014/11/06 14:28:04CET Mertens, Sven (uidv7805)
object update
--- Added comments ---  uidv7805 [Nov 6, 2014 2:28:05 PM CET]
Change Package : 278229:1 http://mks-psad:7002/im/viewissue?selection=278229
Revision 1.20 2014/09/26 12:59:20CEST Hecker, Robert (heckerr)
.
--- Added comments ---  heckerr [Sep 26, 2014 12:59:20 PM CEST]
Change Package : 267232:1 http://mks-psad:7002/im/viewissue?selection=267232
Revision 1.19 2014/09/17 08:31:42CEST Hecker, Robert (heckerr)
Small Update from Miklos.
Revision 1.18 2014/09/09 16:13:49CEST Hecker, Robert (heckerr)
Get BugFix from Jan-Hugo (Miklos)
--- Added comments ---  heckerr [Sep 9, 2014 4:13:49 PM CEST]
Change Package : 262924:1 http://mks-psad:7002/im/viewissue?selection=262924
Revision 1.17 2014/09/09 16:07:35CEST Hecker, Robert (heckerr)
Updates from Miklos.
--- Added comments ---  heckerr [Sep 9, 2014 4:07:36 PM CEST]
Change Package : 262924:1 http://mks-psad:7002/im/viewissue?selection=262924
Revision 1.16 2014/09/09 14:54:21CEST Hecker, Robert (heckerr)
New Updates from Miklos.
--- Added comments ---  heckerr [Sep 9, 2014 2:54:22 PM CEST]
Change Package : 262897:1 http://mks-psad:7002/im/viewissue?selection=262897
Revision 1.15 2014/08/14 14:46:13CEST Hospes, Gerd-Joachim (uidv8815)
changes by Miklos Sandor for faster object detection (>50 times)
--- Added comments ---  uidv8815 [Aug 14, 2014 2:46:13 PM CEST]
Change Package : 253112:2 http://mks-psad:7002/im/viewissue?selection=253112
Revision 1.14 2014/08/12 09:16:09CEST Sandor-EXT, Miklos (uidg3354)
fast matching with GenObjList::get_best_tracked_object(). to be checked
--- Added comments ---  uidg3354 [Aug 12, 2014 9:16:09 AM CEST]
Change Package : 233779:1 http://mks-psad:7002/im/viewissue?selection=233779
Revision 1.13 2014/08/08 15:23:57CEST Sandor-EXT, Miklos (uidg3354)
to be checked yet!
--- Added comments ---  uidg3354 [Aug 8, 2014 3:23:57 PM CEST]
Change Package : 233779:1 http://mks-psad:7002/im/viewissue?selection=233779
Revision 1.12 2014/07/29 18:25:35CEST Hospes, Gerd-Joachim (uidv8815)
fix pylint error W0102 and some others
--- Added comments ---  uidv8815 [Jul 29, 2014 6:25:35 PM CEST]
Change Package : 250927:1 http://mks-psad:7002/im/viewissue?selection=250927
Revision 1.11 2014/07/25 13:23:22CEST Hecker, Robert (heckerr)
Added the needed modifications form Miklos.
--- Added comments ---  heckerr [Jul 25, 2014 1:23:22 PM CEST]
Change Package : 251715:1 http://mks-psad:7002/im/viewissue?selection=251715
Revision 1.10 2014/07/24 16:43:43CEST Hecker, Robert (heckerr)
BugFix in default Argument.
Revision 1.9 2014/07/04 10:30:50CEST Baust, Philipp (uidg5548)
Fix: Wrong length for object lifetimes
Fix: Wrong obj separation, when using eObjMaintenanceState
Feature: Objects as GenericObjectList
--- Added comments ---  uidg5548 [Jul 4, 2014 10:30:50 AM CEST]
Change Package : 235081:1 http://mks-psad:7002/im/viewissue?selection=235081
Revision 1.8 2014/07/03 13:08:26CEST Hecker, Robert (heckerr)
Get needed updates from Miklos.
--- Added comments ---  heckerr [Jul 3, 2014 1:08:27 PM CEST]
Change Package : 244732:1 http://mks-psad:7002/im/viewissue?selection=244732
Revision 1.7 2014/04/30 16:58:07CEST Hecker, Robert (heckerr)
reduced pep8.
--- Added comments ---  heckerr [Apr 30, 2014 4:58:07 PM CEST]
Change Package : 233703:1 http://mks-psad:7002/im/viewissue?selection=233703
Revision 1.6 2014/04/29 10:26:30CEST Hecker, Robert (heckerr)
updated to new guidelines.
Revision 1.5 2014/04/25 09:26:31CEST Hecker, Robert (heckerr)
updated needed files for Miklos.
--- Added comments ---  heckerr [Apr 25, 2014 9:26:31 AM CEST]
Change Package : 233045:1 http://mks-psad:7002/im/viewissue?selection=233045
Revision 1.4 2014/02/21 17:17:25CET Sandor-EXT, Miklos (uidg3354)
write to DB updates
--- Added comments ---  uidg3354 [Feb 21, 2014 5:17:26 PM CET]
Change Package : 208827:2 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.3 2014/01/29 16:09:42CET Sandor-EXT, Miklos (uidg3354)
signal_names to be extracted added
--- Added comments ---  uidg3354 [Jan 29, 2014 4:09:42 PM CET]
Change Package : 208827:2 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.2 2014/01/24 10:52:17CET Sandor-EXT, Miklos (uidg3354)
global obj id added
--- Added comments ---  uidg3354 [Jan 24, 2014 10:52:18 AM CET]
Change Package : 208827:2 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.1 2013/12/16 13:21:25CET Sandor-EXT, Miklos (uidg3354)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm
/STK_ScriptingToolKit/04_Engineering/stk/obj/project.pj
"""
