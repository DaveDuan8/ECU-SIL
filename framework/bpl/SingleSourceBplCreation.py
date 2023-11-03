import os
import gc
import subprocess
from csv import DictReader
from collections import defaultdict


class SingleSourceBplCreation:

    def __init__(self, recordings, sim_path, al_cp):
        print recordings[-5:-1].lower()

        self.bpl_file = os.path.join("..", "..", "output", al_cp + ".bpl")
        self.sim_path = sim_path
        self.cfg = "REC_Test_ECU_SIL_ARS510.cfg"
        self.entry_folder = recordings

        self.suffix = [".rrec"]
        # if projects in the future other cycle setup this have to be changed as parameters START
        self.max_allowed_start_counter = 250  # based on 60ms
        self.fast_cycle_correction_ID = [207]
        self.fast_cycle_correction_factor = [3]  # based on 20ms
        # END
        self.dirs = {}
        self.cycles = ["REC_Test_ECU_SIL_204", "REC_Test_ECU_SIL_205", "REC_Test_ECU_SIL_207", "REC_Test_ECU_SIL_208"]
        self.sensor_cover_test_cycle = 205
        self.cycle_data = []
        self.ecu_sil_requirements = None
        self.ecu_sil_quality = None
        self.ecu_sil_information = None

    def get(self):
        if self.entry_folder[-4:].lower() == ".bpl":
            self.bpl_file = self.entry_folder
            return self.bpl_file

        fw = open(self.bpl_file, "w")
        for suffix in self.suffix:
            self.treewalker(self.entry_folder, self.callback, suffix)
        fw.write("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n")
        fw.write("<BatchList>\n")
        for d in self.dirs.keys():
            l = self.dirs[d]
            if len(l) > 0:
                for f in l:
                    self.check_recording(f)
                    fw.write("  <!-- ECU-SIL Quality:      %s -->\n" % self.ecu_sil_quality)
                    fw.write("  <!-- ECU-SIL Requirements: %s -->\n" % self.ecu_sil_requirements)
                    fw.write("  <!-- ECU-SIL Information:  %s -->\n" % self.ecu_sil_information)
                    if self.ecu_sil_quality is False or self.ecu_sil_requirements is False:
                        fw.write("  <!--\n")
                    fw.write("    <BatchEntry fileName=\"%s\">\n" % f)
                    fw.write("       <SectionList/>\n")
                    fw.write("     </BatchEntry>\n")
                    if self.ecu_sil_quality is False or self.ecu_sil_requirements is False:
                        fw.write("  -->\n")
        fw.write("</BatchList>\n")
        fw.close()
        return self.bpl_file

    def treewalker(self, directory, callback, ftype):
        join = os.path.join
        self.dirs[directory] = []  # takes care of top directory
        for f in os.listdir(directory):
            path_name = join(directory, f)
            if os.path.isdir(path_name):
                self.dirs[path_name] = []  # add key
                print ("...in %s" % path_name)
                self.treewalker(path_name, callback, ftype)
            elif os.path.isfile(path_name):
                callback(path_name, ftype)
            if len(os.listdir(directory)) == 0:
                callback(path_name, ftype)

    def callback(self, pathname, ftype):

        dirname = os.path.dirname(pathname)
        # for ft in ftype:
        if os.path.splitext(pathname)[1] == ftype:
            self.dirs[dirname].append(os.path.normpath(pathname))

    @staticmethod
    def parse_csv(filename, fieldnames=None, delimiter=','):
        result = defaultdict(list)
        with open(filename) as infile:
            reader = DictReader(infile, fieldnames=fieldnames, delimiter=delimiter)
            for row in reader:
                for field_name, value in row.items():
                    result[field_name].append(value)
        gc.collect()
        return result

    def run_recording(self, rec):
        rec_check = str(os.path.join(self.sim_path, r"mts\measapp.exe") + " -lc" + os.path.join(os.getcwd(), '..', 'cfg', self.cfg) +
                        " -lr" + rec + " -pal -eab -silent -norestart")
        print rec_check
        p_rec_check = subprocess.Popen(rec_check)
        p_rec_check.wait()

        for suffix in self.suffix:
            if rec.endswith(suffix):
                    r = rec[:-len(suffix)]
                    for cycle in self.cycles:
                        _file = r.split("\\")[-1]
                        _file = _file + cycle + ".csv"
                        try:
                            tmp = self.parse_csv(os.path.join(self.sim_path, r"mts_measurement\data", _file))
                            self.cycle_data.append(tmp)
                        except os:
                            return False
        gc.collect()
        return True

    def check_init(self, csv):
        sensor_initialization = True
        factor = 1
        for item in csv.items():
            if item[0].find("MTS.Package.CycleID"):
                for entry in item[1]:
                    for i in range(0, len(self.fast_cycle_correction_ID)):
                        if int(entry) == 0:
                            continue
                        elif int(entry) == self.fast_cycle_correction_ID[i]:
                            factor = self.fast_cycle_correction_factor
                            break
        for item in csv.items():
            if item[0].find("MeasurementCounter") != -1 or item[0].find("CycleCounter") != -1:
                for entry in item[1]:
                    if int(entry) == 0:
                        continue
                    elif int(entry) != 0 and int(entry) > self.max_allowed_start_counter * factor:
                        print("In the CSV-File %s: Sensor Initialization problem detected: %s" % (csv, item[0]))
                        sensor_initialization = False
                        break
                    else:
                        break
            del item
        gc.collect()
        return sensor_initialization

    def check_sensor_initialization(self):
        for csv in self.cycle_data:
            if self.check_init(csv):
                continue
            else:
                return False
        gc.collect()
        return True

    def check_sensor_covering(self):
        signal_found = False
        counter = 0
        for csv in self.cycle_data:
            for item_ in csv.items():
                if item_[0].find("MTS.Package.CycleID"):
                    for entry_ in item_[1]:
                        for i in range(0, len(self.fast_cycle_correction_ID)):
                            if int(entry_) == 0:
                                continue
                            elif int(entry_) == self.fast_cycle_correction_ID[i]:
                                for item in csv.items():
                                    if item[0].find("DataProcCycle.EmGenObjectList.HeaderObjList.iNumOfUsedObjects") !=\
                                            -1:
                                        counter = 0
                                        for entry in item[1]:
                                            if int(entry) == 0:
                                                counter += 1
                                                continue
                                            elif int(entry) != 0:
                                                break
                                            del entry
                                    del item
                                gc.collect()
                                if signal_found:
                                    if counter > 150:
                                        return True, ""
                                    else:
                                        return False, ""
        return True, "Sensor covering Signal not found!"

    def check_restart(self, csv):
        sensor_restart = False

        for item in csv.items():
            if item[0].find("MeasurementCounter") != -1 or item[0].find("CycleCounter") != -1:
                last_value = -1
                for entry in item[1]:
                    if last_value == -1:
                        last_value = int(entry)
                        continue
                    elif 0 < last_value < 65534 and int(entry) < last_value and int(
                            entry) == self.max_allowed_start_counter:
                        print("In the CSV-File " +
                              "%s: Sensor Reset problem detected: %s  jumps from %d to %d " % (csv, item[0],
                                                                                               last_value, int(entry)))
                        sensor_restart = True
                        break
                    else:
                        last_value = int(entry)
        gc.collect()
        return sensor_restart

    def check_sensor_restart(self):
        for csv in self.cycle_data:
            if self.check_restart(csv):
                continue
            else:
                return False
        gc.collect()
        return True

    @staticmethod
    def check_sync_ref_qual(csv):
        syn_ref_quality = True
        packages = 0
        for item in csv.items():
            if item[0].find("SyncRef") != -1 and (item[0].find("MeasurementCounter") != -1 or
               item[0].find("CycleCounter") != -1 or item[0].find("TimeStamp") != -1) and item[0].find("Dummy") == -1:
                last_value = -1
                if item[0].find("TimeStamp") != -1:
                    overflow_limit = 0xFFFFFFFFFFFFFFFE
                else:
                    overflow_limit = 65533
                for entry in item[1]:
                    packages += 1
                    if last_value <= 0:
                        last_value = int(entry)
                        continue
                    elif 0 < last_value < overflow_limit and int(entry) < last_value:
                        print("In the CSV-File " +
                              "%s: SynRef Quality problem detected: %s goes from %d to %d" % (csv, item[0], last_value,
                                                                                              int(entry)))
                        syn_ref_quality = False
                        last_value = int(entry)
                    else:
                        last_value = int(entry)
                gc.collect()
        gc.collect()
        return syn_ref_quality

    def check_sync_ref_quality(self):
        for csv in self.cycle_data:
            if self.check_sync_ref_qual(csv):
                continue
            else:
                return False
        gc.collect()
        return True

    def check_recording(self, f):
        self.ecu_sil_quality = False
        self.ecu_sil_requirements = False
        self.ecu_sil_information = ""
        print("Recording: %s" % f)
        if self.run_recording(f):
            print("Load Recording: Sucessfull")

            print("Check sensor_initialization")
            sensor_initialization = self.check_sensor_initialization()
            print("sensor_initialization: %s" % sensor_initialization)

            print("Check sensor_covering")
            sensor_covering, msg = self.check_sensor_covering()
            print("sensor_covering: %s %s" % (sensor_covering, msg))

            print("Check sensor_restart")
            sensor_restart = self.check_sensor_restart()
            print("sensor_restart: %s" % sensor_restart)

            print("Check package_quality")
            package_quality = self.check_sync_ref_quality()
            print("package_quality: %s" % package_quality)

            if sensor_initialization and sensor_covering:
                self.ecu_sil_requirements = True
            if sensor_restart and package_quality:
                self.ecu_sil_quality = True
            if self.ecu_sil_requirements and sensor_restart:
                if msg == "":
                    self.ecu_sil_information = "Recording is complete ECU-SIL use able"
                else:
                    self.ecu_sil_information = "Recording is complete ECU-SIL use able " + msg
            elif self.ecu_sil_requirements and sensor_restart is False and (sensor_restart is False and
                                                                            package_quality > 98):
                if msg == "":
                    self.ecu_sil_information = "Recording is limited ECU-SIL use able, but no analysis for failed" \
                                               " TestCases possible from SIL Team, Required Packages missing"
                else:
                    self.ecu_sil_information = "Recording is limited ECU-SIL use able, but no analysis for failed" \
                                               " TestCases possible from SIL Team, Required Packages missing " + msg
            elif self.ecu_sil_requirements and self.ecu_sil_quality is False:
                self.ecu_sil_information = "Recording is NOT use able depends on bad data quality"
            elif self.ecu_sil_requirements is False and self.ecu_sil_quality:
                self.ecu_sil_information = "Recording is NOT use able; Requirements not fulfilled"
            elif self.ecu_sil_requirements is False and self.ecu_sil_quality is False:
                self.ecu_sil_information = "Recording is NOT use able; Requirements not fulfilled and bad data quality"
        else:
            print("Load Recording: Failed")
            self.ecu_sil_requirements = False
            self.ecu_sil_quality = False
            self.ecu_sil_information = "Recording is NOT available"
