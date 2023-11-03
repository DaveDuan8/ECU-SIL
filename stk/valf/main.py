"""
validation_main.py
------------------

Starts the acc validation.

:org:           Continental AG
:author:        Guenther Raedler

:deprecated:    please use class `Valf` in module valf.py instead
:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:46CEST $
"""
# pylint: disable=W0702

# ===============================================================================
# System Imports
# ===============================================================================
import os
import shutil
import sys
import time
import optparse
import platform
import warnings

# ===============================================================================
# User settings
# ===============================================================================

# The database user name
DB_USER = None

# ===============================================================================
# Project settings
# ===============================================================================

# The database table prefix
DB_TABLE_PREFIX = None

# ===============================================================================
# Master settings
# ===============================================================================
PYLIBFOLDER = os.path.split(os.path.split(os.path.split(__file__)[0])[0])[0]

if PYLIBFOLDER not in sys.path:
    sys.path.append(PYLIBFOLDER)

# ===============================================================================
# Local Imports
# ===============================================================================
import stk.db.db_common as db_common
import stk.util.logger as log
from stk.util.helper import DeprecationUsage

import stk.valf as valf
import stk.valf.db_connector as valf_db

# ===============================================================================
# Constant declarations
# ===============================================================================
DEFAULT_SLAVE_DATA_PROVIDER = "Microsoft.SQLSERVER.MOBILE.OLEDB.3.0"
DEFAULT_SLAVE_DATA_SOURCE = "db_acc_performance.sdf"
DEFAULT_TABLE_PREFIX = ""
TABLE_PREFIX_PATTERN = "<project>_<function>"

# The database file
# Set to None if no database file is being used (e.g. for DBMS with network access)
DB_FILE = None

# The database schema prefix
DB_MASTER_SCHEMA_PREFIX = db_common.DEFAULT_MASTER_SCHEMA_PREFIX

# The database DSN (Data Source Name)
DB_MASTER_DSN = db_common.DEFAULT_MASTER_DSN

# The master DBQ (TSN Service Name)
DB_MASTER_DBQ = db_common.DEFAULT_MASTER_DBQ

SDF_FILE_EXT = [".sdf"]

# Error codes.
RET_VAL_OK = 0
RET_VAL_ERROR = -1

DATA_BUS_NAMES = "DataBusNames"


def list_folders(head_dir):
    """list folders under head dir

    :param head_dir: head folder to search for
    """
    for root, dirs, _ in os.walk(head_dir, topdown=True):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            yield dir_path


def main():
    """main function
    """
    # Parse command line parameters
    optparser = optparse.OptionParser(usage="usage: %prog [options] event-path")
    optparser.add_option("-f", "--dbfile", dest="dbfile",
                         default=None,
                         help="The name of the database file.[default=None]")
    optparser.add_option("-i", "--cfg-file", dest="cfgfile",
                         default='acc_config_file.py',
                         help="The configuration file to use.[default=acc_config_file.py]")
    optparser.add_option("-x", "--cfg-detector-file", dest="cfgdetectorfile",
                         default=None,
                         help="The detector specific xml configuration file to use.[default=None]")
    optparser.add_option("-o", "--output-dir-path", dest="outputdir",
                         default=None,
                         help="The path where the validation results will be generated.[default=None]")
    optparser.add_option("-v", "--software-version", dest="softwareversion",
                         default=None,
                         help="The software version.[default=None]")
    optparser.add_option("-z", "--software-version_reg", dest="softwareversion_regression",
                         default=None,
                         help="The software version.[default=None]")
    optparser.add_option("-m", "--mts-batch-file", dest="mtsbatchfile",
                         default=None,
                         help="The path to the mts batch play list.[default=None]")
    optparser.add_option("-d", "--logging-level", dest="logging_level",
                         default=log.INFO,
                         help="The level of details to be displayed.(10=debug, 20=info,30=warning, "
                              "40=error, 50=critical)[default=%d]" % log.INFO)
    optparser.add_option("-b", "--master-db-dsn", dest="masterdbdsn",
                         default=DB_MASTER_DSN,
                         help="The name of the DSN. [default=%s]" % DB_MASTER_DSN)
    optparser.add_option("-q", "--master-db-dbq", dest="masterdbdbq",
                         default=DB_MASTER_DBQ,
                         help="The name of the DBQ. [default=%s]" % DB_MASTER_DBQ)
    optparser.add_option("-u", "--master-db-user", dest="masterdbuser",
                         default=DB_USER,
                         help="The name of the database user.")
    optparser.add_option("-p", "--master-db-password", dest="masterdbpassword",
                         help="The name of the database password.")
    optparser.add_option("-c", "--master-db-schema-prefix", dest="masterdbschemaprefix",
                         default=DB_MASTER_SCHEMA_PREFIX,
                         help="The name of the database schema prefix. default=%s]"
                               % db_common.DEFAULT_MASTER_SCHEMA_PREFIX)
    optparser.add_option("-t", "--table-prefix", dest="tableprefix",
                         default=None,
                         help="The prefix of the database tables to be used.")
    optparser.add_option("-e", "--error-tolerance", dest="errortolerance",
                         default=db_common.ERROR_TOLERANCE_NONE,
                         help="The error tolerance level from (%d..%d) [default=%d]"
                              % (db_common.ERROR_TOLERANCE_NONE,
                                 db_common.ERROR_TOLERANCE_HIGH,
                                 db_common.ERROR_TOLERANCE_NONE))
    optparser.add_option("-r", "--collection", dest="collection", default=None,
                         help="The name of the rec file catalog collection")
    optparser.add_option("-s", "--report-config", dest="reportconfig", default=None,
                         help="The configuration data for the reporter.")
    optparser.add_option("-w", "--write-option", dest="writeoption", default=None,
                         help="Choose SKIP or REPLACE for database import.")
    optparser.add_option("-y", "--import_by", dest="importby", default=None,
                         help="Import by Login Name - required option")
    optparser.add_option("-a", "--assign_port", dest="assignport", nargs=2, action="append", default=None,
                         help="Assign named Port with given value (2 params!), option repeatable")
    optparser.add_option("--no_deprecation_warings", dest="deprecations", action="store_false", default=True,
                         help="do not print deprecation warnings to output, dangerous as you you'll forget about it!")

    cmd_options = optparser.parse_args()

    # --no_deprecation_warnings
    DeprecationUsage().status = cmd_options[0].deprecations

    # -d    logging_level  The level of details to  be displayed.(10=debug, 20=info,30=warning, 40=error, 50=critical)
    logging_level = int(cmd_options[0].logging_level)

    if logging_level not in log.LEVEL_INFO_MAP:
        logging_level = log.INFO
    logger_file_name = os.path.splitext(os.path.split(__file__)[1])[0]

    # -o     outputdir    The path where the validation results will be generated. [default=None]
    outputdir = cmd_options[0].outputdir
    if outputdir:
        if not os.path.exists(outputdir):
            try:
                os.makedirs(outputdir)
            except:
                print("Error while creating folder: '%s'." % outputdir)
                return RET_VAL_ERROR
        else:
            try:
                outputdir = os.path.abspath(outputdir)
                for entry in os.listdir(outputdir):
                    file_path = os.path.join(outputdir, entry)
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                    elif os.path.isfile(file_path):
                        os.remove(file_path)
            except:
                print("Error while removing folder: '%s'." % outputdir)
                return RET_VAL_ERROR

        if os.path.isdir(outputdir):
            logger = log.Logger(str(sys._getframe().f_code.co_name), logging_level,
                                filename=os.path.join(outputdir, logger_file_name) + ".log")
            logger.warning('Module "main.py" is deprecated, use class "Valf" instead')
            logger.info("Validation started at " + time.strftime('%H:%M:%S', time.localtime(time.time())))
            logger.info("Logging level is set to %s." % (log.LEVEL_INFO_MAP.get(logging_level)))
        else:
            return RET_VAL_ERROR
    else:
        print ("No output folder specified (option -o).")
        return RET_VAL_ERROR

    # -i    cfgfile    The configuration file to use. [default=acc_config_file.py]
    try:
        config_filename = os.path.abspath(cmd_options[0].cfgfile)
        if config_filename is None:
            if os.path.exists(config_filename):
                raise ValueError
    except:
        logger.error("No configuration file specified.")
        optparser.print_help()
        return RET_VAL_ERROR

    plugin_folder_list = []
    for folder_path in list_folders(PYLIBFOLDER):
        plugin_folder_list.append(folder_path)

    try:
        process_mgr_obj = valf.ProcessManager(plugin_folder_list)
    except:
        logger.error("Couldn't instantiate 'ProcessManager' class. ")
        return RET_VAL_ERROR

    if logger is not None:
        logger.info("Using configuration file: '%s'" % config_filename)
    if not process_mgr_obj.load_configuration(config_filename):
        return RET_VAL_ERROR

    process_mgr_obj.set_data_port("ConfigFileName", config_filename)

    # -x     cfgdetectorfile    The detector specific xml configuration file to use. [default=None]
    try:
        config_detector_filename = os.path.abspath(cmd_options[0].cfgdetectorfile)
        if not config_detector_filename:
            if os.path.exists(config_detector_filename):
                raise ValueError
        process_mgr_obj.set_data_port("ConfigDetectorFile", config_detector_filename)
    except:
        logger.error("No configuration file specified.")
        optparser.print_help()
        return RET_VAL_ERROR

    # -e
    process_mgr_obj.set_data_port("ErrorTolerance", cmd_options[0].errortolerance, "Bus#1")

    # -f     dbfile    The name of the database file. [default=None]
    database_filename = cmd_options[0].dbfile
    masterdbuser = cmd_options[0].masterdbuser
    if database_filename is not None:
        try:
            database_filename = os.path.abspath(cmd_options[0].dbfile)
            if not os.path.exists(database_filename):
                raise ValueError
            process_mgr_obj.set_data_port("dbfile", database_filename, "DBBus#1")
        except:
            logger.error("Invalid database file specified: '%s'. (option -f)" % database_filename)
            return RET_VAL_ERROR

    elif masterdbuser is not None:  # could be that Oracle database connection is required
        # -b     masterdbdsn    The name of the DSN. [default=%s]
        try:
            masterdbdsn = cmd_options[0].masterdbdsn
            if masterdbdsn is not None:
                process_mgr_obj.set_data_port(valf_db.MASTER_DB_DSN_PORT_NAME, masterdbdsn, "DBBus#1")
        except:
            logger.error("No '%s' parameter specified. (option -b)" % valf_db.MASTER_DB_DSN_PORT_NAME)

        # -q     masterdbdbq    The name of the DBQ. [default=%s]
        try:
            masterdbdbq = cmd_options[0].masterdbdbq
            if masterdbdbq is not None:
                process_mgr_obj.set_data_port(valf_db.MASTER_DB_DBQ_PORT_NAME, masterdbdbq, "DBBus#1")
        except:
            logger.error("No '%s' parameter specified. (option -q)" % valf_db.MASTER_DB_DSN_PORT_NAME)

        # -u     masterdbuser   The name of the database user
        try:
            masterdbuser = cmd_options[0].masterdbuser
            if masterdbuser is not None:
                process_mgr_obj.set_data_port(valf_db.MASTER_DB_USR_PORT_NAME, masterdbuser, "DBBus#1")
        except:
            logger.error("No '%s' file specified. (option -u)" % valf_db.MASTER_DB_USR_PORT_NAME)

        # -p     masterdbpassword         The name of the database password
        try:
            masterdbpassword = cmd_options[0].masterdbpassword
            if masterdbpassword is not None:
                process_mgr_obj.set_data_port(valf_db.MASTER_DB_PW_PORT_NAME, masterdbpassword, "DBBus#1")
        except:
            logger.error("No '%s' specified. (option -p)" % valf_db.MASTER_DB_PW_PORT_NAME)

        # -c     masterdbschemaprefix     The name of the database schema prefix
        try:
            masterdbschemaprefix = cmd_options[0].masterdbschemaprefix
            if masterdbschemaprefix is not None:
                process_mgr_obj.set_data_port(valf_db.MASTER_DB_SPX_PORT_NAME, masterdbschemaprefix, "DBBus#1")
        except:
            logger.error("No '%s' specified. (option -c)" % valf_db.MASTER_DB_SPX_PORT_NAME)

            try:
                if platform.release() == "XP":
                    process_mgr_obj.set_data_port(valf_db.MASTER_DB_DRV_PORT_NAME,
                                                  db_common.DEFAULT_MASTER_DRV_XP, "DBBus#1")
            except:
                logger.error("Error retrieving the platform or setting '%s'" % valf_db.MASTER_DB_DRV_PORT_NAME)

    # -t      tableprefix              The prefix of the database tables to be used
    try:
        tableprefix = cmd_options[0].tableprefix
        if tableprefix is not None:
            process_mgr_obj.set_data_port("tableprefix", tableprefix, "DBBus#1")
    except:
        logger.error("No 'tableprefix' file specified. (option -c)")
    try:
        if os.path.isdir(outputdir):
            process_mgr_obj.set_data_port("OutputDirPath", os.path.abspath(outputdir))
            logger.debug("OutputDirPath: '%s'" % outputdir)
        else:
            return RET_VAL_ERROR
    except:
        pass

    # -a    assign_port      port, value to preset data ports, repeatable
    try:
        assignport = cmd_options[0].assignport
        for port in assignport:
            process_mgr_obj.set_data_port(port[0], port[1])
            logger.debug("setting input data. [PortName='{0}', PortValue='{1}'] ".format(port[0], port[1]))
    except:
        pass

    # Command line parameters without options. Second imOutputPath is used for regression testing.
    data_bus_names = []
    for bus_num in range(len(cmd_options[1])):
        try:
            sim_output_path = str(cmd_options[1][bus_num])
            bus_name = "bus#{0}".format(bus_num + 1)
            if os.path.exists(sim_output_path):
                process_mgr_obj.set_data_port("SimOutputPath", sim_output_path, bus_name)
                logger.debug("Setting input data. [ bus='{0}', "
                             "PortName='SimOutputPath', PortValue={1}]".format(bus_name, sim_output_path))
                data_bus_names.append(bus_name)
        except:
            pass

    process_mgr_obj.set_data_port(DATA_BUS_NAMES, data_bus_names)

    # -v    softwareversion    The software version. [default=None]
    software_version = cmd_options[0].softwareversion
    if software_version is None:
        logger.error("No software version specified.")
        optparser.print_help()
        return RET_VAL_ERROR
    else:
        process_mgr_obj.set_data_port("SWVersion", software_version)

    # -z  softwareversion    The software version. [default=None]
    softwareversion_regression = cmd_options[0].softwareversion_regression
    if softwareversion_regression is None:
        logger.info("No regression software version specified.")
    else:
        process_mgr_obj.set_data_port("SWVersion_REG", softwareversion_regression)

    # -m    mtsbatchfile       The path to the mts batch play list. [default=None]
    mts_batch_pathname = cmd_options[0].mtsbatchfile
    if mts_batch_pathname is not None:
        # additional check
        if not os.path.isfile(mts_batch_pathname):
            logger.error("MTS batch play list does not exist: %s" % mts_batch_pathname)

        if mts_batch_pathname and os.path.isfile(mts_batch_pathname):
            process_mgr_obj.set_data_port("BplFilePath", os.path.abspath(mts_batch_pathname))
            logger.debug("BplFilePath: '%s'" % mts_batch_pathname)
        else:
            logger.error("Could not open/load mts batch play list %s, check if file is readable." % mts_batch_pathname)
            optparser.print_help()
            return RET_VAL_ERROR

    # -r    collection       The name of the collection
    collection_name = cmd_options[0].collection
    if collection_name is not None:
        process_mgr_obj.set_data_port("RecCatCollectionName", collection_name)
        logger.debug("Rec file cataloge collection name is: '%s'" % collection_name)

    # Check that we have at least a batch or a collection.
    if mts_batch_pathname is None and collection_name is None:
        logger.error("No BplFilePath or Collection specified.")
        optparser.print_help()
        return RET_VAL_ERROR

    # -s    reportconfig    The configuration data for the reporter.
    report_config = cmd_options[0].reportconfig
    if report_config is not None:
        process_mgr_obj.set_data_port("ReportConfig", report_config)
        logger.debug("The report config is: '%s'" % report_config)

    # -w Set the write option.
    write_option = cmd_options[0].writeoption
    if write_option is not None:
        process_mgr_obj.set_data_port("WriteOption", write_option)
        logger.info("Write option is set to %s." % (write_option))

    # -y    importby    The import is done by
    try:
        importby = cmd_options[0].importby
        if importby is None:
            importby = os.environ["USERNAME"]

        process_mgr_obj.set_data_port("ImportBy", importby)
        logger.debug("Files are imported by %s." % (importby))
    except:
        logger.error("No User Id of the Importer specified")
        optparser.print_help()
        return RET_VAL_ERROR

    # start validation
    tstart = time.time()
    ret_val = process_mgr_obj.run()
    if ret_val is RET_VAL_OK:
        logger.info("Test duration(hh:mm:ss): " + time.strftime('%H:%M:%S', time.gmtime(time.time() - tstart)))
        logger_statistics = logger.get_statistics()
        log_info_list = []
        for logging_level in logger_statistics:
            log_info_list.append("%s: %d" % (logging_level, logger_statistics[logging_level]))

        logger.info("Logging statistics: " + ", ".join(log_info_list))

    return ret_val


if __name__ == "__main__":
    warnings.warn("valf's main is deprecated, please use class 'Valf' instead!!!",
                  UserWarning if sys.version_info[1] <= 7 else PendingDeprecationWarning, stacklevel=2)
    sys.exit(main())


"""
CHANGE LOG:
-----------
$Log: main.py  $
Revision 1.1 2015/04/23 19:05:46CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/valf/project.pj
Revision 1.10 2015/02/19 14:35:46CET Mertens, Sven (uidv7805) 
removing some pylints
--- Added comments ---  uidv7805 [Feb 19, 2015 2:35:47 PM CET]
Change Package : 308634:1 http://mks-psad:7002/im/viewissue?selection=308634
Revision 1.9 2015/02/19 13:13:36CET Mertens, Sven (uidv7805)
adaptation to deprecated main as well
Revision 1.8 2014/06/24 10:57:46CEST Hospes, Gerd-Joachim (uidv8815)
improved bpl file error, added deprication warning
--- Added comments ---  uidv8815 [Jun 24, 2014 10:57:46 AM CEST]
Change Package : 243806:1 http://mks-psad:7002/im/viewissue?selection=243806
Revision 1.7 2014/03/26 14:26:13CET Hecker, Robert (heckerr)
Adapted code to python 3.
--- Added comments ---  heckerr [Mar 26, 2014 2:26:13 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.6 2013/05/29 15:26:03CEST Raedler, Guenther (uidt9430)
- undo changes in rev. 1.5
--- Added comments ---  uidt9430 [May 29, 2013 3:26:03 PM CEST]
Change Package : 184344:1 http://mks-psad:7002/im/viewissue?selection=184344
Revision 1.4 2013/05/22 17:54:37CEST Hospes, Gerd-Joachim (uidv8815)
add option 'assign-port' to set any port value usng -a <PortName> <PortValue>
--- Added comments ---  uidv8815 [May 22, 2013 5:54:37 PM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.3 2013/04/23 16:18:37CEST Raedler, Guenther (uidt9430)
- added StandardError for exceptions
- use oracle DB connections optionally
--- Added comments ---  uidt9430 [Apr 23, 2013 4:18:39 PM CEST]
Change Package : 180569:2 http://mks-psad:7002/im/viewissue?selection=180569
Revision 1.2 2013/04/19 18:31:53CEST Hospes, Gerd-Joachim (uidv8815)
pep8 fixes, tested with valf demo
--- Added comments ---  uidv8815 [Apr 19, 2013 6:31:54 PM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.1 2013/04/18 13:59:58CEST Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/valf/project.pj
Revision 2.0 2013/02/20 08:38:22CET Raedler, Guenther (uidt9430)
- supports STK2.0 with packages
--- Added comments ---  uidt9430 [Feb 20, 2013 8:38:22 AM CET]
Change Package : 175124:1 http://mks-psad:7002/im/viewissue?selection=175124
Revision 1.18 2012/11/05 11:29:31CET Raedler, Guenther (uidt9430)
- added new input pararmeter for algo regression version
--- Added comments ---  uidt9430 [Nov 5, 2012 11:29:36 AM CET]
Change Package : 163448:2 http://mks-psad:7002/im/viewissue?selection=163448
Revision 1.17 2012/04/25 10:22:09CEST Raedler-EXT, Guenther (uidt9430)
- check the operating system to set the master driver in case of WinXP
--- Added comments ---  uidt9430 [Apr 25, 2012 10:22:10 AM CEST]
Change Package : 111588:1 http://mks-psad:7002/im/viewissue?selection=111588
Revision 1.16 2012/04/17 12:03:51CEST Raedler-EXT, Guenther (uidt9430)
- upgrades for Oracle 11g (masterdsn is not mandatory for new oracle database)
- use standard port names for database parameters
--- Added comments ---  uidt9430 [Apr 17, 2012 12:03:55 PM CEST]
Change Package : 111588:1 http://mks-psad:7002/im/viewissue?selection=111588
Revision 1.15 2011/11/18 13:21:24CET Raedler Guenther (uidt9430) (uidt9430)
- support multiple simulation output pathes
--- Added comments ---  uidt9430 [Nov 18, 2011 1:21:24 PM CET]
Change Package : 88150:1 http://mks-psad:7002/im/viewissue?selection=88150
Revision 1.14 2011/11/08 13:40:12CET Sorin Mogos (mogoss)
* update: added  STK library path
--- Added comments ---  mogoss [Nov 8, 2011 1:40:13 PM CET]
Change Package : 85403:1 http://mks-psad:7002/im/viewissue?selection=85403
Revision 1.13 2011/09/08 12:03:52CEST Castell Christoph (uidt6394) (uidt6394)
Re-enabled use without database.
--- Added comments ---  uidt6394 [Sep 8, 2011 12:03:52 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.12 2011/08/22 11:58:41CEST Castell Christoph (uidt6394) (uidt6394)
Change to path imports.
--- Added comments ---  uidt6394 [Aug 22, 2011 11:58:42 AM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.11 2011/08/19 09:45:49CEST Sorin Mogos (mogoss)
* fix: corrected import of VALF folder
--- Added comments ---  mogoss [Aug 19, 2011 9:45:54 AM CEST]
Change Package : 75815:1 http://mks-psad:7002/im/viewissue?selection=75815
Revision 1.10 2011/08/19 09:22:53CEST Sorin Mogos (mogoss)
* update: import valf and stk libraries
* fix: exit when output path (-o option) is not specified
--- Added comments ---  mogoss [Aug 19, 2011 9:22:53 AM CEST]
Change Package : 75815:1 http://mks-psad:7002/im/viewissue?selection=75815
Revision 1.9 2011/08/11 14:00:58CEST Sorin Mogos (mogoss)
* update: re-added 'writeoption' and 'importedby' options
--- Added comments ---  mogoss [Aug 11, 2011 2:00:58 PM CEST]
Change Package : 72325:1 http://mks-psad:7002/im/viewissue?selection=72325
Revision 1.8 2011/08/11 13:29:04CEST Sorin Mogos (mogoss)
* fix: some database connection bug fixes
--- Added comments ---  mogoss [Aug 11, 2011 1:29:04 PM CEST]
Change Package : 72325:1 http://mks-psad:7002/im/viewissue?selection=72325
Revision 1.6 2011/07/28 14:24:56CEST Castell Christoph (uidt6394) (uidt6394)
Added -s switch for ReportConfig entry.
--- Added comments ---  uidt6394 [Jul 28, 2011 2:24:57 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.5 2011/07/26 15:00:10CEST Raedler Guenther (uidt9430) (uidt9430)
-- added error handling for output path
--- Added comments ---  uidt9430 [Jul 26, 2011 3:00:11 PM CEST]
Change Package : 67780:5 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.4 2011/07/22 08:41:04CEST Raedler Guenther (uidt9430) (uidt9430)
-- fixed error  in path init
--- Added comments ---  uidt9430 [Jul 22, 2011 8:41:05 AM CEST]
Change Package : 67780:5 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.3 2011/07/14 12:54:20CEST Castell Christoph (uidt6394) (uidt6394)
Included all relevant paths.
--- Added comments ---  uidt6394 [Jul 14, 2011 12:54:20 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.2 2011/07/07 12:44:23CEST Castell Christoph (uidt6394) (uidt6394)
Path changes as validation_main is in a different location
than the old start_em_validation.
Revision 1.1 2011/07/05 12:48:26CEST Castell Christoph (uidt6394) (uidt6394)
Initial revision
Member added to project /nfs/projekte1/PROJECTS/ARS301/06_Algorithm/05_Testing/
05_Test_Environment/algo/ars301_req_test/valf_tests/vpc/project.pj
Revision 1.4 2011/06/16 11:14:44CEST Raedler Guenther (uidt9430) (uidt9430)
- extended start_em_validation by additional options and changed some
existing option tags
- put/load database file on/from new DBBus#1
--- Added comments ---  uidt9430 [Jun 16, 2011 11:14:44 AM CEST]
Change Package : 67780:2 http://mks-psad:7002/im/viewissue?selection=67780
Revision 1.3 2011/03/18 15:19:06CET Castell Christoph (uidt6394) (uidt6394)
Path changes for new location.
--- Added comments ---  uidt6394 [Mar 18, 2011 3:19:06 PM CET]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.2 2011/03/17 09:46:00CET Castell Christoph (uidt6394) (uidt6394)
Small syntax changes.
--- Added comments ---  uidt6394 [Mar 17, 2011 9:46:00 AM CET]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.1 2011/03/08 16:10:27CET Castell Christoph (uidt6394) (uidt6394)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
EM_EnvironmentModel/05_Testing/05_Test_Environment/algo/em_req_test/valf_tests/
em/common/project.pj
Revision 1.1 2011/03/08 15:57:13CET Castell Christoph (uidt6394) (uidt6394)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
EM_EnvironmentModel/05_Testing/05_Test_Environment/algo/em_req_test/valf_tests/
em/common/01_Source_Code/project.pj
Revision 1.15 2011/01/27 11:34:58CET Gicu Benchea (bencheag)
Add the configuration as a data port "ConfigFileName"
--- Added comments ---  bencheag [Jan 27, 2011 11:34:58 AM CET]
Change Package : 54038:1 http://mks-psad:7002/im/viewissue?selection=54038
Revision 1.14 2011/01/11 13:36:14CET Castell Christoph (uidt6394) (uidt6394)
Changed location of ConfigDetectorFile from Bus1 to Global.
--- Added comments ---  uidt6394 [Jan 11, 2011 1:36:14 PM CET]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.13 2011/01/11 11:47:38CET Castell Christoph (uidt6394) (uidt6394)
Added comments and functionality for database_filename (-f)
and config_detector_filename (-x).
Revision 1.12 2010/12/09 14:55:59CET Sorin Mogos (mogoss)
* update: set DEFAULT_TABLE_PREFIX to ""
--- Added comments ---  mogoss [Dec 9, 2010 2:55:59 PM CET]
Change Package : 56339:1 http://mks-psad:7002/im/viewissue?selection=56339
Revision 1.11 2010/11/03 15:59:27CET Sorin Mogos (mogoss)
* update with configuration info
Revision 1.10 2010/10/18 14:24:29CEST Sorin Mogos (mogoss)
* added option for simulation path
--- Added comments ---  mogoss [Oct 18, 2010 2:24:29 PM CEST]
Change Package : 50879:1 http://mks-psad:7002/im/viewissue?selection=50879
Revision 1.9 2010/09/23 10:35:27CEST Sorin Mogos (mogoss)
* updated to store complete rec file path in the report
--- Added comments ---  mogoss [Sep 23, 2010 10:35:27 AM CEST]
Change Package : 51595:1 http://mks-psad:7002/im/viewissue?selection=51595
Revision 1.8 2010/08/03 13:11:23CEST Sorin Mogos (mogoss)
* removed the mandatory database file option from the command line.
--- Added comments ---  mogoss [Aug 3, 2010 1:11:23 PM CEST]
Change Package : 47041:2 http://mks-psad:7002/im/viewissue?selection=47041
Revision 1.7 2010/07/22 11:12:28CEST Sorin Mogos (mogoss)
* changed log file directory
* removed intermediate *.dat files used for plotting
--- Added comments ---  mogoss [Jul 22, 2010 11:12:28 AM CEST]
Change Package : 47041:2 http://mks-psad:7002/im/viewissue?selection=47041
Revision 1.4 2010/06/28 15:56:33EEST Sorin Mogos (smogos)
* changed logger file path
--- Added comments ---  smogos [2010/06/28 12:56:34Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.3 2010/06/28 14:35:31EEST Sorin Mogos (smogos)
* code clean-up
* configuration changes
--- Added comments ---  smogos [2010/06/28 11:35:31Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.2 2010/06/21 16:28:08EEST Sorin Mogos (smogos)
* changed according to new configuration format
--- Added comments ---  smogos [2010/06/21 13:28:08Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.8 2010/05/05 12:19:59EEST Sorin Mogos (smogos)
* small bug-fix and code customisation
--- Added comments ---  smogos [2010/05/05 09:19:59Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.5 2010/03/19 15:26:31EET Sorin Mogos (smogos)
* code customisation and bug-fixes
--- Added comments ---  smogos [2010/03/19 13:26:31Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
"""
