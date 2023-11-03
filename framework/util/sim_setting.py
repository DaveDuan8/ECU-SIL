import os
import shutil
import stat
import logging
from subprocess import Popen
import glob

__author__ = "Suraj Saw"
__version__ = "$Revision: 1.0 $"
__maintainer__ = "$Author: Saw, Suraj Kumar (uic28010) (uic28010) $"
__date__ = "$Date: 2020/05/13 08:53:03CEST $"



_log = logging.getLogger(__name__)

class SimSettingAll(object):

    def change_simcfg_component(self, simcfg, config_path, config_path1, mfc_sim_config):

        _log.info("Changing algo_all_sub.simcfg component for simulation...")

        bak = os.path.abspath(config_path + ".bak")
        if os.path.exists(config_path):
            os.chmod(config_path, stat.S_IWRITE)
            if os.path.exists(bak):
                os.chmod(bak, stat.S_IWRITE)
                os.unlink(bak)
            shutil.move(config_path, bak)
            with open(config_path, "w") as dst:
                with open(bak, "r") as src:
                    for line in src:
                        if line.find("sim_sub_meas")!= -1:
                            line = line.replace("sim_sub_meas", "sim_sub")
                        dst.write(line)
                    src.close()
                dst.flush()
                dst.close()
            #os.remove(bak)

            if simcfg:
                _log.info("Setting Sim config Components.")
                for comp in simcfg:
                    comp = comp.lower()
                    bak = os.path.abspath(config_path + ".bak")
                    if os.path.exists(config_path):
                        if os.path.exists(bak):
                            os.chmod(bak, stat.S_IWRITE)
                            os.unlink(bak)
                        shutil.move(config_path, bak)
                        with open(config_path, "w") as dst:
                            with open(bak, "r") as src:
                                for line in src:
                                    if line.find("\{}_sub".format(comp)) != -1:
                                        line = line.replace("\{}_sub".format(comp), "\{}_sim_sub_meas".format(comp))
                                    elif line.find("{}_sim_sub".format(comp)) != -1:
                                        line = line.replace("\{}_sim_sub".format(comp), "\{}_sim_sub_meas".format(comp))
                                    dst.write(line)

                                src.close()
                            dst.flush()
                            dst.close()
                        #os.remove(bak)

        if mfc_sim_config:

            _log.info("Checking DatabaseFile detail into joint config.")
            bak1 = os.path.abspath(config_path1 + ".bak")
            if os.path.exists(config_path1):
                os.chmod(config_path1, stat.S_IWRITE)
                if os.path.exists(bak1):
                    os.chmod(bak1, stat.S_IWRITE)
                    os.unlink(bak1)
                shutil.move(config_path1, bak1)
                # with open(config_path1, "w") as dst:
                #     with open(bak1, "r") as src:
                #         for line in src:
                #             if line.find('DatabaseFile=""') != -1:
                #                 #line = line.replace('DatabaseFile=""', r'DatabaseFile="%HPCTaskDataFolder%\\$RecFileName$_OD_FULL.csv"')
                #                 line = line.replace('DatabaseFile=""',
                #                                     r'DatabaseFile="%HPCTaskDataFolder%\\mcam_obj_list\\$RecFileName$.csv"')
                #             dst.write(line)
                #         src.close()
                #     dst.flush()
                #     dst.close()
                pattern = "DatabaseFile="
                with open(config_path1, "w") as dst:
                    with open(bak1, "r") as src:
                        for line in src:
                            line = line.strip('\r\n')
                            if pattern in line:
                                # line = r'DatabaseFile="%HPCTaskDataFolder%\\$RecFileName$_OD_FULL.csv"'
                                line = r'DatabaseFile="%HPCTaskDataFolder%\\mcam_obj_list\\$RecFileName$.csv"'
                            dst.write(line + '\n')
                        src.close()
                    dst.flush()
                    dst.close()

    def mfc_csv(self, mts_root, sim_config, config_path, mfc_csv):

        _log.info("Checking DatabaseFile detail into joint config with MFC generated CSV path.")

        # user = os.environ["USERNAME"]
        # str_con_resync_ars = (
        #     """si resync --hostname=ims-adas --port=7001 --nomerge --overwriteChanged --sandbox={1}/mts_measurement/cfg/{2} --recurse --user={0}""").format(
        #     user, mts_root, sim_config)
        #
        # Popen(str_con_resync_ars).communicate()

        csvformat = glob.glob(mfc_csv + '/*.csv')[0]
        #print csvformat
        mfc_csv = str.replace(mfc_csv, "\\", "\\\\")
        bak1 = os.path.abspath(config_path + ".bak")
        if os.path.exists(config_path):
            os.chmod(config_path, stat.S_IWRITE)
            if os.path.exists(bak1):
                os.chmod(bak1, stat.S_IWRITE)
                os.unlink(bak1)
            shutil.move(config_path, bak1)
            pattern = "DatabaseFile="
            with open(config_path, "w") as dst:
                with open(bak1, "r") as src:
                    for line in src:
                        line = line.strip('\r\n')
                        if pattern in line:
                            if csvformat.__contains__("_OD_FULL.csv"):
                                line = r'DatabaseFile="' + mfc_csv + r'\\$RecFileName$_OD_FULL.csv"'
                            else:
                                line = r'DatabaseFile="' + mfc_csv + r'\\$RecFileName$.csv"'
                        dst.write(line + '\n')
                    src.close()
                dst.flush()
                dst.close()
    #
    # def fct_cpar_sim_setting(self, config_path, project):
    #
    #
    #     if project=="ARS410SW29" or project=="ARS410SW39":
    #
    #         bak = os.path.abspath(config_path + ".bak")
    #         if os.path.exists(config_path):
    #             os.chmod(config_path, stat.S_IWRITE)
    #             if os.path.exists(bak):
    #                 os.chmod(bak, stat.S_IWRITE)
    #                 os.unlink(bak)
    #             shutil.move(config_path, bak)
    #             with open(config_path, "w") as dst:
    #                 with open(bak, "r") as src:
    #                     for line in src:
    #                         if project == "ARS410SW29" and line.find(
    #                                 r"[EBA_OBJ_LIST_CONFIG_SEN_SOURCE].Value=1") != -1:
    #                             line = line.replace(r"[EBA_OBJ_LIST_CONFIG_SEN_SOURCE].Value=1  ;EM_GEN_OBJECT_MS_LRR",
    #                                                 r"[EBA_OBJ_LIST_CONFIG_SEN_SOURCE].Value=17  ;EM_GEN_OBJECT_MS_LRR")
    #                         elif project == "ARS410SW39" and line.find(
    #                                 r"[EBA_OBJ_LIST_CONFIG_SEN_SOURCE].Value=17  ;EM_GEN_OBJECT_MS_LRR") != -1:
    #                             line = line.replace(r"[EBA_OBJ_LIST_CONFIG_SEN_SOURCE].Value=17  ;EM_GEN_OBJECT_MS_LRR",
    #                                                 r"[EBA_OBJ_LIST_CONFIG_SEN_SOURCE].Value=1  ;EM_GEN_OBJECT_MS_LRR")
    #                         dst.write(line)
    #                     src.close()
    #                 dst.flush()
    #                 dst.close()
    #
    #     if project == "ARS430BW18":
    #         if os.path.exists(config_path):
    #             switch_parameter(config_path, "EBA_CODING_PAR_CUST", 3)
    #
    #
    # def fct_parameter_sim_setting(self, parameter_file, project, value_ds, value_ds1, value_ds_all, dsvalue, china_en, china_ds):
    #
    #     if os.path.exists(parameter_file):
    #         if value_ds:
    #             switch_parameter(parameter_file, "Sim_OverruleValue_DriverSettings_uint8", 1)
    #         elif value_ds1:
    #             switch_parameter(parameter_file, "Sim_OverruleValue_DriverSettings_uint8", 2)
    #         else:
    #             switch_parameter(parameter_file, "Sim_OverruleValue_DriverSettings_uint8", 0)
    #
    #     if os.path.exists(parameter_file):
    #         if value_ds_all:
    #             switch_parameter(parameter_file, "Sim_OverruleValue_DriverSettings_uint8", dsvalue)
    #
    #     if project == "ARS430BW18" and china_en:
    #         if os.path.exists(parameter_file):
    #             switch_parameter(parameter_file, "Sim_OverruleEnable_bDegradationLightEnabled", 1)
    #             switch_parameter(parameter_file, "Sim_OverruleValue_bDegradationLightEnabled_uint8", 1)
    #
    #     if project == "ARS430BW18" and china_ds:
    #         if os.path.exists(parameter_file):
    #             switch_parameter(parameter_file, "Sim_OverruleEnable_bDegradationLightEnabled", 0)
    #             switch_parameter(parameter_file, "Sim_OverruleValue_bDegradationLightEnabled_uint8", 0)
    #
    # def sim_swc_fct_sim_setting(self, parameter_file, project, china_en, china_ds):
    #
    #     if project == "ARS430BW16" and china_en:
    #         if os.path.exists(parameter_file):
    #             switch_parameter(parameter_file, "HEAD_bDegradationLightEnabled", 1)
    #
    #     if project == "ARS430BW16" and china_ds:
    #         if os.path.exists(parameter_file):
    #             switch_parameter(parameter_file, "HEAD_bDegradationLightEnabled", 0)
    #
    # def ibrake_adaption_dll_sim_setting(self, config_path, project):
    #
    #     if project == "ARS430BW18":
    #
    #         if os.path.exists(config_path):
    #             switch_parameter(config_path, "iBrakeAdaptionDllActive", 1)
