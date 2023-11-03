"""
stk/db/db_common.py
-------------------

Common function database declarations and base class for specialized sub-scheme implementations.

Classes to connect to the sub-schemes are derived from the `BaseDB`:

**User-API**

    ========= ====================   ==============================================================
     package   class                 usage
    ========= ====================   ==============================================================
     `cat`     `BaseRecCatalogDB`    recording (measurement) details and collections
     `cl`      `BaseCLDB`            constraint label tables as used in e.g. EBA
     `fct`     `BaseFctDB`           functional related recording details like scenarios,
                                     ego behaviour and criticality of events
     `gbl`     `BaseGblDB`           global definition tables like constants, units, db users
     `hpc`     `HpcErrorDB`          hpc errors as used by report generation
     `lbl`     `BaseGenLabelDB`      radar events with type and state
     `lbl`     `BaseCameraLabelDB`   additional label information in camera projects
     `obj`     `BaseObjDataDB`       object detection results and calculation
     `sim`     `BaseSimulationDB`    camera and radar sensor fusion
     `val`     `BaseValResDB`        validation results stored for assessment,
                                     reports and doors export
    ========= ====================   ==============================================================

The other classes in this module are handling the different DB types and are derived from BaseDB.

**usage in Valf suites**

For validation suites based on `Valf` class there is the operator `DbLinker` setting up all needed connections.

**using several connections in parallel**

If several sub-schemes have to be used in parallel the first connection should be reused.
Please check for the needed class from the table above for more detail.

**Do not waste the limited number of connections to Oracle DB**
by setting up a new connection for each sub-scheme,
always use the existing one as described in class description of derived sub-scheme class.

:org:           Continental AG
:author:        Dominik Froehlich

:version:       $Revision: 1.37 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/07/21 12:36:37CEST $
"""
# pylint: disable=W0102,W0702,R0903,R0912,R0914,R0915
# - import Python modules ---------------------------------------------------------------------------------------------
from os import path, stat, chmod, environ
from sys import maxint
from stat import ST_MODE, S_IWRITE
from datetime import datetime
from re import compile as recomp, search, finditer
from platform import release
from logging import INFO
from cx_Oracle import connect as cxconnect, DatabaseError
from adodbapi import connect as adoconnect, adUseServer
from sqlite3 import connect as sqconnect, register_adapter, register_converter, sqlite_version
from types import StringTypes
from time import sleep
from random import random
from distutils.version import LooseVersion
from warnings import warn

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.stk import MIN_SQLITE_VERSION
from stk.db.db_sql import GenericSQLStatementFactory, SQLDate, SQLColumnExpr, SQLFuncExpr, SQLListExpr, \
    SCHEMA_PREFIX_SEPARATOR, TABLE_PREFIX_SEPARATOR, SQL_TABLENAMES, SQL_DATETIME, SQL_DT_EXPR, SQL_COLUMNS, \
    CX_VARS, SQ_VARS, DBTYPE, IDENT_SPACE, CONN_STRING
from stk.error import StkError
from stk.util.logger import Logger
from stk.util.helper import deprecated, arg_trans

# - defines -----------------------------------------------------------------------------------------------------------
DEFAULT_MASTER_SCHEMA_PREFIX = None
DEFAULT_MASTER_DSN = None  # CLEO is not used for Oracle 11g
DEFAULT_MASTER_DBQ = "racadmpe"  # use sqlnet.ora and ldap.ora instead of "lidb003:1521/cleo"
DEFAULT_MASTER_DRV_XP = "Oracle in instantclient11_1"  # Released for WinXP
DEFAULT_MASTER_DRV_W7 = "Oracle in instantclient_11_2"  # Released for Win7
DEFAULT_SLAVE_DATA_PROVIDER_XP = "Microsoft.SQLSERVER.MOBILE.OLEDB.3.0"  # Released for WinXP
DEFAULT_SLAVE_DATA_PROVIDER_W7 = "Microsoft.SQLSERVER.CE.OLEDB.3.5"  # Released for Win7

if release() == 'XP':
    DEFAULT_MASTER_DRV = DEFAULT_MASTER_DRV_XP
    DEFAULT_SLAVE_DATA_PROVIDER = DEFAULT_SLAVE_DATA_PROVIDER_XP
else:
    DEFAULT_MASTER_DRV = DEFAULT_MASTER_DRV_W7
    DEFAULT_SLAVE_DATA_PROVIDER = DEFAULT_SLAVE_DATA_PROVIDER_W7

DEFAULT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
ORACLE_DATETIME_FORMAT = "YYYY-MM-DD HH24:MI:SS"

ERROR_TOLERANCE_NONE = 0
ERROR_TOLERANCE_LOW = 1
ERROR_TOLERANCE_MED = 2
ERROR_TOLERANCE_HIGH = 3

DB_FUNC_NAME_MIN = "DB_FUNC_NAME_MIN"
DB_FUNC_NAME_MAX = "DB_FUNC_NAME_MAX"
DB_FUNC_NAME_AVG = "DB_FUNC_NAME_AVG"
DB_FUNC_NAME_LOWER = "DB_FUNC_NAME_LOWER"
DB_FUNC_NAME_UPPER = "DB_FUNC_NAME_UPPER"
DB_FUNC_NAME_GETDATE = 'DB_FUNC_NAME_GETDATE'
DB_FUNC_NAME_SUBSTR = "DB_FUNC_NAME_SUBSTR"

# Common Tables
TABLE_NAME_VERSION = "Versions"

COL_NAME_SUBSCHEMEPREF = "SUBSCHEMEPREF"
COL_NAME_SUBSCHEMEVERSION = "SUBSCHEMEVERSION"

# Roles
ROLE_DB_ADMIN = "ADMIN"
ROLE_DB_USER = "USER"

LAST_ROWID = ";SELECT last_insert_rowid()"

SQLITE_FILE_EXT = (".db", ".db3", ".sqlite",)
SDF_FILE_EXT = (".sdf",)


# - classes -----------------------------------------------------------------------------------------------------------
class AdasDBError(StkError):
    """Base of all ConstraintDatabase errors"""
    pass


class AdasDBNotImplemented(AdasDBError):
    """Feature is not implemented"""
    pass


class BaseDB(object):
    """**base implementation of the Database Interface**

    This class provides a wide range of options to connect to the DB:

    - use the sensor technology name like 'MFC4XX', 'ARX4XX' or 'VGA'
    - use the path/name of the db file e.g. for sqlite or sdf
    - use already existing db connection as stored by this class in ``self._db_connection``
    - use direct db connection string like "uid=DB_USER_ACCOUNT; pwd=password;...."

    Use the derived classes for the sub schemas and tables to connect to the DB. See `db_common` for more detail.

    List of all initializing parameters in `__init__`.

    """

    # ====================================================================
    # Handling of database
    # ====================================================================

    def __init__(self, *args, **kw):
        """base database class for underlying subpackages like cat, gbl, lbl, etc.

        This class can also be used directly.

        :param args: list of additional arguments: table_prefix, stmt_factory, error_tolerance

        :keyword db_connection: The database connection to be used
        :type db_connection: str, cx_oracle.Connection, pydodbc.Connection, sqlite3.Connection, sqlce.Connection
        :param args: list of additional arguments: table_prefix, stmt_factory, error_tolerance
        :keyword table_prefix: The table name prefix which is usually master schema name
        :type table_prefix: str
        :keyword stmt_factory: The SQL statement factory to be used
        :type stmt_factory: GenericSQLStatementFactory
        :keyword strIdent: string identifier used from subclass for identification
        :type strIdent: str
        :keyword error_tolerance: set log level for debugging purposes
        :type error_tolerance: int
        :keyword loglevel: being able to reduce logging, especially with scripts
        :type loglevel: Integer, see logging class for reference
        :keyword autocommit: boolean value to determine wether to commit after an insert or update automatically
        :type autocommit: bool
        :keyword foreign_keys: set to True when sqlite DB connection should take care of foreign key relations
        :type foreign_keys: bool
        :keyword arraysize: only for cxoracle: '...This read-write attribute specifies the number of rows to fetch
                            at a time internally...', default is 50, a good value should be about 500
        :keyword maxtry: try maximum times to get connection to Oracle DB, default: 60
        :type arraysize: int
        :keyword journal: turn off journal mode with sqlite DB, default: True
        :type journal: bool
        """
        opts = arg_trans(["db_connection", ("table_prefix", None), ("sql_factory", GenericSQLStatementFactory()),
                          ("error_tolerance", ERROR_TOLERANCE_NONE), ("strIdent", "")], *args, **kw)
        self._log = Logger(self.__class__.__name__, kw.pop("loglevel", INFO))
        self._table_prefix = "" if opts["table_prefix"] is None else opts["table_prefix"].rstrip('.')
        self._sql_factory = opts["sql_factory"]
        self._ident = opts["strIdent"]
        self.error_tolerance = opts["error_tolerance"]
        self._enable_fks = opts.pop("foreign_keys", False)
        self._arraysize = None

        self._db_type = None
        self.db_func_map = {}
        self.role = None
        self.sync_slave_reload_all = False

        self._connstr = [None, self._table_prefix]
        self._func_params = recomp(r"(\(.*\))")
        self._auto_commit = opts.pop("autocommit", False)
        self._direct_conn = False

        self._db_connection = None

        # connect to DB and configure some DB specifics like role, date, time, etc.
        db_connection = opts["db_connection"]
        if type(db_connection) in StringTypes:
            self._connstr[0] = db_connection
            self._direct_conn = True
            cslower = db_connection.lower()
            if db_connection in CONN_STRING:
                self._table_prefix = CONN_STRING[db_connection][1]
                db_connection = CONN_STRING[db_connection][0]
                cslower = db_connection.lower()

            if any(cslower.endswith(ext) for ext in SQLITE_FILE_EXT) and path.isfile(cslower) or cslower == ":memory:":
                if LooseVersion(sqlite_version) <= LooseVersion(MIN_SQLITE_VERSION):
                    warn("please upgrade r'C:\\Python27\\DLLs\\sqlite.dll' from "
                         "http://www.sqlite.org/download.html!!!", stacklevel=2)
                    warn("some DB features might not work properly.", stacklevel=2)
                try:
                    if not stat(db_connection)[ST_MODE] & S_IWRITE:
                        chmod(db_connection, S_IWRITE)
                except:
                    pass

                self._db_connection = sqconnect(db_connection)
                self._db_connection.text_factory = str
                register_adapter(long, lambda l: str(l) if long(l) > maxint else l)
                register_converter("long", lambda l: long(l))

                if not kw.pop('journal', True):
                    self.execute("PRAGMA JOURNAL_MODE = OFF")

                for i in kw.pop('aggregates', []):
                    self.db_connection.create_aggregate(i.__name__, i.step.im_func.func_code.co_argcount - 1, i)

            elif any(cslower.endswith(ext) for ext in SDF_FILE_EXT):
                if cslower.startswith('data source='):
                    fname = db_connection[cslower.find("data source=") + 12:].partition(";")[0].strip()
                else:
                    fname = cslower
                    db_connection = 'data source=' + db_connection
                if not stat(fname)[ST_MODE] & S_IWRITE:
                    chmod(fname, S_IWRITE)
                if "provider=" not in cslower:
                    db_connection += (";Provider=%s" % DEFAULT_SLAVE_DATA_PROVIDER)
                self._db_connection = adoconnect(db_connection)
                if hasattr(self._db_connection, "adoConn"):
                    self._db_connection.adoConn.CursorLocation = adUseServer
                else:
                    self._db_connection.connector.CursorLocation = adUseServer
            else:
                # ex: DBQ=racadmpe;Uid=DEV_MFC31X_ADMIN;Pwd=MFC31X_ADMIN
                # init argument part, split up and use it for cxconnect
                args = {}
                for arg in db_connection.split(';'):
                    part = arg.split('=', 2)
                    args[part[0].strip().lower()] = part[1].strip()
                for _ in xrange(kw.pop('maxtry', 180)):
                    try:  # min 3 minutes along...
                        self._db_connection = cxconnect(args['uid'], args['pwd'], args.pop('dbq', 'racadmpe'),
                                                        threaded=opts.pop('threaded', False))
                        break
                    except DatabaseError as ex:  # connection requests exceeded, let's wait and retry
                        if ex.message.code == 12516:  # pylint: disable=E1101
                            sleep(3 + random())
                        else:  # otherwise reraise
                            raise
                else:
                    raise AdasDBError("couldn't open database")
                self._arraysize = opts.pop("arraysize", None)

            self._db_type = DBTYPE.index(str(self._db_connection)[1:].split('.')[0])
        else:
            self._db_connection = db_connection
            self._connstr[0] = str(db_connection)
            self._db_type = DBTYPE.index(str(self._db_connection)[1:].split('.')[0])

        self.db_func_map[DB_FUNC_NAME_MIN] = "MIN"
        self.db_func_map[DB_FUNC_NAME_MAX] = "MAX"
        self.db_func_map[DB_FUNC_NAME_LOWER] = "LOWER"
        self.db_func_map[DB_FUNC_NAME_UPPER] = "UPPER"
        self.db_func_map[DB_FUNC_NAME_GETDATE] = "GETDATE()"

        if self._db_type >= 2:
            self._db_type = -1
            if self._table_prefix != "":
                self.execute("ALTER SESSION SET CURRENT_SCHEMA = %s" % self._table_prefix)
            username = ("'%s'" % self._table_prefix) if len(self._table_prefix) > 0 else "(SELECT USER FROM DUAL)"
            self._tablequery = SQL_TABLENAMES[-1].replace("$NM", username).replace("$TS", self._ident[2:])
            self._columnquery = SQL_COLUMNS[-1][1].replace("$NM", username)
            username = self.execute("SELECT sys_context('USERENV', 'SESSION_USER') FROM dual")[0][0]
            self.role = ROLE_DB_ADMIN if ROLE_DB_ADMIN in username.upper() else ROLE_DB_USER

            self.execute("ALTER SESSION SET NLS_COMP=LINGUISTIC")
            self.execute("ALTER SESSION SET NLS_SORT=BINARY_CI")
            self.execute("ALTER SESSION SET NLS_DATE_FORMAT = '%s'" % ORACLE_DATETIME_FORMAT)
        else:
            self.role = ROLE_DB_ADMIN
            self._tablequery = SQL_TABLENAMES[self._db_type].replace("$TS", self._table_prefix)
            self._columnquery = SQL_COLUMNS[self._db_type][1]

        if self._enable_fks and self._db_type == 0:  # off per default to keep unittests running
            self.execute("PRAGMA FOREIGN_KEYS = ON")
        if not self._auto_commit:
            self.commit()

        self.date_time_format = DEFAULT_DATETIME_FORMAT
        # retrieve the sub schema version
        try:
            self._sub_versions = {i[0]: i[1] for i in self.execute("SELECT SUBSCHEMEPREF, SUBSCHEMEVERSION "
                                                                   "FROM VERSIONS")}
        except:
            self._sub_versions = {}

        # retrieve the who is the current user gbl_user table
        try:
            self.current_gbluserid = self.execute("SELECT USERID FROM GBL_USERS WHERE LOGINNAME = $CU")[0][0]
        except:
            self.current_gbluserid = None

    def __del__(self):
        """if not Terminate(d) yet, we should do a bit here, I think
        """
        if self._direct_conn:
            self.close()

    def __str__(self):
        """return some self descriptive information
        """
        return ("connection: %s, DB prefix: %s, type: %s" %
                (str(self._db_connection), self._table_prefix, DBTYPE[self._db_type]))

    def __enter__(self):
        """being able to use with statement
        """
        return self

    def __exit__(self, *_):
        """close connection"""
        if self._direct_conn:
            self.close()

    @property
    def foreign_keys(self):
        """retrieve foreign_keys settings"""
        return self._enable_fks if self._db_type == 0 else True

    @foreign_keys.setter
    def foreign_keys(self, switch):
        """switch on or off foreign key support for sqlite

        :param switch: set foreign_keys ON / OFF (True / False)
        """
        if self._db_type == 0:
            self.execute("PRAGMA FOREIGN_KEYS = " + ("ON" if switch else "OFF"))

    @property
    def connection(self):
        """internal connection string, returns [<connection string>, <table prefix>]"""
        return self._connstr

    @property
    def db_type(self):
        """return a string about what type of DB we have here."""
        return self._db_type, DBTYPE[self._db_type]

    @property
    def ident_str(self):
        """return my own ident
        """
        return self._ident

    def close(self):
        """Terminate the database proxy"""
        if self._db_connection is not None:
            self._db_connection.close()
        self._db_connection = None
        self._connstr[0] = None

    def commit(self):
        """Commit the pending transactions"""
        self._db_connection.commit()

    def rollback(self):
        """Rollback the pending transactions"""
        self._db_connection.rollback()

    def vacuum(self):
        """vacuums sqlite DB"""
        if self._db_type == 0 and self.execute("pragma auto_vacuum")[0][0] == 0:
            self.execute("vacuum")

    def cursor(self):
        """Get the current cursor of DB: only use it if you *really* know what you're doing!!!
        """
        return self._db_connection.cursor()

    def make_var(self, vartype):
        """
        Create a cx_Oracle variable.

        :param vartype: Create a variable associated with the cursor of the given type and
                        characteristics and return a variable object.
        :type vartype: string. Could be 'number' or 'blob'.
        :rtype: object

        :raises AdasDBError: on unknown connection (not oracle, nor sqlite)
        """
        if self._db_type == -1:
            return self._db_connection.cursor().var(CX_VARS[vartype.lower()])  # pylint: disable=E1103
        elif self._db_type == 0:
            return SQ_VARS[vartype.lower()]
        else:
            raise AdasDBError("connection doesn't support var creation!")

    @property
    def table_prefix(self):
        """returns tables prefix used for select queries"""
        return self._table_prefix

    # ====================================================================
    # Handling of generic data.
    # ====================================================================

    def select_generic_data(self, *args, **kwargs):
        """
        Select generic data from a table.

        :param args: list of arguments, covered by kwargs in following order
        :param kwargs: optional arguments
        :keyword select_list: list of selected table columns (list)
        :keyword table_list: list of table names from which to select data (list | None)
        :keyword where: additional condition that must hold for the scenarios to be returned (SQLBinaryExpression)
        :keyword group_by: expression defining the columns by which selected data is grouped (list | None)
        :keyword having: expression defining the conditions that determine groups (SQLExpression)
        :keyword order_by: expression that defines the order of the returned records (list | None)
        :keyword distinct_rows: set True or list of rows, if only distinct rows shall be returned (bool | list)
        :keyword splparams: additional sql parameters passed with the query. see ``execute`` for supported keywords
        :keyword with_clause: Expression defining the clause(s) after the WITH command at beginning of the query
        :return: Returns the list of selected data.
        :rtype: list
        """
        opt = arg_trans([['select_list', ['*']], 'table_list', 'where', 'group_by', 'having', 'order_by',
                         ['distinct_rows', False], ['sqlparams', {}], 'with_clause'], *args, **kwargs)
        sql_select_stmt = self._sql_factory.GetSelectBuilder()
        sql_select_stmt.with_clause = opt[8]
        sql_select_stmt.select_list = opt[0]
        sql_select_stmt.table_list = opt[1]
        sql_select_stmt.where_condition = opt[2]
        sql_select_stmt.group_by_list = opt[3]
        sql_select_stmt.having_condition = opt[4]
        sql_select_stmt.order_by_list = opt[5]
        sql_select_stmt.distinct_rows = opt[6]
        sql_param = opt[7]
        sql_param['incDesc'] = True
        return self.execute(str(sql_select_stmt), **sql_param)  # pylint: disable=W0142

    def select_generic_data_compact(self, *args, **kwargs):
        """Select generic data from a table.

        :param args: list of arguments, covered by kwargs in following order
        :param kwargs: optional arguments
        :keyword select_list: List of selected table columns.
        :keyword table_list: List of table names from which to select data.
        :keyword where: The additional condition that must hold for the scenarios to be returned.
        :keyword group_by: Expression defining the columns by which selected data is grouped.
        :keyword having: Expression defining the conditions that determine groups.
        :keyword order_by: Expression that defines the order of the returned records.
        :keyword distinct_rows: Set True, if only distinct rows shall be returned.
        :keyword splparams: additional sql parameters passed with the query. see ``execute`` for supported keywords
        :keyword with_clause: Expression defining the clause(s) after the WITH command at beginning of the query
        :return: Returns the list of selected data.
        """
        opt = arg_trans([['select_list', ['*']], 'table_list', 'where', 'group_by', 'having', 'order_by',
                         ['distinct_rows', False], ['sqlparams', {}], 'with_clause'], *args, **kwargs)
        sql_select_stmt = self._sql_factory.GetSelectBuilder()
        sql_select_stmt.with_clause = opt[8]
        sql_select_stmt.select_list = opt[0]
        sql_select_stmt.table_list = opt[1]
        sql_select_stmt.where_condition = opt[2]
        sql_select_stmt.group_by_list = opt[3]
        sql_select_stmt.having_condition = opt[4]
        sql_select_stmt.order_by_list = opt[5]
        sql_select_stmt.distinct_rows = opt[6]
        sql_param = opt[7]
        sql_param['iterate'] = True
        cursor = self.execute(str(sql_select_stmt), **sql_param)  # pylint: disable=W0142
        try:
            rows = cursor.fetchall()
            field_list = []
            for column in cursor.description:
                field_list.append(column[0].upper())
        except:
            raise
        finally:
            cursor.close()
        # If the select is just for one column, cursor produces bad results.
        if len(opt['select_list']) == 1 and opt['select_list'][0] != "*" \
                and type(opt['select_list'][0]) is not SQLColumnExpr:
            row_list = [[row[0]] for row in rows]
        else:
            row_list = rows
        # done
        return [field_list, row_list]

    def add_generic_data(self, record, table_name, returning=None):
        """Add generic data to database.

        :param record: The data record to be added to the database.
        :param table_name: The name of the table into which to add the data.
        :param returning: column of autoincrement index of newly added record to get in return
        """
        # build statement
        sql_insert_stmt = self._sql_factory.GetInsertBuilder()
        sql_insert_stmt.table_name = table_name
        sql_insert_stmt.assign_items = record
        sql_insert_stmt.returning = returning

        return self.execute(str(sql_insert_stmt), incDesc=True)

    def add_generic_compact_prepared(self, col_names, values, table_name):
        """
        Add Generic data with prepared statement with compact data as input

        :param col_names: list of column names for values are specified
        :type col_names: list
        :param values: list of tuple contain tuple length and order must be align with col_names
        :type values: list
        :param table_name: Name of the table
        :type table_name: String
        """
        sql_insert_prep_stmt = self._sql_factory.GetPreparedInsertBuilder()
        sql_insert_prep_stmt.table_name = table_name
        sql_insert_prep_stmt.assign_items = col_names
        self.execute(str(sql_insert_prep_stmt), insertmany=values)

    def add_generic_data_prepared(self, records, table_name):
        """Add generic data to database.

        :param records: The data record to be added to the database.
        :type records: list of dict
        :param table_name: The name of the table into which to add the data.
        """

        if len(records) and type(records) is list:
            # build statement
            rowcount = 0
            sql_insert_prep_stmt = self._sql_factory.GetPreparedInsertBuilder()
            sql_insert_prep_stmt.table_name = table_name
            sql_insert_prep_stmt.assign_items = records[0].keys()
            stmt = str(sql_insert_prep_stmt)
            values = [tuple(record.values()) for record in records]
            # insert data
            cursor = self._db_connection.cursor()
            try:
                self._log.debug(stmt)
                cursor.executemany(stmt, values)
                # rowcount = cursor.rowcount
            except Exception as ex:
                self._log.error(stmt)
                self._log.exception(str(ex))
                raise
            finally:
                cursor.close()
            return rowcount

    def update_generic_data(self, record, table_name, where=None, sqlparams={}):
        """
        Update an existing record in the database.

        :param record: The data to be updated.
        :type record: dict
        :param table_name: The name of the table.
        :type table_name: str
        :param where: The condition to be fulfilled by the states to be updated.
        :type where: SQLBinaryExpression
        :return: Returns the number of affected rows.
        :rtype: Integer
        """
        sql_update_stmt = self._sql_factory.GetUpdateBuilder()
        sql_update_stmt.table_name = table_name
        sql_update_stmt.assign_items = record
        sql_update_stmt.where_condition = where
        sqlparams['incDesc'] = True
        try:
            return self.execute(str(sql_update_stmt), **sqlparams)  # pylint: disable=W0142
        except:
            self._log.exception(str(sql_update_stmt))
        return 0

    def delete_generic_data(self, table_name, where=None, sqlparams={}):
        """Delete records from a table.

        :param table_name: The name of the table to deleted the data from.
        :param where: The condition to be fulfilled by the states to be deleted.
        :return: Returns the number of affected rows.
        """
        sql_stmt = self._sql_factory.GetDeleteBuilder()
        sql_stmt.table_name = table_name
        sql_stmt.where_condition = where
        stmt = str(sql_stmt)
        # delete data
        rowcount = 0
        cursor = self._db_connection.cursor()
        try:
            self._log.debug(stmt)
            cursor.execute(stmt, sqlparams)
            # rowcount = cursor.rowcount      #was commented out, but e.g. used in cgeb_fctlabel -> ?
        except:
            self._log.exception(stmt)
            raise AdasDBError(stmt)
        finally:
            cursor.close()
        # done
        return rowcount

    def _get_next_id(self, table_name, col_name):
        """Get the next ID of a column

        :param table_name: The name of the table.
        :param col_name: The name of the column to get the next ID. The column type must be integral
        :return: Returns the next available ID.
        """
        return self.execute("SELECT NVL(MAX(%s), -1) + 1 FROM %s" % (col_name, table_name))[0][0]

    @property
    def auto_commit(self):
        """states if after each insert / update / change a commit should be placed or not
        """
        return self._auto_commit

    @auto_commit.setter
    def auto_commit(self, val):
        """sets internal auto commit flag on executions

        :param val: do you want to commit at each statement, set it to True or False
        :type val: bool
        """
        self._auto_commit = val

    def execute(self, statement, *args, **kwargs):
        """
        Execute SQL statement(s).

        Multiple statements can be semicolon (;) separated.
        Below listed arguments are in use, others are directly passed through to the DB cursor

        :param statement: sql command to be executed
        :type statement: str
        :param args: Variable length argument list to execute method of cursor.
        :param kwargs: Arbitrary keyword arguments, whereas insertmany, incDesc, iterate and id are extracted
                       and rest flows into cursor's execute method.

        :keyword insertmany: supports insertion of many items which improves speed, here you need to provide a
                             list of tuples to be inserted, defaults to None, valid param type is bool.
        :keyword incDesc: include the description when doing a select as first row, defaults to False, type is bool
        :keyword iterate: with it you can iterate over cursor(), but take care to close cursor afterwards

        :return: in case of an insert or update statement, column count (int) is returned. Within an insert statement,
                 you can specify a returning row id, e.g. *insert into table values (7, 'dummy') returning idx*
                 whereas idx would be primary key of table which is autoincreased and it's new value is returned.

                 in case of an select statement, all rows (list) are returned.
                 When ``incDesc`` is set to True, a list of dicts for each row is returned

        :raises AdasDBError: when statement cannot be executed
        """
        # ommit: insertmany, incDesc, iterate, id
        insertmany = kwargs.pop('insertmany', None)
        incdesc = kwargs.pop('incDesc', False)
        iterate = kwargs.pop('iterate', False)
        commit = kwargs.pop('commit', self._auto_commit)
        cursor = None

        # helper to return proper insertion ID
        pat = search(r"(?i)returning\s(\w*)$", statement)
        retlastid = False
        if pat is not None:
            if self._db_type == -1:
                statement = statement[:pat.regs[1][0]] + pat.groups()[0] + " INTO :id"
                rid = self.make_var('number')
                kwargs['id'] = rid
            elif self._db_type == 0:
                statement = statement[:pat.start() - 1]
                retlastid = True
        # we can also replace $DT as current date time, $CD as current date and $CT as current time
        if "$" in statement:
            statement = statement.strip().replace("$DT", "SYSDATE" if self._db_type == -1 else "CURRENT_TIMESTAMP")\
                .replace("$CD", "CURRENT_DATE")\
                .replace("$CT", "CURRENT_TIMESTAMP" if self._db_type == -1 else "CURRENT_TIME") \
                .replace(" None ", " null ") \
                .replace("$ST", "SYSTIMESTAMP" if self._db_type == -1 else "CURRENT_TIMESTAMP")
            if "$CU" in statement:
                kwargs['usr'] = environ['username']
                statement = statement.replace("$CU", ":usr")
            if "$UID" in statement:
                kwargs['usrid'] = self.current_gbluserid
                statement = statement.replace("$UID", ":usrid")

        if self._db_type == 0:
            statement = statement.replace('NVL', 'IFNULL')
            if len(kwargs):
                args = []
                for i in finditer(r':(\w+)\b', statement):
                    statement = statement.replace(":" + i.group(1), "?", 1)
                    args.append(kwargs[i.group(1)])
                args = tuple(args)
        try:
            stmt = ""
            records = []
            cursor = self._db_connection.cursor()
            if self._arraysize:
                cursor.arraysize = self._arraysize

            for stmt in ([statement.strip()] if search(r'(?i)^(begin|declare)\s', statement)
                         else statement.split(';')):
                if len(stmt) == 0:
                    continue

                stmt = stmt.strip()
                self._log.debug(stmt)

                # remove keyword to get more ease in checking later on
                cmd = stmt.split(' ', 1)[0].lower()

                # exec
                if cmd == "insert" and insertmany is not None and all(type(i) == tuple for i in insertmany):
                    cursor.executemany(stmt, insertmany)
                else:
                    if self._db_type == 0:
                        cursor.execute(stmt, args)
                    else:
                        cursor.execute(stmt, **kwargs)

                if cmd in ("select", "pragma", "with", "declare"):
                    if type(records) == int:
                        records = int(cursor.fetchone()[0])
                    elif incdesc and cursor.description is not None:
                        desc = [d[0].upper() for d in cursor.description]
                        for rec in cursor:
                            records.append({desc[i]: rec[i] for i in xrange(len(desc))})
                    elif iterate:
                        records = cursor
                    else:
                        records.extend(cursor.fetchall())
                elif cmd == "execute":
                    # remove 'execute ', find & remove brackets, split args, strip quotes and recombine
                    params = [ii.strip(" '") for ii in self._func_params.findall(stmt[8:])[0].strip('()').split(',')]
                    records = cursor.callproc(stmt[0:stmt.find('(')].strip(), params)
                elif cmd == "func":
                    records = cursor.callfunc(stmt.split(' ')[1], *args, **kwargs)  # pylint: disable=E1103
                elif cmd == "proc":
                    records = cursor.callproc(stmt.split(' ')[1], *args, **kwargs)
                else:
                    records = cursor.rowcount
                    if commit:  # commit if not switched off
                        self._db_connection.commit()

                    if pat is not None and self._db_type == -1:  # grab the returning ID if oracle
                        records = int(rid.getvalue())
                    elif retlastid:
                        records = cursor.lastrowid  # pylint: disable=E1103

        except Exception as ex:
            iterate = False
            raise AdasDBError(stmt + ": " + str(ex))
        finally:
            if not iterate and cursor:
                cursor.close()

        # done
        return records

    def executex(self, statement, *args, **kwargs):  # pylint: disable=R0912
        """Execute SQL statement(s). Multiple statements can be semicolon (;) separated

        :param statement: SQL query, supported statements: select, insert, update, delete, execute
        :keyword insertmany: used to insert more then one item into DB
        :keyword incdesc: include the description when doing a select as first row
        :return: returns all rows
        """
        kwargs['iterate'] = True
        lobo = kwargs.pop('lob', None)
        cur = self.execute(statement, *args, **kwargs)
        try:
            for i in cur:
                if lobo:
                    yield self._lob_conv(i, [lobo])
                else:
                    yield i
        finally:
            cur.close()

    def sql(self, statement, *args, **kw):
        """Execute SQL statement(s) more simpler / faster.

        Below listed arguments are in use, others are directly passed through to the DB cursor

        :param statement: sql command to be executed
        :type statement: str
        :param args: additional arguments to connection's execute
        :param kw: keyword arguments to connection's execute
        :return: list of records (tuples usually)
        """
        iterate = kw.pop('iterate', False)
        cursor = self._db_connection.cursor()

        try:
            # remove keyword to get more ease in checking later on
            cmd = statement.split(' ', 1)[0].lower()

            if cmd in ("select", "with"):
                cursor.execute(statement, *args, **kw)
                if iterate:
                    records = cursor
                else:
                    records = cursor.fetchall()
            elif cmd in ("alter", "insert", "update", "delete"):
                cursor.execute(statement, *args, **kw)
                records = cursor.rowcount
                if self._auto_commit:
                    self._db_connection.commit()
            elif cmd == "proc":
                records = cursor.callproc(statement.split(' ', 1)[1], *args, **kw)
            elif cmd == "func":
                records = cursor.callfunc(statement.split(' ', 1)[1], *args, **kw)  # pylint: disable=E1103
            else:
                raise AdasDBError("unknown command")
        except Exception as ex:
            raise AdasDBError("DB exception: " + str(ex))
        finally:
            if not iterate:
                cursor.close()

        # done
        return records

    # ====================================================================
    # Version methods
    # ====================================================================

    @property
    def sub_scheme_version(self):
        """Returns version number of the component as int.
        """
        return self._sub_versions.get(IDENT_SPACE[self._ident])

    def sub_scheme_versions(self):
        """Returns all the subschema version from validation database.
        """
        return [{COL_NAME_SUBSCHEMEVERSION: v, COL_NAME_SUBSCHEMEPREF: k} for k, v in self._sub_versions.iteritems()]

    # ====================================================================
    # aditive methods
    # ====================================================================

    def timestamp_to_date(self, timestamp):
        """ Convert a timestamp to a date-time of the database

        :param timestamp: The timestamp to convert
        :return: Returns the date-time expression
        """
        if self._db_type == 0:
            return SQLDate(datetime.fromtimestamp(timestamp).strftime(self.date_time_format))
        else:
            exp = SQLDate(datetime.fromtimestamp(timestamp).strftime(self.date_time_format))
            return SQLFuncExpr("TO_DATE", SQLListExpr([exp, "'YYYY-MM-DD HH24:MI:SS'"]))

    @property
    def table_names(self):
        """Returns a list of table names belonging to own table space, e.g. ``CL_``, ``CAT_``, ``GBL_``, etc.
        """
        return [str(i[0]).strip().upper() for i in self.execute(self._tablequery) if i[0] != u"sqlite_sequence"]

    def get_columns(self, table):
        """Gets a list of column names for a given table.

        :param table: name of table
        :return: list of columns
        """
        return [(str(i[SQL_COLUMNS[self._db_type][0][0]]), str(i[SQL_COLUMNS[self._db_type][0][1]]))
                for i in self.execute(self._columnquery.replace('$TBL', table).replace('$TP', self._table_prefix))]

    def get_primary_key(self, table):
        """Gets the primary key column(s).

        :param table: name of table
        :return: list of columns
        """
        if self._db_type == -1:
            return [i[0] for i in self.execute("SELECT COLUMN_NAME FROM ALL_CONSTRAINTS c "
                                               "INNER JOIN ALL_CONS_COLUMNS USING(OWNER, CONSTRAINT_NAME) "
                                               "WHERE c.CONSTRAINT_TYPE = 'P' AND c.TABLE_NAME = :tbl", tbl=table)]
        elif self._db_type == 0:
            return [i[1] for i in self.execute("PRAGMA table_info(%s)" % table) if i[-1] == 1]
        else:
            raise AdasDBError("DB type not supported!")

    def get_foreign_keys(self, table):
        """Gets the foreign key column(s)

        :param table: name of table to query
        :return: tuple containing references to, e.g. (("PARENTID", "TABLE.ID"), ...,)
        """
        if self._db_type == -1:
            sql = "SELECT lcol.COLUMN_NAME, rcol.TABLE_NAME || '.' || rcol.COLUMN_NAME " \
                  "FROM ALL_CONSTRAINTS acon, ALL_CONS_COLUMNS lcol, ALL_CONS_COLUMNS rcol " \
                  "WHERE acon.TABLE_NAME = :tbl " \
                  "AND acon.CONSTRAINT_NAME = lcol.CONSTRAINT_NAME AND acon.R_CONSTRAINT_NAME = rcol.CONSTRAINT_NAME"
            return self.execute(sql, tbl=table)
        elif self._db_type == 0:
            sql = "SELECT SQL FROM (" \
                  "SELECT SQL, type, tbl_name, name FROM sqlite_master UNION ALL " \
                  "SELECT sql, type, tbl_name, name FROM sqlite_temp_master) " \
                  "WHERE type != 'meta' AND sql NOT NULL AND name NOT LIKE 'sqlite_%' " \
                  "AND sql LIKE '%REFERENCES%' AND TBL_NAME = :tbl"
            stmt = self.execute(sql, tbl=table)
            if len(stmt) == 0:
                return ()
            tpl = tuple([(i.group(2) if i.group(3) is None else i.group(3), "%s.%s" % (i.group(4), i.group(5)),)
                         for i in finditer(r'(?i)(\s+\[?([_A-Za-z0-9]+)\]?\s+.*constraint\s+\[?[_A-Za-z0-9]+\]?|'
                                           r'\(([_A-Za-z0-9]+).*\)).*references\s+\[?"?([_A-Za-z0-9]+)"?\]?\s*'
                                           r'\(\[?([_A-Za-z0-9]+)\]?\)', stmt[0][0])])
            return tpl
        else:
            raise AdasDBError("DB type not supported!")

    def curr_date_time(self):
        """Get the current date/time of the database.

        :return: Returns the current date time of the database
        """
        return str(self.execute(SQL_DATETIME[self._db_type])[0][0])

    def curr_datetime_expr(self):
        """Get expression that returns current date/time of database"""
        return SQL_DT_EXPR[self._db_type]

    # ====================================================================
    # deprecated methods and properties
    # ====================================================================

    @staticmethod
    def GetQualifiedTableName(table_base_name):  # pylint: disable=C0103
        """Deprecated and without warning as too many calls are used by now.
        Those would just pollute output
        """
        return table_base_name

    @deprecated('select_generic_data')
    def SelectGenericData(self, *args, **kwargs):  # pylint: disable=C0103
        """deprecated"""
        return self.select_generic_data(*args, **kwargs)

    @deprecated('select_generic_data_compact')
    def SelectGenericDataCompact(self, *args, **kwargs):  # pylint: disable=C0103
        """deprecated"""
        return self.select_generic_data_compact(*args, **kwargs)

    @deprecated('add_generic_data')
    def AddGenericData(self, record, table_name):  # pylint: disable=C0103
        """deprecated"""
        return self.add_generic_data(record, table_name)

    @deprecated('add_generic_data_prepared')
    def AddGenericPreparedData(self, records, table_name):  # pylint: disable=C0103
        """deprecated"""
        return self.add_generic_data_prepared(records, table_name)

    @deprecated('delete_generic_data')
    def DeleteGenericData(self, table_name, where=None, sql_param={}):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_generic_data(table_name, where, sql_param)

    @deprecated('update_generic_data')
    def UpdateGenericData(self, record, table_name, where=None, sql_param={}):  # pylint: disable=C0103
        """deprecated"""
        return self.update_generic_data(record, table_name, where, sql_param)

    @deprecated()
    def GetConnectString(self, *args, **kw):  # pylint: disable=C0103
        """deprecated, as BaseDB can be use by predefined values, e.g. 'ARS4XX', 'MFC4XX', 'algo' or direct
         filename in case of SDF or SQLITE extension.

        Builds the connection string for the DB.
        The arguments must contain the values for the connection string as [DRIVER, DSN, DBQ, Uid, Pwd].
        All elements have type string in the list with the following details:
        * DRIVER: ODBC Driver Name to be provide when using pyodbc driver
        * DSN: Data source Name to be provided when using pydobc driver
        * DSN: str
        * DBQ: TNS service name of the Oracle database
        * DBQ: str
        * Uid: Username to login to the Oracle database
        * Uid: str
        * Pwd: Password to login to the Oracle database
        * Pwd: str

        :keyword dbdriver: ODBC driver name to be provided when using pyodbc driver.
                           If not provided, default value will be used.
        :type dbdriver: str
        :return: Database connection string
        :rtype: str
        """
        if self._db_type == 0:
            return args[1]
        elif self._db_type == 1:
            return "Provider=%s;Data Source=%s;" % (args[0], args[1])
        else:  # dbdsn, dbdbq, dbuser, dbpassword, dbdriver=DEFAULT_MASTER_DRV:
            if args[0] is None:
                connect_str = "DRIVER={%s};" % (args[4] if len(args) > 4 else kw.pop("dbdriver", DEFAULT_MASTER_DRV))
            else:
                connect_str = "DSN=%s;" % args[0]
            if args[1] is not None:
                connect_str += "DBQ=%s;" % args[1]
            if args[2] is not None:
                connect_str += "Uid=%s;" % args[2]
            if args[3] is not None:
                connect_str += "Pwd=%s;" % args[3]
            return connect_str

    @property
    def db_connection(self):
        """:returns raw DB connection"""
        return self._db_connection

    @property
    @deprecated('ident_str')
    def strIdent(self):  # pylint: disable=C0103
        """return my own ident
        """
        return self.ident_str

    @deprecated()
    def initialize(self):
        """deprecated"""
        pass

    @deprecated()
    def Initialize(self):  # pylint: disable=C0103
        """deprecated"""
        pass

    @deprecated('close')
    def Terminate(self):  # pylint: disable=C0103
        """deprecated"""
        self.close()

    @deprecated('close')
    def terminate(self):
        """deprecated"""
        self.close()

    @deprecated('commit')
    def Commit(self):  # pylint: disable=C0103
        """deprecated"""
        self.commit()

    @deprecated('rollback')
    def Rollback(self):  # pylint: disable=C0103
        """deprecated"""
        self.rollback()

    @deprecated('cursor')
    def Cursor(self):  # pylint: disable=C0103
        """deprecated"""
        return self.cursor()

    @property
    @deprecated('auto_commit')
    def autoCommit(self):  # pylint: disable=C0103
        """deprecated"""
        return self.auto_commit

    @autoCommit.setter
    @deprecated('auto_commit')
    def autoCommit(self, val):  # pylint: disable=C0103
        """deprecated"""
        self.auto_commit = val

    @deprecated('table_names (property)')
    def GetTableNames(self):  # pylint: disable=C0103
        """deprecated"""
        return self.table_names

    @deprecated('get_columns')
    def GetColumns(self, tableName):  # pylint: disable=C0103
        """deprecated"""
        return self.get_columns(tableName)

    @property
    @deprecated('db_type')
    def dbType(self):  # pylint: disable=C0103
        """deprecated"""
        return self.db_type

    @deprecated('sub_scheme_version')
    def GetSubSchemeVersion(self, SubSchemeTag):  # pylint: disable=C0103
        """deprecated"""
        return self.sub_scheme_version(SubSchemeTag)

    @deprecated('sub_scheme_versions')
    def GetSubSchemeVersions(self):  # pylint: disable=C0103
        """deprecated"""
        return self.sub_scheme_versions()

    @deprecated('curr_date_time')
    def GetCurrDateTime(self):  # pylint: disable=C0103
        """deprecated"""
        return self.curr_date_time()

    @deprecated('timestamp_to_date')
    def ConvertTimestampToDate(self, timestamp):  # pylint: disable=C0103
        """deprecated"""
        return self.timestamp_to_date(timestamp)

    @deprecated('curr_datetime_expr')
    def GetCurrDateTimeExpr(self):  # pylint: disable=C0103
        """deprecated"""
        return self.curr_datetime_expr()


# ====================================================================
# Interface helper classes
# ====================================================================
class PluginBaseDB(object):
    """used by plugin finder"""
    pass


class OracleBaseDB(object):
    """deprecated"""
    pass


class SQLCEBaseDB(object):
    """deprecated"""
    pass


class SQLite3BaseDB(object):
    """deprecated"""
    pass


# - functions ---------------------------------------------------------------------------------------------------------
# ====================================================================
# Connection string initialization
# ====================================================================
def GetOracleConnectString(dbdsn, dbdbq, dbuser, dbpassword, dbdriver=DEFAULT_MASTER_DRV):  # pylint: disable=C0103
    """
    Build the connection string for Oracle 11g.

    :param dbdsn: Data Source Name
    :type dbdsn: str
    :param dbdbq: TNS service name of the Oracle database to which you want to connect to
    :type dbdbq: str
    :param dbuser: Username
    :type dbuser: str
    :param dbpassword: Password
    :type dbpassword: str
    :param dbdriver: Name of the driver to connect to the database
    :type dbdriver: str
    :return: Returns the Oracle connection string.
    :rtype: str
    """
    if dbdsn is not None:
        connect_str = "DSN=%s;" % dbdsn
    else:
        connect_str = "DRIVER={%s};" % dbdriver
    if dbdbq is not None:
        connect_str += "DBQ=%s;" % dbdbq
    if dbuser is not None:
        connect_str += "Uid=%s;" % dbuser
    if dbpassword is not None:
        connect_str += "Pwd=%s;" % dbpassword
    return connect_str


def GetSQLCEConnectString(dbprovider, dbsource):  # pylint: disable=C0103
    """
    Build the connection string for SQL Server Compact

    Remark
      - May be add SSCE: Default Lock Timeout=20000;
      - May be add SSCE: Max Database Size=1024;

    :param dbsource: Path to the SQL Server Compact database file
    :type dbsource: str
    :param dbprovider:
    :type dbprovider: str
    :return: Returns the SQL Server Compact connection string
    :rtype: str
    """
    return "Provider=%s;Data Source=%s;" % (dbprovider, dbsource)


def GetSQLite3ConnectString(dbsource):  # pylint: disable=C0103
    """
    Build the connection string for SQL Lite.

    only file names are supported: http://www.connectionstrings.com/

    :param dbsource: Path to the SQLite3 database file
    :type dbsource: str
    :return: SQLite connection string
    :rtype: str
    """
    return dbsource


# ====================================================================
# Table prefix
# ====================================================================
def GetFullTablePrefix(schema_prefix, base_table_prefix):  # pylint: disable=C0103
    """ Determine the table prefix from a schema prefix and a base table prefix

    :param schema_prefix: The prefix of the database schema (may be None)
    :param base_table_prefix: The base prefix of the data base tables in the schema (may be None)
    """
    table_prefix = None
    if schema_prefix is not None:
        table_prefix = schema_prefix + SCHEMA_PREFIX_SEPARATOR
    if base_table_prefix is not None:
        if table_prefix is not None:
            table_prefix = "%s%s%s" % (table_prefix, base_table_prefix, TABLE_PREFIX_SEPARATOR)
        else:
            table_prefix = "%s%s" % (base_table_prefix, TABLE_PREFIX_SEPARATOR)
    return table_prefix


"""
CHANGE LOG:
-----------
$Log: db_common.py  $
Revision 1.37 2017/07/21 12:36:37CEST Hospes, Gerd-Joachim (uidv8815) 
allow collumn expression in select_generic_data_compact()
Revision 1.36 2017/04/04 08:21:28CEST Mertens, Sven (uidv7805)
join import
Revision 1.35 2017/04/04 08:19:38CEST Mertens, Sven (uidv7805)
fix for 64bit
Revision 1.34 2017/02/12 13:55:41CET Hospes, Gerd-Joachim (uidv8815)
pep8 fixes
Revision 1.33 2017/02/07 19:32:35CET Hospes, Gerd-Joachim (uidv8815)
change size of result description and name, adappt test to check on Oracle,
fix date setting, still problem: Oracle returned date can not be used as input for date
Revision 1.32 2016/08/16 12:26:19CEST Hospes, Gerd-Joachim (uidv8815)
update module and class docu
Revision 1.31 2016/08/15 14:24:51CEST Mertens, Sven (uidv7805)
another fix for FK quest
Revision 1.30 2016/07/14 08:21:06CEST Mertens, Sven (uidv7805)
enabling sqlite version check again on connection as removed from valf
Revision 1.29 2016/07/13 13:04:32CEST Mertens, Sven (uidv7805)
- enable FK's per default, same way Oracle does,
- use as instead of comma
Revision 1.28 2016/07/12 09:03:54CEST Mertens, Sven (uidv7805)
provide foreign key retrieval method supporting oracle and sqlite
Revision 1.27 2016/07/11 11:36:40CEST Mertens, Sven (uidv7805)
we already have current userid, so we should use it
Revision 1.26 2016/07/11 09:13:55CEST Mertens, Sven (uidv7805)
new appreviation for systimestamp: $ST
Revision 1.25 2016/07/06 13:50:56CEST Mertens, Sven (uidv7805)
we need agregates on top (hard to test)
Revision 1.24 2016/06/23 15:30:47CEST Hospes, Gerd-Joachim (uidv8815)
fix for empty description
Revision 1.23 2016/06/23 15:03:32CEST Mertens, Sven (uidv7805)
using finally, closes 100%
Revision 1.22 2016/06/17 12:06:39CEST Mertens, Sven (uidv7805)
providing some new functionalities:
- cursor iterator (executex),
- sqlite journal mode off (2B faster),
- PK columns
Revision 1.21 2016/06/13 08:27:36CEST Hospes, Gerd-Joachim (uidv8815)
rem from DbBase, start singlton logger with special stream as very first step
Revision 1.20 2016/06/10 17:09:15CEST Hospes, Gerd-Joachim (uidv8815)
update and add test for logstrm
Revision 1.19 2016/06/10 16:02:49CEST Mertens, Sven (uidv7805)
pass through logger stream if in kwargs (used by VAT)
Revision 1.18 2016/06/09 09:29:18CEST Mertens, Sven (uidv7805)
only repeat on timeout, for others, reraise
Revision 1.17 2016/05/30 18:50:47CEST Hospes, Gerd-Joachim (uidv8815)
changed shared coll queries, add tests in test_collections
Revision 1.16 2016/05/30 17:21:44CEST Mertens, Sven (uidv7805)
try to reconnect again and again as connection pooling could be full...
Revision 1.15 2016/04/04 17:40:35CEST Hospes, Gerd-Joachim (uidv8815)
fix epydoc errors
Revision 1.14 2016/04/04 12:17:52CEST Mertens, Sven (uidv7805)
username fix
Revision 1.13 2016/03/29 17:37:24CEST Mertens, Sven (uidv7805)
xtra commit needed
Revision 1.12 2016/02/12 10:41:03CET Ahmed, Zaheer (uidu7634)
bug fix to handle distinct_row in select_generic_data()
select_generic_data_compact() adapted to reuse self.execut() like other methods
Revision 1.11 2016/02/11 16:52:01CET Mertens, Sven (uidv7805)
supporting vacuum for sqlite DB schrinkage
Revision 1.10 2015/11/06 13:30:26CET Mertens, Sven (uidv7805)
column query fix for sqlite
--- Added comments ---  uidv7805 [Nov 6, 2015 1:30:26 PM CET]
Change Package : 394407:1 http://mks-psad:7002/im/viewissue?selection=394407
Revision 1.9 2015/10/13 13:25:03CEST Mertens, Sven (uidv7805)
argument fix
--- Added comments ---  uidv7805 [Oct 13, 2015 1:25:03 PM CEST]
Change Package : 380875:1 http://mks-psad:7002/im/viewissue?selection=380875
Revision 1.8 2015/10/13 12:02:58CEST Mertens, Sven (uidv7805)
fixing arguments bug for sqlite / oracle
--- Added comments ---  uidv7805 [Oct 13, 2015 12:02:58 PM CEST]
Change Package : 380875:1 http://mks-psad:7002/im/viewissue?selection=380875
Revision 1.7 2015/07/16 16:10:23CEST Ahmed, Zaheer (uidu7634)
added function add_generic_compact_prepared()
--- Added comments ---  uidu7634 [Jul 16, 2015 4:10:24 PM CEST]
Change Package : 348978:3 http://mks-psad:7002/im/viewissue?selection=348978
Revision 1.6 2015/07/14 13:18:14CEST Mertens, Sven (uidv7805)
init cursor and stmt before getting lost
--- Added comments ---  uidv7805 [Jul 14, 2015 1:18:15 PM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.5 2015/07/14 08:42:08CEST Mertens, Sven (uidv7805)
adding PluginBaseDB
--- Added comments ---  uidv7805 [Jul 14, 2015 8:42:09 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.4 2015/07/13 10:17:07CEST Ahmed, Zaheer (uidu7634)
pass loginname in lower case to initialize current_gbluserid
--- Added comments ---  uidu7634 [Jul 13, 2015 10:17:07 AM CEST]
Change Package : 348978:1 http://mks-psad:7002/im/viewissue?selection=348978
Revision 1.3 2015/06/30 11:19:27CEST Mertens, Sven (uidv7805)
fix for exception handling
--- Added comments ---  uidv7805 [Jun 30, 2015 11:19:28 AM CEST]
Change Package : 350659:3 http://mks-psad:7002/im/viewissue?selection=350659
Revision 1.2 2015/05/05 13:06:30CEST Ahmed, Zaheer (uidu7634)
default value for sqlparams in select_generic_data, select_generic_data_compact,
delete_generic_data
comprehensive for loop to create list for binded values in add_generic_data_prepared
--- Added comments ---  uidu7634 [May 5, 2015 1:06:30 PM CEST]
Change Package : 318797:5 http://mks-psad:7002/im/viewissue?selection=318797
Revision 1.1 2015/04/23 19:03:52CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/project.pj
Revision 1.96 2015/04/23 08:11:31CEST Ahmed, Zaheer (uidu7634)
bug fix to work SQLIte3 as well to be discuss with Sven
--- Added comments ---  uidu7634 [Apr 23, 2015 8:11:32 AM CEST]
Change Package : 329058:2 http://mks-psad:7002/im/viewissue?selection=329058
Revision 1.95 2015/04/22 11:45:24CEST Ahmed, Zaheer (uidu7634)
added sqlparam argument for variable binding in select generic data
and iterator feature in execute method
--- Added comments ---  uidu7634 [Apr 22, 2015 11:45:24 AM CEST]
Change Package : 329058:2 http://mks-psad:7002/im/viewissue?selection=329058
Revision 1.93 2015/03/20 13:52:58CET Mertens, Sven (uidv7805)
column query update
--- Added comments ---  uidv7805 [Mar 20, 2015 1:52:59 PM CET]
Change Package : 319735:1 http://mks-psad:7002/im/viewissue?selection=319735
Revision 1.92 2015/03/20 11:47:25CET Mertens, Sven (uidv7805)
strip the commands
--- Added comments ---  uidv7805 [Mar 20, 2015 11:47:26 AM CET]
Change Package : 319735:1 http://mks-psad:7002/im/viewissue?selection=319735
Revision 1.91 2015/03/20 10:30:00CET Mertens, Sven (uidv7805)
don't use pyodbc any more, raise an error if cxoracle connection fails
--- Added comments ---  uidv7805 [Mar 20, 2015 10:30:00 AM CET]
Change Package : 319735:1 http://mks-psad:7002/im/viewissue?selection=319735
Revision 1.90 2015/03/13 10:10:21CET Mertens, Sven (uidv7805)
last docu update
--- Added comments ---  uidv7805 [Mar 13, 2015 10:10:21 AM CET]
Change Package : 316693:1 http://mks-psad:7002/im/viewissue?selection=316693
Revision 1.89 2015/03/13 09:15:21CET Mertens, Sven (uidv7805)
docu fix
--- Added comments ---  uidv7805 [Mar 13, 2015 9:15:21 AM CET]
Change Package : 316693:1 http://mks-psad:7002/im/viewissue?selection=316693
Revision 1.88 2015/03/13 08:22:15CET Mertens, Sven (uidv7805)
fix for autocommit and table names
--- Added comments ---  uidv7805 [Mar 13, 2015 8:22:16 AM CET]
Change Package : 316693:1 http://mks-psad:7002/im/viewissue?selection=316693
Revision 1.87 2015/03/05 15:10:02CET Mertens, Sven (uidv7805)
some doc update
--- Added comments ---  uidv7805 [Mar 5, 2015 3:10:02 PM CET]
Change Package : 312989:1 http://mks-psad:7002/im/viewissue?selection=312989
Revision 1.86 2015/03/03 19:31:35CET Hospes, Gerd-Joachim (uidv8815)
fix from Sven
--- Added comments ---  uidv8815 [Mar 3, 2015 7:31:35 PM CET]
Change Package : 312988:1 http://mks-psad:7002/im/viewissue?selection=312988
Revision 1.85 2015/02/26 16:54:48CET Mertens, Sven (uidv7805)
even more docu update
--- Added comments ---  uidv7805 [Feb 26, 2015 4:54:49 PM CET]
Change Package : 310834:1 http://mks-psad:7002/im/viewissue?selection=310834
Revision 1.84 2015/02/26 16:47:50CET Mertens, Sven (uidv7805)
- docu update,
- strip whitespaces from statement,
- adding arraysize support
--- Added comments ---  uidv7805 [Feb 26, 2015 4:47:50 PM CET]
Change Package : 310834:1 http://mks-psad:7002/im/viewissue?selection=310834
Revision 1.83 2015/01/29 07:58:46CET Mertens, Sven (uidv7805)
aligning naming conventions
--- Added comments ---  uidv7805 [Jan 29, 2015 7:58:47 AM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.82 2015/01/28 08:26:15CET Mertens, Sven (uidv7805)
fix for subscheme version
--- Added comments ---  uidv7805 [Jan 28, 2015 8:26:16 AM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.81 2015/01/22 16:52:23CET Mertens, Sven (uidv7805)
taking care of file name extention tuple
--- Added comments ---  uidv7805 [Jan 22, 2015 4:52:24 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.80 2015/01/22 16:15:30CET Mertens, Sven (uidv7805)
using returning statement
--- Added comments ---  uidv7805 [Jan 22, 2015 4:15:31 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.79 2015/01/20 21:40:01CET Mertens, Sven (uidv7805)
fix for wrong append
--- Added comments ---  uidv7805 [Jan 20, 2015 9:40:01 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.78 2015/01/20 14:24:38CET Mertens, Sven (uidv7805)
- removing deprecated call,
- taking over sqlite registrations from dbconnect,
- providing list of dict via execute
--- Added comments ---  uidv7805 [Jan 20, 2015 2:24:38 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.77 2015/01/13 09:38:13CET Mertens, Sven (uidv7805)
fix for SQL_TABLENAMES overwrite
--- Added comments ---  uidv7805 [Jan 13, 2015 9:38:13 AM CET]
Change Package : 294959:1 http://mks-psad:7002/im/viewissue?selection=294959
Revision 1.76 2015/01/12 12:52:18CET Mertens, Sven (uidv7805)
fix for accident DB closure
--- Added comments ---  uidv7805 [Jan 12, 2015 12:52:19 PM CET]
Change Package : 288758:1 http://mks-psad:7002/im/viewissue?selection=288758
Revision 1.75 2014/12/19 11:21:58CET Mertens, Sven (uidv7805)
as agreed, we should use disable each method name
--- Added comments ---  uidv7805 [Dec 19, 2014 11:21:58 AM CET]
Change Package : 288758:1 http://mks-psad:7002/im/viewissue?selection=288758
Revision 1.74 2014/12/17 17:11:45CET Ellero, Stefano (uidw8660)
Removed all db.obj based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Dec 17, 2014 5:11:45 PM CET]
Change Package : 281278:1 http://mks-psad:7002/im/viewissue?selection=281278
Revision 1.73 2014/12/09 10:43:58CET Mertens, Sven (uidv7805)
additional type fixes
--- Added comments ---  uidv7805 [Dec 9, 2014 10:43:59 AM CET]
Change Package : 281273:1 http://mks-psad:7002/im/viewissue?selection=281273
Revision 1.72 2014/12/09 09:20:12CET Mertens, Sven (uidv7805)
another update trial
--- Added comments ---  uidv7805 [Dec 9, 2014 9:20:13 AM CET]
Change Package : 281273:1 http://mks-psad:7002/im/viewissue?selection=281273
Revision 1.71 2014/12/08 09:55:52CET Mertens, Sven (uidv7805)
get_next_id update
--- Added comments ---  uidv7805 [Dec 8, 2014 9:55:52 AM CET]
Change Package : 281273:1 http://mks-psad:7002/im/viewissue?selection=281273
Revision 1.70 2014/12/02 15:27:46CET Hospes, Gerd-Joachim (uidv8815)
adapt to new deprication decorator
--- Added comments ---  uidv8815 [Dec 2, 2014 3:27:47 PM CET]
Change Package : 286836:1 http://mks-psad:7002/im/viewissue?selection=286836
Revision 1.69 2014/11/17 08:10:39CET Mertens, Sven (uidv7805)
name updates
--- Added comments ---  uidv7805 [Nov 17, 2014 8:10:39 AM CET]
Change Package : 281272:1 http://mks-psad:7002/im/viewissue?selection=281272
Revision 1.68 2014/11/11 16:20:52CET Mertens, Sven (uidv7805)
;-( forgot some returns
--- Added comments ---  uidv7805 [Nov 11, 2014 4:20:53 PM CET]
Change Package : 279419:1 http://mks-psad:7002/im/viewissue?selection=279419
Revision 1.67 2014/11/11 15:58:30CET Mertens, Sven (uidv7805)
wrong deprecation
--- Added comments ---  uidv7805 [Nov 11, 2014 3:58:31 PM CET]
Change Package : 279419:1 http://mks-psad:7002/im/viewissue?selection=279419
Revision 1.66 2014/11/11 11:22:48CET Mertens, Sven (uidv7805)
update to deprecation methods / properties
--- Added comments ---  uidv7805 [Nov 11, 2014 11:22:49 AM CET]
Change Package : 279419:1 http://mks-psad:7002/im/viewissue?selection=279419
Revision 1.65 2014/11/10 14:45:13CET Mertens, Sven (uidv7805)
being able to leave out old GetQualifiedTableName
--- Added comments ---  uidv7805 [Nov 10, 2014 2:45:14 PM CET]
Change Package : 279419:1 http://mks-psad:7002/im/viewissue?selection=279419
Revision 1.64 2014/10/31 10:53:21CET Hospes, Gerd-Joachim (uidv8815)
cleanup
--- Added comments ---  uidv8815 [Oct 31, 2014 10:53:22 AM CET]
Change Package : 275077:1 http://mks-psad:7002/im/viewissue?selection=275077
Revision 1.63 2014/10/09 14:23:43CEST Mertens, Sven (uidv7805)
reverting to try/except
--- Added comments ---  uidv7805 [Oct 9, 2014 2:23:43 PM CEST]
Change Package : 270435:1 http://mks-psad:7002/im/viewissue?selection=270435
Revision 1.62 2014/10/09 11:28:37CEST Mertens, Sven (uidv7805)
lint adaption
--- Added comments ---  uidv7805 [Oct 9, 2014 11:28:37 AM CEST]
Change Package : 270336:1 http://mks-psad:7002/im/viewissue?selection=270336
Revision 1.61 2014/10/09 10:31:52CEST Mertens, Sven (uidv7805)
fix table name retrieval for oracle
--- Added comments ---  uidv7805 [Oct 9, 2014 10:31:53 AM CEST]
Change Package : 270336:1 http://mks-psad:7002/im/viewissue?selection=270336
Revision 1.60 2014/10/08 12:38:42CEST Ellero, Stefano (uidw8660)
Improved epydoc documentation for the for stk.db.root subpackage.
--- Added comments ---  uidw8660 [Oct 8, 2014 12:38:43 PM CEST]
Change Package : 245351:1 http://mks-psad:7002/im/viewissue?selection=245351
Revision 1.59 2014/10/07 12:47:29CEST Ellero, Stefano (uidw8660)
Improve epydoc documentation for the for stk.db.root subpakage.
--- Added comments ---  uidw8660 [Oct 7, 2014 12:47:30 PM CEST]
Change Package : 245351:1 http://mks-psad:7002/im/viewissue?selection=245351
Revision 1.58 2014/10/02 12:35:14CEST Ahmed, Zaheer (uidu7634)
bug fix for oracle db to get current_userid from gbl_user
--- Added comments ---  uidu7634 [Oct 2, 2014 12:35:15 PM CEST]
Change Package : 241672:1 http://mks-psad:7002/im/viewissue?selection=241672
Revision 1.57 2014/09/02 15:12:21CEST Ahmed, Zaheer (uidu7634)
new attribute self.current_gbluserid is added into BaseDb class
--- Added comments ---  uidu7634 [Sep 2, 2014 3:12:22 PM CEST]
Change Package : 260448:1 http://mks-psad:7002/im/viewissue?selection=260448
Revision 1.56 2014/07/29 13:55:15CEST Ahmed, Zaheer (uidu7634)
Added GetSubSchemeVersions()
--- Added comments ---  uidu7634 [Jul 29, 2014 1:55:16 PM CEST]
Change Package : 250873:1 http://mks-psad:7002/im/viewissue?selection=250873
Revision 1.55 2014/07/25 15:55:40CEST Mertens, Sven (uidv7805)
adding server flag for SqlCe DB's
--- Added comments ---  uidv7805 [Jul 25, 2014 3:55:41 PM CEST]
Change Package : 251810:1 http://mks-psad:7002/im/viewissue?selection=251810
Revision 1.54 2014/07/14 20:01:46CEST Ahmed, Zaheer (uidu7634)
Db function Substr added added
--- Added comments ---  uidu7634 [Jul 14, 2014 8:01:46 PM CEST]
Change Package : 247294:1 http://mks-psad:7002/im/viewissue?selection=247294
Revision 1.53 2014/07/03 15:52:28CEST Mertens, Sven (uidv7805)
ConvertTimestampToDate: fix for date/time literal
--- Added comments ---  uidv7805 [Jul 3, 2014 3:52:29 PM CEST]
Change Package : 246062:1 http://mks-psad:7002/im/viewissue?selection=246062
Revision 1.52 2014/06/30 16:06:18CEST Ahmed, Zaheer (uidu7634)
bug fix to  correct value for self.role when connected with Oracle database with admin user
--- Added comments ---  uidu7634 [Jun 30, 2014 4:06:18 PM CEST]
Change Package : 236899:1 http://mks-psad:7002/im/viewissue?selection=236899
Revision 1.51 2014/06/24 13:15:36CEST Mertens, Sven (uidv7805)
providing foreign keys switch for future usage
--- Added comments ---  uidv7805 [Jun 24, 2014 1:15:36 PM CEST]
Change Package : 243817:1 http://mks-psad:7002/im/viewissue?selection=243817
Revision 1.50 2014/06/24 11:38:49CEST Mertens, Sven (uidv7805)
disabling foreign keys per default to keep unittests running,
use parameter foreign_keys = True to enable them on sqlite
--- Added comments ---  uidv7805 [Jun 24, 2014 11:38:49 AM CEST]
Change Package : 243817:1 http://mks-psad:7002/im/viewissue?selection=243817
Revision 1.49 2014/06/24 11:18:08CEST Mertens, Sven (uidv7805)
fix for sub scheme version
--- Added comments ---  uidv7805 [Jun 24, 2014 11:18:08 AM CEST]
Change Package : 243817:1 http://mks-psad:7002/im/viewissue?selection=243817
Revision 1.48 2014/06/24 10:32:06CEST Mertens, Sven (uidv7805)
db connection and sub schema version update
--- Added comments ---  uidv7805 [Jun 24, 2014 10:32:06 AM CEST]
Change Package : 243817:1 http://mks-psad:7002/im/viewissue?selection=243817
Revision 1.47 2014/06/04 13:12:42CEST Ahmed, Zaheer (uidu7634)
logger fixed in AddGenericPrepared()
--- Added comments ---  uidu7634 [Jun 4, 2014 1:12:42 PM CEST]
Change Package : 232650:2 http://mks-psad:7002/im/viewissue?selection=232650
Revision 1.46 2014/05/14 16:09:43CEST Mertens, Sven (uidv7805)
fix for AdasDbError argument
--- Added comments ---  uidv7805 [May 14, 2014 4:09:43 PM CEST]
Change Package : 236403:1 http://mks-psad:7002/im/viewissue?selection=236403
Revision 1.45 2014/05/14 14:59:05CEST Mertens, Sven (uidv7805)
- update execute method for "with" support (recursive queries),
- moving table name, etc methods inside BaseDB as being equal.
--- Added comments ---  uidv7805 [May 14, 2014 2:59:06 PM CEST]
Change Package : 236403:1 http://mks-psad:7002/im/viewissue?selection=236403
Revision 1.44 2014/03/24 10:09:19CET Ahmed, Zaheer (uidu7634)
improved data type check in AddGenericPreparedData()
--- Added comments ---  uidu7634 [Mar 24, 2014 10:09:20 AM CET]
Change Package : 224327:1 http://mks-psad:7002/im/viewissue?selection=224327
Revision 1.43 2014/03/24 08:16:18CET Ahmed, Zaheer (uidu7634)
Introduced AddGenericPreparedData() for BaseDB class
Revision 1.42 2013/07/29 09:15:05CEST Raedler, Guenther (uidt9430)
- revert unexpected changes
- removed __del__ method an BaseDB class as not needed. The connections are closed by the connector class.
Terminate() method creates unexpected errors
- left pylint error fixes and regex definition as discussed
--- Added comments ---  uidt9430 [Jul 29, 2013 9:15:05 AM CEST]
Change Package : 191735:1 http://mks-psad:7002/im/viewissue?selection=191735
Revision 1.41 2013/07/17 09:33:50CEST Mertens, Sven (uidv7805)
regex fix: adding apostroph exclude
--- Added comments ---  uidv7805 [Jul 17, 2013 9:33:50 AM CEST]
Change Package : 185933:3 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.40 2013/07/04 16:12:04CEST Mertens, Sven (uidv7805)
adding one more method from DB specific classes to db_common
--- Added comments ---  uidv7805 [Jul 4, 2013 4:12:05 PM CEST]
Change Package : 185933:3 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.39 2013/07/04 14:58:14CEST Mertens, Sven (uidv7805)
added functionality from Oracle-, SQLCE- and SQLite3BaseDB to BaseDB
to remove these class dependencies and providing DB specific things in BaseDB instead.
--- Added comments ---  uidv7805 [Jul 4, 2013 2:58:14 PM CEST]
Change Package : 185933:3 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.38 2013/06/25 13:24:40CEST Mertens, Sven (uidv7805)
adjustment for regex table expression needed
--- Added comments ---  uidv7805 [Jun 25, 2013 1:24:41 PM CEST]
Change Package : 185933:1 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.37 2013/06/24 17:13:20CEST Skerl, Anne (uid19464)
*bugfix identifying Windows version
--- Added comments ---  uid19464 [Jun 24, 2013 5:13:20 PM CEST]
Change Package : 178419:6 http://mks-psad:7002/im/viewissue?selection=178419
Revision 1.36 2013/06/24 16:56:57CEST Skerl, Anne (uid19464)
*add driver for SQL Sercer Compact Edition 3.5 for sdf-files at Windows7 (used for CGEB-Labels)
*switch default db drivers depending on Windows version
--- Added comments ---  uid19464 [Jun 24, 2013 4:56:57 PM CEST]
Change Package : 178419:6 http://mks-psad:7002/im/viewissue?selection=178419
Revision 1.35 2013/06/21 13:56:00CEST Mertens, Sven (uidv7805)
for interim purposes sqlite should be able to connect to :memory: as well (missing)
--- Added comments ---  uidv7805 [Jun 21, 2013 1:56:00 PM CEST]
Change Package : 185933:1 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.34 2013/06/14 13:00:10CEST Mertens, Sven (uidv7805)
adding __del__ method to ensure DB is closed
--- Added comments ---  uidv7805 [Jun 14, 2013 1:00:10 PM CEST]
Change Package : 185933:1 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.33 2013/06/13 15:24:22CEST Mertens, Sven (uidv7805)
Adding possibility to take over connection string.
As new ECU-SIL observer should be on multi processing functionality,
removes the need for involved components and DB classes can be used more directly.
Backwardcompatibility is preserved.
--- Added comments ---  uidv7805 [Jun 13, 2013 3:24:22 PM CEST]
Change Package : 185933:3 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.32 2013/06/06 11:22:22CEST Bratoi, Bogdan-Horia (uidu8192)
- corrected the date_time_format in the init of OracleBaseDB
--- Added comments ---  uidu8192 [Jun 6, 2013 11:22:22 AM CEST]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.31 2013/05/29 15:20:31CEST Raedler, Guenther (uidt9430)
- provide cursor for database procedure calls (required in the LD validation)
--- Added comments ---  uidt9430 [May 29, 2013 3:20:31 PM CEST]
Change Package : 184344:1 http://mks-psad:7002/im/viewissue?selection=184344
Revision 1.30 2013/05/29 14:45:48CEST Mertens, Sven (uidv7805)
making cxOracle connection optional via connectionString's DBQ option which is oracle specific
--- Added comments ---  uidv7805 [May 29, 2013 2:45:48 PM CEST]
Change Package : 179495:8 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.29 2013/05/29 09:10:04CEST Mertens, Sven (uidv7805)
adding local pylint ignores
--- Added comments ---  uidv7805 [May 29, 2013 9:10:05 AM CEST]
Change Package : 179495:7 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.28 2013/05/24 10:51:24CEST Mertens, Sven (uidv7805)
bugfixing connection problem
--- Added comments ---  uidv7805 [May 24, 2013 10:51:24 AM CEST]
Change Package : 179495:7 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.27 2013/05/23 09:14:23CEST Mertens, Sven (uidv7805)
fixing wrong intention
--- Added comments ---  uidv7805 [May 23, 2013 9:14:23 AM CEST]
Change Package : 179495:8 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.26 2013/05/23 06:41:13CEST Mertens, Sven (uidv7805)
new function dbConnect to be able to ease connection setup
--- Added comments ---  uidv7805 [May 23, 2013 6:41:13 AM CEST]
Change Package : 179495:8 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.25 2013/04/26 13:46:57CEST Mertens, Sven (uidv7805)
fixed a raise as tested from unittest
--- Added comments ---  uidv7805 [Apr 26, 2013 1:46:58 PM CEST]
Change Package : 180829:2 http://mks-psad:7002/im/viewissue?selection=180829
Revision 1.24 2013/04/26 10:46:08CEST Mertens, Sven (uidv7805)
moving strIdent
--- Added comments ---  uidv7805 [Apr 26, 2013 10:46:08 AM CEST]
Change Package : 179495:4 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.23 2013/04/25 15:12:39CEST Mertens, Sven (uidv7805)
added column description header to execute
--- Added comments ---  uidv7805 [Apr 25, 2013 3:12:39 PM CEST]
Change Package : 179495:2 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.22 2013/04/19 13:36:30CEST Hecker, Robert (heckerr)
functionality reverted to revision 1.19.
--- Added comments ---  heckerr [Apr 19, 2013 1:36:31 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.21 2013/04/12 15:01:15CEST Mertens, Sven (uidv7805)
minor DB connection update due to VALF connection change
--- Added comments ---  uidv7805 [Apr 12, 2013 3:01:16 PM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.20 2013/04/11 14:32:53CEST Ahmed-EXT, Zaheer (uidu7634)
Fixed Schema prefix bug for SQLite DB support
--- Added comments ---  uidu7634 [Apr 11, 2013 2:32:53 PM CEST]
Change Package : 178419:2 http://mks-psad:7002/im/viewissue?selection=178419
Revision 1.19 2013/04/05 11:17:42CEST Hospes, Gerd-Joachim (uidv8815)
fix documentation
--- Added comments ---  uidv8815 [Apr 5, 2013 11:17:42 AM CEST]
Change Package : 169590:2 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.18 2013/04/03 08:02:13CEST Mertens, Sven (uidv7805)
pylint: minor error, warnings fix
--- Added comments ---  uidv7805 [Apr 3, 2013 8:02:13 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.17 2013/03/28 14:43:10CET Mertens, Sven (uidv7805)
pylint: resolving some R0904, R0913, R0914, W0107
--- Added comments ---  uidv7805 [Mar 28, 2013 2:43:10 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.16 2013/03/28 11:10:54CET Mertens, Sven (uidv7805)
pylint: last unused import removed
--- Added comments ---  uidv7805 [Mar 28, 2013 11:10:54 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.15 2013/03/28 09:33:21CET Mertens, Sven (uidv7805)
pylint: removing unused imports
--- Added comments ---  uidv7805 [Mar 28, 2013 9:33:21 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.14 2013/03/26 16:19:38CET Mertens, Sven (uidv7805)
pylint: using direct imports, no stars any more
Revision 1.13 2013/03/26 13:00:22CET Mertens, Sven (uidv7805)
reverting error for keyword argument spaces
--- Added comments ---  uidv7805 [Mar 26, 2013 1:00:22 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.12 2013/03/26 11:53:20CET Mertens, Sven (uidv7805)
reworking imports on cat, cl and db_common to start testing with.
--- Added comments ---  uidv7805 [Mar 26, 2013 11:53:21 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.11 2013/03/22 15:07:19CET Mertens, Sven (uidv7805)
additional support for call proc (cx_Oracle) added
--- Added comments ---  uidv7805 [Mar 22, 2013 3:07:19 PM CET]
Change Package : 176171:9 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.10 2013/03/15 10:01:19CET Mertens, Sven (uidv7805)
added addConstraint method to add new constrain set with details
--- Added comments ---  uidv7805 [Mar 15, 2013 10:01:19 AM CET]
Change Package : 176171:8 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.9 2013/03/14 11:35:00CET Mertens, Sven (uidv7805)
adding execute for being able to submit SQL queries
--- Added comments ---  uidv7805 [Mar 14, 2013 11:35:00 AM CET]
Change Package : 176171:8 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.8 2013/03/07 07:17:00CET Raedler, Guenther (uidt9430)
- added function to load the subscheme version
- added function to set the current user role
--- Added comments ---  uidt9430 [Mar 7, 2013 7:17:00 AM CET]
Change Package : 100768:2 http://mks-psad:7002/im/viewissue?selection=100768
Revision 1.7 2013/03/04 07:47:33CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 4, 2013 7:47:34 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.6 2013/02/27 13:59:46CET Hecker, Robert (heckerr)
Some changes regarding Pep8
--- Added comments ---  heckerr [Feb 27, 2013 1:59:46 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.5 2013/02/26 20:11:54CET Raedler, Guenther (uidt9430)
- Updates after Pep8 Styleguides
--- Added comments ---  uidt9430 [Feb 26, 2013 8:11:54 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.4 2013/02/26 16:21:43CET Raedler, Guenther (uidt9430)
- added additional exception message for AddGenericData
--- Added comments ---  uidt9430 [Feb 26, 2013 4:21:43 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.3 2013/02/19 14:07:56CET Raedler, Guenther (uidt9430)
- define common db functions
--- Added comments ---  uidt9430 [Feb 19, 2013 2:07:56 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/02/12 08:19:50CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm
    /STK_ScriptingToolKit/04_Engineering/stk/db/project.pj
------------------------------------------------------------------------------
-- From CGEB Archive
------------------------------------------------------------------------------
Revision 1.16 2012/05/02 07:55:37CEST Raedler-EXT, Guenther (uidt9430)
- changed driver default name
--- Added comments ---  uidt9430 [May 2, 2012 7:55:39 AM CEST]
Change Package : 111588:1 http://mks-psad:7002/im/viewissue?selection=111588
Revision 1.15 2012/04/25 10:13:36CEST Raedler-EXT, Guenther (uidt9430)
- set driver for Win7 as default (SimuClients)
- add XP driver definition (current workstations)
--- Added comments ---  uidt9430 [Apr 25, 2012 10:13:37 AM CEST]
Change Package : 111588:1 http://mks-psad:7002/im/viewissue?selection=111588
Revision 1.14 2012/04/17 12:44:26CEST Raedler-EXT, Guenther (uidt9430)
- upgrade for oracle 11g
* define new connection parameters
* support driver instead of dsn
--- Added comments ---  uidt9430 [Apr 17, 2012 12:44:30 PM CEST]
Change Package : 111588:1 http://mks-psad:7002/im/viewissue?selection=111588
Revision 1.13 2011/10/07 14:24:30CEST Castell, Christoph (uidt6394)
Fixed bug bz commenting out rowcount in DeleteGenericData function.
--- Added comments ---  uidt6394 [Oct 7, 2011 2:24:31 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.12 2011/07/19 09:37:35CEST Skerl Anne (uid19464) (uid19464)
*uncomment rowcount in DeleteGenericData
--- Added comments ---  uid19464 [Jul 19, 2011 9:37:36 AM CEST]
Change Package : 38933:9 http://mks-psad:7002/im/viewissue?selection=38933
Revision 1.11 2011/07/04 13:14:52CEST Raedler Guenther (uidt9430) (uidt9430)
-- added new method to get table data more efficiently
--- Added comments ---  uidt9430 [Jul 4, 2011 1:14:53 PM CEST]
Change Package : 67780:2 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.10 2011/01/21 14:12:46CET Skerl Anne (uid19464) (uid19464)
*add comment: GetSQLite3ConnectString does not take ";" at the end
--- Added comments ---  uid19464 [Jan 21, 2011 2:12:46 PM CET]
Change Package : 38933:6 http://mks-psad:7002/im/viewissue?selection=38933
Revision 1.9 2010/11/18 17:32:07CET Dominik Froehlich (froehlichd1)
* change: added special date time format string to Oracle DB catalog class
--- Added comments ---  froehlichd1 [Nov 18, 2010 5:32:08 PM CET]
Change Package : 45990:34 http://mks-psad:7002/im/viewissue?selection=45990
Revision 1.8 2010/11/18 17:11:15CET Dominik Froehlich (froehlichd1)
* fix: corrected GetFullTablePrefix
* change: set default schema prefix to None
--- Added comments ---  froehlichd1 [Nov 18, 2010 5:11:15 PM CET]
Change Package : 45990:33 http://mks-psad:7002/im/viewissue?selection=45990
Revision 1.7 2010/11/18 14:47:29CET Dominik Froehlich (froehlichd1)
* fix: fixed computation of table/schema prefixes
* use one prefix that includes the separators
Revision 1.6 2010/11/10 10:56:36CET Dominik Froehlich (froehlichd1)
* change: removed default table prefixes
* change: full support of 'no table prefix'
Revision 1.5 2010/10/27 10:32:00CEST Skerl Anne (uid19464) (uid19464)
*add close database connection in terminate call
--- Added comments ---  uid19464 [Oct 27, 2010 10:32:00 AM CEST]
Change Package : 38933:4 http://mks-psad:7002/im/viewissue?selection=38933
Revision 1.4 2010/07/14 11:56:56CEST Dominik Froehlich (froehlichd1)
* update
--- Added comments ---  froehlichd1 [Jul 14, 2010 11:56:56 AM CEST]
Change Package : 45990:20 http://fras236:8002/im/viewissue?selection=45990
Revision 1.3 2010/06/25 14:22:12CEST Dominik Froehlich (dfroehlich)
* update
--- Added comments ---  dfroehlich [2010/06/25 12:22:12Z]
Change Package : 45990:3 http://LISS014:6001/im/viewissue?selection=45990
Revision 1.2 2010/06/18 16:01:23CEST Dominik Froehlich (dfroehlich)
* update
--- Added comments ---  dfroehlich [2010/06/18 14:01:23Z]
Change Package : 45990:2 http://LISS014:6001/im/viewissue?selection=45990
Revision 1.1 2009/10/08 12:27:41CEST rthiel
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/Base_CGEB
/06_Algorithm/04_Engineering/02_Development_Tools/scripts/project.pj
Revision 1.6 2009/09/21 14:28:51CEST Dominik Froehlich (dfroehlich)
Improved import for oracle db:

* support of data-time strings
* support of transactions
* extended info during import
--- Added comments ---  dfroehlich [2009/09/21 12:28:51Z]
Change Package : 30406:7 http://LISS014:6001/im/viewissue?selection=30406
Revision 1.5 2009/08/10 10:41:41CEST Dominik Froehlich (dfroehlich)
* various bug-fixes
--- Added comments ---  dfroehlich [2009/08/10 08:41:41Z]
Change Package : 27675:10 http://LISS014:6001/im/viewissue?selection=27675
Revision 1.4 2009/06/17 19:02:07CEST dfroehlich
* change: intermediate version of new simulation report
--- Added comments ---  dfroehlich [2009/06/17 17:02:07Z]
Change Package : 27675:1 http://LISS014:6001/im/viewissue?selection=27675
Revision 1.3 2009/06/16 11:13:34CEST dfroehlich
* fix: various SQL changes
--- Added comments ---  dfroehlich [2009/06/16 09:13:34Z]
Change Package : 21107:4 http://LISS014:6001/im/viewissue?selection=21107
Revision 1.2 2009/05/28 15:01:48CEST dfroehlich
fix: fixed event import and table init
--- Added comments ---  dfroehlich [2009/05/28 13:01:48Z]
Change Package : 21107:3 http://LISS014:6001/im/viewissue?selection=21107
Revision 1.1 2009/05/14 18:20:22CEST dfroehlich
Initial revision
Member added to project /nfs/projekte1/customer/Base_ARS3xx_ISF1xx/
    3_development/7_tools/evaluation_scripts/kcm/project.pj
"""
