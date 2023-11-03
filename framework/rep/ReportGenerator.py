import subprocess
import xml.etree.ElementTree as et


class ReportParameter:

    def __init__(self, pre_fix, middle_fix, cycle, cfg):
        self.pre_fix = pre_fix
        self.middle_fix = middle_fix
        self.cycle = cycle
        self.cfg = cfg


class ReportGenerator:

    def __init__(self, proj, label, report_destination, bpl, input_data, components):
        self.proj = proj  # "AL_ARS510VW19"
        self.label = label  # "AL_ARS510VW19_04.00.00_INT-39SIM2"
        self.bpl = bpl
        self.prog = "ecu_sil_test_main.py"
        self.input_data = input_data
        self.components = components
        self.report_destination = report_destination
        self.file_names = []

    def get_rec_names(self, bpl):
        tree = et.parse(bpl)
        root = tree.getroot()
        for child in root:
            attributes = child.attrib
            file_name = attributes["fileName"].split("\\")[-1]
            self.file_names.append(file_name)

    @staticmethod
    def create_bpl(bpl_name, recs):
        bpl = open(bpl_name, "w")
        bpl.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n')
        bpl.write("<BatchList>\n")
        for rec in recs:
            bpl.write("    <BatchEntry fileName=\"" + rec + "\">\n")
            bpl.write("        <SectionList/>\n")
            bpl.write("    </BatchEntry>\n")
        bpl.write("</BatchList>\n")
        bpl.close()

    def reporter(self, pre_fix, middle_fix, cycle, cfg):
        tmp_bpl = "D:\\bpl\\tmp.bpl"
        self.get_rec_names(self.bpl)
        for rec in self.file_names:
            self.create_bpl(tmp_bpl, [rec])
            post_fix = "_" + rec[0:-5]
            #
            report_name = self.proj + pre_fix + "_ECU_SIL_TestReport_" + middle_fix + post_fix + ".pdf"
            print report_name
            tmp = str("python " + self.prog + " " + self.proj + " " + self.label + " " +
                      tmp_bpl + " " + cfg + " --bsigs_dir " + self.input_data + " --copy_report " +
                      self.report_destination + " --cycle_1 " + cycle[0] + " --cycle_2 " + cycle[1] +
                      " --report_name " + report_name)
            print tmp
            p = subprocess.Popen(tmp)
            p.wait()
        return 0

    def run(self):
        for component in self.components:
            self.reporter(component.pre_fix, component.middle_fix, component.cycle, component.cfg)
