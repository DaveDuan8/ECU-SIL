r"""
catalog.py
----------

    catlogue API

interface to CAT_FILES and CAT_COLLECTIONS tables with classes

- `CollManager` super class to start with
- `Collection`  use collection tree to read/write collections with recordings
- `Recording`   get recording data from db

**Usage Example:**

    code::

        with CollManager('VGA') as collmgr:

            for item in collmgr:  # print only top collections:
                print(item.name)

        # something recusive: print collection tree, just for fun
        with Collection("VGA", name="svens_coll") as coll:

            def recur(coll, space):
                print((" " * space) + str(coll))
                for c in coll:
                    recur(c, space + 3)
            recur(coll, 0)

        # read rec file entries
        with BaseDB('VGA') as db:
            with Recording(db, name=r'\\lifs010.cw01.contiwan.com\prj\path\to\filename.rec') as rec:
                print('measid:' + rec.id)
                print('driven dist:' + str(rec.vdy_dist()))
                print('for project:' + rec.project)

    see more parameter in class `Recording`

"""
# pylint: disable=E1101,C0103,C0302,R0201,W0125,W0201
# - import Python modules ---------------------------------------------------------------------------------------------
from sys import version_info
from os.path import join, sep, getsize
from math import radians, sin, cos, sqrt, asin
from getpass import getuser
from six import iteritems
try:
    from types import StringTypes
except ImportError:
    StringTypes = (str,)

# - import HPC modules ------------------------------------------------------------------------------------------------
from .base import BaseDB, crc
from ..core.tds import replace_server_path
from ..core.path import splitdrive
from ..core.dicts import DefDict

# - defines -----------------------------------------------------------------------------------------------------------
__all__ = ["CollManager", "Collection", "Recording", "CollException"]
ERR_NO_REC = 2
ERR_NO_COL = 3
ERR_NO_PAR = 4
ERR_NO_CON = 5

META_BASE = DefDict(r"\\lufs003x.li.de.conti.de", SHB=r"\\itfs002x.it.cn.conti.de")


# - classes / functions -----------------------------------------------------------------------------------------------
class CollException(Exception):
    """Collection manager exception class"""

    def __init__(self, error, message):
        """
        init this exception

        :param int error: error code
        :param str message: user readable message
        """
        Exception.__init__(self)
        self.error = error
        self.message = message

    def __str__(self):
        """return my own string representation"""
        return "ErrorCode %d \n %s" % (self.error, self.message)


class CollManager(object):  # pylint: disable=R0902
    """common class for collections"""

    # type of entry we are
    NONE, COLL, SHARE, REC, RECOPY = list(range(5))

    # type of mode we do:
    READ, APPEND, WRITE = list(range(3))
    # type of class we are, don't use it privately!
    CLSUB = {}

    def __init__(self, connection="VGA", **kw):  # pylint: disable=R0912,R0915,R1260
        r"""
        initialize a new collection or recording

        code::

            with CollManager('VGA') as collmgr:

                for item in collmgr:  # print only top collections:
                    print(item.name)

            # something recusive, just for fun
            with Collection("VGA", name="svens_coll") as coll:

                def recur(coll, space):
                    print((" " * space) + str(coll))
                    for c in coll:
                        recur(c, space + 3)
                recur(coll, 0)

        Some more samples can be reviewed inside unittest...

        :param BaseDB|str connection: connection name or `BaseDB` object
        :param dict \**kw: see below
        :keyword \**kw:
            * *name* (``str``): if starting with a name, this instance will be the root collection
            * *desc* (``str``): if name shouldn't be unique, add a description to be it
            * *mode* (``CollManager.READ|CollManager.WRITE``): go into read or write mode, use class constants!
        :raises hpc.CollException: once some error is encountered
        """
        self._mode = kw.pop('mode', CollManager.READ)
        self._type = kw.pop('type', CollManager.NONE)

        self._iteridx = 0
        self._myId = None
        self._childs = []
        self._uname = kw.pop('uname', None)
        self._childsfetched = False
        self._db = connection
        self._selfopen = False

        self._parent = kw.pop('parent', None)

        try:  # to get access first
            if isinstance(connection, BaseDB):
                self._db = connection
            else:
                self._db = BaseDB(connection, autocommit=False)
                self._selfopen = True
                # do we need that one?, as inserts don't seem to follow this...
                # if self._db.db_type[0] == -1:
                #     self._db("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI:SS'", commit=True)
        except Exception as _:  # pragma: no cover
            raise CollException(ERR_NO_CON, "DB connection failed!")

        if not self._uname:
            self._uname = list(self._db("SELECT USERID, NAME FROM VAL_GLOBAL_ADMIN.GBL_USERS "
                                        "WHERE LOGINNAME = :lnm OR USERID = 0 ORDER BY USERID DESC",
                                        lnm=getuser())[0])

        if self._type == CollManager.NONE:  # we're the first / initial one

            self._name = kw.pop('name', None)
            self._label = kw.pop('label', None)
            self._desc = kw.pop('desc', None)
            self._prio = kw.pop('prio', 'normal')

            if self._name is None:  # we're all, the root of collections, the manager
                self._myId = None
                self._name = "<CollManager>"
            else:  # so, we're the collection, let's see if we are in DB
                self._type = CollManager.COLL

                if isinstance(self._name, StringTypes):
                    sql = "SELECT COLLID FROM VAL_GLOBAL_ADMIN.CAT_COLLECTIONS WHERE NAME = :name"
                    sqa = {'name': self._name}
                    if self._desc is not None and self._desc:
                        sql += " AND COLLCOMMENT = :dscr"
                        sqa['dscr'] = self._desc
                    if self._label is None:
                        sql += " AND (CP_LABEL IS NULL OR CP_LABEL = '')"
                    else:
                        sql += " AND CP_LABEL = :label"
                        sqa['label'] = self._label
                    cids = [i[0] for i in self._db(sql, **sqa)]
                else:
                    cids = [self._name]

                if len(cids) == 1:  # good, we're already in and can use ourself!
                    self._myId = cids[0]
                    self._label, self._desc, self._parent, self._prio, self._uname[0], self._uname[1] = \
                        self._db("SELECT CP_LABEL, COLLCOMMENT, PARENTID, p.NAME, USERID, u.NAME "
                                 "FROM VAL_GLOBAL_ADMIN.CAT_COLLECTIONS "
                                 "INNER JOIN VAL_GLOBAL_ADMIN.GBL_PRIORITIES p USING(PRID) "
                                 "INNER JOIN VAL_GLOBAL_ADMIN.GBL_USERS u USING(USERID) "
                                 "WHERE COLLID = :cid", cid=self._myId)[0]
                    # update last usage by HPC
                    # self._db("UPDATE VAL_GLOBAL_ADMIN.CAT_COLLECTIONS SET LAST_USAGE = SYSTIMESTAMP "
                    #          "WHERE COLLID = :cid", cid=self._myId)

                elif self._mode == CollManager.READ:
                    raise CollException(ERR_NO_COL, "no collection by name '%s' existing!" % self._name)
                elif self._parent is None:
                    raise CollException(ERR_NO_PAR, "no parent for new collection of '%s' given!" % self._name)
                else:  # otherwise add a new entry  # pragma: no cover
                    if isinstance(self._parent, StringTypes):
                        self._parent = self._db("SELECT COLLID FROM VAL_GLOBAL_ADMIN.CAT_COLLECTIONS "
                                                "WHERE NAME = :coll", coll=self._parent)
                        if self._parent is None or not self._parent:
                            raise CollException(ERR_NO_PAR, "parent '%s' for new collection not found!"
                                                % self._parent)
                        self._parent = self._parent[0][0]
                    sql = ("INSERT INTO VAL_GLOBAL_ADMIN.CAT_COLLECTIONS (NAME, COLLCOMMENT, PARENTID, CP_LABEL, "
                           "PRID, USERID) "
                           "VALUES (:name, :dscr, :par, :label, (SELECT PRID FROM VAL_GLOBAL_ADMIN.GBL_PRIORITIES "
                           "WHERE NAME = :prio), :uid) RETURNING COLLID")
                    sqa = {'name': self._name, 'dscr': self._desc, 'par': self._parent,
                           'label': self._sqnullconv(self._label), 'prio': self._prio, 'uid': self._uname[0]}
                    self._myId = self._db(sql, **sqa)

        elif self._mode == CollManager.WRITE:  # mode set to write!  # pragma: no cover
            self._name = kw['name']
            self._label = kw.pop('label', None)
            self._prio = kw.pop('prio', 'normal')

            if self._type in (CollManager.COLL, CollManager.SHARE):  # what to add?
                self._desc = kw.pop('desc', None)
                # check if we need to update existing collection
                if isinstance(self._name, StringTypes):
                    sql, sqa = "SELECT COLLID FROM VAL_GLOBAL_ADMIN.CAT_COLLECTIONS WHERE NAME LIKE :name", \
                               {'name': self._name}
                    if self._label is not None:
                        sql += " AND CP_LABEL LIKE :label"
                        sqa['label'] = self._label
                    if self._desc is not None:
                        sql += " AND COLLCOMMENT LIKE :dscr"
                        sqa['dscr'] = self._desc
                    cids = [i[0] for i in self._db(sql, **sqa)]
                else:
                    cids = [self._name]
                if self._type == CollManager.SHARE:
                    res = self._db("SELECT SAHREDMAPID, p.NAME FROM VAL_GLOBAL_ADMIN.CAT_SHAREDCOLLECTIONMAP "
                                   "INNER JOIN VAL_GLOBAL_ADMIN.GBL_PRIORITIES p USING(PRID) "
                                   "WHERE PARENT_COLLID = :par AND CHILD_COLLID = :cld",
                                   par=self._parent, cld=cids[0])
                    if res:
                        self._myId, self._prio = res
                    else:
                        self._myId = self._db("INSERT INTO VAL_GLOBAL_ADMIN.CAT_SHAREDCOLLECTIONMAP "
                                              "(PARENT_COLLID, CHILD_COLLID, PRID) VALUES (:par, :cld, "
                                              "(SELECT PRID FROM VAL_GLOBAL_ADMIN.GBL_PRIORITIES "
                                              "WHERE NAME = :prio)) RETURNING SAHREDMAPID",
                                              par=self._parent, cld=cids[0], prio=self._prio)
                elif len(cids) == 1:  # update parent then
                    self._myId = cids[0]
                    self._db("UPDATE VAL_GLOBAL_ADMIN.CAT_COLLECTIONS SET PARENTID = :par WHERE COLLID = :coll",
                             par=self._parent, coll=self._myId)
                else:  # insert new one
                    sql = ("INSERT INTO VAL_GLOBAL_ADMIN.CAT_COLLECTIONS (PARENTID, PRID, NAME, USERID, CP_LABEL$M) "
                           "VALUES (:par, (SELECT PRID FROM VAL_GLOBAL_ADMIN.GBL_PRIORITIES WHERE NAME = :prio), "
                           ":name, :uid, :label$V) RETURNING COLLID")
                    sqa = {'par': self._parent, 'name': self._name, 'label': self._sqnullconv(self._label),
                           'prio': self._prio, 'uid': self._uname[0]}
                    if self._desc is None:
                        sql = sql.replace("$M", "").replace("$V", "")
                    else:
                        sql = sql.replace("$M", ", COLLCOMMENT").replace("$V", ", :comm")
                        sqa['comm'] = self._desc
                    self._myId = self._db(sql, **sqa)
            else:  # add a recording
                self._get_rec_details(self._name)
                self._relts = kw.pop("relts", [])
                if self._relts and not isinstance(self._relts[0], list):  # be a list of relative timestamp's lists
                    self._relts = [self._relts]
                if kw.get("section") is not None:
                    rel = kw["section"]
                    self._relts = [[i.start_ts if i.rel[0] else (i.start_ts - self._timestamp[0]),
                                    i.end_ts if i.rel[1] else (i.end_ts - self._timestamp[0])] for i in rel]

                # for rel in self._relts:
                #     try:
                #         self._relts[0] = int(self._relts[0][:-1]) \
                #             if type(self._relts[0]) in StringTypes and self._relts[0].endswith('R') \
                #             else int(self._relts[0]) - self._timestamp[0]
                #         self._relts[1] = int(self._relts[1][:-1]) \
                #             if type(self._relts[1]) in StringTypes and self._relts[1].endswith('R') \
                #             else int(self._relts[1]) - self._timestamp[0]
                #     except Exception as _:
                #         pass

                sql = "SELECT COUNT(COLLMAPID) FROM VAL_GLOBAL_ADMIN.CAT_COLLECTIONMAP WHERE COLLID = :cid " \
                      "AND MEASID = :mid"
                sqa = {"cid": self._parent, "mid": self._myId, "uid": self._uname[0]}
                for b, e in self._relts:
                    sqla = "  AND BEGINRELTS $B AND ENDRELTS $E"
                    if b is None and e is None:
                        sqla = sqla.replace("$B", "IS NULL").replace("$E", "IS NULL")
                    else:
                        sqla = sqla.replace("$B", "= :beg").replace("$E", "= :end")
                        sqa.update({"beg": b, "end": e})

                    if self._db(sql + sqla, **sqa)[0][0] == 0:
                        if "beg" not in sqa:
                            sqa.update({"beg": None, "end": None})
                        mid = self._db("INSERT INTO VAL_GLOBAL_ADMIN.CAT_COLLECTIONMAP (COLLID, MEASID, "
                                       "BEGINRELTS, ENDRELTS, USERID) VALUES (:cid, :mid, :beg, :end, :uid) "
                                       "RETURNING COLLMAPID", **sqa)
                        self._mapid.append(mid)

        else:  # retrieve the details of me
            if self._type in (CollManager.COLL, CollManager.SHARE):  # details from collection
                self._myId = kw['name']
                if "data" in kw:
                    self._mapid, self._name, self._label, self._desc, self._prio, self._parent = kw["data"]
                else:
                    self._name, self._label, self._desc, self._prio, self._uname[0], self._uname[1] = \
                        self._db("SELECT c.NAME, c.CP_LABEL, c.COLLCOMMENT, p.NAME, USERID, u.NAME "
                                 "FROM VAL_GLOBAL_ADMIN.CAT_COLLECTIONS c "
                                 "INNER JOIN VAL_GLOBAL_ADMIN.GBL_PRIORITIES p USING(PRID) "
                                 "INNER JOIN VAL_GLOBAL_ADMIN.GBL_USERS u USING(USERID) "
                                 "WHERE COLLID = :coll", coll=self._myId)[0]

            elif self._type == CollManager.REC:  # details from recording
                self._relts = []
                if "data" in kw:
                    self._timestamp = [None, None]
                    self._childsfetched = True
                    self._myId, self._mapid, self._relts, self._childs = kw["name"], kw["map"], kw["rel"], kw["childs"]
                    self._name, self._chash, self._timestamp[0], self._timestamp[1], self._dist, self._gpsdist, \
                        self._fsize, self._rectime, self._import, self._recprj, self._fstate, self._location, \
                        self._region = kw["data"]
                    self._import = self._adapt_ts(self._import)
                else:
                    self._get_rec_details(kw['name'])

            else:  # only one thing left over: recording copy (RECOPY)
                if "data" in kw:
                    self._childsfetched = True
                    self._myId = kw["name"]
                    self._parent, self._name, self._import, self._fstate, self._location = kw["data"]
                    self._relts = kw["rel"]
                    self._timestamp = [None, None]
                    self._chash, self._timestamp[0], self._timestamp[1], self._dist, self._gpsdist, self._fstate, \
                        self._rectime, self._import, self._recprj, self._fstate, _, self._region = kw["par"]
                    self._import = self._adapt_ts(self._import)
                else:
                    self._relts = []
                    self._get_rec_details(kw['name'])

    def add(self, item):  # pragma: no cover
        """
        add a collection or recording

        :param Recording|Collection item: recording or collection
        """
        if isinstance(item, Recording):
            i = Recording(self._db, type=CollManager.REC, parent=self._myId, mode=CollManager.WRITE, name=item.id,
                          relts=item.relts)
            self._childs.append(i)

        elif isinstance(item, Collection):
            i = Collection(self._db, type=CollManager.COLL, parent=self._myId, mode=CollManager.WRITE,
                           name=item.name, desc=item.desc)
            self._childs.append(i)

        else:
            raise ValueError("not allowed to add {!s}".format(item))

        return i

    def __del__(self):
        """disconnect"""
        if self._parent is None:
            self.close()

    def __str__(self):
        """return string text summary of me"""
        if self._type == CollManager.NONE:
            return "<collection summary from {!s}>".format(self._db)
        if self._type == CollManager.COLL:
            return "<collection {}: '{}' ({})>".format(self._myId, self._name, "" if self._desc is None else self._desc)
        if self._type == CollManager.SHARE:
            return "<shared collection {}: '{}' ({})>".format(self._myId, self._name,
                                                              "" if self._desc is None else self._desc)
        if self._type == CollManager.REC:
            return "<recording {}: '{}' ({}-{})>".format(self._myId, self._name, self._timestamp[0], self._timestamp[1])

        return "<recording copy {}: '{}' ({})>".format(self._myId, self._name, self._location)

    def __iter__(self):
        """start iterating through test cases"""
        self._iteridx = 0
        return self

    def next(self):
        """next child item to catch and return"""
        if self._iteridx >= self._get_childs():
            raise StopIteration

        self._iteridx += 1
        return self[self._iteridx - 1]

    if version_info > (3, 0):
        __next__ = next

    def __getitem__(self, idx):
        """provide a slice index to be able to iterate through the childs"""
        nchilds = self._get_childs()
        if isinstance(idx, int) and 0 <= idx < nchilds:
            return self._childs[idx]
            # if cls is None:
            #     cls = CollManager.CLSUB[self._childs[idx].kind](self._db, type=self._childs[idx].kind,
            #                                                     parent=self._myId, name=self._childs[idx])
            #     self._childs[idx].clsid = id(cls)
            #     self._childs[idx].cls = cls
            # return cls

        # untested:
        # elif type(idx) == slice and min(0, idx.start, idx.stop) == 0 and max(nchilds, idx.start, idx.stop):
        #     return [CollManager.CLSUB[self._childs[idx][1]](self._db, parent=self._myId, name=self._childs[idx][0],
        #                                                     type=self._childs[idx][1])
        #             for i in range(idx.start, idx.stop, idx.step)]

        raise IndexError

    def __len__(self):
        """provide length of sub items / childs"""
        return self._get_childs()

    def __enter__(self):
        """being able to use with statement"""
        return self

    def __exit__(self, *args):
        """close connection"""
        self.close(True, args[0] is not None)

    def close(self, commit=True, rollback=False):
        """
        commit changes and close connection

        :param bool commit: we should commit
        :param bool rollback: we need to rollback
        """
        if self._db is None or not self._selfopen:
            return
        if rollback:
            self._db.rollback()
        elif commit:
            self._db.commit()
        self._db.close()
        self._db = None

    def _get_rec_details(self, name):
        """retrieve my own details from name or id"""
        self._timestamp, self._import, self._fstate, self._mapid = [None, None], None, None, []

        sqa = {"meas": name}
        if isinstance(name, StringTypes):
            recname = replace_server_path(name, True).lower()
            srv = splitdrive(recname)
            if srv[0] != '':
                sql = 'CRC_NAME = :crc AND SERVERSHARE = :lnm AND BASEPATH = :bpth'
                sqa = {"crc": crc(recname), "lnm": srv[0], "bpth": srv[1].strip(sep)}
            else:
                sql = 'LOWER(RECFILEID) = :meas'
        else:
            sql = 'MEASID = :meas'

        try:
            self._myId, self._name, self._chash, self._timestamp[0], self._timestamp[1], self._dist, \
                self._gpsdist, self._fsize, self._rectime, self._import, self._recprj, self._fstate, \
                self._location, self._region = \
                self._db("SELECT distinct MEASID, FILEPATH, CONTENTHASH, BEGINABSTS, ENDABSTS, "
                         "RECDRIVENDIST, GPSDRIVENDIST, FILESIZE, RECTIME, IMPORTDATE, p.NAME, STATUS, "
                         "LOC, REGION FROM VAL_GLOBAL_ADMIN.CAT_FILES "
                         "INNER JOIN VAL_GLOBAL_ADMIN.GBL_PROJECT p USING(PID) "
                         "INNER JOIN VAL_GLOBAL_ADMIN.GBL_LOCATION USING(LOCATION) "
                         "WHERE " + sql, **sqa)[0]

            self._import = self._adapt_ts(self._import)
        except Exception as _:
            raise CollException(ERR_NO_REC, "recording '%s' does not exist!" % name)

    @staticmethod
    def _adapt_ts(ts):
        """adapt timestamp"""
        if isinstance(ts, StringTypes):  # for sqlite
            idx = ts.find(' ')
            idx = idx if idx > 0 else len(ts)
            return ts[:idx]

        return ts.strftime('%Y-%m-%d')

    def _get_childs(self):
        """retrieve sub items / childs of us"""
        if self._childsfetched:
            return len(self._childs)

        # if self._type != CollManager.RECOPY and self._myId is None:  # as I said: we're all
        #     self._childs = [Child(i[0], CollManager.COLL, name=i[1], label=i[2], desc=i[3], par=i[4], prio=i[5])
        #                    for i in self._db("SELECT COLLID, c.NAME, CP_LABEL, COLLCOMMENT, PARENTID, p.NAME "
        #                                               "FROM VAL_GLOBAL_ADMIN.CAT_COLLECTIONS c "
        #                                               "INNER JOIN VAL_GLOBAL_ADMIN.GBL_PRIORITIES p USING(PRID) "
        #                                               "WHERE PARENTID IS NULL ORDER BY COLLID")]
        # elif len(self._childs) == 0:  # otherwise we're a definite collection
        if self._type in (CollManager.COLL, CollManager.SHARE):
            # check if we have child (shared)collections
            self._childs = [(Collection if i[1] == CollManager.COLL else SharedColl)
                            (self._db, name=i[0], uname=self._uname, type=i[1],
                             data=(i[2], i[3], i[4], i[5], i[6], i[7],))
                            for i in self._db("WITH SHCOL(COLLID, KIND, MID) AS (SELECT COLLID, %d, 0 "
                                              "FROM VAL_GLOBAL_ADMIN.CAT_COLLECTIONS WHERE PARENTID = :par "
                                              "UNION SELECT CHILD_COLLID, %d, SAHREDMAPID "
                                              "FROM VAL_GLOBAL_ADMIN.CAT_SHAREDCOLLECTIONMAP "
                                              "WHERE PARENT_COLLID = :par) "
                                              "SELECT COLLID, KIND, MID, c.NAME, CP_LABEL, COLLCOMMENT, "
                                              "p.NAME, PARENTID FROM VAL_GLOBAL_ADMIN.CAT_COLLECTIONS c "
                                              "INNER JOIN VAL_GLOBAL_ADMIN.GBL_PRIORITIES p USING(PRID) "
                                              "INNER JOIN SHCOL USING(COLLID) ORDER BY COLLID"
                                              % (CollManager.COLL, CollManager.SHARE), par=self._myId)]
            # check for child recordings
            meass = {}
            for i in self._db("SELECT MEASID, COLLMAPID, BEGINRELTS, ENDRELTS, FILEPATH, "
                              "CONTENTHASH, BEGINABSTS, ENDABSTS, RECDRIVENDIST, GPSDRIVENDIST, "
                              "FILESIZE, RECTIME, IMPORTDATE, PROJECT, STATUS, LOC, REGION "
                              "FROM VAL_GLOBAL_ADMIN.CAT_COLLECTIONMAP "
                              "INNER JOIN VAL_GLOBAL_ADMIN.CAT_DMT_FILES USING(MEASID) "
                              "WHERE COLLID = :coll ORDER BY FILEPATH, BEGINRELTS",
                              coll=self._myId):
                if i[0] not in meass:
                    meass[i[0]] = {"map": [i[1]], "rel": [[i[2], i[3]]], "data": i[4:], "childs": []}
                else:
                    m = meass[i[0]]
                    m["map"].append(i[1])
                    m["rel"].append([i[2], i[3]])

            # Child(i[0], CollManager.REC, mapid=[i[1]], rel=[(i[2], i[3],)], path=i[4], hash=i[5],
            #       begts=i[6], endts=i[7], dist=i[8], gps=i[9], fsz=i[10], rtm=i[11], impdt=i[12],
            #       prj=i[13], stat=i[14], loc=i[15], reg=i[16])
            if meass:
                for i in self._db("SELECT PARENT, MEASID, FILEPATH, IMPORTDATE, STATUS, LOC "
                                  "FROM VAL_GLOBAL_ADMIN.CAT_DMT_FILES WHERE PARENT IN ("
                                  "SELECT MEASID FROM VAL_GLOBAL_ADMIN.CAT_COLLECTIONMAP "
                                  "INNER JOIN VAL_GLOBAL_ADMIN.CAT_DMT_FILES USING(MEASID) "
                                  "WHERE COLLID = :coll)", coll=self._myId):
                    par = meass[i[0]]
                    par["childs"].append(RecordingCopy(self._db, name=i[0], uname=self._uname, data=i[1:],
                                                       par=par["data"][1:], rel=par["rel"]))

            self._childs.extend([Recording(self._db, name=k, uname=self._uname, data=v["data"], map=v["map"],
                                           rel=v["rel"], childs=v["childs"]) for k, v in iteritems(meass)])

        self._childsfetched = True
        return len(self._childs)

    def __getattr__(self, name):
        """
        use it for code reduction of property handling, see above attribute GETATTR for valid attributnames (keys)
        additional attributes are inherited from CollManager: id, type, name
        """
        try:
            bak = self.__class__.GETATTR[name]
            return getattr(self, bak[0]) if len(bak) == 1 else getattr(self, bak[0])[bak[1]]
        except Exception:
            raise AttributeError

    def _sqnullconv(self, item):
        """convert null values to empty strings on sqlite"""
        return ('' if item is None else item) if self._db.db_type[0] == BaseDB.SQLITE else item

    @classmethod
    def regsub(cls, theid):
        """use it for subclass registration as we need to return proper child classes for iteration"""
        def inner(subcls):
            """update class dict"""
            cls.CLSUB[theid] = subcls
            return subcls
        return inner

    def commit(self):
        """support for external commit to db"""
        self._db.commit()

    def rollback(self):
        """support for external rollback to db"""
        self._db.rollback()

    @property
    def dbase(self):
        """return db connection"""
        return self._db

    def sql(self, sql, **parms):
        """execute with background db"""
        return self._db(sql, **parms)

    @property
    def type(self):
        """return my type: REC or COLL"""
        return self._type

    @property
    def name(self):
        """return my name"""
        return self._name

    @property
    def user(self):
        """return my name"""
        return self._uname

    @name.setter
    def name(self, value):
        """set new name for collection"""
        if self._type == CollManager.COLL:
            self._db("UPDATE VAL_GLOBAL_ADMIN.CAT_COLLECTIONS SET NAME = :name WHERE COLLID = :coll",
                     name=value, coll=self._myId)
        else:
            raise AttributeError("cannot change name of me!")


@CollManager.regsub(CollManager.COLL)
class Collection(CollManager):
    """
    A collection can contain other collections and for sure recordings.

    Collections have a name and optional description, that's it!

    - You can add another sub-collection via **add_coll** method,
    - another recording can be added through **add_rec**
    - Removal of an subitem (Collection, Recording) is done via **remove** method.
    - Export or Import to/from bpl files

    Several other infos are available through properties, e.g.:

        - name:  complete url of collection  (str)
        - id:  cb internal id  (int)
        - desc:  description (can also be set here)  (str)
        - parent:  parent collection (if defined) (`Collection`)
        - active:  flag if collection is used
        - prio:  priority, e.g. to sort sub collections inside a collection
    """

    GETATTR = {"id": ("_myId",), "desc": ("_desc",), "prio": ("_prio",), "parent": ("_parent",), "label": ("_label",)}
    SETATTR = {"desc": ("_desc",)}

    if False:  # helping intellisense
        id = desc = prio = parent = desc = None

    def __init__(self, *args, **kw):
        r"""
        inti a collection which can contain other collections and for sure recordings.
        Collections have a name and optional description, that's it!

        You can add another sub-collection via **add_coll** method,
        another recording can be added through **add_rec**
        Removal of an subitem is done via **remove** method.

        :param dict \**kw: see below
        :keyword \**kwargs:
            * *name* (``str``): name of collection to use (or create if not existing)
            * *desc* (``str``): description of collection
        """
        CollManager.__init__(self, *args, **kw)

    def add_coll(self, **kw):
        r"""
        add a collection

        :param dict \**kw: see below
        :keyword \**kwargs:
            * *name* (``str``): name of collection
            * *desc* (``str``): description of it
        :return: collection
        :rtype: ``Collection``
        """
        if 'type' not in kw or kw['type'] not in (CollManager.COLL, CollManager.SHARE):
            kw['type'] = CollManager.COLL
        c = Collection(self._db, parent=self._myId, mode=CollManager.WRITE, **kw)
        self._childs.append(c)
        return c

    def add_rec(self, **kw):
        r"""
        add a recording

        :param dict \**kw: see below
        :keyword \**kwargs:
            * *name* (``str``): recfile name or path or it's id
        :return: recording
        :rtype: ``Recording``
        """
        kw['type'] = CollManager.REC
        r = Recording(self._db, parent=self._myId, mode=CollManager.WRITE, **kw)
        self._childs.append(r)
        return r

    def remove(self, sub):
        """
        remove something

        :param Recording|Collection sub: a subitem to be removed, similar to list.remove
        """
        if sub.type in [CollManager.REC, CollManager.RECOPY]:
            for i in sub.map_id:
                self._db("DELETE FROM VAL_GLOBAL_ADMIN.CAT_COLLECTIONMAP WHERE COLLMAPID = :map", map=i)
        else:
            for i in [sub.remove(i) for i in sub]:
                for k in sub._childs:  # pylint: disable=W0212
                    if id(k) == i:
                        sub._childs.remove(k)  # pylint: disable=W0212
                        break

            if sub.type == CollManager.COLL:
                self._db("DELETE FROM VAL_GLOBAL_ADMIN.CAT_COLLECTIONS WHERE COLLID = :coll", coll=sub.id)
            else:
                self._db("DELETE FROM VAL_GLOBAL_ADMIN.CAT_SHAREDCOLLECTIONMAP WHERE SAHREDMAPID = :mid",
                         coll=sub.map_id)

        return id(sub)


@CollManager.regsub(CollManager.SHARE)
class SharedColl(CollManager):
    """
    a shared collection is a special kind of collection which can be used in several parent collections

    removing a shared collection means deleting the link to it,
    the sub collection itself is only removed if the last link is deleted

    a shared collection can contain other (shared) collections and for sure recordings

    otherwise a shared collection is similar to the `Collection`
    """

    GETATTR = {"id": ("_myId",), "desc": ("_desc",), "prio": ("_prio",), "parent": ("_parent",), "label": ("_label",)}
    SETATTR = {"desc": ("_desc",)}

    if False:  # helping intellisense
        id = desc = prio = parent = description = None

    def __init__(self, *args, **kw):
        r"""
        init a collection which can contain other collections and for sure recordings
        collections have a name and optional description, that's it!

        you can add another sub-collection via **add_coll** method,
        another recording can be added through **add_rec**
        removal of an subitem is done via **remove** method

        :param tuple \*args: see ``CollManager`` for more details
        :param dict \**kwargs: see ``CollManager`` for more details
        :keyword \**kwargs:
            * *name* (``str``): name of collection to use (or create if not existing)
            * *desc* (``str``): description of collection

        """
        CollManager.__init__(self, *args, **kw)

    # 2B taken over from Collection:
    # __contains__ = Collection.__dict__['__contains__']


@CollManager.regsub(CollManager.REC)
class Recording(CollManager):
    """
    A recording represents the data from cat_files (measid).

    Several other infos are available through properties, e.g.:

        - name:  complete path and file name
        - id:  measurement id
        - timestamp:  tuple of [abs. start ts, abs. end ts] time stamps ([int, int])
        - state:  status of file on server (transmitted: copied to server, archived: moved to archive)
        - hash:  unique hash key of rec file (str)
        - rectime:  recording time  (daytime object)
        - import_date:  day/time of adding the rec file to the server / db  (daytime object)
        - beginrelts:  first relative time stamp of section to be used in collection  (int)
        - endrelts:  last relative time stamp of section used in collection  (int)
        - distance:  driven distance based on VDY
        - gpsdistance:  driven distance based on GPS positions
        - filesize:  size in byte
        - project:  name of project the rec file belongs to
        - filestate:  acceptance state of the file (int: 1 := unchecked, 2 := rejected, 3 := accepted)

    Set properties for Recording inside a Collection:

        - beginrelts: first relative time stamp of section to be used in collection
        - endrelts:  last relative time stamp of section used in collection

    """

    GETATTR = {"id": ("_myId",), "parent": ("_parent",), "filepath": ("_name",), "timestamp": ("_timestamp",),
               "hash": ("_chash",), "rectime": ("_rectime",), "import_date": ("_import",), "project": ("_recprj",),
               "relts": ("_relts",), "distance": ("_dist",), "gpsdistance": ("_gpsdist",), "filesize": ("_fsize",),
               "map_id": ("_mapid",), "filestate": ("_fstate",), "location": ("_location",), "region": ("_region",)}

    if False:  # helping intellisense
        id = timestamp = state = hash = rectime = import_date = \
            beginrelts = endrelts = distance = gpsdistance = filesize = map_id = project = loation = region = None

    def __init__(self, *args, **kw):
        r"""
        init recording which has a name being path/to/a/filename.

        Several other infos are available through properties, e.g.:
        timestamp, state of recording, recording time, etc.

        :param tuple \*args: see ``CollManager`` for more details
        :param dict \**kwargs: see ``CollManager`` for more details
        :keyword \**kwargs:
            * *name* (``str``): name of recording to use
        """
        kw['type'] = kw.pop('type', CollManager.REC)
        if not args and "connection" not in kw:
            kw["connection"] = "VGA"

        CollManager.__init__(self, *args, **kw)
        self.addColl = None

    @property
    def dist_file(self):
        """
        :return: sqlite DB distance file name
        :rtype: str
        """
        return join(META_BASE[self._location], 'meta', self._recprj, '_DISTANCE',
                    self._chash[:4], self._chash + ".sqlite")

    def _calc_dist(self, which, start, stop):
        """
        retrieve and calc the distance

        :param str which: currently supports 'vdy' and 'gps'
        :param int start: start time
        :param int stop: stop time
        :return: distance from start to stop
        :rtype: float
        :raises hpc.CollException: if no distance data is available
        """
        assert which.upper() in ('VDY', 'GPS'), "only 'VDY' or 'GPS' is supported!"
        try:
            if getsize(self.dist_file) == 0:
                raise Exception
        except Exception:
            raise CollException(ERR_NO_CON, "no VDY or GPS data available from data mining!")

        # build sql query
        sql = "SELECT %s FROM %s" % ("MTSTS, VELOCITY" if which == 'VDY' else "LATITUDE, LONGITUDE", which)
        fltr, fidx = ["WHERE", "AND"], 0
        if isinstance(start, int):
            sql += " {} MTSTS >= {}".format(fltr[fidx], start)
            fidx += 1
        if isinstance(stop, int):
            sql += " {} MTSTS <= {}".format(fltr[fidx], stop)

        # connect and load data from sqlite file
        with BaseDB(self.dist_file) as ddb:
            data = ddb(sql)
            if not data:
                return None

        if which == 'VDY':  # calculate VDY distance
            mts, vdy = list(zip(*data))
            dist = 0.
            for t, v in zip(list(zip(mts[:-1], mts[1:])), list(zip(vdy[:-1], vdy[1:]))):
                dt, dv = (t[1] - t[0]) * 0.000001, v[1] - v[0]
                # dist += v[0] * dt + 0.5 * (dv / dt) * dt**2
                dist += dt * (v[0] + 0.5 * dv)
            dist /= 1000.  # [km]
        else:  # calculate GPS distance
            def haversine(start, end):
                """calculate the haversine distance"""
                lat1, lon1 = start
                lat2, lon2 = end

                d_lat = radians(lat2 - lat1)
                d_lon = radians(lon2 - lon1)
                lat1 = radians(lat1)
                lat2 = radians(lat2)

                a = sin(d_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(d_lon / 2) ** 2
                c = 2 * asin(sqrt(a))

                return 6372.8 * c  # Earth radius in kilometers

            dist = sum([haversine(data[i - 1], data[i]) for i in range(1, len(data))])

        return dist

    def vdy_dist(self, start=None, stop=None):
        """
        calculate VDY distance between start and stop times, default: calc for the whole recording

        :param int start: use specific start time
        :param int stop: use specific stop time
        :return: distance
        :rtype: float
        """
        return self._calc_dist('VDY', start, stop)

    def gps_dist(self, start=None, stop=None):
        """
        calculate GPS distance between start and stop times, default: calc for the whole recording

        :param int start: use specific start time
        :param int stop: use specific stop time
        :return: distance
        :rtype: float
        """
        return self._calc_dist('GPS', start, stop)

    def gps_pos(self, timestamp=None):
        """
        GPS position at a certain timestamp,
        if None, first one is returned, otherwise closest to timestamp

        :param int timestamp: MTS timestamp
        :return: tuple of (LAT, LON)
        :rtype: tuple
        """
        with BaseDB(self.dist_file) as ddb:
            sql = "SELECT LATITUDE, LONGITUDE FROM GPS %sLIMIT 1"
            if timestamp is None:
                sql %= ""
            else:
                sql %= "ORDER BY ABS(MTSTS - %d) " % timestamp

            pos = ddb(sql)
            if len(pos) == 1:
                return pos[0]

        return None


@CollManager.regsub(CollManager.RECOPY)
class RecordingCopy(CollManager):
    """
    A recording represents the data from cat_files (measid).

    Several other infos are available through properties, e.g.:

        - name:  complete path and file name
        - id:  parent id
        - timestamp:  tuple of [abs. start ts, abs. end ts] time stamps ([int, int])
        - state:  status of file on server (transmitted: copied to server, archived: moved to archive)
        - hash:  unique hash key of rec file (str)
        - rectime:  recording time  (daytime object)
        - import_date:  day/time of adding the rec file to the server / db  (daytime object)
        - distance:  driven distance based on VDY
        - gpsdistance:  driven distance based on GPS positions
        - filesize:  size in byte
        - project:  name of project the rec file belongs to
        - filestate:  acceptance state of the file (int: 1 := unchecked, 2 := rejected, 3 := accepted)

    """

    GETATTR = {"id": ("_myId",), "parent": ("_parent",), "filepath": ("_name",), "timestamp": ("_timestamp",),
               "state": ("_state",), "hash": ("_chash",), "rectime": ("_rectime",), "import_date": ("_import",),
               "project": ("_recprj",), "relts": ("_relts",), "distance": ("_dist",), "gpsdistance": ("_gpsdist",),
               "filesize": ("_fsize",), "filestate": ("_fstate",), "location": ("_location",), "region": ("_region",)}
    SETATTR = {}

    if False:  # helping intellisense
        id = timestamp = state = hash = rectime = import_date = \
            beginrelts = endrelts = distance = gpsdistance = filesize = project = loation = region = None

    def __init__(self, *args, **kw):
        r"""
        init recording copy, it has a name being path/to/a/filename.

        Several other infos are available through properties, e.g.:
        timestamp, state of recording, recording time, etc.

        :param tuple \*args: see ``CollManager`` for more details
        :param dict \**kwargs: see ``CollManager`` for more details
        :keyword \**kwargs:
            * *name* (``str``): name of recording to use
        """
        kw['type'] = kw.pop('type', CollManager.RECOPY)
        if not args and "connection" not in kw:
            kw["connection"] = "VGA"

        CollManager.__init__(self, *args, **kw)
        self.addColl = None

    def __getitem__(self, item):
        """
        catch all available types (using global var?)
        catch name / value and save into generated class -> type('MET', .., ..) and return it

        :param object item: todo
        :return: value
        :rtype: object
        """


# class Child(dict):
#     """child object
#     """
#
#     def __init__(self, ident, kind, **kwargs):
#         dict.__init__(self, ident=ident, kind=kind)
#         self.update(kwargs)
#
#     def __setattr__(self, key, value):
#         if key in ["ident", "kind"]:
#             raise AttributeError(key)
#         self[key] = value
#
#     def __getattr__(self, item):
#         if item in self:
#             return self[item]
#         elif type(item) == tuple:
#             return tuple([self[k] for k in self.keys() if not k.startswith('_')])
#         else:
#             return None
#
#     def __hash__(self):
#         return hash((self.ident, self.kind,))
#
#     def __eq__(self, other):
#         return self.ident == other.ident and self.kind == other.ident
#
#     def get(self, key):
#         if type(key) in (tuple, list):
#             return [self[k] for k in key]
#         elif key in self:
#             return self[key]
#         else:
#             return None
