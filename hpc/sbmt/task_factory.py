"""
hpc/task_factory
----------------

TaskFactoryMTS Module for Hpc.

**User-API Interfaces**

    - `hpc` (complete package)
    - `TaskFactory` (this module)
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from os.path import join
from six import iteritems, PY2
if PY2:
    from types import StringTypes
else:
    StringTypes = (str,)

# - import HPC modules ------------------------------------------------------------------------------------------------
from ..sched.sched_defs import INPUT_PATH, OUTPUT_PATH
from ..core.error import HpcError
from ..core.tds import PRODUCTION_HEADS
from ..core.dicts import TASK_DEFAULTS, USR_EXMAP
from ..bpl import Bpl
from .subtask_factory import SubTaskFactory

# - defines ------------------------------------------------------------------------------------------------------------
RUNTM = "runtime"


# - classes -----------------------------------------------------------------------------------------------------------
class TaskFactory(object):
    """
    **Create Tasks based on "normal" commandline call.**

    - Typical usage is first to set all information, which is the same for
      all Tasks. (environment-variables, working-dir, ....)
    - After that, multiple calls of the "create_task" - for the real
      Task creation.

    *Example:*::

        # Import hpc
        import hpc

        #connect to HPC cluster
        job = hpc.Job(name="Training_Ping", project="Short_Test")

        factory = hpc.TaskFactory(job)
        factory.create_task('ping 127.0.0.1')
        job.submit()

    **Creates Tasks based on SubTasks.**

    - Tasks can be the SubTaskIndex from a SubTaskFactory Created Task.

    *Example:*::

        # Import hpc
        import hpc

        # connect to local (pseudo) "HPC" cluster
        job = hpc.JobSim(name="Training_SubTask", project="Short_Test")

        # Create the main task factory
        factory = hpc.TaskFactory(job)

        # Create TaskFactory
        ping1 = hpc.SubTaskFactory(job)
        ping2 = hpc.SubTaskFactory(job)

        sub1 = ping1.create_task("ping.exe 127.0.0.1")

        counter = 0
        for idx in range(0, 10):
            sub2 = ping2.CreateTask("ping.exe 127.0.0.1 -n%d" % counter)
            counter += 1
            factory.create_task(sub1 + sub2)

        job.submit()
    """

    def __init__(self, hpc, **kwargs):
        r"""
        init task factory

        :param hpc.Job hpc: link to job
        :param dict kwargs: see below
        :keyword \**kwargs:
            * *name* (``str``): name of task
            * *io_watch* (``bool``): whether watchdog shall watch io traffic
            * *cpu_watch* (``bool``): whether watchdog shall track cpu usage
            * *time_watch* (``float``): whether watchdog shall monitor time [h]
            * *prn_watch* (``bool``): whether watchdog shall watch the printout
            * *time_factor* (``float``): default 16 x recording length
            * *skipon* (``list``): continue on certain exitcodes of previous subtask, e.g. [-302, -402]
            * *wrapexe* (``dict``): executables wrapped around all sub task, e.g.
                [{"cmd": "foobar.exe -o1 -o2", "cwd": None, "timeout": 0.5,
                  "waitfor": "wait for this on stdout and continue", "erroron": "wait for this on stdout and fail",}]
            * *cncl_cmd* (``str``): cancel command to be executed when task is canceled, max runtime: 60s
            * *exit_map* (``dict``): map real exit code to user defined
            * *folders* (``list[str]``): list of extra folder to create on WSN at start of (sub)task run
            * *env* (``dict``): environment variables to set for the task
            * *notify_on_start* (``bool``): receive an email when job starts
            * *notify_on_completion* (``bool``): receive an email when job completes
            * *out_dir* (``str``): output directory, if it should be different than the task folder or _data
            * *log_dir* (``str``): log directory, if it should be different than the task folder \\ log
        """
        assert hpc.job_name is not None, "name of job is mandatory!"
        self._hpc = hpc
        self._name = kwargs.get('name', None)
        self._runtime = kwargs.get(RUNTM, None)
        self._env_data = kwargs.pop("env", {})
        self._tjenv = {k: kwargs.get(k, d) for k, d in iteritems(TASK_DEFAULTS) if kwargs.get(k, d) != d}
        for k in ("wrapexe", USR_EXMAP,):  # take them out
            if k in kwargs:
                kwargs.pop(k)

        if "stf" in kwargs:
            self._stf = kwargs["stf"]
        else:
            self._stf = SubTaskFactory(hpc, **kwargs)

    def set_cur_work_dir(self, working_dir):
        """
        SetCurWorkingDir set the current working dir for your process.
        Per default the current working directory is set to
        D:/data/%JobName%/1_Input.

        :note:
            - %JobName% will be replaced with the real JobName.
            - %TaskName% will be replaced with the real TaskName.

        :param working_dir:   Name of the Environment Variable.
        :type working_dir:    string
        """
        self._stf.set_cur_work_dir(working_dir)

    def add_environment_variable(self, key, value):
        """
        With this method, you are able to set multiple Environment variables
        for your Task. You can call this method several times, with different
        key/value - pairs. All of them will be set before your task
        starts with execution.

        :param key:   Name of the Environment Variable.
        :type key:    string
        :param value: Value which is used to set the Environment Variable.
        :type value:  string
        """
        self._stf.add_environment_variable(key, value)

    def activate_app_watcher(self, active):
        """
        wether to (de)activate the watcher: deprecated

        The ApplicationWatcher normal checks the real Task, if the task is
        still running. He does this with looking on the cpu-load and the io
        of the process. Is the task under the limit of the minimum cpu-load
        and/or io, he will kill the process to free the node again.

        Sometime it is necessay, to deactivate this, because the
        ApplicationWatcher kills the process in a unwanted situation.
        For this you can call this Method.

        :param bool active: flag if Application Watcher shall be deactivated or not.
        """
        self._stf.activate_app_watcher(active)

    def _create_task_with_subtask(self, subtask, **kwargs):
        """
        create a HPC task based on multiple subtasks.

        :param int subtask: sub tasks id's or command
        :param dict kwargs: misc more params
        :return: task info being created
        :rtype: dict
        :raises HpcError: on any problems
        """
        nargs = dict(**kwargs)
        taskno = len(self._hpc.sched) + 1
        if taskno > self._hpc.maxtasks and self._hpc.head_node in PRODUCTION_HEADS:
            raise HpcError("maximum number of tasks reached: {}!".format(self._hpc.maxtasks))

        if self._hpc.loglevel > 1:
            if isinstance(subtask, list):
                self._hpc.logger.info("adding subtask%s %s as task %d", "" if len(subtask) == 1 else "s",
                                      ", ".join([str(i) for i in subtask]), taskno)
            else:
                self._hpc.logger.info("adding task %d", taskno)

        if self._hpc.starter.endswith(" --id"):
            starter = "{} {}.{}.{}".format(self._hpc.starter, self._hpc.head_node, self._hpc.jobid, taskno)
        else:
            starter = self._hpc.starter

        # create HPC task
        name = nargs.pop('name', self._name)
        name = ("T{:0>5d}".format(taskno) if not name else name[:128].replace(' ', '_'))

        tjenv = dict(self._tjenv)
        tjenv.update({k: v for k, v in iteritems(nargs)
                      if k in TASK_DEFAULTS and v != tjenv.get(k, TASK_DEFAULTS[k])})
        for k in tjenv:
            nargs.pop(k, None)

        # add task information to sqlite db for app_starter
        if isinstance(subtask, int):
            subtask = [subtask]
        self._hpc.env.add(taskno=taskno, stk=subtask, **tjenv)

        basepath = self._hpc.join(self._hpc.sched.work_path, self._hpc.sched.job_folder_name, OUTPUT_PATH, name)
        env_data = dict(self._env_data)
        env_data.update({"TaskName": name, "TaskID": taskno, "HPCTaskTmpFolder": self._hpc.join(basepath, 'tmp'),
                         "HPCTaskDataFolder": self._hpc.join(basepath, "data")})
        env_data.update(nargs.get("env", {}))

        cwd = nargs.get("cwd", self._hpc.join(self._hpc.sched.work_path, self._hpc.sched.job_folder_name, INPUT_PATH))
        cmd = starter
        if "adm" in nargs and self._hpc.template == "Admin":
            cmd = nargs.pop("adm")
        if self._runtime and RUNTM not in nargs:
            nargs[RUNTM] = self._runtime
        if not any([i in nargs for i in ["min_nodes", "max_nodes", "min_cores", "max_cores",
                                         "min_sockets", "max_sockets", "sockets"]]):
            nargs["resources"] = 1

        return self._hpc.sched.append_task(envs=env_data, depends=nargs.pop("depends", None),
                                           taskno=taskno, command_line=cmd, work_directory=cwd, name=name, **nargs)
        # stderr=join(self._hpc.sched.net_out_path, "T{:05d}".format(taskno), "status.url"))

    def create_task(self, cmd, **kwargs):
        """
        Create a new task.

        :param str cmd: Commandline for the executable to start.
        :param dict kwargs: misc more args, see create_task method of subtask_factory for more info...
        :return: info about the task
        :rtype: dict
        """
        subtaskmode = True

        try:
            if isinstance(cmd[0], StringTypes):
                subtaskmode = False
        except Exception:
            subtaskmode = False

        if subtaskmode:
            return self._create_task_with_subtask(cmd, **kwargs)

        # create sub-task for cmd call
        return self._create_task_with_subtask(self._stf.create_task(cmd, **kwargs), **kwargs)

    def create_tasks(self, bpl_file_path, cmd="", **kwargs):
        r"""
        Create multiple tasks based on a given \*.bpl file.
        %recfile% inside 'cmd' keyword will be replaced by iterated recording from bpl
        Sections will not be taken into consideration as for create_tasks of task factory mts...

        :param str bpl_file_path: bpl file name
        :param str cmd: cmd to be used
        :param dict kwargs: misc more args
        :return: info of details being added
        :rtype: list[dict]
        """
        rec = kwargs.get("recording")
        idx = cmd.lower().find("%recfile%")
        tasks = []
        with Bpl(bpl_file_path) as bpl:
            for item in bpl:
                if item.is_simple:
                    rfn = item.filepath[0]
                else:
                    self._hpc.bpl_cnt += 1
                    rfn = join(self._hpc.sched.net_in_path, 'bpl', "rec{:05d}.bpl".format(self._hpc.bpl_cnt))
                    item.save(rfn)

                if rec is True:
                    kwargs["recording"] = rfn
                if idx >= 0 and cmd:
                    newcmd = cmd[:idx] + rfn + cmd[idx + 9:]
                elif cmd:
                    newcmd = cmd
                else:
                    newcmd = rfn

            tasks.append(self.create_task(newcmd, **dict(kwargs)))

        return tasks
