"""
job_sim.py
----------

job_sim module for hpc.

**User-API Interfaces**

    - `hpc` (complete package)
    - `job_sim` (this module)
"""
# pylint: disable=C0413,C0412,E1101
# - import Python modules ---------------------------------------------------------------------------------------------
from sys import platform
from shutil import rmtree
if platform == "win32":
    from os import makedirs
    from shutil import copytree
    from win32file import CreateSymbolicLink
    from pywintypes import error

    def duplicate(src, dst):
        """compat to os.link for windows to create a symlink"""
        try:
            CreateSymbolicLink(dst, src, 1)
        except error:  # user doesn't seem to have full rights, so, let's copy instead
            copytree(src, dst)
else:
    from os import makedirs, link as duplicate

from os.path import join, exists

# - import HPC modules ------------------------------------------------------------------------------------------------
from .job import Job
from ..core.path import on_rm_error
from ..core.hpc_defs import JobState, JobUnitType


# - classes -----------------------------------------------------------------------------------------------------------
class JobSim(Job):
    """
    .. inheritance-diagram:: hpc.JobSim

    The JobSim class can be used instead of the `Job` class to simulate
    a job submit on the HPC-Cluster on the local pc and test the first Task
    of the job in a simple way.

    **Following steps explain the workflow:**

    1. Replace in the submit script the `Job` class with `JobSim`
    2. Be sure you have a local folder called d:/data.
    3. JobSim will copy all needed test files to d:/data with the given jobname.
    4. Execute you submit script.
    5. Go to d:/data/1_JobName/1_Input and execute the test.bat file.
    6. The Job will executed exactly in the same way like on the HPC-Cluster
       The results will be copied to
       D:/data/_hpc_base/1_JobName/2_Output/_data
    7. Go to D:/data/_hpc_base/1_JobName/2_Output/T00001
       and check if the results are ok.
    8. If the results as expected, do a real submit on the HPC-Cluster
       in the Test-Queue.

    **1. Example**::

        # Import hpc
        import hpc

        #Connect to the HPC Server
        with hpc.JobSim(name='Training_Ping', project='Short_Test') as job:
            factory = hpc.TaskFactory(job)
            factory.create_task('ping 127.0.0.1')
    """

    def __init__(self, *args, **kwargs):
        r"""
        initialize HPC job

        :param \*args: *head_node*, *name* and *project* must be given, others are optional (kwargs)

        :keyword \**kwargs:
            * *head_node* (``str``): head node to use, default: Lindau production cluster
            * *name* (``str``): name of job
            * *project* (``str``): name of project to use
            * *template* (``str``): name of template
            * *priority* (``JobPriority``): initial priority, use int or JobPriority class
            * *unit* (``JobUnit``): job unit (JobUnit), can be either Node, Core or Socket
            * *notify_on_start* (``bool``): receive an email when job starts
            * *notify_on_completion* (``bool``): receive an email when job completes
            * *hold_time* (``datetime``): local date/time for first try to start job.
            * *depends* (``list``): job ID('s) this job should depend uppon
            * *bsig_check* (``bool``): check bsig outputs from MTS, default: True
            * *precmd* (``str``): prepare command to be executed after preparation is done
            * *relcmd* (``str``): release command to be executed before release is done
            * *robo_retry* (``int``): retry count for result copy back (starter)
            * *robo_wait* (``int``): wait time between those retries (starter)
            * *runas* (``str``): '<username>[:<password>] to run the job as (password is only needed for first time)
        """
        Job.__init__(self, *args, sim=True, **kwargs)

    def _submit(self):
        """submit!"""
        if self._venv:
            self._handle_venv(self._scheduler.net_in_path)

        self._update_db(self._update_db()[1])
        if self._dbase is not None:
            self._dbase.close()

        # clean up job folder and link / copy all to WS data path
        path = join(self._scheduler.work_path, self._scheduler.job_folder_name)
        if exists(path):
            rmtree(path, onerror=on_rm_error)
        makedirs(path)
        duplicate(self._scheduler.net_in_path, self._scheduler.client_in_path)

        self._logger.info("commit finished, start using %s.", join(self._scheduler.client_in_path, "test.bat"))
        return True

    def wait_until_finished(self, **kwargs):
        """
        Start the local execution of test.bat and wait until it is finalized, return the final job's state

        Set job type to Core to run as many tasks in parallel as your machine provides.
        """
        state = JobState.All

        if self._submitted:
            from multiprocessing import Pool, Manager, cpu_count  # pylint: disable=C0415

            cpus = cpu_count()
            mpl = Pool({JobUnitType.GPU: 1, JobUnitType.Node: 1, JobUnitType.Socket: cpus // 2,
                        JobUnitType.Core: cpus}[int(self._scheduler.unit)])
            man = Manager()
            snake = man.Queue(len(self))
            mpl.map(_starter, [(str(i), self._scheduler.client_in_path, kwargs.get("fastwatch", False), snake,)
                               for i in range(1, len(self) + 1)])

            state = JobState.Finished
            while not snake.empty():
                if snake.get_nowait() != state:
                    state = JobState.Failed
                    break

        return state


# - functions ----------------------------------------------------------------------------------------------------------
def _starter(args):
    """
    start a task

    :param list args: task id, input path and Queue
    """
    taskid, in_path, fastwatch, snk = args
    from ..starter import AppStarter  # pylint: disable=C0415,R0401

    with AppStarter(cwd=in_path, sched=None, fastwatch=fastwatch) as starter:
        snk.put(JobState.Finished if starter.execute(taskid=taskid, verblevel=1) == 0 else JobState.Failed)
        starter.finalize()
