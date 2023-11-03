"""
stk/mks/si
----------

**Module SI (Source Integrity)** provides an Interface to the Source Integrity client of MKS.

**User-API Interfaces**

    - `Si` (this module)
    - `stk.mks` (complete package)


:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.13 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/04/15 15:55:28CEST $
"""
# Import Python Modules -----------------------------------------------------------------------------------------------
import subprocess
import threading
from os import path as opath
from re import match

# Import STK Modules --------------------------------------------------------------------------------------------------

# Defines -------------------------------------------------------------------------------------------------------------
DEBUG = 0

# Functions -----------------------------------------------------------------------------------------------------------


# Classes -------------------------------------------------------------------------------------------------------------


class SiException(Exception):
    """
    Si Exception class which prints the Error Code and the message
    from the cli call.

    :author:        Robert Hecker
    :date:          26.04.2013
    """

    def __init__(self, error, message):
        Exception.__init__(self)
        self.error = error
        self.message = message

    def __str__(self):
        return "ErrorCode %d \n %s" % (self.error, self.message)


class RunCmd(threading.Thread):
    """
    class from http://stackoverflow.com/questions/4158502/python-kill-or-terminate-subprocess-when-timeout
    to run a command with given timeout.

    The command execution will be stopped after given number of seconds.

    It provides following parameters:
      out: stdout
      err: stderr
      returncode: returncode of communicate()

    """
    def __init__(self, cmd, timeout=None):
        """
        initialize the command, its parameters and the timeout

        :param cmd: command and parameter list as used in Popen
        :type  cmd: list
        :param timeout: time in seconds after which the execution should be killed
        :type  timeout: int
        """
        threading.Thread.__init__(self)
        self.prc = None
        self.cmd = cmd
        self.timeout = timeout
        self.out = None
        self.err = None
        self.returncode = 0

    def run(self):
        """
        overwriting Thread.run()
        """
        self.prc = subprocess.Popen(self.cmd, stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        # self.prc.wait()
        self.out, self.err = self.prc.communicate()
        self.returncode = self.prc.returncode

    def run_dur(self):
        """
        final method to start a new command with given timeout

        usage:

          RunCmd(["./someProg", "arg1"], 60).run_dur()
        """
        self.start()
        self.join(self.timeout)

        if self.is_alive():
            self.prc.kill()      # use self.prc.kill() if process needs a kill -9
            self.join()
            self.err = 'Timeout: command terminated!'
            self.returncode = -15


class Si(object):
    """
    The Si-class provides an Interface to the CommandLine Interface of the
    MKS Source-Integrity.
    With this class you are able to connect to the mks-server, and do some
    actions like CreateSandbox, CheckOutMember, Checkpoint,.....

    This class is a wrapper over the CLI which can normally be used in a cmd-prompt.

    :note:      usage: See two examples below.

    :author:    Robert Hecker
    :date:      26.04.2013

    Example 1: (Uses an existing mks server connection)
    ---------------------------------------------------
    .. python::
        from stk.mks.si import Si

        #Create Instance of Source Integrity
        si = Si()

        # Create Directory for the Sandbox
        sandboxdir = os.path.join(os.path.split(__file__)[0], "MySandbox")

        # Create Sandbox
        si.createsandbox(MKSPROJECT, sandboxdir)

        # Drop MKS Sandbox, but don't delete the files
        si.dropsandbox(sandboxdir)


    Example 2: (Creates a new mks server connection)
    ------------------------------------------------
    .. python::
        from stk.mks.si import Si

        si = Si()

        # Setup a new MKS Connection
        si.connect("heckerr", "Password")

        si.setChangePackageId("106870:1")

        # Create Directory for the Sandbox
        sandboxdir = os.path.join(os.path.split(__file__)[0], "MySandbox")

        # Create Sandbox
        si.createsandbox(MKSPROJECT, sandboxdir)

        # Checkout the file
        mks.co(path)

        # Update a member file
        # Put your code here !!!!

        # Checkin file
        mks.ci(path, "BugFix for wrong KPI calc")

        # Set Member Version of File
        mks.updaterevision(path)

        si.dropsandbox(sandboxdir, "all")

        si.disconnect()
    """
    # pylint: disable=C0103
    def __init__(self):
        """
        In the constructor all common needed parameters for all methods
        are initialized.
        """
        self._cpid = ""

    def set_changepackage_id(self, cpid):
        """
        For some commands a ChangePackageId is needed.

        The ChangePackage Id is a string, and is build from
        the Task Id and the ChangePackageId, separated with
        a doubledot.
        Example: 107998:0

        :param cpid: TaskId:ChangePackageId formatted string
        :type cpid:  str
        :return:     -

        :author:        Robert Hecker
        :date:          26.04.2013
        """
        self._cpid = cpid

    def _exe_cmd(self, arg, timeout=None):  # pylint: disable=R0201
        """
        Executes the command with the given parameters, and returns
        when execution is finished.

        :param arg: Arguments for cli call
        :type arg:  list(str)
        :param timeout: time in seconds after which the execution should be killed
        :type  timeout: int
        :return:    Error Code from cli call

        :author:        Robert Hecker
        :date:          26.04.2013
        """

        # Execute the command
        # cli = subprocess.Popen(arg, shell=True, stdin=subprocess.PIPE,
        #                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        cmd = RunCmd(arg, timeout)
        cmd.run_dur()

        # out = cli.communicate()[0].splitlines()
        # error = cli.returncode
        out = cmd.out.splitlines()
        error = cmd.returncode

        if error != 0:
            # Create cli string
            # callstring = ""
            # for el in arg:
            # callstring += el
            #     callstring += " "

            # Get Return String
            raise SiException(error, cmd.out)

        return out

    def connect(self, user, pwd, hostname="ims-adas", port=7001):
        """
        establishes a connection to an Integrity Server.

        This connection will be used for all other commands till a disconnect is done.
        When the connect method is not used, the cli interface try to use a existing connection
        to the mks server. For example over the GUI Interface.
        Multiple Connections for different Servers are not supported, you must use disconnect
        to disconnect from one host before establishing a connection to another.

        :param user:     MKS-USerName
        :type user:      str
        :param pwd:      Password for MKS-Server
        :type pwd:       str
        :param hostname: Name, of server used for connection
        :type hostname:  str
        :param port:     Port
        :type port:      int
        :return:         -

        :author:           Robert Hecker
        :date:             26.04.2013
        """
        arg = ["si", "connect", "--hostname=" + hostname, "--port=" + str(port),
               "--password=" + pwd, "--user=" + user,
               "--quiet", "--batch"]

        # Execute Command
        return self._exe_cmd(arg)

    @property
    def disconnect(self):
        """
        disconnects the client connection to the host Integrity Server.

        The disconnect call will disconnect all client connections to the Server,
        also the GUI based connections.

        :author:           Robert Hecker
        :date:             26.04.2013
        """
        # --batch: without prompting for responses.
        arg = ["si", "disconnect", "--forceConfirm=yes", "--quiet", "--batch"]

        # Execute Command
        return self._exe_cmd(arg)

    def createsandbox(self, project, sandboxdir, revision=None, skip_subpro=False):
        """
        Creates a new sandbox on your local machine.
        The sandbox will be created from the Project specified
        by the project parameter to the path given by the sandboxdir.

        You should only create the sub project you need, or several if needed,
        otherwise you will get several GB of data!

        Using the parameter 'revision' you can create a build sandbox.
        To find the correct string you can use ::

            si viewprojecthistory --project=/nfs/projekte1/REPOSITORY/Base_Development/
            05_Algorithm/STK_ScriptingToolKit/project.pj  --rfilter=labellike:*STK_02.01*INT-2

        :param project:    mks project path
        :type project:     str
        :param sandboxdir: local dir for sandbox
        :type sandboxdir:  str
        :param revision:   opt mks project checkpoint to create build sandbox
        :type revision:    str
        :param skip_subpro:  opt to leave out subprojects, default: use all subprojects
        :type  skip_subpro:  bool
        :return:           Error Code
        :note:             The project parameter must start with /nfs/... and
                           end with "/project.pj"
                           Example:
                           "/nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/project.pj"

        :author:           Robert Hecker
        :date:             26.04.2013
        """
        # --yes: Recursive
        # --batch: without prompting for responses.
        arg = ["si", "createsandbox", "--project=" + project]
        if revision:
            arg.append("--projectRevision=" + revision)
        if skip_subpro:
            arg.append("--norecurse")
        arg.extend(["--cwd=" + sandboxdir, "--quiet", "--yes", "--batch"])

        # Execute Command
        return self._exe_cmd(arg)

    def dropsandbox(self, sandboxdir, delete="none"):
        """
        drops a sandbox

        Following options for delete are possible:
        - "none"
        - "members"
        - "all"

        :param sandboxdir: local dir for sanbox
        :type sandboxdir:  str
        :param delete:     [none|members|all]
        :type delete:      str
        :return:           Error Code

        :author:           Robert Hecker
        :date:             26.04.2013
        """
        # --batch: without prompting for responses.
        arg = ["si", "dropsandbox", "--forceconfirm=yes", "--batch", "--delete=" + delete, sandboxdir + "\\project.pj"]

        # Execute Command
        return self._exe_cmd(arg)

    def co(self, memberpath, lock=True, revision=None):
        """
        checks out members into working files in a sandbox

        if file should be locked (default) a ChangePackage has to be defined using `set_changepackage`

        :param memberpath: sandboxpath to member
        :type memberpath:  str
        :param lock:       lock member, if set to False no ChangePackage will be used
        :type lock:        boolean
        :return:           Error Code

        :author:           Robert Hecker
        :date:             26.04.2013
        """
        arg = ["si", "co"]
        if lock:
            # checkout with locking the version only with cpid!
            arg.extend(["-l", "--changePackageId=" + self._cpid])
        else:
            arg.append("-u")
        if revision:
            arg.append("--revision=" + revision)
        arg.append(memberpath)

        return self._exe_cmd(arg)

    def ci(self, memberpath, desc):
        """
        checks in members of a sandbox

        :param memberpath: sandboxpath to member
        :type memberpath:  str
        :param desc:       check in description
        :type desc:        str
        :return:           Error Code

        :author:           Robert Hecker
        :date:             26.04.2013
        """
        arg = ["si", "ci", "--changePackageId=" + self._cpid, "--description=" + desc, "--unlock", memberpath]

        return self._exe_cmd(arg)

    def updaterevision(self, memberpath, rev=":head"):
        """
        updates a project member revision to a specified revision

        Following options for rev are possible:
        - Revision Number      1.35
        - Label                Label string to use
        - :head                identifies the head revision.
        - :member              identifies the member revision.
        - :memberbranchtip    identifies the tip revision on the member revision branch.
        - :trunktip           identifies the tip revision on the trunk.

        :param memberpath: local path to member.
        :type memberpath:  str
        :param rev:        [RevNum|Label|:head|...]
        :type rev:         str
        :return:           Error Code

        :author:           Robert Hecker
        :date:             26.04.2013
        """
        arg = ["si", "updaterevision", "--changePackageId=" + self._cpid, "--revision=" + rev, "--quiet", "--no",
               memberpath]

        return self._exe_cmd(arg)

    def checkpoint(self, sandbox, desc, label, labelMembers=False):
        """
        checkpoint archives in a project

        :param sandbox:      local path sandbox.
        :type sandbox:       str
        :param desc:         Checkpoint Description.
        :type desc:          str
        :param label:        Checkpoint Label.
        :type label:         str
        :param labelMembers: Label Members (true/false)
        :type labelMembers:  boolean
        :return:             Error Code

        :author:             Robert Hecker
        :date:               26.04.2013
        """
        if sandbox.endswith(r"\project.pj") is False:
            lsandbox = sandbox + r"\project.pj"
        else:
            lsandbox = sandbox
        arg = ["si", "checkpoint", "--quiet", "--description=" + desc]
        # arg.append("--changePackageId=" + self._cpid)
        if labelMembers:
            arg.append("--labelMembers")
        else:
            arg.append("--nolabelMembers")
        arg.extend(["--label=" + label, "--sandbox=" + lsandbox])

        return self._exe_cmd(arg)

    def addlabel(self, folder, label, *options):
        """
        set label in given folder recursively

        :param folder: path of sandbox where to set the label
        :type  folder: str
        :param label:  label to set to each member of given folder
        :type  label:  str
        :return: output of mks to parse, print etc.
        """
        if not opath.isdir(folder):
            raise SiException(1, "si.addlabel called with wrong folder path or path missing: {}".format(folder))
        folder += r'\*'

        arg = ['si', 'addlabel', '-R', '-L {}'.format(label)]
        arg.extend([i for i in options])
        arg.append(folder)

        return self._exe_cmd(arg)

    def resync(self, path):
        r"""
        updates a Sandbox, SubSandbox or member file with the member revision

        :param path: either path to a sandbox (including \*.pj file) or path to sandbox subfolder (including \*.pj) or
                     path to sandbox member.
        :type path:  str
        :return:     Error Code

        :author:     Robert Hecker
        :date:       26.04.2013
        """
        arg = ["si", "resync", "--quiet", "--batch", "--recurse", "--forceConfirm=yes", str(path)]

        return self._exe_cmd(arg)

    def get_file_revision(self, filepath):
        """
        return the working and member revision of the given file of a sandbox

        The file must be in a sandbox so mks can use the project.pj file in the directory.

        If only a path without filename is passed as filepath that is searched recursively,
        the resulting dict contains all file revisions.

        returns a dictionary with filepath as key and following values for each file entry:

        - is_ori_member_rev: True if member_rev == working_rev AND file unchanged, else False
        - working_rev: string of working revision of the mks member
        - member_rev: string of member revision of the mks member
        - changed: True if file is not marked as updated/changed in mks sandbox, else False

        So a result for a sub project folder of a sandbox can look like:

        .. python::
            mks_si = si.Si()
            res = mks_si.get_file_revisions(r'd:\\sandbox\\project\\path\\to\\files\\file.name')
            # results in:                                          ori_head?  w_rev  m_rev changed?
            # res -> {'d:\\sandbox\\project\\path\\to\\files\\file.name': [True, '1.3', '1.3', False]}
            # dict contains more files if a path without filename is passed

        meaning:

        - [True, '1.3', '1.3', False]: original head version (unchanged)
        - [False, '1.2', '1.3', False]: original old version (1.2), needs to be resynchronised
        - [False, '1.3', '1.3', True]: updated head version or deleted in sandbox,
          needs to be checked in or dropped or resynchronised
        - [False, '', '1.2', False]: old version which is dropped in main (no member revision),
          needs to be resynchronised (deleted)
        - [False, '1.3', '', True]: new file on head but not in sandbox, needs to be resynchronised


        The result does not contain folder names as these don't have a revision nor a changed info in mks.
        Use `get_checkpoint()` to read the checkpoint of a folder or file.

        If no MKS session can be established an empty dict is returned.

        :param filepath: absolut path and filename in some mks sandbox
        :type filepath:  string
        :return: dict of (filepath: [is_ori_member_rev, member_rev, working_rev, changed])
        :rtype: dict(list(boolean, str, str, boolean))
        """
        # si call return example:
        # si viewsandbox --cwd <filepath> --fields=name,workingrev,memberrev,wfdelta
        # d:\sandbox\STK\04_Engineering\stk\mks\__init__.py 1.5 1.5
        # d:\sandbox\STK\04_Engineering\stk\mks\im.py 1.3 1.3
        # Working file 3,413 bytes larger, newer (Mar 2, 2015 3:42:42 PM)
        # d:\sandbox\STK\04_Engineering\stk\mks\si.py 1.10 1.12
        #
        mks_files = {}
        sbname = ''
        if opath.isfile(filepath):
            [sbpath, sbname] = opath.split(filepath)
        else:
            sbpath = filepath

        arg = ["si", "viewsandbox", "--fields=name,workingrev,memberrev,wfdelta", "-R", "--cwd", sbpath, "-Y"]
        try:
            mks_out = self._exe_cmd(arg, 30)
        except SiException:
            return {}

        # for prev, line, nxt in previous_and_next(mks_out):
        mkspath = ""
        mrev = ""
        wrev = ""
        for line in mks_out:
            # a line starting with spaces gives a hint about the difference in the file listed before
            # mks output contains something like '    Working file 104 bytes larger, ...' starting with spaces
            if line.startswith('  '):
                mks_files[mkspath.lower()] = [False, mrev, wrev, True]
                continue
            try:
                [mkspath, wrev, mrev, _] = line.split(' ', 3)
                if opath.basename(mkspath) != 'project.pj':  # skip linked project dir, evaluate its files recursively
                    mks_files[mkspath.lower()] = [wrev == mrev, mrev, wrev, False]
            except ValueError:
                # might not be needed anymore as project dirs are caught directly
                pass

        return {filepath: mks_files[filepath.lower()]} if sbname else mks_files

    def get_checkpoint(self, filepath):
        """
        return the checkpoint of the project checked out to the sandbox

        The file/folder must be in some sandbox so mks can use the project.pj file in the directory.

        It returns the checkpoint string of:

        - a shared sub project
        - the build project used for the sandbox
        - the last checkpoint defined for the head or development branch used for the sandbox

        In case of problems (like no mks or no sandbox) an empty string is returned.

        :param filepath: path to the folder
        :type  filepath: str
        :return: project checkpoint like '5.1.4.23'
        :rtype:  str
        """
        # based on result of >si sandboxinfo --cwd d:\sandbox\STK\04_Engineering\stk
        # Sandbox Name: d:\sandbox\STK\04_Engineering\stk\project.pj
        # ...
        # Revision: 1.72
        # ...
        if opath.isfile(filepath):
            (sbpath, _) = opath.split(filepath)
        else:
            sbpath = filepath

        arg = ["si", "sandboxinfo", "--cwd", sbpath, "-Y"]
        try:
            mks_out = self._exe_cmd(arg, 30)
        except SiException:
            return ''
        rev = match(r".*Last Checkpoint: ([\d\.]*)", " ".join(mks_out)).group(1)
        return rev

    def get_checkpoint_label(self, filepath, checkpoint=None):
        """
        return the mks checkpoint label of file/folder of a sandbox

        the file/folder must be in a sandbox so mks can use the project.pj file in the directory,
        and mks must be available on the machine.

        If no checkpoint is given the returned label depends of the folder/sub project configuration of the sandbox.
        It returns the label of:

        - a shared sub project
        - the checkpoint of the build project used for the sandbox
        - the last checkpoint defined for the head or development branch used for the sandbox

        In case of problems (like no mks or no sandbox) empty strings are returned.

        :param filepath: absolute path and filename in some mks sandbox
        :type filepath:  str
        :param checkpoint: optional checkpoint to get the label for like '3.1.2.24'
        :type  checkpoint: str
        :return: checkpoint and checkpoint label of the mks project of the given file/folder
        :rtype: (str, str)
        """
        if opath.isfile(filepath):
            (sbpath, _) = opath.split(filepath)
        else:
            sbpath = filepath
        # get checkpoint value, then search for the label in the project history
        if not checkpoint:
            checkpoint = self.get_checkpoint(sbpath)

        label = ''
        cp_list = self.get_project_labels(sbpath)
        if checkpoint in cp_list:
            label = cp_list[checkpoint]

        return checkpoint, label

    def get_project_labels(self, sb_folder):
        r"""
        retrieve all labels stored for the subproject (and therefore for all files) of the passed sandbox folder

        mks outputs lines like::

            d:\sandbox\SW_ARS4D0\M11_Appl\04_Engineering\04_Build\out
            1.210	SW_ARS4D0_04.09.11
            1.209.1.3	SW_ARS4D0_04.09.10_INT-3
            1.209.1.2	SW_ARS4D0_04.09.10_INT-2
            1.209.1.1	SW_ARS4D0_04.09.10_INT-1
            1.209	SW_ARS4D0_04.09.10,SW_ARS4D0_04.09.10_RELEASE,SW_ARS4D0_04.59.10_DAI_HIL

        storing in dict::

            {'1.209': 'SW_ARS4D0_04.09.10,SW_ARS4D0_04.09.10_RELEASE,SW_ARS4D0_04.59.10_DAI_HIL',
             ...}

        :param sb_folder: sandbox folder of one (sub-) project
        :type  sb_folder: str
        :return: dict of all checkpoints with labels string
        :type:   dict
        """
        if opath.isfile(sb_folder):
            (sbpath, _) = opath.split(sb_folder)
        else:
            sbpath = sb_folder
        # si viewprojecthistory --cwd path --fields=revision,labels
        arg = ['si', 'viewprojecthistory', '--cwd', sbpath, '--fields=revision,labels']
        try:
            mks_out = self._exe_cmd(arg, 60)
        except SiException:
            return []

        cp_dict = {}
        for line in mks_out[1:]:  # skip first line, it contains file path and name
            sp = line.split(None, 1)
            if len(sp) > 1:
                cp_dict[sp[0]] = sp[1]
        return cp_dict

    def get_file_labels(self, file_path):
        r"""
        retrieve all labels stored for a file of the passed sandbox folder

        mks outputs lines like::

            d:\sandbox\SW_ARS4D0\M11_Appl\04_Engineering\04_Build\out\ARS4D0_Appl_Release.cdl
            1.210	SW_ARS4D0_04.09.11
            1.209.1.3	SW_ARS4D0_04.09.10_INT-3
            1.209.1.2	SW_ARS4D0_04.09.10_INT-2
            1.209.1.1	SW_ARS4D0_04.09.10_INT-1
            1.209	SW_ARS4D0_04.09.10,SW_ARS4D0_04.09.10_RELEASE,SW_ARS4D0_04.59.10_DAI_HIL

        storing in dict::

            {'1.209': 'SW_ARS4D0_04.09.10,SW_ARS4D0_04.09.10_RELEASE,SW_ARS4D0_04.59.10_DAI_HIL',
             ...}

        :param file_path: path and name of file in a sandbox
        :type  file_path: str
        :return: dict of all checkpoints with labels string
        :type:   dict
        """
        # si viewprojecthistory --cwd path --fields=revision,labels
        arg = ['si', 'viewhistory', '--fields=revision,labels', file_path]
        try:
            mks_out = self._exe_cmd(arg, 60)
        except SiException:
            return []

        cp_dict = {}
        for line in mks_out[1:]:  # skip first line, it contains file path and name
            sp = line.split(None, 1)
            if len(sp) > 1:
                cp_dict[sp[0]] = sp[1]
        return cp_dict

    def get_revision_descriptions(self, file_path):
        r"""
        retrieve all descriptions stored for a file of the passed sandbox folder

        mks outputs lines like::

            d:\sandbox\SW_ARS4D0\M11_Appl\04_Engineering\04_Build\out\ARS4D0_Appl_Release.cdl
            1.210	SW_ARS4D0_04.09.11
            1.209.1.3	SW_ARS4D0_04.09.10_INT-3
            1.209.1.2	SW_ARS4D0_04.09.10_INT-2
            1.209.1.1	SW_ARS4D0_04.09.10_INT-1
            1.209	SW_ARS4D0_04.09.10,SW_ARS4D0_04.09.10_RELEASE,SW_ARS4D0_04.59.10_DAI_HIL

        storing in dict::

            {'1.209': 'SW_ARS4D0_04.09.10,SW_ARS4D0_04.09.10_RELEASE,SW_ARS4D0_04.59.10_DAI_HIL',
             ...}

        :param file_path: path and name of file in a sandbox
        :type  file_path: str
        :return: dict of all checkpoints with labels string
        :type:   dict
        """
        # si viewprojecthistory --cwd path --fields=revision,labels
        arg = ['si', 'viewhistory', '--fields=revision,description', file_path]
        try:
            mks_out = self._exe_cmd(arg, 60)
        except SiException:
            return []

        cp_dict = {}
        for line in mks_out[1:]:  # skip first line, it contains file path and name
            sp = line.split(None, 1)
            if len(sp) > 1:
                cp_dict[sp[0]] = sp[1]
        return cp_dict

    def get_locked_members(self, sb_folder):
        """
        return all locked members in the given sandbox folder searching recursively,
        ignore files in shared projects

        :return: list with locked files
        """
        arg = ['si', 'viewlocks', '-R', '--cwd={}'.format(sb_folder), '--fields=membername,isreference']
        mks_out = self._exe_cmd(arg)
        res = []
        for line in mks_out:
            name, ref = line.split('\t')
            # check if file is in own project: reference =='0'
            if ref == '0':
                res.append(name)
        return res


"""
CHANGE LOG:
-----------
$Log: si.py  $
Revision 1.13 2016/04/15 15:55:28CEST Hospes, Gerd-Joachim (uidv8815) 
add path to cdl file name in ini file,
add csv file with labels and descriptions for all revisions
Revision 1.12 2016/03/24 22:46:19CET Hospes, Gerd-Joachim (uidv8815)
fix create sandbox without subprojects
Revision 1.11 2016/03/15 19:30:18CET Hospes, Gerd-Joachim (uidv8815)
add skip_subpro to createsandbox
Revision 1.10 2016/03/09 21:10:05CET Hecker, Robert (heckerr)
Removed deprecated function.
Revision 1.9 2015/12/03 17:46:48CET Hospes, Gerd-Joachim (uidv8815)
fix mks/ims keywords after update to ptc 10.6, pylint fixes
Revision 1.8 2015/10/26 16:39:47CET Hospes, Gerd-Joachim (uidv8815)
update mks server to ims-adas
Revision 1.7 2015/10/09 16:50:07CEST Hospes, Gerd-Joachim (uidv8815)
pep8 pylint fixes
--- Added comments ---  uidv8815 [Oct 9, 2015 4:50:08 PM CEST]
Change Package : 381253:1 http://mks-psad:7002/im/viewissue?selection=381253
Revision 1.6 2015/10/09 14:33:16CEST Hospes, Gerd-Joachim (uidv8815)
add get_file_labels
Revision 1.5 2015/09/25 11:55:50CEST Hospes, Gerd-Joachim (uidv8815)
fix call opts for si set label
--- Added comments ---  uidv8815 [Sep 25, 2015 11:55:50 AM CEST]
Change Package : 376211:1 http://mks-psad:7002/im/viewissue?selection=376211
Revision 1.4 2015/05/22 17:04:11CEST Hospes, Gerd-Joachim (uidv8815)
add excluding files from shared projects
--- Added comments ---  uidv8815 [May 22, 2015 5:04:12 PM CEST]
Change Package : 336934:1 http://mks-psad:7002/im/viewissue?selection=336934
Revision 1.3 2015/05/22 16:15:36CEST Hospes, Gerd-Joachim (uidv8815)
add get_locked_files
--- Added comments ---  uidv8815 [May 22, 2015 4:15:36 PM CEST]
Change Package : 336934:1 http://mks-psad:7002/im/viewissue?selection=336934
Revision 1.2 2015/05/19 18:02:37CEST Hospes, Gerd-Joachim (uidv8815)
update get_file_revisions to list files not available in sandbox
--- Added comments ---  uidv8815 [May 19, 2015 6:02:38 PM CEST]
Change Package : 338048:1 http://mks-psad:7002/im/viewissue?selection=338048
Revision 1.1 2015/04/23 19:04:34CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/mks/project.pj
Revision 1.15 2015/03/27 16:03:39CET Hospes, Gerd-Joachim (uidv8815)
epydoc, pylint fixes
--- Added comments ---  uidv8815 [Mar 27, 2015 4:03:39 PM CET]
Change Package : 317821:1 http://mks-psad:7002/im/viewissue?selection=317821
Revision 1.14 2015/03/27 15:12:57CET Hospes, Gerd-Joachim (uidv8815)
add get_file_revision, get_checkpoint and get_checkpoint_label
--- Added comments ---  uidv8815 [Mar 27, 2015 3:12:57 PM CET]
Change Package : 317821:1 http://mks-psad:7002/im/viewissue?selection=317821
Revision 1.13 2015/03/13 15:23:21CET Hospes, Gerd-Joachim (uidv8815)
style fixes
--- Added comments ---  uidv8815 [Mar 13, 2015 3:23:22 PM CET]
Change Package : 311672:1 http://mks-psad:7002/im/viewissue?selection=311672
Revision 1.12 2014/05/26 14:24:06CEST Hecker, Robert (heckerr)
Added feature to create build sandboxes.
--- Added comments ---  heckerr [May 26, 2014 2:24:07 PM CEST]
Change Package : 239363:1 http://mks-psad:7002/im/viewissue?selection=239363
Revision 1.11 2014/03/16 21:55:52CET Hecker, Robert (heckerr)
added pylintrc.
--- Added comments ---  heckerr [Mar 16, 2014 9:55:53 PM CET]
Change Package : 225494:1 http://mks-psad:7002/im/viewissue?selection=225494
Revision 1.10 2014/02/24 16:18:27CET Hospes, Gerd-Joachim (uidv8815)
deprecated classes/methods/functions removed (planned for 2.0.9)
--- Added comments ---  uidv8815 [Feb 24, 2014 4:18:28 PM CET]
Change Package : 219922:1 http://mks-psad:7002/im/viewissue?selection=219922
Revision 1.9 2013/07/04 17:42:21CEST Hecker, Robert (heckerr)
Removed some pep8 violations.
--- Added comments ---  heckerr [Jul 4, 2013 5:42:21 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.8 2013/06/12 11:48:20CEST Hecker, Robert (heckerr)
Set Default value of Argument to False, because MKS forbid the usage of this feature.
--- Added comments ---  heckerr [Jun 12, 2013 11:48:20 AM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.7 2013/05/07 08:53:55CEST Hecker, Robert (heckerr)
Added resync command.
--- Added comments ---  heckerr [May 7, 2013 8:53:56 AM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.6 2013/04/29 10:39:55CEST Hecker, Robert (heckerr)
Added a easy to use mks si class, with two different Use case examples how to use.
--- Added comments ---  heckerr [Apr 29, 2013 10:39:56 AM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.5 2013/04/03 08:02:18CEST Mertens, Sven (uidv7805)
pylint: minor error, warnings fix
--- Added comments ---  uidv7805 [Apr 3, 2013 8:02:19 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.4 2013/04/02 10:25:03CEST Mertens, Sven (uidv7805)
pylint: E0213, E1123, E9900, E9904, E1003, E9905, E1103
--- Added comments ---  uidv7805 [Apr 2, 2013 10:25:04 AM CEST]
Change Package : 176171:9 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.3 2013/03/27 13:51:23CET Mertens, Sven (uidv7805)
pylint: bugfixing and error reduction
Revision 1.2 2013/03/22 08:24:29CET Mertens, Sven (uidv7805)
aligning bulk of files again for peping 8
Revision 1.1 2013/03/15 11:43:06CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
    stk/mks/project.pj
------------------------------------------------------------------------------
-- From STK stk_mks_si Archive
------------------------------------------------------------------------------
Revision 1.10 2012/08/31 08:15:53CEST Mogos, Sorin(mogoss)
* improved error handling while connecting to server
--- Added comments ---  mogoss [Aug 31, 2012 8:15:57 AM CEST]
Change Package : 155168:1 http://mks-psad:7002/im/viewissue?selection=155168
Revision 1.9 2012/08/30 11:39:54CEST Mogos, Sorin(mogoss)
* improved error handling
Revision 1.8 2012/05/24 12:29:08CEST Spruck, Jochen(spruckj)
First try to parse the project
--- Added comments ---  spruckj [May 24, 2012 12:29:08 PM CEST]
Change Package : 98074:3 http://mks-psad:7002/im/viewissue?selection=98074
Revision 1.7 2012/05/21 11:27:54CEST Mogos, Sorin(mogoss)
* code improvements
--- Added comments ---  mogoss [May 21, 2012 11:27:54 AM CEST]
Change Package : 104217:1 http://mks-psad:7002/im/viewissue?selection=104217
Revision 1.3 2012/03/12 12:09:18CET Mogos, Sorin(mogoss)
* added stk_logger
* changes for MKS Integrity 2009 SP6 compatibility
--- Added comments ---  mogoss [Mar 12, 2012 12:09:19 PM CET]
Change Package : 96336:1 http://mks-psad:7002/im/viewissue?selection=96336
Revision 1.2 2012/03/11 19:57:06CET Spruck, Jochen(spruckj)
- Update skt_mks_si use parameter to the si exe
- Checkout also shared-variant-subproject and shared-subprojects
--- Added comments ---  spruckj [Mar 11, 2012 7:57:06 PM CET]
Change Package : 98074:2 http://mks-psad:7002/im/viewissue?selection=98074
Revision 1.1 2011/08/30 11:59:58CEST Mogos, Sorin(mogoss)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
    31_PyLib/project.pj
"""
