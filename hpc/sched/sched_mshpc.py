"""
sched_mshpc.py
--------------

Interface to MS HPC.
This Module reflects some scheduler interfaces from HPC into Python.
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from os import unlink
from os.path import join, dirname
from time import sleep, time
# from threading import Event
from tempfile import NamedTemporaryFile
from socket import gethostbyaddr
from six import iteritems

# - import HPC modules -------------------------------------------------------------------------------------------------
from ..core import LOGINNAME
from ..core.error import HpcError
from ..core.tds import server_path, resolve_alias, location, LOC_HEAD_MAP, HPC_STORAGE_MAP, DEVS
from ..core.hpc_defs import JobState, JobUnitType
from ..core.registry import WinReg, HKEY_CLASSES_ROOT as HKCR, HKEY_LOCAL_MACHINE as HKLM
from ..core.logger import deprecated
from .base import SchedulerBase


# - classes / functions ------------------------------------------------------------------------------------------------
class MsHpcScheduler(SchedulerBase):  # pylint: disable=R0902
    """
    Class, which reflects a bit of IScheduler Interface from Microsoft HPC.
    See http://msdn.microsoft.com/en-us/library/microsoft.hpc.scheduler.ischeduler(v=vs.85)
    """

    def __init__(self, headnode, **kwargs):  # pylint: disable=R0915,R1260
        """
        connect to scheduler and open / create a new job

        :param str headnode: name of head
        :param list kwargs: misc arguments for scheduler base
        :raises hpc.HpcError: e.g. when not being able to connect to Microsoft HPC scheduler
        :raises Exception: on unknown error
        """
        SchedulerBase.__init__(self, headnode, **kwargs)

        self._jattr.update({"retry_limit": "TaskExecutionFailureRetryLimit"})

        # self._state_event = Event()
        self._state_state = JobState.All
        self._location = next((k for k, v in iteritems(LOC_HEAD_MAP) if self._head_node in v), None)
        self._base_dir = server_path(self._head_node)

        # some exceptions: Sven, Cedrik, Mohan, Joachim and our HPC user
        if LOGINNAME not in DEVS:
            loc = location("(unknown)")
            if not self._location:  # or self._location not in [loc, X_SUBMIT_EXC.get(loc)]:
                raise HpcError("it's not allowed to submit a job from {} to {}!".format(loc, self._head_node))

        self._check_df()

        self._job, self._submitted = None, False

        try:  # good to start here: http://pythonnet.github.io/
            _import_hpcdll("Microsoft.Hpc.Scheduler.Scheduler")
            from Microsoft.Hpc.Scheduler import Scheduler  # pylint: disable=C0415,E0401
            from System import IntPtr  # pylint: disable=C0415,E0401
            self._hpc = Scheduler()
            self._hpc.Connect(gethostbyaddr(self._head_node)[0].split('.')[0])
            self._hpc.SetInterfaceMode(True, IntPtr.Zero)
            if self.template != 'Default':
                self.check_template()
            self._job = self._hpc.CreateJob()
            self._job.OnJobState += self._job_state
            self._job.Name = kwargs["name"]
            self._hpc.AddJob(self._job)
            self._jobid = self._job.Id
        except ImportError:  # fallback to older OCX integration
            from win32com.client import Dispatch  # pylint: disable=C0415
            from pythoncom import CoInitializeEx, COINIT_MULTITHREADED, com_error  # pylint: disable=C0415

            if HPC_STORAGE_MAP[self._head_node][2] == "2019":
                raise HpcError("please, install missing pythonnet library!")
            self._logger.warning("please, install pythonnet, we'll need it in short-term!")
            try:
                CoInitializeEx(COINIT_MULTITHREADED)
            except com_error:  # pragma: no cover
                pass

            try:
                with WinReg(HKLM, r"SOFTWARE\Classes\TypeLib\{C45D10A1-54E8-420B-A052-719D47EC7C16}") as wr:
                    ver = int(wr.keys()[0].split('.')[0])
                if ver != 5:  # 5 => HPC pack 2016, 2 => HPC pack 2012 (not supported any more)
                    raise HpcError("to submit to {}, you need HPC pack 2016 client utilities!"
                                   .format(self._head_node))

                self._hpc = Dispatch("Microsoft.Hpc.Scheduler.Scheduler")
                self._hpc.Connect(self._head_node)
                if self.template != 'Default':
                    self.check_template()
                self._job = self._hpc.CreateJob()
                self._job.Name = kwargs["name"]
                self._hpc.AddJob(self._job)
                self._jobid = self._job.Id
            except com_error as exc:  # pragma: no cover
                if exc.hresult == -2147221005:
                    raise HpcError("Microsoft HPC Client Components are not found, please install the correct version!")
                if exc.hresult == -2147352567 and self._head_node != "OTHER":
                    raise HpcError("Seems, you have no rights on that cluster or connection failed!")
                # elif exc.hresult != -2147352567:  # not connected
                raise
        except Exception as exc:  # pragma: no cover
            raise HpcError("MS HPC error: {} -> {}"
                           .format(getattr(exc, "get_HResult", lambda: getattr(exc, "error", 0))(),
                                   getattr(exc, "get_Message", lambda: getattr(exc, "msg", str(exc)))()))

        self.name = kwargs.get('name')

    def __str__(self):
        """
        :return: nice representation
        :rtype: str
        """
        return "<MS HPC scheduler: head={}, id={}, name={}>".format(self._head_node, self._jobid, self.name)

    def close(self):
        """close connection to scheduler"""
        if self._job:
            self._hpc.Close()
            self._job = None

    def submit(self, _prio, runas, dbase):  # pylint: disable=W0221
        """
        configure the job and finalize (submit) it

        :param hpc.JobPriority _prio: wished job priority
        :param str runas: <username>:<password>
        :param BaseDB dbase: database connection
        """
        # create xml file to be used to reconfigure HPC job
        raw_xml = self._to_xml().decode()
        with open(join(dirname(self._base_dir), "HPC_submit", "job",
                       "{}_{}.xml".format(self._head_node, self._jobid)), "w") as fp:
            fp.write(raw_xml)
        with NamedTemporaryFile(mode="w", prefix="hpc_", suffix=".xml", delete=False) as tf:
            tf.write(raw_xml)
        self._job.RestoreFromXml(tf.name)
        unlink(tf.name)

        # set some more attributes out of xml
        excl = []
        for k, v in iteritems(self._sattrs):
            if v:
                if k == "excluded_nodes":
                    excl.extend(v)
                if k == "min_hd_space":
                    sqx = "" if self._attr["unit"][1] in [JobUnitType.Node, JobUnitType.GPU]\
                        else "/ {}S".format(str(self._attr["unit"][1]).upper())
                    excl.extend([n[0] for n in dbase("SELECT NAME FROM HPC_SLAVE INNER JOIN HPC_NODE USING(NODEID) "
                                                     "WHERE NODENAME = :clus AND DTOTAL {} < :minhd ".format(sqx),
                                                     clus=self._head_node, minhd=v)])

        if excl:  # add some nodes to excluded list (cannot be done via xml)
            strcoll = self._hpc.CreateStringCollection()
            for n in set(excl):
                strcoll.Add(n)
            self._job.AddExcludedNodes(strcoll)

        # do the final commit
        self._job.Commit()
        self._hpc.SubmitJob(self._job, *(runas + ":").split(':')[:2])
        self._submitted = True

        # increase prio if possible, some people have more rights and can do, we we won't want
        # if prio > JobPriority.Lowest:
        #     for i in range(int(prio), 0, -1):
        #         try:
        #             self._job.Priority = i
        #             self._job.Commit()
        #             break
        #         except Exception as _:
        #             sleep(1.5)

    def check_template(self):
        """
        check if template is available

        :raises hpc.HpcError: if Default or non-existing template is being used
        """
        if self.template not in {i for i in self._hpc.GetJobTemplateList()} - {"Default"}:  # pylint: disable=R1721
            raise HpcError("error: template '{}' does not exist!".format(self.template))

    def cancel_job(self, message):
        """
        cancel specified job. here, we remove the job from the queue,
        but the job remains in the scheduler.

        :param str message: message to display at HPC Job Manager
        """
        self._hpc.CancelJob(self._job.Id, " " + message[:127])

    @property
    def jobstate(self):
        """
        :return: state of job
        :rtype: int
        """
        for _ in range(3):
            try:
                self._job.Refresh()
                break
            except Exception:
                sleep(0.222)

        state = self._job.State
        if state == JobState.Failed:  # pragma: no cover
            # Due an Microsoft HPC Bug it can happen that all basic tasks are done without Error and only
            # the Node Release Task is failed. This will be check here, and if this happens, the Error Code will be set
            # back to finished, even if it job is failed.
            task_list = self._job.GetTaskList(None, None, True)

            unreachable_error = False
            other_error = False
            for task in task_list:
                if task.ErrorMessage != '' or task.ExitCode != 0:
                    if task.ErrorMessage == 'Job failed to start on some nodes or some nodes became unreachable.':
                        unreachable_error = True
                    else:
                        other_error = True
                        break

            if other_error is False and unreachable_error is True:
                state = JobState.Finished

        return state

    def wait_until_finished(self, **kwargs):
        r"""
        wait until job finishes

        :keyword \**kwargs:
            * *timeout* (``int``): wait timeout [s]
        :return `JobState`: final state of job
        """
        # with HpcSched(self._head_node) as sch:
        #     state = sch.wait_until_finished(self._jobid, kwargs.get("timeout", 12 * 24 * 60 * 60), self._logger)
        # return state
        if self._submitted:
            timeout = kwargs.get("timeout", 12 * 24 * 60 * 60)
            self._logger.info("waiting until max (%s | finished | failed | canceled)....", "{:.0f}s".format(timeout))

            end_tm = time() + timeout
            while self._state_state not in (JobState.Finished, JobState.Failed, JobState.Canceled,) and time() < end_tm:
                sleep(2.9)
                # if not self._state_event.wait(end_tm - time()):
                #     break
                # self._state_event.clear()

        return self._state_state

    def _job_state(self, _src, args):
        """job state change handler"""
        self._state_state = int(args.NewState)
        # print("state: {} => {}".format(args.PreviousState, args.NewState))
        # self._state_event.set()
        self._logger.info("job state changed from %s to %s",
                          str(JobState(int(args.PreviousState))), str(JobState(int(args.NewState))))

    def _set_jattr(self, name, value):
        """set a job attribute"""
        setattr(self._job, name, value)


class HpcSched(object):
    """connection object encapsulating HPC Scheduler"""

    def __init__(self, head):
        """init this"""
        self._head = head.upper()

        self._sched = self._props = self._propid = None

    def __enter__(self):
        """
        initialize connection to an HPC scheduler using IScheduler interface from
        https://learn.microsoft.com/en-us/dotnet/api/microsoft.hpc.scheduler.ischeduler?view=hpc-sdk-5.1.6115

        :return: self
        :rtype: object
        :raise Exception: connection exception
        """
        try:
            _import_hpcdll("Microsoft.Hpc.Scheduler.Scheduler")
            from Microsoft.Hpc.Scheduler import Scheduler, Properties, PropId  # pylint: disable=C0415,E0401
            self._sched = Scheduler()
            self._sched.Connect(resolve_alias(self._head))
            self._props = Properties
            self._propid = PropId
        except Exception:
            self._sched = None
            print("    unable to connect to scheduler %s!" % self._head)
            raise

        return self

    def __exit__(self, *_args):
        """cleanup"""
        if self._sched:
            self._sched.Close()

    connect = __enter__

    close = __exit__

    @property
    def name(self):
        """
        :return: name of head
        :rtype: str
        """
        return self._head

    @property
    def props(self):
        """
        refer to https://docs.microsoft.com/en-us/dotnet/api/microsoft.hpc.scheduler.properties?view=hpc-sdk-5.1.6115
        for further information

        :return: MS-HPC scheduler properties
        :rtype: `Scheduler.Properties`
        """
        return self._props

    @property
    def propid(self):
        """refer to https://docs.microsoft.com/en-us/dotnet/api/microsoft.hpc.scheduler.propid?view=hpc-sdk-5.1.6115"""
        return self._propid

    def __getattr__(self, item):
        """
        :return: scheduler attribute
        :rtype: `Scheduler.__getattr__`
        """
        return getattr(self._sched, item)

    def __str__(self):
        """represet myself"""
        return "<HpcScheduler @ {}>".format(self._head)

    # def wait_until_finished(self, jobid, timeout=12 * 24 * 60 * 60, logger=None):
    #     r"""
    #     wait until job finishes
    #
    #     :param jobid int: id of job
    #     :keyword \**kwargs:
    #         * *timeout* (``int``): wait timeout [s]
    #     :return `JobState`: final state of job
    #     """
    #     logger.info("waiting until max(%s | finished | failed | canceled)....", "{:.0f}s".format(timeout))
    #
    #     job = self._sched.OpenJob(jobid)
    #     ostate, end_tm = job.State, time() + timeout
    #
    #     while int(job.State) not in (JobState.Finished, JobState.Failed, JobState.Canceled,) and time() < end_tm:
    #         sleep(12)
    #         job.Refresh()
    #         if job.State != ostate:
    #             logger.info("job state changed from %s to %s",
    #                         str(JobState(int(ostate))), str(JobState(int(job.State))))
    #             ostate = job.State
    #
    #     return int(job.State)


class HpcClus(object):
    """connection object encapsulating HPC Scheduler"""

    def __init__(self, head):
        """init this"""
        self._head = head.upper()

        self._clus = None

    def __enter__(self):
        """
        initialize connection to an HPC cluster using ICluster interface from
        https://learn.microsoft.com/en-us/dotnet/api/microsoft.computecluster.icluster?view=hpc-sdk-5.1.6115

        :return: self
        :rtype: object
        :raise Exception: connection exception
        """
        try:
            _import_hpcdll("Microsoft.ComputeCluster.Cluster")
            from Microsoft.ComputeCluster import Cluster  # pylint: disable=C0415,E0401
            self._clus = Cluster()
            self._clus.Connect(resolve_alias(self._head))
        except Exception:
            self._clus = None
            print("    unable to connect to scheduler %s!" % self._head)
            raise

        return self

    def __exit__(self, *_args):
        """cleanup"""
        if self._clus:
            self._clus.Close()

    connect = __enter__

    close = __exit__

    @property
    def name(self):
        """
        :return: name of head
        :rtype: str
        """
        return self._head

    def __getattr__(self, item):
        """
        :return: scheduler attribute
        :rtype: `Scheduler.__getattr__`
        """
        return getattr(self._clus, item)

    def __str__(self):
        """represet myself"""
        return "<HpcCluster @ {}>".format(self._head)


class MiniSched(HpcSched):
    """keep it backward compatible for a while backward"""

    @deprecated("please, use 'from hpc import HpcSched' in future!")
    def __init__(self, *args):
        """init me"""
        HpcSched.__init__(self, *args)


def _import_hpcdll(namespace):
    """import HPC .Net components"""
    try:
        with WinReg(HKCR, r"{}\CLSID".format(namespace)) as wr:
            basis = wr.get(None)
        with WinReg(HKCR, r"CLSID\{}\InprocServer32".format(basis)) as wr:
            basis = wr.get("CodeBase")
        assert basis[:8] == "file:///"
    except Exception:
        raise HpcError("seems, you're missing HPC pack client utilities installation!")

    from clr import AddReference  # pylint: disable=C0415
    AddReference(basis[8:])
