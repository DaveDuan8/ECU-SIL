"""
stk/db/lbl/camlabel.py
----------------------

Python library to access camera labels

Sub-Scheme lbl

**User-API**
    - `BaseCameraLabelDB`
        Methods to manage additional label information in camera projects

The other classes in this module are handling the different DB types and are derived from BaseCameraLabelDB.

**usage in Valf suites**

For validation suites based on `Valf` class there is the operator `DbLinker` setting up all needed connections.

**using several connections in parallel**

If several sub-schemes have to be used in parallel the first connection should be reused.
Please check class `BaseCameraLabelDB` for more detail.

**Do not waste the limited number of connections to Oracle DB**
by setting up a new connection for each sub-scheme,
always use the existing one as described in `BaseCameraLabelDB`.

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.8 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 16:01:38CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from os import path
from datetime import datetime

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.db.db_common import BaseDB, DB_FUNC_NAME_LOWER, DB_FUNC_NAME_MAX, DB_FUNC_NAME_SUBSTR, PluginBaseDB
from stk.db.db_sql import SQLBinaryExpr, SQLFuncExpr, SQLColumnExpr, SQLTableExpr, OP_EQ, SQLLiteral, OP_AND, OP_OR, \
    OP_LEQ, OP_AS, OP_GEQ, SQLJoinExpr, OP_INNER_JOIN
from stk.valf.signal_defs import DBCAM

from stk.util.helper import deprecated

# =====================================================================================================================
# Constants
# =====================================================================================================================
# Table base names:
TABLE_NAME_FILE2HSM = "file2hsm"
TABLE_NAME_LBT_CFG = "labeltool_config"
TABLE_NAME_TMT = "TICKET_MASTER_TABLE"
TABLE_NAME_RLT = "revision_log_table"

TABLE_NAME_FOD_CD = "mfc300_fod_cd"
TABLE_NAME_HLA_CD = "mfc300_hla_cd"
TABLE_NAME_LD_CD = "mfc300_ld_cd"
TABLE_NAME_PED_CD = "mfc300_ped_cd"
TABLE_NAME_POD_CD = "mfc300_pod_cd"
TABLE_NAME_PV_CD = "mfc300_pv_cd"
TABLE_NAME_SAC_CD = "mfc300_sac_cd"
TABLE_NAME_SR_CD = "mfc300_sr_cd"

TABLE_NAME_BASE = "mfc300"

TABEL_NAME_CD_POSTFIX = "_CD"
TABEL_NAME_LDSS_POSTFIX = "_LDSS"
TABLE_NAME_ALL_LDSS = "MFC300_%_LSDD"
TABEL_NAME_LDROI_POSTFIX = "_LDROI"

TABEL_NAME_ARC_POSTFIX = "_ARCHIVE"
TABEL_NAME_INF_POSTFIX = "_INTERFACE"

TABLE_NAME_DMT_MANAGED_FILES = "DMT_MANAGED_FILES"
TABLE_NAME_ADMS_LBL_ORDER = "ADMS_LBL_ORDER"
TABLE_NAME_ADMS_LBL_CONFIG = "ADMS_LBL_CONFIG"
TABLE_NAME_ADMS_LBL_SEQUENCES = "ADMS_LBL_SEQUENCES"
TABLE_NAME_ADMS_ADMS_REC_FILE = "ADMS_REC_FILE"

COL_NAME_FILE2HSM_TAN = "TAN"
COL_NAME_FILE2HSM_SOURCE_FILE_SH = "SOURCE_FILE_SH"
COL_NAME_FILE2HSM_SOURCE_FILEPATH = "SOURCE_FILEPATH"
COL_NAME_FILE2HSM_DESTINATION_FILEPATH = "DESTINATION_FILEPATH"
COL_NAME_FILE2HSM_STATUS = "STATUS"
COL_NAME_FILE2HSM_SOURCE_RECIDFILENAME = "SOURCE_RECIDFILENAME"
COL_NAME_FILE2HSM_DESTINATION_RECIDFILENAME = "DESTINATION_RECIDFILENAME"
COL_NAME_FILE2HSM_FILESIZE = "FILESIZE"
COL_NAME_FILE2HSM_GUID = "GUID"

COL_NAME_LBT_CFG_CONF_ID = "CONF_ID"
COL_NAME_LBT_CFG_LABEL_DESC_VERS = "LABEL_DESC_VERS"
COL_NAME_LBT_CFG_CONF_STATUS = "CONF_STATUS"
COL_NAME_LBT_CFG_ASSIGNED_CONF_ID = "ASSIGNED_CONF_ID"

COL_NAME_TMT_TICKET_ID = "TICKET_ID"
COL_NAME_TMT_TRACE_ID = "TRACE_ID"
COL_NAME_TMT_LABEL_DESC_VERS = "LABEL_DESC_VERS"
COL_NAME_TMT_RECMTFILENAME = "RECMTFILENAME"
COL_NAME_TMT_RECIDFILENAME = "RECIDFILENAME"
COL_NAME_TMT_SEQUENZMTTIMESTAMPSTART = "SEQUENZMTTIMESTAMPSTART"
COL_NAME_TMT_SEQUENZMTTIMESTAMPSTOP = "SEQUENZMTTIMESTAMPSTOP"
COL_NAME_TMT_ASSIGNED_TO_USERID = "ASSIGNED_TO_USERID"
COL_NAME_TMT_ASSIGNED_TIMESTAMP = "ASSIGNED_TIMESTAMP"
COL_NAME_TMT_WORK_STATUS = "WORK_STATUS"
COL_NAME_TMT_KOL = "KOL"
COL_NAME_TMT_DATATYPE_IDX = "DATATYPE_IDX"
COL_NAME_TMT_FRAMESELECTION = "FRAMESELECTION"
COL_NAME_TMT_WORK_STATUS_INFO = "WORK_STATUS_INFO"

# Generall collum names
COL_NAME_TAN = "TAN"
COL_NAME_REC_ID_FILE_NAME = "RecIdFileName"

# general rlt collums
COL_NAME_RLT_START_TIME_STAMP = "START_TIME_STAMP"
COL_NAME_RLT_STOP_TIME_STAMP = "STOP_TIME_STAMP"
COL_NAME_RLT_FINAL_TBL = "FINAL_TBL"
COL_NAME_RLT_TAN_FINAL_TBL = "TAN_FINAL_TBL"
COL_NAME_RLT_PROCESS = "PROCESS"
COL_NAME_RLT_TICKET_ID = "TICKET_ID"
COL_NAME_RLT_DESCRIPTION = "DESCRIPTION"
COL_NAME_RLT_FEEDBACK = "FEEDBACK"
COL_NAME_RLT_EVALT_VERSION = "EVALT_VERSION"
COL_NAME_RLT_ALGO_VERSION = "ALGO_VERSION"
COL_NAME_RLT_PRIORITY = "PRIORITY"

# general cd collums
COL_NAME_CD_SEQUENZMTTIMESTAMPSTART = "SEQUENZMTTIMESTAMPSTART"
COL_NAME_CD_START_CYCLE_ID = "CD_START_CYCLE_ID"
COL_NAME_CD_START_CYCLE_COUNTER = "CD_START_CYCLE_COUNTER"
COL_NAME_CD_SEQUENZMTTIMESTAMPSTOP = "SEQUENZMTTIMESTAMPSTOP"
COL_NAME_CD_STOP_CYCLE_ID = "CD_STOP_CYCLE_ID"
COL_NAME_CD_STOP_CYCLE_COUNTER = "CD_STOP_CYCLE_COUNTER"
COL_NAME_CD_GEN_CAR = "GEN_CAR"
COL_NAME_CD_GEN_TEST_SITE = "GEN_TEST_SITE"
COL_NAME_CD_GEN_CHRONO_RELEASE = "GEN_CHRONO_RELEASE"
COL_NAME_CD_GEN_KEYWORD = "GEN_KEYWORD"
COL_NAME_CD_GEN_SENSOR_TYPE = "GEN_SENSOR_TYPE"
COL_NAME_CD_GEN_SAMPLE = "GEN_SAMPLE"
COL_NAME_CD_GEN_SENSOR_NUMBER = "GEN_SENSOR_NUMBER"
COL_NAME_CD_CSF_CAR_LIGHT_SEVERAL = "CSF_CAR_LIGHT_SEVERAL"
COL_NAME_CD_CSF_WINDSCREEN = "CSF_WINDSCREEN"
COL_NAME_CD_CSF_IMAGE_TYPE = "CSF_IMAGE_TYPE"
COL_NAME_CD_GEN_CAR_MAKE = "GEN_CAR_MAKE"
COL_NAME_CD_GEN_CAR_TYPE = "GEN_CAR_TYPE"
COL_NAME_CD_GEN_CAR_OWNER = "GEN_CAR_OWNER"
COL_NAME_CD_START_DATATYPE = "CD_START_DATATYPE"
COL_NAME_CD_STOP_DATATYPE = "CD_STOP_DATATYPE"
COL_NAME_CD_SR_SEQ_SCENARIO = "SR_SEQUENCE_SCENARIO"

# general ldroi collums
COL_NAME_LDROI_TIMESTAMP = "FrameMtLDROITimeStamp"
COL_NAME_LDROI_CYCLE_ID = "LDROI_CYCLE_ID"
COL_NAME_LDROI_CYCLE_COUNTER = "LDROI_CYCLE_COUNTER"
COL_NAME_LDROI_TRACK_ID = "ROI_TRACK_ID"
COL_NAME_LDROI_COORDINATE_X_1 = "ROI_COORDINATE_X_1"
COL_NAME_LDROI_COORDINATE_Y_1 = "ROI_COORDINATE_Y_1"
COL_NAME_LDROI_COORDINATE_X_2 = "ROI_COORDINATE_X_2"
COL_NAME_LDROI_COORDINATE_Y_2 = "ROI_COORDINATE_Y_2"
COL_NAME_LDROI_COORDINATE_X_3 = "ROI_COORDINATE_X_3"
COL_NAME_LDROI_COORDINATE_Y_3 = "ROI_COORDINATE_Y_3"
COL_NAME_LDROI_COORDINATE_X_4 = "ROI_COORDINATE_X_4"
COL_NAME_LDROI_COORDINATE_Y_4 = "ROI_COORDINATE_Y_4"
COL_NAME_LDROI_COORDINATE_X_5 = "ROI_COORDINATE_X_5"
COL_NAME_LDROI_COORDINATE_Y_5 = "ROI_COORDINATE_Y_5"
COL_NAME_LDROI_COORDINATE_X_6 = "ROI_COORDINATE_X_6"
COL_NAME_LDROI_COORDINATE_Y_7 = "ROI_COORDINATE_Y_6"
COL_NAME_LDROI_COORD_QUANTITY = "ROI_QUANTATY_OF_COORDINATES"
COL_NAME_LDROI_DATATYPE = "LDROI_DATATYPE"
COL_NAME_LDROI_BRAKE_LIGHTS = "BRAKE_LIGHTS"
COL_NAME_LDROI_CAM_BOTTOM = "CAM_OBJ_EDGE_VISIBILITY_BOTTOM"
COL_NAME_LDROI_CAM_LEFT = "CAM_OBJ_EDGE_VISIBILITY_LEFT"
COL_NAME_LDROI_CAM_RIGHT = "CAM_OBJ_EDGE_VISIBILITY_RIGHT"
COL_NAME_LDROI_CAM_TOP = "CAM_OBJ_EDGE_VISIBILITY_TOP"
COL_NAME_LDROI_CAM_SIGNAL = "CAM_OBJ_LIGHT_SIGNAL"
COL_NAME_LDROI_FOD_OBJ = "FOD_COVERED_OBJECT"
COL_NAME_LDROI_FOD_OBJ2 = "FOD_COVERED_OBJECT_2ND"
COL_NAME_LDROI_FOD_DIRECTION = "FOD_DIRECTION"
COL_NAME_LDROI_FOD_OBJ_FRAGMENT = "FOD_FRAGMENTARY_OBJECT"
COL_NAME_LDROI_FOD_PED = "FOD_PEDESTRIAN"
COL_NAME_LDROI_FOD_VIEW = "FOD_VIEW"
COL_NAME_LDROI_GEN_LANE = "GEN_LANE_OFFSET"
COL_NAME_LDROI_GEN_OBJ = "GEN_OBJECT_TYPE"
COL_NAME_LDROI_GEN_OBJ_MOVE = "GEN_OBJ_IS_MOVING_OVER_GROUND"
COL_NAME_LDROI_GEN_TARGET = "GEN_TARGET_TYPE"
COL_NAME_LDROI_OD_BOTTOM = "OD_COVERED_FROM_BOTTOM"
COL_NAME_LDROI_OD_LEFT = "OD_COVERED_FROM_LEFT"
COL_NAME_LDROI_OD_RIGHT = "OD_COVERED_FROM_RIGHT"
COL_NAME_LDROI_OD_TOP = "OD_COVERED_FROM_TOP"
COL_NAME_LDROI_OD_ACCESSORY = "PED_CARRY_ACCESSORY"
COL_NAME_LDROI_PED = "PED_GROUP"
COL_NAME_LDROI_PED_PED = "PED_PEDESTRIAN"
COL_NAME_LDROI_PED_VEHICLE = "PED_VEHICLE"
COL_NAME_LDROI_PED_INDICATOR = "TURN_INDICATOR"

# general ldss collums
COL_NAME_LDSS_TIMESTAMP_START = "FRAMEMTLDSSTIMESTAMPSTART"
COL_NAME_LDSS_TIMESTAMP_STOP = "FRAMEMTLDSSTIMESTAMPSTOP"
COL_NAME_LDSS_PED_NO_PEDESTRIAN = "PED_NO_PEDESTRIAN"
COL_NAME_LDSS_PED_PEDS = "PED_PEDESTRIAN_S"
COL_NAME_LDSS_CSF_CHANGING_LIGHT = "CSF_CHANGING_LIGHT_CONDITIONS"
COL_NAME_LDSS_CSF_CONTAMINATION = "CSF_CONTAMINATION"
COL_NAME_LDSS_CSF_LIGHT = "CSF_LIGHT_CONDITIONS"
COL_NAME_LDSS_CSF_SUN = "CSF_SUN_POSITION"
COL_NAME_LDSS_GEN_COUNTRY = "GEN_COUNTRY"
COL_NAME_LDSS_GEN_SPEED = "GEN_EGO_SPEED"
COL_NAME_LDSS_GEN_ROAD = "GEN_ROAD_TYPE"
COL_NAME_LDSS_GEN_ROADWORKS = "GEN_ROAD_WORKS"
COL_NAME_LDSS_GEN_SPECIAL_WEATHER = "GEN_SPECIAL_WEATHER_CONDITIONS"
COL_NAME_LDSS_GEN_STATE = "GEN_STATE"
COL_NAME_LDSS_GEN_STREET = "GEN_STREET_CONDITIONS"
COL_NAME_LDSS_GEN_TUNNEL = "GEN_TUNNEL"
COL_NAME_LDSS_GEN_WEATHER = "GEN_WEATHER"
COL_NAME_LDSS_START_CYCLE = "LDSS_START_CYCLE_COUNTER"
COL_NAME_LDSS_START_CYCLE_ID = "LDSS_START_CYCLE_ID"
COL_NAME_LDSS_START_DTYPE = "LDSS_START_DATATYPE"
COL_NAME_LDSS_STOP_CYCLE = "LDSS_STOP_CYCLE_COUNTER"
COL_NAME_LDSS_STOP_CYCLE_ID = "LDSS_STOP_CYCLE_ID"
COL_NAME_LDSS_STOP_DTYPE = "LDSS_STOP_DATATYPE"
COL_NAME_LDSS_OD_BC = "OD_BC_ALL_LABELED"
COL_NAME_LDSS_OD_BIKE = "OD_BIKE_ALL_LABELED"
COL_NAME_LDSS_OD_MB = "OD_MB_ALL_LABELED"
COL_NAME_LDSS_OD_MC = "OD_MC_ALL_LABELED"
COL_NAME_LDSS_OD_PED = "OD_PED_ALL_LABELED"
COL_NAME_LDSS_OD_UNKN = "OD_UNKN_ALL_LABELED"
COL_NAME_LDSS_OD_VEHICLE = "OD_VEHICLE_ALL_LABELED"

# Table "DMT_MANAGED_FILES"
COL_NAME_DM_FILES_REAL_USED_BLOCKSIZE = "REAL_USED_BLOCKSIZE"
COL_NAME_DM_FILES_TAN = "TAN"
COL_NAME_DM_FILES_SOURCE_FILE_SH = "SOURCE_FILE_SH"
COL_NAME_DM_FILES_SOURCE_FILEPATH = "SOURCE_FILEPATH"
COL_NAME_DM_FILES_DESTINATION_FILEPATH = "DESTINATION_FILEPATH"
COL_NAME_DM_FILES_STATUS = "STATUS"
COL_NAME_DM_FILES_SOURCE_RECIDFILENAME = "SOURCE_RECIDFILENAME"
COL_NAME_DM_FILES_DESTINATION_RECIDFILENAME = "DESTINATION_RECIDFILENAME"
COL_NAME_DM_FILES_FILESIZE = "FILES_FILESIZE"
COL_NAME_DM_FILES_GUID = "GUID"
COL_NAME_DM_FILES_CREATED_TS = "CREATED_TS"
COL_NAME_DM_FILES_MODIFIED_TS = "MODIFIED_TS "
COL_NAME_DM_FILES_DELETED = "DELETED"
COL_NAME_DM_FILES_PREPARATION_TAN = "PREPARATION_TAN"
COL_NAME_DM_FILES_FASTHASH = "FASTHASH"
COL_NAME_DM_FILES_TIMESTAMPSTART = "TIMESTAMPSTART"
COL_NAME_DM_FILES_TIMESTAMPSTOP = "TIMESTAMPSTOP"

# TABLE "ADMS_LBL_ORDER"
COL_NAME_LBL_ORDER_RF_ID = "RF_ID"
COL_NAME_LBL_ORDER_LR_ID = "LR_ID"
COL_NAME_LBL_ORDER_PROJECT_NAME = "PROJECT_NAME"
COL_NAME_LBL_ORDER_FUNCTION_NAME = "FUNCTION_NAME"
COL_NAME_LBL_ORDER_REQ_NO = "REQ_NO"
COL_NAME_LBL_ORDER_SEQUENCE_MT_START = "SEQUENZMTTIMESTAMPSTART"
COL_NAME_LBL_ORDER_SEQUENCE_MT_STOP = "SEQUENZMTTIMESTAMPSTOP"
COL_NAME_LBL_ORDER_H_KZ = "H_KZ"
COL_NAME_LBL_ORDER_REPL_STATUS = "REPL_STATUS"
COL_NAME_LBL_ORDER_LABEL_REQ_TIME_STARTED = "LRTS"

# Table ADMS_LBL_SEQUENCES
COL_NAME_LBL_SEQUENCES_SEQUENZSTART = "SEQUENZSTART"
COL_NAME_LBL_SEQUENCES_SEQUENZSTOP = "SEQUENZSTOP"
COL_NAME_LBL_SEQUENCES_LR_ID = "LR_ID"
COL_NAME_LBL_SEQUENCES_CONF_ID = "CONF_ID"

# Table ADMS_REC_FILE
COL_NAME_REC_FILE_SOURCE_FILE_SH = "SOURCE_FILE_SH"
COL_NAME_REC_FILE_SOURCE_FILE_SH_CORR = "SOURCE_FILE_SH_CORR"
COL_NAME_REC_FILE_RF_ID = "RF_ID"
COL_NAME_REC_FILE_START = "TIMESTAMP_START"
COL_NAME_REC_FILE_STOP = "TIMESTAMP_STOP"
# consts
DEFAULD_TIMESTAMP_THRESHOLD = 61000

LABEL_ORDER_FINAL_TABLE = "F"
LABEL_ORDER_ARCHIVED_TABLE = "A"
LABEL_ORDER_COMPLETED = "COMPLETED"
IDENT_STRING = DBCAM


# - classes -----------------------------------------------------------------------------------------------------------
class BaseCameraLabelDB(BaseDB):  # pylint: disable=R0904
    """**Base implementation of the camera label Database**

    For the first connection to the DB for lbl tables just create a new instance of this class like

    .. python::

        from stk.db.lbl.camlabel import BaseCameraLabelDB

        dbclb = BaseCameraLabelDB("MFC4XX")   # or use "ARS4XX", "VGA" or path/name of sqlite file

    If already some connection to another table of the DB is created use that one to speed up your code:

    .. python::

        dbclb = BaseCameraLabelDB(dbxxx.db_connection)

    The connection is closed when the first instance using it is deleted.

    More optional keywords are described at `BaseDB` class initialization.

    """
    # ====================================================================
    # Constraint DB Libary Interface for public use
    # ====================================================================

    # ====================================================================
    # Handling of database
    # ====================================================================

    def __init__(self, *args, **kwargs):
        """
        Constructor to initialize BaseCameraLabelDB to represent ADMS_ADMIN Scheme

        :keyword db_connection: The database connection to be used
        :type db_connection: cx_oracle.Connection, pydodbc.Connection, sqlite3.Connection, sqlce.Connection
        :keyword table_prefix: The table name prefix which is usually master schema name
        :type table_prefix: str
        """
        tnames = (kwargs.pop('tableBase', 'MFC400'), kwargs.pop('component', 'SOD'), kwargs.pop('labelState', ''),)
        kwargs['strIdent'] = DBCAM
        BaseDB.__init__(self, *args, **kwargs)

        self._table_names = None
        self._table_basis = None
        self.set_table_names(*tnames)

        self.db_func_map[DB_FUNC_NAME_SUBSTR] = "SUBSTR"

#     @property
#     def table_names(self):
#         """property to retrieve table names to be able to reference against
#         """
#         return self._table_names

    def get_table_names(self):
        """property to retrieve table names to be able to reference against
        """
        return self._table_names

    def set_table_names(self, table_base, component, labelState=""):  # pylint: disable=C0103
        """
        sets the table names

        :param table_base: basis, e.g. mfc400
        :type table_base: str
        :param component: subcomponent of table name, e.g. SR, SOD, etc.
        :type component: str
        :param labelState: either '' or 'interface' or 'archive'
        :type labelState: str
        """
        self._table_basis = (table_base.upper(), component.upper(), labelState.upper())
        basename = self._table_basis[0] + "_" + self._table_basis[1] + "_%s"
        if self._table_basis[2] not in (None, ""):
            basename += "_" + self._table_basis[2]
        self._table_names = (basename % "CD", basename % "LDROI", basename % "LDSS")

    def __get_camera_table(self, component, label_type, label_state):
        """
        Get the camera table name which has special naming component_LabelType_labelState

        :param component: The component name ped, fod, pod ..
        :type component: str
        :param label_type: The label type, cd, ldss, ldroi
        :type label_type: str
        :param label_state: The normal, interface, archive
        :type label_state: str
        :return: Return Table name
        :rtype: str
        """
        base_name = self._table_basis[0] + "_"
        base_name += (self._table_basis[1] if component is None else component.upper()) + "_"
        base_name += self._table_basis[2] if label_type is None else label_type.upper()

        if label_state == "interface":
            base_name += "_" + "INTERFACE"
        elif label_state == "archive":
            base_name += "_" + "ARCHIVE"
        elif label_state not in ("normal", "", None):
            self._log.warning("Label state is wrong! No such kind of labels: %s" % label_state)

        return base_name

    def _base_cam_label_cond(self, recfilename, component, label_type, label_state):  # pylint: disable=W0613
        """
        Get the base camera table condition

        :param recfilename: The name of the recfile
        :type recfilename: str
        :param component: The component name ped, fod, pod ..
        :type component: str
        :param label_type: The label type, cd, ldss, ldroi
        :type label_type: str
        :param label_state: The normal, interface, archive
        :type label_state: str
        :return: Returns the condition expression
        :rtype: SQLBinaryExpression
        """
        # table = self.__get_camera_table(component, label_type, label_state)

        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                         SQLColumnExpr(None, COL_NAME_REC_ID_FILE_NAME, True)),
                             OP_EQ, SQLLiteral(recfilename.lower()))

        return cond

    def get_camera_labels(self, recfilename, component=None, label_type=None,  # pylint: disable=R0913
                          label_state=None, where=None):
        """
        Get camera label records.

        :param recfilename: The name of the recfile
        :type recfilename: str
        :param component: The component name ped, fod, pod ..
        :type component: str
        :param label_type: The label type, cd, ldss, ldroi
        :type label_type: str
        :param label_state: The normal, interface, archive
        :type label_state: str
        :param where:
        :return: Returns the label record.
        :rtype:  list
        """
        record = []

        table = self.__get_camera_table(component, label_type, label_state)

        cond = self._base_cam_label_cond(recfilename, component, label_type, label_state)

        if where is not None:
            cond = SQLBinaryExpr(cond, OP_AND, where)

        entries = self.select_generic_data(table_list=[table], where=cond)
        if len(entries) <= 0:
            self._log.warning("No labeles found for table %s" % table)
        else:
            record = entries
        # done
        return record

    def get_camera_labels_at_ts(self, recfilename, timestamp, component=None,  # pylint: disable=R0913
                                label_type=None, label_state=None):
        """
        Get camera label records at timestamp.

        :param recfilename: The name of the recfile
        :type recfilename: str
        :param timestamp: search all labels at this timestamp
        :type timestamp: str
        :param component: The component name ped, fod, pod ..
        :type component: str
        :param label_type: The label type, cd, ldss, ldroi
        :type label_type: str
        :param label_state: The normal, interface, archive
        :type label_state: str
        :return: Returns the label record.
        :rtype: list
        """
        table = self.__get_camera_table(component, label_type, label_state)

        cond = SQLBinaryExpr(self._base_cam_label_cond(recfilename, component, label_type, label_state),
                             OP_AND,
                             SQLBinaryExpr(SQLColumnExpr(None, COL_NAME_LDROI_TIMESTAMP, True), OP_EQ, timestamp))

        entries = self.select_generic_data(table_list=[table], where=cond)
        if len(entries) <= 0:
            self._log.warning("No labeles found for table %s at timestamp %s and recfile %s"
                              % (table, timestamp, recfilename))
        return entries

    def get_camera_labels_prev_ts(self, recfilename, timestamp, component=None,  # pylint: disable=R0913
                                  label_type=None, label_state=None, timestamp_threshold=DEFAULD_TIMESTAMP_THRESHOLD):
        """
        Get camera label records for previous step from timestamp.

        :param recfilename: The name of the recfile
        :type recfilename: str
        :param timestamp: search all labels at this timestamp
        :type timestamp: str
        :param component: The component name ped, fod, pod ..
        :type component: str
        :param label_type: The label type, cd, ldss, ldroi
        :type label_type: str
        :param label_state: The normal, interface, archive
        :type label_state: str
        :param timestamp_threshold:
        :return: Returns the label record, if a label is found within a threshold value, otherwise retern None.
        :rtype: list
        """
        table = self.__get_camera_table(component, label_type, label_state)
        # select max(ifc."FrameMtLDROITimeStamp") from sautners."MFC300_PED_LDROI_INTERFACE" ifc
        # where ifc."RecIdFileName" = 'Continuous_2011.09.11_at_16.27.29.rec' and
        # ifc."FrameMtLDROITimeStamp" <= 168318175
        # order by ifc."FrameMtLDROITimeStamp" desc

        timestampcol = SQLColumnExpr(SQLTableExpr(table), COL_NAME_LDROI_TIMESTAMP, True)

        cond = SQLBinaryExpr(self._base_cam_label_cond(recfilename, component, label_type, label_state),
                             OP_AND,
                             SQLBinaryExpr(timestampcol, OP_LEQ, timestamp))

        select = [SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_MAX], timestampcol),
                                OP_AS, COL_NAME_LDROI_TIMESTAMP.upper())]

        order_expr = [timestampcol]

        entries = self.select_generic_data(select_list=select, table_list=[table],
                                           where=cond, order_by=order_expr)
        prev_timestamp = None
        if len(entries) <= 0:
            self._log.warning("No labeles with lower timestamp %s found for table %s and recording %s"
                              % (timestamp, table, recfilename))
        else:
            prev_timestamp = entries[0][COL_NAME_LDROI_TIMESTAMP.upper()]

        if prev_timestamp is not None and (timestamp - prev_timestamp < timestamp_threshold):
            record = self.get_camera_labels_at_ts(recfilename, prev_timestamp, component, label_type, label_state)
        else:
            record = None

        return record

    def get_camera_labels_next_ts(self, recfilename, timestamp, component=None,  # pylint: disable=R0913
                                  label_type=None, label_state=None, timestamp_threshold=DEFAULD_TIMESTAMP_THRESHOLD):
        """
        Get camera label records for next step from timestamp.

        :param recfilename: The name of the recfile
        :type recfilename: str
        :param timestamp: search all labels at this timestamp
        :type timestamp: str
        :param component: The component name ped, fod, pod ..
        :type component: str
        :param label_type: The label type, cd, ldss, ldroi
        :type label_type: str
        :param label_state: The normal, interface, archive
        :type label_state: str
        :param timestamp_threshold:
        :return: Returns the label record, if a label is found within a threshold value, otherwise return None.
        :rtype: list
        """
        record = []

        table = self.__get_camera_table(component, label_type, label_state)
        # select max(ifc."FrameMtLDROITimeStamp") from sautners."MFC300_PED_LDROI_INTERFACE" ifc
        # where ifc."RecIdFileName" = 'Continuous_2011.09.11_at_16.27.29.rec' and
        # ifc."FrameMtLDROITimeStamp" <= 168318175
        # order by ifc."FrameMtLDROITimeStamp" desc

        timestampcol = SQLColumnExpr(None, COL_NAME_LDROI_TIMESTAMP, True)

        cond = SQLBinaryExpr(self._base_cam_label_cond(recfilename, component, label_type, label_state),
                             OP_AND,
                             SQLBinaryExpr(timestampcol, OP_GEQ, timestamp))

        select = [SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_MAX], timestampcol),
                  OP_AS, COL_NAME_LDROI_TIMESTAMP.upper())]

        order_expr = [timestampcol]

        entries = self.select_generic_data(select_list=select, table_list=[table], where=cond, order_by=order_expr)
        prev_timestamp = None
        if len(entries) <= 0:
            self._log.warning("No labeles with higher timestamp %s found for table %s and recording %s"
                              % (timestamp, table, recfilename))
        else:
            prev_timestamp = entries[0][COL_NAME_LDROI_TIMESTAMP.upper()]

        if prev_timestamp is not None and (timestamp - prev_timestamp < timestamp_threshold):
            record = self.get_camera_labels_at_ts(recfilename, prev_timestamp, component, label_type, label_state)
        else:
            record = None

        return record

    def get_roi_track_ids(self, recfilename, component=None, label_type=None, label_state=None):
        """
        Get camera label records for next step from timestamp.

        :param recfilename: The name of the recfile
        :type recfilename: str
        :param component: The component name ped, fod, pod ..
        :type component: str
        :param label_type: The label type, cd, ldss, ldroi
        :type label_type: str
        :param label_state: The normal, interface, archive
        :type label_state: str
        :return: Returns the label trackids.
        :rtype: list
        """
        record = None

        table = self.__get_camera_table(component, label_type, label_state)

        cond = self._base_cam_label_cond(recfilename, component, label_type, label_state)

        trackidcol = SQLColumnExpr(SQLTableExpr(table), COL_NAME_LDROI_TRACK_ID, True)

        select = [SQLBinaryExpr(trackidcol, OP_AS, COL_NAME_LDROI_TRACK_ID)]

        entries = self.select_generic_data(select_list=select, table_list=[table],
                                           where=cond, order_by=[trackidcol], distinct_rows=True)
        if len(entries) <= 0:
            self._log.warning("No labeles found for table %s" % table)
        else:
            record = []
            for item in entries:
                record.append(int(item[COL_NAME_LDROI_TRACK_ID]))
        # done
        return record

    def get_object_with_track_id(self, recfilename, track_id, component=None, label_type=None,  # pylint: disable=R0913
                                 label_state=None):
        """
        Get camera label records for next step from timestamp.

        :param recfilename: The name of the recfile
        :type recfilename: str
        :param track_id: The labeled object track id
        :type track_id: str
        :param component: The component name ped, fod, pod ..
        :type component: str
        :param label_type: The label type, cd, ldss, ldroi
        :type label_type: str
        :param label_state: The normal, interface, archive
        :type label_state: str
        :return: Returns the label trackids.
        :rtype: list
        """
        record = None

        table = self.__get_camera_table(component, label_type, label_state)

        trackidcol = SQLColumnExpr(SQLTableExpr(table), COL_NAME_LDROI_TRACK_ID, True)

        timestampcol = SQLColumnExpr(None, COL_NAME_LDROI_TIMESTAMP, True)

        cond = self._base_cam_label_cond(recfilename, component, label_type, label_state)

        cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(trackidcol, OP_EQ, track_id))

        entries = self.select_generic_data(table_list=[table], where=cond, order_by=[timestampcol])
        if len(entries) <= 0:
            self._log.warning("No labeles found for table %s" % table)
        else:
            record = entries

        # done
        return record

    def get_measurement_sequences(self, recfile, project_name=None, function=None,  # pylint: disable=R0914,R0915
                                  department=None):
        """
        **Get ordered label sequences (unsorted) for one recording**

        filtered by given project, function and department

        The method returns all label sections that are created for the given parameters,
        the sections might partly or totally overlap in case they are created for later revisions.

        Check short description in Function Test & Validation sharepoint for more details about labeling basics.

        **Carefull**:

        the time stamps in the ordered sections does not have to be a
        valid time stamp of one recording frame, it might be a time value between two adjacend frames!
        Use the returned values as lower or upper border when filtering recording frames.

        :param recfile: name of recording, can contain leading path which will be ignored
        :type recfile: str
        :param project_name: Project name to filter label sequences. Default value None to skip from criteria
        :type project_name: str
        :param function: Function name to filter label sequences. Default value None to skip from criteria
        :type function: str
        :param department: department name to filter sequences. Default value None to skip from criteria
        :type department: str, currently used ['dev'|'eva']
        :return: list of tupels with start and end time of the labeled sections and list of label revision
                 corresponding to each section
        :rtype:  list like [ (2314, 2401), (2450, 2485), (2350, 2378), (2480, 2493)], [1,2,3,3]
        """
        var_values = {}
        alisas_dmf = "dmf"
        alias_lbl_order = "lo"
        alias_adrecfile = "adrecfile"
        alias_lbl_seq = "ls"
        alias_lbconf = "lbconf"
        alias_mt = "mt"
        tbl_adrecfile = SQLTableExpr(TABLE_NAME_ADMS_ADMS_REC_FILE, alias_adrecfile)
        tbl_dmf = SQLTableExpr(TABLE_NAME_DMT_MANAGED_FILES, alisas_dmf)
        tbl_lo = SQLTableExpr(TABLE_NAME_ADMS_LBL_ORDER, alias_lbl_order)
        tbl_ls = SQLTableExpr(TABLE_NAME_ADMS_LBL_SEQUENCES, alias_lbl_seq)
        tbl_lbconf = SQLTableExpr(TABLE_NAME_ADMS_LBL_CONFIG, alias_lbconf)
        tbl_mticket = SQLTableExpr(TABLE_NAME_TMT, alias_mt)

        col_seq_start = SQLColumnExpr(alias_lbl_seq, COL_NAME_LBL_SEQUENCES_SEQUENZSTART)
        col_seq_stop = SQLColumnExpr(alias_lbl_seq, COL_NAME_LBL_SEQUENCES_SEQUENZSTOP)
        col_adrec_srcfile = SQLColumnExpr(alias_adrecfile, COL_NAME_REC_FILE_SOURCE_FILE_SH)
        col_adrec_srcfile_corr = SQLColumnExpr(alias_adrecfile, COL_NAME_REC_FILE_SOURCE_FILE_SH_CORR)
        col_dmf_srcfile = SQLColumnExpr(alisas_dmf, COL_NAME_DM_FILES_SOURCE_FILE_SH)
        col_lo_rf_id = SQLColumnExpr(alias_lbl_order, COL_NAME_LBL_ORDER_RF_ID)
        col_adrecfile_rf_id = SQLColumnExpr(alias_adrecfile, COL_NAME_REC_FILE_RF_ID)
        col_lo_lr_id = SQLColumnExpr(alias_lbl_order, COL_NAME_LBL_ORDER_LR_ID)
        col_lo_h_kz = SQLColumnExpr(alias_lbl_order, COL_NAME_LBL_ORDER_H_KZ)
        col_lo_repl_stat = SQLColumnExpr(alias_lbl_order, COL_NAME_LBL_ORDER_REPL_STATUS)
        col_ls_lr_id = SQLColumnExpr(alias_lbl_seq, COL_NAME_LBL_SEQUENCES_LR_ID)
        col_lbconf_confid = SQLColumnExpr(alias_lbconf, COL_NAME_LBT_CFG_CONF_ID)
        col_ls_confid = SQLColumnExpr(alias_lbl_seq, COL_NAME_LBL_SEQUENCES_CONF_ID)
        col_func_name = SQLColumnExpr(alias_lbl_order, COL_NAME_LBL_ORDER_FUNCTION_NAME)
        col_proj_name = SQLColumnExpr(alias_lbl_order, COL_NAME_LBL_ORDER_PROJECT_NAME)
        col_lbl_des_vers = SQLColumnExpr(alias_lbconf, COL_NAME_LBT_CFG_LABEL_DESC_VERS)
        col_dest_recfile = SQLColumnExpr(alisas_dmf, COL_NAME_DM_FILES_DESTINATION_RECIDFILENAME)
        col_mt_seq_start = SQLBinaryExpr(SQLColumnExpr(alias_mt, '"%s"' % "SequenzMtTimeStampStart"),
                                         OP_AS, COL_NAME_LBL_ORDER_SEQUENCE_MT_START)
        col_mt_seq_stop = SQLBinaryExpr(SQLColumnExpr(alias_mt, '"%s"' % "SequenzMtTimeStampStop"),
                                        OP_AS, COL_NAME_LBL_ORDER_SEQUENCE_MT_STOP)

        col_mt_tkid = SQLColumnExpr(alias_mt, COL_NAME_TMT_TICKET_ID)
        col_lo_tkid = SQLColumnExpr(alias_lbl_order, COL_NAME_TMT_TICKET_ID)
        col_lo_reqno = SQLColumnExpr(alias_lbl_order, COL_NAME_LBL_ORDER_REQ_NO)
        col_lo_lrts = SQLColumnExpr(alias_lbl_order, COL_NAME_LBL_ORDER_LABEL_REQ_TIME_STARTED)
        col_rec_ts_start = SQLColumnExpr(alias_adrecfile, COL_NAME_REC_FILE_START)
        col_rec_ts_stop = SQLColumnExpr(alias_adrecfile, COL_NAME_REC_FILE_STOP)

        _, recfile = path.split(recfile)
        var_values['rec'] = recfile.lower()
        condition = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER], col_dest_recfile), OP_EQ, ":rec")

        # check if order is completed (H_KZ=='F'|'A' and REPL_STATUS=='COMPLETED')
        # so labels are really created and stored
        var_values['hkz'] = LABEL_ORDER_FINAL_TABLE
        label_stat = SQLBinaryExpr(col_lo_h_kz, OP_EQ, ":hkz")
        var_values['loa'] = LABEL_ORDER_ARCHIVED_TABLE
        label_stat = SQLBinaryExpr(label_stat, OP_OR, SQLBinaryExpr(col_lo_h_kz, OP_EQ, ":loa"))
        condition = SQLBinaryExpr(condition, OP_AND, label_stat)
        var_values['cml'] = LABEL_ORDER_COMPLETED
        condition = SQLBinaryExpr(condition, OP_AND, SQLBinaryExpr(col_lo_repl_stat, OP_EQ, ":cml"))
        if project_name is not None:
            var_values['prj'] = project_name.upper()
            condition = SQLBinaryExpr(condition, OP_AND, SQLBinaryExpr(col_proj_name, OP_EQ, ":prj"))
        if function is not None:
            var_values['fnc'] = function.upper()
            condition = SQLBinaryExpr(condition, OP_AND, SQLBinaryExpr(col_func_name, OP_EQ, ":fnc"))
        if department is not None:
            var_values['dep'] = department.upper()
            condition = SQLBinaryExpr(condition, OP_AND,
                                      SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_SUBSTR],
                                                                str(col_lbl_des_vers) + ", 22, 3"),
                                                    OP_EQ, ":dep"))

        join = SQLJoinExpr(tbl_dmf, OP_INNER_JOIN, tbl_adrecfile,
                           SQLBinaryExpr(SQLBinaryExpr(col_adrec_srcfile, OP_EQ, col_dmf_srcfile),
                                         OP_OR,
                                         SQLBinaryExpr(col_adrec_srcfile_corr, OP_EQ, col_dmf_srcfile)))
        join = SQLJoinExpr(join, OP_INNER_JOIN, tbl_lo, SQLBinaryExpr(col_lo_rf_id, OP_EQ, col_adrecfile_rf_id))
        join = SQLJoinExpr(join, OP_INNER_JOIN, tbl_ls, SQLBinaryExpr(col_ls_lr_id, OP_EQ, col_lo_lr_id))
        join = SQLJoinExpr(join, OP_INNER_JOIN, tbl_lbconf, SQLBinaryExpr(col_lbconf_confid, OP_EQ, col_ls_confid))
        join = SQLJoinExpr(join, OP_INNER_JOIN, tbl_mticket, SQLBinaryExpr(col_mt_tkid, OP_EQ, col_lo_tkid))

        entries = self.select_generic_data([col_seq_start, col_seq_stop, col_mt_seq_start, col_mt_seq_stop,
                                            col_lo_lrts, col_lo_reqno, col_rec_ts_start, col_rec_ts_stop],
                                           table_list=[join], where=condition,
                                           order_by=[col_seq_start], sqlparams=var_values)
        label_seq = []  # Label Sequence
        revision = []
        # check if label order is created after 20.09.2014:
        # from this date on all cam label orders are executed on the complete recording ignoring the existence
        #  of sections in the current new order or reorders with 'old' section settings
        #  !! but the section times are not updated !!
        # so the returned start/stop timestamps are not valid if the order is created after the mentioned date
        # in that case only the recording start and stop times are returned:
        rec = entries[0] if entries else None
        if rec is not None and (rec[COL_NAME_LBL_ORDER_LABEL_REQ_TIME_STARTED] - datetime(2014, 9, 20)).days > 0:
            label_seq.append((rec[COL_NAME_REC_FILE_START], rec[COL_NAME_REC_FILE_STOP]))
            revision.append(rec[COL_NAME_LBL_ORDER_REQ_NO])
        else:
            for rec in entries:
                label_seq.append((rec[COL_NAME_LBL_SEQUENCES_SEQUENZSTART],
                                  rec[COL_NAME_LBL_SEQUENCES_SEQUENZSTOP]))
                revision.append(rec[COL_NAME_LBL_ORDER_REQ_NO])

        return label_seq, revision

    @deprecated('set_table_names')
    def setTableNames(self, tableBase, component, labelState=""):  # pylint: disable=C0103
        """deprecated"""
        return self.set_table_names(tableBase, component, labelState)

    @property
    @deprecated('get_table_names (method)')
    def tableNames(self):  # pylint: disable=C0103
        """deprecated"""
        return self._table_names

    @deprecated('get_camera_labels')
    def GetCameraLabels(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_camera_labels(*args, **kw)

    @deprecated('get_camera_labels_at_ts')
    def GetCameraLabelsAtTs(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_camera_labels_at_ts(*args, **kw)

    @deprecated('get_camera_labels_prev_ts')
    def GetCameraLabelsPrevTs(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_camera_labels_prev_ts(*args, **kw)

    @deprecated('get_camera_labels_next_ts')
    def GetCameraLabelsNextTs(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_camera_labels_next_ts(*args, **kw)

    @deprecated('get_roi_track_ids')
    def GetRoiTrackIds(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_roi_track_ids(*args, **kw)

    @deprecated('get_object_with_track_id')
    def GetObjectWithTrackId(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_object_with_track_id(*args, **kw)

    @deprecated('get_measurement_sequences')
    def GetMeasurementSequences(self, recfile, project_name=None,  # pylint: disable=R0914,C0103
                                function=None, department=None):
        """deprecated"""
        return self.get_measurement_sequences(recfile, project_name, function, department)


# =====================================================================================================================
# Constraint DB Libary SQL Server Compact Implementation
# =====================================================================================================================
class PluginCamLabelDB(BaseCameraLabelDB, PluginBaseDB):  # pylint: disable=R0904
    """used by plugin finder"""
    def __init__(self, *args, **kwargs):
        """some comment is missing"""
        BaseCameraLabelDB.__init__(self, *args, **kwargs)


class SQLCECameraLabelDB(BaseCameraLabelDB, PluginBaseDB):  # pylint: disable=R0904
    """SQL Server Compact Edition Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseCameraLabelDB.__init__(self, *args, **kwargs)


class OracleCameraLabelDB(BaseCameraLabelDB, PluginBaseDB):  # pylint: disable=R0904
    """Oracle Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseCameraLabelDB.__init__(self, *args, **kwargs)


class SQLite3CameraLabelDB(BaseCameraLabelDB, PluginBaseDB):  # pylint: disable=R0904
    """Oracle Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseCameraLabelDB.__init__(self, *args, **kwargs)


""" Python library to access camera lables
$Log: camlabel.py  $
Revision 1.8 2016/08/16 16:01:38CEST Hospes, Gerd-Joachim (uidv8815) 
fix epydoc errors
Revision 1.7 2016/08/16 12:26:20CEST Hospes, Gerd-Joachim (uidv8815)
update module and class docu
Revision 1.6 2015/10/13 14:18:50CEST Mertens, Sven (uidv7805)
fix: should be dict, not a tuple
- Added comments -  uidv7805 [Oct 13, 2015 2:18:51 PM CEST]
Change Package : 380875:1 http://mks-psad:7002/im/viewissue?selection=380875
Revision 1.5 2015/08/03 11:11:08CEST Mertens, Sven (uidv7805)
change name
--- Added comments ---  uidv7805 [Aug 3, 2015 11:11:09 AM CEST]
Change Package : 363419:1 http://mks-psad:7002/im/viewissue?selection=363419
Revision 1.4 2015/07/14 13:16:06CEST Mertens, Sven (uidv7805)
reverting some changes
--- Added comments ---  uidv7805 [Jul 14, 2015 1:16:07 PM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.3 2015/07/14 09:30:51CEST Mertens, Sven (uidv7805)
simplify for plugin finder
--- Added comments ---  uidv7805 [Jul 14, 2015 9:30:52 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.2 2015/04/30 11:09:27CEST Hospes, Gerd-Joachim (uidv8815)
merge last changes
--- Added comments ---  uidv8815 [Apr 30, 2015 11:09:27 AM CEST]
Change Package : 330394:1 http://mks-psad:7002/im/viewissue?selection=330394
Revision 1.1 2015/04/23 19:04:09CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/lbl/project.pj
Revision 1.50 2015/04/27 14:38:29CEST Mertens, Sven (uidv7805)
ident string fix
--- Added comments ---  uidv7805 [Apr 27, 2015 2:38:30 PM CEST]
Change Package : 329312:2 http://mks-psad:7002/im/viewissue?selection=329312
Revision 1.49 2015/04/22 11:47:03CEST Ahmed, Zaheer (uidu7634)
corrected keyword argument name
--- Added comments ---  uidu7634 [Apr 22, 2015 11:47:03 AM CEST]
Change Package : 329058:2 http://mks-psad:7002/im/viewissue?selection=329058
Revision 1.48 2015/04/21 16:57:52CEST Ahmed, Zaheer (uidu7634)
binded variables support for select generic function to improve oracle performance
--- Added comments ---  uidu7634 [Apr 21, 2015 4:57:53 PM CEST]
Change Package : 329058:1 http://mks-psad:7002/im/viewissue?selection=329058
Revision 1.47 2015/04/21 11:32:32CEST Ahmed, Zaheer (uidu7634)
improvement in where condition to utilze indexes for the column on which where condition is created
--- Added comments ---  uidu7634 [Apr 21, 2015 11:32:32 AM CEST]
Change Package : 329058:1 http://mks-psad:7002/im/viewissue?selection=329058
Revision 1.46 2015/04/20 10:28:57CEST Ahmed, Zaheer (uidu7634)
temp work around to grab label order sequence with repl_status = Completed with python
i.e. excluding it from where condition of the query
--- Added comments ---  uidu7634 [Apr 20, 2015 10:28:58 AM CEST]
Change Package : 329058:1 http://mks-psad:7002/im/viewissue?selection=329058
Revision 1.45 2015/03/20 08:02:46CET Mertens, Sven (uidv7805)
timestamp column name fix
--- Added comments ---  uidv7805 [Mar 20, 2015 8:02:47 AM CET]
Change Package : 319697:1 http://mks-psad:7002/im/viewissue?selection=319697
Revision 1.44 2015/03/05 14:18:14CET Mertens, Sven (uidv7805)
using keyword is better
--- Added comments ---  uidv7805 [Mar 5, 2015 2:18:14 PM CET]
Change Package : 312989:1 http://mks-psad:7002/im/viewissue?selection=312989
Revision 1.43 2015/03/05 14:10:37CET Mertens, Sven (uidv7805)
fix for parameter
Revision 1.42 2015/02/12 10:36:25CET Mertens, Sven (uidv7805)
rename of column table
Revision 1.41 2015/01/19 16:20:21CET Mertens, Sven (uidv7805)
raw column not needed when not using quotes
Revision 1.40 2014/12/19 11:20:06CET Mertens, Sven (uidv7805)
adaptation of column 'FrameMtLDROITimeStamp', for quotation problem
--- Added comments ---  uidv7805 [Dec 19, 2014 11:20:07 AM CET]
Change Package : 288758:1 http://mks-psad:7002/im/viewissue?selection=288758
Revision 1.39 2014/12/02 17:15:45CET Hospes, Gerd-Joachim (uidv8815)
merge check for empty section list in main
--- Added comments ---  uidv8815 [Dec 2, 2014 5:15:45 PM CET]
Change Package : 285920:1 http://mks-psad:7002/im/viewissue?selection=285920
Revision 1.36.1.1 2014/12/01 16:22:50CET Hospes, Gerd-Joachim (uidv8815)
add check for empty section list
--- Added comments ---  uidv8815 [Dec 1, 2014 4:22:50 PM CET]
Change Package : 285920:1 http://mks-psad:7002/im/viewissue?selection=285920
add missed brackets
--- Added comments ---  uidv8815 [Nov 28, 2014 2:07:27 PM CET]
Change Package : 286089:1 http://mks-psad:7002/im/viewissue?selection=286089
Revision 1.37 2014/11/27 17:00:21CET Hospes, Gerd-Joachim (uidv8815)
extend filter for H_KZ=('A' or 'F')
--- Added comments ---  uidv8815 [Nov 27, 2014 5:00:22 PM CET]
Change Package : 285920:1 http://mks-psad:7002/im/viewissue?selection=285920
Revision 1.36 2014/11/18 19:44:15CET Hospes, Gerd-Joachim (uidv8815)
filter entered in camlabel, manual test as label db changes too often
--- Added comments ---  uidv8815 [Nov 18, 2014 7:44:15 PM CET]
Change Package : 282449:1 http://mks-psad:7002/im/viewissue?selection=282449
Revision 1.35 2014/11/17 08:10:36CET Mertens, Sven (uidv7805)
name updates
--- Added comments ---  uidv7805 [Nov 17, 2014 8:10:37 AM CET]
Change Package : 281272:1 http://mks-psad:7002/im/viewissue?selection=281272
Revision 1.34 2014/11/04 20:50:10CET Ahmed, Zaheer (uidu7634)
remove label sequence which are rejected but allow label sequence with state null
--- Added comments ---  uidu7634 [Nov 4, 2014 8:50:10 PM CET]
Change Package : 274722:1 http://mks-psad:7002/im/viewissue?selection=274722
Revision 1.33 2014/11/04 16:25:39CET Hospes, Gerd-Joachim (uidv8815)
1st try to remove rejected label sections
--- Added comments ---  uidv8815 [Nov 4, 2014 4:25:39 PM CET]
Change Package : 275075:1 http://mks-psad:7002/im/viewissue?selection=275075
Revision 1.32 2014/10/10 08:51:47CEST Hecker, Robert (heckerr)
Updates in naming convensions.
--- Added comments ---  heckerr [Oct 10, 2014 8:51:48 AM CEST]
Change Package : 270868:1 http://mks-psad:7002/im/viewissue?selection=270868
Revision 1.31 2014/10/06 15:43:05CEST Ahmed, Zaheer (uidu7634)
epy doc improvement
--- Added comments ---  uidu7634 [Oct 6, 2014 3:43:06 PM CEST]
Change Package : 245347:1 http://mks-psad:7002/im/viewissue?selection=245347
Revision 1.30 2014/08/20 18:45:00CEST Hospes, Gerd-Joachim (uidv8815)
filter only completed label orders, manual test only in test_dtm/test_lbl
--- Added comments ---  uidv8815 [Aug 20, 2014 6:45:01 PM CEST]
Change Package : 253116:2 http://mks-psad:7002/im/viewissue?selection=253116
Revision 1.29 2014/08/12 10:18:16CEST Hospes, Gerd-Joachim (uidv8815)
add join checking also SOURCE_FILE_SH_CORR, add test
--- Added comments ---  uidv8815 [Aug 12, 2014 10:18:16 AM CEST]
Change Package : 255930:1 http://mks-psad:7002/im/viewissue?selection=255930
Revision 1.28 2014/07/25 15:57:06CEST Mertens, Sven (uidv7805)
added missing defaults to init method
and a bit of duplicate codeline removal
--- Added comments ---  uidv7805 [Jul 25, 2014 3:57:07 PM CEST]
Change Package : 251810:1 http://mks-psad:7002/im/viewissue?selection=251810
Revision 1.27 2014/07/17 13:38:38CEST Ahmed, Zaheer (uidu7634)
function department and project argument made optional
updated module test to check optional parameter
--- Added comments ---  uidu7634 [Jul 17, 2014 1:38:39 PM CEST]
Change Package : 247294:1 http://mks-psad:7002/im/viewissue?selection=247294
Revision 1.26 2014/07/16 14:36:34CEST Hospes, Gerd-Joachim (uidv8815)
cleanup camlabel, reduce dmt.lbl to one function, update tests
--- Added comments ---  uidv8815 [Jul 16, 2014 2:36:34 PM CEST]
Change Package : 245477:1 http://mks-psad:7002/im/viewissue?selection=245477
Revision 1.25 2014/07/16 11:45:15CEST Ahmed, Zaheer (uidu7634)
interface change return just sequence and also revisions
--- Added comments ---  uidu7634 [Jul 16, 2014 11:45:16 AM CEST]
Change Package : 247294:1 http://mks-psad:7002/im/viewissue?selection=247294
Revision 1.24 2014/07/15 15:49:19CEST Ahmed, Zaheer (uidu7634)
modified  GetMeasurementSequences() function to return list of tuple for label sequence
--- Added comments ---  uidu7634 [Jul 15, 2014 3:49:19 PM CEST]
Change Package : 247294:1 http://mks-psad:7002/im/viewissue?selection=247294
Revision 1.23 2014/07/14 17:42:09CEST Hospes, Gerd-Joachim (uidv8815)
add GetMergedSequences and some epydocs
--- Added comments ---  uidv8815 [Jul 14, 2014 5:42:10 PM CEST]
Change Package : 245477:1 http://mks-psad:7002/im/viewissue?selection=245477
Revision 1.22 2014/07/14 10:25:55CEST Ahmed, Zaheer (uidu7634)
refined GetMesurementSequence() by reduced local variables
--- Added comments ---  uidu7634 [Jul 14, 2014 10:25:56 AM CEST]
Change Package : 247294:1 http://mks-psad:7002/im/viewissue?selection=247294
Revision 1.21 2014/07/14 09:59:39CEST Ahmed, Zaheer (uidu7634)
GetMesurementSequence() added to provided label order sequence
--- Added comments ---  uidu7634 [Jul 14, 2014 9:59:40 AM CEST]
Change Package : 247294:1 http://mks-psad:7002/im/viewissue?selection=247294
Revision 1.20 2013/08/07 11:05:22CEST Mertens, Sven (uidv7805)
changed header info from genlabel to camlabel
--- Added comments ---  uidv7805 [Aug 7, 2013 11:05:22 AM CEST]
Change Package : 192785:1 http://mks-psad:7002/im/viewissue?selection=192785
Revision 1.19 2013/08/02 15:39:35CEST Mertens, Sven (uidv7805)
bugfixing recidfilename define
Revision 1.18 2013/06/25 15:35:43CEST Mertens, Sven (uidv7805)
fixing defines to be capital letters as well as column names to be consistent
--- Added comments ---  uidv7805 [Jun 25, 2013 3:35:44 PM CEST]
Change Package : 185933:1 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.17 2013/06/20 15:24:35CEST Mertens, Sven (uidv7805)
1) as initial DB base names can be set via init or setTableNames,
they should be optional by methods now.
2) adding additional defines for label columns specific for SOD;
maybe we should think about moving them seperatly as there
could be hundreds throughout lbl db.
--- Added comments ---  uidv7805 [Jun 20, 2013 3:24:35 PM CEST]
Change Package : 185933:1 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.16 2013/06/13 13:06:45CEST Mertens, Sven (uidv7805)
alignment of table base name,
method setTableNames must be used when going via observers as BaseDB interface is limited.
__GetCameraTable is using this basis then.
--- Added comments ---  uidv7805 [Jun 13, 2013 1:06:45 PM CEST]
Change Package : 185933:1 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.15 2013/04/26 15:39:07CEST Mertens, Sven (uidv7805)
resolving some pep8 / pylint errors
--- Added comments ---  uidv7805 [Apr 26, 2013 3:39:08 PM CEST]
Change Package : 179495:7 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.14 2013/04/26 10:46:01CEST Mertens, Sven (uidv7805)
moving strIdent
Revision 1.13 2013/04/26 10:05:40CEST Mertens, Sven (uidv7805)
added init params for table base like MFC400 and function prefix
as well as a getter for the table names
--- Added comments ---  uidv7805 [Apr 26, 2013 10:05:41 AM CEST]
Change Package : 179495:4 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.12 2013/04/25 14:35:10CEST Mertens, Sven (uidv7805)
epydoc adaptation to colon instead of at
--- Added comments ---  uidv7805 [Apr 25, 2013 2:35:11 PM CEST]
Change Package : 179495:2 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.11 2013/04/19 13:38:59CEST Hecker, Robert (heckerr)
Functionality reverted to revision 1.9.
--- Added comments ---  heckerr [Apr 19, 2013 1:38:59 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.10 2013/04/12 14:37:01CEST Mertens, Sven (uidv7805)
adding a short representation used by db_connector.PostInitialize
--- Added comments ---  uidv7805 [Apr 12, 2013 2:37:02 PM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.9 2013/04/02 10:24:57CEST Mertens, Sven (uidv7805)
pylint: E0213, E1123, E9900, E9904, E1003, E9905, E1103
--- Added comments ---  uidv7805 [Apr 2, 2013 10:24:58 AM CEST]
Change Package : 176171:9 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.8 2013/03/27 11:37:21CET Mertens, Sven (uidv7805)
pep8 & pylint: rowalignment and error correction
Revision 1.7 2013/03/26 16:19:22CET Mertens, Sven (uidv7805)
pylint: using direct imports, no stars any more
--- Added comments ---  uidv7805 [Mar 26, 2013 4:19:23 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.6 2013/03/13 17:52:59CET Hecker, Robert (heckerr)
Added needed changes for Zhang.
--- Added comments ---  heckerr [Mar 13, 2013 5:52:59 PM CET]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.5 2013/02/28 08:12:16CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:16 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2013/02/27 16:19:53CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 27, 2013 4:19:53 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/19 14:07:28CET Raedler, Guenther (uidt9430)
- database interface classes derives from common classes for oracle, ...
- use common exception classes
- use common db functions
--- Added comments ---  uidt9430 [Feb 19, 2013 2:07:28 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.2 2013/02/13 09:43:56CET Hecker, Robert (heckerr)
Added missing import.
--- Added comments ---  heckerr [Feb 13, 2013 9:43:56 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2013/02/11 09:58:40CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/db/lbl/project.pj
------------------------------------------------------------------------------
-- From ETK/ADAS_DB Archive
------------------------------------------------------------------------------
Revision 1.3 2012/10/12 08:45:55CEST Spruck, Jochen (spruckj)
add special camera table defines
--- Added comments ---  spruckj [Oct 12, 2012 8:45:55 AM CEST]
Change Package : 93947:1 http://mks-psad:7002/im/viewissue?selection=93947
Revision 1.2 2012/10/12 08:40:46CEST Spruck, Jochen (spruckj)
add revision log tabel
Revision 1.1 2012/04/27 12:18:29CEST Spruck, Jochen (spruckj)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
PED_PedestrianRecognition/05_Testing/05_Test_Environment/algo/ped_reqtests/valf_tests/adas_database/lb/project.pj
"""
