import os
import argparse
import logging
from subprocess import Popen


__author__ = "Suraj Saw"
__version__ = "$Revision: 1.0 $"
__maintainer__ = "$Duan Shikun(uie89573) $"
__date__ = "$Date: 2023/02/20 17:53:03CEST $"

_log = logging.getLogger("Starting Checkpoint craetion...")

class CreateSandbox(object):

    def create_sandbox(self, project, mts_root, cr_cp_ars, pwd): #, sim_config , mfc_mts_root, cr_cp_mfc, vsc_root, cr_cp_vsc

        user = os.environ["USERNAME"]
        # password=str(input("For Checkpint creation provide your *PASSWORD* and press enter:"))
        if cr_cp_ars:
            _log.info("Starting ARS checkpoint creation...")
            ars_label = cr_cp_ars
            ars_mtsroot = mts_root
            password = str(pwd)
            prj = str(project)
            # str_con_ars = (
            # """si createsandbox --project="/nfs/projekte1/PROJECTS/ARS400/06_Algorithm/05_Testing/06_Test_Tools/project.pj" --scope=subproject:#s=mts\project.pj,subproject:#s=mts_measurement\project.pj -R -Y --cwd="{2}" --projectRevision={1} --hostname=ims-adas --port=7001 --user={0}""").format(
            #     user, ars_label, ars_mtsroot)
            #
            # Popen(str_con_ars).communicate()

            str_con_ars = (
                """si createsandbox --project="/ADAS/SW/Projects/ARS51x/{4}/MTS/05_Testing/MTS/project.pj" --scope=subproject:#s=mts_system\project.pj,subproject:#s=mts_measurement\project.pj --nopopulate --norecurse --noopenview --cwd="{2}" --projectRevision={1} --hostname=ims-adas --port=7001 --user={0} --password={3}""").format(
                user, ars_label, ars_mtsroot, password, project)

            Popen(str_con_ars).communicate()

            str_con_resync_ars = (
                """si resync --hostname=ims-adas --port=7001 --nomerge --overwriteChanged --sandbox={1}/mts_measurement/project.pj --recurse --user={0}""").format(
                user, mts_root)
            Popen(str_con_resync_ars).communicate()

            str_con_resync_ars = (
                """si resync --hostname=ims-adas --port=7001 --nomerge --overwriteChanged --sandbox={1}/mts/project.pj --recurse --user={0}""").format(
                user, mts_root)
            Popen(str_con_resync_ars).communicate()
    #



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Help to creates the algo and mfc checkpoint.")
    parser.add_argument("project", help="The project name (e.g. ARS410GY18).")
    parser.add_argument("--mts_root", help="Path to the folder containing the mts and mts_measurement for ARS.")
    parser.add_argument("--mfc_mts_root", help="Path to the folder containing the mts_system and mts_measurement for MFC")
    parser.add_argument("--vsc_root", help="Path to the folder to download VSC sandbox")

    parser.add_argument("--cr_cp_ars", "-ars",  help="Create algo checkpoint(ars).")
    parser.add_argument("--cr_cp_mfc", "-mfc",  help="Create camera checkpoint (mfc).")
    parser.add_argument("--cr_cp_vsc", "-vsc", help="Create camera checkpoint (mfc).")
    parser.add_argument("--pwd", help="password for current user log in" )


    args = parser.parse_args()
    if args.cr_cp_ars:
        CreateSandbox().create_sandbox(args.project, args.mts_root, args.cr_cp_ars, args.pwd)


