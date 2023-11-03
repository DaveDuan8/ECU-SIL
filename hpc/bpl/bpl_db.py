"""
bpl_db.py
---------

class for collection (BatchPlayList) handling
"""
# - Python imports -----------------------------------------------------------------------------------------------------
from os import sep, environ
from os.path import join
from re import split

# - import HPC modules -------------------------------------------------------------------------------------------------
from .bpl_ex import BplException
from .bpl_cls import BplReaderIfc, BplListEntry, Section
from ..rdb.catalog import Collection, CollManager, CollException, ERR_NO_REC
from ..rdb.base import crc
from ..core.tds import replace_server_path, LOCATION, DEV_LOC, LND_LOC
from ..core.path import splitdrive


# - classes ------------------------------------------------------------------------------------------------------------
class BPLDb(BplReaderIfc):  # pylint: disable=R0902
    """
    Specialized BPL Class which handles only reading of a collection.
    This class is not a customer Interface, it should only be used internal of hpc.
    """

    def __init__(self, *args, **kwargs):
        """
        init collection, as it can and will be recursive, we call ourself again and again and again

        :param tuple args: args for the interface
        :param dict kwargs: kwargs, db, recur are taken out immediately, others are passed through
        """
        BplReaderIfc.__init__(self, *args, **kwargs)

        self._db = self._kwargs.get("db", "VGA_PWR")
        self.uname = ""

        self._recur = self._kwargs.pop("recur", True)
        self._meass = []

        # if self._mode == "w":  # a parent is mandatory!!!
        #     with Collection(self._db, mode=CollManager.READ, **self._xargs) as coll:
        #         coll.dbase.sql("DELETE FROM VAL_GLOBAL_ADMIN.CAT_COLLECTIONMAP WHERE COLLID = :cid", cid=coll.id)

        self._xargs = {"name": self.filepath}
        if self._mode in ["w", "a"]:
            self._xargs["parent"] = self._kwargs["parent"]
            self._kwargs.pop("parent")
        self._local = "PRIMARY_LOCATION" not in environ
        self._locs = split(r',|;', kwargs.get("loc", LOCATION))
        if DEV_LOC in self._locs:
            # Dev server is located in LND, to get the correct files we set this here
            self._locs.remove(DEV_LOC)
            self._locs.append(LND_LOC)
        # set mainfiles to use only original rec files and no copies from other sites at the current location
        # used for submit_ww created jobs on Jenkins submits
        self._mainfiles = "MASTERID" in environ
        if not self._local:
            self._ign = []
            locs = [environ["PRIMARY_LOCATION"], environ["SECONDARY_LOCATION"], environ["TERTIARY_LOCATION"]]
            for i in locs:
                if i in self._locs + ["none"]:
                    break
                self._ign.append(i)

        self._xargs.update(self._kwargs)
        self._written = 0

    def read(self):  # pylint: disable=R1260
        """
        Read the whole content of the Batch Play List into internal storage,
        and return all entries as a list.

        :return:        List of Recording Objects
        :rtype:         BplList
        :raises BplException: once a recording is not available for location
        """
        del self[:]

        def _flatten(rec):
            """recurse _flatten a rec"""
            yield rec
            for i in rec:
                yield i

        def _add2self(rec):
            """add rec to self"""
            ble = BplListEntry(rec.name)
            for beg, end in rec.relts:
                if beg is not None and end is not None:
                    ble.sectionlist.append(Section(beg, end, (True, True,)))
            self.append(ble)
            if len(ble) == 0:
                self._meass.append((rec.id, None, None,))
            else:
                for i in ble.sectionlist:  # pylint: disable=E1133
                    self._meass.append((rec.id, i.start_ts, i.end_ts,))

        try:
            with Collection(self._db, mode=CollManager.READ, **self._xargs) as coll:
                def _recur(icoll):  # pylint: disable=R0912
                    cnt = 0
                    for i in icoll:
                        if i.type == CollManager.COLL:
                            if self._recur:
                                cnt += _recur(i)
                        elif i.type == CollManager.SHARE:
                            if self._recur:
                                cnt += _recur(Collection(self._db, name=i.name, label=i.label))
                        elif self._mainfiles:
                            # use only original rec files and no copies from other sites
                            if i.location in self._locs:
                                _add2self(i)
                                cnt += 1
                        elif self._local:
                            for frf in _flatten(i):
                                if frf.location in self._locs:
                                    _add2self(frf)
                                    cnt += 1
                                    break
                            else:
                                if not self._kwargs.get("ignore_missing", False):
                                    raise CollException(ERR_NO_REC, "child of {} @ {} missing!"
                                                        .format(i.name, ", ".join(self._locs)))
                        else:
                            rec = None
                            for frf in _flatten(i):
                                if frf.location in self._ign:
                                    rec = None
                                    break
                                if frf.location in self._locs:
                                    rec = frf
                            if rec is not None:
                                _add2self(rec)
                                cnt += 1
                    return cnt

                _recur(coll)
        except CollException as ex:
            raise BplException(ex.message)

        self._read = True
        return self

    def write(self):  # pylint: disable=R0912,R1260
        """to write to a collection is not supported!"""
        if self._written:
            return self

        try:
            values = []

            with Collection(self._db, mode=CollManager.WRITE, **self._xargs) as coll:
                usr, self.uname = coll.user
                meass = {}
                for rec in self:  # read in details of each recording
                    if str(rec) in meass:
                        continue

                    parts = splitdrive(str(rec))
                    srv, base = replace_server_path(parts[0], True).lower(), parts[1].strip(sep).lower()
                    meas = coll.dbase("SELECT MEASID, BEGINABSTS, PARENT "  # pylint: disable=E1102
                                      "FROM VAL_GLOBAL_ADMIN.CAT_DMT_FILES "
                                      "INNER JOIN VAL_GLOBAL_ADMIN.GBL_LOCATION l USING(LOCATION) "
                                      "WHERE CRC_NAME = :crc AND l.SERVERSHARE = :loc AND BASEPATH = :bph",
                                      crc=crc(join(srv, base)), loc=srv, bph=base)
                    if meas:
                        meass[str(rec)] = [meas[0][2] if meas[0][2] else meas[0][0], meas[0][1]]

                for rec in self:
                    if len(rec.sectionlist) == 0:
                        if (meass[str(rec)][0], None, None,) not in self._meass:
                            values.append((coll.id, meass[str(rec)][0], None, None, usr,))
                    else:
                        for sec in rec.sectionlist:
                            beg = sec.start_ts if sec.rel[0] else (sec.start_ts - meass[str(rec)][1])
                            end = sec.end_ts if sec.rel[1] else (sec.end_ts - meass[str(rec)][1])
                            if (meass[str(rec)][0], beg, end,) not in self._meass:
                                values.append((coll.id, meass[str(rec)][0], beg, end, usr,))

                if values:
                    coll.dbase.sql("INSERT INTO VAL_GLOBAL_ADMIN.CAT_COLLECTIONMAP (COLLID, MEASID, BEGINRELTS, "
                                   "ENDRELTS, USERID) VALUES (:cid, :mid, :beg, :end, :usr)", insertmany=values)

            self._written = len(values)
            return self

        except CollException as ex:
            raise BplException(ex.message)
