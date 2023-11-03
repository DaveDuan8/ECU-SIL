import os
import subprocess


class EnviromentARS510LegacyIMS:
    def __init__(self, label, project, dev_path, sandbox_base_path=r"D:\Sandboxes\automatedECUSIL"):
        self.label = label
        self.project = project
        self.dev_path = dev_path
        self.build_sandbox_base_path = os.path.join(sandbox_base_path, project, label)
        self.checkin_sandbox_base_path = os.path.join(sandbox_base_path, project, dev_path)
        self.project_path = "/nfs/projekte1/PROJECTS/SMR400/06_Algorithm/project.pj"
        print label

    def get(self):
        cmd = "si viewprojecthistory --rfilter=labeled:" + self.label + " --project="+self.project_path
        p_ims = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        # p_ims.wait()
        sandbox_revision = p_ims.communicate()[0].split()[1]
        print sandbox_revision
        cmd = "si createsandbox --project=" + self.project_path + " --projectRevision=" + sandbox_revision +\
              " --norecurse " + self.build_sandbox_base_path
        print cmd
        p_ims = subprocess.Popen(cmd)
        # p_ims.wait()
        cmd = str(r"si resync -R --sandbox=" + self.build_sandbox_base_path +
                  r"\05_Testing\06_Test_Tools\mts_measurement\project.pj")
        p_ims = subprocess.Popen(cmd)
        # p_ims.wait()
        cmd = str(r"si resync -R -f --sandbox=" + self.build_sandbox_base_path +
                  r"\05_Testing\06_Test_Tools\mts\project.pj")
        p_ims = subprocess.Popen(cmd)
        # p_ims.wait()
        cmd = str(r"si resync -R -f --sandbox=" + self.build_sandbox_base_path +
                  r"\05_Testing\05_Test_Environment\algo\inttests\project.pj")
        p_ims = subprocess.Popen(cmd)
        # p_ims.wait()
        cmd = str("si createsandbox --project=" + self.project_path + " --devpath=" + self.dev_path + " --norecurse " +
                  self.checkin_sandbox_base_path)
        p_ims = subprocess.Popen(cmd)
        # p_ims.wait()
        return (self.build_sandbox_base_path, os.path.join(self.build_sandbox_base_path, r"05_Testing\06_Test_Tools"),
                self.checkin_sandbox_base_path, os.path.join(self.checkin_sandbox_base_path,
                                                             r"05_Testing\02_Reports\algo\inttests"))

    def drop(self):
        cmd = "si dropsandbox --delete=members -f --noconfirm " + self.checkin_sandbox_base_path+"\project.pj"
        p_ims = subprocess.Popen(cmd)
        p_ims.wait()

        cmd = "si dropsandbox --delete=members -f --noconfirm " + self.build_sandbox_base_path+"\project.pj"
        p_ims = subprocess.Popen(cmd)
        p_ims.wait()
