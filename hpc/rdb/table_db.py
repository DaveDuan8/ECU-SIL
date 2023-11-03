"""
table_db.py
-----------

    providing table dictionary for being able to copy / sync a whole table keeping auto-increment keys intact
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from sqlite3 import Binary
from six import PY2
if PY2:
    from StringIO import StringIO  # pylint: disable=E0401
else:
    from io import StringIO
from six import iteritems

# - HPC imports --------------------------------------------------------------------------------------------------------
from hpc.rdb.base import BaseDB, BaseDbException
from hpc.core.md5 import create_from_string


# - classes / functions ------------------------------------------------------------------------------------------------
class TableDict(dict):  # pylint: disable=R0902
    """
    I'm a dict, holding primary keys from source table and on missing keys, new entries are copied
    to destination and it's primary key is saved and returned

    """

    def __init__(self, src_db, dst_db, table, **kwargs):
        r"""
        create new instance

        :param BaseDB src_db: source database connection
        :param BaseDB dst_db: destination database connection
        :param str table: table which this dict refers to
        :param \**dict kwargs: lookup dictionaries from other DbDict's which are used to replace values from source.
                               keys are column names and it's values are lookup dictionaries
        :keyword kwargs:
            * *dontcare* ``list`` -- do not take care about given column details, if they do not match exactly,
                                     this is needed as some Oracle tables are not designed well
            * *recurse*  -- TODO: fill out what's this
            * *defaults* ``dict`` -- explicit default values for different columns
            * *pkey* ``str`` -- primary key of table if not defined in db
            * *lob* ``memoryfile`` -- list of bytes as stored in db fields
        :raises BaseDbException: no primary key defined and no found

        """
        dict.__init__(self)

        self._table = table
        self._dontcare = kwargs.pop("dontcare", [])
        if "recurse" in kwargs:
            kwargs[kwargs.pop("recurse")] = self
        self._defaults = kwargs.pop("defaults", {})
        self._lookup = kwargs
        self._cols = [i[0] for i in src_db.columns(table)]

        if "pkey" in kwargs:
            self._pkey = kwargs.pop("pkey")
        else:
            try:
                self._pkey = src_db.primary_key(table)[0]
            except Exception:
                raise BaseDbException("primary key not found")

        if self._pkey is None:
            # self._pkey = None
            self._keys = []
        else:
            # self._pkey = self._pkey[0]
            self._keys = src_db("SELECT %s FROM %s" % (self._pkey, self._table))
            self._cols.remove(self._pkey)

        self._lobs = kwargs.pop("lob", [])

        self._src = src_db
        self._dst = dst_db

    def __str__(self):
        """my name"""
        return "%s dict: %s; %s" % (self._table, self._pkey, ", ".join(self._cols))

    def keys(self):
        """keys we have"""
        return self._keys

    def __missing__(self, item):  # pylint: disable=R1260
        """
        copy data from source table to destination

        :param ``int`` item: primary key value
        :returns: number of entries added to db
        :rtype: int
        :raises AttributeError: error if no primary key is defined
        """
        if item is None:
            return None

        if self._pkey is None:
            raise AttributeError("no primary key existing, use copy()!")

        vals = list(self._src("SELECT %s FROM %s WHERE %s = :pkey"
                              % (", ".join(self._cols), self._table, self._pkey), pkey=item)[0])

        for k, v in iteritems(self._lookup):
            idx = self._cols.index(k)
            if isinstance(v, dict):
                vals[idx] = v[vals[idx]]
            elif k in self._defaults:
                vals[idx] = self._defaults[k]

        updates = {c: vals[i] for i, c in enumerate(self._cols) if c not in self._dontcare}
        try:
            for k, v in iteritems(updates):
                if k in self._lobs:
                    updates[k] = self._conv_lob(v)

            nkey = self._dst("INSERT INTO %s (%s) VALUES(%s) RETURNING %s"
                             % (self._table, ", ".join(updates.keys()),
                                ", ".join([(":A%d" % i) for i in range(len(updates))]), self._pkey),
                             **{"A%d" % i: v for i, v in enumerate(updates.values())})
        except Exception as _iex:
            try:
                lobs = [i for i, x in enumerate(list(updates.keys())) if x in self._lobs]
                nkey = self._dst("SELECT %s FROM %s WHERE %s"
                                 % (self._pkey, self._table,
                                    " AND ".join([("%s %s" % (x[0], "IS NULL" if x[1] is None else ("= :A%d" % i)))
                                                  for i, x in enumerate(updates.items()) if i not in lobs])),
                                 **{"A%d" % i: x for i, x in enumerate(updates.values())
                                    if i not in lobs and x is not None})[0][0]
            except Exception as _sex:
                raise AttributeError("cannot copy entry: [%s] from table %s"
                                     % (", ".join([str(i) for i in vals]), self._table))

        self[item] = nkey
        return nkey

    def value(self, key, col):
        """
        get a specific item from column by key

        :param ``str`` key: filter value for selection
        :param ``str`` col: column to filter on
        :returns: items found in table
        :rtype: list of lists
        """
        return self._src("SELECT %s FROM %s WHERE %s = :val" % (col, self._table, self._pkey), val=key)[0][0]

    def sync(self, casesens=False, where=""):
        """
        copy data from a non-indexed table such as a mapping table to destination.
        I was too lazy to get into deepcopy, which might be interesting here...

        :param ``boolean`` casesens: take care of case sensitivity of column names
        :param ``str`` where: additional where clause
        :return: number of copied rows
        :rtype: int
        """
        cnt = 0
        cols = ", ".join([('"%s"' % i) for i in self._cols] if casesens else self._cols)
        lobs = [i for i, x in enumerate(self._cols) if x in self._lobs]
        for i in self._src.executex("SELECT {} FROM {}{}".format(cols, self._table,
                                                                 " WHERE {}".format(where) if where else "")):
            vals = list(i)
            if lobs:
                for k, x in enumerate(vals):
                    if k in lobs:
                        vals[k] = self._conv_lob(x)

            for k, v in iteritems(self._lookup):
                if isinstance(v, dict):
                    idx = self._cols.index(k)
                    vals[idx] = v[vals[idx]]
            try:
                cnt += self._dst("INSERT INTO %s (%s) VALUES(%s)"
                                 % (self._table, ", ".join(self._cols),
                                    ", ".join([(":A%d" % k) for k in range(len(vals))])),
                                 **{"A%d" % k: l for k, l in enumerate(vals)})
            except Exception as _:
                pass  # seems record is already

        return cnt

    def _conv_lob(self, lob):
        """
        convert lob 4 destination

        :param ``memoryview`` lob: list of bytes as stored in source db
        :return: bytes to be copied
        :rtype: memoryview
        """
        if not lob:
            return None
        if self._dst.db_type[0] == BaseDB.SQLITE:
            return Binary(lob.read())

        blob = self._dst.mkvar('blob')
        blob.setvalue(0, lob.read())
        return blob


class FixDict(TableDict):
    """specific TableDict for DMT_FILES / CAT_DMT_FILES which is taking care of both"""

    def __init__(self, *args, **kwargs):
        r"""
        create new table dict

        :param \*tuple args: arguments forwarded to hpc.rdb.table_db.TableDict
        :param \**dict kwargs: additonal arguments forwarded to hpc.rdb.table_db.TableDict
        """
        TableDict.__init__(self, *args, **kwargs)

    def __missing__(self, item):
        """
        copy data from source table to destination

        :param ``int`` item: id to search for
        :return: item
        :rtype: int
        :raises AttributeError: error if no primary key was defined during initialization
        """
        if self._pkey is None:
            raise AttributeError("no primary key existing, use copy()!")

        return item


class CfgDict(TableDict):
    """interim solution to be able to merge back old sqlites without bin"""

    def __missing__(self, item):
        """
        add item if it's not in db

        :param ``int`` item: value to check
        :return: id of added item
        :rtype: int
        """
        cfg = self._src("SELECT CFG FROM HPC_SIMCFG WHERE CFGID = :cid", cid=item)[0][0]
        cfghsh = create_from_string(cfg)

        nkey = self._dst("SELECT CFGID FROM HPC_SIMCFG WHERE CFGHASH = :chsh OR "
                         "(CFGHASH IS NULL AND CFG=:cfg)", chsh=cfghsh, cfg=cfg)
        if nkey:
            nkey = nkey[0][0]
        else:
            nkey = self._dst("INSERT INTO HPC_SIMCFG (CFGHASH, CFGBIN) VALUES(:chsh, :cbin) RETURNING CFGID",
                             chsh=cfghsh, cbin=self._dst.stream2blob(StringIO(cfg), False))

        self[item] = nkey
        return nkey
