#!/usr/bin/python3 -u
"""
starter.py
----------

Script to be used to start a CMD Line Application in a HPC task.

Features:
    - moving of task result and log data back to the server
    - app watcher checking if the application is idle
    - graceful exit of GUI applications on task cancellation
    - evaluation of MTS return code and check for crash-dumps
"""
# pylint: disable=C0302,R0912,R0915,R1260
# C0413,E1101,E0611,W0702,W1201,W1202
# - import Python Modules ----------------------------------------------------------------------------------------------
from __future__ import division, print_function
import sys
from os import makedirs, environ, unlink, stat, getcwd, chmod
from os.path import abspath, join, split, exists, dirname, basename, getsize, splitext
from stat import S_IEXEC
from argparse import ArgumentParser, RawDescriptionHelpFormatter, SUPPRESS
from datetime import datetime, timedelta
try:
    from packaging.version import Version
except ImportError:
    from distutils.version import LooseVersion as Version
from platform import architecture, python_version_tuple
from re import match, sub, compile as recomp
from shutil import rmtree
from socket import gethostname
from getpass import getuser
from tempfile import TemporaryFile, SpooledTemporaryFile
from time import time, mktime
from traceback import print_exc
from multiprocessing import Pool, Manager, cpu_count
from itertools import count
# from requests import post
from psutil import pid_exists, virtual_memory, cpu_percent, NoSuchProcess, disk_usage
from numpy import inf
from pytz import UTC
from six import iteritems, PY2
from simplejson import load

if PY2:
    range = xrange  # pylint: disable=W0622,C0103,E0602
    from subprocess import Popen, PIPE
    DEVNULL = PIPE
    NoSuchFile = IOError
    from types import StringTypes
    EPOCH = datetime(1970, 1, 1, 0, 0)
else:
    from subprocess import Popen, PIPE, DEVNULL  # pylint: disable=C0412
    NoSuchFile = FileNotFoundError
    StringTypes = (str,)

MSWIN = sys.platform == "win32"
if MSWIN:
    from signal import signal, SIGBREAK as SIG_END, SIGTERM, SIGINT, SIGSEGV
    from win32api import OpenProcess, CloseHandle, TerminateProcess
    from win32file import GetFileAttributesW, CopyFileEx
    from win32con import FILE_ATTRIBUTE_OFFLINE
    from ctypes import WinError
else:  # pragma: nocover
    from signal import signal, SIGHUP as SIG_END, SIGTERM, SIGINT, SIGSEGV  # pylint: disable=C0412

    class WinError(object):  # pylint: disable=R0903
        """overload for Linux"""

        def __init__(self, _):
            """do nothing"""

        @property
        def strerror(self):
            """no desc"""
            return "no description available"

# - import HPC modules -------------------------------------------------------------------------------------------------
HPC_FOLDER = abspath(join(dirname(__file__), r".."))
if HPC_FOLDER not in sys.path:
    sys.path.append(HPC_FOLDER)

from hpc import __version__
from hpc.core.app_utils import BackgroundProcess, HpcArgumentParser, ArgumentParserError, try_sleep, MonDataCollector, \
    WrapProc, replace_env_vars, LogTimer, file_version, timeit, CloudBlob, IO_CNT, PROC_TIME, \
    REPORT_WAIT_TIME_INITIAL, REPORT_WAIT_TIME_CYCLE, MAX_TIME_WATCH, EXIT_GRACE_TIME
from hpc.core.robocopy import Robocopy
from hpc.core.dicts import JobDict, DefDict, TOUT_DIR, TLOG_DIR, BSIG_CHK, WRAP_EXE, CNCL_CMD, USR_EXMAP, \
    NOTIFY_START, NOTIFY_STOP
from hpc.core.hpc_defs import JobUnitType
from hpc.core.tds import head_name, server_path, replace_server_path, resolve_ip, \
    HPC_STORAGE_MAP, LOC_HEAD_MAP, AZR_BLOB_STX, AZR_CONN_STR, AZR_ACC_KEYS
from hpc.core.path import linux2win, win2linux, on_tree_error
from hpc.core.convert import human_size
from hpc.core.logger import get_logger
from hpc.core.exitcodes import ExitCodes
from hpc.core import proc_vals as pvs
from hpc.rdb.env_data import EnvData, daemon_cmd
from hpc.mts.mts_check import mts_log_check, check_mts_ini
from hpc.mts.bsig_check import bsig_check
from hpc.core.error import HpcError, ERR_OK, EXIT_MAP, MTS_LOOKUP_EXITCODE, MTS_LOOKUP_EXITMSG, ERR_APPLICATION_HANG, \
    ERR_INFRASTRUCTURE_FAILED_TO_COPY_DATA, ERR_HPC_APPLICATION_NOT_LOCAL, ERR_HPC_APPLICATION_NOT_FOUND, \
    ERR_APPLICATION_CPU_IDLE, ERR_APPLICATION_IO_IDLE, ERR_APPLICATION_PRN_IDLE, ERR_APPLICATION_TIMEOUT, \
    ERR_MTS_OLD_DLL_DETECTED, ERR_HPC_WRONG_ARG, ERR_HPC_SCRIPT_MALFUNCTION, ERR_HPC_DATABASE, \
    ERR_INFRASTRUCTURE_UNSPECIFIC_ERROR_FOUND, ERR_INFRASTRUCTURE_RECORDING_UNAVAILABLE, ERR_INFRASTRUCTURE_GPU_EXEC, \
    ERR_MTS_MEM_LEAK_FOUND, ERR_INFRASTRUCTURE_RECORDING_ARCHIVED, ERR_MTS_UNSPECIFIED_ERROR_FOUND, \
    ERR_INFRASTRUCTURE_FAILED_TO_CREATE_DATA, ERR_HPC_INTERNAL_ERROR, ERR_HPC_USER_CANCEL_TASK_DETECTED, \
    ERR_APPLICATION_UNSPECIFIED_ERROR_FOUND, ERR_APPLICATION_LOW_MEM, ERR_APPLICATION_LOW_CPU, \
    ERR_APPLICATION_HIGH_MEM, ERR_APPLICATION_FATAL, ERR_PYTHON_UNSPECIFIED_ERROR_FOUND, \
    ERR_HPC_UNSPECIFIED_ERROR_FOUND, ERR_APPLICATION_WRAPPER, ERR_HPC_PID_INVALID, ERR_APP_ERR_NETWORK_UNAVAILABLE, \
    ERR_HPC_LOW_DISK_SPACE

# - defines ------------------------------------------------------------------------------------------------------------
D_DRIVE = "D:" if MSWIN else "/var/hpc"

DEBUG_ARGS = ["mts_exe", "mem_max"]

SIGNAMES = DefDict("unknown", {int(SIG_END): "SIGBREAK" if MSWIN else "SIGHUB", int(SIGTERM): "SIGTERM",
                               int(SIGINT): "SIGINT", int(SIGSEGV): "SIGSEGV"})

OTHER = "OTHER"

FILE_CHECKS = [["\\sys\\rawrecfilereader.dll", "2.6.260.31"],
               ["\\cfg\\..\\dll\\sim\\sim_vfb.dll", "5.83.0.3264"],
               ["\\cfg\\..\\dll\\algo\\sim\\sim_vfb.dll", "5.83.0.3264"],
               ["\\cfg\\..\\dll\\sim\\sim_vfb_x64.dll", "5.83.0.3264"],
               ["\\cfg\\..\\dll\\algo\\sim\\sim_vfb_x64.dll", "5.83.0.3264"]]


# - starter class ------------------------------------------------------------------------------------------------------
class AppStarter(object):  # pylint: disable=R0902
    """
    Application Handler / HPC executor for:

    - starting the applications,
    - copying results from the apps back to the server,
    - starting the HPC watchdog (check cpu and io usage),
    - interrupt handling like CTRL+C (Cancel Command)
    """

    def __init__(self, **kwargs):
        """initialize the executor"""
        self._wargs = kwargs.get("wargs", {})
        if kwargs.get("fastwatch", False):
            self._wargs.update({"wdog_init": 2, "wdog_loop": 2})
        self.streamer = SpooledTemporaryFile(max_size=67108864, mode='w+', prefix='hpc_', suffix=".log")
        self._streams = [[self.streamer, True]]
        if head_name(kwargs.get('sched')) is None or kwargs.get("stdout"):
            self._streams.append([sys.stdout, False])

        self._logger = get_logger('HPC exec:', self._streams)
        self._proc, self._cpu_time, self._all_cpu_time = None, 0, 0
        self._env = {k: str(v) for k, v in iteritems(environ)}
        self._app_watch_ret, self._app_watch_io = ERR_OK, 0
        self._wdog_log = {}
        self._errmons = []
        self._proclog = None
        self.taskfolder = self.datafolder = self.tempfolder = ''
        self._local_rec, self._cloud_rec = [], None
        self.taskname = ''
        self.networkpath = None
        self.task_id = ''
        self.int_taskid = None
        self._envhandler = None

        self._cwd = kwargs["cwd"]
        self._jobdb = JobDict(fp=join(self._cwd, "hpc", "job.json"))
        self.head_node = (head_name(OTHER) if kwargs.get('sched') is None
                          else kwargs.get('sched')).split('.')[0].upper()
        self._exitcode = ExitCodes(prios=self._jobdb.prios, unfailing=self._jobdb.unfailing,
                                   ignore_codes=getattr(self._jobdb, "ignore_codes", []))
        self._subexit = ExitCodes(self._exitcode)
        if self._jobdb.jobid != int(environ.get("CCP_JOBID", self._jobdb.jobid)):
            self._logger.error("discrepancy on job's Ident!")
            self._exitcode(ERR_HPC_PID_INVALID)
        self.jobname, self.jobid = "{}_{}".format(self._jobdb.jobid, self._jobdb.name), str(self._jobdb.jobid)
        # self._sqlitedb = join(self._cwd, "hpc.sqlite")
        # try:
        #     self._exitcode = ExitCodes(db=self._sqlitedb, unfailing=self._jobdb.unfailing,
        #                                ignore_codes=getattr(self._jobdb, "ignore_codes", []))
        # except Exception:  # seems backup sqlite cannot be used
        #     self._sqlitedb = None
        #     self._exitcode = ExitCodes(unfailing=self._jobdb.unfailing,
        #                                ignore_codes=getattr(self._jobdb, "ignore_codes", []))

        if head_name():
            self._dbase = kwargs.pop('db', HPC_STORAGE_MAP[head_name()][3])
        else:
            self._dbase = join(self._cwd, "hpc.sqlite")

        self._taskpid = 0
        self._subtask = None
        self._recording = None
        self._rec_ip = None
        self._is_mts = self._is_py = self._is_docker, self._docker_err = False, ERR_OK
        self._docker_msgs = {recomp("stderr: nvidia-container-cli: initialization error: nvml "
                                    "error: driver/library version mismatch: unknown"):
                                 (self._docker_exit, ERR_INFRASTRUCTURE_GPU_EXEC,)}
        self._mts_cnt = self._mts_check_cnt = 0
        self._terminated = 0
        # self._verbose = 0
        for i in DEBUG_ARGS:
            if i in kwargs:
                self._wargs[i] = kwargs[i]

    def __enter__(self):
        """just self"""
        return self

    def __exit__(self, *args):
        """clean up 4 testing purposes"""
        if not self.streamer.closed:
            for i in self._streams[:]:
                self._logger.removeHandler(i[0])

            self.streamer.close()

    clear = __exit__

    def _create_std_items(self, part):
        """
        create needed standard folders and files for the task to run being tracked

        :param str part: this part is either start or stop
        :return: success status
        :rtype: bool
        """
        if not self.taskfolder:
            # create standard folders which are available for every application
            self.taskfolder = join(dirname(self._cwd), '2_Output', self.taskname)

            # check if task folder exist
            if exists(self.taskfolder):  # pragma: no cover
                rmtree(self.taskfolder)

            self._logger.info('-' * 112)
            self._logger.info('creating local task folder: %s', self.taskfolder)
            self._logger.info('-' * 112)

            try:
                # create output folder for log files
                makedirs(join(self.taskfolder, 'log'))

                # create output folder for data files
                self.datafolder = join(self.taskfolder, 'data')
                makedirs(self.datafolder)
                self.tempfolder = join(self.taskfolder, 'tmp')
                makedirs(self.tempfolder)
            except Exception as ex:
                self._logger.error("unable to create output folders: %s", str(ex))
                self._exitcode(ERR_INFRASTRUCTURE_FAILED_TO_CREATE_DATA)
                return False

        netp, errmsgs = join(self.networkpath, '2_Output', self.taskname), []
        for fldr in (netp, environ.get("TMP"),):
            try:
                makedirs(fldr)
            except Exception as ex:
                errmsgs.append(str(ex))
        try:
            fname = join(netp, "%s_%s" % (datetime.utcnow().strftime('%Y-%m-%d_%H_%M_%S'), part))
            open(fname, "w").close()
            self._logger.info("created file %s successfully", fname)
            return True
        except Exception as ex:  # pragma: no cover
            self._logger.error("couldn't create %s, due to %s!", fname, str(ex))
            for msg in errmsgs:
                self._logger.error("addon message: %s", msg)
            self._exitcode(ERR_INFRASTRUCTURE_FAILED_TO_CREATE_DATA)

        return False

    def _create_procdumps(self):
        """create a procdump"""
        if not MSWIN:  # pragma: nocover
            return False

        if self._proclog is None:
            self._proclog = get_logger('ProcDump:', self._streams)

        avail = True  # workaround for missing procdump rollout
        for i in range(3):
            start = time()
            if avail:
                self._logger.info("starting dump %d...", i + 1)
                dmp = BackgroundProcess([r"C:\\LegacyApp\\HpcApps\\procdump.exe", "-accepteula", "-ma",
                                         str(self._taskpid),
                                         join(self.taskfolder, 'log', 'mts_{}_{}.dmp'
                                              .format(self._taskpid, datetime.utcnow().strftime('%Y-%m-%d_%H.%M.%S')))],
                                        None, self._proclog.warning, logger=self._proclog,
                                        filter=recomp(r".*Dump\s\d\s.*"))
                if dmp.app is None:
                    self._proclog.error("no ProcDump.exe available!")
                    avail = False
                else:
                    for _ in range(128):
                        if not dmp.running:
                            break
                        try_sleep(0.333)
                    else:
                        self._proclog.warning("proc dump didn't finish, killing it now...")
                        dmp.close()

            while (time() - start) < 5.:
                try_sleep(0.333)
                if not self._proc.running:
                    break

        return avail

    def _create_cdb_info(self):
        """create debug info"""
        if not MSWIN:  # pragma: nocover
            return

        logfn = "mts_cdb_{}_{}.log".format(self._taskpid, datetime.utcnow().strftime('%Y-%m-%d_%H.%M.%S'))
        self._logger.warning("creating cdb log: ....\\log\\%s", logfn)
        cdb = Popen(r'C:\LegacyApp\HpcApps\cdb.exe -p {} -c "~*k;.detach;q" -logo {}'
                    .format(self._taskpid, join(self.taskfolder, 'log', logfn)), stdout=DEVNULL, stderr=DEVNULL)
        for _ in range(32):
            try_sleep(1.)
            if PY2:
                cdb.stdout.read()
            if cdb.poll() is not None:
                break
        else:
            self._logger.error("cdb log takes too long, quitting it!")
            cdb.terminate()

    def _mail_user(self, send, state):
        """mail user about task status"""
        if not send or not self._jobdb.mail:
            return

        res = daemon_cmd("mail;{0};Your task {2}.{3} is now in the '{5}' state;"
                         "Notification from cluster {1}: Task Id: {2}.{3} Name: {4} State: {5}"
                         .format(self._jobdb.mail.split('@')[0], self.head_node, self.jobid, self.task_id,
                                 self.taskname, state), self.head_node)

        log, msg = (self._logger.warning, "failed",) if res == "ERR" else (self._logger.info, "sent",)
        log("notification email to %s %s.", self._jobdb.mail, msg)

    def _on_rm_error(self, func, path, _):
        """
        If the error is due to an access error (read only file)
        it attempts to add write permission and then retries.

        If the error is for another reason it re-raises the error.

        Usage : ``shutil.rmtree(path, onerror=onerror)``
        """
        if not exists(path):  # pragma: no cover
            self._logger.info("folder '%s' does not exist.", path)
        else:
            on_tree_error(func, path, _)

    def _copy_delete_data(self):
        """move data files from local task directory to network location."""
        if self.tempfolder == '':  # pragma: no cover
            return

        # first delete tmp folder to prevent copying it
        self._logger.info('deleting temp folder: %s', self.tempfolder)
        rmtree(self.tempfolder, onerror=self._on_rm_error)

        self._logger.info('moving data results back...')
        # move results to network from d:\\data\\%JobName%\\2_Output\\%TaskName%\\data
        src = self.datafolder

        # sync to primary job's output folder
        robo = Robocopy(stdout=self._logger.info, stderr=self._logger.error, verbose=2,
                        wait=getattr(self._jobdb, "robo_wait", 12), retry=getattr(self._jobdb, "robo_retry", 3),
                        comp_pat="*.dmp", errmon="errmon_*.xlog" if self._exitcode.state == "Failed" else None,
                        stat=False)
        if self._jobdb.orig_loc:
            # a masterjob is copied back to \\<orig_server>\hpc\HPC_output\<masterid>_<jobname>\<exec_head>
            # instead of                    \\<exec_server>\hpc\<exec_head>\<jobid>_<jobname>\2_Output
            orig_head = LOC_HEAD_MAP.get(self._jobdb.orig_loc, ['OTHER'])[0]
            outfldr = abspath(join(server_path(orig_head), '..', 'HPC_output',
                                   "_".join([self._jobdb.masterid, self._jobdb.name])))
            self._robocopy(robo, src, join(outfldr, '_data'), join(outfldr, head_name(OTHER), self.taskname))
        else:
            ofldr = join(self.networkpath, '2_Output')
            outdir = join(ofldr, self.taskname if getattr(self._jobdb, "task_out", False) else '_data')
            outdir = self._jobdb.task(self.task_id, TOUT_DIR, outdir)
            logdir = self._jobdb.task(self.task_id, TLOG_DIR, join(ofldr, self.taskname))
            self._robocopy(robo, src, outdir, logdir)

        self._errmons = [sub(r"\\\\\?\\UNC\\(.*)", r"\\\\\1", i) for i in robo.errmons]

    def _robocopy(self, robo, src, dst, tsk):
        """copy the stuff"""
        error, overwrote = robo.move(src, dst)[2:4]

        # filter return code of robocopy after real error
        if error > 0:  # pragma: no cover
            self._logger.error('robocopy finished with %d errors', error)
            self._exitcode(ERR_INFRASTRUCTURE_FAILED_TO_COPY_DATA)
        elif overwrote > 0:
            self._logger.error('robocopy overwrote %d files on output data folder', overwrote)
            # uncomment when algo Jenkins was fixed
            # self._exitcode(ERR_INFRASTRUCTURE_DATA_OUTPUT_OVERWRITE)

        # copy MTS log folder back to network
        self._logger.info('move other folders back to network...')
        error = robo.move(self.taskfolder, tsk)[2]
        self._logger.info('moved %s in summary', human_size(robo.bytes_written))
        if error > 0:
            self._exitcode(ERR_INFRASTRUCTURE_FAILED_TO_COPY_DATA)

    def _docker_exit(self, code):
        """support the docker specific exitcode from message parsing"""
        self._docker_err = code

    def cancel_handler(self, signum=None, frame=None):
        """we're getting canceled"""
        if self._terminated:
            if signum:
                self._logger.warning("already terminating (%d), repeated signal: %d", self._terminated, signum)
                if frame:
                    self._logger.warning("frame = %s", frame.f_code.co_name)
                self._terminated += 1
            return

        if signum is not None:
            self._terminated += 1
            self._logger.error("=" * 112)
            self._logger.error("signal %d=%s received!", signum, SIGNAMES[signum])
            self._logger.error("=" * 112)
            try:
                if signum == SIGSEGV:
                    self._exitcode(ERR_HPC_UNSPECIFIED_ERROR_FOUND)
                else:
                    self._exitcode(ERR_HPC_USER_CANCEL_TASK_DETECTED)
            except Exception:  # can only happen when not loaded yet...
                pass
            # under Windows, SIGINT does not work
            if self._proc:
                self._proc.close()

        # terminate app process if running
        if self._proc is None or self._proc.app is None:
            return
        if self._proc.running or pid_exists(self._taskpid):  # pylint: disable=R1702
            procdump = self._is_mts and getattr(self._jobdb, "procdump", False) \
                       and self._app_watch_ret in (ERR_APPLICATION_CPU_IDLE, ERR_APPLICATION_IO_IDLE,
                                                   ERR_APPLICATION_TIMEOUT)
            avail = True
            if signum is None:
                if procdump:  # we need to terminate as timeout occurred (e.g. -301) and create a dump
                    self._create_cdb_info()
                    avail = self._create_procdumps()

                if self._proc.running:
                    try:
                        self._proc.close(False)
                    except Exception:  # pragma: no cover
                        self._logger.error("Exception on closing program!")

            if self._proc.running:
                self._logger.info("waiting a bit for client to close down...")

                if procdump and avail and signum is None:
                    self._create_procdumps()

                if self._proc.wait(EXIT_GRACE_TIME):
                    self._logger.warning("trying to terminate now...")
                    try:
                        handle = OpenProcess(1, False, self._taskpid)
                        TerminateProcess(handle, ERR_APPLICATION_HANG)
                        CloseHandle(handle)
                        self._proc.wait(EXIT_GRACE_TIME)
                        self._logger.info("shutdown completed.")
                        self._subexit(ERR_APPLICATION_HANG)
                        try_sleep(3)
                    except Exception:  # pragma: no cover
                        self._logger.error("termination failed!")
            else:
                self._logger.info("shutdown completed within grace time.")

        if self._proc.exitcode is None:  # pragma: no cover
            self._logger.warning("process didn't exit yet, this shouldn't happen!!")
            self._subexit(ERR_HPC_SCRIPT_MALFUNCTION)

        elif self._is_mts and self._proc.exitcode not in [0, 1] or not self._is_mts and self._proc.exitcode != 0:
            self._logger.warning('process exit code: {} (hex: {:08x})'
                                 .format(self._proc.exitcode, self._proc.exitcode & 0xffffffff))
        else:
            self._logger.info("exit successful (exit code: %d).", self._proc.exitcode)

    def _start_process(self, arglist, cwd, wraps, **kwargs):
        """
        start application in a separate process.

        :param list arglist: complete commandline call to start the new process
        :param str cwd:      current working directory
        :param list wraps:   number of wrappers
        :param dict kwargs:  pass through for BackgroundProcess init

        :return: rec on local disk
        :rtype: bool
        :raises HpcError: if azure libs are not installed
        """
        localrec = False
        exe = arglist[0].split()[0].lower() if len(arglist) == 1 else arglist[0].lower()
        base = basename(exe)
        prefix = "[0] " if wraps > 0 else ""

        # check if application to start is local.
        if exe[0:2] == '\\\\':
            self._subexit(ERR_HPC_APPLICATION_NOT_LOCAL)
            self._logger.error("Code: %d: %s.", self._subexit.error, self._subexit.desc)

        # prepare command line
        self._is_mts, self._is_py, self._is_docker, pargs = False, False, False, dict(kwargs)
        app = None
        if base.startswith("python"):
            em = False
            for i in (arglist[0].split() if len(arglist) == 1 else arglist)[1:]:
                if not em and i == "-m":
                    em = True
                    continue
                if em:
                    app = i.split('.')[-1]
                    logger = get_logger(app + ':', self._streams, prefix)
                    break
                if i.endswith(".py"):
                    app = splitext(basename(i))[0]
                    logger = get_logger(app + ':', self._streams, prefix)
                    break
            self._is_py = True
            if MSWIN and isinstance(arglist, list) and environ.get("VIRTUAL_ENV"):
                arglist[0] = "{}\\Scripts\\python.exe".format(environ["VIRTUAL_ENV"])
        elif base in ("measapp.exe", "sil_lite.exe",):
            app = "MTS" if base[0].lower() == 'm' else "SilLite"
            logger = get_logger(app + ':', self._streams, prefix)  # , color="olive")
            pargs.update({"filter": recomp(r"'.*ExtMeasurePointer\.__del__'|.*Closing\sconnection.*"), "inverse": True})
            self._is_mts = True
            self._mts_cnt += 1
        else:
            if base in ["docker", "docker.exe", "docker.bat"]:  # bat is inside for testing purposes
                opts = ArgumentParser()
                opts.add_argument("--name", type=str, help="name of docker")
                try:
                    self._is_docker = opts.parse_known_args(arglist[0].split())[0].name
                    pargs["callback"] = self._docker_msgs
                except Exception:  # ignore index/parsing errors
                    self._logger.warning("unable to find name of docker, or none given.")

            app = splitext(base)[0] if '.' in base else base
            logger = get_logger(app + ':', self._streams, prefix)

        if app is None:
            logger = get_logger("foobar:", self._streams, prefix)
        else:
            self._subtask.app = app

        if MSWIN and self._subtask.get("local_rec", False) and self._is_mts:  # pylint: disable=R1702
            # with NamedMutex("local_copy", True):
            for i, k in enumerate(arglist):  # pylint: disable=R1702
                if k.startswith('-lr'):
                    src = k[3:].strip()  # strip "-lr"
                    dst = join(self._cwd, "{}_{}".format(self.jobid, self.task_id), basename(src))
                    if dst not in self._local_rec:
                        # free = <disk space> - 100MB
                        try:
                            if self._cloud_rec:
                                fsize = self._cloud_rec.fsize
                            else:
                                fsize = getsize(src)

                            free = disk_usage(D_DRIVE).free - 100000000
                            # copy file and replace arguments (only when smaller than 150G)
                            if free > fsize and fsize < 150000000000:
                                try:
                                    makedirs(dirname(dst))
                                except Exception:
                                    pass
                                self._logger.info("copying '%s' (%s) -> %s (%s)", src, human_size(float(fsize)),
                                                  self.taskfolder[:2], human_size(free))
                                startm = time()
                                if self._cloud_rec:
                                    self._cloud_rec.download(dst)
                                else:
                                    CopyFileEx(src, dst, None, None, False, 4096)
                                self._logger.info("copy to '%s' done after %ds", dst, time() - startm)
                                self._local_rec.append(dst)
                            else:  # pragma: no cover
                                raise HpcError("not enough free space: {}MB, rec: {}MB"
                                               .format(free // 1000000, fsize // 1000000))
                        except Exception as ex:  # pragma: no cover
                            self._logger.warning("local copy rec failed: %s!", ex)
                            return ERR_INFRASTRUCTURE_FAILED_TO_COPY_DATA

                    # here we go if rec already on disk
                    arglist[i] = "-lr{}".format(dst)
                    localrec = True
                    break

        if MSWIN and self._is_mts and self._rec_ip:
            lropt = '-lr'
            for i, k in enumerate(arglist):
                if k.startswith(lropt):
                    arglist[i] = lropt + self._rec_ip
                    break

        self._logger.info("%scommand: %s", prefix, " ".join(arglist), extra={"color": "blue"})
        if cwd:
            self._logger.info("%scwd: %s", prefix, cwd)

        # check mts.ini if it might have been manipulated
        if self._is_mts:
            ini = join(dirname(exe), "mts.ini")
            if exists(ini) and check_mts_ini(ini, checkonly=True):
                self._logger.error("mts.ini check failed, not having standard settings done properly!")
                # self._subexit(ERR_MTS_UNSPECIFIED_ERROR_FOUND)

        if not MSWIN:  # pragma: nocover
            try:  # set the x flag on Linux
                chmod(arglist[0], stat(arglist[0]).st_mode | S_IEXEC)
            except Exception:
                pass  # ignore silently

        # start the app
        self._proc = BackgroundProcess(arglist, cwd if cwd != "" else None, logger.info, logger.error,
                                       logger=self._logger, env=self._env, **pargs)
        self._taskpid = self._proc.pid

        return localrec

    def _watch_dog(self, localrec, **kwargs):  # pylint: disable=R0911,R0914
        """wait until process ends"""
        io_watch, time_watch = not localrec and self._subtask.iowatch, self._subtask.timewatch
        vargs = [io_watch, self._subtask.cpuwatch, self._subtask.timewatch, self._subtask.prnwatch]
        logger = get_logger('HPC wdog:', self._streams)  # , color="seagreen")
        what = " and ".join(((k % vargs[i]) if "%" in k else k)
                            for i, k in enumerate(["I/O", "CPU", "Timeout (%s h)", "prints"])
                            if [vargs[0], self._subtask.cpuwatch, self._subtask.timewatch > 0.,
                                self._subtask.prnwatch][i])
        if not what:
            logger.error("all watchdogs switched off, limiting your run to 6 hours!")
            time_watch = 6

        inittime = max(self._wargs.get('wdog_init', REPORT_WAIT_TIME_INITIAL[int(self._is_mts)]), 1.2)
        looptime = max(self._wargs.get('wdog_loop', kwargs['wdog_loop']), 1.2)  # 1.2 -> prevent division by 0
        loop_prn = self._wargs.get('wdog_prns', kwargs['wdog_prns'])
        mts_exe = self._wargs.get("mts_exe", "measapp.exe")
        mem_max = self._wargs.get("mem_max", kwargs['mem_max'])
        virt_max = self._wargs.get("virt_max", kwargs['virt_max'])
        wdog_lst = self._wdog_log[max(self._wdog_log.keys())]

        logger.info("starting to watch PID %d for %s and max mem %dMB / max virt %dMB",
                    self._taskpid, what, mem_max // 1000000, virt_max // 1000000)

        if time_watch <= 0.:
            time_watch = MAX_TIME_WATCH
        maxtime = time() + min(time_watch, MAX_TIME_WATCH) * 3600

        cpu_conf, io_conf, prn_conf = 100.0, 100.0, 100.0
        fail_count = 0
        cpu_usage = []

        def watch_time(until):
            """wait until time expires"""
            k = 0
            while time() < until:
                k += 1
                if not self._proc.running:
                    return False

                try_sleep(1.)
                if k % 12 == 0 and until - time() > 12:
                    try:
                        vals = datacoll.process_stats()
                        self._app_watch_io = vals[IO_CNT]
                        self._cpu_time = vals[PROC_TIME]
                    except Exception:
                        pass
            return True

        try:
            datacoll = MonDataCollector(self._proc.proc, logger, self.taskfolder, self._is_docker)
        except (MemoryError, IOError):  # pragma: no cover
            #  try again if we might be able to...
            logger.error("Memory error at watchdog, falling back to max time = %.1fh!", max(48., time_watch))
            return ERR_APPLICATION_TIMEOUT if watch_time(maxtime) else ERR_OK
        except NoSuchProcess:
            logger.info("seems, process exited already.")
            return ERR_OK
        except Exception as ex:
            logger.info("other exception: %s", ex)
            return ERR_OK

        if not watch_time(time() + inittime):
            logger.info("process exited (init).")
            return ERR_OK

        for lcnt in count():
            # receive Input Data from the app_monitor
            try:
                data = datacoll()
            except Exception:
                data = None

            if data is None:  # pragma: no cover
                if fail_count > pvs.FAIL_THRESHOLD:
                    logger.error("process stat request failed more than %d times in a row!!!", pvs.FAIL_THRESHOLD)
                    return ERR_APPLICATION_UNSPECIFIED_ERROR_FOUND
                fail_count += 1
                logger.warning("no data received (#%d)", fail_count)
            else:
                fail_count = 0
                # CPU load can be greater than 100% due to multicore usage
                io_load, cpu_load = data
                # save disk_io
                self._app_watch_io = datacoll.io_load
                self._cpu_time = datacoll.cpu_time

                cpu_conf = (cpu_conf * (1 - pvs.FILTER_STRENGTH_CPU) + cpu_load * pvs.FILTER_STRENGTH_CPU)
                io_conf = (io_conf * (1 - pvs.FILTER_STRENGTH_IO) +
                           (0 if io_load < pvs.FILTER_THRESHOLD_IO else 100) * pvs.FILTER_STRENGTH_IO)
                prns = self._proc.prn_lines
                prn_conf = min(prn_conf * (1 - pvs.FILTER_STRENGTH_PRN) + prns * 444. * pvs.FILTER_STRENGTH_PRN, 100.)
                cpu_usage.append(cpu_load)

                if getattr(self._jobdb, "wdog_log", False):
                    if PY2:
                        dtnow = int((datetime.utcnow() - EPOCH).total_seconds())
                    else:
                        dtnow = int(datetime.utcnow().timestamp())
                    wdog_lst.append([round(i, 2) for i in [io_load, io_conf, cpu_load, cpu_conf, datacoll.mem_load,
                                                           datacoll.virt_load, datacoll.net_io // 1000]] + [dtnow])

                disk_stat = disk_usage(D_DRIVE)
                if not lcnt % loop_prn:
                    logger.info("IO: %.1fkB/s (conf: %.1f), CPU: %.1f%% (conf: %.1f), "
                                "MEM: %s / VIRT: %s, tot IO: %dkB/s, prints: %d (conf: %.1f), temp free: %s",
                                io_load, io_conf, cpu_load, cpu_conf, human_size(datacoll.mem_load),
                                human_size(datacoll.virt_load), datacoll.net_io // 1000, prns, prn_conf,
                                human_size(disk_stat.free, 'B'))

                ret = None
                if disk_stat.percent > 90.:
                    logger.error("reaching 90%% fill state on %s: %.1f%%, cannot continue!", D_DRIVE, disk_stat.percent)
                    ret = ERR_HPC_LOW_DISK_SPACE
                elif disk_stat.percent > 80.:
                    logger.warning("reaching more than 80%% fill state on %s: %.1f%%", D_DRIVE, disk_stat.percent)

                if io_watch and io_conf < pvs.IO_CONFIDENCE_THRESHOLD:  # check i/o threshold
                    logger.error("Process I/O traffic is too low!!!")
                    ret = ERR_APPLICATION_IO_IDLE

                elif self._subtask.cpuwatch and cpu_conf < pvs.CPU_CONFIDENCE_THRESHOLD:  # check cpu threshold
                    logger.error("Process is idle (no CPU)!!!")
                    ret = ERR_APPLICATION_CPU_IDLE

                elif self._subtask.prnwatch and prn_conf < pvs.PRN_CONFIDENCE_THRESHOLD:  # check prn threshold
                    logger.error("Process has no print outs!!!")
                    ret = ERR_APPLICATION_PRN_IDLE

                elif datacoll.mem_load > mem_max:
                    if datacoll.proc_name == mts_exe:
                        logger.error("MTS uses more memory than allowed: %s", human_size(datacoll.mem_load))
                        ret = ERR_MTS_MEM_LEAK_FOUND
                    elif datacoll.mem_load > 2 * mem_max:
                        logger.error("%s uses more memory than allowed: %s",
                                     datacoll.proc_name, human_size(datacoll.mem_load))
                        ret = ERR_APPLICATION_HIGH_MEM

                if datacoll.virt_load > virt_max:
                    logger.error("%s uses more virtual memory than allowed: %s",
                                 datacoll.proc_name, human_size(datacoll.virt_load))
                    ret = ERR_APPLICATION_HIGH_MEM

                if self._proc.fatal_cnt:
                    logger.error("fatal message appeared")
                    ret = ERR_APPLICATION_FATAL

                if ret:  # should we print?
                    logger.error("issuing errorcode: %d", ret)
                    break

            if time() > maxtime:
                logger.error("application timed out after {:.2f}h, ErrorCode: {!s}"
                             .format(min(time_watch, MAX_TIME_WATCH), ERR_APPLICATION_TIMEOUT))
                ret = ERR_APPLICATION_TIMEOUT
                break

            if not watch_time(time() + looptime):
                logger.info("process exited (loop).")
                ret = ERR_OK
                break

        logger.info("system net IO: %dB/s, system CPU: %.1f%%, system disk I/O: %dB",
                    datacoll.net_io, datacoll.tot_cpu, datacoll.tot_disk)
        runtime = (datacoll.io_tm - datacoll.proc_start).total_seconds()
        logger.info("proc runtime: %s - %s = %ds (%02d:%02d:%02d), proc I/O: %s", datacoll.proc_start, datacoll.io_tm,
                    runtime, runtime // 3600, runtime // 60 % 60, runtime % 60, human_size(datacoll.io_load, 'B'))
        if cpu_usage:
            logger.info("CPU average: %.1f%%", sum(cpu_usage) / len(cpu_usage))
        else:
            logger.info("CPU average: n/a")
        return ret

    def _check_for_error(self, arglist):
        """
        check app watcher and the process, if an error happened or not.

        :param list arglist: argument list (application)
        """
        if (self._app_watch_ret in (ERR_APPLICATION_CPU_IDLE, ERR_APPLICATION_IO_IDLE, ERR_APPLICATION_TIMEOUT) and
                not self._cloud_rec and self._recording and exists(self._recording)):
            self._logger.info("recording '%s' was %d bytes big", self._subtask.recording, getsize(self._recording))

        if self._app_watch_ret != ERR_OK:  # set subtask exitcode for all app watcher errors
            self._subexit(self._app_watch_ret)

        self.cancel_handler()

        self._logger.info("error code after execution: %d", self._subexit.error)

        exmap = dict(self._jobdb.task(self.task_id, USR_EXMAP, {}))
        exmap.update(self._subtask.get(USR_EXMAP, {}))
        procex = exmap.get(str(self._proc.exitcode), self._proc.exitcode)
        if procex != self._proc.exitcode:
            self._logger.info("remapping exitcode to %d", procex)
            self._proc.exitcode = procex

        if self._is_mts:  # check exit code for measapp.exe
            sbase, cbase = dirname(arglist[0]) + "\\", None
            for i in arglist:  # pylint: disable=R1702
                if i.startswith('-pc'):
                    cbase = i[3:] + "\\"
                    break

            if not cbase:
                self._logger.error("MTS is missing config base folder option!")

            elif self._app_watch_ret in (ERR_APPLICATION_CPU_IDLE, ERR_APPLICATION_IO_IDLE, ERR_APPLICATION_TIMEOUT):
                missing = []
                for fname, minver in FILE_CHECKS:
                    fname = fname.replace("\\sys\\", sbase).replace("\\cfg\\", cbase)
                    if not exists(fname):
                        missing.append(basename(fname))
                        continue
                    try:
                        version = file_version(fname)
                        if version < Version(minver):  # pragma: no cover
                            self._logger.error("%s is too old: %s", basename(fname), version, extra={"color": "red"})
                            self._subexit(ERR_MTS_OLD_DLL_DETECTED)
                        else:
                            self._logger.info("%s is alright: %s", basename(fname), version, extra={"color": "green"})
                    except Exception:  # pragma: no cover
                        self._logger.warning("%s's version cannot be distinguished!", basename(fname))
                if missing:
                    self._logger.info("not found: %s", ", ".join(set(missing)), extra={"color": "gray"})

            try:
                self._logger.info("measapp.exe version is: %s", str(file_version(arglist[0])))
            except Exception:
                self._logger.info("unable to extract version from %s", arglist[0])

            self._subexit(MTS_LOOKUP_EXITCODE.get(self._proc.exitcode, ERR_MTS_UNSPECIFIED_ERROR_FOUND))

            if self._subtask.get("mtscheck", False):
                self._logger.info("-" * 112)
                self._mts_check(self._subexit, self._subtask.rectms, self._subtask.recdiff)

        elif self._subtask.get("pass_ecode", False):
            self._subexit(self._proc.exitcode)
        elif self._is_docker and self._docker_err:
            self._logger.warning("docker originally returned %d", self._proc.exitcode)
            self._subexit(self._docker_err)
            self._docker_err = ERR_OK
        elif self._proc.exitcode in [0] + list(range(201, 220)):
            self._subexit(self._proc.exitcode)
        elif self._is_py:
            self._subexit(ERR_PYTHON_UNSPECIFIED_ERROR_FOUND)
        else:
            self._subexit(ERR_APPLICATION_UNSPECIFIED_ERROR_FOUND if self._proc.running or self._proc.exitcode else 0)

    def _mts_check(self, excode, rectms, recdiff):
        """check MTS errors"""
        if getattr(self._jobdb, "mtscheck", True):
            try:
                logger = get_logger('MTS check:', self._streams)
                logger.info("checking MTS logs.")
                errors, ecnt, logs = mts_log_check(folder=join(self.taskfolder, "log"), exitcodes=excode,
                                                   log_corrupts=not self._terminated, logger=logger,
                                                   level=max(self._jobdb.errorlevel, self._subtask.errorlevel))
                self._envhandler.errors(errors, ecnt)
                estr = ["{} {}".format(v, ["crashes", "exceptions", "alerts", "errors"][k])
                        for k, v in iteritems(ecnt) if k in [0, 1, 2] and v > 0]
                if logs:
                    if estr:
                        logger.error("there are MTS log issues: %s", ", ".join(estr))
                    else:
                        logger.info("no issues found from logs.")
            except Exception as ex:  # pragma: no cover
                logger.error("log checker exception: %s", str(ex))
                excode(ERR_INFRASTRUCTURE_UNSPECIFIC_ERROR_FOUND)

            self._logger.info("error code after MTS log check: %s", excode)
            self._mts_check_cnt += 1

        if self._jobdb.task(self.task_id, BSIG_CHK, self._jobdb.bsig_check) or self._subtask.get(BSIG_CHK, False):
            self._logger.info("checking bsig's/csv's...")
            excode(bsig_check(bsigs=self.datafolder, logger=get_logger('bsig check:', self._streams), exit_prio=excode,
                              rectms=rectms, recdiff=recdiff, bsig_ext=getattr(self._jobdb, "bsig_ext", [".bsig"])))
        self._logger.info("-" * 112)

    def _change_ip(self):
        """look up IP address of recording's server which in turn does a round robin of the IP"""
        if self._recording and self._recording[1] != ':':
            orip = self._rec_ip
            for _ in range(3):
                try:
                    splt = self._recording.split('\\')
                    splt[2] = resolve_ip(splt[2])
                    self._rec_ip = "\\".join(splt)
                    if self._rec_ip != orip:
                        break
                    try_sleep(1)
                except Exception as iex:
                    self._logger.warning("unable to find host's IP addr (%s)!", str(iex))

    def _start_app(self, arglist, cwd, **kwargs):  # pylint: disable=R0914
        """
        start real application and watch it.

        :param list arglist: list of parameters
        :param str cwd:      current working dir
        :param dict kwargs:  pass through, for _start_process
        """
        if self._recording is not None:  # recording available -> do the check
            for retr in range(3):
                try:  # check if file exists
                    if self._cloud_rec:
                        fsize = self._cloud_rec.fsize
                        self._logger.info("recording is valid and has size=%dB (%s)", fsize, human_size(fsize))
                    else:
                        self._change_ip()
                        # check network throughput by reading 10 seconds along recording
                        recfn = self._rec_ip if self._rec_ip else self._recording
                        self._logger.info("checking %s (%s)...", recfn, self._recording)
                        with open(recfn, "rb") as fp:
                            dur, cnt, sz = time(), 0, 65536
                            while (time() - dur) < 10.:
                                data = fp.read(sz)  # read about 8k
                                cnt += 1
                                if not data:
                                    break
                            dur, sz = time() - dur, cnt * sz
                            try:
                                throughput = sz / dur
                            except ZeroDivisionError:
                                throughput = inf

                        if throughput < pvs.MIN_NET_THROUGHPUT:  # pragma: no cover
                            log, madd = self._logger.warning, "=> below minimum of {}MB/s!"\
                                .format(pvs.MIN_NET_THROUGHPUT // 1000000)
                        else:
                            log, madd = self._logger.info, "=> good" if sz > 3000000 else "=> unsure"

                        fsize = getsize(recfn)
                        log("size=%dB (%s), read %dB during %.1fs = %s %s", fsize, human_size(fsize),
                            sz, dur, human_size(throughput * 8, "bps"), madd)

                    if virtual_memory().free < pvs.MIN_MEM_FREE:  # pragma: no cover
                        self._logger.warning("free virtual memory is lower than allowed minimum %s < %s!",
                                             human_size(virtual_memory().free), human_size(pvs.MIN_MEM_FREE))
                        self._subexit(ERR_APPLICATION_LOW_MEM)

                    if cpu_percent(2, False) > pvs.MAX_CPU_USAGE:  # pragma: no cover
                        self._logger.warning("cpu utilization exceeds maximum allowed of %.0f!", pvs.MAX_CPU_USAGE)
                        self._subexit(ERR_APPLICATION_LOW_CPU)
                    break

                except Exception as ex:
                    if retr < 2:
                        self._logger.warning("trying again as of error '%s'...", str(ex).replace('\\\\', '\\'))
                        self._change_ip()
                    else:
                        self._logger.error("measurement not available: '%s'", self._recording)
                        self._logger.error("OSError:: '%s'", ex)
                        self._subexit(ERR_INFRASTRUCTURE_RECORDING_UNAVAILABLE)
                        return

            if not self._cloud_rec and MSWIN and GetFileAttributesW(self._recording) & FILE_ATTRIBUTE_OFFLINE:
                self._logger.error("measurement archived: '%s'", self._recording)
                self._subexit(ERR_INFRASTRUCTURE_RECORDING_ARCHIVED)
                return

            if self._subtask.recmap and self._subtask.measid is None:
                self._logger.warning("measurement not registered inside DB!")
        else:
            self._logger.info("we're not testing a measurement, no availability checks performed.")

        # start wrapper apps
        with WrapProc(kwargs.pop("wrapexe", []), self._logger, self._streams, self) as wraproc:
            main_wnd = 0  # workaround for MTS main window creation / reading recording problem
            while main_wnd < 3:  # pylint: disable=R1702
                if main_wnd:
                    self._logger.info("re-starting MTS again...")

                localrec = self._start_process(arglist, cwd, len(wraproc), **kwargs)

                if self._taskpid:
                    # wait until process ends
                    self._app_watch_ret = \
                        self._watch_dog(localrec,
                                        wdog_ltime=getattr(self._jobdb, "wdog_init", REPORT_WAIT_TIME_CYCLE),
                                        wdog_loop=getattr(self._jobdb, "wdog_loop", REPORT_WAIT_TIME_CYCLE),
                                        wdog_prns=getattr(self._jobdb, "wdog_prns", 1),
                                        mem_max=getattr(self._jobdb, "mem_max", pvs.MIN_MEM_FREE),
                                        virt_max=getattr(self._jobdb, "virt_max", pvs.MIN_VIRT_FREE))

                    if not self._proc.running:
                        # if not self._is_mts:
                        #     self._logger.info("application finished (%d)", self._proc.exitcode)
                        if self._is_mts:
                            msg = "measapp.exe finished ({!s}) -> ".format(self._proc.exitcode)
                            if self._proc.exitcode in MTS_LOOKUP_EXITCODE:
                                self._logger.info("%s%s", msg, MTS_LOOKUP_EXITMSG[self._proc.exitcode])
                            else:
                                try:
                                    emsg = WinError(self._proc.exitcode).strerror
                                except Exception:
                                    emsg = "unknown error happened"
                                self._logger.info("%s ?%s?", msg, emsg)

                    main_wnd += 1 if self._is_mts and self._proc.exitcode in (3, 4,) else 3
                    if main_wnd < 3:
                        self._change_ip()
                        continue  # try again to start the MTS

                    # check for an error code from process
                    self._check_for_error(arglist)
                elif localrec == ERR_INFRASTRUCTURE_FAILED_TO_COPY_DATA:
                    self._subexit(ERR_INFRASTRUCTURE_FAILED_TO_COPY_DATA)
                else:
                    self._subexit(ERR_HPC_APPLICATION_NOT_FOUND)
                if main_wnd == 0:
                    break

            # set environ var for original exitcode
            environ["exitcode"] = str(self._proc.exitcode)

    def execute(self, **kwargs):  # pylint: disable=R0914
        """start the application based on database input."""
        taskstarttm = time()
        self._logger.info("starting on node %s inside %s as user %s with HPC V %s with Python %s (%s)",
                          gethostname().split('.')[0], self._cwd, getuser(), __version__,
                          ".".join(python_version_tuple()), architecture()[0])
        df_start = disk_usage(D_DRIVE).free
        log = getattr(self._logger, "info" if df_start > pvs.D_FREE_THRESHOLD else "warning")
        log("space available on {} {}".format(D_DRIVE, human_size(df_start, "B")))
        # self._verbose = kwargs.get("verblevel", 0)

        self.task_id = kwargs.get("taskid", environ.get("CCP_TASKID", "1"))
        self.taskname = environ.get("TASKNAME", "T{:0>5}".format(self.task_id))

        # read job stuff from db
        self.networkpath = join(server_path(self._jobdb.head if head_name() else OTHER), self.jobname)

        self._envhandler = EnvData(db=self._dbase)

        try:
            self._mail_user(self._jobdb.task(self.task_id, NOTIFY_START), "Running")
        except KeyError:
            self._logger.error("TaskID discrepancy: task %s misconfigured!", self.task_id)
            self._exitcode(ERR_HPC_PID_INVALID)

        # create standard folders for the task
        if self._exitcode.error == 0 and self._create_std_items("TaskStart"):
            # set env vars for all subprocess
            for k, v in (("JobID", self.jobid,), ("JobName", self.jobname,),
                         ("TaskID", self.task_id,), ("TaskName", self.taskname,),
                         ("HPCTaskDataFolder", self.datafolder,), ("HPCTaskTmpFolder", self.tempfolder,),):
                self._env[k.upper()] = str(v)

            # set ctrl+break handler
            try:
                signal(SIG_END, self.cancel_handler)
                signal(SIGTERM, self.cancel_handler)
                signal(SIGINT, self.cancel_handler)
                signal(SIGSEGV, self.cancel_handler)
            except ValueError as val:
                # we're already in a thread...
                if val.message != "signal only works in main thread":  # pylint: disable=E1101
                    raise
            skip, skip_prn = [0, 0], False

            with WrapProc(self._jobdb.task(self.task_id, WRAP_EXE), self._logger, self._streams, self) as wraproc:

                if wraproc.failed:  # no chance to do it inside the class itself breaking inside this context
                    raise HpcError(wraproc.failed, ERR_APPLICATION_WRAPPER)

                # do the complete processing of one SubTask
                for subidx, self._subtask in enumerate(self._jobdb[self.task_id]):
                    if self._subtask.command is None:
                        self._logger.info("we have a dummy task (aka NOP), continuing here.")
                        continue

                    if self._terminated:
                        self._logger.warning("we're requested to quit, no further sub-tasks will be executed!")
                        break

                    if getattr(self._jobdb, "eoe", False) and self._exitcode.state == "Failed":
                        self._logger.info("due to eoe=True, no further sub-tasks will be executed!")
                        break

                    which = int(self._subexit.state == "Failed")
                    if skip[which]:
                        if not skip_prn:
                            self._logger.info("skipping next %d subtask(s) as of state %s.",
                                              skip[which], self._subexit.state)
                            skip_prn = True
                        skip[which] -= 1
                        continue
                    if skip[which] is None:
                        self._logger.info("skipping the rest of subtasks as of state %s.", self._subexit.state)
                        break

                    skipon = self._subtask.get("skipon", [])
                    if (self._subexit.error in (self._jobdb.skipon + skipon)
                            or self._subexit.lasterror in (self._jobdb.skipon + skipon)
                            or self._exitcode.error in self._jobdb.skipon):
                        self._logger.info("=" * 112)
                        self._logger.info("stepping over subtask %d due to exitcode %d (%s)", subidx + 1,
                                          self._exitcode.error, EXIT_MAP.get(self._exitcode.error, "-"))
                        # self._subexit = ExitCodes(self._exitcode, init_code=ERR_PSEUDO_SKIPON)
                        continue

                    self._env["SUBTASKID"] = str(subidx)

                    self._subexit.clear()
                    self._taskpid = None
                    starttm = datetime.utcnow()
                    self._logger.info("=" * 112)
                    self._logger.info("starting subtask %d (id %d)", subidx + 1, self._subtask.subid)
                    self._logger.info("=" * 112)

                    # do the extra-logging
                    xlogs = self._subtask.get("xlog", [])
                    if xlogs:
                        log = get_logger('usr xlog:', self._streams)
                        for ent in xlogs:
                            if isinstance(ent, list):
                                getattr(log, ent[0], "error")(ent[1])
                            else:
                                log.info(ent)

                    # set needed environment vars
                    try:
                        env = list(zip(*self._subtask.env))
                    except AttributeError:  # fallback due to transition errors
                        env = list(zip(*self._subtask.envdata))
                    if env:
                        for i, k in zip(env[0], replace_env_vars(self, list(env[1]))):
                            self._env[i] = str(k)

                    # replace all variables in CMDList
                    replace_env_vars(self, self._subtask.command)
                    self._subtask.workdir = replace_env_vars(self, [self._subtask.workdir])[0]

                    if self._subtask.get("replace_path", True):
                        arglist = replace_server_path(self._subtask.command, reverse=self.networkpath[0] == 'D')
                    elif isinstance(self._subtask.command, StringTypes):
                        arglist = [self._subtask.command]
                    else:
                        arglist = self._subtask.command

                    mtc = match(AZR_BLOB_STX, str(self._subtask.recording))
                    if mtc and MSWIN:
                        cstr = AZR_CONN_STR.format(mtc.group("epp"), mtc.group("account"),
                                                   AZR_ACC_KEYS[mtc.group("account")], mtc.group("suffix"))
                        try:
                            self._cloud_rec = CloudBlob(cstr, mtc.group("container"), mtc.group("blob"))
                        except Exception:
                            raise HpcError("Azure STK not properly installed!")
                    else:
                        self._cloud_rec = None

                    self._recording = replace_server_path(self._subtask.recording) if MSWIN \
                        else win2linux(self._subtask.recording)
                    self._rec_ip, self._cpu_time = None, 0

                    # do the real application call and re-prioritise
                    self._wdog_log[subidx] = []
                    self._start_app(arglist, self._subtask.workdir,
                                    **{k: self._subtask.get(k, v) for k, v in [["shell", False], ["outchk", True],
                                                                               ["wrapexe", []]]})
                    self._all_cpu_time += self._cpu_time

                    self._exitcode(self._subexit)
                    logmsg = "error code after subtask: {!s} --> tasks exitcode: {}"\
                        .format(self._subexit, self._exitcode.error)
                    (self._logger.info if self._subexit.error == ERR_OK else self._logger.error)(logmsg)
                    stoptm = datetime.utcnow()

                    self._envhandler.append({"subtaskid": subidx, "starttime": starttm, "stoptime": stoptm,
                                             "exitcode": self._subexit.error, "command": " ".join(arglist)[:2000],
                                             "pid": self._taskpid, "measpath": self._subtask.recording,
                                             "disk_io": self._app_watch_io, "app": self._subtask.app,
                                             "measid": self._subtask.measid if self._subtask.recmap else None,
                                             "cfg": self._subtask.simcfg, "cpu": self._cpu_time})

                    self._env["SUBTASK{}_TIMING".format(subidx)] = "{}:{}"\
                        .format(int(mktime(starttm.timetuple())), int(mktime(stoptm.timetuple())))
                    self._env["SUBTASK{}_ERROR".format(subidx)] = str(self._subexit)
                    self._env["SUBTASK{}_STATE".format(subidx)] = self._subexit.state
                    self._env["TASK_ERROR"] = str(self._exitcode)
                    self._env["TASK_STATE"] = self._exitcode.state
                    skip = self._subtask.get("skip", [0, 0])
                    if self._is_mts:
                        rectms, recdiff = self._subtask.rectms, self._subtask.recdiff

            if wraproc.failed:
                self._exitcode(ERR_APPLICATION_WRAPPER)

            cncl_cmd = self._jobdb.task(self.task_id, CNCL_CMD)
            if self._terminated and cncl_cmd:
                if not isinstance(cncl_cmd, list):
                    cncl_cmd = [cncl_cmd]
                for cmd in cncl_cmd:
                    cmd = " ".join(replace_env_vars(self, cmd.split()))
                    self._logger.info("=" * 112)
                    self._logger.info("executing specified cancel command: %s", cmd)
                    pcncl = BackgroundProcess([cmd], None, get_logger('cancel cmd:', self._streams).info, None,
                                              logger=self._logger, shell=True, env=self._env)
                    tmr = LogTimer(60, pcncl.close)
                    tmr.start()
                    pcncl.wait()

            self._logger.info("=" * 112)
            self._logger.info("all subtasks finished.", extra={"color": "brown"})
            self._logger.info("-" * 112)

            # remove local recordings
            for rec in self._local_rec:
                unlink(rec)

            if not self._terminated:
                if self._mts_cnt > self._mts_check_cnt:
                    # let's take the times from last task
                    self._mts_check(self._exitcode, rectms, recdiff)

                # copy and delete data files
                self._copy_delete_data()

                self._create_std_items("TaskStop")

        if not self._terminated:
            self._logger.info("=" * 112)
            df_end = disk_usage(D_DRIVE).free
            log = getattr(self._logger, "info" if df_end > pvs.D_FREE_THRESHOLD else "warning")
            log("space available on {} {}, diff: {:.2f}%"
                .format(D_DRIVE, human_size(df_end, "B"), abs(df_end * 100. / df_start)))
        self._mail_user(self._jobdb.task(self.task_id, NOTIFY_STOP), self._exitcode.state)

        self._logger.info("total subtask runtime: %s", str(timedelta(seconds=time() - taskstarttm)).split('.')[0])
        if self._exitcode.history:
            self._logger.info("exitcode history:")
            for i in sorted(self._exitcode.history, key=lambda e: self._exitcode.prio(e[0]), reverse=True):
                self._logger.info("exitcode %d (%s) with prio %d reported @ %s",
                                  i[0], EXIT_MAP.get(i[0], "-"), self._exitcode.prio(i[0]), i[1].replace(tzinfo=UTC))
        self._logger.info('=> HPC task ends with exit code %d (%s): %s: state=%s.',
                          self._exitcode.error, EXIT_MAP.get(self._exitcode.error, "-"), self._exitcode.desc,
                          self._exitcode.state)

        return self._exitcode.error

    @property
    def exitcode(self):
        """
        :return: exit code
        :rtype: int
        """
        return self._exitcode.error

    @exitcode.setter
    def exitcode(self, value):
        """:param int value: new exitcode value"""
        self._exitcode(value)

    @property
    def exitmessage(self):
        """
        :return: exit message
        :rtype: str
        """
        return self._exitcode.desc

    def _write_stream(self):
        """write stream to file"""
        outdir = join(self.networkpath, "2_Output", self.taskname)
        outfile = None
        for k in range(12):
            try:
                try:  # seems, output dir doesn't exist sometimes???
                    makedirs(outdir)
                except Exception:
                    pass
                ecnt, msg = 0, "data %s is no longer available at storage location"
                for i in range(99999):
                    fname = join(outdir, "stdout_%05d.txt" % i)
                    if not exists(fname):
                        try:
                            outfile = open(fname, "w")
                            break
                        except IOError as ex:
                            if ecnt < 3:
                                self._logger.error(msg, str(ex).split("'")[1])
                                try_sleep(3)
                            else:
                                self._logger.error(msg + ", giving up", str(ex).split("'")[1])  # pylint: disable=W1201
                                return None
                            ecnt += 1
                else:
                    outfile = TemporaryFile(dir=outdir, delete=False)

                self.streamer.seek(0)
                while 1:
                    l = self.streamer.readline()
                    if not l:
                        break
                    outfile.write(sub(r"^(.*)(<span style=\"background-color: \w+\">)(.*)(</span>)(.*)$", r"\1\3\5", l))

                # copyfileobj(self.streamer, outfile)
                outfile.close()
                outfile = outfile.name
                if outfile is not None:
                    break
            except Exception as _ex:
                if k == 11:
                    print("unable to write stdoutfile to {}!\n".format(outdir))
                else:
                    try_sleep(12)

        return outfile

    @property
    def out_stream(self):
        """
        :return: output stream
        :rtype: list
        """
        self.streamer.seek(0)
        return [i.strip() for i in self.streamer.readlines()]

    @timeit
    def finalize(self):
        """finalize by saving rest of data to DB"""
        head = self._jobdb.head if head_name() else self.head_node
        out, portal = None, HPC_STORAGE_MAP[head][5]
        _taskdur = self._envhandler.end_task()
        try:
            used_db, requ = self._envhandler.update_task(noprn=True, exitcode=self._exitcode.error,
                                                         headnode=head, jobid=self.jobid,
                                                         stdout=self.streamer, errmons=self._errmons,
                                                         ehist=self._exitcode.history + self._subexit.history,
                                                         cpu=self._all_cpu_time, state=self._exitcode.state,
                                                         tname=self.taskname, wdog=self._wdog_log)
            if not head_name():  # when running locally (via JobSim)
                return

            if used_db == EnvData.NO_DB:
                print("\nwe've failed to connect to DB!")
                out = self._write_stream()
            else:
                # doesn't work any longer as users do not have the right to overwrite.....
                # print("[{{000214A0-0000-0000-C000-000000000046}}]\r\nProp3=19,2\r\n[InternetShortcut]\r\n"
                #       "IDList=\r\nURL=http://hpcportal.conti.de/php/HPC/task/{}/{}/{}"
                #       .format(self.head_node, self.jobid, self.task_id), file=sys.stderr)
                print("\nyou'll find your task output here:")
                # requ = int(environ["CCP_RETRY_COUNT"])
                if requ:
                    print("{}/task/{}/{}/{}/{}\n".format(portal, head, self.jobid, self.task_id, requ))
                else:
                    print("{}/task/{}/{}/{}\n".format(portal, head, self.jobid, self.task_id))

        except Exception as ex:  # pragma: no cover
            self._exitcode(ERR_HPC_DATABASE)
            self._logger.info("Database Exception happened: %s", str(ex))
            self._logger.info("HPC task's exitcode adjusted as being unable to write to DB: %d = %s.",
                              self._exitcode.error, self._exitcode.desc)
            out = self._write_stream()
        if out is not None:
            print("\nyou'll find your task output here:\n{}".format(linux2win(out)))
            # with open(join(HPC_STORAGE_MAP[self.head_node][1], "hpc", "HPC_backup",
            #                "{}_{}_{}".format(self.head_node, self.jobid, self.task_id)), "w") as lnkfp:
            #     lnkfp.write(join(self.networkpath, '2_Output', self.taskname, "hpc.sqlite"))
        self.clear()


# - functions ----------------------------------------------------------------------------------------------------------
def _multi_start(args):
    """
    start a task

    :param list args: scheduler name, task id and Q are given
    """
    sched, taskid, snk = args

    try:
        starter = AppStarter(sched=sched)
        starter.execute(taskid=taskid)
    except Exception as ex:  # pragma: no cover
        # catches all non system exiting exceptions
        try:
            msg = getattr(ex, "message", str(ex))
            if msg.startswith("no such task:"):  # pylint: disable=E1101
                print(msg)  # pylint: disable=E1101
                return
        except Exception:
            pass

        print_exc()

        starter.cancel_handler(SIG_END)
        starter.exitcode = ERR_HPC_SCRIPT_MALFUNCTION

    starter.finalize()
    snk.put((taskid, int(starter.exitcode),))


def _main_start():  # pylint: disable=R0911
    """start to process the task...."""
    verstr = "\n{}, version {}".format(split(sys.argv[0])[1], __version__)
    if PY2:
        opts = HpcArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter, version=verstr)
    else:
        opts = HpcArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
        opts.add_argument("-v", "--version", action="version", version=verstr)

    opts.add_argument("-t", "--taskid", type=str, default=environ.get("CCP_TASKID", "1"), help="task name from HPC")
    opts.add_argument("-l", "--verblevel", default=0, action="count", help="be a bit more verbose")
    opts.add_argument("-o", "--stdout", default=False, action="store_true", help="write to stdout as well")
    opts.add_argument("-c", "--cwd", type=str, default=getcwd(), help=SUPPRESS)
    opts.add_argument("-s", "--sched", default=None, help=SUPPRESS)
    opts.add_argument("-f", "--fastwatch", default=False, action="store_true", help=SUPPRESS)
    opts.add_argument("--id", default=None, help="if given it's just ignored")

    try:
        args = opts.parse_args()

        print("\n{} -> Python {} ({}) -> HPC V {}\n"
              .format(gethostname().split('.')[0], ".".join(python_version_tuple()), architecture()[0], __version__))
    except ArgumentParserError as ex:
        print("argument error: {!s}".format(ex))
        return ERR_HPC_WRONG_ARG

    if args.taskid == "all":  # used by test.bat
        with open(join(abspath("."), "hpc", "job.json")) as efp:
            jobenv = load(efp)
            tasks = len(jobenv["tsk"])
            unit = JobUnitType(jobenv["job"]["unit"])
            args.sched = jobenv["job"]["head"]

        cpus = cpu_count()
        mpl = Pool({"Node": 1, "Socket": cpus // 2, "Core": cpus}[str(unit)])
        snake = Manager().Queue(tasks)
        mpl.map(_multi_start, [(args.sched, str(i), snake,) for i in range(1, tasks + 1)])

        ecode = ExitCodes(db=abspath("hpc.sqlite"))

        while not snake.empty():
            taskid, exitint = snake.get()
            texit = ExitCodes(ecode, init_code=exitint)
            ecode(texit)
            print("task {}: exitcode {!s} ({!s})".format(taskid, texit, str(EXIT_MAP.get(texit.error, "-"))))
        print("\ntask output can be queried by issuing: (exchanging correct task id")
        print(r"python hpc\cmd\env_collector.py -d {}\hpc.sqlite log -n {} -j {} -s <task id>"
              .format(args.cwd, args.sched, jobenv["job"]["jobid"]))

        return ecode.error

    try:
        starter = AppStarter(**vars(args))
        starter.execute(**vars(args))
    except HpcError as ex:  # pragma: no cover
        print(str(ex))
        return ex.error
    except NoSuchFile:  # coming from Jobdict as no hpc.json found
        opts.print_help()
        return 0
    except Exception as ex:  # pragma: no cover
        # catches all non system exiting exceptions
        try:
            msg = getattr(ex, "message", str(ex))
            if msg.startswith("no such task:"):  # pylint: disable=E1101
                print(msg)  # pylint: disable=E1101
                return ERR_HPC_INTERNAL_ERROR
        except Exception:
            pass

        print_exc()

        starter.cancel_handler(SIG_END)
        starter.exitcode = ERR_HPC_SCRIPT_MALFUNCTION

    frmt = "DB update time: {:.1f}s" if args.verblevel > 0 else None
    starter.finalize(timeit_frmt=frmt)  # pylint: disable=E1123

    if head_name():
        print("exitcode {} ({!s}): {}".format(starter.exitcode, str(EXIT_MAP.get(starter.exitcode, "-")),
                                              starter.exitmessage))
        if starter.exitcode in [ERR_INFRASTRUCTURE_FAILED_TO_COPY_DATA, ERR_INFRASTRUCTURE_UNSPECIFIC_ERROR_FOUND,
                                ERR_APP_ERR_NETWORK_UNAVAILABLE, ERR_HPC_SCRIPT_MALFUNCTION,
                                ERR_HPC_INTERNAL_ERROR, ERR_HPC_PID_INVALID, ERR_HPC_DATABASE,
                                ERR_HPC_WRONG_ARG, ERR_HPC_UNSPECIFIED_ERROR_FOUND, ERR_HPC_LOW_DISK_SPACE]:
            print("\nif you think it's an HPC / infrastructure problem, don't hesitate and let us know via"
                  "\nhttps://github-am.geo.conti.de/ADAS/HPC_two/issues")

    # special behaviour needed when ERR_INFRASTRUCTURE_FAILED_TO_CREATE_DATA: take node offline
    # if starter.exitcode in (ERR_INFRASTRUCTURE_FAILED_TO_COPY_DATA, ERR_INFRASTRUCTURE_FAILED_TO_CREATE_DATA):
    #     if take_offline():
    #         return ERR_INFRASTRUCTURE_FAILED_TO_CREATE_DATA

    return starter.exitcode


if __name__ == "__main__":
    sys.exit(_main_start())
