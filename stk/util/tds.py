"""
stk/util/tds.py
---------------

Test Data Server (LIFS010) utilities checking and updating server and pathnames
e.g. if running on HPC.

Features:
  - checking if running on HPC client
  - checking if the server is available
  - changing server name in list of strings

On HPC there is a fast connection server in parallel to the test data server LIFS010,
if the script runs on HPC the fast one should be used
to prevent that HPC clients wait for file transfer.

The provided functions can be used to update e.g. pathnames, server names etc.

As the check for the TDS can take some time the result should be stored and reused!

**example:**

.. python::
        if tds.run_on_hpc():
            self.__hpc_run = True
            self.__logger.info("running on HPC, will change LIFS010 to LIFS010s for rec file paths")
        ...
        rec_file_list = ['\\\\LIFs010\\data\\MFC310\\_HPC\\_MeasFiles\\Continuous_2012.06.06_at_14.23.23.rec',
                         '\\\\LIFs010\\data\\MFC310\\_HPC\\_MeasFiles\\Continuous_2012.06.06_at_14.23.24.rec']

        meas_file_list = tds.replace_lifs(rec_file_list, self.__hpc_run)

:org:           Continental AG
:author:        Joachim Hospes

:version:       $Revision: 1.2 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/11/13 17:09:34CET $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
import os
from subprocess import Popen, PIPE
from re import compile as recomp, escape, IGNORECASE, match, sub as resub
from time import sleep
try:
    from wmi import WMI
except ImportError:
    WMI = None

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.util.helper import singleton

# - defines -----------------------------------------------------------------------------------------------------------
REPLACEMENTS = (('\\\\LIFS010.', '\\\\LIFS010S.'),  # Lindau(1)
                ('\\\\LIFS010\\', '\\\\LIFS010S\\'),
                # currently no replacement for LUFS003X  Lindau(2)
                ('\\\\OZFS110.', '\\\\OZFS110H.'),  # Bangalore
                ('\\\\OZFS110\\', '\\\\OZFS110H\\'),
                ('\\\\QHFS004X.', '\\\\QHSIMU.'),   # Auburn Hills
                ('\\\\QHFS004X\\', '\\\\QHSIMU\\'))


# - functions ---------------------------------------------------------------------------------------------------------
def check_server_available(name='LIFS010s'):
    """
    **Check if a server is available**

    Usage mainly to check if we are on a Fast Network (e.g. on HPC),
    then we should be able to access server LIFS010S for fast file transfer.

    :param name: name of host to check (ping)

    **Coution:** this function gets really slow (~4 sec) if the server is not available,
    so use it only where it is really needed!

    :rtype:  boolean
    :return: True if \\LIFS010S is found

    :author:           Robert Hecker
    """

    # change with extreme caution!!
    # this function is used by HPC app_watcher and therefore an error will stop the complete cloud!

    # try to connect the server:
    proc = Popen([r"ping.exe", "-n", "1", name], stdout=PIPE)

    # wait until subprocess is finished.
    while proc and proc.poll() is None:
        sleep(1)

    return proc.returncode == 0


def run_on_hpc():
    """
    **Return if the task is executed on HPC client.**

    It checks for environment variable CCP_SCHEDULER which is only available on HPC clients
    giving the name of the HPC head node.

    Additionally it tests if the connection to the fast  file server LIFSxxxS is available.
    So this method provides a fast and reliable way to prove that the task is running on an HPC client
    with all needed connections available to process the job.
    """
    hpc_available = os.getenv("CCM_SCHEDULER")
    if hpc_available is not None and check_server_available() is True:
        return True
    return False


def replace_lifs(arglist, on_hpc):
    """
    replace all server name entries like \\LIFS010 entries
    with the fast connection server name like \\LIFS010s when running on HPC.

    update server names as defined in `REPLACEMENTS` if on_hpc is True

    :param arglist: input argument list for HPC.
    :type arglist:  list[string]
    :param on_hpc: running on hpc -> yes/no
    :type on_hpc:  bool

    :return: modified argument list.
    :rtype:  list[string]
    """

    # change with extreme caution!!
    # this function is used by HPC app_watcher and therefore an error will stop the complete cloud!

    arglist2 = []
    # Replace \\LIFS010 with LIFS010S if we run on HPC
    if on_hpc:
        for item in arglist:
            for repl in REPLACEMENTS:
                regexp = recomp(escape(repl[0]), IGNORECASE)
                item = regexp.sub(repl[1].replace('\\', '\\\\'), item)
            arglist2.append(item)
    else:
        arglist2 = arglist

    return arglist2


# - classes -----------------------------------------------------------------------------------------------------------
@singleton
class UncRepl(object):
    """UncRepl: uniform name convention replacer to check and use fast connection if available.
    This class checks for fast server connection of given unc path.
    Server part of unc is extracted, e.g. 'lifs010' from '\\\\lifs010\\prj' and a fast server with
    's' extention ('lifs010s') is checked for availability (once) and adjusted path is returned.

        **Example:**
        self._lifs = UncRepl()
        # my_path = '\\\\LiFs010\\prj\\smfc4b0\\...'
        my_path = self._lifs(my_path)
        # when 's' available, my_path contains now: '\\\\LiFs010s\\prj\\smfc4b0\\...'
    """
    def __init__(self):
        """set up the essential"""
        if WMI is not None:
            self._wmi = WMI("localhost", namespace="root\\cimv2")
        self._repl = {}
        self._pat = r'(?i)^(\\+)([a-zA-Z0-9_-]+(?<!s))((\.|\\).*)'

    def __call__(self, path):
        """keep it simple, see class doc for details

        :param path: //unc/path/to/any/file
        :type path: str | unicode
        :return: replace path
        :rtype: str | unicode
        """
        return self.repl(path)

    def repl(self, path):
        """see class doc for details

        :param path: //unc/path/to/any/file
        :type path: str | unicode
        :return: replace path
        :rtype: str | unicode
        """
        if path is not None:
            mtc = match(self._pat, path)
            if mtc:
                if self._repl.get(mtc.group(2), None) is None:
                    if WMI is None:  # what if we don't have WMI installed?
                        proc = Popen([r"ping.exe", "-n", "1", mtc.group(2) + "s"], stdout=PIPE, shell=False)
                        proc.communicate()
                        self._repl[mtc.group(2)] = proc.returncode == 0
                    else:  # well, otherwise we're going faster if we have
                        for item in self._wmi.Win32_PingStatus(["StatusCode"], Address=mtc.group(2) + "s"):
                            self._repl[mtc.group(2)] = item.StatusCode == 0

                if self._repl[mtc.group(2)]:
                    return resub(self._pat, r'\1\2s\3', path)

        return path


"""
CHANGE LOG:
-----------
$Log: tds.py  $
Revision 1.2 2017/11/13 17:09:34CET Hospes, Gerd-Joachim (uidv8815) 
use location, update tests, add table gbl_location and cat_files column location to sqlite
Revision 1.1 2015/04/23 19:05:32CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/util/project.pj
Revision 1.10 2015/03/09 11:40:25CET Mertens, Sven (uidv7805)
coverage improvement
--- Added comments ---  uidv7805 [Mar 9, 2015 11:40:25 AM CET]
Change Package : 314290:1 http://mks-psad:7002/im/viewissue?selection=314290
Revision 1.9 2015/02/26 19:19:56CET Hospes, Gerd-Joachim (uidv8815)
ping now taking the correct server name
--- Added comments ---  uidv8815 [Feb 26, 2015 7:19:57 PM CET]
Change Package : 311345:1 http://mks-psad:7002/im/viewissue?selection=311345
Revision 1.8 2015/01/30 11:10:44CET Mertens, Sven (uidv7805)
path can be None sometimes...
--- Added comments ---  uidv7805 [Jan 30, 2015 11:10:45 AM CET]
Change Package : 288765:1 http://mks-psad:7002/im/viewissue?selection=288765
Revision 1.7 2015/01/22 10:34:56CET Mertens, Sven (uidv7805)
adding fallback for WMI
Revision 1.6 2015/01/20 16:30:09CET Mertens, Sven (uidv7805)
wmi should be on all machines now
Revision 1.5 2014/12/08 13:25:08CET Mertens, Sven (uidv7805)
update according related CR
Revision 1.4 2014/11/21 13:40:40CET Hospes, Gerd-Joachim (uidv8815)
remove ping, can only run by admin
--- Added comments ---  uidv8815 [Nov 21, 2014 1:40:41 PM CET]
Change Package : 279149:1 http://mks-psad:7002/im/viewissue?selection=279149
Revision 1.3 2014/11/11 14:27:19CET Mertens, Sven (uidv7805)
adding pure python ping
--- Added comments ---  uidv7805 [Nov 11, 2014 2:27:20 PM CET]
Change Package : 279543:1 http://mks-psad:7002/im/viewissue?selection=279543
Revision 1.2 2014/08/29 13:49:21CEST Hospes, Gerd-Joachim (uidv8815)
using new module stk.util.tds and its functions to change LIFS010 to fast server
--- Added comments ---  uidv8815 [Aug 29, 2014 1:49:22 PM CEST]
Change Package : 259660:1 http://mks-psad:7002/im/viewissue?selection=259660
Revision 1.1 2014/08/28 14:11:12CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/
    04_Engineering/stk/util/project.pj
"""
