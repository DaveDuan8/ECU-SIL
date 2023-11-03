"""
stk/db/catalog.py
-----------------

catalog API

interface to CAT_FILES and CAT_COLLECTIONS tables with classes

- `Collection`  use collection tree to read/write collections with recordings
- `Recording`   get recording data from db

**Usage Example:**

    .. python::

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


:org:           Continental AG
:author:        Sven Mertens

:version:       $Revision: 1.22 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/11/18 23:46:37CET $
"""
# pylint: disable=E1101,C0103,R0201,R0924,W0142,W0201
# - import Python modules ---------------------------------------------------------------------------------------------
from types import StringTypes
from os.path import splitunc, join
from math import radians, sin, cos, sqrt, asin
from xml.etree.ElementTree import Element, SubElement, tostring, parse
from xml.dom.minidom import parseString

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.db.db_common import BaseDB, AdasDBError

# - defines -----------------------------------------------------------------------------------------------------------
__all__ = ["Collection", "Recording", "CollException", "CollManager"]
ERR_NO_REC = 2
CAT_LOCATIONUSAGE_VERSION = 13


# - classes / functions -----------------------------------------------------------------------------------------------
class CollException(Exception):
    """Collection manager exception class"""
    def __init__(self, error, message):
        Exception.__init__(self)
        self.error = error
        self.message = message

    def __str__(self):
        return "ErrorCode %d \n %s" % (self.error, self.message)


class CollManager(object):  # pylint: disable=R0902,R0924
    """common class for collections
    """
    # type of entry we are
    NONE, COLL, SHARE, REC = range(4)

    # type of mode we do:
    READ, APPEND, WRITE = range(3)
    # type of class we are, don't use it privately!
    CLSUB = {}

    def __init__(self, connection, **kw):  # pylint: disable=R0912,R0915
        """initialize a new collection or recording

        .. python::

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

        :param connection: connection name or BaseDB object
        :type connection: BaseDB | str
        :keyword name: if starting with a name, this instance will be the root collection
        :type name: str
        :keyword desc: if name shouldn't be unique, add a description to be it
        :type desc: str
        :keyword mode: go into read or write mode, use class constants!
        :type mode: CollManager.READ | CollManager.WRITE
        """
        self._mode = kw.pop('mode', CollManager.READ)
        self._type = kw.pop('type', CollManager.NONE)

        self._iteridx = 0
        self._myId = None
        self._childs = []
        self._db = connection
        self._selfopen = False
        self._asign = kw.pop('asgnby', False)

        self._parent = kw.pop('parent', None)

        if self._type == CollManager.NONE:  # we're the first / initial one
            try:  # to get access first
                if isinstance(connection, BaseDB):
                    self._db = connection
                else:
                    self._db = BaseDB(connection)
                    self._selfopen = True
                # do we need that one?, as inserts don't seem to follow this...
                if self._db.db_type[0] == -1:
                    self._db.execute("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI:SS'", commit=True)
                self._asign = "ASGNBY" in [i[0] for i in self._db.get_columns("CAT_COLLECTIONMAP")]
            except:
                raise AdasDBError("DB connection failed!")

            if self._db._sub_versions['CAT'] < CAT_LOCATIONUSAGE_VERSION:
                raise AdasDBError("update DB! DB version for cat_files: %d, min. needed: %d" %
                                  (self._db._sub_versions['CAT'], CAT_LOCATIONUSAGE_VERSION))
            self._name = kw.pop('name', None)
            self._label = kw.pop('label', None)
            self._desc = kw.pop('desc', None)
            self._prio = kw.pop('prio', 'normal')

            if self._name is None:  # we're all, the root of collections, the manager
                self._myId = None
                self._name = "<CollManager>"
            else:  # so, we're the collection, let's see if we are in DB
                self._type = CollManager.COLL

                if type(self._name) in StringTypes:
                    sql = "SELECT COLLID FROM CAT_COLLECTIONS WHERE NAME = :name"
                    sqa = {'name': self._name}
                    if self._desc is not None:
                        sql += " AND COLLCOMMENT = :desc"
                        sqa['desc'] = self._desc
                    if self._label is None:
                        sql += " AND (CP_LABEL IS NULL OR CP_LABEL = '')"
                    else:
                        sql += " AND CP_LABEL = :label"
                        sqa['label'] = self._label
                    cids = [i[0] for i in self._db.execute(sql, **sqa)]
                else:
                    cids = [self._name]

                if len(cids) == 1:  # good, we're already in and can use ourself!
                    self._myId = cids[0]
                    self._label, self._desc, self._active, self._parent, self._prio = \
                        self._db.execute("SELECT CP_LABEL, COLLCOMMENT, IS_ACTIVE, PARENTID, p.NAME "
                                         "FROM CAT_COLLECTIONS INNER JOIN GBL_PRIORITIES p USING(PRID) "
                                         "WHERE COLLID = :cid", cid=self._myId)[0]

                    # if self._parent is not None:
                    #     raise ValueError("collection with name / desc already existing")
                elif self._parent is None:  # otherwise add a new entry
                    sql = ("INSERT INTO CAT_COLLECTIONS (NAME, CP_LABEL, PRID, USERID$M) VALUES (:name, :label, "
                           "(SELECT PRID FROM GBL_PRIORITIES WHERE NAME = :prio), $UID$V) RETURNING COLLID")
                    sqa = {'name': self._name, 'label': self._sqnullconv(self._label), 'prio': self._prio}
                    if self._desc is not None:
                        sql = sql.replace("$M", ", COLLCOMMENT").replace("$V", ", :comm")
                        sqa['comm'] = self._desc
                    else:
                        sql = sql.replace("$M", "").replace("$V", "")
                    self._myId = self._db.execute(sql, **sqa)

        elif self._mode == CollManager.WRITE:  # mode set to write!
            self._name = kw['name']
            self._label = kw.pop('label', None)
            self._prio = kw.pop('prio', 'normal')

            if self._type in (CollManager.COLL, CollManager.SHARE):  # what to add?
                self._desc = kw.pop('desc', None)
                # check if we need to update existing collection
                if type(self._name) in StringTypes:
                    sql, sqa = "SELECT COLLID FROM CAT_COLLECTIONS WHERE NAME LIKE :name", \
                               {'name': self._name}
                    if self._label is not None:
                        sql += " AND CP_LABEL LIKE :label"
                        sqa['label'] = self._label
                    if self._desc is not None:
                        sql += " AND COLLCOMMENT LIKE :descr"
                        sqa['descr'] = self._desc
                    cids = [i[0] for i in self._db.execute(sql, **sqa)]
                else:
                    cids = [self._name]
                if self._type == CollManager.SHARE:
                    res = self._db.execute("SELECT SAHREDMAPID, p.NAME FROM CAT_SHAREDCOLLECTIONMAP "
                                           "INNER JOIN GBL_PRIORITIES p USING(PRID) WHERE PARENT_COLLID = :par "
                                           "AND CHILD_COLLID = :cld", par=self._parent, cld=cids[0])
                    if len(res) > 0:
                        self._myId, self._prio = res
                    else:
                        self._myId = self._db.execute("INSERT INTO CAT_SHAREDCOLLECTIONMAP (PARENT_COLLID, "
                                                      "CHILD_COLLID, PRID) VALUES (:par, :cld, "
                                                      "(SELECT PRID FROM GBL_PRIORITIES WHERE NAME = :prio)) "
                                                      "RETURNING SAHREDMAPID",
                                                      par=self._parent, cld=cids[0], prio=self._prio)
                elif len(cids) == 1:  # update parent then
                    self._myId = cids[0]
                    self._db.execute("UPDATE CAT_COLLECTIONS SET PARENTID = :par WHERE COLLID = :coll",
                                     par=self._parent, coll=self._myId)
                else:  # insert new one
                    sql = ("INSERT INTO CAT_COLLECTIONS (PARENTID, PRID, NAME, CP_LABEL, USERID$M) VALUES (:par, "
                           "(SELECT PRID FROM GBL_PRIORITIES WHERE NAME = :prio), :name, :label, $UID$V) "
                           "RETURNING COLLID")
                    sqa = {'par': self._parent, 'name': self._name, 'label': self._sqnullconv(self._label),
                           'prio': self._prio}
                    if self._desc is None:
                        sql = sql.replace("$M", "").replace("$V", "")
                    else:
                        sql = sql.replace("$M", ", COLLCOMMENT").replace("$V", ", :comm")
                        sqa['comm'] = self._desc
                    self._myId = self._db.execute(sql, **sqa)
            else:  # add a recording
                self._get_rec_details(self._name)

                self._relts = [(None if i == 'None' else i) for i in [kw.pop('beginrelts', None),
                                                                      kw.pop('endrelts', None)]]
                if self._relts[0] is not None:
                    try:
                        self._relts[0] = int(self._relts[0][:-1]) \
                            if type(self._relts[0]) in StringTypes and self._relts[0].endswith('R') \
                            else int(self._relts[0]) - self._timestamp[0]
                        self._relts[1] = int(self._relts[1][:-1]) \
                            if type(self._relts[1]) in StringTypes and self._relts[1].endswith('R') \
                            else int(self._relts[1]) - self._timestamp[0]
                    except Exception as ex:
                        pass

                sql = "SELECT COUNT(COLLMAPID) FROM CAT_COLLECTIONMAP WHERE COLLID = :cid " \
                      "AND MEASID = :mid AND BEGINRELTS $B AND ENDRELTS $E"
                sqa = {"cid": self._parent, "mid": self._myId}
                if self._relts[0] is None:
                    sql = sql.replace("$B", "IS NULL")
                else:
                    sql = sql.replace("$B", "= :beg")
                    sqa["beg"] = self._relts[0]
                if self._relts[1] is None:
                    sql = sql.replace("$E", "IS NULL")
                else:
                    sql = sql.replace("$E", "= :end")
                    sqa["end"] = self._relts[1]

                if self._db.execute(sql, **sqa)[0][0] == 0:
                    self._db.execute("INSERT INTO CAT_COLLECTIONMAP (COLLID, MEASID, USERID, BEGINRELTS, ENDRELTS$A) "
                                     "VALUES (:cid, :mid, $UID, :beg, :end$B)"
                                     .replace("$A", ", ASGNBY, ASGNDATE" if self._asign else "")
                                     .replace("$B", ", 'foo', $CD" if self._asign else ""),
                                     cid=self._parent, mid=self._myId, beg=self._relts[0], end=self._relts[1])

        else:  # retrieve the details of me
            if self._type in (CollManager.COLL, CollManager.SHARE):  # details from collection
                self._myId = kw['name']
                self._name, self._label, self._desc, self._prio, self._active = \
                    self._db.execute("SELECT c.NAME, c.CP_LABEL, c.COLLCOMMENT, p.NAME, c.IS_ACTIVE "
                                     "FROM CAT_COLLECTIONS c LEFT JOIN GBL_PRIORITIES p USING(PRID) "
                                     "WHERE COLLID = :coll", coll=self._myId)[0]

            else:  # details from recording
                self._relts = [None, None]
                if type(kw['name']) == tuple:
                    self._myId, self._mapid, self._relts[0], self._relts[1] = kw['name']
                else:
                    self._myId = kw['name']

                self._get_rec_details(self._myId)

        self._get_childs()

    def add(self, item):
        """add a collection or recording

        :param item: recording or collection
        :type item: Recording | Collection
        """
        if isinstance(item, Recording):
            i = Recording(self._db, type=CollManager.REC, parent=self._myId, mode=CollManager.WRITE, name=item.id,
                          beginrelts=item.beginrelts, endrelts=item.endrelts, asgnby=self._asign)
            self._childs.append([i.id, CollManager.REC])

        elif isinstance(item, Collection):
            i = Collection(self._db, type=CollManager.COLL, parent=self._myId, mode=CollManager.WRITE,
                           name=item.name, desc=item.desc, asgnby=self._asign)
            self._childs.append([i.id, CollManager.COLL])

        else:
            raise ValueError("not allowed to add " + str(item))

        return i

    def __del__(self):
        """disconnect"""
        if self._parent is None:
            self.close()

    def __str__(self):
        """return string text summary of me"""
        if self._type == CollManager.NONE:
            return "<collection summary from %s>" % (str(self._db))
        elif self._type == CollManager.COLL:
            return "<collection %d: '%s' (%s)>" % (self._myId, self._name, "" if self._desc is None else self._desc)
        elif self._type == CollManager.SHARE:
            return "<shared collection %d: '%s' (%s)>" % (self._myId, self._name,
                                                          "" if self._desc is None else self._desc)
        else:
            return "<recording %d: '%s' (%d-%d)>" % (self._myId, self._name, self._timestamp[0], self._timestamp[1])

    def __iter__(self):
        """start iterating through test cases"""
        self._iteridx = 0
        return self

    def next(self):
        """next child item to catch and return"""
        if self._iteridx >= self._get_childs():
            raise StopIteration
        else:
            self._iteridx += 1
            return self[self._iteridx - 1]

    def __getitem__(self, idx):
        """provide a slice index to be able to iterate through the childs"""
        nchilds = self._get_childs()
        if type(idx) == int and 0 <= idx < nchilds:
            return CollManager.CLSUB[self._childs[idx][1]](self._db, parent=self._myId, name=self._childs[idx][0],
                                                           type=self._childs[idx][1], asgnby=self._asign)
        # untested:
        # elif type(idx) == slice and min(0, idx.start, idx.stop) == 0 and max(nchilds, idx.start, idx.stop):
        #     return [CollManager.CLSUB[self._childs[idx][1]](self._db, parent=self._myId, name=self._childs[idx][0],
        #                                                     type=self._childs[idx][1])
        #             for i in xrange(idx.start, idx.stop, idx.step)]
        else:
            raise IndexError

    def __len__(self):
        """provide length of sub items / childs"""
        return self._get_childs()

    def __enter__(self):
        """being able to use with statement
        """
        return self

    def __exit__(self, *args):
        """close connection"""
        self.close(True, args[0] is not None)

    def close(self, commit=True, rollback=False):
        """commit changes and close connection

        :param commit: we should commit
        :param rollback: we need to rollback
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
        if type(name) in StringTypes:
            srv = splitunc(name)
            if srv[0] != '':
                part = srv[0].split('\\')
                name = ('\\\\%s.cw01.contiwan.com\\%s%s' % (part[-2].split('.')[0], part[-1], srv[1])).lower()
                sql = 'FILEPATH LIKE :meas'
            else:
                sql = 'LOWER(RECFILEID) = :meas'
        else:
            sql = 'MEASID = :meas'

        self._timestamp, self._import = [None, None], None
        self._fstate = None
        try:
            self._myId, self._name, self._chash, self._timestamp[0], self._timestamp[1], self._dist, self._gpsdist, \
                self._fsize, self._state, self._rectime, self._import, self._recprj, \
                self._fstate, self._locname, self._region = \
                self._db.execute("SELECT distinct MEASID, FILEPATH, CONTENTHASH, BEGINABSTS, ENDABSTS, RECDRIVENDIST, "
                                 "GPSDRIVENDIST, FILESIZE, NVL(s.NAME, ''), RECTIME, IMPORTDATE, p.NAME, "
                                 "STATUS, l.NAME, REGION "
                                 "FROM CAT_FILES LEFT JOIN GBL_PROJECT p USING(PID) "
                                 "LEFT JOIN CAT_FILESTATES s USING(FILESTATEID) "
                                 "INNER JOIN GBL_LOCATION l USING(LOCATION) "
                                 "WHERE " + sql, meas=name)[0]
        except Exception as _:
            raise CollException(ERR_NO_REC, "recording '%s' does not exist!" % name)

        if type(self._import) in StringTypes:  # for sqlite
            idx = self._import.find(' ')
            idx = idx if idx > 0 else len(self._import)
            self._import = self._import[:idx]
        else:
            self._import = self._import.strftime('%Y-%m-%d')

    def _get_childs(self):
        """retrieve sub items / childs of us"""
        if self._myId is None:  # as I said: we're all
            self._childs = [[i[0], CollManager.COLL]
                            for i in self._db.execute("SELECT COLLID FROM CAT_COLLECTIONS WHERE PARENTID IS NULL "
                                                      "ORDER BY COLLID")]
        elif len(self._childs) == 0:  # otherwise we're a definite collection
            if self._type in (CollManager.COLL, CollManager.SHARE):
                # check if we have child runs
                self._childs = self._db.execute("SELECT COLLID, %d FROM CAT_COLLECTIONS WHERE PARENTID = :par "
                                                "UNION "
                                                "SELECT CHILD_COLLID, %d FROM CAT_SHAREDCOLLECTIONMAP "
                                                "WHERE PARENT_COLLID = :par"
                                                % (CollManager.COLL, CollManager.SHARE), par=self._myId)
                self._childs.extend([[i, CollManager.REC]
                                     for i in self._db.execute("SELECT MEASID, COLLMAPID, BEGINRELTS, ENDRELTS "
                                                               "FROM CAT_COLLECTIONMAP "
                                                               "INNER JOIN CAT_COLLECTIONS USING(COLLID) "
                                                               "INNER JOIN CAT_FILES USING(MEASID) "
                                                               "WHERE COLLID = :coll ORDER BY FILEPATH, BEGINRELTS",
                                                               coll=self._myId)])
        return len(self._childs)

    def __getattr__(self, name):
        """used for code reduction of property handling, see above attribute GETATTR for valid attributnames (keys)
        additional attributes are inherited from CollManager: id, type, name
        """
        try:
            bak = self.__class__.GETATTR[name]
            return getattr(self, bak[0]) if len(bak) == 1 else getattr(self, bak[0])[bak[1]]
        except:
            raise AttributeError

    def _sqnullconv(self, item):
        """convert null values to empty strings on sqlite
        """
        return ('' if item is None else item) if self._db.db_type[0] == 0 else item

    @classmethod
    def regsub(cls, theid):
        """used for subclass registration as we need to return proper child classes for iteration
        """
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
        """returns db connection"""
        return self._db

    def sql(self, sql, **parms):
        """executes with background db"""
        return self._db.execute(sql, **parms)

    @property
    def type(self):
        """returns my type: REC or COLL"""
        return self._type

    @property
    def name(self):
        """returns my name"""
        return self._name

    @name.setter
    def name(self, value):
        """set new name for collection"""
        if self._type == CollManager.COLL:
            self._db.execute("UPDATE CAT_COLLECTIONS SET NAME = :name WHERE COLLID = :coll",
                             name=value, coll=self._myId)
        else:
            raise AttributeError("cannot change name of me!")


@CollManager.regsub(CollManager.COLL)
class Collection(CollManager):
    """ A collection can contain other collections and for sure recordings.

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
    GETATTR = {"id": ("_myId",), "desc": ("_desc",), "prio": ("_prio",), "active": ("_active",), "parent": ("_parent",)}
    SETATTR = {"desc": ("_desc",)}

    if False:  # helping intellisense
        id = desc = prio = active = parent = desc = None

    def __init__(self, *args, **kw):
        """ Collections have a name and optional description, that's it!

        :keyword name: name of collection to use (or create if not existing)
        :keyword desc: description of collection
        """
        CollManager.__init__(self, *args, **kw)

    def add_coll(self, **kw):
        """add a collection

        :keyword name: name of collection
        :keyword desc: description of it"""
        if 'type' not in kw or kw['type'] not in (CollManager.COLL, CollManager.SHARE):
            kw['type'] = CollManager.COLL
        kw['asgnby'] = kw.pop('asgnby', self._asign)
        c = Collection(self._db, parent=self._myId, mode=CollManager.WRITE, **kw)
        if [c.id, kw['type']] not in self._childs:  # we could have it already because we updated
            self._childs.append([c.id, kw['type']])
        return c

    def add_rec(self, **kw):
        """add a recording

        :keyword name: recfile path or it's id
        """
        kw['type'] = CollManager.REC
        kw['asgnby'] = kw.pop('asgnby', self._asign)
        r = Recording(self._db, parent=self._myId, mode=CollManager.WRITE, **kw)
        self._childs.append([r.id, CollManager.REC])
        return r

    def remove(self, sub, start=True):
        """remove something

        :param sub: a subitem to be removed, similar to list.remove
        :type sub: Recording | Collection
        :param start: DO NOT USE, only internally used.
        """
        if sub.type == CollManager.REC:
            # print("rec removal %d (%d): %s" % (sub.id, sub.map_id, sub.name))
            self._db.execute("DELETE FROM CAT_COLLECTIONMAP WHERE COLLMAPID = :map", map=sub.map_id)
        else:
            for i in sub:
                sub.remove(i, False)

            # print("coll removal: %d: %s" % (sub.id, sub.name))
            self._db.execute("DELETE FROM CAT_COLLECTIONS WHERE COLLID = :coll", coll=sub.id)

        if start:
            if sub.type == CollManager.COLL:
                self._childs.remove(next(k for k in [i for i in self._childs if i[1] == sub.type]
                                         if k[0] == sub.id))
            else:
                self._childs.remove(next(k for k in [i for i in self._childs if i[1] == sub.type]
                                         if k[0][1] == sub.map_id))

    def export_bpl(self, filename):
        """export recordings to a bpl file

        :param filename: path to file.bpl
        :type filename: str | file
        """
        recs = {}
        # grab all details from recordings first, to do the section list properly
        for rec in self:
            if rec not in recs:
                recs[rec.name] = []
            if rec.beginrelts and rec.endrelts:  # we just ignore duplicates, e.g. rec without relts and same with
                recs[rec.name] += [[rec.beginrelts, rec.endrelts]]

        # build xml
        top = Element('BatchList')
        for rec, times in recs.iteritems():
            entry = SubElement(top, "BatchEntry", {'fileName': rec})
            secent = SubElement(entry, "SectionList")

            for time in times:
                SubElement(secent, "Section", {'startTime': "%dR" % time[0], 'endTime': "%dR" % time[1]})

        # file data:
        fdata = parseString(tostring(top, 'utf-8')).toprettyxml(indent='    ', encoding='UTF-8')

        if hasattr(filename, 'read'):
            filename.write(fdata)
        else:
            with open(filename, "wb") as fpo:
                fpo.write(fdata)

    def import_bpl(self, filename):
        """import recordings from a bpl file

        :param filename: path to file.bpl
        :type filename: str | file
        """
        try:
            root = parse(filename).getroot()
        except:
            root = []

        if root == [] or root.tag != "BatchList":
            raise CollException("'%s' doesn't seem like a valid bpl" % filename)

        recnt = 0
        for rec in root:
            fname, times = rec.get("fileName", ""), [(None, None,)]
            childs = rec.getchildren()[0]
            if len(childs) and childs.tag == "SectionList":
                times = [(ch.get('startTime'), ch.get('endTime')) for ch in childs if ch.tag == "Section"]
            try:
                for ch in times:
                    self.add_rec(name=fname, beginrelts=ch[0], endrelts=ch[1])
                    recnt += 1
            except CollException as cex:
                if cex.error != ERR_NO_REC:
                    raise
        self._db.commit()
        return len(root)


@CollManager.regsub(CollManager.SHARE)
class SharedColl(CollManager):
    """ a shared collection is a special kind of collection which can be used in several parent collections

        removing a shared collection means deleting the link to it,
        the sub collection itself is only removed if the last link is deleted

        a shared collection can contain other (shared) collections and for sure recordings

        otherwise a shared collection is similar to the `Collection`
    """
    GETATTR = {"id": ("_myId",), "desc": ("_desc",), "prio": ("_prio",), "active": ("_active",), "parent": ("_parent",)}
    SETATTR = {"desc": ("_desc",)}

    if False:  # helping intellisense
        id = desc = prio = active = parent = description = None

    def __init__(self, *args, **kw):
        """a shared collection has a name and optional description, that's it!

        :keyword name: name of collection to use (or create if not existing)
        :keyword desc: description of collection
        """
        CollManager.__init__(self, *args, **kw)

    # 2B taken over from Collection:
    # __contains__ = Collection.__dict__['__contains__']


@CollManager.regsub(CollManager.REC)
class Recording(CollManager):
    """A recording represents the data from cat_files (measid).

        Several other infos are available through properties, e.g.:

            - name:  complete path and file name
            - id:  measurement id
            - timestamp:  tuple of [abs. start ts, abs. end ts] time stamps ([int, int])
            - state:  status of file on server (transmitted: copied to server, archived: moved to archive=not available)
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
    GETATTR = {"id": ("_myId",), "timestamp": ("_timestamp",), "state": ("_state",), "hash": ("_chash",),
               "rectime": ("_rectime",), "import_date": ("_import",), "project": ("_recprj",),
               "beginrelts": ("_relts", 0), "endrelts": ("_relts", 1), "distance": ("_dist",),
               "gpsdistance": ("_gpsdist",), "filesize": ("_fsize",), "map_id": ("_mapid",),
               "filestate": ("_fstate",), "location": ("_locname",), "region": ("_region",)}

    SETATTR = {"beginrelts": ("_relts", 0), "endrelts": ("_relts", 1)}

    if False:  # helping intellisense
        id = timestamp = state = hash = rectime = import_date = project = \
            beginrelts = endrelts = distance = \
            gpsdistance = filesize = map_id = \
            filestate = location = region = None

    def __init__(self, *args, **kw):
        """A recording has a name being /server/path/to/a/filename.

        :keyword name: path of recording file or it's measid
        """
        kw['type'] = kw.pop('type', CollManager.REC)
        CollManager.__init__(self, *args, **kw)
        self.addColl = None

    def __getitem__(self, item):
        """"""
        # catch all available types (using global var?)
        # catch name / value and save into generated class -> type('MET', .., ..) and return it

    def __setitem__(self, key, value):
        """change some details like beginrelts or endrelts"""
        bak = self.__class__.SETATTR[key]
        if key not in self.__class__.SETATTR:
            raise ValueError

        if key.endswith('relts'):
            if value == "":
                value = None
            elif int(value) < self._timestamp[1] - self._timestamp[0]:
                value = long(value)
            else:
                raise ValueError

            getattr(self, bak[0])[bak[1]] = value  # self._relts[bak[1]] = value
            if all(self._relts) and self._relts[0] < self._relts[1]:
                self._db.execute("UPDATE CAT_COLLECTIONMAP SET BEGINRELTS = :beg, ENDRELTS = :end "
                                 "WHERE COLLMAPID = :map", beg=self._relts[0], end=self._relts[1], map=self._mapid)
        else:
            raise ValueError

    def _calc_dist(self, which, start, stop):
        """retrieves and calcs the distance

        :param which: currently supports 'vdy' and 'gps'
        :param start: start time
        :param stop: stop time
        """
        assert which.upper() in ('VDY', 'GPS'), "'VDY' or 'GPS' is supported!"
        # build sql query
        sql = "SELECT %s FROM %s" % ("MTSTS, VELOCITY" if which == 'VDY' else "LATITUDE, LONGITUDE", which)
        fltr, fidx, sqa = ["WHERE", "AND"], 0, {}
        if start is not None:
            sql += " %s MTSTS >= :start" % fltr[fidx]
            sqa['start'] = start
            fidx += 1
        if stop is not None:
            sql += " %s MTSTS <= :stop" % fltr[fidx]
            sqa['stop'] = stop

        # connect and load data from sqlite file
        with BaseDB(join(r'\\lifs010\meta', self._recprj, '_DISTANCE', self._chash + ".sqlite")) as ddb:
            data = ddb.sql(sql, sqa)
            if len(data) == 0:
                return None

        if which == 'VDY':  # calculate VDY distance
            mts, vdy = zip(*data)
            dist = 0.
            for t, v in zip(zip(mts[:-1], mts[1:]), zip(vdy[:-1], vdy[1:])):
                dt, dv = (t[1] - t[0]) * 0.000001, v[1] - v[0]
                # dist += v[0] * dt + 0.5 * (dv / dt) * dt**2
                dist += dt * (v[0] + 0.5 * dv)
            dist /= 1000.  # [km]
        else:  # calculate GPS distance
            def haversine(start, end):
                """calculates the haversine distance"""
                lat1, lon1 = start
                lat2, lon2 = end

                d_lat = radians(lat2 - lat1)
                d_lon = radians(lon2 - lon1)
                lat1 = radians(lat1)
                lat2 = radians(lat2)

                a = sin(d_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(d_lon / 2) ** 2
                c = 2 * asin(sqrt(a))

                return 6372.8 * c  # Earth radius in kilometers

            dist = sum([haversine(data[i - 1], data[i]) for i in xrange(1, len(data))])

        return dist

    def vdy_dist(self, start=None, stop=None):
        """calculates VDY distance between start and stop times, default: calc for the whole recording

        :param start: use specific start time
        :param stop: use specific stop time
        """
        return self._calc_dist('VDY', start, stop)

    def gps_dist(self, start=None, stop=None):
        """calculates GPS distance between start and stop times, default: calc for the whole recording

        :param start: use specific start time
        :param stop: use specific stop time
        """
        return self._calc_dist('GPS', start, stop)


"""
CHANGE LOG:
-----------
$Log: catalog.py  $
Revision 1.22 2017/11/18 23:46:37CET Hospes, Gerd-Joachim (uidv8815) 
fix docu 2
Revision 1.20 2017/11/17 17:54:28CET Hospes, Gerd-Joachim (uidv8815)
using db cat vers 13, adding location and region, del usage of archived and deleted
Revision 1.19 2017/07/14 13:51:08CEST Mertens, Sven (uidv7805)
remove importby
Revision 1.18 2016/08/08 10:32:21CEST Hospes, Gerd-Joachim (uidv8815)
fix epydoc errors
Revision 1.17 2016/08/04 19:16:10CEST Hospes, Gerd-Joachim (uidv8815)
fix to get labelled colls added
Revision 1.16 2016/08/01 14:51:55CEST Mertens, Sven (uidv7805)
in case name is integer, we already have it
Revision 1.15 2016/07/19 09:39:58CEST Mertens, Sven (uidv7805)
fix for cp_label
Revision 1.14 2016/07/11 16:44:24CEST Mertens, Sven (uidv7805)
commit at end of import at least
Revision 1.13 2016/07/11 11:36:39CEST Mertens, Sven (uidv7805)
we already have current userid, so we should use it
Revision 1.12 2016/07/11 10:31:41CEST Mertens, Sven (uidv7805)
adding helper for intellisense
Revision 1.11 2016/07/11 10:16:01CEST Mertens, Sven (uidv7805)
fix for interfernce of $C <-> $CU
Revision 1.10 2016/07/11 09:45:12CEST Mertens, Sven (uidv7805)
we need to care about asngby backward compatibility as it's defined with 'not null'
Revision 1.9 2016/07/11 09:13:24CEST Mertens, Sven (uidv7805)
support for cp_label added
Revision 1.8 2016/07/08 10:16:26CEST Mertens, Sven (uidv7805)
integrate priority, parent attribute and shared collection support
Revision 1.7 2016/06/17 15:48:12CEST Mertens, Sven (uidv7805)
reducing pylints
Revision 1.6 2016/06/17 12:07:01CEST Mertens, Sven (uidv7805)
comment fix
Revision 1.5 2016/04/27 16:20:03CEST Mertens, Sven (uidv7805)
import / export bpl
Revision 1.4 2016/04/12 17:01:25CEST Mertens, Sven (uidv7805)
name does not exists
Revision 1.3 2016/04/05 15:47:15CEST Mertens, Sven (uidv7805)
null uses is, not equals
Revision 1.2 2016/03/29 17:36:40CEST Mertens, Sven (uidv7805)
support for shared collections and distance calculation
Revision 1.1 2015/10/13 12:03:36CEST Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/
    04_Engineering/01_Source_Code/stk/db/project.pj
"""
