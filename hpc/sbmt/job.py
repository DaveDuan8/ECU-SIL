"""
job.py
------

job module for HPC.

**User-API Interfaces**

    - `Job` (complete package)
"""
from __future__ import print_function
# pylint: disable=E1101
# - import Python modules ----------------------------------------------------------------------------------------------
import sys
from os import environ, makedirs, linesep, name as osname
from os.path import splitext, join, dirname, basename, abspath
from datetime import datetime
from time import sleep
from collections import defaultdict
from socket import gethostname
from platform import architecture, python_version_tuple
from zlib import decompress as zdeco
from traceback import extract_stack
from re import search
from json import dump
from six import PY2, iteritems

if PY2:
    from StringIO import StringIO  # pylint: disable=E0401
    PermissionError = IOError  # pylint: disable=W0622
else:
    from dill import loads as dloads
    from io import StringIO

# - import HPC modules -------------------------------------------------------------------------------------------------
from ..version import VERSION
from ..sched.sched_defs import SHORT_TEST_RUNTIME, STD_SWEEP_RUNTIME, MAX_SWEEP_RUNTIME
from ..sched.scheduler import Scheduler
from ..core import UID_NAME, LOGINNAME, proc_vals as pvs
from ..core.tds import VALID_PYVER, HPC_STORAGE_MAP, DEFAULT_HEAD_NODE, LIN_EXE, HPC_SHARES, MAX_TASKS, DEVS, DEV_HEAD,\
    PY_2_EXE, SHORT_VER, validate_project
from ..core.hpc_defs import JobPriority, JobUnitType, TaskType
from ..core.convert import arg_trans
from ..core.logger import get_logger, deprecated, suppress_warnings, HpcPassword
from ..core.robocopy import Robocopy
from ..core.error import HpcError, ERR_OK, UNFAILING_EXITCODES, SKIP_EXITCODES
from ..core.dicts import JobDict, BSIG_CHK
from ..core.path import win2linux, linux2win
from ..rdb.sqlite_defs import create_sqlite
from ..rdb.base import BaseDB
from ..rdb.env_data import EnvData
from .task import Task

from .task_factory import TaskFactory
from .task_factory_mts import TaskFactoryMTS
from .subtask_factory import SubTaskFactory


# - classes ------------------------------------------------------------------------------------------------------------
class Job(object):  # pylint: disable=R0902,R0904
    """
    **main Interface of HPC.**

    - You can use this class to submit jobs onto the ADAS HPC Cluster.
    - For minimum functionality you need at least the `hpc` and :class:`hpc.TaskFactory`.
    - To simulate a whole submit and execute a testrun, you can use instead of
      the Hpc the `HpcSim` class.

    **1. Example:**::

        # Import hpc
        import hpc

        #Connect to the HPC Server
        with hpc.Job(name='Trainging_Ping', project='MFC310') as job:
            factory = hpc.TaskFactory(job)
            factory.create_task('ping 127.0.0.1')

    **2. Example**::

        # Import hpc
        import hpc

        # calls the init and start job creation
        with hpc.Job(name="my first job", project="Short_Test") as job:
            # create a factory from myJob to be able to create your tasks
            fact = hpc.TaskFactory(job)
            # now create the task(s) finally
            fact.create_task('ping 127.0.0.1')
        # when *with* exits, job is going to get submitted automagically.
    """

    __opt_args__ = ["robo_retry", "robo_wait", "eoe", "task_out", "wdog_init", "wdog_loop", "wdog_prns",
                    "mem_max", "virt_max", "ignore_codes", "mtscheck", "procdump", "bsig_ext"]

    __xml_slots__ = ["name", "is_exclusive", "run_until_canceled", "notify_on_completion", "notify_on_start",
                     "fail_on_task", "auto_calculate_max", "auto_calculate_min", "requested_nodes",
                     "min_nodes", "min_sockets", "min_cores", "max_node_cores",
                     "max_sockets", "max_cores", "max_nodes", "unit", "project", "template", "priority",
                     "hold_until", "depends", "parent_jobs", "TaskExecutionFailureRetryLimit"]

    __deprecated__ = {"set_project": "project", "set_priority": "priority", "set_job_unit": "unit",
                      "set_hold_until": "hold_until", "set_requested_nodes": "requested_nodes",
                      "set_max_core_count": "max_cores", "set_max_socket_count": "max_sockets",
                      "set_max_node_count": "max_nodes",
                      "set_parent_job_ids": "parent_jobs"}

    def __init__(self, *args, **kwargs):  # pylint: disable=R1260,R0912,R0915
        r"""
        initialize HPC job

        :param \*args: *head_node*, *name* and *project* must be given, others are optional (kwargs)

        :keyword \**kwargs:
            * *head_node* (``str``): head node to use, default: site local simulation cluster
            * *name* (``str``): :py:meth:`name of job <hpc.core.tds.validate_name>`
            * *project* (``str``): name of project to use
            * *template* (``str``): name of template
            * *priority* (``JobPriority``): initial priority, int and string values are allowed, e.g. 'Normal+100'
            * *unit* (``JobUnit``): job unit (JobUnit), can be either Node, Core or Socket
            * *pyexe* (``str``): python.exe including path pointing to another interpreter job should execute on
            * *notify_on_start* (``bool``): receive an email when job starts
            * *notify_on_completion* (``bool``): receive an email when job completes
            * *hold_time* (``datetime``): local date/time for first try to start job.
            * *depends* (``list``): job ID('s) this job should depend upon
            * *requested_nodes* (``list``): list of nodes this job should run
            * *excluded_nodes* (``list``): list of nodes to be excluded
            * *min_hd_space* (``float``): minimum HD space requirement for a node
            * *env* (``dict``): dictionary containing additional environment variables
            * *venv* (``list`` | ``str``): list of requirements.txt entries or requirements file name
            * *venv_sys* (``bool``): use system-site-packages on venv, default: True
            * *popts* (``str``): extra options to pip when using venv next to -r
                (=> https://pip.pypa.io/en/stable/cli/pip_install/#options)
            * *xlog* (``Logger``): extra logger to use and to log to
            * *mtscheck* (``bool``): check MTS errmon / crashrep log files, default: True
            * *procdump* (``bool``): do a procdump on "frozen" MTS, default: False
            * *bsig_check* (``bool``): check bsig outputs from MTS, default: True
            * *bsig_ext* (``list``): bsig extensions to be used, default: [".bsig"]
            * *precmd* (``str``): prepare command to be executed after preparation is done
            * *relcmd* (``str``): release command to be executed before release is done
            * *exit_codes* (``list``): list of codes to Finish each task
            * *add_exit_codes* (``list``): list of codes to append to exit_codes
            * *ignore_codes* (``list``): list of codes to completely ignore
            * *robo_retry* (``int``): retry count for result copy back (starter)
            * *robo_wait* (``int``): wait time between those retries (starter)
            * *task_out* (``bool``): copy back task's output data to task folder instead of _data folder
            * *runas* (``str``): <username>[:<password>] to run the job as (password is only needed for first time)
            * *eoe* (``bool``): on first failure subtask execution stops, no further processing done if set

        :raises hpc.HpcError: on any
        """
        self._hver = VERSION
        self._enter = self._cancel = False
        kwargs = arg_trans([['head_node', DEFAULT_HEAD_NODE], 'name', 'project'], *args, **kwargs)

        self.loglevel = kwargs.get('loglevel', 2)
        self.errorlevel = kwargs.get('errorlevel', 1)
        self.maxtasks = kwargs.get('max_tasks', MAX_TASKS)
        self.bpl_cnt = 0
        self._streamer = StringIO()  # TemporaryFile(prefix='hpc_')
        loggers = [[sys.stdout, False], [self._streamer, True]] if self.loglevel >= 1 else [[self._streamer, True]]
        if "xlog" in kwargs:
            loggers.append([kwargs["xlog"], False])
        self._logger = get_logger('PyHPC:', loggers, level=self.loglevel)

        if sys.platform == "win32" and sys.version not in VALID_PYVER:
            warnfo = getattr(self._logger, "info" if environ.get("BUILD_URL") else "warning")
            warnfo("you're submitting from a non-supported Python version: %s!", sys.version)
            warnfo("please, use latest official: "
                   "https://confluence.auto.continental.cloud/display/GITTE/Python+Installers")

        if PY2 and LOGINNAME not in DEVS:
            self._logger.warning("Python 2 is dead (https://www.python.org/dev/peps/pep-0373)")
            memorate = max(3, (datetime.utcnow() - datetime(2020, 4, 15)).days // 32)
            self._logger.info("we commemorate a bit (%ds), giving you time to switch to Python 3 in the meanwhile....",
                              memorate)
            sleep(memorate)

        msgadd = environ.get("CCP_TASKCONTEXT", "")
        if msgadd:
            msgadd = " from {}.{}".format(environ.get("CCP_CLUSTER_NAME", "???"), msgadd)
        self._logger.info("using HPC V %s with %s (%s) on host %s%s", self._hver, ".".join(python_version_tuple()),
                          architecture()[0], gethostname().upper().split('.')[0], msgadd)

        head_node = str(kwargs.pop("head_node")).split('.')[0].upper()
        self._job_sim = kwargs.get('sim', False)
        # check for latest version
        if LOGINNAME not in DEVS:
            try:
                with open(join(HPC_STORAGE_MAP[head_node][1], "hpc", "HPC_Python", "latest")) as fp:
                    latest = fp.read()
            except PermissionError:  # pragma: no cover
                if not self._job_sim:
                    raise HpcError("seems, you don't have HPC_User rights yet?!.")
                latest = VERSION
            except Exception as ex:  # pragma: no cover
                if not self._job_sim:
                    raise HpcError("unknown error: {!s}".format(ex))
                latest = VERSION
            if latest != VERSION:
                self._logger.error("Please, upgrade HPC package, submission might fail very soon!")

        # check deprecations.....
        name = kwargs.pop('name')
        if not name:
            name = kwargs.pop('job_name', '')
            if name:
                self._logger.warning("do not use 'job_name' any more, just use 'name' instead!")
            else:
                raise HpcError("please, specify a 'name' for the job!!!")

        if "template" not in kwargs:
            raise HpcError("please, specify a 'template' for the job!!!")

        if "project_name" in kwargs:
            self._logger.warning("do not use 'project_name' any more, just use 'project' instead!")
            project = kwargs.pop('project_name')[:80]
        else:
            project = kwargs["project"][:80]
        spid = validate_project(project)
        if not self._job_sim and not isinstance(spid, int):
            # also activate in module_tests/test_sched/test_job.py:53
            # raise HpcError("SPARCS responded with: {}, please, contact your data lifecycle manager!".format(spid))
            self._logger.error("SPARCS responded with: %s, please, contact your data lifecycle manager!", spid)
            spid = 0
        else:
            self._logger.info("SPARCS ID = %s", str(spid))

        if "sockets" in kwargs and "mem_max" not in kwargs:
            kwargs["mem_max"] = pvs.MIN_MEM_FREE * kwargs["sockets"] * 1.5

        if environ.get("BUILD_URL"):
            self._logger.info('build on Jenkins %s by %s (%s)',
                              environ.get("BUILD_URL"), environ.get("BUILD_USER"), environ.get("BUILD_USER_ID"))

        self._venv, self._popts = kwargs.pop("venv", None), kwargs.pop("popts", "")
        self._venv_sys = kwargs.pop("venv_sys", True)
        if self._venv:
            if kwargs["pyexe"] == PY_2_EXE or PY2 and kwargs["pyexe"] is None:
                raise HpcError("'venv' is not supported on Python 2!")
            if isinstance(self._venv, list):
                self._venv = linesep.join(self._venv)
            else:
                try:
                    with open(self._venv) as fp:
                        self._venv = fp.read()
                except Exception:
                    raise HpcError("seems we cannot read the venv file!")

        self.linux = str(kwargs["pyexe"]).startswith(LIN_EXE)

        defprio = JobPriority.Highest if str(kwargs["template"]).lower() in ["short_test", "Admin"] \
            else JobPriority.Lowest
        kwargs["priority"] = JobPriority(kwargs.pop('priority', defprio))

        unit = kwargs.pop("unit_type", None)
        if unit:
            self._logger.warning("please, use 'unit' instead of 'unit_type' in future!")
        else:
            unit = JobUnitType(kwargs.pop("unit", JobUnitType.Socket))

        add = kwargs.pop('add_exit_codes', [])
        if not isinstance(add, list):
            add = [add]
        unfailing = list(set([ERR_OK] + kwargs.pop('exit_codes', UNFAILING_EXITCODES) + add))
        with HpcPassword() as hset:
            restsched = kwargs.pop("restsched", osname != 'nt' or hset[UID_NAME] is not None)

        if not isinstance(kwargs.get("bsig_ext", []), list):
            raise HpcError("bsig_ext option must be a list!")

        self._scheduler = Scheduler(head_node, name=name, sim=self._job_sim,
                                    logger=self._logger, linux=self.linux, join=self.join, unit=unit,
                                    version=VERSION, priority=kwargs.pop("priority"), template=kwargs["template"],
                                    venv=bool(self._venv), exe=kwargs.get("pyexe", sys.executable),
                                    exit_codes=unfailing, restsched=restsched, xargs=kwargs)
        self._usr_log = get_logger('job {}:'.format(self._scheduler.jobid), loggers, level=self.loglevel)
        self._logger.info("%s's job arguments: user=%s, %s", name, UID_NAME,
                          ", ".join(["{}={!s}".format(k, v) for k, v in kwargs.items()]))
        self._log_info()
        self._portal_link = "{}/job/{}/{}" \
            .format(HPC_STORAGE_MAP[self._scheduler.head_node][5], self.head_node, self.jobid)

        self.sep = "/" if self.linux else "\\"
        # .format("" if not self._venv else "%VIRTUAL_ENV%\\Scripts\\")
        self.starter = "{}hpc{}starter.py".format("./" if self.linux else "python.exe -u ", self.sep)
        # self.starter = ("./" if self.linux else "python.exe -u ") + self.join("hpc", "starter.py")
        if kwargs["starter_opts"]:
            self.starter += " " + kwargs["starter_opts"]

        self.records = []
        self.taskmeas = defaultdict(lambda: 0)
        self._sweep = kwargs.get("sweep_task", True)

        # self._scheduler.update(**kwargs)

        self._env_data = {"headnode": self._scheduler.head_node, "jname": name, "jobid": self._scheduler.jobid,
                          "tasks": self.taskmeas, "project": project, "template": kwargs["template"], "spid": spid,
                          "submitstart": datetime.utcnow(), "records": self.records, "logger": self._streamer}

        self._xcmds = [[], []]
        self._jrelcmd, self._jprecmd, self._nrelcmd, self._nprecmd = [], [], [], []
        for nm, func in (["precmd", self.nodeprecmd], ["relcmd", self.noderelcmd],):
            for cmd in kwargs.pop(nm, []):
                func(cmd)

        self._skipon = kwargs.get('skipon', SKIP_EXITCODES)
        self._runas = kwargs.get("runas", UID_NAME)
        self._dbase = None
        self.changes = []
        self.mts_zips = []

        self._logger.info("configuring job %d", self.jobid, extra={"color": "green"})

        self._db_env = EnvData(self.base_db)

        self._prepare_hpc(self._job_sim or ((self._scheduler.head_node == DEV_HEAD or
                                             LOGINNAME in DEVS) and kwargs.get("copy_hpc", False)))

        # create local DB with all needed entries for tasks and subtasks
        self.env = JobDict(mode='w', jobid=self.jobid, name=self._scheduler.name, head=self._scheduler.head_node,
                           unit=int(unit), errorlevel=self.errorlevel, skipon=self._skipon, unfailing=unfailing,
                           bsig_check=kwargs.get(BSIG_CHK, True), mail=self._scheduler.mail,
                           wdog_log=kwargs.get("wdog_log", False),
                           **{k: kwargs[k] for k in self.__opt_args__ if k in kwargs})
        self._submitted = False

        self._taskfactory = self._taskfactory_mts = self._subtaskfactory = None

    def __str__(self):
        """self repr"""
        return '<{} head="{}", id="{!s}">'.format(self.__class__.__name__, self._scheduler.head_node, self.jobid)

    def __enter__(self):
        """provide with statement support"""
        self._enter = True
        return self

    def __exit__(self, etype, exval, _):  # pylint: disable=R0912,R1260
        """
        on with cleanup, we just submit the job

        :param `Exception` etype: if set skip the final submit during exiting Job instance
        :param `str` exval: exception message to show in case of skipping the exit
        """
        if etype is not None:
            self.cancel(exval)
            return

        if self._cancel:
            return

        try:
            self._scheduler.check_template()
        except HpcError as ex:
            self._scheduler.cancel_job(getattr(ex, "message", str(ex)))
            raise

        if not self._scheduler.name:
            raise HpcError("without a 'name', job is invalid!")

        env = {k: v for k, v in iteritems(environ) if k.startswith("HPC_")}
        net_path = self._scheduler.net_job_path
        if self.linux:
            for i, v in enumerate(HPC_SHARES["win32"]):
                # if self.head_node == AZR_HEAD and i < 8:
                #     continue
                if net_path.startswith(v):
                    net_path = self.join(HPC_SHARES["linux"][i], "hpc",
                                         basename(dirname(net_path)), basename(net_path))
                    break
            env.update({"CLIENT_IN_PATH": self._scheduler.client_in_path, "JOB_NET_PATH": net_path})
        else:
            env.update({"CLIENT_IN_PATH": linux2win(self._scheduler.client_in_path),
                        "JOB_NET_PATH": linux2win(self._scheduler.net_job_path)})
        self._scheduler.update(env=env)

        self._logger.info("writing environment data")

        if self.changes:
            self._env_data["changes"] = StringIO("\n".join(self.changes))

        self.env.prios = self.base_db("SELECT EXITCODE, PRIO, DESCR FROM HPC_EXITCODES "  # pylint: disable=E1102
                                      "WHERE EXITCODE >= 0")
        self.env.close(join(self._scheduler.net_in_path, "hpc", "job.json"))

        self._submitted = self._submit()
        self._write_test_bat()

        if self._dbase is not None:
            self._dbase.close()

    def __setattr__(self, key, value):
        """set a value, either to provided xml slot or internal variable, use on your own risk!"""
        if key in self.__xml_slots__:
            if self._submitted:
                raise HpcError("please, set any attribute before submission!")

            setattr(self._scheduler, key, value)
        else:
            super(Job, self).__setattr__(key, value)

    def __getattr__(self, key):
        """
        get any missing attribute

        :param str key: name of attribute
        :return: value of attribute
        :rtype: object
        """
        if key in self.__xml_slots__:
            return getattr(self._scheduler, key)

        def method_missing(*args, **_):
            if key in self.__deprecated__:
                self._logger.warning("method '%s' is deprecated, please use init param '%s' instead!!!",
                                     key, self.__deprecated__[key])

            return setattr(self._scheduler, self.__deprecated__[key], args[0])

        return method_missing

    def __len__(self):
        """:return int: number of tasks"""
        return len(self._scheduler)

    def join(self, *args):
        """
        join arguments

        :param list args: join those with destination separator
        :return: path join
        :rtype: str
        """
        return self.sep.join(args)

    @deprecated("please, use initparam 'name' in future!")
    def create(self, job_name):
        """remove me 2011: compat: create"""
        self._scheduler.name = job_name
        return self.job_folder

    def submit(self):
        """be compatible to hpc_one"""
        if self._enter:
            raise HpcError("with 'with' statements you shouldn't use submit method!")
        self.__exit__(None, None, None)

    def cancel(self, msg="canceled on purpose"):
        """cancel the already submitted job"""
        if msg:
            print("Exception:\n{!s}".format(msg))
        if self._scheduler is not None:
            try:
                self._scheduler.cancel_job(msg)
                self._cancel = True
            except Exception:
                pass

    @property
    def jobid(self):
        """:return int: the id of job"""
        return self._scheduler.jobid

    @property
    def job_name(self):
        """:return str: name of job"""
        return self._scheduler.name

    @property
    def job_folder(self):
        """:return str: folder of job on hpc share"""
        return self._scheduler.net_job_path

    @property
    def client_folder(self):
        """:return str: folder of job on client"""
        return dirname(self._scheduler.client_in_path)

    @property
    def portal_link(self):
        """:return str: portal link"""
        return self._portal_link

    @property
    def head_node(self):
        """:return str: head node name"""
        return self._scheduler.head_node

    @property
    def sched(self):
        """:return `Scheduler`: scheduler instance"""
        return self._scheduler

    @property
    def base_db(self):
        """:return `BaseDb`: HPC DB connection"""
        if self._dbase is None:
            if self._job_sim:
                self._dbase = BaseDB(create_sqlite(join(self._scheduler.net_in_path, "hpc.sqlite")))
            else:
                self._dbase = BaseDB(HPC_STORAGE_MAP[self._scheduler.head_node][3])

        return self._dbase

    @property
    def job_sim(self):
        """:return bool: wether it's sim or real"""
        return self._job_sim

    @property
    def logger(self):
        """:return submit logger"""
        return self._usr_log

    @property
    def precmd(self):
        """:return preparation command"""
        return self._xcmds[0]

    @precmd.setter
    def precmd(self, value):
        """:param str value: set preparation command"""
        self._logger.warning("deprecated: prefer using the nodeprecmd() method!")
        self._xcmds[0] = value

    @property
    def relcmd(self):
        """:return release command"""
        return self._xcmds[1]

    @relcmd.setter
    def relcmd(self, value):
        """:param str value: set release command"""
        self._logger.warning("deprecated: prefer using the noderelcmd() method!")
        self._xcmds[1] = value

    def nodeprecmd(self, cmds, **kwargs):
        """
        append a node prepare command to be done on first node prepare

        :param str cmds: command (plus arguments) to be executed
        :param dict kwargs: arguments for cmds to used, e.g. cwd, ...
        """
        self._nprecmd.append([cmds, kwargs])

    def noderelcmd(self, cmds, **kwargs):
        """
        append a node release command to be done on last node release

        :param str cmds: command (plus arguments) to be executed
        :param dict kwargs: arguments for cmds to used, e.g. cwd, ...
        """
        self._nrelcmd.append([cmds, kwargs])
        self._logger.info("added release cmd(s): '%s'", str(cmds))

    def jobprecmd(self, cmds, **kwargs):
        """
        append a job prepare command to be done on the very first prepare

        :param str cmds: command (plus arguments) to be executed
        :param dict kwargs: arguments for cmds to used, e.g. cwd, ...
        """
        self._jprecmd.append([cmds, kwargs])

    def jobrelcmd(self, cmds, **kwargs):
        """
        append a job release command to be done on the very last node release

        :param str cmds: command (plus arguments) to be executed
        :param dict kwargs: arguments for cmds to used, e.g. cwd, ...
        """
        self._jrelcmd.append([cmds, kwargs])
        self._logger.info("added release cmd(s): '%s'", str(cmds))

    def _log_info(self):
        """log some info"""
        self._logger.info("connected to scheduler %s", self._scheduler.head_node, extra={"color": "green"})
        self._logger.info("we'll use %s to execute on cluster", self._scheduler.exe)
        self._logger.info("job's path is %s", self._scheduler.net_job_path)

        self._logger.info("trace back to here:")
        for cnt, frame in enumerate(extract_stack()):
            if frame[0] == __file__:
                break
            if not search(r"(\\|/)(pydev|pycharm)(\\|/)|C:\\LegacyApp", frame[0]):
                self._logger.info("%d: %s, line %d", cnt, frame[0], frame[1])

    def _prepare_hpc(self, real_copy):
        """copy the whole hpc package into the input folder for the job"""
        hpath = join(self._scheduler.net_in_path, 'hpc')
        if real_copy:  # copy local hpc with just py / pyc files
            self._logger.info("copying HPC package")
            ign = lambda s, k: {i for i in k if '.' in i and splitext(i)[-1] != ".py" or i in ("__pycache__", "docs")}
            Robocopy(ignore=ign, verbose=0, stat=False).copy(dirname(dirname(abspath(__file__))), hpath)
            open(join(self._scheduler.net_in_path, 'HPC_V{}'.format(self._hver)), 'w').close()
            self._logger.info("hpc package copy finished")
        else:
            makedirs(hpath)
            open(join(hpath, "__init__.py"), 'w').close()

        try:
            makedirs(join(self._scheduler.net_in_path, 'bpl'))
        except Exception:
            pass

    def _write_test_bat(self):
        """write test.bat to input folder"""
        if self.linux:
            cmds = ['#!/bin/bash', 'if [ $# -eq 1 ]; then', '  task=$1', 'else', '  task=1', 'fi',
                    'export CCP_SCHEDULER="{}"'.format(self.head_node),
                    'export CCP_JOBID="{}"'.format(self.jobid), 'export CCP_TASKID="$task"',
                    'cp {}/HPC_Python/{} ./hpc -r'
                    .format(win2linux(dirname(self._scheduler.base_dir)), self._scheduler.hpcversion),
                    '{} -ot $task'.format(self.starter)]
            fname = "test"
        else:
            cmds = ['@echo off', 'if "%1" == "" (set task=1) else (set task=%1)',
                    'set CCP_SCHEDULER={}'.format(self.head_node), 'set CCP_JOBID={}'.format(self.jobid),
                    'set CCP_TASKID=%task%']
            if not self._job_sim:
                cmds.append('xcopy {}\\HPC_Python\\{} .\\hpc /S /I /Y /Q > NUL'
                            .format(dirname(self._scheduler.base_dir), self._scheduler.hpcversion))
            if self._venv:
                cmds.extend([self._nprecmd[-3][0], 'call .\\venv\\Scripts\\activate.bat',
                             self._nprecmd[-2][0], self._nprecmd[-1][0]])
            cmds.extend(['{} -ot %task%'.format(self.starter), 'pause'])
            fname = "test.bat"
        # folder = self._scheduler.client_in_path if self._job_sim else self._scheduler.net_in_path
        for fldr in [self._scheduler.net_in_path] + ([self._scheduler.client_in_path] if self._job_sim else []):
            with open(join(fldr, fname), 'w') as bfile:
                bfile.write(linesep.join(cmds))

    def _submit(self):  # pylint: disable=R0912,R1260
        """submit!"""
        if self._sweep:
            if self.linux:
                cmd, wdir = "/usr/local/bin/node.py prepare", None
            else:
                cmd, wdir = "python.exe -u node.py prepare", r"C:\LegacyApp\HPC"
            if self._venv:
                self._handle_venv(join(dirname(self._scheduler.base_dir), "HPC_submit", "job"))

            # finalize environment file
            jents = {"portal": HPC_STORAGE_MAP[self._scheduler.head_node][5]}
            if any(self._xcmds) or self._jrelcmd or self._jprecmd or self._nrelcmd or self._nprecmd:
                for tnm, cmds in zip(["npre", "nrel"], self._xcmds):
                    if cmds:
                        if not isinstance(cmds, list):
                            cmds = [cmds]
                        jents[tnm] = {"cmds": [[i, {}] for i in cmds]}

                for nm, cmds in (["jrel", self._jrelcmd], ["jpre", self._jprecmd],
                                 ["nrel", self._nrelcmd], ["npre", self._nprecmd],):
                    if cmds:
                        jents[nm] = {"cmds": cmds}

                with open(linux2win(join(self._scheduler.net_job_path, "1_Input", "hpc", "par.json")), "w") as fp:
                    dump(jents, fp, indent=2)

            if "npre" in jents or "jpre" in jents:
                runtime = self._scheduler.runtime
            else:
                runtime = SHORT_TEST_RUNTIME * 2

            self._scheduler.append_task(name="prepare", type=TaskType.NodePrep, sockets=1, resources=1,
                                        command_line=cmd, work_directory=wdir, stderr=None, runtime=runtime,
                                        envs={"TASKNAME": "prepare"})

            # create release task
            if self.linux:
                cmd, wdir = "/usr/local/bin/node.py release", None
            else:
                cmd, wdir = "python.exe -u node.py release", r"C:\LegacyApp\HPC"

            self._scheduler.append_task(name="release", type=TaskType.NodeRelease, sockets=1, resources=1,
                                        command_line=cmd, work_directory=wdir, stderr=None,
                                        runtime=MAX_SWEEP_RUNTIME if self._jrelcmd else STD_SWEEP_RUNTIME,
                                        envs={"TASKNAME": "release"})

        # update env vars in case we packed some
        if self.mts_zips:
            self._scheduler.update(env={"HPC_ZIPS": " ".join(self.mts_zips)})

        # self._forecast()
        self._env_data["taskcnt"] = len(self._scheduler) - (2 if self._sweep else 0)
        jid = self._update_db()[1]
        self._logger.info("committing now => %s", self.portal_link)
        try:
            self._scheduler.submit(self.priority, self._runas, self._dbase)
            self._update_db(jid)
            if len(self._scheduler) <= (2 if self._sweep else 0):
                self._logger.error("you don't have any tasks%s!", " besides prepare/release" if self._sweep else "")
                return False
            self._logger.info("total submission finished.")
            return True
        except Exception as ex:
            err = str(ex)
            err = err if err else "unknown error occurred!"
            self._logger.error(err)
            try:
                self._scheduler.cancel_job(err)
            except Exception:
                pass
            self._update_db(jid)
            return False
        # finally:
        #     self._scheduler.close()

    def _handle_venv(self, folder):
        """add extra xcmds for venv"""
        with open(join(folder, "{}_{}.txt".format(self.head_node, self.jobid)), "w") as fp:
            fp.write(self._venv)

        pybase = "{}\\venv\\Scripts\\python.exe -m".format(self._scheduler.client_in_path)
        if self._venv_sys:
            self.nodeprecmd("python.exe -m venv {} --system-site-packages"
                            .format(join(self._scheduler.client_in_path, "venv")))
            # self._xcmds[0].append("{} ensurepip".format(pybase))
            self.nodeprecmd("{} pip install -U pip setuptools wheel".format(pybase))
        else:
            self.nodeprecmd("python.exe -m venv {}".format(join(self._scheduler.client_in_path, "venv")))
            # self._xcmds[0].append("{} ensurepip".format(pybase))
            self.nodeprecmd(r"{} pip install --prefer-binary -U -r {}\hpc\HPC_Python\hpcreq_{}.txt"
                            .format(pybase, HPC_STORAGE_MAP[self._scheduler.head_node][1],
                                    SHORT_VER[self._scheduler.exe]))
        if self._popts:
            self._popts = " " + self._popts
        self.nodeprecmd("{} pip install -r {}{}".format(pybase, fp.name, self._popts))

    def _update_db(self, jobid=None):
        """
        create a fallback database

        :return int: ident of job
        """
        if jobid is None:
            return self._db_env.insert_job(**self._env_data)

        return self._db_env.update_job(jobid=jobid, logger=self._env_data["logger"], resource=self._scheduler.unit)

    def wait_until_finished(self, **kwargs):
        r"""
        wait until job finishes

        :keyword \**kwargs:
            * *timeout* (``int``): wait timeout [s]
        :return `JobState`: final state of job
        """
        return self._scheduler.wait_until_finished(**kwargs)

    @suppress_warnings
    def _forecast(self):
        """calc job forecast"""
        if PY2:
            self._logger.info("running under Python2: no forecast available!")
            return
        if self._job_sim:
            self._logger.info("running locally: no forecast available!")
            return
        if not self.taskmeas:
            self._logger.info("no measurements mapped, no forecast available!")
            return

        try:
            ncst = dloads(zdeco(self.base_db("SELECT NETCAST FROM HPC_NODE "  # pylint: disable=E1102
                                             "WHERE NODENAME = :head",
                                             head=self._scheduler.head_node)[0][0].read()), encoding='bytes')
            regr = ncst.get(b"job_regs", {}).get(self._scheduler.project)
            if regr:
                eta = sum([regr.predict([i.tolist()]) for i in self.taskmeas.values() if i.all()])
                if not isinstance(eta, int):
                    eta = int(eta[0])
                if eta == 0:
                    self.logger.info("job estimation is zero, seems no measurements are used.")
                else:
                    self.logger.info("job estimation: {}s ({:02d}:{:02d}:{:02d})"
                                     .format(eta, eta // 3600, eta // 60 % 60, eta % 60))
            else:
                self.logger.info("job estimation for project '%s' not available (yet).", self._scheduler.project)
        except Exception as ex:
            self.logger.info("job estimation didn't work: %s (just ignore it)!", str(ex))

    def add_task(self, **kwargs):
        """add a task to job"""
        return Task(self, **kwargs)

    def task_factory(self, **kwargs):
        """create a taskfactory and return it, see :class:`hpc.TaskFactoy` for more information"""
        if self._taskfactory is None:
            self._taskfactory = TaskFactory(self, **kwargs)

        return self._taskfactory

    def create_task(self, *args, **kwargs):
        """create a task"""
        if self._taskfactory is None:
            self._taskfactory = TaskFactory(self, **kwargs)

        return self._taskfactory.create_task(*args)

    def task_factory_mts(self, **kwargs):
        """create a taskfactory and return it, see :class:`hpc.TaskFactoyMTS` for more information"""
        if self._taskfactory_mts is None:
            self._taskfactory_mts = TaskFactoryMTS(self, **kwargs)

        return self._taskfactory_mts

    def create_mts_task(self, *args, **kwargs):
        """create a task"""
        if self._taskfactory_mts is None:
            self._taskfactory_mts = TaskFactory(self, **kwargs)

        return self._taskfactory_mts.create_task(*args)

    def subtask_factory(self, **kwargs):
        """create a taskfactory and return it, see :class:`hpc.SubTaskFactoy` for more information"""
        if self._subtaskfactory is None:
            self._subtaskfactory = SubTaskFactory(self, **kwargs)
        return self._subtaskfactory
