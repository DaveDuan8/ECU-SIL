"""
stk/val/events.py
-----------------

 Subpackage for Handling Events Class and States

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.8 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/02/05 18:25:08CET $
"""
# pylint: disable=R0914
# - import Python modules ---------------------------------------------------------------------------------------------
from os import path

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.db.val.val import COL_NAME_EVENTS_MEASID, COL_NAME_EVENTS_RESASSID, COL_NAME_ASS_USER_ID, \
    COL_NAME_ASS_COMMENT, COL_NAME_ASS_DATE, COL_NAME_ASS_TRACKING_ID, COL_NAME_EVENT_IMG_IMAGE, \
    COL_NAME_EVENT_ATTR_TYPES_UNITID, COL_NAME_EVENTS_SEID, COL_NAME_EVENTS_VIEW_CLASSNAME, \
    COL_NAME_EVENT_ATTR_ATTRID, COL_NAME_EVENTS_VIEW_BEGINABSTS, COL_NAME_EVENTS_VIEW_START_IDX, \
    COL_NAME_EVENTS_VIEW_ENDABSTS, COL_NAME_EVENTS_VIEW_STOP_IDX, COL_NAME_EVENT_ATTR_VALUE, \
    COL_NAME_EVENT_ATTR_TYPES_NAME

from stk.db.gbl.gbl import COL_NAME_UNIT_NAME, COL_NAME_UNIT_ID, COL_NAME_WORKFLOW_NAME, COL_NAME_ASSESSMENT_STATE_NAME
from stk.val.asmt import ValAssessment
from stk.val.result_types import ValSaveLoadLevel
from stk.valf import PluginManager
from stk.val.base_events import ValBaseEvent, ValEventError
from stk.util.helper import list_folders
from stk.util.logger import Logger

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

    def Load(self, dbi_val, dbi_gbl, testrun_id, coll_id=None, meas_id=None,  # pylint: disable=C0103
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
                statement = self.__filter.Load(dbi_val, filtermap_name=filter_cond)
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

        if level & ValSaveLoadLevel.VAL_DB_LEVEL_2:
            inc_asmt = True

        if level & ValSaveLoadLevel.VAL_DB_LEVEL_3:
            inc_attrib = True
            unit_records = dbi_gbl.get_unit()
            for unit_entry in unit_records:
                unit_map[str(unit_entry[COL_NAME_UNIT_ID])] = unit_entry[COL_NAME_UNIT_NAME]

        if level & ValSaveLoadLevel.VAL_DB_LEVEL_4:
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

        while True:
            if len(records) <= 10000:
                self._prepare_events(dbi_val, records, col_list, image_attribs, unit_map,
                                     inc_asmt=inc_asmt, inc_attrib=inc_attrib, inc_images=inc_images)
                records = []
                break
            else:
                self._prepare_events(dbi_val, records[:10000], col_list, image_attribs, unit_map,
                                     inc_asmt=inc_asmt, inc_attrib=inc_attrib, inc_images=inc_images)
                del records[:10000]

        self.__event_inst_created = {}
        return True

    def _prepare_events(self, dbi_val, records, col_list, image_attribs, unit_map,
                        inc_asmt=True, inc_attrib=True, inc_images=True):
        """
        Prepare Event Object list by taking chunks for records from database

        :param dbi_val: DB interface to Validation Database
        :type dbi_val: OracleValResDB or  SQLite3ValResDB
        :param records: List of records as list of dict
        :type records: list
        :param col_list: Column List in records
        :type col_list: list
        :param image_attribs: Event Image attribute Id
        :type image_attribs: list
        :param unit_map: Unit map of Unit Id VS Unit Name
        :type unit_map: Dict
        :param inc_asmt: Flag to include Assessment in Event. Default True
        :type inc_asmt: Bool
        :param inc_attrib: Flag to include Event Attributes. Default True
        :type inc_attrib: Bool
        :param inc_images: Flag to include Event Attribute Images. Default True
        :type inc_images: Bool
        """
        event = ValBaseEvent()  # fix pylint problem, event will be set properly later
        if len(records) > 0:
            seid_eventlistmap = self.__event_inst_created
            sed_idx = col_list.index(COL_NAME_EVENTS_SEID)
            cls_name_idx = col_list.index(COL_NAME_EVENTS_VIEW_CLASSNAME)
            begin_idx = col_list.index(COL_NAME_EVENTS_VIEW_BEGINABSTS)
            start_idx = col_list.index(COL_NAME_EVENTS_VIEW_START_IDX)
            end_idx = col_list.index(COL_NAME_EVENTS_VIEW_ENDABSTS)
            stop_idx = col_list.index(COL_NAME_EVENTS_VIEW_STOP_IDX)
            measid_idx = col_list.index(COL_NAME_EVENTS_MEASID)

            if inc_asmt:
                usr_idx = col_list.index(COL_NAME_ASS_USER_ID)
                wf_idx = col_list.index("WF" + COL_NAME_WORKFLOW_NAME)
                asmtst_idx = col_list.index("ST" + COL_NAME_ASSESSMENT_STATE_NAME)
                comm_idx = col_list.index(COL_NAME_ASS_COMMENT)
                asmt_date_idx = col_list.index(COL_NAME_ASS_DATE)
                issue_idx = col_list.index(COL_NAME_ASS_TRACKING_ID)
                resassid_idx = col_list.index(COL_NAME_EVENTS_RESASSID)
            if inc_attrib:
                unitid_idx = col_list.index(COL_NAME_EVENT_ATTR_TYPES_UNITID)
                arribid_idx = col_list.index(COL_NAME_EVENT_ATTR_ATTRID)
                atrtypeid_idx = col_list.index(COL_NAME_EVENT_ATTR_TYPES_NAME)
                value_idx = col_list.index(COL_NAME_EVENT_ATTR_VALUE)

        for record in records:
            if str(int(record[sed_idx])) not in seid_eventlistmap:

                cls = None
                for etype in self.__event_types_list:
                    if etype['name'] == record[cls_name_idx]:
                        cls = etype['type']
                        break

                if cls is None:
                    e_type = type(record[cls_name_idx], (ValBaseEvent,), {})
                    event = e_type(start_time=record[begin_idx], start_index=record[start_idx],
                                   stop_time=record[end_idx], stop_index=record[stop_idx], seid=record[sed_idx])
                else:
                    event = object.__new__(cls)
                    event.__init__(start_time=record[begin_idx], start_index=record[start_idx],
                                   stop_time=record[end_idx], stop_index=record[stop_idx], seid=record[sed_idx])

                event.SetMeasId(record[measid_idx])

                if inc_asmt:
                    asmt = ValAssessment(user_id=record[usr_idx], wf_state=record[wf_idx],
                                         ass_state=record[asmtst_idx], ass_comment=record[comm_idx],
                                         date_time=record[asmt_date_idx], issue=record[issue_idx])
                    asmt.ass_id = record[resassid_idx]
                    event.AddAssessment(asmt)

                self.__event_list.append(event)
                seid_eventlistmap[str(int(record[sed_idx]))] = len(self.__event_list) - 1

            else:
                event = self.__event_list[seid_eventlistmap[str(int(record[sed_idx]))]]

            if inc_attrib:
                if record[unitid_idx] is not None:
                    unit = unit_map[str(record[unitid_idx])]
                else:
                    unit = str(record[unitid_idx])

                if inc_images and record[arribid_idx] in image_attribs:
                    image = dbi_val.get_event_image(record[arribid_idx])[COL_NAME_EVENT_IMG_IMAGE]
                else:
                    image = None
                event.AddAttribute(record[atrtypeid_idx], value=record[value_idx], unit=unit, image=image)

    def Save(self, dbi_val, dbi_gbl, testrun_id, coll_id, obs_name=None, parent_id=None,  # pylint: disable=C0103
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
                res = evt.Save(dbi_val, dbi_gbl, testrun_id, coll_id, evt.GetMeasId(),
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

    def AddEvent(self, event):  # pylint: disable=C0103
        """
        Add a new event to the events list

        :param event: Event Object
        :type event: Child of `ValBaseEvent`
        """
        if issubclass(event.__class__, ValBaseEvent):
            self.__event_list.append(event)

    def GetEvents(self):  # pylint: disable=C0103
        """
        Get the loaded event list
        """
        return self.__event_list


"""
CHANGE LOG:
-----------
$Log: events.py  $
Revision 1.8 2016/02/05 18:25:08CET Hospes, Gerd-Joachim (uidv8815) 
rel 2.3.18
Revision 1.7 2016/02/05 11:03:38CET Hospes, Gerd-Joachim (uidv8815)
pep8/pylint fixes
Revision 1.6 2016/02/04 16:33:43CET Ahmed, Zaheer (uidu7634)
documentation improvement. plugin folder is optional in results.py for loading events
Revision 1.5 2015/10/05 13:37:20CEST Ahmed, Zaheer (uidu7634)
pep8 fixes
--- Added comments ---  uidu7634 [Oct 5, 2015 1:37:21 PM CEST]
Change Package : 376758:1 http://mks-psad:7002/im/viewissue?selection=376758
Revision 1.4 2015/10/05 12:52:39CEST Ahmed, Zaheer (uidu7634)
check if the tesrun is not locked before saving ValEventList
--- Added comments ---  uidu7634 [Oct 5, 2015 12:52:39 PM CEST]
Change Package : 376758:1 http://mks-psad:7002/im/viewissue?selection=376758
Revision 1.3 2015/05/19 12:57:46CEST Ahmed, Zaheer (uidu7634)
remove commit events are saved through testcase and commit is there
--- Added comments ---  uidu7634 [May 19, 2015 12:57:46 PM CEST]
Change Package : 338368:1 http://mks-psad:7002/im/viewissue?selection=338368
Revision 1.2 2015/05/18 14:44:07CEST Ahmed, Zaheer (uidu7634)
mem cleanup after loading event
--- Added comments ---  uidu7634 [May 18, 2015 2:44:07 PM CEST]
Change Package : 338368:1 http://mks-psad:7002/im/viewissue?selection=338368
Revision 1.1 2015/04/23 19:05:37CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/val/project.pj
Revision 1.20 2015/03/06 14:55:30CET Mertens, Sven (uidv7805)
logger change
--- Added comments ---  uidv7805 [Mar 6, 2015 2:55:32 PM CET]
Change Package : 314290:1 http://mks-psad:7002/im/viewissue?selection=314290
Revision 1.19 2015/01/20 13:37:45CET Mertens, Sven (uidv7805)
removing commit deprecation
Revision 1.18 2014/12/17 14:57:46CET Ellero, Stefano (uidw8660)
Removed all db.obj based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Dec 17, 2014 2:57:47 PM CET]
Change Package : 281278:1 http://mks-psad:7002/im/viewissue?selection=281278
Revision 1.17 2014/10/22 11:46:54CEST Ahmed, Zaheer (uidu7634)
Removed deprecated method usage
--- Added comments ---  uidu7634 [Oct 22, 2014 11:46:55 AM CEST]
Change Package : 267593:5 http://mks-psad:7002/im/viewissue?selection=267593
Revision 1.16 2014/10/17 10:59:01CEST Ahmed, Zaheer (uidu7634)
bug fix for missing attributes values in events
--- Added comments ---  uidu7634 [Oct 17, 2014 10:59:01 AM CEST]
Change Package : 267593:3 http://mks-psad:7002/im/viewissue?selection=267593
Revision 1.15 2014/10/14 16:13:33CEST Ahmed, Zaheer (uidu7634)
bug fix for loading events without rd_id
--- Added comments ---  uidu7634 [Oct 14, 2014 4:13:34 PM CEST]
Change Package : 268541:1 http://mks-psad:7002/im/viewissue?selection=268541
Revision 1.14 2014/10/14 15:25:04CEST Ahmed, Zaheer (uidu7634)
pep8 fixes
--- Added comments ---  uidu7634 [Oct 14, 2014 3:25:05 PM CEST]
Change Package : 268541:1 http://mks-psad:7002/im/viewissue?selection=268541
Revision 1.13 2014/10/14 14:47:42CEST Ahmed, Zaheer (uidu7634)
Re implemented EventList Load function to avoid using Views from database due to poor performance
with SQLite DB.
Improve epy Doc
--- Added comments ---  uidu7634 [Oct 14, 2014 2:47:43 PM CEST]
Change Package : 268541:1 http://mks-psad:7002/im/viewissue?selection=268541
Revision 1.12 2014/10/14 11:40:28CEST Hecker, Robert (heckerr)
Removed W0403 Message.
--- Added comments ---  heckerr [Oct 14, 2014 11:40:29 AM CEST]
Change Package : 271208:1 http://mks-psad:7002/im/viewissue?selection=271208
"""
