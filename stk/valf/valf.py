"""
stk/valf/valf.py
----------------

Class to provide methods to start a validation.

**User-API Interfaces**

  - `stk.valf` (complete package)
  - `Valf` (this module)
  - `GetSwVersion` (this module)


:org:           Continental AG
:author:        Joachim Hospes

:version:       $Revision: 1.5 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/07/04 15:44:24CEST $
"""
# =====================================================================================================================
# system Imports
# =====================================================================================================================
import sys
from os import path as opath, makedirs, listdir, remove, getenv
from shutil import rmtree
from time import strftime, localtime, time, gmtime
from inspect import currentframe
from re import match
from distutils.version import LooseVersion
from logging import INFO
from sqlite3 import sqlite_version

# =====================================================================================================================
# STK Imports
# =====================================================================================================================
from stk.valf.error import ValfError
from stk.stk import MIN_SQLITE_VERSION, RELEASE, INTVERS, RELDATE, MKS_CP, stk_checksum
from stk.util.logger import Logger, LEVEL_CALL_MAP
from stk.util.helper import list_folders, DeprecationUsage, arg_trans
from stk.util.tds import UncRepl
from stk.db.db_common import DEFAULT_MASTER_SCHEMA_PREFIX, ERROR_TOLERANCE_NONE
from stk.valf.db_connector import DB_FILE_PORT_NAME, MASTER_DB_DBQ_PORT_NAME, MASTER_DB_DSN_PORT_NAME, \
    MASTER_DB_USR_PORT_NAME, MASTER_DB_PW_PORT_NAME, MASTER_DB_SPX_PORT_NAME
from stk.valf.signal_defs import OUTPUTDIRPATH_PORT_NAME, CFG_FILE_PORT_NAME, PLAY_LIST_FILE_PORT_NAME, \
    COLLECTION_NAME_PORT_NAME, ERROR_TOLERANCE_PORT_NAME, SIM_PATH_PORT_NAME, SWVERSION_PORT_NAME, \
    SWVERSION_REG_PORT_NAME, SAVE_RESULT_IN_DB, HPC_AUTO_SPLIT_PORT_NAME
from stk.valf.process_manager import ProcessManager
from stk.util.helper import deprecated

# =====================================================================================================================
# constant declarations
# =====================================================================================================================
DATA_BUS_NAMES = "DataBusNames"
HEAD_DIR = opath.abspath(opath.join(opath.dirname(__file__), "..\\.."))
# SMe: do we really need to add head to search path?
# if HEAD_DIR not in sys.path:
#     sys.path.append(HEAD_DIR)

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

    returns error level::

      RET_VAL_OK = 0       suite returned without error
      RET_GEN_ERROR = -1   general error
      RET_SYS_EXIT = -2    sys.exit called
      RET_CFG_ERROR = -3   error in direct settings or configuration file

    **Example:**

    .. python::

        # Import valf module
        from stk.valf import valf

        # set output path for logging ect., logging level and directory of plugins (if not subdir of current HEADDIR):
        vsuite = valf.Valf(getenv('HPCTaskDataFolder'), 10)  # logging level DEBUG, default level: INFO

        # mandatory: set config file and version of sw under test
        vsuite.LoadConfig(r'demo\\cfg\\bpl_demo.cfg')
        vsuite.SetSwVersion('AL_STK_V02.00.06')

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

        :param args: additional argument list which are also covered by keywords in order of occurence

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
        self.__version = "$Revision: 1.5 $"
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
        self.__logger.info("Validation based on %s STK %s-%s of %s, CP: %s."
                           % ("original" if stk_checksum(True) else "adapted", RELEASE, INTVERS, RELDATE, MKS_CP))
        self.__logger.info("Logging level is set to %s."
                           % next(i for i, k in LEVEL_CALL_MAP.items() if k == opts['logging_level']))
        self.__logger.info("Validation arguments have been:")
        for k, v in opts.iteritems():
            self.__logger.info("    %s: %s" % (k, str(v)))

        if not opts['deprecations']:
            self.__logger.warning("Deprecation warnings have been switched off!")
            DeprecationUsage().status = False

        # find all observers down current path
        plugin_search_path = opts['plugin_search_path']
        plugin_folder_list = []
        if plugin_search_path is None:
            plugin_search_path = [HEAD_DIR]
        # take care of fast connections
        plugin_search_path = [self._uncrepl(i) for i in plugin_search_path]
        for spath in plugin_search_path:
            plugin_folder_list.extend([dirPath for dirPath in list_folders(spath) if "\\stk\\" not in dirPath])
            # left over from testing??? found in vers.1.14, introduced in 1.6
            # else:
            #     print folder_path

            self.__logger.info('added to plugin search path:' + spath)
        # and add all observers down calling script's path
        stk_plugins = [opath.join(HEAD_DIR, "stk", "valf"), opath.join(HEAD_DIR, "stk", "valf", "obs"),
                       opath.join(HEAD_DIR, "stk", "val")]

        plugin_folder_list.extend(plugin_search_path)

        for spath in stk_plugins:
            plugin_folder_list.append(spath)
            self.__logger.debug('added to plugin search path:' + spath)

        # start process manager
        try:
            self.__process_mgr = ProcessManager(plugin_folder_list, self._fail_on_error)
        except:  # pylint: disable=W0702
            self.__logger.exception("Couldn't instantiate 'ProcessManager' class.")
            if self._fail_on_error:
                raise
            sys.exit(RET_GEN_ERROR)

        self.__process_mgr.set_data_port(OUTPUTDIRPATH_PORT_NAME, outpath)
        self.__logger.debug("OutputDirPath: '%s'" % outpath)

        # set still needed default settings as have been in valf.main
        self.SetMasterDbPrefix(DEFAULT_MASTER_SCHEMA_PREFIX)
        self.SetErrorTolerance(ERROR_TOLERANCE_NONE)

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

        if self.GetDataPort("SWVersion", "Global") is None:
            self.__logger.error("version of test sw not defined!")
            error_cnt += 1

        if (self.GetDataPort("HpcAutoSplit", "Global") is True
                and self.GetDataPort("SimSelection", "Global") is not None):
            self.__logger.error("DataPort 'SimSelection' used by HPC, not available if 'HpcAutoSplit' is active!")
            self.__logger.error("Set either 'HpcAutoSplit' to False or don't set 'SimSelection'!")
            error_cnt += 1

        return error_cnt

    def _set_hpc_selection(self):
        """ private method

        if the start script is running as HPC task on an HPC machine then
        set SimSelection to use only the entry given by the task number.

        e.g. for HPC task003: set SimSelection to [2]
        """
        # check HPC usage
        if self.GetDataPort("HpcAutoSplit", "Global") is True:
            task_name = getenv("TaskName")
            try:
                # T0000x task ids start with 1,  bpl list index with 0
                task_id = int(match(r'T(\d+)', str(task_name)).group(1)) - 1
            except AttributeError:
                self.__logger.exception("can't set Hpc Auto Split value as HPC environment variable Task Id"
                                        " is empty or not valid: %s" % task_name)
                if self._fail_on_error:
                    raise
                sys.exit(RET_CFG_ERROR)
            self.__logger.info("HpcAutoSplit: using entry %d of the sim collection" % task_id)
            self.SetDataPort("SimSelection", "[%d]" % task_id, "Global")

    def LoadConfig(self, filepath):  # pylint: disable=C0103
        """
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
            version="$Revision: 1.5 $"
            ;PortOut: Informs the name of the port that are set by the component
            PortOut=["ProjectName", "SWVersion", "FunctionName", "Device_Prefix"]
            ;InputData: Declares all input parameters
            InputData=[('ProjectName', 'VALF-test'),
                       ('FunctionName', 'STK_moduletest'),
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

            - set "ConfigFileVersions"
                dict with file name as key and version as value for each loaded config file
            - read "FileCount"
                to show progress bar
            - read "IsFinished"
                to continue with next state when all sections of a recording are validated (set by `SignalExtractor`)

        Also setting ports as defined in ``InputData``  for the named bus.


        usage (example):

        .. python::

          from stk.valf import Valf

          vrun = stk.valf.Valf()
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

    def SetBplFile(self, filepath):  # pylint: disable=C0103
        """
        set data port ``BplFilePath`` to path/filename of bpl file (.ini or .bpl)
        path can be relative to starting script, checks existence of file and stops in case of errors

        :param filepath: path/filename of batch play list
        :type filepath:  string
        """
        absfilepath = self._uncrepl(opath.abspath(filepath))
        self.__logger.debug("BplFilePath: '%s'" % absfilepath)
        if filepath is not None and opath.isfile(absfilepath):
            self.__process_mgr.set_data_port(PLAY_LIST_FILE_PORT_NAME, absfilepath)
        else:
            self.__logger.error("Missing mts batch play list: can not open bpl file '%s'" % absfilepath)
            sys.exit(RET_CFG_ERROR)

    def SetCollectionName(self, collection_name):  # pylint: disable=C0103
        """
        set data port ``RecCatCollectionName`` giving the collection name of rec files in catalog db
        used by the cat reader to select the recording list for a project

        :param collection_name: name of the collection
        :type collection_name:  string
        """
        self.__process_mgr.set_data_port(COLLECTION_NAME_PORT_NAME, collection_name)
        self.__logger.debug("Rec file cataloge collection name is: '%s'" % collection_name)

    def SetDataPort(self, port_name, value, bus_name='Global'):  # pylint: disable=C0103
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
        self.__logger.debug('valf script setting port "%s" :' % port_name + str(value))

    def SetDbFile(self, filepath):  # pylint: disable=C0103
        """
        set data port ``dbfile`` to define name of sqlite data base file to be used instead of oracle db
        checks existence of the file and raises an error if it's not readable

        :param filepath: path/name of the database file
        :type filepath:  string
        """
        database_filename = self._uncrepl(opath.abspath(filepath))
        if not opath.exists(database_filename):
            self.__logger.error("defined db file '%s' not found" % database_filename)
            sys.exit(RET_CFG_ERROR)
        self.__process_mgr.set_data_port(DB_FILE_PORT_NAME, database_filename, 'DBBus#1')

    def SetErrorTolerance(self, tolerance):  # pylint: disable=C0103
        """
        set data port ``ErrorTolerance`` to a value as defined in `db_commmon`

        :param tolerance: error tolerance value
        :type tolerance:  integer
        """
        self.__process_mgr.set_data_port(ERROR_TOLERANCE_PORT_NAME, tolerance, "Bus#1")

    @deprecated()
    def SetMasterDbDbq(self, dbq):  # pylint: disable=C0103
        """
        set data port "masterdbdbq" (name defined in `valf.db_connector`) to given name
        default value defined in db.db_common by DEFAULT_MASTER_DBQ

        :param dbq: data base qualifier for oracle data bases
        :type dbq:  string
        :note:      don't use together with DSN setting
        """
        self.__process_mgr.set_data_port(MASTER_DB_DBQ_PORT_NAME, dbq, "DBBus#1")

    @deprecated()
    def SetMasterDbDsn(self, dsn):  # pylint: disable=C0103
        """
        set data port ``masterdbdsn`` (name defined in `valf.db_connector`) to given name
        default value defined in db.db_common by DEFAULT_MASTER_DSN

        :param dsn: data source name for odbc interface connections
        :type dsn:  string
        :note:      don't use together with DBQ setting
        """
        self.__process_mgr.set_data_port(MASTER_DB_DSN_PORT_NAME, dsn, "DBBus#1")

    def SetMasterDbUser(self, user):  # pylint: disable=C0103
        """
        set data port ``masterdbuser`` (name defined in `valf.db_connector`) to given name

        :param user: name of data base user
        :type user:  string
        """
        self.__process_mgr.set_data_port(MASTER_DB_USR_PORT_NAME, user, "DBBus#1")

    def SetMasterDbPwd(self, passwd):  # pylint: disable=C0103
        """
        set data port ``masterdbpassword`` (name defined in `valf.db_connector`) to given name

        :param passwd: password for data base user
        :type passwd:  string
        """
        self.__process_mgr.set_data_port(MASTER_DB_PW_PORT_NAME, passwd, "DBBus#1")

    def SetMasterDbPrefix(self, prefix):  # pylint: disable=C0103
        """
        set data port ``masterdbschemaprefix`` (name defined in `valf.db_connector`) to given name

        :param prefix: schema prefix for data base table
        :type prefix:  string
        """
        self.__process_mgr.set_data_port(MASTER_DB_SPX_PORT_NAME, prefix, "DBBus#1")

    def SetSimPath(self, pathname, bus_name="Bus#1"):  # pylint: disable=C0103
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
            self.__logger.debug("Setting input data. [ Bus='{0}', "
                                "PortName='SimOutputPath', PortValue={1}]".format(bus_name, pathname))
            if bus_name not in self.__data_bus_names:
                self.__data_bus_names.append(bus_name)
                self.__process_mgr.set_data_port(DATA_BUS_NAMES, self.__data_bus_names)
        else:
            exception_msg = "Sim Output folder providing bsig/csv files does not exist:\n" +\
                            "{}\nPlease check your setup".format(pathname)
            self.__logger.exception(exception_msg)
            raise ValfError(exception_msg)

    def SetSwVersion(self, version):  # pylint: disable=C0103
        """
        set data port ``SWVersion`` to given value
        currently mandatory setting!!

        :param version: sw version of sw under test
        :type version:  string
        """
        self.__process_mgr.set_data_port(SWVERSION_PORT_NAME, version)

    def SetRefSwVersion(self, version):  # pylint: disable=C0103
        """
        set data port ``SWVersion_REG`` to given value (optional)

        :param version: sw version of regression sw under test
        :type version:  string
        """
        self.__process_mgr.set_data_port(SWVERSION_REG_PORT_NAME, version)

    def SetSaveResults(self, saveit=True):  # pylint: disable=C0103
        """
        set data port ``SaveResultInDB`` to given value (optional)

        :param saveit: Save the results into the database, default = True
        :type saveit:  boolean
        """
        self.__process_mgr.set_data_port(SAVE_RESULT_IN_DB, saveit)

    def GetDataPort(self, port_name, bus_name='Global'):  # pylint: disable=C0103
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

    def ActivateHpcAutoSplit(self):  # pylint: disable=C0103
        r"""
        activate auto splitting of bpl/cat list on HPC

        Running on HPC a validation can run in parallel on several tasks. This method sets data port ``HpcAutoSplit``
        to ``True`` so each validation suite running on one task/machine only reads the sim results of one recording::

              bpl / cat list       HPC TaskID
            ---------------------- ----------
            recording_entry_0.rec    T00001
            recording_entry_1.rec    T00002
            recording_entry_2.rec    T00003
            ...                      ...

        **The tasks must be created during job submit,** this is not done by Valf!!

        Example to create an own task for each bpl entry:

        .. python::

            # Create the Validation Tasks
            reclist = bpl.Bpl(BPL_FILE).read()
            task = hpc.TaskFactory(job)
            for rec in reclist:
                task.create_task(r"D:\data\%JobName%\1_Input\valf_tests\custom\demo\run_valf_demo_bpl.py")

        """
        self.SetDataPort(HPC_AUTO_SPLIT_PORT_NAME, True, 'global')

    def Run(self):
        """ start the validation after all needed preparations

        :return:  success or error value during validation run
        :rtype:   error codes:
          RET_VAL_OK = 0
          RET_GEN_ERROR = -1
          RET_SYS_EXIT = -2
          RET_CFG_ERROR = -3

        """
        if LooseVersion(sqlite_version) <= LooseVersion(MIN_SQLITE_VERSION):
            self.__logger.error("error in setup: please update your sqlite3.dll!\n"
                                "Just call batch script listed on Validation wiki -> needed tools.")
            sys.exit(RET_CFG_ERROR)

        if self._check_mandatory_settings() is not 0:
            self.__logger.error("error in setup: mandatory settings missing")
            sys.exit(RET_CFG_ERROR)
        tstart = time()
        self._set_hpc_selection()
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
        except:  # pylint: disable=W0702
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
        except:  # pylint: disable=W0702
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

    usage examples
    ==============
    in your start script:

    .. python::

        vsuite = stk.valf.Valf(my_out_path, my_log_level, [my_plugin_path1, ...])
        vsuite.SetSwVersion(stk.valf.sw_version())

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


# @deprecated('clear_folder')
def CreateClearFolder(pathname, purge=True):  # pylint: disable=C0103
    """deprecated"""
    clear_folder(pathname, purge)


# @deprecated('sw_version')
def GetSwVersion():  # pylint: disable=C0103
    """deprecated"""
    return sw_version()


"""
CHANGE LOG:
-----------
$Log: valf.py  $
Revision 1.5 2017/07/04 15:44:24CEST Hospes, Gerd-Joachim (uidv8815) 
rem SetMasterDbDsn and SetMasterDbDbq calls in Valf.__init__ and tests
Revision 1.4 2016/06/23 18:34:31CEST Hospes, Gerd-Joachim (uidv8815)
update docu, use full #Revision: 1.2 # string for version
Revision 1.3 2016/06/23 15:14:20CEST Mertens, Sven (uidv7805)
pylint fix
Revision 1.2 2016/06/23 14:42:33CEST Mertens, Sven (uidv7805)
be more verbose on config reading errors
Revision 1.1 2015/04/23 19:05:49CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/valf/project.pj
Revision 1.42 2015/04/20 18:10:26CEST Hospes, Gerd-Joachim (uidv8815)
add logging exception in SetSimPath
--- Added comments ---  uidv8815 [Apr 20, 2015 6:10:27 PM CEST]
Change Package : 328869:1 http://mks-psad:7002/im/viewissue?selection=328869
Revision 1.41 2015/04/16 10:21:09CEST Hospes, Gerd-Joachim (uidv8815)
raise runprocess error with complete traceback
Revision 1.40 2015/03/27 07:59:17CET Mertens, Sven (uidv7805)
remove port warnings option
--- Added comments ---  uidv7805 [Mar 27, 2015 7:59:18 AM CET]
Change Package : 317742:2 http://mks-psad:7002/im/viewissue?selection=317742
Revision 1.39 2015/03/24 11:32:54CET Mertens, Sven (uidv7805)
changing CP info to info level
--- Added comments ---  uidv7805 [Mar 24, 2015 11:32:54 AM CET]
Change Package : 318008:2 http://mks-psad:7002/im/viewissue?selection=318008
Revision 1.38 2015/03/19 13:21:28CET Mertens, Sven (uidv7805)
changing define import from logger
--- Added comments ---  uidv7805 [Mar 19, 2015 1:21:28 PM CET]
Change Package : 318794:1 http://mks-psad:7002/im/viewissue?selection=318794
Revision 1.37 2015/03/18 13:26:20CET Mertens, Sven (uidv7805)
user can switch off all port / bus warnings
--- Added comments ---  uidv7805 [Mar 18, 2015 1:26:20 PM CET]
Change Package : 317742:1 http://mks-psad:7002/im/viewissue?selection=317742
Revision 1.36 2015/03/18 07:44:47CET Mertens, Sven (uidv7805)
adding STK version info and parameters to logger at start
--- Added comments ---  uidv7805 [Mar 18, 2015 7:44:48 AM CET]
Change Package : 318008:1 http://mks-psad:7002/im/viewissue?selection=318008
Revision 1.35 2015/02/27 11:54:21CET Hospes, Gerd-Joachim (uidv8815)
add sqlite update info
--- Added comments ---  uidv8815 [Feb 27, 2015 11:54:22 AM CET]
Change Package : 300340:1 http://mks-psad:7002/im/viewissue?selection=300340
Revision 1.34 2015/02/24 12:47:06CET Mertens, Sven (uidv7805)
enabling sqlite SW version check
--- Added comments ---  uidv7805 [Feb 24, 2015 12:47:06 PM CET]
Change Package : 309755:1 http://mks-psad:7002/im/viewissue?selection=309755
Revision 1.33 2015/02/19 13:00:54CET Mertens, Sven (uidv7805)
docu indentation fix
--- Added comments ---  uidv7805 [Feb 19, 2015 1:00:55 PM CET]
Change Package : 308634:1 http://mks-psad:7002/im/viewissue?selection=308634
Revision 1.32 2015/02/19 12:58:42CET Mertens, Sven (uidv7805)
fix wrong import
--- Added comments ---  uidv7805 [Feb 19, 2015 12:58:42 PM CET]
Change Package : 308634:1 http://mks-psad:7002/im/viewissue?selection=308634
Revision 1.31 2015/02/19 11:37:03CET Mertens, Sven (uidv7805)
adding option to Valf to be able to switch off deprecation warnings right away
--- Added comments ---  uidv7805 [Feb 19, 2015 11:37:03 AM CET]
Change Package : 308634:1 http://mks-psad:7002/im/viewissue?selection=308634
Revision 1.30 2015/02/10 19:39:59CET Hospes, Gerd-Joachim (uidv8815)
update docu, fix epydoc errors
--- Added comments ---  uidv8815 [Feb 10, 2015 7:40:00 PM CET]
Change Package : 302321:1 http://mks-psad:7002/im/viewissue?selection=302321
Revision 1.29 2015/02/06 16:56:40CET Hospes, Gerd-Joachim (uidv8815)
add '\' around stk in plugin folder check to allow folders like my_stk_for_testing
--- Added comments ---  uidv8815 [Feb 6, 2015 4:56:40 PM CET]
Change Package : 303227:1 http://mks-psad:7002/im/viewissue?selection=303227
Revision 1.28 2015/01/30 13:12:42CET Hospes, Gerd-Joachim (uidv8815)
remove sqlite version check, planned for 2.2.1
--- Added comments ---  uidv8815 [Jan 30, 2015 1:12:43 PM CET]
Change Package : 296832:1 http://mks-psad:7002/im/viewissue?selection=296832
Revision 1.27 2015/01/30 09:09:19CET Mertens, Sven (uidv7805)
adding deprecation to old functions
--- Added comments ---  uidv7805 [Jan 30, 2015 9:09:20 AM CET]
Change Package : 288765:1 http://mks-psad:7002/im/viewissue?selection=288765
Revision 1.26 2015/01/29 16:11:06CET Mertens, Sven (uidv7805)
using replacer to care about fast connections
Revision 1.25 2015/01/28 15:52:33CET Hospes, Gerd-Joachim (uidv8815)
fix parameter default
--- Added comments ---  uidv8815 [Jan 28, 2015 3:52:34 PM CET]
Change Package : 299370:1 http://mks-psad:7002/im/viewissue?selection=299370
Revision 1.24 2014/11/20 19:37:30CET Hospes, Gerd-Joachim (uidv8815)
add valf/obs to plugin path
--- Added comments ---  uidv8815 [Nov 20, 2014 7:37:30 PM CET]
Change Package : 282158:1 http://mks-psad:7002/im/viewissue?selection=282158
Revision 1.23 2014/07/18 09:30:45CEST Hospes, Gerd-Joachim (uidv8815)
set time log active for passed runs
--- Added comments ---  uidv8815 [Jul 18, 2014 9:30:45 AM CEST]
Change Package : 244453:1 http://mks-psad:7002/im/viewissue?selection=244453
Revision 1.22 2014/07/15 14:00:11CEST Hospes, Gerd-Joachim (uidv8815)
epydoc update, add task loop to submit script
--- Added comments ---  uidv8815 [Jul 15, 2014 2:00:11 PM CEST]
Change Package : 248363:1 http://mks-psad:7002/im/viewissue?selection=248363
Revision 1.21 2014/06/24 13:55:03CEST Hospes, Gerd-Joachim (uidv8815)
update error message for missing bpl file now giving full path/filename
--- Added comments ---  uidv8815 [Jun 24, 2014 1:55:03 PM CEST]
Change Package : 243806:2 http://mks-psad:7002/im/viewissue?selection=243806
Revision 1.20 2014/06/02 14:29:46CEST Hospes, Gerd-Joachim (uidv8815)
set logger name to start script name or to 'valf' if nothing defined
--- Added comments ---  uidv8815 [Jun 2, 2014 2:29:46 PM CEST]
Change Package : 238466:1 http://mks-psad:7002/im/viewissue?selection=238466
Revision 1.19 2014/05/09 11:32:13CEST Hospes, Gerd-Joachim (uidv8815)
report prints either detailed overview table or developer details
--- Added comments ---  uidv8815 [May 9, 2014 11:32:14 AM CEST]
Change Package : 233158:1 http://mks-psad:7002/im/viewissue?selection=233158
Revision 1.18 2014/05/09 10:04:40CEST Hospes, Gerd-Joachim (uidv8815)
pylint fixes
--- Added comments ---  uidv8815 [May 9, 2014 10:04:41 AM CEST]
Change Package : 230866:1 http://mks-psad:7002/im/viewissue?selection=230866
Revision 1.17 2014/05/08 20:08:11CEST Hospes, Gerd-Joachim (uidv8815)
added files from P.Baust with additional tests and some minor valf fixes
--- Added comments ---  uidv8815 [May 8, 2014 8:08:12 PM CEST]
Change Package : 230866:1 http://mks-psad:7002/im/viewissue?selection=230866
Revision 1.16 2014/03/26 14:26:12CET Hecker, Robert (heckerr)
Adapted code to python 3.
--- Added comments ---  heckerr [Mar 26, 2014 2:26:12 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.15 2014/03/13 17:28:49CET Hospes, Gerd-Joachim (uidv8815)
show/log exceptions with stack trace in valf, add. test_exceptions and
fixes in process_manager
--- Added comments ---  uidv8815 [Mar 13, 2014 5:28:49 PM CET]
Change Package : 221496:1 http://mks-psad:7002/im/viewissue?selection=221496
Revision 1.14 2013/11/13 17:50:28CET Hospes, Gerd-Joachim (uidv8815)
type description in docu fixed
--- Added comments ---  uidv8815 [Nov 13, 2013 5:50:28 PM CET]
Change Package : 206278:1 http://mks-psad:7002/im/viewissue?selection=206278
Revision 1.13 2013/11/13 16:20:38CET Hospes, Gerd-Joachim (uidv8815)
add ActivateHpcAutoSplit method and usage of port HpcAutoSplit to Valf class,
updated tests and epydoc for all related files
--- Added comments ---  uidv8815 [Nov 13, 2013 4:20:39 PM CET]
Change Package : 206278:1 http://mks-psad:7002/im/viewissue?selection=206278
Revision 1.12 2013/11/05 11:46:25CET Raedler, Guenther (uidt9430)
- add root path for plugins
--- Added comments ---  uidt9430 [Nov 5, 2013 11:46:26 AM CET]
Change Package : 199465:1 http://mks-psad:7002/im/viewissue?selection=199465
Revision 1.11 2013/10/02 11:44:45CEST Mertens, Sven (uidv7805)
well, sys need to be used directly as it seems to differ from imported variable
--- Added comments ---  uidv7805 [Oct 2, 2013 11:44:45 AM CEST]
Change Package : 185933:7 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.10 2013/10/02 11:24:17CEST Mertens, Sven (uidv7805)
removing additional pylint/pep8 warnings
--- Added comments ---  uidv7805 [Oct 2, 2013 11:24:17 AM CEST]
Change Package : 185933:7 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.9 2013/10/02 11:16:19CEST Mertens, Sven (uidv7805)
help to prevent removal of simulation output data from previous tasks,
defaults stay as they are: output folder is cleared
--- Added comments ---  uidv7805 [Oct 2, 2013 11:16:20 AM CEST]
Change Package : 185933:7 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.8 2013/10/01 13:48:09CEST Hospes, Gerd-Joachim (uidv8815)
new error msg for operator load problems
--- Added comments ---  uidv8815 [Oct 1, 2013 1:48:10 PM CEST]
Change Package : 196951:1 http://mks-psad:7002/im/viewissue?selection=196951
Revision 1.7 2013/10/01 07:32:25CEST Raedler, Guenther (uidt9430)
- added new method to get data ports
--- Added comments ---  uidt9430 [Oct 1, 2013 7:32:26 AM CEST]
Change Package : 197855:1 http://mks-psad:7002/im/viewissue?selection=197855
Revision 1.6 2013/09/19 10:42:56CEST Raedler, Guenther (uidt9430)
- added possiblility to customize plugin folder (review by R.H.)
- use signal_def for Ports
- added busname as argument in SetSimPath(). removed automated bus name
generation as not useful.
- created new methods SetRefSwVersion() and SetSaveResults()
--- Added comments ---  uidt9430 [Sep 19, 2013 10:42:56 AM CEST]
Change Package : 197855:1 http://mks-psad:7002/im/viewissue?selection=197855
Revision 1.5 2013/07/16 13:16:01CEST Hospes, Gerd-Joachim (uidv8815)
update to new style guide
--- Added comments ---  uidv8815 [Jul 16, 2013 1:16:01 PM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.4 2013/07/05 11:47:52CEST Hospes, Gerd-Joachim (uidv8815)
remove nasty prints left from testing
--- Added comments ---  uidv8815 [Jul 5, 2013 11:47:52 AM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.3 2013/07/04 14:34:29CEST Hospes, Gerd-Joachim (uidv8815)
pep8 fix
--- Added comments ---  uidv8815 [Jul 4, 2013 2:34:29 PM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.2 2013/07/04 14:12:59CEST Hospes, Gerd-Joachim (uidv8815)
set simpath second time can't be tested on Jenkins
--- Added comments ---  uidv8815 [Jul 4, 2013 2:12:59 PM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.1 2013/07/04 11:09:23CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
    STK_ScriptingToolKit/04_Engineering/stk/valf/project.pj
"""
