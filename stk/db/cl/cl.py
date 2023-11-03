"""
db_cldata.py
-------------

Python library to access Constraint Label database schema

Sub-Scheme CL

**User-API**
    - `BaseCLDB`
        Providing methods to add, read and modify constraint labels

The other classes in this module are handling the different DB types and are derived from BaseRecCatalogDB.

**usage in Valf suites**

For validation suites based on `Valf` class there is the operator `DbLinker` setting up all needed connections.

**using several connections in parallel**

If several sub-schemes have to be used in parallel the first connection should be reused.
Please check class `BaseCLDB` for more detail.

**Do not waste the limited number of connections to Oracle DB**
by setting up a new connection for each sub-scheme,
always use the existing one as described in `BaseCLDB`.


:org:           Continental AG
:author:        Sven Mertens

:version:       $Revision: 1.5 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 16:01:35CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from datetime import datetime
from copy import deepcopy
from warnings import warn

# - import STK Modules ------------------------------------------------------------------------------------------------
from stk.db.db_sql import GenericSQLStatementFactory, SQLTableExpr, SQLBinaryExpr, SQLColumnExpr, OP_EQ, \
    SQLIntegral, OP_LIKE, SQLString, SQLFuncExpr, OP_AS, OP_IN, GenericSQLSelect
from stk.db.db_common import BaseDB, PluginBaseDB
from stk.valf.signal_defs import DBCL

from stk.util.trie import CTrie

# =====================================================================================================================
# Constants
# =====================================================================================================================

# Table base names:
TABLE_NAME_SIG_CONSIG = "CL_ConsSignals"
TABLE_NAME_SIG_SIGCON = "CL_SigConstraints"
TABLE_NAME_SIG_CONMAP = "CL_ConstraintMap"
TABLE_NAME_SIG_CONSET = "CL_ConstraintSets"
TABLE_NAME_SIG_TRIG = "CL_Triggers"

#  Column base names:
# TABLE_NAME_SIG_CONSIG:
COL_NAME_CONSIG_SIGNALID = "SIGNALID"
COL_NAME_CONSIG_NAME = "NAME"
COL_NAME_CONSIG_DERIVED = "DERIVED"
COL_NAME_CONSIG_STATE = "STATEID"
COL_NAME_CONSIG_MODTIME = "MODTIME"

# TABLE_NAME_SIG_SIGCON:
COL_NAME_SIGCON_CONSID = "CONSID"
COL_NAME_SIGCON_MEASID = "MEASID"
COL_NAME_SIGCON_TRIGGERID = "TRIGGERID"
COL_NAME_SIGCON_SIGNALID = "SIGNALID"
COL_NAME_SIGCON_BEGINTS = "BEGINTS"
COL_NAME_SIGCON_ENDTS = "ENDTS"
COL_NAME_SIGCON_UPPERTOL = "UPPERTOL"
COL_NAME_SIGCON_LOWERTOL = "LOWERTOL"
COL_NAME_SIGCON_COEFA = "COEFFA"
COL_NAME_SIGCON_COEFB = "COEFFB"
COL_NAME_SIGCON_MINSAMPLES = "MINSAMPLES"
COL_NAME_SIGCON_MAXSAMPLES = "MAXSAMPLES"
COL_NAME_SIGCON_COMMENT = "COMMENTS"

COL_NAMES_SIGCON = [COL_NAME_SIGCON_CONSID,
                    COL_NAME_SIGCON_MEASID,
                    COL_NAME_SIGCON_TRIGGERID,
                    COL_NAME_SIGCON_SIGNALID,
                    COL_NAME_SIGCON_BEGINTS,
                    COL_NAME_SIGCON_ENDTS,
                    COL_NAME_SIGCON_UPPERTOL,
                    COL_NAME_SIGCON_LOWERTOL,
                    COL_NAME_SIGCON_COEFA,
                    COL_NAME_SIGCON_COEFB,
                    COL_NAME_SIGCON_MINSAMPLES,
                    COL_NAME_SIGCON_MAXSAMPLES]

INTEGER_NOT_NULL = 'INTEGER_NOT_NULL'
FLOAT_NOT_NULL = 'FLOAT_NOT_NULL'

SIGCON_TEMPLATE = {COL_NAME_SIGCON_CONSID: None,
                   COL_NAME_SIGCON_MEASID: None,
                   COL_NAME_SIGCON_TRIGGERID: None,
                   COL_NAME_SIGCON_SIGNALID: 'INT_OR_STR',
                   COL_NAME_SIGCON_BEGINTS: INTEGER_NOT_NULL,
                   COL_NAME_SIGCON_ENDTS: INTEGER_NOT_NULL,
                   COL_NAME_SIGCON_UPPERTOL: FLOAT_NOT_NULL,
                   COL_NAME_SIGCON_LOWERTOL: FLOAT_NOT_NULL,
                   COL_NAME_SIGCON_COEFA: FLOAT_NOT_NULL,
                   COL_NAME_SIGCON_COEFB: FLOAT_NOT_NULL,
                   COL_NAME_SIGCON_MINSAMPLES: INTEGER_NOT_NULL,
                   COL_NAME_SIGCON_MAXSAMPLES: INTEGER_NOT_NULL}

# TABLE_NAME_SIG_CONMAP:
COL_NAME_CONMAP_MAPID = "MAPID"
COL_NAME_CONMAP_SETID = "SETID"
COL_NAME_CONMAP_CONSID = "CONSID"

# TABLE_NAME_SIG_CONSET:
COL_NAME_CONSET_SETID = "SETID"
COL_NAME_CONSET_PARENTID = "PARENTID"
COL_NAME_CONSET_NAME = "NAME"
COL_NAME_CONSET_MEASID = "MEASID"
COL_NAME_CONSET_COMMENT = "COMMENTS"
COL_NAME_CONSET_SETOP = "OPERANT"
COL_NAME_CONSET_MODTIME = "MODTIME"

# TABLE_NAME_SIG_TRIG:
COL_NAME_TRIGGERS_TRIGGERID = "TRIGGERID"
COL_NAME_TRIGGERS_PARENTID = "PARENTID"
COL_NAME_TRIGGERS_SIGNALID = "SIGNALID"
COL_NAME_TRIGGERS_VALUE = "VALUE"
COL_NAME_TRIGGERS_OPERANT = "OPERANT"
COL_NAME_TRIGGERS_COND = "CONDITION"
COL_NAME_TRIGGERS_USAGE = "USAGE"

IDENT_STRING = DBCL

# TODO: how to initialize consTrie? rework trie/kid structure
KID_NAME_SETID = 'SetID'
KID_NAME_KIDIDS = 'KidIDs'
KID_NAME_SETNAME = 'SetName'

KID_VALUENAME_OPERANT = 'Operant'
KID_VALUENAME_CONSTRAINTS = 'Constraints'
KID_VALUENAME_SIGNALS = 'Signals'

KID_VALUENAME_COMP_RESULTS = 'Compare_results'
KID_VALUENAME_COMP_DETAILS = 'Compare_details'
KID_VALUENAME_COMP_SUM = 'Compare_summary'

KID_DEFAULT_COMP_RESULTS = {KID_VALUENAME_COMP_DETAILS: [], KID_VALUENAME_COMP_SUM: None}

SIGCON_DEFAULT_TRIGGER = 'Timestamp'


# --- this should go to db_common ----------------------------------------------
COL_NAME_LAST_ROWID = "ROWID"
STMT_LAST_ROWID_SQLITE = "last_insert_rowid"

# TODO: if define functions to return last inserted row id does not work,
# get GetGenericMaxValue working
DB_FUNC_NAME_MAX = "DB_FUNC_NAME_MAX"


CL_OP_AND = 0
CL_OP_OR = 1
CL_OP_XOR = 2
CL_OP_NAND = 3
CL_OP_NOR = 4

CL_OP_FUNC_MAP = {CL_OP_AND: 'not False in %s',
                  CL_OP_OR: 'True in %s',
                  CL_OP_XOR: '%s.count(True)==1',
                  CL_OP_NAND: 'False in %s',
                  CL_OP_NOR: 'not True in %s'}

CL_OP_NAME_MAP = {CL_OP_AND: 'AND',
                  CL_OP_OR: 'OR',
                  CL_OP_XOR: 'XOR',
                  CL_OP_NAND: 'NAND',
                  CL_OP_NOR: 'NOR'}


class BaseCLDBException(StandardError):
    """Base of all cl errors"""
    pass

# ===============================================================================
# Constraint DB Libary Base Implementation
# ===============================================================================

# TODO: change AddGenericData in db_common to return real rowcount
# -> that value can be used to check result, see Rev. 1.40

# TODO: force to build up foreign key connections,
# e.g. ConsSignal <-> SignalConstraint


class BaseCLDB(BaseDB):
    """
    **Base implementation of the CL Database**

    For the first connection to the DB for cat tables just create a new instance of this class like

    .. python::

        from stk.db.cl import BaseCLDB

        dbcl = BaseCLDB("ARS4XX")   # or use "MFC4XX", "VGA" or path/name of sqlite file

    If already some connection to another table of the DB is created use that one to speed up your code:

    .. python::

        dbcl = BaseCLDB(dbxxx.db_connection)

    The connection is closed when the first instance using it is deleted.

    More optional keywords are described at `BaseDB` class initialization.

    """
    def __init__(self, *args, **kwargs):
        """
        Initialize constraint database

        :keyword db_connection: The database connection to be used
        :type db_connection: cx_oracle.Connection, pydodbc.Connection, sqlite3.Connection, sqlce.Connection
        :keyword table_prefix: The table name prefix which is usually master schema name
        :type table_prefix: str
        :keyword sql_factory: SQL Query building factory
        :type sql_factory: GenericSQLStatementFactory
        """
        kwargs['strIdent'] = DBCL
        BaseDB.__init__(self, *args, **kwargs)

    def get_last_row_id(self, column_name, table_name):
        """function to return last rowid by executing last_rowid function
        !!! must be overwritten by derived DB classes depending on DB type !!!
        :return: autoincrement ID
        """
        self._log.warning('Baseclass BaseCLDB has no clean implementation of function getLastRowID(). '
                          'That might lead to an ERROR!!!')

        if column_name is None or table_name is None:
            self._log.error('When using the baseclass implementation column_name and table_name must be given.')

        # def GetGenericMaxValue(self, column_name, table_name):
        """Get maximum value of certain column in a table.
        :param column_name: The name of the column to take the maximum from. [str]
        :param table_name: The name of the table to take the maximum from. [str]

        :return max_value: Maximum value found.
        """
        sql_select_stmt = self._sql_factory.GetSelectBuilder()
        sql_select_stmt.select_list = [SQLFuncExpr(self.db_func_map[DB_FUNC_NAME_MAX], column_name)]
        sql_select_stmt.table_list = [table_name]
        stmt = str(sql_select_stmt)
        # fetch max. value
        max_value = 0
        cursor = self._db_connection.cursor()
        try:
            self._log.debug(stmt)
            cursor.execute(stmt)
            row = cursor.fetchone()
            if (row is not None) and (row[0] is not None):
                max_value = row[0]
        finally:
            cursor.close()
        # done
        return max_value

    def getLastRowID(self, column_name, table_name):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "getLastRowID" is deprecated use '
        msg += '"get_last_row_id" instead'
        warn(msg, stacklevel=2)
        return self.get_last_row_id(column_name, table_name)

    # ===========================================================================
    # Conversion methods
    # ===========================================================================

    # TODO: these methods ever used?
    def _get_one(self, stmt):
        """returns only first row of SQL select execution
        :param stmt: select statement
        :return: fetchone() result
        """
        cursor = self._db_connection.cursor()
        try:
            cursor.execute(stmt)
            res = str(cursor.fetchone()[0])
        finally:
            cursor.close()
        # done
        return res

    def _getOne(self, stmt):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "_getOne" is deprecated use '
        msg += '"_get_one" instead'
        warn(msg, stacklevel=2)
        return self._get_one(stmt)

    def _get_col(self, stmt):
        """returns only first column of SQL select execution
        :param stmt: select statement
        :return: for row in fetchone([0]) result
        """
        cursor = self._db_connection.cursor()
        try:
            res = []
            for row in cursor.execute(stmt):
                res.append(str(row[0]))
        finally:
            cursor.close()
        # done
        return res

    def _getCol(self, stmt):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "_get_col" is deprecated use '
        msg += '"_get_one" instead'
        warn(msg, stacklevel=2)
        return self._get_col(stmt)

    # ===========================================================================
    # Handling of special data
    # ===========================================================================

    def get_constraints(self, cons_set, measid):
        """
        returns related constraint sets for given ConstraintSet

        :param cons_set: constraint set name or ID or None
        :type cons_set: str, int
        :param measid: measurement id from CAT_FILES or None
        :type measid: int
        :return: list of matching constraint sets saved as CTrie elements
        :rtype: list of CTrie
        """
        # get initial constraint set
        cons_list = self.get_constraint_set(cons_set, measid, parents_only=True)

        if len(cons_list) == 0:
            raise BaseCLDBException("WARNING: no matching data found for ConstraintSet %s, measid %s"
                                    % (cons_set, measid))

        cons_trie_list = []
        for cons in cons_list:
            parent_id = cons[COL_NAME_CONSET_SETID]

            sigcons_list = self.get_sig_constraints_per_set(parent_id)

            cons_trie = CTrie(parent_id,
                              None,
                              {KID_VALUENAME_OPERANT: cons[COL_NAME_CONSET_SETOP],
                               KID_VALUENAME_CONSTRAINTS: sigcons_list,
                               KID_NAME_SETNAME: cons[COL_NAME_CONSET_NAME],
                               # KID_VALUENAME_SIGNALS: {},
                               KID_VALUENAME_COMP_RESULTS: deepcopy(KID_DEFAULT_COMP_RESULTS)})

            # get child constraint sets
            cons = [cons]  # convert to list to work in following where condition
            while len(cons) > 0:
                where = COL_NAME_CONSET_PARENTID + ' IN (%s)' % (", ".join([str(p[COL_NAME_CONSET_SETID])
                                                                            for p in cons]))
                cons = self.get_constraint_set(where=where)

                for ccc in cons:
                    sigcons_list = self.get_sig_constraints_per_set(ccc[COL_NAME_CONSET_SETID])

                    # TODO: update to new dict structs
                    cons_trie.add_kid(ccc[COL_NAME_CONSET_SETID],
                                      ccc[COL_NAME_CONSET_PARENTID],
                                      {KID_VALUENAME_OPERANT: ccc[COL_NAME_CONSET_SETOP],
                                       KID_VALUENAME_CONSTRAINTS: sigcons_list,
                                       # KID_VALUENAME_SIGNALS: {},
                                       KID_VALUENAME_COMP_RESULTS: deepcopy(KID_DEFAULT_COMP_RESULTS)})

            cons_trie_list.append(cons_trie)

        return cons_trie_list

    def getConstraints(self, cons_set, measid):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "getConstraints" is deprecated use '
        msg += '"get_constraints" instead'
        warn(msg, stacklevel=2)
        return self.get_constraints(cons_set, measid)

    def add_constraints(self, set_name, meas_id, cons, operant, parent_id=None):
        """inserts new constraint(s) into DB

        :param set_name: name of constraint set to create [str]
        :param meas_id: measurement id to refer to
        :param cons: list of constraints to add, each consisting of
                     [BeginTS, EndTS, UpperTol, LowerTol, CoeffA, CoeffB, MinSamples, MaxSamples, SigName]
        :param operant: operant constraints are connected with
        :return: SetID of just created constraint set
        """

        # check meas_id format
        if not isinstance(meas_id, int):
            raise BaseCLDBException("ERROR: meas_id given is no integer: %s" % str(meas_id))

        # add new signal constraint(s)
        consids = []
        for con in cons:

            # check signal and convert to ID
            sig = self.get_cons_signal(con[COL_NAME_SIGCON_SIGNALID], select=[COL_NAME_CONSIG_SIGNALID])
            if len(sig) == 0:
                if isinstance(con[COL_NAME_SIGCON_SIGNALID], str):
                    sig_id = self.add_cons_signal(con[COL_NAME_SIGCON_SIGNALID])
                    con[COL_NAME_SIGCON_SIGNALID] = sig_id
                else:
                    raise BaseCLDBException('Signal %s missing in table %s'
                                            % (con[COL_NAME_SIGCON_SIGNALID], TABLE_NAME_SIG_CONSIG))
            elif len(sig) == 1:
                sig_id = sig[0][COL_NAME_CONSIG_SIGNALID]
                con[COL_NAME_SIGCON_SIGNALID] = sig_id
            else:
                raise BaseCLDBException("Too many matching signals for %s in table %s"
                                        % (con[COL_NAME_SIGCON_SIGNALID], TABLE_NAME_SIG_CONSIG))

            # add constraint
            consids.append(self.add_sig_constraint(con))

        # add new constraint set if it doesn't exist
        cons = self.get_constraint_set(set_name)
        if cons:
            setid = cons[0]['SETID']
        else:
            setid = self.add_constraint_set(set_name, operant, parent_id=parent_id, meas_id=meas_id)

        # add mappings
        for conid in consids:

            self.add_cons_map(setid, conid)

        return setid

    def addConstraints(self, set_name, meas_id, cons, operant, parent_id=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "addConstraints" is deprecated use '
        msg += '"add_constraints" instead'
        warn(msg, stacklevel=2)
        return self.add_constraints(set_name, meas_id, cons, operant, parent_id)

    # =================================================================================================================
    # Handling of file data
    # =================================================================================================================

    # --- Signal Constraint ---------------------------------------------------------------------------------------
    def add_sig_constraint(self, data_dict):
        """
        Add a new signal constraint record to the database.

        # :param col: column to use: either MeasID (CAT_FILES.MEASID) or TriggerID
        # :param col_id: id of column
        # :param beginTS: BeginTimestamp of measurement: absolut if related to measID, relative if using triggerID
        # :param endTS: EndTimestamp of measurement: length
        # :param upper_tol: upper value tolerance (+deviation)
        # :param lower_tol: lower value tolerance (-deviation)
        # :param coeffa: function coefficient A: y = Ax + B
        # :param coeffb: function coefficient B: y = Ax + B
        # :param min_samples: measurement samples which need to fit at minimum
        # :param max_samples: measurement samples which need to fit at maximum
        :return: ConsID of last added signal constraint
        """

        # check dict values
        for key in data_dict:
            if key not in COL_NAMES_SIGCON:
                self._log.warning('Constraint column %s does not exist in table %s' % (key, TABLE_NAME_SIG_SIGCON))
            elif data_dict[key] is not None and data_dict[key] == SIGCON_TEMPLATE[key]:
                self._log.warning('Constraint column %s has still its default value %s' % (key, data_dict[key]))
                raise BaseCLDBException('Constraint column %s has still its default value %s' % (key, data_dict[key]))

        self.add_generic_data(data_dict, TABLE_NAME_SIG_SIGCON)
        ident = self.get_last_row_id()
        # self.commit()
        return ident

    def addSigConstraint(self, data_dict):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "addSigConstraint" is deprecated use "add_sig_constraint" instead'
        warn(msg, stacklevel=2)
        return self.add_sig_constraint(data_dict)

    # TODO: use dict as input
    def update_sig_constraint(self, cons_id, signal_id, col, col_id, begin_ts,
                              end_ts, upper_tol, lower_tol, coeffa, coeffb,
                              min_samples, max_samples):
        """Add a new signal constraint record to the database.

        :param cons_id: which constraints ID to update
        :param col: column to use: either MeasID (CAT_FILES.MEASID) or TriggerID
        :param col_id: id of column
        :param begin_ts: BeginTimestamp of measurement: absolut if related to measID, relative if using triggerID
        :param end_ts: EndTimestamp of measurement: length
        :param upper_tol: upper value tolerance (+deviation)
        :param lower_tol: lower value tolerance (-deviation)
        :param coeffa: function coefficient A: y = Ax + B
        :param coeffb: function coefficient B: y = Ax + B
        :param min_samples: measurement samples which need to fit at minimum
        :param max_samples: measurement samples which need to fit at maximum
        :return: True if successfull / False if failed
        """
        x = self.UpdateGenericData({COL_NAME_SIGCON_SIGNALID: signal_id, col: col_id, COL_NAME_SIGCON_BEGINTS: begin_ts,
                                    COL_NAME_SIGCON_ENDTS: end_ts, COL_NAME_SIGCON_UPPERTOL: upper_tol,
                                    COL_NAME_SIGCON_LOWERTOL: lower_tol, COL_NAME_SIGCON_COEFA: coeffa,
                                    COL_NAME_SIGCON_COEFB: coeffb, COL_NAME_SIGCON_MINSAMPLES: min_samples,
                                    COL_NAME_SIGCON_MAXSAMPLES: max_samples},
                                   SQLTableExpr(TABLE_NAME_SIG_SIGCON),
                                   where=SQLBinaryExpr(SQLColumnExpr(COL_NAME_SIGCON_CONSID), OP_EQ,
                                                       SQLIntegral(cons_id)))
        if x > 0:
            self.commit()
        return bool(x)

    def updateSigConstraint(self, cons_id, signal_id, col, col_id, begi_ts,  # pylint: disable=C0103
                            end_ts, upper_tol, lower_tol, coeffa, coeffb,
                            min_samples, max_samples):
        """deprecated"""
        msg = 'Method "updateSigConstraint" is deprecated use '
        msg += '"update_sig_constraint" instead'
        warn(msg, stacklevel=2)
        return self.update_sig_constraint(cons_id, signal_id, col, col_id,
                                          begi_ts, end_ts, upper_tol, lower_tol,
                                          coeffa, coeffb, min_samples, max_samples)

    def del_sig_constraint(self, cons_id):
        """deletes a signal constraint record from DB

        :param cons_id: constraint ID to be deleted,
        :return: True if successfull / False if failed
        """
        x = self.DeleteGenericData(SQLTableExpr(TABLE_NAME_SIG_SIGCON),
                                   SQLBinaryExpr(SQLColumnExpr(COL_NAME_SIGCON_CONSID), OP_EQ,
                                                 SQLIntegral(cons_id)))
        if x >= 0:
            self.commit()
        return bool(x)

    def delSigConstraint(self, cons_id):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "delSigConstraint" is deprecated use '
        msg += '"del_sig_constraint" instead'
        warn(msg, stacklevel=2)
        return self.del_sig_constraint(cons_id)

    @staticmethod
    def get_empty_sig_constraint():
        """get empty constraint template to know structure

        :return empty constraint template [dict]
        """
        return deepcopy(SIGCON_TEMPLATE)

    def getEmptySigConstraint(self):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "getEmptySigConstraint" is deprecated use '
        msg += '"get_empty_sig_constraint" instead'
        warn(msg, stacklevel=2)
        return self.get_empty_sig_constraint()

    def get_sig_constraint(self, cons_id):
        """retrieves details from a constraint

        :param cons_id: constraint ID
        :return: list of details
        """
        return self.select_generic_data(table_list=[SQLTableExpr(TABLE_NAME_SIG_SIGCON)],
                                        where=SQLBinaryExpr(SQLColumnExpr(TABLE_NAME_SIG_SIGCON,
                                                                          COL_NAME_SIGCON_CONSID), OP_EQ,
                                                            SQLIntegral(cons_id)))

    def getSigConstraint(self, cons_id):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "getSigConstraint" is deprecated use '
        msg += '"get_sig_constraint" instead'
        warn(msg, stacklevel=2)
        return self.get_sig_constraint(cons_id)

    def get_sig_constraints_per_set(self, set_id):
        """return all constraints that belong directly to a ConstrSet (without Kids)

        :param set_id: ConstraintSet ID [int]
        :return: list with all constraints [list of dicts]
        """

        cons_maps = self.get_cons_map(set_id)

        sigcons_list = []
        for cons_map in cons_maps:
            sigcons = self.get_sig_constraint(cons_map[COL_NAME_CONMAP_CONSID])[0]

            # maybe move this to get_sig_constraint? or keep get_sig_constraint as "base method"
            signalinfo = self.get_cons_signal(sigcons[COL_NAME_CONSIG_SIGNALID])
            signalname = signalinfo[0][COL_NAME_CONSIG_NAME]

            sigcons[COL_NAME_CONSIG_NAME] = signalname

            sigcons_list.append(sigcons)

        return sigcons_list

    def getSigConstraintsPerSet(self, set_id):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "getSigConstraintsPerSet" is deprecated use '
        msg += '"get_sig_constraints_per_set" instead'
        warn(msg, stacklevel=2)
        return self.get_sig_constraints_per_set(set_id)

    # --- Constraint Signal ----------------------------------------------------
    def add_cons_signal(self, signal_name, derived=0, cons_state='I'):
        """add a constraint signal name

        :param signal_name: the name of signal to add
        :param derived: wether the signal is derived
        :param cons_state: initial signal state
        :return: signal_id of just added set
        """
        data_dict = {COL_NAME_CONSIG_NAME: signal_name,
                     COL_NAME_CONSIG_DERIVED: derived,
                     COL_NAME_CONSIG_STATE: cons_state,
                     COL_NAME_CONSIG_MODTIME: datetime.now().isoformat(' ')}

        # check if already exists
        where_condition = COL_NAME_CONSIG_DERIVED + " = " + str(derived)
        where_condition += ' AND ' + COL_NAME_CONSIG_STATE + " = '" + str(cons_state) + "'"
        existing_sig = self.get_cons_signal(signal_name, where=where_condition)
        if len(existing_sig) > 0:
            self._log.warning('Signal %s already in table %s with identical attributes, not registered again.'
                              % (signal_name, TABLE_NAME_SIG_CONSIG))
            ident = existing_sig[0][COL_NAME_CONSIG_SIGNALID]

        # add if not existing
        else:
            self.add_generic_data(data_dict, SQLTableExpr(TABLE_NAME_SIG_CONSIG))
            ident = self.get_last_row_id(None, None)
            # self.commit()

        return ident

    def addConsSignal(self, signal_name, derived=0, cons_state='I'):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "addConsSignal" is deprecated use '
        msg += '"add_cons_signal" instead'
        warn(msg, stacklevel=2)
        return self.add_cons_signal(signal_name, derived, cons_state)

    def update_cons_signal(self, signal_id, signal_name, derived=0, cons_state='I'):
        """add a constraint signal name

        :param signal_id: which signal ID to update
        :param signal_name: the name of signal to add
        :param derived: wether the signal is derived
        :param cons_state: initial signal state
        :return: True if successfull / False if failed
        """
        x = self.UpdateGenericData({COL_NAME_CONSIG_NAME: signal_name, COL_NAME_CONSIG_DERIVED: derived,
                                   COL_NAME_CONSIG_STATE: cons_state,
                                   COL_NAME_CONSIG_MODTIME: datetime.now().isoformat(' ')},
                                   SQLTableExpr(TABLE_NAME_SIG_CONSIG),
                                   where=SQLBinaryExpr(SQLColumnExpr(COL_NAME_CONSIG_SIGNALID), OP_EQ,
                                                       SQLIntegral(signal_id)))
        if x > 0:
            self.commit()
        return bool(x)

    def updateConsSignal(self, signal_id, signal_name, derived=0, cons_state='I'):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "updateConsSignal" is deprecated use '
        msg += '"update_cons_signal" instead'
        warn(msg, stacklevel=2)
        return self.update_cons_signal(signal_id, signal_name, derived, cons_state)

    def del_cons_signal(self, signal):
        """deletes a constraint signal by name or ID

        :param signal: ID or name of signal
        :return: True if successfull / False if failed
        """
        """
        stmt = "DELETE FROM %s WHERE " % TABLE_NAME_SIG_CONSIG
        if isinstance(signal, str):
            stmt += COL_NAME_CONSIG_NAME + " LIKE '" + signal + "'"
        else:
            stmt += COL_NAME_CONSIG_SIGNALID + " = " + str(signal)
        """

        stp = isinstance(signal, str)
        x = self.DeleteGenericData(SQLTableExpr(TABLE_NAME_SIG_CONSIG),
                                   SQLBinaryExpr(SQLColumnExpr(COL_NAME_CONSIG_NAME), OP_LIKE, SQLString(signal))
                                   if stp else SQLBinaryExpr(SQLColumnExpr(COL_NAME_CONSIG_SIGNALID), OP_EQ,
                                                             SQLIntegral(signal)))
        if x >= 0:
            self.commit()
        return bool(x)

    def delConsSignal(self, signal):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "delConsSignal" is deprecated use '
        msg += '"del_cons_signal" instead'
        warn(msg, stacklevel=2)
        return self.del_cons_signal(signal)

    def get_cons_signal(self, signal, select='*', where=None):
        """retrieves details of signal(s)

        :param signal: ID [int] or name [str] of signal
        :return: list of details
        """

        # TODO: replace creation of where_condition?
        where_condition = ''
        if isinstance(signal, str):
            where_condition += COL_NAME_CONSIG_NAME + " LIKE '" + signal + "'"
        else:
            where_condition += COL_NAME_CONSIG_SIGNALID + " = " + str(signal)

        if where is not None:
            if len(where_condition) > 0:
                where_condition += ' AND '
            where_condition += where

        cons_signal = self.select_generic_data(select, table_list=[TABLE_NAME_SIG_CONSIG], where=where_condition)

        return cons_signal

    def getConsSignal(self, signal, select='*', where=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "getConsSignal" is deprecated use '
        msg += '"get_cons_signal" instead'
        warn(msg, stacklevel=2)
        return self.get_cons_signal(signal, select, where)

        # --- Constraint Map ---------------------------------------------------
    def add_cons_map(self, setid, cons_id):
        """adds a constraint map

        :param setid: id of constraint set
        :param cons_id: id of signal constraint
        :return: added mapID
        """
        data_dict = {COL_NAME_CONMAP_SETID: setid,
                     COL_NAME_CONMAP_CONSID: cons_id}

        self.add_generic_data(data_dict, SQLTableExpr(TABLE_NAME_SIG_CONMAP))
        ident = self.get_last_row_id()
        self.commit()
        return ident

    def addConsMap(self, setID, cons_id):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "addConsMap" is deprecated use '
        msg += '"add_cons_map" instead'
        warn(msg, stacklevel=2)
        return self.add_cons_map(setID, cons_id)

    def update_cons_map(self, mapid, setid, cons_id):
        """adds a constraint map

        :param mapid: which map ID to update
        :param setid: id of constraint set
        :param cons_id: id of signal constraint
        :return: True if successfull / False on failure
        """
        x = self.UpdateGenericData({COL_NAME_CONMAP_SETID: setid, COL_NAME_CONMAP_CONSID: cons_id},
                                   SQLTableExpr(TABLE_NAME_SIG_CONMAP),
                                   where=SQLBinaryExpr(SQLColumnExpr(COL_NAME_CONMAP_MAPID), OP_EQ,
                                                       SQLIntegral(mapid)))
        if x > 0:
            self.commit()
        return bool(x)  #

    def updateConsMap(self, mapid, setid, cons_id):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "updateConsMap" is deprecated use '
        msg += '"update_cons_map" instead'
        warn(msg, stacklevel=2)
        return self.update_cons_map(mapid, setid, cons_id)

    def del_cons_map(self, mapid):
        """deletes a constraint map by id
        :param mapid: mapid to delete
        :return: True if successfull / False on failure
        """
        x = self.DeleteGenericData(SQLTableExpr(TABLE_NAME_SIG_CONMAP),
                                   SQLBinaryExpr(SQLColumnExpr(COL_NAME_CONMAP_MAPID), OP_EQ, SQLIntegral(mapid)))
        if x >= 0:
            self.commit()
        return x

    def delConsMap(self, mapID):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "delConsMap" is deprecated use '
        msg += '"del_cons_map" instead'
        warn(msg, stacklevel=2)
        return self.del_cons_map(mapID)

    def get_cons_map(self, col_id, col=COL_NAME_CONMAP_SETID, select='*'):
        """gets a list of maps

        :param col: column to search on
        :param col_id: id to search for
        :return: found maps
        """
        return self.select_generic_data(select_list=select,
                                        table_list=[SQLTableExpr(TABLE_NAME_SIG_CONMAP)],
                                        where=SQLBinaryExpr(SQLColumnExpr(TABLE_NAME_SIG_CONMAP, col),
                                                            OP_EQ, SQLIntegral(col_id)))

    def getConsMap(self, col_id, col=COL_NAME_CONMAP_SETID, select='*'):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "getConsMap" is deprecated use '
        msg += '"get_cons_map" instead'
        warn(msg, stacklevel=2)
        return self.get_cons_map(col_id, col, select)

        # --- Constraint Set ---------------------------------------------------
    def add_constraint_set(self, set_name, operant, parent_id=None, meas_id=None, comment=None):
        """adds a new constraint set

        :param set_name: name of set
        :param operant: operant for child members
        :param parent_id: parent constraint set ID
        :param meas_id: db internal measurement ID
        :param comment: comment of set
        :return: id of just added constraint set
        """
        data_dict = {COL_NAME_CONSET_NAME: set_name,
                     COL_NAME_CONSET_SETOP: operant,
                     COL_NAME_CONSET_PARENTID: parent_id,
                     COL_NAME_CONSET_MEASID: meas_id,
                     COL_NAME_CONSET_COMMENT: comment,
                     COL_NAME_CONSET_MODTIME: datetime.now().isoformat(' ')}
        if self.get_constraint_set(set_name):
            return self.get_constraint_set(set_name)[0][COL_NAME_CONMAP_SETID]
        else:
            self.add_generic_data(data_dict, SQLTableExpr(TABLE_NAME_SIG_CONSET))
            ident = self.get_last_row_id()
            # self.commit()
            return ident

    def addConstraintSet(self, set_name, operant, parent_id=None, meas_id=None, comment=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "addConstraintSet" is deprecated use '
        msg += '"add_constraint_set" instead'
        warn(msg, stacklevel=2)
        return self.add_constraint_set(set_name, operant, parent_id, meas_id, comment)

    def update_constraint_set(self, setid, set_name, operant, parent_id, comment):
        """adds a new constraint set

        :param setid: set id to update
        :param set_name: name of set
        :param operant: operant for child members
        :param parent_id: parent constraint set ID
        :param comment: comment of set
        :return: True if successfull / False if failed
        """
        stmt = "UPDATE %s SET %s = '%s', %s = %d, " % (TABLE_NAME_SIG_CONSET, COL_NAME_CONSET_NAME, set_name,
                                                       COL_NAME_CONSET_SETOP, operant)
        stmt += "%s = %d, %s = '%s', " % (COL_NAME_CONSET_PARENTID, parent_id, COL_NAME_CONSET_COMMENT, comment)
        stmt += "%s = '%s' WHERE %s = %d" % (COL_NAME_CONSET_MODTIME, datetime.now().isoformat(' '),
                                             COL_NAME_CONSET_SETID, setid)
        return self.execute(stmt) > 0

    def updateConstraintSet(self, setID, set_name, operant, parent_id, comment):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "updateConstraintSet" is deprecated use '
        msg += '"update_constraint_set" instead'
        warn(msg, stacklevel=2)
        return self.update_constraint_set(setID, set_name, operant, parent_id, comment)

    def del_constraint_set(self, cons_set):
        """deletes a constraint set by it's ID or name

        :param cons_set: name or ID of constraint set
        :return: True if successfull / False if failed
        """
        ctp = isinstance(cons_set, str)
        x = self.DeleteGenericData(SQLTableExpr(TABLE_NAME_SIG_CONSET),
                                   SQLBinaryExpr(SQLColumnExpr(COL_NAME_CONSET_NAME), OP_LIKE, SQLString(cons_set))
                                   if ctp else SQLBinaryExpr(SQLColumnExpr(COL_NAME_CONSET_SETID), OP_EQ,
                                                             SQLIntegral(cons_set)))
        if x >= 0:
            self.commit()
        return x

    def delConstraintSet(self, cons_set):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "delConstraintSet" is deprecated use '
        msg += '"del_constraint_set" instead'
        warn(msg, stacklevel=2)
        return self.del_constraint_set(cons_set)

    def get_constraint_set(self, cons_set=None, measid=None, parents_only=False, where=None):
        """retrieves details of a constraint set by ID or name

        :param cons_set: name or ID of constraint set
        :return: list of details
        """
        where_condition = ''
        # TODO: rework building where_condition
        if cons_set is not None:
            if isinstance(cons_set, int):
                where_condition = COL_NAME_CONSET_SETID + " = " + str(cons_set)
            else:
                # TODO: should work as well
                # where_condition = COL_NAME_CONSET_NAME + " = '" + consSet + "'"
                where_condition = COL_NAME_CONSET_NAME + " LIKE '" + cons_set + "%'"

        if measid is not None:
            if len(where_condition) > 0:
                where_condition += ' AND '
            where_condition += COL_NAME_CONSET_MEASID + " = " + str(measid)

        if parents_only is True:
            # and (parentid not in (SELECT setid FROM cl_constraintsets where measid=1) or parentid is null)
            where_not_in = 'SELECT %s FROM %s WHERE %s' % (COL_NAME_CONSET_SETID, TABLE_NAME_SIG_CONSET,
                                                           where_condition)
            where_not_in = ' AND (%s NOT IN (%s) or %s is NULL)' \
                           % (COL_NAME_CONSET_PARENTID, where_not_in, COL_NAME_CONSET_PARENTID)
            where_condition += where_not_in

        if where is not None:
            if len(where_condition) > 0:
                where_condition += ' AND '
            where_condition += where

        cons = self.select_generic_data(table_list=[SQLTableExpr(TABLE_NAME_SIG_CONSET)], where=where_condition)

        return cons

    def getConstraintSet(self, cons_set=None, measid=None, parents_only=False, where=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "getConstraintSet" is deprecated use '
        msg += '"get_constraint_set" instead'
        warn(msg, stacklevel=2)
        return self.get_constraint_set(cons_set, measid, parents_only, where)

    def get_constraint_set_ids(self):
        """return IDs of all ConstraintSets listed in database

        :return: list of constraint set ids
        """
        ids = self.execute("SELECT %s from %s" % (COL_NAME_CONSET_SETID, TABLE_NAME_SIG_CONSET))

        # convert list of lists to list = flattening lists of lists
        ids = [item for sublist in ids for item in sublist]
        return ids

    def getConstraintSetIDs(self):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "getConstraintSetIDs" is deprecated use '
        msg += '"get_constraint_set_ids" instead'
        warn(msg, stacklevel=2)
        return self.get_constraint_set_ids()

        # --- Triggers ---------------------------------------------------------
    def add_trigger(self, signal_id, parent_id, value, condition, operant, usage):
        """adds a new trigger

        :param signal_id: link to a name = a signal name
        :param parent_id: id of parent trigger
        :param value: value of trigger
        :param condition: to trigger on
        :param operant: operant for child members
        :param usage: on what the trigger should be used for
        :return: id of just added trigger
        """
        self.add_generic_data({COL_NAME_TRIGGERS_SIGNALID: signal_id, COL_NAME_TRIGGERS_PARENTID: parent_id,
                               COL_NAME_TRIGGERS_OPERANT: operant, COL_NAME_TRIGGERS_VALUE: value,
                               COL_NAME_TRIGGERS_COND: condition, COL_NAME_TRIGGERS_USAGE: usage},
                              SQLTableExpr(TABLE_NAME_SIG_TRIG))
        # TODO: replace STMT_LAST_ROWID_SQLITE
        ident = self.select_generic_data(select_list=[SQLBinaryExpr(SQLFuncExpr(STMT_LAST_ROWID_SQLITE), OP_AS,
                                                                    COL_NAME_LAST_ROWID)])
        self.commit()
        return ident

    def addTrigger(self, signal_id, parent_id, value, condition, operant, usage):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "addTrigger" is deprecated use '
        msg += '"add_trigger" instead'
        warn(msg, stacklevel=2)
        return self.add_trigger(signal_id, parent_id, value, condition, operant, usage)

    def update_trigger(self, triggerid, signal_id, parent_id, value, condition, operant, usage):
        """adds a new trigger

        :param triggerid: id of trigger to update
        :param signal_id: link to a name, a signal name
        :param parent_id: id of parent trigger
        :param value: value of trigger
        :param condition: to trigger on
        :param operant: operant for child members
        :param usage: on what the trigger should be used for
        :return: True if successfull / False if failed
        """
        x = self.UpdateGenericData({COL_NAME_TRIGGERS_SIGNALID: signal_id, COL_NAME_TRIGGERS_PARENTID: parent_id,
                                    COL_NAME_TRIGGERS_VALUE: value, COL_NAME_TRIGGERS_COND: condition,
                                    COL_NAME_TRIGGERS_OPERANT: operant, COL_NAME_TRIGGERS_USAGE: usage},
                                   SQLTableExpr(TABLE_NAME_SIG_TRIG),
                                   where=SQLBinaryExpr(SQLColumnExpr(COL_NAME_TRIGGERS_TRIGGERID), OP_EQ,
                                                       SQLIntegral(triggerid)))
        if x > 0:
            self.commit()
        return bool(x)

    def updateTrigger(self, triggerID, signal_id, parent_id, value, condition, operant, usage):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "updateTrigger" is deprecated use '
        msg += '"update_trigger" instead'
        warn(msg, stacklevel=2)
        return self.update_trigger(triggerID, signal_id, parent_id, value, condition, operant, usage)

    def del_trigger(self, trigger):
        """deletes a trigger by it's ID or signal name

        :param trigger: name or ID of trigger
        :return: True if successfull / False if failed
        """
        x = 0
        if isinstance(trigger, str):
            x = self.DeleteGenericData(SQLTableExpr(TABLE_NAME_SIG_TRIG),
                                       SQLBinaryExpr(SQLColumnExpr(COL_NAME_TRIGGERS_SIGNALID), OP_IN,
                                                     GenericSQLSelect([SQLColumnExpr(COL_NAME_CONSIG_SIGNALID)], False,
                                                                      [SQLTableExpr(TABLE_NAME_SIG_CONSIG)],
                                                                      SQLBinaryExpr(SQLColumnExpr(COL_NAME_CONSIG_NAME),
                                                                                    OP_LIKE, SQLString(trigger)))))
        else:
            x = self.DeleteGenericData(SQLTableExpr(TABLE_NAME_SIG_TRIG),
                                       SQLBinaryExpr(SQLColumnExpr(TABLE_NAME_SIG_TRIG),
                                                     OP_EQ, SQLIntegral(trigger)))

        if x >= 0:
            self.commit()
        return x

    def delTrigger(self, trigger):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "delTrigger" is deprecated use '
        msg += '"del_trigger" instead'
        warn(msg, stacklevel=2)
        return self.del_trigger(trigger)

    def get_trigger(self, trigger):
        """retrieves details of a trigger by ID or signal name

        :param trigger: name or ID of trigger
        :return: list of details
        """
        """
        stmt = "SELECT * FROM %s WHERE " % TABLE_NAME_SIG_TRIG
        if isinstance(trigger, str):
            stmt += "%s IN (SELECT %s FROM %s WHERE %s LIKE '%s')" % (COL_NAME_TRIGGERS_SIGNALID,
                    COL_NAME_CONSIG_SIGNALID, TABLE_NAME_SIG_CONSIG, COL_NAME_CONSIG_NAME, trigger)
        else:
            stmt += "%s = %d" % (COL_NAME_TRIGGERS_TRIGGERID, trigger)
        self.execute(stmt)
        """

        if isinstance(trigger, str):
            return self.select_generic_data(table_list=[SQLTableExpr(TABLE_NAME_SIG_TRIG)],
                                            where=SQLBinaryExpr(SQLColumnExpr(SQLTableExpr(TABLE_NAME_SIG_TRIG),
                                                                              COL_NAME_CONSET_SETID), OP_IN,
                                                                GenericSQLSelect(
                                                                    [SQLColumnExpr(SQLTableExpr(TABLE_NAME_SIG_CONSIG),
                                                                                   COL_NAME_CONSIG_SIGNALID)],
                                                                    table_list=[SQLTableExpr(TABLE_NAME_SIG_TRIG)],
                                                                    where=SQLBinaryExpr(SQLTableExpr(TABLE_NAME_SIG_TRIG), OP_LIKE,
                                                                                        SQLString(trigger)))))
        else:
            return self.select_generic_data(table_list=[SQLTableExpr(TABLE_NAME_SIG_TRIG)],
                                            where=SQLBinaryExpr(SQLColumnExpr(TABLE_NAME_SIG_TRIG,
                                                                              COL_NAME_TRIGGERS_TRIGGERID), OP_EQ,
                                                                SQLIntegral(trigger)))

    def getTrigger(self, trigger):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "getTrigger" is deprecated use '
        msg += '"get_trigger" instead'
        warn(msg, stacklevel=2)
        return self.get_trigger(trigger)


# ===============================================================================
# Constraint DB Libary: kept for backward compatibility
# ===============================================================================
class PluginCLDB(BaseCLDB, PluginBaseDB):  # pylint: disable=R0904
    """used by plugin finder"""
    def __init__(self, *args, **kwargs):
        """some comment is missing"""
        BaseCLDB.__init__(self, *args, **kwargs)

    def get_last_row_id(self, column_name=None, table_name=None):
        """return last rowid by executing last_rowid function

        :param column_name, table_name: just to have same signature
        :return: autoincrement ID
        """
        id_dict = self.select_generic_data(select_list=[SQLBinaryExpr(SQLFuncExpr(STMT_LAST_ROWID_SQLITE), OP_AS,
                                                                      COL_NAME_LAST_ROWID)])
        return id_dict[0][COL_NAME_LAST_ROWID]

    def getLastRowID(self, column_name=None, table_name=None):  # pylint: disable=C0103
        """deprecated"""
        msg = 'Method "getLastRowID" is deprecated use '
        msg += '"get_last_row_id" instead'
        warn(msg, stacklevel=2)
        return self.get_last_row_id(column_name, table_name)


"""
CHANGE LOG:
-----------
$Log: cl.py  $
Revision 1.5 2016/08/16 16:01:35CEST Hospes, Gerd-Joachim (uidv8815) 
fix epydoc errors
Revision 1.4 2016/08/16 12:26:17CEST Hospes, Gerd-Joachim (uidv8815)
update module and class docu
Revision 1.3 2015/07/14 09:33:13CEST Mertens, Sven (uidv7805)
simplify for plugin finder
- Added comments -  uidv7805 [Jul 14, 2015 9:33:13 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.2 2015/04/30 11:09:36CEST Hospes, Gerd-Joachim (uidv8815)
merge last changes
--- Added comments ---  uidv8815 [Apr 30, 2015 11:09:37 AM CEST]
Change Package : 330394:1 http://mks-psad:7002/im/viewissue?selection=330394
Revision 1.1 2015/04/23 19:03:59CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/cl/project.pj
Revision 1.69 2015/03/05 09:26:09CET Mertens, Sven (uidv7805)
init argument and logger fix
--- Added comments ---  uidv7805 [Mar 5, 2015 9:26:10 AM CET]
Change Package : 312989:1 http://mks-psad:7002/im/viewissue?selection=312989
Revision 1.68 2015/02/06 11:56:52CET Mertens, Sven (uidv7805)
removing relative paths
--- Added comments ---  uidv7805 [Feb 6, 2015 11:56:52 AM CET]
Change Package : 303748:1 http://mks-psad:7002/im/viewissue?selection=303748
Revision 1.67 2015/02/06 08:43:47CET Mertens, Sven (uidv7805)
fix for missing arguments
--- Added comments ---  uidv7805 [Feb 6, 2015 8:43:48 AM CET]
Change Package : 303748:1 http://mks-psad:7002/im/viewissue?selection=303748
Revision 1.66 2015/02/06 08:08:29CET Mertens, Sven (uidv7805)
using absolute imports
--- Added comments ---  uidv7805 [Feb 6, 2015 8:08:30 AM CET]
Change Package : 303748:1 http://mks-psad:7002/im/viewissue?selection=303748
Revision 1.65 2015/01/29 09:12:02CET Mertens, Sven (uidv7805)
alignment to internal _db_connection
--- Added comments ---  uidv7805 [Jan 29, 2015 9:12:02 AM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.64 2015/01/28 16:29:07CET Mertens, Sven (uidv7805)
alignment to rest of DB sub modules
--- Added comments ---  uidv7805 [Jan 28, 2015 4:29:07 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.63 2015/01/28 10:54:38CET Mertens, Sven (uidv7805)
removing deprecated method calls
--- Added comments ---  uidv7805 [Jan 28, 2015 10:54:39 AM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.62 2015/01/23 21:44:24CET Ellero, Stefano (uidw8660)
Removed all util based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 23, 2015 9:44:24 PM CET]
Change Package : 296837:1 http://mks-psad:7002/im/viewissue?selection=296837
Revision 1.61 2014/12/09 19:02:32CET Ellero, Stefano (uidw8660)
Removed all db.cl based deprecated function usage inside stk and module tests
--- Added comments ---  uidw8660 [Dec 9, 2014 7:02:33 PM CET]
Change Package : 281274:1 http://mks-psad:7002/im/viewissue?selection=281274
Revision 1.60 2014/10/16 18:48:42CEST Skerl, Anne (uid19464)
*update get_constraint_set() to deliver all constraint sets that match to the measid
--- Added comments ---  uid19464 [Oct 16, 2014 6:48:43 PM CEST]
Change Package : 271545:1 http://mks-psad:7002/im/viewissue?selection=271545
Revision 1.59 2014/08/05 09:23:31CEST Hecker, Robert (heckerr)
Moved Methods to new Naming convensions, and created Backward-Compatibility Methods.
--- Added comments ---  heckerr [Aug 5, 2014 9:23:31 AM CEST]
Change Package : 253983:1 http://mks-psad:7002/im/viewissue?selection=253983
Revision 1.58 2014/06/06 16:00:54CEST Ahmed, Zaheer (uidu7634)
Rename Columna name COMMENT to COMMENTS
in CL subschema tables
--- Added comments ---  uidu7634 [Jun 6, 2014 4:00:54 PM CEST]
Change Package : 239332:1 http://mks-psad:7002/im/viewissue?selection=239332
Revision 1.57 2014/05/05 11:24:57CEST Skerl, Anne (uid19464)
*bugfix error message
--- Added comments ---  uid19464 [May 5, 2014 11:24:58 AM CEST]
Change Package : 234186:1 http://mks-psad:7002/im/viewissue?selection=234186
Revision 1.56 2014/04/30 18:07:05CEST Skerl, Anne (uid19464)
*improve error message in getConstraints()
--- Added comments ---  uid19464 [Apr 30, 2014 6:07:05 PM CEST]
Change Package : 234186:1 http://mks-psad:7002/im/viewissue?selection=234186
Revision 1.55 2014/04/16 11:18:10CEST Ahmed, Zaheer (uidu7634)
New column defination for COMMENT for CL_SigConstraints
--- Added comments ---  uidu7634 [Apr 16, 2014 11:18:10 AM CEST]
Change Package : 230894:1 http://mks-psad:7002/im/viewissue?selection=230894
Revision 1.54 2014/02/26 08:43:28CET Weinhold, Oliver (uidg4236)
If the CS already exists, only return its set id.
--- Added comments ---  uidg4236 [Feb 26, 2014 8:43:29 AM CET]
Change Package : 221579:1 http://mks-psad:7002/im/viewissue?selection=221579
Revision 1.53 2014/02/19 17:57:36CET Skerl, Anne (uid19464)
*use dicts as Trie-values
--- Added comments ---  uid19464 [Feb 19, 2014 5:57:36 PM CET]
Change Package : 220258:1 http://mks-psad:7002/im/viewissue?selection=220258
Revision 1.52 2014/02/13 18:00:59CET Skerl, Anne (uid19464)
*cleanup: change name KID_VALUENAME_SETNAME to KID_NAME_SETNAME
--- Added comments ---  uid19464 [Feb 13, 2014 6:00:59 PM CET]
Change Package : 198254:14 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.51 2014/02/10 11:00:19CET Skerl, Anne (uid19464)
*save also ConstrSetName to CTrie
*return also SignalName in getSigConstraintsPerSet()
*add flag "parents_only" at getConstraintSet() to prevent loading also subsets of same measid
--- Added comments ---  uid19464 [Feb 10, 2014 11:00:19 AM CET]
Change Package : 198254:6 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.50 2014/02/07 11:01:27CET Weinhold, Oliver (uidg4236)
Catch an exception (measurements in bpl for which no constraints exist)
--- Added comments ---  uidg4236 [Feb 7, 2014 11:01:27 AM CET]
Change Package : 213341:9 http://mks-psad:7002/im/viewissue?selection=213341
Revision 1.49 2013/12/18 16:49:33CET Skerl, Anne (uid19464)
*pylint
--- Added comments ---  uid19464 [Dec 18, 2013 4:49:33 PM CET]
Change Package : 198254:10 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.48 2013/12/18 16:09:02CET Skerl, Anne (uid19464)
*pep8
--- Added comments ---  uid19464 [Dec 18, 2013 4:09:02 PM CET]
Change Package : 198254:9 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.47 2013/12/18 13:39:11CET Skerl, Anne (uid19464)
*add KID_DEFAULT_COMP_RESULTS
*change getConstraints(): return list
*correct spelling of getSigConstraintsPerSet()
*change addConsSignal(): check if signal is already in db
*update getConsSignal(): add where parameter
--- Added comments ---  uid19464 [Dec 18, 2013 1:39:11 PM CET]
Change Package : 198254:6 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.46 2013/12/10 15:28:48CET Skerl, Anne (uid19464)
*add CL_OP_NAME_MAP for ucv._getCompareResultDetails() to get all compare results of trie
--- Added comments ---  uid19464 [Dec 10, 2013 3:28:49 PM CET]
Change Package : 198254:5 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.45 2013/12/09 18:45:03CET Skerl, Anne (uid19464)
*pep8
--- Added comments ---  uid19464 [Dec 9, 2013 6:45:03 PM CET]
Change Package : 198254:6 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.44 2013/12/09 17:07:44CET Skerl, Anne (uid19464)
*bugfix at getConstraints()
*change interface of addSigConstraint() to use dict
--- Added comments ---  uid19464 [Dec 9, 2013 5:07:45 PM CET]
Change Package : 198254:6 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.43 2013/12/02 14:38:31CET Skerl, Anne (uid19464)
*update cl to return integer at getLastRowID
--- Added comments ---  uid19464 [Dec 2, 2013 2:38:32 PM CET]
Change Package : 198254:4 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.42 2013/11/29 16:41:49CET Skerl, Anne (uid19464)
*pep8
--- Added comments ---  uid19464 [Nov 29, 2013 4:41:49 PM CET]
Change Package : 198254:3 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.41 2013/11/29 14:55:07CET Skerl, Anne (uid19464)
*several bugfixes, e.g. AddGenericData does not return rowcount
*make it nicer
--- Added comments ---  uid19464 [Nov 29, 2013 2:55:07 PM CET]
Change Package : 198254:3 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.40 2013/11/26 13:34:00CET Skerl, Anne (uid19464)
*change structure of trie values
*change addConstraints: add parent_id, way to write to ConsMap, return value
*add: getSigContraintsPerSet
--- Added comments ---  uid19464 [Nov 26, 2013 1:34:00 PM CET]
Change Package : 198254:2 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.39 2013/11/21 15:39:23CET Skerl, Anne (uid19464)
*comment out some unused imports
*implement logical operations for combining constraints
*add compare result to Trie structure
*change addConstraints() to allow writing of constraints for different constraints
--- Added comments ---  uid19464 [Nov 21, 2013 3:39:24 PM CET]
Change Package : 198254:1 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.38 2013/11/18 17:00:38CET Skerl, Anne (uid19464)
*add: SIGCON_DEFAULT_TRIGGER = 'Timestamp'
*change: use only measid inside cl, not recfilename
*remove: getSigConstraintDict(), not needed any more
--- Added comments ---  uid19464 [Nov 18, 2013 5:00:38 PM CET]
Change Package : 198254:1 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.37 2013/11/13 18:31:06CET Skerl, Anne (uid19464)
*change: getConstraints(self, consSet) -> getConstraints(self, consSet, measid),
         getConstraintSet(self, consSet) -> getConstraintSet(self, consSet=None, measid=None, where=None)
*change: write values of Trie kids as list of dicts
--- Added comments ---  uid19464 [Nov 13, 2013 6:31:07 PM CET]
Change Package : 198254:1 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.36 2013/11/11 10:52:19CET Skerl, Anne (uid19464)
*rework: addConstraints() and connected add-methods
*rework: use getLastRowID() depending on DB format
--- Added comments ---  uid19464 [Nov 11, 2013 10:52:19 AM CET]
Change Package : 198254:1 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.35 2013/11/08 14:58:03CET Skerl, Anne (uid19464)
*bugfix: repair wrong line formats after merge
--- Added comments ---  uid19464 [Nov 8, 2013 2:58:03 PM CET]
Change Package : 198254:1 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.34 2013/11/08 14:43:52CET Skerl, Anne (uid19464)
*merged with Rev. 1.23, remove plain SQL by statements from db_common.py
--- Added comments ---  uid19464 [Nov 8, 2013 2:43:53 PM CET]
Change Package : 198254:1 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.33 2013/10/25 12:33:16CEST Skerl, Anne (uid19464)
*add: constant definitions COL_NAMES_SIGCON, CL_OP_xxx
*add: SQLite3RecCatalogDB
*add: methods getSigConstraintDict, getConstraintSetIDs(self)
*change: getConsMap to use different select
--- Added comments ---  uid19464 [Oct 25, 2013 12:33:17 PM CEST]
Change Package : 198254:1 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.32 2013/07/29 12:57:38CEST Raedler, Guenther (uidt9430)
- revert changes of rev. 1.30 and 1.31
- removed unused methods
--- Added comments ---  uidt9430 [Jul 29, 2013 12:57:38 PM CEST]
Change Package : 191735:1 http://mks-psad:7002/im/viewissue?selection=191735
Revision 1.31 2013/07/04 16:10:25CEST Mertens, Sven (uidv7805)
removing unneeded methods from db_common
--- Added comments ---  uidv7805 [Jul 4, 2013 4:10:26 PM CEST]
Change Package : 185933:3 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.30 2013/07/04 15:01:47CEST Mertens, Sven (uidv7805)
providing tableSpace to BaseDB for what sub-schema space each module is intended to be responsible
--- Added comments ---  uidv7805 [Jul 4, 2013 3:01:47 PM CEST]
Change Package : 185933:3 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.29 2013/04/26 13:31:51CEST Mertens, Sven (uidv7805)
testing MKS bug
--- Added comments ---  uidv7805 [Apr 26, 2013 1:31:51 PM CEST]
Change Package : 179495:5 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.28 2013/04/26 10:46:11CEST Mertens, Sven (uidv7805)
moving strIdent
Revision 1.27 2013/04/25 15:31:37CEST Mertens, Sven (uidv7805)
_connection --> db_connection
Revision 1.26 2013/04/25 14:35:12CEST Mertens, Sven (uidv7805)
epydoc adaptation to colon instead of at
Revision 1.25 2013/04/12 14:37:05CEST Mertens, Sven (uidv7805)
adding a short representation used by db_connector.PostInitialize
--- Added comments ---  uidv7805 [Apr 12, 2013 2:37:06 PM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.24 2013/04/10 17:29:56CEST Mertens, Sven (uidv7805)
rewind to SQL statements, no more dependancy to db_sql
Revision 1.23 2013/04/05 11:17:40CEST Hospes, Gerd-Joachim (uidv8815)
fix documentation
--- Added comments ---  uidv8815 [Apr 5, 2013 11:17:41 AM CEST]
Change Package : 169590:2 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.22 2013/03/28 11:10:55CET Mertens, Sven (uidv7805)
pylint: last unused import removed
--- Added comments ---  uidv7805 [Mar 28, 2013 11:10:56 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.21 2013/03/27 11:37:27CET Mertens, Sven (uidv7805)
pep8 & pylint: rowalignment and error correction
Revision 1.20 2013/03/26 16:19:40CET Mertens, Sven (uidv7805)
pylint: using direct imports, no stars any more
--- Added comments ---  uidv7805 [Mar 26, 2013 4:19:40 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.19 2013/03/26 13:00:21CET Mertens, Sven (uidv7805)
reverting error for keyword argument spaces
--- Added comments ---  uidv7805 [Mar 26, 2013 1:00:21 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.18 2013/03/26 11:53:20CET Mertens, Sven (uidv7805)
reworking imports on cat, cl and db_common to start testing with.
--- Added comments ---  uidv7805 [Mar 26, 2013 11:53:20 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.17 2013/03/21 17:22:40CET Mertens, Sven (uidv7805)
solving some pylint warnings / errors
Revision 1.16 2013/03/15 10:01:18CET Mertens, Sven (uidv7805)
added addConstraint method to add new constrain set with details
--- Added comments ---  uidv7805 [Mar 15, 2013 10:01:18 AM CET]
Change Package : 176171:8 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.15 2013/03/14 11:34:21CET Mertens, Sven (uidv7805)
using new execute function instead (for testing)
--- Added comments ---  uidv7805 [Mar 14, 2013 11:34:21 AM CET]
Change Package : 176171:8 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.14 2013/03/14 09:21:52CET Mertens, Sven (uidv7805)
adding OP_AS to next column...
--- Added comments ---  uidv7805 [Mar 14, 2013 9:21:52 AM CET]
Change Package : 176171:8 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.13 2013/03/14 08:34:12CET Mertens, Sven (uidv7805)
trying to use as operator to distinguish column name
--- Added comments ---  uidv7805 [Mar 14, 2013 8:34:12 AM CET]
Change Package : 176171:8 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.12 2013/03/13 16:27:55CET Mertens, Sven (uidv7805)
testing COL_NAME instead of SQLColumnExpr(SQLTableExpr(self.GetQualifiedTableName(TABLE_NAME)), COL_NAME)
--- Added comments ---  uidv7805 [Mar 13, 2013 4:27:56 PM CET]
Change Package : 176171:8 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.11 2013/03/13 15:44:00CET Mertens, Sven (uidv7805)
lower case column defines are needed, anyway.
--- Added comments ---  uidv7805 [Mar 13, 2013 3:44:00 PM CET]
Change Package : 176171:8 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.10 2013/03/13 15:10:01CET Mertens, Sven (uidv7805)
serving keyError 'CONSID'
--- Added comments ---  uidv7805 [Mar 13, 2013 3:10:01 PM CET]
Change Package : 176171:8 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.9 2013/03/13 13:48:01CET Mertens, Sven (uidv7805)
changes done
--- Added comments ---  uidv7805 [Mar 13, 2013 1:48:01 PM CET]
Change Package : 176171:8 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.8 2013/03/06 10:21:19CET Mertens, Sven (uidv7805)
done, pep8 styling
--- Added comments ---  uidv7805 [Mar 6, 2013 10:21:19 AM CET]
Change Package : 176171:7 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.7 2013/03/05 12:55:39CET Mertens, Sven (uidv7805)
adaptation done
--- Added comments ---  uidv7805 [Mar 5, 2013 12:55:40 PM CET]
Change Package : 176171:4 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.6 2013/03/04 07:47:22CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 4, 2013 7:47:24 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.5 2013/03/01 10:29:35CET Mertens, Sven (uidv7805)
bugfixing STK imports
--- Added comments ---  uidv7805 [Mar 1, 2013 10:29:35 AM CET]
Change Package : 176171:2 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.4 2013/02/28 17:02:47CET Mertens, Sven (uidv7805)
first working version of constraint related things
--- Added comments ---  uidv7805 [Feb 28, 2013 5:02:47 PM CET]
Change Package : 176171:1 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.1 2013/02/21 12:39:43CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/db/cl/project.pj
"""
