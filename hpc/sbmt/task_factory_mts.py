"""
task_factory_mts.py
-------------------

TaskFactoryMTS Module for Hpc.

**User-API Interfaces**

    - `hpc` (complete package)
    - `TaskFactoryMTS` (this module)
"""
# pylint: disable=W0212,E1103
# # - Python imports ---------------------------------------------------------------------------------------------------
from os.path import join
from six import iteritems

# - import HPC modules -------------------------------------------------------------------------------------------------
from ..core.error import HpcError
from ..core.tds import LOC_HEAD_MAP
from ..core.logger import deprecated
from ..core.convert import arg_trans
from ..bpl import Bpl
from .task_factory import TaskFactory
from .subtask_factory_mts import SubTaskFactoryMTS


# - classes ------------------------------------------------------------------------------------------------------------
class TaskFactoryMTS(TaskFactory):
    r"""
    .. inheritance-diagram:: hpc.TaskFactoryMTS

    - Specialized class for creating Hpc Tasks which run out MTS.
    - Typical usage is first to set all information, which is the
      same for all Tasks. (SetConfigFolder,SetConfigFile,...)
    - After that, multiple calls of the "create_task" - for the real
      MTS-Task creation.
    - This class is derived from the `TaskFactory`, this means all
      methods from there can also be used.

    **To Create multiple Tasks from a given *.bpl do**::

        # Create multiple task, to use as much as possible hpc power
        factory.create_tasks(bpl_path)

    **To Create a single Task to replay a single *.rec file do**::

        # Create a single task, which replay a single *.rec
        factory.create_task(rec_file_url)

    **To Create a single Task to replay a complete *.bpl do**::

        # Create a single task, which replay the whole bpl
        factory.create_task(bpl_path)

    **Full Example how a MTS Job can be submitted**::

        bpl_path = os.path.join(os.path.split(__file__)[0], r'07_training_mts.bpl')

        # Connect to the HPC Server
        job = hpc.Job(name="Training_MTS_Job", project="Short_Test", unit=hpc.JobUnitType.Node)

        # Create TaskFactory
        factory = hpc.TaskFactoryMTS(job)

        # Copy Job Input to the Job Folder
        factory.copy_mts_folders('.\\..\\..\\..\\06_Test_Tools\\mts_system',
                                 '.\\..\\..\\..\\06_Test_Tools\\mts_measurement')

        # Set some general Task settings
        factory.set_config('mts_measurement\\cfg\\algo', 'hpc_mts_test.cfg')
        factory.set_data_folder("d:\\data\\%JobName%\\2_Output\\%TaskName%\\data")

        # Create for every entry inside the bpl-file one Tasks
        factory.create_tasks(bpl_path)

        job.submit()

    """

    def __init__(self, hpc, **kwargs):
        """init task factory first"""
        TaskFactory.__init__(self, hpc, stf=SubTaskFactoryMTS(hpc, **kwargs), **kwargs)

        self._cfg_fldr = None
        self._cfg_file = None

    def set_app_path(self, app_path="d:\\data\\%JobName%\\1_Input\\mts_system\\measapp.exe"):
        """
        Provide the possibility to set the path to the measapp.exe
        to the correct one, if the default path can't be used.

        :note: %JobName% will be replaced with the real JobName.

        :param app_path:   Absolute path to the measapp.exe,
                           which is used to start the Task.
        :type app_path:    string
        """
        self._stf.set_app_path(app_path)

    def set_config(self, folder, file_name):
        """
        Set the folder, where MTS will find the given config file.
        This folder will also be used, if you have multiple configuration,
        which depends via a relative path from each other. So this Folder
        will also be used as the base config folder to resolve
        the relative paths to other given config files.

        Set the config file name, which shall be used by MTS.
        This FileName can also contain a relative path to the
        config file, if the Base Config Folder feature is needed.
        Please see also `TaskFactoryMTS.SetConfigFolder`

        :param str folder:    path to the base config folder.
        :param str file_name: name of config File or relative path to config file.
        :raises hpc.HpcError: raised when either folder of file is empty
        """
        if not folder or not file_name:
            raise HpcError("folder or file_name to MTS config is empty!")
        self._stf.set_config(folder, file_name)
        self._cfg_fldr = folder
        self._cfg_file = file_name

    @deprecated("please use set_config")
    def set_config_folder(self, folder):
        """deprecate it!"""
        if self._cfg_file:
            self.set_config(folder, self._cfg_file)
        else:
            self._cfg_fldr = folder

    @deprecated("please use set_config")
    def set_config_file_name(self, fname):
        """deprecate it!"""
        if self._cfg_fldr:
            self.set_config(self._cfg_fldr, fname)
        else:
            self._cfg_file = fname

    def set_data_folder(self, data_folder):
        r"""
        Set output data folder for MTS to a different than standard:
        "D:\\data\\%JobName%\\2_Output\\%TaskName%\\data"

        :param data_folder: path to the output data folder on the hpc-client.
        :type data_folder:  str
        """
        self._stf.set_data_folder(data_folder)

    def set_parameter(self, param, value):
        """set an extra parameter's value"""
        self._stf.set_parameter(param, value)

    def create_task(self, bpl_rec_filepath, *args, **kwargs):  # pylint: disable=W0221
        r"""
        Create a single task with the given input.

        :param str bpl_rec_filepath: Bpl or Rec File URL which must be used for MTS.
                                     Type depends on initializer mode ('rec', 'bpl')

        :param tuple args: for more args, please review subtask_factory.create_task's doc.
        :param dict kwargs: for more kwargs, please review subtask_factory.create_task's doc.

        :return: task info being added herein
        :rtype: dict

        The use case will be selected automatically with the argument of
        `bpl_rec_filepath` and depends on the given File Ending.

        *2 use cases are currently supported:*

        1. | Create a single task with one rec file.
           | HPC will replay in this task one rec
        2. | Create a single task with one bpl file.
           |  HPC will replay in this task the whole \*.bpl file with the given
           |  settings from MTS.
           |  In this mode, the MTS Batch settings must be considered:
           |      - Player mode:           [Play sections, Ignore sections]
           |      - Simulator reset mode:  [No Reset, Reset, Reset + Init]
           |      - Simulator restet time: [Before whole batch, Before batch entry]
           |  Please set the mts player settings manually with the mts itself,
           |  the settings are stored inside the configuration which must be used to
           |  submit the job.

        """
        opts = arg_trans(['depends', ['checker', True]], *args, **kwargs)

        sub_task = self._stf.create_task(bpl_rec_filepath, **opts)

        return self._create_task_with_subtask(sub_task, **opts)

    def create_tasks(self, bpl_file_path, *args, **kwargs):  # pylint: disable=W0221
        r"""
        Create a multiple Tasks based on a given \*.bpl file.

        If bpl file entry contains a section, then a bpl file based task
        will be created, and also the needed split new bpl file with this
        single entry. If bpl file entry is without sections, the task creation
        will use directly the \*.rec file path as argument.

        *checker* is an older argument to be able to disable mts check (bsigs),
        *depends* is used to create dependent tasks,

        for more kwargs, please review subtask_factory.create_task's doc.

        :param str bpl_file_path: Bpl File URL which must be used for MTS.
        :param tuple args: *depends* and *checker* can be given, others are optional (kwargs)
        :param dict kwargs: see below
        :keyword \**kwargs:
            * *ignore_missing* (``bool``): if using a collection and True here,
                                           recs inside not on same cluster are ignored
            * *loc* (``str``): location as a fallback for JobSim usage

        :return: task infos being added herein
        :rtype: list[dict]
        """
        opts = arg_trans(['depends', ['checker', True]], *args, **kwargs)
        tasks = []

        with Bpl(bpl_file_path, db="VGA_PWR", ignore_missing=kwargs.get("ignore_missing", False),
                 loc=next((k for k, v in iteritems(LOC_HEAD_MAP) if self._hpc.head_node in v),
                          opts.get('loc', ''))) as bpl:
            for item in bpl:
                if item.is_simple:
                    tasks.append(self.create_task(item.filepath[0], **opts))
                else:
                    self._hpc.bpl_cnt += 1
                    bpl_file = join(self._hpc.sched.net_in_path, 'bpl', "rec{:05d}.bpl".format(self._hpc.bpl_cnt))
                    item.save(bpl_file)
                    tasks.append(self.create_task(bpl_file, **opts))

        # for bplf, item in BplSplitter(self._hpc, bpl_file_path, **opts):
        #     if bplf:
        #         tasks.append(self.create_task(item, **opts))
        #     else:
        #         tasks.append(self.create_task(str(item), **opts))

        return tasks

    def copy_mts_folders(self, *args, **kwargs):
        r"""
        copy MTS folders from default (or given) directories and
        omit unneeded mts files and folders that are not needed in offline simulation

        :param \*args: *mts_sys_folder_name*, *mts_measure_folder_name*, *use_filter*, *mts_sys_dest*
                       and *mts_measure_dest* can be given, others are optional (kwargs)

        :keyword \**kwargs:
            * *mts_sys_folder_name* (``str``): MTS system folder path, can also be an artifactory (zip file)
            * *mts_measure_folder_name* (``str``): MTS measurement folder path
            * *use_filter* (``bool``): optional to deactivate ignore filter
            * *mts_sys_dest* (``str``): destination path for mts_system
            * *mts_measure_dest* (``str``): destination path for mts_measurement
        :raises hpc.HpcError: on copy error
        :raises ValueError: in case path cannot be found
        """
        self._stf.copy_mts_folders(*args, **kwargs)

    @property
    def cfg_folder(self):
        """return the config folder"""
        return self._cfg_fldr

    @property
    def cfg_file(self):
        """return the config file name"""
        return self._cfg_file
