"""
subtask_factory.py
------------------

SubTaskFactory Module for Hpc.

**User-API Interfaces**

    - `hpc` (complete package)
    - `SubTaskFactory` (this module)
"""
# pylint: disable=E1101,W0201
# - import Python modules ----------------------------------------------------------------------------------------------
from sys import maxsize
from os import getenv
from os.path import basename, getsize
from re import match, split as resplit
from collections import OrderedDict
from six import iteritems
from numpy import array as nparray, int64

# - import HPC modules -------------------------------------------------------------------------------------------------
from ..core.error import HpcError
from ..core.tds import HPC_STORAGE_MAP, AZR_BLOB_STX, AZR_CONN_STR, AZR_ACC_KEYS, replace_server_path
from ..core.dicts import WRAP_EXE, USR_EXMAP
from ..core.app_utils import CloudBlob, MAX_TIME_WATCH
from ..core.logger import deprecated
from ..rdb.base import basepath, serverpath, crc
from ..bpl import Bpl

# - defines ------------------------------------------------------------------------------------------------------------
SIZE_TO_TIMEOUT = 1.


# - classes ------------------------------------------------------------------------------------------------------------
class CmdHelper(object):
    """
    Helper Class to handle in a easy way the cmd-line arguments from the different applications.
    Main goal is to convert the cmd-line string into a list of items.
    """

    def __init__(self, cmd, linux):
        """
        init me with

        :param str cmd: command line
        :param bool linux: if we have a linux command
        """
        self._cmd = cmd
        self._linux = linux

    @property
    def command(self):
        """
        :return: actual command
        :rtype: str
        """
        return self._cmd

    @property
    def cwd(self):
        """return working directory"""
        return None

    def get_cmd_list(self, cmd_asis=False):  # pylint: disable=R1260
        """
        convert the internal set cmd-line string to to a list of arguments.

        :return:          List of Arguments
        :rtype:           list[string,...]
        """
        if self._cmd is None:
            return None

        if cmd_asis:
            return self._cmd if isinstance(self._cmd, list) else [self._cmd]

        # parse the cmdline and create a list out of it
        arg = []

        in_string = False
        cmd = ''
        for char in self._cmd:
            if char == '"':
                in_string = not in_string
                # if cmd_asis:
                #     cmd += char
            elif char == ' ' and not in_string:
                arg.append(cmd)
                cmd = ''
            else:
                cmd += char
        # append at end of line
        if cmd != '':
            arg.append(cmd)

        # don't use / accept python at start
        if self._linux:
            if arg[0][-3:] == '.py':
                arg.insert(0, self._linux)
                arg.insert(1, '-u')
        else:
            if basename(arg[0]) in ["python", "python.exe"]:
                arg[0] = "python.exe"
            elif arg[0][-3:] == '.py':
                arg.insert(0, "python.exe")
                arg.insert(1, '-u')

        return arg


class SubTaskFactory(object):  # pylint: disable=R0902
    """
    - Specialized class for creating Hpc SubTasks which are based
      on "normal" commandline call.
    - Typical usage is first to set all information, which is the same for
      all Tasks. (environment variables, working dir, ....)
    - After that, multiple calls of the "create_task"
      -> for the real Task creation.
    """

    def __init__(self, hpc, **kwargs):
        r"""
        init subtaskfactory

        :param hpc.Job hpc: link to job
        :param dict kwargs: see below
        :keyword \**kwargs:
            * *head_node* (``str``): head node to use, default: Lindau production cluster
            * *io_watch* (``bool``): whether watchdog shall watch io traffic
            * *cpu_watch* (``bool``): whether watchdog shall track cpu usage
            * *time_watch* (``float``): whether watchdog shall monitor time [h]
            * *prn_watch* (``bool``): whether watchdog shall watch the printout
            * *time_factor* (``float``): default 16 x recording length
            * *skipon* (``list``): continue on certain exitcodes of previous subtask, e.g. [-302, -402]
            * *wrapexe* (``str``): executable wrapped around each sub task
            * *exit_map* (``dict``): map real exit code to user defined
            * *folders* (``list[str]``): list of extra folder to create on WSN at start of (sub)task run
            * *env* (``list``): list of lists containing environment variables to set when running all subtasks
            * *skip* (``list``): skip this amount of subtasks when [Finished, Failed]
        """
        self._hpc = hpc
        self._cwd = None
        self._simcfg = OrderedDict()
        self._playsections = False

        for k, o, d in (("_iowatch", "io_watch", not self._hpc.linux,), ("_cpuwatch", "cpu_watch", True,),
                        ("_timewatch", "time_watch", 0.), ("_prnwatch", "prn_watch", False,),
                        ("_timefactor", "time_factor", 16.,), ("_errorlevel", "errorlevel", self._hpc.errorlevel,),
                        ("_local_rec", "local_rec", False,), ("_type", "mode", "APP",), ("_wrapexe", WRAP_EXE, [],),
                        ("_envdata", "env", []), ("_exitmap", USR_EXMAP, {}),
                        ):
            setattr(self, k, kwargs.get(o, d))

    def _create_task(self, cmd_helper, **kwargs):  # pylint: disable=R0912,R0914,R0915,R1260
        """
        create a new task (internal)

        :param CmdHelper cmd_helper: CommandHelper
        :param dict kwargs: misc args from above
        :return: created SubTaskList
        :rtype: list[int]
        :raises HpcError: if azure libs are not found
        """
        tmwatch = float(kwargs.get("time_watch", self._timewatch))
        tmfact = float(kwargs.get("time_factor", self._timefactor))
        recording = kwargs.get("recording", None)
        recinfo = kwargs.get("recinfo")
        recmap = kwargs.get("rec_map", True) if recording is not None else False
        rectms, recdiff = [], kwargs.get("rec_diff", 10)
        task = len(self._hpc.sched) + 1
        if task not in self._hpc.taskmeas:
            self._hpc.taskmeas[task] = nparray([0, 0], dtype=int64)

        if recinfo:  # use provided info [<size of rec>, <duration>], not caring about later adds
            if any([i > maxsize for i in recinfo]):
                self._hpc.logger.warning("recinfo too big!")
            self._hpc.taskmeas[task] += [min(maxsize, i) for i in recinfo]

        cnt, tms, measid, rec, rsz = -1, [], [], None, 0.
        if recording is not None and self._hpc.base_db is not None:  # pylint: disable=R1702
            for cnt, rec in enumerate(self._split_rec_name(recording)):
                try:
                    totms = True
                    res = self._hpc.base_db("SELECT MEASID, NVL(BEGINABSTS, 0) BA, NVL(ENDABSTS, 0), FILESIZE, PARENT, "
                                            "STATUS "
                                            "FROM DMT_FILES WHERE CRC_NAME = :crc AND SERVERSHARE = :srvs "
                                            "AND BASEPATH = :bph AND NVL(BEGINABSTS, 0) <= NVL(ENDABSTS, 0) "
                                            "ORDER BY BA DESC", crc=crc(rec[1].lower()),
                                            srvs=serverpath(rec[1].lower()), bph=basepath(rec[1].lower()))

                    if len(res) > 0 and len(res[0]) > 0:
                        res = list(res[0])
                        measid.append(res[0])
                        tms = list(res[1:3])
                        rsz += res[3]
                        # do we have a parent?
                        if res[4] is not None:
                            par = self._hpc.base_db("SELECT NVL(BEGINABSTS, 0), NVL(ENDABSTS, 0), FILESIZE "
                                                    "FROM DMT_FILES WHERE MEASID = :meas", meas=res[4])
                            if len(par) > 0 and len(par[0]) > 0:
                                tms = list(par[0][0:2])

                        if res[5] != "transmitted":
                            self._hpc.logger.error("recording is marked '%s' in DB and might cause problems!", res[5])

                        if not self._playsections:  # it's weird, MTS config set's it to 0 if sections should be played
                            for sec in rec[2]:
                                rectms.append([sec[0] + (tms[0] if sec[2][0] else 0),
                                               sec[1] + (tms[0] if sec[2][1] else 0)])
                                if not (tms[0] <= rectms[-1][0] <= tms[1] and tms[0] <= rectms[-1][1] <= tms[1]
                                        and rectms[-1][0] < rectms[-1][1]):
                                    self._hpc.logger.warning("section times out of bounds: begin=%d, end=%d",
                                                             rectms[-1][0], rectms[-1][1])
                                totms = False

                        # save to local sqlite db
                        if recinfo:
                            res[1], res[2], res[3] = 0, recinfo[1], recinfo[0]
                        else:
                            self._hpc.taskmeas[task] += [res[3], res[2] - res[1]]

                        self._hpc.records.append({"measid": res[0], "beginabsts": res[1], "endabsts": res[2],
                                                  "filepath": rec[1], "filesize": res[3], "basepath": basepath(rec[1])})

                    if totms and len(tms) > 0:
                        if tms[1] - tms[0] == 0.:
                            tms[0], tms[1] = 0., res[2] * 0.25
                            self._hpc.logger.warning("recording times not available, assuming 0.25 times filesize!")
                        else:
                            rectms.append(tms)

                except Exception as _:  # in case of escape sequences (seen at unittest)
                    pass

            if cnt < 0:
                recmap = False
            elif cnt > 0:
                recording = None
            else:
                recording = rec[1]

        if not recinfo and recording and tmwatch == 0.:  # 16 x actual / ([us] * 1[h]) + about 12' for loading # pylint: disable=R1702
            for tms in rectms:
                tmwatch += tmfact * (tms[1] - tms[0])
            if tmwatch == 0.:
                if rsz > 0.:
                    self._hpc.logger.warning("recording duration inside DB is zero (0), "
                                             "assuming %.2f times filesize %dB!", SIZE_TO_TIMEOUT, rsz)
                else:
                    try:
                        mtc = match(AZR_BLOB_STX, recording)
                        if mtc:
                            cstr = AZR_CONN_STR.format(mtc.group("epp"), mtc.group("account"),
                                                       AZR_ACC_KEYS[mtc.group("account")], mtc.group("suffix"))
                            try:
                                cli = CloudBlob(cstr, mtc.group("container"), mtc.group("blob"))
                                rsz = cli.fsize
                            except Exception:
                                raise HpcError("please, upgrade your installation as azure_storage_blob not available!")
                        else:
                            rsz = getsize(recording)
                        self._hpc.logger.warning("assuming %.2f times filesize %dB!", SIZE_TO_TIMEOUT, rsz)
                    except Exception as ex:
                        self._hpc.logger.warning("size of recording couldn't be checked (%s)!",
                                                 str(ex).replace('\\\\', '\\'))
                tmwatch = rsz * SIZE_TO_TIMEOUT
            tmwatch = round(tmwatch / 3600000000 + 0.2, 2)

        if tmwatch > MAX_TIME_WATCH:
            self._hpc.logger.warning("time watch too high, limit of %.0f hours exceeded: %.1f!",
                                     MAX_TIME_WATCH, tmwatch)
            tmwatch = MAX_TIME_WATCH
        kwargs["time_watch"] = tmwatch

        wrap = kwargs.get(WRAP_EXE, self._wrapexe)
        if not isinstance(wrap, list):
            wrap = [wrap]

        xargs = {k: kwargs.get(n, d) for k, n, d
                 in (("iowatch", "io_watch", self._iowatch,), ("cpuwatch", "cpu_watch", self._cpuwatch,),
                     ("prnwatch", "prn_watch", self._prnwatch,), ("errorlevel", "errorlevel", self._errorlevel,),
                     (USR_EXMAP, USR_EXMAP, self._exitmap,),)}
        xargs.update({k: v for k, v in iteritems(kwargs)
                      if k in ["xlog", "skip", "skipon", "shell", "outchk", "mtscheck", "local_rec", "pass_ecode",
                               "replace_path", "bsig_check"]})

        cmd = cmd_helper.get_cmd_list(kwargs.get("cmd_asis", False))
        tno, dup = self._hpc.env.append(command=cmd, workdir=kwargs.pop("cwd", self._cwd), wrapexe=wrap,
                                        env=self._envdata, timewatch=tmwatch, recmap=recmap, simcfg=self._simcfg,
                                        recording=recording, measid=None if len(measid) != 1 else measid[0],
                                        rectms=rectms, recdiff=recdiff, app=self._type, **xargs)

        if self._hpc.loglevel > 1:
            self._hpc.logger.info("%sing subtask %d: %s%s", "us" if dup else "add", tno, " ".join(cmd) if cmd else "",
                                  " (arguments: {})".format(", ".join("{}={}".format(i, v) for i, v in iteritems(kwargs)
                                                                      if v is not None and i != "rec_map")))

        return [tno]

    @staticmethod
    def _split_rec_name(rec_file_path):
        """
        prepare file path for DB search

        :param str rec_file_path: path/to/recording
        :return: recording name and splitted name
        :rtype: list
        """
        if rec_file_path is None:
            return [[None]]
        recording = rec_file_path.strip()

        if recording[-4:].lower() == '.bpl':
            with Bpl(recording) as bpl:  # pylint: disable=E1129
                return [([i for i in resplit(r"\\|/", fnm) if i], fnm, [[i.start_ts, i.end_ts, i.rel]
                                                                        for i in rec.sectionlist],)
                        for rec in bpl for fnm in rec.filepath]
        else:
            return [([i for i in resplit(r"\\|/", recording) if i], replace_server_path(recording, True), [],)]

    @deprecated("please, use 'cwd' at init or create_task method!")
    def set_cur_work_dir(self, working_dir):
        """
        set the working dir for your process.
        default working directory is D:/data/%JobName%/1_Input.

        :note:
            - %JobName% will be replaced with the real JobName.
            - %TaskName% will be replaced with the real TaskName.

        :param str working_dir:   Name of the Environment Variable.
        """
        self._cwd = working_dir

    @deprecated("please, use 'env' (dict) option instead!")
    def add_environment_variable(self, key, value):
        """
        With this method, you are able to set multiple Environment variables
        for your Task. You can call this method several times, with different
        key/value - pairs. All of them will be set before your task
        starts with execution.

        :param str key: name of the Environment Variable.
        :param str value: value which is used to set the Environment Variable.
        """
        self._envdata.append([key, value])

    @deprecated("please, use io_watch and/or cpu_watch options instead!")
    def activate_app_watcher(self, value):
        """deprecate me on time!"""
        self._iowatch = self._cpuwatch = value

    def _check_server_url(self, recfn):
        r"""
        check if recording's file_path can be simulated on intended cluster, cross simulation is not allowed

        :param str recfn: File URL which must be used for MTS.
        :raises HpcError: in case of wrong imput file
        """
        if not self._hpc.job_sim and not self._local_rec and recfn.startswith('\\') and not getenv("HPC_STORE"):
            if not any([match(r"(?i)\\\\%s\\.*" % i, recfn) for i in HPC_STORAGE_MAP[self._hpc.head_node][0]]):
                raise HpcError(r'This input file {} is not available for cluster {}!'
                               .format(recfn, self._hpc.head_node))

    def create_task(self, cmd, **kwargs):
        r"""
        create a new task

        :param str|list cmd: command(line) for the executable to start.

        :keyword \**kwargs:
            * *time_watch* (``float``): max runtime for subtask [h]
            * *io_watch* (``bool``): whether watchdog shall watch io traffic
            * *cpu_watch* (``bool``): whether watchdog shall track cpu usage
            * *time_factor* (``float``): calculated time of recording * 16. is default
            * *recording* (``str``): full path to recording to be used later on
            * *mtscheck* (``bool``): check MTS log files for problems, default: False
            * *errorlevel* (``int``): which errorlevel to use for MTS reporting, 0-6, default 1
            * *rec_map* (``bool``): set it to False, when recording's usage should not be tracked
            * *rec_diff* (``float``): allowed difference [%] from calculated time of recording compared to bsig output
            * *wrapexe* (``str``): executable(s) which are wrapped around actual main call of e.g. MTS
            * *exit_map* (``dict``): map real exit code to user defined
            * *cmd_asis* (``bool``): set to true, if you don't want the app call to be manipulated by Popen
            * *replace_path* (``bool``): if set to True, do not replace any path's from command
            * *shell* (``bool``): use a shell for execution of a command
            * *env* (``dict``): additional environment data to be set when calling Popen for execution
            * *folders* (``list``): additional folders to create when task executes
            * *skipon* (``list``): skip this subtask if previous exits with one of those in list
            * *skip* (``list``): skip this amount of subtasks when [Finished, Failed]
            * *xlog* (``list``): extra list to log out during (sub)task execution

        :return: created SubTaskList
        :rtype: list[int]
        """
        return self._create_task(CmdHelper(cmd, self._hpc.linux and self._hpc.sched.exe), **kwargs)
