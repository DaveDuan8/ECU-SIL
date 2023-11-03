"""
stk/db/fct/fct.py
-----------------

Classes for Database access of FCT Label Tables.

Sub-Scheme FCT

*User-API**
    - `BaseFctDB`
        Providing methods to read functional related recording (measurements) details
        like scenarios, ego behaviour and criticality of events

The other classes in this module are handling the different DB types and are derived from BaseFctDB.

**usage in Valf suites**

For validation suites based on `Valf` class there is the operator `DbLinker` setting up all needed connections.

**using several connections in parallel**

If several sub-schemes have to be used in parallel the first connection should be reused.
Please check class `BaseFctDB` for more detail.

**Do not waste the limited number of connections to Oracle DB**
by setting up a new connection for each sub-scheme,
always use the existing one as described in `BaseFctDB`.



:org:           Continental AG
:author:        Sohaib Zafar

:version:       $Revision: 1.9 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 12:26:27CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from warnings import warn

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.db.db_common import BaseDB, DB_FUNC_NAME_LOWER, DB_FUNC_NAME_UPPER, AdasDBError, PluginBaseDB
from stk.db.db_sql import GenericSQLStatementFactory, SQLBinaryExpr, SQLFuncExpr, OP_EQ, OP_NEQ, SQLLiteral, OP_AND, \
    OP_LEQ, OP_GEQ, OP_AS
from stk.valf.signal_defs import DBFCT

# ===============================================================================
# Constants
# ===============================================================================
# Table base names:
TABLE_NAME_CRITICALITY = "FCT_CRITICALITY"
TABLE_NAME_EGOBEHAVIOUR = "FCT_EGOBEHAVIOUR"
TABLE_NAME_SCENARIO = "FCT_SCENARIO"
TABLE_NAME_ENVIRONMENT = "FCT_ENVIRONMENT"
TABLE_NAME_ENVIRONMENT_TYPE = "FCT_ENVIRONMENT_TYPE"

# Criticality Table
COL_NAME_CRITICALITY_CID = "CID"
COL_NAME_CRITICALITY_NAME = "NAME"
COL_NAME_CRITICALITY_DESC = "DESCRIPTION"

# EgoBehaviour Table
COL_NAME_EGOBEHAVIOUR_EBID = "EBID"
COL_NAME_EGOBEHAVIOUR_NAME = "NAME"
COL_NAME_EGOBEHAVIOUR_DESC = "DESCRIPTION"

# Environment Table
COL_NAME_ENVIRONMENT_ENVID = "ENVID"
COL_NAME_ENVIRONMENT_NAME = "NAME"
COL_NAME_ENVIRONMENT_ENVTYPEID = "ENVTYPEID"
COL_NAME_ENVIRONMENT_DESC = "DESCRIPTION"

# Environment Type Table
COL_NAME_ENVIRONMENT_TYPE_ENVTYPEID = "ENVTYPEID"
COL_NAME_ENVIRONMENT_TYPE_NAME = "NAME"
COL_NAME_ENVIRONMENT_TYPE_DESC = "DESCRIPTION"

# Scenario Table
COL_NAME_SCENARIO_SCENARIOID = "SCENARIOID"
COL_NAME_SCENARIO_MEASID = "MEASID"
COL_NAME_SCENARIO_STARTABSTS = "STARTABSTS"
COL_NAME_SCENARIO_ENDABSTS = "ENDABSTS"
COL_NAME_SCENARIO_LBLCOMMENT = "LBLCOMMENT"
COL_NAME_SCENARIO_ENV_INFRASTRUCTURE = "ENV_INFRASTRUCTURE"
COL_NAME_SCENARIO_ENV_LIGHT_CONDITION = "ENV_LIGHT_CONDITION"
COL_NAME_SCENARIO_ENV_WEATHER_CONDITION = "ENV_WEATHER_CONDITION"
COL_NAME_SCENARIO_ENV_DATAINTEGRITY = "ENV_DATAINTEGRITY"
COL_NAME_SCENARIO_LABELER_CRITICALITY = "LABELER_CRITICALITY"
COL_NAME_SCENARIO_VEHICLE_CRITICALITY = "VEHICLE_CRITICALITY"
COL_NAME_SCENARIO_DRIVER_CRITICALITY = "DRIVER_CRITICALITY"
COL_NAME_SCENARIO_LBLSTATEID = "LBLSTATEID"
COL_NAME_SCENARIO_LBLBY = "LBLBY"
COL_NAME_SCENARIO_LBLTIME = "LBLTIME"
COL_NAME_SCENARIO_PID = "PID"
COL_NAME_SCENARIO_RECTOBJID = "RECTOBJID"
COL_NAME_SCENARIO_EGO_BEHAVIOR = "EGO_BEHAVIOR"
COL_NAME_SCENARIO_REL_EGO_BEHAVIOR = "REL_EGO_BEHAVIOR"
COL_NAME_SCENARIO_OBJ_DYNAMIC = "OBJ_DYNAMIC"
COL_NAME_SCENARIO_OBJ_TYPE = "OBJ_TYPE"
COL_NAME_SCENARIO_OBJ_BEHAVIOR = "OBJ_BEHAVIOR"
COL_NAME_SCENARIO_EVASION_RIGHT = "EVASION_RIGHT"
COL_NAME_SCENARIO_EVASION_LEFT = "EVASION_LEFT"

FCT_ACTIVE_VERSION = 2

IDENT_STRING = DBFCT

# ===============================================================================
# Constraint DB Libary Base Implementation
# ===============================================================================


# - classes -----------------------------------------------------------------------------------------------------------
class BaseFctDB(BaseDB):
    """**Base implementation of the Function Database**

    For the first connection to the DB for fct tables just create a new instance of this class like

    .. python::

        from stk.db.fct import BaseFctDB

        dbfct = BaseFctDB("MFC4XX")   # or use "ARS4XX", "VGA" or path/name of sqlite file

    If already some connection to another table of the DB is created use that one to speed up your code:

    .. python::

        dbfct = BaseFctDB(dbxxx.db_connection)

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
        Initialize function database

        :keyword db_connection: The database connection to be used
        :type db_connection: cx_oracle.Connection, pydodbc.Connection, sqlite3.Connection, sqlce.Connection
        :keyword table_prefix: The table name prefix which is usually master schema name
        :type table_prefix: String
        """
        kwargs['strIdent'] = DBFCT
        self.__last_measid = None
        self.__no_scenario_last_measid = False

        BaseDB.__init__(self, *args, **kwargs)

        if self.sub_scheme_version < FCT_ACTIVE_VERSION:
            self._log.warning("please update your DB, minimum FCT version %d is needed, your version is %d."
                              % (FCT_ACTIVE_VERSION, self.sub_scheme_version))

    def get_column_names(self, table_name):
        """deprecated"""
        msg = 'Method "GetColumnNames" is deprecated use "get_columns" instead'
        warn(msg, stacklevel=2)
        return self.get_columns(table_name)

    def GetColumnNames(self, table_name):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetColumnNames" is deprecated use "get_columns" instead'
        warn(msg, stacklevel=2)
        return self.get_columns(table_name)

    # ====================================================================
    # Handling of Criticality
    # ====================================================================
    def add_criticality(self, criticality):
        """
        Add criticality state to database

        :param criticality: The criticality record.
        :type criticality: Dict
        :return: Returns the criticality ID.
        :rtype: Integer
        """
        entries = self.get_criticality(criticality[COL_NAME_CRITICALITY_NAME].upper())
        if len(entries) <= 0:
            criticality[COL_NAME_CRITICALITY_NAME] = criticality[COL_NAME_CRITICALITY_NAME].upper()
            self.add_generic_data(criticality, TABLE_NAME_CRITICALITY)
        else:
            tmp = "Criticality name '%s' " % (criticality[COL_NAME_CRITICALITY_NAME])
            tmp += "already exists in the database."
            raise AdasDBError(tmp)
        cid = self.get_criticality_id(criticality[COL_NAME_CRITICALITY_NAME].upper())
        return cid

    def AddCriticality(self, criticality):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "AddCriticality" is deprecated use '
        msg += '"add_criticality" instead'
        warn(msg, stacklevel=2)
        return self.add_criticality(criticality)

    def update_criticality(self, criticality, where=None):
        """
        Update existing criticality records.

        :param criticality: The criticality record update.
        :type criticality: Dict
        :param where: The condition to be fulfilled by the criticality to the updated, by default based on ID.
        :type where: SQLBinaryExpression
        :return: Returns the number of affected criticality.
        :rtype: Integer
        """
        rowcount = 0
        if where is None:
            where = SQLBinaryExpr(COL_NAME_CRITICALITY_CID, OP_EQ, criticality[COL_NAME_CRITICALITY_CID])
        if (criticality is not None) and (len(criticality) != 0):
            rowcount = self.update_generic_data(criticality, TABLE_NAME_CRITICALITY, where)
        return rowcount

    def UpdateCriticality(self, criticality, where=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "UpdateCriticality" is deprecated use '
        msg += '"update_criticality" instead'
        warn(msg, stacklevel=2)
        return self.update_criticality(criticality, where)

    def delete_criticality(self, criticality):
        """
        Delete existing criticality records.

        :param criticality: The criticality record update.
        :type criticality: Dict
        :return: Returns the number of affected criticality.
        :rtype: Integer
        """
        rowcount = 0
        if (criticality is not None) and (len(criticality) != 0):
            cond = self.__get_criticality_condition(criticality[COL_NAME_CRITICALITY_NAME].upper())
            rowcount = self.delete_generic_data(TABLE_NAME_CRITICALITY, where=cond)
        return rowcount

    def DeleteCriticality(self, criticality):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "DeleteCriticality" is deprecated use '
        msg += '"delete_criticality" instead'
        warn(msg, stacklevel=2)
        return self.delete_criticality(criticality)

    def get_criticality(self, name):
        """
        Get existing criticality records.

        :param name: The criticality name.
        :type name: String
        :return: Returns the criticality record.
        :rtype: dict
        """
        record = {}
        cond = self.__get_criticality_condition(name)
        entries = self.select_generic_data(table_list=[TABLE_NAME_CRITICALITY], where=cond)
        if len(entries) <= 0:
            self._log.info(str("Criticality with name '%s' does not exists in the FCT  database." % name))
        elif len(entries) > 1:
            self._log.warning(str("Criticality with name '%s' cannot be resolved because it is ambiguous." % name))
            record = entries
        else:
            record = entries[0]
        return record

    def GetCriticality(self, name):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetCriticality" is deprecated use '
        msg += '"get_criticality" instead'
        warn(msg, stacklevel=2)
        return self.get_criticality(name)

    def get_criticality_name(self, cid):
        """
        Get criticality name.

        :param cid: The criticality ID.
        :type cid: Integer
        :return: Returns the criticality name.
        :rtype: String
        """
        record = {}
        cond = SQLBinaryExpr(COL_NAME_CRITICALITY_CID, OP_EQ, cid)
        entries = self.select_generic_data(table_list=[TABLE_NAME_CRITICALITY], where=cond)
        if len(entries) <= 0:
            self._log.info(str("Criticality with cid '%s' does not exists in the FCT  database." % cid))
        elif len(entries) > 1:
            self._log.warning(str("Criticality with cid '%s' cannot be resolved because it is ambiguous." % cid))
            record = entries
        else:
            record = entries[0]
        return record[COL_NAME_CRITICALITY_NAME]

    def GetCriticalityName(self, cid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetCriticalityName" is deprecated use '
        msg += '"get_criticality_name" instead'
        warn(msg, stacklevel=2)
        return self.get_criticality_name(cid)

    def get_criticality_id(self, name):
        """
        Get existing criticality records.

        :param name: The criticality name.
        :type name: String
        :return: Returns the criticality ID.
        :rtype: Integer
        """
        record = self.get_criticality(name)
        if COL_NAME_CRITICALITY_CID in record:
            return record[COL_NAME_CRITICALITY_CID]
        else:
            return None

    def __get_criticality_condition(self, name):
        """
        Get the condition expression to access the criticality.

        :param name: Name of the criticality
        :type name: String
        :return: Returns the condition expression
        :rtype: SQLBinaryExpression
        """
        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_UPPER],
                             COL_NAME_CRITICALITY_NAME), OP_EQ, SQLLiteral(name.upper()))
        return cond

    # ====================================================================
    # Handling of Ego Behaviour
    # ====================================================================
    def add_ego_behaviour(self, egobehaviour):
        """
        Add egobehaviour state to database.

        :param egobehaviour: The egobehaviour record.
        :type egobehaviour: Dict
        :return: Returns the egobehaviour ID.
        :rtype: Integer
        """
        entries = self.get_ego_behaviour(egobehaviour[COL_NAME_EGOBEHAVIOUR_NAME].lower())
        if len(entries) <= 0:
            egobehaviour[COL_NAME_EGOBEHAVIOUR_NAME] = egobehaviour[COL_NAME_EGOBEHAVIOUR_NAME].lower()
            self.add_generic_data(egobehaviour, TABLE_NAME_EGOBEHAVIOUR)
        else:
            tmp = "Ego Behaviour name '%s' " % (egobehaviour[COL_NAME_EGOBEHAVIOUR_NAME])
            tmp += "already exists in the database. "
            raise AdasDBError(tmp)
        ebid = self.get_ego_behaviour_id(egobehaviour[COL_NAME_CRITICALITY_NAME].lower())
        return ebid

    def AddEgoBehaviour(self, EgoBehaviour):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "AddEgoBehaviour" is deprecated use '
        msg += '"add_ego_behaviour" instead'
        warn(msg, stacklevel=2)
        return self.add_ego_behaviour(EgoBehaviour)

    def update_ego_behaviour(self, egobehaviour, where=None):
        """
        Update existing egobehaviour records.

        :param egobehaviour: The egobehaviour record update.
        :type egobehaviour: Dict
        :param where: The condition to be fulfilled by the egobehaviour to the updated, by default based on ID.
        :type where: SQLBinaryExpression
        :return: Returns the number of affected egobehaviour.
        :rtype: Integer
        """
        rowcount = 0
        if where is None:
            where = SQLBinaryExpr(COL_NAME_EGOBEHAVIOUR_EBID, OP_EQ, egobehaviour[COL_NAME_EGOBEHAVIOUR_EBID])
        if (egobehaviour is not None) and (len(egobehaviour) != 0):
            rowcount = self.update_generic_data(egobehaviour, TABLE_NAME_EGOBEHAVIOUR, where)
        return rowcount

    def UpdateEgoBehaviour(self, egobehaviour, where=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "UpdateEgoBehaviour" is deprecated use '
        msg += '"update_ego_behaviour" instead'
        warn(msg, stacklevel=2)
        return self.update_ego_behaviour(egobehaviour, where)

    def delete_ego_behaviour(self, egobehaviour):
        """
        Delete existing egobehaviour records.

        :param egobehaviour: The egobehaviour record update.
        :type egobehaviour: dict
        :return: Returns the number of affected egobehaviour.
        :rtype: int
        """
        rowcount = 0
        if (egobehaviour is not None) and (len(egobehaviour) != 0):
            cond = self.__get_ego_behaviour_condition(egobehaviour[COL_NAME_EGOBEHAVIOUR_NAME])
            rowcount = self.delete_generic_data(TABLE_NAME_EGOBEHAVIOUR, where=cond)
        return rowcount

    def DeleteEgoBehaviour(self, EgoBehaviour):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "DeleteEgoBehaviour" is deprecated use '
        msg += '"delete_ego_behaviour" instead'
        warn(msg, stacklevel=2)
        return self.delete_ego_behaviour(EgoBehaviour)

    def get_ego_behaviour(self, name):
        """
        Get existing EgoBehaviour records.

        :param name: The EgoBehaviour name.
        :type name: String
        :return: Returns the EgoBehaviour record.
        :rtype: Dict
        """
        record = {}
        cond = self.__get_ego_behaviour_condition(name)
        entries = self.select_generic_data(table_list=[TABLE_NAME_EGOBEHAVIOUR], where=cond)
        if len(entries) <= 0:
            self._log.info(str("EgoBehaviour with name '%s' does not exists in the FCT  database." % name))
        elif len(entries) > 1:
            self._log.warning(str("EgoBehaviour with name '%s' cannot be resolved because it is ambiguous. (%s)"
                                  % (name, entries)))
            record = entries
        else:
            record = entries[0]
        return record

    def GetEgoBehaviour(self, name):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetEgoBehaviour" is deprecated use '
        msg += '"get_ego_behaviour" instead'
        warn(msg, stacklevel=2)
        return self.get_ego_behaviour(name)

    def get_ego_behavior_names(self):
        """
        Get all existing EgoBehaviour names.

        :return: Returns the EgoBehaviour record names.
        :rtype: list
        """
        record_name = []
        entries = self.select_generic_data(table_list=[TABLE_NAME_EGOBEHAVIOUR])
        if len(entries) <= 0:
            self._log.warning(str("EgoBehaviours do not exist in the FCT  database."))
        else:
            for i in range(0, len(entries)):
                record_name.append(entries[i][COL_NAME_EGOBEHAVIOUR_NAME])
        return record_name

    def GetEgoBehaviorNames(self):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetEgoBehaviorNames" is deprecated use '
        msg += '"get_ego_behavior_names" instead'
        warn(msg, stacklevel=2)
        return self.get_ego_behavior_names()

    def get_ego_behaviour_id(self, name):
        """
        Get existing EgoBehaviour records.

        :param name: The EgoBehaviour name.
        :type name: String
        :return: Returns the EgoBehaviour ID.
        :rtype: Integer
        """
        record = self.get_ego_behaviour(name)
        if COL_NAME_EGOBEHAVIOUR_EBID in record:
            return record[COL_NAME_EGOBEHAVIOUR_EBID]
        else:
            return None

    def GetEgoBehaviourID(self, name):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetEgoBehaviourID" is deprecated use '
        msg += '"get_ego_behaviour_id" instead'
        warn(msg, stacklevel=2)
        return self.get_ego_behaviour_id(name)

    def __get_ego_behaviour_condition(self, name):
        """
        Get the condition expression to access the EgoBehaviour.

        :param name: Name of the EgoBehaviour
        :type name: Sring
        :return: Returns the condition expression
        :rtype: SQLBinaryExpression
        """
        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                             COL_NAME_CRITICALITY_NAME), OP_EQ, SQLLiteral(name.lower()))
        return cond

    # ====================================================================
    # Handling of Environment
    # ====================================================================
    def get_environment(self, envid):
        """
        Get existing Environment names based on Environment Identifier.

        :param envid: The Environment Identifier.
        :type envid: Integer
        :return: Returns the Environment record related to an environment id.
        :rtype: Dict
        """
        record = None
        cond = SQLBinaryExpr(COL_NAME_ENVIRONMENT_ENVID, OP_EQ, envid)
        entries = self.select_generic_data(table_list=[TABLE_NAME_ENVIRONMENT], where=cond)
        if len(entries) <= 0:
            self._log.warning(str("Environment with id '%s' does not exists in the FCT database." % envid))
        elif len(entries) > 1:
            self._log.warning(str("Environment with id '%s' cannot be resolved because it is ambiguous." % envid))
        else:
            record = entries[0]
        return record

    def get_environment_names_for_type(self, envtypeid):
        """
        Get existing Environment names based on Environment Type Identifier.

        :param envtypeid: The Environment Type Identifier.
        :type envtypeid: Integer
        :return: Returns the Environment names related to an environment type.
        :rtype: list
        """
        record_name = []
        cond = SQLBinaryExpr(COL_NAME_ENVIRONMENT_ENVTYPEID, OP_EQ, envtypeid)
        entries = self.select_generic_data(select_list=[COL_NAME_ENVIRONMENT_NAME],
                                           table_list=[TABLE_NAME_ENVIRONMENT], where=cond)
        if len(entries) <= 0:
            self._log.warning(str("Environment with type id '%s' does not exists in the FCT  database." % envtypeid))
        else:
            for i in range(0, len(entries)):
                record_name.append(entries[i][COL_NAME_ENVIRONMENT_NAME])
        return record_name

    def GetEnvironmentNamesforType(self, envtypeid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetEnvironmentNamesforType" is deprecated use '
        msg += '"get_environment_names_for_type" instead'
        warn(msg, stacklevel=2)
        return self.get_environment_names_for_type(envtypeid)

    def get_enabled_environment_names_for_type(self, envtypeid, disable=None):  # pylint: disable=C0103
        """
        Get existing not disabled Environment names based on Environment Type Identifier.

        :param envtypeid: The Environment Type Identifier.
        :type envtypeid: Integer
        :param disable: The disable key (For e.g '0')
        :type disable: Integer
        :return: Returns the Environment names related to an environment type which are not disabled.
        :rtype: list
        """
        record_name = []
        cond = SQLBinaryExpr(COL_NAME_ENVIRONMENT_ENVTYPEID, OP_EQ, envtypeid)
        entries = self.select_generic_data(select_list=[COL_NAME_ENVIRONMENT_NAME, COL_NAME_ENVIRONMENT_DESC],
                                           table_list=[TABLE_NAME_ENVIRONMENT], where=cond)
        if len(entries) <= 0:
            self._log.warning(str("Environment with type id '%s' does not exists in the FCT  database." % envtypeid))
        else:
            for i in range(0, len(entries)):
                if entries[i][COL_NAME_ENVIRONMENT_DESC] is None:
                    record_name.append(entries[i][COL_NAME_ENVIRONMENT_NAME])
                elif entries[i][COL_NAME_ENVIRONMENT_DESC][0] != disable:
                    record_name.append(entries[i][COL_NAME_ENVIRONMENT_NAME])
                else:
                    pass
        return record_name

    def GetEnabledEnvironmentNamesforType(self, envtypeid, disable=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetEnabledEnvironmentNamesforType" is deprecated use '
        msg += '"get_enabled_environment_names_for_type" instead'
        warn(msg, stacklevel=2)
        return self.get_enabled_environment_names_for_type(envtypeid, disable)

    def get_environment_name(self, envid):
        """
        Get existing Environment name based on Environment Identifier.

        :param envid: The Environment Identifier.
        :type envid: Integer
        :return: Returns the Environment names related to an environment identifier.
        :rtype: String
        """
        cond = SQLBinaryExpr(COL_NAME_ENVIRONMENT_ENVID, OP_EQ, envid)
        entries = self.select_generic_data(select_list=[COL_NAME_ENVIRONMENT_NAME],
                                           table_list=[TABLE_NAME_ENVIRONMENT], where=cond)
        if len(entries) <= 0:
            self._log.warning(str("Environment with id '%s' does not exists in the FCT  database." % envid))
        elif len(entries) > 1:
            self._log.warning(str("Environment with id '%s' cannot be resolved because it is ambiguous." % envid))
        else:
            return entries[0][COL_NAME_ENVIRONMENT_NAME]

    def GetEnvironmentName(self, envid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetEnvironmentName" is deprecated use '
        msg += '"get_environment_name" instead'
        warn(msg, stacklevel=2)
        return self.get_environment_name(envid)

    def get_environment_id(self, name, envtypeid):
        """
        Get existing Environment ID based on Environment Type Identifier.

        :param name: The Environment name.
        :type name: String
        :param envtypeid: Environment Type ID
        :type envtypeid: Integer
        :return: Returns the Environment ID.
        :rtype: Integer
        """
        cond1 = self.__get_environment_condition(name)
        cond2 = SQLBinaryExpr(COL_NAME_ENVIRONMENT_ENVTYPEID, OP_EQ, envtypeid)
        cond = SQLBinaryExpr(cond1, OP_AND, cond2)
        entries = self.select_generic_data(table_list=[TABLE_NAME_ENVIRONMENT], where=cond)
        if len(entries) <= 0:
            self._log.warning(str("Environment with name '%s' does not exists in the FCT  database." % name))
        elif len(entries) > 1:
            self._log.warning(str("Environment with name '%s' cannot be resolved because it is ambiguous." % name))
        else:
            record_id = entries[0][COL_NAME_ENVIRONMENT_ENVID]
            return record_id

    def GetEnvironmentID(self, name, envtypeid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetEnvironmentID" is deprecated use '
        msg += '"get_environment_id" instead'
        warn(msg, stacklevel=2)
        return self.get_environment_id(name, envtypeid)

    def __get_environment_condition(self, name):
        """
        Get the condition expression to access the Environment.

        :param name: Name of the Environment
        :type name: String
        :return: Returns the condition expression
        :rtype: SQLBinaryExpression
        """
        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                             COL_NAME_ENVIRONMENT_NAME), OP_EQ, SQLLiteral(name.lower()))
        return cond

    # ====================================================================
    # Handling of Scenario
    # ====================================================================
    def add_scenario(self, scenario):
        """
        Add Scenario record to database.

        :param scenario: The Scenario record.
        :type scenario: Dict
        :return: Returns the Scenario ID.
        :rtype: Integer
        """
        if scenario[COL_NAME_SCENARIO_STARTABSTS] >= scenario[COL_NAME_SCENARIO_ENDABSTS]:
            tmp = "(TimeIntegrityError) Scenario Begin Timestamp is not less than the Scenario End timestamp."
            raise AdasDBError(tmp)
        cond = self._get_scenario_condition(scenario[COL_NAME_SCENARIO_MEASID])
        entries = self.select_generic_data(table_list=[TABLE_NAME_SCENARIO], where=cond)
        if len(entries) <= 0:
            self.add_generic_data(scenario, TABLE_NAME_SCENARIO)
        else:
            tmp = "Measurement '%s' exists already in the generic label database" % scenario[COL_NAME_SCENARIO_MEASID]
            self._log.info(tmp)
            overlap = self._check_overlap(scenario, entries)
            if overlap is 0:
                self.add_generic_data(scenario, TABLE_NAME_SCENARIO)
            else:
                # tmp = "'%s' " % (scenario)
                tmp = "Scenario cannot be added to generic label database because the time range is overlapping "
                tmp += "with %s existing Scenario(s)." % overlap
                self._log.warning(tmp)
                return -overlap
        scenario_id = self.__get_scenario_id(scenario)
        return scenario_id

    def AddScenario(self, scenario):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "AddScenario" is deprecated use '
        msg += '"add_scenario" instead'
        warn(msg, stacklevel=2)
        return self.add_scenario(scenario)

    @staticmethod
    def _check_overlap(scenario, entries):
        """
        Checking the time overlap of new and existing scenario in the label database related to same measurement

        :param scenario: New scenario record
        :type scenario: Dict
        :param entries: Existing scenario record
        :type entries: Dict
        :return: Returns the number of existing scenarios affected by the new Scenario
        :rtype: Integer
        """
        overlap = 0
        for i in range(0, len(entries)):
            if scenario[COL_NAME_SCENARIO_MEASID] == entries[i][COL_NAME_SCENARIO_MEASID]:
                if ((scenario[COL_NAME_SCENARIO_STARTABSTS] >= entries[i][COL_NAME_SCENARIO_STARTABSTS] and
                     scenario[COL_NAME_SCENARIO_STARTABSTS] <= entries[i][COL_NAME_SCENARIO_ENDABSTS])
                    or (scenario[COL_NAME_SCENARIO_ENDABSTS] >= entries[i][COL_NAME_SCENARIO_STARTABSTS] and
                        scenario[COL_NAME_SCENARIO_ENDABSTS] <= entries[i][COL_NAME_SCENARIO_ENDABSTS])
                    or (entries[i][COL_NAME_SCENARIO_STARTABSTS] >= scenario[COL_NAME_SCENARIO_STARTABSTS] and
                        entries[i][COL_NAME_SCENARIO_STARTABSTS] <= scenario[COL_NAME_SCENARIO_ENDABSTS])
                    or (entries[i][COL_NAME_SCENARIO_ENDABSTS] >= scenario[COL_NAME_SCENARIO_STARTABSTS] and
                        entries[i][COL_NAME_SCENARIO_ENDABSTS] <= scenario[COL_NAME_SCENARIO_ENDABSTS])):
                    overlap += 1
                else:
                    pass
            else:
                tmp = "\n The check for overlap doesn't deal with the same measurement."
                raise AdasDBError(tmp)
        return overlap

    def update_scenario(self, scenario, where=None, updated_start=None, updated_end=None):
        """
        Update existing Scenario records.

        :param scenario: The Scenario record to be updated.
        :type scenario: Dict
        :param where: Special condition for selecting the scenario
        :type where: SQLBinaryExpression
        :param updated_start: Updated Scenario Start Timestamp
        :type updated_start: Integer
        :param updated_end: Updated Scenario End Timestamp
        :type updated_end: Integer
        :return: Returns the number of affected Scenario.
        :rtype: Integer
        """
        rowcount = 0
        cond1 = self._get_scenario_condition(scenario[COL_NAME_SCENARIO_MEASID])
        cond2 = SQLBinaryExpr(COL_NAME_SCENARIO_SCENARIOID, OP_NEQ, self.__get_scenario_id(scenario))
        cond = SQLBinaryExpr(cond1, OP_AND, cond2)
        entries = self.select_generic_data(table_list=[TABLE_NAME_SCENARIO], where=cond)
        if where is None:
            where = self._get_scenario_condition(scenario[COL_NAME_SCENARIO_MEASID],
                                                 scenario[COL_NAME_SCENARIO_STARTABSTS],
                                                 scenario[COL_NAME_SCENARIO_ENDABSTS])
        if updated_start is not None:
            scenario[COL_NAME_SCENARIO_STARTABSTS] = updated_start
        if updated_end is not None:
            scenario[COL_NAME_SCENARIO_ENDABSTS] = updated_end
        if scenario[COL_NAME_SCENARIO_STARTABSTS] >= scenario[COL_NAME_SCENARIO_ENDABSTS]:
            tmp = "(TimeIntegrityError) Scenario Begin Timestamp is not less than the Scenario End timestamp. \
                %d >= %d" % (scenario[COL_NAME_SCENARIO_STARTABSTS], scenario[COL_NAME_SCENARIO_ENDABSTS])
            raise AdasDBError(tmp)
        if (scenario is not None) and (len(scenario) != 0):
            overlap = self._check_overlap(scenario, entries)
            if overlap is 0:
                rowcount = self.update_generic_data(scenario, TABLE_NAME_SCENARIO, where)
            else:
                # tmp = "'%s' " % (scenario)
                tmp = "Scenario cannot be added to generic label database because the time range is overlapping "
                tmp += "with %s other existing Scenario(s)." % overlap
                raise AdasDBError(tmp)
        return rowcount

    def UpdateScenario(self, scenario, where=None, updated_start=None, updated_end=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "UpdateScenario" is deprecated use '
        msg += '"update_scenario" instead'
        warn(msg, stacklevel=2)
        return self.update_scenario(scenario, where, updated_start, updated_end)

    def delete_scenario(self, scenario):
        """
        Delete existing Scenario record.

        :param scenario: The Scenario record to be deleted.
        :type scenario: Dict
        :return: Returns the number of affected Scenario.
        :rtype: Integer
        """
        rowcount = 0
        if (scenario is not None) and (len(scenario) != 0):
            if COL_NAME_SCENARIO_SCENARIOID in scenario and \
                    (scenario[COL_NAME_SCENARIO_SCENARIOID] is not None):
                cond = SQLBinaryExpr(COL_NAME_SCENARIO_SCENARIOID, OP_EQ, scenario[COL_NAME_SCENARIO_SCENARIOID])
            else:
                cond = self._get_scenario_condition(scenario[COL_NAME_SCENARIO_MEASID],
                                                    scenario[COL_NAME_SCENARIO_STARTABSTS],
                                                    scenario[COL_NAME_SCENARIO_ENDABSTS])
            rowcount = self.delete_generic_data(TABLE_NAME_SCENARIO, where=cond)
        return rowcount

    def DeleteScenario(self, scenario):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "DeleteScenario" is deprecated use '
        msg += '"delete_scenario" instead'
        warn(msg, stacklevel=2)
        return self.delete_scenario(scenario)

    def get_scenario(self, meas_id, start=None, end=None):
        """
        Get the Scenario record based on measurement idetifier and/or start and end scenario timestamps.

        :param meas_id: The measurement id.
        :type meas_id: Integer
        :param start: The Scenario Start Timestamp.
        :type start: Integer
        :param end: The Scenario End Timestamp.
        :type end: Integer
        :return: Returns the Scenario record.
        :rtype: Dict
        """
        record = {}
        if start is None or end is None:
            cond = self._get_scenario_condition(meas_id)
        else:
            cond = self._get_scenario_condition(meas_id, start, end)

        entries = self.select_generic_data(table_list=[TABLE_NAME_SCENARIO], where=cond)
        if len(entries) <= 0:
            self._log.warning(str("Scenario with measurement id '%s' does not exists in the FCT  database." % meas_id))
        elif len(entries) > 1:
            self._log.info(str("More than one scenario exists with measurement id '%s'." % meas_id))
            record = entries
        else:
            record = entries[0]
        return record

    def GetScenario(self, meas_id, start=None, end=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetScenario" is deprecated use '
        msg += '"get_scenario" instead'
        warn(msg, stacklevel=2)
        return self.get_scenario(meas_id, start, end)

    @staticmethod
    def _get_scenario_condition(meas_id, start=None, end=None):
        """
        Get the condition expression to access the Scenario.

        :param meas_id: ID of the Measurement
        :type meas_id: Integer
        :param start: Scenario Start Timestamp
        :type start: Integer
        :param end: Scenario End Timestamp
        :type end: Integer
        :return: Returns the condition expression
        :rtype: SQLBinaryExpression
        """
        if start is None or end is None:
            cond = SQLBinaryExpr(COL_NAME_SCENARIO_MEASID, OP_EQ, meas_id)
        else:
            cond1 = SQLBinaryExpr(COL_NAME_SCENARIO_STARTABSTS, OP_EQ, start)
            cond2 = SQLBinaryExpr(COL_NAME_SCENARIO_ENDABSTS, OP_EQ, end)
            cond3 = SQLBinaryExpr(COL_NAME_SCENARIO_MEASID, OP_EQ, meas_id)
            cond_tmp = SQLBinaryExpr(cond1, OP_AND, cond2)
            cond = SQLBinaryExpr(cond_tmp, OP_AND, cond3)
        return cond

    def get_event_scenario(self, meas_id, start, end):
        """
        Get corresponding scenario record from the event.

        :param meas_id: The measurement id.
        :type meas_id: Integer
        :param start: The Event Start Timestamp.
        :type start: Integer
        :param end: The Event End Timestamp.
        :type end: Integer
        :return: Returns the Scenario record.
        :rtype: Dict
        """
        record = {}
#        Cache last recfile scenario if doesnt have any scenario at then dont execute actual and return blank dict
        if meas_id == self.__last_measid:
            if self.__no_scenario_last_measid:
                return record
        else:
            self.__last_measid = meas_id
            cond3 = SQLBinaryExpr(COL_NAME_SCENARIO_MEASID, OP_EQ, meas_id)
            entries = self.select_generic_data(select_list=[SQLBinaryExpr("count(*)", OP_AS, "COUNT")],
                                               table_list=[TABLE_NAME_SCENARIO],
                                               where=cond3)
            self.__no_scenario_last_measid = entries[0]["COUNT"] == 0

        sql_param = {"1": start, "2": end, "3": meas_id}
        cond1 = SQLBinaryExpr(COL_NAME_SCENARIO_STARTABSTS, OP_LEQ, ":1")
        cond2 = SQLBinaryExpr(COL_NAME_SCENARIO_ENDABSTS, OP_GEQ, ":2")
        cond3 = SQLBinaryExpr(COL_NAME_SCENARIO_MEASID, OP_EQ, ":3")
        cond_tmp = SQLBinaryExpr(cond1, OP_AND, cond2)
        cond = SQLBinaryExpr(cond_tmp, OP_AND, cond3)
        entries = self.select_generic_data(table_list=[TABLE_NAME_SCENARIO], where=cond, sqlparams=sql_param)
        if len(entries) <= 0:
            self._log.warning(str("Scenario with meas_id '%s' does not exists in the FCT  database." % meas_id))
        elif len(entries) > 1:
            self._log.warning(str("Scenario with meas_id '%s' cannot be resolved because it is ambiguous." % meas_id))
        else:
            record = entries[0]
        return record

    def GetEventScenario(self, meas_id, start, end):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "GetEventScenario" is deprecated use '
        msg += '"get_event_scenario" instead'
        warn(msg, stacklevel=2)
        return self.get_event_scenario(meas_id, start, end)

    @staticmethod
    def _get_event_scenario_condition(meas_id, start, end):
        """
        Get the condition expression to access the Scenario.

        :param meas_id: ID of the Measurement
        :type meas_id: Integer
        :param start: The Event Start Timestamp.
        :type start: Integer
        :param end: The Event End Timestamp.
        :type end: Integer
        :return: Returns the condition expression
        :rtype: SQLBinaryExpression
        """
        cond1 = SQLBinaryExpr(COL_NAME_SCENARIO_STARTABSTS, OP_LEQ, start)
        cond2 = SQLBinaryExpr(COL_NAME_SCENARIO_ENDABSTS, OP_GEQ, end)
        cond3 = SQLBinaryExpr(COL_NAME_SCENARIO_MEASID, OP_EQ, meas_id)
        cond_tmp = SQLBinaryExpr(cond1, OP_AND, cond2)
        cond = SQLBinaryExpr(cond_tmp, OP_AND, cond3)
        return cond

    def __get_scenario_id(self, scenario):
        """
        Get existing Scenario ID.

        :param scenario: Scenario record
        :type scenario: Dict
        :return: Returns Scenario ID
        :rtype: Integer
        """
        meas_id = scenario[COL_NAME_SCENARIO_MEASID]
        start = scenario[COL_NAME_SCENARIO_STARTABSTS]
        end = scenario[COL_NAME_SCENARIO_ENDABSTS]
        record = self.get_scenario(meas_id, start, end)
        if COL_NAME_SCENARIO_SCENARIOID in record:
            return record[COL_NAME_SCENARIO_SCENARIOID]
        else:
            return None

    def get_all_scenarios(self):
        """
        Get all existing Scenario records.

        :return: Returns all Scenario records from database.
        :rtype: dict
        """
        record = {}
        entries = self.select_generic_data(table_list=[TABLE_NAME_SCENARIO])
        if len(entries) <= 0:
            self._log.warning(str("No Scenario exists in the FCT database."))
        elif len(entries) > 1:
            self._log.info(str("More than one scenario exists."))
            record = entries
        else:
            record = entries[0]
        return record


# ====================================================================
# Constraint DB Libary SQL Server Compact Implementation
# ====================================================================
class PluginFctDB(BaseFctDB, PluginBaseDB):  # pylint: disable=R0904
    """used by plugin finder"""
    def __init__(self, *args, **kwargs):
        """some comment is missing"""
        BaseFctDB.__init__(self, *args, **kwargs)


class SQLCEFctDB(BaseFctDB, PluginBaseDB):  # pylint: disable=R0904
    """SQL Server Compact Edition Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseFctDB.__init__(self, *args, **kwargs)


class OracleFctDB(BaseFctDB, PluginBaseDB):  # pylint: disable=R0904
    """Oracle Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseFctDB.__init__(self, *args, **kwargs)


class SQLite3FctDB(BaseFctDB, PluginBaseDB):  # pylint: disable=R0904
    """Oracle Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseFctDB.__init__(self, *args, **kwargs)


"""
CHANGE LOG:
-----------
$Log: fct.py  $
Revision 1.9 2016/08/16 12:26:27CEST Hospes, Gerd-Joachim (uidv8815) 
update module and class docu
Revision 1.8 2015/11/06 13:38:44CET Mertens, Sven (uidv7805)
pep8 renice
- Added comments -  uidv7805 [Nov 6, 2015 1:38:45 PM CET]
Change Package : 394407:1 http://mks-psad:7002/im/viewissue?selection=394407
Revision 1.7 2015/11/06 13:31:15CET Mertens, Sven (uidv7805)
add version support for FCt plus warning to be easiest for added EVASION... table columns
--- Added comments ---  uidv7805 [Nov 6, 2015 1:31:15 PM CET]
Change Package : 394407:1 http://mks-psad:7002/im/viewissue?selection=394407
Revision 1.6 2015/11/06 11:14:36CET Mertens, Sven (uidv7805)
adding column definitions
--- Added comments ---  uidv7805 [Nov 6, 2015 11:14:36 AM CET]
Change Package : 394407:1 http://mks-psad:7002/im/viewissue?selection=394407
Revision 1.5 2015/07/14 11:31:14CEST Mertens, Sven (uidv7805)
rewinding some changes
--- Added comments ---  uidv7805 [Jul 14, 2015 11:31:15 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.4 2015/07/14 09:29:47CEST Mertens, Sven (uidv7805)
simplify for plugin finder
--- Added comments ---  uidv7805 [Jul 14, 2015 9:29:47 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.3 2015/05/18 14:53:54CEST Ahmed, Zaheer (uidu7634)
variable binding and cahce for get_event_scenario
removed SQLiteral usage from number datatypes
--- Added comments ---  uidu7634 [May 18, 2015 2:53:54 PM CEST]
Change Package : 338368:1 http://mks-psad:7002/im/viewissue?selection=338368
Revision 1.2 2015/04/30 11:09:28CEST Hospes, Gerd-Joachim (uidv8815)
merge last changes
--- Added comments ---  uidv8815 [Apr 30, 2015 11:09:28 AM CEST]
Change Package : 330394:1 http://mks-psad:7002/im/viewissue?selection=330394
Revision 1.1 2015/04/23 19:04:01CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/fct/project.pj
Revision 1.19 2015/04/29 12:19:54CEST Ahmed, Zaheer (uidu7634)
variable binding for get_event_scenario and remove SQL literals over numeric datatype
--- Added comments ---  uidu7634 [Apr 29, 2015 12:19:54 PM CEST]
Change Package : 318797:1 http://mks-psad:7002/im/viewissue?selection=318797
Revision 1.18 2015/04/27 14:36:21CEST Mertens, Sven (uidv7805)
ident string fix
--- Added comments ---  uidv7805 [Apr 27, 2015 2:36:22 PM CEST]
Change Package : 329312:2 http://mks-psad:7002/im/viewissue?selection=329312
Revision 1.17 2015/04/24 12:46:17CEST Mertens, Sven (uidv7805)
using fct import as ident string
--- Added comments ---  uidv7805 [Apr 24, 2015 12:46:18 PM CEST]
Change Package : 331116:2 http://mks-psad:7002/im/viewissue?selection=331116
Revision 1.16 2015/03/09 11:52:16CET Ahmed, Zaheer (uidu7634)
passing error_tolerance as keyword argument
--- Added comments ---  uidu7634 [Mar 9, 2015 11:52:17 AM CET]
Change Package : 314217:1 http://mks-psad:7002/im/viewissue?selection=314217
Revision 1.15 2015/03/05 15:12:05CET Mertens, Sven (uidv7805)
using keyword is better
--- Added comments ---  uidv7805 [Mar 5, 2015 3:12:06 PM CET]
Change Package : 312989:1 http://mks-psad:7002/im/viewissue?selection=312989
Revision 1.14 2015/03/05 09:30:39CET Mertens, Sven (uidv7805)
init argument and logger fix
Revision 1.13 2015/01/12 13:16:34CET Mertens, Sven (uidv7805)
removing deprecated method calls
--- Added comments ---  uidv7805 [Jan 12, 2015 1:16:34 PM CET]
Change Package : 288758:1 http://mks-psad:7002/im/viewissue?selection=288758
Revision 1.12 2014/12/17 14:32:04CET Ellero, Stefano (uidw8660)
Removed all db.obj based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Dec 17, 2014 2:32:05 PM CET]
Change Package : 281278:1 http://mks-psad:7002/im/viewissue?selection=281278
Revision 1.11 2014/10/09 14:34:32CEST Zafar, Sohaib (uidu6396)
Epydoc documentation
--- Added comments ---  uidu6396 [Oct 9, 2014 2:34:32 PM CEST]
Change Package : 245346:1 http://mks-psad:7002/im/viewissue?selection=245346
Revision 1.10 2014/10/09 10:33:24CEST Mertens, Sven (uidv7805)
change column name retrieval
--- Added comments ---  uidv7805 [Oct 9, 2014 10:33:25 AM CEST]
Change Package : 270336:1 http://mks-psad:7002/im/viewissue?selection=270336
Revision 1.9 2014/09/16 11:08:09CEST Zafar, Sohaib (uidu6396)
Delete Scenario bug fix
--- Added comments ---  uidu6396 [Sep 16, 2014 11:08:10 AM CEST]
Change Package : 264021:1 http://mks-psad:7002/im/viewissue?selection=264021
Revision 1.8 2014/08/20 17:39:17CEST Hospes, Gerd-Joachim (uidv8815)
remove non-ascii chars causing 'import cat' in other modules to fail
--- Added comments ---  uidv8815 [Aug 20, 2014 5:39:18 PM CEST]
Change Package : 253112:4 http://mks-psad:7002/im/viewissue?selection=253112
Revision 1.7 2014/08/18 16:03:24CEST Zafar-EXT, Sohaib (uidu6396)
New functions added for FCT Label merging Tool.
get_environment() and get_all_scenarios()
--- Added comments ---  uidu6396 [Aug 18, 2014 4:03:25 PM CEST]
Change Package : 253409:1 http://mks-psad:7002/im/viewissue?selection=253409
Revision 1.6 2014/08/05 09:28:24CEST Hecker, Robert (heckerr)
Moved to new coding convensions.
--- Added comments ---  heckerr [Aug 5, 2014 9:28:24 AM CEST]
Change Package : 253983:1 http://mks-psad:7002/im/viewissue?selection=253983
Revision 1.5 2014/06/24 13:23:14CEST Mertens, Sven (uidv7805)
- removing obvious duplicate methods,
- adding log
--- Added comments ---  uidv7805 [Jun 24, 2014 1:23:14 PM CEST]
Change Package : 243817:1 http://mks-psad:7002/im/viewissue?selection=243817
"""
