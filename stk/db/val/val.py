"""
stk/db/val/val.py
-----------------

Classes for Database access of Validation Results and Events.

Sub-Scheme VAL

**User-API**
    - `BaseValResDB`
        Providing methods to store validation results
        used for assessment, reports and export to Doors

The other classes in this module are handling the different DB types and are derived from BaseValResDB.

**usage in Valf suites**

For validation suites based on `Valf` class there is the operator `DbLinker` setting up all needed connections.

**using several connections in parallel**

If several sub-schemes have to be used in parallel the first connection should be reused.
Please check class `BaseValResDB` for more detail.

**Do not waste the limited number of connections to Oracle DB**
by setting up a new connection for each sub-scheme,
always use the existing one as described in `BaseValResDB`.

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.23 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/10/28 15:39:43CEST $
"""
# pylint: disable=R0914,R0915
# - import Python modules ---------------------------------------------------------------------------------------------
from time import time
from cx_Oracle import LOB

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.db.db_common import BaseDB, DB_FUNC_NAME_MAX, DB_FUNC_NAME_LOWER, AdasDBError, \
    ERROR_TOLERANCE_LOW, ROLE_DB_ADMIN, PluginBaseDB
from stk.db.db_sql import SQLBinaryExpr, OP_EQ, OP_IS, SQLLiteral, OP_AND, SQLFuncExpr, \
    SQLTableExpr, SQLJoinExpr, OP_INNER_JOIN, OP_OR, SQLColumnExpr, OP_LEFT_OUTER_JOIN, OP_AS, OP_IN, SQLNull, \
    OP_SUB, SQLUnaryExpr, OP_RETURNING
from stk.db.gbl.gbl import TABLE_NAME_WORKFLOW, COL_NAME_WORKFLOW_NAME, TABLE_NAME_USERS, COL_NAME_USER_LOGIN, \
    COL_NAME_ASSESSMENT_STATE_ASSID, COL_NAME_ASSESSMENT_STATE_NAME, COL_NAME_USER_ID, COL_NAME_WORKFLOW_WFID, \
    TABLE_NAME_ASSESSMENT_STATE
from stk.valf.signal_defs import DBVAL

from stk.util.helper import deprecation

# - defines -----------------------------------------------------------------------------------------------------------
# Table base names:
TABLE_NAME_TESTRUN = "VAL_Testrun"
TABLE_NAME_VRKEY = "VAL_Keys"
TABLE_NAME_VRKEY_MAP = "VAL_ConstraintsMap"
TABLE_NAME_RESULT_DESC = "VAL_ResultDescriptor"
TABLE_NAME_RESULTTYPE = "VAL_ResultTypes"
TABLE_NAME_RESULT = "VAL_Result"
TABLE_NAME_RESULT_IMAGE = "VAL_ResultImage"
TABLE_NAME_RESULT_VALUES = "VAL_ResultValues"
TABLE_NAME_RESULT_MESSAGES = "VAL_ResultMessages"
TABLE_NAME_RESULT_LABEL_MAP = "VAL_ResultLabelMap"
TABLE_NAME_HIST = "VAL_Hist"

TABLE_NAME_ROAD_EVENTS = "VAL_EnvRoadEvents"

TABLE_NAME_EVENTTYPE = "VAL_EventTypes"
TABLE_NAME_EVENTS = "VAL_Events"
TABLE_NAME_EVENT_DETAILS = "VAL_EventDetails"
TABLE_NAME_EVENT_ATTR = "VAL_EventAttr"
TABLE_NAME_EVENT_ATTR_TYPES = "VAL_EventAttrTypes"
TABLE_NAME_EVENT_IMAGE = "VAL_EventImage"

TABLE_NAME_ASSESSMENT = "VAL_Assessment"
TABLE_NAME_ASSESSMENT_ARCHIVE = "VAL_Assessment_Archive"
TABLE_NAME_EVENTS_VIEW = "VAL_View_Events"
TABLE_NAME_EVENTS_ATTRIBUTES_VIEW = "VAL_View_Events_Attributes"

TABLE_NAME_JOBS = "VAL_Jobs"
TABLE_NAME_TRUN_JOB_MAP = "VAL_Trun_JobMap"

# Testrun Table
COL_NAME_TR_ID = "TRID"
COL_NAME_TR_NAME = "NAME"
COL_NAME_TR_DESC = "DESCRIPTION"
COL_NAME_TR_START = "STARTTS"
COL_NAME_TR_END = "ENDTS"
COL_NAME_TR_CHECKPOINT = "CHECKPOINT"
COL_NAME_TR_USERID = "USERID"
COL_NAME_TR_TYPE_ID = "TYPEID"
COL_NAME_TR_PARENT = "PARENT"
COL_NAME_TR_COLL_NAME = "TESTDESIGN"
COL_NAME_TR_DELETED = "IS_DELETED"
COL_NAME_TR_TRUNLOCK = "IS_LOCKED"
COL_NAME_TR_PID = "PID"
COL_NAME_TR_CMPID = "CMPID"
COL_NAME_TR_TTID = "TTID"
COL_NAME_TR_ADD_INFO = "ADD_INFO"
COL_NAME_TR_SIM_NAME = "SIM_NAME"
COL_NAME_TR_SIM_VERSION = "SIM_VERSION"
COL_NAME_TR_VAL_SW_VERSION = "VAL_SW_VERSION"
COL_NAME_TR_REMARKS = "REMARKS"

# EventType Table
COL_NAME_EVENTTYPE_ID = "EVENTTYPEID"
COL_NAME_EVENTTYPE_NAME = "NAME"
COL_NAME_EVENTTYPE_DESC = "DESCRIPTION"
COL_NAME_EVENTTYPE_CLASSNAME = "CLASSNAME"

# Result Revision Key Table
COL_NAME_VRKEY_ID = "VAL_REV_KEY"
COL_NAME_VRKEY_NAME = "NAME"
COL_NAME_VRKEY_DESCRIPTION = "DESCRIPTION"

# Result Revision Key Mapping Table
COL_NAME_VRKEY_MAP_ID = "VAL_REV_KEY"
COL_NAME_VRKEY_MAP_RDID = "RDID"

# Result Descriptor Table
COL_NAME_RESDESC_ID = "RDID"
COL_NAME_RESDESC_NAME = "NAME"
COL_NAME_RESDESC_COLLID = "COLLID"
COL_NAME_RESDESC_RESTYPE_ID = "RESTYPEID"
COL_NAME_RESDESC_UNIT_ID = "UNITID"
COL_NAME_RESDESC_PARENT = "PARENT"
COL_NAME_RESDESC_REFTAG = "REFTAG"
COL_NAME_RESDESC_DOORS_URL = "DOORS_URL"
COL_NAME_RESDESC_EXPECTRES = "EXPECTRES"
COL_NAME_RESDESC_DESCRIPTION = "DESCRIPTION"

# ResultType Table
COL_NAME_RESULTTYPE_ID = "RESTYPEID"
COL_NAME_RESULTTYPE_NAME = "NAME"
COL_NAME_RESULTTYPE_DESC = "DESCRIPTION"
COL_NAME_RESULTTYPE_CLASS = "CLASSNAME"

# Result Table
COL_NAME_RES_ID = "RESID"
COL_NAME_RES_TESTRUN_ID = "TRID"
COL_NAME_RES_RESDESC_ID = "RDID"
COL_NAME_RES_VALUE = "VALUE"
COL_NAME_RES_MEASID = "MEASID"
COL_NAME_RES_RESASSID = "RESASSID"

# Result Image Table
COL_NAME_RESIMG_ID = "RESID"
COL_NAME_RESIMG_IMAGE = "IMAGE"
COL_NAME_RESIMG_TITLE = "TITLE"
COL_NAME_RESIMG_FORMAT = "FORMAT"

# Result Values  Table
COL_NAME_RESVAL_SUBID = "SUBID"
COL_NAME_RESVAL_ID = "RESID"
COL_NAME_RESVAL_VALUE = "VALUE"

# Result Messages  Table
COL_NAME_RESMESS_SUBID = "SUBID"
COL_NAME_RESMESS_ID = "RESID"
COL_NAME_RESMESS_MESS = "MESSAGE"


# Assessment  Table
COL_NAME_ASS_ID = "RESASSID"
COL_NAME_ASS_USER_ID = "USERID"
COL_NAME_ASS_COMMENT = "ASSCOMMENT"
COL_NAME_ASS_WFID = "WFID"
COL_NAME_ASS_DATE = "ASSDATE"
COL_NAME_ASS_ASSSTID = "ASSSTID"
COL_NAME_ASS_TRACKING_ID = "TRACKING_ID"

# Assessment_Archive Table"
COL_NAME_ASS_ARCH_ID = "RESASSID"
COL_NAME_ASS_USER_ARCH_ID = "USERID"
COL_NAME_ASS_ARCH_COMMENT = "ASSCOMMENT"
COL_NAME_ASS_ARCH_WFID = "WFID"
COL_NAME_ASS_ARCH_DATE = "ASSDATE"
COL_NAME_ASS_ARCH_ASSSTID = "ASSSTID"
COL_NAME_ASS_ARCH_TRACKING_ID = "TRACKING_ID"


# Result Label Map Table
COL_NAME_RESLB_RESID = "RESID"
COL_NAME_RESLB_LBID = "LBID"

# Road evaluation table
COL_NAME_ROAD_EVALUATION_EVALID = "EVALID"
COL_NAME_ROAD_EVALUATION_TRID = "TRID"
COL_NAME_ROAD_EVALUATION_COLLID = "COLLID"
COL_NAME_ROAD_EVALUATION_MEASID = "MEASID"
COL_NAME_ROAD_EVALUATION_AREA = "AREA"

# Road events table
COL_NAME_ROAD_EVENTS_EVENTID = "EVENTID"
COL_NAME_ROAD_EVENTS_RESID = "RESID"
COL_NAME_ROAD_EVENTS_TIMESAMPLE = "TIMESAMPLE"
COL_NAME_ROAD_EVENTS_THRESHOLD = "THRESHOLD"
COL_NAME_ROAD_EVENTS_BEGINABSTS = "BEGINABSTS"
COL_NAME_ROAD_EVENTS_ENDABSTS = "ENDABSTS"

# AccSimAtomObjEvRectObjMap Table
COL_NAME_ACC_A_OBJ_EVENT_ROM_EVRECTOBJMAPID = "EVTRECTOBJOBJMAPID"
COL_NAME_ACC_A_OBJ_EVENT_ROM_SIMATOMOBJEVID = "SIMATOMOBJEVENTID"
COL_NAME_ACC_A_OBJ_EVENT_ROM_RECTOBJID = "RECTOBJID"

# AccSimAtomicObjEvent Table
COL_NAME_ACC_A_OBJ_EVENT_ATOMEVENTDESCID = "ATOMEVENTDESCID"
COL_NAME_ACC_A_OBJ_EVENT_OBJBININDEX = "OBJBININDEX"
COL_NAME_ACC_A_OBJ_EVENT_ATOMEVENTTIMESTAMP = "ATOMEVENTTIMESTAMP"
COL_NAME_ACC_A_OBJ_EVENT_OBJEVENTID = "OBJEVENTID"
COL_NAME_ACC_A_OBJ_EVENT_EGOSPDX = "EGOSPDX"
COL_NAME_ACC_A_OBJ_EVENT_EGOACCELX = "EGOACCELX"
COL_NAME_ACC_A_OBJ_EVENT_VDYRADIUS = "VDYRADIUS"
COL_NAME_ACC_A_OBJ_EVENT_OBJACCELX = "OBJACCELX"
COL_NAME_ACC_A_OBJ_EVENT_DISTX = "DISTX"
COL_NAME_ACC_A_OBJ_EVENT_RELSPDX = "RELSPDX"
COL_NAME_ACC_A_OBJ_EVENT_DISTY = "DISTY"
COL_NAME_ACC_A_OBJ_EVENT_RELSPDY = "RELSPDY"
COL_NAME_ACC_A_OBJ_EVENT_DISTYEGOPATH = "DISTYEGOPATH"
COL_NAME_ACC_A_OBJ_EVENT_DYNPROP = "DYNPROP"
COL_NAME_ACC_A_OBJ_EVENT_OBJCLASS = "OBJCLASS"

# Acc SimEvents Table
COL_NAME_ACC_EVENTS_SIMEVENTID = "SIMEVENTID"
COL_NAME_ACC_EVENTS_RESID = "RESID"
COL_NAME_ACC_EVENTS_BEGINABSTS = "BEGINABSTS"
COL_NAME_ACC_EVENTS_ENDABSTS = "ENDABSTS"
COL_NAME_ACC_EVENTS_STARTDRIVENDIST = "STARTDRIVENDIST"
COL_NAME_ACC_EVENTS_ENDDRIVENDIST = "ENDDRIVENDIST"

# Events Table
COL_NAME_EVENTS_SEID = "SEID"
COL_NAME_EVENTS_BEGINABSTS = "BEGINABSTS"
COL_NAME_EVENTS_ENDABSTS = "ENDABSTS"
COL_NAME_EVENTS_START_IDX = "START_IDX"
COL_NAME_EVENTS_STOP_IDX = "STOP_IDX"
COL_NAME_EVENTS_INDEX = "INDX"
COL_NAME_EVENTS_MEASID = "MEASID"
COL_NAME_EVENTS_TRID = "TRID"
COL_NAME_EVENTS_EVENTTYPEID = "EVENTTYPEID"
COL_NAME_EVENTS_RESASSID = "RESASSID"
COL_NAME_EVENTS_RDID = "RDID"

# Events View
COL_NAME_EVENTS_VIEW_ASSESSMENT = "ASSESSMENT"
COL_NAME_EVENTS_VIEW_SEID = "SEID"
COL_NAME_EVENTS_VIEW_BEGINABSTS = "BEGINABSTS"
COL_NAME_EVENTS_VIEW_ENDABSTS = "ENDABSTS"
COL_NAME_EVENTS_VIEW_START_IDX = "START_IDX"
COL_NAME_EVENTS_VIEW_STOP_IDX = "STOP_IDX"
COL_NAME_EVENTS_VIEW_MEASID = "MEASID"
COL_NAME_EVENTS_VIEW_TRID = "TRID"
COL_NAME_EVENTS_VIEW_EVENTTYPE = "EVENTTYPE"
COL_NAME_EVENTS_VIEW_CLASSNAME = "CLASSNAME"
COL_NAME_EVENTS_VIEW_FILE_NAME = "FILENAME"
COL_NAME_EVENTS_VIEW_COMMENT = "ASSCOMMENT"
COL_NAME_EVENTS_VIEW_RESASSID = "RESASSID"
COL_NAME_EVENTS_VIEW_ABSTS = "ABSTS"
COL_NAME_EVENTS_VIEW_NAME = "NAME"
COL_NAME_EVENTS_VIEW_ATTRID = "ATTRID"
COL_NAME_EVENTS_VIEW_VALUE = "VALUE"
COL_NAME_EVENTS_VIEW_ATTRTYPEID = "ATTRTYPEID"
COL_NAME_EVENTS_VIEW_RDID = "RDID"

# EventDetails Table
COL_NAME_EVENT_DET_EDID = "EDID"
COL_NAME_EVENT_DET_ABSTS = "ABSTS"
COL_NAME_EVENT_DET_SEID = "SEID"

# EventAttr Table
COL_NAME_EVENT_ATTR_ATTRID = "ATTRID"
COL_NAME_EVENT_ATTR_ATTRTYPEID = "ATTRTYPEID"
COL_NAME_EVENT_ATTR_VALUE = "VALUE"
COL_NAME_EVENT_ATTR_EDID = "EDID"

# Result Image Table
COL_NAME_EVENT_IMG_ATTRID = "ATTRID"
COL_NAME_EVENT_IMG_IMAGE = "IMAGE"
COL_NAME_EVENT_IMG_TITLE = "TITLE"
COL_NAME_EVENT_IMG_FORMAT = "FORMAT"

# EventAttrTypes
COL_NAME_EVENT_ATTR_TYPES_ATTRTYPEID = "ATTRTYPEID"
COL_NAME_EVENT_ATTR_TYPES_NAME = "NAME"
COL_NAME_EVENT_ATTR_TYPES_DESC = "DESCRIPTION"
COL_NAME_EVENT_ATTR_TYPES_UNITID = "UNITID"
COL_NAME_EVENT_ATTR_TYPES_PARENT = "PARENT"

# AccSimObjEvents Table
COL_NAME_ACC_OBJ_EVENTS_OBJEVENTID = "OBJEVENTID"
COL_NAME_ACC_OBJ_EVENTS_SIMEVENTID = "SIMEVENTID"
COL_NAME_ACC_OBJ_EVENTS_OBJEVENTTYPE = "OBJEVENTTYPE"
COL_NAME_ACC_OBJ_EVENTS_CRITICALITY = "CRITICALITY"

# AccSimObjEventTypes Table
COL_NAME_ACC_OBJ_EVENT_T_OBJEVENTTYPE = "OBJEVENTTYPE"
COL_NAME_ACC_OBJ_EVENT_T_NAME = "NAME"
COL_NAME_ACC_OBJ_EVENT_T_DESCRIPTION = "DESCRIPTION"

# VAL_Jobs Table
COL_NAME_JOBS_JBID = "JBID"
COL_NAME_JOBS_SERVID = "SERVID"
COL_NAME_JOBS_HPCJOBID = "HPCJOBID"

# VAL_JOBS_MAP  Table
COL_NAME_TRUN_JOB_MAP_TRUNMAPID = "TRUNMAPID"
COL_NAME_TRUN_JOB_MAP_TRID = "TRID"
COL_NAME_TRUN_JOB_MAP_JBID = "JBID"

# Column result default value. Default return value if no result is found.
COL_RES_DEF_VAL = -1

# Testrun lock is supported with version 8.0
TRUN_LOCK_VALUE = 1
TRUN_UNLOCK_VALUE = 0
TRUN_IS_DELETED = 1
TRUN_IS_NOT_DELETED = 0

# VAL subschema features and version definition
DELETE_LOCK_TRUN_FEATURE = 8
TRUN_COMPONENT_FEATURE = 15
TRUN_TESTTYPE_FEATURE = 16
TRUN_ADD_INFO_FEATURE = 17
TRUN_SIM_NAME_FEATURE = 18
TRUN_REMAKRS_FEATURE = 19
TRUN_VAL_VERSION_FEATURE = 20

SUB_SCHEME_TAG = "VAL"

IDENT_STRING = DBVAL


# - classes -----------------------------------------------------------------------------------------------------------
class BaseValResDB(BaseDB):  # pylint: disable=R0904
    """
    **base implementation of the Validation Result Database**

    For the first connection to the DB for val tables just create a new instance of this class like

    .. python::

        from stk.db.val import BaseValResDB

        dbval = BaseValResDB("MFC4XX")   # or use "ARS4XX", "VGA" or path/name of sqlite file

    If already some connection to another table of the DB is created use that one to speed up your code:

    .. python::

        dbval = BaseValResDB(dbxxx.db_connection)

    The connection is closed when the first instance using it is deleted.

    **error_tolerance**

    The setting of an error tolerance level allows to define if an error during later processing is

    - just listed to the log file (error_tolerance = 3, HIGH) if possible,
      e.g. if it can return the existing id without changes in case of adding an already existing entry
    - raising an AdasDBError immediately (error_tolerance < 1, LOW)

    More optional keywords are described at `BaseDB` class initialization.

    """
    # ===================================================================
    # Constraint DB Libary Interface for public use
    # ===================================================================

    # ===================================================================
    # Handling of database
    # ===================================================================

    def __init__(self, *args, **kw):
        """Initialize constraint database

        :keyword db_connection: The database connection to be used
        :type db_connection: cx_oracle.Connection, pydodbc.Connection, sqlite3.Connection, sqlce.Connection
        :keyword table_prefix: The table name prefix which is usually master schema name
        :type table_prefix: str
        :keyword sql_factory: SQL Query building factory
        :type sql_factory: GenericSQLStatementFactory
        :keyword error_tolerance: Error tolerance level based on which some error are acceptable
        :type error_tolerance: int
        """
        kw['strIdent'] = DBVAL
        # cache result type id by name
        self._restypeid_by_cache = {}
        # cache event type id by classname
        self._eventtypeid_cache = {}
        # cache attribute typeid by name
        self._attrib_typeid_cache = {}
        # cache trun recordy by trid
        self._testrun_cache = {}
        BaseDB.__init__(self, *args, **kw)

    # --- TESTRUN Table. --------------------------------------------------
    def add_testrun(self, testrun, replace=False):  # pylint: disable=R0912
        """Add a new testrun to the database.

        :param testrun: The testrun dictionary
        :param replace: Replace
        :return: Returns the testrun ID.
        """
        try:
            if self.sub_scheme_version >= TRUN_COMPONENT_FEATURE:
                if COL_NAME_TR_CMPID not in testrun:
                    testrun[COL_NAME_TR_CMPID] = None
                cond = self._get_testrun_condition(name=testrun[COL_NAME_TR_NAME],
                                                   check_point=testrun[COL_NAME_TR_CHECKPOINT],
                                                   tr_type=testrun[COL_NAME_TR_TYPE_ID],
                                                   pid=testrun[COL_NAME_TR_PID],
                                                   cmpid=testrun[COL_NAME_TR_CMPID])
            else:
                cond = self._get_testrun_condition(name=testrun[COL_NAME_TR_NAME],
                                                   check_point=testrun[COL_NAME_TR_CHECKPOINT],
                                                   tr_type=testrun[COL_NAME_TR_TYPE_ID],
                                                   pid=testrun[COL_NAME_TR_PID])
                if COL_NAME_TR_CMPID in testrun:
                    testrun.pop(COL_NAME_TR_CMPID)

        except StandardError, ex:
            raise AdasDBError("Can't create testrun condition. Error: '%s'" % (ex))

        if COL_NAME_TR_TTID in testrun and self.sub_scheme_version < TRUN_TESTTYPE_FEATURE:
            testrun.pop(COL_NAME_TR_TTID)

        if COL_NAME_TR_ADD_INFO in testrun and self.sub_scheme_version < TRUN_ADD_INFO_FEATURE:
            testrun.pop(COL_NAME_TR_ADD_INFO)

        if COL_NAME_TR_SIM_NAME in testrun and self.sub_scheme_version < TRUN_SIM_NAME_FEATURE:
            testrun.pop(COL_NAME_TR_SIM_NAME)

        if COL_NAME_TR_SIM_VERSION in testrun and self.sub_scheme_version < TRUN_VAL_VERSION_FEATURE:
            testrun.pop(COL_NAME_TR_SIM_VERSION)

        if COL_NAME_TR_VAL_SW_VERSION in testrun and self.sub_scheme_version < TRUN_VAL_VERSION_FEATURE:
            testrun.pop(COL_NAME_TR_VAL_SW_VERSION)

        if COL_NAME_TR_REMARKS in testrun and self.sub_scheme_version < TRUN_REMAKRS_FEATURE:
            testrun.pop(COL_NAME_TR_REMARKS)

        entries = self.select_generic_data(table_list=[TABLE_NAME_TESTRUN], where=cond)

        if COL_NAME_TR_COLL_NAME not in testrun:
            testrun[COL_NAME_TR_COLL_NAME] = ''

        if len(entries) == 1 and replace is True:
            stored_tr_uid = int(entries[0][COL_NAME_TR_USERID])
            current_uid = int(testrun[COL_NAME_TR_USERID])
            if stored_tr_uid != current_uid:
                msg = "For the checkpoint '" + testrun[COL_NAME_TR_CHECKPOINT]
                msg += "' a Testrun '%s' has already been created in" % testrun[COL_NAME_TR_NAME]
                msg += "the validation result database by another user (user_id %d)" % stored_tr_uid
                raise AdasDBError(msg)

            trid = int(entries[0][COL_NAME_TR_ID])
            if self.delete_testrun(tr_id=trid) != -1:
                self.commit()
                self._log.debug("Testrun '%s' deleted." % testrun[COL_NAME_TR_NAME])
                self.add_generic_data(testrun, TABLE_NAME_TESTRUN)
                entries = self.select_generic_data(table_list=[TABLE_NAME_TESTRUN], where=cond)
                if len(entries) == 1:
                    trid = entries[0][COL_NAME_TR_ID]
                else:
                    raise AdasDBError("Testrun name '%s' cannot be added. " % (testrun[COL_NAME_TR_NAME]))
            else:
                return trid
        elif len(entries) <= 0:
            self.add_generic_data(testrun, TABLE_NAME_TESTRUN)
            entries = self.select_generic_data(table_list=[TABLE_NAME_TESTRUN], where=cond)
            if len(entries) == 1:
                trid = entries[0][COL_NAME_TR_ID]
            else:
                raise AdasDBError("Testrun name '%s' cannot be added. " % (testrun[COL_NAME_TR_NAME]))
        else:
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                tmp = "Testrun '%s' exists already in the validation result database" % testrun[COL_NAME_TR_NAME]
                raise AdasDBError(tmp)
            else:
                tmp = "Testrun '%s' already exists in the validation result database." % testrun[COL_NAME_TR_NAME]
                self._log.warning(tmp)
                if len(entries) == 1:
                    trid = entries[0][COL_NAME_TR_ID]
                elif len(entries) > 1:
                    tmp = "Testrun name '%s' " % (testrun[COL_NAME_TR_NAME])
                    tmp += "cannot be resolved because it is ambiguous. (%s)" % (entries)
                    raise AdasDBError(tmp)
        # done
        return int(trid)

    def update_testrun(self, testrun, where=None):
        """
        Update existing testrun records.

        :param testrun: The testrun record update.
        :param where: The condition to be fulfilled by the workflow to the updated.
        :return: Returns the number of affected workflow.
        """
        rowcount = 0

        if where is None:
            where = self._get_testrun_condition(name=testrun[COL_NAME_TR_NAME], delete_status=0)

        if (testrun is not None) and (len(testrun) != 0):
            rowcount = self.update_generic_data(testrun, TABLE_NAME_TESTRUN, where)
        # done
        return rowcount

    def delete_testrun(self, name=None, checkpoint=None, type_id=None, user_id=None,  # pylint: disable=R0913
                       tr_id=None, recursive=False):
        """
        Delete existing testrun records. if testrun is locked its will not be deleted

        :param name: name of the testrun to delete
        :param checkpoint: corresponding checkpoint
        :param type_id: Type of the testrun
        :param user_id: user ID of the testrun
        :param tr_id: Testrun ID - If given, the parameter name, checkpoint, typeid and user_id will be neglegted.
        :param recursive: delete the child testruns as well - optional argument
        :return: Returns the number of affected workflow.
        """
        if tr_id is None:
            tr_id = self.get_testrun_id(name=name, checkpoint=checkpoint, type_id=type_id,
                                        user_id=user_id)
        if self._is_testrun_lock(tr_id):
            raise AdasDBError("Testrun id = '%d' is Locked and in the validation result database" % id)

        testrun_tree = self.execute("""with recur(TRID,PARENT, IS_DELETED, IS_LOCKED) as (
                                        select c.TRID, c.PARENT,c.IS_DELETED, c.IS_LOCKED from VAL_TESTRUN c
                                        where c.PARENT = %d and c.IS_DELETED = 0 and c.IS_LOCKED = 0 union all
                                        select c.TRID, c.PARENT,c.IS_DELETED, c.IS_LOCKED from VAL_TESTRUN c
                                        inner join recur r on c.PARENT = r.trid) select TRID from recur """ % (tr_id))

        del_trids = [i[0] for i in reversed(testrun_tree)]
        del_trids.append(tr_id)

        if not recursive and len(testrun_tree) > 0:
            raise AdasDBError("Testrun id = '%d' has dependent child testrun.use recursive flag to " % (tr_id) +
                              "delete child testrun if needed otherwise delete child first")

        if self.sub_scheme_version < DELETE_LOCK_TRUN_FEATURE or self.role == ROLE_DB_ADMIN:
            # Support for old version of VAL db

            for del_trid in del_trids:
                self._delete_all_results_of_testrun(tr_id)
                cond = self._get_testrun_condition(tr_id=del_trid)
                self.delete_generic_data(TABLE_NAME_TESTRUN, where=cond)
                self.commit()
                if int(del_trid) in self._testrun_cache:
                    self._testrun_cache.pop(int(del_trid))
        else:
            for del_trid in del_trids:
                if self._is_testrun_lock(tr_id):
                    raise AdasDBError("Testrun id = '%d' is Locked and in the validation result database" % del_trid)

            # check if the test run is not already deleted
                cond = self._get_testrun_condition(tr_id=tr_id, delete_status=0)
                self.update_generic_data({COL_NAME_TR_DELETED: TRUN_IS_DELETED}, TABLE_NAME_TESTRUN, where=cond)
            self.commit()
            return 1

    def restore_testrun(self, name=None, checkpoint=None, type_id=None, user_id=None,  # pylint: disable=R0913
                        tr_id=None, recursive=False):
        """ Restore a deleted TestRun

        :param name: Name of the testrun
        :param checkpoint: checkpoint name
        :param type_id: Oberserver Type ID
        :param user_id: User Identifier
        :param tr_id: Testrun ID
        :param recursive: If True, process child testruns as well
        """
        # rowcount = 0
        if self.role != ROLE_DB_ADMIN:
            raise AdasDBError("Inssufficient Priviliage to Restore TestRUN")
        if tr_id is None:
            testrun = self.get_testrun(name=name, checkpoint=checkpoint, type_id=type_id, user_id=user_id)
            tr_id = testrun[COL_NAME_TR_ID]
        else:
            # cond = self._get_testrun_condition(name, checkpoint, type, user_id, delete_status=1)
            testrun = self.get_testrun(tr_id=tr_id)
        if recursive:
            trids = self.get_testrun_ids_for_parent(tr_id, delete_status=1)
            if len(trids) > 0:
                for _tr_id in trids:
                    self.restore_testrun(tr_id=_tr_id, recursive=True)
            else:
                self.restore_testrun(tr_id=tr_id, recursive=False)

        cond = self._get_testrun_condition(tr_id=tr_id, delete_status=1)
        testrun = self.select_generic_data(table_list=[TABLE_NAME_TESTRUN], where=cond)
        if len(testrun) == 1:
            testrun = testrun[0]
            testrun.pop(COL_NAME_TR_START)
            testrun.pop(COL_NAME_TR_END)
            testrun[COL_NAME_TR_DELETED] = 0
            self.update_generic_data(testrun, TABLE_NAME_TESTRUN, where=cond)
            if int(tr_id) in self._testrun_cache:
                self._testrun_cache.pop(int(tr_id))
        else:
            raise AdasDBError("Testrun name cannot be restore due to ambigious data in TestRun table. ")
            # rowcount += self.DeleteTestRun(tr_id=testrun, recursive=rowcount)

    def get_testrun_lock(self, name=None, checkpoint=None, type_id=None, user_id=None,  # pylint: disable=R0913
                         tr_id=None):
        """Check lock status for the given TestRun ID

        :param name: Testrun id
        :param checkpoint:
        :param type_id:
        :param user_id:
        :param tr_id:
        :return: boolean status if lock value is None-Zero return True else return False
        """
        if tr_id is None:
            tr_id = self.get_testrun_id(name, checkpoint, type_id, user_id)
        return int(self._is_testrun_lock(tr_id))

    def update_testrun_lock(self, name=None,  # pylint: disable=R0913
                            checkpoint=None,
                            type_id=None, user_id=None, tr_id=None,
                            recursive=False, lock=None, unlock=None):
        """
        Update Testrun Flag

        :param name: TestRun Name
        :type name: str
        :param checkpoint: Checkpoint
        :type checkpoint: str
        :param type_id: Observer type id
        :type type_id: int
        :param user_id: User Id db internal primary key
        :type user_id: int
        :param tr_id: Test Run Id db internal primary key
        :type tr_id: int
        :param recursive: flag to recursively lock/unlock all the child testrun
        :type recursive: Bool
        :param lock: Set this boolean flag to True if lock is required
        :type lock: Bool
        :param unlock: Set this boolean flag to True if unlock is required
        :type unlock: boolean
        """
        if self.sub_scheme_version < DELETE_LOCK_TRUN_FEATURE:
            raise AdasDBError("The Lock system is only available in dbval ver>= %d" % DELETE_LOCK_TRUN_FEATURE)

        if tr_id is None:
            testrun = self.get_testrun(name=name, checkpoint=checkpoint, type_id=type_id, user_id=user_id)
            tr_id = testrun[COL_NAME_TR_ID]
        else:
            testrun = self.get_testrun(tr_id=tr_id)

        if recursive:
            trids = self.get_testrun_ids_for_parent(tr_id)
            if len(trids) > 0:
                for trid in trids:
                    self.update_testrun_lock(tr_id=trid, recursive=True, lock=lock, unlock=unlock)
            else:
                self.update_testrun_lock(tr_id=tr_id, recursive=False, lock=lock, unlock=unlock)
        testrun.pop(COL_NAME_TR_START)
        testrun.pop(COL_NAME_TR_END)
        if self._is_testrun_lock(tr_id) and testrun[COL_NAME_TR_USERID] != self.current_gbluserid:
            other_user = self.execute("SELECT LOGINNAME FROM GBL_USERS WHERE USERID= %d"
                                      % testrun[COL_NAME_TR_USERID])[0][0]

            self._log.warning("Lock/Unlock is not possible because TestRun is already locked by user " + other_user +
                              "Please contact the user to acquire lock or unlock")
            return

        if lock is not None and unlock is None:
            testrun[COL_NAME_TR_TRUNLOCK] = TRUN_LOCK_VALUE

        if lock is None and unlock is not None:
            testrun[COL_NAME_TR_TRUNLOCK] = TRUN_UNLOCK_VALUE

        if (lock is not None and unlock is not None) or (lock is None and unlock is None):
            raise AdasDBError("Testrun Lock request is ambigious \
                               because both flag are set to True or False for TRUN ID %d " % (tr_id))
        else:
            cond = self._get_testrun_condition(tr_id=tr_id)
            self.update_generic_data(testrun, TABLE_NAME_TESTRUN, where=cond)
            if int(tr_id) in self._testrun_cache:
                self._testrun_cache.pop(int(tr_id))

    def _is_testrun_lock(self, tr_id):
        """Check lock status for the given TestRun ID

        :param tr_id: Testrun id
        :return: boolean status if lock value is None-Zero return True else return False
        """
        if self.sub_scheme_version < DELETE_LOCK_TRUN_FEATURE:
            raise AdasDBError("The Lock system is only available in dbval ver>= %d" % DELETE_LOCK_TRUN_FEATURE)
        else:
            testrun = self.get_testrun(tr_id=tr_id)
            if testrun[COL_NAME_TR_TRUNLOCK] != 0:
                return True
            else:
                return False
        # done

    def _delete_all_results_of_testrun(self, tr_id=None):
        """Delete existing results of a testrun.

        :param tr_id: The testrun id to delete.
        :return: Returns the number of affected event types.

        """
#        Delete events
        event_data, image_attrib = self.get_event_for_testrun(tr_id)
        col_list = event_data[0]
        event_data = event_data[1]

        resassid_idx = col_list.index(COL_NAME_EVENTS_RESASSID)
        arribid_idx = col_list.index(COL_NAME_EVENT_ATTR_ATTRID)
        seid_idx = col_list.index(COL_NAME_EVENTS_SEID)
        edid_idx = col_list.index(COL_NAME_EVENT_DET_EDID)
        assess_ids = list(set([i[resassid_idx] for i in event_data]))
        attrib_ids = list(set([i[arribid_idx] for i in event_data]))
        seids = list(set([i[seid_idx] for i in event_data]))
        edids = list(set([i[edid_idx] for i in event_data]))
        del event_data
        for attrid in image_attrib:
            self.delete_event_image(attrid=attrid)
        del image_attrib
        self.commit()
        for attrid in attrib_ids:
            self.delete_generic_data(TABLE_NAME_EVENT_ATTR, where=self._get_event_attribute_condition(attrid))
        del attrib_ids
        self.commit()
        for edid in edids:
            self.delete_generic_data(TABLE_NAME_EVENT_DETAILS, where=self._get_event_details_condition(edid=edid))
        del edids
        self.commit()
        for seid in seids:
            self.delete_generic_data(TABLE_NAME_EVENTS, where=self._get_event_condition(seid=seid))
        del seids
        self.commit()
        for assess_id in assess_ids:
            self.delete_assessment(assess_id)
        del assess_ids
        self.commit()
#        Delete results
        records = self.get_result(tr_id=tr_id)
        if records and type(records) is dict:
            records = [records]

        for record in records:
            self.delete_result_image({COL_NAME_RESIMG_ID: record[COL_NAME_RES_ID]})
            self.delete_result_message({COL_NAME_RESMESS_ID: record[COL_NAME_RES_ID]})
            self.delete_result_value({COL_NAME_RESVAL_ID: record[COL_NAME_RES_ID]})
            self.delete_result_label(record[COL_NAME_RES_ID])
            self.delete_result({COL_NAME_RES_TESTRUN_ID: tr_id})
            self.commit()
        self.delete_hpc_jobs_for_testrun(tr_id)

    def get_all_testruns(self, name=None, checkpoint=None, type_id=None,  # pylint: disable=R0913
                         user_id=None, tr_id=None, proj_id=None, delete_status=0, cmpid=None):
        """
        Get all testruns by Name and optional Checkpoint, TestRunType or UserID

        :param name: Name of the testrun
        :param checkpoint: Checkpoint Name
        :param type_id: Checkpoint Name
        :param user_id: User Identifier
        :param tr_id: Testrun Identifier
        :param proj_id: Project id
        :param delete_status: 0/1 - not/ deleted
        :param cmpid: Component Id
        :return: Testrun record
        """
        record = {}
        if self.sub_scheme_version < TRUN_COMPONENT_FEATURE:
            cmpid = None
        cond = self._get_testrun_condition(name, checkpoint, type_id, user_id, tr_id,
                                           delete_status, pid=proj_id, cmpid=cmpid)
        orderby = [COL_NAME_TR_START]
        entries = self.select_generic_data(table_list=[TABLE_NAME_TESTRUN], where=cond, order_by=orderby)
        if len(entries) <= 0:
            self._log.warning(str("testrun with name '%s' does not exist in the validation result database." % name))
        else:
            record = entries
        # done
        return record

    def get_seids_for_testrun(self, tr_id, measids):
        """
        Get all SEIDs for the specified testrun and measid

        :return: seid's record
        """
        columns = [COL_NAME_EVENTS_VIEW_SEID]
        cond = self._get_event_condition(trid=tr_id, measid=measids)
        entries = self.select_generic_data(distinct_rows=True, select_list=columns,
                                           table_list=[TABLE_NAME_EVENTS_VIEW],
                                           where=cond)
        if len(entries) <= 0:
            tmp = "There are no seids for testrun '%s'" % str(tr_id)
            tmp += "and measid '%s' in the validation result database." % str(measids)
            self._log.warning(tmp)
        # done
        return entries

    def get_measids_for_testrun(self, tr_id):
        """ Get all MEASIDs for the specified testrun

        :return: measid's record
        """
        columns = [COL_NAME_EVENTS_VIEW_MEASID, COL_NAME_EVENTS_VIEW_FILE_NAME]
        orderby = [COL_NAME_EVENTS_VIEW_FILE_NAME]
        cond = self._get_testrun_condition(tr_id=tr_id)
        entries = self.select_generic_data(distinct_rows=True, select_list=columns,
                                           table_list=[TABLE_NAME_EVENTS_VIEW],
                                           where=cond, order_by=orderby)
        if len(entries) <= 0:
            self._log.warning("There are no measids for testrun '%s' in the validation result database." % str(tr_id))
        # done
        return entries

    def get_testrun(self, name=None, checkpoint=None, type_id=None, user_id=None,  # pylint: disable=R0913
                    tr_id=None, parent_id=None, pid=None, cmpid=None):
        """ Get a testrun by Name and optional Checkpoint, TestRunType or UserID

        :param name: Name of the testrun
        :param checkpoint: Checkpoint Name
        :param type_id: Checkpoint Name
        :param user_id: User Identifier
        :param tr_id: Testrun Identifier
        :param parent_id: Parent Id of testrun
        :param cmpid: Component Id
        :return: Testrun record
        """
        record = {}
        if tr_id is not None and int(tr_id) in self._testrun_cache:
            return self._testrun_cache[int(tr_id)]

        if self.sub_scheme_version < TRUN_COMPONENT_FEATURE:
            cmpid = None
        cond = self._get_testrun_condition(name=name, check_point=checkpoint,
                                           tr_type=type_id, user_id=user_id, tr_id=tr_id,
                                           parent_id=parent_id, pid=pid, cmpid=cmpid)
        entries = self.select_generic_data(table_list=[TABLE_NAME_TESTRUN], where=cond)
        if len(entries) <= 0:
            msg = "testrun with name '%s' does not exist in the val result database for the current user" % name
            self._log.warning(msg)
        elif len(entries) > 1:
            self._log.warning("testrun with name '%s' cannot be resolved because it is ambiguous. (%d)"
                              % (name, len(entries)))
        else:
            record = entries[0]
            self._testrun_cache[int(record[COL_NAME_TR_ID])] = record
        # done

        return record

    def get_testrun_ids_for_parent(self, parent_id, delete_status=0):
        """ Get the testruns for a given parent id

        :param parent_id: Parent ID of the Test run
        :return: Returns a list of testrun Id taking the parent ID as parent
        """
        try:
            parent_id = int(parent_id)
        except:
            raise AdasDBError("Parent_id is not an integer")

        id_list = []
        cond = self._get_testrun_parent_condition(parent_id, delete_status)
        entries = self.select_generic_data(table_list=[TABLE_NAME_TESTRUN], where=cond)
        for rec in entries:
            id_list.append(int(rec[COL_NAME_TR_ID]))

        return id_list

    def get_testrun_id(self, name, checkpoint=None, type_id=None, user_id=None,  # pylint: disable=R0913
                       parent_id=None):
        """ Get a testrun by Name and optional Checkpoint, TestRunType or UserID

        :param name: Name of the testrun
        :param checkpoint: Checkpoint Name
        :param type_id: Validation Observer ID
        :param user_id: User Identifier
        :param parent_id:
        :return: Testrun ID
        """
        record = self.get_testrun(name=name, checkpoint=checkpoint, type_id=type_id,
                                  user_id=user_id, parent_id=parent_id)
        if COL_NAME_TR_ID in record:
            return int(record[COL_NAME_TR_ID])

        return -1

    def get_deleted_testrun_ids(self, name=None, checkpoint=None, pid=None, limit=10,  # pylint: disable=R0913
                                distinct=True):
        """
        Get all Parent Test Run given with limited no. of record for testrun

        :param name:
        :param checkpoint:
        :param pid:
        :param limit: limit to return no. of testrun ids since deletetion takes long time
        :type limit: int
        :param distinct:
        :return: List of testrun Ids
        """

        if self.role == ROLE_DB_ADMIN and self.sub_scheme_version >= DELETE_LOCK_TRUN_FEATURE:
            cond_del = self._get_testrun_condition(name=name, check_point=checkpoint,
                                                   pid=pid, delete_status=1)
            cond = cond_del
            entries = self.select_generic_data(select_list=[COL_NAME_TR_ID],
                                               table_list=[TABLE_NAME_TESTRUN],
                                               where=cond)
            record = []
            for entry in entries:
                record.append(entry[COL_NAME_TR_ID])

            if 0 < limit < len(record):
                record = record[:limit]

            childs = []
            for rec in record:
                childs += self._get_child_testrun_id(rec, delete_status=1, recursive=True)

            if distinct:
                return list(set(record + childs))
            else:
                return record + childs
#            return record
        else:
            raise AdasDBError("Cannot executed due to inssufficient privilage contact Administrator")

    def _get_child_testrun_id(self, parent_id, delete_status=0, recursive=True):
        """ Get the testruns for a given parent id

        :param parent_id: Parent ID of the Test run
        :return: Returns a list of testrun Id taking the parent ID as parent
        """

        trids = self.get_testrun_ids_for_parent(parent_id, delete_status=delete_status)
        if not recursive:
            return trids
        else:
            for trid in trids:
                return trids + self._get_child_testrun_id(trid, delete_status=delete_status, recursive=recursive)
            return trids

    def _get_testrun_condition(self, name=None, check_point=None, tr_type=None,  # pylint: disable=R0912,R0913
                               user_id=None, tr_id=None, delete_status=0, parent_id=None, pid=None, cmpid=None):
        """Get the condition expression to access the testrun.

        :param name: Name of the testrun (optional)
        :param check_point: checkpoint (optional)
        :param tr_type: Testrun type id (optional)
        :param user_id: User ID (optional)
        :param tr_id: Test run ID. If set, other setting will neglected
        :param delete_status: Flag to add delete condition for newer version
                                support to set condition for undelete testrun
        :param parent_id: Parent Id of the testrun
        :param pid: Project Id binded to testrun
        :param cmpid: Component Id
        :return: Returns the condition expression
        """
        cond = None

        if tr_id is not None:
            cond = SQLBinaryExpr(COL_NAME_TR_ID, OP_EQ, tr_id)
        else:
            if name is not None:
                cond_name = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER], COL_NAME_TR_NAME),
                                          OP_EQ,
                                          SQLLiteral(name.lower()))
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_name)
                else:
                    cond = cond_name
            if check_point is not None:
                cond_cp = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER], COL_NAME_TR_CHECKPOINT),
                                        OP_EQ,
                                        SQLLiteral(check_point.lower()))
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_cp)
                else:
                    cond = cond_cp
            if tr_type is not None:
                cond_cp = SQLBinaryExpr(COL_NAME_TR_TYPE_ID, OP_EQ, tr_type)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_cp)
                else:
                    cond = cond_cp
            if user_id is not None:
                cond_cp = SQLBinaryExpr(COL_NAME_TR_USERID, OP_EQ, user_id)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_cp)
                else:
                    cond = cond_cp
            if parent_id is not None:
                cond_pt = SQLBinaryExpr(COL_NAME_TR_PARENT, OP_EQ, parent_id)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_pt)
                else:
                    cond = cond_pt
            if pid is not None:
                cond_pid = SQLBinaryExpr(COL_NAME_TR_PID, OP_EQ, pid)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_pid)
                else:
                    cond = cond_pid

            if cmpid is not None:
                cond_cmpid = SQLBinaryExpr(COL_NAME_TR_CMPID, OP_EQ, cmpid)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_cmpid)
                else:
                    cond = cond_cmpid

            if self.sub_scheme_version >= DELETE_LOCK_TRUN_FEATURE and delete_status is not None:
                cond_del = SQLBinaryExpr(COL_NAME_TR_DELETED, OP_EQ, delete_status)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_del)
                else:
                    cond = cond_del
        return cond

    def get_filtered_results_types_details_assessment(self, tr_id, meas_id=None,  # pylint:disable=C0103,R0913
                                                      res_id=None, predef_filter_str=None, filter_str=None,
                                                      how_many=None):
        """Get the Results from VAL_RESULTS.

        :param tr_id: Testrun id
        :param meas_id: Measurement id (optional)
        :param res_id: result id (optional)
        :param predef_filter_str: prepared predefined filter list (optional)
        :param filter_str: prepared filter list (optional)
        :param how_many: how many rows should be retrieved (if not set - all rows to be retrieved)
        :return: time, results : Returns the duration and the list of selected results
        """
        # select rt.name        as res_type,
        #       rd.rdid,
        #       rd.name        as res_descriptor,
        #       re.value,
        #       gu.name        as unit,
        #       cf.recfileid   as filename,
        #       re.resassid    as assessment
        # from DEV_ARS4XX_ADMIN.val_result re
        # inner join DEV_ARS4XX_ADMIN.val_testrun tr on tr.trid = re.trid
        # inner join DEV_ARS4XX_ADMIN.val_resultdescriptor rd on rd.rdid = re.rdid
        # inner join DEV_ARS4XX_ADMIN.val_resulttypes rt on rt.restypeid = rd.restypeid
        # inner join DEV_ARS4XX_ADMIN.cat_files cf on cf.measid = re.measid
        # inner join DEV_ARS4XX_ADMIN.gbl_units gu on gu.unitid = rd.unitid
        # where tr.typeid = 10 and tr.trid = 1095
        # order by re.measid

        _ = predef_filter_str  # intentionally, preventing W0613
        _ = filter_str  # intentionally, preventing W0613
        _ = how_many  # intentionally, preventing W0613
        start_time = time()
        columns = ["rt." + COL_NAME_RESULTTYPE_NAME + " AS Res_type",
                   "re." + COL_NAME_RES_ID,
                   "rd." + COL_NAME_RESDESC_NAME + " AS Res_descriptor",
                   "re." + COL_NAME_RES_VALUE,
                   "rd." + COL_NAME_RESDESC_UNIT_ID + " AS Unit",
                   "re." + COL_NAME_RES_MEASID + " AS Filename",
                   "re." + COL_NAME_RES_RESASSID + " AS Assessment"]

        orderby = ["re." + COL_NAME_RES_MEASID]
        tables = []
        join = SQLTableExpr(TABLE_NAME_RESULT + " re")
        join_1 = SQLJoinExpr(join,
                             OP_INNER_JOIN,
                             SQLTableExpr(TABLE_NAME_TESTRUN + " tr"),
                             "tr." + COL_NAME_TR_ID + " = re." + COL_NAME_RES_TESTRUN_ID)
        join_2 = SQLJoinExpr(join_1,
                             OP_INNER_JOIN,
                             SQLTableExpr(TABLE_NAME_RESULT_DESC + " rd"),
                             "rd." + COL_NAME_RESDESC_ID + " = re." + COL_NAME_RES_RESDESC_ID)
        join_3 = SQLJoinExpr(join_2,
                             OP_INNER_JOIN,
                             SQLTableExpr(TABLE_NAME_RESULTTYPE + " rt"),
                             "rt." + COL_NAME_RESULTTYPE_ID + " = rd." + COL_NAME_RESDESC_RESTYPE_ID)

        tables.append(join_3)

        cond = []
        if cond == []:
            cond = SQLBinaryExpr("re." + COL_NAME_RES_TESTRUN_ID, OP_EQ, tr_id)
        if meas_id is not None:
            cond_cp = SQLBinaryExpr("re." + COL_NAME_RES_MEASID, OP_EQ, meas_id)
            cond = SQLBinaryExpr(cond, OP_AND, cond_cp)
        if res_id is not None:
            cond_cp = SQLBinaryExpr("re." + COL_NAME_RES_ID, OP_EQ, res_id)
            cond = SQLBinaryExpr(cond, OP_AND, cond_cp)

        entries = self.select_generic_data(distinct_rows=True, select_list=columns,
                                           table_list=tables, where=cond, order_by=orderby)
        elapsed_time = time() - start_time
        return elapsed_time, entries

    def get_filtered_event_types_details_attributes_assessment(self, trid,  # pylint:disable=C0103,R0912,R0913
                                                               measid=None,
                                                               seid=None,
                                                               predef_filter_str=None,
                                                               filter_str=None,
                                                               how_many=None):
        """Get the events attributes for the assessment from the VAL_VIEW_EVENTS_ATRIBUTES.

        :param trid: Testrun id
        :param measid: Measurement id (optional)
        :param seid: seid (optional)
        :param predef_filter_str: prepared predefined filter list (optional)
        :param filter_str: prepared filter list (optional)
        :param how_many: how many rows should be retrieved (if not set - all rows to be retrieved)
        :return: time, events : Returns the duration and the list of selected events
        """
        # SELECT DISTINCT SEID, q1.BEGINABSTS, q1.ENDABSTS, q1.FILENAME, q1.EVENTTYPE, q1.ASSESSMENT
        # FROM DEV_ARS34X_ADMIN.VAL_View_Events_Attributes Q1
        # INNER JOIN
        #    (SELECT * FROM VAL_EVENTDETAILS evd
        #    INNER JOIN DEV_ARS34X_ADMIN.VAL_EventAttr ea ON ea.EDID = evd.EDID
        #    INNER JOIN DEV_ARS34X_ADMIN.VAL_EventAttrTypes eat ON ea.ATTRTYPEID =
        #     eat.ATTRTYPEID  AND eat.NAME = 'distx' AND ea.VALUE > 95) Q2
        # ON Q1.SEID = Q2.SEID
        # INNER JOIN
        #    (SELECT * FROM VAL_EVENTDETAILS evd
        #    INNER JOIN DEV_ARS34X_ADMIN.VAL_EventAttr ea ON ea.EDID = evd.EDID
        #    INNER JOIN DEV_ARS34X_ADMIN.VAL_EventAttrTypes eat ON ea.ATTRTYPEID =
        #    eat.ATTRTYPEID  AND eat.NAME = 'vehspeed' AND ea.VALUE > 33.5) Q3
        # ON Q1.SEID = Q3.SEID
        # WHERE (TRID = 2741) And (assessment = 'Valid')  ORDER BY SEID;

        _ = how_many  # intentionally, preventing W0613
        start_time = time()

        alias_tb_event_attrib_view = "Q1"
        col_seid = SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(alias_tb_event_attrib_view),
                                               COL_NAME_EVENTS_VIEW_SEID),
                                 OP_AS, COL_NAME_EVENTS_VIEW_SEID)

        col_beginabsts = SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(alias_tb_event_attrib_view),
                                                     COL_NAME_EVENTS_VIEW_BEGINABSTS),
                                       OP_AS, COL_NAME_EVENTS_VIEW_BEGINABSTS)

        col_endabsts = SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(alias_tb_event_attrib_view),
                                                   COL_NAME_EVENTS_VIEW_ENDABSTS),
                                     OP_AS, COL_NAME_EVENTS_VIEW_ENDABSTS)

        col_filename = SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(alias_tb_event_attrib_view),
                                                   COL_NAME_EVENTS_VIEW_FILE_NAME),
                                     OP_AS, COL_NAME_EVENTS_VIEW_FILE_NAME)

        col_eventtype = SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(alias_tb_event_attrib_view),
                                                    COL_NAME_EVENTS_VIEW_EVENTTYPE),
                                      OP_AS, COL_NAME_EVENTS_VIEW_EVENTTYPE)
#         col_classname = SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(alias_tb_event_attrib_view),
#                                                 COL_NAME_EVENTS_VIEW_CLASSNAME),
#                                   OP_AS, COL_NAME_EVENTS_VIEW_CLASSNAME),
        coll_assess_state = SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(alias_tb_event_attrib_view),
                                                        COL_NAME_EVENTS_VIEW_ASSESSMENT),
                                          OP_AS, COL_NAME_EVENTS_VIEW_ASSESSMENT)

        columns = [col_seid, col_beginabsts,
                   col_endabsts, col_filename,
                   col_eventtype, coll_assess_state]

        orderby = [COL_NAME_EVENTS_VIEW_SEID]
        tables = []
        join = SQLTableExpr(TABLE_NAME_EVENTS_ATTRIBUTES_VIEW, alias_tb_event_attrib_view)

        i = 0
        for _filter in filter_str:
            if _filter.GetType() == 'attribute':
                i += 1
                values = _filter.GetValues()
                sel_stmt = "(SELECT * FROM " + TABLE_NAME_EVENT_DETAILS + \
                           " evd INNER JOIN " + TABLE_NAME_EVENT_ATTR + \
                           " ea ON  ea.EDID = evd.EDID " + " INNER JOIN " + \
                           TABLE_NAME_EVENT_ATTR_TYPES + \
                           " eat ON ea.ATTRTYPEID = eat.ATTRTYPEID  AND eat.NAME = '" + \
                           str(_filter.GetName())
                sel_stmt += "' AND ea.VALUE "  # > 22.22 and ea.value < 40) j2 on j1.edid = j2.edid
                if str(_filter.GetOperator()) == 'Between':
                    sel_stmt = sel_stmt + "> " + str(values[0]) + " AND ea.VALUE < " + str(values[1])
                else:
                    sel_stmt = sel_stmt + str(_filter.GetOperator()) + " " + str(values[0])
                sel_stmt = sel_stmt + ") Q" + str(i + 1)

                join = SQLJoinExpr(join,
                                   OP_INNER_JOIN,
                                   sel_stmt,
                                   "Q1.SEID = Q" + str(i + 1) + ".SEID")
        tables.append(join)

        cond = []
        if cond == []:
            cond = SQLBinaryExpr(COL_NAME_EVENTS_TRID, OP_EQ, trid)
        if measid is not None:
            cond_cp = SQLBinaryExpr(COL_NAME_EVENTS_MEASID, OP_EQ, measid)
            cond = SQLBinaryExpr(cond, OP_AND, cond_cp)
        if seid is not None:
            cond_cp = SQLBinaryExpr(COL_NAME_EVENTS_SEID, OP_EQ, seid)
            cond = SQLBinaryExpr(cond, OP_AND, cond_cp)

        tmp_filter = {}
        for _filter in filter_str:
            if _filter.GetType() == 'assessment':
                cond_stmt = "(" + str(_filter.GetName()) + str(_filter.GetOperator()) + ")"
                if _filter.GetName() in tmp_filter:
                    tmp_filter[_filter.GetName()].append(cond_stmt)
                else:
                    tmp_filter[_filter.GetName()] = []
                    tmp_filter[_filter.GetName()].append(cond_stmt)

        for _filter in tmp_filter:
            cond_or = []
            for i in xrange(len(tmp_filter[_filter])):
                if i == 0:
                    cond_or = str(tmp_filter[_filter][i])
                else:
                    cond_or = SQLBinaryExpr(cond_or, OP_OR, str(tmp_filter[_filter][i]))

            cond = SQLBinaryExpr(cond, OP_AND, cond_or)

        if isinstance(predef_filter_str, SQLBinaryExpr):
            cond = SQLBinaryExpr(cond, OP_AND, predef_filter_str)

        entries = self.select_generic_data(distinct_rows=True, select_list=columns,
                                           table_list=tables, where=cond, order_by=orderby)
        elapsed_time = time() - start_time
        return elapsed_time, entries

    def get_events_info_for_export_to_csv(self, trid):  # pylint:disable=C0103
        """Get the events information for the export to CSV from the VAL_VIEW_EVENTS_ATRIBUTES.

        :param trid: test run id
        :return: events_infos : the list of the selected informations
        """
        columns = ["Q1." + COL_NAME_EVENTS_VIEW_SEID,
                   "Q1." + COL_NAME_EVENTS_VIEW_BEGINABSTS,
                   "Q1." + COL_NAME_EVENTS_VIEW_ENDABSTS,
                   "Q1." + COL_NAME_EVENTS_VIEW_FILE_NAME,
                   "Q1." + COL_NAME_EVENTS_VIEW_NAME,
                   "Q1." + COL_NAME_EVENTS_VIEW_VALUE]

        orderby = ["Q1." + COL_NAME_EVENTS_VIEW_SEID]

        tables = []
        attr_list = "('distx','disty','vrelx','rectobjid')"
        sel_stmt = TABLE_NAME_EVENTS_ATTRIBUTES_VIEW + " Q1" + \
            " INNER JOIN ( SELECT * FROM " + TABLE_NAME_EVENT_DETAILS + \
            " evd INNER JOIN " + TABLE_NAME_EVENT_ATTR + " ea ON  ea.EDID = evd.EDID " + \
            " INNER JOIN " + TABLE_NAME_EVENT_ATTR_TYPES + \
            " eat ON ea.ATTRTYPEID = eat.ATTRTYPEID  AND eat.NAME IN " + attr_list + ") Q2 ON Q1.SEID = Q2.SEID "

        cond = " TRID = " + str(trid) + " AND Q1.NAME IN " + attr_list

        tables.append(sel_stmt)
        entries = self.select_generic_data(distinct_rows=True, select_list=columns, table_list=tables,
                                           where=cond, order_by=orderby)
        return entries

    # --- EVENTDETAILS Table ---------------------------------------------
    def add_event_details(self, seid, absts):
        """Add detail entry to the event

        :param seid: Event Id
        :type seid: int
        :param absts: Absolute Timestamp
        :type absts: int
        :return: edid: Event Detail Id
        :rtype: int
        """

        if seid is None or absts is None:
            raise AdasDBError("Seid or absts are not integers.")

        edid = self.get_event_details_id(seid=seid, absts=absts)
        if edid is None:
            details = {COL_NAME_EVENT_DET_ABSTS: absts, COL_NAME_EVENTS_SEID: seid}
            edid = self.add_generic_data(details, TABLE_NAME_EVENT_DETAILS,
                                         SQLUnaryExpr(OP_RETURNING, COL_NAME_EVENT_DET_EDID))
            if edid is None:
                tmp = "Timestamp '%s' " % (details[COL_NAME_EVENT_DET_ABSTS])
                tmp += "for '%s' Event cannot be added." % (details[COL_NAME_EVENTS_SEID])
                raise AdasDBError(tmp)

        # done
        return int(edid)

    def get_event_details(self, edid=None, seid=None, absts=None):
        """Get Event detail data

        :param edid: Event Detail ID --> Mandatory parameter
        :type edid: int
        :param seid: Event id  --> Mandatory parameter
        :type seid: int
        :param absts: Abolute Timestamp  --> Mandatory parameter
        :type absts: int
        :return: Record of Event Detail
        :rtype: list of dict
        """

        if (edid is None) and (seid is None) and (absts is None):
            raise AdasDBError("Seid, absts, edid not defined")

        records = []
        cond = self._get_event_details_condition(edid, seid, absts)
        entries = self.select_generic_data(table_list=[TABLE_NAME_EVENT_DETAILS], where=cond)

        if len(entries) >= 1:
            records = entries

        return records

    def get_event_details_id(self, edid=None, seid=None, absts=None):
        """Get Event Detail id i.e. edid

        :param edid: Event Detail Id
        :type edid: int
        :param seid: Event Id
        :type seid: int
        :param absts: Absolute Time stamp
        :type absts: int
        :return: list of all detail Ids
        :rtype: list
        """
        entries = self.get_event_details(edid=edid, seid=seid, absts=absts)

        if len(entries) == 1:
            edid = entries[0][COL_NAME_EVENT_DET_EDID]
        elif len(entries) > 1:
            edid = []
            for item in entries:
                edid.append(item[COL_NAME_EVENT_DET_EDID])
        else:
            edid = None

        return edid

    def get_event_details_timestamps(self, seid=None, globs=False):
        """Get Timestamps list of event details

        :param seid: Event Id
        :type seid: int
        :param globs: Flag for Global Attribute
        :type globs: boolean
        :return: list of all timestamp
        :rtype: list
        """
        if seid is None:
            raise AdasDBError("Seid not defined")
        if globs:
            absts = -1
        else:
            absts = None

        entries = self.get_event_details(seid=seid, absts=absts)
        if len(entries) == 1:
            timestamps = entries[0][COL_NAME_EVENT_DET_ABSTS]
        elif len(entries) > 1:
            timestamps = []
            for item in entries:
                if not globs and item[COL_NAME_EVENT_DET_ABSTS] != -1:
                    timestamps.append(item[COL_NAME_EVENT_DET_ABSTS])
        else:
            timestamps = []

        # done
        return timestamps

    def get_event_details_attributes(self, seid, timestamps=None, attribute_name=None):
        """Get Attribute Data for an Event

        :param seid: Event id
        :type seid: int
        :param timestamps: Absolute Timestamp
        :type timestamps: int
        :param attribute_name: attribute name
        :type attribute_name: string
        :return: Record contain Attribute name, value and timestamps
        :rtype: list of dict
        """
        columns = [COL_NAME_EVENT_DET_ABSTS, COL_NAME_EVENT_ATTR_TYPES_NAME, COL_NAME_EVENT_ATTR_VALUE]

        tables = []

        cond = self._get_event_details_condition(seid=seid, absts=timestamps)

        if attribute_name is not None:
            cond_attr = SQLBinaryExpr(COL_NAME_EVENT_ATTR_TYPES_NAME, OP_EQ, SQLLiteral(attribute_name))
            if cond is not None:
                cond = SQLBinaryExpr(cond, OP_AND, cond_attr)

        tbldetails = TABLE_NAME_EVENT_DETAILS
        tbleventattr = TABLE_NAME_EVENT_ATTR
        tbleventdet = TABLE_NAME_EVENT_DETAILS
        tblattrtypes = TABLE_NAME_EVENT_ATTR_TYPES

        valeventattrjoin = SQLJoinExpr(SQLTableExpr(tbldetails),
                                       OP_INNER_JOIN,
                                       SQLTableExpr(tbleventattr),
                                       SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tbleventdet),
                                                                   COL_NAME_EVENT_DET_EDID),
                                                     OP_EQ,
                                                     SQLColumnExpr(SQLTableExpr(tbleventattr),
                                                                   COL_NAME_EVENT_DET_EDID)))

        tables.append(SQLJoinExpr(SQLTableExpr(valeventattrjoin),
                                  OP_INNER_JOIN,
                                  SQLTableExpr(tblattrtypes),
                                  SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tbleventattr),
                                                              COL_NAME_EVENT_ATTR_ATTRTYPEID),
                                                OP_EQ,
                                                SQLColumnExpr(SQLTableExpr(tblattrtypes),
                                                              COL_NAME_EVENT_ATTR_TYPES_ATTRTYPEID))))

        orderby = [COL_NAME_EVENT_DET_ABSTS, COL_NAME_EVENT_ATTR_TYPES_NAME]
        entries = self.select_generic_data(select_list=columns, table_list=tables, where=cond, order_by=orderby)
        return entries

    def delete_event_details(self, seid):
        """Delete all event details and the attributes assigned to this event details

        :param seid: event details id
        """
        rowcount = 0

        try:
            seid = int(seid)
        except:
            raise AdasDBError("Seid is not a integer.")

        cond = self._get_event_details_condition(seid=seid)

        entries = self.select_generic_data(table_list=[TABLE_NAME_EVENT_DETAILS], where=cond)

#        if self.error_tolerance < ERROR_TOLERANCE_LOW:
#            if len(entries) == 0:
#                raise AdasDBError("No record found for SEID: %s." % seid)

        # loop over all details assigned to the event seid
        for entry in entries:
            edid = entry[COL_NAME_EVENT_DET_EDID]
            self.delete_event_attributes(edid)
            cond = self._get_event_details_condition(seid=seid, edid=edid)
            self.delete_generic_data(TABLE_NAME_EVENT_DETAILS, where=cond)
            rowcount += 1
        # done
        return rowcount

    @staticmethod
    def _get_event_details_condition(edid=None, seid=None, absts=None):
        """ Get Event Details Condition selection statement

        :param edid: Event Description Identifier
        :param seid: SEID
        :param absts: Absolute Timestamp
        :return: Selection Statement
        """
        cond = None

        if edid is not None:
            cond = SQLBinaryExpr(COL_NAME_EVENT_DET_EDID, OP_EQ, edid)
        else:
            if seid is not None:
                cond_seid = SQLBinaryExpr(COL_NAME_EVENTS_SEID, OP_EQ, seid)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_seid)
                else:
                    cond = cond_seid

            if absts is not None:
                cond_rel = SQLBinaryExpr(COL_NAME_EVENT_DET_ABSTS, OP_EQ, SQLLiteral(absts))
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_rel)
                else:
                    cond = cond_rel

        return cond

    # --- EVENTATTR Table ---------------------------------------------
    def add_event_attribute(self, attribute, getattrid=False):
        """Add Attribute Data

        :param attribute: attribute Record
        :type attribute: dict
        :param getattrid: flag to return attribute id for newly insert data
        :type getattrid: int
        :return: Attribute Id
        :rtype: if getattrid is false return type is None if getattrid is true return type is int
        """
        attrid = None

        if((COL_NAME_EVENT_ATTR_ATTRTYPEID not in attribute) or
           (COL_NAME_EVENT_ATTR_EDID not in attribute) or
           (COL_NAME_EVENT_ATTR_VALUE not in attribute)):
            raise AdasDBError("AddEventAttribute: attribute not completly setted.")

        if getattrid:
            attrid = self.add_generic_data(attribute, TABLE_NAME_EVENT_ATTR,
                                           SQLUnaryExpr(OP_RETURNING, COL_NAME_EVENT_ATTR_ATTRID))
            if attrid is None:
                raise AdasDBError("Event attribute cannot be added.")
        else:
            self.add_generic_data(attribute, TABLE_NAME_EVENT_ATTR)

        return attrid

    def get_event_attribute(self, attrid=None, edid=None, attrtypeid=None, value=None,  # pylint: disable=R0913
                            attrname=None):
        """Get Event Attribute Data based on criteria depending on the passed parameter

        :param attrid: attibute ID
        :type attrid: int
        :param edid: event detail id
        :type edid: int
        :param attrtypeid: attribute type id
        :type attrtypeid: int
        :param value: attribute value
        :type value: float
        :param attrname: attribute name
        :type attrname: string
        :return: records contain attribute data
        :rtype: list of dictionary
        """

        if attrname is not None:
            attrtypeid = self.get_event_attribute_type_id(attrname.lower())

        cond = self._get_event_attribute_condition(attrid, attrtypeid, edid, value)

        entries = self.select_generic_data(table_list=[TABLE_NAME_EVENT_ATTR], where=cond)

        # done
        return entries

    def get_event_attribute_id(self, attribute_name=None, attrid=None, edid=None,  # pylint: disable=R0913
                               attrtypeid=None, value=None):
        """Get Attribute Id with criteria based on parameter passed

        :param attribute_name: name of attribute
        :type attribute_name: string
        :param attrid: attribute id
        :type attrid: int
        :param edid: event detail id
        :type edid: int
        :param attrtypeid: attribute type id
        :type attrtypeid: int
        :param value: attribtue value
        :type value: float
        :return: attribute id
        :rtype: int
        """

        attribute_id = None
        entries = self.get_event_attribute(attrid=attrid, edid=edid, attrtypeid=attrtypeid,
                                           value=value, attrname=attribute_name)

        if len(entries) == 1:
            attribute_id = entries[0][COL_NAME_EVENT_ATTR_ATTRID]
        return attribute_id

    def delete_event_attributes(self, edid):
        """Delete all the attributes with the event details id

        :param edid: event details id
        :return: 0
        """
        rowcount = 0

        cond = self._get_event_attribute_condition(edid=edid)
        entries = self.select_generic_data(table_list=[TABLE_NAME_EVENT_ATTR], where=cond)
        for entry in entries:
            attrid = entry[COL_NAME_EVENT_ATTR_ATTRID]
            rowcount += self.delete_event_image(attrid=attrid)
            cond = self._get_event_attribute_condition(attrid=attrid)
            rowcount += self.delete_generic_data(TABLE_NAME_EVENT_ATTR, where=cond)
        # done
        return rowcount

    def update_event_attribute(self, attrid, value):
        """Update Value of an attribute

        :param attrid: attribute  id
        :type attrid: int
        :param value: attribute value
        :type value: flaot
        """
        attribute = {}
        attribute[COL_NAME_EVENT_ATTR_VALUE] = value

        where = self._get_event_attribute_condition(attrid=attrid)

        rowcount = self.update_generic_data(attribute, TABLE_NAME_EVENT_ATTR, where)
        self.commit()

        return rowcount

    @staticmethod
    def _get_event_attribute_condition(attrid=None, attrtypeid=None, edid=None, value=None):
        """ Get Event Attribute Condition selection statement

        :param attrid: Attribute Identifier
        :param attrtypeid: Attribute Type Identifier
        :param edid: Event Description Identifier
        :param value: Event Attribute Value
        :return: Selection Statement
        """
        cond = None

        if attrid is not None:
            cond = SQLBinaryExpr(COL_NAME_EVENT_ATTR_ATTRID, OP_EQ, attrid)
        else:
            if attrtypeid is not None:
                cond_e = SQLBinaryExpr(COL_NAME_EVENT_ATTR_TYPES_ATTRTYPEID, OP_EQ, attrtypeid)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_e)
                else:
                    cond = cond_e

            if edid is not None:
                cond_e = SQLBinaryExpr(COL_NAME_EVENT_DET_EDID, OP_EQ, edid)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_e)
                else:
                    cond = cond_e
            if value is not None:
                cond_v = SQLBinaryExpr(COL_NAME_EVENT_ATTR_VALUE, OP_EQ, SQLLiteral(value))
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_v)
                else:
                    cond = cond_v

        # done
        return cond

    # --- EVENTATTRTYPES Table ---------------------------------------------
    def add_event_attribute_type(self, attribute_type):
        """Add new Attribute Type

        :param attribute_type: dictionary of a record to be insert
        :type attribute_type: dict
        :return: attribute type id
        :rtype: int
        """
        try:
            attribute_type[COL_NAME_EVENT_ATTR_TYPES_NAME] = attribute_type[COL_NAME_EVENT_ATTR_TYPES_NAME].lower()
            attribute_type_name = attribute_type[COL_NAME_EVENT_ATTR_TYPES_NAME]
        except:
            raise AdasDBError("AddEventAttributeType: Is not a dictionary")

        atrttype_id = self.get_event_attribute_type_id(attribute_type_name)

        if atrttype_id is None:
            self.add_generic_data(attribute_type, TABLE_NAME_EVENT_ATTR_TYPES)
            entries = self.get_event_attribute_type(attribute_type_name)
            if len(entries) == 1:
                atrttype_id = entries[0][COL_NAME_EVENT_ATTR_TYPES_ATTRTYPEID]
            elif len(entries) > 1:
                raise AdasDBError("Attribute Type is ambiguous in the database. (%s)" % attribute_type_name)
            else:
                raise AdasDBError("Event attribute type name '%s' cannot be added. " % (attribute_type_name))

        return atrttype_id

    def get_event_attribute_type(self, name=None):
        """Get Attribute Type record for Given attribute Name

        :param name: attribute name
        :type name: string
        :return: record containing attribute type data. list contain only one element
        :rtype: list
        """

        if name is not None and not isinstance(name, str):
            raise AdasDBError("GetEventAttributeType: name is not a string.")

        cond = self._get_event_attribute_type_condition(name)
        entries = self.select_generic_data(table_list=[TABLE_NAME_EVENT_ATTR_TYPES], where=cond)

        if len(entries) <= 0:
            self._log.warning("Event attribute '%s' does not exist in the validation database." % name)

        return entries

    def get_event_attribute_type_id(self, name):
        """Get Attribute Id for a given Name

        :param name: attribute name
        :type name: str
        :return: Attribute type id
        :rtype: int
        """
        attrtype_id = None
        if name.lower() in self._attrib_typeid_cache:
            return self._attrib_typeid_cache[name.lower()]
        entries = self.get_event_attribute_type(name)

        if len(entries) == 1:
            attrtype = entries[0]
            attrtype_id = attrtype[COL_NAME_EVENT_ATTR_TYPES_ATTRTYPEID]
            self._attrib_typeid_cache[name.lower()] = attrtype_id
        elif len(entries) > 1:
            raise AdasDBError("Attribute Type is ambiguous in the database. (%s)" % name)
        return attrtype_id

    def get_event_attribute_type_ids_for_parent(self, parent_id):  # pylint:disable=C0103
        """Get Attribute Types under the given parent id

        :param parent_id: parent Id
        :type parent_id: int
        """
        id_list = []
        try:
            parent_id = int(parent_id)
        except:
            raise AdasDBError("Parent id is not an integer.")

        cond = self._get_event_attribute_type_condition(parent=parent_id)
        entries = self.select_generic_data(table_list=[TABLE_NAME_EVENT_ATTR_TYPES], where=cond)

        for types in entries:
            id_list.append(types[COL_NAME_EVENT_ATTR_TYPES_ATTRTYPEID])

        return id_list

    @staticmethod
    def _get_event_attribute_type_condition(name=None, parent=None):  # pylint:disable=C0103
        """Generic method to create condition for AttributeType table

        :param name: arrtibute name
        :type name: string
        :param parent: parent id
        :type parent: int
        """
        cond = None
        if name is not None:
            cond = SQLBinaryExpr(COL_NAME_EVENT_ATTR_TYPES_NAME, OP_EQ, SQLLiteral(name.lower()))

        if parent is not None:
            cond_p = SQLBinaryExpr(COL_NAME_EVENT_ATTR_TYPES_PARENT, OP_EQ, parent)
            if cond is not None:
                cond = SQLBinaryExpr(cond, OP_AND, cond_p)
            else:
                cond = cond_p

        # done
        return cond

    # --- EVENTIMAGE Table ---------------------------------------------
    def add_event_image(self, event_img):
        """Add a new image to the database.

        :param event_img: The result assessment - resid is mandatory as it is the primary key
        :return: Returns the number of affected rows.
        """
        # event_image = {}

        if not isinstance(event_img[COL_NAME_EVENT_IMG_IMAGE], buffer) and \
                event_img[COL_NAME_EVENT_IMG_IMAGE] is not None:
            raise AdasDBError('AddEventImage: Image ist not a buffer!')

        rowcount = 0
        cond = self._get_event_image_condition(event_img[COL_NAME_EVENT_IMG_ATTRID])
        entries = self.select_generic_data(table_list=[TABLE_NAME_EVENT_IMAGE], where=cond)
        if len(entries) <= 0:
            stmt = 'INSERT INTO ' + str(TABLE_NAME_EVENT_IMAGE)
            stmt += " (%s," % COL_NAME_EVENT_IMG_ATTRID
            stmt += "%s," % COL_NAME_EVENT_IMG_TITLE
            stmt += "%s," % COL_NAME_EVENT_IMG_FORMAT
            stmt += "%s)" % COL_NAME_EVENT_IMG_IMAGE
            stmt += " VALUES('%s'," % (event_img[COL_NAME_EVENT_IMG_ATTRID])
            stmt += "'%s'," % (event_img[COL_NAME_EVENT_IMG_TITLE])
            stmt += "'%s', :1)" % (event_img[COL_NAME_EVENT_IMG_FORMAT])
            cursor = self._db_connection.cursor()
            try:
                self._log.debug(stmt)
                cursor.execute(stmt, (event_img[COL_NAME_EVENT_IMG_IMAGE],))
                rowcount = cursor.rowcount
            except:
                self._log.error(stmt)
                raise
            finally:
                cursor.close()

        else:
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                tmp = "Image for Attrid ID '%s' " % event_img[COL_NAME_EVENT_IMG_ATTRID]
                tmp += "exists already in the validation result database"
                raise AdasDBError(tmp)
            else:
                tmp = "Image for Result ID '%s' " % event_img[COL_NAME_EVENT_IMG_ATTRID]
                tmp += "exists already in the validation result database"
                self._log.warning(tmp)
                if len(entries) == 1:
                    # id = entries[0][COL_NAME_EVENT_IMG_ATTRID]
                    pass
                elif len(entries) > 1:
                    raise AdasDBError("Image for result ID cannot be found because it is ambiguous. (%s)" % entries)
        # done
        return rowcount

    def get_event_image(self, attrid):
        """Get existing event image.

        :param attrid: attribute ID
        :return: Record if exist
        """
        record = {}
        cond = self._get_event_image_condition(attrid)
        entries = self.select_generic_data(table_list=[TABLE_NAME_EVENT_IMAGE], where=cond)
        if len(entries) <= 0:
            self._log.warning(str("Image for Result ID '%s' does not exist in the validation result database."
                                  % str(attrid)))
        elif len(entries) > 1:
            self._log.warning(str("Image for Result '%s' cannot be found because it is ambiguous. (%s)"
                                  % (str(attrid), entries)))
        else:
            record = entries[0]
            record[COL_NAME_EVENT_IMG_IMAGE] = self._get_blob_buffer(record[COL_NAME_EVENT_IMG_IMAGE])

        # done
        return record

    def update_event_image(self):
        """
        Is it really needed?
        """
        pass

    def delete_event_image(self, attrid):
        """Delete existing event image records.

        :param attrid:
        :return: Returns the number of affected assessments.
        """
        if attrid is not None:
            cond = self._get_event_image_condition(attrid)

        rowcount = self.delete_generic_data(TABLE_NAME_EVENT_IMAGE, where=cond)
        # done
        return rowcount

    @staticmethod
    def _get_blob_buffer(blob_data):
        """Get Instance of buffer for the blob data

        :param blob_data: blob data from database
        :type blob_data: any datatype representing
                         BLOB depending on database and its driver
        """
        if blob_data is not None:
            if type(blob_data) is LOB:
                return buffer(blob_data.read())
            else:
                return buffer(blob_data)
        else:
            return None

    @staticmethod
    def _get_event_image_condition(attrid):
        """Get the condition expression to access the event image

        :param attrid: attrid
        :return: Returns the condition expression
        """
        return SQLBinaryExpr(COL_NAME_EVENT_IMG_ATTRID, OP_EQ, SQLLiteral(attrid))

    def get_event_image_plot_seq(self, seid, attr_type, plot=False):
        """
        Get sequence of plot or video images with timestamps

        :param seid: event Id
        :type seid: int
        :param attr_type: attribute type name
        :type attr_type: string
        :param plot: unused parameter. Dont use it
        :type plot: Bool
        :return: recordings containg time stamp and corresponding image as list of dict records
        :rtype: list

        """

        # SELECT IMAGE
        # FROM VAL_EventDetails
        # INNER JOIN VAL_EventAttr ON (VAL_EventDetails.EDID = VAL_EventAttr.EDID)
        # INNER JOIN VAL_EventAttrTypes ON (VAL_EventAttr.ATTRTYPEID = VAL_EventAttrTypes.ATTRTYPEID)
        # LEFT JOIN VAL_EVENTIMAGE ON (VAL_EVENTIMAGE.ATTRID = VAL_EventAttr.ATTRID)
        # WHERE (SEID = 4430) AND (NAME = 'video_seq_file') AND (ABSTS = '-1') ORDER BY ABSTS

        _ = plot  # intentionally, preventing W0613
        columns = [COL_NAME_EVENT_IMG_IMAGE]
        # columns = ["*"]

        tables = []

        cond = SQLBinaryExpr(COL_NAME_EVENT_DET_SEID, OP_EQ, seid)

        cond_att = SQLBinaryExpr(COL_NAME_EVENT_ATTR_TYPES_NAME, OP_EQ, SQLLiteral(attr_type))

        cond = SQLBinaryExpr(cond, OP_AND, cond_att)
        cond_absts = SQLBinaryExpr(COL_NAME_EVENT_DET_ABSTS, OP_EQ, -1)
        cond = SQLBinaryExpr(cond, OP_AND, cond_absts)

        join = SQLJoinExpr(SQLTableExpr(TABLE_NAME_EVENT_DETAILS),
                           OP_INNER_JOIN,
                           SQLTableExpr(TABLE_NAME_EVENT_ATTR),
                           SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_EVENT_DETAILS),
                                                       COL_NAME_EVENT_DET_EDID),
                                         OP_EQ,
                                         SQLColumnExpr(SQLTableExpr(TABLE_NAME_EVENT_ATTR),
                                                       COL_NAME_EVENT_ATTR_EDID)))

        join_1 = SQLJoinExpr(SQLTableExpr(join),
                             OP_INNER_JOIN,
                             SQLTableExpr(TABLE_NAME_EVENT_ATTR_TYPES),
                             SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_EVENT_ATTR),
                                                         COL_NAME_EVENT_ATTR_ATTRTYPEID),
                                           OP_EQ,
                                           SQLColumnExpr(SQLTableExpr(TABLE_NAME_EVENT_ATTR_TYPES),
                                                         COL_NAME_EVENT_ATTR_TYPES_ATTRTYPEID)))

        join_2 = SQLJoinExpr(SQLTableExpr(join_1),
                             OP_LEFT_OUTER_JOIN,
                             SQLTableExpr(TABLE_NAME_EVENT_IMAGE),
                             SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_EVENT_IMAGE),
                                                         COL_NAME_EVENT_IMG_ATTRID),
                                           OP_EQ,
                                           SQLColumnExpr(SQLTableExpr(TABLE_NAME_EVENT_ATTR),
                                                         COL_NAME_EVENT_ATTR_ATTRID)))

        tables.append(join_2)

        # orderby = [COL_NAME_EVENT_DET_absts]
        # entries = self.select_generic_data(select_list=columns, table_list=tables,
        #                                 where=cond, order_by=orderby,
        #                                 how_many = how_many)
        entries = self.select_generic_data(select_list=columns, table_list=tables, where=cond)

        return entries

    # --- EVENTS Table ----------------------------------------------------
    def add_event(self, event, replace=False):
        """Add a new sim event to the database.

        :param event: event dictionary record
        :type event: dict
        :param replace: if Replace is True --> Delete all the events existing events that matches passed event
                                                dictionary record therefore only event exist with index = 0
                                                will be allow
                        if Replace is False --> Add the passed event dict record if the event is already stored
                                                then Addevent with incrementing index. This will allow multiple
                                                events of same type occured at sametime to be save in database
        :type replace: bool
        :return: Returns the event ID.
        """
        try:
            cond = self._get_event_condition(event_type_id=event[COL_NAME_EVENTS_EVENTTYPEID],
                                             trid=event[COL_NAME_EVENTS_TRID],
                                             measid=event[COL_NAME_EVENTS_MEASID],
                                             beginabsts=event[COL_NAME_EVENTS_BEGINABSTS],
                                             endabsts=event[COL_NAME_EVENTS_ENDABSTS],
                                             start_idx=event[COL_NAME_EVENTS_START_IDX],
                                             stop_idx=event[COL_NAME_EVENTS_STOP_IDX])
        except Exception as ex:
            raise AdasDBError("Couldn't generate EventCondition. %s" % str(ex))

        status, msg = self._check_event_data(event)
        if not status:
            raise AdasDBError(msg)
        if replace:
            entries = self.select_generic_data(table_list=[TABLE_NAME_EVENTS], where=cond)
            if len(entries):
                self._log.warning(str(len(entries)) +
                                  " event(s) already saved in database will be replace as requested")
            for entry in entries:
                self.delete_event(seid=entry[COL_NAME_EVENTS_SEID])
        event[COL_NAME_EVENTS_INDEX] = self._get_event_next_index(cond)
        seid = self.add_generic_data(event, TABLE_NAME_EVENTS, SQLUnaryExpr(OP_RETURNING, COL_NAME_EVENTS_SEID))
        if seid is None:
            tmp = "'%s' Event from " % (event[COL_NAME_EVENTS_EVENTTYPEID])
            tmp += "'%s' to " % (event[COL_NAME_EVENTS_BEGINABSTS])
            tmp += "'%s' cannot be added." % (event[COL_NAME_EVENTS_ENDABSTS])
            tmp += "'%s' cannot be added." % str(event[COL_NAME_EVENTS_INDEX])
            raise AdasDBError(tmp)

        return seid

    def _get_event_next_index(self, cond):
        """Get next index value for the current

        :param cond: Sql expression representing condition
        """
        select_list = [SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_MAX], COL_NAME_EVENTS_INDEX),
                                     OP_AS, COL_NAME_EVENTS_INDEX)]
        entries = self.select_generic_data(select_list=select_list, table_list=[TABLE_NAME_EVENTS], where=cond)

        if entries[0][COL_NAME_EVENTS_INDEX] is not None:
            return entries[0][COL_NAME_EVENTS_INDEX] + 1
        else:
            return 0

    @staticmethod
    def _check_event_data(event):
        """Check Event data is logically correct

        :param event: Event Dictionary
        :type event: dict
        """
        msg = ""
        start_idx = event[COL_NAME_EVENTS_START_IDX]
        stop_idx = event[COL_NAME_EVENTS_STOP_IDX]
        status = True
        start_time = event[COL_NAME_EVENTS_BEGINABSTS]
        stop_time = event[COL_NAME_EVENTS_ENDABSTS]

        if stop_idx < start_idx:
            status = False
            msg += "Start_Indx is greater than Stop_Indx"

        if stop_time < start_time:
            status = False
            msg += " Start_Time is greater than Stop_Time"

        return status, msg

    def add_event1(self, event, replace=False):
        """deprecated"""
        # Mistakenly added while debugging and optimizing orignal function and should be remove (Zaheer)
        deprecation('add_event1() is deprecated and will be removed soon')
        return self.add_event(event, replace)

    def get_measid_for_seid(self, seid):
        """
        Get measurement Id for the given event id seid

        :param seid: event id
        :type seid: int
        """

        columns = [COL_NAME_EVENTS_VIEW_MEASID]
        cond = self._get_event_condition(table_name=TABLE_NAME_EVENTS_VIEW, seid=seid)
        entries = self.select_generic_data(select_list=columns, table_list=[TABLE_NAME_EVENTS_VIEW], where=cond)
        return entries[0][COL_NAME_EVENTS_VIEW_MEASID]

    def get_event_for_testrun(self, trid, measid=None, beginabsts=None, endabsts=None,  # pylint: disable=R0912,R0913
                              rdid=None, cond=None, filt_stat=None, inc_asmt=True, inc_attrib=True, inc_images=True):
        """
        Get Event for Testrun without Event View or Event Attribute optionally using custom filters

        :param trid: Test Run Id
        :type trid: Integer
        :param measid: Measurement Id
        :type measid: Integer
        :param beginabsts: Begin Absolute TimeStamp
        :type beginabsts: Integer
        :param endabsts: End Absolute TimeStamp
        :type endabsts: Integer
        :param rdid: Result Descriptor
        :type rdid: Integer
        :param cond: SQL Condition optionally
        :type cond: `SQLBinaryExpr`
        :param filt_stat: Filter Statement
        :type filt_stat: List
        :param inc_asmt: Flag to include assessment data
        :type inc_asmt: Bool
        :param inc_attrib: Flag to include Attribute data
        :type inc_attrib: Bool
        :param inc_images: Flag to include Images
        :type inc_images: Bool
        :return: Return records and Image Attribute Id list
        :rtype: list, list
        """

        select_list = []
        image_attribs = []
        aliasevents = "ev"
        tblevents = SQLTableExpr(TABLE_NAME_EVENTS, aliasevents)
        aliaseventtype = "et"
        tbleventtype = SQLTableExpr(TABLE_NAME_EVENTTYPE, aliaseventtype)
        where = SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_TRID), OP_EQ, trid)
        if measid is not None:
            measid_cond = SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_MEASID),
                                        OP_EQ, measid)
            where = SQLBinaryExpr(where, OP_AND, measid_cond)
        if beginabsts is not None:
            begints_cond = SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_BEGINABSTS),
                                         OP_EQ, beginabsts)
            where = SQLBinaryExpr(where, OP_AND, begints_cond)

        if endabsts is not None:
            endts_cond = SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_ENDABSTS),
                                       OP_EQ, endabsts)
            where = SQLBinaryExpr(where, OP_AND, endts_cond)

        # where = self._GetEventCondition(trid=trid, measid=measid, beginabsts=beginabsts, endabsts=endabsts)
        if rdid is not None:
            if type(rdid) is list:
                if len(rdid) == 1:
                    where = SQLBinaryExpr(where, OP_AND, SQLBinaryExpr(SQLColumnExpr(aliasevents,
                                                                                     COL_NAME_EVENTS_VIEW_RDID),
                                                                       OP_EQ, rdid[0]))
                elif len(rdid) > 1:
                    where = SQLBinaryExpr(where, OP_AND, SQLBinaryExpr(SQLColumnExpr(aliasevents,
                                                                                     COL_NAME_EVENTS_VIEW_RDID),
                                                                       OP_IN, str(tuple(rdid))))
            else:
                where = SQLBinaryExpr(where, OP_AND, SQLBinaryExpr(SQLColumnExpr(aliasevents,
                                                                                 COL_NAME_EVENTS_VIEW_RDID),
                                                                   OP_EQ, rdid))
        if cond is not None:
            where = SQLBinaryExpr(where, OP_AND, cond)

        select_list.append(SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_MEASID),
                                         OP_AS, COL_NAME_EVENTS_MEASID))
        select_list.append(SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_EVENTTYPEID),
                                         OP_AS, COL_NAME_EVENTS_EVENTTYPEID))
        select_list.append(SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_RDID),
                                         OP_AS, COL_NAME_EVENTS_RDID))
        select_list.append(SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_SEID),
                                         OP_AS, COL_NAME_EVENTS_SEID))
        select_list.append(SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_BEGINABSTS),
                                         OP_AS, COL_NAME_EVENTS_BEGINABSTS))
        select_list.append(SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_ENDABSTS),
                                         OP_AS, COL_NAME_EVENTS_ENDABSTS))
        select_list.append(SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_START_IDX),
                                         OP_AS, COL_NAME_EVENTS_START_IDX))
        select_list.append(SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_STOP_IDX),
                                         OP_AS, COL_NAME_EVENTS_STOP_IDX))

        select_list.append(SQLBinaryExpr(SQLColumnExpr(aliaseventtype, COL_NAME_EVENTTYPE_CLASSNAME),
                                         OP_AS, COL_NAME_EVENTTYPE_CLASSNAME))

        join_0 = SQLJoinExpr(tblevents, OP_INNER_JOIN, tbleventtype,
                             SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_EVENTTYPEID), OP_EQ,
                                           SQLColumnExpr(aliaseventtype, COL_NAME_EVENTTYPE_ID)))
        table_list = [join_0]
        if inc_attrib:
            aliaseventdet = "ed"
            tbleventdet = SQLTableExpr(TABLE_NAME_EVENT_DETAILS, aliaseventdet)
            aliaseventattr = "ea"
            tbleventattr = SQLTableExpr(TABLE_NAME_EVENT_ATTR, aliaseventattr)
            aliaseventattrtype = "eat"
            tblattrtypes = SQLTableExpr(TABLE_NAME_EVENT_ATTR_TYPES, aliaseventattrtype)
            aliaseventimg = "eim"
            tblimg = SQLTableExpr(TABLE_NAME_EVENT_IMAGE, aliaseventimg)

            attrib_id_col = SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(aliaseventattr), COL_NAME_EVENT_ATTR_ATTRID),
                                          OP_AS, COL_NAME_EVENT_ATTR_ATTRID)
            select_list.append(attrib_id_col)

            select_list.append(SQLBinaryExpr(SQLColumnExpr(aliaseventattr, COL_NAME_EVENT_ATTR_VALUE),
                                             OP_AS, COL_NAME_EVENT_ATTR_VALUE))

            select_list.append(SQLBinaryExpr(SQLColumnExpr(aliaseventattr, COL_NAME_EVENT_ATTR_EDID),
                                             OP_AS, COL_NAME_EVENT_ATTR_EDID))

            select_list.append(SQLBinaryExpr(SQLColumnExpr(aliaseventdet, COL_NAME_EVENT_DET_ABSTS),
                                             OP_AS, COL_NAME_EVENT_DET_ABSTS))

            select_list.append(SQLBinaryExpr(SQLColumnExpr(aliaseventattrtype, COL_NAME_EVENT_ATTR_TYPES_NAME),
                                             OP_AS, COL_NAME_EVENT_ATTR_TYPES_NAME))

            select_list.append(SQLBinaryExpr(SQLColumnExpr(aliaseventattrtype,
                                                           COL_NAME_EVENT_ATTR_TYPES_UNITID),
                                             OP_AS, COL_NAME_EVENT_ATTR_TYPES_UNITID))

            join_1 = SQLJoinExpr(join_0, OP_INNER_JOIN, tbleventdet,
                                 SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_SEID), OP_EQ,
                                               SQLColumnExpr(aliaseventdet, COL_NAME_EVENT_DET_SEID)))

            join_2 = SQLJoinExpr(SQLTableExpr(join_1), OP_INNER_JOIN, tbleventattr,
                                 SQLBinaryExpr(SQLColumnExpr(aliaseventdet, COL_NAME_EVENT_DET_EDID), OP_EQ,
                                               SQLColumnExpr(aliaseventattr, COL_NAME_EVENT_ATTR_EDID)))

            join_2a = SQLJoinExpr(SQLTableExpr(join_2), OP_INNER_JOIN, tblimg,
                                  SQLBinaryExpr(SQLColumnExpr(aliaseventattr, COL_NAME_EVENT_ATTR_ATTRID),
                                                OP_EQ,
                                                SQLColumnExpr(aliaseventimg, COL_NAME_EVENT_ATTR_ATTRID)))

            join_3 = SQLJoinExpr(SQLTableExpr(join_2), OP_INNER_JOIN, tblattrtypes,
                                 SQLBinaryExpr(SQLColumnExpr(aliaseventattr, COL_NAME_EVENT_ATTR_ATTRTYPEID),
                                               OP_EQ,
                                               SQLColumnExpr(aliaseventattrtype,
                                                             COL_NAME_EVENT_ATTR_TYPES_ATTRTYPEID)))

            if inc_images:
                image_attr = self.select_generic_data(select_list=[attrib_id_col], table_list=[join_2a], where=where)

                for entry in image_attr:
                    image_attribs.append(entry[COL_NAME_EVENT_ATTR_ATTRID])
                del image_attr

            table_list = [join_3]
        if inc_asmt:
            aliasasmt = "asmt"
            tblasmt = SQLTableExpr(TABLE_NAME_ASSESSMENT, aliasasmt)
            aliaswf = "wf"
            tblwkf = SQLTableExpr(TABLE_NAME_WORKFLOW, aliaswf)
            aliasuser = "usr"
            tbluser = SQLTableExpr(TABLE_NAME_USERS, aliasuser)
            aliasasmstate = "asmtst"
            tblasmstate = SQLTableExpr(TABLE_NAME_ASSESSMENT_STATE, aliasasmstate)

            select_list.append(SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_RESASSID),
                                             OP_AS, COL_NAME_EVENTS_RESASSID))
            select_list.append(SQLBinaryExpr(SQLColumnExpr(aliasasmt, COL_NAME_ASS_USER_ID),
                                             OP_AS, COL_NAME_ASS_USER_ID))
            select_list.append(SQLBinaryExpr(SQLColumnExpr(aliasasmt, COL_NAME_ASS_COMMENT),
                                             OP_AS, COL_NAME_ASS_COMMENT))
            select_list.append(SQLBinaryExpr(SQLColumnExpr(aliasasmt, COL_NAME_ASS_DATE),
                                             OP_AS, COL_NAME_ASS_DATE))
            select_list.append(SQLBinaryExpr(SQLColumnExpr(aliasasmt, COL_NAME_ASS_TRACKING_ID),
                                             OP_AS, COL_NAME_ASS_TRACKING_ID))
            select_list.append(SQLBinaryExpr(SQLColumnExpr(aliaswf, COL_NAME_WORKFLOW_NAME),
                                             OP_AS, "WF" + COL_NAME_WORKFLOW_NAME))
            select_list.append(SQLBinaryExpr(SQLColumnExpr(aliasuser, COL_NAME_USER_LOGIN),
                                             OP_AS, COL_NAME_USER_LOGIN))
            select_list.append(SQLBinaryExpr(SQLColumnExpr(aliasasmstate, COL_NAME_ASSESSMENT_STATE_NAME),
                                             OP_AS, "ST" + COL_NAME_ASSESSMENT_STATE_NAME))

            if inc_attrib:
                # inner join event ressassid= asmt ressassid
                join_8 = SQLJoinExpr(SQLTableExpr(join_3), OP_INNER_JOIN, tblasmt,
                                     SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_RESASSID),
                                                   OP_EQ,
                                                   SQLColumnExpr(aliasasmt, COL_NAME_ASS_ID)))
            else:
                # inner join event ressassid= asmt ressassid
                join_8 = SQLJoinExpr(join_0, OP_INNER_JOIN, tblasmt,
                                     SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_RESASSID),
                                                   OP_EQ,
                                                   SQLColumnExpr(aliasasmt, COL_NAME_ASS_ID)))

            # inner join global wfid = asmt wfid
            join_9 = SQLJoinExpr(SQLTableExpr(join_8), OP_INNER_JOIN, tblwkf,
                                 SQLBinaryExpr(SQLColumnExpr(aliasasmt, COL_NAME_ASS_WFID),
                                               OP_EQ,
                                               SQLColumnExpr(aliaswf, COL_NAME_WORKFLOW_WFID)))
            # inner join gbluserid = asmt userid
            join_10 = SQLJoinExpr(SQLTableExpr(join_9), OP_INNER_JOIN, tbluser,
                                  SQLBinaryExpr(SQLColumnExpr(aliasasmt, COL_NAME_ASS_USER_ID),
                                                OP_EQ,
                                                SQLColumnExpr(aliasuser, COL_NAME_USER_ID)))
            # inner join gblasmt stateID = asmt stateID
            join_11 = SQLJoinExpr(SQLTableExpr(join_10), OP_INNER_JOIN, tblasmstate,
                                  SQLBinaryExpr(SQLColumnExpr(aliasasmt, COL_NAME_ASS_ASSSTID),
                                                OP_EQ,
                                                SQLColumnExpr(aliasasmstate, COL_NAME_ASSESSMENT_STATE_ASSID)))

            table_list = [join_11]

        cond_flt = None
        if filt_stat is not None:
            table_list[0], cond_flt = self._get_filter_joins(filt_stat, table_list[0])

        if cond_flt is not None:
            where = SQLBinaryExpr(where, OP_AND, cond_flt)

        entries = self.select_generic_data_compact(select_list=select_list, table_list=table_list, where=where,
                                                   distinct_rows=True,
                                                   order_by=[SQLColumnExpr(aliasevents, COL_NAME_EVENTS_MEASID),
                                                             SQLColumnExpr(aliasevents, COL_NAME_EVENTS_EVENTTYPEID),
                                                             SQLColumnExpr(aliasevents, COL_NAME_EVENTS_SEID)])
        return entries, image_attribs

    def _get_filter_joins(self, filt_str, join):  # pylint: disable=R0912
        """
        Generate Inner joins for custom filter

        :param filt_str: Filter Statement
        :param join: Existing inner join
        :type join: `SQLJoinExpr`
        :return: SQL Innert join
        :rtype: `SQLJoinExpr`
        """
        count = 1
#         sql_select_stmt = ""
        aliasevents = "ev"
        aliaseventtype = "et"
        aliasasmstate = "asmtst"
#         statement = [{"field": "vehspeed", "comparitor": ">", "value": "22.22", "vtype": "float"}, "and",
#                     {"field": "assessment", "comparitor":"=", "value": "Invalid", "vtype": "str"}

        where = None
        bin_join = ""
        for filt in filt_str:

            if type(filt) is dict:
                aliaseventdet = "ed%s" % (str(count))
                tbleventdet = SQLTableExpr(TABLE_NAME_EVENT_DETAILS, aliaseventdet)
                aliaseventattr = "ea1%s" % (str(count))
                tbleventattr = SQLTableExpr(TABLE_NAME_EVENT_ATTR, aliaseventattr)
                aliaseventattrtype = "eat%s" % (str(count))
                tblattrtypes = SQLTableExpr(TABLE_NAME_EVENT_ATTR_TYPES,
                                            aliaseventattrtype)

                stmt = "SELECT %s from " % str(SQLColumnExpr(aliaseventdet, COL_NAME_EVENT_DET_SEID))

                if "field" in filt and "value" in filt and "comparitor" in filt:
                    if filt["field"].lower() == "eventtype":

                        if where is None:
                            where = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                              SQLColumnExpr(aliaseventtype, COL_NAME_EVENTTYPE_NAME)),
                                                  filt["comparitor"], SQLLiteral(filt["value"].lower()))
                        else:
                            where = SQLBinaryExpr(where, bin_join,
                                                  SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                                            SQLColumnExpr(aliaseventtype,
                                                                                          COL_NAME_EVENTTYPE_NAME)),
                                                                filt["comparitor"], SQLLiteral(filt["value"].lower())))

                    elif filt["field"].lower() == "assessment":
                        if where is None:
                            where = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                              SQLColumnExpr(aliasasmstate,
                                                                            COL_NAME_ASSESSMENT_STATE_NAME)),
                                                  filt["comparitor"], SQLLiteral(filt["value"].lower()))

                        else:
                            where = SQLBinaryExpr(where, bin_join,
                                                  SQLBinaryExpr(SQLColumnExpr(aliasasmstate,
                                                                              COL_NAME_ASSESSMENT_STATE_NAME),
                                                                filt["comparitor"], SQLLiteral(filt["value"])))

                    elif filt["field"].lower() == "duration":

                        field_name = SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_VIEW_ENDABSTS), OP_SUB,
                                                   SQLColumnExpr(aliasevents, COL_NAME_EVENTS_VIEW_BEGINABSTS))

                        if where is None:
                            where = SQLBinaryExpr(field_name, filt["comparitor"], filt["value"])
                        else:
                            where = SQLBinaryExpr(where, bin_join, SQLBinaryExpr(field_name, filt["comparitor"],
                                                                                 filt["value"]))

                    elif filt["field"].lower() == "measid":
                        if where is None:
                            where = SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_MEASID),
                                                  filt["comparitor"], filt["value"])

                        else:
                            where = SQLBinaryExpr(where, bin_join,
                                                  SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_MEASID),
                                                                filt["comparitor"], filt["value"]))

                    elif len(self.get_event_attribute_type(str(filt["field"]))) > 0:
                        join_2 = SQLJoinExpr(SQLTableExpr(tbleventdet), OP_INNER_JOIN, tbleventattr,
                                             SQLBinaryExpr(SQLColumnExpr(aliaseventdet, COL_NAME_EVENT_DET_EDID),
                                                           OP_EQ,
                                                           SQLColumnExpr(aliaseventattr, COL_NAME_EVENT_ATTR_EDID)))

                        cond = SQLBinaryExpr(SQLColumnExpr(aliaseventattr, COL_NAME_EVENT_ATTR_ATTRTYPEID), OP_EQ,
                                             SQLColumnExpr(aliaseventattrtype, COL_NAME_EVENT_ATTR_TYPES_ATTRTYPEID))

                        cond1 = SQLBinaryExpr(SQLColumnExpr(aliaseventattrtype, COL_NAME_EVENT_ATTR_TYPES_NAME),
                                              OP_EQ, SQLLiteral(filt["field"].lower()))

                        if filt["vtype"] == "str":
                            value = SQLLiteral(filt["value"].lower())
                        else:
                            value = filt["value"]

                        cond2 = SQLBinaryExpr(SQLColumnExpr(aliaseventattr, COL_NAME_EVENT_ATTR_VALUE),
                                              filt["comparitor"], value)

                        cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(cond1, OP_AND, cond2))

                        join_3 = SQLJoinExpr(SQLTableExpr(join_2), OP_INNER_JOIN, tblattrtypes, cond)

                        join_alias = "Q" + str(count)
                        join_alias_1 = "Q" + str(count - 1)

                        stmt = "(%s %s )" % (stmt, join_3)
                        if count == 1:

                            join = SQLJoinExpr(join, OP_INNER_JOIN, SQLTableExpr(stmt, join_alias),
                                               SQLBinaryExpr(SQLColumnExpr(aliasevents, COL_NAME_EVENTS_SEID), OP_EQ,
                                                             (SQLColumnExpr(join_alias, COL_NAME_EVENT_DET_SEID))))
                        else:
                            join = SQLJoinExpr(join, OP_INNER_JOIN, SQLTableExpr(stmt, join_alias),
                                               SQLBinaryExpr(SQLColumnExpr(join_alias_1, COL_NAME_EVENTS_SEID), OP_EQ,
                                                             (SQLColumnExpr(join_alias, COL_NAME_EVENT_DET_SEID))))
                        count += 1
                bin_join = ""
            else:

                bin_join = filt
        return join, where

    def get_events_attributes_view(self, seid=None, trid=None, measid=None,  # pylint: disable=R0913
                                   beginabsts=None, endabsts=None, start_idx=None,
                                   stop_idx=None, assessment=None, eventtype=None, rdid=None, cond=None):
        """
        Get Event list from Event Attribute View

        based filter criteria of passed argument
        if the argument cond is passed then other argument will be suppressed will be use as filter
        criteria

        :param seid: event Id
        :type seid: int
        :param trid: Testrun Id
        :type trid: int
        :param measid: Measurement Id
        :type measid: int
        :param beginabsts: Event Begin abs timestamp
        :type beginabsts: int
        :param endabsts:  Event Ending abs timestamp
        :type endabsts: int
        :param start_idx: Index of Event Begin abs timestamp
        :type start_idx: int
        :param stop_idx:  Index of Event Ending abs timestamp
        :type stop_idx: int
        :param assessment: Assessment State
        :type assessment: String
        :param eventtype: event Type name
        :type eventtype: string
        :param rdid: result descriptor Id
        :type rdid: int
        :param cond: where condition
        :type cond: SQLBinaryExpression
        """
        entries = []
        if cond is None:
            cond = self._get_event_condition(table_name=TABLE_NAME_EVENTS_VIEW,
                                             seid=seid, trid=trid, measid=measid,
                                             beginabsts=beginabsts, endabsts=endabsts,
                                             start_idx=start_idx, stop_idx=stop_idx,
                                             assessment=assessment, eventtype=eventtype, rdid=rdid)

        if cond is not None:
            entries = self.select_generic_data(table_list=[TABLE_NAME_EVENTS_ATTRIBUTES_VIEW], where=cond)

        # done
        return entries

    def get_event_types_view(self, trid=None):
        """Get List of Eventtype name used in given test run

        :param trid: testrun Id
        :type trid: int
        """
        entries = []
        cond = self._get_event_condition(table_name=TABLE_NAME_EVENTS_VIEW, trid=trid)

        columns = [COL_NAME_EVENTS_VIEW_EVENTTYPE]
        if cond is not None:
            entries = self.select_generic_data(distinct_rows=True,
                                               select_list=columns,
                                               table_list=[TABLE_NAME_EVENTS_VIEW],
                                               where=cond)
        # done
        return entries

    def get_events_view(self, seid=None, trid=None, measid=None, beginabsts=None,
                        endabsts=None, start_idx=None, stop_idx=None,
                        assessment=None, eventtype=None, rdid=None, cond=None):
        """
        Get Event list from Event View based on filter criteria of passed argument

        cond is also passed then other argument will be suppressed in filter criteria

        :param seid: Event id
        :type seid: int
        :param trid: TestRun Id
        :type trid: int
        :param measid: Measurement Id
        :type measid: int
        :param beginabsts: Begin ABS timestamp
        :type beginabsts: int
        :param endabsts: Ending ABS timestamp
        :type endabsts: int
        :param start_idx: Index of Begin ABS timestamp
        :type start_idx: int
        :param stop_idx: Index of Ending ABS timestamp
        :type stop_idx: int
        :param assessment: Assessment State
        :type assessment: String
        :param eventtype: Event Type name
        :type eventtype: String
        :param rdid: Result Descriptor Id
        :type rdid: int
        :param cond: SQL condition
        :type cond: SQLBinaryExpression
        """
        # pylint: disable=R0913
        entries = []
        if cond is None:
            cond = self._get_event_condition(table_name=TABLE_NAME_EVENTS_VIEW,
                                             seid=seid, trid=trid, measid=measid,
                                             beginabsts=beginabsts, endabsts=endabsts,
                                             start_idx=start_idx, stop_idx=stop_idx,
                                             assessment=assessment,
                                             eventtype=eventtype, rdid=rdid)

        if cond is not None:
            entries = self.select_generic_data(table_list=[TABLE_NAME_EVENTS_VIEW], where=cond)

        # done
        return entries

    def get_events(self, seid=None, trid=None, event_type_id=None, measid=None,
                   beginabsts=None, endabsts=None, start_idx=None, stop_idx=None,
                   resass_id=None):
        """Get Event from Val_Events Table

        :param seid:
        :param trid:
        :param event_type_id:
        :param measid:
        :param beginabsts:
        :param endabsts:
        :param start_idx:
        :param stop_idx:
        :param resass_id:
        :return: Returns the Event record
        """
        # pylint: disable=R0913
        entries = []
        cond = self._get_event_condition(seid=seid, trid=trid,
                                         event_type_id=event_type_id, measid=measid,
                                         beginabsts=beginabsts, endabsts=endabsts,
                                         start_idx=start_idx, stop_idx=stop_idx,
                                         resass_id=resass_id)

        if cond is not None:
            entries = self.select_generic_data(table_list=[TABLE_NAME_EVENTS], where=cond)

        # done
        return entries

    def update_event(self, event, where=None):
        """Update existing event records.

        :param event: The event record update.
        :param where:
        :return: number of affected result descriptors.
        """
        rowcount = None

        if not isinstance(event, dict):
            raise AdasDBError("UpdateEvent: event is not a dictionary!")

        if where is None:
            try:
                where = self._get_event_condition(seid=event[COL_NAME_EVENTS_SEID])
            except KeyError, ex:
                raise AdasDBError("Couldn't generate EventCondition. %s" % str(ex))

        if (event is not None) and (len(event) != 0):
            rowcount = self.update_generic_data(event, TABLE_NAME_EVENTS, where)
        # done
        return rowcount

    def delete_event(self, seid):
        """Delete existing event record.

        :param seid: The event record update.
        :return: number of affected result descriptors.
        """
        try:
            seid = int(seid)
        except:
            raise AdasDBError("Seid is not an Integer")

        rowcount = 0
        # Delete the event details container
        try:
            rowcount += self.delete_event_details(seid)
            # Delete the event
            cond = self._get_event_condition(seid=seid)
            self.delete_generic_data(TABLE_NAME_EVENTS, where=cond)
            rowcount += 1
        except:
            raise AdasDBError("Event with seid '%i' cannot be deleted." % seid)

        return rowcount

    def _get_event_condition(self, table_name=None, seid=None, trid=None,  # pylint: disable=R0912,R0913
                             event_type_id=None, measid=None, beginabsts=None,
                             endabsts=None, start_idx=None, stop_idx=None,
                             resass_id=None, assessment=None, eventtype=None, rdid=None,
                             indx=None):
        """Get the condition expression to access the simeevnt.

        :param seid:
        :param trid:
        :param event_type_id:
        :param measid:
        :param beginabsts:
        :param endabsts:
        :param start_idx:
        :param stop_idx:
        :param resass_id:
        :return: Returns the condition expression
        """
        cond = None

        # todo: table_name is not used further more!
        if table_name is None:
            table_name = TABLE_NAME_EVENTS

        if seid is not None:
            cond = SQLBinaryExpr(COL_NAME_EVENTS_SEID, OP_EQ, seid)
        else:
            if trid is not None:
                cond_tr = SQLBinaryExpr(COL_NAME_EVENTS_TRID, OP_EQ, trid)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_tr)
                else:
                    cond = cond_tr

            if event_type_id is not None:
                cond_ev = SQLBinaryExpr(COL_NAME_EVENTS_EVENTTYPEID, OP_EQ, event_type_id)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_ev)
                else:
                    cond = cond_ev

            if beginabsts is not None:
                cond_b = SQLBinaryExpr(COL_NAME_EVENTS_BEGINABSTS, OP_EQ, beginabsts)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_b)
                else:
                    cond = cond_b

            if endabsts is not None:
                cond_e = SQLBinaryExpr(COL_NAME_EVENTS_ENDABSTS, OP_EQ, endabsts)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_e)
                else:
                    cond = cond_e

            if measid is not None:
                cond_m = SQLBinaryExpr(COL_NAME_EVENTS_MEASID, OP_EQ, measid)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_m)
                else:
                    cond = cond_m

            if start_idx is not None:
                cond_si = SQLBinaryExpr(COL_NAME_EVENTS_START_IDX, OP_EQ, start_idx)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_si)
                else:
                    cond = cond_si

            if stop_idx is not None:
                cond_sp = SQLBinaryExpr(COL_NAME_EVENTS_STOP_IDX, OP_EQ, stop_idx)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_sp)
                else:
                    cond = cond_sp

            if resass_id is not None:
                cond_r = SQLBinaryExpr(COL_NAME_EVENTS_RESASSID, OP_EQ, resass_id)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_r)
                else:
                    cond = cond_r

            if assessment is not None:
                cond_ass = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                     COL_NAME_EVENTS_VIEW_ASSESSMENT),
                                         OP_EQ, SQLLiteral(assessment.lower()))
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_ass)
                else:
                    cond = cond_ass

            if eventtype is not None:
                cond_evt = SQLBinaryExpr(COL_NAME_EVENTS_VIEW_EVENTTYPE, OP_EQ, SQLLiteral(eventtype))
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_evt)
                else:
                    cond = cond_evt

            if rdid is not None:
                cond_rd = SQLBinaryExpr(COL_NAME_EVENTS_VIEW_RDID, OP_EQ, rdid)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_rd)
                else:
                    cond = cond_rd

            if indx is not None:
                cond_indx = SQLBinaryExpr(COL_NAME_EVENTS_INDEX, OP_EQ, indx)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_indx)
                else:
                    cond = cond_indx
        return cond

    # --- EVENTTYPE Table. --------------------------------------------------
    def add_event_type(self, event_type):
        """Add a new event type to the database.

        :param event_type: The event type dictionary
        :return: Returns the event type ID.
        """
        try:
            cond = self._get_event_type_condition(None, event_type[COL_NAME_EVENTTYPE_CLASSNAME])
        except StandardError, ex:
            raise AdasDBError("Can't create eventtype condition. Error: '%s'" % (ex))

        entries = self.select_generic_data(table_list=[TABLE_NAME_EVENTTYPE], where=cond)
        if len(entries) <= 0:
            if COL_NAME_EVENTTYPE_NAME not in event_type:
                event_type[COL_NAME_EVENTTYPE_NAME] = 'auto generated name'

            if COL_NAME_EVENTTYPE_DESC not in event_type:
                event_type[COL_NAME_EVENTTYPE_DESC] = 'auto generated description'

            self.add_generic_data(event_type, TABLE_NAME_EVENTTYPE)
            etid = self.select_generic_data(table_list=[TABLE_NAME_EVENTTYPE], where=cond)[0][COL_NAME_EVENTTYPE_ID]
        else:
            tmp = "Event type '%s' " % event_type[COL_NAME_EVENTTYPE_NAME]
            tmp += "exists already in the validation database"
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError(tmp)
            else:
                self._log.warning(tmp)
                if len(entries) == 1:
                    etid = entries[0][COL_NAME_EVENTTYPE_ID]
                elif len(entries) > 1:
                    tmp = "Event type name '%s' " % (event_type[COL_NAME_TR_NAME])
                    tmp += "cannot be resolved because it is ambiguous. "
                    tmp += "(%s)" % (entries)
                    raise AdasDBError(tmp)
        # done
        return int(etid)

    def get_event_type(self, event_type_id=None, name=None, class_name=None):
        """Get existing event type records.

        :param event_type_id:
        :param name: - The event type name.
        :param class_name: The event Class Name
        :return: Returns the event type record.
        """
        record = {}
        try:
            if event_type_id is not None:
                event_type_id = int(event_type_id)
        except:
            raise AdasDBError("Eventtype ID is not an integer.")

        if class_name is None and event_type_id is None:
            raise AdasDBError("Classname and eventtype id are None of event_type_id is not an integer.")

        # if event_type_id is None:
            # if not isinstance(event_type_id, (int, float, long)):
        #    raise AdasDBError("event_type_id is not an integer.")

        cond = self._get_event_type_condition(event_type_id, class_name, name)

        entries = self.select_generic_data(table_list=[TABLE_NAME_EVENTTYPE], where=cond)
        if len(entries) <= 0:
            self._log.info(str("Event type '%s' does not exist in the validation result database." % name))
        elif len(entries) > 1:
            self._log.warning(str("Event type '%s' cannot be resolved because it is ambiguous. (%s)"
                                  % (name, entries)))
        else:
            record = entries[0]
        # done
        return record

    def get_event_type_id(self, class_name=None, name=None):
        """ Get the EventType ID

        :param name: Event Type Name
        :param class_name: The event Class Name
        :return: Returns the Event Type IDcondition expression
        """
        if name is None and class_name in self._eventtypeid_cache:
            return self._eventtypeid_cache[class_name]
        eventtype = self.get_event_type(class_name=class_name, name=name)
        if COL_NAME_EVENTTYPE_ID in eventtype:
            self._eventtypeid_cache[class_name] = int(eventtype[COL_NAME_EVENTTYPE_ID])
            return self._eventtypeid_cache[class_name]
        else:
            return None

    def update_event_type(self, event_type, where=None):
        """Update existing event type records.

        :param event_type: The event type record update.
        :param where: The condition to be fulfilled by the event type to the updated.
        :return: Returns the number of affected event types.
        """
        rowcount = None
        if not isinstance(event_type, dict):
            raise AdasDBError("event_type parameter is not a dictionary!")

        if COL_NAME_EVENTTYPE_CLASSNAME not in event_type:
            raise AdasDBError("UpdateEventType: classname not set.")

        if where is None:
            where = self._get_event_type_condition(None, class_name=event_type[COL_NAME_EVENTTYPE_CLASSNAME])

        if (event_type is not None) and (len(event_type) != 0):
            rowcount = self.update_generic_data(event_type, TABLE_NAME_EVENTTYPE, where)
        # done
        return rowcount

    def delete_event_type(self, event_type):
        """Delete existing event type records.

        :param event_type: - The event type record to delete.
        :return: Returns the number of affected event types.
        """
        rowcount = None
        if not isinstance(event_type, dict):
            raise AdasDBError("event_type parameter is not a dictionary!")

        if (event_type is not None) and (len(event_type) != 0):
            try:
                cond = self._get_event_type_condition(class_name=event_type[COL_NAME_EVENTTYPE_CLASSNAME])
            except:
                raise AdasDBError("DeleteEventType: Couldn't generate EventTypeCondition.")

            rowcount = self.delete_generic_data(TABLE_NAME_EVENTTYPE, where=cond)
        # done
        return rowcount

    def _get_event_type_condition(self, event_type_id=None, class_name=None, name=None):
        """Get the condition expression to access the event type record

        :param name: Event Type ID
        :return: Returns the condition expression
        """
        cond = None
        if event_type_id is not None:
            cond = SQLBinaryExpr(COL_NAME_EVENTTYPE_ID, OP_EQ, event_type_id)
        else:
            if class_name is not None:
                cond_class = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                       COL_NAME_EVENTTYPE_CLASSNAME),
                                           OP_EQ, SQLLiteral(class_name.lower()))
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_class)
                else:
                    cond = cond_class

            if name is not None:
                cond_name = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                      COL_NAME_EVENTTYPE_NAME),
                                          OP_EQ, SQLLiteral(name.lower()))
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_name)
                else:
                    cond = cond_name

        return cond

    # --- RESULTTYPE Table. --------------------------------------------------
    def add_result_type(self, result_type):
        """Add a new result type to the database.

        :param result_type: The result type dictionary
        :return: Returns the testrun ID.
        """
        sql_param, cond = self._get_result_type_condition(result_type[COL_NAME_RESULTTYPE_NAME])
        entries = self.select_generic_data(table_list=[TABLE_NAME_RESULTTYPE], where=cond, sqlparams=sql_param)
        if len(entries) <= 0:
            self.add_generic_data(result_type, TABLE_NAME_RESULTTYPE)
            rtid = self.select_generic_data(table_list=[TABLE_NAME_RESULTTYPE], where=cond,
                                            sqlparams=sql_param)[0][COL_NAME_RESULTTYPE_ID]
        else:
            tmp = "Result type '%s' " % result_type[COL_NAME_RESULTTYPE_NAME]
            tmp += "exists already in the validation result database"
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError(tmp)
            else:
                self._log.warning(tmp)
                if len(entries) == 1:
                    rtid = entries[0][COL_NAME_RESULTTYPE_ID]
                elif len(entries) > 1:
                    tmp = "Result type name '%s' " % (result_type[COL_NAME_RESULTTYPE_NAME])
                    tmp += "cannot be resolved because it is ambiguous. "
                    tmp += "(%s)" % (entries)
                    raise AdasDBError(tmp)
        # done
        return int(rtid)

    def update_result_type(self, result_type, where=None):
        """Update existing result type records.

        :param result_type: The result type record update.
        :param where: The condition to be fulfilled by the result type to the updated.
        :return: Returns the number of affected result types.
        """
        rowcount = 0

        if where is None:
            sql_param, where = self._get_result_type_condition(result_type[COL_NAME_RESULTTYPE_NAME])

        if (result_type is not None) and (len(result_type) != 0):
            rowcount = self.update_generic_data(result_type, TABLE_NAME_RESULTTYPE, where=where, sqlparams=sql_param)
        # done
        return rowcount

    def delete_result_type(self, result_type):
        """Delete existing result type records.

        :param result_type: - The result type record to delete.
        :return: Returns the number of affected resulttypes.
        """
        rowcount = 0
        if (result_type is not None) and (len(result_type) != 0):
            sql_param, cond = self._get_result_type_condition(result_type[COL_NAME_RESULTTYPE_NAME])
            rowcount = self.delete_generic_data(TABLE_NAME_RESULTTYPE, where=cond, sqlparams=sql_param)
        # done
        return rowcount

    def get_result_type(self, name):
        """Get existing result type records.

        :param name: - The result type name.
        :return: Returns the result type record.
        """
        record = {}
        sql_param, cond = self._get_result_type_condition(name)

        entries = self.select_generic_data(table_list=[TABLE_NAME_RESULTTYPE], where=cond, sqlparams=sql_param)
        if len(entries) <= 0:
            tmp = "Result type with name '%s' " % name
            tmp += "does not exist in the validation result database."
            self._log.info(tmp)
        elif len(entries) > 1:
            tmp = "Result type with name '%s' " % (name)
            tmp += "cannot be resolved because it is ambiguous. "
            tmp += "(%s)" % entries
            self._log.warning(tmp)
        else:
            record = entries[0]
        # done
        return record

    def get_result_type_id(self, name):
        """ Get the resultType ID

        :param name: result Type Name
        :return: Returns the result Type IDcondition expression
        """
        if name in self._restypeid_by_cache:
            return self._restypeid_by_cache[name]

        resulttype = self.get_result_type(name)
        if COL_NAME_RESULTTYPE_ID in resulttype:
            self._restypeid_by_cache[name] = int(resulttype[COL_NAME_RESULTTYPE_ID])
            return self._restypeid_by_cache[name]
        else:
            return None

    def get_result_type_by_id(self, res_id):
        """ Get the resultType ID

        :param res_id: result id
        :return: Returns the result Type IDcondition expression
        """
        sql_param, cond = self._get_result_type_condition(res_id=res_id)
        entries = self.select_generic_data(table_list=[TABLE_NAME_RESULTTYPE], where=cond, sqlparams=sql_param)
        if len(entries) == 1:
            return entries[0]
        else:
            tmp = "Result Type does not exist in the reult database"
            if self.error_tolerance <= ERROR_TOLERANCE_LOW:
                raise AdasDBError(tmp)
            self._log.warning(tmp)

    def _get_result_type_condition(self, name=None, res_id=None):
        """Get the condition expression to access the result type record

        :param name: result Type ID
        :return: Returns the condition expression
        """
        sql_param = {}
        cond = None
        if res_id is not None:
            sql_param = {str(len(sql_param) + 1): res_id}
            cond = SQLBinaryExpr(COL_NAME_RESULTTYPE_ID, OP_EQ, ":%d" % (len(sql_param)))
        else:
            sql_param = {str(len(sql_param) + 1): name.lower()}
            cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                             COL_NAME_RESULTTYPE_NAME),
                                 OP_EQ, ":%d" % (len(sql_param)))

        return sql_param, cond

    # --- KEYS Table. ----------------------------------------------------------
    def add_val_rev_key(self, name, description):
        """Add a new result revision key to the database.

        :param name: Result revision key Name.
        :param description: Result revision key Description.
        :return: Returns the new result revision key ID.
        """
        tr_id = None
        rec = {}
        rec[COL_NAME_VRKEY_NAME] = name
        rec[COL_NAME_VRKEY_DESCRIPTION] = description

        entries = self.get_val_rev_key(name)
        if len(entries) <= 0:
            self.add_generic_data(rec, TABLE_NAME_VRKEY)
        else:
            tmp = "Result revision key '%s' " % rec[COL_NAME_VRKEY_NAME]
            tmp += "exists already in the validation result database"
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError(tmp)
            else:
                self._log.warning(tmp)
                if len(entries) == 1:
                    tr_id = entries[0][COL_NAME_VRKEY_ID]
                elif len(entries) > 1:
                    tmp = "Result revision key '%s' " % (rec[COL_NAME_VRKEY_NAME])
                    tmp += "cannot be resolved because it is ambiguous. "
                    tmp += "(%s)" % (entries)
                    raise AdasDBError(tmp)

        # done
        return tr_id

    def delete_val_rev_key(self, name):
        """Delete existing result revision key records.

        :param name: Result revision key Name.
        :return: Returns the number of affected records.
        """
        rowcount = 0
        if (name is not None) and (len(name) != 0):
            entries = self.get_val_rev_key(name)
            if len(entries) == 1:
                # delete revision key mapping if exists
                val_rev_key = entries[0][COL_NAME_VRKEY_ID]
                self.delete_val_rev_key_constraint(val_rev_key)

                # delete revision key if exists
                cond = self._get_val_rev_key_condition(val_rev_key, None)
                rowcount = self.delete_generic_data(TABLE_NAME_VRKEY, where=cond)

        # done
        return rowcount

    def update_val_rev_key(self, rec, where=None):
        """Update existing Result revision key record.

        :param rec: The Result revision key record.
        :param where: The condition to be fulfilled by the result type to the updated.
        :return: Returns the number of affected records.
        """
        rowcount = 0
        if (rec is not None) and (len(rec) != 0):
            if where is None:
                where = self._get_val_rev_key_condition(rec[COL_NAME_VRKEY_ID], None)
            rowcount = self.update_generic_data(rec, TABLE_NAME_VRKEY, where)

        # done
        return rowcount

    def get_val_rev_key(self, name):
        """Get existing result revision key records.

        :param name: Result revision key Name.
        :return: Returns the result revision key records.
        """
        # entries = {}
        cond = self._get_val_rev_key_condition(None, name)
        entries = self.select_generic_data(table_list=[TABLE_NAME_VRKEY], where=cond)
        if len(entries) <= 0:
            tmp = "Result Revision Key with name '%s' " % (name)
            tmp += "does not exist in the validation result database."
            self._log.warning(tmp)
        elif len(entries) > 1:
            tmp = "Result Revision Key with name '%s' " % (name)
            tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
            self._log.warning(tmp)

        # done
        return entries

    def get_val_rev_key_id(self, name):
        """Get existing result revision key record ID.

        :param name: Result revision key Name.
        :return: Returns the ID of the found result revision key.
        """
        kid = None
        entries = self.get_val_rev_key(name)
        if len(entries) == 1:
            kid = entries[0][COL_NAME_VRKEY_ID]

        # done
        return kid

    def _get_val_rev_key_condition(self, val_rev_key=None, name=None):
        """Get the condition expression to access the result record

        :param val_rev_key: Result revision key ID.
        :param name: Result revision key Name.
        :return: Returns the condition expression.
        """
        cond = None
        if val_rev_key is not None:
            cond = SQLBinaryExpr(COL_NAME_VRKEY_ID, OP_EQ, SQLLiteral(val_rev_key))

        if name is not None:
            cond_lb = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                COL_NAME_VRKEY_NAME),
                                    OP_EQ,
                                    SQLLiteral(name.lower()))
            if cond is not None:
                cond = SQLBinaryExpr(cond, OP_AND, cond_lb)
            else:
                cond = cond_lb

        # done
        return cond

    # --- CONSTRAINTSMAP Table. ---------------------------------------------------
    def add_val_rev_key_constraint(self, val_rev_key, rdid):
        """Add a new result revision key - result descriptor record to the database.

        :param val_rev_key: The result revision key ID
        :param rdid: The result descriptor ID
        """
        rec = {}
        rec[COL_NAME_VRKEY_MAP_ID] = val_rev_key
        rec[COL_NAME_VRKEY_MAP_RDID] = rdid

        entries = self.get_val_rev_key_constraint(val_rev_key, rdid)
        if len(entries) <= 0:
            self.add_generic_data(rec, TABLE_NAME_VRKEY_MAP)
        else:
            tmp = "Link for Result revision key ID '%s' " % val_rev_key
            tmp += "and Result descriptor ID '%s' " % rdid
            tmp += "exists already in the validation result database"
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError(tmp)
            else:
                self._log.warning(tmp)
        # done

    def delete_val_rev_key_constraint(self, val_rev_key=None, rdid=None):
        """Delete existing result revision key - result descriptor record.

        :param val_rev_key: The result revision key ID (optional)
        :param rdid: The result descriptor ID (optional)
        :return: Returns the number of affected records.
        """
        # rowcount = 0
        cond = self._get_val_rev_key_constraintCondition(val_rev_key, rdid)
        rowcount = self.delete_generic_data(TABLE_NAME_VRKEY_MAP, where=cond)

        # done
        return rowcount

    def get_val_rev_key_constraint(self, val_rev_key=None, rdid=None):
        """Get existing result revision key - result descriptor records.

        :param val_rev_key: The result revision key ID (optional)
        :param rdid: The result descriptor ID (optional)
        :return: Records if exists
        """
        # entries = {}
        cond = self._get_val_rev_key_constraintCondition(val_rev_key, rdid)
        entries = self.select_generic_data(table_list=[TABLE_NAME_VRKEY_MAP], where=cond)
        if len(entries) <= 0:
            tmp = "Value for Result revision key ID '%s' " % val_rev_key
            tmp += "and Result descriptor ID '%s' " % rdid
            tmp += "doesn't exists in the validation result database"
            self._log.warning(tmp)

        # done
        return entries

    @staticmethod
    def _get_val_rev_key_constraintCondition(val_rev_key=None, rdid=None):  # pylint:disable=C0103
        """Get the condition expression to access the result record

        :param val_rev_key: The result revision key ID (optional)
        :param rdid: The result descriptor ID (optional)
        :return: Returns the condition expression
        """
        cond = None
        if val_rev_key is not None:
            cond = SQLBinaryExpr(COL_NAME_VRKEY_MAP_ID, OP_EQ, SQLLiteral(val_rev_key))

        if rdid is not None:
            cond_lb = SQLBinaryExpr(COL_NAME_VRKEY_MAP_RDID, OP_EQ, SQLLiteral(rdid))
            if cond is not None:
                cond = SQLBinaryExpr(cond, OP_AND, cond_lb)
            else:
                cond = cond_lb

        # done
        return cond

    # --- RESULT_DESC Table. --------------------------------------------------
    def add_result_descriptor_with_parent(self, rdtype, name, collect_id, unit_id,  # pylint: disable=C0103,R0913
                                          parent, ref_tag=None, doors_url="", exp_res="", desc=""):
        """ Add result descriptor

        :param rdtype: Result Descriptor type id
        :type rdtype: int
        :param name: Result descriptor name
        :type name: Str
        :param collect_id: collection id
        :type collect_id: int
        :param unit_id: unit Id correspond to unit name as defined in global unit table
        :type unit_id: int
        :param parent: parent Id of result descriptor. if this entry is child
        :type parent: int
        :param ref_tag: DOORS ID
        :type ref_tag: str
        :param doors_url: DOORS URL to test specification are located
        :type doors_url: str
        :param exp_res: pass fail criteria
        :type exp_res: str
        :param desc: one sentence description about the purpose of test
        :type desc: str
        :return: Primary key Result descriptor ID i.e. RDID
        :rtype: int
        """
        rd_record = self.get_result_descriptor_with_parent(collect_id, name, parent, ev_type_name=rdtype,
                                                           ref_tag=ref_tag)
        if len(rd_record) == 1:
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                tmp = "Result Descriptor '%s' " % name
                tmp += "exists already in the validation result database"
                raise AdasDBError(tmp)
            else:
                return rd_record[0][COL_NAME_RESDESC_ID]
        elif len(rd_record) == 0:
            res_des = {COL_NAME_RESDESC_NAME: name,
                       COL_NAME_RESDESC_COLLID: collect_id,
                       COL_NAME_RESDESC_UNIT_ID: unit_id,
                       COL_NAME_RESDESC_PARENT: parent,
                       COL_NAME_RESDESC_DOORS_URL: doors_url,
                       COL_NAME_RESDESC_EXPECTRES: exp_res,
                       COL_NAME_RESDESC_DESCRIPTION: desc}

            if ref_tag is None:
                res_des[COL_NAME_RESDESC_REFTAG] = ''
            else:
                res_des[COL_NAME_RESDESC_REFTAG] = ref_tag
            evnt = self.get_result_type(rdtype)
            if COL_NAME_RESULTTYPE_ID in evnt:
                res_des[COL_NAME_RESDESC_RESTYPE_ID] = evnt[COL_NAME_RESULTTYPE_ID]
            else:
                if self.error_tolerance < ERROR_TOLERANCE_LOW:
                    tmp = "Result Type '%s' " % rdtype
                    tmp += "doesn't exist in the validation result database. "
                    tmp += "Define a new one before adding the result descriptor"
                    raise AdasDBError(tmp)
                else:
                    tmp = "Result Type '%s' " % rdtype
                    tmp += "doesn't exist in the validation result database. "
                    tmp += "A new one without a description is generated"
                    self._log.info(tmp)
                    evnt = {COL_NAME_RESULTTYPE_NAME: rdtype,
                            COL_NAME_RESULTTYPE_DESC: 'auto generated type - change description'}
                    res_des[COL_NAME_RESDESC_RESTYPE_ID] = self.add_result_type(evnt)

            self.add_generic_data(res_des, TABLE_NAME_RESULT_DESC)
            rd_record = self.get_result_descriptor_with_parent(collect_id, name, parent, ev_type_name=rdtype,
                                                               ref_tag=ref_tag)
            return rd_record[0][COL_NAME_RESDESC_ID]
        else:
            tmp = "Result Descriptor name '%s' for collection id %s and parent id %s " % (name, collect_id, parent)
            tmp += "cannot be resolved because it is ambiguous."
            tmp += " (%s)" % name
            raise AdasDBError(tmp)

    def get_result_descriptor_with_parent(self, coll_id, name, parent, ev_type_id=None,  # pylint: disable=C0103,R0913
                                          ev_type_name=None, ref_tag=None):
        """TODO

        :param coll_id:
        :type coll_id:
        :param name:
        :type name:
        :param parent:
        :type parent:
        :param ev_type_id:
        :type ev_type_id:
        :param ev_type_name:
        :type ev_type_name:
        :param ref_tag:
        :type ref_tag:
        :return:
        :rtype:
        """
        if ev_type_id is None and ev_type_name is not None:
            ev_type_id = self.get_result_type_id(ev_type_name)

        if name is None:
            self._log.error("Result Descriptor name is undefined. Check the source code")

        sql_param, cond = self._get_res_desc_condition(coll_id, name, ev_type_id)
        if parent is not None:
            cond_parent = SQLBinaryExpr(COL_NAME_RESDESC_PARENT, OP_EQ, parent)
        else:
            cond_parent = SQLBinaryExpr(COL_NAME_RESDESC_PARENT, OP_IS, SQLNull())

        cond = SQLBinaryExpr(cond, OP_AND, cond_parent)

        if ref_tag is not None:
            cond_reftag = SQLBinaryExpr(COL_NAME_RESDESC_REFTAG, OP_EQ, SQLLiteral(ref_tag))
            cond = SQLBinaryExpr(cond, OP_AND, cond_reftag)

        record = self.select_generic_data(table_list=[TABLE_NAME_RESULT_DESC], where=cond, sqlparams=sql_param)

        return record

    def add_result_descriptor(self, rdtype, name, collect_id, unit_id, ref_tag=None, parent=None,
                              doors_url="", exp_res="", desc=""):
        """Add a new result descriptor to the database.
        TODO: description

        :param rdtype: Descriptor type
        :param name: Descriptor Name
        :param collect_id: Collection ID from CAT
        :param unit_id: Unit ID from GBL
        :param ref_tag:
        :param parent:
        :param doors_url:
        :param exp_res:
        :param desc:
        :return: Returns the result descriptor ID.
        """

        # pylint: disable=R0913
        res_des = {COL_NAME_RESDESC_NAME: name,
                   COL_NAME_RESDESC_COLLID: collect_id,
                   COL_NAME_RESDESC_UNIT_ID: unit_id,
                   COL_NAME_RESDESC_PARENT: parent,
                   COL_NAME_RESDESC_DOORS_URL: doors_url,
                   COL_NAME_RESDESC_EXPECTRES: exp_res,
                   COL_NAME_RESDESC_DESCRIPTION: desc}

        if ref_tag is None:
            res_des[COL_NAME_RESDESC_REFTAG] = ''
        else:
            res_des[COL_NAME_RESDESC_REFTAG] = ref_tag
        evnt = self.get_result_type(rdtype)
        if COL_NAME_RESULTTYPE_ID in evnt:
            res_des[COL_NAME_RESDESC_RESTYPE_ID] = evnt[COL_NAME_RESULTTYPE_ID]
        else:
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                tmp = "Result Type '%s' " % rdtype
                tmp += "doesn't exist in the validation result database. "
                tmp += "Define a new one before adding the result descriptor"
                raise AdasDBError(tmp)
            else:
                tmp = "Result Type '%s' " % rdtype
                tmp += "doesn't exist in the validation result database. "
                tmp += "A new one without a description is generated"
                self._log.info(tmp)
                evnt = {COL_NAME_RESULTTYPE_NAME: rdtype,
                        COL_NAME_RESULTTYPE_DESC: 'auto generated type - change description'}
                res_des[COL_NAME_RESDESC_RESTYPE_ID] = self.add_result_type(evnt)

        rdid = self._add_result_descriptor(res_des)
        return rdid

    def _add_result_descriptor(self, res_desc):
        """Add a new result descriptor to the database.

        :param res_desc: The result description dictionary - name, collid and result type id are mandatory
        :return: Returns the result descriptor ID.
        """
        sql_param, cond = self._get_res_desc_condition(res_desc[COL_NAME_RESDESC_COLLID],
                                                       res_desc[COL_NAME_RESDESC_NAME],
                                                       res_desc[COL_NAME_RESDESC_RESTYPE_ID],
                                                       parent_id=res_desc[COL_NAME_RESDESC_PARENT])
        entries = self.select_generic_data(table_list=[TABLE_NAME_RESULT_DESC], where=cond, sqlparams=sql_param)
        if len(entries) <= 0:
            res_desc[COL_NAME_RESDESC_ID] = None
            self.add_generic_data(res_desc, TABLE_NAME_RESULT_DESC)
            entries = self.select_generic_data(table_list=[TABLE_NAME_RESULT_DESC], where=cond, sqlparams=sql_param)
            if len(entries) == 1:
                return entries[0][COL_NAME_RESDESC_ID]
            else:
                raise AdasDBError("Result Descriptor could not be added ")
        else:
            tmp = "Result Descriptor '%s' " % res_desc[COL_NAME_RESDESC_NAME]
            tmp += "exists already in the validation result database"
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError(tmp)
            else:
                self._log.warning(tmp)
                if len(entries) == 1:
                    return entries[0][COL_NAME_RESDESC_ID]
                elif len(entries) > 1:
                    tmp = "Result Descriptor name '%s' " % (res_desc[COL_NAME_RESDESC_NAME])
                    tmp += "cannot be resolved because it is ambiguous."
                    tmp += " (%s)" % entries
                    raise AdasDBError(tmp)
        # done
        return

    def delete_result_descriptor(self, res_desc):
        """Delete existing result type records.

        :param res_desc: The result description record to delete.
        :return: Returns the number of affected result types.
        """
        cond, sql_param = None, None
        if (res_desc is not None) and (len(res_desc) != 0):
            sql_param, cond = self._get_res_desc_condition(res_desc[COL_NAME_RESDESC_COLLID],
                                                           res_desc[COL_NAME_RESDESC_NAME],
                                                           res_desc[COL_NAME_RESDESC_RESTYPE_ID])
        rowcount = self.delete_generic_data(TABLE_NAME_RESULT_DESC, where=cond, sqlparams=sql_param)
        # done
        return rowcount

    def get_result_descriptor(self, coll_id, name, ev_type_id=None, ev_type_name=None, parent_id=None):
        """Get existing result type records.

        :param name: The result descriptor name.
        :param coll_id: The collection id (testcase).
        :param ev_type_id: The result type identifier.
        :return: Returns the result type record.
        """
        record = {}
        if ev_type_id is None and ev_type_name is not None:
            ev_type_id = self.get_result_type_id(ev_type_name)

        if name is None:
            self._log.error("Result Descriptor name is undefined. Check the source code")

        sql_param, cond = self._get_res_desc_condition(coll_id, name, ev_type_id, parent_id=parent_id)
        entries = self.select_generic_data(table_list=[TABLE_NAME_RESULT_DESC], where=cond, sqlparams=sql_param)
        if len(entries) <= 0:
            tmp = "Result Descriptor with name '%s' " % name
            tmp += "in collection '%s' " % coll_id
            tmp += "does not exist in the validation result database."
            self._log.info(tmp)
        else:
            record = entries

        # done
        return record

    def get_result_descriptor_with_id(self, rd_id):
        """Get existing result type records.

        :param rd_id: Result descriptor id
        :return: Returns the result descriptor record.
        """
        record = {}
        if rd_id is None:
            self._log.warning("Result Descriptor id not defined")
            return record

        tblnamed = TABLE_NAME_RESULT_DESC
        tblnamer = TABLE_NAME_RESULTTYPE

        cond = SQLBinaryExpr(COL_NAME_RESDESC_ID, OP_EQ, rd_id)
        tables = []
        tables.append(SQLJoinExpr(SQLTableExpr(tblnamed),
                                  OP_INNER_JOIN,
                                  SQLTableExpr(tblnamer),
                                  SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblnamed), COL_NAME_RESDESC_RESTYPE_ID),
                                                OP_EQ,
                                                SQLColumnExpr(SQLTableExpr(tblnamer), COL_NAME_RESULTTYPE_ID))))
        select_list = []
        select_list.append(SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblnamed),
                                                       COL_NAME_RESDESC_NAME),
                                         OP_AS, COL_NAME_RESDESC_NAME))
        select_list.append(SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblnamed),
                                                       COL_NAME_RESDESC_COLLID),
                                         OP_AS, COL_NAME_RESDESC_COLLID))
        select_list.append(SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblnamed),
                                                       COL_NAME_RESDESC_REFTAG),
                                         OP_AS, COL_NAME_RESDESC_REFTAG))
        select_list.append(SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblnamer),
                                                       COL_NAME_RESULTTYPE_NAME),
                                         OP_AS, "TYPE_" + COL_NAME_RESULTTYPE_NAME))
        select_list.append(SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblnamer),
                                                       COL_NAME_RESULTTYPE_CLASS),
                                         OP_AS, COL_NAME_RESULTTYPE_CLASS))
        select_list.append(SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblnamed),
                                                       COL_NAME_RESDESC_UNIT_ID),
                                         OP_AS, COL_NAME_RESDESC_UNIT_ID))
        select_list.append(SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblnamed),
                                                       COL_NAME_RESDESC_PARENT),
                                         OP_AS, COL_NAME_RESDESC_PARENT))
        select_list.append(SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblnamed),
                                                       COL_NAME_RESDESC_DOORS_URL),
                                         OP_AS, COL_NAME_RESDESC_DOORS_URL))
        select_list.append(SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblnamed),
                                                       COL_NAME_RESDESC_EXPECTRES),
                                         OP_AS, COL_NAME_RESDESC_EXPECTRES))
        select_list.append(SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblnamed),
                                                       COL_NAME_RESDESC_DESCRIPTION),
                                         OP_AS, COL_NAME_RESDESC_DESCRIPTION))

        entries = self.select_generic_data(select_list=select_list, table_list=tables, where=cond)
        if len(entries) <= 0:
            self._log.debug("Result Descriptor with id '%s' does not exist in the validation result database."
                            % str(rd_id))
        elif len(entries) > 1:
            self._log.warning("Result Descriptor with id '%s' cannot be resolved because it is ambiguous. (%s)"
                              % str(rd_id))
        else:
            record = entries[0]
        # done
        return record

    def get_result_descriptor_id(self, coll_id, name, ev_type_id=None, ev_type_name=None, parent_id=None):
        """ Get the Result Descriptor ID

        :param coll_id: Collection ID
        :param name: Name of the Descriptor
        :param ev_type_id: Event Type ID (optional)
        :param ev_type_name: Name of the Event Type (optional)
        """
        if name is None:
            tmp = "Result Descriptor with name '%s' " % name
            tmp += "does not exist in the validation result database."
            self._log.warning(tmp)

        result = self.get_result_descriptor(coll_id, name, ev_type_id, ev_type_name, parent_id)
        if len(result) <= 0:
            tmp = "Result Descriptor with name '%s' " % name
            tmp += "does not exist in the validation result database."
            self._log.info(tmp)
        elif len(result) > 1:
            tmp = "Result Descriptor with name '%s' " % name
            tmp += "cannot be resolved because it is ambiguous."
            tmp += " (%s)" % result
            self._log.warning(tmp)
        else:
            return result[0][COL_NAME_RESDESC_ID]
        return None

    def get_result_descriptor_id_list(self, name, coll_id_list, ev_type_id=None, ev_type_name=None):
        """ Get the List of Result Descriptor IDs

        :param name: Name of the Descriptor
        :param coll_id_list: List of Collections
        :param ev_type_id: Event Type ID (optional)
        :param ev_type_name: Name of the Event Type (optional)
        """
        result = []
        select_list = [COL_NAME_RESDESC_ID]
        if ev_type_id is None and ev_type_name is not None:
            ev_type_id = self.get_result_type_id(ev_type_name)

        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                             COL_NAME_RESDESC_NAME),
                             OP_EQ,
                             SQLLiteral(name.lower()))

        if ev_type_id is not None:
            query = ','.join(str(n) for n in coll_id_list)
            cond_col = SQLBinaryExpr(COL_NAME_RESDESC_COLLID, OP_IN, "(%s)" % query)
            cond = SQLBinaryExpr(cond, OP_AND, cond_col)
        else:
            raise AdasDBError("Event type %s not defined" % (ev_type_name))

        entries = self.select_generic_data(select_list, table_list=[TABLE_NAME_RESULT_DESC], where=cond)

        for res in entries:
            result.append(res[COL_NAME_RESDESC_ID])

        return result

    def get_result_descriptor_info_for_testrun(self, tr_name=None, tr_checkpoint=None,  # pylint:disable=C0103,R0913
                                               res_type_name=None, select_list=None, where=None, incl_del=False):
        """ Get the List of Result Descriptor IDs

        select * from val_resulttypes rt
            inner join val_resultdescriptor rd on rd.restypeid = rt.restypeid
            inner join val_result vr on vr.rdid = rd.rdid
            inner join val_testrun tr on tr.trid = vr.trid where rt.name = 'VAL_TESTCASE' and tr.is_deleted=0;

        :param tr_name: Name of the Testrun
        :param tr_checkpoint: Testrun checkpoint
        :param res_type_name:
        :param select_list: customized select list
        :param where: customized where condition overwrites the given parameters
        :param incl_del: include the deleted testruns as well. By default, the current valid TR will be returned
        """
        alias_table_name_result_desc = 'rd'
        alias_table_name_result_type = 'rt'
        alias_table_name_result = 'vr'
        alias_table_name_testrun = 'tr'

        tbl_tr = SQLTableExpr(TABLE_NAME_TESTRUN, alias_table_name_testrun)
        tbl_rd = SQLTableExpr(TABLE_NAME_RESULT_DESC, alias_table_name_result_desc)
        tbl_rt = SQLTableExpr(TABLE_NAME_RESULTTYPE, alias_table_name_result_type)
        tbl_vr = SQLTableExpr(TABLE_NAME_RESULT, alias_table_name_result)
        col_rt_id = SQLColumnExpr(alias_table_name_result_type, COL_NAME_RESULTTYPE_ID)
        col_rt_name = SQLColumnExpr(alias_table_name_result_type, COL_NAME_RESULTTYPE_NAME)
        col_rd_name = SQLColumnExpr(alias_table_name_result_desc, COL_NAME_RESDESC_NAME)
        col_rd_rt_id = SQLColumnExpr(alias_table_name_result_desc, COL_NAME_RESDESC_RESTYPE_ID)
        col_rd_id = SQLColumnExpr(alias_table_name_result_desc, COL_NAME_RESDESC_ID)
        col_vr_rd_id = SQLColumnExpr(alias_table_name_result, COL_NAME_RES_RESDESC_ID)
        col_tr_id = SQLColumnExpr(alias_table_name_testrun, COL_NAME_TR_ID)
        col_tr_cp = SQLColumnExpr(alias_table_name_testrun, COL_NAME_TR_CHECKPOINT)
        col_tr_name = SQLColumnExpr(alias_table_name_testrun, COL_NAME_TR_NAME)
        col_vr_tr_id = SQLColumnExpr(alias_table_name_result, COL_NAME_RES_TESTRUN_ID)
        col_vr_tr_del = SQLColumnExpr(alias_table_name_testrun, COL_NAME_TR_DELETED)

        tables = []

        join1 = SQLJoinExpr(tbl_rt, OP_INNER_JOIN, tbl_rd, SQLBinaryExpr(col_rt_id, OP_EQ, col_rd_rt_id))
        join2 = SQLJoinExpr(join1, OP_INNER_JOIN, tbl_vr, SQLBinaryExpr(col_rd_id, OP_EQ, col_vr_rd_id))
        join3 = SQLJoinExpr(join2, OP_INNER_JOIN, tbl_tr, SQLBinaryExpr(col_tr_id, OP_EQ, col_vr_tr_id))
        tables.append(join3)

        if select_list is None:
            select_list = [SQLBinaryExpr(col_rd_id, OP_AS, COL_NAME_RES_RESDESC_ID),
                           SQLBinaryExpr(col_rd_name, OP_AS, COL_NAME_RESDESC_NAME),
                           SQLBinaryExpr(col_tr_id, OP_AS, COL_NAME_RES_TESTRUN_ID),
                           SQLBinaryExpr(col_tr_cp, OP_AS, COL_NAME_TR_CHECKPOINT),
                           SQLBinaryExpr(col_tr_name, OP_AS, "TR_" + COL_NAME_TR_NAME),
                           SQLBinaryExpr(col_rt_name, OP_AS, "RT_" + COL_NAME_RESULTTYPE_NAME)]

        if where is None:
            cond = None
            if res_type_name is not None:
                cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER], col_rt_name),
                                     OP_EQ, SQLLiteral(res_type_name.lower()))
            if tr_name is not None:
                cond_name = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER], col_tr_name),
                                          OP_EQ, SQLLiteral(tr_name.lower()))
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_name)
            if tr_checkpoint is not None:
                cond_cp = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER], col_tr_cp),
                                        OP_EQ, SQLLiteral(tr_checkpoint.lower()))
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_cp)

            where = cond

        if incl_del is False:
            cond_del = SQLBinaryExpr(col_vr_tr_del, OP_EQ, 0)
            where = SQLBinaryExpr(where, OP_AND, cond_del)

        entries = self.select_generic_data(select_list, table_list=tables, where=where)

        return entries

    def get_result_descriptor_list(self, coll_id, name=None, ev_type_name=None):
        """ Return a list of descriptor names for the given collection and the optional event type

        :param coll_id: The collection id (testcase).
        :param name: Name of the result descriptors (optional)
        :param ev_type_name: The event type name (Image, MAX, MIN, ...)
        :return: Returns l list if descriptor names
        """
        rdlist = []

        if ev_type_name is not None:
            ev_type_id = self.get_result_type_id(ev_type_name)
            if ev_type_id is None:
                return rdlist

        else:
            ev_type_id = None

        sql_param, cond = self._get_res_desc_condition(coll_id, name, ev_type_id)
        entries = self.select_generic_data(table_list=[TABLE_NAME_RESULT_DESC], where=cond, sqlparams=sql_param)
        if len(entries) <= 0:
            tmp = "Result Descriptor for TC '%i' with " % coll_id
            tmp += "name '%s' " % name
            tmp += "does not exist in the validation result database."
            if name is None:
                self._log.info(tmp)
            else:
                self._log.info(tmp)
        else:
            for rec in entries:
                desc = rec[COL_NAME_RESDESC_NAME]
                if desc not in rdlist:
                    rdlist.append(rec[COL_NAME_RESDESC_NAME])

        return rdlist

    def get_resuls_descriptor_child_list(self, rd_id):  # pylint:disable=C0103
        """ Return a list of child descriptor id's for given parent descriptor id

        :param rd_id: The parent result descriptor id.
        :return: Returns l list if descriptor id's
        """
        rdlist = []

        cond = SQLBinaryExpr(COL_NAME_RESDESC_PARENT, OP_EQ, rd_id)

        entries = self.select_generic_data(table_list=[TABLE_NAME_RESULT_DESC], where=cond)
        if len(entries) <= 0:
            tmp = "Result Descriptor(s) with parent rd_id '%i' " % rd_id
            tmp += "does not exist in the validation result database."
            self._log.warning(tmp)
        else:
            for rec in entries:
                desc = rec[COL_NAME_RESDESC_ID]
                if desc not in rdlist:
                    rdlist.append(rec[COL_NAME_RESDESC_ID])

        return rdlist

    def _get_res_desc_condition(self, coll_id, name=None, result_type_id=None, ref_tag=None, parent_id=None):
        """Get the condition expression to access the result descriptors.

        :param coll_id: Collection ID (TestCase ID)
        :param name: Name of the result descriptors (optional)
        :param result_type_id: event type id (optional)
        :return: Returns the condition expression
        """
        sql_param = {}
        if type(coll_id) is list:
            cond = SQLBinaryExpr(COL_NAME_RESDESC_COLLID, OP_IN, str(tuple(coll_id)))
        else:
            sql_param[str(len(sql_param) + 1)] = coll_id
            cond = SQLBinaryExpr(COL_NAME_RESDESC_COLLID, OP_EQ, ":%d" % (len(sql_param)))

        if name is not None:
            sql_param[str(len(sql_param) + 1)] = name.lower()
            cond_name = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                  COL_NAME_RESDESC_NAME),
                                      OP_EQ, ":%d" % (len(sql_param)))
            cond = SQLBinaryExpr(cond, OP_AND, cond_name)

        if parent_id is not None:
            sql_param[str(len(sql_param) + 1)] = parent_id
            cond_parent_id = SQLBinaryExpr(COL_NAME_RESDESC_PARENT, OP_EQ, ":%d" % (len(sql_param)))
            cond = SQLBinaryExpr(cond, OP_AND, cond_parent_id)

        if result_type_id is not None:
            sql_param[str(len(sql_param) + 1)] = result_type_id
            cond_ev_type = SQLBinaryExpr(COL_NAME_RESDESC_RESTYPE_ID, OP_EQ, ":%d" % (len(sql_param)))
            cond = SQLBinaryExpr(cond, OP_AND, cond_ev_type)

        if ref_tag is not None:
            sql_param[str(len(sql_param) + 1)] = ref_tag
            cond_ref_tag = SQLBinaryExpr(COL_NAME_RESDESC_REFTAG, OP_EQ, ":%d" % (len(sql_param)))
            cond = SQLBinaryExpr(cond, OP_AND, cond_ref_tag)
        return sql_param, cond

    def update_result_descriptor(self, res_desc, where=None):
        """Update existing result descriptor records.

        :param res_desc: The result description record update.
        :param where: The condition to be fulfilled by the result descriptor to the updated.
        :return: Returns the number of affected result descriptors.
        """
        rowcount = 0

        if where is None:
            sql_param, where = self._get_res_desc_condition(res_desc[COL_NAME_RESDESC_COLLID],
                                                            res_desc[COL_NAME_RESDESC_NAME],
                                                            res_desc[COL_NAME_RESDESC_RESTYPE_ID])

        if (res_desc is not None) and (len(res_desc) != 0):
            rowcount = self.update_generic_data(res_desc, TABLE_NAME_RESULT_DESC, where, sqlparams=sql_param)
        # done
        return rowcount

    # --- Test Result. --------------------------------------------------
    def add_test_result_with_res_desc(self, tr_id, rd_id, meas_id=None, data=None,  # pylint: disable=R0913
                                      image=None, image_title=None, labels=None):
        """ Add a new TestResult for the Testrun, the TestCase and MeasId to the database

        :param tr_id: Testrun
        :param rd_id: Result descriptor id
        :param meas_id: Meas File Identifier (Catalog)
        :param data: Array of Result Values (optional)
        :param image: Result Image (optional)
        :param image_title: Title of the Result Image (optional)
        :param labels: Array of Labels Identifiers to be linked to the result (optional)
        :return: new TestResult Identifier.
        """
        result_id = None

        if data is None and image is None and labels is None or rd_id is None:
            msg = "No data to be stored: TR:%s" % tr_id
            if meas_id is not None:
                msg += str(", MEASID: %s" % meas_id)
                self._log.info(msg)
            return result_id

        return self._base_add_test_result(tr_id, rd_id, meas_id, data, image, image_title, labels)

    def add_test_result(self, tr_id, coll_id, name, ev_type, meas_id=None,
                        data=None, image=None, image_title=None, labels=None):
        """ Add a new TestResult for the Testrun, the TestCase and MeasId to the database

        :param tr_id: Testrun
        :param coll_id: Collection or TestCase Identifier (Catalog)
        :param name: Result Name
        :param ev_type: Result Type
        :param meas_id: Meas File Identifier (Catalog)
        :param data: Array of Result Values (optional)
        :param image: Result Image (optional)
        :param image_title: Title of the Result Image (optional)
        :param labels: Array of Labels Identifiers to be linked to the result (optional)
        :return: new TestResult Identifier.
        """

        # pylint: disable=R0913
        result_id = None

        try:
            rd_id = self.get_result_descriptor_id(coll_id, name, ev_type_name=ev_type)
        except StandardError:
            msg = "No Result Descriptor found: TR:%s, COLLID:%s, Name:'%s', EV:%s" % (tr_id, coll_id, name, ev_type)
            if meas_id is not None:
                msg += str(", MEASID: %s" % meas_id)
            self._log.info(msg)
            return result_id

        if data is None and image is None and labels is None or rd_id is None:
            msg = "No data to be stored: TR:%s, COLLID:%sma, Name:'%s', EV:%s" % (tr_id, coll_id, name, ev_type)
            if meas_id is not None:
                msg += str(", MEASID: %s" % meas_id)
            self._log.info(msg)
            return result_id

        return self._base_add_test_result(tr_id, rd_id, meas_id, data, image, image_title, labels)

    def _base_add_test_result(self, tr_id, rd_id, meas_id=None, data=None, image=None,  # pylint: disable=R0913
                              image_title=None, labels=None):
        """ Basic Add a new TestResult for the Testrun, the TestCase and MeasId to the database

        :param tr_id: Testrun
        :param rd_id: Result descriptor id
        :param meas_id: Meas File Identifier (Catalog)
        :param data: Array of Result Values (optional)
        :param image: Result Image (optional)
        :param image_title: Title of the Result Image (optional)
        :param labels: Array of Labels Identifiers to be linked to the result (optional)
        :return: new TestResult Identifier.
        """
        _ = labels  # preventing W0613 intentionally
        result_id = None
        if rd_id is not None:
            res = {COL_NAME_RES_RESDESC_ID: rd_id, COL_NAME_RES_TESTRUN_ID: tr_id}
            if meas_id is not None and meas_id > -1:
                res[COL_NAME_RES_MEASID] = meas_id

            # Store a single value directly to the result
            if data is not None and len(data) == 1:
                res[COL_NAME_RES_VALUE] = data[0]

            result_id = self.add_result(res)

            if data is not None and len(data) > 1:
                res_dat = {COL_NAME_RESVAL_ID: result_id}
                for i in range(len(data)):
                    res_dat[COL_NAME_RESVAL_SUBID] = i
                    res_dat[COL_NAME_RESVAL_VALUE] = data[i]
                    self.add_result_value(res_dat)

            # Add the image
            if image is not None:
                res_img = {COL_NAME_RESIMG_ID: result_id, COL_NAME_RESIMG_IMAGE: image,
                           COL_NAME_RESIMG_TITLE: '', COL_NAME_RESIMG_FORMAT: 'png'}
                if image_title is not None:
                    if len(image_title) >= 60:
                        image_title = image_title.replace(' ', '')
                        image_title = image_title.replace('.', '')
                        image_title = image_title.replace(':', '')
                        image_title = image_title.replace('(', '')
                        image_title = image_title.replace(')', '')
                        image_title = image_title[:59]
                    res_img[COL_NAME_RESIMG_TITLE] = image_title
                self.add_result_image(res_img)

        return result_id

    def add_result(self, result):
        """Add a new result descriptor to the database.

        :param result: The result dictionary - trid, rdid, measid are mandatory
        :return: Returns the result ID.
        """
        if COL_NAME_RES_MEASID in result:
            meas_id = result[COL_NAME_RES_MEASID]
        else:
            meas_id = None

        sqlparams, cond = self._get_result_condition(result[COL_NAME_RES_TESTRUN_ID],
                                                     result[COL_NAME_RES_RESDESC_ID],
                                                     meas_id)
        entries = self.select_generic_data(table_list=[TABLE_NAME_RESULT], where=cond, sqlparams=sqlparams)
        if len(entries) <= 0:
            rid = self.add_generic_data(result, TABLE_NAME_RESULT, SQLUnaryExpr(OP_RETURNING, COL_NAME_RES_ID))
            if rid is not None:
                return rid
            else:
                szmsg = "Result for testrun '%s', " % (result[COL_NAME_RES_TESTRUN_ID])
                szmsg += "Result Descriptor '%s' " % (result[COL_NAME_RES_RESDESC_ID])
                szmsg += "and MeasID '%s' " % (result[COL_NAME_RES_MEASID])
                szmsg += "exists already in the validation result database"
                raise AdasDBError(szmsg)
        else:
            szmsg = "Result for testrun '%s', " % (result[COL_NAME_RES_TESTRUN_ID])
            szmsg += "Result Descriptor '%s' " % (result[COL_NAME_RES_RESDESC_ID])
            szmsg += "and MeasID '%s' " % (result[COL_NAME_RES_MEASID])
            szmsg += "exists already in the validation result database"

            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError(szmsg)
            else:
                self._log.warning(szmsg)
                if len(entries) == 1:
                    rid = entries[0][COL_NAME_RES_ID]
                elif len(entries) > 1:
                    raise AdasDBError("Specific result cannot be found because it is ambiguous. (%s)" % entries)
        # done
        return rid

    def delete_result(self, result):
        """Delete existing result records.

        :param result: The result descrition record to delete.
        :return: Returns the number of affected eventtypes.
        """
        if (result is not None) and (len(result) != 0):
            measid = None
            rdid = None
            if COL_NAME_RES_RESDESC_ID in result:
                rdid = result[COL_NAME_RES_RESDESC_ID]
            if COL_NAME_RES_MEASID in result:
                measid = result[COL_NAME_RES_MEASID]

            sqlparams, cond = self._get_result_condition(result[COL_NAME_RES_TESTRUN_ID], rdid, measid)

        rowcount = self.delete_generic_data(TABLE_NAME_RESULT, where=cond, sqlparams=sqlparams)
        # done
        return rowcount

    def get_result(self, tr_id=None, rd_id=None, meas_id=None, res_id=None):
        """
        Get existing result records.

        :param tr_id: Testrun ID
        :param rd_id: Result descriptor ID (optional)
        :param meas_id: Measurement file ID (optional)
        :param res_id: Result ID(optional, if this is the the other arguments are ignored)
        """
        record = {}
        if res_id is None:
            sqlparams, cond = self._get_result_condition(tr_id, rd_id, meas_id)
        else:
            sqlparams = {}
            cond = SQLBinaryExpr(COL_NAME_RES_ID, OP_EQ, res_id)

        entries = self.select_generic_data(table_list=[TABLE_NAME_RESULT], where=cond, sqlparams=sqlparams)

        if len(entries) > 1:
            record = entries
        if len(entries) == 1:
            record = entries[0]
        # done
        return record

    def get_result_ids(self, tr_id, rd_id=None, meas_id=None):
        """Get existing result ids.

        :param tr_id: Testrun ID
        :param rd_id: Result descriptor ID (optional)
        :param meas_id: Measurement file ID (optional)
        """
        sqlparams, cond = self._get_result_condition(tr_id, rd_id, meas_id)
        select_list = [COL_NAME_RES_ID]
        _, entries = self.select_generic_data_compact(select_list, [TABLE_NAME_RESULT],
                                                      where=cond, sqlparams=sqlparams)
        # done
        return entries

    @staticmethod
    def _get_result_condition(tr_id, rd_id=None, meas_id=None):
        """Get the condition expression to access the result record

        :param tr_id: Testrun ID
        :param rd_id: Result descriptor ID (optional)
        :param meas_id: Measurement file ID (optional)
        :return: Returns the condition expression
        """
        sql_param = {}
        sql_param["1"] = tr_id
        cond = SQLBinaryExpr(COL_NAME_RES_TESTRUN_ID, OP_EQ, ":1")

        if rd_id is not None:
            sql_param["2"] = rd_id
            cond_rd = SQLBinaryExpr(COL_NAME_RES_RESDESC_ID, OP_EQ, ":2")
            cond = SQLBinaryExpr(cond, OP_AND, cond_rd)

        if meas_id is not None:
            sql_param["3"] = meas_id
            cond_mid = SQLBinaryExpr(COL_NAME_RES_MEASID, OP_EQ, ":3")
            cond = SQLBinaryExpr(cond, OP_AND, cond_mid)

        return sql_param, cond

    def update_result(self, result, where=None):
        """Update existing result record.

        :param result: The result record update.
        :param where: The condition to be fulfilled by the result to the updated.
        :return: Returns the number of affected result descriptors.
        """
        rowcount = 0

        if where is None:
            sqlparams, where = self._get_result_condition(result[COL_NAME_RES_TESTRUN_ID],
                                                          result[COL_NAME_RES_RESDESC_ID],
                                                          result[COL_NAME_RES_MEASID])

        if (result is not None) and (len(result) != 0):
            rowcount = self.update_generic_data(result, TABLE_NAME_RESULT, where, sqlparams=sqlparams)
        # done
        return rowcount

    # --- ASSESSMENT Table. --------------------------------------------------
    def add_assessment(self, assessment):
        """Add a new assessment record to the database.

        :param assessment: The assessment record to add, dict with table column names as keys for values to record
        :type  assessment: dict
        :return: Returns the result ID.
        """
        resassid = None
        try:
            resassid = self.add_generic_data(assessment, TABLE_NAME_ASSESSMENT,
                                             SQLUnaryExpr(OP_RETURNING, COL_NAME_ASS_ID))
        except StandardError, ex:
            raise AdasDBError("Assessment cannot be added due error:%s" % (str(ex)))
        return resassid

    def delete_assessment(self, assessment_id):
        """Delete existing result assessment records.

        :param assessment_id: The assessment record to delete.
        :return: Returns the number of affected assessments.
        """
#         try:
#             assessment_id = int(assessment_id)
#         except:
#             raise AdasDBError("DeleteAssessment: assessment_id is not an integer.")

        cond = self._get_assessment_condition(assid=assessment_id)
        return self.delete_generic_data(TABLE_NAME_ASSESSMENT, where=cond)
        # done

    def get_assessment(self, assid=None, assstid=None, asscomment=None, wfid=None,  # pylint: disable=R0913
                       userid=None):
        """Get existing result assessment records.

        :param assid: Assessment ID
        :param assstid: Assessment State Identifier
        :param asscomment:
        :param wfid:
        :param userid:
        :return: Record if exist
        """
        try:
            cond = self._get_assessment_condition(assid=assid, wfid=wfid, asscomment=asscomment,
                                                  user_id=userid, assstid=assstid)

            entries = self.select_generic_data(table_list=[TABLE_NAME_ASSESSMENT], where=cond)
        except:
            raise AdasDBError("Assessment could not retrieved. Please check the parameters")

        if len(entries) <= 0:
            self._log.warning(str("Assessment ID '%s' does not exist in the validation result database." % assid))
        else:
            return entries

        # done
        return []

    def get_assessment_id(self, assstid=None, asscomment=None, wfid=None, userid=None):
        """ Get the Assessment Identifier

        :param assstid: Assessment State Identifier
        :param asscomment: Assessment comment
        :param wfid: WorkFlow Identifier
        :param userid: User Identifier
        """
        assid = []
        entries = self.get_assessment(assstid=assstid, asscomment=asscomment, wfid=wfid, userid=userid)

        if len(entries) > 1:
            for item in entries:
                assid.append(item[COL_NAME_ASS_ID])
        elif len(entries) == 1:
            assid = entries[0][COL_NAME_ASS_ID]

        return assid

    def update_assessment(self, assessment, where=None):
        """Update existing result assessment record.

        :param res_ass: The result assessment record update.
        :param where: The condition to be fulfilled by the result assessment to the updated.
        :return: Returns the number of affected assessments descriptors.
        """
        rowcount = None
        if not isinstance(assessment, dict):
            raise AdasDBError("UpdateAssessment: assessment id is not a dict.")

        if COL_NAME_ASS_ID not in assessment:
            raise AdasDBError("UpdateAssessment: Assessment id not set.")

        if where is None:
            where = self._get_assessment_condition(assessment[COL_NAME_ASS_ID])

        if (assessment is not None) and (len(assessment) != 0):
            rowcount = self.update_generic_data(assessment, TABLE_NAME_ASSESSMENT, where)
        # done
        self.commit()
        return rowcount

    def is_assessment_locked(self, ass_id):
        """
        Check if the testrun is locked for the given Assessment Id

        :param ass_id:
        :type ass_id:
        """
        sql_param = {"1": ass_id}
        cond = SQLBinaryExpr(COL_NAME_RES_RESASSID, OP_EQ, ":1")
        entries = self.select_generic_data(select_list=[COL_NAME_RES_TESTRUN_ID],
                                           table_list=[TABLE_NAME_RESULT], where=cond, sqlparams=sql_param)
        if len(entries) == 0:
            entries = self.select_generic_data(select_list=[COL_NAME_EVENTS_TRID],
                                               table_list=[TABLE_NAME_EVENTS], where=cond, sqlparams=sql_param)
        if len(entries) > 0:
            return self._is_testrun_lock(entries[0][COL_NAME_RES_TESTRUN_ID])
        else:
            return False

    @staticmethod
    def _get_assessment_condition(assid=None, user_id=None, asscomment=None,  # pylint: disable=R0912,R0913
                                  wfid=None, assdate=None, assstid=None):
        """Get the condition expression to access the assessment record

        :param assid: Assessment ID
        :return: Returns the condition expression
        """
        if assid is None:
            cond = SQLBinaryExpr(COL_NAME_ASS_ID, OP_IS, SQLNull())
        else:
            cond = SQLBinaryExpr(COL_NAME_ASS_ID, OP_EQ, assid)

        if user_id is not None:
            cond_user = SQLBinaryExpr(COL_NAME_ASS_USER_ID, OP_EQ, user_id)
            if cond is not None:
                cond = SQLBinaryExpr(cond, OP_AND, cond_user)
            else:
                cond = cond_user

        if asscomment is not None:
            cond_com = SQLBinaryExpr(COL_NAME_ASS_COMMENT, OP_EQ, SQLLiteral(asscomment))
            if cond is not None:
                cond = SQLBinaryExpr(cond, OP_AND, cond_com)
            else:
                cond = cond_com

        if wfid is not None:
            cond_wfid = SQLBinaryExpr(COL_NAME_ASS_WFID, OP_EQ, wfid)
            if cond is not None:
                cond = SQLBinaryExpr(cond, OP_AND, cond_wfid)
            else:
                cond = cond_wfid

        if assdate is not None:
            cond_date = SQLBinaryExpr(COL_NAME_ASS_DATE, OP_EQ, SQLLiteral(assdate))
            if cond is not None:
                cond = SQLBinaryExpr(cond, OP_AND, cond_date)
            else:
                cond = cond_date

        if assstid is not None:
            cond_ass = SQLBinaryExpr(COL_NAME_ASS_ASSSTID, OP_EQ, assstid)
            if cond is not None:
                cond = SQLBinaryExpr(cond, OP_AND, cond_ass)
            else:
                cond = cond_ass

        return cond

    # --- IMAGE Table. --------------------------------------------------
    def add_result_image(self, res_img):
        """Add a new image to the database.

        :param res_img: The result assessment - resid is mandatory as it is the primary key
        :return: Returns the number of affected rows.
        """
        rowcount = 0
        cond = self._get_result_img_condition(res_img[COL_NAME_RESIMG_ID])
        entries = self.select_generic_data(table_list=[TABLE_NAME_RESULT_IMAGE], where=cond)
        if len(entries) <= 0:
            stmt = 'INSERT INTO '
            stmt += str(TABLE_NAME_RESULT_IMAGE)
            stmt += " (%s," % COL_NAME_RESIMG_ID
            stmt += "%s," % COL_NAME_RESIMG_TITLE
            stmt += "%s," % COL_NAME_RESIMG_FORMAT
            stmt += "%s)" % COL_NAME_RESIMG_IMAGE
            stmt += " VALUES('%s'," % (res_img[COL_NAME_RESIMG_ID],)
            stmt += "'%s'," % (res_img[COL_NAME_RESIMG_TITLE])
            stmt += "'%s', :1)" % (res_img[COL_NAME_RESIMG_FORMAT])
            cursor = self._db_connection.cursor()
            try:
                self._log.debug(stmt)
                cursor.execute(stmt, (res_img[COL_NAME_RESIMG_IMAGE],))
                rowcount = cursor.rowcount
            except:
                self._log.error(stmt)
                raise
            finally:
                cursor.close()

        else:
            tmp = "Image for Result ID '%s' " % res_img[COL_NAME_RESIMG_ID]
            tmp += "exists already in the validation result database"
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError(tmp)
            else:
                self._log.warning(tmp)
                if len(entries) == 1:
                    # ident = entries[0][COL_NAME_RESIMG_ID]
                    pass
                elif len(entries) > 1:
                    raise AdasDBError("Image for result ID cannot be found because it is ambiguous. (%s)" % entries)
        # done
        return rowcount

    def delete_result_image(self, res_img):
        """Delete existing result image records.
        :param res_img: The result image record to delete.
        :return: Returns the number of affected assessments.
        """
        if (res_img is not None) and (len(res_img) != 0):
            cond = self._get_result_img_condition(res_img[COL_NAME_RESIMG_ID])

        rowcount = self.delete_generic_data(TABLE_NAME_RESULT_IMAGE, where=cond)
        # done
        return rowcount

    def get_result_image(self, res_id):
        """Get existing result assessment records.

        :param res_id: Result ID
        :return: Record if exist
        """
        record = {}
        cond = self._get_result_img_condition(res_id)
        entries = self.select_generic_data(table_list=[TABLE_NAME_RESULT_IMAGE], where=cond)
        if len(entries) <= 0:
            self._log.warning(str("Image for Result ID '%s' does not exist in the validation result database."
                                  % res_id))
        elif len(entries) > 1:
            self._log.warning(str("Image for Result '%s' cannot be found because it is ambiguous. (%s)"
                                  % (res_id, str(entries))))
        else:
            record = entries[0]
            record[COL_NAME_RESIMG_IMAGE] = self._get_blob_buffer(record[COL_NAME_RESIMG_IMAGE])
        # done
        return record

    def get_image(self, tr_id, name, ev_type, coll_id, meas_id=None):  # pylint: disable=R0913
        """ Get Image and Title

        :param tr_id: Testrun
        :param name: Name of the Result
        :param ev_type: Name of the event type
        :param coll_id: Collection or Testcase Identifier (Catalog)
        :param meas_id: Meas File Identifier (Catalog) (optional)
        :return: Return the buffer of image data and the title
        """
        select = [COL_NAME_RES_ID]

        if meas_id == -1:
            meas_id = None

        rd_id = self.get_result_descriptor_id(coll_id, name, ev_type_name=ev_type)
        sqlparams, cond = self._get_result_condition(tr_id, rd_id, meas_id)
        entries = self.select_generic_data(select, table_list=[TABLE_NAME_RESULT], where=cond, sqlparams=sqlparams)

        if entries is not None and len(entries) == 1:
            res_id = entries[0][COL_NAME_RES_ID]
            result = self.get_result_image(res_id)
            if COL_NAME_RESIMG_IMAGE in result:
                return buffer(result[COL_NAME_RESIMG_IMAGE]), result[COL_NAME_RESIMG_TITLE]

        return None, ""

    @staticmethod
    def _get_result_img_condition(res_id):
        """Get the condition expression to access the result record

        :param res_id: Result ID
        :return: Returns the condition expression
        """
        return SQLBinaryExpr(COL_NAME_RESIMG_ID, OP_EQ, res_id)

    # --- RESULT_MESSAGES Table. --------------------------------------------------
    def add_result_message(self, res_val):
        """Add a new result message record to the database.

        :param res_val: The result message - resid and index are mandatory as they are the primary keys
        :return: Returns the result ID.
        """
        cond = self._get_result_message_condition(res_val[COL_NAME_RESMESS_ID], res_val[COL_NAME_RESMESS_SUBID])
        entries = self.select_generic_data(table_list=[TABLE_NAME_RESULT_MESSAGES], where=cond)
        if len(entries) <= 0:
            self.add_generic_data(res_val, TABLE_NAME_RESULT_MESSAGES)
        else:
            tmp = "Message for Result ID '%s' " % (res_val[COL_NAME_RESMESS_ID])
            tmp += "and Index '%s' " % (res_val[COL_NAME_RESMESS_SUBID])
            tmp += "exists already in the validation result database"

            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError(tmp)
            else:
                self._log.warning(tmp)
        # done

    def delete_result_message(self, res_val):
        """Delete existing result message record(s).

        :param res_val: The result assessment record to delete.
        :return: Returns the number of affected records.
        """
        rowcount = 0
        if (res_val is not None) and (len(res_val) != 0):
            if COL_NAME_RESMESS_SUBID in res_val:
                cond = self._get_result_message_condition(res_val[COL_NAME_RESMESS_ID],
                                                          res_val[COL_NAME_RESMESS_SUBID])
            else:
                cond = self._get_result_message_condition(res_val[COL_NAME_RESMESS_ID])
            rowcount = self.delete_generic_data(TABLE_NAME_RESULT_MESSAGES, where=cond)

        # done
        return rowcount

    def get_list_of_result_messages(self, res_id, sub_id=None):
        """Get existing result assessment records.

        :param res_id: Result ID
        :param sub_id: Sub identifier
        :return: Record if exist
        """
        record = {}
        cond = self._get_result_message_condition(res_id, sub_id)
        select_list = [COL_NAME_RESMESS_MESS]
        sort = [COL_NAME_RESMESS_SUBID]
        entries = self.select_generic_data_compact(select_list, table_list=[TABLE_NAME_RESULT_MESSAGES],
                                                   where=cond, order_by=sort)
        if len(entries) <= 0:
            tmp = "Message for Result ID '%s' " % res_id
            tmp += "and Index '%s' " % sub_id
            tmp += "exists already in the validation result database"
            self._log.warning(tmp)
        else:
            if len(entries) > 0:
                res_list = []
                for i in range(len(entries[1])):
                    res_list.append(entries[1][i][0])

            record = res_list
        # done
        return record

    def get_array_of_result_messages(self, res_id):
        """ Get array of result messages.

        :param res_id: Result ID
        :return: Array with result messages. Empty array if none found.
        """
        record = self.get_list_of_result_messages(res_id)

        message_array = []

        for item in record:
            message_array.append(item)

        return message_array

    def get_result_messages(self, tr_id, name, ev_type, coll_id, meas_id=None):  # pylint: disable=R0913
        """ Add the sum of messages

        :param tr_id: Testrun
        :param name: Name of the Result
        :param ev_type: Name of the event type
        :param coll_id: Collection or Testcase Identifier (Catalog)
        :param meas_id: Meas File Identifier (Catalog) (optional)
        :return: Return the sum of the Testmessages
        """
        select = [COL_NAME_RES_ID, COL_NAME_RESMESS_MESS]

        rd_id = self.get_result_descriptor_id(coll_id, name, ev_type_name=ev_type)
        if rd_id is None:
            return None
        sqlparams, cond = self._get_result_condition(tr_id, rd_id, meas_id)
        entries = self.select_generic_data(select, table_list=[TABLE_NAME_RESULT], where=cond, sqlparams=sqlparams)

        if len(entries) == 1:
            result_list = self.get_list_of_results(entries[0][COL_NAME_RES_ID])
            if len(result_list):
                return result_list
            return [entries[0][COL_NAME_RESMESS_MESS]]
        else:
            return None

    @staticmethod
    def _get_result_message_condition(res_id, idx=None):
        """Get the condition expression to access the result record

        :param res_id: Result ID
        :param idx: Index (optional)
        :return: Returns the condition expression
        """
        cond = SQLBinaryExpr(COL_NAME_RESMESS_ID, OP_EQ, res_id)

        if idx is not None:
            cond_mid = SQLBinaryExpr(COL_NAME_RESMESS_SUBID, OP_EQ, idx)
            cond = SQLBinaryExpr(cond, OP_AND, cond_mid)

        return cond

    # --- RESULT_VALUES Table. --------------------------------------------------
    def add_result_value(self, res_val):
        """Add a new result value record to the database.

        :param res_val: The result value - resid and index are mandatory as they are the primary keys
        :return: Returns the result ID.
        """
        cond = self._get_result_value_condition(res_val[COL_NAME_RESVAL_ID], res_val[COL_NAME_RESVAL_SUBID])
        entries = self.select_generic_data(table_list=[TABLE_NAME_RESULT_VALUES], where=cond)
        if len(entries) <= 0:
            self.add_generic_data(res_val, TABLE_NAME_RESULT_VALUES)
        else:
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                tmp = "Value for Result ID '%s' " % (res_val[COL_NAME_RESVAL_ID])
                tmp += "and Index '%s' " % (res_val[COL_NAME_RESVAL_SUBID])
                tmp += "exists already in the validation result database"
                raise AdasDBError(tmp)
            else:
                tmp = "Value for Result ID '%s' " % (res_val[COL_NAME_RESVAL_ID])
                tmp += "and Index '%s' " % (res_val[COL_NAME_RESVAL_SUBID])
                tmp += "exists already in the validation result database"
                self._log.warning(tmp)
        # done

    def delete_result_value(self, res_val):
        """Delete existing result value record(s).

        :param res_desc: The result assessment record to delete.
        :return: Returns the number of affected records.
        """
        rowcount = 0
        if (res_val is not None) and (len(res_val) != 0):
            if COL_NAME_RESVAL_SUBID in res_val:
                cond = self._get_result_value_condition(res_val[COL_NAME_RESVAL_ID], res_val[COL_NAME_RESVAL_SUBID])
            else:
                cond = self._get_result_value_condition(res_val[COL_NAME_RESVAL_ID])
            rowcount = self.delete_generic_data(TABLE_NAME_RESULT_VALUES, where=cond)

        # done
        return rowcount

    def get_list_of_results(self, res_id, sub_id=None):
        """Get existing result assessment records.

        :param res_id: Result ID
        :param sub_id: Sub identifier
        :return: Record if exist
        """
        record = []
        cond = self._get_result_value_condition(res_id, sub_id)
        select_list = [COL_NAME_RESVAL_VALUE]
        sort = [COL_NAME_RESVAL_SUBID]
        entries = self.select_generic_data_compact(select_list, table_list=[TABLE_NAME_RESULT_VALUES],
                                                   where=cond, order_by=sort)
        if len(entries) <= 0:
            tmp = "Value for Result ID '%s' and Index '%s' " % (res_id, sub_id)
            tmp += "exists already in the validation result database"
            self._log.warning(tmp)
        else:
            if len(entries) > 0:
                res_list = []
                for i in range(len(entries[1])):
                    res_list.append(entries[1][i][0])

            record = res_list
        # done
        return record

    def get_result_values(self, tr_id, name=None, ev_type=None, coll_id=None, meas_id=None,  # pylint: disable=R0913
                          rd_id=None):
        """ Add the sum of values

        :param tr_id: Testrun
        :param name: Name of the Result
        :param ev_type: Name of the event type
        :param coll_id: Collection or Testcase Identifier (Catalog)
        :param meas_id: Meas File Identifier (Catalog) (optional)
        :param rd_id: Result descriptor id
        :return: Return the sum of the Testvalues
        """
        select = [COL_NAME_RES_ID, COL_NAME_RES_VALUE]

        if rd_id is None:
            rd_id = self.get_result_descriptor_id(coll_id, name, ev_type_name=ev_type)

        if rd_id is None:
            return None

        sqlparams, cond = self._get_result_condition(tr_id, rd_id, meas_id)
        entries = self.select_generic_data(select, table_list=[TABLE_NAME_RESULT], where=cond, sqlparams=sqlparams)

        if len(entries) == 1:
            result_list = self.get_list_of_results(entries[0][COL_NAME_RES_ID])
            if len(result_list):
                return result_list
            return [entries[0][COL_NAME_RES_VALUE]]
        else:
            return None

    @staticmethod
    def _get_result_value_condition(res_id, idx=None):
        """Get the condition expression to access the result record

        :param res_id: Result ID
        :param idx: Index (optional)
        :return: Returns the condition expression
        """
        cond = SQLBinaryExpr(COL_NAME_RESVAL_ID, OP_EQ, res_id)

        if idx is not None:
            cond_mid = SQLBinaryExpr(COL_NAME_RESVAL_SUBID, OP_EQ, idx)
            cond = SQLBinaryExpr(cond, OP_AND, cond_mid)

        return cond

    # --- RESULT_LABEL Table. --------------------------------------------------
    def add_result_label(self, res_id, lb_id):
        """Add a new result - label map record to the database.

        :param res_id: The result id
        :param lb_id: The label id
        """
        cond = self._get_result_label_map_condition(res_id, lb_id)
        entries = self.select_generic_data(table_list=[TABLE_NAME_RESULT_LABEL_MAP], where=cond)

        res_val = {COL_NAME_RESLB_RESID: res_id, COL_NAME_RESLB_LBID: lb_id}

        if len(entries) <= 0:
            self.add_generic_data(res_val, TABLE_NAME_RESULT_LABEL_MAP)
        else:
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                tmp = "Link for Result ID '%s' and Label '%s' " % (res_id, lb_id)
                tmp += "exists already in the validation result database"
                raise AdasDBError(tmp)
            else:
                tmp = "Link for Result ID '%s' and Label '%s' " % (res_id, lb_id)
                tmp += "exists already in the validation result database"
                self._log.warning(tmp)
        # done

    def delete_result_label(self, res_id=None, lb_id=None):
        """Delete existing result to label map.

        :param res_id: The result id (optional)
        :param lb_id: The label id (optional)
        :return: Returns the number of affected records.
        """
        cond = self._get_result_label_map_condition(res_id, lb_id)
        rowcount = self.delete_generic_data(TABLE_NAME_RESULT_LABEL_MAP, where=cond)

        # done
        return rowcount

    def get_result_label(self, res_id=None, lb_id=None):
        """Get existing result assessment records.

        :param res_id: The result id (optional)
        :param lb_id: The label id (optional)
        :return: Record if exist
        """
        record = {}
        cond = self._get_result_label_map_condition(res_id, lb_id)
        entries = self.select_generic_data(table_list=[TABLE_NAME_RESULT_LABEL_MAP], where=cond)
        if len(entries) <= 0:
            tmp = "Value for Result ID '%s' and Index '%s' " % (res_id, lb_id)
            tmp += "exists already in the validation result database"
            self._log.warning(tmp)
        else:
            record = entries
        # done
        return record

    @staticmethod
    def _get_result_label_map_condition(res_id=None, lb_id=None):  # pylint:disable=C0103
        """Get the condition expression to access the result record

        :param res_id: Result ID (optional)
        :param lb_id:  Label ID (optional)
        :return: Returns the condition expression
        """
        cond = None

        if res_id is not None:
            cond = SQLBinaryExpr(COL_NAME_RESVAL_ID, OP_EQ, res_id)

        if lb_id is not None:
            cond_lb = SQLBinaryExpr(COL_NAME_RESLB_LBID, OP_EQ, lb_id)
            if cond is not None:
                cond = SQLBinaryExpr(cond, OP_AND, cond_lb)
            else:
                cond = cond_lb
        return cond

    # --- VALIDATION RESULT COMMON METHODS ------------------------------------------------------------------
    def get_test_run_sum_value(self, tr_id, name, ev_type, coll_id_list, meas_id=None,  # pylint: disable=R0913
                               rd_id=None):
        """ Add the sum of values

        :param tr_id: Testrun
        :param name: Name of the Result
        :param ev_type: Name of the event type
        :param coll_id_list: List of Collections or Testcase Identifiers (Catalog)
        :param meas_id: Meas File Identifier (Catalog) if specific COLLID is given
        :param rd_id:
        :return: Return the sum of the Testvalues
        """
        _ = rd_id

        expr = "SUM(%s)" % COL_NAME_RES_VALUE
        select = [expr]
        table_list = [TABLE_NAME_RESULT]

        if len(coll_id_list) == 1:
            rd_id = self.get_result_descriptor_id(coll_id_list[0], name, ev_type_name=ev_type)
            sqlparams, cond = self._get_result_condition(tr_id, rd_id, meas_id)
        else:
            sqlparams, cond = self._get_result_condition(tr_id)
            res_desc_list = self.get_result_descriptor_id_list(name, coll_id_list, ev_type_name=ev_type)
            where_in = ','.join(str(n) for n in res_desc_list)
            cond_rd = SQLBinaryExpr(COL_NAME_RES_RESDESC_ID, OP_IN, "(%s)" % where_in)
            cond = SQLBinaryExpr(cond, OP_AND, cond_rd)

        entries = self.select_generic_data(select, table_list, where=cond, sqlparams=sqlparams)
        if len(entries) == 1:
            return entries[0][expr]
        else:
            return 0

    def get_test_run_time_distance(self, trid, res_typename, sum=True):
        """
        Get Distance or Time process statistic under Testrun

        :param res_typename: ResultType name could be
                             for distance -->'VAL_TESTCASE_SUB_MEASRES_DIST_PROC'
                             for time --> 'VAL_TESTCASE_SUB_MEASRES_DIST_PROC'
        :type res_typename: string
        :param trid: testrun id
        :type trid: int
        :type sum:
        :return: entries: list of records
        :rtype: entries: list of dict
        """
        select_list = []
        tblresult = TABLE_NAME_RESULT
        tblresulttype = TABLE_NAME_RESULTTYPE
        tblresultdesc = TABLE_NAME_RESULT_DESC

        select_list.append(SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblresult),
                                                       COL_NAME_RES_VALUE),
                                         OP_AS, COL_NAME_RES_VALUE))

        select_list.append(SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblresult),
                                                       COL_NAME_RES_MEASID),
                                         OP_AS, COL_NAME_RES_MEASID))

        join_cond_col1 = SQLColumnExpr(SQLTableExpr(tblresultdesc), COL_NAME_RES_RESDESC_ID)
        join_cond_col2 = SQLColumnExpr(SQLTableExpr(tblresult), COL_NAME_RES_RESDESC_ID)
        join_cond1 = SQLBinaryExpr(join_cond_col1, OP_EQ, join_cond_col2)

        first_join = SQLJoinExpr(SQLTableExpr(tblresult),
                                 OP_INNER_JOIN,
                                 SQLTableExpr(tblresultdesc),
                                 join_cond1)
        join_cond_col3 = SQLColumnExpr(SQLTableExpr(tblresulttype), COL_NAME_RESULTTYPE_ID)
        join_cond_col4 = SQLColumnExpr(SQLTableExpr(tblresultdesc), COL_NAME_RESDESC_RESTYPE_ID)
        join_cond2 = SQLBinaryExpr(join_cond_col3, OP_EQ, join_cond_col4)

        second_join = SQLJoinExpr(first_join,
                                  OP_INNER_JOIN,
                                  SQLTableExpr(tblresulttype),
                                  join_cond2)

        tables = [second_join]

        cond1 = SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblresult),
                                            COL_NAME_RES_TESTRUN_ID),
                              OP_EQ, trid)
        cond2 = SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblresulttype),
                                            COL_NAME_RESULTTYPE_NAME),
                              OP_EQ, SQLLiteral(res_typename))
        cond = SQLBinaryExpr(cond1, OP_AND, cond2)

        records = self.select_generic_data(select_list=select_list, table_list=tables,
                                           where=cond)  # , group_by=[COL_NAME_RES_MEASID])
        total = 0.0
        processed_meas = []
        entries = []
        if len(records) > 0:
            for rec in records:
                if rec[COL_NAME_RES_MEASID] not in processed_meas:
                    processed_meas.append(rec[COL_NAME_RES_MEASID])
                    entries.append(rec)
                    total += rec[COL_NAME_RES_VALUE]
            if sum:
                return total
            else:
                return entries
        else:
            return None

    def add_hpc_job_for_testrun(self, trid, jbid):
        """
        Add Testrun HPC job map

        :param trid: testrun id
        :type trid: int
        :param jbid: HPC Jobid
        :type jbid: int
        """
        # Check if the jbid is not already Added to testrun
        if not self._has_job_for_testrun(trid, jbid):
            trun_jobmap_rec = {COL_NAME_TRUN_JOB_MAP_JBID: jbid,
                               COL_NAME_TRUN_JOB_MAP_TRID: trid}
            self.add_generic_data(trun_jobmap_rec, TABLE_NAME_TRUN_JOB_MAP)

    def delete_hpc_jobs_for_testrun(self, trid):
        """
        Get list of HPC Jobids for the given Testrun

        :param trid: TestRun Id
        :type trid: int
        """
        cond = SQLBinaryExpr(trid, OP_EQ, COL_NAME_TRUN_JOB_MAP_TRID)
        self.delete_generic_data(TABLE_NAME_TRUN_JOB_MAP, where=cond)

    def get_hpc_jobs_for_testrun(self, trid):
        """
        Get list of HPC Jobids for the given Testrun

        :param trid: TestRun Id
        :type trid: int
        """
        cond = SQLBinaryExpr(trid, OP_EQ, COL_NAME_TRUN_JOB_MAP_TRID)
        table_list = [TABLE_NAME_TRUN_JOB_MAP]
        records = self.select_generic_data(table_list=table_list, where=cond)
        entries = []
        for rec in records:
            entries.append(self.get_job(jbid=rec[COL_NAME_TRUN_JOB_MAP_JBID]))

        return entries

    def _has_job_for_testrun(self, trid, jbid):
        """
        Check if the Job has been already added to Testrun to avoid duplication

        :param trid:
        :type trid:
        :param jbid:
        :type jbid:
        """
        cond = SQLBinaryExpr(COL_NAME_TRUN_JOB_MAP_TRID, OP_EQ, trid)
        cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COL_NAME_TRUN_JOB_MAP_JBID, OP_EQ, jbid))
        table_list = [TABLE_NAME_TRUN_JOB_MAP]
        entries = self.select_generic_data(table_list=table_list, where=cond)
        if len(entries):
            return True
        else:
            return False

    def add_job(self, serverid, hpcjobid):
        """
        Add HPC job to database.

        If the record already exist then return its jbid
        otherwise return jbid of the new record

        :param serverid: server Id
        :type serverid: int
        :param hpcjobid: hpc Job Id
        :type hpcjobid: int
        """
        job_rec = self.get_job(serverid, hpcjobid)
        if job_rec is None:
            job_rec = {COL_NAME_JOBS_SERVID: serverid,
                       COL_NAME_JOBS_HPCJOBID: hpcjobid}
            self.add_generic_data(job_rec, TABLE_NAME_JOBS)
            job_rec = self.get_job(serverid, hpcjobid)

        return job_rec[COL_NAME_JOBS_JBID]

    def get_job(self, serverid=None, hpcjobid=None, jbid=None):
        """
        Get Record of the given HPCJobid and serverid or specifc record with given jbid

        :param serverid: Server Id
        :type serverid: int
        :param hpcjobid: HPC Job Id
        :type hpcjobid: int
        :param jbid: jbid database internal id
        :type jbid: int
        """
        cond = None
        if jbid is not None:
            cond = SQLBinaryExpr(jbid, OP_EQ, COL_NAME_JOBS_JBID)
        elif serverid is not None and hpcjobid is not None:
            cond = SQLBinaryExpr(serverid, OP_EQ, COL_NAME_JOBS_SERVID)
            cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(hpcjobid, OP_EQ, COL_NAME_JOBS_HPCJOBID))

        if cond is not None:
            entries = self.select_generic_data(table_list=[TABLE_NAME_JOBS], where=cond)
            if len(entries) == 1:
                return entries[0]
            elif len(entries) == 0:
                return None
        raise StandardError("The requested HPCJobId for the given server is ambigeious")

    # --- HISTOGRAM (RESULT_MESSAGES, RESULT_VALUES)Table. --------------------------------------------------
    def add_histogram(self, resid, columns, values):
        """ Writes a histogram to the RESULT_MESSAGES and RESULT_VALUES tables

        :param resid: The results id to which the histogram data is linked.
        :param columns: Array type variable containing the column information
        :param values: Array type variable containing the value information
        """
        columns_dict = {}
        values_dict = {}
        for idx in xrange(len(columns)):
            columns_dict[COL_NAME_RESMESS_ID] = resid
            columns_dict[COL_NAME_RESMESS_SUBID] = idx
            columns_dict[COL_NAME_RESMESS_MESS] = columns[idx]
            self.add_result_message(columns_dict)
            values_dict[COL_NAME_RESVAL_ID] = resid
            values_dict[COL_NAME_RESVAL_SUBID] = idx
            values_dict[COL_NAME_RESVAL_VALUE] = values[idx]
            self.add_result_value(values_dict)
        self.commit()

    def delete_histogram(self, resid):
        """ Deletes the histogram is in the database based on trid and name.

        :param resid: The result id.
        :return: The number of entries deleted.
        """
        res_val = {COL_NAME_RESMESS_ID: resid, COL_NAME_RESVAL_ID: resid}

        self.delete_result_message(res_val)
        entries = self.delete_result_value(res_val)
        return entries

    def get_histogramm(self, resid):
        """ Gets the histogram using statistics from all the files used with trid

        :param resid: Result id
        :return: array_histogram: 2D array containing the bins columns and values.
        """
        res_columns = self.get_array_of_result_messages(resid)
        res_values = self.get_list_of_results(resid)

        return [res_columns, res_values]

    # --- ROAD_EVALUATION Tables. --------------------------------------------------
    def add_road_event(self, record):
        """ Writes a single event line in the road event table

        :param record: dictionary type variable containing the event information
        """
        deprecation('AddRoadEvent() is deprecated. Will be remove in future!')
        cond_1 = SQLBinaryExpr(record[COL_NAME_ROAD_EVENTS_RESID], OP_EQ, COL_NAME_ROAD_EVENTS_RESID)
        cond_2 = SQLBinaryExpr(record[COL_NAME_ROAD_EVENTS_TIMESAMPLE], OP_EQ, COL_NAME_ROAD_EVENTS_TIMESAMPLE)
        cond_3 = SQLBinaryExpr(record[COL_NAME_ROAD_EVENTS_THRESHOLD], OP_EQ, COL_NAME_ROAD_EVENTS_THRESHOLD)
        cond_4 = SQLBinaryExpr(record[COL_NAME_ROAD_EVENTS_BEGINABSTS], OP_EQ, COL_NAME_ROAD_EVENTS_BEGINABSTS)
        cond_5 = SQLBinaryExpr(record[COL_NAME_ROAD_EVENTS_ENDABSTS], OP_EQ, COL_NAME_ROAD_EVENTS_ENDABSTS)
        cond1 = SQLBinaryExpr(cond_1, OP_AND, cond_2)
        cond2 = SQLBinaryExpr(cond_3, OP_AND, cond_4)
        cond3 = SQLBinaryExpr(cond1, OP_AND, cond2)
        cond = SQLBinaryExpr(cond3, OP_AND, cond_5)
        entries = self.select_generic_data(table_list=[TABLE_NAME_ROAD_EVENTS], where=cond)
        if len(entries) != 0:
            self._log.info('Event already in the database')
        else:
            record[COL_NAME_ROAD_EVENTS_EVENTID] = None
            self.add_generic_data(record, TABLE_NAME_ROAD_EVENTS)
            entries = self.select_generic_data(table_list=[TABLE_NAME_ROAD_EVENTS], where=cond)
            if len(entries) == 1:
                return entries[0][COL_NAME_ROAD_EVENTS_EVENTID]
            else:
                raise AdasDBError("Roadevent could not be added ")
        return 0

    def get_list_of_events(self, res_id):
        """
        Get list of road Type of event

        :param res_id:
        :type res_id:
        """
        deprecation('GetListOfEvents() is deprecated. Will be remove in future!')
        record = []
        cond = SQLBinaryExpr(int(res_id), OP_EQ, COL_NAME_ROAD_EVENTS_RESID)
        entries = self.select_generic_data(select_list=[COL_NAME_ROAD_EVENTS_EVENTID],
                                           table_list=[TABLE_NAME_ROAD_EVENTS], where=cond)
        for i in xrange(0, len(entries)):
            record.append(entries[i][COL_NAME_ROAD_EVENTS_EVENTID])

        return record

    def delete_road_event(self, res_id=None):
        """Delete existing rresult to label map.

        :param res_id: The result id (optional)
        :return: Returns the number of affected records.
        """
        deprecation('DeleteRoadEvent() is deprecated. Will be remove in future!')
        cond = SQLBinaryExpr(COL_NAME_ROAD_EVENTS_RESID, OP_EQ, res_id)

        rowcount = self.delete_generic_data(TABLE_NAME_ROAD_EVENTS, where=cond)

        # done
        return rowcount

    # =========================================================================
    # Functions for generating the pdf report based on the road estimation
    # validation information available in the database
    # =========================================================================

    def get_road_number_of_sw_versions_with_collid(self, collid, test_run_name):  # pylint:disable=C0103
        """ Returns the list of checkpoints for a given collid and test run name

        :param collid: the collection id
        :param test_run_name: the test run name
        :return: SW_list: the software list
        """
        deprecation('get_road_number_of_sw_versions_with_collid() is deprecated. Will be remove in future!')
        sw_list = []
        # First we get the RDID list: the list of result descriptors having collid as COLLID
        rdid_list = []
        cond = SQLBinaryExpr(collid, OP_EQ, COL_NAME_RESDESC_COLLID)
        entries = self.select_generic_data(select_list=[COL_NAME_RESDESC_ID], table_list=[TABLE_NAME_RESULT_DESC],
                                           where=cond)
        for i in xrange(0, len(entries)):
            rdid_list.append(entries[i][COL_NAME_RESDESC_ID])
        # Now we look for all the elements in VAL_Result having RDID. We take out the list of TRID.
        trid_list = []
        for i in xrange(0, len(rdid_list)):
            cond = SQLBinaryExpr(rdid_list[i], OP_EQ, COL_NAME_RES_RESDESC_ID)
            entries = self.select_generic_data(select_list=[COL_NAME_RES_TESTRUN_ID], table_list=[TABLE_NAME_RESULT],
                                               where=cond)
            for j in xrange(0, len(entries)):
                trid_list.append(entries[j][COL_NAME_RES_TESTRUN_ID])
        # Finally, we get the sw names using the TRID list
        trid_list = list(set(trid_list))
        pre_cond = SQLBinaryExpr(COL_NAME_TR_NAME, OP_EQ, SQLLiteral(test_run_name))
        for i in xrange(0, len(trid_list)):
            cond1 = SQLBinaryExpr(trid_list[i], OP_EQ, COL_NAME_TR_ID)
            cond = SQLBinaryExpr(pre_cond, OP_AND, cond1)
            entries = self.select_generic_data(select_list=[COL_NAME_TR_CHECKPOINT], table_list=[TABLE_NAME_TESTRUN],
                                               where=cond)
            for j in xrange(0, len(entries)):
                sw_list.append(entries[j][COL_NAME_TR_CHECKPOINT])
        # done
        return sw_list

    # ===================================================================
    # deprecated methods
    # ===================================================================

    def Initialize(self):  # pylint: disable=C0103
        """deprecated"""
        return self.initialize()

    def AddTestRun(self, testrun, replace=False):  # pylint: disable=C0103
        """deprecated"""
        return self.add_testrun(testrun, replace)

    def UpdateTestRun(self, testrun, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_testrun(testrun, where)

    def DeleteTestRun(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_testrun(*args, **kw)

    def RestoreTestRun(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.restore_testrun(*args, **kw)

    def GetTestRunLock(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_testrun_lock(*args, **kw)

    def UpdateTestRunLock(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.update_testrun_lock(*args, **kw)

    def GetAllTestruns(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_all_testruns(*args, **kw)

    def GetSeidsForTestrun(self, tr_id, measids):  # pylint: disable=C0103
        """deprecated"""
        return self.get_seids_for_testrun(tr_id, measids)

    def GetMeasidsForTestrun(self, tr_id):  # pylint: disable=C0103
        """deprecated"""
        return self.get_measids_for_testrun(tr_id)

    def GetTestRun(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_testrun(*args, **kw)

    def GetTestRunIdsForParent(self, parent_id, delete_status=0):  # pylint: disable=C0103
        """deprecated"""
        return self.get_testrun_ids_for_parent(parent_id, delete_status)

    def GetTestRunId(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_testrun_id(*args, **kw)

    def GetDeletedTestRunIds(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_deleted_testrun_ids(*args, **kw)

    def GetFilteredResultsTypesDetailsAssessment(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_filtered_results_types_details_assessment(*args, **kw)

    def GetFilteredEventTypesDetailsAttributesAssessment(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_filtered_event_types_details_attributes_assessment(*args, **kw)

    def GetEventsInfoForExportToCsv(self, trid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_events_info_for_export_to_csv(trid)

    def AddEventDetails(self, seid, absts):  # pylint: disable=C0103
        """deprecated"""
        return self.add_event_details(seid, absts)

    def GetEventDetails(self, edid=None, seid=None, absts=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_event_details(edid, seid, absts)

    def GetEventDetailsId(self, edid=None, seid=None, absts=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_event_details_id(edid, seid, absts)

    def GetEventDetailsTimestamps(self, seid=None, globs=False):  # pylint: disable=C0103
        """deprecated"""
        return self.get_event_details_timestamps(seid, globs)

    def GetEventDetailsAttributes(self, seid, timestamps=None, attribute_name=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_event_details_attributes(seid, timestamps, attribute_name)

    def DeleteEventDetails(self, seid):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_event_details(seid)

    def AddEventAttribute(self, attribute, getattrid=False):  # pylint: disable=C0103
        """deprecated"""
        return self.add_event_attribute(attribute, getattrid)

    def GetEventAttribute(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_event_attribute(*args, **kw)

    def GetEventAttributeId(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_event_attribute_id(*args, **kw)

    def DeleteEventAttributes(self, edid):
        """deprecated"""  # pylint: disable=C0103
        return self.delete_event_attributes(edid)

    def UpdateEventAttribute(self, attrid, value):  # pylint: disable=C0103
        """deprecated"""
        return self.update_event_attribute(attrid, value)

    def AddEventAttributeType(self, attribute_type):  # pylint: disable=C0103
        """deprecated"""
        return self.add_event_attribute_type(attribute_type)

    def GetEventAttributeType(self, name=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_event_attribute_type(name)

    def GetEventAttributeTypeId(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_event_attribute_type_id(name)

    def GetEventAttributeTypeIdsForParent(self, parent_id):  # pylint: disable=C0103
        """deprecated"""
        return self.get_event_attribute_type_ids_for_parent(parent_id)

    def AddEventImage(self, event_img):  # pylint: disable=C0103
        """deprecated"""
        return self.add_event_image(event_img)

    def GetEventImage(self, attrid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_event_image(attrid)

    def UpdateEventImage(self):  # pylint: disable=C0103
        """deprecated"""
        return self.update_event_image()

    def DeleteEventImage(self, attrid):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_event_image(attrid)

    def GetEventImagePlotSeq(self, seid, attr_type, plot=False):  # pylint: disable=C0103
        """deprecated"""
        return self.get_event_image_plot_seq(seid, attr_type, plot)

    def AddEvent(self, event, replace=False):  # pylint: disable=C0103
        """deprecated"""
        return self.add_event(event, replace)

    def AddEvent1(self, event, replace=False):  # pylint: disable=C0103
        """deprecated"""
        return self.add_event1(event, replace)

    def GetMeasidForSeid(self, seid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_measid_for_seid(seid)

    def GetEventsAttributesView(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_events_attributes_view(*args, **kw)

    def GetEventTypesView(self, trid=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_event_types_view(trid)

    def GetEventsView(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_events_view(*args, **kw)

    def GetEvents(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_events(*args, **kw)

    def UpdateEvent(self, event, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_event(event, where)

    def DeleteEvent(self, seid):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_event(seid)

    def AddEventType(self, event_type):  # pylint: disable=C0103
        """deprecated"""
        return self.add_event_type(event_type)

    def GetEventType(self, event_type_id=None, name=None, class_name=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_event_type(event_type_id, name, class_name)

    def GetEventTypeId(self, class_name=None, name=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_event_type_id(class_name, name)

    def UpdateEventType(self, event_type, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_event_type(event_type, where)

    def DeleteEventType(self, event_type):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_event_type(event_type)

    def AddResultType(self, result_type):  # pylint: disable=C0103
        """deprecated"""
        return self.add_result_type(result_type)

    def UpdateResultType(self, result_type, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_result_type(result_type, where)

    def DeleteResultType(self, result_type):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_result_type(result_type)

    def GetResultType(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_result_type(name)

    def GetResultTypeId(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_result_type_id(name)

    def GetResultTypeById(self, res_id):  # pylint: disable=C0103
        """deprecated"""
        return self.get_result_type_by_id(res_id)

    def AddValRevKey(self, name, description):  # pylint: disable=C0103
        """deprecated"""
        return self.add_val_rev_key(name, description)

    def DeleteValRevKey(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_val_rev_key(name)

    def UpdateValRevKey(self, rec, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_val_rev_key(rec, where)

    def GetValRevKey(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_val_rev_key(name)

    def GetValRevKeyId(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_val_rev_key_id(name)

    def AddValRevKeyConstraint(self, val_rev_key, rdid):  # pylint: disable=C0103
        """deprecated"""
        return self.add_val_rev_key_constraint(val_rev_key, rdid)

    def DeleteValRevKeyConstraint(self, val_rev_key=None, rdid=None):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_val_rev_key_constraint(val_rev_key, rdid)

    def GetValRevKeyConstraint(self, val_rev_key=None, rdid=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_val_rev_key_constraint(val_rev_key, rdid)

    def AddResultDescriptor(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.add_result_descriptor(*args, **kw)

    def DeleteResultDescriptor(self, res_desc):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_result_descriptor(res_desc)

    def GetResultDescriptor(self, coll_id, name, ev_type_id=None, ev_type_name=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_result_descriptor(coll_id, name, ev_type_id, ev_type_name)

    def GetResultDescriptorWithId(self, rd_id):  # pylint: disable=C0103
        """deprecated"""
        return self.get_result_descriptor_with_id(rd_id)

    def GetResultDescriptorId(self, coll_id, name, ev_type_id=None, ev_type_name=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_result_descriptor_id(coll_id, name, ev_type_id, ev_type_name)

    def GetResultDescriptorIdList(self, name, coll_id_list, ev_type_id=None, ev_type_name=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_result_descriptor_id_list(name, coll_id_list, ev_type_id, ev_type_name)

    def GetResultDescriptorInfoForTestrun(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_result_descriptor_info_for_testrun(*args, **kw)

    def GetResultDescriptorList(self, coll_id, name=None, ev_type_name=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_result_descriptor_list(coll_id, name, ev_type_name)

    def GetResulsDescriptorChildList(self, rd_id):  # pylint: disable=C0103
        """deprecated"""
        return self.get_resuls_descriptor_child_list(rd_id)

    def UpdateResultDescriptor(self, res_desc, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_result_descriptor(res_desc, where)

    def AddTestResultWithResDesc(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.add_test_result_with_res_desc(*args, **kw)

    def AddTestResult(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.add_test_result(*args, **kw)

    def AddResult(self, result):  # pylint: disable=C0103
        """deprecated"""
        return self.add_result(result)

    def DeleteResult(self, result):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_result(result)

    def GetResult(self, tr_id=None, rd_id=None, meas_id=None, res_id=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_result(tr_id, rd_id, meas_id, res_id)

    def GetResultIds(self, tr_id, rd_id=None, meas_id=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_result_ids(tr_id, rd_id, meas_id)

    def UpdateResult(self, result, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_result(result, where)

    def AddAssessment(self, assessment):  # pylint: disable=C0103
        """deprecated"""
        return self.add_assessment(assessment)

    def DeleteAssessment(self, assessment_id):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_assessment(assessment_id)

    def GetAssessment(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_assessment(*args, **kw)

    def GetAssessmentId(self, assstid=None, asscomment=None, wfid=None, userid=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_assessment_id(assstid, asscomment, wfid, userid)

    def UpdateAssessment(self, assessment, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_assessment(assessment, where)

    def AddResultImage(self, res_img):  # pylint: disable=C0103
        """depreccated"""
        return self.add_result_image(res_img)

    def DeleteResultImage(self, res_img):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_result_image(res_img)

    def GetResultImage(self, res_id):  # pylint: disable=C0103
        """deprecated"""
        return self.get_result_image(res_id)

    def GetImage(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_image(*args, **kw)

    def AddResultMessage(self, res_val):  # pylint: disable=C0103
        """deprecated"""
        return self.add_result_message(res_val)

    def DeleteResultMessage(self, res_val):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_result_message(res_val)

    def GetListOfResultMessages(self, res_id, sub_id=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_list_of_result_messages(res_id, sub_id)

    def GetArrayOfResultMessages(self, res_id):  # pylint: disable=C0103
        """deprecated"""
        return self.get_array_of_result_messages(res_id)

    def GetResultMessages(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_result_messages(*args, **kw)

    def AddResultValue(self, res_val):  # pylint: disable=C0103
        """deprecated"""
        return self.add_result_value(res_val)

    def DeleteResultValue(self, res_val):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_result_value(res_val)

    def GetListOfResults(self, res_id, sub_id=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_list_of_results(res_id, sub_id)

    def GetResultValues(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_result_values(*args, **kw)

    def AddResultLabel(self, res_id, lb_id):  # pylint: disable=C0103
        """deprecated"""
        return self.add_result_label(res_id, lb_id)

    def DeleteResultLabel(self, res_id=None, lb_id=None):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_result_label(res_id, lb_id)

    def GetResultLabel(self, res_id=None, lb_id=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_result_label(res_id, lb_id)

    def GetTestRunSumValue(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_test_run_sum_value(*args, **kw)

    def GetTestRunTimeDistance(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_test_run_time_distance(*args, **kw)

    def AddHPCJobForTestRun(self, trid, jbid):  # pylint: disable=C0103
        """deprecated"""
        return self.add_hpc_job_for_testrun(trid, jbid)

    def DeleteHPCJobsForTestRun(self, trid):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_hpc_jobs_for_testrun(trid)

    def GetHPCJobsForTestRun(self, trid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_hpc_jobs_for_testrun(trid)

    def AddJob(self, serverid, hpcjobid):  # pylint: disable=C0103
        """deprecated"""
        return self.add_job(serverid, hpcjobid)

    def GetJob(self, serverid=None, hpcjobid=None, jbid=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_job(serverid, hpcjobid, jbid)

    def AddHistogram(self, resid, columns, values):  # pylint: disable=C0103
        """deprecated"""
        return self.add_histogram(resid, columns, values)

    def DeleteHistogram(self, resid):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_histogram(resid)

    def GetHistogramm(self, resid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_histogramm(resid)

    def AddRoadEvent(self, record):  # pylint: disable=C0103
        """deprecated"""
        return self.add_road_event(record)

    def GetListOfEvents(self, res_id):  # pylint: disable=C0103
        """deprecated"""
        return self.get_list_of_events(res_id)

    def DeleteRoadEvent(self, res_id=None):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_road_event(res_id)

    def GetRoadNumberOfSWVersionsWithCollid(self, collid, test_run_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_road_number_of_sw_versions_with_collid(collid, test_run_name)

    def _GetNextID(self, table_name, col_name):  # pylint: disable=C0103
        """deprecated"""
        return self._get_next_id(table_name, col_name)

    def _get_testrun_parent_condition(self, parent_id, delete_status=0):
        """deprecated"""

        cond = SQLBinaryExpr(COL_NAME_TR_PARENT, OP_EQ, SQLLiteral(parent_id))
        if self.sub_scheme_version >= DELETE_LOCK_TRUN_FEATURE:
            cond_del = SQLBinaryExpr(COL_NAME_TR_DELETED, OP_EQ, delete_status)
            cond = SQLBinaryExpr(cond, OP_AND, cond_del)
        return cond


# ===================================================================
# Constraint DB Libary SQL Server Compact Implementation
# ===================================================================
class PluginValResDB(BaseValResDB, PluginBaseDB):  # pylint: disable=R0904
    """used by plugin finder"""
    def __init__(self, *args, **kwargs):
        """some comment is missing"""
        BaseValResDB.__init__(self, *args, **kwargs)


class SQLCEValResDB(BaseValResDB, PluginBaseDB):  # pylint: disable=R0904
    """SQL Server Compact Edition Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseValResDB.__init__(self, *args, **kwargs)


class OracleValResDB(BaseValResDB, PluginBaseDB):  # pylint: disable=R0904
    """Oracle Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseValResDB.__init__(self, *args, **kwargs)


class SQLite3ValResDB(BaseValResDB, PluginBaseDB):  # pylint: disable=R0904
    """Oracle Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseValResDB.__init__(self, *args, **kwargs)


"""
$Log: val.py  $
Revision 1.23 2016/10/28 15:39:43CEST Hospes, Gerd-Joachim (uidv8815) 
fix deprecation call
Revision 1.22 2016/10/28 14:59:11CEST Hospes, Gerd-Joachim (uidv8815)
pylint and doc creation error fixes
Revision 1.21 2016/10/20 14:50:33CEST Hospes, Gerd-Joachim (uidv8815)
in delete_testrun check type or returned value, single tr with result caused exception
Revision 1.20 2016/08/16 12:26:24CEST Hospes, Gerd-Joachim (uidv8815)
update module and class docu
Revision 1.19 2016/07/26 15:54:38CEST Hospes, Gerd-Joachim (uidv8815)
fix component usage in save and load
Revision 1.18 2016/07/22 15:54:07CEST Hospes, Gerd-Joachim (uidv8815)
new fields sim version and val sw version
Revision 1.17 2016/07/08 17:16:47CEST Hospes, Gerd-Joachim (uidv8815)
doc fixes
Revision 1.16 2016/07/08 09:24:22CEST Ahmed, Zaheer (uidu7634)
pep8 fixes
Revision 1.15 2016/07/07 16:22:48CEST Ahmed, Zaheer (uidu7634)
rework of delete testrun to run faster
Fxied foreign dependency issue on deleteing assessment
Revision 1.14 2016/05/09 11:00:20CEST Hospes, Gerd-Joachim (uidv8815)
add new column REMARKS to val.db and to pfd reports as new overview table row
Revision 1.13 2015/10/29 14:55:11CET Ahmed, Zaheer (uidu7634)
add new column VAL_TESTRUN.SIM_NAME
backward compatibility check adding column value for add_testrun()
- Added comments -  uidu7634 [Oct 29, 2015 2:55:11 PM CET]
Change Package : 390794:1 http://mks-psad:7002/im/viewissue?selection=390794
Revision 1.12 2015/10/05 13:37:21CEST Ahmed, Zaheer (uidu7634)
pep8 fixes
--- Added comments ---  uidu7634 [Oct 5, 2015 1:37:22 PM CEST]
Change Package : 376758:1 http://mks-psad:7002/im/viewissue?selection=376758
Revision 1.11 2015/10/05 12:55:49CEST Ahmed, Zaheer (uidu7634)
Cache testrun Record with Trid as key
Implement testrun lock in exclusive mode
new function is_assessment_locked()
--- Added comments ---  uidu7634 [Oct 5, 2015 12:55:50 PM CEST]
Change Package : 376758:1 http://mks-psad:7002/im/viewissue?selection=376758
Revision 1.10 2015/09/10 10:07:24CEST Ahmed, Zaheer (uidu7634)
load result descriptor with parent_id for ensure precise loading
bug fix in TestCase parent_id it must be NULL
--- Added comments ---  uidu7634 [Sep 10, 2015 10:07:25 AM CEST]
Change Package : 375792:1 http://mks-psad:7002/im/viewissue?selection=375792
Revision 1.9 2015/08/20 15:23:19CEST Ahmed, Zaheer (uidu7634)
bug fix get result to prevent crashing for empty entries
--- Added comments ---  uidu7634 [Aug 20, 2015 3:23:20 PM CEST]
Change Package : 360221:1 http://mks-psad:7002/im/viewissue?selection=360221
Revision 1.8 2015/08/20 14:33:31CEST Ahmed, Zaheer (uidu7634)
remove logger warning spam for result not exist
--- Added comments ---  uidu7634 [Aug 20, 2015 2:33:32 PM CEST]
Change Package : 360221:1 http://mks-psad:7002/im/viewissue?selection=360221
Revision 1.7 2015/07/14 13:21:52CEST Mertens, Sven (uidv7805)
reverting some changes
--- Added comments ---  uidv7805 [Jul 14, 2015 1:21:53 PM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.6 2015/07/14 09:32:41CEST Mertens, Sven (uidv7805)
simplify for plugin finder
--- Added comments ---  uidv7805 [Jul 14, 2015 9:32:42 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.5 2015/05/19 12:56:42CEST Ahmed, Zaheer (uidu7634)
bug fix in _base_add_test_result should return RESID not RESASSID
--- Added comments ---  uidu7634 [May 19, 2015 12:56:43 PM CEST]
Change Package : 338368:1 http://mks-psad:7002/im/viewissue?selection=338368
Revision 1.4 2015/05/18 14:52:24CEST Ahmed, Zaheer (uidu7634)
cache event typeid, restypeid, attribtypeid
grab newly inserted pk value for EDID, ATTRID, SEID, RESID with return SQL keyword
sql variable bindings usage
--- Added comments ---  uidu7634 [May 18, 2015 2:52:25 PM CEST]
Change Package : 338368:1 http://mks-psad:7002/im/viewissue?selection=338368
Revision 1.3 2015/05/05 14:44:58CEST Ahmed, Zaheer (uidu7634)
variable binding in _get_res_desc_condition()
returning newly insert PK value for add_result(), add_assessment
--- Added comments ---  uidu7634 [May 5, 2015 2:44:59 PM CEST]
Change Package : 318797:5 http://mks-psad:7002/im/viewissue?selection=318797
Revision 1.2 2015/04/30 11:09:29CEST Hospes, Gerd-Joachim (uidv8815)
merge last changes
--- Added comments ---  uidv8815 [Apr 30, 2015 11:09:29 AM CEST]
Change Package : 330394:1 http://mks-psad:7002/im/viewissue?selection=330394
Revision 1.1 2015/04/23 19:04:24CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/val/project.pj
Revision 1.86 2015/04/27 14:33:53CEST Mertens, Sven (uidv7805)
ident string fix
--- Added comments ---  uidv7805 [Apr 27, 2015 2:33:54 PM CEST]
Change Package : 329312:2 http://mks-psad:7002/im/viewissue?selection=329312
Revision 1.85 2015/03/09 11:52:13CET Ahmed, Zaheer (uidu7634)
passing error_tolerance as keyword argument
--- Added comments ---  uidu7634 [Mar 9, 2015 11:52:14 AM CET]
Change Package : 314217:1 http://mks-psad:7002/im/viewissue?selection=314217
Revision 1.84 2015/03/09 10:17:36CET Mertens, Sven (uidv7805)
another try to resolve unittest failure
--- Added comments ---  uidv7805 [Mar 9, 2015 10:17:37 AM CET]
Change Package : 314290:1 http://mks-psad:7002/im/viewissue?selection=314290
Revision 1.83 2015/03/06 12:48:50CET Mertens, Sven (uidv7805)
fix for last docu error
--- Added comments ---  uidv7805 [Mar 6, 2015 12:48:51 PM CET]
Change Package : 312989:1 http://mks-psad:7002/im/viewissue?selection=312989
Revision 1.82 2015/03/06 11:50:13CET Mertens, Sven (uidv7805)
changing protected members also to private and merging changes back to trunk
--- Added comments ---  uidv7805 [Mar 6, 2015 11:50:14 AM CET]
Change Package : 312989:1 http://mks-psad:7002/im/viewissue?selection=312989
Revision 1.81 2015/02/12 18:17:02CET Ellero, Stefano (uidw8660)
Removed all io and val based deprecated function usage inside stk and module tests
--- Added comments ---  uidw8660 [Feb 12, 2015 6:17:03 PM CET]
Change Package : 301799:1 http://mks-psad:7002/im/viewissue?selection=301799
Revision 1.80 2015/01/29 09:12:03CET Mertens, Sven (uidv7805)
alignment to internal _db_connection
--- Added comments ---  uidv7805 [Jan 29, 2015 9:12:04 AM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.79 2015/01/28 09:49:39CET Ahmed, Zaheer (uidu7634)
Bug fix in constructor of BaseValDb Class
--- Added comments ---  uidu7634 [Jan 28, 2015 9:49:40 AM CET]
Change Package : 298628:1 http://mks-psad:7002/im/viewissue?selection=298628
Revision 1.78 2015/01/27 18:57:00CET Hospes, Gerd-Joachim (uidv8815)
add TRUN_ADD_INFO_FEATURE
--- Added comments ---  uidv8815 [Jan 27, 2015 6:57:01 PM CET]
Change Package : 296832:1 http://mks-psad:7002/im/viewissue?selection=296832
Revision 1.77 2015/01/27 14:13:31CET Ahmed, Zaheer (uidu7634)
add new column ADD_INFO
changes in add_testrun method to handle this column data with compatiblity
--- Added comments ---  uidu7634 [Jan 27, 2015 2:13:32 PM CET]
Change Package : 298628:1 http://mks-psad:7002/im/viewissue?selection=298628
Revision 1.76 2015/01/27 13:09:24CET Mertens, Sven (uidv7805)
some deprecation usage update, but not all
--- Added comments ---  uidv7805 [Jan 27, 2015 1:09:26 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.74 2014/12/16 19:23:00CET Ellero, Stefano (uidw8660)
Remove all db.obj based deprecated function usage inside STK and module tests.
--- Added comments ---  uidw8660 [Dec 16, 2014 7:23:01 PM CET]
Change Package : 281278:1 http://mks-psad:7002/im/viewissue?selection=281278
Revision 1.73 2014/12/08 10:08:31CET Mertens, Sven (uidv7805)
removing duplicate get_next_id
--- Added comments ---  uidv7805 [Dec 8, 2014 10:08:31 AM CET]
Change Package : 281273:1 http://mks-psad:7002/im/viewissue?selection=281273
Revision 1.72 2014/12/04 19:40:28CET Ahmed, Zaheer (uidu7634)
bug fix to allow None for event attribute Value and image
as per database design they are nullable
--- Added comments ---  uidu7634 [Dec 4, 2014 7:40:29 PM CET]
Change Package : 287876:1 http://mks-psad:7002/im/viewissue?selection=287876
Revision 1.71 2014/10/17 10:59:02CEST Ahmed, Zaheer (uidu7634)
bug fix for missing attributes values in events
--- Added comments ---  uidu7634 [Oct 17, 2014 10:59:03 AM CEST]
Change Package : 267593:3 http://mks-psad:7002/im/viewissue?selection=267593
Revision 1.70 2014/10/14 17:29:09CEST Ahmed, Zaheer (uidu7634)
pylint fixes and epy doc improvement
--- Added comments ---  uidu7634 [Oct 14, 2014 5:29:12 PM CEST]
Change Package : 268541:1 http://mks-psad:7002/im/viewissue?selection=268541
Revision 1.69 2014/10/14 16:53:35CEST Ahmed, Zaheer (uidu7634)
added support for measurement Id for custom filters
--- Added comments ---  uidu7634 [Oct 14, 2014 4:53:36 PM CEST]
Change Package : 268541:1 http://mks-psad:7002/im/viewissue?selection=268541
Revision 1.68 2014/10/14 15:22:11CEST Ahmed, Zaheer (uidu7634)
pep8 fix and code clean up
--- Added comments ---  uidu7634 [Oct 14, 2014 3:22:12 PM CEST]
Change Package : 268541:1 http://mks-psad:7002/im/viewissue?selection=268541
Revision 1.67 2014/10/14 14:49:21CEST Ahmed, Zaheer (uidu7634)
added get_event_for_testrun()  to load events attribute without View
adedd __get_filter_joins()  to handle filter Customiz filter inner joins
--- Added comments ---  uidu7634 [Oct 14, 2014 2:49:22 PM CEST]
Change Package : 268541:1 http://mks-psad:7002/im/viewissue?selection=268541
Revision 1.66 2014/10/10 08:51:48CEST Hecker, Robert (heckerr)
Updates in naming convensions.
--- Added comments ---  heckerr [Oct 10, 2014 8:51:49 AM CEST]
Change Package : 270868:1 http://mks-psad:7002/im/viewissue?selection=270868
Revision 1.65 2014/09/16 11:27:37CEST Zafar, Sohaib (uidu6396)
Missing Event Type Column added
--- Added comments ---  uidu6396 [Sep 16, 2014 11:27:37 AM CEST]
Change Package : 264171:1 http://mks-psad:7002/im/viewissue?selection=264171
Revision 1.64 2014/09/04 11:05:46CEST Ahmed, Zaheer (uidu7634)
GetResult() has been modified with trid as optional argument
--- Added comments ---  uidu7634 [Sep 4, 2014 11:05:47 AM CEST]
Change Package : 253432:1 http://mks-psad:7002/im/viewissue?selection=253432
Revision 1.63 2014/06/30 17:34:51CEST Ahmed, Zaheer (uidu7634)
Changes made to support old behavior for GetDeletedTestRunIds()
--- Added comments ---  uidu7634 [Jun 30, 2014 5:34:52 PM CEST]
Change Package : 236899:1 http://mks-psad:7002/im/viewissue?selection=236899
Revision 1.62 2014/06/30 16:05:31CEST Ahmed, Zaheer (uidu7634)
bug fix to  get correct order of child testrun in GetDeletedTestRunIds()
--- Added comments ---  uidu7634 [Jun 30, 2014 4:05:32 PM CEST]
Change Package : 236899:1 http://mks-psad:7002/im/viewissue?selection=236899
Revision 1.61 2014/06/19 12:20:44CEST Ahmed, Zaheer (uidu7634)
Support load store of testtype for testrun which use by report librart to choose apprioate template
--- Added comments ---  uidu7634 [Jun 19, 2014 12:20:44 PM CEST]
Change Package : 241731:1 http://mks-psad:7002/im/viewissue?selection=241731
Revision 1.60 2014/05/28 16:16:00CEST Ahmed, Zaheer (uidu7634)
pylint fixes
--- Added comments ---  uidu7634 [May 28, 2014 4:16:01 PM CEST]
Change Package : 239969:1 http://mks-psad:7002/im/viewissue?selection=239969
Revision 1.59 2014/05/28 13:53:13CEST Ahmed, Zaheer (uidu7634)
Backward compatiblity suppport on Add testrun if there is no component feature in schema
remove the entry from record dictioary
--- Added comments ---  uidu7634 [May 28, 2014 1:53:13 PM CEST]
Change Package : 239969:1 http://mks-psad:7002/im/viewissue?selection=239969
Revision 1.58 2014/05/22 15:12:26CEST Ahmed, Zaheer (uidu7634)
Backward compatiblity
--- Added comments ---  uidu7634 [May 22, 2014 3:12:26 PM CEST]
Change Package : 235884:1 http://mks-psad:7002/im/viewissue?selection=235884
Revision 1.57 2014/05/22 09:15:11CEST Ahmed, Zaheer (uidu7634)
Add new column and cmpid in VAL_TESTRUN table and function related to testrun tablss are changed
--- Added comments ---  uidu7634 [May 22, 2014 9:15:12 AM CEST]
Change Package : 235884:1 http://mks-psad:7002/im/viewissue?selection=235884
Revision 1.56 2014/05/19 11:30:02CEST Ahmed, Zaheer (uidu7634)
Coumn defination for VAL_ASSESSMENT_ARCHIVE table
--- Added comments ---  uidu7634 [May 19, 2014 11:30:02 AM CEST]
Change Package : 235091:1 http://mks-psad:7002/im/viewissue?selection=235091
Revision 1.55 2014/04/16 11:16:25CEST Ahmed, Zaheer (uidu7634)
GetFilteredEventTypesDetailsAttributesAssessment() issue is fixed for all db drivers
--- Added comments ---  uidu7634 [Apr 16, 2014 11:16:25 AM CEST]
Change Package : 230865:1 http://mks-psad:7002/im/viewissue?selection=230865
Revision 1.54 2014/03/24 10:23:17CET Ahmed, Zaheer (uidu7634)
Bug fix for Result Image BLOB type casting to buffer
Revision 1.53 2014/03/24 10:08:49CET Ahmed, Zaheer (uidu7634)
Bug fix for Event Image BLOB type casting
--- Added comments ---  uidu7634 [Mar 24, 2014 10:08:49 AM CET]
Change Package : 226767:1 http://mks-psad:7002/im/viewissue?selection=226767
Revision 1.52 2014/03/24 08:11:11CET Ahmed, Zaheer (uidu7634)
add indx column in VAL_EVENTS to support multiple event with same timestamp values allowed to save
Split Add Event function with better and clear implementation
Fixed bug in GetTestRunTimeDistance
--- Added comments ---  uidu7634 [Mar 24, 2014 8:11:11 AM CET]
Change Package : 219788:1 http://mks-psad:7002/im/viewissue?selection=219788
Revision 1.51 2014/03/12 14:30:09CET Ahmed, Zaheer (uidu7634)
Db interface functions for adding HPC job to testrun
--- Added comments ---  uidu7634 [Mar 12, 2014 2:30:10 PM CET]
Change Package : 221470:1 http://mks-psad:7002/im/viewissue?selection=221470
Revision 1.50 2014/03/07 11:33:11CET Ahmed, Zaheer (uidu7634)
pylint pep8 fix
removed unused import
improved doucmentation
deprecated ROADEVENT related function
--- Added comments ---  uidu7634 [Mar 7, 2014 11:33:11 AM CET]
Change Package : 221506:1 http://mks-psad:7002/im/viewissue?selection=221506
Revision 1.49 2014/02/21 15:27:45CET Ahmed, Zaheer (uidu7634)
If no distance/time process statistic found then return None instead
of empty list
--- Added comments ---  uidu7634 [Feb 21, 2014 3:27:46 PM CET]
Change Package : 220098:3 http://mks-psad:7002/im/viewissue?selection=220098
Revision 1.48 2014/02/20 17:50:24CET Ahmed, Zaheer (uidu7634)
pep8 fixes
--- Added comments ---  uidu7634 [Feb 20, 2014 5:50:25 PM CET]
Change Package : 220098:2 http://mks-psad:7002/im/viewissue?selection=220098
Revision 1.47 2014/02/20 14:29:29CET Ahmed, Zaheer (uidu7634)
GetTestRunTimeDistance() added to get Driver distance/time processed
for all measurement in a testrun
--- Added comments ---  uidu7634 [Feb 20, 2014 2:29:30 PM CET]
Change Package : 220098:1 http://mks-psad:7002/im/viewissue?selection=220098
Revision 1.46 2013/12/09 18:05:52CET Ahmed-EXT, Zaheer (uidu7634)
Added Tracking ID  Column def for Val_Assement table
--- Added comments ---  uidu7634 [Dec 9, 2013 6:05:53 PM CET]
Change Package : 210017:3 http://mks-psad:7002/im/viewissue?selection=210017
Revision 1.45 2013/12/05 15:57:05CET Ahmed-EXT, Zaheer (uidu7634)
Improve GetDeletedTestrun function and fixed bugs
Revision 1.44 2013/11/28 12:32:42CET Ahmed-EXT, Zaheer (uidu7634)
Improve doc string
pep8 pylint fix
added new function GetDeletedTestRunIds()
--- Added comments ---  uidu7634 [Nov 28, 2013 12:32:42 PM CET]
Change Package : 203293:1 http://mks-psad:7002/im/viewissue?selection=203293
Revision 1.43 2013/11/26 14:49:06CET Bratoi-EXT, Bogdan-Horia (uidu8192)
Project_id and filter implementation
--- Added comments ---  uidu8192 [Nov 26, 2013 2:49:07 PM CET]
Change Package : 193409:1 http://mks-psad:7002/im/viewissue?selection=193409
Revision 1.42 2013/10/31 17:26:57CET Ahmed-EXT, Zaheer (uidu7634)
Project Id column added into VAL_TESTRUN table changes made to support the coumn into db interface function
--- Added comments ---  uidu7634 [Oct 31, 2013 5:26:57 PM CET]
Change Package : 203293:1 http://mks-psad:7002/im/viewissue?selection=203293
Revision 1.41 2013/09/09 16:38:41CEST Raedler, Guenther (uidt9430)
- return only valid testruns by default. As option, all TR could be returned.
--- Added comments ---  uidt9430 [Sep 9, 2013 4:38:41 PM CEST]
Change Package : 196718:1 http://mks-psad:7002/im/viewissue?selection=196718
Revision 1.40 2013/08/26 15:26:38CEST Ahmed-EXT, Zaheer (uidu7634)
Fixed ViewEvent column
--- Added comments ---  uidu7634 [Aug 26, 2013 3:26:38 PM CEST]
Change Package : 192688:1 http://mks-psad:7002/im/viewissue?selection=192688
Revision 1.39 2013/08/05 14:42:35CEST Raedler, Guenther (uidt9430)
- add new param cond to event view queries
- fixed cx_oracle failure when adding the path of a file as blop
--- Added comments ---  uidt9430 [Aug 5, 2013 2:42:36 PM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.38 2013/07/25 10:06:15CEST Raedler, Guenther (uidt9430)
- added new conditions to select testruns
--- Added comments ---  uidt9430 [Jul 25, 2013 10:06:16 AM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.37 2013/07/17 15:00:36CEST Raedler, Guenther (uidt9430)
- revert changes of BaseDB class
--- Added comments ---  uidt9430 [Jul 17, 2013 3:00:37 PM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.36 2013/07/15 13:58:27CEST Raedler, Guenther (uidt9430)
- added new column rdid into val_events table
--- Added comments ---  uidt9430 [Jul 15, 2013 1:58:27 PM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.35 2013/07/09 11:24:50CEST Raedler, Guenther (uidt9430)
- added new column rdid to val_events table
--- Added comments ---  uidt9430 [Jul 9, 2013 11:24:50 AM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.34 2013/07/04 15:01:49CEST Mertens, Sven (uidv7805)
providing tableSpace to BaseDB for what sub-schema space each module is intended to be responsible
--- Added comments ---  uidv7805 [Jul 4, 2013 3:01:49 PM CEST]
Change Package : 185933:3 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.33 2013/07/04 07:56:34CEST Bratoi, Bogdan-Horia (uidu8192)
- first results implementation
--- Added comments ---  uidu8192 [Jul 4, 2013 7:56:34 AM CEST]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.32 2013/06/05 16:20:01CEST Raedler, Guenther (uidt9430)
- fixed error when storing images to sqlite
- abort when a testrun exists for another user
- add new column class_name in function GetResultDescriptorWithId()
--- Added comments ---  uidt9430 [Jun 5, 2013 4:20:01 PM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.31 2013/05/02 09:15:51CEST Bratoi, Bogdan-Horia (uidu8192)
- update of GetTestrunCondition
--- Added comments ---  uidu8192 [May 2, 2013 9:15:51 AM CEST]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.30 2013/04/26 15:39:11CEST Mertens, Sven (uidv7805)
resolving some pep8 / pylint errors
--- Added comments ---  uidv7805 [Apr 26, 2013 3:39:12 PM CEST]
Change Package : 179495:7 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.29 2013/04/26 13:23:34CEST Mertens, Sven (uidv7805)
as row is specified to allow nulls, None type of Python should be able to reflect this
--- Added comments ---  uidv7805 [Apr 26, 2013 1:23:35 PM CEST]
Change Package : 180829:1 http://mks-psad:7002/im/viewissue?selection=180829
Revision 1.28 2013/04/26 10:46:02CEST Mertens, Sven (uidv7805)
moving strIdent
--- Added comments ---  uidv7805 [Apr 26, 2013 10:46:04 AM CEST]
Change Package : 179495:4 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.27 2013/04/25 14:37:14CEST Mertens, Sven (uidv7805)
epydoc adaptation to colon instead of at
--- Added comments ---  uidv7805 [Apr 25, 2013 2:37:14 PM CEST]
Change Package : 179495:2 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.26 2013/04/25 08:28:33CEST Bratoi, Bogdan-Horia (uidu8192)
- merging the 1.24 changes
--- Added comments ---  uidu8192 [Apr 25, 2013 8:28:33 AM CEST]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.25 2013/04/25 08:19:18CEST Bratoi, Bogdan-Horia (uidu8192)
- changes in GetAllTestruns - adding delete_status as parameter
--- Added comments ---  uidu8192 [Apr 25, 2013 8:19:18 AM CEST]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.21.1.1 2013/04/16 11:35:21CEST Raedler, Guenther (uidt9430)
- added new function GetResultTypeById()
- fixed some errors due to pylint fixes (usage of list)
- fixed some typos
--- Added comments ---  uidt9430 [Apr 16, 2013 11:35:22 AM CEST]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.21 2013/04/11 14:33:56CEST Ahmed-EXT, Zaheer (uidu7634)
Fixed bugs for SQLite db support for delete test run
--- Added comments ---  uidu7634 [Apr 11, 2013 2:33:57 PM CEST]
Change Package : 178419:2 http://mks-psad:7002/im/viewissue?selection=178419
Revision 1.20 2013/04/03 08:17:14CEST Mertens, Sven (uidv7805)
pep8: removing format errors
--- Added comments ---  uidv7805 [Apr 3, 2013 8:17:14 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.19 2013/04/03 08:02:17CEST Mertens, Sven (uidv7805)
pylint: minor error, warnings fix
--- Added comments ---  uidv7805 [Apr 3, 2013 8:02:18 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.18 2013/04/02 10:06:57CEST Raedler, Guenther (uidt9430)
- use logging for all log messages again
- use specific indeitifier names
- removed some pylint warnings
--- Added comments ---  uidt9430 [Apr 2, 2013 10:06:57 AM CEST]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.17 2013/03/28 15:25:14CET Mertens, Sven (uidv7805)
pylint: W0311 (indentation), string class
--- Added comments ---  uidv7805 [Mar 28, 2013 3:25:14 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.16 2013/03/27 17:34:03CET Mertens, Sven (uidv7805)
id --> ident as id is a reserved word
--- Added comments ---  uidv7805 [Mar 27, 2013 5:34:04 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.15 2013/03/27 11:37:23CET Mertens, Sven (uidv7805)
pep8 & pylint: rowalignment and error correction
--- Added comments ---  uidv7805 [Mar 27, 2013 11:37:23 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.14 2013/03/27 09:04:33CET Mertens, Sven (uidv7805)
pylint: reorg of imports, rename of some variables
--- Added comments ---  uidv7805 [Mar 27, 2013 9:04:34 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.13 2013/03/26 16:19:27CET Mertens, Sven (uidv7805)
pylint: using direct imports, no stars any more
--- Added comments ---  uidv7805 [Mar 26, 2013 4:19:27 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.12 2013/03/22 08:24:28CET Mertens, Sven (uidv7805)
aligning bulk of files again for peping 8
Revision 1.11 2013/03/21 17:22:36CET Mertens, Sven (uidv7805)
solving some pylint warnings / errors
--- Added comments ---  uidv7805 [Mar 21, 2013 5:22:36 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.10 2013/03/21 16:25:29CET Hecker, Robert (heckerr)
Added needed parameters, because class_name is not all the time unique.
--- Added comments ---  heckerr [Mar 21, 2013 4:25:29 PM CET]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.9 2013/03/08 08:39:19CET Raedler, Guenther (uidt9430)
- fixed module test errors
--- Added comments ---  uidt9430 [Mar 8, 2013 8:39:19 AM CET]
Change Package : 100768:2 http://mks-psad:7002/im/viewissue?selection=100768
Revision 1.8 2013/03/07 07:19:43CET Raedler, Guenther (uidt9430)
- replaced id with tr_id for all testrun related methods
- support delete flag and lock flag for testruns
- merged latest changes from etk/adas_db
- fixed some pep8 warnings
--- Added comments ---  uidt9430 [Mar 7, 2013 7:19:43 AM CET]
Change Package : 100768:2 http://mks-psad:7002/im/viewissue?selection=100768
Revision 1.7 2013/03/02 20:50:20CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 2, 2013 8:50:20 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.6 2013/03/01 18:41:19CET Hecker, Robert (heckerr)
Updated regarding Pep8 Styleguide.
--- Added comments ---  heckerr [Mar 1, 2013 6:41:24 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.5 2013/02/27 19:57:33CET Hecker, Robert (heckerr)
Update regarding Pep8 (partly)
--- Added comments ---  heckerr [Feb 27, 2013 7:57:33 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2013/02/26 20:10:26CET Raedler, Guenther (uidt9430)
- Updates after Pep8 Styleguides
--- Added comments ---  uidt9430 [Feb 26, 2013 8:10:26 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.3 2013/02/26 16:15:08CET Raedler, Guenther (uidt9430)
- renamed relts in absts
- raise error if id is not an integer (support module test)
- don't mix up return of list and dict for event related methods
- removed testcode
--- Added comments ---  uidt9430 [Feb 26, 2013 4:15:08 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.2 2013/02/19 14:07:33CET Raedler, Guenther (uidt9430)
- database interface classes derives from common classes for oracle, ...
- use common exception classes
- use common db functions
--- Added comments ---  uidt9430 [Feb 19, 2013 2:07:33 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/02/11 09:59:38CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/db/val/project.pj
------------------------------------------------------------------------------
-- From ETK/ADAS_DB Archive
------------------------------------------------------------------------------
Revision 1.56 2012/11/26 14:49:46CET Bratoi, Bogdan-Horia (uidu8192)
- removed GetResultId function
- added an parameter to GetEventImagePlotSeq function
--- Added comments ---  uidu8192 [Nov 26, 2012 2:49:47 PM CET]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.55 2012/11/26 11:02:07CET Bratoi, Bogdan-Horia (uidu8192)
- small bug fix
--- Added comments ---  uidu8192 [Nov 26, 2012 11:02:07 AM CET]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.54 2012/11/26 10:08:50CET Bratoi, Bogdan-Horia (uidu8192)
- changed the GetEventImagePlotSeq function
--- Added comments ---  uidu8192 [Nov 26, 2012 10:08:52 AM CET]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.53 2012/11/23 12:20:11CET Bratoi, Bogdan-Horia (uidu8192)
- Changes in the GetFilteredEventTypesDetailsAttributesAssessment function
--- Added comments ---  uidu8192 [Nov 23, 2012 12:20:11 PM CET]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.52 2012/11/22 14:51:17CET Hammernik-EXT, Dmitri (uidu5219)
- changed default measid when adding new result without definiton for measid
--- Added comments ---  uidu5219 [Nov 22, 2012 2:51:20 PM CET]
Change Package : 163367:1 http://mks-psad:7002/im/viewissue?selection=163367
Revision 1.51 2012/11/15 09:54:38CET Hammernik-EXT, Dmitri (uidu5219)
- bugfixes in delete histogramm and read histogramm in/from database
- defined new function GetResultId
- removed commets in UpdateResult
- bugfix delete testrun -> added function to delete message
--- Added comments ---  uidu5219 [Nov 15, 2012 9:54:40 AM CET]
Change Package : 163367:1 http://mks-psad:7002/im/viewissue?selection=163367
Revision 1.50 2012/11/06 15:36:35CET Bratoi, Bogdan-Horia (uidu8192)
-bugfix in GetEventDetailsAttributes
--- Added comments ---  uidu8192 [Nov 6, 2012 3:36:35 PM CET]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.49 2012/11/06 15:13:43CET Bratoi, Bogdan-Horia (uidu8192)
- added UpdateEvent Attribute method and changed GetEventAttributeId
--- Added comments ---  uidu8192 [Nov 6, 2012 3:13:45 PM CET]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.48 2012/11/06 09:04:08CET Hammernik-EXT, Dmitri (uidu5219)
- changed AddEventAttribute method
- small changes
--- Added comments ---  uidu5219 [Nov 6, 2012 9:04:14 AM CET]
Change Package : 163367:1 http://mks-psad:7002/im/viewissue?selection=163367
Revision 1.47 2012/11/05 13:47:47CET Bratoi, Bogdan-Horia (uidu8192)
- added some functions and updates of the filtering feature for the assessment tool
--- Added comments ---  uidu8192 [Nov 5, 2012 1:47:50 PM CET]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.46 2012/10/23 14:32:50CEST Bratoi, Bogdan-Horia (uidu8192)
- updated the filter implementation of the Assessment tool
--- Added comments ---  uidu8192 [Oct 23, 2012 2:32:55 PM CEST]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.44 2012/10/16 18:03:29CEST Hammernik-EXT, Dmitri (uidu5219)
- bugfix: deleting of the assessment was changed
- column COL_NAME_ASS_ASSESSMENT was changed in COL_NAME_ASS_ASSSTID
--- Added comments ---  uidu5219 [Oct 16, 2012 6:03:29 PM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.43 2012/10/10 19:31:44CEST Hammernik-EXT, Dmitri (uidu5219)
- added new function for val_view_events_attributes
- renamed some columnames
--- Added comments ---  uidu5219 [Oct 10, 2012 7:31:47 PM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.42 2012/10/10 10:18:11CEST Hammernik-EXT, Dmitri (uidu5219)
- bugfixes: changed columnames for views
--- Added comments ---  uidu5219 [Oct 10, 2012 10:18:12 AM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.41 2012/10/09 14:29:22CEST Hammernik-EXT, Dmitri (uidu5219)
- added functionality to add an event image
- bugfixes: primery/foreign key of a table could be of type integer, float, long
- improved functions for accessing val tables with val_gui
--- Added comments ---  uidu5219 [Oct 9, 2012 2:29:24 PM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.38.1.11 2012/07/18 08:52:21CEST Hammernik-EXT, Dmitri (uidu5219)
- bugfixes in Assessment, Eventdetails and Events table methods
--- Added comments ---  uidu5219 [Jul 18, 2012 8:52:21 AM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.38.1.10 2012/07/02 14:20:42CEST Hammernik-EXT, Dmitri (uidu5219)
- changed val_assessment methods
- bugfixes
--- Added comments ---  uidu5219 [Jul 2, 2012 2:20:43 PM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.38.1.9 2012/06/29 10:58:06CEST Spruck, Jochen (spruckj)
add test run id for if event is added
--- Added comments ---  spruckj [Jun 29, 2012 10:58:06 AM CEST]
Change Package : 98074:5 http://mks-psad:7002/im/viewissue?selection=98074
Revision 1.38.1.8 2012/06/18 14:42:28CEST Spruck, Jochen (spruckj)
Some small bug fixes du to introduction of events
--- Added comments ---  spruckj [Jun 18, 2012 2:42:28 PM CEST]
Change Package : 98074:3 http://mks-psad:7002/im/viewissue?selection=98074
Revision 1.38.1.7 2012/06/05 14:10:24CEST Hammernik-EXT, Dmitri (uidu5219)
- bugfixes
--- Added comments ---  uidu5219 [Jun 5, 2012 2:10:25 PM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.38.1.6 2012/06/01 13:55:46CEST Spruck, Jochen (spruckj)
Change during renaming EventType to ResultType
--- Added comments ---  spruckj [Jun 1, 2012 1:55:46 PM CEST]
Change Package : 98074:3 http://mks-psad:7002/im/viewissue?selection=98074
Revision 1.38.1.5 2012/05/30 08:50:28CEST Hammernik-EXT, Dmitri (uidu5219)
- added function for update event
- added functions to add/ get/ update assessment
--- Added comments ---  uidu5219 [May 30, 2012 8:50:30 AM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.38.1.2 2012/05/15 10:36:42CEST Hammernik-EXT, Dmitri (uidu5219)
update
--- Added comments ---  uidu5219 [May 15, 2012 10:36:42 AM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.38 2012/03/06 16:20:39CET Raedler-EXT, Guenther (uidt9430)
- extended interface to get result values by descriptor id
--- Added comments ---  uidt9430 [Mar 6, 2012 4:20:39 PM CET]
Change Package : 100768:2 http://mks-psad:7002/im/viewissue?selection=100768
Revision 1.37 2012/03/05 10:38:06CET Raedler-EXT, Guenther (uidt9430)
- fixed error for functions returning the id when adding items
--- Added comments ---  uidt9430 [Mar 5, 2012 10:38:06 AM CET]
Change Package : 100768:2 http://mks-psad:7002/im/viewissue?selection=100768
Revision 1.36 2012/03/02 11:51:01CET Raedler-EXT, Guenther (uidt9430)
- use trigger for road events
- fixed error in GetListOfResults()
- removed GetArrayOfResultValues() as not needed
--- Added comments ---  uidt9430 [Mar 2, 2012 11:51:01 AM CET]
Change Package : 100768:2 http://mks-psad:7002/im/viewissue?selection=100768
Revision 1.35 2012/03/02 09:28:03CET Farcas-EXT, Florian Radu (uidu4753)
Added return value for functions that don't use GetNextID()
--- Added comments ---  uidu4753 [Mar 2, 2012 9:28:03 AM CET]
Change Package : 100437:1 http://mks-psad:7002/im/viewissue?selection=100437
Revision 1.34 2012/03/01 14:00:05CET Ibrouchene-EXT, Nassim (uidt5589)
Updated road event functions.
--- Added comments ---  uidt5589 [Mar 1, 2012 2:00:06 PM CET]
Change Package : 94467:1 http://mks-psad:7002/im/viewissue?selection=94467
Revision 1.33 2012/02/28 16:41:38CET Farcas-EXT, Florian Radu (uidu4753)
Update DB interface
--- Added comments ---  uidu4753 [Feb 28, 2012 4:41:38 PM CET]
Change Package : 100439:1 http://mks-psad:7002/im/viewissue?selection=100439
Revision 1.32 2012/02/07 16:34:02CET Raedler-EXT, Guenther (uidt9430)
- changed interface to support new column in VAL_Testrun
--- Added comments ---  uidt9430 [Feb 7, 2012 4:34:02 PM CET]
Change Package : 88154:1 http://mks-psad:7002/im/viewissue?selection=88154
Revision 1.31 2012/02/07 12:02:33CET Raedler Guenther (uidt9430) (uidt9430)
- cast new ID as integer value
Revision 1.30 2011/12/01 11:36:35CET Farcas-EXT, Florian Radu (uidu4753)
Corrected a typo in the name of AddResultDescriptor function
--- Added comments ---  uidu4753 [Dec 1, 2011 11:36:36 AM CET]
Change Package : 83163:1 http://mks-psad:7002/im/viewissue?selection=83163
Revision 1.29 2011/12/01 11:30:04CET Farcas-EXT, Florian Radu (uidu4753)
Added DB access functions for KEYS and CONSTRAINTSMAP tables
--- Added comments ---  uidu4753 [Dec 1, 2011 11:30:05 AM CET]
Change Package : 83163:1 http://mks-psad:7002/im/viewissue?selection=83163
Revision 1.28 2011/11/15 15:51:49CET Raedler-EXT, Guenther (uidt9430)
-- extension to delete of testrun recursively (by given parent id)
-- support to delete road events
--- Added comments ---  uidt9430 [Nov 15, 2011 3:51:50 PM CET]
Change Package : 76661:1 http://mks-psad:7002/im/viewissue?selection=76661
Revision 1.27 2011/10/19 08:17:32CEST Raedler Guenther (uidt9430) (uidt9430)
- reduce image filename if it exceeds the limit of 60 characters
--- Added comments ---  uidt9430 [Oct 19, 2011 8:17:32 AM CEST]
Change Package : 78376:5 http://mks-psad:7002/im/viewissue?selection=78376
Revision 1.26 2011/10/18 11:55:59CEST Ibrouchene Nassim (uidt5589) (uidt5589)
Updated the name of the road events table
--- Added comments ---  uidt5589 [Oct 18, 2011 11:56:00 AM CEST]
Change Package : 78373:1 http://mks-psad:7002/im/viewissue?selection=78373
Revision 1.25 2011/10/10 11:18:50CEST Raedler Guenther (uidt9430) (uidt9430)
- store format of image into DB
--- Added comments ---  uidt9430 [Oct 10, 2011 11:18:51 AM CEST]
Change Package : 78376:6 http://mks-psad:7002/im/viewissue?selection=78376
Revision 1.24 2011/09/22 13:24:16CEST Raedler Guenther (uidt9430) (uidt9430)
- fixed error if no image could be loaded
--- Added comments ---  uidt9430 [Sep 22, 2011 1:24:16 PM CEST]
Change Package : 78376:3 http://mks-psad:7002/im/viewissue?selection=78376
Revision 1.23 2011/09/09 08:16:05CEST Spruck Jochen (spruckj) (spruckj)
Get also the validation results wiht option res_id
--- Added comments ---  spruckj [Sep 9, 2011 8:16:05 AM CEST]
Change Package : 69027:1 http://mks-psad:7002/im/viewissue?selection=69027
Revision 1.22 2011/09/07 08:11:58CEST Raedler Guenther (uidt9430) (uidt9430)
-- return emtpy list if descriptor is not defined
--- Added comments ---  uidt9430 [Sep 7, 2011 8:11:59 AM CEST]
Change Package : 67780:6 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.21 2011/09/06 10:24:32CEST Spruck Jochen (spruckj) (spruckj)
Add GetResulsDescriptorChildList funktion
--- Added comments ---  spruckj [Sep 6, 2011 10:24:32 AM CEST]
Change Package : 69027:1 http://mks-psad:7002/im/viewissue?selection=69027
Revision 1.20 2011/09/05 12:49:08CEST Castell Christoph (uidt6394) (uidt6394)
Fixed bug with COL_NAME_ACC_A_OBJ_EVENT_ROM_EVRECTOBJMAPID.
--- Added comments ---  uidt6394 [Sep 5, 2011 12:49:08 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.19 2011/09/05 11:01:11CEST Castell Christoph (uidt6394) (uidt6394)
Added ACC tabel definitions.
--- Added comments ---  uidt6394 [Sep 5, 2011 11:01:11 AM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.18 2011/09/02 07:52:28CEST Raedler Guenther (uidt9430) (uidt9430)
-- replaced warning by error messsage changed the message text in GetResultDescriptor()
--- Added comments ---  uidt9430 [Sep 2, 2011 7:52:28 AM CEST]
Change Package : 67780:2 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.17 2011/09/01 09:06:36CEST Raedler Guenther (uidt9430) (uidt9430)
-- added documentation
--- Added comments ---  uidt9430 [Sep 1, 2011 9:06:36 AM CEST]
Change Package : 67780:2 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.16 2011/08/30 09:39:29CEST Spruck Jochen (spruckj) (spruckj)
-Add function to get Result descriptor main values function for rd_id
-Add function to add Result values with parameter rd_id
--- Added comments ---  spruckj [Aug 30, 2011 9:39:29 AM CEST]
Change Package : 69027:1 http://mks-psad:7002/im/viewissue?selection=69027
Revision 1.15 2011/08/30 09:20:56CEST Castell Christoph (uidt6394) (uidt6394)
Added support for ResultMessages and Histograms.
--- Added comments ---  uidt6394 [Aug 30, 2011 9:20:56 AM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.14 2011/08/29 17:29:52CEST Castell Christoph (uidt6394) (uidt6394)
Layout changes.
--- Added comments ---  uidt6394 [Aug 29, 2011 5:29:52 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.12 2011/08/25 17:04:45CEST Ibrouchene Nassim (uidt5589) (uidt5589)
fixed some import issues used for the road estimation.
--- Added comments ---  uidt5589 [Aug 25, 2011 5:04:45 PM CEST]
Change Package : 69072:2 http://mks-psad:7002/im/viewissue?selection=69072
Revision 1.11 2011/08/25 14:49:12CEST Ibrouchene Nassim (uidt5589) (uidt5589)
Updated the functions used for the road estimation
--- Added comments ---  uidt5589 [Aug 25, 2011 2:49:12 PM CEST]
Change Package : 69072:2 http://mks-psad:7002/im/viewissue?selection=69072
Revision 1.10 2011/08/11 10:52:42CEST Raedler Guenther (uidt9430) (uidt9430)
-- added some checks
--- Added comments ---  uidt9430 [Aug 11, 2011 10:52:42 AM CEST]
Change Package : 67780:5 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.9 2011/08/02 12:32:18CEST Castell Christoph (uidt6394) (uidt6394)
Added HasHistoram() and DeleteHistogram() functions.
--- Added comments ---  uidt6394 [Aug 2, 2011 12:32:19 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.8 2011/08/01 12:37:45CEST Castell Christoph (uidt6394) (uidt6394)
Fixed GetHistogram() function.
--- Added comments ---  uidt6394 [Aug 1, 2011 12:37:45 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.7 2011/08/01 11:32:02CEST Castell Christoph (uidt6394) (uidt6394)
Added Histogram table and Road tables from Nassim.
--- Added comments ---  uidt6394 [Aug 1, 2011 11:32:03 AM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.6 2011/07/28 10:59:05CEST Raedler Guenther (uidt9430) (uidt9430)
-- updated methods
-- support storage and laod of result arrays
--- Added comments ---  uidt9430 [Jul 28, 2011 10:59:06 AM CEST]
Change Package : 67780:5 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.5 2011/07/19 16:28:12CEST Raedler Guenther (uidt9430) (uidt9430)
-- fixed some errors
Revision 1.4 2011/07/19 16:25:38CEST Raedler Guenther (uidt9430) (uidt9430)
-- fixed some errors
Revision 1.3 2011/07/19 16:08:17CEST Raedler Guenther (uidt9430) (uidt9430)
-- added support of tesrun replace
Revision 1.2 2011/07/19 09:42:10CEST Raedler Guenther (uidt9430) (uidt9430)
- updated interface functions
- fixed errors
--- Added comments ---  uidt9430 [Jul 19, 2011 9:42:10 AM CEST]
Change Package : 67780:2 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.1 2011/07/01 07:07:09CEST Raedler Guenther (uidt9430) (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/EM_EnvironmentModel/05_Testing/05_Test_Environment/algo/em_req_test/valf_tests/
    adas_database/val/project.pj
"""
