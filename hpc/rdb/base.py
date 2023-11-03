"""
base_db.py
----------

base database interface
"""
# pylint: disable=E1103
# - import Python modules ----------------------------------------------------------------------------------------------
from __future__ import print_function
from os import stat, chmod, sep, altsep, makedirs
from os.path import basename, dirname
from stat import ST_MODE, S_IWRITE
from re import search, sub, split as resplit
from random import seed, random
from time import sleep
from zlib import decompress, compress as zcomp, error as zliberr, crc32
from sqlite3 import connect as sqconnect, register_adapter, register_converter, Binary, PARSE_DECLTYPES
from six import PY2
from cx_Oracle import connect as cxconnect, NUMBER, BLOB, DatabaseError  # pylint:disable=E0611

if PY2:  # pragma: no cover
    from StringIO import StringIO  # pylint: disable=E0401
    from types import StringTypes, LongType
else:  # pragma: no cover
    long = int  # pylint: disable=C0103
    from io import StringIO, BytesIO
    StringTypes, LongType = (str,), int

# - import HPC modules -------------------------------------------------------------------------------------------------
from ..core.error import HpcError, ERR_HPC_DATABASE
from ..core.tds import DEFAULT_DB_CONN, VGA_DB_CONN
from ..core.path import splitdrive

# - defines ------------------------------------------------------------------------------------------------------------
# db_type --> 0: sqlite, 1: oracle
DBTYPE = ["sqlite3", "cx_Oracle", "postgresql", "appsrv"]
SQL_TABLENAMES = ["SELECT name FROM sqlite_master WHERE type in ('table', 'view')",
                  "SELECT DISTINCT OBJECT_NAME FROM ALL_OBJECTS WHERE OBJECT_TYPE IN ('TABLE', 'VIEW') "
                  "AND OWNER = $TS"]
SQL_DT_EXPR = ["CURRENT_TIMESTAMP", "CURRENT_DATE"]
SQL_DATETIME = ["SELECT strftime('%Y-%m-%d %H:%M:%S','now')",
                "SELECT TO_CHAR(systimestamp at time zone 'utc', 'YYYY-MM-DD HH24:MI:SS') FROM SYS.dual"]
SQL_COLUMNS = [([1, 2], "PRAGMA table_info($TBL)"),
               ([0, 1], "SELECT column_name, data_type FROM all_tab_cols WHERE table_name = '$TBL' AND owner = '$TP'")]

VARS = [{'blob': Binary}, {'number': NUMBER, 'blob': BLOB}]

SQLITE_FILE_EXT = (".db", ".sqlite",)
DEFAULT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# - functions and classes ----------------------------------------------------------------------------------------------
def _reconnect(fnc):
    """reconnect to DB, just in case"""
    def _decorate(self, *args, **kwargs):
        """inner decoration (providing self)"""
        kws = kwargs.copy()
        print_err = kws.pop('print_err', self._print_err)  # pylint: disable=W0212
        exc_retry = kws.pop('exc_retry', self._maxretry)  # pylint: disable=W0212
        raise_err = kws.pop('raise_err', True)
        for _ in range(max(exc_retry, 1)):
            try:
                return fnc(self, *args, **kws)
            except Exception as ex:
                if print_err:
                    print("DB error: {!s}".format(ex).replace('\n', ' '))
                mtc = search(r".+ORA-([0-9]{5}):.+", str(ex))
                if mtc is not None and 24280 >= int(mtc.group(1)) > 29250:  # pragma: no cover
                    self.reconnect()
                elif raise_err:
                    raise HpcError("unable to execute SQL (ORA-%s)!" % mtc.group(1) if mtc else "-", ERR_HPC_DATABASE)
        # else:  # pragma: no cover
        #     raise HpcError("unable to connect to DB!", ERR_HPC_DATABASE)
    return _decorate


class BaseDbException(Exception):
    """Base database exception"""


class BaseDB(object):  # pylint: disable=R0902
    """Base implementation of the Database Interface"""

    SQLITE, ORACLE, APPSRV = list(range(3))

    def __init__(self, db_connection="HPC", **kwargs):  # pylint: disable=R0912,R0915,R1260
        r"""
        initialize database

        :param str db_connection: The database connection to be used

        :param dict kwargs: see below
        :keyword \**kwargs:
            * *aggregates* (``list``): list of additional aggregates
            * *maxtry* (``int``): try maximum times to get connection to Oracle DB, default: 60
            * *create* (``bool``): flag to create a non-existing sqlite DB, default: False (do not create)
            * *journal* (``bool``): turn off journal mode with sqlite DB, default: True

        """
        assert isinstance(kwargs.get('maxtry', 0), int), "maxtry argument should be int!"
        assert isinstance(kwargs.get('create', False), bool), "create flag should be boolean!"
        assert isinstance(kwargs.get('journal', False), bool), "journal mode should be boolean!"

        self.autocommit = kwargs.pop('autocommit', True)
        self._db_type = None
        self._own_conn = True
        self._conn_dict = None
        self.lob_conv = None
        self._maxretry = kwargs.pop('maxtry', 23)
        self._print_err = kwargs.pop('print_err', True)
        self._agregates = kwargs.pop('aggregates', [])
        self._functions = kwargs.pop('functions', [])
        self._call_tout = kwargs.pop('call_timeout', 0)
        # self._functions.extend([(self._path.subpath, 1,), basename])

        self.db_connection = None
        if isinstance(db_connection, StringTypes):  # if we have a connection string, do connect here
            if db_connection == 'HPC':  # do we have a string from predefined?
                db_connection = DEFAULT_DB_CONN
            elif db_connection == 'VGA':
                db_connection = VGA_DB_CONN
            elif db_connection == 'VGA_PWR':
                db_connection = {"args": ("VAL_GLOBAL_PWUSER_RES", "VAL_GLBL_PWUSER_RES1", "racadmpe",), "kwargs": {},
                                 "conn_func": cxconnect, "db_type": BaseDB.ORACLE, "repr": "VGA_PWR@oracle",
                                 "exec": ["ALTER SESSION SET current_schema = VAL_GLOBAL_ADMIN"],
                                 "set": [("autocommit", self.autocommit,)]}
            elif "uid=" in db_connection and "pwd=" in db_connection:  # pragma: no cover
                conn = dict(i.split('=', 1) for i in db_connection.split(';'))
                db_connection = {"args": (conn["uid"], conn["pwd"], conn.get("dbq", "racadmpe"),), "kwargs": {},
                                 "conn_func": cxconnect, "db_type": BaseDB.ORACLE,
                                 "repr": "{}@oracle".format(conn["uid"]),
                                 "exec": ["ALTER SESSION SET current_schema = {}".format(conn.get("sch", conn["uid"]))],
                                 "set": [("autocommit", self.autocommit,)]}

        if isinstance(db_connection, StringTypes):
            # seems like an sqlite3 ...
            # if splitext(db_connection)[-1].lower() in SQLITE_FILE_EXT and \
            #         (isfile(str(db_connection)) or kwargs.get("create", False)) or db_connection == ":memory:":
            try:
                if not stat(db_connection)[ST_MODE] & S_IWRITE:
                    chmod(db_connection, S_IWRITE)
            except Exception:  # pylint: disable=W0702
                pass
            try:
                makedirs(dirname(db_connection))
            except Exception:
                pass
            # self.str_connection = db_connection
            self._db_type = BaseDB.SQLITE
            exe = ["PRAGMA foreign_keys = ON"]
            if not kwargs.get('journal', False):
                exe.extend(["PRAGMA JOURNAL_MODE = OFF", "PRAGMA synchronous = OFF"])

            self._connect({"conn_func": sqconnect, "args": (db_connection,),
                           "kwargs": {"detect_types": PARSE_DECLTYPES}, "exec": exe,
                           "set": [("text_factory", str,)], "repr": db_connection})

        elif isinstance(db_connection, dict):
            # arg = {}
            # for i, v in [a.split('=', 2) for a in db_connection.split(';')]:
            #     arg[i.strip().lower()] = v.strip()
            # self.str_connection = (arg['uid'], arg['pwd'], arg.pop('dbname', kwargs.get('dbname', 'racadmpe')))
            self._db_type = db_connection["db_type"]
            self._connect(db_connection)
            self.lob_conv = lambda r, l: [((r[i].read() if r[i] is not None else None) if i in l else r[i])
                                          for i in range(len(r))]
        # otherwise we have an already existing connection
        else:
            self.db_connection = db_connection.db_connection
            self._own_conn = False
            self.autocommit = db_connection.autocommit
            self._db_type = db_connection.db_type[0]
            self.str_connection = db_connection.str_connection
            self.lob_conv = db_connection.lob_conv

        # as large objects need to be retrieved at once, speed it up here for each item of a record line
        if self.lob_conv is None:
            def _conv(res, idxs):
                """convert lobs"""
                ret = []
                for i, k in enumerate(res):
                    if i in idxs:
                        try:
                            ret.append(decompress(k))
                        except zliberr:
                            ret.append(k)
                    else:
                        ret.append(k)
                return ret
            self.lob_conv = _conv
            # self.lob_conv = lambda r, l: [((str(r[i]) if r[i] is not None else None) if i in l else r[i])
            #                               for i in range(len(r))]

        self.date_time_format = DEFAULT_DATETIME_FORMAT
        self._trans_acted = True
        self._cur = None

    def __str__(self):
        """return some self descriptive information"""
        return "connection: {}, type: {}".format(self.str_connection, DBTYPE[self._db_type])

    def __enter__(self):
        """being able to use with statement"""
        return self

    def _connect(self, conn=None):  # pylint: disable=R0912,R1260
        """connect to DB"""
        if conn:
            self._conn_dict = conn
        else:
            conn = self._conn_dict

        seed()  # init rng
        exc = "-"
        self.str_connection = conn["repr"]
        for _ in range(self._maxretry):
            try:  # min 3 minutes along...
                self.db_connection = conn["conn_func"](*conn["args"], **conn["kwargs"])
                sleep(0.2)
                break
            except Exception as ex:  # pragma: no cover
                exc = ex
                sleep(1 + random())
        else:  # pragma: no cover
            raise HpcError("cannot connect to DB ({!s})!".format(exc), ERR_HPC_DATABASE)

        if self._db_type == BaseDB.SQLITE:
            register_adapter(LongType, lambda n: '#{:d}'.format(n) if n > 2147483647 else n)
            if PY2:
                register_converter("integer", lambda n: int(n.decode('utf-8')[1:] if n[0] == '#' else n))
            else:
                register_converter("integer", lambda n: int(n.decode('utf-8')[1:] if chr(n[0]) == '#' else n))

            for i in self._agregates:  # pragma: no cover
                if PY2:
                    self.db_connection.create_aggregate(i.__name__, i.step.im_func.func_code.co_argcount - 1, i)
                else:
                    self.db_connection.create_aggregate(i.__name__, i.step.__func__.__code__.co_argcount - 1, i)
            for i in self._functions:
                name, argcnt, func = (i[0].__name__, i[1], i[0]) if isinstance(i, tuple) \
                    else (i.__name__, i.func_code.co_argcount if PY2 else i.__code__.co_argcount, i)
                self.db_connection.create_function(name, argcnt, func)
            if self.autocommit:
                toset = conn.pop("set", [])
                toset.append(("isolation_level", None,))
                conn["set"] = toset
        elif self._db_type == BaseDB.ORACLE:
            if self._call_tout:
                try:
                    setattr(self.db_connection, "callTimeout", self._call_tout * 1000)
                except DatabaseError:
                    self._call_tout = 0

        for i in conn.get("exec", []):
            self(i)
        for i in conn.get("copy", []):
            if isinstance(i, (tuple, list,)):
                k, l = i
            else:
                k = l = i
            setattr(self.db_connection, k, getattr(self, l))
        for k, l in conn.get("set", []):
            setattr(self.db_connection, k, l)
        sleep(0.2)

    def reconnect(self):  # pragma: no cover
        """close and re-open connection"""
        if self._own_conn:
            self.close()
            sleep(0.7)
            self._connect()

    def close(self, *_):
        """close connection"""
        if self._own_conn and self.db_connection is not None:
            try:
                self.db_connection.close()
            except Exception as _:  # pragma: no cover
                pass  # we'll get the exception when connection is lost
            self.db_connection = None

    __del__ = close
    __exit__ = close

    @property
    def db_type(self):
        """return a string about what type of DB we have here."""
        return self._db_type, DBTYPE[self._db_type]

    def commit(self):
        """Commit the pending transactions"""
        if not self._trans_acted and self.db_connection is not None:
            self.db_connection.commit()
            self._trans_acted = True

    def rollback(self):
        """Rollback the pending transactions"""
        if not self._trans_acted and self.db_connection is not None:
            self.db_connection.rollback()
            self._trans_acted = True

    def mkvar(self, vartype):
        """
        create a cx_Oracle / sqlite variable

        :param str vartype: current supported ones are blob and number
        :return: oracle variable
        :rtype: object
        :raises Exception: when connection is unknown
        """
        if self.db_type[0] == BaseDB.ORACLE:
            return self.db_connection.cursor().var(VARS[self._db_type][vartype.lower()])
        if self.db_type[0] == BaseDB.SQLITE:
            return VARS[self._db_type][vartype.lower()]

        raise Exception("connection doesn't support var creation!")

    def stream2blob(self, stream, compress=False):
        """
        convert a stream object to oracle blob

        :param stream stream: some stream from which data can be read
        :param bool compress: do a zlib compress before converting
        :return: cx_Oracle BLOB
        :rtype: buffer
        """
        if stream is None:
            return None

        if hasattr(stream, 'seek'):
            stream.seek(0)

        if isinstance(stream, StringTypes):
            if PY2:  # pragma: no cover
                strm = StringIO()
                strm.write(stream)
            else:
                strm = BytesIO()
                strm.write(stream.encode('utf-8'))
            stream = strm
            stream.seek(0)

        if compress:
            if PY2:  # pragma: no cover
                strm = StringIO()
                strm.write(str(zcomp(stream.read(), 9)))
            else:
                strm = BytesIO()
                data = stream.read()
                try:
                    data = data.encode()
                except AttributeError:
                    pass
                strm.write(zcomp(data, 9))
            stream = strm
            stream.seek(0)

        if self._db_type == BaseDB.SQLITE:
            return Binary(stream.read())

        blob = self.db_connection.cursor().var(BLOB)
        blob.setvalue(0, stream.read())
        return blob

    @_reconnect
    def execute(self, statement, **kwargs):  # pylint: disable=R0912
        """see __call__(...)"""
        return self(statement, **kwargs)

    @_reconnect
    def __call__(self, statement, **kwargs):  # pylint: disable=R0912,R0915,R1260
        r"""
        Execute SQL statement(s). Multiple statements can be semicolon (;) separated

        :param str statement: SQL query, supported statements: select, insert, update, delete, execute
        :param dict kwargs: see below
        :keyword \**kwargs:
            * *insertmany* (``list[tuple]``): used to insert more then one item into DB
            * *lob* (``int``): index / indices which column have LOB's to be read out
            * *commit* (``bool``): overwrites autocommit
            * *iter* (``bool``): return an iterator instead of a list

        :return: returns all rows
        :rtype: int|list|iterator
        :raises Exception: once statement caused trouble
        """
        if self._db_type == BaseDB.APPSRV:  # we handle it special here...
            data = None
            try:
                data = self.db_connection(statement, **kwargs)
            except Exception:
                return data

        iterate = kwargs.pop('iter', False)
        commit = kwargs.pop('commit', self.autocommit)
        insertmany = kwargs.pop('insertmany', None)
        lobo = None
        if "lob" in kwargs:
            lobo = [kwargs.pop('lob')] if isinstance(kwargs['lob'], int) else kwargs.pop('lob')
            if len(lobo) == 0:
                lobo = None

        # helper to return proper insertion ID
        pat = search(r"(?i)returning\s(\w*);?$", statement)
        retlastid = False
        if pat is not None:
            if self._db_type == BaseDB.ORACLE:
                statement = statement[:pat.regs[1][0]] + pat.groups()[0] + " INTO :id"
                rid = self.mkvar('number')
                kwargs['id'] = rid
            elif self._db_type == BaseDB.SQLITE:
                statement = statement[:pat.start() - 1]
                retlastid = True
        # we can also replace $DT as current date time, $CD as current date and $CT as current time
        # .replace("$DT", "SYSDATE" if self._db_type == -1 else "CURRENT_TIMESTAMP")
        # .replace("$CD", "CURRENT_DATE")
        # .replace("$CT", "CURRENT_TIMESTAMP" if self._db_type == -1 else "CURRENT_TIME")
        statement = statement.replace(" None", " null")
        if self._db_type == BaseDB.SQLITE:
            statement = statement.replace('NVL', 'IFNULL').replace(" FROM DUAL", "")\
                .replace(" NULLS LAST", "").replace(" NULLS FIRST", "")
            statement = sub(r"WHERE ROWNUM (\<=?|=)", "LIMIT", statement)

        try:
            records = []
            cursor = self.db_connection.cursor()

            # remove keyword to get more ease in checking later on
            kwd = statement.split(' ', 1)[0].lower()

            # execute
            if insertmany:
                cursor.executemany(statement, insertmany)
            elif lobo is None:
                if self._db_type == BaseDB.SQLITE:
                    cursor.execute(statement, kwargs)
                else:
                    cursor.execute(statement, **kwargs)

            if kwd in ("select", "pragma", "with", "declare"):
                if isinstance(records, int):
                    records = int(cursor.fetchone()[0])
                elif lobo is not None:  # let's do weird stuff here:
                    if self._db_type == BaseDB.SQLITE:
                        records = [self.lob_conv(r, lobo) for r in cursor.execute(statement, kwargs)]
                    else:
                        records = [self.lob_conv(r, lobo) for r in cursor.execute(statement, **kwargs)]
                    # for rec in records:
                    #     for i in lobo:
                    #         if rec[i] is not None:
                    #             try:
                    #                 rec[i] = decompress(rec[i])
                    #             except zliberr:  # pragma: no cover
                    #                 pass
                else:
                    if iterate:
                        records = cursor
                    else:
                        records.extend(cursor.fetchall())
            else:
                records = cursor.rowcount
                # commit if not switched off
                if commit and not self.autocommit:
                    self.db_connection.commit()
                elif not self.autocommit:
                    self._trans_acted = False

                if pat is not None and self._db_type == BaseDB.ORACLE:  # grab the returning ID if oracle
                    records = rid.getvalue()
                    if isinstance(records, list):
                        records = int(records[0])
                    else:
                        records = int(records)
                elif retlastid:
                    records = cursor.lastrowid

        except Exception as ex:
            raise Exception("error: {!s}, statement: {} data: {!s}".format(ex, statement, kwargs))
        finally:
            if not iterate:
                cursor.close()
            elif self._cur is None:
                self._cur = cursor

        # done
        return records

    def executex(self, statement, *args, **kwargs):  # pylint: disable=R0912
        """
        Execute SQL statement(s).

        :param str statement: SQL query, supported statements: select, insert, update, delete, execute
        :param list args: additional arguments
        :param dict kwargs: additional arguments
        :return: returns all rows
        :rtype: tuple
        """
        kwargs['iter'] = True
        try:
            for i in self(statement, *args, **kwargs):
                yield i
        finally:
            self._cur.close()
            self._cur = None

    def columns(self, table):
        """
        Get a list of column names for a given table.

        :param str table: name of table
        :return: list of columns
        :rtype: list
        """
        return [(str(i[SQL_COLUMNS[self._db_type][0][0]]), str(i[SQL_COLUMNS[self._db_type][0][1]]))
                for i in self(SQL_COLUMNS[self._db_type][1]
                              .replace('$TBL', table).replace('$TP', getattr(self.db_connection,
                                                                             "current_schema", "")))]

    @property
    def tables(self):
        """
        :return: tables of DB
        :rtype: list
        """
        return [i[0] for i in self(SQL_TABLENAMES[self._db_type]
                                   .replace('$TS', getattr(self.db_connection, "current_schema", "")))]

    def primary_key(self, table):
        """
        Get the primary key column(s).

        :param str table: name of table
        :return: list of columns
        :rtype: list
        """
        if self._db_type == BaseDB.ORACLE:
            return [i[0] for i in self("SELECT COLUMN_NAME FROM ALL_CONSTRAINTS c "
                                       "INNER JOIN ALL_CONS_COLUMNS USING(OWNER, CONSTRAINT_NAME) "
                                       "WHERE c.CONSTRAINT_TYPE = 'P' AND c.TABLE_NAME = :tbl", tbl=table)]
        if self._db_type == BaseDB.SQLITE:
            return [i[1] for i in self("PRAGMA table_info(%s)" % table) if i[-1] == 1]

        return []


def tohex(val):
    """sqlite function to support hex output"""
    return "%X" % val


def bitand(col, val):
    """sqlite function to support for oracle's bitand"""
    return col & val


def serverpath(filepath):
    """only return server share part"""
    if filepath[0] in [sep, altsep]:
        return splitdrive(filepath)[0].lower()

    try:
        jnr, jps = ("/", 4,) if filepath.startswith("http") else ("\\", 2,)
        return jnr.join(resplit(r"\\|/", filepath)[0:jps]).lower()
    except Exception as _:
        return basename(filepath)


def basepath(filepath):
    """strip server share apart"""
    if filepath[0] in [sep, altsep]:
        return splitdrive(filepath)[1][1:].lower()

    try:
        jnr, jps = ("/", 4,) if filepath.startswith("http") else ("\\", 2,)
        return jnr.join(resplit(r"\\|/", filepath)[jps:]).lower()
    except Exception as _:
        return basename(filepath)


def crc(filepath):
    """calc crc32 out of filepath"""
    if PY2:
        return crc32(filepath.lower()) & long(0xFFFFFFFF)
    return crc32(bytes(filepath.lower(), 'utf-8'))
