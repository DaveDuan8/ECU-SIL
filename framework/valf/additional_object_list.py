"""
framework/valf/additional_object_list.py
----------------------------------

Extends SignalExtractor object list section with an additional object list: 62 element list with 100 element list
The mapping of the object list indexes is specified as attribute

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 10:14:08CEST $
"""
# =====================================================================================================================
# Imports
# =====================================================================================================================

from framework.util.logger import Logger

# =====================================================================================================================
# Global Definitions
# =====================================================================================================================
# same values as in signal extractor!
PORT_NAME = "PortName"
SIGNAL_NAME = "SignalName"


# =====================================================================================================================
# Classes
# =====================================================================================================================
class AdditionalObjectList(object):
    """
    AdditionalObjectList maps a smaller object list to a larger one, e.g.:

    OBJ_signals: EmGenObjectList (62 elements) -> AOJ_signals: EMPublicObjData (100 elements)

    via a mapping signal AOJ_mapping: ``SIM VFB ALL.DataProcCycle.EmGenObjectList.aObject[%].General.uiID``
    ``EmGenObjectList.aObject[3].General.uiID = 17 -> EMPublicObjData.Objects[17].Private.u_RadarBasisClassInternal``

    the output port is same as for OBJList:
    ``objects = self._data_manager.GetDataPort(OBJECT_PORT_NAME, self.bus_name)``

    Config file example::

           ("OBJ_min_lifetime",        50),
           ("OBJ_number_of_objects",  62),
           ("OOI_number_of_objects",   6),
           ("AOJ_list_size", 100), <--- mandatory
           ("AOJ_mapping", "SIM VFB ALL.DataProcCycle.EmGenObjectList.aObject[%].General.uiID"), <--- mandatory
           ("OBJ_prefix",                 ""),
           ("AOJ_prefix",             ""), <--- optional (needs not be necessarily present in the config, if yes,
                                                    the prefix is added to AOJ_mapping and AOJ_signals)
           ("OBJ_signals", [
           {'SignalName':"SIM VFB ALL.DataProcCycle.EmGenObjectList.aObject[%].General.eMaintenanceState",
           'PortName':'eObjMaintenanceState'},
           {'SignalName':"SIM VFB ALL.DataProcCycle.EmGenObjectList.aObject[%].Kinematic.fDistX",
           'PortName':'DistX'}]),
           ("AOJ_signals", [
           {'SignalName':"SIM VFB ALL.DataProcCycle.EMPublicObjData.Objects[%].Private.u_RadarBasisClassInternal",
           'PortName':'Object_RadarBasisClass'}])
    """
    AOJ_INIT_ERROR = 'mandatory init parameters of AdditionalObjectList are None'

    def __init__(self, sig_read, add_obj_mapping_rule, add_obj_port_and_signal_names, add_obj_list_size,
                 add_obj_prefix):
        """init

        :param sig_read: former binary signal reader, not needed anymore
        :type  sig_read: None
        :param add_obj_mapping_rule: AOJ_mapping signal name
        :type  add_obj_mapping_rule: string
        :param add_obj_port_and_signal_names: AOJ_signals
        :type  add_obj_port_and_signal_names: list of strings
        :param add_obj_list_size: AOJ_list_size
        :type  add_obj_list_size: integer
        :param add_obj_prefix: AOJ_prefix for signal and mapping name
        :type  add_obj_prefix: string
        """
        if (add_obj_mapping_rule is None or add_obj_port_and_signal_names is None or
                add_obj_list_size is None):
            raise ValueError(AdditionalObjectList.AOJ_INIT_ERROR)
        self.__sig_read = sig_read
        self.__add_obj_port_and_signal_names = add_obj_port_and_signal_names
        self.__add_obj_mapping_rule = add_obj_mapping_rule
        self.__add_obj_list_size = add_obj_list_size
        if add_obj_prefix is None:
            self.__add_obj_prefix = ""
        else:
            self.__add_obj_prefix = add_obj_prefix.strip()
        # my object list
        self.__my_object_index = None
        self.__mapping_signal = None
        # all obj cache
        self.__object_list = {}
        self.__log = Logger(self.__class__.__name__)

    def clear_cache(self):
        """
        call this in SignalExtractor when the file has been already processed e.g. in PostProcessData
        """
        self.__my_object_index = None
        if self.__mapping_signal is not None:
            del self.__mapping_signal
            self.__mapping_signal = None
        if self.__object_list is not None:
            del self.__object_list
            self.__object_list = {}

    def __get_other_obj(self, object_index):
        """
        Builds an on demand cache with all signals of the object with the given index. All addressed objects are kept.

        :param object_index: object index
        """
        ret_obj = self.__object_list.get(object_index)
        if ret_obj is not None:
            return ret_obj
        else:
            new_obj = {}
            for list_item in self.__add_obj_port_and_signal_names:
                signal_name = self.__add_obj_prefix + list_item[SIGNAL_NAME].replace('%', str(object_index))
                port_name = list_item[PORT_NAME]
                new_obj[port_name] = self.__sig_read[signal_name]
            self.__object_list[object_index] = new_obj
            return new_obj

    def __get_mapping_signal(self, object_index):
        """
        Builds an on demand cache with the mapping signal of the object with the given index.

        New index deletes previous signal.

        :param object_index: object index
        """
        if self.__my_object_index is None:
            # mapping:
            mapping_signal_name = self.__add_obj_prefix + self.__add_obj_mapping_rule.replace('%', str(object_index))
            self.__mapping_signal = self.__sig_read[mapping_signal_name]
            self.__my_object_index = object_index
        elif self.__my_object_index != object_index:
            del self.__mapping_signal[:]
            mapping_signal_name = self.__add_obj_mapping_rule.replace('%', str(object_index))
            self.__mapping_signal = self.__sig_read[mapping_signal_name]
            self.__my_object_index = object_index
        else:
            # self.__my_object_index == object_index
            pass
        return self.__mapping_signal

    def add_additional_object_signals(self, new_obj, object_index, start_position, end_position, sig_read):
        """
        Builds an on demand cache with the mapping signal of the object with the given index.

        New index deletes previous signal.

        :param new_obj: object represented as a dictionary of list (see SignalExtractor). key is port of sig name,
                        **it extends the passed object new_obj with the other list's signals**
        :type  new_obj: dict
        :param object_index: current object index
        :type  object_index: integer
        :param start_position: start position in the meas file (cycle)
        :type  start_position: integer
        :param end_position: end position in the meas file (cycle)
        :type  end_position: integer
        :param sig_read: signal reader instance to extract a signal
        :type  sig_read: SignalReader
        :return: success (means: mapping object found, otherwise do not use 'new_obj' in signal extractor)
        :rtype:  boolean
        """
        if sig_read is None:
            raise ValueError(AdditionalObjectList.AOJ_INIT_ERROR)
        self.__sig_read = sig_read
        ret_success = False
        mapping_signal = self.__get_mapping_signal(object_index)
        # mapping assumes that the corresponding object id pointing to the other object list
        # is constant between start and end:
        idx_larger_list = mapping_signal[start_position] if mapping_signal is not None else -1
        if 0 <= idx_larger_list < self.__add_obj_list_size:
            self.__log.debug("MYOID: " + str(object_index) + " OOID: " + str(idx_larger_list) + " START: " +
                             str(start_position) + " END: " + str(end_position))
            other_obj = self.__get_other_obj(idx_larger_list)
            for sig_name, sig_val in other_obj.iteritems():
                new_obj[sig_name] = sig_val[start_position:end_position]
            ret_success = True
        else:
            self.__log.warning("obj idx: " + str(object_index) + " pos: " + str(start_position) + '..' +
                               str(end_position) + " index: " + str(mapping_signal[start_position]) +
                               " is out of range [0.." + str(self.__add_obj_list_size - 1) + "]: " +
                               ", obj period will be omitted")
        return ret_success


"""
CHANGE LOG:
-----------
 $Log: additional_object_list.py  $
 Revision 1.2 2020/03/31 10:14:08CEST Leidenberger, Ralf (uidq7596) 
 initial update
 Revision 1.1 2020/03/25 21:38:05CET Leidenberger, Ralf (uidq7596) 
 Initial revision
 Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/valf/project.pj
"""
