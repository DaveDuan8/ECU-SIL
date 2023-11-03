"""
base.py
-------

base class for local and MS HPC scheduler
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from sys import executable
from os import makedirs
from os.path import join, basename, dirname, normpath
from ntpath import dirname as ntdirname, join as ntjoin
from datetime import datetime
from xml.dom.minidom import Document
# from inspect import stack
from copy import deepcopy
from psutil import disk_usage
from six import iteritems

# - import HPC modules -------------------------------------------------------------------------------------------------
from ..version import VERSION
from ..core import UID_NAME
from ..core.convert import human_size
from ..core.dicts import DefDict
from ..core.error import HpcError
from ..core.logger import DummyLogger
from ..core.hpc_defs import JobState, JobUnitType, JobPriority, TaskType
from ..core.tds import LIN_EXE, PY_2_EXE, PY_36_EXE, PY_38_EXE, PY_310_EXE, HPC_STORAGE_MAP, resolve_mail, \
    validate_name
from .sched_defs import INPUT_PATH, OUTPUT_PATH, OUTPUT_DATA_PATH, \
    SHORT_TEST_RUNTIME, STD_TASK_RUNTIME, MAX_TASK_RUNTIME

# - defines ------------------------------------------------------------------------------------------------------------
STD_PATH = r"C:\Program Files\Microsoft HPC Pack {}\Bin\;C:\Program Files\Microsoft MPI\Bin\;C:\Windows;" \
           r"C:\Windows\system32;C:\Windows\System32\Wbem;C:\Windows\System32\WindowsPowerShell\v1.0\;" \
           r"C:\LegacyApp\Oracle\client19600_64\bin;C:\LegacyApp\Oracle\client19600_64;"

# r"C:\LegacyApp\Python27_64;C:\LegacyApp\Python27_64\Scripts;C:\LegacyApp\Python27_64\Library\bin;"
# r"C:\LegacyApp\Python27_64\Lib\site-packages\osgeo"
GEN_PATHS = ["Scripts", r"Library\mingw-w64\bin", r"Library\usr\bin", r"Library\bin",
             r"Lib\site-packages\pywin32_system32"]
PY_PATH = {PY_2_EXE: ["Scripts", r"Library\bin", r"Lib\site-packages\osgeo"],
           PY_36_EXE: GEN_PATHS,
           PY_38_EXE: GEN_PATHS,
           PY_310_EXE: GEN_PATHS}

STD_PY_VAR = {PY_2_EXE:
                  {"GDAL_DATA": r"C:\LegacyApp\Python27_64\Lib\site-packages\osgeo\data",
                   "GDAL_DRIVER_PATH": r"C:\LegacyApp\Python27_64\Lib\site-packages\osgeo\gdalplugins",
                   "KERAS_BACKEND": "cntk",
                   "CCP_TASK_NOTIFY": "CTRL_C"},
              PY_36_EXE:
                  {"GDAL_DATA": r"C:\LegacyApp\Python36\Lib\site-packages\osgeo\data",
                   "GDAL_DRIVER_PATH": r"C:\LegacyApp\Python36\Lib\site-packages\osgeo\gdalplugins",
                   "CCP_TASK_NOTIFY": "CTRL_C"},
              PY_38_EXE:
                  {"GDAL_DATA": r"C:\LegacyApp\Python38\Lib\site-packages\osgeo\data",
                   "CCP_TASK_NOTIFY": "CTRL_C"},
              PY_310_EXE:
                  {"GDAL_DATA": r"C:\LegacyApp\Python310\Lib\site-packages\osgeo\data",
                   "CCP_TASK_NOTIFY": "CTRL_C"},
              LIN_EXE:
                  {"CCP_TASK_NOTIFY": "CTRL_C"}
              }

TEMPL_EXC = "(Cluster|Short|WSN|Linux|MTS.?)_Test|Admin|DataMining|MeasDataCheck|IBEO|REF2KPI|LX_Fusion"

LOW_NET_SPACE = 20.  # in percent
NO_NET_SPACE = 500000000000  # 500 GB left over: nearly nothing!


# - classes ------------------------------------------------------------------------------------------------------------
class SchedulerBase(object):  # pylint: disable=R0902
    """meant to be base of all schedulers"""

    # __slots__ = ("_attr", "_eattr", "_tasks", "_exe", "_sim", "__dict__",)

    def __init__(self, headnode, **kwargs):
        """
        init scheduler base

        :param str headnode: name of ...
        :keyword dict kwargs: misc args
        """
        self._head_node = headnode.split('.')[0].upper()

        self._deprecated = {"parent_jobs": "depends"}

        # "user_name": "UserName"
        self._attr = {"version": ["Version", '3.000'], "name": ["Name", None], "project": ["Project", None],
                      "template": ["JobTemplate", "Default"], "priority": ["Priority", JobPriority(JobPriority.Lowest)],
                      "unit": ["UnitType", JobUnitType(JobUnitType.Socket)], "is_exclusive": ['IsExclusive', None],
                      "run_until_canceled": ["RunUntilCanceled", None], "fail_on_task": ["FailOnTask", None],
                      "email": ["EmailAddress", None], "notify_on_completion": ["NotifyOnCompletion", None],
                      "notify_on_start": ["NotifyOnStart", None], "node_groups": ["NodeGroups", None],
                      "min_cores": ["MinCores", None], "max_cores": ["MaxCores", None],
                      "min_node_cores": ["MinCoresPerNode", None], "max_node_cores": ["MaxCoresPerNode", None],
                      "min_memory": ["MinMemory", None],
                      "min_sockets": ["MinSockets", None], "max_sockets": ["MaxSockets", None],
                      "min_nodes": ["MinNodes", None], "max_nodes": ["MaxNodes", None],
                      "auto_calculate_min": ["AutoCalculateMin", True],
                      "auto_calculate_max": ["AutoCalculateMax", True],
                      "requested_nodes": ["RequestedNodes", None], "exit_codes": ["JobValidExitCodes", []],
                      "depends": ["ParentJobIds", []], "parent_jobs": [None, None], "hold_until": ["HoldUntil", None]
                      }
        self._tattrs = {
            "name": ["Name", None], "type": ["Type", TaskType.Basic],
            "runtime": ["RuntimeSeconds", "{:.0f}".format(STD_TASK_RUNTIME * 3600)],
            "command_line": ['CommandLine', None], "work_directory": ["WorkDirectory", None],
            "depends": ["DependsOn", None], "increment_value": ["IncrementValue", None],
            "required_nodes": ["RequiredNodes", None], "is_rerunable": ["IsRerunable", None],
            "is_exclusive": ["IsExclusive", None], "is_parametric": ["IsParametric", None],
            "start_value": ["StartValue", None], "end_value": ["EndValue", None],
            "min_sockets": ["MinSockets", None], "max_sockets": ["MaxSockets", None], "min_cores": ["MinCores", None],
            "max_cores": ["MaxCores", None], "min_nodes": ["MinNodes", None], "max_nodes": ["MaxNodes", None],
            "stdin": ["StdInFilePath", None], "stdout": ["StdOutFilePath", None], "stderr": ["StdErrFilePath", None]
        }
        self._jattr = {}

        kws = dict(kwargs)
        kws.pop("name", None)
        self._sattrs = {"excluded_nodes": None, "min_hd_space": None}

        self._sim = kwargs.get("sim", False)
        self._work_path = "/var/hpc" if kws.pop("linux") else "D:\\data"
        self._join = kws.pop("join")

        # extended terms / attributes
        self._eattr = {}
        self._mail = resolve_mail(UID_NAME)
        self._logger = kws.pop("logger", DummyLogger(True))
        self._hpcversion = kws.pop("version", VERSION)
        if kws.get("template"):
            self.template = kws.pop("template")

        self._tasks = []

        self._exe = kws.pop("exe", executable)
        if not self._exe.startswith(LIN_EXE) and self._exe not in STD_PY_VAR:
            self._logger.warning("pyexe=%s => unknown, falling back to %s!", self._exe, PY_36_EXE)
            self._exe = PY_36_EXE

        # to be able to set extra environment variables
        self._jenvs = {}
        self._venv = kwargs.pop("venv", False)
        self._hpc = None
        self._net_job_path = None
        self._runtime = SHORT_TEST_RUNTIME if self.template.lower() == "short_test" else STD_TASK_RUNTIME

        self.update(**kws)
        if kwargs.get("xargs"):
            self._runtime = min(kwargs["xargs"].pop("runtime", self._runtime), MAX_TASK_RUNTIME)
            self._tattrs["runtime"][1] = "{:.0f}".format(self._runtime * 3600)
            if "sockets" in kwargs["xargs"]:
                socks = kwargs["xargs"].pop("sockets")
                kwargs["xargs"]["min_sockets"] = kwargs["xargs"]["max_sockets"] = socks
                self._tattrs["min_sockets"][1] = self._tattrs["max_sockets"][1] = socks

            self.update(**kwargs["xargs"])

    def __enter__(self):
        """with ..."""
        return self

    def __exit__(self, *_):
        """end of block"""
        self.close()

    def close(self):
        """do nothing as we don't have anything"""

    def __getattr__(self, key):
        """try to grab from HPC first"""
        if key.startswith('_'):
            return object.__getattribute__(self, key)

        if key in self._deprecated:
            nkey = self._deprecated[key]
            self._logger.warning("method '%s' is deprecated, please use '%s' instead!!!", key, nkey)
            key = nkey

        if key in self._attr:
            return self._attr[key][1]

        key = "_{}".format(key)
        if not hasattr(self, key):
            raise AttributeError

        return object.__getattribute__(self, key)

    def __setattr__(self, key, value):  # pylint: disable=R0912,R0915,R1260
        """set a value"""
        # if key in self.__slots__:
        #     super(SchedulerBase, self).__setattr__(key, value)
        if key.startswith('_'):
            object.__setattr__(self, key, value)
            return

        if key in self._attr:
            if key == "name":  # specific action: check naming convention
                if value:
                    if self.name:
                        raise HpcError("ambiguous usage of 'name' param and create method usage!")
                    self._prepare_paths(value)

            elif key == 'unit':
                if int(value) == JobUnitType.GPU:  # special behaviour: Gpu mode
                    value = JobUnitType(JobUnitType.Socket)
                    self._eattr["gpujob"] = ["GPUJob", "True"]
                else:
                    value = JobUnitType(int(value))

            elif key == "priority":
                if isinstance(value, int):
                    value = JobPriority(value)

            elif key in ('notify_on_completion', 'notify_on_start') and value is True:
                if not self._mail:
                    self._logger.warning("user %s has no email address", UID_NAME)
                    return
                self._attr["email"][1] = self._mail

            elif key in ["parent_jobs", "requested_nodes", "hold_until", "depends"]:
                if key == "parent_jobs":  # old and deprecated, but take it here
                    key = "depends"
                elif key == "hold_until" and isinstance(value, datetime) and value < datetime.utcnow():
                    raise HpcError("'hold_until' date already past by, we cannot do that!")

                value = to_string(value)

            elif key.startswith("min_"):
                self._attr["auto_calculate_min"][1] = False
            elif key.startswith("max_"):
                self._attr["auto_calculate_max"][1] = False

            self._attr[key][1] = value
        elif key in self._eattr:
            self._eattr[key][1] = to_string(value)
        elif key in self._sattrs:
            self._sattrs[key] = value
        elif key in self._jattr:
            self._set_jattr(self._jattr[key], value)
        else:
            raise AttributeError(key)

    def update(self, **kwargs):
        """update several keys"""
        for k, v in sorted(kwargs.items()):  # we sort to get template setting b4 unit setting to ease things
            try:
                if k == "env":
                    self._jenvs.update(v)
                elif not k.startswith('_'):
                    setattr(self, k, v)
            except AttributeError:  # ignore silently as others from Job coming as well
                pass

    def append_task(self, **kwargs):  # pylint: disable=R0912,R1260
        """append a task with given arguments"""
        tattrs, tenvs = deepcopy(self._tattrs), {}
        if kwargs.get("is_exclusive", False):
            kwargs.pop("resources")
            kwargs["min_nodes"] = kwargs["max_nodes"] = 1

        for key, value in iteritems(kwargs):
            if key == "sockets":
                key = "min_sockets"

            if key == "resources":
                for i in ["min_nodes", "max_nodes", "min_cores", "max_cores", "min_sockets", "max_sockets"]:
                    if not tattrs[i][1]:
                        tattrs[i][1] = value
                continue
            if key == "envs":
                tenvs.update(value)
                continue
            if self._venv and key == "name" and value == "prepare":
                tenvs["PATH"] = self._env_path(dirname(self._exe))
                tattrs[key][1] = value
                continue

            if key not in tattrs or value is None:
                continue  # ignore silently
                # raise AttributeError(key)

            if key in ["stderr", "stdout"]:
                try:
                    makedirs(dirname(value))
                except Exception:
                    pass
            elif key == "type":
                if int(value) == TaskType.NodePrep:
                    value = 'NodePrep'
                elif int(value) == TaskType.NodeRelease:
                    value = 'NodeRelease'
                else:
                    raise HpcError('Undefined TaskType')
            elif key == "runtime":
                value = "{:.0f}".format(min(self._runtime, value) * 3600.)
            elif key in ["requested_nodes", "required_nodes", "depends"] and value is not None:
                value = to_string(value)

            tattrs[key][1] = value
            if key.startswith("min_"):
                mxname = "max_" + key[4:]
                if tattrs[mxname][1] is None or tattrs[mxname][1] < tattrs[key][1]:
                    tattrs[mxname][1] = tattrs[key][1]

        xml = Document().createElement("Task")

        for key, value in iteritems(tattrs):
            if value[1]:
                xml.setAttribute(value[0], str(value[1]))

        self._add_env(xml, tenvs)

        self._tasks.append(xml)

        tattrs["taskno"] = [None, kwargs.get("taskno")]
        return DefDict(**{k: v[1] for k, v in iteritems(tattrs)})

    def __len__(self):
        """
        :return: length of job (how many tasks do we have
        :rtype: int
        """
        return len(self._tasks)

    def _prepare_paths(self, name):
        """create neccessary paths"""
        if not name:
            return
        if not validate_name(self._head_node, name):
            raise HpcError("JobName '{}' does not follow HPC rules, either class, type, function, "
                           "checkpoint name, or free text comment is wrong, too long, "
                           "or contains illegal characters (\\ / : * ? \" < > |)!"
                           .format(name))

        cc_name = "{}_{}".format(self._jobid, name)
        self._net_job_path = normpath(join(self._base_dir, cc_name))
        self._jenvs.update({"JobName": cc_name, "JobId": str(self._jobid)})

        for path in (self.net_in_path, self.net_out_data_path,):
            try:
                makedirs(path)
            except Exception:
                pass

    @staticmethod
    def _add_env(root, env):
        """
        add environment vars

        :param Document root: root to add this child to
        :param dict env: environment vars
        """
        doc = Document()
        envs = doc.createElement("EnvironmentVariables")
        for n, v in iteritems(env):
            var = doc.createElement("Variable")
            sub = doc.createElement("Name")
            sub.appendChild(doc.createTextNode(n))
            var.appendChild(sub)
            sub = doc.createElement("Value")
            sub.appendChild(doc.createTextNode(str(v)))
            var.appendChild(sub)
            envs.appendChild(var)
        root.appendChild(envs)

    def _env_path(self, bpath):
        """bundle PATH"""
        epath = ntdirname(self._exe)
        return ntjoin(bpath, "Scripts;") + STD_PATH.format(HPC_STORAGE_MAP[self._head_node][2]) + epath + ";" + \
               ";".join([ntjoin(epath, i) for i in PY_PATH[self._exe]])

    def _to_xml(self):
        """create an xml-doc from job including tasks, which is used for submitting the job."""
        doc = Document()
        root = doc.createElement("Job")

        # we place it here to not get overwritten
        self._jenvs.update({"HPC_VERSION": self._hpcversion})
        if self._venv:
            vpath = join(self.client_in_path, "venv")
            self._jenvs.update({"PIP_INDEX_URL":
                                    "https://eu.artifactory.conti.de/artifactory/api/pypi/c_adas_cip_pypi_v/simple",
                                "PIP_TRUSTED_HOST": "eu.artifactory.conti.de",
                                "PIP_CACHE_DIR": r"D:\pipcache",
                                "VIRTUAL_ENV": vpath, "PYTHONPATH": vpath})
        else:
            vpath = ntdirname(self._exe)

        if self._exe.startswith(LIN_EXE):
            self._jenvs.update(STD_PY_VAR[LIN_EXE])
        else:
            self._jenvs["PATH"] = self._env_path(vpath)
            self._jenvs["TEMP"] = self._jenvs["TMP"] = self.join(self._work_path, self.job_folder_name,
                                                                 "2_Output", "tmp")
            self._jenvs.update(STD_PY_VAR[self._exe])

        self._add_env(root, self._jenvs)

        for k, v in self._attr.values():
            if v is not None:
                root.setAttribute(k, to_string(v))

        # add custom properties now
        if self._eattr:
            arr = doc.createElement("CustomProperties")
            for k, v in list(self._eattr.values()):
                if v:
                    var = doc.createElement("Term")
                    sub = doc.createElement("Name")
                    sub.appendChild(doc.createTextNode(k))
                    var.appendChild(sub)
                    sub = doc.createElement("Value")
                    sub.appendChild(doc.createTextNode(v))
                    var.appendChild(sub)
                    arr.appendChild(var)

            root.appendChild(arr)

        # add tasks
        tasks = doc.createElement("Tasks")
        for task in self._tasks:
            tasks.appendChild(task)
        root.appendChild(tasks)

        # end
        doc.appendChild(root)

        return doc.toprettyxml(indent="   ", encoding="utf-8")

    def _check_df(self):
        """check disk free"""
        try:
            drv = disk_usage(dirname(self._base_dir))
            if 100. - drv.percent < LOW_NET_SPACE:
                self._logger.warning("we're running low on diskspace @ %s: %.1f%% used!", self._base_dir, drv.percent)
            elif drv.free < NO_NET_SPACE:
                raise HpcError("nearly no space left over on {}: {}!".format(self._base_dir, human_size(drv.free)))
        except HpcError:
            raise
        except Exception:  # pragma: no cover
            pass  # ignore silently

    @property
    def job_folder_name(self):
        """
        Name of the Job Folder (e.g. 1025_MTS_Training)

        :rtype: string
        """
        return basename(self._net_job_path)

    @property
    def work_path(self):
        r"""
        WSN node working path

        :return: usually, D:\data
        :rtype: str
        """
        return self._work_path

    @property
    def client_out_path(self):
        """
        Local Client (WorkstationNode) Path to Job Out Folder
        e.g. "d:/data/3522_MTS_Training/2_Output"
        :type: string
        """
        return self.join(self._work_path, self.job_folder_name, OUTPUT_PATH)

    @property
    def client_in_path(self):
        """
        Local Client (WorkstationNode) Path to Job Input Folder
        e.g. "d:/data/3522_MTS_Training/1_Input"
        :type: string
        """
        return self.join(self._work_path, self.job_folder_name, INPUT_PATH)

    @property
    def net_out_path(self):
        r"""
        Complete URL to the Network Job Out Folder
        e.g. "\\LIFS010S/hpc/LUSS013/3522_MTS_Training/2_Output"

        :rtype: string
        """
        return normpath(join(self._net_job_path, OUTPUT_PATH))

    @property
    def net_out_data_path(self):
        r"""
        Complete URL to the Network Job Out Data Folder
        e.g. "\\LIFS010S/hpc/LUSS013/3522_MTS_Training/2_Output/_data"

        :rtype: string
        """
        return normpath(join(self._net_job_path, OUTPUT_DATA_PATH))

    @property
    def net_in_path(self):
        r"""
        Complete URL to the Network Job Input Folder
        e.g. "\\LIFS010S/hpc/LUSS013/3522_MTS_Training/1_Input"

        :rtype: string
        """
        return normpath(join(self._net_job_path, INPUT_PATH))

    def check_template(self):
        """
        check if template is available

        :raises hpc.HpcError: if Default template is being used
        """
        if self.template == "Default":
            raise HpcError("error: usage of 'Default' template is not allowed.")

    def cancel_job(self, message):
        """virtual"""

    def submit(self, *args, **kwargs):
        """virtual"""

    @property
    def jobstate(self):
        """virtual"""
        return JobState.All

    # @staticmethod
    # def _in_unittest():
    #     """are we unit test?"""
    #     current_stack = stack()
    #     for stack_frame in current_stack:
    #         for program_line in stack_frame[4]:  # This element of the stack frame contains
    #             if "unittest" in program_line:  # some contextual program lines
    #                 return True
    #     return False


# - functions ----------------------------------------------------------------------------------------------------------
def to_string(value):
    """
    convert a boolean, list or time value to a string

    :param value: True/False, list with values, date and time
    :type value: Boolean, List or DateTime
    :return: True, False or csv as string, or time in "dd.mm.yy HH:MM:SS" format
    :rtype: string
    """
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, list):
        return ','.join([to_string(i) for i in value])
    if isinstance(value, datetime):  # it should be UTC!!!
        return value.strftime('%d.%m.%Y %H:%M:%S')

    return str(value)
