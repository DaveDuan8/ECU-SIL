import multiprocessing
from psutil import virtual_memory
import subprocess
import time
import xml.etree.ElementTree as et
import os


class RunLocalSimulationMTS:

    def __init__(self, sim_path, bpl, cfgs):
        mem = virtual_memory()
        self.ram_gb = mem.total / 1000000000
        self.cpu_cores = multiprocessing.cpu_count()
        self.maximum_mts_instances = max(1, min(int(self.ram_gb/4/2), self.cpu_cores))
        self.sim_path = sim_path
        self.cmds = []
        self.recordings = []
        self.get_rec_names(bpl)
        self.create_mts_cmds(cfgs)

    def get_rec_names(self, bpl):
        tree = et.parse(bpl)
        root = tree.getroot()
        for child in root:
            attributes = child.attrib
            file_name = attributes["fileName"]
            self.recordings.append(file_name)

    def create_mts_cmds(self, cfgs):
        for cfg in cfgs:
            for rec in self.recordings:
                # str("measapp.exe -lc" + cfg_awv + " -lr" + rec + " -pal -eab -silent -norestart")
                self.cmds.append(str(os.path.join(self.sim_path, r"mts\measapp.exe") + " -lc" +
                                     os.path.join(self.sim_path, r"mts_measurement\cfg\algo\joint", cfg) + " -lr" +
                                     rec + " -pal -eab -silent -norestart"))

    def run(self):
        running_mts_instances = 0
        running_process = []
        free = []
        for cmd in self.cmds:
            if running_mts_instances < self.maximum_mts_instances:
                if len(running_process) < self.maximum_mts_instances:
                    running_process.append(subprocess.Popen(cmd))
                    time.sleep(15)
                else:
                    for idx in range(0, len(free)):
                        running_process[free.pop(0)] = subprocess.Popen(cmd)
                        time.sleep(15)
                running_mts_instances += 1
            else:
                print("wait")
                while running_mts_instances >= self.maximum_mts_instances:
                    time.sleep(5)
                    for idx in range(0, len(running_process)):
                        if running_process[idx].poll() is not None:
                            print "one job ends idx"
                            running_mts_instances -= 1
                            free.append(idx)
        print("wait until last job is done")
        for idx in range(0, len(running_process)):
            running_process[idx].wait()
        return os.path.join(self.sim_path, r"mts_measurement\data")
