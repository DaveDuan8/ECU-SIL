"""
framework/valf/valf.py
----------------

Class to provide methods to start a validation.

**User-API Interfaces**

  - `framework.valf` (complete package)
  - `Valf` (this module)
  - `GetSwVersion` (this module)


:org:           Continental AG
:author:        Joachim Hospes

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 10:14:12CEST $
"""
# =====================================================================================================================
# system Imports
# =====================================================================================================================
import sys
from inspect import currentframe
from logging import INFO
from os import path as opath, makedirs, listdir, remove, getenv
from shutil import rmtree
from time import strftime, localtime, time, gmtime

# =====================================================================================================================
# framework Imports
# =====================================================================================================================
from framework.util.error import ValfError
from framework.util.logger import Logger, LEVEL_CALL_MAP
from framework.util.helper import list_folders, arg_trans
from framework.util.tds import UncRepl
from framework.util.defines import OUTPUTDIRPATH_PORT_NAME, CFG_FILE_PORT_NAME, PLAY_LIST_FILE_PORT_NAME, \
    COLLECTION_NAME_PORT_NAME, SIM_PATH_PORT_NAME, SWVERSION_PORT_NAME, \
    SAVE_RESULT_IN_DB
from framework.valf.process_manager import ProcessManager

# =====================================================================================================================
# constant declarations
# =====================================================================================================================
DATA_BUS_NAMES = "DataBusNames"
HEAD_DIR = opath.abspath(opath.join(opath.dirname(__file__), "..\\.."))

# Error codes.
RET_VAL_OK = 0
RET_GEN_ERROR = -1
RET_SYS_EXIT = -2
RET_CFG_ERROR = -3


# =====================================================================================================================
# classes
# =====================================================================================================================
class Valf(object):
    """
    class defining methods to easily start validation suites
    by calling a python script without additional option settings (double click in win)

    mandatory settings:

    - outputpath (as instantiation parameter)
    - config file with `LoadConfig`
    - sw version of sw under test with `SetSwVersion`

    see `__init__` for additional options

    returns error level::

      RET_VAL_OK = 0       suite returned without error
      RET_GEN_ERROR = -1   general error
      RET_SYS_EXIT = -2    sys.exit called
      RET_CFG_ERROR = -3   error in direct settings or configuration file

    **Example:**

    .. code-block:: python

        # Import valf module
        from framework.valf import valf

        # set output path for logging ect., logging level and directory of plugins (if not subdir of current HEADDIR):
        vsuite = valf.Valf(getenv('HPCTaskDataFolder'), 10)  # logging level DEBUG, default level: INFO

        # mandatory: set config file and version of sw under test

        # additional defines not already set in config files or to be overwritten:
        vsuite.SetBplFile(r'cfg\\bpl.ini')
        vsuite.SetSimPath(r'\\\\Lifs010.cw01.contiwan.com\\data\\MFC310\\SOD_Development')

        # start validation:
        vsuite.Run()

    :author:        Joachim Hospes
    :date:          29.05.2013

    """
    def __init__(self, outpath, *args, **kwargs):
        """
        initialise all needed variables and settings

          - creates/cleans output folder
          - start process manager
          - start logging of all events, therefore the output path must be given

        :param outpath: path to output directory, can be relative to calling script
        :type outpath: str

        :param args: additional argument list which are also covered by keywords in order of occurrence

        :keyword logging_level: level of details to be displayed. default: info
                                (10=debug, 20=info, 30=warning, 40=error, 50=critical, 60=exception)
        :type logging_level: int [10|20|30|40|50]

        :keyword plugin_search_path: default: parent dir of stk folder, normally parallel to validation scripts
        :type plugin_search_path: str

        :keyword clean_folder:  default ``True``, set to ``False`` if the files in output folder should not be deleted
                                during instantiation of Valf
        :type clean_folder: bool

        :keyword logger_name:   name of logger is used for logfile name and printed in log file as base name,
                                if not set name/filename of calling function/module is used
        :type logger_name: str

        :keyword fail_on_error: Switch to control exception behaviour, if set
                                exceptions will be re-thrown rather than omitted or logged.
        :type fail_on_error: bool

        :keyword deprecations: set me to False to remove any deprecation warning outputs inside log
        :type deprecations: bool
        """
        self.__version = "$Revision: 1.2 $"
        self._uncrepl = UncRepl()

        self.__data_bus_names = []  # store all names of generated data busses like bus#0
        self.__process_mgr = None

        opts = arg_trans([['logging_level', INFO], ['plugin_search_path', None], ['clean_folder', True],
                          ['logger_name', None], ['fail_on_error', False], ['deprecations', True]], *args, **kwargs)

        self._fail_on_error = opts['fail_on_error']

        # prep output directory: create or clear content
        outpath = self._uncrepl(opath.abspath(outpath))
        clear_folder(outpath, opts['clean_folder'])

        logger_name = opts['logger_name']
        if logger_name is None:
            # get name of calling module
            frm = currentframe().f_back  # : disable=W0212
            if frm.f_code.co_filename:
                logger_name = opath.splitext(opath.basename(frm.f_code.co_filename))[0]
            else:
                logger_name = 'Valf'
        # start logger, first with default level, idea for extension: can be changed later
        self.__logger = Logger(logger_name, opts['logging_level'], filename=opath.join(outpath, logger_name + ".log"))
        self.__logger.info("Validation started at %s." % strftime('%H:%M:%S', localtime(time())))
        # self.__logger.info("Validation based on %s STK %s-%s of %s, CP: %s."
        #                    % ("original" if stk_checksum(True) else "adapted", RELEASE, INTVERS, RELDATE, MKS_CP))
        self.__logger.info("Logging level is set to %s."
                           % next(i for i, k in LEVEL_CALL_MAP.items() if k == opts['logging_level']))
        self.__logger.info("Validation arguments have been:")
        for k, v in opts.items():
            self.__logger.info("    %s: %s" % (k, str(v)))

        # find all observers down current path
        plugin_search_path = opts['plugin_search_path']
        plugin_folder_list = []
        if plugin_search_path is None:
            plugin_search_path = [HEAD_DIR]
        # take care of fast connections
        plugin_search_path = [self._uncrepl(i) for i in plugin_search_path]
        for spath in plugin_search_path:
            plugin_folder_list.extend([dirPath for dirPath in list_folders(spath) if "\\framework\\" not in dirPath])
            # left over from testing??? found in vers.1.14, introduced in 1.6
            # else:
            #     print folder_path

            self.__logger.info('added to plugin search path:' + spath)
        # and add all observers down calling script's path
        framework_plugins = [opath.join(HEAD_DIR, "framework", "valf"), opath.join(HEAD_DIR, "framework", "valf", "obs"),
                       opath.join(HEAD_DIR, "framework", "val")]

        plugin_folder_list.extend(plugin_search_path)

        for spath in framework_plugins:
            plugin_folder_list.append(spath)
            self.__logger.info('added to plugin search path:' + spath)

        # start process manager
        # noinspection PyBroadException
        try:
            self.__process_mgr = ProcessManager(plugin_folder_list, self._fail_on_error)
        except:  # pylint: disable=W0702
            self.__logger.exception("Couldn't instantiate 'ProcessManager' class.")
            if self._fail_on_error:
                raise
            sys.exit(RET_GEN_ERROR)

        self.__process_mgr.set_data_port(OUTPUTDIRPATH_PORT_NAME, outpath)
        self.__logger.info("OutputDirPath: '%s'" % outpath)

        # set still needed default settings as have been in valf.main
        # self.SetMasterDbPrefix(DEFAULT_MASTER_SCHEMA_PREFIX)
        # self.SetErrorTolerance(ERROR_TOLERANCE_NONE)

        # should be activated some day, for now not all validation suites can be parallelised
        # if set on default we should invent a method DeactivateHpcAutoSplit to run the remaining or old suites
        # self.SetDataPort("HpcAutoSplit", True, "Global")

    def _check_mandatory_settings(self):
        """ private method

        check if additional mandatory settings are done

        does not run complete sanity check for config, here we just check additional mandatory settings
        that do not prevent the validation to run if they are missing
        e.g. no test if db connection is defined for cat reader, if not set cat reader will stop the initialisation

        :return:   number of missing settings, 0 if settings completed
        :rtype:    integer
        """
        error_cnt = 0

        if self.get_data_port("SWVersion", "Global") is None:
            self.__logger.error("version of test sw not defined!")
            error_cnt += 1

        if self.get_data_port("HpcAutoSplit", "Global") is True and \
           self.get_data_port("SimSelection", "Global") is not None:
            self.__logger.error("DataPort 'SimSelection' used by HPC, not available if 'HpcAutoSplit' is active!")
            self.__logger.error("Set either 'HpcAutoSplit' to False or don't set 'SimSelection'!")
            error_cnt += 1

        return error_cnt

    def load_config(self, filepath):  # pylint: disable=C0103
        r"""
        load configuration from path/filename, path can be relative to calling script

        Valid configuration properties are:

            - version: string defining version of config file, added to dict on port "ConfigFileVersions"
            - ClassName: quoted string to determine observer class to include in run (not in section "Global")
            - PortOut: list of port values (quoted strings) which should be exported to given bus name
            - InputData: pythonic list of tuples/lists which are taken and given as input for observer to be configured
            - ConnectBus: list of bus names to connect / register observer to (first one is taken actually)
            - Active: True/False value weather observer should be enabled or not
            - include: file (quoted) to include herein, chapter should be repeated there,
              if include is used within global scope, all chapters from included file are used

        config file example::

            # valf_basic.cfg
            # config for testing Valf class, based on valf_demo settings,

            [Global]
            ; version string will be added to dict on port "ConfigFileVersions":
            version="$Revision: 1.2 $"
            ;PortOut: Informs the name of the port that are set by the component
            PortOut=["ProjectName", "SWVersion", "FunctionName", "Device_Prefix"]
            ;InputData: Declares all input parameters
            InputData=[('ProjectName', 'VALF-test'),
                       ('FunctionName', 'framework_moduletest'),
                       ('SimName', 'N/A'),
                       ('Multiprocess', True ),
                       ('ValName', 'N/A')]
            ;ConnectBus: Specifies the bus connect to the component
            ConnectBus=["Global"]

            ; db connection is needed for the catalog reader only, **deactivated** here!!
            ; connection parameters passed to validation_main.py as options because it will differ for projects
            [DBConnector]
            ClassName="DBConnector"
            InputData=[("UseAllConnections", "True")]
            PortOut=[ "DataBaseObjects"]
            ConnectBus=["DBBus#1"]
            Active=False
            ;Order: Specifies the calling order
            Order=0

            ; bpl reader can be used to read simulation results, but in future the cat_reader should be used
            ;  to test the difference switch Activate setting for BPLReader and CATReader
            [VALF_BPL_test]
            ClassName="BPLReader"
            PortOut=["CurrentMeasFile", "CurrentSimFile"]
            InputData=[("SimFileExt", "bin")]
            ConnectBus=["bus#1"]
            ; read additional config file data for this section, can overwrite complete setting before
            ; so e.g. InputData needs to list all input values,
            ; the values from include-cfg are not added but replace former set!
            Include="..\..\..\04_Test_Data\01a_Input\valf\valf_include_VALF_BPL_test.cfg"
            Active=True
            ;Order: Specifies the calling order
            Order=1

            ; cat reader needs db connector to setup connection to catalog db!
            [VALF_CAT_REF]
            ClassName="CATReader"
            PortOut=[ "CurrentMeasFile", "CurrentSimFile"]
            InputData=[("SimFileExt", "bsig"),("SimFileBaseName", "") ]
            ConnectBus=["Bus#1"]
            Active=False
            Order=1

        general used ports on bus ``Global`` (set by `ProjectManager`):

            - set ``ConfigFileVersions``: dict with file name as key and version as value for each loaded config file
            - read ``FileCount``:   to show progress bar
            - read ``IsFinished``:  to continue with next state when all sections of a recording
                                    are validated (set by `SignalExtractor`)

        Also setting ports as defined in ``InputData``  for the named bus.


        **usage (example)**

        .. code-block:: python

          from framework.valf import Valf

          vrun = framework.valf.Valf()
          vrun.load_config(r'conf/validation.cfg')

        :param filepath: path and filename of the config file to load
        :type filepath:  string
        """
        absfile = self._uncrepl(opath.abspath(filepath))
        # preset of port ConfigFileName currently not supported!!! what was it used for??
        # config_filename = self.__process_mgr.get_data_port(CFG_FILE_PORT_NAME)
        # if config_filename is None:
        #     config_filename = absfile
        # else:
        #     config_filename += ', ' + absfile
        self.__process_mgr.set_data_port(CFG_FILE_PORT_NAME, absfile)
        if self.__logger is not None:
            self.__logger.info("Using configuration file: '%s'" % absfile)
            # noinspection PyBroadException
            try:
                if not self.__process_mgr.load_configuration(absfile):
                    sys.exit(RET_CFG_ERROR)
            except ValfError:
                msg = 'Validation error during configuration load'
                if self.__process_mgr.last_config is not None:
                    msg += (" (%s)" % self.__process_mgr.last_config)
                self.__logger.exception(msg)
                if self._fail_on_error:
                    raise
                sys.exit(RET_SYS_EXIT)
            except SystemExit:
                msg = 'system exit by one module during configuration load'
                if self.__process_mgr.last_config is not None:
                    msg += (" (%s)" % self.__process_mgr.last_config)
                    self.__logger.exception(msg)
                self.__logger.error(msg)
                if self._fail_on_error:
                    raise
                sys.exit(RET_SYS_EXIT)
            except:
                msg = "unexpected error (%s) during configuration load" % str(sys.exc_info)
                if self.__process_mgr.last_config is not None:
                    msg += (" (%s)" % self.__process_mgr.last_config)
                    self.__logger.exception(msg)
                self.__logger.exception(msg)
                if self._fail_on_error:
                    raise
                sys.exit(RET_GEN_ERROR)

    def set_bpl_file(self, filepath):  # pylint: disable=C0103
        """
        set data port ``BplFilePath`` to path/filename of bpl file (.ini or .bpl)

        path can be relative to starting script, checks existence of file and stops in case of errors

        :param filepath: path/filename of batch play list
        :type filepath:  string
        """
        absfilepath = self._uncrepl(opath.abspath(filepath))
        self.__logger.info("BplFilePath: '%s'" % absfilepath)
        if filepath is not None and opath.isfile(absfilepath):
            self.__process_mgr.set_data_port(PLAY_LIST_FILE_PORT_NAME, absfilepath)
        else:
            self.__logger.error("Missing mts batch play list: can not open bpl file '%s'" % absfilepath)
            sys.exit(RET_CFG_ERROR)

    def set_collection_name(self, collection_name):  # pylint: disable=C0103
        """
        set data port ``RecCatCollectionName`` giving the collection name of rec files in catalog db
        used by the cat reader to select the recording list for a project

        :param collection_name: name of the collection
        :type collection_name:  string
        """
        self.__process_mgr.set_data_port(COLLECTION_NAME_PORT_NAME, collection_name)
        self.__logger.debug("Rec file cataloge collection name is: '%s'" % collection_name)

    def set_data_port(self, port_name, value, bus_name='Global'):  # pylint: disable=C0103
        """
        set named valf data port at named bus with given value,
        can be repeated for different ports and bus names

        in general these ports should be set using the config file ``InputData`` entry!

        :param port_name: valf data port name, not case sensitiv
        :type port_name:  string
        :param value:     port value, type depends on port usage
        :type value:      user defined
        :param bus_name:  valf data bus name, default: ``Global``, not case sensitiv
        :type bus_name:   string
        """
        self.__process_mgr.set_data_port(port_name, value, bus_name)
        self.__logger.info('valf script setting port "%s" :' % port_name + str(value))

    def set_sim_path(self, pathname, bus_name="Bus#1"):  # pylint: disable=C0103
        """
        set data port ``SimOutputPath`` at named bus (default:``Bus#0``) to given path
        where measurement files are stored

        checks if path exists and raises an `ValfError` if not

        for historical reasons the bus_name is set as default to ``bus#0``
        make sure your config sets the similar busses for bpl/cat reader(s)!

        :param pathname: absolute path where simulation result files are stored
        :type pathname:  string
        :param bus_name: data bus name of the bpl/cat reader, default ``bus#0``, not case sensitiv
        :type bus_name:  string
        """
        pathname = self._uncrepl(pathname)
        if opath.exists(pathname):
            self.__process_mgr.set_data_port(SIM_PATH_PORT_NAME, pathname, bus_name)
            self.__logger.info("Setting input data. [ Bus='{0}', "
                               "PortName='SimOutputPath', PortValue={1}]".format(bus_name, pathname))
            if bus_name not in self.__data_bus_names:
                self.__data_bus_names.append(bus_name)
                self.__process_mgr.set_data_port(DATA_BUS_NAMES, self.__data_bus_names)
        else:
            exception_msg = "Sim Output folder providing bsig/csv files does not exist:\n" +\
                            "{}\nPlease check your setup".format(pathname)
            self.__logger.exception(exception_msg)
            raise ValfError(exception_msg)

    def set_sw_version(self, version):  # pylint: disable=C0103
        """
        set data port ``SWVersion`` to given value

        currently mandatory setting!!

        :param version: sw version of sw under test
        :type version:  string
        """
        self.__process_mgr.set_data_port(SWVERSION_PORT_NAME, version)

    def set_save_results(self, saveit=True):  # pylint: disable=C0103
        """
        set data port ``SaveResultInDB`` to given value (optional)

        :param saveit: Save the results into the database, default = True
        :type saveit:  boolean
        """
        self.__process_mgr.set_data_port(SAVE_RESULT_IN_DB, saveit)

    def get_data_port(self, port_name, bus_name='Global'):  # pylint: disable=C0103
        """
        get named valf data port at named bus,
        can be repeated for different ports and bus names

        :param port_name: valf data port name, not case sensitiv
        :type port_name:  string

        :param bus_name: valf data bus name, default: ``Global``, not case sensitiv
        :type bus_name:  string

        :return: port data
        :rtype:  undefined
        """
        return self.__process_mgr.get_data_port(port_name, bus_name)

    def run(self):
        """ start the validation after all needed preparations

        :return:  success or error value during validation run
        :rtype:   error codes:
          RET_VAL_OK = 0
          RET_GEN_ERROR = -1
          RET_SYS_EXIT = -2
          RET_CFG_ERROR = -3
        """

        if self._check_mandatory_settings() is not 0:
            self.__logger.error("error in setup: mandatory settings missing")
            sys.exit(RET_CFG_ERROR)
        tstart = time()
        # noinspection PyBroadException
        try:
            ret_val = self.__process_mgr.run()
        except Exception:
            self.__logger.exception("unexpected runtime error")
            if self._fail_on_error:
                raise
            sys.exit(RET_GEN_ERROR)

        if ret_val is not RET_VAL_OK:
            self.__logger.error("runtime error in validation suite, error level %d" % ret_val)

        self.__logger.info("Test duration(hh:mm:ss): " + strftime('%H:%M:%S', gmtime(time() - tstart)))

        self.__logger.info("Logging statistics: " +
                           ", ".join(["%s: %d" % (k, v) for k, v in self.__logger.get_statistics().items() if v > 0]))

        print('val run ended with result', ret_val)
        return ret_val


# =====================================================================================================================
# functions
# =====================================================================================================================
def clear_folder(pathname, purge=True):
    """
    empty given folder completely or create a new one

    :param pathname: folder to empty or create
    :type pathname:  string

    :param purge:    default ``True``, set to ``False`` if the given path should not be cleared
    :type purge:     boolean
    """
    if not opath.exists(pathname):
        try:
            makedirs(pathname)
        except sys:  # pylint: disable=W0702
            sys.stderr.write("Error while creating folder: '%s'." % pathname)
            sys.exit(RET_GEN_ERROR)
    elif purge is True:
        try:
            pathname = opath.abspath(pathname)
            for entry in listdir(pathname):
                file_path = opath.join(pathname, entry)
                if opath.isdir(file_path):
                    rmtree(file_path)
                elif opath.isfile(file_path):
                    remove(file_path)
        except sys:  # pylint: disable=W0702
            sys.stderr.write("valf: Error while removing folder: '%s'." % pathname)
            sys.exit(RET_GEN_ERROR)


def sw_version():
    r"""
    get some string as sw version either by

      - checking call arguments of main script for one parameter and take that
      - requesting direct user input if not running on `HPC`

    and raising exit(-3) if called on `HPC` without parameter

    :return: test-sw version
    :rtype:  string

    **usage examples**

    in your start script:

    .. code-block:: python

        vsuite = framework.valf.Valf(my_out_path, my_log_level, [my_plugin_path1, ...])
        vsuite.SetSwVersion(framework.valf.sw_version())

    a) call argument

        run your start script like::

            d:\tests\start_vali.py AL_FUNCT_03.05.01-INT2

    a) direct input (only on workstation, not for HPC submits)

        run your start script like::

          d:\tests\start_vali.py

        and get the input request::

          enter test sw version (checkpoint):

    """
    test_sw_version = None
    if len(sys.argv) > 2:
        sys.exit("ERROR in calling main program, only one argument accepted: test sw version")
    elif len(sys.argv) == 2:
        test_sw_version = sys.argv[1]
    elif getenv("TaskName") is None and getenv('JobName') is None:
        while test_sw_version is None or len(test_sw_version) < 1:
            test_sw_version = raw_input("enter test sw version (checkpoint):")
    else:
        sys.stderr.write("ERROR: running on HPC but no algo sw version provided as call parameter\n")
        sys.stderr.write("set SW version on data port ")
        sys.exit(RET_CFG_ERROR)
    return test_sw_version


"""
CHANGE LOG: 
-----------
$Log: valf.py  $
Revision 1.2 2020/03/31 10:14:12CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:38:09CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/valf/project.pj
"""
