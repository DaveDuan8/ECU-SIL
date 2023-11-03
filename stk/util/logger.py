"""
stk/util/logger
---------------

Logger class for logging messages to the console and/or file

**User-API Interfaces**

    - `utils` (complete package),
    - `Logger`,
    - `LoggerException`

Other defined classes for internal usage, interface changes are possible without warning.

:org:           Continental AG
:author:        Sorin Mogos

:version:       $Revision: 1.11 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/12/13 16:14:34CET $
"""
# pylint: disable=W0142

__all__ = ["Logger", "LoggerException"]

# - imports -----------------------------------------------------------------------------------------------------------
import sys
from logging import NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL, getLogger, addLevelName, \
    FileHandler, StreamHandler, Formatter
from os import getpid, environ
from collections import OrderedDict

# - stk imports -------------------------------------------------------------------------------------------------------
from stk.error import StkError
from stk.util.helper import singleton, Wmi

# - defines -----------------------------------------------------------------------------------------------------------
EXCEPTION = CRITICAL + 10

LEVEL_CALL_MAP = OrderedDict((('notset', 0), ('debug', DEBUG), ('info', INFO), ('warning', WARNING),
                              ('error', ERROR), ('critical', CRITICAL), ('exception', EXCEPTION)))

MEM_LEVELS = ((1228, DEBUG), (1433, INFO), (1638, WARNING), (sys.maxint, CRITICAL))
MBYTE = 1048576


# - classes -----------------------------------------------------------------------------------------------------------
class LoggerException(StkError):
    """Database errors """
    def __init__(self, description):
        self.__description = description
        StkError.__init__(self, description)

    def __str__(self):
        return str(self.__description)


@singleton
class LoggerManager(object):
    """
    **the singleton logging mechanism **

    for handling runtime information of different modules.

    If no output stream is defined 'sys.stdout' is used.
    """

    DEBUG, INFO, WARNING, ERROR, CRITICAL = range(10, 51, 10)

    # def __init__(self, logger_name, level=DEBUG, filename=None, strm=None):

    def __init__(self, filename=None, strm=None):
        """init the real logger (but just once)"""
        self._statistics = {v: 0 for v in LEVEL_CALL_MAP.values()}
        self._level = NOTSET
        self._lastmsg = None
        self.handlers = []
        self._wmi = Wmi()
        self._pid = getpid()

        if not strm:
            strm = sys.stdout

        # we're on HPC cluster, here we're using appstarter log and want to prevent double timing prints...
        self._use_print = "CCP_SCHEDULER" in environ and strm in [sys.stdout, sys.stderr]

        addLevelName(EXCEPTION, 'EXCEPTION')
        logger = getLogger()
        logger.setLevel(DEBUG)

        if filename is not None:
            try:
                handler = FileHandler(filename, "w")
            except:
                raise LoggerException("Couldn't create/open file '%s'. Please check permisions." % filename)

            formatter = Formatter("%(asctime)s %(name)-15s - %(levelname)s: %(message)s", "%d.%m.%Y %H:%M:%S")
            handler.setFormatter(formatter)
            handler.setLevel(DEBUG)
            self.handlers.append(handler)

        if not self._use_print:
            handler = StreamHandler(strm)
            formatter = Formatter("%(asctime)s %(name)s - %(levelname)s: %(message)s", "%d.%m.%Y %H:%M:%S")
            handler.setFormatter(formatter)
            handler.setLevel(DEBUG)
            self.handlers.append(handler)

        for i in self.handlers:
            logger.addHandler(i)

    @property
    def level(self):
        """retrieves initial debug level
        """
        return self._level

    @level.setter
    def level(self, level):
        """sets initial debug level

        :param level: this level will be taken once when not set before
        :return: level
        """
        if self._level == NOTSET:
            if level == NOTSET:
                self._level = DEBUG
            else:
                self._level = level

    def get_statistics(self):
        """Gets number of each type of logging message"""
        return OrderedDict((k, self._statistics[v]) for k, v in LEVEL_CALL_MAP.items())

    @property
    def lastmsg(self):
        """returns the last logging message text"""
        return self._lastmsg

    def log(self, name, baselevel, level, msg):
        """do the log

        :param name: name of logger to use
        :param baselevel: base log level of logger
        :param level: level of logging
        :param msg: message to log
        """
        if level >= baselevel:
            if self._use_print:
                if level > INFO:
                    sys.stderr.write(msg + '\n')
                else:
                    print(msg)
            if len(self.handlers) > 0:
                getLogger(name).log(level, msg)
            self._statistics[level] += 1
        else:
            self._statistics[0] += 1

        self._lastmsg = msg

    def mem_usage(self, name, baselevel):
        """logs memory usage for current PID

        :param baselevel: base log level
        :param name: name of logging
        """
        try:
            proc = self._wmi.execute('Win32_PerfRawData_PerfProc_Process', ["WorkingSet", "WorkingSetPeak"],
                                     IDProcess=self._pid)[0]
            if proc is not None:
                wset = int(proc.WorkingSet) / MBYTE
                self.log(name, baselevel, next(i[1] for i in MEM_LEVELS if wset < i[0]),
                         "memory usage: %dMB, peak: %dMB" % (wset, int(proc.WorkingSetPeak) / MBYTE))
        except:
            self.log(name, baselevel, INFO, "please, check your WMI installation!")


class ProxyLogger(object):
    """Wrapper object for a method to be called.
    """
    def __init__(self, func, **xargs):
        """
        :param func: function / method to wrap
        :param xargs: arguments to pass via __call__
        """
        self.func, self.xargs = func, xargs

    def __call__(self, *args, **kwds):
        """
        :param args: additional arguments
        :param kwds: even more arguments to pass than given in __init__
        :return: result from actual function call
        """
        self.xargs.update(kwds)
        if len(args) == 1:  # can only be the msg
            self.xargs.update({'msg': args[0]})
            return self.func(**self.xargs)
        elif len(args) == 0 and 'level' in self.xargs and self.xargs['level'] == DEBUG:
            self.xargs['msg'] = str(sys._getframe(1).f_code.co_name) + "()" + " called."
            return self.func(**self.xargs)
        else:
            return self.func(*args, **self.xargs)


class Logger(object):
    """logger instance

    :

    usage
    -----
    .. python::

        from logging import DEBUG
        # logging to file + console
        main_logger = logger.Logger("my_main_logger", level=DEBUG, filename="my_logging_file.log")

        # logging to console
        main_logger = logger.Logger("my_main_logger", level=DEBUG)

        #where:
        #  logger_name: is the name of the logger
        #  level:       is the logging level [10=DEBUG, 20=INFO,
        #                                     30=WARNING, 40=ERROR,
        #                                     50=CRITICAL]
        #  filename:    None : only console,  FilePath: Log file

        # displays message as debug
        main_logger.debug("This is a debug message")
        # displays message as info
        main_logger.info("This is an info message")
        # displays message as warning
        main_logger.warning("This is a warning")
        # displays message as error
        main_logger.error("This is an error message")
        # displays message as critical
        main_logger.critical("This is a critical message")
        # displays message as exception
        # -> to be called from an exception handler
        main_logger.exception("This is an exception message")

        # change global logging level to INFO level (from logging import INFO)
        main_logger.level = INFO

        # log memory usage info of current process < 1.2GB, level will be DEBUG, etc...
        main_logger.mem_usage()

        # retrieve actual logging level
        lev = main_logger.level

        # retrieve statistics
        stats = main_logger.get_statistics()

        # created from another script
        logger2 = logger.Logger("my_logger2")
        # displays message as info
        logger2.info(" This is an info message")
        #...

    """
    def __init__(self, logger_name, level=NOTSET, filename=None, strm=None):
        """your logger...

        :param logger_name: name of global logger
        :type logger_name: str
        :param level: initial level of logging, if NOTSET, DEBUG level will be used
        :type level: int
        :param filename: name of file (incl. path) to log to
        :type filename: str | None
        :param strm: stream to push logs out as well
        :type strm: None | stdout | stderr
        """
        self._logger_name = logger_name
        self._logger = LoggerManager(filename, strm)
        self._logger.level = level
        if level == NOTSET:
            self._level = self._logger.level
        else:
            self._level = level

    def __getattr__(self, item):
        """uses proxy to pass calls to logger manager

        :param item: log level
        :type item: str
        :return: function pointer from logger manager to debug, info, etc method
        """
        if item in LEVEL_CALL_MAP:
            return ProxyLogger(self._logger.log, name=self._logger_name,
                               baselevel=self._level, level=LEVEL_CALL_MAP[item])
        elif hasattr(self._logger, item):
            if item == "mem_usage":
                return ProxyLogger(self._logger.mem_usage, name=self._logger_name, baselevel=self._level)
            return getattr(self._logger, item)
        else:
            raise AttributeError(item)

    @property
    def level(self):
        """returns current log level"""
        return self._level

    @level.setter
    def level(self, level):
        """changes level of logger

        :param level: level to change global level to
        """
        self._level = level

    def log(self, level, msg):
        """log a msg at a certain level

        :param msg: message to log
        :param level: level to use
        """
        self._logger.log(self._logger_name, self._level, level, msg)

    if 0:  # please, don't remove: kept here for documentation purposes and intellisense...
        @staticmethod
        def debug(msg=None):
            """do a debug log entry

            :param msg: message to push to logger, can be left out to just state your method has been called.
            """
            pass

        @staticmethod
        def info(msg):
            """do an info log entry

            :param msg: message to push to logger
            """
            pass

        @staticmethod
        def warning(msg):
            """do a warning log entry

            :param msg: message to push to logger
            """
            pass

        @staticmethod
        def critical(msg):
            """do a critical log entry

            :param msg: message to push to logger
            """
            pass

        @staticmethod
        def error(msg):
            """do an error log entry

            :param msg: message to push to logger
            """
            pass

        @staticmethod
        def exception(msg):
            """do an exception log entry

            :param msg: message to push to logger
            """
            pass

        @staticmethod
        def mem_usage():
            """does a log at certain level of how much memory is in use and peak mem was used
            """
            pass

        @staticmethod
        def get_statistics():
            """returns statistics

            :returns: statistics of how much messages have been sent via levels
            """
            pass


class DummyLogger(object):
    """dummy logger"""
    def __init__(self, use_print=False):
        """use real print or not"""
        self._use_print = False if hasattr(use_print, "__call__") else use_print
        self._store = use_print if hasattr(use_print, "__call__") else None

    def _dummy(self, data):
        """dummy method"""
        if self._store:
            self._store(data)

    @staticmethod
    def _print(text):
        """print text"""
        print(text)

    @staticmethod
    def _perr(text):
        """print to stderr"""
        sys.stderr.write(text + "\n")

    def __getattr__(self, which):
        """for each missing, return dummy"""
        if self._use_print:
            return self._perr if which == "error" else self._print
        else:
            return self._dummy


"""
CHANGE LOG:
-----------
$Log: logger.py  $
Revision 1.11 2016/12/13 16:14:34CET Hospes, Gerd-Joachim (uidv8815) 
fix LoggerException and test
Revision 1.10 2016/08/15 15:49:30CEST Mertens, Sven (uidv7805)
although print could be used, filehandler should taken care of nevertheless
Revision 1.9 2016/06/17 12:33:01CEST Mertens, Sven (uidv7805)
providing a dummy logger for cmd output vs. logger output automaticamente
Revision 1.8 2016/06/13 11:43:59CEST Hospes, Gerd-Joachim (uidv8815)
strm param default to None again, does not update stream if directly set to sys.stdout
Revision 1.7 2016/06/10 17:02:24CEST Hospes, Gerd-Joachim (uidv8815)
set default strm to stdout and remove check
Revision 1.6 2016/05/20 08:02:52CEST Mertens, Sven (uidv7805)
remove times when run on hpc cluster
Revision 1.5 2016/05/13 17:51:00CEST Hospes, Gerd-Joachim (uidv8815)
fix logger error on jenkins runs
Revision 1.4 2016/05/09 12:42:28CEST Mertens, Sven (uidv7805)
in case of HPC run, use AppStarter logging and just write to stdout and stderr
Revision 1.3 2016/03/24 17:08:14CET Hospes, Gerd-Joachim (uidv8815)
set stdout as default for logging output
Revision 1.2 2015/08/07 14:39:24CEST Mertens, Sven (uidv7805)
update
- Added comments -  uidv7805 [Aug 7, 2015 2:39:25 PM CEST]
Change Package : 365583:1 http://mks-psad:7002/im/viewissue?selection=365583
Revision 1.1 2015/04/23 19:05:31CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/util/project.pj
Revision 1.19 2015/04/09 16:31:40CEST Hospes, Gerd-Joachim (uidv8815)
add traceback to log for exceptions
--- Added comments ---  uidv8815 [Apr 9, 2015 4:31:41 PM CEST]
Change Package : 326836:1 http://mks-psad:7002/im/viewissue?selection=326836
Revision 1.18 2015/03/19 17:05:34CET Mertens, Sven (uidv7805)
removing some pylints
--- Added comments ---  uidv7805 [Mar 19, 2015 5:05:35 PM CET]
Change Package : 318794:1 http://mks-psad:7002/im/viewissue?selection=318794
Revision 1.17 2015/03/19 13:18:39CET Mertens, Sven (uidv7805)
implementation for changing log levels,
first instanziation sets global level
--- Added comments ---  uidv7805 [Mar 19, 2015 1:18:39 PM CET]
Change Package : 318794:1 http://mks-psad:7002/im/viewissue?selection=318794
Revision 1.16 2015/01/23 14:50:02CET Mertens, Sven (uidv7805)
adding memory logging
--- Added comments ---  uidv7805 [Jan 23, 2015 2:50:03 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.15 2014/03/24 21:56:57CET Hecker, Robert (heckerr)
Adapted to python 3.
--- Added comments ---  heckerr [Mar 24, 2014 9:56:57 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.14 2013/10/01 16:41:24CEST Mertens, Sven (uidv7805)
last fine adjustment
--- Added comments ---  uidv7805 [Oct 1, 2013 4:41:24 PM CEST]
Change Package : 185933:7 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.13 2013/10/01 14:43:03CEST Mertens, Sven (uidv7805)
importing logging as needed by other modules
--- Added comments ---  uidv7805 [Oct 1, 2013 2:43:04 PM CEST]
Change Package : 185933:7 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.12 2013/10/01 13:36:23CEST Mertens, Sven (uidv7805)
adding removed StkLogger functionality to util logger instead
--- Added comments ---  uidv7805 [Oct 1, 2013 1:36:23 PM CEST]
Change Package : 185933:7 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.11 2013/09/10 16:10:02CEST Hospes, Gerd-Joachim (uidv8815)
add lastmsg method, fix pep8/pylint errors, update docu
--- Added comments ---  uidv8815 [Sep 10, 2013 4:10:03 PM CEST]
Change Package : 190320:1 http://mks-psad:7002/im/viewissue?selection=190320
Revision 1.10 2013/05/23 06:33:19CEST Mertens, Sven (uidv7805)
to ease function call debug output, empty msg can be used
--- Added comments ---  uidv7805 [May 23, 2013 6:33:20 AM CEST]
Change Package : 179495:8 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.9 2013/04/19 12:51:07CEST Hecker, Robert (heckerr)
Functionality revert to version 1.7.
--- Added comments ---  heckerr [Apr 19, 2013 12:51:07 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.8 2013/04/12 14:38:29CEST Mertens, Sven (uidv7805)
empty debug message is replace by function call () output
--- Added comments ---  uidv7805 [Apr 12, 2013 2:38:30 PM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.7 2013/03/28 15:25:16CET Mertens, Sven (uidv7805)
pylint: W0311 (indentation), string class
--- Added comments ---  uidv7805 [Mar 28, 2013 3:25:17 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.6 2013/03/28 14:20:07CET Mertens, Sven (uidv7805)
pylint: solving some W0201 (Attribute %r defined outside __init__) errors
Revision 1.5 2013/02/27 17:55:08CET Hecker, Robert (heckerr)
Removed all E000 - E200 Errors regarding Pep8.
--- Added comments ---  heckerr [Feb 27, 2013 5:55:09 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2012/12/14 16:22:46CET Hecker, Robert (heckerr)
Removed stk Prefixes in Classes, Member Variables,....
--- Added comments ---  heckerr [Dec 14, 2012 4:22:46 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2012/12/05 13:49:47CET Hecker, Robert (heckerr)
Updated code to pep8 guidelines.
--- Added comments ---  heckerr [Dec 5, 2012 1:49:47 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2012/12/05 11:56:24CET Hecker, Robert (heckerr)
Update regarding pep8.
--- Added comments ---  heckerr [Dec 5, 2012 11:56:24 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2012/12/04 18:01:46CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/util/project.pj
"""
