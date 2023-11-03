"""
stk/db/par/__init__.py
----------------------

Classes for Database access of Parameter Definitions.

Sub-Scheme PAR

**User-API**
    - `BaseParDB`
        unused database, currently (Jun.16) nothing stored on Oracle,
        purpose unknown, could be used as sqlite only

The other classes in this module are handling the different DB types and are derived from BaseParDB.

**usage in Valf suites**

For validation suites based on `Valf` class there is the operator `DbLinker` setting up all needed connections.

**using several connections in parallel**

If several sub-schemes have to be used in parallel the first connection should be reused.
Please check class `BaseParDB` for more detail.

**Do not waste the limited number of connections to Oracle DB**
by setting up a new connection for each sub-scheme,
always use the existing one as described in `BaseParDB`.

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.6 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 16:01:42CEST $
"""
# pylint: disable=R0913
# =====================================================================================================================
# Imports
# =====================================================================================================================
from stk.db.db_common import BaseDB, ERROR_TOLERANCE_NONE, AdasDBError, ERROR_TOLERANCE_LOW, DB_FUNC_NAME_LOWER, \
    PluginBaseDB
from stk.db.db_sql import GenericSQLStatementFactory, SQLBinaryExpr, OP_EQ, SQLLiteral, SQLFuncExpr, OP_AND
from stk.valf.signal_defs import DBPAR

from stk.util.helper import deprecated

# =====================================================================================================================
# Constants
# =====================================================================================================================

# Table base names:
TABLE_NAME_DESCRIPTION = "PAR_Description"
TABLE_NAME_CONFIGS = "PAR_Configs"
TABLE_NAME_CFGMAP = "PAR_CfgMap"
TABLE_NAME_VALUE = "PAR_Value"
TABLE_NAME_VALUEARCHIVE = "PAR_ValueArchive"

# Parameter Description Table
COL_NAME_DESC_ID = "PDID"
COL_NAME_DESC_NAME = "NAME"
COL_NAME_DESC_TYPE = "VTID"
COL_NAME_DESC_UNIT = "UNITID"

# Parameter Configs Table
COL_NAME_CFG_ID = "PCID"
COL_NAME_CFG_NAME = "CFGNAME"

# Parameter-Config Map Table
COL_NAME_PARCFG_MAP_ID = "PMID"
COL_NAME_PARCFG_MAP_PDID = "PDID"
COL_NAME_PARCFG_MAP_PCID = "PCID"

# Parameter Value Table
COL_NAME_PAR_VAL_ID = "PARID"
COL_NAME_PAR_VAL_MEASID = "MEASID"
COL_NAME_PAR_VAL_PMID = "PMID"
COL_NAME_PAR_VAL_USERID = "USERID"
COL_NAME_PAR_VAL_WFID = "WFID"
COL_NAME_PAR_VAL_TIMESTAMP = "MODDATE"
COL_NAME_PAR_VAL_VALUE = "VALUE"

# Default return value if no result is found.
COL_PAR_DEF_VAL = -1

IDENT_STRING = DBPAR

# ===============================================================================
# Parameters DB Library Base Implementation
# ===============================================================================


class BaseParDB(BaseDB):  # pylint: disable=R0904
    """**ase implementation of the Parameter File Database**

    For the first connection to the DB for par tables just create a new instance of this class like

    .. python::

        from stk.db.par.par import BaseParDB

        dbpar = BaseParDB("MFC4XX")   # or use "ARS4XX", "VGA" or path/name of sqlite file

    If already some connection to another table of the DB is created use that one to speed up your code:

    .. python::

        dbpar = BaseParDB(dbxxx.db_connection)

    The connection is closed when the first instance using it is deleted.

    **error_tolerance**

    The setting of an error tolerance level allowes to define if an error during later processing is

    - just listed to the log file (error_tolerance = 3, HIGH) if possible,
      e.g. if it can return the existing id without changes in case of adding an already existing entry
    - raising an AdasDBError immediately (error_tolerance < 1, LOW)

    More optional keywords are described at `BaseDB` class initialization.

    """
    # ====================================================================
    # Parameters DB Library Interface for public use
    # ====================================================================

    # ====================================================================
    # Handling of database
    # ====================================================================

    def __init__(self, *args, **kwargs):
        """
        Constructor to initialize BaseParDB to represent PAR subschema

        :keyword db_connection: The database connection to be used
        :type db_connection: cx_oracle.Connection, pydodbc.Connection, sqlite3.Connection, sqlce.Connection
        :keyword table_prefix: The table name prefix which is usually master schema name
        :type table_prefix: str
        :keyword error_tolerance: Error tolerance level based on which some error are exceptable
        :type error_tolerance: int
        """
        kwargs['strIdent'] = DBPAR
        BaseDB.__init__(self, *args, **kwargs)

    # --- Parameters Description Table. ----------------------------------------
    def add_parameter_description(self, param, type_id, unit_id):
        """
        Add a new parameter description to the database.

        :param param: The parameter description NAME
        :type param: str
        :param type_id: The parameter type ID
        :type type_id: int
        :param unit_id: The parameter unit ID
        :type unit_id: int
        :return: Returns the new parameter description ID
        :rtype: int
        """
        if param is None:
            raise AdasDBError("Parameter description name is not set.")
        if type_id is None:
            raise AdasDBError("Parameter description type is not set.")
        if unit_id is None:
            raise AdasDBError("Parameter description unit is not set.")

        pardesc = {COL_NAME_DESC_ID: None, COL_NAME_DESC_NAME: param,
                   COL_NAME_DESC_TYPE: type_id, COL_NAME_DESC_UNIT: unit_id}

        pdid = self.get_parameter_description_id(param)
        if pdid is None:
            self.add_generic_data(pardesc, TABLE_NAME_DESCRIPTION)
            pdid = self.get_parameter_description_id(param)
            return pdid
        else:
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                tmp = "Parameter description '%s' exists already in the validation parameter database." % param
                raise AdasDBError(tmp)
            else:
                return pdid

    def update_parameter_description(self, param, type_id, unit_id):
        """
        Update an already existing parameter description into the database.

        :param param: The parameter description NAME
        :type param: str
        :param type_id: The parameter type ID
        :type type_id: int
        :param unit_id: The parameter unit ID
        :type unit_id: int
        :return: No. of rows effected
        :rtype: int
        """
        if param is None:
            raise AdasDBError("Parameter description name is not set.")
        if type_id is None:
            raise AdasDBError("Parameter description type is not set.")
        if unit_id is None:
            raise AdasDBError("Parameter description unit is not set.")

        pardesc = {COL_NAME_DESC_ID: None, COL_NAME_DESC_NAME: param,
                   COL_NAME_DESC_TYPE: type_id, COL_NAME_DESC_UNIT: unit_id}

        pdid = self.get_parameter_description_id(param)
        if pdid is None:
            raise AdasDBError("Parameter description '%s' doesn't exists in the validation parameter database." %
                              param)
        else:
            pardesc[COL_NAME_DESC_ID] = pdid
            return self.update_generic_data(pardesc, TABLE_NAME_DESCRIPTION,
                                            where=self._get_parameter_description_condition(param))

    def delete_parameter_description(self, param):
        """
        Add a new parameter description to the database.

        :param param: The parameter description NAME
        :type param: str
        :return: Returns the number of affected rows
        :rtype: int
        """
        if param is None:
            raise AdasDBError("Parameter description name is not set.")
        return self.delete_generic_data(TABLE_NAME_DESCRIPTION,
                                        where=self._get_parameter_description_condition(param))

    def get_parameter_description_id(self, param):
        """
        Get a parameter description ID from the database.

        :param param: The parameter description NAME
        :type param: str
        :return: Returns the parameter description ID
        :rtype: int
        """
        if param is None:
            raise AdasDBError("Parameter description name is not set.")
        entries = self.select_generic_data(table_list=[TABLE_NAME_DESCRIPTION],
                                           where=self._get_parameter_description_condition(param))
        if len(entries) <= 0:
            return None
        elif len(entries) == 1:
            return entries[0][COL_NAME_DESC_ID]
        elif len(entries) > 1:
            tmp = "Parameter description '%s' cannot be resolved because it is ambiguous. (%s)" % (param, entries)
            raise AdasDBError(tmp)

    def get_parameter_description(self, param):
        """
        Get a parameter description from the database.

        :param param: The parameter description NAME
        :type param: str
        :return: Returns the parameter description record
        :rtype: dict
        """
        if param is None:
            raise AdasDBError("Parameter description name is not set.")
        entries = self.select_generic_data(table_list=[TABLE_NAME_DESCRIPTION],
                                           where=self._get_parameter_description_condition(param))
        if len(entries) <= 0:
            return None
        elif len(entries) == 1:
            return entries[0]
        else:
            tmp = "Parameter description '%s' cannot be resolved because it is ambiguous. (%s)" % (param, entries)
            raise AdasDBError(tmp)

    def _get_parameter_description_condition(self, name=None, type_id=None, unit_id=None,  # pylint: disable=C0103
                                             pdid=None):
        """
        Get the condition expression to access the testrun.

        :param name: Name of the parameter description (optional)
        :type name: str
        :param type_id: Type of the parameter description (optional)
        :type type_id: int
        :param unit_id: Unit of the parameter description (optional)
        :type unit_id: int
        :param pdid: Parameter description ID. If set, the other settings will neglected.
        :type pdid: int
        :return: Returns the condition expression for selecting parameter descriptions
        :rtype: SQLBinaryExpression
        """
        cond = None

        if pdid is not None:
            cond = SQLBinaryExpr(COL_NAME_DESC_ID, OP_EQ, SQLLiteral(pdid))
        else:
            if name is not None:
                cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER], COL_NAME_DESC_NAME),
                                     OP_EQ, SQLLiteral(name.lower()))
            if type_id is not None:
                cond_type = SQLBinaryExpr(COL_NAME_DESC_TYPE, OP_EQ, SQLLiteral(type_id))
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_type)
                else:
                    cond = cond_type

            if unit_id is not None:
                cond_unit = SQLBinaryExpr(COL_NAME_DESC_UNIT, OP_EQ, SQLLiteral(unit_id))
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_unit)
                else:
                    cond = cond_unit

        return cond

    # --- Parameter Configs Table. ---------------------------------------------
    def add_config(self, config):
        """
        Add a new parameter config to the database.

        :param config: The parameter config NAME
        :type config: str
        :return: Returns the new parameter config ID
        :rtype: int
        """
        if config is None:
            raise AdasDBError("Parameter config name is not set.")

        parcfg = {COL_NAME_CFG_ID: None, COL_NAME_CFG_NAME: config}

        pcid = self.get_config_id(config)
        if pcid is None:
            self.add_generic_data(parcfg, TABLE_NAME_CONFIGS)
            pcid = self.get_config_id(config)
            return pcid
        else:
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError("Parameter config '%s' exists already in the validation parameter database." %
                                  config)
            else:
                return pcid

    def delete_config(self, config):
        """
        Add a new parameter description to the database.

        :param config: The parameter config NAME
        :type config: str
        :return: Returns the number of affected rows
        :rtype: int
        """
        if config is None:
            raise AdasDBError("Parameter config name is not set.")
        return self.delete_generic_data(TABLE_NAME_CONFIGS, where=self._get_config_condition(name=config))

    def get_config_id(self, config):
        """
        Get a parameter config ID from the database.

        :param config: The parameter config NAME
        :type config: str
        :return: Returns the parameter config ID
        :rtype: int
        """
        if config is None:
            raise AdasDBError("Parameter config name is not set.")
        entries = self.select_generic_data(table_list=[TABLE_NAME_CONFIGS],
                                           where=self._get_config_condition(name=config))
        if len(entries) <= 0:
            return None
        elif len(entries) == 1:
            return entries[0][COL_NAME_CFG_ID]
        elif len(entries) > 1:
            tmp = "Parameter config '%s' cannot be resolved because it is ambiguous. (%s)" % (config, entries)
            raise AdasDBError(tmp)

    def _get_config_condition(self, name=None, cid=None):
        """Get the condition expression to access the testrun.

        :param name: Name of the parameter config(optional)
        :param cid: Parameter config ID. If set, the other settings will neglected.
        :return: Returns the condition expression for selecting parameter configs
        :rtype: SQLBinaryExpression
        """
        cond = None

        if cid is not None:
            cond = SQLBinaryExpr(COL_NAME_CFG_ID, OP_EQ, SQLLiteral(cid))
        else:
            if name is not None:
                cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                 COL_NAME_CFG_NAME), OP_EQ, SQLLiteral(name.lower()))
        return cond

    # --- Parameter Config Map Table. ------------------------------------------
    def add_parameter_config_map(self, config_id, par_id):
        """
        Add a new parameter config mapping to the database.

        :param config_id: The parameter config ID
        :type config_id: int
        :param par_id: The parameter description ID
        :type par_id: int
        :return: Returns the parameter config map ID
        :rtype: int
        """
        if config_id is None:
            raise AdasDBError("Parameter config identifier is not set.")
        if par_id is None:
            raise AdasDBError("Parameter description identifier is not set.")

        parcfgmap = {COL_NAME_PARCFG_MAP_ID: None,
                     COL_NAME_PARCFG_MAP_PDID: par_id,
                     COL_NAME_PARCFG_MAP_PCID: config_id}

        pmid = self.get_parameter_config_map_id(config_id, par_id)
        if pmid is None:
            self.add_generic_data(parcfgmap, TABLE_NAME_CFGMAP)
            pmid = self.get_parameter_config_map_id(config_id, par_id)
            return pmid
        else:
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                tmp = "Parameter config mapping [%s|%s] " % (config_id, par_id)
                tmp += "exists already in the validation parameter database."
                raise AdasDBError(tmp)
            else:
                return pmid

    def delete_parameter_config_map(self, config_id, par_id):
        """
        Delete a parameter config mapping from the database.

        :param config_id: The parameter config ID
        :type config_id: int
        :param par_id: The parameter description ID
        :type par_id: int
        :return: Returns the number of affected rows
        :rtype: int
        """
        if config_id is None:
            raise AdasDBError("Parameter config identifier is not set.")
        if par_id is None:
            raise AdasDBError("Parameter description identifier is not set.")
        return self.delete_generic_data(TABLE_NAME_CFGMAP,
                                        where=self._get_parameter_config_map_condition(config_id, par_id))

    def get_parameter_config_map_id(self, config_id, par_id):
        """
        Get a parameter config mapping identifier from the database.

        :param config_id: The parameter config ID
        :type config_id: int
        :param par_id: The parameter description ID
        :type par_id: int
        :return: Returns the parameter config map ID
        :rtype: int
        """
        if config_id is None:
            raise AdasDBError("Parameter config identifier is not set.")
        if par_id is None:
            raise AdasDBError("Parameter description identifier is not set.")
        entries = self.select_generic_data(table_list=[TABLE_NAME_CFGMAP],
                                           where=self._get_parameter_config_map_condition(config_id, par_id))
        if len(entries) <= 0:
            return None
        elif len(entries) == 1:
            return entries[0][COL_NAME_PARCFG_MAP_ID]
        elif len(entries) > 1:
            tmp = "Parameter config mapping [%s|%s] " % (config_id, par_id)
            tmp += "cannot be resolved because it is ambiguous. "
            tmp += "(%s)" % entries
            raise AdasDBError(tmp)

    @staticmethod
    def _get_parameter_config_map_condition(config_id=None, par_id=None, pcmid=None):  # pylint: disable=C0103
        """
        Get the condition expression to access the testrun.

        :param config_id: The parameter config ID
        :param par_id: The parameter description ID
        :param pcmid: Parameter config ID. If set, the other settings will neglected.
        :return: Returns the condition expression for selecting parameter config mappings
        :rtype: SQLBinaryExpression
        """
        cond = None

        if pcmid is not None:
            cond = SQLBinaryExpr(COL_NAME_PARCFG_MAP_ID, OP_EQ, SQLLiteral(pcmid))
        else:
            if config_id is not None:
                cond = SQLBinaryExpr(COL_NAME_PARCFG_MAP_PCID, OP_EQ, SQLLiteral(config_id))

            if par_id is not None:
                cond_par = SQLBinaryExpr(COL_NAME_PARCFG_MAP_PDID, OP_EQ, SQLLiteral(par_id))
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_par)
                else:
                    cond = cond_par
        return cond

    # --- Parameter Values Table. ----------------------------------------------
    def add_parameter_value(self, measid, pmid, userid, wfid, value):
        """
        Add a new parameter value to the database.

        :param measid: The measurement file ID
        :type measid: int
        :param pmid: The parameter config map ID
        :type pmid: int
        :param userid: The user ID
        :type userid: int
        :param wfid: The workflow ID
        :type wfid: int
        :param value: The parameter value
        :type value: float | int
        :return: Returns the parameter value ID
        :rtype: int
        """
        if measid is None:
            raise AdasDBError("Parameter measurement file identifier is not set.")
        if pmid is None:
            raise AdasDBError("Parameter config map is not set.")
        if userid is None:
            raise AdasDBError("Parameter user identifier is not set.")
        if wfid is None:
            raise AdasDBError("Parameter workflow identifier is not set.")
        if value is None:
            raise AdasDBError("Parameter value is not set.")

        parval = {COL_NAME_PAR_VAL_ID: None,
                  COL_NAME_PAR_VAL_MEASID: measid,
                  COL_NAME_PAR_VAL_PMID: pmid,
                  COL_NAME_PAR_VAL_USERID: userid,
                  COL_NAME_PAR_VAL_WFID: wfid,
                  COL_NAME_PAR_VAL_VALUE: value}
        # Remark: Don't put NULL for the timestamp, because the timestamp column is NULLABLE
        # Leave it out of the query and it will be auto-completed with the current TIMESTAMP
        # parval[COL_NAME_PAR_VAL_TIMESTAMP] = CURRENT_TIMESTAMP

        parid = self.get_parameter_value_id(measid, pmid)
        if parid is None:
            self.add_generic_data(parval, TABLE_NAME_VALUE)
            parid = self.get_parameter_value_id(measid, pmid)
            return parid
        else:
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                tmp = "Parameter value [%s|%s|%s|%s] " % (measid, pmid, userid, wfid)
                tmp += "exists already in the validation parameter database."
                raise AdasDBError(tmp)
            else:
                return parid

    def update_parameter_value(self, measid, pmid, userid, wfid, value):
        """
        Update a parameter value into the database.

        :param measid: The measurement file ID
        :type measid: int
        :param pmid: The parameter config map ID
        :type pmid: int
        :param userid: The user ID
        :type userid: int
        :param wfid: The workflow ID
        :type wfid: int
        :param value: The parameter value
        :type value: float | int
        :return: Returns number of rows effected
        :rtype: int
        """
        if measid is None:
            raise AdasDBError("Parameter measurement file identifier is not set.")
        if pmid is None:
            raise AdasDBError("Parameter config map is not set.")
        if userid is None:
            raise AdasDBError("Parameter user identifier is not set.")
        if wfid is None:
            raise AdasDBError("Parameter workflow identifier is not set.")
        if value is None:
            raise AdasDBError("Parameter value is not set.")

        parval = {COL_NAME_PAR_VAL_ID: None,
                  COL_NAME_PAR_VAL_MEASID: measid,
                  COL_NAME_PAR_VAL_PMID: pmid,
                  COL_NAME_PAR_VAL_USERID: userid,
                  COL_NAME_PAR_VAL_WFID: wfid,
                  COL_NAME_PAR_VAL_TIMESTAMP: self.curr_datetime_expr(),
                  COL_NAME_PAR_VAL_VALUE: value}
        # Remark: Don't put NULL for the timestamp, because the timestamp column is NULLABLE
        # Leave it out of the query and it will be auto-completed with the current TIMESTAMP

        parid = self.get_parameter_value_id(measid, pmid)
        if parid is None:
            tmp = "Parameter value [%s|%s|%s|%s] " % (measid, pmid, userid, wfid)
            tmp += "doesn't exists in the validation parameter database."
            raise AdasDBError(tmp)
        else:
            parval[COL_NAME_PAR_VAL_ID] = parid
            return self.update_generic_data(parval, TABLE_NAME_VALUE,
                                            where=self._get_parameter_value_condition(measid, pmid))

    def delete_parameter_value(self, measid, pmid):
        """
        Delete a parameter value from the database.

        :param measid: The measurement file ID
        :type measid: int
        :param pmid: The parameter config map ID
        :type pmid: int
        :return: Returns the number of affected rows
        :rtype: int
        """
        if measid is None:
            raise AdasDBError("Parameter measurement file identifier is not set.")
        if pmid is None:
            raise AdasDBError("Parameter config map is not set.")
        return self.delete_generic_data(TABLE_NAME_VALUE, where=self._get_parameter_value_condition(measid, pmid))

    def get_parameter_value(self, measid, pmid):
        """
        Get a parameter value from the database.

        :param measid: The measurement file ID
        :type measid: int
        :param pmid: The parameter config map ID
        :type pmid: int
        :return: Returns the parameter value
        :rtype: int
        """
        if measid is None:
            raise AdasDBError("Parameter measurement file identifier is not set.")
        if pmid is None:
            raise AdasDBError("Parameter config map is not set.")
        entries = self.select_generic_data(table_list=[TABLE_NAME_VALUE],
                                           where=self._get_parameter_value_condition(measid, pmid))
        if len(entries) <= 0:
            return None
        elif len(entries) == 1:
            return entries[0][COL_NAME_PAR_VAL_VALUE]
        elif len(entries) > 1:
            tmp = "Parameter value [%s|%s|%s] " % (measid, pmid, entries)
            tmp += "cannot be resolved because it is ambiguous."
            raise AdasDBError(tmp)

    def get_parameter_workflow_id(self, measid, pmid):
        """
        Get a parameter workflow ID from the database.

        :param measid: The measurement file ID
        :type measid: int
        :param pmid: The parameter config map ID
        :type pmid: int
        :return: Returns the parameter workflow id
        :rtype: int
        """
        if measid is None:
            raise AdasDBError("Parameter measurement file identifier is not set.")
        if pmid is None:
            raise AdasDBError("Parameter config map is not set.")
        entries = self.select_generic_data(table_list=[TABLE_NAME_VALUE],
                                           where=self._get_parameter_value_condition(measid, pmid))
        if len(entries) <= 0:
            return None
        elif len(entries) == 1:
            return entries[0][COL_NAME_PAR_VAL_WFID]
        elif len(entries) > 1:
            tmp = "Parameter value [%s|%s|%s] " % (measid, pmid, entries)
            tmp += "cannot be resolved because it is ambiguous."
            raise AdasDBError(tmp)

    def get_parameter_value_id(self, measid, pmid):
        """
        Get a parameter value ID from the database.

        :param measid: The measurement file ID
        :type measid: int
        :param pmid: The parameter config map ID
        :type pmid: int
        :return: Returns the parameter value ID
        :rtype: int
        """
        if measid is None:
            raise AdasDBError("Parameter measurement file identifier is not set.")
        if pmid is None:
            raise AdasDBError("Parameter config map is not set.")
        entries = self.select_generic_data(table_list=[TABLE_NAME_VALUE],
                                           where=self._get_parameter_value_condition(measid, pmid))
        if len(entries) <= 0:
            return None
        elif len(entries) == 1:
            return entries[0][COL_NAME_PAR_VAL_ID]
        elif len(entries) > 1:
            tmp = "Parameter value [%s|%s|%s] " % (measid, pmid, entries)
            tmp += "cannot be resolved because it is ambiguous."
            raise AdasDBError(tmp)

    @staticmethod
    def _get_parameter_value_condition(measid=None, pmid=None, userid=None, wfid=None, pvid=None):
        """
        Get the condition expression to access the parameter value.

        :param measid: The measurement file ID (optional)
        :param pmid: The parameter config map ID (optional)
        :param userid: The parameter user ID (optional)
        :param wfid: The parameter workflow ID (optional)
        :param pvid: Parameter value ID. If set, the other settings will neglected.
        :return: Returns the condition expression
        :rtype: SQLBinaryExpression
        """
        cond = None

        if pvid is not None:
            cond = SQLBinaryExpr(COL_NAME_PAR_VAL_ID, OP_EQ, SQLLiteral(pvid))
        else:
            if measid is not None:
                cond = SQLBinaryExpr(COL_NAME_PAR_VAL_MEASID, OP_EQ, SQLLiteral(measid))

            if pmid is not None:
                cond_pmid = SQLBinaryExpr(COL_NAME_PAR_VAL_PMID, OP_EQ, SQLLiteral(pmid))
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_pmid)
                else:
                    cond = cond_pmid

            if userid is not None:
                cond_userid = SQLBinaryExpr(COL_NAME_PAR_VAL_USERID, OP_EQ, SQLLiteral(userid))
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_userid)
                else:
                    cond = cond_userid

            if wfid is not None:
                cond_wfid = SQLBinaryExpr(COL_NAME_PAR_VAL_WFID, OP_EQ, SQLLiteral(wfid))
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_wfid)
                else:
                    cond = cond_wfid

        return cond

    # --- Utilities Functions --------------------------------------------------

    # --- Parameter Configuration Functions ------------------------------------
    def add_parameter_description_to_config(self, config, param):  # pylint: disable=C0103
        """
        Add a parameter description to a parameter configuration

        :param config: The parameter configuration NAME
        :type config: str
        :param param: The parameter description NAME
        :type param: str
        :return: Returns the config-parameter map ID
        :rtype: int
        """
        par_id = self.get_parameter_description_id(param)
        config_id = self.get_config_id(config)
        return self.add_parameter_config_map(config_id, par_id)

    def delete_parameter_description_from_config(self, config, param):  # pylint: disable=C0103
        """
        Delete a parameter description from a parameter configuration

        :param config: The parameter configuration NAME
        :type config: str
        :param param: The parameter description NAME
        :type param: str
        :return: Returns the number of affected rows
        :rtype: int
        """
        par_id = self.get_parameter_description_id(param)
        config_id = self.get_config_id(config)
        return self.delete_parameter_config_map(config_id, par_id)

    def get_parameter_config_map_id_using_names(self, config, param):  # pylint: disable=C0103
        """
        Get a parameter config identifier using config and parameter descriptions names

        :param config: The parameter config NAME
        :type config: str
        :param param: The parameter description NAME
        :type param: str
        :return: Returns the parameter config map ID
        :rtype: int
        """
        par_id = self.get_parameter_description_id(param)
        config_id = self.get_config_id(config)
        return self.get_parameter_config_map_id(config_id, par_id)

    # --- Parameter Value Functions --------------------------------------------
    def add_parameter_value_to_meas_id(self, measid, config, param, userid, wfid, value):
        """
        Add a new parameter value for a file

        :param measid: The measurement file ID
        :type measid: int
        :param config: The parameter config NAME
        :type config: str
        :param param: The parameter description NAME
        :type param: str
        :param userid: The user ID
        :type userid: int
        :param wfid: The workflow ID
        :type wfid: int
        :param value: The parameter value
        :type value: float | int
        :return: Returns the new parameter value ID
        :rtype: int
        """
        par_id = self.get_parameter_description_id(param)
        config_id = self.get_config_id(config)
        pmid = self.get_parameter_config_map_id(config_id, par_id)
        return self.add_parameter_value(measid, pmid, userid, wfid, value)

    def update_parameter_value_of_meas_id(self, measid, config, param, userid, wfid, value):  # pylint: disable=C0103
        """
        Update a parameter value associated to a file

        :param measid: The measurement file ID
        :type measid: int
        :param config: The parameter config NAME
        :type config: str
        :param param: The parameter description NAME
        :type param: str
        :param userid: The user ID
        :type userid: int
        :param wfid: The workflow ID
        :type wfid: int
        :param value: The parameter value
        :type value: int
        :return: Returns the parameter value ID
        :rtype: int
        """
        par_id = self.get_parameter_description_id(param)
        config_id = self.get_config_id(config)
        pmid = self.get_parameter_config_map_id(config_id, par_id)
        return self.update_parameter_value(measid, pmid, userid, wfid, value)

    def delete_parameter_value_from_meas_id(self, measid, config, param):  # pylint: disable=C0103
        """
        Delete parameter value associated to a file

        :param measid: The measurement file ID
        :type measid: int
        :param config: The parameter config NAME
        :type config: str
        :param param: The parameter description NAME
        :type param: str
        :return: Returns the number of affected rows
        :rtype: int
        """
        par_id = self.get_parameter_description_id(param)
        config_id = self.get_config_id(config)
        pmid = self.get_parameter_config_map_id(config_id, par_id)
        return self.delete_parameter_value(measid, pmid)

    def get_parameter_value_of_meas_id(self, measid, config, param):
        """
        Get parameter value associated to a file

        :param measid: The measurement file ID
        :type measid: int
        :param config: The parameter config NAME
        :type config: str
        :param param: The parameter description NAME
        :type param: str
        :return: Returns the parameter value
        :rtype: int | float
        """
        par_id = self.get_parameter_description_id(param)
        config_id = self.get_config_id(config)
        pmid = self.get_parameter_config_map_id(config_id, par_id)
        return self.get_parameter_value(measid, pmid)

    def get_parameter_workflow_id_of_meas_id(self, measid, config, param):  # pylint: disable=C0103
        """
        Get parameter Workflow associated to a file

        :param measid: The measurement file ID
        :type measid: int
        :param config: The parameter config NAME
        :type config: str
        :param param: The parameter description NAME
        :type param: str
        :return: Returns the parameter workflowid
        :rtype: int
        """
        par_id = self.get_parameter_description_id(param)
        config_id = self.get_config_id(config)
        pmid = self.get_parameter_config_map_id(config_id, par_id)
        return self.get_parameter_workflow_id(measid, pmid)

    # =================================================================================================================
    # deprecated methods
    # =================================================================================================================

    @deprecated('add_parameter_description')
    def AddParameterDescription(self, param, type_id, unit_id):  # pylint: disable=C0103
        """deprecated"""
        return self.add_parameter_description(param, type_id, unit_id)

    @deprecated('update_parameter_description')
    def UpdateParameterDescription(self, param, type_id, unit_id):  # pylint: disable=C0103
        """deprecated"""
        return self.update_parameter_description(param, type_id, unit_id)

    @deprecated('delete_parameter_description')
    def DeleteParameterDescription(self, param):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_parameter_description(param)

    @deprecated('get_parameter_description_id')
    def GetParameterDescriptionID(self, param):  # pylint: disable=C0103
        """deprecated"""
        return self.get_parameter_description_id(param)

    @deprecated('get_parameter_description')
    def GetParameterDescription(self, param):  # pylint: disable=C0103
        """deprecated"""
        return self.get_parameter_description(param)

    @deprecated('add_config')
    def AddConfig(self, config):  # pylint: disable=C0103
        """deprecated"""
        return self.add_config(config)

    @deprecated('delete_config')
    def DeleteConfig(self, config):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_config(config)

    @deprecated('get_config_id')
    def GetConfigID(self, config):  # pylint: disable=C0103
        """deprecated"""
        return self.get_config_id(config)

    @deprecated('add_parameter_config_map')
    def AddParameterConfigMap(self, config_id, par_id):  # pylint: disable=C0103
        """deprecated"""
        return self.add_parameter_config_map(config_id, par_id)

    @deprecated('delete_parameter_config_map')
    def DeleteParameterConfigMap(self, config_id, par_id):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_parameter_config_map(config_id, par_id)

    @deprecated('get_parameter_config_map_id')
    def GetParameterConfigMapID(self, config_id, par_id):  # pylint: disable=C0103
        """deprecated"""
        return self.get_parameter_config_map_id(config_id, par_id)

    @deprecated('add_parameter_value')
    def AddParameterValue(self, measid, pmid, userid, wfid, value):  # pylint: disable=C0103
        """deprecated"""
        return self.add_parameter_value(measid, pmid, userid, wfid, value)

    @deprecated('update_parameter_value')
    def UpdateParameterValue(self, measid, pmid, userid, wfid, value):  # pylint: disable=C0103
        """deprecated"""
        return self.update_parameter_value(measid, pmid, userid, wfid, value)

    @deprecated('delete_parameter_value')
    def DeleteParameterValue(self, measid, pmid):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_parameter_value(measid, pmid)

    @deprecated('get_parameter_value')
    def GetParameterValue(self, measid, pmid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_parameter_value(measid, pmid)

    @deprecated('get_parameter_workflow_id')
    def GetParameterWorkflowID(self, measid, pmid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_parameter_workflow_id(measid, pmid)

    @deprecated('get_parameter_value_id')
    def GetParameterValueID(self, measid, pmid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_parameter_value_id(measid, pmid)

    @deprecated('add_parameter_description_to_config')
    def AddParameterDescriptionToConfig(self, config, param):  # pylint: disable=C0103
        """deprecated"""
        return self.add_parameter_description_to_config(config, param)

    @deprecated('delete_parameter_description_from_config')
    def DeleteParameterDescriptionFromConfig(self, config, param):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_parameter_description_from_config(config, param)

    @deprecated('get_parameter_config_map_id_using_names')
    def GetParameterConfigMapIDUsingNames(self, config, param):  # pylint: disable=C0103
        """deprecated"""
        return self.get_parameter_config_map_id_using_names(config, param)

    @deprecated('add_parameter_value_to_meas_id')
    def AddParameterValueToMeasId(self, measid, config, param, userid, wfid, value):  # pylint: disable=C0103
        """deprecated"""
        return self.add_parameter_value_to_meas_id(measid, config, param, userid, wfid, value)

    @deprecated('update_parameter_value_of_meas_id')
    def UpdateParameterValueOfMeasId(self, measid, config, param, userid, wfid, value):  # pylint: disable=C0103
        """deprecated"""
        return self.update_parameter_value_of_meas_id(measid, config, param, userid, wfid, value)

    @deprecated('delete_parameter_value_from_meas_id')
    def DeleteParameterValueFromMeasId(self, measid, config, param):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_parameter_value_from_meas_id(measid, config, param)

    @deprecated('get_parameter_value_of_meas_id')
    def GetParameterValueOfMeasId(self, measid, config, param):  # pylint: disable=C0103
        """deprecated"""
        return self.get_parameter_value_of_meas_id(measid, config, param)

    @deprecated('get_parameter_workflow_id_of_meas_id')
    def GetParameterWorkflowIdOfMeasId(self, measid, config, param):  # pylint: disable=C0103
        """deprecated"""
        return self.get_parameter_workflow_id_of_meas_id(measid, config, param)


# ====================================================================
# Parameters DB Library SQL Server Compact Implementation
# ====================================================================
class PluginParDB(BaseParDB, PluginBaseDB):  # pylint: disable=R0904
    """used by plugin finder"""
    def __init__(self, *args, **kwargs):
        """some comment is missing"""
        BaseParDB.__init__(self, *args, **kwargs)


class SQLCEParDB(BaseParDB, PluginBaseDB):  # pylint: disable=R0904
    """SQL Server Compact Edition Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseParDB.__init__(self, *args, **kwargs)


class OracleParDB(BaseParDB, PluginBaseDB):  # pylint: disable=R0904
    """Oracle Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseParDB.__init__(self, *args, **kwargs)


class SQLite3ParDB(BaseParDB, PluginBaseDB):  # pylint: disable=R0904
    """Oracle Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseParDB.__init__(self, *args, **kwargs)


"""
$Log: par.py  $
Revision 1.6 2016/08/16 16:01:42CEST Hospes, Gerd-Joachim (uidv8815) 
fix epydoc errors
Revision 1.5 2016/08/16 12:26:25CEST Hospes, Gerd-Joachim (uidv8815)
update module and class docu
Revision 1.4 2015/07/14 13:18:53CEST Mertens, Sven (uidv7805)
reverting some changes
- Added comments -  uidv7805 [Jul 14, 2015 1:18:54 PM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.3 2015/07/14 09:31:42CEST Mertens, Sven (uidv7805)
simplify for plugin finder
--- Added comments ---  uidv7805 [Jul 14, 2015 9:31:42 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.2 2015/04/30 11:09:34CEST Hospes, Gerd-Joachim (uidv8815)
merge last changes
--- Added comments ---  uidv8815 [Apr 30, 2015 11:09:35 AM CEST]
Change Package : 330394:1 http://mks-psad:7002/im/viewissue?selection=330394
Revision 1.1 2015/04/23 19:04:17CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/par/project.pj
Revision 1.25 2015/04/27 14:35:11CEST Mertens, Sven (uidv7805)
ident string fix
--- Added comments ---  uidv7805 [Apr 27, 2015 2:35:12 PM CEST]
Change Package : 329312:2 http://mks-psad:7002/im/viewissue?selection=329312
Revision 1.24 2015/03/09 11:52:11CET Ahmed, Zaheer (uidu7634)
passing error_tolerance as keyword argument
--- Added comments ---  uidu7634 [Mar 9, 2015 11:52:12 AM CET]
Change Package : 314217:1 http://mks-psad:7002/im/viewissue?selection=314217
Revision 1.23 2015/03/05 14:25:22CET Mertens, Sven (uidv7805)
parameter adaptation
--- Added comments ---  uidv7805 [Mar 5, 2015 2:25:23 PM CET]
Change Package : 312989:1 http://mks-psad:7002/im/viewissue?selection=312989
Revision 1.22 2015/01/19 16:14:37CET Mertens, Sven (uidv7805)
removing unneeded calls
Revision 1.21 2014/12/04 21:36:11CET Ellero, Stefano (uidw8660)
Removed all db.par based deprecated function usage inside stk and module tests (included also some code clean-up).
--- Added comments ---  uidw8660 [Dec 4, 2014 9:36:12 PM CET]
Change Package : 286454:1 http://mks-psad:7002/im/viewissue?selection=286454
Revision 1.20 2014/10/31 10:53:20CET Hospes, Gerd-Joachim (uidv8815)
cleanup
--- Added comments ---  uidv8815 [Oct 31, 2014 10:53:21 AM CET]
Change Package : 275077:1 http://mks-psad:7002/im/viewissue?selection=275077
Revision 1.19 2014/08/22 13:30:03CEST Ahmed, Zaheer (uidu7634)
improve Doc
--- Added comments ---  uidu7634 [Aug 22, 2014 1:30:03 PM CEST]
Change Package : 245349:3 http://mks-psad:7002/im/viewissue?selection=245349
Revision 1.18 2014/08/22 13:00:54CEST Ahmed, Zaheer (uidu7634)
Improved epy documentation
--- Added comments ---  uidu7634 [Aug 22, 2014 1:00:54 PM CEST]
Change Package : 245349:3 http://mks-psad:7002/im/viewissue?selection=245349
Revision 1.17 2014/08/06 10:00:55CEST Hecker, Robert (heckerr)
updated to new naming convensions.
--- Added comments ---  heckerr [Aug 6, 2014 10:00:56 AM CEST]
Change Package : 253983:1 http://mks-psad:7002/im/viewissue?selection=253983
Revision 1.16 2013/11/25 14:39:36CET Ahmed, Zaheer (uidu7634)
fixed pep8 and pylint errors
Added GetParameterDescription functio to return record
--- Added comments ---  uidu7634 [Nov 25, 2013 2:39:36 PM CET]
Change Package : 192744:1 http://mks-psad:7002/im/viewissue?selection=192744
Revision 1.15 2013/07/29 08:44:41CEST Raedler, Guenther (uidt9430)
- revert changes of rev. 1.14
--- Added comments ---  uidt9430 [Jul 29, 2013 8:44:42 AM CEST]
Change Package : 191735:1 http://mks-psad:7002/im/viewissue?selection=191735
Revision 1.14 2013/07/04 15:01:47CEST Mertens, Sven (uidv7805)
providing tableSpace to BaseDB for what sub-schema space each module
is intended to be responsible
--- Added comments ---  uidv7805 [Jul 4, 2013 3:01:47 PM CEST]
Change Package : 185933:3 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.13 2013/04/26 10:46:10CEST Mertens, Sven (uidv7805)
moving strIdent
--- Added comments ---  uidv7805 [Apr 26, 2013 10:46:11 AM CEST]
Change Package : 179495:4 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.12 2013/04/25 14:35:13CEST Mertens, Sven (uidv7805)
epydoc adaptation to colon instead of at
Revision 1.11 2013/04/19 13:37:15CEST Hecker, Robert (heckerr)
Functionality reverted to revision 1.9.
--- Added comments ---  heckerr [Apr 19, 2013 1:37:16 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.10 2013/04/12 14:37:06CEST Mertens, Sven (uidv7805)
adding a short representation used by db_connector.PostInitialize
--- Added comments ---  uidv7805 [Apr 12, 2013 2:37:07 PM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.9 2013/04/03 08:02:18CEST Mertens, Sven (uidv7805)
pylint: minor error, warnings fix
--- Added comments ---  uidv7805 [Apr 3, 2013 8:02:18 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.8 2013/04/02 10:05:34CEST Raedler, Guenther (uidt9430)
- use logging for all log messages again
- use specific indeitifier names
- removed some pylint warnings
--- Added comments ---  uidt9430 [Apr 2, 2013 10:05:34 AM CEST]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.7 2013/03/26 16:19:38CET Mertens, Sven (uidv7805)
pylint: using direct imports, no stars any more
--- Added comments ---  uidv7805 [Mar 26, 2013 4:19:39 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.6 2013/03/21 17:22:39CET Mertens, Sven (uidv7805)
solving some pylint warnings / errors
--- Added comments ---  uidv7805 [Mar 21, 2013 5:22:40 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.5 2013/03/04 07:47:26CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 4, 2013 7:47:28 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2013/02/28 08:12:22CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:22 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/27 16:19:58CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 27, 2013 4:19:59 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/19 14:07:31CET Raedler, Guenther (uidt9430)
- database interface classes derives from common classes for oracle, ...
- use common exception classes
- use common db functions
--- Added comments ---  uidt9430 [Feb 19, 2013 2:07:32 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/02/11 09:59:24CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/db/par/project.pj
Revision 1.5 2012/04/13 09:16:23CEST Spruck, Jochen (spruckj)
- If the parameter is updated, update the timestamp
- Add GetParameterWorkflowID function
- Add GetParameterWorkflowIdOfMeasId function
--- Added comments ---  spruckj [Apr 13, 2012 9:16:23 AM CEST]
Change Package : 98074:2 http://mks-psad:7002/im/viewissue?selection=98074
Revision 1.4 2012/03/09 11:40:19CET Farcas-EXT, Florian Radu (uidu4753)
Changed the return type for GetParameterValueOfMeasId for be value instead of record
--- Added comments ---  uidu4753 [Mar 9, 2012 11:40:19 AM CET]
Change Package : 100439:1 http://mks-psad:7002/im/viewissue?selection=100439
Revision 1.3 2012/03/05 10:29:08CET Farcas-EXT, Florian Radu (uidu4753)
Corrected id return value
--- Added comments ---  uidu4753 [Mar 5, 2012 10:29:08 AM CET]
Change Package : 100439:1 http://mks-psad:7002/im/viewissue?selection=100439
Revision 1.2 2012/02/29 10:33:47CET Farcas-EXT, Florian Radu (uidu4753)
Corrected the timestamp usage and the comments
--- Added comments ---  uidu4753 [Feb 29, 2012 10:33:47 AM CET]
Change Package : 100439:1 http://mks-psad:7002/im/viewissue?selection=100439
Revision 1.1 2012/02/28 16:39:24CET Farcas-EXT, Florian Radu (uidu4753)
Initial revision
Member added to project /nfs/projekte1/PROJECTS/ARS301/06_Algorithm/
    05_Testing/05_Test_Environment/algo/ars301_req_test/valf_tests/adas_database/par/project.pj
"""
