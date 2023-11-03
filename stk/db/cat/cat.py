"""
stk/db/cat/cat.py
-----------------

Classes for Database access of Catalog Tables.

Sub-Scheme CAT

**User-API**

    - `BaseRecCatalogDB`
        Providing methods to read recording (measurements) details
        and to create, modify and delete collections and bpl files

The other classes in this module are handling the different DB types and are derived from BaseRecCatalogDB.

**usage in Valf suites**

For validation suites based on `Valf` class there is the operator `DbLinker` setting up all needed connections.

**using several connections in parallel**

If several sub-schemes have to be used in parallel the first connection should be reused.
Please check class `BaseRecCatalogDB` for more detail.

**Do not waste the limited number of connections to Oracle DB**
by setting up a new connection for each sub-scheme,
always use the existing one as described in `BaseRecCatalogDB`.

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.80 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/11/14 16:23:25CET $
"""
# pylint: disable=W0702
# - import Python modules ---------------------------------------------------------------------------------------------
from datetime import datetime
from logging import warn, info
from os import path, environ
from time import time
from copy import deepcopy
from re import search, sub as resub

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.db.db_common import BaseDB, ERROR_TOLERANCE_LOW, AdasDBError, DB_FUNC_NAME_LOWER, PluginBaseDB
from stk.db.db_sql import GenericSQLSelect, SQLBinaryExpr, SQLFuncExpr, SQLJoinExpr, SQLLiteral, SQLIntegral, \
    SQLColumnExpr, SQLTableExpr, SQLNull, SQLUnaryExpr, SQLConcatExpr, SQLTernaryExpr, OP_NOP, OP_RETURNING, OP_AND, \
    OP_IS, OP_AS, OP_INNER_JOIN, OP_IN, OP_SUB, OP_ADD, OP_EQ, OP_LIKE, OP_MUL, OP_UNION_ALL, OP_USING, \
    GEN_RECUR_NAME, EXPR_WITH, EXPR_COUNT, OP_DIV, OP_GEQ, OP_LEQ, OP_OR, SQLListExpr
from stk.valf.signal_defs import DBCAT

from stk.db.gbl.gbl import TABLE_NAME_PROJECT, COL_NAME_PROJECT_PID, COL_NAME_PROJECT_NAME, \
    TABLE_NAME_LOCATION, COL_NAME_LOCATION_LOCATION, COL_NAME_LOCATION_NAME
from stk.mts.bpl import Bpl, BplListEntry
from stk.util.helper import deprecated, arg_trans

# - defines -----------------------------------------------------------------------------------------------------------
# Table base names:
TABLE_NAME_KWMAP = "CAT_KeywordMap"
TABLE_NAME_KW = "CAT_Keywords"
TABLE_NAME_COLLMAP = "CAT_CollectionMap"
TABLE_NAME_COLL = "CAT_Collections"
TABLE_NAME_FILES = "CAT_Files"
TABLE_NAME_PARTCFGS = "CAT_PartCfgs"
TABLE_NAME_PARTTYPES = "CAT_PartTypes"
TABLE_NAME_VEHICLECFGS = "CAT_VehicleCfgs"
TABLE_NAME_VEHICLECFGSTATES = "CAT_VehicleCfgStates"
TABLE_NAME_VEHICLES = "CAT_Vehicles"
TABLE_NAME_FILESTATES = "CAT_FileStates"
TABLE_NAME_DRIVERS = "CAT_Drivers"
TABLE_NAME_DATAINTTESTS = "CAT_DataIntTests"
TABLE_NAME_CAT_COLLECTION_LOG = "CAT_COLLECTION_LOG"
TABLE_NAME_CAT_COLLECTION_LOGDETAILS = "CAT_COLLECTION_LOGDETAILS"
TABLE_NAME_CAT_SHAREDCOLLECTIONMAP = "CAT_SHAREDCOLLECTIONMAP"

COL_NAME_DRIVERS_DRIVERID = "DRIVERID"
COL_NAME_DRIVERS_NAME = "NAME"

COL_NAME_FILESTATES_FILESTATEID = "FILESTATEID"
COL_NAME_FILESTATES_NAME = "NAME"

COL_NAME_VEHICLES_VEHICLEID = "VEHICLEID"
COL_NAME_VEHICLES_NAME = "NAME"
COL_NAME_VEHICLES_MODEL = "MODEL"
COL_NAME_VEHICLES_LICNUMBER = "LICNUMBER"
COL_NAME_VEHICLES_VEHCOMMENT = "VEHCOMMENT"

COL_NAME_VEHICLECFGSTATES_VEHICLECFGSTATEID = "VEHCFGSTATEID"
COL_NAME_VEHICLECFGSTATES_NAME = "NAME"

COL_NAME_VEHICLECFGS_VEHCFGID = "VEHICLECFGID"
COL_NAME_VEHICLECFGS_VEHICLEID = "VEHICLEID"
COL_NAME_VEHICLECFGS_VEHICLECFGSTATEID = "VEHCFGSTATEID"
COL_NAME_VEHICLECFGS_NAME = "NAME"
COL_NAME_VEHICLECFGS_SETUPDATE = "SETUPDATE"
COL_NAME_VEHICLECFGS_SETUPBY = "SETUPBY"
COL_NAME_VEHICLECFGS_CFGCOMMENT = "CFGCOMMENT"

COL_NAME_PARTCFGS_PARTCFGID = "PARTCFGID"
COL_NAME_PARTCFGS_VEHCFGID = "VEHICLECFGID"
COL_NAME_PARTCFGS_NAME = "NAME"
COL_NAME_PARTCFGS_HWVERSION = "HWVERSION"
COL_NAME_PARTCFGS_SWVERSION = "SWVERSION"
COL_NAME_PARTCFGS_PARTCOMMENT = "PARTCOMMENT"
COL_NAME_PARTCFGS_PARTTYPEID = "PARTTYPEID"

COL_NAME_PARTTYPES_PARTTYPEID = "PARTTYPEID"
COL_NAME_PARTTYPES_NAME = "NAME"

COL_NAME_FILES_MEASID = "MEASID"
COL_NAME_FILES_RECFILEID = "RECFILEID"
COL_NAME_FILES_BEGINTIMESTAMP = "BEGINABSTS"
COL_NAME_FILES_ENDTIMESTAMP = "ENDABSTS"
COL_NAME_FILES_FILEPATH = "FILEPATH"
COL_NAME_FILES_LOCATION = "LOCATION"
COL_NAME_FILES_RECTIME = "RECTIME"
COL_NAME_FILES_IMPORTDATE = "IMPORTDATE"
COL_NAME_FILES_IMPORTBY = "IMPORTBY"
COL_NAME_FILES_FILESTATEID = "FILESTATEID"
COL_NAME_FILES_VEHICLECFGID = "VEHICLECFGID"
COL_NAME_FILES_DRIVERID = "DRIVERID"
COL_NAME_FILES_CONTENTHASH = "CONTENTHASH"
COL_NAME_FILES_RECDRIVENDIST = "RECDRIVENDIST"
COL_NAME_FILES_RECODOSTARTDIST = "RECODOSTARTDIST"
COL_NAME_FILES_DATAINTTESTRESULT = "DATAINTTESTRESULT"
COL_NAME_FILES_DATAINTTESTSTATUS = "DATAINTTESTSTATUS"
COL_NAME_FILES_FILESIZE = "FILESIZE"
COL_NAME_FILES_ARCHIVED = "ARCHIVED"
COL_NAME_FILES_DELETED = "DELETED"
COL_NAME_FILES_GPSDRIVENDIST = "GPSDRIVENDIST"
COL_NAME_FILES_STATUS = "STATUS"
COL_NAME_FILES_PID = "PID"

COL_NAME_KW_KWID = "KWID"
COL_NAME_KW_PARENTID = "PARENTID"
COL_NAME_KW_NAME = "NAME"
COL_NAME_KW_KWCOMMENT = "KWCOMMENT"

COL_NAME_KWMAP_KWMAPID = "KWMAPID"
COL_NAME_KWMAP_KWID = "KWID"
COL_NAME_KWMAP_MEASID = "MEASID"
COL_NAME_KWMAP_BEGINTIMESTAMP = "BEGINRELTS"
COL_NAME_KWMAP_ENDTIMESTAMP = "ENDRELTS"
COL_NAME_KWMAP_ASGNBY = "ASGNBY"
COL_NAME_KWMAP_ASGNDATE = "ASGNDATE"

COL_NAME_COLL_COLLID = "COLLID"
COL_NAME_COLL_PARENTID = "PARENTID"
COL_NAME_COLL_NAME = "NAME"
COL_NAME_COLL_COLLCOMMENT = "COLLCOMMENT"
COL_NAME_COLL_PRID = "PRID"
COL_NAME_COLL_IS_ACTIVE = "IS_ACTIVE"
COL_NAME_COLL_USERID = "USERID"
COL_NAME_COLL_CREATED = "CREATED"
COL_NAME_COLL_CP_LABEL = "CP_LABEL"

COL_NAME_COLLMAP_COLLMAPID = "COLLMAPID"
COL_NAME_COLLMAP_COLLID = "COLLID"
COL_NAME_COLLMAP_MEASID = "MEASID"
COL_NAME_COLLMAP_BEGINTIMESTAMP = "BEGINRELTS"
COL_NAME_COLLMAP_ENDTIMESTAMP = "ENDRELTS"
COL_NAME_COLLMAP_ASGNBY = "ASGNBY"
COL_NAME_COLLMAP_ASGNDATE = "ASGNDATE"
COL_NAME_COLLMAP_USERID = "USERID"
COL_NAME_COLLMAP_ASSIGNED = "ASSIGNED"

COL_NAME_DATAINTTESTS_TESTID = "TESTID"
COL_NAME_DATAINTTESTS_NAME = "NAME"
COL_NAME_DATAINTTESTS_DITCOMMENT = "DITCOMMENT"

COL_NAME_COLLOG_LOG_ID = "LOG_ID"
COL_NAME_COLLOG_COLL_NAME = "COLL_NAME"
COL_NAME_COLLOG_ACTION = "ACTION"
COL_NAME_COLLOG_ACTION_DATE = "ACTION_DATE"
COL_NAME_COLLOG_ACTIONBY = "ACTIONBY"
COL_NAME_COLLOG_COLLID = "COLLID"
COL_NAME_COLLOG_DETAILS = "COLLID"

COL_NAME_COLLDET_DETAILID = "DETAILID"
COL_NAME_COLLDET_LOG_ID = "LOG_ID"
COL_NAME_COLLDET_MEASID = "MEASID"

COL_NANE_SHARECOLL_SAHREDMAPID = "SAHREDMAPID"
COL_NANE_SHARECOLL_PARENT_COLLID = "PARENT_COLLID"
COL_NANE_SHARECOLL_CHILD_COLLID = "CHILD_COLLID"
COL_NANE_SHARECOLL_PRID = "PRID"
PATH_SEPARATOR = "/"

DBCAT_SUB_SCHEME_TAG = "CAT"
CAT_PRIORIRTY_VERSION = 7
CAT_ACTIVE_VERSION = 8
CAT_SHARECOLL_VERSION = 10
CAT_CHECKPOINT_VERSION = 11
CAT_NOVEHICLEINFO_VERSION = 12
CAT_LOCATIONUSAGE_VERSION = 13

IDENT_STRING = DBCAT

FILESERVER_HOST_MAPS = {r"lifs010": "lifs010.cw01.contiwan.com",
                        r"lufs003x": r"lufs003x.li.de.conti.de"}
# virtual columns
SHARED_FLAG = "SHARED_FLAG"
# Flag definition from shared collections
# No shared collection
N0T_SHARED_COLL = 0
# The collection is shared
SHARED_COLL = 1


# - classes -----------------------------------------------------------------------------------------------------------
# Constraint DB Libary Base Implementation
class BaseRecCatalogDB(BaseDB):  # pylint: disable=R0904
    """**Base implementation of the Rec File Database** storing recordings and collections

    For the first connection to the DB for cat tables just create a new instance of this class like

    .. python::

        from stk.db.cat.cat import BaseRecCatalogDB

        dbcat = BaseRecCatalogDB("MFC4XX")   # or use "ARS4XX", "VGA" or path/name of sqlite file

    If already some connection to another table of the DB is created use that one to speed up your code:

    .. python::

        dbcat = BaseRecCatalogDB(dbxxx.db_connection)

    The connection is closed when the first instance using it is deleted.

    **error_tolerance**

    The setting of an error tolerance level allows to define if an error during later processing is

    - just listed to the log file (error_tolerance = 3, HIGH) if possible,
      e.g. if it can return the existing id without changes in case of adding an already existing entry
    - raising an AdasDBError immediately (error_tolerance < 1, LOW)

    More optional keywords are described at `BaseDB` class initialization.

    """
    # ====================================================================
    # Constraint DB Library Interface for public use
    # ====================================================================

    # ====================================================================
    # Handling of database
    # ====================================================================

    def __init__(self, *args, **kw):
        """
        Constructor to initialize BaseRecCatalogDB to represent CAT subschema

        :keyword db_connection: The database connection to be used
        :type db_connection: cx_oracle.Connection, pydodbc.Connection, sqlite3.Connection, sqlce.Connection
        :keyword table_prefix: The table name prefix which is usually master schema name
        :type table_prefix: str
        :keyword sql_factory: SQL Query building factory
        :type sql_factory: GenericSQLStatementFactory
        :keyword error_tolerance: Error tolerance level based on which some error are acceptable
        :type error_tolerance: int
        """
        kw['strIdent'] = DBCAT
        BaseDB.__init__(self, *args, **kw)
        #  cache by project name as key and project Id as value
        self._gbl_projectid_cache = {}
        self._gbl_location_cache = {}
        # fill gbl locations if available
        try:
            self._gbl_location_cache = {i[2]: (i[0], i[1]) for i in
                                        self.execute("SELECT LOCATION, NAME, SERVERSHARE FROM GBL_LOCATION")}
        except Exception as ex:
            # if we can't get the dict from db it will stay empty to be backward compatible, check before usage
            pass
        self._server_mapping = {search(r'\\+(\w*)\.', s).group(1):
                                    search(r'\\+(.*)\\', s).group(1) for s in self._gbl_location_cache}
        return

    # ====================================================================
    # Handling of file data
    # ====================================================================

    def get_measurement(self, measid=None, file_name=None, file_path=None, select_list=["*"], location=None):
        """
        Get measurement record based on criteria on optional argument.

        User can select how to define the measurement files using either

            - db internal id (unique in db)
            - file name or
            - complete path and file name (unique in db)

        If no argument is passed all the measurement file  from table will be returned!

        The returned list contains a dict for each matching measurement file with keys as defined in select_list.
        The list can have one or more of following key names:

            - MEASID
            - RECFILEID
            - BEGINABSTS
            - ENDABSTS
            - FILEPATH
            - LOCATION
            - RECTIME
            - IMPORTDATE
            - IMPORTBY
            - FILESTATEID
            - VEHICLECFGID
            - DRIVERID
            - DATAINTTESTRESULT
            - DATAINTTESTSTATUS
            - CONTENTHASH
            - RECDRIVENDIST
            - RECODOSTARTDIST
            - FILESIZE
            - ARCHIVED
            - DELETED
            - GPSDRIVENDIST
            - REGION
            - STATUS
            - PID

        If no selection_list is passed dictionaries with all keys are returned.

        :param measid: opt. the db internal id of the measurement file
        :type measid: int
        :param file_name: opt. name of measurement file in db without path, can return several entries
        :type  file_name: str
        :param file_path: opt. full path for measurement file, will be unique in db
        :type  file_path: str
        :param select_list: opt. list of column names to return  to reduce
                            the transferred size if not all values are needed, default: ["*"] for all
        :type  select_list: list of str
        :param location: short name of location of server storing the measurement file like LND, BLR or ABH
        :type  location: str
        :return: list of dict with selected db column names as keys
        """

        cond = None
        sql_param = {}
        if measid is not None:
            sql_param[str(len(sql_param) + 1)] = measid
            cond = SQLBinaryExpr(COL_NAME_FILES_MEASID,
                                 OP_EQ, ":%d" % (len(sql_param)))

        if file_path is not None:
            file_path = file_path.lower()
            if file_name is None:
                file_name = path.basename(file_path)
            # get server share names from GBL_LOCATION and update file path with it, get project id if using Oracle
            server_share, file_path, pid = self._convert_filepath(file_path)
            # speed up query by adding location filter
            cond_loc = None
            if self._sub_versions['CAT'] >= CAT_LOCATIONUSAGE_VERSION:
                if location:
                    if location in [l[1] for l in self._gbl_location_cache.values()]:
                        sql_param[str(len(sql_param) + 1)] = location
                        loc_slct = GenericSQLSelect(select_list=[COL_NAME_LOCATION_LOCATION],
                                                    table_list=[TABLE_NAME_LOCATION],
                                                    where_condition=SQLBinaryExpr(COL_NAME_LOCATION_NAME, OP_LIKE,
                                                                                  ":%d" % (len(sql_param))))
                        cond_loc = SQLBinaryExpr(COL_NAME_LOCATION_LOCATION, OP_IN, loc_slct)
                    else:
                        self._log.error("unknown site location name: {}".format(location))

                if server_share:
                    # Oracle db sets default server share: 0 - LND - \\lufs003x.li.de.conti.de\legacy
                    # so if there is some unlisted server share we take that
                    sql_param[str(len(sql_param) + 1)] = self._gbl_location_cache.get(server_share, (0, 'LND'))[0]
                    cond_loc = SQLBinaryExpr(COL_NAME_FILES_LOCATION,
                                             OP_EQ, ":%d" % (len(sql_param)))
            if pid is not None:
                sql_param[str(len(sql_param) + 1)] = file_path
                # make exact filepath lower case SQL condition
                cond_fpath = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                       COL_NAME_FILES_FILEPATH),
                                           OP_EQ, ":%d" % (len(sql_param)))
                sql_param[str(len(sql_param) + 1)] = pid
                cond_fpath = SQLBinaryExpr(cond_fpath, OP_AND, SQLBinaryExpr(COL_NAME_FILES_PID,
                                                                             OP_EQ, ":%d" % (len(sql_param))))
            else:
                if file_path[:2] != r"\\":
                    _, file_path = path.splitdrive(file_path)

                    file_path = "%%%s" % file_path
                sql_param[str(len(sql_param) + 1)] = file_path
                cond_fpath = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                       COL_NAME_FILES_FILEPATH),
                                           OP_LIKE, ":%d" % (len(sql_param)))
            if cond_loc is not None:
                cond_fpath = SQLBinaryExpr(cond_loc, OP_AND, cond_fpath)

            if cond is None:
                cond = cond_fpath
            else:
                cond = SQLBinaryExpr(cond, OP_AND, cond_fpath)
        if file_name is not None:
            file_name = file_name.lower()
            sql_param[str(len(sql_param) + 1)] = file_name
            if cond is None:
                cond = SQLBinaryExpr(COL_NAME_FILES_RECFILEID, OP_EQ, ":%d" % (len(sql_param)))
            else:
                cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COL_NAME_FILES_RECFILEID,
                                                                 OP_EQ, ":%d" % (len(sql_param))))

        return self.select_measurements(select_list, where=cond, sqlparams=sql_param)

    def select_measurements(self, select_list=["*"], where=None, group_by=None,  # pylint: disable=W0102,R0913
                            having=None, order_by=None, distinct_rows=False, sqlparams={}):
        """
        Get all measurements which fulfill some condition.

        :param select_list: List of selected table columns, see description in ``get_measurement``
        :type select_list: list
        :param where: The additional condition that must hold for the scenarios to be returned.
        :type where: SQLBinaryExpression
        :param group_by: Expression defining the columns by which selected data is grouped.
        :type group_by: list
        :param having: Expression defining the conditions that determine groups
        :type having: SQLExpression
        :param order_by: Expression that defines the order of the returned records.
        :type order_by: list
        :param distinct_rows: use distinct in query
        :type distinct_rows: bool
        :param sqlparams: more sql parameters
        :type sqlparams: dict
        :return: Returns the list of scenarios.
        :rtype: list
        """
        return self.select_generic_data(select_list, [TABLE_NAME_FILES], where, group_by, having, order_by,
                                        distinct_rows, sqlparams)

    def add_measurement(self, measurement):
        """
        Add new file to database.

        Usage on Oracle db restricted to admin group.

        :param measurement: The measurement record.
        :type measurement: dict
        :return: Returns the measurement ID. If a recording with the
                 same recfileid exists already an exception is raised.
        :rtype: int
        """
        # check for duplicate recfileid
        entries = self.get_measurement(file_path=measurement[COL_NAME_FILES_FILEPATH].lower())

        if len(entries) <= 0:
            measurement[COL_NAME_FILES_RECFILEID] = measurement[COL_NAME_FILES_RECFILEID].lower()
            if self.sub_scheme_version < CAT_ACTIVE_VERSION:
                measid = self._get_next_id(TABLE_NAME_FILES, COL_NAME_FILES_MEASID)
                measurement[COL_NAME_FILES_MEASID] = measid

                self.add_generic_data(measurement, TABLE_NAME_FILES)
            else:
                server_share, file_path, pid = self._convert_filepath(measurement[COL_NAME_FILES_FILEPATH])
                measurement[COL_NAME_FILES_FILEPATH] = file_path
                if pid is not None:
                    measurement[COL_NAME_FILES_PID] = pid
                # handle old columnS DRIVERID and IMPORTBY, removed in stk 02.03.33
                if self.sub_scheme_version < CAT_NOVEHICLEINFO_VERSION:
                    if COL_NAME_FILES_IMPORTBY not in measurement:
                        measurement[COL_NAME_FILES_IMPORTBY] = 0
                    if COL_NAME_FILES_DRIVERID not in measurement:
                        measurement[COL_NAME_FILES_DRIVERID] = 0
                elif self.sub_scheme_version >= CAT_NOVEHICLEINFO_VERSION:
                    if COL_NAME_FILES_IMPORTBY in measurement:
                        measurement.pop(COL_NAME_FILES_IMPORTBY)
                    if COL_NAME_FILES_DRIVERID in measurement:
                        measurement.pop(COL_NAME_FILES_DRIVERID)
                # handle column LOCATION and its link to GBL_LOCATION, replace regardless what's passed
                if self.sub_scheme_version >= CAT_LOCATIONUSAGE_VERSION:
                    # default as in Oracle db: lifs010\testdata = (0, 'LND')
                    measurement[COL_NAME_FILES_LOCATION] = self._gbl_location_cache.get(server_share, (0, 'LND'))[0]
                self.add_generic_data(measurement, TABLE_NAME_FILES)
                entries = self.get_measurement(file_path=measurement[COL_NAME_FILES_FILEPATH].lower())
                measid = entries[0][COL_NAME_FILES_MEASID]
            return measid
        else:
            tmp = "Recording '%s' " % measurement[COL_NAME_FILES_FILEPATH]
            tmp += "exists already in the catalog."
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError(tmp)
            else:
                warn(tmp)
                if len(entries) == 1:
                    return entries[0][COL_NAME_FILES_MEASID]
                elif len(entries) > 1:
                    tmp = "File '%s' " % (measurement[COL_NAME_FILES_RECFILEID])
                    tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
                    raise AdasDBError(tmp)

    def _convert_filepath(self, file_path):
        """
        Convert File path in to FQDN hostname for oracle only aligned with DMT

        :param file_path: path to search and convert hostname
        :type file_path: str
        :return: Dmt standard file path, project Id
        :rtype: str, int

        """
        pid = None
        server_share = ""
        if file_path[:2] == r"\\":

            # Is this lifs010 and oracle then convert to FQDN hostname
            # mount_point.split(path.sep)[2:]
            path_dirs = file_path.split(path.sep)
            if self._sub_versions['CAT'] >= CAT_LOCATIONUSAGE_VERSION and self._server_mapping:
                server_name = self._server_mapping.get(path_dirs[2].lower().split(".")[0], "")
                if server_name: # change path only if server is known
                    path_dirs[2] = server_name
                    server_share = path.sep.join(path_dirs[:4]).lower()
                file_path = path.sep.join(path_dirs)
            else:  # stay backward compatible where no GBL_LOCATION was available
                if self.db_type[0] == -1:
                    for host_alias in FILESERVER_HOST_MAPS:
                        if host_alias in path_dirs[2].lower():
                            path_dirs[2] = FILESERVER_HOST_MAPS[host_alias]
                            file_path = path.sep.join(path_dirs)
                            break

            if self.db_type[0] == -1:
                project_name = path_dirs[4] if len(path_dirs) >= 5 else "None"

                if project_name in self._gbl_projectid_cache:
                    pid = self._gbl_projectid_cache[project_name]
                else:
                    records = self.execute("SELECT %s from %s where lower(%s) = '%s'"
                                           % (COL_NAME_PROJECT_PID, TABLE_NAME_PROJECT,
                                              COL_NAME_PROJECT_NAME, project_name))
                    if len(records) == 1:
                        pid = records[0][0]
                    else:
                        pid = None
                    self._gbl_projectid_cache[project_name] = pid

        return server_share, file_path, pid

    def has_measurement(self, filepath):
        """
        Function to check if a file is in the database.

        :param filepath: The filepath.
        :type filepath: str
        :return: True or False.
        :rtype: bool
        """
        entries = self.get_measurement(file_path=filepath, select_list=[COL_NAME_FILES_MEASID])
        return len(entries) == 1

    def get_measurement_id(self, recfile, location=None):
        """
        Get a measurement ID of a file

        :param recfile: The file path name to be resolved.
        :type recfile: str
        :param location: short name of location of server storing the recfile like LND, BLR or ABH
        :type  location: str
        :return: Returns the ID for the file path or None if file not exists.
        :rtype: int
        """
        entries = self.get_measurement(file_path=recfile, select_list=[COL_NAME_FILES_MEASID], location=location)
        if len(entries) == 1:
            measid = entries[0][COL_NAME_FILES_MEASID]
        elif len(entries) > 1:
            raise AdasDBError("File '%s' cannot be resolved because it is ambiguous. (%s)" % (recfile, entries))
        else:
            raise AdasDBError("No resolution of '%s'. (%s)" % (recfile, entries))
        return measid

    def get_measurement_content_hash(self, measid):
        """
        Get a content hash of a file

        :param measid: The measurement id.
        :type measid: int
        :return: Returns the content hash for the given measid or None if measid does not exist.
        :rtype: str
        """
        entries = self.get_measurement(measid=measid, select_list=[COL_NAME_FILES_CONTENTHASH])
        if len(entries) == 1:
            hash_content = entries[0][COL_NAME_FILES_CONTENTHASH]
        elif len(entries) > 1:
            raise AdasDBError("Meas ID '%s' cannot be resolved because it is ambiguous. (%s)" % (measid, entries))
        else:
            raise AdasDBError("No resolution of Meas ID '%s'. (%s)" % (measid, entries))
        return hash_content

    def get_measurement_with_sections(self, measid, collid=None):
        """
        Get all the data from a measurement, including a list of the sections.

        :param measid: The measurement id.
        :type measid: int
        :param collid: The collection id. If None, sections from all collections are retreived.
        :type collid: Ineger
        :return: Return two values: measurement record, sections list.
        :rtype: dict, list
        """

        bpl_attr_name_start_time = "startTime"
        bpl_attr_name_end_time = "endTime"

        cond = SQLBinaryExpr(COL_NAME_FILES_MEASID, OP_EQ, measid)
        measurement_list = self.select_generic_data(select_list=["*"], table_list=[TABLE_NAME_FILES], where=cond)
        if len(measurement_list) != 1:
            raise AdasDBError("No resolution of measid: '%s'" % measid)

        measurement = measurement_list[0]

        # get sections of this measurement
        if collid is None:
            coll_cond = SQLBinaryExpr(COL_NAME_COLLMAP_MEASID, OP_EQ, measid)
        else:
            coll_cond = SQLBinaryExpr(SQLBinaryExpr(COL_NAME_COLLMAP_COLLID, OP_EQ, collid),
                                      OP_AND,
                                      SQLBinaryExpr(COL_NAME_COLLMAP_MEASID, OP_EQ, measid))

        order_expr = [SQLColumnExpr(SQLTableExpr(TABLE_NAME_COLLMAP), COL_NAME_COLLMAP_BEGINTIMESTAMP)]

        entries = self.select_generic_data(table_list=[TABLE_NAME_COLLMAP], where=coll_cond, order_by=order_expr)

        # create section list
        section_list = []
        for entry in entries:
            if((entry[COL_NAME_COLLMAP_BEGINTIMESTAMP] is not None) or
               (entry[COL_NAME_COLLMAP_ENDTIMESTAMP] is not None)):
                section = {bpl_attr_name_start_time: str("%d" % entry[COL_NAME_COLLMAP_BEGINTIMESTAMP])}

                if entry[COL_NAME_COLLMAP_ENDTIMESTAMP] is not None:
                    section[bpl_attr_name_end_time] = str("%d" % entry[COL_NAME_COLLMAP_ENDTIMESTAMP])

                section_list.append(section)

        return measurement, section_list

    def update_measurements(self, measurement, where=None):
        """
        Update existing file records.

        :param measurement: Dictionary of record with new or modified values
        :type measurement: dict
        :param where: The condition to be fulfilled by the files to the updated.
        :type where: SQLBinaryExpression
        :return: Returns the number of affected files.
        :rtype: int
        """
        rowcount = 0
        if measurement is not None:
            if where is None:
                where = SQLBinaryExpr(COL_NAME_FILES_MEASID, OP_EQ, measurement[COL_NAME_FILES_MEASID])
            self.update_generic_data(measurement, TABLE_NAME_FILES, where)
        # done
        return rowcount

    # ====================================================================
    # Handling of collection data
    # ====================================================================

    def add_collection(self, collection):
        """
        Add collection state to database.

        collection record is a dictionary with following keys/values:
            - COLLID        int (mandatory)
            - PARENTID      int (mandatory, only master collection can have None)
            - NAME          str (mandatory)
            - COLLCOMMENT   str (optional)
            - PRID          int (mandatory)
            - IS_ACTIVE     int (optional, default=1: active)
            - CP_LABEL      str (optional),

        :param collection: The collection record.
        :type collection: dict
        :return: Returns the collection ID.
        :rtype: int
        """
        collid = None

        entries = []
        # if db type is Sqlite keep the collname unique
        if self._db_type == 0:
            try:
                collid = self.get_collection_id(collection[COL_NAME_COLL_NAME], collection.get(COL_NAME_COLL_CP_LABEL))
            except AdasDBError:
                collid = None
            if collid is not None:
                tmp = "Collection '%s' " % collection[COL_NAME_COLL_NAME]
                tmp += "exists already in the catalog for this parent."
                if self.error_tolerance < ERROR_TOLERANCE_LOW:
                    raise AdasDBError(tmp)
            else:
                if len(entries) == 1:
                    return entries[0][COL_NAME_COLL_COLLID]
                elif len(entries) > 1:
                    tmp = "Collection '%s' " % (collection[COL_NAME_COLL_NAME])
                    tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
                    raise AdasDBError(tmp)
        if collid is None:
            collid = self.add_generic_data(collection, TABLE_NAME_COLL,
                                           SQLUnaryExpr(OP_RETURNING, COL_NAME_COLL_COLLID))

        return collid

    def update_collection(self, collection, collid):
        """
        Update existing collection records.

        :param collection: The collection record update, structure see at ``add_collection``
        :type collection: dict
        :param collid: collection Id
        :type collid: int
        :return: Returns the number of affected collections.
        :rtype: int
        """
        cond = SQLBinaryExpr(COL_NAME_COLL_COLLID, OP_EQ, collid)
        rowcount = 0
        if collection is not None:
            self.update_generic_data(collection, TABLE_NAME_COLL, cond)
        # done
        return rowcount

    def add_collection_map(self, collmap):
        """
        Add collection mapping to database.

        collection passed as dictionary with following structure:

        ..python::

            # mandatory values:
            collmap = {'COLLID': <int>, 'MEASID': <int>}

            # optional additions for section start and/or end timestamp:
            collmap = {'COLLID': <int>, 'MEASID': <int>, 'BEGINRELTS': <int>, 'ENDRELTS': <int>}

        A collection can have several mappings with different timestamps for the same recording.

        All timestamps are relative.

        :param collmap: The collection mapping record.
        :type collmap: dict
        :return: Returns the collection map ID.
        :rtype: int
        """
        sql_param = {}
        sql_param[str(len(sql_param) + 1)] = collmap[COL_NAME_COLLMAP_COLLID]
        coll_cond = SQLBinaryExpr(COL_NAME_COLLMAP_COLLID, OP_EQ, ":%d" % (len(sql_param)))
        sql_param[str(len(sql_param) + 1)] = collmap[COL_NAME_COLLMAP_MEASID]
        coll_cond = SQLBinaryExpr(coll_cond, OP_AND,
                                  SQLBinaryExpr(COL_NAME_COLLMAP_MEASID, OP_EQ, ":%d" % (len(sql_param))))

        if COL_NAME_COLLMAP_BEGINTIMESTAMP in collmap and collmap[COL_NAME_COLLMAP_BEGINTIMESTAMP] is not None:
            sql_param[str(len(sql_param) + 1)] = collmap[COL_NAME_COLLMAP_BEGINTIMESTAMP]
            coll_cond = SQLBinaryExpr(SQLBinaryExpr(COL_NAME_COLLMAP_BEGINTIMESTAMP,
                                                    OP_EQ, ":%d" % (len(sql_param))), OP_AND, coll_cond)

        if COL_NAME_COLLMAP_ENDTIMESTAMP in collmap and collmap[COL_NAME_COLLMAP_ENDTIMESTAMP] is not None:
            sql_param[str(len(sql_param) + 1)] = collmap[COL_NAME_COLLMAP_ENDTIMESTAMP]
            coll_cond = SQLBinaryExpr(SQLBinaryExpr(COL_NAME_COLLMAP_ENDTIMESTAMP,
                                                    OP_EQ, ":%d" % (len(sql_param))), OP_AND, coll_cond)

        entries = self.select_generic_data(table_list=[TABLE_NAME_COLLMAP], where=coll_cond, sqlparams=sql_param)
        if len(entries) <= 0:
            collmapid = self.add_generic_data(collmap, TABLE_NAME_COLLMAP,
                                              SQLUnaryExpr(OP_RETURNING, COL_NAME_COLLMAP_COLLMAPID))

            return collmapid
        else:
            tmp = "File '%s' " % collmap[COL_NAME_COLLMAP_MEASID]
            tmp += "is already assigned to collection '%s'." % collmap[COL_NAME_COLLMAP_COLLID]
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError(tmp)
            else:
                warn(tmp)
                if len(entries) == 1:
                    return entries[0][COL_NAME_COLLMAP_COLLMAPID]
                elif len(entries) > 1:
                    tmp = "Collection mapping of file '%s' " % collmap[COL_NAME_COLLMAP_MEASID]
                    tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
                    raise AdasDBError(tmp)

    def copy_collection_map(self, src_dest_collids):
        """
        Copy collection map for source collids to destination collids

        Typically copying file link information to creating collection checkpoint

        :param src_dest_collids: pair of source and destination collids
        :type src_dest_collids: list of tuple
        """
        col_list = [COL_NAME_COLLMAP_COLLID, COL_NAME_COLLMAP_MEASID, COL_NAME_COLLMAP_BEGINTIMESTAMP,
                    COL_NAME_COLLMAP_ENDTIMESTAMP, COL_NAME_COLLMAP_ASGNBY, COL_NAME_COLLMAP_ASGNDATE,
                    COL_NAME_COLLMAP_USERID, COL_NAME_COLLMAP_ASSIGNED]
        ins_stmt = "INSERT INTO %s (%s) " % (TABLE_NAME_COLLMAP, str(col_list).replace("'", "")[1:-1])

        collid_idx = col_list.index(COL_NAME_COLLMAP_COLLID)
        for src_collid, dest_collid in src_dest_collids:
            col_list[collid_idx] = str(dest_collid)
            sel_stmt = str(GenericSQLSelect(col_list, False, [TABLE_NAME_COLLMAP],
                                            SQLBinaryExpr(COL_NAME_COLLMAP_COLLID, OP_EQ, src_collid)))
            self.execute(ins_stmt + sel_stmt)

    def delete_collection_map(self, measid, collection_name):
        """
        Delete a collection map based on measid and collection name.

        In case there are several entries for one recording with different sections in one collection, then
            - all of them will be deleted

        :param measid: The measurement id.
        :type measid: int
        :param collection_name: The collection name.
        :type collection_name: str
        """
        # Find the collection id.
        collection_id = self.get_collection_id(collection_name)

        pre_cond = SQLBinaryExpr(COL_NAME_COLLMAP_MEASID, OP_EQ, measid)
        cond = SQLBinaryExpr(SQLBinaryExpr(COL_NAME_COLLMAP_COLLID, OP_EQ, collection_id), OP_AND, pre_cond)

        self.delete_generic_data(TABLE_NAME_COLLMAP, where=cond)

    def delete_collection_map_section(self, measid, collection, start_ts, end_ts):
        """
        delete a section from a collection entry

        internally: either
            - if there is only one entry: set section start and end to begin and end of recording
            - if there are several entries with different sections: delete the entry with matching start/end ts

        if start_ts and end_ts are None (so no section is set for that collection map entry)
            - if there are other entries with sections for that recording: the entry will be deleted
            - if the entry is the only one: an error will be raised,
              use ``delete_collection_map`` to delete (unlink) the complete recording

        All timestamps are relative timestamps.

        :param measid: The measurement id.
        :type measid: int
        :param collection: collection name or db internal id (if available, otherwise will be extracted from db)
        :type collection: str
        :param start_ts: rel. timestamp of section start used for recording in this collection
        :type  start_ts: int
        :param end_ts: rel. timestamp of section end used for recording in this collection
        :type  end_ts: int
        """
        if type(collection) == str:
            collid = self.get_collection_id(collection)
        else:
            collid = collection

        # get all section entries for measid in collection
        cat_meas, sec_data = self.get_measurement_with_sections(measid, collid=collid)

        if len(sec_data) == 1:
            # if it's the only one : delete the section (set to None)
            if start_ts is None and end_ts is None:
                raise AdasDBError("no sections defined for measid={} in collection {}, "
                                  "use 'delete_collection_map()' to unlink this entry!".format(measid, collection))
            self.update_collection_map_section(measid, collid, start_ts, end_ts, None, None)
        else:
            # if there are others: delete the correct entry
            map_cond = SQLBinaryExpr(SQLBinaryExpr(COL_NAME_COLLMAP_COLLID, OP_EQ, collid),
                                     OP_AND,
                                     SQLBinaryExpr(COL_NAME_COLLMAP_MEASID, OP_EQ, measid))
            sect_cond = SQLBinaryExpr(SQLBinaryExpr(COL_NAME_COLLMAP_BEGINTIMESTAMP, OP_EQ, start_ts),
                                      OP_AND,
                                      SQLBinaryExpr(COL_NAME_COLLMAP_ENDTIMESTAMP, OP_EQ, end_ts))
            cond = SQLBinaryExpr(map_cond, OP_AND, sect_cond)
            self.delete_generic_data(TABLE_NAME_COLLMAP, where=cond)

    def update_collection_map_section(self, measid, collection, old_start_ts, old_end_ts, new_start_ts, new_end_ts,
                                      label=None):
        """
        changes stored section start/end timestamps for a collection entry

        All timestamps are relative timestamps.

        An error is raised if there is no entry with given measid, collection, old_start_ts and new_start_ts.

        :param measid: The measurement id.
        :type measid: int
        :param collection: collection name or db internal id (if available, otherwise will be extracted from db)
        :type collection: str
        :param old_start_ts: rel. timestamp of section start stored for recording in this collection
        :type  old_start_ts: int
        :param old_end_ts: rel. timestamp of section end stored for recording in this collection
        :type  old_end_ts: int, None
        :param new_start_ts: new rel. start timestamp to replace the stored one
        :type  new_start_ts: int, None
        :param new_end_ts: new rel. end timestamp to replace the stored one
        :param label: opt. checkpoint label, reqires name (str) for collection
        :type  label: str
        :return: Returns the number of affected rows.
        :rtype: Integer
        """
        if type(collection) == str:
            collid = self.get_collection_id(collection, label=label)
        else:
            collid = collection

        # assemble the query and update entry
        cond1 = SQLBinaryExpr(COL_NAME_COLLMAP_COLLID, OP_EQ, collid)
        cond2 = SQLBinaryExpr(COL_NAME_COLLMAP_MEASID, OP_EQ, measid)
        cond3 = SQLBinaryExpr(cond1, OP_AND, cond2)

        cond4 = SQLBinaryExpr(COL_NAME_COLLMAP_BEGINTIMESTAMP, OP_EQ, old_start_ts)
        cond5 = SQLBinaryExpr(COL_NAME_COLLMAP_ENDTIMESTAMP, OP_EQ, old_end_ts)
        cond6 = SQLBinaryExpr(cond4, OP_AND, cond5)

        cond = SQLBinaryExpr(cond3, OP_AND, cond6)

        return self.update_generic_data({COL_NAME_COLLMAP_BEGINTIMESTAMP: new_start_ts,
                                         COL_NAME_COLLMAP_ENDTIMESTAMP: new_end_ts},
                                        TABLE_NAME_COLLMAP, where=cond)

    def delete_collection(self, collection_name, label=None):
        """
        Delete a collection based on the collection name.This function requires as prerequisite removal of all the
        collection map entries and collection should not be the parent of other collection.

        :param collection_name: The collection name.
        :type collection_name: str
        :param label: opt. checkpoint label
        :type  label: str
        :return: Return boolean representing success or failure of delete, error string
        :rtype: bool, string
        """
        # Find the collection id.
        collection_id = self.get_collection_id(collection_name, label)

        # Get the measurements. There should be none.
        meas_count = self.get_measurements_number(collection_id, recurse=False)
        if meas_count != 0:
            return False, "Delete measurements prior to deleting collection."

        # Find collections with the collection id as parent. There should be none.
        sub_collections = self.get_collections(collection_id)
        if len(sub_collections) != 0:
            return False, "Delete sub-collections prior to deleting collection."

        cond = SQLBinaryExpr(COL_NAME_COLL_COLLID, OP_EQ, collection_id)
        self.delete_generic_data(TABLE_NAME_COLL, where=cond)

        return True, ""

    def activate_collection(self, coll_name=None, collid=None, label=None):
        """
        Set collection active flag 1 to activate collection

        :param coll_name: collection name
        :type coll_name: String
        :param collid: Collection Id
        :type collid: Integer
        :param label: opt. checkpoint label
        :type  label: str
        :return: return True if the execution was sucessfull otherwise return false on failure
        :rtype: Boolean
        """
        return self.update_collection_active_flag(1, coll_name, collid, label)

    def is_collection_active(self, coll_name=None, collid=None, label=None):
        """
        Get collection active status

        :param coll_name: collection name
        :type coll_name: String
        :param collid: db internal ID of Collection, use instead of coll_name, taken first if both provided
        :type collid: Integer
        :param label: opt. checkpoint label, reqires coll_name
        :type  label: str
        :return: return True if the collection is active otherwise return False if the collection is Inactive
        :rtype: Boolean
        """
        if self.sub_scheme_version >= CAT_ACTIVE_VERSION:
            cond = None
            sql_param = {}
            if coll_name is not None:
                sql_param[str(len(sql_param) + 1)] = coll_name.lower()

                cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                 COL_NAME_COLL_NAME), OP_EQ, ":%d" % (len(sql_param)))

            if collid is not None:
                sql_param[str(len(sql_param) + 1)] = collid
                if cond is None:
                    cond = SQLBinaryExpr(COL_NAME_COLL_COLLID, OP_EQ, ":%d" % (len(sql_param)))
                else:
                    cond = SQLBinaryExpr(cond, OP_AND,
                                         SQLBinaryExpr(COL_NAME_COLL_COLLID, OP_EQ, ":%d" % (len(sql_param))))
            if self.sub_scheme_version >= CAT_CHECKPOINT_VERSION:

                if label is None or label == "":
                    cp_cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                        COL_NAME_COLL_CP_LABEL), OP_EQ, SQLLiteral(""))
                    cp_cond = SQLBinaryExpr(cp_cond, OP_OR, SQLBinaryExpr(COL_NAME_COLL_CP_LABEL, OP_IS, SQLNull()))
                else:
                    sql_param[str(len(sql_param) + 1)] = label.lower()
                    cp_cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                        COL_NAME_COLL_CP_LABEL), OP_EQ, ":%d" % (len(sql_param)))

            entries = []
            if cond is not None:
                entries = self.select_generic_data([COL_NAME_COLL_IS_ACTIVE],
                                                   table_list=[TABLE_NAME_COLL], where=cond, sqlparams=sql_param)
            if len(entries) == 1:
                return entries[0][COL_NAME_COLL_IS_ACTIVE]
            else:
                raise AdasDBError("Invalid collection name %s or Collid %s" % (coll_name, str(collid)))

        # if the feature missing then all collection are treated as active
        return 1

    def deactivate_collection(self, coll_name=None, collid=None, label=None):
        """
        Set collection active flag 0 to deactivate collection

        :param coll_name: collection name
        :type  coll_name: str
        :param collid: Collection Id
        :type  collid: Integer
        :param label: opt. name of checkpoint label, reqires coll_name
        :type  label: str
        :return: return True if the execution was successful otherwise return false on failure
        :rtype: Boolean
        """
        return self.update_collection_active_flag(0, coll_name, collid, label)

    def update_collection_active_flag(self, is_active, coll_name=None, collid=None, label=None):
        """
        update collection is_active value in cat_collection table

        :param is_active: Flag value representing with allowed value 0 or 1
        :type is_active: int
        :param coll_name: collection name
        :type coll_name: str
        :param collid: Collection Id
        :type collid: int
        :param label: opt. checkpoint label, requires coll_name
        :type  label: str
        :return: return True if the execution was sucessful otherwise return false on failure
        :rtype: Boolean
        """
        if self.sub_scheme_version < CAT_ACTIVE_VERSION:
            warn("Database schema is too old to support collection active inactive feature")

        elif is_active == 1 or is_active == 0:
            if collid is None and coll_name is not None:
                collid = self.get_collection_id(coll_name, label)

            if collid is not None:
                self.update_collection({COL_NAME_COLL_IS_ACTIVE: is_active}, collid)
                return True

        return False

    def get_collection(self, coll_id):
        """
        Return all the collection entry based on the collection id.

        :param coll_id: The collection id.
        :type coll_id: int
        :return: Collection record in dict format, see details in ``add_collection``
        :rtype: dict
        """
        cond = SQLBinaryExpr(COL_NAME_COLL_COLLID, OP_EQ, ":1")
        collection_list = self.select_generic_data(["*"], [TABLE_NAME_COLL], where=cond, sqlparams={"1": coll_id})
        if len(collection_list) == 0:
            return None
        return collection_list[0]

    def get_collection_id(self, coll_name, label=None):
        """
        Find a collection with a given name (absolute or basic).

        :param coll_name: The collection name.
        :type coll_name: str
        :param label: opt. checkpoint label
        :type  label: str
        :return: Returns the collection ID or None if not exists.
        :rtype: int
        """
        collid = None
        coll_name = coll_name.rstrip(PATH_SEPARATOR).split(PATH_SEPARATOR)
        coll_name = coll_name[-1]
        sql_param = {"1": coll_name.lower()}
        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER], COL_NAME_COLL_NAME), OP_EQ, ":1")
        if self.sub_scheme_version >= CAT_CHECKPOINT_VERSION:
            if label is None or label == "":
                cp_cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                    COL_NAME_COLL_CP_LABEL), OP_EQ, SQLLiteral(""))
                cp_cond = SQLBinaryExpr(cp_cond, OP_OR, SQLBinaryExpr(COL_NAME_COLL_CP_LABEL, OP_IS, SQLNull()))
            else:
                sql_param[str(len(sql_param) + 1)] = label.lower()
                cp_cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                    COL_NAME_COLL_CP_LABEL), OP_EQ, ":%d" % (len(sql_param)))
            cond = SQLBinaryExpr(cond, OP_AND, cp_cond)
        entries = self.select_generic_data([COL_NAME_COLL_COLLID], table_list=[TABLE_NAME_COLL], where=cond,
                                           sqlparams=sql_param)
        if len(entries) == 1:
            collid = entries[0][COL_NAME_COLL_COLLID]
        elif len(entries) <= 0:
            raise AdasDBError("Collection '%s' doesn't exists in the catalog." % coll_name)

        return collid

    def get_collection_name(self, collid):
        """Get the name of a collection either basic or absolute.

        :param collid: The collection ID.
        :type collid: int
        :return: Returns the collection name or None if not exists.
        :rtype: str
        """
        coll_name = ""
        if collid is None:
            return coll_name

        else:
            record = self.get_collection(collid)
            if record is None:
                raise AdasDBError("Collection '%s' doesn't exists in the catalog." % collid)
            else:
                parent_coll_name = self.get_collection_name(record[COL_NAME_COLL_PARENTID])
                coll_name = parent_coll_name + PATH_SEPARATOR + record[COL_NAME_COLL_NAME]

        return coll_name

    def get_collection_checkpoint(self, collid):
        """return the checkpoint label

        If no checkpoint is defined for the collection an empty string is returned.

        An AdasDBError is raised if passed collection Id is not found.

        :param collid: db internal id of collection with/without checkpoint
        :type  collid: int
        :return: name of checkpoint label or empty string
        :rtype: str
        """
        chkpt_name = ""
        if collid is not None:
            record = self.get_collection(collid)
            if record is None:
                raise AdasDBError("Collection '%s' doesn't exists in the catalog." % collid)
            else:
                chkpt_name = record.get(COL_NAME_COLL_CP_LABEL)
        # if column is not available (old db) or empty (None) we need to return ''
        return chkpt_name if chkpt_name is not None else ''

    def get_collections_details(self, collection, recurse=True, label=None):
        """gets all sub-collection details of a given collection

        :param collection: name of collection or it's ID
        :type collection: int | str
        :param recurse: set True, if sub-collections shall be searched recursively
        :type recurse: bool
        :param label: opt. checkpoint label, collection param must pass name of collection
        :type  label: str
        :return: returns sub-collection details
        :rtype: list[dict]
        """
        if type(collection) == str:
            collid = self.get_collection_id(collection, label=label)
        else:
            collid = collection

        col_list = [COL_NAME_COLL_COLLID, COL_NAME_COLL_NAME, COL_NAME_COLL_IS_ACTIVE, COL_NAME_COLL_PRID,
                    COL_NAME_COLL_COLLCOMMENT, COL_NAME_COLL_PARENTID]
        if recurse:
            rec_list, col_list = self.get_collection_tree(collid, incl_shared=True, col_list=col_list)
            # exclude the first record it was not expect as per previous implementation and convert to list of dict
            records = [dict(zip(col_list, rec)) for rec in rec_list[1:]]
        else:

            cond = SQLBinaryExpr(COL_NAME_COLL_PARENTID, OP_EQ, ":1")
            records = self.select_generic_data(col_list, table_list=[TABLE_NAME_COLL],
                                               where=cond, sqlparams={"1": collid})
        return records

    @deprecated()
    def _get_union_shared_collection_cond(self, tree_sql, sql_param):  # pylint: disable=C0103
        """
        Generate SQL condition for the given recursive query to include all the shared collection subtree

        :deprecated: method not used anymore, will be deleted in future, update for get_collections() missing
        """
        trees_sql = "(%s)" % (str(tree_sql))
        if self.sub_scheme_version >= CAT_SHARECOLL_VERSION:

            shared_coll_cond = SQLBinaryExpr(COL_NANE_SHARECOLL_PARENT_COLLID, OP_IN, trees_sql)
            shared_coll_query = GenericSQLSelect([COL_NANE_SHARECOLL_CHILD_COLLID], True,
                                                 [TABLE_NAME_CAT_SHAREDCOLLECTIONMAP], shared_coll_cond)
            shared_coll = [i[0] for i in self.execute(str(shared_coll_query), **sql_param)]  # pylint: disable=W0142
            for i in range(len(shared_coll)):
                shared_coll = shared_coll + self.get_collections(shared_coll[i])
            shared_coll = list(set(shared_coll))
            shared_coll = [shared_coll[i:i + 999] for i in range(0, len(shared_coll), 999)]
            cond = SQLBinaryExpr(COL_NAME_COLL_COLLID, OP_IN, trees_sql)
            trees_sql = "(%s)" % str(GenericSQLSelect([COL_NAME_COLL_COLLID], False, [TABLE_NAME_COLL], cond))
            for entry in shared_coll:
                cond = SQLBinaryExpr(COL_NAME_COLL_COLLID, OP_IN, str(tuple(entry)))
                trees_sql += " UNION (%s)" % (str(GenericSQLSelect([COL_NAME_COLL_COLLID],
                                                                   False, [TABLE_NAME_COLL], cond)))
        cond = SQLBinaryExpr(COL_NAME_COLL_COLLID, OP_IN, trees_sql)
        return cond

    def get_collection_summary(self, collid, recurse=True, group_by=None):
        """
        Make summary of aggregated statistic of file_size, file_count and duration for TDSM

        :param collid: collection Id
        :type collid: int
        :param recurse: boolean flag to include sub collection
        :type recurse: boolean
        :param group_by: aggregate the value in group_by column. group by column will included select stmt implicity
        :type group_by: list
        :return: list of dict on executed query
        :rtype: list
        """
        file_count = SQLBinaryExpr(SQLFuncExpr(EXPR_COUNT, COL_NAME_FILES_MEASID), OP_AS, "FILE_COUNT")

        file_size = SQLBinaryExpr(SQLFuncExpr("SUM", SQLBinaryExpr(COL_NAME_FILES_FILESIZE, OP_DIV,
                                                                   "(1073741824)")),  # 1024^3
                                  OP_AS, COL_NAME_FILES_FILESIZE)
        file_dur = SQLBinaryExpr(SQLBinaryExpr("NVL(%s, 0)" % COL_NAME_FILES_ENDTIMESTAMP, OP_SUB,
                                               "NVL(%s, 0)" % COL_NAME_FILES_BEGINTIMESTAMP),
                                 OP_MUL, 0.000001)  # convert to second

        file_dur = SQLBinaryExpr(SQLFuncExpr("SUM", file_dur), OP_AS, "DURATION")
        return self._get_collection_stats(collid, [file_count, file_size, file_dur], recurse, group_by)

    def _get_collection_stats(self, collid, cf_columns, recurse=True, group_by=None):
        """
        Generic function get aggregated statistic over recordings inside collection

        :param collid: collection id
        :type collid: int
        :param cf_columns: list of column from cat_Files table
        :type cf_columns: list
        :param recurse: boolean flag to include sub collection
        :type recurse: boolean
        :param group_by: aggregate the value in group_by column
        :type group_by: list
        :return: return records as list of dict on executed query
        :rtype: list
        """
        sql_param = {}
        sql_param[str(len(sql_param) + 1)] = collid
        recurs_with = ''
        if recurse:
            cond1, recurs_with = self._get_shared_collection_tree_query()
        else:
            cond1 = SQLBinaryExpr(COL_NAME_COLLMAP_COLLID, OP_EQ, ":%s" % (len(sql_param)))
        cmap_tbl = str(GenericSQLSelect([COL_NAME_COLLMAP_MEASID], True, [TABLE_NAME_COLLMAP], cond1))
        cond = SQLBinaryExpr(COL_NAME_FILES_MEASID, OP_IN, "(%s)" % cmap_tbl)

        if group_by is not None:
            select_list = cf_columns + group_by
        else:
            select_list = cf_columns
        return self.select_generic_data(select_list, [TABLE_NAME_FILES], cond, group_by, sqlparams=sql_param,
                                        with_clause=recurs_with)

    def get_measurements_number(self, collection, recurse=True, group_by=None, label=None):
        """retrieves the amount of measurements being inside a collection

        :param collection: name or id of collection which is considered as root of desire tree
        :type collection: str, int
        :param recurse: count also sub collections along with root collection
        :type recurse: bool
        :param group_by: group by column list e.g. ARCHIVED, PID or any column in CAT_FILES
        :type group_by: list
        :param label: opt. checkpoint label, only used if collection passed by name
        :type  label: str
        :return: number of recordings as integer group_by is not provide, otherwise list of dict
        :rtype: int | list
        """
        if type(collection) == str:
            collid = self.get_collection_id(collection, label=label)
        else:
            collid = collection
        cf_columns = [SQLBinaryExpr(SQLFuncExpr(EXPR_COUNT, COL_NAME_FILES_MEASID), OP_AS, "FILE_COUNT")]

        entries = self._get_collection_stats(collid, cf_columns, recurse, group_by)
        return entries[0]["FILE_COUNT"] if group_by is None else entries

    def _build_collection_query(self, collection, recurse, startcol, label=None):
        """builds up recursive query for collection details

        :param collection: name or id of collection
        :type collection: int | str
        :param recurse: weather we need to follow recurse query or not
        :type recurse: bool
        :param startcol: column name to base query upon
        :type startcol: str
        :param label: opt. checkpoint label, only used if collection passed by name
        :type  label: str
        :return: recursive and out query
        :rtype: SQLBinaryExpr, GenericSQLSelect
        """

        if type(collection) == str:
            cond = SQLBinaryExpr(COL_NAME_COLL_NAME, OP_LIKE, SQLLiteral(collection))

            if self.sub_scheme_version >= CAT_CHECKPOINT_VERSION:
                if label is None or label == "":
                    cp_cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                        COL_NAME_COLL_CP_LABEL), OP_EQ, SQLLiteral(""))
                    cp_cond = SQLBinaryExpr(cp_cond, OP_OR, SQLBinaryExpr(COL_NAME_COLL_CP_LABEL, OP_IS, SQLNull()))
                    cond = SQLBinaryExpr(cond, OP_AND, cp_cond)
                else:
                    cp_cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                        COL_NAME_COLL_CP_LABEL), OP_EQ, label.lower())
                    cond = SQLBinaryExpr(cond, OP_AND, cp_cond)
            sbe = GenericSQLSelect([COL_NAME_COLL_COLLID], False, [TABLE_NAME_COLL], cond)
            oper = OP_IN
        else:
            sbe = SQLIntegral(collection)
            oper = OP_EQ

        sbe = SQLBinaryExpr(startcol, oper, sbe)

        if not recurse:
            return sbe, None

        virtcoll = "coll"
        start = GenericSQLSelect([COL_NAME_COLL_COLLID], False, [TABLE_NAME_COLL], sbe)
        join = SQLJoinExpr(TABLE_NAME_COLL, OP_INNER_JOIN, SQLTableExpr(GEN_RECUR_NAME, "r"),
                           SQLBinaryExpr(COL_NAME_COLL_PARENTID, OP_EQ, SQLColumnExpr("r", virtcoll)))
        stop = GenericSQLSelect([COL_NAME_COLL_COLLID], False, [join])
        outer = GenericSQLSelect([virtcoll], False, [GEN_RECUR_NAME])
        wexp = str(SQLConcatExpr(EXPR_WITH, SQLFuncExpr(GEN_RECUR_NAME, virtcoll)))
        wexp = SQLBinaryExpr(wexp, OP_AS, SQLConcatExpr(start, OP_UNION_ALL, stop))

        return wexp, outer

    def get_collections(self, collid, recurse=True):
        """
        Get the sub-collections of a collection.

        :param collid: The ID of the collection.
        :type collid: int
        :param recurse: Set True, if sub-collections shall be searched recursively.
        :type recurse: bool
        :return: Returns the sub-collection ids of a collection.
        :rtype: list
        """
        if recurse:
            records, _ = self.get_collection_tree(collid, incl_shared=True, col_list=[COL_NAME_COLL_COLLID])
            # remove the first entry this function doesnt expect the entry of passed collid
            records = records[1:] if len(records) >= 1 else []
        else:
            if self.sub_scheme_version < CAT_SHARECOLL_VERSION:
                cond = ' PARENTID = :1'
            else:
                cond = ' PARENTID = :1' \
                       ' UNION ALL' \
                       ' SELECT CHILD_COLLID as COLLID FROM CAT_SHAREDCOLLECTIONMAP' \
                       ' WHERE PARENT_COLLID = :1'
            records = self.select_generic_data_compact([COL_NAME_COLL_COLLID], [TABLE_NAME_COLL],
                                                       where=cond, sqlparams={"1": collid})[1]
        return [rec[0] for rec in records if rec[0] != collid]

    def get_all_collection_names(self):
        """Get the Names of all collections.

        :return: Returns all collections names list
        :rtype: list
        """
        select_list = [SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_COLL), COL_NAME_COLL_NAME),
                                     OP_AS, COL_NAME_COLL_NAME)]

        entries = self.select_generic_data(select_list=select_list, table_list=[TABLE_NAME_COLL])
        return [entrie[COL_NAME_COLL_NAME] for entrie in entries]

    def get_collection_measurements(self, collid, recurse=True,  # pylint: disable=R0912,R0914
                                    recfile_paths=False, recfile_dict=False):
        """
        Get all measurement for the given collection

        :param collid: The ID of the collection.
        :type collid: int
        :param recurse: if Set True, sub-collections shall be searched recursively.
        :type recurse: bool
        :param recfile_paths: if Set True then recfile paths shall be returned.
               Otherwise the measurement IDs are returned.
        :type recfile_paths: bool
        :param recfile_dict: if Set True then dictionary with recfile path as keys
               and measurement Id as values will be returned
        :type recfile_dict: bool
        :return: Returns the list of recording as list or dictionary
        :rtype: dict | list
        """
        sql_param = {}
        cmap_tbl_alias = "cmap"
        cf_tbl_alias = "cf"
        cf_tbl = SQLTableExpr(TABLE_NAME_FILES, cf_tbl_alias)
        sql_param[str(len(sql_param) + 1)] = collid
        # default column to return: measid, add filepath if requested
        columns = [SQLColumnExpr(cf_tbl_alias, COL_NAME_FILES_MEASID)]
        if recfile_paths or recfile_dict:
            columns.append(SQLColumnExpr(cf_tbl_alias, COL_NAME_FILES_FILEPATH))

        # setup select, join and condition
        join_map = SQLJoinExpr(TABLE_NAME_COLL, OP_INNER_JOIN,
                               SQLTableExpr(TABLE_NAME_COLLMAP, cmap_tbl_alias),
                               SQLFuncExpr(OP_USING, COL_NAME_COLL_COLLID), OP_NOP)
        join = SQLJoinExpr(join_map, OP_INNER_JOIN, cf_tbl,
                           SQLFuncExpr(OP_USING, COL_NAME_FILES_MEASID), OP_NOP)
        if recurse:
            cond, rewith = self._get_shared_collection_tree_query()
        else:
            cond = SQLBinaryExpr(COL_NAME_COLLMAP_COLLID, OP_EQ, ":%s" % (len(sql_param)))
            rewith = ''

        columns = [COL_NAME_FILES_MEASID]
        if recfile_paths or recfile_dict:
            columns.append(SQLColumnExpr(cf_tbl_alias, COL_NAME_FILES_FILEPATH))
        try:
            rec_data = self.select_generic_data_compact(with_clause=rewith, select_list=columns,
                                                        table_list=[join], where=cond,
                                                        distinct_rows=False, sqlparams=sql_param)
        except TypeError:
            # for empty collection an empty list should be returned,
            # in this case there is no description and select_generic_data_compact stumbles while extracting from it
            records = []
        else:
            records = rec_data[1]

        if recfile_paths and recfile_dict:
            recfile_data_dict = {recfile[1]: recfile[0]
                                 for recfile in records}
        elif recfile_paths and not recfile_dict:
            recfile_list = list(set([recfile[1] for recfile in records]))

        elif not recfile_paths and recfile_dict:
            recfile_data_dict = {recfile[0]: recfile[1]
                                 for recfile in records}
        elif not recfile_paths and not recfile_dict:
            recfile_list = list(set([recfile[0] for recfile in records]))
        if recfile_dict:
            return recfile_data_dict
        else:
            return recfile_list

    def update_collection_priority(self, collid, prid):
        """
        Update/Assign priority to collection

        :param collid: collection Id
        :type collid: int
        :param prid: priority Id
        :type prid: int
        """
        # cond = SQLBinaryExpr(collid, OP_EQ, collid)
        cond = SQLBinaryExpr(COL_NAME_COLL_COLLID, OP_EQ, collid)
        self.update_generic_data({COL_NAME_COLL_PRID: prid}, TABLE_NAME_COLL, cond)

    def update_shared_collection_priority(self, parent_collid, child_collid, prid):  # pylint: disable=C0103
        """
        Update/Assign priority to collection in its shared location

        :param parent_collid: parent collection Id
        :type parent_collid: int
        :param child_collid: child collection id
        :type child_collid: int
        :param prid: priority id
        :type prid: int
        """
        cond = SQLBinaryExpr(COL_NANE_SHARECOLL_PARENT_COLLID, OP_EQ, parent_collid)
        cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COL_NANE_SHARECOLL_CHILD_COLLID, OP_EQ, child_collid))
        self.update_generic_data({COL_NANE_SHARECOLL_PRID: prid}, TABLE_NAME_CAT_SHAREDCOLLECTIONMAP, cond)

    def get_shared_collection_priority(self, parent_collid, child_collid):
        """
        get priority for the shared location

        :param parent_collid: parent collection Id
        :type parent_collid: int
        :param child_collid: child collection id
        :type child_collid: int
        :return: list of dictionary record contain prority Id
        :rtype: list[dict]
        """
        sql_param = {}
        sql_param[str(len(sql_param) + 1)] = parent_collid
        cond = SQLBinaryExpr(COL_NANE_SHARECOLL_PARENT_COLLID, OP_EQ, ":%s" % str(len(sql_param)))
        sql_param[str(len(sql_param) + 1)] = child_collid
        cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COL_NANE_SHARECOLL_CHILD_COLLID,
                                                         OP_EQ, ":%s" % str(len(sql_param))))
        return self.select_generic_data([COL_NANE_SHARECOLL_PRID], [TABLE_NAME_CAT_SHAREDCOLLECTIONMAP],
                                        cond, sqlparams=sql_param)

    def get_collection_priority(self, collid):
        """
        Get Priority Id for the given collection Id

        :param collid: Collection Id
        :type collid: int
        :return: Return priority of collection
        :rtype: int
        """
        # cond = SQLBinaryExpr(collid, OP_EQ, collid)
        cond = SQLBinaryExpr(COL_NAME_COLL_COLLID, OP_EQ, collid)
        tblcollections = TABLE_NAME_COLL

        entries = self.select_generic_data(select_list=[COL_NAME_COLL_PRID], table_list=[tblcollections], where=cond)
        if len(entries) == 1:
            return entries[0][COL_NAME_COLL_PRID]
        elif len(entries) > 1:
            raise StandardError("Cannot Resolve collid " + str(collid) + " because it is ambigious")
        return -1

    def add_collection_checkpoint(self, coll_name, label, desc=None):
        """
        adds a new collection checkpoint out of ``collection`` using new ``label``
        with changed ``description`` on same parent level(s)

        Copy all collection entries to a new collection with same name and set the checkpoint label for it,
        do this also for all sub collections and all linked shared collections.

        A checkpointed collection freezes the current state for simulation and validation for customer reports.
        It can not be updated anymore and deleted only with special user rights.
        Because it is frozen it doesn't make sense to create a checkpoint for a checkpointed collection (no difference),
        therefore the starting collection has to be one without checkpoint.

        It is possible to have different checkpoints of the same starting collection,
        but please **check before creating a new checkpoint if there is really a difference to existing ones**
        as we always create a real complete copy of all entries to keep forever!

        **The collection name together with the checkpoint label have to be unique in the database!**

        :param coll_name: name of collection to create a checkpoint from
        :type coll_name: str
        :param label: checkpoint label
        :type label: str
        :param desc: changed description
        :type desc: None | str
        :return: collection identifier of new checkpointed collection, None if failed
        :rtype: int
        """
        src_id = self.get_collection_id(coll_name)
        src = self.get_collection(src_id)
        maps = []
        ret = self._copy_collection(src, None, label, desc, maps)
        self.copy_collection_map(maps)
        self.commit()
        return ret

    def _copy_collection(self, src, par_id, label, desc, maps):
        """recursively copy new collection

        :param src: source collection dict
        :type  src: collection dict (see 'add_collection')
        :param par_id: new parent id of copy
        :type  par_id: int
        :param label: collection label
        :type  label: str
        :param maps: collection maps to be copied [(src-id, dst-id),...], extended with each copied collection
        :type  maps: list of tuples
        :param desc: collection description
        :type  desc: str

        :return: DB ID of collection
        :rtype:  int
        """
        # dst = dst.add_coll(name=src.name, label=label, desc=desc, prio=src.prio)
        dst = deepcopy(src)
        dst[COL_NAME_COLL_CP_LABEL] = label
        dst[COL_NAME_COLL_PARENTID] = par_id
        if desc:
            dst[COL_NAME_COLL_COLLCOMMENT] = desc
        dst[COL_NAME_COLL_COLLID] = None
        dst.pop(COL_NAME_COLL_CREATED)
        dst_id = self.add_collection(dst)
        maps.append((src[COL_NAME_COLL_COLLID], dst_id))
        colls = self.get_collections(src[COL_NAME_COLL_COLLID], recurse=False)
        # iterate thought child collections
        for i in colls:
            self._copy_collection(self.get_collection(i), dst_id, label, desc, maps)
        # create copies of shared colls
        # colls = self.get_shared_collid(src[COL_NAME_COLL_COLLID])
        # for i in colls:
        #     self._copy_collection(self.get_collection(i), dst_id, label, desc, maps)
        return dst_id

    def export_bpl_measurment(self, measid_list, output_path, inc_section=False, relativets=True):
        """
        Export BPL file for the selected measurement Ids

        :param measid_list: list of measurement Ids
        :type measid_list: list
        :param output_path: path to output BPL file
        :type output_path: string
        :param inc_section: flag to include section information if avaiable, default: don't include
        :type inc_section: bool
        :param relativets: Boolean flag to specify whether section timestamps are relative or absolute
                           default is Relative. Set it to false if sections are based absolute timestamp
        :type relativets: bool
        """
        bplfile = Bpl(output_path)
        for measid in measid_list:
            resdict = self.get_measurement(measid=measid, select_list=[COL_NAME_FILES_FILEPATH])
            bplentry = BplListEntry(resdict[0][COL_NAME_FILES_FILEPATH])
            bplfile.append(bplentry)

            if inc_section:
                cat_meas, sec_data = self.get_measurement_with_sections(measid)
                for section in sec_data:
                    if relativets:
                        # add relative timestamps
                        bplentry.append(int(section['startTime']), int(section['endTime']), True)
                    else:
                        # calculate absolute timestamps
                        bplentry.append(cat_meas[COL_NAME_FILES_BEGINTIMESTAMP] + int(section['startTime']),
                                        cat_meas[COL_NAME_FILES_BEGINTIMESTAMP] + int(section['endTime']),
                                        False)

        bplfile.write()

    def export_bpl_for_collection(self, coll_name, output_path,  # pylint: disable=W0102,R0912,R0913,R0914,R0915
                                  recurse=True, inc_section=False, relativets=True, orderby=[], label=None):
        """
        Export BPL file for the given collection based on priority.

        If no priority is assigned then default priority level NORMAL will be used.
        For backward compatibility to older subschema all the collections have NORMAL priority

        :param coll_name: Collection name
        :type coll_name: string
        :param output_path: path to output BPL FILE
        :type output_path: string
        :param recurse: Boolean flag to include child collection
        :type recurse: bool
        :param inc_section: Boolean flag to include Sections in BPL default is False i.e. dont include
        :type inc_section: bool
        :param relativets: Boolean flag to specify whether section timestamps are relative or absolute,
                           default: True (relative).
                           Set it to false if sections should be listed with absolute timestamp
        :type relativets: bool
        :param orderby: give it an order, dude!
        :type  orderby: list
        :param label: opt. checkpoint label
        :type  label: str
        """
        bplfile = Bpl(output_path)
        cmap_tbl_alias = "cmap"
        cf_tbl_alias = "cf"
        coll_tbl_alias = "coll"
        cf_tbl = SQLTableExpr(TABLE_NAME_FILES, cf_tbl_alias)
        coll_tbl = SQLTableExpr(TABLE_NAME_COLL, coll_tbl_alias)
        collid = self.get_collection_id(coll_name, label=label)
        fpath_exports = {}
        sql_param = {"1": collid}
        select_list = []
        recurs_with = None
        join_map = SQLJoinExpr(coll_tbl, OP_INNER_JOIN, SQLTableExpr(TABLE_NAME_COLLMAP, cmap_tbl_alias),
                               SQLFuncExpr(OP_USING, COL_NAME_COLL_COLLID), OP_NOP)
        join = SQLJoinExpr(join_map, OP_INNER_JOIN, cf_tbl,
                           SQLFuncExpr(OP_USING, COL_NAME_FILES_MEASID), OP_NOP)
        if recurse and collid is not None:
            cond, recurs_with = self._get_shared_collection_tree_query()
            select_list.append(COL_NAME_COLL_PRID)
        else:
            cond = SQLBinaryExpr(SQLColumnExpr(cmap_tbl_alias, COL_NAME_COLLMAP_COLLID),
                                 OP_EQ, ":%d" % (len(sql_param)))

        col_sectbegin_collmap = SQLColumnExpr(cmap_tbl_alias, COL_NAME_COLLMAP_BEGINTIMESTAMP)
        col_sectend_collmap = SQLColumnExpr(cmap_tbl_alias, COL_NAME_COLLMAP_ENDTIMESTAMP)
        select_list.append(COL_NAME_FILES_FILEPATH)
        select_list.append(COL_NAME_COLLMAP_COLLID)
        select_list.append(COL_NAME_COLLMAP_MEASID)

        if inc_section:
            if relativets:
                select_list.append(SQLBinaryExpr(col_sectbegin_collmap, OP_AS, COL_NAME_COLLMAP_BEGINTIMESTAMP))
                select_list.append(SQLBinaryExpr(col_sectend_collmap, OP_AS, COL_NAME_COLLMAP_ENDTIMESTAMP))
            else:
                col_beginabsts_catfiles = SQLColumnExpr(cf_tbl_alias, COL_NAME_FILES_BEGINTIMESTAMP)
                col_sectbeginabsts_collmap = SQLBinaryExpr(col_beginabsts_catfiles, OP_ADD, col_sectbegin_collmap)
                col_sectendabsts_collmap = SQLBinaryExpr(col_beginabsts_catfiles, OP_ADD, col_sectend_collmap)
                select_list.append(SQLBinaryExpr(col_sectbeginabsts_collmap, OP_AS, COL_NAME_COLLMAP_BEGINTIMESTAMP))
                select_list.append(SQLBinaryExpr(col_sectendabsts_collmap, OP_AS, COL_NAME_COLLMAP_ENDTIMESTAMP))
        if len(orderby) == 0 and recurse:
            orderby.append(COL_NAME_COLL_PRID)

        records = self.select_generic_data_compact(with_clause=recurs_with,
                                                   select_list=select_list, table_list=[join],
                                                   where=cond, order_by=orderby, sqlparams=sql_param)
        col_list = records[0]
        records = records[1]

        for rec in records:
            entry = dict(zip(col_list, rec))
            if entry[COL_NAME_FILES_FILEPATH] not in fpath_exports:
                fpath_exports[entry[COL_NAME_FILES_FILEPATH]] = []
            if inc_section:
                begints = entry[COL_NAME_COLLMAP_BEGINTIMESTAMP]
                endts = entry[COL_NAME_COLLMAP_ENDTIMESTAMP]
                if begints is not None and endts is not None:
                    fpath_exports[entry[COL_NAME_FILES_FILEPATH]].append([begints, endts, relativets])

        for recfile in fpath_exports:
            bplentry = BplListEntry(recfile)
            for section in fpath_exports[recfile]:
                bplentry.append(section[0], section[1], section[2])
            bplfile.append(bplentry)
        bplfile.write()
        return bplfile

    def import_bpl_to_collection(self, bplfilepath, coll_name, inc_section=False, label=None):
        """
        import BPL file into given Collection Name

        :param bplfilepath: path/filename of bpl file to import
        :type  bplfilepath: str
        :param coll_name:   collection name to link recordings to
        :type  coll_name:   str
        :param inc_section: opt. include defined sections into collection entry
        :type inc_section:  bool
        :param label: opt. checkpoint label
        :type  label: str
        :return: True
        """
        if label:
            raise AdasDBError("Collection Checkpoint can not be changed (label '%s' used as target for import)"
                              % str(label))
        bpl_file = Bpl(bplfilepath)
        bpl_file.read()
        collid = self.get_collection_id(coll_name, label=label)
        for bpl_list_entry in bpl_file.get_bpl_list_entries():
            self.add_bplentry_to_collection(collid, bpl_list_entry, inc_section)

        return True

    def add_bplentry_to_collection(self, collid, bpl_list_entry, inc_section):
        """
        add a single bpl entry to a given collection

        :param collid: db internal collection id
        :type  collid: int
        :param bpl_list_entry: bpl entry with rec file name and sections
        :type  bpl_list_entry: BplListEntry
        :param inc_section:  opt. include defined sections into collection entry
        :type  inc_section:  bool
        """
        measid = str(int(self.get_measurement_id(str(bpl_list_entry))))
        collmap_record = {COL_NAME_COLLMAP_COLLID: collid, COL_NAME_COLLMAP_MEASID: measid,
                          COL_NAME_COLLMAP_ASGNBY: environ["USERNAME"],
                          COL_NAME_COLLMAP_ASGNDATE: self.timestamp_to_date(time())}
        if inc_section and bpl_list_entry.has_sections():
            # get absolute start time stamp, only first element of returned list is used
            file_record = self.get_measurement(measid=measid)
            for section in bpl_list_entry.get_sections():
                start_ts, end_ts, rel = section.sect2list()
                # if the timstamp are not relative then make it relative because db stores sections as relative
                if not rel:
                    start_ts = start_ts - file_record[0][COL_NAME_FILES_BEGINTIMESTAMP]
                    end_ts = end_ts - file_record[0][COL_NAME_FILES_BEGINTIMESTAMP]
                collmap_record[COL_NAME_COLLMAP_BEGINTIMESTAMP] = start_ts
                collmap_record[COL_NAME_COLLMAP_ENDTIMESTAMP] = end_ts
                self.add_collection_map(collmap_record)
        else:
            self.add_collection_map(collmap_record)

    def get_rec_file_name_for_measid(self, measid):
        """
        Returns the filepath for a measid

        :param measid: the measurement id
        :type measid: int
        :return: Returns the corresponding filepath
        :rtype: str
        """
        measid_cond = SQLBinaryExpr(COL_NAME_FILES_MEASID, OP_EQ, measid)
        return self.select_generic_data(select_list=[COL_NAME_FILES_FILEPATH],
                                        table_list=[TABLE_NAME_FILES],
                                        where=measid_cond)[0][COL_NAME_FILES_FILEPATH]

    def _get_measurement_collection_names(self, file_path):  # pylint: disable=C0103
        """
        Get the Collection Names of a measurement.

        :param file_path: The file_path of the measurement.
        :type file_path: str
        :return: Returns the Collection Names to which the measurement is
                assigned, if file is not assigned return empty list.
        :rtype: list
        """
        measid = self.get_measurement_id(file_path)
        collectionnames = []

        tblcoll = TABLE_NAME_COLL
        tblcollmap = TABLE_NAME_COLLMAP
        columns = [SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblcoll), COL_NAME_COLL_NAME), OP_AS, COL_NAME_COLL_NAME)]

        collmapcolljoin = SQLJoinExpr(SQLTableExpr(TABLE_NAME_COLLMAP),
                                      OP_INNER_JOIN,
                                      SQLTableExpr(TABLE_NAME_COLL),
                                      SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblcollmap), COL_NAME_COLLMAP_COLLID),
                                                    OP_EQ, SQLColumnExpr(SQLTableExpr(tblcoll), COL_NAME_COLL_COLLID)))

        cond = SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(tblcollmap), COL_NAME_COLLMAP_MEASID), OP_EQ, ":1")
        entries = self.select_generic_data(columns, [collmapcolljoin], cond, sqlparams={"1": measid})

        if len(entries) >= 1:
            for ent in range(len(entries)):
                collectionnames.append(entries[ent][COL_NAME_COLL_NAME])
        else:
            info("Rec file '" + file_path + "' is not assigned to a collection")

        return collectionnames

    def get_measurement_collection_names(self, file_path, coll_name=None):  # pylint: disable=C0103
        """
        Get list of collection name to which the given rec file path belong
        in the given pre select collection

        :param file_path: The file_path of the measurement.
        :type file_path: str
        :param coll_name: list of collection Name or Parent Collection Name as filter criteria
        :type coll_name: list or str
        :return: List of Collection name to which the given measurement belongs
        :rtype: list
        """
        coll_names = []
        if coll_name is not None:

            if type(coll_name) is list:
                collids = []
                for c_name in coll_name:
                    collids.append(self.get_collection_id(c_name))
            else:
                parent_collid = self.get_collection_id(coll_name)
                collids = self.get_collections(parent_collid, recurse=True)
                collids.append(parent_collid)
            collids = list(set(collids))
            for collid in collids:
                if self.is_measurement_in_collection(collid, measid=None, file_path=file_path):
                    coll_names.append(self.get_collection(collid)[COL_NAME_COLL_NAME])
            return coll_names

        else:
            return self._get_measurement_collection_names(file_path)

    def is_measurement_in_collection(self, collid, measid=None, file_path=None):
        """
        Tells whether the given measurement is in the  collection.
        The function doesnt recursively for the child collections

        :param collid: Collection Id
        :type collid: int
        :param measid: Meaurement ID
        :type measid: int | None
        :param file_path: filepath of recording
        :type file_path: str | None
        :return: return True if meas belongs to collection othersie return False
        :rtype: bool
        """
        if measid is not None or file_path is not None:
            if measid is None:
                measid = self.get_measurement_id(file_path)
            sql_param = {"1": measid, "2": collid}
            cond1 = SQLBinaryExpr(COL_NAME_COLLMAP_MEASID, OP_EQ, ":1")
            cond2 = SQLBinaryExpr(COL_NAME_COLLMAP_COLLID, OP_EQ, ":2")
            cond = SQLBinaryExpr(cond1, OP_AND, cond2)
            entries = self.select_generic_data([SQLBinaryExpr(SQLFuncExpr(EXPR_COUNT, OP_MUL), OP_AS, "COUNT")],
                                               table_list=[TABLE_NAME_COLLMAP], where=cond, sqlparams=sql_param)
            if entries[0]["COUNT"] > 0:
                return True
        return False

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def get_collection_hours_kilometer_for_part_config_version(self, collection_name,  # pylint: disable=C0103,R0914
                                                               version_type, label=None):
        """
        Get hours for Part Configuration version.

        :param collection_name: The name of the collection,
        :type collection_name: str
        :param version_type: HW oder SW version
        :type version_type: str
        :param label: opt. checkpoint label
        :type  label: str
        :return: return list of list with following format
                [[version string, time in us, number of files, kilometer],...]
        :rtype: list
        """
        collection_id = self.get_collection_id(collection_name, label=label)

        rec, sql = self._build_collection_query(collection_id, True, COL_NAME_COLL_COLLID)
        join = SQLTernaryExpr(TABLE_NAME_FILES, OP_INNER_JOIN, TABLE_NAME_COLLMAP, OP_NOP,
                              SQLFuncExpr(OP_USING, COL_NAME_FILES_MEASID))
        cond = SQLBinaryExpr(COL_NAME_COLL_COLLID, OP_IN, sql)
        sql = GenericSQLSelect([COL_NAME_COLLMAP_MEASID], True, [join], cond)
        cond = SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_FILES), COL_NAME_FILES_MEASID),
                             OP_IN, SQLConcatExpr(rec, sql))

        version_time_files_dict = {}
        time_diff = SQLBinaryExpr("NVL(%s, 0)" % (str(SQLColumnExpr(SQLTableExpr(TABLE_NAME_FILES),
                                                                    COL_NAME_FILES_ENDTIMESTAMP))),
                                  OP_SUB,
                                  "NVL(%s, 0)" % (str(SQLColumnExpr(SQLTableExpr(TABLE_NAME_FILES),
                                                                    COL_NAME_FILES_BEGINTIMESTAMP))))
        time_diff = SQLBinaryExpr(time_diff, OP_AS, "DURATION")

        dist_km = SQLColumnExpr(SQLTableExpr(TABLE_NAME_FILES), COL_NAME_FILES_RECDRIVENDIST)
        dist_km = "NVL(%s, 0)" % (str(dist_km))
        dist_km = SQLBinaryExpr(dist_km, OP_AS, COL_NAME_FILES_RECDRIVENDIST)
        select_list = [SQLColumnExpr(SQLTableExpr(TABLE_NAME_PARTCFGS), version_type), dist_km, time_diff]

        tables = []
        join_cond_col1 = SQLColumnExpr(SQLTableExpr(TABLE_NAME_FILES), COL_NAME_FILES_VEHICLECFGID)
        join_cond_col2 = SQLColumnExpr(SQLTableExpr(TABLE_NAME_PARTCFGS), COL_NAME_PARTCFGS_VEHCFGID)
        join_cond = SQLBinaryExpr(join_cond_col1, OP_EQ, join_cond_col2)

        first_join = SQLJoinExpr(SQLTableExpr(TABLE_NAME_FILES), OP_INNER_JOIN,
                                 SQLTableExpr(TABLE_NAME_PARTCFGS), join_cond)
        tables.append(first_join)
        entries = self.select_generic_data(select_list, tables, where=cond)
        for entry in entries:
            if entry[version_type] not in version_time_files_dict:
                version_time_files_dict[entry[version_type]] = [0, 0, 0]

            recdist = entry[COL_NAME_FILES_RECDRIVENDIST]
            version_time_files_dict[entry[version_type]][0] += entry["DURATION"]
            version_time_files_dict[entry[version_type]][1] += 1
            version_time_files_dict[entry[version_type]][2] += recdist if recdist >= 0 else 0

        version_time_files_list = [[ver_type, values[0], values[1], values[2]]
                                   for ver_type, values in version_time_files_dict.iteritems()]
        return version_time_files_list

    def get_collection_hours_kilometer_per_recdate(self, collection_name, label=None):  # pylint: disable=C0103,R0914
        """
        Get hours and kilometer per recording date.

        :param collection_name: The collection name.
        :type collection_name: str
        :param label: opt. checkpoint label
        :type  label: str
        :return: list of tuples where each tuple has forllowing format
                (recording_date, hours, files, kilometer).
        :rtype: list
        """
        recdate_hours_files_list = []
        raw_recdate_hours_files = []

        # Getting the collection ID from the collection name
        collection_id = self.get_collection_id(collection_name, label=label)

        # Getting the MEASID's for collection with subcollections
        coll_measid_list = self.get_collection_measurements(collection_id, True, False)
        if len(coll_measid_list) == 0:
            return recdate_hours_files_list

        recdate_list = []

        for measid in coll_measid_list:
            condition = SQLBinaryExpr(COL_NAME_FILES_MEASID, OP_EQ, measid)
            select_list = [COL_NAME_FILES_MEASID, COL_NAME_FILES_RECTIME, COL_NAME_FILES_BEGINTIMESTAMP,
                           COL_NAME_FILES_ENDTIMESTAMP, COL_NAME_FILES_RECDRIVENDIST]
            order_by_list = [COL_NAME_FILES_RECTIME]
            recdate_list.append(self.select_generic_data(select_list, [TABLE_NAME_FILES],
                                                         where=condition, order_by=order_by_list))

        for first_lst in recdate_list:
            for recdate_idx in first_lst:
                recdate = {COL_NAME_FILES_MEASID: recdate_idx[COL_NAME_FILES_MEASID],
                           COL_NAME_FILES_RECTIME: recdate_idx[COL_NAME_FILES_RECTIME],
                           "Timestamp": (recdate_idx[COL_NAME_FILES_ENDTIMESTAMP] -
                                         recdate_idx[COL_NAME_FILES_BEGINTIMESTAMP]),
                           COL_NAME_FILES_RECDRIVENDIST: recdate_idx[COL_NAME_FILES_RECDRIVENDIST]}
                raw_recdate_hours_files.append(recdate)

        for idx in raw_recdate_hours_files:
            new_entry = True
            for recdate_hours_files in recdate_hours_files_list:
                if recdate_hours_files[0] == datetime.date(idx[COL_NAME_FILES_RECTIME]):
                    recdate_hours_files[1] += idx["Timestamp"]
                    recdate_hours_files[2] += 1
                    if idx[COL_NAME_FILES_RECDRIVENDIST] is not None:
                        recdate_hours_files[3] += idx[COL_NAME_FILES_RECDRIVENDIST]
                    new_entry = False
            if new_entry:
                recdate_hours_files_list.append([datetime.date(idx[COL_NAME_FILES_RECTIME]), idx["Timestamp"],
                                                 1, idx[COL_NAME_FILES_RECDRIVENDIST]])

        return recdate_hours_files_list

    def get_collection_hours_kilometer_per_driver(self, collection_name, label=None):  # pylint: disable=C0103,R0914
        """
        Get the Driver hours and kilometer for the collection

        :param collection_name: The name of the collection.
        :type collection_name: str
        :param label: opt. checkpoint label
        :type  label: str
        :return: return list of list with following info [[driver_id, time in us, number of files, kilometer], .., ..]
        :rtype: list
        """
        raw_driver_hours_files = []
        driver_hours_files_list = []
        # Getting the collection ID from the collection name
        collection_id = self.get_collection_id(collection_name, label=label)

        # Getting the MEASID's for collection with subcollections
        coll_measid_list = self.get_collection_measurements(collection_id, True, False)
        if len(coll_measid_list) == 0:
            return driver_hours_files_list

        driver_list = []

        for measid in coll_measid_list:
            condition = SQLBinaryExpr(COL_NAME_FILES_MEASID, OP_EQ, measid)
            select_list = [COL_NAME_FILES_MEASID,
                           COL_NAME_FILES_BEGINTIMESTAMP,
                           COL_NAME_FILES_ENDTIMESTAMP,
                           COL_NAME_FILES_RECDRIVENDIST]
            driver_list.append(self.select_generic_data(select_list, [TABLE_NAME_FILES], where=condition))

        for first_lst in driver_list:
            for driver_idx in first_lst:
                driver = {COL_NAME_FILES_MEASID: driver_idx[COL_NAME_FILES_MEASID],
                          COL_NAME_FILES_DRIVERID: 0,
                          "Timestamp": (driver_idx[COL_NAME_FILES_ENDTIMESTAMP] -
                                        driver_idx[COL_NAME_FILES_BEGINTIMESTAMP]),
                          COL_NAME_FILES_RECDRIVENDIST: driver_idx[COL_NAME_FILES_RECDRIVENDIST]}
                raw_driver_hours_files.append(driver)

        for idx in raw_driver_hours_files:
            new_entry = True
            for driver_hours_files in driver_hours_files_list:
                if driver_hours_files[0] == idx[COL_NAME_FILES_DRIVERID]:
                    driver_hours_files[1] += idx["Timestamp"]
                    driver_hours_files[2] += 1
                    if idx[COL_NAME_FILES_RECDRIVENDIST] is not None:
                        driver_hours_files[3] += idx[COL_NAME_FILES_RECDRIVENDIST]
                    new_entry = False
            if new_entry:
                driver_hours_files_list.append([idx[COL_NAME_FILES_DRIVERID], idx["Timestamp"], 1,
                                               idx[COL_NAME_FILES_RECDRIVENDIST]])

        # replace driverid with driver name in driver_hours_files
        for idx in driver_hours_files_list:
            if idx[0] is not None:
                idx[0] = self.get_driver_name(idx[0])

        return driver_hours_files_list

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def get_collection_hours_kilometer_per_vehicle(self, collection_name, label=None):  # pylint: disable=C0103,R0914
        """
        Get hours and kilometer per vehicle.

        :param collection_name: The name of the collection.
        :type collection_name: str
        :param label: opt. checkpoint label
        :type  label: str
        :return:  return list of list with following info
                [[vehicle string, time in us,, number of files, kilometer][,..].[..]]
        :rtype: list
        """
        vehicle_time_files_list = []

        collection_id = self.get_collection_id(collection_name, label=label)

        select_list = [SQLColumnExpr(SQLTableExpr(TABLE_NAME_FILES), COL_NAME_FILES_MEASID),
                       SQLColumnExpr(SQLTableExpr(TABLE_NAME_VEHICLES), COL_NAME_VEHICLES_NAME),
                       SQLColumnExpr(SQLTableExpr(TABLE_NAME_FILES), COL_NAME_FILES_BEGINTIMESTAMP),
                       SQLColumnExpr(SQLTableExpr(TABLE_NAME_FILES), COL_NAME_FILES_ENDTIMESTAMP),
                       SQLColumnExpr(SQLTableExpr(TABLE_NAME_FILES), COL_NAME_FILES_RECDRIVENDIST)]

        tables = []
        join_cond_col1 = SQLColumnExpr(SQLTableExpr(TABLE_NAME_FILES), COL_NAME_FILES_VEHICLECFGID)
        join_cond_col2 = SQLColumnExpr(SQLTableExpr(TABLE_NAME_VEHICLECFGS), COL_NAME_VEHICLECFGS_VEHCFGID)
        join_cond = SQLBinaryExpr(join_cond_col1, OP_EQ, join_cond_col2)

        first_join = SQLJoinExpr(SQLTableExpr(TABLE_NAME_FILES), OP_INNER_JOIN,
                                 SQLTableExpr(TABLE_NAME_VEHICLECFGS), join_cond)

        join_cond_col1_3 = SQLColumnExpr(SQLTableExpr(TABLE_NAME_VEHICLECFGS), COL_NAME_VEHICLECFGS_VEHICLEID)
        join_cond_col2_3 = SQLColumnExpr(SQLTableExpr(TABLE_NAME_VEHICLES), COL_NAME_VEHICLES_VEHICLEID)
        join_cond_3 = SQLBinaryExpr(join_cond_col1_3, OP_EQ, join_cond_col2_3)

        tables.append(SQLJoinExpr(SQLTableExpr(first_join), OP_INNER_JOIN,
                                  SQLTableExpr(TABLE_NAME_VEHICLES), join_cond_3))

        # Get the measid's for the collection (with subcollections)
        coll_measid_list = self.get_collection_measurements(collection_id, True, False)
        if len(coll_measid_list) == 0:
            return vehicle_time_files_list

        query = ','.join(str(n) for n in coll_measid_list)
        cond = SQLBinaryExpr(COL_NAME_FILES_MEASID, OP_IN, "%s" % "(" + query + ")")

        try:
            entries = self.select_generic_data(select_list, tables, where=cond)

            # Check for measurement duplicates.
            measurements = []

            for entry in entries:
                if entry[COL_NAME_FILES_MEASID] in measurements:
                    continue
                new_entry = True
                for vehicle_time_files in vehicle_time_files_list:
                    if vehicle_time_files[0] == entry[COL_NAME_VEHICLES_NAME]:
                        vehicle_time_files[1] += (entry[COL_NAME_FILES_ENDTIMESTAMP] -
                                                  entry[COL_NAME_FILES_BEGINTIMESTAMP])
                        vehicle_time_files[2] += 1
                        if entry[COL_NAME_FILES_RECDRIVENDIST] is not None:
                            vehicle_time_files[3] += entry[COL_NAME_FILES_RECDRIVENDIST]
                        measurements.append(entry[COL_NAME_FILES_MEASID])
                        new_entry = False
                if new_entry:
                    time_ = (entry[COL_NAME_FILES_ENDTIMESTAMP] - entry[COL_NAME_FILES_BEGINTIMESTAMP])
                    vehicle_time_files_list.append([entry[COL_NAME_VEHICLES_NAME], time_,
                                                    1, entry[COL_NAME_FILES_RECDRIVENDIST]])
                    measurements.append(entry[COL_NAME_FILES_MEASID])

        except:
            pass

        return vehicle_time_files_list

    def get_collection_filesize(self, collid, recurse=False, group_by=None):
        """
        Filesize in GB for recordings in collection

        :param collid: collection id. if not collection provided then whole catalog i.e. all files
        :type collid: int
        :param recurse: flag to recusrively include sub collection and shared collections
        :type recurse: boolean
        :param group_by: group by column list e.g. ARCHIVED, PID or any column in CAT_FILES
        :type group_by: list
        :return: if group_by is None return total Filesize(GB) for the collection otherwise list of dictionary
                contain Filesize (GB) for each value of the columns given in group_by
        :rtype: dict | list
        """
        col_sum_fsize = SQLBinaryExpr(SQLFuncExpr("SUM", SQLBinaryExpr(COL_NAME_FILES_FILESIZE, OP_DIV,
                                                                       "(1073741824)")),  # 1024^3
                                      OP_AS, COL_NAME_FILES_FILESIZE)

        entries = self._get_collection_stats(collid, [col_sum_fsize], recurse, group_by)
        return entries[0] if group_by is None else entries

    def get_collection_kilometer(self, collection_name=None, recurse=False, group_by=None,  # pylint: disable=R0914
                                 label=None):
        """
        Get driven distance in kilometers for the collection

        If searched recursively through all child collections
        measurement files are only added once, even if they are linked in different child collections.

        :param collection_name: The name of the collection, if None sum of driven distance for all files.
        :type collection_name: str
        :param recurse: flag to recusrively include sub collection and shared collections
        :type recurse: boolean
        :param group_by: driven distance statistic group by column list e.g. ARCHIVED, PID or any column in CAT_FILES
        :type group_by: list
        :param label: opt. checkpoint label
        :type  label: str
        :return: if group_by is None return total km for the collection otherwise list of dictionary contain kilometer
                for each value of the columns given in group_by
        :rtype: dict dict | list
        """
        if collection_name is not None:
            collid = self.get_collection_id(collection_name, label=label)
        else:
            collid = None

        sql_param = {}
        if collid is not None:
            sql_param[str(len(sql_param) + 1)] = collid

        # new sql query setup:
        # old stuff cont:
        km_cond = "NVL({}, 0) > 0".format(COL_NAME_FILES_RECDRIVENDIST)
        rewith = ''
        if collid is None:
            cond = km_cond
        else:
            # setup select, join and condition
            if recurse:
                cond, rewith = self._get_shared_collection_tree_query()
            else:
                cond = "{cat_collectionmap} = :{i}".format(cat_collectionmap=COL_NAME_COLLMAP_COLLID,
                                                           i=len(sql_param))

            cond += ' AND {}'.format(km_cond)

        sql_names = {'recdrivendist': COL_NAME_FILES_RECDRIVENDIST,
                     'groupby': (', ' + ', '.join(group_by)) if group_by else '',
                     'measid': COL_NAME_FILES_MEASID,
                     'collid': COL_NAME_COLL_COLLID,
                     'cat_collections': TABLE_NAME_COLL,
                     'cat_collectionmap': TABLE_NAME_COLLMAP,
                     'cat_files': TABLE_NAME_FILES,
                     'cond': str(cond)}
        sql_stmt = 'SELECT SUM(DIST_SUM) AS {recdrivendist} {groupby} FROM (' \
                   '  SELECT DISTINCT {measid}, NVL({recdrivendist}, 0) AS DIST_SUM {groupby}' \
                   '  FROM ({cat_collections} INNER JOIN {cat_collectionmap} cmap  USING({collid}))' \
                   '    INNER JOIN {cat_files} USING({measid})' \
                   '  WHERE {cond})'.format(**sql_names)

        if group_by:
            # append GROUP BY statement
            sql_stmt += 'GROUP BY {}'.format(', '.join(group_by))
        if rewith:
            # insert WITH clause at beginning
            sql_stmt = 'WITH {} {}'.format(rewith, sql_stmt)
        sql_param['incDesc'] = True

        entries = self.execute(sql_stmt, **sql_param)

        if not entries:
            if group_by:
                for col in group_by:
                    entries = {COL_NAME_FILES_RECDRIVENDIST: 0}
                    entries[col] = None
            else:
                entries = [{COL_NAME_FILES_RECDRIVENDIST: 0}]

        return entries[0] if group_by is None else entries

    @staticmethod
    def _get_collections_tree_query(sql_value, sql_oper=OP_EQ):
        """
        Get shared recursive query that to generatee collection tree

        :param sql_value: SQL variable name for binding
        :type sql_value: str
        :param sql_oper: SQL variable name for binding
        :type sql_oper: str
        :return: sql recursive query
        :rtype: `SQLBinaryExpr`,`GenericSQLSelect`
        """
        col_list = [COL_NAME_COLL_PARENTID, COL_NAME_COLL_COLLID, COL_NAME_COLL_NAME, COL_NAME_COLL_COLLCOMMENT,
                    COL_NAME_COLL_PRID, COL_NAME_COLL_IS_ACTIVE]
        catcoll_tbl_alias = "c"
        cat_coll_tbl = SQLTableExpr(TABLE_NAME_COLL, catcoll_tbl_alias)
        col_list_aliased = [SQLColumnExpr(catcoll_tbl_alias, COL_NAME_COLL_PARENTID),
                            SQLColumnExpr(catcoll_tbl_alias, COL_NAME_COLL_COLLID),
                            SQLColumnExpr(catcoll_tbl_alias, COL_NAME_COLL_NAME),
                            SQLColumnExpr(catcoll_tbl_alias, COL_NAME_COLL_COLLCOMMENT),
                            SQLColumnExpr(catcoll_tbl_alias, COL_NAME_COLL_PRID),
                            SQLColumnExpr(catcoll_tbl_alias, COL_NAME_COLL_IS_ACTIVE)]

        start = GenericSQLSelect(col_list, False, [cat_coll_tbl],
                                 SQLBinaryExpr(COL_NAME_COLL_COLLID, sql_oper, sql_value))
        join = SQLJoinExpr(cat_coll_tbl, OP_INNER_JOIN, SQLTableExpr(GEN_RECUR_NAME, "r"),
                           SQLBinaryExpr(SQLColumnExpr(catcoll_tbl_alias, COL_NAME_COLL_PARENTID), OP_EQ,
                                         SQLColumnExpr("r", COL_NAME_COLL_COLLID)))
        stop = GenericSQLSelect(col_list_aliased, False, [join])
        outer = GenericSQLSelect(col_list, False, [GEN_RECUR_NAME])
        wexp = str(SQLConcatExpr(EXPR_WITH, SQLFuncExpr(GEN_RECUR_NAME, str(col_list)[1:-1].replace("'", ""))))
        wexp = SQLBinaryExpr(wexp, OP_AS, SQLConcatExpr(start, OP_UNION_ALL, stop))
        return wexp, outer

    def _get_shared_collection_tree_query(self):
        """
        Get shared recursive query used to generate collection tree

        retruns WHILE parameters to put at beginning of query (like a declaration)
        and the condition to use in WHERE condition.

        uses ``:1`` substituion for collection id: ``WHERE COLLID=:1`` so first sql parameterof the query
        needs to be the collection id of the selected collection

        :return: sql recursive query, parameter str of WITH declaration
        :rtype: str, str
        """

        # condition using the recursions
        cond = 'MEASID IN (SELECT DISTINCT MEASID FROM CAT_COLLECTIONMAP INNER JOIN RECOLL USING(COLLID))'
        # recursive WITH declaration, put on beginning of query:
        if self.sub_scheme_version < CAT_SHARECOLL_VERSION:
            rwith = 'COLLS(PARENTID, COLLID) AS (' \
                    '  SELECT PARENTID, COLLID FROM CAT_COLLECTIONS),'
        else:
            rwith = 'COLLS(PARENTID, COLLID) AS (' \
                    '  SELECT PARENTID, COLLID FROM CAT_COLLECTIONS' \
                    '  UNION ALL' \
                    '  SELECT  PARENT_COLLID PARENTID, CHILD_COLLID COLLID FROM CAT_SHAREDCOLLECTIONMAP' \
                    '),'

        rwith += 'RECOLL(PARENTID, COLLID) AS (' \
                 '  SELECT PARENTID, COLLID FROM COLLS c' \
                 '  WHERE COLLID = :1' \
                 '  UNION ALL' \
                 '  SELECT c.PARENTID, c.COLLID FROM COLLS c' \
                 '  INNER JOIN RECOLL r ON (c.PARENTID = r.COLLID)' \
                 ')'
        return cond, rwith

    def get_shared_collid(self, parent_collid):
        """
        get list of all shared collection ids for given parent collection Id

        :param parent_collid: parent collection
        :type parent_collid: list or int
        :return: list of child collection Id
        :rtype: list
        """
        cond = SQLBinaryExpr(COL_NANE_SHARECOLL_PARENT_COLLID, OP_EQ, ":1")
        records = self.select_generic_data_compact([COL_NANE_SHARECOLL_CHILD_COLLID],
                                                   [TABLE_NAME_CAT_SHAREDCOLLECTIONMAP],
                                                   where=cond, sqlparams={"1": parent_collid})[1]
        return [rec[0] for rec in records]

    def add_shared_collection(self, parent_collid, child_collid, prid=None):
        """
        Add shared collection link. The oracle database may throw exception if the collection shared is creating
        cyclic loop

        :param parent_collid: parent collection id
        :type parent_collid: int
        :param child_collid: child collection id
        :type child_collid: int
        :param prid: priority Id
        :type prid: int
        :return: primary key value of sharedmapid for the newly inserted row
        :rtype: int
        """

        if self.sub_scheme_version < CAT_SHARECOLL_VERSION:
            return []
        record_dict = {COL_NANE_SHARECOLL_PARENT_COLLID: parent_collid,
                       COL_NANE_SHARECOLL_CHILD_COLLID: child_collid,
                       COL_NANE_SHARECOLL_PRID: prid}
        sharedmapid = self.add_generic_data(record_dict, TABLE_NAME_CAT_SHAREDCOLLECTIONMAP,
                                            SQLUnaryExpr(OP_RETURNING, COL_NANE_SHARECOLL_SAHREDMAPID))
        return sharedmapid

    def delete_shared_collection(self, parent_collid, child_collid):
        """
        Delete shared link

        :param parent_collid: parent collection id
        :type parent_collid: int
        :param child_collid: child collection id
        :type child_collid: int
        """
        if self.sub_scheme_version < CAT_SHARECOLL_VERSION:
            return
        cond = SQLBinaryExpr(COL_NANE_SHARECOLL_PARENT_COLLID, OP_EQ, parent_collid)
        cond = SQLBinaryExpr(SQLBinaryExpr(COL_NANE_SHARECOLL_CHILD_COLLID, OP_EQ, child_collid), OP_AND, cond)
        self.delete_generic_data(TABLE_NAME_CAT_SHAREDCOLLECTIONMAP, where=cond)

    def get_collection_tree(self, *args, **kwargs):  # pylint: disable=R0914
        """
        Get collection tree starting from the specified collid as root_collid.

        The list is sorted by hiarchical level
        i.e. root collection corresponding to paramter root_collid will be the first entry in the list

        :keyword root_collid: The collection as the starting collection as root of tree or sub-tree
        :type    root_collid: int
        :keyword incl_shared: flag to include or exclude the shared collection in the tree. This will recursively
                              populate shared collection till the max depth limit reached or
                              all the shared collection tree are populated
        :type    incl_shared: bool
        :keyword col_list:    list of column names to return
        :type    col_list:    list of str
        :keyword depth_size:  number of recursions to run in one query, default=100
        :type    depth_size:  int
        :return: list of tuple as all set of records. selected columns,
                 the order of tuple will be (shared_flag, parent_id, collid, coll_name, comment, prid, is_active)
        :rtype:  list
        """
        opt = arg_trans(['root_collid', ['incl_shared', True], ['col_list', None],
                         ['depth_size', 100], 'label', None], *args, **kwargs)

        root_collid = opt[0]
        incl_shared = opt[1]
        col_list = opt[2]
        depth_size = opt[3]
        label = opt[4]
        # Disable include_shared collection if the feature not available in database
        if self.sub_scheme_version < CAT_SHARECOLL_VERSION:
            incl_shared = False
        max_depth = 100
        if depth_size > max_depth:
            raise AdasDBError("Leave the depth_size as default value %d" % max_depth)
        if depth_size == -1:
            raise AdasDBError("Max recursion depth has been reacheded")

        if col_list is None:
            col_list = [SHARED_FLAG, COL_NAME_COLL_PARENTID, COL_NAME_COLL_COLLID, COL_NAME_COLL_NAME,
                        COL_NAME_COLL_COLLCOMMENT, COL_NAME_COLL_PRID, COL_NAME_COLL_IS_ACTIVE]

        shared_flag_idx = None
        if depth_size < max_depth:
            if SHARED_FLAG in col_list:
                shared_flag_idx = col_list.index(SHARED_FLAG)
                col_list[shared_flag_idx] = SQLBinaryExpr(SHARED_COLL, OP_AS, SHARED_FLAG)

            master_sql = GenericSQLSelect(col_list, False, [GEN_RECUR_NAME])
        else:
            if SHARED_FLAG in col_list:
                shared_flag_idx = col_list.index(SHARED_FLAG)
                col_list[shared_flag_idx] = SQLBinaryExpr(N0T_SHARED_COLL, OP_AS, SHARED_FLAG)
            master_sql = GenericSQLSelect(col_list, False, [GEN_RECUR_NAME])
        recurs, _ = self._get_collections_tree_query(":1")

        sql_param = {"1": root_collid}
        if self.sub_scheme_version >= CAT_CHECKPOINT_VERSION:
            if label is None or label == "":
                cp_cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                    COL_NAME_COLL_CP_LABEL), OP_EQ, SQLLiteral(""))
                cp_cond = SQLBinaryExpr(cp_cond, OP_OR, SQLBinaryExpr(COL_NAME_COLL_CP_LABEL, OP_IS, SQLNull()))
            else:
                sql_param[str(len(sql_param) + 1)] = label.lower()
                cp_cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                    COL_NAME_COLL_CP_LABEL), OP_EQ, ":%d" % (len(sql_param)))

        try:
            master_coll_tree = self.execute(str(SQLConcatExpr(recurs, master_sql)),  # pylint: disable=W0142
                                            ** sql_param)
        except Exception as exp:
            raise AdasDBError(str(exp) + "\nRecursive Query gone into infinite loopg for collection %s"
                              % str(sql_param))
        if incl_shared:
            master_sql = GenericSQLSelect([COL_NAME_COLL_COLLID], False, [GEN_RECUR_NAME])
            shared_coll_cond = SQLBinaryExpr(COL_NANE_SHARECOLL_PARENT_COLLID, OP_IN,
                                             "(%s)" % str(SQLConcatExpr(recurs, master_sql)))

            sharecoll_sql = GenericSQLSelect([COL_NANE_SHARECOLL_PARENT_COLLID, COL_NANE_SHARECOLL_CHILD_COLLID],
                                             False, [TABLE_NAME_CAT_SHAREDCOLLECTIONMAP], shared_coll_cond)
            sharedcolls = self.execute(str(sharecoll_sql), **sql_param)  # pylint: disable=W0142
            for shared_coll in sharedcolls:

                if shared_flag_idx is not None:
                    col_list[shared_flag_idx] = SHARED_FLAG
                shared_coll_tree, col_list = self.get_collection_tree(shared_coll[1], depth_size=depth_size - 1,
                                                                      incl_shared=incl_shared, col_list=col_list)

                if len(shared_coll_tree) > 0:
                    first_rec = list(shared_coll_tree[0])
                    if COL_NAME_COLL_PARENTID in col_list:
                        first_rec[col_list.index(COL_NAME_COLL_PARENTID)] = shared_coll[0]
                    shared_coll_tree[0] = tuple(first_rec)
                master_coll_tree += shared_coll_tree
            if shared_flag_idx is not None:
                col_list[shared_flag_idx] = SHARED_FLAG
            return master_coll_tree, col_list
        else:
            if shared_flag_idx is not None:
                col_list[shared_flag_idx] = SHARED_FLAG
            return master_coll_tree, col_list

    def get_collection_time(self, collection_name=None, label=None):
        """
        Get collection Diving duration in Microsecond.

        :param collection_name: The name of the collection, if None sum of all files.
        :type collection_name: str
        :param label: opt. checkpoint label
        :type  label: str
        :return: the total time over all the files or None if collection is empty
        :rtype: dict
        """
        record = {}
        cond = []
        if collection_name is not None:
            typejoin = SQLJoinExpr(SQLTableExpr(TABLE_NAME_FILES),
                                   OP_INNER_JOIN,
                                   SQLTableExpr(TABLE_NAME_COLLMAP),
                                   SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_COLLMAP),
                                                               COL_NAME_COLLMAP_MEASID),
                                                 OP_EQ,
                                                 SQLColumnExpr(SQLTableExpr(TABLE_NAME_FILES), COL_NAME_FILES_MEASID)))

            typejoin = SQLJoinExpr(SQLTableExpr(typejoin),
                                   OP_INNER_JOIN,
                                   SQLTableExpr(TABLE_NAME_COLL),
                                   SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_COLL), COL_NAME_COLL_COLLID),
                                                 OP_EQ,
                                                 SQLColumnExpr(SQLTableExpr(TABLE_NAME_COLLMAP),
                                                               COL_NAME_COLLMAP_COLLID)))

            cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                             SQLColumnExpr(SQLTableExpr(TABLE_NAME_COLL),
                                                           COL_NAME_COLL_NAME)),
                                 OP_EQ,
                                 SQLLiteral(collection_name.lower()))

            if self.sub_scheme_version >= CAT_CHECKPOINT_VERSION:
                if label is None or label == "":
                    cp_cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                        SQLColumnExpr(SQLTableExpr(TABLE_NAME_COLL),
                                                                      COL_NAME_COLL_CP_LABEL)),
                                            OP_EQ, SQLLiteral(""))
                    cp_cond = SQLBinaryExpr(cp_cond, OP_OR, SQLBinaryExpr(COL_NAME_COLL_CP_LABEL, OP_IS, SQLNull()))
                else:
                    cp_cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                        SQLColumnExpr(SQLTableExpr(TABLE_NAME_COLL),
                                                                      COL_NAME_COLL_CP_LABEL)),
                                            OP_EQ, SQLLiteral(label.lower()))
                cond = SQLBinaryExpr(cond, OP_AND, cp_cond)

        delta = SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_FILES), COL_NAME_FILES_ENDTIMESTAMP),
                              OP_SUB,
                              SQLColumnExpr(SQLTableExpr(TABLE_NAME_FILES), COL_NAME_FILES_BEGINTIMESTAMP))
        select_list = [SQLBinaryExpr(SQLFuncExpr("SUM", delta), OP_AS, "TOTAL")]

        try:
            entries = self.select_generic_data(select_list, [typejoin], where=cond)
            record = entries[0]["TOTAL"]
        except:
            pass

        # done
        return record

    def add_collection_log(self, record):
        """
        Add collection log entry

        :param record: dictionary record
        :type record: dict
        :return: log_id value of the newly inserted record
        :rtype: Integer
        """
        return self.add_generic_data(record, TABLE_NAME_CAT_COLLECTION_LOG,
                                     SQLUnaryExpr(OP_RETURNING, COL_NAME_COLLOG_LOG_ID))

    def get_collection_log(self, coll_name, action=None, start_date=None, end_date=None,
                           action_by=None, order_by=None):
        """
        Get Collection log

        :param coll_name: collection name
        :type coll_name:
        :param action: action string e.g. Deleted, Renamed
        :type action: string
        :param start_date: start date time default none means that it is not included in sql condition
        :type start_date: datetime
        :param end_date: end date time default none means that it is not included in sql condition
        :type end_date: datetime
        :param action_by: windows loginname who performed action
        :type action_by: str
        :param order_by: sorted by columns default logid
        :type order_by: list
        """
        if order_by is None:
            order_by = [COL_NAME_COLLOG_LOG_ID]

        sql_param = {}
        sql_param[str(len(sql_param) + 1)] = coll_name
        cond = SQLBinaryExpr(COL_NAME_COLLOG_COLL_NAME, OP_EQ, ":%d" % (len(sql_param)))

        if action is not None:
            sql_param[str(len(sql_param) + 1)] = action
            cond = SQLBinaryExpr(cond, OP_AND,
                                 SQLBinaryExpr(COL_NAME_COLLOG_ACTION, OP_EQ, ":%d" % (len(sql_param))))

        if action_by is not None:
            sql_param[str(len(sql_param) + 1)] = action_by
            cond = SQLBinaryExpr(cond, OP_AND,
                                 SQLBinaryExpr(COL_NAME_COLLOG_ACTIONBY, OP_EQ, ":%d" % (len(sql_param))))

        if start_date is not None:
            sql_param[str(len(sql_param) + 1)] = start_date
            cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COL_NAME_COLLOG_ACTION_DATE, OP_GEQ,
                                                             ":%d" % (len(sql_param))))
        if end_date is not None:
            sql_param[str(len(sql_param) + 1)] = end_date
            cond = SQLBinaryExpr(cond, OP_AND, SQLBinaryExpr(COL_NAME_COLLOG_ACTION_DATE, OP_LEQ,
                                                             ":%d" % (len(sql_param))))

        return self.select_generic_data(table_list=[TABLE_NAME_CAT_COLLECTION_LOG],
                                        where=cond, order_by=order_by, sqlparams=sql_param)

    def add_collection_log_details(self, log_id, measids):
        """
        Add log details i.e. list of recording involved in the log activity

        :param log_id: log Id foreign key reference log_id from collection_log table
        :type  log_id: Integer
        :param measids: list of measurement Ids
        :type  measids: list
        :return: None
        :rtype:  None
        """
        col_names = [COL_NAME_COLLDET_LOG_ID, COL_NAME_COLLDET_MEASID]
        values = [tuple([log_id, measid]) for measid in measids]
        self.add_generic_compact_prepared(col_names, values, TABLE_NAME_CAT_COLLECTION_LOGDETAILS)

    def get_collection_log_details(self, log_id):
        """
        Get details of collection log activity

        :param log_id: Log id corresponding to action
        :type  log_id: integer
        :return: details containing filepath, filename and measurement id of the recording
        :rtype:  list
        """

        col_logdet_logid = SQLColumnExpr(SQLTableExpr(TABLE_NAME_CAT_COLLECTION_LOGDETAILS),
                                         COL_NAME_COLLDET_LOG_ID)
        col_logdet_measid = SQLColumnExpr(SQLTableExpr(TABLE_NAME_CAT_COLLECTION_LOGDETAILS),
                                          COL_NAME_COLLDET_MEASID)

        col_cf_measid = SQLColumnExpr(SQLTableExpr(TABLE_NAME_FILES), COL_NAME_FILES_MEASID)
        col_recfileid = SQLColumnExpr(SQLTableExpr(TABLE_NAME_FILES), COL_NAME_FILES_RECFILEID)
        col_filepath = SQLColumnExpr(SQLTableExpr(TABLE_NAME_FILES), COL_NAME_FILES_FILEPATH)

        join_1 = SQLJoinExpr(SQLTableExpr(TABLE_NAME_FILES),
                             OP_INNER_JOIN,
                             SQLTableExpr(TABLE_NAME_CAT_COLLECTION_LOGDETAILS),
                             SQLBinaryExpr(col_logdet_measid, OP_EQ, col_cf_measid))

        columns = [SQLBinaryExpr(col_logdet_logid, OP_AS, COL_NAME_COLLDET_LOG_ID),
                   SQLBinaryExpr(col_cf_measid, OP_AS, COL_NAME_FILES_MEASID),
                   SQLBinaryExpr(col_recfileid, OP_AS, COL_NAME_FILES_RECFILEID),
                   SQLBinaryExpr(col_filepath, OP_AS, COL_NAME_FILES_FILEPATH)]
        sql_param = {"1": log_id}
        cond = SQLBinaryExpr(col_logdet_logid, OP_EQ, ":%d" % (len(sql_param)))
        return self.select_generic_data(columns, table_list=[join_1],
                                        where=cond, sqlparams=sql_param)

    # ====================================================================
    # Handling of keyword data
    # ====================================================================

    def add_keyword(self, keyword):
        """
        Add keyword state to database.

        :param keyword: The keyword record.
        :type  keyword: str
        :return: Returns the keyword ID.
        :rtype:  int
        """
        parentid_expr = SQLNull()
        parentid_op = OP_IS
        if keyword[COL_NAME_KW_PARENTID] is not None:
            parentid_expr = SQLLiteral(keyword[COL_NAME_KW_PARENTID])
            parentid_op = OP_EQ
        kw_cond = SQLBinaryExpr(SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                          COL_NAME_KW_NAME), OP_EQ,
                                              SQLLiteral(keyword[COL_NAME_KW_NAME].lower())),
                                OP_AND, SQLBinaryExpr(COL_NAME_KW_PARENTID, parentid_op, parentid_expr))

        entries = self.select_generic_data(table_list=[TABLE_NAME_KW], where=kw_cond)
        if len(entries) <= 0:
            if self.sub_scheme_version < CAT_ACTIVE_VERSION:
                kwid = self._get_next_id(TABLE_NAME_KW, COL_NAME_KW_KWID)
                keyword[COL_NAME_KW_KWID] = kwid
                self.add_generic_data(keyword, TABLE_NAME_KW)
            else:
                entries = self.select_generic_data(table_list=[TABLE_NAME_KW], where=kw_cond)
                kwid = entries[0][COL_NAME_KW_KWID]
                self.add_generic_data(keyword, TABLE_NAME_KW)
            return kwid
        else:
            tmp = "Keyword '%s' " % keyword[COL_NAME_KW_NAME]
            tmp += "exists already in the catalog for this parent."
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError(tmp)
            else:
                warn(tmp)
                if len(entries) == 1:
                    return entries[0][COL_NAME_KW_KWID]
                elif len(entries) > 1:
                    tmp = "Keyword name '%s' " % (keyword[COL_NAME_KW_NAME])
                    tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
                    raise AdasDBError(tmp)

    def update_keywords(self, keyword, where=None):
        """
        Update existing keyword records.

        :param keyword: dictionary of record with update values.
        :type  keyword: dict
        :param where: The condition to be fulfilled by the keywords to the updated.
        :type  where: SQLBinaryExpression
        :return: Returns the number of affected keywords.
        :rtype: int
        """
        rowcount = 0
        if keyword is not None:
            self.update_generic_data(keyword, TABLE_NAME_KW, where)
        # done
        return rowcount

    def add_keyword_map(self, kwmap):
        """
        Add keyword mapping to database.

        :param kwmap: The keyword mapping record.
        :type kwmap: dict
        :return: Returns the keyword map ID.
        :rtype: int
        """
        kw_cond = SQLBinaryExpr(SQLBinaryExpr(COL_NAME_KWMAP_KWID, OP_EQ, kwmap[COL_NAME_KWMAP_KWID]),
                                OP_AND,
                                SQLBinaryExpr(COL_NAME_KWMAP_MEASID, OP_EQ, kwmap[COL_NAME_KWMAP_MEASID]))
        entries = self.select_generic_data(table_list=[TABLE_NAME_KWMAP], where=kw_cond)
        if len(entries) <= 0:
            if self.sub_scheme_version < CAT_ACTIVE_VERSION:
                kwmapid = self._get_next_id(TABLE_NAME_KWMAP, COL_NAME_KWMAP_KWMAPID)
                kwmap[COL_NAME_KWMAP_KWMAPID] = kwmapid
                self.add_generic_data(kwmap, TABLE_NAME_KWMAP)
            else:
                self.add_generic_data(kwmap, TABLE_NAME_KWMAP)
                entries = self.select_generic_data(table_list=[TABLE_NAME_KWMAP], where=kw_cond)
                kwmapid = entries[0][COL_NAME_KWMAP_KWMAPID]
            return kwmapid
        else:
            tmp = "Keyword '%s' " % (kwmap[COL_NAME_KWMAP_KWID])
            tmp += "is already assigned to file "
            tmp += "'%s'." % (kwmap[COL_NAME_KWMAP_MEASID])
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError(tmp)
            else:
                warn(tmp)
                if len(entries) == 1:
                    return entries[0][COL_NAME_KWMAP_KWMAPID]
                elif len(entries) > 1:
                    tmp = "Keyword mapping of file '%s' " % (kwmap[COL_NAME_KWMAP_MEASID])
                    tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
                    raise AdasDBError(tmp)

    def get_keyword_id(self, kw_name):
        """
        Find a keyword Id with a given name.

        :param kw_name: The keyword name.
        :type kw_name: str
        :return: Returns the keyword ID or None if not exists.
        :rtype: int
        """

        kwid = None
        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER], COL_NAME_KW_NAME),
                             OP_EQ, SQLLiteral(kw_name.lower()))
        entries = self.select_generic_data(table_list=[TABLE_NAME_KW], where=cond)
        if len(entries) == 1:
            kwid = entries[0][COL_NAME_KW_KWID]

        # done
        return kwid

    def get_keyword_name(self, kwid):
        """
        Get the name of a keyword for given.

        :param kwid: The keyword ID.
        :type kwid: int
        :return: Returns the keyword name or None if not exists.
        :rtype: str
        """
        kw_name = None
        if kwid is not None:
            cond = SQLBinaryExpr(COL_NAME_KW_KWID, OP_EQ, kwid)
            entries = self.select_generic_data(select_list=[COL_NAME_KW_NAME],
                                               table_list=[TABLE_NAME_KW], where=cond)
            if len(entries) == 1:
                kw_name = entries[0][COL_NAME_KW_NAME]

        return kw_name

    # ====================================================================
    # Handling of location data
    # ====================================================================

    @staticmethod
    @deprecated()
    def add_country(country):  # pylint: disable=W0613
        """deprecated
        """
        raise AdasDBError("tables dropped")

    @staticmethod
    @deprecated()
    def update_countries(country, where=None):  # pylint: disable=W0613
        """deprecated
        """
        raise AdasDBError("tables dropped")

    @staticmethod
    @deprecated()
    def get_country_id(country):  # pylint: disable=W0613
        """deprecated
        """
        raise AdasDBError("tables dropped")

    @staticmethod
    @deprecated()
    def get_country_name(cntryid):  # pylint: disable=W0613
        """deprecated
        """
        raise AdasDBError("tables dropped")

    @staticmethod
    @deprecated()
    def add_location(location):  # pylint: disable=W0613
        """deprecated
        """
        raise AdasDBError("tables dropped")

    @staticmethod
    @deprecated()
    def get_location_id(location):  # pylint: disable=W0613
        """deprecated
        """
        raise AdasDBError("tables dropped")

    @staticmethod
    @deprecated()
    def update_locations(location, where=None):  # pylint: disable=W0613
        """deprecated
        """
        raise AdasDBError("tables dropped")

    @staticmethod
    @deprecated()
    def add_location_info(location):  # pylint: disable=W0613
        """deprecated
        """
        raise AdasDBError("tables dropped")

    @staticmethod
    @deprecated()
    def get_location_info(locinfoid):  # pylint: disable=W0613
        """deprecated
        """
        raise AdasDBError("tables dropped")

    @staticmethod
    @deprecated()
    def get_location_info_ids(measid, location):  # pylint: disable=W0613
        """deprecated
        """
        raise AdasDBError("tables dropped")

    @staticmethod
    @deprecated()
    def get_location_info_idat_rel_time(measid, location, reltime):  # pylint: disable=W0613
        """deprecated
        """
        raise AdasDBError("tables dropped")

    @staticmethod
    @deprecated()
    def update_locations_info(location, where=None):  # pylint: disable=W0613
        """deprecated
        """
        raise AdasDBError("tables dropped")

    # ====================================================================
    # Handling of vehicle configuration data
    # ====================================================================

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def add_vehicle(self, vehicle):
        """
        Add new vehicle to database.

        :param vehicle: The vehicle record.
        :type vehicle: dict
        :return: Returns the vehicle ID.
        :rtype: int
        """
        veh_cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                             COL_NAME_VEHICLES_NAME),
                                 OP_EQ, SQLLiteral(vehicle[COL_NAME_VEHICLES_NAME].lower()))
        entries = self.select_generic_data(table_list=[TABLE_NAME_VEHICLES], where=veh_cond)
        if len(entries) <= 0:
            if self.sub_scheme_version < CAT_ACTIVE_VERSION:
                vehid = self._get_next_id(TABLE_NAME_VEHICLES, COL_NAME_VEHICLES_VEHICLEID)
                vehicle[COL_NAME_VEHICLES_VEHICLEID] = vehid
                self.add_generic_data(vehicle, TABLE_NAME_VEHICLES)
            else:
                self.add_generic_data(vehicle, TABLE_NAME_VEHICLES)
                entries = self.select_generic_data(table_list=[TABLE_NAME_VEHICLES], where=veh_cond)
                vehid = entries[0][COL_NAME_VEHICLES_VEHICLEID]
            return vehid
        else:
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError("Vehicle '%s' exists already in the catalog." % vehicle[COL_NAME_VEHICLES_NAME])
            else:
                warn("Vehicle '" + vehicle[COL_NAME_VEHICLES_VEHICLEID] + "' already exists in the catalog.")
                if len(entries) == 1:
                    return entries[0][COL_NAME_VEHICLES_VEHICLEID]
                elif len(entries) > 1:
                    tmp = "Vehicle '%s' " % (vehicle[COL_NAME_VEHICLES_NAME])
                    tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
                    raise AdasDBError(tmp)

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def update_vehicles(self, vehicle, where=None):
        """
        Update existing vehicle records.

        :param vehicle: The vehicle record update.
        :type vehicle: dict
        :param where: The condition to be fulfilled by the vehicles to the updated.
        :type where: SQLBinaryExpression
        :return: Returns the number of affected vehicles.
        :rtype: int
        """
        rowcount = 0
        if vehicle is not None:
            self.update_generic_data(vehicle, TABLE_NAME_VEHICLES, where)
        # done
        return rowcount

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def get_vehicle_id(self, veh_name):
        """
        Get a vehicle ID for a vehicle name

        :param veh_name: The vehicle name to be resolved.
        :type veh_name: str
        :return: Returns the ID for the vehicle or None if not exists.
        :rtype: int
        """
        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                         COL_NAME_VEHICLES_NAME),
                             OP_EQ, SQLLiteral(veh_name.lower()))
        entries = self.select_generic_data(select_list=[COL_NAME_VEHICLES_VEHICLEID],
                                           table_list=[TABLE_NAME_VEHICLES],
                                           where=cond)
        if len(entries) == 1:
            return entries[0][COL_NAME_VEHICLES_VEHICLEID]
        elif len(entries) > 1:
            raise AdasDBError("Vehicle '%s' cannot be resolved because it is ambiguous. (%s)" % (veh_name, entries))

        raise AdasDBError("No resolution of '%s'. (%s)" % (veh_name, entries))

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def get_vehicle_name(self, vehid):
        """
        Get a vehicle name for a ID

        :param vehid: The vehicle ID to be resolved.
        :type vehid: int
        :return: Returns the name for the vehicle or if not exists then raises AdasDBError
        :rtype: str
        """
        vehid_cond = SQLBinaryExpr(COL_NAME_VEHICLES_VEHICLEID, OP_EQ, SQLLiteral(vehid))
        entries = self.select_generic_data(select_list=[COL_NAME_VEHICLES_NAME],
                                           table_list=[TABLE_NAME_VEHICLES],
                                           where=vehid_cond)
        if len(entries) == 1:
            return entries[0][COL_NAME_VEHICLES_NAME]
        elif len(entries) > 1:
            raise AdasDBError("Vehicle ID '%s' cannot be resolved because it is ambiguous. (%s)" % (vehid, entries))

        raise AdasDBError("No resolution of '%s'. (%s)" % (vehid, entries))

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def add_vehicle_cfg(self, vehiclecfg):
        """
        Add new vehicle cfg to database.

        :param vehiclecfg: The vehicle cfg record.
        :return: Returns the vehicle cfg ID.
        :rtype: int
        """
        vehcfgid = self._get_next_id(TABLE_NAME_VEHICLECFGS, COL_NAME_VEHICLECFGS_VEHCFGID)
        vehiclecfg[COL_NAME_VEHICLECFGS_VEHCFGID] = vehcfgid
        self.add_generic_data(vehiclecfg, TABLE_NAME_VEHICLECFGS)
        return vehcfgid

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def update_vehicle_cfgs(self, vehiclecfg, where=None):
        """
        Update existing vehicle cfg records.

        :param vehiclecfg: The vehicle cfg record update.
        :type vehiclecfg: dict
        :param where: The condition to be fulfilled by the vehicle cfgs to the updated.
        :type where: SQLBinaryExpression
        :return: Returns the number of affected vehicle cfgs.
        :rtype: int
        """
        rowcount = 0
        if vehiclecfg is not None:
            self.update_generic_data(vehiclecfg, TABLE_NAME_VEHICLECFGS, where)
        # done
        return rowcount

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def get_vehicle_cfg_id(self, vehcfg_name):
        """
        Get a vehicle cfg ID for a vehicle cfg name

        :param vehcfg_name: The vehicle cfg name to be resolved.
        :type vehcfg_name: str
        :return: Returns the ID for the vehicle cfg or None if not exists.
        :rtype: Intege
        """
        is_rooted = False
        cfg_name = vehcfg_name.rstrip(PATH_SEPARATOR)
        if self.is_absolute_name(cfg_name):
            cfg_name = cfg_name.lstrip(PATH_SEPARATOR)
            is_rooted = True
        cfg_name_parts = cfg_name.split(PATH_SEPARATOR)
        # if absolute name, get vehicle ID
        vehid_cond = None
        if is_rooted:
            if len(cfg_name_parts) != 2:
                tmp = "Vehicle configuration name '%s' " % vehcfg_name
                tmp += "cannot be resolved. Name must have format '/vehicle/config'."
                raise AdasDBError(tmp)
            vehid = self.get_vehicle_id(cfg_name_parts[0])
            vehid_cond = SQLBinaryExpr(COL_NAME_VEHICLECFGS_VEHICLEID, OP_EQ, SQLLiteral(vehid))
            cfg_name = cfg_name_parts[1].strip()
        # get configuration id (for vehicle, if absolute)
        cfg_cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                             COL_NAME_VEHICLECFGS_NAME),
                                 OP_EQ, SQLLiteral(cfg_name.lower()))
        if vehid_cond is not None:
            cfg_cond = SQLBinaryExpr(vehid_cond, OP_AND, cfg_cond)
        entries = self.select_generic_data(select_list=[COL_NAME_VEHICLECFGS_VEHCFGID],
                                           table_list=[TABLE_NAME_VEHICLECFGS],
                                           where=cfg_cond)
        if len(entries) == 1:
            return entries[0][COL_NAME_VEHICLECFGS_VEHCFGID]
        elif len(entries) > 1:
            tmp = "Vehicle configuration '%s' " % vehcfg_name
            tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
            raise AdasDBError(tmp)

        raise AdasDBError("No resolution of '%s'. (%s)" % (vehcfg_name, entries))

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def get_vehicle_cfg_name(self, vehcfgid, absolute=True):
        """
        Get a vehicle configuration name for a ID

        :param vehcfgid: The vehicle configuration ID to be resolved.
        :type vehcfgid: int
        :param absolute: Set True to return absolute names
        :type absolute: bool
        :return: Returns the name for the vehicle configuration or if not exists raises AdasDBError
        :rtype: str
        """
        vehcfgid_cond = SQLBinaryExpr(COL_NAME_VEHICLECFGS_VEHCFGID, OP_EQ, SQLLiteral(vehcfgid))
        entries = self.select_generic_data(select_list=[COL_NAME_VEHICLECFGS_NAME, COL_NAME_VEHICLECFGS_VEHICLEID],
                                           table_list=[TABLE_NAME_VEHICLECFGS],
                                           where=vehcfgid_cond)
        if len(entries) == 1:
            if absolute:
                veh_name = self.get_vehicle_name(entries[0][COL_NAME_VEHICLECFGS_VEHICLEID])
                return "%s%s%s" % (veh_name, PATH_SEPARATOR, entries[0][COL_NAME_VEHICLECFGS_NAME])
            else:
                return entries[0][COL_NAME_VEHICLECFGS_NAME]
        elif len(entries) > 1:
            tmp = "Vehicle configuration ID '%s' " % vehcfgid
            tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
            raise AdasDBError(tmp)

        raise AdasDBError("No resolution of '%s'. (%s)" % (vehcfgid, entries))

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def add_vehicle_cfg_state(self, vehiclecfgstate):
        """
        Add new vehicle cfg to database.

        :param vehiclecfgstate: The vehicle cfg state record.
        :type vehiclecfgstate: dict
        :return: Returns the vehicle cfg state ID.
        :rtype: int
        """
        vehcfgstateid = self._get_next_id(TABLE_NAME_VEHICLECFGSTATES, COL_NAME_VEHICLECFGSTATES_VEHICLECFGSTATEID)
        vehiclecfgstate[COL_NAME_VEHICLECFGSTATES_VEHICLECFGSTATEID] = vehcfgstateid
        self.add_generic_data(vehiclecfgstate, TABLE_NAME_VEHICLECFGSTATES)
        return vehcfgstateid

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def update_vehicle_cfg_states(self, vehiclecfgstate, where=None):
        """
        Update vehicle cfg in database.

        :param vehiclecfgstate: The vehicle cfg state record
        :type vehiclecfgstate: dict
        :param where: The condition to be fulfilled by the vehicle cfgs to the updated.
        :type where: SQLBinaryExpression
        :return: Returns the number of affected vehicle cfgs.
        :rtype: int
        """
        rowcount = 0
        if vehiclecfgstate is not None:
            self.update_generic_data(vehiclecfgstate, TABLE_NAME_VEHICLECFGSTATES, where)
        # done
        return rowcount

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def get_vehicle_cfg_state_id(self, vehcfgstate_name):
        """
        Get a vehicle cfg ID for a vehicle cfg name

        :param vehcfgstate_name: The vehicle cfg state name to be resolved.
        :type vehcfgstate_name: str
        :return: Returns the ID for the vehicle cfg. if not exist raises AdasDBError
        :rtype: int
        """
        # is_rooted = False
        cfg_name = vehcfgstate_name.rstrip(PATH_SEPARATOR)
        # get configuration id (for vehicle, if absolute)
        cfg_cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                             COL_NAME_VEHICLECFGSTATES_NAME),
                                 OP_EQ, SQLLiteral(cfg_name.lower()))
        entries = self.select_generic_data(select_list=[COL_NAME_VEHICLECFGSTATES_VEHICLECFGSTATEID],
                                           table_list=[TABLE_NAME_VEHICLECFGSTATES],
                                           where=cfg_cond)
        if len(entries) == 1:
            return entries[0][COL_NAME_VEHICLECFGSTATES_VEHICLECFGSTATEID]
        elif len(entries) > 1:
            tmp = "Vehicle configuration state '%s' " % vehcfgstate_name
            tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
            raise AdasDBError(tmp)

        raise AdasDBError("No resolution of vehicle configuration state '%s'. (%s)" % (vehcfgstate_name, entries))

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def get_vehicle_cfg_state_name(self, vehcfgstateid):
        """
        Get a vehicle configuration name for a ID

        :param vehcfgstateid: The vehicle configuration state ID to be resolved.
        :type vehcfgstateid: int
        :return: Returns the name for the vehicle configuration. if not exist raises AdasDBError
        :rtype: str
        """
        vehcfgid_cond = SQLBinaryExpr(COL_NAME_VEHICLECFGSTATES_VEHICLECFGSTATEID, OP_EQ, SQLLiteral(vehcfgstateid))
        entries = self.select_generic_data(select_list=[COL_NAME_VEHICLECFGSTATES_NAME],
                                           table_list=[TABLE_NAME_VEHICLECFGSTATES],
                                           where=vehcfgid_cond)
        if len(entries) == 1:
            return entries[0][COL_NAME_VEHICLECFGSTATES_NAME]
        elif len(entries) > 1:
            tmp = "Vehicle configuration state ID '%s' " % vehcfgstateid
            tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
            raise AdasDBError(tmp)

        raise AdasDBError("No resolution of '%s'. (%s)" % (vehcfgstateid, entries))

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def add_vehicle_cfg_part(self, vehiclecfgpart):
        """
        Add new vehicle cfg part to database.

        :param vehiclecfgpart: The vehicle cfg part record.
        :type vehiclecfgpart: dict
        :return: Returns the vehicle cfg ID.
        :rtype: int
        """
        partid = self._get_next_id(TABLE_NAME_PARTCFGS, COL_NAME_PARTCFGS_PARTCFGID)
        vehiclecfgpart[COL_NAME_PARTCFGS_PARTCFGID] = partid
        self.add_generic_data(vehiclecfgpart, TABLE_NAME_PARTCFGS)
        # done
        return partid

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def update_vehicle_cfg_parts(self, vehiclecfgpart, where=None):
        """
        Update vehicle cfg parts in database.

        :param vehiclecfgpart: The vehicle cfg part record.
        :type vehiclecfgpart: dict
        :param where: The condition to be fulfilled by the vehicle cfg parts to the updated.
        :type where: SQLBinaryExpression
        :return: Returns the number of affected vehicle cfg parts.
        :rtype: int
        """
        rowcount = 0
        if vehiclecfgpart is not None:
            self.update_generic_data(vehiclecfgpart, TABLE_NAME_PARTCFGS, where)
        # done
        return rowcount

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def get_vehicle_part_cfg_id(self, partcfg_name):
        """
        Get a vehicle cfg ID for a vehicle cfg name

        :param partcfg_name: The vehicle cfg name to be resolved.
        :type partcfg_name: str
        :return: Returns the ID for the vehicle cfg. if not exist raises AdasDBError
        :rtype: int
        """
        is_rooted = False
        cfg_name = partcfg_name.rstrip(PATH_SEPARATOR)
        if self.is_absolute_name(cfg_name):
            cfg_name = cfg_name.lstrip(PATH_SEPARATOR)
            is_rooted = True
        cfg_name_parts = cfg_name.split(PATH_SEPARATOR)
        # if absolute name, get vehicle ID
        # partcfgid_cond = None
        if is_rooted:
            if len(cfg_name_parts) != 3:
                tmp = "Part configuration name '%s' " % partcfg_name
                tmp += "cannot be resolved. Name must have format "
                tmp += "'/vehicle/config/part'."
                raise AdasDBError(tmp)
            vehcfgid = self.get_vehicle_cfg_id("%s%s%s" % (cfg_name_parts[0], PATH_SEPARATOR, cfg_name_parts[1]))
            vehcfgid_cond = SQLBinaryExpr(COL_NAME_PARTCFGS_VEHCFGID, OP_EQ, SQLLiteral(vehcfgid))
            cfg_name = cfg_name_parts[2].strip()
        else:
            vehcfgid_cond = None
        # get configuration id (for vehicle configuration, if absolute)
        cfg_cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                             COL_NAME_PARTCFGS_NAME),
                                 OP_EQ, SQLLiteral(cfg_name.lower()))
        if vehcfgid_cond is not None:
            cfg_cond = SQLBinaryExpr(vehcfgid_cond, OP_AND, cfg_cond)
        entries = self.select_generic_data(select_list=[COL_NAME_PARTCFGS_VEHCFGID],
                                           table_list=[TABLE_NAME_PARTCFGS],
                                           where=cfg_cond)
        if len(entries) == 1:
            return entries[0][COL_NAME_PARTCFGS_PARTCFGID]
        elif len(entries) > 1:
            tmp = "Part configuration '%s' " % partcfg_name
            tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
            raise AdasDBError(tmp)

        raise AdasDBError("No resolution of '%s'. (%s)" % (partcfg_name, entries))

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def get_vehicle_cfg_part_name(self, partid, absolute=True):
        """
        Get a part name for a ID

        :param partid: The part ID to be resolved.
        :type partid: int
        :param absolute: Set True to return absolute name
        :type absolute: bool
        :return: Returns the name for the part or None if not exists.
        """
        partid_cond = SQLBinaryExpr(COL_NAME_PARTCFGS_PARTCFGID, OP_EQ, SQLLiteral(partid))
        entries = self.select_generic_data(select_list=[COL_NAME_PARTCFGS_VEHCFGID, COL_NAME_PARTCFGS_NAME],
                                           table_list=[TABLE_NAME_PARTCFGS],
                                           where=partid_cond)
        if len(entries) == 1:
            if absolute:
                vehcfg_name = self.get_vehicle_cfg_name(entries[0][COL_NAME_PARTCFGS_VEHCFGID])
                return "%s%s%s" % (entries[0][COL_NAME_PARTCFGS_NAME], PATH_SEPARATOR, vehcfg_name)
            else:
                return entries[0][COL_NAME_PARTCFGS_NAME]
        elif len(entries) > 1:
            tmp = "Part configuration ID '%s' " % partid
            tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
            raise AdasDBError(tmp)

        raise AdasDBError("No resolution of '%s'. (%s)" % (partid, entries))

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def add_vehicle_cfg_part_type(self, parttype):
        """
        Add new part type to database.

        :param parttype: The part type record.
        :type parttype: dict
        :return: Returns the part type ID.
        """
        pt_cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                            COL_NAME_PARTTYPES_NAME),
                                OP_EQ, SQLLiteral(parttype[COL_NAME_PARTTYPES_NAME].lower()))
        entries = self.select_generic_data(table_list=[TABLE_NAME_PARTTYPES], where=pt_cond)
        if len(entries) <= 0:
            ptid = self._get_next_id(TABLE_NAME_PARTTYPES, COL_NAME_PARTTYPES_PARTTYPEID)
            parttype[COL_NAME_PARTTYPES_PARTTYPEID] = ptid
            self.add_generic_data(parttype, TABLE_NAME_PARTTYPES)
            return ptid
        else:
            if self.error_tolerance < ERROR_TOLERANCE_LOW:
                raise AdasDBError("Part type '%s' exists already in the catalog." % parttype[COL_NAME_PARTTYPES_NAME])
            else:
                warn("Part type '" + parttype[COL_NAME_PARTTYPES_NAME] + "' already exists in the catalog.")
                if len(entries) == 1:
                    return entries[0][COL_NAME_PARTTYPES_PARTTYPEID]
                elif len(entries) > 1:
                    tmp = "Part type '%s' " % (parttype[COL_NAME_PARTTYPES_NAME])
                    tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
                    raise AdasDBError(tmp)

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def update_vehicle_cfg_part_types(self, vehiclecfgparttype, where=None):
        """
        Update vehicle cfg parts in database.

        :param vehiclecfgparttype: The vehicle cfg part type record.
        :type vehiclecfgparttype: dict
        :param where: The condition to be fulfilled by the vehicle cfg part types to the updated.
        :type where: SQLBinaryExpression
        :return: Returns the number of affected vehicle cfg part types.
        :rtype: int
        """
        rowcount = 0
        if vehiclecfgparttype is not None:
            self.update_generic_data(vehiclecfgparttype, TABLE_NAME_PARTTYPES, where)
        # done
        return rowcount

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def get_part_type_id(self, parttype_name):
        """
        Get a parttype ID for a parttype name

        :param parttype_name: The parttype name to be resolved.
        :type parttype_name: str
        :return: Returns the ID for the parttype. if parttype not exists raises AdasDBError.
        :rtype: int
        """
        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                         COL_NAME_PARTTYPES_NAME),
                             OP_EQ, SQLLiteral(parttype_name.lower()))
        entries = self.select_generic_data(select_list=[COL_NAME_PARTTYPES_PARTTYPEID],
                                           table_list=[TABLE_NAME_PARTTYPES],
                                           where=cond)
        if len(entries) == 1:
            return entries[0][COL_NAME_PARTTYPES_PARTTYPEID]
        elif len(entries) > 1:
            tmp = "Part type '%s' " % parttype_name
            tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
            raise AdasDBError(tmp)

        raise AdasDBError("No resolution of '%s'. (%s)" % (parttype_name, entries))

    @deprecated("soon, vehiclecfg table will be removed, don't use!")
    def get_vehicle_cfg_part_type_name(self, parttypeid):
        """
        Get a part type name for a ID

        :param parttypeid: The parttype ID to be resolved.
        :type parttypeid:
        :return: Returns the name for the part type. if name not exist then raises AdasDBError.
        :rtype: int
        """
        partid_cond = SQLBinaryExpr(COL_NAME_PARTTYPES_PARTTYPEID, OP_EQ, SQLLiteral(parttypeid))
        entries = self.select_generic_data(select_list=[COL_NAME_PARTTYPES_NAME],
                                           table_list=[TABLE_NAME_PARTTYPES],
                                           where=partid_cond)
        if len(entries) == 1:
            return entries[0][COL_NAME_PARTTYPES_NAME]
        elif len(entries) > 1:
            tmp = "Part type ID '%s' cannot be resolved because it is ambiguous. (%s)" % (parttypeid, entries)
            raise AdasDBError(tmp)

        raise AdasDBError("No resolution of '%s'. (%s)" % (parttypeid, entries))

    # ====================================================================
    # Handling of driver data
    # ====================================================================

    @staticmethod
    @deprecated()
    def add_driver(driver):
        """
        Add new driver to database.

        :param driver: The driver record.
        :type driver: dict
        :return: Returns the driver ID.
        :rtype: int
        """
        raise AdasDBError("It's not allowed to add any driver any more here, use meta data API!")

    @staticmethod
    @deprecated()
    def update_drivers(driver, where=None):
        """
        Update drivers in database.

        :param driver: The driver record.
        :type driver: dict
        :param where: The condition to be fulfilled by the drivers to the updated.
        :type where: SQLBinaryExpression
        :return: Returns the number of affected drivers.
        :rtype: int
        """
        return 0

    @staticmethod
    @deprecated()
    def get_driver_id(driver_name):
        """
        Get a driver ID for a driver name

        :param driver_name: The driver name to be resolved.
        :type driver_name: str
        :return: Returns the ID for the driver. if doesn't exist then raises AdasDBError.
        :rtype: int
        """
        raise AdasDBError("No resolution of '%s'." % driver_name)

    @staticmethod
    @deprecated()
    def get_driver_name(driverid):
        """
        Get a driver name for a ID

        :param driverid: The driver ID to be resolved.
        :type driverid: int
        :return: Returns the name for the driver. if doesn't exist then raises AdasDBError.
        :rtype: str
        """
        if driverid == 0:
            return "(unknown)"

        raise AdasDBError("No resolution of '%s'." % driverid)

    # ====================================================================
    # Handling of auxiliary data
    # ====================================================================

    def add_file_state(self, filestate):
        """
        Add new file state to database.

        :param filestate: The file state record.
        :type filestate: dict
        :return: Returns the file state ID.
        :rtype: int
        """
        if filestate is not None:
            fs_cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                                COL_NAME_FILESTATES_NAME),
                                    OP_EQ, SQLLiteral(filestate[COL_NAME_FILESTATES_NAME].lower()))
            entries = self.select_generic_data(table_list=[TABLE_NAME_FILESTATES], where=fs_cond)
            if len(entries) <= 0:

                if self.sub_scheme_version < CAT_ACTIVE_VERSION:
                    fsid = self._get_next_id(TABLE_NAME_FILESTATES, COL_NAME_FILESTATES_FILESTATEID)
                    filestate[COL_NAME_FILESTATES_FILESTATEID] = fsid
                else:
                    self.add_generic_data(filestate, TABLE_NAME_FILESTATES)
                    entries = self.select_generic_data(table_list=[TABLE_NAME_FILESTATES], where=fs_cond)
                    fsid = entries[0][COL_NAME_FILESTATES_FILESTATEID]

                return fsid
            else:
                if self.error_tolerance < ERROR_TOLERANCE_LOW:
                    tmp = "File state '%s' exists already in the catalog." % filestate[COL_NAME_FILESTATES_NAME]
                    raise AdasDBError(tmp)
                else:
                    warn("File state '" + filestate[COL_NAME_FILESTATES_NAME] + "' already exists in the catalog.")
                    if len(entries) == 1:
                        return entries[0][COL_NAME_FILESTATES_FILESTATEID]
                    elif len(entries) > 1:
                        tmp = "File state '%s' " % (filestate[COL_NAME_FILESTATES_NAME])
                        tmp += "cannot be resolved because it is ambiguous. (%s)" % entries
                        raise AdasDBError(tmp)
        return None

    def update_file_states(self, filestate, where=None):
        """
        Update file states in database.

        :param filestate: The file state record with new or modified values
        :type filestate: dict
        :param where: The condition to be fulfilled by the file states to the updated.
        :type where: SQLBinaryExpression
        :return: Returns the number of affected file states.
        :rtype: int
        """
        rowcount = 0
        if filestate is not None:
            self.update_generic_data(filestate, TABLE_NAME_FILESTATES, where)
        # done
        return rowcount

    def get_file_state_id(self, fstate_name):
        """
        Get a file state ID for a file state name

        :param fstate_name: The file state name to be resolved.
        :type fstate_name: str
        :return: Returns the ID for the file stat. if file state not exists then raise AdasDBError.
        :rtype: int
        """
        cond = SQLBinaryExpr(SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_LOWER],
                                         COL_NAME_FILESTATES_NAME),
                             OP_EQ, SQLLiteral(fstate_name.lower()))
        entries = self.select_generic_data(select_list=[COL_NAME_FILESTATES_FILESTATEID],
                                           table_list=[TABLE_NAME_FILESTATES],
                                           where=cond)
        if len(entries) == 1:
            return entries[0][COL_NAME_FILESTATES_FILESTATEID]
        elif len(entries) > 1:
            tmp = "File state '%s' cannot be resolved because it is ambiguous. (%s)" % (fstate_name, entries)
            raise AdasDBError(tmp)

        raise AdasDBError("No resolution of '%s'. (%s)" % (fstate_name, entries))

    def get_file_state_name(self, fstateid):
        """
        Get a file state name for a file state ID

        :param fstateid: The file state ID to be resolved.
        :type fstateid: int
        :return: Returns the name for the file state or None. if file state not exists then raise AdasDBError.
        :rtype: str
        """
        cond = SQLBinaryExpr(COL_NAME_FILESTATES_FILESTATEID, OP_EQ, SQLLiteral(fstateid))
        entries = self.select_generic_data(select_list=[COL_NAME_FILESTATES_NAME],
                                           table_list=[TABLE_NAME_FILESTATES],
                                           where=cond)
        if len(entries) == 1:
            return entries[0][COL_NAME_FILESTATES_NAME]
        elif len(entries) > 1:
            raise AdasDBError("File state '%s' cannot be resolved because it is ambiguous. (%s)" % (fstateid, entries))

        raise AdasDBError("No resolution of '%s'. (%s)" % (fstateid, entries))

    # ====================================================================
    # Rec File Catalog Helper Functions
    # ====================================================================

    @staticmethod
    def is_absolute_name(name):
        """
        Check if a name is absolute.Absolute names start with path separator.

        :param name: The name to check.
        :type name: str
        :return: Returns true if the name is an absolute path name.
        :rtype: bool
        """
        if name is None:
            raise AdasDBError("Invalid name '%s'." % name)
        return name.startswith(PATH_SEPARATOR)

    @staticmethod
    def is_basic_name(name):
        """
        Check if a name is basic (doesnt contain path separator).

        :param name: The name to check.
        :type name: str
        :return: Returns true if the name is an basic name.
        :rtype: bool
        """
        if name is None:
            raise AdasDBError("Invalid name '%s'." % name)
        return name.find(PATH_SEPARATOR)

    # ====================================================================
    # deprecated methods
    # ====================================================================

    @deprecated('curr_date_time')
    def get_curr_date_time(self):
        """deprecated"""
        return self.curr_date_time()

    @deprecated('curr_date_time')
    def GetCurrDateTime(self):  # pylint: disable=C0103
        """deprecated"""
        return self.curr_date_time()

    @deprecated('select_measurements')
    def SelectMeasurements(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.select_measurements(*args, **kw)

    @deprecated('add_measurement')
    def AddMeasurement(self, measurement):  # pylint: disable=C0103
        """deprecated"""
        return self.add_measurement(measurement)

    @deprecated('add_collection_map')
    def AddCollectionMap(self, collmap):  # pylint: disable=C0103
        """deprecated"""
        return self.add_collection_map(collmap)

    @deprecated('has_measurement')
    def HasMeasurement(self, filepath):  # pylint: disable=C0103
        """deprecated"""
        return self.has_measurement(filepath)

    @deprecated('get_measurement_id')
    def GetMeasurementID(self, recfile):  # pylint: disable=C0103
        """deprecated"""
        return self.get_measurement_id(recfile)

    @deprecated('get_measurement_with_sections')
    def GetMeasurementWithSections(self, measid, collid=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_measurement_with_sections(measid, collid)

    @deprecated('update_measurements')
    def UpdateMeasurements(self, measurement, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_measurements(measurement, where)

    @staticmethod
    @deprecated()
    def check_measurement_availability(_):
        """deprecated"""
        raise DeprecationWarning("Use has_measurement and check the existing methods before implementing new ones!")

    @deprecated('check_measurement_availability')
    def CheckMeasurementAvailability(self, recfile):  # pylint: disable=C0103
        """deprecated"""
        return self.check_measurement_availability(recfile)

    @deprecated('add_collection')
    def AddCollection(self, collection):  # pylint: disable=C0103
        """deprecated"""
        return self.add_collection(collection)

    @deprecated('update_collection')
    def UpdateCollection(self, collection, collid):  # pylint: disable=C0103
        """deprecated"""
        return self.update_collection(collection, collid)

    @deprecated('delete_collection_map')
    def DeleteCollectionMap(self, measid, collection_name):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_collection_map(measid, collection_name)

    @deprecated('delete_collection')
    def DeleteCollection(self, collection_name):  # pylint: disable=C0103
        """deprecated"""
        return self.delete_collection(collection_name)

    @deprecated('get_collection')
    def GetCollection(self, coll_id):  # pylint: disable=C0103
        """deprecated"""
        return self.get_collection(coll_id)

    @deprecated('get_collection_id')
    def GetCollectionID(self, coll_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_collection_id(coll_name)

    @deprecated('get_collection_name')
    def GetCollectionName(self, collid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_collection_name(collid)

    @deprecated('get_collections')
    def GetCollections(self, collid, recurse=True):  # pylint: disable=C0103
        """deprecated"""
        return self.get_collections(collid, recurse)

    @deprecated('get_all_collection_names')
    def GetAllCollectionsNames(self):  # pylint: disable=C0103
        """deprecated"""
        return self.get_all_collection_names()

    @deprecated('get_collection_measurements')
    def GetCollectionMeasurements(self, collid, recurse=True, recfile_paths=False,  # pylint: disable=C0103
                                  recfile_dict=False):
        """deprecated"""
        return self.get_collection_measurements(collid, recurse, recfile_paths, recfile_dict)

    @deprecated('update_collection_priority')
    def UpdateCollectionPriority(self, collid, prid):  # pylint: disable=C0103
        """deprecated"""
        return self.update_collection_priority(collid, prid)

    @deprecated('get_collection_priority')
    def GetCollectionPriority(self, collid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_collection_priority(collid)

    @deprecated('export_bpl_measurment')
    def ExportBPLMeasurment(self, measid_list, output_path):  # pylint: disable=C0103
        """deprecated"""
        return self.export_bpl_measurment(measid_list, output_path)

    @deprecated('export_bpl_for_collection')
    def ExportBPLForCollection(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.export_bpl_for_collection(*args, **kw)

    @deprecated('get_rec_file_name_for_measid')
    def GetRecFileNameForMeasid(self, measid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_rec_file_name_for_measid(measid)

    @deprecated('get_measurement_collection_names')
    def GetMeasurementCollectionNames(self, file_path, coll_name=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_measurement_collection_names(file_path, coll_name)

    @deprecated('is_measurement_in_collection')
    def IsMeasurementInCollection(self, collid, measid=None, file_path=None):  # pylint: disable=C0103
        """deprecated"""
        return self.is_measurement_in_collection(collid, measid, file_path)

    @deprecated('get_collection_hours_kilometer_for_part_config_version')
    def GetCollectionHoursKilometerForPartConfigVersion(self, collection_name, version_type):  # pylint: disable=C0103
        """deprecated"""
        return self.get_collection_hours_kilometer_for_part_config_version(collection_name, version_type)

    @deprecated('get_collection_hours_kilometer_per_recdate')
    def GetCollectionHoursKilometerPerRecdate(self, collection_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_collection_hours_kilometer_per_recdate(collection_name)

    @deprecated('get_collection_hours_kilometer_per_driver')
    def GetCollectionHoursKilometerPerDriver(self, collection_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_collection_hours_kilometer_per_driver(collection_name)

    @deprecated('get_collection_hours_kilometer_per_vehicle')
    def GetCollectionHoursKilometerPerVehicle(self, collection_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_collection_hours_kilometer_per_vehicle(collection_name)

    @deprecated('get_collection_kilometer')
    def GetCollectionKilometer(self, collection_name=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_collection_kilometer(collection_name)

    @deprecated('get_collection_time')
    def GetCollectionTime(self, collection_name=None):  # pylint: disable=C0103
        """deprecated"""
        return self.get_collection_time(collection_name)

    @deprecated('add_keyword')
    def AddKeyword(self, keyword):  # pylint: disable=C0103
        """deprecated"""
        return self.add_keyword(keyword)

    @deprecated('update_keywords')
    def UpdateKeywords(self, keyword, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_keywords(keyword, where)

    @deprecated('add_keyword_map')
    def AddKeywordMap(self, kwmap):  # pylint: disable=C0103
        """deprecated"""
        return self.add_keyword_map(kwmap)

    @deprecated('get_keyword_id')
    def GetKeywordID(self, kw_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_keyword_id(kw_name)

    @deprecated('get_keyword_name')
    def GetKeywordName(self, kwid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_keyword_name(kwid)

    @deprecated('add_country')
    def AddCountry(self, country):  # pylint: disable=C0103
        """deprecated"""
        return self.add_country(country)

    @deprecated('update_countries')
    def UpdateCountries(self, country, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_countries(country, where)

    @deprecated('get_country_id')
    def GetCountryID(self, country):  # pylint: disable=C0103
        """deprecated"""
        return self.get_country_id(country)

    @deprecated('get_country_name')
    def GetCountryName(self, cntryid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_country_name(cntryid)

    @deprecated('add_location')
    def AddLocation(self, location):  # pylint: disable=C0103
        """deprecated"""
        return self.add_location(location)

    @deprecated('get_location_id')
    def GetLocationID(self, location):  # pylint: disable=C0103
        """deprecated"""
        return self.get_location_id(location)

    @deprecated('update_locations')
    def UpdateLocations(self, location, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_locations(location, where)

    @deprecated('add_location_info')
    def AddLocationInfo(self, location):  # pylint: disable=C0103
        """deprecated"""
        return self.add_location_info(location)

    @deprecated('get_location_info')
    def GetLocationInfo(self, locinfoid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_location_info(locinfoid)

    @deprecated('get_location_info_ids')
    def GetLocationInfoIDs(self, measid, location):  # pylint: disable=C0103
        """deprecated"""
        return self.get_location_info_ids(measid, location)

    @deprecated('get_location_info_idat_rel_time')
    def GetLocationInfoIDatRelTime(self, measid, location, reltime):  # pylint: disable=C0103
        """deprecated"""
        return self.get_location_info_idat_rel_time(measid, location, reltime)

    @deprecated('update_locations_info')
    def UpdateLocationsInfo(self, location, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_locations_info(location, where)

    @deprecated('add_vehicle')
    def AddVehicle(self, vehicle):  # pylint: disable=C0103
        """deprecated"""
        return self.add_vehicle(vehicle)

    @deprecated('update_vehicles')
    def UpdateVehicles(self, vehicle, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_vehicles(vehicle, where)

    @deprecated('get_vehicle_id')
    def GetVehicleID(self, veh_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_vehicle_id(veh_name)

    @deprecated('get_vehicle_name')
    def GetVehicleName(self, vehid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_vehicle_name(vehid)

    @deprecated('add_vehicle_cfg')
    def AddVehicleCfg(self, vehiclecfg):  # pylint: disable=C0103
        """deprecated"""
        return self.add_vehicle_cfg(vehiclecfg)

    @deprecated('update_vehicle_cfgs')
    def UpdateVehicleCfgs(self, vehiclecfg, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_vehicle_cfgs(vehiclecfg, where)

    @deprecated('get_vehicle_cfg_id')
    def GetVehicleCfgID(self, vehcfg_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_vehicle_cfg_id(vehcfg_name)

    @deprecated('get_vehicle_cfg_name')
    def GetVehicleCfgName(self, vehcfgid, absolute=True):  # pylint: disable=C0103
        """deprecated"""
        return self.get_vehicle_cfg_name(vehcfgid, absolute)

    @deprecated('add_vehicle_cfg_state')
    def AddVehicleCfgState(self, vehiclecfgstate):  # pylint: disable=C0103
        """deprecated"""
        return self.add_vehicle_cfg_state(vehiclecfgstate)

    @deprecated('update_vehicle_cfg_states')
    def UpdateVehicleCfgStates(self, vehiclecfgstate, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_vehicle_cfg_states(vehiclecfgstate, where)

    @deprecated('get_vehicle_cfg_state_id')
    def GetVehicleCfgStateID(self, vehcfgstate_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_vehicle_cfg_state_id(vehcfgstate_name)

    @deprecated('get_vehicle_cfg_state_name')
    def GetVehicleCfgStateName(self, vehcfgstateid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_vehicle_cfg_state_name(vehcfgstateid)

    @deprecated('add_vehicle_cfg_part')
    def AddVehicleCfgPart(self, vehiclecfgpart):  # pylint: disable=C0103
        """deprecated"""
        return self.add_vehicle_cfg_part(vehiclecfgpart)

    @deprecated('update_vehicle_cfg_parts')
    def UpdateVehicleCfgParts(self, vehiclecfgpart, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_vehicle_cfg_parts(vehiclecfgpart, where)

    @deprecated('get_vehicle_part_cfg_id')
    def GetVehiclePartCfgID(self, partcfg_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_vehicle_part_cfg_id(partcfg_name)

    @deprecated('get_vehicle_cfg_part_name')
    def GetVehicleCfgPartName(self, partid, absolute=True):  # pylint: disable=C0103
        """deprecated"""
        return self.get_vehicle_cfg_part_name(partid, absolute)

    @deprecated('add_vehicle_cfg_part_type')
    def AddVehicleCfgPartType(self, parttype):  # pylint: disable=C0103
        """deprecated"""
        return self.add_vehicle_cfg_part_type(parttype)

    @deprecated('update_vehicle_cfg_part_types')
    def UpdateVehicleCfgPartTypes(self, vehiclecfgparttype, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_vehicle_cfg_part_types(vehiclecfgparttype, where)

    @deprecated('get_part_type_id')
    def GetPartTypeID(self, parttype_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_part_type_id(parttype_name)

    @deprecated('get_vehicle_cfg_part_type_name')
    def GetVehicleCfgPartTypeName(self, parttypeid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_vehicle_cfg_part_type_name(parttypeid)

    @deprecated('add_driver')
    def AddDriver(self, driver):  # pylint: disable=C0103
        """deprecated"""
        return self.add_driver(driver)

    @deprecated('update_drivers')
    def UpdateDrivers(self, driver, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_drivers(driver, where)

    @deprecated('get_driver_id')
    def GetDriverID(self, driver_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_driver_id(driver_name)

    @deprecated('get_driver_name')
    def GetDriverName(self, driverid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_driver_name(driverid)

    @deprecated('add_file_state')
    def AddFileState(self, filestate):  # pylint: disable=C0103
        """deprecated"""
        return self.add_file_state(filestate)

    @deprecated('update_file_states')
    def UpdateFileStates(self, filestate, where=None):  # pylint: disable=C0103
        """deprecated"""
        return self.update_file_states(filestate, where)

    @deprecated('get_file_state_id')
    def GetFileStateID(self, fstate_name):  # pylint: disable=C0103
        """deprecated"""
        return self.get_file_state_id(fstate_name)

    @deprecated('get_file_state_name')
    def GetFileStateName(self, fstateid):  # pylint: disable=C0103
        """deprecated"""
        return self.get_file_state_name(fstateid)

    @deprecated('is_absolute_name')
    def IsAbsoluteName(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.is_absolute_name(name)

    @deprecated('is_basic_name')
    def IsBasicName(self, name):  # pylint: disable=C0103
        """deprecated"""
        return self.is_basic_name(name)


# ====================================================================
# Constraint DB Libary SQL Server Compact Implementation
# ====================================================================
class PluginRecCatalogDB(BaseRecCatalogDB, PluginBaseDB):  # pylint: disable=R0904
    """used by plugin finder"""
    def __init__(self, *args, **kwargs):
        """some comment is missing"""
        BaseRecCatalogDB.__init__(self, *args, **kwargs)


class SQLCERecCatalogDB(BaseRecCatalogDB, PluginBaseDB):  # pylint: disable=R0904
    """SQL Server Compact Edition Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseRecCatalogDB.__init__(self, *args, **kwargs)


class OracleRecCatalogDB(BaseRecCatalogDB, PluginBaseDB):  # pylint: disable=R0904
    """Oracle Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseRecCatalogDB.__init__(self, *args, **kwargs)


class SQLite3RecCatalogDB(BaseRecCatalogDB, PluginBaseDB):  # pylint: disable=R0904
    """Oracle Implementation of rec file DB access"""
    def __init__(self, *args, **kwargs):
        """deprecated"""
        BaseRecCatalogDB.__init__(self, *args, **kwargs)


"""
$Log: cat.py  $
Revision 1.80 2017/11/14 16:23:25CET Hospes, Gerd-Joachim (uidv8815) 
use location cond als for oracle
Revision 1.79 2017/11/14 12:14:01CET Hospes, Gerd-Joachim (uidv8815)
fix typo
Revision 1.78 2017/11/14 11:54:05CET Hospes, Gerd-Joachim (uidv8815)
fix version check, use cat verson 13
Revision 1.77 2017/11/13 17:09:32CET Hospes, Gerd-Joachim (uidv8815)
use location, update tests, add table gbl_location and cat_files column location to sqlite
Revision 1.76 2017/08/07 08:56:47CEST Hospes, Gerd-Joachim (uidv8815)
further speedup for Oracle, speedup test in test_db_common unchanged
Revision 1.75 2017/07/18 13:30:06CEST Hospes, Gerd-Joachim (uidv8815)
fix to run old sqlite versions: set cat db version and check
Revision 1.74 2017/07/18 10:36:41CEST Hospes, Gerd-Joachim (uidv8815)
return empty list if collection is empty, test extended
Revision 1.73 2017/07/14 17:24:58CEST Mertens, Sven (uidv7805)
mark vehicle info methods as being deprecated
Revision 1.72 2017/07/14 16:44:25CEST Mertens, Sven (uidv7805)
go around driverid
Revision 1.71 2017/07/13 14:48:47CEST Mertens, Sven (uidv7805)
deprecating cat_driver interface
Revision 1.70 2017/06/08 13:51:15CEST Ahmed, Zaheer (uidu7634)
get measurment speedup for new fileserver
Revision 1.69 2016/09/30 11:42:39CEST Hospes, Gerd-Joachim (uidv8815)
get_collections return also shared if not recursive, new test added
Revision 1.68 2016/09/19 13:32:33CEST Hospes, Gerd-Joachim (uidv8815)
combine col maps for add checkpoint in _copy_collection
Revision 1.67 2016/09/16 17:57:37CEST Hospes, Gerd-Joachim (uidv8815)
speedup add_collection_checkpoint and add label to some coll methods
Revision 1.66 2016/09/16 11:43:46CEST Ahmed, Zaheer (uidu7634)
copy collection_map table to file link data for checkpoint collection
Revision 1.65 2016/08/16 16:01:37CEST Hospes, Gerd-Joachim (uidv8815)
fix epydoc errors
Revision 1.64 2016/08/16 12:26:18CEST Hospes, Gerd-Joachim (uidv8815)
update module and class docu
Revision 1.63 2016/08/08 10:31:55CEST Hospes, Gerd-Joachim (uidv8815)
fix epydoc errors
Revision 1.62 2016/08/04 19:16:06CEST Hospes, Gerd-Joachim (uidv8815)
fix to get labelled colls added
Revision 1.61 2016/08/01 14:55:07CEST Mertens, Sven (uidv7805)
adding method to create a collection checkpoint
Revision 1.60 2016/07/27 15:49:28CEST Hospes, Gerd-Joachim (uidv8815)
rem chars from top entered by PyCharm
Revision 1.59 2016/07/27 15:38:39CEST Hospes, Gerd-Joachim (uidv8815)
new get_collection_checkpoint, some docu updates
Revision 1.56 2016/07/27 10:23:56CEST Ahmed, Zaheer (uidu7634)
bug fix in get_collection_id()
Revision 1.55 2016/07/25 11:05:24CEST Ahmed, Zaheer (uidu7634)
adaption of exist method to support collection checkpoint
Revision 1.54 2016/07/11 09:12:06CEST Mertens, Sven (uidv7805)
new column definitions
Revision 1.53 2016/07/01 18:48:14CEST Hospes, Gerd-Joachim (uidv8815)
check if shared colls are supported by db
Revision 1.52 2016/06/23 15:53:01CEST Hospes, Gerd-Joachim (uidv8815)
fix mks checkin errors
Revision 1.51 2016/05/31 14:34:27CEST Hospes, Gerd-Joachim (uidv8815)
cleanup
Revision 1.50 2016/05/30 18:50:45CEST Hospes, Gerd-Joachim (uidv8815)
changed shared coll queries, add tests in test_collections
Revision 1.49 2016/05/23 15:46:34CEST Hospes, Gerd-Joachim (uidv8815)
split import_bpl_to_collection to create add_bplentry_to_collection
Revision 1.48 2016/05/19 18:38:51CEST Hospes, Gerd-Joachim (uidv8815)
add delete_collection_map_section and update_collection_map_section with module tests
Revision 1.47 2016/05/13 11:30:02CEST Hospes, Gerd-Joachim (uidv8815)
fix record start ts in import bpl
Revision 1.46 2016/05/12 17:07:46CEST Hospes, Gerd-Joachim (uidv8815)
add sections to export_bpl_measurement
Revision 1.45 2016/04/25 11:18:43CEST Mertens, Sven (uidv7805)
fix for wrong sub collection ID's
Revision 1.44 2016/04/01 09:26:59CEST Mertens, Sven (uidv7805)
some fixes
Revision 1.43 2016/03/31 17:56:46CEST Mertens, Sven (uidv7805)
as unittest somehow uses prios with extension "...priority", we need a like here
Revision 1.42 2016/03/16 16:56:23CET Ahmed, Zaheer (uidu7634)
variable binding fix for date to support sqlite and oracle in get_collection_log()
Revision 1.41 2016/03/16 15:25:09CET Ahmed, Zaheer (uidu7634)
pep8 fixes
Revision 1.40 2016/03/16 14:19:17CET Ahmed, Zaheer (uidu7634)
aligned collection log table according to production db
added more argument  in get_collection_log for filter crieteria
Revision 1.39 2016/03/16 11:58:07CET Ahmed, Zaheer (uidu7634)
renamed update_collections() to update_collection()
fixed internal usage of update_collection()
Revision 1.38 2016/03/16 11:28:43CET Ahmed, Zaheer (uidu7634)
extended collection summary with duration field
Revision 1.37 2016/03/15 16:26:46CET Ahmed, Zaheer (uidu7634)
added get_collection_summary(), get_collection_filesize()   with online offline stats
support online offline stats for get_measurement_number()
fixed deprecated UpdateCollections() input parameter
Revision 1.36 2016/03/14 15:53:08CET Hospes, Gerd-Joachim (uidv8815)
fixing the fix to COLLID instead of MEASID
Revision 1.35 2016/03/09 16:43:08CET Hospes, Gerd-Joachim (uidv8815)
use condition in get_collection_measurements()
Revision 1.34 2016/03/04 14:22:38CET Ahmed, Zaheer (uidu7634)
add new praram group_by in get_collection_kilometer() to get kilometer for offline/online files
Revision 1.33 2016/03/04 11:03:55CET Ahmed, Zaheer (uidu7634)
improve has_measurement(), get_meaurement_id() get_measurement_content_hash()
interface change for update_collection() to avoid risk of misuse
bugfix for is_collection_active()
Revision 1.32 2016/02/26 16:18:30CET Hospes, Gerd-Joachim (uidv8815)
fix docu format in some methods
Revision 1.31 2016/02/25 14:34:29CET Ahmed, Zaheer (uidu7634)
bug fix to calculate absoluate section end timestamp
Revision 1.30 2016/02/25 14:18:11CET Ahmed, Zaheer (uidu7634)
_get_measurement_collection_names() improved query and variable binding
is_measurement_in_collection() improved query and variable binding
Revision 1.29 2016/02/25 13:45:29CET Ahmed, Zaheer (uidu7634)
adapted export_bpl_collection() for share collection
Revision 1.28 2016/02/24 17:15:17CET Ahmed, Zaheer (uidu7634)
added method update_shared_collection_priority(), get_shared_collection_priority()
Revision 1.27 2016/02/24 15:54:46CET Ahmed, Zaheer (uidu7634)
adapted get_collection_kilometer() for shared collection with recursvie usecase
Revision 1.26 2016/02/24 10:24:03CET Ahmed, Zaheer (uidu7634)
bug fix for backward compatiblity _get_union_shared_collection_cond()
Revision 1.25 2016/02/24 09:36:15CET Ahmed, Zaheer (uidu7634)
get_collection_id() variable binding. add new function get_shared_collid()
get_collections_details() non recursive usecase has been fixed
get_measurements_number(), get_collection_measurements() adapted for shared collections
documentation improvement
Revision 1.24 2016/02/22 12:18:11CET Hospes, Gerd-Joachim (uidv8815)
update get_collectins_details()
Revision 1.23 2016/02/22 11:44:18CET Ahmed, Zaheer (uidu7634)
improved get_collection_id() variable binding
adapted get_collection_details() for shared collections
Revision 1.22 2016/02/19 17:00:46CET Ahmed, Zaheer (uidu7634)
rollback get_collection_id() to analyze later
Revision 1.21 2016/02/19 16:43:46CET Ahmed, Zaheer (uidu7634)
pep8 fixes
Revision 1.20 2016/02/19 16:31:28CET Ahmed, Zaheer (uidu7634)
get_collection() variable binding
get_collection_id() rework for optmization variable binding
get_collection_name() rework for optimzation
get_collections() bug fix to avoid potential crash
Revision 1.19 2016/02/19 15:14:56CET Ahmed, Zaheer (uidu7634)
adapted get_collections()
backword compatiblity for shared colleciton feature
Revision 1.18 2016/02/19 10:19:59CET Ahmed, Zaheer (uidu7634)
added function to get_collection_tree() which support shared collection tree
Revision 1.17 2016/02/12 10:43:36CET Ahmed, Zaheer (uidu7634)
rework for improving performance get_collections() get_collection_measurements()
Revision 1.16 2016/02/11 11:35:23CET Ahmed, Zaheer (uidu7634)
Rework of  get_collection_hours_kilometer_for_part_config_version() for perfomrance
pylint fixes
Revision 1.15 2016/02/04 15:34:30CET Ahmed, Zaheer (uidu7634)
bug fix to grab project name
Revision 1.14 2016/02/04 14:16:44CET Ahmed, Zaheer (uidu7634)
handling smb share with python ospath for get_measurement() and add_measurement()
Revision 1.13 2016/02/01 15:19:43CET Ahmed, Zaheer (uidu7634)
improved get_measurement()
Revision 1.12 2016/01/26 10:10:57CET Ahmed, Zaheer (uidu7634)
improved add_collection(), add_collection_map, delete_collection()
Revision 1.11 2015/12/07 10:01:15CET Mertens, Sven (uidv7805)
removing pep8 error
Revision 1.10 2015/12/04 14:31:13CET Mertens, Sven (uidv7805)
removing some lints
Revision 1.9 2015/12/04 11:58:11CET Mertens, Sven (uidv7805)
removing old location information methods
Revision 1.8 2015/07/30 10:35:20CEST Ahmed, Zaheer (uidu7634)
re adjustment in the function for catalog tagging feature
--- Added comments ---  uidu7634 [Jul 30, 2015 10:35:21 AM CEST]
Change Package : 361221:1 http://mks-psad:7002/im/viewissue?selection=361221
Revision 1.7 2015/07/16 16:05:19CEST Ahmed, Zaheer (uidu7634)
db interface for collection activity log
--- Added comments ---  uidu7634 [Jul 16, 2015 4:05:19 PM CEST]
Change Package : 348978:3 http://mks-psad:7002/im/viewissue?selection=348978
Revision 1.6 2015/07/14 11:14:44CEST Mertens, Sven (uidv7805)
rewinding some changes
--- Added comments ---  uidv7805 [Jul 14, 2015 11:14:44 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.5 2015/07/14 09:29:06CEST Mertens, Sven (uidv7805)
simplify for plugin finder
--- Added comments ---  uidv7805 [Jul 14, 2015 9:29:07 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.4 2015/05/19 16:19:47CEST Ahmed, Zaheer (uidu7634)
add measurement function must convert recfile name into lower case to have uniform pattern
to maximize index uliization fast select on cat_files
--- Added comments ---  uidu7634 [May 19, 2015 4:19:48 PM CEST]
Change Package : 338368:1 http://mks-psad:7002/im/viewissue?selection=338368
Revision 1.3 2015/05/19 12:55:49CEST Ahmed, Zaheer (uidu7634)
removed SQL function lower() from get_measurement to utilize index for performance
--- Added comments ---  uidu7634 [May 19, 2015 12:55:50 PM CEST]
Change Package : 338368:1 http://mks-psad:7002/im/viewissue?selection=338368
Revision 1.2 2015/04/30 11:09:32CEST Hospes, Gerd-Joachim (uidv8815)
merge last changes
--- Added comments ---  uidv8815 [Apr 30, 2015 11:09:33 AM CEST]
Change Package : 330394:1 http://mks-psad:7002/im/viewissue?selection=330394
Revision 1.1 2015/04/23 19:03:56CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/cat/project.pj
Revision 1.63 2015/04/30 10:07:31CEST Ahmed, Zaheer (uidu7634)
variable binding in get_measurement() and bug fix
--- Added comments ---  uidu7634 [Apr 30, 2015 10:07:32 AM CEST]
Change Package : 318797:1 http://mks-psad:7002/im/viewissue?selection=318797
Revision 1.62 2015/04/27 14:36:57CEST Mertens, Sven (uidv7805)
ident string fix
--- Added comments ---  uidv7805 [Apr 27, 2015 2:36:58 PM CEST]
Change Package : 329312:2 http://mks-psad:7002/im/viewissue?selection=329312
Revision 1.61 2015/04/23 08:44:17CEST Ahmed, Zaheer (uidu7634)
bug fixes in get_measurement() to grab correct substring
--- Added comments ---  uidu7634 [Apr 23, 2015 8:44:18 AM CEST]
Change Package : 328856:1 http://mks-psad:7002/im/viewissue?selection=328856
Revision 1.60 2015/04/22 11:52:52CEST Ahmed, Zaheer (uidu7634)
fixed to ignore fileserver host name of fileserver or the driver letter in case of local path
--- Added comments ---  uidu7634 [Apr 22, 2015 11:52:52 AM CEST]
Change Package : 328856:1 http://mks-psad:7002/im/viewissue?selection=328856
Revision 1.59 2015/03/25 14:25:09CET Mertens, Sven (uidv7805)
removing column defines again
--- Added comments ---  uidv7805 [Mar 25, 2015 2:25:10 PM CET]
Change Package : 319735:4 http://mks-psad:7002/im/viewissue?selection=319735
Revision 1.58 2015/03/20 14:31:46CET Mertens, Sven (uidv7805)
adding new column name defines
--- Added comments ---  uidv7805 [Mar 20, 2015 2:31:47 PM CET]
Change Package : 319735:1 http://mks-psad:7002/im/viewissue?selection=319735
Revision 1.57 2015/03/09 11:52:10CET Ahmed, Zaheer (uidu7634)
passing error_tolerance as keyword argument
--- Added comments ---  uidu7634 [Mar 9, 2015 11:52:11 AM CET]
Change Package : 314217:1 http://mks-psad:7002/im/viewissue?selection=314217
Revision 1.56 2015/03/05 15:02:01CET Mertens, Sven (uidv7805)
another doc update
--- Added comments ---  uidv7805 [Mar 5, 2015 3:02:02 PM CET]
Change Package : 312989:1 http://mks-psad:7002/im/viewissue?selection=312989
Revision 1.55 2015/03/05 14:59:41CET Mertens, Sven (uidv7805)
underline missing
--- Added comments ---  uidv7805 [Mar 5, 2015 2:59:42 PM CET]
Change Package : 312989:1 http://mks-psad:7002/im/viewissue?selection=312989
Revision 1.54 2015/03/05 14:27:51CET Mertens, Sven (uidv7805)
using keyword is better
--- Added comments ---  uidv7805 [Mar 5, 2015 2:27:53 PM CET]
Change Package : 312989:1 http://mks-psad:7002/im/viewissue?selection=312989
Revision 1.53 2015/03/03 19:31:10CET Hospes, Gerd-Joachim (uidv8815)
fix from Sven
--- Added comments ---  uidv8815 [Mar 3, 2015 7:31:10 PM CET]
Change Package : 312988:1 http://mks-psad:7002/im/viewissue?selection=312988
Revision 1.52 2015/02/26 15:50:11CET Mertens, Sven (uidv7805)
- new method 'get_collections_details',
- new mehod 'get_measurements_number'
--- Added comments ---  uidv7805 [Feb 26, 2015 3:50:12 PM CET]
Change Package : 310834:1 http://mks-psad:7002/im/viewissue?selection=310834
Revision 1.51 2015/02/13 10:28:48CET Ahmed, Zaheer (uidu7634)
bug fix in add_measurement() checking existing recording with filename is ambigious
--- Added comments ---  uidu7634 [Feb 13, 2015 10:28:49 AM CET]
Change Package : 296838:1 http://mks-psad:7002/im/viewissue?selection=296838
Revision 1.50 2015/02/06 11:57:14CET Mertens, Sven (uidv7805)
fix for measurement_id
--- Added comments ---  uidv7805 [Feb 6, 2015 11:57:14 AM CET]
Change Package : 303748:1 http://mks-psad:7002/im/viewissue?selection=303748
Revision 1.49 2015/02/06 08:07:43CET Mertens, Sven (uidv7805)
using absolute imports
--- Added comments ---  uidv7805 [Feb 6, 2015 8:07:44 AM CET]
Change Package : 303748:1 http://mks-psad:7002/im/viewissue?selection=303748
Revision 1.48 2015/02/03 17:22:52CET Mertens, Sven (uidv7805)
using basename instead of whole path to grab ID
--- Added comments ---  uidv7805 [Feb 3, 2015 5:22:53 PM CET]
Change Package : 302778:1 http://mks-psad:7002/im/viewissue?selection=302778
Revision 1.47 2015/02/03 16:36:23CET Mertens, Sven (uidv7805)
update for rec file path
--- Added comments ---  uidv7805 [Feb 3, 2015 4:36:24 PM CET]
Change Package : 302778:1 http://mks-psad:7002/im/viewissue?selection=302778
Revision 1.46 2015/01/28 08:31:32CET Mertens, Sven (uidv7805)
fix for subscheme version
--- Added comments ---  uidv7805 [Jan 28, 2015 8:31:33 AM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.45 2015/01/27 11:23:47CET Ahmed, Zaheer (uidu7634)
bug fix in get_file_state()
--- Added comments ---  uidu7634 [Jan 27, 2015 11:23:48 AM CET]
Change Package : 283686:1 http://mks-psad:7002/im/viewissue?selection=283686
Revision 1.44 2015/01/27 11:18:04CET Ahmed, Zaheer (uidu7634)
Remove get next Id for add_file_state()
--- Added comments ---  uidu7634 [Jan 27, 2015 11:18:04 AM CET]
Change Package : 283686:1 http://mks-psad:7002/im/viewissue?selection=283686
Revision 1.43 2015/01/19 14:25:17CET Ahmed, Zaheer (uidu7634)
removed get next ID usage specially for oracle due to migration.
add_measurement, add_collection, add_collection_map,
add_keyword, add_keyword_map, add_country, add_location, add_vehicle
The next is generated automatically from database sequence
--- Added comments ---  uidu7634 [Jan 19, 2015 2:25:18 PM CET]
Change Package : 283686:1 http://mks-psad:7002/im/viewissue?selection=283686
Revision 1.42 2015/01/19 11:04:59CET Ahmed, Zaheer (uidu7634)
add new function activate_collection(), is_collection_active(),
deactivate_collection(), update_collection_active_flag()
to support collection active inactive feature
--- Added comments ---  uidu7634 [Jan 19, 2015 11:04:59 AM CET]
Change Package : 283678:1 http://mks-psad:7002/im/viewissue?selection=283678
Revision 1.41 2014/12/09 10:48:43CET Mertens, Sven (uidv7805)
too much fixes for typejoin
--- Added comments ---  uidv7805 [Dec 9, 2014 10:48:43 AM CET]
Change Package : 281273:1 http://mks-psad:7002/im/viewissue?selection=281273
Revision 1.40 2014/12/09 10:43:08CET Mertens, Sven (uidv7805)
some more alignment
--- Added comments ---  uidv7805 [Dec 9, 2014 10:43:09 AM CET]
Change Package : 281273:1 http://mks-psad:7002/im/viewissue?selection=281273
Revision 1.39 2014/12/08 17:29:53CET Mertens, Sven (uidv7805)
removing init call
--- Added comments ---  uidv7805 [Dec 8, 2014 5:29:54 PM CET]
Change Package : 281273:1 http://mks-psad:7002/im/viewissue?selection=281273
Revision 1.38 2014/12/08 08:43:28CET Mertens, Sven (uidv7805)
something went wrong?
--- Added comments ---  uidv7805 [Dec 8, 2014 8:43:29 AM CET]
Change Package : 281273:1 http://mks-psad:7002/im/viewissue?selection=281273
Revision 1.37 2014/12/08 08:35:01CET Mertens, Sven (uidv7805)
deprecation name update
--- Added comments ---  uidv7805 [Dec 8, 2014 8:35:02 AM CET]
Change Package : 281273:1 http://mks-psad:7002/im/viewissue?selection=281273
Revision 1.35 2014/11/05 15:29:12CET Ahmed, Zaheer (uidu7634)
import export of bpl is now supported with absolute and relative time stamp
added generic function get measurement and changed other to resuse it
--- Added comments ---  uidu7634 [Nov 5, 2014 3:29:13 PM CET]
Change Package : 274722:1 http://mks-psad:7002/im/viewissue?selection=274722
Revision 1.34 2014/10/21 21:00:10CEST Ahmed, Zaheer (uidu7634)
Added section feature for export bpl for collection method
--- Added comments ---  uidu7634 [Oct 21, 2014 9:00:10 PM CEST]
Change Package : 273583:1 http://mks-psad:7002/im/viewissue?selection=273583
Revision 1.33 2014/09/09 13:48:43CEST Dintzer, Philippe (dintzerp)
- add function to get hash content of a recording
--- Added comments ---  dintzerp [Sep 9, 2014 1:48:43 PM CEST]
Change Package : 254432:2 http://mks-psad:7002/im/viewissue?selection=254432
Revision 1.32 2014/08/22 10:30:22CEST Ahmed, Zaheer (uidu7634)
Improve epy documentation
--- Added comments ---  uidu7634 [Aug 22, 2014 10:30:23 AM CEST]
Change Package : 245349:2 http://mks-psad:7002/im/viewissue?selection=245349
Revision 1.31 2014/08/04 16:31:13CEST Hecker, Robert (heckerr)
Moved cat to new naming convensions.
--- Added comments ---  heckerr [Aug 4, 2014 4:31:13 PM CEST]
Change Package : 253983:1 http://mks-psad:7002/im/viewissue?selection=253983
Revision 1.30 2014/07/31 11:55:33CEST Hecker, Robert (heckerr)
Changed to correct Bpl Interface.
--- Added comments ---  heckerr [Jul 31, 2014 11:55:33 AM CEST]
Change Package : 252989:1 http://mks-psad:7002/im/viewissue?selection=252989
Revision 1.29 2014/06/24 13:22:11CEST Mertens, Sven (uidv7805)
need for error tolerance inside BaseDB
--- Added comments ---  uidv7805 [Jun 24, 2014 1:22:11 PM CEST]
Change Package : 243817:1 http://mks-psad:7002/im/viewissue?selection=243817
Revision 1.28 2014/06/24 10:34:17CEST Mertens, Sven (uidv7805)
alignment db_common / rec cat manager
--- Added comments ---  uidv7805 [Jun 24, 2014 10:34:17 AM CEST]
Change Package : 243817:1 http://mks-psad:7002/im/viewissue?selection=243817
Revision 1.27 2014/05/16 11:59:01CEST Ahmed, Zaheer (uidu7634)
Add pre select filter coll_name in GetMeasurementCollectionNames()
--- Added comments ---  uidu7634 [May 16, 2014 11:59:02 AM CEST]
Change Package : 236953:1 http://mks-psad:7002/im/viewissue?selection=236953
Revision 1.26 2014/03/20 15:00:27CET Bratoi-EXT, Bogdan-Horia (uidu8192)
- bug fixing small problems in the Interface implementation for Priorization of collections
--- Added comments ---  uidu8192 [Mar 20, 2014 3:00:27 PM CET]
Change Package : 221494:2 http://mks-psad:7002/im/viewissue?selection=221494
Revision 1.25 2014/03/17 10:37:56CET Ahmed, Zaheer (uidu7634)
pep8/pylint fixes
--- Added comments ---  uidu7634 [Mar 17, 2014 10:37:56 AM CET]
Change Package : 224333:1 http://mks-psad:7002/im/viewissue?selection=224333
Revision 1.24 2014/03/14 15:29:11CET Ahmed, Zaheer (uidu7634)
pylint and pep8 fixes
added function UpdateCollectionPriority(), GetCollectionPriority()
ExportBPLMeasurment(), ExporBPLForCollection()
--- Added comments ---  uidu7634 [Mar 14, 2014 3:29:12 PM CET]
Change Package : 221492:2 http://mks-psad:7002/im/viewissue?selection=221492
Revision 1.23 2013/07/29 09:28:32CEST Raedler, Guenther (uidt9430)
- revert changes of rev. 1.22
--- Added comments ---  uidt9430 [Jul 29, 2013 9:28:32 AM CEST]
Change Package : 191735:1 http://mks-psad:7002/im/viewissue?selection=191735
Revision 1.22 2013/07/04 15:01:42CEST Mertens, Sven (uidv7805)
providing tableSpace to BaseDB for what sub-schema space each module is intended to be responsible
--- Added comments ---  uidv7805 [Jul 4, 2013 3:01:43 PM CEST]
Change Package : 185933:3 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.21 2013/04/26 15:39:09CEST Mertens, Sven (uidv7805)
resolving some pep8 / pylint errors
--- Added comments ---  uidv7805 [Apr 26, 2013 3:39:10 PM CEST]
Change Package : 179495:7 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.20 2013/04/26 10:46:06CEST Mertens, Sven (uidv7805)
moving strIdent
Revision 1.19 2013/04/25 14:35:12CEST Mertens, Sven (uidv7805)
epydoc adaptation to colon instead of at
--- Added comments ---  uidv7805 [Apr 25, 2013 2:35:12 PM CEST]
Change Package : 179495:2 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.17 2013/04/19 13:41:47CEST Hecker, Robert (heckerr)
- adding GetRecFleForMeasid function
--- Added comments ---  uidu8192 [Apr 25, 2013 8:31:57 AM CEST]
Change Package : 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.15 2013/04/05 11:17:40CEST Hospes, Gerd-Joachim (uidv8815)
fix documentation
--- Added comments ---  uidv8815 [Apr 5, 2013 11:17:40 AM CEST]
Change Package : 169590:2 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.14 2013/04/03 08:02:12CEST Mertens, Sven (uidv7805)
pylint: minor error, warnings fix
--- Added comments ---  uidv7805 [Apr 3, 2013 8:02:12 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.13 2013/04/02 10:01:20CEST Raedler, Guenther (uidt9430)
- use logging for all log messages again
- added column names for cat_files
--- Added comments ---  uidt9430 [Apr 2, 2013 10:01:21 AM CEST]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.12 2013/03/27 11:37:24CET Mertens, Sven (uidv7805)
pep8 & pylint: rowalignment and error correction
--- Added comments ---  uidv7805 [Mar 27, 2013 11:37:24 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.11 2013/03/26 16:19:34CET Mertens, Sven (uidv7805)
pylint: using direct imports, no stars any more
--- Added comments ---  uidv7805 [Mar 26, 2013 4:19:34 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.10 2013/03/26 13:00:20CET Mertens, Sven (uidv7805)
reverting error for keyword argument spaces
--- Added comments ---  uidv7805 [Mar 26, 2013 1:00:21 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.9 2013/03/26 11:53:19CET Mertens, Sven (uidv7805)
reworking imports on cat, cl and db_common to start testing with.
--- Added comments ---  uidv7805 [Mar 26, 2013 11:53:19 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.8 2013/03/21 17:22:38CET Mertens, Sven (uidv7805)
solving some pylint warnings / errors
--- Added comments ---  uidv7805 [Mar 21, 2013 5:22:39 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.7 2013/03/04 07:41:35CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 4, 2013 7:41:35 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.6 2013/02/28 08:12:14CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:14 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.5 2013/02/27 14:51:10CET Hecker, Robert (heckerr)
Updated regarding Pep8 partly.
--- Added comments ---  heckerr [Feb 27, 2013 2:51:11 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2013/02/26 20:10:33CET Raedler, Guenther (uidt9430)
- Updates after Pep8 Styleguides
--- Added comments ---  uidt9430 [Feb 26, 2013 8:10:33 PM CET]
Change Package: 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.3 2013/02/19 14:07:25CET Raedler, Guenther (uidt9430)
- database interface classes derives from common classes for oracle, ...
- use common exception classes
- use common db functions
--- Added comments ---  uidt9430 [Feb 19, 2013 2:07:26 PM CET]
Change Package: 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.2 2013/02/11 10:09:51CET Raedler, Guenther (uidt9430)
- fixed wrong intension in comment section
--- Added comments ---  uidt9430 [Feb 11, 2013 10:09:53 AM CET]
Change Package: 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/02/11 09:55:37CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/
    04_Engineering/stk/db/cat/project.pj
------------------------------------------------------------------------------
-- From CGEB Archive
------------------------------------------------------------------------------
Revision 1.52 2012/10/19 10:40:04CEST Hammernik-EXT, Dmitri (uidu5219)
- changed type of the return value in GetCountryID function
--- Added comments ---  uidu5219 [Oct 19, 2012 10:40:05 AM CEST]
Change Package: 163367:1 http://mks-psad:7002/im/viewissue?selection=163367
Revision 1.51 2012/08/21 10:08:27CEST Sav, Claudiu (uid95402)
Updated GetCollectionMeasurements - it can also return a dictionary with MeasID and FilePath.
--- Added comments ---  uid95402 [Aug 21, 2012 10:08:31 AM CEST]
Change Package: 93290:1 http://mks-psad:7002/im/viewissue?selection=93290
Revision 1.50 2012/07/06 15:24:33CEST Spruck, Jochen (spruckj)
Add get Collection time,
Correct location info and location name interface regarding the db struct
--- Added comments ---  spruckj [Jul 6, 2012 3:24:33 PM CEST]
Change Package: 98074:5 http://mks-psad:7002/im/viewissue?selection=98074
Revision 1.49 2012/04/23 10:55:52CEST Bratoi, Bogdan-Horia (uidu8192)
Override the WHERE IN limitations from Oracle
--- Added comments ---  uidu8192 [Apr 23, 2012 10:55:56 AM CEST]
Change Package: 112275:1 http://mks-psad:7002/im/viewissue?selection=112275
Revision 1.48 2012/03/20 11:10:45CET Spruck, Jochen (spruckj)
Add funktion to get the collection kilometers
--- Added comments ---  spruckj [Mar 20, 2012 11:10:45 AM CET]
Change Package: 98074:2 http://mks-psad:7002/im/viewissue?selection=98074
Revision 1.47 2012/03/02 13:49:04CET Bratoi, Bogdan-Horia (uidu8192)
Added some new functions.
- GetCollectionHoursKilometerPerRoadtype(self,collection_name)
- GetCollectionHoursKilometerPerRecdate(self,collection_name)
- GetCollectionHoursKilometerPerDriver(self,collection_name)
Updated functions: GetCollectionHoursKilometerPerVehicle
Removed function: GetCollectionHoursPerSoftwareVersion
Supporting 2 new columns in CAT_FILES (RECDRIVENDIST, RECODOSTARTDIST)
--- Added comments ---  uidu8192 [Mar 2, 2012 1:49:07 PM CET]
Change Package: 100767:1 http://mks-psad:7002/im/viewissue?selection=100767
Revision 1.46 2012/02/06 08:23:58CET Raedler Guenther (uidt9430) (uidt9430)
- cast new ID as integer value
--- Added comments ---  uidt9430 [Feb 6, 2012 8:23:59 AM CET]
Change Package: 95134:1 http://mks-psad:7002/im/viewissue?selection=95134
Revision 1.45 2011/12/22 17:33:47CET Castell, Christoph (uidt6394)
Added two new functions. GetCollectionHoursPerSoftwareVersion() and GetCollectionHoursPerVehicle().
--- Added comments ---  uidt6394 [Dec 22, 2011 5:33:47 PM CET]
Change Package: 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.44 2011/12/12 10:29:00CET Castell, Christoph (uidt6394)
Fixed bug in GetMeasurementWithSections() function.
Revision 1.43 2011/12/08 18:18:39CET Froehlich, Dominik01 (froehlichd1)
* change: removed CheckMeasurementAvailability because its redundant with HasMeasurement
--- Added comments ---  froehlichd1 [Dec 8, 2011 6:18:39 PM CET]
Change Package: 45990:65 http://mks-psad:7002/im/viewissue?selection=45990
Revision 1.40 2011/10/26 15:00:27CEST Castell Christoph (uidt6394) (uidt6394)
Added code to GetCollectionMeasurements() to remove duplicates.
--- Added comments ---  uidt6394 [Oct 26, 2011 3:00:30 PM CEST]
Change Package: 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.39 2011/10/07 14:25:03CEST Castell Christoph (uidt6394) (uidt6394)
Added DeleteCollectionMap function.
--- Added comments ---  uidt6394 [Oct 7, 2011 2:25:03 PM CEST]
Change Package: 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.38 2011/09/22 13:45:00CEST Castell Christoph (uidt6394) (uidt6394)
Added:
HasMeasurement(self, filepath)
GetMeasurementWithSections(self, measid, collid=None)
functions.
--- Added comments ---  uidt6394 [Sep 22, 2011 1:45:01 PM CEST]
Change Package: 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.37 2011/09/07 19:11:34CEST Ibrouchene Nassim (uidt5589) (uidt5589)
Deleted GetTotalDuration and GetListOfFiles functions
--- Added comments ---  uidt5589 [Sep 7, 2011 7:11:35 PM CEST]
Change Package: 69072:2 http://mks-psad:7002/im/viewissue?selection=69072
Revision 1.36 2011/08/29 16:45:11CEST Ibrouchene Nassim (uidt5589) (uidt5589)
Added GetListOfFiles() and GetTotalDuration() functions
--- Added comments ---  uidt5589 [Aug 29, 2011 4:45:12 PM CEST]
Change Package: 69072:2 http://mks-psad:7002/im/viewissue?selection=69072
Revision 1.35 2011/08/24 09:26:25CEST Hanel Nele (haneln) (haneln)
add again changes from Rev. 1.27, which got lost somehow
--- Added comments ---  haneln [Aug 24, 2011 9:26:26 AM CEST]
Change Package: 70482:6 http://mks-psad:7002/im/viewissue?selection=70482
Revision 1.34 2011/08/19 10:31:31CEST Raedler Guenther (uidt9430) (uidt9430)
-- fixed wrong column selection when using qualified column names in select statement - use alias
--- Added comments ---  uidt9430 [Aug 19, 2011 10:31:32 AM CEST]
Change Package: 67780:2 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.33 2011/08/18 13:57:38CEST Froehlich Dominik (froehlichd1) (froehlichd1)
* fix: fixed qualified column names in get collection measurements
--- Added comments ---  froehlichd1 [Aug 18, 2011 1:57:39 PM CEST]
Change Package: 45990:62 http://mks-psad:7002/im/viewissue?selection=45990
Revision 1.32 2011/08/18 09:18:07CEST Froehlich Dominik (froehlichd1) (froehlichd1)
* added data integrity tests to table export and catalog
Revision 1.31 2011/08/12 14:51:00CEST Froehlich Dominik (froehlichd1) (froehlichd1)
* fix: fixed bug with adding files to collections
--- Added comments ---  froehlichd1 [Aug 12, 2011 2:51:01 PM CEST]
Change Package: 45990:56 http://mks-psad:7002/im/viewissue?selection=45990
Revision 1.30 2011/08/11 20:04:04CEST Froehlich Dominik (froehlichd1) (froehlichd1)
* fix: added distinct for colelction measurements due to section functionality
--- Added comments ---  froehlichd1 [Aug 11, 2011 8:04:04 PM CEST]
Change Package: 45990:53 http://mks-psad:7002/im/viewissue?selection=45990
Revision 1.29 2011/08/11 19:58:30CEST Froehlich Dominik (froehlichd1) (froehlichd1)
* fix: fixed add collection map check of duplicate sections
* add: added insert of batches incl. sections to collections
Revision 1.28 2011/08/11 15:40:49CEST Froehlich Dominik (froehlichd1) (froehlichd1)
* fix: fixed columns in get colelction measurements method
--- Added comments ---  froehlichd1 [Aug 11, 2011 3:40:49 PM CEST]
Change Package: 45990:49 http://mks-psad:7002/im/viewissue?selection=45990
Revision 1.26.1.1 2011/08/11 15:38:50CEST Froehlich Dominik (froehlichd1) (froehlichd1)
* fix: fixed columns in get collection measurements method
--- Added comments ---  froehlichd1 [Aug 11, 2011 3:38:50 PM CEST]
Change Package: 45990:49 http://mks-psad:7002/im/viewissue?selection=45990
Revision 1.26 2011/07/11 09:22:17CEST Spruck Jochen (spruckj) (spruckj)
Add function to get all collection names
--- Added comments ---  spruckj [Jul 11, 2011 9:22:19 AM CEST]
Change Package: 69027:1 http://mks-psad:7002/im/viewissue?selection=69027
Revision 1.25 2011/07/07 09:14:46CEST Raedler Guenther (uidt9430) (uidt9430)
-- fixed bug in GetComponentIDs(). It returns the correct list of childs now
--- Added comments ---  uidt9430 [Jul 7, 2011 9:14:47 AM CEST]
Change Package: 67780:5 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.24 2011/06/17 08:30:56CEST Raedler Guenther (uidt9430) (uidt9430)
- fixed error when rec files is assigned to more than 1 collection
--- Added comments ---  uidt9430 [Jun 17, 2011 8:30:57 AM CEST]
Change Package: 67780:3 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.23 2011/06/14 13:40:51CEST Spruck Jochen (spruckj) (spruckj)
add additional function, get all collection names assigned to a recording
Revision 1.22 2011/03/10 09:21:51CET Froehlich Dominik (froehlichd1) (froehlichd1)
* added missing columns
--- Added comments ---  froehlichd1 [Mar 10, 2011 9:21:52 AM CET]
Change Package: 33544:84 http://mks-psad:7002/im/viewissue?selection=33544
Revision 1.21 2011/02/16 10:00:43CET Froehlich Dominik (froehlichd1) (froehlichd1)
* fixed missing GetLocationID
--- Added comments ---  froehlichd1 [Feb 16, 2011 10:00:43 AM CET]
Change Package: 30321:300 http://mks-psad:7002/im/viewissue?selection=30321
Revision 1.20 2011/01/20 15:43:54CET Norman Apel (apeln)
- add CAT subscheme prefix to table names
--- Added comments ---  apeln [Jan 20, 2011 3:43:55 PM CET]
Change Package: 43037:6 http://mks-psad:7002/im/viewissue?selection=43037
Revision 1.19 2010/11/18 19:59:04CET Dominik Froehlich (froehlichd1)
* fix: corrected support of Oracle date/time format strings
* change: added support of error tolerance levels in rec catalog library
--- Added comments ---  froehlichd1 [Nov 18, 2010 7:59:04 PM CET]
Change Package: 45990:36 http://mks-psad:7002/im/viewissue?selection=45990
Revision 1.18 2010/11/18 17:35:54CET Dominik Froehlich (froehlichd1)
* change: support special date time format per dbms
Revision 1.17 2010/09/27 10:06:19CEST Dominik Froehlich (froehlichd1)
* change: implemented update function
Revision 1.16 2010/09/24 13:50:19CEST Dominik Froehlich (froehlichd1)
* fix: fixed add file command
* add: added update file command
* add: added update coll command
* add: added update kw command
Revision 1.15 2010/09/20 12:30:02CEST Dominik Froehlich (froehlichd1)
* corercted GetXXName methods of db_reccatalog.py
Revision 1.14 2010/09/17 15:09:00CEST Dominik Froehlich (froehlichd1)
* add aprtcfg
* add vehcfgstate
* add parttype
* diverse fixes
* list cmds not adapted yet
--- Added comments ---  froehlichd1 [Sep 17, 2010 3:09:01 PM CEST]
Change Package: 45990:25 http://mks-psad:7002/im/viewissue?selection=45990
Revision 1.13 2010/07/14 11:57:14CEST Dominik Froehlich (froehlichd1)
* update
--- Added comments ---  froehlichd1 [Jul 14, 2010 11:57:15 AM CEST]
Change Package: 45990:20 http://fras236:8002/im/viewissue?selection=45990
Revision 1.12 2010/07/06 12:45:11CEST Dominik Froehlich (dfroehlich)
* added list for vehicle cfgs
* added list for part cfgs
--- Added comments ---  dfroehlich [2010/07/06 10:45:11Z]
Change Package: 45990:19 http://LISS014:6001/im/viewissue?selection=45990
Revision 1.11 2010/07/05 11:56:07CEST Dominik Froehlich (dfroehlich)
* implemented list cmd for keywords an collections
--- Added comments ---  dfroehlich [2010/07/05 09:56:08Z]
Change Package: 45990:17 http://LISS014:6001/im/viewissue?selection=45990
Revision 1.10 2010/07/01 14:05:52CEST Dominik Froehlich (dfroehlich)
* support of location info
--- Added comments ---  dfroehlich [2010/07/01 12:05:52Z]
Change Package: 45990:12 http://LISS014:6001/im/viewissue?selection=45990
Revision 1.9 2010/07/01 11:37:42CEST Dominik Froehlich (dfroehlich)
* update
--- Added comments ---  dfroehlich [2010/07/01 09:37:42Z]
Change Package: 45990:11 http://LISS014:6001/im/viewissue?selection=45990
Revision 1.8 2010/06/30 17:26:53CEST Dominik Froehlich (dfroehlich)
* cleanup
--- Added comments ---  dfroehlich [2010/06/30 15:26:53Z]
Change Package: 45990:10 http://LISS014:6001/im/viewissue?selection=45990
Revision 1.7 2010/06/30 10:39:12CEST Dominik Froehlich (dfroehlich)
* add: support of keyword to collection insertion
--- Added comments ---  dfroehlich [2010/06/30 08:39:13Z]
Change Package: 45990:6 http://LISS014:6001/im/viewissue?selection=45990
Revision 1.6 2010/06/29 17:16:52CEST Dominik Froehlich (dfroehlich)
* change: support vehicle configurations
--- Added comments ---  dfroehlich [2010/06/29 15:16:52Z]
Change Package: 45990:8 http://LISS014:6001/im/viewissue?selection=45990
Revision 1.5 2010/06/28 17:13:02CEST Dominik Froehlich (dfroehlich)
* add: support of file->coll assoc.
* add: support of kw->file assoc.
--- Added comments ---  dfroehlich [2010/06/28 15:13:02Z]
Change Package: 45990:5 http://LISS014:6001/im/viewissue?selection=45990
Revision 1.4 2010/06/28 09:34:14CEST Dominik Froehlich (dfroehlich)
* update
--- Added comments ---  dfroehlich [2010/06/28 07:34:14Z]
Change Package: 45990:5 http://LISS014:6001/im/viewissue?selection=45990
Revision 1.3 2010/06/25 14:22:12CEST Dominik Froehlich (dfroehlich)
* update
--- Added comments ---  dfroehlich [2010/06/25 12:22:12Z]
Change Package: 45990:3 http://LISS014:6001/im/viewissue?selection=45990
Revision 1.2 2010/06/18 16:01:24CEST Dominik Froehlich (dfroehlich)
* update
--- Added comments ---  dfroehlich [2010/06/18 14:01:24Z]
Change Package: 45990:2 http://LISS014:6001/im/viewissue?selection=45990
Revision 1.1 2010/06/17 13:30:10CEST Dominik Froehlich (dfroehlich)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/Base_CGEB/06_Algorithm/04_Engineering/
    02_Development_Tools/scripts/project.pj
"""
