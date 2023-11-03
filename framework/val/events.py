"""
framework/val/events.py
-----------------

 Subpackage for Handling Events Class and States

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 09:24:00CEST $
"""
# pylint: disable=R0914
# - import Python modules ---------------------------------------------------------------------------------------------
from os import path

# - import framework modules ------------------------------------------------------------------------------------------------
from framework.val.result_types import ValSaveLoadLevel
from framework.valf import PluginManager
from framework.val.base_events import ValBaseEvent, ValEventError
from framework.util.helper import list_folders
from framework.util.logger import Logger

# - defines -----------------------------------------------------------------------------------------------------------
HEAD_DIR = path.abspath(path.join(path.dirname(path.split(__file__)[0]), ".."))
EVENT_PLUGIN_FOLDER_LIST = []

for folder_path in list_folders(HEAD_DIR):
    EVENT_PLUGIN_FOLDER_LIST.append(folder_path)


# - classes -----------------------------------------------------------------------------------------------------------
class ValEventList(object):
    """
    ValEventLoader Class - loads Event details from Database
    """
    def __init__(self, plugin_folder_list=None, ev_filter=None):
        """class for loading events form database

        :param plugin_folder_list: list of Plugin folders i.e. location where event class definition are located.
                               If folders are not provided or definition were not found by plugin manager
                               then typed class will be generated runtime inherited from `ValBaseEvent`.
                               **Pass this argument only if you have defined additional method.**
        :type plugin_folder_list: list
        :param ev_filter: Instance of Event Filter
        :type ev_filter: `ValEventFilter`
        """
        self._log = Logger(self.__class__.__name__)

        if plugin_folder_list is not None:
            self.__plugin_folders = plugin_folder_list
        else:
            self.__plugin_folders = None  # EVENT_PLUGIN_FOLDER_LIST
        self.__plugin_manager = None
        self.__event_types_list = None
        self.__event_list = []
        self.__event_inst_created = []
        self.__filter = ev_filter

    def __del__(self):
        """clean up
        """
        self.__event_list = []

    def _init_event_types(self, plugin_folders=None):
        """ Init the Plugin """
        new_plugin = False

        if plugin_folders is not None:
            new_plugin = True
            self.__plugin_folders = plugin_folders
        if self.__plugin_manager is None or new_plugin:
            if self.__plugin_folders is not None:
                self.__plugin_manager = PluginManager(self.__plugin_folders, ValBaseEvent)

        if self.__event_types_list is None and self.__plugin_folders is not None:
            self.__event_types_list = self.__plugin_manager.get_plugin_class_list(remove_duplicates=True)
        else:
            self.__event_types_list = []

    # noinspection PyUnusedLocal
    def load(self, dbi_val, dbi_gbl, testrun_id, coll_id=None, meas_id=None,  # pylint: disable=C0103
             rd_id=None, obs_name=None, level=ValSaveLoadLevel.VAL_DB_LEVEL_BASIC,
             beginabsts=None, endabsts=None, asmt_state=None, filter_cond=None, plugin_folders=None, cons_key=None):
        """
        Load Events

        :param dbi_val: Validation Result Database interface
        :type dbi_val: `OracleValResDB` or `SQLite3ValResDB`
        :param dbi_gbl: Validation Global Database interface
        :type dbi_gbl: `OracleGblDB` or `SQLite3GblDB`
        :param testrun_id: Testrun Id as mandatory field
        :type testrun_id: Integer
        :param coll_id:  Not Used. It is useless to pass any values. This information is taken
                        from database using rd_id
        :type coll_id: Integer
        :param meas_id: Measurement Id load event only for specific recording
        :type meas_id: Integer
        :param rd_id: Result Descriptor Id as mandatory field
        :type rd_id: Integer or List
        :param obs_name: Not Used. It is useless to pass any values.
                        This information is taken from database with testrun_id
        :type obs_name: String
        :param level: Load Level to specify to which level the event data should be level
                      with following possibilities::

                        VAL_DB_LEVEL_STRUCT = Events
                        VAL_DB_LEVEL_BASIC = Events + Assessment
                        VAL_DB_LEVEL_INFO = Events + Assessment + Attribute
                        VAL_DB_LEVEL_ALL = Events + Assessment + Attribute + Image

        :type level: `ValSaveLoadLevel`
        :param beginabsts: Basic filter. Begin Absolute Time stamp i.e. Start of the events
        :type beginabsts: Integer
        :param endabsts: End Absolute Time stamp i.e. End of the events
        :type endabsts: Integer
        :param asmt_state: Assessment State
        :type asmt_state: String
        :param filter_cond: Advance filter feature which can filter events based on event attributes;
                            filter map name specified in XML config file of custom filters.
                            Please read documentation of `ValEventFilter` for more detail
        :param plugin_folders: The value passed in constructor overrules. It is useless to pass value
        :type plugin_folders: list
        :param cons_key: Constrain Key. Not used
        :type cons_key: NoneType
        """
        _ = coll_id
        _ = obs_name
        _ = asmt_state
        _ = plugin_folders
        _ = cons_key

        inc_asmt = False
        inc_attrib = False
        inc_images = False
        self.__event_list = []
        self.__event_inst_created = []
        unit_map = {}

        statement = None
        if filter_cond is not None:
            if self.__filter is not None:
                statement = self.__filter.load(dbi_val, filtermap_name=filter_cond)
                if statement is None:
                    self._log.error("The map filter was invalid. Events will be loaded without filter")
                elif type(statement) is list:
                    self._log.debug("The map filter was found. Events will be loaded with filter")

        if rd_id is not None:
            rd_list = dbi_val.get_resuls_descriptor_child_list(rd_id)
            if len(rd_list) == 0:
                rd_list = [rd_id]
        else:
            return True

        if level == ValSaveLoadLevel.VAL_DB_LEVEL_2:
            inc_asmt = True

        if level == ValSaveLoadLevel.VAL_DB_LEVEL_4:
            inc_images = True

        records, image_attribs = dbi_val.get_event_for_testrun(testrun_id, measid=meas_id, beginabsts=beginabsts,
                                                               endabsts=endabsts, rdid=rd_list, cond=None,
                                                               filt_stat=statement,
                                                               inc_asmt=inc_asmt, inc_attrib=inc_attrib,
                                                               inc_images=inc_images)
        col_list = records[0]
        records = records[1]
        self.__event_inst_created = {}
        self._init_event_types()

        self.__event_inst_created = {}
        return True

    def save(self, dbi_val, dbi_gbl, testrun_id, coll_id, obs_name=None, parent_id=None,  # pylint: disable=C0103
             level=ValSaveLoadLevel.VAL_DB_LEVEL_BASIC, cons_key=None):
        """
        Save Events

        :param dbi_val: Validation Result Database interface
        :type dbi_val: `OracleValResDB` or `SQLite3ValResDB`
        :param dbi_gbl: Validation Global Database interface
        :type dbi_gbl: `OracleGblDB` or `SQLite3GblDB`
        :param testrun_id: Testrun Id
        :type testrun_id: Integer
        :param coll_id: Collection ID
        :type coll_id: Integer
        :param obs_name: Observer Name registered in Global Database
        :type obs_name: String
        :param parent_id: Parent Result Descriptor Id
        :type parent_id: Integer
        :param level: Save level::

                            - VAL_DB_LEVEL_STRUCT: Result Descriptor only,
                            - VAL_DB_LEVEL_BASIC: Result Descriptor and result,
                            - VAL_DB_LEVEL_INFO: Result Descriptor, Result and Assessment
                            - VAL_DB_LEVEL_ALL: Result with images and all messages

        :param cons_key: constraint key -- for future use
        :type cons_key: NoneType
        """
        res = False

        if dbi_val.get_testrun_lock(tr_id=testrun_id) == 1:
            self._log.error("No Event is saved due to locked testrun ")
            return res
        for evt in self.__event_list:
            try:
                res = evt.save(dbi_val, dbi_gbl, testrun_id, coll_id, evt.get_meas_id(),
                               obs_name, parent_id, level, cons_key)
            except ValEventError, ex:
                self._log.warning("Events %s could not be stored. See details: %s " % (str(evt), ex))
                res = False

            if res is False:
                break

        if res is True:
            pass
            # dbi_val.commit()
            # dbi_gbl.commit()

        return res

    def add_event(self, event):  # pylint: disable=C0103
        """
        Add a new event to the events list

        :param event: Event Object
        :type event: Child of `ValBaseEvent`
        """
        if issubclass(event.__class__, ValBaseEvent):
            self.__event_list.append(event)

    def get_events(self):  # pylint: disable=C0103
        """
        Get the loaded event list
        """
        return self.__event_list


"""
CHANGE LOG:
-----------
$Log: events.py  $
Revision 1.2 2020/03/31 09:24:00CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:34:07CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/val/project.pj
"""
