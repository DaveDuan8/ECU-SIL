"""
framework/util/tds.py
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

.. code-block:: python

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
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 09:22:59CEST $
"""
# - import framework modules -------------------------------------------------------------------------------------------------

# - import Python modules ----------------------------------------------------------------------------------------------
from os import getenv
from subprocess import Popen, PIPE
from re import match, sub
from time import sleep
try:
    from wmi import WMI
except ImportError:
    WMI = None

# - import framework modules ------------------------------------------------------------------------------------------------
from framework.util.helper import singleton

# - defines -----------------------------------------------------------------------------------------------------------
REPLACEMENTS = ((r"(?i)(\\\\)(lifs010)(s?(\.cw01\.contiwan\.com)?)(\\.*)", r"\1\2s.cw01.contiwan.com\5"),
                (r"(?i)(\\\\)(lufs003x)(\.li\.de\.conti\.de)?(\\.*)", r"\1\2.li.de.conti.de\4"),
                (r"(?i)(\\\\)(mdm-adas-hub2-lu\.conti\.de)(\\.*)", r"\1lufs003x.li.de.conti.de\3"),
                (r"(?i)(\\\\)(qhfs004x)(\.qh\.us\.conti\.de)?(\\.*)", r"\1qhsimu.qh.us.conti.de\4"),
                (r"(?i)(\\\\)(mdm-adas-hub1-qh\.conti\.de)(\\.*)", r"\1qhsimu.qh.us.conti.de\3"),
                (r"(?i)(\\\\)(ozfs110)(h?(\.oz\.in\.conti\.de)?)(\\.*)", r"\1\2h.oz.in.conti.de\5"),
                (r"(?i)(\\\\)(mdm-adas-hub1-oz\.conti\.de)(\\.*)", r"\1ozfs110h.oz.in.conti.de\3"),)
REVPLACMENTS = ((r"(?i)(\\\\)(lifs010)s?((\.|\\).*)", r"\1\2\3"),
                (r"(?i)(\\\\)(qhsimu)((\.|\\).*)", r"\1qhfs004x\3"),
                (r"(?i)(\\\\)(ozfs110)h?((\.|\\).*)", r"\1\2\3"),)


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
    hpc_available = getenv("CCM_SCHEDULER")
    if hpc_available is not None and check_server_available() is True:
        return True
    return False


def replace_server_path(arg_list, reverse=False):
    """
    replace all server name entries like \\LIFS010 entries
    with the fast connection server name like \\LIFS010s when running on HPC.

    update server names as defined in `REPLACEMENTS` if on_hpc is True

    :param arg_list: input argument list for HPC.
    :type arg_list:  list[string] | str
    :param reverse: do a reverse replace
    :type reverse: bool

    :return: modified argument list.
    :rtype:  list[string]
    """
    if arg_list is None:
        return None

    def conv(x):
        return x

    if not hasattr(arg_list, "__iter__"):
        arg_list = [arg_list]

        def conv(x):
            return x[0]

    clst = arg_list[:]
    for i in range(len(clst)):
        for k in (REVPLACMENTS if reverse else REPLACEMENTS):
            clst[i] = sub(k[0], k[1], clst[i])

    return conv(clst)


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
                    return sub(self._pat, r'\1\2s\3', path)

        return path


"""
CHANGE LOG:
-----------
$Log: tds.py  $
Revision 1.2 2020/03/31 09:22:59CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:33:26CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/util/project.pj
"""
