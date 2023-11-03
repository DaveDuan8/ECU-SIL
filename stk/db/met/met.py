"""
stk/db/met/met.py
-----------------

Classes for Database access of MET Tables for Meta Data.

Sub-Scheme MET


:org:           Continental AG
:author:        Sohaib Zafar

:version:       $Revision: 1.3 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/02/12 13:55:39CET $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from warnings import warn

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.db.db_common import BaseDB
from stk.db.db_sql import SQLBinaryExpr, OP_EQ, SQLLiteral, OP_AND, \
    SQLColumnExpr, OP_INNER_JOIN, SQLTableExpr, SQLJoinExpr
from stk.valf.signal_defs import DBMET

# ===============================================================================
# Constants
# ===============================================================================
# Table base names:
TABLE_NAME_MET_DATA = "MET_DATA"
TABLE_NAME_MET_TYPES = "MET_TYPES"
TABLE_NAME_MET_STATES = "MET_STATES"

# Meta Data Table
COL_NAME_MET_DATA_MET_ID = "MET_ID"
COL_NAME_MET_DATA_MEASID = "MEASID"
COL_NAME_MET_DATA_ABSTS = "ABSTS"
COL_NAME_MET_DATA_STATEID = "STATEID"
COL_NAME_MET_DATA_VALUE = "VALUE"
COL_NAME_MET_DATA_SECTION_DISTANCE = "SECTION_DISTANCE"

# Meta Types Table
COL_NAME_MET_TYPES_TYPEID = "TYPEID"
COL_NAME_MET_TYPES_NAME = "NAME"
COL_NAME_MET_TYPES_PICK_VALUE = "PICK_VALUE"
COL_NAME_MET_TYPES_DESCRIPTION = "DESCRIPTION"

# Meta States Table
COL_NAME_MET_STATES_STATEID = "STATEID"
COL_NAME_MET_STATES_TYPEID = "TYPEID"
COL_NAME_MET_STATES_NAME = "NAME"
COL_NAME_MET_STATES_DESCRIPTION = "DESCRIPTION"

MET_ACTIVE_VERSION = 1

IDENT_STRING = DBMET

# ===============================================================================
# Constraint DB Libary Base Implementation
# ===============================================================================


# - classes ----------------------------------------------------------------------------------------------------------
class BaseMetDB(BaseDB):  # pylint: disable=R0904
    """Base implementation of the Rec File Database"""
    # ====================================================================
    # Constraint DB Libary Interface for public use
    # ====================================================================

    # ====================================================================
    # Handling of database
    # ====================================================================

    def __init__(self, *args, **kwargs):
        """
        Initialize constraint database

        :keyword db_connection: The database connection to be used
        :type db_connection: cx_oracle.Connection, pydodbc.Connection, sqlite3.Connection, sqlce.Connection
        :keyword table_prefix: The table name prefix which is usually master schema name
        :type table_prefix: String
        :keyword sql_factory: SQL Query building factory
        :type sql_factory: GenericSQLStatementFactory
        :keyword error_tolerance: Error tolerance level based on which some error are acceptable
        :type error_tolerance: Integer
        """
        kwargs['strIdent'] = DBMET
        self.__last_measid = None
        self.__no_scenario_last_measid = False

        BaseDB.__init__(self, *args, **kwargs)
        """
        if self.sub_scheme_version < MET_ACTIVE_VERSION:
            self._log.warning("please update your DB, minimum MET version %d is needed, your version is %d."
                              % (MET_ACTIVE_VERSION, self.sub_scheme_version))
        """
    def get_column_names(self, table_name):
        """deprecated"""
        msg = 'Method "GetColumnNames" is deprecated use "get_columns" instead'
        warn(msg, stacklevel=2)
        return self.get_columns(table_name)

    # ====================================================================
    # Handling of Meta Data
    # ====================================================================
    def add_meta_data(self, meta_data, update=False):
        """
        Add Meta Data record to database.

        :param meta_data: The meta_data record.
        :type meta_data: Dict
        :return: Returns the meta_data ID.
        :rtype: Integer
        """
        cond = self._get_meta_data_condition(meta_data)
        entries = self.select_generic_data(table_list=[TABLE_NAME_MET_DATA], where=cond)
        if len(entries) <= 0:
            self.add_generic_data(meta_data, TABLE_NAME_MET_DATA)
        elif len(entries) == 1 and update is True:
            self.update_generic_data(meta_data, TABLE_NAME_MET_DATA, where=cond)
            tmp2 = "Updated Meta Data for State '%s' and MeasID '%s' exists already in the database" \
                % (meta_data[COL_NAME_MET_DATA_STATEID], meta_data[COL_NAME_MET_DATA_MEASID])
            self._log.info(tmp2)
        else:
            tmp = "Meta Data for State '%s' and MeasID '%s' exists already in the database" \
                  % (meta_data[COL_NAME_MET_DATA_STATEID], meta_data[COL_NAME_MET_DATA_MEASID])
            self._log.info(tmp)
        met_id = self.__get_meta_data_id(meta_data)
        return met_id

    def add_meta_data_compact(self, meta_data_records):
        """
        Add Meta Data record to database.

        :param meta_data_records: The meta_data record.
        :type meta_data_records: Dict
        :return: Returns the meta_data ID.
        :rtype: Integer
        """
        self.add_generic_compact_prepared([COL_NAME_MET_DATA_MEASID, COL_NAME_MET_DATA_ABSTS,
                                           COL_NAME_MET_DATA_STATEID, COL_NAME_MET_DATA_VALUE,
                                           COL_NAME_MET_DATA_SECTION_DISTANCE], meta_data_records, TABLE_NAME_MET_DATA)

    def get_meta_data(self, meta_data):
        """
        Get the Meta Data record..

        :param meta_data: The meta_data record.
        :type meta_data: Dict
        :return: Returns the Meta Data record.
        :rtype: Dict
        """
        record = {}
        cond = self._get_meta_data_condition(meta_data)
        entries = self.select_generic_data(table_list=[TABLE_NAME_MET_DATA], where=cond)
        if len(entries) <= 0:
            self._log.warning(str("Meta data '%s' does not exists in the MET  database." % meta_data))
        elif len(entries) > 1:
            self._log.info(str("More than one such meta data exists '%s'." % meta_data))
            record = entries
        else:
            record = entries[0]
        return record

    def __get_meta_data_id(self, meta_data):
        """
        Get existing Meta Data ID.

        :param meta_data: The meta_data record.
        :type meta_data: Dict
        :return: Returns Meta Data ID
        :rtype: Integer
        """
        cond = self._get_meta_data_condition(meta_data)
        entries = self.select_generic_data(table_list=[TABLE_NAME_MET_DATA], where=cond)
        if len(entries) <= 0:
            self._log.warning(str("Meta data name does not exists in the META_  database."))
        elif len(entries) > 1:
            self._log.warning(str("Meta data with name cannot be resolved because it is ambiguous."))
        else:
            record_id = entries[0][COL_NAME_MET_DATA_MET_ID]
            return record_id

    def _get_meta_data_condition(self, meta_data):
        """
        Get the condition expression to access the meta data.

        :param meta_data: The meta_data record.
        :type meta_data: Dict
        :return: Returns the condition expression
        :rtype: SQLBinaryExpression
        """
        pick_val = self._get_pickvalue_from_stateid(meta_data[COL_NAME_MET_DATA_STATEID])
        if pick_val == 0 and COL_NAME_MET_DATA_ABSTS not in meta_data:
            existing_stateid = self._get_existing_stateid(meta_data[COL_NAME_MET_DATA_MEASID],
                                                          meta_data[COL_NAME_MET_DATA_STATEID])
        else:
            existing_stateid = meta_data[COL_NAME_MET_DATA_STATEID]
        cond1 = SQLBinaryExpr(COL_NAME_MET_DATA_MEASID, OP_EQ, meta_data[COL_NAME_MET_DATA_MEASID])
        if (COL_NAME_MET_DATA_ABSTS in meta_data) and (COL_NAME_MET_DATA_STATEID in meta_data):
            cond2 = SQLBinaryExpr(COL_NAME_MET_DATA_ABSTS, OP_EQ, meta_data[COL_NAME_MET_DATA_ABSTS])
            cond3 = SQLBinaryExpr(COL_NAME_MET_DATA_STATEID, OP_EQ, existing_stateid)
            cond_tmp = SQLBinaryExpr(cond1, OP_AND, cond2)
            cond = SQLBinaryExpr(cond_tmp, OP_AND, cond3)
        elif (COL_NAME_MET_DATA_ABSTS not in meta_data) and (COL_NAME_MET_DATA_STATEID in meta_data):
            cond3 = SQLBinaryExpr(COL_NAME_MET_DATA_STATEID, OP_EQ, existing_stateid)
            cond = SQLBinaryExpr(cond1, OP_AND, cond3)
        elif (COL_NAME_MET_DATA_ABSTS in meta_data) and (COL_NAME_MET_DATA_STATEID not in meta_data):
            cond2 = SQLBinaryExpr(COL_NAME_MET_DATA_ABSTS, OP_EQ, meta_data[COL_NAME_MET_DATA_ABSTS])
            cond = SQLBinaryExpr(cond1, OP_AND, cond2)
        else:
            cond = cond1
        return cond

    # ====================================================================
    # Handling of Meta Types
    # ====================================================================
    def add_meta_type(self, meta_type):
        """
        Add Meta Type record to database.

        :param meta_type: The meta_type record.
        :type meta_type: Dict
        :return: Returns the meta_type ID and default meta state ID (if pick_value is 1)
        :rtype: Integer
        """
        cond = self._get_meta_type_condition(meta_type[COL_NAME_MET_TYPES_NAME])
        entries = self.select_generic_data(table_list=[TABLE_NAME_MET_TYPES], where=cond)
        meta_type[COL_NAME_MET_TYPES_NAME] = meta_type[COL_NAME_MET_TYPES_NAME].upper()
        if len(entries) <= 0:
            self.add_generic_data(meta_type, TABLE_NAME_MET_TYPES)
        else:
            tmp = "Meta Type '%s' exists already in the database" % meta_type[COL_NAME_MET_TYPES_NAME]
            self._log.info(tmp)

        type_id = self.__get_meta_type_id(meta_type)
        if meta_type[COL_NAME_MET_TYPES_PICK_VALUE] == 1 and type_id is not None:
            meta_state = {}
            meta_state[COL_NAME_MET_STATES_TYPEID] = type_id
            meta_state[COL_NAME_MET_STATES_NAME] = 'default'
            meta_state[COL_NAME_MET_STATES_DESCRIPTION] = "default state for type " + meta_type[COL_NAME_MET_TYPES_NAME]
            state_id = self.add_meta_state(meta_state)
        else:
            state_id = None
        return type_id, state_id

    def get_meta_type(self, name):
        """
        Get the Meta Type record based on measurement idetifier and/or start and end scenario timestamps.

        :param name: The meta type name.
        :type name: String
        :return: Returns the Meta Type record.
        :rtype: Dict
        """
        record = {}
        cond = self._get_meta_type_condition(name)
        entries = self.select_generic_data(table_list=[TABLE_NAME_MET_TYPES], where=cond)
        if len(entries) <= 0:
            self._log.warning(str("Meta Types with name '%s' does not exists in the MET_TYPES table." % name))
        elif len(entries) > 1:
            self._log.info(str("More than one Meta Types exists with name '%s'." % name))
            record = entries
        else:
            record = entries[0]
        return record

    def __get_meta_type_id(self, meta_type):
        """
        Get existing Meta Data ID.

        :param meta_type: Meta Data record
        :type meta_type: Dict
        :return: Returns Meta Data ID
        :rtype: Integer
        """
        name = meta_type[COL_NAME_MET_TYPES_NAME]
        record = self.get_meta_type(name)
        if COL_NAME_MET_TYPES_TYPEID in record:
            return record[COL_NAME_MET_TYPES_TYPEID]
        else:
            return None

    @staticmethod
    def _get_meta_type_condition(name):
        """
        Get the condition expression to access the Scenario.

        :param name: State ID
        :type name: String
        :return: Returns the condition expression
        :rtype: SQLBinaryExpression
        """
        cond = SQLBinaryExpr(COL_NAME_MET_TYPES_NAME, OP_EQ, SQLLiteral(name.upper()))
        return cond

    def _get_meta_types_pickvalue(self, typeid):
        """
        Get the pick value state of a meta type.

        :param typeid: Type ID of the Meta Type
        :type typeid: Integer
        :return: Pick Value state
        :rtype: Boolean
        """
        record = {}
        cond = SQLBinaryExpr(COL_NAME_MET_TYPES_TYPEID, OP_EQ, typeid)
        entries = self.select_generic_data(table_list=[TABLE_NAME_MET_TYPES], where=cond)
        if len(entries) <= 0:
            self._log.warning(str("Meta Types with record '%s' does not exists in the MET_TYPES table." % typeid))
        elif len(entries) > 1:
            self._log.info(str("More than one Meta Types exists with record '%s'." % typeid))
            record = entries
        else:
            record = entries[0]
        return record[COL_NAME_MET_TYPES_PICK_VALUE]

    def get_all_meta_types(self):
        """
        Returns all meta types
        """
        record = []
        entries = self.select_generic_data(table_list=[TABLE_NAME_MET_TYPES])
        for idx in xrange(len(entries)):
            record.append(entries[idx][COL_NAME_MET_TYPES_NAME])
        return record

    # ====================================================================
    # Handling of Meta States
    # ====================================================================
    def add_meta_state(self, meta_state):
        """
        Add Meta State record to database.

        :param meta_state: The meta_state record.
        :type meta_state: Dict
        :return: Returns the meta_state ID.
        :rtype: Integer
        """
        cond = self._get_meta_state_condition(meta_state)
        entries = self.select_generic_data(table_list=[TABLE_NAME_MET_STATES], where=cond)
        if len(entries) <= 0:
            self.add_generic_data(meta_state, TABLE_NAME_MET_STATES)
        else:
            tmp = "Meta State '%s' exists already in the database" % meta_state[COL_NAME_MET_STATES_NAME]
            self._log.info(tmp)

        state_id = self.__get_meta_state_id(meta_state)
        return state_id

    def get_meta_state(self, meta_state):
        """
        Get the Meta State record.

        :param meta_state: The meta state record.
        :type meta_state: Dict
        :return: Returns the Meta State record.
        :rtype: Dict
        """
        record = {}
        cond = self._get_meta_state_condition(meta_state)
        entries = self.select_generic_data(table_list=[TABLE_NAME_MET_STATES], where=cond)
        if len(entries) <= 0:
            self._log.warning(str("Meta States '%s' does not exists in the MET_STATES table." % str(meta_state)))
        elif len(entries) > 1:
            self._log.info(str("More than one Meta States exists with record '%s'." % str(meta_state)))
            record = entries
        else:
            record = entries[0]
        return record

    def __get_meta_state_id(self, meta_state):
        """
        Get existing Meta State ID.

        :param meta_state: Meta State record
        :type meta_state: Dict
        :return: Returns Meta State ID
        :rtype: Integer
        """
        record = self.get_meta_state(meta_state)
        if COL_NAME_MET_STATES_STATEID in record:
            return record[COL_NAME_MET_STATES_STATEID]
        else:
            return None

    @staticmethod
    def _get_meta_state_condition(meta_state):
        """
        Get the condition expression to access the meta state.

        :param meta_state: Meta State record.
        :type meta_state: Dict
        :return: Returns the condition expression
        :rtype: SQLBinaryExpression
        """
        name = meta_state[COL_NAME_MET_STATES_NAME]
        typeid = meta_state[COL_NAME_MET_STATES_TYPEID]
        cond1 = SQLBinaryExpr(COL_NAME_MET_STATES_NAME, OP_EQ, SQLLiteral(name))
        cond2 = SQLBinaryExpr(COL_NAME_MET_STATES_TYPEID, OP_EQ, SQLLiteral(typeid))
        cond = SQLBinaryExpr(cond1, OP_AND, cond2)
        return cond

    def _get_meta_states_typeid(self, stateid):
        """
        Get Meta Type ID from Meta State ID

        :param stateid: Meta State ID.
        :type stateid: Integer
        :return: Meta Type ID
        :rtype: Integer
        """
        record = {}
        cond = SQLBinaryExpr(COL_NAME_MET_STATES_STATEID, OP_EQ, stateid)
        entries = self.select_generic_data(table_list=[TABLE_NAME_MET_STATES], where=cond)
        if len(entries) <= 0:
            self._log.warning(str("Meta States with id '%s' does not exists in the MET_STATES table." % stateid))
        elif len(entries) > 1:
            self._log.info(str("More than one Meta States exists with id '%s'." % stateid))
            record = entries
        else:
            record = entries[0]
        return record[COL_NAME_MET_STATES_TYPEID]

    def _get_pickvalue_from_stateid(self, stateid):
        """
        Get Pick Value State from Meta State ID

        :param stateid: Meta State ID.
        :type stateid: Integer
        :return: Pick Value State
        :rtype: Boolean
        """
        typeid = self._get_meta_states_typeid(stateid)
        return self._get_meta_types_pickvalue(typeid)

    def _get_existing_stateid(self, measid, stateid):
        """
        Get the existing state id for a measid.

        :param measid: Measurement ID.
        :type measid: Integer
        :param stateid: Meta State ID.
        :type stateid: Integer
        :return: Meta State ID
        :rtype: Integer
        """
        typeid = self._get_meta_states_typeid(stateid)
        tblmd = TABLE_NAME_MET_DATA
        tblms = TABLE_NAME_MET_STATES
        join_1 = SQLJoinExpr(SQLTableExpr(tblmd),
                             OP_INNER_JOIN, SQLTableExpr(tblms),
                             SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblmd),
                                                         COL_NAME_MET_DATA_STATEID), OP_EQ,
                                           SQLColumnExpr(SQLTableExpr(tblms),
                                                         COL_NAME_MET_STATES_STATEID)))

        cond1 = SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblmd), COL_NAME_MET_DATA_MEASID), OP_EQ, measid)
        cond2 = SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblms), COL_NAME_MET_STATES_TYPEID), OP_EQ, typeid)
        cond = SQLBinaryExpr(cond1, OP_AND, cond2)
        col_list = [SQLColumnExpr(SQLTableExpr(tblmd), COL_NAME_MET_DATA_STATEID)]
        ex_stateid = self.select_generic_data(select_list=col_list, table_list=[join_1], where=cond)
        if ex_stateid == []:
            return stateid
        else:
            return ex_stateid[0][COL_NAME_MET_DATA_STATEID]

    def get_stateids_from_type(self, name):
        """
        Get the state ids for a meta type.

        :param name: Meta Type Name.
        :type name: String
        :return: Meta State IDs
        :rtype: List
        """
        tblms = TABLE_NAME_MET_STATES
        tblmt = TABLE_NAME_MET_TYPES
        join_1 = SQLJoinExpr(SQLTableExpr(tblms),
                             OP_INNER_JOIN, SQLTableExpr(tblmt),
                             SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblms),
                                                         COL_NAME_MET_STATES_TYPEID), OP_EQ,
                                           SQLColumnExpr(SQLTableExpr(tblmt),
                                                         COL_NAME_MET_TYPES_TYPEID)))

        cond = SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblmt), COL_NAME_MET_TYPES_NAME),
                             OP_EQ, SQLLiteral(name.upper()))
        col_list = [SQLColumnExpr(SQLTableExpr(tblms), COL_NAME_MET_DATA_STATEID)]
        stateids = self.select_generic_data(select_list=col_list, table_list=[join_1], where=cond)
        return stateids

"""
CHANGE LOG:
-----------
$Log: met.py  $
Revision 1.3 2017/02/12 13:55:39CET Hospes, Gerd-Joachim (uidv8815) 
pep8 fixes
Revision 1.2 2016/09/27 15:39:27CEST Hospes, Gerd-Joachim (uidv8815)
doc and pylint fixes
Revision 1.1 2016/09/20 15:28:17CEST Zafar, Sohaib (uidu6396)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/db/met/project.pj
"""
