"""
HPC Simulation & Validation Task Submit
------------------------

"""
import sys
import os
import shutil
import argparse
import configparser
import io
import stat
import tempfile
import codecs

try:

    # Annoying! Required when debugging with pycharm since it monkey patches PyQt in a suboptimal way
    import PyQt4
except:
    pass
import logging

VALF_PATH = os.path.abspath(os.path.join(__file__, ".."))
if VALF_PATH not in sys.path:
    sys.path.append(VALF_PATH)

## Utils
from framework.util.utils import BatchPlaylist, configure_logger, Configuration
from framework.util.create_sandbox import CreateSandbox
from framework.util.sim_setting import SimSettingAll
## HPC package

from hpc.sbmt.task_factory import TaskFactory
from hpc.sbmt.subtask_factory import SubTaskFactory
from hpc.sbmt.subtask_factory_mts import SubTaskFactoryMTS
from hpc.sbmt.job_sim import JobSim
from hpc.sbmt.job import Job
from hpc.bpl.bpl_splt import BplSplitter
from hpc import Bpl
from hpc.sbmt.job_sim import JobUnitType

__author__ = "Duan Shikun"
__copyright__ = "Copyright 2023, Continental AG"
__version__ = "$Revision: 0.1 $"
__date__ = "$Date: 2023/02/20 $"

_log = logging.getLogger(__name__)
_cfg = Configuration()


class TaskFactoryAdapter(TaskFactory, object):
    def __init__(self, hpc, *args, **kwargs):
        """ Custom task factory to submit fusion simulation for ARS440DPxx.

        :param hpc:
        """
        # super(TaskFactoryAdapter, self).__init__(*args, **kwargs)
        TaskFactory.__init__(self, hpc)
        self._hpc = hpc

        # Subtask factory for command line calls
        self._stf_cmd_builder = SubTaskFactory(hpc, io_watch=False, cpu_watch=False)
        # self._stf_cmd_builder.activate_app_watcher(False)

    def create_task(self, bpl_rec_filepath, depends_on=None, checker=True, runtime=None):
        """ See: HPC client package documentation

        :param bpl_rec_filepath:
        :param depends_on:
        :param checker:
        :param runtime:
        """
        pass

    def create_tasks(self, bpl_file_path, depends_on=None, checker=True, runtime=None):
        """ See: HPC client package documentation

        :param bpl_file_path:   Bpl File URL which must be used for MTS.
        :type bpl_file_path:    string
        :param depends_on:      list of TaskNames
        :type depends_on:       list of strings
        :param checker:         Enables a second SubTask which checks the
                                MTS Output (xlog, crash)
        :type checker:          boolean

        :note:                  The paths to the single rec files should not
                                contain the server "\\LIFS010S", just use
                                "\\LIFS010" On hpc, the extension "S"
                                will be added automatically.

        :author:                 Robert Hecker
        """
        # TODO: Hack to work around, that every useful thing is hidden in a three layer cake of confuscation

        # self._bpl_name = os.path.split(bpl_file_path)[1]
        # with Bpl(bpl_file_path) as bpl:
        #     for tsk, ent in enumerate(bpl):
        #         tskbpl = os.path.join(self._hpc.job_folder, "1_Input", "bpl", "T{:0>5d}.bpl".format(tsk + 1))
        #         ent.save(tskbpl)
        #         self.create_task(str(tskbpl), depends_on, checker, runtime)
        # No splitting bpl and it could be locate on the root dir of HPC input folder
        self._bpl_name = os.path.split(bpl_file_path)[1]
        # for bplf, item in BplSplitter(self._hpc, self._hpc.sched.net_in_path, bpl_file_path):
        #     if bplf:
        #         self.create_task(item, depends_on, checker, runtime)
        #     else:
        self.create_task(bpl_file_path, depends_on, checker, runtime)

    @classmethod
    def _update_ini(cls, ini_path, user_path):
        """ Rewrites the mts.ini to find the correct mts_measurements directory.

        :param ini_path: Path to mts.ini
        _:param user_path: name of mts measurements folder
        """

        config = configparser.RawConfigParser()
        config.optionxform = str
        with io.open(ini_path, 'r', encoding='utf_8_sig') as filep:
            config.readfp(filep)
            config.set('System', 'UserPath', user_path)

        with open(ini_path, 'w') as filep:
            config.write(filep)


class EcuSilFctSubTaskMixin(TaskFactoryAdapter):

    def __init__(self, hpc, *args, **kwargs):
        """ Mixin that provides EcuSil sub-task

        :param args:
        :param kwargs:
        """
        super(EcuSilFctSubTaskMixin, self).__init__(hpc, *args, **kwargs)
        self.data_root = None
        self.EcuSil_script = r"executable\ecu_sil_test_main.py"
        self.EcuSilFct_config = r"cfg\ecu_sil_MFC5J3_EBA.cfg"  ## Default for develp, change if needed
        self.prj = None
        self.sw_ver = None

    def _create_ecusilfct_task(self, bpl_rec_filepath):

        from datetime import datetime as actual_ts

        """ Creates EcuSil subtask.
            ##Do Not Touch!!!##
           :param bpl_rec_filepath: recording path or if bpl with sections a batch playlist
           :return: subtask
           
           """
        if os.path.split(bpl_rec_filepath)[1] == ".bpl":
            _log.info("BPL")
            bpl = BatchPlaylist(bpl_rec_filepath)
            rec = bpl.recordings[0]
        else:
            rec = bpl_rec_filepath

        bpl = os.path.join(r"d:\data\%JobName%\1_Input\bpl", self._bpl_name)

        out_dir = os.path.join(r"d:\data\%JobName%\2_Output\%TaskName%\data")

        if self.data_root is None:
            base_folder = out_dir
        else:
            base_folder = " ".join(self.data_root)
        if self.prj is None:
            prj = "Default_Project"
            _log.error("Project of running ECU SIL is not properly defined")
        else:
            prj = str(self.prj)
        if self.sw_ver is None:
            sw_ver = "Default_Project_SW_CP"
            _log.error("SW CP of running ECU SIL is not properly defined")
        else:
            sw_ver = str(self.sw_ver)

        ## Building cmd command

        cmd = os.path.join(r'python.exe d:\data\%JobName%\1_Input\req_tests', self.EcuSil_script)
        cmd += ' ' + prj  # Required args
        cmd += ' ' + sw_ver  # Required args
        cmd += ' ' + bpl  # Required args
        cmd += ' ' + os.path.join(r'd:\data\%JobName%\1_Input\req_tests', self.EcuSilFct_config)  # Required args
        cmd += ' --bsigs_dir ' + base_folder  # opt args
        cmd += ' --copy_report ' + str("\\\\itfs002x.it.cn.conti.de\\transfer\\duanshikun\\ECUSIL_Report")
        cmd += ' --cycle_1 ' + "207"  # opt args
        cmd += ' --cycle_2 ' + "207"  # opt args
        cmd += ' --report_name ' + str(actual_ts.utcnow().date()) + "_" + sw_ver + "_ECU-SIL_EBA.pdf"
        cmd += ' --output_dir ' + os.path.join(out_dir, "fct")

        return self._stf_cmd_builder.create_task(cmd)


class EcuSilAlnSubTaskMixin(TaskFactoryAdapter):

    def __init__(self, hpc, *args, **kwargs):
        """ Mixin that provides EcuSil sub-task

        :param args:
        :param kwargs:
        """
        super(EcuSilAlnSubTaskMixin, self).__init__(hpc, *args, **kwargs)
        self.data_root = None
        self.EcuSil_script = r"executable\ecu_sil_test_main.py"
        self.EcuSilAln_config = r"cfg\ecu_sil_ARS510_ALN.cfg"
        self.prj = None
        self.sw_ver = None
        self.report_dir = None

    def _create_ecusilaln_task(self, bpl_rec_filepath):

        from datetime import datetime as actual_ts

        """ Creates EcuSil subtask.
            ##Do Not Touch!!!##
           :param bpl_rec_filepath: recording path or if bpl with sections a batch playlist
           :return: subtask

           """
        if os.path.split(bpl_rec_filepath)[1] == ".bpl":
            _log.info("BPL")
            bpl = BatchPlaylist(bpl_rec_filepath)
            rec = bpl.recordings[0]
        else:
            rec = bpl_rec_filepath

        bpl = os.path.join(r"d:\data\%JobName%\1_Input\bpl", self._bpl_name)

        out_dir = os.path.join(r"d:\data\%JobName%\2_Output\%TaskName%\data")

        if self.data_root is None:
            base_folder = out_dir
        else:
            base_folder = " ".join(self.data_root)
        if self.prj is None:
            prj = "Default_Project"
            _log.error("Project of running ECU SIL is not properly defined")
        else:
            prj = str(self.prj)
        if self.sw_ver is None:
            sw_ver = "Default_Project_SW_CP"
            _log.error("SW CP of running ECU SIL is not properly defined")
        else:
            sw_ver = str(self.sw_ver)

        ## Building cmd command

        cmd = os.path.join(r'python.exe d:\data\%JobName%\1_Input\req_tests', self.EcuSil_script)
        cmd += ' ' + prj  # Required args
        cmd += ' ' + sw_ver  # Required args
        cmd += ' ' + bpl  # Required args
        cmd += ' ' + os.path.join(r'd:\data\%JobName%\1_Input\req_tests', self.EcuSilAln_config)  # Required args
        cmd += ' --bsigs_dir ' + base_folder  # opt args
        cmd += ' --copy_report ' + str(self.report_dir)
        cmd += ' --cycle_1 ' + "204"  # opt args
        cmd += ' --cycle_2 ' + "204"  # opt args
        cmd += ' --report_name ' + str(actual_ts.utcnow().date()) + "_" + sw_ver + "_ECU-SIL_ALN.pdf"
        cmd += ' --output_dir ' + out_dir

        return self._stf_cmd_builder.create_task(cmd)


class EcuSilBlkSubTaskMixin(TaskFactoryAdapter):

    def __init__(self, hpc, *args, **kwargs):
        """ Mixin that provides EcuSil sub-task

        :param args:
        :param kwargs:
        """
        super(EcuSilBlkSubTaskMixin, self).__init__(hpc, *args, **kwargs)
        self.data_root = None
        self.EcuSil_script = r"executable\ecu_sil_test_main.py"
        self.EcuSilBlk_config = r"cfg\ecu_sil_ARS510_FCT.cfg"  ## Default for develp, change if needed
        self.prj = None
        self.sw_ver = None
        self.report_dir = None

    def _create_ecusilblk_task(self, bpl_rec_filepath):

        from datetime import datetime as actual_ts

        """ Creates EcuSil subtask.
            ##Do Not Touch!!!##
           :param bpl_rec_filepath: recording path or if bpl with sections a batch playlist
           :return: subtask

           """
        if os.path.split(bpl_rec_filepath)[1] == ".bpl":
            _log.info("BPL")
            bpl = BatchPlaylist(bpl_rec_filepath)
            rec = bpl.recordings[0]
        else:
            rec = bpl_rec_filepath

        bpl = os.path.join(r"d:\data\%JobName%\1_Input\bpl", self._bpl_name)

        out_dir = os.path.join(r"d:\data\%JobName%\2_Output\%TaskName%\data")

        if self.data_root is None:
            base_folder = out_dir
        else:
            base_folder = " ".join(self.data_root)
        if self.prj is None:
            prj = "Default_Project"
            _log.error("Project of running ECU SIL is not properly defined")
        else:
            prj = str(self.prj)
        if self.sw_ver is None:
            sw_ver = "Default_Project_SW_CP"
            _log.error("SW CP of running ECU SIL is not properly defined")
        else:
            sw_ver = str(self.sw_ver)

        ## Building cmd command

        cmd = os.path.join(r'python.exe d:\data\%JobName%\1_Input\req_tests', self.EcuSil_script)
        cmd += ' ' + prj  # Required args
        cmd += ' ' + sw_ver  # Required args
        cmd += ' ' + bpl  # Required args
        cmd += ' ' + os.path.join(r'd:\data\%JobName%\1_Input\req_tests', self.EcuSilBlk_config)  # Required args
        cmd += ' --bsigs_dir ' + base_folder  # opt args
        cmd += ' --copy_report ' + str(self.report_dir)
        cmd += ' --cycle_1 ' + "208"  # opt args
        cmd += ' --cycle_2 ' + "208"  # opt args
        cmd += ' --report_name ' + str(actual_ts.utcnow().date()) + "_" + sw_ver + "_ECU-SIL_FCT.pdf"
        cmd += ' --output_dir ' + out_dir

        return self._stf_cmd_builder.create_task(cmd)


class EcuSilEmSubTaskMixin(TaskFactoryAdapter):

    def __init__(self, hpc, *args, **kwargs):
        """ Mixin that provides EcuSil sub-task

        :param args:
        :param kwargs:
        """
        super(EcuSilEmSubTaskMixin, self).__init__(hpc, *args, **kwargs)
        self.data_root = None
        self.EcuSil_script = r"executable\ecu_sil_test_main.py"
        self.EcuSilEm_config = r"cfg\ecu_sil_ARS510_EM.cfg"
        self.prj = None
        self.sw_ver = None
        self.report_dir = None

    def _create_ecusilem_task(self, bpl_rec_filepath):

        from datetime import datetime as actual_ts

        """ Creates EcuSil subtask.
            ##Do Not Touch!!!##
           :param bpl_rec_filepath: recording path or if bpl with sections a batch playlist
           :return: subtask

           """
        if os.path.split(bpl_rec_filepath)[1] == ".bpl":
            _log.info("BPL")
            bpl = BatchPlaylist(bpl_rec_filepath)
            rec = bpl.recordings[0]
        else:
            rec = bpl_rec_filepath

        bpl = os.path.join(r"d:\data\%JobName%\1_Input\bpl", self._bpl_name)

        out_dir = os.path.join(r"d:\data\%JobName%\2_Output\%TaskName%\data")

        if self.data_root is None:
            base_folder = out_dir
        else:
            base_folder = " ".join(self.data_root)
        if self.prj is None:
            prj = "Default_Project"
            _log.error("Project of running ECU SIL is not properly defined")
        else:
            prj = str(self.prj)
        if self.sw_ver is None:
            sw_ver = "Default_Project_SW_CP"
            _log.error("SW CP of running ECU SIL is not properly defined")
        else:
            sw_ver = str(self.sw_ver)

        # Building cmd command

        cmd = os.path.join(r'python.exe d:\data\%JobName%\1_Input\req_tests', self.EcuSil_script)
        cmd += ' ' + prj  # Required args
        cmd += ' ' + sw_ver  # Required args
        cmd += ' ' + bpl  # Required args
        cmd += ' ' + os.path.join(r'd:\data\%JobName%\1_Input\req_tests', self.EcuSilEm_config)  # Required args
        cmd += ' --bsigs_dir ' + base_folder  # opt args
        cmd += ' --copy_report ' + str(self.report_dir)
        cmd += ' --cycle_1 ' + "205"  # opt args
        cmd += ' --cycle_2 ' + "205"  # opt args
        cmd += ' --report_name ' + str(actual_ts.utcnow().date()) + "_" + sw_ver + "_ECU-SIL_EM.pdf"
        cmd += ' --output_dir ' + out_dir

        return self._stf_cmd_builder.create_task(cmd)


class EcuSilVdySubTaskMixin(TaskFactoryAdapter):

    def __init__(self, hpc, *args, **kwargs):
        """ Mixin that provides EcuSil sub-task

        :param args:
        :param kwargs:
        """
        super(EcuSilVdySubTaskMixin, self).__init__(hpc, *args, **kwargs)
        self.data_root = None
        self.EcuSil_script = r"executable\\ecu_sil_test_main.py"
        self.EcuSilVdy_config = r"\\ecu_sil_ARS510_VDY.cfg"
        self.prj = None
        self.sw_ver = None
        self.report_dir = None


    def _create_ecusilvdy_task(self, bpl_rec_filepath):

        from datetime import datetime as actual_ts

        """ Creates EcuSil subtask.
            ##Do Not Touch!!!##
           :param bpl_rec_filepath: recording path or if bpl with sections a batch playlist
           :return: subtask

           """
        if os.path.split(bpl_rec_filepath)[1] == ".bpl":
            _log.info("BPL")
            bpl = BatchPlaylist(bpl_rec_filepath)
            rec = bpl.recordings[0]
        else:
            rec = bpl_rec_filepath

        bpl = os.path.join(r"d:\data\%JobName%\1_Input\bpl", self._bpl_name)

        out_dir = os.path.join(r"d:\data\%JobName%\2_Output\%TaskName%\data")

        if self.data_root is None:
            base_folder = out_dir
        else:
            base_folder = " ".join(self.data_root)
        if self.prj is None:
            prj = "Default_Project"
            _log.error("Project of running ECU SIL is not properly defined")
        else:
            prj = str(self.prj)
        if self.sw_ver is None:
            sw_ver = "Default_Project_SW_CP"
            _log.error("SW CP of running ECU SIL is not properly defined")
        else:
            sw_ver = str(self.sw_ver)

        # Building cmd command

        cmd = os.path.join(r"python.exe d:\data\%JobName%\1_Input\req_tests", self.EcuSil_script)
        cmd += ' ' + prj  # Required args
        cmd += ' ' + sw_ver  # Required args
        cmd += ' ' + bpl  # Required args
        cmd += ' ' + os.path.join(r"d:\\data\\%JobName%\\1_Input\\req_tests", self.EcuSilVdy_config)  # Required args
        cmd += ' --bsigs_dir ' + base_folder  # opt args
        cmd += ' --copy_report ' + str(self.report_dir)
        cmd += ' --cycle_1 ' + "207"  # opt args
        cmd += ' --cycle_2 ' + "207"  # opt args
        cmd += ' --report_name ' + str(actual_ts.utcnow().date()) + "_" + sw_ver + "_ECU-SIL_VDY.pdf"
        cmd += ' --output_dir ' + str(out_dir)

        return self._stf_cmd_builder.create_task(cmd)


class EcuSilRsp2SubTaskMixin(TaskFactoryAdapter):

    def __init__(self, hpc, *args, **kwargs):
        """ Mixin that provides EcuSil sub-task

        :param args:
        :param kwargs:
        """
        super(EcuSilRsp2SubTaskMixin, self).__init__(hpc, *args, **kwargs)
        self.data_root = None
        self.EcuSil_script = r"executable\ecu_sil_test_main.py"
        self.EcuSilRsp2_config = r"cfg\ecu_sil_ARS510_RSP2_160.cfg"
        self.prj = None
        self.sw_ver = None
        self.report_dir = None

    def _create_ecusilrsp2_task(self, bpl_rec_filepath):

        from datetime import datetime as actual_ts

        """ Creates EcuSil subtask.
            ##Do Not Touch!!!##
           :param bpl_rec_filepath: recording path or if bpl with sections a batch playlist
           :return: subtask

           """
        if os.path.split(bpl_rec_filepath)[1] == ".bpl":
            _log.info("BPL")
            bpl = BatchPlaylist(bpl_rec_filepath)
            rec = bpl.recordings[0]
        else:
            rec = bpl_rec_filepath

        bpl = os.path.join(r"d:\data\%JobName%\1_Input\bpl", self._bpl_name)

        out_dir = os.path.join(r"d:\data\%JobName%\2_Output\%TaskName%\data")

        if self.data_root is None:
            base_folder = out_dir
        else:
            base_folder = " ".join(self.data_root)
        if self.prj is None:
            prj = "Default_Project"
            _log.error("Project of running ECU SIL is not properly defined")
        else:
            prj = str(self.prj)
        if self.sw_ver is None:
            sw_ver = "Default_Project_SW_CP"
            _log.error("SW CP of running ECU SIL is not properly defined")
        else:
            sw_ver = str(self.sw_ver)

        # Building cmd command

        cmd = os.path.join(r'python.exe d:\data\%JobName%\1_Input\req_tests', self.EcuSil_script)
        cmd += ' ' + prj  # Required args
        cmd += ' ' + sw_ver  # Required args
        cmd += ' ' + bpl  # Required args
        cmd += ' ' + os.path.join(r'd:\data\%JobName%\1_Input\req_tests', self.EcuSilRsp2_config)  # Required args
        cmd += ' --bsigs_dir ' + base_folder  # opt args
        cmd += ' --copy_report ' + str(self.report_dir)
        cmd += ' --cycle_1 ' + "204"  # opt args
        cmd += ' --cycle_2 ' + "204"  # opt args
        cmd += ' --report_name ' + str(actual_ts.utcnow().date()) + "_" + sw_ver + "_ECU-SIL_RSP2.pdf"
        cmd += ' --output_dir ' + out_dir

        return self._stf_cmd_builder.create_task(cmd)


class TaskfactoryEcuSil(EcuSilAlnSubTaskMixin, EcuSilBlkSubTaskMixin, EcuSilEmSubTaskMixin,
                        EcuSilFctSubTaskMixin, EcuSilVdySubTaskMixin, EcuSilRsp2SubTaskMixin):

    def __init__(self, hpc, esFct=False, esFct_suffix="EcuSilFct",  esAln=False, esAln_suffix="EcuSilAln",
                 esBlk=False, esBlk_suffix="EcuSilBlk",
                 esEm=False, esEm_suffix="EcuSilEm", esVdy=False, esVdy_suffix="EcuSilVdy",
                 esRsp2=False, esRsp2_suffix="EcuSilRsp2", esAll=False,
                 time_watch=0.0, data_root=None, sw_ver=None, prj=None, report_dir=None):
        """ Custom task factory to perform ECU SIL VAL for already performed HPC runs.
        :param hpc:
        """
        super(TaskfactoryEcuSil, self).__init__(hpc, esFct=esFct, esFct_suffix=esFct_suffix,
                                                esAln=esAln, esAln_suffix=esAln_suffix,
                                                esBlk=esBlk, esBlk_suffix=esBlk_suffix,
                                                esEm=esEm, esEm_suffix=esEm_suffix,
                                                esVdy=esVdy, esvdy_suffix=esVdy_suffix,
                                                esRsp2=esRsp2, esrsp2_suffix=esRsp2_suffix,
                                                esAll=esAll,
                                                time_watch=time_watch)

        # Flag to enable ecusil Fct run after MTS simulation
        self._enable_esFct = esFct
        self._esFct_suffix = esFct_suffix
        self._enable_esAln = esAln
        self._esAln_suffix = esAln_suffix
        self._enable_esBlk = esBlk
        self._esBlk_suffix = esBlk_suffix
        self._enable_esEm = esEm
        self.esEm_suffix = esEm_suffix
        self._enable_esVdy = esVdy
        self.esVdy_suffix = esVdy_suffix
        self._enable_esRsp2 = esRsp2
        self.esRsp2_suffix = esRsp2_suffix
        self._enable_esAll = esAll
        self._bpl_name = None
        self.data_root = data_root
        self.sw_ver = sw_ver
        self.prj = prj
        self.report_dir = report_dir
        self.subtaskfactory = SubTaskFactory(hpc)

    def create_task(self, bpl_rec_filepath, depends_on=None, checker=True, runtime=None):
        """ Creates a task consisting of 2 sub-tasks:

            * ecu sil for all or for each component

        :param bpl_rec_filepath: recording or bpl depending on simulation mode
        :param depends_on: see parent
        :param checker: see parent
        :param runtime: see parent
        :return: task
        """
        sub_task_list = []
        bpl_folder_hpc = os.path.join(self._hpc.job_folder, "1_Input", "bpl")
        if not os.path.exists(bpl_folder_hpc):
            os.makedirs(bpl_folder_hpc)
        shutil.copy(bpl_rec_filepath, bpl_folder_hpc)

        if self._enable_esAll:
            print("Creating ECU SIL Validation subtask for all component for VDY==meas")
            sub_task_list += self._create_ecusilaln_task(bpl_rec_filepath)
            sub_task_list += self._create_ecusilblk_task(bpl_rec_filepath)
            sub_task_list += self._create_ecusilem_task(bpl_rec_filepath)
            sub_task_list += self._create_ecusilrsp2_task(bpl_rec_filepath)
            #sub_task_list += self._create_ecusilvdy_task(bpl_rec_filepath)

        elif self._enable_esAln:
            print("Creating ECU SIL ALN subtask")
            sub_task_list += self._create_ecusilaln_task(bpl_rec_filepath)
        elif self._enable_esBlk:
            print("Creating ECU SIL BLK subtask")
            sub_task_list += self._create_ecusilblk_task(bpl_rec_filepath)
        elif self._enable_esEm:
            print("Creating ECU SIL EM subtask")
            sub_task_list += self._create_ecusilem_task(bpl_rec_filepath)
        elif self._enable_esFct:
            print("Creating ECU SIL FCT subtask")
            sub_task_list += self._create_ecusilfct_task(bpl_rec_filepath)
        elif self._enable_esVdy:
            print("Creating ECU SIL VDY subtask")
            sub_task_list += self._create_ecusilvdy_task(bpl_rec_filepath)
        elif self._enable_esRsp2:
            print("Creating ECU SIL RSP2 subtask")
            sub_task_list += self._create_ecusilrsp2_task(bpl_rec_filepath)

        return self._create_task_with_subtask(sub_task_list)  # deleted  depends_on, runtime

    def set_data_folder(self, data_folder):
        pass  # implemntation side effect
        # self._stf_cmd_builder.set_data_folder(data_folder)


class TaskFactoryEBA(EcuSilAlnSubTaskMixin, EcuSilBlkSubTaskMixin, EcuSilEmSubTaskMixin,
                    EcuSilFctSubTaskMixin, EcuSilVdySubTaskMixin, EcuSilRsp2SubTaskMixin):

    def __init__(self, hpc, esFct=False, esFct_suffix="EcuSilFct", esAll=False, time_watch=0.0,
                 sw_ver=None, prj=None, report_dir=None, esVdy=False, esAln=False, esEm=False,
                 esRsp2=False, esBlk=False):
        """ Custom task factory to submit fusion simulation for ARS440DPxx.
        :param hpc:
        """
        super(TaskFactoryEBA, self).__init__(hpc, esFct=esFct, esFct_suffix=esFct_suffix,
                                             time_watch=time_watch, esAll=esAll, esEm=esEm,
                                             esVdy=esVdy, esBlk=esBlk, esAln=esAln)

        # Flag to enable ECU-SIL Validation run after MTS simulation
        self._enable_esRsp2 = esRsp2
        self._enable_esFct = esFct
        self._esFct_suffix = esFct_suffix
        self._enable_esAll = esAll
        self._enable_esVdy = esVdy
        self._enable_esAln = esAln
        self._enable_esBlk = esBlk
        self._enable_esEm = esEm


        self.sw_ver = sw_ver
        self.prj = prj
        self.report_dir = report_dir
        self._bpl_name = None

        # Subtask factory Simulation
        self._subtaskfactory_mts = SubTaskFactoryMTS(hpc, time_watch=time_watch, cpu_watch=False)
        self._subtaskfactory_mts.set_app_path("d:\\data\\%JobName%\\1_Input\\mts\\measapp.exe")

    def set_cur_work_dir(self, working_dir):
        self._subtaskfactory_mts.set_cur_work_dir(working_dir)

    def add_environment_variable(self, key, value):
        self._subtaskfactory_mts.add_environment_variable(key, value)

    def append_node_folder(self, folder):
        self._subtaskfactory_mts.append_node_folder(folder)

    def activate_app_watcher(self, active):
        self._subtaskfactory_mts.activate_app_watcher(active)

    def use_global_data_folder(self, value):  # No sure useful anymore?
        self._subtaskfactory_mts.use_global_data_folder(value)

    def set_config_file_name_ars(self, file_name):
        self._subtaskfactory_mts.set_config(folder="mts_measurement\\cfg", file_name=file_name)
        # self._subtaskfactory_mts.set_config_file_name(file_name)

    def set_data_folder(self, data_folder):
        self._subtaskfactory_mts.set_data_folder(data_folder)

    def create_task(self, bpl_rec_filepath, depends_on=None, checker=True, runtime=None):
        """ Creates a task consisting of several (optional) sub-tasks:

            * Optional cam preprocessing (BW18)
            * ARS MTS Sim
            * Optional PySTC
            * Optional Labelset Creator
            * Optional Norm Converter (BW18)

        :param bpl_rec_filepath: recording or bpl depending on simulation mode
        :param depends_on: see parent
        :param checker: see parent
        :param runtime: see parent
        :return: task
        """
        sub_task_list = self._subtaskfactory_mts.create_task(bpl_rec_filepath, checker=checker)

        if self._enable_esFct:
            print("Creating ECU SIL Simulation and Validation subtask for MFC FCT component")
            sub_task_list += self._create_ecusilfct_task(bpl_rec_filepath)

        if self._enable_esAll:

            print("Creating ECU SIL Simulation and Validation subtask for all ARS component")
            sub_task_list += self._create_ecusilaln_task(bpl_rec_filepath)
            sub_task_list += self._create_ecusilblk_task(bpl_rec_filepath)
            sub_task_list += self._create_ecusilem_task(bpl_rec_filepath)
            sub_task_list += self._create_ecusilrsp2_task(bpl_rec_filepath)
            #sub_task_list += self._create_ecusilvdy_task(bpl_rec_filepath)

        elif self._enable_esVdy:
            print("Creating ECU SIL Simulation and Validation subtask for VDY component")
            sub_task_list += self._create_ecusilvdy_task(bpl_rec_filepath)

        elif self._enable_esAln:
            print("Creating ECU SIL Simulation and Validation subtask for ALN component")
            sub_task_list += self._create_ecusilaln_task(bpl_rec_filepath)

        elif self._enable_esBlk:
            print("Creating ECU SIL Simulation and Validation subtask for BLK component")
            sub_task_list += self._create_ecusilblk_task(bpl_rec_filepath)

        elif self._enable_esEm:
            print("Creating ECU SIL Simulation and Validation subtask for EM component")
            sub_task_list += self._create_ecusilem_task(bpl_rec_filepath)

        elif self._enable_esRsp2:
            print("Creating ECU SIL Simulation and Validation subtask for RSP2 component")
            sub_task_list += self._create_ecusilrsp2_task(bpl_rec_filepath)

        return self._create_task_with_subtask(sub_task_list)  # deleted ,,, depends_on, runtime as 2 more arguments

    def copy_mts_folders(self, mts_sys_folder_name=r'.\mts', mts_measure_folder_name=r'.\mts_measurement',
                         use_filter=True):
        # Rewrite to target mts_measurement
        mts_ini = os.path.abspath(os.path.join(mts_sys_folder_name, "mts.ini"))
        os.chmod(mts_ini, stat.S_IWRITE)
        # self._update_ini(mts_ini, u'"..\\\\mts_measurement_{}\\\\"'.format("ars"))

        v = self._subtaskfactory_mts.copy_mts_folders(mts_sys_folder_name, mts_measure_folder_name,
                                                      mts_sys_dest=r'mts',
                                                      mts_measure_dest=r'mts_measurement',
                                                      use_filter=use_filter)

        return v


class SimulationSubmit(object):

    def __init__(self):
        """ Sets up the submit factory for HPC. """

        self.job = None
        self.job_folder = None

        # For ECU SIL
        self.prj = None
        self.sw_ver = None
        self.report_dir = None

        self.EcuSil_script = r"executable\ecu_sil_test_main.py"
        # FCT (EBA/ACC)
        self.EcuSilFct_config = r"cfg\ecu_sil_MFC5J3_EBA.cfg"
        self.add_esFct = False
        self.esFct_suffix = False
        # Aln
        self.add_esAln = False
        self.esAln_suffix = False
        self.EcuSilAln_config = r"cfg\ecu_sil_ARS510_ALN.cfg"
        # Blk
        self.add_esBlk = False
        self.esBlk_suffix = False
        self.EcuSilBlk_config = r"cfg\ecu_sil_ARS510_FCT.cfg"
        # Em
        self.add_esEm = False
        self.esEm_suffix = False
        self.EcuSilEm_config = r"cfg\ecu_sil_ARS510_EM.cfg"
        # Vdy
        self.add_esVdy = False
        self.esVdy_suffix = False
        self.EcuSilVdy_config = r"cfg\ecu_sil_ARS510_VDY.cfg"
        # Rsp2
        self.add_esRsp2 = False
        self.esRsp2_suffix = False
        self.EcuSilRsp2_config = r"cfg\ecu_sil_ARS510_RSP2.cfg"
        # all components
        self.add_all = False

        self.force_improvements = False
        # TODO: ADDING improvement that deleteing all bsigs in data folder when copy to HPC

    def check_batchplaylist(self, playlist):
        """ Checks the BPL for validity.

        :param playlist: path to batch playlist or Collection name.
        :return playlist: if collection name was given return path to batch playlist.
        """

        # if not playlist.lower().endswith(".bpl"):
        #     # Get Oracle DB COnection
        #     db_connector = DatabaseConnection(masterdbuser=DB_USER, masterdbpassword=DB_PW, masterdb=DB_MASTER)
        #     _log.info("Collection name was given, DB connection established")
        #     # Get Temporary directory and bpl path
        #     tmp_dic_name = tempfile.mkdtemp()
        #     bpl_path = os.path.abspath(os.path.join(tmp_dic_name, playlist + ".bpl"))
        #     # Get BPL from Collection Name
        #     db_connector.db_cat.export_bpl_for_collection(playlist, bpl_path)
        #     playlist = bpl_path

        _log.info("Checking BPL file paths.")
        bpl = BatchPlaylist(playlist)
        for recording in bpl.recordings:
            if recording.startswith("\\\\lifs010\\"):
                _log.debug("Valid recording: '{}'".format(recording))
            elif recording.startswith("\\\\lufs003x"):
                _log.debug("Valid recording: '{}'".format(recording))
            elif recording.startswith("\\\\lufs009x"):
                _log.debug("Valid recording: '{}'".format(recording))
            elif recording.startswith("\\\\lifs010."):
                _log.debug("Valid recording: '{}'".format(recording))
            elif recording.startswith("\\\\qhfs004x."):
                _log.debug("Valid recording: '{}'".format(recording))
            elif recording.startswith("\\\\ozfs110."):
                _log.debug("Valid recording: '{}'".format(recording))
            elif recording.startswith("\\\\itfs001x."):
                _log.debug("Valid recording: '{}'".format(recording))
            elif recording.startswith("\\\\itfs002x."):
                _log.debug("Valid recording: '{}'".format(recording))

            else:
                _log.debug("Invalid recording: '{}'".format(recording))
                _log.error("BPL contains invalid paths. Only recordings on LIFS010 are supported.")
                sys.exit(-1)

        return playlist

    def check_mts_root(self, directory):
        """ Checks if the mts root directory is valid.

        :param directory:
        :return:
        """
        mts = os.path.abspath(os.path.join(directory, "mts"))
        mts_measurement = os.path.abspath(os.path.join(directory, "mts_measurement"))

        for f in [mts, mts_measurement]:
            if not os.path.exists(f) or not os.path.isdir(f):
                _log.error("Folder '{}' does not exist.".format(f))
                sys.exit(-1)

        return mts, mts_measurement

    def clean_mts_measurement(self, meas_dir):
        """ Removes all files from
            * data
            * log

        :param meas_dir: path to mts_measurement
        """
        meas_data = os.path.join(meas_dir, "data")
        meas_log = os.path.join(meas_dir, "log")

        if os.path.exists(meas_data):
            _log.info("Cleaning mts_measurement\data")
            # improvements.delete_data_dir(meas_data)
        if os.path.exists(meas_log):
            _log.info("Cleaning mts_measurement\log")
            # improvements.delete_data_dir(meas_log)

    def create_job(self, name, project, template, job_unit_type, local_sim):
        """ Sets up the HPC job.

        :param name: HPC job name
        :param project: project name
        :param template: HPC job template
        :param job_unit_type: HPC job unit type
        :param local_sim: Flag, if set the sim is submitted locally
        :return:
        """
        # Build job
        if local_sim:
            self.job = JobSim(name=name, project=project, template=template)
        else:
            self.job = Job(head_node="ITAS004A", priority="Normal", name=name, project=project, template=template)
            self.force_improvements = True

        self.job_folder = self.job.job_folder
        self.job.notify_on_completion = True

    def check_config(self, mts_measurement, cfg_sub_path):
        """ Checks that given MTS config exists.

        If submit is to HPC or force improvements is set also removes all vizualizations from the
        configuration, disables generic draw and deletes all visualization MOs from the sandbox.

        :param mts_measurement:
        :param cfg_sub_path:
        :return:
        """
        meas_cfg = os.path.join(mts_measurement, "cfg", cfg_sub_path)
        if not os.path.exists(meas_cfg):
            _log.error("Configuration file '{}' could not be found.".format(meas_cfg))
            sys.exit(-1)

        if self.force_improvements:
            _log.info("Applying sim improvements")
            # improvements.delete_non_sim_mo(mts_measurement)
            # improvements.set_generic_draw(mts_measurement, False)
            # improvements.strip_config(meas_cfg)

    def auto_make_ars_sim_config(self, ars_mts_measurement):
        """ Creates the simulation configuration for ARS simulation if parameter sim_config is not used.

        :param ars_mts_measurement:
        :return:
        """
        _log.info("Creating SIL configuration automatically.")
        meas_cfg = os.path.join(ars_mts_measurement, "cfg", "algo", "algo_cfg", "hpc_sim.cfg")
        sim_all_1x = os.path.join(ars_mts_measurement, "cfg", "algo", "algo_cfg", "ars400_all_sim_1x_best.cfg")
        sim_exp_1x = os.path.join(ars_mts_measurement, "cfg", "algo", "algo_cfg", "ars400_simexp_1x.cfg")
        # if self.single_task:
        #     #improvements.set_batch_settings(sim_all_1x, "SimResetMode=2", "SimResetMode=1",
        #                                    # "SimresetTime=1", "SimresetTime=0")
        # else:
        #     #improvements.set_batch_settings(sim_all_1x, "SimResetMode=1", "SimResetMode=2",
        #                                    # "SimresetTime=0", "SimresetTime=1")
        if not os.path.exists(sim_all_1x):
            _log.error("Autoconf is only available for ARS4xx projects.")
            sys.exit(-1)

        # improvements.glue_configs(meas_cfg, sim_all_1x, sim_exp_1x)
        return r"algo\algo_cfg\hpc_sim.cfg"

    def merge_configs(self, ars_mts_measurement, configs):
        _log.info("Merging SIL configurations: {}.".format(configs))
        mts_measurement_cfg_path = os.path.join(ars_mts_measurement, "cfg")
        if not os.path.exists(mts_measurement_cfg_path):
            raise Exception("Config folder for MTS does not exist in '{}'. Review your parameters"
                            .format(mts_measurement_cfg_path))

        sim_cfg = os.path.join(mts_measurement_cfg_path, "hpc_sim.cfg")

        config_full_paths = []  # [os.path.join(ars_mts_measurement, "cfg", p) for p in configs]
        for cfg in configs:
            if os.path.commonprefix([mts_measurement_cfg_path, cfg]) == mts_measurement_cfg_path:
                # Absolute path name, no problem do nothing
                config_full_paths.append(cfg)
            elif os.path.exists(os.path.join(mts_measurement_cfg_path, cfg)):
                config_full_paths.append(os.path.join(mts_measurement_cfg_path, cfg))
            else:
                raise Exception("Config '{}' does not exist in '{}'.".format(cfg, mts_measurement_cfg_path))

        self.glue_configs(sim_cfg, *config_full_paths)
        return r"hpc_sim.cfg"

    @staticmethod
    def glue_configs(target_config_path, sim_cfg, *exporter_configs):
        """ Glues configs together.

        :param sim_cfg: full path simulator configuration
        :param exporter_cfg: list of all exporter configs that should be added to the resulting config.
        """

        with codecs.open(sim_cfg, mode='r', encoding='UTF-8-sig') as fd:
            file_content = "# -*- coding: utf-8 -*-"
            file_content += "".join(fd.readlines())

        for exp_config in exporter_configs:
            file_content += "\n"
            with codecs.open(exp_config, mode='r', encoding='UTF-8-sig') as fd:
                file_content += "".join(fd.readlines())

        with codecs.open(target_config_path, mode="w", encoding='UTF-8-sig') as fh:
            fh.writelines(file_content)
            fh.flush()
            fh.close()

    def upload_vsc(self):
        """ Uploads the validation environment to HPC head node. """
        # Copy this valf to Head node
        src = os.path.abspath(os.path.join(__file__, "..", ".."))
        dest = os.path.join(self.job_folder, "1_Input", "req_tests")
        _log.info("Uploading VSC...")
        shutil.copytree(src, dest)

    def create_ecusilfct_factory(self, data_root):

        print("Creating ecusil EBA val factory")
        factory = TaskfactoryEcuSil(self.job, esFct=self.add_esFct, esFct_suffix="EcuSilFct", time_watch=48.0,
                                    data_root=data_root, sw_ver=self.sw_ver, prj=self.prj, report_dir=self.report_dir)
        factory.EcuSil_script = self.EcuSil_script
        factory.EcuSilFct_config = self.EcuSilFct_config

        return factory

    def create_ecusilaln_factory(self, data_root):

        print("Creating ecusil ALN val factory")
        factory = TaskfactoryEcuSil(self.job, esAln=self.add_esAln, esAln_suffix="EcuSilAln", time_watch=48.0,
                                    data_root=data_root, sw_ver=self.sw_ver, prj=self.prj, report_dir=self.report_dir)
        factory.EcuSil_script = self.EcuSil_script
        factory.EcuSilAln_config = self.EcuSilAln_config

        return factory

    def create_ecusilblk_factory(self, data_root):

        print("Creating ecusil BLK val factory")
        factory = TaskfactoryEcuSil(self.job, esBlk=self.add_esBlk, esBlk_suffix="EcuSilBLK", time_watch=48.0,
                                    data_root=data_root, sw_ver=self.sw_ver, prj=self.prj, report_dir=self.report_dir)
        factory.EcuSil_script = self.EcuSil_script
        factory.EcuSilBlk_config = self.EcuSilBlk_config

        return factory

    def create_ecusilem_factory(self, data_root):

        print("Creating ecusil EM val factory")
        factory = TaskfactoryEcuSil(self.job, esEm=self.add_esEm, esEm_suffix="EcuSilEM", time_watch=48.0,
                                    data_root=data_root, sw_ver=self.sw_ver, prj=self.prj, report_dir=self.report_dir)
        factory.EcuSil_script = self.EcuSil_script
        factory.EcuSilEm_config = self.EcuSilEm_config

        return factory

    def create_ecusilvdy_factory(self, data_root):

        print("Creating ecusil VDY val factory")
        factory = TaskfactoryEcuSil(self.job, esVdy=self.add_esVdy, esVdy_suffix="EcuSilVDY", time_watch=48.0,
                                    data_root=data_root, sw_ver=self.sw_ver, prj=self.prj, report_dir=self.report_dir)
        factory.EcuSil_script = self.EcuSil_script
        factory.EcuSilVdy_config = self.EcuSilVdy_config

        return factory

    def create_ecusilrsp2_factory(self, data_root):

        print("Creating ecusil RSP2 val factory")
        factory = TaskfactoryEcuSil(self.job, esRsp2=self.add_esRsp2, esRsp2_suffix="EcuSilRsp2", time_watch=48.0,
                                    data_root=data_root, sw_ver=self.sw_ver, prj=self.prj, report_dir=self.report_dir)
        factory.EcuSil_script = self.EcuSil_script
        factory.EcuSilRsp2_config = self.EcuSilRsp2_config

        return factory

    def create_ecusilall_factory(self, data_root):

        print("Creating ECUSIL all components validation factory")

        factory = TaskfactoryEcuSil(self.job, esAll=self.add_esAll, time_watch=48.0,
                                    data_root=data_root, sw_ver=self.sw_ver, prj=self.prj, report_dir=self.report_dir)

        factory.EcuSil_script = self.EcuSil_script
        factory.EcuSilRsp2_config = self.EcuSilRsp2_config
        factory.EcuSilVdy_config = self.EcuSilVdy_config
        factory.EcuSilEm_config = self.EcuSilEm_config
        factory.EcuSilBlk_config = self.EcuSilBlk_config
        factory.EcuSilAln_config = self.EcuSilAln_config

        return factory

    def create_mts_simulation_factory(self, mts, mts_measurement, sim_configs):
        """ Creates a factory for MTS simulation

        Subtasks:
            * MTS simulation
            * ECU SIL Validation for selected Components/project

        :param mts:
        :param mts_measurement:
        :param sim_configs:
        :return: hpc task factory
        """
        factory = TaskFactoryEBA(self.job, esFct=self.add_esFct, time_watch=self.time_watch,
                                 esFct_suffix=self.esFct_suffix, esAll=self.add_esAll, sw_ver=self.sw_ver,
                                 prj=self.prj, report_dir=self.report_dir, esRsp2=self.add_esRsp2,
                                 esAln=self.add_esAln, esBlk=self.add_esBlk, esEm=self.add_esEm,
                                 esVdy=self.add_esVdy)

        # check config or create
        if sim_configs is None:
            _log.error("The Simulation configuration path is not given")
            sys.exit(-1)
        #     sim_config = self.auto_make_ars_sim_config(mts_measurement)
        elif len(sim_configs) > 1:
            sim_config = self.merge_configs(mts_measurement, sim_configs)
        else:
            sim_config = sim_configs[0]

        self.check_config(mts_measurement, sim_config)

        # try:
        #     # TEMP FIX: Raw RecFile reader, if it fails not critical
        #     improvements.replace_raw_recfile_reader(mts)
        # except Exception as ex:
        #     _log.debug("failed to replace rawrecfilereader.dll ({}).".format(ex))

        _log.info("Uploading MTS...")
        # Preserve original mts_measurments
        temp_measurements = os.path.join(tempfile.mkdtemp(), "mts_measurements")
        shutil.copytree(mts_measurement, temp_measurements)

        self.clean_mts_measurement(temp_measurements)
        factory.copy_mts_folders(mts, temp_measurements, use_filter=False)
        factory.set_config_file_name_ars(sim_config)

        def on_rm_error(func, path, exc_info):
            # path contains the path of the file that couldn't be removed
            # let's just assume that it's read-only and unlink it.
            os.chmod(path, stat.S_IWRITE)
            os.unlink(path)

        shutil.rmtree(temp_measurements, onerror=on_rm_error)

        return factory

    def submit_main(self, project, template, name, playlist, data_root=None, mts_root=None, sim_config=None,
                    local_sim=False, force_improvements=False, cr_cp_ars=None, pwd=None,
                    # ECU_SIL
                    add_esFct=False,  Fct_suffix="EcuSilFct",   Fct_config=None,
                    add_esAln=False,  Aln_suffix="EcuSilAln",   Aln_config=None,
                    add_esEm=False,   Em_suffix="EcuSilEm",     Em_config=None,
                    add_esBlk=False,  Blk_suffix="EcuSilBlk",   Blk_config=None,
                    add_esVdy=False,  Vdy_suffix="EcuSilVdy",   Vdy_config=None,
                    add_esRsp2=False, Rsp2_suffix="EcuSilRsp2", Rsp2_config=None,
                    add_esAll=False,
                    sw_ver=None, report_dir=None,
                    #
                    job_unit_type="socket",
                    time_watch=0.0):
        """
        Submits a job with the given parameters to HPC.

        TODO: Defaults

        :param project: Project name
        :param template: HPC job template (e.g. ARS_SRR)
        :param name:  HPC job name
        :param mts_root: Path to directory with mts and mts_measurement. In fusion case ARS MTS
        :param playlist: Path to batch playlist that should be simulated
        :param sim_config:  Path to MTS config(s). In fusion case ARS MTS config(s)
        :param local_sim: Flag, if set the job is submited to d:\data for testing purposes only.
        :param force_improvements: Flag, if set applies all imrprovements
        :param add_esxxx: Flag, add Ecu sil as subtask to every task.

        """
        # ecu sil
        # Fct (EBA/ ACC)
        self.add_esFct = add_esFct
        self.esFct_suffix = Fct_suffix
        # Aln
        self.add_esAln = add_esAln
        self.esAln_suffix = Aln_suffix
        # Blk
        self.add_esBlk = add_esBlk
        self.esBlk_suffix = Blk_suffix
        # Em
        self.add_esEm = add_esEm
        self.esEm_suffix = Em_suffix
        # Vdy
        self.add_esVdy = add_esVdy
        self.esVdy_suffix = Vdy_suffix
        # Rsp2
        self.add_esRsp2 = add_esRsp2
        self.esRsp2_suffix = Rsp2_suffix
        # ALL
        self. add_esAll = add_esAll

        self.sw_ver = sw_ver  ## Generally, this attr is not needed, for ECU-SIL report, SW CP has to be transmitted to cmd
        self.prj = project  ## Generally, this attr is not needed, for ECU-SIL report, project has to be transmitted to cmd
        self.report_dir = report_dir  # Could be self-defined, or use default

        self.time_watch = time_watch
        self.force_improvements = force_improvements

        if Fct_config:
            self.esFct_config = Fct_config

        if Aln_config:
            self.esAln_config = Aln_config


        # Check bpl
        batch_playlist = self.check_batchplaylist(playlist)

        self.create_job(name, project, template, job_unit_type, local_sim)

        # make job
        if mts_root is not None:
            _log.info("Starting submit for MTS simulation'.")
            mts = os.path.abspath(os.path.join(mts_root, "mts"))
            # Mainstream naming
            if not os.path.exists(mts):
                mts = os.path.abspath(os.path.join(mts_root, "mts_system"))
            if "x64" in args.name:
                mts = os.path.abspath(os.path.join(mts_root, "mts_system_x64"))
            mts_measurement = os.path.abspath(os.path.join(mts_root, "mts_measurement"))
            factory = self.create_mts_simulation_factory(mts, mts_measurement, sim_config)

        elif data_root is not None:
            print("Using given Bsig path:", data_root, "to run ECU-SIL validation")

            if add_esAln is not False:
                factory = self.create_ecusilaln_factory(data_root)

            if add_esFct is not False:
                factory = self.create_ecusilfct_factory(data_root)

            if add_esBlk is not False:
                factory = self.create_ecusilblk_factory(data_root)

            if add_esEm is not False:
                factory = self.create_ecusilem_factory(data_root)

            if add_esVdy is not False:
                factory = self.create_ecusilvdy_factory(data_root)

            if add_esRsp2 is not False:
                factory = self.create_ecusilrsp2_factory(data_root)

            if add_esAll is not False:
                factory = self.create_ecusilall_factory(data_root)


        factory.set_data_folder(r"d:\data\%JobName%\2_Output\%TaskName%\data")

        self.upload_vsc()

        _log.info("Creating job database...")

        factory.create_tasks(batch_playlist)

        _log.info("Finishing submit...")
        self.job.submit()
        _log.debug("Done.")

        return self.job.jobid, self.job.job_name



# ---------------------------------------
#  command line
# ---------------------------------------
if __name__ == "__main__":
    _cfg.verbosity_level = 1
    configure_logger("hpc_submit.log")
    _log.info("Submit MTS HPC Simulation")

    parser = argparse.ArgumentParser(description="Submits a job to HPC where each task does a MTS simulation and "
                                                 "optional invokes the python STC.")
    # Absolutely required arguments
    parser.add_argument("project", help="The project name (e.g. ARS410GY18).")
    parser.add_argument("template", help="The HPC job template (see HPC guidelines).")
    parser.add_argument("name", help="The HPC job name (see guidelines for HPC Job naming).")

    parser.add_argument("playlist", help="Path to bpl or collection name.")

    # Optionals
    parser.add_argument("--data_root", nargs='+', help="Path to the bsigs folder root for Statistics jobs")

    # MTS Simulations
    parser.add_argument("--mts_root", help="Path to the folder containing the mts and mts_measurement for ARS.")
    parser.add_argument("--sim_config", nargs='+',
                        help="Path to config for MTS simulation, relative from mts_measurement/cfg. In case of "
                             "fusion simulation this config is assigned to the ARS simulation.")

    # testing purposes
    parser.add_argument("--local_sim", "-l", action="store_true", help="Submit local sim for testing purposes.")
    parser.add_argument("--force_improvements", action="store_true", help="Force the same improvements as on HPC to "
                                                                          "local simulation.")

    # Additional subtasks
    # Sync the checkpoint from IMS
    parser.add_argument("--cr_cp_ars", "-ars", help="Create algo checkpoint(ars).")
    parser.add_argument("--pwd", help="password for current user log in, necessary is sync cp is required")
    # IMS is no longer available, can be ignored.

    # parser.add_argument("--ori_sim_config", help="use this sim config to copy in newly downloaded sandbox")
    # To be deleted as using exporter merge

    # Subtask for ecu sil fct
    parser.add_argument("--esFct", dest="add_esFct", action="store_true",
                        help="adding ecusil validation after simulation.")

    parser.add_argument("--Fct_suffix", help="Use if different es suffix is needed.", default="EcuSilFct")
    parser.add_argument("--Fct_config",
                        help="provide the component cfg for ecusil test")  # Not applicable yet, define in def

    # ALN
    parser.add_argument("--esAln", dest="add_esAln", action="store_true")
    parser.add_argument("--Aln_config",
                        help="provide the component cfg for ecusil test")  # Not applicable yet, define in def
    parser.add_argument("--Aln_suffix", help="Use if different es suffix is needed.", default="EcuSilAln")

    # EM
    parser.add_argument("--esEm", dest="add_esEm", action="store_true")
    parser.add_argument("--Em_config",
                        help="provide the component cfg for ecusil test")  # Not applicable yet, define in def
    parser.add_argument("--Em_suffix", help="Use if different es suffix is needed.", default="EcuSilEm")

    # FCT (blk in case of radar)
    parser.add_argument("--esBlk", dest="add_esBlk", action="store_true")
    parser.add_argument("--Blk_config",
                        help="provide the component cfg for ecusil test")  # Not applicable yet, define in def
    parser.add_argument("--Blk_suffix", help="Use if different es suffix is needed.", default="EcuSilBlk")

    # VDY
    parser.add_argument("--esVdy", dest="add_esVdy", action="store_true")
    parser.add_argument("--Vdy_config",
                        help="provide the component cfg for ecusil test")  # Not applicable yet, define in def
    parser.add_argument("--Vdy_suffix", help="Use if different es suffix is needed.", default="EcuSilVdy")

    # RSP2
    parser.add_argument("--esRsp2", dest="add_esRsp2", action="store_true")
    parser.add_argument("--Rsp2_config",
                        help="provide the component cfg for ecusil test")  # Not applicable yet, define in def
    parser.add_argument("--Rsp2_suffix", help="Use if different es suffix is needed.", default="EcuSilRsp2")

    # ECU-SIL Validation all
    parser.add_argument("--esAll", dest="add_esAll", action="store_true",
                        help="Activate all component for ES validation")

    parser.add_argument("--sw_ver", help=" CP version of current sw")  # Common element for all comps

    parser.add_argument("--report_dir", "-rd", help="Report output path",
                        default=r"\\itfs002x.it.cn.conti.de\transfer\duanshikun\ECUSIL_Report")

    #parser.add_argument("--simcfg_comp", "-comp", nargs='+', help="Change sim config components.")

    # Fixes and special purpose switches
    parser.add_argument("--job_unit_type", "-j", choices=['socket', 'node'], default='socket',
                        help="Specifies job type.")
    parser.add_argument("--time_watch", default=2.0, help="Specifies timout for MTS job. Defaults to 2.")

    args = parser.parse_args()

    if args.cr_cp_ars:
        if args.pwd is None:
            _log.error("Your password is not provided to log in IMS")
            sys.exit(-1)
        else:
            CreateSandbox().create_sandbox(args.project, args.mts_root, args.cr_cp_ars, args.pwd)
        # sim_cfg = str(args.ori_sim_config)
        # if not sim_cfg:
        #     _log.error("Please provide the sim config for simulation for newly sync CP")
        #     sys.exit(-1)
        # else:
        #     mts_meas = os.path.join(args.mts_root, "mts_measurement", "cfg")
        #     target_dir = os.path.join(mts_meas, args.sim_config)
        #     shutil.copyfile(sim_cfg, target_dir)
        #     _log.info("The sim config {0} is from {1} copied to {2} as {3}".format(os.path.split(sim_cfg)[1],
        #                                                                            os.path.split(sim_cfg)[0],
        #                                                                            os.path.split(target_dir)[0],
        #                                                                            os.path.split(target_dir)[1]))

    sim_submit = SimulationSubmit()
    job_id, name = sim_submit.submit_main(**vars(args))

    print("Job-ID:", job_id)
    print("Job-Name:", name)

"""
..
    CHANGE LOG:
    -----------
    $Log: ecu_sil_sim_val_ars_mfc.py  $
    Revision 1.1 2023/02/19 Duan Shikun (uie89573)
    auto-run for mts simulation and validation on HPC for each single component or All comps together;
    enabled MFC FCT ECU SIL or ARS one/all comp(s) Sim and Val; 
    Supporting copy report to given directory on itfsxxx (by default dir)
    Revision 1.2 2023/07/03  Duan Shikun (uie89573)
    change the default bpl loading path to 1_Input\bpl to have consistency 
    add an opt parameter to define the report output path;
    Revision 1.3 2023/07/04 Duan Shikun(uie89573)
    add sinngle component val after simulation is submit 
    
    TODO: 
    adding improvement to delete all local data folder existing bsig(s) while submitting
    adding logic for select ecu sil config between given and default 
    adding "--report path" for given path in case of different prj or requirement
    adding merging/auto-make for sim cfg (joint sim + sim_exporter) in the case of ARS
    
            
"""
