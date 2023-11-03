"""
table.py
--------

by now, starting with some table copy...

:org:           Continental AG
:author:        uidv7805

:version:       $Revision: 1.8 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2017/07/14 14:11:09CEST $
"""


# - classes / functions ------------------------------------------------------------------------------------------------
class TableDict(dict):
    """I'm a dict, holding primary keys from source table and on missing keys, new entries are copied
    to destination and it's primary key is saved and returned

    :param src_db: source database connection
    :param dst_db: destination database connection
    :param table: table which this dict refers to
    :keyword dontcare: do not take care about given column details, if they do not match exactly,
                       this is needed as some Oracle tables are not designed well
    :param kwargs: lookup dictionaries from other DbDict's which are used to replace values from source.
                   keys are column names and it's values are lookup dictionaries
    """
    def __init__(self, src_db, dst_db, table, **kwargs):
        dict.__init__(self)

        self._table = table
        self._dontcare = kwargs.pop("dontcare", [])
        if "recurse" in kwargs:
            kwargs[kwargs.pop("recurse")] = self
        self._defaults = kwargs.pop("defaults", {})
        self._lookup = kwargs
        self._cols = [i[0] for i in src_db.get_columns(table)]

        for c in self._dontcare:
            self._cols.remove(c)

        if "pkey" in kwargs:
            self._pkey = [kwargs.pop("pkey")]
        else:
            self._pkey = src_db.get_primary_key(table)

        if len(self._pkey) == 0:
            self._pkey = None
        else:
            self._pkey = self._pkey[0]
            self._cols.remove(self._pkey)

        self._fixed = False
        self._none = None
        self._src = src_db
        self._dst = dst_db

    def __str__(self):
        """my name"""
        return "%s dict: %s; %s" % (self._table, self._pkey, ", ".join(self._cols))

    def fix(self):
        """fix me, that means: no more lookup in DB, no more inserts,
        dict is it is and returns None if something still should be missing
        """
        self._fixed = True

    def keys(self):
        """keys we have"""
        return dict.keys(self)

    def __missing__(self, item):
        """copy data from source table to destination

        :param item:
        :return:
        """
        if self._fixed or item is None:
            return self._none

        if self._pkey is None:
            raise AttributeError("no primary key existing, use copy()!")

        # lob = self._cols.index(self._lob) if self._lob else None
        vals = list(self._src.execute("SELECT %s FROM %s WHERE %s = :pkey"
                                      % (", ".join(self._cols), self._table, self._pkey), pkey=item)[0])
                                      # lob=lob)[0])

        for k, v in self._lookup.iteritems():
            idx = self._cols.index(k)
            if isinstance(v, dict):
                vals[idx] = v[vals[idx]]
            elif k in self._defaults:
                vals[idx] = self._defaults[k]

        try:
            nkey = self._dst.execute("INSERT INTO %s (%s) VALUES(%s) RETURNING %s"
                                     % (self._table, ", ".join(self._cols),
                                        ", ".join([(":A%d" % k) for k in xrange(len(vals))]), self._pkey),  # lob=lob,
                                     **{"A%d" % k: l for k, l in enumerate(vals)})
        except Exception as _:
            try:
                excl = self._dontcare  # + [self._lob]
                nkey = self._dst.execute("SELECT %s FROM %s WHERE %s"
                                         % (self._pkey, self._table,
                                            " AND ".join([("%s %s" % (self._cols[k],
                                                                      "IS NULL" if vals[k] is None else ("= :A%d" % k)))
                                                          for k in xrange(len(vals)) if self._cols[k] not in excl])),
                                         **{"A%d" % k: l for k, l in enumerate(vals)
                                            if self._cols[k] not in excl and l is not None})[0][0]
            except Exception as _:
                raise AttributeError("cannot copy entry: [%s] from table %s"
                                     % (", ".join([str(i) for i in vals]), self._table))

        self[item] = nkey
        return nkey

    def value(self, key, col):
        """get a specific item from colmn by key"""
        return self._src.execute("SELECT %s FROM %s WHERE %s = :val" % (col, self._table, self._pkey), val=key)[0][0]

    def copy(self, casesens=False):
        """copies data from a non-indexed table such as a mapping table to destination.
        I was too lazy to get into deepcopy, which might be interesting here...

        :param casesens: take care of case sensitivity of column names
        :return: number of copied rows
        """
        cnt = 0
        cols = ", ".join([('"%s"' % i) for i in self._cols] if casesens else self._cols)
        lob = self._cols.index(self._lob) if self._lob else None
        for i in self._src.executex("SELECT %s FROM %s" % (cols, self._table), lob=lob):
            vals = list(i)
            for k, v in self._lookup.iteritems():
                if isinstance(v, dict):
                    idx = self._cols.index(k)
                    vals[idx] = v[vals[idx]]

            if lob:
                vals[lob] = self._dst.stream2blob(vals[lob], True)
            try:
                cnt += self._dst.execute("INSERT INTO %s (%s) VALUES(%s)"
                                         % (self._table, ", ".join(self._cols),
                                            ", ".join([(":A%d" % k) for k in xrange(len(vals))
                                                       if self._cols[k] not in self._dontcare])),
                                         **{"A%d" % k: l for k, l in enumerate(vals)
                                            if self._cols[k] not in self._dontcare})
            except Exception as _:
                pass  # seems record is already

        return cnt


class MeasDict(TableDict):
    """specific TableDict for DMT_FILES / CAT_DMT_FILES which is taking care of both
    """
    def __init__(self, *args, **kwargs):

        TableDict.__init__(self, *args, **kwargs)

    def __missing__(self, item):
        """copy data from source table to destination

        :param item:
        :return:
        """
        if self._fixed or item is None:
            return None

        if self._pkey is None:
            raise AttributeError("no primary key existing, use copy()!")

        rec = self._src.execute("SELECT FILEPATH FROM %s WHERE MEASID = :meas" % self._table, meas=item)[0][0]
        self[item] = self._dst.execute("SELECT MEASID FROM %s WHERE LOWER(FILEPATH) LIKE :meas" % self._table,
                                       meas=("%" + rec.split("\\", 3)[-1].lower()))[0][0]

        return self[item]


class UserTableDict(TableDict):
    """specific TableDict for GBL_USERS which is taking care YOU are inside with proper values
    """
    def __init__(self, *args, **kwargs):
        TableDict.__init__(self, *args, **kwargs)

        self._none = self._dst.execute("SELECT %s FROM %s WHERE LOGINNAME = $CU" % (self._pkey, self._table))
        if len(self._none) == 0:
            from win32com.client import GetObject, Dispatch
            from os import environ
            full = GetObject("WinNT://%s/%s,user" % (environ["USERDOMAIN"], environ["USERNAME"])).FullName
            nres = Dispatch(dispatch="NameTranslate")
            nres.Set(3, "%s\\%s" % (environ["USERDOMAIN"], environ["USERNAME"]))
            email = GetObject("LDAP://" + nres.Get(1)).Get("mail")
            self._none = self._dst.execute("INSERT INTO %s (LOGINNAME, NAME, EMAIL) VALUES (:login, :name, :email) "
                                           "RETURNING USERID" % self._table,
                                           login=environ["USERNAME"], name=full, email=email, commit=True)
        else:
            self._none = self._none[0][0]


class NoneDict(dict):
    """workaround for sqlite's unique constraints having null values
    """
    @staticmethod
    def __missing__(item):
        """use same data, but convert None to empty str
        """
        return '' if item is None else item


"""
CHANGE LOG:
-----------
$Log: table.py  $
Revision 1.8 2017/07/14 14:11:09CEST Mertens, Sven (uidv7805) 
return proper keys
Revision 1.7 2017/07/14 13:50:30CEST Mertens, Sven (uidv7805) 
update for dont care attribs
Revision 1.6 2016/07/13 13:02:23CEST Mertens, Sven (uidv7805) 
provide value info and a conversation from None to empty
Revision 1.5 2016/07/11 11:36:11CEST Mertens, Sven (uidv7805)
support for future table column ignorance which need some default
Revision 1.4 2016/07/11 09:14:15CEST Mertens, Sven (uidv7805)
enabling usertabledict
Revision 1.3 2016/07/08 10:19:11CEST Mertens, Sven (uidv7805)
support recursion, used by parent key relations of same table
Revision 1.2 2016/06/17 12:20:34CEST Mertens, Sven (uidv7805)
too long line
Revision 1.1 2016/06/17 12:18:34CEST Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/project.pj
"""
