"""
error_db.py
-----------

hpc error database interface
"""
# - Python imports -----------------------------------------------------------------------------------------------------
from sys import version_info
from hashlib import sha256
from functools import partial
from datetime import datetime as dt
from time import sleep
from six import iteritems, PY2
# from pytz import utc, timezone
# from time import timezone as tzone
if version_info < (3, 0):
    from types import StringTypes
else:
    StringTypes = (str,)

# - HPC imports --------------------------------------------------------------------------------------------------------
from ..version import VERSION
from .base import BaseDB, tohex
from .env_data import EnvData
from ..core.dicts import DefDict
from ..core.path import splitdrive
from ..core.logger import DummyLogger
from ..core.tds import HPC_STORAGE_MAP
from ..mts.parser import XlogHandler


# - classes -----------------------------------------------------------------------------------------------------------
class ErrorDB(BaseDB):  # pylint: disable=R0902
    """
    Hpc Error DB Interface

    This Class provides a interface towards the Error-DB from HPC.
    All Errors which are found in the Subtask xxx_check will be stored here.
    """

    def __init__(self, node, jobid, **kwargs):
        r"""
        error DB interface

        :param str node: name of node to use
        :param int jobid: id of job to use
        :param dict kwargs: see below
        :keyword \**kwargs:
            * *logger* (``Logger``): logger instance
            * *mode* (``str``): mode can be 'r' for reading, 'w' for writing
        """
        BaseDB.__init__(self, kwargs.pop('db', HPC_STORAGE_MAP[node][3]), autocommit=kwargs.pop('autocommit', False),
                        functions=[tohex])

        # set some local things
        self._logger = kwargs.pop('logger', DummyLogger())

        mode = kwargs.pop('mode', 'r')
        assert mode in ('r', 'w'), "mode should be either 'r' or 'w' (read / write)!"

        for _ in range(12):
            try:
                self._jobid = self("SELECT JOBID FROM HPC_JOB INNER JOIN HPC_NODE USING(NODEID) "
                                   "WHERE NODENAME LIKE :node AND HPCJOBID = :job", node=node, job=jobid)
                if self._jobid:
                    self._jobid = self._jobid[0][0]
                elif mode == 'w':
                    self._jobid = self("INSERT INTO HPC_JOB (HPCJOBID, NODEID, VERID) "
                                       "VALUES(:job, (SELECT NODEID FROM HPC_NODE WHERE NODENAME LIKE :node), "
                                       "(SELECT VERID FROM HPC_VER WHERE VERSTR = :ver)) RETURNING JOBID",
                                       job=jobid, node=node, ver=VERSION, commit=True)
                break
            except Exception as _:
                sleep(3)

        if self._jobid == []:
            self._jobid = None
            self.tasks = []
        else:
            self.tasks = [t[0] for t in self("SELECT HPCTASKID FROM HPC_TASK WHERE JOBID = :job", job=self._jobid)]

        self._slaveid = EnvData(db=self).get_slave_ident()
        self.err_types = {i[0]: i[1] for i in self("SELECT TYPENAME, TYPEID FROM HPC_ERRTYPE")}
        self._meass = {}

        # only because of pylint
        self._err_items = self._task_items = self._task_errors = self._items_commited = None
        self._cleanup()

    def __exit__(self, *args):  # value / traceback
        """just exit"""
        self.commit_items()
        BaseDB.__exit__(self, args)

    @property
    def jobid(self):
        """
        :return: db's jobid
        :rtype: int
        """
        return self._jobid

    def items(self, task_id):
        """
        :return: all error items for given task
        :rtype: int
        """
        return [(XlogHandler.levels[i['type']].capitalize(), i['cnt'], i['code'], i['desc'], i['src'], i['mts'])
                for i in list(self._err_items.values()) if i['task'] == task_id]

    def add_item(self, task_id, type_id, err_code, err_desc, err_src, meas=0,  # pylint: disable=R0912,R0913
                 time=dt.utcnow(), mts_ts=0, cnt=1):
        """
        Add a new item entry into hpc's error database.

        :param task_id:  Hpc Task ID
        :type task_id:   int
        :param type_id:  Error Type ID
        :type type_id:   int | str
        :param err_code: Error Code of the Error
        :type err_code:  int
        :param err_desc: Error Description of the Error
        :type err_desc:  str
        :param err_src:  Additional Error Source Information
        :type err_src:   str
        :param meas:     measurement which was used
        :type meas:      str | int
        :param time:     time of item
        :type time:      datetime
        :param mts_ts:   time of MTS
        :type mts_ts:    int
        :param cnt:      counter of occurence of this error
        :type cnt:       int
        """
        if task_id not in self._task_items:
            self._task_items.append(task_id)

        # find measid from path, and store temporarily
        if isinstance(meas, StringTypes):
            srv = splitdrive(meas)
            if srv[0] != '':
                part = srv[0].split('\\')
                meas = '\\\\%s%%\\%s%s' % (part[-2].split('.')[0], part[-1], srv[1])
            if meas not in self._meass:
                measid = self("SELECT MEASID FROM DMT_FILES WHERE FILEPATH LIKE :meas", meas=meas)
                if measid:
                    measid = measid[0][0]
                    self._meass[meas] = measid
                    self._logger.debug("meas '%s' has ID %d" % (meas.replace('%', ''), measid))
                else:
                    measid = 0
                    self._logger.error("meas: %s" % meas)
            else:
                measid = self._meass[meas]
        else:
            measid = meas

        if isinstance(type_id, StringTypes):
            type_id = self.err_types[type_id.capitalize()]

        chk = sha256()
        if PY2:
            chk.update("{}{}{}{}{}{}".format(task_id, type_id, err_code, err_desc, err_src, measid).
                       decode('utf-8').encode('latin1'))
        else:
            chk.update("{}{}{}{}{}{}".format(task_id, type_id, err_code, err_desc, err_src, measid).encode())
        if chk.hexdigest() in self._err_items:
            self._err_items[chk.hexdigest()]['cnt'] += cnt
        else:
            self._err_items[chk.hexdigest()] = {'task': task_id, 'type': type_id, 'code': err_code, 'desc': err_desc,
                                                'src': err_src, 'meas': measid, 'time': time, 'mts': mts_ts, 'cnt': cnt}
        self._task_errors[(task_id, type_id)] += cnt

        self._items_commited = False

    def add_crash(self, task_id, err_code, err_desc, err_src):
        """
        Add a new crash entry into the Database.

        :param int task_id:   Hpc Task ID
        :param int err_code:  Error Code of the Error
        :param str err_desc:  Error Description of the Error
        :param str err_src:   Additional Error Source Inforamtion
        """
        self.add_item(task_id, "crash", err_code, err_desc, err_src, meas=0, cnt=1)

    def add_error(self, task_id, err_code, err_desc, err_src, cnt=1):  # pylint: disable=R0913
        """
        Add a new Error entry into the Database.

        :param int task_id:   Hpc Task ID
        :param int err_code:  Error Code of the Error
        :param str err_desc:  Error Description of the Error
        :param str err_src:   Additional Error Source Information
        :param int cnt:       counter of occurence of this error
        """
        self.add_item(task_id, "error", err_code, err_desc, err_src, meas=0, cnt=cnt)

    def add_exception(self, task_id, err_code, err_desc, err_src, cnt=1):  # pylint: disable=R0913
        """
        add a new Exception entry into the Database.

        :param int task_id:   Hpc Task ID
        :param int err_code:  Error Code of the Error
        :param str err_desc:  Error Description of the Error
        :param str err_src:   Additional Error Source Information
        :param int cnt:       counter of occurence of this error
        """
        self.add_item(task_id, "exception", err_code, err_desc, err_src, meas=0, cnt=cnt)

    def add_count(self, task_id, type_id, cnt=1):
        """
        add a certain count to task errors

        :param int task_id: id of hpc task
        :param int type_id: id of type
        :param int cnt: how many should be added
        """
        if task_id not in self._task_items:
            self._task_items.append(task_id)

        self._task_errors[(task_id, type_id)] += cnt
        self._items_commited = False

    def commit_items(self, purge=False):  # pylint: disable=R1260
        """
        commit error items

        :param bool purge: remove task results beforehand
        """
        if purge or not self._items_commited:
            # get already inserted tasks
            tasks = dict(self("SELECT HPCTASKID, TASKID FROM HPC_TASK WHERE JOBID = :job", job=self._jobid))
            for tit in self._task_items:
                if tit in tasks:
                    self("DELETE FROM HPC_TASKERRORS WHERE TASKID = :task", task=tasks[tit])
                    self("DELETE FROM HPC_ERRORS WHERE TASKID = :task", task=tasks[tit])

        if self._items_commited:
            return

        # add missing tasks
        for tit in self._task_items:
            cnt = 0
            if tit not in tasks:
                tasks[tit] = self("INSERT INTO HPC_TASK (JOBID, HPCTASKID, SLAVEID) "
                                  "VALUES(:job, :task, :slave) RETURNING TASKID",
                                  job=self._jobid, task=tit, slave=self._slaveid)
                cnt += 1
            self._logger.debug("committed %d new task item(s)" % cnt)

        # tmzone = timezone('Etc/GMT%+d' % (tzone / 3600))
        # values with timezone (when DB table type has TZ enabled)
        # values=[(tasks[i['task']], i['type'], i['code'], i['desc'], i['src'], i['cnt'],
        #          i['time'].replace(tzinfo=tmzone).astimezone(utc).strftime(dtfmt)
        #          if self._db_type == 0 else i['time'].replace(tzinfo=tmzone).astimezone(utc))
        #         for i in self._err_items.values()]

        # insert error items
        for tit in self._task_items:
            if purge:
                cnt = 0
            else:
                cnt = self("SELECT COUNT(*) FROM HPC_TASKERRORS WHERE TASKID = :task", task=tasks[tit])[0][0]
            if cnt == 0:
                dtfmt = '%y-%m-%d %H:%M:%S'
                values = [(tasks[i['task']], i['type'], i['code'], i['desc'], i['src'], i['cnt'],
                           i['time'].strftime(dtfmt) if self._db_type == BaseDB.SQLITE
                           else i['time'], i['mts']) for i in list(self._err_items.values())]
                if values:
                    cnt = self("INSERT INTO HPC_ERRORS (TASKID, TYPEID, CODE, DESCR, SRC, CNT, ERRDATE, MTSTIME) "
                               "VALUES(:1, :2, :3, :4, :5, :6, :7, :8)", insertmany=values)
                    self._logger.debug("committed %d item(s)" % cnt)

                # add things to hpc_taskerrors here
                cnt = self("INSERT INTO HPC_TASKERRORS (TASKID, TYPEID, CNT) VALUES(:1, :2, :3)",
                           insertmany=[(tasks[k[0]], k[1], v) for k, v in iteritems(self._task_errors)])
                self._logger.debug("committed %d task error item(s)" % cnt)

        self.commit()
        self._cleanup()

    def _cleanup(self):
        """reset values"""
        self._err_items = {}
        self._task_items = []
        self._task_errors = DefDict(0)
        self._items_commited = True

    def delete_errors(self, task_id=None):
        """
        delete all errors, exceptions and crashes, which belong to a dedicated task (if given)

        :param int task_id: task id to take care of, otherwise remove all from job
        :return: number of deletions
        :rtype: int
        """
        if task_id is None:
            cnt = self("DELETE FROM HPC_TASKERRORS WHERE TASKID = (SELECT TASKID FROM HPC_TASK "
                       "WHERE JOBID = :job)", job=self._jobid)
            cnt += self("DELETE FROM HPC_ERRORS WHERE TASKID = (SELECT TASKID FROM HPC_TASK "
                        "WHERE JOBID = :job)", job=self._jobid)
            return cnt

        cnt = self("DELETE FROM HPC_TASKERRORS WHERE TASKID = (SELECT TASKID FROM HPC_TASK "
                   "WHERE JOBID = :job AND HPCTASKID = :task)", job=self._jobid, task=task_id)
        cnt += self("DELETE FROM HPC_ERRORS WHERE TASKID = (SELECT TASKID FROM HPC_TASK "
                    "WHERE JOBID = :job AND HPCTASKID = :task)", job=self._jobid, task=task_id)
        return cnt

    def __getattr__(self, item):
        """
        old signatures looked like that:
            def get_count(self, task_id=None, err_type=None)
                '''return the amount of errors for given task and type (either or both can be None).'''

        also provides those:
            def get_num_crashes(self, task_id=None)
            def get_num_exceptions(self, task_id=None)
            def get_num_errors(self, task_id=None)
            def get_num_alerts(self, task_id=None)
            def get_num_information(self, task_id=None)
            def get_num_debugs(self, task_id=None)

        """
        def get_count(*args, **kwargs):
            r"""
            get count

            :param \*args: *err_type*, *task_id*: see below
            :keyword \**kwargs:
                * *err_type* (``str``): type of error to get count for
                * *task_id* (``int``): number of task
            :return: a number of how much items we have in DB
            :rtype: int
            """
            if self._jobid is None:
                return 0

            vals = {'job': self._jobid}
            errtype = kwargs.pop('err_type', None if len(args) <= 1 else args[1])
            if errtype in (None, "count"):
                errtype = ""
            else:
                vals['terr'] = self.err_types[errtype.capitalize()]
                errtype = " AND TYPEID = :terr "

            taskid = kwargs.pop('task_id', None if len(args) == 0 else args[0])
            if taskid is None:
                taskid = ""
            else:
                vals['task'] = taskid
                taskid = " AND HPCTASKID = :task "

            sql = ("SELECT SUM(CNT) FROM HPC_ERRTYPE INNER JOIN HPC_TASKERRORS USING(TYPEID) "
                   "INNER JOIN HPC_TASK USING(TASKID) INNER JOIN HPC_JOB USING(JOBID) "
                   "WHERE JOBID = :job %s%s"
                   "GROUP BY TYPENAME" % (errtype, taskid))

            return sum([k[0] for k in self(sql, **vals)])

        item = item.rstrip('es').lower()
        if item in ([("get_num_" + i.lower()) for i in self.err_types] + ["get_count"]):
            item = item[8 if item[4:].startswith('num_') else 4:]

            return partial(get_count, err_type=item)

        raise AttributeError(item)

    def get_list_of_incidents(self, task_id=None, err_type=None, **kwargs):
        """
        get a list of all incidents (errors, exceptions and crashes)
        for the given job_id and, optionally, task_id

        :param int task_id: hpc task id to get the list from
        :param int err_type: type of incidents to return: 'Error', 'Exception', 'Crash'
        :param kwargs: additional parameters to execute statement
        :return: list of incidents
        :rtype: list
        """
        if self._jobid is None:
            return []

        if err_type is None:
            err_type = list(self.err_types.values())
        elif isinstance(err_type, StringTypes):
            err_type = [self.err_types[err_type.capitalize()]]

        args = {'job': self._jobid}
        args.update({("id%d" % (k + 1)): v for k, v in enumerate(err_type)})

        sql = ("SELECT TYPEID, TYPENAME, SUM(CNT), '0x' || %s, DESCR, NVL(SRC, '-'), NVL(%s, '-') "
               "FROM HPC_ERRORS INNER JOIN HPC_ERRTYPE USING(TYPEID) "
               "INNER JOIN HPC_TASK USING(TASKID) "
               "INNER JOIN HPC_JOB USING(JOBID) "
               "WHERE JOBID = :job AND TYPEID IN (%s) "
               % (["TOHEX(CODE)", "TRIM(TO_CHAR(CODE,'XXXXXXXX'))"][self._db_type],
                  ["strftime('%%Y-%%m-%%d %%H:%%M:%%S', ERRDATE)",
                   "TO_CHAR(ERRDATE, 'YYYY-MM-DD HH24:MI:SS')"][self._db_type],
                  ", ".join([":id%d" % i for i in range(1, len(err_type) + 1)])))

        if task_id is not None and task_id != []:
            if isinstance(task_id, int):
                task_id = [task_id]
            args.update({("tsk%d" % (k + 1)): v for k, v in enumerate(task_id)})
            sql += "AND HPCTASKID in (%s) " % ", ".join([":tsk%d" % i for i in range(1, len(task_id) + 1)])
        sql += ("GROUP BY TYPEID, TYPENAME, CODE, DESCR, SRC, ERRDATE "
                "ORDER BY 1, 4, 3 DESC")
        args.update(kwargs)

        return self(sql, **args)
