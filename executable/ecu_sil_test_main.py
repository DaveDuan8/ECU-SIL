"""
Validation suite setup for ecu_sil_tool.executable.ecu_sil_test_main
-------------------------------------------------------

The main entry point to setup and execute a validation run.

"""

from __future__ import print_function

import argparse
import logging
import shutil
import subprocess
import sys
import os
import re
import logging as log

VALFTEST_PATH = os.path.abspath(os.path.join(__file__, "..", ".."))
print (VALFTEST_PATH)
if VALFTEST_PATH not in sys.path:
    sys.path.append(VALFTEST_PATH)

from framework.bpl.batch_playlist import BatchPlaylist
from framework.util import logger
from framework.util.defines import *
from framework.valf import valf


__author__ = "Leidenberger Ralf"
__copyright__ = "Copyright 2020, Continental AG"
__version__ = "$Revision: 1.2 $"
__maintainer__ = "$Author: Leidenberger, Ralf (uidq7596) $"
__date__ = "$Date: 2020/03/31 08:45:36CEST $"


def start_validation_run(project, checkpoint, bsig_base_dir, batch_playlist, config, sim_cfg, ref_sw, output_dir):
    """ Starts the report generation.
    :param project: The project under test
    :param checkpoint: The checkpoint under test
    :param bsig_base_dir: Base directory where to look for the BSIG exports
    :param batch_playlist: batch play list whoich contains the recordings
    :param config: which contain the test case definition
    :param sim_cfg: name or description of the simulation configuration
    :param ref_sw: name of the reference s
    :param output_dir: output path on HPC job folder
    """
    # Main entry point to start a valf run.
    current_dir = os.path.abspath(os.path.split(__file__)[0])
    print("current_dir", current_dir)
    #out_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "2_Output", "_data", "output",
                                 #str(actual_ts.now().strftime('%Y_%m_%d_%H_%M_%S_%f')[:-3])))

    # if not os.path.exists(output_dir):
    #     os.makedirs(output_dir)
    #
    # test_data_out = os.path.abspath(os.path.join(output_dir, "output",
    #                                         str(actual_ts.now().strftime('%Y_%m_%d_%H_%M_%S_%f')[:-3])))

    #out_dir = os.path.abspath(os.path.join(output_dir, test_data_out))
    #print("out_dir", out_dir)
    out_dir = os.path.abspath(output_dir)

    # Observer search path for all observers which do not reside in the
    # framework
    plugins = [os.path.join(current_dir, PLUGINS_DIR), ]

    vsuite = valf.Valf(out_dir, logger.DEBUG, plugins, clean_folder=False, fail_on_error=True)

    # Disable logging for modules which have no meaning for me.
    components = ["BPL_ECU60", "BPL_SIM60", "BPL_ECU20", "BPL_SIM20",
                  "TestRunManager", "ProcessManager", "PdSignalExtractor_ECU20",
                  "PdSignalExtractor_SIL20", "PdSignalExtractor_SIM",
                  "PdSignalExtractor_ECU"]

    for c in components:
        requests_log = logging.getLogger(c)
        requests_log.setLevel(logging.ERROR)

    vsuite.load_config(config)

    # Simulation file selection either batch play list for testing
    vsuite.set_bpl_file(batch_playlist)
    vsuite.set_data_port("ProjectName", project)
    rc = None
    output = None
    # try:
    #     command = subprocess.Popen(["si", "diff", config], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    #     output = command.communicate(b"")
    #     rc = command.returncode
    #     if rc == 0:
    #         state_diff = "synced"
    #     else:
    #         state_diff = "changed"
    # except output:
    #     state_diff = "changed+"
    # rev = "Member Revision: unknown"
    # try:
    #     command = subprocess.Popen(["si", "memberinfo", config], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    #     output, err = command.communicate(b"")
    #     rc = command.returncode
    #     lines = output.split("\n")
    #     for line in lines:
    #         if line.find("Member Revision") >= 0:
    #             rev = line
    #             break
    #         else:
    #             continue
    # except rc:
    #     rev = "Member Revision: unknown+"
    # vsuite.set_data_port("FunctionName", os.path.split(config)[1] + " -- "+rev + " file is " + state_diff)

    if sim_cfg is not None:
        vsuite.set_data_port("sim_name", sim_cfg)
    if ref_sw is not None:
        vsuite.set_data_port(SWVERSION_REG_PORT_NAME, ref_sw)

    sil208_path = os.path.join(bsig_base_dir, SIL_208_DIR)
    ecu208_path = os.path.join(bsig_base_dir, ECU_208_DIR)
    vsuite.set_sim_path(sil208_path, BUS_SIL_208)
    vsuite.set_sim_path(ecu208_path, BUS_ECU_208)

    sil207_path = os.path.join(bsig_base_dir, SIL_207_DIR)
    ecu207_path = os.path.join(bsig_base_dir, ECU_207_DIR)
    vsuite.set_sim_path(sil207_path, BUS_SIL_207)
    vsuite.set_sim_path(ecu207_path, BUS_ECU_207)

    vsuite.set_sw_version(checkpoint)

    # start validation:
    vsuite.run()


def perform_mts_simulation():
    print("Running simulation! Please do not exit mts!")
    print("It might take some time...")

    # Directory for MTS
    mts_dir = os.path.join(args.sandbox,  "05_Testing", "06_Test_Tools")
    # Output path for log file
    log_file_path = os.path.join(args.sandbox, "05_Testing", "04_Test_Data", "algo", "02_Output", "inttest", "crt",
                                 "ecu_sil")

    # configuration of the cfg-file for the simulation
    if args.cfg_file is not None:
        # already merged ecu_sil.cfg
        cfg_file = args.cfg_file
    else:
        # merging the sim.cfg with the exp.cfg
        cur_dir = os.path.abspath(".")
        os.chdir(mts_dir + "\\mts_measurement\\cfg\\algo\\algo_cfg")
        os.system("copy /b " + args.sim_cfg + "+" + args.exp_cfg + " ecu_sil_gen.cfg")
        cfg_file = "ecu_sil_gen.cfg"
        os.chdir(cur_dir)

    print("Starting the Simulation with \"" + cfg_file + "\"...")

    subprocess.call([mts_dir + "\\mts\\measapp.exe", "-norestart",                   # no automatically restart
                                                     "-silent",                      # no popups
                                                     "-pal",                         # play recording after loading
                                                     "-eab",                         # exit MTS after playing Batch
                                                     "-lcalgo/algo_cfg/"+cfg_file,   # MTS Config file
                                                     "-lb"+args.batch_playlist,      # filepath for batch list
                                                     "-pl"+log_file_path,            # output path for log file
                                                     "-psd"])                         # default path for data files


def bsig_root_folder_struct(root_path, bsig_base_name=None):
    """ Checks that all expected subfolders are in place.

    :param root_path: The path to the BSIG exports
    :param bsig_base_name: When supplied the bsig name is also checked.
    :returns: True -- if all as expected
    """
    if not os.path.exists(root_path):
        return False

    for sf in [SIL_60_DIR, ECU_60_DIR, SIL_20_DIR, ECU_20_DIR]:
        if not os.path.exists(os.path.join(root_path, sf)):
            return False

        if bsig_base_name is None:
            continue

        dir_contents_base = [os.path.splitext(_f)[0].lower() for _f in os.listdir(os.path.join(root_path, sf))]

        if not bsig_base_name.lower() in dir_contents_base:
            return False

    return True


def bsig_name_from_recording(recording):
    """ Extracts the BSIG file name WITHOUT the extension from the
    recording name.

    :param recording: Path to the recording for with the report should be
    generated
    :returns: BSIG base name
    """
    _, tail = os.path.split(recording)
    return os.path.splitext(tail)[0]


def bsig_root_location(_args):
    """Checks if the given bsig file location exists, prior to executing the
    report generation.
    The following locations, depending on the commandline parameters will
    be checked:
    1. Direct entering of the bsig location, or either of the following
    2. MTS: <sandbox>/06_Testing/05_Tools/mts_measurement/data/
    3. File server \\lifs010/data/<project>/_Validation/ECU_SIL/<checkpoint>/

    :param _args: The parsed commandline arguments.
    :returns: A valid BSIG root location.
    :raises: IOError
    """

    # # Get the expected bsigname from the recording name
    bpl = BatchPlaylist(_args.batch_playlist)
    recordings = bpl.recordings

    # Using --bsigs_dir bypasses all other searches
    if _args.bsig_root_path is not None:
        root_path = _args.bsig_root_path
        for rec in recordings:
            bsig = bsig_name_from_recording(rec)
            if not bsig_root_folder_struct(root_path, bsig):
                raise IOError("The directory given by argument '--bsigs_dir' " +
                              "does not contain the expected directory " +
                              "and/or BSIG exports.")

        return root_path

    # Check the MTS sandbox
    if _args.sandbox is not None:
        mts_measurement = os.path.join(_args.sandbox, "05_Testing", "06_Test_Tools", "mts_measurement")

        data_dir = os.path.join(mts_measurement, "data")
        for rec in recordings:
            bsig = bsig_name_from_recording(rec)
            if not bsig_root_folder_struct(data_dir, bsig):
                print(bsig)
                raise IOError("The directory given by argument '--bsigs_dir' does not contain the expected directory " +
                              "and/or BSIG exports.")
        return data_dir

    # Last option the file is already on the file server
    # file_server_path = os.path.join(r"\\itfs001h", "data", _args.project, "_Validation", "ECU_SIL", _args.checkpoint)
    #
    # for rec in recordings:
    #     bsig = bsig_name_from_recording(rec)
    #     if not bsig_root_folder_struct(file_server_path, bsig):
    #         print(bsig)
    #         raise IOError("The directory given by argument '--bsigs_dir' " +
    #                       "does not contain the expected directory " +
    #                       "and/or BSIG exports.")
    # return file_server_path


if __name__ == '__main__':

    """ The main entry point from the command line. """
    parser = argparse.ArgumentParser()
    parser.add_argument("project",
                        help="project name, e.g. ARS4B0")

    parser.add_argument("checkpoint",
                        help="Algorithm checkpoint, e.g. AL_ARS400PR_02.05.01_INT-1")

    parser.add_argument("batch_playlist",
                        help="Batch play list containing the recordings used for ECU-SIL Simulation")

    parser.add_argument("configuration",
                        help="path to valf configuration file.")

    parser.add_argument("-s", "--sandbox",
                        dest="sandbox",
                        help="Sandbox directory, checked out on 06_Algorithm/project.pj. Required when MTS " +
                              "simulation should be performed prior to generating the report")

    parser.add_argument("--bsigs_dir", dest="bsig_root_path",
                        help="Root path to the BSIG exports. Using this parameter  will supersede looking up the bsig"
                             " files in the sandbox or on the fileserver.")

    parser.add_argument("--copy_report", dest="copy_report",
                        help="Will copy the finished report to the given location to prevent it from delectation on"
                             " revalidation")

    parser.add_argument("-cfg_file", dest="cfg_file",
                        help="MTS will start and generate the bsigs from the given bpl with the given cfg file.")

    parser.add_argument("-sim_cfg", dest="sim_cfg",
                        help="Will merge this sim.cfg with the exp.cfg to generate the ecu_sil.cfg.")

    parser.add_argument("-exp_cfg", dest="exp_cfg",
                        help="Will merge this exp.cfg with the sim.cfg to generate the ecu_sil.cfg.")

    parser.add_argument("--cycle_1", dest="cycle1",
                        help="Select the cycle number for the exporter of the '20ms' cycle")

    parser.add_argument("--cycle_2", dest="cycle2",
                        help="Select the cycle number for the exporter of the '60ms' cycle")

    parser.add_argument("-ref_sw", dest="ref_sw", help="Define the name of the reference software")

    parser.add_argument("--report_name", dest="report_name", help="Define the name for the report for copy or Checkin")

    parser.add_argument("--output_dir", dest="output_dir", help="Directory for csv output.")

    args = parser.parse_args()

    if args.cycle1 is not None:
        SIL_20_DIR = "bin_data_" + args.cycle1 + "_sil"
        ECU_20_DIR = "bin_data_" + args.cycle1 + "_ecu"
        SIL_207_DIR = "bin_data_" + args.cycle1 + "_sil"
        ECU_207_DIR = "bin_data_" + args.cycle1 + "_ecu"
    if args.cycle2 is not None:
        SIL_60_DIR = "bin_data_" + args.cycle2 + "_sil"
        ECU_60_DIR = "bin_data_" + args.cycle2 + "_ecu"
        SIL_208_DIR = "bin_data_" + args.cycle2 + "_sil"
        ECU_208_DIR = "bin_data_" + args.cycle2 + "_ecu"
        SIL_205_DIR = "bin_data_" + args.cycle2 + "_sil"
        ECU_205_DIR = "bin_data_" + args.cycle2 + "_ecu"

    bsig_dir = bsig_root_location(args)

    start_validation_run(args.project, args.checkpoint, bsig_dir, args.batch_playlist, args.configuration, args.sim_cfg,
                         args.ref_sw, args.output_dir)

    if args.copy_report:
        if not os.path.exists(args.copy_report):
            os.makedirs(args.copy_report)

        for f in os.listdir(args.output_dir):     # modified for suit HPC from TEST_DATA_OUT to test_data_out  xxx
            head, ext = os.path.splitext(f)
            if ext == ".pdf":
                if args.report_name is not None:
                    shutil.copyfile(os.path.join(args.output_dir, f), os.path.join(args.copy_report, args.report_name))
                else:
                    shutil.copyfile(os.path.join(args.output_dir, f), os.path.join(args.copy_report, f))

"""
CHANGE LOG:

-----------
$Log: ecu_sil_test_main.py  $
Revision 1.2 2020/03/31 08:45:36CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 20:55:16CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/executable/project.pj
"""