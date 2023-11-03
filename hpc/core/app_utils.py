"""
app_utils.py
------------

Utilities needed by the starter and maybe also by others
"""
# pylint: disable=E0611,C0413,C0412
# - import Python modules ----------------------------------------------------------------------------------------------
import sys
from os import linesep
from os.path import join, splitext, basename, expandvars, sep
from threading import Thread
from subprocess import Popen, PIPE, STDOUT
from argparse import ArgumentParser
from time import sleep, time
from timeit import default_timer
from datetime import datetime
try:
    from packaging.version import Version
except ImportError:
    from distutils.version import LooseVersion as Version
from re import split, sub, compile as recomp, escape, IGNORECASE
try:
    from collections.abc import Callable
except ImportError:  # deprecated on Python 3.10
    from collections import Callable
from functools import wraps
from numpy import inf
from psutil import Process, NoSuchProcess, cpu_times, virtual_memory, net_io_counters, disk_io_counters
from six import PY3, iteritems

if PY3:
    from threading import Timer
    StringTypes = (str,)
    try:
        from azure.storage.blob import BlobClient
        # from azure.storage.blob.blockblobservice import BlockBlobService as BlobClient
    except ImportError:
        BlobClient = None
else:
    from threading import _Timer as Timer
    from types import StringTypes
    BlobClient = None

try:
    from docker import from_env
except ImportError:
    from_env = None

MSWIN = sys.platform == "win32"
if MSWIN:
    from win32con import WM_CLOSE
    from win32gui import EnumWindows, PostMessage, IsWindowEnabled  # ,GetWindowText
    from win32process import GetWindowThreadProcessId
    from subprocess import CREATE_NEW_PROCESS_GROUP
    from signal import CTRL_BREAK_EVENT
    from win32api import GetFileVersionInfo, LOWORD, HIWORD
else:
    from signal import SIGINT

try:
    from psutil import NUM_CPUS as CPU_CNT, AccessDenied  # pylint: disable=C0412
except ImportError:
    from psutil import cpu_count, AccessDenied  # pylint: disable=C0412
    CPU_CNT = cpu_count()

# - HPC imports --------------------------------------------------------------------------------------------------------
from ..core.error import ERR_OK, ERR_HPC_APPLICATION_NOT_LOCAL, ERR_APPLICATION_WRAPPER, HpcError
from ..core.logger import get_logger

# - defines ------------------------------------------------------------------------------------------------------------
REPORT_WAIT_TIME_INITIAL = [60, 240]  # Initial Wait Time for 1. Report in [s] for regular / mts apps
REPORT_WAIT_TIME_CYCLE = 60  # time to wait between to requests in [s]
MAX_TIME_WATCH = 120.  # [h] of a task to run
EXIT_GRACE_TIME = 120.  # [s] of a task to finish up after CTRL+break / WM_CLOSE

TIME = 'Time'
PROC_TIME = 'ProcTime'
MEM_BYTES = 'Membytes'
COM_BYTES = 'CommittedSize'
IO_CNT = 'IoCount'

FATALS = r"WindowsError: \[Error 1455\] The paging file is too small for this operation to complete"


# - classes and functions ----------------------------------------------------------------------------------------------
class MonDataCollector(object):  # pylint: disable=R0902
    """class which provides all needed monitor values from a process."""

    def __init__(self, proc, logger, taskfolder, docker):
        """
        init monitor data collector

        :param Process proc: running process
        :param logging.Logger logger: logger instance to use
        :param str taskfolder: task folder
        :param str docker: name of docker to take CPU, MEM and I/O from
        """
        self._proc = proc
        self._logger = logger
        self._accdenied = []
        ctm = self._proc.create_time
        self.proc_start = datetime.utcfromtimestamp(ctm() if isinstance(ctm, Callable) else ctm)
        if from_env and docker:
            self._cli, self._docker = from_env(), docker
        else:
            self._cli = self._docker = None

        self._vals = self.process_stats()

        self._first_tm = self._last_tm = time()
        self._first_io = self._last_io = net_io_counters()
        self._io_offs_cnt = 0
        self._first_cpu = self._last_cpu = cpu_times()
        self._first_disk = self._last_disk = disk_io_counters()

        self.io_tm = self.proc_start
        self.io_load = 0
        self.mem_load = self.virt_load = 0
        self.cpu_time = 0
        self.proc_name = self._proc.name() if isinstance(self._proc.name, Callable) else self._proc.name

        mem_fn = datetime.utcnow().strftime("mem_dump_%Y.%m.%d_%H.%M.%S.csv")
        self._mem_file = join(taskfolder, 'log', mem_fn)
        try:
            with open(self._mem_file, "w") as csv:
                csv.write("time;CPU load [%];total CPU load [%];disk I/O traffic [B/s];total net I/O traffic [B/s];"
                          "Mem load [B];total Mem load[B]")
            self._logger.info("mem dump file: %s", mem_fn)
        except Exception as ex:  # pragma: no cover
            self._logger.error("writing log: {!s}".format(ex))

    @property
    def net_io(self):
        """
        :return: network io until now
        :rtype: float
        """
        if self._last_tm == self._first_tm:
            return 0

        return (self._last_io.bytes_sent + self._last_io.bytes_recv
                - self._first_io.bytes_sent - self._first_io.bytes_recv) / (self._last_tm - self._first_tm)

    @property
    def tot_cpu(self):
        """
        :return: CPU utilization until now
        :rtype: float
        """
        if self._last_tm == self._first_tm:
            return 0

        return ((self._last_cpu.user + self._last_cpu.system - self._first_cpu.user - self._first_cpu.system)
                / (self._last_tm - self._first_tm) * 100. / CPU_CNT)

    @property
    def tot_disk(self):
        """
        :return: total disk I/O until now
        :rtype: int
        """
        return (self._last_disk.read_bytes + self._last_disk.write_bytes
                - self._first_disk.read_bytes - self._first_disk.write_bytes)

    def __call__(self):
        """get io and cpu values"""
        try:
            vals = self.process_stats()
        except Exception:  # pragma: no cover
            raise RuntimeWarning('process is not available')

        self.io_load = vals[IO_CNT]
        self.io_tm = vals[TIME]
        self.mem_load, self.virt_load = vals[MEM_BYTES], vals[COM_BYTES]
        self.cpu_time = vals[PROC_TIME]

        delta_time = (vals[TIME] - self._vals[TIME]).total_seconds()

        # load times are in 100ns ticks -> conversion to seconds -> to percentage from 1s
        # CPU load can be greater then 100% due to multi core usage but this is not of interest to us
        if self._docker:
            cpu_load = 0
        else:
            cpu_load = (max(0., vals[PROC_TIME] - self._vals[PROC_TIME])) / delta_time * 100. / CPU_CNT

        # i/o traffic in [kB/s]
        io_load = max(0., vals[IO_CNT] - self._vals[IO_CNT]) / delta_time

        self._vals = vals

        # same goes for global:
        tm_now = time()

        cpu_now = cpu_times()
        glob_cpu = ((cpu_now.user + cpu_now.system - self._last_cpu.user - self._last_cpu.system) /
                    (tm_now - self._last_tm) * 100. / CPU_CNT)
        self._last_cpu = cpu_now

        io_now = net_io_counters()
        net_io = ((io_now.bytes_sent + io_now.bytes_recv + self._io_offs_cnt
                   - self._last_io.bytes_sent - self._last_io.bytes_recv) / (tm_now - self._last_tm))
        self._last_io = io_now

        self._last_disk = disk_io_counters()
        self._last_tm = tm_now

        # dump memory log to file
        try:
            with open(self._mem_file, "a") as csv:
                csv.write("\n%s;%.1f;%.1f;%d;%d;%d;%d"
                          % (vals[TIME].strftime('%Y-%m-%d %H:%M:%S'), cpu_load, glob_cpu, io_load, net_io,
                             vals[MEM_BYTES], virtual_memory().used))
        except Exception as ex:  # pragma: no cover
            self._logger.error("appending log: {!s}".format(ex))

        return io_load / 1000., cpu_load

    def process_stats(self):  # pylint: disable=R0915,R1260
        """
        get current process states.

        :return:    process states
        :rtype:     dict
        """
        vals = {TIME: datetime.utcnow(), PROC_TIME: 0, IO_CNT: 0, MEM_BYTES: 0, COM_BYTES: 0}

        def _childs(pids):  # pylint: disable=R0912
            """iterate through childs"""
            for i in pids:
                try:
                    if isinstance(i, int):
                        proc = Process(i)
                    else:
                        proc = i
                except NoSuchProcess:
                    return
                else:
                    ctm = proc.cpu_times()
                    vals[PROC_TIME] += ctm.user + ctm.system

                    if MSWIN:
                        ioc = proc.io_counters()
                        vals[IO_CNT] += ioc.read_bytes + ioc.write_bytes

                    try:
                        if MSWIN:
                            mem = proc.memory_full_info()
                            vals[MEM_BYTES] += mem.uss
                            vals[COM_BYTES] += mem.vms + mem.rss + mem.pagefile
                        else:  # pragma: nocover
                            mem = proc.memory_info()
                            vals[MEM_BYTES] += mem.rss
                            vals[COM_BYTES] += mem.vms + mem.rss + mem.shared
                    except AccessDenied:
                        if proc.pid not in self._accdenied:
                            self._accdenied.append(proc.pid)
                            self._logger.warning("no access to mem info for PID %d", proc.pid)

                    _childs(proc.children())

        if isinstance(self._docker, str):
            try:
                self._docker = self._cli.containers.list(filters={"name": self._docker})[0]
                self._logger.info("docker running: %s", self._docker.short_id)
            except Exception:
                pass
        if self._docker is not None and not isinstance(self._docker, str):
            try:
                if self._docker.status == "running":
                    _childs([int(i[0]) for i in self._docker.top(ps_args="o pid")["Processes"]])
                else:
                    self._logger.info("docker not running: state=%s", self._docker.status)
            except Exception:
                self._logger.info("PID retrieval failed: state=%s", self._docker.status)
        else:
            _childs([self._proc])

        return vals


def replace_env_vars(hpc, lot):
    """
    replace a list of things by environmental variables

    :param Starter hpc: the app starter
    :param list lot: list of things
    :return: replaced list
    :rtype: list
    """
    old = list()
    while old != lot:
        old = list(lot)
        for idx, var in enumerate(lot):
            if not var:
                continue
            if isinstance(var, list):
                for i, v in enumerate(var):
                    var[i] = _expandvars(hpc, v)
            else:
                lot[idx] = _expandvars(hpc, var)
    return lot


def _expandvars(hpc, var):
    """expand environment variables"""
    var = expandvars(var)
    for k, v in (("JobID", hpc.jobid,), ("JobName", hpc.jobname,),
                 ("TaskID", hpc.task_id,), ("TaskName", hpc.taskname,),
                 ("HPCTaskDataFolder", hpc.datafolder,), ("HPCTaskTmpFolder", hpc.tempfolder,),):
        var = sub('%{}%'.format(k), escape(v), var, flags=IGNORECASE)

    return var


def try_sleep(seconds):
    """catch IOError and forget about it (https://mail.python.org/pipermail/python-list/2008-August/485397.html)"""
    until = time() + seconds
    steps = min(max(seconds / 13., 0.33), 1.65)
    while time() < until:
        try:
            sleep(steps)
        except IOError:  # pragma: no cover
            pass


def perr(text):
    """
    print to stderr

    :param str text: text to print
    """
    sys.stderr.write(text + linesep)


def file_version(fname):
    """extract file version"""
    info = GetFileVersionInfo(fname, sep)
    fms = info['FileVersionMS']
    fls = info['FileVersionLS']
    return Version("%d.%d.%d.%d" % (HIWORD(fms), LOWORD(fms), HIWORD(fls), LOWORD(fls)))


def webscape(txt):
    """
    took it from html package,
    there might me more to convert, see e.g. here: https://devpractical.com/display-html-tags-as-plain-text/
    """
    ori = txt
    txt = txt.replace("&", "&amp;")  # Must be done first!
    txt = txt.replace("<", "&lt;")
    txt = txt.replace(">", "&gt;")
    if ori != txt:
        txt = txt.replace('"', "&quot;")
        txt = txt.replace('\'', "&#x27;")
    return txt, ori == txt


class ArgumentParserError(Exception):
    """placeholder for parser exceptions"""


class HpcArgumentParser(ArgumentParser):
    """HPC argument parser wrapper exception"""

    def __init__(self, *args, **kwargs):
        """overload"""
        ArgumentParser.__init__(self, *args, **kwargs)

    def error(self, message):
        """
        print a usage message incorporating the message to stderr and exits.

        If you override this in a subclass, it should not return -- it
        should either exit or raise an exception.
        """
        raise ArgumentParserError(message)


class NonBlockingStreamReader(Thread):  # pylint: disable=R0903,R0902
    """the non-blocking stream reader (intended for stdout and stderr)"""

    def __init__(self, stream, writer, **kwargs):
        """
        stream: the stream to read from.
                Usually a process' stdout or stderr.
        """
        self._strm = stream
        self._writer = writer
        self._filter = kwargs.get("filter", None)
        self._inverse = kwargs.get("inverse", False)
        self._callback = kwargs.get("callback", {})
        self._fatals, self._fatcnt = recomp(FATALS), 0
        self.running = False
        self._prnlines = 0
        self.stoptm = None

        Thread.__init__(self)
        self.start()

    def run(self):  # pylint: disable=R0912,R1260
        """Collect lines from 'stream' and put them in 'quque'."""
        self.running = True
        while self.running:  # pylint: disable=R1702
            line = self._strm.readline()
            if line:
                for i in split('\r|\n', line.decode('latin1')):
                    l = i.strip()
                    if l:
                        mtc = True
                        if self._filter:
                            mtc = self._filter.match(l) is not None
                            if self._inverse:
                                mtc = not mtc
                        if mtc:
                            if not PY3:
                                l = l.encode('ascii')
                            try:
                                l, o = webscape(l)
                                self._writer(l if o else "<tt>{}</tt>".format(l))
                            except Exception:
                                print("logging error '{!s}'".format(i))
                        if self._fatals.match(l) is not None:
                            self._fatcnt += 1

                        # call back function on certain messages
                        for cmp, cbi in iteritems(self._callback):
                            if cmp.search(l):
                                cbi[0](cbi[1])

                    self._prnlines += 1
            else:
                self.running = False
        self.stoptm = time()

    @property
    def prn_lines(self):
        """
        :return: lines in output
        :rtype: int
        """
        lns = self._prnlines
        self._prnlines = 0
        return lns

    @property
    def fatal_cnt(self):
        """
        :return: fatal printout lines
        :rtype: int
        """
        return self._fatcnt


class BackgroundProcess(object):  # pylint: disable=R0902
    """a little util to spawn an executable and catch stdout / stderr via streams"""

    def __init__(self, cmd, cwd, sout, serr=None, **kwargs):  # pylint: disable=R1260
        r"""
        initialize and start command

        :param Union[list,str] cmd: full command line
        :param str cwd: working dir of command
        :param stream sout: where to log stdout to
        :param stream serr: where to log stderr to
        :param dict kwargs: additional arguments
        :keyword \**kwargs:
            * *outchk* (``bool``): stdout check if subprocess is still running - tweak to let e.g. EDP com server run
            * *logger* (``Logger``): which logger object to use
        """
        self._outchk = kwargs.pop("outchk", True)
        self._logger = kwargs.pop("logger", None)
        self._excode = None
        if MSWIN:
            kwargs["creationflags"] = CREATE_NEW_PROCESS_GROUP
        self._pdet = None
        self._ecode = -1
        self._starttm = time()
        try:
            if len(cmd) == 1:
                cmd = cmd[0]

            xargs = {k: kwargs.pop(k, v) for k, v in [("filter", None,), ("inverse", False,), ("callback", {},)]}
            if serr is None:
                serr = sout
                self._proc = Popen(cmd[0] if len(cmd) == 1 else cmd, cwd=cwd, stdout=PIPE, stderr=STDOUT, **kwargs)
                self._out = NonBlockingStreamReader(self._proc.stdout, sout, **xargs)
                self._err = None
            else:
                self._proc = Popen(cmd[0] if len(cmd) == 1 else cmd, cwd=cwd, stdout=PIPE, stderr=PIPE, **kwargs)
                self._out = NonBlockingStreamReader(self._proc.stdout, sout, **xargs)
                self._err = NonBlockingStreamReader(self._proc.stderr, serr, **xargs)

            try:
                self._pdet = Process(self._proc.pid)
            except Exception:
                pass

        except Exception as ex:
            if "The system cannot find the file" in str(ex):
                self._ecode = ERR_HPC_APPLICATION_NOT_LOCAL
            serr("exec error occured: {!s}".format(ex))
            self._proc = None

    def close(self, term=True, logger=None):
        """
        send wm_close

        read a bug: https://bugs.python.org/issue33245
        """
        if logger is None:
            logger = self._logger

        if self.running:
            if MSWIN:
                hwnds = self._get_hwnds_for_pid()
                if hwnds:
                    if logger:
                        logger.warning("...sending WM_CLOSE to %d handles", len(hwnds))
                    for hwnd in hwnds:
                        try:
                            # logger.info("window text: %d -> '%s'", hwnd, GetWindowText(hwnd))
                            PostMessage(hwnd, WM_CLOSE, 0, 0)
                        except Exception as ex:
                            if ex.args != (1400, 'PostMessage', 'Invalid window handle.',):  # already closed
                                raise
                else:
                    self._kill_childs(self._pdet, term, logger)
            else:  # pragma: nocover
                self._kill_childs(self._pdet, term, logger)

    def _kill_childs(self, proc, term, logger):  # pylint: disable=R1260
        """issue a func with args to all childs of proc and lastly to proc itself"""
        if MSWIN:
            funcs = [("send_signal", (CTRL_BREAK_EVENT,), "closing", logger.info if logger else None)]
        else:
            funcs = [("send_signal", (SIGINT,), "closing", logger.info if logger else None)]

        if term:
            funcs += [("terminate", (), "terminating", logger.warning if logger else None)]

        for func, args, desc, log in funcs:
            if proc and proc.is_running():
                for chp in [proc] + proc.children(True):
                    if log:
                        log("%s '%s' with PID %d ...", desc, chp.name(), chp.pid)
                    try:
                        getattr(chp, func)(*args)
                    except NoSuchProcess:
                        if logger:
                            logger.info("process %d already died", chp.pid)

                wtm = time() + EXIT_GRACE_TIME
                while proc.is_running() and time() < wtm:
                    try_sleep(0.333)
                if not proc.is_running():
                    if logger:
                        logger.info("process ended")
                    break

        # clean up, we don't mind more
        # self._proc = None
        self._ecode = ERR_OK

    def _get_hwnds_for_pid(self):
        """
        get HWNDs from PID
        taken essencially from http://timgolden.me.uk/python/win32_how_do_i/find-the-window-for-my-subprocess.html
        """
        def _callback(hwnd, hwnds):
            """CB"""
            if IsWindowEnabled(hwnd):
                _, found_pid = GetWindowThreadProcessId(hwnd)
                if found_pid == self.pid:
                    hwnds.append(hwnd)
            return True

        hwnds = []
        if self.pid:
            EnumWindows(_callback, hwnds)
        return hwnds

    @property
    def running(self):
        """
        :return: indication whether process is running
        :rtype: bool
        """
        if self._proc:
            return self._proc.poll() is None or (self._outchk and self._out.running)

        return False

    def wait(self, timeout=inf):
        """wait until process finishes"""
        if timeout != inf:
            timeout += time()

        while time() < timeout and self.running:
            try_sleep(1.)

        return self.running

    @property
    def app(self):
        """
        :return: the app itself
        :rtype: `Process`
        """
        return self._proc

    @property
    def proc(self):
        """
        :return: process instance
        :rtype: ``Process``
        """
        return self._pdet

    @property
    def pid(self):
        """
        :return: PID of process
        :rtype: int
        """
        if self._proc is None:
            return None
        return self._proc.pid

    @property
    def exitcode(self):
        """
        :return: exit code of application
        :rtype: int
        """
        if self._excode is not None:
            return self._excode

        if self._proc:
            return self._proc.poll()
        return self._ecode

    @exitcode.setter
    def exitcode(self, value):
        """overwrite the real exitcode"""
        self._excode = value

    @property
    def prn_lines(self):
        """
        :return: lines being printed
        :rtype: int
        """
        lns = 0
        if self._err:
            lns += self._err.prn_lines

        return self._out.prn_lines + lns

    @property
    def fatal_cnt(self):
        """
        :return: lines being printed
        :rtype: int
        """
        cnt = 0
        if self._err:
            cnt += self._err.fatal_cnt

        return self._out.fatal_cnt + cnt

    @property
    def wall_time(self):
        """
        :return: wall / real time
        :rtype: float
        """
        if self._proc is None or self._out is None or self._out.stoptm is None:
            return 0.

        return self._out.stoptm - self._starttm


class WrapProc(object):
    """wrap execution(s)"""

    def __init__(self, wrapers, logger, streams, hpc):  # pylint: disable=R0912,R1260
        """init and start all executables..."""
        self._logger = logger
        self._cmp, self._wflag = None, True
        self._wrappers, self._loggers = [], []
        self._failed = None

        if isinstance(wrapers, StringTypes):
            wrapers = {"cmd": wrapers}
        elif isinstance(wrapers, list):
            for i, v in enumerate(wrapers):
                if isinstance(v, StringTypes):
                    wrapers[i] = {"cmd": v}
        if isinstance(wrapers, dict):
            wrapers = [wrapers]

        for exe in wrapers:
            clst = exe.get("cmd", "").split()
            if clst:  # extract name for logger
                cmd = replace_env_vars(hpc, [exe.pop("cmd")])[0]
                if clst[0].endswith(".py"):
                    cmd = "python -u " + cmd

                # setup logger and start process
                self._logger.info("starting wrapper '%s' ...", cmd)
                wlog = get_logger(splitext(basename(clst[0]))[0] + ":", streams, "[%d] " % (len(self._wrappers) + 1))
                self._loggers.append(wlog)

                cwd = exe.pop("cwd") if "cwd" in exe else None
                tout = min(MAX_TIME_WATCH / 2, exe.pop("timeout") if "timeout" in exe else (MAX_TIME_WATCH / 2)) * 3600
                cbfnc = {}

                if exe.get("waitfor"):
                    txt = exe.pop("waitfor")
                    cbfnc[recomp(txt)] = (self._cbwaiter, txt,)
                if exe.get("erroron"):
                    txt = exe.pop("erroron")
                    cbfnc[recomp(txt)] = (self._cberror, txt,)

                pproc = BackgroundProcess(cmd, cwd, wlog.info, logger=wlog, callback=cbfnc, **exe)

                if cbfnc:
                    mxwt = tout + time()
                    while self._wflag and pproc.running and mxwt > time():
                        sleep(0.5)

                    if self._wflag and mxwt > time():
                        self._failed = "max timeout of {:.0f}s for wrapper reached to wait for indication!".format(tout)

                if not pproc.running:
                    self._failed = "wrapper not running any longer, or didn't start at all!"

                self._wrappers.append(pproc)

                if self._failed:
                    break
            else:
                self._failed = "empty wrapper (no cmd) specified!"

    def __enter__(self):
        """:return self"""
        return self

    def __exit__(self, etype, exval, _):
        """get out: close apps"""
        for i in range(len(self._wrappers) - 1, -1, -1):
            wrp = self._wrappers[i]
            if wrp.running:
                wrp.close(logger=self._logger)
            else:
                self._logger.info("%s not running any more!", self._loggers[i].name)

        if isinstance(exval, HpcError) and exval.error == ERR_APPLICATION_WRAPPER:
            self._logger.error(exval.message)
            return True
        return False

    close = __exit__

    @property
    def running(self):
        """return if all wrappers are still running"""
        return all([i.running for i in self._wrappers])

    def __len__(self):
        """
        :return: number of wrappers
        :rtype: int
        """
        return len(self._wrappers)

    @property
    def failed(self):
        """
        :return: failure desc, if any
        :rtype: str
        """
        return self._failed

    def _cbwaiter(self, line):
        """call back the waiter function"""
        if self._wflag:
            self._logger.info("stdout line detected to continue: '%s'.", line)
            self._wflag = False

    def _cberror(self, line):
        """call back for errors"""
        if self._wflag:
            self._logger.error("stdout line detected to break: '%s'.", line)
            self._failed = line
            self._wflag = False


class LogTimer(Timer):
    """derived for logging"""

    def __init__(self, *args, **kwargs):
        """overload"""
        Timer.__init__(self, *args, **kwargs)
        self.timed_out = False

    def run(self):
        """run it"""
        self.finished.wait(self.interval)
        if not self.finished.is_set():
            self.timed_out = True
            self.function(*self.args, **self.kwargs)
        self.finished.set()


class CloudBlob(object):
    """encapsulates Win and Linux parts"""

    def __init__(self, conn, cont, blob):
        """set up the blob"""
        self._blob = BlobClient.from_connection_string(conn, cont, blob)
        # else:
        #     self._blob = BlobClient(connection_string=conn)
        #     self._xargs = {"container_name": cont, "blob_name": blob}

    @property
    def properties(self):
        """return the props"""
        return self._blob.get_blob_properties()
        # return self._blob.get_blob_properties(**self._xargs).properties

    @property
    def fsize(self):
        """return the file size"""
        return self.properties["size"]
        # return self.properties.content_length

    def download(self, fpath):
        """download blob to fpath"""
        with open(fpath, "wb") as blob:
            strm = self._blob.download_blob()  # offset=0, length=16384)
            strm.readinto(blob)
        # else:
        #     self._blob.get_blob_to_path(file_path=fpath, **self._xargs)


def timeit(func):
    """decorate to measure function calls"""
    @wraps(func)
    def _timeit(*args, **kwargs):

        frmt_str = kwargs.pop("timeit_frmt") if "timeit_frmt" in kwargs else None
        startm = default_timer()
        try:
            return func(*args, **kwargs)
        finally:
            if frmt_str:
                print(frmt_str.format(default_timer() - startm))
    return _timeit
