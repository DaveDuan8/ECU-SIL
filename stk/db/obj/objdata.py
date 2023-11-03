"""
stk/db/obj/objdata.py
---------------------

Classes for Database access of Object Subschema

Sub-Scheme OBJ

**User-API**
    - `BaseObjDataDB`
        Providing methods to handle details of recognised objects (cars, trucks, pedestrians etc.)
        and calculate relative position and movement to them

The other classes in this module are handling the different DB types and are derived from BaseObjDataDB.

**usage in Valf suites**

For validation suites based on `Valf` class there is the operator `DbLinker` setting up all needed connections.

**using several connections in parallel**

If several sub-schemes have to be used in parallel the first connection should be reused.
Please check class `BaseObjDataDB` for more detail.

**Do not waste the limited number of connections to Oracle DB**
by setting up a new connection for each sub-scheme,
always use the existing one as described in `BaseObjDataDB`.

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.11 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/10/20 14:19:03CEST $
"""
# pylint: disable=R0904,W0702
# - import Python modules ---------------------------------------------------------------------------------------------
from warnings import warn
from uuid import uuid4

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.db.db_common import BaseDB, DB_FUNC_NAME_MIN, DB_FUNC_NAME_MAX, PluginBaseDB
from stk.db.db_sql import GenericSQLStatementFactory, SQLBinaryExpr, OP_EQ, SQLLiteral, OP_GT, OP_AND, OP_LT, \
    SQLColumnExpr, SQLTableExpr, SQLTernaryExpr, OP_INNER_JOIN, OP_ON, OP_LEQ, OP_GEQ, OP_BETWEEN, OP_OR, \
    SQLFuncExpr, OP_AS, OP_NOP, OP_USING, OP_IN, GenericSQLSelect, SQLJoinExpr
from stk.db.gbl.gbl import TABLE_NAME_USERS, COL_NAME_USER_ID, COL_NAME_USER_LOGIN
from stk.valf.signal_defs import DBOBJ


# - defines -----------------------------------------------------------------------------------------------------------
DEFAULT_ADMA_NAME = "adma"
DEFAULT_RT_RANGE_NAME = "rtrange"
DEFAULT_RECT_NAME = "rect"
LBL_STATE_UNLABLED = "unlabeled"
LBL_STATE_AUTO = "auto"
LBL_STATE_MANUAL = "manual"
LBL_STATE_REVIEWED = "reviewed"

DBOBJ_SUB_SCHEME_TAG = "OBJ"
SUBSCHEMA_UUID_FEATURE = 7
SUBSCHEMA_LANEDEL_FEATURE = 9
ASSOCIATION_TYPE_TABLE_NAME_FEATURE = 12

# =====================================================================================================================
# Table Definitions
# =====================================================================================================================

# OBJ table names.
TABLE_NAME_ACC_LANE_REL = "OBJ_ACCLANERELATION"
TABLE_NAME_ACC_LANE_TYPES = "OBJ_ACCLANETYPES"
# TABLE_NAME_ADMIN_ATTRIB_STATES = "OBJ_ADMINATTRIBSTATES"
# TABLE_NAME_ADMINISTRATION = "OBJ_ADMINISTRATION"
TABLE_NAME_ASSOC_TYPE = "OBJ_ASSOCIATIONTYPES"
TABLE_NAME_OBJECT_CLASS = "OBJ_CLASSTYPES"
TABLE_NAME_DOCU_CAM_CALIB = "OBJ_DOCUCAMCALIB"
TABLE_NAME_EGO_KINEMATICS = "OBJ_EGOKINEMATICS"
TABLE_NAME_EGO_KINEMATICS_ADMA = "OBJ_EGOKINEMATICS_ADMA"
TABLE_NAME_KINEMATICS = "OBJ_KINEMATICS"
TABLE_NAME_ADMA_KINEMATICS = "OBJ_KINEMATICSADMA"
TABLE_NAME_OBJ_LBL_STATE = "OBJ_LBLSTATE"
TABLE_NAME_PROBS_CAM = "OBJ_PROBS_CAM"
TABLE_NAME_RECTANGULAR_OBJECT = "OBJ_RECTANGULAROBJECT"
TABLE_NAME_TEST_CASES = "OBJ_TESTCASES"
TABLE_NAME_TEST_CASE_TYPE = "OBJ_TESTCASETYPE"
TABLE_NAME_EGO_MOTION = "OBJ_EGOMOTION"
TABLE_NAME_RECTANGULAR_OBJECT_VIEW = "OBJ_VIEW_RECTANGULAROBJECT"
TABLE_NAME_OBJ_TESTCASES_VIEW = "OBJ_VIEW_TESTCASES"
TABLE_NAME_OBJ_ACCLANERELATION_VIEW = "OBJ_VIEW_ACCLANERELATION"
TABLE_NAME_OBJ_LBLCHECKPOINTS = "OBJ_LBLCHECKPOINTS"
TABLE_NAME_OBJ_RECTOBJ_CHECKPOINTMAP = "OBJ_RECTOBJ_CHECKPOINTMAP"
TABLE_NAME_OBJ_EGOKINE_CHECKPOINTMAP = "OBJ_EGOKINE_CHECKPOINTMAP"
TABLE_NAME_ACC_LANEDEL_ACTIVITY = "OBJ_ACCLANEDELETE_ACTIVITY"
TABLE_NAME_ACC_LANEDEL_ACTIVITY_VIEW = "OBJ_VIEW_ACCLANEDEL_ACTIVITY"
# =====================================================================================================================
# Table Column definitions
# =====================================================================================================================

# TABLE_NAME_RECTANGULAR_OBJECT = "OBJ_RectangularObject"
COL_NAME_RECT_OBJ_RECTOBJID = "RECTOBJID"
COL_NAME_RECT_OBJ_MEASID = "MEASID"
COL_NAME_RECT_OBJ_ASSOCTYPEID = "ASSOCTYPEID"
COL_NAME_RECT_OBJ_RECTOBJ_IS_DELETED = "RECTOBJ_IS_DELETED"
COL_NAME_RECT_OBJ_OBJCLASSID = "CLSID"
COL_NAME_RECT_OBJ_CLSLBLSTATEID = "CLSLBLSTATEID"
COL_NAME_RECT_OBJ_CLSLBLTIME = "CLSLBLTIME"
COL_NAME_RECT_OBJ_CLSLBLBY = "CLSLBLBY"
COL_NAME_RECT_OBJ_OBJWIDTH = "OBJWIDTH"
COL_NAME_RECT_OBJ_OBJLENGTH = "OBJLENGTH"
COL_NAME_RECT_OBJ_OBJHEIGHT = "OBJHEIGHT"
COL_NAME_RECT_OBJ_DIMLBLSTATEID = "DIMLBLSTATEID"
COL_NAME_RECT_OBJ_DIMLBLTIME = "DIMLBLTIME"
COL_NAME_RECT_OBJ_DIMLBLBY = "DIMLBLBY"
COL_NAME_RECT_OBJ_ZLAYER = "ZLAYER"
COL_NAME_RECT_OBJ_ZOVERGROUND = "ZOVERGROUND"
COL_NAME_RECT_OBJ_ZOLBLSTATEID = "ZOLBLSTATEID"
COL_NAME_RECT_OBJ_ZOLBLBY = "ZOLBLBY"
COL_NAME_RECT_OBJ_ZOLBLTIME = "ZOLBLTIME"
COL_NAME_RECT_OBJ_KINLBLSTATEID = "KINLBLSTATEID"
COL_NAME_RECT_OBJ_KINLBLMODTIME = "KINLBLTIME"
COL_NAME_RECT_OBJ_LBLBY = "KINLBLBY"
COL_NAME_RECT_OBJ_UUID = "UUID"

# TABLE_NAME_EGO_KINEMATICS = "Obj_EgoKinematics"
COL_NAME_EGO_KINEMATICS_MEASID = "MEASID"
COL_NAME_EGO_KINEMATICS_KINABSTS = "KINABSTS"
COL_NAME_EGO_KINEMATICS_VELOCITY = "VELOCITY"
COL_NAME_EGO_KINEMATICS_ACCELERATION = "ACCELERATION"
COL_NAME_EGO_KINEMATICS_YAWRATE = "YAWRATE"
COL_NAME_EGO_KINEMATICS_RADARCYCLEID = "RADARCYCLEID"

# TABLE_NAME_KINEMATICS = "Obj_Kinematics"
COL_NAME_KINEMATICS_KINABSTS = "KINABSTS"
COL_NAME_KINEMATICS_RECTOBJID = "RECTOBJID"
COL_NAME_KINEMATICS_RELDISTX = "RELDISTX"
COL_NAME_KINEMATICS_RELDISTY = "RELDISTY"
COL_NAME_KINEMATICS_RELVELX = "RELVELX"
COL_NAME_KINEMATICS_HEADINGOVERGND = "HEADINGOVERGND"

# TABLE_NAME_ADMA_KINEMATICS = "Obj_KinematicsADMA"
COL_NAME_ADMA_KINEMATICS_RECTOBJID = "RECTOBJID"
COL_NAME_ADMA_KINEMATICS_KINABSTS = "KINABSTS"
COL_NAME_ADMA_KINEMATICS_RELDISTX = "RELDISTX"
COL_NAME_ADMA_KINEMATICS_RELDISTY = "RELDISTY"
COL_NAME_ADMA_KINEMATICS_RELDISTZ = "RELDISTZ"
COL_NAME_ADMA_KINEMATICS_RELVELX = "RELVELX"
COL_NAME_ADMA_KINEMATICS_RELVELY = "RELVELY"
COL_NAME_ADMA_KINEMATICS_ARELX = "RELACCELX"
COL_NAME_ADMA_KINEMATICS_ARELY = "RELACCELY"
COL_NAME_ADMA_KINEMATICS_HEADINGOG = "HEADINGOVERGND"
COL_NAME_ADMA_KINEMATICS_ADMAOK = "ADMAVALID"

# TABLE_NAME_ASSOC_TYPE = "OBJ_AssociationTypes"
COL_NAME_ASSOC_TYPE_ASSOCTYPEID = "ASSOCTYPEID"
COL_NAME_ASSOC_TYPE_NAME = "NAME"
COL_NAME_ASSOC_TYPE_DESC = "DESCRIPTION"
COL_NAME_ASSOC_TYPE_TABLE = "OBJ_TABLE_NAME"

# TABLE_NAME_TEST_CASES = "OBJ_TestCase"
COL_NAME_TEST_CASES_TESTCASEID = "TESTCASEID"
COL_NAME_TEST_CASES_TYPEID = "TESTCASETYPEID"
COL_NAME_TEST_CASES_RECTOBJID = "RECTOBJID"
COL_NAME_TEST_CASES_BEGINABSTS = "BEGINABSTS"
COL_NAME_TEST_CASES_ENDABSTS = "ENDABSTS"
COL_NAME_TEST_CASES_LBLSTATEID = "LBLSTATEID"
COL_NAME_TEST_CASES_LBLMODTIME = "LBLMODTIME"
COL_NAME_TEST_CASES_LBLBY = "LBLBY"

# TABLE_NAME_ACC_LANE_REL = "OBJ_AccLaneRelation"
COL_NAME_ACC_LANE_REL_ACCLANERELID = "ACCLANERELID"
COL_NAME_ACC_LANE_REL_RECTOBJID = "RECTOBJID"
COL_NAME_ACC_LANE_REL_BEGINABSTS = "BEGINABSTS"
COL_NAME_ACC_LANE_REL_ENDABSTS = "ENDABSTS"
COL_NAME_ACC_LANE_REL_LANEID = "LANEID"
COL_NAME_ACC_LANE_REL_LANEASSOCWEIGHT = "LANEASSOCWEIGHT"
COL_NAME_ACC_LANE_REL_LBLSTATEID = "LBLSTATEID"
COL_NAME_ACC_LANE_REL_LBLMODTIME = "LBLMODTIME"
COL_NAME_ACC_LANE_REL_LBLBY = "LBLBY"

# TABLE_NAME_TEST_CASE_TYPE = "OBJ_TestCaseType"
COL_NAME_TEST_CASE_TYPE_ID = "TESTCASETYPEID"
COL_NAME_TEST_CASE_TYPE_NAME = "NAME"
COL_NAME_TEST_CASE_TYPE_DESCRIPTION = "DESCRIPTION"

# TABLE_NAME_OBJ_LBL_STATE = "OBJ_LBLSTATE"
COL_NAME_LBL_STATE_LBL_STATE_ID = "LBLSTATEID"
COL_NAME_LBL_STATE_NAME = "NAME"
COL_NAME_LBL_STATE_DESCRIPTION = "DESCRIPTION"

# TABLE_NAME_ACC_LANE_TYPES = "OBJ_ACCLANETYPES"
COL_NAME_LANE_TYPES_LANE_ID = "LANEID"
COL_NAME_LANE_TYPES_LANE_NAME = "LANENAME"
COL_NAME_LANE_TYPES_DESCRIPTION = "DESCRIPTION"

# TABLE_NAME_OBJECT_CLASS = "OBJ_CLASSTYPES"
COL_NAME_OBJECT_CLASS_CLS_ID = "CLSID"
COL_NAME_OBJECT_CLASS_CLASS_NAME = "CLASSNAME"
COL_NAME_OBJECT_CLASS_DESCRIPTION = "DESCRIPTION"

# TABLE_NAME_EGO_KINEMATICS_ADMA = "OBJ_EGOKINEMATICS_ADMA"
COL_NAME_EGO_ADMA_MEASID = "MEASID"
COL_NAME_EGO_ADMA_KINABSTS = "KINABSTS"
COL_NAME_EGO_ADMA_VELOCITY_X = "VELOCITY_X"
COL_NAME_EGO_ADMA_VELOCITY_Y = "VELOCITY_Y"
COL_NAME_EGO_ADMA_VELOCITY_Z = "VELOCITY_Z"
COL_NAME_EGO_ADMA_ACCELERATION = "ACCELERATION"
COL_NAME_EGO_ADMA_YAWRATE = "YAWRATE"
COL_NAME_EGO_ADMA_PITCH = "PITCH"
COL_NAME_EGO_ADMA_ROLL = "ROLL"
COL_NAME_EGO_ADMA_PITCHRATE = "PITCHRATE"
COL_NAME_EGO_ADMA_ROLLRATE = "ROLLRATE"
COL_NAME_EGO_ADMA_SUMDIST = "SUMDIST"
COL_NAME_EGO_ADMA_SUMYAW = "SUMYAW"

# TABLE_NAME_PROBS_CAM = "OBJ_PROBS_CAM"
COL_NAME_PROBSCAM_ABSTS = "ABSTS"
COL_NAME_PROBSCAM_RECTOBJID = "RECTOBJID"
COL_NAME_PROBSCAM_OCCLUDED = "OCCLUDED"
COL_NAME_PROBSCAM_RELEVX = "RELEVX"
COL_NAME_PROBSCAM_RELEVY = "RELEVY"

COL_NAME_BEGIN_TS = "BeginAbsTS"
COL_NAME_END_TS = "EndAbsTS"

# TABLE_NAME_RECTANGULAR_OBJECT_VIEW = "OBJ_VIEW_RECTANGULAROBJECT"
COL_NAME_RECT_OBJ_VIEW_RECTOBJID = "RECTOBJID"
COL_NAME_RECT_OBJ_VIEW_RECFILEID = "RECFILEID"
COL_NAME_RECT_OBJ_VIEW_ASSOCTYPE = "ASSOCTYPE"
COL_NAME_RECT_OBJ_VIEW_CLASSNAME = "CLASSNAME"
COL_NAME_RECT_OBJ_VIEW_CLSLBLSTATE = "CLSLBLSTATE"
COL_NAME_RECT_OBJ_VIEW_CLSLBLTIME = "CLSLBLTIME"
COL_NAME_RECT_OBJ_VIEW_CLSLBLUSER = "CLSLBLUSER"
COL_NAME_RECT_OBJ_VIEW_OBJWIDTH = "OBJWIDTH"
COL_NAME_RECT_OBJ_VIEW_OBJLENGTH = "OBJLENGTH"
COL_NAME_RECT_OBJ_VIEW_OBJHEIGHT = "OBJHEIGHT"
COL_NAME_RECT_OBJ_VIEW_DIMLBLSTATE = "DIMLBLSTATE"
COL_NAME_RECT_OBJ_VIEW_DIMLBLTIME = "DIMLBLTIME"
COL_NAME_RECT_OBJ_VIEW_DIMLBLUSER = "DIMLBLUSER"
COL_NAME_RECT_OBJ_VIEW_ZLAYER = "ZLAYER"
COL_NAME_RECT_OBJ_VIEW_ZOVERGROUND = "ZOVERGROUND"
COL_NAME_RECT_OBJ_VIEW_ZOLBLSTATE = "ZOLBLSTATE"
COL_NAME_RECT_OBJ_VIEW_ZOLBLUSER = "ZOLBLUSER"
COL_NAME_RECT_OBJ_VIEW_ZOLBLTIME = "ZOLBLTIME"
COL_NAME_RECT_OBJ_VIEW_KINLBLSTATE = "KINLBLSTATE"
COL_NAME_RECT_OBJ_VIEW_KINLBLTIME = "KINLBLTIME"
COL_NAME_RECT_OBJ_VIEW_KINLBLUSER = "KINLBLUSER"
COL_NAME_RECT_OBJ_VIEW_RECTOBJ_IS_DELETED = "RECTOBJ_IS_DELETED"
COL_NAME_RECT_OBJ_VIEW_UUID = "UUID"

# TABLE_NAME_OBJ_TESTCASES_VIEW = "OBJ_VIEW_TESTCASES"
COL_NAME_TEST_CASES_VIEW_TESTCASEID = "TESTCASEID"
COL_NAME_TEST_CASES_VIEW_TESTCASENAME = "TESTCASENAME"
COL_NAME_TEST_CASES_VIEW_RECTOBJID = "RECTOBJID"
COL_NAME_TEST_CASES_VIEW_BEGINABSTS = "BEGINABSTS"
COL_NAME_TEST_CASES_VIEW_ENDABSTS = "ENDABSTS"
COL_NAME_TEST_CASES_VIEW_LBLUSER = "LBLUSER"
COL_NAME_TEST_CASES_VIEW_LBLSTATE = "LBLSTATE"
COL_NAME_TEST_CASES_VIEW_LBLMODTIME = "LBLMODTIME"

# TABLE_NAME_OBJ_ACCLANERELATION_VIEW = "OBJ_VIEW_ACCLANERELATION"
COL_NAME_ACC_LANE_REL_VIEW_LBLUSER = "LBLUSER"
COL_NAME_ACC_LANE_REL_VIEW_ACCLANERELID = "ACCLANERELID"
COL_NAME_ACC_LANE_REL_VIEW_RECTOBJID = "RECTOBJID"
COL_NAME_ACC_LANE_REL_VIEW_BEGINABSTS = "BEGINABSTS"
COL_NAME_ACC_LANE_REL_VIEW_ENDABSTS = "ENDABSTS"
COL_NAME_ACC_LANE_REL_VIEW_LANENAME = "LANENAME"
COL_NAME_ACC_LANE_REL_VIEW_LANEASSOCWEIGHT = "LANEASSOCWEIGHT"
COL_NAME_ACC_LANE_REL_VIEW_LBLMODTIME = "LBLMODTIME"
COL_NAME_ACC_LANE_REL_VIEW_LBLSTATE = "LBLSTATE"

# TABLE_NAME_OBJ_LBLCHECKPOINTS = "OBJ_LBLCHECKPOINTS"
COL_NAME_LBLCHECKPOINTS_CHECKPOINTID = "CHECKPOINTID"
COL_NAME_LBLCHECKPOINTS_NAME = "NAME"

# TABLE_NAME_OBJ_RECTOBJ_CHECKPOINTMAP = "OBJ_RECTOBJ_CHECKPOINTMAP"
COL_NAME_RECTOBJ_CHECKPOINTMAP_RECTOBJMAPID = "RECTOBJMAPID"
COL_NAME_RECTOBJ_CHECKPOINTMAP_RECTOBJID = "RECTOBJID"
COL_NAME_RECTOBJ_CHECKPOINTMAP_CHECKPOINTID = "CHECKPOINTID"

# TABLE_NAME_OBJ_EGOKINE_CHECKPOINTMAP = "OBJ_EGOKINE_CHECKPOINTMAP"
COL_NAME_EGOKINE_CHECKPOINTMAP_EGOMAPID = "EGOMAPID"
COL_NAME_EGOKINE_CHECKPOINTMAP_MEASID = "MEASID"
COL_NAME_EGOKINE_CHECKPOINTMAP_CHECKPOINTID = "CHECKPOINTID"
COL_NAME_EGOKINE_CHECKPOINTMAP_IS_ADMA = "IS_ADMA"

# TABLE_NAME_ACC_LANEDEL_ACTIVITY = "OBJ_ACCLANEDELETE_ACTIVITY"
COL_NAME_ACCLANEDEL_REL_ACCLANERELID = "ACCLANERELID"
COL_NAME_ACCLANEDEL_RECTOBJID = "RECTOBJID"
COL_NAME_ACCLANEDEL_BEGINABSTS = "BEGINABSTS"
COL_NAME_ACCLANEDEL_ENDABSTS = "ENDABSTS"
COL_NAME_ACCLANEDEL_LANEID = "LANEID"
COL_NAME_ACCLANEDEL_LANEASSOCWEIGHT = "LANEASSOCWEIGHT"
COL_NAME_ACCLANEDEL_LBLSTATEID = "LBLSTATEID"
COL_NAME_ACCLANEDEL_LBLMODTIME = "LBLMODTIME"
COL_NAME_ACCLANEDEL_LBLBY = "LBLBY"
COL_NAME_ACCLANEDEL_DELBY = "DELBY"
COL_NAME_ACCLANEDEL_DELTIME = "DELTIME"

# TABLE_NAME_ACC_LANEDEL_ACTIVITY_VIEW = "OBJ_VIEW_ACCLANEDELETE_ACTIVITY"
COL_NAME_ACCLANEDEL_VIEW_ACCLANERELID = "ACCLANERELID"
COL_NAME_ACCLANEDEL_VIEW_RECTOBJID = "RECTOBJID"
COL_NAME_ACCLANEDEL_VIEW_BEGINABSTS = "BEGINABSTS"
COL_NAME_ACCLANEDEL_VIEW_ENDABSTS = "ENDABSTS"
COL_NAME_ACCLANEDEL_VIEW_LANENAME = "LANENAME"
COL_NAME_ACCLANEDEL_VIEW_LANEASSOCWEIGHT = "LANEASSOCWEIGHT"
COL_NAME_ACCLANEDEL_VIEW_LBLSTATE = "LBLSTATE"
COL_NAME_ACCLANEDEL_VIEW_LBLMODTIME = "LBLMODTIME"
COL_NAME_ACCLANEDEL_VIEW_LBLUSER = "LBLUSER"
COL_NAME_ACCLANEDEL_VIEW_DELUSER = "DELUSER"
COL_NAME_ACCLANEDEL_VIEW_DELTIME = "DELTIME"

PATH_SEPARATOR = "/"

# Test cases
TEST_CASE_TYPE_APPROACH = "approach"
TEST_CASE_TYPE_CUTIN = "cutin"
TEST_CASE_TYPE_CUTOUT = "cutout"

IDENT_STRING = DBOBJ


# - classes -----------------------------------------------------------------------------------------------------------
class BaseObjDataDB(BaseDB):
    """**base implementation of the OBJ Data Database**

    For the first connection to the DB for obj tables just create a new instance of this class like

    .. python::

        from stk.db.obj.objdata import BaseObjDataDB

        dbobj = BaseObjDataDB("ARS4XX")   # or use "MFC4XX", "VGA" or path/name of sqlite file

    If already some connection to another table of the DB is created use that one to speed up your code:

    .. python::

        dbobj = BaseObjDataDB(dbxxx.db_connection)

    The connection is closed when the first instance using it is deleted.

    More optional keywords are described at `BaseDB` class initialization.

    """
    # ===================================================================
    # Constraint DB Libary Interface for public use
    # ===================================================================

    # ===================================================================
    # Handling of database
    # ===================================================================
    def __init__(self, *args, **kwargs):
        """
        Constructor to initialize BaseObjDataDB to represent OBJ subschema

        :keyword db_connection: The database connection to be used
        :type db_connection: cx_oracle.Connection, pydodbc.Connection, sqlite3.Connection, sqlce.Connection
        :keyword table_prefix: The table name prefix which is usually master schema name
        :type table_prefix: str
        """
        kwargs['strIdent'] = DBOBJ
        BaseDB.__init__(self, *args, **kwargs)

        self.__object_map = {}

    def add_adma_kinematics(self, adma_kin_map):
        """
        Add a new set of data into the OBJ_ADMAObjKinematics table.

        Kinematics data related to Adma or rt range type rectangular object

        :param adma_kin_map: record to be insert
        :type adma_kin_map: dict
        """
        try:
            self.add_generic_data(adma_kin_map, TABLE_NAME_ADMA_KINEMATICS)
        except StandardError as ex:
            self._log.error(str(ex))
            return False

        return True

    def AddAdmaKinematics(self, adma_kin_map):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "AddAdmaKinematics" is deprecated use '
        msg += '"add_adma_kinematics" instead'
        warn(msg, stacklevel=2)
        return self.add_adma_kinematics(adma_kin_map)

    def add_kinematics(self, kin_map, table_name=None):
        """
        Add a new set of data into one of the OBJ_KINEMATICS* tables.

        :param kin_map: record to be insert
        :type  kin_map: dict
        :param table_name: name of table to add data to, default: OBJ_KINEMATICS
        :type  table_name: str
        :return: Boolean status True for successful insert or False if failed to insert
        :rtype: bool
        """
        if not table_name:
            table_name = TABLE_NAME_KINEMATICS
        try:
            self.add_generic_data(kin_map, table_name)
        except StandardError as ex:
            self._log.error(str(ex))
            return False

        return True

    def AddKinematics(self, kin_map):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "AddKinematics" is deprecated use '
        msg += '"add_kinematics" instead'
        warn(msg, stacklevel=2)
        return self.add_kinematics(kin_map)

    def add_test_case(self, rect_obj_id, test_case_type, begin_ts, end_ts,
                      user_id, lb_state=LBL_STATE_AUTO, lbl_modtime=None):
        """
        Add record into OBJ_TESTCASE table which represent Object Testcase

        :param rect_obj_id: rectangular object Id
        :type rect_obj_id: int
        :param test_case_type: test case type e.g. dropin, dropout
        :type test_case_type: str
        :param begin_ts: Begin Absolute Time stamp
        :type begin_ts: int
        :param end_ts: End Absolute Time stamp
        :type end_ts: int
        :param user_id: User Id which is primarkey from GBL_USER
        :type user_id: int
        :param lb_state: Label state e.g. manual, auto. Default auto
        :type lb_state: str
        :param lbl_modtime: Modification Date. Default Current Date
        :type lbl_modtime: str
        :return: Testcase Id which is primary key of the table
        :rtype: int
        """

#         if self.has_test_case(rect_obj_id, test_case_type):
#             self._log.warning("AddTestCase() failed as rect object has a test case.")
#             return

        test_case_type_id = self.get_test_case_type_id(test_case_type)
        label_state_id = self.get_label_state_id(lb_state)
        # userid           =  self.GetUser(login = os.environ["USERNAME"])

        test_case_map = {}
        tcid = self._get_next_id(TABLE_NAME_TEST_CASES, COL_NAME_TEST_CASES_TESTCASEID)
        test_case_map[COL_NAME_TEST_CASES_TESTCASEID] = tcid
        test_case_map[COL_NAME_TEST_CASES_TYPEID] = test_case_type_id
        test_case_map[COL_NAME_TEST_CASES_RECTOBJID] = rect_obj_id
        test_case_map[COL_NAME_TEST_CASES_BEGINABSTS] = begin_ts
        test_case_map[COL_NAME_TEST_CASES_ENDABSTS] = end_ts
        test_case_map[COL_NAME_TEST_CASES_LBLSTATEID] = label_state_id
        test_case_map[COL_NAME_TEST_CASES_LBLBY] = user_id
#       TimeStamp for LBLMODTIME will be current Time by default from Database
        if lbl_modtime is not None:
            test_case_map[COL_NAME_TEST_CASES_LBLMODTIME] = lbl_modtime

        self.add_generic_data(test_case_map, TABLE_NAME_TEST_CASES)
        return tcid

    def AddTestCase(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "AddTestCase" is deprecated use '
        msg += '"add_test_case" instead'
        warn(msg, stacklevel=2)
        return self.add_test_case(*args, **kw)

    def add_rectangular_object(self, obj):
        """Adds new object to database.

        :param obj: The general object record.
        :type obj: dict
        :return: Returns the object ID of newly inserted entry.
        :rtype: int
        """
        if self.sub_scheme_version < SUBSCHEMA_UUID_FEATURE:
            try:
                db_object_id = self.__get_db_rect_object_id(obj[COL_NAME_RECT_OBJ_RECTOBJID])
                if db_object_id is not None:
                    return db_object_id
            except:
                pass

        if self.sub_scheme_version < SUBSCHEMA_UUID_FEATURE:
            object_id = self.__get_next_rect_object_id()
            self.add_generic_data(obj, TABLE_NAME_RECTANGULAR_OBJECT)
        else:
            unique_uuid4 = str(uuid4())
            if COL_NAME_RECT_OBJ_UUID not in obj:
                obj[COL_NAME_RECT_OBJ_UUID] = unique_uuid4
            else:
                unique_uuid4 = obj[COL_NAME_RECT_OBJ_UUID]
            # obj[COL_NAME_RECT_OBJ_RECTOBJID] = None
            self.add_generic_data(obj, TABLE_NAME_RECTANGULAR_OBJECT)
            where = SQLBinaryExpr(COL_NAME_RECT_OBJ_UUID, OP_EQ,
                                  SQLLiteral(unique_uuid4))
            records = self.select_generic_data([COL_NAME_RECT_OBJ_RECTOBJID], [TABLE_NAME_RECTANGULAR_OBJECT], where)
            if len(records) == 1:
                object_id = records[0][COL_NAME_RECT_OBJ_RECTOBJID]
                obj.pop(COL_NAME_RECT_OBJ_UUID)
                self.update_generic_data({COL_NAME_RECT_OBJ_UUID: None}, TABLE_NAME_RECTANGULAR_OBJECT, where)
            else:
                object_id = None
        try:
            self.__object_map[obj[COL_NAME_RECT_OBJ_RECTOBJID]] = object_id
        except:
            pass
        # obj[COL_NAME_RECT_OBJ_RECTOBJID] = object_id

        # done
        return object_id

    def AddRectangularObject(self, obj):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "AddRectangularObject" is deprecated use '
        msg += '"add_rectangular_object" instead'
        warn(msg, stacklevel=2)
        return self.add_rectangular_object(obj)

    def update_rectangular_object(self, record, rectobjid):
        """
        Update rectangular object record for the given rectangular object Id

        :param record: record containing rect object attribute values
        :type record: dict
        :param rectobjid: Rectangular Object Id
        :type rectobjid: int
        """

        if COL_NAME_RECT_OBJ_RECTOBJID in record:
            record.pop(COL_NAME_RECT_OBJ_RECTOBJID)

        if rectobjid is not None:
            self.update_generic_data(record, TABLE_NAME_RECTANGULAR_OBJECT,
                                     SQLBinaryExpr(COL_NAME_RECT_OBJ_RECTOBJID, OP_EQ, rectobjid))
        else:
            self._log.error("Rectangular object Id was not provided")

    def UpdateRectangularObject(self, record, rectobjid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "UpdateRectangularObject" is deprecated use '
        msg += '"update_rectangular_object" instead'
        warn(msg, stacklevel=2)
        return self.update_rectangular_object(record, rectobjid)

    def delete_rectangular_object(self, rect_obj_id, remove=False):
        """ Deletes the given rectangular object from the database.

            *NOTE:* Instead of dropping the record from the database. The entry
            for this object will be updated to 'RECTOBJ_IS_DELETED' = 1.
            or delete the record depending on remove flag in argument

            Associated kinematics remain unchanged.

            :param rect_obj_id: The rectangular object id that is about to be deleted.
            :type rect_obj_id: int
            :param remove: False to update RECTOBJ_IS_DELETED' = 1 or Set True to delete the record
            :type remove: bool
            :return: The affected row count.
            :rtype: int
        """
        where = SQLBinaryExpr(COL_NAME_RECT_OBJ_RECTOBJID, OP_EQ, rect_obj_id)
        if not remove:
            record = {COL_NAME_RECT_OBJ_RECTOBJ_IS_DELETED: 1, }
            return self.update_generic_data(record, TABLE_NAME_RECTANGULAR_OBJECT, where)
        else:
            self.delete_generic_data(TABLE_NAME_RECTANGULAR_OBJECT, where)

    def DeleteRectangularObject(self, rect_obj_id, remove=False):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "DeleteRectangularObject" is deprecated use '
        msg += '"delete_rectangular_object" instead'
        warn(msg, stacklevel=2)
        return self.delete_rectangular_object(rect_obj_id, remove=remove)

    def add_ego_kinematics_adma(self, obj_adma_kine):
        """
        Insert new record into Object OBJ_EGOKINEMATICADMA table.

        :param obj_adma_kine: adma kinematic data record
        :type obj_adma_kine: dict
        :return: success status (True/False)
        :rtype: bool
        """
        try:
            self.add_generic_data(obj_adma_kine, TABLE_NAME_EGO_KINEMATICS_ADMA)
            return True
        except:
            return False

    def AddEgoKinematicsAdma(self, obj_adma_kine):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "AddEgoKinematicsAdma" is deprecated use '
        msg += '"add_ego_kinematics_adma" instead'
        warn(msg, stacklevel=2)
        return self.add_ego_kinematics_adma(obj_adma_kine)

    def addEgoKinematicsAdma(self, adma):  # pylint: disable=C0103
        """
        Adds a new entry to table OBJ_EGOKINEMATICS_ADMA

        *NOTE:* The function is deprecated

        :param adma: adma data to be added (dict of values)
        :return: success status (True/False)
        :rtype: bool
        """
        """deprecated"""
        msg = 'Method "addEgoKinematicsAdma" is deprecated use '
        msg += '"add_ego_kinematics_adma" instead'
        warn(msg, stacklevel=2)
        return self.add_ego_kinematics_adma(adma)

    def add_probs_cam(self, prob_record):
        """
        Add new entry for OBJ_PROB_C

        :param prob_record:
        :type prob_record:
        :return: success status (True/False)
        :rtype: bool
        """
        try:
            self.add_generic_data(prob_record, TABLE_NAME_PROBS_CAM)
            return True
        except:
            return False

    def AddProbsCam(self, prob_record):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "AddProbsCam" is deprecated use '
        msg += '"add_probs_cam" instead'
        warn(msg, stacklevel=2)
        return self.add_probs_cam(prob_record)

    def addProbsCam(self, prob):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "addProbsCam" is deprecated use '
        msg += '"add_probs_cam" instead'
        warn(msg, stacklevel=2)
        return self.add_probs_cam(prob)

    def delete_adma_kinematics(self, rect_obj_id):
        """
        Deletes a Adma object kinematics from OBJ_KinematicsADMA table
        for given rectangular object Id

        :param rect_obj_id: Rectangular Object id
        :type rect_obj_id: int
        :return: Number of rows deleted
        :rtype: int
        """
        condition = SQLBinaryExpr(COL_NAME_ADMA_KINEMATICS_RECTOBJID, OP_EQ, rect_obj_id)
        rowcount = self.delete_generic_data(TABLE_NAME_ADMA_KINEMATICS, condition)
        return rowcount

    def DeleteAdmaKinematics(self, rect_obj_id):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "DeleteAdmaKinematics" is deprecated use '
        msg += '"delete_adma_kinematics" instead'
        warn(msg, stacklevel=2)
        return self.delete_adma_kinematics(rect_obj_id)

    def delete_adma_kin_rect_obj(self, rectobj_id):
        """
        Deletes Rectangular object record OBJ_RectangularObject table for given rectangular object Id.
        If the kinematics are not deleted before calling this function StandardError will be raise
        *NOTE:* This function deletes the record from table unlike `DeleteRectangularObject`

        :param rectobj_id: The identifier of the rectangular object.
        :type rectobj_id: int
        :return: Number of rows deleted
        :rtype: int
        """
        kin_table = self.get_rect_object_kinematics(rectobj_id)

        if len(kin_table) > 0:
            self._log.error("Error: Failed to delete kinematics prior to rect obj delete. " + str(rectobj_id))
            raise StandardError("Failed to delete kinematics prior to rect obj delete. '%s'." % rectobj_id)

        condition = SQLBinaryExpr(COL_NAME_RECT_OBJ_RECTOBJID, OP_EQ, rectobj_id)
        rowcount = self.delete_generic_data(TABLE_NAME_RECTANGULAR_OBJECT, condition)
        return rowcount

    def DeleteAdmaKinRectObj(self, rectobj_id):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "DeleteAdmaKinRectObj" is deprecated use '
        msg += '"delete_adma_kin_rect_obj" instead'
        warn(msg, stacklevel=2)
        return self.delete_adma_kin_rect_obj(rectobj_id)

    def get_adma_kin_range(self, kinabsts1, kinabsts2, select_list=None):
        """
        Get Kinematics data from AdmaObjKinematics table based on time stamp range from OBJ_KinematicsADMA table

        :param kinabsts1: Start Time stamp
        :type kinabsts1: int
        :param kinabsts2: End Time stamp
        :type kinabsts2: int
        :param select_list: list of column name for which values are needed. Default all columns in the table
        :type select_list: list
        :return: List of records
        :rtype: list

        **1. Example:**

        .. python::
            # Get ADMA Object Kinematic data from 150 to 3000
            record = self.__objDb.GetAdmaKinRange(150, 3000)
        """
        if select_list is None:
            select_list = ['*']
        condition = SQLBinaryExpr(COL_NAME_ADMA_KINEMATICS_KINABSTS,
                                  OP_GT, kinabsts1)
        condition = SQLBinaryExpr(condition, OP_AND,
                                  SQLBinaryExpr(COL_NAME_ADMA_KINEMATICS_KINABSTS, OP_LT, kinabsts2))

        adma_obj_kinematics_list = self.select_generic_data(select_list, [TABLE_NAME_ADMA_KINEMATICS], condition)

        return adma_obj_kinematics_list

    def GetAdmaKinRange(self, kinabsts1, kinabsts2, select_list=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetAdmaKinRange" is deprecated use '
        msg += '"get_adma_kin_range" instead'
        warn(msg, stacklevel=2)
        return self.get_adma_kin_range(kinabsts1, kinabsts2, select_list)

    def get_adma_associated_type_id(self):
        """
        Get associated type Id for adma from OBJ_ASSOCIATIONTYPE table

        :return: Association type id
        :rtype: int
        """
        return self.get_object_association_type_id(DEFAULT_ADMA_NAME)

    def GetAdmaAssociatedTypeId(self):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetAdmaAssociatedTypeId" is deprecated use '
        msg += '"get_adma_associated_type_id" instead'
        warn(msg, stacklevel=2)
        return self.get_adma_associated_type_id()

    def get_rt_range_associated_type_id(self):
        """
        Get Association type id for RT RANGE

        :return: Association type id
        :rtype: int
        """
        try:
            return self.get_object_association_type_id(DEFAULT_RT_RANGE_NAME)
        except StandardError:
            return None

    def GetRtRangeAssociatedTypeId(self):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetRtRangeAssociatedTypeId" is deprecated use '
        msg += '"get_rt_range_associated_type_id" instead'
        warn(msg, stacklevel=2)
        return self.get_rt_range_associated_type_id()

    def get_adma_rect_obj_id(self, meas_id):
        """
        Get all Rectangular object Ids for given measurement
        with ADMA association type

        :param meas_id: mesurement id
        :type meas_id: int
        :return: List of rectangular object Id
        :rtype: list
        """
        adma_id = self.get_adma_associated_type_id()
        obj_ids = self.__get_associated_rect_obj_id(meas_id, adma_id)
        if obj_ids is not None:
            if len(obj_ids) == 1:
                return obj_ids[0]
            else:
                self._log.error("Only one Adma object expected per measurement file")
                return None

        return obj_ids

    def GetAdmaRectObjId(self, meas_id):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetAdmaRectObjId" is deprecated use '
        msg += '"get_adma_rect_obj_id" instead'
        warn(msg, stacklevel=2)
        return self.get_adma_rect_obj_id(meas_id)

    def get_rt_range_rect_obj_id(self, meas_id):
        """
        Get all Rectangular object Ids for given measurement with
        RT RANGE association type

        :param meas_id: mesurement id
        :type meas_id: int
        :return: List of rectangular object Id
        :rtype: list

        **1. Example:**

        .. python::
            # Get rect object id list meaurement Id 302
            record = self.__objDb.GetRtRangeRectObjId(302)
        """
        rtrange_id = self.get_rt_range_associated_type_id()
        obj_ids = self.__get_associated_rect_obj_id(meas_id, rtrange_id)
        return obj_ids

    def GetRtRangeRectObjId(self, meas_id):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetRtRangeRectObjId" is deprecated use '
        msg += '"get_rt_range_rect_obj_id" instead'
        warn(msg, stacklevel=2)
        return self.get_rt_range_rect_obj_id(meas_id)

    def __get_associated_rect_obj_id(self, meas_id, assoc_id):
        """
        Get all Rectangular object Ids for given measurement and
        association type Id

        :param meas_id: mesurement id
        :type meas_id: int
        :param assoc_id: association type id
        :type assoc_id: int
        :return: List of rectangular object Id
        :rtype: list
        """
        assoc_rectobj_list = None
        if assoc_id is not None:
            condition = SQLBinaryExpr(COL_NAME_ASSOC_TYPE_ASSOCTYPEID, OP_EQ, assoc_id)
            condition = SQLBinaryExpr(condition, OP_AND, SQLBinaryExpr(COL_NAME_RECT_OBJ_MEASID,
                                                                       OP_EQ, meas_id))
            entries = self.select_generic_data([COL_NAME_RECT_OBJ_RECTOBJID], [TABLE_NAME_RECTANGULAR_OBJECT],
                                               condition)
            if len(entries) > 0:
                assoc_rectobj_list = []
                for entry in entries:
                    assoc_rectobj_list.append(entry[COL_NAME_RECT_OBJ_RECTOBJID])
            return assoc_rectobj_list

    def get_approach_label_for_rect(self, rect_id):
        """
        Get Testcase record for given rectangular object Id labeled as 'approach' tescase

        :param rect_id: Rectangular Object Id
        :type rect_id: int
        :return: List of all label approached label testcase records
        :rtype: list

        **1. Example:**

        .. python::
            # Get approach label testcses for rect object id 2100
            record = self.__objDb.GetApproachLabelForRect(2100)
        """
        return self.get_object_test_case(rect_id, "approach")

    def GetApproachLabelForRect(self, rect_id):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetApproachLabelForRect" is deprecated use '
        msg += '"get_approach_label_for_rect" instead'
        warn(msg, stacklevel=2)
        return self.get_approach_label_for_rect(rect_id)

    def get_object_test_cases(self, rectobjid, testcase_name=None, select_list=None):
        """
        Get Object Test case record for the given rectangular object with optional criteria of testcase name

        :param rectobjid: Rectangular Object
        :type rectobjid: int
        :param testcase_name: testcase name e.g. dropin, approach. Default value is None to skip this criteria
        :type testcase_name: str
        :param select_list: List of column names for which values are needed. Default all column in the table
        :type select_list: list
        :return: List of label testcase records
        :rtype: list

        **1. Example:**

        .. python::
            # Get label testcses for rect object id 2100 labeld as dropin test case
            record = self.__objDb.get_object_test_cases(2100, 'dropin')
        """
        test_case_typeid = None
        if testcase_name is not None:
            test_case_typeid = self.get_test_case_type_id(testcase_name)

        # Get the approach labels.
        if select_list is None:
            select_list = [COL_NAME_TEST_CASES_TESTCASEID,
                           COL_NAME_TEST_CASES_TYPEID,
                           COL_NAME_TEST_CASES_RECTOBJID,
                           COL_NAME_TEST_CASES_BEGINABSTS,
                           COL_NAME_TEST_CASES_ENDABSTS]

        condition = SQLBinaryExpr(COL_NAME_TEST_CASES_RECTOBJID, OP_EQ, rectobjid)
        if test_case_typeid is not None:
            condition = SQLBinaryExpr(condition,
                                      OP_AND,
                                      SQLBinaryExpr(COL_NAME_TEST_CASES_TYPEID, OP_EQ, test_case_typeid))

        entries = self.select_generic_data(select_list, [TABLE_NAME_TEST_CASES], condition)
        return entries

    def GetObjectTestCases(self, rectobjid, testcase_name=None, select_list=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetObjectTestCases" is deprecated use '
        msg += '"get_object_test_cases" instead'
        warn(msg, stacklevel=2)
        return self.get_object_test_cases(rectobjid, testcase_name, select_list)

    def get_object_test_case(self, rectobjid, testcase_name):
        """
        Get Object Test case record for the given rectangular object

        :param rectobjid: Rectangular Object Id
        :type rectobjid: int
        :param testcase_name: test case name
        :type testcase_name: str
        :return: list of all testcase record
        :rtype: list

        **1. Example:**

        .. python::
            # Get label testcses for rect object ids 2100 labeld as dropin test case
            record = self.__objDb.get_object_test_case(2100, 'dropin')
        """
        entries = self.get_object_test_cases(rectobjid, testcase_name)

        if len(entries) == 1:
            # Found approach
            return entries[0]
        elif len(entries) > 1:
            self._log.error("No TestCase found for RectObjectID but it is ambigeous" + str(rectobjid))
        return []

    def GetObjectTestCase(self, rectobjid, testcase_name):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetObjectTestCase" is deprecated use '
        msg += '"get_object_test_case" instead'
        warn(msg, stacklevel=2)
        return self.get_object_test_case(rectobjid, testcase_name)

    def get_labeled_object_kinematics(self, measid, kinabsts, incl_deleted=True):
        """
        Gets object kinematic record for all rectangular object
        for given measurement id at the specfied time stamp

        :param measid: Measurement Id
        :type measid: int
        :param kinabsts: Time stamp
        :type kinabsts: int
        :param incl_deleted: Boolean flag to incldue or exclude kinematics for deleted rect objects
        :type incl_deleted: Boolean
        :return: List of Object Kinematic records
        :rtype: list

        **1. Example:**

        .. python::
            # Get Object kinematic data for rect object ids 2100 at timestamp 5323423
            record = self.__objDb.GetLabeledObjectKinematics(2100, 5323423)
        """

        rect_obj_rectobjid = SQLColumnExpr(SQLTableExpr(TABLE_NAME_RECTANGULAR_OBJECT), COL_NAME_RECT_OBJ_RECTOBJID)
        kinematics_rectobjid = SQLColumnExpr(SQLTableExpr(TABLE_NAME_KINEMATICS), COL_NAME_KINEMATICS_RECTOBJID)
        is_deleted = SQLColumnExpr(SQLTableExpr(TABLE_NAME_RECTANGULAR_OBJECT), COL_NAME_RECT_OBJ_RECTOBJ_IS_DELETED)

        select_list = [kinematics_rectobjid,
                       COL_NAME_KINEMATICS_KINABSTS,
                       COL_NAME_KINEMATICS_RELDISTX,
                       COL_NAME_KINEMATICS_RELDISTY,
                       COL_NAME_KINEMATICS_RELVELX]

        join_expr = SQLTernaryExpr(SQLTableExpr(TABLE_NAME_RECTANGULAR_OBJECT),
                                   OP_INNER_JOIN,
                                   SQLTableExpr(TABLE_NAME_KINEMATICS),
                                   OP_ON,
                                   SQLBinaryExpr(rect_obj_rectobjid, OP_EQ, kinematics_rectobjid))

        condition = SQLBinaryExpr(COL_NAME_RECT_OBJ_MEASID,
                                  OP_EQ,
                                  measid)
        if not incl_deleted:
            condition = SQLBinaryExpr(condition, OP_AND, SQLBinaryExpr(is_deleted, OP_EQ, 0))

        where_expr = SQLBinaryExpr(condition, OP_AND, SQLBinaryExpr(COL_NAME_ADMA_KINEMATICS_KINABSTS, OP_EQ,
                                                                    kinabsts))

        obj_kinematic_list = self.select_generic_data(select_list, table_list=[join_expr], where=where_expr)

        return obj_kinematic_list

    def GetLabeledObjectKinematics(self, measid, kinabsts):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetLabeledObjectKinematics" is deprecated use '
        msg += '"get_labeled_object_kinematics" instead'
        warn(msg, stacklevel=2)
        return self.get_labeled_object_kinematics(measid, kinabsts)

    def get_labeled_lane_association_for_meas_id(self, measid,  # pylint: disable=C0103
                                                 lblstateid=None,
                                                 select_list=None):
        """
        Get list of lane association record for all rectangular object for specified measurement

        :param measid: measurement id
        :type measid: int
        :param lblstateid: Criterea as label state id. Default criteria will be ignore
        :type lblstateid: int
        :param select_list: list of column to be select default all
        :type select_list: list of string
        :return: List of record
        :rtype: list

        **1. Example:**

        .. python::
            # Get Labeled lane relation for measurement ID 21
            record = self.__objDb.get_labeled_lane_association_for_meas_id(21)
        """
        if select_list is None:
            select_list = ['*']
        condition = SQLBinaryExpr(COL_NAME_RECT_OBJ_MEASID, OP_EQ, measid)

        if lblstateid is not None:
            where_expr = SQLBinaryExpr(condition, OP_AND,
                                       SQLBinaryExpr(COL_NAME_ACC_LANE_REL_LBLSTATEID,
                                                     OP_EQ, lblstateid))
        else:
            where_expr = condition

        rect_obj_rectobjid = SQLColumnExpr(SQLTableExpr(TABLE_NAME_RECTANGULAR_OBJECT), COL_NAME_RECT_OBJ_RECTOBJID)
        acc_lane_rectobjid = SQLColumnExpr(SQLTableExpr(TABLE_NAME_ACC_LANE_REL), COL_NAME_ACC_LANE_REL_RECTOBJID)

        join_expr = SQLTernaryExpr(SQLTableExpr(TABLE_NAME_ACC_LANE_REL),
                                   OP_INNER_JOIN,
                                   SQLTableExpr(TABLE_NAME_RECTANGULAR_OBJECT),
                                   OP_NOP,
                                   SQLFuncExpr(OP_USING, COL_NAME_RECT_OBJ_RECTOBJID))

        lane_association_list = self.select_generic_data(select_list, table_list=[join_expr], where=where_expr)

        return lane_association_list

    def GetLabeledLaneAssociationForMeasId(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetLabeledLaneAssociationForMeasId" is deprecated use '
        msg += '"get_labeled_lane_association_for_meas_id" instead'
        warn(msg, stacklevel=2)
        return self.get_labeled_lane_association_for_meas_id(*args, **kw)

    def get_labeled_lane_association(self, rectobjid, startTimestamp=None,  # pylint: disable=C0103
                                     stopTimestamp=None, laneid=None,  # pylint: disable=C0103
                                     lblstate=None, select_list=None, order_by=None):
        """
        Gets lane association record for given rect object Id with optional argument as filter criteria
        from OBJ_ACCLANERELATION table

        :param rectobjid: The rectangular object id.
        :type rectobjid:
        :param startTimestamp: Start time stamp
        :type startTimestamp: int
        :param stopTimestamp: stop time stamp
        :type stopTimestamp: int
        :param laneid: Lane Id corresponding to lane mention in OBJ_ACCLANETYPES
        :type laneid: int
        :param lblstate: Label state id corresponding to label states mentioned in OBJ_LBLSTATE
        :type lblstate: int
        :param select_list: list of column name for which values are desired
        :type select_list: list
        :param order_by: list of column by which values should be sorted.
        :type order_by: list
        :return: List of record
        :rtype: list

        **1. Example:**

        .. python::
            # Get Labeled lane relation for rectangular object 2100
            record = self.__objDb.GetLabeledLaneAssociation(2100)

        **2. Example:**

        .. python::
            # Get Labeled lane relation for rectangular object 2100 for time stampe range 345-6700
            record = self.__objDb.GetLabeledLaneAssociation(12, 345, 6700)

        **3. Example:**

        .. python::
            # Get Labeled lane relation for rectangular object 2100 for time stampe range 345-6700 at lane id 2
            record = self.__objDb.GetLabeledLaneAssociation(12, 345, 6700, 2)
        """
        if select_list is None:
            select_list = ['*']
        condition = self.__get_labeled_lane_association_condition(rectobjid, startTimestamp,
                                                                  stopTimestamp, laneid, lblstate)

        lane_association_list = self.select_generic_data(select_list, [TABLE_NAME_ACC_LANE_REL],
                                                         where=condition, order_by=order_by)

        return lane_association_list

    def GetLabeledLaneAssociation(self, rectobjid, startTimestamp=None, stopTimestamp=None,  # pylint: disable=C0103
                                  laneid=None, lblstate=None, select_list=None, order_by=None):
        """deprecated"""
        msg = 'Method "GetLabeledLaneAssociation" is deprecated use '
        msg += '"get_labeled_lane_association" instead'
        warn(msg, stacklevel=2)
        return self.get_labeled_lane_association(rectobjid,
                                                 startTimestamp,
                                                 stopTimestamp,
                                                 laneid, lblstate,
                                                 select_list, order_by)

    def get_last_deleted_lane_assocation_date(self, recotbjid):  # pylint: disable=C0103
        """
        Get Last delete activity date perform on lane label for given rectangular object
        :param recotbjid: Rectangular object Id
        :type recotbjid: int
        :return: last delete active date
        :rtype: DateTime
        """

        max_date = SQLBinaryExpr(str(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_MAX], COL_NAME_ACCLANEDEL_DELTIME)),
                                 OP_AS, COL_NAME_ACCLANEDEL_DELTIME)

        select_list = [COL_NAME_ACCLANEDEL_RECTOBJID, max_date]

        table_list = [TABLE_NAME_ACC_LANEDEL_ACTIVITY]

        condition = self.__get_labeled_lane_association_condition(recotbjid)
        lastdel_lane = self.select_generic_data(select_list=select_list, table_list=table_list, where=condition,
                                                group_by=[COL_NAME_ACCLANEDEL_RECTOBJID])
        if len(lastdel_lane) > 1:
            raise StandardError("Expecting one row for last modified date of ACC Lane relation")
        elif len(lastdel_lane) == 1:
            return lastdel_lane[0][COL_NAME_ACCLANEDEL_DELTIME]
        else:
            return None

    def add_labeled_lane_association(self, record):
        """
        Add LabeledLaneRelation Record for rectangular object

        :param record: lane record
        :type record: dict
        """

        self.add_generic_data(record, TABLE_NAME_ACC_LANE_REL)

    def AddLabeledLaneAssociation(self, record):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "AddLabeledLaneAssociation" is deprecated use '
        msg += '"add_labeled_lane_association" instead'
        warn(msg, stacklevel=2)
        return self.add_labeled_lane_association(record)

    def delete_labeled_lane_association(self, rectobjid, log_activity=True):
        """
        Delete Lane Relation data for rect object Id

        :param rectobjid: rectangular Object Id
        :type rectobjid: int
        :return: Number of rows effected
        :rtype: int

        **1. Example:**

        .. python::
            # Delete lane relation data for rectangular object id 23
            self.__objDb.DeleteLabeledLaneAssociation(23)
        """
        if rectobjid is not None:
            condition = SQLBinaryExpr(COL_NAME_ACC_LANE_REL_RECTOBJID, OP_EQ, rectobjid)
            if self.sub_scheme_version >= SUBSCHEMA_LANEDEL_FEATURE and log_activity:
                lane_lbl_entries = self.get_labeled_lane_association(rectobjid)
                self.add_labeld_lane_delete_activity(lane_lbl_entries)

            rowcount = self.delete_generic_data(TABLE_NAME_ACC_LANE_REL, condition)
            return rowcount

    def add_labeld_lane_delete_activity(self, lane_lbl_entries):
        """
        Add records into obj_acclane_Delete_activity
        :param lane_lbl_entries: list of dictionary records
        :type lane_lbl_entries: list
        """
        for entry in lane_lbl_entries:
            if COL_NAME_ACCLANEDEL_DELBY not in entry:
                entry[COL_NAME_ACCLANEDEL_DELBY] = self.current_gbluserid
            self.add_generic_data(entry, TABLE_NAME_ACC_LANEDEL_ACTIVITY)

    def delete_labeld_lane_delete_activity(self, rectobjid):
        """
        Delete lane delete history for given rectangular object
        :param rectobjid: rect object Id
        :type rectobjid: Integer
        """
        condition = SQLBinaryExpr(COL_NAME_ACC_LANE_REL_RECTOBJID, OP_EQ, SQLLiteral(rectobjid))
        self.delete_generic_data(TABLE_NAME_ACC_LANEDEL_ACTIVITY, condition)

    def get_lane_delete_activity(self, rectobjid):
        """
        Get lane delete activty record for given rect object Id
        :param rectobjid: rect object Id
        :type rectobjid: int
        """
        condition = SQLBinaryExpr(COL_NAME_ACC_LANE_REL_RECTOBJID, OP_EQ, SQLLiteral(rectobjid))
        self.select_generic_data(self.GetQualifiedTableName(TABLE_NAME_ACC_LANE_REL), condition)

    def DeleteLabeledLaneAssociation(self, rectobjid, log_activity=True):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "DeleteLabeledLaneAssociation" is deprecated use '
        msg += '"delete_labeled_lane_association" instead'
        warn(msg, stacklevel=2)
        return self.delete_labeled_lane_association(rectobjid, log_activity=log_activity)

    @staticmethod
    def __get_labeled_lane_association_condition(rectobjid, startTimestamp=None,  # pylint: disable=C0103
                                                 stopTimestamp=None, laneid=None,  # pylint: disable=C0103
                                                 lblstate=None):
        """
        Prepare Sql Expression for where condition

        :param rectobjid: rectangular object id
        :type rectobjid: int
        :param startTimestamp: start time stamp
        :type startTimestamp: int
        :param stopTimestamp: stop time stamp
        :type stopTimestamp: int
        :param laneid: lane id from database
        :type laneid: int
        :param lblstate: lable state
        :type lblstate: int
        :return: SQL Condition representing filter criteria
        :rtype: SQLBinartExpression
        """
        cond = SQLBinaryExpr(COL_NAME_ACC_LANE_REL_RECTOBJID, OP_EQ, rectobjid)

        if startTimestamp is not None and stopTimestamp is None:
            condition2 = SQLBinaryExpr(COL_NAME_ACC_LANE_REL_BEGINABSTS, OP_LEQ, startTimestamp)
            condition3 = SQLBinaryExpr(COL_NAME_ACC_LANE_REL_ENDABSTS, OP_GEQ, startTimestamp)
            condition23 = SQLBinaryExpr(condition2, OP_AND, condition3)
            cond = SQLBinaryExpr(cond, OP_AND, condition23)

        if startTimestamp is not None and stopTimestamp is not None:
            betweencondition1 = SQLTernaryExpr(COL_NAME_ACC_LANE_REL_BEGINABSTS, OP_BETWEEN,
                                               startTimestamp, OP_AND, stopTimestamp)
            betweencondition2 = SQLTernaryExpr(COL_NAME_ACC_LANE_REL_ENDABSTS, OP_BETWEEN, startTimestamp,
                                               OP_AND, SQLLiteral(stopTimestamp))
            betweencondition3 = SQLTernaryExpr(COL_NAME_ACC_LANE_REL_BEGINABSTS, OP_LEQ, startTimestamp,
                                               OP_AND, SQLBinaryExpr(COL_NAME_ACC_LANE_REL_ENDABSTS, OP_GEQ,
                                                                     stopTimestamp))

            condition2 = SQLTernaryExpr(betweencondition1, OP_OR, betweencondition2, OP_OR, betweencondition3)
            cond = SQLBinaryExpr(cond, OP_AND, condition2)

        if laneid is not None:
            condition4 = SQLBinaryExpr(COL_NAME_ACC_LANE_REL_LANEID, OP_EQ, laneid)
            cond = SQLBinaryExpr(cond, OP_AND, condition4)

        if lblstate is not None:
            condition5 = SQLBinaryExpr(COL_NAME_ACC_LANE_REL_LBLSTATEID, OP_EQ, lblstate)
            cond = SQLBinaryExpr(cond, OP_AND, condition5)

        return cond

    def get_rad_kin_range(self, kinabsts1, kinabsts2, select_list=None):
        """
        Get a data range form the ObjKinematics table based on KINABSTS.

        :param kinabsts1: Start absoluate time stamp
        :type kinabsts1: int
        :param kinabsts2: End absoluate time stamp
        :type kinabsts2: int
        :param select_list: List of column names for which values are desireed
        :type select_list: list
        :return: List of record
        :rtype: list

        **1. Example:**

        .. python::
            # Get Object starting from absolute time stamp value 1299 till 400000
            self.__objDb.GetRadKinRange(1299, 400000)
        """
        if select_list is None:
            select_list = ['*']
        condition = SQLBinaryExpr(COL_NAME_KINEMATICS_KINABSTS, OP_GT, kinabsts1)
        condition = SQLBinaryExpr(condition, OP_AND, SQLBinaryExpr(COL_NAME_KINEMATICS_KINABSTS,
                                                                   OP_LT, kinabsts2))

        obj_kinematics_list = self.select_generic_data(select_list, [TABLE_NAME_KINEMATICS], condition)
        return obj_kinematics_list

    def GetRadKinRange(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetRadKinRange" is deprecated use '
        msg += '"get_rad_kin_range" instead'
        warn(msg, stacklevel=2)
        return self.get_rad_kin_range(*args, **kw)

    def get_ego_kinematics(self, measid, start_absts=None, end_absts=None):
        """
        Get EgoKinemtics data for given measurement along with optionally
        given time window based on start timestamp and end timestamp

        :param measid: measurement id
        :type measid: int
        :param start_absts: start absts optional
        :type start_absts: int
        :param end_absts: end absts optional
        :type end_absts: int

        **1. Example:**

        .. python::
            # Get Ego Kinematics for measurement within given time window
            ego_kines = self.__objDb.GetEgoKinematics(12, start_absts=10000, end_absts=2000)

        **2. Example:**

        .. python::
            # Get Ego Kinematics for measurement from given start time till end of measurement
            ego_kines = self.__objDb.GetEgoKinematics(12, start_absts=10000, end_absts=None)

        **3. Example:**

        .. python::
            # Get Ego Kinematics for measurement from given start time till end of measurement
            ego_kines = self.__objDb.GetEgoKinematics(12, start_absts=10000, end_absts=None)

        **4. Example:**

        .. python::
            # Get Ego Kinematics for measurement from given start of the measure time till the end time
            ego_kines = self.__objDb.GetEgoKinematics(12, start_absts=None, end_absts=10000)
        """
        select_list = ['*']
        condition = SQLBinaryExpr(COL_NAME_EGO_KINEMATICS_MEASID, OP_EQ, measid)
        if start_absts is not None:
            condition = SQLBinaryExpr(condition, OP_AND,
                                      SQLBinaryExpr(COL_NAME_EGO_KINEMATICS_KINABSTS, OP_GEQ, start_absts))
        if end_absts is not None:
            condition = SQLBinaryExpr(condition, OP_AND,
                                      SQLBinaryExpr(COL_NAME_EGO_KINEMATICS_KINABSTS, OP_LEQ, end_absts))

        ego_kinematics_list = self.select_generic_data(select_list, [TABLE_NAME_EGO_KINEMATICS],
                                                       condition, order_by=[COL_NAME_EGO_KINEMATICS_KINABSTS])

        return ego_kinematics_list

    def GetEgoKinematics(self, measid, start_absts=None, end_absts=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetEgoKinematics" is deprecated use '
        msg += '"get_ego_kinematics" instead'
        warn(msg, stacklevel=2)
        return self.get_ego_kinematics(measid, start_absts, end_absts)

    def get_rect_object_kinematics(self, rect_obj_id, select_list=None,
                                   start_kineabsts=None, stop_kineabsts=None,
                                   orderby=None):
        """
        Selects kinematics from database for a rectangular object.

        :param rect_obj_id: The rectangular object id.
        :type rect_obj_id: int
        :param select_list: Selected Columns (default ALL)
        :type select_list: list
        :param start_kineabsts: Start Time Stamp
        :type start_kineabsts: int
        :param stop_kineabsts: Stop Time Stamp
        :type stop_kineabsts: int
        :param orderby: List of column by which values should be sorted
        :type orderby: list
        :return: Returns the object kinematics as a list of dictionaries
        :rtype: list

        **1. Example:**

        .. python::
            # Get complete Object kinematcs for rectangular object Id 12
            obj_kines = self.__objDb.get_rect_object_kinematics(12)

        **2. Example:**

        .. python::
            # Get  Object kinematcs with given rectangular object Id= 12 from start time = 10000
            # till end of object life
            obj_kines = self.__objDb.get_rect_object_kinematics(12, start_kineabsts=10000)

        **3. Example:**

        .. python::
            # Get  Object kinematcs with given rectangular object Id= 12 from absolute timestamp= 10000 till 430000
            obj_kines = self.__objDb.get_rect_object_kinematics(12, start_kineabsts=10000, stop_kineabsts=430000)
        """
        if select_list is None:
            select_list = ['*']
        obj_record = self.get_rect_object_by_rect_obj_id(rect_obj_id)
        table_name = [TABLE_NAME_KINEMATICS]
        if obj_record is not None and len(obj_record) == 1:
            adma_id = self.get_adma_associated_type_id()
            rt_range_id = self.get_rt_range_associated_type_id()
            obj_assoc_id = obj_record[0][COL_NAME_RECT_OBJ_ASSOCTYPEID]

            if ((adma_id is not None and
                 obj_assoc_id == adma_id) or (rt_range_id is not None and
                                              obj_assoc_id == rt_range_id)):

                table_name = [TABLE_NAME_ADMA_KINEMATICS]

        condition = SQLBinaryExpr(COL_NAME_ADMA_KINEMATICS_RECTOBJID, OP_EQ, rect_obj_id)
        if start_kineabsts is not None and stop_kineabsts is not None:
            condition2 = SQLTernaryExpr(COL_NAME_KINEMATICS_KINABSTS, OP_BETWEEN,
                                        start_kineabsts, OP_AND, stop_kineabsts)
            condition = SQLBinaryExpr(condition, OP_AND, condition2)

        obj_kinematic_list = self.select_generic_data(select_list, table_name, condition, order_by=orderby)

        return obj_kinematic_list

    def GetRectObjectKinematics(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetRectObjectKinematics" is deprecated use '
        msg += '"get_rect_object_kinematics" instead'
        warn(msg, stacklevel=2)
        return self.get_rect_object_kinematics(*args, **kw)

    def get_rect_object_kinematics_array(self, rect_obj_id, select_list=None):  # pylint: disable=C0103
        """
        Selects kinematics from database for a rectangular object.

        If the rectangular object is an ADMA object, the data of adma kinematic table will be returned

        :param rect_obj_id: The rectangular object id.
        :type rect_obj_id: int
        :param select_list: Selected Columns (default ALL)
        :type select_list: list
        :return: Returns the object kinematics as a header and 2D array.
        :rtype: list

        **1. Example:**

        .. python::
            # Get Object kinematcs for rectangular object Id 125
            kine_list = self.__objDb.GetRectObjectKinematicsArray(125)
        """
        if select_list is None:
            select_list = ['*']
        obj_record = self.get_rect_object_by_rect_obj_id(rect_obj_id)

        obj_kinematic_list = []

        if obj_record is not None and len(obj_record) == 1:
            adma_id = self.get_adma_associated_type_id()
            rtrange_id = self.get_rt_range_associated_type_id()
            obj_assoc_id = obj_record[0][COL_NAME_RECT_OBJ_ASSOCTYPEID]
            if ((adma_id is not None and obj_assoc_id == adma_id) or
                    (rtrange_id is not None and obj_assoc_id == rtrange_id)):
                table_name = [TABLE_NAME_ADMA_KINEMATICS]
            else:
                table_name = [TABLE_NAME_KINEMATICS]

            condition = SQLBinaryExpr(COL_NAME_KINEMATICS_RECTOBJID, OP_EQ, rect_obj_id)
            obj_kinematic_list = self.select_generic_data_compact(select_list, table_name, condition)

        return obj_kinematic_list

    def GetRectObjectKinematicsArray(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetRectObjectKinematicsArray" is deprecated use '
        msg += '"get_rect_object_kinematics_array" instead'
        warn(msg, stacklevel=2)
        return self.get_rect_object_kinematics_array(*args, **kw)

    def get_rect_object_kinematics_begin_end(self, rect_obj_id):  # pylint: disable=C0103
        """
        Gets object kinematics STart and Stop time stamp which represent lifespan of object

        :param rect_obj_id: The rectangular object id.
        :type rect_obj_id: int
        :return: Returns the object kinematics map.
        :rtype: dict

        **1. Example:**

        .. python::
            # Get Object Begin End time for rectangular object Id 125
            object_start_stop_dict = self.__objDb.get_rect_object_kinematics_begin_end(125)
        """
#        Select * From Obj_Kinematics Where (Rectobjid = '235399') And
#        ((Kinabsts = (Select Min(Kinabsts) From Obj_Kinematics Where Rectobjid = '235399') ) Or
#        (KINABSTS = (Select MAX(Kinabsts) From Obj_Kinematics Where Rectobjid = '235399')) )
#        ORDER BY KINABSTS
        adma_id = self.get_adma_associated_type_id()
        rtrange_id = self.get_rt_range_associated_type_id()
        obj_record = self.get_rect_object_by_rect_obj_id(rect_obj_id)

        if ((adma_id is not None and obj_record[0][COL_NAME_RECT_OBJ_ASSOCTYPEID]
             == adma_id) or (rtrange_id is not None and obj_record[0][COL_NAME_RECT_OBJ_ASSOCTYPEID]
                             == rtrange_id)):

            table_name = TABLE_NAME_ADMA_KINEMATICS
        else:
            table_name = TABLE_NAME_KINEMATICS

        min_exp = "(SELECT %s FROM %s " % (str(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_MIN],
                                                           COL_NAME_KINEMATICS_KINABSTS)),
                                           table_name)
        max_exp = "(SELECT %s FROM %s " % (str(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_MAX],
                                                           COL_NAME_KINEMATICS_KINABSTS)),
                                           table_name)
        cond1 = SQLBinaryExpr(COL_NAME_KINEMATICS_RECTOBJID, OP_EQ, rect_obj_id)
        min_exp += "WHERE %s)" % str(cond1)
        max_exp += "WHERE %s)" % str(cond1)

        cond2 = SQLBinaryExpr(COL_NAME_KINEMATICS_KINABSTS, OP_EQ, min_exp)
        cond3 = SQLBinaryExpr(COL_NAME_KINEMATICS_KINABSTS, OP_EQ, max_exp)
        cond = SQLBinaryExpr(cond1, OP_AND, SQLBinaryExpr(cond2, OP_OR, cond3))

        entries = self.select_generic_data(select_list=["*"], table_list=[table_name],
                                           where=cond, order_by=[COL_NAME_KINEMATICS_KINABSTS])
        if len(entries) == 2:
            return {"BeginTS": entries[0], "EndTS": entries[1]}
        else:
            return None

    def GetRectObjectKinematicsBeginEnd(self, rect_obj_id):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetRectObjectKinematicsBeginEnd" is deprecated use '
        msg += '"get_rect_object_kinematics_begin_end" instead'
        warn(msg, stacklevel=2)
        return self.get_rect_object_kinematics_begin_end(rect_obj_id)

    def get_rect_object_start_end_time(self, rect_obj_id):
        """
        Get start and end time for rectangular object.

        :param rect_obj_id: The rectangular object id.
        :type rect_obj_id: int
        :return: The start and end times.
        :rtype: tuple

        **1. Example:**

        .. python::
            # Get Object start stop time for rectangular object Id 125
            start, end= self.__objDb.GetRectObjectStartEndTime(125)
        """
        obj_kin_map = self.get_rect_object_kinematics_begin_end(rect_obj_id)
        if obj_kin_map is not None:
            start_time = obj_kin_map["BeginTS"][COL_NAME_KINEMATICS_KINABSTS]
            end_time = obj_kin_map["EndTS"][COL_NAME_KINEMATICS_KINABSTS]
        else:
            start_time = None
            end_time = None
        return start_time, end_time

    def GetRectObjectStartEndTime(self, rect_obj_id):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetRectObjectStartEndTime" is deprecated use '
        msg += '"get_rect_object_start_end_time" instead'
        warn(msg, stacklevel=2)
        return self.get_rect_object_start_end_time(rect_obj_id)

    @staticmethod
    def __rect_obj_del_condition(cond, incl_deleted):
        """ extend the given condition with the the condition for deleted rect objects """
        if incl_deleted is False:
            cond_del = SQLBinaryExpr(COL_NAME_RECT_OBJ_RECTOBJ_IS_DELETED, OP_EQ, 0)
            if cond is not None:
                return SQLBinaryExpr(cond, OP_AND, cond_del)
            else:
                return cond_del
        else:
            return cond

    def get_rect_objects_for_meas_id(self, meas_id, incl_deleted=False):
        """
        Get all rectangular object start stop kinematics info for given measurement ID

        :param meas_id: Measurement Id
        :type meas_id: int
        :param incl_deleted: Flag to include delete rect obj i.e. which are makred as deleted
        :type incl_deleted: Bool
        :return: List of record containing BeginAbsTs, EndAbsTs and ClassID for each rectangular object
        :rtype: list
        """
        # object_rect_map = {COL_NAME_BEGIN_TS: None, COL_NAME_END_TS: None}

        min_exp = SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_MIN],
                              SQLColumnExpr(SQLTableExpr(TABLE_NAME_KINEMATICS), COL_NAME_KINEMATICS_KINABSTS))
        max_exp = SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_MAX],
                              SQLColumnExpr(SQLTableExpr(TABLE_NAME_KINEMATICS), COL_NAME_KINEMATICS_KINABSTS))

        min_exp = SQLBinaryExpr(min_exp, OP_AS, COL_NAME_BEGIN_TS)
        max_exp = SQLBinaryExpr(max_exp, OP_AS, COL_NAME_END_TS)

        select_list = [SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_RECTANGULAR_OBJECT),
                                                   COL_NAME_RECT_OBJ_RECTOBJID), OP_AS, COL_NAME_RECT_OBJ_RECTOBJID),
                       SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_RECTANGULAR_OBJECT),
                                                   COL_NAME_RECT_OBJ_OBJCLASSID), OP_AS, COL_NAME_RECT_OBJ_OBJCLASSID),
                       min_exp, max_exp]

        col1 = SQLColumnExpr(SQLTableExpr(TABLE_NAME_RECTANGULAR_OBJECT), COL_NAME_RECT_OBJ_RECTOBJID)
        col2 = SQLColumnExpr(SQLTableExpr(TABLE_NAME_KINEMATICS), COL_NAME_KINEMATICS_RECTOBJID)

        join_expr = SQLTernaryExpr(SQLTableExpr(TABLE_NAME_RECTANGULAR_OBJECT),
                                   OP_INNER_JOIN,
                                   SQLTableExpr(TABLE_NAME_KINEMATICS),
                                   OP_ON,
                                   SQLBinaryExpr(col1, OP_EQ, col2))

        col1 = SQLColumnExpr(SQLTableExpr(TABLE_NAME_RECTANGULAR_OBJECT), COL_NAME_RECT_OBJ_MEASID)
        condition = SQLBinaryExpr(col1, OP_EQ, meas_id)

        condition = self.__rect_obj_del_condition(condition, incl_deleted)

        group = [SQLColumnExpr(SQLTableExpr(TABLE_NAME_RECTANGULAR_OBJECT), COL_NAME_RECT_OBJ_RECTOBJID),
                 SQLColumnExpr(SQLTableExpr(TABLE_NAME_RECTANGULAR_OBJECT), COL_NAME_RECT_OBJ_OBJCLASSID)]

        obj_rect_list = self.select_generic_data(select_list, [join_expr], condition,
                                                 group, order_by=[COL_NAME_BEGIN_TS])

        return obj_rect_list

    def GetRectObjectsForMeasId(self, meas_id, incl_deleted=False):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetRectObjectsForMeasId" is deprecated use '
        msg += '"get_rect_objects_for_meas_id" instead'
        warn(msg, stacklevel=2)
        return self.get_rect_objects_for_meas_id(meas_id, incl_deleted)

    def get_rect_object_ids(self, measid, incl_deleted=False,
                            cls_lblstateids=None):
        """
        Gets rectangular object id's from database.

        :param measid: The measurement id.
        :type measid: int
        :param incl_deleted: Flag to include delete rect obj i.e. which are makred as deleted
        :type incl_deleted: Bool
        :param cls_lblstateids: Filter criteria to retrieve data for specific label state Id(s)
        :type cls_lblstateids: list or int
        :return: Returns the list of record containing rect object Ids
        :rtype: list
        """
        condition = SQLBinaryExpr(COL_NAME_RECT_OBJ_MEASID, OP_EQ, measid)
        lblstates = None

        if cls_lblstateids == []:
            cls_lblstateids = None

        if cls_lblstateids is not None:
            if type(cls_lblstateids) is list and len(cls_lblstateids) > 0:
                if len(cls_lblstateids) == 1:
                    lblstates = "(%d)" % cls_lblstateids[0]
                else:
                    lblstates = str(tuple(cls_lblstateids))
            else:
                lblstates = "(%d)" % cls_lblstateids

            condition = SQLBinaryExpr(condition, OP_AND, SQLBinaryExpr(COL_NAME_RECT_OBJ_CLSLBLSTATEID,
                                                                       OP_IN, lblstates))

        select_list = [COL_NAME_RECT_OBJ_RECTOBJID]
        condition = self.__rect_obj_del_condition(condition, incl_deleted)
        object_id_list = self.select_generic_data(select_list, [TABLE_NAME_RECTANGULAR_OBJECT], condition)
        return object_id_list

    def GetRectObjectIds(self, measid, incl_deleted=False, cls_lblstateids=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetRectObjectIds" is deprecated use '
        msg += '"get_rect_object_ids" instead'
        warn(msg, stacklevel=2)
        return self.get_rect_object_ids(measid, incl_deleted, cls_lblstateids)

    def get_rect_objects(self, measid, incl_deleted=False, select_list=None):
        """
        Gets rectangular object id from database.

        :param measid: The measurement id.
        :type measid: int
        :param incl_deleted: Flag to include delete rect obj i.e. which are makred as deleted
        :type incl_deleted: Bool
        :param select_list: list of column to be select from table OBJ_RECTANGULAROBJECT
        :type select_list: list
        :return: Returns the object record list.
        :rtype: list
        """
        if select_list is None:
            select_list = [COL_NAME_RECT_OBJ_RECTOBJID,
                           COL_NAME_RECT_OBJ_OBJCLASSID,
                           COL_NAME_RECT_OBJ_ASSOCTYPEID,
                           COL_NAME_RECT_OBJ_OBJWIDTH,
                           COL_NAME_RECT_OBJ_OBJLENGTH,
                           COL_NAME_RECT_OBJ_OBJHEIGHT,
                           COL_NAME_RECT_OBJ_ZLAYER,
                           COL_NAME_RECT_OBJ_KINLBLSTATEID]

        condition = SQLBinaryExpr(COL_NAME_RECT_OBJ_MEASID, OP_EQ, measid)

        # include only not deleted rect objects
        condition = self.__rect_obj_del_condition(condition, incl_deleted)
        if incl_deleted:
            select_list.append(COL_NAME_RECT_OBJ_RECTOBJ_IS_DELETED)

        object_record_list = self.select_generic_data(select_list, [TABLE_NAME_RECTANGULAR_OBJECT], condition)
        return object_record_list

    def GetRectObjects(self, measid, incl_deleted=False, select_list=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetRectObjects" is deprecated use '
        msg += '"get_rect_objects" instead'
        warn(msg, stacklevel=2)
        return self.get_rect_objects(measid, incl_deleted, select_list)

    def get_rect_object_by_rect_obj_id(self, rect_obj_id, select=None, incl_deleted=False):
        """
        Gets the retangular object data for the given id.

        :param rect_obj_id: rectangular object Id
        :type rect_obj_id: int
        :param select: User sepecific selections of column
        :type select: list
        :param incl_deleted: Flag to include delete rect obj i.e. which are makred as deleted
        :type incl_deleted: Bool
        :return: Returns list of record
        :rtype: list
        """
        if select is None:
            select = [COL_NAME_RECT_OBJ_RECTOBJID, COL_NAME_RECT_OBJ_OBJCLASSID,
                      COL_NAME_RECT_OBJ_ASSOCTYPEID, COL_NAME_RECT_OBJ_OBJWIDTH,
                      COL_NAME_RECT_OBJ_OBJLENGTH, COL_NAME_RECT_OBJ_OBJHEIGHT,
                      COL_NAME_RECT_OBJ_ZLAYER, COL_NAME_RECT_OBJ_KINLBLSTATEID]

        condition = SQLBinaryExpr(COL_NAME_RECT_OBJ_RECTOBJID, OP_EQ, rect_obj_id)
        # include only not deleted rect objects
        condition = self.__rect_obj_del_condition(condition, incl_deleted)
        if incl_deleted:
            select.append(COL_NAME_RECT_OBJ_RECTOBJ_IS_DELETED)

        object_record = self.select_generic_data(select, [TABLE_NAME_RECTANGULAR_OBJECT], condition)
        return object_record

    def GetRectObjectByRectObjId(self, rect_obj_id, select=None, incl_deleted=False):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetRectObjectByRectObjId" is deprecated use '
        msg += '"get_rect_object_by_rect_obj_id" instead'
        warn(msg, stacklevel=2)
        return self.get_rect_object_by_rect_obj_id(rect_obj_id, select,
                                                   incl_deleted)

    def get_test_case_type_id(self, test_case_name):
        """
        Selects the test case typeid for the given testcase name

        :param test_case_name: The name key. (e.g. "cutin", "approach", ...)
        :type test_case_name: str
        :return: The typeid (int) of the test case.
        :rtype: int
        """
        condition = SQLBinaryExpr(COL_NAME_TEST_CASE_TYPE_NAME, OP_EQ, SQLLiteral(test_case_name))
        test_case_id_list = self.select_generic_data([COL_NAME_TEST_CASE_TYPE_ID],
                                                     [TABLE_NAME_TEST_CASE_TYPE], condition)

        test_case_type_id = None

        if len(test_case_id_list):
            test_case_type_id = test_case_id_list[0][COL_NAME_TEST_CASE_TYPE_ID]
        else:
            self._log.info("No test case id found for test case name " + test_case_name)

        return test_case_type_id

    def GetTestCaseTypeID(self, test_case_name):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetTestCaseTypeID" is deprecated use '
        msg += '"get_test_case_type_id" instead'
        warn(msg, stacklevel=2)
        return self.get_test_case_type_id(test_case_name)

    def get_test_case_type_name(self, test_case_type_id):
        """
        Get testcase name for given test case type id

        :param test_case_type_id: Test case type id
        :type test_case_type_id: int
        :return: testcase name
        :rtype: str
        """
        condition = SQLBinaryExpr(COL_NAME_TEST_CASE_TYPE_ID, OP_EQ, test_case_type_id)
        test_case_list = self.select_generic_data([COL_NAME_TEST_CASE_TYPE_NAME],
                                                  [TABLE_NAME_TEST_CASE_TYPE], condition)

        test_case_type_name = None

        if len(test_case_list):
            test_case_type_name = test_case_list[0][COL_NAME_TEST_CASE_TYPE_NAME]
        else:
            self._log.error("No test case name found for test case Id " + str(test_case_type_id))

        return test_case_type_name

    def GetTestCaseTypeName(self, test_case_type_id):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetTestCaseTypeName" is deprecated use '
        msg += '"get_test_case_type_name" instead'
        warn(msg, stacklevel=2)
        return self.get_test_case_type_name(test_case_type_id)

    def get_test_cases_for_rec_file(self, recfile_id, testcase_name=None, inc_kinematics=True,
                                    columns_list=None):
        """
        Generic Function to get Test case for the recoding file

        returns a list of dicts with default and additional column names as keys
        and their stored values for the recfile:

        .. python::
            [{"TESTCASEID": 12, "TESTCASETYPEID": 3, "RECTOJID": 47, "BEGINABSTS": 3721532, "ENDABSTS:l 3721789,
              "obj_kinematics": [<RELDISTX>, <RELDISTY>, <RELVELX>]},
             {'TESTCASEID': 13, ...}]

        :param recfile_id: recfile id e.g. 'continuous_2012.11.05_at_14.55.54.rec'
        :type recfile_id: string
        :param testcase_name: test case name e.g. 'ooi', 'cutin' if not provide then all testcases for recfile
        :type testcase_name: string
        :param inc_kinematics: flag to include object kinematics for object testcases default True
        :type inc_kinematics: bool
        :param columns_list: add list of columns to return from table obj_testcases, default: empty list
        :param columns_list: list
        :return: list of dict records
        :rtype: list
        """

        test_case_typeid = None
        if testcase_name is not None:
            test_case_typeid = self.get_test_case_type_id(testcase_name)
        else:
            testcase_name = ''

        # Get the cutin labels.
        select_list = [COL_NAME_TEST_CASES_TESTCASEID,
                       COL_NAME_TEST_CASES_TYPEID,
                       COL_NAME_TEST_CASES_RECTOBJID,
                       COL_NAME_TEST_CASES_BEGINABSTS,
                       COL_NAME_TEST_CASES_ENDABSTS]
        if columns_list:
            select_list.extend(columns_list)

        join_expr = SQLTernaryExpr(SQLTableExpr(TABLE_NAME_TEST_CASES),
                                   OP_INNER_JOIN,
                                   SQLTableExpr(TABLE_NAME_RECTANGULAR_OBJECT),
                                   OP_NOP,
                                   SQLFuncExpr(OP_USING, COL_NAME_RECT_OBJ_RECTOBJID))

        condition = SQLBinaryExpr(COL_NAME_RECT_OBJ_MEASID, OP_EQ, recfile_id)
        if test_case_typeid is not None:
            condition = SQLBinaryExpr(condition, OP_AND,
                                      SQLBinaryExpr(COL_NAME_TEST_CASES_TYPEID, OP_EQ, test_case_typeid))

        label_list = self.select_generic_data(select_list, table_list=[join_expr], where=condition)

        if len(label_list) > 0:
            # Found some cutin testcases
            select_list = [COL_NAME_KINEMATICS_RELDISTX, COL_NAME_KINEMATICS_RELDISTY,
                           COL_NAME_KINEMATICS_RELVELX]
            if inc_kinematics:
                for testcase in label_list:
                    testcase['obj_kinematics'] = []
                    # get obj kinematics for testcase begints and endts
                    condition1 = SQLBinaryExpr(COL_NAME_KINEMATICS_RECTOBJID, OP_EQ,
                                               testcase[COL_NAME_RECT_OBJ_RECTOBJID])
                    condition2 = SQLBinaryExpr(COL_NAME_KINEMATICS_KINABSTS, OP_EQ,
                                               testcase[COL_NAME_TEST_CASES_BEGINABSTS])
                    condition3 = SQLBinaryExpr(COL_NAME_KINEMATICS_KINABSTS, OP_EQ,
                                               testcase[COL_NAME_TEST_CASES_ENDABSTS])
                    condition23 = SQLBinaryExpr(condition2, OP_OR, condition3)
                    condition = SQLBinaryExpr(condition1, OP_AND, condition23)
                    table_list = [TABLE_NAME_KINEMATICS]
                    testcase_obj_kinematics = self.select_generic_data(select_list, table_list=table_list,
                                                                       where=condition)
                    testcase['obj_kinematics'] = testcase_obj_kinematics
        else:
            self._log.info("No " + testcase_name + " testcase found for RecFile '%s'." % recfile_id)

        return label_list

    def GetTestCasesForRecFile(self, recfile_id, testcase_name=None, inc_kinematics=True):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetTestCasesForRecFile" is deprecated use '
        msg += '"get_test_cases_for_rec_file" instead'
        warn(msg, stacklevel=2)
        return self.get_test_cases_for_rec_file(recfile_id, testcase_name, inc_kinematics)

    def get_ego_kinematics_adma(self, measid, kinabsts):
        """
        Get EgoKinematic data for ADMA measurement at given time stamp

        :param measid: measurement ID
        :type measid: int
        :param kinabsts: absolute timestamp
        :type kinabsts: int
        :return: list of  dictionary record
        :rtype: list
        """
        if measid is not None:
            cond = SQLBinaryExpr(COL_NAME_EGO_ADMA_MEASID, OP_EQ, measid)
        else:
            cond = None
        if kinabsts is not None:
            if cond is not None:
                cond = SQLBinaryExpr(cond, OP_AND,
                                     SQLBinaryExpr(COL_NAME_EGO_ADMA_KINABSTS, OP_EQ, kinabsts))
            else:
                cond = SQLBinaryExpr(COL_NAME_EGO_ADMA_KINABSTS, OP_EQ, kinabsts)
        entries = self.select_generic_data(table_list=[TABLE_NAME_EGO_KINEMATICS_ADMA], where=cond)
        return entries

    def delete_ego_kinematics_adma(self, measid):
        """
        Delete EgoKinematics data for Adma measurement
        :param measid: measurement ID
        :type measid: int
        """
        cond = SQLBinaryExpr(COL_NAME_EGO_ADMA_MEASID, OP_EQ, measid)
        self.delete_generic_data(TABLE_NAME_EGO_KINEMATICS_ADMA, cond)

    def GetEgoKinematicsAdma(self, measid, kinabsts):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetEgoKinematicsAdma" is deprecated use '
        msg += '"get_ego_kinematics_adma" instead'
        warn(msg, stacklevel=2)
        return self.get_ego_kinematics_adma(measid, kinabsts)

    def getEgoKinematicsAdma(self, measid, kinabsts):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "getEgoKinematicsAdma" is deprecated use '
        msg += '"get_ego_kinematics_adma" instead'
        warn(msg, stacklevel=2)
        return self.get_ego_kinematics_adma(measid, kinabsts)

    def get_probs_cam(self, absts, rectobjid):
        """
        Get Data from PROB CAM (e.g. occlude factor, relevanceX, relevanceY)

        :param absts: absolute timestamp
        :type absts: int
        :param rectobjid: rectangular object ID
        :type rectobjid: int
        :return: list of  dictionary record
        :rtype: list
        """
        if absts is not None:
            cond = SQLBinaryExpr(COL_NAME_PROBSCAM_ABSTS, OP_EQ, absts)
        else:
            cond = None
        if rectobjid is not None:
            if cond is not None:
                cond = SQLBinaryExpr(cond, OP_AND,
                                     SQLBinaryExpr(COL_NAME_PROBSCAM_RECTOBJID, OP_EQ, rectobjid))
            else:
                cond = SQLBinaryExpr(COL_NAME_PROBSCAM_RECTOBJID, OP_EQ, rectobjid)
        entries = self.select_generic_data(table_list=[TABLE_NAME_PROBS_CAM], where=cond)
        return entries

    def GetProbsCam(self, absts, rectobjid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetProbsCam" is deprecated use '
        msg += '"get_probs_cam" instead'
        warn(msg, stacklevel=2)
        return self.get_probs_cam(absts, rectobjid)

    def getProbsCam(self, absts, recid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "getProbsCam" is deprecated use '
        msg += '"get_probs_cam" instead'
        warn(msg, stacklevel=2)
        return self.get_probs_cam(absts, recid)

    def has_test_case(self, rect_id, test_case_type, begin_absts=None, end_absts=None):
        """
        Checks if there exist testcase for rect object for given tescase type

        :param rect_id: The RectId key from the 'Obj_RectangularObject' table.
        :type rect_id: int
        :param test_case_type: The test case type as a string.
        :type test_case_type: The test case type as a string.
        :return: return boolean flag True if the the rect object has such test case. otherwise return False
        :rtype: bool
        """
        # First get the test case id for approach.
        test_case_typeid = self.get_test_case_type_id(test_case_type)

        # Get the approach labels.
        select_list = [COL_NAME_TEST_CASES_TESTCASEID,
                       COL_NAME_TEST_CASES_TYPEID,
                       COL_NAME_TEST_CASES_RECTOBJID,
                       COL_NAME_TEST_CASES_BEGINABSTS,
                       COL_NAME_TEST_CASES_ENDABSTS]

        condition = SQLBinaryExpr(COL_NAME_TEST_CASES_RECTOBJID, OP_EQ, rect_id)
        condition = SQLBinaryExpr(condition, OP_AND,
                                  SQLBinaryExpr(COL_NAME_TEST_CASES_TYPEID, OP_EQ, test_case_typeid))

        if begin_absts is not None:
            condition = SQLBinaryExpr(condition, OP_AND,
                                      SQLBinaryExpr(COL_NAME_TEST_CASES_BEGINABSTS, OP_EQ, begin_absts))
        if end_absts is not None:
            condition = SQLBinaryExpr(condition, OP_AND,
                                      SQLBinaryExpr(COL_NAME_TEST_CASES_ENDABSTS, OP_EQ, end_absts))

        approach_label_list = self.select_generic_data(select_list, [TABLE_NAME_TEST_CASES], condition)
        if len(approach_label_list):
            # Found approach
            return True
        else:
            return False

    def HasTestCase(self, rect_id, test_case_type, begin_absts=None, end_absts=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "HasTestCase" is deprecated use '
        msg += '"has_test_case" instead'
        warn(msg, stacklevel=2)
        return self.has_test_case(rect_id, test_case_type, begin_absts=begin_absts, end_absts=end_absts)

    def has_adma_rectangular_object_id(self, meas_id):
        """
        Get boolean status whether measurement has Adma objects or not

        :param meas_id: mesurement id
        :type meas_id: int
        :return: return boolean flag True if measurement has Adma object otherwise return False
        :rtype: bool
        """
        adma_id = self.get_adma_associated_type_id()
        return self.__has_associated_rectangular_object_id(meas_id, adma_id)

    def HasAdmaRectangularObjectId(self, meas_id):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "HasAdmaRectangularObjectId" is deprecated use '
        msg += '"has_adma_rectangular_object_id" instead'
        warn(msg, stacklevel=2)
        return self.has_adma_rectangular_object_id(meas_id)

    def has_rt_range_rectangular_object_id(self, meas_id):  # pylint: disable=C0103
        """
        Get boolean status whether measurement has rtrange objects or not

        :param meas_id: mesurement id
        :type meas_id: int
        :return: return boolean flag True if measurement has Rtrange object otherwise return False
        :rtype: bool
        """
        rtrange_id = self.get_rt_range_associated_type_id()
        return self.__has_associated_rectangular_object_id(meas_id, rtrange_id)

    def HasRtRangeRectangularObjectId(self, meas_id):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "HasRtRangeRectangularObjectId" is deprecated use '
        msg += '"has_rt_range_rectangular_object_id" instead'
        warn(msg, stacklevel=2)
        return self.has_rt_range_rectangular_object_id(meas_id)

    def __has_associated_rectangular_object_id(self, meas_id, assoc_id):  # pylint: disable=C0103
        """
        Generic private function to check the given measurement has rectangular object with specified
        association type id

        :param meas_id: The MeasId key from the 'Files' table.
        :type meas_id: int
        """
        ret_val = False
        if assoc_id is not None:
            condition = SQLBinaryExpr(COL_NAME_ASSOC_TYPE_ASSOCTYPEID, OP_EQ, assoc_id)
            condition = SQLBinaryExpr(condition, OP_AND, SQLBinaryExpr(COL_NAME_RECT_OBJ_MEASID,
                                                                       OP_EQ, meas_id))
            table_list = [TABLE_NAME_RECTANGULAR_OBJECT]
            select_list = [SQLBinaryExpr(SQLFuncExpr("count", COL_NAME_RECT_OBJ_RECTOBJID),
                                         OP_AS, "TOTAL_OBJ")]
            rt_obj_count = self.select_generic_data(select_list, table_list, condition)[0]["TOTAL_OBJ"]

            if rt_obj_count > 0:
                ret_val = True
        else:
            self._log.error("Associated Type not found for assoc id = " + str(assoc_id))

        return ret_val

    def is_adma_associated_type_id(self):
        """
        Get boolean if  association type adma exist in Database.

        :return: return boolean flag True if database has Adma association type registered otherwise return False
        :rtype: bool
        """
        try:
            adma_id = self.get_adma_associated_type_id()
            if adma_id is not None:
                return True
        except StandardError:
            return False
        return False

    def IsAdmaAssociatedTypeId(self):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "IsAdmaAssociatedTypeId" is deprecated use '
        msg += '"is_adma_associated_type_id" instead'
        warn(msg, stacklevel=2)
        return self.is_adma_associated_type_id()

    def is_rt_range_associated_type_id(self):
        """
        Get boolean if  association type rt range exist in Database.

        :return: return boolean flag True if database has RT range association type registered otherwise return False
        :rtype: bool
        """
        try:
            rt_range_id = self.get_rt_range_associated_type_id()
            if rt_range_id is not None:
                return True
        except StandardError:
            return False
        return False

    def IsRtRangeAssociatedTypeId(self):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "IsRtRangeAssociatedTypeId" is deprecated use '
        msg += '"is_rt_range_associated_type_id" instead'
        warn(msg, stacklevel=2)
        return self.is_rt_range_associated_type_id()

    def get_label_state_id(self, name):
        """
        Get lable state id for given label state name

        :param name: label state name e.g. auto manual
        :type name: str
        :return: Label State Id. If lable state doesnt exist StandardError will be raise
        :rtype: int
        """
        lbl_state_id = self.get_label_state(statename=name)
        if len(lbl_state_id) == 1:
            lbl_state_id = lbl_state_id[0][COL_NAME_LBL_STATE_LBL_STATE_ID]
        else:
            self._log.error("No Label state id or Ambigious found for label state " + name)
            raise StandardError("No Label state id or Ambigious found for label state'%s'." % name)
        return lbl_state_id

    def GetLabelStateId(self, name):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetLabelStateId" is deprecated use '
        msg += '"get_label_state_id" instead'
        warn(msg, stacklevel=2)
        return self.get_label_state_id(name)

    def get_label_state_name(self, stateid):
        """
        Get Label state name for given labels state id

        :param stateid: label state id
        :type stateid: int
        :return: Label State Name . If lable state Id exist StandardError will be raise
        :rtype: int
        """
        lbl_state_name = self.get_label_state(stateid=stateid)

        if len(lbl_state_name) == 1:
            lbl_state_name = lbl_state_name[0][COL_NAME_LBL_STATE_NAME]
        else:
            self._log.error("No Label state name  or Ambigious found for label id " + str(stateid))
            raise StandardError("No Label state id or Ambigious found for label state'%s'." % str(stateid))
        return lbl_state_name

    def GetLabelStateName(self, stateid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetLabelStateName" is deprecated use '
        msg += '"get_label_state_name" instead'
        warn(msg, stacklevel=2)
        return self.get_label_state_name(stateid)

    def get_label_state(self, statename=None, stateid=None):
        """
        Get Label State record for given state name or state id

        :param statename: label state name e.g. auto, manual, reviewed
        :type statename: str
        :param stateid: label state id
        :type stateid: int
        :return: list of record
        :rtype: list
        """
        condition = None
        lbl_state = []

        if statename is not None:
            condition = SQLBinaryExpr(COL_NAME_LBL_STATE_NAME, OP_EQ, SQLLiteral(statename))

        if stateid is not None:
            if condition is not None:
                condition = SQLBinaryExpr(condition, OP_AND,
                                          SQLBinaryExpr(COL_NAME_LBL_STATE_LBL_STATE_ID, OP_EQ, stateid))
            else:
                condition = SQLBinaryExpr(COL_NAME_LBL_STATE_LBL_STATE_ID, OP_EQ, stateid)

        if condition is not None:
            lbl_state = self.select_generic_data(table_list=[TABLE_NAME_OBJ_LBL_STATE], where=condition)
        return lbl_state

    def GetLabelState(self, statename=None, stateid=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetLabelState" is deprecated use '
        msg += '"get_label_state" instead'
        warn(msg, stacklevel=2)
        return self.get_label_state(statename, stateid)

    def get_label_class_id(self, classname):
        """
        Get lable class id for given label class name

        :param classname: label state name e.g. car truck
        :type classname: str
        :return: Label Class Id. If class Id doesnt exist Standard Error will be raise
        :rtype: int
        """
        clsid = self.get_label_class(classname=classname)
        if len(clsid) == 1:
            clsid = clsid[0][COL_NAME_OBJECT_CLASS_CLS_ID]
        else:
            self._log.error("No Object Class Label id or Ambigious found for label state " + classname)
            raise StandardError("No Object Class Label id found for %s" % classname)
        return clsid

    def GetLabelClassId(self, classname):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetLabelClassId" is deprecated use '
        msg += '"get_label_class_id" instead'
        warn(msg, stacklevel=2)
        return self.get_label_class_id(classname)

    def get_label_class_name(self, clsid):
        """
        Get label class name for given class Id

        :param clsid: class id
        :type clsid: int
        :return: Label Class Name. if Class name doesnt exist StandardError will be raise
        :rtype: str
        """
        classname = self.get_label_class(clsid=clsid)
        if len(classname) == 1:
            classname = classname[0][COL_NAME_OBJECT_CLASS_CLASS_NAME]
        else:
            self._log.error("No Object label Class or Ambigious found for class id " + str(clsid))
            raise StandardError("No Object label Class found for class id %s" % str(clsid))
        return classname

    def GetLabelClassName(self, clsid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetLabelClassName" is deprecated use '
        msg += '"get_label_class_name" instead'
        warn(msg, stacklevel=2)
        return self.get_label_class_name(clsid)

    def get_label_class(self, classname=None, clsid=None):
        """
        Get label Class record for given classname

        :param classname: class name of object e.g. truck,
        :type classname: str
        :param clsid: class id
        :type clsid: int
        :return: List of records
        :rtype: list
        """
        condition = None
        lbl_class = []
        if classname is not None:
            condition = SQLBinaryExpr(COL_NAME_OBJECT_CLASS_CLASS_NAME, OP_EQ, SQLLiteral(classname))

        if clsid is not None:
            if condition is not None:
                condition = SQLBinaryExpr(condition, OP_AND,
                                          SQLBinaryExpr(COL_NAME_OBJECT_CLASS_CLS_ID, OP_EQ, clsid))
            else:
                condition = SQLBinaryExpr(COL_NAME_OBJECT_CLASS_CLS_ID, OP_EQ, clsid)

        if condition is not None:
            lbl_class = self.select_generic_data(table_list=[TABLE_NAME_OBJECT_CLASS], where=condition)
        return lbl_class

    def GetLabelClass(self, classname=None, clsid=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetLabelClass" is deprecated use '
        msg += '"get_label_class" instead'
        warn(msg, stacklevel=2)
        return self.get_label_class(classname, clsid)

    def get_object_association(self, name=None, typeid=None):
        """
        Get Object Association record for given name or typeid

        :param name: association name e.g. adma,rtrange, rect
        :type name: string
        :param typeid: association type id
        :type typeid: int
        :return: List of records
        :rtype: list
        """
        condition = None
        assoc_type = []
        if name is not None:
            condition = SQLBinaryExpr(COL_NAME_ASSOC_TYPE_NAME, OP_EQ, SQLLiteral(name))
        if typeid is not None:
            if condition is not None:
                condition = SQLBinaryExpr(condition, OP_AND,
                                          SQLBinaryExpr(COL_NAME_ASSOC_TYPE_ASSOCTYPEID, OP_EQ, typeid))
            else:
                condition = SQLBinaryExpr(COL_NAME_ASSOC_TYPE_ASSOCTYPEID, OP_EQ, typeid)
        if condition is not None:
            assoc_type = self.select_generic_data(table_list=[TABLE_NAME_ASSOC_TYPE], where=condition)
        return assoc_type

    def GetObjectAssociation(self, name=None, typeid=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetObjectAssociation" is deprecated use '
        msg += '"get_object_association" instead'
        warn(msg, stacklevel=2)
        return self.get_object_association(name, typeid)

    def get_object_association_name(self, typeid):
        """
        Get Object Association Name for given association type id

        :param typeid: object association type id
        :type typeid: int
        :return: Object Association name. if Object Association name doesnt exist StandardError will be raise
        :rtype: str
        """

        assoc_type = self.get_object_association(typeid=typeid)
        if len(assoc_type) == 1:
            assoc_type = assoc_type[0][COL_NAME_ASSOC_TYPE_NAME]
        else:
            self._log.error("No Object Association name or Ambigious found" +
                            "for object association id " + str(typeid))
            raise StandardError("Couldn't find Association Type name for Id %s" % str(typeid))
        return assoc_type

    def GetObjectAssociationName(self, typeid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetObjectAssociationName" is deprecated use '
        msg += '"get_object_association_name" instead'
        warn(msg, stacklevel=2)
        return self.get_object_association_name(typeid)

    def get_object_association_type_id(self, name):
        """
        Get object Association id for given name

        :param name: association name e.g. adma, rect
        :type name: str
        :return: Object Association type id. if Object Association type id doesnt exist StandardError will be raise
        :rtype: int
        """
        assoc_type = self.get_object_association(name=name)
        if len(assoc_type) == 1:
            assoc_type = assoc_type[0][COL_NAME_ASSOC_TYPE_ASSOCTYPEID]
        else:
            self._log.error("No Object Association type id or Ambigious found for object association state " + name)
            raise StandardError("Couldn't Association Type id for {}".format(name))
        return assoc_type

    def get_object_associated_table(self, ass_name):
        """
        Get associated object table for given type name

        :param ass_name: association name e.g. adma, rect
        :type ass_name: str
        :return: table name for object. if Object Association type id doesnt exist StandardError will be raise
        :rtype: str
        """
        assoc_table = self.get_object_association(name=ass_name)
        if len(assoc_table) == 1:
            assoc_table = assoc_table[0][COL_NAME_ASSOC_TYPE_TABLE]
        else:
            self._log.error("No Object Association type table or ambiguous one found for association state " + ass_name)
            raise StandardError("Couldn't get Association Type id for {}".format(ass_name))
        return assoc_table

    def GetObjectAssociationTypeId(self, name):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetObjectAssociationTypeId" is deprecated use '
        msg += '"get_object_association_type_id" instead'
        warn(msg, stacklevel=2)
        return self.get_object_association_type_id(name)

    def get_object_lane_type_id(self, lane_name):
        """
        Get Lane Id for the given Lane name

        :param lane_name: lane name e.g. left, right, ego
        :type lane_name: string
        :return: Lane type id. if lane id doesnt exist StandardError will be raise
        :rtype: int
        """
        condition = SQLBinaryExpr(COL_NAME_LANE_TYPES_LANE_NAME, OP_EQ, SQLLiteral(lane_name))
        lane_type = self.select_generic_data([COL_NAME_LANE_TYPES_LANE_ID], [TABLE_NAME_ACC_LANE_TYPES], condition)
        if len(lane_type) == 1:
            lane_type = lane_type[0][COL_NAME_LANE_TYPES_LANE_ID]
        else:
            self._log.error("No Object Lane type id or Ambigious found for lane name " + lane_name)
            raise StandardError("No Object Lane type id or Ambigious found for lane name '%s'." % lane_name)
        return lane_type

    def GetObjectLaneTypeId(self, lane_name):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetObjectLaneTypeId" is deprecated use '
        msg += '"get_object_lane_type_id" instead'
        warn(msg, stacklevel=2)
        return self.get_object_lane_type_id(lane_name)

    def get_rectangular_object_view(self, rectobjid):
        """
        Get Rectangular Object record from view for the rectobjid

        :param rectobjid: rectangular object Id
        :type rectobjid: int
        :return: List of record
        :rtype: int
        """
        condition = SQLBinaryExpr(COL_NAME_RECT_OBJ_VIEW_RECTOBJID, OP_EQ, rectobjid)
        rectobject_view_rec = self.select_generic_data(table_list=[TABLE_NAME_RECTANGULAR_OBJECT_VIEW],
                                                       where=condition)
        return rectobject_view_rec

    def GetRectangularObjectView(self, rectobjid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetRectangularObjectView" is deprecated use '
        msg += '"get_rectangular_object_view" instead'
        warn(msg, stacklevel=2)
        return self.get_rectangular_object_view(rectobjid)

    def get_object_testcases_view(self, rectobjid, testcase_name=None):
        """
        Get Object testcases from View

        :param rectobjid: rectangular object Id
        :type rectobjid: int
        :param testcase_name: object testcase name
        :type testcase_name: str
        :return: List of record
        :rtype: int
        """
        condition = SQLBinaryExpr(COL_NAME_TEST_CASES_VIEW_RECTOBJID, OP_EQ, rectobjid)
        if testcase_name is not None:
            condition = SQLBinaryExpr(condition, OP_AND, SQLBinaryExpr(COL_NAME_TEST_CASES_VIEW_TESTCASENAME, OP_EQ,
                                                                       SQLLiteral(testcase_name.lower())))
        objtestcases_view = self.select_generic_data(table_list=[TABLE_NAME_OBJ_TESTCASES_VIEW], where=condition)
        return objtestcases_view

    def GetObjectTestcasesView(self, rectobjid, testcase_name=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetObjectTestcasesView" is deprecated use '
        msg += '"get_object_testcases_view" instead'
        warn(msg, stacklevel=2)
        return self.get_object_testcases_view(rectobjid, testcase_name)

    def get_labeled_lane_association_view(self, rectobjid, order_by=None):  # pylint: disable=C0103
        """
        Get Lane assocation assoction from View for given rectangular object id

        :param rectobjid: Rectangular Object Id
        :type rectobjid: int
        :param order_by: list of column name by which record to be sorted
        :type order_by: list
        :return: List of record
        :rtype: int
        """
        condition = SQLBinaryExpr(COL_NAME_ACC_LANE_REL_VIEW_RECTOBJID, OP_EQ, rectobjid)
        labeledlane_view = self.select_generic_data(table_list=[TABLE_NAME_OBJ_ACCLANERELATION_VIEW],
                                                    where=condition, order_by=order_by)
        return labeledlane_view

    def get_labeled_lane_delete_activity_view(self, rectobjid, order_by=None):
        """
        Get Lane delete activity view for given recobjid

        :param rectobjid: rectangular object Id
        :type rectobjid: int
        :param order_by: list of column name by which records should be sorted
        :type order_by: list
        """
        condition = SQLBinaryExpr(COL_NAME_ACCLANEDEL_VIEW_RECTOBJID, OP_EQ, rectobjid)
        if self.sub_scheme_version > SUBSCHEMA_LANEDEL_FEATURE:
            lane_del_act_view = self.select_generic_data(table_list=[TABLE_NAME_ACC_LANEDEL_ACTIVITY_VIEW],
                                                         where=condition, order_by=order_by)
            return lane_del_act_view
        else:
            aliaslanedel = "acclanedel"
            tbllanedel = SQLTableExpr(TABLE_NAME_ACC_LANEDEL_ACTIVITY, aliaslanedel)
            alias_state = "state"
            tblobjstate = SQLTableExpr(TABLE_NAME_OBJ_LBL_STATE, alias_state)
            alias_user = "usr"
            tblusr = SQLTableExpr(TABLE_NAME_USERS, alias_user)
            alias_user1 = "usr1"
            tblusr1 = SQLTableExpr(TABLE_NAME_USERS, alias_user1)
            alias_lanetypes = "lanetype"
            tbllanetypes = SQLTableExpr(TABLE_NAME_ACC_LANE_TYPES, alias_lanetypes)
            col_lblstate = SQLBinaryExpr(SQLColumnExpr(alias_state, COL_NAME_LBL_STATE_NAME),
                                         OP_AS, COL_NAME_ACCLANEDEL_VIEW_LBLSTATE)
            col_lbluser = SQLBinaryExpr(SQLColumnExpr(alias_user, COL_NAME_USER_LOGIN),
                                        OP_AS, COL_NAME_ACCLANEDEL_VIEW_LBLUSER)
            col_deluser = SQLBinaryExpr(SQLColumnExpr(alias_user1, COL_NAME_USER_LOGIN),
                                        OP_AS, COL_NAME_ACCLANEDEL_VIEW_DELUSER)

            select_list = [COL_NAME_ACCLANEDEL_VIEW_ACCLANERELID,
                           COL_NAME_ACCLANEDEL_VIEW_RECTOBJID,
                           COL_NAME_ACCLANEDEL_VIEW_BEGINABSTS,
                           COL_NAME_ACCLANEDEL_VIEW_ENDABSTS,
                           COL_NAME_ACCLANEDEL_VIEW_LANENAME,
                           COL_NAME_ACCLANEDEL_VIEW_LANEASSOCWEIGHT,
                           col_lblstate, COL_NAME_ACCLANEDEL_VIEW_LBLMODTIME,
                           col_lbluser, col_deluser, COL_NAME_ACCLANEDEL_VIEW_DELTIME]

            join_0 = SQLJoinExpr(tbllanedel, OP_INNER_JOIN, tblobjstate,
                                 SQLBinaryExpr(SQLColumnExpr(aliaslanedel, COL_NAME_ACC_LANE_REL_LBLSTATEID), OP_EQ,
                                               SQLColumnExpr(alias_state, COL_NAME_LBL_STATE_LBL_STATE_ID)))

            join_1 = SQLJoinExpr(join_0, OP_INNER_JOIN, tblusr,
                                 SQLBinaryExpr(SQLColumnExpr(alias_user, COL_NAME_USER_ID), OP_EQ,
                                               SQLColumnExpr(aliaslanedel, COL_NAME_ACCLANEDEL_LBLBY)))
            join_2 = SQLJoinExpr(join_1, OP_INNER_JOIN, tblusr1,
                                 SQLBinaryExpr(SQLColumnExpr(alias_user1, COL_NAME_USER_ID), OP_EQ,
                                               SQLColumnExpr(aliaslanedel, COL_NAME_ACCLANEDEL_DELBY)))

            join_3 = SQLJoinExpr(join_2, OP_INNER_JOIN, tbllanetypes,
                                 SQLBinaryExpr(SQLColumnExpr(alias_lanetypes, COL_NAME_LANE_TYPES_LANE_ID), OP_EQ,
                                               SQLColumnExpr(aliaslanedel, COL_NAME_ACCLANEDEL_LANEID)))
            return self.select_generic_data(select_list=select_list, table_list=[join_3], where=condition)

    def GetLabeledLaneAssociationView(self, rectobjid, order_by=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetLabeledLaneAssociationView" is deprecated use '
        msg += '"get_labeled_lane_association_view" instead'
        warn(msg, stacklevel=2)
        return self.get_labeled_lane_association_view(rectobjid, order_by)

    def get_last_modified_lane_association_view(self, rectobjid, bylabelstate=True):  # pylint: disable=C0103
        """
        Get Last modified Lane relation entry for given rect object Id

        :param rectobjid: rectangular Object Id
        :type rectobjid: int
        :param bylabelstate: if record with same date are found then use include label state criteria
                            last change (new-->old ) is review-->manual-->auto
        :type bylabelstate: Bool
        :return: Signle record as dictionary
        :rtype: dict
        """
        table_list = [TABLE_NAME_OBJ_ACCLANERELATION_VIEW]
        cond = SQLBinaryExpr(COL_NAME_ACC_LANE_REL_VIEW_RECTOBJID, OP_EQ, rectobjid)

        max_date = SQLBinaryExpr(str(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_MAX],
                                                 COL_NAME_ACC_LANE_REL_VIEW_LBLMODTIME)),
                                 OP_AS, COL_NAME_ACC_LANE_REL_VIEW_LBLMODTIME)
        stmt = GenericSQLSelect(select_list=[str(max_date)], table_list=table_list, where_condition=cond)

        condition = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COL_NAME_ACC_LANE_REL_VIEW_LBLMODTIME, OP_EQ, stmt))

        select_list = [COL_NAME_ACC_LANE_REL_VIEW_RECTOBJID, COL_NAME_ACC_LANE_REL_VIEW_LBLMODTIME,
                       COL_NAME_ACC_LANE_REL_VIEW_LBLSTATE]

        labeledlane_view = self.select_generic_data(select_list=select_list, table_list=table_list, where=condition)
        if len(labeledlane_view) > 1:
            review_idx = -1
            manual_idx = -1
            auto_idx = -1
            if bylabelstate:
                for i in range(len(labeledlane_view)):
                    if labeledlane_view[i][COL_NAME_ACC_LANE_REL_VIEW_LBLSTATE] == LBL_STATE_REVIEWED:
                        review_idx += 1
                    if labeledlane_view[i][COL_NAME_ACC_LANE_REL_VIEW_LBLSTATE] == LBL_STATE_MANUAL:
                        manual_idx += 1

                    if labeledlane_view[i][COL_NAME_ACC_LANE_REL_VIEW_LBLSTATE] == LBL_STATE_AUTO:
                        auto_idx += 1
                if review_idx > -1:
                    return labeledlane_view[review_idx]
                elif manual_idx > -1:
                    return labeledlane_view[manual_idx]
                elif auto_idx >= -1:
                    return labeledlane_view[auto_idx]

            raise StandardError("Expecting one row for last modified date of ACC Lane relation")

        elif len(labeledlane_view) == 1:
            return labeledlane_view[0]
        else:
            return {}

    def get_last_delete_lane_association(self, rectobjid):  # pylint: disable=C0103
        """
        Get Date when last the delete lane deletion was done on the given rectangular object
        :param rectobjid: Rectangular Object Id
        :type rectobjid: int
        :return: Signle record as dictionary
        :rtype: dict
        """

        if self.sub_scheme_version >= SUBSCHEMA_LANEDEL_FEATURE:
            max_date = SQLBinaryExpr(str(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_MAX],
                                                     COL_NAME_ACCLANEDEL_DELTIME)),
                                     OP_AS, COL_NAME_ACCLANEDEL_DELTIME)

            cond = SQLBinaryExpr(COL_NAME_ACC_LANE_REL_VIEW_RECTOBJID, OP_EQ, rectobjid)
            last_del = self.select_generic_data(select_list=[max_date],
                                                table_list=[TABLE_NAME_ACC_LANEDEL_ACTIVITY],
                                                where=cond)
            if len(last_del) > 1:
                raise StandardError("Expecting one row for last modified date of ACC Lane relation")
            elif len(last_del) == 1:
                if last_del[0][COL_NAME_ACCLANEDEL_DELTIME] is not None:
                    return last_del[0]
        return {}

    def GetLastModifiedLaneAssociationView(self, rectobjid, bylabelstate=True):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetLastModifiedLaneAssociationView" is deprecated use '
        msg += '"get_last_modified_lane_association_view" instead'
        warn(msg, stacklevel=2)
        return self.get_last_modified_lane_association_view(rectobjid, bylabelstate=bylabelstate)

    def add_label_checkpoint(self, name):
        """
        Add Algo Checkpoint for Auto Label in database if algo checkpoint already exist then return
        checkpoint id from database otherwise add new record and return db generated checkpoint id
        the checkpoint label is always saved in lower case inside database

        :param name: Algo Checkpoint
        :type name: str
        :return: Checkpoint Id
        :rtype: int
        """
        checkpointid = self.get_label_checkpoint_id(name)

        if checkpointid is None:
            label_checkpoint_record = {COL_NAME_LBLCHECKPOINTS_NAME: name.lower()}
            self.add_generic_data(label_checkpoint_record, TABLE_NAME_OBJ_LBLCHECKPOINTS)
            checkpointid = self.get_label_checkpoint_id(name=name)

        return checkpointid

    def AddLabelCheckpoint(self, name):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "AddLabelCheckpoint" is deprecated use '
        msg += '"add_label_checkpoint" instead'
        warn(msg, stacklevel=2)
        return self.add_label_checkpoint(name)

    def delete_label_checkpoint(self, checkpointid=None, name=None):
        """
        Delete Algo Checkpoint entry from database based on given checkpoint name or checkpoint id

        :param checkpointid: checkpoint id
        :type checkpointid: int
        :param name: Algo Checkpoint
        :type name: str
        :return: Number of row effected
        :rtype: int
        """
        condition = None
        if checkpointid is not None:
            condition = SQLBinaryExpr(COL_NAME_LBLCHECKPOINTS_CHECKPOINTID, OP_EQ, checkpointid)

        if name is not None:
            if condition is not None:
                condition = SQLBinaryExpr(condition, OP_AND, SQLBinaryExpr(COL_NAME_LBLCHECKPOINTS_NAME, OP_EQ,
                                                                           SQLLiteral(name.lower())))
            else:
                condition = SQLBinaryExpr(COL_NAME_LBLCHECKPOINTS_NAME, OP_EQ, SQLLiteral(name.lower()))
        rowcount = self.delete_generic_data(TABLE_NAME_OBJ_LBLCHECKPOINTS, condition)
        return rowcount

    def DeleteLabelCheckpoint(self, checkpointid=None, name=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "DeleteLabelCheckpoint" is deprecated use '
        msg += '"delete_label_checkpoint" instead'
        warn(msg, stacklevel=2)
        return self.delete_label_checkpoint(checkpointid, name)

    def update_label_checkpoint(self, checkpointid, new_name):
        """
        Update label checkpoint entry i.e. rename the label checkpoint

        :param checkpointid: checkpoint id
        :type checkpointid: int
        :param new_name: Update or New name for existing checkpoint id
        :type new_name: str
        :return: Number of row effected
        :rtype: int
        """
        condition = SQLBinaryExpr(COL_NAME_LBLCHECKPOINTS_CHECKPOINTID, OP_EQ, checkpointid)
        update_record = {COL_NAME_LBLCHECKPOINTS_NAME: new_name.lower().lower()}
        rowcount = self.update_generic_data(update_record, TABLE_NAME_OBJ_LBLCHECKPOINTS, condition)
        return rowcount

    def UpdateLabelCheckpoint(self, checkpointid, new_name):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "UpdateLabelCheckpoint" is deprecated use '
        msg += '"update_label_checkpoint" instead'
        warn(msg, stacklevel=2)
        return self.update_label_checkpoint(checkpointid, new_name)

    def get_label_checkpoint(self, checkpointid=None, name=None):
        """
        Get Label Checkpoint for given name or checkpoint id
        if such record exist return dictionary as record otherwise return None

        :param checkpointid: checkpoint id from database
        :type checkpointid: int
        :param name: Algo Checkpoint e.g. AL_ARSD0_02.00.00.01_INT-2
        :type name: str
        :return: Singla record as dictionary. if no record found return None
        :rtype: dict
        """
        condition = None
        if checkpointid is not None:
            condition = SQLBinaryExpr(COL_NAME_LBLCHECKPOINTS_CHECKPOINTID, OP_EQ, checkpointid)

        if name is not None:
            if condition is not None:
                condition = SQLBinaryExpr(condition, OP_AND,
                                          SQLBinaryExpr(COL_NAME_LBLCHECKPOINTS_NAME, OP_EQ,
                                                        SQLLiteral(name.lower())))
            else:
                condition = SQLBinaryExpr(COL_NAME_LBLCHECKPOINTS_NAME, OP_EQ, SQLLiteral(name.lower()))

        lbl_checkpoint_record = self.select_generic_data(table_list=[TABLE_NAME_OBJ_LBLCHECKPOINTS], where=condition)

        if len(lbl_checkpoint_record) > 1:
            self._log.error("Ambigious or duplicate Checkpoint entry found")
            raise StandardError("Ambigious or duplicate Checkpoint entry found")
        elif len(lbl_checkpoint_record) == 1:
            return lbl_checkpoint_record[0]

        return None

    def GetLabelCheckpoint(self, checkpointid=None, name=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetLabelCheckpoint" is deprecated use '
        msg += '"get_label_checkpoint" instead'
        warn(msg, stacklevel=2)
        return self.get_label_checkpoint(checkpointid, name)

    def get_label_checkpoint_name(self, checkpointid):
        """
        Get Label Checkpoint name for given checkpoint id

        :param checkpointid: checkpoint id from database
        :type checkpointid: int
        :return: Checkpoint LAbel
        :rtype: str
        """
        lbl_checkpoint_record = self.get_label_checkpoint(checkpointid=checkpointid)
        if lbl_checkpoint_record is None:
            return None
        else:
            return lbl_checkpoint_record[COL_NAME_LBLCHECKPOINTS_NAME]

    def GetLabelCheckpointName(self, checkpointid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetLabelCheckpointName" is deprecated use '
        msg += '"get_label_checkpoint_name" instead'
        warn(msg, stacklevel=2)
        return self.get_label_checkpoint_name(checkpointid)

    def get_label_checkpoint_id(self, name):
        """
        Get Label Checkpoint id for given checkpoint name

        :param name: Algo Checkpoint e.g. AL_ARSD0_02.00.00.01_INT-2
        :type name: str
        :return: Checkpoint Id
        :rtype: int
        """
        lbl_checkpoint_record = self.get_label_checkpoint(name=name)
        if lbl_checkpoint_record is None:
            return None
        else:
            return lbl_checkpoint_record[COL_NAME_LBLCHECKPOINTS_CHECKPOINTID]

    def GetLabelCheckpointId(self, name):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetLabelCheckpointId" is deprecated use '
        msg += '"get_label_checkpoint_id" instead'
        warn(msg, stacklevel=2)
        return self.get_label_checkpoint_id(name)

    def add_ego_kine_adma_label_checkpoint(self, measid, checkpointid):  # pylint: disable=C0103
        """
        Add LabelCheckpoint used to import EgoKinematics Adma data

        :param measid: Measurement Id
        :type measid: int
        :param checkpointid: Checkpoint Id
        :type checkpointid: int
        :return: Ego Kinematic checkpoint map id of newly insert row
        :rtype: int
        """
        return self.__add_ego_kine_label_checkpoint(measid, checkpointid, is_adma=1)

    def AddEgoKineAdmaLabelCheckpoint(self, measid, checkpointid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "AddEgoKineAdmaLabelCheckpoint" is deprecated use '
        msg += '"add_ego_kine_adma_label_checkpoint" instead'
        warn(msg, stacklevel=2)
        return self.add_ego_kine_adma_label_checkpoint(measid, checkpointid)

    def add_ego_kine_label_checkpoint(self, measid, checkpointid):
        """
        Get LabelCheckpoint Id used for import EgoKinematics data

        :param measid: Measurement Id
        :type measid: int
        :param checkpointid: Checkpoint Id
        :type checkpointid: int
        :return: List of record
        :rtype: list
        """
        return self.__add_ego_kine_label_checkpoint(measid, checkpointid, is_adma=0)

    def AddEgoKineLabelCheckpoint(self, measid, checkpointid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "AddEgoKineLabelCheckpoint" is deprecated use '
        msg += '"add_ego_kine_label_checkpoint" instead'
        warn(msg, stacklevel=2)
        return self.add_ego_kine_label_checkpoint(measid, checkpointid)

    def __add_ego_kine_label_checkpoint(self, measid, checkpointid, is_adma=0):
        """
        Generic fucntion to Add Checkpoint measurement map
        :param measid: Measurement Id
        :type measid: int
        :param checkpointid: Checkpoint Id
        :type checkpointid: int
        :param is_adma: flag Is_Adma if the kinematics were imported in EgoKinematcs_Adma
        :type is_adma: int
        :return: Return Ego checkpoint map ID for newly inserted row
        :rtype: int
        """

        if self.__get_ego_kine_label_checkpoint_id(measid, is_adma=is_adma) is None:

            ego_kine_checkpoiont = {COL_NAME_EGOKINE_CHECKPOINTMAP_MEASID: measid,
                                    COL_NAME_EGOKINE_CHECKPOINTMAP_CHECKPOINTID: checkpointid,
                                    COL_NAME_EGOKINE_CHECKPOINTMAP_IS_ADMA: is_adma}

            self.add_generic_data(ego_kine_checkpoiont, TABLE_NAME_OBJ_EGOKINE_CHECKPOINTMAP)
            map_record = self.__get_ego_kine_checkpoint_map(measid=measid, checkpointid=checkpointid, is_adma=is_adma)
            return map_record[0][COL_NAME_EGOKINE_CHECKPOINTMAP_EGOMAPID]
        else:
            self._log.error("Checkpoint entry already exist for measurement")
            return None

    def get_ego_kine_label_checkpoint_id(self, measid):  # pylint: disable=C0103
        """
        Get LabelCheckpoint Id used for import EgoKinematics data

        :param measid: Measurement Id
        :type measid: int
        :return: Return Ego label checkpoint Id
        :rtype: int
        """
        return self.__get_ego_kine_label_checkpoint_id(measid)

    def GetEgoKineLabelCheckpointId(self, measid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetEgoKineLabelCheckpointId" is deprecated use '
        msg += '"get_ego_kine_label_checkpoint_id" instead'
        warn(msg, stacklevel=2)
        return self.get_ego_kine_label_checkpoint_id(measid)

    def get_ego_kine_label_checkpoint_name(self, measid):  # pylint: disable=C0103
        """
        Get LabelCheckpoint Name used for import EgoKinematics data

        :param measid: Measurement Id
        :type measid: int
        :return: Return Ego label checkpoint Name
        :rtype: str
        """
        checkpointid = self.get_ego_kine_label_checkpoint_id(measid)
        if checkpointid is not None:
            return self.get_label_checkpoint_name(checkpointid=checkpointid)
        return None

    def GetEgoKineLabelCheckpointName(self, measid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetEgoKineLabelCheckpointName" is deprecated use '
        msg += '"get_ego_kine_label_checkpoint_name" instead'
        warn(msg, stacklevel=2)
        return self.get_ego_kine_label_checkpoint_name(measid)

    def get_ego_kine_adma_label_checkpoint_id(self, measid):  # pylint: disable=C0103
        """
        Get Algo Checkpoint Id used for import EgoKinematics Adma data

        :param measid: Measurement Id
        :type measid: int
        :return: Checkpoint label ID
        :rtype: int
        """
        return self.__get_ego_kine_label_checkpoint_id(measid, is_adma=1)

    def GetEgoKineAdmaLabelCheckpointId(self, measid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetEgoKineAdmaLabelCheckpointId" is deprecated use '
        msg += '"get_ego_kine_adma_label_checkpoint_id" instead'
        warn(msg, stacklevel=2)
        return self.get_ego_kine_adma_label_checkpoint_id(measid)

    def get_ego_kine_adma_label_checkpoint_name(self, measid):  # pylint: disable=C0103
        """
        Get LabelCheckpoint Name used for import EgoKinematics Adma data

        :param measid: Measurement Id
        :type measid: int
        :return: Checkpoint label Name
        :rtype: str
        """
        checkpointid = self.get_ego_kine_adma_label_checkpoint_id(measid)
        if checkpointid is not None:
            return self.get_label_checkpoint_name(checkpointid=checkpointid)
        return None

    def GetEgoKineAdmaLabelCheckpointName(self, measid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetEgoKineAdmaLabelCheckpointName" is deprecated use '
        msg += '"get_ego_kine_adma_label_checkpoint_name" instead'
        warn(msg, stacklevel=2)
        return self.get_ego_kine_adma_label_checkpoint_name(measid)

    def __get_ego_kine_label_checkpoint_id(self, measid, is_adma=0):  # pylint: disable=C0103
        """
        Generic fucntion to get Checkpoint for given measurement

        :param measid: Measurement Id
        :type measid: int
        :param is_adma: flag Is_Adma if the kinematics were imported in EgoKinematcs_Adma
        :type is_adma: int
        :return: Checkpoint label Id
        :rtype: int
        """
        ego_checkpoint_record = self.__get_ego_kine_checkpoint_map(measid=measid, is_adma=is_adma)

        if len(ego_checkpoint_record) > 1:
            self._log.error("Ambigious or duplicate Checkpoint entry found for measurement")
            raise StandardError("Ambigious or duplicate Checkpoint entry found for measurement")
        elif len(ego_checkpoint_record) == 1:
            return ego_checkpoint_record[0][COL_NAME_EGOKINE_CHECKPOINTMAP_CHECKPOINTID]
        return None

    def __get_ego_kine_checkpoint_map(self, mapid=None, measid=None, checkpointid=None, is_adma=0):
        """
        Basic Function Get checkpoint maps record for Ego Kinematics

        :param mapid: Ego Kine Checkpoint map Id
        :type mapid: int
        :param measid: Measurement Id
        :type measid: int
        :param checkpointid: Checkpoint Id
        :type checkpointid:
        :param is_adma: Flag whether the ego kinematics was ADMA or not: Default 0 i.e. not Adma
        :type is_adma: int
        :return: List of record
        :rtype: list
        """
        where = SQLBinaryExpr(COL_NAME_EGOKINE_CHECKPOINTMAP_IS_ADMA, OP_EQ, is_adma)
        conditions = []

        if mapid is not None:
            conditions.append(SQLBinaryExpr(COL_NAME_EGOKINE_CHECKPOINTMAP_EGOMAPID, OP_EQ, mapid))

        if measid is not None:
            conditions.append(SQLBinaryExpr(COL_NAME_EGOKINE_CHECKPOINTMAP_MEASID, OP_EQ, measid))

        if checkpointid is not None:
            conditions.append(SQLBinaryExpr(COL_NAME_EGOKINE_CHECKPOINTMAP_CHECKPOINTID, OP_EQ, checkpointid))

        for i in range(len(conditions)):
            where = SQLBinaryExpr(where, OP_AND, conditions[i])

        ego_kine_chkpt_map = self.select_generic_data(table_list=[TABLE_NAME_OBJ_EGOKINE_CHECKPOINTMAP], where=where)
        return ego_kine_chkpt_map

    def add_rect_obj_label_checkpoint(self, rectobjid, checkpointid):
        """
        Add checkpoint info for rectangular object

        :param rectobjid: rectangular object Id
        :type rectobjid: int
        :param checkpointid: checkpoint id
        :type checkpointid: int
        :return: Checkpoint map ID for newly inserted record
        :rtype: int
        """
        if self.get_rect_obj_label_checkpoint_id(rectobjid) is not None:
            self._log.error("Rectangular object is already binded with a checkpoint")
            return None
        else:
            rectobj_checkpoint_map = {COL_NAME_RECTOBJ_CHECKPOINTMAP_RECTOBJID: rectobjid,
                                      COL_NAME_RECTOBJ_CHECKPOINTMAP_CHECKPOINTID: checkpointid}

            self.add_generic_data(rectobj_checkpoint_map, TABLE_NAME_OBJ_RECTOBJ_CHECKPOINTMAP)
            records = self.get_rect_obj_checkpoint_map(rectobjid=rectobjid, checkpointid=checkpointid)
            return records[0][COL_NAME_RECTOBJ_CHECKPOINTMAP_RECTOBJMAPID]

    def AddRectObjLabelCheckpoint(self, rectobjid, checkpointid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "AddRectObjLabelCheckpoint" is deprecated use '
        msg += '"add_rect_obj_label_checkpoint" instead'
        warn(msg, stacklevel=2)
        return self.add_rect_obj_label_checkpoint(rectobjid, checkpointid)

    def delete_rect_obj_label_checkpoint(self, rectobjid):  # pylint: disable=C0103
        """
        Delete checkpoint info for rectangular object

        :param rectobjid: rectangular object Id
        :type rectobjid: int
        :return:  No. of rows deleted
        :rtype: int
        """
        condition = SQLBinaryExpr(COL_NAME_RECTOBJ_CHECKPOINTMAP_RECTOBJID, OP_EQ, rectobjid)
        rowcount = self.delete_generic_data(TABLE_NAME_OBJ_RECTOBJ_CHECKPOINTMAP, condition)
        return rowcount

    def DeleteRectObjLabelCheckpoint(self, rectobjid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "DeleteRectObjLabelCheckpoint" is deprecated use '
        msg += '"delete_rect_obj_label_checkpoint" instead'
        warn(msg, stacklevel=2)
        return self.delete_rect_obj_label_checkpoint(rectobjid)

    def get_rect_obj_label_checkpoint_id(self, rectobjid):  # pylint: disable=C0103
        """
        Get Algo Checkpoint used to import given rectangular object

        :param rectobjid: Rectangular Object ID
        :type rectobjid: int
        :return: Checkpoint Id
        :rtype: int
        """
        recobj_chkpt_map = self.get_rect_obj_checkpoint_map(rectobjid=rectobjid)
        if len(recobj_chkpt_map) > 1:
            self._log.error("Ambigious or duplicate Checkpoint entry found for rectangular Object")
            raise StandardError("Ambigious or duplicate Checkpoint entry found for rectangular Object")

        elif len(recobj_chkpt_map) == 1:
            return int(recobj_chkpt_map[0][COL_NAME_RECTOBJ_CHECKPOINTMAP_CHECKPOINTID])

        return None

    def GetRectObjLabelCheckpointId(self, rectobjid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetRectObjLabelCheckpointId" is deprecated use '
        msg += '"get_rect_obj_label_checkpoint_id" instead'
        warn(msg, stacklevel=2)
        return self.get_rect_obj_label_checkpoint_id(rectobjid)

    def get_rect_obj_label_checkpoint_name(self, rectobjid):  # pylint: disable=C0103
        """
        Get Algo Checkpoint name used to import given rectangular object

        :param rectobjid: Rectangular Object Id
        :type rectobjid: int
        :return: Checkpoint Name
        :rtype: str
        """
        checkpointid = self.get_rect_obj_label_checkpoint_id(rectobjid)
        if checkpointid is not None:
            return self.get_label_checkpoint_name(checkpointid=checkpointid)
        return None

    def GetRectObjLabelCheckpointName(self, rectobjid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetRectObjLabelCheckpointName" is deprecated use '
        msg += '"get_rect_obj_label_checkpoint_name" instead'
        warn(msg, stacklevel=2)
        return self.get_rect_obj_label_checkpoint_name(rectobjid)

    def get_rect_obj_checkpoint_map(self, mapid=None, rectobjid=None, checkpointid=None):
        """
        Basic Function Get rectangular object checkpoint maps

        :param mapid: Checkpoint map id
        :type mapid: int
        :param rectobjid: Rectangular Object Id
        :type rectobjid: int
        :param checkpointid: Checkpoint Id
        :type checkpointid: int
        :return: list of record
        :rtype: list
        """
        conditions = []
        where = None
        if mapid is not None:
            conditions.append(SQLBinaryExpr(COL_NAME_RECTOBJ_CHECKPOINTMAP_RECTOBJMAPID, OP_EQ, mapid))

        if rectobjid is not None:
            conditions.append(SQLBinaryExpr(COL_NAME_RECTOBJ_CHECKPOINTMAP_RECTOBJID, OP_EQ, rectobjid))

        if checkpointid is not None:
            conditions.append(SQLBinaryExpr(COL_NAME_RECTOBJ_CHECKPOINTMAP_CHECKPOINTID, OP_EQ, checkpointid))

        if len(conditions):
            where = conditions[0]
        for i in range(1, len(conditions)):
            where = SQLBinaryExpr(where, OP_AND, conditions[i])

        table_list = [TABLE_NAME_OBJ_RECTOBJ_CHECKPOINTMAP]
        recobj_chkpt_map = self.select_generic_data(table_list=table_list, where=where)
        return recobj_chkpt_map

    def GetRectObjCheckpointMap(self, mapid=None, rectobjid=None, checkpointid=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetRectObjCheckpointMap" is deprecated use '
        msg += '"get_rect_obj_checkpoint_map" instead'
        warn(msg, stacklevel=2)
        return self.get_rect_obj_checkpoint_map(mapid, rectobjid, checkpointid)

    # ===================================================================
    # Interface helper functions
    # ===================================================================
    def __get_db_rect_object_id(self, object_id):
        """
        Get rect object id from current object map

        :param object_id: rect object id
        :type object_id: int
        :return: Rectangular Object Id
        :rtype: int
        """
        return self.__object_map.get(object_id)

    def __get_next_rect_object_id(self):
        """
        Get the next available rectangular object ID
        :return: Rectangular object Id
        :rtype: int
        """
        return self._get_next_id(TABLE_NAME_RECTANGULAR_OBJECT, COL_NAME_RECT_OBJ_RECTOBJID)


# ====================================================================
# Constraint DB Libary SQL Server Compact Implementation
# ====================================================================
class PluginObjDataDB(BaseObjDataDB, PluginBaseDB):  # pylint: disable=R0904
    """used by plugin finder"""
    def __init__(self, *args, **kwargs):
        """some comment is missing"""
        BaseObjDataDB.__init__(self, *args, **kwargs)


class SQLCEObjDataDB(BaseObjDataDB, PluginBaseDB):  # pylint: disable=R0904
    """SQL Server Compact Edition Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseObjDataDB.__init__(self, *args, **kwargs)


class OracleObjDataDB(BaseObjDataDB, PluginBaseDB):  # pylint: disable=R0904
    """Oracle Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseObjDataDB.__init__(self, *args, **kwargs)


class SQLite3ObjDataDB(BaseObjDataDB, PluginBaseDB):  # pylint: disable=R0904
    """Oracle Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseObjDataDB.__init__(self, *args, **kwargs)


"""
$Log: objdata.py  $
Revision 1.11 2017/10/20 14:19:03CEST Hospes, Gerd-Joachim (uidv8815) 
fix error in logging for missing name
Revision 1.10 2017/10/20 13:50:02CEST Hospes, Gerd-Joachim (uidv8815)
final corrections
Revision 1.9 2017/10/20 12:16:54CEST Hospes, Gerd-Joachim (uidv8815)
add usage of obj_table_name in OBJ_ASSOCIATIONTYPES
Revision 1.8 2016/08/16 16:01:41CEST Hospes, Gerd-Joachim (uidv8815)
fix epydoc errors
Revision 1.7 2016/08/16 12:26:21CEST Hospes, Gerd-Joachim (uidv8815)
update module and class docu
Revision 1.6 2016/07/05 10:07:11CEST Hospes, Gerd-Joachim (uidv8815)
add column list to get_test_cases_for_rec_file,
some pylint fixes
Revision 1.5 2015/12/07 10:00:33CET Mertens, Sven (uidv7805)
removing pep8 errors
Revision 1.4 2015/07/14 11:40:32CEST Mertens, Sven (uidv7805)
rewinding some changes
--- Added comments ---  uidv7805 [Jul 14, 2015 11:40:32 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.3 2015/07/14 09:31:18CEST Mertens, Sven (uidv7805)
simplify for plugin finder
--- Added comments ---  uidv7805 [Jul 14, 2015 9:31:19 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.2 2015/04/30 11:09:31CEST Hospes, Gerd-Joachim (uidv8815)
merge last changes
--- Added comments ---  uidv8815 [Apr 30, 2015 11:09:32 AM CEST]
Change Package : 330394:1 http://mks-psad:7002/im/viewissue?selection=330394
Revision 1.1 2015/04/23 19:04:15CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/obj/project.pj
Revision 1.62 2015/04/27 14:35:37CEST Mertens, Sven (uidv7805)
ident string fix
--- Added comments ---  uidv7805 [Apr 27, 2015 2:35:38 PM CEST]
Change Package : 329312:2 http://mks-psad:7002/im/viewissue?selection=329312
Revision 1.61 2015/03/26 11:40:17CET Ahmed, Zaheer (uidu7634)
add delete_labeld_lane_delete_activity()
changes in get_labeled_lane_delete_activity_view() to get data with
inner join query if view is not available
--- Added comments ---  uidu7634 [Mar 26, 2015 11:40:18 AM CET]
Change Package : 314217:1 http://mks-psad:7002/im/viewissue?selection=314217
Revision 1.60 2015/03/23 10:39:57CET Ahmed, Zaheer (uidu7634)
get_labeled_object_kinematics() added new argment incl_deleted
--- Added comments ---  uidu7634 [Mar 23, 2015 10:39:57 AM CET]
Change Package : 318005:1 http://mks-psad:7002/im/viewissue?selection=318005
Revision 1.59 2015/03/20 10:52:24CET Ahmed, Zaheer (uidu7634)
create view for lanedelete activity table
added function get_labeled_lane_delete_activity_view()
bug fix for missing argument in deprecated method
--- Added comments ---  uidu7634 [Mar 20, 2015 10:52:25 AM CET]
Change Package : 314217:1 http://mks-psad:7002/im/viewissue?selection=314217
Revision 1.58 2015/03/12 10:11:25CET Ahmed, Zaheer (uidu7634)
bug fix to prevent crash for invalid rect obj ID
--- Added comments ---  uidu7634 [Mar 12, 2015 10:11:25 AM CET]
Change Package : 316389:1 http://mks-psad:7002/im/viewissue?selection=316389
Revision 1.57 2015/03/09 11:55:40CET Ahmed, Zaheer (uidu7634)
improved doc string and remove depracted method usage
--- Added comments ---  uidu7634 [Mar 9, 2015 11:55:41 AM CET]
Change Package : 314217:1 http://mks-psad:7002/im/viewissue?selection=314217
Revision 1.56 2015/03/09 11:52:09CET Ahmed, Zaheer (uidu7634)
passing error_tolerance as keyword argument
--- Added comments ---  uidu7634 [Mar 9, 2015 11:52:10 AM CET]
Change Package : 314217:1 http://mks-psad:7002/im/viewissue?selection=314217
Revision 1.55 2015/03/05 12:55:54CET Mertens, Sven (uidv7805)
parameter fix
--- Added comments ---  uidv7805 [Mar 5, 2015 12:55:54 PM CET]
Change Package : 312733:1 http://mks-psad:7002/im/viewissue?selection=312733
Revision 1.54 2015/02/26 15:47:10CET Ahmed, Zaheer (uidu7634)
removed uncessary SQLiteral over integer datatypes
--- Added comments ---  uidu7634 [Feb 26, 2015 3:47:11 PM CET]
Change Package : 310109:1 http://mks-psad:7002/im/viewissue?selection=310109
Revision 1.53 2015/01/29 09:16:29CET Mertens, Sven (uidv7805)
disabling naming convention for deprecated methods
--- Added comments ---  uidv7805 [Jan 29, 2015 9:16:29 AM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.52 2015/01/28 08:25:29CET Mertens, Sven (uidv7805)
removing deprecated calls
--- Added comments ---  uidv7805 [Jan 28, 2015 8:25:30 AM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.51 2014/12/16 19:23:04CET Ellero, Stefano (uidw8660)
Remove all db.obj based deprecated function usage inside STK and module tests.
--- Added comments ---  uidw8660 [Dec 16, 2014 7:23:04 PM CET]
Change Package : 281278:1 http://mks-psad:7002/im/viewissue?selection=281278
Revision 1.50 2014/12/08 10:05:28CET Mertens, Sven (uidv7805)
removing duplicate get_next_id
--- Added comments ---  uidv7805 [Dec 8, 2014 10:05:29 AM CET]
Change Package : 281273:1 http://mks-psad:7002/im/viewissue?selection=281273
Revision 1.49 2014/10/13 15:19:02CEST Ahmed, Zaheer (uidu7634)
add argument remove in delete_rectangular_object
add new function delete_ego_kinematics_adma()
--- Added comments ---  uidu7634 [Oct 13, 2014 3:19:03 PM CEST]
Change Package : 268541:2 http://mks-psad:7002/im/viewissue?selection=268541
Revision 1.48 2014/10/09 10:35:23CEST Mertens, Sven (uidv7805)
remove terminate overwrite
--- Added comments ---  uidv7805 [Oct 9, 2014 10:35:24 AM CEST]
Change Package : 270336:1 http://mks-psad:7002/im/viewissue?selection=270336
Revision 1.47 2014/10/07 15:20:42CEST Ahmed, Zaheer (uidu7634)
added new argument bylabelstate in get_last_modified_lane_association_view()
--- Added comments ---  uidu7634 [Oct 7, 2014 3:20:42 PM CEST]
Change Package : 241672:1 http://mks-psad:7002/im/viewissue?selection=241672
Revision 1.46 2014/10/02 12:34:45CEST Ahmed, Zaheer (uidu7634)
added new function get_last_delete_lane_association()
--- Added comments ---  uidu7634 [Oct 2, 2014 12:34:46 PM CEST]
Change Package : 241672:1 http://mks-psad:7002/im/viewissue?selection=241672
Revision 1.45 2014/09/30 15:42:42CEST Ahmed, Zaheer (uidu7634)
remove comment which was place to disable lane deleted activity for debug purpose
--- Added comments ---  uidu7634 [Sep 30, 2014 3:42:43 PM CEST]
Change Package : 241672:1 http://mks-psad:7002/im/viewissue?selection=241672
Revision 1.44 2014/09/30 13:53:47CEST Ahmed, Zaheer (uidu7634)
remove check of already existing obj testcase of same type in add_test_case()
added new argument in has_test_case()
get_last_modified_lane_assocation_view() bug fix
--- Added comments ---  uidu7634 [Sep 30, 2014 1:53:48 PM CEST]
Change Package : 241672:1 http://mks-psad:7002/im/viewissue?selection=241672
Revision 1.43 2014/09/02 15:11:44CEST Ahmed, Zaheer (uidu7634)
added defination for OBJ_ACCLANEDELETE_ACTIVITY
new method get_last_deleted_lane_assocation_date()
backward compatibilty for SUBSCHEMA_LANEDEL_FEATURE
--- Added comments ---  uidu7634 [Sep 2, 2014 3:11:45 PM CEST]
Change Package : 260448:1 http://mks-psad:7002/im/viewissue?selection=260448
Revision 1.42 2014/09/01 14:54:54CEST Ahmed, Zaheer (uidu7634)
Added new parameter select_list in GetRectObjects()
pep8 and pylint fixes
--- Added comments ---  uidu7634 [Sep 1, 2014 2:54:55 PM CEST]
Change Package : 260441:1 http://mks-psad:7002/im/viewissue?selection=260441
Revision 1.41 2014/08/06 09:56:25CEST Hecker, Robert (heckerr)
updated to new naming convensions.
--- Added comments ---  heckerr [Aug 6, 2014 9:56:25 AM CEST]
Change Package : 253983:1 http://mks-psad:7002/im/viewissue?selection=253983
Revision 1.40 2014/07/30 16:01:25CEST Ahmed, Zaheer (uidu7634)
added new parameter cls_lblstateids in GetRectObjectIds()
--- Added comments ---  uidu7634 [Jul 30, 2014 4:01:26 PM CEST]
Change Package : 252797:1 http://mks-psad:7002/im/viewissue?selection=252797
Revision 1.39 2014/07/18 10:54:38CEST Ahmed, Zaheer (uidu7634)
Correct Doc string in the header of module
--- Added comments ---  uidu7634 [Jul 18, 2014 10:54:39 AM CEST]
Change Package : 241672:1 http://mks-psad:7002/im/viewissue?selection=241672
Revision 1.38 2014/07/16 10:49:20CEST Ahmed, Zaheer (uidu7634)
improved epy documentation
--- Added comments ---  uidu7634 [Jul 16, 2014 10:49:21 AM CEST]
Change Package : 245348:1 http://mks-psad:7002/im/viewissue?selection=245348
Revision 1.37 2014/07/14 15:13:59CEST Ahmed, Zaheer (uidu7634)
Added new function UpdateRectangularObject(), AddLabeledLaneAssociation(), GetTestCaseTypeName(),
GetLastModifiedLaneAssociationView()
Bug Fix in GetRectObjectStartEndTime()
--- Added comments ---  uidu7634 [Jul 14, 2014 3:13:59 PM CEST]
Change Package : 241672:1 http://mks-psad:7002/im/viewissue?selection=241672
Revision 1.36 2014/06/16 10:46:00CEST Ahmed, Zaheer (uidu7634)
Add functions related to Algo Checkpoint for object and ego kinematics label
--- Added comments ---  uidu7634 [Jun 16, 2014 10:46:01 AM CEST]
Change Package : 238464:1 http://mks-psad:7002/im/viewissue?selection=238464
Revision 1.35 2014/06/04 15:51:58CEST Hecker, Robert (heckerr)
BugFix :-)
--- Added comments ---  heckerr [Jun 4, 2014 3:51:59 PM CEST]
Change Package : 241085:1 http://mks-psad:7002/im/viewissue?selection=241085
Revision 1.34 2014/06/04 13:12:06CEST Ahmed, Zaheer (uidu7634)
added new function  GetRectangularObjectView(), GetObjectTestcasesView()
GetLabeledLaneAssociationView()
--- Added comments ---  uidu7634 [Jun 4, 2014 1:12:06 PM CEST]
Change Package : 232650:2 http://mks-psad:7002/im/viewissue?selection=232650
Revision 1.33 2014/05/28 16:15:57CEST Ahmed, Zaheer (uidu7634)
pylint fixes
--- Added comments ---  uidu7634 [May 28, 2014 4:15:58 PM CEST]
Change Package : 239969:1 http://mks-psad:7002/im/viewissue?selection=239969
Revision 1.32 2014/05/28 13:49:21CEST Ahmed, Zaheer (uidu7634)
Change GetEgokinematics to handle timestamp range
--- Added comments ---  uidu7634 [May 28, 2014 1:49:22 PM CEST]
Change Package : 239969:1 http://mks-psad:7002/im/viewissue?selection=239969
Revision 1.31 2014/05/25 19:08:24CEST Ahmed, Zaheer (uidu7634)
from GetNextId() usage in AddRectangular object
Added new coumn UUID in OBJ_RectangularObject
--- Added comments ---  uidu7634 [May 25, 2014 7:08:25 PM CEST]
Change Package : 239054:1 http://mks-psad:7002/im/viewissue?selection=239054
Revision 1.30 2014/04/16 11:17:38CEST Ahmed, Zaheer (uidu7634)
New column defination for RELDISTZ for OBJ_KINEMATICSADMA
--- Added comments ---  uidu7634 [Apr 16, 2014 11:17:39 AM CEST]
Change Package : 224329:2 http://mks-psad:7002/im/viewissue?selection=224329
Revision 1.29 2014/03/10 15:51:45CET Ahmed, Zaheer (uidu7634)
Added DeleteRectangularObject()
--- Added comments ---  uidu7634 [Mar 10, 2014 3:51:46 PM CET]
Change Package : 224154:1 http://mks-psad:7002/im/viewissue?selection=224154
Revision 1.28 2014/03/05 10:40:55CET Ahmed, Zaheer (uidu7634)
Carved out new geneic GetObjectTestCase() from GetApproachLabelForRect() for better code reusability
--- Added comments ---  uidu7634 [Mar 5, 2014 10:40:56 AM CET]
Change Package : 222745:4 http://mks-psad:7002/im/viewissue?selection=222745
Revision 1.27 2014/03/04 11:21:33CET Ahmed, Zaheer (uidu7634)
pep8 pylint fixes
--- Added comments ---  uidu7634 [Mar 4, 2014 11:21:34 AM CET]
Change Package : 222745:3 http://mks-psad:7002/im/viewissue?selection=222745
Revision 1.26 2014/03/04 10:10:31CET Ahmed, Zaheer (uidu7634)
optimized code by increasing reusability, better sql queries to fetch only desired data,
removed uncessary duplicate code, replace sys.exit() with raise StandardErrorand commit() from function
--- Added comments ---  uidu7634 [Mar 4, 2014 10:10:31 AM CET]
Change Package : 222745:3 http://mks-psad:7002/im/viewissue?selection=222745
Revision 1.25 2014/03/03 13:57:38CET Ahmed, Zaheer (uidu7634)
deprecated addEgoKinematicsAdma, addProbsCam, getEgoKinematicsAdma
getProbsCam, getEgoKinematicsAdma
added AddEgoKinematicsAdma, AddProbsCam, GetEgoKinematicsAdma
GetProbsCam, GetEgoKinematicsAdma

remove __getSimpleData, __addSimpleData
--- Added comments ---  uidu7634 [Mar 3, 2014 1:57:38 PM CET]
Change Package : 222745:2 http://mks-psad:7002/im/viewissue?selection=222745
Revision 1.24 2014/02/21 17:46:13CET Sandor-EXT, Miklos (uidg3354)
new add kinematics method
--- Added comments ---  uidg3354 [Feb 21, 2014 5:46:14 PM CET]
Change Package : 208827:2 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.23 2014/02/20 17:25:56CET Ahmed, Zaheer (uidu7634)
pep8 fixes
--- Added comments ---  uidu7634 [Feb 20, 2014 5:25:57 PM CET]
Change Package : 220526:1 http://mks-psad:7002/im/viewissue?selection=220526
Revision 1.22 2014/02/20 16:33:34CET Ahmed, Zaheer (uidu7634)
Optimzed the function GetRectObjectKinematicsBeginEnd()
to get Start and End Kinematic Record with single querey which
feteching only two records from OBJ_KINEMATICS table
--- Added comments ---  uidu7634 [Feb 20, 2014 4:33:34 PM CET]
Change Package : 220526:1 http://mks-psad:7002/im/viewissue?selection=220526
Revision 1.21 2013/08/23 11:05:57CEST Ahmed-EXT, Zaheer (uidu7634)
Fixed pep8 and pylint issues Added  GetLabelClassId GetObjectAssociationTypeId GetObjectLaneTypeId
--- Added comments ---  uidu7634 [Aug 23, 2013 11:05:57 AM CEST]
Change Package : 190321:1 http://mks-psad:7002/im/viewissue?selection=190321
Revision 1.20 2013/07/17 15:00:34CEST Raedler, Guenther (uidt9430)
- revert changes of BaseDB class
--- Added comments ---  uidt9430 [Jul 17, 2013 3:00:34 PM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.19 2013/07/10 09:42:43CEST Raedler, Guenther (uidt9430)
- fixed error for user specific selections in method GetRectObjectByRectObjId()
- added documentation
--- Added comments ---  uidt9430 [Jul 10, 2013 9:42:43 AM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.18 2013/07/04 15:01:30CEST Mertens, Sven (uidv7805)
providing tableSpace to BaseDB for what sub-schema space each module is intended to be responsible
--- Added comments ---  uidv7805 [Jul 4, 2013 3:01:30 PM CEST]
Change Package : 185933:3 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.17 2013/05/27 08:17:33CEST Raedler, Guenther (uidt9430)
- return condition in all cases
--- Added comments ---  uidt9430 [May 27, 2013 8:17:33 AM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.16 2013/05/27 08:12:39CEST Raedler, Guenther (uidt9430)
- added new condition to use only not deleted rect objects for the validation
- added new column COL_NAME_RECT_OBJ_RECTOBJ_IS_DELETED if all RectObjects are requested
--- Added comments ---  uidt9430 [May 27, 2013 8:12:39 AM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.15 2013/04/30 15:48:01CEST Mertens, Sven (uidv7805)
adding select columns when parameter are None
--- Added comments ---  uidv7805 [Apr 30, 2013 3:48:02 PM CEST]
Change Package : 179495:5 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.14 2013/04/26 15:39:06CEST Mertens, Sven (uidv7805)
resolving some pep8 / pylint errors
--- Added comments ---  uidv7805 [Apr 26, 2013 3:39:07 PM CEST]
Change Package : 179495:7 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.13 2013/04/26 10:46:06CEST Mertens, Sven (uidv7805)
moving strIdent
--- Added comments ---  uidv7805 [Apr 26, 2013 10:46:06 AM CEST]
Change Package : 179495:4 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.12 2013/04/25 14:36:51CEST Mertens, Sven (uidv7805)
epydoc adaptation: change from at to colon,
new functions for add and delete for addtional tables added
--- Added comments ---  uidv7805 [Apr 25, 2013 2:36:52 PM CEST]
Change Package : 179495:2 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.11 2013/04/19 13:37:58CEST Hecker, Robert (heckerr)
Functionality reverted to revision 1.9.
--- Added comments ---  heckerr [Apr 19, 2013 1:37:58 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.10 2013/04/12 14:37:00CEST Mertens, Sven (uidv7805)
adding a short representation used by db_connector.PostInitialize
--- Added comments ---  uidv7805 [Apr 12, 2013 2:37:00 PM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.9 2013/04/02 10:04:24CEST Raedler, Guenther (uidt9430)
- use logging for all log messages again
- use specific indeitifier names
--- Added comments ---  uidt9430 [Apr 2, 2013 10:04:24 AM CEST]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.8 2013/03/26 16:19:32CET Mertens, Sven (uidv7805)
pylint: using direct imports, no stars any more
--- Added comments ---  uidv7805 [Mar 26, 2013 4:19:32 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.7 2013/03/21 17:22:38CET Mertens, Sven (uidv7805)
solving some pylint warnings / errors
--- Added comments ---  uidv7805 [Mar 21, 2013 5:22:38 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.6 2013/02/28 08:12:19CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:20 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.5 2013/02/27 17:55:11CET Hecker, Robert (heckerr)
Removed all E000 - E200 Errors regarding Pep8.
--- Added comments ---  heckerr [Feb 27, 2013 5:55:12 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2013/02/27 16:19:56CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 27, 2013 4:19:56 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/26 20:10:30CET Raedler, Guenther (uidt9430)
- Updates after Pep8 Styleguides
--- Added comments ---  uidt9430 [Feb 26, 2013 8:10:30 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.2 2013/02/19 14:07:30CET Raedler, Guenther (uidt9430)
- database interface classes derives from common classes for oracle, ...
- use common exception classes
- use common db functions
--- Added comments ---  uidt9430 [Feb 19, 2013 2:07:31 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/02/11 09:58:59CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/db/obj/project.pj
------------------------------------------------------------------------------
-- From ETK/ADAS_DB Archive
------------------------------------------------------------------------------
Revision 1.27 2012/10/19 10:34:55CEST Hammernik-EXT, Dmitri (uidu5219)
- removed wrong setted comments
- added GetLabeledLaneAssociation und changed GetLabeledLaneAssociationForMeasId
--- Added comments ---  uidu5219 [Oct 19, 2012 10:34:56 AM CEST]
Change Package : 163367:1 http://mks-psad:7002/im/viewissue?selection=163367
Revision 1.26 2012/10/19 08:10:01CEST Ahmed-EXT, Zaheer (uidu7634)
add table and column def OBJ_LBL_STATE and OBJ_ACCLANETYPES
add support function to get LabelStateId and USERID for LBLBY
add column def for labling info  in OBJ_TEST_CASES and ACC_Lane_Relation
updated AddTestCase fucntion
--- Added comments ---  uidu7634 [Oct 19, 2012 8:10:04 AM CEST]
Change Package : 153893:1 http://mks-psad:7002/im/viewissue?selection=153893
Revision 1.25 2012/08/24 10:44:50CEST Ahmed-EXT, Zaheer (uidu7634)
Removed Following Tables:
- Obj_AccLaneRelationLblState
- Obj_ClassLblState
- Obj_DimLblState
- Obj_KinematicLblState

Added Following Tables:

- OBJ_LblState

Add New column def for TABLE_NAME_RECTANGULAR_OBJECT
- RectObj_Is_Deleted
- CLSLBLTIME
- CLSLBLBY
- DIMLBLBSTATEID
- DIMLBLTIME
- DIMLBLBY
- Z0LBLSTATEID
- Z0LBLBY
- Z0LBLTIME
- KINLBLTIME
- KINLBLBY

Remove column def for TABLE_NAME_RECTANGULAR_OBJECT
- LBLMODTIME
- LBLBY
- BEGINOBJABSSTS
- ENDOBJABSTS

Removed Duplicating Column Def for TABLE_NAME_RECTANGULAR_OBJECT
Fix empty list return for GetApproachLabelForRect() when no lable found
Changed select_list for new colum  in GetRectObjects()
Changed select_list for new colum  in GetRectObjectByRectObjId()
--- Added comments ---  uidu7634 [Aug 24, 2012 10:44:54 AM CEST]
Change Package : 153893:1 http://mks-psad:7002/im/viewissue?selection=153893
Revision 1.24 2012/05/16 13:33:53CEST Hammernik-EXT, Dmitri (uidu5219)
- Removed GetCutinTestCasesForRecFile -> use more generic method (GetTestCasesForRecFile)
- added additional parameter in GeLabeledLaneAssociation
--- Added comments ---  uidu5219 [May 16, 2012 1:33:53 PM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.23 2012/05/02 14:53:52CEST Hielscher, Patrick (uidt6110)
Added new functions GetLabeledObjectByLane, GetRectObjectKinematicsSortByKinabsts and GetTestCasesForRecFile
--- Added comments ---  uidt6110 [May 2, 2012 2:53:54 PM CEST]
Change Package : 94404:1 http://mks-psad:7002/im/viewissue?selection=94404
Revision 1.22 2012/03/16 15:22:19CET Hammernik-EXT, Dmitri (uidu5219)
- added new function GetLabeledLaneAssociationForMeasid
--- Added comments ---  uidu5219 [Mar 16, 2012 3:22:19 PM CET]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.21 2012/03/16 10:03:54CET Hammernik-EXT, Dmitri (uidu5219)
- changed GetLabeledLaneAssociation
--- Added comments ---  uidu5219 [Mar 16, 2012 10:03:57 AM CET]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.20 2012/03/05 10:33:16CET Raedler-EXT, Guenther (uidt9430)
- added new functions for lane association
- changed return value of GetLabeledObjectKinematics()
--- Added comments ---  uidt9430 [Mar 5, 2012 10:33:16 AM CET]
Change Package : 100768:2 http://mks-psad:7002/im/viewissue?selection=100768
Revision 1.19 2012/03/02 16:24:43CET Hielscher, Patrick (uidt6110)
Add new function GetLabeledLaneAssociationForRectObjID
--- Added comments ---  uidt6110 [Mar 2, 2012 4:24:43 PM CET]
Change Package : 94393:2 http://mks-psad:7002/im/viewissue?selection=94393
Revision 1.18 2012/02/06 16:35:54CET Hammernik-EXT, Dmitri (uidu5219)
- add new column to selectlist in GetLabeledLaneassociation
--- Added comments ---  uidu5219 [Feb 6, 2012 4:35:55 PM CET]
Change Package : 91989:2 http://mks-psad:7002/im/viewissue?selection=91989
Revision 1.17 2012/02/06 08:23:24CET Raedler Guenther (uidt9430) (uidt9430)
- cast new ID as integer value
--- Added comments ---  uidt9430 [Feb 6, 2012 8:23:25 AM CET]
Change Package : 95134:1 http://mks-psad:7002/im/viewissue?selection=95134
Revision 1.16 2011/12/15 09:41:11CET Hanel, Nele (haneln)
fixed GetLabeledObjectKinematics(self, measid, kinabsts)
added GetLabeledLaneAssociation(self, rectobjid, timestamp)
--- Added comments ---  haneln [Dec 15, 2011 9:41:12 AM CET]
Change Package : 88881:2 http://mks-psad:7002/im/viewissue?selection=88881
Revision 1.15 2011/11/16 11:04:27CET Bogne-EXT, Claude (uidu3860)
- fixed error due to uninitialized parameter
--- Added comments ---  uidu3860 [Nov 16, 2011 11:04:28 AM CET]
Change Package : 78562:1 http://mks-psad:7002/im/viewissue?selection=78562
Revision 1.14 2011/11/14 11:46:24CET Castell Christoph (uidt6394) (uidt6394)
Added GetEgoKinematics(self, measid) function and table definition.
--- Added comments ---  uidt6394 [Nov 14, 2011 11:46:24 AM CET]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.13 2011/11/08 10:44:36CET Raedler Guenther (uidt9430) (uidt9430)
- use new methods to get the kinematics of an rectobject
--- Added comments ---  uidt9430 [Nov 8, 2011 10:44:36 AM CET]
Change Package : 67780:7 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.12 2011/11/08 10:30:57CET Raedler Guenther (uidt9430) (uidt9430)
-
Revision 1.11 2011/10/04 13:09:18CEST Raedler Guenther (uidt9430) (uidt9430)
- fixed error in 'goup by' query option
--- Added comments ---  uidt9430 [Oct 4, 2011 1:09:18 PM CEST]
Change Package : 62766:1 http://mks-psad:7002/im/viewissue?selection=62766
Revision 1.10 2011/09/08 10:07:28CEST Castell Christoph (uidt6394) (uidt6394)
Added GetNextID() for AddTestCase() function.
--- Added comments ---  uidt6394 [Sep 8, 2011 10:07:28 AM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.9 2011/08/29 13:43:51CEST Castell Christoph (uidt6394) (uidt6394)
Fixed logging class bug.
--- Added comments ---  uidt6394 [Aug 29, 2011 1:43:51 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.8 2011/08/25 10:03:09CEST Castell Christoph (uidt6394) (uidt6394)
Removed duplicate functions and corrected naming.
--- Added comments ---  uidt6394 [Aug 25, 2011 10:03:09 AM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.7 2011/08/23 13:59:56CEST Castell Christoph (uidt6394) (uidt6394)
Tidy up of function list. Removal of duplicate function.
--- Added comments ---  uidt6394 [Aug 23, 2011 1:59:56 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.6 2011/08/23 13:37:46CEST Raedler Guenther (uidt9430) (uidt9430)
-- added function to get the rect objects for a defined measid
-- added functions to get the kinematic data for a rect object
--- Added comments ---  uidt9430 [Aug 23, 2011 1:37:46 PM CEST]
Change Package : 67780:2 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.5 2011/07/15 10:47:39CEST Raedler Guenther (uidt9430) (uidt9430)
- renamed base classes to avoid conflicts in namings
--- Added comments ---  uidt9430 [Jul 15, 2011 10:47:39 AM CEST]
Change Package : 67780:2 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.4 2011/07/12 15:52:11CEST Hanel Nele (haneln) (haneln)
add get function for cutin testcases
--- Added comments ---  haneln [Jul 12, 2011 3:52:11 PM CEST]
Change Package : 70482:1 http://mks-psad:7002/im/viewissue?selection=70482
Revision 1.3 2011/06/21 15:33:44CEST Castell Christoph (uidt6394) (uidt6394)
Re-introduced approach functions.
--- Added comments ---  uidt6394 [Jun 21, 2011 3:33:44 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.2 2011/06/20 16:34:36CEST Hanel Nele (haneln) (haneln)
add interface for object test case type id
--- Added comments ---  haneln [Jun 20, 2011 4:34:36 PM CEST]
Change Package : 70482:1 http://mks-psad:7002/im/viewissue?selection=70482
Revision 1.1 2011/06/20 11:15:43CEST Raedler Guenther (uidt9430) (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/EM_EnvironmentModel/05_Testing/05_Test_Environment/algo/
em_req_test/valf_tests/adas_database/obj/project.pj
"""
