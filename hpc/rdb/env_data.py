"""
env_data.py
-----------

management of environment data
"""
# pylint: disable=R1260,W0212,E1129
# - import Python modules ---------------------------------------------------------------------------------------------
from __future__ import print_function

from sys import platform, version
from os import environ, listdir, makedirs
from os.path import join, dirname, basename, exists
from glob import glob
from datetime import datetime
from time import sleep
from random import random
from re import search, sub
from csv import DictWriter
from zlib import decompress, error as zliberr
from xml.etree.ElementTree import parse
from socket import gethostname
# from json import dumps
# from requests import post
from numpy import cumsum
from six import iteritems, PY3

# - import HPC modules -------------------------------------------------------------------------------------------------
from ..version import VERSION
from ..core.tds import head_name, HPC_STORAGE_MAP, LOCATION, daemon_cmd, DEFAULT_HEAD_NODE, VALID_NAME
from ..core import UID_NAME
from ..core.md5 import create_from_string
from ..core.dicts import JobDict
from ..core.error import HpcError
from ..core.convert import human_size
from ..sched.sched_mshpc import HpcSched
from ..bpl import Bpl, BplListEntry, Section
from .base import BaseDB
from .catalog import CollManager, Collection


# - defines -----------------------------------------------------------------------------------------------------------
MSWIN = platform == "win32"
TASKSTATE = {'None': 0, 'Configuring': 1, 'Submitted': 2, 'Validating': 4, 'Queued': 8, 'Dispatching': 16,
             'Running': 32, 'Finishing': 64, 'Finished': 128, 'Failed': 256, 'Canceled': 512, 'Canceling': 1024,
             'All': 2047}
MAX_STDOUT = 65536 * 3
STDOUT_HINT = '<span style="background-color: DarkOrange">' + \
              "\n".join(["&boxDR;" + "&boxH;" * 120 + "&boxDL;"] + ["&boxV;" + " " * 120 + "&boxV;"] + \
                        ["&boxV;{:^120}&boxV;"] + ["&boxV;{:^120}&boxV;"] + \
                        ["&boxV;" + " " * 120 + "&boxV;"] + ["&boxUR;" + "&boxH;" * 120 + "&boxUL;"]) + \
              '</span>'
# STDOUT_HINT = r"exec 'python hpc\cmd\env_collector.py log -n {} -j {} -s {}' to see full log."


# - classes and functions ---------------------------------------------------------------------------------------------
def _connect(func):
    """open db connection and call function"""

    def _wrapconn(self, **kwargs):
        """iterate over connections"""
        err, ret, wty = None, None, EnvData.NO_DB
        noprn = kwargs.pop("noprn", False)
        for _ in range(3):
            try:
                if self._conn is None:
                    break
                with BaseDB(self._conn, maxtry=1) as dbase:
                    ret = func(self, dbase=dbase, **kwargs)
                wty = EnvData.DEFAULT_DB
                break
            except HpcError as _ex:
                # err = "ERR: {!s} => {!s}".format(func, ex)
                break
            except Exception as ex:
                err = "ERR: {!s} => {!s}".format(func, ex)
                sleep(1 + random())
        else:
            if noprn:
                err = None
            else:
                print(err)

        return wty, ret

    return _wrapconn


class EnvData(object):
    """supporting starter to save environment data into HPC schema"""

    DEFAULT_DB, NO_DB = list(range(2))

    def __init__(self, db='HPC'):
        """
        save some initial data from job into DB:
        add an hpc_job and hpc_task entry

        :param ``str`` db: database connection to be used, default: HPC schema of Oracle DB
        :param ``str`` fallback_db: sqlite filename to be used if connection fails
        """
        self._conn = db
        self._taskstart, self._taskstop = datetime.utcnow(), None

        self._envdata = []
        self._errs = []
        self._ecnt = {}

    def __enter__(self):
        """support"""
        return self

    def __exit__(self, *_):
        """support"""

    # @staticmethod
    # def _ipaddr(host):
    #     """find out IP address"""
    #     if MSWIN:
    #         out = Popen('ping -n 1 %s' % host, stdout=PIPE).communicate()[0]
    #         mtc = search(r'^\r\nPing(ing| wird ausgef.+hrt f.+r) %s \[(.+)\].*' % host.replace('.', '\\.'),
    #                      out.decode('latin1'))
    #         return None if mtc is None else mtc.group(2)
    #
    #     return None

    def append(self, subdata):
        """append subtask infos"""
        self._envdata.append(subdata)

    def errors(self, errors, cnt):
        """append errors from bsig checker"""
        self._errs, self._ecnt = errors, cnt

    def get_slave_ident(self, dbase=None):
        """
        retrieve ident of slave computer

        :param ``hpc.rdb.base.BaseDB`` dbase: database connection
        :return: get slave ident of mine
        :rtype: int
        """
        selfopen = False
        if dbase is None:
            dbase = BaseDB(self._conn)
            selfopen = True

        mach = gethostname().upper().split('.')[0]
        slaveid = dbase("SELECT SLAVEID FROM HPC_SLAVE WHERE NAME = :slave", slave=mach)
        if slaveid:
            slaveid = slaveid[0][0]
        else:  # pragma: no cover
            slaveid = dbase("INSERT INTO HPC_SLAVE (NODEID, NAME) VALUES((SELECT NODEID "
                            "FROM HPC_NODE WHERE NODENAME = :node), :name) RETURNING SLAVEID",
                            node=head_name("OTHER").split('.')[0].upper(), name=mach)
        if selfopen:
            dbase.close()

        return slaveid

    @staticmethod
    def _user_ident(dbase):
        """
        check / insert user from / into HPC_LOGITEM

        :param ``hpc.rdb.base.BaseDB`` dbase: DB connection
        :return: ident of user
        :rtype: int
        """
        usridx = dbase("SELECT IID FROM HPC_LOGITEM WHERE NAME = :usr ORDER BY IID", usr=UID_NAME)
        if usridx and usridx[0]:
            usridx = usridx[-1][0]
            dbase("UPDATE HPC_LOGITEM SET CNT = CNT + 1 WHERE IID = :usr", usr=usridx)
        else:  # pragma: no cover
            try:
                # vary rare adding of an user, import here to speed up general usage of this module
                from win32com.client import GetObject  # pylint: disable=import-outside-toplevel
                udesc = GetObject("WinNT://%s,user" % UID_NAME.replace('\\', '/')).FullName
            except Exception as _ex:
                udesc = None
            usridx = dbase('INSERT INTO HPC_LOGITEM (NAME, "DESCR", CNT) VALUES(:usr, :dsc, 1) RETURNING IID',
                           usr=UID_NAME, dsc=udesc, exc_retry=23)
        return usridx

    @staticmethod
    def _simple_ident(dbase, iname, cname, cval, table):
        """
        check / insert data into table returning ident by column value

        :param ``hpc.rdb.base.BaseDB`` dbase: DB connection
        :param ``str`` iname: name of ident
        :param ``str`` cname: name of column of name
        :param ``str`` cval: value of column
        :param ``str`` table: name of table
        """
        for _ in range(3):
            try:
                tid = dbase("SELECT {} FROM {} WHERE {} = :cval".format(iname, table, cname), cval=cval)
                if tid:
                    return tid[0][0]

                return dbase("INSERT INTO {} ({}) VALUES(:cval) RETURNING {}".format(table, cname, iname), cval=cval)
            except Exception:
                pass

        return None

    def _log_ident(self, dbase):
        """
        check / insert machine

        :param ``hpc.rdb.base.BaseDB`` dbase: DB connection
        :return: ident of log
        :rtype: int
        """
        mach = gethostname().upper().split('.')[0]
        logid = dbase("SELECT IID FROM HPC_LOGITEM WHERE NAME = :name", name=mach)
        if logid:
            logid = logid[0][0]
        else:  # pragma: no cover
            logid = dbase("INSERT INTO HPC_LOGITEM (NAME, SLAVEID) VALUES(:name, :slaveid) RETURNING IID",
                          name=mach, slaveid=self.get_slave_ident(dbase))
        return logid

    @_connect
    def insert_job(self, **kwargs):
        r"""
        insert new job entry into DB

        :param \**dict kwargs:
        :keyword kwargs:
            * *jobid* ``int`` -- id of HPC job
            * *jname* ``str`` -- name of job
            * *headnode* ``str`` -- HPC head node name
            * *dbase* ``hpc.rdb.base.BaseDB`` -- DB connection
            * *submitstart* ``datetime`` -- start of submit time
            * *submitstop* ``datetime`` -- stop of submit time
        :return: DB's job index
        :rtype: int
        """
        mtc, fnc, cls = search(VALID_NAME, kwargs["jname"]), "n/a", "n/a"
        if mtc:
            fnc = (mtc.groups()[0] if mtc.groups()[0] else mtc.groups()[4]) or fnc
            cls = (mtc.groups()[0] if mtc.groups()[0] else mtc.groups()[2]) or cls

        # future
        # json = {
        #     "dbconn": "PGS_LND",
        #     "head": kwargs['headnode'],
        #     "usr": UID_NAME,
        #     "mach": gethostname().split('.')[0].upper(),
        #     "project": kwargs["project"],
        #     "template": kwargs["template"],
        #     "fnc": "ADM",
        #     "cls": "ADM",
        #     "version": version,
        #     "jobid": kwargs.get('jobid', int(environ.get("CCP_JOBID", environ.get("JobID", 0)))),
        #     "jname": kwargs['jname'],
        #     "hver": VERSION,
        #     "submitstart": kwargs['submitstart'].strftime('%Y-%m-%dT%H:%M:%S'),
        #     "changes": kwargs.get("changes"),
        #     "tasks": kwargs["tasks"],
        #     "spid": kwargs["spid"]
        # }
        #
        # res = post(f"http://localhost/ins_job", dumps(json))
        # print("posted {!s}\nreturned code={}, res={}".format(json, res.status_code, res.text))

        dbase = kwargs.pop("dbase")
        usridx = self._user_ident(dbase)
        logid = self._log_ident(dbase)
        prj = self._simple_ident(dbase, "PTID", "NAME", kwargs["project"], "HPC_PRJTMPL")
        tmpl = self._simple_ident(dbase, "PTID", "NAME", kwargs["template"], "HPC_PRJTMPL")
        pyv = self._simple_ident(dbase, "PYVERID", "VERSTR", version, "HPC_PYVER")

        if mtc:
            fnc = self._simple_ident(dbase, "FCID", "FCNAME", fnc, "HPC_FUNCLASS")
            cls = self._simple_ident(dbase, "FCID", "FCNAME", cls, "HPC_FUNCLASS")
        else:
            fnc = cls = 0

        # add recordings
        if dbase.db_type[0] == BaseDB.SQLITE:  # only if sqlite
            dbase("INSERT OR IGNORE INTO HPC_VER(VERSTR) VALUES(:hpc)", hpc=VERSION)
            if kwargs.get("records"):
                mids = [i[0] for i in dbase("SELECT MEASID FROM DMT_FILES")]
                upds = []
                for i in kwargs.get("records", []):
                    if i["measid"] not in mids:
                        upds.append(i)
                        mids.append(i["measid"])

                if upds:
                    dbase("INSERT INTO DMT_FILES (%s) VALUES(%s)"
                          % (", ".join(list(upds[0].keys())),
                             ", ".join([(":%d" % i) for i in range(1, len(list(upds[0].keys())) + 1)])),
                          insertmany=[tuple(i.values()) for i in upds])

        jid = dbase("INSERT INTO HPC_JOB (HPCJOBID, NODEID, IID, SID, JOBNAME, TASK_CNT, "
                    "SUBMITSTART, PRJID, TMPLID, CHANGES, PYVERID, FNCID, CLSID, VERID, SPID) "
                    "VALUES(:job, (SELECT NODEID FROM HPC_NODE WHERE NODENAME = :node), :usr, :sid, "
                    ":jnm, :tct, :strt, :prj, :tmpl, :chngs, :pyv, :fnc, :cls, "
                    "(SELECT MAX(VERID) FROM HPC_VER WHERE VERSTR IN (:hpc, 'unknown')), :spid) RETURNING JOBID",
                    job=kwargs.get('jobid', int(environ.get("CCP_JOBID", environ.get("JobID", 0)))),
                    node=kwargs['headnode'], jnm=kwargs['jname'], usr=usridx, hpc=VERSION, sid=logid,
                    strt=kwargs.get('submitstart'), prj=prj, tmpl=tmpl, fnc=fnc, cls=cls,
                    pyv=pyv, tct=kwargs.get("taskcnt", 0), chngs=dbase.stream2blob(kwargs.get("changes"), True),
                    spid=kwargs["spid"])

        if kwargs["tasks"]:  # let user get the exception from scheduler instead of here!
            dbase("INSERT INTO HPC_TASK (JOBID, HPCTASKID, SLAVEID, RECSIZE, RECDURATION) "
                  "VALUES(:1, :2, 0, :3, :4)",
                  insertmany=[(jid, t, int(v[0]), int(v[1]),) for t, v in iteritems(kwargs["tasks"])])

        return jid

    @_connect
    def update_job(self, **kwargs):  # pylint: disable=R0201
        r"""
        update logger and task to meas related information

        :param \**dict kwargs:
        :keyword kwargs:
            * *dbase* ``hpc.rdb.base.BaseDB`` -- DB connection
            * *jobid* ``int`` -- update for special job, default is last entry in db
            * *logger* ``obj`` -- logger instance
            * *resource* ``str`` -- resource type of job like *N*ode, *C*ore, *S*ocket, *G*pu
        :return: if job could be updated
        :rtype: bool
        """
        dbase = kwargs.pop('dbase')
        jid = kwargs["jobid"]

        if environ.get("MASTERID", "") and environ.get("JOB_NAME", "") == "HPC_submit":
            dbase("UPDATE HPC_MASTERJOB SET JOBID = :jid, STATUS = :stat WHERE MASTERID = :mid "
                  "AND NODEID = (SELECT NODEID FROM HPC_NODE WHERE NODENAME = :loc)",
                  jid=jid, stat="HPC job submitted", mid=environ["MASTERID"], loc=LOCATION)

        return dbase("UPDATE HPC_JOB SET SUBMIT_LOG = :sout, SUBMITSTOP = :stp, RESRS = :rsrc WHERE JOBID = :jid",
                     jid=jid, sout=dbase.stream2blob(kwargs["logger"], True), rsrc=str(kwargs["resource"])[0],
                     stp=datetime.utcnow()) == 1

    @_connect
    def update_task(self, **kwargs):  # pragma: no cover  # pylint: disable=R0912,R0914,R0915
        r"""
        update hpc_task table with infos.
        more keywords are table's columns, e.g. exitcode

        :param \**dict kwargs:
        :keyword kwargs:
            * *dbase* ``hpc.rdb.base.BaseDB`` -- DB connection
            * *headnode* ``str`` -- HPC head node name
            * *stdout* ``stream`` -- stdout stream
        :return: requeue count from DB
        :rtype: int
        :raises HpcError: if JobID defined as env var is not found in db
        """
        dbase = kwargs.get("dbase")
        head = kwargs.get("headnode", 'OTHER')
        hpcjobid = int(kwargs.get("jobid", environ.get("CCP_JOBID", environ.get("JobID", 1))))

        jobid = dbase("SELECT JOBID FROM HPC_JOB WHERE HPCJOBID = :job "
                      "AND NODEID = (SELECT NODEID FROM HPC_NODE WHERE NODENAME = :node)", job=hpcjobid, node=head)

        if jobid:
            jobid = jobid[0][0]
        else:
            raise HpcError("no job info inside Oracle!")

        # get requeue number in case we got requeued
        hpctaskid = int(environ.get("CCP_TASKID", environ.get("TaskID", 1)))
        try:
            taskid, requeue, rsz, rdn, starttm = dbase("SELECT TASKID, REQUEUE, RECSIZE, RECDURATION, "
                                                       "CASE WHEN STARTTIME IS NULL THEN 0 ELSE 1 END "
                                                       "FROM HPC_TASK WHERE JOBID = :job AND HPCTASKID = :task "
                                                       "ORDER BY REQUEUE", job=jobid, task=hpctaskid)[-1]
        except IndexError:
            raise HpcError("no task entry inside DB!")

        sout = kwargs.get("stdout", None)
        if sout:
            if sout.tell() > MAX_STDOUT + 4096:    # cut out with some extra space....
                sout.seek(0)
                sout = sout.read().split('\n')
                fsum = cumsum([len(i) for i in sout])
                fidx = next((i for i, v in enumerate(fsum) if v > MAX_STDOUT // 2)) - 1
                ridx = fsum.size - next((i for i, v in enumerate(reversed(fsum)) if fsum[-1] - v > MAX_STDOUT // 2)) + 1
                bstr = fsum[ridx] - fsum[fidx] + (ridx - fidx)
                strp = "stripped out {}B ({}) / {} lines, as log was too long: {}B ({})"\
                    .format(bstr, human_size(bstr), ridx - fidx,
                            fsum[-1] + fsum.size, human_size(fsum[-1] + fsum.size))
                sout = "\n".join(sout[:fidx] +
                                 [STDOUT_HINT.format(strp, "If you need more logging, "
                                                           "implement it on your client app!")] + sout[ridx:])
                # STDOUT_HINT.format(head, hpcjobid, hpctaskid)
            sout = dbase.stream2blob(sout, True)

        slaveid = self.get_slave_ident(dbase)

        state_sub = "(SELECT STATEID FROM HPC_STATE WHERE NAME = :snm)"
        if not starttm:  # never run b4
            dbase("UPDATE HPC_TASK SET SLAVEID = :slave, STARTTIME = :stm, STOPTIME = :etm, EXITCODE = :exc, "
                  "STDOUT = :sout, CPU_TIME = :cpt, STATEID = {}, TASKNAME = :tnm "
                  "WHERE TASKID = :task".format(state_sub),
                  task=taskid, slave=slaveid, stm=self._taskstart, etm=self._taskstop, exc=kwargs.get("exitcode", 0),
                  sout=sout, cpt=kwargs.get("cpu", 0), snm=kwargs["state"], tnm=kwargs.get("tname"))
        else:
            # tables = ["HPC_TASKERRORS", "HPC_ERRORS", "HPC_SUBTASK", "HPC_TASK_ECODE_HIST"]
            # if dbase.db_type[0] == BaseDB.ORACLE:
            #     tables.append("HPC_TASK_LOG")
            # cnts = [k[0] for k in dbase(" UNION ALL ".join([("SELECT COUNT(TASKID) FROM %s WHERE TASKID = :tid" % i)
            #                                                 for i in tables]), tid=taskid[0])]
            # for tab, cnt in zip(tables, cnts):
            #     if cnt > 0:
            #         dbase("DELETE FROM %s WHERE TASKID = :tid" % tab, tid=taskid[0])
            requeue += 1
            taskid = dbase("INSERT INTO HPC_TASK (JOBID, HPCTASKID, REQUEUE, SLAVEID, STARTTIME, STOPTIME, "
                           "EXITCODE, STDOUT, RECSIZE, RECDURATION, CPU_TIME, STATEID, TASKNAME) "
                           "VALUES(:job, :task, :req, :slave, :stm, :etm, :exc, :sout, :rsz, :rdn, :cpt, "
                           "{}, :tnm) RETURNING TASKID".format(state_sub), job=jobid, req=requeue, slave=slaveid,
                           stm=self._taskstart, task=hpctaskid, etm=self._taskstop, exc=kwargs.get('exitcode', 0),
                           sout=sout, rsz=rsz, rdn=rdn, cpt=kwargs['cpu'], snm=kwargs["state"], tnm=kwargs.get("tname"))

        if dbase.db_type[0] == BaseDB.ORACLE:  # connect log errors
            daemon_cmd("savelogs")
            lids = dbase("SELECT LOGID FROM HPC_LOG "
                         "WHERE DID = (SELECT IID FROM HPC_LOGITEM WHERE SLAVEID = :slaveid) "
                         "AND LOGTIME BETWEEN (SELECT STARTTIME FROM HPC_TASK WHERE TASKID = :taskid) "
                         "AND (SELECT STOPTIME FROM HPC_TASK WHERE TASKID = :taskid)",
                         slaveid=slaveid, taskid=taskid)
            if lids:
                dbase("INSERT INTO HPC_TASK_LOG (LOGID, TASKID) VALUES(:1, :2)",
                      insertmany=[(i[0], taskid) for i in lids])

            if kwargs.get("errmons"):
                dbase("INSERT INTO HPC_ERRMON (TASKID, ERRMON) VALUES(:1, :2)",
                      insertmany=[(taskid, i) for i in kwargs["errmons"]])

        # now we update sub-task info
        wdog_lst = kwargs.get("wdog", {})
        for i in self._envdata:
            cfg = None
            if i["cfg"]:
                cfgstr = str(i["cfg"])
                cfghsh = create_from_string(cfgstr)
                sadd, padd = "", {"chsh": cfghsh}
                if len(cfgstr) <= 4000:
                    sadd = " OR (CFGHASH IS NULL AND CFG=:cfg)"
                    padd["cfg"] = cfgstr
                for _ in range(3):
                    cfg = dbase("SELECT CFGID FROM HPC_SIMCFG WHERE CFGHASH = :chsh%s" % sadd, **padd)
                    if cfg:
                        cfg = cfg[0][0]
                        break

                    try:
                        cfg = dbase("INSERT INTO HPC_SIMCFG (CFGHASH, CFGBIN) VALUES(:chsh, :cbin) RETURNING CFGID",
                                    chsh=cfghsh, cbin=dbase.stream2blob(cfgstr, False))
                        break
                    except Exception as _:
                        pass
                    sleep(0.7)
                else:
                    cfg = None

            subid = dbase("INSERT INTO HPC_SUBTASK (TASKID, SUBTASKID, STARTTIME, STOPTIME, EXITCODE, COMMAND, PID, "
                          "MEASID, APP, CFGID, DISK_IO, CPU_TIME) "
                          "VALUES(:tid, :sid, :stm, :etm, :exc, :cmd, :pid, :meas, :app, :cfg, :dio, :cpt) "
                          "RETURNING SUBID", tid=taskid, sid=i["subtaskid"], stm=i["starttime"], etm=i["stoptime"],
                          exc=i["exitcode"], cmd=i["command"], pid=i["pid"], meas=i["measid"], app=i["app"], cfg=cfg,
                          dio=i["disk_io"], cpt=i["cpu"])

            # save subtask watchdog logs
            wdog_stsk = wdog_lst.get(i["subtaskid"])
            if len(wdog_stsk) > 2:
                dbase("INSERT INTO HPC_SUBTASK_WDOG (SUBID, IOLOAD, IOCONF, CPULOAD, CPUCONF, MEMLOAD, VIRTLOAD, "
                      "NETLOAD, WDOGTIME) VALUES(:sid, :iol, :ioc, :cld, :ccf, :mld, :vld, :nld, :wtm)",
                      insertmany=[[subid] + i for i in wdog_stsk])

        # insert error counters
        if self._ecnt:
            dbase("INSERT INTO HPC_TASKERRORS (TASKID, TYPEID, CNT) VALUES(:tid, :tpe, :cnt)",
                  insertmany=[(taskid, i, k,) for i, k in iteritems(self._ecnt)])

        # insert error items
        if self._errs:
            # for i in self._errs:
            dbase("INSERT INTO HPC_ERRORS (TASKID, TYPEID, CODE, DESCR, SRC, CNT, ERRDATE, MTSTIME) "
                  "VALUES(:tid, :tpe, :cd, :dsc, :src, :cnt, :ed, :mtm)",
                  insertmany=[(taskid, i["type"], i["code"], i["desc"], i["src"], i["cnt"], i["time"], i["mts"],)
                              for i in self._errs])

        # insert exitcode history
        if kwargs.get("ehist", []):
            dbase("INSERT INTO HPC_TASK_ECODE_HIST (TASKID, EXITCODE, LOGTIME) "
                  "VALUES(:tid, :ecd, :ltm)", insertmany=[(taskid, i[0], i[1],) for i in kwargs.get("ehist", [])])

        return requeue

    def end_task(self):
        """end the task"""
        self._taskstop = datetime.utcnow()
        return (self._taskstop - self._taskstart).total_seconds()


def env_exporter(**kwargs):
    r"""
    export collected data into a csv file

    :param \**dict kwargs:
    :keyword kwargs:
        * *headnode* ``str`` -- head node name
        * *jobid* ``int`` -- HPC job id
        * *sortcol* ``int`` -- field to sort results, default: TASK
        * *outfile* ``str`` -- CSV output file name
    :return: exitcode
    :rtype: int
    """
    sqargs = {'node': kwargs.get("headnode", DEFAULT_HEAD_NODE).upper(), 'jobid': kwargs["jobid"],
              'iter': True}
    fields = ['JOB', 'USER', 'TASK', 'NODE', 'START', 'EXITCODE']
    # conversation needed for datetime
    conv = [lambda x: x] * len(fields)
    conv[4] = lambda x: x.strftime("%y-%m-%d %H:%M:%S") if x else "no time"

    if isinstance(kwargs["outfile"], str):
        outfp, tbc = open(kwargs["outfile"], "w" if PY3 else "wb", newline=''), True
    else:
        outfp, tbc = kwargs["outfile"], False

    with BaseDB(kwargs.get("db", HPC_STORAGE_MAP[sqargs["node"]][3])) as hpc:
        csvlog = DictWriter(outfp, delimiter=';', fieldnames=fields)
        csvlog.writeheader()
        for row in hpc("SELECT HPCJOBID, NVL(u.DESCR, '-'), HPCTASKID, s.NAME, STARTTIME, EXITCODE "
                       "FROM HPC_JOB j INNER JOIN HPC_TASK USING(JOBID) "
                       "INNER JOIN HPC_SLAVE s USING(SLAVEID) "
                       "INNER JOIN HPC_LOGITEM u USING(IID) "
                       "INNER JOIN HPC_NODE n ON n.NODEID = j.NODEID "
                       "WHERE HPCJOBID = :jobid and NODENAME = :node "
                       "ORDER BY %d" % kwargs.get("sortcol", 3), **sqargs):
            csvlog.writerow({v: conv[i](row[i]) for i, v in enumerate(fields)})

    if tbc:
        outfp.close()

    return 0


def env_log(**kwargs):  # pylint: disable=R0911,R0912
    r"""
    return STDOUT from environment data

    :param \**dict kwargs:
    :keyword kwargs:
        * *db* ``str`` -- db to use
        * *headnode* ``str`` -- head node name
        * *jobid* ``int`` -- HPC job id
        * *taskid* ``int`` -- HPC task id
    :return: exitcode
    :rtype: int
    """
    sqargs = {'node': kwargs.get("headnode", DEFAULT_HEAD_NODE).upper(), 'job': kwargs["jobid"]}

    if kwargs["stdout"]:
        if kwargs["taskid"] is None:
            return "please provide valid task id!"

        with BaseDB(kwargs.get("db", HPC_STORAGE_MAP[sqargs["node"]][3])) as hpc:
            out = hpc("SELECT STDOUT, STARTTIME FROM HPC_TASK INNER JOIN HPC_JOB USING(JOBID) "
                      "INNER JOIN HPC_NODE USING(NODEID) WHERE NODENAME = :node AND HPCJOBID = :job "
                      "AND HPCTASKID = :task", lob=0, task=kwargs["taskid"], **sqargs)
        if not out:
            return "no STDOUT data found!"
        try:
            out[0][0] = decompress(out[0][0])
        except zliberr:
            pass

        if out[0][0] is None:
            return "task still running since %s" % out[0][1].strftime("%Y-%m-%d %H:%M:%S")

        cleared = []
        for l in out[0][0].decode().split('\n'):
            cleared.append(sub(r"^(.*)(<span style=\"background-color: \w+\">)(.*)(</span>)(.*)$", r"\1\3\5", l))
        return "\n".join(cleared)

    if kwargs["submit"]:
        with BaseDB(kwargs.get("db", HPC_STORAGE_MAP[sqargs["node"]][3])) as hpc:
            out = hpc("SELECT SUBMIT_LOG, SUBMITSTART, SUBMITSTOP FROM HPC_JOB "
                      "INNER JOIN HPC_NODE USING(NODEID) WHERE NODENAME = :node AND HPCJOBID = :job ", lob=0, **sqargs)
        if not out:
            return "no submit STDOUT data found!"

        if out[0][0] is None:
            return "sorry, nothing logged!"

        try:
            out[0][0] = decompress(out[0][0])
        except zliberr:
            pass

        cleared = []
        for l in out[0][0].decode().split('\n'):
            cleared.append(sub(r"^(.*)(<span style=\"background-color: \w+\">)(.*)(</span>)(.*)$", r"\1\3\5", l))

        return "{}: submit started\n{}{}: submit stopped"\
            .format(out[0][1].strftime("%Y-%m-%d %H:%M:%S"), "\n".join(cleared),
                    out[0][2].strftime("%Y-%m-%d %H:%M:%S"))

    if kwargs["commands"]:
        sqadd = ("HPCTASKID, ", "",)
        if kwargs["taskid"] is not None:
            sqadd = ("", "AND HPCTASKID = :task ",)
            sqargs["task"] = kwargs["taskid"]

        with BaseDB(kwargs.get("db", HPC_STORAGE_MAP[sqargs["node"]][3])) as hpc:
            out = hpc("SELECT %sSUBTASKID + 1, COMMAND FROM HPC_SUBTASK INNER JOIN HPC_TASK USING(TASKID) "
                      "INNER JOIN HPC_JOB USING(JOBID) INNER JOIN HPC_NODE USING(NODEID) "
                      "WHERE NODENAME = :node AND HPCJOBID = :job %s"
                      "ORDER BY HPCTASKID, SUBTASKID" % sqadd, **sqargs)
        if out:
            if len(out[0]) == 2:
                return "\n".join([("%d: %s" % i) for i in out])

            return "\n".join([("%d.%d: %s" % i) for i in out])

        out = "task not finished, having a look locally\n\n"
        dbbase = join(HPC_STORAGE_MAP[sqargs["node"]][1], "hpc", sqargs["node"])
        dbfile = [i for i in listdir(dbbase) if i.startswith("%d_" % sqargs["job"])]
        if len(dbfile) != 1:
            return out + ("no job folder exists on %s!" % dbbase)

        with JobDict(fp=join(dbbase, dbfile[0], "1_Input", "hpc", "job.json")) as job:
            return out + "\n".join([("%d: %s" % (j.subtask + 1, " ".join(j.command))) for j in job[kwargs["taskid"]]])
    return "Nothing done!"


def env_log_print(**kwargs):
    r"""
    print info from env_log

    :param \**dict kwargs:
    :keyword kwargs:
        * *db* ``str`` -- db to use
        * *headnode* ``str`` -- head node name
        * *jobid* ``int`` -- HPC job id
        * *taskid* ``int`` -- HPC task id
    :return: exitcode
    :rtype: int
    """
    print(env_log(**kwargs))
    return 0


def env_stdout_search(**kwargs):  # pylint: disable=R0912
    r"""
    search all stdout of a certain HPC job by some pattern

    :param \**dict kwargs:
    :keyword kwargs:
        * *db* ``str`` -- db to use
        * *headnode* ``str`` -- head node name
        * *jobid* ``int`` -- HPC job id
        * *pattern* ``str`` -- regular expression pattern
    :return: exitcode
    :rtype: int
    """
    sqargs = {'node': kwargs.get("headnode", DEFAULT_HEAD_NODE).upper(), 'job': kwargs["jobid"]}
    cnt = 0

    with BaseDB(kwargs.get("db", HPC_STORAGE_MAP[sqargs["node"]][3])) as hpc:
        for i in hpc.execute("SELECT HPCTASKID, STDOUT FROM HPC_TASK INNER JOIN HPC_JOB USING(JOBID) "
                             "INNER JOIN HPC_NODE USING(NODEID) WHERE NODENAME = :node AND HPCJOBID = :job "
                             "AND EXITCODE IS NOT NULL ORDER BY HPCTASKID",
                             lob=1, **sqargs):
            if i[1] is None:
                continue

            spos = 0
            out = i[1]
            while spos < len(out):
                mtc = search(kwargs["pattern"], out[spos:])
                if mtc:
                    cnt += 1
                    for k in range(mtc.start() + spos, 0, -1):
                        if out[k] == '\n':
                            break
                    else:
                        k = None
                    for j in range(mtc.end() + spos, len(out)):
                        if out[j] == '\n':
                            break
                    else:
                        j = None
                    if k and j:
                        print("task %d fits at line %3d: %s"
                              % (i[0], out[:mtc.start() + spos].count("\n") + 1, out[k + 1:j]))
                    spos += mtc.end()
                else:
                    spos = len(out)

    if cnt == 0:
        print("nothing found inside job %d!" % kwargs["jobid"])
    else:
        print("found %d occurances inside job %d." % (cnt, kwargs["jobid"]))

    return 0


def env_export_bpl(**kwargs):  # pylint: disable=R0912,R0914,R0915,import-outside-toplevel
    r"""
    create a bpl file from given job with only those recordings processed with a certain task state or exitcode.

    :param \**dict kwargs:
    :keyword kwargs:
        * *headnode* ``str`` -- head node name
        * *jobid* ``int`` -- HPC job id
        * *state* ``str`` -- state of task to filter
        * *exitcode* ``str`` -- filter for exit codes
        * *bpl* ``str`` -- output bpl file
    :return: exitcode
    :rtype: int
    """
    # connect to server and open job
    head = kwargs.get("headnode", DEFAULT_HEAD_NODE).upper()
    with HpcSched(head) as sched:
        try:
            job = sched.OpenJob(kwargs["jobid"])
        except Exception as ex:
            print("your job cannot be opened: '{!s}'".format(ex))
            return []

        job_db, db_path, fnd = None, join(HPC_STORAGE_MAP[head][1], "hpc", head), False
        for i in glob(join(db_path, "%s_*" % kwargs["jobid"])):
            for k in ("1_Input", "1_Input\\hpc",):
                job_db = join(db_path, i, k, "job.json")
                if exists(job_db):
                    fnd = True
                    break
            if fnd:
                break
        else:
            print("cannot find job info!")
            return []

        # get the whole task list of the job filtered by either status and / or exitcode
        filters = sched.CreateFilterCollection()
        if kwargs["exitcode"]:
            filters.Add(sched.props.FilterOperator.Equal, sched.propid.Task_ExitCode, kwargs["exitcode"])
        if kwargs["state"].lower() != 'all':
            filters.Add(sched.props.FilterOperator.Equal, sched.propid.Task_State, TASKSTATE[kwargs["state"]])

        task_list = job.GetTaskList(filters, None, False)
        recs, lrec = [], []
        try:
            with JobDict(fp=job_db) as jdb:
                for task in task_list:  # pylint: disable=R1702
                    try:
                        for subt in jdb[str(task.TaskId.JobTaskId)]:
                            if subt.command[0].endswith("measapp.exe"):
                                for i in subt.command[1:]:
                                    if i.startswith("-lr"):
                                        if i[3:].lower() not in lrec:
                                            lrec.append(i[3:].lower())
                                            recs.append(i[3:])
                                        break
                                    if i.startswith("-lb"):
                                        recl = [k.get("fileName")
                                                for k in parse(join(db_path, "bpl", basename(i[3:]))).getroot()]
                                        for k in recl:
                                            if k.lower() not in lrec:
                                                lrec.append(k.lower())
                                                recs.append(k)
                                        break
                    except IndexError as _:
                        pass  # now, we're on a parametric task, although False, it's still delivered by HPC
        except Exception as _:
            print("ERROR reading from %s" % job_db)
            return 0

    if recs:
        # arrange bpl file
        bpl = kwargs["bpl"]
        if not hasattr(bpl, 'read'):
            if bpl == "<job_id>.bpl":
                bpl = "%d.bpl" % kwargs["jobid"]

            # create a folder for bpl extraction
            bpl_folder = dirname(bpl)
            if bpl_folder != '':
                try:
                    makedirs(bpl_folder)
                except Exception:
                    pass

        # build xml
        with Bpl(bpl, "w") as bfp:
            bfp.extend(recs)

        print("%d recording(s) written to %s" % (len(recs), bpl))
    else:
        print("no failed MTS tasks inside job %d" % kwargs["jobid"])

    return 0


def env_bpl_filter(**kwargs):
    r"""
    filter input bpl by location and output only valid ones

    :param \**dict kwargs:
    :keyword kwargs:
        * *inbpl* ``str`` -- input BPL file
        * *outbpl* ``str`` -- output BPL file
        * *rest* ``str`` -- left over BPL file
        * *location* ``str`` -- location to use (e.g. LND for Lindau)
    :return: 0
    :rtype: int
    """
    rest = kwargs.get('rest')
    if rest is not None:
        rest = Bpl(rest, "w")

    collname = kwargs["inbpl"].split('\\') + [None]

    with Collection(mode=CollManager.READ, name=collname[0], label=collname[1]) as coll, \
            Bpl(kwargs["outbpl"], "w") as outbpl:
        for i in coll:
            for k in i:
                if k.location == kwargs["location"]:
                    ble = BplListEntry(k.filepath)
                    for l in k.relts:
                        if l != [None, None]:
                            ble.append(l[0], l[1], (True, True,))
                    outbpl.append(ble)
                    break
            else:
                if rest is not None:
                    rest.append(BplListEntry(i.filepath, Section(k.beginrelts, k.endrelts, (True, True,))))

    if rest is not None:
        rest.write()

    print("found %d recordings on %s location for collection %s"
          % (len(outbpl), kwargs["location"].upper(), kwargs["inbpl"]))

    return 0


def env_bpl_operation(**kwargs):
    r"""
    do some operation on the bpl's given and output the result accordingly

    :param \**dict kwargs:
    :keyword kwargs:
        * *inbpl* ``str`` -- input BPL file
        * *outbpl* ``str`` -- output BPL file
        * *arith* ``str`` -- math operation to do, e.g. (or, and, xor)
    """
    arith = {"xor": lambda x, y: x ^ y, "or": lambda x, y: x | y, "and": lambda x, y: x & y, "sub": lambda x, y: x - y}

    with Bpl(kwargs["inbpls"][0]) as src1, Bpl(kwargs["inbpls"][1]) as src2, Bpl(kwargs["outbpl"], mode='w') as trgt:
        trgt.extend(arith[kwargs["arith"]](src1, src2))
