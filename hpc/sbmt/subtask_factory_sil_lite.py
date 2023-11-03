"""
subtask_factory_sil_lite.py
---------------------------

SubTaskFactorySILLite Module for HPC.

**User-API Interfaces**

    - `hpc` (complete package)
    - `SubTaskFactorySILLite` (this module)
"""
# - import HPC modules -------------------------------------------------------------------------------------------------
from .subtask_factory_mts import SubTaskFactoryMTS


# - classes ------------------------------------------------------------------------------------------------------------
class SubTaskFactorySILLite(SubTaskFactoryMTS):
    """
    Specialized class for creating Hpc SubTasks which run out SIL Lite.

    - Typical usage is first to set all information,
      which is the same for all Tasks. (SetConfigFolder,SetConfigFile,...)
    - After that, multiple calls of the "create_task"
      -> for the real SIL Lite-Task creation.
    - This class is derived from the `SubTaskFactory`,
      this means all methods from there can also be used.
    - a private check method is registered to be executed in Job.submit() checking
      the availability of the SIL Lite config file.
    """

    def __init__(self, hpc, **kwargs):
        r"""
        :param hpc.Job hpc: hpc job class
        :param dict kwargs: see below

        :keyword \**kwargs:
            * *io_watch* (``bool``): whether watchdog shall watch io traffic
            * *cpu_watch* (``bool``): whether watchdog shall track cpu usage
            * *time_watch* (``float``): whether watchdog shall monitor time [h]
            * *prn_watch* (``bool``): whether watchdog shall watch the printout
            * *time_factor* (``float``): default 16 x recording length
            * *loglevel* (``int``): use a certain logging level (mts_check)
            * *exist* (``bool``): check existence of recording, default: False
            * *mtscheck* (``bool``): check MTS log files for problems, default: False
            * *skipon* (``list``): continue on certain exitcodes of previous subtask, e.g. [-302, -402]
            * *cfg_blacklist* (``list[str]``): blacklisted MTS / SilLite config sections
            * *wrapexe* (``str``): executable wrapped around each sub task
        """
        kwargs['exist'] = None  # overwrite as we cannot check DB
        SubTaskFactoryMTS.__init__(self, hpc, mode="SIL", map_rec=False, **kwargs)

    def set_app_path(self, app_path="d:\\data\\%JobName%\\1_Input\\sil_lite\\sil_lite.exe"):
        """
        Provide the possibility to set the path to sil_lite
        to the correct one, if the default path can't be used.

        :note: %JobName% will be replaced with the real JobName.

        :param str app_path:   Absolute path to the sil_lite.exe,
                           which is used to start the Task.
        """
        SubTaskFactoryMTS.set_app_path(self, app_path)

    def copy_sil_lite_folders(self, sil_sys_folder_name=r'.\sil_lite', sil_measure_folder_name=r'.\mts_measurement',
                              use_filter=True, sil_sys_dest=r'sil_lite', sil_measure_dest=r'mts_measurement',):
        """
        Copy SIL lite folders from default (or given) directories and
        omit unneeded mts files and folders that are not needed in offline simulation

        :param str sil_sys_folder_name:     optional path to sil_lite folder
        :param str sil_measure_folder_name: optional path to mts_measurement folder
        :param bool use_filter:             optional to deactivate ignore filter
        :param str sil_sys_dest:            destination path for sil_lite
        :param str sil_measure_dest:        destination path for mts_measurement
        """
        SubTaskFactoryMTS.copy_mts_folders(self, sil_sys_folder_name, sil_measure_folder_name, use_filter,
                                           sil_sys_dest, sil_measure_dest)
