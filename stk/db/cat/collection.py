"""
collection.py
-------------

starting with some helpers to be able to copy collections from one DB to another...

:org:           Continental AG
:author:        uidv7805

:version:       $Revision: 1.7 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2017/07/14 13:51:26CEST $
"""
# pylint: disable=W0104,W0142
__all__ = ["copy_collection_data"]

# - Python imports ----------------------------------------------------------------------------------------------------
from re import search

# - STK imports -------------------------------------------------------------------------------------------------------
from stk.db.catalog import CollManager, Collection
from stk.db.db_common import BaseDB
from stk.db.table import TableDict, UserTableDict, NoneDict
from stk.util.logger import DummyLogger, Logger


# - classes / functions -----------------------------------------------------------------------------------------------
def _copy_collection(src, dst, par, colls, recs=None, start=False):
    """copy all collections

    :param src: source (-> Collection)
    :param dst: destination (-> DBase)
    :param par: parent collection, starting by None, used for recursion
    :param colls: collection dict
    :param recs: link to CAT_FILES
    :param start: start of recursion
    """
    if start:
        if par is None:
            par = Collection(dst, name=src.name, prio=src.prio)
        else:
            pname = src.sql("SELECT NAME, CP_LABEL FROM CAT_COLLECTIONS WHERE COLLID = :pid", pid=par)[0]
            while par is not None:
                colls[par]
                par = src.sql("SELECT PARENTID FROM CAT_COLLECTIONS WHERE COLLID = :cid", cid=par)[0][0]

            par = Collection(dst, name=pname[0], label=pname[1]).add_coll(name=src.name, desc=src.desc, prio=src.prio)
    else:
        par = par.add_coll(name=src.name, desc=src.desc, type=src.type, prio=src.prio)

    # iterate throught source collection
    for i in src:
        # if item is a (shared /) collection
        if i.type == CollManager.COLL:
            # copy inside as well
            _copy_collection(i, dst, par, colls, recs)
        elif i.type == CollManager.SHARE:
            coll = Collection(src.dbase, name=i.name)
            _copy_collection(coll, dst, coll.parent, colls, recs, start=True)
            par.add_coll(type=CollManager.SHARE, name=i.name)
        else:
            # copy recording itself to sqlite file
            par.add_rec(name=recs[i.id], beginrelts=i.beginrelts, endrelts=i.endrelts)


def _create_label_table(src, dst, table):
    """create label table at destination

    :param src: source DB connection
    :param dst: destination DB connection (sqlite)
    :param table: name of table to create
    """
    cols = src.execute("SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH FROM ALL_TAB_COLUMNS "
                       "WHERE OWNER = 'ADMSADMIN' AND TABLE_NAME = :tbl ORDER BY COLUMN_ID", tbl=table)
    sql = ("CREATE TABLE IF NOT EXISTS %s (" % table) + ", ".join([("%s %s(%d)" % i) for i in cols]) + ")"

    dst.execute(sql, commit=True)

    return [i[0] for i in cols]

# _create_label_table(BaseDB(r"D:\SandBoxes\STK\04_Engineering\01_Source_Code\stk\db\sqlite_db\adas_db_2_2.sqlite"), "MFC400_SOD_LDROI")


def copy_collection_data(**kwargs):
    """start copying from base collection by initializing DB access

    :keyword source: source database
    :keyword destination: destination database
    :keyword name: name of collection to copy recursivly
    :keyword purge: purge destination colleciton tables before starting to copy, default: False
    :keyword rectobj: also copy related rectangual objects, default: False
    :keyword scenarios: also copy related FCT scenarios, default: False
    :keyword labels: also copy related label information, default: False
    """
    logger = DummyLogger(True) if kwargs.pop("use_print", False) else Logger("collection copy:")
    try:
        with BaseDB(kwargs["destination"], autocommit=False, journal=False) as ddb, \
                BaseDB(kwargs["source"], autocommit=True) as sdb:
            if kwargs.get("purge"):
                ddb.execute("DELETE FROM CAT_COLLECTIONMAP")
                ddb.execute("DELETE FROM CAT_SHAREDCOLLECTIONMAP")
                ddb.execute("DELETE FROM CAT_COLLECTIONS")
                ddb.commit()

            prios = TableDict(sdb, ddb, "GBL_PRIORITIES", pkey="PRID")
            users = UserTableDict(sdb, ddb, "GBL_USERS", pkey="USERID")
            colls = TableDict(sdb, ddb, "CAT_COLLECTIONS", pkey="COLLID", PRID=prios, USERID=users, CP_LABEL=NoneDict(),
                              recurse="PARENTID", dontcare=["CREATED"])
            recs = TableDict(sdb, ddb, "CAT_FILES", pkey="MEASID", dontcare=["DRIVERID", "IMPORTBY"])

            with Collection(sdb, name=kwargs["name"]) as cmgr:
                if ddb.db_type == -1:
                    print("copy to oracle not permitted by now!")
                    return -1

                _copy_collection(cmgr, ddb, cmgr.parent, colls, recs=recs, start=True)
                recs.fix()
                ddb.commit()
                logger.info("copied %d collections and recordings" % len(recs))

                def copy_simple(sdct, ddct, sql):
                    """copy simple"""
                    for i in sdct.keys():
                        cnt = 0
                        for k in sdb.executex(sql, **{search(r":(\w+)\b", sql).group(1): i}):
                            ddct[k[0]]
                            cnt += 1
                        if cnt > 0:
                            ddb.commit()

                if kwargs.get("scenarios", False) or kwargs.get("genlabels", False):
                    wflow = TableDict(sdb, ddb, "GBL_WORKFLOW", pkey="WFID")
                if kwargs.get("rectobj", False) or kwargs.get("scenarios", False):
                    assoc = TableDict(sdb, ddb, "OBJ_ASSOCIATIONTYPES")
                    clstp = TableDict(sdb, ddb, "OBJ_CLASSTYPES")
                    label = TableDict(sdb, ddb, "OBJ_LBLSTATE")
                    rectobj = {"MEASID": recs, "ASSOCTYPEID": assoc, "CLSID": clstp, "CLSLBLSTATEID": label,
                               "DIMLBLSTATEID": label, "KINLBLSTATEID": label, "ZOLBLSTATEID": label, "ZOLBLBY": users,
                               "DIMLBLBY": users, "CLSLBLBY": users, "KINLBLBY": users}
                    objs = TableDict(sdb, ddb, "OBJ_RECTANGULAROBJECT", **rectobj)
                    copy_simple(recs, objs, "SELECT RECTOBJID FROM OBJ_RECTANGULAROBJECT WHERE MEASID = :meas")
                    logger.info("copied %d rectangular objects" % len(objs))

                if kwargs.get("scenarios", False):
                    project = TableDict(sdb, ddb, "GBL_PROJECT", pkey="PID", dontcare=["SOFTQUOTA", "HARDQUOTA"])
                    fenv = TableDict(sdb, ddb, "FCT_ENVIRONMENT")
                    fcrit = TableDict(sdb, ddb, "FCT_CRITICALITY")

                    fscens = {"MEASID": recs, "ENV_INFRASTRUCTURE": fenv, "ENV_LIGHT_CONDITION": fenv,
                              "ENV_WEATHER_CONDITION": fenv, "ENV_DATAINTEGRITY": fenv, "LABELER_CRITICALITY": fcrit,
                              "VEHICLE_CRITICALITY": fcrit, "DRIVER_CRITICALITY": fcrit, "LBLSTATEID": wflow,
                              "PID": project, "RECTOBJID": objs, "EGO_BEHAVIOR": fenv, "REL_EGO_BEHAVIOR": fenv,
                              "OBJ_DYNAMIC": fenv, "OBJ_TYPE": fenv, "OBJ_BEHAVIOR": fenv, "LBLBY": users,
                              "EVASION_RIGHT": fenv, "EVASION_LEFT": fenv}
                    scens = TableDict(sdb, ddb, "FCT_SCENARIO", **fscens)
                    copy_simple(recs, scens, "SELECT SCENARIOID FROM FCT_SCENARIO WHERE MEASID = :meas")
                    logger.info("copied %d scenario objects" % len(scens))

                if kwargs.get("genlabels", False):
                    # attention: we're not taking care of lb_types.parent, as even inside ARS4xx DB, relation
                    # is invalid as of writing right now: 14.06.2016 (SMe)
                    ltypes = TableDict(sdb, ddb, "LB_TYPES", dontcare=["PARENT"])
                    lstates = TableDict(sdb, ddb, "LB_STATES", TYPEID=ltypes)
                    lbids = TableDict(sdb, ddb, "LB_LABELS", MEASID=recs, USERID=users, WFID=wflow, STATEID=lstates,
                                      TYPEID=ltypes)
                    copy_simple(recs, lbids, "SELECT LBID FROM LB_LABELS WHERE MEASID = :meas")

                    # now we need addtionalinfo as well, due to too bad designed table space :-(
                    for i, k in lbids.iteritems():
                        for desc in sdb.executex("SELECT DESCRIPTION FROM LB_ADDITIONALINFO WHERE LBID = :lid", lid=i):
                            if len(desc) > 0:
                                ddb.execute("INSERT INTO LB_ADDITIONALINFO (LBID, DESCRIPTION) VALUES (:lid, :dscr)",
                                            lid=k, dscr=desc[0][0])
                    # and on top we need the attributes...
                    valtypes = TableDict(sdb, ddb, "GBL_VALTYPES", pkey="VTID")
                    units = TableDict(sdb, ddb, "GBL_UNITS", pkey="UNITID")
                    attrname = TableDict(sdb, ddb, "LB_ATTRIBUTENAMES")
                    attribs = TableDict(sdb, ddb, "LB_ATTRIBUTES", LBID=lbids, VTID=valtypes, LBATTNAMEID=attrname,
                                        UNITID=units)
                    copy_simple(lbids, attribs, "SELECT LBATTRID FROM LB_ATTRIBUTES WHERE LBID = :lid")
                    logger.info("copied %d label objects" % len(lbids))

                if kwargs.get("rectobj", False) and kwargs.get("genlabels", False):
                    rectlb = TableDict(sdb, ddb, "LB_RECTOBJIDMAP", RECTOBJID=objs, LBID=lbids)
                    cnt = rectlb.copy()
                    ddb.commit()
                    logger.info("copied %d rectangular object / label mappings" % cnt)

                if kwargs.get("camlabels", None):
                    algo = BaseDB('algo')
                    for i in ("CD", "LDROI", "LDSS"):
                        table = "%s_%s_%s" % (kwargs["camlabels"][0], kwargs["camlabels"][1], i)
                        cols = _create_label_table(algo, ddb, table)
                        # lbls = TableDict(algo, ddb, table)
                        # lbls.copy(casesens=True)
                        for v in recs.keys():
                            ins = algo.execute('SELECT %s FROM %s WHERE LOWER("RecIdFileName") = :rfid'
                                               % (", ".join([('"%s"' % c) for c in cols]), table),
                                               rfid=recs.value(v, "RECFILEID").lower())
                            if len(ins) > 0:
                                ddb.execute("INSERT INTO %s (%s) VALUES(%s)"
                                            % (table, ", ".join(cols), ", ".join(["?" for _ in xrange(len(cols))])),
                                            insertmany=ins)

    except Exception as ex:
        logger.error(str(ex))
        return -2

    return 0


"""
CHANGE LOG:
-----------
$Log: collection.py  $
Revision 1.7 2017/07/14 13:51:26CEST Mertens, Sven (uidv7805) 
ignore importby and driverid
Revision 1.6 2016/07/13 13:22:57CEST Mertens, Sven (uidv7805) 
- include cp_label info,
- include cam-labels as well
Revision 1.5 2016/07/11 09:12:39CEST Mertens, Sven (uidv7805)
users are special
Revision 1.4 2016/07/08 10:17:20CEST Mertens, Sven (uidv7805)
fix for collection copy of a root
Revision 1.3 2016/06/20 12:09:54CEST Mertens, Sven (uidv7805)
there is more data inside LB space...
Revision 1.2 2016/06/17 12:20:19CEST Mertens, Sven (uidv7805)
adding copy collection data
Revision 1.1 2016/06/17 12:11:04CEST Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/db/cat/project.pj
"""
