import os
import shutil
import xml.etree.ElementTree as et


class CheckinReportsARS510LegacyIMS:

    def __init__(self, change_package_id, checkin_path, project, label, bpl):
        self.changePackageID = change_package_id
        self.checkin_path = checkin_path
        self.project = project
        self.label = label
        self.bpl = bpl
        self.report_prefix = "AL_" + project

    def get_rec_names(self):
        tree = et.parse(self.bpl)
        root = tree.getroot()
        file_names = []
        for child in root:
            attributes = child.attrib
            file_name = attributes["fileName"].split("\\")[-1]
            file_names.append(file_name)
        return file_names

    def update_report(self, _cfg, _component):
        recs = self.get_rec_names()
        file_middle = ""
        if _cfg == "ALL":
            file_middle = "_" + _cfg
        elif _cfg == "_ALL":
            file_middle = _cfg

        dest_file = self.checkin_path + self.report_prefix + file_middle + "_ECU_SIL_TestReport_" + _component + ".pdf"
        counter = 1
        for rec in recs:
            post_fix = "_" + str(rec[0:-5])

            src_file = str(self.checkin_path + self.report_prefix + file_middle + "_ECU_SIL_TestReport_" + _component +
                           post_fix + ".pdf")

            description_text = "\"ECU-SIL Report for -AL-CP: " + self.label + " ; -cfg-Type:" + _cfg +\
                               " ; -Component: " + _component + " ; -Recording: " + rec + "\""
            counter += 1

            if os.path.isfile(src_file):
                co = str("si co --lock --cpid=" + self.changePackageID + " -f --forceConfirm=yes " + dest_file)
                print co
                # p1 = subprocess.Popen(co)
                # p1.wait()

                shutil.copy(src_file, dest_file)

                ci = str("si ci --lock --cpid=" + self.changePackageID + " --update --description=" + description_text +
                         " " + dest_file)
                print ci
                # p2 = subprocess.Popen(ci)
                # p2.wait()
            else:
                print(src_file + " not Exist")
        un = str("si unlock --action=remove " + dest_file)
        print un
        # p3 = subprocess.Popen(un)
        # p3.wait()

        return 0

    def run(self, components):
        for component in components:
            self.update_report(component.pre_fix, component.middle_fix)
#
#
# # cfg = "ALN"
# # component = "ALN"
# # updateReport(changePackageID,SandboxPath,al_cp,FilePre,cfg,component,bpl)
#
# cfg = "ALL"
# component = "ALN"
# # updateReport(changePackageID,SandboxPath,al_cp,FilePre,cfg,component,bpl)
#
# # cfg = "VDY"
# # component = "VDY"
# # updateReport(changePackageID,SandboxPath,al_cp,FilePre,cfg,component,bpl)
#
# cfg = "ALL"
# component = "VDY"
# # updateReport(changePackageID,SandboxPath,al_cp,FilePre,cfg,component,bpl)
#
# # cfg = "ALL"
# # component = "RSP1"
# # updateReport(changePackageID,SandboxPath,al_cp,FilePre,cfg,component,bpl)
#
# # cfg = "RSP1"
# # component = "RSP1"
# # updateReport(changePackageID,SandboxPath,al_cp,FilePre,cfg,component,bpl)
#
# cfg = "ALL"
# component = "RSP2"
# # updateReport(changePackageID,SandboxPath,al_cp,FilePre,cfg,component,bpl)
#
# # cfg = "RSP2"
# # component = "RSP2"
# # updateReport(changePackageID,SandboxPath,al_cp,FilePre,cfg,component,bpl)
#
# cfg = "ALL"
# component = "EM"
# updateReport(changePackageID, SandboxPath, al_cp, FilePre, cfg, component, bpl)
#
# # cfg = "EM"
# # component = "EM"
# # updateReport(changePackageID,SandboxPath,al_cp,FilePre,cfg,component,bpl)
#
# cfg = "ALL"
# component = "FCT"
# # updateReport(changePackageID,SandboxPath,al_cp,FilePre,cfg,component,bpl)
#
# # cfg = "FCT"
# # component = "FCT"
# # updateReport(changePackageID,SandboxPath,al_cp,FilePre,cfg,component,bpl)
#
# cfg = "ALL"
# component = "ACC-AWV"
# updateReport(changePackageID, SandboxPath, al_cp, FilePre, cfg, component, bpl)
