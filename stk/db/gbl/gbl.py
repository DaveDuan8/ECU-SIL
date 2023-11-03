"""
stk/db/gbl/gbl.py
-----------------

Classes for Database access of Global Definition Tables.

Sub-Scheme GBL

**User-API**
    - `BaseGblDB`
        global definition tables like constants, units, db users

The other classes in this module are handling the different DB types and are derived from BaseGblDB.

**usage in Valf suites**

For validation suites based on `Valf` class there is the operator `DbLinker` setting up all needed connections.

**using several connections in parallel**

If several sub-schemes have to be used in parallel the first connection should be reused.
Please check class `BaseGblDB` for more detail.

**Do not waste the limited number of connections to Oracle DB**
by setting up a new connection for each sub-scheme,
always use the existing one as described in `BaseGblDB`.

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.12 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/11/13 17:09:34CET $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from stk.util.helper import deprecated

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.db.db_common import BaseDB, DB_FUNC_NAME_LOWER, ERROR_TOLERANCE_LOW, AdasDBError, PluginBaseDB
from stk.db.db_sql import GenericSQLStatementFactory, SQLBinaryExpr, SQLFuncExpr, OP_EQ, SQLLiteral, OP_IS, OP_OR, \
    OP_AND, SQLColumnExpr, SQLTableExpr, OP_AS
from stk.valf.signal_defs import DBGBL

# =====================================================================================================================
# Constants
# =====================================================================================================================

# Table base names:
TABLE_NAME_WORKFLOW = "GBL_Workflow"
TABLE_NAME_USERS = "GBL_Users"
TABLE_NAME_UNITS = "GBL_Units"
TABLE_NAME_TR_TYPE = "GBL_ValObserver"
TABLE_NAME_VALTYPES = "GBL_ValTypes"
TABLE_NAME_ASSESSMENT_STATE = "GBL_Assessment_State"
TABLE_NAME_PROJECT = "GBL_PROJECT"
TABLE_NAME_HPCSERVER = "GBL_HPCSERVER"
TABLE_NAME_PRIORITIES = "GBL_PRIORITIES"
TABLE_NAME_COMPONENTS = "GBL_COMPONENTS"
TABLE_NAME_TESTTYPE = "GBL_TESTTYPE"
TABLE_NAME_LOCATION = "GBL_LOCATION"

# Workflow Table
COL_NAME_WORKFLOW_WFID = "WFID"
COL_NAME_WORKFLOW_NAME = "NAME"
COL_NAME_WORKFLOW_DESC = "DESCRIPTION"

# Assessment State Table
COL_NAME_ASSESSMENT_STATE_ASSID = "ASSSTID"
COL_NAME_ASSESSMENT_STATE_NAME = "NAME"
COL_NAME_ASSESSMENT_STATE_DESCRIPTION = "DESCRIPTION"
COL_NAME_ASSESSMENT_STATE_VALOBS_TYPEID = "VALOBS_TYPEID"
# User Table
COL_NAME_USER_ID = "USERID"
COL_NAME_USER_NAME = "NAME"
COL_NAME_USER_LOGIN = "LOGINNAME"
COL_NAME_USER_EMAIL = "EMAIL"
COL_NAME_USER_COLL_ADMIN = "COLL_ADMIN"
COL_NAME_USER_COLL_USER = "COLL_USER"
COL_NAME_USER_CAT_ADMIN = "CAT_ADMIN"
COL_NAME_USER_HD_PREP_USER = "HD_PREP_USER"

# Unit Table
COL_NAME_UNIT_ID = "UNITID"
COL_NAME_UNIT_NAME = "NAME"
COL_NAME_UNIT_TYPE = "TYPE"
COL_NAME_UNIT_LABEL = "LABEL"

# Testrun Type Table
COL_NAME_VO_TYPE_ID = "TYPEID"
COL_NAME_VO_TYPE_NAME = "NAME"
COL_NAME_VO_TYPE_DESC = "DESCRIPTION"

# Value Types Table
COL_NAME_VALTYPE_ID = "VTID"
COL_NAME_VALTYPE_NAME = "NAME"
COL_NAME_VALTYPE_DESC = "DESCRIPTION"

# Project Table
COL_NAME_PROJECT_PID = "PID"
COL_NAME_PROJECT_NAME = "NAME"
COL_NAME_PROJECT_DESC = "DESCRIPTION"

# HPCSERVERS Table
COL_NAME_HPCSERVER_SERVID = "SERVID"
COL_NAME_HPCSERVER_NAME = "NAME"
COL_NAME_HPCSERVER_DESC = "DESCRIPTION"

# PRIORITIES Table
COL_NAME_PRIORITIES_PRID = "PRID"
COL_NAME_PRIORITIES_NAME = "NAME"
COL_NAME_PRIORITIES_DESC = "DESCRIPTION"

# COMPONENTS Table
COL_NAME_COMPONENTS_CMPID = "CMPID"
COL_NAME_COMPONENTS_NAME = "NAME"
COL_NAME_COMPONENTS_DESC = "DESCRIPTION"

#  TESTTYPE Table
COL_NAME_COMPONENTS_TTID = "TTID"
# COL_NAME_COMPONENTS_NAME = "NAME"

# location table
COL_NAME_LOCATION_LOCATION = "LOCATION"
COL_NAME_LOCATION_NAME = "NAME"
COL_NAME_LOCATION_SERVERSHARE = "SERVERSHARE"

DEFAULT_HPC_SERVER = "LUSS013.cw01.contiwan.com"

PRIORITY_HIGH = "high"  # 1
PRIORITY_ABOVE_NORMAL = "above_normal"  # 2
PRIORITY_NORMAL = "normal"  # 3
PRIORITY_BELOW_NORMAL = "below_normal"  # 4
PRIORITY_LOW = "low"  # 5
PRIORITY_DEFAULT = PRIORITY_NORMAL
PRIORITY_DEFAULT_ID = 3
SUB_SCHEME_TAG = "GBL"
GBL_COMPONENT_FEATURE = 7
GBL_TESTTYPE_FEATURE = 8
GBL_USER_ROLE_FEATURE = 9

IDENT_STRING = DBGBL

# =====================================================================================================================
# Constraint DB Library Base Implementation
# =====================================================================================================================


class BaseGblDB(BaseDB):
    """Base implementation of the Rec File Database

    For the first connection to the DB for cat tables just create a new instance of this class like

    .. python::

        from stk.db.gbl import BaseGblDB

        dbgbl = BaseGblDB("MFC4XX")   # or use "ARS4XX", "VGA" or path/name of sqlite file

    If already some connection to another table of the DB is created use that one to speed up your code:

    .. python::

        dbgbl = BaseGblDB(dbxxx.db_connection)

    The connection is closed when the first instance using it is deleted.

    **error_tolerance**

    The setting of an error tolerance level allowes to define if an error during later processing is

    - just listed to the log file (error_tolerance = 3, HIGH) if possible,
      e.g. if it can return the existing id without changes in case of adding an already existing entry
    - raising an AdasDBError immediately (error_tolerance < 1, LOW)

    More optional keywords are described at `BaseDB` class initialization.

    """
    # =================================================================================================================
    # Constraint DB Library Interface for public use
    # =================================================================================================================

    # =================================================================================================================
    # Handling of database
    # =================================================================================================================

    def __init__(self, *args, **kwargs):
        """
        Constructor to initialize BaseGblDB to represent GBL subschema

        :keyword db_connection: The database connection to be used
        :type db_connection: cx_oracle.Connection, pydodbc.Connection, sqlite3.Connection, sqlce.Connection
        :keyword table_prefix: The table name prefix which is usually master schema name
        :type table_prefix: str
        :keyword sql_factory: SQL Query building factory
        :type sql_factory: GenericSQLStatementFactory
        :keyword error_tolerance: Error tolerance level based on which some error are exceptable
        :type error_tolerance: int
        """
        kwargs['strIdent'] = DBGBL
        #  cache by unit name name as key and unit Id as value
        self._gbl_unitid_cache = {}
        #  cache by work flow name as key and record as value
        self._gbl_worklfow_cache = {}
        #  cache by obsertype Id as key and assessment state record as value
        self._assess_state_byobstypeid_cache = {}
        #  cache by assessment state name with obsertype Id null as key and assessment state id as value
        self._asses_stateid_byname_cache = {}

        # cache by observer name as key with obstypeid as value
        self._obstypeid_byname_cache = {}
        # cache by user by SQL condition as key and record as value
        self._gbl_user_by_sqlcond_cache = {}
        BaseDB.__init__(self, *args, **kwargs)

    # ====================================================================
    # Handling of workflow
    # ====================================================================
    def add_workflow(self, workflow):
        """
        Add workflow state to database.

        :param workflow: The workflow record
        :type workflow: dict
        :return: Returns the workflow ID.
        :rtype: int
        """

        cond = self._get_workflow_condition(workflow[COL_NAME_WORKFLOW_NAME])

        entries = self.select_generic_data(table_list=[TABLE_NAME_WORKFLOW], where=cond)
        if len(entries) <= 0:
            wfid = self._get_next_id(TABLE_NAME_WORKFLOW, COL_NAME_WORKFLOW_WFID)
            workflow[COL_NAME_WORKFLOW_WFID] = wfid
            self.add_generic_data(workflow, TABLE_NAME_WORKFLOW)
            return wfid
        else:
            tmp = "Workflow '%s' exists already in the generic label database" % workflow[COL_NAME_WORKFLOW_NAME]
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError(tmp)
            else:
                self._log.warning(tmp)
                if len(entries) == 1:
                    return entries[0][COL_NAME_WORKFLOW_WFID]
                elif len(entries) > 1:
                    tmp = "Worflow name '%s' " % workflow[COL_NAME_WORKFLOW_NAME]
                    tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
                    raise AdasDBError(tmp)

    def update_workflow(self, workflow, where=None):
        """
        Update existing workflow records.

        :param workflow: The workflow record with new values
        :type workflow: dict
        :param where: SQL condition for update
        :type where: SQLBinaryExpression
        :return: Returns the number of affected workflow.
        :rtype: int
        """

        rowcount = 0

        if where is None:
            where = self._get_workflow_condition(workflow[COL_NAME_WORKFLOW_NAME])

        if (workflow is not None) and (len(workflow) != 0):
            rowcount = self.update_generic_data(workflow, TABLE_NAME_WORKFLOW, where)
        # done
        return rowcount

    def delete_workflow(self, workflow):
        """
        Delete workflow entry from database

        :param workflow: Delete existing workflow record must contain Workflow ID
        :type workflow: dict
        :return: Returns the number of rows deleted.
        :rtype: int
        """

        rowcount = 0
        if (workflow is not None) and (len(workflow) != 0):
            cond = self._get_workflow_condition(workflow[COL_NAME_WORKFLOW_NAME])
            rowcount = self.delete_generic_data(TABLE_NAME_WORKFLOW, where=cond)
        # done
        return rowcount

    def get_workflow(self, name):
        """
        Work Flow Record for the given Name

        :param name: work flow name
        :type name: int
        :return: Return Dictionary representing single record if there exist single in database
                 otherwise return empty dictionary with warning message
        :rtype: dict
        """
        record = {}
        if name.lower() in self._gbl_worklfow_cache:
            return self._gbl_worklfow_cache[name.lower()]

        cond = self._get_workflow_condition(name)

        entries = self.select_generic_data(table_list=[TABLE_NAME_WORKFLOW], where=cond)
        if len(entries) <= 0:
            self._log.warning(str("Worflow with name '%s' does not exists in the global  database." % name))
        elif len(entries) > 1:
            self._log.warning(str("Worflow with name '%s' cannot be resolved because it is ambiguous. (%s)"
                                  % (name, entries)))
        else:
            record = entries[0]
            self._gbl_worklfow_cache[name.lower()] = record
        # done
        return record

    def get_workflow_name(self, wfid):
        """Get existing workflow records by id.

        :param wfid: The id of workflow.
        :type wfid: int
        :return: Returns workflow name if found otherwise return empty dictionary with warning message
        :rtype: str | dict
        """
        cond = SQLBinaryExpr(COL_NAME_WORKFLOW_WFID, OP_EQ, wfid)

        entries = self.select_generic_data(select_list=[COL_NAME_WORKFLOW_NAME],
                                           table_list=[TABLE_NAME_WORKFLOW], where=cond)
        if len(entries) <= 0:
            self._log.warning(str("Workflow with id '%d' does not exists in the global database." % wfid))
            return {}

        return entries[0][COL_NAME_WORKFLOW_NAME]

    def _get_workflow_condition(self, name):
        """
        Function to Generate where SQL condition for Global WorkFlow table

        :param name: workflow name
        :type name: str
        :return: Returns the condition expression
        :rtype: SQLBinaryExpression
        """
        return SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER], COL_NAME_WORKFLOW_NAME),
                             OP_EQ, SQLLiteral(name.lower()))

    # ====================================================================
    # Handling of assessment
    # ====================================================================
    def add_assessment_state(self, ass_state):
        """
        Add Assessment state to database.

        :param ass_state: The Assessment State record to be added.
        :type ass_state: Dictionary
        :return: Returns the AssessmentState ID if the record already exist returns its ID
        :rtype: int
        """
        obs_type_id = None
        if COL_NAME_ASSESSMENT_STATE_VALOBS_TYPEID in ass_state:
            obs_type_id = ass_state[COL_NAME_ASSESSMENT_STATE_VALOBS_TYPEID]
        cond = self._get_assessment_state_condition(name=ass_state[COL_NAME_ASSESSMENT_STATE_NAME],
                                                    observer_type_id=obs_type_id)

        entries = self.select_generic_data(table_list=[TABLE_NAME_ASSESSMENT_STATE], where=cond)
        if len(entries) <= 0:
            # ass_state_id = self._get_next_id(TABLE_NAME_ASSESSMENT_STATE, COL_NAME_ASSESSMENT_STATE_ASSID)
            # ass_state[COL_NAME_ASSESSMENT_STATE_ASSID] = ass_state_id
            self.add_generic_data(ass_state, TABLE_NAME_ASSESSMENT_STATE)

            entries = self.select_generic_data(table_list=[TABLE_NAME_ASSESSMENT_STATE], where=cond)
            if len(entries) == 1:
                return entries[0][COL_NAME_ASSESSMENT_STATE_ASSID]
            else:
                tmp = "Assessment State name '%s' " % (ass_state[COL_NAME_ASSESSMENT_STATE_NAME])
                tmp += "cannot be added to database. (%s)" % entries
                raise AdasDBError(tmp)
        else:
            tmp = "Assessment State '%s' " % ass_state[COL_NAME_ASSESSMENT_STATE_NAME]
            tmp += "exists already in the generic label database"
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError(tmp)
            else:
                self._log.warning(tmp)
                if len(entries) == 1:
                    return entries[0][COL_NAME_ASSESSMENT_STATE_ASSID]
                elif len(entries) > 1:
                    tmp = "Assessment State name '%s' " % (ass_state[COL_NAME_ASSESSMENT_STATE_NAME])
                    tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
                    raise AdasDBError(tmp)

    def get_assessment_state(self, name=None, assstid=None, observer_type_id=None):
        """
        Get Assessment State record(s) based on arguments passed

        :param name: Workflow Name
        :type name: str
        :param assstid: Assessment State ID
        :type assstid: int
        :param observer_type_id: Observer Type Id
        :type observer_type_id: int
        :return: return records from Global Assessment Table
        :rtype: list
        """

        cond = self._get_assessment_state_condition(name=name, assstid=assstid, observer_type_id=observer_type_id)
        if str(cond) in self._assess_state_byobstypeid_cache:
            return self._assess_state_byobstypeid_cache[str(cond)]
        entries = self.select_generic_data(table_list=[TABLE_NAME_ASSESSMENT_STATE], where=cond)
        if len(entries) <= 0:
            self._log.warning(str("Assessment with name '%s' does not exists in the global  database." % name))

        self._assess_state_byobstypeid_cache[str(cond)] = entries
        return entries

    def get_assessment_state_id(self, name, observer_type_id=None):
        """
        Get Assessment State Id

        :param name: Assessment name
        :type name: str
        :param observer_type_id: Observer Type Id
        :type observer_type_id: str
        :return: Returns the Assessment State Id not record found then raise AdasDBError
        :rtype: int
        """
        entries = self.get_assessment_state(name=name, observer_type_id=observer_type_id)
        # done
        if len(entries) == 1:
            return int(entries[0][COL_NAME_ASSESSMENT_STATE_ASSID])
        elif len(entries) > 1:
            tmp = "Assessment with name '%s' " % name
            tmp += "for ObserverID %s " % (str(observer_type_id))
            tmp += "cannot be resolved because it is ambiguous."
            raise AdasDBError(tmp)

    def _get_assessment_state_condition(self, name=None, assstid=None, observer_type_id=None):
        """
        Get the condition SQL expression to access the workflow.

        :param name: Assessment state name
        :type name: str
        :param assstid: Assessment State Id
        :type assstid: int
        :param observer_type_id: Observer Type Id
        :type observer_type_id: int
        :return: Returns the condition expression
        :rtype: SQLBinaryExpression
        """
        cond = None
        if assstid is not None:
            cond = SQLBinaryExpr(COL_NAME_ASSESSMENT_STATE_ASSID, OP_EQ, assstid)
        else:
            if name is not None:
                cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                 COL_NAME_ASSESSMENT_STATE_NAME),
                                     OP_EQ, SQLLiteral(name.lower()))

            if observer_type_id is not None:
                cond_obs1 = SQLBinaryExpr(COL_NAME_ASSESSMENT_STATE_VALOBS_TYPEID, OP_EQ, observer_type_id)
                cond_obs2 = SQLBinaryExpr(COL_NAME_ASSESSMENT_STATE_VALOBS_TYPEID, OP_IS, 'null')
                cond_obs = SQLBinaryExpr(cond_obs1, OP_OR, cond_obs2)
                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_obs)
                else:
                    cond = cond_obs
        return cond

    # ====================================================================
    # Handling of Users
    # ====================================================================
    def add_user(self, user):
        """
        Add User entry into GBL_USERS table

        :param user: user record to be insert
        :type user: dict
        :return: Returns the user ID.
        :rtype: int
        """
        cond = self._get_user_condition(login=user[COL_NAME_USER_LOGIN])

        entries = self.select_generic_data(table_list=[TABLE_NAME_USERS], where=cond)
        if len(entries) <= 0:
            uid = self._get_next_id(TABLE_NAME_USERS, COL_NAME_USER_ID)
            user[COL_NAME_USER_ID] = uid
            self.add_generic_data(user, TABLE_NAME_USERS)
            return uid
        else:
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError("User '%s' exists already in the global database" % user[COL_NAME_USER_LOGIN])
            else:
                self._log.warning(str("User '%s' already exists in the global database." % user[COL_NAME_USER_LOGIN]))
                if len(entries) == 1:
                    return entries[0][COL_NAME_USER_ID]
                elif len(entries) > 1:
                    tmp = "User name '%s' " % (user[COL_NAME_USER_LOGIN])
                    tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
                    raise AdasDBError(tmp)

    def update_user(self, user, where=None):
        """
        Update existing user record

        :param user: User record representing new values
        :type user: dict
        :param where: SQL condition based on which records are update.
                      if the condition is not passed then condition will be created from User name specified in record
        :type where: SQLBinaryExpression
        :return: No of rows updated
        :rtype: int
        """
        rowcount = 0

        if where is None:
            if COL_NAME_USER_ID in user:
                where = self._get_user_condition(user_id=user[COL_NAME_USER_ID])
            elif COL_NAME_USER_LOGIN in user:
                where = self._get_user_condition(login=user[COL_NAME_USER_LOGIN])
            elif COL_NAME_USER_NAME in user:
                where = self._get_user_condition(name=user[COL_NAME_USER_NAME])
            else:
                self._log.error("update failed: Couldn't determine where condition for update user record")
                return
        if (user is not None) and (len(user) != 0):
            rowcount = self.update_generic_data(user, TABLE_NAME_USERS, where)
#             Clear cache because record is update
            self._gbl_user_by_sqlcond_cache = {}
        # done
        return rowcount

    def delete_user(self, user):
        """
        Delete user record from GBL_USERS table in database

        :param user: user record to be deleted containing User name
        :type user: dict
        :return: No of rows deleted
        :rtype: int
        """
        rowcount = 0
        if user is not None and len(user) != 0:
            cond = self._get_user_condition(user[COL_NAME_USER_NAME])
            rowcount = self.delete_generic_data(TABLE_NAME_USERS, where=cond)
#             Clear cache because record is deleted
            self._gbl_user_by_sqlcond_cache = {}
        # done
        return rowcount

    def get_user(self, name=None, login=None, user_id=None):
        """
        Get user record based on passed parameter(s)

        :param name: Name of the person
        :type name: str
        :param login: Windows login name
        :type login: str
        :param user_id: User Id as Primary key in GBL_USER table
        :type user_id: int
        :return: Return database single record or multiple records with Warning message
                 If no record exist then return None with Warning message
        :rtype: dict | list | None
        """
        record = {}
        cond = self._get_user_condition(name, login, user_id)
        if str(cond) in self._gbl_user_by_sqlcond_cache:
            return self._gbl_user_by_sqlcond_cache[str(cond)]
        else:

            entries = self.select_generic_data(table_list=[TABLE_NAME_USERS], where=cond)
            if len(entries) <= 0:
                self._log.warning(str("User with name '%s' does not exists in the global  database." % name))
            elif len(entries) > 1:
                self._log.warning(str("User with name '%s' cannot be resolved because it is ambiguous. (%s)"
                                      % (name, entries)))
            else:
                record = entries[0]
                self._gbl_user_by_sqlcond_cache[str(cond)] = record
            # done
            return record

    def is_coll_admin(self, name=None, login=None, user_id=None):
        """
        Get boolean flag whether the user is collection admin or not
        :param name: Name of the person
        :type name: str
        :param login: Windows login name
        :type login: str
        :param user_id: User Id as Primary key in GBL_USER table
        :type user_id: int
        :return: return True if the user is collection admin otherwise False
        :rtype: Boolean
        """

        return self.get_user_access_role(COL_NAME_USER_COLL_ADMIN, name=name,
                                         login=login, user_id=user_id)

    def is_coll_user(self, name=None, login=None, user_id=None):
        """
        Get boolean flag whether the user is collection user or not
        :param name: Name of the person
        :type name: str
        :param login: Windows login name
        :type login: str
        :param user_id: User Id as Primary key in GBL_USER table
        :type user_id: int
        :return: return True if the user is collection user otherwise False
        :rtype: Boolean
        """

        return self.get_user_access_role(COL_NAME_USER_COLL_USER, name=name,
                                         login=login, user_id=user_id)

    def is_catalog_admin(self, name=None, login=None, user_id=None):
        """
        Get boolean flag whether the user is catalog admin or not
        :param name: Name of the person
        :type name: str
        :param login: Windows login name
        :type login: str
        :param user_id: User Id as Primary key in GBL_USER table
        :type user_id: int
        :return: return True if the user is catalog admin otherwise False
        :rtype: Boolean
        """

        return self.get_user_access_role(COL_NAME_USER_CAT_ADMIN, name=name,
                                         login=login, user_id=user_id)

    def is_hdprep_user(self, name=None, login=None, user_id=None):
        """
        Get boolean flag whether the user is catalog admin or not
        :param name: Name of the person
        :type name: str
        :param login: Windows login name
        :type login: str
        :param user_id: User Id as Primary key in GBL_USER table
        :type user_id: int
        :return: return True if the user is catalog admin otherwise False
        :rtype: Boolean
        """

        return self.get_user_access_role(COL_NAME_USER_HD_PREP_USER, name=name,
                                         login=login, user_id=user_id)

    def get_user_access_role(self, role_column, name=None, login=None, user_id=None):
        """
        Get boolean flag whether the user has any roles as specified in parameter
        :param role_column: Column name represent user role
        :type role_column: String
        :param name: Name of the person
        :type name: str
        :param login: Windows login name
        :type login: str
        :param user_id: User Id as Primary key in GBL_USER table
        :type user_id: int
        :return: return True if the user is has specified role otherwise False
        :rtype: Boolean
        """
        if self.sub_scheme_version >= GBL_USER_ROLE_FEATURE:
            record = self.get_user(name=name, login=login, user_id=user_id)
            if COL_NAME_USER_ID in record and int(record[role_column]) == 1:
                return True
        else:
            self._log.warning("user role management feature not available in database")
        return False

    def set_user_access_role(self, role_column, grant_flag, login=None, user_id=None):
        """
        Generic function to grant to revoke user role
        :param role_column: Column name represent specific user role
        :type role_column: String
        :param login: Windows login name
        :type login: str
        :param grant_flag: Flag as integer where 1 means grant 0 means revoke
        :type grant_flag: int
        :param user_id: User Id as Primary key in GBL_USER table
        :type user_id: int
        :return: return True if the grant or revoke for desired user was sucessfull otherwise false
        :rtype: Boolean
        """
        if self.sub_scheme_version >= GBL_USER_ROLE_FEATURE:
            record = self.get_user(login=login, user_id=user_id)
            if role_column in record:
                record[role_column] = grant_flag
                self.update_user(record)
                return True
            else:
                self._log.warning("user doesn't exist in database")
        else:
            self._log.warning("user role management feature not available in database")
        return False

    def get_user_id(self, name=None, login=None, user_id=None):
        """
        Get user Id primary key for passed parameter(s)

        :param name: Name of the person
        :type name: str
        :param login: Windows login name
        :type login: str
        :param user_id: User Id as Primary key in GBL_USER table
        :type user_id: int
        :return: Return database single record or multiple records with Warning message
                 If no record exist then return None with Warning message
        :rtype: str | None
        """
        record = self.get_user(name=name, login=login, user_id=user_id)
        if COL_NAME_USER_ID in record:
            return record[COL_NAME_USER_ID]
        else:
            return None

    def get_all_users(self):
        """
        Get all existing user names.

        :return: Returns the user name list.
        :rtype: list
        """
        record = []

        select_list = [SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_USERS),
                                                   COL_NAME_USER_NAME), OP_AS, COL_NAME_USER_NAME)]

        entries = self.select_generic_data(select_list=select_list, table_list=[TABLE_NAME_USERS])
        if len(entries) <= 0:
            self._log.warning("No Users defined in database.")
        else:
            for item in entries:
                record.append(item[COL_NAME_USER_NAME])
        # done
        return record

    def _get_user_condition(self, name=None, login=None, user_id=None):
        """
        Get the condition expression to access the user record.

        :param name: Name of the user
        :type name: str
        :param login: windows login name
        :type login: str
        :param user_id: user identifier which is primary key in GBL_USERS table inside database
        :type user_id: int
        :return: Returns the condition expression
        :rtype: SQLBinaryExpression
        """
        cond = None

        if user_id is not None:
            cond = SQLBinaryExpr(COL_NAME_USER_ID, OP_EQ, user_id)

        else:
            if name is not None:
                cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                 COL_NAME_USER_NAME),
                                     OP_EQ, SQLLiteral(name.lower()))

            if login is not None:
                cond_ln = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                    COL_NAME_USER_LOGIN),
                                        OP_EQ, SQLLiteral(login.lower()))

                if cond is not None:
                    cond = SQLBinaryExpr(cond, OP_AND, cond_ln)
                else:
                    cond = cond_ln
        return cond

    # ====================================================================
    # Handling of Units
    # ====================================================================
    def add_unit(self, unit):
        """
        Add unit to database.

        :param unit: The unit record.
        :type unit: dict
        :return: Returns the unit ID.
        :rtype: int
        """
        cond = self._get_unit_condition(unit[COL_NAME_UNIT_NAME])

        entries = self.select_generic_data(table_list=[TABLE_NAME_UNITS], where=cond)
        if len(entries) <= 0:
            uid = self._get_next_id(TABLE_NAME_UNITS, COL_NAME_UNIT_ID)
            unit[COL_NAME_UNIT_ID] = uid
            self.add_generic_data(unit, TABLE_NAME_UNITS)
            return uid
        else:
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError("Unit '%s' exists already in the global database" % unit[COL_NAME_UNIT_NAME])
            else:
                self._log.warning(str("Unit '%s' already exists in the global database." % unit[COL_NAME_UNIT_NAME]))
                if len(entries) == 1:
                    return entries[0][COL_NAME_UNIT_ID]
                elif len(entries) > 1:
                    tmp = "Unit '%s' " % (unit[COL_NAME_UNIT_NAME])
                    tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
                    raise AdasDBError(tmp)

    def update_unit(self, unit, where=None):
        """
        Update existing unit records.

        :param unit: The unit record containing new values
        :type unit: dict
        :param where: The condition to be fulfilled by the unit to the updated. if not passed then default will
            be create from Unit Name
        :type where: SQLBinaryExpression
        :return: Returns the number of affected units.
        :rtype: int
        """
        rowcount = 0

        if where is None:
            where = self._get_unit_condition(unit[COL_NAME_UNIT_NAME])

        if unit is not None and len(unit) != 0:
            rowcount = self.update_generic_data(unit, TABLE_NAME_UNITS, where)
        # done
        return rowcount

    def delete_unit(self, unit):
        """
        Delete existing unit records.

        :param unit: The unit record to be deleted containing unit name
        :type unit: dict
        :return: Returns the number of affected units.
        :rtype: int
        """
        rowcount = 0
        if unit is not None and len(unit) != 0:
            cond = self._get_unit_condition(unit[COL_NAME_UNIT_NAME])
            rowcount = self.delete_generic_data(TABLE_NAME_UNITS, where=cond)
        # done
        return rowcount

    def get_unit(self, name=None, uid=None):
        """
        Get existing unit record from GBL_UNIT based on a criteria with passed argument(s).

        :param name: The unit name (optional)
        :type name: str
        :param uid: The unit Identifier (optional)
        :type uid: int
        :return: Returns the unit record. If no record or multiple records are found
                 then None will be return with warning message
        :rtype: dict | None
        """
        record = None
        cond = self._get_unit_condition(name, uid)

        entries = self.select_generic_data(table_list=[TABLE_NAME_UNITS], where=cond)
        if len(entries) <= 0:
            self._log.debug(str("Unit with name '%s' does not exists in the global  database." % name))
        elif len(entries) > 1:
            if name is not None or uid is not None:
                self._log.warning(str(("Unit with name '%s' cannot be resolved " % name) +
                                      ("because it is ambiguous. (%s)" % entries)))
            else:
                record = entries
        else:
            record = entries[0]
        # done
        return record

    def get_unit_id_by_name(self, name):
        """
        Get the Unit Id by the given name

        :param name: Name of the unit
        :type name: str
        :return: Return Unit Id such name exist otherwise raise AdasDBError
        :rtype: int
        """
        if name.lower() in self._gbl_unitid_cache:
            return self._gbl_unitid_cache[name.lower()]
        record = self.get_unit(name=name)
        if record is not None:
            self._gbl_unitid_cache[name.lower()] = record[COL_NAME_UNIT_ID]
            return record[COL_NAME_UNIT_ID]
        else:
            raise AdasDBError("Unit with name '%s' does not exists in the global  database." % name)

    def _get_unit_condition(self, name=None, uid=None):
        """
        Get the SQL condition expression GBL_UNIT table

        :param name: Name of the workflow
        :type name: str
        :param uid: Unit Identifier which primary key of the table
        :type uid: int
        :return: Returns the condition expression
        :rtype: SQLBinaryExpression
        """
        cond = None
        if name is not None:
            cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                 COL_NAME_UNIT_NAME), OP_EQ, SQLLiteral(name.lower()))
        elif uid is not None:
            cond = SQLBinaryExpr(COL_NAME_UNIT_ID, OP_EQ, uid)
        return cond

    def get_table_data(self, table, columns=None):
        """
        Get table data and return it in a format suitable for display. Double array.

        :param table: The table name
        :param table: The table name
        :param columns: List of columns to be selected.
        :return: Table data. Field list array and Table data double array.
        """
        if columns is not None:
            select_list = columns
        else:
            select_list = '*'

        table_data = self.select_generic_data_compact(select_list, [table])
        return table_data

    def get_select_data(self, table, columns, field_select, comparitor, value, sort):
        """
        Get table data and return it in a format suitable for display. Double array.

        :param table: The table name
        :type table: str
        :param columns: List of columns to be selected in record(s).
        :type columns: list
        :param field_select: The field to perform the query on.
        :type field_select: str
        :param comparitor: The comparitor eg. ==, >
        :type comparitor: str
        :param value: The value to compare with.
        :type value: str
        :param sort: List of column by which record should be sorted (Currently Unused parameter)
        :type sort: list
        :return: Table data. Field list array and Table data double array.
        :rtype: list
        """
        _ = sort
        cond = SQLBinaryExpr(field_select, comparitor, SQLLiteral(value))

        return self.select_generic_data_compact(columns, [table], where=cond)
        # , order_by=[sort])

    # ====================================================================
    # Handling of Validation Observer Types
    # ====================================================================
    def add_val_observer_type(self, tr_type):
        """
        Add a new observer type to GBL_OBSERVERS table.

        :param tr_type: The observer type dictionary
        :type tr_type: dict
        :return: Returns the observertype ID.
        :rtype: int
        """
        cond = self._get_val_observer_type_condition(tr_type[COL_NAME_VO_TYPE_NAME])
        entries = self.select_generic_data(table_list=[TABLE_NAME_TR_TYPE], where=cond)
        if len(entries) <= 0:
            tr_type_id = self._get_next_id(TABLE_NAME_TR_TYPE, COL_NAME_VO_TYPE_ID)
            tr_type[COL_NAME_VO_TYPE_ID] = tr_type_id
            self.add_generic_data(tr_type, TABLE_NAME_TR_TYPE)
            return tr_type_id
        else:
            # TODO: tr_type will be None in former version and not being a list, please fix!!!
            tmp = "Event type '%s' exists already in the validation result database" % tr_type[COL_NAME_VO_TYPE_NAME]
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError(tmp)
            else:
                self._log.warning(tmp)
                if len(entries) == 1:
                    return entries[0][COL_NAME_VO_TYPE_ID]
                elif len(entries) > 1:
                    tmp = "Event type name '%s' " % (tr_type[COL_NAME_VO_TYPE_NAME])
                    tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
                    raise AdasDBError(tmp)

    def update_val_observer_type(self, tr_type, where=None):
        """
        Update existing Observer type records in GBL_OBSERVERS table.

        :param tr_type: The Observer type record update.
        :type tr_type: dict
        :param where: The condition to be fulfilled based on which record to be update. If not provide then
            observer type name mentioned in tr_type dictionary will be use to create SQL condition
        :type where: SQLBinaryExpression
        :return: Returns the number of effect rows.
        :rtype: int
        """
        rowcount = 0

        if where is None:
            where = self._get_val_observer_type_condition(tr_type[COL_NAME_VO_TYPE_NAME])

        if (tr_type is not None) and (len(tr_type) != 0):
            rowcount = self.update_generic_data(tr_type, TABLE_NAME_TR_TYPE, where)
        # done
        return rowcount

    def delete_val_observer_type(self, tr_type):
        """
        Delete existing Observer type record(s) from GBL_OBSERVERS table

        :param tr_type: - The observer type record to delete.
        :type tr_type: dict
        :return: Returns the number of rows deleted.
        :rtype: int
        """
        rowcount = 0
        if tr_type is not None and len(tr_type) != 0:
            cond = self._get_val_observer_type_condition(tr_type[COL_NAME_VO_TYPE_NAME])
            rowcount = self.delete_generic_data(TABLE_NAME_TR_TYPE, where=cond)
        # done
        return rowcount

    def get_val_observer_type(self, name=None, type_id=None):
        """
        Get Observer type records from database

        :param name: The Observer type name.
        :type name: str
        :param type_id: The Observer type Id
        :type type_id: int
        :return: Returns the Observer type record or list of record if duplicate entries found with warning message
        :rtype: dict | list
        """
        record = {}
        cond = self._get_val_observer_type_condition(name, type_id)
        if str(cond) in self._obstypeid_byname_cache:
            return self._obstypeid_byname_cache[str(cond)]

        entries = self.select_generic_data(table_list=[TABLE_NAME_TR_TYPE], where=cond)
        if len(entries) <= 0:
            self._log.warning(str("Observer Type with name '%s' does not exist in the GBL database." % name))
        elif len(entries) > 1:
            record = entries
            self._obstypeid_byname_cache[str(cond)] = record
        else:
            record = entries[0]
            self._obstypeid_byname_cache[str(cond)] = record
        # done
        return record

    def get_val_observer_type_id(self, name):
        """
        Get the Observer Type ID for given Name

        :param name: Observer Type Name
        :type name: str
        :return: Returns the Observer Type ID
        :rtype: int
        """
        tr_type = self.get_val_observer_type(name)
        if COL_NAME_VO_TYPE_ID in tr_type:
            return int(tr_type[COL_NAME_VO_TYPE_ID])
        else:
            return None

    def _get_val_observer_type_condition(self, name, type_id=None):  # pylint: disable=C0103
        """
        Get the SQL condition expression to GBL_Observer table

        :param name: Observer Name
        :type name: str
        :param type_id: The Observer type Id
        :type type_id: int
        :return: Returns the condition expression
        :rtype: SQLBinaryExpression
        """
        cond = None
        if name is not None:
            cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                             COL_NAME_VO_TYPE_NAME),
                                 OP_EQ, SQLLiteral(name.lower()))
        if type_id is not None:
            cond_type = SQLBinaryExpr(COL_NAME_VO_TYPE_ID, OP_EQ, type_id)
            if cond is None:
                cond = cond_type
            else:
                cond = SQLBinaryExpr(cond, OP_AND, cond_type)
        return cond

    # ====================================================================
    # Handling of Validation Value Types
    # ====================================================================
    def add_value_type(self, type_name, desc):
        """
        Add a new new record to GBL_ValTypes table

        :param type_name: Value type NAME
        :type type_name: str
        :param desc: description of value type
        :type desc: str
        :return: Returns the value type ID for newly inserted record. If an attempt of duplicate entry is made then
                 AdasDBError exception will be raised
        :rtype: int
        """

        # check the function input parameters
        if type_name is None:
            raise AdasDBError("Value type name is not set!")
        if desc is None:
            raise AdasDBError("Value type description is not set!")

        # create record dictionary
        valuetype = {COL_NAME_VALTYPE_ID: 0, COL_NAME_VALTYPE_NAME: type_name, COL_NAME_VALTYPE_DESC: desc}

        # create and execute insert sql query
        cond = self.__get_value_type_condition(valuetype[COL_NAME_VALTYPE_NAME])
        entries = self.select_generic_data(table_list=[TABLE_NAME_VALTYPES], where=cond)
        if len(entries) <= 0:
            vtid = self._get_next_id(TABLE_NAME_VALTYPES, COL_NAME_VALTYPE_ID)
            valuetype[COL_NAME_VALTYPE_ID] = vtid
            self.add_generic_data(valuetype, TABLE_NAME_VALTYPES)
            return vtid
        else:
            tmp = "Value type '%s' exists already in the validation result database" % valuetype[COL_NAME_VALTYPE_NAME]
            raise AdasDBError(tmp)

    def update_value_type(self, type_name, desc):
        """
        Update Value Type

        :param type_name: The value type NAME
        :type type_name: str
        :param desc: The value type DESCRIPTION
        :return: Returns the value type ID or failure will raise AdasDBError
        :rtype: dict
        """
        # check the function input parameters
        if type_name is None:
            raise AdasDBError("Value type name is not set!")
        if desc is None:
            raise AdasDBError("Value type description is not set!")

        # create record dictionary
        valuetype = {COL_NAME_VALTYPE_ID: 0, COL_NAME_VALTYPE_NAME: type_name, COL_NAME_VALTYPE_DESC: desc}

        # create and execute insert sql query
        cond = self.__get_value_type_condition(valuetype[COL_NAME_VALTYPE_NAME])
        entries = self.select_generic_data(table_list=[TABLE_NAME_VALTYPES], where=cond)
        if len(entries) == 1:
            val_type_id = entries[0][COL_NAME_VALTYPE_ID]
            cond = self.__get_value_type_condition(type_id=val_type_id)
            valuetype[COL_NAME_VALTYPE_ID] = val_type_id
            self.update_generic_data(valuetype, TABLE_NAME_VALTYPES, where=cond)
            return val_type_id
        else:
            tmp = "Value type '%s' doesn't exist in the validation result database" % valuetype[COL_NAME_VALTYPE_NAME]
            raise AdasDBError(tmp)

    def delete_value_type(self, type_name):
        """
        Delete existing value type record from database

        :param type_name: The value type name to delete.
        :type type_name: str
        :return: Returns the number of rows deleted.
        :rtype: int
        """
        if type_name is None:
            raise AdasDBError("Value type name is not set!")

        # rowcount = 0
        cond = self.__get_value_type_condition(type_name)
        rowcount = self.delete_generic_data(TABLE_NAME_VALTYPES, where=cond)
        return rowcount

    def get_value_type(self, type_name):
        """
        Get existing value type record by name

        :param type_name: The value type NAME
        :type type_name: str
        :return: Returns the value type record if multiple or no record found
                 then list will be return with warning message
        :rtype: dict | list
        """
        record = {}
        cond = self.__get_value_type_condition(type_name)

        entries = self.select_generic_data(table_list=[TABLE_NAME_VALTYPES], where=cond)
        # TODO: what is type of, please fix???
        if len(entries) <= 0:
            self._log.warning("Value type with name '%s' does not exist in the validation result database." % type)
        elif len(entries) > 1:
            self._log.warning("Value type with name '%s' cannot be resolved because it is ambiguous. (%s)"
                              % (type, entries))
        else:
            record = entries[0]

        return record

    def get_value_type_id(self, type_name):
        """
        Get the Value Type ID for given name

        :param type_name: The value type NAME
        :type type_name: str
        :return: Returns the value type identifier number
        :rtype: int
        """
        value_type = self.get_value_type(type_name)
        if COL_NAME_VALTYPE_ID in value_type:
            return int(value_type[COL_NAME_VALTYPE_ID])
        else:
            return None

    def __get_value_type_condition(self, type_name=None, type_id=None):
        """
        Get the condition expression to access the value type record

        :param type_name: The value type NAME
        :type type_name: str
        :param type_id: The value type Id
        :type type_id: int
        :return: Returns the condition expression
        :rtype: SQLBinaryExpression
        """
        cond = None

        if type_id is not None:
            cond = SQLBinaryExpr(COL_NAME_VALTYPE_ID, OP_EQ, type_id)
        else:
            if type_name is not None:
                cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                 COL_NAME_VALTYPE_NAME),
                                     OP_EQ, SQLLiteral(type_name.lower()))
        return cond

    def add_project(self, proj_name, desc):
        """
        Add a new Project to database.

        :param proj_name: The Project NAME
        :type proj_name: str
        :param desc: Prjoect DESCRIPTION
        :type desc: str
        :return: Returns the project ID.
        :rtype: int
        """
        # check the function input parameters
        if proj_name is None:
            raise AdasDBError("Project name is not set!")
        if desc is None:
            raise AdasDBError("Project description is not set!")

        # create record dictionary
        project = {COL_NAME_PROJECT_PID: 0, COL_NAME_PROJECT_NAME: proj_name, COL_NAME_PROJECT_DESC: desc}

        # create and execute insert sql query
        entries = self.get_project_id(proj_name)
        if entries is None:
            pid = self._get_next_id(TABLE_NAME_PROJECT, COL_NAME_PROJECT_PID)
            project[COL_NAME_PROJECT_PID] = pid
            self.add_generic_data(project, TABLE_NAME_PROJECT)
            return pid
        else:
            tmp = "Project with name '%s' exists already in the validation result database" % proj_name[proj_name]
            raise AdasDBError(tmp)

    def get_project_name(self, pid):
        """
        Get project name corresponding to project ID

        :param pid:  project ID
        :type pid: int
        :return: Returns name of of project. If no record found None is return if multiple record found
            then list of all duplicated Ids will be return
        :rtype: str | list | None
        """
        cond = SQLBinaryExpr(COL_NAME_PROJECT_PID, OP_EQ, pid)
        entries = self.select_generic_data(table_list=[TABLE_NAME_PROJECT], where=cond)
        if len(entries) == 1:
            record = entries[0][COL_NAME_PROJECT_NAME]
        else:
            self._log.warning("Project with id '%s' does not exist or ambiguous in the validation database."
                              % str(pid))
            record = None
        return record

    def get_all_project_name(self):
        """
        Get All the project name from database

        :return: Returns all the list of project names
        :rtype: list
        """
        record = []
        entries = self.select_generic_data(select_list=[COL_NAME_PROJECT_NAME], table_list=[TABLE_NAME_PROJECT])
        for row in entries:
            record.append(row[COL_NAME_PROJECT_NAME])
        return record

    def get_project_id(self, proj_name):
        """
        Get Project Id of the prjoect name

        :param proj_name: name of the project e.g. ARS400
        :type proj_name: str
        :return: If one record found then project Id otherwise with warning message return duplicate entries
            if no record found return None
        :rtype: int | list | None
        """
        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                         COL_NAME_PROJECT_NAME),
                             OP_EQ, SQLLiteral(proj_name.lower()))

        entries = self.select_generic_data(table_list=[TABLE_NAME_PROJECT], where=cond)
        if len(entries) <= 0:
            self._log.warning("Project with name '%s' does not exist in the validation result database." % proj_name)
            record = None
        elif len(entries) > 1:
            self._log.warning("Project with name '%s' cannot be resolved because it is ambiguous. (%s)"
                              % (proj_name, entries))
            record = entries
        else:
            record = entries[0][COL_NAME_PROJECT_PID]
        return record

    def get_hpc_server_id(self, name=DEFAULT_HPC_SERVER):
        """
        Get Server Id for the given Name

        :param name:  Server name  default value "LUSS013"
        :type name: str
        :return: Return HPC server Id for single entry otherwise return list of record for duplicate entry
            or return None if no Name found in datbase
        :rtype: int | list | None
        """

        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                         COL_NAME_HPCSERVER_NAME),
                             OP_EQ, SQLLiteral(name.lower()))

        entries = self.select_generic_data(table_list=[TABLE_NAME_HPCSERVER], where=cond)
        if len(entries) <= 0:
            self._log.warning("HPC Server '%s' does not exist in the validation result database." % name)
            record = None
        elif len(entries) > 1:
            self._log.warning("HPC Server  '%s' cannot be resolved because it is ambiguous. (%s)" % (name, entries))
            record = entries
        else:
            record = entries[0][COL_NAME_HPCSERVER_SERVID]
        return record

    def get_priority_name(self, prid):
        """
        Get prority name for Given priority Id

        :param prid: priority Id
        :type prid: int
        :return: Priority Name if prid exist otherwise return None
        :rtype: str | None
        """
        record = self.get_priority(prid=prid, name=None)
        if COL_NAME_PRIORITIES_NAME in record:
            return record[COL_NAME_PRIORITIES_NAME]
        else:
            return None

    def get_priority_id(self, name):
        """
        Get prority name for Given priority Id

        :param name: Prority name e.g. high, normal, low
        :type name: str
        :return: Priority Id if such name exist otherwise return None
        :rtype: int | None
        """
        record = self.get_priority(prid=None, name=name)
        if COL_NAME_PRIORITIES_PRID in record:
            return record[COL_NAME_PRIORITIES_PRID]
        else:
            return None

    def get_priority(self, prid=None, name=None):
        """
        Get priority dictionary record for given Id and Name

        :param prid: priority id
        :type prid: int | None
        :param name: Prority name e.g. high, normal, low
        :type name: str | None
        :return: record if such entry found otherwise raise StandardError
        :rtype: dict
        """
        cond = None
        if prid is not None:
            cond = SQLBinaryExpr(COL_NAME_PRIORITIES_PRID, OP_EQ, prid)

        if name is not None:
            if cond is None:
                cond = SQLBinaryExpr(COL_NAME_PRIORITIES_NAME, OP_EQ, SQLLiteral(name.lower()))
            else:
                cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COL_NAME_PRIORITIES_NAME, OP_EQ,
                                                                 SQLLiteral(name.lower())))

        entries = self.select_generic_data(table_list=[TABLE_NAME_PRIORITIES], where=cond)
        if len(entries) == 1:
            return entries[0]
        elif len(entries) > 1:
            raise StandardError("Priority cannot be resolved because it is ambiguous")
        else:
            return entries

    def add_component(self, name, desc=None):
        """
        Add new component into databse

        :param name: component name
        :type name: string
        :param desc: description of component
        :type desc: string
        """
        if self.get_component_id(name) is None:
            comp_rec = {COL_NAME_COMPONENTS_NAME: name.lower(), COL_NAME_COMPONENTS_DESC: desc}
            self.add_generic_data(comp_rec, TABLE_NAME_COMPONENTS)

    def get_component_name(self, cmpid):
        """
        Get Component name for Given Component Id

        :param cmpid: Component Id
        :type cmpid: int
        :return: Return Component Name of Id exist otherwise return None
        :rtype: str | None
        """
        record = self.get_component(cmpid=cmpid, name=None)
        if COL_NAME_COMPONENTS_NAME in record:
            return record[COL_NAME_COMPONENTS_NAME]
        else:
            return None

    def get_component_id(self, name):
        """
        Get Component Id for Given component Name

        :param name: Component Name
        :type name: str
        :return: Return ComponentId exist otherwise return None
        :rtype: int | None
        """
        record = self.get_component(cmpid=None, name=name)
        if COL_NAME_COMPONENTS_CMPID in record:
            return record[COL_NAME_COMPONENTS_CMPID]
        else:
            return None

    def get_component(self, cmpid=None, name=None):
        """
        Get Component Record for given Component Id or Component Name

        :param cmpid: Component Id
        :type cmpid: int | None
        :param name: Name of component
        :type name: str | None
        :return: record if such entry found otherwise raise StandardError
        :rtype: dict
        """
        if self.sub_scheme_version >= GBL_COMPONENT_FEATURE:
            cond = None
            if cmpid is not None:
                cond = SQLBinaryExpr(COL_NAME_COMPONENTS_CMPID, OP_EQ, cmpid)

            if name is not None:
                if cond is None:
                    cond = SQLBinaryExpr(COL_NAME_COMPONENTS_NAME, OP_EQ, SQLLiteral(name.lower()))
                else:
                    cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COL_NAME_COMPONENTS_NAME, OP_EQ,
                                                                     SQLLiteral(name.lower())))

            entries = self.select_generic_data(table_list=[TABLE_NAME_COMPONENTS], where=cond)
            if len(entries) == 1:
                return entries[0]
            elif len(entries) > 1:
                raise StandardError("Component cannot be resolved because it is ambiguous")
            else:
                return entries
        else:
            self._log.warning(str("Component Feature in Global Subschema is not available"))
            return []

    def get_test_type_name(self, ttypeid):
        """
        Get test type name for given Id which used to by report template library to decide
        whether function or performace report template should be use

        :param ttypeid: test type id
        :type ttypeid: int
        :return: Return Test Type Name if exist otherwise return None
        :rtype: str | None
        """
        testtype_rec = self.get_test_type(ttypeid=ttypeid)
        if testtype_rec is not None:
            return testtype_rec[COL_NAME_COMPONENTS_NAME]
        else:
            return None

    def get_test_typeid(self, name):
        """
        Get Test Type id for the given name

        :param name: test type name
        :type name: str
        :return: Return Test Type Id if exist otherwise return None
        :rtype: int | None
        """

        testtype_rec = self.get_test_type(name=name)
        if testtype_rec is not None:
            return testtype_rec[COL_NAME_COMPONENTS_TTID]
        else:
            return None

    def get_test_type(self, ttypeid=None, name=None):
        """
        Get TestType record for given name or typeid.
        Returns None if the feature is not available or no record found

        :param ttypeid: test type id
        :type ttypeid: int
        :param name: test type name
        :type name: str
        :return: record if such entry found otherwise raise StandardError for duplicate entry
        :rtype: dict
        """
        if self.sub_scheme_version >= GBL_TESTTYPE_FEATURE:
            cond = None
            if ttypeid is not None:
                cond = SQLBinaryExpr(COL_NAME_COMPONENTS_TTID, OP_EQ, ttypeid)

            if name is not None:
                if cond is None:
                    cond = SQLBinaryExpr(COL_NAME_COMPONENTS_NAME, OP_EQ, SQLLiteral(name.lower()))
                else:
                    cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COL_NAME_COMPONENTS_NAME, OP_EQ,
                                                                     SQLLiteral(name.lower())))
            entries = self.select_generic_data(table_list=[TABLE_NAME_TESTTYPE], where=cond)
            if len(entries) == 1:
                return entries[0]
            elif len(entries) > 1:
                raise StandardError("Test type cannot be resolved because it is ambiguous")
            else:
                return None
        else:
            self._log.warning(str("Test type Feature in Global Subschema is not available"))
            return None

    def add_test_type(self, name):
        """
        Add test type entry in database. If the name already exist return its id otherwise insert new entry and
        return id of newly entred record

        :param name: test type name
        :type name: str
        :return: Return Id of the newly inserted row on failure return None with warning message
        :rtype: int | None
        """
        testtypeid = None
        if self.sub_scheme_version >= GBL_TESTTYPE_FEATURE:
            testtypeid = self.get_test_typeid(name)
            if testtypeid is None:
                testtype_rec = {COL_NAME_COMPONENTS_NAME: name.lower()}
                self.add_generic_data(testtype_rec, TABLE_NAME_TESTTYPE)
                testtypeid = self.get_test_typeid(name)
        else:
            self._log.warning(str("Test type Feature in Global Subschema is not available"))

        return testtypeid

    # ====================================================================
    # deprecated methods
    # ====================================================================

    @deprecated('add_workflow')
    def AddWorkflow(self, workflow):  # pylint: disable=C0103
        """deprecated"""
        return self.add_workflow(workflow)

    @deprecated('update_workflow')
    def UpdateWorkflow(self, workflow, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_workflow(workflow, where)

    @deprecated('delete_workflow')
    def DeleteWorkflow(self, workflow):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_workflow(workflow)

    @deprecated('get_workflow')
    def GetWorkflow(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_workflow(name)

    @deprecated('get_workflow_name')
    def GetWorkflowName(self, wfid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_workflow_name(wfid)

    @deprecated('add_assessment_state')
    def AddAssessmentState(self, ass_state):  # pylint: disable=C0103
        """deprecated"""
        return self.add_assessment_state(ass_state)

    @deprecated('get_assessment_state')
    def GetAssessmentState(self, name=None, assstid=None, observer_type_id=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_assessment_state(name, assstid, observer_type_id)

    @deprecated('get_assessment_state_id')
    def GetAssessmentStateId(self, name, observer_type_id=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_assessment_state_id(name, observer_type_id)

    @deprecated('add_user')
    def AddUser(self, user):  # pylint: disable=C0103
        """deprecated"""
        return self.add_user(user)

    @deprecated('update_user')
    def UpdateUser(self, user, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_user(user, where)

    @deprecated('delete_user')
    def DeleteUser(self, user):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_user(user)

    @deprecated('get_user')
    def GetUser(self, name=None, login=None, user_id=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_user(name, login, user_id)

    @deprecated('get_user_id')
    def GetUserId(self, name=None, login=None, user_id=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_user_id(name, login, user_id)

    @deprecated('get_all_users')
    def GetAllUsers(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_all_users()

    @deprecated('add_unit')
    def AddUnit(self, unit):  # pylint: disable=C0103
        """deprecated"""
        return self.add_unit(unit)

    @deprecated('update_unit')
    def UpdateUnit(self, unit, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_unit(unit, where)

    @deprecated('delete_unit')
    def DeleteUnit(self, unit):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_unit(unit)

    @deprecated('get_unit')
    def GetUnit(self, name=None, uid=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_unit(name, uid)

    @deprecated('get_unit_id_by_name')
    def GetUnitIdByName(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_unit_id_by_name(name)

    @deprecated('get_table_data')
    def GetTableData(self, table, columns=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_table_data(table, columns)

    @deprecated('get_select_data')
    def GetSelectData(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.get_select_data(*args, **kw)

    @deprecated('add_val_observer_type')
    def AddValObserverType(self, tr_type):  # pylint: disable=C0103
        """deprecated"""
        return self.add_val_observer_type(tr_type)

    @deprecated('update_val_observer_type')
    def UpdateValObserverType(self, tr_type, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_val_observer_type(tr_type, where)

    @deprecated('delete_val_observer_type')
    def DeleteValObserverType(self, tr_type):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_val_observer_type(tr_type)

    @deprecated('get_val_observer_type')
    def GetValObserverType(self, name=None, type_id=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_val_observer_type(name, type_id)

    @deprecated('get_val_observer_type_id')
    def GetValObserverTypeId(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_val_observer_type_id(name)

    @deprecated('add_value_type')
    def AddValueType(self, type_name, desc):  # pylint: disable=C0103
        """deprecated"""
        return self.add_value_type(type_name, desc)

    @deprecated('update_value_type')
    def UpdateValueType(self, type_name, desc):  # pylint: disable=C0103
        """deprecated"""
        return self.update_value_type(type_name, desc)

    @deprecated('delete_value_type')
    def DeleteValueType(self, type_name):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_value_type(type_name)

    @deprecated('get_value_type')
    def GetValueType(self, type_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_value_type(type_name)

    @deprecated('get_value_type_id')
    def GetValueTypeId(self, type_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_value_type_id(type_name)

    @deprecated('add_project')
    def AddProject(self, proj_name, desc):  # pylint: disable=C0103
        """deprecated"""
        return self.add_project(proj_name, desc)

    @deprecated('get_project_name')
    def GetProjectName(self, pid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_project_name(pid)

    @deprecated('get_all_project_name')
    def GetAllProjectName(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_all_project_name()

    @deprecated('get_project_id')
    def GetProjectId(self, proj_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_project_id(proj_name)

    @deprecated('get_hpc_server_id')
    def GetHPCServerId(self, name=DEFAULT_HPC_SERVER):  # pylint: disable=C0103
        """deprecated"""
        return self.get_hpc_server_id(name)

    @deprecated('get_priority_name')
    def GetPriorityName(self, prid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_priority_name(prid)

    @deprecated('get_priority_id')
    def GetPriorityId(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_priority_id(name)

    @deprecated('get_priority')
    def GetPriority(self, prid=None, name=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_priority(prid, name)

    @deprecated('add_component')
    def AddComponent(self, name, desc=None):  # pylint: disable=C0103
        """deprecated"""
        return self.add_component(name, desc)

    @deprecated('get_component_name')
    def GetComponentName(self, cmpid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_component_name(cmpid)

    @deprecated('get_component_id')
    def GetComponentId(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_component_id(name)

    @deprecated('get_component')
    def GetComponent(self, cmpid=None, name=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_component(cmpid, name)

    @deprecated('get_test_type_name')
    def GetTestTypeName(self, ttypeid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_test_type_name(ttypeid)

    @deprecated('get_test_typeid')
    def GetTestTypeid(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_test_typeid(name)

    @deprecated('get_test_type')
    def GetTestType(self, ttypeid=None, name=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_test_type(ttypeid, name)

    @deprecated('add_test_type')
    def AddTestType(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.add_test_type(name)

    @deprecated('table_names (property)')
    def GetTableNames(self):  # pylint: disable=C0103
        """deprecated"""
        return self.table_names

    @deprecated('table_names (property)')
    def get_table_names(self):
        """deprecated"""
        return self.table_names

    @deprecated('get_columns')
    def GetColumnNames(self, table_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_columns(table_name)

    @deprecated('get_columns')
    def get_column_names(self, table_name):
        """deprecated"""
        return self.get_columns(table_name)


# ====================================================================
# Constraint DB Libary SQL Server Compact Implementation
# ====================================================================
class PluginGblDB(BaseGblDB, PluginBaseDB):  # pylint: disable=R0904
    """used by plugin finder"""
    def __init__(self, *args, **kwargs):
        """some comment is missing"""
        BaseGblDB.__init__(self, *args, **kwargs)


class SQLCEGblDB(BaseGblDB, PluginBaseDB):  # pylint: disable=R0904
    """SQL Server Compact Edition Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseGblDB.__init__(self, *args, **kwargs)


class OracleGblDB(BaseGblDB, PluginBaseDB):  # pylint: disable=R0904
    """Oracle Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseGblDB.__init__(self, *args, **kwargs)


class SQLite3GblDB(BaseGblDB, PluginBaseDB):  # pylint: disable=R0904
    """Oracle Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseGblDB.__init__(self, *args, **kwargs)


"""
$Log: gbl.py  $
Revision 1.12 2017/11/13 17:09:34CET Hospes, Gerd-Joachim (uidv8815) 
use location, update tests, add table gbl_location and cat_files column location to sqlite
Revision 1.11 2016/08/16 12:26:16CEST Hospes, Gerd-Joachim (uidv8815)
update module and class docu
Revision 1.10 2016/06/12 20:25:50CEST Hospes, Gerd-Joachim (uidv8815)
use LOGINNAME for existence check in add_user
Revision 1.9 2016/04/04 17:40:34CEST Hospes, Gerd-Joachim (uidv8815)
fix epydoc errors
Revision 1.8 2015/07/16 11:41:26CEST Ahmed, Zaheer (uidu7634)
user role management functions
- Added comments -  uidu7634 [Jul 16, 2015 11:41:26 AM CEST]
Change Package : 348978:1 http://mks-psad:7002/im/viewissue?selection=348978
Revision 1.7 2015/07/14 11:33:07CEST Mertens, Sven (uidv7805)
rewinding some changes
--- Added comments ---  uidv7805 [Jul 14, 2015 11:33:08 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.6 2015/07/14 09:30:13CEST Mertens, Sven (uidv7805)
simplify for plugin finder
--- Added comments ---  uidv7805 [Jul 14, 2015 9:30:14 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.5 2015/05/18 14:53:10CEST Ahmed, Zaheer (uidu7634)
remove SQLiteral usage for number datatypes
--- Added comments ---  uidu7634 [May 18, 2015 2:53:11 PM CEST]
Change Package : 338368:1 http://mks-psad:7002/im/viewissue?selection=338368
Revision 1.4 2015/04/30 11:48:24CEST Hospes, Gerd-Joachim (uidv8815)
fix merge errors
--- Added comments ---  uidv8815 [Apr 30, 2015 11:48:24 AM CEST]
Change Package : 330394:1 http://mks-psad:7002/im/viewissue?selection=330394
Revision 1.3 2015/04/30 11:30:44CEST Hospes, Gerd-Joachim (uidv8815)
correct indent
--- Added comments ---  uidv8815 [Apr 30, 2015 11:30:44 AM CEST]
Change Package : 330394:1 http://mks-psad:7002/im/viewissue?selection=330394
Revision 1.2 2015/04/30 11:09:34CEST Hospes, Gerd-Joachim (uidv8815)
merge last changes
--- Added comments ---  uidv8815 [Apr 30, 2015 11:09:34 AM CEST]
Change Package : 330394:1 http://mks-psad:7002/im/viewissue?selection=330394
Revision 1.1 2015/04/23 19:04:04CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/gbl/project.pj
Revision 1.48 2015/04/30 10:19:46CEST Ahmed, Zaheer (uidu7634)
cache for gbl_observertype and gbl_assessment_state
--- Added comments ---  uidu7634 [Apr 30, 2015 10:19:46 AM CEST]
Change Package : 318797:1 http://mks-psad:7002/im/viewissue?selection=318797
Revision 1.47 2015/04/29 12:25:29CEST Ahmed, Zaheer (uidu7634)
cache records for global configuration
--- Added comments ---  uidu7634 [Apr 29, 2015 12:25:30 PM CEST]
Change Package : 318797:1 http://mks-psad:7002/im/viewissue?selection=318797
Revision 1.46 2015/04/27 14:36:05CEST Mertens, Sven (uidv7805)
ident string fix
--- Added comments ---  uidv7805 [Apr 27, 2015 2:36:06 PM CEST]
Change Package : 329312:2 http://mks-psad:7002/im/viewissue?selection=329312
Revision 1.45 2015/04/24 12:46:54CEST Mertens, Sven (uidv7805)
well, for gbl we can do the same
--- Added comments ---  uidv7805 [Apr 24, 2015 12:46:55 PM CEST]
Change Package : 331116:2 http://mks-psad:7002/im/viewissue?selection=331116
Revision 1.44 2015/03/09 11:52:12CET Ahmed, Zaheer (uidu7634)
passing error_tolerance as keyword argument
--- Added comments ---  uidu7634 [Mar 9, 2015 11:52:13 AM CET]
Change Package : 314217:1 http://mks-psad:7002/im/viewissue?selection=314217
Revision 1.43 2015/03/05 14:19:38CET Mertens, Sven (uidv7805)
using keyword is better
--- Added comments ---  uidv7805 [Mar 5, 2015 2:19:38 PM CET]
Change Package : 312989:1 http://mks-psad:7002/im/viewissue?selection=312989
Revision 1.42 2015/03/05 09:49:08CET Mertens, Sven (uidv7805)
argument adaption and fix for logger
Revision 1.41 2014/12/09 11:36:48CET Mertens, Sven (uidv7805)
deprecation update
Revision 1.40 2014/12/08 10:00:21CET Mertens, Sven (uidv7805)
removing duplicate get_next_id
Revision 1.39 2014/10/14 14:48:22CEST Ahmed, Zaheer (uidu7634)
Supressed Logger warning if the user has intention to load all Units in form GBL_UNITS
--- Added comments ---  uidu7634 [Oct 14, 2014 2:48:22 PM CEST]
Change Package : 268541:1 http://mks-psad:7002/im/viewissue?selection=268541
Revision 1.38 2014/10/09 10:34:53CEST Mertens, Sven (uidv7805)
remove terminate overwrites
--- Added comments ---  uidv7805 [Oct 9, 2014 10:34:54 AM CEST]
Change Package : 270336:1 http://mks-psad:7002/im/viewissue?selection=270336
Revision 1.37 2014/09/02 12:28:09CEST Hecker, Robert (heckerr)
Changed default HPC Head Node.
--- Added comments ---  heckerr [Sep 2, 2014 12:28:09 PM CEST]
Change Package : 260443:1 http://mks-psad:7002/im/viewissue?selection=260443
Revision 1.36 2014/08/05 09:32:35CEST Hecker, Robert (heckerr)
Moved to new coding style.
--- Added comments ---  heckerr [Aug 5, 2014 9:32:36 AM CEST]
Change Package : 253983:1 http://mks-psad:7002/im/viewissue?selection=253983
Revision 1.35 2014/07/16 10:49:21CEST Ahmed, Zaheer (uidu7634)
improved epy documentation
--- Added comments ---  uidu7634 [Jul 16, 2014 10:49:22 AM CEST]
Change Package : 245348:1 http://mks-psad:7002/im/viewissue?selection=245348
Revision 1.34 2014/07/14 14:57:29CEST Ahmed, Zaheer (uidu7634)
Added GetUSerId() function
--- Added comments ---  uidu7634 [Jul 14, 2014 2:57:29 PM CEST]
Change Package : 241672:1 http://mks-psad:7002/im/viewissue?selection=241672
Revision 1.33 2014/06/26 21:22:27CEST Ahmed, Zaheer (uidu7634)
epy doc improvement
--- Added comments ---  uidu7634 [Jun 26, 2014 9:22:27 PM CEST]
Change Package : 242647:1 http://mks-psad:7002/im/viewissue?selection=242647
Revision 1.32 2014/06/25 13:23:39CEST Ahmed, Zaheer (uidu7634)
epy doc improvement
--- Added comments ---  uidu7634 [Jun 25, 2014 1:23:39 PM CEST]
Change Package : 242647:1 http://mks-psad:7002/im/viewissue?selection=242647
Revision 1.31 2014/06/19 12:19:29CEST Ahmed, Zaheer (uidu7634)
add new function related to table GBL_TESTTYPE
--- Added comments ---  uidu7634 [Jun 19, 2014 12:19:29 PM CEST]
Change Package : 241731:1 http://mks-psad:7002/im/viewissue?selection=241731
Revision 1.30 2014/05/28 16:15:59CEST Ahmed, Zaheer (uidu7634)
pylint fixes
--- Added comments ---  uidu7634 [May 28, 2014 4:15:59 PM CEST]
Change Package : 239969:1 http://mks-psad:7002/im/viewissue?selection=239969
Revision 1.29 2014/05/28 13:50:32CEST Ahmed, Zaheer (uidu7634)
Backward compatiblity for GetComponent() check the subschema version before running query
--- Added comments ---  uidu7634 [May 28, 2014 1:50:33 PM CEST]
Change Package : 239969:1 http://mks-psad:7002/im/viewissue?selection=239969
Revision 1.28 2014/05/22 09:11:09CEST Ahmed, Zaheer (uidu7634)
Add new defination for Table GBL_Components
new function AddComponen()t GetComponent() GetComponentName() GetComponentIdI()
--- Added comments ---  uidu7634 [May 22, 2014 9:11:09 AM CEST]
Change Package : 235884:1 http://mks-psad:7002/im/viewissue?selection=235884
Revision 1.27 2014/03/14 15:29:28CET Ahmed, Zaheer (uidu7634)
added functions GetPriorityName(), GetPriorityId(), GetPriority()
--- Added comments ---  uidu7634 [Mar 14, 2014 3:29:28 PM CET]
Change Package : 221492:2 http://mks-psad:7002/im/viewissue?selection=221492
Revision 1.26 2014/03/12 14:28:54CET Ahmed, Zaheer (uidu7634)
Added HPC Server Table and functions related to
--- Added comments ---  uidu7634 [Mar 12, 2014 2:28:55 PM CET]
Change Package : 221470:1 http://mks-psad:7002/im/viewissue?selection=221470
Revision 1.25 2014/01/23 15:38:42CET Wartenberg-EXT, Jan (uidw3910)
added method GetWorkflowName()
--- Added comments ---  uidw3910 [Jan 23, 2014 3:38:42 PM CET]
Change Package : 209812:1 http://mks-psad:7002/im/viewissue?selection=209812
Revision 1.24 2013/11/05 15:16:52CET Ahmed, Zaheer (uidu7634)
Added GetAllProjectName function to list all projects registered in Database
--- Added comments ---  uidu7634 [Nov 5, 2013 3:16:53 PM CET]
Change Package : 203293:1 http://mks-psad:7002/im/viewissue?selection=203293
Revision 1.23 2013/10/31 17:25:11CET Ahmed-EXT, Zaheer (uidu7634)
Added GBL_PROJECT table defination and db interface functions
--- Added comments ---  uidu7634 [Oct 31, 2013 5:25:11 PM CET]
Change Package : 203293:1 http://mks-psad:7002/im/viewissue?selection=203293
Revision 1.22 2013/07/29 08:41:42CEST Raedler, Guenther (uidt9430)
- revert changes of rev. 1.21
--- Added comments ---  uidt9430 [Jul 29, 2013 8:41:43 AM CEST]
Change Package : 191735:1 http://mks-psad:7002/im/viewissue?selection=191735
Revision 1.21 2013/07/04 15:01:48CEST Mertens, Sven (uidv7805)
providing tableSpace to BaseDB for what sub-schema space each module is intended to be responsible
--- Added comments ---  uidv7805 [Jul 4, 2013 3:01:48 PM CEST]
Change Package : 185933:3 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.20 2013/04/26 10:46:07CEST Mertens, Sven (uidv7805)
moving strIdent
--- Added comments ---  uidv7805 [Apr 26, 2013 10:46:07 AM CEST]
Change Package : 179495:4 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.19 2013/04/25 14:35:14CEST Mertens, Sven (uidv7805)
epydoc adaptation to colon instead of at
--- Added comments ---  uidv7805 [Apr 25, 2013 2:35:15 PM CEST]
Change Package : 179495:2 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.18 2013/04/23 14:02:53CEST Raedler, Guenther (uidt9430)
- added additional option (user_id) to get user information - GetUser()
- extendend __get_user_condition() accordingly
--- Added comments ---  uidt9430 [Apr 23, 2013 2:02:53 PM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.17 2013/04/19 13:40:08CEST Hecker, Robert (heckerr)
Functionality reverted to revision 1.13.
--- Added comments ---  heckerr [Apr 19, 2013 1:40:09 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.16 2013/04/15 12:08:42CEST Mertens, Sven (uidv7805)
small bugfixes
--- Added comments ---  uidv7805 [Apr 15, 2013 12:08:42 PM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.15 2013/04/12 14:37:07CEST Mertens, Sven (uidv7805)
adding a short representation used by db_connector.PostInitialize
--- Added comments ---  uidv7805 [Apr 12, 2013 2:37:08 PM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.14 2013/04/03 08:17:13CEST Mertens, Sven (uidv7805)
pep8: removing format errors
--- Added comments ---  uidv7805 [Apr 3, 2013 8:17:13 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.13 2013/04/02 10:03:04CEST Raedler, Guenther (uidt9430)
- use logging for all log messages again
- use specific identifier names
- removed pylint warnings
--- Added comments ---  uidt9430 [Apr 2, 2013 10:03:05 AM CEST]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.12 2013/03/28 15:25:19CET Mertens, Sven (uidv7805)
pylint: W0311 (indentation), string class
--- Added comments ---  uidv7805 [Mar 28, 2013 3:25:20 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.11 2013/03/27 11:37:25CET Mertens, Sven (uidv7805)
pep8 & pylint: rowalignment and error correction
--- Added comments ---  uidv7805 [Mar 27, 2013 11:37:26 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.10 2013/03/26 16:19:36CET Mertens, Sven (uidv7805)
pylint: using direct imports, no stars any more
--- Added comments ---  uidv7805 [Mar 26, 2013 4:19:37 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.9 2013/03/21 17:22:39CET Mertens, Sven (uidv7805)
solving some pylint warnings / errors
--- Added comments ---  uidv7805 [Mar 21, 2013 5:22:39 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.8 2013/03/04 07:47:30CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 4, 2013 7:47:31 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.7 2013/02/28 08:12:11CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:12 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.6 2013/02/27 16:19:52CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 27, 2013 4:19:53 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.5 2013/02/26 20:10:34CET Raedler, Guenther (uidt9430)
- Updates after Pep8 Styleguides
--- Added comments ---  uidt9430 [Feb 26, 2013 8:10:34 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.4 2013/02/26 16:18:05CET Raedler, Guenther (uidt9430)
- add assessment state method
- renamed observer_type into observer_type_id
--- Added comments ---  uidt9430 [Feb 26, 2013 4:18:05 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.3 2013/02/20 09:38:53CET Raedler, Guenther (uidt9430)
- fixed wrong number of arguments
--- Added comments ---  uidt9430 [Feb 20, 2013 9:38:53 AM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.2 2013/02/19 14:07:26CET Raedler, Guenther (uidt9430)
- database interface classes derives from common classes for oracle, ...
- use common exception classes
- use common db functions
--- Added comments ---  uidt9430 [Feb 19, 2013 2:07:27 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/02/11 09:57:29CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
    05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/db/gbl/project.pj
------------------------------------------------------------------------------
-- From ETK/ADAS_DB Archive
------------------------------------------------------------------------------
Revision 1.24 2012/11/08 10:25:32CET Bratoi, Bogdan-Horia (uidu8192)
- Changing the GetValObserverType - adding the Type_id as parameter
--- Added comments ---  uidu8192 [Nov 8, 2012 10:25:35 AM CET]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.23 2012/11/05 13:53:51CET Bratoi, Bogdan-Horia (uidu8192)
- Adding the observer type in the GBL_ASSESSMENT_STATE
--- Added comments ---  uidu8192 [Nov 5, 2012 1:53:56 PM CET]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.22 2012/10/17 13:16:06CEST Bratoi, Bogdan-Horia (uidu8192)
Updated the GetValObserverType function
--- Added comments ---  uidu8192 [Oct 17, 2012 1:16:09 PM CEST]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.21 2012/10/17 11:36:29CEST Ahmed-EXT, Zaheer (uidu7634)
Redefine GBL_Assessment_State table and column definations
Fixed int type cast
--- Added comments ---  uidu7634 [Oct 17, 2012 11:36:31 AM CEST]
Change Package : 153893:1 http://mks-psad:7002/im/viewissue?selection=153893
Revision 1.20 2012/10/09 14:33:35CEST Hammernik-EXT, Dmitri (uidu5219)
- added new table functions for gbl_assessment_state
--- Added comments ---  uidu5219 [Oct 9, 2012 2:33:37 PM CEST]
Change Package : 100180:1 http://mks-psad:7002/im/viewissue?selection=100180
Revision 1.19 2012/03/22 11:47:36CET Raedler-EXT, Guenther (uidt9430)
- fixed error when reading column definition from ADMIN tables
- fixed some typos
--- Added comments ---  uidt9430 [Mar 22, 2012 11:47:37 AM CET]
Change Package : 100768:2 http://mks-psad:7002/im/viewissue?selection=100768
Revision 1.18 2012/03/02 11:18:55CET Bratoi Bogdan-Horia (uidu8192) (uidu8192)
Changed GetTables for Oracle DB supporting all users
--- Added comments ---  uidu8192 [Mar 2, 2012 11:18:55 AM CET]
Change Package : 100767:1 http://mks-psad:7002/im/viewissue?selection=100767
Revision 1.17 2012/02/28 16:41:38CET Farcas-EXT, Florian Radu (uidu4753)
Update DB interface
--- Added comments ---  uidu4753 [Feb 28, 2012 4:41:38 PM CET]
Change Package : 100439:1 http://mks-psad:7002/im/viewissue?selection=100439
Revision 1.16 2012/02/06 08:23:00CET Raedler-EXT, Guenther (uidt9430)
- cast new ID as integer value
--- Added comments ---  uidt9430 [Feb 6, 2012 8:23:01 AM CET]
Change Package : 95134:1 http://mks-psad:7002/im/viewissue?selection=95134
Revision 1.15 2011/09/08 17:00:57CEST Castell, Christoph (uidt6394)
Added GetSelectData() function. Needs to be completed.
--- Added comments ---  uidt6394 [Sep 8, 2011 5:00:58 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.14 2011/09/06 10:01:13CEST Spruck Jochen (spruckj) (spruckj)
Remove some typing erros in error logging
--- Added comments ---  spruckj [Sep 6, 2011 10:01:13 AM CEST]
Change Package : 69027:1 http://mks-psad:7002/im/viewissue?selection=69027
Revision 1.13 2011/09/06 09:56:53CEST Spruck Jochen (spruckj) (spruckj)
Remove some typing errors
--- Added comments ---  spruckj [Sep 6, 2011 9:56:53 AM CEST]
Change Package : 69027:1 http://mks-psad:7002/im/viewissue?selection=69027
Revision 1.12 2011/09/05 15:24:51CEST Castell Christoph (uidt6394) (uidt6394)
Fixed bug in GetUnitIdByName().
--- Added comments ---  uidt6394 [Sep 5, 2011 3:24:51 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.11 2011/09/05 14:00:48CEST Castell Christoph (uidt6394) (uidt6394)
Changed default return type of GetUnit() to None.
--- Added comments ---  uidt6394 [Sep 5, 2011 2:00:48 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.10 2011/09/01 09:09:41CEST Raedler Guenther (uidt9430) (uidt9430)
-- added function GetUnitIdByName
--- Added comments ---  uidt9430 [Sep 1, 2011 9:09:42 AM CEST]
Change Package : 67780:2 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.9 2011/08/29 17:02:46CEST Ibrouchene Nassim (uidt5589) (uidt5589)
Added column TYPE in Unit table
--- Added comments ---  uidt5589 [Aug 29, 2011 5:02:47 PM CEST]
Change Package : 69072:2 http://mks-psad:7002/im/viewissue?selection=69072
Revision 1.8 2011/08/25 17:08:27CEST Ibrouchene Nassim (uidt5589) (uidt5589)
Fixed an issue with the AddUnit() : wrong column names.
--- Added comments ---  uidt5589 [Aug 25, 2011 5:08:27 PM CEST]
Change Package : 69072:2 http://mks-psad:7002/im/viewissue?selection=69072
Revision 1.7 2011/08/09 12:42:49CEST Castell Christoph (uidt6394) (uidt6394)
GetColumnNames() for Oracle.
--- Added comments ---  uidt6394 [Aug 9, 2011 12:42:49 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.6 2011/08/09 11:23:51CEST Castell Christoph (uidt6394) (uidt6394)
Changed GetTableNames() functions so that both return a list of table names. (not a dict)
--- Added comments ---  uidt6394 [Aug 9, 2011 11:23:51 AM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.5 2011/08/09 10:23:05CEST Castell Christoph (uidt6394) (uidt6394)
Implemented GetTableNames() for Oracle.
Revision 1.4 2011/07/19 11:46:53CEST Raedler Guenther (uidt9430) (uidt9430)
-- fixed some errors
-- added validation oberserver support
--- Added comments ---  uidt9430 [Jul 19, 2011 11:46:53 AM CEST]
Change Package : 67780:2 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.3 2011/07/12 16:15:28CEST Spruck Jochen (spruckj) (spruckj)
Add get all users function
--- Added comments ---  spruckj [Jul 12, 2011 4:15:28 PM CEST]
Change Package : 69027:1 http://mks-psad:7002/im/viewissue?selection=69027
Revision 1.2 2011/07/04 13:17:11CEST Raedler Guenther (uidt9430) (uidt9430)
-- added new table functions and testcode
--- Added comments ---  uidt9430 [Jul 4, 2011 1:17:12 PM CEST]
Change Package : 67780:2 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.1 2011/07/01 14:55:56CEST Raedler Guenther (uidt9430) (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/EM_EnvironmentModel/05_Testing/05_Test_Environment/algo/em_req_test/valf_tests/
    adas_database/gbl/project.pj
"""
